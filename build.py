"""Build the site: fill templates/home.html with partials, write `_site/`.

Usage: python build.py [--offline]

Per docs/decisions/0001-a-small-python-build-deployed-by-actions.md:

- `templates/*.html` are page shells with `{{ name }}` placeholders. They hold markup
  and short labels only, never paragraphs of prose.
- `partials/*.html` hold HTML kept word for word from the old page (ADR 0006): the
  nav, hero, ticker, the two demos, the work list, the about section and the contact
  section. Each fills exactly one placeholder, as trusted HTML, unescaped.
- `content/` (Markdown pages) and `notes/` (Markdown notes) are not built into any
  page yet; this task only reproduces the page that already existed. They exist as
  empty folders so later tasks have somewhere to write.
- `static/` (the shared stylesheet and script) is copied into `_site/static/`
  unchanged.
- `googleb968c9a0c91c49c6.html` is copied byte for byte to the root of `_site/`.
- `projects.toml` lists the numbers each source repo's `reports/metrics.json` may
  show, per docs/decisions/0002-where-each-number-comes-from.md. No page uses a
  number placeholder yet (that starts in the Home and project-page tasks), but the
  fetch-and-match pipeline runs on every build and writes `_site/sources.json`, so
  the machinery is exercised and tested before any page depends on it.
- Output goes to `_site/` (what is deployed) and `_build/md/` (every page and note as
  filled-in Markdown, for the writing and number checks; empty today, since no
  Markdown content exists yet). Both are gitignored.

`--offline` reads `tests/fixtures/` instead of the network for the numbers step, the
same fixtures the tests use. It needs no network.

Only the Python standard library is used.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

from scripts.shared.render_readme import (  # noqa: E402
    Fetcher,
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

SITE_DIR = ROOT / "_site"
BUILD_MD_DIR = ROOT / "_build" / "md"
TEMPLATES_DIR = ROOT / "templates"
PARTIALS_DIR = ROOT / "partials"
STATIC_DIR = ROOT / "static"
VERIFICATION_FILE = "googleb968c9a0c91c49c6.html"

PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")

# Every partial that fills the home page, in the order it appears on the page.
HOME_PARTIALS = ["nav", "hero", "ticker", "risk", "fit", "work", "about", "contact"]


class BuildError(Exception):
    """Raised when the site cannot be built safely."""


def load_partial(name: str) -> str:
    path = PARTIALS_DIR / f"{name}.html"
    if not path.is_file():
        raise BuildError(f"missing partial: {path}")
    return path.read_text(encoding="utf-8")


def render_template(template_text: str, context: dict[str, str]) -> str:
    """Fill `{{ name }}` placeholders. Every value is trusted HTML, never escaped.

    Fails on a placeholder the context does not cover. Does not require every
    context entry to be used, unlike the profile's number renderer, because a page
    shell may reuse the same context across pages later.
    """

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in context:
            raise BuildError(f"template uses unknown placeholder: {{{{ {name} }}}}")
        return context[name]

    return PLACEHOLDER_RE.sub(replace, template_text)


def build_home_page() -> str:
    template_text = (TEMPLATES_DIR / "home.html").read_text(encoding="utf-8")
    context = {name: load_partial(name) for name in HOME_PARTIALS}
    rendered = render_template(template_text, context)
    if "{{" in rendered:
        raise BuildError("a placeholder was left unfilled in the built home page")
    return rendered


def copy_static(site_dir: Path) -> None:
    dest = site_dir / "static"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(STATIC_DIR, dest)


def copy_verification_file(site_dir: Path) -> None:
    src = ROOT / VERIFICATION_FILE
    if not src.is_file():
        raise BuildError(f"missing verification file: {src}")
    shutil.copyfile(src, site_dir / VERIFICATION_FILE)


def fetch_sources(config: list[ProjectConfig], fetcher: Fetcher) -> dict[str, str]:
    """Fetch, match and format every configured number. Returns the commit used per
    metrics-bearing repo, for `_site/sources.json` (ADR 0002).

    Every number is checked against its own repo's CLAIMS.md before the build
    trusts it, exactly like the profile's renderer does. A failure here stops the
    whole build: nothing is deployed, and the last good site stays up.
    """
    sources: dict[str, str] = {}
    for project in config:
        if not project.numbers:
            continue
        commit = fetcher.commit(project.repo)
        sources[project.repo] = commit
        metrics = json.loads(fetcher.read(project.repo, commit, project.metrics_file))
        claim_rows = parse_claims_table(fetcher.read(project.repo, commit, "CLAIMS.md"))
        for number in project.numbers:
            row = next((r for r in claim_rows if r.claim.strip() == number.row.strip()), None)
            if row is None:
                raise RenderError(
                    f"{project.repo}: CLAIMS.md has no row '{number.row}' for {number.id}"
                )
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
    return sources


def build(offline: bool) -> None:
    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    SITE_DIR.mkdir(parents=True)
    BUILD_MD_DIR.mkdir(parents=True, exist_ok=True)

    (SITE_DIR / "index.html").write_text(build_home_page(), encoding="utf-8", newline="\n")
    copy_static(SITE_DIR)
    copy_verification_file(SITE_DIR)

    config = load_config(ROOT / "projects.toml")
    fetcher: Fetcher = OfflineFetcher(ROOT / "tests" / "fixtures") if offline else OnlineFetcher()
    sources = fetch_sources(config, fetcher)
    sources_text = json.dumps(sources, indent=2, sort_keys=True) + "\n"
    (SITE_DIR / "sources.json").write_text(sources_text, encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument(
        "--offline", action="store_true", help="read tests/fixtures/ instead of the network"
    )
    args = parser.parse_args(argv)
    try:
        build(args.offline)
    except (BuildError, RenderError) as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        return 1
    print("wrote _site/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
