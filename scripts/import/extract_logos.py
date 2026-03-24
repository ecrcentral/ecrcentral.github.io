#!/usr/bin/env python3
"""
Generate logo mapping from legacy funder logo paths.

Reads all funder YAML files, collects legacy_logo_path and logo fields,
outputs a logo_mapping.json with instructions for fetching logos from the
live server.

Usage:
    python extract_logos.py --entries data/entries/funders/
    python extract_logos.py  # uses default path
"""
import json
import shutil
import sys
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


def load_funder_yamls(entries_dir: Path) -> List[Dict[str, Any]]:
    """Load all YAML files from the funder entries directory."""
    funders = []
    yaml_files = sorted(entries_dir.glob('*.yaml'))
    if not yaml_files:
        print(f"  Warning: no YAML files found in {entries_dir}", file=sys.stderr)
        return funders
    for yf in yaml_files:
        try:
            with open(yf, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            if data:
                data['_file'] = str(yf)
                funders.append(data)
        except Exception as e:
            print(f"  Warning: failed to load {yf}: {e}", file=sys.stderr)
    return funders


def build_logo_mapping(funders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Build a list of logo mapping entries for each funder that has a legacy logo.

    Each entry contains:
      - slug: funder slug
      - name: funder name
      - legacy_path: original path stored in the DB (legacy_logo_path)
      - normalized_path: target path in the repo (logo field)
      - source_url: suggested URL to fetch the logo from the live server
    """
    mapping = []
    for funder in funders:
        legacy_path = funder.get('legacy_logo_path')
        normalized_path = funder.get('logo')
        slug = funder.get('slug', '')
        name = funder.get('name', '')

        if not legacy_path:
            continue

        # Strip leading slash / relative prefix from legacy path
        clean_legacy = legacy_path.lstrip('/')

        # Build a suggested live URL (adjust base URL to your legacy server)
        # Common patterns: /uploads/logos/filename.png
        source_url = f"https://ecrcentral.org/{clean_legacy}"

        mapping.append({
            'slug': slug,
            'name': name,
            'legacy_path': legacy_path,
            'normalized_path': normalized_path,
            'source_url': source_url,
        })

    return mapping


def create_placeholder_dirs(logo_dir: Path) -> None:
    """Ensure the logo output directory exists."""
    logo_dir.mkdir(parents=True, exist_ok=True)
    gitkeep = logo_dir / '.gitkeep'
    if not gitkeep.exists():
        gitkeep.touch()


def copy_logos(
    funders: List[Dict[str, Any]],
    source_dir: Path,
    logo_dir: Path,
) -> None:
    """
    Copy logo files from source_dir to logo_dir, renaming to {slug}.{ext},
    and update the 'logo' field in each funder's YAML file in-place.
    """
    logo_dir.mkdir(parents=True, exist_ok=True)

    copied = skipped = already_done = 0

    for funder in funders:
        legacy_path = funder.get('legacy_logo_path')
        slug = funder.get('slug', '')
        yaml_file = funder.get('_file')

        if not legacy_path or not slug or not yaml_file:
            continue

        src = source_dir / legacy_path
        ext = src.suffix.lower() or '.png'
        dest_name = f"{slug}{ext}"
        dest = logo_dir / dest_name
        logo_value = f"/logos/funders/{dest_name}"

        if not src.exists():
            print(f"  [SKIP] not found: {src}")
            skipped += 1
            continue

        if dest.exists() and funder.get('logo') == logo_value:
            already_done += 1
            continue

        shutil.copy2(src, dest)
        copied += 1

        # Update YAML logo field in-place
        with open(yaml_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        data['logo'] = logo_value
        with open(yaml_file, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        print(f"  [OK]   {src.name} → {dest_name}")

    print(f"\nLogos: {copied} copied, {skipped} skipped (not found), {already_done} already up-to-date.")


def print_fetch_instructions(mapping: List[Dict[str, Any]], logo_dir: Path) -> None:
    """Print shell commands to fetch all logos from the live server."""
    if not mapping:
        print("\nNo logos to fetch.")
        return

    print("\n" + "=" * 70)
    print("LOGO FETCH INSTRUCTIONS")
    print("=" * 70)
    print(f"\nFetch {len(mapping)} logo(s) using wget or curl:")
    print(f"  mkdir -p {logo_dir}\n")

    for entry in mapping:
        src = entry['source_url']
        dst = logo_dir / Path(entry['normalized_path']).name if entry['normalized_path'] else logo_dir / f"{entry['slug']}.png"
        print(f"  wget -q -O '{dst}' '{src}'")

    print()
    print("Or use the bulk download script (requires curl):")
    print(f"  while IFS= read -r line; do")
    print(f"    slug=$(echo \"$line\" | python3 -c \"import sys,json; d=json.load(sys.stdin); print(d['slug'])\")  ")
    print(f"    # etc.")
    print(f"  done < scripts/import/logo_mapping.json")
    print()
    print("After downloading, verify logos exist and update the 'logo' field in")
    print("each funder YAML if the file extension differs from expected.")
    print("=" * 70)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Generate logo mapping from legacy funder logo paths.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        '--entries',
        default='data/entries/funders/',
        help='Path to funder YAML entries directory (default: data/entries/funders/)',
    )
    parser.add_argument(
        '--output',
        default='scripts/import/logo_mapping.json',
        help='Output path for logo mapping JSON (default: scripts/import/logo_mapping.json)',
    )
    parser.add_argument(
        '--logo-dir',
        default='apps/web/public/logos/funders/',
        help='Target directory for funder logos (default: apps/web/public/logos/funders/)',
    )
    parser.add_argument(
        '--copy',
        action='store_true',
        help='Copy logos from --source-dir to --logo-dir and update YAML logo fields',
    )
    parser.add_argument(
        '--source-dir',
        default='storage/app/public',
        help='Root directory containing downloaded legacy logos (default: storage/app/public)',
    )
    args = parser.parse_args()

    entries_dir = Path(args.entries)
    output_path = Path(args.output)
    logo_dir = Path(args.logo_dir)
    source_dir = Path(args.source_dir)

    if not entries_dir.exists():
        print(f"Error: entries directory not found: {entries_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading funder entries from: {entries_dir}")
    funders = load_funder_yamls(entries_dir)
    print(f"  Loaded {len(funders)} funder YAML files")

    mapping = build_logo_mapping(funders)
    print(f"  Found {len(mapping)} funders with legacy logo paths")

    # Save mapping JSON
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    print(f"  Logo mapping saved to: {output_path}")

    # Ensure logo directory exists
    create_placeholder_dirs(logo_dir)
    print(f"  Logo directory ready: {logo_dir}")

    if args.copy:
        print(f"\nCopying logos from: {source_dir}")
        copy_logos(funders, source_dir, logo_dir)
    else:
        # Print fetch instructions
        print_fetch_instructions(mapping, logo_dir)

    # Summary
    no_logo = [f for f in funders if not f.get('legacy_logo_path')]
    print(f"\nSummary:")
    print(f"  Total funders:             {len(funders)}")
    print(f"  Funders with logos:        {len(mapping)}")
    print(f"  Funders without logos:     {len(no_logo)}")


if __name__ == '__main__':
    main()
