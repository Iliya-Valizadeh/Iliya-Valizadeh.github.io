"""Tests for the project pages and the number additions of
docs/decisions/0008-project-pages.md. All offline, against `tests/fixtures/`.
"""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

import pytest

import build as build_module
from scripts.check_numbers import allowed_values
from scripts.shared.render_readme import (
    ClaimRow,
    NumberConfig,
    OfflineFetcher,
    ProjectConfig,
    RenderError,
    load_config,
)

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
PAGES = {
    "credit-risk-scorecard": "projects/credit-risk-scorecard",
    "bank-filings-rag": "projects/bank-filings-rag",
    "second-look": "for-everyone/second-look",
}


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    base = tmp_path_factory.mktemp("project_pages")
    site_dir, md_dir = base / "_site", base / "_build" / "md"
    orig = build_module.SITE_DIR, build_module.BUILD_MD_DIR
    build_module.SITE_DIR, build_module.BUILD_MD_DIR = site_dir, md_dir
    try:
        build_module.build(offline=True)
    finally:
        build_module.SITE_DIR, build_module.BUILD_MD_DIR = orig
    return site_dir, md_dir


def _html(built: tuple[Path, Path], repo: str) -> str:
    return (built[0] / f"{PAGES[repo]}.html").read_text(encoding="utf-8")


def _md(built: tuple[Path, Path], repo: str) -> str:
    return (built[1] / f"{PAGES[repo]}.md").read_text(encoding="utf-8")


# ------------------------------------------------------------------ the pages


@pytest.mark.parametrize("repo", sorted(PAGES))
def test_each_page_links_back_from_its_folder(built: tuple[Path, Path], repo: str) -> None:
    html = _html(built, repo)
    assert 'href="../static/style.css"' in html
    assert '<script src="../static/site.js">' in html
    assert 'href="../about.html"' in html
    assert 'href="../index.html#work"' in html
    assert f'href="https://github.com/Iliya-Valizadeh/{repo}"' in html


@pytest.mark.parametrize("repo", sorted(PAGES))
def test_each_page_says_what_is_weak(built: tuple[Path, Path], repo: str) -> None:
    html = _html(built, repo)
    match = re.search(r'<aside class="weak"[^>]*>(.*?)</aside>', html, re.S)
    assert match, f"{repo} has no 'What's weak' box"
    assert "What's weak" in match.group(1)
    assert "<li>" in match.group(1)
    assert "docs/whats_weak.md" in match.group(1)


def test_home_cards_link_to_each_page(built: tuple[Path, Path]) -> None:
    home = (built[0] / "index.html").read_text(encoding="utf-8")
    for path in PAGES.values():
        assert f'href="{path}.html"' in home


def test_credit_page_numbers_come_from_the_fixtures(built: tuple[Path, Path]) -> None:
    md = _md(built, "credit-risk-scorecard")
    for text in ("307,511", "0.769", "0.752", "0.745 to 0.759", "39.5%", "8.07%", "0.876"):
        assert text in md, text
    assert "0.7703" in md and "0.7687" in md
    assert "<table>" in _html(built, "credit-risk-scorecard")


def test_bank_page_numbers_come_from_the_fixtures(built: tuple[Path, Path]) -> None:
    md = _md(built, "bank-filings-rag")
    for text in ("256", "981", "96%", "0.58", "0.25", "0.50", "0.67", "0.70"):
        assert text in md, text


def test_second_look_page_leads_with_the_failed_bar(built: tuple[Path, Path]) -> None:
    md = _md(built, "second-look")
    for text in ("0.861", "0.90", "0.4589", "0.50"):
        assert text in md, text
    assert "did not pass the bar" in md


def test_second_look_page_says_synthetic_in_every_sentence_with_a_number(
    built: tuple[Path, Path],
) -> None:
    text = " ".join(_md(built, "second-look").split())
    has_number = re.compile(r"\d[.,]\d|\d%")
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text) if has_number.search(s)]
    assert sentences
    for sentence in sentences:
        assert "synthetic" in sentence.lower(), sentence


def test_second_look_page_never_says_fraud_and_links_the_live_tool(
    built: tuple[Path, Path],
) -> None:
    html = _html(built, "second-look")
    assert "fraud" not in html.lower()
    assert "fraud" not in _md(built, "second-look").lower()
    assert 'href="https://iliya-valizadeh.github.io/second-look/"' in html


def test_second_look_page_shows_no_unbuilt_demo_and_no_lighthouse(
    built: tuple[Path, Path],
) -> None:
    md = _md(built, "second-look").lower()
    assert "find it in the report" not in md
    assert "lighthouse" not in md


def test_all_synthetic_page_needs_the_word_for_any_number() -> None:
    numbers = build_module.Numbers(values={"a.x": "0.50"}, synthetic=set(), flags={}, sources={})
    text = "The bar was {{ a.x }}."
    assert build_module.fill_text(text, numbers, {}, "t") == "The bar was 0.50."
    with pytest.raises(build_module.BuildError, match="synthetic"):
        build_module.fill_text(text, numbers, {}, "t", all_synthetic=True)


# ------------------------------------------------------------------ number additions


def test_check_numbers_allows_the_new_kinds_of_number() -> None:
    allowed = allowed_values(load_config(ROOT / "projects.toml"), OfflineFetcher(FIXTURES))
    assert Decimal("307511") in allowed  # thousands commas
    assert Decimal("0.876") in allowed  # second results file
    assert Decimal("0.50") in allowed  # list item and row entry
    assert Decimal("256") in allowed  # row entry from a Markdown report
    assert Decimal("0.96") in allowed  # "96%" read as a share


def test_json_number_reads_list_items_and_rejects_bad_paths() -> None:
    data = {"results": [{"v": 0.5}, {"v": 0.25}]}
    assert build_module.json_number(data, "results.1.v") == Decimal("0.25")
    for path in ("results.2.v", "results.x.v", "missing"):
        with pytest.raises(RenderError, match="not found"):
            build_module.json_number(data, path)
    with pytest.raises(RenderError, match="not a number"):
        build_module.json_number({"a": True}, "a")


def test_cell_numbers_keeps_thousands_together() -> None:
    assert build_module.cell_numbers("307,511; 244; 8.07%") == ["307,511", "244", "8.07%"]
    assert build_module.cell_numbers("170,769, 854, 0.26%") == ["170,769", "854", "0.26%"]
    assert build_module.cell_numbers("0.2414, 0.7772") == ["0.2414", "0.7772"]


def test_cell_matches_reads_commas_only_for_thousands() -> None:
    plain = NumberConfig(id="x", path="p", row="r", decimals=0, percent=False, thousands=False)
    grouped = NumberConfig(id="x", path="p", row="r", decimals=0, percent=False, thousands=True)
    assert build_module.cell_matches("307,511; 244", "307,511", grouped)
    assert not build_module.cell_matches("307,511; 244", "307511", plain)


def _row(value: str, source: str) -> list[ClaimRow]:
    return [ClaimRow(claim="The row", value=value, source=source)]


def test_row_entry_reads_the_value_cell_as_written() -> None:
    entry = build_module.RowNumber(id="x", row="The row", index=1)
    assert build_module.row_value(_row("0.80; 96%", "reports/a.md"), entry, "r") == "96%"


def test_row_entry_is_refused_for_a_json_source() -> None:
    entry = build_module.RowNumber(id="x", row="The row", index=0)
    with pytest.raises(RenderError, match="JSON entry"):
        build_module.row_value(_row("0.5", "reports/metrics.json#a"), entry, "r")


def test_row_entry_needs_a_number_at_its_index() -> None:
    entry = build_module.RowNumber(id="x", row="The row", index=3)
    with pytest.raises(RenderError, match="no number at index"):
        build_module.row_value(_row("0.5", "src/a.py"), entry, "r")


def test_a_number_id_used_twice_fails() -> None:
    site = [
        build_module.SiteProject(
            repo="bank-filings-rag",
            kind="work",
            row_numbers=(
                build_module.RowNumber("dup", "Fixed-chunk size, in words", 0),
                build_module.RowNumber("dup", "Fixed-chunk size, in words", 0),
            ),
        )
    ]
    config = [
        ProjectConfig(repo="bank-filings-rag", metrics_file="reports/metrics.json", numbers=())
    ]
    with pytest.raises(build_module.BuildError, match="defined twice"):
        build_module.fetch_numbers(config, site, OfflineFetcher(FIXTURES))


@pytest.mark.parametrize(
    ("entry", "message"),
    [
        (
            'repo = "a"\nkind = "work"\ntitle = "t"\nsummary = "s"\n'
            '[[project.row_number]]\nid = "x"\nrow = "r"\nindex = -1',
            "index of 0 or more",
        ),
        (
            'repo = "a"\nkind = "standard"\n[[project.row_number]]\nid = "x"\nrow = "r"\nindex = 0',
            "no card",
        ),
    ],
)
def test_bad_row_number_config_fails(tmp_path: Path, entry: str, message: str) -> None:
    path = tmp_path / "projects.toml"
    path.write_text(f"[[project]]\n{entry}\n", encoding="utf-8")
    with pytest.raises(build_module.BuildError, match=message):
        build_module.load_site_projects(path)
