#!/usr/bin/env python3
"""
Clean up legacy fields in all travel grant YAML files.

For each data/entries/travel-grants/*.yaml:
  1. Extract deadline_month from the deadline field (month names, comma-separated)
  2. Remove deadline_raw (already null everywhere)
  3. Remove academic_level (career_levels covers this already)

Usage:
    python scripts/build/clean_travel_grants_fields.py
    python scripts/build/clean_travel_grants_fields.py --dry-run
"""
import argparse
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
TRAVEL_GRANTS_DIR = REPO_ROOT / 'data' / 'entries' / 'travel-grants'

MONTH_MAP = {
    'january': 'January', 'jan': 'January',
    'february': 'February', 'feb': 'February',
    'march': 'March', 'mar': 'March',
    'april': 'April', 'apr': 'April',
    'may': 'May',
    'june': 'June', 'jun': 'June',
    'july': 'July', 'jul': 'July',
    'august': 'August', 'aug': 'August',
    'september': 'September', 'sep': 'September', 'sept': 'September',
    'october': 'October', 'oct': 'October',
    'november': 'November', 'nov': 'November',
    'december': 'December', 'dec': 'December',
}

SPLIT_RE = re.compile(r'[\s,/;.\-–]+')


def extract_months(deadline: str | None) -> str | None:
    """Extract month names from a free-text deadline string."""
    if not deadline:
        return None
    tokens = SPLIT_RE.split(deadline.lower())
    seen: set[str] = set()
    result: list[str] = []
    for t in tokens:
        t = t.strip()
        if t in MONTH_MAP and MONTH_MAP[t] not in seen:
            result.append(MONTH_MAP[t])
            seen.add(MONTH_MAP[t])
    return ', '.join(result) if result else None


def process_file(path: Path, dry_run: bool) -> bool:
    with path.open('r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    if data is None:
        return False

    changed = False

    # 1. Populate deadline_month from deadline if not already set
    if not data.get('deadline_month'):
        months = extract_months(data.get('deadline'))
        if months:
            data['deadline_month'] = months
            changed = True

    # 2. Remove deadline_raw
    if 'deadline_raw' in data:
        del data['deadline_raw']
        changed = True

    # 3. Remove academic_level
    if 'academic_level' in data:
        del data['academic_level']
        changed = True

    if not changed:
        return False

    if dry_run:
        print(f'  [DRY] would update {path.name}')
        return True

    with path.open('w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    return True


def main():
    parser = argparse.ArgumentParser(description='Clean legacy fields from travel grant YAML files.')
    parser.add_argument('--dry-run', action='store_true', help='Preview without writing')
    args = parser.parse_args()

    if not TRAVEL_GRANTS_DIR.exists():
        print(f'[ERR] directory not found: {TRAVEL_GRANTS_DIR}', file=sys.stderr)
        sys.exit(1)

    files = sorted(TRAVEL_GRANTS_DIR.glob('*.yaml'))
    print(f'Processing {len(files)} files in {TRAVEL_GRANTS_DIR.name}/')

    total = modified = errors = 0
    for path in files:
        total += 1
        try:
            if process_file(path, dry_run=args.dry_run):
                modified += 1
                if not args.dry_run:
                    print(f'  [OK] {path.name}')
        except Exception as exc:
            errors += 1
            print(f'  [ERR] {path.name}: {exc}', file=sys.stderr)

    mode = ' (dry-run)' if args.dry_run else ''
    print(f'\nDone{mode} — {total} checked, {modified} modified, {errors} errors.')
    if args.dry_run:
        print('Re-run without --dry-run to apply.')


if __name__ == '__main__':
    main()
