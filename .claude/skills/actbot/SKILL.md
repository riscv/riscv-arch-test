---
name: actbot
description: Static review of a riscv-arch-test change following docs/ACTBot.md, run in the actbot agent. Use before opening or updating a PR, or when asked to review an ACT PR. Does not build or simulate; CI does that.
argument-hint: "[PR number, or empty for the current branch]"
context: fork
agent: actbot
---

Review this riscv-arch-test change: $ARGUMENTS

If that is a PR number, review that PR. If it is empty, review the current branch against act4, including uncommitted
changes. Follow `docs/ACTBot.md` and `docs/ReviewRules.md`, and return only the report.
