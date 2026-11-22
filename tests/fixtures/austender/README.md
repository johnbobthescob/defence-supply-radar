# Australian Tenders (AusTender) OCDS fixtures

These reduced JSON fixtures are derived from saved responses to the Australian Government AusTender API. The source material is made available under the **Creative Commons Attribution 3.0 Australia (CC BY 3.0 AU)** licence. Attribution: Australian Government, AusTender, [AusTender API](https://api.tenders.gov.au/ocds/).

The fixtures retain selected release records and their `ocid`, `id`, contract descriptions and titles, periods, values, statuses, and tags. Relevant root response fields are retained, including pagination `links` exactly as provided by the source response. Party contact points and addresses are removed. Supplier names and identifiers are removed from party and award supplier records; procuring agency names and identifiers remain to identify the public buyer. These transformations make the records reduced test fixtures and do not represent full API responses.

`by-id.json` preserves the source response's actual shape: it has no top-level `license` field. Do not infer a licence field for that response from the other fixtures.

`page2.json` is intentionally an incomplete extract of the second source page. Its pagination links, including `next`, remain intact and must not be interpreted as a terminal page. The terminal response fixture is `terminal.json`.

Each `.meta.json` records the source request and response status, access time from the HTTP `Date` header, and only the `Content-Type` and `Date` headers. `provenance.json` maps each fixture to its source URL, original access time, SHA-256 of the original saved body, original release count, and reduction description. These fixtures are synthetic reductions for automated tests only; they are not complete procurement records and must not be used as a data feed or for operational, procurement, or decision-making purposes.
