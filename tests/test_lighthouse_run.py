"""Tests for the pure parts of scripts/lighthouse_run.py (the part that runs Chrome is not
tested here, because CI has no Chrome)."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import lighthouse_run as lh


def _report(**scores: float | None) -> dict[str, object]:
    return {"categories": {name: {"score": score} for name, score in scores.items()}}


def test_scores_are_whole_numbers_out_of_100() -> None:
    report = _report(performance=0.894, accessibility=1, **{"best-practices": 0.955}, seo=0.5)
    assert lh.scores_from_report(report) == {
        "performance": 89,
        "accessibility": 100,
        "best-practices": 96,
        "seo": 50,
    }


def test_a_missing_or_null_score_is_an_error_not_a_guess() -> None:
    with pytest.raises(ValueError, match="no categories.seo"):
        lh.scores_from_report(_report(performance=1, accessibility=1, **{"best-practices": 1}))
    with pytest.raises(ValueError, match="null"):
        lh.scores_from_report(
            _report(performance=None, accessibility=1, **{"best-practices": 1}, seo=1)
        )


def test_scores_can_be_limited_to_some_categories() -> None:
    report = _report(accessibility=0.97)
    assert lh.scores_from_report(report, ("accessibility",)) == {"accessibility": 97}


def _page(perf: int, dark: int | None = None) -> dict[str, dict[str, int]]:
    full = {"performance": perf, "accessibility": 100, "best-practices": 100, "seo": 100}
    page = {"mobile": dict(full), "desktop": dict(full)}
    if dark is not None:
        page["dark"] = {"accessibility": dark}
    return page


def test_summary_takes_the_lowest_score_and_checks_the_90_line() -> None:
    summary = lh.summarise({"a.html": _page(95, 100), "b.html": _page(90, 98)})
    assert summary["lowest"]["mobile"]["performance"] == 90
    assert summary["lowest"]["dark"] == {"accessibility": 98}
    assert summary["every_score_at_least_90"] is True
    failing = lh.summarise({"a.html": _page(89)})
    assert failing["every_score_at_least_90"] is False


def test_a_low_dark_score_fails_the_summary() -> None:
    assert lh.summarise({"a.html": _page(100, 80)})["every_score_at_least_90"] is False


def test_build_report_keeps_the_version_and_pages() -> None:
    runs = {"a.html": _page(95)}
    report = lh.build_report(runs, "12.8.2", "2026-10-20T00:00:00Z")
    assert report["tool"] == "Lighthouse 12.8.2"
    assert report["pages"] == runs
    assert "dark" not in report["summary"]["lowest"]


def test_page_paths_skip_static_files_and_the_search_console_file(tmp_path: Path) -> None:
    for rel in ("index.html", "notes/index.html", "googleabc.html", "static/x.html"):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("<html></html>", encoding="utf-8")
    assert lh.page_paths(tmp_path) == ["index.html", "notes/index.html"]
