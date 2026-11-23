"""Explainable capability fit, separate from eligibility and source permission."""
from copy import deepcopy
import re
from .evidence import digest
from .eligibility import evaluate
from .models import Opportunity, MatchResult

RULE_VERSION = "match-1"
MARINE_CONTEXT = re.compile(r"\b(marine|maritime|naval|vessels?|ship\w*|submarines?|frigates?|boats?|hmas|rmp west)\b", re.I)


def normal(text):
    return re.sub(r"[^\w]+", " ", text.casefold()).strip()


def tag_scope(text, taxonomy, evidence_id, *, existing_supplier=False):
    normalized = normal(text)
    if existing_supplier or not MARINE_CONTEXT.search(normalized):
        return []
    tags = []
    for key, category in taxonomy["categories"].items():
        for alias in category["aliases"]:
            pattern = r"\b" + re.escape(normal(alias)) + r"\b"
            spans = list(re.finditer(pattern, normalized))
            valid = [m for m in spans if not re.search(r"\b(no|not|excluding|without)\b[^.]{0,35}$", normalized[max(0, m.start()-40):m.start()])]
            if valid:
                tags.append(dict(id=key, role="core", evidence_id=evidence_id, span=alias,
                                 reason="Controlled phrase in marine scope; not a certification or supplier approval."))
                break
    return tags


def enrich_scope(record, taxonomy):
    result = Opportunity.from_dict(deepcopy(record.to_dict()))
    if not result.capabilities and result.sources:
        result.capabilities = tag_scope(result.summary or result.title, taxonomy, result.sources[0]["evidence_id"],
                                        existing_supplier=bool(result.evidence_flags.get("existing_supplier")))
    if result.capabilities and not result.activities:
        text = normal(result.summary or result.title)
        for activity, pattern in {"repair": r"\b(repair\w*|maintenance|overhaul)\b", "supply": r"\b(supply|supplies|procurement of)\b", "install": r"\b(install\w*)\b", "inspect": r"\b(inspect\w*|survey)\b", "manufacture": r"\b(manufactur\w*|fabrication)\b"}.items():
            if re.search(pattern, text):
                result.activities.append(activity)
    return result


def match(record, profile, taxonomy, as_of):
    record = enrich_scope(record, taxonomy)
    evidence_ids = {s["evidence_id"] for s in record.sources}
    tags = {}
    evidence = []
    for tag in record.capabilities:
        key = tag.get("id")
        if key in taxonomy["categories"] and tag.get("evidence_id") in evidence_ids and tag.get("span"):
            tags[key] = max(tags.get(key, 0), 2 if tag.get("role") == "core" else 1)
            evidence.append(f"{key}: {tag['span']} ({tag['evidence_id']})")
    intersection = sorted(set(tags) & set(profile.capabilities))
    components = dict(capability=0, activity=0, delivery=0, specificity=0)
    exclusions = []
    if intersection:
        components["capability"] = round(60 * sum(tags[k] for k in intersection) / sum(tags.values()))
        if set(record.activities) & set(profile.activities):
            components["activity"] = 20
            evidence.append("Explicit activity overlap: " + ", ".join(sorted(set(record.activities) & set(profile.activities))))
        elif record.activities and profile.activities:
            compatible = record.evidence_flags.get("reviewed_compatible_activities", [])
            if set(compatible) & set(profile.activities):
                components["activity"] = 10
                evidence.append("Reviewer-recorded compatible activity; verify delivery method.")
            else:
                exclusions.append("Known activity mismatch; required activity is outside the profile.")
        places = [p for p in record.locations if p.get("role") in {"worksite", "delivery"} and p.get("evidence_id") in evidence_ids]
        service = {normal(s) for s in profile.service_regions}
        if any(normal(p.get("name", "")) in service for p in places):
            components["delivery"] = 15
            evidence.append("Evidenced work/delivery location is within the declared service area.")
        elif (profile.national_supply and "supply" in profile.activities and "supply" in record.activities
              and (record.evidence_flags.get("offsite_supply") is True or any(p.get("national_supply") is True for p in places))):
            components["delivery"] = 8
            evidence.append("Explicit offsite/national supply is compatible with the declared reach.")
        elif places and (not record.evidence_flags.get("offsite_supply") or not profile.national_supply):
            exclusions.append("Known worksite is outside declared service regions; delivery ability is not established.")
        else:
            evidence.append("Delivery location unknown; supplier addresses add no geographic credit.")
        if record.evidence_flags.get("specific_scope") is True or any(len(t.get("span", "").split()) >= 2 for t in record.capabilities if t.get("id") in intersection):
            components["specificity"] = 5
    else:
        evidence.append("No evidenced capability intersects the profile; geography cannot create a match.")
    if set(profile.exclusions) & set(tags):
        exclusions.append("Scope intersects an explicit profile exclusion.")
    eligibility = evaluate(record, profile, as_of)
    if eligibility["status"] == "does_not_meet":
        exclusions.append("A mandatory eligibility requirement is not met.")
    score = sum(components.values())
    shortlist = (score >= 40 and not exclusions and record.status_class is not None
                 and record.status_class.value in {"confirmed_open", "published_future_scope"}
                 and record.review_state.value == "reviewed" and record.lifecycle.value not in {"closed", "awarded", "cancelled", "superseded"})
    return MatchResult(record.id, profile.id, digest(profile.to_dict()), taxonomy["version"], RULE_VERSION, score,
                       components, intersection, sorted(set(tags) - set(profile.capabilities)), sorted(set(evidence)), exclusions, eligibility, shortlist).validate()
