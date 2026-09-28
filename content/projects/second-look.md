---
title: second-look, for everyone | Iliya Valizadeh
description: second-look reads a bank or card statement in your browser and points out charges worth a second look. Nothing is uploaded. So far it has been tested on synthetic statements only.
synthetic_only: yes
---
<!-- slot: lede -->
A free tool that reads your bank or card statement and points out charges you may want
to check again. It runs inside your browser, and your statement is never uploaded.

<!-- slot: main -->
## What it does

You save a statement from your bank's website as a CSV file. You open second-look and
pick the file. You tell it which column holds the date, the description and the
amount. Then it lists charges worth a second look:

- a charge that repeats, like a subscription
- a subscription whose price went up
- two charges that may be the same thing charged twice
- a charge that looks unusual for you

Each flag comes with one plain sentence that says why. The tool cannot tell whether a
charge is right or wrong. Only you, the shop or your bank can. It is not financial
advice.

## Is my statement safe?

The whole tool runs inside the web page, on your own device. Your statement is not
sent anywhere. The page blocks requests to other web addresses, and an automatic test
checks one full run for any request that should not be there.

## How well does it work?

The honest answer first: it did not pass the bar I set for it before I saw any
results. Its first test run failed several checks. After two fixes, two checks still
fall short.

- Repeating charges: on synthetic statements,
  {{ second_look.recurring_precision_share }} of its flags were right. It needed
  {{ second_look.recurring_precision_bar }} on the same synthetic test.
- Unusual charges: on synthetic statements, {{ second_look.unusual_precision }} of its
  flags were right (a {{ second_look.interval_level }} confidence range of
  {{ second_look.unusual_precision_lo }} to {{ second_look.unusual_precision_hi }}). It
  needed {{ second_look.unusual_precision_bar }} on the same synthetic test. So more
  than half of these flags were wrong. One fix already raised this share from
  {{ second_look.first_run_unusual_precision }} on the first synthetic run.

The share of right flags is called
[precision](https://github.com/Iliya-Valizadeh/second-look/blob/main/docs/glossary.md#precision).
The share of real events it finds is called
[recall](https://github.com/Iliya-Valizadeh/second-look/blob/main/docs/glossary.md#recall).

It finds most repeating charges. On synthetic statements it found
{{ second_look.recurring_recall }} of the planted repeating charges (a
{{ second_look.interval_level }} confidence range of
{{ second_look.recurring_recall_lo }} to {{ second_look.recurring_recall_hi }}). A
simple method that only groups charges with the same shop and amount found
{{ second_look.baseline_recurring_recall }} on the same synthetic statements. This is
probably the easiest kind of charge to find, because the script plants these charges
at regular gaps on purpose.

## What "synthetic" means here

A script made up every test statement and planted the charges for the tool to find.
No real bank statement was used. I wrote both the script and the rules, so the test
may suit the rules. When the synthetic statements get a little more delay and noise,
the share of repeating charges it finds falls from {{ second_look.recurring_recall }}
to {{ second_look.stress_recurring_recall }} on that harder synthetic set. So these
results do not show how well it works on your statement.

<!-- slot: weak -->
- It has been tested on synthetic statements only. There is no result on real
  statements yet.
- Two of its checks are below the bar I set in advance, as shown above.
- It misses some things without saying so. Bills whose amount changes each month,
  like electricity, are almost never found: on synthetic statements it found
  {{ second_look.varying_bill_recall }} of them.
- If you choose the wrong sign for amounts, every charge is read as money coming in.
  The tool then says there is nothing to check, with no warning. Check one purchase
  you know first.
- The page was tested in one browser only, and no one has tested it with real users
  yet.

The full list is in
[docs/whats_weak.md](https://github.com/Iliya-Valizadeh/second-look/blob/main/docs/whats_weak.md).

<!-- slot: next -->
## Try it

Open [second-look](https://iliya-valizadeh.github.io/second-look/) and choose a CSV
file from your bank. Nothing is uploaded. If
your bank's columns are hard to match, this
[short guide](https://github.com/Iliya-Valizadeh/second-look/blob/main/docs/how-to/map-a-banks-csv-columns.md)
can help.
