"""Curated offline seed validation; candidate links are never fetched."""
import json
from pathlib import Path
from urllib.parse import urlparse

from ..evidence import digest
from ..models import Opportunity, utc_datetime, utc_iso

_ALLOWED = {"defence.gov.au", "www.defence.gov.au", "asa.gov.au", "www.asa.gov.au", "tenders.gov.au", "www.tenders.gov.au"}


def ingest_seeds(repo, path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("seed schema_version must be 1")
    result = {"imported": 0, "candidates": 0, "held": 0, "warnings": []}
    for candidate in data.get("candidates", []):
        host = urlparse(candidate.get("url", "")).hostname
        if host not in _ALLOWED or candidate.get("enabled") is not False:
            result["warnings"].append(f"candidate {candidate.get('id')}: rejected host or enabled state")
            result["held"] += 1
        else:
            result["candidates"] += 1
    for item in data.get("records", []):
        try:
            record = dict(item["record"])
            review = item.get("review", {})
            if record.get("status_class") is not None or "status_override" in record:
                raise ValueError("status overrides rejected")
            valid = review.get("content_sha256") == digest(record) and bool(review.get("reviewed_at")) and bool(review.get("reviewer"))
            if any(urlparse(s["url"]).scheme != "https" or urlparse(s["url"]).hostname not in _ALLOWED for s in record.get("sources", [])):
                raise ValueError("seed sources must use an official HTTPS host")
            record.setdefault("evidence_flags", {})["review"] = {"content_sha256":review.get("content_sha256"), "reviewed_at":review.get("reviewed_at"), "reviewer":review.get("reviewer")}
            record["verified_at"] = utc_iso(min([utc_datetime(s["accessed_at"]) for s in record["sources"]] + [utc_datetime(review["reviewed_at"])])) if review.get("reviewed_at") else None
            record["review_state"] = "reviewed" if valid else "needs_review"
            record["publication_state"] = "held"
            repo.save_record(Opportunity.from_dict(record), event_at=review.get("reviewed_at"))
            result["imported"] += 1
            if not valid: result["held"] += 1
        except Exception as exc:
            result["held"] += 1
            result["warnings"].append(f"seed held: {exc}")
    return result
