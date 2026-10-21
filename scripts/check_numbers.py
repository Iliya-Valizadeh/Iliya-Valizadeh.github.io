"""Check that every number in `_build/md/` came from a number placeholder.

Usage: python scripts/check_numbers.py [--offline] [PATH ...]

Per docs/decisions/0002-where-each-number-comes-from.md: no page may contain a
number that did not come from a `{{ placeholder }}` build.py filled in. This script
does not know which literal spans in a built page came from a placeholder, so it
takes the safer, checkable version of that rule: it computes the full set of values
that `projects.toml`'s number pipeline would legitimately produce right now (by
running build.py's own `fetch_numbers()`, so each one is already checked against its
own repo's CLAIMS.md), then fails if any "claim-like" number appears in the built
Markdown that is not one of those values.

It reuses the same number-finding rules as `tools/claims_check.py` (years, dates and
whole numbers up to ten are skipped), so a typed number such as an unlisted count or a
raw ROC-AUC fails the same way an unclaimed number would fail `claims_check.py`.

`--offline` reads `tests/fixtures/` instead of the network, the same as `build.py`.
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

from build import BuildError, SiteProject, fetch_numbers, load_site_projects  # noqa: E402
from scripts.shared.render_readme import (  # noqa: E402
    Fetcher,
    NumberConfig,
    OfflineFetcher,
    OnlineFetcher,
    ProjectConfig,
    RenderError,
    load_config,
)

CONFIG_PATH = ROOT / "projects.toml"


def allowed_values(
    config: list[ProjectConfig], fetcher: Fetcher, site: list[SiteProject] | None = None
) -> set[Decimal]:
    """Every value the number pipeline would produce right now, in every form.

    It runs build.py's own `fetch_numbers` (ADR 0008), so it raises under exactly the
    same conditions: a missing CLAIMS.md row, a Source cell that does not cover the
    path, or a value that CLAIMS.md's Value cell does not already contain.
    """
    if site is None:
        site = load_site_projects(CONFIG_PATH)
    allowed: set[Decimal] = set()
    for formatted in fetch_numbers(config, site, fetcher).values.values():
        allowed |= _forms(formatted)
    return allowed


def _forms(formatted: str, config: NumberConfig | None = None) -> set[Decimal]:
    """Every Decimal value a formatted number could be read back as."""
    value = Decimal(formatted.rstrip("%").replace(",", ""))
    out = {value}
    if formatted.endswith("%") or (config is not None and config.percent):
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

    config = load_config(CONFIG_PATH)
    fetcher: Fetcher = (
        OfflineFetcher(ROOT / "tests" / "fixtures") if args.offline else OnlineFetcher()
    )
    try:
        allowed = allowed_values(config, fetcher)
    except (RenderError, BuildError) as exc:
        print(f"numbers check failed: {exc}", file=sys.stderr)
        return 1

    errors = find_bad_numbers(args.paths, allowed)
    for e in errors:
        print(e)
    print(f"numbers check: {len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
