#!/usr/bin/env python3
"""
Validate taxonomy references in entity YAML files.

Checks that all slugs referenced in M2M fields (funders, career_levels,
subjects, etc.) actually exist in the corresponding vocabulary directories.

Exit code: 0 if valid, 1 if any broken references found.

Usage:
    python validate_taxonomies.py
    python validate_taxonomies.py --entries data/entries/
"""
import sys
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml


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


def build_slug_set(directory: Path) -> Set[str]:
    """Return the set of slugs (filenames without .yaml) in a directory."""
    if not directory.exists():
        return set()
    return {yf.stem for yf in directory.glob('*.yaml')}


def check_refs(
    yaml_path: Path,
    record: Dict[str, Any],
    field: str,
    valid_slugs: Set[str],
    errors: List[str],
) -> None:
    """
    Check that all slugs in record[field] exist in valid_slugs.

    Appends error messages to `errors`.
    """
    values = record.get(field) or []
    if not isinstance(values, list):
        return
    for slug in values:
        if slug and slug not in valid_slugs:
            errors.append(
                f"  {yaml_path.name}: [{field}] unknown slug '{slug}'"
            )


# ---------------------------------------------------------------------------
# Per-entity validators
# ---------------------------------------------------------------------------

def validate_fundings(
    entries_root: Path,
    funder_slugs: Set[str],
    career_level_slugs: Set[str],
    subject_slugs: Set[str],
    funding_purpose_slugs: Set[str],
) -> Tuple[int, int]:
    """Validate all funding YAML files. Returns (files_checked, error_count)."""
    funding_dir = entries_root / 'fundings'
    if not funding_dir.exists():
        return 0, 0

    files = sorted(funding_dir.glob('*.yaml'))
    error_count = 0

    print(f"\nValidating fundings/ ({len(files)} files) …")
    for yaml_path in files:
        record = load_yaml_file(yaml_path)
        if not record:
            continue
        errors: List[str] = []
        check_refs(yaml_path, record, 'funders', funder_slugs, errors)
        check_refs(yaml_path, record, 'career_levels', career_level_slugs, errors)
        check_refs(yaml_path, record, 'subjects', subject_slugs, errors)
        check_refs(yaml_path, record, 'funding_purposes', funding_purpose_slugs, errors)
        if errors:
            for e in errors:
                print(e)
            error_count += len(errors)

    return len(files), error_count


def validate_travel_grants(
    entries_root: Path,
    funder_slugs: Set[str],
    career_level_slugs: Set[str],
    subject_slugs: Set[str],
    travel_purpose_slugs: Set[str],
) -> Tuple[int, int]:
    """Validate all travel grant YAML files. Returns (files_checked, error_count)."""
    tg_dir = entries_root / 'travel-grants'
    if not tg_dir.exists():
        return 0, 0

    files = sorted(tg_dir.glob('*.yaml'))
    error_count = 0

    print(f"\nValidating travel-grants/ ({len(files)} files) …")
    for yaml_path in files:
        record = load_yaml_file(yaml_path)
        if not record:
            continue
        errors: List[str] = []
        check_refs(yaml_path, record, 'funders', funder_slugs, errors)
        check_refs(yaml_path, record, 'career_levels', career_level_slugs, errors)
        check_refs(yaml_path, record, 'subjects', subject_slugs, errors)
        check_refs(yaml_path, record, 'travel_purposes', travel_purpose_slugs, errors)
        if errors:
            for e in errors:
                print(e)
            error_count += len(errors)

    return len(files), error_count


def validate_resources(
    entries_root: Path,
    funder_slugs: Set[str],
    resource_category_slugs: Set[str],
    subject_slugs: Set[str],
) -> Tuple[int, int]:
    """Validate all resource YAML files. Returns (files_checked, error_count)."""
    res_dir = entries_root / 'resources'
    if not res_dir.exists():
        return 0, 0

    files = sorted(res_dir.glob('*.yaml'))
    error_count = 0

    print(f"\nValidating resources/ ({len(files)} files) …")
    for yaml_path in files:
        record = load_yaml_file(yaml_path)
        if not record:
            continue
        errors: List[str] = []
        check_refs(yaml_path, record, 'funders', funder_slugs, errors)
        check_refs(yaml_path, record, 'resource_categories', resource_category_slugs, errors)
        check_refs(yaml_path, record, 'subjects', subject_slugs, errors)
        if errors:
            for e in errors:
                print(e)
            error_count += len(errors)

    return len(files), error_count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Validate taxonomy references in entity YAML files.',
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

    print(f"Building slug sets from vocabulary directories …")

    funder_slugs = build_slug_set(entries_root / 'funders')
    career_level_slugs = build_slug_set(entries_root / 'career-levels')
    subject_slugs = build_slug_set(entries_root / 'subjects')
    funding_purpose_slugs = build_slug_set(entries_root / 'funding-purposes')
    travel_purpose_slugs = build_slug_set(entries_root / 'travel-purposes')
    resource_category_slugs = build_slug_set(entries_root / 'resource-categories')

    print(f"  funders:             {len(funder_slugs)}")
    print(f"  career-levels:       {len(career_level_slugs)}")
    print(f"  subjects:            {len(subject_slugs)}")
    print(f"  funding-purposes:    {len(funding_purpose_slugs)}")
    print(f"  travel-purposes:     {len(travel_purpose_slugs)}")
    print(f"  resource-categories: {len(resource_category_slugs)}")

    total_files = 0
    total_errors = 0

    files, errors = validate_fundings(
        entries_root, funder_slugs, career_level_slugs, subject_slugs, funding_purpose_slugs
    )
    total_files += files
    total_errors += errors

    files, errors = validate_travel_grants(
        entries_root, funder_slugs, career_level_slugs, subject_slugs, travel_purpose_slugs
    )
    total_files += files
    total_errors += errors

    files, errors = validate_resources(
        entries_root, funder_slugs, resource_category_slugs, subject_slugs
    )
    total_files += files
    total_errors += errors

    print("\n" + "=" * 50)
    print(f"Taxonomy validation summary:")
    print(f"  Total files checked: {total_files}")
    print(f"  Broken references:   {total_errors}")
    print("=" * 50)

    if total_errors > 0:
        print(f"\nFAIL: {total_errors} broken reference(s) found.")
        sys.exit(1)
    else:
        print("\nOK: All taxonomy references valid.")
        sys.exit(0)


if __name__ == '__main__':
    main()
