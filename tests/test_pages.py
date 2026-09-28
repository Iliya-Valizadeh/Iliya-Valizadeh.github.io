"""Tests for the Home and About pages, per docs/decisions/0007-home-and-about-pages.md.

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


def test_home_cards_are_work_then_tool_and_no_standard(built: tuple[Path, Path]) -> None:
    ids = re.findall(r'<article class="proj" id="([^"]+)">', _home(built))
    assert ids == ["credit-risk-scorecard", "bank-filings-rag", "second-look"]


def test_home_numbers_come_from_the_fixtures(built: tuple[Path, Path]) -> None:
    html = _home(built)
    assert '<div class="pmetric"><b>0.769</b>' in html
    assert '<div class="pmetric"><b>0.58</b>' in html
    assert '<div class="pmetric"><b>0.9588</b><span>recurring recall, synthetic' in html


def test_home_links_the_live_tool(built: tuple[Path, Path]) -> None:
    assert 'href="https://iliya-valizadeh.github.io/second-look/"' in _home(built)


def test_home_says_seeking_a_co_op_and_the_idea(built: tuple[Path, Path]) -> None:
    html = _home(built)
    assert "Seeking a Winter 2027 co-op" in html
    assert "Data science that shows its work." in html


def test_home_shows_the_failed_bar_from_metrics(built: tuple[Path, Path]) -> None:
    assert "did not meet the bar I set" in _home(built)


def test_home_has_no_decorative_sparklines(built: tuple[Path, Path]) -> None:
    assert 'class="spk"' not in _home(built)


def test_pages_load_the_right_script(built: tuple[Path, Path]) -> None:
    assert '<script src="static/main.js">' in _home(built)
    about = (built[0] / "about.html").read_text(encoding="utf-8")
    assert '<script src="static/site.js">' in about


def test_markdown_record_holds_every_page(built: tuple[Path, Path]) -> None:
    names = sorted(p.relative_to(built[1]).as_posix() for p in built[1].rglob("*.md"))
    assert names == [
        "about.md",
        "drafts/notes/a-quarter-of-each-page.md",
        "for-everyone/second-look.md",
        "index.md",
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


def test_a_new_work_project_gets_a_card_with_no_template_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ADR 0003 and ADR 0008: adding a project is one config entry and one page."""
    extra = (
        '\n[[project]]\nrepo = "made-up-example"\nkind = "work"\nmetrics = false\n'
        'title = "A made-up example"\nsummary = "Only here for a test."\n'
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

    # With no page of its own, the build stops: no card without a page.
    with pytest.raises(build_module.BuildError, match="missing content"):
        build_module.build(offline=True)

    (content / "projects" / "made-up-example.md").write_text(MADE_UP_PAGE, encoding="utf-8")
    build_module.build(offline=True)
    html = (tmp_path / "_site" / "index.html").read_text(encoding="utf-8")
    ids = re.findall(r'<article class="proj" id="([^"]+)">', html)
    assert ids == ["credit-risk-scorecard", "bank-filings-rag", "made-up-example", "second-look"]
    assert 'href="projects/made-up-example.html"' in html
    assert (tmp_path / "_site" / "projects" / "made-up-example.html").is_file()


# ------------------------------------------------------------------ site.js


def test_site_js_blocks_are_copied_from_main_js() -> None:
    main = (ROOT / "static" / "main.js").read_text(encoding="utf-8")
    site = (ROOT / "static" / "site.js").read_text(encoding="utf-8")
    blocks = re.findall(r"/\* [a-z +,]+ \*/\n\(function\(\)\{.*?\n\}\)\(\);", site, re.S)
    assert len(blocks) == 4
    for block in blocks:
        assert block in main


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


def test_synthetic_metric_label_must_say_synthetic() -> None:
    project = build_module.SiteProject(
        repo="second-look",
        kind="tool",
        title="t",
        summary="s",
        metric="second_look.recurring_recall",
        metric_label="recall",
    )
    with pytest.raises(build_module.BuildError, match="synthetic"):
        build_module.project_card(1, project, _numbers(), {})


def test_metric_must_be_a_configured_number() -> None:
    project = build_module.SiteProject(
        repo="r", kind="work", title="t", summary="s", metric="no.such", metric_label="x"
    )
    with pytest.raises(build_module.BuildError, match="not a number"):
        build_module.project_card(1, project, _numbers(), {})


# ------------------------------------------------------------------ config and content errors


@pytest.mark.parametrize(
    ("entry", "message"),
    [
        ('repo = "a"\nkind = "other"', "kind must be"),
        ('repo = "a"\nkind = "work"', "title and a summary"),
        ('repo = "a"\nkind = "standard"\ntitle = "t"', "no card"),
        ('repo = "a"\nkind = "work"\ntitle = "t"\nsummary = "s"\nmetric = "m"', "go together"),
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
