# 0015: One plain column that leads with three projects <!-- not-a-claim -->

Date: 2026-10-29. Status: accepted. Replaces the page design in ADR 0003, ADR 0007 and <!-- not-a-claim -->
ADR 0013, and the kept demos in ADR 0006. <!-- not-a-claim -->

## Context

The first version of the site looked like a template. It had a fake app window around
each demo, small capital labels such as "01 / MODEL", a gold italic tagline, a grid and
glow behind the header, rounded pill buttons, a custom cursor and three web fonts from
Google. The Home page opened with a credit risk demo whose weights I set by hand. A
reader could take that demo for one of my real models, and it was not one.

A person who hires for a data role reads a page like this for a minute or two. In that
time they should see my best projects, one real chart from each and one number they can
check.

## Options

1. Keep the design and only fix the text.
2. Rebuild the look from scratch with a new framework.
3. Keep the build, and change the pages to one plain column with no script.

## Decision

Option 3. The number pipeline, the checks and the deploy stay the same.

What the pages are now:

- One column on a white background, in the system font. Links are plain and
  underlined. A page loads one small stylesheet and runs no script. There is a single
  light theme.
- Home leads with three `featured` projects, in the order of `projects.toml`:
  nyc-rideshare-congestion, bank-filings-rag and credit-risk-scorecard. Each has its
  name linked to the repo, one result sentence with its numbers, and one chart. Then
  the `other` projects get one short entry each. Then a short About and Contact.
- Each chart is a PNG copied byte for byte from the project's own `reports/figures/`
  into `static/charts/`. It has alt text, a caption that says what to notice, and a
  link to the source file in the repo. The build reads the PNG's size so the page
  does not jump while it loads.
- nyc-rideshare-congestion has no outcome result yet, and its only committed figure is
  the template's example chart. So it shows no chart for now, and its sentence says
  what the pipeline has loaded and that the congestion pricing result is still to
  come. Its three numbers come from its `reports/source_manifest.json` and
  `reports/load_summary.json`, each checked against a row in its `CLAIMS.md`, the same
  way as every other number (ADR 0002).
- The Notes index and `feed.xml` are still built. Home links to the notes only once a
  note is published, so it never points at an empty page.
- Every page has a "Resume (PDF)" link to `/resume.pdf`. I add that file by hand. Until
  then the link checker skips that one path, and the exclusion in `lychee.site.toml`
  matches nothing else.

What was removed:

- The credit risk demo with hand-set weights, the least squares demo, the scrolling
  ticker and the hero block, with their partials and `static/main.js` and
  `static/site.js`. The archived old page, `docs/archive/index-2026-09.html`, still
  holds all of them, script included, word for word.
- The labels, the window frames, the tagline, the background effects and the pill
  buttons.

What stayed word for word: the four About paragraphs (ADR 0006). The test now compares
those paragraphs with the archive and no longer checks the demos or the old labels
around them.

## Consequences

- The site has no JavaScript, so it is quick and has less to break.
- A new featured project is one `[[project]]` entry, one PNG and, if it has a page, one
  Markdown file.
- Dark mode is gone. One light theme with strong contrast is easier to keep accessible.
- The Lighthouse scores in the README were measured again on the new pages.
