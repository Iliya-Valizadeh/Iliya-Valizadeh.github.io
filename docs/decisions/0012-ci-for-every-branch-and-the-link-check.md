# 0012: CI on every branch, and a site-specific link check settings file <!-- not-a-claim -->

Date: 2026-10-20. Status: accepted.

## Context

[ADR 0004](0004-checks.md) says the checks run in `ci.yml` on every push and pull
request. Until now only `pages.yml` existed, and it runs on `main` alone. The branch
`phase-e-site` had no checks on GitHub at all.

Two problems showed up when the checks were first run together.

- `tools/lychee.toml` is copied unchanged from `ds-project-standard` and must not be
  edited here. Every page carries an absolute canonical link and share tags that point
  at this site's own address. Before the first deploy those pages do not exist, so
  lychee reports them as broken.
- The old lychee arguments in `pages.yml` scanned every Markdown file, including the
  saved copies of other repos in `tests/fixtures/`. Their glossary links point at
  files that are not in this repo, so that job would fail on the first deploy.

## Decision

- `ci.yml` runs on every push and pull request. It is offline: the build reads
  `tests/fixtures/`. It has no schedule.
- `lychee.site.toml` is `tools/lychee.toml` plus one more skipped pattern, this
  site's own address. Links between built pages are relative, so lychee still checks
  them as files. The live site is checked once after the deploy, by the merge task.
- Lychee reads `_site/`, `README.md`, `CLAIMS.md` and `docs/` only.
- The readability step lists its plain-writing globs on the command line: the notes
  and the "For everyone" pages. A glob given on the command line replaces the tool's
  default, so the notes globs are repeated.
- `pages.yml` gets the same writing, claims and link steps, so a deploy runs what CI
  runs plus the live numbers.

## Consequences

- A red run on a branch means a real problem in this repo, not a change elsewhere.
- Web links to other sites can only fail in CI, as the `ship` skill expects.
