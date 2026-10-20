# Iliya Valizadeh's site

The source of my portfolio site, built by a small Python script from templates, Markdown and the results files of my project repos.

## In plain words

This repo makes the website at iliya-valizadeh.github.io. A short script turns Markdown pages and a few HTML templates into plain static pages. Every number on the site is read from a project's own results file, so no number is typed by hand.

## Try it

You need Python and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --locked
uv run python build.py --offline
```

The offline build reads saved copies of the results files from `tests/fixtures/`, so it needs no network. Open `_site/index.html` in a browser to look at the result.

Drop `--offline` to read the live results files from GitHub instead. That is what the deploy build does.

## How the checks run

`.github/workflows/ci.yml` runs on every push and pull request. It runs these checks, all offline except the link check:

- ruff for lint and format, and mypy for types
- pytest, with the coverage floor set in `pyproject.toml`, measured on `build.py` and `scripts/`
- the offline build
- the AI-writing signs check, with zero flags allowed
- the readability check, with notes and the "For everyone" pages held to the plain limit and the rest to the general limit set in ADR 0004
- the numbers check, which fails if any page holds a number the build did not fill in from a results file
- the claims check and the local link check
- the draft test, which proves a note marked as a draft is missing from the built site, the Notes index and the feed
- lychee, which checks every link in the built site

`.github/workflows/pages.yml` builds from the live results files and deploys, but only on `main` and only once the repo's Pages source is set to GitHub Actions.

To run the same checks yourself, follow the commands in `ci.yml`. The reasons for each one are in [ADR 0004](docs/decisions/0004-checks.md).

## Where things live

| Path | What |
|---|---|
| `build.py` | The build |
| `projects.toml` | Which projects are shown and which result each number comes from |
| `content/` | The prose of each page, in Markdown |
| `notes/` | One file per note. A note starts with `DRAFT: Iliya to edit` until it is published |
| `templates/`, `partials/`, `static/` | Page shell, page blocks, and files copied unchanged |
| `scripts/` | The numbers check |
| `tools/` | The shared writing and claims checkers, copied unchanged from `ds-project-standard` |
| `tests/` | Offline tests, with saved results files in `tests/fixtures/` |
| `docs/decisions/` | Why the site is built this way |

## What's weak

The site copy is a draft that Iliya has not yet read in full. The three notes are drafts and stay off the built site until he edits them and removes the draft line.

Lighthouse scores are not a CI check, because Lighthouse needs a browser. A separate task measures them on the local build.

## Claims

This repo makes no numbers of its own. See [CLAIMS.md](CLAIMS.md) for how numbers reach the site.
