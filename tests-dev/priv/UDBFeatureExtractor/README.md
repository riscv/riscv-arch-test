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
M-mode, with version 1.12 if `mconfigptr` and (on RV32) `mstatush` both exist and 1.11 otherwise. 1.13 is
reported when `medeleg` can delegate the hardware-error exception (19), or the software-check
exception (18) without Zicfilp or Zicfiss, both reserved before 1.13, or on RV32 when `medelegh`
exists; a 1.13 hart without S-mode is reported as 1.12. Address-translation modes are found by writing each mode to `satp` and
reading it back, which also gives Svbare, and Shgatpa and Shvsatpa by repeating that on `hgatp` and
`vsatp`. Sscounterenw and Shcounterenw compare the writable bits of `scounteren` and `hcounteren`
with those of `mcounteren`, on a hart with Zihpm (UDB defines them only with it). A 32-bit hart
without Sv32 gets `PHYS_ADDR_WIDTH` 32 even when `pmpaddr` keeps bits 33:32 writable, with a note.
Sspm, Supm, Ssu32xl on RV32, Svade with Svadu, and Sha are derived as
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

Some trap-report parameters are measured in S-mode and VS-mode: the extractor enters the mode with
`mret` into a stub that executes one instruction, with the exception delegated through `medeleg`
(and `hedeleg`) to a small handler in `start.S` that records `scause`, `stval` and `sepc` (which
name the VS copies in VS-mode) and returns to M-mode with `ecall`. That gives the
`REPORT_*_IN_STVAL_ON_*` and `REPORT_*_IN_VSTVAL_ON_*` values for illegal instructions,
breakpoints, misaligned accesses, and load, store and instruction access faults, the last three
by pointing PMP entry 0 at the scratch page with no permissions while entry 1 grants everything
else, plus `TRAP_ON_ECALL_FROM_VS` and `REPORT_VA_IN_MTVAL_ON_INSTRUCTION_ACCESS_FAULT`.

Page faults use a one-level page table built in the scratch area: the entry for the region that
holds the program maps it to itself and every other entry is invalid, so a load, store or jump to
another region page-faults while the stubs and handlers keep running. With the table in `satp` the
faults are taken delegated (`STVAL`) and undelegated (`MTVAL`); with it in `vsatp` and the G-stage
Bare they are taken in VS-mode (`VSTVAL`); with a G-stage table in `hgatp` (leaf `U` bit set, 16 KiB
root, which is why the scratch area is 16 KiB) and the VS-stage Bare they are guest page faults,
whose GPA is read from `htval` when HS-mode took the trap or `mtval2` when M-mode did. A hart whose
`satp` accepts no translation mode instead gets `TRAP_ON_SFENCE_VMA_WHEN_SATP_MODE_IS_READ_ONLY`.
Putting the VS-stage root itself in an unmapped guest-physical region makes the walk's first PTE
fetch an intermediate guest page fault.

The `TINST_VALUE_ON_*` parameters repeat the VS-mode traps with nothing delegated to VS-mode, so
HS-mode takes them and its handler records `htinst`; the ecalls reach M-mode and `mtinst` is read
there. Zero is `always zero`, a value whose opcode field is a load, store or AMO is `always
transformed standard instruction`, and anything else `custom`.

Vector parameters beyond `VLEN`/`ELEN`/`SEW_MIN` come from vsetvli experiments: `vtype` and `vl` as
left by reset (read before any probe touches the vector unit), whether `vill` is set by the
`x0, x0` form when `vill` is already set or when VLMAX would change, `vl` for an AVL between VLMAX
and twice VLMAX, the widest index EEW an indexed load accepts, the `vstart` values an arithmetic
instruction accepts, and whether a whole-register load tolerates a misaligned base.

The fault-only-first and segment parameters use a second page table with one 4 KiB page mapped and
the page after it invalid (Sv39 or Sv32, whose levels fit the scratch area). In S-mode a
fault-only-first load, an ordinary load, a two-field segment load and a two-field segment store are
run against the page's edge, and `vl`, the destination registers (written back to memory in M-mode)
and the page's last bytes say what was trimmed, loaded or stored.

Memory-model and reduction parameters: LR/SC behavior comes from an `sc.w` inside an `lr.d`
reservation (non-exact), from SCs at increasing offsets from the LR (the reservation set), and from
an SC through a second virtual address of the scratch area (VA synonym); the misaligned exception
priority and split strategy from a misaligned access straddling the mapped page's edge; `VFREDUSUM_NAN`
from a reduction with all elements masked off and a NaN payload as the scalar;
`VFREDUSUM_NODE_ROUNDING_BEHAVIOR` from a two-element reduction whose three operands give one
result under every reduction tree when the inner sum is rounded to SEW precision and another when
it is kept wider; `HPM_EVENTS` from writing event numbers to `mhpmevent3`; `TRAP_ON_ILLEGAL_WLRL`
from writing an exception code no hart implements to `mcause`; and `FORCE_UPGRADE_CBO_INVAL_TO_FLUSH`
from whether `menvcfg.CBIE` accepts 11.

At the end of the `params` section the extractor prints, commented out and without values, every
parameter that applies to the hart but that it could not determine, under a comment saying so. The
parameter list with each one's defining extension is `udb_parameters.h`, generated by
`test/gen_udb_parameters.py` from the udb gem that `framework/src/act/data/Gemfile` pins (or from a
riscv-unified-db checkout given as its argument); regenerate it when the pin moves.

More parameters from CSR read-back: `MEDELEG_DELEGATABLE` and `MIDELEG_DELEGATABLE` (all ones
written to `medeleg`/`mideleg`, and `medelegh`/`midelegh` on RV32), `HPM_COUNTER<n>_WIDTH` (the
highest bit of `mhpmcounter<n>` that holds a one), `NON_STANDARD_EXTENSION_IMPLEMENTED`
(`misa.X`), `SSEED_READ_ONLY_ZERO` and `USEED_READ_ONLY_ZERO`, and `SUPPORTED_PMLEN_*` (the
`PMM` values each pointer-masking field accepts). `WFI_U_MODE` is whether `wfi` in U-mode with
`mstatus.TW` clear retires or traps; it is probed only with S-mode present, where the spec bounds
the wait. With the watchdog's timer, `wfi` and `wrs.nto` (with a reservation held) run in M-mode
with only `mie.MTIE` set and an interrupt due 2^16 `mtime` ticks later: `WFI_FINITE` is whether
`wfi` resumed before then, and `ZAWRS_NTO_IS_NOP` whether `wrs.nto` took fewer than 50 cycles more
than two back-to-back `mcycle` reads. The Sdtrig parameters come from walking `tselect` (a value that does not stick, or a
`tinfo` with only type 0, ends the walk), `tinfo` or a type written to `tdata1` for each trigger's
types, inert `mcontrol6` values written to `tdata1` (never a privilege bit together with an access
type, so no trigger can fire) for the writable bits and the `MATCH` and `SIZE` values, an all-ones
NAPOT `tdata2` for `maskmax6`, `chain` set on successive triggers for the longest chain, an
all-ones `textra` for its field widths, all-ones `tdata2` for the interrupts and exceptions
`itrigger` and `etrigger` can select, and `icount.count` holding 2 or 1. `tdata1` is written with
zero before each value, since a hart may take a new configuration only for a disabled trigger.

### Sail configuration keys

Some behavior the Sail reference model needs configured has no UDB parameter. The extractor
measures what it can and prints each as a comment, `# sail: <key>: <JSON value>`, with the key
being the dotted path in Sail's configuration: `base.writable_fiom`, `base.hpmevent_width_bits`,
`base.reserved_behavior.*` (a reserved `pmpcfg` R/W combination, `menvcfg.CBIE` value, `stvec` mode,
dynamic rounding mode, odd `amocas` and RV32 Zdinx register pair), `platform.hartid`,
`platform.reservation.invalidate_on_same_hart_store` and `require_exact_reservation_addr` (an SC to
the word after the LR's failing), `extensions.Zkr.*_reset_value`, the
`extensions.Stateen` bits UDB has no parameter for, `extensions.V.reserved_behavior.vstart_out_of_bounds`,
`extensions.F.fflags_dirty_policy` (whether `feq.s` makes `FS` Dirty with no flag raised, with a
flag raised again, and with a new flag) and `memory.misaligned.exceptions.{load_store,amo,vector}`.
A behavior that none of Sail's options describes is printed as `# sail-unmodelled: <key>: ...`.

Control-flow integrity: with `mseccfg.MLPE` set, an indirect jump to an instruction that is not
`lpad` raises a software-check exception with tval 2, in M-mode directly and in S-mode and
VS-mode through `menvcfg.LPE`/`henvcfg.LPE`; a shadow-stack pop whose value does not match
(`sspush`, then `sspopchk` of a different value) raises one with tval 3 in S-mode and VS-mode
through `menvcfg.SSE`/`henvcfg.SSE`, and undelegated in M-mode; the shadow stack has to be a page
with the shadow-stack permission encoding, so the page table's second region aliases the program's
region that way and `ssp` points into the scratch area through the alias. While
these run the M-mode handler also clears the pending landing pad and `MLPE`, or the resume itself
would fault.

The parameters that are not extracted, grouped by what it would take, are tracked in
[parameters_not_extracted.md](parameters_not_extracted.md).

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

`Sm` is reported as 1.12 only when both `mconfigptr` and, on RV32, `mstatush` are present, since 1.12
added both (`menvcfg` is not used as the marker because it exists only with U-mode). A hart with
1.12 CSRs but no `mstatush` matches neither version; the extractor reports the lower one, which is the version such a hart actually works under, and prints a note. Declaring 1.12
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

### The watchdog

A hart with a buggy implementation of an extension may hang on its probe instead of retiring the
instruction or trapping. When `rvmodel_macros.h` defines `RVMODEL_MTIME_ADDRESS` and
`RVMODEL_MTIMECMP_ADDRESS`, the extractor arms a machine-timer interrupt around every extension
probe and every probe run in a lower mode. A probe still running when the interrupt arrives is
stopped, and its feature is reported as not implemented with a `# warning:` line. At boot the
extractor times a counted loop against `mtime` and sets the timeout to 64 such loops, about half a
million instructions whatever rate `mtime` counts at. It then checks that the interrupt really
arrives before relying on it. A probe that times out is tried once more with a timeout 16 times
longer, so a simulator whose `mtime` follows the host's clock cannot fail a probe by being
descheduled. The `# watchdog:` line at the top of the output gives the timeout, or the reason there
is none. `EXTRA_CFLAGS=-DWATCHDOG_SELFTEST` adds a probe that never finishes, to check the watchdog
on a new DUT.

The watchdog cannot help when the hart has no machine timer or the simulator itself stops; the
Sargantana testbench, for example, ends the run when 200 cycles pass without an instruction
committing. `make_config.py` handles those runs: see below.

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

A hart that ignores CSR instructions instead of trapping on them (Wally's rv32i and rv64i, which
have no Zicsr) is recognized at startup, because a value written to `mscratch` does not read back.
No probe can work on such a hart, so the extractor reports only I or E, Sm and `MXLEN`.

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

## Generating a configuration for a new DUT

```
make -f tests-dev/priv/UDBFeatureExtractor/Makefile config CONFIG_DIR=config/cores/<vendor>/<core>
uv run tests-dev/priv/UDBFeatureExtractor/make_config.py --config-dir config/cores/<vendor>/<core> --out-dir OUT
```

reads only the four files a DUT port starts with — `test_config.yaml`, `run_cmd.txt`, `link.ld`
and `rvmodel_macros.h` — and writes `<name>.yaml` and `sail.json` to `OUT` (the Make target uses
`work/UDBFeatureExtractor/config/<core>`):

1. `xlen_probe.S` runs on the DUT to find XLEN. Its instructions behave the same on RV32 and RV64,
   but simulators refuse an ELF of the wrong class, so both classes are tried; the run command only
   decides which goes first.
2. The extractor is built for that XLEN and run with `run_cmd.txt`. If the run ends without the
   extractor's last line (`# end of extractor output`), the extractor is rebuilt with
   `-DTRACE_PROBES`, which prints `# probe: NAME` as each extension probe starts, and run again.
   The probe the run stopped in is then run by itself (`-DONLY_PROBE='"NAME"'`). If it finishes
   alone, the run hit a cycle or time limit, not a hang, so nothing is left out. Otherwise it is
   left out with `-DSKIP_PROBES='"NAME,..."'` and reported as not implemented, and this repeats
   until the run finishes. A run that stops after the extension probes, or that takes longer than
   `--timeout` while the watchdog is on, is used as far as it got, and the parameters it did not
   reach are assumed.
3. The yaml gets the extensions and parameters the extractor reported. `udb validate cfg` then says
   what is still wrong, and the script repeats until UDB accepts the file: a missing parameter gets
   the value most ACT configurations of the same XLEN use; a parameter that does not apply, or that
   the schema rejects, is dropped; an extension that another one requires and the extractor cannot
   probe (such as Shtvala for Sha) is added; and an extension's version is raised when another one
   requires a later one (Ssqosid needs S 1.13, which the extractor cannot tell from 1.12 on RV64).
   Every such value carries an `# assumed:` comment, so the file says exactly what was measured.
   Assumed parameters that no probe can measure on any hart (the list in
   `parameters_not_extracted.md`) are grouped apart from those not determined on this DUT.
4. `udb_to_sail.py` turns the yaml into `sail.json`, adding the Sail-only values the extractor
   measured (its `# sail:` lines).
5. The script ends with a list of what to check or fix by hand, each item as `file:lines` in the
   generated files: probes the watchdog stopped or that were left out, the untested extensions,
   UDB's remaining complaints, the extensions added because another requires them, the parameters
   no probe can measure, the parameters assumed on this DUT, measured values UDB rejected, the Sail
   keys left at Sail's default, and those of them no probe can measure.

UDB keeps a cache of every configuration it has resolved, under the configuration's name, and
reuses it while it is newer than the yaml. A generated yaml has the same name as the checked-in
one, so the script points UDB at a data directory of its own (`OUT/udb-data`).

## Converting a UDB configuration to a Sail configuration

```
uv run tests-dev/priv/UDBFeatureExtractor/udb_to_sail.py <udb.yaml> -o sail.json --config-dir DIR [--sail-extra extra.json] [--compare old.json]
```

starts from Sail's default configuration for the XLEN (`sail_riscv_sim --print-default-config`) and
sets every key a UDB extension or parameter determines. The memory map comes from `DIR`: main memory
from `RAM_ORIGIN`/`RAM_LENGTH` in `link.ld`, and an IO region holding Sail's CLINT (at the DUT's
`RVMODEL_MTIME_ADDRESS` - 0xBFF8 when that is free) and the simple interrupt generator, kept clear of
`RVMODEL_ACCESS_FAULT_ADDRESS`. The macros are evaluated by assembling `.dword MACRO`, so `.EQU`
symbols and expressions work. The output is checked with `sail_riscv_sim --validate-config`.

The comment block at the top of the output lists the keys left at Sail's default because neither
UDB nor a measurement determines them, and the UDB values Sail cannot express. Some UDB facts map
onto Sail only approximately:

- Sail has one `xtval_nonzero` switch per exception for M, S and VS together, where UDB has one
  parameter per mode; the converter uses the M-mode value and reports a disagreement.
- `mideleg` bits 2, 6, 10 and 12 are read-only one with H, so Sail does not count them as
  delegatable, though UDB's `MIDELEG_DELEGATABLE` lists them.
- Trigger support is per trigger in UDB and per trigger type in Sail.
- `MISALIGNED_AMO` says whether a misaligned AMO traps but not with which exception; the
  converter assumes a misaligned-address exception unless the extractor measured otherwise. Sail
  lets a misaligned AMO proceed only inside the main-memory region's atomicity granule, so a hart
  whose misaligned AMOs succeed gets at least a 16-byte granule.
- `MISALIGNED_SPLIT_STRATEGY` = `sequential_bytes` becomes aligned pieces in increasing address
  order; Sail's byte-by-byte option looks the same, since a piece can only fault at a page or PMP
  boundary, which is piece-aligned.
- Reserved `medeleg` bits that a hart lets be set, and an RV64 `mstateen0.P1P13` that is writable,
  are left out: Sail rejects both.
- Stateen bits without a UDB parameter are writable exactly when what they guard exists.
- Sail allows more than 16 PMP entries only from privileged ISA 1.12, so a 1.11 configuration with
  64 entries gets 1.12.

`--compare` lists the relevant keys that differ from an existing `sail.json`; misaligned-access
settings are compared on what they do (trap, or allowed within a granule) rather than on how
they are spelled.

## Regression for the generated configurations

```
make -f tests-dev/priv/UDBFeatureExtractor/Makefile config-regression JOBS=16
```

runs `make_config.py` on every configuration with a `run_cmd.txt` and reports, per configuration:
whether UDB and Sail accept the generated files; the extensions and measured parameters that
differ from the configuration's yaml; the generated `sail.json` keys that differ from the
configuration's, labelled by where the generated value came from (measured, assumed, an untested
extension, or Sail's default); and the keys where the configuration's own yaml and `sail.json`
disagree.

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
