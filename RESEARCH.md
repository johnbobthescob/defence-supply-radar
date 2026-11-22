# Henderson Defence Supply-Chain Radar — research

Research date: **Sunday 22 November 2026, Australia/Perth (AWST, UTC+08:00)**.

Purpose: help Henderson marine engineering SMEs identify relevant Defence supply-chain work, distinguish an actionable procurement from a published pipeline or an inference, understand eligibility and timing, and reach the official application route. Free data and free tooling are constraints. This document records research, not a claim that any sample is currently open for bids.

## 1. Findings and feasibility

1. **A small, partly curated v1 is feasible.** The strongest automated input is the Department of Finance's public AusTender OCDS **contract-notice** API. Saved successful responses establish keyless access, JSON release packages, a data licence and working pagination. They do not establish an API for approaches to market (ATMs) or annual procurement plans (APPs).
2. **Contract notices are awarded-work intelligence.** An active contract, an open procurement method in a historical record, or a future contract end date is not a current invitation to bid. Keep this material as context; do not fill the open-opportunities list with it.
3. **Public AIC plans provide useful supply-chain scope and routes to primes.** The four saved PDFs cover RMP-West, Hunter, Austal SSA/MSTS and LM2500 support. They mix existing supply arrangements, conditional future scope and general engagement. None supplies evidence sufficient to confirm an open work package on the research date.
4. **Access and reuse are different questions.** The OCDS date-query packages declare CC BY 3.0 AU. Defence-hosted documents, ASA pages and WA material must not inherit that licence. Commercial reuse of AIC text remains unverified; BAE's sample carries a proprietary marking.
5. **The gap beyond ICN is narrow and must be tested.** ICN already offers supplier profiles, capability-related notifications, work-package discovery and EOIs. A Henderson-specific evidence review, consistent status labels, explicit readiness gaps and a concise cross-source briefing could save time. Merely collecting links or matching keywords would duplicate existing services.
6. **Comprehensive automated open-tender coverage is not demonstrated.** AusTender web/help/RSS requests were blocked in this environment; official reports exist, but their current export schemas and reuse conditions were not verified. A v1 must disclose this gap and allow zero confirmed-open results.

## 2. Evidence and access method

The original brief and `/tmp/defence-radar-logs/RESUME-AFTER-QUOTA.md` were read first. Existing evidence in `data/raw/2026-11-22/` was reused: all four AIC text extractions, their PDF metadata, the AIC index, ASA industry HTML, four OCDS responses, and saved robots/blocked-response bodies and metadata. Existing raw files were not re-downloaded or altered.

New browsing was limited to missing official documentation, rights statements, competitor descriptions and the ICN project linked inside Austal's saved PDF. Government sources and the first-party AusTender, Creative Commons and ICN sites were used. The WA directory was considered qualitatively only; no company lead list or directory dataset was downloaded. No procurement registration, enquiry, application or other message was sent.

Evidence levels used below:

- **Saved HTTP evidence:** `.meta.json` records an exact URL, response status and server date; adjacent `.body`, `.pdf` or `.txt` supplies content. Server `Last-Modified` is not necessarily a publication date. The old metadata lacks a separate client `fetched_at` field, so its HTTP `Date` is the available timing evidence.
- **Official documentation:** a first-party page was consulted through the browser research tool on 22 November 2026. The tool can use indexed content; this is not a fresh direct HTTP probe or an assurance of present procurement status. No local raw copy is claimed for these supplemental pages.
- **Unverified:** an API, export format, licence, cadence, deadline or condition was not established. Absence from this investigation is not proof that it does not exist.
- **Recommendation/inference:** a product policy proposed here, distinguished from a publisher's rule.

### Source register

All access notes are dated **22 November 2026**. Exact sampled API/PDF URLs and blocked endpoints follow the table. A proposed polling interval is an operator choice, not an official service guarantee.

| Source and exact entry URL | Access, format and authentication | Publisher cadence / proposed v1 handling | Licence / access evidence |
| --- | --- | --- | --- |
| AusTender OCDS, [API documentation](https://github.com/austender/austender-ocds-api); base `https://api.tenders.gov.au/ocds/` | Official JSON CN API; sampled GETs succeeded without a token or account. Date endpoints and `findById` below. No APP/ATM endpoint established. | On-demand queries; update latency and rate limits unverified. Proposed daily incremental CN pull, weekly output. | Saved date packages explicitly name CC BY 3.0 AU. `findById` sample omits the licence field. Saved HTTP 200. |
| AusTender [main service](https://www.tenders.gov.au/), [Current ATMs report help](https://help.tenders.gov.au/getting-started-with-austender/information-made-easy/current-approaches-to-market/) | Official search/report interface; Finance confirms a Current ATMs report. Exact downloadable CSV/JSON schema and unauthenticated export route unverified. Free registration supports notifications and tender participation. | Event-driven notices/amendments; exact feed latency unverified. Manual verification before an open alert. | [Current terms](https://help.tenders.gov.au/terms-of-use/) blocked. Do not apply the CN API licence to web notices or attachments without evidence. Help report fetch returned 403. |
| AusTender [Planned Procurements report help](https://help.tenders.gov.au/getting-started-with-austender/information-made-easy/future-business-opportunities/) | Official APP/report route linked by Finance; view/export through official UI when accessible. API, bulk format and export authentication unverified. | Agencies update plans during the year; not a guaranteed annual-only refresh. Curate reviewed entries, initially weekly. | Help fetch returned 403. Report download and redistribution terms unverified. APPs are indicative, not bid invitations. |
| AusTender [public RSS path](https://www.tenders.gov.au/public_data/rss/rss.xml) | A saved request exists, but body was a CloudFront error, not XML. Current feed contents and coverage unverified. | Unverified; disabled in v1. | Saved HTTP 403. Do not design around an assumed ATM/APP feed or licence. |
| Defence [public AIC index](https://www.defence.gov.au/business-industry/finding-opportunities/public-australian-industry-capability-plans) | Public HTML directory with PDF links, dates and domains; no account on saved requests. Observed pagination `?page=0` through `?page=7`; only the saved first index page was inspected. No public API/CSV/Atom export established. | Documents are published/revised irregularly. Start from saved PDFs and a small manually maintained manifest. | Saved index and four PDFs HTTP 200. Defence site copyright applies subject to document-specific rights; commercial reuse unverified. |
| Defence [finding opportunities](https://www.defence.gov.au/business-industry/finding-opportunities) and [Estate Works Program forward schedule](https://www.defence.gov.au/business-industry/finding-opportunities/estate-works-program-forward-schedule) | Official navigation/forecast sources. HTML/PDF, no API verified. Generic landing-page browser extraction yielded only a browser warning; forward-schedule page was inaccessible through that tool. | Forecast revisions, not a live package feed. Optional curated source after content/rights review. | Defence rights restrictions. The separately indexed official 2026 forecast explains its indicative nature; see section 7. |
| ASA [industry opportunities](https://www.asa.gov.au/industry) | Public HTML with qualification, security, engagement and project links; no API/feed found in saved content. No login for the saved page. | No publication SLA; saved page HTTP Last-Modified 20 Nov 2026. Review selected pages weekly, using curated facts. | Saved HTTP 200. Its footer links to Defence copyright; no independent open licence established. |
| ASA [Henderson precinct](https://www.asa.gov.au/projects/henderson-defence-precinct), [SRF-West infrastructure](https://www.asa.gov.au/projects/submarine-rotational-force-west-infrastructure-project), [qualification pathways](https://www.asa.gov.au/industry-qualification-pathways), [security](https://www.asa.gov.au/industry-security) | Exact links discovered in saved ASA HTML. Destination contents, any applications and any API/export remain unverified in this research. | Candidate manual-review seeds, initially disabled for content ingestion. | Apply source-specific review; a link's presence supplies neither eligibility nor a tender status. |
| Defence West [Western Defence Forge](https://www.wa.gov.au/organisation/defence-west/western-defence-forge) and [Land Forces engagement](https://www.wa.gov.au/organisation/defence-west/defence-west-land-forces-international-land-defence-exposition-2026) | Official indexed pages describe readiness, supply-chain engagement and events. No procurement API or export verified. | Programme/event updates, cadence unverified. Research/reference only under the present source policy. | [WA terms](https://www.wa.gov.au/terms-of-use) restrict automation and reuse. **No automated WA.gov.au ingestion in v1.** |
| [WA Defence Industry & Science Capability Directory](https://directory.defencewest.wa.gov.au/) | Qualitative research only: supplier/capability directory, not proof of open demand. Login/export terms and subdomain-specific licence unverified. | No ingestion, no lead-list download, no commercial scraping. | Owner's explicit exclusion applies regardless of any technical accessibility. Do not infer a bulk-data licence from public profiles. |
| ICN [Gateway](https://gateway.icn.org.au/), [join](https://gateway.icn.org.au/join), [FAQ](https://gateway.icn.org.au/faq), [terms](https://icn.org.au/terms-use) | First-party competitor and application-route research. Free Limited registration exists for eligible ANZ businesses; other tiers exist. No public ingestion API/bulk licence verified. | Project owners update packages; no latency guarantee established. Link out, do not crawl or mirror. | ICN retains rights; restricted functionality can require subscriptions. This is not a radar data-feed entitlement. |
| Finance [Using AusTender](https://sellingtogov.finance.gov.au/faq/using-austender), [finding opportunities guide](https://sellingtogov.finance.gov.au/guide/identifying-opportunities-to-sell-to-government), [procurement transparency rules](https://www.finance.gov.au/government/procurement/commonwealth-procurement-rules/accountability-and-transparency) | Public official guidance used to verify distinctions and report entry points, not an opportunity feed. | Guidance changes as policy changes; review before implementation. | Guidance does not grant a licence to third-party tender attachments. |

### Saved endpoint results, including 403s

The following are direct saved HTTP observations, not guesses about host-wide availability. Four saved 403 responses were CloudFront HTML errors. The API robots response was a different JSON error.

| Exact requested URL | Result and local evidence |
| --- | --- |
| `https://www.tenders.gov.au/robots.txt` | 403, `austender-robots.*`, HTTP Date 08:10:48 UTC / 16:10:48 AWST. |
| `https://help.tenders.gov.au/robots.txt` | 403, `austender-help-robots.*`, 08:10:49 UTC. |
| `https://api.tenders.gov.au/robots.txt` | 403 JSON `Missing Authentication Token`, `austender-api-robots.*`, 08:10:50 UTC. A failure at this path does **not** establish that the working OCDS routes need authentication. |
| `https://www.tenders.gov.au/public_data/rss/rss.xml` | 403, `austender-rss.*`, 08:10:54 UTC. |
| `https://help.tenders.gov.au/terms-of-use/` | 403, `austender-current-terms.*`, 08:11:53 UTC. |
| `https://api.tenders.gov.au/ocds/findByDates/contractPublished/2026-10-01T00:00:00Z/2026-10-02T00:00:00Z` | 200, `cn-sample.*`, 08:10:56 UTC; 93 releases, no `links.next`. |
| `https://api.tenders.gov.au/ocds/findById/CN4280056` | 200, `cn-by-id.*`, 08:13:38 UTC; one release. |
| `https://api.tenders.gov.au/ocds/findByDates/contractLastModified/2026-11-20T00:00:00Z/2026-11-21T00:00:00Z` | 200, `cn-last-modified.*`, 08:13:39 UTC; 100 releases and `links.next`. |
| `https://api.tenders.gov.au/ocds/findByDates/contractLastModified/2026-11-20T00:00:00Z/2026-11-21T00:00:00Z?cursor=VWak_KQoQW9OdzRxT2srNkVES1VOT05ESTRPVGszTlNsRFRqUXlPRGs1TnpVPWQ&prevcursor=initial&lastcursor=initial` | 200, `cn-last-modified-page2.*`, 08:14:52 UTC; another 100 releases, `links.prev` and another `links.next`. **This saved window is incomplete.** |
| `https://www.defence.gov.au/robots.txt` | 200, `defence-robots.*`. Generic-agent rules restrict administrative/search paths; a separate Googlebot group disallows certain document paths. These are access rules, not copyright permission. |
| `https://www.wa.gov.au/robots.txt` | 200, `wa-robots.*`. Site terms impose further restrictions; robots availability does not override them. |
| `https://www.asa.gov.au/robots.txt` | 200, `asa-robots.*`. Administrative/search restrictions; no reuse licence. |

Two additional official report-help endpoints returned **403 through the browser tool**, without saved HTTP metadata: the Current ATMs and Planned Procurements URLs in the register. `https://gateway.icn.org.au/robots.txt` and the Defence forward-schedule page were reported inaccessible by that tool without a verified HTTP status. Do not relabel those errors as 403s. The recovery note's broader report that AusTender web hosts were blocked is consistent with the saved endpoint failures, but not every page on those hosts was tested. No block bypass, proxy rotation or authenticated scraping is proposed.

## 3. AusTender: a supported route and its limits

### 3.1 Contract notices through OCDS

The [AusTender publisher repository](https://github.com/austender/austender-ocds-api) describes a CN API and links to [its Swagger documentation](https://app.swaggerhub.com/apis/austender/ocds-api/1.1#/). The README documents ISO 8601 date paths and CN searches, with several searches covering data from 1 January 2013. Swagger details were not independently inspected; live limits, error schemas and date-boundary inclusivity remain unverified.

Verified request templates:

```text
GET https://api.tenders.gov.au/ocds/findByDates/contractPublished/{start_utc}/{end_utc}
GET https://api.tenders.gov.au/ocds/findByDates/contractLastModified/{start_utc}/{end_utc}
GET https://api.tenders.gov.au/ocds/findById/{contract_notice_id}
```

The README also documents `contractStart` and `contractEnd` date searches. They were not exercised here. Do not invent `tenderPublished`, `APP`, `ATM` or an agency-filter query parameter. Filter locally after receiving official releases unless later documentation verifies a server-side filter.

Saved observations with implementation consequences:

- Packages declare `version: "1.1"`, `publisher.name: "Department of Finance"`, `releases`, `publishedDate`, and an extension reference. Do not automatically fetch arbitrary extension URLs.
- The three date pages contain **293 distinct `(ocid, id)` release pairs**. Their tags are `contract` or `contractAmendment`; no tender publication was observed. This is a small sample, not a measure of total Defence demand.
- The 20 November date query genuinely paginates. Follow the supplied `links.next` as an opaque URL after validating the expected HTTPS API host/path/window. Stop only when no next link remains. Do not generate/decode cursor values, assume 100 records is a universal limit, or call the first two pages a complete run.
- Agency identity is in `parties` with the `procuringEntity` role in these samples; `buyer` is absent. Match the documented agency name/identifier, retain the source value, and avoid confusing it with a supplier.
- Capability clues appear in `contracts[].description` and item `classification` with scheme `UNSPSC`; contract titles can instead be purchase-order identifiers. No official UNSPSC-to-Henderson mapping was verified.
- `contracts[].period.endDate` is a contract end, never a tender closing date. `awards[].status`, `contracts[].status` and `tender.procurementMethod` describe other stages of the procurement.
- Monetary amounts appear as strings. Preserve original currency/value and use decimal arithmetic if needed. An award's value is not the SME-accessible subcontract budget; amendments must not be summed blindly.
- Contact points in the sample are not a safe application route: an agency-looking contact can sit on a supplier party, and a generic Finance mailbox appears on procuring entities. Do not manufacture an application email from these fields.
- For example, CN4280056 is a Defence electronic-equipment contract notice, not a marine open tender. Its sparse description and supplier address cannot prove Henderson delivery or a relevant electrical work package.

### 3.2 Licence and operational access

The three saved date packages contain this exact field:

```json
"license": "https://creativecommons.org/licenses/by/3.0/au/"
```

The [Creative Commons deed](https://creativecommons.org/licenses/by/3.0/au/) permits reuse **“for any purpose, even commercially”**, subject to attribution and its other conditions. Preserve publisher/source/title where supplied, link the licence, identify transformations, retain relevant notices and avoid endorsement claims or new restrictions on the licensed material. Consult the linked legal code when implementing attribution.

Suggested output credit: “Contains AusTender contract-notice data published by the Australian Government Department of Finance, licensed under CC BY 3.0 AU. Filtered and classified by Henderson Defence Supply-Chain Radar; not endorsed by the Commonwealth.” Include the source query/notice and access date alongside the credit.

The `findById` sample omits `license`. Preserve the date-package provenance for that same notice and the source-level licence evidence; do not pretend that this particular response explicitly declared it. For a standalone record without established licence provenance, record that limitation before redistribution. No inference about rights in tender attachments, supplier trademarks or other websites follows from the API licence.

Use the intentional public API conservatively: one request at a time, identifiable user agent, cache responses, bounded timeouts and retry/backoff for 429/temporary server failures, honour `Retry-After`, and stop on persistent access denial. A two-second minimum gap is a proposed v1 default, **not** an advertised rate limit. The API's robots path failure does not invalidate observed keyless access, nor confer permission for unrelated scraping. Current service-wide terms remain unverified because the help page was blocked.

### 3.3 Procurement plans and approaches to market

[Finance's supplier guide](https://sellingtogov.finance.gov.au/guide/identifying-opportunities-to-sell-to-government) explicitly points to the Current ATMs report and Planned Procurements report. [Finance's AusTender FAQ](https://sellingtogov.finance.gov.au/faq/using-austender) describes free registration, profile-based notifications, current/closed notices and plans; APPs can change or be withdrawn. These are supported discovery routes, but not evidence of a machine-readable APP/ATM API.

The lawful v1 path is therefore conditional and modest:

1. A human uses the official reports/search and free account where necessary; follows the current terms and notice-specific document conditions; and records the exact source, notice identifier, status, deadline, eligibility and application route.
2. If the service offers an official export and its terms permit the intended use, save it unchanged with provenance and implement an importer for the **observed** format. Until a real sample and rights evidence exist, CSV/export automation is unverified and no such adapter is promised.
3. Otherwise retain a small reviewed seed record containing a link and independently written factual notes, subject to rights review. Do not mirror tender documents or scrape a blocked web interface. An official report is not itself blanket redistribution permission.
4. Direct applicants to the official ATM and its actual lodgement instructions, with registration/login requirements stated. A notification email, contract notice, APP entry or radar record cannot substitute for an application.

The [current Finance transparency guidance](https://www.finance.gov.au/government/procurement/commonwealth-procurement-rules/accountability-and-transparency) distinguishes planned procurement, open tenders and contracts awarded. It calls for APP updates during the year and generally requires reportable contract publication within 42 days. Thus even a newly published CN can describe earlier activity. No claim of immediate, complete supply-chain visibility is supportable.

## 4. Public AIC plans and the four saved samples

### 4.1 Discovery and reuse

The saved [Defence AIC index](https://www.defence.gov.au/business-industry/finding-opportunities/public-australian-industry-capability-plans) says plans inform industry of forward opportunities and provide contractor contacts for discussion/registration. Its exact currency caveat is **“accurate as at the date of publication.”** The first saved page includes both maritime and other domains. Pagination means a one-page scrape would miss older plans; no completeness claim is made for the four samples.

The [Defence copyright page](https://www.defence.gov.au/copyright) permits material to be **“downloaded, displayed, printed and reproduced in unaltered form for personal and non-commercial use.”** It reserves other rights and specifies a separate conditional news-media permission. This project has not established that it qualifies for that exception. Its imagery provisions are not a licence for AIC PDFs. ASA's saved footer points to this policy.

**Product decision:** use saved documents for controlled research and extraction evaluation; do not redistribute whole PDFs, substantial extracted tables, logos or copied descriptions. Keep rights/provenance per document. Public or commercial publication of AIC-derived content requires a documented lawful basis for the intended use; public hosting and a “public plan” title do not settle this. An independently written fact-and-link summary reduces copying but is not a declared legal exemption. Document-specific permission and third-party ownership remain unverified. No rights enquiry has been sent.

### 4.2 Sample URLs, versions and findings

All four saved PDF responses were HTTP 200 on 22 November, at approximately 16:11–16:12 AWST. Page references below are PDF pages; text line references refer to the existing local `.txt` extraction. Full supplier tables are deliberately not reproduced.

#### RMP-West — Babcock

Exact source: [RMP-W-PublicAICPlan.pdf](https://www.defence.gov.au/sites/default/files/aic/2025-02/RMP-W-PublicAICPlan.pdf). Local files: `aic-rmp-west.pdf`, `.pdf.meta.json`, `.txt`.

- **Identity/date:** contract CASG/MSD/Con17640/1. No explicit issue date or revision was found in the extraction. HTTP Last-Modified is 12 February 2025; do not substitute this for a verified issue date. Page 2 describes an initial five-year term effective 13 October 2022.
- **Scope and geography:** western-region maintenance management and sustainment for Anzac, Arafura and, as described in this older plan, Supply-class vessels. Subcontract categories on pages 3–4 repeatedly specify Henderson and Garden Island, WA. This is the strongest direct local evidence among the samples.
- **Relevant capabilities:** engines, gearboxes, pumps, hydraulics/steering/stabilisers, hoses, pipework, HVAC, preservation, hull valves/anodes, structural work, cable repair, generation, instrumentation, hull surveys, tank cleaning, docking, craneage and scaffolding. See `.txt` lines 61–173.
- **Eligibility:** the plan encourages capable Australian suppliers, especially SMEs and Indigenous/veteran businesses. This is not proof of an exclusive eligibility rule, nor a universal NATA requirement; certification/NATA is itself listed as a service category.
- **Route:** page 5 invites supplier contact via `marineausprocurement@babcock.com.au`; the PDF hyperlink corroborates that spelling. It also describes ICN and industry engagement. This is an enquiry/registration route, not a package-specific bid portal or deadline.
- **Status:** published supply-chain scope, with no verified closing date. An already operating prime contract can still describe possible subcontract scope; it cannot establish that a particular trade package is presently being competed.
- **Data caution:** page 2's total-subcontractor forecast is $378m, while page 3 describes approximately $366m of Australian subcontract scope. Preserve their different labels; do not silently reconcile them or present either as an available budget.

#### Hunter — BAE Systems Maritime Australia / ASC Shipbuilding

Exact source: [BAESystemsMaritimeAustraliaPublicAICPlan.pdf](https://www.defence.gov.au/sites/default/files/aic/2025-04/BAESystemsMaritimeAustraliaPublicAICPlan.pdf). Local files: `aic-hunter.pdf`, `.pdf.meta.json`, `.txt`.

- **Identity/date:** approved 22 April 2025; server Last-Modified 28 April 2025. Covers the June 2024 amendment for the first three Hunter frigates, with an expected eight-year Batch 1 scope. These are programme facts, not bidding dates.
- **Geography:** shipbuilding at Osborne, SA, with national supplier participation. The equipment table includes WA stabiliser/steering supply. A WA supplier entry does not relocate the whole project to Henderson.
- **Existing versus prospective:** pages 2–3 name equipment packages with suppliers; treat those as established supply-chain context. Page 3 separately identifies future HVAC, surface-ship torpedo-defence and visual-surveillance scope, plus later Batch 2 engagement. Do not merge those sections into a list of unawarded packages.
- **Route:** businesses are directed to the ICN Hunter portal, with specific opportunities to be posted through ICN. The saved PDF's actual link is `http://www.icn-sa.org.au/`; a current Hunter project URL was not independently resolved. Retain the original route and mark current resolution unverified. The named programme contact is an enquiry contact, not a bid lodgement instruction.
- **Eligibility/rights:** no universal certification threshold is stated. Pages carry **OFFICIAL** and **BAE SYSTEMS PROPRIETARY** markings; no open-reuse grant was identified. Public availability does not erase the latter marking.
- **Status:** future scope where explicitly described; supplier table is awarded/existing context. No confirmed-open entry follows from this plan alone. Relevant `.txt` lines: 18–34, 71–141 and 175–185.

#### Austal — Strategic Shipbuilding Agreement / Management Services Tasking Statement

Exact source: [Annex-Public Australian-Industry-Capability-SSA-MSTS.pdf](https://www.defence.gov.au/sites/default/files/aic/2026-04/Annex-Public%20Australian-Industry-Capability-SSA-MSTS.pdf). Local files: `aic-austal-ssa.pdf`, `.pdf.meta.json`, `.txt`.

- **Identity/date:** SSA NSSG/PBSS/Con42030/1 and MSTS NSSG/PBSS/Con42030/2. No explicit issue date/revision was found in extracted text. The index gives 20 April 2026 and the server Last-Modified is the same date.
- **Scope:** a framework for subsequent shipbuilding tasking statements at Henderson, including LCM/LCH programmes. MSTS largely covers enabling management, engineering, procurement and governance. Its stated maximum duration/value is not a trade-package budget or closing date.
- **Actual pipeline evidence:** pages 3–4 anticipate fitout, HVAC/chilled water, propulsion subassemblies, power equipment, pumps/valves/pipes, water plant, cabling, switchboards, lighting, surveillance/combat systems and logistics. Some critical-path sourcing decisions have already been made. Separate plans are expected for subsequent tasking statements; do not assume every listed category remains available.
- **Route:** the saved PDF's embedded hyperlink resolves to [ICN Defence Strategic Shipbuilding, project 10366](https://gateway.icn.org.au/projects/10366/pg-10366). Page 4 supplies `Robert.mccullagh@austal.com` for supplier enquiries. No application is implied by merely contacting that address.
- **Classification check:** the supplemental ICN page displayed one open entry called **Keep Me Updated**, whose purpose is future communications/briefings. It also displayed closed or awarded packages. The registration entry is not an open work procurement. Several dates were masked, and the page overview retained older conditional SSA wording: use page-specific evidence cautiously and recheck before action. This browser observation is not a complete current market survey.
- **Conditions:** the plan describes sourcing trade-offs against delivery milestones, not universal SME eligibility. There is no blanket supplier certification rule or verified closing date. The extracted LCM AIA-1 cell says LCH; flag the source inconsistency instead of automatically repairing it. See `.txt` lines 98–178.
- **Status:** published future scope, conditional on sourcing and tasking. Supplier registration is a separate engagement action. No open-reuse licence was identified in the extraction.

#### LM2500 in-service support — GE Aviation Systems Australia

Exact source: [LM2500GasTurbinesInServieSupportContractGeneralElectricAviationSystemsAustraliaPtyLtd-AICPublicPlan.pdf](https://www.defence.gov.au/sites/default/files/aic/2026-04/LM2500GasTurbinesInServieSupportContractGeneralElectricAviationSystemsAustraliaPtyLtd-AICPublicPlan.pdf). The `InServie` spelling is part of the actual URL. Local files: `aic-lm2500.pdf`, `.pdf.meta.json`, `.txt`.

- **Identity/date:** contract CASG/MSD/Con31154/1; issue date 14 April 2026, Revision 2, signed 15 April; server/index date 21 April 2026. Initial term is five years three months from 1 January 2024, with extension options. Do not present optional extensions as exercised contracts.
- **Scope:** LM2500 support for Anzac, Canberra and Hobart classes; Level 1/2 repair and field maintenance, spares, warehousing, programme management and management of higher-level maintenance. The supplier table provides WA-related support context including Rockingham, but is not a vacancy list.
- **Capabilities:** engine/component repair, fluid systems, electrical/generator services, calibration, inspection, testing, cranes, scaffolding, logistics and specialist tooling. The dense table's scope/location headings and values are awkwardly arranged; row inference needs visual review.
- **Future scope:** page 7 explicitly explores expanded domestic depot/component capability, including Level 4/5 support if commercially viable. That condition must remain attached to a future-scope alert; it is not a confirmed purchase or a claim that every maintenance SME qualifies.
- **Route and extraction defect:** page 7 names a senior programme contact but prints an email with a space: `Janina Hildebrandt@geaerospace.com.au`. Visual inspection of the saved PDF confirmed the defect; do not invent a dot or silently normalize it. The separately printed alternative is `Andy.Mckenzie@geaerospace.com.au`, an enquiry route only. Current deliverability was not tested.
- **Eligibility/rights/status:** no general accreditation threshold or bid deadline is stated. OFFICIAL markings are present, but no reuse licence was identified. Existing-supplier information is context; explicit future depot scope is published future scope, with commercial viability unresolved. Relevant `.txt` lines: 19–60, 311–377.

## 5. Practical capability taxonomy

Use a small, versioned, many-to-many taxonomy with aliases and evidence spans. It is a radar classification scheme, **not** an official Defence procurement code or certification standard. Keep what a business can do separate from what it is permitted/qualified to bid for. The examples below normalize the four plans; some adjacent terms require human confirmation.

| Stable capability key | Included work and useful aliases | Evidence and boundary |
| --- | --- | --- |
| `marine_electrical` | Marine cabling, cable repair, switchboards, distribution, generation, motors, lighting | RMP-West pp. 3–4; Austal p. 4. A generic electronic-equipment CN is insufficient without scope. |
| `fabrication_welding` | Structural/plate fabrication, steel/aluminium work, welded assemblies, fitout structures | RMP-West structural work; Austal Australian steel/outfitting pp. 3–4; GE fabrication entries. Material and weld qualifications must come from the actual package/profile. |
| `precision_machining` | CNC/manual machining, turning/milling, shafts, precision component manufacture/repair | Owner-requested SME category; GE component-repair scope is adjacent evidence, not proof that it requires machining. CNC appears in the directory's qualitative industrial vocabulary. Require explicit task evidence before a strong match. |
| `corrosion_preservation` | Surface preparation, protective coatings, blasting/painting, anodes/cathodic-protection work | RMP-West preservation and hull anodes. Aliases are proposed normalizations; a single anode supply item does not prove a coating-services package. |
| `hydraulics_pneumatics` | Hydraulic pumps/hoses, steering gear, stabilisers, cylinders, air/compressed-gas systems | RMP-West pp. 3–4; Hunter steering/stabiliser equipment; GE fluid/hoses evidence. Distinguish mechanical hydraulic systems from building plumbing. |
| `piping_fluid_systems` | Pipe fabrication/installation, valves, tanks, fuel/oil transfer, water and sewage systems, lagging | RMP-West and Austal machinery systems. Keep contamination/hazard requirements as separate explicit conditions. |
| `propulsion_rotating_equipment` | Engines, gas turbines, gearbox/drivetrain, pumps/compressors, component overhaul | All four plans. OEM authorization and maintenance level cannot be inferred from a keyword match. |
| `vessel_maintenance_docking` | Preventive/corrective maintenance, refit, docking/undocking, boats/RHIBs, hull work | RMP-West is direct Henderson/Garden Island evidence. Naval construction and shore-estate work remain separate contexts. |
| `hvac_refrigeration` | Ventilation, air conditioning, refrigeration, chilled water, cold rooms | RMP-West, Hunter and Austal. Existing Hunter HVAC supply and future HVAC scope are different evidence items. |
| `instrumentation_controls` | Instrument calibration, sensors, control panels, platform controls, testing equipment | RMP-West, Hunter, GE. Combat/radar/sonar integration is a specialist subtag, not automatic eligibility for an electrical SME. |
| `inspection_assurance` | Hull survey, testing, metrology/calibration, certification services; NDT only when evidenced | RMP-West hull survey/certification and GE testing/calibration. A service category named NATA does not make NATA mandatory for every trade. |
| `lifting_access_support` | Craneage, rigging, scaffold, access systems, lifting equipment, wharf/hardstand support | RMP-West p. 4 and GE supplier scope. Separate equipment supply, hire, installation and operation. |
| `cleaning_environmental_services` | Tank cleaning, oily-water systems, waste handling, vessel cleaning | RMP-West pp. 3–4. Environmental/site permissions are unknown unless specified. |
| `engineering_logistics_support` | Marine design, production engineering, integrated support, warehousing, transport, spares | Austal MSTS, Hunter strategy and GE support. Lower trade-specific relevance unless a concrete deliverable is identified. |

Additional profile dimensions: materials; fabrication/machining size limits; workshop versus mobile service; build/repair/supply/inspection activity; vessel/system experience; capacity; delivery regions; subcontract tier; self-declared qualifications with expiry and evidence. Geography should distinguish Henderson, Garden Island/HMAS Stirling, wider Perth/WA, national/offsite supply and unknown. Supplier headquarters must not stand in for work location.

Security, export controls, OEM approvals, quality systems, insurance and site access are **readiness dimensions**, not assumed universal requirements. ASA's saved industry page links to qualification and security guidance; the linked details were not reviewed here. Record individual requirements as required/preferred/unknown only when supported by the specific notice or applicable verified guidance. Do not turn Indigenous/veteran participation objectives into an exclusivity rule.

## 6. Competitors, substitutes and an honest residual gap

| Service | What it already does | Implication for this radar |
| --- | --- | --- |
| **ICN Gateway / ICN advisers** | Supplier profiles, project/work-package discovery, EOIs and notification preferences by region/sectors/capabilities; advisers connect businesses to projects. [FAQ](https://gateway.icn.org.au/faq), [how it works](https://gateway.icn.org.au/how-it-works), [government overview](https://business.gov.au/expertise-and-advice/industry-capability-network). | Capability matching and alerts are existing features. Austal and Hunter explicitly direct suppliers there. Link to the authoritative route and add interpretation only where it improves a user's decision. |
| **ICN free versus paid packages** | The current [join page](https://gateway.icn.org.au/join) offers a free Limited profile/EOI tier and paid tiers with additional features. Plain-text comparison extraction does not reliably establish every feature entitlement. | Do not promise all searches/alerts are free, require a paid account, or reproduce hidden dates. Verify the user's applicable tier before making a feature comparison. |
| **Defence West / Western Defence Forge** | Official descriptions include industry readiness, capability registration, supplier connections and engagement events; see [Forge](https://www.wa.gov.au/organisation/defence-west/western-defence-forge) and [Land Forces](https://www.wa.gov.au/organisation/defence-west/defence-west-land-forces-international-land-defence-exposition-2026). | Local advice and introductions are strong substitutes. A narrow weekly assessment may complement them, but evidence does not establish that Defence West lacks equivalent internal support. WA source restrictions prevent treating its pages as a free aggregation feed. |
| **WA capability directory** | Searchable supplier/capability discovery and regional/industrial vocabulary. | Supply-side visibility is not proof of unfilled demand. Qualitative research only; no lead generation, company harvesting or commercial scraping. |
| **AusTender itself** | Official procurement publication, plans, search, free profile-based notifications and submission routes. [Finance FAQ](https://sellingtogov.finance.gov.au/faq/using-austender). | Retain it as the authority for Commonwealth ATMs. Useful radar work is trade-specific interpretation across sources, not a claim to discover all tenders earlier. |
| **Defence AIC index and ASA industry hub** | Prime forward-scope/contact information and readiness/programme navigation, respectively, as established by the saved pages. | Good research inputs but not a standardized live package feed. Curated explanation of what is known, conditional and missing can help a small firm. |
| **Defence estate forward schedule** | Publishes an indicative pipeline with project regions and timing; official forecast below. | Relevant adjacent infrastructure work may compete for an SME's attention. Preserve the distinction between shore works and naval vessel supply; do not label the forecast open. |

ICN's [terms](https://icn.org.au/terms-use) permit specified unaltered uses **“for your personal, non-commercial use or use within your organisation”**, retain other rights, and restrict obtaining information through unintended means. This is not verified permission for a commercial mirror or bulk feed. ICN is researched here as a competitor and a destination named by official plans, not added to the allowed automatic ingestion set.

**Residual-gap hypothesis:** a firm supplies its own capabilities once and receives (a) a short weekly view across CN context, reviewed AIC scope and official opportunity seeds; (b) explanations of the matched work, geography and evidence; (c) a strict distinction between bid, prepare/register and speculative watch; (d) close-date/route/eligibility completeness and explicit unknowns; and (e) a one-page preparation assessment. It must be possible to trace every substantive statement back to a source and date.

**Unproven demand:** whether firms save enough time, whether the extra public evidence adds useful work beyond their ICN/AusTender alerts, and whether permitted content supports a sustainable product. Validate with a few consenting Henderson SMEs comparing real weekly briefings against their existing workflow. Measure relevant new information and decision time, not alert volume. Do not claim an exclusive database, complete subcontract coverage, legal clearance or a competitive advantage already demonstrated.

## 7. Classification and evidence rules

The three labels describe evidence for an alert; they are not exhaustive lifecycle states. Maintain record kind, lifecycle and review state separately so awarded contracts, closed tenders and supplier registrations are not squeezed into misleading opportunity labels.

| Public alert class | Minimum evidence | What cannot establish it |
| --- | --- | --- |
| **Confirmed open opportunity** | A named procurement/work package on an authoritative buyer/prime route, expressly accepting submissions; specific scope; verified application instructions; a future deadline with timezone, or explicit ongoing intake; sufficiently recent verification and no later closure/cancellation. State whether it is an EOI, RFT, RFQ or another actual procurement stage. | An AIC plan, APP, contract award, “active” contract, generic EOI/signup/newsletter, masked deadline, search snippet or large investment announcement. An open EOI is not a contract award. |
| **Published future work scope** | An official plan/prime public AIC statement identifies scope or a planned procurement, with source date, conditions and uncertainty preserved. No current bid invitation is established. | An inferred package created solely from generic spending, an unrelated capability term, or an old closed tender with no new planning evidence. |
| **Speculative** | An explicit analyst hypothesis grounded in cited official facts, with reasoning and missing evidence shown. No claim of buyer commitment, eligibility or a deadline. Human review required. | Unsupported rumours; guesses presented as sourced packages; automatically predicting a re-tender from a contract end date. |

Apply these rules in order:

1. **Scope gate:** identify whether the item is procurement, planning, contract context, registration, grant/event or general news. Keep events/grants/registrations in a separate optional readiness/context view; do not count them as work packages.
2. **Rights and evidence gate:** retain provenance and permission state. Unverified rights or unreviewed extraction means hold from distributable content, not “speculative” as a workaround.
3. **Lifecycle gate:** expired, cancelled, awarded or superseded items leave current alerts. Preserve their history and a closure reason. Missing/retrieval-failed evidence does not mean closed; mark verification unavailable/stale.
4. **Open gate:** all minimum evidence above must be satisfied. Unknown eligibility is shown explicitly and can coexist with a genuinely open opportunity; it cannot become “eligible.” Unknown application instructions cannot support an actionable open alert.
5. **Future gate:** quote/locate the official forward-scope evidence and retain limitations. An AIC scope might already be partly contracted; use “availability not verified” where appropriate.
6. **Inference gate:** if scope is the radar's hypothesis rather than publisher intent, require a reviewable explanation and make speculative visibility opt-in. No ML probability score can replace these gates.

Concrete examples from the evidence:

- RMP-West hydraulics and local maintenance categories: **published future/ongoing supply-chain scope**, with an enquiry route and no bid deadline.
- Austal anticipated shipbuilding categories: **published future scope**. The ICN **Keep Me Updated** item: **registration/context**, even if the portal labels it Open. Do not assign an open-procurement alert to it.
- Hunter's named existing equipment suppliers: **context**; its separately identified future systems scope: **published future scope**. A package at Osborne needs an offsite/national-supply rationale for a Henderson business.
- LM2500 domestic Level 4/5 development: **published future scope**, explicitly conditional on commercial viability. Current subcontractor rows are not vacancies.
- CN4280056 and other `contract`/`contractAmendment` releases: **contract context**, no submission route. A hypothesized future replacement order would be **speculative** only if separately justified, not silently derived.
- The official [2026 Estate Works tender forecast](https://www.defence.gov.au/sites/default/files/2026-03/EstateWorksProgramTenderForecast2026.pdf) labels its dates indicative, warns they can change, and says projects are formally released on AusTender. A forecast quarter is a **future-scope timing range**, never a closing date. The indexed version was correct as at 5 May 2026; its currentness on 22 November is unverified.

Recommended freshness defaults, to be tuned in a pilot: open records reverified within 24 hours of output; future scope reviewed within 30 days, retaining the original publication date; speculative analysis expires/requires review within 30 days. These are product policies, not source guarantees. Automatic time passage closes an exact expired deadline but never proves an unobserved award. If only a date or ambiguous zone is given, retain that raw value and hold open classification until clarified. Store UTC instants and render AWST; also show the source's original zone and wording. Do not assume an east-coast deadline uses Perth time.

Each alert must show: class; procurement stage; lifecycle/currentness; capability reasons; location; eligibility requirements and unknowns; closing date or an explicit “not published/not applicable”; official application/enquiry route with its purpose; source links and document page/notice ID; source and verification dates; conditions; and any analyst inference. Suggested labels are “Apply via official notice,” “Prepare / verify future scope,” and “Watch hypothesis,” according to the actual evidence.

## 8. Risks and controls

| Risk | Consequence | v1 response |
| --- | --- | --- |
| Restrictive or uncertain reuse | Public data access is mistaken for commercial publication rights. | Per-source permission record; link/fact-only or internal evaluation where justified; hold uncertain derived content from distribution. No PDF/table mirror. |
| WA automation restrictions | A technically fetchable page is treated as an allowed feed. | [WA terms](https://www.wa.gov.au/terms-of-use) expressly say **“not access or use the WA.gov.au website or Other Government Services using automated means”**; they also restrict commercial reuse and competitive use. Exclude automated WA ingestion. Directory remains qualitative only. |
| APP/ATM access gap | Product implies complete live opportunity discovery with no working feed. | Curated official records/export only after verification; publish coverage and failure notes. Do not invent an API or bypass 403s. |
| Snapshot and update lag | Old plans and CN reporting delays look like new opportunities. | Separate published, source-modified, fetched, reviewed and first-seen dates. Changed-content detection and explicit staleness; no “new” alert on every re-import. |
| Truncated pagination or failed refresh | Partial data silently becomes authoritative. | Complete-window checkpoints; preserve last successful data; output run health and omissions. The saved two-page modified query is a regression case, not a complete fixture window. |
| Misleading matching | Generic procurement, supplier addresses or named incumbents yield false local matches. | Scope-first matching, explicit activity/location evidence, negative rules and auditable reasons; agency affiliation alone is insufficient. |
| Table/PDF defects | Contact, scope and location cells are swapped or repaired incorrectly. | Page/line evidence, extraction warnings, human review; malformed LM2500 email and Austal AIA cell are concrete cases. |
| Eligibility overclaim | A relevant trade is mistaken for an approved Defence supplier. | Separate capability fit from eligibility, record conditions individually, show unknowns and require official validation. |
| Application-route errors | Users miss a deadline or submit through the wrong channel. | Link directly to verified official instructions; label enquiry versus registration versus submission. Radar never lodges on behalf of users. |
| Sensitive/commercial profile data | A firm's capacity, contacts or credentials leak in public outputs. | Local profiles; no credentials or personal contact harvesting; explicitly public versus internal outputs. Use necessary published business routes only. |
| Overbuilding | One developer ends up maintaining a broad scraper or a paid intelligence service. | Small allowlist, stdlib pipeline, manual curation, static outputs and offline tests; no paid feeds/LLM runtime dependency. |

Public-launch blockers are specific: unverified rights for AIC-derived distribution, unproven reliable open-notice input, and unvalidated user value. They do not prevent building a transparent local research tool on licensed CN data, author-created fixtures and permission-reviewed seeds. They do prevent claiming a complete automatically updated commercial tender service now.

## 9. Recommended v1 ingestion and delivery approach

1. **Source registry and evidence store first.** Record allowed access mode, terms URL/check date, licence/permission evidence, permitted output mode, exact origin URL, retrieval result, hash and attribution. Keep raw bodies outside git and retain original bytes. A disabled source remains visible in a coverage report.
2. **AusTender CN adapter.** Use Python 3 stdlib HTTP/JSON and local storage. Bootstrap a bounded recent period with `contractPublished`; update with `contractLastModified` using overlapping UTC windows and deduplication. Proposed overlap: seven days, configurable. Backfill/reconcile periodically because maximum lag and boundary semantics are unverified. Follow all pages and checkpoint only after success. Cache `findById` for targeted corroboration, not one extra call per row.
3. **AIC local extraction.** Reuse the four saved `.txt` files and PDFs. Later use local `pdftotext -layout` or a narrowly scoped optional Python PDF library; no OCR/network service is required for the current samples. A manifest maps each file to its exact official URL and dates. Human-reviewed scope records preserve page references, future wording, existing-supplier exclusions and rights restrictions. Do not attempt generic automatic table-to-opportunity conversion.
4. **Curated official seeds.** A small JSON file holds reviewed facts from Defence/ASA pages or verified official notices and permitted report exports. A source URL alone is a review candidate, not an opportunity. No unverified destination from the ASA hub becomes active automatically. Manual review is a real ongoing requirement; authoring a seed is not a copyright exemption.
5. **Explainable matching.** A local SME capability profile is matched to normalized work scope, activity and delivery location using controlled aliases and explicit exclusions. Eligibility remains separate. Show why each match occurred and why stronger relevance was withheld; do not score speculative records into the confirmed-open group.
6. **Three required outputs in `out/`.** Weekly filtered Markdown briefing; a searchable static HTML list with CSV and JSON equivalents; and a printable one-page capability-to-opportunity assessment. Each includes status, eligibility/unknowns, deadline, route and evidence, plus coverage limitations and source attribution. Awarded/context records must be visibly separate from current opportunities.
7. **Operate modestly.** Daily API refresh if available, weekly human seed review and briefing, monthly source/rights review, with configurable policies. A local scheduler is sufficient; no paid hosting, API subscription, live dashboard server or model inference is necessary.
8. **Test without network.** Derive small permitted CN fixtures from the saved responses and create clearly labelled synthetic edge cases. Keep restricted AIC text local; use original synthetic fixtures for public tests and opt-in local checks against the saved samples. Test incomplete pagination, amendments, staleness, deadlines, the registration trap, table defects, attribution and publication gating.

The first implementation should prove provenance and honest classification before breadth. Success is a useful, reproducible briefing that can say “no confirmed-open opportunities verified,” explain relevant future work and readiness actions, and direct the SME to the correct official route without inventing an opportunity or a right to reuse content.
