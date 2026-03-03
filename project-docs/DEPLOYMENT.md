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

`gba-refresh` is the canonical command because it refreshes both data and the mirrored Pages output.

## GitHub Actions

The repository also includes `.github/workflows/refresh-pages.yml` for scheduled and manual refreshes.

The workflow:

- sets up Python 3.11
- installs the package in editable mode
- runs `gba-refresh --force`
- commits changed datasets and `docs/` back to the default branch

Pushing that workflow file requires a GitHub token with the `workflow` scope.

## Assumptions

- the repository is hosted on GitHub
- Pages is configured to serve from the default branch and `/docs`
- the committed `docs/` output always matches the current `site/` source

## Failure Modes

- If the source HTML structure changes, `gba-refresh` can fail or produce incomplete fields.
- If the published Pages site is stale, regenerate the local build and push the updated `docs/`.
- If `docs/` is stale but `site/` is current, run `gba-build-site`.
- If GitHub Pages is disabled in repository settings, re-enable it for branch `codex/bootstrap-pages` and folder `/docs`.
