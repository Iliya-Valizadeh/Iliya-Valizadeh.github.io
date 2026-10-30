"""Build the site: Home, About and one page per project, from templates and content.

Usage: python build.py [--offline]

Per docs/decisions/0001-a-small-python-build-deployed-by-actions.md,
docs/decisions/0007-home-and-about-pages.md and docs/decisions/0008-project-pages.md:

- `templates/page.html` is the shell every page shares. `partials/*.html` are the
  blocks a page is made of. Both hold markup and short labels only. The About
  paragraphs are kept word for word from the old page (ADR 0006, ADR 0015). The pages
  are one plain column with no script (ADR 0015).
- Prose lives in `content/*.md` (one file per page, split into named slots by
  `<!-- slot: name -->` lines) and in the card fields of `projects.toml`. It is
  Markdown, turned into HTML with markdown-it-py.
- Numbers are never typed. A `{{ repo.name }}` placeholder in prose is filled from
  that repo's `reports/metrics.json`, and only after the value is found in the repo's
  own `CLAIMS.md` (ADR 0002). A sentence that uses a number measured on synthetic
  data must say "synthetic". A `[[project.flag]]` turns a true/false value in
  `metrics.json` into one of two sentences.
- The Home project list is a loop over `projects.toml` (ADR 0015): every `featured`
  entry, with its chart and result sentence, then every `other` entry as one short
  item. `standard` entries are not listed.
- A project with a `page` gets that page, built from `content/projects/<repo>.md`
  (ADR 0008).
- Beyond the shared code, a number may come from a second results file, from a list
  item in a JSON path, from a Value cell with thousands commas, or, as a row entry,
  from the Value cell itself when its Source is not a JSON file (ADR 0008).
- Each `notes/*.md` file is a note. Its first line of text is either
  `DRAFT: Iliya to edit` or `Published: YYYY-MM-DD` (ADR 0005). A draft never reaches
  `_site/`: its Markdown goes to `_build/md/drafts/` for the checks, and its page to
  `_build/preview/` for reading. After the build, the marker anywhere in `_site/`
  fails it. A `<!-- chart: name -->` line in a note draws a chart from built numbers.
- Published notes get a Notes index (`notes/index.html`), an RSS feed (`feed.xml`) and
  `notes.json` for the profile. All three list published notes only. With none, the
  index says no notes are published yet, the feed has no items and `notes.json` is an
  empty list (ADR 0005 and ADR 0011).
- Every page carries Open Graph and Twitter card tags, with an absolute `og:url`.
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
from datetime import UTC, date, datetime
from decimal import Decimal
from email.utils import format_datetime
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape

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
# Where the site is served (a user site), for the absolute links that Open Graph, the
# feed and notes.json need.
SITE_URL = "https://iliya-valizadeh.github.io"
SITE_NAME = "Iliya Valizadeh"

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

KINDS = ("featured", "other", "standard")
CHART_FIELDS = ("chart", "chart_source", "chart_alt", "chart_caption")
CHARTS_DIR = STATIC_DIR / "charts"
PAGE_RE = re.compile(r"^[a-z0-9-]+/[a-z0-9.-]+\.html$")

MARKDOWN = MarkdownIt("commonmark").enable("table")


class BuildError(Exception):
    """Raised when the site cannot be built safely."""


@dataclass(frozen=True)
class Page:
    """One built page: which partials it is made of, in order, and its prose file."""

    output: str
    content: str
    partials: tuple[str, ...]
    root: str = ""
    project: SiteProject | None = None


PAGES = (
    Page(output="index.html", content="home.md", partials=("nav", "home", "contact")),
    Page(output="about.html", content="about.md", partials=("nav", "about", "contact")),
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
    about: str = ""
    result: str = ""
    summary: str = ""
    chart: str = ""
    chart_source: str = ""
    chart_alt: str = ""
    chart_caption: str = ""
    page: str = ""
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
        text = {
            key: p.get(key, "")
            for key in ("title", "about", "result", "summary", "page", "live_url", *CHART_FIELDS)
        }
        project = SiteProject(
            repo=repo,
            kind=kind,
            flags=flags,
            number_files=number_files,
            row_numbers=tuple(row_numbers),
            **text,
        )
        check_site_project(project)
        projects.append(project)
    return projects


def check_site_project(project: SiteProject) -> None:
    """The rules of ADR 0015 for one entry's own fields."""
    repo, kind = project.repo, project.kind
    if kind == "featured" and not (project.title and project.result):
        raise BuildError(f"{repo}: a featured project needs a title and a result")
    if kind == "other" and not (project.title and project.summary):
        raise BuildError(f"{repo}: an other project needs a title and a summary")
    has_numbers = project.flags or project.row_numbers
    if kind == "standard" and (project.title or project.page or has_numbers):
        raise BuildError(f"{repo}: a standard repo gets no entry, page, number or flag")
    charts = [bool(getattr(project, f)) for f in CHART_FIELDS]
    if any(charts) and not all(charts):
        raise BuildError(f"{repo}: {', '.join(CHART_FIELDS)} go together")
    if project.chart and kind != "featured":
        raise BuildError(f"{repo}: only a featured project shows a chart")
    if project.chart and not (CHARTS_DIR / project.chart).is_file():
        raise BuildError(f"{repo}: chart file not found: static/charts/{project.chart}")
    if project.page and not PAGE_RE.match(project.page):
        raise BuildError(f"{repo}: page must look like 'folder/name.html', not {project.page!r}")


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


def png_size(path: Path) -> tuple[int, int]:
    """Width and height of a PNG, read from its header, so the page can reserve room."""
    head = path.read_bytes()[:24]
    if head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        raise BuildError(f"{path}: not a PNG file")
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


def inline_html(text: str) -> str:
    """One piece of Markdown as inline HTML, with its line breaks joined."""
    rendered: str = MARKDOWN.renderInline(" ".join(text.split()))
    return rendered


def featured_entry(
    project: SiteProject, numbers: Numbers, flags: dict[str, Flag]
) -> tuple[str, str]:
    """One featured project on Home as HTML, and its prose as Markdown for the checks."""
    where = f"projects.toml ({project.repo})"
    url = repo_url(project.repo)
    about = fill_text(project.about.strip(), numbers, flags, where)
    result = fill_text(project.result.strip(), numbers, flags, where)
    parts = [f'<h3><a href="{url}">{html.escape(project.title)}</a></h3>']
    md = [f"### {project.title}"]
    if about:
        parts.append(f"<p>{inline_html(about)}</p>")
        md.append(about)
    parts.append(f"<p>{inline_html(result)}</p>")
    md.append(result)
    if project.chart:
        caption = fill_text(project.chart_caption.strip(), numbers, flags, where)
        width, height = png_size(CHARTS_DIR / project.chart)
        source = f"{url}/blob/main/{project.chart_source}"
        parts.append(
            "<figure>\n"
            f'<img src="static/charts/{html.escape(project.chart, quote=True)}" '
            f'alt="{html.escape(project.chart_alt, quote=True)}" '
            f'width="{width}" height="{height}" loading="lazy">\n'
            f"<figcaption>{inline_html(caption)} Chart from "
            f'<a href="{source}"><code>{html.escape(project.chart_source)}</code></a>.'
            "</figcaption>\n</figure>"
        )
        md += [f"Chart: {project.chart_alt}", caption]
    if project.page:
        parts.append(f'<p><a href="{project.page}">Project page for {project.title}</a></p>')
    entry = f'<article class="project" id="{project.repo}">\n' + "\n".join(parts) + "\n</article>"
    return entry, "\n\n".join(md)


def other_entry(project: SiteProject, numbers: Numbers, flags: dict[str, Flag]) -> tuple[str, str]:
    """One short item in the Home list of other projects, as HTML and as Markdown."""
    where = f"projects.toml ({project.repo})"
    summary = fill_text(project.summary.strip(), numbers, flags, where)
    links = []
    if project.live_url:
        links.append(f'<a href="{html.escape(project.live_url, quote=True)}">try it live</a>')
    if project.page:
        links.append(f'<a href="{project.page}">project page</a>')
    more = f" ({', '.join(links)})" if links else ""
    title = f'<a href="{repo_url(project.repo)}">{html.escape(project.title)}</a>'
    item = f'<li id="{project.repo}">{title}: {inline_html(summary)}{more}</li>'
    return item, f"- {project.title}: {' '.join(summary.split())}"


def project_lists(
    site: list[SiteProject], numbers: Numbers, flags: dict[str, Flag]
) -> dict[str, str]:
    """The featured entries and the list of other projects, in config order (ADR 0015)."""
    featured = [featured_entry(p, numbers, flags) for p in site if p.kind == "featured"]
    others = [other_entry(p, numbers, flags) for p in site if p.kind == "other"]
    return {
        "featured": "\n".join(h for h, _ in featured),
        "others": '<ul class="others">\n' + "\n".join(h for h, _ in others) + "\n</ul>",
        "projects_md": "\n\n".join([*(m for _, m in featured), "\n".join(m for _, m in others)]),
    }


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


def project_pages(site: list[SiteProject]) -> list[Page]:
    """One page per project that sets `page`, in config order (ADR 0008, ADR 0015)."""
    return [
        Page(
            output=p.page,
            content=f"projects/{p.repo}.md",
            partials=("nav", "project", "contact"),
            root="../",
            project=p,
        )
        for p in site
        if p.page
    ]


def project_context(project: SiteProject) -> dict[str, str]:
    """The title and links a project page shows around its prose."""
    links = [f'<a href="{repo_url(project.repo)}">Code and full write-up on GitHub</a>']
    if project.live_url:
        live = html.escape(project.live_url, quote=True)
        links.insert(0, f'<a href="{live}">Try it live</a>')
    return {
        "project_title": html.escape(project.title),
        "project_links": " | ".join(links),
    }


def page_url(output: str) -> str:
    """The absolute address of a built page. `index.html` is served at its folder."""
    if output == "index.html":
        return f"{SITE_URL}/"
    return f"{SITE_URL}/{output.removesuffix('index.html')}"


def build_page(
    page: Page,
    numbers: Numbers,
    site: list[SiteProject],
    flags: dict[str, Flag],
    notes: list[Note] | None = None,
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
        root=page.root,
        page_title=html.escape(front["title"]),
        page_description=html.escape(front["description"], quote=True),
        page_url=page_url(page.output),
        og_type="website",
    )
    if page.project is not None:
        context.update(project_context(page.project))
    md_parts = [f"Page title: {front['title']}.", front["description"], *filled.values()]
    if "notes" in page.partials:
        list_html, list_md = notes_list(notes or [])
        if list_html:
            context["note_list"] = list_html
            md_parts.append(list_md)
        else:
            context["note_list"] = context["empty"]
    if "home" in page.partials:
        lists = project_lists(site, numbers, flags)
        context.update(featured=lists["featured"], others=lists["others"])
        md_parts.append(lists["projects_md"])
        # The Notes index is linked from Home only once a note is published (ADR 0015).
        context["notes_link"] = (
            '<p>I also write short <a href="notes/index.html">notes</a> on what I find.</p>'
            if published_notes(notes or [])
            else ""
        )

    parts_html = [render_template(load_partial(name), context) for name in page.partials]
    # The nav stays outside <main>, so the skip link and screen readers can jump past it.
    body = (
        parts_html[0]
        + '\n\n<main id="main" tabindex="-1">\n'
        + "\n\n".join(parts_html[1:])
        + "\n</main>"
    )
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
    title: str = ""
    description: str = ""

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


def _chart_numbers(numbers: Numbers, ids: list[str], chart: str) -> list[tuple[str, Decimal]]:
    """The shown text and the value of each number a chart needs, or a build error."""
    texts = [numbers.values.get(f"credit_risk_scorecard.{i}", "") for i in ids]
    if not all(texts):
        raise BuildError(f"the {chart} chart needs these numbers: {', '.join(ids)}")
    values = [Decimal(t.rstrip("%").replace(",", "")) for t in texts]
    if not all(v > 0 for v in values):
        raise BuildError(f"the {chart} chart needs numbers above zero")
    return list(zip(texts, values, strict=True))


def mean_pd_chart(numbers: Numbers) -> tuple[str, str]:
    """Three bars: the raw and calibrated average PD, and the real default rate.

    All three are credit-risk-scorecard CLAIMS.md entries (ADR 0002). The bars are
    scaled to the largest one. The chart shows no number of its own.
    """
    shown = _chart_numbers(
        numbers, ["raw_mean_pd", "isotonic_mean_pd", "observed_default_rate"], "mean PD"
    )
    labels = ["Raw model", "After calibration", "Real default rate"]
    top = max(v for _, v in shown)
    left, bar_x, width = 20, 170, 180
    rows = []
    for i, (label, (text, value)) in enumerate(zip(labels, shown, strict=True)):
        y = 14 + i * 34
        w = round(float(width * value / top), 1)
        rows.append(
            f'  <text class="chart-label" x="{left}" y="{y + 15}">{label}</text>\n'
            f'  <rect class="chart-read" x="{bar_x}" y="{y}" width="{w}" height="22" rx="3">'
            f"<title>{label}: {text}</title></rect>\n"
            f'  <text class="chart-tick" x="{round(bar_x + w + 6, 1)}" y="{y + 15}">{text}</text>'
        )
    parts = [f"{label}: {text}" for label, (text, _) in zip(labels, shown, strict=True)]
    label = "Average chance of default on the test part. " + ". ".join(parts) + "."
    svg = (
        f'<svg viewBox="0 0 400 134" role="img" aria-label="{html.escape(label, quote=True)}">\n'
        + "\n".join(rows)
        + f'\n  <text class="chart-axis" x="{bar_x + width / 2}" y="126" text-anchor="middle">'
        "average chance of default</text>\n</svg>"
    )
    md = (
        "Chart: three bars for the average chance of default on the test part. "
        + "; ".join(parts)
        + "."
    )
    return svg, md


def gender_approval_chart(numbers: Numbers) -> tuple[str, str]:
    """Approval rates for women and men, with and without gender as an input.

    One row per model, a dot per group and a line for the gap between them. The four
    rates are credit-risk-scorecard CLAIMS.md entries (ADR 0002). The x scale only
    spans those rates. The chart shows no number of its own.
    """
    shown = _chart_numbers(
        numbers,
        [
            "approval_women_with_gender_pct",
            "approval_men_with_gender_pct",
            "approval_women_without_gender_pct",
            "approval_men_without_gender_pct",
        ],
        "approval",
    )
    lo, hi = min(v for _, v in shown), max(v for _, v in shown)
    if lo == hi:
        raise BuildError("the approval chart needs rates that differ")
    pad = (hi - lo) / 4
    x0, span = 150, 230

    def x(value: Decimal) -> float:
        return round(float(x0 + span * (value - lo + pad) / (hi - lo + 2 * pad)), 1)

    rows, parts = [], []
    for i, model in enumerate(["With gender", "Without gender"]):
        (w_text, w_val), (m_text, m_val) = shown[2 * i], shown[2 * i + 1]
        cy = 46 + i * 50
        xw, xm = x(w_val), x(m_val)
        rows.append(
            f'  <text class="chart-label" x="20" y="{cy + 4}">{model}</text>\n'
            f'  <line class="chart-line" x1="{xm}" y1="{cy}" x2="{xw}" y2="{cy}"/>\n'
            f'  <circle class="chart-read" cx="{xm}" cy="{cy}" r="6">'
            f"<title>{model}, men approved: {m_text}</title></circle>\n"
            f'  <circle class="chart-read" cx="{xw}" cy="{cy}" r="6">'
            f"<title>{model}, women approved: {w_text}</title></circle>\n"
            f'  <text class="chart-tick" x="{xm}" y="{cy - 12}" text-anchor="middle">'
            f"Men {m_text}</text>\n"
            f'  <text class="chart-tick" x="{xw}" y="{cy - 12}" text-anchor="middle">'
            f"Women {w_text}</text>"
        )
        parts.append(f"{model.lower()}, women {w_text} and men {m_text}")
    label = "Share of applicants approved: " + "; ".join(parts) + "."
    svg = (
        f'<svg viewBox="0 0 400 134" role="img" aria-label="{html.escape(label, quote=True)}">\n'
        + "\n".join(rows)
        + f'\n  <text class="chart-axis" x="{x0 + span / 2}" y="126" text-anchor="middle">'
        "share of applicants approved</text>\n</svg>"
    )
    md = "Chart: a dot for women and a dot for men, joined by a line, per model. " + label
    return svg, md


CHARTS = {
    "word_pieces": word_pieces_chart,
    "mean_pd": mean_pd_chart,
    "gender_approval": gender_approval_chart,
}


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
        "root": "../",
        "page_title": f"{title} | Iliya Valizadeh",
        "page_description": html.escape(front["description"], quote=True),
        "page_url": page_url(f"notes/{path.stem}.html"),
        "og_type": "article",
        "note_title": title,
        "note_status": f"Published {published}" if published else "Draft, not published",
        "note_body": body_html,
    }
    nav, note, contact = (
        render_template(load_partial(n), context) for n in ("nav", "note", "contact")
    )
    context["body"] = f'{nav}\n\n<main id="main" tabindex="-1">\n{note}\n\n{contact}\n</main>'
    shell = (TEMPLATES_DIR / "page.html").read_text(encoding="utf-8")
    rendered = render_template(shell, context)
    if "{{" in rendered:
        raise BuildError(f"a placeholder was left unfilled in {where}")
    md = "\n\n".join([f"Page title: {front['title']}.", front["description"], body_md]) + "\n"
    return Note(
        slug=path.stem,
        published=published,
        html=rendered,
        md=md,
        title=front["title"],
        description=front["description"],
    )


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


def published_notes(notes: list[Note]) -> list[Note]:
    """The notes that are not drafts, newest first (ADR 0005)."""
    items = [n for n in notes if not n.draft]
    return sorted(items, key=lambda n: (n.published, n.slug), reverse=True)


def notes_list(notes: list[Note]) -> tuple[str, str]:
    """The Notes index list as HTML and as Markdown. Both are empty with no notes."""
    items = published_notes(notes)
    if not items:
        return "", ""
    rows = []
    for n in items:
        rows.append(
            f'<li><a href="{html.escape(n.slug, quote=True)}.html">{html.escape(n.title)}</a>'
            f' <span class="notedate">{n.published}</span>'
            f"<br>{html.escape(n.description)}</li>"
        )
    md = "\n".join(f"- {n.title}, {n.published}. {n.description}" for n in items)
    return '<ul class="notelist">\n' + "\n".join(rows) + "\n</ul>", md


NOTES_PAGE = Page(
    output="notes/index.html",
    content="notes.md",
    partials=("nav", "notes", "contact"),
    root="../",
)


def feed_xml(notes: list[Note]) -> str:
    """An RSS 2.0 feed of the published notes. With none, it is valid and has no items."""
    items = []
    for n in published_notes(notes):
        url = page_url(f"notes/{n.slug}.html")
        when = datetime.combine(date.fromisoformat(n.published), datetime.min.time(), tzinfo=UTC)
        items.append(
            "    <item>\n"
            f"      <title>{xml_escape(n.title)}</title>\n"
            f"      <link>{url}</link>\n"
            f'      <guid isPermaLink="true">{url}</guid>\n'
            f"      <pubDate>{format_datetime(when, usegmt=True)}</pubDate>\n"
            f"      <description>{xml_escape(n.description)}</description>\n"
            "    </item>\n"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "  <channel>\n"
        f"    <title>{xml_escape(SITE_NAME)}: notes</title>\n"
        f"    <link>{page_url('notes/index.html')}</link>\n"
        "    <description>Short notes on what I found while building my data science "
        "projects.</description>\n"
        "    <language>en</language>\n"
        f'    <atom:link href="{SITE_URL}/feed.xml" rel="self" type="application/rss+xml"/>\n'
        + "".join(items)
        + "  </channel>\n</rss>\n"
    )


def notes_json(notes: list[Note]) -> str:
    """The published notes as a JSON list, for the profile README (ADR 0005)."""
    rows = [
        {
            "slug": n.slug,
            "title": n.title,
            "description": n.description,
            "published": n.published,
            "url": page_url(f"notes/{n.slug}.html"),
        }
        for n in published_notes(notes)
    ]
    return json.dumps(rows, indent=2, ensure_ascii=False) + "\n"


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

    notes = [build_note(path, numbers, flags) for path in sorted(NOTES_DIR.glob("*.md"))]
    all_pages = [*PAGES, *project_pages(site), NOTES_PAGE]
    pages = [(page, *build_page(page, numbers, site, flags, notes)) for page in all_pages]

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
    for name, text in (("feed.xml", feed_xml(notes)), ("notes.json", notes_json(notes))):
        (SITE_DIR / name).write_text(text, encoding="utf-8", newline="\n")
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
