# UDB feature extractor

Detects which ratified unprivileged and privileged extensions a hart implements and prints the result as the
`implemented_extensions` section of a [UDB](https://github.com/riscv-software-src/riscv-unified-db)
configuration, ready to seed a `config/cores/<vendor>/<core>/<core>.yaml`.

Adapted by David Harris from the original by Jayant Malvi
([riscv-arch-test #1655](https://github.com/riscv/riscv-arch-test/pull/1655)), with assistance
from Claude.

## How it works

Every extension in `extensions.h` is detected the same way: the program executes one instruction
(or CSR access) that only that extension makes legal and checks whether it traps. The trap
handler in `start.S` returns to the probe when the instruction traps, so a trap means "absent" and
retiring means "present". This relies on the hart raising an illegal-instruction exception for
encodings it does not implement, which the Ssstrict extension guarantees; on a hart without
Ssstrict an unimplemented encoding may do anything, and the result is not trustworthy.

Some extensions are derived rather than probed: umbrella names such as A, B, C, Zkn, Zks and
Zve64f from their members; V and the Zvl*b extensions from Zve64d and `vlenb`; and Zfinx, Zdinx,
Zhinx and Zhinxmin from the floating-point arithmetic executing while the corresponding load
(`flw`, `fld`, `flh`) does not, since the x-register extensions share the arithmetic encodings but
have no loads. I versus E is decided by touching x16.

Three extensions need special handling because their encodings overlap another extension's:
Zcmp reuses Zcd's `c.fsdsp` space, so it is probed only when Zcd is absent; on RV32, Zclsd's
`c.ld` is Zcf's `c.flw`, so the encoding is executed and the extension decided by which register
file it wrote; and Zicfilp's `lpad` is a hint until landing pads are enabled, so Zicfilp is
detected by whether the `MLPE` bit it adds to `mseccfg` can be set.

### Privileged extensions

Privileged extensions mostly add a CSR, or a field of an existing CSR, so their probes are CSR
accesses built from three helpers in `extensions.h`: `CSR_EXISTS` (the access traps unless the
extension is present), `CSR_BIT` and `CSR_FIELD` (the field accepts a value; the original value is
restored afterwards). For example Sstc is `stimecmp` existing, Svadu is `menvcfg.ADUE` being
settable, and Sstvecd is `stvec` accepting mode 0. The privilege modes are U (`mstatus.MPP` can hold
0), S (`sstatus` exists) and H (`hstatus` exists); Sm is always present since the extractor runs in
M-mode, with version 1.12 if `menvcfg` and (on RV32) `mstatush` both exist and 1.11 otherwise (1.13
is not distinguished). Address-translation modes are found by writing each mode to `satp` and
reading it back, which also gives Svbare, and Shgatpa and Shvsatpa by repeating that on `hgatp` and
`vsatp`. Sscounterenw and Shcounterenw compare the writable bits of `scounteren` and `hcounteren`
with those of `mcounteren`. Sspm, Supm, Ssu32xl on RV32, Svade with Svadu, and Sha are derived as
described in `extensions.h`.

### Parameters

`parameters.c` measures the UDB parameters that M-mode code can see and prints them as the
`params` section, each only when the extension that defines it was detected and the
measurement was conclusive. Most are CSR facts: identification CSRs (`VENDOR_ID_*`,
`ARCH_ID_VALUE`, `IMP_ID_VALUE`, `CONFIG_PTR_ADDRESS`), which `misa` bits can be cleared
(`MUTABLE_MISA_*`), the legal values and hardware updating of `mstatus.FS`/`VS`, endianness and
XLEN choices per mode, `mtvec`/`stvec`/`vstvec` modes, base alignment and behavior on an illegal
write, `mtval`/`stval` widths, which counters exist and which enable and inhibit bits are writable,
which interrupts are implemented (`*_INTR_IMPL`), the PMP entry count, granularity, address-match
modes and physical address width, `satp`/`hgatp`/`vsatp` modes, ASID and VMID widths, guest
interrupt count, `CACHE_BLOCK_SIZE` (bytes cleared by `cbo.zero`), `VLEN`, `ELEN`, `SEW_MIN`,
`VILL_SET_ON_RESERVED_VTYPE`, `VECTOR_LS_MISALIGNED_LEGAL`, the `mstateen0`/`hstateen0` enable
bit types, `srmcfg` and debug context widths, and the `mctrctl` controls. The rest come from
trapping: `MISALIGNED_LDST`, `MISALIGNED_AMO`, `LRSC_MISALIGNED_BEHAVIOR`, `TRAP_ON_EBREAK`,
`TRAP_ON_ECALL_FROM_M/S/U` (the S and U cases enter the mode with `mret`, after opening PMP
entry 0 to everything), `TRAP_ON_RESERVED_INSTRUCTION`, `TRAP_ON_UNIMPLEMENTED_CSR`, and the
`REPORT_*_IN_MTVAL_ON_*` parameters for the traps the extractor can provoke: illegal
instruction, breakpoint, misaligned load, store/AMO and instruction fetch, and load and store
access faults (taken with `mstatus.MPRV` set and `MPP` = U, so that no PMP entry matches).

Parameters that are not extracted, because nothing M-mode code can execute settles them:

- **Need an S-, VS- or virtualized trap handler:** every `REPORT_*_IN_STVAL_ON_*`,
  `REPORT_*_IN_VSTVAL_ON_*`, `REPORT_GPA_IN_*`, `TINST_VALUE_ON_*`, and `TRAP_ON_ECALL_FROM_VS`.
- **Need page tables or an inaccessible fetch:** `REPORT_VA_IN_MTVAL_ON_*_PAGE_FAULT`,
  `REPORT_VA_IN_MTVAL_ON_INSTRUCTION_ACCESS_FAULT`, `TRAP_ON_SFENCE_VMA_WHEN_SATP_MODE_IS_READ_ONLY`.
- **Memory-system behavior:** `LRSC_RESERVATION_STRATEGY`, `LRSC_FAIL_ON_VA_SYNONYM`,
  `LRSC_FAIL_ON_NON_EXACT_LRSC`, `MISALIGNED_LDST_EXCEPTION_PRIORITY`,
  `MISALIGNED_MAX_ATOMICITY_GRANULE_SIZE`, `MISALIGNED_SPLIT_STRATEGY`, `PMA_GRANULARITY`,
  `FORCE_UPGRADE_CBO_INVAL_TO_FLUSH`, `ZAWRS_NTO_IS_NOP`, `PRECISE_SYNCHRONOUS_EXCEPTIONS`.
- **Unbounded or undefined search:** `HPM_EVENTS` (every event number would have to be tried),
  `TRAP_ON_ILLEGAL_WLRL` and `TRAP_ON_UNIMPLEMENTED_INSTRUCTION` (no encoding is known to be
  illegal on every hart), `PMLEN` (the yamls do not agree on what it counts),
  `SCTRDEPTH_DEPTH_LEGAL_VALUES`.
- **Control-flow-integrity and debug traps:** `REPORT_CAUSE_IN_*_ON_*_SOFTWARE_CHECK`
  (a landing-pad or shadow-stack fault would have to be provoked), `DCSR_*_TYPE` (`dcsr` is
  only accessible in debug mode).
- **Vector behavior beyond legality:** `LEGAL_VSTART`, `RESERVED_VSET_X0X0_*`,
  `RVV_VL_WHEN_AVL_LT_DOUBLE_VLMAX`, `SUPPORT_FRACTIONAL_LMUL_BEYOND_REQUIRED`,
  `FOLLOW_VTYPE_RESET_RECOMMENDATION`, `IMPRECISE_VECTOR_TRAP_SETTABLE`, `VECTOR_FF_*`,
  `VECTOR_LOAD_*`, `VECTOR_LS_INDEX_MAX_EEW`, `VECTOR_LS_SEG_PARTIAL_ACCESS`,
  `VECTOR_LS_WHOLEREG_MISALIGNED_LEGAL`, `VFREDUSUM_*`.

Two measured values deserve a caveat: `HW_MSTATUS_FS_DIRTY_UPDATE` (and `VS`) reports `precise`
whenever one floating-point (vector) instruction leaves the field Dirty, since `imprecise` cannot
be told apart, and the `REPORT_VA_IN_MTVAL_ON_*_MISALIGNED` parameters can only be measured on a
hart where the misaligned access traps.

### Probes that can over-report

A probe shows that an instruction retires or that a CSR field holds a value. That is not always
the same as the extension being implemented, and two cases are known:

- **Smepmp** is probed by setting `mseccfg.RLB`. A hart may implement the `mseccfg` register
  without enforcing the MML and MMWP rules the extension defines — VeeR EL2 implements the CSR
  unconditionally while a build option gates only the PMP enforcement — and the probe reports
  Smepmp for such a hart. The behaviour cannot be probed instead, because MML and MMWP are sticky
  until reset, so setting either would change the machine under every later probe.
- **Any extension whose CSR exists but whose semantics are partial** has the same shape. Treat the
  output as a starting point to check against the core's documentation, not as a verdict.

The reverse mistake is worth naming too: an extension is reported only when _every_ part of it is
present. `Zicntr` needs `cycle`, `time` and `instret`, so a hart with two of the three — VeeR EL2
and Ibex both have `cycle` and `instret` but no `time` — is not reported, and the extractor prints
a note saying which one is missing. If the platform supplies `time` another way, set
`TIME_CSR_IMPLEMENTED` to false and claim `Zicntr` by hand.

`Sm` is reported as 1.12 only when both `menvcfg` and, on RV32, `mstatush` are present, since 1.12
added both. A hart with one and not the other matches neither version; the extractor reports the
lower one, which is the version such a hart actually works under, and prints a note. Declaring 1.12
for a hart without `mstatush` makes the test environment read it on every trap, and each trap then
takes a nested trap.

### Untested extensions

Extensions that add no instruction or CSR whose legality could be tested cannot be detected, and
the output names them on a `# untested:` line so the reader knows they were not looked for:

- hints, which execute everywhere: Zihintpause, Zihintntl, Zicbop
- behavioral guarantees: Zicclsm, Ztso, Zkt, Zvkt, Zic64b, Ziccif, Ziccamoa, Ziccamoc, Ziccrse,
  Za64rs, Za128rs, Zama16b, and Zk, Zvkn, Zvknc, Zvkng, Zvks, Zvksc, Zvksg (which need Zkt or Zvkt)
- trap-value guarantees: Sstvala, Shtvala, Shvstvala
- page-table-walk behavior: Ssccptr, Svvptc, Svnapot, Svrsw60t59b, and Svade unless Svadu is
  present (with Svadu, `menvcfg.ADUE = 0` is defined as Svade behavior)
- Ssstrict, which is what every other probe assumes
- Sdext, which is only visible from debug mode

Zibi and Zvabd are not probed because they are frozen, not ratified. Sha is reported when H and
its testable members (Shcounterenw, Shgatpa, Shvsatpa, Shvstvecd) are present, assuming the two
untested ones.

## Building and running

The program is compiled for the E base ISA (`rv32e` or `rv64e`, plus Zicsr) so that it runs on E
harts as well; each probe enables the extension it needs with `.option arch`. Only two files are
taken from the target's configuration directory: `rvmodel_macros.h`, for console output and
halting, and `link.ld`, for the memory map.

```
make -f tests-dev/priv/UDBFeatureExtractor/Makefile                       # RV64 on Sail, RVA23S64
make -f tests-dev/priv/UDBFeatureExtractor/Makefile XLEN=32 CONFIG_DIR=config/sail/sail-rv32-max
make -f tests-dev/priv/UDBFeatureExtractor/Makefile elf CONFIG_DIR=config/cores/cvw/cvw-rv64gc
```

`run` writes the YAML to `work/UDBFeatureExtractor/extracted_config<XLEN>.yaml`; `elf` only builds,
for running on a DUT with its own simulator. The console output is the YAML, so any target whose
`RVMODEL_IO_WRITE_STR` reaches a log works.

## Testing

```
make -f tests-dev/priv/UDBFeatureExtractor/Makefile regression JOBS=8
```

runs the extractor on every configuration directory under `config/` that has a `run_cmd.txt` (the
Sail profile and max configurations, and the cores) using that command, and compares the
extensions it reports with the directory's UDB yaml. Configurations whose simulator is not on
`PATH` are skipped. Names are compared, not versions; extensions the extractor lists as untested
are counted separately rather than as mismatches. The summary gives, per configuration and in
total, how many extensions match and which are missing (in the yaml but not detected) or extra
(detected but not in the yaml). An extra that is defined as exactly a set of extensions the yaml
does list (Zkn, Zks, Zbkc) is shown as implied instead. `--jobs` runs configurations in parallel;
a Verilator run of Wally takes minutes the first time, Sail a few seconds.
The params section is compared the same way: each parameter the extractor prints is checked against
the yaml's value, and the per-configuration line lists mismatches with both values, plus how many of
the yaml's parameters were not extracted.

Two steps before the first probe matter for some targets: `mstatus.MDT` is cleared, since
Smdbltrp sets it at reset and a probe's trap would then be a double trap, and `mnstatus.NMIE` is
set, since with Smrnmi an exception taken while it is clear goes to the RNMI vector rather than
`mtvec`. Both are probes themselves, so a hart without the CSR just traps normally.

```
make -f tests-dev/priv/UDBFeatureExtractor/Makefile test
```

is a finer self-test of the unprivileged probes: it runs the extractor for RV32 and RV64 on the
Sail max configurations with groups of extensions switched off through `--config-override` (M, A,
B, C, Zi*, vector, floating point, Zfinx family, and E) and checks that every extension the Sail
configuration names is reported exactly when the configuration enables it. Privileged
extensions, the untested ones above and extensions that are not yet ratified are not checked.

## Adding an extension

Add one row to `extensions.h`:

```
X(Zfoo, "1.0.0", "zfoo", "foo t1, t2, t2")
```

giving the UDB name and version, the extension the assembler must enable to accept the
instruction, and an instruction that is legal only with the extension and harmless when it
executes. The probe function, the YAML line and the self-test follow from the row. Inside the
instruction, `a1` points at aligned scratch memory for loads, stores, atomics and cache-block
operations, and `t1`, `t2`, `a2`, `a3`, `s0`, `s1`, the low floating-point registers and all
vector registers may be written.

A privileged extension is a row in the `PRIV_EXTENSIONS` table instead:

```
P(Sfoo, "1.0.0", "zicsr", CSR_EXISTS(0x5C0))
P(Sbar, "1.0.0", "zicsr", CSR_BIT(menvcfg, 58))
```

Any sequence that leaves `a3` nonzero when the extension is present, and traps or leaves it zero
otherwise, may be used in place of the helpers.
