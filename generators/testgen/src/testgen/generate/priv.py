##################################
# generate/priv.py
#
# Privileged test generation orchestration.
# jcarlin@hmc.edu Jan 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Privileged test generation orchestration."""

from pathlib import Path
from random import seed

from testgen.asm.helpers import reproducible_hash
from testgen.data.config import TestConfig
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.io.writer import write_test_file
from testgen.priv.registry import (
    get_priv_test_defines,
    get_priv_test_generator,
    get_priv_test_march_extensions,
    get_priv_test_params,
    get_priv_test_required_extensions,
)

# ---------------------------------------------------------------------------
# Testsuites that need file splitting AND a per-file fast trap handler.
# These generate very large bodies (100k+ lines) that would overflow Sail's
# trap signature region if the standard framework handler were used.
# ---------------------------------------------------------------------------
_SPLIT_TESTSUITES: frozenset[str] = frozenset({"SsstrictSm", "SsstrictS", "SsstrictU"})

# Maximum body lines per generated .S file for split testsuites.
# 8000 lines keeps file count low (~10 files) which minimises per-file startup
# overhead on slower simulators (spike, QEMU).  Each file still completes in
# well under one second on Sail even when every instruction traps.
_LINES_PER_FILE: int = 8000

#     "// ── Fast illegal-instruction handler (prepended to every Ssstrict file) ────",
#     "// Handles ALL illegal instruction traps — writes mcause, mepc and mtval to",
#     "// signature on each trap, then advances mepc by 2 or 4.",
#     "//",
#     "// Assumptions:",
#     "//   - Machine mode has read access to the trapping instruction (PMP/physical",
#     "//     memory allows M-mode instruction reads at the faulting PC).",
#     "//   - Address translation is disabled (bare/Sv modes off) so the handler can",
#     "//     read the instruction word directly from mepc without manipulating",
#     "//     mstatus.MPRV.",
#     "//",
#     "// Instruction-width detection reads bits[1:0] from mepc directly.",
#     "// Width computation is branchless:",
#     "//   bits[1:0] = 0b11 (uncompressed) → advance = 4",
#     "//   bits[1:0] != 0b11 (compressed)  → advance = 2",
#     "//   Formula: advance = ((bits[1:0] >> 1) + 1) << 1",
#     "//",
#     "// Register usage:",
#     "//   t0 (x5)  — scratch throughout: CSR reads, instruction word, advance amount",
#     "//   t1 (x6)  — touched ONLY at the very end (csrr mepc / add / csrw) and in",
#     "//              the othertrap path.
_FAST_HANDLER_PREFIX: list[str] = [
    "\tj ssstrict_test_body",
    "",
    "\t.align 4",
    "trap_handler_fastillegalinstr:",
    "\tcsrr t0, mcause                 # read trap cause",
    "\tli   t1, 2                      # Illegal Instruction cause = 2",
    "\tbne  t0, t1, othertrap          # not illegal instruction — use regular handler",
    "illegalinstruction:",
    "\tSREG t0, 0(x2)                  # store mcause (=2) to signature",
    "\taddi x2, x2, SIG_STRIDE",
    "\tcsrr t0, mepc",
    "\tSREG t0, 0(x2)                  # store mepc to signature",
    "\taddi x2, x2, SIG_STRIDE",
    "\tcsrr t0, mtval",
    "\tSREG t0, 0(x2)                  # store mtval to signature",
    "\taddi x2, x2, SIG_STRIDE",
    "    # Branchless mepc advance — reads bits[1:0] from *mepc using lhu.",
    "    # lhu (not lw) is used because mepc is only guaranteed 2-byte aligned;",
    "    # a 4-byte lw at a 2n address would misalign on cores without HW misaligned",
    "    # support. bits[1:0] are sufficient for width detection and fit in 16 bits.",
    "    # PMP/MPRV: safe because Ssstrict tests run with full PMP permissions",
    "    # (R=1,W=1,X=1) and address translation disabled, so M-mode can always",
    "    # load from mepc without needing to set mstatus.MPRV.",
    "    # advance = (((bits[1:0]+1) >> 2) + 1) << 1  =  4 if bits[1:0]==0b11, else 2.",
    "    # (bits[1:0]+1)>>2 is 1 only for 0b11; all other values (0b10,0b01,0b00) give 0.",
    "\tcsrr t0, mepc",
    "\tlhu  t0, 0(t0)                  # load lower 16 bits from *mepc (always 2-byte aligned)",
    "\tandi t0, t0, 3                  # t0 = bits[1:0]",
    "\taddi t0, t0, 1                  # t0 = bits[1:0]+1; equals 4 only when was 0b11",
    "\tsrli t0, t0, 2                  # t0 = 1 iff uncompressed (0b11), else 0",
    "\taddi t0, t0, 1                  # t0 = 2 or 1",
    "\tslli t0, t0, 1                  # t0 = 4 (uncompressed) or 2 (compressed)",
    "\tcsrr t1, mepc                   # t1 = mepc  (t1 first written here)",
    "\tadd  t1, t1, t0                 # t1 = mepc + advance",
    "\tcsrw mepc, t1",
    "\tmret",
    "",
    "othertrap:",
    "\tcsrr t1, mtval",
    "\tj    Mtrampoline                # hand off all non-illegal-instruction traps",
    "",
    "ssstrict_test_body:",
    "\tLA(t0, trap_handler_fastillegalinstr)",
    "\tCSRW(mtvec, t0)",
    "\t.align 4",
    "",
]
_SPLIT_FILE_GPR_INIT: list[str] = (
    [
        "",
        "# Re-initialize GPRs at the top of every split Ssstrict file.",
        "# This ensures scratch base and safe registers are valid when a split",
        "# file begins in the middle of a large sweep.",
        "\t# x8 = permanent scratch base, 8-byte aligned for atomics",
        "\tnop",
        "\tnop",
        "\tla x8, scratch",
    ]
    + [f"\tmv x{r}, x8" for r in range(7, 32) if r != 8]
    + ["", ""]
)


def _split_at_blank(lines: list[str], max_lines: int) -> list[list[str]]:
    """Split lines into groups of ≤ max_lines, preferring blank-line boundaries."""
    if not lines:
        return [[]]
    groups: list[list[str]] = []
    start = 0
    while start < len(lines):
        end = min(start + max_lines, len(lines))
        if end == len(lines):
            groups.append(lines[start:])
            break
        # Search backwards up to 20 % of the window for a blank-line cut point
        search_from = max(start, end - max_lines // 5)
        split_at = end
        for i in range(end - 1, search_from - 1, -1):
            if lines[i].strip() == "":
                split_at = i + 1
                break
        groups.append(lines[start:split_at])
        start = split_at
    return groups


def generate_priv_test(testsuite: str, output_test_dir: Path) -> None:
    """
    Generate tests for a privileged testsuite.

    For most testsuites: produces a single SsstrictXx-00.S file (original
    behaviour, generate/priv.py unchanged from the framework default).

    For Ssstrict testsuites (SsstrictSm, SsstrictS, SsstrictU): splits the
    body into multiple ≤ _LINES_PER_FILE-line files and prepends the inline
    fast trap handler to every file.  This prevents the standard framework
    trap handler from overflowing the trap-signature region across the
    150k+ traps generated by the CSR and instruction-encoding sweeps.

    Args:
        testsuite: Testsuite name (e.g., \"ExceptionsSm\", \"SsstrictSm\")
        output_test_dir: Base directory to output generated tests
    """
    output_path = output_test_dir / "priv" / testsuite
    output_path.mkdir(parents=True, exist_ok=True)

    test_config = TestConfig(
        xlen=0,
        flen=64,
        testsuite=testsuite,
        E_ext=False,
        # config_dependent=True,
        required_extensions=get_priv_test_required_extensions(testsuite),
        march_extensions=get_priv_test_march_extensions(testsuite),
        extra_params=get_priv_test_params(testsuite),
    )

    test_data = TestData(test_config)
    tc = test_data.begin_test_chunk()

    # Reserve registers for priv tests:
    #   - x0: avoid so desired values are actually loaded into registers
    #   - x1/ra: used as the return address for function calls
    #   - x6, x7, x9: used by the RVTEST_GOTO_LOWER_MODE macro
    #   - x16-x31: ensure the same test can be used for I or E bases
    priv_exclude_regs = [0, 1, 6, 7, 9, *range(16, 32)]
    test_data.int_regs.consume_registers(priv_exclude_regs)
    seed(reproducible_hash(testsuite))

    priv_test_generator = get_priv_test_generator(testsuite)
    body_lines = priv_test_generator(test_data)

    test_data.int_regs.return_registers(priv_exclude_regs)
    tc.code = "\n".join(body_lines)
    test_data.end_test_chunk()

    # Produce actual test file
    extra_defines = [*get_priv_test_defines(testsuite)]
    write_test_file(test_config, None, [tc], output_path, extra_defines=extra_defines)

    if testsuite not in _SPLIT_TESTSUITES:
        # ── Standard single-file output (original behaviour) ──────────────────
        write_test_file(test_config, None, [tc], output_path, file_idx=0, extra_defines=extra_defines)
    else:
        # ── Ssstrict: split into multiple files with fast handler per file ─────
        #
        # SsstrictS/U files end in S-mode (the CSR sweep stays in S-mode until
        # RVTEST_CODE_END).  RVTEST_CODE_END issues an ecall (cause=9, s-call)
        # which Mtrampoline catches and routes through Mrtn2mmode → rtn_fm_mmode.
        # rtn_fm_mmode restores sp from the framework save area (offset 0x274).
        # That value was written when RVTEST_GOTO_LOWER_MODE Smode ran FROM M-MODE
        # at the start of this file's code section.
        #
        # Invariant enforced by SsstrictS.py's batch boundary layout:
        #   The splitter blank line is placed AFTER RVTEST_GOTO_LOWER_MODE Smode,
        #   not before it.  This guarantees that every split file's first code
        #   line (after the fast-handler prefix) is GOTO Smode executing from
        #   M-mode, which writes a valid M-mode sp into the save area.  When
        #   RVTEST_CODE_END later runs from S-mode, rtn_fm_mmode restores that
        #   valid sp and the epilog succeeds.
        #
        # Do NOT append a RVTEST_GOTO_LOWER_MODE Mmode suffix here.
        # On some configs (including RV32 sail-rv32-max) that macro is a
        # preprocessor no-op that generates zero machine code.  Appending it
        # does nothing useful, and the accompanying `csrw mie, x0` becomes
        # unreachable dead code that clutters the generated files.

        groups = _split_at_blank(body_lines, _LINES_PER_FILE)
        for file_idx, group in enumerate(groups):
            chunk = TestChunk()
            # Prepend the fast handler + per-file register init to EVERY file
            # so mtvec is always redirected to it and scratch registers are
            # reloaded at the start of each split body.
            chunk.code = "\n".join(_FAST_HANDLER_PREFIX + _SPLIT_FILE_GPR_INIT + group)
            # Count trap-inducing instructions in this group to size the
            # signature region correctly.  There are two kinds:
            #   1. _cg_ testcase labels — each precedes a CSR instruction that
            #      may trap (illegal CSR access).
            #   2. Raw .word/.hword directives — each IS an illegal instruction
            #      in the reserved-encoding sweeps; every one traps.
            # Each trap writes 4 signature words (mstatus, mcause, mepc, mtval).
            # Counting both kinds ensures that large compressed/vector sweeps
            # (thousands of .hword/.word lines, zero _cg_ labels) don't
            # overflow the signature region and corrupt the TRAP_CANARY.
            cg_count = sum(1 for line in group if line.strip().endswith(":") and "_cg_" in line)
            raw_instr_count = sum(
                1 for line in group if line.strip().startswith(".word ") or line.strip().startswith(".hword ")
            )
            chunk.sigupd_count = 4 * (cg_count + raw_instr_count)
            # Pass a COPY of extra_defines: insert_header_template() calls
            # extra_defines.extend(...) which mutates the list in-place.
            # Without a copy, each successive file accumulates duplicate
            # #define RVTEST_FP / #define rvtest_mtrap_routine lines.
            write_test_file(
                test_config,
                None,
                [chunk],
                output_path,
                file_idx=file_idx,
                extra_defines=extra_defines[:],
            )

    test_data.destroy()
