DRAFT: Iliya to edit
---
title: My search model only read a quarter of each page
description: The model I used to search a long bank report reads only the start of each page. What that did to my results, and what I would change.
---
I built a tool that answers questions about RBC's 2024 Annual Report. It also names
the page each answer came from, so a reader can check it. Before it can answer, it has
to find the right page. I scored that step with one simple number: how often the right
page is in the top five results
([hit@5](https://github.com/Iliya-Valizadeh/bank-filings-rag/blob/main/docs/glossary.md#hit5)).

Later, I went back and read through the misses one by one. I found a problem I
had not planned for. The search model was only looking at the top of each page.

## How the search works

The tool can search in two ways.
[Dense search](https://github.com/Iliya-Valizadeh/bank-filings-rag/blob/main/docs/glossary.md#dense-search)
turns each page into a list of numbers, called a vector, that stands for what the page
means. Then it looks for pages whose vectors are close to the question's vector.
[BM25](https://github.com/Iliya-Valizadeh/bank-filings-rag/blob/main/docs/glossary.md#bm25)
is plain keyword search. It looks for pages that use the same words as the question.
[Hybrid search](https://github.com/Iliya-Valizadeh/bank-filings-rag/blob/main/docs/glossary.md#hybrid-search)
merges the two ranked lists into one.

For the vectors I used a small, free model,
[all-MiniLM-L6-v2](https://github.com/Iliya-Valizadeh/bank-filings-rag/blob/main/docs/glossary.md#embedding),
that runs on my own laptop. A bank could not send its private filings to an outside
service, so I wanted this part to work without one.

The model first cuts text into
[word pieces](https://github.com/Iliya-Valizadeh/bank-filings-rag/blob/main/docs/glossary.md#word-piece).
A word piece is a whole word or a part of one. The model reads at most
{{ bank_filings_rag.word_piece_limit }} word pieces. It drops everything after that,
and it does not warn you.

## How much of each page it missed

That limit sounds large until you compare it with the pages. The median page in this
report has {{ bank_filings_rag.median_word_pieces }} word pieces. In total,
{{ bank_filings_rag.share_over_limit }} of pages are longer than the limit. So on a
typical page, the vector describes about the top quarter of the page and nothing below
it.

<!-- chart: word_pieces -->
On a median page, the model reads only the filled part, and the dashed part never
reaches it.

A bank report is a hard case for this. Its pages are long, and many hold big tables. A
page can start on one topic and end on another. In the misses I read, the answer was often
far down the page, under text about something else. Dense search could not see it.
BM25 does not have this problem, because it reads the whole page.

## What it did to the results

I read every question that my best setup missed and wrote down a cause for each one.
The best setup was whole pages with hybrid search. On all
{{ bank_filings_rag.n_all }} questions in my
[answer key](https://github.com/Iliya-Valizadeh/bank-filings-rag/blob/main/docs/glossary.md#answer-key),
its hit@5 was {{ bank_filings_rag.all30_hybrid_pages_hit5 }}. Most of those questions
are checked only by a script. That left nine misses.

In five of the nine, the answer sat past word piece
{{ bank_filings_rag.word_piece_limit }} on the right page. That was the largest single
cause. In other misses, a word from the question appeared all over the report with
another meaning, or the tool found a page next to the right one. A few misses had more
than one cause.

Being past the limit did not always mean a miss. Six other questions also had their
answer past the limit, and the tool still found a right page. Sometimes the top of the page
was about the same topic, so the vector still matched. Sometimes keyword search found
the page, and the merge kept it.

My headline scores use only the {{ bank_filings_rag.n_verified }} questions that I
checked by hand. On those, whole pages with dense search scored
{{ bank_filings_rag.dense_pages_hit5 }} ({{ bank_filings_rag.interval_level }} interval
{{ bank_filings_rag.dense_pages_hit5_lo }} to {{ bank_filings_rag.dense_pages_hit5_hi }}).
Adding keyword search, which reads the whole page, gave
{{ bank_filings_rag.hit5 }} ({{ bank_filings_rag.hit5_lo }} to
{{ bank_filings_rag.hit5_hi }}). That fits the story. But the gap is one question, and
the two intervals overlap a lot. So this points in a direction. It does not prove that
the limit is what held dense search back.

Shorter chunks were not a fix on their own. Fixed {{ bank_filings_rag.chunk_words }}-word
chunks with dense search scored lowest, at {{ bank_filings_rag.baseline_hit5 }}
({{ bank_filings_rag.baseline_hit5_lo }} to {{ bank_filings_rag.baseline_hit5_hi }}).
Their interval overlaps too. The limit is one cause of misses, not the whole story.

## What I would change

First, I would split each long page into pieces that fit under the limit, and make one
vector per piece. The tool would still cite the whole page. This goes after the
largest group of misses. I have not built it yet, so I do not know how much it helps.

Second, I would give keyword search more weight in the merge. In one miss, keyword
search alone put the right page in the top five, and the merge pushed it out.

## What I learned

I picked the model because it was small and ran on my laptop. I did not check how
much text it takes in. So my scores for whole pages were partly scores for the top quarter
of each page. Next time, I will look up a model's input limit and count the word pieces
in my data before I score anything.

This comes from one report and a small set of questions. The full list of misses and
their causes is in the
[error analysis](https://github.com/Iliya-Valizadeh/bank-filings-rag/blob/main/reports/error_analysis.md).
