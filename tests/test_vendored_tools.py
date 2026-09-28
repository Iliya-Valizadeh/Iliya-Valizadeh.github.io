"""Checks that tools/ still matches the copies named in tools/SOURCE.json.

Per docs/decisions/0004-checks.md, the files in tools/ are copied byte for byte from
ds-project-standard and must never be edited here. This test fails if a copy no
longer matches the SHA-256 recorded when it was vendored.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
SOURCE = json.loads((TOOLS / "SOURCE.json").read_text(encoding="utf-8"))


def test_source_json_names_the_vendored_commit() -> None:
    assert SOURCE["source_commit"] == "602ec779782c7466703a2093832e0e091c3316b8"


def test_every_vendored_file_matches_its_recorded_hash() -> None:
    for name, expected_hash in SOURCE["files"].items():
        data = (TOOLS / name).read_bytes()
        actual_hash = hashlib.sha256(data).hexdigest()
        assert actual_hash == expected_hash, (
            f"tools/{name} has changed since it was vendored: "
            f"got {actual_hash}, expected {expected_hash}. "
            "Do not edit vendored tools; see docs/decisions/0004.md."
        )


def test_readme_sections_is_not_vendored() -> None:
    # ADR 0004: this repo's README does not use the project README layout, so
    # readme_sections.py is deliberately left out of tools/.
    assert not (TOOLS / "readme_sections.py").exists()
    assert "readme_sections.py" not in SOURCE["files"]
