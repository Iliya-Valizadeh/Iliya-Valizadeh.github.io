# 0009: Note files, draft previews and charts

Date: 2026-09-28. Status: accepted.

## Context

ADR 0001 puts notes in `notes/`, one Markdown file each. ADR 0005 says how a draft
stays out of the site. The first note needed three more choices: the exact file
layout, how Iliya can read a draft before he publishes it, and how a note shows a
chart without a typed number.

## Options

1. Treat notes like `content/` pages, with named slots. Too much structure for a short
   essay.
2. One Markdown body per note, with the status line first, then front matter.
3. Put the status inside the front matter. Then the draft marker is not the first line
   of text, which breaks ADR 0005's rule.

For charts: a picture made by hand would hold numbers the checks cannot read. A chart
drawn by `build.py` from the same built numbers as the text can be checked.

## Decision

Option 2, and charts drawn by the build.

- A note starts with one status line: `DRAFT: Iliya to edit`, or
  `Published: YYYY-MM-DD` once he publishes it. Then comes front matter with `title`
  and `description`, then the body. Numbers in the body are `{{ placeholders }}`, the
  same as every other page (ADR 0002).
- A draft's filled-in Markdown goes to `_build/md/drafts/notes/`, where the writing and
  number checks read it. A preview page goes to `_build/preview/notes/`, with its own
  copy of `static/`. Neither folder is deployed. A published note goes to
  `_site/notes/`.
- A line `<!-- chart: name -->` draws the chart that `build.py` names in `CHARTS`. The
  paragraph right after it is the caption, and a chart with no caption fails the build.
  A chart only scales numbers the pipeline already built. It shows no number of its
  own.
- After every build, the draft marker anywhere under `_site/` fails it.

The Notes index and the feed are a later task. A test already checks that no file
under `_site/` names the draft note, so they will be covered from their first build.

## Consequences

- Iliya reads a draft at `_build/preview/notes/<name>.html` after `python build.py`.
- Publishing is still one line: he swaps the marker for a `Published:` line.
- A chart cannot drift from the text, because both come from the same numbers.
