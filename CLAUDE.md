# CLAUDE.md

## Rules

- Update the relevant guide immediately when corrected or when you learn something new.
- Verify work before marking complete (run tests, check logs).
- Read the guide for a task before reading raw code.
- **NEVER use Agent with `subagent_type=Explore`** unless the user explicitly gives permission. Direct Grep/Glob/Read is fine.
- **Context refresh between problems**: When switching from one problem/coverpoint to another, STOP. Re-read the relevant guide files from the Task Routing table below. Then summarize your current context: what was just completed, what you're starting next, and what the current state is. This is where context drift happens — prevent it by resetting at every transition.

## Task Routing

| Task                                   | Read                                                                                           |
| -------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Fix coverage holes                     | `generators/testgen/scripts/custom/CLAUDE-coverage-workflow.md`                                |
| Write/edit CSV cells                   | `guides/csv-editing.md`                                                                        |
| Write/fix cp*custom*\*.py script       | `generators/testgen/scripts/custom/GUIDE.md`                                                   |
| Look up vector encodings/FP hex values | `guides/vector-reference.md` (grep, don't read whole file)                                     |
| Project structure, build commands      | `guides/architecture.md`                                                                       |
| Debug a hanging test                   | `guides/debugging-hangs.md`                                                                    |
| Known pitfalls and bugs                | `generators/testgen/scripts/custom/claude-scripts/knowledge.md`                                |
| Fix/edit coverpoint templates          | `generators/coverage/src/covergroupgen/templates/` (scalar) and `…/templates/vector/` (vector) |
| Simulator bugs / unsupported tests     | `simulator-issues.md` (repo root)                                                              |
