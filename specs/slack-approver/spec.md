# Spec: slack-approver

Jira: SDD-4
Risk class: high
Risk evidence: new approval path for merges (a change-control mechanism); slack_approver/ is CODEOWNERS-protected.

## Problem
Low-risk PR reviewers must open GitHub to review and approve, adding steps to small reviews.

## User stories (prioritised)
1. As a qualified reviewer, I can read a low-risk PR's full diff in Slack and approve it there, recorded under my own GitHub account.

## Requirements (numbered, testable)
- R1. Approve is available only inside the diff view, and only when the whole diff is shown.
- R2. The approval is a GitHub review by the approver's own account, pinned to the commit shown.
- R3. Refused when the approver authored the PR or any commit, or ran the agent (Requested-by trailer).
- R4. Refused for agent PRs with no Requested-by record.
- R5. Refused for medium or high risk, closed PRs, other repos, or a head commit that changed.
- R6. Every link, view and approve attempt is logged with outcome and reason.

## Out of scope
Reviewer qualification (GitHub team check) and hosting; tracked as gaps in the proposal.

## Open questions
None.
