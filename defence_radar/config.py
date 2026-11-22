"""Strict JSON configuration loaders with path-rich errors."""
import json
from pathlib import Path
from .models import Profile, SourcePolicy

def _read(path):
    p=Path(path)
    try:
        with p.open(encoding="utf-8") as f: return json.load(f)
    except Exception as e: raise ValueError(f"{p}: cannot load JSON: {e}") from e

def load_taxonomy(path):
    p=Path(path); data=_read(p)
    try:
        if set(data)!={"version","categories"}: raise ValueError("expected version and categories only")
        if isinstance(data["version"],bool) or not isinstance(data["version"],int) or data["version"]<1: raise ValueError("version must be a positive integer")
        if not isinstance(data["categories"],dict) or not data["categories"]: raise ValueError("categories must be a non-empty object")
        for key,cat in data["categories"].items():
            if not isinstance(cat,dict) or set(cat)!={"label","aliases","weight"}: raise ValueError(f"categories.{key}: expected label, aliases, weight")
            if not isinstance(cat["label"],str) or not isinstance(cat["aliases"],list) or any(not isinstance(x,str) for x in cat["aliases"]): raise ValueError(f"categories.{key}: invalid label/aliases")
            if isinstance(cat["weight"],bool) or not isinstance(cat["weight"],int): raise ValueError(f"categories.{key}.weight: expected integer")
        return data
    except Exception as e: raise ValueError(f"{p}: {e}") from e

def load_sources(path):
    p=Path(path); data=_read(p)
    try:
        if not isinstance(data,list): raise ValueError("expected an array of source policies")
        result=[]; seen=set()
        for i,item in enumerate(data):
            try:
                policy=SourcePolicy.from_dict(item)
                if policy.id in seen: raise ValueError(f"duplicate id {policy.id}")
                seen.add(policy.id); result.append(policy)
            except Exception as e: raise ValueError(f"sources[{i}]: {e}") from e
        return result
    except Exception as e: raise ValueError(f"{p}: {e}") from e

def load_profile(path, taxonomy_path="config/taxonomy.json"):
    p=Path(path)
    try:
        profile=Profile.from_dict(_read(p)); taxonomy=load_taxonomy(taxonomy_path)
        unknown=set(profile.capabilities)-set(taxonomy["categories"])
        if unknown: raise ValueError(f"capabilities: unknown taxonomy keys {sorted(unknown)}")
        return profile
    except Exception as e: raise ValueError(f"{p}: {e}") from e
