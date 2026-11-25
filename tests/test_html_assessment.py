from defence_radar.render.assessment import render_assessment_html, render_assessment_md
from defence_radar.render.html_list import render_html


def row(title='Marine opportunity', status='confirmed_open', lifecycle='open', shortlist=True, score=75, kind='procurement'):
    return {'record': {'id': title, 'title': title, 'summary': 'Hydraulic repair scope', 'record_kind': kind,
        'status_class': status, 'lifecycle': lifecycle, 'classification_reason': 'Official notice',
        'procurement_stage': 'open', 'freshness_state': 'fresh', 'verified_at': '2026-11-24T00:00:00Z',
        'capabilities': [{'id': 'hydraulics'}], 'locations': [], 'eligibility': [], 'close_precision': 'instant', 'close_at_utc': '2026-12-01T00:00:00Z', 'close_raw': '1 Dec 2026',
        'application_route': {'purpose':'submit','url':'https://example.org/apply','email':None,'instructions':'Use portal','account_required':'yes'},
        'conditions': ['Safety plan'], 'sources': [{'source_id':'notice','url':'https://example.org/notice','accessed_at':'2026-11-24T00:00:00Z','pointer':'/x','snapshot_sha256':'abc','licence_url':'https://creativecommons.org/licenses/by/4.0/'}]},
        'match': {'score':score,'shortlist':shortlist,'components':{'capability':30},'matched_capabilities':['hydraulics'],
                  'missing_capabilities':['security clearance'],'evidence':['scope text'],'exclusions':[], 'eligibility':{'status':'incomplete','limitation':'Clearance unknown'}}}


def payload(rows): return {'period':'2026-W48','as_of':'2026-11-24T00:00:00Z','rows':rows,
    'coverage':{'confirmed_open':sum(x['record']['status_class']=='confirmed_open' for x in rows),'held':{'total':2},'context_records':1},
    'profile':{'name':'Public profile','credentials':{'secret':'PRIVATE_SENTINEL'}},'attribution':['Notice CC BY 4.0']}


def test_html_fields_escape_and_offline_controls():
    text=render_html(payload([row('<img src=x onerror=alert(1)> </script>')]))
    for term in ('Official notice','Lifecycle:','fresh','hydraulics','Geography:','Eligibility:','Safety plan','AWST','account required','licence','Search','Clear filters','aria-live','Fit 75/100 (strong)','Class','Minimum score','Agency / buyer unit','Capability / category'):
        assert term in text
    assert '&lt;img' in text and '&lt;/script&gt;' in text
    assert '<img src=x' not in text and '<script src=' not in text and 'PRIVATE_SENTINEL' not in text
    assert 'No confirmed-open opportunities' not in text
    assert 'No route published' not in text
    assert 'https://example.org/apply' in text


def test_html_default_shows_all_rows_with_unmistakable_awarded_badge_and_safe_url():
    text=render_html(payload([row(),row('Awarded','awarded_context','awarded',False,0,'contract_context'),row('Hypothesis','speculative','planned',False,40)]))
    assert text.count('<article class="card')==3
    assert 'AWARDED \u2014 not an opportunity' in text and 'data-cls="confirmed_open"' in text
    assert '<noscript>' in text and 'id="controls"' in text and 'hidden' in text
    # Unsafe links are rendered as text, never as navigable hrefs.
    bad=row('bad'); bad['record']['application_route']['url']='javascript:alert(1)'
    assert 'href="javascript:' not in render_html(payload([bad]))


def test_assessment_caps_shortlist_and_handles_zero_match():
    p=payload([row(f'R{i}', score=i) for i in range(5)])
    md=render_assessment_md(p)
    assert md.count('## R') == 3 and 'R4' in md and 'R1' not in md
    assert 'Safety plan' in md and 'Next action' in md and 'licence' in md
    html=render_assessment_html(p)
    assert html.count('<article>') == 3 and '@page{size:A4' in html
    empty=payload([row('context',None,'awarded',False,0,'contract_context')])
    assert 'No verified shortlist matches' in render_assessment_md(empty)
    assert 'does not establish that no opportunity exists' in render_assessment_html(empty)
    future = payload([row('Future preparation', 'published_future_scope', 'planned')])
    assert 'Future preparation' in render_assessment_md(future)
