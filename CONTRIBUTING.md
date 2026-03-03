# Contributing

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Typical Change Flow

1. Create or switch to a working branch.
2. Make code or frontend changes in `src/` and `site/`.
3. Rebuild generated artifacts with `gba-refresh` or `gba-build-site`.
4. Review the generated changes in `data/`, `site/data.js`, and `docs/`.
5. Commit code and generated outputs together.

## Commands

Refresh the live dataset and GitHub Pages artifact:

```bash
gba-refresh
```

Rebuild the frontend payload from an existing local dataset:

```bash
gba-build-site
```

Basic syntax check:

```bash
python3 -m compileall src
```

## Data Semantics

The default neurology dataset follows the public G-BA online filter for `neurologische Erkrankungen`.

Please preserve that behavior unless the repository explicitly changes scope. If you change the classification logic, update:

- `README.md`
- `project-docs/ARCHITECTURE.md`
- `project-docs/DEPLOYMENT.md`
- the frontend copy in `site/index.html` and `site/app.js`

## Generated Files

These files are generated and should usually be committed when they change:

- `data/projects_all.json`
- `data/projects_all.csv`
- `data/projects_neurology.json`
- `data/neurology_ui_payload.json`
- `site/data.js`
- `docs/`

## Pull Requests

Keep pull requests narrow and include:

- what changed
- whether the scrape logic changed
- whether generated outputs were refreshed
- any known source-site assumptions or breakage risks
