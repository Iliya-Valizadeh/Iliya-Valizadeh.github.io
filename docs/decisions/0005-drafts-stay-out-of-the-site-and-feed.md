# 0005: Drafts stay out of the site and the feed

Date: 2026-09-26. Status: accepted.

## Context

Plan section `5.7` asks for three short notes in Iliya's voice. Each starts with the
line `DRAFT: Iliya to edit` and must not be published until he removes that line
himself. The site also has an RSS feed, and the profile lists published notes. A draft
must not leak through any of these.

## Options

1. Keep drafts on another branch. Easy to forget, and they would miss the checks.
2. Keep drafts in the repo and trust each task to leave them out. Nothing checks it.
3. Keep drafts in the repo, have the build drop them by one written rule, and fail the
   build if the marker ever reaches the output.

## Decision

Option 3, with the same rule as the profile repo.

What counts as a draft:

- A file is a draft when its first line of text starts with `DRAFT: Iliya to edit`.
  Blank lines and a UTF-8 byte order mark before it are ignored. This applies to notes
  and to pages in `content/`.
- A section is a draft when the first line of text under its heading starts with the
  marker. The heading and everything under it, up to the next heading of the same or a
  higher level, are left out.

What the build does with a draft:

- It writes the draft to `_build/md/drafts/`, so the writing and number checks still
  read it.
- It leaves the draft out of `_site/`. The draft gets neither a page nor a link from
  another page. It is also missing from the Notes index, `feed.xml` and `notes.json`.
- It fails if the marker text appears anywhere in a file other than as the first line
  of a file or section. It does not guess what a stray marker means.
- After the build, it fails if `DRAFT: Iliya to edit` appears anywhere under `_site/`.

Publishing a note:

- Iliya deletes the marker line and adds a line `Published: YYYY-MM-DD` with the date
  he chooses. The build never makes up a date. A note without the marker and without a
  valid `Published:` line fails the build.
- The next deploy (on push, or the daily run) publishes it. The profile picks it up
  from `notes.json` on its next daily sync.

With no published notes:

- The Notes page says in one plain sentence that no notes are published yet. It does
  not name the drafts or promise dates.
- `feed.xml` is still a valid RSS file, with no items.
- `notes.json` is an empty list. The profile then leaves out its Notes section.

Tests cover each case with small fixtures: a draft note, a draft section, a stray
marker, a published note with and without its date, and zero published notes. With the
three real notes still drafts, a test checks that the built Notes page shows the
"no notes yet" sentence and that `feed.xml` has no items.

## Consequences

- Iliya controls publication with one line per note.
- A draft cannot reach the live site, the feed or the profile, even by mistake in a
  template, because the final scan of `_site/` catches the marker.
- Drafts are still checked, so what he edits is already clean.
