"""Offline deterministic build pipeline and rollback-safe artifact publication."""
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

from .evidence import digest
from .models import utc_datetime, utc_iso
from .reporting import prepare_payload, record_states
from .render.briefing import render_briefing
from .render.exports import render_json, render_csv
from .render.html_list import render_html
from .render.assessment import render_assessment_md, render_assessment_html


class StrictCoverageError(ValueError):
    """A usable local build was refused by explicit publication health policy."""


def _profile_id(profile):
    value = getattr(profile, "id", None) or getattr(profile, "profile_id", None)
    if value is None and isinstance(profile, dict): value = profile.get("id", profile.get("profile_id"))
    if value is None: value = "profile-" + digest(profile.to_dict() if hasattr(profile, "to_dict") else profile)[:12]
    value = str(value)
    if value in {".", ".."} or "/" in value or "\\" in value or ".." in value or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", value):
        raise ValueError("profile id must be a safe filename component")
    return value


def _coverage(repo, policies, as_of):
    runs = repo.runs() if repo else []
    records = repo.list_records() if repo else []
    safe_runs = [{k: r.get(k) for k in ("source_id", "field", "start", "end", "state", "at", "pages", "records", "live")} for r in runs]
    result = {"sources": [], "runs": safe_runs, "unresolved_incomplete_intervals": [], "review_held": 0,
              "missing_aic_documents": None, "aic_candidate_count": None, "warnings": ["AIC document and disabled-candidate inventories are not persisted in the repository; counts are unknown."]}
    for p in policies:
        data = p.to_dict() if hasattr(p, "to_dict") else dict(p)
        sid = data.get("id")
        sruns = [r for r in runs if r["source_id"] == sid]
        latest = next((r for r in reversed(safe_runs) if r["source_id"] == sid), None)
        successful = [r for r in sruns if r["state"] == "complete" and r.get("live")]
        result["sources"].append({"id": sid, "access_mode": data.get("access_mode"), "rights_status": data.get("rights_status"),
            "allowed_audiences": data.get("allowed_audiences", []), "latest_run": latest,
            "last_successful_refresh": successful[-1]["at"] if successful else None})
        for run in sruns:
            if run["state"] != "complete":
                covering = any(c["state"] == "complete" and c.get("live") and c.get("field") == run.get("field")
                    and c.get("start", "") <= run.get("start", "") and c.get("end", "") >= run.get("end", "")
                    and c.get("at", "") >= run.get("at", "") for c in sruns)
                if not covering: result["unresolved_incomplete_intervals"].append({**{k: run.get(k) for k in ("source_id", "field", "start", "end", "state", "at")}, "live": bool(run.get("live"))})
    result["review_held"] = sum(1 for r in records if getattr(r, "publication_state", None) and str(r.publication_state) == "held")
    if not any(p.id == "austender" for p in policies):
        result["warnings"].append("AusTender contract-notice source policy is missing.")
    result["warnings"].append("Current APP/ATM open-tender feed is unavailable; coverage is not complete.")
    result["warnings"].append("AIC-derived content remains rights-held for public distribution.")
    cutoff = utc_datetime(as_of) - timedelta(days=7)
    for p in policies:
        if getattr(p, "access_mode", None) == "disabled": result["warnings"].append(f"Source {p.id} is disabled by policy.")
    for src in result["sources"]:
        if src["access_mode"] not in {"disabled", "local_only", "manual_reference"} and src["last_successful_refresh"] and utc_datetime(src["last_successful_refresh"]) < cutoff:
            src["stale"] = True
            result["warnings"].append(f"Source {src['id']} has no successful refresh within seven days of as_of.")
        else: src["stale"] = False
    result["summary"] = (f"{len(runs)} recorded source runs; {len(result['unresolved_incomplete_intervals'])} unresolved live or saved intervals. "
                          "Current APP/ATM feed is missing; disabled and rights-held sources are expected gaps.")
    root = Path(__file__).resolve().parents[1]
    try:
        manifest = json.loads((root / "config/aic_manifest.json").read_text())
        seeds = json.loads((root / "config/official_seeds.json").read_text())
        result["missing_aic_documents"] = sum(not (root / d["text_path"]).is_file() for d in manifest["documents"])
        result["aic_document_count"] = len(manifest["documents"])
        result["disabled_seed_candidates"] = len(seeds.get("candidates", []))
        result["aic_candidate_count"] = sum("aic" in r.source_ids for r in records)
        result["inventory_hashes"] = {"aic_manifest": digest(manifest), "official_seeds": digest(seeds)}
        result["warnings"] = [w for w in result["warnings"] if not w.startswith("AIC document and disabled-candidate")]
    except (OSError, ValueError, KeyError):
        pass
    return result


def build_outputs(repo, profile, taxonomy, policies, as_of, period, audience, out,
                  include_speculative=False, strict=False):
    """Build a complete offline bundle. The destination is restored if any step fails."""
    if audience not in {"public", "research"}: raise ValueError("audience must be public or research")
    pid = _profile_id(profile)
    if audience == "public" and not profile.fictional and "id" not in profile.public_fields:
        pid = "profile-" + digest(profile.to_dict())[:12]
    as_of = utc_iso(utc_datetime(as_of))
    coverage = _coverage(repo, policies, as_of)
    if strict:
        failures = [r for r in coverage["unresolved_incomplete_intervals"] if r["live"]]
        for src in coverage["sources"]:
            if src["access_mode"] not in {"disabled", "local_only", "manual_reference"} and src["allowed_audiences"] and (src["last_successful_refresh"] is None or src["stale"]):
                failures.append(src["id"])
        if failures: raise StrictCoverageError("strict build refused: live source coverage is incomplete or stale")
    payload = prepare_payload(repo, profile, taxonomy, policies, as_of, str(period), audience, include_speculative, coverage)
    files = {
        f"briefing-{period}.md": render_briefing(payload),
        "work-packages.json": render_json(payload), "work-packages.csv": render_csv(payload),
        "work-packages.html": render_html(payload),
        f"assessment-{pid}.md": render_assessment_md(payload),
        f"assessment-{pid}.html": render_assessment_html(payload),
        "coverage.json": json.dumps(payload["coverage"], sort_keys=True, ensure_ascii=False, indent=2) + "\n",
    }
    inputs = sorted({s.get("snapshot_sha256") for r in repo.list_records() for s in r.sources if s.get("snapshot_sha256")}) if repo else []
    policy_versions = {p.id: digest(p.to_dict()) for p in policies}
    manifest = {"schema_version": 1, "as_of": as_of, "period": str(period), "profile_id": pid,
        "profile_hash": payload["profile_hash"], "audience": audience, "taxonomy_version": taxonomy["version"],
        "rule_versions": payload["rule_versions"], "policy_hashes": policy_versions,
        "taxonomy_hash": digest(taxonomy), "inventory_hashes": coverage.get("inventory_hashes", {}),
        "input_snapshot_sha256": inputs, "held_count": payload["coverage"].get("held", {}).get("total", 0),
        "excluded_counts": {"irrelevant": payload["coverage"].get("excluded_irrelevant", 0)},
        "output_sha256": {name: hashlib.sha256(content.encode("utf-8")).hexdigest() for name, content in sorted(files.items())}}
    files["manifest.json"] = json.dumps(manifest, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
    target = Path(out)
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{target.name}.stage-", dir=target.parent))
    backup = target.with_name(f".{target.name}.backup-{os.getpid()}")
    moved_old = False
    installed = False
    try:
        for name, content in files.items():
            (stage / name).write_text(content, encoding="utf-8", newline="\n")
        expected = set(files)
        if {p.name for p in stage.iterdir()} != expected: raise ValueError("artifact validation failed")
        json.loads((stage / "coverage.json").read_text(encoding="utf-8")); json.loads((stage / "manifest.json").read_text(encoding="utf-8"))
        for name, sha in manifest["output_sha256"].items():
            if hashlib.sha256((stage / name).read_bytes()).hexdigest() != sha: raise ValueError("artifact hash validation failed")
        with repo.transaction():
            if backup.exists(): shutil.rmtree(backup) if backup.is_dir() else backup.unlink()
            if target.exists(): os.replace(target, backup); moved_old = True
            os.replace(stage, target)
            installed = True
            repo.save_build(manifest, record_states(payload))
        if moved_old:
            try: shutil.rmtree(backup) if backup.is_dir() else backup.unlink()
            except OSError: pass
        return manifest
    except BaseException:
        if target.exists() and installed: shutil.rmtree(target) if target.is_dir() else target.unlink()
        if moved_old and backup.exists(): os.replace(backup, target)
        raise
    finally:
        if stage.exists(): shutil.rmtree(stage, ignore_errors=True)
