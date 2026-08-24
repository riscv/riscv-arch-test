##################################
# priv/pmp/suites/_pmpsm_cfg.py
#
# PMPSm cfg_* families: machine-mode pmpcfg A/L/XWR enforcement tests.
# SPDX-License-Identifier: Apache-2.0
##################################

"""The ``pmpsm_cfg_*`` files of the PMPSm suite."""

from __future__ import annotations

from collections.abc import Callable

from testgen.priv.pmp.macros import sigupd_count, test_case_str, zero_pmp_regs
from testgen.priv.pmp.model import XLENS, PmpFile, Xlen

_COPYRIGHT = (
    "// Copyright (C) 2025 Harvey Mudd College & Oklahoma State University, UET Lahore, Habib University",
    "// SPDX-License-Identifier: Apache-2.0",
    "//",
)

_HEADING = """
// Title           : Comprehensive PMP (Physical Memory Protection) Verification
// Authors         : Umer Shahid, Allen Baum, David Harris
//                  Muhammad Abdullah, Hamza Ali, Muhammad Zain
//
// Description : This test verifies the functionality and enforcement of
//               Physical Memory Protection (PMP) configurations in RISC-V
//               systems. It specifically tests the Read, Write, and Execute
//               permissions for a designated memory region, ensuring that
//               the PMP settings are correctly applied and that the system
//               behaves as expected when accessing this region.
//
"""

_HEADING_TOR_ZERO = """
// Title           : Comprehensive PMP (Physical Memory Protection) Verification
// Authors         : Umer Shahid, Allen Baum, David Harris
//                  Muhammad Abdullah, Hamza Ali, Muhammad Zain
//
// Description : This test verifies the functionality and enforcement of
//               Physical Memory Protection (PMP) configurations in RISC-V
//               systems. It checks that region 0 extends from 0 to pmpaddr0
//               in TOR mode.
//
"""

_EXTENSIONS = ("Sm",)

VERIFICATION_BANNER = "//                                            Verification Section"

_GOTO_MMODE = ["", "    RVTEST_GOTO_MMODE"]

_EXIT = [
    "",
    "    j exit                                                        // Verification Complete, exit the test",
    "exit:",
]

#: Address-mask defines used by every family that programs a NAPOT pmpaddr.
_MASK_DEFINES = [
    "#if UDB_PMP_GRANULARITY != 2",
    "    #define PMP_MASK            ~((1 << (UDB_PMP_GRANULARITY - 3))-1)",
    "    #define PMP_REGION_SIZE     (1 << (UDB_PMP_GRANULARITY - 3)) - 1",
    "#else",
    "    #define PMP_MASK            ~0",
    "    #define PMP_REGION_SIZE     0",
    "#endif",
]

_FILLER_COMMENT = (
    "              // one PMP granule of return-instruction fillers: places the region on the next "
    "granule boundary (= PMP_REGION_START at coverage grain 2), grain-aligned at larger grains"
)
_PAD_COMMENT = (
    "   // g_napot-byte pad -> NAPOT region-under-test at 0x80005008 (PMP_NAPOT_REGION_START); "
    "pmpaddr matches STANDARD_REGION, region does not cover the pad"
)
_RETURN_TRAMPOLINE = [
    "RETURN_INSTRUCTION:",
    "    nop",
    "    nop",
    (
        "    jr ra                                                        "
        "// Get back to the point from where TEST_FOR_EXECUTION was called."
    ),
]


def _banner(rest: str, heading: str = _HEADING) -> str:
    """One file's comment banner: the shared heading plus its Coverpoints/Test Cases text."""
    return f"{heading}{rest}"


def _params(*extra: str) -> tuple[str, ...]:
    """The NUM_PMP_ENTRIES gate every file carries, plus any address-mode gate."""
    return ("NUM_PMP_ENTRIES: '>0'", *extra)


def _zero_cfg_only(xlen: Xlen) -> list[str]:
    """Just the pmpcfg-clearing loop (cfg_A_all leaves the pmpaddr CSRs alone)."""
    return zero_pmp_regs(xlen)[:6]


def _data_tail(
    *,
    granule_top: bool = True,
    pad: str = "(1 << (UDB_PMP_GRANULARITY - 2))",
    pad_comment: str = _FILLER_COMMENT,
    granule_mid: bool = False,
    region: str = "(1<<(UDB_PMP_GRANULARITY))",
    region_insn: str = "nop",
) -> tuple[str, ...]:
    """The executable blob in the data section: a pad, the region under test, the trampoline."""
    lines = [".p2align 12"]
    if granule_top:
        lines.append(".p2align (UDB_PMP_GRANULARITY)")
    lines.extend(["TEST_FOR_EXECUTION_0:", f"    .rept {pad}{pad_comment}", "    jr ra", "    .endr", ""])
    if granule_mid:
        lines.append(".p2align (UDB_PMP_GRANULARITY)")
    lines.extend(["TEST_FOR_EXECUTION:", f"    .rept {region}", f"    {region_insn}", "    .endr", ""])
    lines.extend(_RETURN_TRAMPOLINE)
    return tuple(lines)


def _sig_strs(count: int, coverpoint: str) -> tuple[tuple[str, str], ...]:
    """``test_<n>_str`` reporting strings numbered 1..count, all naming one coverpoint."""
    return tuple((f"test_{n}", test_case_str(n, coverpoint)) for n in range(1, count + 1))


def _sig_strs_named(names: list[str]) -> tuple[tuple[str, str], ...]:
    """``test_<n>_str`` reporting strings, one coverpoint name per testcase."""
    return tuple((f"test_{n}", test_case_str(n, cp)) for n, cp in enumerate(names, start=1))


def _nop_const(xlen: Xlen) -> str:
    return "DOUBLE_NOP" if xlen.bits == 64 else "NOP"


# ---------------------------------------------------------------------------
# cfg_A_all: pmpcfg.A is writable in every region
# ---------------------------------------------------------------------------

_A_ALL_CASES = """// Coverpoints : cp_cfg_A_all for PMPM is fully covered in this test file.
//
// Test Cases  : Checking that A is writable in each region. For each standard
//               region, attempt to write pmpcfg.A={OFF, TOR, NA4, NAPOT} with
//               pmpcfg.L=0, pmpcfg.RWX = 000.  Only able to write NA4 if grain
//               G = 0. Other pmpcfg bits are writable.
"""

#: (A-mode constant, source register) for the four passes cfg_A_all makes over the pmpcfg CSRs.
_A_ALL_PASSES = [("NA4", "x4"), ("NAPOT", "x4"), ("TOR", "x4"), (None, "zero")]


def _a_all_value(xlen: Xlen, name: str) -> str:
    """The all-regions ``LI`` operand for one A mode; rv64 leaves the last term unshifted."""
    top = xlen.cfgs_per_reg - 1
    terms = [f"{name} << PMP{i}_CFG_SHIFT" for i in range(top, 0, -1)]
    terms.append(f"{name}" if xlen.bits == 64 else f"{name} << PMP0_CFG_SHIFT")
    return "|".join(terms)


def _a_all_body(xlen: Xlen) -> list[str]:
    """Write each A mode into every pmpcfg CSR and read it back."""
    csrs = [i * xlen.cfg_step for i in range(16 // xlen.cfg_step)]
    base = 4 // xlen.cfg_step  # pmpcfg CSRs present with the standard 16 PMP entries
    lines = [
        *_zero_cfg_only(xlen),
        "",
        "#define NAPOT   (PMP_NAPOT & 0xFF)",
        "#define TOR     (PMP_TOR   & 0xFF)",
        "#define NA4     (PMP_NA4   & 0xFF)",
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        VERIFICATION_BANNER,
        "// Test Case 1 : Setting region 0-14 to be NA4, NAPOT, TOR and OFF with L->0, XWR->000",
    ]
    n = 0
    for mode, src in _A_ALL_PASSES:
        lines.append("")
        if mode is not None:
            lines.append(f"    LI(x4, ({_a_all_value(xlen, mode)}))")
        for i, csr in enumerate(csrs):
            if i == base:
                lines.extend(["", ".if UDB_NUM_PMP_ENTRIES == 64"])
            n += 1
            lines.append(f"    test_{n}:")
            if xlen.bits == 32:
                lines.append(f"        # Write {src} to pmpcfg{csr}, read back and check against expected.")
            lines.append(f"        RVTEST_SIGUPD_CSR_WRITE(pmpcfg{csr}, {src}, test_{n}, test_{n}_str)")
        lines.append(".endif")
    lines.extend(["", "// ---------------------------------------------------------------------------"])
    return lines


def _a_all_files() -> list[PmpFile]:
    files = []
    for bits, granule_top in ((32, False), (64, True)):
        xlen = XLENS[bits]
        count = 64 // xlen.cfgs_per_reg * 4
        files.append(
            PmpFile(
                filename="pmpsm_cfg_A_all.S",
                xlen=xlen,
                copyright=_COPYRIGHT,
                banner=_banner(_A_ALL_CASES),
                required_extensions=_EXTENSIONS,
                params=_params(),
                priv_test=False,
                sigupd=sigupd_count(count),
                body=tuple(_a_all_body(xlen)),
                data_align=4,
                sig_strs=_sig_strs_named([f"cp_cfg_A_all_test_{n}" for n in range(1, count + 1)]),
                data=_data_tail(granule_top=granule_top),
            )
        )
    return files


# ---------------------------------------------------------------------------
# cfg_A_off_all: A=OFF never matches
# ---------------------------------------------------------------------------

_A_OFF_CASES = """// Coverpoints : cp_cfg_A_off_all for PMPM is fully covered in this test file.
//
// Test Cases  : Checking that A=OFF never matches for each region. For each
//               standard region with pmpcfg.L=1, pmpcfg.A=OFF, pmpcfg.XWR=000.
//               Fetching, reading and writing from that region. Should succeed
//               because region is off even though inaccessible.
"""

_A_OFF_MACRO = """
.macro VERIFICATION_RWX ADDRESS, TEST_CASE
    // Execution Access Check
    LA (a4, \\ADDRESS)
    LA(x1, 1f)                            // Store the return Address in x1
    RVTEST_FENCEI                              // sync I-cache: a prior store may have updated this executable region
    \\TEST_CASE\\()_3:
    jalr ra, 0(a4)
    RVTEST_SIGUPD(x2, x5, x4, a4, \\TEST_CASE\\()_3, test_3_str)               // Signature update for jalr
    nop
    nop
1:
    nop
    nop

    // Store Access Check
    LA(a5, \\ADDRESS)                                         // Address to be verified
    LI(a4, DOUBLE_NOP)                                              // Value to write (DOUBLE_NOP)
    \\TEST_CASE\\()_2:
    sw a4, 0(a5)                                             // Word store test
    RVTEST_SIGUPD(x2, x5, x4, a4, \\TEST_CASE\\()_2, test_2_str)               // Signature update for sw
    nop
    nop

    // Load Access Check
    \\TEST_CASE\\()_1:
    lw a4, 0(a5)                                             // Word load test
    RVTEST_SIGUPD(x2, x5, x4, a4, \\TEST_CASE\\()_1, test_1_str)               // Signature update for lw
    nop
    nop

.endm
"""


def _mask_block(li_open: str) -> list[str]:
    """Mask REGIONSTART down to a NAPOT pmpaddr value in x5, with this file's ``LI`` spelling."""
    return [
        "    LA(x5, REGIONSTART)",
        "    srl x5, x5, PMP_SHIFT",
        f"    {li_open}PMP_MASK)",
        "    and x5, x5, x6",
        f"    {li_open}PMP_REGION_SIZE)",
        "    or x5, x5, x6",
    ]


def _cfg_names(xlen: Xlen, entry: int) -> tuple[str, str]:
    """(pmpcfg CSR, PMPn_CFG_SHIFT) for one PMP entry."""
    return (
        f"pmpcfg{(entry // xlen.cfgs_per_reg) * xlen.cfg_step}",
        f"PMP{entry % xlen.cfgs_per_reg}_CFG_SHIFT",
    )


def _a_off_body(xlen: Xlen) -> list[str]:
    li_open = "LI(x6, " if xlen.bits == 64 else "LI(x6,"
    runner = "VERIFICATION_RWX" if xlen.bits == 64 else "PMP_VERIFICATION_RWX"
    region_comment = "        // RAM_BASE_ADDR + PROGRAM_SIZE" if xlen.bits == 64 else ""
    entries = list(range(14, -1, -1))
    if xlen.bits == 64:
        entries.append(0)  # test 16 repeats region 0
    lines = [
        *zero_pmp_regs(xlen),
        "",
        f"#define REGIONSTART            TEST_FOR_EXECUTION{region_comment}",
        *_MASK_DEFINES,
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        VERIFICATION_BANNER,
    ]
    for n, entry in enumerate(entries, start=1):
        csr, shift = _cfg_names(xlen, entry)
        lines.extend(
            [
                f"// Test Case: {n} -- No Permissions given to the PMP Region {entry}",
                "",
                *_mask_block(li_open),
                f"    csrw pmpaddr{entry}, x5",
                "",
                f"    LI(x4, (0x80 << {shift}))",
                f"    csrw {csr}, x4",
                "",
                "    RVTEST_SFENCE_VMA_IF_SUPPORTED",
                f"    {runner}    TEST_FOR_EXECUTION, test_{n}",
                *([] if n == len(entries) and xlen.bits == 64 else _GOTO_MMODE),
                "",
            ]
        )
    return lines


def _a_off_files() -> list[PmpFile]:
    files = []
    for bits in (32, 64):
        xlen = XLENS[bits]
        cases = 16 if bits == 64 else 15
        names = (
            ["cp_cfg_A_off_all_lw", "cp_cfg_A_off_all_sw", "cp_cfg_A_off_all_x"]
            if bits == 64
            else ["pmpm_cfg_A_off_all_jalr", "pmpm_cfg_A_off_all_sw", "pmpm_cfg_A_off_all_lw"]
        )
        files.append(
            PmpFile(
                filename="pmpsm_cfg_A_off_all.S",
                xlen=xlen,
                copyright=_COPYRIGHT if bits == 64 else (),
                banner=_banner(_A_OFF_CASES),
                required_extensions=_EXTENSIONS,
                params=_params(),
                priv_test=False,
                sigupd=sigupd_count(cases * 3),
                macro_blocks=(_A_OFF_MACRO,) if bits == 64 else (),
                body=tuple(_a_off_body(xlen)),
                data_align=4,
                sig_strs=_sig_strs_named(names),
                data=_data_tail(granule_top=bits == 64, pad="PMP_NAPOT_REGION_PAD_WORDS", pad_comment=_PAD_COMMENT),
            )
        )
    return files


# ---------------------------------------------------------------------------
# cfg_A_tor_bot: region 1 extends from pmpaddr0 to pmpaddr1
# ---------------------------------------------------------------------------

_A_TOR_BOT_CASES = """// Coverpoints : cp_cfg_A_tor_bot for PMPM is fully covered in this test file.
//
// Test cases  : In this test, we check that region 1 extends from pmpaddr0 to
//                pmpaddr1. We set up a default TOR region, then make accesses
//                {lw,sw,jalr} at addresses {pmpadr0-4, pmpadr0, pmpadr1-4, pmpadr1}.
//
//                Test case 1: pmpcfg1.L=1, pmpcfg1.A = TOR, pmpcfg1.XWR=101,
//               pmpcfg0.L = 0, pmpcfg0.A = OFF, pmpcfg0.XWR = 000
//
//              Test case 2: pmpcfg1.L=1, pmpcfg1.A = TOR, pmpcfg1.XWR=101,
//               pmpcfg0.L = 1, pmpcfg0.A = OFF, pmpcfg0.XWR = 000
"""

#: (address expression, opcode) for the eight data probes cfg_A_tor_bot makes.
_A_TOR_BOT_PROBES = [
    ("\\ADDRESS-4", "sw"),
    ("\\ADDRESS", "sw"),
    ("(\\ADDRESS+g)-4", "sw"),
    ("\\ADDRESS+g", "sw"),
    ("\\ADDRESS-4", "lw"),
    ("\\ADDRESS", "lw"),
    ("(\\ADDRESS+g)-4", "lw"),
    ("\\ADDRESS+g", "lw"),
]

_FENCEI_COMMENT = "                              // sync I-cache: a prior store may have updated this executable region"


def _a_tor_bot_macro(xlen: Xlen) -> str:
    nop = _nop_const(xlen)
    lines = [
        ".macro VERIFICATION_RWX ADDRESS, TEST_CASE",
        "",
        f"    LI(a4, {nop})                                      // Value to write ({nop})",
    ]
    for n, (addr, op) in enumerate(_A_TOR_BOT_PROBES, start=1):
        comment = "word-level store test" if op == "sw" else "Word load test"
        lines.extend(
            [
                "",
                f"    LA(a5, ({addr}))                                // Address to be verified",
                f"    \\TEST_CASE\\()_{n}:",
                f"    {op} a4, 0(a5)                                            // {comment}",
                "    nop",
                f"    RVTEST_SIGUPD(x2, x5, x4, a4, \\TEST_CASE\\()_{n}, test_{n}_str)",
            ]
        )
    # rv64 fences once before the jump probes; rv32 fences inside the first one.
    if xlen.bits == 64:
        lines.extend(["", "   RVTEST_FENCEI"])
    for n, addr in enumerate(["\\ADDRESS-4", "\\ADDRESS", "(\\ADDRESS+g)-4", "\\ADDRESS+g"], start=1):
        lines.extend(
            [
                "",
                f"    LA (a4, ({addr}))",
                f"    LA(x1, {n}f)                            // Store the return Address in x1",
            ]
        )
        if xlen.bits == 32 and n == 1:
            lines.append(f"    RVTEST_FENCEI{_FENCEI_COMMENT}")
        lines.extend(["    jalr ra, 0(a4)", "    nop", f"{n}:", "    nop"])
    lines.extend(["", ".endm"])
    return "\n".join(lines)


def _a_tor_bot_body(xlen: Xlen) -> list[str]:
    return [
        *zero_pmp_regs(xlen),
        "",
        "#define PMPREGION_UPPER_BOUND        ((((PMP_L|PMP_R      |PMP_X|PMP_TOR)  &0xFF) << PMP1_CFG_SHIFT))",
        "#define PMPREGION_LOWER_BOUND        ((((PMP_L)                            &0xFF) << PMP0_CFG_SHIFT))",
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        "    // x4 = base address of TEST_FOR_EXECUTION (must be g-byte aligned)",
        "    // x5 = x4 + g (upper bound, also g-byte aligned)",
        "    // After >> PMP_SHIFT (>>2): bit[0] of pmpaddr will be 0",
        "    LA(x4, TEST_FOR_EXECUTION)",
        "    LI(t0, g)",
        "    add      x5, x4, t0",
        "    srl      x4, x4, PMP_SHIFT",
        "    srl      x5, x5, PMP_SHIFT",
        "",
        "    csrw     pmpaddr0, x4",
        "    csrw     pmpaddr1, x5",
        "",
        VERIFICATION_BANNER,
        "// Test Case: 1",
        "",
        "    LI(x4, PMPREGION_UPPER_BOUND)",
        "    csrw pmpcfg0, x4",
        "",
        "    RVTEST_SFENCE_VMA_IF_SUPPORTED",
        "    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_1",
        "",
        "// Test Case: 2",
        "",
        "    LI(x4, PMPREGION_UPPER_BOUND)",
        "    csrw pmpcfg0, x4",
        "    LI(x4, PMPREGION_LOWER_BOUND)",
        "    csrw pmpcfg0, x4",
        "",
        "    RVTEST_SFENCE_VMA_IF_SUPPORTED",
        "    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_2",
        *_GOTO_MMODE,
    ]


def _a_tor_bot_files() -> list[PmpFile]:
    names = [
        f"pmpm_cfg_A_tor_bot_{kind}_access_at_pmpaddr{bound}{sign}"
        for kind in ("store", "load")
        for bound, sign in (("0", "-4"), ("0", "+4"), ("1", "-4"), ("1", "+4"))
    ]
    files = []
    for bits in (32, 64):
        xlen = XLENS[bits]
        tail = (
            _data_tail(
                pad="((1<<(UDB_PMP_GRANULARITY))>>2)",
                pad_comment="",
                granule_mid=True,
                region="((1<<(UDB_PMP_GRANULARITY))>>2)",
                region_insn="jr ra",
            )
            if bits == 64
            else _data_tail()
        )
        files.append(
            PmpFile(
                filename="pmpsm_cfg_A_tor_bot.S",
                xlen=xlen,
                copyright=_COPYRIGHT,
                banner=_banner(_A_TOR_BOT_CASES),
                required_extensions=_EXTENSIONS,
                params=_params("PMP_TOR_SUPPORTED: true"),
                priv_test=False,
                sigupd=sigupd_count(16),
                macro_blocks=(
                    "#define g         (1<<(UDB_PMP_GRANULARITY))",
                    _a_tor_bot_macro(xlen),
                ),
                body=tuple(_a_tor_bot_body(xlen)),
                data_align=4,
                sig_strs=_sig_strs_named(names),
                data=tail,
            )
        )
    return files


# ---------------------------------------------------------------------------
# cfg_A_tor_zero: region 0 extends from address 0 to pmpaddr0
# ---------------------------------------------------------------------------

_A_TOR_ZERO_CASES = """// Coverpoints:  cp_cfg_A_tor0 for PMPM is fully covered in this test file.
//
// Test Cases  : Checking region 0 extends from 0 to pmpaddr0 in TOR mode.
//                 Dropping the background region. With pmpcfg0.L=1, pmpcfg0.A=TOR,
//                 pmpcfg0.XWR=111, default TOR region: {lw, sw, jalr} to {0,
//                 pmpaddr0-4, pmpaddr0}.
"""


def _a_tor_zero_macro(xlen: Xlen) -> str:
    nop = _nop_const(xlen)
    lines = [
        ".macro VERIFICATION_RWX ADDRESS, TEST_CASE",
        "",
        f"    LI(a4, {nop})                                              // Value to write ({nop})",
    ]
    for n, (addr, op) in enumerate(
        [("\\ADDRESS", "sw"), ("\\ADDRESS-4", "sw"), ("\\ADDRESS", "lw"), ("\\ADDRESS-4", "lw")], start=1
    ):
        comment = "word-level store test" if op == "sw" else "Word load test"
        lines.extend(
            [
                "",
                f"    LA(a5, ({addr}))                                         // Address to be verified",
                f"    \\TEST_CASE\\()_{n}:",
                f"    {op} a4, 0(a5)                                             // {comment}",
                "    nop",
                f"    RVTEST_SIGUPD(x2, x5, x4, a4,\\TEST_CASE\\()_{n},test_{n}_str)               // Signature update",
            ]
        )
        if n == 2:
            lines.extend(
                [
                    "",
                    (
                        "    LI(a4, 0x00008067)                                       // ret (jalr x0, 0(ra)):"
                        " on cores where addr 0 is mapped RAM the store lands and the later execute probe at 0"
                        " must return"
                    ),
                    "    LI(a5, 0)",
                    "    LA(x1, 4f)                                               // Address to be verified",
                    "    sw a4, 0(a5)                                             // word-level store test",
                    "    nop",
                    "4:",
                    "    nop",
                ]
            )
        if n == 4:
            lines.extend(
                [
                    "",
                    "    LA(x1, 5f)",
                    "    LI(a5, 0)                                                   // Address to be verified",
                    "    lw a4, 0(a5)                                             // word-level store test",
                    "    nop",
                    "",
                    "5:",
                    "    nop",
                ]
            )
    lines.extend(
        [
            "",
            "    LA (a4, (\\ADDRESS))",
            "    LA(x1, 1f)                                                // Store the return Address in x1",
            f"    RVTEST_FENCEI{_FENCEI_COMMENT}",
            "    jalr ra, 0(a4)",
            "    nop",
            "1:",
            "    nop",
            "",
            "    LA (a4, (\\ADDRESS-4))",
            "    LA(x1, 2f)                            // Store the return Address in x1",
            "    jalr ra, 0(a4)",
            "    nop",
            "2:",
            "    nop",
            "",
            "    LI(a5, 0)",
            "    LA(x1, 3f)                            // Store the return Address in x1",
            "    jalr ra, 0(a5)",
            "    nop",
            "3:",
            "    nop",
            "",
            ".endm",
        ]
    )
    return "\n".join(lines)


def _a_tor_zero_body(xlen: Xlen) -> list[str]:
    return [
        *zero_pmp_regs(xlen),
        "",
        "#define PMPREGION_TOR                 ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_TOR)&0xFF)   << PMP0_CFG_SHIFT))",
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        "    LA(x4, TEST_FOR_EXECUTION)",
        "    srl x4, x4, PMP_SHIFT",
        "    csrw     pmpaddr0, x4",
        "",
        VERIFICATION_BANNER,
        "// Test Case 1: Default TOR region with XWR permissions",
        "",
        "    LI(x4, PMPREGION_TOR)",
        "    csrw pmpcfg0, x4",
        "",
        "    RVTEST_SFENCE_VMA_IF_SUPPORTED",
        "    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_1",
        *_GOTO_MMODE,
    ]


def _a_tor_zero_files() -> list[PmpFile]:
    names = [
        "pmpm_cfg_A_tor_zero_store_access_at_pmpaddr0",
        "pmpm_cfg_A_tor_zero_store_access_at_pmpaddr0-4",
        "pmpm_cfg_A_tor_zero_load_access_at_pmpaddr0",
        "pmpm_cfg_A_tor_zero_load_access_at_pmpaddr0-4",
    ]
    files = []
    for bits in (32, 64):
        xlen = XLENS[bits]
        files.append(
            PmpFile(
                filename="pmpsm_cfg_A_tor_zero.S",
                xlen=xlen,
                copyright=_COPYRIGHT,
                banner=_banner(_A_TOR_ZERO_CASES, _HEADING_TOR_ZERO),
                required_extensions=_EXTENSIONS,
                params=_params("PMP_TOR_SUPPORTED: true"),
                priv_test=False,
                extra_defines=("#define SKIP_MTVAL",),
                sigupd=sigupd_count(4),
                macro_blocks=(_a_tor_zero_macro(xlen),),
                body=tuple(_a_tor_zero_body(xlen)),
                data_align=4 if bits == 64 else None,
                sig_strs=_sig_strs_named(names),
                data=_data_tail(granule_mid=bits == 32),
            )
        )
    return files


# ---------------------------------------------------------------------------
# cfg_L_access_all: L=0 never restricts M-mode
# ---------------------------------------------------------------------------

_L_ACCESS_CASES = """// Coverpoints : cp_cfg_L_access_all & cp_none for PMPM are fully covered in
//                 this test file.
//
// Test Cases  : Checking M-mode access when all PMP are off. Checking that XWR
//                 doesn't affect M-mode access when L=0. Setting (PMP_writable_regs-1)
//                 as standard PMP regions, with pmp.L = 0, pmp.A=NAPOT, pmp.XWR = 0
//                 {jalr, lw, sw} in each PMP region. Access should always succeed
//                 because L=0 doesn't enforce permissions.
"""

_L_ACCESS_MACRO = """
.macro VERIFICATION_RWX ADDRESS, TEST_CASE      // {jalr, sw, lw} at start of region (0x80002000)
    // Execution Access Check
    LA (a4, \\ADDRESS)
    LA(x1, 1f)                            // Store the return Address in x1
    RVTEST_FENCEI                              // sync I-cache: a prior store may have updated this executable region
    jalr ra, 0(a4)
    nop
    nop
1:
    nop
    nop

    // Store Access Check
    LA(a5, \\ADDRESS)                        // Address to be verified
    LI(a4, @NOP@)                                // Value to write (@NOP@)
    \\TEST_CASE\\()_2:
    sw a4, 0(a5)                            // Word store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \\TEST_CASE\\()_2, test_2_str)

    // Load Access Check
    \\TEST_CASE\\()_1:
    lw a4, 0(a5)                            // Word load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \\TEST_CASE\\()_1, test_1_str)     // Signature update

.endm
"""


def _l_access_body(xlen: Xlen) -> list[str]:
    li_open = "LI (x6, " if xlen.bits == 64 else "LI(x6,"
    target = "REGIONSTART" if xlen.bits == 64 else "TEST_FOR_EXECUTION"
    region_comment = "        // RAM_BASE_ADDR + PROGRAM_SIZE" if xlen.bits == 64 else ""
    lines = [
        *zero_pmp_regs(xlen),
        "",
        VERIFICATION_BANNER,
        "    RVTEST_SFENCE_VMA_IF_SUPPORTED",
        "",
        "// Test Case: 0 -- M-mode access succeeds when all PMP are off",
        "    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_0",
        "    RVTEST_GOTO_MMODE",
        "",
        "#define PMPREGION_XWR_000   ((                        PMP_NAPOT)&0xFF)",
        "",
        f"#define REGIONSTART            TEST_FOR_EXECUTION{region_comment}",
        *_MASK_DEFINES,
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        VERIFICATION_BANNER,
    ]
    for n, entry in enumerate(range(14, -1, -1), start=1):
        csr, shift = _cfg_names(xlen, entry)
        block = _mask_block(li_open)
        block[0] = f"    LA(x5, {target})"
        lines.extend(
            [
                f"// Test Case: {n} : L -> 0 and No Permissions given to the PMP Region {entry}",
                "",
                *block,
                f"    csrw pmpaddr{entry}, x5",
                "",
                f"    LI(x4, (PMPREGION_XWR_000 << {shift}))",
                f"    csrw {csr}, x4",
                "",
                "    RVTEST_SFENCE_VMA_IF_SUPPORTED",
                f"    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_{n}",
                "",
            ]
        )
    return lines


def _l_access_files() -> list[PmpFile]:
    names = ["cp_cfg_L_access_all_lw and cp_none_lw", "cp_cfg_L_access_all_sw and cp_none_sw"]
    files = []
    for bits in (32, 64):
        xlen = XLENS[bits]
        files.append(
            PmpFile(
                filename="pmpsm_cfg_L_access_all.S",
                xlen=xlen,
                copyright=_COPYRIGHT,
                banner=_banner(_L_ACCESS_CASES),
                required_extensions=_EXTENSIONS,
                params=_params(),
                priv_test=False,
                sigupd=sigupd_count(32),
                macro_blocks=(_L_ACCESS_MACRO.replace("@NOP@", _nop_const(xlen)),),
                body=tuple(_l_access_body(xlen)),
                data_align=4 if bits == 64 else None,
                sig_strs=_sig_strs_named(names),
                data=_data_tail(granule_top=bits == 64, pad="PMP_NAPOT_REGION_PAD_WORDS", pad_comment=_PAD_COMMENT),
            )
        )
    return files


# ---------------------------------------------------------------------------
# cfg_L_modify_{off,tor,napot}: locked entries reject writes
# ---------------------------------------------------------------------------


def _l_modify_banner(amode: str, prev_lock: str, addr: str, i_lock: str) -> str:
    return f"""// Coverpoints : cp_cfg_L_modify for PMPM is partially covered in this test file.
//
// Test Cases  : Checking that pmpcfg and pmpaddr are unwritable when L = 1.
//               With pmpcfg_i.L ={{0/1}}, pmpcfg_i.A = {amode}, pmpcfg_i.XWR = 111,
//               pmpaddr_i = 0x100, trying to change pmpcfg_i to 000000000,
//               and to change pmpaddr_i to 0s, and reading these back.
//               When L = 1, should be unchanged because of lock.
//               When L = 0, changeable.
//
//               Checking that pmpcfg and pmpaddr of previous region are unwritable
//               when {prev_lock}. With pmpcfg_i.L{i_lock}{{0/1}}, pmpcfg_i.A={amode}, pmpcfg_i.XWR=111,
//               {addr}, pmpcfg_i-1.L = 0 trying to change pmpcfg_i-1 to
//               00000111, and to change pmpaddr_i-1 to 1s and reading these back.
//               pmpaddr_i-1 should be unchanged because of lock iff pmpcfg_i.A = TOR,
//               otherwise change. pmpcfg_i-1 is changeable independent of pmpcfg_i.A.
"""


#: amode -> (test name suffix, PMP_* constant, params gate, banner text, coverpoint name template)
_L_MODIFY_VARIANTS = {
    "off": ("OFF", "", (), "cp_cfg_L_modify_{n}"),
    "tor": ("TOR", "|PMP_TOR", ("PMP_TOR_SUPPORTED: true",), "cp_cfg_L_modify"),
    "napot": ("NAPOT", "|PMP_NAPOT", ("PMP_NAPOT_SUPPORTED: true",), "cp_cfg_L_modify_test_{n}"),
}


def _l_modify_body(xlen: Xlen, amode_name: str, amode_const: str) -> list[str]:
    lines = [*zero_pmp_regs(xlen), "", "    RVTEST_PMP_SET_BACKGROUND x4", "", VERIFICATION_BANNER]
    for case, (lock, n0) in enumerate([("0", 0), ("1", 8)], start=1):
        perms = "PMP_L|PMP_R|PMP_W|PMP_X" if lock == "1" else "PMP_R|PMP_W|PMP_X"
        lines.extend(
            [
                (
                    f"// Test Case {case} : Setting region 1 to be {amode_name} with L->{lock},"
                    " XWR->111 and pmpaddr->0x100"
                ),
                "",
                "    addi x4, x0, 0x100",
                f"    test_{n0 + 1}:",
                "        # Write x4 to pmpaddr1, read back and check against expected.",
                f"        RVTEST_SIGUPD_CSR_WRITE(pmpaddr1, x4, test_{n0 + 1}, test_{n0 + 1}_str)",
                "",
                f"    LI(x4, (({perms}{amode_const})&0xFF) << PMP1_CFG_SHIFT)",
                f"    test_{n0 + 2}:",
                "        # Write x4 to pmpcfg0, read back and check against expected.",
                f"        RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, x4, test_{n0 + 2}, test_{n0 + 2}_str)",
                "",
                "        // Now trying to change pmp0cfg0 to 000000111, and to change pmpaddr0 to 1s.",
                "",
                "    addi x5, x4, 7",
                f"    test_{n0 + 3}:",
                "        # Write x5 to pmpcfg0, read back and check against expected.",
                f"        RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, x5, test_{n0 + 3}, test_{n0 + 3}_str)",
                "",
                "    addi x4, x0,-1",
                f"    test_{n0 + 4}:",
                "        # Write x4 to pmpaddr0, read back and check against expected.",
                f"        RVTEST_SIGUPD_CSR_WRITE(pmpaddr0, x4, test_{n0 + 4}, test_{n0 + 4}_str)",
                "",
                "// Now trying to change pmp1cfg0 to 000000000, and to change pmpaddr1 to 0s.",
                "",
                f"    test_{n0 + 5}:",
                "        # Write x0 to pmpaddr1, read back and check against expected.",
                f"        RVTEST_SIGUPD_CSR_WRITE(pmpaddr1, x0, test_{n0 + 5}, test_{n0 + 5}_str)",
                "",
                f"    test_{n0 + 6}:",
                "        # Write x0 to pmpcfg0, read back and check against expected.",
                f"        RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, x0, test_{n0 + 6}, test_{n0 + 6}_str)",
                "",
            ]
        )
        if case == 1:
            lines.extend(
                [
                    "",
                    "//--- Re-initialize the CSRs. ---",
                    "    test_7:",
                    "        # Write x0 to pmpaddr0, read back and check against expected.",
                    "        RVTEST_SIGUPD_CSR_WRITE(pmpaddr0, x0, test_7, test_7_str)",
                    "",
                    "    test_8:",
                    "        # Write x0 to pmpcfg0, read back and check against expected.",
                    "        RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, x0, test_8, test_8_str)",
                    "    //-------------------------------",
                    "",
                ]
            )
    lines.append("// ---------------------------------------------------------------------------")
    return lines


def _l_modify_files() -> list[PmpFile]:
    banners = {
        "off": _l_modify_banner("OFF", "L=1", "pmpaddr_i = 0x100", "="),
        "tor": _l_modify_banner("TOR", "L=1", "pmpaddr_i=0x100", " ="),
        "napot": _l_modify_banner("NAPOT", "L = 1", "pmpaddr_i = 0x100", "="),
    }
    files = []
    for amode, (name, const, gate, cp) in _L_MODIFY_VARIANTS.items():
        for bits in (32, 64):
            xlen = XLENS[bits]
            files.append(
                PmpFile(
                    filename=f"pmpsm_cfg_L_modify_{amode}.S",
                    xlen=xlen,
                    copyright=_COPYRIGHT,
                    banner=_banner(banners[amode]),
                    required_extensions=_EXTENSIONS,
                    params=_params(*gate),
                    priv_test=False,
                    sigupd=sigupd_count(14),
                    body=tuple(_l_modify_body(xlen, name, const)),
                    data_align=None if (bits == 32 and amode == "off") else 4,
                    sig_strs=_sig_strs_named([cp.format(n=n) for n in range(1, 15)]),
                    data=_data_tail(
                        granule_top=bits == 64,
                        pad="PMP_NAPOT_REGION_PAD_WORDS" if amode == "napot" else "(1 << (UDB_PMP_GRANULARITY - 2))",
                        pad_comment=_PAD_COMMENT if amode == "napot" else _FILLER_COMMENT,
                    ),
                )
            )
    return files


# ---------------------------------------------------------------------------
# cfg_XWR_all: every legal XWR encoding in every region
# ---------------------------------------------------------------------------

_XWR_CASES = """// Coverpoints : cp_cfg_X0_all, cp_cfg_X1_all, cp_cfg_RW00_all, cp_cfg_RW10_all
//                 and cp_cfg_RW11_all for PMPM is partially covered in this file.
//
// Test Cases  : Rolling legal XWR starting from region with lowest priority i.e.,
//               region 14 to region with highest priority i.e., region 0 such
//               that each of the writable registers gets each of the 6 legal
//               combinations at least once.
"""

_XWR_DEFINES = [
    "#define PMPREGION_XWR_000   ((PMP_L|                  PMP_NAPOT)&0xFF)",
    "#define PMPREGION_XWR_100   ((PMP_L|            PMP_X|PMP_NAPOT)&0xFF)",
    "#define PMPREGION_XWR_001   ((PMP_L|PMP_R|            PMP_NAPOT)&0xFF)",
    "#define PMPREGION_XWR_101   ((PMP_L|PMP_R|      PMP_X|PMP_NAPOT)&0xFF)",
    "#define PMPREGION_XWR_011   ((PMP_L|PMP_R|PMP_W      |PMP_NAPOT)&0xFF)",
    "#define PMPREGION_XWR_111   ((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF)",
]

#: XWR code -> the wording the `// Test Case:` comment uses for it.
_XWR_PERMS = {
    "000": "No Permissions",
    "100": "X Permissions",
    "001": "R Permissions",
    "101": "XR Permissions",
    "011": "WR Permissions",
    "111": "XWR Permissions",
}

#: rv32 file -> (first testcase number, XWR code per region 14..0), and per-file comment quirks.
_XWR32_CODES = {
    "01": (1, "000 100 001 101 011 111 000 100 001 101 011 111 000 100 001"),
    "02": (16, "101 011 111 000 100 001 101 011 111 000 100 001 101 011 111"),
    "03": (1, "111 001 101 001 100 000 111 001 101 001 101 000 111 001 101"),
    "04": (16, "001 100 000 111 001 101 001 100 000 111 011 101 001 100 000"),
}
#: rv64 file -> (first testcase number, XWR code per region, count).
_XWR64_CODES = {
    "01": (1, "000 100 001 101 011 111 000 100"),
    "02": (9, "001 101 011 111 000 100 001"),
    "03": (16, "101 011 111 000 100 001 101 011 111"),
    "04": (25, "000 100 001 101 011 111"),
    "05": (1, "111 001 101 001 100 000 111 001"),
    "06": (9, "101 001 101 000 111 001 101"),
    "07": (16, "001 100 000 111 001 101 001 100 000"),
    "08": (25, "111 011 101 001 100 000"),
}
#: `// Test Case:` permission wordings that disagree with the encoding actually written.
_XWR_COMMENT_FIXUPS = {(32, "01", 11): "XR Permissions", (64, "02", 11): "XR Permissions"}
#: rv32-02 writes three of its LI operands without a space before `<<`.
_XWR_TIGHT_SHIFT = {(32, "02", 21), (32, "02", 25), (32, "02", 29)}


def _xwr_body(xlen: Xlen, key: str, first: int, codes: list[str], sep: str, exit_block: bool) -> list[str]:
    lines = [
        *zero_pmp_regs(xlen),
        "",
        *_XWR_DEFINES,
        "",
        "",
        "#define PMPADDRESS            TEST_FOR_EXECUTION                              // Test section address",
        *_MASK_DEFINES,
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        "    LA(x4, PMPADDRESS)",
        "    srl x4, x4, PMP_SHIFT",
        "",
        ".if UDB_PMP_GRANULARITY != 2",
        "    LI(t0, PMP_MASK)",
        "    and x4, x4, t0",
        "    LI(t0, PMP_REGION_SIZE)",
        "    or x4, x4, t0",
        ".endif",
        "",
        "    .set pmpaddri, CSR_PMPADDR0",
        "    .rept UDB_NUM_PMP_ENTRIES",
        "    csrw pmpaddri, x4",
        "    .set pmpaddri, pmpaddri+1",
        "    .endr",
        "",
        VERIFICATION_BANNER,
    ]
    entry = 14 - (first - 1) % 15
    for i, code in enumerate(codes):
        n = first + i
        csr, shift = _cfg_names(xlen, entry)
        perms = _XWR_COMMENT_FIXUPS.get((xlen.bits, key, n), _XWR_PERMS[code])
        space = "" if (xlen.bits, key, n) in _XWR_TIGHT_SHIFT else " "
        lines.extend(
            [
                f"// Test Case: {n} -- {perms} given to the PMP Region {entry}",
                "",
                f"    LI(x4, (PMPREGION_XWR_{code}{space}<< {shift}))",
                f"    csrw {csr}, x4",
                "",
                "    RVTEST_SFENCE_VMA_IF_SUPPORTED",
                f"    PMP_VERIFICATION_RWX_ALL    TEST_FOR_EXECUTION{sep}test_{n}",
            ]
        )
        if xlen.bits == 64:
            lines.extend(_GOTO_MMODE)
        lines.append("")
        entry -= 1
    if exit_block:
        lines.extend(_EXIT)
    return lines


_XWR32_STRS = ["sb", "sh", "sw", "lb", "lbu", "lh", "lhu", "lw", "jalr"]
_XWR64_STRS = ["sb", "sh", "sw", "sd", "lb", "lbu", "lh", "lhu", "lw", "lwu", "ld", "jalr"]

#: rv64 file -> the exact spacing it uses between the two PMP_VERIFICATION_RWX_ALL arguments.
_XWR64_SEP = {"01": " , ", "02": " , ", "03": ",", "04": ",", "05": " , ", "06": " , ", "07": " , ", "08": " , "}


def _xwr_files() -> list[PmpFile]:
    files = []
    for key, (first, codes) in _XWR32_CODES.items():
        xlen = XLENS[32]
        case_list = codes.split()
        files.append(
            PmpFile(
                filename=f"pmpsm_cfg_XWR_all-{key}.S",
                xlen=xlen,
                copyright=_COPYRIGHT,
                banner=_banner(_XWR_CASES),
                required_extensions=_EXTENSIONS,
                params=_params(),
                priv_test=False,
                sigupd=sigupd_count(len(case_list) * 9),
                body=tuple(_xwr_body(xlen, key, first, case_list, ", ", exit_block=False)),
                data_align=4,
                sig_strs=_sig_strs_named([f"pmpm_cfg_XWR_all_{s}" for s in _XWR32_STRS]),
                data=_NAPOT_PAD_TAIL_XWR,
            )
        )
    for key, (first, codes) in _XWR64_CODES.items():
        xlen = XLENS[64]
        case_list = codes.split()
        files.append(
            PmpFile(
                filename=f"pmpsm_cfg_XWR_all-{key}.S",
                xlen=xlen,
                copyright=_COPYRIGHT,
                banner=_banner(_XWR_CASES),
                required_extensions=_EXTENSIONS,
                params=_params(),
                priv_test=False,
                sigupd=sigupd_count(len(case_list) * 12),
                body=tuple(
                    _xwr_body(xlen, key, first, case_list, _XWR64_SEP[key], exit_block=key in ("05", "06", "07", "08"))
                ),
                sig_strs=_sig_strs_named([f"pmpm_cfg_XWR_all_{s}" for s in _XWR64_STRS]),
                data=_NAPOT_PAD_TAIL_XWR,
            )
        )
    return files


_NAPOT_PAD_TAIL_XWR = _data_tail(pad="PMP_NAPOT_REGION_PAD_WORDS", pad_comment=_PAD_COMMENT, granule_mid=True)


# ---------------------------------------------------------------------------
# cfg_na4_all / cfg_napot_all: A=NA4 / A=NAPOT works in every region
# ---------------------------------------------------------------------------

_NA4_CASES = """// Coverpoints : cp_cfg_A_na4_all for PMPM is fully covered in this test file.
//
// Test Cases  : Checking A=NA4 works in each region with pmpcfg.L = 1,
//                 pmpcfg.A=NA4, pmpcfg.XWR=000, standard regions and making lw,
//                 sw and jalr at that address, address - 4, and address + 4.
"""

_NAPOT_CASES = """// Coverpoints : cp_cfg_A_napot_all for PMPM is fully covered in this test file.
//
// Test Cases  : Checking A=NAPOT works in each region with pmpcfg.L = 1,
//                 pmpcfg.A=NAPOT, pmpcfg.XWR=000, standard regions and making lw,
//                 sw and jalr at that address, address - 4, and just beyond top
//                 of the region. Test file will get reasonably large in size if
//                 Grain Index value will increase.
"""


def _load_probe_macro(xlen: Xlen, third: list[str], pad: str) -> str:
    """VERIFICATION_RWX for na4/napot: three loads at the region, just below it, and past its top."""
    lines = [
        ".macro VERIFICATION_RWX ADDRESS, TEST_CASE",
        "",
        f"    LA(a5, \\ADDRESS){pad}// Address to be verified",
    ]
    if xlen.bits == 64:
        lines.append("    LI(a4, DOUBLE_NOP)")
    for n, step in enumerate([[], ["    addi a5, a5, -4"], third], start=1):
        lines.extend(
            [
                *step,
                f"    \\TEST_CASE\\()_{n}:",
                "    lw a4, 0(a5)",
                "    nop",
                "    nop",
                (
                    f"    RVTEST_SIGUPD(x2, x5, x4, a4, \\TEST_CASE\\()_{n}, test_{n}_str)"
                    "                                   // Signature update"
                ),
                "",
            ]
        )
    lines.append(".endm")
    return "\n".join(lines)


def _region_walk_body(
    xlen: Xlen,
    *,
    defines: list[str],
    li_open: str | None,
    cfg_expr: Callable[[int, str], str],
) -> list[str]:
    """Program one locked region per PMP entry, from region 14 down to region 0, and probe it."""
    lines = [*zero_pmp_regs(xlen), "", *defines, "", "    RVTEST_PMP_SET_BACKGROUND x4", "", VERIFICATION_BANNER]
    for n, entry in enumerate(range(14, -1, -1), start=1):
        csr, shift = _cfg_names(xlen, entry)
        addr = _mask_block(li_open) if li_open else ["    LA(x5, REGIONSTART)", "    srl x5, x5, PMP_SHIFT"]
        lines.extend(
            [
                f"// Test Case: {n} : L -> 1 and No Permissions given to the PMP Region {entry}",
                "",
                *addr,
                f"    csrw pmpaddr{entry}, x5",
                "",
                f"    LI(x4, ({cfg_expr(entry, shift)}))",
                f"    csrw {csr}, x4",
                "",
                "    RVTEST_SFENCE_VMA_IF_SUPPORTED",
                f"    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_{n}",
                "",
            ]
        )
    return lines


def _shift_defines(amode: str, pad: str) -> list[str]:
    """Per-entry-slot ``PMPREGION<n>_XWR_000`` defines, as the rv32 files spell them."""
    return [f"#define PMPREGION{i}_XWR_000{pad}(((PMP_L|PMP_{amode})&0xFF) << PMP{i}_CFG_SHIFT)" for i in range(4)]


def _na4_files() -> list[PmpFile]:
    files = []
    for bits in (32, 64):
        xlen = XLENS[bits]
        if bits == 32:
            defines = [*_shift_defines("NA4", "   "), "", "#define REGIONSTART     TEST_FOR_EXECUTION"]

            def cfg_expr(entry: int, shift: str) -> str:
                return f"PMPREGION{entry % 4}_XWR_000"
        else:
            defines = [
                "#define PMPREGION_XWR_000    ((PMP_L|                  PMP_NA4  )&0xFF)",
                "",
                "#define REGIONSTART        TEST_FOR_EXECUTION        // RAM_BASE_ADDR + PROGRAM_SIZE",
            ]

            def cfg_expr(entry: int, shift: str) -> str:
                return f"PMPREGION_XWR_000 << {shift}"

        files.append(
            PmpFile(
                filename="pmpsm_cfg_na4_all.S",
                xlen=xlen,
                copyright=_COPYRIGHT,
                banner=_banner(_NA4_CASES),
                required_extensions=_EXTENSIONS,
                params=_params("PMP_NA4_SUPPORTED: true"),
                priv_test=False,
                sigupd=sigupd_count(45),
                macro_blocks=(
                    _load_probe_macro(xlen, ["    addi a5, a5, 8"], "                                        "),
                ),
                body=tuple(_region_walk_body(xlen, defines=defines, li_open=None, cfg_expr=cfg_expr)),
                data_align=4 if bits == 64 else None,
                sig_strs=_sig_strs_named(
                    [
                        "pmpm_cfg_na4_all_lw_address",
                        "pmpm_cfg_na4_all_address-4",
                        "pmpm_cfg_na4_all_address+4",
                    ]
                ),
                data=_data_tail(),
            )
        )
    return files


_NAPOT_G_DEFINE = """
#if UDB_PMP_GRANULARITY != 2
  #define g   (1 << (UDB_PMP_GRANULARITY))
#else
  #define g   (1 << (UDB_PMP_GRANULARITY + 1))
#endif
"""


def _napot_files() -> list[PmpFile]:
    files = []
    for bits in (32, 64):
        xlen = XLENS[bits]
        size_else = "(1<<(UDB_PMP_GRANULARITY+1))" if bits == 32 else "(1<<(UDB_PMP_GRANULARITY+6))"
        mask = [
            "#if UDB_PMP_GRANULARITY != 2",
            "    #define PMP_MASK            ~((1 << (UDB_PMP_GRANULARITY - 3))-1)",
            "    #define PMP_REGION_SIZE     (1 << (UDB_PMP_GRANULARITY - 3)) - 1",
            "    #define SIZE                (1<<(UDB_PMP_GRANULARITY))",
            "#else",
            "    #define PMP_MASK            ~0",
            "    #define PMP_REGION_SIZE     0",
            f"    #define SIZE                {size_else}",
            "#endif",
        ]
        if bits == 32:
            defines = [
                *_shift_defines("NAPOT", "  "),
                "",
                "#define REGIONSTART         TEST_FOR_EXECUTION",
                *mask,
            ]
            li_open = "LI(x6,"
            third = ["    LI(t0, g)", "    add    a5, a5, t0", "    addi a5, a5, 4"]

            def cfg_expr(entry: int, shift: str) -> str:
                return f"PMPREGION{entry % 4}_XWR_000"
        else:
            defines = [
                "#define PMPREGION_XWR_000   ((PMP_L|PMP_NAPOT)&0xFF)",
                "",
                "#define    REGIONSTART            TEST_FOR_EXECUTION        // RAM_BASE_ADDR + PROGRAM_SIZE",
                *mask,
            ]
            li_open = "LI (x6, "
            third = ["    LI(t0, (g+4))", "    add a5, a5, t0"]

            def cfg_expr(entry: int, shift: str) -> str:
                return f"PMPREGION_XWR_000 << {shift}"

        files.append(
            PmpFile(
                filename="pmpsm_cfg_napot_all.S",
                xlen=xlen,
                copyright=_COPYRIGHT,
                banner=_banner(_NAPOT_CASES),
                required_extensions=_EXTENSIONS,
                params=_params("PMP_NAPOT_SUPPORTED: true"),
                priv_test=False,
                sigupd=sigupd_count(45),
                macro_blocks=(
                    _NAPOT_G_DEFINE,
                    _load_probe_macro(xlen, third, "                                                            "),
                ),
                body=tuple(_region_walk_body(xlen, defines=defines, li_open=li_open, cfg_expr=cfg_expr)),
                data_align=4 if bits == 32 else None,
                sig_strs=_sig_strs_named(
                    [
                        "pmpm_cfg_napot_all_lw_address",
                        "pmpm_cfg_napot_all_address-4",
                        "pmpm_cfg_napot_all_address+4",
                    ]
                ),
                data=_data_tail(
                    pad="(g>>2)" if bits == 32 else "PMP_NAPOT_REGION_PAD_WORDS",
                    pad_comment=_PAD_COMMENT,
                    region="(SIZE/4)",
                ),
            )
        )
    return files


# ---------------------------------------------------------------------------
# cfg_tor_all: A=TOR works in every region
# ---------------------------------------------------------------------------

_TOR_ALL_CASES = """// Coverpoints : cp_cfg_A_tor_all for PMPM is fully covered in this test file.
//
// Test Cases  : Checking A = TOR works in each region. Preconfigure all
//                 (PMP_writable_regs-1) PMP regions in with pmpcfg.L = 1,
//                 pmpcfg.A = TOR, pmpcfg.XWR=00(i%2), starting with default
//                 TOR region and moving up by g*i (each region getting larger by g).
//                 Attempt lw at at start of region.  Odd regions should allow lw,
//                 and all others should trap.
"""

_TOR_ALL_MACRO = """
.macro VERIFICATION_RWX ADDRESS TEST_CASE

    LA(a5, \\ADDRESS)                                         // Address to be verified
@LOAD@    \\TEST_CASE\\()_1:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \\TEST_CASE\\()_1, test_1_str)                                   // Signature update

.endm
"""


def _tor_all_defines(xlen: Xlen) -> list[str]:
    lines = [
        "#define DEFAULT_TOR_REGION  (((PMP_L|PMP_R|PMP_W|PMP_X|PMP_TOR)&0xFF) << PMP0_CFG_SHIFT)",
    ]
    for i in range(xlen.cfgs_per_reg):
        if i % 2 == 0:
            lines.append(
                f"#define PMPREGION{i}_XWR_000  (((PMP_L|                  PMP_TOR)&0xFF) << PMP{i}_CFG_SHIFT)"
            )
        else:
            lines.append(
                f"#define PMPREGION{i}_XWR_001  (((PMP_L|PMP_R|            PMP_TOR)&0xFF) << PMP{i}_CFG_SHIFT)"
            )
    return lines


def _tor_all_slot(i: int) -> str:
    return f"PMPREGION{i}_XWR_{'001' if i % 2 else '000'}"


def _tor_all_body(xlen: Xlen) -> list[str]:
    per = xlen.cfgs_per_reg
    lines = [*zero_pmp_regs(xlen), "", *_tor_all_defines(xlen), "", "", "    RVTEST_PMP_SET_BACKGROUND x4", ""]
    for entry in range(15):
        target = "TEST_FOR_EXECUTION_0" if entry == 0 else f"(TEST_FOR_EXECUTION_{entry})"
        lines.extend([f"    LA(x4, {target})", "    srl x4, x4, PMP_SHIFT", f"    csrw pmpaddr{entry}, x4", ""])
    lines.extend(
        [
            VERIFICATION_BANNER,
            (
                "// Test Case: 1 : Preconfigure all (PMP_writable_regs-1) PMP regions in with pmpcfg.L = 1,"
                " pmpcfg.A = TOR, pmpcfg.XWR=00(i%2)"
            ),
            "",
        ]
    )
    for csr_index in range(16 // per):
        top = min(per, 15 - csr_index * per)
        slots = [_tor_all_slot(i) for i in range(top - 1, 0, -1)]
        slots.append("DEFAULT_TOR_REGION" if csr_index == 0 else _tor_all_slot(0))
        lines.extend([f"    LI(x4, ({'|'.join(slots)}))", f"    csrw pmpcfg{csr_index * xlen.cfg_step}, x4"])
    lines.extend(["", "    RVTEST_SFENCE_VMA_IF_SUPPORTED", ""])
    calls = [("TEST_FOR_EXECUTION_0 - 4", True)] if xlen.bits == 64 else []
    calls += [(f"TEST_FOR_EXECUTION_{i}", False) for i in range(15 - len(calls))]
    for n, (addr, parens) in enumerate(calls, start=1):
        if parens:
            lines.append(f"    VERIFICATION_RWX    ({addr}) , test_{n}     // Access at the end of default region")
        else:
            lines.append(f"    VERIFICATION_RWX    {addr:<21}, test_{n}")
    return lines


def _tor_all_data() -> tuple[str, ...]:
    lines = [
        ".p2align 12",
        "TEST_FOR_EXECUTION_X:",
        f"    .rept (1 << (UDB_PMP_GRANULARITY - 2)){_FILLER_COMMENT}",
        "    jr ra",
        "    .endr",
        "",
    ]
    for i in range(15):
        rept = f"({i + 1}*((1<<(UDB_PMP_GRANULARITY))/4))" if i else "((1<<(UDB_PMP_GRANULARITY))/4)"
        lines.extend(
            [
                f"TEST_FOR_EXECUTION_{i}:                       // Adding nops in the TOR Region {i}",
                f"    .rept {rept}",
                "    nop",
                "    .endr",
                "",
            ]
        )
    lines.extend(_RETURN_TRAMPOLINE)
    return tuple(lines)


def _tor_all_files() -> list[PmpFile]:
    files = []
    for bits in (32, 64):
        xlen = XLENS[bits]
        load = "    LI(a4, DOUBLE_NOP)\n" if bits == 64 else ""
        files.append(
            PmpFile(
                filename="pmpsm_cfg_tor_all.S",
                xlen=xlen,
                copyright=_COPYRIGHT,
                banner=_banner(_TOR_ALL_CASES),
                required_extensions=_EXTENSIONS,
                params=_params("PMP_TOR_SUPPORTED: true"),
                priv_test=False,
                sigupd=sigupd_count(15),
                macro_blocks=(_TOR_ALL_MACRO.replace("@LOAD@", load),),
                body=tuple(_tor_all_body(xlen)),
                data_align=4,
                sig_strs=_sig_strs_named(["pmpm_cfg_tor_all_lw"]),
                data=_tor_all_data(),
            )
        )
    return files


# ---------------------------------------------------------------------------
# cfg_tor_check: a TOR region with pmpaddr0 >= pmpaddr1 never matches
# ---------------------------------------------------------------------------


def _tor_check_banner(ordinal: str, cfg_line: str, case_line: str) -> str:
    return f"""// Coverpoints : {ordinal} test case of cp_cfg_A_tor_non-overlap for PMPM is covered
//                 in this test file.
//
// Test case    : We check that there is no match when pmpaddr0 >= pmpaddr1 with
//                  the following cfgs pmpcfg1.L=1, pmpcfg1.A=TOR, {cfg_line}
//                  pmpcfg0.L=0, pmpcfg0.A=OFF, pmpcfg1.XWR=000. This test exercises
//                   {case_line}
"""


def _tor_check_macro(xlen: Xlen) -> str:
    nop = _nop_const(xlen)
    lines = [
        ".macro VERIFICATION_RWX ADDRESS TEST_CASE",
        "",
        f"    LI(a4, {nop})                                             // Value to write ({nop})",
    ]
    probes = [("-4", "sw"), ("", "sw"), ("+4", "sw"), ("-4", "lw"), ("", "lw"), ("+4", "lw")]
    for n, (off, op) in enumerate(probes, start=1):
        comment = "word-level store test" if op == "sw" else "Word load test"
        lines.extend(
            [
                "",
                f"    LA(a5, (\\ADDRESS{off}))                                    // Address to be verified",
                f"    \\TEST_CASE\\()_{n}:",
                f"    {op} a4, 0(a5)                                            // {comment}",
                "    nop",
                "    nop",
                (
                    f"    RVTEST_SIGUPD(x2, x5, x4, a4, \\TEST_CASE\\()_{n}, test_{n}_str)"
                    "                               // Signature update"
                ),
            ]
        )
    for n, off in enumerate(["-4", "", "+4"], start=1):
        lines.extend(
            [
                "",
                f"    LA (a4, (\\ADDRESS{off}))",
                f"    LA(x1, {n}f)                                                // Store the return Address in x1",
            ]
        )
        if n == 1:
            lines.append(f"    RVTEST_FENCEI{_FENCEI_COMMENT}")
        lines.extend(["    jalr ra, 0(a4)", "    nop", "    nop", f"{n}:", "    nop", "    nop"])
    lines.extend(["", ".endm"])
    return "\n".join(lines)


#: file -> (banner ordinal, banner cfg line, banner case line, test case comment, extra setup, all-ones,
#:          pmpaddr0 source, macro argument separator, string suffix per XLEN)
_TOR_CHECK_VARIANTS = {
    "01": (
        "1st",
        "pmpcfg1.XWR = 000",
        "test case 1 that is when pmpaddr0 = pmpaddr1",
        "pmpaddr0 = pmpaddr1",
        False,
        False,
        "x4",
        ", ",
        {32: "check1", 64: "check1"},
    ),
    "02": (
        "2nd",
        "pmpcfg1.XWR=000,",
        "test case 2 that is when  pmpaddr0 = pmpaddr1 + g",
        "pmpaddr0 = pmpaddr1 + g",
        True,
        False,
        "x5",
        " , ",
        {32: "check1", 64: "check2"},
    ),
    "03": (
        "3rd",
        "pmpcfg1.XWR=000,",
        "test case 3 that is when pmpaddr0 =  all 1s",
        "pmpaddr0 = all1s",
        True,
        True,
        "x5",
        ",",
        {32: "check3", 64: "check3"},
    ),
}


def _tor_check_body(xlen: Xlen, *, plus_g: bool, all_ones: bool, addr0: str, sep: str, case: str) -> list[str]:
    lines = [
        *zero_pmp_regs(xlen),
        "",
        "#define PMPREGION_UPPER_BOUND      ((((PMP_L                  |PMP_TOR)     &0xFF) << PMP1_CFG_SHIFT))",
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        "    //addresses for a default TOR region",
        "    LA(x4, TEST_FOR_EXECUTION)",
    ]
    if plus_g:
        lines.extend(["    LI(t0, g)", "    add x5, x4, t0"])
    lines.append("    srl x4, x4, PMP_SHIFT")
    if plus_g:
        lines.append("    srl x5, x5, PMP_SHIFT")
    lines.extend(["", VERIFICATION_BANNER, f"// Test Case:  {case}", ""])
    if all_ones:
        lines.append("    LI(x5, -1)")
    lines.extend(
        [
            f"    csrw     pmpaddr0, {addr0}",
            "    csrw     pmpaddr1, x4",
            "",
            "    LI(x4, PMPREGION_UPPER_BOUND)",
            "    csrw pmpcfg0, x4",
            "",
            "    RVTEST_SFENCE_VMA_IF_SUPPORTED",
            f"    VERIFICATION_RWX    TEST_FOR_EXECUTION{sep}test_1",
            *_GOTO_MMODE,
        ]
    )
    return lines


def _tor_check_files() -> list[PmpFile]:
    probes = [
        ("store", "-4"),
        ("store", ""),
        ("store", "+4"),
        ("load", "-4"),
        ("load", ""),
        ("load", "+4"),
    ]
    files = []
    for key, (ordinal, cfg_line, case_line, case, plus_g, all_ones, addr0, sep, suffix) in _TOR_CHECK_VARIANTS.items():
        for bits in (32, 64):
            xlen = XLENS[bits]
            names = [f"pmpm_cfg_tor_{suffix[bits]}_{kind}_access_at_pmpaddr{off}" for kind, off in probes]
            files.append(
                PmpFile(
                    filename=f"pmpsm_cfg_tor_check-{key}.S",
                    xlen=xlen,
                    copyright=_COPYRIGHT,
                    banner=_banner(_tor_check_banner(ordinal, cfg_line, case_line)),
                    required_extensions=_EXTENSIONS,
                    params=_params("PMP_TOR_SUPPORTED: true"),
                    priv_test=False,
                    sigupd=sigupd_count(6),
                    macro_blocks=(
                        "#define g         (1<<(UDB_PMP_GRANULARITY))",
                        _tor_check_macro(xlen),
                    ),
                    body=tuple(
                        _tor_check_body(xlen, plus_g=plus_g, all_ones=all_ones, addr0=addr0, sep=sep, case=case)
                    ),
                    data_align=4,
                    sig_strs=_sig_strs_named(names),
                    data=_data_tail(),
                )
            )
    return files


# ---------------------------------------------------------------------------


def build_cfg_files() -> list[PmpFile]:
    """Every ``pmpsm_cfg_*`` file of the PMPSm suite, for both XLENs."""
    return [
        *_a_all_files(),
        *_a_off_files(),
        *_a_tor_bot_files(),
        *_a_tor_zero_files(),
        *_l_access_files(),
        *_l_modify_files(),
        *_xwr_files(),
        *_na4_files(),
        *_napot_files(),
        *_tor_all_files(),
        *_tor_check_files(),
    ]
