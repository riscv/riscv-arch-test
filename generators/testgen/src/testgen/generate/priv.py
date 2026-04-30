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
# 1000 lines keeps file count low (~80 files) which minimises per-file startup
# overhead on slower simulators (spike, QEMU).  Each file still completes in
# well under one second on Sail even when every instruction traps.
_LINES_PER_FILE: int = 1000

# Fast illegal-instruction trap handler, prepended to every split file.
#
# Why here and not in the generator?
# The generator body is split across many files. If the preamble is only in
# the generator's first lines it ends up only in file -00. Files -01, -02 ...
# start mid-body and have no mtvec override, so they use the standard framework
# handler (installed by RVTEST_TRAP_PROLOG). The standard handler writes 4 words
# to the trap-signature region on every trap; with 15k-150k expected traps the
# signature overflows, corrupting the signature pointer and causing Sail to enter
# an infinite fetch-fault loop.
#
# By prepending these lines to every split file we guarantee that mtvec is
# redirected to our fast handler at the start of every file's code section,
# after RVTEST_TRAP_PROLOG has already run.
#
# Handler design
# --------------
# mcause is checked FIRST, before touching any save area or general registers.
# - cause != 2: jump to Mtrampoline immediately with a clean CPU state.
#   Mtrampoline (exported .global from arch_test.h RVTEST_TRAP_HANDLER) is the
#   real framework handler — it handles store/fetch faults and epilog traps
#   correctly, ending the test cleanly when appropriate.
# - cause == 2 (illegal instruction): check mtval bits[1:0].
#   - bits[1:0] != 11 (compressed): Mtrampoline handles it.
#   - bits[1:0] == 11 (uncompressed): advance mepc+4 and mret directly.
#     Clobbers t0 and t1 only — acceptable for Ssstrict.
#
# The handler is defined before ssstrict_test_body: so that the LA() forward
# reference resolves within this single translation unit.
_FAST_HANDLER_PREFIX: list[str] = [
    "",
    "// ── Fast illegal-instruction handler (prepended to every Ssstrict file) ────",
    "// Handles ALL illegal instruction traps fast (no signature write).",
    "// 32-bit (bits[1:0]==11): advance mepc+4.",
    "// 16-bit (bits[1:0]!=11): advance mepc+2.",
    "// Any non-illegal trap: hand off to Mtrampoline (real framework handler).",
    "//",
    "// Uses ONLY t0 (x5). t1 (x6) is deliberately never touched: when",
    "// rvtest_strap_routine is defined (SsstrictS/U), x6 holds the Mtrampoline",
    "// trap-signature pointer. Clobbering it corrupts that pointer and causes",
    "// RVTEST_CODE_END signature-offset checks to fail.",
    "\tj ssstrict_test_body",
    "",
    "\t.align 4",
    "trap_handler_fastuncompressedillegalinstr:",
    "\tcsrr t0, mcause         # Check the cause",
    "\tli t1, 2                # Illegal Instruction cause = 2",
    "\tbne t0, t1, othertrap   # not illegal instruction, use regular handler",
    "illegalinstruction:",
    "\tcsrr t0, mtval          # get the faulting instruction encoding",
    "\tandi t0, t0, 3          # extract bits[1:0] into t0",
    "\tli t1, 3                # uncompressed marker = 0b11",
    "\tbeq t0, t1, uncompressedillegalinstructionreturn  # bits[1:0]==11 → uncompressed",
    "compressedillegalinstructionreturn:",
    "\tcsrr t0, mepc",
    "\taddi t0, t0, 2          # compressed: skip 2 bytes",
    "\tj doneillegalinstructionreturn",
    "uncompressedillegalinstructionreturn:",
    "\tcsrr t0, mepc",
    "\taddi t0, t0, 4          # uncompressed: skip 4 bytes",
    "doneillegalinstructionreturn:",
    "\tcsrw mepc, t0",
    "\tmret",
    "",
    "othertrap:",
    "\tcsrr t1, mtval",
    "\tbgez t0, Mtrampoline    # msb clear = exception, jump to full handler",
    "",
    "ssstrict_test_body:",
    "\tLA(t0, trap_handler_fastuncompressedillegalinstr)",
    "\tCSRW(mtvec, t0)",
    "\t.align 4",
    "",
]


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
            # Prepend the fast handler to EVERY file so mtvec is always
            # redirected to it at the start of each file's code section,
            # regardless of which part of the body the file contains.
            chunk.code = "\n".join(_FAST_HANDLER_PREFIX + group)
            # Count testcase labels in this group to set the correct
            # sigupd_count. Without this, write_test_file uses only
            # SIGUPD_MARGIN (=10), which overflows on RV32 when a CSR-sweep
            # file has hundreds of testcase labels (50 CSRs × 5 ops = 250).
            chunk.sigupd_count = sum(1 for line in group if line.strip().endswith(":") and "_cg_" in line)
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
