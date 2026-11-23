"""Offline extraction and reviewed import for Defence AIC documents."""
import hashlib
from email.utils import parsedate_to_datetime
import json
import re
import subprocess
from pathlib import Path

from ..models import Opportunity, utc_datetime, utc_iso
from ..evidence import digest


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def extract_text(text_path):
    raw = Path(text_path).read_text(encoding="utf-8", errors="replace")
    pages = []
    lines_all = raw.splitlines(keepends=True)
    page_texts = raw.split("\f")
    offset = 1
    for number, page_text in enumerate(page_texts, 1):
        lines = page_text.splitlines()
        start = offset if lines else None
        end = offset + len(lines) - 1 if lines else None
        pages.append({"page": number, "text": page_text, "start_line": start, "end_line": end})
        offset += len(lines)
    warnings, candidates = [], []
    for page in pages:
        lines = page["text"].splitlines()
        for i, line in enumerate(lines, 1):
            low = line.lower()
            kind = None
            if re.search(r"\b(existing|appointed|supplier|contracted)\b", low) and re.search(r"\bsupplier\b", low):
                kind = "existing_supplier"
            elif re.search(r"\b(register|keep me updated|briefing|engagement)\b", low):
                kind = "engagement"
            elif re.search(r"\b(future|planned|anticipated|subject to|if commercially viable|tasking statement)\b", low):
                kind = "future"
            elif re.search(r"\b(scope|subcontract|work package|capability)\b", low):
                kind = "scope"
            if kind:
                candidates.append({"page": page["page"], "kind": kind, "line_start": i, "line_end": i})
            if re.search(r"[A-Z0-9._%+-]+\s+[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", line, re.I):
                warnings.append(f"page {page['page']} line {i}: malformed spaced email retained")
            if re.search(r"\bLCM\b", line, re.I) and re.search(r"\bLCH\b", line, re.I):
                warnings.append(f"page {page['page']} line {i}: contradictory AIA wording retained")
    return {"sha256": _sha(text_path), "pages": pages, "warnings": warnings, "candidates": candidates}


def extract_pdf(pdf_path, output_path):
    result = subprocess.run(["pdftotext", "-layout", str(pdf_path), str(output_path)], capture_output=True, text=True, timeout=60, check=True)
    version = subprocess.run(["pdftotext", "-v"], capture_output=True, text=True, timeout=10)
    return {"version": (version.stderr or version.stdout).splitlines()[0] if (version.stderr or version.stdout) else "unknown", "sha256": _sha(output_path)}


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def ingest_aic(repo, manifest_path, root=Path("."), extract_pdf=False):
    root = Path(root)
    manifest = _read_json(manifest_path)
    if manifest.get("schema_version") != 1:
        raise ValueError("manifest.schema_version must be 1")
    counts = {"documents": len(manifest.get("documents", [])), "missing": 0, "changed": 0, "imported": 0, "held": 0, "warnings": []}
    index = manifest.get("index", {})
    index_path = root / index.get("path", "")
    if index.get("path") and (not index_path.exists() or _sha(index_path) != index.get("sha256")):
        counts["warnings"].append("AIC index is missing or its saved hash changed")
    for doc in manifest.get("documents", []):
        txt = root / doc["text_path"]
        if not txt.exists() and extract_pdf and doc.get("pdf_path"):
            pdf = root / doc["pdf_path"]
            if pdf.exists():
                txt.parent.mkdir(parents=True, exist_ok=True)
                extract_pdf_fn = globals()["extract_pdf"]
                extract_pdf_fn(pdf, txt)
        if not txt.exists():
            counts["missing"] += 1
            continue
        actual = _sha(txt)
        text_changed = actual != doc.get("text_sha256")
        pdf_path = root / doc["pdf_path"] if doc.get("pdf_path") else None
        pdf_changed = bool(pdf_path and pdf_path.exists() and doc.get("pdf_sha256") and _sha(pdf_path) != doc["pdf_sha256"])
        if text_changed or pdf_changed:
            counts["changed"] += 1
        report = extract_text(txt)
        review_path = root / doc["reviews_file"]
        entries = _read_json(review_path) if review_path.exists() else []
        if not isinstance(entries, list):
            counts["warnings"].append(f"{doc['id']}: reviews must be a JSON list")
            entries = []
        imported_here = 0
        held_before = counts["held"]
        for entry in entries:
            try:
                record = dict(entry["record"])
                review = entry["review"]
                valid = (not text_changed and not pdf_changed and review.get("content_sha256") == actual
                         and review.get("scope_sha256") == digest(record)
                         and bool(review.get("reviewed_at")) and bool(review.get("reviewer")))
                if record.get("status_class") is not None:
                    raise ValueError("status override rejected; classification is deferred")
                key = entry["key"]
                if record.get("record_kind") not in {"planned_scope", "contract_context", "registration_context", "readiness_context"}:
                    raise ValueError("record_kind must be an explicit reviewed scope or context kind")
                reviewed_at = review.get("reviewed_at")
                record.setdefault("evidence_flags", {})["review"] = {"content_sha256":review.get("content_sha256"), "reviewed_at":reviewed_at, "reviewer":review.get("reviewer")}
                record.update(id=f"aic:{doc['id']}:{key}", source_record_id=f"aic:{doc['id']}:{key}", source_ids=["aic"], rights=["aic"], publication_state="held", review_state="reviewed" if valid else "needs_review", status_class=None, lifecycle="unknown", verified_at=reviewed_at)
                page = record.get("evidence_flags", {}).get("page")
                if isinstance(page, bool) or not isinstance(page, int) or not 1 <= page <= len(report["pages"]):
                    raise ValueError("record.evidence_flags.page must be an integer")
                accessed_at = doc["accessed_at"]
                try:
                    accessed_at = parsedate_to_datetime(accessed_at).isoformat() if not ("T" in accessed_at) else accessed_at
                except (TypeError, ValueError):
                    pass
                record["sources"] = [{"source_id":"aic", "url":doc["url"], "accessed_at":accessed_at, "evidence_id":doc["id"], "snapshot_sha256":actual, "pointer":f"page:{page}"}]
                # Reviewing an old local file cannot refresh authoritative status.
                record["verified_at"] = utc_iso(min(utc_datetime(accessed_at), utc_datetime(reviewed_at))) if reviewed_at else None
                record["classification_evidence"] = [doc["id"]]
                record["evidence_flags"]["source_issue_date"] = doc.get("issue_date")
                record["evidence_flags"]["server_last_modified"] = doc.get("server_last_modified")
                record["attribution"] = []
                repo.save_record(Opportunity.from_dict(record), event_at=reviewed_at)
                imported_here += 1
                counts["held"] += 1  # distribution rights are held regardless of review
            except Exception as exc:
                counts["warnings"].append(f"{doc['id']}: invalid reviewed entry ({exc})")
                counts["held"] += 1
        counts["imported"] += imported_here
        if not entries and counts["held"] == held_before:
            counts["held"] += 1
        review_path.parent.mkdir(parents=True, exist_ok=True)
        (review_path.parent / f"{doc['id']}-extraction.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return counts
