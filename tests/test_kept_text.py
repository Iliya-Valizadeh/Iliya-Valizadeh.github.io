"""The About paragraphs must read the same as the old page.

Per docs/decisions/0006-text-kept-word-for-word-and-the-old-page.md and
docs/decisions/0015-one-plain-column.md: the four About paragraphs are my own words,
kept word for word from `docs/archive/index-2026-09.html`. The two demos and the
section labels around the paragraphs were removed in ADR 0015; the archive still holds
them. This test takes the text of every `<p>` in the About section, strips tags and
joins white space, and compares the words. Markup changes still pass as long as the
words do not change.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / "docs" / "archive" / "index-2026-09.html"


def about_paragraphs(html: str) -> list[str]:
    match = re.search(r'<section id="about">.*?</section>', html, re.S)
    assert match, 'no <section id="about"> found'
    paragraphs = re.findall(r"<p\b[^>]*>(.*?)</p>", match.group(0), re.S)
    return [" ".join(re.sub(r"<[^>]+>", " ", p).split()) for p in paragraphs]


@pytest.fixture(scope="module")
def built_site() -> Path:
    subprocess.run(
        [sys.executable, str(ROOT / "build.py"), "--offline"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return ROOT / "_site"


def test_about_paragraphs_read_the_same_as_the_archive(built_site: Path) -> None:
    archived = about_paragraphs(ARCHIVE.read_text(encoding="utf-8"))
    assert len(archived) == 4
    built = about_paragraphs((built_site / "about.html").read_text(encoding="utf-8"))
    # The built section has the "now" paragraph first; the kept four follow in order.
    start = built.index(archived[0])
    assert built[start : start + 4] == archived
