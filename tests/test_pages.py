"""Tests for the Home and About pages, per docs/decisions/0007 and 0015.

All offline, against `tests/fixtures/`.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

import build as build_module
from scripts.shared.render_readme import OfflineFetcher, load_config

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
HACK_THE_NORTH_RE = re.compile(r"hack\W*the\W*north", re.IGNORECASE)


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    base = tmp_path_factory.mktemp("pages")
    site_dir, md_dir = base / "_site", base / "_build" / "md"
    orig = build_module.SITE_DIR, build_module.BUILD_MD_DIR
    build_module.SITE_DIR, build_module.BUILD_MD_DIR = site_dir, md_dir
    try:
        build_module.build(offline=True)
    finally:
        build_module.SITE_DIR, build_module.BUILD_MD_DIR = orig
    return site_dir, md_dir


def _home(built: tuple[Path, Path]) -> str:
    return (built[0] / "index.html").read_text(encoding="utf-8")


def _numbers() -> build_module.Numbers:
    config = load_config(build_module.CONFIG_PATH)
    site = build_module.load_site_projects(build_module.CONFIG_PATH)
    return build_module.fetch_numbers(config, site, OfflineFetcher(FIXTURES))


# ------------------------------------------------------------------ the Home page


def test_home_leads_with_the_three_featured_projects_in_order(built: tuple[Path, Path]) -> None:
    ids = re.findall(r'<article class="project" id="([^"]+)">', _home(built))
    assert ids == ["nyc-rideshare-congestion", "bank-filings-rag", "credit-risk-scorecard"]


def test_home_lists_the_other_projects_and_no_standard(built: tuple[Path, Path]) -> None:
    ids = re.findall(r'<li id="([^"]+)">', _home(built))
    assert ids == ["second-look", "household-credit-stress", "ds-project-standard"]


def test_home_numbers_come_from_the_fixtures(built: tuple[Path, Path]) -> None:
    html = _home(built)
    assert ">ROC-AUC</a> of 0.769 on the test set (95% interval 0.762 to 0.775)" in html
    assert "0.58 of the time (95% interval 0.33 to 0.83)" in html
    assert "kept 532,128,361 rows and set aside 114,113 rows" in html
    assert "The congestion pricing result is still to come." in html


def test_home_charts_link_their_source_files(built: tuple[Path, Path]) -> None:
    html = _home(built)
    charts = {
        "bank-filings-rag-hit-at-5.png": "bank-filings-rag/blob/main/reports/figures/hit_at_5.png",
        "credit-risk-scorecard-calibration.png": (
            "credit-risk-scorecard/blob/main/reports/figures/calibration.png"
        ),
    }
    for chart, source in charts.items():
        assert f'<img src="static/charts/{chart}" alt="' in html
        assert f'href="https://github.com/Iliya-Valizadeh/{source}"' in html
    assert len(re.findall(r'<img [^>]*alt="[^"]{40,}"', html)) == 2


def test_home_links_the_live_tool_and_the_resume(built: tuple[Path, Path]) -> None:
    html = _home(built)
    assert 'href="https://iliya-valizadeh.github.io/second-look/"' in html
    assert '<a href="static/resume.pdf">Resume (PDF)</a>' in html


def test_home_says_co_op_and_dates(built: tuple[Path, Path]) -> None:
    html = _home(built)
    assert "in York&#x27;s co-op program." in html or "in York's co-op program." in html
    assert "Winter 2027 co-op" in html
    assert "Summer 2027 internship" in html
    assert "April 2028" in html
    assert "co-op stream" not in html


def test_home_shows_the_failed_bar_from_metrics(built: tuple[Path, Path]) -> None:
    assert "under the bar I set before the first test" in _home(built)


def test_home_has_none_of_the_removed_decoration(built: tuple[Path, Path]) -> None:
    html = _home(built)
    for gone in ("predict_proba", 'class="dot', "Move something", 'id="risk"', 'id="fit"'):
        assert gone not in html


def test_markdown_record_holds_every_page(built: tuple[Path, Path]) -> None:
    names = sorted(p.relative_to(built[1]).as_posix() for p in built[1].rglob("*.md"))
    assert names == [
        "about.md",
        "drafts/notes/a-quarter-of-each-page.md",
        "drafts/notes/removing-gender-from-a-credit-model.md",
        "drafts/notes/the-fix-that-broke-my-probabilities.md",
        "for-everyone/second-look.md",
        "index.md",
        "notes/index.md",
        "projects/bank-filings-rag.md",
        "projects/credit-risk-scorecard.md",
    ]
    for path in built[1].rglob("*.md"):
        assert not HACK_THE_NORTH_RE.search(path.read_text(encoding="utf-8"))


MADE_UP_PAGE = """---
title: A made-up example
description: Only here for a test.
---
<!-- slot: lede -->
Lede.
<!-- slot: main -->
Main.
<!-- slot: weak -->
Weak.
<!-- slot: next -->
Next.
"""


def test_a_new_featured_project_needs_no_template_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ADR 0008 and ADR 0015: adding a project is one config entry and one page."""
    extra = (
        '\n[[project]]\nrepo = "made-up-example"\nkind = "featured"\nmetrics = false\n'
        'title = "A made-up example"\nresult = "Only here for a test."\n'
        'page = "projects/made-up-example.html"\n'
    )
    config_path = tmp_path / "projects.toml"
    config_path.write_text(
        build_module.CONFIG_PATH.read_text(encoding="utf-8") + extra, encoding="utf-8"
    )
    content = tmp_path / "content"
    shutil.copytree(build_module.CONTENT_DIR, content)
    monkeypatch.setattr(build_module, "CONFIG_PATH", config_path)
    monkeypatch.setattr(build_module, "CONTENT_DIR", content)
    monkeypatch.setattr(build_module, "SITE_DIR", tmp_path / "_site")
    monkeypatch.setattr(build_module, "BUILD_MD_DIR", tmp_path / "_build" / "md")

    # With a page set but no content file for it, the build stops.
    with pytest.raises(build_module.BuildError, match="missing content"):
        build_module.build(offline=True)

    (content / "projects" / "made-up-example.md").write_text(MADE_UP_PAGE, encoding="utf-8")
    build_module.build(offline=True)
    html = (tmp_path / "_site" / "index.html").read_text(encoding="utf-8")
    ids = re.findall(r'<article class="project" id="([^"]+)">', html)
    assert ids[-1] == "made-up-example"
    assert 'href="projects/made-up-example.html"' in html
    assert (tmp_path / "_site" / "projects" / "made-up-example.html").is_file()


def test_png_size_reads_the_header_and_rejects_other_files(tmp_path: Path) -> None:
    chart = build_module.CHARTS_DIR / "credit-risk-scorecard-calibration.png"
    assert build_module.png_size(chart) == (597, 609)
    bad = tmp_path / "x.png"
    bad.write_bytes(b"not a png at all, just some bytes")
    with pytest.raises(build_module.BuildError, match="not a PNG"):
        build_module.png_size(bad)


# ------------------------------------------------------------------ number and flag rules


def test_synthetic_number_needs_the_word_in_its_sentence() -> None:
    numbers = _numbers()
    text = "Recall is {{ second_look.recurring_recall }}. These statements are synthetic."
    with pytest.raises(build_module.BuildError, match="synthetic"):
        build_module.fill_text(text, numbers, {}, "test")


def test_synthetic_number_passes_when_its_sentence_says_so() -> None:
    numbers = _numbers()
    text = "On synthetic statements, recall is {{ second_look.recurring_recall }}."
    assert build_module.fill_text(text, numbers, {}, "test").endswith("0.9588.")


def test_unknown_number_placeholder_fails() -> None:
    with pytest.raises(build_module.BuildError, match="unknown number"):
        build_module.fill_text("{{ nope.nothing }}", _numbers(), {}, "test")


@pytest.mark.parametrize(("value", "expected"), [(True, "yes"), (False, "no")])
def test_flag_picks_its_sentence(value: bool, expected: str) -> None:
    flag = build_module.Flag(id="x.flag", path="p", if_true="yes", if_false="no")
    numbers = build_module.Numbers(values={}, synthetic=set(), flags={"x.flag": value}, sources={})
    assert build_module.fill_text("{{ x.flag }}", numbers, {"x.flag": flag}, "t") == expected


def test_json_flag_rejects_a_missing_path_and_a_non_boolean() -> None:
    with pytest.raises(build_module.BuildError, match="not found"):
        build_module.json_flag({"a": {}}, "a.b")
    with pytest.raises(build_module.BuildError, match="true or false"):
        build_module.json_flag({"a": 1}, "a")


def test_synthetic_number_in_a_featured_result_needs_the_word() -> None:
    project = build_module.SiteProject(
        repo="second-look",
        kind="featured",
        title="t",
        result="Recall is {{ second_look.recurring_recall }}.",
    )
    with pytest.raises(build_module.BuildError, match="synthetic"):
        build_module.featured_entry(project, _numbers(), {})


# ------------------------------------------------------------------ config and content errors


@pytest.mark.parametrize(
    ("entry", "message"),
    [
        ('repo = "a"\nkind = "work"', "kind must be"),
        ('repo = "a"\nkind = "featured"\ntitle = "t"', "title and a result"),
        ('repo = "a"\nkind = "other"\ntitle = "t"', "title and a summary"),
        ('repo = "a"\nkind = "standard"\ntitle = "t"', "no entry"),
        (
            'repo = "a"\nkind = "featured"\ntitle = "t"\nresult = "r"\nchart = "c.png"',
            "go together",
        ),
        (
            'repo = "a"\nkind = "featured"\ntitle = "t"\nresult = "r"\nchart = "none.png"\n'
            'chart_source = "s"\nchart_alt = "a"\nchart_caption = "c"',
            "chart file not found",
        ),
        (
            'repo = "a"\nkind = "other"\ntitle = "t"\nsummary = "s"\nchart = "c.png"\n'
            'chart_source = "s"\nchart_alt = "a"\nchart_caption = "c"',
            "only a featured",
        ),
        ('repo = "a"\nkind = "other"\ntitle = "t"\nsummary = "s"\npage = "../x.html"', "page must"),
    ],
)
def test_bad_site_config_fails(tmp_path: Path, entry: str, message: str) -> None:
    path = tmp_path / "projects.toml"
    path.write_text(f"[[project]]\n{entry}\n", encoding="utf-8")
    with pytest.raises(build_module.BuildError, match=message):
        build_module.load_site_projects(path)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("---\ntitle: t\n---\n<!-- slot: a -->\nx\n", "needs 'description'"),
        ("---\ntitle t\n---\n", "has no ':'"),
        ("---\ntitle: t\ndescription: d\n---\nstray\n<!-- slot: a -->\nx\n", "before the first"),
    ],
)
def test_bad_content_file_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, text: str, message: str
) -> None:
    (tmp_path / "page.md").write_text(text, encoding="utf-8")
    monkeypatch.setattr(build_module, "CONTENT_DIR", tmp_path)
    with pytest.raises(build_module.BuildError, match=message):
        build_module.read_content("page.md")


def test_missing_content_file_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(build_module, "CONTENT_DIR", tmp_path)
    with pytest.raises(build_module.BuildError, match="missing content"):
        build_module.read_content("nope.md")
