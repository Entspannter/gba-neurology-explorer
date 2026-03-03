# Architecture Notes

## Pipeline

The project is intentionally simple:

1. `gba-refresh` calls the live scraper.
2. The scraper walks the paginated G-BA index and caches the HTML under `data/cache/`.
3. Each detail page is normalized into a structured project record.
4. A second pass compares every project URL against the public G-BA neurology filter.
5. `site_builder.py` creates a frontend-friendly payload for neurology exploration.
6. The static site loads `site/data.js` and the same publishable files are mirrored into `docs/` for GitHub Pages.

## Scraper

Entry point:

- `src/gba_projects/scraper.py`

Key behaviors:

- parses pagination from the server-rendered project index
- follows every detail page under `/projekte/`
- extracts project metadata, funding information, lead contact block, project partners, documents, and description text
- handles singular and plural source labels such as `Themenschwerpunkt/Themenschwerpunkte`
- writes both full and neurology-only exports
- classifies neurology matches into `exclusive` and `multiple`

## Frontend

Entry point:

- `site/app.js`

Key behaviors:

- renders the map tiles from the generated payload
- keeps filters, search, list view, and detail panel in sync
- exposes a `Neurologie-Definition` filter that separates strict and multi-focus matches
- handles special source cases such as `bundesweit` and projects without any `Bundesland`

## Publish Layout

- `site/` is the editable frontend source
- `docs/` is the committed Pages artifact

This split keeps GitHub Pages simple while preserving a clear working directory for the frontend source.

## Why The Site Is Static

The source website is already public and server-rendered, so a client-side API layer is not needed here. Committing the generated dataset makes the GitHub Pages deployment deterministic and keeps the published site fast.

## Tradeoffs

- Pros: cheap hosting, easy publishing, reproducible output, simple maintenance
- Cons: the site is only as fresh as the last committed scrape
