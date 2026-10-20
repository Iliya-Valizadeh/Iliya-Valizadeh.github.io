# 0011: Notes index, RSS feed and share tags <!-- not-a-claim -->

Date: 2026-10-20. Status: accepted.

## Context

ADR 0005 says what a draft is and what the Notes page, the feed and `notes.json` must
do with one. This task builds those three files. Plan section `5.7` also asks for Open
Graph tags on every page, so that a shared link shows a title and a description.

## Options

For the index:

1. A hand-written Notes page. A published note would need a second edit to appear.
2. A page built from the notes themselves, so the list, the feed and `notes.json`
   always agree.

For the share tags:

1. Tags only on the pages that have a picture. The site has no picture to share.
2. The same tags on every page, with a small card (`summary`) and no image.

## Decision

Option 2 in both cases.

- `notes/index.html` is built from `content/notes.md` (an intro and one "no notes yet"
  sentence) and from the list of published notes, newest first. Each entry has the
  title, the date and the description from the note's front matter. With no published
  notes, the page shows the one sentence and no list.
- `feed.xml` is RSS 2.0, with one item per published note. Each item has the title, the <!-- not-a-claim -->
  address, the same address as its `guid`, the date from the `Published:` line at
  midnight GMT, and the description. The feed has no build date, so the same input
  always gives the same file. With no published notes, it is a valid feed with no
  items.
- `notes.json` is a list of `{slug, title, description, published, url}`, newest
  first, and `[]` with no published notes. The profile reads it (profile ADR 0005).
- Every page has `og:title`, `og:description`, `og:type`, `og:url`, `og:site_name`,
  `og:locale`, a canonical link, `twitter:card`, `twitter:title` and
  `twitter:description`, plus a link to the feed. `og:type` is `article` for a note
  and `website` for every other page. The address is the full address on
  `https://iliya-valizadeh.github.io`.
- The card is `summary`, not `summary_large_image`, because the site has no share
  image yet. Adding one means a picture file and an `og:image` tag. That is a design
  choice for Iliya.
- The nav gets a Notes link on every page.
- Drafts are left out of all three files, by the same list ADR 0005 uses. A published
  note is the only thing the list is built from, so a draft has no path into them.

Section-level drafts from ADR 0005 are still not built. A draft marker below a
heading in a note fails the build with the "may only start" message, so it cannot
leak. Building the section rule is left until a note needs it.

## Consequences

- Publishing a note is still one edit. The index, the feed and `notes.json` follow on
  the next build.
- The tests build the real drafts and a fixture with two published notes and one
  draft, and check all three files, the tags on every page and the draft marker.
- A shared link shows the title and the description, but no picture.
