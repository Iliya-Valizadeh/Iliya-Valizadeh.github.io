---
title: Document question answering, a case study | Iliya Valizadeh
description: How a question-answering tool over RBC's 2024 Annual Report was measured, why its search model sees only the top of each page, and why no setup clearly wins yet.
---
<!-- slot: lede -->
A tool that answers questions about RBC's 2024 Annual Report and names the page each
answer came from. The part I cared about most was measuring how often it finds the
right page.

<!-- slot: main -->
## The problem

An analyst who asks a question about a long bank report needs the answer and the page
it came from, so they can check it. If the search step misses the right page, the
answer cannot be trusted. So this project measures the search step: how often the
right page is in the top five results. That score is called
[hit@5](https://github.com/Iliya-Valizadeh/bank-filings-rag/blob/main/docs/glossary.md#hit5).

## What I did

- Wrote an
  [answer key](https://github.com/Iliya-Valizadeh/bank-filings-rag/blob/main/docs/glossary.md#answer-key)
  of {{ bank_filings_rag.n_all }} questions, each with the page that answers it. I
  checked {{ bank_filings_rag.n_verified }} of them myself by reading the report. The
  other {{ bank_filings_rag.n_script_only }} are checked by a script only.
- Split the report three ways: fixed {{ bank_filings_rag.chunk_words }}-word chunks,
  paragraphs and whole pages.
- Searched each split three ways:
  [dense search](https://github.com/Iliya-Valizadeh/bank-filings-rag/blob/main/docs/glossary.md#dense-search)
  by meaning,
  [BM25](https://github.com/Iliya-Valizadeh/bank-filings-rag/blob/main/docs/glossary.md#bm25)
  keyword search, and
  [hybrid search](https://github.com/Iliya-Valizadeh/bank-filings-rag/blob/main/docs/glossary.md#hybrid-search),
  which merges the two ranked lists.
- Turned the text into vectors on my own machine. A bank could not send its private
  filings to an outside service, so I wanted the search half to work without one.
  Writing the final answer does call Google's Gemini API, so the pages it finds leave
  the machine at that step.
- Used only the hand-checked questions for the headline, each result with a
  bootstrap interval.

## What I found

On the {{ bank_filings_rag.n_verified }} hand-checked questions:

| Split the report into | Search | hit@5 | {{ bank_filings_rag.interval_level }} interval |
|---|---|---|---|
| Fixed {{ bank_filings_rag.chunk_words }}-word chunks (baseline) | dense | {{ bank_filings_rag.baseline_hit5 }} | {{ bank_filings_rag.baseline_hit5_lo }} to {{ bank_filings_rag.baseline_hit5_hi }} |
| Whole pages (the first version) | dense | {{ bank_filings_rag.dense_pages_hit5 }} | {{ bank_filings_rag.dense_pages_hit5_lo }} to {{ bank_filings_rag.dense_pages_hit5_hi }} |
| Whole pages | hybrid | {{ bank_filings_rag.hit5 }} | {{ bank_filings_rag.hit5_lo }} to {{ bank_filings_rag.hit5_hi }} |

Whole pages with hybrid search score highest. But every interval overlaps the others.
With so few questions, one more right or wrong answer moves hit@5 by one twelfth. So I
cannot claim that any setup beats another. On all {{ bank_filings_rag.n_all }}
questions, hybrid search over fixed chunks is one question behind the best setup
({{ bank_filings_rag.all30_hybrid_chunks_hit5 }} against
{{ bank_filings_rag.all30_hybrid_pages_hit5 }}). That points to hybrid search mattering
more than whole pages, but most of those questions were checked by a script only.

The most useful finding was about the search model itself. The model that turns text
into vectors,
[all-MiniLM-L6-v2](https://github.com/Iliya-Valizadeh/bank-filings-rag/blob/main/docs/glossary.md#embedding),
reads at most {{ bank_filings_rag.word_piece_limit }}
[word pieces](https://github.com/Iliya-Valizadeh/bank-filings-rag/blob/main/docs/glossary.md#word-piece)
and ignores the rest. A page in this report has a median of
{{ bank_filings_rag.median_word_pieces }} word pieces, and
{{ bank_filings_rag.share_over_limit }} of pages are longer than the limit. So dense
search over whole pages mostly sees the top of each page. When I went through every
question the best setup misses, an answer past that limit was the largest single
cause. A model that reads more of each page could change which setup wins.

<!-- slot: weak -->
- Only {{ bank_filings_rag.n_verified }} questions are checked by hand, and the top
  setups' intervals overlap. A few more questions could change which setup looks best.
- There are no held-out questions. The best setup was picked on the same questions it
  is scored on.
- The search model reads only the start of each page, as above. This is measured, not
  fixed.
- I wrote the evaluation plan after the results existed. The scoring rule and the
  first results appeared in the same commit, so nothing proves the rule came first.
- It covers one report, from one bank, for one year. The answers Gemini writes are not
  scored at all.

The full ranked list is in
[docs/whats_weak.md](https://github.com/Iliya-Valizadeh/bank-filings-rag/blob/main/docs/whats_weak.md).

<!-- slot: next -->
## What I would do next

- Read the questions that only a script has checked, and write new questions after the
  setup is fixed, to get a fair held-out test.
- Split each page into pieces that fit the search model for the vectors, while still
  citing whole pages.
- Pin the exact version of the search model, so a new release cannot move the numbers.
- Add an interval for the gap between two setups, instead of comparing intervals by
  eye.

## Links

- [The code and the full write-up](https://github.com/Iliya-Valizadeh/bank-filings-rag)
- [The error analysis](https://github.com/Iliya-Valizadeh/bank-filings-rag/blob/main/reports/error_analysis.md),
  which explains every miss of the best setup by hand
- [The evaluation plan](https://github.com/Iliya-Valizadeh/bank-filings-rag/blob/main/docs/eval_plan.md),
  which says in its title that it came after the results
