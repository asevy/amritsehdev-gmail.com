"""Append-only claim ledger.

Three JSONL files (entities, sources, claims) under graph/data/. Nothing
is ever rewritten in place: every mutation appends a new record, and the
latest record for an id wins on load - so the full history of every
claim, including supersessions and status changes, stays in the file.

Usage:
    from graph.store import Ledger
    led = Ledger("caribbean-platform/graph/data")
    led.current("goddard_enterprises")          # live claims about GEL
    led.approve("C-0002", analyst="MR", date="2026-09-10")
    led.supersede("C-0003", new_claim)          # correction, not erasure

Self-test: python3 graph/store.py
"""
from __future__ import annotations

import dataclasses
import json
import pathlib
from typing import Optional

from schema import Claim, Entity, Source, publishable  # noqa: F401


class Ledger:
    def __init__(self, data_dir: str):
        self.dir = pathlib.Path(data_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.entities: dict[str, Entity] = {}
        self.sources: dict[str, Source] = {}
        self.claims: dict[str, Claim] = {}
        self._load()

    # -- persistence ----------------------------------------------------
    def _file(self, kind: str) -> pathlib.Path:
        return self.dir / f"{kind}.jsonl"

    def _load(self) -> None:
        for kind, cls, target in (("entities", Entity, self.entities),
                                  ("sources", Source, self.sources),
                                  ("claims", Claim, self.claims)):
            f = self._file(kind)
            if not f.exists():
                continue
            for line in f.read_text().splitlines():
                if not line.strip():
                    continue
                rec = cls(**json.loads(line))
                target[rec.id] = rec  # latest record for an id wins

    def _append(self, kind: str, rec) -> None:
        with self._file(kind).open("a") as f:
            f.write(json.dumps(dataclasses.asdict(rec),
                               ensure_ascii=False) + "\n")

    # -- writes (validated, append-only) --------------------------------
    def add_entity(self, e: Entity) -> Entity:
        e.validate()
        self.entities[e.id] = e
        self._append("entities", e)
        return e

    def add_source(self, s: Source) -> Source:
        s.validate()
        self.sources[s.id] = s
        self._append("sources", s)
        return s

    def add_claim(self, c: Claim) -> Claim:
        c.validate()
        for sid in c.sources:
            if sid not in self.sources:
                raise ValueError(f"{c.id}: unknown source {sid}")
        if c.subject not in self.entities:
            raise ValueError(f"{c.id}: unknown subject {c.subject}")
        self.claims[c.id] = c
        self._append("claims", c)
        return c

    def approve(self, claim_id: str, analyst: str, date: str) -> Claim:
        c = dataclasses.replace(self.claims[claim_id], status="APPROVED",
                                analyst=analyst, verified_date=date)
        c.validate()
        self.claims[c.id] = c
        self._append("claims", c)
        return c

    def supersede(self, old_id: str, new_claim: Claim) -> Claim:
        """Corrections chain; they never erase."""
        self.add_claim(new_claim)
        old = dataclasses.replace(self.claims[old_id], status="SUPERSEDED",
                                  superseded_by=new_claim.id)
        self.claims[old.id] = old
        self._append("claims", old)
        return new_claim

    # -- reads ----------------------------------------------------------
    def query(self, subject: Optional[str] = None,
              predicate: Optional[str] = None,
              status: Optional[str] = None) -> list[Claim]:
        out = []
        for c in self.claims.values():
            if subject and c.subject != subject:
                continue
            if predicate and c.predicate != predicate:
                continue
            if status and c.status != status:
                continue
            out.append(c)
        return sorted(out, key=lambda c: c.id)

    def current(self, subject: Optional[str] = None) -> list[Claim]:
        """Live claims: not superseded, not retracted."""
        return [c for c in self.query(subject=subject)
                if c.status in ("LEAD", "PROPOSED", "APPROVED")]

    def verified_graph(self) -> list[Claim]:
        """Only APPROVED claims support publication or valuation."""
        return self.query(status="APPROVED")


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        led = Ledger(td)
        led.add_entity(Entity(id="co_x", name="Company X", type="company"))
        led.add_entity(Entity(id="fam_y", name="Family Y", type="family"))
        s = led.add_source(Source(id="S1", description="registry filing",
                                  tier=1, retrieval_date="2026-09-09",
                                  access="internal"))
        # LEAD without source: fine (research layer).
        led.add_claim(Claim(id="C1", subject="fam_y",
                            predicate="possible_link", object="co_x"))
        # PROPOSED without source: must fail.
        try:
            led.add_claim(Claim(id="C2", subject="fam_y",
                                predicate="owns", object="co_x",
                                status="PROPOSED"))
            raise AssertionError("unsourced PROPOSED accepted")
        except ValueError:
            pass
        # Registry claim without verbatim: must fail.
        try:
            led.add_claim(Claim(id="C3", subject="fam_y",
                                predicate="registry_shareholder_of",
                                object="co_x", sources=["S1"],
                                status="PROPOSED"))
            raise AssertionError("registry claim without verbatim accepted")
        except ValueError:
            pass
        # BO claim without statutory basis: must fail.
        try:
            led.add_claim(Claim(id="C4", subject="fam_y",
                                predicate="bo_owner_of", object="co_x",
                                sources=["S1"], status="PROPOSED"))
            raise AssertionError("BO claim without basis accepted")
        except ValueError:
            pass
        # Correct forms pass; approval and supersession chain works.
        c5 = led.add_claim(Claim(
            id="C5", subject="fam_y",
            predicate="registry_shareholder_of", object="co_x",
            sources=["S1"], status="PROPOSED",
            registry_verbatim="Family Y Holdings Ltd - 62,000 shares"))
        led.approve("C5", analyst="test", date="2026-09-09")
        c6 = Claim(id="C6", subject="fam_y",
                   predicate="registry_shareholder_of", object="co_x",
                   sources=["S1"], status="PROPOSED",
                   registry_verbatim="Family Y Holdings Ltd - 54,000 shares")
        led.supersede("C5", c6)
        assert led.claims["C5"].status == "SUPERSEDED"
        assert led.claims["C5"].superseded_by == "C6"
        assert not publishable(c5, led.sources)  # internal-only source
        # Reload from disk: history intact, latest state wins.
        led2 = Ledger(td)
        assert led2.claims["C5"].status == "SUPERSEDED"
        assert len(led2.verified_graph()) == 0  # C5 no longer live
        print("ledger self-test: OK "
              f"({len(led2.claims)} claims, {len(led2.sources)} sources)")
