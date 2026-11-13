#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Claude Code PreToolUse hook: the first `gh pr create` at each commit is blocked with a reminder to run
# /actbot and address its findings. A second attempt at the same commit goes through.
input=$(cat)
case "$input" in
*"gh pr create"*) ;;
*) exit 0 ;;
esac
head=$(git rev-parse HEAD 2>/dev/null) || exit 0
marker="$(git rev-parse --git-dir)/actbot-reminded-$head"
[ -e "$marker" ] && exit 0
touch "$marker"
echo "Before opening a PR, run the ACTBot review (/actbot, or docs/ACTBot.md) on this branch and address its findings. Then run gh pr create again." >&2
exit 2
