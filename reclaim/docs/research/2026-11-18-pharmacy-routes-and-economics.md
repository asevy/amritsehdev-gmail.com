# Pharmacy routes and per-fill economics for a GLP-1 body-composition programme (Ontario first)

Prepared 2026-11-18. This is pharmacy-operations and regulatory research, not legal advice. Items marked **[COUNSEL]** need an Ontario health-regulatory lawyer, and for the physician/NP side ideally CMPA/CNPS input too.

## How to read this report

**Figure labels**

| Label | Meaning |
|---|---|
| **VERIFIED** | Read directly in a primary source during this session (statute or regulation text, ODB price file, OCP or CPSO document). |
| **ADVERTISED** | A retail or cash price published by a pharmacy, a price aggregator or the media. These were not checked against a live pharmacy quote. |
| **BENCHMARK** | A comparable reference figure, such as the ODB public-plan fee. It is not the price the platform will actually pay or receive. |
| **ASSUMPTION** | An analyst modelling input with no source. Replace it with real quotes or data. |
| **UNKNOWN** | Not found or not verifiable in this session. |

**Confidence:** H = primary text read; M = reputable secondary source or a search-engine summary of a primary source; U = aggregator, unverified, or analyst inference.

**Research constraints in this session (they matter for how far to trust some sections)**
- The session's network allowlist let me fetch only these directly: ontario.ca (e-Laws, ODB files), cpso.on.ca, OCP PDFs under www.ocpinfo.com/wp-content, and laws-lois.justice.gc.ca.
- These were **blocked**: OCP HTML pages, canada.ca, Job Bank, Costco, insurer sites and news sites. For those I relied on search-engine result summaries, labelled "(via search)".
- The shared web-search budget ran out part-way through. As a result, private-insurer fee caps, Job Bank wages, card-processing price lists and courier rate cards are **UNKNOWN** and are entered as labelled assumptions.
- To close these gaps, allow www.jobbank.gc.ca, ocpinfo.com, canada.ca and the relevant insurer and pharmacy sites in the environment's network settings, and run a follow-up search pass.

---

## 0. Decision-relevant summary

1. **A commercial company cannot control an Ontario pharmacy.** DPRA s.142 sets two separate tests. A majority of the **directors** must be pharmacists (s.142(1)), **and** a majority of **each class of shares** must be owned and registered by pharmacists or OCP-authorised pharmacy professional corporations (s.142(2)). So a platform can hold **at most a minority (under 50%) of every share class** and a minority of board seats. You cannot structure around this with non-voting or preferred classes, because the test applies class by class. (VERIFIED, H)
2. **The physicians (and very likely the NPs) in the partner practice should hold no equity in, and take no money from, the pharmacy.** This should extend to any platform entity that takes pharmacy income. O. Reg. 114/94 s.16(a) makes it a conflict for a physician, their family or a corporation they control to receive **any benefit, directly or indirectly**, from a supplier that supplies goods or services to the physician's patients. Unlike s.17 (facilities), s.16 has **no disclosure exception**. (VERIFIED text, H; application M) **[COUNSEL]**
3. **Per-prescription fees, revenue shares and referral-linked "marketing" fees paid by the pharmacy to the platform are the highest-risk structures.**
   - O. Reg. 264/16 s.34 para 2 bars a pharmacy from conferring a benefit "by reason of the referral of a patient".
   - s.34 para 4 bars arrangements that influence, or appear to influence, a prescriber to promote the pharmacy.
   - s.34 para 5 bars arrangements that adversely influence, or appear to influence, professional judgment.
   - All of these reach acts done "directly or indirectly" or through "another person". (VERIFIED, H)
   - The only explicit safe harbours are three: normal-market **rent** (s.35(2)); disclosed non-arm's-length referrals where **no direct benefit** is received (s.35(1)); and disclosed or public-company **supplier interests** (s.35(3)).
   - Fixed, fair-market-value fees for real services are **not expressly permitted**. They are defensible only by analogy to the rent safe harbour. **[COUNSEL]**
4. **Patient choice is hard law, not just policy.**
   - Restricting choice of pharmacy without written consent is proprietary misconduct (O. Reg. 264/16 s.32 para 18), and the pharmacist-level equivalent is O. Reg. 130/17 Part I para 22.
   - CPSO says suggesting a specific pharmacy is appropriate only where it is in the patient's best interest and creates no conflict of interest.
   - Pharmacy benefits to patients are limited to price adjustments or nominal-value items (s.34 para 3).
   - Price advertising of Schedule I (prescription) drugs is restricted (O. Reg. 264/16 s.29; FDR C.01.044). (VERIFIED, H)
5. **Economics: a GLP-1 fill is a thin-margin, pass-through-heavy transaction.**
   - Roughly **90–95% of the retail price is drug cost** passed through to the wholesaler and manufacturer.
   - The pharmacy's gross margin is the markup plus the dispensing fee: about **$29–$74 on a ~$430–$475 brand pen**, and **$15–$26 on a ~$94–$104 generic semaglutide pen** (ILLUSTRATIVE).
   - After pharmacist and technician time, cold-chain packaging, signature courier, card fees, bad debt and non-returnable spoilage, the **pharmacy-level retained contribution before fixed overhead and tax** is roughly:
     - brand, couriered: **−$68 to +$43 per fill (mid −$14)**
     - brand, picked up: **−$18 to +$58 (mid +$15)**
     - generic semaglutide, couriered: **−$58 to +$2 (mid −$25)**
     - generic, picked up: **−$13 to +$16 (mid +$2)**
   - A platform holding a ≤49% minority stake would retain **≤49% of the pharmacy's after-overhead, after-tax profit**. That is plausibly **$0–$20 per fill in favourable cases, and negative for couriered generics**.
   - Generic semaglutide (ODB price **$78.141 per pen**, VERIFIED, effective 2026-06-30) and Sevmia (generic Wegovy, approved 2026-06-29) will push gross margin further toward the dispensing fee alone.
6. **Implication.** The pharmacy is unlikely to be a material lawful profit centre for the platform. The more robust lawful income route is **patient-paid programme fees that are identical wherever the patient fills**, with any pharmacy relationship limited to:
   - (a) a minority equity stake with pro-rata dividends that are not tied to referrals; and/or
   - (b) fixed, FMV-supported fees for real services (technology, logistics), not tied to volume and documented by an independent valuation. **[COUNSEL]**

---

## 1. Corrections to the "already established" list

| Item as given | Correction or refinement | Confidence |
|---|---|---|
| "DPRA ss.142, 144 (ownership by pharmacists or corporations with pharmacist-majority directors)" | **Incomplete.** s.142 has **two cumulative limbs**: (1) a majority of directors are pharmacists, **and** (2) a majority of **each class of shares** is owned by and registered to pharmacists or pharmacy health profession corporations holding an OCP certificate of authorization. Other points: s.142(4) exempts only the share limb, and only for corporations operating a pharmacy on 14 May 1954. s.142(5) exempts non-profit multidisciplinary health corporations. New s.142(6) and s.144(3) (in force 2026-01-01, S.O. 2025 c.11 Sched. 3, Bill 56) exclude "As of Right" out-of-province pharmacists from counting as "pharmacist" for ownership. The e-Laws code is 90h04 (R.S.O. 1990, c. H.4). | H |
| "O. Reg. 264/16 ss.29, 34–35 (pharmacy conflicts/inducements)" | **s.29 is the advertising rule**, not a conflict rule. Conflicts are in **ss.33 (definitions), 34 and 35**. Operating in conflict is proprietary misconduct under **s.32 para 13**. Also relevant from s.32: para 11 (disclosing prescription information only de-identified, under written agreement); para 15 (excessive fees); para 16 (charging more than the advertised total including dispensing fee); para 17 (solicitation); para 18 (agreements restricting choice of pharmacy); para 19 (refrigerated drugs cannot be returned to stock). | H |
| "O. Reg. 130/17" | Correct. Its title is *Professional Misconduct and Conflict of Interest* (Pharmacy Act, 1991), and it binds individual pharmacists and technicians. Conflicts are in Part II ss.4–7. Part I para 9 is practising in a conflict; para 22 is restricting choice of pharmacist; para 24 is permitting contravention of Part V (advertising) of O. Reg. 264/16. | H |
| "O. Reg. 114/94 s.16 (physician conflicts)" | Correct. Add s.15, whose very broad "benefit" definition includes any fee for services except under a compliant written contract. Add s.16(d): no selling drugs to patients at a profit, except immediate, emergency or no-pharmacist circumstances. Note that s.16 has **no disclosure exception**; the disclosure and public-company exceptions are only in s.17, for facilities. | H |
| "FDR C.01.044" | Correct. The current wording refers to a "prescription drug": representations to the general public are limited to brand name, proper name, common name, price and quantity. | H |

---

## 2. Ownership routes (Q1)

### 2.1 Exact statutory text (DPRA, R.S.O. 1990 c. H.4; e-Laws consolidation from 2026-01-01)

- **s.142(1):** "No corporation shall own or operate a pharmacy unless the majority of the directors of the corporation are pharmacists." (VERIFIED, H)
- **s.142(2):** "No corporation shall own or operate a pharmacy unless a majority of each class of shares of the corporation is owned by and registered in the name of pharmacists or in the name of health profession corporations each of which holds a valid certificate of authorization issued by the College." (VERIFIED, H)
- **s.142(3):** shares of a deceased pharmacist's estate count as a pharmacist's shares for up to 4 years. **s.142(4):** subs. (2) does not apply to corporations operating a pharmacy on 14 May 1954. **s.142(5):** the section does not apply to non-profit multidisciplinary health corporations. **s.142(6):** "pharmacist" excludes persons prescribed by regulation ("As of Right" out-of-province registrants). (VERIFIED, H)
- **s.144(1):** "No person other than a pharmacist or a corporation complying with the requirements of section 142 shall own or operate a pharmacy." (VERIFIED, H)
- **s.143:** a pharmacist whose registration is revoked or suspended for cause may not work in a pharmacy, act as a director, or vote as a shareholder. **s.146:** a pharmacy must be supervised by a physically present pharmacist (except remote dispensing locations) and managed by a pharmacist designated manager. (VERIFIED, H)
- **Background to the 2026 change.** The OCP Board briefing (20 Nov 2025) explains that Bill 56, the *Building a More Competitive Economy Act, 2025*, extended "As of Right" to pharmacists. It also notes that the deemed-pharmacist definition "does not apply to Section 142 … and Section 144". (VERIFIED, H)

### 2.2 Who can hold what

| Holder | Shares | Directors | Notes | Confidence |
|---|---|---|---|---|
| Ontario-registered pharmacists / pharmacy HPCs | Must hold a majority of **each** class | Must be a majority of the board | The designated manager must be a pharmacist (s.146). | H |
| Commercial company (the platform), non-pharmacist individuals | **Minority of each class only** (i.e., <50%) | Minority | The draft OCP *Standards of Operation* (consultation, June 2026) state that "owners, shareholders, officers and directors, whether or not they are registered with the College," must understand their responsibilities. The definition of "Owner" includes each director. | H (statute); M (draft standard) |
| Physicians / NPs (as investors) | DPRA itself does not bar a minority stake | DPRA itself does not bar a minority seat | **But** O. Reg. 114/94 s.16(a) makes it a conflict for a physician who refers patients to that pharmacy, or whose patients it supplies (see 2.3). A stake in an unrelated pharmacy that never serves their patients is not caught by s.16. | H (text); M (application) |
| A pre-1954 grandfathered corporation | The share-majority test is waived (s.142(4)) | **The director-majority test still applies** | This is a real but scarce route to non-pharmacist economic ownership. Its availability and acquisition terms are UNKNOWN. **[COUNSEL]** | H (text); U (market) |
| Non-profit multidisciplinary health corporation | Exempt (s.142(5)) | Exempt | Not available to a commercial platform. | H |

**Control rights.** s.142 counts shares and directors. It does not expressly address shareholder agreements, vetoes, debt covenants or management contracts that give a minority investor practical control. Such terms create risk in two ways:
- they may make the investor "non-arm's length" (O. Reg. 264/16 s.33 defines this by "ability to exercise … control or significant influence over the operating and financial decisions");
- they may "adversely influence … professional judgment" (s.34 para 5). **[COUNSEL]** (H text; M interpretation)

**Franchise precedent.** DIDFA s.12.1(1) expressly refers to "companies that own, operate or franchise pharmacies", so franchisor/pharmacist-owner models are a recognised structure in Ontario. Whether a franchise royalty is lawful when the **franchisor is also the patient-referral source** (as the platform would be) is a separate and open question under s.34 para 2. **[COUNSEL]** (H text; U application)

### 2.3 Prescriber (physician / NP) ownership or financial interest

- **Physicians, O. Reg. 114/94 s.16.** It is a conflict where the member, a family member, or a corporation "wholly, substantially, or actually owned or controlled" by either:
  - (a) "receives any benefit, directly or indirectly, from (i) a supplier to whom the member refers his or her patients … or (ii) a supplier who sells or otherwise supplies any medical goods or services to the patients of the member";
  - (b)/(c) rents premises to or from such a supplier, except at normal rent not tied to volume or referrals;
  - (d) sells drugs to a patient at a profit, except in immediate, emergency or no-pharmacist circumstances.
  - "Medical goods or services" includes drugs. A "supplier" includes anyone who supplies medical goods or services, so a pharmacy is a supplier and **the platform itself may be one**. (VERIFIED, H)
  - Under s.15(c), fees for services count as a "benefit" unless paid under a written contract for each service, within the member's specialty, and supported by records. (VERIFIED, H)
- **What this means for the structure.**
  - Physician equity in the fulfilment pharmacy → dividends are a benefit from a supplier to their patients → conflict. There is no disclosure cure. (H text; M application)
  - Physician equity in, or volume-linked pay from, a platform that takes pharmacy income → "indirect" benefit risk. (M) **[COUNSEL]**
  - The platform paying the practice in any way that varies with pharmacy fills → high risk under both O. Reg. 114/94 s.16 and O. Reg. 264/16 s.34 para 4. (M)
- **CPSO, current "Professional Obligations" format** (the old "Prescribing Drugs" policy has been restructured; page downloaded 17 Nov 2026):
  - *Obligations in Practice: Prescribing Drugs*, "Pharmacy selection": "Patients may choose the pharmacy that best meets their needs. Suggesting a specific pharmacy is appropriate only where it is in the patient's best interest and does not give rise to a conflict of interest." (VERIFIED, H)
  - *Medical Professionalism*: "Physicians must maintain their clinical objectivity and professional independence in all interactions with industry." "Industry" expressly includes "commercial providers of services related to clinical practice". Conflicts include those defined in O. Reg. 114/94 ss.15–17. (VERIFIED, H)
  - *Association with Products or Services*: a physician's name or likeness must not be associated with advertising for commercial products or services other than their own medical services. This matters for platform marketing. (VERIFIED, H)
- **Nurse practitioners.** O. Reg. 799/93 (Nursing Act) para 26 makes "practising the profession while the member is in a conflict of interest" professional misconduct, but the regulation does not define it (VERIFIED, H). CNO's practice standards (cno.org was not reachable) supply the content. **[COUNSEL]**: confirm the CNO conflict standard on pharmacy and supplier benefits. The safe working assumption is that NPs are treated like physicians. (U)

### 2.4 Arrangements between a pharmacy and a non-pharmacy business

The core rule is O. Reg. 264/16 s.34. It is a conflict for an owner or designated manager "to do, or to cause or permit another person to do, directly or indirectly" any of:
1. refer a patient while receiving a benefit;
2. confer a benefit "by reason of the referral of a patient to a pharmacy associated with the owner or designated manager";
3. confer a benefit on a patient other than a fee adjustment or a nominal-value health item;
4. any arrangement that influences or encourages, **or appears to**, a prescriber to promote the pharmacy;
5. any arrangement that adversely influences, **or appears to**, professional judgment or ethical practice.

"Benefit" means any incentive or inducement of more than nominal value, direct or indirect, including rebate, credit or gift (s.33). The individual-pharmacist equivalents are in O. Reg. 130/17 s.6(a)–(e). (VERIFIED, H)

| Arrangement (pharmacy → platform unless noted) | Clause | Assessment | Confidence |
|---|---|---|---|
| **Per-prescription / per-patient fee** to the platform that sources the patients | s.34 para 2 (benefit by reason of referral); para 4 if the prescriber is linked | **Prohibited in substance, or very high risk.** It is volume-linked to referrals. | H (text); M (application) |
| **Revenue share / % of drug sales** | s.34 paras 2 and 5; O. Reg. 130/17 s.6(b), (e) | **Very high risk**: it scales with referrals and pressures judgment. | M |
| **"Marketing fee"** tied to patients delivered | s.34 para 2; s.29 advertising limits; FDR C.01.044 | **High risk** if tied to volume or referrals. A genuine flat-fee advertising service that complies with s.29 is lower risk. | M |
| **Fixed FMV technology / services fee** (software, patient portal, logistics, customer service), not tied to volume | No express permission. The analogy is the rent safe harbour, s.35(2) ("normal rent … same type of premises in the same geographical area") | **Defensible only if** the price is at independently supported FMV, the fee is fixed rather than per-Rx or percentage-based, the services are really delivered and needed, the pharmacy is free to use other vendors, and the pharmacy is not dependent on the platform for patient flow. Get a written valuation. **[COUNSEL]** | M/U |
| **Rent** (platform or clinic leases space to the pharmacy) | s.35(2) (pharmacy side); O. Reg. 114/94 s.16(b)/(c) (physician side: normal rent **and** not related to volume or referrals) | **Expressly permitted** at normal market rent that is not volume-linked. | H |
| **Minority equity** by the platform with pro-rata dividends | DPRA s.142; O. Reg. 264/16 s.33 (non-arm's length), s.35(1)(b) | Permitted by the DPRA if under 50% of each class. Referrals from a non-arm's-length person avoid conflict only if **"no direct benefit is received by the owner or designated manager"** and the relationship is **disclosed to the patient before services**. Whether pro-rata dividends to a referring shareholder are "by reason of the referral" is unresolved. **[COUNSEL]** | H (text); U (application) |
| **Platform discount to patients who fill at the aligned pharmacy**, funded by the pharmacy | s.34 para 3 ("cause or permit another person … indirectly") | **High risk.** The pharmacy itself may lower its own price, which is expressly allowed as "an adjustment in the fee". Cross-subsidised platform-fee discounts are not. | M |
| **Free delivery / free cold-chain shipping** | s.34 para 3; s.32 para 15 | Unclear whether free delivery is a "benefit of more than nominal value". It is common in practice. **[COUNSEL]** | U |
| **Data sharing** of prescription information to the platform | s.32 paras 11–12; PHIPA | Disclosure only under a written agreement for **de-identified** data, with the DM aware of it. Identifiable data needs PHIPA-compliant consent or authority. | H |
| **Agreement routing all programme patients to one pharmacy** | s.32 para 18; O. Reg. 130/17 Part I para 22; CPSO "Pharmacy selection" | **Prohibited** without the patient's written consent. Even with consent, it is at odds with CPSO and the programme's own patient-choice rule. | H |
| Manufacturer rebates to the pharmacy on **generic semaglutide** (now an interchangeable product) | DIDFA s.12.1; Reg. 935 s.2(3) | Rebates are prohibited. Only prompt-pay discounts, volume discounts and distribution service fees under a written agreement are allowed. | H |

### 2.5 Patient choice, steering, telepharmacy, mail-order and courier

- **Choice of pharmacy:**
  - O. Reg. 264/16 s.32 para 18 and O. Reg. 130/17 Part I para 22 (VERIFIED, H).
  - CPSO "Pharmacy selection" (VERIFIED, H).
  - DIDFA s.4(2): the patient has a right to request an interchangeable (generic) product, and the pharmacy must inform them of that right (s.4(3)) (VERIFIED, H).
- **Solicitation:** a pharmacy may solicit only if it discloses the purpose at the outset and stops on request (O. Reg. 264/16 s.32 para 17; O. Reg. 130/17 para 25) (VERIFIED, H).
- **Price advertising of Schedule I drugs** (all PDL drugs, including GLP-1s; O. Reg. 264/16 s.3(2)):
  - an advertised price must state how long it is available, plus quantity, strength, dosage and dispensing fee (s.29(2));
  - a Schedule I price may not be advertised unless enough other drug prices are included that the public is not drawn to the pharmacy "principally on the basis of the price of the drug in Schedule I" (s.29(3));
  - there may be no safety, effectiveness or indication claims (s.29(1)(f));
  - federally, see FDR C.01.044.
  - A "Wegovy $X at our partner pharmacy" campaign is therefore problematic. (VERIFIED, H)
- **Courier / mail delivery** is permitted, with conditions:
  - DPRA s.152(1): Schedule I drugs go by registered mail, or by a method that is "both traceable and auditable, with a receipt for the drug signed by the patient or the patient's agent" (VERIFIED, H).
  - The OCP *Community Pharmacy Accreditation Assessment Criteria* (Updated Oct 2026) requires processes so all delivered or mailed prescriptions are traceable and auditable, with a patient or agent signature unless there is a documented valid reason, plus confidentiality (VERIFIED, H).
  - The OCP *Delivery of Prescriptions* fact sheet (via search) adds that a pharmacy-employed courier cannot act as the patient's agent, and a locker cannot be an agent. Cold-chain drugs must ship in validated containers or temperature-controlled vehicles, with delay and excursion procedures. (M)
- **Cold chain:**
  - The OCP accreditation criteria require SOPs that keep the cold chain "throughout the time a product is received, stored, dispensed and delivered", staff training, temperature monitoring (min/max twice daily if manual), and excursion assessment by the DM (VERIFIED, H).
  - OCP's *Protecting the Cold Chain* guideline is referenced; its HTML was not reachable (M).
  - **Refrigerated drugs that are returned cannot be restocked or resold** (O. Reg. 264/16 s.32 para 19(i)). A refused or failed GLP-1 delivery is therefore a full write-off of drug cost (VERIFIED, H).
- **Telepharmacy:**
  - Ontario allows **remote dispensing locations** under a separate certificate of accreditation, where a technician dispenses under active remote pharmacist supervision (DPRA s.146(1.0.1), s.149(3); O. Reg. 264/16 remote-dispensing Part) (VERIFIED, H).
  - Virtual counselling is governed by the OCP *Virtual Care Policy* (v1.10, effective 2025-09-30, via search): private setting, and patient consent to virtual care (M).
- **Patients outside Ontario:** the OCP *Cross-Jurisdictional Pharmacy Services Policy* (Board-approved June 2022, via search) requires the registrant to meet Ontario standards plus those of the patient's jurisdiction. Shipping to other provinces generally requires compliance with, and often licensure in, the receiving province (M). **[COUNSEL]** if the programme serves patients outside Ontario.
- **Physician dispensing as an alternative to a pharmacy:** this is not an income route. O. Reg. 114/94 s.16(d) bars selling drugs at a profit except in limited circumstances, and the CPSO dispensing obligations require pharmacist-equivalent dispensing standards (VERIFIED, H).

---

## 3. How an Ontario pharmacy earns on a private-pay prescription (Q2)

### 3.1 Components and legal constraints

Patient price = **drug acquisition cost** + **markup** + **dispensing fee** (plus any separately disclosed service or delivery charge).

| Component | Rule | Label / confidence |
|---|---|---|
| Dispensing fee | The pharmacy must set and file **one** "usual and customary" (U&C) dispensing fee with the OCP Registrar and post it (DIDFA s.6). It may not charge more than its U&C fee (s.7(1)) unless it explains the excess before dispensing and the excess is not misconduct (Reg. 935 s.5). **So the pharmacy cannot charge programme patients a special, higher dispensing fee as a matter of course.** | VERIFIED, H |
| Markup on cash / private pay | No statutory cap on cash or private pay. The constraints are "excessive" fee or amount misconduct (O. Reg. 264/16 s.32 para 15; O. Reg. 130/17 para 21), charging more than an advertised total (s.32 para 16), and competition. For **interchangeable** products (e.g., generic semaglutide), the pharmacy may not charge more than the lowest amount for the interchangeable products in its inventory, unless the patient asks for a specific product or there is "no sub" (DIDFA s.7(2)–(3)). | VERIFIED, H |
| Receipt | The pharmacy must give particulars of the amount charged (DIDFA s.10). | VERIFIED, H |
| Fill quantity | The pharmacy must dispense the **entire prescribed quantity at one time** unless the person presenting the prescription authorises smaller quantities **in writing** (DIDFA s.9(1)). Monthly fills of a 3-month prescription therefore need written patient authorisation. Each extra fill earns an extra dispensing fee and will be scrutinised. | VERIFIED, H |
| Manufacturer rebates | Prohibited for interchangeable products (DIDFA s.12.1). Permitted "ordinary commercial terms" are prompt-pay discounts, volume discounts and distribution service fees under a written agreement (Reg. 935 s.2(3)). Brand single-source products (Wegovy, Mounjaro, Saxenda) are not caught by s.12.1. Whether manufacturer patient-support programmes pay pharmacies anything is UNKNOWN. | VERIFIED, H (text) |

### 3.2 ODB reference schedule (BENCHMARK; VERIFIED in O. Reg. 201/96, consolidated from 2026-07-01, last amended O. Reg. 97/26)

- **Dispensing fee (s.13(4)):**
  - $8.83 for a standard pharmacy;
  - $9.93, $12.14 or $13.25 for rural or remote pharmacies, depending on rurality index and the distance to the nearest other pharmacy. (H)
- **Markup on the drug benefit price (s.13(2), O. Reg. 157/24, in force April 2024)**, by total drug cost:

  | Total drug cost | Markup |
  |---|---|
  | under $100 | 8.5% |
  | $100–<$500 | 8% |
  | $500–<$1,000 | 7% |
  | $1,000–<$2,000 | 6% |
  | $2,000–<$4,000 | 5.5% |
  | $4,000 and over | 5% |

  (H)
- **ODB co-payment cap:** $2, or the U&C fee if lower (s.20.1), for most recipients (H).
- **Relevance:** ODB does not fund GLP-1s for weight management (see §4.2). These numbers are only a public-plan floor and comparison for private-pay pricing.

### 3.3 Private-pay and private-insurer fees and markups

- **Typical Ontario cash dispensing fees and markups: UNKNOWN (not verified this session).**
  - Reasons: the insurer, chain and pharmacy-association sites were blocked, and the search budget ran out.
  - Indirect evidence: advertised Costco cash prices for Mounjaro are reported as "dispensing fee included" (§4). Aggregators report that other chains charge about $55 per month more than Costco for the same dose (U).
- **Private insurer caps on dispensing fees and markups: UNKNOWN.**
  - Many Canadian carriers apply "reasonable and customary" fee and markup limits and prior-authorisation rules. The actual Ontario values must be sourced from the carriers (Sun Life, Manulife, Canada Life, Green Shield, Desjardins, etc.) or from a Telus Health / Express Scripts Canada adjudication contract. (U)
- **Modelling approach used in §5:** markup 5–15% on acquisition cost and dispensing fee $8.83–$14 (**ASSUMPTION**, anchored to the ODB benchmark). These inputs reproduce the advertised retail bands in §4.

### 3.4 Labour

- **Ontario pharmacist and pharmacy technician wages: UNKNOWN in this session.** Job Bank (jobbank.gc.ca) was unreachable.
- For modelling only (**ASSUMPTION**, loaded cost including benefits and payroll taxes): pharmacist **$55–$75/h**; registered pharmacy technician **$25–$35/h**. Replace with Job Bank Ontario median and high wages for NOC 31120 (pharmacists) and 32124 (pharmacy technical assistants and technicians), plus a 15–25% load.
- **Time per fill (ASSUMPTION):** about 5–10 min pharmacist (clinical check, counselling, virtual counselling for remote patients) and 5–10 min technician (entry, adjudication, packing, cold-chain documentation) for a refill. A **new start** (injection teaching, titration counselling) could plausibly take 15–30 min of pharmacist time. That is not modelled in the refill waterfall.

### 3.5 Payment processing

- **UNKNOWN (not verified this session).** Modelled as **1.5–3.0% of the transaction plus $0.10–$0.30** (**ASSUMPTION**, covering a range from negotiated interchange-plus pricing to blended online-processor list pricing).
- **Merchant of record should be the pharmacy.** If the platform collects drug payments, it should do so only as the pharmacy's disclosed payment agent. Those funds are **pass-through, not platform revenue** (DIDFA s.10 receipt; O. Reg. 264/16 s.32 para 14 on false or misleading accounts). **[COUNSEL]**

### 3.6 Cold-chain packaging and delivery

- **OCP expectations:** VERIFIED (see §2.5): traceable and auditable delivery with a signature, validated containers or temperature-controlled transport, excursion procedures, trained staff, and DM accountability.
- **Ontario public cost benchmarks for refrigerated pharmacy courier: UNKNOWN.** No public rate data was found.
- **Modelled (ASSUMPTION):**
  - insulated shipper with gel packs and temperature indicator: **$5–$15 per shipment**;
  - signature-on-delivery courier: **$10–$30 per delivery** (the low end is intra-city route delivery, the high end ad-hoc or regional);
  - pickup in store: about $1–$2 for a bag and cold pack.
- Replace with courier quotes (same-day GTA, next-day province-wide) and packaging supplier quotes.

---

## 4. Prices and coverage (Q3)

### 4.1 Advertised and benchmark prices (CAD, Canada/Ontario, 2025–2026)

All retail figures are **ADVERTISED** via price aggregators and telehealth sites, not checked against a live pharmacy quote. Pharmacy-level verification (for example, Costco's Ontario price lookup) was blocked in this session.

| Product / dose | Figure | Date | Includes dispensing fee? | Source (label) | Conf. |
|---|---|---|---|---|---|
| **Generic semaglutide (Ozempic-interchangeable)**: Apo-Semaglutide 0.68 mg/mL 2 mg pen; Apo-Semaglutide and Dr. Reddy's 1.34 mg/mL 2 mg or 4 mg pens | **$78.1410 per pen** (ODB drug benefit price) | Effective 2026-06-30 | No (DBP excludes markup and fee) | ODB Summary of Changes, June 2026 (**VERIFIED BENCHMARK**) | H |
| Generic semaglutide, retail cash | ~$88–$99 per month (Costco); ~$110–$125 per month at pharmacies generally | mid-2026 | Not stated | Aggregators and B&P Monitor headline, via search (**ADVERTISED**) | U |
| Apotex statement | Generic "approximately one-third the price" of brand Ozempic | 2026-05 | n/a | Apotex / BNN Bloomberg, via search | M |
| Brand Ozempic | $200–$450 per month (range cited by a telehealth platform); ODB brand DBP reportedly $227.94; Apotex-cited brand wholesale $240.48 | 2026 | Varies | BNN Bloomberg (citing Felix); aggregators, via search (**ADVERTISED / BENCHMARK, unverified**) | U |
| Brand Ozempic, manufacturer response | Novo said some Canadians would get Ozempic "aligned" with generic pricing via its savings card | 2026-05-26 | n/a | News, via search | M/U |
| **Wegovy** (maintenance 2.4 mg implied) | $431.12 (Costco) to $492.80 per month | June 2026 | Not stated | teletest.ca, via search (**ADVERTISED**) | U |
| Wegovy | "$297–$460.65 at 3 pharmacies" | Updated 2026-11-11 | Not stated | glp1prices.ca, via search (**ADVERTISED**) | U |
| Wegovy | Reported Novo cash price of $349 per month | March 2026 | Not stated | glp1prices.ca, via search. **Not confirmed with Novo.** | U |
| Wegovy by dose | **UNKNOWN**. No dose-level Canadian price found. | | | | U |
| **Sevmia** (Apotex generic Wegovy) | Price **UNKNOWN** (not published). Health Canada approval 2026-06-29. ODB OFI submission DIN 02569582 listed in the July 2026 report. | 2026 | | Health Canada (via search); ODB OFI report (**VERIFIED** listing) | H (listing); U (price) |
| **Mounjaro** (Costco) | 2.5/5 mg **$325.67**; 7.5/10 mg **$454.00**; 12.5/15 mg **$582.00** per month | June 2026 (phone checks) | Not stated | teletest.ca, via search (**ADVERTISED**) | U |
| Mounjaro (Costco) | ~$330 / $458 / $586 (same dose bands) | Aug 2026 audit | **Yes, stated as including the dispensing fee** | semaglutidecanada.com, via search (**ADVERTISED**) | U |
| Mounjaro (other chains) | About $55 per month above Costco at 10 mg (Alberta data) | 2026 | n/a | Aggregator, via search | U |
| **Saxenda** (3 mg/day; a 5-pen box is about 30 days) | $450–$600 per month | 2026 | Not stated | teletest.ca, via search (**ADVERTISED**) | U |
| **Generic liraglutide (Canada)** | **UNKNOWN / not found.** No Canadian generic listing in the ODB summaries checked (2025-03, -04, -08, -09; 2026-01, -04, -06; OFI and multi-source reports for May, July and Sept 2026). The US generic (Victoza reference) was approved December 2024. | | | ODB files (**VERIFIED** absence in the files checked) | M |
| Other generic semaglutide entrants | Sandoz semaglutide approved by Health Canada 2026-09-18 (launch date UNKNOWN). Aspen Pharmacare semaglutide submissions appear in the ODB multi-source report for Sept 2026. One aggregator claims a Dr. Reddy's recall on 2026-08-26 (**unverified**). | 2026 | | Sandoz/newswire (via search); ODB report (**VERIFIED** submission listing) | H/M/U |

**Approval timeline (M, via Health Canada news releases found through search):**
- first generic semaglutide (Dr. Reddy's): 2026-04-28;
- Apotex (Ozempic generic): 2026-05-01;
- product reached pharmacies about 2026-05-20 (BNN Bloomberg);
- Sevmia, the first generic for weight management: 2026-06-29;
- Sandoz: 2026-09-18.
- pCPA generic pricing: about 50% of brand with two generics, falling to about 35% with three or more (BNN Bloomberg, M).

**Supply per pen (U, analyst inference from standard labelling; verify against the product monographs):** Ozempic, generic semaglutide, Wegovy and Mounjaro multi-dose pens each deliver four weekly doses, so one pen is roughly one 28-day fill.

### 4.2 Coverage

- **ODB:**
  - Brand Ozempic and the generic semaglutide products are listed as **Limited Use** (LU) benefits (VERIFIED, H). The LU criteria are for type 2 diabetes. The exact LU codes were not verified (M).
  - Ontario does **not** fund GLP-1s for obesity or weight management alone (via search, M).
  - The ODB status of Wegovy, Saxenda and Mounjaro was not verified in this session (U). The working assumption is not funded for weight management.
- **Private plans:** the share of Ontario plan members with GLP-1 coverage for weight management is **UNKNOWN**.
  - Trade press (Benefits and Pensions Monitor, Insurance Business, 2026) reports plan sponsors weighing coverage, generic substitution and cost pressure. Canada Life commentary notes trade-offs, and currently available generics are diabetes-indicated (M/U).
  - The model should assume **mostly cash pay** for weight-management indications, with an insured minority subject to prior authorisation and rejections.

---

## 5. ILLUSTRATIVE per-fill waterfall: one 28-day private-pay GLP-1 fill at an Ontario pharmacy

> **Everything in this section is illustrative.** Only the generic acquisition benchmark ($78.14 ODB DBP) and the ODB fee and markup schedule are verified. The brand acquisition cost is **UNKNOWN**. $400 is an ASSUMPTION chosen so that modelled retail ($429–$474) falls inside the advertised Wegovy and Mounjaro band of about $325–$590. All cost lines are ASSUMPTIONS (see §3). Results are **pharmacy-level contribution before fixed overhead** (rent, software, insurance, OCP fees, minimum staffing, inventory carrying cost) **and before tax**.

### 5.1 Inputs

| Line | Adverse | Mid | Favourable | Label |
|---|---|---|---|---|
| Brand acquisition cost C (per pen) | $400 | $400 | $400 | ASSUMPTION (true value UNKNOWN) |
| Generic semaglutide acquisition cost C | $78.14 | $78.14 | $78.14 | BENCHMARK (ODB DBP; actual may be lower with lawful volume or prompt-pay discounts) |
| Markup %, brand | 5% | 8% | 15% | ASSUMPTION (ODB: 8% for $100–<$500) |
| Markup %, generic | 8.5% | 10% | 15% | ASSUMPTION (ODB: 8.5% under $100) |
| Dispensing fee (the pharmacy's single U&C fee) | $8.83 | $11.00 | $14.00 | ASSUMPTION (ODB $8.83 = BENCHMARK) |
| Pharmacist time × loaded rate | 10 min × $75/h | 7.5 min × $65/h | 5 min × $55/h | ASSUMPTION |
| Technician time × loaded rate | 10 min × $35/h | 7.5 min × $30/h | 5 min × $25/h | ASSUMPTION |
| Cold-chain packaging (courier) / pickup bag | $15 / $2 | $9 / $1 | $5 / $1 | ASSUMPTION |
| Signature courier delivery | $30 | $18 | $10 | ASSUMPTION |
| Card processing | 3.0% + $0.30 | 2.2% + $0.20 | 1.5% + $0.10 | ASSUMPTION |
| Failed collections / chargebacks (% of price) | 2.0% | 0.75% | 0.25% | ASSUMPTION |
| Failed delivery or spoilage: probability × (C + pack + courier), non-returnable per O. Reg. 264/16 s.32 para 19 | 2% | 1% | 0.25% (pickup: ÷4) | ASSUMPTION (rule VERIFIED) |
| Rejected-claim rework (blended; zero for pure cash) | $3 | $1 | $0 | ASSUMPTION |

### 5.2 Results: brand GLP-1 (Wegovy or Mounjaro class), couriered cold chain

| Step | Adverse | Mid | Favourable |
|---|---|---|---|
| **Retail price paid by patient** (gross drug sale) | $428.83 | $443.00 | $474.00 |
| − Drug acquisition cost (pass-through to wholesaler/manufacturer) | −$400.00 | −$400.00 | −$400.00 |
| = Markup | $20.00 | $32.00 | $60.00 |
| + Dispensing fee | $8.83 | $11.00 | $14.00 |
| **= Pharmacy gross margin** | **$28.83** | **$43.00** | **$74.00** |
| − Pharmacist + technician time | −$18.33 | −$11.88 | −$6.67 |
| − Cold-chain packaging | −$15.00 | −$9.00 | −$5.00 |
| − Signature courier | −$30.00 | −$18.00 | −$10.00 |
| − Card fees | −$13.16 | −$9.95 | −$7.21 |
| − Failed collections | −$8.58 | −$3.32 | −$1.18 |
| − Failed delivery / spoilage (expected) | −$8.90 | −$4.27 | −$1.04 |
| − Rejected-claim rework | −$3.00 | −$1.00 | $0.00 |
| **= Retained contribution per fill (pre-overhead, pre-tax)** | **−$68.14** | **−$14.41** | **+$42.90** |

### 5.3 Summary of all cases (retained contribution per 28-day fill)

| Case | Retail | Gross margin | Adverse | Mid | Favourable |
|---|---|---|---|---|---|
| Brand, couriered | $429–$474 | $29–$74 | **−$68** | **−$14** | **+$43** |
| Brand, in-store pickup | $429–$474 | $29–$74 | **−$18** | **+$15** | **+$58** |
| Generic semaglutide, couriered | $94–$104 | $15–$26 | **−$58** | **−$25** | **+$2** |
| Generic semaglutide, pickup | $94–$104 | $15–$26 | **−$13** | **+$2** | **+$16** |
| Brand, 84-day fill (3 pens, one fee, one delivery; needs a 3-pen prescription), couriered, **per 28 days** | $1,269–$1,394 per fill | | **−$30** | **+$5** | **+$48** |
| Generic, 84-day fill, couriered, **per 28 days** | $263–$284 per fill | | **−$20** | **−$6** | **+$7** |

**Readings**
- **The dispensing fee and delivery cost decide the result.** The markup in dollars is small even on a $400 pen. Courier plus packaging ($15–$45) can consume the whole gross margin.
- **The move to generics makes this worse.** On generic semaglutide (and, once launched, Sevmia), gross margin collapses to roughly the dispensing fee plus about $7–$12 of markup, while labour and cold-chain costs stay the same. Couriered generic fills lose money unless:
  - (a) the patient picks up;
  - (b) a separately disclosed delivery fee is charged (**[COUNSEL]**: it must not be "excessive", and must be disclosed in advertised totals); or
  - (c) multi-month fills spread the fixed cost. Multi-month fills need an appropriate prescription; DIDFA s.9 governs fill splitting.
- **Separately charged delivery fee (sensitivity).** Each $10 charged to the patient lifts every couriered case by about $10. This would be pharmacy revenue, not pass-through.
- **New starts.** Extra pharmacist time for injection teaching and titration (about +$10–$30, ASSUMPTION) makes first fills negative in most cases.
- **Inventory risk.** Holding $400 brand pens with titration across six or more dose strengths ties up working capital. Refrigerated stock cannot be returned once dispensed, and supply disruptions and dose changes create dead stock (UNKNOWN cost, not modelled).

### 5.4 Keeping the money flows separate (as the plan requires)

| Bucket | What it is | Whose revenue | Illustrative per brand fill |
|---|---|---|---|
| **Gross drug sales** | Retail price × fills | Pharmacy's | $429–$474 |
| **Pass-through funds** | Drug acquisition cost (to wholesaler/manufacturer). Also any drug money the platform collects as the pharmacy's payment agent, and any insurer payments it relays. | Not anyone's margin | ~$400 (≈ 85–93% of gross sales) |
| **Pharmacy gross margin** | Markup + dispensing fee (+ any disclosed delivery fee) | Pharmacy's | $29–$74 |
| **Pharmacy retained contribution** | Gross margin − variable costs (§5.2) | Pharmacy's, before overhead and tax | −$68 to +$58 |
| **Platform revenue** | Patient programme or membership fees; FMV fixed service fees from the pharmacy (if lawful); rent at market | Platform's | Independent of fills, by design |
| **Platform retained income from the pharmacy** | ≤49% × pharmacy **net** profit (after overhead and tax), as pro-rata dividends | Platform's | ≈ ≤49% of (contribution − overhead per fill). Plausibly **$0–$20 in favourable brand-pickup cases; ≤$0 for couriered generics.** |

**Expected value per clinical patient-month** = (share of patients who **choose** to fill at the aligned pharmacy, *p*) × (fills per month) × (contribution − overhead per fill) × (platform equity %).
- *p* is **UNKNOWN** and must not be assumed to be 100%.
- CPSO and O. Reg. 264/16 s.32 para 18 require real choice. Scenario-test *p* = 10–50% (ASSUMPTION) and use patients' own pharmacy preferences from intake data.

---

## 6. Lawful income routes, ranked by robustness (analyst view; all **[COUNSEL]**)

1. **Patient-paid programme fees that do not depend on where the patient fills** (clinical-adjacent coaching, body-composition testing, software). This is independent of pharmacy economics. It needs physician and NP compensation that complies with O. Reg. 114/94 s.15(c)/s.16 and CNO standards, and advertising that complies with CPSO and FDR. **Most robust.**
2. **Minority equity (<50% of each class, minority of the board) in a pharmacist-controlled pharmacy**, with pro-rata dividends only. Requirements:
   - no shareholder-agreement control over professional matters;
   - disclosure of the relationship to patients before services (s.35(1)(b));
   - no physician or NP equity anywhere in the chain;
   - a neutral pharmacy-choice step in the platform's flow.
   - Economic upside is small (§5).
3. **Fixed FMV fees for real services** (technology licence, logistics, call centre), paid by the pharmacy. Requirements: independent valuation, flat fees, no per-Rx or percentage terms, a non-exclusive arrangement, and documentation. **Moderate risk.**
4. **Market-rent lease** (s.35(2); O. Reg. 114/94 s.16(b)/(c): normal rent, not volume-linked). **Low risk, low value.**
5. **Not recommended / likely prohibited:**
   - per-prescription or per-patient fees;
   - percentage revenue shares;
   - referral-linked "marketing" fees;
   - pharmacy-funded discounts on platform fees;
   - exclusive routing agreements;
   - any payment that flows, directly or indirectly, from the pharmacy to the prescribing practice;
   - physician or NP equity in the pharmacy or in a platform that takes pharmacy income.

---

## 7. Questions for counsel

1. Are pro-rata dividends to a minority shareholder that is also the patients' referral source a "benefit by reason of the referral" (O. Reg. 264/16 s.34 para 2)? What does "no direct benefit is received by the owner or designated manager" mean in s.35(1)(b)?
2. Do fixed FMV technology or services fees from the pharmacy to the platform fall outside s.34? What evidence of FMV would OCP expect?
3. Which shareholder-agreement terms (vetoes, debt covenants, management agreements, change-of-control rights) would make the platform "non-arm's length", or breach s.34 para 5 or the spirit of DPRA s.142?
4. Is the platform itself a "supplier" under O. Reg. 114/94 s.15? If so, how must physician and NP compensation be structured (written contract per s.15(c))? Can any physician or NP hold platform equity if the platform has pharmacy income?
5. What do the CNO conflict-of-interest standards require of NPs on pharmacy relationships and supplier benefits?
6. Is free delivery or free cold-chain shipping a "benefit" under s.34 para 3? Is a separately charged delivery fee permitted, and how must it appear in advertised totals (s.32 para 16; s.29(2))?
7. Is acquiring a pre-1954 grandfathered pharmacy corporation (s.142(4)) available and appropriate? Note that the director-majority test still applies.
8. For patients outside Ontario: what does the receiving province require for licensure and shipping (OCP Cross-Jurisdictional Policy)?
9. Payment flows: what agency structure is needed if the platform collects drug payments as the pharmacy's agent? What are the PHIPA and s.32 para 11 limits on data the pharmacy shares with the platform?

---

## 8. Sources

All were accessed 2026-11-18. "Direct" means fetched and read in this session. "Via search" means only a search-engine summary was seen; the page itself was blocked.

**Primary: legislation (direct, H)**
1. *Drug and Pharmacies Regulation Act*, R.S.O. 1990, c. H.4: ss.1, 139–149, 152. https://www.ontario.ca/laws/statute/90h04. King's Printer for Ontario (e-Laws), consolidation from 2026-01-01, last amendment 2025 c.11 Sched. 3.
2. O. Reg. 264/16 (General, DPRA): ss.3, 28–35 and the remote-dispensing Part. https://www.ontario.ca/laws/regulation/160264. e-Laws, consolidation from 2026-01-01, last amendment O. Reg. 344/25.
3. O. Reg. 130/17 (*Professional Misconduct and Conflict of Interest*, Pharmacy Act, 1991). https://www.ontario.ca/laws/regulation/170130. e-Laws, consolidation from 2017-05-05.
4. O. Reg. 114/94 (General, Medicine Act, 1991): Part IV ss.15–17. https://www.ontario.ca/laws/regulation/940114. e-Laws, consolidation from 2025-04-01, last amendment O. Reg. 221/24.
5. *Drug Interchangeability and Dispensing Fee Act*, R.S.O. 1990, c. P.23: ss.4–12.1. https://www.ontario.ca/laws/statute/90p23. e-Laws, consolidation from 2016-06-03.
6. R.R.O. 1990, Reg. 935 (General, DIDFA): ss.2(3), 5. https://www.ontario.ca/laws/regulation/900935. e-Laws, consolidation from 2024-03-07.
7. O. Reg. 201/96 (General, Ontario Drug Benefit Act): ss.13, 20.1. https://www.ontario.ca/laws/regulation/960201. e-Laws, consolidation from 2026-07-01, last amendment O. Reg. 97/26.
8. O. Reg. 799/93 (Professional Misconduct, Nursing Act, 1991): para 26. https://www.ontario.ca/laws/regulation/930799. e-Laws.
9. *Food and Drug Regulations*, C.R.C., c. 870, s. C.01.044. https://laws-lois.justice.gc.ca/eng/regulations/C.R.C.,_c._870/FullText.html. Justice Canada.

**Primary: Ontario Ministry of Health / ODB (direct, H)**
10. ODB Formulary/CDI Edition 43, *Summary of Changes – June 2026* (effective 2026-06-30). https://www.ontario.ca/files/2026-06/moh-ontario-drug-benefit-odb-formulary-edition-43-summary-en-2026-06-23.pdf
11. *Complete Streamlined Multi-Source / OFI Report – July 2026* (Sevmia DIN 02569582), posted 2026-08-04. https://www.ontario.ca/files/2026-08/moh-complete-streamlined-multi-source-off-formulary-interchangeability-ofi-report-july-en-2026-08-04.pdf
12. *Multi-Source Submissions Report – May 2026*, posted 2026-06-03. https://www.ontario.ca/files/2026-06/moh-complete-streamlined-multi-source-submissions-future-formulary-listing-odb-report-may-en-2026-06-03.pdf
13. *Multi-Source Submissions Report – September 2026* (Aspen semaglutide), posted 2026-10-07. https://www.ontario.ca/files/2026-10/moh-complete-streamlined-multi-source-submissions-future-formulary-listing-odb-report-september-en-2026-10-07.pdf
14. ODB Formulary Edition 43 (PDF), posted 2026-09-03. https://www.ontario.ca/files/2026-09/moh-formulary-edition-43-en-2026-09-03.pdf
15. ODB Summaries of Changes checked for liraglutide (none found): 2025-03-26, 2025-04-28, 2025-08-26, 2025-09-24, 2026-01-23, 2026-04-23. Files under https://www.ontario.ca/files/…
16. *Ontario public drug programs: Executive Officer communications* (2026 list; no GLP-1-specific notice). https://www.ontario.ca/page/ontario-public-drug-programs-executive-officer-communications

**Primary: regulators (direct unless noted)**
17. CPSO, *Obligations in Practice: Prescribing Drugs* ("Pharmacy selection"), page stamp 2026-11-17, H. https://www.cpso.on.ca/physicians-physician-assistants/professional-resources/professional-obligations/clinical-care/Obligations-prescribing-drugs
18. CPSO, *Medical Professionalism* obligations (conflicts, industry definition), H. https://www.cpso.on.ca/physicians-physician-assistants/professional-resources/professional-obligations/medical-professionalism
19. CPSO, *Obligations in Practice: Industry Relationships*, H. https://www.cpso.on.ca/physicians-physician-assistants/professional-resources/professional-obligations/medical-professionalism/Obligations-industry-relationships
20. CPSO, *Obligations in Practice: Association with Products or Services*, H. https://www.cpso.on.ca/physicians-physician-assistants/professional-resources/professional-obligations/practice-management/Obligations-association-with-products-or-services
21. CPSO, *Clinical Care* obligations (prescribing and dispensing), H. https://www.cpso.on.ca/Physicians/Policies-Guidance/Policies/Prescribing-Drugs (redirects to the Professional Obligations page)
22. OCP, *Community Pharmacy Accreditation Assessment Criteria*, "Updated October 2026", H. https://www.ocpinfo.com/wp-content/uploads/2025/05/community-pharmacy-accreditation-assessment-criteria.pdf
23. OCP, *Standards of Operation for Pharmacies*, draft for consultation (June 2026), M (draft). https://www.ocpinfo.com/wp-content/uploads/2026/06/Standards-of-Operation-for-Pharmacies_revisions-for-consultation.pdf
24. OCP, Board meeting materials, 20 Nov 2025 (As of Right; ss.142/144 carve-out), H. https://www.ocpinfo.com/wp-content/uploads/2025/11/november-20-2025-board-meeting-agenda-materials.pdf
25. OCP, *Delivery of Prescriptions* fact sheet (via search), M. https://www.ocpinfo.com/practice-education/practice-tools/fact-sheets/delivery-prescriptions/
26. OCP, *Protecting the Cold Chain* guideline (via search), M. https://www.ocpinfo.com/regulations-standards/practice-policies-guidelines/cold-chain/
27. OCP, *Virtual Care Policy* v1.10, effective 2025-09-30 (via search), M. https://www.ocpinfo.com/wp-content/uploads/2021/03/Virtual-Care-Policy.pdf
28. OCP, *Cross-Jurisdictional Pharmacy Services Policy*, June 2022 (via search), M. https://www.ocpinfo.com/wp-content/uploads/2021/03/Cross-Jurisdictional-Pharmacy-Services-Policy.pdf
29. OCP, *Close Up on Complaints: Avoiding Actual or Perceived Conflict of Interest in Business Dealings*, 2017-05-01 (via search), M. https://ocpinfo.com/ocp-resources/close-up-on-complaints-avoiding-actual-or-percieved-conflict-of-interest-in-business-dealings/
30. OCP, *Code of Ethics*, Nov 2022 (via search), M. https://ocpinfo.com/ocp-resources/code-of-ethics/

**Health Canada and manufacturers (via search, M)**
31. Health Canada, "Canada becomes the first G7 country to approve a generic version of semaglutide", 2026-04-28. https://www.canada.ca/en/health-canada/news/2026/04/canada-becomes-the-first-g7-country-to-approve-a-generic-version-of-semaglutide.html
32. Health Canada, "Canada approves second generic semaglutide…", May 2026. https://www.canada.ca/en/health-canada/news/2026/05/canada-approves-second-generic-semaglutide-the-first-g7-country-to-do-so.html
33. Health Canada, "Canada approves first generic semaglutide for weight loss", June 2026. https://www.canada.ca/en/health-canada/news/2026/06/canada-approves-first-generic-semaglutide-for-weight-loss.html
34. Apotex IR, 2026-05-01. https://investors.apotex.com/2026-05-01-Apotex-becomes-the-first-Canadian-based-pharmaceutical-company-to-receive-Health-Canada-approval-for-a-generic-equivalent-of-Ozempic-R
35. Sandoz Canada (Newswire), approval of Sandoz Semaglutide, 2026-09-18. https://www.newswire.ca/news-releases/sandoz-canada-receives-health-canada-regulatory-approval-for-pr-sandoz-r-semaglutide-a-generic-version-of-pr-ozempic-r--885564869.html

**News and trade press (via search, M/U)**
36. BNN Bloomberg (Canadian Press), "Generic semaglutide to hit Canadian pharmacies this week at a fraction of the cost of Ozempic", 2026-05-20. https://www.bnnbloomberg.ca/business/2026/05/20/generic-semaglutide-to-hit-canadian-pharmacies-this-week-at-a-fraction-of-the-cost-of-ozempic/
37. CNBC, "Healthy Returns: First Ozempic generics in Canada…", 2026-05-07. https://www.cnbc.com/2026/05/07/healthy-returns-novo-nordisk-faces-ozempic-generics-in-canada-.html
38. Benefits and Pensions Monitor, GLP-1 generics and plan-sponsor coverage articles, 2026. https://www.benefitsandpensionsmonitor.com/benefits/pharma/plan-sponsors-weigh-glp-1-generics-amid-supply-cost-gaps/393967 and https://www.benefitsandpensionsmonitor.com/benefits/pharma/a-40-obesity-drug-could-soon-land-in-your-benefits-plan/393498
39. Insurance Business Canada, "GLP-1 cost surge puts pressure on Canadian drug plans", 2026. https://www.insurancebusinessmag.com/ca/news/breaking-news/glp1-cost-surge-puts-pressure-on-canadian-drug-plans-report-571024.aspx

**Price aggregators (ADVERTISED; via search, U)**
40. teletest.ca: Wegovy (June 2026), Mounjaro (June 2026), Saxenda (2026). https://teletest.ca/cost/drug/wegovy/ ; https://teletest.ca/cost/drug/mounjaro/ ; https://teletest.ca/cost/drug/saxenda/
41. glp1prices.ca: Wegovy (updated 2026-11-11); "Novo Nordisk cuts Wegovy cash price to $349" (2026); Ozempic Ontario. https://glp1prices.ca/guides/wegovy-cost-canada ; https://glp1prices.ca/glp1-news/novo-nordisk-cuts-wegovy-cash-price-349-monthly-canada-2026 ; https://glp1prices.ca/drugs/ozempic/ontario
42. semaglutidecanada.com: Mounjaro Costco audit (Aug 2026); generic semaglutide pricing. https://www.semaglutidecanada.com/mounjaro/costco/ ; https://www.semaglutidecanada.com/semaglutide/generic/

**Blocked or unavailable this session (to complete in a follow-up):** Job Bank wages (jobbank.gc.ca); Costco Pharmacy price lookup; insurer dispensing-fee and markup caps; card-processor list pricing; courier and cold-chain rate cards; CNO conflict-of-interest standard; OCP HTML pages; product monographs (storage and pen supply).
