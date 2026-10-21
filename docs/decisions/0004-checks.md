# 0004: The checks this repo runs

Date: 2026-09-26. Status: accepted.

## Context

Every repo in the portfolio runs the same writing and number checks. They live in
`ds-project-standard/tools` and read Markdown. This repo is a website, not a data
science project, so parts of the house standard do not fit it: it has neither a model
nor a dataset, and its README is not a project README. Its output is HTML.

Two rules are special to Phase E. The profile's Hack the North line must not change,
and nothing about Hack the North may be added anywhere, including this site. The site
has no text about it today, and the old page has none either.

## Options

For the checkers:

1. Generate this repo from the `ds-project-standard` template with `copier`. The
   template brings a project layout, `src/`, a model card and a datasheet, none of
   which fit a website.
2. Write new, smaller checkers here. They would drift from the rules every other repo
   follows.
3. Copy the checker files from `ds-project-standard/tools` as they are, note the source
   commit, and add a test that fails if a copy is edited.

## Decision

Checkers: option 3. These files are copied byte for byte from `ds-project-standard` at
commit `602ec779782c7466703a2093832e0e091c3316b8`: `tools/_markdown.py`,
`tools/ai_signs_check.py`, `tools/readability_check.py`, `tools/claims_check.py`,
`tools/links_check.py` and `tools/lychee.toml`. `tools/readme_sections.py` is not
copied, because no file here uses the project README layout. `tools/SOURCE.json`
records the source commit and the SHA-256 of each file, and a test fails if any copy
differs. `tools/README.md` says not to edit them here.

The writing checks read Markdown, so they run on `_build/md/`, where the build writes
every page and note as filled-in Markdown, drafts included. Drafts are checked too,
because Iliya should get clean drafts to edit.

The gates, run in `ci.yml` on every push and pull request with `--offline`, and again
in `pages.yml` on the live build before deploying:

| Gate | Command, in short | Scope |
|---|---|---|
| Lint and format | `ruff check`, `ruff format --check` | `build.py`, `scripts/`, `tests/` |
| Types | `mypy` | `build.py`, `scripts/` |
| Tests | `pytest` with coverage of `build.py` and `scripts/` at `80%` or more, offline | `tests/` <!-- not-a-claim --> |
| Build | `python build.py --offline` | writes `_site/` and `_build/md/` |
| AI signs | `tools/ai_signs_check.py`, zero flags | `_build/md/`, `README.md`, `docs/` |
| Readability | `tools/readability_check.py`, notes and the "For everyone" page at grade `9` or below, the rest at `12` or below | `_build/md/`, `README.md`, `docs/` <!-- not-a-claim --> |
| Numbers | `scripts/check_numbers.py` ([ADR 0002](0002-where-each-number-comes-from.md)) | `_build/md/` |
| Claims in docs | `tools/claims_check.py` with this repo's `CLAIMS.md` | `README.md`, `docs/` |
| Local links | `tools/links_check.py` | `README.md`, `docs/` |
| Site links | `lychee --config tools/lychee.toml` over `_site/`, which covers links between pages and to other sites | `_site/` |

Tests that are specific to this site, all offline:

- Drafts: a note or section marked as a draft is missing from `_site/`, the Notes
  index, `feed.xml` and `notes.json`
  ([ADR 0005](0005-drafts-stay-out-of-the-site-and-feed.md)).
- Verification file: `_site/googleb968c9a0c91c49c6.html` has the SHA-256
  `6aeaef4372c8319c6cb681646cad909eac9f38c37143c932edf74a4688cd57ef`, the same as the
  file at commit `efa1a03`.
- Kept text: the About section and the two demos match the archived page
  ([ADR 0006](0006-text-kept-word-for-word-and-the-old-page.md)).
- Hack the North guard: the regular expression `hack\W*the\W*north`, ignoring case,
  matches nothing in `_site/`, `_build/md/`, `content/`, `notes/`, `templates/`,
  `partials/`, `static/`, `projects.toml`, `README.md` or `docs/archive/`. The site
  has no such text today, so any match means something was added. Decision records
  and the test file itself are not scanned, because they name the rule.
- The `second-look` page never contains the word "fraud", in any case.
- `_site/` contains no `{{`, so no placeholder was left unfilled.
- Every project in `projects.toml` has fixture files, so no entry can point at a repo
  that has no data.

Lighthouse is not a CI gate, because it needs a browser. The accessibility task runs
it on the local build and records the scores in `reports/lighthouse.json`.

## Consequences

- The writing rules here are the same rules every project repo follows.
- Prose that sits in HTML templates would escape the writing checks. That is why
  templates hold markup and short labels only, as
  [ADR 0001](0001-a-small-python-build-deployed-by-actions.md) says. The verbatim
  partials are not rewritten in this phase, so the writing checks do not read them.
  If a later reading finds a problem in them, it goes to Iliya.
- A newer version of the tools needs a new copy and a new `tools/SOURCE.json`, made on
  purpose.
