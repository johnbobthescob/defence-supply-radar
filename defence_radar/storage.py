"""SQLite persistence for immutable evidence, releases, record versions and builds."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sqlite3

from .evidence import canonical_json, digest
from .models import Opportunity, SourcePolicy, utc_iso


def _time(value):
    if isinstance(value, datetime):
        if value.tzinfo is None: raise ValueError("timestamps must be timezone-aware")
        return value.astimezone(timezone.utc).isoformat()
    if value is None: return datetime.now(timezone.utc).isoformat()
    try: return utc_iso(value)
    except ValueError: return str(value)


def material_state(record):
    """Facts used for conflict/delta detection, excluding retrieval observations."""
    data = record.to_dict() if isinstance(record, Opportunity) else dict(record)
    for key in ("first_seen_at", "last_seen_at", "verified_at", "sources", "classification_evidence",
                "last_verification_attempt", "verification_error", "freshness_state"):
        data.pop(key, None)
    route = dict(data.get("application_route", {}))
    route.pop("verified_at", None)
    data["application_route"] = route
    # Licence provenance may be enriched by a date package for an identical release.
    if data.get("source_ids") == ["austender"]:
        flags = dict(data.get("evidence_flags", {}))
        for key in ("licence_declared", "package_licence", "licence_evidence"):
            flags.pop(key, None)
        data["evidence_flags"] = flags
        data.pop("attribution", None)
        data["warnings"] = [w for w in data.get("warnings", []) if not w.startswith(("Package has no established licence", "This response omits the licence"))]
    return data


class Repository:
    def __init__(self, path):
        self.path = Path(path)
        if str(path) != ":memory:": self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(path))
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS policies(id TEXT, hash TEXT, payload TEXT, at TEXT, PRIMARY KEY(id,hash));
        CREATE TABLE IF NOT EXISTS snapshots(id TEXT PRIMARY KEY, source_id TEXT, payload TEXT);
        CREATE TABLE IF NOT EXISTS releases(id INTEGER PRIMARY KEY, ocid TEXT, release_id TEXT, hash TEXT, payload TEXT, snapshot_id TEXT, event_at TEXT, UNIQUE(ocid,release_id,hash), FOREIGN KEY(snapshot_id) REFERENCES snapshots(id));
        CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY, current_hash TEXT, current_event TEXT);
        CREATE TABLE IF NOT EXISTS record_versions(id TEXT, hash TEXT, payload TEXT, event_at TEXT, needs_review INTEGER DEFAULT 0, PRIMARY KEY(id,hash));
        CREATE TABLE IF NOT EXISTS checkpoints(source_id TEXT, field TEXT, value TEXT, PRIMARY KEY(source_id,field));
        CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY, source_id TEXT, field TEXT, start TEXT, end TEXT, state TEXT, at TEXT, pages INTEGER, records INTEGER, error TEXT, live INTEGER);
        CREATE TABLE IF NOT EXISTS builds(profile_hash TEXT, audience TEXT, period TEXT, manifest TEXT, states TEXT, PRIMARY KEY(profile_hash,audience,period));
        PRAGMA user_version=1;
        """)
        self._depth = 0

    def __enter__(self): return self
    def __exit__(self, typ, value, tb): self.close()
    def close(self): self.connection.close()

    @contextmanager
    def transaction(self):
        name = f"sp_{self._depth}"
        if self._depth == 0: self.connection.execute("BEGIN")
        else: self.connection.execute(f"SAVEPOINT {name}")
        self._depth += 1
        try:
            yield self
        except BaseException:
            self._depth -= 1
            if self._depth == 0: self.connection.rollback()
            else:
                self.connection.execute(f"ROLLBACK TO {name}")
                self.connection.execute(f"RELEASE {name}")
            raise
        else:
            self._depth -= 1
            if self._depth == 0: self.connection.commit()
            else: self.connection.execute(f"RELEASE {name}")

    def _tx(self):
        return self.transaction()

    def save_policy(self, policy, at):
        policy = policy if isinstance(policy, SourcePolicy) else SourcePolicy.from_dict(policy)
        payload = canonical_json(policy.to_dict()); h = digest(policy.to_dict())
        with self._tx():
            self.connection.execute("INSERT OR IGNORE INTO policies VALUES(?,?,?,?)", (policy.id,h,payload,_time(at)))

    def add_snapshot(self, snapshot):
        sid = snapshot.get("id") or digest(snapshot)
        with self._tx():
            self.connection.execute("INSERT OR IGNORE INTO snapshots VALUES(?,?,?)",
                                    (sid,snapshot["source_id"],canonical_json(snapshot)))
        return sid

    def add_release(self, ocid, release_id, payload, snapshot_id, event_at):
        h = digest(payload); event = _time(event_at)
        with self._tx():
            cur = self.connection.execute("INSERT OR IGNORE INTO releases(ocid,release_id,hash,payload,snapshot_id,event_at) VALUES(?,?,?,?,?,?)",
                                          (ocid,release_id,h,canonical_json(payload),snapshot_id,event))
            count = self.connection.execute("SELECT COUNT(DISTINCT hash) FROM releases WHERE ocid=? AND release_id=?", (ocid,release_id)).fetchone()[0]
        return {"inserted": cur.rowcount == 1, "conflict": count > 1, "hash": h}

    def _save_record(self, record, event_at=None):
        record = record if isinstance(record, Opportunity) else Opportunity.from_dict(record)
        payload = record.to_dict()
        # Observation timestamps do not constitute substantive changes.
        payload.pop("first_seen_at", None); payload.pop("last_seen_at", None)
        h = digest(payload); event = _time(event_at or record.source_modified_at or record.source_published_at or record.verified_at or "")
        raw = canonical_json(record.to_dict())
        self.connection.execute("INSERT OR IGNORE INTO records(id) VALUES(?)", (record.id,))
        versions = self.connection.execute("SELECT hash,event_at,payload FROM record_versions WHERE id=?", (record.id,)).fetchall()
        equal = [r for r in versions if r["event_at"] == event and material_state(json.loads(r["payload"])) != material_state(record)]
        self.connection.execute("INSERT OR IGNORE INTO record_versions(id,hash,payload,event_at,needs_review) VALUES(?,?,?,?,?)",
                                (record.id,h,raw,event,int(bool(equal))))
        if equal:
            self.connection.execute("UPDATE record_versions SET needs_review=1 WHERE id=? AND event_at=?", (record.id,event))
        current = self.connection.execute("SELECT current_hash,current_event FROM records WHERE id=?", (record.id,)).fetchone()
        if current["current_hash"] is None or event > (current["current_event"] or "") or (event == current["current_event"] and not equal):
            self.connection.execute("UPDATE records SET current_hash=?,current_event=? WHERE id=?", (h,event,record.id))
        return h

    def save_record(self, record, event_at=None):
        with self._tx(): return self._save_record(record,event_at)

    def list_records(self):
        rows=self.connection.execute("SELECT v.payload,v.needs_review FROM records r JOIN record_versions v ON r.id=v.id AND r.current_hash=v.hash ORDER BY r.id")
        return [self._decode(r) for r in rows]

    @staticmethod
    def _decode(row):
        record = Opportunity.from_dict(json.loads(row[0]))
        if row[1]:
            record.review_state = "needs_review"
            record.publication_state = "held"
            record.status_class = None
            record.evidence_flags["conflicting_versions"] = True
            record.warnings.append("Conflicting equal-time source versions require review.")
            record.validate()
        return record

    def get_record(self, record_id):
        row=self.connection.execute("SELECT v.payload,v.needs_review FROM records r JOIN record_versions v ON r.id=v.id AND r.current_hash=v.hash WHERE r.id=?", (record_id,)).fetchone()
        return self._decode(row) if row else None

    def checkpoint(self, source_id, field):
        row=self.connection.execute("SELECT value FROM checkpoints WHERE source_id=? AND field=?", (source_id,field)).fetchone()
        return row[0] if row else None

    def _window(self, source_id, field, start, end, snapshots, releases, records, at, live=True):
        snapshot_ids={}
        for snap in snapshots: snapshot_ids[snap.get("id") or digest(snap)] = self.add_snapshot(snap)
        for rel in releases:
            self.add_release(rel["ocid"],rel["release_id"],rel["payload"],rel["snapshot_id"],rel["event_at"])
        for rec in records: self._save_record(rec)
        result = self._record_run(source_id,field,start,end,"complete",at,len(snapshots),len(releases),None,live)
        if live:
            prior=self.checkpoint(source_id,field)
            # A failed gap pins progress until a window beginning at/before it completes.
            gap=self.connection.execute("""
                SELECT f.start FROM runs f
                WHERE f.source_id=? AND f.field=? AND f.state!='complete' AND f.live=1
                AND NOT EXISTS (
                  SELECT 1 FROM runs c WHERE c.source_id=f.source_id AND c.field=f.field
                  AND c.state='complete' AND c.live=1 AND c.start<=f.start AND c.end>=f.end
                ) ORDER BY f.start LIMIT 1
            """,(source_id,field)).fetchone()
            if gap is None or end <= gap[0]:
                value=max((x for x in (prior,end) if x is not None), default=end)
                self.connection.execute("INSERT INTO checkpoints VALUES(?,?,?) ON CONFLICT(source_id,field) DO UPDATE SET value=excluded.value",(source_id,field,value))
        return result

    def complete_window(self, source_id, field, start, end, snapshots, releases, records, at, live=True):
        with self._tx(): return self._window(source_id,field,start,end,snapshots,releases,records,at,live)

    def _record_run(self, source_id, field, start, end, state, at, pages, records, error, live):
        if error is not None:
            error = re.sub(r"(?i)(authorization|cookie|token|api[_-]?key|password)(\s*[:=]\s*)[^\s,;]+", r"\1\2[redacted]", str(error))
        self.connection.execute("INSERT INTO runs(source_id,field,start,end,state,at,pages,records,error,live) VALUES(?,?,?,?,?,?,?,?,?,?)",
                                (source_id,field,start,end,state,_time(at),pages,records,error,int(live)))
        return {"source_id":source_id,"field":field,"start":start,"end":end,"state":state,"at":_time(at),"pages":pages,"records":records,"error":error,"live":bool(live)}

    def record_run(self, source_id, field, start, end, state, at, pages=0, records=0, error=None, live=True):
        if state not in {"complete","partial","failed"}: raise ValueError("invalid run state")
        with self._tx(): return self._record_run(source_id,field,start,end,state,at,pages,records,error,live)

    def runs(self):
        return [dict(r) for r in self.connection.execute("SELECT source_id,field,start,end,state,at,pages,records,error,live FROM runs ORDER BY id")]

    def save_build(self, manifest, record_states):
        profile=manifest["profile_hash"]; audience=manifest["audience"]; period=str(manifest["period"])
        with self._tx():
            self.connection.execute("INSERT OR REPLACE INTO builds VALUES(?,?,?,?,?)",(profile,audience,period,canonical_json(manifest),canonical_json(record_states)))

    def previous_build(self, profile_hash, audience, period):
        row=self.connection.execute("SELECT manifest,states FROM builds WHERE profile_hash=? AND audience=? AND period<? ORDER BY period DESC LIMIT 1",(profile_hash,audience,str(period))).fetchone()
        return {"manifest":json.loads(row["manifest"]),"record_states":json.loads(row["states"])} if row else None
