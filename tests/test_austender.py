import json
from pathlib import Path
from urllib.parse import urlsplit
import pytest

from defence_radar.config import load_sources
from defence_radar.evidence import save_snapshot
from defence_radar.http_client import HttpClient, Response, FetchError
from defence_radar.ingest.austender import (parse_package, normalize, fetch_window, date_url,
                                           replay_saved, incremental_start)
from defence_radar.storage import Repository
from defence_radar.models import utc_datetime

FIX = Path(__file__).parent / "fixtures/austender"
AT = "2026-11-22T09:00:00Z"
START, END = "2026-11-20T00:00:00Z", "2026-11-21T00:00:00Z"
URL = date_url("contractLastModified", START, END)
POLICY = load_sources("config/sources.json")[0]


def client(responses, **kwargs):
    calls, sleeps = [], []
    def transport(url, timeout, size):
        calls.append(url)
        response = responses[len(calls)-1]
        return Response(response[0], response[1], response[2], url)
    kwargs.setdefault("clock", lambda: utc_datetime(AT))
    return HttpClient(POLICY, transport=transport, sleeper=sleeps.append, min_gap=0, **kwargs), calls, sleeps


def test_real_context_and_missing_license(tmp_path):
    body = (FIX / "terminal.json").read_bytes()
    package = parse_package(body)
    snapshot = save_snapshot(tmp_path, "austender", URL, body, AT)
    records = normalize(package, snapshot)
    assert records and all(r.buyer == "Department of Defence" for r in records)
    for record in records:
        assert record.record_kind.value == "contract_context"
        assert record.close_at_utc is None and record.application_route["email"] is None
        assert not record.locations
        assert record.evidence_flags["licence_declared"]
    by_id = normalize(parse_package((FIX / "by-id.json").read_bytes()), snapshot)
    assert by_id and not by_id[0].evidence_flags["licence_declared"]


def test_complete_chain_and_replay_dedup(tmp_path):
    first = json.loads((FIX / "page1.json").read_text())
    # Original authored terminal page, explicitly synthetic; real saved page2 is NOT terminal.
    terminal = {"releases": [], "license": first["license"]}
    responses = [(200, {}, json.dumps(p).encode()) for p in (first, terminal)]
    with Repository(tmp_path / "db") as repo:
        http, calls, _ = client(responses)
        run = fetch_window(repo, http, tmp_path, "contractLastModified", START, END, AT)
        assert run["state"] == "complete" and run["pages"] == 2
        assert calls[1] == first["links"]["next"]
        assert repo.checkpoint("austender", "contractLastModified") == END
        count = repo.connection.execute("select count(*) from releases").fetchone()[0]
        http, _, _ = client(responses)
        fetch_window(repo, http, tmp_path, "contractLastModified", START, END, AT)
        assert repo.connection.execute("select count(*) from releases").fetchone()[0] == count


@pytest.mark.parametrize("next_url", [URL, "https://evil.example/ocds/a", URL.replace("20T", "19T")])
def test_bad_next_never_promotes(tmp_path, next_url):
    p = json.loads((FIX / "page1.json").read_text()); p["links"] = {"next": next_url}
    http, calls, _ = client([(200, {}, json.dumps(p).encode())])
    with Repository(tmp_path / "db") as repo:
        run = fetch_window(repo, http, tmp_path, "contractLastModified", START, END, AT)
        assert run["state"] == "partial" and len(calls) == 1
        assert repo.list_records() == [] and repo.checkpoint("austender", "contractLastModified") is None


def test_page2_is_incomplete_and_no_checkpoint(tmp_path):
    http, calls, _ = client([(200, {}, (FIX / f"page{i}.json").read_bytes()) for i in (1, 2)])
    with Repository(tmp_path / "db") as repo:
        run = fetch_window(repo, http, tmp_path, "contractLastModified", START, END, AT, max_pages=2)
        assert run["state"] == "partial" and repo.list_records() == []
        assert len(calls) == 2


def test_saved_replay_retains_dates_and_reports_gap(tmp_path):
    with Repository(tmp_path / "db") as repo:
        runs = replay_saved(repo, FIX, tmp_path)
        assert any(r["state"] == "partial" for r in runs)
        assert any(r["state"] == "complete" for r in runs)
        assert repo.checkpoint("austender", "contractPublished") is None
        assert all(r.verified_at.startswith("2026-11-22") for r in repo.list_records())
        assert all(r.review_state.value == "reviewed" for r in repo.list_records())
        with pytest.raises(ValueError, match="explicit"): incremental_start(repo, "contractLastModified")


def test_retry_and_redirect_boundaries():
    http, calls, sleeps = client([(429, {"Retry-After": "3"}, b""), (200, {}, b"{}")])
    assert http.get(URL).status == 200 and sleeps == [3]
    for responses, kwargs, expected in [
        ([(403, {}, b"")], {}, 1),
        ([(503, {}, b"")] * 3, {}, 3),
        ([(429, {"Retry-After": "99"}, b"")], {}, 1),
        ([(302, {"Location": "https://evil.example/"}, b"")], {}, 1),
        ([(200, {}, b"12345")], {"max_bytes": 3}, 1),
        ([], {"offline": True}, 0),
    ]:
        http, calls, _ = client(responses, **kwargs)
        with pytest.raises(FetchError): http.get(URL, expected_path=urlsplit(URL).path)
        assert len(calls) == expected


@pytest.mark.parametrize("body", [b"oops", b"{}", b'{"releases":{}}'])
def test_invalid_package(body):
    with pytest.raises(ValueError): parse_package(body)


def test_empty_window_400_errorcode_100_completes_with_zero_records(tmp_path):
    body = b'{"errorCode": 100, "message": "No Records found for Date Range [\'2026-11-21T00:00:00Z\'-\'2026-11-22T00:00:00Z\']"}'
    c, calls, _ = client([(400, {"Content-Type": "application/json"}, body)])
    with Repository(tmp_path / "db") as repo:
        run = fetch_window(repo, c, tmp_path / "raw", "contractLastModified", START, END, AT)
        assert run["state"] == "complete" and run["records"] == 0 and run["pages"] == 1
        assert repo.checkpoint("austender", "contractLastModified") == END


def test_other_400_still_fails(tmp_path):
    c, _, _ = client([(400, {}, b'{"errorCode": 7, "message": "Bad date"}')])
    with Repository(tmp_path / "db") as repo:
        run = fetch_window(repo, c, tmp_path / "raw", "contractLastModified", START, END, AT)
        assert run["state"] == "failed" and repo.checkpoint("austender", "contractLastModified") is None


def test_notice_page_url_from_award_id_and_supplier_enrichment(tmp_path):
    from defence_radar.ingest.austender import notice_url
    # Verified pair (25 Nov 2026): API awardID suffix == public CN page GUID.
    assert notice_url({"awardID": "CN3954729-ffe437df1cc74959b8a430c96c25fcfa"}) == \
        "https://www.tenders.gov.au/Cn/Show/ffe437df-1cc7-4959-b8a4-30c96c25fcfa"
    assert notice_url({"awardID": "CN385455-A2-62eff52de613d2a913b4473c2db77455"}).endswith("/62eff52d-e613-d2a9-13b4-473c2db77455")
    assert notice_url({}) is None and notice_url({"awardID": "garbage"}) is None
    package = {"license": "https://creativecommons.org/licenses/by/3.0/au/", "releases": [{
        "ocid": "prod-1", "id": "prod-1-r", "date": "2026-11-16T02:34:55Z", "tag": ["contract"],
        "tender": {"procurementMethodDetails": "Limited tender"},
        "parties": [{"id": "s1", "name": "DELTA HYDRAULICS PTY LTD", "roles": ["supplier"],
                     "address": {"locality": "HENDERSON", "region": "WA", "postalCode": "6166"},
                     "contactPoint": {"branch": "NSSG - Maritime Sustainment Division", "division": "NSSG"}},
                    {"id": "b", "name": "Department of Defence", "roles": ["procuringEntity"]}],
        "awards": [{"id": "CN1-0123456789abcdef0123456789abcdef", "suppliers": [{"id": "s1", "name": "DELTA HYDRAULICS PTY LTD"}]}],
        "contracts": [{"id": "CN1", "awardID": "CN1-0123456789abcdef0123456789abcdef", "description": "Hydraulic Components",
                       "dateSigned": "2026-11-16T02:34:55Z", "value": {"amount": "1000.00", "currency": "AUD"},
                       "items": [{"classification": {"scheme": "UNSPSC", "id": "25170000"}}]}]}]}
    snap = save_snapshot(tmp_path, "austender", URL, json.dumps(package).encode(), AT)
    rec = normalize(package, snap)[0]
    assert rec.sources[0]["url"] == "https://www.tenders.gov.au/Cn/Show/01234567-89ab-cdef-0123-456789abcdef"
    assert rec.sources[0]["api_url"] == URL
    assert rec.prime == "DELTA HYDRAULICS PTY LTD"
    f = rec.evidence_flags
    assert f["suppliers"][0] == {"name": "DELTA HYDRAULICS PTY LTD", "locality": "Henderson", "region": "WA", "postcode": "6166"}
    assert f["buyer_branch"] == "NSSG - Maritime Sustainment Division" and f["procurement_method"] == "Limited tender"
    assert rec.source_published_at == "2026-11-16T02:34:55Z" and not rec.locations  # supplier address is never a worksite
