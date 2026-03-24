#!/usr/bin/env python3
"""
Clean description fields in YAML entry files.

For each entry in fundings, travel-grants, and resources:
  1. Strip HTML tags from descriptions
  2. Truncate descriptions >200 words using Claude Haiku (AI summarization)
  3. Fetch descriptions for entries with null/empty descriptions
     using the entry URL + Claude Haiku

Usage:
    pip install anthropic requests beautifulsoup4 pyyaml
    export ANTHROPIC_API_KEY=sk-ant-...
    python scripts/build/clean_descriptions.py
    python scripts/build/clean_descriptions.py --dry-run
"""
import argparse
import re
import sys
import time
from pathlib import Path

import anthropic
import requests
import yaml
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
ENTRY_DIRS = [
    REPO_ROOT / 'data' / 'entries' / 'fundings',
    REPO_ROOT / 'data' / 'entries' / 'travel-grants',
    REPO_ROOT / 'data' / 'entries' / 'resources',
]

MODEL = 'claude-haiku-4-5-20251001'
MAX_WORDS = 200
API_SLEEP = 0.5  # seconds between API calls
FETCH_TIMEOUT = 10
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; ECRcentral/1.0)'}


# ---------------------------------------------------------------------------
# HTML stripping
# ---------------------------------------------------------------------------

HTML_TAG_RE = re.compile(r'<[^>]+>')


def has_html(text: str) -> bool:
    return bool(HTML_TAG_RE.search(text))


def strip_html(text: str) -> str:
    soup = BeautifulSoup(text, 'html.parser')
    return soup.get_text(separator=' ').strip()


# ---------------------------------------------------------------------------
# Word count
# ---------------------------------------------------------------------------

def word_count(text: str) -> int:
    return len(text.split())


# ---------------------------------------------------------------------------
# Claude API helpers
# ---------------------------------------------------------------------------

def ai_summarize(client: anthropic.Anthropic, text: str) -> str:
    """Summarize text to 2-3 sentences (~50 words)."""
    message = client.messages.create(
        model=MODEL,
        max_tokens=200,
        messages=[{
            'role': 'user',
            'content': (
                'Summarize the following in 2-3 sentences (50 words max). '
                'Return only the summary, no preamble or labels:\n\n' + text
            ),
        }],
    )
    return message.content[0].text.strip()


def ai_generate_from_page(client: anthropic.Anthropic, name: str, page_text: str) -> str:
    """Generate a 2-3 sentence description from scraped page content."""
    message = client.messages.create(
        model=MODEL,
        max_tokens=200,
        messages=[{
            'role': 'user',
            'content': (
                f"Write a 2-3 sentence description (50 words max) for '{name}', "
                "a research funding opportunity, based on this webpage content. "
                "Return only the description, no preamble or labels:\n\n"
                + page_text[:3000]
            ),
        }],
    )
    return message.content[0].text.strip()


# ---------------------------------------------------------------------------
# URL fetching
# ---------------------------------------------------------------------------

def fetch_page_text(url: str) -> str | None:
    """
    Fetch a URL and return the best available text:
    meta description > og:description > first paragraphs.
    Returns None on failure.
    """
    try:
        resp = requests.get(url, timeout=FETCH_TIMEOUT, headers=HEADERS)
        resp.raise_for_status()
    except Exception as exc:
        print(f'  [WARN] fetch failed ({url}): {exc}', file=sys.stderr)
        return None

    soup = BeautifulSoup(resp.text, 'html.parser')

    # 1. meta[name=description]
    tag = soup.find('meta', attrs={'name': 'description'})
    if tag and tag.get('content', '').strip():
        return tag['content'].strip()

    # 2. og:description
    tag = soup.find('meta', attrs={'property': 'og:description'})
    if tag and tag.get('content', '').strip():
        return tag['content'].strip()

    # 3. First paragraph text
    paragraphs = [p.get_text(separator=' ').strip() for p in soup.find_all('p') if p.get_text().strip()]
    if paragraphs:
        combined = ' '.join(paragraphs[:5])
        return combined[:500]

    return None


# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------

def load_yaml(path: Path):
    with path.open('r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def dump_yaml(data, path: Path):
    with path.open('w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------

def process_file(path: Path, client: anthropic.Anthropic, dry_run: bool) -> bool:
    """
    Process one YAML file. Returns True if the file was (or would be) modified.
    """
    data = load_yaml(path)
    if data is None:
        return False

    name = data.get('name', path.stem)
    description = data.get('description') or ''
    url = data.get('url', '')
    original = description
    changed = False

    # Step 1: strip HTML
    if description and has_html(description):
        description = strip_html(description)
        print(f'  [HTML] stripped tags from "{name}"')
        changed = True

    # Step 2: truncate if >200 words
    if description and word_count(description) > MAX_WORDS:
        print(f'  [LONG] {word_count(description)} words — summarizing "{name}"')
        if not dry_run:
            try:
                description = ai_summarize(client, description)
                time.sleep(API_SLEEP)
            except Exception as exc:
                print(f'  [WARN] summarize failed: {exc}', file=sys.stderr)
                description = original  # revert
        changed = True

    # Step 3: fetch missing
    if not description:
        if not url:
            print(f'  [SKIP] no description and no URL for "{name}"')
            return False
        print(f'  [MISS] fetching description for "{name}" from {url}')
        if not dry_run:
            page_text = fetch_page_text(url)
            if page_text:
                try:
                    description = ai_generate_from_page(client, name, page_text)
                    time.sleep(API_SLEEP)
                    changed = True
                except Exception as exc:
                    print(f'  [WARN] generate failed: {exc}', file=sys.stderr)
            else:
                print(f'  [SKIP] could not extract page text for "{name}"')
        else:
            changed = True  # would change in non-dry-run

    if changed and description != (original or ''):
        if not dry_run:
            data['description'] = description
            dump_yaml(data, path)
        print(f'  [OK]   updated "{name}"')
        return True

    return False


def main():
    parser = argparse.ArgumentParser(description='Clean descriptions in YAML entry files.')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without writing files')
    args = parser.parse_args()

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    total = modified = skipped = 0

    for entry_dir in ENTRY_DIRS:
        if not entry_dir.exists():
            print(f'[WARN] directory not found: {entry_dir}', file=sys.stderr)
            continue

        yaml_files = sorted(entry_dir.glob('*.yaml'))
        print(f'\nProcessing {len(yaml_files)} files in {entry_dir.name}/')

        for path in yaml_files:
            total += 1
            try:
                was_modified = process_file(path, client, dry_run=args.dry_run)
                if was_modified:
                    modified += 1
            except Exception as exc:
                print(f'  [ERR] {path.name}: {exc}', file=sys.stderr)
                skipped += 1

    mode = '(dry-run) ' if args.dry_run else ''
    print(f'\nDone {mode}— {total} files checked, {modified} modified, {skipped} errors.')
    if args.dry_run:
        print('Re-run without --dry-run to apply changes.')


if __name__ == '__main__':
    main()
