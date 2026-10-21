# 0002: Where each number on the site comes from

Date: 2026-09-26. Status: accepted.

## Context

Every number in this portfolio must trace to a committed script through a `CLAIMS.md`
row. The site makes no numbers of its own. It shows numbers that the project repos
make and list in their own `CLAIMS.md`. The profile repo, `Iliya-Valizadeh`, faces the
same problem, and both should follow one rule.

## Options

1. Type the numbers into the pages. They drift, and nothing checks them.
2. Read each repo's JSON file and trust it. A number could appear on the site that its
   own repo never claims.
3. Read each repo's JSON file and its `CLAIMS.md` from the same commit, and show a
   number only when both agree. This is the profile repo's rule too.

## Decision

Option 3.

Fetching, the same as the profile:

- `git ls-remote https://github.com/Iliya-Valizadeh/<repo> refs/heads/main` gives the
  current commit of `main`.
- The build reads `https://raw.githubusercontent.com/Iliya-Valizadeh/<repo>/<commit>/<file>`
  for the source file and for `CLAIMS.md`, both at that commit.
- The build uses no key, token or paid API. The repos are public.
- The build writes the commits it used to `_site/sources.json`, so a reader can trace
  any number back to one commit.

Each number is one entry in `projects.toml`, with an `id` (the placeholder name),
`repo`, `file`, `row` (the exact Claim cell of the source row) and `format`. There are
two kinds of entry:

- JSON entries have a `path`, a dotted key in a `reports/*.json` file. The row's
  Source cell must name the same file, and its `#key`, if any, must be the start of
  `path`. The formatted value must equal a number in the row's Value cell, using the
  number matching of the vendored `tools/claims_check.py`.
- Row entries have no `path`. They take the number from the row's Value cell, by
  position. They are allowed only when the row's Source is not a JSON file, such as a
  Markdown report or a constant in code. A number that exists in a JSON file always
  comes from the JSON file.

If any check fails, the build stops and nothing is deployed. The build does no
arithmetic other than rounding and turning a fraction into a percent. A number with no
`CLAIMS.md` row in its own repo is left out of the site and logged in
`_portfolio/STATUS.md`. This phase adds no rows to other repos.

The numbers planned at design time are below. Values are left out of this record on
purpose, because they live in the source repos. Later tasks may add entries under the
same rules.

| Repo | Shown number | Kind, file and path | `CLAIMS.md` row (Claim cell) |
|---|---|---|---|
| `credit-risk-scorecard` | LightGBM ROC-AUC with its interval, and the baseline | JSON, `reports/metrics.json`: `models.lightgbm.roc_auc`, `bootstrap.roc_auc.lightgbm.lo`, `bootstrap.roc_auc.lightgbm.hi`, `models.logreg.roc_auc` | "ROC-AUC and PR-AUC by model, with 95% intervals" <!-- not-a-claim --> |
| `credit-risk-scorecard` | applications used | JSON, `reports/metrics.json`: `data.rows_used` | "Rows used, features, default rate" |
| `credit-risk-scorecard` | observed default rate | JSON, `reports/metrics.json`: `calibration.observed_default_rate_test` | "Observed default rate on test" |
| `credit-risk-scorecard` | mean predicted default rate before and after calibration, Brier score before and after | JSON, `reports/metrics.json`: `calibration.raw.mean_pd`, `calibration.isotonic.mean_pd`, `calibration.raw.brier`, `calibration.isotonic.brier` | "Calibration table (raw, Platt, isotonic)" |
| `credit-risk-scorecard` | how well the other inputs predict gender | JSON, `reports/gender_check.json`: `gender_predictability_auc` | "Gender predictability from remaining inputs" |
| `bank-filings-rag` | hit@5 and baseline, each with its interval | JSON, `reports/metrics.json`: `headline.model.value`, `.ci_low`, `.ci_high`, and the same under `headline.baseline` | "Headline hit@5, whole pages + hybrid, ..." and "Baseline hit@5, fixed chunks + dense, ..." |
| `bank-filings-rag` | hand-checked questions, questions in the key | JSON, `reports/metrics.json`: `n_questions.verified`, `n_questions.all` | "Hand-checked questions" and "Questions in the answer key" |
| `bank-filings-rag` | word-piece limit, median word pieces per page, share of pages over the limit | Row entries (source is `reports/error_analysis.md`) | "Embedding model's word-piece limit", "Median word pieces per page (980.5, rounded)" <!-- not-a-claim -->, "Pages longer than the word-piece limit" |
| `second-look` | recurring recall and precision, each with its interval | JSON, `reports/metrics.json`: `engine.recurring.recall.value`, `.ci_low`, `.ci_high`, and the same under `engine.recurring.precision` | "Recurring recall" and "Recurring precision" |
| `second-look` | baseline recall and precision | JSON, `reports/metrics.json`: `baseline.recurring.recall.value`, `baseline.recurring.precision.value` | "Baseline recurring precision and recall" |
| `second-look` | precision bar the tool had to meet | Row entry (source is `evaluation/evaluate.py`) | "Failure bar: recurring precision" |
| `second-look` | Lighthouse scores on the live page | JSON, `reports/metrics.json`: `lighthouse.performance`, `lighthouse.accessibility` | "Lighthouse scores on the live page, mobile setting, first screen only: performance, accessibility" |
| `ds-project-standard`, `.github` | none | none | none |

The "..." stands for the rest of the Claim cell, which `projects.toml` spells out in
full.

Special rules:

- `ds-project-standard` and `.github` have no `reports/metrics.json`. Their config
  entries have `metrics = false` and cannot have number entries. They are linked from
  the text with no headline number, and none is ever invented for them.
- Every `second-look` number measured on its synthetic test statements is marked
  `synthetic = true`. The Lighthouse scores are not, because they measure the live
  page. A test fails if a marked number appears in a sentence or table cell without the word "synthetic". The
  `second-look` page never uses the word "fraud".
- Whether `second-look` met its failure bar is read from `failure_bar.passed` in its
  `reports/metrics.json` and shown as words. It is a yes or no, not a number, so it
  needs no `CLAIMS.md` row.
- The number of synthetic test statements, `test_seeds.statements`, has no row in
  `second-look`'s `CLAIMS.md` today. So the site does not show that count. This is
  logged for a later phase.
- No page may contain a number that did not come from a placeholder. The check uses
  the number rules of `tools/claims_check.py` (years, dates and whole numbers up to
  ten are skipped). A typed number fails the build.

Shared code: the fetching, row matching and number formatting are written once, in the
profile repo, as part of its renderer task. The site's scaffold task copies them into
`scripts/shared/` with `scripts/shared/SOURCE.json`, which records the profile commit
and the SHA-256 of each file. A test fails if a copy is edited here.

## Consequences

- The site and the profile always show the same value for the same number, because
  they read the same files by the same rules.
- A renamed row in a source repo stops the site from deploying until a person updates
  `projects.toml`. That is on purpose.
- Offline tests use copies of the source files recorded in `tests/fixtures/SOURCES.md`:
  `credit-risk-scorecard` at `35a17fd`, `bank-filings-rag` at `45246f8`, `second-look`
  at `0da821d`.
