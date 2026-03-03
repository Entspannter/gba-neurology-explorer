# Releasing

## Versioning

Use lightweight semantic versioning for repository releases:

- patch: documentation, styling, scraper robustness, or dataset refreshes without interface changes
- minor: new filters, new exported fields, or frontend features
- major: breaking changes to data shape, commands, or deployment strategy

The package version lives in `pyproject.toml`.

## Release Checklist

1. Run `python3 -m compileall src`.
2. Run `gba-refresh --force`.
3. Review generated changes in `data/`, `site/data.js`, and `docs/`.
4. Update `README.md` snapshot numbers if they changed materially.
5. Commit with a release-oriented message.
6. Create an annotated git tag.
7. Push the branch and tag.

## Example

```bash
git checkout codex/bootstrap-pages
python3 -m compileall src
source .venv/bin/activate
gba-refresh --force
git add .
git commit -m "release: v0.2.0"
git tag -a v0.2.0 -m "v0.2.0"
git push origin codex/bootstrap-pages --follow-tags
```
