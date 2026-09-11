# Bug report: whisper does not fire mcontrol6 data-match (select=1) triggers on LR loads

**Date:** 2026-09-10
**Reporter:** Pierce Clark (pclark@hmc.edu)
**Component:** whisper (`/opt/riscv/bin/whisper`), Sdtrig 1.0 / mcontrol6
**Severity:** Medium — silent under-trigger; a data-watch trigger misses the load half of LR/SC
**Reference model for comparison:** Spike (fires correctly)

## Summary

An mcontrol6 trigger configured as a **data match** (`tdata1.select = 1`) with the
**load** permission (`tdata1.xsl = 0b001`) fires correctly on plain scalar loads
(`lw`, `ld`), but does **not** fire when the matching value is loaded by
`lr.w` / `lr.d`. The `lr` retires normally and no breakpoint exception is raised.

The store half is unaffected: the same trigger with the store permission fires on
`sc.w` / `sc.d`, and address matches (`select = 0`) fire on both `lr` and `sc`.
So the gap is specific to **data matching on LR**.

Per the RISC-V Debug spec, `lr` is a load: a `select=1` trigger with `load=1`
must compare the loaded value against `tdata2` and raise a breakpoint on a match.

## Environment

- whisper on PATH (`/opt/riscv/bin/whisper`)
- Configs: `config/whisper/whisper-rv64-max-spike-ref/`,
  `config/whisper/whisper-rv32-max-spike-ref/` (both already carry the `triggers`
  array with `tinfo` and `trigger_use_tcontrol: false`, so M-mode triggers do fire)
- Tests: `SdtrigSm_AExt-00`, `SdtrigS_AExt-00`, `SdtrigU_AExt-00`
  (`EXTENSIONS=SdtrigSm,SdtrigS,SdtrigU EXCLUDE_EXTENSIONS=`), coverpoint
  `cp_sdtrig_lrsc_data`

## Reproduction

```bash
make whisper-rv64-max-spike-ref EXTENSIONS=SdtrigSm,SdtrigS,SdtrigU EXCLUDE_EXTENSIONS=
```

Without the ACT makefiles, the exact whisper invocation ACT uses is:

```bash
# RV64
whisper --log --loglabel --traceload --logfile SdtrigSm_AExt-00.trace.log \
        --config config/whisper/whisper-rv64-max-spike-ref/whisper.json \
        work/whisper-rv64-max-spike-ref/elfs/priv/SdtrigSm/SdtrigSm_AExt-00.elf

# RV32
whisper --log --loglabel --traceload --logfile SdtrigSm_AExt-00.trace.log \
        --config config/whisper/whisper-rv32-max-spike-ref/whisper.json \
        work/whisper-rv32-max-spike-ref/elfs/priv/SdtrigSm/SdtrigSm_AExt-00.elf
```

(The `--log --loglabel --traceload --logfile` flags are debug-only; whisper needs
only `--config <whisper.json> <elf>` to run the test and print the pass/fail
summary.)

All three `*_AExt-00` tests fail with a trap-count mismatch:

```
RVCP: Expected trap signature byte count: 0x280   # spike: 20 breakpoints
RVCP: Actual trap signature byte count:   0x240   # whisper: 18 breakpoints
RVCP: DIAGNOSIS: DUT recorded FEWER traps (missing traps).
```

The relevant test sequence (scratch pre-seeded with the watched value):

```asm
  csrw tdata2, <dataval>              # randomized per suite; LI trims it to XLEN on RV32
  csrw tdata1, 0x6000000000200041     # mcontrol6, m=1, select=1 (data), xsl=001 (load)
  lr.d x14, (x13)                     # loads dataval -> should raise a breakpoint
  nop                                 # data matches fire AFTER: this is the reported epc
```

## Evidence

Breakpoints per instruction, RV64, `SdtrigSm_AExt-00` (spike trace vs `whisper --log`):

| instruction                               | spike  | whisper |
| ----------------------------------------- | ------ | ------- |
| `lr.w` (addr match)                       | 2      | 2       |
| `lr.d` (addr match)                       | 2      | 2       |
| `sc.w` (addr match)                       | 2      | 2       |
| `sc.d` (addr + data match)                | 4      | 4       |
| `amoswap.w` / `amoswap.d`                 | 4 / 4  | 4 / 4   |
| `nop` after `lr.d` (**data match on LR**) | 2      | **0**   |
| **total**                                 | **20** | **18**  |

RV32 is the same shape: spike 12 breakpoints, whisper 10, the two missing ones
being the `select=1` `lr.w` data matches (`0xc0` vs `0xa0` trap bytes).

Extract the whisper side with:

```bash
whisper --config config/whisper/whisper-rv64-max-spike-ref/whisper.json \
        --log --logfile /tmp/w.log \
        work/whisper-rv64-max-spike-ref/elfs/priv/SdtrigSm/SdtrigSm_AExt-00.elf
grep " c 0000000000000342 0000000000000003 " /tmp/w.log | awk '{print $5}' | sort | uniq -c
```

and the spike side from the reference trace built with `DEBUG=True`:

```bash
grep -c trap_breakpoint \
  work/whisper-rv64-max-spike-ref/build/priv/SdtrigSm/SdtrigSm_AExt-00.sig.trace
```

## Notes

`select=1` data matches on ordinary loads _do_ work — `SdtrigSm_Mcontrol6-00`
(coverpoint `cp_sdtrig_mcontrol6_load_store_data`, which exercises `lw` under the
load permission) passes against the same spike reference. Only LR is skipped.
