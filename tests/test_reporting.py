"""Synthetic, clearly labelled M7 reporting contract tests."""
import csv
import io
import json

from defence_radar.config import load_taxonomy
from defence_radar.evidence import digest
from defence_radar.models import Opportunity, Profile, SourcePolicy
from defence_radar.reporting import prepare_payload, record_states
from defence_radar.render.briefing import render_briefing
from defence_radar.render.exports import render_csv, render_json
from defence_radar.render.common import md_text, md_inline

NOW = "2026-11-23T02:00:00Z"
TAX = load_taxonomy("config/taxonomy.json")
LICENCE = "https://creativecommons.org/licenses/by/4.0/"


class Repo:
    def __init__(self, records, previous=None): self.records, self.previous = records, previous
    def list_records(self): return self.records
    def previous_build(self, profile_hash, audience, period): return self.previous


def record(identifier="synthetic-1", **changes):
    data = dict(id=identifier, source_record_id="fixture", source_ids=["fixture_source"], rights=["fixture_source"],
                attribution=["Synthetic test source; CC BY 4.0"], title="Synthetic marine hydraulic scope", summary="Marine hydraulic hose repair",
                record_kind="planned_scope", review_state="reviewed", publication_state="publishable", verified_at=NOW,
                classification_evidence=["e1"], sources=[dict(source_id="fixture_source", url="https://example.invalid/synthetic", accessed_at=NOW,
                evidence_id="e1", snapshot_sha256="a"*64, pointer="/synthetic", licence_url=LICENCE, local_path="/secret/test")],
                evidence_flags={"published_scope": True, "authoritative_scope": True, "specific_scope": True},
                close_precision="not_published", application_route=dict(purpose="enquire", url="https://example.invalid/contact", email=None,
                instructions="Synthetic route", verified_at=NOW, evidence_id="e1", account_required="unknown"))
    data.update(changes)
    return Opportunity.from_dict(data)


def profile(**changes):
    data = dict(id="fictional-test-profile", version=1, name="Synthetic test business", fictional=True,
                public_fields=["name", "capabilities"], capabilities=["hydraulics_pneumatics"], activities=["repair"],
                service_regions=["Henderson"], national_supply=False, credentials={"secret": {"value": True, "evidence": "PRIVATE_SENTINEL"}})
    data.update(changes)
    return Profile.from_dict(data)


def policy(source="fixture_source", rights="licensed"):
    return SourcePolicy(source, access_mode="api", rights_status=rights, allowed_audiences=["public"], licence_url=LICENCE)


def test_public_rights_gate_precedes_derivations_and_hides_mixed_source_text():
    restricted = record("restricted", title="RESTRICTED_PHRASE", source_ids=["fixture_source", "unknown"], rights=["fixture_source", "unknown"],
                        sources=[record().sources[0], {**record().sources[0], "source_id": "unknown", "evidence_id": "e2"}])
    good = record("permitted", title="Synthetic permitted")
    payload = prepare_payload(Repo([restricted, good]), profile(), TAX, [policy()], NOW, "2026-W47")
    text = render_json(payload) + render_csv(payload) + render_briefing(payload)
    assert "RESTRICTED_PHRASE" not in text
    assert [x["record"]["id"] for x in payload["rows"]] == ["permitted"]


def test_private_profile_and_match_credentials_are_omitted_by_default():
    p = profile()
    payload = prepare_payload(Repo([record()]), p, TAX, [policy()], NOW, "2026-W47")
    exported = render_json(payload)
    assert "PRIVATE_SENTINEL" not in exported
    assert "credentials" not in payload["profile"]
    assert payload["rows"][0]["match"]["profile_hash"] == digest(p.to_dict())
    assert payload["rows"][0]["match"]["components"]["activity"] == 0
    assert "fictional-test-profile" not in exported


def test_csv_formula_cells_are_escaped_but_json_keeps_originals():
    r = record(title="\t@SUM(A1)", conditions=["=1+1"])
    payload = prepare_payload(Repo([r]), profile(), TAX, [policy()], NOW, "2026-W47")
    cells = next(csv.DictReader(io.StringIO(render_csv(payload))))
    assert cells["title"].startswith("'\t@")
    assert cells["conditions"] == "'=1+1"
    assert cells["id"] == "synthetic-1"
    assert json.loads(render_json(payload))["data"]["rows"][0]["record"]["title"] == "\t@SUM(A1)"


def test_markdown_escapes_html_and_syntax_and_zero_open_context_is_clear():
    assert "&lt;script&gt;" in md_text("<script>")
    assert "\\*" in md_text("*bold*")
    assert md_inline("<script>*x*") == "\\<script\\>\\*x\\*" and md_inline("a.b-c 1.5") == "a.b-c 1.5"
    context = record("context", record_kind="contract_context", status_class=None, lifecycle="awarded",
                     evidence_flags={"marine_candidate": True})
    payload = prepare_payload(Repo([context]), profile(capabilities=["hydraulics_pneumatics"], activities=[]), TAX, [policy()], NOW, "2026-W47")
    brief = render_briefing(payload)
    assert "No verified open tenders were imported this week" in brief
    assert "## Open opportunities" in brief and "Synthetic marine hydraulic scope" not in brief.split("## Upcoming")[0]
    assert "&#x27;" not in brief and "{'" not in brief


def test_delta_uses_prior_distinct_period_and_material_state_ignores_retrieval():
    p = profile()
    base = prepare_payload(Repo([]), p, TAX, [policy()], NOW, "2026-W46")
    baseline = {"manifest": {"period": "2026-W46"}, "record_states": {"synthetic-1": "old"}}
    first = prepare_payload(Repo([record()], baseline), p, TAX, [policy()], NOW, "2026-W47")
    assert first["delta"] == {"new": [], "changed": ["synthetic-1"], "closed": []}
    revised = record(summary="Marine hydraulic hose repair and overhaul")
    newer = prepare_payload(Repo([revised], {"manifest": {}, "record_states": record_states(first)}), p, TAX, [policy()], NOW, "2026-W48")
    assert newer["delta"]["changed"] == ["synthetic-1"]
    retrieval = record(last_seen_at="2026-11-23T03:00:00Z", verified_at="2026-11-23T03:00:00Z")
    assert record_states({"rows": [{"record": record().to_dict(), "match": first["rows"][0]["match"]}]}) == record_states({"rows": [{"record": retrieval.to_dict(), "match": first["rows"][0]["match"]}]})


def test_exports_have_versioned_envelope_required_fields_and_cc_link():
    payload = prepare_payload(Repo([record()]), profile(), TAX, [policy()], NOW, "2026-W47")
    envelope = json.loads(render_json(payload))
    assert envelope["schema_version"] == 1
    row = next(csv.DictReader(io.StringIO(render_csv(payload))))
    assert {"status", "reason", "lifecycle", "eligibility", "close_precision", "route_purpose", "sources", "conditions"} <= set(row)
    assert LICENCE in row["sources"]
    assert row["close_utc"] == ""
    assert "incomplete" in row["eligibility_limitations"]


def test_disappearance_is_not_closure_and_permission_can_release_reviewed_seed():
    p = profile()
    first = prepare_payload(Repo([record(publication_state="held")]), p, TAX, [policy()], NOW, "2026-W47")
    assert len(first["rows"]) == 1
    removed = prepare_payload(Repo([], {"record_states": record_states(first)}), p, TAX, [policy()], NOW, "2026-W48")
    assert removed["delta"]["closed"] == []
    closed = prepare_payload(Repo([record(lifecycle="closed")], {"record_states": record_states(first)}), p, TAX, [policy()], NOW, "2026-W48")
    assert closed["delta"]["closed"] == ["synthetic-1"]
