#!/usr/bin/env python3
"""
Suggest Wikipedia/Wikidata links for clubs in gaapitchfinder_data.csv.

This script is intentionally review-first. It writes candidate links to a CSV
under data/derived/ but does not modify the site or the canonical dataset.

Usage:
    python3 scripts/enrich_club_wikipedia.py --limit 25
    python3 scripts/enrich_club_wikipedia.py --club "Portobello GAA"
    python3 scripts/enrich_club_wikipedia.py --min-confidence 80
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from site_build_utils import DATASET_PATH, ROOT_DIR, row_location_label


OUTPUT_CSV = ROOT_DIR / "data" / "derived" / "club_wikipedia_links.csv"
WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"
USER_AGENT = "gaapitchfinder/1.0 (https://github.com/ryanmcg2203/gaapitchfinder)"
REQUEST_DELAY_S = 0.2
REQUEST_TIMEOUT_S = 20

CLUB_SUFFIX_RE = re.compile(
    r"\b("
    r"gaa|gac|gfc|clg|hurling|hurling club|gaelic football|"
    r"gaelic football club|camogie|ladies football club"
    r")\b",
    re.IGNORECASE,
)


def normalize(value: str) -> str:
    value = value.lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def clean_club_name(club: str) -> str:
    name = club.split(",", 1)[0].strip()
    name = CLUB_SUFFIX_RE.sub(" ", name)
    name = re.sub(r"\s+", " ", name).strip(" -")
    return name or club.strip()


def search_terms(club: str, county: str, country: str) -> list[str]:
    base = club.strip()
    clean = clean_club_name(club)
    terms = [
        base,
        f"{base} GAA",
        f"{base} Gaelic",
        f"{clean} GAA",
        f"{clean} Gaelic",
    ]
    if county:
        terms.extend([f"{base} {county}", f"{clean} {county} GAA"])
    if country and country not in {county, "Ireland"}:
        terms.append(f"{clean} {country} GAA")

    unique_terms = []
    seen = set()
    for term in terms:
        key = normalize(term)
        if key and key not in seen:
            seen.add(key)
            unique_terms.append(term)
    return unique_terms


def wikidata_request(params: dict[str, str | int]) -> dict:
    query = urllib.parse.urlencode({"format": "json", **params})
    request = urllib.request.Request(
        f"{WIKIDATA_API_URL}?{query}",
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_S) as response:
        return json.loads(response.read())


def search_wikidata(term: str) -> list[dict]:
    data = wikidata_request(
        {
            "action": "wbsearchentities",
            "language": "en",
            "type": "item",
            "limit": 7,
            "search": term,
        }
    )
    return data.get("search", [])


def get_entities(ids: Iterable[str]) -> dict[str, dict]:
    ids = [item_id for item_id in ids if item_id]
    if not ids:
        return {}
    data = wikidata_request(
        {
            "action": "wbgetentities",
            "ids": "|".join(ids),
            "props": "labels|descriptions|sitelinks|claims",
            "languages": "en",
            "sitefilter": "enwiki",
        }
    )
    return data.get("entities", {})


def enwiki_url(entity: dict) -> str:
    title = entity.get("sitelinks", {}).get("enwiki", {}).get("title", "")
    if not title:
        return ""
    return "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))


def claim_values(entity: dict, property_id: str) -> set[str]:
    values = set()
    for claim in entity.get("claims", {}).get(property_id, []):
        datavalue = (
            claim.get("mainsnak", {})
            .get("datavalue", {})
            .get("value")
        )
        if isinstance(datavalue, dict) and "id" in datavalue:
            values.add(datavalue["id"])
    return values


def score_candidate(row: dict[str, str], candidate: dict, entity: dict, term: str) -> tuple[int, list[str]]:
    club = row["Club"].strip()
    county = row["County"].strip()
    country = row["Country"].strip()
    division = row["Division"].strip()
    label = candidate.get("label", "")
    description = candidate.get("description", "")

    club_norm = normalize(club)
    clean_norm = normalize(clean_club_name(club))
    label_norm = normalize(label)
    description_norm = normalize(description)
    term_norm = normalize(term)
    haystack = normalize(f"{label} {description}")
    reasons = []
    score = 0

    if label_norm == club_norm:
        score += 45
        reasons.append("label_exact")
    elif label_norm == clean_norm:
        score += 40
        reasons.append("clean_label_exact")
    elif clean_norm and clean_norm in label_norm:
        score += 30
        reasons.append("clean_name_in_label")
    elif label_norm and label_norm in club_norm:
        score += 25
        reasons.append("label_in_club")

    club_tokens = set(club_norm.split())
    label_tokens = set(label_norm.split())
    token_overlap = len(club_tokens & label_tokens)
    if token_overlap >= 2:
        score += min(token_overlap * 5, 20)
        reasons.append(f"token_overlap_{token_overlap}")

    if "gaa" in haystack or "gaelic" in haystack:
        score += 20
        reasons.append("gaa_context")
    if "sports club" in description_norm or "club" in description_norm:
        score += 8
        reasons.append("club_context")
    if county and normalize(county) in haystack:
        score += 12
        reasons.append("county_context")
    if division and normalize(division) in haystack:
        score += 8
        reasons.append("division_context")
    if country and normalize(country) in haystack:
        score += 6
        reasons.append("country_context")
    if enwiki_url(entity):
        score += 12
        reasons.append("enwiki_sitelink")

    sports = claim_values(entity, "P641")
    instances = claim_values(entity, "P31")
    if sports:
        score += 5
        reasons.append("sport_claim")
    if instances:
        score += 4
        reasons.append("instance_claim")

    if term_norm == label_norm:
        score += 3
        reasons.append("query_label_exact")

    has_sport_context = any(
        reason in reasons
        for reason in {"gaa_context", "sport_claim", "club_context"}
    )
    if not has_sport_context:
        score = min(score, 65)
        reasons.append("capped_no_sport_context")

    return min(score, 100), reasons


def load_clubs() -> list[dict[str, str]]:
    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    with DATASET_PATH.open(newline="") as csvfile:
        for row in csv.DictReader(csvfile):
            key = (row["Club"].strip(), row["Country"].strip(), row_location_label(row))
            grouped[key].append(row)

    clubs = []
    for (_club, _country, _location), rows in sorted(grouped.items()):
        first = rows[0].copy()
        first["Pitch Count"] = str(len(rows))
        clubs.append(first)
    return clubs


def best_candidate(row: dict[str, str]) -> dict[str, str]:
    seen_ids = set()
    candidates = []
    source_terms = {}
    for term in search_terms(row["Club"], row["County"], row["Country"]):
        try:
            time.sleep(REQUEST_DELAY_S)
            results = search_wikidata(term)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            return {
                "match_status": "api_error",
                "notes": str(error),
            }
        for candidate in results:
            item_id = candidate.get("id", "")
            if not item_id or item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            source_terms[item_id] = term
            candidates.append(candidate)

    entities = get_entities([candidate.get("id", "") for candidate in candidates])
    best = None
    for candidate in candidates:
        item_id = candidate.get("id", "")
        entity = entities.get(item_id, {})
        confidence, reasons = score_candidate(row, candidate, entity, source_terms[item_id])
        result = {
            "candidate_label": candidate.get("label", ""),
            "wikidata_id": item_id,
            "wikipedia_url": enwiki_url(entity),
            "match_confidence": str(confidence),
            "source_query": source_terms[item_id],
            "candidate_description": candidate.get("description", ""),
            "notes": ";".join(reasons),
        }
        if best is None or confidence > int(best["match_confidence"]):
            best = result

    if not best:
        return {
            "candidate_label": "",
            "wikidata_id": "",
            "wikipedia_url": "",
            "match_confidence": "0",
            "source_query": "",
            "candidate_description": "",
            "match_status": "no_match",
            "notes": "no_candidates",
        }
    return best


def write_results(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "Club",
        "County",
        "Country",
        "Division",
        "Pitch Count",
        "candidate_label",
        "wikidata_id",
        "wikipedia_url",
        "match_confidence",
        "match_status",
        "source_query",
        "candidate_description",
        "notes",
    ]
    with output_path.open("w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--club", help="Only process clubs containing this text")
    parser.add_argument("--limit", type=int, help="Limit number of grouped clubs to process")
    parser.add_argument("--min-confidence", type=int, default=75)
    parser.add_argument("--output", type=Path, default=OUTPUT_CSV)
    args = parser.parse_args()

    clubs = load_clubs()
    if args.club:
        club_filter = normalize(args.club)
        clubs = [row for row in clubs if club_filter in normalize(row["Club"])]
    if args.limit:
        clubs = clubs[: args.limit]

    results = []
    for index, row in enumerate(clubs, 1):
        print(f"[{index}/{len(clubs)}] {row['Club']} ({row['County'] or row['Country']})")
        result = best_candidate(row)
        confidence = int(result.get("match_confidence") or 0)
        if result.get("match_status") == "api_error":
            status = "api_error"
        elif confidence >= args.min_confidence and result.get("wikipedia_url"):
            status = "suggested"
        elif confidence:
            status = "needs_review"
        else:
            status = "no_match"

        merged = {
            "Club": row["Club"].strip(),
            "County": row["County"].strip(),
            "Country": row["Country"].strip(),
            "Division": row["Division"].strip(),
            "Pitch Count": row["Pitch Count"],
            **result,
            "match_status": status,
        }
        results.append(merged)
        print(
            f"  {status}: {merged.get('candidate_label', '')} "
            f"{merged.get('wikidata_id', '')} ({confidence})"
        )

    write_results(results, args.output)
    print(f"\nWrote {len(results)} rows to {args.output}")


if __name__ == "__main__":
    main()
