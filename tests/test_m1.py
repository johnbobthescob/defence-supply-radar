import json
from pathlib import Path
import pytest
from defence_radar.models import Opportunity
from defence_radar.config import load_profile, load_sources
from defence_radar.cli import main

ROOT=Path(__file__).resolve().parents[1]
SRC={"source_id":"s1","url":"https://example.gov.au/item","accessed_at":"2026-11-22T10:00:00Z","evidence_id":"e1","snapshot_sha256":"a"*64,"pointer":"/releases/0"}
BASE={"id":"opp-1","source_record_id":"CN-1","source_ids":["s1"],"title":"Example","record_kind":"procurement","sources":[SRC]}

def test_opportunity_roundtrip_and_conservative_defaults():
    obj=Opportunity.from_dict(BASE)
    assert Opportunity.from_dict(obj.to_dict()).to_dict()==obj.to_dict()
    assert obj.publication_state.value=="held" and obj.status_class is None

@pytest.mark.parametrize("change", [
    {"source_ids":[]}, {"record_kind":"invented"},
    {"sources":[{**SRC,"accessed_at":"2026-11-22T10:00:00"}]},
    {"sources":[{**SRC,"snapshot_sha256":"bad"}]},
    {"unexpected":True},
    {"sources":[]}, {"title":""}, {"freshness_state":"currentish"},
    {"close_at_utc":"2026-12-01T00:00:00Z"},
])
def test_opportunity_rejects_bad_fields(change):
    with pytest.raises(ValueError): Opportunity.from_dict({**BASE,**change})

def test_private_profile_fields_and_taxonomy_validation(tmp_path):
    profile=load_profile(ROOT/"examples/sme_profile.json",ROOT/"config/taxonomy.json")
    assert profile.fictional and profile.credentials=={}
    bad=tmp_path/"bad.json"; data=json.loads((ROOT/"examples/sme_profile.json").read_text()); data["capabilities"]=["made_up"]
    bad.write_text(json.dumps(data))
    with pytest.raises(ValueError,match="made_up"): load_profile(bad,ROOT/"config/taxonomy.json")

def test_help_has_no_database_side_effect(capsys,tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as ex: main(["--help"])
    assert ex.value.code==0
    assert not list(tmp_path.rglob("*.sqlite3"))

def test_missing_rights_never_grants_audience():
    policies=load_sources(ROOT/"config/sources.json")
    for p in policies:
        if p.rights_status in {"restricted","unverified"}: assert p.allowed_audiences==[]

def test_bad_email_is_warning_only():
    route={"purpose":"enquire","url":None,"email":"not an email","instructions":"","verified_at":None,"evidence_id":None,"account_required":"unknown"}
    obj=Opportunity.from_dict({**BASE,"application_route":route})
    assert obj.application_route["email"] is None and obj.warnings
