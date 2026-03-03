# G-BA Neurology Explorer

Static data pipeline and GitHub Pages frontend for neurologische Projekte aus dem Innovationsfonds des G-BA.

## What This Repo Does

- scrapes the public G-BA Innovationsfonds project index and all detail pages
- stores a full local dataset for every scraped project
- derives a neurology-focused subset from the live source data
- builds a static interactive website with filters, project detail view, and state-based map
- deploys the generated site to GitHub Pages from the `site/` directory

## Live Site

After the first Pages deployment, the site will be available at:

`https://entspannter.github.io/gba-neurology-explorer/`

## Data Source

Primary source:

- [Innovationsfonds Projekte](https://innovationsfonds.g-ba.de/projekte/)

The scraper currently works against the server-rendered HTML project index and the detail pages behind each project entry.

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

## Project Structure

```text
src/gba_projects/
  scraper.py        scrape the project index and detail pages
  site_builder.py   transform scraped data into the frontend payload
  refresh.py        run scrape + site build in one command
site/
  index.html        static frontend shell
  styles.css        UI styling
  app.js            map, filters, and detail interactions
data/
  *.json, *.csv     generated datasets committed for deployment
```

## Deployment

GitHub Pages is deployed with GitHub Actions. The workflow publishes the contents of `site/` as the final Pages artifact.

- Workflow file: `.github/workflows/deploy-pages.yml`
- Trigger: pushes to the default branch and manual runs
- Output: GitHub Pages site

More detail:

- [Architecture Notes](./docs/ARCHITECTURE.md)
- [Deployment Notes](./docs/DEPLOYMENT.md)

## Current Snapshot

The checked-in dataset was generated on March 3, 2026 and currently contains:

- 803 scraped projects in total
- 122 neurology projects
- 0 scrape errors in the latest full run

