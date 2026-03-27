# Migration Guide

This document describes how the legacy ECRcentral MySQL database was converted into the YAML-based static site format. It covers the database schema, the import pipeline, logo extraction, known data quality issues, and how to verify the migration.

This was a one-time migration. The scripts in `scripts/import/` are preserved for reference and reproducibility, but are not part of the regular build pipeline.


## Overview

The original ECRcentral site ran on a MySQL-backed PHP application. The database contained approximately:

- 656 funder (organization) records
- 856 funding opportunity records
- 179 travel grant records
- 178 resource records
- Several taxonomy tables (career levels, funding purposes, subjects, etc.)

The migration converts all of this to one YAML file per record in `data/entries/`, with vocabulary terms in `data/entries/vocab/`.

The SQL dump is stored at the repo root:

```
backup_ecrcentral_2026-02-19_103503.sql
```

This file is not committed to the repository's public history (it is listed in `.gitignore` under `scripts/import/raw/`) but is provided to repository maintainers for verification purposes.


## Legacy database schema overview

The following tables were migrated:

### `companies` → `data/entries/funders/`

| Legacy column | YAML field | Notes |
|--------------|------------|-------|
| `id` | `legacy_id` | Preserved for traceability |
| `name` | `name` | Cleaned of HTML entities |
| `website` | `url` | Validated as HTTP/HTTPS |
| `description` | `description` | HTML stripped to plain text |
| `country` | `country` | Normalized to English name |
| `logo` | `legacy_logo_path` | Original path; actual file fetched separately |
| `status` | `status` | Mapped: `1` → `active`, `0` → `archived` |

### `fundings` → `data/entries/fundings/`

| Legacy column | YAML field | Notes |
|--------------|------------|-------|
| `id` | `legacy_id` | |
| `name` | `name` | |
| `url` | `url` | |
| `description` | `description` | HTML stripped |
| `company_id` | `funders` | Resolved to funder slug via `companies.id` lookup |
| `company_name` | `legacy_funder_name` | Kept when `company_id` had no match |
| `career_level` | `career_levels` | Mapped to vocab slugs |
| `funding_purpose` | `funding_purposes` | Mapped to vocab slugs |
| `subject` | `subjects` | Mapped to vocab slugs |
| `country` | `applicant_countries` | Normalized |
| `host_country` | `host_countries` | Normalized |
| `award` | `award_amount` | Free text, kept as-is |
| `duration` | `duration` | Free text |
| `deadline` | `deadline` | Free text |
| `frequency` | `frequency` | Normalized where possible |
| `is_membership` | `membership_required` | Boolean conversion |
| `status` | `status` | Integer → enum |
| `featured` | `featured` | Boolean |

### `travel_grants` → `data/entries/travel-grants/`

Similar structure to `fundings`, with `travel_purpose` in place of `funding_purpose`.

### `resources` → `data/entries/resources/`

| Legacy column | YAML field | Notes |
|--------------|------------|-------|
| `id` | `legacy_id` | |
| `name` | `name` | |
| `url` | `url` | |
| `description` | `description` | HTML stripped |
| `source` | `source` | Publisher/author |
| `category` | `resource_categories` | Mapped to vocab slugs |
| `subject` | `subjects` | |

### Taxonomy tables → `data/entries/vocab/`

The legacy taxonomy values (career levels, funding purposes, etc.) were stored as enum-like integer codes or string constants. These were mapped to named vocab YAML files during import.


## Running the import pipeline

The import is a one-time operation. Do not re-run it against the live YAML content as it will overwrite any manual edits made after the initial migration.

### Prerequisites

```bash
pip install pyyaml mysqlclient python-slugify beautifulsoup4 lxml
```

### Step 1: Parse the SQL dump and extract YAML

```bash
python scripts/import/normalize_legacy_records.py \
  --sql backup_ecrcentral_2026-02-19_103503.sql \
  --output data/entries/
```

This script:
1. Parses the SQL dump (no running MySQL server needed)
2. Normalizes each record
3. Generates slugs from names using `python-slugify`
4. Resolves company IDs to funder slugs
5. Maps taxonomy integer codes to vocab slugs
6. Strips HTML from description fields
7. Writes one YAML file per record

Output summary is printed to stdout, including counts of records written and any records skipped due to missing required fields.

### Step 2: Validate the output

```bash
make validate
```

Review all validation errors. Most will be:
- Missing funder references (records where the original `company_id` pointed to a deleted or null company)
- Invalid URLs (legacy data had many malformed URLs)
- Duplicate slugs (two records with identical names)

### Step 3: Manual clean-up

After import, a round of manual review is needed:
- Fill in missing funder slugs (or use `legacy_funder_name` as a placeholder)
- Fix broken URLs
- Resolve duplicate slugs by appending a distinguishing suffix (e.g., `-2`, `-postdoc`)
- Set `review_status: pending` on all imported records (the import script sets this by default)

### Step 4: Logo extraction

See "Fetching legacy logos" below.

### Step 5: Build and verify

```bash
make build
make dev
```

Browse the site at `http://localhost:4321` and check a sample of records.


## What the import scripts do

### `normalize_legacy_records.py`

The main import script. Responsibilities:
- Reads the SQL dump line-by-line and reconstructs INSERT statements
- Parses the values for each table
- Applies field mappings (see schema overview above)
- Generates slugs using `python-slugify` with collision detection
- Writes YAML files using `pyyaml` with block style for multi-line strings

### `extract_logos.py`

Reads all funder YAML files, collects `legacy_logo_path` values, and writes a mapping file:

```bash
python scripts/import/extract_logos.py
# Output: scripts/import/logo_mapping.json
```

`logo_mapping.json` format:
```json
[
  {
    "funder_slug": "embo",
    "legacy_path": "/uploads/logos/embo_logo.png",
    "target_path": "apps/web/public/logos/funders/embo.png"
  }
]
```

### `fetch_logos.py`

Uses `logo_mapping.json` to download logos from the legacy server:

```bash
python scripts/import/fetch_logos.py \
  --base-url https://legacy.ecrcentral.org \
  --mapping scripts/import/logo_mapping.json \
  --output apps/web/public/logos/funders/
```

This script:
- Downloads each logo via HTTP
- Saves it to the target path
- Skips files that already exist (use `--force` to overwrite)
- Logs 404s and other errors to `scripts/import/logo_fetch_errors.log`


## Fetching legacy logos from the original server

The legacy server hosted logos at paths like `/uploads/logos/embo_logo.png`. To migrate logos:

1. Generate the logo mapping:
   ```bash
   python scripts/import/extract_logos.py
   ```

2. Review `scripts/import/logo_mapping.json` for accuracy.

3. Download logos:
   ```bash
   python scripts/import/fetch_logos.py \
     --base-url https://legacy.ecrcentral.org \
     --mapping scripts/import/logo_mapping.json
   ```

4. Update each funder's YAML to set `logo_path` pointing to the downloaded file:
   ```yaml
   logo_path: logos/funders/embo.png
   ```
   The import script attempts to set this automatically when `legacy_logo_path` is present, but verify the paths are correct.

5. Commit the logos:
   ```bash
   git add apps/web/public/logos/funders/
   git commit -m "Add: funder logos from legacy server"
   ```

Logo files should be:
- PNG or SVG preferred; JPG acceptable
- Named exactly as `{funder-slug}.{ext}`
- Placed in `apps/web/public/logos/funders/`
- Ideally square or landscape, at least 200px wide


## Known data quality issues from the legacy import

The following issues were identified during migration and may require ongoing clean-up:

### 1. Missing funder associations (~12% of fundings)

Some funding records in the legacy database had a `company_id` of `0` or pointed to a deleted company record. These records have `funders: []` and a `legacy_funder_name` string. They should be reviewed and linked to the correct funder record.

Filter these records with:
```bash
python -c "
import yaml, glob
for f in glob.glob('data/entries/fundings/*.yaml'):
    d = yaml.safe_load(open(f))
    if not d.get('funders') and d.get('legacy_funder_name'):
        print(f, d['legacy_funder_name'])
"
```

### 2. Broken or malformed URLs (~8% of records)

The legacy database contained many records with:
- URLs missing the `https://` scheme
- URLs that are now 404
- URLs that were plain text descriptions rather than links

`validate_links.py` will flag format errors. URL reachability is not checked automatically (to avoid slow CI).

### 3. HTML in description fields

Most HTML was stripped during import using BeautifulSoup, but some records may still contain HTML entities (`&amp;`, `&nbsp;`) or leftover tags. Review descriptions for entries that appear garbled.

### 4. Duplicate records (~3% of fundings)

The legacy database had some duplicate entries entered under slightly different names. The `validate_duplicates.py` script uses fuzzy name matching to flag likely duplicates. Review these manually.

### 5. Inconsistent country names

Country names in the legacy data were free text and inconsistent (`UK`, `United Kingdom`, `Great Britain`). The import script normalizes common variants, but unusual country names may still be inconsistent.

### 6. Missing vocabulary mappings

Some legacy taxonomy values did not map cleanly to the new vocabulary. These were left as empty arrays and logged to `scripts/import/unmapped_vocab.log`. Review this file and add the appropriate vocab entries.

### 7. Expired entries included

The legacy data included many entries whose deadlines had passed. These were imported with `status: active` and must be manually reviewed. Set `status: expired` for opportunities that are no longer open.


## Fields preserved vs normalized

| Category | Decision |
|----------|----------|
| `legacy_id` | Preserved on all records |
| `legacy_logo_path` | Preserved on funders |
| `legacy_funder_name` | Preserved on fundings/travel-grants when funder unresolved |
| Description HTML | Stripped to plain text |
| Country names | Normalized to common English names |
| Status integers | Mapped to enum strings |
| Taxonomy integers | Mapped to vocab slugs |
| Award amounts | Kept as free text (not parsed) |
| Deadline text | Kept as free text (not parsed) |
| Slugs | Generated from name using python-slugify |


## Verifying the migration

### Count check

```bash
python scripts/import/verify_migration.py \
  --sql backup_ecrcentral_2026-02-19_103503.sql \
  --entries data/entries/
```

This script compares the count of records in the SQL dump to the count of YAML files and reports any discrepancy.

Expected output:
```
Funders:    SQL=656  YAML=656  OK
Fundings:   SQL=856  YAML=856  OK
Travel:     SQL=179  YAML=179  OK
Resources:  SQL=178  YAML=178  OK
```

### Spot-check

For a manual spot-check, pick 10–20 records at random from the SQL dump and verify that their YAML counterparts have the correct data. Pay particular attention to:
- Name (no truncation or encoding issues)
- URL (correct and well-formed)
- Funder association (correct slug or correct `legacy_funder_name`)
- Description (readable, no HTML artifacts)

### Validation

```bash
make validate
```

A clean migration should produce zero errors from `validate_yaml.py` and `validate_taxonomies.py`. `validate_duplicates.py` may still report suspected duplicates that require human judgement.
