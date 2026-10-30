# 0006: Text kept word for word, and what happens to the old page

Date: 2026-09-26. Status: accepted.

## Context

Phase E replaces the hand-written `index.html` with pages built by `build.py`. Parts of
the old page are my own words and my own work, and the new build should not rewrite
them. The old page is never deleted. The Google
site-verification file must keep working.

## Options

1. Rewrite the whole site to the plan and check every line again. I would have to
   find my own words again inside new text.
2. Keep those parts exactly as they are, and move them into the new build unchanged.

## Decision

Option 2.

Kept word for word:

- The About section, `<section id="about">`, headed "Who you would be working with".
  It becomes `partials/about.html` and appears on the About page.
- The two demos: the credit risk demo, `<section id="risk">`, and the least squares
  demo, `<section id="fit">`. They become partials, and the script that runs them
  moves to `static/` unchanged.

How this is checked:

- A test takes each kept section from `docs/archive/index-2026-09.html`, strips the
  tags, joins the white space, and compares the words with the same section in the
  built site. They must be equal.
- A test compares the moved script with the inline script in the archived page, byte
  for byte, after turning CRLF line endings into LF.
- The markup of a kept section may change only to fix accessibility, such as a missing
  label, in the accessibility task. Its words may not change.

The old page and the verification file:

- Once the new build makes an `index.html`, the scaffold task moves the old one with
  `git mv index.html docs/archive/index-2026-09.html`. It is never deleted, and the
  build never copies `docs/` into `_site/`.
- `googleb968c9a0c91c49c6.html` stays at the repo root and is copied byte for byte to
  the root of `_site/`, so Google can still find it.

Lines that will become untrue:

- The footer of the old page says the page was hand written without a framework or a
  template. Once the pages come from templates, the part about templates is no longer
  true. The scaffold
  task keeps it, because its job is to reproduce the old page exactly. The Home page
  task replaces it with a true sentence, and I pick the final words.
- The opening line says two models are "running on this page". If a later task moves
  the demos off the Home page, it must keep that line true in the same way.
- The "Built alone, start to finish" section is not on the kept list. The Home page
  task replaces it with the project list from `projects.toml`. Its sentence "No
  template" should be checked against the fact that the projects now share
  `ds-project-standard`. The review task looks at this.

Any other change to a kept part needs a new decision record.
No task in this phase rewrites a kept part on its own.

## Consequences

- My own words stay as I wrote them, and the demos behave as before.
- The old page stays in the repo as a record of what was live before this phase.
- The rest of the site's copy is a draft. I read it again before I share it.
