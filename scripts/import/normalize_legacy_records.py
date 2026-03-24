#!/usr/bin/env python3
"""
Normalize legacy MySQL records into YAML entry files.

This script orchestrates the full import pipeline:
  1. Parses the MySQL dump via parse_mysql_dump
  2. Builds lookup/pivot tables for M2M relations and vocabularies
  3. Writes one YAML file per entity into data/entries/{type}/

Usage:
    python normalize_legacy_records.py --sql backup.sql
    python normalize_legacy_records.py --sql backup.sql --output data/entries/
"""
import re
import sys
import json
import argparse
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

# Allow import of sibling module
sys.path.insert(0, str(Path(__file__).parent))
from parse_mysql_dump import parse_mysql_dump


# ---------------------------------------------------------------------------
# Slug generation
# ---------------------------------------------------------------------------

def make_slug(text: str) -> str:
    """Generate a clean URL slug from arbitrary text.

    - Normalises unicode to ASCII
    - Lowercases
    - Strips non-alphanumeric characters
    - Collapses whitespace / hyphens to single hyphen
    - Trims leading / trailing hyphens
    - Caps at 100 characters
    """
    text = unicodedata.normalize('NFKD', str(text))
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^a-z0-9\s-]', '', text.lower())
    text = re.sub(r'[\s-]+', '-', text).strip('-')
    return text[:100]


def ensure_unique_slug(base_slug: str, seen: Dict[str, int]) -> str:
    """Return a slug guaranteed to be unique by appending a counter if needed."""
    if base_slug not in seen:
        seen[base_slug] = 1
        return base_slug
    count = seen[base_slug] + 1
    seen[base_slug] = count
    candidate = f"{base_slug}-{count}"
    # Recurse in case the suffixed version is also taken
    return ensure_unique_slug(candidate, seen)


# ---------------------------------------------------------------------------
# Status / date helpers
# ---------------------------------------------------------------------------

FUNDING_STATUS_MAP = {1: 'active', 0: 'expired', '1': 'active', '0': 'expired'}
FUNDER_STATUS_MAP  = {1: 'active', 0: 'inactive', '1': 'active', '0': 'inactive'}
RESOURCE_STATUS_MAP = {1: 'active', 0: 'expired', '1': 'active', '0': 'expired'}


def map_status(raw: Any, mapping: Dict) -> str:
    """Map a raw DB status value to a string status."""
    if raw is None:
        return 'draft'
    try:
        v = int(raw)
    except (ValueError, TypeError):
        v = raw
    return mapping.get(v, 'draft')


def format_datetime(raw: Any) -> Optional[str]:
    """Convert MySQL datetime string 'YYYY-MM-DD HH:MM:SS' to ISO-8601 UTC string."""
    if not raw:
        return None
    s = str(raw).strip()
    # Already ISO format
    if 'T' in s:
        return s if s.endswith('Z') else s + 'Z'
    # MySQL format: 2020-05-22 15:57:55
    m = re.match(r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})', s)
    if m:
        return f"{m.group(1)}T{m.group(2)}Z"
    # Date only
    m2 = re.match(r'(\d{4}-\d{2}-\d{2})$', s)
    if m2:
        return f"{m2.group(1)}T00:00:00Z"
    return s or None


def coerce_bool(raw: Any) -> bool:
    """Coerce a DB value to Python bool."""
    if raw is None:
        return False
    if isinstance(raw, bool):
        return raw
    try:
        return int(raw) != 0
    except (ValueError, TypeError):
        return bool(raw)


def str_or_none(raw: Any) -> Optional[str]:
    """Return stripped string or None if empty / null."""
    if raw is None:
        return None
    s = str(raw).strip()
    return s if s else None


# ---------------------------------------------------------------------------
# Search text builder
# ---------------------------------------------------------------------------

def make_search_text(
    record: Dict[str, Any],
    funder_names: List[str],
    taxonomy_names: Dict[str, List[str]],
) -> str:
    """Build a flat search text string for full-text indexing."""
    parts = [
        record.get('name', '') or '',
        record.get('description', '') or '',
    ]
    parts.extend(funder_names)
    parts.extend(taxonomy_names.get('career_levels', []))
    parts.extend(taxonomy_names.get('subjects', []))
    parts.extend(taxonomy_names.get('funding_purposes', []))
    parts.extend(taxonomy_names.get('travel_purposes', []))
    parts.append(record.get('host_country', '') or '')
    parts.append(record.get('applicant_country', '') or '')
    return ' '.join(p for p in parts if p).strip()


# ---------------------------------------------------------------------------
# YAML write helper
# ---------------------------------------------------------------------------

def write_yaml(path: Path, data: Dict[str, Any]) -> None:
    """Write a dict as a YAML file with safe Unicode handling."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(
            data,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )


# ---------------------------------------------------------------------------
# Pivot / lookup builders
# ---------------------------------------------------------------------------

def build_id_map(rows: List[Dict[str, Any]], id_col: str = 'id') -> Dict[Any, Dict[str, Any]]:
    """Build a dict keyed by id_col value."""
    return {r[id_col]: r for r in rows if id_col in r}


def build_pivot(
    rows: List[Dict[str, Any]],
    left_col: str,
    right_col: str,
) -> Dict[Any, List[Any]]:
    """
    Build a one-to-many lookup from pivot table rows.

    Returns: { left_id: [right_id, ...] }
    """
    mapping: Dict[Any, List[Any]] = {}
    for row in rows:
        left = row.get(left_col)
        right = row.get(right_col)
        if left is None or right is None:
            continue
        mapping.setdefault(left, []).append(right)
    return mapping


# ---------------------------------------------------------------------------
# Vocabulary writers
# ---------------------------------------------------------------------------

def write_vocab_entries(
    rows: List[Dict[str, Any]],
    out_dir: Path,
    vocab_type: str,
    id_prefix: str,
    parent_id_col: Optional[str] = None,
    parent_map: Optional[Dict[Any, str]] = None,
) -> Dict[Any, str]:
    """
    Write YAML files for a vocabulary table.

    Returns a dict mapping legacy_id → slug (for M2M resolution).
    """
    seen_slugs: Dict[str, int] = {}
    legacy_to_slug: Dict[Any, str] = {}

    for row in rows:
        legacy_id = row.get('id')
        name = str_or_none(row.get('name'))
        if not name:
            continue

        base_slug = make_slug(name)
        slug = ensure_unique_slug(base_slug, seen_slugs)
        entry_id = f"{id_prefix}-{slug}"

        # Parent handling (subjects have parent_id)
        parent_id = None
        parent_slug = None
        if parent_id_col and parent_id_col in row:
            raw_parent = row.get(parent_id_col)
            if raw_parent is not None:
                try:
                    parent_id = int(raw_parent)
                except (ValueError, TypeError):
                    parent_id = None
            if parent_id and parent_map:
                parent_slug = parent_map.get(parent_id)

        record: Dict[str, Any] = {
            'id': entry_id,
            'legacy_id': int(legacy_id) if legacy_id is not None else None,
            'slug': slug,
            'name': name,
        }
        if parent_id_col:
            record['parent_id'] = parent_id
            record['parent_slug'] = parent_slug
        record['created_at'] = format_datetime(row.get('created_at'))
        record['updated_at'] = format_datetime(row.get('updated_at'))

        write_yaml(out_dir / f"{slug}.yaml", record)
        if legacy_id is not None:
            try:
                legacy_to_slug[int(legacy_id)] = slug
            except (ValueError, TypeError):
                legacy_to_slug[legacy_id] = slug

    return legacy_to_slug


# ---------------------------------------------------------------------------
# Funder writer
# ---------------------------------------------------------------------------

def write_funder_entries(
    rows: List[Dict[str, Any]],
    out_dir: Path,
) -> Dict[Any, str]:
    """
    Write YAML files for funders.

    Returns a dict mapping legacy_id → slug.
    """
    seen_slugs: Dict[str, int] = {}
    legacy_to_slug: Dict[Any, str] = {}

    for row in rows:
        legacy_id = row.get('id')
        name = str_or_none(row.get('name'))
        if not name:
            continue

        base_slug = make_slug(name)
        slug = ensure_unique_slug(base_slug, seen_slugs)
        entry_id = f"funder-{slug}"

        # Logo: derive from legacy_logo_path extension
        legacy_logo_path = str_or_none(row.get('logo'))
        logo_path: Optional[str] = None
        if legacy_logo_path:
            ext = Path(legacy_logo_path).suffix.lower()
            if not ext:
                ext = '.png'
            logo_path = f"/logos/funders/{slug}{ext}"

        country = str_or_none(row.get('country')) or 'Unknown'
        website = str_or_none(row.get('url'))

        record: Dict[str, Any] = {
            'id': entry_id,
            'legacy_id': int(legacy_id) if legacy_id is not None else None,
            'slug': slug,
            'name': name,
            'short_name': name,  # can be manually edited
            'funder_registry_id': str_or_none(row.get('funder_id')),
            'country': country,
            'website': website,
            'logo': logo_path,
            'legacy_logo_path': legacy_logo_path,
            'dora': coerce_bool(row.get('dora')),
            'aliases': [],
            'description': None,
            'status': map_status(row.get('status'), FUNDER_STATUS_MAP),
            'featured': False,
            'review_status': 'approved',
            'last_verified': '2026-02-19',
            'verified_by': 'asntech',
            'created_at': format_datetime(row.get('created_at')),
            'updated_at': format_datetime(row.get('updated_at')),
            'source': 'legacy-import',
        }

        write_yaml(out_dir / f"{slug}.yaml", record)
        if legacy_id is not None:
            try:
                legacy_to_slug[int(legacy_id)] = slug
            except (ValueError, TypeError):
                legacy_to_slug[legacy_id] = slug

    return legacy_to_slug


# ---------------------------------------------------------------------------
# Funding writer
# ---------------------------------------------------------------------------

def write_funding_entries(
    rows: List[Dict[str, Any]],
    out_dir: Path,
    funder_pivot: Dict[Any, List[Any]],      # funding_id → [funder_legacy_id, ...]
    funder_id_to_slug: Dict[Any, str],
    career_level_pivot: Dict[Any, List[Any]],
    career_level_id_to_slug: Dict[Any, str],
    subject_pivot: Dict[Any, List[Any]],
    subject_id_to_slug: Dict[Any, str],
    funding_purpose_pivot: Dict[Any, List[Any]],
    funding_purpose_id_to_slug: Dict[Any, str],
    funder_id_to_name: Dict[Any, str],
    career_level_id_to_name: Dict[Any, str],
    subject_id_to_name: Dict[Any, str],
    funding_purpose_id_to_name: Dict[Any, str],
) -> int:
    """Write YAML files for fundings. Returns count written."""
    seen_slugs: Dict[str, int] = {}
    count = 0

    for row in rows:
        legacy_id = row.get('id')
        name = str_or_none(row.get('name'))
        if not name:
            continue

        base_slug = make_slug(name)
        slug = ensure_unique_slug(base_slug, seen_slugs)
        entry_id = f"funding-{slug}"

        # M2M relations
        funder_legacy_ids = funder_pivot.get(legacy_id, [])
        funder_slugs = [funder_id_to_slug[fid] for fid in funder_legacy_ids if fid in funder_id_to_slug]
        funder_names = [funder_id_to_name[fid] for fid in funder_legacy_ids if fid in funder_id_to_name]

        cl_ids = career_level_pivot.get(legacy_id, [])
        career_level_slugs = [career_level_id_to_slug[i] for i in cl_ids if i in career_level_id_to_slug]
        career_level_names = [career_level_id_to_name[i] for i in cl_ids if i in career_level_id_to_name]

        subj_ids = subject_pivot.get(legacy_id, [])
        subject_slugs = [subject_id_to_slug[i] for i in subj_ids if i in subject_id_to_slug]
        subject_names = [subject_id_to_name[i] for i in subj_ids if i in subject_id_to_name]

        fp_ids = funding_purpose_pivot.get(legacy_id, [])
        funding_purpose_slugs = [funding_purpose_id_to_slug[i] for i in fp_ids if i in funding_purpose_id_to_slug]
        funding_purpose_names = [funding_purpose_id_to_name[i] for i in fp_ids if i in funding_purpose_id_to_name]

        taxonomy_names = {
            'career_levels': career_level_names,
            'subjects': subject_names,
            'funding_purposes': funding_purpose_names,
        }

        record: Dict[str, Any] = {
            'id': entry_id,
            'legacy_id': int(legacy_id) if legacy_id is not None else None,
            'slug': slug,
            'name': name,
            'description': str_or_none(row.get('description')),
            'url': str_or_none(row.get('url')) or '',
            'funders': funder_slugs,
            'legacy_funder_name': str_or_none(row.get('funder_name')),
            'host_country': str_or_none(row.get('host_country')),
            'applicant_country': str_or_none(row.get('applicant_country')),
            'academic_level': str_or_none(row.get('academic_level')),
            'career_levels': career_level_slugs,
            'years_since_phd': str_or_none(row.get('years_since_phd')),
            'duration': str_or_none(row.get('duration')),
            'award': str_or_none(row.get('award')),
            'mobility_rule': str_or_none(row.get('mobility_rule')),
            'research_costs': str_or_none(row.get('research_costs')),
            'deadline': str_or_none(row.get('deadline')),
            'deadline_raw': str_or_none(row.get('deadline_raw')),
            'deadline_month': str_or_none(row.get('deadline_month')),
            'diversity': str_or_none(row.get('diversity')),
            'comments': str_or_none(row.get('comments')),
            'benefits': str_or_none(row.get('benefits')),
            'frequency': str_or_none(row.get('frequency')),
            'fileds': str_or_none(row.get('fileds')),
            'featured': coerce_bool(row.get('featured')),
            'review_status': 'approved',
            'status': map_status(row.get('status'), FUNDING_STATUS_MAP),
            'last_verified': '2026-02-19',
            'verified_by': 'asntech',
            'legacy_user_id': int(row['user_id']) if row.get('user_id') is not None else None,
            'created_at': format_datetime(row.get('created_at')),
            'updated_at': format_datetime(row.get('updated_at')),
            'subjects': subject_slugs,
            'funding_purposes': funding_purpose_slugs,
            'search_text': make_search_text({'name': name, 'description': row.get('description'),
                                              'host_country': row.get('host_country'),
                                              'applicant_country': row.get('applicant_country')},
                                             funder_names, taxonomy_names),
            'source': 'legacy-import',
        }

        write_yaml(out_dir / f"{slug}.yaml", record)
        count += 1

    return count


# ---------------------------------------------------------------------------
# Travel grant writer
# ---------------------------------------------------------------------------

def write_travel_grant_entries(
    rows: List[Dict[str, Any]],
    out_dir: Path,
    funder_pivot: Dict[Any, List[Any]],
    funder_id_to_slug: Dict[Any, str],
    career_level_pivot: Dict[Any, List[Any]],
    career_level_id_to_slug: Dict[Any, str],
    subject_pivot: Dict[Any, List[Any]],
    subject_id_to_slug: Dict[Any, str],
    travel_purpose_pivot: Dict[Any, List[Any]],
    travel_purpose_id_to_slug: Dict[Any, str],
    funder_id_to_name: Dict[Any, str],
    career_level_id_to_name: Dict[Any, str],
    subject_id_to_name: Dict[Any, str],
    travel_purpose_id_to_name: Dict[Any, str],
) -> int:
    """Write YAML files for travel grants. Returns count written."""
    seen_slugs: Dict[str, int] = {}
    count = 0

    for row in rows:
        legacy_id = row.get('id')
        name = str_or_none(row.get('name'))
        if not name:
            continue

        base_slug = make_slug(name)
        slug = ensure_unique_slug(base_slug, seen_slugs)
        entry_id = f"travel-grant-{slug}"

        # M2M
        funder_legacy_ids = funder_pivot.get(legacy_id, [])
        funder_slugs = [funder_id_to_slug[fid] for fid in funder_legacy_ids if fid in funder_id_to_slug]
        funder_names = [funder_id_to_name[fid] for fid in funder_legacy_ids if fid in funder_id_to_name]

        cl_ids = career_level_pivot.get(legacy_id, [])
        career_level_slugs = [career_level_id_to_slug[i] for i in cl_ids if i in career_level_id_to_slug]
        career_level_names = [career_level_id_to_name[i] for i in cl_ids if i in career_level_id_to_name]

        subj_ids = subject_pivot.get(legacy_id, [])
        subject_slugs = [subject_id_to_slug[i] for i in subj_ids if i in subject_id_to_slug]
        subject_names = [subject_id_to_name[i] for i in subj_ids if i in subject_id_to_name]

        tp_ids = travel_purpose_pivot.get(legacy_id, [])
        travel_purpose_slugs = [travel_purpose_id_to_slug[i] for i in tp_ids if i in travel_purpose_id_to_slug]
        travel_purpose_names = [travel_purpose_id_to_name[i] for i in tp_ids if i in travel_purpose_id_to_name]

        taxonomy_names = {
            'career_levels': career_level_names,
            'subjects': subject_names,
            'travel_purposes': travel_purpose_names,
        }

        record: Dict[str, Any] = {
            'id': entry_id,
            'legacy_id': int(legacy_id) if legacy_id is not None else None,
            'slug': slug,
            'name': name,
            'url': str_or_none(row.get('url')) or '',
            'description': str_or_none(row.get('description')),
            'funders': funder_slugs,
            'legacy_funder_name': str_or_none(row.get('funder_name')),
            'applicant_country': str_or_none(row.get('applicant_country')),
            'host_country': str_or_none(row.get('host_country')),
            'award': str_or_none(row.get('award')),
            'deadline': str_or_none(row.get('deadline')),
            'deadline_raw': str_or_none(row.get('deadline_raw')),
            'deadline_month': str_or_none(row.get('deadline_month')),
            'membership': str_or_none(row.get('membership')),
            'membership_time': str_or_none(row.get('membership_time')),
            'purpose_text': str_or_none(row.get('purpose_text')),
            'career_levels': career_level_slugs,
            'subjects': subject_slugs,
            'travel_purposes': travel_purpose_slugs,
            'featured': coerce_bool(row.get('featured')),
            'review_status': 'approved',
            'status': map_status(row.get('status'), FUNDING_STATUS_MAP),
            'last_verified': '2026-02-19',
            'verified_by': 'asntech',
            'created_at': format_datetime(row.get('created_at')),
            'updated_at': format_datetime(row.get('updated_at')),
            'search_text': make_search_text({'name': name, 'description': row.get('description'),
                                              'host_country': row.get('host_country'),
                                              'applicant_country': row.get('applicant_country')},
                                             funder_names, taxonomy_names),
            'source': 'legacy-import',
        }

        write_yaml(out_dir / f"{slug}.yaml", record)
        count += 1

    return count


# ---------------------------------------------------------------------------
# Resource writer
# ---------------------------------------------------------------------------

def write_resource_entries(
    rows: List[Dict[str, Any]],
    out_dir: Path,
    funder_pivot: Dict[Any, List[Any]],
    funder_id_to_slug: Dict[Any, str],
    resource_category_pivot: Dict[Any, List[Any]],
    resource_category_id_to_slug: Dict[Any, str],
    subject_pivot: Dict[Any, List[Any]],
    subject_id_to_slug: Dict[Any, str],
) -> int:
    """Write YAML files for resources. Returns count written."""
    seen_slugs: Dict[str, int] = {}
    count = 0

    for row in rows:
        legacy_id = row.get('id')
        name = str_or_none(row.get('name'))
        if not name:
            continue

        base_slug = make_slug(name)
        slug = ensure_unique_slug(base_slug, seen_slugs)
        entry_id = f"resource-{slug}"

        funder_legacy_ids = funder_pivot.get(legacy_id, [])
        funder_slugs = [funder_id_to_slug[fid] for fid in funder_legacy_ids if fid in funder_id_to_slug]

        rc_ids = resource_category_pivot.get(legacy_id, [])
        resource_category_slugs = [resource_category_id_to_slug[i] for i in rc_ids if i in resource_category_id_to_slug]

        subj_ids = subject_pivot.get(legacy_id, [])
        subject_slugs = [subject_id_to_slug[i] for i in subj_ids if i in subject_id_to_slug]

        record: Dict[str, Any] = {
            'id': entry_id,
            'legacy_id': int(legacy_id) if legacy_id is not None else None,
            'slug': slug,
            'name': name,
            'url': str_or_none(row.get('url')) or '',
            'description': str_or_none(row.get('description')),
            'source_name': str_or_none(row.get('source_name')),
            'funders': funder_slugs,
            'resource_categories': resource_category_slugs,
            'subjects': subject_slugs,
            'featured': coerce_bool(row.get('featured')),
            'review_status': 'approved',
            'status': map_status(row.get('status'), RESOURCE_STATUS_MAP),
            'last_verified': '2026-02-19',
            'verified_by': 'asntech',
            'created_at': format_datetime(row.get('created_at')),
            'updated_at': format_datetime(row.get('updated_at')),
            'source': 'legacy-import',
        }

        write_yaml(out_dir / f"{slug}.yaml", record)
        count += 1

    return count


# ---------------------------------------------------------------------------
# Normalise integers in pivot ids
# ---------------------------------------------------------------------------

def int_key(v: Any) -> Any:
    """Try to convert v to int for consistent dict key lookup."""
    if v is None:
        return v
    try:
        return int(v)
    except (ValueError, TypeError):
        return v


def normalize_pivot(
    rows: List[Dict[str, Any]],
    left_col: str,
    right_col: str,
) -> Dict[Any, List[Any]]:
    """Build pivot with integer-normalised keys and values."""
    mapping: Dict[Any, List[Any]] = {}
    for row in rows:
        left = int_key(row.get(left_col))
        right = int_key(row.get(right_col))
        if left is None or right is None:
            continue
        mapping.setdefault(left, []).append(right)
    return mapping


def build_id_name_maps(
    rows: List[Dict[str, Any]],
) -> Tuple[Dict[Any, str], Dict[Any, str]]:
    """
    Build two maps from a vocab table:
      id → slug (after make_slug of name)
      id → name
    """
    id_to_slug: Dict[Any, str] = {}
    id_to_name: Dict[Any, str] = {}
    seen: Dict[str, int] = {}

    for row in rows:
        raw_id = row.get('id')
        if raw_id is None:
            continue
        try:
            int_id = int(raw_id)
        except (ValueError, TypeError):
            int_id = raw_id

        name = str_or_none(row.get('name'))
        if not name:
            continue

        base_slug = make_slug(name)
        slug = ensure_unique_slug(base_slug, seen)
        id_to_slug[int_id] = slug
        id_to_name[int_id] = name

    return id_to_slug, id_to_name


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entry point for the full import pipeline."""
    parser = argparse.ArgumentParser(
        description='Normalize legacy MySQL records into YAML entry files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--sql', required=True, help='Path to MySQL .sql dump file')
    parser.add_argument(
        '--output', default='data/entries/',
        help='Root directory for YAML output (default: data/entries/)',
    )
    args = parser.parse_args()

    out_root = Path(args.output)

    # ------------------------------------------------------------------
    # 1. Parse dump
    # ------------------------------------------------------------------
    print(f"Parsing MySQL dump: {args.sql}")
    data = parse_mysql_dump(args.sql)

    # ------------------------------------------------------------------
    # 2. Build vocabulary maps (id→slug, id→name)
    # ------------------------------------------------------------------
    print("Building vocabulary maps …")

    career_level_id_to_slug, career_level_id_to_name = build_id_name_maps(data['career_levels'])
    subject_id_to_slug, subject_id_to_name = build_id_name_maps(data['subjects'])
    funding_purpose_id_to_slug, funding_purpose_id_to_name = build_id_name_maps(data['funding_purposes'])
    travel_purpose_id_to_slug, travel_purpose_id_to_name = build_id_name_maps(data['travel_purposes'])
    resource_category_id_to_slug, resource_category_id_to_name = build_id_name_maps(data['resource_categories'])
    funder_id_to_slug, funder_id_to_name = build_id_name_maps(data['funders'])

    # ------------------------------------------------------------------
    # 3. Write vocabulary YAML files
    # ------------------------------------------------------------------
    print("Writing vocabulary entries …")

    # career-levels
    career_level_dir = out_root / 'career-levels'
    career_level_dir.mkdir(parents=True, exist_ok=True)
    write_vocab_entries(data['career_levels'], career_level_dir, 'career-levels', 'career-level')

    # subjects (have parent_id)
    subject_dir = out_root / 'subjects'
    subject_dir.mkdir(parents=True, exist_ok=True)
    # Build parent_id → slug for subjects (two-pass: first build slug map, then write with parent info)
    parent_map: Dict[int, str] = {}
    for row in data['subjects']:
        raw_id = row.get('id')
        name = str_or_none(row.get('name'))
        if raw_id is not None and name:
            try:
                parent_map[int(raw_id)] = make_slug(name)
            except (ValueError, TypeError):
                pass
    write_vocab_entries(
        data['subjects'], subject_dir, 'subjects', 'subject',
        parent_id_col='parent_id', parent_map=parent_map,
    )

    # funding-purposes
    fp_dir = out_root / 'funding-purposes'
    fp_dir.mkdir(parents=True, exist_ok=True)
    write_vocab_entries(data['funding_purposes'], fp_dir, 'funding-purposes', 'funding-purpose')

    # travel-purposes
    tp_dir = out_root / 'travel-purposes'
    tp_dir.mkdir(parents=True, exist_ok=True)
    write_vocab_entries(data['travel_purposes'], tp_dir, 'travel-purposes', 'travel-purpose')

    # resource-categories
    rc_dir = out_root / 'resource-categories'
    rc_dir.mkdir(parents=True, exist_ok=True)
    write_vocab_entries(data['resource_categories'], rc_dir, 'resource-categories', 'resource-category')

    # ------------------------------------------------------------------
    # 4. Write funder YAML files
    # ------------------------------------------------------------------
    print("Writing funder entries …")
    funder_dir = out_root / 'funders'
    funder_dir.mkdir(parents=True, exist_ok=True)
    funder_id_to_slug = write_funder_entries(data['funders'], funder_dir)
    # Rebuild name map using the now-correct slugs (write_funder_entries re-generates slugs)
    funder_id_to_name_final: Dict[Any, str] = {}
    for row in data['funders']:
        raw_id = row.get('id')
        if raw_id is not None:
            try:
                iid = int(raw_id)
            except (ValueError, TypeError):
                iid = raw_id
            name = str_or_none(row.get('name')) or ''
            funder_id_to_name_final[iid] = name

    # ------------------------------------------------------------------
    # 5. Build pivot tables
    # ------------------------------------------------------------------
    print("Building pivot tables …")

    # fundings
    funding_funder_pivot = normalize_pivot(data['funder_funding'], 'funding_id', 'funder_id')
    funding_cl_pivot = normalize_pivot(data['careerlevel_funding'], 'funding_id', 'career_level_id')
    funding_subj_pivot = normalize_pivot(data['subject_funding'], 'funding_id', 'subject_id')
    funding_fp_pivot = normalize_pivot(data['fundingpurpose_funding'], 'funding_id', 'funding_purpose_id')

    # travel grants
    tg_funder_pivot = normalize_pivot(data['funder_travelgrant'], 'travel_grant_id', 'funder_id')
    tg_cl_pivot = normalize_pivot(data['careerlevel_travelgrant'], 'travel_grant_id', 'career_level_id')
    tg_subj_pivot = normalize_pivot(data['subject_travelgrant'], 'travel_grant_id', 'subject_id')
    tg_tp_pivot = normalize_pivot(data['travelpurpose_travelgrant'], 'travel_grant_id', 'travel_purpose_id')

    # resources
    res_funder_pivot = normalize_pivot(data['funder_travelgrant'], 'resource_id', 'funder_id')
    # funder_travelgrant won't have resource_id; use correct pivot table
    res_rc_pivot = normalize_pivot(data['resource_category_resource'], 'resource_id', 'resource_category_id')
    # subjects for resources — look for subject_resource pivot if present, else skip
    res_subj_pivot: Dict[Any, List[Any]] = {}

    # Normalise funder id→slug with int keys
    funder_id_to_slug_int: Dict[int, str] = {}
    for row in data['funders']:
        raw_id = row.get('id')
        name = str_or_none(row.get('name'))
        if raw_id is not None and name:
            try:
                funder_id_to_slug_int[int(raw_id)] = make_slug(name)
            except (ValueError, TypeError):
                pass

    # ------------------------------------------------------------------
    # 6. Write entity YAML files
    # ------------------------------------------------------------------
    print("Writing funding entries …")
    funding_dir = out_root / 'fundings'
    funding_dir.mkdir(parents=True, exist_ok=True)
    n_fundings = write_funding_entries(
        data['fundings'], funding_dir,
        funder_pivot=funding_funder_pivot,
        funder_id_to_slug=funder_id_to_slug_int,
        career_level_pivot=funding_cl_pivot,
        career_level_id_to_slug=career_level_id_to_slug,
        subject_pivot=funding_subj_pivot,
        subject_id_to_slug=subject_id_to_slug,
        funding_purpose_pivot=funding_fp_pivot,
        funding_purpose_id_to_slug=funding_purpose_id_to_slug,
        funder_id_to_name=funder_id_to_name_final,
        career_level_id_to_name=career_level_id_to_name,
        subject_id_to_name=subject_id_to_name,
        funding_purpose_id_to_name=funding_purpose_id_to_name,
    )

    print("Writing travel grant entries …")
    tg_dir = out_root / 'travel-grants'
    tg_dir.mkdir(parents=True, exist_ok=True)
    n_tgs = write_travel_grant_entries(
        data['travel_grants'], tg_dir,
        funder_pivot=tg_funder_pivot,
        funder_id_to_slug=funder_id_to_slug_int,
        career_level_pivot=tg_cl_pivot,
        career_level_id_to_slug=career_level_id_to_slug,
        subject_pivot=tg_subj_pivot,
        subject_id_to_slug=subject_id_to_slug,
        travel_purpose_pivot=tg_tp_pivot,
        travel_purpose_id_to_slug=travel_purpose_id_to_slug,
        funder_id_to_name=funder_id_to_name_final,
        career_level_id_to_name=career_level_id_to_name,
        subject_id_to_name=subject_id_to_name,
        travel_purpose_id_to_name=travel_purpose_id_to_name,
    )

    print("Writing resource entries …")
    res_dir = out_root / 'resources'
    res_dir.mkdir(parents=True, exist_ok=True)

    # Resources: funder pivot uses funder_resource or funder_travelgrant table?
    # Use a dedicated resource funder pivot if available; otherwise empty
    res_funder_pivot2 = normalize_pivot(data.get('funder_resource', []), 'resource_id', 'funder_id')

    n_resources = write_resource_entries(
        data['resources'], res_dir,
        funder_pivot=res_funder_pivot2,
        funder_id_to_slug=funder_id_to_slug_int,
        resource_category_pivot=res_rc_pivot,
        resource_category_id_to_slug=resource_category_id_to_slug,
        subject_pivot=res_subj_pivot,
        subject_id_to_slug=subject_id_to_slug,
    )

    # ------------------------------------------------------------------
    # 7. Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 50)
    print("Import summary")
    print("=" * 50)
    print(f"  career-levels:      {len(data['career_levels'])} entries")
    print(f"  subjects:           {len(data['subjects'])} entries")
    print(f"  funding-purposes:   {len(data['funding_purposes'])} entries")
    print(f"  travel-purposes:    {len(data['travel_purposes'])} entries")
    print(f"  resource-categories:{len(data['resource_categories'])} entries")
    print(f"  funders:            {len(data['funders'])} entries")
    print(f"  fundings:           {n_fundings} entries")
    print(f"  travel-grants:      {n_tgs} entries")
    print(f"  resources:          {n_resources} entries")
    print()
    print(f"Output written to: {out_root}")


if __name__ == '__main__':
    main()
