# Data Model

ECRcentral stores all content as YAML files under `data/entries/`. Each record is one file. Build scripts read those files and produce JSON artifacts consumed by the frontend. This document covers every field, every entity type, the vocabulary system, the JSON artifact format, and the legacy field conventions.


## One-file-per-record approach

Each entry lives at a path like:

```
data/entries/{type}/{slug}.yaml
```

For example:
```
data/entries/fundings/embo-scientific-exchange-grants.yaml
data/entries/funders/embo.yaml
data/entries/travel-grants/gordion-knot-travel-awards.yaml
data/entries/resources/ten-simple-rules-writing-research.yaml
```

The slug in the filename is the canonical identifier. It is used in page URLs, in cross-references between records, and as the unique key in JSON indexes. Slugs are lowercase, hyphenated, ASCII-only, and must be unique within their type.


## Entity types

| Type | Directory | Schema file |
|------|-----------|-------------|
| Funder | `data/entries/funders/` | `data/schema/funder.schema.json` |
| Funding | `data/entries/fundings/` | `data/schema/funding.schema.json` |
| Travel Grant | `data/entries/travel-grants/` | `data/schema/travel-grant.schema.json` |
| Resource | `data/entries/resources/` | `data/schema/resource.schema.json` |
| Vocabulary | `data/entries/vocab/` | `data/schema/vocab.schema.json` |


## Shared fields (all types)

These fields appear on every entry type.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `slug` | string | yes | Unique identifier; must match the filename without `.yaml`. URL-safe, lowercase, hyphenated. |
| `name` | string | yes | Human-readable display name. |
| `status` | enum | yes | Lifecycle status: `active`, `expired`, `archived`, `draft`. Only `active` entries appear in search results by default. |
| `review_status` | enum | yes | Editorial review status: `approved`, `pending`, `rejected`. Only `approved` entries are shown to site visitors. |
| `featured` | boolean | no | When `true`, the entry may appear on the homepage featured section. Default: `false`. |
| `created_at` | date (YYYY-MM-DD) | no | Date the YAML file was first created. |
| `updated_at` | date (YYYY-MM-DD) | no | Date the entry was last meaningfully updated. |
| `notes` | string | no | Internal editorial notes, not shown on the site. |


## Funder

Funders are organizations that offer funding opportunities or travel grants. They are referenced by slug from funding and travel-grant records.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `slug` | string | yes | Unique ID, e.g. `embo`, `wellcome-trust`. |
| `name` | string | yes | Full official name of the organization. |
| `short_name` | string | no | Abbreviated name or acronym, e.g. `EMBO`. Shown in compact UI contexts. |
| `url` | string (URL) | yes | Official website URL. |
| `description` | string | no | One or two sentence description of the organization. |
| `country` | string | no | Country where the funder is headquartered. Use English country names. |
| `region` | string | no | Geographic region: `Europe`, `North America`, `Asia`, `Africa`, `South America`, `Oceania`, `Global`. |
| `funder_type` | enum | no | Organization type: `government`, `charity`, `foundation`, `university`, `professional-society`, `intergovernmental`, `corporate`, `other`. |
| `logo_path` | string | no | Relative path to logo file under `apps/web/public/`, e.g. `logos/funders/embo.png`. |
| `status` | enum | yes | `active`, `archived`. |
| `review_status` | enum | yes | `approved`, `pending`, `rejected`. |
| `featured` | boolean | no | Whether to feature on homepage. |
| `legacy_id` | integer | no | Primary key from the legacy MySQL database. Preserved for traceability. |
| `legacy_logo_path` | string | no | Original logo path from the legacy system. Used during logo migration. |

### Example

```yaml
slug: embo
name: European Molecular Biology Organization
short_name: EMBO
url: https://www.embo.org
description: >
  EMBO is an organization of more than 1,800 leading researchers that promotes
  excellence in life sciences through grants, courses, and scientific exchange programmes.
country: Germany
region: Europe
funder_type: intergovernmental
logo_path: logos/funders/embo.png
status: active
review_status: approved
featured: false
legacy_id: 42
legacy_logo_path: /uploads/funders/embo_logo.png
```


## Funding

Funding opportunities include fellowships, scholarships, research grants, awards, and other financial support for ECRs.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `slug` | string | yes | Unique ID, e.g. `embo-scientific-exchange-grants`. |
| `name` | string | yes | Official name of the funding opportunity. |
| `url` | string (URL) | yes | Link to the application or official page. |
| `description` | string | no | Markdown-supported description of the opportunity. |
| `funders` | array of slug strings | yes | Slugs of funder records that offer this funding. At least one required. |
| `legacy_funder_name` | string | no | Raw funder name string from legacy import; kept when no funder record exists yet. |
| `funding_purposes` | array of vocab slugs | no | What the funding is for. Values from `data/entries/vocab/funding-purpose/`. |
| `career_levels` | array of vocab slugs | no | Who is eligible. Values from `data/entries/vocab/career-level/`. |
| `subjects` | array of vocab slugs | no | Relevant disciplines. Values from `data/entries/vocab/subject/`. |
| `applicant_countries` | array of strings | no | Countries from which applicants are eligible. Use `Worldwide` for no restriction. |
| `host_countries` | array of strings | no | Countries where the funded activity must take place. |
| `award_amount` | string | no | Free-text description of the award, e.g. `Up to EUR 2,500` or `Stipend of USD 30,000/year`. |
| `duration` | string | no | Length of the funded period, e.g. `3–12 months`, `1 year`. |
| `deadline` | string | no | Application deadline description, e.g. `Rolling`, `15 January annually`. |
| `deadline_date` | date (YYYY-MM-DD) | no | Machine-readable next deadline date for sorting and expiry detection. |
| `frequency` | string | no | How often the opportunity recurs: `Annual`, `Bi-annual`, `Rolling`, `One-off`. |
| `membership_required` | boolean | no | Whether membership of the funder organization is required to apply. Default: `false`. |
| `status` | enum | yes | `active`, `expired`, `archived`, `draft`. |
| `review_status` | enum | yes | `approved`, `pending`, `rejected`. |
| `featured` | boolean | no | Feature on homepage. |
| `created_at` | date | no | Date added to ECRcentral. |
| `updated_at` | date | no | Date last updated. |
| `legacy_id` | integer | no | Legacy MySQL primary key. |

### Example

```yaml
slug: embo-scientific-exchange-grants
name: EMBO Scientific Exchange Grants
url: https://www.embo.org/funding-awards/scientific-exchange-grants/
description: >
  EMBO Scientific Exchange Grants support short-term visits by scientists to
  collaborate with colleagues at EMBO Member State institutions. Grants cover
  travel and subsistence for visits of up to three months.
funders:
  - embo
funding_purposes:
  - collaboration
  - research
career_levels:
  - phd
  - postdoc
  - junior-faculty
subjects:
  - life-sciences
applicant_countries:
  - Worldwide
host_countries:
  - EMBO Member States
award_amount: Up to EUR 2,500
duration: Up to 3 months
deadline: Rolling
frequency: Rolling
membership_required: false
status: active
review_status: approved
featured: false
created_at: 2024-01-15
updated_at: 2024-03-01
legacy_id: 318
```

## Travel Grant

Travel grants cover costs associated with attending conferences, workshops, research visits, or other scientific travel.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `slug` | string | yes | Unique ID, e.g. `gordion-knot-conference-travel-award`. |
| `name` | string | yes | Official name of the travel grant. |
| `url` | string (URL) | yes | Link to the application or official page. |
| `description` | string | no | Markdown-supported description. |
| `funders` | array of slug strings | yes | Slugs of offering funders. |
| `legacy_funder_name` | string | no | Raw funder name from legacy import. |
| `travel_purposes` | array of vocab slugs | no | What type of travel is supported. Values from `data/entries/vocab/travel-purpose/`. |
| `career_levels` | array of vocab slugs | no | Eligible career stages. Values from `data/entries/vocab/career-level/`. |
| `subjects` | array of vocab slugs | no | Relevant disciplines. |
| `applicant_countries` | array of strings | no | Countries of eligible applicants. |
| `destination_countries` | array of strings | no | Countries where travel must go. |
| `award_amount` | string | no | Amount or range, e.g. `Up to EUR 1,000`. |
| `deadline` | string | no | Deadline description. |
| `deadline_date` | date (YYYY-MM-DD) | no | Machine-readable deadline. |
| `frequency` | string | no | `Annual`, `Bi-annual`, `Rolling`, `Per event`. |
| `membership_required` | boolean | no | Whether funder membership is required. Default: `false`. |
| `status` | enum | yes | `active`, `expired`, `archived`, `draft`. |
| `review_status` | enum | yes | `approved`, `pending`, `rejected`. |
| `featured` | boolean | no | Feature on homepage. |
| `created_at` | date | no | |
| `updated_at` | date | no | |
| `legacy_id` | integer | no | |

### Example

```yaml
slug: isth-young-investigator-award-travel-grant
name: ISTH Young Investigator Award Travel Grant
url: https://www.isth.org/page/YIA
description: >
  The ISTH Young Investigator Award provides travel support for early career
  researchers to present their work at the ISTH Congress and attend scientific
  sessions in haemostasis and thrombosis.
funders:
  - isth
travel_purposes:
  - conference
career_levels:
  - phd
  - postdoc
subjects:
  - medicine
  - haematology
applicant_countries:
  - Worldwide
award_amount: Up to USD 1,500
deadline: March annually
deadline_date: 2025-03-01
frequency: Annual
membership_required: false
status: active
review_status: approved
featured: false
created_at: 2024-02-10
updated_at: 2024-02-10
legacy_id: 204
```

## Resource

Resources are tools, guides, databases, online courses, or other assets useful to ECRs that are not funding opportunities.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `slug` | string | yes | Unique ID, e.g. `mit-commkit`. |
| `name` | string | yes | Name of the resource. |
| `url` | string (URL) | yes | Where to access the resource. |
| `description` | string | yes | What the resource is and who it is for. |
| `source` | string | yes | Publisher, institution, or author name. |
| `resource_categories` | array of vocab slugs | no | Type of resource. Values from `data/entries/vocab/resource-category/`. |
| `subjects` | array of vocab slugs | no | Relevant disciplines. |
| `career_levels` | array of vocab slugs | no | Who the resource targets. |
| `access` | enum | no | `free`, `subscription`, `registration-required`. Default: `free`. |
| `language` | string | no | Primary language of the resource. Default: `English`. |
| `status` | enum | yes | `active`, `archived`, `draft`. |
| `review_status` | enum | yes | `approved`, `pending`, `rejected`. |
| `featured` | boolean | no | Feature on homepage. |
| `created_at` | date | no | |
| `updated_at` | date | no | |
| `legacy_id` | integer | no | |

### Example

```yaml
slug: mit-commkit
name: MIT CommKit
url: https://mitcommlab.mit.edu/broad/use-the-commkit/
description: >
  A collection of guides on scientific communication produced by MIT's
  Communication Lab. Covers research articles, grant proposals, conference
  abstracts, figures, and oral presentations.
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
review_status: approved
featured: false
created_at: 2024-01-20
updated_at: 2024-01-20
legacy_id: 91
```


## Vocabulary (Taxonomy)

Vocabularies define the controlled lists used in multi-select fields. They live under `data/entries/vocab/{vocab-type}/` as individual YAML files.

### Vocabulary types

| Vocabulary type | Directory | Used by |
|----------------|-----------|---------|
| `career-level` | `data/entries/vocab/career-level/` | fundings, travel-grants, resources |
| `funding-purpose` | `data/entries/vocab/funding-purpose/` | fundings |
| `travel-purpose` | `data/entries/vocab/travel-purpose/` | travel-grants |
| `resource-category` | `data/entries/vocab/resource-category/` | resources |
| `subject` | `data/entries/vocab/subject/` | fundings, travel-grants, resources |
| `funder-type` | `data/entries/vocab/funder-type/` | funders |
| `region` | `data/entries/vocab/region/` | funders |

### Vocabulary record fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `slug` | string | yes | Machine identifier used in entry arrays. |
| `label` | string | yes | Human-readable display label. |
| `description` | string | no | Optional clarification of what belongs in this category. |
| `sort_order` | integer | no | Controls display order in facet lists and checkboxes. |
| `parent` | string | no | Slug of a parent term (for hierarchical vocabularies). |

### Standard career-level slugs

| Slug | Label |
|------|-------|
| `bachelor` | Bachelor students |
| `master` | Master students |
| `phd` | PhD |
| `postdoc` | Postdoc |
| `junior-faculty` | Junior Faculty |
| `senior-faculty` | Senior Faculty |
| `md` | MD |

### Standard funding-purpose slugs

| Slug | Label |
|------|-------|
| `fellowship` | Fellowship, scholarship or training |
| `research` | Research |
| `collaboration` | Collaboration |
| `publishing` | Publishing and editorial |
| `equipment` | Equipment |
| `award` | Award |
| `feasibility` | Feasibility Studies |

### Standard travel-purpose slugs

| Slug | Label |
|------|-------|
| `conference` | Conference |
| `collaboration` | Collaboration |
| `workshop` | Workshop, training or course |
| `research-visit` | Research visit |
| `field-work` | Field work |
| `new-technique` | Learn new technique |

### Standard resource-category slugs

| Slug | Label |
|------|-------|
| `career-development` | Career development |
| `reproducibility` | Reproducibility |
| `science-communication` | Science Communication |
| `academic-writing` | Academic writing |
| `policy` | Policy |
| `preprints` | Preprints |
| `publishing` | Publishing |
| `peer-review` | Peer review |
| `data-management` | Data management |
| `mental-health` | Mental health and wellbeing |
| `networking` | Networking |
| `funding-advice` | Funding advice |
| `other` | Other |

### Vocabulary example

```yaml
# data/entries/vocab/career-level/postdoc.yaml
slug: postdoc
label: Postdoc
description: Postdoctoral researchers, typically within 5 years of PhD completion.
sort_order: 4
```


## Relationships between entities

Funding and travel-grant records reference funders via the `funders` field, which is an array of funder slugs:

```yaml
funders:
  - embo
  - hfsp
```

The build scripts resolve these slugs to full funder objects when generating JSON artifacts. At validation time, `validate_taxonomies.py` checks that every slug in a `funders` array has a matching file in `data/entries/funders/{slug}.yaml`.

Similarly, vocabulary slugs in fields like `career_levels`, `funding_purposes`, and `subjects` are validated against the corresponding vocabulary directories.

## Legacy fields

When content was migrated from the legacy MySQL database, some data could not be cleanly normalized. Legacy fields are preserved in YAML to maintain traceability and allow future clean-up.

| Field | Appears on | Purpose |
|-------|-----------|---------|
| `legacy_id` | all types | Primary key (`id`) from the legacy MySQL table. Allows mapping back to the original database row. |
| `legacy_logo_path` | funders | The original path of the logo on the legacy server (e.g., `/uploads/logos/embo.png`). Used when fetching logos from the legacy server during migration. |
| `legacy_funder_name` | fundings, travel-grants | The raw funder name string from the legacy `company` or `funder` column, preserved when no matching funder YAML record has been created yet. |

Legacy fields are prefixed with `legacy_` to make them visually distinct and to signal that they are not part of the canonical data model. They are ignored by the frontend and the build scripts, but should not be deleted until the migration is fully verified.

---

## Built JSON artifact format

The `scripts/build/` scripts read all YAML files and generate JSON artifacts in `data/built/`. These files are committed to the repository so the site works without a CI build step (GitHub Pages can serve them directly).

Do not edit files in `data/built/` manually — regenerate them with `make build`.

### `data/built/records.json`

A flat array of all approved, active records across all types, fully resolved (vocabulary labels included, funder objects embedded).

```json
[
  {
    "slug": "embo-scientific-exchange-grants",
    "type": "funding",
    "name": "EMBO Scientific Exchange Grants",
    "url": "https://www.embo.org/funding-awards/scientific-exchange-grants/",
    "description": "EMBO Scientific Exchange Grants support...",
    "funders": [
      { "slug": "embo", "name": "European Molecular Biology Organization", "short_name": "EMBO" }
    ],
    "funding_purposes": ["Collaboration", "Research"],
    "career_levels": ["PhD", "Postdoc", "Junior Faculty"],
    "subjects": ["Life Sciences"],
    "award_amount": "Up to EUR 2,500",
    "deadline": "Rolling",
    "status": "active",
    "featured": false
  }
]
```

### `data/built/facets.json`

Aggregated facet counts for the search/filter UI.

```json
{
  "funding_purposes": [
    { "slug": "research", "label": "Research", "count": 412 },
    { "slug": "fellowship", "label": "Fellowship, scholarship or training", "count": 287 }
  ],
  "career_levels": [
    { "slug": "postdoc", "label": "Postdoc", "count": 651 }
  ],
  "subjects": [...],
  "regions": [...]
}
```

### `data/built/search-index.json`

A MiniSearch-compatible JSON index for client-side full-text search. Contains tokenized, weighted fields for name, description, funder names, and subjects.

### `data/built/homepage-featured.json`

A curated array of records where `featured: true`, used to populate the homepage showcase section.

```json
[
  {
    "slug": "embo-scientific-exchange-grants",
    "type": "funding",
    "name": "EMBO Scientific Exchange Grants",
    "funder_name": "EMBO",
    "award_amount": "Up to EUR 2,500"
  }
]
```

### `data/built/funders.json`

Index of all approved funder records, used to resolve funder slugs to display names in the UI.


## Validation rules summary

The validation scripts enforce the following constraints:

- Every YAML file must parse without errors.
- Every record must have `slug`, `name`, `status`, and `review_status`.
- The `slug` must exactly match the filename (without `.yaml`).
- Slugs must be unique within each type directory.
- All funder slugs referenced in `funders` arrays must have a corresponding funder YAML file.
- All vocabulary slugs must have a corresponding vocab YAML file of the correct type.
- All URL fields must be valid HTTP/HTTPS URLs.
- `status` must be one of: `active`, `expired`, `archived`, `draft`.
- `review_status` must be one of: `approved`, `pending`, `rejected`.
- Dates must be in `YYYY-MM-DD` format.
