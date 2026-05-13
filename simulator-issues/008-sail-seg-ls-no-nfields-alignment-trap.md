# Issue 008: Sail seg load/store does not enforce vd/vs3 alignment to EMUL*NFIELDS

## Summary

Sail's segmented vector load/store reservation check uses
`valid_reg_group(vd, EMUL_pow)` which only enforces alignment to the
EMUL group size (`2^EMUL_pow`). It never enforces alignment to the
larger segmented register group size (`EMUL * NFIELDS`).

The consequence is that an encoding such as `vssseg2e8.v v30, (x31), x6`
with `vsetivli e8, m2` (EMUL=2, NFIELDS=2 → segmented group = 4) is
silently accepted and executed by Sail, even though `v30` is not a
multiple of 4 and the segmented vector register group `v30, v31, v32, v33`
runs past the architectural register file (no `v32`/`v33`).

## Spec reference

RISC-V Vector spec, segmented load/store section
(`v-st-ext.adoc:1849-1853`):

> ... the vector register group for each field must follow the usual
> vector register alignment constraints (e.g., when EMUL=2 and NFIELDS=4,
> each field's vector register group must start at an even vector
> register, but does not have to start at a multiple of 8 vector
> register number).

Combined with section 6.2 ("vector register grouping"):

> Using other than the lowest-numbered vector register to specify a
> vector register group is a reserved encoding.

For a segmented load/store, the destination vector register group spans
`EMUL * NFIELDS` registers and must be aligned to that size **and** must
not exceed `v31`. Any encoding that violates either condition is
_reserved_ and must raise `Illegal_Instruction`.

## How to reproduce

Trace excerpt from
`work/sail-rv64-max/coverage/priv/SsstrictV/SsstrictV_rv64_p20.rvvi`:

```
ORDER 283644 PC 000000008001F284 INSN 2A6F8F27 MODE 3 \
    CSR 300 8000000A00006680 CSR 008 0000000000000000 \
    CSR 300 8000000A00006680 CSR 008 0000000000000000
```

- `INSN 2A6F8F27` = `vssseg2e8.v v30, (x31), x6` (NFIELDS=2)
- preceding `vsetivli x28, 1, e8, m2, tu, mu` sets EMUL=2
- segmented register group spans `v30..v33`, not aligned to 4 and runs
  past `v31` → must trap with `Illegal_Instruction`
- Sail emits no `CSR 342` (mcause), no `CSR 343` (mtval), no
  `CSR 341` (mepc) — instruction silently executes

## Root cause in the model

`model/extensions/V/vext_utils_insts.sail`:

```
function valid_reg_group(r : vregidx, EMUL_pow : int) -> bool = {
  let reg_group_size = if EMUL_pow > 0 then 2 ^ EMUL_pow else 1;
  unsigned(vregidx_bits(r)) % reg_group_size == 0
}

function valid_segment(nf : nfields, EMUL_pow : int) -> bool = {
  if EMUL_pow < 0 then nf / (2 ^ (0 - EMUL_pow)) <= 8
  else nf * 2 ^ EMUL_pow <= 8
}
```

Neither `valid_reg_group` nor `valid_segment` consider the combined
segmented group size when checking alignment / overflow of `vd` (load)
or `vs3` (store).

## Affected coverpoints

- `cp_ssstrictv_ls_seg_vd_overflow_emulgt1` — 144 ZERO bins across all
  segment loads (`vlseg`, `vlsseg`, `vluxseg`, `vloxseg`) and all
  segment stores (`vsseg`, `vssseg`, `vsuxseg`, `vsoxseg`) when
  `EMUL > 1` and `vd + EMUL*NFIELDS > 32` but `vd % EMUL == 0`.

## Workaround

The cross is added to
`generators/testgen/scripts/ssstrictv_skip_combinations.py` for every
segment LS instruction so the priv testgen does not emit it; the
covergroup template still defines the cross for documentation but no
test triggers it. When Sail adds the missing
`if EMUL_pow >= 0 & not(valid_reg_group(vd, EMUL_pow + nfields_pow))
then return Illegal_Instruction()` check (or equivalent), remove the
SKIP entries and regenerate.
