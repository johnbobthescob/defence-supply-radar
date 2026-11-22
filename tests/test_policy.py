from defence_radar.models import Opportunity, SourcePolicy
from defence_radar.policy import publication_allowed, validate_fetch_url

SRC={"source_id":"s1","url":"https://example.gov.au/item","accessed_at":"2026-11-22T10:00:00Z","evidence_id":"e1","snapshot_sha256":"a"*64,"pointer":"/"}
BASE={"id":"opp-1","source_record_id":"x","source_ids":["s1"],"title":"Example","record_kind":"procurement","sources":[SRC]}


def test_default_deny_and_mixed_rights():
    record=Opportunity.from_dict(BASE)
    good=SourcePolicy("s1",access_mode="api",rights_status="licensed",allowed_audiences=["public"])
    assert publication_allowed(record,[good],"public")[0] is False
    record=Opportunity.from_dict({**BASE,"rights":["s1"],"attribution":["Credit"]})
    bad=SourcePolicy("s2",access_mode="api",rights_status="restricted",allowed_audiences=[])
    mixed=Opportunity.from_dict({**record.to_dict(),"source_ids":["s1","s2"],"sources":[SRC,{**SRC,"source_id":"s2","evidence_id":"e2"}]})
    assert publication_allowed(mixed,[good,bad],"public")[0] is False
    assert publication_allowed(record,[good],"public")[0] is True


def test_austender_requires_licence_evidence():
    policy=SourcePolicy("austender",access_mode="api",rights_status="licensed",allowed_audiences=["public"])
    src={**SRC,"source_id":"austender"}
    base={**BASE,"source_ids":["austender"],"sources":[src],"rights":["austender"],"attribution":["AusTender"]}
    assert not publication_allowed(Opportunity.from_dict(base),[policy],"public")[0]
    assert publication_allowed(Opportunity.from_dict({**base,"evidence_flags":{"licence_declared":True}}),[policy],"public")[0]


def test_fetch_url_allowlist_and_restrictions():
    policy=SourcePolicy("s1",access_mode="api",allowed_hosts=["example.gov.au"],allowed_path_prefixes=["/api"])
    assert validate_fetch_url(policy,"https://example.gov.au/api/v1")[0]
    for url in ("http://example.gov.au/api","https://user@example.gov.au/api","https://example.gov.au:444/api",
                "https://example.gov.au/api#x","https://other.gov.au/api","https://example.gov.au/private"):
        assert not validate_fetch_url(policy,url)[0], url
    assert not validate_fetch_url(policy,"https://example.gov.au/api/v1",expected_path="/api")[0]
    policy.access_mode="manual_reference"
    assert not validate_fetch_url(policy,"https://example.gov.au/api")[0]
