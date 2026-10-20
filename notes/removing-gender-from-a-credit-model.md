DRAFT: Iliya to edit
---
title: I removed gender from a credit model. The gap shrank but didn't close.
description: Taking the gender column out of my credit model narrowed the gap between women and men. What did not change, and why removing a column is not a fairness fix.
---
The Home Credit loan data has a gender column. My first credit model used it as an
input, like any other column. In my first full results, it was the eighth most
important input.

Then I took it out. I kept the column in the data, but only to check how the model
treats women and men. The model itself can no longer see it. I did not write down why
at the time, and I made the change after I had seen the first results by gender. Later
I trained the model both ways on the same split of the data, to see what the change
really did.

## How I measured the gap

The model gives each applicant a risk score. In my setup, a lender turns down the
riskiest {{ credit_risk_scorecard.decline_rate }} of applicants
([decline rate](https://github.com/Iliya-Valizadeh/credit-risk-scorecard/blob/main/docs/glossary.md#decline-rate)).
For women and for men, I counted the share of applicants approved. I also counted how
often the model turns down people who in fact paid without trouble. That is the
false-positive rate.

## The gap shrank

Removing gender made the ranking a tiny bit worse. How well a model ranks risky
applicants above safe ones is its
[ROC-AUC](https://github.com/Iliya-Valizadeh/credit-risk-scorecard/blob/main/docs/glossary.md#roc-auc).
It went from {{ credit_risk_scorecard.with_gender_roc_auc }} to
{{ credit_risk_scorecard.without_gender_roc_auc }}. That comes from one split with no
interval, so the change may be noise.

With gender as an input, the model approved
{{ credit_risk_scorecard.approval_women_with_gender_pct }} of women and
{{ credit_risk_scorecard.approval_men_with_gender_pct }} of men. Without it, the model
approved {{ credit_risk_scorecard.approval_women_without_gender_pct }} of women and
{{ credit_risk_scorecard.approval_men_without_gender_pct }} of men.

<!-- chart: gender_approval -->
The line between women and men is shorter without gender, but it does not shrink to a
point.

Look at how it shrank. Men gained, and women lost. Among women who paid without
trouble, the model turned down {{ credit_risk_scorecard.fpr_women_with_gender }} with
gender as an input and {{ credit_risk_scorecard.fpr_women_without_gender }} without it.
For men, the same rate fell from {{ credit_risk_scorecard.fpr_men_with_gender }} to
{{ credit_risk_scorecard.fpr_men_without_gender }}. So part of the smaller gap came from
being harder on women who would have paid. A smaller gap does not by itself make a model
fairer.

## Why it did not close

I see two reasons, and my check cannot tell them apart.

First, the other inputs still carry gender. I trained a simple model to guess gender
from the inputs that were left. It told women from men with ROC-AUC
{{ credit_risk_scorecard.gender_predictability_auc }}, far better than a guess. Some of
those inputs matter a lot to the credit model. The third most important one is a credit
score from an outside source, and it is linked to gender. Age and owning a car are also
linked to gender, and the model uses both. So gender still reaches the model, only by a
longer road.

Second, the groups differ in the data. Men had payment difficulties more often:
{{ credit_risk_scorecard.default_rate_men }}, against
{{ credit_risk_scorecard.default_rate_women }} for women. A model that knew nothing
about gender would likely still turn down more men.

## Its probabilities got worse by group

The model also gives each applicant a probability of default (PD), after a
[calibration](https://github.com/Iliya-Valizadeh/credit-risk-scorecard/blob/main/docs/glossary.md#calibration)
step. With gender as an input, the average PD was close to the real default rate for
both groups. Without it, the average PD for women was
{{ credit_risk_scorecard.pd_women_without_gender }}, against a real rate of
{{ credit_risk_scorecard.default_rate_women }}. For men it was
{{ credit_risk_scorecard.pd_men_without_gender }}, against
{{ credit_risk_scorecard.default_rate_men }}. So the model now puts the risk too high
for women and too low for men.

## What I take from it

Removing the column was a choice about inputs. It was not a fix for outcomes. It stops
the model from using gender directly. In return, it cost a little ranking and made the
probabilities worse by group. Age also enters the model directly, and I have not
decided whether that should be allowed.

## What I would do next

First, I would put intervals on these gaps, the same way I did for ROC-AUC, so I know
which ones are bigger than noise. Second, I would decide what "fair" should mean for
this model before I choose a fix. Equal approval rates, equal error rates and correct
PDs for each group can pull in different directions. I would want to make that choice with
someone who knows the rules lenders must follow.

This comes from one random split of one public dataset. The full tables are in the
[gender check report](https://github.com/Iliya-Valizadeh/credit-risk-scorecard/blob/main/reports/gender_check.md),
and the choice itself is in
[decision record 0005](https://github.com/Iliya-Valizadeh/credit-risk-scorecard/blob/main/docs/decisions/0005-drop-code-gender-as-a-model-input.md).
