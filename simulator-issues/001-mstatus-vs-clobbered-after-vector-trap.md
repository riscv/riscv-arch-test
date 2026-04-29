# Issue 001 — `mstatus.VS` clobbered after vector reserved-encoding trap

## Symptom

When a vector instruction with a reserved/illegal encoding raises an
illegal-instruction exception (mcause=2) under Sail, the *next* instruction
emitted by the SsstrictV / ExceptionsVx test harness — `csrw vstart, x0` —
itself raises a second illegal-instruction trap, even though `vstart` is the
canonical *vector status* CSR and was perfectly accessible just two
instructions earlier.

The trap handler counts these pair-traps until it overruns the trap-signature
ring buffer and reports:

```
RVCP-SUMMARY: TEST FAILED - Test File "SsstrictV.S"
RVCP: Test Info: "The trap handler aborted the test before normal completion!"
RVCP: Bad Value:      0xbad0dead
RVCP: Address of instruction that trapped (XEPC): 0x800298d8
RVCP: Instruction that trapped: 0x00801073    ; csrw vstart, x0
```

## Reproduction

The trapping context (`SsstrictV_rv32.sig.elf`, before the framework
workaround):

```
80029888 <SsstrictV_vminu_vv_cg_cp_ssstrictv_masking_vd_v0_overlap_duplicate_3>:
80029888: 11c40057   vminu.vv  v0,v28,v8,v0.t   ; vd=v0 + masked: reserved
8002988c: 00000013   nop
80029890: 00801073   csrw      vstart, zero     ; <-- raises 2nd illegal-instr
```

The first instruction is reserved per Vector spec §5.3 ("when destination is
v0 and v0 is also the mask, the result is reserved"). Sail correctly raises
illegal-instruction. The handler returns to MEPC+4 (the nop), then the
`csrw vstart, x0` traps too.

## Why this is suspicious vs the spec

* RISC-V V-extension v1.0, §3.4 *Vector State*: `mstatus.VS` is updated by
  Sail to **Dirty** when a vector instruction *successfully* writes vector
  state. The spec does **not** say that an illegal-instruction trap on a
  vector instruction should *clear* `mstatus.VS`.
* Privileged spec §3.1.6: **Off → Initial/Clean/Dirty transitions** require
  an explicit `csrw mstatus`. A trap is not such a write.
* Yet observably, after a Sail illegal-instruction trap on a reserved vector
  encoding, the subsequent `csrw vstart, x0` (also a vector CSR) raises
  illegal-instruction — exactly as if `mstatus.VS == 0` (Off).

If we explicitly re-prime `mstatus.{FS,VS} = Dirty` between the trapping
test and the cleanup `csrw vstart`, the second trap disappears.

## Framework workaround (applied)

`generators/testgen/scripts/vector_testgen_common.py` (function
`writeVecTest`, ~line 2019, priv branch):

```python
if (priv):
  writeLine("nop", "# nop after possible trap")
  # The test instruction may have trapped or otherwise left mstatus.VS in a
  # state where vector CSR access (csrw vstart) is itself illegal. Restore
  # FS|VS = Dirty BEFORE touching any vector CSR so the cleanup epilog never
  # itself traps...
  vstart_scratch = ...
  writeLine(f"li x{vstart_scratch}, {(3 << 13) | (3 << 9)}", "# FS|VS = Dirty mask")
  writeLine(f"csrs mstatus, x{vstart_scratch}",              "# restore FS|VS = Dirty")
  writeLine("csrw vstart, x0", ...)
```

After this fix, `make coverage` for SsstrictV passes the sail signature run
on both rv32 and rv64.

## Affected generators

All `cp_ssstrictv_*` and `cp_exceptionsv_*` generators that funnel through
`writeVecTest(... priv=True)` (i.e., effectively the entire SsstrictV /
ExceptionsV* corpus). The fix in `writeVecTest` is sufficient for all of
them; no generator-side change is needed.

## Suggested upstream investigation

1. Confirm reproducibility on a 4-instruction microtest fed directly to
   `sail-riscv`'s C model: a `vsetivli` setting VS=Dirty, then
   `vminu.vv v0, v8, v17, v0.t`, then `csrw vstart, x0` — observe whether
   the third instruction raises illegal-instruction.
2. Inspect `model/riscv_insts_vext_*.sail` for early-exit paths that may
   overwrite `mstatus.VS` on illegal-encoding detection.
3. Cross-check against the table in priv spec §3.1.6.5 — only
   `mstatus.VS` writes by the hart should change `VS`.
