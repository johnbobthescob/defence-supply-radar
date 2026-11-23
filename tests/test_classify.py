from copy import deepcopy
import pytest
from defence_radar.classify import classify, parse_close
from defence_radar.eligibility import evaluate, extract_requirements
from defence_radar.config import load_profile
from defence_radar.models import Opportunity

NOW = "2026-11-23T02:00:00Z"
SRC = dict(source_id="official_manual", url="https://www.defence.gov.au/test", accessed_at=NOW,
           evidence_id="e1", snapshot_sha256="a"*64, pointer="section 1")


def opportunity(**changes):
    data = dict(id="test-1", source_record_id="TEST1", source_ids=["official_manual"], title="Vessel cable repair",
                record_kind="procurement", sources=[SRC], review_state="reviewed", verified_at=NOW,
                classification_evidence=["e1"], close_at_utc="2026-11-24T02:00:00Z", close_precision="instant",
                procurement_stage="procurement_EOI", evidence_flags={"authoritative_scope": True, "accepting_submissions": True},
                application_route=dict(purpose="procurement_eoi", url="https://www.defence.gov.au/test/apply", email=None,
                                       instructions="Submit the package EOI via the notice", verified_at=NOW, evidence_id="e1", account_required="unknown"))
    data.update(deepcopy(changes))
    return Opportunity.from_dict(data)


def test_specific_eoi_and_unknown_eligibility():
    result = classify(opportunity(), NOW)
    assert result.status_class.value == "confirmed_open" and result.rule_ids and result.classification_reason
    assert evaluate(result, load_profile("examples/sme_profile.json"), NOW)["status"] == "unknown"


@pytest.mark.parametrize("changes,life", [
    ({"close_at_utc": NOW}, "closed"),
    ({"close_at_utc": "2026-11-22T00:00:00Z"}, "closed"),
    ({"lifecycle": "cancelled"}, "cancelled"), ({"lifecycle": "awarded"}, "awarded"),
    ({"lifecycle": "superseded"}, "superseded"),
])
def test_inactive(changes, life):
    result = classify(opportunity(**changes), NOW)
    assert result.status_class is None and result.lifecycle.value == life


@pytest.mark.parametrize("changes", [
    {"title": "Keep Me Updated"}, {"record_kind": "registration_context"},
    {"source_ids": ["austender"], "sources": [{**SRC, "source_id": "austender"}]},
    {"verified_at": "2026-11-21T00:00:00Z"}, {"verified_at": None},
    {"review_state": "pending"}, {"classification_evidence": ["missing"]},
    {"evidence_flags": {"conflicting_evidence": True}}, {"verification_error": "HTTP 403"},
    {"close_at_utc": None, "close_precision": "date_only", "close_raw": "2026-11-24"},
    {"close_at_utc": None, "close_precision": "not_published"},
    {"evidence_flags": {"authoritative_scope": True, "accepting_submissions": True, "opens_at": "2026-11-24T00:00:00Z"}},
])
def test_cannot_claim_open(changes):
    assert classify(opportunity(**changes), NOW).status_class is None


def test_all_future_hypothesis_ongoing_gates():
    flags = {"authoritative_scope": True, "published_scope": True}
    plan = opportunity(record_kind="planned_scope", evidence_flags=flags, close_at_utc=None, close_precision="not_published", conditions=["Subject to commercial viability"])
    result = classify(plan, NOW)
    assert result.status_class.value == "published_future_scope" and result.conditions == plan.conditions
    assert classify(plan, "2026-12-24T02:00:01Z").status_class is None
    hypothesis = opportunity(record_kind="hypothesis", evidence_flags={"hypothesis_reason": "Official capacity expansion may require trade input", "missing_evidence": ["No package or buyer commitment"]}, close_at_utc=None, close_precision="not_published")
    assert classify(hypothesis, NOW).status_class.value == "speculative"
    ongoing = opportunity(close_at_utc=None, close_precision="ongoing_explicit", evidence_flags={"authoritative_scope": True, "accepting_submissions": True, "ongoing_intake": True})
    assert classify(ongoing, NOW).status_class.value == "confirmed_open"


def test_dst_dates_and_ambiguous_local_time():
    assert parse_close("2026-12-01T17:00:00", "Australia/Sydney")["close_at_utc"] == "2026-12-01T06:00:00Z"
    assert parse_close("2026-12-01T17:00:00", "Australia/Perth")["close_at_utc"] == "2026-12-01T09:00:00Z"
    assert parse_close("2026-04-05T02:30:00", "Australia/Sydney")["close_at_utc"] is None
    assert parse_close("2026-10-04T02:30:00", "Australia/Sydney")["close_at_utc"] is None
    assert parse_close("2026-12-01T17:00:00")["close_at_utc"] is None
    assert parse_close("2026-12-01")["close_precision"] == "date_only"
    assert parse_close("Login to view")["close_at_utc"] is None


@pytest.mark.parametrize("credential,status", [
    ({"value": True, "evidence": "User declaration"}, "meets_known_requirements"),
    ({"value": False, "evidence": "User declaration"}, "does_not_meet"),
    ({"value": True}, "unknown"),
    ({"value": True, "evidence": "cert", "expires_at": NOW}, "does_not_meet"),
])
def test_mandatory_requirements(credential, status):
    profile = load_profile("examples/sme_profile.json"); profile.credentials["iso9001"] = credential
    record = opportunity(eligibility=[dict(key="iso9001", strength="required", expected=True, evidence_id="e1", verified_at=NOW, text="ISO 9001 required")])
    result = evaluate(record, profile, NOW)
    assert result["status"] == status and not result["completeness"]
    record.eligibility[0]["strength"] = "preferred"
    assert evaluate(record, profile, NOW)["status"] != "does_not_meet"


def test_extraction_does_not_convert_trade_list_to_requirements():
    assert extract_requirements("NATA services, certification, ISO 9001 support. Australian SMEs encouraged.", "e1", NOW) == []
    req = extract_requirements("Suppliers must hold ISO 9001. OEM approval preferred. DISP not required.", "e1", NOW)
    assert [(r["key"], r["strength"]) for r in req] == [("iso9001", "required"), ("oem_authorisation", "preferred")]
    assert extract_requirements("DISP may be required", "e1", NOW)[0]["strength"] == "unknown"
    assert extract_requirements("DISP Level 2 is required", "e1", NOW)[0]["expected"] == "level_2"
