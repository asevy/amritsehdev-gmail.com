"""Valuation engine v1 - the first decomposition.

Values an ownership block at market without attributing it to anyone
the graph hasn't earned: the WGCL block prices mechanically
(shares x price -> JMD -> USD), every input carries its as-of date and
computed freshness, the deduplication invariant is enforced via block
ids, and family attribution renders as UNRESOLVED while the blocker
claim stands. This proves the engine's mechanics without violating the
attribution invariant.

Usage: python3 valuation.py            # prints the WGCL decomposition
"""
from __future__ import annotations

import datetime

from schema import freshness, no_double_count
from store import Ledger


def _num(x) -> float:
    return float(str(x).replace(",", ""))


def latest(led, subject, predicate):
    cands = [c for c in led.claims.values()
             if c.subject == subject and c.predicate == predicate
             and c.status in ("PROPOSED", "APPROVED")
             and not c.valid_to]
    return max(cands, key=lambda c: str(c.valid_from or "")) if cands \
        else None


def decompose_holding(led, holding_claim_id: str, today: str = None):
    """Value one holding block; refuse silent attribution."""
    today = today or datetime.date.today().isoformat()
    h = led.claims[holding_claim_id]
    blocks = no_double_count([h])  # invariant: block_id required
    h = blocks[0]
    held = h.object.get("company") if isinstance(h.object, dict) else None
    shares = _num(h.object["shares"])
    price_c = latest(led, held, "reported_price")
    fx_c = latest(led, held, "reported_fx")
    if price_c is None:
        return {"error": "no price claim for " + str(held)}
    price = _num(price_c.object["price_jmd"])
    jmd = shares * price
    usd = jmd / _num(fx_c.object["rate"]) if fx_c else None

    def inp(c, label):
        o = c.object if isinstance(c.object, dict) else {}
        return {"claim": c.id, "label": label,
                "as_of": o.get("as_of", c.valid_from),
                "freshness": freshness(c, today),
                "status": c.status}

    inputs = [inp(h, "holding"), inp(price_c, "price")]
    if fx_c:
        inputs.append(inp(fx_c, "fx"))
    # Attribution: does an unresolved blocker stand over this holder?
    blockers = [c for c in led.claims.values()
                if c.predicate.endswith("_unresolved")
                and c.status in ("LEAD", "PROPOSED")
                and h.subject in (
                    [c.object] if isinstance(c.object, str) else
                    list(c.object.values())
                    if isinstance(c.object, dict) else [])]
    approved_only = all(c.status == "APPROVED"
                        for c in (h, price_c) + ((fx_c,) if fx_c else ()))
    return {
        "holder": led.entities[h.subject].name,
        "company": led.entities[held].name if held in led.entities
        else held,
        "block_id": h.block_id,
        "shares": f"{shares:,.0f}",
        "pct": h.object.get("pct", ""),
        "value_jmd": jmd,
        "value_usd": usd,
        "inputs": inputs,
        "family_attributable": ("UNRESOLVED — " + "; ".join(
            c.id for c in blockers)) if blockers else
        "no unresolved blocker recorded",
        "basis": ("verified graph" if approved_only else
                  "mark-to-model on UNAPPROVED research-layer inputs — "
                  "internal only, not publishable"),
        "today": today,
    }


def decompose_family(led, fam_id: str, today: str = None):
    """v1: the family's blocked holdco block(s), priced but
    unattributed."""
    out = []
    for c in led.claims.values():
        if c.subject == fam_id and \
                c.predicate == "beneficial_ownership_unresolved" and \
                c.status in ("LEAD", "PROPOSED"):
            target = c.object if isinstance(c.object, str) else None
            if not target:
                continue
            for h in led.claims.values():
                if h.subject == target and \
                        "shareholder" in h.predicate and \
                        h.status in ("PROPOSED", "APPROVED") and \
                        not h.valid_to and h.block_id:
                    out.append(decompose_holding(led, h.id, today))
    return out


def state_card(led, fam_id: str, today: str = None):
    """Known Value vs Attributable Value — the honest readout.

    'Asset value known / control path partly known / family attribution
    unresolved' is a valid, useful state; the card states it explicitly
    instead of forcing a net-worth number. The attribution stop rule
    applies: nothing traverses upward past the first unresolved control
    or beneficial-ownership edge.
    """
    today = today or datetime.date.today().isoformat()
    decs = [d for d in decompose_family(led, fam_id, today)
            if "error" not in d and d.get("value_usd")]
    if not decs:
        return None
    seen_blocks = set()
    total = 0.0
    for d in decs:
        if d["block_id"] in seen_blocks:
            continue
        seen_blocks.add(d["block_id"])
        total += d["value_usd"]
    holders = {d["holder"] for d in decs}
    own_asof = max((str(i["as_of"]) for d in decs for i in d["inputs"]
                    if i["label"] == "holding"), default="—")
    marks = [(str(i["as_of"]), i["freshness"]) for d in decs
             for i in d["inputs"] if i["label"] == "price"]
    live = all(f in ("current",) for _, f in marks) if marks else False
    ctrl_stated = any("ultimate_controlling" in c.predicate
                      and c.status in ("PROPOSED", "APPROVED")
                      for c in led.claims.values())
    ctrl_open = any(c.predicate == "control_path_unresolved"
                    and c.status in ("LEAD", "PROPOSED")
                    for c in led.claims.values())
    control = ("partial — ultimate controller stated, path unverified"
               if ctrl_stated and ctrl_open else
               "stated" if ctrl_stated else "unknown")
    members = {c.subject for c in led.claims.values()
               if c.predicate == "member_of" and c.object == fam_id
               and c.status not in ("SUPERSEDED", "RETRACTED",
                                    "REJECTED")}
    bo_ack = any(c.predicate == "beneficial_interest_in"
                 and c.subject in members
                 and c.status in ("PROPOSED", "APPROVED")
                 for c in led.claims.values())
    bo_conf = ("moderate on existence (issuer-acknowledged), low on "
               "quantum" if bo_ack else "low")
    blockers = sorted({c.id for c in led.claims.values()
                       if c.predicate.endswith("_unresolved")
                       and c.status in ("LEAD", "PROPOSED")
                       and (c.subject == fam_id or
                            (isinstance(c.object, str) and
                             led.entities.get(c.object) and
                             led.entities[c.object].name in holders)
                            or led.entities.get(c.subject, None) and
                            led.entities[c.subject].name in holders)})
    return {
        "family": led.entities[fam_id].name,
        "known_value_usd": total,
        "known_value_label": f"US${total/1e6:,.0f}M",
        "attributable": "unresolved — " + ", ".join(blockers)
        if blockers else "resolved",
        "live_priced_portion": "100% of the known block(s)"
        if marks else "0%",
        "control_chain": control,
        "bo_confidence": bo_conf,
        "last_ownership_verification": own_asof,
        "last_market_mark": (f"{marks[-1][0]} [{marks[-1][1]}]"
                             if marks else "none"),
        "public_form": (
            f"Publicly traceable assets associated with the family's "
            f"control structure exceed US${total/1e6:,.0f}M, but the "
            f"exact attributable family interest remains unresolved."),
        "today": today,
    }


if __name__ == "__main__":
    led = Ledger("data")
    for d in decompose_family(led, "mahfood_family"):
        if "error" in d:
            print("error:", d["error"]); continue
        usd = (f" ≈ USD {d['value_usd']/1e6:,.1f}M"
               if d["value_usd"] else "")
        print(f"{d['holder']} — {d['pct']} of {d['company']} "
              f"({d['shares']} sh)")
        print(f"  block {d['block_id']}: "
              f"JMD {d['value_jmd']/1e9:,.2f}B{usd}")
        for i in d["inputs"]:
            print(f"  input {i['label']}: {i['claim']} as of "
                  f"{i['as_of']} [{i['freshness']}] ({i['status']})")
        print(f"  family-attributable portion: {d['family_attributable']}")
        print(f"  basis: {d['basis']}")
    card = state_card(led, "mahfood_family")
    if card:
        print("\nKNOWN vs ATTRIBUTABLE —", card["family"])
        for k in ("known_value_label", "attributable",
                  "live_priced_portion", "control_chain",
                  "bo_confidence", "last_ownership_verification",
                  "last_market_mark"):
            print(f"  {k.replace('_', ' ')}: {card[k]}")
        print(f"  public form: {card['public_form']}")
