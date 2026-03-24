#!/usr/bin/env python3
"""
Build facet value counts from built JSON records.

Reads data/built/{fundings,travel-grants,resources,funders}.json and
computes facet counts for each entity type.

Output: data/built/facets.json

Usage:
    python build_facets.py
    python build_facets.py --input data/built/ --output data/built/facets.json
"""
import json
import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path: Path) -> List[Dict[str, Any]]:
    """Load a JSON file as a list of dicts."""
    if not path.exists():
        print(f"  Warning: {path} not found, skipping.")
        return []
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def count_scalar(
    records: List[Dict[str, Any]],
    field: str,
    label_field: Optional[str] = None,
    label_index: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """
    Count occurrences of a scalar field across records.

    Returns a sorted list of {value, label, count} dicts,
    descending by count.
    """
    counter: Counter = Counter()
    labels: Dict[str, str] = {}

    for record in records:
        val = record.get(field)
        if val is None or val == '':
            continue
        key = str(val)
        counter[key] += 1
        if label_field and isinstance(record, dict):
            lbl = record.get(label_field) or key
            labels[key] = str(lbl)
        elif label_index and key in label_index:
            labels[key] = label_index[key]
        else:
            labels[key] = key

    return [
        {'value': val, 'label': labels.get(val, val), 'count': cnt}
        for val, cnt in counter.most_common()
    ]


def count_array_field(
    records: List[Dict[str, Any]],
    field: str,
    label_field: Optional[str] = None,
    name_suffix: str = '_names',
) -> List[Dict[str, Any]]:
    """
    Count occurrences of items in an array field across records.

    For array fields like career_levels (slugs), looks for a parallel
    {field}_names array to get display names.

    Returns a sorted list of {value, label, count} dicts.
    """
    counter: Counter = Counter()
    slug_to_name: Dict[str, str] = {}
    names_field = field + name_suffix

    for record in records:
        items = record.get(field) or []
        names = record.get(names_field) or []
        # Build slug→name mapping from this record
        for slug, name in zip(items, names):
            if slug and name:
                slug_to_name[str(slug)] = str(name)
        for item in items:
            if item is not None and item != '':
                counter[str(item)] += 1

    return [
        {'value': val, 'label': slug_to_name.get(val, val), 'count': cnt}
        for val, cnt in counter.most_common()
    ]


def count_funder_facet(
    records: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Count funder occurrences using funders (slugs) + funder_names arrays."""
    return count_array_field(records, 'funders', name_suffix='_names'.replace('funders', 'funder_names'))


def count_bool_facet(
    records: List[Dict[str, Any]],
    field: str,
    true_label: str = 'Yes',
    false_label: str = 'No',
) -> List[Dict[str, Any]]:
    """Count a boolean or presence facet (has value vs does not)."""
    true_count = sum(1 for r in records if r.get(field))
    false_count = len(records) - true_count
    result = []
    if true_count:
        result.append({'value': 'true', 'label': true_label, 'count': true_count})
    if false_count:
        result.append({'value': 'false', 'label': false_label, 'count': false_count})
    return result


def count_presence_facet(
    records: List[Dict[str, Any]],
    field: str,
    has_label: str = 'Has value',
    missing_label: str = 'No value',
) -> List[Dict[str, Any]]:
    """Count a facet based on whether a field has a non-null/non-empty value."""
    has_count = sum(1 for r in records if r.get(field))
    missing_count = len(records) - has_count
    result = []
    if has_count:
        result.append({'value': 'yes', 'label': has_label, 'count': has_count})
    if missing_count:
        result.append({'value': 'no', 'label': missing_label, 'count': missing_count})
    return result


# ---------------------------------------------------------------------------
# Per-entity facet builders
# ---------------------------------------------------------------------------

def build_funding_facets(records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Compute all facets for fundings."""
    # For funder facet: zip funders (slugs) with funder_names
    funder_counter: Counter = Counter()
    funder_slug_to_name: Dict[str, str] = {}
    for r in records:
        slugs = r.get('funders') or []
        names = r.get('funder_names') or []
        for slug, name in zip(slugs, names):
            funder_slug_to_name[str(slug)] = str(name)
        for slug in slugs:
            if slug:
                funder_counter[str(slug)] += 1
    funder_facet = [
        {'value': v, 'label': funder_slug_to_name.get(v, v), 'count': c}
        for v, c in funder_counter.most_common()
    ]

    return {
        'funder': funder_facet,
        'applicant_country': count_scalar(records, 'applicant_country'),
        'host_country': count_scalar(records, 'host_country'),
        'career_levels': count_array_field(records, 'career_levels'),
        'subjects': count_array_field(records, 'subjects'),
        'funding_purposes': count_array_field(records, 'funding_purposes'),
        'deadline_month': count_scalar(records, 'deadline_month'),
        'frequency': count_scalar(records, 'frequency'),
        'status': count_scalar(records, 'status'),
        'featured': count_bool_facet(records, 'featured', 'Featured', 'Not Featured'),
        'diversity': count_presence_facet(records, 'diversity', 'Has Diversity Info', 'No Diversity Info'),
    }


def build_travel_grant_facets(records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Compute all facets for travel grants."""
    funder_counter: Counter = Counter()
    funder_slug_to_name: Dict[str, str] = {}
    for r in records:
        slugs = r.get('funders') or []
        names = r.get('funder_names') or []
        for slug, name in zip(slugs, names):
            funder_slug_to_name[str(slug)] = str(name)
        for slug in slugs:
            if slug:
                funder_counter[str(slug)] += 1
    funder_facet = [
        {'value': v, 'label': funder_slug_to_name.get(v, v), 'count': c}
        for v, c in funder_counter.most_common()
    ]

    return {
        'funder': funder_facet,
        'applicant_country': count_scalar(records, 'applicant_country'),
        'career_levels': count_array_field(records, 'career_levels'),
        'subjects': count_array_field(records, 'subjects'),
        'travel_purposes': count_array_field(records, 'travel_purposes'),
        'membership': count_presence_facet(records, 'membership', 'Membership Required', 'No Membership'),
        'deadline_month': count_scalar(records, 'deadline_month'),
        'status': count_scalar(records, 'status'),
    }


def build_resource_facets(records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Compute all facets for resources."""
    return {
        'resource_categories': count_array_field(records, 'resource_categories'),
        'subjects': count_array_field(records, 'subjects'),
        'featured': count_bool_facet(records, 'featured', 'Featured', 'Not Featured'),
        'status': count_scalar(records, 'status'),
    }


def build_funder_facets(records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Compute all facets for funders."""
    return {
        'country': count_scalar(records, 'country'),
        'featured': count_bool_facet(records, 'featured', 'Featured', 'Not Featured'),
        'status': count_scalar(records, 'status'),
        'dora': count_bool_facet(records, 'dora', 'DORA Signatory', 'Not DORA'),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Build facet value counts from built JSON records.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        '--input', default='data/built/',
        help='Directory containing built JSON files (default: data/built/)',
    )
    parser.add_argument(
        '--output', default='data/built/facets.json',
        help='Output path for facets JSON (default: data/built/facets.json)',
    )
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_path = Path(args.output)

    print("Loading built JSON files …")
    fundings = load_json(input_dir / 'fundings.json')
    travel_grants = load_json(input_dir / 'travel-grants.json')
    resources = load_json(input_dir / 'resources.json')
    funders = load_json(input_dir / 'funders.json')

    print(f"  fundings:      {len(fundings)}")
    print(f"  travel-grants: {len(travel_grants)}")
    print(f"  resources:     {len(resources)}")
    print(f"  funders:       {len(funders)}")

    print("\nComputing facets …")
    facets = {
        'fundings': build_funding_facets(fundings),
        'travel_grants': build_travel_grant_facets(travel_grants),
        'resources': build_resource_facets(resources),
        'funders': build_funder_facets(funders),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(facets, f, ensure_ascii=False, indent=2)

    print(f"\nFacets written to: {output_path}")

    # Print facet summary
    for entity, facet_dict in facets.items():
        print(f"\n  {entity}:")
        for facet_name, values in facet_dict.items():
            print(f"    {facet_name}: {len(values)} distinct values")


if __name__ == '__main__':
    main()
