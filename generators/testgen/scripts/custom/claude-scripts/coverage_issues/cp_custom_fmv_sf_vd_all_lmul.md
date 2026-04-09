# cp_custom_fmv_sf_vd_all_lmul — Hang on VfCustom64

## Status

Build hangs on VfCustom64-vfmv.s.f (rv32). Likely an illegal instruction causing a trap loop.

## Diagnosis Needed

Follow `guides/debugging-hangs.md`: find the ELF, run with `--inst-limit 50000 --trace-instr`, identify the hanging instruction. Since this is VfCustom64 on rv32, likely SEW=64 FP on a system without D extension causes illegal instruction.
