#!/usr/bin/env python3
"""
Validate YAML entry files against their JSON schemas.

Reads all YAML files from data/entries/ and validates each file against the
appropriate JSON schema using jsonschema.

Exit code: 0 if all valid, 1 if any errors found.

Usage:
    python validate_yaml.py
    python validate_yaml.py --entries data/entries/ --schema data/schema/
"""
import sys
import json
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
import jsonschema
from jsonschema import Draft7Validator


# Map entry subdirectory → schema filename
SCHEMA_MAP: Dict[str, str] = {
    'funders': 'funder.schema.json',
    'fundings': 'funding.schema.json',
    'travel-grants': 'travel-grant.schema.json',
    'resources': 'resource.schema.json',
    'career-levels': 'vocab.schema.json',
    'subjects': 'vocab.schema.json',
    'funding-purposes': 'vocab.schema.json',
    'travel-purposes': 'vocab.schema.json',
    'resource-categories': 'vocab.schema.json',
}


def load_schema(schema_path: Path) -> Optional[Dict[str, Any]]:
    """Load a JSON schema from file. Returns None on failure."""
    if not schema_path.exists():
        print(f"  Warning: schema not found: {schema_path}", file=sys.stderr)
        return None
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"  Error loading schema {schema_path}: {e}", file=sys.stderr)
        return None


def load_yaml_file(path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Load a YAML file.

    Returns (data, None) on success, (None, error_message) on failure.
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            return None, f"Expected a YAML mapping, got {type(data).__name__}"
        return data, None
    except yaml.YAMLError as e:
        return None, f"YAML parse error: {e}"
    except Exception as e:
        return None, f"File read error: {e}"


def validate_file(
    yaml_path: Path,
    schema: Dict[str, Any],
    validator: Draft7Validator,
) -> List[str]:
    """
    Validate a single YAML file against a schema.

    Returns a list of error message strings (empty if valid).
    """
    data, load_error = load_yaml_file(yaml_path)
    if load_error:
        return [load_error]

    errors = []
    for error in sorted(validator.iter_errors(data), key=lambda e: e.path):
        path_str = '.'.join(str(p) for p in error.path) if error.path else '(root)'
        errors.append(f"  Field '{path_str}': {error.message}")
    return errors


def validate_all(
    entries_root: Path,
    schema_root: Path,
) -> Tuple[int, int, int]:
    """
    Validate all YAML files in entries_root against their schemas.

    Returns (total_files, error_files, total_errors).
    """
    total_files = 0
    error_files = 0
    total_errors = 0

    # Cache loaded schemas + validators
    schema_cache: Dict[str, Optional[Draft7Validator]] = {}

    for subdir_name, schema_filename in SCHEMA_MAP.items():
        subdir = entries_root / subdir_name
        if not subdir.exists():
            continue

        schema_path = schema_root / schema_filename
        if schema_filename not in schema_cache:
            schema = load_schema(schema_path)
            if schema:
                schema_cache[schema_filename] = Draft7Validator(schema)
            else:
                schema_cache[schema_filename] = None

        validator = schema_cache.get(schema_filename)
        if not validator:
            print(f"\n  Skipping {subdir_name}/ — schema not available")
            continue

        yaml_files = sorted(subdir.glob('*.yaml'))
        if not yaml_files:
            continue

        print(f"\nValidating {subdir_name}/ ({len(yaml_files)} files) …")
        for yaml_path in yaml_files:
            total_files += 1
            errors = validate_file(yaml_path, {}, validator)
            if errors:
                error_files += 1
                total_errors += len(errors)
                print(f"  FAIL: {yaml_path.name}")
                for err in errors:
                    print(f"    {err}")
            else:
                # Uncomment for verbose output:
                # print(f"  OK:   {yaml_path.name}")
                pass

    return total_files, error_files, total_errors


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Validate YAML entry files against JSON schemas.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        '--entries', default='data/entries/',
        help='Root directory of YAML entry files (default: data/entries/)',
    )
    parser.add_argument(
        '--schema', default='data/schema/',
        help='Directory containing JSON schema files (default: data/schema/)',
    )
    args = parser.parse_args()

    entries_root = Path(args.entries)
    schema_root = Path(args.schema)

    if not entries_root.exists():
        print(f"Error: entries directory not found: {entries_root}", file=sys.stderr)
        sys.exit(1)

    if not schema_root.exists():
        print(f"Error: schema directory not found: {schema_root}", file=sys.stderr)
        sys.exit(1)

    print(f"Validating YAML entries in: {entries_root}")
    print(f"Using schemas from:         {schema_root}")

    total_files, error_files, total_errors = validate_all(entries_root, schema_root)

    print("\n" + "=" * 50)
    print(f"Validation summary:")
    print(f"  Total files checked: {total_files}")
    print(f"  Files with errors:   {error_files}")
    print(f"  Total errors:        {total_errors}")
    print("=" * 50)

    if total_errors > 0:
        print(f"\nFAIL: {total_errors} validation error(s) found.")
        sys.exit(1)
    else:
        print("\nOK: All files valid.")
        sys.exit(0)


if __name__ == '__main__':
    main()
