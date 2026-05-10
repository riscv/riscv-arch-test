# Sail vs Spike Mismatches

Tracks reference-model disagreements between Spike and Sail that surface when
running `make spike` against the generated tests in this repo. These tests
are still **emitted** by the generator; the mismatch is a downstream
ref-model bug, not a generator bug.

## cp_vill on whole-register move instructions

Affected coverpoint: `cp_vill`
Affected instructions: `vmv1r.v`, `vmv2r.v`, `vmv4r.v`, `vmv8r.v`

### Symptom

After installing an illegal vtype (vill=1) via
`li xN, -1; vsetvl x{scratch}, x0, xN`, executing one of the
`vmv<nr>r.v` instructions:

* **Spike**: raises an illegal-instruction exception (correct per
  RISC-V V-extension spec §16.6, which states whole-register moves still
  observe `vill`).
* **Sail (sail-riscv)**: silently executes the move and does **not** trap.

This produces an `mepc` mismatch in the generated cp_vill signature
section — Spike reports the trap-vector PC for the move, Sail reports
the address after it.

Example diagnostic (rv64-max, ExceptionsVx):

```
RVCP: Test Info: "Mismatch in mepc value! Trap was being handled in M-Mode."
RVCP: Instruction that trapped: 0x9f103357   # vmv1r.v v6, v17
```

### Root cause

Sail does not perform the `vill` check for the `vmv<nr>r.v` family. Per
V-spec §16.6: "These instructions ... are still subject to the rules
related to vill." Spike implements this; Sail does not.

### Status

* Generator emits the cp_vill tests as designed (proper vsetvl-from-register
  trigger; no fractional-LMUL hack).
* `make spike` is expected to FAIL on these specific tests until Sail is
  patched. All other `cp_vill` cases (and all non-`cp_vill` priv tests) pass.
* No skip is committed. Add a temporary `if instruction in ("vmv1r.v",
  "vmv2r.v", "vmv4r.v", "vmv8r.v"): return` near the top of `make_vill`
  in `generators/testgen/scripts/vector-testgen-priv.py` if you need
  `make spike` to be green locally.

### Related issues

* Earlier `cp_vstart` / `cp_vstart_gt_vl` mismatches are tracked under
  acted issue #1445 and sail-riscv issue #1104. The new `cp_vill` mismatch
  is in the same family of "Sail skips a vtype-state check the spec
  mandates".
