# ACTBot: static review of ACT changes

ACTBot is a review procedure that any AI agent (or person) can follow to review a riscv-arch-test change before it is
opened as a PR, or to review an existing PR. It checks the change against the rules in
[ReviewRules.md](ReviewRules.md). It only reads: CI builds and runs every simulator, so ACTBot never runs `make`,
simulators, `run_tests.py` or coverage, never modifies files, and never commits, pushes or posts to GitHub.

## Running it

- Claude Code: `/actbot` reviews the current branch; `/actbot <N>` reviews PR N. Both run the `actbot` agent in its
  own context and return the report.
- Other agents: follow the procedure below. If your tool can start a subagent or a fresh session, run the review
  there, so the reviewer does not share the context of whoever wrote the change. Otherwise run it in place.
- Then fix each finding that holds up. Drop a finding only if it is wrong, and be ready to say why.

Review quality matters more than speed. ACTBot is a full code review plus ACT-specific checks, not a checklist: the
rules and the related-work step add to an ordinary correctness review and never replace it. Follow each lead as far as
it needs to go to confirm or drop a finding, including into unchanged code the change calls or relies on.

## Procedure

### 1. Get the change

- Act4 reference: use whichever of `upstream/act4`, `origin/act4` or `act4` exists and points at
  riscv/riscv-arch-test. If none does, run
  `git fetch https://github.com/riscv/riscv-arch-test act4:refs/remotes/upstream/act4`.
- Current branch: find the base with `git merge-base HEAD <act4 ref>`, then review `git diff <base>` (committed and
  uncommitted changes) and `git log <base>..HEAD`.
- PR N: with the GitHub CLI, `gh pr view N -R riscv/riscv-arch-test --json title,body,baseRefName,commits,files`,
  `gh pr diff N -R riscv/riscv-arch-test`, and the discussion with `gh pr view N -R riscv/riscv-arch-test --comments`
  and `gh api repos/riscv/riscv-arch-test/pulls/N/comments`. Without `gh`, fetch the head with
  `git fetch https://github.com/riscv/riscv-arch-test pull/N/head:refs/remotes/prs/N` and review its diff against
  the act4 reference; say in the report that the PR discussion was not read.

### 2. Decide what applies

Read [ReviewRules.md](ReviewRules.md) as it is on the act4 reference (`git show <act4 ref>:docs/ReviewRules.md`), so a
change that edits the rules is reviewed against the current ones; if act4 doesn't have the file yet, read the working
tree's. Classify the changed files; each class needs at least these sections, and any other rule that fits applies too:

- docs, README, AGENTS.md: sections 1-2;
- CI workflows, `config/`: sections 1-2 and the config rules in 6;
- framework (`framework/`, `run_tests.py`, `tests/env`): sections 1-3;
- generators, testplans, templates: sections 1-4, and 6 for spec claims;
- coverpoints and `coverpoints/norm/`: sections 1-2, 5 and 6.

For generated files under `tests/` and `coverpoints/`, check that they changed along with their generator, and read
enough of them to confirm the generator does what it claims, including the edge cases below.

### 3. Review

First review the change as you would any code change, for correctness. Read each changed hunk with the code it calls
and the code that calls it, and ask:

- Is the logic right? Look for wrong conditions, off-by-one ranges, wrong signs or widths, and RV32/RV64, E,
  misaligned, illegal-encoding or privilege-mode cases it handles wrongly or not at all.
- Does each test exercise what it claims, and could it pass without doing so (a check that can't fail, a value that is
  never compared, a trap that skips the instruction under test, a gate that is never true)?
- Does each coverpoint hit the bins it should, and can a bin be hit by the wrong instruction or state?
- Can it be made significantly simpler? Look for a function, layer or mechanism that can go; logic that repeats
  across functions or reimplements an existing helper; general machinery with only one use; dead code and unused
  options; and tests or probes beyond what the coverpoints need. Sketch the simpler version.
- Is the reading of the spec right? Look it up when the change depends on it; if no riscv-isa-manual checkout is at
  hand, read the adoc from github.com/riscv/riscv-isa-manual.

Then apply the rules from step 2, and check the change against the layers it must agree with: testplan, coverpoints,
generator, generated test, normative mapping, CTP, configs.

Verify every candidate finding before reporting it, by quoting the code, the spec, or a generated test that shows it.
Before calling behavior wrong, check that the spec doesn't allow it. Drop what you can't verify, or ask it as a
question.

### 4. Related work

The change has to fit with act4 as it is now and with the other open PRs.

- Act4 since the base: `git log <base>..<act4 ref> -- <changed files>` and the suites they belong to. Look for merged
  changes that make part of the change stale (an exclusion whose cause was fixed, a renamed helper or API, a moved
  coverpoint) or that conflict with it. `git merge-tree --write-tree <act4 ref> HEAD` (or the PR head) shows textual
  conflicts.
- Open PRs: `gh pr list -R riscv/riscv-arch-test --state open --limit 300 --json number,title,files`, keeping those
  that touch the same files or suites. For each, read its diff of the shared files and decide whether it duplicates
  this change, conflicts with it, or must merge first. Ignore overlaps that are only adjacent edits. Without `gh`,
  skip this and say so in the report.
- Earlier review: a point already raised in the PR's discussion and not yet addressed goes under "Still open from
  review" as one line with a link, not as a new finding. A thread marked resolved is not necessarily fixed; check the
  code. On a PR updated since a review, look hardest at the commits added after it.

### 5. Report

Return only the report:

- one line saying what was reviewed (PR number, or branch and head SHA), and any step skipped for lack of a tool;
- findings grouped under **Blocking**, **Should fix** and **Minor**, each with `file:line`, what is wrong, the rule or
  spec text it rests on, and a concrete fix (a `suggestion` block when the fix is mechanical); mark a finding that
  applies in several places "Global" and list the places;
- **Related PRs**: duplicates, conflicts and merge-order dependencies, one line each, if any;
- **Still open from review**, if any;
- **Questions**, if any;
- "No findings." when there are none.

The report holds findings and questions only. Don't list or summarize checks that passed, and don't pad it. Write
each finding plainly and briefly, but report every finding you verified: brevity is about wording, not about how many
findings to report.
