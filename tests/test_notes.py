"""Tests for notes, and the draft rules of ADR 0005 (drafts stay out of the site).

All offline, against `tests/fixtures/`. The real note in `notes/` is still a draft, so
it must be missing from every file under `_site/`, whatever pages (a Notes index, a
feed) later tasks add there.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import build as build_module
from scripts.shared.render_readme import OfflineFetcher, load_config

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
REAL_NOTE = ROOT / "notes" / "a-quarter-of-each-page.md"
REAL_NOTES = sorted((ROOT / "notes").glob("*.md"))
MARKER = "DRAFT: Iliya to edit"

NOTE_BODY = """---
title: A made-up note
description: Only here for a test.
---
Some text.
"""


def _build_into(base: Path, notes_dir: Path | None = None) -> tuple[Path, Path]:
    site_dir, md_dir = base / "_site", base / "_build" / "md"
    orig = build_module.SITE_DIR, build_module.BUILD_MD_DIR, build_module.NOTES_DIR
    build_module.SITE_DIR, build_module.BUILD_MD_DIR = site_dir, md_dir
    if notes_dir is not None:
        build_module.NOTES_DIR = notes_dir
    try:
        build_module.build(offline=True)
    finally:
        build_module.SITE_DIR, build_module.BUILD_MD_DIR, build_module.NOTES_DIR = orig
    return site_dir, md_dir


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    return _build_into(tmp_path_factory.mktemp("notes"))


def _numbers() -> build_module.Numbers:
    config = load_config(build_module.CONFIG_PATH)
    site = build_module.load_site_projects(build_module.CONFIG_PATH)
    return build_module.fetch_numbers(config, site, OfflineFetcher(FIXTURES))


# ------------------------------------------------------------------ the real draft note


def _title(note: Path) -> str:
    for line in note.read_text(encoding="utf-8").splitlines():
        if line.startswith("title: "):
            return line.removeprefix("title: ")
    raise AssertionError(f"{note} has no title")


def test_all_three_real_notes_are_there() -> None:
    assert [p.stem for p in REAL_NOTES] == [
        "a-quarter-of-each-page",
        "removing-gender-from-a-credit-model",
        "the-fix-that-broke-my-probabilities",
    ]


@pytest.mark.parametrize("note", REAL_NOTES, ids=lambda p: p.stem)
def test_real_note_starts_with_the_draft_marker(note: Path) -> None:
    first = note.read_text(encoding="utf-8").lstrip("﻿").splitlines()[0]
    assert first == MARKER


def test_draft_notes_are_left_out_of_the_built_site(built: tuple[Path, Path]) -> None:
    site_dir = built[0]
    assert not (site_dir / "notes").exists()
    leaks = [MARKER] + [n.stem for n in REAL_NOTES] + [_title(n) for n in REAL_NOTES]
    for path in site_dir.rglob("*"):
        if path.is_file():
            text = path.read_bytes().decode("utf-8", errors="replace")
            for leak in leaks:
                assert leak not in text, (path, leak)


def test_draft_note_is_still_checked(built: tuple[Path, Path]) -> None:
    md = (built[1] / "drafts" / "notes" / f"{REAL_NOTE.stem}.md").read_text(encoding="utf-8")
    assert "{{" not in md
    assert MARKER not in md
    # Its numbers come from the fixtures' CLAIMS.md rows, like every other page.
    for value in ("256", "981", "96%", "0.58", "0.50", "0.25"):
        assert value in md
    assert "Chart: one bar for a median page of 981 word pieces." in md


def test_credit_notes_are_checked_with_their_numbers(built: tuple[Path, Path]) -> None:
    drafts = built[1] / "drafts" / "notes"
    pd_note = (drafts / "the-fix-that-broke-my-probabilities.md").read_text(encoding="utf-8")
    for value in ("39.5%", "8.07%", "8.0%", "0.1851", "0.0673", "0.769", "0.768", "45%"):
        assert value in pd_note
    for value in ("4,312,985,709", "642,168,648", "633,364,511"):
        assert value in pd_note
    gender = (drafts / "removing-gender-from-a-credit-model.md").read_text(encoding="utf-8")
    for value in ("84.5%", "72.3%", "83.2%", "75.2%", "13.1%", "14.4%", "23.9%", "20.9%"):
        assert value in gender
    for value in ("0.7703", "0.7687", "0.876", "10.2%", "7.0%", "7.4%", "9.2%", "20%"):
        assert value in gender
    for md in (pd_note, gender):
        assert "{{" not in md
        assert MARKER not in md


@pytest.mark.parametrize("note", REAL_NOTES, ids=lambda p: p.stem)
def test_draft_note_has_a_preview_page_with_its_chart(built: tuple[Path, Path], note: Path) -> None:
    preview = built[1].parent / "preview"
    html = (preview / "notes" / f"{note.stem}.html").read_text(encoding="utf-8")
    assert "{{" not in html
    assert "Draft, not published" in html
    assert html.count('<figure class="chart">') == 1
    assert html.count("<figcaption>") == 1
    assert 'href="../static/style.css"' in html
    assert (preview / "static" / "style.css").is_file()


# ------------------------------------------------------------------ draft and publish rules


@pytest.mark.parametrize(
    "text",
    [
        f"{MARKER}\n{NOTE_BODY}",
        f"﻿\n\n  \n{MARKER}\n{NOTE_BODY}",
        f"{MARKER}, then more words\n{NOTE_BODY}",
    ],
)
def test_a_draft_is_found_after_a_bom_and_blank_lines(text: str) -> None:
    published, rest = build_module.note_status(text, Path("n.md"))
    assert published == ""
    assert rest.lstrip("\n").startswith("---")


def test_a_published_note_keeps_its_date() -> None:
    published, _ = build_module.note_status(f"Published: 2026-10-01\n{NOTE_BODY}", Path("n.md"))
    assert published == "2026-10-01"


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (NOTE_BODY, "first line must be"),
        (f"Published: 2026-02-30\n{NOTE_BODY}", "not a real date"),
        (f"Published: soon\n{NOTE_BODY}", "first line must be"),
        (f"{MARKER}\n{NOTE_BODY}\n{MARKER}\n", "may only start the first line"),
        (f"Published: 2026-10-01\n{NOTE_BODY}\nsee {MARKER}\n", "may only start"),
        (f"{MARKER} {MARKER}\n{NOTE_BODY}", "may only start"),
    ],
)
def test_bad_note_status_fails(text: str, message: str) -> None:
    with pytest.raises(build_module.BuildError, match=message):
        build_module.note_status(text, Path("n.md"))


def test_a_published_note_gets_a_page_and_a_draft_does_not(tmp_path: Path) -> None:
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "out.md").write_text(f"Published: 2026-10-01\n{NOTE_BODY}", encoding="utf-8")
    (notes / "kept.md").write_text(f"{MARKER}\n{NOTE_BODY}", encoding="utf-8")
    site_dir, md_dir = _build_into(tmp_path, notes)
    page = (site_dir / "notes" / "out.html").read_text(encoding="utf-8")
    assert "Published 2026-10-01" in page
    assert (md_dir / "notes" / "out.md").is_file()
    assert not (site_dir / "notes" / "kept.html").exists()
    assert (md_dir / "drafts" / "notes" / "kept.md").is_file()


def test_the_marker_in_the_built_site_fails(tmp_path: Path) -> None:
    (tmp_path / "page.html").write_text(f"<p>{MARKER}</p>", encoding="utf-8")
    with pytest.raises(build_module.BuildError, match="reached the built site"):
        build_module.check_no_draft_marker(tmp_path)


# ------------------------------------------------------------------ charts


def test_chart_is_drawn_to_scale_from_the_built_numbers() -> None:
    svg, md = build_module.word_pieces_chart(_numbers())
    # 360 * 256 / 981, rounded to one decimal: the filled part of the bar.
    assert 'class="chart-read" x="20" y="40" width="93.9"' in svg
    assert ">981</text>" in svg
    assert "256" in md


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("Text.\n\n<!-- chart: nope -->\nCaption.\n", "unknown chart"),
        ("Text.\n\n<!-- chart: word_pieces -->\n", "needs a caption"),
    ],
)
def test_bad_chart_line_fails(body: str, message: str) -> None:
    with pytest.raises(build_module.BuildError, match=message):
        build_module.note_body(body, _numbers(), "notes/x.md")


def test_chart_needs_its_numbers() -> None:
    empty = build_module.Numbers(values={}, synthetic=set(), flags={}, sources={})
    with pytest.raises(build_module.BuildError, match="needs the limit"):
        build_module.word_pieces_chart(empty)
    wrong = build_module.Numbers(
        values={
            "bank_filings_rag.word_piece_limit": "981",
            "bank_filings_rag.median_word_pieces": "256",
        },
        synthetic=set(),
        flags={},
        sources={},
    )
    with pytest.raises(build_module.BuildError, match="below the median"):
        build_module.word_pieces_chart(wrong)


def test_mean_pd_chart_scales_the_bars_to_the_raw_pd() -> None:
    svg, md = build_module.mean_pd_chart(_numbers())
    # 180 * 8.0 / 39.5 and 180 * 8.07 / 39.5, rounded to one decimal.
    assert 'width="180.0"' in svg
    assert 'width="36.5"' in svg
    assert 'width="36.8"' in svg
    assert md.endswith("Raw model: 39.5%; After calibration: 8.0%; Real default rate: 8.07%.")


def _line_lengths(svg: str) -> list[float]:
    lines = re.findall(r'<line class="chart-line" x1="([\d.]+)" y1="[\d.]+" x2="([\d.]+)"', svg)
    return [float(b) - float(a) for a, b in lines]


def test_gender_chart_shows_the_gap_shrink_but_not_close() -> None:
    svg, md = build_module.gender_approval_chart(_numbers())
    with_gender, without_gender = _line_lengths(svg)
    assert 0 < without_gender < with_gender
    for text in ("Women 84.5%", "Men 72.3%", "Women 83.2%", "Men 75.2%"):
        assert f">{text}</text>" in svg
    assert "with gender, women 84.5% and men 72.3%" in md


def _credit_numbers(**values: str) -> build_module.Numbers:
    return build_module.Numbers(
        values={f"credit_risk_scorecard.{k}": v for k, v in values.items()},
        synthetic=set(),
        flags={},
        sources={},
    )


def test_credit_charts_need_their_numbers() -> None:
    empty = _credit_numbers()
    with pytest.raises(build_module.BuildError, match="mean PD chart needs"):
        build_module.mean_pd_chart(empty)
    with pytest.raises(build_module.BuildError, match="approval chart needs these"):
        build_module.gender_approval_chart(empty)
    zero = _credit_numbers(
        raw_mean_pd="0.0%", isotonic_mean_pd="8.0%", observed_default_rate="8.07%"
    )
    with pytest.raises(build_module.BuildError, match="above zero"):
        build_module.mean_pd_chart(zero)
    same = _credit_numbers(
        approval_women_with_gender_pct="80.0%",
        approval_men_with_gender_pct="80.0%",
        approval_women_without_gender_pct="80.0%",
        approval_men_without_gender_pct="80.0%",
    )
    with pytest.raises(build_module.BuildError, match="rates that differ"):
        build_module.gender_approval_chart(same)
