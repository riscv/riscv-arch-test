# Status

Working on Task 1. No open questions — proceeding under the explicit rule
in instructions.md: "the instruction is not required to trap to exercise
the reserved behaviour, the coverpoint should simply reflect what is
required to exercise the reserved behaviour".

## Plan

1. Strip `trap_occurred*` / `mcause` constraints from priv ssstrictv
   templates. Keep `std_trap_vec` (it's just trap-eligible pre-state, not
   a post-condition).
2. Implement remaining missing generators using `issue_simple_test`.
3. Iterate `make tests vector-tests && make coverage`.
4. Once SsstrictV is at/near 100% on sail, start Task 2 (MissalignedV).
   For naming I'll use `cp_missalignedv_*` (rename) — easy to revert if
   you prefer otherwise.
