---
name: lint-fix
description: Run ruff and pyright linting, auto-fix what's possible, and report remaining issues. Use before committing or creating PRs.
user-invocable: true
argument-hint: "[optional: path to specific file]"
---

# Lint and Fix

Run the project linters and fix what can be auto-fixed.

## Steps

1. Run `make format` to auto-format with ruff
2. Run `make lint-fix` to auto-fix lint issues
3. Run `make lint` to check for remaining issues
4. If there are remaining issues, fix them manually
5. If a specific file was provided ($ARGUMENTS), focus on that file first

Always use `uv run` prefix when running Python tools directly.
Report a summary of what was fixed and what remains.
