# tests_ai: certification tests derived from normative rules

Each test checks one normative rule (`norm:` tag in the ISA manual). The file is `<Suite>/<rule>.S`, and its header holds the rule text, context, clarifying issues and the test plan. Expected values are built into the test from the spec. No reference model, test plan, or UDB parameter other than the list of supported extensions is involved. Legal outcomes that the spec leaves open are all accepted. Each suite's README lists the rules it does not test, and why.

Layout:

- `<Suite>/*.S` are the generated tests. They are not committed: `make tests-ai` writes them by running every
  `gen/gen_*.py` (with the repository's uv Python, as for the other generators; they also run on Python 3.9), and
  regenerates all suites when a generator or helper changes. `run_ai.sh` runs it first. `<Suite>/README.md`
  describes the tests.
- `gen/gen_<Suite>.py` is the generator for one suite. `gen/aigen.py` is the shared writer: XLEN-dual tables, checks, registers, T-SBI and trap-window helpers.
- `gen/norm_rules.py` lists the rules in ISA-manual sources. `gen/mutate.py` regenerates a suite from deliberately wrong semantics to show the tests catch those bugs.
- `common/ai_macros.h` holds the check and trap-window macros on top of `tests/env`.
- `run_ai.sh` builds and runs suites on ACT configurations. `run_mutants.sh <prefix> <config>` runs every mutant whose
  name starts with prefix and requires each to fail a test. Mutants are named `<area>:<mutant>` for H (one `MUTANTS`
  dict per `gen/h_*.py`) and `<Suite>:<mutant>` for any other `gen/gen_<Suite>.py` with a `MUTANTS` dict.

Running:

```bash
mise exec -- tests_ai/run_ai.sh M,Sstc config/sail/sail-rv64-max config/spike/spike-rv32-max
DEBUG=1 mise exec -- tests_ai/run_ai.sh Sstc config/qemu/qemu-rv32-max   # traces and objdumps
AI_ONLY="hgatp_* sret_*" mise exec -- tests_ai/run_ai.sh H config/sail/sail-rv64-max   # only matching tests
mise exec -- tests_ai/run_mutants.sh h_csr: config/sail/sail-rv64-max                    # mutation check
make tests-ai                                                            # generate every suite
python3 tests_ai/gen/gen_Sstc.py                                         # regenerate one generator's suites
```

Logs are in `work/tests_ai/<config>/logs/ai/<Suite>/`. Concurrent runs need their own `AI_WORKDIR` and
`XDG_DATA_HOME` (the UDB configuration cache). A failing check prints the rule, the case, the expected value(s) and the actual value.

Mechanics:

- **No signature.** Tests use `NEEDS_SIGNATURE: false`. `x3` walks a table of operands and expected values, emitted separately for RV32 and RV64 under `#if __riscv_xlen`. `AI_CHECK` uses the same `LREG`/`beq`/`jal failedtest_x5_x4` shape as `RVTEST_SIGUPD`, so the standard failure report applies.
- **Traps: the framework trap log.** In a no-signature build, the framework trap handlers (M, HS and VS) record each trap in a small ring in the signature section, the trap log (`TRAP LOG` in `tests/env/rvtest_trap_handler.h`). A test permits traps with `AI_ALLOW(n)`; any trap it did not permit fails the test, and the report shows xcause, xepc and xtval.
  - Each entry holds the handler mode, xcause, xepc, xtval, the second trap value and xtinst with H, xstatus and mstatush/hstatus on entry, and the resume address. Setting `rvtest_trap_resume` makes the handler resume at a chosen address.
  - After the instructions under test, `AI_OUTCOME` gives the number of traps (x13) and the last xcause, or -1 for none (x14). `AI_LOG` reads any word of the last entry, and `AI_ORIGIN` decodes the mode the trap came from (from xPP and MPV/SPV).
  - `TestFile.window(mode, lines, expect, ...)` wraps this. `expect` is "ok", a cause, or a list of legal alternatives such as `["ok", 4, 5]` for a misaligned load. For a trap it also checks xepc, legal xtval values and the mode the trap came from.
  - Windows work in any mode (M, S, U, VS, VU). T-SBI calls inside a window are not logged, and neither are instructions emulated by the invisible trap handler. Lower modes are entered with `sret`/`mret` and left with a T-SBI GOTO.
- **Registers.** Tests use x1-x15 only, so no separate E directories are needed. Tests that call T-SBI or open trap windows draw operands from x1 and x6-x9 (`POOL_TRAP`). E configurations still don't select these tests: the header's `MARCH: rv${XLEN}i...` and `REQUIRED_EXTENSIONS: ['I', ...]` fix the base ISA, and ACT has no MARCH substitution for I/E. Changing that is a framework decision.
- **Unprivileged tests** set no boot mode and run in the lowest mode, where they can open trap windows directly. Without S, traps from U reach the M handler.
- **RV64-only rules.** Their files have the whole body under `#if __riscv_xlen == 64` and pass trivially on RV32; no `params:` are used. M-mode-only parts of a rule go in `<rule>_Sm.S`, which requires `Sm` so RVA23 excludes it.
- **Discovery.** ACT finds tests under `<test-dir>/*/<Suite>/*.S`. `run_ai.sh` builds a staging test dir with symlinks to `tests/env` and `tests_ai`, and always passes `--extensions`.
