# 0007: The Home and About pages

Date: 2026-09-28. Status: accepted.

## Context

The scaffold rebuilt the old one-page site from partials, with its typed numbers still
in the work list. Plan section `5.7` asks for a Home page (the idea, the work projects,
the public tool, a "Seeking a Winter 2027 co-op" line) and an About and contact page.
[ADR 0006](0006-text-kept-word-for-word-and-the-old-page.md) keeps the About section and
both demos word for word, and keeps `static/main.js` byte for byte. That script runs
the demos, and it stops at the first demo element it cannot find on a page.

## Options

1. Keep one long page with the About section on it. The plan asks for a separate page.
2. Move the demos off the Home page. The opening line says two models run "on this
   page", so it would become untrue.
3. Keep the demos on the Home page and give the About section its own page. Pages
   without demos load a second script that holds only the page-wide parts of
   `main.js`.

## Decision

Option 3.

Pages:

- `index.html` (Home): nav, opening, the two demos, the work list, contact.
- `about.html`: nav, the kept About section, a short "Now" section with the co-op
  line, contact.
- Both pages share one shell, `templates/page.html`. The contact section is on both,
  because `main.js` expects the email button on the Home page.
- `static/site.js` holds the cursor, button, email and reveal blocks of `main.js`,
  copied unchanged. A test checks that each block still appears in `main.js`.

Where the words live:

- Page prose is in `content/home.md` and `content/about.md`, split into named slots by
  `<!-- slot: name -->` lines. Each file starts with a title and a description.
- Card prose is in `projects.toml`: `title`, `tags`, `summary`, `finding`, `headline`,
  and one `metric` shown large with its `metric_label`.
- Markdown becomes HTML with `markdown-it-py`, the one package
  [ADR 0001](0001-a-small-python-build-deployed-by-actions.md) planned for.
- The build writes each page's prose, filled in, to `_build/md/`, so the writing and
  number checks read everything new. The kept partials are not in it, as ADR 0004
  says.

Numbers and flags:

- Card text uses the number placeholders from `projects.toml` (ADR 0002). A sentence
  that holds a number marked `synthetic` must say "synthetic", and so must the label
  of a synthetic `metric`. The build stops otherwise.
- `[[project.flag]]` reads a true or false value from `metrics.json` and shows one of
  two sentences. `second-look` uses it for `failure_bar.passed`, as ADR 0002 planned.
  If the tool later meets its bar, the Home page changes with no edit here.

The project list:

- Every `work` entry, then every `tool` entry, in config order, numbered in that
  order. `standard` entries get no card. The Home text links them by name, in a short
  paragraph on how the projects are built (ADR 0003).
- A test adds a made-up `work` project to a copy of the config and checks it gets a
  card with no template change.

Removed from the old work list:

- The small line charts next to each project. They were drawn from a fixed random
  seed, not from data, so they looked like results that do not exist. The card's
  headline number takes their place.
- Every typed number in the old card text.

Numbers left out for now, with the reason:

- `credit-risk-scorecard` rows used: the shared matcher reads a comma-grouped number
  in a `CLAIMS.md` Value cell as two numbers, so it cannot match. The text says "the
  public Home Credit data" with no count.
- `credit-risk-scorecard` interval level: its `metrics.json` has no level, so its card
  says "interval" with no level. Its gender result is in
  `reports/gender_check.json`, and the shared config reads one results file per repo.
- `bank-filings-rag` word-piece numbers and the `second-look` precision bar: their
  `CLAIMS.md` rows point at a Markdown report or a code constant. ADR 0002's "row
  entries" for these are not built yet. The cards describe them in words.

The footer:

- The old footer said the page was hand written with no framework and no template.
  The new line says it is built from templates by a small Python script, with no
  framework. Iliya picks the final words (a "Needs Iliya" item quotes both).

## Consequences

- The opening line stays true, and the About section keeps its words.
- The two scripts share some code. A change to the page-wide parts of `main.js` must
  be copied to `site.js`, and the test catches a copy that drifts.
- Adding a project is one config entry. Its card needs no template change.
