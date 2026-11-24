# Defence supply radar

An offline first, local evidence and matching tool for a fictional Henderson marine SME. It adds a structured view of source evidence, timing, eligibility and supplier readiness to ordinary ICN and AusTender research. It does not claim exclusive discovery, current open tender coverage, qualification, or a guarantee of work.

## Setup

Python 3.11+ is sufficient at runtime; application code uses the standard library. Pytest is only for development tests.

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
PATH=.venv/bin:$PATH python -m pytest -q
```

The command entry point is `python -m defence_radar`. `init` checks local config and creates the SQLite database and local directories. `--help`, builds, local AIC/seed imports and source checks are offline. Explicit AusTender ingestion can use the network.

## Offline fixture walkthrough

This fixture is a reduced CC BY 3.0 AU AusTender response. `page2.json` deliberately points to a missing next page; its chain must remain incomplete and cannot advance the live checkpoint. The terminal-only fixture is useful for a successful reproducible build:

```sh
python -m defence_radar init
python -m defence_radar ingest austender --saved-dir tests/fixtures/austender --offline
# The fixture includes an intentionally incomplete chain, so this returns exit 3.
python -m defence_radar build --profile examples/sme_profile.json --as-of 2026-11-24T12:00:00Z --week-ending 2026-11-22 --audience public --out out/fixture-demo --offline
```

To replay only the terminal response, copy `terminal.json` and `terminal.meta.json` into a local saved directory and pass it to `ingest austender`. Saved replay keeps original access times and never refreshes a live checkpoint. Outputs are UTF-8 files: briefing Markdown, work package JSON/CSV/HTML, assessment Markdown/HTML, coverage, and a manifest with hashes.

## Refresh and build

Online access occurs only when explicitly invoking `fetch` or `all`. Each request is serial, policy checked, paginated and bounded to 90 days. With no dates, refresh defaults to the prior 30 days; end time is current UTC rounded to seconds. Explicit `--start` and `--end` timestamps must include a timezone.

```sh
python -m defence_radar fetch --field contractLastModified --start 2026-10-25T00:00:00Z --end 2026-11-24T00:00:00Z
python -m defence_radar fetch --field contractLastModified --incremental --end 2026-11-24T00:00:00Z
python -m defence_radar all --start 2026-10-25T00:00:00Z --end 2026-11-24T00:00:00Z --profile examples/sme_profile.json --week-ending 2026-11-22 --audience public --out out/live-public/2026-11-22
python -m defence_radar build --profile examples/sme_profile.json --as-of 2026-11-24T12:00:00Z --week-ending 2026-11-22 --audience research --out out/research/2026-11-22 --offline
python -m defence_radar assess --profile examples/sme_profile.json --week-ending 2026-11-22 --out out/sample
python -m defence_radar inspect cn:example-id --offline
python -m defence_radar audit --offline
```

Incremental refresh uses the stored successful checkpoint with a seven-day overlap. An initial incremental refresh requires `--start`. A partial or failed window returns 3 and cannot advance its checkpoint, and does not make `all` build a bundle. Already completed windows remain available. Build is always offline; it can render old local evidence with visible coverage warnings. `--strict` refuses publication when relevant live coverage is unresolved, has no successful live refresh, or is over seven days old. Replays never count as live refresh. Disabled rights-held sources are expected coverage gaps.

All CLI database, raw input, and output paths must stay within this project; output bundles must be under `out/`. Defaults separate audience, profile and reporting date. `out/sample/` is reserved for public fictional-profile builds; real profiles cannot overwrite it. `pipeline.build_outputs` accepts arbitrary paths for embedding and tests. Avoid placing credentials or private files in project output directories.

## Review inputs and source limits

`config/sources.json` defines each source's access mode, rights status, allowed audiences, hosts, paths, licence or terms references and evidence. `config/official_seeds.json` holds manually reviewed records and disabled candidate links; seed review `content_sha256` currently binds `digest(record)`, with reviewer and review time. `config/aic_manifest.json` maps saved AIC documents to text/PDF hashes and review files. Each AIC scope review binds both the document `content_sha256` and `scope_sha256` (`digest(record)`). Recompute the record digest after any edit. Coverage checks the committed inventory against local text availability and reports disabled seed candidates; these checks do not refresh remote content.

AusTender packages that declare CC BY 3.0 AU can be attributed and transformed under that licence. AIC records remain rights-held for both public and research output; local extraction is not reuse permission. ASA/manual references remain unverified unless reviewed. WA sources and ICN are disabled for automated crawling. AusTender is a contract-notice source, not a current open opportunity feed. There is no current APP/ATM open feed in this implementation, and coverage always reports that gap. Review official notices and routes manually; a contract award value is not subcontract spend.

Manual cadence: review the source policies, candidate links, AIC revisions and held items weekly; verify any apparent open notice and its deadline/route directly before acting; then build and inspect the briefing and assessment. A richer product adds evidence-linked classification, capability fit, eligibility unknowns, deltas and source-health visibility alongside ICN. It does not replace ICN or agency portals.

## Output and recovery

Build files are generated in a sibling temporary directory, checked, then installed with a backup of the prior bundle. The build baseline is saved in the same SQLite transaction; on any error, including repository failure, the previous bundle and baseline remain intact. Rebuilding a profile/audience/period uses only a strictly earlier period as its delta baseline and replaces the same-period baseline only after success. The output manifest records explicit effective time, period, profile hash, versions, snapshot hashes, audience, held/excluded counts and artifact hashes, and excludes its own hash. Coverage omits private paths and raw error strings.

Exit codes: 0 means the requested operation completed; 2 means invalid input, policy or configuration; 3 means a partial/failed refresh or integrity/strict coverage failure. For exit 3, inspect `audit`, resolve the source gap or replay a complete saved chain, then build offline. A failed window does not erase the last complete output or advance its checkpoint; earlier completed windows may already have advanced it.

No scheduler, notification, or background refresh is activated. Use an operator-controlled schedule only after separate review and authorization.

Source links: [AusTender API documentation](https://github.com/austender/austender-ocds-api), [CC BY 3.0 AU](https://creativecommons.org/licenses/by/3.0/au/), [official AIC index](https://www.defence.gov.au/business-industry/finding-opportunities/public-australian-industry-capability-plans). Each permitted record retains query/notice identifiers, source access date, snapshot hash and attribution. Data are filtered and classified; no Commonwealth endorsement is implied. CSV list cells use semicolons (rich requirements and sources use JSON); potentially executable spreadsheet cells receive a leading apostrophe. JSON preserves original values.

Timezone conversion requires system tzdata including Australia/Perth and Australia/Sydney. Date-only, masked and ambiguous-zone deadlines cannot establish an open opportunity. Optional PDF extraction needs local Poppler; supplied text and the default offline tests do not.

If interrupted during the two directory renames, a sibling `.NAME.backup-PID` retains the previous output. Restore it before rerunning if the destination is absent. Ordinary exceptions are rolled back automatically. This directory swap is not a cross-filesystem or power-loss transaction.
