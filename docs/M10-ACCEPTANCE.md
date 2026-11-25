# M10 — Real-data acceptance and pilot handoff

Recorded 25 November 2026 (AWST) against commit `7ec0719` plus the empty-window fix in the M10 commit.
PLAN.md §9 defines M10 as: bounded live CN smoke, local four-sample check, reviewed seed/profile run and final evidence audit.

## Acceptance criteria

| Criterion (PLAN.md §9) | Result | Evidence |
|---|---|---|
| Full offline suite passes | **Pass** | `python -m pytest -q` passes 86 tests, 0 failures, with no network access. |
| Successful bounded live CN refresh is evidenced or explicitly remains blocked | **Pass** | `fetch --field contractPublished --start 2026-11-16T00:00:00Z --end 2026-11-24T00:00:00Z` ran at 2026-11-25T00:48Z and exited 0. All 8 daily windows completed: 22 pages, 1,226 releases. `audit` reports `incomplete_runs: 0` and `integrity: ok`. |
| All three output types generated from real permitted data | **Pass** (with defects listed below) | `build --strict --audience public` and `--audience research` both produced the briefing, work packages (JSON/CSV/HTML) and the assessment, using only CC BY 3.0 AU AusTender contract notices. |
| Synthetic demonstrations stay in separate test outputs | **Pass** | Fixtures live only under `tests/fixtures/`. Real builds read only the SQLite store populated by live fetches. The profile is clearly marked `fictional: true`. |
| Permission holds and open-input gap remain visible | **Pass** | Coverage holds 6 records: 4 AIC records (rights-restricted) and 2 AusTender records held for review. Coverage warnings state that the APP/ATM open-tender feed is unavailable and that WA, ICN and the directory are disabled. |
| No public/commercial launch claim | **Pass** | README and outputs describe a local pilot. No launch claim is made. |

## Bug found and fixed during live acceptance

On days with no notices (here Saturday 21 Nov UTC), the AusTender CN API returns **HTTP 400** with body
`{"errorCode": 100, "message": "No Records found for Date Range [...]"}`. Before this fix the client counted that as a failed window. The failed window then pinned the incremental checkpoint on every weekend and made `all` and `--strict` refuse to build.
Now that exact documented body completes the window with zero records, and the response is saved as evidence. Any other 400 still fails. Tests: `test_empty_window_400_errorcode_100_completes_with_zero_records` and `test_other_400_still_fails`.

A second suspicion was checked and ruled out. The 17 Nov window returned exactly 100 releases with no pagination links. Splitting it into 6-hour windows gave 70, 7 and 23 releases, which also sum to 100, so the count is genuine and not a silent cap.

## Four-sample (AIC) and seed check

- `ingest aic`: all 4 saved AIC documents load with matching hashes: Austal SSA, Hunter, LM2500 and RMP West. None are missing. All 4 remain **held** because Defence copyright gives no distribution permission. Exit 3 signals those holds. It is not an error.
- `ingest seeds`: 7 official candidate links, all disabled pending review, so none imported. This is expected. No reviewed seed claims current availability.

## Known output defects carried into the post-M10 work

The acceptance build showed problems that do not breach the rights or evidence gates but make the product much less useful. They are fixed in the following commits:

1. Every work-package row has `status_class: null`. CN context records have no explicit display state.
2. Every match score is 0. Scope tagging required a marine keyword in the text, and UNSPSC codes were ignored.
3. Fit lines print escaped Python dicts.
4. Source links point at OCDS API pages, not the human AusTender notice page.
5. The briefing filename uses the UTC as-of date, not the AWST week-ending period.

## Pilot handoff notes

- Weekly operator routine: `fetch --incremental` (or a bounded `--start/--end`), then `build --strict`. Read the briefing. Verify anything actionable on AusTender directly.
- The AusTender website (`www.tenders.gov.au`) returns CloudFront 403 to this host, so links to notice pages could not be checked automatically. API data was used to verify the URL format (see the briefing link commit).
