DRAFT: Iliya to edit
---
title: The fix that broke my probabilities
description: I gave extra weight to the rare loans that went bad. My credit model still ranked people well, but its probabilities were far too high. How I found it and fixed it.
---
I built a model that looks at a loan application and estimates the chance that the
person will have trouble paying. It uses public data from Home Credit, a lender, with
{{ credit_risk_scorecard.rows_used }} past applications. The model has two jobs. First,
it ranks applicants from safe to risky. Second, it gives each one a probability of
default (PD). That is a number a lender can plan with.

The first job went well. I broke the second one myself, with a fix I never tested.

## The fix

Defaults are rare in this data. In the test part, only
{{ credit_risk_scorecard.observed_default_rate }} of applicants had payment
difficulties. A common worry is that a model trained on a rare outcome will pay too
little attention to it. A common answer is to give the rare cases more weight while the
model learns.

So I did that. I told LightGBM, the model I used, to weigh each person who defaulted so
heavily that the two groups counted the same in total. I did it because it is common
advice. I never trained a model without the weights to see if they helped.

## What broke

The ranking was fine. How well a model ranks risky applicants above safe ones is its
[ROC-AUC](https://github.com/Iliya-Valizadeh/credit-risk-scorecard/blob/main/docs/glossary.md#roc-auc).
Mine scored {{ credit_risk_scorecard.raw_roc_auc }} on the test part.

The probabilities were not fine. On average, the raw model said an applicant had a
{{ credit_risk_scorecard.raw_mean_pd }} chance of default. The real rate was
{{ credit_risk_scorecard.observed_default_rate }}.

<!-- chart: mean_pd -->
The raw model's average guess is far above the real default rate, and the calibrated
one lands right next to it.

The reason is simple once you see it. The weights told the model that defaults were as
common as repayments. So it learned scores for that made-up world, not for the real one.
Pushing every score up does not have to change their order. That is how the ranking
could look good while every probability was too high.

For a while, the demo app showed this raw score as a probability of default. Nobody
should have read it that way.

## What it would cost

A lender uses PDs to plan for losses. The
[expected loss](https://github.com/Iliya-Valizadeh/credit-risk-scorecard/blob/main/docs/glossary.md#expected-loss)
on a loan is the PD, times the share of the loan lost if the person defaults, times the
amount lent. The data has no recovery amounts, so I assumed that share is
{{ credit_risk_scorecard.lgd }}
([LGD](https://github.com/Iliya-Valizadeh/credit-risk-scorecard/blob/main/docs/glossary.md#lgd)).
The amounts are in the data's own currency, which the dataset does not name.

Added up over the approved applicants, the raw PDs give an expected loss of
{{ credit_risk_scorecard.el_raw_pd }}. The loss implied by what really happened is
{{ credit_risk_scorecard.el_implied }}. A lender that trusted the raw scores would set
aside far more money than it needed.

## The fix for the fix

The answer was
[calibration](https://github.com/Iliya-Valizadeh/credit-risk-scorecard/blob/main/docs/glossary.md#calibration):
a second step that maps each raw score to a probability that matches real outcomes. I
kept a separate calibration part of the data for this. Neither training nor testing
used it. On that part I fitted
[isotonic regression](https://github.com/Iliya-Valizadeh/credit-risk-scorecard/blob/main/docs/glossary.md#isotonic-regression),
a curve that can only go up. A simpler method,
[Platt scaling](https://github.com/Iliya-Valizadeh/credit-risk-scorecard/blob/main/docs/glossary.md#platt-scaling),
came out almost the same.

After calibration, the average predicted chance was
{{ credit_risk_scorecard.isotonic_mean_pd }}, against the real
{{ credit_risk_scorecard.observed_default_rate }}. The
[Brier score](https://github.com/Iliya-Valizadeh/credit-risk-scorecard/blob/main/docs/glossary.md#brier-score)
is the average squared gap between the predicted chance and what happened, so lower is
better. It fell from {{ credit_risk_scorecard.raw_brier }} to
{{ credit_risk_scorecard.isotonic_brier }}. The ranking barely moved: ROC-AUC went from
{{ credit_risk_scorecard.raw_roc_auc }} to {{ credit_risk_scorecard.isotonic_roc_auc }}.
With calibrated PDs, the expected loss was {{ credit_risk_scorecard.el_calibrated_pd }},
close to the {{ credit_risk_scorecard.el_implied }} from real outcomes.

That close match is not a separate proof. I fitted the calibration step to make PDs
match default rates, on data drawn the same way as the test part. So it shows the step
did its job here. It does not show the PDs would still be right next year.

## What I would change

First, I would train the model once without the weights. If the ranking stays the
same, the weights add nothing but a problem, and I would drop them. I would still
calibrate, because a model's scores are not probabilities until I check them.

Second, I would check calibration on later applications. My split was random, not by
time, because the table has no application date. A PD that is right today can drift
when the default rate changes.

## What I learned

A model can rank people well and still give the wrong probabilities. Ranking and
probability are two different jobs, and a good score on one says little about the
other. Now I compare the average prediction with the real rate before I trust any
probability. It takes one line of code.

This comes from one random split of one public dataset. The full tables are in the
[results report](https://github.com/Iliya-Valizadeh/credit-risk-scorecard/blob/main/reports/results.md),
and the reasons for each choice are in the
[decision records](https://github.com/Iliya-Valizadeh/credit-risk-scorecard/tree/main/docs/decisions).
