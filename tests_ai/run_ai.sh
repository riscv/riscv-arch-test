#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Build and run tests_ai suites on one or more ACT configurations.
#
# Usage: tests_ai/run_ai.sh <Suite[,Suite...]> <config-dir>...
#   e.g. tests_ai/run_ai.sh M,Sstc config/sail/sail-rv64-max config/spike/spike-rv32-max
# Environment: DEBUG=1 adds objdumps and simulator traces; AI_WORKDIR overrides the work dir;
#   AI_ONLY="glob ..." builds only the tests whose file names (without .S) match one of the globs;
#   AI_JOBS=N limits the parallel build and run jobs (default: all CPUs).
#
# The tests are generated, not committed: the script first runs `make tests-ai`, which regenerates
# tests_ai/<Suite>/*.S from tests_ai/gen when a generator or helper has changed.
# act discovers tests under <test-dir>/*/<Suite>/*.S and includes <test-dir>/env, so the
# script builds a staging test dir with symlinks to tests/env and tests_ai.
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
make -C "$root" -s tests-ai
suites=$1
shift
work=${AI_WORKDIR:-$root/work/tests_ai}
stage=$work/testroot
mkdir -p "$stage"
ln -sfn "$root/tests/env" "$stage/env"
if [ -n "${AI_ONLY:-}" ]; then
  rm -rf "$stage/ai"
  mkdir -p "$stage/ai"
  ln -sfn "$root/tests_ai/common" "$stage/ai/common"
  for s in ${suites//,/ }; do
    mkdir -p "$stage/ai/$s"
    for f in "$root/tests_ai/$s"/*.S; do
      b=$(basename "$f" .S)
      for g in $AI_ONLY; do
        # shellcheck disable=SC2053
        if [[ $b == $g ]]; then
          ln -sfn "$f" "$stage/ai/$s/$b.S"
          break
        fi
      done
    done
  done
else
  rm -rf "$stage/ai"
  ln -sfn "$root/tests_ai" "$stage/ai"
fi

for d in "$@"; do rm -rf "$work/$(basename "${d%/}")/elfs/ai"; done

cfgs=()
for d in "$@"; do cfgs+=("$root/${d%/}/test_config.yaml"); done

cd "$root"
uv run act "${cfgs[@]}" --test-dir "$stage" --workdir "$work" --extensions "$suites" \
  ${DEBUG:+--debug} ${AI_JOBS:+--jobs "$AI_JOBS"} --keep-going || true

rc=0
for d in "$@"; do
  name=$(basename "${d%/}")
  [ -d "$work/$name/elfs" ] || {
    echo "no ELFs for $name"
    rc=1
    continue
  }
  ./run_tests.py ${DEBUG:+--debug} ${AI_JOBS:+--jobs "$AI_JOBS"} "$(cat "$root/${d%/}/run_cmd.txt")" "$work/$name/elfs" || rc=1
done
exit $rc
