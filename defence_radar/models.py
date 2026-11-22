"""Validated, JSON-friendly domain models for the radar."""
from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from enum import Enum
import re
from urllib.parse import urlparse


class StrEnum(str, Enum):
    def __str__(self): return self.value


class RecordKind(StrEnum):
    procurement="procurement"; planned_scope="planned_scope"; hypothesis="hypothesis"; contract_context="contract_context"; registration_context="registration_context"; readiness_context="readiness_context"
class StatusClass(StrEnum):
    confirmed_open="confirmed_open"; published_future_scope="published_future_scope"; speculative="speculative"
class Lifecycle(StrEnum):
    open="open"; planned="planned"; ongoing_scope="ongoing_scope"; closed="closed"; awarded="awarded"; cancelled="cancelled"; superseded="superseded"; unknown="unknown"
class ReviewState(StrEnum):
    pending="pending"; reviewed="reviewed"; needs_review="needs_review"
class PublicationState(StrEnum):
    publishable="publishable"; held="held"; context_only="context_only"


def utc_datetime(value):
    if not isinstance(value, str): raise ValueError("timestamp must be an ISO 8601 string")
    try: dt=datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as e: raise ValueError(f"invalid ISO timestamp: {value!r}") from e
    if dt.tzinfo is None or dt.utcoffset() is None: raise ValueError("timestamp must include a timezone")
    return dt.astimezone(timezone.utc)

def utc_iso(value):
    dt = utc_datetime(value) if isinstance(value, str) else value
    if not isinstance(dt, datetime) or dt.tzinfo is None or dt.utcoffset() is None: raise ValueError("datetime must be timezone-aware")
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

def _identifier(v, path):
    if not isinstance(v, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,199}", v): raise ValueError(f"{path}: invalid identifier")
def _url(v, path, nullable=False):
    if nullable and v is None: return
    if not isinstance(v, str): raise ValueError(f"{path}: expected URL string")
    p=urlparse(v)
    if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password: raise ValueError(f"{path}: expected safe http(s) URL")
def _dict(v, path):
    if not isinstance(v, dict) or any(not isinstance(k,str) for k in v): raise ValueError(f"{path}: expected object")
def _list(v,path, item=None):
    if not isinstance(v,list): raise ValueError(f"{path}: expected list")
    if item and any(not isinstance(x,item) for x in v): raise ValueError(f"{path}: invalid list item type")

@dataclass
class Opportunity:
    id: str
    source_record_id: str
    source_ids: list[str]
    title: str
    record_kind: RecordKind
    sources: list[dict]
    schema_version: int = 1
    summary: str = ""
    programme: str = ""
    buyer: str = ""
    prime: str = ""
    status_class: StatusClass | None = None
    lifecycle: Lifecycle = Lifecycle.unknown
    review_state: ReviewState = ReviewState.pending
    publication_state: PublicationState = PublicationState.held
    classification_evidence: list[str] = field(default_factory=list)
    rule_ids: list[str] = field(default_factory=list)
    classification_reason: str = ""
    conditions: list[str] = field(default_factory=list)
    procurement_stage: str = "unknown"
    locations: list[dict] = field(default_factory=list)
    capabilities: list[dict] = field(default_factory=list)
    activities: list[str] = field(default_factory=list)
    eligibility: list[dict] = field(default_factory=list)
    eligibility_complete: bool = False
    close_at_utc: str | None = None
    close_raw: str | None = None
    close_zone: str | None = None
    close_precision: str = "not_published"
    forecast_period: dict = field(default_factory=dict)
    contract_period: dict = field(default_factory=dict)
    application_route: dict = field(default_factory=lambda: dict(purpose="none_published",url=None,email=None,instructions="",verified_at=None,evidence_id=None,account_required="unknown"))
    source_published_at: str | None = None
    source_modified_at: str | None = None
    first_seen_at: str | None = None
    last_seen_at: str | None = None
    verified_at: str | None = None
    freshness_state: str = "unknown"
    last_verification_attempt: str | None = None
    verification_error: str | None = None
    rights: list[str] = field(default_factory=list)
    attribution: list[str] = field(default_factory=list)
    related_record_ids: list[str] = field(default_factory=list)
    supersedes_id: str | None = None
    value_context: dict = field(default_factory=dict)
    evidence_flags: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self): self.validate()
    def validate(self):
        _identifier(self.id,"id"); _identifier(self.source_record_id,"source_record_id")
        if self.schema_version != 1 or isinstance(self.schema_version,bool): raise ValueError("schema_version: expected 1")
        for f in ("source_ids","classification_evidence","rule_ids","conditions","activities","rights","attribution","related_record_ids","warnings"): _list(getattr(self,f),f,str)
        if not self.source_ids: raise ValueError("source_ids: at least one source required")
        for name in ("title", "summary", "programme", "buyer", "prime", "classification_reason"):
            if not isinstance(getattr(self, name), str): raise ValueError(f"{name}: expected string")
        if not self.title.strip(): raise ValueError("title: required")
        for name, cls in (("record_kind",RecordKind),("status_class",StatusClass),("lifecycle",Lifecycle),("review_state",ReviewState),("publication_state",PublicationState)):
            val=getattr(self,name)
            if val is None and name=="status_class": continue
            try: setattr(self,name, cls(val))
            except (ValueError,TypeError): raise ValueError(f"{name}: invalid value {val!r}")
        if not isinstance(self.eligibility_complete,bool): raise ValueError("eligibility_complete: expected boolean")
        _list(self.sources,"sources")
        if not self.sources: raise ValueError("sources: at least one evidence reference required")
        evidence_ids=set()
        for i,s in enumerate(self.sources):
            _dict(s,f"sources[{i}]")
            for k in ("source_id","url","accessed_at","evidence_id","snapshot_sha256","pointer"):
                if k not in s: raise ValueError(f"sources[{i}].{k}: required")
            _identifier(s["source_id"],f"sources[{i}].source_id"); evidence_ids.add(s["source_id"])
            _identifier(s["evidence_id"],f"sources[{i}].evidence_id")
            _url(s["url"],f"sources[{i}].url")
            utc_datetime(s["accessed_at"])
            if not isinstance(s["snapshot_sha256"],str) or not re.fullmatch(r"[0-9a-fA-F]{64}",s["snapshot_sha256"]): raise ValueError(f"sources[{i}].snapshot_sha256: expected 64 hex characters")
            if not isinstance(s["pointer"],str) or not s["pointer"].strip(): raise ValueError(f"sources[{i}].pointer: required locator")
        if not evidence_ids.issubset(set(self.source_ids)): raise ValueError("source_ids: must cover every sources[].source_id")
        for f in ("source_published_at","source_modified_at","first_seen_at","last_seen_at","verified_at","last_verification_attempt","close_at_utc"):
            if getattr(self,f) is not None: utc_datetime(getattr(self,f))
        if self.close_precision not in {"instant","date_only","range","ongoing_explicit","not_published","not_applicable"}: raise ValueError("close_precision: invalid value")
        if self.close_at_utc and self.close_precision != "instant": raise ValueError("close_at_utc: requires instant precision")
        if self.freshness_state not in {"fresh", "stale", "unknown"}: raise ValueError("freshness_state: invalid value")
        for name in ("locations", "capabilities", "eligibility"):
            _list(getattr(self, name), name, dict)
        for f in ("forecast_period","contract_period","application_route","value_context","evidence_flags"): _dict(getattr(self,f),f)
        route=self.application_route
        for k in ("purpose","url","email","instructions","verified_at","evidence_id","account_required"):
            if k not in route: raise ValueError(f"application_route.{k}: required")
        if route["purpose"] not in {"submit", "procurement_eoi", "register_interest", "enquire", "none_published"}: raise ValueError("application_route.purpose: invalid value")
        if route["account_required"] not in {"yes", "no", "unknown"}: raise ValueError("application_route.account_required: invalid value")
        if route["url"] is not None: _url(route["url"],"application_route.url")
        if route["email"] is not None and (not isinstance(route["email"],str) or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",route["email"])): raise ValueError("application_route.email: invalid email")
        if route["verified_at"] is not None: utc_datetime(route["verified_at"])
        return self
    def to_dict(self):
        def cv(x):
            if isinstance(x,Enum): return x.value
            if isinstance(x,list): return [cv(y) for y in x]
            if isinstance(x,dict): return {k:cv(v) for k,v in x.items()}
            return x
        return {f.name:cv(getattr(self,f.name)) for f in fields(self)}
    @classmethod
    def from_dict(cls,data):
        if not isinstance(data,dict): raise ValueError("opportunity: expected object")
        allowed={f.name for f in fields(cls)}; unknown=set(data)-allowed
        if unknown: raise ValueError(f"unknown opportunity fields: {', '.join(sorted(unknown))}")
        required={"id","source_record_id","source_ids","title","record_kind","sources"}; missing=required-set(data)
        if missing: raise ValueError(f"missing opportunity fields: {', '.join(sorted(missing))}")
        data=dict(data)
        route=data.get("application_route")
        if isinstance(route,dict) and route.get("email") is not None and (not isinstance(route["email"],str) or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",route["email"])):
            route=dict(route); route["email"]=None; data["application_route"]=route
            data["warnings"]=list(data.get("warnings",[]))+["Malformed application route email retained as a warning."]
        return cls(**data)

@dataclass
class SourcePolicy:
    id:str; access_mode:str="disabled"; rights_status:str="unverified"; allowed_audiences:list[str]=field(default_factory=list); allowed_hosts:list[str]=field(default_factory=list); allowed_path_prefixes:list[str]=field(default_factory=list); licence_url:str|None=None; terms_url:str|None=None; reviewed_at:str|None=None; evidence:str=""; notes:str=""
    def validate(self):
        _identifier(self.id,"id")
        if self.access_mode not in {"api","local_only","manual_reference","disabled"}: raise ValueError("access_mode: invalid value")
        if self.rights_status not in {"licensed","permission_documented","restricted","unverified"}: raise ValueError("rights_status: invalid value")
        for name in ("allowed_audiences", "allowed_hosts", "allowed_path_prefixes"):
            _list(getattr(self, name), name, str)
        if self.rights_status in {"restricted", "unverified"} and self.allowed_audiences:
            raise ValueError("allowed_audiences: restricted or unverified rights cannot grant publication")
        for v in self.allowed_audiences:
            if v not in {"research","public"}: raise ValueError("allowed_audiences: invalid value")
        for f in ("licence_url","terms_url"):
            if getattr(self,f) is not None: _url(getattr(self,f),f)
        if self.reviewed_at is not None: utc_datetime(self.reviewed_at)
        return self
    def to_dict(self): return {f.name:getattr(self,f.name) for f in fields(self)}
    @classmethod
    def from_dict(cls,d):
        allowed={f.name for f in fields(cls)}
        if set(d)-allowed: raise ValueError(f"unknown source policy fields: {sorted(set(d)-allowed)}")
        return cls(**d).validate()

@dataclass
class Profile:
    id:str; version:int; name:str; fictional:bool; public_fields:list[str]; capabilities:list[str]; activities:list[str]; service_regions:list[str]; national_supply:bool; credentials:dict=field(default_factory=dict); exclusions:list[str]=field(default_factory=list); materials:list[str]=field(default_factory=list); processes:list[str]=field(default_factory=list); capacity:str=""; experience:list[str]=field(default_factory=list)
    def validate(self):
        _identifier(self.id,"id")
        if isinstance(self.version,bool) or not isinstance(self.version,int) or self.version<1: raise ValueError("version: expected positive integer")
        for f in ("fictional","national_supply"):
            if not isinstance(getattr(self,f),bool): raise ValueError(f"{f}: expected boolean")
        for f in ("public_fields","capabilities","activities","service_regions","exclusions","materials","processes","experience"): _list(getattr(self,f),f,str)
        _dict(self.credentials,"credentials")
        for k,c in self.credentials.items():
            _dict(c,f"credentials.{k}")
            if set(c)-{"value","expires_at","evidence"}: raise ValueError(f"credentials.{k}: unknown field")
            if c.get("expires_at") is not None: utc_datetime(c["expires_at"])
        return self
    def to_dict(self): return {f.name:getattr(self,f.name) for f in fields(self)}
    @classmethod
    def from_dict(cls,d):
        allowed={f.name for f in fields(cls)}
        if set(d)-allowed: raise ValueError(f"unknown profile fields: {sorted(set(d)-allowed)}")
        req={"id","version","name","fictional","public_fields","capabilities","activities","service_regions","national_supply"}
        if req-set(d): raise ValueError(f"missing profile fields: {sorted(req-set(d))}")
        return cls(**d).validate()

@dataclass
class MatchResult:
    opportunity_id:str; profile_id:str; profile_hash:str; taxonomy_version:int; rule_version:str; score:int; components:dict=field(default_factory=dict); matched_capabilities:list[str]=field(default_factory=list); missing_capabilities:list[str]=field(default_factory=list); evidence:list[str]=field(default_factory=list); exclusions:list[str]=field(default_factory=list); eligibility:dict=field(default_factory=dict); shortlist:bool=False
    def validate(self):
        if isinstance(self.score,bool) or not isinstance(self.score,int) or not 0<=self.score<=100: raise ValueError("score: expected integer 0..100")
        if not isinstance(self.shortlist,bool): raise ValueError("shortlist: expected boolean")
        for f in ("components","eligibility"): _dict(getattr(self,f),f)
        for f in ("matched_capabilities","missing_capabilities","evidence","exclusions"): _list(getattr(self,f),f,str)
        return self
