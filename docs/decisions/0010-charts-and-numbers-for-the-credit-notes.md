# 0010: Charts and numbers for the credit notes

Date: 2026-10-20. Status: accepted.

## Context

Notes 2 and 3 come from `credit-risk-scorecard`. Each needs one chart, drawn by
`build.py` under ADR 0009. Note 3 also gives approval and error rates for women and
men. The case study shows these rates as decimal shares, which read badly in a
sentence about how many women were approved.

## Options

For note 3's rates:

1. Reuse the case study's share entries in the note. Hard to read.
2. Change the case study's entries to percentages. That changes a finished page.
3. Add new entries in `projects.toml` for the same JSON keys, shown as percentages.

For note 3's chart:

1. Bars from zero. The four approval rates sit close together, so the change in the gap
   is hard to see.
2. A dot for women and a dot for men on each row, joined by a line, with a scale that
   spans only the four rates. Dots carry no zero line, and each dot has its value
   written next to it, so the scale cannot mislead about size.

## Decision

Option 3 for the rates, and option 2 for the chart.

- New entries: `*_pct` approval rates, the four false-positive rates and two
  calibrated PDs from `reports/gender_check.json`, the raw and isotonic ROC-AUC, the
  three expected-loss amounts and the assumed LGD. Each one names its `CLAIMS.md` row,
  and the build checks the value against it, as for every other number (ADR 0002).
- `mean_pd`: three bars from zero (raw average PD, calibrated average PD, real default
  rate), scaled to the largest.
- `gender_approval`: one row per model, as above. The scale adds a quarter of the
  range on each side so the labels fit. It shows no tick values.

## Consequences

- The same JSON key can feed two entries with different formats. Both are checked, so
  they cannot disagree.
- Left out, because they have no `CLAIMS.md` row: the women-minus-men gaps (marked
  not-a-claim in the source repo), the calibrated PD for men with gender as an input,
  and the weight LightGBM gives each defaulter. The notes say these in words or not at
  all.
