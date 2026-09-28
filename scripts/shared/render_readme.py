"""Fill README.md from README.template.md with numbers other repos already claim.

Usage:
    python scripts/render_readme.py [--offline] [--check]

Per docs/decisions/0001-how-the-readme-is-built-and-synced.md and
docs/decisions/0002-where-each-number-comes-from.md:

- `projects.toml` lists, for each source repo, which numbers the template may show
  and which CLAIMS.md row in that repo covers each one.
- For each repo used, this script finds the commit at the tip of its `main` branch
  with `git ls-remote` (no key, no API call), then reads its metrics file and its
  CLAIMS.md from that exact commit on raw.githubusercontent.com, so the two files
  can never disagree because one was read later than the other.
- A number is only shown if: its CLAIMS.md row exists, that row's Source cell names
  the same file (and any `#key` is a prefix of the number's path), and the formatted
  value equals a number already written in that row's Value cell. If any of this
  fails, the script writes nothing and exits with an error.
- It fails, too, if the template uses a placeholder no entry in `projects.toml`
  defines, or if `projects.toml` defines a number the template never shows.
- A `{{ project_table }}` line in the template becomes one table row per
  `[[project]]` entry, in config order (ADR 0003). Each row's words come from that
  entry's `what`, `finding` and `headline`; `headline` may hold number placeholders.
  An entry with `metrics = false` has no metrics file, may not define numbers, and
  its row shows no number (ADR 0002).
- A number marked `synthetic = true` may only appear on a line that also says
  "synthetic" (ADR 0002).
- `README.md` is written only if the rendered text differs from what's already
  there. `data/sources.json` is written with the commit used for every source repo,
  so any shown number can be traced by hand.

`--offline` reads `tests/fixtures/` (recorded in `tests/fixtures/SOURCES.md`)
instead of the network. Tests always use it, and it needs no network.
`--check` renders without writing anything, and exits 1 if `README.md` or
`data/sources.json` would change.

Only the Python standard library is used.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
import urllib.request
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
GITHUB_USER = "Iliya-Valizadeh"
PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}")
# A "-" counts as a minus sign only when no digit comes right before it, so a range
# written "0.762-0.775" reads as 0.762 and 0.775, the way tools/claims_check.py reads
# it, while "; -0.20" still reads as a negative number.
VALUE_NUMBER_RE = re.compile(r"(?:(?<![\d.])-)?\d+(?:\.\d+)?%?")
TABLE_TOKEN = "{{ project_table }}"
NO_NUMBER_TEXT = "None. It holds rules and templates, not a model"
SOURCES_LINE_RE = re.compile(r"^\s*-\s*`([\w.-]+)`\s+at\s+`([0-9a-f]{7,40})`")


class RenderError(Exception):
    """Raised when a number, or the template, cannot be rendered safely."""


@dataclass(frozen=True)
class NumberConfig:
    id: str
    path: str
    row: str
    decimals: int
    percent: bool
    thousands: bool
    synthetic: bool = False


@dataclass(frozen=True)
class ProjectConfig:
    repo: str
    metrics_file: str
    numbers: tuple[NumberConfig, ...]
    what: str = ""
    finding: str = ""
    headline: str = ""


@dataclass(frozen=True)
class ClaimRow:
    claim: str
    value: str
    source: str


def load_config(path: Path) -> list[ProjectConfig]:
    """Read projects.toml into a list of ProjectConfig."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    projects = []
    for p in data.get("project", []):
        numbers = tuple(
            NumberConfig(
                id=n["id"],
                path=n["path"],
                row=n["row"],
                decimals=int(n.get("decimals", 0)),
                percent=bool(n.get("percent", False)),
                thousands=bool(n.get("thousands", False)),
                synthetic=bool(n.get("synthetic", False)),
            )
            for n in p.get("number", [])
        )
        has_metrics = bool(p.get("metrics", True))
        if not has_metrics and (numbers or p.get("metrics_file") or p.get("headline")):
            raise RenderError(
                f"{p['repo']}: metrics = false, so it may not have a metrics_file, "
                "a headline or any numbers (ADR 0002)"
            )
        if has_metrics and "metrics_file" not in p:
            raise RenderError(f"{p['repo']}: no metrics_file (or set metrics = false)")
        projects.append(
            ProjectConfig(
                repo=p["repo"],
                metrics_file=p.get("metrics_file", ""),
                numbers=numbers,
                what=p.get("what", ""),
                finding=p.get("finding", ""),
                headline=p.get("headline", ""),
            )
        )
    return projects


def table_cell(text: str) -> str:
    """One Markdown table cell: no pipes and no line breaks inside it."""
    if "|" in text:
        raise RenderError(f"table text may not contain '|': {text!r}")
    return " ".join(text.split())


def project_table(config: list[ProjectConfig]) -> str:
    """The project table, one row per [[project]] entry in config order (ADR 0003)."""
    lines = [
        "| Project | What it is | Most interesting finding | Headline number |",
        "|---|---|---|---|",
    ]
    for p in config:
        link = f"[{p.repo}](https://github.com/{GITHUB_USER}/{p.repo})"
        headline = p.headline if p.numbers else NO_NUMBER_TEXT
        cells = [link, table_cell(p.what), table_cell(p.finding), table_cell(headline)]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def split_row(line: str) -> list[str]:
    """Split one Markdown table row into its cells."""
    cells = re.split(r"(?<!\\)\|", line.strip().strip("|"))
    return [c.strip().replace("\\|", "|") for c in cells]


def parse_claims_table(text: str) -> list[ClaimRow]:
    """Read every claims table in a CLAIMS.md, keeping the Claim, Value and Source cells."""
    lines = text.splitlines()
    rows: list[ClaimRow] = []
    i = 0
    while i < len(lines):
        is_table = (
            lines[i].lstrip().startswith("|")
            and i + 1 < len(lines)
            and re.match(r"^\s*\|?\s*:?-{3,}", lines[i + 1])
        )
        if not is_table:
            i += 1
            continue
        header = [h.lower().strip("`* ") for h in split_row(lines[i])]
        i += 2
        needed = {"claim", "value", "source"}
        if not needed <= set(header):
            continue
        ci, vi, si = (header.index(k) for k in ("claim", "value", "source"))
        while i < len(lines) and lines[i].lstrip().startswith("|"):
            cells = split_row(lines[i])
            cells += [""] * (len(header) - len(cells))
            rows.append(ClaimRow(claim=cells[ci], value=cells[vi], source=cells[si].strip("` ")))
            i += 1
    return rows


def json_value(data: Any, path: str) -> Decimal:
    """Read a dotted key out of parsed JSON, as a Decimal."""
    node = data
    for part in path.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            raise RenderError(f"path '{path}' not found in metrics file")
    if isinstance(node, bool) or not isinstance(node, int | float):
        raise RenderError(f"path '{path}' is not a number")
    return Decimal(repr(node))


def format_number(value: Decimal, config: NumberConfig) -> str:
    """Format a number the way ADR 0002's `format` rules say to."""
    shown = value * 100 if config.percent else value
    step = Decimal(1).scaleb(-config.decimals)
    rounded = shown.quantize(step, rounding=ROUND_HALF_UP)
    text = f"{rounded:.{config.decimals}f}" if config.decimals else str(int(rounded))
    if config.thousands:
        negative = text.startswith("-")
        digits = text[1:] if negative else text
        text = ("-" if negative else "") + f"{int(digits):,}"
    if config.percent:
        text += "%"
    return text


def source_matches(source_cell: str, metrics_file: str, path: str) -> bool:
    """True if a CLAIMS.md row's Source cell really covers this number's path."""
    file_part, _, key = source_cell.partition("#")
    if file_part.strip() != metrics_file:
        return False
    return not key or path.startswith(key)


def value_cell_matches(value_cell: str, formatted: str, config: NumberConfig) -> bool:
    """True if the formatted number is already one of the numbers in the Value cell."""
    target = Decimal(formatted.rstrip("%").replace(",", ""))
    for m in VALUE_NUMBER_RE.finditer(value_cell):
        text = m.group(0)
        is_percent = text.endswith("%")
        num = Decimal(text.rstrip("%"))
        candidates = {num}
        if is_percent:
            candidates.add(num / 100)
        if config.percent:
            candidates.add(num if is_percent else num * 100)
        if target in candidates:
            return True
    return False


class Fetcher:
    """Where the source files for one project come from."""

    def commit(self, repo: str) -> str:  # pragma: no cover - interface only
        raise NotImplementedError

    def read(self, repo: str, commit: str, file: str) -> str:  # pragma: no cover
        raise NotImplementedError


class OnlineFetcher(Fetcher):
    """Reads the real commit and files from GitHub. Per ADR 0002: no key, no API."""

    def commit(self, repo: str) -> str:
        url = f"https://github.com/{GITHUB_USER}/{repo}"
        result = subprocess.run(
            ["git", "ls-remote", url, "refs/heads/main"],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        line = result.stdout.strip()
        if not line:
            raise RenderError(f"{repo}: 'git ls-remote' found no main branch at {url}")
        return line.split()[0]

    def read(self, repo: str, commit: str, file: str) -> str:
        url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{repo}/{commit}/{file}"
        with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310
            text: str = response.read().decode("utf-8")
            return text


class OfflineFetcher(Fetcher):
    """Reads tests/fixtures/ instead of the network. Used by tests and --offline."""

    def __init__(self, fixtures_dir: Path) -> None:
        self.fixtures_dir = fixtures_dir
        self._commits = self._load_sources()

    def _load_sources(self) -> dict[str, str]:
        sources_path = self.fixtures_dir / "SOURCES.md"
        commits: dict[str, str] = {}
        for line in sources_path.read_text(encoding="utf-8").splitlines():
            match = SOURCES_LINE_RE.match(line)
            if match:
                commits[match.group(1)] = match.group(2)
        return commits

    def commit(self, repo: str) -> str:
        if repo not in self._commits:
            raise RenderError(f"{repo}: no commit recorded in tests/fixtures/SOURCES.md")
        return self._commits[repo]

    def read(self, repo: str, commit: str, file: str) -> str:
        path = self.fixtures_dir / repo / file.replace("/", "_")
        if not path.is_file():
            raise RenderError(f"{repo}: fixture not found: {path}")
        return path.read_text(encoding="utf-8")


def render(
    template_text: str, config: list[ProjectConfig], fetcher: Fetcher
) -> tuple[str, dict[str, str]]:
    """Fill the template. Returns the rendered text and the commit used per repo."""
    if TABLE_TOKEN in template_text:
        template_text = template_text.replace(TABLE_TOKEN, project_table(config))
    used_placeholders = set(PLACEHOLDER_RE.findall(template_text))
    all_numbers = {number.id: (project, number) for project in config for number in project.numbers}

    unknown = used_placeholders - set(all_numbers)
    if unknown:
        raise RenderError(
            f"README.template.md uses placeholder(s) not in projects.toml: {sorted(unknown)}"
        )
    unused = set(all_numbers) - used_placeholders
    if unused:
        raise RenderError(
            f"projects.toml defines number(s) README.template.md never shows: {sorted(unused)}"
        )

    values: dict[str, str] = {}
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
            values[number.id] = formatted

    synthetic_ids = {n.id for p in config for n in p.numbers if n.synthetic}
    for line in template_text.splitlines():
        ids = set(PLACEHOLDER_RE.findall(line))
        if ids & synthetic_ids and "synthetic" not in line.lower():
            raise RenderError(
                f"{sorted(ids & synthetic_ids)} measured on synthetic data, but the "
                f"line does not say 'synthetic': {line[:80]!r}"
            )

    rendered = PLACEHOLDER_RE.sub(lambda m: values[m.group(1)], template_text)
    return rendered, sources


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument(
        "--offline", action="store_true", help="read tests/fixtures/ instead of the network"
    )
    parser.add_argument(
        "--check", action="store_true", help="render without writing; exit 1 if it would change"
    )
    args = parser.parse_args(argv)

    template_text = (ROOT / "README.template.md").read_text(encoding="utf-8")
    fetcher: Fetcher = (
        OfflineFetcher(ROOT / "tests" / "fixtures") if args.offline else OnlineFetcher()
    )

    try:
        config = load_config(ROOT / "projects.toml")
        rendered, sources = render(template_text, config, fetcher)
    except RenderError as exc:
        print(f"render failed: {exc}", file=sys.stderr)
        return 1

    readme_path = ROOT / "README.md"
    current_readme = readme_path.read_text(encoding="utf-8") if readme_path.is_file() else None
    readme_changed = current_readme != rendered

    sources_path = ROOT / "data" / "sources.json"
    sources_text = json.dumps(sources, indent=2, sort_keys=True) + "\n"
    current_sources = sources_path.read_text(encoding="utf-8") if sources_path.is_file() else None
    sources_changed = current_sources != sources_text

    if args.check:
        if readme_changed or sources_changed:
            print(
                "would change: "
                + ", ".join(
                    p
                    for p, c in (
                        ("README.md", readme_changed),
                        ("data/sources.json", sources_changed),
                    )
                    if c
                )
            )
            return 1
        print("README.md and data/sources.json are already up to date")
        return 0

    if readme_changed:
        # newline="\n" so this write is bytes-for-bytes the same on every platform,
        # rather than relying on .gitattributes to fix it up after the fact. The
        # Hack the North guard depends on that (ADR 0004).
        readme_path.write_text(rendered, encoding="utf-8", newline="\n")
        print("wrote README.md")
    else:
        print("README.md already up to date, not written")

    if sources_changed:
        sources_path.parent.mkdir(parents=True, exist_ok=True)
        sources_path.write_text(sources_text, encoding="utf-8", newline="\n")
        print("wrote data/sources.json")
    else:
        print("data/sources.json already up to date, not written")

    return 0


if __name__ == "__main__":
    sys.exit(main())
