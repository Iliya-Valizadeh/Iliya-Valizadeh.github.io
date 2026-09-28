# Claims

Every number in this repo's Markdown files has a row here. Each row says where the
number comes from and which command makes that file. `make check-docs` fails if a
number in the docs has no row, or if a row does not match its source.

Small whole numbers (0 to 10), years, dates and version numbers are skipped. To skip
one line by hand, add the comment `<!-- not-a-claim -->` to it.

| Claim | Value | Source | Command |
|---|---|---|---|
| Hand-checked questions | 12 | `reports/metrics.json#n_questions.verified` | `make eval` |
| Questions in the [answer key](docs/glossary.md#answer-key) | 30 | `reports/metrics.json#n_questions.all` | `make eval` |
| New questions added after the first results (rows for ids 11-30) | 20 | `eval/gold_check.md` | `python -m eval.check_gold` |
| First id in the range of new questions | 11 | `eval/gold_check.md` | `python -m eval.check_gold` |
| Questions checked by script only (30 rows minus the 12 marked `hand`) | 18 | `eval/gold_check.md` | `python -m eval.check_gold` |
| New questions that pass the stricter label-and-figure check, of 20 (Check 2 table, `ok` rows) | 18 | `eval/gold_check.md` | `python -m eval.check_gold` |
| Questions where the answer-text check finds the answer, of 30 (Check 1 table, `ok` rows; Q8 and Q10 are not checkable) | 28 | `eval/gold_check.md` | `python -m eval.check_gold` |
| Headline [hit@5](docs/glossary.md#hit5), whole pages + hybrid, 12 questions, with its 95% interval | 0.58 (0.33 to 0.83) | `reports/metrics.json#headline.model` | `make eval` |
| [Baseline](docs/glossary.md#baseline) hit@5, fixed chunks + dense, 12 questions, with its 95% interval | 0.25 (0.00 to 0.50) | `reports/metrics.json#headline.baseline` | `make eval` |
| hit@5, whole pages + dense, 12 questions, with its 95% interval | 0.50 (0.25 to 0.75) | `reports/metrics.json#results.6.verified.hit_at_k` | `make eval` |
| hit@5, whole pages + hybrid, all 30 questions | 0.70 | `reports/metrics.json#results.8.all.hit_at_k` | `make eval` |
| hit@5, fixed chunks + hybrid, all 30 questions | 0.67 | `reports/metrics.json#results.2.all.hit_at_k` | `make eval` |
| Confidence level for every interval | 95% | `reports/metrics.json#interval.level` | `make eval` |
| [Bootstrap](docs/glossary.md#bootstrap) resamples for every interval | 1,000 | `reports/metrics.json#interval.resamples` | `make eval` |
| Fixed-chunk size, in words | 180 | `src/bank_filings_rag/chunking.py` | source code, `fixed_words` defaults |
| Fixed-chunk overlap, in words | 40 | `src/bank_filings_rag/chunking.py` | source code, `fixed_words` defaults |
| [Reciprocal rank fusion](docs/glossary.md#reciprocal-rank-fusion) constant | 60 | `src/bank_filings_rag/retrieve.py` | source code, `RRF_K` |
| Reciprocal rank fusion depth | 50 | `src/bank_filings_rag/retrieve.py` | source code, `FUSION_DEPTH` |
| [Embedding](docs/glossary.md#embedding) model's word-piece limit | 256 | `reports/error_analysis.md` | worked out in `notebooks/01_explore.ipynb` |
| Median word pieces per page (980.5, rounded) | 981 | `reports/error_analysis.md` | worked out in `notebooks/01_explore.ipynb` |
| Pages longer than the word-piece limit | 96% | `reports/error_analysis.md` | worked out in `notebooks/01_explore.ipynb` |
| Test coverage floor (`--cov-fail-under`) | 47% | `pyproject.toml` | `grep cov-fail-under pyproject.toml` |
| Q1 answer, net income figure (id 1, `answer_any`) | 16.2 | `eval/gold_qa.jsonl` | hand-authored, checked by `python -m eval.check_gold` |
| Q1 answer-key page (id 1, `source_pages`) | 23 | `eval/gold_qa.jsonl` | hand-authored, checked by `python -m eval.check_gold` |
| Pages that mention the net income figure, documented in the module docstring | 13 | `eval/metrics.py` | documented in the source, not regenerated |
| Stricter-check example figure (id 12, "Net interest margin") | 1.54% | `eval/gold_check.md` | `python -m eval.check_gold` |

Example row, for the format only:
`| Test AUC | 0.58 (0.55 to 0.61) | reports/metrics.json#auc | make eval |`
