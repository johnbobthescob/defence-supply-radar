import hashlib
import json
from pathlib import Path
import shutil

import pytest

from defence_radar.cli import main
from defence_radar.config import load_profile, load_sources, load_taxonomy
from defence_radar.pipeline import build_outputs
from defence_radar.storage import Repository
from defence_radar.ingest.austender import replay_saved

ROOT = Path(__file__).resolve().parents[1]
AT = "2026-11-24T12:00:00Z"

def inputs():
    return load_profile(ROOT / "examples/sme_profile.json", ROOT / "config/taxonomy.json"), load_taxonomy(ROOT / "config/taxonomy.json"), load_sources(ROOT / "config/sources.json")

def test_terminal_fixture_build_has_complete_bundle_and_stable_hashes(tmp_path):
    profile, taxonomy, policies = inputs()
    fixture = ROOT / "tests/fixtures/austender"
    saved = tmp_path / "saved"; saved.mkdir()
    for name in ("terminal.json", "terminal.meta.json"): shutil.copy(fixture / name, saved / name)
    db=tmp_path/"db.sqlite3"; out=tmp_path/"out"
    with Repository(db) as repo:
        assert all(r["state"] == "complete" for r in replay_saved(repo,saved,tmp_path/"raw"))
        first=build_outputs(repo,profile,taxonomy,policies,AT,"2026-11-22","public",out)
        one={p.name:p.read_bytes() for p in out.iterdir()}
        second=build_outputs(repo,profile,taxonomy,policies,AT,"2026-11-22","public",out)
    assert first["output_sha256"]==second["output_sha256"]
    assert {p.name:p.read_bytes() for p in out.iterdir()}==one
    assert set(one)=={"briefing-2026-11-24.md","work-packages.json","work-packages.csv","work-packages.html","assessment-fictional-henderson-marine-sme.md","assessment-fictional-henderson-marine-sme.html","coverage.json","manifest.json"}
    manifest=json.loads(one["manifest.json"])
    assert all(hashlib.sha256(one[n]).hexdigest()==h for n,h in manifest["output_sha256"].items())
    assert "private" not in one["manifest.json"].decode().lower()

def test_partial_saved_chain_and_strict_refusal_preserve_output(tmp_path):
    profile,taxonomy,policies=inputs(); fixture=ROOT/"tests/fixtures/austender"; out=tmp_path/"out"; db=tmp_path/"db.sqlite3"
    with Repository(db) as repo:
        build_outputs(repo,profile,taxonomy,policies,AT,"2026-11-22","public",out)
    previous={p.name:p.read_bytes() for p in out.iterdir()}
    with Repository(db) as repo: assert any(r["state"] != "complete" for r in replay_saved(repo,fixture,tmp_path/"raw"))
    assert {p.name:p.read_bytes() for p in out.iterdir()}==previous
    with Repository(db) as repo:
        repo.record_run("austender","contractLastModified","2026-11-22T00:00:00Z","2026-11-23T00:00:00Z","partial",AT,error="partial chain",live=True)
        with pytest.raises(ValueError,match="strict build"):
            build_outputs(repo,profile,taxonomy,policies,AT,"2026-11-23","public",out,strict=True)
    assert {p.name:p.read_bytes() for p in out.iterdir()}==previous

def test_rollback_on_renderer_and_save_failure_and_bad_profile(tmp_path,monkeypatch):
    import defence_radar.pipeline as pipe
    profile,taxonomy,policies=inputs(); out=tmp_path/"out"; db=tmp_path/"db.sqlite3"
    with Repository(db) as repo:
        build_outputs(repo,profile,taxonomy,policies,AT,"2026-11-22","public",out)
        old={p.name:p.read_bytes() for p in out.iterdir()}
        monkeypatch.setattr(pipe,"render_html",lambda p: (_ for _ in ()).throw(RuntimeError("renderer failed")))
        with pytest.raises(RuntimeError): build_outputs(repo,profile,taxonomy,policies,AT,"2026-11-23","public",out)
        monkeypatch.undo()
        monkeypatch.setattr(repo,"save_build",lambda *a: (_ for _ in ()).throw(RuntimeError("db failed")))
        with pytest.raises(RuntimeError): build_outputs(repo,profile,taxonomy,policies,AT,"2026-11-23","public",out)
        assert {p.name:p.read_bytes() for p in out.iterdir()}==old
        bad=profile.to_dict(); bad["id"]="../escape"
        with pytest.raises(ValueError,match="profile id"): build_outputs(repo,bad,taxonomy,policies,AT,"2026-11-24","public",out)

def test_help_and_init_audit_are_offline(tmp_path,capsys):
    with pytest.raises(SystemExit) as exc: main(["--help"])
    assert exc.value.code==0
    root=tmp_path/"project"; root.mkdir()
    import defence_radar.cli as cli
    old=cli.ROOT; cli.ROOT=root
    try:
        shutil.copytree(ROOT/"config",root/"config");
        assert main(["init","--directory","."])==0
        assert main(["audit"])==0
    finally: cli.ROOT=old


def test_all_cli_replay_and_failure_preserve_bundle(tmp_path, monkeypatch):
    import defence_radar.cli as cli
    root = tmp_path / "project"; root.mkdir()
    for name in ("config", "examples"):
        shutil.copytree(ROOT/name, root/name)
    saved = root / "saved"; saved.mkdir()
    for name in ("terminal.json", "terminal.meta.json"):
        shutil.copy(ROOT/"tests/fixtures/austender"/name, saved/name)
    monkeypatch.setattr(cli, "ROOT", root)
    args = ["all", "--offline", "--saved-dir", "saved", "--as-of", AT, "--out", "out/test"]
    assert main(args) == 0
    before = {p.name: p.read_bytes() for p in (root/"out/test").iterdir()}
    for name in ("page1.json", "page1.meta.json", "page2.json", "page2.meta.json"):
        shutil.copy(ROOT/"tests/fixtures/austender"/name, saved/name)
    assert main(args) == 3
    assert before == {p.name: p.read_bytes() for p in (root/"out/test").iterdir()}
    assert main(["build", "--offline", "--strict", "--as-of", AT, "--out", "out/test"]) == 3
    assert main(["build", "--offline", "--out", "out"]) == 2
    assert main(["build", "--offline", "--audience", "research", "--out", "out/sample"]) == 2
    assert main(["fetch", "--start", "not-a-date"]) == 2
