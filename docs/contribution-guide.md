# Contribution Guide

ECRcentral is community-maintained. Every funding opportunity, travel grant, and resource in the database was added by a contributor. This guide explains how to add, edit, and report entries — whether you are comfortable with GitHub or not.


## How the site works

All content lives as YAML files in `data/entries/`. There is one file per record. When a change is merged to the `main` branch, GitHub Actions automatically validates the content, rebuilds the JSON search indexes, and deploys the updated site to https://ecrcentral.org.

You do not need to understand the build pipeline to contribute — you only need to edit YAML files.


## Contributing without GitHub knowledge

If you are not comfortable with Git or GitHub, you can submit contributions via GitHub Issue Forms. A maintainer will convert your submission into a YAML file and open a pull request on your behalf.

**Choose the right form:**

- [Add a funding opportunity](https://github.com/ecrcentral/ecrcentral.github.io/issues/new?template=funding.yml)
- [Add a travel grant](https://github.com/ecrcentral/ecrcentral.github.io/issues/new?template=travel-grant.yml)
- [Add a resource](https://github.com/ecrcentral/ecrcentral.github.io/issues/new?template=resource.yml)
- [Report an outdated entry](https://github.com/ecrcentral/ecrcentral.github.io/issues/new?template=outdated-entry.yml)

You will need a free GitHub account. If you do not have one, you can create one at https://github.com/signup.

---

## Contributing via Pull Request (technical workflow)

### 1. Fork and clone the repository

```bash
git clone https://github.com/YOUR-USERNAME/ecrcentral
cd ecrcentral
```

### 2. Install dependencies

```bash
pip install pyyaml jsonschema
cd apps/web && npm install && cd ../..
```

### 3. Create a branch

Use a descriptive branch name:

```bash
git checkout -b add/embo-scientific-exchange-grants
# or
git checkout -b fix/wellcome-trust-url
# or
git checkout -b update/nih-fellowship-deadline
```

### 4. Make your changes

Edit or create YAML files in `data/entries/`. See the sections below for details on each entry type.

### 5. Validate your changes

```bash
make validate
```

This runs three checks:
- Schema validation against `data/schema/*.schema.json`
- Taxonomy reference validation (funder slugs, vocab slugs)
- Duplicate detection

Fix any errors reported before proceeding.

### 6. Rebuild JSON artifacts

```bash
make build
```

This regenerates all files in `data/built/`. Commit these along with your YAML changes.

### 7. Optionally run the site locally

```bash
make dev
# Visit http://localhost:4321
```

### 8. Commit and push

```bash
git add data/entries/fundings/your-new-entry.yaml data/built/
git commit -m "Add: EMBO Scientific Exchange Grants"
git push origin add/embo-scientific-exchange-grants
```

### 9. Open a Pull Request

Go to https://github.com/ecrcentral/ecrcentral.github.io/pulls and open a PR from your branch to `main`. Fill in the PR description with what you added or changed and why.

### 10. Wait for review

A maintainer will review your PR, leave comments if needed, and merge it when it is ready. The site updates automatically within a few minutes of merging.


## Adding a new funding opportunity

### 1. Choose a slug

The slug is a lowercase, hyphen-separated identifier derived from the funding name. It must be unique in `data/entries/fundings/`.

Examples:
- `embo-scientific-exchange-grants`
- `wellcome-trust-research-fellowships`
- `nih-ruth-l-kirschstein-nrsa-f31`

Rules:
- Lowercase ASCII only
- Hyphens between words, no underscores, no spaces
- No punctuation other than hyphens
- Should be recognizable from the funding name
- Should include the funder acronym when the name alone would be ambiguous

### 2. Check whether the funder exists

Look in `data/entries/funders/` for a YAML file matching the funder's slug. If it does not exist, create one first (see "Adding a new funder" below).

### 3. Create the YAML file

Create `data/entries/fundings/{your-slug}.yaml`:

```yaml
slug: your-slug
name: Full Official Name of the Funding
url: https://official-url.org/apply
description: >
  A one to three sentence description of what the funding supports,
  who is eligible, and what it covers.
funders:
  - funder-slug
funding_purposes:
  - research            # or fellowship, collaboration, publishing, equipment, award, feasibility
career_levels:
  - phd
  - postdoc
subjects:
  - life-sciences       # see vocab list in docs/data-model.md
applicant_countries:
  - Worldwide           # or list specific countries
award_amount: "Up to EUR 10,000"
duration: "6–12 months"
deadline: "Rolling"     # or "15 January annually" etc.
frequency: Annual
membership_required: false
status: active
review_status: pending
featured: false
created_at: 2025-01-01  # today's date
```

Set `review_status: pending` — a maintainer will change it to `approved` after verifying the entry.

### 4. Validate and build

```bash
make validate
make build
```

---

## Adding a new travel grant

Travel grants follow the same pattern as fundings, but live in `data/entries/travel-grants/` and use `travel_purposes` instead of `funding_purposes`.

```yaml
slug: isth-young-investigator-travel-award
name: ISTH Young Investigator Award Travel Grant
url: https://www.isth.org/page/YIA
description: >
  Travel support for early career researchers to present at the ISTH Congress.
funders:
  - isth
travel_purposes:
  - conference
career_levels:
  - phd
  - postdoc
subjects:
  - medicine
applicant_countries:
  - Worldwide
award_amount: "Up to USD 1,500"
deadline: "March annually"
frequency: Annual
membership_required: false
status: active
review_status: pending
featured: false
created_at: 2025-01-01
```



## Adding a new resource

Resources live in `data/entries/resources/`. They use `resource_categories` and a `source` field (the publisher or institution) instead of `funders`.

```yaml
slug: mit-commkit
name: MIT CommKit
url: https://mitcommlab.mit.edu/broad/use-the-commkit/
description: >
  A collection of guides on scientific communication from MIT's Communication Lab.
  Covers research articles, grants, abstracts, figures, and oral presentations.
source: MIT Communication Lab
resource_categories:
  - science-communication
  - academic-writing
subjects:
  - all-disciplines
career_levels:
  - phd
  - postdoc
access: free
language: English
status: active
review_status: pending
featured: false
created_at: 2025-01-01
```

## Adding a new funder

If a funder does not yet exist in `data/entries/funders/`, create a file for them:

```yaml
slug: embo
name: European Molecular Biology Organization
short_name: EMBO
url: https://www.embo.org
description: >
  EMBO promotes excellence in life sciences through grants, courses, and
  scientific exchange programmes across Europe and beyond.
country: Germany
region: Europe
funder_type: intergovernmental
status: active
review_status: pending
```

Funder slugs should be short and recognizable: `embo`, `wellcome-trust`, `nih`, `hfsp`, `marie-curie`.

## Editing an existing entry

1. Find the file: `data/entries/{type}/{slug}.yaml`
2. Edit the fields you want to change
3. Update `updated_at` to today's date
4. Run `make validate` and `make build`
5. Commit and open a PR

Common edits:
- Updating a deadline date
- Fixing a broken URL
- Updating the award amount
- Adding missing vocabulary tags
- Correcting a description

## Reporting an outdated entry

If you notice an entry that is out of date but cannot fix it yourself:

1. Open the [outdated entry form](https://github.com/ecrcentral/ecrcentral.github.io/issues/new?template=outdated-entry.yml)
2. Name the entry and describe what is wrong
3. Include the correct information and a source link if possible

A maintainer will update the entry.

## File naming conventions

| Rule | Example |
|------|---------|
| Slug matches filename exactly | `embo-grants.yaml` has `slug: embo-grants` |
| Lowercase only | `wellcome-trust.yaml` not `Wellcome_Trust.yaml` |
| Hyphens between words | `hfsp-research-grants.yaml` |
| No special characters | No `&`, `(`, `)`, `/` in filenames |
| Type-namespaced | Two types can share a slug (e.g., a funder and a funding), filenames within a type must be unique |


## Required vs optional fields

### All types — required

- `slug`
- `name`
- `status`
- `review_status`

### Fundings — required

- `url`
- `funders` (at least one)

### Travel grants — required

- `url`
- `funders` (at least one)

### Resources — required

- `url`
- `description`
- `source`

All other fields are optional but strongly encouraged. The more fields you fill in, the more useful the entry is for search and filtering.


## Running validation locally

```bash
# Validate all YAML against schemas and check references
make validate

# Rebuild JSON artifacts
make build

# Run site dev server
make dev
```

Individual scripts:

```bash
python scripts/validate/validate_yaml.py       # Schema validation
python scripts/validate/validate_taxonomies.py # Funder/vocab slug references
python scripts/validate/validate_duplicates.py # Duplicate detection
python scripts/validate/validate_links.py      # URL format check
```

## Editorial standards checklist

Before opening a PR, verify:

- [ ] The funding/grant/resource is currently active and accepting applications (or will reopen)
- [ ] The URL is the official page (not a third-party aggregator)
- [ ] The description is accurate and written in neutral, factual language
- [ ] Career level eligibility is correctly tagged
- [ ] The entry does not already exist (search the site and `data/entries/`)
- [ ] `make validate` passes with no errors
- [ ] `make build` completes without errors and the `data/built/` files are updated in the commit
- [ ] `review_status` is set to `pending` for new entries


## What happens after you submit a PR

1. **Automated validation** — GitHub Actions runs `make validate` on your PR. If it fails, you will see error details in the Checks tab and need to fix the issues before the PR can be merged.

2. **Maintainer review** — A maintainer will review the content for accuracy and editorial standards. They may leave comments or request changes.

3. **Approval and merge** — Once approved, the maintainer will change `review_status` to `approved` (if it was `pending`) and merge the PR.

4. **Automatic deployment** — GitHub Actions runs `make build` and deploys the updated site. The live site at https://ecrcentral.org is updated within a few minutes.

5. **Credit** — Your GitHub username is recorded in the commit history. If you prefer to be credited differently (e.g., your name), mention this in the PR description.


## Getting help

- Open a [GitHub Discussion](https://github.com/ecrcentral/ecrcentral.github.io/discussions) to ask questions
- Tag your issue or PR with `help wanted` if you are stuck
- Check [docs/data-model.md](docs/data-model.md) for field reference
- Check [docs/editorial-policy.md](docs/editorial-policy.md) for inclusion criteria
