"""Versioned evidence gates. Relevance and publication permission are separate."""
from copy import deepcopy
from datetime import datetime, timedelta
import re
from zoneinfo import ZoneInfo

from .models import Opportunity, RecordKind, StatusClass, Lifecycle, ReviewState, PublicationState, utc_datetime, utc_iso

RULE_VERSION = "status-1"
INACTIVE = {"closed", "awarded", "cancelled", "superseded"}
CONTEXT = {"contract_context", "registration_context", "readiness_context"}


def parse_close(raw, zone=None):
    """An offset or unambiguous IANA local time establishes an instant; dates do not."""
    result = dict(close_raw=raw, close_zone=zone, close_at_utc=None, close_precision="not_published")
    if not raw:
        return result
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        datetime.fromisoformat(raw)
        result["close_precision"] = "date_only"
        return result
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if value.tzinfo is None:
            if not zone:
                return result
            if zone != "UTC" and "/" not in zone:
                return result  # Abbreviations such as EST do not identify the source zone.
            tz = ZoneInfo(zone)
            a, b = value.replace(tzinfo=tz, fold=0), value.replace(tzinfo=tz, fold=1)
            if a.utcoffset() != b.utcoffset():
                return result  # ambiguous or nonexistent daylight-saving local time
            value = a
        result.update(close_at_utc=utc_iso(value), close_precision="instant")
    except ValueError:
        pass  # masked or publisher prose remains raw, never a guessed instant
    return result


def _age(value, now):
    return now - utc_datetime(value) if value else None


def classify(record, as_of):
    result = Opportunity.from_dict(deepcopy(record.to_dict()))
    now = utc_datetime(as_of)
    flags = result.evidence_flags
    result.status_class = None
    result.rule_ids = []
    result.classification_reason = ""

    def decide(rule, reason, status=None, lifecycle=None, held=False):
        result.rule_ids = [f"{RULE_VERSION}:{rule}"]
        result.classification_reason = reason
        result.status_class = StatusClass(status) if status else None
        if lifecycle:
            result.lifecycle = Lifecycle(lifecycle)
        if held:
            result.review_state = ReviewState.needs_review
            result.publication_state = PublicationState.held
        return result

    age = _age(result.verified_at, now)
    limit = timedelta(hours=24) if result.record_kind == RecordKind.procurement else timedelta(days=30)
    result.freshness_state = "unknown" if age is None else "fresh" if timedelta(0) <= age <= limit else "stale"
    if flags.get("conflicting_versions") or flags.get("conflicting_evidence"):
        return decide("CONFLICT", "Conflicting evidence requires reconciliation by official identity.", held=True)
    # Type and source stage trump portal badges and caller-supplied class labels.
    if "austender" in result.source_ids or set(flags.get("tags", [])) & {"contract", "contractAmendment"}:
        result.record_kind = RecordKind.contract_context
        result.publication_state = PublicationState.context_only
        return decide("CN_CONTEXT", "Published contract notice/amendment; awarded contract context, with no verified submission invitation.", lifecycle="awarded")
    if flags.get("registration_only") or re.search(r"\bkeep me updated\b|\bnewsletter\b", result.title, re.I):
        result.record_kind = RecordKind.registration_context
    if result.record_kind.value in CONTEXT:
        result.publication_state = PublicationState.context_only
        return decide("CONTEXT", "Registration, readiness or existing-supplier context is not a current work package.")
    if result.lifecycle.value in INACTIVE:
        return decide("INACTIVE", f"Official lifecycle is {result.lifecycle.value}; excluded from current alerts.")
    if result.close_at_utc and now >= utc_datetime(result.close_at_utc):
        return decide("DEADLINE_PASSED", "The exact submission deadline has passed; no award is inferred.", lifecycle="closed")
    evidence_ids = {s["evidence_id"] for s in result.sources}
    if result.review_state != ReviewState.reviewed or not result.classification_evidence or not set(result.classification_evidence) <= evidence_ids:
        return decide("REVIEW", "Status evidence is absent, unreviewed or lacks a valid source reference.", held=True)
    if age is None or age < timedelta(0):
        return decide("UNVERIFIED", "No authoritative verification at or before this build time.", held=True)
    if result.verification_error:
        result.freshness_state = "stale"
        return decide("VERIFICATION_FAILED", "Latest verification failed; prior facts retained without renewing current status.", held=True)
    opening = flags.get("opens_at")
    not_yet_open = bool(opening and utc_datetime(opening) > now)
    route = result.application_route
    route_age = _age(route.get("verified_at"), now)
    route_ok = (route.get("purpose") in {"submit", "procurement_eoi"}
                and bool(route.get("url") or route.get("email")) and bool(route.get("instructions", "").strip())
                and route.get("evidence_id") in evidence_ids and route_age is not None
                and timedelta(0) <= route_age <= timedelta(hours=24))
    time_ok = ((result.close_precision == "instant" and result.close_at_utc is not None)
               or (result.close_precision == "ongoing_explicit" and flags.get("ongoing_intake") is True))
    if (result.record_kind == RecordKind.procurement and flags.get("authoritative_scope") is True
            and flags.get("accepting_submissions") is True and not not_yet_open
            and result.procurement_stage in {"RFT", "RFQ", "procurement_EOI", "verified_other"}
            and route_ok and time_ok and age <= timedelta(hours=24)):
        return decide("OPEN", "Specific procurement expressly accepts submissions; verified official route and future exact deadline or explicit ongoing intake.", "confirmed_open", "open")
    if flags.get("published_scope") is True and flags.get("authoritative_scope") is True and result.record_kind in {RecordKind.planned_scope, RecordKind.procurement}:
        if age > timedelta(days=30):
            return decide("STALE_PLAN", "Published scope is overdue for the 30-day review; present availability is unverified.", held=True)
        forecast_end = result.forecast_period.get("end")
        forecast_expired = False
        if forecast_end:
            try:
                forecast_expired = utc_datetime(forecast_end) < now
            except ValueError:
                if re.fullmatch(r"\d{4}-\d{2}-\d{2}", forecast_end):
                    forecast_expired = datetime.fromisoformat(forecast_end).date() < now.date()
        if forecast_expired:
            return decide("PAST_FORECAST", "Indicative forecast period has elapsed; updated planning evidence is required.", held=True)
        return decide("FUTURE", "Official published future/ongoing scope; current availability and any bid invitation are not established. Conditions remain applicable.", "published_future_scope", "ongoing_scope" if result.lifecycle == Lifecycle.ongoing_scope else "planned")
    if result.record_kind == RecordKind.hypothesis and flags.get("hypothesis_reason") and flags.get("missing_evidence") and age <= timedelta(days=30):
        return decide("HYPOTHESIS", "Reviewed analyst hypothesis: " + flags["hypothesis_reason"] + "; missing evidence: " + "; ".join(flags["missing_evidence"]), "speculative")
    return decide("INSUFFICIENT", "Current procurement gates are not met: verify scope, intake, deadline, official route and freshness. Missing evidence is not speculation.", held=True)
