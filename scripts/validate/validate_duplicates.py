#!/usr/bin/env python3
"""
Validate uniqueness of slugs, names, and URLs in YAML entry files.

Checks:
  1. Slug uniqueness per entity type (error — exit 1)
  2. Near-duplicate names (case-insensitive) per entity type (warning)
  3. Duplicate URLs within the same entity type (warning)

Exit code: 0 if no slug duplicates, 1 if slug duplicates found.

Usage:
    python validate_duplicates.py
    python validate_duplicates.py --entries data/entries/
"""
import sys
import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml


# Entity types that have their own slug namespace
ENTITY_TYPES = [
    'funders',
    'fundings',
    'travel-grants',
    'resources',
    'career-levels',
    'subjects',
    'funding-purposes',
    'travel-purposes',
    'resource-categories',
]

# Entity types that have URL fields
URL_ENTITY_TYPES = ['fundings', 'travel-grants', 'resources']


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_yaml_file(path: Path) -> Optional[Dict[str, Any]]:
    """Load a YAML file, returning None on failure."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"  Warning: failed to load {path}: {e}", file=sys.stderr)
        return None


def load_entity_dir(directory: Path) -> List[Tuple[Path, Dict[str, Any]]]:
    """Load all YAML files in a directory. Returns list of (path, record)."""
    if not directory.exists():
        return []
    result = []
    for yf in sorted(directory.glob('*.yaml')):
        record = load_yaml_file(yf)
        if record:
            result.append((yf, record))
    return result


# ---------------------------------------------------------------------------
# Duplicate checks
# ---------------------------------------------------------------------------

def check_slug_duplicates(
    entity_type: str,
    records: List[Tuple[Path, Dict[str, Any]]],
) -> int:
    """
    Check for duplicate slug values within an entity type.

    Returns the number of duplicate slugs found.
    """
    seen: Dict[str, List[Path]] = defaultdict(list)
    for path, record in records:
        slug = record.get('slug')
        if slug:
            seen[slug].append(path)

    errors = 0
    for slug, paths in seen.items():
        if len(paths) > 1:
            errors += 1
            print(f"  ERROR: Duplicate slug '{slug}' in {entity_type}/:")
            for p in paths:
                print(f"    - {p.name}")

    return errors


def check_name_near_duplicates(
    entity_type: str,
    records: List[Tuple[Path, Dict[str, Any]]],
) -> int:
    """
    Check for near-duplicate names (case-insensitive) within an entity type.

    Returns the number of near-duplicate name groups found (warning only).
    """
    seen: Dict[str, List[Tuple[Path, str]]] = defaultdict(list)
    for path, record in records:
        name = record.get('name')
        if name:
            key = name.strip().lower()
            seen[key].append((path, name))

    warnings = 0
    for key, entries in seen.items():
        if len(entries) > 1:
            warnings += 1
            print(f"  WARN: Near-duplicate name '{key}' in {entity_type}/:")
            for path, original_name in entries:
                print(f"    - {path.name}: '{original_name}'")

    return warnings


def check_url_duplicates(
    entity_type: str,
    records: List[Tuple[Path, Dict[str, Any]]],
) -> int:
    """
    Check for duplicate URL values within an entity type.

    Returns the number of duplicate URL groups found (warning only).
    """
    seen: Dict[str, List[Path]] = defaultdict(list)
    for path, record in records:
        url = record.get('url')
        if url and isinstance(url, str):
            # Normalize: strip trailing slash, lowercase scheme+host
            normalized = url.strip().rstrip('/')
            seen[normalized].append(path)

    warnings = 0
    for url, paths in seen.items():
        if len(paths) > 1:
            warnings += 1
            print(f"  WARN: Duplicate URL in {entity_type}/:")
            print(f"    URL: {url}")
            for p in paths:
                print(f"    - {p.name}")

    return warnings


def check_id_duplicates(
    entity_type: str,
    records: List[Tuple[Path, Dict[str, Any]]],
) -> int:
    """
    Check for duplicate id values within an entity type.

    Returns the number of duplicate IDs found.
    """
    seen: Dict[str, List[Path]] = defaultdict(list)
    for path, record in records:
        entry_id = record.get('id')
        if entry_id:
            seen[str(entry_id)].append(path)

    errors = 0
    for entry_id, paths in seen.items():
        if len(paths) > 1:
            errors += 1
            print(f"  ERROR: Duplicate id '{entry_id}' in {entity_type}/:")
            for p in paths:
                print(f"    - {p.name}")

    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Validate uniqueness of slugs, names, and URLs in YAML files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        '--entries', default='data/entries/',
        help='Root directory of YAML entry files (default: data/entries/)',
    )
    args = parser.parse_args()

    entries_root = Path(args.entries)

    if not entries_root.exists():
        print(f"Error: entries directory not found: {entries_root}", file=sys.stderr)
        sys.exit(1)

    total_errors = 0
    total_warnings = 0
    total_files = 0

    for entity_type in ENTITY_TYPES:
        entity_dir = entries_root / entity_type
        records = load_entity_dir(entity_dir)
        if not records:
            continue

        total_files += len(records)
        print(f"\nChecking {entity_type}/ ({len(records)} files) …")

        # Slug duplicates (error)
        slug_errors = check_slug_duplicates(entity_type, records)
        total_errors += slug_errors

        # ID duplicates (error)
        id_errors = check_id_duplicates(entity_type, records)
        total_errors += id_errors

        # Name near-duplicates (warning)
        name_warns = check_name_near_duplicates(entity_type, records)
        total_warnings += name_warns

        # URL duplicates for entity types that have URLs (warning)
        if entity_type in URL_ENTITY_TYPES:
            url_warns = check_url_duplicates(entity_type, records)
            total_warnings += url_warns

        if slug_errors == 0 and id_errors == 0 and name_warns == 0:
            if entity_type not in URL_ENTITY_TYPES:
                print(f"  OK")
            elif check_url_duplicates(entity_type, []) == 0:
                print(f"  OK")

    print("\n" + "=" * 50)
    print(f"Duplicate check summary:")
    print(f"  Total files checked: {total_files}")
    print(f"  Errors (slug/id):    {total_errors}")
    print(f"  Warnings (name/url): {total_warnings}")
    print("=" * 50)

    if total_warnings > 0:
        print(f"\nWARN: {total_warnings} near-duplicate warning(s) — manual review recommended.")

    if total_errors > 0:
        print(f"\nFAIL: {total_errors} duplicate slug/id error(s) found.")
        sys.exit(1)
    else:
        print("\nOK: No duplicate slugs or IDs found.")
        sys.exit(0)


if __name__ == '__main__':
    main()
