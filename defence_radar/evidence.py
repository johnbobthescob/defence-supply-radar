"""Immutable evidence snapshots and canonical content hashes."""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def save_snapshot(root, source_id, url, body, accessed_at, status=200, headers=None, final_url=None):
    if not isinstance(body, bytes):
        raise TypeError("body must be bytes")
    sha = hashlib.sha256(body).hexdigest()
    clean = {}
    for key, value in (headers or {}).items():
        name = str(key).lower()
        if name in {"content-type", "last-modified", "etag", "retry-after"}:
            clean[name] = str(value)
    content_type = clean.get("content-type")
    parsed = urlparse(url)
    ext = {"application/json": ".json", "text/plain": ".txt", "application/pdf": ".pdf"}.get((content_type or "").split(";")[0].lower(), ".bin")
    root = Path(root)
    rel = Path("raw") / re.sub(r"[^A-Za-z0-9_.-]", "_", source_id) / sha[:2] / (sha + ext)
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation means concurrent/repeated retrievals cannot replace evidence.
    try:
        with target.open("xb") as stream:
            stream.write(body)
    except FileExistsError:
        pass
    metadata = {"source_id": source_id, "url": url, "final_url": final_url or url,
                "accessed_at": accessed_at, "status": status, "headers": clean,
                "sha256": sha, "path": rel.as_posix(), "content_type": content_type}
    # Each retrieval has its own immutable ledger entry, even when bytes are identical.
    ledger = root / "snapshots" / re.sub(r"[^A-Za-z0-9_.-]", "_", source_id)
    ledger.mkdir(parents=True, exist_ok=True)
    identity = digest(metadata)
    entry = ledger / (identity + ".json")
    try:
        with entry.open("x", encoding="utf-8") as stream:
            stream.write(canonical_json(metadata))
    except FileExistsError:
        pass
    return metadata
