"""The verified AusTender contract-notice API, never an open-tender feed."""
from datetime import timedelta
from email.utils import parsedate_to_datetime
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, parse_qsl

from ..evidence import save_snapshot
from ..models import Opportunity, utc_datetime, utc_iso
from ..policy import validate_fetch_url

BASE = "https://api.tenders.gov.au/ocds/findByDates"
LICENCE = "https://creativecommons.org/licenses/by/3.0/au/"
ATTRIBUTION = ("Contains AusTender contract-notice data published by the Australian Government "
               "Department of Finance, licensed under CC BY 3.0 AU " + LICENCE +
               ". Filtered and classified by Henderson Defence Supply-Chain Radar; "
               "not endorsed by the Commonwealth.")
FIELDS = {"contractPublished", "contractLastModified"}
AGENCIES = {"department of defence", "australian submarine agency", "department of veterans' affairs"}
MARINE = re.compile(r"\b(marine|maritime|naval|vessel|ship|shipbuilding|submarine|henderson|hydraulic|corrosion|cabling|switchboard|hmas|frigate|boat|docking)\w*\b", re.I)


def windows(start, end):
    start, end = utc_datetime(start), utc_datetime(end)
    if not start < end:
        raise ValueError("start must be earlier than end")
    if end - start > timedelta(days=90):
        raise ValueError("Each requested interval is bounded to 90 days")
    while start < end:
        stop = min(start + timedelta(days=1), end)
        yield utc_iso(start), utc_iso(stop)
        start = stop


def date_url(field, start, end):
    if field not in FIELDS:
        raise ValueError("Unsupported date field; only contractPublished/contractLastModified")
    return f"{BASE}/{field}/{utc_iso(start)}/{utc_iso(end)}"


def parse_package(body):
    try:
        package = json.loads(body)
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Malformed AusTender JSON") from exc
    if not isinstance(package, dict) or not isinstance(package.get("releases"), list):
        raise ValueError("AusTender package requires releases array")
    if not isinstance(package.get("links", {}), dict):
        raise ValueError("AusTender links must be an object")
    for release in package["releases"]:
        if not isinstance(release, dict) or not release.get("ocid") or not release.get("id"):
            raise ValueError("Each release requires ocid and id")
    return package


def agency(release):
    for party in release.get("parties", []):
        if "procuringEntity" in party.get("roles", []):
            return party.get("name", ""), "parties/procuringEntity"
    return release.get("buyer", {}).get("name", ""), "buyer (fallback)"


def normalize(package, snapshot):
    """Keep Defence agency context; marine relevance is explicit, never a location guess."""
    result = []
    for i, release in enumerate(package["releases"]):
        buyer, buyer_method = agency(release)
        if buyer.casefold() not in AGENCIES:
            continue
        for j, contract in enumerate(release.get("contracts", [])):
            official_id = contract.get("id")
            if not official_id:
                raise ValueError("Contract lacks official identity")
            pointer = f"/releases/{i}/contracts/{j}"
            evidence_id = f"cn:{snapshot['sha256'][:16]}:{i}:{j}"
            description = contract.get("description", "")
            # The process OCID is stable across contract amendments; retain official IDs verbatim.
            identity = f"cn:{release['ocid']}" if len(release["contracts"]) == 1 else f"cn:{release['ocid']}:{official_id}"
            source = dict(source_id="austender", url=snapshot["url"], accessed_at=snapshot["accessed_at"],
                          evidence_id=evidence_id, snapshot_sha256=snapshot["sha256"], pointer=pointer,
                          notice_id=official_id, release_id=release["id"], source_date=release.get("date"))
            result.append(Opportunity(
                id=identity, source_record_id=official_id, source_ids=["austender"],
                title=description or contract.get("title") or official_id, summary=description,
                buyer=buyer, record_kind="contract_context", lifecycle="awarded", review_state="reviewed",
                publication_state="context_only", sources=[source], rights=["austender"],
                close_precision="not_applicable", contract_period=contract.get("period", {}),
                source_modified_at=release.get("date"), first_seen_at=snapshot["accessed_at"],
                last_seen_at=snapshot["accessed_at"], verified_at=snapshot["accessed_at"],
                attribution=[ATTRIBUTION] if package.get("license") == LICENCE else [],
                classification_evidence=[evidence_id],
                value_context={**contract.get("value", {}), "meaning": "Prime contract value; not available subcontract spend"},
                evidence_flags={"licence_declared": package.get("license") == LICENCE,
                                "package_licence": package.get("license"), "ocid": release["ocid"],
                                "release_id": release["id"], "tags": release.get("tag", []),
                                "buyer_mapping": buyer_method, "marine_candidate": bool(MARINE.search(description)),
                                "unspsc": [item.get("classification", {}) for item in contract.get("items", [])]},
                warnings=[] if package.get("license") == LICENCE else ["Package has no established licence declaration; held from export."],
            ))
    return result


def _url_key(url):
    p = urlsplit(url)
    return p.scheme, p.netloc, p.path, tuple(sorted(parse_qsl(p.query)))


def _licence_history(records, repo):
    for record in records:
        if record.evidence_flags.get("licence_declared"):
            continue
        old = repo.get_record(record.id)
        if (old and old.evidence_flags.get("release_id") == record.evidence_flags.get("release_id")
                and (old.evidence_flags.get("licence_declared") or old.evidence_flags.get("licence_evidence"))):
            record.evidence_flags["licence_evidence"] = old.evidence_flags.get("licence_evidence") or old.sources[0]
            record.attribution = list(old.attribution)
            record.warnings = ["This response omits the licence; attribution relies on the cited date-package evidence for the same release."]
    return records


def _checked(policy, url, expected_path):
    result = validate_fetch_url(policy, url, expected_path=expected_path)
    if isinstance(result, tuple) and not result[0]:
        raise ValueError(result[1])


def fetch_window(repo, client, raw_root, field, start, end, at, *, max_pages=100):
    url = date_url(field, start, end)
    expected_path = urlsplit(url).path
    seen, snapshots, releases, records = set(), [], [], []
    try:
        while url:
            _checked(client.policy, url, expected_path)
            if _url_key(url) in seen:
                raise ValueError("Repeated pagination URL")
            if len(seen) >= max_pages:
                raise ValueError("Page cap reached before terminal page")
            seen.add(_url_key(url))
            response = client.get(url, expected_path=expected_path)
            snapshot = save_snapshot(raw_root, "austender", url, response.body, at,
                                     headers=response.headers, final_url=response.url)
            snapshots.append(snapshot)
            # Evidence remains available after partial failure; current records promote only at completion.
            snapshot_id = repo.add_snapshot(snapshot)
            package = parse_package(response.body)
            records.extend(_licence_history(normalize(package, snapshot), repo))
            releases.extend(dict(ocid=r["ocid"], release_id=r["id"], payload=r,
                                 snapshot_id=snapshot_id, event_at=r.get("date")) for r in package["releases"])
            url = package.get("links", {}).get("next")
            if url is not None and (not isinstance(url, str) or not url):
                raise ValueError("Invalid next URL")
        return repo.complete_window("austender", field, start, end, snapshots, releases, records, at, live=True)
    except (ValueError, OSError, TypeError, KeyError) as exc:
        return repo.record_run("austender", field, start, end, "partial" if snapshots else "failed", at,
                               pages=len(snapshots), records=len(releases), error=str(exc), live=True)


def fetch(repo, client, raw_root, field, start, end, at, *, max_pages=100):
    runs = []
    for begin, stop in windows(start, end):
        run = fetch_window(repo, client, raw_root, field, begin, stop, at, max_pages=max_pages)
        runs.append(run)
        if run["state"] != "complete":
            break
    return runs


def incremental_start(repo, field, start=None, overlap_days=7):
    checkpoint = repo.checkpoint("austender", field)
    if checkpoint:
        return utc_iso(utc_datetime(checkpoint) - timedelta(days=overlap_days))
    if not start:
        raise ValueError("Initial incremental refresh requires an explicit bounded --start")
    return utc_iso(start)


def replay_saved(repo, directory, raw_root):
    """Replay original retrieval metadata. An unfinished saved chain remains partial."""
    directory = Path(directory)
    available = {}
    for meta_path in sorted(directory.glob("*.meta.json")):
        meta = json.loads(meta_path.read_text())
        url = meta.get("url", "")
        if not url.startswith("https://api.tenders.gov.au/ocds/") or meta.get("status") != 200:
            continue
        stem = meta_path.name.removesuffix(".meta.json")
        body_path = next((p for p in (directory / (stem + ".body"), directory / (stem + ".json")) if p.exists()), None)
        if body_path is None:
            continue
        headers = {k.lower(): v for k, v in meta.get("headers", {}).items()}
        at = meta.get("accessed_at")
        if not at and headers.get("date"):
            at = utc_iso(parsedate_to_datetime(headers["date"]))
        if not at:
            raise ValueError(f"{meta_path.name}: original access time required; replay cannot renew verification")
        available[_url_key(url)] = (url, body_path.read_bytes(), meta, at)
    runs = []
    roots = sorted([v for v in available.values() if not urlsplit(v[0]).query], key=lambda v: "/findById/" in v[0])
    for initial, _, _, original_at in roots:
        path = urlsplit(initial).path
        parts = path.split("/")
        dated = "/findByDates/" in path
        field, start, end = parts[-3:] if dated else ("findById", original_at, original_at)
        snapshots, releases, records, seen = [], [], [], set()
        url = initial
        try:
            while url:
                key = _url_key(url)
                if key in seen or key not in available:
                    raise ValueError("Saved chain incomplete or repeated; no promotion or live checkpoint")
                if urlsplit(url).path != path:
                    raise ValueError("Saved next URL changes query window")
                seen.add(key)
                _, body, meta, at = available[key]
                snap = save_snapshot(raw_root, "austender", url, body, at, headers=meta.get("headers"), final_url=meta.get("final_url"))
                snapshots.append(snap)
                sid = repo.add_snapshot(snap)
                package = parse_package(body)
                records.extend(_licence_history(normalize(package, snap), repo))
                releases.extend(dict(ocid=r["ocid"], release_id=r["id"], payload=r, snapshot_id=sid, event_at=r.get("date")) for r in package["releases"])
                url = package.get("links", {}).get("next")
            runs.append(repo.complete_window("austender", field, start, end, snapshots, releases, records, original_at, live=False))
        except (ValueError, TypeError, KeyError) as exc:
            runs.append(repo.record_run("austender", field, start, end, "partial", original_at,
                                        pages=len(snapshots), records=len(releases), error=str(exc), live=False))
    if not roots:
        raise ValueError("No saved AusTender packages with original metadata found")
    return runs
