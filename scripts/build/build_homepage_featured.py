#!/usr/bin/env python3
"""
Build homepage featured and recently-updated data from built JSON records.

Output: data/built/homepage-featured.json

Structure:
  {
    "featured_fundings":      [...],  # up to 6
    "featured_travel_grants": [...],  # up to 6
    "featured_resources":     [...],  # up to 6
    "featured_funders":       [...],  # up to 8
    "recently_updated":       [...]   # up to 10 mixed types
  }

Usage:
    python build_homepage_featured.py
    python build_homepage_featured.py --input data/built/ --output data/built/homepage-featured.json
"""
import json
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional


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


def is_approved_active(record: Dict[str, Any]) -> bool:
    """Return True if the record is approved and active."""
    return (
        record.get('review_status') == 'approved'
        and record.get('status') == 'active'
    )


def is_featured_approved_active(record: Dict[str, Any]) -> bool:
    """Return True if the record is featured, approved, and active."""
    return bool(record.get('featured')) and is_approved_active(record)


def updated_at_key(record: Dict[str, Any]) -> str:
    """Sort key for descending updated_at order (None sorts last)."""
    val = record.get('updated_at') or ''
    # Prefix with '~' so string comparison reversal works
    return val if val else ''


def pick_featured(
    records: List[Dict[str, Any]],
    entity_type: str,
) -> List[Dict[str, Any]]:
    """
    Select featured items: featured=True AND review_status=approved AND status=active.

    Returns the full eligible pool (slimmed); client-side JS randomly picks n to display.
    """
    featured = [r for r in records if is_featured_approved_active(r)]
    return [slim(r, entity_type) for r in featured]


def slim(record: Dict[str, Any], entity_type: str) -> Dict[str, Any]:
    """Return a slimmed-down record suitable for homepage display."""
    base: Dict[str, Any] = {
        'id': record.get('id', ''),
        'type': entity_type,
        '_type': entity_type,
        'slug': record.get('slug', ''),
        'name': record.get('name', ''),
        'description': _truncate(record.get('description'), 200),
        'url': record.get('url') or record.get('website') or '',
        'status': record.get('status', ''),
        'featured': record.get('featured', False),
        'updated_at': record.get('updated_at') or '',
    }

    if entity_type == 'funder':
        base['country'] = record.get('country') or ''
        base['logo'] = record.get('logo') or ''
        base['legacy_logo_path'] = record.get('legacy_logo_path') or ''
        base['dora'] = record.get('dora', False)
        base['short_name'] = record.get('short_name') or ''
        base['website'] = record.get('website') or ''
        base['active_funding_count'] = record.get('active_funding_count', 0)
        base['active_travel_grant_count'] = record.get('active_travel_grant_count', 0)

    elif entity_type == 'funding':
        base['funder_names'] = record.get('funder_names') or []
        base['funder_logos'] = record.get('funder_logos') or []
        base['funders'] = record.get('funders') or []
        base['applicant_country'] = record.get('applicant_country') or ''
        base['host_country'] = record.get('host_country') or ''
        base['career_levels'] = record.get('career_levels') or []
        base['career_level_names'] = record.get('career_level_names') or []
        base['deadline'] = record.get('deadline') or ''
        base['deadline_month'] = record.get('deadline_month') or ''
        base['award'] = record.get('award') or ''
        base['subjects'] = record.get('subjects') or []
        base['funding_purposes'] = record.get('funding_purposes') or []
        base['search_text'] = record.get('search_text') or ''
        base['legacy_funder_name'] = record.get('legacy_funder_name') or ''
        base['frequency'] = record.get('frequency') or ''

    elif entity_type == 'travel_grant':
        base['funder_names'] = record.get('funder_names') or []
        base['funder_logos'] = record.get('funder_logos') or []
        base['funders'] = record.get('funders') or []
        base['applicant_country'] = record.get('applicant_country') or ''
        base['career_levels'] = record.get('career_levels') or []
        base['career_level_names'] = record.get('career_level_names') or []
        base['deadline'] = record.get('deadline') or ''
        base['award'] = record.get('award') or ''

    elif entity_type == 'resource':
        base['funder_names'] = record.get('funder_names') or []
        base['funders'] = record.get('funders') or []
        base['resource_categories'] = record.get('resource_categories') or []
        base['resource_category_names'] = record.get('resource_category_names') or []
        base['subjects'] = record.get('subjects') or []
        base['subject_names'] = record.get('subject_names') or []

    return base


def _truncate(text: Optional[str], max_chars: int) -> Optional[str]:
    """Truncate text to max_chars."""
    if not text:
        return None
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + '…'


def build_recently_updated(
    fundings: List[Dict[str, Any]],
    travel_grants: List[Dict[str, Any]],
    resources: List[Dict[str, Any]],
    funders: List[Dict[str, Any]],
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Build a mixed list of recently updated approved+active records.

    Sorted by updated_at descending, up to `limit` items.
    """
    all_records: List[Dict[str, Any]] = []

    for record in fundings:
        if is_approved_active(record):
            all_records.append(slim(record, 'funding'))

    for record in travel_grants:
        if is_approved_active(record):
            all_records.append(slim(record, 'travel_grant'))

    for record in resources:
        if is_approved_active(record):
            all_records.append(slim(record, 'resource'))

    for record in funders:
        if is_approved_active(record):
            all_records.append(slim(record, 'funder'))

    all_records.sort(key=lambda r: r.get('updated_at') or '', reverse=True)
    return all_records[:limit]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Build homepage featured and recently-updated data.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        '--input', default='data/built/',
        help='Directory containing built JSON files (default: data/built/)',
    )
    parser.add_argument(
        '--output', default='data/built/homepage-featured.json',
        help='Output path (default: data/built/homepage-featured.json)',
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

    print("\nBuilding homepage featured data …")

    homepage = {
        'featured_fundings': pick_featured(fundings, 'funding'),
        'featured_travel_grants': pick_featured(travel_grants, 'travel_grant'),
        'featured_resources': pick_featured(resources, 'resource'),
        'featured_funders': pick_featured(funders, 'funder'),
        'recently_updated': build_recently_updated(fundings, travel_grants, resources, funders, limit=10),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(homepage, f, ensure_ascii=False, indent=2)

    print(f"\nHomepage data written to: {output_path}")
    print(f"  featured_fundings:      {len(homepage['featured_fundings'])}")
    print(f"  featured_travel_grants: {len(homepage['featured_travel_grants'])}")
    print(f"  featured_resources:     {len(homepage['featured_resources'])}")
    print(f"  featured_funders:       {len(homepage['featured_funders'])}")
    print(f"  recently_updated:       {len(homepage['recently_updated'])}")


if __name__ == '__main__':
    main()
