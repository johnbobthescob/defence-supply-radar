"""Compact weekly Markdown briefing."""
from datetime import datetime
from zoneinfo import ZoneInfo

from .common import closing_label, eligibility_label, md_text, route_label, source_summaries, status_label


def _awst(value):
    try: return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(ZoneInfo("Australia/Perth")).isoformat()
    except (ValueError, AttributeError): return str(value)


def _item(row):
    rec, fit = row["record"], row["match"]
    lines = [f"### {md_text(rec.get('title', 'Untitled'))}",
             f"- Status: {md_text(status_label(rec))}. Reason: {md_text(rec.get('classification_reason', ''))}",
             f"- Eligibility: {md_text(eligibility_label(fit))}",
             f"- Stage / lifecycle / currentness: {md_text(rec.get('procurement_stage'))} / {md_text(rec.get('lifecycle'))} / {md_text(rec.get('freshness_state'))}. Verified {md_text(rec.get('verified_at') or 'not published')}; source publication {md_text(rec.get('source_published_at') or 'not published')}.",
             f"- Work location: {md_text('; '.join(p.get('name', '') for p in rec.get('locations', []) if p.get('role') in {'worksite', 'delivery'}) or 'not published')}.",
             f"- Deadline: {md_text(closing_label(rec))}",
             f"- Route: {md_text(route_label(rec.get('application_route')))}",
             f"- Fit: {fit.get('score', 0)}/100; components {md_text(fit.get('components', {}))}; matched {md_text(', '.join(fit.get('matched_capabilities', [])) or 'none')}; missing {md_text(', '.join(fit.get('missing_capabilities', [])) or 'none')}.",
             f"- Conditions: {md_text('; '.join(rec.get('conditions', [])) or 'None recorded')}"]
    if fit.get("exclusions"):
        lines.append("- Constraints: " + md_text("; ".join(fit["exclusions"])))
    action = {"confirmed_open": "Apply only through the verified official notice; check all requirements.", "published_future_scope": "Prepare capability evidence and verify scope via the published enquiry route.", "speculative": "Watch hypothesis; no buyer commitment or application is established."}.get(rec.get("status_class"), "Use as historical context only; no submission route is established.")
    lines.append("- Next action: " + action)
    src = source_summaries(rec)
    lines.append("- Sources: " + ("; ".join(f"[{md_text(s['source_id'])}]({s['url']}) accessed {md_text(s['accessed_at'])}; pointer {md_text(s['pointer'])}; licence {s['licence_url'] or 'not stated'}" for s in src) if src else "None recorded"))
    return "\n".join(lines)


def render_briefing(payload):
    rows = payload.get("rows", [])
    def kind(r): return r["record"].get("record_kind")
    def status(r): return r["record"].get("status_class")
    open_rows = [r for r in rows if status(r) == "confirmed_open" and r["match"].get("shortlist")]
    future = [r for r in rows if status(r) == "published_future_scope" and r["match"].get("score", 0) > 0]
    speculative = [r for r in rows if status(r) == "speculative"]
    context = [r for r in rows if kind(r) == "contract_context"]
    history = [r for r in rows if r["record"].get("lifecycle") in {"closed", "awarded", "cancelled", "superseded"} and kind(r) != "contract_context"]
    other_context = [r for r in rows if kind(r) in {"registration_context", "readiness_context"}]
    cov = payload.get("coverage", {})
    lines = [f"# Defence supply radar — {md_text(payload.get('period', ''))}", "",
             f"As of **{md_text(_awst(payload.get('as_of', '')))} AWST**.", "",
             "## Coverage", "",
             f"{cov.get('confirmed_open', 0)} verified open records; {cov.get('context_records', 0)} relevant contract-context records; {cov.get('held', {}).get('total', 0)} records held; {cov.get('excluded_irrelevant', 0)} unrelated agency records excluded.",
             "APP/ATM API coverage is missing. AIC-derived distribution remains held pending rights review.",
             "", "## Confirmed open", ""]
    health = cov.get("summary") or "See coverage.json for source refresh status, partial windows and access gaps."
    lines.insert(lines.index("## Confirmed open"), md_text(health))
    lines.extend([_item(r) for r in open_rows] if open_rows else ["No confirmed-open matches are verified for this build."])
    for title, subset in (("Published future scope", future), ("Speculative watch", speculative), ("Awarded history — context, not work available", context), ("Inactive history", history), ("Other context", other_context)):
        lines.extend(["", f"## {title}", ""])
        lines.extend([_item(r) for r in subset] if subset else ["None."])
    delta = payload.get("delta", {})
    lines.extend(["", "## Period changes", "", f"New: {len(delta.get('new', []))}; changed: {len(delta.get('changed', []))}; closed: {len(delta.get('closed', []))}."])
    for key, label in (("new", "New IDs"), ("changed", "Changed IDs"), ("closed", "Closed IDs")):
        if delta.get(key): lines.append(f"{label}: {', '.join(md_text(i) for i in delta[key])}.")
    lines.extend(["", "## Attribution", "", "; ".join(md_text(a) for a in payload.get("attribution", [])) or "No attribution supplied.", ""])
    return "\n".join(lines)
