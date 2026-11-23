"""Conservative extraction and comparison of source-specific requirements."""
import re
from .models import utc_datetime


def extract_requirements(text, evidence_id, verified_at):
    """Only express modal requirements; category lists never imply accreditation."""
    found = []
    patterns = {"iso9001": r"\bISO\s*9001\b", "disp": r"\bDISP\b",
                "oem_authorisation": r"\bOEM (?:authori[sz]ation|approv(?:al|ed))\b",
                "australian_entity": r"\bAustralian (?:registered )?(?:business|entity|company)\b"}
    for clause in re.split(r"[.;\n]+", text):
        if re.search(r"\b(not required|no requirement|not mandatory)\b", clause, re.I):
            continue
        required = bool(re.search(r"\b(must|mandatory|required|shall)\b", clause, re.I))
        preferred = bool(re.search(r"\b(preferred|desirable)\b", clause, re.I))
        if not (required or preferred):
            continue
        keys = [key for key, pat in patterns.items() if re.search(pat, clause, re.I)] or ["unmapped_requirement"]
        for key in keys:
            level = re.search(r"\bDISP\s+(?:membership\s+)?level\s*(\d+)\b", clause, re.I) if key == "disp" else None
            found.append(dict(key=key, text=clause.strip(), strength="unknown" if required and preferred else "required" if required else "preferred",
                              expected=f"level_{level[1]}" if level else True, evidence_id=evidence_id, verified_at=verified_at))
    return found


def evaluate(record, profile, as_of):
    now = utc_datetime(as_of)
    details = []
    for requirement in record.eligibility:
        key = requirement.get("key", "unmapped_requirement")
        strength = requirement.get("strength", "unknown")
        credential = profile.credentials.get(key)
        state, reason = "unknown", "No current user-supplied credential evidence."
        source_ok = (requirement.get("evidence_id") in {s["evidence_id"] for s in record.sources}
                     and requirement.get("verified_at") and utc_datetime(requirement["verified_at"]) <= now)
        if not source_ok:
            reason = "Requirement provenance or verification is incomplete."
        elif credential and credential.get("evidence"):
            if credential.get("expires_at") and utc_datetime(credential["expires_at"]) <= now:
                state, reason = "failed", "Supplied credential has expired."
            elif credential.get("value") is None:
                reason = "Credential value is unknown."
            elif type(credential.get("value")) is type(requirement.get("expected", True)) and credential.get("value") == requirement.get("expected", True):
                state, reason = "passed", "Matches current user-supplied evidence; not independently certified."
            else:
                state, reason = "failed", "Supplied value does not meet the stated criterion."
        details.append({**requirement, "result": state, "reason": reason})
    required = [r for r in details if r.get("strength") == "required"]
    if any(r["result"] == "failed" for r in required):
        status = "does_not_meet"
    elif any(r["result"] == "unknown" for r in required) or not required:
        status = "unknown"
    else:
        status = "meets_known_requirements"
    return dict(status=status, requirements=details, completeness=record.eligibility_complete,
                limitation="Source requirements may be incomplete; confirm notice-specific requirements with the buyer." if not record.eligibility_complete else "Only the recorded requirements were compared.",
                disclaimer="Profile evidence is user-supplied. This is not official supplier approval.")
