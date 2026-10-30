# Claims

This repo makes no numbers of its own. Every number on the site comes from another
repo, through `build.py`:

- `projects.toml` names, for each shown number, the source repo, the key in that repo's
  `reports/metrics.json`, and the row in that repo's own `CLAIMS.md` that covers it.
- The build shows a number only when that row exists, covers the key, and already
  holds the same value. Otherwise it stops and deploys nothing.
- `scripts/check_numbers.py` fails if any page's prose in `_build/md/` holds a number
  that the pipeline did not produce.
- `_site/sources.json` records the commit of each source repo that fed the numbers, so
  each one can be traced by hand.

The rules are in [ADR 0002](docs/decisions/0002-where-each-number-comes-from.md).

The table below is for numbers in this repo's own docs. Small whole numbers (0 to 10),
years, dates and version numbers are skipped. To skip one line by hand, add the comment
`<!-- not-a-claim -->` to it.

| Claim | Value | Source | Command |
|---|---|---|---|
| Lowest performance score, mobile preset, over all built pages | 100 | `reports/lighthouse.json#summary.lowest.mobile.performance` | `uv run python scripts/lighthouse_run.py` |
| Lowest accessibility score, mobile preset, over all built pages | 100 | `reports/lighthouse.json#summary.lowest.mobile.accessibility` | `uv run python scripts/lighthouse_run.py` |
| Lowest best practices score, mobile preset, over all built pages | 100 | `reports/lighthouse.json#summary.lowest.mobile.best-practices` | `uv run python scripts/lighthouse_run.py` |
| Lowest seo score, mobile preset, over all built pages | 100 | `reports/lighthouse.json#summary.lowest.mobile.seo` | `uv run python scripts/lighthouse_run.py` |
| Lowest performance score, desktop preset, over all built pages | 100 | `reports/lighthouse.json#summary.lowest.desktop.performance` | `uv run python scripts/lighthouse_run.py` |
| Lowest accessibility score, desktop preset, over all built pages | 100 | `reports/lighthouse.json#summary.lowest.desktop.accessibility` | `uv run python scripts/lighthouse_run.py` |
| Lowest best practices score, desktop preset, over all built pages | 100 | `reports/lighthouse.json#summary.lowest.desktop.best-practices` | `uv run python scripts/lighthouse_run.py` |
| Lowest seo score, desktop preset, over all built pages | 100 | `reports/lighthouse.json#summary.lowest.desktop.seo` | `uv run python scripts/lighthouse_run.py` |
| Lowest accessibility score in dark mode, over all built pages | 100 | `reports/lighthouse.json#summary.lowest.dark.accessibility` | `uv run python scripts/lighthouse_run.py` |
