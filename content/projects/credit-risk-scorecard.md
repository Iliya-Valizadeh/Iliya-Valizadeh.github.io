---
title: Credit risk model, a case study | Iliya Valizadeh
description: How a credit risk model on public Home Credit data ranks loan applicants, why its first probabilities were far too high, and what a check on gender found.
---
<!-- slot: lede -->
A model that ranks loan applicants by the risk that they miss payments, then turns that
rank into a probability a bank could use. It is built on
{{ credit_risk_scorecard.rows_used }} applications from the public Home Credit data on
Kaggle.

<!-- slot: main -->
## The problem

A lender needs two things from a credit model. It must rank applicants, so that the
riskiest come first. And its predicted chance of default must be right on average,
because a bank uses that number to set money aside for losses. Making it right is
called
[calibration](https://github.com/Iliya-Valizadeh/credit-risk-scorecard/blob/main/docs/glossary.md#calibration). A model can do the first well and the second badly. I wanted to measure both,
and to check whether its decisions fall unevenly on men and women.

## What I did

- Used the main application table: {{ credit_risk_scorecard.rows_used }} applications.
  Only {{ credit_risk_scorecard.observed_default_rate }} of the applicants in the test
  part had payment difficulties.
- Split the rows at random into a training part, a calibration part and a test part.
  Every result below is on the test part.
- Trained a logistic regression as the
  [baseline](https://github.com/Iliya-Valizadeh/credit-risk-scorecard/blob/main/docs/glossary.md#baseline)
  and LightGBM, a model built from many small decision trees, as the main model. Both
  gave extra weight to the rare applicants who defaulted.
- Fitted
  [isotonic regression](https://github.com/Iliya-Valizadeh/credit-risk-scorecard/blob/main/docs/glossary.md#isotonic-regression)
  on the calibration part, to turn LightGBM's raw score into a probability.
- Trained the model with and without the gender column, then compared who gets
  declined when the riskiest {{ credit_risk_scorecard.decline_rate }} of applicants
  are turned down.

## What I found

LightGBM ranks applicants a little better than the baseline. How well a model ranks
risky applicants above safe ones is its
[ROC-AUC](https://github.com/Iliya-Valizadeh/credit-risk-scorecard/blob/main/docs/glossary.md#roc-auc).

| Model | ROC-AUC on the test part | {{ credit_risk_scorecard.interval_level }} interval |
|---|---|---|
| Logistic regression (baseline) | {{ credit_risk_scorecard.logreg_roc_auc }} | {{ credit_risk_scorecard.logreg_roc_auc_lo }} to {{ credit_risk_scorecard.logreg_roc_auc_hi }} |
| LightGBM | {{ credit_risk_scorecard.lightgbm_roc_auc }} | {{ credit_risk_scorecard.lightgbm_roc_auc_lo }} to {{ credit_risk_scorecard.lightgbm_roc_auc_hi }} |

Both models were scored on the same resampled test sets. The gap between them is
{{ credit_risk_scorecard.gap_roc_auc_lo }} to {{ credit_risk_scorecard.gap_roc_auc_hi }}
of ROC-AUC. It is above zero, but it is small.

The extra weight on rare defaults broke the probabilities. The raw model said the
average applicant had a {{ credit_risk_scorecard.raw_mean_pd }} chance of default. The
real rate in the test part was {{ credit_risk_scorecard.observed_default_rate }}. After
calibration, the average predicted chance was
{{ credit_risk_scorecard.isotonic_mean_pd }}. The
[Brier score](https://github.com/Iliya-Valizadeh/credit-risk-scorecard/blob/main/docs/glossary.md#brier-score),
the average squared gap between the predicted chance and what happened, fell from
{{ credit_risk_scorecard.raw_brier }} to {{ credit_risk_scorecard.isotonic_brier }}.
The ranking barely moved. So the calibration step mostly undoes a side effect of a
choice I made.

Removing gender narrowed the gap between men and women, but did not close it. ROC-AUC
went from {{ credit_risk_scorecard.with_gender_roc_auc }} with the gender column to
{{ credit_risk_scorecard.without_gender_roc_auc }} without it. The approval rate for
men rose from {{ credit_risk_scorecard.approval_men_with_gender }} to
{{ credit_risk_scorecard.approval_men_without_gender }}. For women it fell from
{{ credit_risk_scorecard.approval_women_with_gender }} to
{{ credit_risk_scorecard.approval_women_without_gender }}. The other inputs still carry
gender: from them, a simple model can tell men from women with ROC-AUC
{{ credit_risk_scorecard.gender_predictability_auc }}. Men also had payment
difficulties more often in this data ({{ credit_risk_scorecard.default_rate_men }}
against {{ credit_risk_scorecard.default_rate_women }}), so some gap would remain even
if the model knew nothing about gender. This check cannot separate the two causes.

<!-- slot: weak -->
- The split is random, not by time. The table has no application date, so I cannot
  test the model on later applicants. Ranking would likely fall on them, and
  calibration is the part most likely to break.
- The baseline is a plain logistic regression, not the binned scorecard that banks
  use, and neither model is tuned. A stronger baseline could narrow or widen the gap.
- Only the application table is used. The credit bureau and previous-application
  tables are not, and adding them would likely change every number.
- I wrote the evaluation plan after the results existed. The test part was scored
  many times, so a reader cannot check that no choice was steered by test numbers.
- The gender results come from one split and have no interval. The change in ROC-AUC
  from dropping gender may be noise.

The full ranked list is in
[docs/whats_weak.md](https://github.com/Iliya-Valizadeh/credit-risk-scorecard/blob/main/docs/whats_weak.md).
The model is not for pricing, collections or any real lending decision.

<!-- slot: next -->
## What I would do next

- Find loan data with application dates, and test on the newest applicants.
- Build a binned scorecard as a stronger baseline, and tune both models the same way.
- Add the credit bureau and previous-application tables.
- Put intervals on the gender and age results, so that small gaps are not read as
  real.

## Links

- [The code and the full write-up](https://github.com/Iliya-Valizadeh/credit-risk-scorecard)
- [The evaluation plan](https://github.com/Iliya-Valizadeh/credit-risk-scorecard/blob/main/docs/eval_plan.md),
  which says plainly that it was written after the results
- [The gender check](https://github.com/Iliya-Valizadeh/credit-risk-scorecard/blob/main/reports/gender_check.md)
- [The model card](https://github.com/Iliya-Valizadeh/credit-risk-scorecard/blob/main/MODEL_CARD.md)
