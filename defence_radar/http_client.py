"""Bounded serial GETs. Redirects are validated before any follow-up request."""
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, HTTPRedirectHandler, build_opener

from .policy import validate_fetch_url


class FetchError(ValueError):
    pass


class NoRecordsError(FetchError):
    """The CN API's documented empty-window answer (HTTP 400, errorCode 100)."""
    def __init__(self, response):
        super().__init__("No records found for date range")
        self.response = response


def is_no_records(response):
    if response.status != 400:
        return False
    try:
        data = json.loads(response.body)
    except (ValueError, UnicodeError):
        return False
    return (isinstance(data, dict) and data.get("errorCode") == 100
            and str(data.get("message", "")).startswith("No Records found"))


@dataclass
class Response:
    status: int
    headers: dict
    body: bytes
    url: str


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def urllib_transport(url, timeout, max_bytes):
    request = Request(url, headers={"User-Agent": "HendersonDefenceSupplyRadar/0.1 (public CN research; serial requests)",
                                    "Accept": "application/json"})
    try:
        response = build_opener(NoRedirect()).open(request, timeout=timeout)
    except HTTPError as exc:
        response = exc
    with response:
        body = response.read(max_bytes + 1)
        if len(body) > max_bytes:
            raise FetchError("Response exceeds configured size bound")
        return Response(response.code, dict(response.headers), body, response.geturl())


class HttpClient:
    def __init__(self, policy, *, offline=False, transport=urllib_transport,
                 sleeper=time.sleep, monotonic=time.monotonic,
                 clock=lambda: datetime.now(timezone.utc), min_gap=2.0,
                 timeout=30, max_bytes=8_000_000, attempts=3, wait_budget=30):
        self.policy, self.offline, self.transport = policy, offline, transport
        self.sleeper, self.monotonic, self.clock = sleeper, monotonic, clock
        self.min_gap, self.timeout, self.max_bytes = min_gap, timeout, max_bytes
        self.attempts, self.wait_budget = min(3, max(1, attempts)), wait_budget
        self.last_request = None

    def _validate(self, url, expected_path):
        allowed, reason = validate_fetch_url(self.policy, url, expected_path=expected_path)
        if not allowed:
            raise FetchError(reason)

    def _request(self, url):
        if self.last_request is not None:
            remaining = self.min_gap - (self.monotonic() - self.last_request)
            if remaining > 0:
                self.sleeper(remaining)
        self.last_request = self.monotonic()
        result = self.transport(url, self.timeout, self.max_bytes)
        if len(result.body) > self.max_bytes:
            raise FetchError("Response exceeds configured size bound")
        return result

    def get(self, url, *, expected_path=None):
        if self.offline:
            raise FetchError("Offline mode prohibits remote requests")
        waited = 0.0
        redirects = 0
        attempt = 0
        while attempt < self.attempts:
            self._validate(url, expected_path)
            try:
                response = self._request(url)
            except (URLError, TimeoutError, OSError) as exc:
                attempt += 1
                if attempt >= self.attempts:
                    raise FetchError(f"Transport failed after {attempt} attempts: {type(exc).__name__}") from exc
                delay = 2 ** attempt
            else:
                self._validate(response.url, expected_path)
                headers = {k.lower(): v for k, v in response.headers.items()}
                if response.status in (301, 302, 303, 307, 308):
                    redirects += 1
                    if redirects > 3 or not headers.get("location"):
                        raise FetchError("Invalid or excessive redirects")
                    url = urljoin(url, headers["location"])
                    self._validate(url, expected_path)
                    continue
                if response.status == 200:
                    return response
                if is_no_records(response):
                    raise NoRecordsError(response)
                attempt += 1
                if response.status not in (429, 500, 502, 503, 504) or attempt >= self.attempts:
                    raise FetchError(f"HTTP {response.status}; request stopped")
                delay = 2 ** attempt
                retry = headers.get("retry-after")
                if retry:
                    try:
                        delay = max(0.0, float(retry))
                    except ValueError:
                        try:
                            delay = max(0.0, (parsedate_to_datetime(retry) - self.clock()).total_seconds())
                        except (TypeError, ValueError):
                            raise FetchError("Unparseable Retry-After; deferred")
            if waited + delay > self.wait_budget:
                raise FetchError("Retry-After/backoff exceeds wait budget; deferred")
            self.sleeper(delay)
            waited += delay
        raise FetchError("Request attempts exhausted")
