from defence_radar.classify import classify
from defence_radar.config import load_taxonomy, load_profile
from defence_radar.match import match, tag_scope
from defence_radar.models import Opportunity

NOW = "2026-11-23T02:00:00Z"
TAX = load_taxonomy("config/taxonomy.json")
PROFILE = load_profile("examples/sme_profile.json")


def scope(text="Marine hydraulic hose repair", **changes):
    data = dict(id="scope1", source_record_id="s1", source_ids=["official_manual"], title=text, summary=text,
                record_kind="planned_scope", review_state="reviewed", verified_at=NOW, classification_evidence=["e1"],
                sources=[dict(source_id="official_manual", url="https://www.defence.gov.au/s", accessed_at=NOW, evidence_id="e1", snapshot_sha256="a"*64, pointer="p1")],
                evidence_flags={"authoritative_scope": True, "published_scope": True, "specific_scope": True},
                locations=[dict(name="Henderson", role="worksite", evidence_id="e1")])
    data.update(changes)
    return classify(Opportunity.from_dict(data), NOW)


def test_realistic_hydraulic_scope_outranks_generic_electronics():
    good = match(scope(), PROFILE, TAX, NOW)
    generic = match(scope("Electronic Equipment"), PROFILE, TAX, NOW)
    assert good.score >= 90 and good.band == "strong" and good.shortlist and good.reasons
    assert good.eligibility["status"] == "unknown"
    assert generic.score == 0 and not generic.shortlist


def test_no_keyword_repetition_credit_and_no_inferred_machining():
    once = tag_scope("Marine hydraulic hose repair", TAX, "e1")
    repeated = tag_scope("Marine hydraulic hose repair hydraulic hose hydraulic hose", TAX, "e1")
    assert once == repeated
    assert "precision_machining" not in {t["id"] for t in tag_scope("Marine engine component repair", TAX, "e1")}
    assert tag_scope("Existing marine hydraulic hose supplier", TAX, "e1", existing_supplier=True) == []
    assert tag_scope("Marine work excluding hydraulic hose", TAX, "e1") == []
    assert tag_scope("Shipment of hydraulic hose", TAX, "e1") == []


def test_supplier_location_and_activity_mismatch():
    result = match(scope(locations=[dict(name="Henderson", role="supplier_address", evidence_id="e1")]), PROFILE, TAX, NOW)
    assert result.components["delivery"] == 0
    mismatch = match(scope(activities=["manufacture"]), PROFILE, TAX, NOW)
    assert not mismatch.shortlist and mismatch.exclusions


def test_national_supply_requires_explicit_evidence():
    far = dict(name="Osborne", role="worksite", evidence_id="e1")
    no = match(scope(activities=["supply"], locations=[far]), PROFILE, TAX, NOW)
    assert no.components["delivery"] == 0 and not no.shortlist
    flags = {"published_scope": True, "authoritative_scope": True, "offsite_supply": True}
    yes = match(scope(activities=["supply"], locations=[far], evidence_flags=flags), PROFILE, TAX, NOW)
    assert yes.components["delivery"] == 8


def test_eligibility_failure_never_overridden_by_score():
    profile = load_profile("examples/sme_profile.json")
    profile.credentials["iso9001"] = dict(value=False, evidence="self declared")
    result = match(scope(eligibility=[dict(key="iso9001", strength="required", evidence_id="e1", verified_at=NOW)]), profile, TAX, NOW)
    assert result.score >= 90 and result.eligibility["status"] == "does_not_meet" and not result.shortlist
