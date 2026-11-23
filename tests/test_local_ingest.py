import hashlib
import json
from pathlib import Path

from defence_radar.evidence import digest
from defence_radar.ingest.aic import extract_text, ingest_aic
from defence_radar.ingest.seeds import ingest_seeds
from defence_radar.models import Opportunity
from defence_radar.storage import Repository

FIX = Path(__file__).parent / "fixtures/synthetic/aic-layout.txt"


def test_extract_distinctions_and_warnings():
    text = extract_text(FIX)
    kinds = {x["kind"] for x in text["candidates"]}
    assert {"engagement", "existing_supplier", "future", "scope"} <= kinds
    assert any("malformed spaced email" in x for x in text["warnings"])
    assert any("contradictory AIA" in x for x in text["warnings"])
    assert "Janina Hildebrandt@geaerospace.example" in text["pages"][0]["text"]


def test_form_feed_page_boundaries(tmp_path):
    source = tmp_path / "pages.txt"
    source.write_text("one\n\ftwo\n")
    result = extract_text(source)
    assert len(result["pages"]) == 2
    assert result["pages"][0]["text"] == "one\n"
    assert result["pages"][1]["text"] == "two\n"


def test_aic_review_hash_and_date_binding(tmp_path):
    text = tmp_path / "doc.txt"
    text.write_text("future scope\n")
    sha = hashlib.sha256(text.read_bytes()).hexdigest()
    doc = {"id":"d1","url":"https://www.defence.gov.au/doc.pdf","text_path":"doc.txt","text_sha256":sha,"pdf_path":None,"accessed_at":"2026-01-01T00:00:00Z","reviews_file":"data/review/aic-scopes-d1.json"}
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema_version":1,"documents":[doc]}))
    record = Opportunity(id="temp",source_record_id="temp",source_ids=["aic"],title="Scope",record_kind="planned_scope",sources=[{"source_id":"aic","url":doc["url"],"accessed_at":doc["accessed_at"],"evidence_id":"d1","snapshot_sha256":sha,"pointer":"page:1"}],evidence_flags={"page":1}).to_dict()
    reviewfile = tmp_path / doc["reviews_file"]
    reviewfile.parent.mkdir(parents=True)
    reviewfile.write_text(json.dumps([{"key":"scope1","review":{"content_sha256":sha,"scope_sha256":digest(record),"reviewed_at":"2025-02-03T04:05:00Z","reviewer":"editor"},"record":record}]))
    with Repository(tmp_path / "db.sqlite") as repo:
        out = ingest_aic(repo, manifest, tmp_path)
        assert out["imported"] == 1
        saved = repo.get_record("aic:d1:scope1").to_dict()
        assert saved["review_state"] == "reviewed"
        assert saved["publication_state"] == "held"
        assert saved["rights"] == ["aic"]
        assert saved["verified_at"] == "2025-02-03T04:05:00Z"
        assert saved["evidence_flags"]["review"]["reviewer"] == "editor"
        assert saved["sources"][0]["accessed_at"] == doc["accessed_at"]
        text.write_text("changed content\n")
        out = ingest_aic(repo, manifest, tmp_path)
        assert out["changed"] == 1
        assert repo.get_record("aic:d1:scope1").review_state.value == "needs_review"


def test_seed_candidates_disabled_and_reviews_bound(tmp_path):
    rec = {"id":"seed1","source_record_id":"seed1","source_ids":["asa"],"title":"Reviewed fact","record_kind":"readiness_context","sources":[{"source_id":"asa","url":"https://www.asa.gov.au/industry","accessed_at":"2026-01-01T00:00:00Z","evidence_id":"seed1","snapshot_sha256":"0"*64,"pointer":"#section"}]}
    data = {"schema_version":1,"candidates":[{"id":"link","url":"https://www.asa.gov.au/industry","source_id":"asa","enabled":False,"reason":"unread"}],"records":[{"record":rec,"review":{"content_sha256":digest(rec),"reviewed_at":"2025-01-01T00:00:00Z","reviewer":"r"}}]}
    path=tmp_path/"seeds.json"; path.write_text(json.dumps(data))
    with Repository(tmp_path/"db.sqlite") as repo:
        out=ingest_seeds(repo,path)
        assert (out["candidates"],out["imported"],out["held"]) == (1,1,0)
        assert repo.get_record("seed1").record_kind.value == "readiness_context"
        data["records"][0]["review"]["content_sha256"]="f"*64
        path.write_text(json.dumps(data))
        assert ingest_seeds(repo,path)["held"] == 1
