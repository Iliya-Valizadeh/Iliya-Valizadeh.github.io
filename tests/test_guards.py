"""Guards that must hold on every build, per docs/decisions/0004-checks.md.

- Nothing about Hack the North is added anywhere in this repo's build inputs or
  output. The site has none today, so any match means something was added.
- The word "fraud" never appears in the built site.
- No unfilled `{{` placeholder reaches `_site/`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import build as build_module

ROOT = Path(__file__).resolve().parent.parent
HACK_THE_NORTH_RE = re.compile(r"hack\W*the\W*north", re.IGNORECASE)

# Per ADR 0004. Decision records and this test file are not scanned, because they
# name the rule.
SCANNED_DIRS = [
    "content",
    "notes",
    "templates",
    "partials",
    "static",
    "docs/archive",
]
SCANNED_FILES = ["projects.toml"]


def _all_text_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(p for p in path.rglob("*") if p.is_file())
        elif path.is_file():
            files.append(path)
    return files


@pytest.fixture(scope="module")
def built_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    site_dir = tmp_path_factory.mktemp("site") / "_site"
    build_md_dir = tmp_path_factory.mktemp("build_md") / "_build" / "md"
    orig_site, orig_build_md = build_module.SITE_DIR, build_module.BUILD_MD_DIR
    build_module.SITE_DIR = site_dir
    build_module.BUILD_MD_DIR = build_md_dir
    try:
        build_module.build(offline=True)
    finally:
        build_module.SITE_DIR, build_module.BUILD_MD_DIR = orig_site, orig_build_md
    return site_dir


def test_no_hack_the_north_in_source_inputs() -> None:
    paths = [ROOT / d for d in SCANNED_DIRS] + [ROOT / f for f in SCANNED_FILES]
    for path in _all_text_files(paths):
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert not HACK_THE_NORTH_RE.search(text), f"{path} mentions Hack the North"


def test_no_hack_the_north_in_built_site(built_site: Path) -> None:
    for path in _all_text_files([built_site]):
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert not HACK_THE_NORTH_RE.search(text), f"{path} mentions Hack the North"


def test_no_fraud_word_in_built_site(built_site: Path) -> None:
    for path in _all_text_files([built_site]):
        if path.suffix.lower() not in {".html", ".css", ".js", ".json"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert "fraud" not in text.lower(), f"{path} contains the word 'fraud'"


def test_no_unfilled_placeholder_in_built_site(built_site: Path) -> None:
    for path in _all_text_files([built_site]):
        if path.suffix.lower() not in {".html"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert "{{" not in text, f"{path} has an unfilled placeholder"
