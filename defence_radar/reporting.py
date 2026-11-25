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


from datetime import date, timedelta
from zoneinfo import ZoneInfo

AWST = ZoneInfo("Australia/Perth")
ATM_SEARCH = "https://www.tenders.gov.au/atm"
ICN_GATEWAY = "https://gateway.icn.org.au/"


def week_bounds(period):
    """Seven AWST calendar days ending on the period (week-ending) date, inclusive."""
    end = date.fromisoformat(str(period))
    return {"start": (end - timedelta(days=6)).isoformat(), "end": end.isoformat(), "zone": "Australia/Perth"}


def _awst_date(value):
    try: return utc_datetime(value).astimezone(AWST).date().isoformat()
    except (ValueError, TypeError): return None


def _amount(record):
    try: return float(str(record.get("value_context", {}).get("amount", "")).replace(",", ""))
    except ValueError: return None


def market_summary(rows, week, taxonomy):
    """Who is winning relevant awarded work. Awards are context, never opportunities."""
    awards = [r for r in rows if r["record"].get("status_class") == "awarded_context"]
    in_week = [r for r in awards if week["start"] <= (_awst_date(r["record"].get("source_published_at")) or "") <= week["end"]]
    scope = in_week
    suppliers, buyers, caps = {}, {}, {}
    for r in scope:
        rec, fit = r["record"], r["match"]
        amount = _amount(rec) or 0.0
        for s in rec.get("evidence_flags", {}).get("suppliers", []) or [{"name": rec.get("prime") or "Not published"}]:
            e = suppliers.setdefault(s.get("name") or "Not published", {"name": s.get("name") or "Not published", "count": 0, "value": 0.0,
                                     "locality": s.get("locality", ""), "region": s.get("region", ""), "titles": [], "best_score": 0, "notice_ids": []})
            e["count"] += 1; e["value"] += amount; e["best_score"] = max(e["best_score"], fit.get("score", 0))
            if rec.get("title") not in e["titles"]: e["titles"].append(rec.get("title"))
            e["notice_ids"].append(rec.get("source_record_id"))
        unit = rec.get("evidence_flags", {}).get("buyer_branch") or rec.get("buyer") or "Not published"
        b = buyers.setdefault(unit, {"name": unit, "agency": rec.get("buyer", ""), "count": 0, "value": 0.0})
        b["count"] += 1; b["value"] += amount
        for k in fit.get("matched_capabilities", []):
            c = caps.setdefault(k, {"id": k, "label": taxonomy["categories"].get(k, {}).get("label", k), "count": 0, "value": 0.0})
            c["count"] += 1; c["value"] += amount
    order = lambda d: sorted(d.values(), key=lambda x: (-x["value"], -x["count"], x["name"] if "name" in x else x["id"]))
    for e in suppliers.values(): e["value"] = round(e["value"], 2); e["titles"] = e["titles"][:4]; e["notice_ids"] = sorted(set(e["notice_ids"]))[:6]
    for d in (buyers, caps):
        for e in d.values(): e["value"] = round(e["value"], 2)
    return {"window": week, "awards_in_week": len(in_week), "relevant_awards_total": len(awards),
            "total_value": round(sum(_amount(r["record"]) or 0.0 for r in scope), 2), "currency": "AUD",
            "suppliers": order(suppliers), "buyers": sorted(buyers.values(), key=lambda x: (-x["count"], -x["value"], x["name"])), "capabilities": order(caps),
            "wa_suppliers": [e for e in order(suppliers) if e["region"] == "WA"],
            "note": "Awarded contract notices published on AusTender in the reporting week. Values are the head-contract value "
                    "reported by the agency, not available subcontract spend. These are not open opportunities."}


def _money(v):
    return f"${v/1e6:.1f}m" if v >= 1e6 else f"${v/1e3:.0f}k" if v >= 1e3 else f"${v:.0f}"


def recommended_actions(rows, market, taxonomy):
    """Deterministic, evidence-linked next steps for a BD manager. No action implies a bid route exists unless verified."""
    actions = []
    open_rows = [r for r in rows if r["record"].get("status_class") == "confirmed_open" and r["match"].get("score", 0) >= 25]
    for r in sorted(open_rows, key=lambda x: (x["record"].get("close_at_utc") or "9999", -x["match"]["score"]))[:3]:
        rec = r["record"]; route = rec.get("application_route") or {}
        actions.append({"priority": 1, "kind": "bid", "text": f"Decide bid/no-bid on '{rec.get('title')}' (fit {r['match']['score']}/100) before it closes; "
                        "read the full ATM documents and conditions on AusTender first.", "url": route.get("url") or (rec.get("sources") or [{}])[0].get("url")})
    future = [r for r in rows if r["record"].get("status_class") == "published_future_scope" and r["match"].get("score", 0) >= 45]
    for r in sorted(future, key=lambda x: -x["match"]["score"])[:2]:
        rec = r["record"]
        actions.append({"priority": 2, "kind": "prepare", "text": f"Prepare a capability statement for the published future scope '{rec.get('title')}' and contact the listed enquiry route.",
                        "url": (rec.get("application_route") or {}).get("url") or (rec.get("sources") or [{}])[0].get("url")})
    awards = sorted((r for r in rows if r["record"].get("status_class") == "awarded_context" and r["match"].get("score", 0) >= 45),
                    key=lambda x: (-x["match"]["score"], -(_amount(x["record"]) or 0)))
    seen = set()
    for r in awards:
        rec = r["record"]; who = rec.get("prime") or ""
        if not who or who in seen: continue
        seen.add(who)
        sup = (rec.get("evidence_flags", {}).get("suppliers") or [{}])[0]
        where = ", ".join(x for x in (sup.get("locality"), sup.get("region")) if x)
        amount = _amount(rec)
        caps = ", ".join(taxonomy["categories"].get(k, {}).get("label", k) for k in r["match"].get("matched_capabilities", [])) or "marine work"
        actions.append({"priority": 3, "kind": "teaming", "text": f"Approach {who.title()}{' (' + where + ')' if where else ''} as a potential subcontract or teaming partner: "
                        f"they won '{rec.get('title')}' ({rec.get('source_record_id')}{', ' + _money(amount) if amount else ''}) in {caps}.",
                        "url": (rec.get("sources") or [{}])[0].get("url")})
        if len(seen) >= 3: break
    if market.get("buyers"):
        top = market["buyers"][0]
        actions.append({"priority": 4, "kind": "engage", "text": f"Most active relevant buyer this week: {top['name']} ({top['count']} awards, {_money(top['value'])}). "
                        "Make sure your capability statement reaches them, and watch AusTender for their approaches to market.", "url": ATM_SEARCH})
    if not open_rows:
        actions.append({"priority": 5, "kind": "check", "text": "No verified open tender was imported this week. Check AusTender Current ATMs (filter: Department of Defence) "
                        "and set up the free AusTender email notifications for UNSPSC 25111900, 26120000, 39120000 and 40150000.", "url": ATM_SEARCH})
    actions.append({"priority": 6, "kind": "check", "text": "Check ICN Gateway for Henderson-precinct work packages from primes (packages are published there, not ingested here).", "url": ICN_GATEWAY})
    return actions


CONTEXT_MIN_SCORE = 25  # awarded-contract context below "possible" fit is market noise for this profile


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
    visible = set(data.get("public_fields", []))
    for key, empty in {"credentials": {}, "capabilities": [], "activities": [], "service_regions": [],
                       "national_supply": False, "exclusions": [], "materials": [], "processes": [],
                       "experience": [], "capacity": ""}.items():
        if key not in visible: data[key] = empty
    return Profile.from_dict(data)


def _public_sources(record, policies):
    by_id = {p.id: p for p in policies}
    for source in record.sources:
        source.pop("path", None)
        source.pop("local_path", None)
        for key in list(source):
            folded = key.casefold().replace("-", "_")
            if folded == "api_url": continue  # public provenance URL, not a credential
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
        if classified.review_state.value == "reviewed" and classified.status_class is not None and classified.status_class.value != "held":
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
        if record.record_kind.value == "contract_context" and matched.score < CONTEXT_MIN_SCORE:
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
    week = week_bounds(period)
    market = market_summary(rows, week, taxonomy)
    actions = recommended_actions(rows, market, taxonomy)
    return {"schema_version": 1, "as_of": as_of, "period": period, "audience": audience,
            "profile": profile_view, "profile_hash": profile_hash,
            "taxonomy_version": taxonomy["version"],
            "rule_versions": {"classification": "status-2", "matching": "match-2"},
            "rows": rows, "coverage": cov, "delta": delta,
            "week": week, "market": market, "actions": actions,
            "attribution": sorted({a for row in rows for a in row["record"].get("attribution", [])})}
