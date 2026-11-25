# Open tender source: AusTender current ATM RSS feed

## What it is
The Department of Finance publishes an RSS feed of all AusTender approaches to market (ATMs) that are currently open:
https://www.tenders.gov.au/public_data/rss/rss.xml. The radar source id is `austender_atm`.

## Licence evidence
The data.gov.au dataset "Latest Approaches to Markets listed on AusTender"
(https://data.gov.au/data/dataset/efe713db-f91e-4708-9edb-e3d3e321cfee, organisation Department of Finance) lists the feed
under Creative Commons Attribution 3.0 Australia (https://creativecommons.org/licenses/by/3.0/au/) and states it is
"updated daily after business hours" (checked via the CKAN API on 2026-11-25). The policy is in `config/sources.json`.

## Why this is compliant
- It is an official open-data feed published for reuse; no login is needed.
- Attribution is preserved on every record (`ATTRIBUTION` in `defence_radar/ingest/atm_rss.py`).
- Only feed fields are used. ATM pages and ATM documents are not scraped, mirrored or redistributed.
- The ATM page on AusTender remains the authority; records link there and say so.

## Limitation: automated access returns 403
From the development host the URL returns a CloudFront 403. We do not bypass this (no proxies, browser automation or
header spoofing). The primary path is therefore a local import of a copy saved by the operator. `--fetch` makes one plain
policy-checked GET and records a failed run honestly if it is refused.

## Operator workflow
1. Open the RSS URL in your own browser and save it as `data/inbox/atm-YYYY-MM-DD.xml`.
2. `python -m defence_radar ingest atm-rss --file data/inbox/atm-YYYY-MM-DD.xml --accessed-at <time you saved it, ISO with offset>`
   (without `--accessed-at` the file modification time is used, which is wrong if the file was copied later).
3. Run `build` as usual.

## Freshness
A listing counts as `confirmed_open` only if the feed copy is 48 hours old or less and the close time has not passed.
Older copies are `held` until the feed is re-imported. Close times are converted only when the feed states
"(ACT Local Time)" (treated as Australia/Sydney); date-only or other zones are kept raw with no instant.

## Caveats
The exact item schema of the real feed has not been verified; the parser treats every description field as optional.
`tests/fixtures/atm_rss/` is synthetic test data (invented titles and IDs), not real notices. Re-check real output
after the first genuine import.

## Other sources considered and rejected
- AusTender HTML / ATM pages: blocked to automated clients, terms unverified.
- WA Tenders / wa.gov.au: terms forbid automated access.
- ICN Gateway: terms of use; no bulk licence.
- Defence / ASA pages: no reuse permission established.
- Commercial aggregators and Apify scrapers: not official, and they rely on scraping.
