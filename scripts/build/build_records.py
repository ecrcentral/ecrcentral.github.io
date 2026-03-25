#!/usr/bin/env python3
"""
Build denormalized JSON records from YAML entry files.

Reads all YAML from each data/entries/{type}/ directory, resolves
cross-references, applies sorting, and writes consolidated JSON to
data/built/.

Usage:
    python build_records.py
    python build_records.py --entries data/entries/ --output data/built/
"""
import json
import sys
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


# ---------------------------------------------------------------------------
# YAML loading helpers
# ---------------------------------------------------------------------------

def load_yaml_dir(directory: Path) -> List[Dict[str, Any]]:
    """Load all YAML files from a directory, return list of dicts."""
    records = []
    if not directory.exists():
        return records
    for yf in sorted(directory.glob('*.yaml')):
        try:
            with open(yf, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            if data and isinstance(data, dict):
                records.append(data)
        except Exception as e:
            print(f"  Warning: failed to load {yf}: {e}", file=sys.stderr)
    return records


def build_slug_index(records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Build a slug → record dict for fast lookup."""
    return {r['slug']: r for r in records if 'slug' in r}


# ---------------------------------------------------------------------------
# Sorting
# ---------------------------------------------------------------------------

def sort_key(record: Dict[str, Any]) -> Tuple:
    """
    Sort key: featured DESC, active first, updated_at DESC, name ASC.

    Returns a tuple suitable for Python sort (lower = earlier in list).
    """
    featured = 0 if record.get('featured') else 1
    # active before everything else
    status = record.get('status', 'draft')
    status_order = {'active': 0, 'draft': 1, 'expired': 2, 'archived': 3, 'inactive': 2}.get(status, 9)
    # Negate updated_at for descending sort (None sorts last)
    updated_at = record.get('updated_at') or ''
    name = (record.get('name') or '').lower()
    return (featured, status_order, updated_at and f"~{updated_at}" or 'z', name)


def sort_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return records sorted by: featured DESC, active first, updated_at DESC, name ASC."""
    return sorted(records, key=sort_key)


# ---------------------------------------------------------------------------
# Denormalization helpers
# ---------------------------------------------------------------------------

def resolve_slugs_to_names(slugs: List[str], index: Dict[str, Dict[str, Any]]) -> List[str]:
    """Resolve a list of slugs to display names using an index dict."""
    names = []
    for slug in slugs:
        record = index.get(slug)
        if record:
            names.append(record.get('name', slug))
        else:
            names.append(slug)  # fallback to slug itself
    return names


def enrich_funding(
    record: Dict[str, Any],
    funder_index: Dict[str, Dict[str, Any]],
    career_level_index: Dict[str, Dict[str, Any]],
    subject_index: Dict[str, Dict[str, Any]],
    funding_purpose_index: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Add denormalized display fields to a funding record."""
    enriched = dict(record)
    funder_slugs = record.get('funders', []) or []
    enriched['funder_names'] = resolve_slugs_to_names(funder_slugs, funder_index)
    enriched['funder_logos'] = [
        funder_index.get(slug, {}).get('logo') for slug in funder_slugs
    ]
    enriched['career_level_names'] = resolve_slugs_to_names(
        record.get('career_levels', []) or [], career_level_index
    )
    enriched['subject_names'] = resolve_slugs_to_names(
        record.get('subjects', []) or [], subject_index
    )
    enriched['funding_purpose_names'] = resolve_slugs_to_names(
        record.get('funding_purposes', []) or [], funding_purpose_index
    )
    return enriched


def enrich_travel_grant(
    record: Dict[str, Any],
    funder_index: Dict[str, Dict[str, Any]],
    career_level_index: Dict[str, Dict[str, Any]],
    subject_index: Dict[str, Dict[str, Any]],
    travel_purpose_index: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Add denormalized display fields to a travel grant record."""
    enriched = dict(record)
    tg_funder_slugs = record.get('funders', []) or []
    enriched['funder_names'] = resolve_slugs_to_names(tg_funder_slugs, funder_index)
    enriched['funder_logos'] = [
        funder_index.get(slug, {}).get('logo') for slug in tg_funder_slugs
    ]
    enriched['career_level_names'] = resolve_slugs_to_names(
        record.get('career_levels', []) or [], career_level_index
    )
    enriched['subject_names'] = resolve_slugs_to_names(
        record.get('subjects', []) or [], subject_index
    )
    enriched['travel_purpose_names'] = resolve_slugs_to_names(
        record.get('travel_purposes', []) or [], travel_purpose_index
    )
    return enriched


def enrich_resource(
    record: Dict[str, Any],
    funder_index: Dict[str, Dict[str, Any]],
    resource_category_index: Dict[str, Dict[str, Any]],
    subject_index: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Add denormalized display fields to a resource record."""
    enriched = dict(record)
    enriched['funder_names'] = resolve_slugs_to_names(
        record.get('funders', []) or [], funder_index
    )
    enriched['resource_category_names'] = resolve_slugs_to_names(
        record.get('resource_categories', []) or [], resource_category_index
    )
    enriched['subject_names'] = resolve_slugs_to_names(
        record.get('subjects', []) or [], subject_index
    )
    return enriched


# ---------------------------------------------------------------------------
# JSON write helper
# ---------------------------------------------------------------------------

def write_json(path: Path, data: Any) -> None:
    """Write data as pretty-printed JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Build denormalized JSON records from YAML entry files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        '--entries', default='data/entries/',
        help='Root directory of YAML entry files (default: data/entries/)',
    )
    parser.add_argument(
        '--output', default='data/built/',
        help='Output directory for built JSON files (default: data/built/)',
    )
    args = parser.parse_args()

    entries_root = Path(args.entries)
    out_dir = Path(args.output)

    # ------------------------------------------------------------------
    # Load all YAML
    # ------------------------------------------------------------------
    print("Loading YAML entries …")
    funders_raw = load_yaml_dir(entries_root / 'funders')
    fundings_raw = load_yaml_dir(entries_root / 'fundings')
    travel_grants_raw = load_yaml_dir(entries_root / 'travel-grants')
    resources_raw = load_yaml_dir(entries_root / 'resources')

    career_levels_raw = load_yaml_dir(entries_root / 'career-levels')
    subjects_raw = load_yaml_dir(entries_root / 'subjects')
    funding_purposes_raw = load_yaml_dir(entries_root / 'funding-purposes')
    travel_purposes_raw = load_yaml_dir(entries_root / 'travel-purposes')
    resource_categories_raw = load_yaml_dir(entries_root / 'resource-categories')

    print(f"  funders:             {len(funders_raw)}")
    print(f"  fundings:            {len(fundings_raw)}")
    print(f"  travel-grants:       {len(travel_grants_raw)}")
    print(f"  resources:           {len(resources_raw)}")
    print(f"  career-levels:       {len(career_levels_raw)}")
    print(f"  subjects:            {len(subjects_raw)}")
    print(f"  funding-purposes:    {len(funding_purposes_raw)}")
    print(f"  travel-purposes:     {len(travel_purposes_raw)}")
    print(f"  resource-categories: {len(resource_categories_raw)}")

    # ------------------------------------------------------------------
    # Build indexes
    # ------------------------------------------------------------------
    funder_index = build_slug_index(funders_raw)
    career_level_index = build_slug_index(career_levels_raw)
    subject_index = build_slug_index(subjects_raw)
    funding_purpose_index = build_slug_index(funding_purposes_raw)
    travel_purpose_index = build_slug_index(travel_purposes_raw)
    resource_category_index = build_slug_index(resource_categories_raw)

    # ------------------------------------------------------------------
    # Enrich entities
    # ------------------------------------------------------------------
    print("\nEnriching records …")

    fundings_enriched = [
        enrich_funding(r, funder_index, career_level_index, subject_index, funding_purpose_index)
        for r in fundings_raw
    ]

    travel_grants_enriched = [
        enrich_travel_grant(r, funder_index, career_level_index, subject_index, travel_purpose_index)
        for r in travel_grants_raw
    ]

    resources_enriched = [
        enrich_resource(r, funder_index, resource_category_index, subject_index)
        for r in resources_raw
    ]

    # Funders: add counts
    funders_enriched = []
    for funder in funders_raw:
        enriched = dict(funder)
        slug = funder.get('slug', '')
        enriched['active_funding_count'] = sum(
            1 for f in fundings_raw
            if slug in (f.get('funders') or []) and f.get('status') == 'active'
        )
        enriched['active_travel_grant_count'] = sum(
            1 for tg in travel_grants_raw
            if slug in (tg.get('funders') or []) and tg.get('status') == 'active'
        )
        enriched['resource_count'] = sum(
            1 for r in resources_raw if slug in (r.get('funders') or [])
        )
        funders_enriched.append(enriched)

    # ------------------------------------------------------------------
    # Sort
    # ------------------------------------------------------------------
    print("Sorting records …")
    funders_sorted = sort_records(funders_enriched)
    fundings_sorted = sort_records(fundings_enriched)
    travel_grants_sorted = sort_records(travel_grants_enriched)
    resources_sorted = sort_records(resources_enriched)

    # ------------------------------------------------------------------
    # Write entity JSON
    # ------------------------------------------------------------------
    print("\nWriting built JSON files …")

    write_json(out_dir / 'funders.json', funders_sorted)
    print(f"  Written: {out_dir / 'funders.json'} ({len(funders_sorted)} records)")

    write_json(out_dir / 'fundings.json', fundings_sorted)
    print(f"  Written: {out_dir / 'fundings.json'} ({len(fundings_sorted)} records)")

    write_json(out_dir / 'travel-grants.json', travel_grants_sorted)
    print(f"  Written: {out_dir / 'travel-grants.json'} ({len(travel_grants_sorted)} records)")

    write_json(out_dir / 'resources.json', resources_sorted)
    print(f"  Written: {out_dir / 'resources.json'} ({len(resources_sorted)} records)")

    # ------------------------------------------------------------------
    # Vocabularies JSON
    # ------------------------------------------------------------------
    vocabularies = {
        'career_levels': career_levels_raw,
        'subjects': subjects_raw,
        'funding_purposes': funding_purposes_raw,
        'travel_purposes': travel_purposes_raw,
        'resource_categories': resource_categories_raw,
    }
    write_json(out_dir / 'vocabularies.json', vocabularies)
    print(f"  Written: {out_dir / 'vocabularies.json'}")

    print("\nBuild complete.")


if __name__ == '__main__':
    main()
