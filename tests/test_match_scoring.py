"""Realistic scoring tests for the explainable match-2 capability scorer."""
import pytest

from defence_radar.classify import classify
from defence_radar.config import load_taxonomy, load_profile
from defence_radar.match import match
from defence_radar.models import Opportunity

NOW = "2026-11-23T02:00:00Z"
TAX = load_taxonomy("config/taxonomy.json")
PROFILE = load_profile("examples/sme_profile.json")
MARITIME = "NSSG - Maritime Sustainment Division"
CAPS = dict(capability=45, domain=15, activity=15, delivery=15, specificity=10)


def contract(title, unspsc=None, branch=MARITIME, summary=None, n=1):
    evidence_id = f"cn:{'b' * 16}:0:{n}"
    flags = {"licence_declared": True, "unspsc": [{"scheme": "UNSPSC", "id": unspsc}] if unspsc else [],
             "buyer_branch": branch, "buyer_division": "",
             "suppliers": [dict(name="Example Marine Pty Ltd", locality="Henderson", region="WA", postcode="6166")]}
    record = Opportunity(
        id=f"cn:ocid-{n}", source_record_id=f"CN{n}", source_ids=["austender"], title=title,
        summary=title if summary is None else summary, buyer="Department of Defence",
        record_kind="contract_context", lifecycle="awarded", review_state="reviewed",
        publication_state="context_only", rights=["austender"], close_precision="not_applicable",
        verified_at=NOW, first_seen_at=NOW, last_seen_at=NOW,
        sources=[dict(source_id="austender", url="https://www.tenders.gov.au/Cn/Show/x", accessed_at=NOW,
                      evidence_id=evidence_id, snapshot_sha256="c" * 64, pointer="/releases/0/contracts/0")],
        classification_evidence=[evidence_id], attribution=["Source: AusTender (CC BY 3.0 AU)"],
        evidence_flags=flags)
    return classify(record, NOW)


def run(title, unspsc=None, branch=MARITIME, **kw):
    return match(contract(title, unspsc, branch, **kw), PROFILE, TAX, NOW)


def text(result):
    return " | ".join(result.reasons).casefold()


def scope(text_="Marine hydraulic hose repair", **changes):
    data = dict(id="scope1", source_record_id="s1", source_ids=["official_manual"], title=text_, summary=text_,
                record_kind="planned_scope", review_state="reviewed", verified_at=NOW, classification_evidence=["e1"],
                sources=[dict(source_id="official_manual", url="https://www.defence.gov.au/s", accessed_at=NOW,
                              evidence_id="e1", snapshot_sha256="a" * 64, pointer="p1")],
                evidence_flags={"authoritative_scope": True, "published_scope": True, "specific_scope": True},
                locations=[dict(name="Henderson", role="worksite", evidence_id="e1")])
    data.update(changes)
    return classify(Opportunity.from_dict(data), NOW)


def test_hydraulic_components_maritime_branch():
    r = run("Hydraulic Components", "25170000")
    assert r.score >= 60 and r.band in {"good", "strong"}
    t = text(r)
    assert "hydraulics and pneumatics" in t and "maritime" in t
    assert "hydraulics_pneumatics" in r.matched_capabilities


def test_marine_equipment():
    r = run("Marine Equipment", "39120000")
    assert r.score >= 45 and r.band in {"good", "strong"}


def test_electrical_spare_parts_strong():
    r = run("Electrical Spare Parts", "26120000")
    assert r.score >= 70 and r.band == "strong"
    assert "26120000" in text(r)


def test_electrical_without_maritime_signal_is_capped():
    for branch in ("Army Headquarters", ""):
        r = run("Electrical Equipment", "26120000", branch=branch)
        assert r.score <= 50
        assert "capped at" in text(r)


def test_vehicle_spare_parts_non_maritime_capped_30():
    r = run("Vehicle Spare Parts", "39120000", branch="Army Headquarters")
    assert r.score <= 30
    assert "non-maritime platform" in text(r)


@pytest.mark.parametrize("title,code", [
    ("Catering Services", "90101600"), ("Software Licence", "43230000"),
    ("ICT Support Services", "81112300"), ("Legal Services", "80120000"),
    ("Recruitment Services", "80111700")])
def test_off_profile_services_are_low(title, code):
    r = run(title, code)
    assert r.score <= 10 and r.band == "low" and not r.shortlist


def test_shipping_containers_is_not_a_ship():
    r = run("Shipping Containers", "24110000")
    assert r.band == "low"


def test_negated_hydraulics_not_awarded():
    r = run("Marine works excluding hydraulic hose")
    assert "hydraulics_pneumatics" not in r.matched_capabilities
    assert "hydraulics and pneumatics" not in text(r)
    assert r.components["capability"] == 0


def test_domain_only_generic_purchase():
    r = run("Watercraft Spare Parts", "24140000")
    assert 1 <= r.score <= 35
    assert r.components["capability"] == 0
    assert "no specific capability named" in text(r)


def test_no_capability_no_domain_zero_even_with_henderson():
    rec = contract("Office Chairs", None, branch="Army Headquarters")
    rec.locations = [dict(name="Henderson", role="worksite", evidence_id=rec.sources[0]["evidence_id"])]
    r = match(rec, PROFILE, TAX, NOW)
    assert r.score == 0 and r.band == "low" and r.components["delivery"] == 0
    assert "geography alone cannot create a match" in text(r)


def test_ordering_for_same_buyer():
    hyd = run("Hydraulic Components", "25170000")
    gen = run("Marine Equipment", "39120000")
    cat = run("Catering Services", "90101600")
    assert hyd.score > gen.score > cat.score


def test_determinism_and_bounds():
    cases = [("Hydraulic Components", "25170000"), ("Marine Equipment", "39120000"),
             ("Electrical Spare Parts", "26120000"), ("Catering Services", "90101600"),
             ("Watercraft Spare Parts", "24140000"), ("Marine electrical rewiring and corrosion protection", "26120000")]
    for title, code in cases:
        a, b = run(title, code), run(title, code)
        assert a == b
        assert isinstance(a.score, int) and not isinstance(a.score, bool) and 0 <= a.score <= 100
        for k, cap in CAPS.items():
            assert 0 <= a.components[k] <= cap
        assert a.reasons and a.band in {"strong", "good", "possible", "low"}


def test_awarded_context_never_shortlisted():
    r = run("Hydraulic Components", "25170000")
    assert r.score >= 60 and r.shortlist is False


def test_planned_scope_henderson_shortlisted():
    r = match(scope(), PROFILE, TAX, NOW)
    assert r.score >= 70 and r.band == "strong" and r.shortlist and not r.exclusions
    assert "henderson" in text(r)


def test_planned_scope_outside_service_area_excluded():
    far = [dict(name="Osborne", role="worksite", evidence_id="e1")]
    r = match(scope(locations=far), PROFILE, TAX, NOW)
    assert r.exclusions and not r.shortlist
    assert "outside your service area" in text(r)
