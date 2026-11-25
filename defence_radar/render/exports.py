"""JSON and spreadsheet-safe CSV exports."""
import csv
import io
import json

from .common import (api_url, band_for, buyer_unit, closing_label, eligibility_label, notice_url, record_amount, route_label,
                     all_reasons, signed_stamp, source_summaries, supplier_text, suppliers_of, awst_iso_date, class_of)


def render_json(payload):
    return json.dumps({"schema": "defence-radar/work-packages", "schema_version": 1, "build": {k: payload.get(k) for k in ("as_of", "period", "audience", "profile_hash", "taxonomy_version", "rule_versions")}, "data": payload}, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def _cell(value):
    text = str(value if value is not None else "")
    probe = text.lstrip(" \t\r\n\v\f\x00\x1b")
    if (probe and probe[:1] in "=+-@") or (text and ord(text[0]) < 32): return "'" + text
    return text


def render_csv(payload):
    fields = ["id", "kind", "title", "status", "reason", "lifecycle", "eligibility", "eligibility_limitations", "stage", "score", "capabilities", "close_precision", "close_raw", "close_utc", "close_awst", "route_purpose", "route_url", "route_email", "sources", "conditions", "attribution", "limitations"]
    fields.extend(["programme", "buyer", "prime", "geography", "verified_at", "source_published_at", "source_modified_at", "eligibility_requirements"])
    fields.extend(["band", "fit_reasons", "notice_url", "api_url", "supplier", "buyer_unit", "value_aud", "signed_date"])
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in payload.get("rows", []):
        rec, fit = row["record"], row["match"]
        elig = fit.get("eligibility", {})
        values = {"id": rec.get("id"), "kind": rec.get("record_kind"), "title": rec.get("title"), "status": class_of(rec), "reason": rec.get("classification_reason"), "lifecycle": rec.get("lifecycle"), "eligibility": elig.get("status", "unknown"), "eligibility_limitations": elig.get("limitation", elig.get("reason", "")), "stage": rec.get("procurement_stage"), "score": fit.get("score"), "capabilities": "; ".join(t.get("id", "") for t in rec.get("capabilities", [])), "close_precision": rec.get("close_precision"), "close_raw": rec.get("close_raw"), "close_utc": rec.get("close_at_utc"), "close_awst": closing_label(rec), "route_purpose": (rec.get("application_route") or {}).get("purpose"), "route_url": (rec.get("application_route") or {}).get("url"), "route_email": (rec.get("application_route") or {}).get("email"), "sources": json.dumps(source_summaries(rec), ensure_ascii=False, sort_keys=True), "conditions": "; ".join(rec.get("conditions", [])), "attribution": "; ".join(rec.get("attribution", [])), "limitations": "Relevance is not approval; verify source and eligibility."}
        values.update({key: rec.get(key) for key in ("programme", "buyer", "prime", "verified_at", "source_published_at", "source_modified_at")})
        values["geography"] = "; ".join(p.get("name", "") for p in rec.get("locations", []) if p.get("role") in {"worksite", "delivery"}) or "not published"
        values["eligibility_requirements"] = json.dumps(elig.get("requirements", []), ensure_ascii=False, sort_keys=True)
        amt = record_amount(rec)
        values.update({"band": fit.get("band") or band_for(fit.get("score") or 0), "fit_reasons": "; ".join(all_reasons(fit)),
                       "notice_url": notice_url(rec) or "", "api_url": api_url(rec) or "",
                       "supplier": "; ".join(n for n, _ in suppliers_of(rec)) if rec.get("record_kind") == "contract_context" else "",
                       "buyer_unit": buyer_unit(rec), "value_aud": f"{amt:.2f}" if amt is not None else "",
                       "signed_date": awst_iso_date(signed_stamp(rec)) or ""})
        writer.writerow({key: _cell(value) for key, value in values.items()})
    return out.getvalue()
