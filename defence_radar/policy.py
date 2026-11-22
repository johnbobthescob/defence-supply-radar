"""Conservative source access and publication policy checks."""
from urllib.parse import urlparse


def publication_allowed(record, policies, audience):
    by_id = {p.id: p for p in policies}
    source_ids = set(record.source_ids) | set(record.rights)
    if not source_ids or not record.sources:
        return False, "missing provenance"
    if not set(by_id).intersection(source_ids) or any(sid not in by_id for sid in source_ids):
        return False, "missing source policy"
    if not record.rights:
        return False, "missing rights provenance"
    if not record.attribution:
        return False, "missing attribution"
    for sid in source_ids:
        policy = by_id[sid]
        if policy.access_mode == "disabled":
            return False, f"source disabled: {sid}"
        if policy.rights_status not in {"licensed", "permission_documented"}:
            return False, f"source rights not verified: {sid}"
        if audience not in policy.allowed_audiences:
            return False, f"audience not permitted: {sid}"
    if audience not in {"research", "public"}:
        return False, "audience not permitted"
    if "austender" in source_ids:
        flags = record.evidence_flags
        if not (flags.get("licence_declared") or flags.get("licence_evidence")):
            return False, "AusTender licence provenance missing"
    return True, "permitted"


def validate_fetch_url(policy, url, expected_path=None):
    p = urlparse(url)
    if p.scheme != "https" or not p.hostname or p.username is not None or p.password is not None:
        return False, "URL must be HTTPS without user information"
    try:
        port = p.port
    except ValueError:
        return False, "invalid port"
    if port not in (None, 443):
        return False, "port must be 443"
    if p.fragment:
        return False, "fragments are not permitted"
    if policy.access_mode in {"disabled", "local_only", "manual_reference"}:
        return False, "source mode does not permit fetching"
    if p.hostname.lower() not in {h.lower() for h in policy.allowed_hosts}:
        return False, "host is outside source allowlist"
    path = p.path or "/"
    if expected_path is not None and path != expected_path:
        return False, "path does not match expected path"
    if not any(path == prefix.rstrip("/") or path.startswith(prefix.rstrip("/") + "/")
                 for prefix in policy.allowed_path_prefixes):
        return False, "path is outside source allowlist"
    return True, "permitted"
