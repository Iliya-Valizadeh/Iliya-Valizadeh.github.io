"""Tests for build.py: the home page assembles correctly, and the site is inert.

Per docs/decisions/0001 and 0004: no placeholder is left unfilled, the verification
file is copied byte for byte, and static/ is copied unchanged.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import build as build_module

ROOT = Path(__file__).resolve().parent.parent
VERIFICATION_HASH = "6aeaef4372c8319c6cb681646cad909eac9f38c37143c932edf74a4688cd57ef"


@pytest.fixture()
def built_site(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    site_dir = tmp_path / "_site"
    build_md_dir = tmp_path / "_build" / "md"
    monkeypatch.setattr(build_module, "SITE_DIR", site_dir)
    monkeypatch.setattr(build_module, "BUILD_MD_DIR", build_md_dir)
    build_module.build(offline=True)
    return site_dir


def test_home_page_has_no_unfilled_placeholder(built_site: Path) -> None:
    html = (built_site / "index.html").read_text(encoding="utf-8")
    assert "{{" not in html
    assert "}}" not in html


@pytest.mark.parametrize(
    ("page", "sections"),
    [
        ("index.html", ("risk", "fit", "work", "contact")),
        ("about.html", ("about", "now", "contact")),
    ],
)
def test_each_page_has_its_sections(built_site: Path, page: str, sections: tuple[str, ...]) -> None:
    html = (built_site / page).read_text(encoding="utf-8")
    for section_id in sections:
        assert html.count(f'<section id="{section_id}">') == 1
    assert "{{" not in html


def test_verification_file_is_copied_byte_for_byte(built_site: Path) -> None:
    data = (built_site / "googleb968c9a0c91c49c6.html").read_bytes()
    assert hashlib.sha256(data).hexdigest() == VERIFICATION_HASH
    # And matches the copy still at the repo root, per ADR 0006.
    root_data = (ROOT / "googleb968c9a0c91c49c6.html").read_bytes()
    assert data == root_data


def test_static_is_copied(built_site: Path) -> None:
    assert (built_site / "static" / "style.css").is_file()
    assert (built_site / "static" / "main.js").is_file()
    built_css = (built_site / "static" / "style.css").read_text(encoding="utf-8")
    source_css = (ROOT / "static" / "style.css").read_text(encoding="utf-8")
    assert built_css == source_css


def test_sources_json_records_a_commit_per_metrics_bearing_repo(built_site: Path) -> None:
    sources = json.loads((built_site / "sources.json").read_text(encoding="utf-8"))
    assert sources == {
        "credit-risk-scorecard": "35a17fd2454ced157bdab00dc6b0301e67893240",
        "bank-filings-rag": "45246f8af21e907912d5611ccadb9158315255a3",
        "second-look": "0da821d9af2c15782d4e60abfd54572c1d34d0be",
    }


def test_unknown_placeholder_fails_the_build() -> None:
    with pytest.raises(build_module.BuildError):
        build_module.render_template("{{ nope }}", {})


def test_known_placeholder_is_filled() -> None:
    out = build_module.render_template("<p>{{ x }}</p>", {"x": "<b>hi</b>"})
    assert out == "<p><b>hi</b></p>"
