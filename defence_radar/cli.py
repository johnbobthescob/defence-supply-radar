import argparse
from pathlib import Path
from .config import load_profile, load_sources

def build_parser():
    p=argparse.ArgumentParser(prog="defence-radar", description="Offline-first local supply-chain radar")
    sub=p.add_subparsers(dest="command", required=True)
    for cmd in ("init","fetch","build","brief","assess","all"):
        c=sub.add_parser(cmd, help=f"{cmd} pipeline step (not implemented in M1)")
        if cmd=="init": c.add_argument("--directory",default=".")
    profile=sub.add_parser("profile"); ps=profile.add_subparsers(dest="profile_command",required=True); v=ps.add_parser("validate"); v.add_argument("path")
    sources=sub.add_parser("sources"); ss=sources.add_subparsers(dest="sources_command",required=True); c=ss.add_parser("check"); c.add_argument("--offline",action="store_true"); c.add_argument("--path",default="config/sources.json")
    return p

def main(argv=None):
    args=build_parser().parse_args(argv)
    if args.command=="init":
        root=Path(args.directory)
        for name in ("data/raw","data/cache","data/profiles","data/review","out"): (root/name).mkdir(parents=True,exist_ok=True)
        return 0
    if args.command=="profile":
        try: load_profile(args.path); print(f"Valid profile: {args.path}"); return 0
        except ValueError as e: print(e); return 2
    if args.command=="sources":
        try:
            policies=load_sources(args.path)
            print(f"Loaded {len(policies)} source policies (offline; no rights are inferred).")
            return 0
        except ValueError as e: print(e); return 2
    raise SystemExit(f"{args.command}: not implemented yet (planned for M9)")
