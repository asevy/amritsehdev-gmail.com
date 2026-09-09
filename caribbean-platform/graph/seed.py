"""One-time bootstrap: the first real entities, sources and claims from
the validation sprint's live research (2026-09-08/09). Everything enters
as PROPOSED or LEAD - nothing is APPROVED until an analyst verifies it
against preserved primary documents. Run once: python3 graph/seed.py
"""
from schema import Claim, Entity, Source
from store import Ledger


def main() -> None:
    led = Ledger("data")
    if led.claims:
        print(f"ledger already seeded ({len(led.claims)} claims); "
              "refusing to reseed")
        return

    # -- entities -------------------------------------------------------
    for e in [
        Entity("goddard_enterprises", "Goddard Enterprises Limited",
               "company", jurisdiction="BB",
               notes="BSE-listed conglomerate; validation-sprint "
                     "Profile #1 anchor"),
        Entity("goddard_family", "Goddard family", "family",
               jurisdiction="BB",
               notes="Founding family of Goddard Enterprises; current "
                     "economic ownership is the open Profile #1 question"),
        Entity("neptune_investments_bb", "Neptune Investments Limited",
               "company", jurisdiction="BB", status="unknown",
               notes="Disclosed >5% GEL holder per 2022 shareholder "
                     "analysis; ownership unresolved - CAIPO inquiry is "
                     "the follow-up task"),
        Entity("sagicor_group", "Sagicor Group", "company",
               notes="Disclosed >5% GEL holder per 2022 shareholder "
                     "analysis; institutional"),
        Entity("matthew_d_goddard", "Matthew D. Goddard", "person",
               jurisdiction="BB"),
        Entity("wisynco_group", "Wisynco Group Limited", "company",
               jurisdiction="JM",
               notes="JSE-listed; validation-sprint Profile #3 anchor"),
        Entity("mahfood_family", "Mahfood family", "family",
               jurisdiction="JM",
               notes="Profile #3; listed/private hybrid stress case"),
    ]:
        led.add_entity(e)

    # -- sources --------------------------------------------------------
    led.add_source(Source(
        id="S-2026-0001",
        description="Goddard Enterprises corporate site (For Investors / "
                    "company pages), located via open-web search",
        tier=3, retrieval_date="2026-09-08",
        url_or_registry_id="https://goddardenterprisesltd.com/for-investors/",
        passage="Founded 1921, Bridgetown; publicly listed; four "
                "divisions; ~22 countries; AR archive incl. 2012",
        analyst="claude-session", access="publishable",
        preserved=False,
        notes="Direct retrieval blocked by session egress proxy; "
              "preservation pending network policy or manual pull"))
    led.add_source(Source(
        id="S-2026-0002",
        description="GEL shareholder notice: availability of 2025 annual "
                    "report (31 Dec 2025); management proxy circular URL",
        tier=2, retrieval_date="2026-09-09",
        url_or_registry_id="https://goddardenterprisesltd.com/"
                           "2025-annual-report/",
        analyst="claude-session", access="publishable", preserved=False,
        notes="Company-published; document itself not yet retrieved"))
    led.add_source(Source(
        id="S-2026-0003",
        description="Founder-supplied reading of GEL 2022 shareholder "
                    "analysis and 2024 annual report board listing",
        tier=3, retrieval_date="2026-09-09",
        passage=">5% holders 2022: Neptune Investments Limited 13.87M "
                "shares; Sagicor Group 26.21M shares; no Goddard-family "
                "block >5%. Matthew D. Goddard on 2024 board.",
        analyst="claude-session", access="internal", preserved=False,
        notes="Secondhand until verified against the annual reports "
              "themselves; then re-source at tier 2 and re-grade"))
    led.add_source(Source(
        id="S-2026-0004",
        description="Barbados Companies Act Cap. 308 - official PDFs "
                    "(CAIPO / Barbados Law Courts); s.176 'Basic list of "
                    "shareholders' heading in arrangement of sections",
        tier=1, retrieval_date="2026-09-09",
        url_or_registry_id="https://caipo.gov.bb/wp-content/uploads/2021/"
                           "09/5.-Companies-Act-Cap.-308.pdf",
        analyst="claude-session", access="publishable", preserved=False,
        notes="Statute copy; permitted-use question outstanding with "
              "counsel"))

    # -- claims (all PROPOSED/LEAD; approval awaits analyst + primary
    #    documents) ------------------------------------------------------
    led.add_claim(Claim(
        id="C-2026-0001", subject="goddard_enterprises",
        predicate="listed_on", object="Barbados Stock Exchange",
        sources=["S-2026-0001"], status="PROPOSED",
        notes="Confirm listing detail from BSE data in live requests"))
    led.add_claim(Claim(
        id="C-2026-0002", subject="goddard_enterprises",
        predicate="founded", object="1921",
        sources=["S-2026-0001"], status="PROPOSED"))
    led.add_claim(Claim(
        id="C-2026-0003", subject="goddard_family",
        predicate="heritage_founder_of", object="goddard_enterprises",
        sources=["S-2026-0001"], status="PROPOSED",
        notes="Heritage edge only - implies NO current economic stake; "
              "current ownership is the open research question"))
    led.add_claim(Claim(
        id="C-2026-0004", subject="neptune_investments_bb",
        predicate="registry_registered_shareholder_of",
        object={"company": "goddard_enterprises",
                "shares": "13,870,000",
                "context": ">5% disclosed holders, 2022"},
        valid_from="2022", sources=["S-2026-0003"], status="PROPOSED",
        registry_verbatim="Neptune Investments Limited - 13.87M shares "
                          "(2022 shareholder analysis, as related; "
                          "verify against the annual report)",
        notes="Registered relationship only; who owns Neptune is the "
              "next node"))
    led.add_claim(Claim(
        id="C-2026-0005", subject="sagicor_group",
        predicate="registry_registered_shareholder_of",
        object={"company": "goddard_enterprises",
                "shares": "26,210,000",
                "context": ">5% disclosed holders, 2022"},
        valid_from="2022", sources=["S-2026-0003"], status="PROPOSED",
        registry_verbatim="Sagicor Group - 26.21M shares (2022 "
                          "shareholder analysis, as related; verify "
                          "against the annual report)"))
    led.add_claim(Claim(
        id="C-2026-0006", subject="matthew_d_goddard",
        predicate="role_director_of", object="goddard_enterprises",
        valid_from="2024", sources=["S-2026-0003"], status="PROPOSED",
        notes="Board presence is never evidence of economic ownership"))
    led.add_claim(Claim(
        id="C-2026-0007", subject="neptune_investments_bb",
        predicate="ownership_unresolved", object="unknown",
        status="LEAD",
        notes="Follow-up task: CAIPO Company Inquiry on Neptune "
              "Investments Limited (Barbados playbook step 5)"))
    led.add_claim(Claim(
        id="C-2026-0008", subject="mahfood_family",
        predicate="possible_controlling_interest_in",
        object="wisynco_group", status="LEAD",
        notes="Profile #3 starting hypothesis; COJ reverse search and "
              "Wisynco AR top-shareholder table are the first requests"))

    print(f"seeded: {len(led.entities)} entities, {len(led.sources)} "
          f"sources, {len(led.claims)} claims "
          f"(verified graph: {len(led.verified_graph())} - correctly "
          f"empty until analyst approval)")


if __name__ == "__main__":
    main()
