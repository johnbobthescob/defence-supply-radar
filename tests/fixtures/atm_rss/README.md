# Synthetic ATM RSS fixtures

`synthetic-current-atm.xml` is SYNTHETIC TEST DATA. Titles, ATM IDs, links and dates are invented; none are real
AusTender notices. The real feed's item schema has not been verified, so this file only exercises the parser's
defensive handling of the fields we expect (title, link, description, pubDate, guid).

`doctype.xml` is a deliberately malicious feed with an ENTITY declaration; the parser must reject it.

Test clock: 2026-11-25T03:00:00Z.
