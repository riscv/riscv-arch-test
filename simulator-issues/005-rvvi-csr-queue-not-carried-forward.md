# Framework issue 005: rvvi CSR queue does not carry forward unchanged CSR values

## Summary

`framework/src/act/fcov/coverage/RISCV_coverage_rvvi.svh:save_rvvi_data`
contains the comment

```sv
// Todo: CSR values should use the current values and only update the changed ones
rvviData.csr = this.rvvi.csr[hart][issue];
rvviData.csr_wb = this.rvvi.csr_wb[hart][issue];
```

i.e. for every retired (non-trapping) instruction, `traceDataQ[hart][issue][0].csr[*]`
is overwritten with whatever the current RVVI signal exposes — and the RVVI
adapter (`framework/src/act/sail_to_rvvi.py`) only emits CSR fields for CSRs
that actually changed in the just-retired instruction. The result is that any
CSR not modified by the most recent instruction reads as **0** (not its true
last-written value).

## Impact on SsstrictV / vector coverage

Almost every SsstrictV "reserved encoding" cross uses `std_trap_vec`, which is

```sv
std_trap_vec : coverpoint {get_csr_val(... `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                            get_csr_val(... `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                            get_csr_val(... `SAMPLE_BEFORE, "vl", "vl") != 0 &
                            get_csr_val(... `SAMPLE_BEFORE, "mstatus", "vs") != 0}
```

The test sequence emitted by `_ssstrictv_helpers.issue_simple_test` is

```asm
vsetivli x28, 1, e8, m1, tu, mu     # sets vtype, vstart, vl
la x28, random_mask_0
vle8.v v??, (x28)                   # init vd  (writes mstatus.VS but not vtype/vl/vstart)
vle8.v v??, (x28)                   # init vs2 (writes mstatus.VS but not vtype/vl/vstart)
<TEST INSTRUCTION>                  # SAMPLE_BEFORE here reads CSRs from previous insn (vle8.v)
```

The `vle8.v` does **not** write `vtype`/`vl`/`vstart` so those CSRs are not in
the rvvi line. The traceDataQ entry for `vle8.v` therefore reports
`vtype=0, vl=0, vstart=0`. So `std_trap_vec.vl != 0` evaluates **false**, and
the cross never samples — even though the architectural state actually satisfies
all four conditions.

Concrete evidence: `cp_ssstrictv_masking_vd_eq_v0` is a single-bin cross
`{std_trap_vec, vtype_lmul_1, vd=v0, mask_enabled}` and the corresponding
encoding (`vaadd.vv v0, v16, v27, v0.t`) is recorded in
`work/sail-rv64-max/coverage/priv/SsstrictV/SsstrictV_rv64.rvvi` as

```
ORDER 241 PC 00000000800004F0 INSN 250DA057 MODE 3
    CSR 300 8000000A00007E00 CSR 342 0000000000000002 CSR 343 ... CSR 341 ...
```

— note the absence of CSR 0xC21 (`vtype`), 0xC20 (`vl`), 0x008 (`vstart`).
The covergroup reports the cross at 0%.

## Workaround applied in this repo

`generators/testgen/scripts/priv/_ssstrictv_helpers.py:issue_simple_test` and
`generators/testgen/scripts/priv/cp_ssstrictv_lmulgt1_off_group.py:_emit_one`
re-emit the `vsetivli` immediately before the test instruction so that the
RVVI line for the previous instruction (the second `vsetivli`) explicitly
carries `vtype`, `vl`, and `vstart` writes. This makes `std_trap_vec` reach
the cross. The proper fix in the framework is still recommended.

## Workaround / fix

Two complementary options:

1. **Framework**: implement the TODO at
   `framework/src/act/fcov/coverage/RISCV_coverage_rvvi.svh` —
   carry forward CSR values from `traceDataQ[hart][issue][1].csr[idx]` for
   every CSR that is NOT in the current `csr_wb` mask, the same way `x_wdata`
   already does.
2. **rvvi adapter**: make `framework/src/act/sail_to_rvvi.py` re-emit ALL CSRs
   that were ever written (or at least the small set used by the vector
   covergroups: `vtype`, `vl`, `vstart`, `mstatus`, `vcsr`, `frm`) on every
   instruction line. This is a workaround that loses the "delta only" property
   but unblocks coverage immediately.

Until either is in place, all `cp_ssstrictv_*` crosses that include
`std_trap_vec` (the majority of the templates) cannot reliably reach 100% on
Sail no matter how exhaustive the test generator is — the test programs are
already correct.

## Reproduction

```bash
cd /home/jacassidy/ssstrictV
make coverage EXTENSIONS=SsstrictV
grep -E "^ORDER .* PC 00000000800004F0 " \
     work/sail-rv64-max/coverage/priv/SsstrictV/SsstrictV_rv64.rvvi
# CSR 300 (mstatus) is present, CSR 008 (vstart), CSR C20 (vl), CSR C21 (vtype) are NOT
grep -A 6 "Cross cp_ssstrictv_masking_vd_eq_v0\b" \
     work/sail-rv64-max/reports/SsstrictV_uncovered.txt | head -7
# 0.00% — single bin <true,one,v0,enabled> ZERO
```

## Suggested upstream filing

Repository: this repo's `framework/` (the RVVI coverage shim is local).
Same issue likely affects all extensions whose coverage uses `SAMPLE_BEFORE`
on CSRs that the test instruction itself doesn't write (which is the common
case for vector coverage that conditions on "trap-eligible vtype state").
