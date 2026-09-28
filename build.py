"""Build the site: the Home and About pages, from templates, partials and content.

Usage: python build.py [--offline]

Per docs/decisions/0001-a-small-python-build-deployed-by-actions.md and
docs/decisions/0007-home-and-about-pages.md:

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
from pathlib import Path
from typing import Any

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parent

from scripts.shared.render_readme import (  # noqa: E402
    GITHUB_USER,
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
from scripts.shared.render_readme import PLACEHOLDER_RE as NUMBER_PLACEHOLDER_RE  # noqa: E402

SITE_DIR = ROOT / "_site"
BUILD_MD_DIR = ROOT / "_build" / "md"
TEMPLATES_DIR = ROOT / "templates"
PARTIALS_DIR = ROOT / "partials"
CONTENT_DIR = ROOT / "content"
STATIC_DIR = ROOT / "static"
CONFIG_PATH = ROOT / "projects.toml"
VERIFICATION_FILE = "googleb968c9a0c91c49c6.html"

PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")
SLOT_RE = re.compile(r"^<!--\s*slot:\s*([a-z0-9_]+)\s*-->[ \t]*$", re.M)
FRONT_MATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)
SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+")

KINDS = ("work", "tool", "standard")
CARD_KINDS = ("work", "tool")

MARKDOWN = MarkdownIt("commonmark")


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
class SiteProject:
    """The site's own fields for one `[[project]]` entry (ADR 0003, ADR 0007)."""

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
        )
        if kind in CARD_KINDS and not (project.title and project.summary):
            raise BuildError(f"{repo}: a {kind} project needs a title and a summary")
        if kind == "standard" and (project.title or project.metric or project.flags):
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
    trusts it, exactly like the profile's renderer does (ADR 0002). A failure stops
    the whole build: nothing is deployed, and the last good site stays up.
    """
    flags_by_repo = {p.repo: p.flags for p in site}
    numbers = Numbers(values={}, synthetic=set(), flags={}, sources={})
    for project in config:
        project_flags = flags_by_repo.get(project.repo, ())
        if not project.numbers and not project_flags:
            continue
        commit = fetcher.commit(project.repo)
        numbers.sources[project.repo] = commit
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
            numbers.values[number.id] = formatted
            if number.synthetic:
                numbers.synthetic.add(number.id)
        for flag in project_flags:
            numbers.flags[flag.id] = json_flag(metrics, flag.path)
    return numbers


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


def fill_text(text: str, numbers: Numbers, flags: dict[str, Flag], where: str) -> str:
    """Fill flag and number placeholders in one piece of Markdown prose.

    Flags first, since a flag's sentence may hold number placeholders. Then every
    sentence that uses a synthetic number must say "synthetic" (ADR 0002).
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
        if used & numbers.synthetic and "synthetic" not in sentence.lower():
            raise BuildError(
                f"{where}: {sorted(used & numbers.synthetic)} was measured on synthetic "
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
    front: dict[str, str] = {}
    match = FRONT_MATTER_RE.match(text)
    if match:
        for line in match.group(1).splitlines():
            key, sep, value = line.partition(":")
            if not sep:
                raise BuildError(f"{path}: front matter line has no ':': {line!r}")
            front[key.strip()] = value.strip()
        text = text[match.end() :]
    parts = SLOT_RE.split(text)
    if parts[0].strip():
        raise BuildError(f"{path}: text before the first '<!-- slot: name -->' line")
    slots = {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}
    for key in ("title", "description"):
        if key not in front:
            raise BuildError(f"{path}: front matter needs '{key}'")
    return front, slots


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
    links = [f'<a href="{url}" target="_blank" rel="noopener">Code and write-up</a>']
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


def build_page(
    page: Page, numbers: Numbers, site: list[SiteProject], flags: dict[str, Flag]
) -> tuple[str, str]:
    """One page as HTML, and its prose as filled-in Markdown."""
    front, slots = read_content(page.content)
    where = f"content/{page.content}"
    filled = {name: fill_text(text, numbers, flags, where) for name, text in slots.items()}

    context = {name: markdown_html(text) for name, text in filled.items()}
    context.update(
        home=page.home,
        contact_label=page.contact_label,
        script=f"static/{page.script}",
        page_title=html.escape(front["title"]),
        page_description=html.escape(front["description"], quote=True),
    )
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

    pages = [(page, *build_page(page, numbers, site, flags)) for page in PAGES]

    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    SITE_DIR.mkdir(parents=True)
    if BUILD_MD_DIR.exists():
        shutil.rmtree(BUILD_MD_DIR)
    BUILD_MD_DIR.mkdir(parents=True)

    for page, page_html, page_md in pages:
        (SITE_DIR / page.output).write_text(page_html, encoding="utf-8", newline="\n")
        md_name = Path(page.output).with_suffix(".md").name
        (BUILD_MD_DIR / md_name).write_text(page_md, encoding="utf-8", newline="\n")
    copy_static(SITE_DIR)
    copy_verification_file(SITE_DIR)
    sources_text = json.dumps(numbers.sources, indent=2, sort_keys=True) + "\n"
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
