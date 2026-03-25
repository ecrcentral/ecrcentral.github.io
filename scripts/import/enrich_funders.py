#!/usr/bin/env python3
"""
Enrich funder YAML files with website, description, DORA status, and logo.

Usage:
    python scripts/import/enrich_funders.py --data enrichment.json
"""
import argparse
import json
import shutil
import sys
import urllib.request
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
FUNDERS_DIR = REPO_ROOT / 'data' / 'entries' / 'funders'
LOGO_DIR = REPO_ROOT / 'apps' / 'web' / 'public' / 'logos' / 'funders'


def download_logo(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
        # Basic check: must be image (not HTML)
        if data[:4] in (b'\x89PNG', b'<svg', b'GIF8') or data[:2] == b'\xff\xd8':
            dest.write_bytes(data)
            return True
        if b'<html' in data[:200].lower():
            print(f'    [SKIP] got HTML instead of image: {url}')
            return False
        dest.write_bytes(data)
        return True
    except Exception as e:
        print(f'    [SKIP] download failed: {e}')
        return False


def enrich(slug: str, record: dict, dry_run: bool) -> bool:
    path = FUNDERS_DIR / f'{slug}.yaml'
    if not path.exists():
        print(f'  [SKIP] file not found: {slug}')
        return False

    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    if not data:
        return False

    changed = False

    if record.get('website') and not data.get('website'):
        data['website'] = record['website']
        changed = True

    if record.get('description') and not data.get('description'):
        data['description'] = record['description']
        changed = True

    if record.get('dora') is not None and data.get('dora') != record['dora']:
        data['dora'] = record['dora']
        changed = True

    logo_url = record.get('logo_url')
    if logo_url and not data.get('logo'):
        ext = Path(logo_url.split('?')[0]).suffix.lower() or '.png'
        if ext not in ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'):
            ext = '.png'
        logo_filename = f'{slug}{ext}'
        logo_dest = LOGO_DIR / logo_filename
        logo_value = f'/logos/funders/{logo_filename}'
        if not dry_run:
            LOGO_DIR.mkdir(parents=True, exist_ok=True)
            if download_logo(logo_url, logo_dest):
                data['logo'] = logo_value
                changed = True
                print(f'    logo → {logo_filename}')
            else:
                print(f'    logo download failed, skipping')
        else:
            print(f'    [DRY] would download logo from {logo_url}')
            changed = True

    if not changed:
        return False

    if dry_run:
        print(f'  [DRY] would update {slug}')
        return True

    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return True


def main():
    parser = argparse.ArgumentParser(description='Enrich funder YAML files.')
    parser.add_argument('--data', required=True, help='JSON file with enrichment data')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    with open(args.data, 'r', encoding='utf-8') as f:
        records = json.load(f)

    updated = skipped = 0
    for record in records:
        slug = record.get('slug')
        if not slug:
            continue
        print(f'  {slug}')
        if enrich(slug, record, dry_run=args.dry_run):
            updated += 1
        else:
            skipped += 1

    print(f'\nDone — {updated} updated, {skipped} skipped/unchanged.')


if __name__ == '__main__':
    main()
