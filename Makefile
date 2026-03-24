.PHONY: build validate logos dev build-site all

build:
	python scripts/build/build_records.py
	python scripts/build/build_facets.py
	python scripts/build/build_search_index.py
	python scripts/build/build_homepage_featured.py

validate:
	python scripts/validate/validate_yaml.py
	python scripts/validate/validate_taxonomies.py
	python scripts/validate/validate_duplicates.py

logos:
	python scripts/import/extract_logos.py

dev: build
	cd apps/web && npm run dev

build-site: build
	cd apps/web && npm run build

all: validate build build-site
