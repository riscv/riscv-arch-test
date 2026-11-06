#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Mutation check: for each mutant matching a prefix, regenerate its suite with the wrong semantics and run
# it on one configuration (a correct model). Every mutant must make at least one test fail.
# Usage: tests_ai/run_mutants.sh <mutant-prefix> <config-dir>   e.g. tests_ai/run_mutants.sh h_csr: config/sail/sail-rv64-max
# Environment: AI_MUT_SUITE (default Mut), AI_WORKDIR as for run_ai.sh.
set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
prefix=$1
cfg=$2
suite=${AI_MUT_SUITE:-Mut}
export AI_MUT_SUITE=$suite
survivors=()
for m in $(python3 "$root/tests_ai/gen/mutate.py" --list | grep "^$prefix"); do
  python3 "$root/tests_ai/gen/mutate.py" "$m" >/dev/null
  out=$("$root/tests_ai/run_ai.sh" "$suite" "$cfg" 2>&1)
  if grep -q "FAIL " <<<"$out"; then
    echo "caught   $m: $(grep -c 'FAIL ' <<<"$out") failing test(s)"
  else
    echo "SURVIVED $m"
    survivors+=("$m")
  fi
done
rm -rf "${root:?}/tests_ai/$suite"
[ ${#survivors[@]} -eq 0 ] || { echo "survivors: ${survivors[*]}"; exit 1; }
