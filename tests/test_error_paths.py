"""Error branches in build.py and scripts/check_numbers.py: a bad CLAIMS.md match,
a missing partial, a missing verification file, and the CLI entry points.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

import build as build_module
import scripts.check_numbers as check_numbers_module
from scripts.shared.render_readme import NumberConfig, OfflineFetcher, ProjectConfig, RenderError

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"


def test_load_partial_missing_file_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(build_module, "PARTIALS_DIR", tmp_path)
    with pytest.raises(build_module.BuildError):
        build_module.load_partial("does-not-exist")


def test_copy_static_overwrites_an_existing_destination(tmp_path: Path) -> None:
    site_dir = tmp_path / "_site"
    (site_dir / "static").mkdir(parents=True)
    (site_dir / "static" / "stale.txt").write_text("old", encoding="utf-8")
    build_module.copy_static(site_dir)
    assert (site_dir / "static" / "style.css").is_file()
    assert not (site_dir / "static" / "stale.txt").exists()


def test_copy_verification_file_missing_source_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(build_module, "ROOT", tmp_path)
    with pytest.raises(build_module.BuildError):
        build_module.copy_verification_file(tmp_path)


def _bad_config(row: str, path: str) -> list[ProjectConfig]:
    number = NumberConfig(id="x", path=path, row=row, decimals=3, percent=False, thousands=False)
    return [
        ProjectConfig(
            repo="credit-risk-scorecard",
            metrics_file="reports/metrics.json",
            numbers=(number,),
        )
    ]


def test_fetch_sources_missing_claims_row_raises() -> None:
    fetcher = OfflineFetcher(FIXTURES)
    config = _bad_config("This row does not exist", "models.lightgbm.roc_auc")
    with pytest.raises(RenderError):
        build_module.fetch_sources(config, fetcher)


def test_fetch_sources_source_mismatch_raises() -> None:
    fetcher = OfflineFetcher(FIXTURES)
    # Real row, but a path its Source cell (no #key, whole-file) still covers, so
    # force a mismatch by pointing metrics_file at a different file than the row names.
    config = [
        ProjectConfig(
            repo="credit-risk-scorecard",
            metrics_file="reports/other.json",
            numbers=(
                NumberConfig(
                    id="x",
                    path="models.lightgbm.roc_auc",
                    row="ROC-AUC and PR-AUC by model, with 95% intervals",
                    decimals=3,
                    percent=False,
                    thousands=False,
                ),
            ),
        )
    ]
    with pytest.raises(RenderError):
        build_module.fetch_sources(config, fetcher)


def test_fetch_sources_value_mismatch_raises() -> None:
    fetcher = OfflineFetcher(FIXTURES)
    # A real, matching row, but decimals=6 formats a value ("0.768740") that is not
    # literally written in the Value cell ("0.769 (0.762-0.775)").
    bad = [
        ProjectConfig(
            repo="credit-risk-scorecard",
            metrics_file="reports/metrics.json",
            numbers=(
                NumberConfig(
                    id="x",
                    path="models.lightgbm.roc_auc",
                    row="ROC-AUC and PR-AUC by model, with 95% intervals",
                    decimals=6,
                    percent=False,
                    thousands=False,
                ),
            ),
        )
    ]
    with pytest.raises(RenderError):
        build_module.fetch_sources(bad, fetcher)


def test_build_removes_a_previously_built_site(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    site_dir = tmp_path / "_site"
    build_md_dir = tmp_path / "_build" / "md"
    monkeypatch.setattr(build_module, "SITE_DIR", site_dir)
    monkeypatch.setattr(build_module, "BUILD_MD_DIR", build_md_dir)
    site_dir.mkdir(parents=True)
    (site_dir / "stale.txt").write_text("old", encoding="utf-8")
    build_module.build(offline=True)
    assert not (site_dir / "stale.txt").exists()
    assert (site_dir / "index.html").is_file()


def test_main_reports_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(build_module, "SITE_DIR", tmp_path / "_site")
    monkeypatch.setattr(build_module, "BUILD_MD_DIR", tmp_path / "_build" / "md")
    assert build_module.main(["--offline"]) == 0


def test_main_reports_failure_on_a_build_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(build_module, "SITE_DIR", tmp_path / "_site")
    monkeypatch.setattr(build_module, "BUILD_MD_DIR", tmp_path / "_build" / "md")
    monkeypatch.setattr(build_module, "PARTIALS_DIR", tmp_path / "no-partials-here")
    assert build_module.main(["--offline"]) == 1


def test_check_numbers_main_passes_on_a_clean_folder(tmp_path: Path) -> None:
    empty_md = tmp_path / "md"
    empty_md.mkdir()
    assert check_numbers_module.main(["--offline", str(empty_md)]) == 0


def test_check_numbers_main_fails_on_a_typed_number(tmp_path: Path) -> None:
    bad_md = tmp_path / "page.md"
    bad_md.write_text("A made-up figure of 0.4242 appears here.\n", encoding="utf-8")
    assert check_numbers_module.main(["--offline", str(bad_md)]) == 1


def test_check_numbers_main_fails_when_the_pipeline_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bad_config = _bad_config("This row does not exist in CLAIMS.md", "models.lightgbm.roc_auc")
    monkeypatch.setattr(check_numbers_module, "load_config", lambda _path: bad_config)
    empty_md = tmp_path / "md"
    empty_md.mkdir()
    assert check_numbers_module.main(["--offline", str(empty_md)]) == 1


def test_forms_includes_the_percent_reading() -> None:
    config = NumberConfig(id="x", path="a", row="r", decimals=0, percent=True, thousands=False)
    assert check_numbers_module._forms("8%", config) == {Decimal("8"), Decimal("0.08")}
