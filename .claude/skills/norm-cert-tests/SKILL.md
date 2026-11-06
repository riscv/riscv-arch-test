---
name: norm-cert-tests
description: Use when asked to generate certification tests for a RISC-V extension directly from its normative rules (tests_ai/ in riscv-arch-test). Produces one self-checking assembly test per norm: tag, with expected values derived from the spec. Uses no reference model, ACT test plan, or UDB parameters.
---

# Rule-derived certification tests (tests_ai)

Goal: catch implementation errors that would break software compatibility, independently of the human-written ACT test plans, the Sail model and UDB parameters. A test is worth keeping only if it can fail on a plausible design bug.

Before starting, read `tests_ai/README.md` (mechanics), `tests_ai/gen/aigen.py` (the `TestFile` API) and one existing generator: `gen_M.py` for unprivileged extensions, `gen_Sstc.py` for privileged ones.

## Hard rules

**Scope and naming**

- Write one test per normative rule. Every `norm:` tag is a rule (riscv-isa-manual #3422).
- The file is `tests_ai/<Suite>/<rule>.S`. The suite is the extension name, and its tests require that extension.
- If a rule needs a second file (only the M-mode part, see "Privilege mode"), name it `<rule>_Sm.S` with `suffix="_Sm"`.

**Expected values**

- Expected values come from the spec. A generator may compute arithmetic (Python, or SoftFloat for FP), but nothing comes from Sail or another model.
- Accept every legal outcome:
  - Up to 3 discrete values: `check(reg, [a, b, c], ...)`.
  - "Some bits are free": `check_masked`.
  - Larger sets (ranges, "anything but X"): compute a predicate into a register with branch-free code and use `check_bool`.
  - Never drop a legal outcome to fit a helper.
- If the value is UNSPECIFIED, test what is constrained instead. For example, marchid's value is free, but its readability and the effect of writing it are not. Write no test only when no observable behavior is inconsistent with the spec, and list such rules in the README.

**What a test may use**

- The only configuration inputs are the `X_SUPPORTED` extension macros, `__riscv_xlen`, and DUT macros from `rvmodel_macros.h` (e.g. `RVMODEL_MTIMECMP_ADDRESS`, under `#ifdef`).
- Use no UDB parameters, and no `params:` in the test header.
- Optional behavior is probed at run time: read or write the CSR, or attempt the access inside a trap window, then branch on the outcome with `t.either(reg, if_set, if_clear)`. Both paths are emitted with their own expectations and each skips the other's table entries. Check WARL control bits the test depends on, such as `hcounteren.TM`, which may be read-only zero.
- Do not consult existing generators, test plans, coverpoints or `coverpoints/norm`. You may look at one existing test for syntax only.

**Framework and DUT bugs**

- Do not modify `tests/env`. When the framework blocks a test, stop on that point and report it to the user.
- Do not ask for `medeleg`/`mideleg` in T-SBI; only M-mode tests change them.
- Do not work around DUT bugs. Report them.

**Registers and XLEN**

- Never repurpose x2 (signature pointer), x3 (table pointer), x4/x5 (check temporaries) or a0-a2 (T-SBI).
- Use x1-x15 only, so tests remain E-compatible. Draw operands with `t.regs()` from the pool (`POOL_TRAP` when the test calls T-SBI or opens trap windows; those use x13-x15).
- Write one file per rule for both XLENs:
  - `X(v32, v64)` for XLEN-dependent values; `rv64_only()`/`rv32_only()` for XLEN-specific code.
  - `rv64=True` for an RV64-only rule (the file passes trivially on RV32).

**Size and form**

- Stay under 100k dynamic instructions per file; `TestFile.render` asserts this.
- No loops, except bounded wait loops with no checks inside. Size them deliberately: about 500 iterations to await a change, about 50 to watch a steady state. Polls dominate the instruction count.
- Gate cross-extension cases with `only_if("defined(F_SUPPORTED)")`, or with `REQUIRED_EXTENSIONS` for a whole file. MARCH must include every extension whose instructions the file assembles.
- Generate no coverage files and no rule mapping.

## Workflow

1. **Collect the rules.**
   - Run `python3 tests_ai/gen/norm_rules.py <chapter.adoc>` (reads upstream/main of `~/repos/riscv-isa-manual`).
   - Behavior is often tagged outside the extension's chapter; Sstc's chapter only declares CSRs. Also run `--grep '<csr>|<field>|<insn>'` over `src/priv/*.adoc` or `src/unpriv/*.adoc`.
   - Sort every hit into one of three groups:
     - tested here;
     - belongs to another suite (say which, e.g. "when X is not implemented" needs `FORBIDDEN_EXTENSIONS: [X]`);
     - untestable (say why: reserved or UNSPECIFIED outcome, timing, unreachable state, conflicting rules).
   - Read the whole section around each rule.
2. **Search issues.**
   - Search with `gh search issues --repo riscv/riscv-isa-manual "<term>"` for each CSR, field and instruction.
   - Read the outcome with `gh issue view N --comments`.
   - In the header, cite the issue as a full URL and quote the resolution.
   - Issues often turn a seemingly fixed value into an UNSPECIFIED one (STIP after an STCE change, #1636).
3. **Design each test** and write its plan into `describe(plan=...)` before coding. Cover:
   - **Classes.** Split what the rule covers into classes that could behave differently and test one representative each. Test all members only when the rule is about all of them (access or read-only rules).
   - **Edges.** Cross the arithmetic edges 0, 1, 2, -1, -2, MIN, MIN+1, MAX, MAX-1, 2^(n/2), 2^(n/2)-1, 0x55.. and 0xAA.., plus random values.
   - **State sweeps.** Sweep the state the rule depends on (enables, modes, delegation). Add negative-dependency sweeps over state a buggy design might wrongly consult (e.g. TM=0 must not stop the timer comparison).
   - **Enabled-but-denied cases.** E.g. U-mode access to an S-level CSR with every enable set. Counter-enable leaks are plausible bugs.
   - **Transitions.** Clear an enable while the gated bit holds 1, set one while software held the bit. These show masking versus stored state.
   - **Exact causes.** Illegal versus virtual instruction from VS/VU, and every legal xtval.
   - **Landing checks.** For successful accesses, check where a write landed (e.g. a VS-mode stimecmp write updates vstimecmp, not stimecmp), not only that nothing trapped.
   - **Similar mechanisms must not cross.** E.g. mtimecmp versus stimecmp.
   - **Microarchitecture.** Operand aliasing, x0 operands and destination, back-to-back dependencies on multi-cycle results, fusible sequences and their near misses, half-word and sign boundaries, RV32 high halves.
   - **CSR instruction forms.** All eight; rs1=x0 and uimm=0 are read-only.
4. **Write the generator** `tests_ai/gen/gen_<Suite>.py`. Mutant switches belong in the generator too (step 6).
5. **Run** `mise exec -- tests_ai/run_ai.sh <Suite> <config-dir>...`.
   - Configurations: Sail, Spike, Whisper, QEMU and Imperas (`-max`, rv32 and rv64), the RVI20U configs for M-only harts, and cvw RTL (`source ~/cvw/setup.sh` first).
   - Most first-run failures are generator bugs. A failure on every model is almost certainly yours.
   - Before calling something a DUT bug:
     - reduce it to a minimal reproducer (save it as `~/repros/YYYY-MM-DD-<topic>.tar.gz`) and double-check the reproducer's own pass/fail signaling;
     - check whether it is already known (comments in `config/<dut>/ci.yaml`, issue trackers);
     - check whether existing ACT suites already catch it (`make tests EXTENSIONS=...`, then run them).
   - Report new bugs to the user; never file them yourself.
6. **Mutation check.** Every mutant must make at least one test fail on a correct model. A surviving mutant means a gap: add the missing case, then re-run.
   - Arithmetic: wrap the generator's reference function, as `M_MUTANTS` in `gen/mutate.py` does.
   - Control and CSR semantics: read `AI_MUTANT` in the generator and flip one expectation per mutant (`SSTC_MUTANTS`).
   - Mutants model real bugs: wrong signedness, missing sign extension, signed or 32-bit comparison, an ignored enable, a leaked permission, a sticky bit, the wrong exception cause.
7. **Write `<Suite>/README.md`.** Keep it succinct, with three parts:
   - how the extension is tested;
   - every rule from step 1 that is not tested here, and why (another suite, untestable, or not yet generated);
   - subtleties, with issue links.
8. **Get an unanchored review.** Have a fresh agent check the skill's requirements and the spec text against a sample of tests: missing modes, missing legal outcomes, headers that don't match the code. Fix what it finds, then re-run steps 5 and 6.

## Privilege mode

- **Boot mode.** Boot to the extension's privilege: `boot="S"` for S-level extensions. Unprivileged tests set no boot mode and run in the lowest mode.
- **Changing modes.** Reach higher-privilege CSRs or memory through T-SBI (`tsbi_csr`, `RVTEST_TSBI_SW`). `t.window(mode, ...)` enters a lower mode (U, VS, VU from S; S, U from M) with `sret`/`mret` and returns with a T-SBI GOTO.
- **M-mode tests.** Tests that need M-mode (e.g. changing `mideleg`/`medeleg`) are separate `_Sm` files with `Sm` in `REQUIRED_EXTENSIONS` and `boot="M"`. Certification profiles without M-mode, such as RVA23, drop every test that requires Sm, so keep the rest of the rule out of that file.
- **Privilege-dependent rules** run at every mode where the outcome could differ: M (T-SBI or `_Sm`), S, U, and VS/VU under `only_if("defined(H_SUPPORTED)")`.

## Traps and interrupts: the trap log

- **Mechanism.** In these no-signature builds, the framework trap handlers (M, HS, VS) record every trap in the trap log and fail the test on any trap the test did not permit (`TRAP LOG` in `tests/env/rvtest_trap_handler.h`; macros in `common/ai_macros.h`). T-SBI calls and invisibly emulated instructions are not logged, so T-SBI works inside a window.
- **Windows.** `t.window(mode, lines, expect, desc, tval)` permits one trap, runs `lines` in `mode` (the first line is the instruction under test), and checks:
  - the number of traps and the cause; `expect` is "ok", a cause, or a list of up to three legal alternatives (e.g. `["ok", 4, 5]`);
  - for a trap: xepc is the instruction, xtval is one of `tval`, and xPP/xPV record `mode` as where the trap came from.
  - The checks on a trap are skipped when no trap is a legal outcome and none occurred.
- **Building blocks.** For anything `window()` does not fit, use `t.allow(n)`, the instructions, then `t.outcome(expect, lab, desc, tval, epc, origin)`. `AI_LOG(reg, TRAPLOG_*)` reads any word of the last entry: handler mode, cause, epc, tval, tval2, tinst, xstatus, mstatush/hstatus, resume address.
- **Resuming elsewhere.** The handler steps past the trapping instruction (or returns to `ra` after a fetch fault). Store an address in `rvtest_trap_resume` to resume there instead, e.g. after a jump to a faulting target.
- **Interrupts.**
  - Make the interrupt pending, open the window, then enable it or enter the mode. A pending interrupt can be taken at the xret itself.
  - Wait in a bounded loop, then call `outcome(cause or "ok", ..., epc=False, origin=mode)`: the epc of an interrupt is anywhere in the loop.
  - The framework handler masks the interrupt's xIE bit before returning, so re-enable it for the next case.

## Rules whose trapping depends on unknown parameters

Accept every legal outcome; use the trap log's fields to tell them apart. Typical outcome sets:

- **Misaligned load, store or AMO:** success, misaligned (4/6), or access fault (5/7). A trapping store may have written part of memory.
- **Optional CSR:** illegal-instruction (virtual-instruction from VS/VU), or no trap with a value that satisfies the WARL or read-only-zero rule. Branch later cases on the probed outcome.
- **WFI and Zawrs:** a NOP, waiting until an interrupt, or an illegal/virtual-instruction trap after a bounded time (TW/VTW). Keep the window open across a bounded wait.
- **Counters:** `time` and the other counters may be implemented, invisibly emulated, or trap, according to the counter-enable bits.
- **CBO with CBIE/CBCFE/CBZE:** illegal or virtual instruction; `cbo.inval` with CBIE=01 may act as a flush.
- **Svade/Svadu:** a page fault, or a hardware A/D update (check the PTE through a T-SBI load).
- **Stale translations or instructions** without `sfence.vma`/`fence.i`: old or new behavior.
- **PMP grain and PMA:** sub-grain accesses may or may not fault; probe the grain through pmpaddr (M tests). AMOs on regions without AMO support may fault.
- **Trap fields:**
  - xtval is 0 or the instruction bits for illegal instruction, and 0 or the address for misaligned accesses, access faults and breakpoints.
  - htval/mtval2 are 0 or GPA>>2; htinst/mtinst are 0, the transformed instruction, or the required pseudoinstruction.
  - Priority between simultaneous exceptions is fixed only where the spec says so.
- **Not yet supported by the framework:** a T-SBI CSR access that may trap (probing an optional M-level CSR from S, U or VS), and the fidelity of invisible-trap forwarding on DUTs that emulate instructions. Report rules that need these instead of working around them.

## Pitfalls seen so far

- **Checks.** Never check x4: AI_CHECK loads the expected value into x4 first, so the check compares x4 with itself.
  `check_masked` uses x5 as its temporary.
- **xtval of memory faults.** Page, guest-page, access and misaligned faults may write xtval = 0 (stval holds the
  address only "if written with a nonzero value"). For an access or fetch whose second page faults, a nonzero xtval is
  the page boundary. GVA must be 1 only when xtval is nonzero.
- **Framework state.** sscratch, vsscratch, mscratch, stvec and vstvec hold the trap handlers' state. Write them only
  with their own values, or save and restore them with no trap in between.
- **T-SBI table.** It has no mtval, mtval2, mtinst, mideleg or mstatush entries. Rules that need them are `_Sm` files.
- **Mutants.** A mutant must expect a wrong value that a correct model fails. A mutant that only loosens a check
  always survives.

- **CSR instruction forms.** Reference code must treat rs1=x0 and uimm=0 as "no write".
- **Field modulation.** A write that changes another field's legal values leaves that field UNSPECIFIED. Write it again before checking.
- **Time.** `time` cannot be stopped, so use margins (time + k·2^32), not equality. On RV32, order the timeh/time reads so a carry between them cannot make a "future" value past (or the reverse). Reading `time` below M-mode needs mcounteren.TM=1 and Zicntr.
- **Unexpected traps** fail at the trap with "Unexpected trap" and xcause/xepc/xtval. If one appears in a mode change, check that the window did not enter the mode with a pending, enabled interrupt you did not expect.
- **SIE after an xret.** An `sret` from HS-mode into VS or VU (or from S into U) copies SPIE into the returning mode's SIE, and the framework boots with SIE=1. Clear SIE before enabling an interrupt that HS- or S-mode must take only inside a window.
- **DUT bug triage.** QEMU rv32 fails every Sstc test that writes `henvcfgh` (illegal-instruction on `csrs henvcfgh`) because of known QEMU #4611 (mstateen0 writes clear mstateen0h.ENVCFG), which `config/qemu/ci.yaml` already excludes. Check known issues before reporting a bug.
