# Deployment Notes

## GitHub Pages Strategy

The repository uses GitHub Pages from the `docs/` directory on the default branch.

That means:

- `site/` is the maintained source for the frontend
- `docs/` is the publish target mirrored from `site/`

## Operational Flow

To publish updated data:

```bash
source .venv/bin/activate
gba-refresh --force
git add data site docs
git commit -m "Refresh data"
git push
```

GitHub Pages will serve the new `docs/` contents automatically after the push.

## Assumptions

- the repository is hosted on GitHub
- Pages is configured to serve from the default branch and `/docs`
- the committed `docs/` output always matches the current `site/` source

## Failure Modes

- If the source HTML structure changes, `gba-refresh` can fail or produce incomplete fields.
- If the published Pages site is stale, regenerate the local build and push the updated `docs/`.
- If GitHub Pages is disabled in repository settings, re-enable it for branch `codex/bootstrap-pages` and folder `/docs`.

