# 0014: No scheduled run for the Pages workflow <!-- not-a-claim -->

Date: 2026-10-20. Status: accepted. Replaces the daily run described in
[ADR 0001](0001-a-small-python-build-deployed-by-actions.md).

## Context

`pages.yml` had a daily `cron` trigger, so the site's numbers would follow the source
repos even when nobody pushed here. Workspace rule 6 says a scheduled workflow must
never be able to fail again and again, because every failed run emails me.

This one could. The scheduled run builds from the live results files in the other
repos, with no `--offline`, and the build stops on any check failure by design. Three
things outside this repo could make it fail every day until someone acted:

- GitHub or a source repo is down or slow when the run fetches a file.
- A source repo changes a number but its `CLAIMS.md` row does not match yet, so the
  claims check stops the build.
- A source repo renames or removes a file the build reads.

Each is a correct stop for a deploy. None is correct for a background job that nobody
is watching.

## Options

1. Keep the schedule and make a failed scheduled run print a warning and exit 0.
2. Drop the schedule and keep `workflow_dispatch`.

## Decision

Option 2.

Option 1 hides a real failure: the site would go stale and nothing would say so. It
also adds a special case to a workflow that is otherwise a plain build.

There is no clear need for the schedule. The numbers on the site change only when a
project's own results file changes, and I make those changes. After one, a push to
this repo or the "Run workflow" button rebuilds the site with the new numbers, and the
build checks them before anything is published. A site that is a little stale is not
harmful. A site that fails every day and emails me is.

Nothing else changes: `pages.yml` still runs on pushes to `main` and on
`workflow_dispatch`, skips itself until the Pages source is set to GitHub Actions, and
deploys only from `main`.

## Consequences

- If a project's numbers change, the site does not follow until a push or a manual run.
  The project's own task list should say so. The profile repo has its own sync, which
  is outside this decision.
- Pushes to `main` can still fail a live build. That is one failure per push, on a
  push someone just made, not a repeating one.
