# Spec: greet-collapse-whitespace

Jira: SDD-3
Risk class: low
Risk evidence: src/app/greeting.py only; no auth, data or dependency changes.

## Problem
Names typed with repeated spaces keep them in the greeting: "ada   lovelace" becomes "Hello, Ada   Lovelace!".

## User stories (prioritised)
1. As a user, I am greeted with single spaces between the parts of my name.

## Requirements (numbered, testable)
- R1. `greet("ada   lovelace")` returns `"Hello, Ada Lovelace!"`.
- R2. Tabs between name parts are treated as a single space.
- R3. Existing behaviour is unchanged: title case, and empty or whitespace-only names raise `ValueError`.

## Out of scope
Localisation and non-Latin casing rules.

## Open questions
None.
