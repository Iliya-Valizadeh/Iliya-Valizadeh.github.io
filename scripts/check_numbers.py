"""Check that every number in `_build/md/` came from a number placeholder.

Usage: python scripts/check_numbers.py [--offline] [PATH ...]

Per docs/decisions/0002-where-each-number-comes-from.md: no page may contain a
number that did not come from a `{{ placeholder }}` build.py filled in. This script
does not know which literal spans in a built page came from a placeholder, so it
takes the safer, checkable version of that rule: it computes the full set of values
that `projects.toml`'s number pipeline would legitimately produce right now (each one
already checked against its own repo's CLAIMS.md, exactly like build.py's
`fetch_sources()` does), then fails if any "claim-like" number appears in the built
Markdown that is not one of those values.

It reuses the same number-finding rules as `tools/claims_check.py` (years, dates and
whole numbers up to ten are skipped), so a typed number such as a rows_used count or a
raw ROC-AUC fails the same way an unclaimed number would fail `claims_check.py`.

`--offline` reads `tests/fixtures/` instead of the network, the same as `build.py`.

Only the Python standard library is used.
"""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from _markdown import iter_markdown_files  # noqa: E402
from claims_check import prose_numbers  # noqa: E402

from scripts.shared.render_readme import (  # noqa: E402
    Fetcher,
    NumberConfig,
    OfflineFetcher,
    OnlineFetcher,
    ProjectConfig,
    RenderError,
    format_number,
    json_value,
    load_config,
    parse_claims_table,
    source_matches,
    value_cell_matches,
)


def allowed_values(config: list[ProjectConfig], fetcher: Fetcher) -> set[Decimal]:
    """Every value the number pipeline would produce right now, in every form.

    Raises RenderError under the same conditions build.py's own fetch would: a
    missing CLAIMS.md row, a Source cell that does not cover the path, or a formatted
    value that CLAIMS.md's Value cell does not already contain.
    """
    allowed: set[Decimal] = set()
    for project in config:
        if not project.numbers:
            continue
        commit = fetcher.commit(project.repo)
        metrics = _load_json(fetcher.read(project.repo, commit, project.metrics_file))
        claim_rows = parse_claims_table(fetcher.read(project.repo, commit, "CLAIMS.md"))
        for number in project.numbers:
            row = next((r for r in claim_rows if r.claim.strip() == number.row.strip()), None)
            if row is None:
                raise RenderError(f"{project.repo}: CLAIMS.md has no row '{number.row}'")
            if not source_matches(row.source, project.metrics_file, number.path):
                raise RenderError(
                    f"{project.repo}: CLAIMS.md row '{number.row}' Source "
                    f"'{row.source}' does not cover {number.path}"
                )
            formatted = format_number(json_value(metrics, number.path), number)
            if not value_cell_matches(row.value, formatted, number):
                raise RenderError(
                    f"{project.repo}: {number.id} = {formatted} is not in CLAIMS.md "
                    f"row '{number.row}' Value cell '{row.value}'"
                )
            allowed |= _forms(formatted, number)
    return allowed


def _load_json(text: str) -> object:
    import json

    return json.loads(text)


def _forms(formatted: str, config: NumberConfig) -> set[Decimal]:
    """Every Decimal value a formatted number could be read back as."""
    value = Decimal(formatted.rstrip("%").replace(",", ""))
    out = {value}
    if config.percent:
        out.add(value / 100)
    return out


def find_bad_numbers(paths: list[str], allowed: set[Decimal]) -> list[str]:
    """Claim-like numbers in the built Markdown that are not in `allowed`."""
    errors = []
    for path in iter_markdown_files(paths):
        text = path.read_text(encoding="utf-8")
        for line_no, num in prose_numbers(text):
            if not num.forms() & allowed:
                errors.append(
                    f"{path}:{line_no}: {num.text} did not come from a number placeholder"
                )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument("paths", nargs="*", default=["_build/md"])
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)

    config = load_config(ROOT / "projects.toml")
    fetcher: Fetcher = (
        OfflineFetcher(ROOT / "tests" / "fixtures") if args.offline else OnlineFetcher()
    )
    try:
        allowed = allowed_values(config, fetcher)
    except RenderError as exc:
        print(f"numbers check failed: {exc}", file=sys.stderr)
        return 1

    errors = find_bad_numbers(args.paths, allowed)
    for e in errors:
        print(e)
    print(f"numbers check: {len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
