"""Self-contained, print-friendly HTML weekly briefing (no external assets, no scripts)."""
import html

from .common import (ATM_URL, AUSTENDER_ATTRIBUTION, CLASS_BADGE_TEXT, ICN_URL, WORK_PACKAGES_PAGE, awst_date, awst_stamp,
                     austender_present, briefing_model, buyer_unit, clean_reason, fit_label, money, notice_ref, notice_url,
                     open_gap_text, record_amount, safe_url, signed_stamp, source_refresh_rows, supplier_text, top_reasons,
                     all_reasons, band_for, closing_label)

CSS = """
:root{--navy:#102b46;--teal:#087e83;--ink:#1b2b38;--muted:#4a5c69;--line:#d3dde2;--paper:#f3f7f8;--amber:#8a5200;--award:#5b3a8c}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
.wrap{max-width:860px;margin:0 auto;padding:0 20px}
header.top{background:var(--navy);color:#fff;border-bottom:5px solid var(--teal)}
header.top .wrap{padding-top:28px;padding-bottom:22px}
header.top h1{margin:0 0 6px;font-size:1.85rem;line-height:1.2;letter-spacing:-.01em}
header.top p{margin:2px 0;color:#d6e4ee}
header.top .profile{font-size:1.1rem;color:#fff;font-weight:600}
main{padding-top:8px;padding-bottom:24px}
section{margin:28px 0}
h2{font-size:1.3rem;line-height:1.25;color:var(--navy);margin:0 0 12px;padding-bottom:6px;border-bottom:2px solid var(--teal)}
h3{font-size:1.05rem;margin:18px 0 8px;color:var(--navy)}
p{margin:8px 0}
a{color:#06607a}
.summary{background:#fff;border:1px solid var(--line);border-left:6px solid var(--teal);border-radius:6px;padding:14px 20px}
.summary ul{margin:0;padding-left:20px}.summary li{margin:7px 0}
.card{background:#fff;border:1px solid var(--line);border-left:6px solid #1e7d4a;border-radius:6px;padding:14px 18px;margin:12px 0;break-inside:avoid}
.card.future{border-left-color:#2a64a8}.card.spec{border-left-color:var(--amber)}
.card h3{margin:0 0 4px;font-size:1.1rem}
.meta{color:var(--muted);font-size:.93rem;margin:2px 0}
.badge{display:inline-block;border-radius:999px;padding:1px 10px;font-size:.82rem;font-weight:700;border:1px solid transparent;white-space:nowrap}
.b-open{background:#e0f3e8;color:#0d5a31;border-color:#9fd3b3}.b-future{background:#e3edf9;color:#1b4a85;border-color:#a6c1e4}
.b-spec{background:#fdf0d8;color:var(--amber);border-color:#e6c88f}
.b-award{background:var(--award);color:#fff}
.b-fit{background:#e6f4f4;color:#05575b;border-color:#8bcac9}
.reasons{margin:6px 0 6px;padding-left:20px}.reasons li{margin:2px 0}
.respond{background:#f1f8f8;border-radius:5px;padding:8px 12px;margin-top:8px;font-size:.96rem}
.empty{background:#fff;border:1px dashed #7f98a6;border-radius:6px;padding:14px 18px}
.empty ul{margin:6px 0 0;padding-left:20px}
.award-banner{background:var(--award);color:#fff;border-radius:6px;padding:10px 16px;margin:0 0 12px}
.award-banner strong{letter-spacing:.06em}
table{border-collapse:collapse;width:100%;font-size:.9rem;background:#fff;margin:6px 0 14px}
caption{text-align:left;font-weight:700;color:var(--navy);padding:6px 0}
th,td{border:1px solid var(--line);padding:5px 8px;text-align:left;vertical-align:top}
th{background:#e8f0f3;color:var(--navy)}
td.num,th.num{text-align:right;white-space:nowrap}
.award-row{background:#fff;border:1px solid var(--line);border-left:5px solid var(--award);border-radius:5px;padding:9px 14px;margin:8px 0;break-inside:avoid}
.award-row .t{font-weight:700}
.award-row .why{color:var(--muted);font-size:.92rem;margin-top:3px}
.award-row small{color:var(--muted)}
ol.actions{padding-left:22px}ol.actions li{margin:9px 0}
.warn{color:#7a2b00}
footer{border-top:2px solid var(--navy);margin-top:30px;padding:16px 0 30px;color:var(--muted);font-size:.88rem}
footer h2{font-size:1rem;border:0}
.note{color:var(--muted);font-size:.92rem}
:focus-visible{outline:3px solid #f2ac42;outline-offset:2px}
@page{size:A4;margin:14mm 13mm}
@media (max-width:560px){header.top h1{font-size:1.5rem}.wrap{padding:0 14px}}
@media print{
body{background:#fff;font-size:10.5pt;line-height:1.42}
.wrap{max-width:none;padding:0}
header.top{-webkit-print-color-adjust:exact;print-color-adjust:exact}
header.top .wrap{padding:14px 16px 12px}
.badge,.award-banner,.b-award,th,.card,.award-row,.summary{-webkit-print-color-adjust:exact;print-color-adjust:exact}
section{margin:16px 0;break-inside:auto}
h2,h3{break-after:avoid}
.card,.award-row,table,tr,.empty,.summary{break-inside:avoid}
a{color:#06607a;text-decoration:none}
a.pl::after{content:" (" attr(href) ")";font-size:.82em;color:#333;word-break:break-all}
.nopr{display:none}
}
"""


def _e(v): return html.escape(str(v if v is not None else ""), quote=True).replace("&#x27;", "&apos;")


def _a(label, url, cls=""):
    safe = safe_url(url)
    c = f' class="{cls}"' if cls else ""
    return f'<a{c} href="{_e(safe)}">{_e(label)}</a>' if safe else _e(label)


def _fit_badge(match):
    s = int(match.get("score") or 0)
    return f'<span class="badge b-fit" title="Relevance to your declared capabilities, not eligibility">{_e(fit_label(match))}</span>'


def _open_card(row, kind="open"):
    rec, m = row["record"], row["match"]
    route = rec.get("application_route") or {}
    cls = {"open": "", "future": " future", "spec": " spec"}[kind]
    badge = {"open": ('b-open', CLASS_BADGE_TEXT["confirmed_open"]), "future": ('b-future', CLASS_BADGE_TEXT["published_future_scope"]),
             "spec": ('b-spec', "Speculative — no buyer commitment")}[kind]
    lis = "".join(f"<li>{_e(clean_reason(r))}</li>" for r in top_reasons(m, 3)) or "<li>No scoring reasons recorded.</li>"
    close = ""
    if kind == "open" or rec.get("close_at_utc") or rec.get("close_raw"):
        awst = awst_stamp(rec.get("close_at_utc")) if rec.get("close_at_utc") else "not published"
        raw = f' <span class="note">(published as: {_e(rec["close_raw"])})</span>' if rec.get("close_raw") else ""
        close = f'<p class="meta"><strong>Closes:</strong> {_e(awst)}{raw}</p>'
    route_url = route.get("url")
    if kind == "open":
        acct = {"yes": "An account/registration on the portal is required to respond.", "no": "No portal account is required."}.get(str(route.get("account_required")), "Check whether a portal account is required.")
        resp = (f'<div class="respond"><strong>How to respond:</strong> '
                + (_a(route_url, route_url, "pl") if safe_url(route_url) else (_e(route.get("email")) if route.get("email") else "No route published; use the notice page"))
                + f' &middot; {_e(acct)}'
                + (f' {_e(route.get("instructions"))}' if route.get("instructions") else "") + "</div>")
    else:
        link = route_url or notice_url(rec)
        resp = f'<div class="respond"><strong>Where to enquire:</strong> {_a(link, link, "pl") if safe_url(link) else "see source notice"}</div>'
    summary = f'<p class="meta">{_e(rec.get("summary"))}</p>' if rec.get("summary") and rec.get("summary") != rec.get("title") else ""
    return (f'<article class="card{cls}"><h3>{_e(rec.get("title", "Untitled"))}</h3>'
            f'<p class="meta"><span class="badge {badge[0]}">{_e(badge[1])}</span> {_fit_badge(m)}</p>'
            f'<p class="meta"><strong>Buyer:</strong> {_e(buyer_unit(rec))}'
            + (f" ({_e(rec.get('buyer'))})" if rec.get("buyer") and rec.get("buyer") != buyer_unit(rec) else "") + "</p>"
            + close + summary + f'<ul class="reasons">{lis}</ul>{resp}</article>')


def _empty_open(cov):
    return ('<div class="empty"><p><strong>No verified open tenders were imported this week.</strong></p>'
            f'<p>{_e(open_gap_text(cov))} Import the feed from {_a(ATM_URL, ATM_URL)} to have open tenders scored here. '
            'This does not mean nothing is open.</p><p>Where to check now:</p><ul>'
            f'<li>{_a("AusTender Current ATMs", ATM_URL)} (filter: Department of Defence)</li>'
            f'<li>{_a("ICN Gateway", ICN_URL)} for Henderson-precinct work packages from primes</li></ul></div>')


def _award_row(row):
    rec, m = row["record"], row["match"]
    ref = notice_ref(rec)
    amount = record_amount(rec)
    reasons = all_reasons(m)
    why = "; ".join(clean_reason(r) for r in top_reasons(m, 2))
    detail = "; ".join(reasons[:2])
    return (f'<div class="award-row"><div class="t"><span class="badge b-award">AWARDED</span> {_e(rec.get("title", "Untitled"))}</div>'
            f'<div class="meta">{_a(ref, notice_url(rec))} &middot; {_e(supplier_text(rec))} &middot; {_e(buyer_unit(rec))}'
            f' &middot; {_e(money(amount) if amount is not None else "value n/a")} &middot; signed {_e(awst_date(signed_stamp(rec)))} '
            f'&middot; {_fit_badge(m)}</div>'
            f'<div class="why" title="{_e(detail)}"><strong>Why relevant:</strong> {_e(why or "No reasons recorded")} '
            f'<small>({_e(", ".join(r.split(" ", 1)[0] for r in reasons if r[:1] in "+-")[:60])})</small></div></div>')


def _table(caption, heads, rows, numeric=()):
    th = "".join(f'<th scope="col"{" class=num" if i in numeric else ""}>{_e(h)}</th>' for i, h in enumerate(heads))
    body = "".join("<tr>" + "".join(f'<td{" class=num" if i in numeric else ""}>{_e(c)}</td>' for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f"<table><caption>{_e(caption)}</caption><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>"


def render_briefing_html(payload):
    mdl = briefing_model(payload)
    cov, market, week = mdl["cov"], mdl["market"], mdl["week"]
    profile = (payload.get("profile") or {}).get("name") or "Your business"
    subtitle_week = f"Week {week.get('start', '')} to {week.get('end', payload.get('period', ''))} (AWST)"
    parts = [f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
             f'<title>Defence Supply Radar — weekly briefing — {_e(payload.get("period", ""))}</title><style>{CSS}</style></head><body>',
             f'<header class="top"><div class="wrap"><h1>Defence Supply Radar — weekly briefing</h1>'
             f'<p class="profile">{_e(profile)}</p><p>{_e(subtitle_week)}</p><p>Data as of {_e(awst_stamp(payload.get("as_of")))}</p></div></header>'
             '<main class="wrap">']
    # a/b summary
    parts.append('<section id="summary" aria-labelledby="h-summary"><h2 id="h-summary">Executive summary</h2><div class="summary"><ul>'
                 + "".join(f"<li>{_e(b)}</li>" for b in mdl["bullets"]) + "</ul></div></section>")
    # c open
    parts.append('<section id="open" aria-labelledby="h-open"><h2 id="h-open">Open opportunities</h2>')
    parts.append("".join(_open_card(r) for r in mdl["open"]) if mdl["open"] else _empty_open(cov))
    parts.append("</section>")
    # d future
    parts.append('<section id="future" aria-labelledby="h-future"><h2 id="h-future">Upcoming and future scope</h2>')
    if mdl["future"] or mdl["speculative"]:
        parts.append("".join(_open_card(r, "future") for r in mdl["future"]))
        if mdl["speculative"]:
            parts.append("<h3>Speculative — no buyer commitment</h3>" + "".join(_open_card(r, "spec") for r in mdl["speculative"]))
    else:
        parts.append('<div class="empty"><p>No published future work scope matched your capabilities in this build. '
                     f'Primes publish many Henderson work packages on {_a("ICN Gateway", ICN_URL)}, which this tool does not import.</p></div>')
    parts.append("</section>")
    # e winning
    parts.append('<section id="winning" aria-labelledby="h-win"><h2 id="h-win">Who is winning (awarded contracts — not open opportunities)</h2>'
                 '<div class="award-banner"><strong>AWARDED</strong> &mdash; every item in this section is a contract that has already been won. '
                 'Use it to find teaming and subcontract leads, not to bid.</div>')
    parts.append(f'<p><strong>{market.get("awards_in_week", 0)} relevant awards</strong> published this week, '
                 f'<strong>{_e(money(market.get("total_value", 0)))}</strong> total head-contract value. '
                 f'<span class="note">{_e(market.get("note", ""))}</span></p>')
    sup = (market.get("suppliers") or [])[:8]
    if sup:
        parts.append(_table("Top suppliers by contract value (awarded this week)", ["Supplier", "Location", "Awards", "Value", "Example work"],
                            [(s["name"].title() if s["name"].isupper() else s["name"], ", ".join(x for x in (s.get("locality"), s.get("region")) if x) or "n/a",
                              s["count"], money(s.get("value", 0)), (s.get("titles") or [""])[0]) for s in sup], numeric=(2, 3)))
    buy = (market.get("buyers") or [])[:6]
    if buy:
        parts.append(_table("Most active buyer units", ["Buyer unit", "Awards", "Value"], [(b["name"], b["count"], money(b.get("value", 0))) for b in buy], numeric=(1, 2)))
    caps = sorted(market.get("capabilities") or [], key=lambda c: (-c.get("count", 0), c.get("label", "")))
    if caps:
        parts.append(_table("Awards by capability area", ["Capability area", "Awards", "Value"], [(c["label"], c["count"], money(c.get("value", 0))) for c in caps], numeric=(1, 2)))
    if mdl["top_awards"]:
        parts.append(f'<h3>Top {len(mdl["top_awards"])} awards by fit with your capabilities</h3>' + "".join(_award_row(r) for r in mdl["top_awards"]))
    elif not sup:
        parts.append("<p>No relevant awarded contracts were published this week.</p>")
    parts.append(f'<p>Full list of {len(mdl["awarded_week"])} awarded notices this week and filters: {_a("work-packages page", WORK_PACKAGES_PAGE)}.</p></section>')
    # f actions
    parts.append('<section id="actions" aria-labelledby="h-act"><h2 id="h-act">Recommended actions this week</h2><ol class="actions">')
    for a in mdl["actions"]:
        link = f' {_a("Open link", a.get("url"), "pl")}' if safe_url(a.get("url")) else ""
        parts.append(f"<li>{_e(a.get('text'))}{link}</li>")
    parts.append("</ol>" + ("" if mdl["actions"] else "<p>No actions generated.</p>") + "</section>")
    # g coverage
    held = cov.get("held") or {}
    by_src = held.get("by_source") or {}
    parts.append('<section id="coverage" aria-labelledby="h-cov"><h2 id="h-cov">Coverage and data quality</h2>'
                 f'<p><strong>Open-tender gap:</strong> {_e(open_gap_text(cov))}</p>')
    rows = source_refresh_rows(cov)
    if rows: parts.append(_table("Sources and last successful refresh (AWST)", ["Source", "Access", "Last refresh / status"], rows))
    held_txt = "; ".join(f"{k}: {v}" for k, v in sorted(by_src.items())) or "none"
    parts.append(f'<p><strong>Records held back:</strong> {held.get("total", 0)} (by source: {_e(held_txt)}). Held records are withheld for rights or review reasons and are not shown.</p>'
                 f'<p><strong>Unrelated records excluded:</strong> {cov.get("excluded_irrelevant", 0)} agency contract notices scored below the relevance threshold.</p>')
    if cov.get("warnings"):
        parts.append('<p><strong>Warnings</strong></p><ul class="warn">' + "".join(f"<li>{_e(w)}</li>" for w in cov["warnings"]) + "</ul>")
    parts.append('<p class="note">Scores explain relevance to your declared capabilities; they are not eligibility or approval.</p></section>')
    # h footer
    rv = payload.get("rule_versions") or {}
    attrs = list(payload.get("attribution") or [])
    if austender_present(payload) and AUSTENDER_ATTRIBUTION not in attrs: attrs.append(AUSTENDER_ATTRIBUTION)
    parts.append('</main><footer><div class="wrap"><h2>Attribution</h2>' + "".join(f"<p>{_e(a)}</p>" for a in attrs)
                 + f'<p>Generated by Henderson Defence Supply-Chain Radar &middot; classification {_e(rv.get("classification", "n/a"))}, matching {_e(rv.get("matching", "n/a"))}, taxonomy v{_e(payload.get("taxonomy_version", "n/a"))}.</p>'
                 '</div></footer></body></html>')
    return "".join(parts)
