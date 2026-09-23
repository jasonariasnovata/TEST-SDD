# TEST-SDD

Sandbox for testing the Spec Driven Development (SDD) flow against SDLC controls.
Not production. No customer or production data.

## What this repo demonstrates

| SDD step | Control in this repo |
|---|---|
| Gate 1: spec.md PR | PR containing only `specs/<feature>/spec.md`; CODEOWNERS on `specs/` |
| Gate 2: plan.md PR | PR containing only `specs/<feature>/plan.md` (required for medium/high risk) |
| Implementation PR | `sdd-gate-check` CI: must link a **merged** gate PR, a Jira key, a risk class and a runnable verification command |
| AI first-pass review | GitHub Copilot code review, guided by `.github/copilot-instructions.md` |
| Human approval | Slack notification with summary + deep link; human approves **in GitHub** under their own identity |
| Standards | `.specify/memory/constitution.md` |

## Flow

1. Open a PR with `specs/<feature>/spec.md` only -> review -> merge (Gate 1).
2. Medium/high risk: open a PR with `specs/<feature>/plan.md` only -> review -> merge (Gate 2).
3. Open the implementation PR using the PR template, linking the merged gate PR.
4. CI runs tests + `sdd-gate-check`; Copilot reviews; Slack posts a summary with a link.
5. Human approves in GitHub and merges.

## Known gaps (solo test)

- Approver != author cannot be demonstrated with one GitHub account. GitHub blocks self-approval.
- Slack is notify-only; approval happens in GitHub.
