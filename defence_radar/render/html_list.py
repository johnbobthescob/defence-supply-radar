"""Self-contained, searchable and filterable offline work-package page (vanilla JS, no external assets)."""
import html

from .common import (CLASS_BADGE_TEXT, CLASS_LABELS, all_reasons, api_url, awst_date, awst_stamp, band_for, buyer_unit,
                     capability_label, clean_reason, class_of, closing_label, eligibility_label, fit_label, money, notice_ref,
                     notice_url, record_amount, safe_url, signed_stamp, source_summaries, supplier_text, top_reasons,
                     unspsc_families, awst_iso_date)


def _e(v): return html.escape(str(v if v is not None else ""), quote=True).replace("&#x27;", "&apos;")


def _link(label, url, cls=""):
    safe = safe_url(url)
    c = f' class="{cls}"' if cls else ""
    return f'<a{c} href="{_e(safe)}">{_e(label)}</a>' if safe else _e(label)


ORDER = ["confirmed_open", "published_future_scope", "speculative", "awarded_context", "context_only", "inactive", "held"]
BADGE_CLASS = {"confirmed_open": "c-open", "published_future_scope": "c-future", "speculative": "c-spec", "awarded_context": "c-award",
               "context_only": "c-ctx", "inactive": "c-inactive", "held": "c-held"}

CSS = """
:root{--navy:#102b46;--teal:#087e83;--ink:#1b2b38;--muted:#4a5c69;--line:#d3dde2;--paper:#f3f7f8}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
header{background:var(--navy);color:#fff;border-bottom:5px solid var(--teal);padding:22px max(16px,calc((100% - 1100px)/2))}
header h1{margin:0 0 4px;font-size:1.6rem}header p{margin:2px 0;color:#d6e4ee}header a{color:#bfe9ea}
main{max-width:1100px;margin:auto;padding:12px 16px 40px}
h2{font-size:1.15rem;line-height:1.3;margin:0 0 6px;color:var(--navy)}
.panel{background:#fff;border:1px solid var(--line);border-radius:8px;padding:12px 16px;margin:12px 0}
.panel.note{border-left:6px solid #5b3a8c}
.stats{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}.stat{border-radius:6px;padding:4px 10px;font-size:.9rem}
.controls{display:flex;flex-wrap:wrap;gap:12px;align-items:end}
label{display:grid;gap:3px;font-weight:600;font-size:.88rem;color:var(--navy)}
input,select,button{font:inherit;padding:6px 8px;border:1px solid #627d89;border-radius:5px;background:#fff;color:var(--ink);max-width:260px}
input[type=range]{padding:0}
button{background:var(--teal);color:#fff;border-color:var(--teal);cursor:pointer;font-weight:600}
#count{font-weight:700;color:var(--navy);align-self:center}
:focus-visible{outline:3px solid #f2ac42;outline-offset:2px}
.card{background:#fff;border:1px solid var(--line);border-left:7px solid #999;border-radius:8px;padding:12px 16px;margin:10px 0}
.card[hidden]{display:none}
.card.c-open{border-left-color:#1e7d4a}.card.c-future{border-left-color:#2a64a8}.card.c-spec{border-left-color:#b36b00}
.card.c-award{border-left-color:#5b3a8c}.card.c-ctx{border-left-color:#6b7b86}.card.c-inactive{border-left-color:#8a8f94}.card.c-held{border-left-color:#a33}
.card h2{font-size:1.05rem}
.badge{display:inline-block;border-radius:999px;padding:1px 10px;font-size:.8rem;font-weight:700;border:1px solid transparent;margin:0 4px 2px 0}
.b-c-open{background:#e0f3e8;color:#0d5a31;border-color:#9fd3b3}.b-c-future{background:#e3edf9;color:#1b4a85;border-color:#a6c1e4}
.b-c-spec{background:#fdf0d8;color:#8a5200;border-color:#e6c88f}.b-c-award{background:#5b3a8c;color:#fff}
.b-c-ctx{background:#e6ebee;color:#33434e;border-color:#b5c1c8}.b-c-inactive{background:#eceeef;color:#444}.b-c-held{background:#f8e0e0;color:#7a1c1c;border-color:#e2a9a9}
.b-fit{background:#e6f4f4;color:#05575b;border-color:#8bcac9}
.meta{color:var(--muted);font-size:.92rem;margin:3px 0}.meta strong{color:var(--ink)}
.reasons{margin:6px 0;padding-left:20px}
details{margin-top:6px}summary{cursor:pointer;color:#06607a;font-weight:600;font-size:.92rem}
.small{font-size:.82rem}a{color:#06607a}
@media print{header{-webkit-print-color-adjust:exact;print-color-adjust:exact}.controls{display:none}.card{break-inside:avoid}}
"""

JS = r"""(()=>{
const cards=[...document.querySelectorAll('.card')],list=document.getElementById('results');
const ids=['q','cls','minscore','agency','cat','sort'],el=Object.fromEntries(ids.map(i=>[i,document.getElementById(i)]));
document.getElementById('controls').hidden=false;
function update(){
 const q=el.q.value.trim().toLowerCase(),min=Number(el.minscore.value||0);let shown=0;const per={};
 cards.forEach(c=>{const d=c.dataset;
  const ok=(!q||d.search.includes(q))&&(!el.cls.value||d.cls===el.cls.value)&&Number(d.score)>=min&&(!el.agency.value||d.agency===el.agency.value)&&(!el.cat.value||d.cats.split('|').includes(el.cat.value));
  c.hidden=!ok;if(ok){shown++;per[d.cls]=(per[d.cls]||0)+1}});
 const s=el.sort.value;
 const key={score:(a,b)=>Number(b.dataset.score)-Number(a.dataset.score)||a.dataset.title.localeCompare(b.dataset.title),
  value:(a,b)=>Number(b.dataset.value)-Number(a.dataset.value)||Number(b.dataset.score)-Number(a.dataset.score),
  date:(a,b)=>b.dataset.date.localeCompare(a.dataset.date)||Number(b.dataset.score)-Number(a.dataset.score),
  title:(a,b)=>a.dataset.title.localeCompare(b.dataset.title)}[s];
 [...cards].sort(key).forEach(c=>list.append(c));
 document.getElementById('count').textContent=shown+' of '+cards.length+' records shown'+(Object.keys(per).length?' ('+Object.entries(per).map(([k,v])=>v+' '+(window.LABELS[k]||k)).join(', ')+')':'');
 document.getElementById('none').hidden=shown>0||!cards.length;
}
ids.forEach(i=>el[i].addEventListener('input',update));
el.minscore.addEventListener('input',()=>{});
document.getElementById('clear').addEventListener('click',()=>{ids.forEach(i=>el[i].value=(i==='sort'?'score':i==='minscore'?'0':''));update()});
update();})();"""


def _opts(values, selected=""):
    return "".join(f'<option value="{_e(v)}">{_e(l)}</option>' for v, l in values)


def render_html(payload):
    rows = payload.get("rows", [])
    cov = payload.get("coverage", {})
    cards, agencies, cats, counts = [], set(), set(), {}
    for row in rows:
        r, m = row["record"], row["match"]
        cls = class_of(r)
        counts[cls] = counts.get(cls, 0) + 1
        unit = buyer_unit(r)
        agencies.add(unit)
        cap_labels = [capability_label(c, payload) for c in m.get("matched_capabilities", [])]
        fams = unspsc_families(r)
        cats.update(cap_labels + fams)
        score = int(m.get("score") or 0)
        amount = record_amount(r)
        elig = m.get("eligibility", {}) or {}
        places = [p.get("name", "") for p in r.get("locations", []) if p.get("role") in {"worksite", "delivery"}]
        route = r.get("application_route") or {}
        ref = notice_ref(r)
        reasons = all_reasons(m)
        topr = top_reasons(m, 3)
        date_key = (r.get("close_at_utc") if cls == "confirmed_open" and r.get("close_at_utc") else signed_stamp(r)) or ""
        date_key = awst_iso_date(date_key) or ""
        searchable = " ".join([r.get("title", ""), r.get("summary", ""), unit, r.get("buyer", ""), supplier_text(r), ref, " ".join(cap_labels), " ".join(fams),
                               CLASS_LABELS.get(cls, ""), " ".join(reasons)]).lower()
        top_li = "".join(f"<li>{_e(clean_reason(x))}</li>" for x in topr) or "<li>No scoring reasons recorded.</li>"
        rest = reasons[len(topr):] if topr and topr == reasons[:len(topr)] else [x for x in reasons if x not in topr]
        more = (f'<details><summary>All {len(reasons)} scoring reasons</summary><ul class="reasons">' + "".join(f"<li>{_e(x)}</li>" for x in reasons) + "</ul></details>") if len(reasons) > len(topr) else ""
        api = api_url(r)
        id_html = (_link(ref, notice_url(r)) if ref else "") + (f' <a class="small" href="{_e(api)}">API record</a>' if api else "")
        if route.get("url") or route.get("email"):
            dest = route.get("url") or ("mailto:" + route["email"])
            route_html = f'<p class="meta"><strong>Official route:</strong> {_e(route.get("purpose", "unknown"))}; {_link(route.get("url") or route.get("email"), dest)}; account required: {_e(route.get("account_required", "unknown"))}; {_e(route.get("instructions") or "no instructions published")}</p>'
        else:
            route_html = ""
        srcs = "; ".join(_link(s.get("source_id") or "Source", s.get("url")) + " accessed " + _e(s.get("accessed_at") or "unknown") + ("; " + _link("licence", s["licence_url"]) if s.get("licence_url") else "") for s in source_summaries(r)) or "None recorded"
        close = f'<p class="meta"><strong>Close:</strong> {_e(closing_label(r))} (original: {_e(r.get("close_raw") or "not published")})</p>' if cls == "confirmed_open" or r.get("close_at_utc") else ""
        value = money(amount) if amount is not None else "n/a"
        supplier = f'<p class="meta"><strong>Supplier:</strong> {_e(supplier_text(r))}</p>' if r.get("prime") or (r.get("evidence_flags") or {}).get("suppliers") else ""
        cards.append(
            f'<article class="card {BADGE_CLASS.get(cls, "c-ctx")}" data-cls="{_e(cls)}" data-score="{score}" data-agency="{_e(unit)}" data-cats="{_e("|".join(cap_labels + fams))}" '
            f'data-value="{amount or 0}" data-date="{_e(date_key)}" data-title="{_e(r.get("title", ""))}" data-search="{_e(searchable)}">'
            f'<h2>{_e(r.get("title", "Untitled"))}</h2>'
            f'<p><span class="badge b-{BADGE_CLASS.get(cls, "c-ctx")}">{_e(CLASS_BADGE_TEXT.get(cls, cls))}</span><span class="badge b-fit">{_e(fit_label(m))}</span></p>'
            f'<ul class="reasons">{top_li}</ul>{more}'
            f'<p class="meta"><strong>Buyer unit:</strong> {_e(unit)}'
            + (f' ({_e(r.get("buyer"))})' if r.get("buyer") and r.get("buyer") != unit else "") + f' &middot; <strong>Value:</strong> {_e(value)}'
            f' &middot; <strong>Notice:</strong> {id_html}</p>{supplier}'
            f'<p class="meta"><strong>Signed/published:</strong> {_e(awst_date(signed_stamp(r)))}'
            + (f' &middot; <strong>Contract period:</strong> {_e(awst_date((r.get("contract_period") or {}).get("startDate")))} to {_e(awst_date((r.get("contract_period") or {}).get("endDate")))}' if (r.get("contract_period") or {}).get("startDate") else "")
            + f'</p>{close}<p class="meta"><strong>Why this class:</strong> {_e(r.get("classification_reason") or "Not recorded")}</p>{route_html}'
            f'<details><summary>More detail and sources</summary><p class="meta"><strong>Lifecycle:</strong> {_e(r.get("lifecycle", "unknown"))}; freshness {_e(r.get("freshness_state", "unknown"))}; verified {_e(r.get("verified_at") or "not published")}. '
            f'<strong>Stage:</strong> {_e(r.get("procurement_stage", "unknown"))}. <strong>Geography:</strong> {_e("; ".join(places) or "not published")}.</p>'
            f'<p class="meta"><strong>Eligibility:</strong> {_e(eligibility_label(m))}. Constraints: {_e("; ".join(m.get("exclusions") or []) or "None recorded")}. Missing capabilities: {_e("; ".join(m.get("missing_capabilities") or []) or "none")}.</p>'
            f'<p class="meta"><strong>Conditions:</strong> {_e("; ".join(r.get("conditions") or []) or "None recorded")}</p>'
            f'<p class="meta"><strong>Summary:</strong> {_e(r.get("summary", ""))}</p><p class="meta"><strong>Sources:</strong> {srcs}</p>'
            f'<p class="meta"><strong>Attribution:</strong> {_e("; ".join(r.get("attribution") or []) or "None recorded")}</p></details></article>')
    stats = "".join(f'<span class="stat badge b-{BADGE_CLASS[c]}">{counts[c]} {_e(CLASS_LABELS[c])}</span>' for c in ORDER if counts.get(c))
    open_count = counts.get("confirmed_open", 0)
    banner = ("" if open_count else '<div class="panel note"><strong>No verified open tenders are in this build.</strong> Everything marked AWARDED is a contract that has already been won; it is context and teaming intelligence, not work you can bid for.</div>')
    class_opts = [(c, CLASS_LABELS[c]) for c in ORDER]
    cat_opts = [(c, c) for c in sorted(cats)]
    agency_opts = [(a, a) for a in sorted(agencies)]
    labels_js = "window.LABELS={" + ",".join(f'"{k}":"{v}"' for k, v in CLASS_LABELS.items()) + "};"
    data = "\n".join(cards) or '<p id="empty">No records in this build.</p>'
    profile = (payload.get("profile") or {}).get("name") or "Your business"
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Defence supply radar — work packages — {_e(payload.get("period", ""))}</title><style>{CSS}</style></head><body>
<header><h1>Defence Supply Radar — work packages</h1><p>{_e(profile)} &middot; Period {_e(payload.get("period", "not specified"))} &middot; Data as of {_e(awst_stamp(payload.get("as_of")))}</p></header><main>
<section class="panel" aria-label="Coverage summary"><h2>What is in this list</h2><p>{len(rows)} records. {open_count} verified open. {_e(cov.get("summary") or "")}</p><div class="stats">{stats}</div>
<p class="meta small">Scores explain relevance to your declared capabilities; they are not eligibility or approval. Awarded contracts are never open opportunities.</p></section>{banner}
<noscript><div class="panel"><p>JavaScript is off; all records are shown below. Search and filters need JavaScript.</p></div></noscript>
<section id="controls" class="panel controls" aria-label="Search and filters" hidden>
<label>Search<input id="q" type="search" aria-label="Search records"></label>
<label>Class<select id="cls"><option value="">All classes</option>{_opts(class_opts)}</select></label>
<label>Minimum score<select id="minscore"><option value="0">Any (0+)</option><option value="25">Possible (25+)</option><option value="45">Good (45+)</option><option value="70">Strong (70+)</option></select></label>
<label>Agency / buyer unit<select id="agency"><option value="">All buyer units</option>{_opts(agency_opts)}</select></label>
<label>Capability / category<select id="cat"><option value="">All categories</option>{_opts(cat_opts)}</select></label>
<label>Sort by<select id="sort"><option value="score">Fit score</option><option value="date">Date (newest)</option><option value="value">Value</option><option value="title">Title</option></select></label>
<button id="clear" type="button">Clear filters</button><span id="count" aria-live="polite"></span></section>
<p id="none" hidden class="panel">No records match these filters. Use Clear filters.</p>
<section id="results" aria-label="Records">{data}</section></main>
<script>{labels_js}{JS}</script></body></html>'''
