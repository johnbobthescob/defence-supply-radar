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
             "accessed_at": s.get("accessed_at"), "pointer": s.get("pointer"),
             "snapshot_sha256": s.get("snapshot_sha256"), "licence_url": safe_url(s.get("licence_url"))}
            for s in record.get("sources", [])]
