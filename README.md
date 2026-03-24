# ECRcentral

> Funding opportunities, travel grants, and resources for early career researchers.

ECRcentral is a community-maintained, open-source database of funding opportunities, travel grants, and scientific resources for early career researchers (ECRs) worldwide. The site is fully static, hosted on GitHub Pages, and free to maintain — every entry is a YAML file that anyone can contribute to via a GitHub Pull Request.

**Live site**: https://ecrcentral.org
**GitHub**: https://github.com/ecrcentral/ecrcentral.github.io


**Tech stack:**
- Frontend: [Astro](https://astro.build) + TypeScript + CSS
- Search: [MiniSearch](https://lucaong.github.io/minisearch/) (client-side)
- Content: YAML (one file per record)
- Hosting: GitHub Pages (free)
- CI/CD: GitHub Actions


## Local Development

### Prerequisites

- Node.js 20+
- Python 3.11+
- `pip install pyyaml jsonschema`

### Setup

```bash
git clone https://github.com/ecrcentral/ecrcentral.github.io
cd ecrcentral

# Install frontend dependencies
cd apps/web && npm install && cd ../..

# Build JSON artifacts from YAML content
make build

# Start development server
make dev
```

Visit `http://localhost:4321`


## Content Workflow

### Editing an existing entry

1. Find the YAML file in `data/entries/{type}/{slug}.yaml`
2. Edit the file
3. Run `make validate` to check for errors
4. Run `make build` to regenerate JSON artifacts
5. Open a Pull Request

### Adding a new entry

1. Create a new YAML file following the schema in `data/schema/`
2. Use the existing entries as examples
3. Run `make validate` and `make build`
4. Open a Pull Request

### Contributing without GitHub knowledge

Use our [GitHub Issue Forms](https://github.com/ecrcentral/ecrcentral.github.io/issues/new/choose):
- [Add a funding opportunity](https://github.com/ecrcentral/ecrcentral.github.io/issues/new?template=funding.yml)
- [Add a travel grant](https://github.com/ecrcentral/ecrcentral.github.io/issues/new?template=travel-grant.yml)
- [Add a resource](https://github.com/ecrcentral/ecrcentral.github.io/issues/new?template=resource.yml)
- [Report an outdated entry](https://github.com/ecrcentral/ecrcentral.github.io/issues/new?template=outdated-entry.yml)


## Build System


### Build

Generates JSON artifacts from YAML content:

```bash
make build
# Runs: build_records.py, build_facets.py, build_search_index.py, build_homepage_featured.py
```

### Validate

```bash
make validate
# Runs: validate_yaml.py, validate_taxonomies.py, validate_duplicates.py
```

### Build Site

```bash
make build-site
# Equivalent to: make build && cd apps/web && npm run build
```


## Data Model

See [docs/data-model.md](docs/data-model.md) for full field reference.

### Entry types

| Type | Directory | Count | Schema |
|------|-----------|-------|--------|
| Funders | `data/entries/funders/` | ~656 | `data/schema/funder.schema.json` |
| Fundings | `data/entries/fundings/` | ~856 | `data/schema/funding.schema.json` |
| Travel Grants | `data/entries/travel-grants/` | ~179 | `data/schema/travel-grant.schema.json` |
| Resources | `data/entries/resources/` | ~178 | `data/schema/resource.schema.json` |

### Key fields

- `slug` — unique identifier used in URLs (e.g., `embo-scientific-exchange-grants`)
- `status` — `active`, `expired`, `archived`, `draft`
- `review_status` — `approved`, `pending`, `rejected`
- `featured` — shown on homepage when `true`
- `funders` — array of funder slugs (references `data/entries/funders/`)


## Deployment

The site deploys automatically to GitHub Pages when code is pushed to `main`.

GitHub Actions workflows:
1. **validate.yml** — runs on every push/PR: validates YAML, checks taxonomy references, detects duplicates
2. **build.yml** — builds JSON artifacts and Astro site
3. **deploy-pages.yml** — deploys to GitHub Pages on `main`

### Manual deployment

```bash
make build-site
# Then upload apps/web/dist/ to any static host
```

## Logo Assets

Funder logos should be placed in `apps/web/public/logos/funders/` named as `{funder-slug}.{ext}`.


## Contributing

See [docs/contribution-guide.md](docs/contribution-guide.md) for detailed contributing instructions.

All contributions are welcome! ECRcentral is community-maintained — the more contributors, the better the data quality.


## License

MIT — see [LICENSE](LICENSE)

ECRcentral content (YAML files in `data/entries/`) is shared under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
