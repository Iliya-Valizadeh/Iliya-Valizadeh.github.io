# Claims

Every number in this repo's Markdown files has a row here. Each row says where the
number comes from and which command makes that file. `make check-docs` fails if a
number in the docs has no row, or if a row does not match its source.

Small whole numbers (0 to 10), years, dates and version numbers are skipped. To skip
one line by hand, add the comment `<!-- not-a-claim -->` to it.

| Claim | Value | Source | Command |
|---|---|---|---|
| Rows used, features, default rate | 307,511; 244; 8.07% | `reports/metrics.json#data` | `make eval` |
| Rows by split | 184,506 train; 61,502 [calibration](docs/glossary.md#calibration); 61,503 test | `reports/metrics.json#data` | `make eval` |
| Split shares (docstring) | 60%, 20%, 20% | `src/credit_risk_scorecard/model.py` | `make eval` |
| `DAYS_EMPLOYED` sentinel | 365243 | `src/credit_risk_scorecard/features.py` | `make eval` |
| Random seed | 42 | `src/credit_risk_scorecard/config.py` | `make eval` |
| [Bootstrap](docs/glossary.md#bootstrap) resamples and interval width | 1,000; 95% | `src/credit_risk_scorecard/evaluate.py` | `make eval` |
| Illustrative [decline rate](docs/glossary.md#decline-rate) | 20% | `src/credit_risk_scorecard/model.py` | `make eval` |
| LightGBM hyperparameters | 600 trees; 0.02 learning rate; 31 leaves | `src/credit_risk_scorecard/model.py` | `make eval` |
| Assumed [LGD](docs/glossary.md#lgd) | 45% | `src/credit_risk_scorecard/expected_loss.py` | `make eval` |
| [ROC-AUC](docs/glossary.md#roc-auc) and [PR-AUC](docs/glossary.md#pr-auc) by model, with 95% intervals | 0.752 (0.745-0.759); 0.227 (0.216-0.238); 0.769 (0.762-0.775); 0.254 (0.242-0.265) | `reports/metrics.json` | `make eval` |
| Gap between models (bootstrap) | 0.013 to 0.020 ROC-AUC; 0.021 to 0.033 PR-AUC | `reports/metrics.json#bootstrap` | `make eval` |
| Calibration table (raw, Platt, isotonic) | 0.395; 0.1851; 0.3145; 0.080; 0.0673; 0.0032; 0.0027; 0.768; 0.769 | `reports/metrics.json#calibration` | `make eval` |
| Isotonic PR-AUC after calibration | 0.244 | `reports/metrics.json#calibration.isotonic.pr_auc` | `make eval` |
| Observed default rate on test | 8.07%; 0.0807 | `reports/metrics.json#calibration.observed_default_rate_test` | `make eval` |
| Operating point (threshold, precision, recall, flag rate) | 0.600; 22.0%; 0.2197; 53.2%; 0.5317; 19.5%; 0.1954 | `reports/metrics.json#operating_point` | `make eval` |
| Threshold table | 0.30; 0.40; 0.50; 0.60; 0.70; 0.118; 0.897; 0.142; 0.800; 0.175; 0.685; 0.220; 0.532; 0.281; 0.341; 0.614; 0.455; 0.316; 0.196; 0.098 | `reports/metrics.json#threshold_table` | `make eval` |
| [Expected loss](docs/glossary.md#expected-loss) (raw, calibrated, implied) | 4,312,985,709; 642,168,648; 633,364,511 | `reports/metrics.json#expected_loss` | `make eval` |
| With/without gender LightGBM ROC-AUC | 0.770; 0.769; 0.7703; 0.7687 | `reports/gender_check.json` | `python -m credit_risk_scorecard.gender_check` |
| Gender group decisions (approval, recall, false-positive rate) | 0.845; 0.723; 0.475; 0.617; 0.131; 0.239; 0.832; 0.752; 0.492; 0.583; 0.144; 0.209 | `reports/gender_check.json` | `python -m credit_risk_scorecard.gender_check` |
| Gender predictability from remaining inputs | 0.876 | `reports/gender_check.json#gender_predictability_auc` | `python -m credit_risk_scorecard.gender_check` |
| Gender-correlated top inputs ([SHAP](docs/glossary.md#shap) rank, correlation) | 3; -0.20; 9; 0.15; 20; 0.34 | `reports/gender_check.json#proxies` | `python -m credit_risk_scorecard.gender_check` |
| Observed default rate by gender | 10.2%; 7.0% | `reports/gender_check.json` | `python -m credit_risk_scorecard.gender_check` |
| Calibrated PD by gender | 7.4%; 7.0%; 9.2%; 10.2% | `reports/gender_check.json` | `python -m credit_risk_scorecard.gender_check` |
| Age-band decisions (n, observed rate, mean PD, approval, recall, false-positive rate) | 8,975; 24,664; 20,778; 7,086; 0.115; 0.090; 0.066; 0.048; 0.116; 0.088; 0.650; 0.774; 0.860; 0.946; 0.679; 0.578; 0.429; 0.202; 0.307; 0.191; 0.120; 0.047 | `reports/metrics.json#fairness.age_band` | `make eval` |
| Decline rate by age, 20-29 vs 60+ | 30.7%; 4.7% | `reports/metrics.json#fairness.age_band` | `make eval` |
| SHAP sample size | 2,000 | `src/credit_risk_scorecard/model.py` | `make eval` |
| Logistic regression convergence (iterations, ROC-AUC) | 1,000; 149; 227; 0.7533; 0.7524; 0.752; 0.753 | `reports/logreg_convergence.md` | `python -m credit_risk_scorecard.logreg_check` |
| Retrain trigger (lower bound of test interval) | 0.762 | `reports/metrics.json#bootstrap.roc_auc.lightgbm.lo` | `make eval` |

Numbers not traced above are marked `<!-- not-a-claim -->` in place, for one of three
reasons:

- They are historical figures quoted from git history that can't be regenerated (an
  old README's 17,000-row sample, and an old 0.40 fixed cutoff, both replaced long
  ago).
- They are policy suggestions the model card calls "common starting points, not
  values validated for this model" (the [PSI](docs/glossary.md#psi) monitoring thresholds).
- They are a plain-language difference between two numbers this file already traces
  (a percentage-point gap, or a percent reduction), and the checker matches numbers
  literally rather than doing arithmetic. Each such line names both numbers it was
  computed from, so it can still be checked by hand.

Example row, for the format only:
`| Test AUC | 0.58 (0.55 to 0.61) | reports/metrics.json#auc | make eval |`
