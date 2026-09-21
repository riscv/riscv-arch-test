# UDB feature extractor

Detects which ratified unprivileged extensions a hart implements and prints the result as the
`implemented_extensions` section of a [UDB](https://github.com/riscv-software-src/riscv-unified-db)
configuration, ready to seed a `config/cores/<vendor>/<core>/<core>.yaml`.

Adapted by David Harris from the original by Jayant Malvi
([riscv-arch-test #1655](https://github.com/riscv/riscv-arch-test/pull/1655)), with assistance
from Claude.

## How it works

Every extension in `extensions.h` is detected the same way: the program executes one instruction
(or CSR access) that only that extension makes legal and checks whether it traps.  The trap
handler in `start.S` returns to the probe when the instruction traps, so a trap means "absent" and
retiring means "present".  This relies on the hart raising an illegal-instruction exception for
encodings it does not implement, which the Ssstrict extension guarantees; on a hart without
Ssstrict an unimplemented encoding may do anything, and the result is not trustworthy.

Some extensions are derived rather than probed: umbrella names such as A, B, C, Zkn, Zks and
Zve64f from their members; V and the Zvl*b extensions from Zve64d and `vlenb`; and Zfinx, Zdinx,
Zhinx and Zhinxmin from the floating-point arithmetic executing while the corresponding load
(`flw`, `fld`, `flh`) does not, since the x-register extensions share the arithmetic encodings but
have no loads.  I versus E is decided by touching x16.

Three extensions need special handling because their encodings overlap another extension's:
Zcmp reuses Zcd's `c.fsdsp` space, so it is probed only when Zcd is absent; on RV32, Zclsd's
`c.ld` is Zcf's `c.flw`, so the encoding is executed and the extension decided by which register
file it wrote; and Zicfilp's `lpad` is a hint until landing pads are enabled, so Zicfilp is
detected by whether the `MLPE` bit it adds to `mseccfg` can be set.

Extensions that add no instruction whose legality could be tested cannot be detected: hints
(Zihintpause, Zihintntl, Zicbop) execute everywhere, and the behavioral extensions (Zicclsm, Ztso,
Zkt, Zvkt, Zic64b, Ziccif, Ziccamoa, Ziccamoc, Ziccrse, Za64rs, Za128rs, Zama16b) change what
instructions do rather than whether they trap.  The output names them in a comment.

## Building and running

The program is compiled for the E base ISA (`rv32e` or `rv64e`, plus Zicsr) so that it runs on E
harts as well; each probe enables the extension it needs with `.option arch`.  Only two files are
taken from the target's configuration directory: `rvmodel_macros.h`, for console output and
halting, and `link.ld`, for the memory map.

```
make -f tests-dev/priv/UDBFeatureExtractor/Makefile                       # RV64 on Sail, RVA23S64
make -f tests-dev/priv/UDBFeatureExtractor/Makefile XLEN=32 CONFIG_DIR=config/sail/sail-rv32-max
make -f tests-dev/priv/UDBFeatureExtractor/Makefile elf CONFIG_DIR=config/cores/cvw/cvw-rv64gc
```

`run` writes the YAML to `work/UDBFeatureExtractor/extracted_config<XLEN>.yaml`; `elf` only builds,
for running on a DUT with its own simulator.  The console output is the YAML, so any target whose
`RVMODEL_IO_WRITE_STR` reaches a log works.

## Testing

```
make -f tests-dev/priv/UDBFeatureExtractor/Makefile test
```

runs the extractor for RV32 and RV64 on the Sail max configurations with groups of extensions
switched off through `--config-override` (M, A, B, C, Zi*, vector, floating point, Zfinx family,
and E) and checks that every extension the Sail configuration names is reported exactly when the
configuration enables it.  Privileged extensions, the undetectable ones above and extensions that
are not yet ratified (Zibi, Zvabd) are not checked.

## Adding an extension

Add one row to `extensions.h`:

```
X(Zfoo, "1.0.0", "zfoo", "foo t1, t2, t2")
```

giving the UDB name and version, the extension the assembler must enable to accept the
instruction, and an instruction that is legal only with the extension and harmless when it
executes.  The probe function, the YAML line and the self-test follow from the row.  Inside the
instruction, `a1` points at aligned scratch memory for loads, stores, atomics and cache-block
operations, and `t1`, `t2`, `a2`, `a3`, `s0`, `s1`, the low floating-point registers and all
vector registers may be written.
