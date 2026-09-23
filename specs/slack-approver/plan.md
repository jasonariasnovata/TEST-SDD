# Plan: slack-approver

Spec: specs/slack-approver/spec.md

## Verification (first, not last)
```bash
python -m py_compile slack_approver/app.py slack_approver/open_agent_pr.py
```
Plus end-to-end in the sandbox: agent PR approved by a non-requester; requester, author and commit author refused.

## Approach
Bolt (Python) app over Socket Mode. GitHub App user tokens via device flow, so reviews post as the human.
Card posted by the slack-review-notify workflow; the app handles "View diff & approve".

## Alternatives considered
- Approve in GitHub only (kept for medium/high risk).
- Shared token approving on a person's behalf: rejected, it would misattribute approvals.

## Files / modules touched
slack_approver/ (new), .gitignore.

## New dependencies (justify each, or "none")
slack-bolt, requests, python-dotenv, PyJWT[crypto]: Slack app framework, HTTP, local config, GitHub App JWT.

## Constitution check
No secrets in repo (1Password references at runtime). Auth enforced on every action. Tests: refusal rules unit-tested.

## PR breakdown (vertical slices)
One PR: slack_approver/ and .gitignore.
