# Where the offline fixtures came from

Per docs/decisions/0002-where-each-number-comes-from.md. Each fixture file is an
exact copy of that repo's file at the commit named here, on its `main` branch. To
refresh a fixture, copy the file again from a newer commit and update the commit
here; nothing else in the tests needs to change unless the file's shape changed too.

- `credit-risk-scorecard` at `b9638595eb94b93c7fe4db22bb21b02a63ee22bf`: `reports/metrics.json`, `reports/gender_check.json` and `CLAIMS.md`
- `bank-filings-rag` at `222548390393096b31dfd77963a46e7f404db62f`: `reports/metrics.json` and `CLAIMS.md`
- `second-look` at `4a53ecf4e571e75b2d538ce76fb81f5d1a571e99`: `reports/metrics.json` and `CLAIMS.md`
- `nyc-rideshare-congestion` at `05717f6cd9f02ef59ed9dfbc700a0e986a9ca56a`: `reports/load_summary.json`, `reports/source_manifest.json` and `CLAIMS.md`

All four are used by `projects.toml`. `household-credit-stress`, `ds-project-standard`
and `.github` have no fixture, because the site reads no numbers from them.
