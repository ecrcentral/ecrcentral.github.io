#!/usr/bin/env python3
"""
Normalise country name variants to standard forms across all YAML entries.

Replaces USA / U.S.A / U.S.A. / U.S. / United States of America → United States
Handles comma-separated values like "USA, Canada" → "United States, Canada"

Usage:
    python scripts/build/normalise_countries.py
    python scripts/build/normalise_countries.py --dry-run
"""
import argparse
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

NORMALISE = {
    'usa': 'United States',
    'u.s.a': 'United States',
    'u.s.a.': 'United States',
    'u.s.': 'United States',
    'united states of america': 'United States',
    # United Kingdom variants
    'uk': 'United Kingdom',
    'u.k.': 'United Kingdom',
    'u.k': 'United Kingdom',
    # Worldwide variants
    'global': 'Worldwide',
    'all': 'Worldwide',
    'all countries': 'Worldwide',
    'worldwide': 'Worldwide',
    'international': 'Worldwide',
    'no restrictions': 'Worldwide',
    'any': 'Worldwide',
}

# Fields to check per directory
FIELD_MAP = {
    'fundings': ['applicant_country', 'host_country'],
    'travel-grants': ['applicant_country', 'host_country'],
    'funders': ['country'],
}


def normalise_value(val: str) -> str:
    """Normalise a single country string, handling comma-separated lists."""
    if not val or not isinstance(val, str):
        return val
    parts = [p.strip() for p in val.split(',')]
    normalised = [NORMALISE.get(p.lower(), p) for p in parts]
    return ', '.join(normalised)


def process_file(path: Path, fields: list, dry_run: bool) -> bool:
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    if not data:
        return False

    changed = False
    for field in fields:
        original = data.get(field)
        if not original or not isinstance(original, str):
            continue
        updated = normalise_value(original)
        if updated != original:
            data[field] = updated
            changed = True
            if dry_run:
                print(f'  [DRY] {path.name}: {field}: "{original}" → "{updated}"')

    if not changed:
        return False

    if not dry_run:
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        print(f'  [OK] {path.name}')
    return True


def main():
    parser = argparse.ArgumentParser(description='Normalise country names in YAML entries.')
    parser.add_argument('--dry-run', action='store_true', help='Preview without writing')
    args = parser.parse_args()

    entries_dir = REPO_ROOT / 'data' / 'entries'
    total = modified = errors = 0

    for subdir, fields in FIELD_MAP.items():
        dir_path = entries_dir / subdir
        if not dir_path.exists():
            print(f'[SKIP] directory not found: {dir_path}', file=sys.stderr)
            continue
        files = sorted(dir_path.glob('*.yaml'))
        print(f'\nProcessing {len(files)} files in {subdir}/ ({", ".join(fields)})')
        for path in files:
            total += 1
            try:
                if process_file(path, fields, dry_run=args.dry_run):
                    modified += 1
            except Exception as exc:
                errors += 1
                print(f'  [ERR] {path.name}: {exc}', file=sys.stderr)

    mode = ' (dry-run)' if args.dry_run else ''
    print(f'\nDone{mode} — {total} checked, {modified} modified, {errors} errors.')
    if args.dry_run:
        print('Re-run without --dry-run to apply.')


if __name__ == '__main__':
    main()
