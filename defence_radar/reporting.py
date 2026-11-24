"""Deterministic, rights-filtered preparation for M7 output formats."""
from dataclasses import asdict
from datetime import datetime, timezone
from copy import deepcopy

from .classify import classify
from .evidence import digest
from .match import match, enrich_scope
from .models import Opportunity, Profile, PublicationState, utc_datetime
from .policy import publication_allowed
from .storage import material_state


def _profile_view(profile, audience):
    data = profile.to_dict() if hasattr(profile, "to_dict") else dict(profile)
    if audience != "public":
        return data
    allowed = set(data.get("public_fields", []))
    return {k: v for k, v in data.items() if k in allowed and k not in {"credentials", "public_fields"}}


def _profile_for_match(profile, audience):
    if audience != "public":
        return profile
    data = profile.to_dict() if hasattr(profile, "to_dict") else dict(profile)
    if "credentials" not in data.get("public_fields", []):
        data["credentials"] = {}
        return Profile.from_dict(data)
    return profile


def _public_sources(record, policies):
    by_id = {p.id: p for p in policies}
    for source in record.sources:
        source.pop("path", None)
        source.pop("local_path", None)
        for key in list(source):
            folded = key.casefold().replace("-", "_")
            if "path" in folded or any(secret in folded for secret in ("credential", "authorization", "auth", "cookie", "token", "password", "api", "secret")):
                source.pop(key, None)
        policy = by_id.get(source.get("source_id"))
        if policy:
            source["licence_url"] = policy.licence_url


def record_states(payload):
    """Stable material-state hashes keyed by record ID; ignores retrieval-only changes."""
    return {row["record"]["id"]: {"hash": digest({
        "material": material_state(row["record"]),
        "match": {k: row["match"].get(k) for k in
                  ("score", "components", "matched_capabilities", "missing_capabilities", "exclusions", "eligibility", "shortlist", "taxonomy_version", "rule_version")},
    }), "lifecycle": row["record"]["lifecycle"]} for row in payload.get("rows", [])}


def prepare_payload(repo, profile, taxonomy, policies, as_of, period, audience="public", include_speculative=False, coverage=None):
    profile_data = profile.to_dict() if hasattr(profile, "to_dict") else dict(profile)
    profile_hash = digest(profile_data)
    public = audience == "public"
    match_profile = _profile_for_match(profile, audience)
    allowed, held, held_by_source = [], 0, {}
    irrelevant = 0
    # Apply record level rights before classification, matching, or derived text.
    for raw in repo.list_records():
        record = raw if isinstance(raw, Opportunity) else Opportunity.from_dict(raw)
        if not publication_allowed(record, policies, audience)[0]:
            held += 1
            for source_id in record.source_ids:
                held_by_source[source_id] = held_by_source.get(source_id, 0) + 1
            continue
        if any(utc_datetime(s["accessed_at"]) > utc_datetime(as_of) for s in record.sources):
            raise ValueError("Historical as_of precedes required source evidence; use a historical snapshot")
        classified = classify(enrich_scope(record, taxonomy), as_of)
        if classified.review_state.value == "reviewed" and (classified.status_class or classified.lifecycle.value in {"closed", "awarded", "cancelled", "superseded"}):
            classified.publication_state = PublicationState.context_only if classified.record_kind.value.endswith("context") else PublicationState.publishable
        allowed.append(classified)
    rows = []
    for record in allowed:
        if record.review_state.value != "reviewed" or record.publication_state.value == "held":
            held += 1
            for source_id in record.source_ids:
                held_by_source[source_id] = held_by_source.get(source_id, 0) + 1
            continue
        matched = match(record, match_profile, taxonomy, as_of)
        matched.profile_hash = profile_hash
        if public and "id" not in profile.public_fields:
            matched.profile_id = "profile-" + profile_hash[:12]
        if record.record_kind.value == "contract_context" and not (matched.score > 0 or record.evidence_flags.get("marine_candidate") is True):
            irrelevant += 1
            continue
        if record.status_class and record.status_class.value == "speculative" and not include_speculative:
            continue
        # Preserve classification/context and match results as explicit, identifiable rows.
        data = record.to_dict()
        if public:
            _public_sources(record, policies)
            data = record.to_dict()
        rows.append({"record": data, "match": asdict(matched)})
    priority = {"confirmed_open": 0, "published_future_scope": 1, "speculative": 2, None: 3}
    rows.sort(key=lambda x: (priority.get(x["record"]["status_class"], 4), -x["match"]["score"], x["record"]["close_at_utc"] or "z", x["record"]["id"]))
    if public:
        profile_view = _profile_view(profile, audience)
    else:
        profile_view = _profile_view(profile, audience)
    cov = deepcopy(coverage or {})
    cov["held"] = {"total": held, "by_source": held_by_source}
    cov["excluded_irrelevant"] = irrelevant
    cov["confirmed_open"] = sum(r["record"]["status_class"] == "confirmed_open" for r in rows)
    cov["context_records"] = sum(r["record"]["record_kind"].endswith("context") for r in rows)
    prev = repo.previous_build(profile_hash, audience, period) if repo else None
    current_states = record_states({"rows": rows})
    old_states = (prev or {}).get("record_states", {})
    current_ids, old_ids = set(current_states), set(old_states)
    closed_lifecycles = {"closed", "awarded", "cancelled", "superseded"}
    delta = {"new": sorted(current_ids-old_ids),
             "changed": sorted(i for i in current_ids & old_ids if current_states[i] != old_states[i]),
             "closed": sorted(i for i in current_ids & old_ids if current_states[i]["lifecycle"] in closed_lifecycles
                              and isinstance(old_states[i], dict) and old_states[i].get("lifecycle") not in closed_lifecycles)}
    return {"schema_version": 1, "as_of": as_of, "period": period, "audience": audience,
            "profile": profile_view, "profile_hash": profile_hash,
            "taxonomy_version": taxonomy["version"],
            "rule_versions": {"classification": "status-1", "matching": "match-1"},
            "rows": rows, "coverage": cov, "delta": delta,
            "attribution": sorted({a for row in rows for a in row["record"].get("attribution", [])})}
