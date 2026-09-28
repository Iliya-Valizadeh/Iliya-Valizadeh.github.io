# 0008: The project pages

Date: 2026-09-28. Status: accepted.

## Context

Plan section `5.7` asks for one case study per work project (about a three-minute
read: the problem, what I did, what I found, what I would do next, and links) and a
"For everyone" page for the public tool. Each page must say what is weak. The
`second-look` page must say "synthetic" next to every number and must never use the
word "fraud" ([ADR 0002](0002-where-each-number-comes-from.md)).

These pages need numbers the Home cards did not. The number rules of ADR 0002 could
not yet read all of them:

- `credit-risk-scorecard` lists its gender result in a second results file,
  `reports/gender_check.json`. The config read one results file per repo.
- Some results sit inside a list in `metrics.json`, such as `results.6` in
  `bank-filings-rag`. The shared path reader follows object keys only.
- The rows-used Value cell writes the count with a thousands comma. The shared matcher
  reads it as two numbers.
- ADR 0002 planned "row entries" for numbers whose `CLAIMS.md` Source is a Markdown
  report or a constant in code, such as the word-piece limit and the precision bars.
  They were not built.

## Options

1. Show only the numbers the Home cards already use. The pages would have to describe
   their main findings without the numbers behind them.
2. Change the shared code in `scripts/shared/`. It is a byte-for-byte copy of the
   profile repo's renderer, and a test fails if it is edited here.
3. Add the missing parts to this repo's own `build.py`, around the shared code, and
   keep every check ADR 0002 asks for.

## Decision

Option 3. `build.py` reads four more things, and `scripts/check_numbers.py` now uses
the same pipeline, so the two can never disagree:

- A `[[project.number]]` entry may name its own `file`. The row's Source cell must name
  that file, as before.
- A path part that is a whole number picks an item from a list, so
  `results.6.verified.hit_at_k.value` works. Object keys work as before.
- An entry with `thousands = true` is matched against the Value cell with its
  thousands commas removed, so a comma-grouped count is read as one number.
- `[[project.row_number]]` entries are ADR 0002's row entries. Each has an `id`, the
  exact Claim cell (`row`) and an `index`, the position of the number in the Value
  cell, counting from zero. The number is shown exactly as the cell writes it. The
  build refuses a row entry whose Source is a JSON file, because a number in a JSON
  file must always come from the JSON file.

Pages:

- A `work` project gets `projects/<repo>.html`. A `tool` gets
  `for-everyone/<repo>.html`. Each is built from `content/projects/<repo>.md`, and a
  `work` or `tool` entry without that file stops the build. So a new project cannot
  get a card without a page.
- Each content file has four slots: `lede`, `main`, `weak` and `next`. The `weak` slot
  is shown in a box headed "What's weak". A page without it does not build.
- The Home card links to the page. Pages in a folder use a `root` prefix of `../` for
  the stylesheet, the script and the links back.
- A content file whose front matter says `synthetic_only: yes` treats every number on
  the page as synthetic. Every sentence that holds a number must then say "synthetic",
  or the build stops. The `second-look` page uses it. It shows no Lighthouse score,
  because those measure the live page, not synthetic data, and the rule has no
  exceptions.
- The Markdown record in `_build/md/` keeps the same folders as `_site/`. The "For
  everyone" page is at `_build/md/for-everyone/`, so the readability check can hold
  it to grade 9 with `--plain-glob "*/for-everyone/*.md"`, as
  [ADR 0004](0004-checks.md) asks.

Numbers left out, with the reason:

- `second-look`'s count of synthetic test statements has no `CLAIMS.md` row (ADR
  0002). The page says "synthetic statements" with no count.
- `credit-risk-scorecard`'s gaps between men and women in percentage points are marked
  `not-a-claim` in its README and have no row. The page gives the approval rates from
  the "Gender group decisions" row instead.
- `bank-filings-rag`'s lenient score and its count of misses past the word-piece limit
  have no row. The page describes them in words.

## Consequences

- The pages can show each project's real finding with its number, and every number
  still passes the same row, source and value checks.
- `build.py` holds more of the number logic, and the shared copy stays unchanged. If
  the profile ever needs these features, they should move into the shared code there
  first, and be copied back here.
- A future project page is one Markdown file with four slots.
