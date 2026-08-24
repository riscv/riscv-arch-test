##################################
# priv/pmp/suites/_pmpsm_walk.py
#
# PMPSm pmpcfg_walk family: WARL readback of every pmpcfg CSR bit.
# SPDX-License-Identifier: Apache-2.0
##################################

"""The ``pmpsm_pmpcfg_walk-*`` files of the PMPSm suite."""

from __future__ import annotations

from testgen.priv.pmp.macros import sigupd_count
from testgen.priv.pmp.model import XLENS, PmpFile, Xlen

#: Largest PMP entry count the architecture allows, used to size the signature region.
_MAX_PMP_ENTRIES = 64

#: The walking-one blocks step the pmpcfg CSR number by 2 and repeat
#: UDB_NUM_PMP_ENTRIES/8 times on both XLENs, so on RV32 they touch only the even
#: pmpcfg CSRs even though all 16 are implemented.
_WALK_REPT = "UDB_NUM_PMP_ENTRIES/8"
_WALK_STEP = 2
_WALK_REPS = _MAX_PMP_ENTRIES // 8

_COVERPOINT = "cp_pmpcfg_walk"

#: Bits skipped because W=1 with R=0 is reserved; the file keeps a comment for them.
_RESERVED_WR = 1
#: Bits skipped because they select A=NA4; the file passes over them silently.
_SILENT_NA4 = 4

_COPYRIGHT = (
    "// Copyright (C) 2025 Harvey Mudd College & Oklahoma State University, UET Lahore, Habib University",
    "// Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.",
    "// SPDX-License-Identifier: Apache-2.0",
    "//",
)

#: Title/Authors block, indented differently on each XLEN.
_HEADINGS = {
    32: (
        "// Title        : PMP configuration CSR walk verification\n"
        "// Authors      : Umer Shahid, Allen Baum, David Harris\n"
        "//                Muhammad Abdullah, Hamza Ali, Muhammad Zain\n"
        "//                Jordan Carlin"
    ),
    64: (
        "// Title           : PMP configuration CSR walk verification\n"
        "// Authors         : Umer Shahid, Allen Baum, David Harris\n"
        "//                  Muhammad Abdullah, Hamza Ali, Muhammad Zain\n"
        "//                  Jordan Carlin"
    ),
}

_DESCRIPTION_INTRO = "// Description : This test verifies WARL-safe writes to PMP configuration CSRs."

#: (description tail, "Test Cases" line) for each flavour of walk file.
_ZERO_ONLY = (
    "//               It writes zero to implemented pmpcfg CSRs and checks the\n//               readback signature.",
    "// Test Cases  : Write zero to pmpcfg CSRs and check readback.",
)
_WALKING_ONE = (
    (
        "//               It writes walking-one values to implemented pmpcfg CSRs and\n"
        "//               checks the readback signature."
    ),
    "// Test Cases  : Write walking-one values to pmpcfg CSRs and check readback.",
)
_ZERO_AND_WALKING_ONE = (
    (
        "//               It writes zero and walking-one values to implemented pmpcfg\n"
        "//               CSRs and checks the readback signature."
    ),
    "// Test Cases  : Write zero and walking-one values to pmpcfg CSRs and check readback.",
)

#: Coverage claim: the RV64 files claim full coverage, the RV32 files partial.
_COVERAGE = {
    32: f"// Coverpoints : {_COVERPOINT} for PMPSm is partially in\n//               this test file.",
    64: f"// Coverpoints : {_COVERPOINT} for PMPSm is fully covered in\n//               this test file.",
}

_EVEN_REGS_NOTE = (
    "",
    "    // -----------------------------------------------------------------------",
    "    // Walking ones through even pmpcfg registers (pmpcfg0, pmpcfg2, ...).",
    "    // Count of even pmpcfg registers:",
    "    //   16 PMPs -> 2 even regs (pmpcfg0, pmpcfg2)",
    "    //   64 PMPs -> 8 even regs (pmpcfg0 .. pmpcfg14, step 2)",
    "    // -----------------------------------------------------------------------",
)

#: Bit spans covered by each walk file, in file-name order.
_SPANS = {
    32: ((0, 2), (3, 9), (10, 16), (17, 23), (24, 30), (31, 31)),
    64: ((0, 5), (6, 11), (12, 19), (20, 26), (27, 33), (34, 40), (41, 47), (48, 54), (55, 61), (62, 63)),
}


def _banner(xlen: Xlen, flavour: tuple[str, str]) -> str:
    description, test_cases = flavour
    return "\n".join(
        (_HEADINGS[xlen.bits], "//", _DESCRIPTION_INTRO, description, "//", _COVERAGE[xlen.bits], "//", test_cases)
    )


def _zero_block(xlen: Xlen, label: str, heading: str) -> list[str]:
    """Write zero to every legal pmpcfg CSR and check the readback."""
    return [
        "",
        "    // -----------------------------------------------------------------------",
        f"    // {heading}",
        "    // -----------------------------------------------------------------------",
        "    .set pmpcfgi, CSR_PMPCFG0",
        f"    .rept {xlen.cfg_rept}",
        f"1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, x0, 1b, {label}_str)",
        f"    .set pmpcfgi, pmpcfgi+{xlen.cfg_step}",
        "    .endr",
    ]


def _walk_block(bit: int, label: str) -> list[str]:
    """Write ``1 << bit`` to every even pmpcfg CSR and check the readback."""
    note = " (MSB for RV64)" if bit == 63 else ""
    return [
        "",
        f"    // --- pmpcfg even walking ones, bit {bit}{note} ---",
        "",
        "    .set pmpcfgi, CSR_PMPCFG0",
        f"    .rept {_WALK_REPT}",
        f"1:  LI(t2, 1 << {bit})",
        f"    RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, {label}_str)",
        f"    .set pmpcfgi, pmpcfgi+{_WALK_STEP}",
        "    .endr",
    ]


def _skipped_block(bit: int) -> list[str]:
    return [
        "",
        f"    // --- pmpcfg even walking ones, bit {bit} ---",
        "    // Skipped, R=0,W=1 is reserved",
    ]


def _walk_span(span: tuple[int, int], first_index: int) -> tuple[list[str], list[tuple[str, str]]]:
    """Blocks and reporting strings for the bits of one file's span."""
    lines: list[str] = []
    sig_strs: list[tuple[str, str]] = []
    index = first_index
    for bit in range(span[0], span[1] + 1):
        if bit % 8 == _RESERVED_WR:
            lines.extend(_skipped_block(bit))
        elif bit % 8 == _SILENT_NA4:
            continue
        else:
            label = f"test_{index}"
            lines.extend(_walk_block(bit, label))
            sig_strs.append((label, f"write walking-one bit {bit} to even pmpcfg CSRs; cp: {_COVERPOINT}"))
            index += 1
    return lines, sig_strs


def _spec(
    xlen: Xlen,
    filename: str,
    flavour: tuple[str, str],
    body: list[str],
    sig_strs: list[tuple[str, str]],
    updates: int,
) -> PmpFile:
    return PmpFile(
        filename=filename,
        xlen=xlen,
        copyright=_COPYRIGHT,
        banner=_banner(xlen, flavour),
        required_extensions=("Sm",),
        params=("NUM_PMP_ENTRIES: '>0'",),
        sigupd=sigupd_count(updates),
        body=tuple(body),
        sig_strs=tuple(sig_strs),
    )


def _walk_file(xlen: Xlen, filename: str, span: tuple[int, int]) -> PmpFile:
    """One walking-ones file: enter M mode, walk the file's bit span, return to M mode."""
    lines, sig_strs = _walk_span(span, first_index=0)
    body = ["    RVTEST_GOTO_MMODE", *_EVEN_REGS_NOTE, *lines, "", "    RVTEST_GOTO_MMODE"]
    return _spec(xlen, filename, _WALKING_ONE, body, sig_strs, len(sig_strs) * _WALK_REPS)


def _rv32_first_file(xlen: Xlen) -> PmpFile:
    """RV32 file 1: zero all pmpcfg CSRs, then walk the first bits."""
    zero = _zero_block(xlen, "test_0", "SET ALL pmpcfg REGs to zero")
    lines, sig_strs = _walk_span(_SPANS[32][0], first_index=1)
    body = ["    RVTEST_GOTO_MMODE", *zero, *_EVEN_REGS_NOTE, *lines, "", "    RVTEST_GOTO_MMODE"]
    sig_strs = [("test_0", f"write zero to pmpcfg CSRs; cp: {_COVERPOINT}"), *sig_strs]
    updates = _MAX_PMP_ENTRIES // xlen.cfgs_per_reg + (len(sig_strs) - 1) * _WALK_REPS
    return _spec(xlen, "pmpsm_pmpcfg_walk-1.S", _ZERO_AND_WALKING_ONE, body, sig_strs, updates)


def _rv64_first_file(xlen: Xlen) -> PmpFile:
    """RV64 file 01: zero all pmpcfg CSRs; no walking ones, and no leading mode switch."""
    body = [*_zero_block(xlen, "test_0", "SET even pmpcfg CSRs to zero"), "", "    RVTEST_GOTO_MMODE"]
    sig_strs = [("test_0", f"write zero to even pmpcfg CSRs; cp: {_COVERPOINT}")]
    return _spec(xlen, "pmpsm_pmpcfg_walk-01.S", _ZERO_ONLY, body, sig_strs, _MAX_PMP_ENTRIES // xlen.cfgs_per_reg)


def build_walk_files() -> list[PmpFile]:
    """Every ``pmpsm_pmpcfg_walk-*`` file of the PMPSm suite, for both XLENs."""
    xlen32, xlen64 = XLENS[32], XLENS[64]
    specs = [_rv32_first_file(xlen32)]
    specs += [_walk_file(xlen32, f"pmpsm_pmpcfg_walk-{n}.S", span) for n, span in enumerate(_SPANS[32][1:], start=2)]
    specs.append(_rv64_first_file(xlen64))
    specs += [_walk_file(xlen64, f"pmpsm_pmpcfg_walk-{n:02d}.S", span) for n, span in enumerate(_SPANS[64], start=2)]
    return specs
