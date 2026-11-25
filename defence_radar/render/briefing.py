"""Plain-text-friendly Markdown weekly briefing; mirrors the HTML briefing structure."""
from .common import (ATM_URL, AUSTENDER_ATTRIBUTION, ICN_URL, WORK_PACKAGES_PAGE, all_reasons, austender_present, awst_date,
                     awst_stamp, briefing_model, buyer_unit, clean_reason, fit_label, md_inline as t, money, notice_ref,
                     notice_url, open_gap_text, record_amount, safe_url, signed_stamp, source_refresh_rows, supplier_text,
                     top_reasons)


def _link(label, url):
    u = safe_url(url)
    return f"[{t(label)}]({u.replace(')', '%29').replace('(', '%28')})" if u else t(label)


def _card(row, kind):
    rec, m = row["record"], row["match"]
    route = rec.get("application_route") or {}
    lines = [f"### {t(rec.get('title', 'Untitled'))}",
             f"**{fit_label(m)}** | Buyer: {t(buyer_unit(rec))}"]
    if kind == "open":
        close = awst_stamp(rec.get("close_at_utc")) if rec.get("close_at_utc") else "not published"
        raw = f" (published as: {t(rec['close_raw'])})" if rec.get("close_raw") else ""
        lines.append(f"Closes: {t(close)}{raw}")
    elif kind == "spec":
        lines.append("Speculative - no buyer commitment.")
    lines.append("")
    lines += [f"- {t(clean_reason(r))}" for r in top_reasons(m, 3)]
    link = route.get("url") or notice_url(rec)
    if kind == "open":
        acct = {"yes": "account required", "no": "no account required"}.get(str(route.get("account_required")), "check whether an account is required")
        lines += ["", f"How to respond: {_link(link, link) if safe_url(link) else t(route.get('email') or 'see notice')} ({acct})."]
    else:
        lines += ["", f"Where to enquire: {_link(link, link) if safe_url(link) else 'see source notice'}"]
    return lines + [""]


def render_briefing(payload):
    mdl = briefing_model(payload)
    cov, market, week = mdl["cov"], mdl["market"], mdl["week"]
    L = ["# Defence Supply Radar — weekly briefing", "",
         f"**{t((payload.get('profile') or {}).get('name') or 'Your business')}**  ",
         f"Week {week.get('start', '')} to {week.get('end', payload.get('period', ''))} (AWST)  ",
         f"Data as of {awst_stamp(payload.get('as_of'))}", "",
         "## Executive summary", ""] + [f"- {t(b)}" for b in mdl["bullets"]] + ["", "## Open opportunities", ""]
    if mdl["open"]:
        for r in mdl["open"]: L += _card(r, "open")
    else:
        L += ["**No verified open tenders were imported this week.**", "",
              t(open_gap_text(cov)) + f" Import the feed from {ATM_URL} to have open tenders scored here. This does not mean nothing is open.", "",
              "Where to check now:", "", f"- {_link('AusTender Current ATMs', ATM_URL)} (filter: Department of Defence)",
              f"- {_link('ICN Gateway', ICN_URL)} for Henderson-precinct work packages from primes", ""]
    L += ["## Upcoming and future scope", ""]
    if mdl["future"] or mdl["speculative"]:
        for r in mdl["future"]: L += _card(r, "future")
        for r in mdl["speculative"]: L += _card(r, "spec")
    else:
        L += ["No published future work scope matched your capabilities in this build.", ""]
    L += ["## Who is winning (awarded contracts — not open opportunities)", "",
          "**AWARDED** - every item here is a contract that has already been won. Use it to find teaming and subcontract leads, not to bid.", "",
          f"{market.get('awards_in_week', 0)} relevant awards published this week, {money(market.get('total_value', 0))} total head-contract value. {t(market.get('note', ''))}", ""]
    sup = (market.get("suppliers") or [])[:8]
    if sup:
        L += ["| Supplier | Location | Awards | Value | Example work |", "|---|---|---:|---:|---|"]
        for s in sup:
            loc = ", ".join(x for x in (s.get("locality"), s.get("region")) if x) or "n/a"
            nm = s["name"].title() if s["name"].isupper() else s["name"]
            L.append(f"| {t(nm)} | {t(loc)} | {s['count']} | {money(s.get('value', 0))} | {t((s.get('titles') or [''])[0])} |")
        L.append("")
    if market.get("buyers"):
        L += ["| Buyer unit | Awards | Value |", "|---|---:|---:|"] + [f"| {t(b['name'])} | {b['count']} | {money(b.get('value', 0))} |" for b in market["buyers"][:6]] + [""]
    caps = sorted(market.get("capabilities") or [], key=lambda c: (-c.get("count", 0), c.get("label", "")))
    if caps:
        L += ["| Capability area | Awards | Value |", "|---|---:|---:|"] + [f"| {t(c['label'])} | {c['count']} | {money(c.get('value', 0))} |" for c in caps] + [""]
    if mdl["top_awards"]:
        L += [f"### Top {len(mdl['top_awards'])} awards by fit", ""]
        for r in mdl["top_awards"]:
            rec, m = r["record"], r["match"]
            amt = record_amount(rec)
            why = "; ".join(clean_reason(x) for x in top_reasons(m, 2))
            L += [f"- **{t(rec.get('title', 'Untitled'))}** - {_link(notice_ref(rec), notice_url(rec))}, {t(supplier_text(rec))}, {t(buyer_unit(rec))}, "
                  f"{money(amt) if amt is not None else 'value n/a'}, signed {awst_date(signed_stamp(rec))}, {fit_label(m)}",
                  f"  Why relevant: {t(why or 'none recorded')}"]
        L.append("")
    L += [f"Full list of {len(mdl['awarded_week'])} awarded notices this week: {WORK_PACKAGES_PAGE}", "", "## Recommended actions this week", ""]
    for i, a in enumerate(mdl["actions"], 1):
        L.append(f"{i}. {t(a.get('text'))}" + (f" {_link('Link', a['url'])}" if safe_url(a.get("url")) else ""))
    held = cov.get("held") or {}
    held_txt = "; ".join(f"{k}: {v}" for k, v in sorted((held.get("by_source") or {}).items())) or "none"
    L += ["", "## Coverage and data quality", "", f"**Open-tender gap:** {t(open_gap_text(cov))}", "", "Sources (last successful refresh, AWST):", ""]
    L += [f"- {t(i)} ({t(m)}): {t(s)}" for i, m, s in source_refresh_rows(cov)]
    L += ["", f"Records held back: {held.get('total', 0)} (by source: {t(held_txt)}).",
          f"Unrelated records excluded: {cov.get('excluded_irrelevant', 0)}."]
    if cov.get("warnings"):
        L += ["", "Warnings:", ""] + [f"- {t(w)}" for w in cov["warnings"]]
    L += ["", "Scores explain relevance to your declared capabilities; they are not eligibility or approval.", "", "---", ""]
    attrs = list(payload.get("attribution") or [])
    if austender_present(payload) and AUSTENDER_ATTRIBUTION not in attrs: attrs.append(AUSTENDER_ATTRIBUTION)
    L += [t(a) + "  " for a in attrs]
    rv = payload.get("rule_versions") or {}
    L += [f"Generated by Henderson Defence Supply-Chain Radar; classification {rv.get('classification', 'n/a')}, matching {rv.get('matching', 'n/a')}, taxonomy v{payload.get('taxonomy_version', 'n/a')}.", ""]
    return "\n".join(L)
