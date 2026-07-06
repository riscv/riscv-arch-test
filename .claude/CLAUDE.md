# CLAUDE.md (local, personal — not tracked)

Shared project guidance lives in the repo-root **`AGENTS.md`**, which Claude Code
reads via the tracked `CLAUDE.md` symlink (`CLAUDE.md` → `AGENTS.md`). Do **not**
duplicate that content here. This file holds only personal / Claude-specific
harness setup. Edit project guidance in `AGENTS.md`.

@RTK.md

# OpenWolf

@.wolf/OPENWOLF.md

This project uses OpenWolf for context management. Read and follow .wolf/OPENWOLF.md every session. Check .wolf/cerebrum.md before generating code. Check .wolf/anatomy.md before reading files.

# Caveman final summary

When caveman mode active: keep caveman style during working turns (analysis, intermediate replies, tool narration), but write the final wrap-up summary — the "here's what I did" message — in normal, full English. Resume caveman next working turn.

# Claude-specific assets

- **`.claude/rules/`** — path-scoped conventions that fire when editing matching files.
- **`.claude/agents/`** — step-by-step workflows (coverpoint-developer, priv-test-developer, instruction-formatter, dut-config-creator, extension-developer).
- **`.claude/skills/`** — `/lint-fix`, `/gen-tests`, `/verify-ext`.
- **`.claude/hooks/`** — guards/formatters (block-generated-edits, enforce-uv-run, format-python, check-spdx-header, pyright-check).

When you update project facts, edit `AGENTS.md` (shared). When you update Claude
tooling above, edit the relevant `.claude/` asset.
