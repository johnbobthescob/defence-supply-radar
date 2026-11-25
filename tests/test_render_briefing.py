"""Briefing, work-package and CSV rendering contract tests on synthetic payloads."""
import csv
import io
import re

from defence_radar.render.briefing import render_briefing
from defence_radar.render.briefing_html import render_briefing_html
from defence_radar.render.common import money, md_inline
from defence_radar.render.exports import render_csv
from defence_radar.render.html_list import render_html

NOTICE = "https://www.tenders.gov.au/Cn/Show/d5553bae-31bf-4445-9416-f9253ba85b4f"
REASONS = ["+42 Marine electrical: UNSPSC 39120000 (Electrical equipment and components); 'electrical' in title",
           "+15 activity matches your profile: supply", "+10 maritime context: buyer unit NSSG is maritime", "+0 delivery location not published"]


def match(score=72, band="strong"):
    return {"score": score, "band": band, "reasons": REASONS, "components": {"capability": 42}, "matched_capabilities": ["marine_electrical"],
            "missing_capabilities": [], "evidence": [], "exclusions": [], "shortlist": True, "eligibility": {"status": "incomplete", "limitation": "unknown"}}


def award(cn="CN4289100", title="Electrical Component", score=72, amount="36841.20"):
    return {"record": {"id": "cn:" + cn, "source_record_id": cn, "source_ids": ["austender"], "title": title, "summary": title, "record_kind": "contract_context",
            "status_class": "awarded_context", "lifecycle": "awarded", "buyer": "Department of Defence", "prime": "ELECTROTECH AUSTRALIA PTY LTD",
            "classification_reason": "Awarded contract notice: market context, not an opportunity to bid.", "source_published_at": "2026-11-16T04:10:17Z",
            "value_context": {"amount": amount, "currency": "AUD"}, "contract_period": {"startDate": "2026-10-27T13:00:00Z", "endDate": "2027-02-01T13:00:00Z"},
            "evidence_flags": {"buyer_branch": "NSSG - Maritime Sustainment Division", "date_signed": "2026-11-16T04:10:17Z", "unspsc": [{"scheme": "UNSPSC", "id": "39120000"}],
                               "suppliers": [{"name": "ELECTROTECH AUSTRALIA PTY LTD", "locality": "Brookvale", "region": "NSW", "postcode": "2100"}]},
            "sources": [{"source_id": "austender", "url": NOTICE, "api_url": "https://api.tenders.gov.au/ocds/findById/CN", "notice_id": cn, "accessed_at": "2026-11-25T01:00:00Z",
                         "licence_url": "https://creativecommons.org/licenses/by/3.0/au/"}], "attribution": ["AusTender"], "close_precision": "not_applicable",
            "application_route": {"purpose": "none_published"}, "conditions": []},
            "match": match(score)}


def open_row(title="Hydraulic hose supply", score=60):
    return {"record": {"id": "atm:1", "source_record_id": "ATM2026-1", "source_ids": ["austender_atm"], "title": title, "summary": "Supply hoses", "record_kind": "procurement",
            "status_class": "confirmed_open", "lifecycle": "open", "buyer": "Department of Defence", "close_at_utc": "2026-12-01T06:00:00Z", "close_raw": "1-Dec-2026 2:00 pm",
            "close_precision": "instant", "classification_reason": "Open ATM", "conditions": [],
            "application_route": {"purpose": "submit", "url": "https://www.tenders.gov.au/Atm/Show/abc", "account_required": "yes", "instructions": "Submit via AusTender"},
            "sources": [{"source_id": "austender_atm", "url": "https://www.tenders.gov.au/Atm/Show/abc", "notice_id": "ATM2026-1", "accessed_at": "2026-11-25T01:00:00Z"}], "attribution": []},
            "match": match(score, "good")}


def payload(rows):
    aw = [r for r in rows if r["record"]["status_class"] == "awarded_context"]
    return {"period": "2026-11-22", "week": {"start": "2026-11-16", "end": "2026-11-22", "zone": "Australia/Perth"}, "as_of": "2026-11-25T02:00:00Z",
            "rows": rows, "profile": {"name": "Synthetic Marine Co <b>"}, "rule_versions": {"classification": "status-2", "matching": "match-2"}, "taxonomy_version": 2,
            "attribution": ["Contains AusTender data; CC BY 3.0 AU"], "delta": {"new": [], "changed": [], "closed": []},
            "market": {"awards_in_week": len(aw), "total_value": 1_234_567.0, "currency": "AUD", "note": "Awards are not open opportunities.",
                       "suppliers": [{"name": "ELECTROTECH AUSTRALIA PTY LTD", "count": 1, "value": 36841.2, "locality": "Brookvale", "region": "NSW", "titles": ["Electrical Component"], "best_score": 72, "notice_ids": ["CN4289100"]}],
                       "buyers": [{"name": "NSSG - Maritime Sustainment Division", "agency": "Department of Defence", "count": 1, "value": 36841.2}],
                       "capabilities": [{"id": "marine_electrical", "label": "Marine electrical", "count": 1, "value": 36841.2}], "wa_suppliers": []},
            "actions": [{"priority": 3, "kind": "teaming", "text": "Approach Electrotech (Brookvale, NSW) as a teaming partner: they won 'Electrical Component' (CN4289100, $37k).", "url": NOTICE},
                        {"priority": 6, "kind": "check", "text": "Check ICN Gateway.", "url": "https://gateway.icn.org.au/"}],
            "coverage": {"summary": "s", "warnings": ["Source x is stale <script>"], "held": {"total": 3, "by_source": {"aic": 3}}, "excluded_irrelevant": 5,
                         "confirmed_open": sum(r["record"]["status_class"] == "confirmed_open" for r in rows), "context_records": len(aw),
                         "sources": [{"id": "austender", "access_mode": "api", "rights_status": "licensed", "last_successful_refresh": "2026-11-25T01:04:19Z", "stale": False},
                                     {"id": "austender_atm", "access_mode": "api", "rights_status": "licensed", "last_successful_refresh": None, "stale": False}]}}


HEADINGS = ["Executive summary", "Open opportunities", "Upcoming and future scope", "Who is winning", "Recommended actions this week", "Coverage and data quality"]


def section(text, start, end=None):
    i = text.index(start)
    j = text.index(end, i + 1) if end else len(text)
    return text[i:j]


def test_section_order_in_html_and_markdown():
    p = payload([award(), open_row()])
    for text in (render_briefing_html(p), render_briefing(p)):
        pos = [text.index(h) for h in HEADINGS]
        assert pos == sorted(pos)
    assert "Defence Supply Radar — weekly briefing" in render_briefing(p)
    assert "Wed 25 Nov 2026 10:00 AWST" in render_briefing_html(p)
    assert "Week 2026-11-16 to 2026-11-22 (AWST)" in render_briefing_html(p)


def test_awarded_rows_never_in_open_section_and_open_card_content():
    p = payload([award(), open_row()])
    for text, nxt in ((render_briefing_html(p), "Upcoming and future scope"), (render_briefing(p), "## Upcoming and future scope")):
        open_part = section(text, "Open opportunities", nxt)
        assert "Hydraulic hose supply" in open_part and "Electrical Component" not in open_part and "CN4289100" not in open_part
        assert "Tue 1 Dec 2026 14:00 AWST" in open_part and "1-Dec-2026 2:00 pm" in open_part and "Fit 60/100 (good)" in open_part
        assert "https://www.tenders.gov.au/Atm/Show/abc" in open_part
        win = text[text.index("Who is winning"):]
        assert "AWARDED" in win and "CN4289100" in win
    low = payload([award(), open_row(score=10)])
    assert "Hydraulic hose supply" not in section(render_briefing(low), "## Open opportunities", "## Upcoming")


def test_empty_open_state_is_honest():
    p = payload([award()])
    for text in (render_briefing_html(p), render_briefing(p)):
        assert "No verified open tenders were imported this week." in text
        assert "https://www.tenders.gov.au/atm" in text and "https://gateway.icn.org.au/" in text
        assert "No verified open tenders this week" in text
        assert "does not mean nothing is open" in text


def test_no_dict_artefacts_and_escaping():
    p = payload([award(title="O'Brien <img src=x> & Sons"), open_row()])
    md, h = render_briefing(p), render_briefing_html(p)
    for text in (md, h):
        for bad in ("{'", "&#x27;", "{&", "defaultdict"):
            assert bad not in text
    assert "<img src=x>" not in h and "&lt;img src=x&gt;" in h and "O&apos;Brien" in h and "<script>" not in h
    assert "Synthetic Marine Co &lt;b&gt;" in h
    assert "O'Brien" in md and "\\<img" in md
    assert "\\." not in md and "\\-" not in md


def test_notice_links_and_money():
    p = payload([award()])
    assert f"[CN4289100]({NOTICE})" in render_briefing(p)
    assert f'href="{NOTICE}"' in render_briefing_html(p)
    assert money(1_234_567) == "$1.2m" and money(350_000) == "$350k" and money(999_700) == "$1.0m" and money(350) == "$350"
    assert "$1.2m" in render_briefing_html(p) and "$37k" in render_briefing_html(p)


def test_html_is_self_contained_and_deterministic():
    p = payload([award(), open_row()])
    h = render_briefing_html(p)
    assert h == render_briefing_html(p) and render_briefing(p) == render_briefing(p)
    assert "<script" not in h and "@import" not in h and "url(http" not in h.lower()
    assert not re.search(r"<link[^>]+href", h) and not re.search(r"\ssrc=", h)
    assert 'lang="en"' in h and "@page" in h and "@media print" in h
    assert "AusTender data © Commonwealth of Australia (Department of Finance), CC BY 3.0 AU" in h
    assert "not eligibility or approval" in h


def test_work_packages_filters_and_awarded_badge():
    p = payload([award(), open_row()])
    h = render_html(p)
    for ident in ('id="cls"', 'id="minscore"', 'id="agency"', 'id="cat"', 'id="q"', 'id="sort"', 'aria-live'):
        assert ident in h
    assert "AWARDED — not an opportunity" in h and "API record" in h and NOTICE in h
    assert "Fit 72/100 (strong)" in h and "All 4 scoring reasons" in h
    assert "{'" not in h and "&#x27;" not in h
    assert "<script src" not in h and "@import" not in h and not re.search(r"<link[^>]+href", h)
    assert "UNSPSC 39" in h


def test_csv_new_columns_and_formula_escaping():
    p = payload([award(title="=HYPERLINK(\"x\")")])
    row = next(csv.DictReader(io.StringIO(render_csv(p))))
    for col in ("score", "band", "fit_reasons", "notice_url", "api_url", "supplier", "buyer_unit", "value_aud", "signed_date"):
        assert col in row
    assert row["title"].startswith("'=") and row["status"] == "awarded_context"
    assert row["notice_url"] == NOTICE and row["band"] == "strong" and row["value_aud"] == "36841.20"
    assert row["signed_date"] == "2026-11-16" and "Marine electrical" in row["fit_reasons"] and "{" not in row["fit_reasons"]
    assert row["supplier"] == "ELECTROTECH AUSTRALIA PTY LTD" and row["buyer_unit"].startswith("NSSG")


def test_md_inline_minimal():
    assert md_inline("a.b-c (1)! #x") == "a.b-c (1)! #x"
    assert md_inline("x|y *z* `c` [l]") == "x\\|y \\*z\\* \\`c\\` \\[l\\]"
