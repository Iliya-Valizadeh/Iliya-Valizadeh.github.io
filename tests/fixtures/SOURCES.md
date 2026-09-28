# Where the offline fixtures came from

Per docs/decisions/0002-where-each-number-comes-from.md. Each fixture file is an
exact copy of that repo's file at the commit named here, on its `main` branch. To
refresh a fixture, copy the file again from a newer commit and update the commit
here; nothing else in the tests needs to change unless the file's shape changed too.

- `credit-risk-scorecard` at `35a17fd2454ced157bdab00dc6b0301e67893240`: `reports/metrics.json` and `CLAIMS.md`
- `bank-filings-rag` at `45246f8af21e907912d5611ccadb9158315255a3`: `reports/metrics.json` and `CLAIMS.md`
- `second-look` at `0da821d9af2c15782d4e60abfd54572c1d34d0be`: `reports/metrics.json` and `CLAIMS.md`

All three are used by `projects.toml`. `ds-project-standard` and `.github` have no
fixture, because they have no `reports/metrics.json` and the renderer never reads them.
