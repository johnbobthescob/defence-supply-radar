"""AusTender current approach-to-market (ATM) RSS feed (Department of Finance, CC BY 3.0 AU).

Primary path is import of an operator-saved copy; the optional live fetch goes through the
policy-checked HttpClient and records a failed run honestly (e.g. CloudFront 403). The exact item
schema is unverified, so every description field is optional. ATM pages/documents are never fetched."""
from datetime import datetime, timezone
import hashlib
import html
from email.utils import parsedate_to_datetime
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from ..classify import parse_close
from ..evidence import save_snapshot
from ..http_client import FetchError
from ..models import Opportunity, utc_iso

SOURCE_ID = "austender_atm"
ORIGINAL_FEED_URL = "https://www.tenders.gov.au/public_data/rss/rss.xml"
FEED_PATH = "/public_data/rss/rss.xml"
MAX_BYTES = 5_000_000
ATTRIBUTION = ("Contains AusTender approach-to-market data published by the Australian Government "
               "Department of Finance, licensed under CC BY 3.0 AU https://creativecommons.org/licenses/by/3.0/au/. "
               "Filtered and classified by Henderson Defence Supply-Chain Radar; not endorsed by the Commonwealth.")
INSTRUCTIONS = ("Register (free) on AusTender, download the approach-to-market documents and lodge "
                "through the ATM page before the closing time.")
SITE = "https://www.tenders.gov.au/"
_DOCTYPE = re.compile(rb"<!\s*(DOCTYPE|ENTITY)", re.I)
_MONTHS = {m: i for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}


def _text(element, tag):
    child = element.find(tag)
    return (child.text or "").strip() if child is not None else ""


def _html_to_lines(value):
    value = re.sub(r"(?i)<\s*(br\s*/?|/p|/div|/li|/tr|/h\d)\s*>", "\n", value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return [re.sub(r"\s+", " ", line).strip() for line in value.splitlines() if line.strip()]


def _field(lines, *labels):
    for line in lines:
        for label in labels:
            m = re.match(rf"{label}\s*:\s*(.+)$", line, re.I)
            if m:
                return m[1].strip()
    return ""


def _parse_close_text(raw):
    """Return (close_raw, zone, iso_local_or_date_or_None). Only ACT local time (Sydney zone) is converted."""
    m = re.search(r"(\d{1,2})-([A-Za-z]{3})[a-z]*-(\d{4})(?:\s+(\d{1,2}):(\d{2})\s*([ap]m)?)?\s*(?:\(([^)]*)\))?", raw, re.I)
    if not m or m[2].lower() not in _MONTHS:
        return raw, None, None
    day, mon, year = int(m[1]), _MONTHS[m[2].lower()], int(m[3])
    try:
        if m[4] is None:
            return raw, None, datetime(year, mon, day).date().isoformat()
        hour, minute = int(m[4]), int(m[5])
        if m[6]:
            if not 1 <= hour <= 12:
                return raw, None, None
            hour = hour % 12 + (12 if m[6].lower() == "pm" else 0)
        local = datetime(year, mon, day, hour, minute).isoformat()
    except ValueError:
        return raw, None, None
    zone_text = (m[7] or "").strip()
    if re.match(r"ACT\b", zone_text, re.I):
        return raw, "Australia/Sydney", local
    return raw, None, None  # other or absent abbreviations do not identify a zone


def parse_feed(body):
    if not isinstance(body, bytes):
        raise TypeError("body must be bytes")
    if len(body) > MAX_BYTES:
        raise ValueError("ATM feed exceeds the 5 MB bound")
    if _DOCTYPE.search(body):
        raise ValueError("ATM feed contains a DOCTYPE/ENTITY declaration; rejected")
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise ValueError("Malformed ATM RSS XML") from exc
    channel = root.find("channel") if root.tag == "rss" else None
    if channel is None:
        raise ValueError("ATM feed requires RSS 2.0 <rss><channel>")
    items = []
    for element in channel.findall("item"):
        lines = _html_to_lines(_text(element, "description"))
        pub = _text(element, "pubDate")
        try:
            pub_iso = utc_iso(parsedate_to_datetime(pub)) if pub else None
        except (TypeError, ValueError):
            pub_iso = None
        code = re.search(r"\b(\d{8})\b", _field(lines, "UNSPSC(?: Code)?", "Category(?: Code)?") or "")
        close_text = _field(lines, r"Close(?:s)? Date(?: (?:&|and) Time)?", r"Closing Date(?: (?:&|and) Time)?")
        close_raw = close_zone = None
        if close_text:
            close_raw, close_zone, _ = _parse_close_text(close_text)
        items.append(dict(
            title=re.sub(r"\s+", " ", _text(element, "title")), link=_text(element, "link"),
            description_text=" ".join(lines), pub_date=pub_iso, guid=_text(element, "guid"),
            atm_id=_field(lines, r"ATM ID", r"ATM Id", r"Reference(?: Number)?"),
            agency=_field(lines, "Agency"), category_code=code[1] if code else None,
            close_raw=close_raw, close_zone=close_zone, _close_text=close_text or None))
    return items


def _close_fields(item):
    text = item.get("_close_text")
    if not text:
        return parse_close(None)
    raw, zone, iso = _parse_close_text(text)
    if iso is None:
        result = parse_close(None)
        result["close_raw"] = raw
        return result
    return parse_close(iso, zone) | {"close_raw": raw}


def _site_url(link):
    return link if isinstance(link, str) and link.startswith(SITE) and " " not in link else None


def normalize(items, snapshot):
    records = []
    at = snapshot["accessed_at"]
    for index, item in enumerate(items):
        atm_id = re.sub(r"[^A-Za-z0-9_.:/-]", "", item.get("atm_id") or "")
        ident = atm_id or hashlib.sha256((item.get("link") or item.get("guid") or item["title"]).encode()).hexdigest()[:16]
        evidence_id = f"atm:{snapshot['sha256'][:16]}:{index}"
        link = _site_url(item.get("link"))
        close = _close_fields(item)
        code = item.get("category_code")
        records.append(Opportunity(
            id="atm:" + ident, source_record_id="atm:" + ident, source_ids=[SOURCE_ID], rights=[SOURCE_ID],
            title=item["title"] or ident, summary=item["description_text"], buyer=item.get("agency") or "",
            record_kind="procurement", lifecycle="open", review_state="reviewed", publication_state="publishable",
            procurement_stage="verified_other",
            sources=[dict(source_id=SOURCE_ID, url=link or snapshot["url"], api_url=snapshot["url"], accessed_at=at,
                          evidence_id=evidence_id, snapshot_sha256=snapshot["sha256"],
                          pointer=f"/rss/channel/item[{index}]", notice_id=atm_id)],
            classification_evidence=[evidence_id], verified_at=at, first_seen_at=at, last_seen_at=at,
            source_published_at=item.get("pub_date"),
            close_at_utc=close["close_at_utc"], close_raw=close["close_raw"], close_zone=close["close_zone"],
            close_precision=close["close_precision"],
            application_route=dict(purpose="submit", url=link, email=None, instructions=INSTRUCTIONS,
                                   verified_at=at, evidence_id=evidence_id, account_required="yes"),
            attribution=[ATTRIBUTION],
            evidence_flags={"unspsc": [{"scheme": "UNSPSC", "id": code}] if code else [], "atm_feed": True,
                            "licence_declared": True, "authoritative_scope": True, "accepting_submissions": True},
            warnings=[]))
    return records


def _persist(repo, body, raw_root, accessed_at, headers):
    snapshot = save_snapshot(raw_root, SOURCE_ID, ORIGINAL_FEED_URL, body, accessed_at, headers=headers)
    repo.add_snapshot(snapshot)
    items = parse_feed(body)
    records = normalize(items, snapshot)
    for record in records:
        repo.save_record(record, accessed_at)
    return items, records


def import_feed(repo, path, raw_root, accessed_at=None):
    """Import a feed copy saved by the operator. accessed_at should be the time it was saved (pass
    --accessed-at); it defaults to the file mtime, which is only right if the file was not copied since."""
    path = Path(path)
    body = path.read_bytes()
    if accessed_at is None:
        accessed_at = utc_iso(datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0))
    accessed_at = utc_iso(accessed_at)
    items, records = _persist(repo, body, raw_root, accessed_at, {"content-type": "application/rss+xml"})
    repo.record_run(SOURCE_ID, "feed", accessed_at, accessed_at, "complete", accessed_at,
                    pages=1, records=len(records), live=False)
    return {"items": len(items), "imported": len(records), "accessed_at": accessed_at}


def fetch_feed(repo, client, raw_root, at):
    try:
        response = client.get(ORIGINAL_FEED_URL, expected_path=FEED_PATH)
        items, records = _persist(repo, response.body, raw_root, utc_iso(client.clock()), response.headers)
    except (FetchError, ValueError, OSError) as exc:
        return repo.record_run(SOURCE_ID, "feed", at, at, "failed", at, error=str(exc), live=True)
    return repo.record_run(SOURCE_ID, "feed", at, at, "complete", at, pages=1, records=len(records), live=True)
