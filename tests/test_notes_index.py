"""Tests for the Notes index, the RSS feed, notes.json and the Open Graph tags.

All offline. The three real notes are drafts, so the built index must say no notes are
published, the feed must have no items and notes.json must be an empty list (ADR 0005).
Small fixture notes cover the published case.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import build as build_module
from tests.test_notes import MARKER, NOTE_BODY, _build_into

ROOT = Path(__file__).resolve().parent.parent
REAL_NOTES = sorted((ROOT / "notes").glob("*.md"))
SITE = "https://iliya-valizadeh.github.io"
RSS_TYPE = "application/rss+xml"


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _build_into(tmp_path_factory.mktemp("index"))[0]


@pytest.fixture(scope="module")
def published(tmp_path_factory: pytest.TempPathFactory) -> Path:
    base = tmp_path_factory.mktemp("published")
    notes = base / "notes"
    notes.mkdir()
    older = NOTE_BODY.replace("A made-up note", "Older & plainer <note>")
    newer = NOTE_BODY.replace("A made-up note", "The newer note")
    (notes / "older.md").write_text(f"Published: 2026-10-01\n{older}", encoding="utf-8")
    (notes / "newer.md").write_text(f"Published: 2026-11-15\n{newer}", encoding="utf-8")
    (notes / "hidden.md").write_text(f"{MARKER}\n{NOTE_BODY}", encoding="utf-8")
    return _build_into(base, notes)[0]


# ------------------------------------------------------------ the real drafts stay out


def test_index_says_no_notes_are_published_yet(built: Path) -> None:
    index = (built / "notes" / "index.html").read_text(encoding="utf-8")
    assert "<p>No notes are published yet.</p>" in index
    assert "notelist" not in index


def test_feed_is_valid_and_has_no_items(built: Path) -> None:
    root = ET.fromstring((built / "feed.xml").read_text(encoding="utf-8"))
    assert root.tag == "rss"
    assert root.findall("./channel/item") == []
    assert root.findtext("./channel/title")


def test_notes_json_is_an_empty_list(built: Path) -> None:
    assert json.loads((built / "notes.json").read_text(encoding="utf-8")) == []


@pytest.mark.parametrize("note", REAL_NOTES, ids=lambda p: p.stem)
def test_real_drafts_are_in_no_built_file(built: Path, note: Path) -> None:
    assert MARKER not in note.read_text(encoding="utf-8").split("\n", 1)[1]
    title = re.search(r"^title: (.+)$", note.read_text(encoding="utf-8"), re.M)
    assert title is not None
    for path in sorted(built.rglob("*")):
        if path.is_file():
            data = path.read_bytes()
            assert note.stem.encode() not in data, path
            assert title.group(1).encode() not in data, path
            assert MARKER.encode() not in data, path


# ------------------------------------------------------------ published notes


def test_published_notes_are_listed_newest_first_and_the_draft_is_not(published: Path) -> None:
    index = (published / "notes" / "index.html").read_text(encoding="utf-8")
    assert "No notes are published yet" not in index
    assert index.index('href="newer.html"') < index.index('href="older.html"')
    assert "hidden" not in index
    assert "Older &amp; plainer &lt;note&gt;" in index
    assert "2026-11-15" in index


def test_feed_lists_published_notes_only(published: Path) -> None:
    root = ET.fromstring((published / "feed.xml").read_text(encoding="utf-8"))
    items = root.findall("./channel/item")
    assert [i.findtext("link") for i in items] == [
        f"{SITE}/notes/newer.html",
        f"{SITE}/notes/older.html",
    ]
    assert items[0].findtext("pubDate") == "Sun, 15 Nov 2026 00:00:00 GMT"
    assert items[1].findtext("title") == "Older & plainer <note>"
    assert items[0].findtext("guid") == f"{SITE}/notes/newer.html"
    assert "hidden" not in (published / "feed.xml").read_text(encoding="utf-8")


def test_notes_json_lists_published_notes_only(published: Path) -> None:
    rows = json.loads((published / "notes.json").read_text(encoding="utf-8"))
    assert [r["slug"] for r in rows] == ["newer", "older"]
    assert rows[0] == {
        "slug": "newer",
        "title": "The newer note",
        "description": "Only here for a test.",
        "published": "2026-11-15",
        "url": f"{SITE}/notes/newer.html",
    }


def test_a_published_note_page_is_an_article(published: Path) -> None:
    page = (published / "notes" / "newer.html").read_text(encoding="utf-8")
    assert '<meta property="og:type" content="article">' in page
    assert f'<meta property="og:url" content="{SITE}/notes/newer.html">' in page
    assert not (published / "notes" / "hidden.html").exists()


# ------------------------------------------------------------ Open Graph and the feed link


def test_every_built_page_has_open_graph_and_twitter_tags(built: Path) -> None:
    pages = sorted(built.rglob("*.html"))
    pages = [p for p in pages if p.name != build_module.VERIFICATION_FILE]
    assert len(pages) == 6
    for page in pages:
        text = page.read_text(encoding="utf-8")
        rel = page.relative_to(built).as_posix()
        for tag in ("og:title", "og:description", "og:type", "og:url", "og:site_name"):
            assert f'<meta property="{tag}"' in text, (rel, tag)
        for tag in ("twitter:card", "twitter:title", "twitter:description"):
            assert f'<meta name="{tag}"' in text, (rel, tag)
        assert f'<link rel="alternate" type="{RSS_TYPE}"' in text, rel
        url = re.search(r'<meta property="og:url" content="([^"]+)"', text)
        assert url is not None
        assert url.group(1).startswith(f"{SITE}/"), rel
        assert url.group(1).removeprefix(f"{SITE}/") in (
            "",
            rel.removesuffix("index.html"),
        ), rel
        assert f'<link rel="canonical" href="{url.group(1)}">' in text


def test_page_url() -> None:
    assert build_module.page_url("index.html") == f"{SITE}/"
    assert build_module.page_url("notes/index.html") == f"{SITE}/notes/"
    assert build_module.page_url("about.html") == f"{SITE}/about.html"


def test_home_links_notes_only_once_one_is_published(built: Path, published: Path) -> None:
    # ADR 0015: with no published note, Home does not point at an empty Notes page.
    assert 'href="notes/index.html"' not in (built / "index.html").read_text(encoding="utf-8")
    assert 'href="notes/index.html">notes</a>' in (published / "index.html").read_text(
        encoding="utf-8"
    )
    note_index = (built / "notes" / "index.html").read_text(encoding="utf-8")
    assert 'href="../feed.xml">RSS feed</a>' in note_index
