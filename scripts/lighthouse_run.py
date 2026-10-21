"""Run Lighthouse on every built page and write the scores to `reports/lighthouse.json`.

Usage (after `uv run python build.py --offline`):

    uv run python scripts/lighthouse_run.py

It serves `_site/` on 127.0.0.1, with text files gzip-compressed as GitHub Pages does,
and runs Lighthouse 12 on every page. Each page gets three runs: the mobile preset, the
desktop preset, and an accessibility-only run in dark mode. It keeps only the category
scores (0 to 100).
It never makes up a score: it copies what Lighthouse wrote, and it stops with an error
if a report is missing. Needs Node.js (for `npx`) and Chrome. Not part of CI, which has
no Chrome set up (ADR 0013).

Lighthouse can print a harmless "EPERM" error on Windows when it deletes its own temp
folder after it has already written the report. This script accepts a non-zero exit
only if the report file exists and is new.
"""

from __future__ import annotations

import functools
import gzip
import http.server
import json
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "_site"
OUTPUT = ROOT / "reports" / "lighthouse.json"
LIGHTHOUSE = "lighthouse@12"
CATEGORIES = ("performance", "accessibility", "best-practices", "seo")
PRESETS = ("mobile", "desktop")
# Accessibility only, desktop preset, with Chrome forced into dark mode.
DARK = "dark"
THRESHOLD = 90
# The Search Console ownership file is not a page of the site.
SKIP_PREFIXES = ("google",)


def page_paths(site: Path) -> list[str]:
    """Every built HTML page, as a path under `site`, in a stable order."""
    paths = []
    for path in sorted(site.rglob("*.html")):
        rel = path.relative_to(site).as_posix()
        if rel.startswith(SKIP_PREFIXES) or rel.startswith("static/"):
            continue
        paths.append(rel)
    return paths


def scores_from_report(
    report: dict[str, Any], categories: tuple[str, ...] = CATEGORIES
) -> dict[str, int]:
    """Whole-number scores out of 100 from one Lighthouse JSON report."""
    scores: dict[str, int] = {}
    for name in categories:
        try:
            raw = report["categories"][name]["score"]
        except KeyError as exc:
            raise ValueError(f"report has no categories.{name}.score") from exc
        if raw is None:
            raise ValueError(f"categories.{name}.score is null in this report")
        scores[name] = round(raw * 100)
    return scores


def summarise(runs: dict[str, dict[str, dict[str, int]]]) -> dict[str, Any]:
    """The lowest score per category and preset, and whether every score is 90 or more."""
    lowest: dict[str, dict[str, int]] = {}
    for preset in PRESETS:
        lowest[preset] = {
            name: min(page[preset][name] for page in runs.values()) for name in CATEGORIES
        }
    dark = [page[DARK]["accessibility"] for page in runs.values() if DARK in page]
    if dark:
        lowest[DARK] = {"accessibility": min(dark)}
    every_score_ok = all(
        score >= THRESHOLD for preset in lowest.values() for score in preset.values()
    )
    return {"lowest": lowest, "every_score_at_least_90": every_score_ok}


def build_report(
    runs: dict[str, dict[str, dict[str, int]]], lighthouse_version: str, fetch_time: str
) -> dict[str, Any]:
    return {
        "tool": f"Lighthouse {lighthouse_version}",
        "run_at": fetch_time,
        "how": "scripts/lighthouse_run.py on the offline build in _site/, served on 127.0.0.1",
        "scale": "0 to 100, as Lighthouse prints them",
        "summary": summarise(runs),
        "pages": runs,
    }


class _QuietHandler(http.server.SimpleHTTPRequestHandler):  # pragma: no cover
    """Serves files like GitHub Pages does: text files are gzip-compressed when the
    browser accepts it. Without this, Lighthouse would time the page over the wire with
    every byte uncompressed, which is slower than the live site."""

    def log_message(self, format: str, *args: Any) -> None:
        pass

    def do_GET(self) -> None:
        path = Path(self.translate_path(self.path.split("?")[0]))
        if path.is_dir():
            path = path / "index.html"
        compressible = path.suffix in (".html", ".css", ".js", ".json", ".xml", ".svg")
        if not (
            compressible and path.is_file() and "gzip" in self.headers.get("Accept-Encoding", "")
        ):
            super().do_GET()
            return
        body = gzip.compress(path.read_bytes())
        self.send_response(200)
        self.send_header("Content-Type", self.guess_type(str(path)))
        self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class _QuietServer(http.server.ThreadingHTTPServer):  # pragma: no cover
    def handle_error(self, request: Any, client_address: Any) -> None:
        pass  # Chrome closes sockets early; that is not an error worth printing


def _serve(site: Path) -> tuple[http.server.ThreadingHTTPServer, int]:  # pragma: no cover
    handler = functools.partial(_QuietHandler, directory=str(site))
    server = _QuietServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, int(server.server_address[1])


def _run_one(url: str, preset: str, out: Path, npx: str) -> dict[str, Any]:  # pragma: no cover
    out.unlink(missing_ok=True)
    cmd = [
        npx,
        "--yes",
        LIGHTHOUSE,
        url,
        "--output=json",
        f"--output-path={out}",
        "--chrome-flags=--headless=new --no-sandbox"
        + (" --force-dark-mode" if preset == DARK else ""),
        "--quiet",
        "--only-categories=" + ("accessibility" if preset == DARK else ",".join(CATEGORIES)),
    ]
    if preset in ("desktop", DARK):
        cmd.append("--preset=desktop")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=False)
    if not out.is_file():
        raise RuntimeError(
            f"Lighthouse wrote no report for {url} ({preset}):\n{result.stderr[-800:]}"
        )
    data: dict[str, Any] = json.loads(out.read_text(encoding="utf-8"))
    return data


def main() -> int:  # pragma: no cover
    npx = shutil.which("npx")
    if npx is None:
        print("npx not found: install Node.js first.", file=sys.stderr)
        return 1
    pages = page_paths(SITE)
    if not pages:
        print("No built pages in _site/: run `python build.py --offline` first.", file=sys.stderr)
        return 1
    server, port = _serve(SITE)
    runs: dict[str, dict[str, dict[str, int]]] = {}
    version = ""
    fetch_time = ""
    try:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "report.json"
            for rel in pages:
                runs[rel] = {}
                for preset in (*PRESETS, DARK):
                    report = _run_one(f"http://127.0.0.1:{port}/{rel}", preset, out, npx)
                    cats = ("accessibility",) if preset == DARK else CATEGORIES
                    runs[rel][preset] = scores_from_report(report, cats)
                    version = version or str(report.get("lighthouseVersion", ""))
                    fetch_time = fetch_time or str(report.get("fetchTime", ""))
                    print(rel, preset, runs[rel][preset], flush=True)
    finally:
        server.shutdown()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(build_report(runs, version, fetch_time), indent=2) + "\n", encoding="utf-8"
    )
    ok = summarise(runs)["every_score_at_least_90"]
    print("wrote", OUTPUT, "| every score 90 or more:", ok)
    return 0 if ok else 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
