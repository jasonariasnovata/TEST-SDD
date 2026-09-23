# Spec: greet-title-case

Jira: SDD-1
Risk class: low
Risk evidence: src/app/greeting.py only; no auth, data or dependency changes.

## Problem
Greetings echo names exactly as typed, so "ada lovelace" is greeted in lower case.

## User stories (prioritised)
1. As a user, I am greeted with my name in title case.

## Requirements (numbered, testable)
- R1. `greet("ada lovelace")` returns `"Hello, Ada Lovelace!"`.
- R2. Empty or whitespace-only names still raise `ValueError`.

## Out of scope
Localisation and non-Latin casing rules.

## Open questions
None.
