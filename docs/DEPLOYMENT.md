# Deployment Notes

## GitHub Pages Strategy

The repository deploys the static frontend from `site/` via GitHub Actions.

Workflow:

1. Checkout repository
2. Configure Pages
3. Upload `site/` as the Pages artifact
4. Deploy with `actions/deploy-pages`

## Operational Flow

To publish updated data:

```bash
source .venv/bin/activate
gba-refresh --force
git add data site/data.js
git commit -m "Refresh data"
git push
```

GitHub Actions will automatically publish the updated frontend.

## Assumptions

- the repository is hosted on GitHub
- Pages is served from GitHub Actions
- the committed `site/data.js` is the exact data artifact to publish

## Failure Modes

- If the source HTML structure changes, `gba-refresh` can fail or produce incomplete fields.
- If a deployment fails, inspect the `Deploy GitHub Pages` workflow logs in Actions.
- If the site loads but has outdated data, regenerate `data/` and `site/data.js` locally and push a new commit.

