#!/usr/bin/env python3
"""
Build a flat search index from built JSON records.

Creates a MiniSearch-compatible flat document array with fields:
  id, type, slug, name, description, funder_names, country,
  career_levels, subjects

Output: data/built/search-index.json

Usage:
    python build_search_index.py
    python build_search_index.py --input data/built/ --output data/built/search-index.json
"""
import json
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional


DESCRIPTION_MAX_CHARS = 300


def load_json(path: Path) -> List[Dict[str, Any]]:
    """Load a JSON file as a list of dicts."""
    if not path.exists():
        print(f"  Warning: {path} not found, skipping.")
        return []
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def truncate(text: Optional[str], max_chars: int = DESCRIPTION_MAX_CHARS) -> Optional[str]:
    """Truncate a string to max_chars, appending ellipsis if truncated."""
    if not text:
        return None
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + '…'


def make_funding_doc(record: Dict[str, Any]) -> Dict[str, Any]:
    """Build a search document from a funding record."""
    return {
        'id': record.get('id', ''),
        'type': 'funding',
        'slug': record.get('slug', ''),
        'name': record.get('name', ''),
        'description': truncate(record.get('description')),
        'funder_names': record.get('funder_names') or [],
        'funders': record.get('funders') or [],
        'country': record.get('applicant_country') or record.get('host_country') or '',
        'applicant_country': record.get('applicant_country') or '',
        'host_country': record.get('host_country') or '',
        'career_levels': record.get('career_levels') or [],
        'career_level_names': record.get('career_level_names') or [],
        'subjects': record.get('subjects') or [],
        'subject_names': record.get('subject_names') or [],
        'funding_purposes': record.get('funding_purposes') or [],
        'funding_purpose_names': record.get('funding_purpose_names') or [],
        'status': record.get('status', ''),
        'featured': record.get('featured', False),
        'deadline_month': record.get('deadline_month') or '',
        'search_text': record.get('search_text') or '',
        'url': record.get('url') or '',
        'updated_at': record.get('updated_at') or '',
    }


def make_travel_grant_doc(record: Dict[str, Any]) -> Dict[str, Any]:
    """Build a search document from a travel grant record."""
    return {
        'id': record.get('id', ''),
        'type': 'travel_grant',
        'slug': record.get('slug', ''),
        'name': record.get('name', ''),
        'description': truncate(record.get('description')),
        'funder_names': record.get('funder_names') or [],
        'funders': record.get('funders') or [],
        'country': record.get('applicant_country') or record.get('host_country') or '',
        'applicant_country': record.get('applicant_country') or '',
        'host_country': record.get('host_country') or '',
        'career_levels': record.get('career_levels') or [],
        'career_level_names': record.get('career_level_names') or [],
        'subjects': record.get('subjects') or [],
        'subject_names': record.get('subject_names') or [],
        'travel_purposes': record.get('travel_purposes') or [],
        'travel_purpose_names': record.get('travel_purpose_names') or [],
        'status': record.get('status', ''),
        'featured': record.get('featured', False),
        'deadline_month': record.get('deadline_month') or '',
        'search_text': record.get('search_text') or '',
        'url': record.get('url') or '',
        'updated_at': record.get('updated_at') or '',
    }


def make_resource_doc(record: Dict[str, Any]) -> Dict[str, Any]:
    """Build a search document from a resource record."""
    return {
        'id': record.get('id', ''),
        'type': 'resource',
        'slug': record.get('slug', ''),
        'name': record.get('name', ''),
        'description': truncate(record.get('description')),
        'funder_names': record.get('funder_names') or [],
        'funders': record.get('funders') or [],
        'country': '',
        'applicant_country': '',
        'host_country': '',
        'career_levels': [],
        'career_level_names': [],
        'subjects': record.get('subjects') or [],
        'subject_names': record.get('subject_names') or [],
        'resource_categories': record.get('resource_categories') or [],
        'resource_category_names': record.get('resource_category_names') or [],
        'status': record.get('status', ''),
        'featured': record.get('featured', False),
        'url': record.get('url') or '',
        'updated_at': record.get('updated_at') or '',
    }


def make_funder_doc(record: Dict[str, Any]) -> Dict[str, Any]:
    """Build a search document from a funder record."""
    return {
        'id': record.get('id', ''),
        'type': 'funder',
        'slug': record.get('slug', ''),
        'name': record.get('name', ''),
        'description': truncate(record.get('description')),
        'funder_names': [],
        'funders': [],
        'country': record.get('country') or '',
        'applicant_country': '',
        'host_country': '',
        'career_levels': [],
        'career_level_names': [],
        'subjects': [],
        'subject_names': [],
        'aliases': record.get('aliases') or [],
        'status': record.get('status', ''),
        'featured': record.get('featured', False),
        'website': record.get('website') or '',
        'updated_at': record.get('updated_at') or '',
    }


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Build a flat search index from built JSON records.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        '--input', default='data/built/',
        help='Directory containing built JSON files (default: data/built/)',
    )
    parser.add_argument(
        '--output', default='data/built/search-index.json',
        help='Output path for search index JSON (default: data/built/search-index.json)',
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

    print("\nBuilding search index …")
    documents: List[Dict[str, Any]] = []

    for record in fundings:
        documents.append(make_funding_doc(record))

    for record in travel_grants:
        documents.append(make_travel_grant_doc(record))

    for record in resources:
        documents.append(make_resource_doc(record))

    for record in funders:
        documents.append(make_funder_doc(record))

    print(f"  Total documents: {len(documents)}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(documents, f, ensure_ascii=False, indent=2)

    print(f"\nSearch index written to: {output_path}")
    print(f"  Size: {output_path.stat().st_size / 1024:.1f} KB")


if __name__ == '__main__':
    main()
