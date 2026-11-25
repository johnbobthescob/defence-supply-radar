import pytest

from defence_radar.models import Opportunity
from defence_radar.storage import Repository

SRC = {"source_id":"s1","url":"https://example.gov.au/item","accessed_at":"2026-11-22T10:00:00Z","evidence_id":"e1","snapshot_sha256":"a"*64,"pointer":"/"}
BASE = {"id":"opp-1","source_record_id":"x","source_ids":["s1"],"title":"Example","record_kind":"procurement","sources":[SRC]}


def record(**changes):
    return Opportunity.from_dict({**BASE, **changes})


def test_replay_idempotent_and_release_conflicts_retained(tmp_path):
    with Repository(tmp_path/"db.sqlite") as repo:
        snap=repo.add_snapshot({"source_id":"s1","sha256":"x"})
        a=repo.add_release("ocid","r1",{"x":1},snap,"2026-01-01T00:00:00Z")
        b=repo.add_release("ocid","r1",{"x":1},snap,"2026-01-01T00:00:00Z")
        c=repo.add_release("ocid","r1",{"x":2},snap,"2026-01-01T00:00:00Z")
        assert a["inserted"] and not a["conflict"]
        assert not b["inserted"] and not b["conflict"]
        assert c["inserted"] and c["conflict"]
        assert repo.connection.execute("select count(*) from releases").fetchone()[0] == 2


def test_transaction_rollback_and_versions_order_conflict(tmp_path):
    with Repository(tmp_path/"db.sqlite") as repo:
        with pytest.raises(RuntimeError):
            with repo.transaction():
                repo.save_record(record(title="Interrupted"), "2026-01-01T00:00:00Z")
                raise RuntimeError()
        assert repo.get_record("opp-1") is None
        repo.save_record(record(title="new"), "2026-02-01T00:00:00Z")
        repo.save_record(record(title="old"), "2026-01-01T00:00:00Z")
        assert repo.get_record("opp-1").title == "new"
        repo.save_record(record(title="same-time-conflict"), "2026-02-01T00:00:00Z")
        assert repo.connection.execute("select count(*) from record_versions where needs_review=1").fetchone()[0] == 2
        assert repo.get_record("opp-1").review_state.value == "needs_review"
        assert repo.get_record("opp-1").publication_state.value == "held"


def test_first_seen_and_last_seen_not_substantive(tmp_path):
    with Repository(tmp_path/"db.sqlite") as repo:
        repo.save_record(record(first_seen_at="2026-01-01T00:00:00Z"), "2026-01-01T00:00:00Z")
        repo.save_record(record(last_seen_at="2026-01-02T00:00:00Z"), "2026-01-02T00:00:00Z")
        assert repo.connection.execute("select count(*) from record_versions").fetchone()[0] == 1


def test_replay_checkpoint_and_period_baseline(tmp_path):
    with Repository(tmp_path/"db.sqlite") as repo:
        repo.record_run("s1","published","2026-01-01","2026-01-02","failed","2026-01-02",live=True)
        repo.complete_window("s1","published","2026-01-03","2026-01-04",[],[],[],"2026-01-04")
        assert repo.checkpoint("s1","published") is None
        repo.complete_window("s1","published","2026-01-01","2026-01-02",[],[],[],"2026-01-05",live=True)
        assert repo.checkpoint("s1","published") == "2026-01-02"
        repo.complete_window("s1","published","2026-01-03","2026-01-04",[],[],[],"2026-01-06",live=False)
        assert repo.checkpoint("s1","published") == "2026-01-02"
        repo.save_build({"profile_hash":"p","audience":"public","period":"2026-01"}, {"a":"open"})
        repo.save_build({"profile_hash":"p","audience":"public","period":"2026-02"}, {"a":"closed"})
        prior=repo.previous_build("p","public","2026-02")
        assert prior["record_states"] == {"a":"open"}
        assert repo.previous_build("p","public","2026-01") is None


def test_snapshot_headers_and_run_errors_sanitized(tmp_path):
    from defence_radar.evidence import save_snapshot
    snap=save_snapshot(tmp_path,"s1","https://example.gov.au",b"abc","2026-01-01T00:00:00Z",
                       headers={"Authorization":"secret","Cookie":"secret","ETag":"e","Content-Type":"application/json"})
    assert snap["headers"] == {"etag":"e","content-type":"application/json"}
    assert b"secret" not in (tmp_path/"snapshots"/"s1").glob("*.json").__iter__().__next__().read_bytes()
    with Repository(tmp_path/"db.sqlite") as repo:
        repo.record_run("s1","x","a","b","failed","now",error="authorization=secret")
        assert "secret" not in str(repo.runs())


def test_same_release_changed_payload_holds_normalized_record(tmp_path):
    with Repository(tmp_path/"db") as repo:
        sid = repo.add_snapshot({"source_id": "s1", "sha256": "x"})
        rel = dict(ocid="o", release_id="r", payload={"x": 1}, snapshot_id=sid, event_at="2026-01-01T00:00:00Z")
        rec = record(evidence_flags={"ocid": "o", "release_id": "r"}, verified_at="2026-01-01T00:00:00Z")
        repo.complete_window("s1", "field", "a", "b", [], [rel], [rec], "2026-01-02T00:00:00Z")
        rel["payload"] = {"x": 2}
        repo.complete_window("s1", "field", "a", "b", [], [rel], [rec], "2026-01-03T00:00:00Z")
        assert repo.get_record(rec.id).evidence_flags["conflicting_versions"]
        assert repo.get_record(rec.id).review_state.value == "needs_review"


def test_fractional_event_order_and_equivalent_timezone_conflicts(tmp_path):
    with Repository(tmp_path/"db") as repo:
        repo.save_record(record(title="earlier"), "2026-01-01T00:00:00Z")
        repo.save_record(record(title="later"), "2026-01-01T00:00:00.500Z")
        assert repo.get_record("opp-1").title == "later"
        repo.save_record(record(title="conflict"), "2026-01-01T08:00:00.500+08:00")
        assert repo.get_record("opp-1").review_state.value == "needs_review"
