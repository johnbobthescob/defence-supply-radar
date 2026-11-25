"""Explainable capability fit, separate from eligibility and source permission."""
from copy import deepcopy
import re
from .evidence import digest
from .eligibility import evaluate
from .models import Opportunity, MatchResult

RULE_VERSION = "match-2"
MARINE_CONTEXT = re.compile(r"\b(marine|maritime|naval|vessels?|ship(?:s|board|building)?|submarines?|frigates?|boats?|hmas|rmp west)\b", re.I)


def normal(text):
    return re.sub(r"[^\w]+", " ", text.casefold()).strip()


def tag_scope(text, taxonomy, evidence_id, *, existing_supplier=False):
    normalized = normal(text)
    if existing_supplier or not MARINE_CONTEXT.search(normalized):
        return []
    tags = []
    for key, category in taxonomy["categories"].items():
        for alias in category["aliases"]:
            pattern = r"\b" + re.escape(normal(alias)) + r"\b"
            spans = list(re.finditer(pattern, normalized))
            valid = [m for m in spans if not re.search(r"\b(no|not|excluding|without)\b[^.]{0,35}$", normalized[max(0, m.start()-40):m.start()])]
            if valid:
                tags.append(dict(id=key, role="core", evidence_id=evidence_id, span=alias,
                                 reason="Controlled phrase in marine scope; not a certification or supplier approval."))
                break
    return tags


def enrich_scope(record, taxonomy):
    result = Opportunity.from_dict(deepcopy(record.to_dict()))
    if not result.capabilities and result.sources:
        result.capabilities = tag_scope(result.summary or result.title, taxonomy, result.sources[0]["evidence_id"],
                                        existing_supplier=bool(result.evidence_flags.get("existing_supplier")))
    if result.capabilities and not result.activities:
        text = normal(result.summary or result.title)
        for activity, pattern in {"repair": r"\b(repair\w*|maintenance|overhaul)\b", "supply": r"\b(supply|supplies|procurement of)\b", "install": r"\b(install\w*)\b", "inspect": r"\b(inspect\w*|survey)\b", "manufacture": r"\b(manufactur\w*|fabrication)\b"}.items():
            if re.search(pattern, text):
                result.activities.append(activity)
    return result


UNSPSC_FAMILIES = {
    "1512": "Lubricants, oils, greases and anti-corrosives", "2410": "Material handling machinery", "2413": "Industrial refrigeration",
    "2511": "Marine transport (watercraft)", "2517": "Transportation components and systems", "2610": "Power sources and motors",
    "2611": "Batteries, generators and power transmission", "2612": "Electrical wire, cable and harness", "2613": "Power generation",
    "2712": "Hydraulic machinery and equipment", "2713": "Pneumatic machinery and equipment", "3010": "Structural components and basic shapes",
    "3019": "Construction and maintenance support equipment", "3115": "Rope, chain, cable and wire", "3117": "Bearings, bushings, wheels and gears",
    "3118": "Gaskets and seals", "3120": "Adhesives and sealants", "3121": "Paints, primers and finishes",
    "3125": "Hydraulic, pneumatic and electric control systems", "3910": "Lamps and light bulbs", "3911": "Lighting fixtures",
    "3912": "Electrical equipment and components", "4010": "Heating, ventilation and air circulation", "4014": "Fluid and gas distribution",
    "4015": "Industrial pumps and compressors", "4016": "Industrial filtering and purification", "4017": "Pipe, piping and pipe fittings",
    "4018": "Tubes, tubing and tube fittings", "4110": "Laboratory and scientific equipment", "4111": "Measuring, observing and testing instruments",
    "7318": "Machining and processing services", "7610": "Decontamination services", "7611": "Cleaning and janitorial services",
    "7612": "Refuse disposal and treatment", "7710": "Environmental management", "7813": "Storage", "7814": "Transport services (port)",
    "7818": "Transportation repair or maintenance services", "8110": "Professional engineering services", "8114": "Manufacturing technologies and quality control",
    "8115": "Inspection services", "251117": "Military watercraft", "251119": "Marine craft systems and subassemblies",
}
# Segments/families that a marine engineering/fabrication SME cannot deliver; a match here is capped.
OFF_PROFILE = {
    "14": "paper and stationery", "42": "medical equipment", "43": "information technology and telecoms", "44": "office equipment",
    "49": "sports and recreation", "50": "food and beverage", "53": "apparel", "55": "publications", "56": "furniture",
    "60": "education materials", "80": "management and business services", "82": "editorial and design services",
    "84": "financial services", "85": "healthcare services", "86": "education and training", "90": "travel, food and lodging",
    "93": "politics and civic affairs", "94": "organisations and clubs", "8111": "computer services", "8112": "data services",
    "8116": "IT service delivery",
}
OFF_WORDS = re.compile(r"\b(software|ict|licen[cs]es?|subscriptions?|recruitment|legal|catering|consult(?:ancy|ing)|financial|medical|"
                       r"health|psycholog\w*|advertising|venue|travel|accommodation|rations|apparel|clothing|furniture|stationery|"
                       r"printing|editorial|fitness|events? management|training services|research services|database|network services)\b", re.I)
DOMAIN_WORDS = re.compile(r"\b(marine|maritime|naval|navy|vessels?|ships?|shipboard|shipbuilding|shipyard|watercraft|boats?|"
                          r"submarines?|frigates?|destroyers?|hmas|hulls?|anchor|test vessel)\b", re.I)
OTHER_PLATFORM = re.compile(r"\b(vehicles?|aircraft|airborne|aviation|helicopters?|army|airfield|tanks?|armoured|land)\b", re.I)
MARINE_BRANCH = re.compile(r"maritime|navy|naval|submarine|fleet|shipbuild|nssg", re.I)
GOODS_WORDS = re.compile(r"\b(equipment|parts|spares?|components?|assemblies|kits?|supplies|stores)\b", re.I)
NEGATED = re.compile(r"\b(no|not|excluding|without|except)\b[^.]{0,35}$")
ACTIVITY_WORDS = {"repair": r"\b(repairs?|repairing|maintenance|maintain|overhaul|servicing|refit|sustainment)\b",
                  "supply": r"\b(supply|supplies|spares?|parts|components?|equipment|assemblies|kits?|procurement of)\b",
                  "install": r"\b(install\w*|integration|fit[- ]out)\b",
                  "inspect": r"\b(inspect\w*|survey|testing)\b", "manufacture": r"\b(manufactur\w*|fabricat\w*)\b"}
CAPS = dict(capability=45, domain=15, activity=15, delivery=15, specificity=10)


def _codes(record):
    out = []
    for c in record.evidence_flags.get("unspsc", []) or []:
        code = str((c or {}).get("id", "")) if isinstance(c, dict) else str(c)
        if re.fullmatch(r"\d{8}", code):
            out.append(code)
    return sorted(set(out))


def _code_label(code):
    return UNSPSC_FAMILIES.get(code[:6]) or UNSPSC_FAMILIES.get(code[:4]) or f"segment {code[:2]}"


def _find(term, text):
    pattern = r"\b" + re.escape(normal(term)) + r"\b"
    return [m for m in re.finditer(pattern, text) if not NEGATED.search(text[max(0, m.start() - 40):m.start()])]


def band(score):
    return "strong" if score >= 70 else "good" if score >= 45 else "possible" if score >= 25 else "low"


def match(record, profile, taxonomy, as_of):
    """match-2: explainable 0-100 fit. Each point has a reason; capability evidence comes from the
    notice text, reviewed scope tags and UNSPSC codes. Geography alone never creates a match."""
    record = enrich_scope(record, taxonomy)
    evidence_ids = {s["evidence_id"] for s in record.sources}
    cats = taxonomy["categories"]
    title = normal(record.title)
    text = normal(" ".join(x for x in (record.title, record.summary) if x))
    flags = record.evidence_flags
    codes = _codes(record)
    existing_supplier = bool(flags.get("existing_supplier"))
    reasons, evidence, exclusions = [], [], []
    comp = dict.fromkeys(CAPS, 0)

    # 1. Capability evidence per taxonomy category (best signal per source type, summed, capped).
    found = {}
    for key, cat in cats.items():
        hits = []
        for tag in record.capabilities:
            if tag.get("id") == key and tag.get("evidence_id") in evidence_ids and tag.get("span"):
                hits.append((35 if tag.get("role") == "core" else 20, f"scope phrase '{tag['span']}'", "scope"))
        if not existing_supplier:
            terms = {a: 35 for a in cat["aliases"]}
            for term, pts in cat.get("keywords", {}).items():
                terms[term] = max(terms.get(term, 0), pts)
            best = None
            for term, pts in terms.items():
                if _find(term, text):
                    where = "title" if _find(term, title) else "description"
                    if best is None or pts > best[0]:
                        best = (pts, f"'{term}' in {where}", "text")
            if best: hits.append(best)
        for code in codes:
            for prefix, pts in cat.get("unspsc", {}).items():
                if code.startswith(prefix):
                    hits.append((pts, f"UNSPSC {code} ({_code_label(code)})", "unspsc"))
        if hits:
            by_kind = {}
            for pts, why, kind in hits:
                if pts > by_kind.get(kind, (0,))[0]: by_kind[kind] = (pts, why)
            if set(by_kind) == {"unspsc"}:
                # Code-only evidence: the agency's category suggests the capability but the notice does not name it.
                pts, why = by_kind["unspsc"]
                by_kind["unspsc"] = (round(pts * 0.7), why + " (category code only; title does not name it)")
            ordered = sorted(by_kind.values(), reverse=True)
            # Strongest signal counts in full; corroborating signals of another kind add half.
            total = ordered[0][0] + sum(p // 2 for p, _ in ordered[1:])
            found[key] = (min(total, CAPS["capability"]), [w for _, w in ordered])
    intersection = sorted(k for k in found if k in profile.capabilities)
    if intersection:
        ranked = sorted(intersection, key=lambda k: -found[k][0])
        top = ranked[0]
        comp["capability"] = min(CAPS["capability"], found[top][0] + 5 * (len(ranked) - 1))
        reasons.append(f"+{found[top][0]} {cats[top]['label']}: " + "; ".join(found[top][1]))
        for k in ranked[1:]:
            reasons.append(f"+5 also {cats[k]['label']}: " + "; ".join(found[k][1]))
        for k in ranked: evidence.append(f"{k}: " + "; ".join(found[k][1]))
    other = sorted(k for k in found if k not in profile.capabilities)

    # 2. Maritime domain signals.
    dom = []
    m = DOMAIN_WORDS.search(record.title + " " + record.summary)
    if m: dom.append((10, f"marine term '{m[0]}' in notice"))
    mc = next((c for c in codes if c.startswith(("2511", "7814"))), None)
    if mc: dom.append((10, f"UNSPSC {mc} ({_code_label(mc)})"))
    branch = " ".join(x for x in (flags.get("buyer_branch", ""), flags.get("buyer_division", "")) if x)
    if branch and MARINE_BRANCH.search(branch): dom.append((10, f"buyer unit {flags.get('buyer_branch') or branch} is maritime"))
    elif "submarine" in record.buyer.casefold(): dom.append((10, f"buyer {record.buyer}"))
    if dom:
        comp["domain"] = min(CAPS["domain"], sum(p for p, _ in dom))
        reasons.append(f"+{comp['domain']} maritime context: " + "; ".join(w for _, w in dom))

    # 3. Activity fit.
    acts = set(record.activities)
    if not acts:
        acts = {a for a, pat in ACTIVITY_WORDS.items() if re.search(pat, text)}
    goods = bool(codes) and all(10 <= int(c[:2]) <= 60 for c in codes)
    overlap = acts & set(profile.activities)
    if (comp["capability"] or comp["domain"]):
        if overlap:
            comp["activity"] = 15
            reasons.append("+15 activity matches your profile: " + ", ".join(sorted(overlap)))
        elif record.activities and profile.activities:
            compatible = set(flags.get("reviewed_compatible_activities", [])) & set(profile.activities)
            if compatible:
                comp["activity"] = 8; reasons.append("+8 reviewer-recorded compatible activity; verify delivery method")
            else:
                exclusions.append("Known activity mismatch; required activity is outside the profile.")
        elif goods and "supply" in profile.activities:
            comp["activity"] = 8; reasons.append("+8 goods purchase (UNSPSC) suits your supply activity")

    # 4. Delivery / location fit. Supplier addresses never count as worksites.
    places = [p for p in record.locations if p.get("role") in {"worksite", "delivery"} and p.get("evidence_id") in evidence_ids]
    service = {normal(s) for s in profile.service_regions}
    if comp["capability"] or comp["domain"]:
        if any(normal(p.get("name", "")) in service for p in places):
            comp["delivery"] = 15
            reasons.append("+15 work/delivery location is in your service area: " + ", ".join(p["name"] for p in places if normal(p.get("name", "")) in service))
        elif (profile.national_supply and "supply" in profile.activities and "supply" in acts
              and (flags.get("offsite_supply") is True or any(p.get("national_supply") is True for p in places))):
            comp["delivery"] = 8; reasons.append("+8 explicit offsite/national supply suits your declared reach")
        elif places and (not flags.get("offsite_supply") or not profile.national_supply):
            exclusions.append("Known worksite is outside declared service regions; delivery ability is not established.")
            reasons.append("+0 worksite " + ", ".join(p.get("name", "?") for p in places) + " is outside your service area")
        elif not places and any(_find(r, text) for r in profile.service_regions):
            comp["delivery"] = 10
            reasons.append("+10 notice text names your service area (" + ", ".join(r for r in profile.service_regions if _find(r, text)) + "); confirm worksite")
        elif not places and goods and profile.national_supply and "supply" in profile.activities:
            comp["delivery"] = 8; reasons.append("+8 goods can be shipped; national supply declared (delivery location not published)")
        else:
            evidence.append("Delivery location not published.")
    sup = flags.get("suppliers") or []
    wa = [s["name"] for s in sup if isinstance(s, dict) and s.get("region") == "WA"]
    if wa: evidence.append("Supplier based in WA (incumbent/teaming lead, not a worksite): " + ", ".join(wa))

    # 5. Specificity.
    if comp["capability"]:
        multi = any(len(normal(t.get("span", "")).split()) >= 2 for t in record.capabilities if t.get("id") in intersection)
        strong = any(found[k][0] >= 30 for k in intersection)
        if flags.get("specific_scope") is True or multi:
            comp["specificity"] = 10; reasons.append("+10 specific scope phrase")
        elif strong:
            comp["specificity"] = 5; reasons.append("+5 capability is named specifically")

    score = sum(comp.values())
    # Gates and caps.
    if not comp["capability"] and comp["domain"]:
        branch_only = all(w.startswith(("buyer unit", "buyer ")) for _, w in dom)
        if branch_only:
            reasons.append("capped at 20: only the buyer unit is maritime; the notice itself names no marine scope or capability")
            score = min(score, 20)
        else:
            if GOODS_WORDS.search(record.title) or goods:
                reasons.append("No specific capability named: generic marine purchase; open the notice to check the scope")
            score = min(score, 35)
    if not comp["capability"] and not comp["domain"]:
        score = 0
        reasons.append("No capability or maritime evidence; geography alone cannot create a match")
    if comp["capability"] and not comp["domain"]:
        plat = OTHER_PLATFORM.search(record.title + " " + record.summary + " " + branch)
        if plat and score > 20:
            reasons.append(f"capped at 20: non-maritime platform ('{plat[0]}')"); score = 20
        elif score > 50:
            reasons.append("capped at 50: no maritime context in the notice (could be land or air work)"); score = 50
    off = next(((c, OFF_PROFILE[c[:4]] if c[:4] in OFF_PROFILE else OFF_PROFILE[c[:2]]) for c in codes if c[:4] in OFF_PROFILE or c[:2] in OFF_PROFILE), None)
    offword = OFF_WORDS.search(record.title)
    if (off or offword) and score > 10 and not (comp["capability"] >= 30 and not offword):
        why = f"UNSPSC {off[0]} is {off[1]}" if off else f"'{offword[0]}' is outside a marine engineering profile"
        reasons.append(f"capped at 10: {why}")
        score = 10
    if set(profile.exclusions) & set(found):
        exclusions.append("Scope intersects an explicit profile exclusion.")
        reasons.append("capped at 10: scope intersects a profile exclusion"); score = min(score, 10)
    if not intersection and other:
        evidence.append("Capabilities outside your profile: " + ", ".join(cats[k]["label"] for k in other))
    eligibility = evaluate(record, profile, as_of)
    if eligibility["status"] == "does_not_meet":
        exclusions.append("A mandatory eligibility requirement is not met.")
        reasons.append("gate: a mandatory eligibility requirement is not met (not shortlisted)")
    elif record.eligibility:
        reasons.append("check: notice lists requirements (" + ", ".join(sorted({r.get('key', '?') for r in record.eligibility})) + "); eligibility " + eligibility["status"].replace("_", " "))
    score = max(0, min(100, score))
    shortlist = (score >= 40 and not exclusions and record.status_class is not None
                 and record.status_class.value in {"confirmed_open", "published_future_scope"}
                 and record.review_state.value == "reviewed" and record.lifecycle.value not in {"closed", "awarded", "cancelled", "superseded"})
    return MatchResult(record.id, profile.id, digest(profile.to_dict()), taxonomy["version"], RULE_VERSION, score,
                       comp, reasons, band(score), intersection, other, sorted(set(evidence)), exclusions, eligibility, shortlist).validate()
