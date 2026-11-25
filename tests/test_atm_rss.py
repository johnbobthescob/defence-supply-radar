from pathlib import Path
import pytest

from defence_radar.classify import classify
from defence_radar.cli import main
from defence_radar.config import load_sources, load_profile, load_taxonomy
from defence_radar.http_client import HttpClient, Response
from defence_radar.ingest.atm_rss import (ATTRIBUTION, fetch_feed, import_feed, parse_feed)
from defence_radar.match import match
from defence_radar.models import utc_datetime
from defence_radar.policy import publication_allowed
from defence_radar.storage import Repository

FIX = Path(__file__).parent / "fixtures/atm_rss"
AT = "2026-11-25T03:00:00Z"
LATER = "2026-11-28T03:00:00Z"
POLICIES = load_sources("config/sources.json")
POLICY = next(p for p in POLICIES if p.id == "austender_atm")


@pytest.fixture
def repo(tmp_path):
    with Repository(tmp_path / "r.sqlite3") as r:
        yield r


def imported(repo, tmp_path):
    summary = import_feed(repo, FIX / "synthetic-current-atm.xml", tmp_path / "raw", AT)
    return summary, {r.source_record_id: r for r in repo.list_records()}


def test_parse_fields():
    items = parse_feed((FIX / "synthetic-current-atm.xml").read_bytes())
    assert len(items) == 6
    first = items[0]
    assert first["title"].startswith("Hydraulic system maintenance")
    assert first["atm_id"] == "SYN-ATM-0001" and first["agency"] == "Department of Defence"
    assert first["category_code"] == "25111900"
    assert first["pub_date"] == "2026-11-24T11:00:00Z"
    assert first["guid"] == "SYN-ATM-0001"
    assert first["close_zone"] == "Australia/Sydney" and "15-Dec-2026" in first["close_raw"]
    assert "<" not in first["description_text"] and "  " not in first["description_text"]
    assert items[4]["close_raw"] is None


def test_import_close_and_status(repo, tmp_path):
    summary, recs = imported(repo, tmp_path)
    assert summary == {"items": 6, "imported": 6, "accessed_at": AT}
    hyd = recs["atm:SYN-ATM-0001"]
    assert hyd.close_at_utc == "2026-12-15T03:00:00Z" and hyd.close_precision == "instant"
    assert recs["atm:SYN-ATM-0004"].close_precision == "date_only" and recs["atm:SYN-ATM-0004"].close_at_utc is None
    assert recs["atm:SYN-ATM-0005"].close_precision == "not_published"
    assert repo.runs()[-1]["state"] == "complete" and repo.runs()[-1]["live"] == 0
    fresh = {k: classify(v, AT).status_class.value for k, v in recs.items()}
    assert fresh["atm:SYN-ATM-0006"] == "inactive"
    assert all(fresh[k] == "confirmed_open" for k in fresh if k != "atm:SYN-ATM-0006")
    later = {k: classify(v, LATER).status_class.value for k, v in recs.items()}
    assert later["atm:SYN-ATM-0001"] == "held" and later["atm:SYN-ATM-0005"] == "held"


def test_doctype_rejected():
    with pytest.raises(ValueError, match="DOCTYPE"):
        parse_feed((FIX / "doctype.xml").read_bytes())
    with pytest.raises(ValueError):
        parse_feed(b"<rss>" + b"x" * 5_000_001)


def test_publication_allowed(repo, tmp_path):
    _, recs = imported(repo, tmp_path)
    for r in recs.values():
        assert r.attribution == [ATTRIBUTION]
        assert publication_allowed(r, POLICIES, "public")[0] is True


def test_fetch_403_records_failed_run(repo, tmp_path):
    def transport(url, timeout, size):
        return Response(403, {}, b"blocked", url)
    client = HttpClient(POLICY, transport=transport, sleeper=lambda s: None, min_gap=0,
                        clock=lambda: utc_datetime(AT))
    run = fetch_feed(repo, client, tmp_path / "raw", AT)
    assert run["state"] == "failed" and run["live"] and "403" in run["error"]
    assert repo.list_records() == []


def test_cli_rules(tmp_path, capsys):
    db = Path(__file__).parents[1] / "data/atm-test.sqlite3"
    try:
        assert main(["ingest", "atm-rss", "--fetch", "--offline", "--db", str(db)]) == 2
        assert main(["ingest", "atm-rss", "--file", "/etc/passwd", "--db", str(db)]) == 2
    finally:
        db.unlink(missing_ok=True)


def test_end_to_end_match(repo, tmp_path):
    _, recs = imported(repo, tmp_path)
    tax, profile = load_taxonomy("config/taxonomy.json"), load_profile("examples/sme_profile.json")
    score = {k: match(classify(v, AT), profile, tax, AT).score for k, v in recs.items()}
    assert score["atm:SYN-ATM-0001"] > score["atm:SYN-ATM-0004"] + 20
    assert score["atm:SYN-ATM-0001"] > score["atm:SYN-ATM-0003"] + 20
