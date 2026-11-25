"""Short printable assessment of the strongest actionable records."""
import html
from .common import (closing_label, eligibility_label, md_inline as md_text, safe_url, source_summaries, status_label, fit_label,
                     all_reasons, clean_reason, notice_url, notice_ref, api_url, ATM_URL, awst_stamp)


def _e(v): return html.escape(str(v if v is not None else ""), quote=True)
def _list(v): return "; ".join(map(str, v or [])) or "None recorded"
def _link(label, url):
    u = safe_url(url)
    return f'<a href="{_e(u)}">{_e(label)}</a>' if u else _e(label)

def _teaming(payload):
    return [a for a in payload.get("actions", []) if a.get("kind") == "teaming"][:3]


def _selected(payload):
    rows = [r for r in payload.get("rows", []) if r.get("match", {}).get("shortlist") and r["record"].get("status_class") in {"confirmed_open", "published_future_scope"}]
    rows.sort(key=lambda r: r["match"].get("score", 0), reverse=True)
    selected, budget = [], 210  # reserve room for heading, coverage and attribution
    for row in rows:
        rec, match = row["record"], row["match"]
        route = rec.get("application_route") or {}
        src = source_summaries(rec)
        words = sum(len(str(x or "").split()) for x in (
            rec.get("title"), rec.get("classification_reason"), rec.get("close_raw"),
            route.get("instructions"), rec.get("conditions"), rec.get("eligibility"),
            match.get("missing_capabilities"), match.get("exclusions"),
            [(s.get("source_id"), s.get("url"), s.get("accessed_at"), s.get("licence_url")) for s in src])) + 65
        if len(selected) < 3:
            selected.append(row); budget += words
    return selected

def render_assessment_md(payload):
    cov = payload.get("coverage", {}); rows = _selected(payload)
    lines = [f"# Defence supply assessment — {payload.get('period','')}", f"As of {awst_stamp(payload.get('as_of'))}.", f"Profile: {md_text(payload.get('profile', {}).get('name', 'Private profile'))}.", "",
             f"Coverage: {cov.get('confirmed_open',0)} confirmed open; {cov.get('held',{}).get('total',0)} held; {cov.get('context_records',0)} context. This assessment complements ICN by separating evidence, timing, eligibility and context; it makes no exclusive discovery claim.", ""]
    if not rows:
        lines += ["## No verified shortlist matches", "No current or published-future records have enough permitted evidence for a capability shortlist. This does not establish that no opportunity exists.", "", "Next verification: check current official AusTender and relevant agency procurement notices, confirm source coverage and refresh date, then verify eligibility and submission route directly."]
        leads = _teaming(payload)
        if leads:
            lines += ["", "### Awarded context: teaming leads (not open opportunities)"] + [f"- AWARDED: {md_text(a.get('text'))}" + (f" [notice]({safe_url(a.get('url'))})" if safe_url(a.get('url')) else "") for a in leads]
    for row in rows:
        r,m=row["record"],row["match"]; route=r.get("application_route") or {}; src=source_summaries(r)
        source="; ".join(f"[{md_text(s['source_id'])}]({notice_url(r) or s['url']}) accessed {md_text(s['accessed_at'])}; licence " + (f"[licence]({s['licence_url']})" if s.get('licence_url') else "not stated") for s in src) or "No source recorded"
        lines += [f"## {md_text(r.get('title','Untitled'))}", f"Status: {md_text(status_label(r))}. **{fit_label(m)}**; shortlist.", *[f"- {md_text(clean_reason(x))}" for x in all_reasons(m)[:4]], f"Reason: {md_text(r.get('classification_reason', 'Not recorded'))}.",
            f"Eligibility: {md_text(eligibility_label(m))}. Unknowns/requirements: {md_text(_list(r.get('eligibility')))}.",
            f"Deadline: {md_text(closing_label(r))}; original: {md_text(r.get('close_raw') or 'not published')}.",
            f"Official route: {md_text(route.get('purpose','unknown'))}; {safe_url(route.get('url')) or md_text(route.get('email') or 'none published')}; account required {md_text(route.get('account_required','unknown'))}; {md_text(route.get('instructions') or 'no instructions published')}.",
            f"Conditions: {md_text(_list(r.get('conditions')))}.",
            f"Readiness gaps: {md_text(_list(m.get('missing_capabilities')))}; exclusions/constraints: {md_text(_list(m.get('exclusions')))}; eligibility completeness: {'complete' if m.get('eligibility',{}).get('completeness') else 'requires verification'}.",
            f"Next action: verify the live official notice, eligibility and deadline; use its enquiry route to prepare, or submit only against a verified current invitation.", f"Evidence: {source}.", ""]
    lines += ["Attribution: " + md_text(_list(payload.get("attribution")))]
    result = "\n".join(lines)
    if len(result.split()) > 450 and rows:
        lowest = rows[-1]["record"].get("id")
        reduced = dict(payload)
        reduced["rows"] = [dict(r, match={**r["match"], "shortlist": False}) if r["record"].get("id") == lowest else r for r in payload.get("rows", [])]
        return render_assessment_md(reduced)
    return result

def render_assessment_html(payload):
    md = render_assessment_md(payload)
    # Build semantic HTML from the same bounded assessment fields.
    rows = [r for r in _selected(payload) if "## " + md_text(r["record"].get("title", "Untitled")) in md]; cov=payload.get('coverage',{})
    blocks=[]
    for row in rows:
        r,m=row['record'],row['match']; route=r.get('application_route') or {}; src=source_summaries(r)
        links='; '.join(_link(notice_ref(r) or s.get('source_id') or 'Source',notice_url(r) or s.get('url'))+f" accessed {_e(s.get('accessed_at') or 'unknown')}; licence "+(_link('licence',s.get('licence_url')) if s.get('licence_url') else 'not stated') for s in src) or 'No source recorded'
        route_link=_link(route.get('url') or route.get('email') or 'none published', route.get('url') or ('mailto:'+route['email'] if route.get('email') else None))
        blocks.append(f"<article><h2>{_e(r.get('title','Untitled'))}</h2><p><strong>{_e(status_label(r))}</strong> · <strong>{_e(fit_label(m))}</strong></p><ul>{''.join('<li>'+_e(clean_reason(x))+'</li>' for x in all_reasons(m)[:4])}</ul><p><b>Reason:</b> {_e(r.get('classification_reason', 'Not recorded'))}</p><p><b>Eligibility:</b> {_e(eligibility_label(m))}. Unknowns/requirements: {_e(_list(r.get('eligibility')))}</p><p><b>Deadline:</b> {_e(closing_label(r))}; original: {_e(r.get('close_raw') or 'not published')}</p><p><b>Official route:</b> {_e(route.get('purpose','unknown'))}; {route_link}; account required {_e(route.get('account_required','unknown'))}; {_e(route.get('instructions') or 'no instructions published')}</p><p><b>Conditions:</b> {_e(_list(r.get('conditions')))}</p><p><b>Readiness gaps:</b> {_e(_list(m.get('missing_capabilities')))}; constraints: {_e(_list(m.get('exclusions')))}; eligibility completeness: {_e(m.get('eligibility',{}).get('status','unknown'))}</p><p><b>Next action:</b> verify the live official notice, eligibility and deadline; use its enquiry route to prepare, or submit only against a verified current invitation.</p><p><b>Evidence:</b> {links}</p></article>")
    empty=''
    leads=_teaming(payload)
    lead_html=('<h2>Awarded context: teaming leads (not open opportunities)</h2><ul>'+''.join('<li><b>AWARDED:</b> '+_e(a.get('text'))+(' '+_link('notice',a.get('url')) if safe_url(a.get('url')) else '')+'</li>' for a in leads)+'</ul>') if leads else ''
    if not rows: empty='<p>No current or published-future records have enough permitted evidence for a capability shortlist. This does not establish that no opportunity exists. Check current official AusTender and agency notices, confirm source coverage and refresh date, then verify eligibility and submission route.</p>'
    attrib='; '.join(_e(x) for x in payload.get('attribution',[])) or 'No attribution supplied.'
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Defence supply assessment — {_e(payload.get('period',''))}</title><style>@page{{size:A4;margin:15mm}}body{{font:10pt/1.35 Arial,sans-serif;color:#182b3a;max-width:190mm;margin:auto;overflow-wrap:anywhere}}h1,h2{{color:#102b46}}article{{break-inside:avoid;border-top:1px solid #087e83;padding:.35em 0}}a{{color:#075d74;overflow-wrap:anywhere}}.note{{background:#edf6f5;padding:.7em}}@media print{{body{{max-width:none}}}}</style><h1>Defence supply assessment — {_e(payload.get('period',''))}</h1><p>As of {_e(awst_stamp(payload.get('as_of')))}.</p><p><b>Profile:</b> {_e(payload.get('profile', {}).get('name', 'Private profile'))}.</p><p class="note">Coverage: {cov.get('confirmed_open',0)} confirmed open; {cov.get('held',{}).get('total',0)} held; {cov.get('context_records',0)} context. Complements ICN by separating evidence, timing, eligibility and context; no exclusive discovery claim.</p>{''.join(blocks) or empty}{lead_html if not rows else ''}<p><b>Attribution:</b> {attrib}</p></html>'''
