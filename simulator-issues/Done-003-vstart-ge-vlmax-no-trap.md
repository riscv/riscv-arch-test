# Issue 003 — Sail does not raise illegal-instruction for `vstart >= VLMAX`

## Symptom

The coverpoint `cp_ssstrictv_vstart_ge_vlmax` reads:

```sv
// generators/coverage/src/covergroupgen/templates/vector/priv/cp_ssstrictv_vstart_ge_vlmax.sv
vstart_ge_vlmax: coverpoint (get_csr_val(..., `SAMPLE_BEFORE, "vstart", "vstart") >=
                             get_vtype_vlmax(..., `SAMPLE_BEFORE)) {
    bins true = {1'b1};
}
trap_occurred_8f65a1: coverpoint (get_csr_val(..., `SAMPLE_AFTER, "mcause", "int") == 2) {
    bins trapped = {1'b1};
}
cp_ssstrictv_vstart_ge_vlmax: cross vstart_ge_vlmax, vtype_valid_8f65a1, trap_occurred_8f65a1;
```

The generator `cp_ssstrictv_vstart_ge_vlmax.py` emits one test per relevant
instruction with `vstart = 2048` (large), valid vtype, then the test
instruction. Coverage stays **0.00 %** — the trap_occurred slot of the cross
is never hit.

## Why this is consistent with the spec but not with our cross

RISC-V V-extension v1.0, §3.6 *Vector Start Index CSR (`vstart`)*:

> Implementations are *permitted* to raise illegal-instruction exceptions
> when attempting to execute a vector instruction with values of `vstart`
> that the implementation can never produce when executing that same
> instruction with the same `vtype` setting.

i.e., trapping is **optional**. Sail chooses *not* to trap; instead it
performs the instruction with all elements skipped (vector-state
unchanged). This is fully spec-compliant.

Therefore the cross can never be reached on Sail.

## Reproduction (theoretical microtest)

```asm
vsetivli x0, 1, e8, m1, tu, mu     ; VLMAX = VLEN/8
li       t0, 2048
csrw     vstart, t0                  ; vstart >= VLMAX
vadd.vv  v1, v2, v3                 ; should trap per generator's intent
```

Sail executes `vadd.vv` without raising an illegal-instruction trap;
`mcause` remains at whatever it was previously.

## Workaround

The coverpoint is **skipped from generator emission**. The
`cp_ssstrictv_vstart_ge_vlmax.py` generator is gated by an early `return`
on this entry — see `_ssstrictv_helpers.SKIP_COVERPOINTS`.

## Possible upstream changes that would close this gap

* Add an opt-in `--strict-vstart` model option in `sail-riscv` that raises
  illegal-instruction whenever `vstart > vl`.
* Or, change the SsstrictV template to make the trap slot optional
  (e.g., `cross … iff (trap_occurred)` is not valid SystemVerilog; we'd
  have to split the cross into "trap" and "executed" variants and accept
  whichever Sail produces).

## Affected templates / generators

* `generators/coverage/src/covergroupgen/templates/vector/priv/cp_ssstrictv_vstart_ge_vlmax.sv`
* `generators/testgen/scripts/priv/cp_ssstrictv_vstart_ge_vlmax.py`
