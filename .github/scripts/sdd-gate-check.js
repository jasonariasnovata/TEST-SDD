// Enforces the SDD gates on a pull request.
// Instruction files (AI prompts, standards, CI and ownership rules) must change in a PR of their own,
// so an agent cannot rewrite its own rules alongside the code those rules judge.
// Agent (bot) PRs must record who ran the agent in a "Requested-by:" commit trailer.
// Gate PRs (only specs/** or .specify/bugs/** files) need a Jira key.
// Implementation PRs must link a merged gate PR whose artefact matches the risk class,
// and carry a runnable verification command.
const ARTEFACT_PATH = /^(specs\/|\.specify\/bugs\/)/;
const INSTRUCTION_PATH = /^(\.github\/|\.specify\/(memory|templates)\/|\.claude\/|AGENTS\.md$|CLAUDE\.md$)|(^|\/)(SKILL\.md|[^/]+\.instructions\.md)$/;
const REQUESTED_BY = /^Requested-by:\s*@?[A-Za-z0-9-]+\s*$/m;
const JIRA_KEY = /^Jira:\s*([A-Z][A-Z0-9]+-\d+)\s*$/m;
const LINKED_PR = /^Approved artifact PR:\s*#(\d+)\s*$/m;
const RISK = /^Risk class:\s*(low|medium|high)\s*$/im;
const VERIFICATION = /##\s*Verification[\s\S]*?```[a-z]*\n\s*\S[\s\S]*?```/i;

module.exports = async ({ github, context, core }) => {
  const { owner, repo } = context.repo;
  const pr = context.payload.pull_request;
  const body = pr.body || '';
  const failures = [];

  const files = await github.paginate(github.rest.pulls.listFiles, {
    owner, repo, pull_number: pr.number, per_page: 100,
  });
  const paths = files.map((f) => f.filename);
  const isGatePr = paths.length > 0 && paths.every((p) => ARTEFACT_PATH.test(p));
  const instructionPaths = paths.filter((p) => INSTRUCTION_PATH.test(p));
  const isInstructionPr = paths.length > 0 && instructionPaths.length === paths.length;

  if (!JIRA_KEY.test(body)) failures.push('Missing "Jira: <KEY-123>" line.');

  if (instructionPaths.length && !isInstructionPr) {
    failures.push(`Instruction files must change in their own PR: ${instructionPaths.join(', ')}`);
  }

  if (pr.user?.type === 'Bot') {
    const commits = await github.paginate(github.rest.pulls.listCommits, {
      owner, repo, pull_number: pr.number, per_page: 100,
    });
    if (!commits.some((c) => REQUESTED_BY.test(c.commit.message))) {
      failures.push('Agent PR has no "Requested-by:" commit trailer naming who ran the agent.');
    }
  }

  if (isInstructionPr) {
    core.notice(`Instruction-only PR (needs CODEOWNERS review): ${paths.join(', ')}`);
  } else if (isGatePr) {
    core.notice(`Gate PR: ${paths.join(', ')}`);
  } else {
    const risk = (body.match(RISK) || [])[1]?.toLowerCase();
    if (!risk) failures.push('Missing "Risk class: low|medium|high" line.');

    const linked = (body.match(LINKED_PR) || [])[1];
    if (!linked) {
      failures.push('Missing "Approved artifact PR: #<number>" line.');
    } else {
      const { data: gate } = await github.rest.pulls.get({ owner, repo, pull_number: Number(linked) });
      if (!gate.merged) failures.push(`Linked PR #${linked} is not merged.`);
      const gateFiles = (await github.paginate(github.rest.pulls.listFiles, {
        owner, repo, pull_number: gate.number, per_page: 100,
      })).map((f) => f.filename);
      const hasSpec = gateFiles.some((p) => /^specs\/.+\/spec\.md$/.test(p));
      const hasPlan = gateFiles.some((p) => /^specs\/.+\/plan\.md$/.test(p));
      const hasAssessment = gateFiles.some((p) => /^\.specify\/bugs\/.+\/assessment\.md$/.test(p));
      if (risk === 'low' && !(hasSpec || hasPlan || hasAssessment)) {
        failures.push(`Linked PR #${linked} carries no spec.md, plan.md or assessment.md.`);
      }
      if ((risk === 'medium' || risk === 'high') && !(hasPlan || hasAssessment)) {
        failures.push(`Risk class ${risk} needs a merged plan.md (or assessment.md) gate; #${linked} has none.`);
      }
    }

    const touchesAuth = paths.some((p) => p.startsWith('src/auth/'));
    if (touchesAuth && risk === 'low') {
      failures.push('Change touches src/auth/ (high-risk path) but is marked low risk.');
    }

    if (!VERIFICATION.test(body)) {
      failures.push('"## Verification" section must contain a fenced, runnable command.');
    }
  }

  if (failures.length) core.setFailed(failures.join('\n'));
  else core.notice('SDD gate check passed.');
};
