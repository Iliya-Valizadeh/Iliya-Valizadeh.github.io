# Iliya Valizadeh's site

The source of my portfolio site, built by a small Python script from templates, Markdown and the results files of my project repos.

## In plain words

This repo makes the website at iliya-valizadeh.github.io. A short script turns Markdown pages and a few HTML templates into plain static pages: one column, no script. Every number on the site is read from a project's own results file, so no number is typed by hand.

The Home page leads with three projects, each with one result and one chart copied from the project's repo. The page design is in [ADR 0015](docs/decisions/0015-one-plain-column.md). <!-- not-a-claim -->

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
- the writing-style check (`tools/writing_style_check.py`), with zero flags allowed
- the readability check, with notes and the "For everyone" pages held to the plain limit and the rest to the general limit set in ADR 0004
- the numbers check, which fails if any page holds a number the build did not fill in from a results file
- the claims check and the local link check
- the draft test, which proves a note marked as a draft is missing from the built site, the Notes index and the feed
- lychee, which checks every link in the built site. It skips one path, `resume.pdf`, until I add that file (see `lychee.site.toml`)

`.github/workflows/pages.yml` builds from the live results files and deploys, but only on `main` (a push or the "Run workflow" button, with no schedule, see [ADR 0014](docs/decisions/0014-no-scheduled-run-for-pages.md)) and only once the repo's Pages source is set to GitHub Actions. <!-- not-a-claim -->

To run the same checks yourself, follow the commands in `ci.yml`. The reasons for each one are in [ADR 0004](docs/decisions/0004-checks.md).

## Accessibility and speed

The site is one column in a light theme, with no script and no web font. It has a skip link, visible keyboard focus and alt text on every chart. The reasons are in [ADR 0015](docs/decisions/0015-one-plain-column.md), which replaces the dark mode of [ADR 0013](docs/decisions/0013-accessibility-dark-mode-and-lighthouse.md). <!-- not-a-claim -->

Lighthouse scores each page from 0 to 100. The table shows the lowest score across all 6 built pages, measured on the one-column design. The goal is 90 or more in every cell. <!-- not-a-claim -->

| Category | Mobile | Desktop |
|---|---|---|
| Performance | 100 | 100 |
| Accessibility | 100 | 100 |
| Best practices | 100 | 100 |
| SEO | 100 | 100 |
| Accessibility, forced dark mode (desktop preset) | not run | 100 |

The scores are in `reports/lighthouse.json`. To make them again, build the site, then run `uv run python scripts/lighthouse_run.py`. You need Node.js and Chrome. CI does not run it.

What is weak:

- Each score comes from one run on one machine, on the offline build served from my computer. I have not run Lighthouse on the live site.
- My first run on this design gave one page a mobile performance score far below the rest. I was taking browser screenshots on the same machine at the time, so I ran it again with nothing else open. A busy machine can move these scores.
- Lighthouse runs automatic checks only. I have not tested the site with a screen reader.

## Where things live

| Path | What |
|---|---|
| `build.py` | The build |
| `projects.toml` | Which projects are shown and which result each number comes from |
| `content/` | The prose of each page, in Markdown |
| `notes/` | One file per note. A note starts with `DRAFT: Iliya to edit` until it is published |
| `templates/`, `partials/`, `static/` | Page shell, page blocks, and files copied unchanged. `static/charts/` holds the charts copied from each project's repo |
| `scripts/` | The numbers check |
| `tools/` | The shared writing and claims checkers, copied unchanged from `ds-project-standard` |
| `tests/` | Offline tests, with saved results files in `tests/fixtures/` |
| `docs/decisions/` | Why the site is built this way |

## What's weak

The three notes are drafts. They stay off the built site until I edit them and remove the draft line.

The "Resume (PDF)" link points at `resume.pdf`, which is not in the repo yet. Until I add it, that link leads nowhere.

Lighthouse scores are not a CI check, because Lighthouse needs a browser. I measure them by hand on the local build.

## Claims

This repo makes no numbers of its own. See [CLAIMS.md](CLAIMS.md) for how numbers reach the site.
