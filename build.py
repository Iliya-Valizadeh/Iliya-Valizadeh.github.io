"""Build the site: Home, About and one page per project, from templates and content.

Usage: python build.py [--offline]

Per docs/decisions/0001-a-small-python-build-deployed-by-actions.md,
docs/decisions/0007-home-and-about-pages.md and docs/decisions/0008-project-pages.md:

- `templates/page.html` is the shell every page shares. `partials/*.html` are the
  blocks a page is made of. Both hold markup and short labels only. The About section
  and the two demos are kept word for word from the old page (ADR 0006).
- Prose lives in `content/*.md` (one file per page, split into named slots by
  `<!-- slot: name -->` lines) and in the card fields of `projects.toml`. It is
  Markdown, turned into HTML with markdown-it-py.
- Numbers are never typed. A `{{ repo.name }}` placeholder in prose is filled from
  that repo's `reports/metrics.json`, and only after the value is found in the repo's
  own `CLAIMS.md` (ADR 0002). A sentence that uses a number measured on synthetic
  data must say "synthetic". A `[[project.flag]]` turns a true/false value in
  `metrics.json` into one of two sentences.
- The Home project list is a loop over `projects.toml`: every `work` entry, then
  every `tool` entry. `standard` entries get no card (ADR 0003).
- Every `work` project gets a case study at `projects/<repo>.html`, and every `tool`
  a "For everyone" page at `for-everyone/<repo>.html`, both from
  `content/projects/<repo>.md` (ADR 0008).
- Beyond the shared code, a number may come from a second results file, from a list
  item in a JSON path, from a Value cell with thousands commas, or, as a row entry,
  from the Value cell itself when its Source is not a JSON file (ADR 0008).
- Each `notes/*.md` file is a note. Its first line of text is either
  `DRAFT: Iliya to edit` or `Published: YYYY-MM-DD` (ADR 0005). A draft never reaches
  `_site/`: its Markdown goes to `_build/md/drafts/` for the checks, and its page to
  `_build/preview/` for reading. After the build, the marker anywhere in `_site/`
  fails it. A `<!-- chart: name -->` line in a note draws a chart from built numbers.
- Output goes to `_site/` (what is deployed) and `_build/md/` (each page's prose as
  filled-in Markdown, for the writing and number checks). Both are gitignored.
- `static/` is copied unchanged, and `googleb968c9a0c91c49c6.html` is copied byte for
  byte to the root of `_site/`.

`--offline` reads `tests/fixtures/` instead of the network. It needs no network.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
import tomllib
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parent

from scripts.shared.render_readme import (  # noqa: E402
    GITHUB_USER,
    ClaimRow,
    Fetcher,
    NumberConfig,
    OfflineFetcher,
    OnlineFetcher,
    ProjectConfig,
    RenderError,
    format_number,
    load_config,
    parse_claims_table,
    source_matches,
    value_cell_matches,
)
from scripts.shared.render_readme import PLACEHOLDER_RE as NUMBER_PLACEHOLDER_RE  # noqa: E402

SITE_DIR = ROOT / "_site"
BUILD_MD_DIR = ROOT / "_build" / "md"
TEMPLATES_DIR = ROOT / "templates"
PARTIALS_DIR = ROOT / "partials"
CONTENT_DIR = ROOT / "content"
STATIC_DIR = ROOT / "static"
CONFIG_PATH = ROOT / "projects.toml"
NOTES_DIR = ROOT / "notes"
VERIFICATION_FILE = "googleb968c9a0c91c49c6.html"

# ADR 0005: a note whose first line of text starts with this is a draft.
DRAFT_MARKER = "DRAFT: Iliya to edit"
PUBLISHED_RE = re.compile(r"^Published: (\d{4}-\d{2}-\d{2})$")
CHART_RE = re.compile(r"^<!--\s*chart:\s*([a-z0-9_]+)\s*-->[ \t]*$", re.M)

PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")
SLOT_RE = re.compile(r"^<!--\s*slot:\s*([a-z0-9_]+)\s*-->[ \t]*$", re.M)
FRONT_MATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)
SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+")
# A number in a CLAIMS.md Value cell, with thousands commas kept together ("307,511").
# Otherwise it reads a cell the way the shared VALUE_NUMBER_RE does.
CELL_NUMBER_RE = re.compile(r"(?:(?<![\d.])-)?(?:\d{1,3}(?:,\d{3})+(?!\d)|\d+)(?:\.\d+)?%?")

KINDS = ("work", "tool", "standard")
CARD_KINDS = ("work", "tool")
# Where each kind's page goes, and the words that name it (ADR 0008).
PAGE_DIRS = {"work": "projects", "tool": "for-everyone"}
PAGE_LABELS = {"work": "CASE STUDY", "tool": "FOR EVERYONE"}
PAGE_LINK_TEXT = {"work": "Read the case study", "tool": "What it does, for everyone"}

MARKDOWN = MarkdownIt("commonmark").enable("table")


class BuildError(Exception):
    """Raised when the site cannot be built safely."""


@dataclass(frozen=True)
class Page:
    """One built page: which partials it is made of, in order, and its prose file."""

    output: str
    content: str
    partials: tuple[str, ...]
    script: str
    home: str
    contact_label: str
    root: str = ""
    project: SiteProject | None = None


PAGES = (
    Page(
        output="index.html",
        content="home.md",
        partials=("nav", "hero", "ticker", "risk", "fit", "work", "contact"),
        script="main.js",
        home="",
        contact_label="04 / CONTACT",
    ),
    Page(
        output="about.html",
        content="about.md",
        partials=("nav", "about", "now", "contact"),
        script="site.js",
        home="index.html",
        contact_label="06 / CONTACT",
    ),
)


@dataclass(frozen=True)
class Flag:
    """A true/false value in metrics.json, shown as one of two sentences."""

    id: str
    path: str
    if_true: str
    if_false: str


@dataclass(frozen=True)
class RowNumber:
    """A row entry (ADR 0002, ADR 0008): a number read from a CLAIMS.md Value cell."""

    id: str
    row: str
    index: int
    synthetic: bool = False


@dataclass(frozen=True)
class SiteProject:
    """The site's own fields for one `[[project]]` entry (ADR 0003, 0007, 0008)."""

    repo: str
    kind: str
    title: str = ""
    tags: tuple[str, ...] = ()
    summary: str = ""
    finding: str = ""
    headline: str = ""
    metric: str = ""
    metric_label: str = ""
    live_url: str = ""
    flags: tuple[Flag, ...] = ()
    number_files: tuple[tuple[str, str], ...] = ()
    row_numbers: tuple[RowNumber, ...] = ()


@dataclass
class Numbers:
    """What the number pipeline produced: shown values, flags, and the commits used."""

    values: dict[str, str]
    synthetic: set[str]
    flags: dict[str, bool]
    sources: dict[str, str]


# ---------------------------------------------------------------------------- config


def load_site_projects(path: Path) -> list[SiteProject]:
    """Read the site's own fields from projects.toml and check them."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    projects = []
    for p in data.get("project", []):
        repo = p["repo"]
        kind = p.get("kind", "")
        if kind not in KINDS:
            raise BuildError(f"{repo}: kind must be one of {KINDS}, not {kind!r}")
        flags = tuple(
            Flag(id=f["id"], path=f["path"], if_true=f["if_true"], if_false=f["if_false"])
            for f in p.get("flag", [])
        )
        number_files = tuple((n["id"], n["file"]) for n in p.get("number", []) if "file" in n)
        row_numbers = []
        for r in p.get("row_number", []):
            index = r.get("index")
            if not isinstance(index, int) or isinstance(index, bool) or index < 0:
                raise BuildError(f"{repo}: row_number {r.get('id')!r} needs an index of 0 or more")
            synthetic = bool(r.get("synthetic", False))
            row_numbers.append(RowNumber(r["id"], r["row"], index, synthetic))
        project = SiteProject(
            repo=repo,
            kind=kind,
            title=p.get("title", ""),
            tags=tuple(p.get("tags", [])),
            summary=p.get("summary", ""),
            finding=p.get("finding", ""),
            headline=p.get("headline", ""),
            metric=p.get("metric", ""),
            metric_label=p.get("metric_label", ""),
            live_url=p.get("live_url", ""),
            flags=flags,
            number_files=number_files,
            row_numbers=tuple(row_numbers),
        )
        if kind in CARD_KINDS and not (project.title and project.summary):
            raise BuildError(f"{repo}: a {kind} project needs a title and a summary")
        has_numbers = project.metric or project.flags or project.row_numbers
        if kind == "standard" and (project.title or has_numbers):
            raise BuildError(f"{repo}: a standard repo gets no card, number or flag (ADR 0003)")
        if bool(project.metric) != bool(project.metric_label):
            raise BuildError(f"{repo}: metric and metric_label go together")
        projects.append(project)
    return projects


# ---------------------------------------------------------------------------- numbers


def fetch_numbers(
    config: list[ProjectConfig], site: list[SiteProject], fetcher: Fetcher
) -> Numbers:
    """Fetch, match and format every configured number and flag.

    Every number is checked against its own repo's CLAIMS.md before the build
    trusts it, exactly like the profile's renderer does (ADR 0002), with the
    additions of ADR 0008. A failure stops the whole build: nothing is deployed, and
    the last good site stays up.
    """
    site_by_repo = {p.repo: p for p in site}
    numbers = Numbers(values={}, synthetic=set(), flags={}, sources={})
    for project in config:
        repo = project.repo
        extra = site_by_repo.get(repo, SiteProject(repo=repo, kind="standard"))
        if not (project.numbers or extra.flags or extra.row_numbers):
            continue
        commit = fetcher.commit(repo)
        numbers.sources[repo] = commit
        results = ResultFiles(fetcher, repo, commit)
        claim_rows = parse_claims_table(fetcher.read(repo, commit, "CLAIMS.md"))
        files = dict(extra.number_files)
        for number in project.numbers:
            file = files.get(number.id, project.metrics_file)
            row = find_row(claim_rows, number.row, repo, number.id)
            if not source_matches(row.source, file, number.path):
                raise RenderError(
                    f"{repo}: CLAIMS.md row '{number.row}' Source "
                    f"'{row.source}' does not cover {file}#{number.path}"
                )
            formatted = format_number(json_number(results.get(file), number.path), number)
            if not cell_matches(row.value, formatted, number):
                raise RenderError(
                    f"{repo}: {number.id} = {formatted} is not in CLAIMS.md "
                    f"row '{number.row}' Value cell '{row.value}'"
                )
            add_number(numbers, number.id, formatted, number.synthetic)
        for entry in extra.row_numbers:
            add_number(numbers, entry.id, row_value(claim_rows, entry, repo), entry.synthetic)
        for flag in extra.flags:
            numbers.flags[flag.id] = json_flag(results.get(project.metrics_file), flag.path)
    return numbers


class ResultFiles:
    """One repo's JSON results files at one commit, each read once."""

    def __init__(self, fetcher: Fetcher, repo: str, commit: str) -> None:
        self.fetcher, self.repo, self.commit = fetcher, repo, commit
        self.loaded: dict[str, Any] = {}

    def get(self, file: str) -> Any:
        if file not in self.loaded:
            self.loaded[file] = json.loads(self.fetcher.read(self.repo, self.commit, file))
        return self.loaded[file]


def add_number(numbers: Numbers, number_id: str, value: str, synthetic: bool) -> None:
    if number_id in numbers.values:
        raise BuildError(f"number id '{number_id}' is defined twice")
    numbers.values[number_id] = value
    if synthetic:
        numbers.synthetic.add(number_id)


def find_row(rows: list[ClaimRow], claim: str, repo: str, number_id: str) -> ClaimRow:
    """The CLAIMS.md row whose Claim cell is exactly `claim`."""
    row = next((r for r in rows if r.claim.strip() == claim.strip()), None)
    if row is None:
        raise RenderError(f"{repo}: CLAIMS.md has no row '{claim}' for {number_id}")
    return row


def json_number(data: Any, path: str) -> Decimal:
    """Read a dotted path out of parsed JSON, as a Decimal.

    The same as the shared `json_value`, except that a whole-number part also picks a
    list item (ADR 0008), so `results.6.all.hit_at_k.value` works.
    """
    node = data
    for part in path.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        else:
            raise RenderError(f"path '{path}' not found in its results file")
    if isinstance(node, bool) or not isinstance(node, int | float):
        raise RenderError(f"path '{path}' is not a number")
    return Decimal(repr(node))


def cell_numbers(value_cell: str) -> list[str]:
    """Every number in a Value cell, as written, with thousands commas kept together."""
    return CELL_NUMBER_RE.findall(value_cell)


def cell_matches(value_cell: str, formatted: str, number: NumberConfig) -> bool:
    """The shared Value-cell match, reading "307,511" as one number for `thousands`."""
    if number.thousands:
        value_cell = CELL_NUMBER_RE.sub(lambda m: m.group(0).replace(",", ""), value_cell)
    return value_cell_matches(value_cell, formatted, number)


def row_value(rows: list[ClaimRow], entry: RowNumber, repo: str) -> str:
    """A row entry's number, exactly as its CLAIMS.md Value cell writes it (ADR 0008)."""
    row = find_row(rows, entry.row, repo, entry.id)
    source_file = row.source.partition("#")[0].strip()
    if source_file.endswith(".json"):
        raise RenderError(
            f"{repo}: {entry.id}: row '{entry.row}' comes from {source_file}, so it needs "
            "a JSON entry with a path, not a row entry (ADR 0002)"
        )
    found = cell_numbers(row.value)
    if entry.index >= len(found):
        raise RenderError(
            f"{repo}: {entry.id}: Value cell '{row.value}' has no number at index {entry.index}"
        )
    return found[entry.index]


def fetch_sources(config: list[ProjectConfig], fetcher: Fetcher) -> dict[str, str]:
    """The commit used per metrics-bearing repo, for `_site/sources.json`."""
    return fetch_numbers(config, [], fetcher).sources


def json_flag(data: Any, path: str) -> bool:
    """Read a dotted key out of parsed JSON. It must be true or false."""
    node = data
    for part in path.split("."):
        if not (isinstance(node, dict) and part in node):
            raise BuildError(f"flag path '{path}' not found in metrics file")
        node = node[part]
    if not isinstance(node, bool):
        raise BuildError(f"flag path '{path}' is not true or false")
    return node


def fill_text(
    text: str,
    numbers: Numbers,
    flags: dict[str, Flag],
    where: str,
    all_synthetic: bool = False,
) -> str:
    """Fill flag and number placeholders in one piece of Markdown prose.

    Flags first, since a flag's sentence may hold number placeholders. Then every
    sentence that uses a synthetic number must say "synthetic" (ADR 0002). With
    `all_synthetic`, every number counts as synthetic (ADR 0008).
    """

    def fill_flag(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in flags:
            return match.group(0)
        text = flags[name].if_true if numbers.flags[name] else flags[name].if_false
        return text.strip()

    text = NUMBER_PLACEHOLDER_RE.sub(fill_flag, text)

    for sentence in SENTENCE_END_RE.split(text):
        used = set(NUMBER_PLACEHOLDER_RE.findall(sentence))
        marked = used if all_synthetic else used & numbers.synthetic
        if marked and "synthetic" not in sentence.lower():
            raise BuildError(
                f"{where}: {sorted(marked)} was measured on synthetic "
                f"data, but its sentence does not say 'synthetic': {sentence.strip()[:80]!r}"
            )

    def fill_number(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in numbers.values:
            raise BuildError(f"{where}: unknown number placeholder {{{{ {name} }}}}")
        return numbers.values[name]

    return NUMBER_PLACEHOLDER_RE.sub(fill_number, text)


# ---------------------------------------------------------------------------- content


def read_content(name: str) -> tuple[dict[str, str], dict[str, str]]:
    """Read one content file: its front matter and its named slots, in order."""
    path = CONTENT_DIR / name
    if not path.is_file():
        raise BuildError(f"missing content file: {path}")
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    front, text = parse_front_matter(text, path)
    parts = SLOT_RE.split(text)
    if parts[0].strip():
        raise BuildError(f"{path}: text before the first '<!-- slot: name -->' line")
    slots = {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}
    return front, slots


def parse_front_matter(text: str, path: Path) -> tuple[dict[str, str], str]:
    """Split off the `---` front matter. It must give a title and a description."""
    front: dict[str, str] = {}
    match = FRONT_MATTER_RE.match(text)
    if match:
        for line in match.group(1).splitlines():
            key, sep, value = line.partition(":")
            if not sep:
                raise BuildError(f"{path}: front matter line has no ':': {line!r}")
            front[key.strip()] = value.strip()
        text = text[match.end() :]
    for key in ("title", "description"):
        if key not in front:
            raise BuildError(f"{path}: front matter needs '{key}'")
    return front, text


def markdown_html(text: str) -> str:
    rendered: str = MARKDOWN.render(text)
    return rendered.strip()


def repo_url(repo: str) -> str:
    return f"https://github.com/{GITHUB_USER}/{repo}"


def project_card(
    index: int, project: SiteProject, numbers: Numbers, flags: dict[str, Flag]
) -> tuple[str, str]:
    """One Home card as HTML, and the same prose as Markdown for the checks."""
    where = f"projects.toml ({project.repo})"
    texts = [
        fill_text(t.strip(), numbers, flags, where)
        for t in (project.summary, project.finding, project.headline)
        if t.strip()
    ]
    body = "\n".join(markdown_html(t) for t in texts)

    metric_html = ""
    metric_md = ""
    if project.metric:
        if project.metric not in numbers.values:
            raise BuildError(f"{where}: metric '{project.metric}' is not a number in the config")
        is_synthetic = project.metric in numbers.synthetic
        if is_synthetic and "synthetic" not in project.metric_label.lower():
            raise BuildError(f"{where}: metric_label must say 'synthetic'")
        value = numbers.values[project.metric]
        label = html.escape(project.metric_label)
        metric_html = f'<div class="pmetric"><b>{value}</b><span>{label}</span></div>'
        metric_md = f"Headline number, {project.metric_label}: {value}."

    tags = "".join(f'<span class="tag2">{html.escape(t)}</span>' for t in project.tags)
    url = repo_url(project.repo)
    links = [
        f'<a href="{page_path(project)}">{PAGE_LINK_TEXT[project.kind]}</a>',
        f'<a href="{url}" target="_blank" rel="noopener">Code and write-up</a>',
    ]
    if project.live_url:
        live = html.escape(project.live_url, quote=True)
        links.append(f'<a href="{live}" target="_blank" rel="noopener">Try it live</a>')
    title = html.escape(project.title)
    card = (
        f'<article class="proj" id="{html.escape(project.repo, quote=True)}">\n'
        f'  <div class="pnum">{index:02d}</div>\n'
        f'  <div><h3><a href="{url}" target="_blank" rel="noopener">{title}</a></h3>\n'
        f"{body}\n"
        f'    <div class="tags">{tags}</div>\n'
        f'    <p class="plinks">{"".join(links)}</p></div>\n'
        f"  {metric_html}\n"
        f"</article>"
    )
    md = "\n\n".join([f"### {project.title}", *texts] + ([metric_md] if metric_md else []))
    return card, md


def project_cards(
    site: list[SiteProject], numbers: Numbers, flags: dict[str, Flag]
) -> tuple[str, str]:
    """Every work project, then every public tool, in config order (ADR 0003)."""
    ordered = [p for kind in CARD_KINDS for p in site if p.kind == kind]
    built = [project_card(i, p, numbers, flags) for i, p in enumerate(ordered, start=1)]
    return "\n".join(c for c, _ in built), "\n\n".join(m for _, m in built)


# ---------------------------------------------------------------------------- pages


def load_partial(name: str) -> str:
    path = PARTIALS_DIR / f"{name}.html"
    if not path.is_file():
        raise BuildError(f"missing partial: {path}")
    return path.read_text(encoding="utf-8")


def render_template(template_text: str, context: dict[str, str]) -> str:
    """Fill `{{ name }}` placeholders. Every value is trusted HTML, never escaped.

    Fails on a placeholder the context does not cover. Does not require every
    context entry to be used, because pages share one context shape.
    """

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in context:
            raise BuildError(f"template uses unknown placeholder: {{{{ {name} }}}}")
        return context[name]

    return PLACEHOLDER_RE.sub(replace, template_text)


def page_path(project: SiteProject) -> str:
    """Where a work or tool project's own page is built, relative to the site root."""
    return f"{PAGE_DIRS[project.kind]}/{project.repo}.html"


def project_pages(site: list[SiteProject]) -> list[Page]:
    """One page per work project, then per tool, in config order (ADR 0008)."""
    ordered = [p for kind in CARD_KINDS for p in site if p.kind == kind]
    return [
        Page(
            output=page_path(p),
            content=f"projects/{p.repo}.md",
            partials=("nav", "project", "contact"),
            script="site.js",
            home="../index.html",
            contact_label="02 / CONTACT",
            root="../",
            project=p,
        )
        for p in ordered
    ]


def project_context(project: SiteProject) -> dict[str, str]:
    """The labels and links a project page shows around its prose."""
    url = repo_url(project.repo)
    links = [f'<a href="{url}" target="_blank" rel="noopener">Code and full write-up</a>']
    if project.live_url:
        live = html.escape(project.live_url, quote=True)
        links.insert(0, f'<a href="{live}" target="_blank" rel="noopener">Try it live</a>')
    return {
        "page_label": f"01 / {PAGE_LABELS[project.kind]}",
        "project_title": html.escape(project.title),
        "project_links": "".join(links),
    }


def build_page(
    page: Page, numbers: Numbers, site: list[SiteProject], flags: dict[str, Flag]
) -> tuple[str, str]:
    """One page as HTML, and its prose as filled-in Markdown."""
    front, slots = read_content(page.content)
    where = f"content/{page.content}"
    all_synthetic = front.get("synthetic_only", "no") == "yes"
    filled = {
        name: fill_text(text, numbers, flags, where, all_synthetic) for name, text in slots.items()
    }

    context = {name: markdown_html(text) for name, text in filled.items()}
    context.update(
        home=page.home,
        root=page.root,
        contact_label=page.contact_label,
        script=f"{page.root}static/{page.script}",
        page_title=html.escape(front["title"]),
        page_description=html.escape(front["description"], quote=True),
    )
    if page.project is not None:
        context.update(project_context(page.project))
    md_parts = [f"Page title: {front['title']}.", front["description"], *filled.values()]
    if "work" in page.partials:
        cards_html, cards_md = project_cards(site, numbers, flags)
        context["project_cards"] = cards_html
        md_parts.append(cards_md)

    body = "\n\n".join(render_template(load_partial(name), context) for name in page.partials)
    context["body"] = body
    shell = (TEMPLATES_DIR / "page.html").read_text(encoding="utf-8")
    rendered = render_template(shell, context)
    if "{{" in rendered:
        raise BuildError(f"a placeholder was left unfilled in {page.output}")
    return rendered, "\n\n".join(md_parts) + "\n"


# ---------------------------------------------------------------------------- notes


@dataclass(frozen=True)
class Note:
    """One note from `notes/`, as a full HTML page and as filled-in Markdown."""

    slug: str
    published: str  # "" while the note is a draft (ADR 0005)
    html: str
    md: str

    @property
    def draft(self) -> bool:
        return not self.published


def note_status(text: str, path: Path) -> tuple[str, str]:
    """A note's publish date ("" for a draft), and its text after that first line.

    Per ADR 0005, the first line of text (a byte order mark and blank lines before it
    are ignored) is either the draft marker or `Published: YYYY-MM-DD`. The marker
    anywhere else fails the build, and so does a note with neither line.
    """
    lines = text.lstrip("﻿").replace("\r\n", "\n").split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    first = lines[0].strip() if lines else ""
    rest = "\n".join(lines[1:])
    if DRAFT_MARKER in rest or DRAFT_MARKER in first[len(DRAFT_MARKER) :]:
        raise BuildError(f"{path}: '{DRAFT_MARKER}' may only start the first line of text")
    if first.startswith(DRAFT_MARKER):
        return "", rest
    match = PUBLISHED_RE.match(first)
    if match is None:
        raise BuildError(
            f"{path}: the first line must be '{DRAFT_MARKER}' or 'Published: YYYY-MM-DD'"
        )
    try:
        date.fromisoformat(match.group(1))
    except ValueError as exc:
        raise BuildError(f"{path}: '{first}' is not a real date") from exc
    return match.group(1), rest


def word_pieces_chart(numbers: Numbers) -> tuple[str, str]:
    """A median bank-filings-rag page drawn to scale, with the part the model reads filled.

    Both lengths are the repo's own CLAIMS.md row entries (ADR 0002). The chart only
    scales them to a width. It shows no number of its own.
    """
    limit_text = numbers.values.get("bank_filings_rag.word_piece_limit", "")
    median_text = numbers.values.get("bank_filings_rag.median_word_pieces", "")
    if not (limit_text and median_text):
        raise BuildError("the word-piece chart needs the limit and the median page length")
    limit, median = Decimal(limit_text), Decimal(median_text)
    if not 0 < limit < median:
        raise BuildError("the word-piece chart needs a limit below the median page length")
    left, width, gap = 20, 360, 2
    read = round(float(width * limit / median), 1)
    rest_x, rest_w = left + read + gap, round(width - read - gap, 1)
    end = left + width
    label = (
        f"A bar for a median page of {median_text} word pieces. The first {limit_text} "
        "word pieces, the part the search model reads, are filled in. The rest is empty."
    )
    svg = (
        f'<svg viewBox="0 0 400 118" role="img" aria-label="{html.escape(label, quote=True)}">\n'
        f'  <text class="chart-label" x="{left}" y="30">Read: first {limit_text}</text>\n'
        f'  <text class="chart-label" x="{end}" y="30" text-anchor="end">'
        "Not read: the rest</text>\n"
        f'  <rect class="chart-read" x="{left}" y="40" width="{read}" height="30" rx="3">'
        f"<title>Read by the model: word pieces 1 to {limit_text}</title></rect>\n"
        f'  <rect class="chart-rest" x="{rest_x}" y="40" width="{rest_w}" height="30" rx="3">'
        f"<title>Never read: everything after word piece {limit_text}</title></rect>\n"
        f'  <text class="chart-tick" x="{left}" y="88">0</text>\n'
        f'  <text class="chart-tick" x="{left + read}" y="88" text-anchor="middle">'
        f"{limit_text}</text>\n"
        f'  <text class="chart-tick" x="{end}" y="88" text-anchor="end">{median_text}</text>\n'
        f'  <text class="chart-axis" x="{left + width / 2}" y="110" text-anchor="middle">'
        "word pieces on a median page</text>\n"
        "</svg>"
    )
    md = (
        f"Chart: one bar for a median page of {median_text} word pieces. The first "
        f"{limit_text} word pieces, the part the search model reads, are filled in."
    )
    return svg, md


CHARTS = {"word_pieces": word_pieces_chart}


def note_body(body: str, numbers: Numbers, where: str) -> tuple[str, str]:
    """A note's filled-in body as HTML and as Markdown, with each chart line drawn.

    A `<!-- chart: name -->` line becomes that chart, and the paragraph right after it
    becomes its caption. Every chart needs one.
    """
    parts = CHART_RE.split(body)
    html_parts = [markdown_html(parts[0])]
    md_parts = [parts[0].strip()]
    for i in range(1, len(parts), 2):
        name = parts[i]
        if name not in CHARTS:
            raise BuildError(f"{where}: unknown chart '{name}'")
        caption, _, after = parts[i + 1].strip().partition("\n\n")
        if not caption.strip():
            raise BuildError(f"{where}: chart '{name}' needs a caption paragraph after it")
        svg, chart_md = CHARTS[name](numbers)
        caption_html = MARKDOWN.renderInline(caption.strip())
        html_parts.append(
            f'<figure class="chart">\n{svg}\n<figcaption>{caption_html}</figcaption>\n</figure>'
        )
        md_parts += [chart_md, caption.strip()]
        if after.strip():
            html_parts.append(markdown_html(after))
            md_parts.append(after.strip())
    return "\n".join(html_parts), "\n\n".join(p for p in md_parts if p)


def build_note(path: Path, numbers: Numbers, flags: dict[str, Flag]) -> Note:
    """One note as a page in `notes/`, and its prose as filled-in Markdown."""
    published, rest = note_status(path.read_text(encoding="utf-8"), path)
    front, body = parse_front_matter(rest.lstrip("\n"), path)
    where = f"notes/{path.name}"
    body_html, body_md = note_body(fill_text(body, numbers, flags, where), numbers, where)
    title = html.escape(front["title"])
    context = {
        "home": "../index.html",
        "root": "../",
        "contact_label": "02 / CONTACT",
        "script": "../static/site.js",
        "page_title": f"{title} | Iliya Valizadeh",
        "page_description": html.escape(front["description"], quote=True),
        "page_label": "01 / NOTE",
        "note_title": title,
        "note_status": f"Published {published}" if published else "Draft, not published",
        "note_body": body_html,
    }
    parts = ("nav", "note", "contact")
    context["body"] = "\n\n".join(render_template(load_partial(n), context) for n in parts)
    shell = (TEMPLATES_DIR / "page.html").read_text(encoding="utf-8")
    rendered = render_template(shell, context)
    if "{{" in rendered:
        raise BuildError(f"a placeholder was left unfilled in {where}")
    md = "\n\n".join([f"Page title: {front['title']}.", front["description"], body_md]) + "\n"
    return Note(slug=path.stem, published=published, html=rendered, md=md)


def write_notes(notes: list[Note]) -> None:
    """Published notes go to `_site/notes/`. Drafts never do (ADR 0005).

    A draft's Markdown goes to `_build/md/drafts/notes/`, where the writing and number
    checks read it, and its page to `_build/preview/notes/` for reading before it is
    published. Neither folder is deployed.
    """
    preview_dir = BUILD_MD_DIR.parent / "preview"
    if preview_dir.exists():
        shutil.rmtree(preview_dir)
    for note in notes:
        if note.draft:
            md_path = BUILD_MD_DIR / "drafts" / "notes" / f"{note.slug}.md"
            html_path = preview_dir / "notes" / f"{note.slug}.html"
        else:
            md_path = BUILD_MD_DIR / "notes" / f"{note.slug}.md"
            html_path = SITE_DIR / "notes" / f"{note.slug}.html"
        for path, text in ((html_path, note.html), (md_path, note.md)):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
    if any(n.draft for n in notes):
        copy_static(preview_dir)


def check_no_draft_marker(site_dir: Path) -> None:
    """Fail if the draft marker reached any built file (ADR 0005's final scan)."""
    marker = DRAFT_MARKER.encode("utf-8")
    for path in sorted(site_dir.rglob("*")):
        if path.is_file() and marker in path.read_bytes():
            raise BuildError(f"{path}: the draft marker reached the built site (ADR 0005)")


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


def build(offline: bool) -> None:
    config = load_config(CONFIG_PATH)
    site = load_site_projects(CONFIG_PATH)
    fetcher: Fetcher = OfflineFetcher(ROOT / "tests" / "fixtures") if offline else OnlineFetcher()
    numbers = fetch_numbers(config, site, fetcher)
    flags = {f.id: f for p in site for f in p.flags}

    all_pages = [*PAGES, *project_pages(site)]
    pages = [(page, *build_page(page, numbers, site, flags)) for page in all_pages]
    notes = [build_note(path, numbers, flags) for path in sorted(NOTES_DIR.glob("*.md"))]

    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    SITE_DIR.mkdir(parents=True)
    if BUILD_MD_DIR.exists():
        shutil.rmtree(BUILD_MD_DIR)
    BUILD_MD_DIR.mkdir(parents=True)

    for page, page_html, page_md in pages:
        md_path = (BUILD_MD_DIR / page.output).with_suffix(".md")
        for path, text in ((SITE_DIR / page.output, page_html), (md_path, page_md)):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
    copy_static(SITE_DIR)
    copy_verification_file(SITE_DIR)
    sources_text = json.dumps(numbers.sources, indent=2, sort_keys=True) + "\n"
    (SITE_DIR / "sources.json").write_text(sources_text, encoding="utf-8", newline="\n")
    write_notes(notes)
    check_no_draft_marker(SITE_DIR)


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
