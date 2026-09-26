# 0001: A small Python build, deployed by GitHub Actions from main

Date: 2026-09-26. Status: accepted.

## Context

The site is one hand-written `index.html` with two in-browser demos, two project
cards and an About section, plus Google's site-verification file
`googleb968c9a0c91c49c6.html`. GitHub Pages serves the repo root of `main` as it is.
There is no build and no CI.

Plan section `5.7` asks for more: a Home page, a case-study page per project, a page
for the public tool, Notes with an RSS feed, and About and contact. The numbers must
be the same synced numbers as the profile, read at build time. The site must be fast,
static and free of heavy frameworks.

## Options

1. Keep writing HTML by hand. Numbers would be typed, and every shared header would be
   copied into every page.
2. A static site generator such as Jekyll, Hugo or MkDocs. Each brings its own
   language, theme rules and many packages, which is a lot for a few pages.
3. One small Python script, `build.py`, that turns Markdown pages into HTML with a few
   templates.

## Decision

Option 3.

Layout of the repo:

- `build.py`: the build. It reads the config, fetches the numbers, drops drafts, fills
  placeholders, turns Markdown into HTML and writes the output.
- `projects.toml`: the projects shown and the numbers each page uses
  ([ADR 0002](0002-where-each-number-comes-from.md)).
- `content/`: one Markdown file per page. All prose lives here, so the writing checks
  can read it.
- `notes/`: one Markdown file per note.
- `templates/`: HTML page shells with `{{ name }}` placeholders. They hold markup and
  short labels only, never paragraphs of prose.
- `partials/`: HTML kept word for word from the old page (the About section and the
  two demos), see [ADR 0006](0006-text-kept-word-for-word-and-the-old-page.md).
- `static/`: the shared stylesheet, scripts and images.

Build details:

- The only package the build needs is `markdown-it-py`, pinned in `uv.lock`. Page
  shells use the same small `{{ name }}` substitution as the profile repo. It fails on
  an unknown placeholder and escapes every value unless the value is HTML that the
  build made itself.
- Output goes to `_site/` (what is deployed) and `_build/md/` (every page as filled-in
  Markdown, drafts included, for the writing and number checks). Both folders are in
  `.gitignore`.
- The build copies into `_site/` only what it made plus `static/` and the
  verification file. It never copies `docs/`, `tests/`, `notes/` source or anything
  else by accident.
- `googleb968c9a0c91c49c6.html` stays at the repo root and is copied byte for byte to
  the root of `_site/`.
- `--offline` reads the committed fixture copies in `tests/fixtures/` instead of the
  network. CI and tests use it.
- Python `3.11`, `pyproject.toml` and a committed `uv.lock`, as in the other repos.

Deploying:

- `.github/workflows/pages.yml` runs on pushes to `main`, on a daily schedule and on
  `workflow_dispatch`. It never runs on other branches, and its deploy job also checks
  that the ref is `refs/heads/main`.
- A first job asks the Pages API whether the site's Pages source is "GitHub Actions".
  If not, the other jobs are skipped, not failed. This follows the pattern in
  `second-look`'s `pages.yml`.
- The build job installs with `uv sync --locked`, builds from the live source files,
  runs the checks in [ADR 0004](0004-checks.md), and uploads `_site/` with
  `actions/upload-pages-artifact`. The deploy job uses `actions/deploy-pages`.
  Permissions are `contents: read`, `pages: write` and `id-token: write`. The workflow
  commits nothing.
- The daily run is how the site's numbers stay in sync with the project repos. If a
  live build fails a check, nothing is deployed and the last good site stays up.

Switching over:

- The Pages source stays "Deploy from a branch" until the merge task at the end of
  this phase. That task merges to `main`, then switches the source with
  `gh api -X PUT repos/Iliya-Valizadeh/Iliya-Valizadeh.github.io/pages -f build_type=workflow`,
  then runs the workflow by hand and checks the live site and the verification file
  with `curl`.
- Between the merge and the first Actions deploy, the branch source would serve a repo
  root that no longer has an `index.html`. The merge task keeps that gap to a few
  minutes by switching right after the merge. This is a known cost, written down here
  so it is not a surprise.

## Consequences

- Numbers on the site are never typed. A redeploy picks up changes in the source
  repos.
- Adding a page means adding one Markdown file and, if it has numbers, entries in
  `projects.toml`.
- The build is plain Python, so it is tested like the rest of the portfolio.
- The site now depends on a workflow. If Actions is down, the last deploy stays up.
