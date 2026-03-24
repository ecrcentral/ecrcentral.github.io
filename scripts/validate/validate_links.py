#!/usr/bin/env python3
"""
Validate URL fields in YAML entry files.

Checks:
  1. All 'url' fields are syntactically valid (http:// or https://, parseable)
  2. Optionally performs HTTP HEAD requests if --check-http is passed

Exit code: 0 if all URLs valid, 1 if malformed URLs found.

Usage:
    python validate_links.py
    python validate_links.py --entries data/entries/ --check-http
    python validate_links.py --entries data/entries/ --check-http --timeout 10
"""
import sys
import argparse
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


# Entity types with URL fields and which field to check
URL_FIELDS: Dict[str, List[str]] = {
    'fundings': ['url'],
    'travel-grants': ['url'],
    'resources': ['url'],
    'funders': ['website'],
}

HTTP_TIMEOUT_DEFAULT = 10  # seconds


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


def is_valid_url(url: str) -> bool:
    """
    Check that a URL is syntactically valid.

    Requires http:// or https:// scheme and a non-empty netloc.
    """
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    if not (url.startswith('http://') or url.startswith('https://')):
        return False
    try:
        parsed = urllib.parse.urlparse(url)
        return bool(parsed.scheme in ('http', 'https') and parsed.netloc)
    except Exception:
        return False


def check_url_http(url: str, timeout: int = HTTP_TIMEOUT_DEFAULT) -> Tuple[bool, str]:
    """
    Perform an HTTP HEAD request to verify the URL is reachable.

    Returns (ok, message).
    """
    try:
        req = urllib.request.Request(url, method='HEAD')
        req.add_header('User-Agent', 'ECRcentral-validator/1.0')
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = resp.status
            if code < 400:
                return True, f"HTTP {code}"
            else:
                return False, f"HTTP {code}"
    except urllib.error.HTTPError as e:
        if e.code in (405, 403):
            # 405 Method Not Allowed for HEAD is common; try GET
            try:
                req2 = urllib.request.Request(url, method='GET')
                req2.add_header('User-Agent', 'ECRcentral-validator/1.0')
                with urllib.request.urlopen(req2, timeout=timeout) as resp2:
                    code = resp2.status
                    return code < 400, f"HTTP {code} (GET fallback)"
            except Exception as e2:
                return False, f"HTTP error {e.code}, GET also failed: {e2}"
        return False, f"HTTP error {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return False, f"URL error: {e.reason}"
    except Exception as e:
        return False, f"Error: {e}"


# ---------------------------------------------------------------------------
# Validation functions
# ---------------------------------------------------------------------------

def validate_entity_urls(
    entries_root: Path,
    entity_type: str,
    url_fields: List[str],
    check_http: bool = False,
    timeout: int = HTTP_TIMEOUT_DEFAULT,
) -> Tuple[int, int, int]:
    """
    Validate URLs for all YAML files in an entity directory.

    Returns (files_checked, malformed_count, http_error_count).
    """
    entity_dir = entries_root / entity_type
    if not entity_dir.exists():
        return 0, 0, 0

    files = sorted(entity_dir.glob('*.yaml'))
    if not files:
        return 0, 0, 0

    print(f"\nValidating {entity_type}/ ({len(files)} files) …")

    malformed_count = 0
    http_error_count = 0

    for yaml_path in files:
        record = load_yaml_file(yaml_path)
        if not record:
            continue

        for field in url_fields:
            url = record.get(field)
            if not url:
                # Skip null/empty URLs (nullable field)
                continue

            url = str(url).strip()

            if not is_valid_url(url):
                malformed_count += 1
                print(f"  MALFORMED [{field}]: {yaml_path.name}")
                print(f"    Value: {url!r}")
                continue

            if check_http:
                ok, msg = check_url_http(url, timeout=timeout)
                if not ok:
                    http_error_count += 1
                    print(f"  HTTP FAIL [{field}]: {yaml_path.name}")
                    print(f"    URL: {url}")
                    print(f"    Reason: {msg}")
                # else:
                #     print(f"  OK [{field}]: {url} — {msg}")  # verbose

    return len(files), malformed_count, http_error_count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Validate URL fields in YAML entry files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        '--entries', default='data/entries/',
        help='Root directory of YAML entry files (default: data/entries/)',
    )
    parser.add_argument(
        '--check-http', action='store_true',
        help='Perform HTTP HEAD checks on all URLs (slow — use sparingly)',
    )
    parser.add_argument(
        '--timeout', type=int, default=HTTP_TIMEOUT_DEFAULT,
        help=f'HTTP request timeout in seconds (default: {HTTP_TIMEOUT_DEFAULT})',
    )
    args = parser.parse_args()

    entries_root = Path(args.entries)

    if not entries_root.exists():
        print(f"Error: entries directory not found: {entries_root}", file=sys.stderr)
        sys.exit(1)

    print(f"Validating URLs in: {entries_root}")
    if args.check_http:
        print(f"HTTP checks ENABLED (timeout: {args.timeout}s)")
    else:
        print("HTTP checks disabled (use --check-http to enable)")

    total_files = 0
    total_malformed = 0
    total_http_errors = 0

    for entity_type, url_fields in URL_FIELDS.items():
        files, malformed, http_errors = validate_entity_urls(
            entries_root, entity_type, url_fields,
            check_http=args.check_http, timeout=args.timeout,
        )
        total_files += files
        total_malformed += malformed
        total_http_errors += http_errors

    print("\n" + "=" * 50)
    print(f"Link validation summary:")
    print(f"  Total files checked:   {total_files}")
    print(f"  Malformed URLs:        {total_malformed}")
    if args.check_http:
        print(f"  HTTP errors:           {total_http_errors}")
    print("=" * 50)

    if total_malformed > 0:
        print(f"\nFAIL: {total_malformed} malformed URL(s) found.")
        sys.exit(1)
    elif args.check_http and total_http_errors > 0:
        print(f"\nWARN: {total_http_errors} URL(s) returned HTTP errors.")
        # HTTP errors are warnings, not hard failures — don't exit 1
        sys.exit(0)
    else:
        print("\nOK: All URLs syntactically valid.")
        sys.exit(0)


if __name__ == '__main__':
    main()
