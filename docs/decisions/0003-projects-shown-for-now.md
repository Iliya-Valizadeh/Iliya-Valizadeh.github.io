# 0003: The projects the site shows for now, with room for one more

Date: 2026-09-26. Status: accepted.

## Context

Plan section `5.7` asks for a Home page with three work projects and the public tool,
and a case-study page per project. The plan's third work project,
`fraud-review-queue`, is Phase C. Phase C has not started, because it needs a Kaggle
key that only Iliya can set up. The profile repo has the same gap: the plan's "six
pinned projects" become five rows there for now. The site must not suggest that a
project exists before it does.

## Options

1. Show three work projects, with the third marked as coming soon. This describes work
   that does not exist.
2. Write the two projects into the Home template. Adding the third later means editing
   templates, navigation and tests.
3. Drive the project lists from `projects.toml`, so adding a project is one new entry.

## Decision

Option 3. Each `[[project]]` entry in `projects.toml` has a `kind`:

- `work`: a project with a case-study page. Today: `credit-risk-scorecard` and
  `bank-filings-rag`.
- `tool`: a public tool with a "For everyone" page. Today: `second-look`, with a link
  to its live page. There is no "Find it in the report" demo, because it was not
  built.
- `standard`: a repo of rules and templates. Today: `ds-project-standard` and
  `.github`. They are linked from the text about how Iliya works. They get no card
  and no number.

So the Home page shows two work projects and one public tool for now, not three work
projects. Across both repos, five projects are shown.

The Home list, the project navigation and the case-study index are loops over these
entries. The templates have no project names, no fixed counts and no empty slot. There
is no card, page, link, number or "coming soon" text for `fraud-review-queue` anywhere
in the config, content, templates or output. Its name appears only in decision
records.

When Phase C is done, adding it to every list takes one new `[[project]]` entry. Its
case-study page is one new Markdown file in `content/projects/`, which Phase C writes
anyway.

A test proves the slot works without naming the future repo. It builds the site with
a test config that has one extra, made-up `work` project and a fixture page, and checks
that it appears in each list with no template change.

## Consequences

- Nothing on the site describes work that has not been done.
- Adding a project touches the config and adds its own page, nothing else.
- The review task at the end of this phase greps the config, content, templates and
  `_site/` for `fraud-review-queue` and expects no match.
