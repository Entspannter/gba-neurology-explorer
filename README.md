# G-BA Neurology Explorer

Static data pipeline and GitHub Pages frontend for neurologische Projekte aus dem Innovationsfonds des G-BA.

## What This Repo Does

- scrapes the public G-BA Innovationsfonds project index and all detail pages
- stores a full local dataset for every scraped project
- derives a neurology-focused subset by matching the public online filter for `neurologische Erkrankungen`
- distinguishes between projects with an exclusive neurology focus and projects where neurology is one focus among several
- builds a static interactive website with filters, project detail view, and state-based map
- deploys the generated site to GitHub Pages from the committed `docs/` directory

## Live Site

After the first Pages deployment, the site will be available at:

`https://entspannter.github.io/gba-neurology-explorer/`

## Data Source

Primary source:

- [Innovationsfonds Projekte](https://innovationsfonds.g-ba.de/projekte/)

The scraper currently works against the server-rendered HTML project index and the detail pages behind each project entry.

Neurology subset reference:

- [Public G-BA filter for neurologische Erkrankungen](https://innovationsfonds.g-ba.de/projekte/?projektname=&themenschwerpunkt=neurologische+Erkrankungen&zielgruppe=&projektelemente%5BprojektelementGruppe%5D=&projektelemente%5Bprojektelement%5D=&foerderbereich%5Bfoerderbereich%5D=&foerderverfahren%5Bfoerderverfahren%5D=&versorgungsbereich=&bundesland=&status%5Bstatus%5D=&status%5Btransferempfehlung%5D=&sort=projekt.akronym&direction=asc)

## Quick Start

### 1. Create the local environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Refresh data and rebuild the site

```bash
gba-refresh
```

`gba-refresh` now performs the full pipeline:

- scrape or reuse cached HTML
- rebuild all JSON and CSV artifacts
- regenerate `site/data.js`
- mirror the publishable frontend into `docs/` for GitHub Pages

Useful flags:

```bash
gba-refresh --force
gba-refresh --limit 25
gba-refresh --delay 0.05
```

### 3. Preview locally

```bash
python -m http.server 8000 -d site
```

Then open `http://127.0.0.1:8000`.

## Generated Outputs

- `data/projects_all.json`: full structured dataset for all scraped projects
- `data/projects_all.csv`: flattened CSV export
- `data/projects_neurology.json`: neurology subset
- `data/neurology_ui_payload.json`: compact payload for the website
- `site/data.js`: generated browser bundle used by the frontend
- `site/index.html`: static Pages entrypoint
- `docs/`: mirrored publish artifact for GitHub Pages

## Project Structure

```text
src/gba_projects/
  scraper.py        scrape the project index and detail pages
  site_builder.py   transform scraped data into the frontend payload
  refresh.py        run scrape + site build in one command
site/
  *                 source frontend files
docs/
  *                 published GitHub Pages artifact mirrored from site/
data/
  *.json, *.csv     generated datasets committed for deployment
project-docs/
  *.md              repository and operational documentation
```

## Deployment

GitHub Pages is served directly from the `docs/` folder on the default branch. The build step mirrors the current static site from `site/` into `docs/`.

- Source branch: `codex/bootstrap-pages`
- Source folder: `/docs`
- Published URL: `https://entspannter.github.io/gba-neurology-explorer/`

More detail:

- [Architecture Notes](./project-docs/ARCHITECTURE.md)
- [Deployment Notes](./project-docs/DEPLOYMENT.md)
- [Release Notes](./project-docs/RELEASING.md)
- [Contributing Guide](./CONTRIBUTING.md)

## Current Snapshot

The checked-in dataset was generated on March 3, 2026 and currently contains:

- 803 scraped projects in total
- 167 projects returned by the public neurology online filter
- 45 projects with neurology as the only listed thematic focus
- 122 projects where neurology is listed alongside additional thematic focuses
- 0 scrape errors in the latest full run

## Interpretation Of The Neurology Filter

The website defaults to the same project set as the public G-BA online filter for `neurologische Erkrankungen`.

That is important because the source data is broader than a strict one-focus definition:

- some projects list only `neurologische Erkrankungen`
- some projects list `neurologische Erkrankungen` together with other thematic focuses

The frontend therefore includes a dedicated filter called `Neurologie-Definition` so the user can switch between:

- all online-filter matches
- exclusive neurology focus only
- multi-focus neurology projects only

## Automation

A GitHub Actions workflow is included under `.github/workflows/refresh-pages.yml`.

Its intended job is:

- scheduled or manual refresh of the live dataset
- rebuild of the frontend and Pages artifact
- auto-commit of changed data and `docs/`

If pushing workflow files fails, the local GitHub CLI token most likely needs the `workflow` scope:

```bash
gh auth refresh -s workflow
```

## License

This repository is released under the permissive [MIT License](./LICENSE).
