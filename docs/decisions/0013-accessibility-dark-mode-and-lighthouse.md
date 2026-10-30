# 0013: Accessibility, dark mode and how Lighthouse is run <!-- not-a-claim -->

Date: 2026-10-20. Status: accepted, then partly replaced by [ADR 0015](0015-one-plain-column.md). <!-- not-a-claim -->

## Context

The plan asks for dark mode, a mobile-first layout, the basics of WCAG 2.1 level AA, <!-- not-a-claim -->
and Lighthouse scores of 90 or more in every category. <!-- not-a-claim --> A first
Lighthouse run on the offline build found three real problems:

- Small grey text and gold text on the cream background were too faint to read well.
  <!-- not-a-claim -->
- On a phone the page links were hidden. A reader on a phone could not reach About or
  Notes from the top of the page.
- The mobile performance score sat just under the line, because the stylesheet for the
  Google fonts and the page script both held up the first paint.

Two constraints came from earlier ADRs. `static/main.js` must stay byte for byte as it
was ([ADR 0007](0007-home-and-about-pages.md)), and the HTML in `partials/` is kept
word for word ([ADR 0006](0006-text-kept-word-for-word-and-the-old-page.md)). So the
changes went into the stylesheet, the page shell and `build.py`, and into attributes
only in the partials.

## Decision

Colour and dark mode:

- The small grey text colour and the gold text colour were darkened until both read at
  least 4.5 to 1 against the page colours (the WCAG 2.1 AA rule for body text). <!-- not-a-claim -->
  <!-- not-a-claim -->
- Dark mode follows the visitor's system setting through `prefers-color-scheme`. There
  is no toggle, so there is no state to store. Every colour is a variable, and the dark
  set was picked to meet the same 4.5 to 1 rule. <!-- not-a-claim -->
- The risk panel sets its own text colour from a script I may not edit. In dark mode a
  CSS rule uses the normal text colour for that text, because red on a dark card is too
  faint. The gauge arc keeps its colour, and the written band ("Low risk") carries the
  meaning, so colour is never the only signal.
- The least-squares canvas draws in fixed colours set by `main.js`, so in dark mode it
  keeps a light panel.

Mobile, keyboard and screen readers:

- On narrow screens the page links now show in a second row instead of vanishing, and
  each link is large enough to tap (at least 24 by 24 pixels). <!-- not-a-claim -->
- Every page has a skip link, a `<main>` landmark (the nav stays outside it), a
  labelled nav, a visible focus outline on everything that can take focus, and a
  text label on the two canvases and the gauge that a screen reader can read.
- A `prefers-reduced-motion` rule turns off the ticker, the reveal-on-scroll motion
  and the other transitions.

Speed:

- The Google fonts stylesheet loads without blocking the first paint, with a
  `<noscript>` fallback, and the page script has `defer`. Three page-test checks that
  matched the exact `<script>` tag now match the tag with `defer`.

How Lighthouse is run:

- `scripts/lighthouse_run.py` serves `_site/` on 127.0.0.1 and runs Lighthouse 12 <!-- not-a-claim -->
  through `npx` on every built page. Each page gets a mobile run, a desktop run and an
  accessibility-only run with Chrome forced into dark mode.
- It writes `reports/lighthouse.json` and copies only what Lighthouse printed. The
  pure parts (reading a score, taking the lowest, the 90 line) have tests. The part <!-- not-a-claim -->
  that starts Chrome does not, and is not run in CI, which has no Chrome set up.
  <!-- not-a-claim -->
- On Windows, Lighthouse often prints an `EPERM` error when it deletes its own temp
  folder after it has already written the report. The script accepts a non-zero exit
  only when the report file exists.

## Consequences

- The scores in `reports/lighthouse.json` come from one real run on one machine, on
  the offline build. The local server gzip-compresses text files the way GitHub Pages
  does, because without that Lighthouse timed every byte uncompressed and the mobile
  performance score fell under the line on some runs. I have not run Lighthouse on the
  live site.
- Mobile performance is a simulated score and moves by a point or two between runs.
  Its lowest value sits at the 90 line, so a later run may read just under it. That is <!-- not-a-claim -->
  noise to watch, not a reason to loosen the check. <!-- not-a-claim -->
- I also looked at screenshots of the dark and phone layouts by hand. Those are not
  saved in the repo.
- Lighthouse runs automatic checks only. A pass is not proof the site works with a
  screen reader, and I have not tested with one.
- Re-run `scripts/lighthouse_run.py` after any change to the stylesheet, the page
  shell or the partials, then commit the new `reports/lighthouse.json`.
