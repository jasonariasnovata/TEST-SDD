# Constitution

Non-negotiable criteria that must hold after every change, whoever or whatever makes it.

1. No secrets, tokens or credentials in code, config, logs or test fixtures.
2. No customer or production data in this repository.
3. Every endpoint or function that exposes data enforces authentication and authorisation.
4. No new third-party dependency without it being named and justified in plan.md.
5. Every behaviour change has a test that asserts the actual requirement, not just "no error".
6. Code under `src/auth/` is high risk: it needs a merged plan.md and a CODEOWNERS review.
7. Implementation matches the approved spec.md/plan.md; deviations are called out in the PR.
