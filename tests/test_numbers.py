"""Tests for scripts/check_numbers.py and the number pipeline it shares with build.py.

Per docs/decisions/0002-where-each-number-comes-from.md: every number `projects.toml`
defines must already be a matching CLAIMS.md row in its own repo, and no page may
contain a claim-like number that did not come from a number placeholder. All of this
runs offline, against `tests/fixtures/`.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from scripts.check_numbers import allowed_values, find_bad_numbers
from scripts.shared.render_readme import OfflineFetcher, RenderError, load_config

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"


@pytest.fixture(scope="module")
def allowed() -> set[Decimal]:
    config = load_config(ROOT / "projects.toml")
    fetcher = OfflineFetcher(FIXTURES)
    return allowed_values(config, fetcher)


def test_every_metrics_bearing_project_has_a_fixture() -> None:
    # ADR 0004: every project in projects.toml has fixture files, so no entry can
    # point at a repo that has no data.
    config = load_config(ROOT / "projects.toml")
    for project in config:
        if not project.numbers:
            continue
        assert (FIXTURES / project.repo / "CLAIMS.md").is_file(), project.repo
        assert (FIXTURES / project.repo / "reports_metrics.json").is_file(), project.repo


def test_allowed_values_covers_the_real_headline_numbers(allowed: set[Decimal]) -> None:
    # From _portfolio/STATUS.md's "Real headline numbers", at the same fixture commits.
    assert Decimal("0.769") in allowed  # credit-risk-scorecard LightGBM ROC-AUC
    assert Decimal("0.58") in allowed  # bank-filings-rag hit@5
    assert Decimal("0.9588") in allowed  # second-look recurring recall


def test_a_number_not_in_the_allowed_set_fails(tmp_path: Path, allowed: set[Decimal]) -> None:
    bad = tmp_path / "page.md"
    bad.write_text("The model reaches 0.4242 on the held-out set.\n", encoding="utf-8")
    errors = find_bad_numbers([str(bad)], allowed)
    assert errors, "a made-up number should be flagged"


def test_a_number_in_the_allowed_set_passes(tmp_path: Path, allowed: set[Decimal]) -> None:
    good = tmp_path / "page.md"
    good.write_text("The headline hit@5 is 0.58 on the hand-checked questions.\n", encoding="utf-8")
    errors = find_bad_numbers([str(good)], allowed)
    assert errors == []


def test_small_whole_numbers_and_years_are_never_flagged(
    tmp_path: Path, allowed: set[Decimal]
) -> None:
    page = tmp_path / "page.md"
    page.write_text("Written in 2026, across three repos, over 5 years.\n", encoding="utf-8")
    errors = find_bad_numbers([str(page)], allowed)
    assert errors == []


def test_missing_claims_row_raises(tmp_path: Path) -> None:
    bad_toml = tmp_path / "projects.toml"
    bad_toml.write_text(
        """
[[project]]
repo = "credit-risk-scorecard"
metrics_file = "reports/metrics.json"

[[project.number]]
id = "x"
path = "models.lightgbm.roc_auc"
row = "This row does not exist in CLAIMS.md"
decimals = 3
""",
        encoding="utf-8",
    )
    config = load_config(bad_toml)
    fetcher = OfflineFetcher(FIXTURES)
    with pytest.raises(RenderError):
        allowed_values(config, fetcher)
