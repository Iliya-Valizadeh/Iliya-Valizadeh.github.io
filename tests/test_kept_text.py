"""The About section and the two demos must read the same as the old page.

Per docs/decisions/0006-text-kept-word-for-word-and-the-old-page.md: these parts are
Iliya's own words or his own work, kept word for word from
`docs/archive/index-2026-09.html`. This test strips tags, joins white space, and
compares the words, so markup changes for accessibility later would still pass as
long as the words themselves do not change. It also checks the moved script (now
`static/main.js`) matches the archived page's inline script byte for byte, after
turning CRLF into LF.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / "docs" / "archive" / "index-2026-09.html"
# Which built page each kept section lives on (ADR 0007).
KEPT_SECTIONS = {"about": "about.html", "risk": "index.html", "fit": "index.html"}


def section_words(html: str, section_id: str) -> str:
    match = re.search(rf'<section id="{section_id}">.*?</section>', html, re.S)
    assert match, f'no <section id="{section_id}"> found'
    text = re.sub(r"<[^>]+>", " ", match.group(0))
    return " ".join(text.split())


@pytest.fixture(scope="module")
def built_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    site_dir = ROOT / "_site"
    subprocess.run(
        [sys.executable, str(ROOT / "build.py"), "--offline"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return site_dir


@pytest.mark.parametrize(("section_id", "page"), sorted(KEPT_SECTIONS.items()))
def test_kept_section_reads_the_same_as_the_archive(
    built_site: Path, section_id: str, page: str
) -> None:
    archive_html = ARCHIVE.read_text(encoding="utf-8")
    built_html = (built_site / page).read_text(encoding="utf-8")
    assert section_words(built_html, section_id) == section_words(archive_html, section_id)


def test_moved_script_matches_the_archived_inline_script() -> None:
    archive_text = ARCHIVE.read_text(encoding="utf-8").replace("\r\n", "\n")
    match = re.search(r"<script>\n(.*)\n</script>", archive_text, re.S)
    assert match, "no inline <script> block found in the archived page"
    inline_script = match.group(1)
    moved_script = (ROOT / "static" / "main.js").read_text(encoding="utf-8")
    assert moved_script.rstrip("\n") == inline_script.rstrip("\n")
