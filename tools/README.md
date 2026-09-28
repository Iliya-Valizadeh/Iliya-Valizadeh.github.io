# tools

Do not edit the files in this folder. They are copied byte for byte from
`ds-project-standard/tools` at commit `602ec779782c7466703a2093832e0e091c3316b8`,
so that this repo checks its writing and its numbers the same way every other repo in
the portfolio does. `SOURCE.json` records the source commit and the SHA-256 hash of
each copy. `tests/test_vendored_tools.py` fails the build if a copy no longer matches
its hash.

`readme_sections.py` is not copied here, because this repo's README does not use the
project README layout (see [ADR 0004](../docs/decisions/0004-checks.md)).

To pick up a newer version of these tools, copy the files again from a newer commit of
`ds-project-standard` and update `SOURCE.json` on purpose. See
[ADR 0004](../docs/decisions/0004-checks.md).

## What each tool checks

| Tool | What it checks |
|---|---|
| `ai_signs_check.py` | Common signs of AI writing: puffery words, em dashes, bold lead-ins, title-case headings |
| `claims_check.py` | Every number in `CLAIMS.md` matches its source file, and every number in the docs is listed in `CLAIMS.md` |
| `readability_check.py` | Reading grade of the "In plain words" section and notes, reading grade of the rest |
| `links_check.py` | Links between local files and to sections inside them, with no network access |
| `lychee.toml` | Settings for lychee, which checks links to other websites |
