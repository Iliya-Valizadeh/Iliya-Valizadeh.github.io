---
title: Iliya Valizadeh | Data science that shows its work
description: Iliya Valizadeh studies data science at York University in Toronto. Every number in his projects traces back to the script that made it, and two small models run on this page.
---
<!-- slot: idea -->
Data science that shows its work.

<!-- slot: seeking -->
Seeking a Winter 2027 co-op in data science or analytics. I graduate in April 2028.

<!-- slot: work_intro -->
Each project ties every number to the script that made it, records its design choices,
and has a page on what is weak. This page reads each number from the project's own
results file when the site is built. It shows a number only if that project's
`CLAIMS.md` lists it. The commit each number came from is in
[sources.json](sources.json).

<!-- slot: how_i_work -->
Each project is built on the same template,
[ds-project-standard](https://github.com/Iliya-Valizadeh/ds-project-standard). It gives
every repo the same docs, tests and checks. A build stops when a number has no source,
a page is hard to read, or a link is broken. The shared issue forms and the pull
request checklist are in [.github](https://github.com/Iliya-Valizadeh/.github).
