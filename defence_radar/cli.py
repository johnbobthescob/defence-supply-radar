"""Operator CLI. Only explicit fetch/all commands can access the network."""
import argparse
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import sys

from .config import load_profile, load_sources, load_taxonomy
from .evidence import digest
from .http_client import HttpClient
from .ingest.austender import fetch, incremental_start, replay_saved
from .ingest.aic import ingest_aic
from .ingest.seeds import ingest_seeds
from .models import utc_datetime, utc_iso
from .pipeline import build_outputs, StrictCoverageError, _coverage
from .classify import classify
from .match import match
from .policy import publication_allowed
from .storage import Repository


ROOT = Path(__file__).resolve().parents[1]

def _project(path, output=False):
    p = (ROOT / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    base = (ROOT / "out").resolve() if output else ROOT
    if not base.is_relative_to(ROOT) or not p.is_relative_to(base) or (output and p == base): raise ValueError("path must stay inside the project" + (" out/ subdirectory" if output else ""))
    return p

def _aware(value):
    try: return utc_iso(utc_datetime(value))
    except ValueError as exc: raise argparse.ArgumentTypeError(str(exc)) from exc

def build_parser():
    p = argparse.ArgumentParser(prog="defence-radar", description="Offline-first local supply-chain radar")
    sub = p.add_subparsers(dest="command", required=True)
    def common(c, *, profile=False, output=False, audience=False, strict=False, speculative=False):
        c.add_argument("--db", default="data/radar.sqlite3")
        if profile: c.add_argument("--profile", default="examples/sme_profile.json")
        c.add_argument("--as-of", type=_aware)
        c.add_argument("--week-ending")
        if audience: c.add_argument("--audience", choices=("public", "research"), default="public")
        if output: c.add_argument("--out")
        c.add_argument("--offline", action="store_true")
        if strict: c.add_argument("--strict", action="store_true")
        if speculative: c.add_argument("--include-speculative", action="store_true")
    c = sub.add_parser("init"); common(c); c.add_argument("--directory", default=".")
    src = sub.add_parser("sources"); ss = src.add_subparsers(dest="sources_command", required=True); c=ss.add_parser("check"); c.add_argument("--offline", action="store_true"); c.add_argument("--path", default="config/sources.json")
    pr = sub.add_parser("profile"); ps=pr.add_subparsers(dest="profile_command", required=True); c=ps.add_parser("validate"); c.add_argument("path"); c.add_argument("--taxonomy", default="config/taxonomy.json")
    for name in ("fetch", "build", "brief", "assess", "all"):
        c=sub.add_parser(name); common(c, profile=name!="fetch", output=name!="fetch", audience=name!="fetch", strict=name!="fetch", speculative=name!="fetch")
        if name in {"fetch", "all"}:
            c.add_argument("--field", choices=("contractPublished", "contractLastModified"))
            c.add_argument("--start"); c.add_argument("--end"); c.add_argument("--incremental", action="store_true"); c.add_argument("--saved-dir"); c.add_argument("--max-pages", type=int, default=100)
        if name == "all": c.add_argument("--aic-manifest", default="config/aic_manifest.json"); c.add_argument("--seeds", default="config/official_seeds.json")
    ing = sub.add_parser("ingest"); ins=ing.add_subparsers(dest="ingest_command", required=True)
    c=ins.add_parser("austender"); common(c); c.add_argument("--field", choices=("contractPublished", "contractLastModified"), default=None); c.add_argument("--start"); c.add_argument("--end"); c.add_argument("--incremental", action="store_true"); c.add_argument("--saved-dir"); c.add_argument("--max-pages", type=int, default=100)
    c=ins.add_parser("aic"); common(c); c.add_argument("--manifest", default="config/aic_manifest.json"); c.add_argument("--root", default="."); c.add_argument("--extract-pdf", action="store_true")
    c=ins.add_parser("seeds"); common(c); c.add_argument("--file", default="config/official_seeds.json")
    c=sub.add_parser("inspect"); c.add_argument("id"); common(c, profile=True)
    c=sub.add_parser("audit"); common(c)
    return p

def _clock(args):
    now = args.as_of or utc_iso(datetime.now(timezone.utc).replace(microsecond=0))
    return now

def _range(args, repo):
    end = utc_iso(args.end) if args.end else _clock(args)
    if args.incremental: start = incremental_start(repo, args.field, args.start)
    elif args.start: start = utc_iso(args.start)
    else: start = utc_iso(utc_datetime(end) - timedelta(days=30))
    if utc_datetime(start) >= utc_datetime(end): raise ValueError("start must be earlier than end")
    if utc_datetime(end) - utc_datetime(start) > timedelta(days=90): raise ValueError("refresh interval is limited to 90 days")
    return start, end

def _refresh(repo, args, policies, at):
    args.field = args.field or ("contractLastModified" if args.incremental else "contractPublished")
    if args.max_pages < 1: raise ValueError("max-pages must be positive")
    policy = next((p for p in policies if p.id == "austender"), None)
    if not policy: raise ValueError("AusTender source policy is missing")
    raw = _project("data/raw")
    for p in policies: repo.save_policy(p, at)
    if args.saved_dir:
        runs = replay_saved(repo, _project(args.saved_dir), raw)
    elif args.offline:
        raise ValueError("--offline requires --saved-dir for AusTender replay")
    else:
        start,end = _range(args, repo)
        runs = fetch(repo, HttpClient(policy), raw, args.field, start, end, at, max_pages=args.max_pages)
    return runs, any(r["state"] != "complete" for r in runs)

def _build(args, repo, at):
    policies=load_sources(_project("config/sources.json")); taxonomy=load_taxonomy(_project("config/taxonomy.json")); profile=load_profile(_project(args.profile), _project("config/taxonomy.json"))
    period=args.week_ending or at[:10]
    date.fromisoformat(period)
    out=_project(args.out or f"out/{args.audience}/{profile.id}/{period}", output=True)
    if out.is_relative_to(ROOT / "out/sample") and (args.audience != "public" or not profile.fictional):
        raise ValueError("out/sample requires a public build with a fictional profile")
    for p in policies: repo.save_policy(p, at)
    return build_outputs(repo, profile, taxonomy, policies, at, period, args.audience, out, args.include_speculative, args.strict)

def main(argv=None):
    args=build_parser().parse_args(argv)
    try:
        if args.command == "profile":
            load_profile(_project(args.path), _project(args.taxonomy)); print(f"Valid profile: {args.path}"); return 0
        if args.command == "sources":
            policies=load_sources(_project(args.path)); print(f"Loaded {len(policies)} source policies (offline; no remote terms rechecked).")
            for p in policies: print(f"{p.id}: {p.access_mode}; rights={p.rights_status}; audiences={','.join(p.allowed_audiences) or 'none'}")
            manifest=json.loads(_project("config/aic_manifest.json").read_text())
            print(f"Saved AIC text missing: {sum(not _project(d['text_path']).exists() for d in manifest['documents'])}/{len(manifest['documents'])}")
            return 0
        if args.command == "init":
            root=_project(args.directory); load_taxonomy(root/"config/taxonomy.json"); load_sources(root/"config/sources.json")
            for name in ("data/raw", "data/cache", "data/profiles", "data/review", "out"): (root/name).mkdir(parents=True, exist_ok=True)
            db=_project(args.db)
            with Repository(db): pass
            print(f"Initialized local radar at {root}"); return 0
        at=_clock(args)
        db=_project(args.db)
        with Repository(db) as repo:
            if args.command in {"fetch", "all"} or (args.command=="ingest" and args.ingest_command=="austender"):
                policies=load_sources(_project("config/sources.json")); runs,partial=_refresh(repo,args,policies,at)
                if args.command=="all":
                    aic=ingest_aic(repo,_project(args.aic_manifest),ROOT,False); seeds=ingest_seeds(repo,_project(args.seeds)); print(json.dumps({"runs":runs,"aic":aic,"seeds":seeds},sort_keys=True))
                    if partial: return 3
                    _build(args,repo,at if args.as_of else _clock(args)); return 0
                print(json.dumps(runs,sort_keys=True)); return 3 if partial else 0
            if args.command=="ingest":
                if args.ingest_command=="aic": result=ingest_aic(repo,_project(args.manifest),_project(args.root),args.extract_pdf)
                else: result=ingest_seeds(repo,_project(args.file))
                print(json.dumps(result,sort_keys=True)); return 3 if result.get("warnings") or result.get("held") or result.get("missing") else 0
            if args.command in {"build", "brief", "assess"}:
                manifest=_build(args,repo,at); print(json.dumps(manifest,sort_keys=True)); return 0
            if args.command=="inspect":
                record=repo.get_record(args.id)
                if not record: print("record not found"); return 2
                classified=classify(record,at); policies=load_sources(_project("config/sources.json")); taxonomy=load_taxonomy(_project("config/taxonomy.json")); profile=load_profile(_project(args.profile),_project("config/taxonomy.json"))
                from dataclasses import asdict
                print(json.dumps({"record":classified.to_dict(),"match":asdict(match(classified,profile,taxonomy,at)),"publication":{a:publication_allowed(classified,policies,a) for a in ("research","public")}},ensure_ascii=False,sort_keys=True,indent=2)); return 0
            if args.command=="audit":
                check=repo.connection.execute("PRAGMA integrity_check").fetchone()[0]; records=[classify(r,at) for r in repo.list_records()]; policies=load_sources(_project("config/sources.json"))
                report={"integrity":check,"records":len(records),"incomplete_runs":len(_coverage(repo,policies,at)["unresolved_incomplete_intervals"]),"held":sum(not publication_allowed(r,policies,"public")[0] or r.review_state.value!="reviewed" for r in records),"stale":sum(r.freshness_state in {"stale","unknown"} for r in records)}
                print(json.dumps(report,sort_keys=True)); return 0 if check=="ok" else 3
    except StrictCoverageError as exc:
        print(f"{args.command}: {exc}",file=sys.stderr); return 3
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"{args.command}: {exc}",file=sys.stderr)
        return 3 if getattr(args, "strict", False) and "strict build" in str(exc) else 2
    return 0
