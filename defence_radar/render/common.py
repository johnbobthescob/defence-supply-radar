"""Shared safe formatting helpers."""
import html
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from urllib.parse import urlparse, quote


def safe_url(value):
    if not isinstance(value, str): return None
    if re.search(r"[\x00-\x20\x7f]", value) or re.search(r"%(0a|0d)", value, re.I): return None
    p = urlparse(value.strip())
    if p.scheme not in {"https", "http", "mailto"} or (p.scheme != "mailto" and not p.hostname): return None
    if p.username or p.password: return None
    if p.scheme == "mailto" and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", p.path): return None
    return quote(value.strip(), safe=":/?#@!$&'*+,;=%-._~")


def md_text(value):
    text = html.escape(str(value), quote=True)
    return re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", text)


def status_label(record):
    status = record.get("status_class")
    return {"confirmed_open": "Confirmed open opportunity", "published_future_scope": "Published future work scope", "speculative": "Speculative"}.get(status, "Context / " + str(record.get("lifecycle") or "unknown"))


def closing_label(record):
    precision = record.get("close_precision", "not_published")
    raw = record.get("close_raw")
    if precision == "not_applicable": return "Not applicable"
    if precision == "not_published": return "Not published"
    value = raw or ""
    utc = record.get("close_at_utc")
    awst = ""
    if utc:
        awst = datetime.fromisoformat(utc.replace("Z", "+00:00")).astimezone(ZoneInfo("Australia/Perth")).isoformat()
    return "; ".join(x for x in (value, record.get("close_zone"), f"UTC {utc}" if utc else "", f"AWST {awst}" if awst else "") if x) or precision.replace("_", " ")


def route_label(route):
    route = route or {}
    target = safe_url(route.get("url")) or route.get("email") or "No route published"
    purpose = str(route.get("purpose", "unknown")).replace("_", " ")
    return f"{purpose}: {target}"


def eligibility_label(match):
    eligibility = match.get("eligibility", {})
    status = eligibility.get("status", "unknown").replace("_", " ")
    details = eligibility.get("limitation") or eligibility.get("limitations") or eligibility.get("reason") or ""
    return status + (f" — {details}" if details else "")


def source_summaries(record):
    return [{"source_id": s.get("source_id"), "url": safe_url(s.get("url")),
             "notice_id": s.get("notice_id"), "release_id": s.get("release_id"),
             "accessed_at": s.get("accessed_at"), "pointer": s.get("pointer"),
             "snapshot_sha256": s.get("snapshot_sha256"), "licence_url": safe_url(s.get("licence_url"))}
            for s in record.get("sources", [])]


# ---------------------------------------------------------------------------
# Presentation helpers shared by the briefing, work-package page, assessment
# and CSV renderers. Everything here returns plain strings or simple lists.
# ---------------------------------------------------------------------------
AWST = ZoneInfo("Australia/Perth")
ATM_URL = "https://www.tenders.gov.au/atm"
ICN_URL = "https://gateway.icn.org.au/"
AUSTENDER_ATTRIBUTION = "AusTender data © Commonwealth of Australia (Department of Finance), CC BY 3.0 AU"
WORK_PACKAGES_PAGE = "work-packages.html"
OPEN_MIN_SCORE = 25

CLASS_LABELS = {
    "confirmed_open": "Open", "published_future_scope": "Future scope", "speculative": "Speculative",
    "awarded_context": "Awarded (context)", "context_only": "Context", "inactive": "Inactive", "held": "Held",
}
CLASS_BADGE_TEXT = {
    "confirmed_open": "OPEN — verified tender", "published_future_scope": "FUTURE SCOPE — not yet open",
    "speculative": "SPECULATIVE — no buyer commitment", "awarded_context": "AWARDED — not an opportunity",
    "context_only": "CONTEXT — not an opportunity", "inactive": "INACTIVE", "held": "HELD",
}
UNSPSC_FAMILIES = {
    "23": "Industrial manufacturing machinery", "24": "Material handling equipment", "25": "Vehicles and vessels",
    "26": "Power generation and distribution", "27": "Tools and machinery", "30": "Structures and building components",
    "31": "Manufacturing components", "32": "Electronic components", "39": "Electrical systems and lighting",
    "40": "Distribution and conditioning systems", "41": "Laboratory and test equipment", "43": "IT and communications",
    "46": "Defence and law enforcement", "72": "Building and facility services", "73": "Industrial production services",
    "76": "Industrial cleaning services", "78": "Transport and storage services", "81": "Engineering and research services",
    "84": "Financial services", "92": "Defence and safety services",
}


def parse_dt(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(AWST)
    except (ValueError, TypeError):
        return None


def awst_stamp(value):
    """'Wed 25 Nov 2026 10:00 AWST' (or the raw text if it cannot be parsed)."""
    d = parse_dt(value)
    return f"{d.strftime('%a')} {d.day} {d.strftime('%b %Y %H:%M')} AWST" if d else str(value or "not published")


def awst_date(value):
    d = parse_dt(value)
    return f"{d.day} {d.strftime('%b %Y')}" if d else "not published"


def awst_iso_date(value):
    d = parse_dt(value)
    return d.date().isoformat() if d else None


def money(value):
    """$1.2m / $350k / $350."""
    try: v = float(value)
    except (TypeError, ValueError): return "n/a"
    if v >= 999500: return f"${v / 1e6:.1f}m"
    if v >= 1000: return f"${round(v / 1e3):.0f}k"
    return f"${v:.0f}"


def record_amount(rec):
    try: return float(str((rec.get("value_context") or {}).get("amount", "")).replace(",", ""))
    except ValueError: return None


def band_for(score):
    return "strong" if score >= 70 else "good" if score >= 45 else "possible" if score >= 25 else "low"


def fit_label(match):
    score = int(match.get("score") or 0)
    return f"Fit {score}/100 ({match.get('band') or band_for(score)})"


def clean_reason(reason):
    """Drop the leading '+42 ' so the reason reads as a sentence."""
    return re.sub(r"^\s*[+-]?\d+\s+", "", str(reason)).strip()


def _points(reason):
    m = re.match(r"\s*\+(\d+)\s", str(reason))
    return int(m.group(1)) if m else 0


def all_reasons(match):
    reasons = [str(r) for r in (match.get("reasons") or [])]
    return reasons or [str(e) for e in (match.get("evidence") or [])]


def top_reasons(match, n=3):
    """Highest-value scoring reasons first (original order kept), zero-point notes last."""
    reasons = all_reasons(match)
    scored = [r for r in reasons if _points(r) > 0]
    return scored[:n] if scored else reasons[:n]


def notice_url(rec):
    for s in rec.get("sources") or []:
        u = safe_url(s.get("url"))
        if u: return u
    return None


def api_url(rec):
    for s in rec.get("sources") or []:
        u = safe_url(s.get("api_url"))
        if u: return u
    return None


def notice_ref(rec):
    s0 = (rec.get("sources") or [{}])[0]
    return rec.get("source_record_id") or s0.get("notice_id") or rec.get("id") or ""


def buyer_unit(rec):
    return (rec.get("evidence_flags") or {}).get("buyer_branch") or rec.get("buyer") or "Not published"


def suppliers_of(rec):
    sup = (rec.get("evidence_flags") or {}).get("suppliers") or []
    out = []
    for s in sup:
        where = ", ".join(x for x in (s.get("locality"), s.get("region")) if x)
        out.append((s.get("name") or "Not published", where))
    if not out and rec.get("prime"):
        out = [(p.strip(), "") for p in str(rec["prime"]).split(";") if p.strip()]
    return out


def supplier_text(rec):
    parts = [n + (f" ({w})" if w else "") for n, w in suppliers_of(rec)]
    return "; ".join(parts) or "Not published"


def signed_stamp(rec):
    return (rec.get("evidence_flags") or {}).get("date_signed") or rec.get("source_published_at")


def class_of(rec):
    return rec.get("status_class") or "context_only"


def capability_label(cid, payload):
    for c in (payload.get("market") or {}).get("capabilities", []):
        if c.get("id") == cid and c.get("label"): return c["label"]
    return str(cid).replace("_", " ").capitalize()


def unspsc_families(rec):
    fams = []
    for u in (rec.get("evidence_flags") or {}).get("unspsc") or []:
        code = str(u.get("id") or "")[:2]
        if code.isdigit():
            label = f"UNSPSC {code} — {UNSPSC_FAMILIES.get(code, 'family')}"
            if label not in fams: fams.append(label)
    return fams


def in_week(rec, week):
    d = awst_iso_date(rec.get("source_published_at"))
    return bool(d) and week.get("start", "") <= d <= week.get("end", "")


def md_inline(value):
    """Minimal Markdown escaping for inline text: only characters that would change rendering."""
    text = re.sub(r"\s+", " ", str(value if value is not None else "")).strip()
    text = text.replace("\\", "\\\\")
    text = re.sub(r"([*`\[\]<>|])", r"\\\1", text)
    text = re.sub(r"(?<![A-Za-z0-9])_|_(?![A-Za-z0-9])", r"\\_", text)
    return text


def briefing_model(payload):
    """Deterministic view-model shared by the HTML and Markdown briefings."""
    rows = payload.get("rows", [])
    week = payload.get("week") or {}
    market = payload.get("market") or {}
    cov = payload.get("coverage") or {}
    score = lambda r: r["match"].get("score", 0) or 0
    open_rows = sorted((r for r in rows if r["record"].get("status_class") == "confirmed_open" and score(r) >= OPEN_MIN_SCORE),
                       key=lambda r: (r["record"].get("close_at_utc") or "9999", -score(r), r["record"].get("id", "")))
    future = sorted((r for r in rows if r["record"].get("status_class") == "published_future_scope"),
                    key=lambda r: (-score(r), r["record"].get("id", "")))
    spec = sorted((r for r in rows if r["record"].get("status_class") == "speculative"),
                  key=lambda r: (-score(r), r["record"].get("id", "")))
    awarded = [r for r in rows if r["record"].get("status_class") == "awarded_context"]
    wk = [r for r in awarded if in_week(r["record"], week)] if week else awarded
    top_awards = sorted(wk, key=lambda r: (-score(r), -(record_amount(r["record"]) or 0), r["record"].get("id", "")))[:10]
    actions = payload.get("actions") or []
    teaming = [a for a in actions if a.get("kind") == "teaming"]
    caps = sorted(market.get("capabilities") or [], key=lambda c: (-c.get("count", 0), -c.get("value", 0), c.get("label", "")))
    buyers = market.get("buyers") or []
    n_awards = market.get("awards_in_week", len(wk))
    total = market.get("total_value", 0) or 0
    bullets = []
    if open_rows:
        n = len(open_rows)
        nxt = open_rows[0]["record"]
        bullets.append(f"{n} verified open tender{'s' if n != 1 else ''} match{'' if n != 1 else 'es'} your capabilities; the first closes {awst_stamp(nxt.get('close_at_utc')) if nxt.get('close_at_utc') else 'on a date not published'}.")
    else:
        bullets.append("No verified open tenders this week. The open-tender feed is imported manually, so check AusTender and ICN Gateway yourself (see Open opportunities).")
    if n_awards:
        big = market.get("largest") or {}
        share = f" The largest, {big['title']} won by {big['supplier']} ({money(big['value'])}), is {round(100 * big['value'] / total)}% of that." if big.get("value") and total and big["value"] / total >= 0.25 else ""
        bullets.append(f"{n_awards} relevant awarded contract{'s' if n_awards != 1 else ''} published this week, worth {money(total)} in total.{share} These are awarded context, not open work.")
    else:
        bullets.append("No relevant awarded contracts were published this week.")
    if caps:
        c = caps[0]
        bullets.append(f"Top capability area by awards: {c['label']} ({c['count']} award{'s' if c['count'] != 1 else ''}, {money(c.get('value', 0))}).")
    if buyers:
        b = buyers[0]
        bullets.append(f"Most active buyer unit: {b['name']} ({b['count']} award{'s' if b['count'] != 1 else ''}, {money(b.get('value', 0))}).")
    if teaming:
        bullets.append("Best teaming lead: " + teaming[0]["text"])
    return {"open": open_rows, "future": future, "speculative": spec, "awarded_week": wk, "top_awards": top_awards,
            "bullets": bullets, "market": market, "cov": cov, "week": week, "actions": actions, "teaming": teaming,
            "n_awarded_rows": len(awarded)}


def open_gap_text(cov):
    atm = next((s for s in cov.get("sources", []) if s.get("id") == "austender_atm"), None)
    last = atm.get("last_successful_refresh") if atm else None
    base = ("Open tenders come only from the AusTender Current ATM feed, which must be imported manually; it is not fetched automatically. "
            "Verified open tenders in this build: " + str(cov.get("confirmed_open", 0)) + ". ")
    base += (f"Last ATM import: {awst_stamp(last)}." if last else "No ATM import has been recorded yet.")
    return base


def austender_present(payload):
    if any("austender" in str(s) for r in payload.get("rows", []) for s in r["record"].get("source_ids", [])): return True
    return any(str(s.get("id", "")).startswith("austender") and s.get("last_successful_refresh") for s in (payload.get("coverage") or {}).get("sources", []))


def source_refresh_rows(cov):
    out = []
    for s in cov.get("sources", []):
        mode = s.get("access_mode")
        if s.get("last_successful_refresh"):
            status = awst_stamp(s["last_successful_refresh"]) + (" (stale)" if s.get("stale") else "")
        elif mode in {"disabled", "local_only", "manual_reference"}:
            status = {"disabled": "disabled by policy", "local_only": "not published (rights)", "manual_reference": "manual reference only"}[mode]
        else:
            status = "never imported"
        out.append((s.get("id", ""), str(mode or "").replace("_", " "), status))
    return out
