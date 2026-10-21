"""Checks that scripts/shared/ still matches the copy named in its SOURCE.json.

Per docs/decisions/0002-where-each-number-comes-from.md's "Shared code" rule, the
fetching, row matching and number formatting live once in the profile repo and are
copied here byte for byte. This test fails if the copy no longer matches the SHA-256
recorded when it was vendored.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "scripts" / "shared"
SOURCE = json.loads((SHARED / "SOURCE.json").read_text(encoding="utf-8"))


def test_source_json_names_the_profile_repo() -> None:
    assert SOURCE["source_repo"].endswith("/Iliya-Valizadeh")


def test_every_vendored_file_matches_its_recorded_hash() -> None:
    for name, expected_hash in SOURCE["files"].items():
        data = (SHARED / name).read_bytes()
        actual_hash = hashlib.sha256(data).hexdigest()
        assert actual_hash == expected_hash, (
            f"scripts/shared/{name} has changed since it was vendored: "
            f"got {actual_hash}, expected {expected_hash}. "
            "Do not edit this copy; see docs/decisions/0002.md."
        )
