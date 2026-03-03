# Architecture Notes

## Pipeline

The project is intentionally simple:

1. `gba-refresh` calls the live scraper.
2. The scraper walks the paginated G-BA index and caches the HTML under `data/cache/`.
3. Each detail page is normalized into a structured project record.
4. `site_builder.py` creates a frontend-friendly payload for neurology-only exploration.
5. The static site loads `site/data.js` and renders the UI entirely in the browser.

## Scraper

Entry point:

- `src/gba_projects/scraper.py`

Key behaviors:

- parses pagination from the server-rendered project index
- follows every detail page under `/projekte/`
- extracts project metadata, funding information, lead contact block, project partners, documents, and description text
- writes both full and neurology-only exports

## Frontend

Entry point:

- `site/app.js`

Key behaviors:

- renders the map tiles from the generated payload
- keeps filters, search, list view, and detail panel in sync
- handles special source cases such as `bundesweit` and projects without any `Bundesland`

## Why The Site Is Static

The source website is already public and server-rendered, so a client-side API layer is not needed here. Committing the generated dataset makes the GitHub Pages deployment deterministic and keeps the published site fast.

## Tradeoffs

- Pros: cheap hosting, easy publishing, reproducible output, simple maintenance
- Cons: the site is only as fresh as the last committed scrape

