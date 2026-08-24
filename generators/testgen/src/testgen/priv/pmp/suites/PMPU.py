##################################
# priv/pmp/suites/PMPU.py
#
# PMPU: PMP enforcement of U-mode accesses.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMPU suite: PMP configurations programmed in M mode and exercised from U mode."""

from __future__ import annotations

from testgen.priv.pmp import add_pmp_suite
from testgen.priv.pmp.macros import (
    VERIFICATION_SECTION_BANNER,
    case_banner,
    cfg_csr,
    cfg_shift,
    lxwr_expr,
    regionstart_define,
    set_pmpaddr_napot,
    set_pmpaddr_plain,
    sigupd_count,
    test_case_str,
    zero_pmp_regs,
)
from testgen.priv.pmp.model import XLENS, PmpFile, Xlen

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

_COPYRIGHT = (
    "// Copyright (C) 2025 Harvey Mudd College & Oklahoma State University, UET Lahore, Habib University",
    "// SPDX-License-Identifier: Apache-2.0",
    "//",
)

#: Only the rv32 tor-01 file carries the second copyright line.
_COPYRIGHT_QUALCOMM = (
    _COPYRIGHT[0],
    "// Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.",
    *_COPYRIGHT[1:],
)


def _banner(coverpoints: str, test_cases: str) -> str:
    """Assemble one file's comment banner from the parts that vary between files."""
    return f"{_HEADING}{coverpoints}//\n{test_cases}"


_GOTO_UMODE = "    RVTEST_GOTO_LOWER_MODE    Umode        // SWITCH TO U-mode"
_EXIT = [
    "",
    "    j exit                                                        // Verification Complete, exit the test",
    "",
    "exit:",
]

_NUM_ENTRIES_PARAM = "NUM_PMP_ENTRIES: '>0'"


def _mask_defines(xlen: Xlen) -> list[str]:
    """NAPOT address-mask defines; rv64 spells the shift amount without spaces."""
    gran = "UDB_PMP_GRANULARITY - 3" if xlen.bits == 32 else "UDB_PMP_GRANULARITY-3"
    return [
        "#if UDB_PMP_GRANULARITY != 2",
        f"    #define PMP_MASK            ~((1 << ({gran}))-1)",
        f"    #define PMP_REGION_SIZE     (1 << ({gran})) - 1",
        "#else",
        "    #define PMP_MASK            ~0",
        "    #define PMP_REGION_SIZE     0",
        "#endif",
    ]


def _lxwr_defines(xlen: Xlen, cases: list[tuple[str, int]], amode: str, *, locked: bool) -> list[str]:
    """`#define PMPREGION_LXWR_<name>` lines; `locked` selects whether PMP_L is in the value."""
    return [
        f"#define PMPREGION_LXWR_{name} "
        f"(((({lxwr_expr(name if locked else f'0{name[1:]}', amode)})&0xFF) << {cfg_shift(xlen, entry)}))"
        for name, entry in cases
    ]


#####################################################################
# Data sections
#####################################################################

_RETURN_TRAMPOLINE = [
    "RETURN_INSTRUCTION:",
    "    nop",
    "    nop",
    "    jr ra                                                        // Get back to the point from where TEST_FOR_EXECUTION was called.",
]

_GRANULE_PAD = (
    "    .rept (1 << (UDB_PMP_GRANULARITY - 2))              // one PMP granule of return-instruction fillers: "
    "places the region on the next granule boundary (= PMP_REGION_START at coverage grain 2), grain-aligned at larger grains"
)

_NAPOT_PAD = (
    "    .rept PMP_NAPOT_REGION_PAD_WORDS  // NAPOT-safe fillers: places the region at PMP_NAPOT_REGION_START "
    "(matches cp_mprv_*'s standard_region requirement)"
)


def _nop_region_data(pad: str) -> list[str]:
    """A granule of `jr ra` fillers followed by a granule-sized region of nops."""
    return [
        ".p2align 12",
        ".p2align (UDB_PMP_GRANULARITY)",
        "TEST_FOR_EXECUTION_0:",
        pad,
        "    jr ra",
        "    .endr",
        "",
        ".p2align (UDB_PMP_GRANULARITY)",
        "TEST_FOR_EXECUTION:",
        "    .rept (1<<(UDB_PMP_GRANULARITY))",
        "    nop",
        "    .endr",
        "",
        *_RETURN_TRAMPOLINE,
    ]


def _jr_region_data(count: str) -> list[str]:
    """Two granule-sized regions of `jr ra`, so any word in the region is a valid target."""
    return [
        ".p2align 12",
        ".p2align (UDB_PMP_GRANULARITY)",
        "TEST_FOR_EXECUTION_0:",
        f"    .rept {count}",
        "    jr ra",
        "    .endr",
        "",
        ".p2align (UDB_PMP_GRANULARITY)",
        "TEST_FOR_EXECUTION:",
        f"    .rept {count}",
        "    jr ra",
        "    .endr",
        "",
        *_RETURN_TRAMPOLINE,
    ]


#####################################################################
# cfg_A_off: A=OFF never matches, so U mode falls through to the
# permissive background region.
#####################################################################

_A_OFF_TEST_CASES = """\
// Test Cases  : Checking that A=OFF never matches a region. Configuring
//                 PMP in M and switching to U mode. For pmpaddr with all 1s
//                 pmpcfg.L=0, pmpcfg.A=OFF, pmpcfg.XWR=000. Fetching, reading
//                 and writing from that region. Should succeed because region
//                 is off even though inaccessible.
"""


def _a_off_body(xlen: Xlen) -> list[str]:
    return [
        *zero_pmp_regs(xlen),
        "",
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        "    LA(x4, -1)",
        "    // Putting all 1s in pmpaddr0",
        "    csrw pmpaddr0, x4",
        "",
        VERIFICATION_SECTION_BANNER,
        "// Test Case: 1 -- No Permissions given to the PMP Region 0",
        "",
        "    csrw pmpcfg0, x0        // pmp0cfg0.L = 0, pmp0cfg0.A = OFF and pmp0cfg0.WXR = 000",
        "",
        "    RVTEST_SFENCE_VMA_IF_SUPPORTED",
        _GOTO_UMODE,
        "    PMP_VERIFICATION_RWX    TEST_FOR_EXECUTION, test_1",
        "    RVTEST_GOTO_MMODE",
        *_EXIT,
    ]


def _a_off_file(xlen: Xlen) -> PmpFile:
    # The rv64 coverpoint line names PMPS.
    suite = "PMPU" if xlen.bits == 32 else "PMPS"
    return PmpFile(
        filename="pmpu_cfg_A_off.S",
        xlen=xlen,
        banner=_banner(
            f"// Coverpoints : cp_cfg_A_off for {suite} is fully covered in this test file.\n",
            _A_OFF_TEST_CASES,
        ),
        required_extensions=("U",),
        params=(_NUM_ENTRIES_PARAM,),
        sigupd=sigupd_count(3),
        body=tuple(_a_off_body(xlen)),
        sig_strs=tuple(
            (f"test_{n}", test_case_str(n, f"pmpu_cfg_A_off_all_{op}"))
            for n, op in enumerate(("jalr", "sw", "lw"), start=1)
        ),
        data_align=None if xlen.bits == 32 else 4,
        data=tuple(_nop_region_data(_GRANULE_PAD)),
    )


#####################################################################
# cfg_XWR / cfg_XWR_unlocked: walk the six legal XWR encodings against
# a NAPOT region and try every width of load and store from U mode.
#####################################################################

_XWR_CASES: list[tuple[str, int]] = [("1000", 5), ("1001", 4), ("1011", 3), ("1100", 2), ("1101", 1), ("1111", 0)]
_XWR_UNLOCKED_CASES: list[tuple[str, int]] = [(f"0{name[1:]}", entry) for name, entry in _XWR_CASES]

_XWR_COVERPOINTS = (
    "// Coverpoints : cp_cfg_X and cp_cfg_RW from PMPU are partially covered in this\n//                 test file.\n"
)


def _xwr_test_cases(xlen: Xlen) -> str:
    # rv32 abbreviates "and" as "&" in the description.
    conj = "&" if xlen.bits == 32 else "and"
    return f"""\
// Test Cases  : Checking that X alone determines execute access and WR bits control
//               write/read access for every type of load and store. Configuring
//               PMP in M mode {conj} then switching to U mode. For a standard region with
//               pmpcfg_i.L = 1, pmpcfg_i.A=NAPOT, all legal pmpcfg_i.XWR, making
//               {{lw, sw, jalr}} at that start of region.
"""


def _access_check(index: int, insn: str, extra_nops: int = 0) -> list[str]:
    """One labelled load/store followed by its signature update."""
    return [
        f"    \\TEST_CASE\\()_{index}:",
        f"    {insn} a4, 0(a5)",
        *(["    nop"] * (1 + extra_nops)),
        f"    RVTEST_SIGUPD(x2, x5, x4, a4, \\TEST_CASE\\()_{index}, test_{index}_str)",
    ]


def _xwr_macro(xlen: Xlen) -> str:
    stores = ["sb", "sh", "sw"] + (["sd"] if xlen.bits == 64 else [])
    loads = ["lb", "lbu", "lh", "lhu", "lw"] + (["lwu", "ld"] if xlen.bits == 64 else [])
    nop_value = "NOP" if xlen.bits == 32 else "DOUBLE_NOP"
    lines = [
        ".macro VERIFICATION_RWX ADDRESS TEST_CASE",
        "",
        "    // Execution Access Check",
        "    LA (a4, \\ADDRESS)",
        "    LA(x1, 1f)                            // Store the return Address in x1",
        "    RVTEST_FENCEI                              // sync I-cache: a prior store may have updated this executable region",
        "    \\TEST_CASE\\()_1:",
        "    jalr ra, 0(a4)",
        "    nop",
        "1:",
        "    nop",
        "    RVTEST_SIGUPD(x2, x5, x4, a4, \\TEST_CASE\\()_1, test_1_str)",
        "",
        f"    LI(a4, {nop_value})                                              // Value to write ({nop_value})",
        "    // Store Access Check",
        "    LA(a5, \\ADDRESS)                                         // Address to be verified",
    ]
    index = 1
    for insn in stores:
        index += 1
        lines.extend(_access_check(index, insn))
    lines.extend(["", "    LA(a5, \\ADDRESS)                                         // Address to be verified"])
    for insn in loads:
        index += 1
        lines.extend(_access_check(index, insn))
    lines.extend(["", ".endm"])
    return "\n".join(lines)


def _lower_mode_run(runner: str, index: int) -> list[str]:
    """Drop to U mode, run the verification macro, and come back to M mode."""
    return [
        "",
        "    RVTEST_SFENCE_VMA_IF_SUPPORTED",
        _GOTO_UMODE,
        f"    {runner}    TEST_FOR_EXECUTION, test_{index}",
        "    RVTEST_GOTO_MMODE",
    ]


def _xwr_body(xlen: Xlen, cases: list[tuple[str, int]]) -> list[str]:
    lines = [
        *zero_pmp_regs(xlen),
        "",
        *_lxwr_defines(xlen, cases, "PMP_NAPOT", locked=True),
        "",
        regionstart_define(),
        *_mask_defines(xlen),
        "",
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        "",
        VERIFICATION_SECTION_BANNER,
    ]
    for n, (name, entry) in enumerate(cases, start=1):
        if n > 1:
            lines.append("")
        lines.append(case_banner(n, name, entry)[1])
        lines.append("")
        lines.extend(set_pmpaddr_napot(entry, addr_reg="x5", tmp_reg="x6"))
        lines.extend([f"    LI(t1, PMPREGION_LXWR_{name})", f"    csrw {cfg_csr(xlen, entry)}, t1"])
        lines.extend(_lower_mode_run("VERIFICATION_RWX", n))
    lines.extend(_EXIT)
    return lines


def _xwr_file(xlen: Xlen, *, unlocked: bool) -> PmpFile:
    cases = _XWR_UNLOCKED_CASES if unlocked else _XWR_CASES
    stem = "pmpu_cfg_XWR_unlocked" if unlocked else "pmpu_cfg_XWR"
    ops = ["jalr", "sb", "sh", "sw"] + (["sd"] if xlen.bits == 64 else [])
    ops += ["lb", "lbu", "lh", "lhu", "lw"] + (["lwu", "ld"] if xlen.bits == 64 else [])
    # Both rv32 files report the PMPS coverpoint names, and both report the locked file's name.
    reported = "pmps_cfg_XWR.S" if xlen.bits == 32 else f"{stem}.S"
    return PmpFile(
        filename=f"{stem}.S",
        xlen=xlen,
        banner=_banner(_XWR_COVERPOINTS, _xwr_test_cases(xlen)),
        required_extensions=("U",),
        params=(_NUM_ENTRIES_PARAM,),
        sigupd=sigupd_count(len(cases) * len(ops)),
        macro_blocks=(_xwr_macro(xlen),),
        body=tuple(_xwr_body(xlen, cases)),
        sig_strs=tuple((f"test_{n}", test_case_str(n, f"{reported}_{op}")) for n, op in enumerate(ops, start=1)),
        data_align=4,
        data=tuple(_nop_region_data(_GRANULE_PAD)),
    )


#####################################################################
# csr_access: every pmpaddr and pmpcfg CSR written from U mode.
#####################################################################

_CSR_ACCESS_TEST_CASES = """\
// Test Cases  : Test pmpcfg and pmpaddr access from U-mode. Trying to write
//               all 64 pmpaddr and 16 pmpcfg registers. Should throw illegal
//               instruction faults because PMP CSRs are only accessible to
//               M-mode.
"""


def _csr_walk(symbol: str, first: str, count: int, index: int) -> list[str]:
    """A `.rept` loop that writes every CSR of one family from U mode."""
    return [
        f"    .set {symbol}, {first}",
        f"    .rept {count}",
        _GOTO_UMODE,
        "    99:",
        f"    RVTEST_SIGUPD_CSR_WRITE({symbol}, x4, 99b, test_{index}_str)",
        "    nop",
        "    RVTEST_GOTO_MMODE",
        f"    .set {symbol}, {symbol}+1",
        "    .endr",
    ]


_CSR_ACCESS_BODY = [
    "",
    "// Trying to access PMP CSRs in U-mode by writing all 1s.",
    "",
    "    // Value to write in PMP CSRs in U-mode",
    "    LA(x4, -1)",
    "",
    *_csr_walk("pmpaddri", "CSR_PMPADDR0", 64, 1),
    "",
    *_csr_walk("pmpcfgi", "CSR_PMPCFG0", 16, 2),
    "",
    "    j exit                                                        // Verification Complete, exit the test",
    "",
    ".p2align 10",
    ".p2align (UDB_PMP_GRANULARITY)",
    *_RETURN_TRAMPOLINE,
    "",
    "exit:",
]


def _csr_access_file(xlen: Xlen) -> PmpFile:
    # The rv32 file reports the S-mode coverpoint names.
    suffix = "_s" if xlen.bits == 32 else ""
    return PmpFile(
        filename="pmpu_csr_access.S",
        xlen=xlen,
        banner=_banner(
            "// Coverpoints : cp_pmpaddr_access_u and cp_pmpcfg_access_u are fully covered in\n//                 this test file.\n",
            _CSR_ACCESS_TEST_CASES,
        ),
        required_extensions=("U",),
        params=(_NUM_ENTRIES_PARAM,),
        sigupd=sigupd_count(64 + 16),
        pre_main=("    RVTEST_PMP_SET_BACKGROUND x4",),
        body=tuple(_CSR_ACCESS_BODY),
        sig_strs=(
            ("test_1", test_case_str(1, f"cp_pmpaddr_access{suffix}")),
            ("test_2", test_case_str(2, f"cp_pmpcfg_access{suffix}")),
        ),
        data_align=4,
    )


#####################################################################
# mprv_check: MPRV makes M mode use U-mode permissions, so the L bit
# stops mattering. Stays in M mode throughout.
#####################################################################

_MPRV_DEFINES = ["#define MPRV                    (1 << 17)", "#define MPP                        (3 << 11)"]

_MPRV_SET_MPP_MPRV = [
    "    li t0, (MPP|MPRV)        // Initialize mstatus.MPRV & mstatus.MPP",
    "    csrc mstatus, t0",
]


def _mprv_test_cases(xwr: str) -> str:
    return f"""\
// Test Cases  : Checking L bit doesn't matter with MPRV setting to lower privilege
//                 mode. Configuring PMP in M-mode. Setting mstatus.MPRV = {{0/1}},
//                 mstatus.MPP = {{11 / 00}}. While staying in M-mode doing {{lw/sw/jalr}}
//                 with pmpcfg_i.L={{0/1}}, XWR = {xwr}. Observing access faults for
//                 restricted execution regions even with L = 0 in effective U mode.
"""


def _mprv_program_region(xlen: Xlen, name: str) -> list[str]:
    """Reprogram entry 0 with one configuration byte, bracketed by the file's rule comments."""
    return [
        "//-------------------------------------",
        *set_pmpaddr_napot(0, addr_reg="x5", tmp_reg="x6")[:-1],
        "    csrw pmpaddr0, x5",
        "",
        f"    LI(x4, PMPREGION_LXWR_{name})",
        "    csrw pmpcfg0, x4",
        "    RVTEST_SFENCE_VMA_IF_SUPPORTED",
        "//-------------------------------------",
    ]


def _mprv_body(xlen: Xlen, names: tuple[str, str], perms: str, banner_indices: tuple[int, int]) -> list[str]:
    unlocked, locked = names
    lines = [
        *zero_pmp_regs(xlen),
        "",
        f"#define PMPREGION_LXWR_{locked}   (({lxwr_expr(locked, 'PMP_NAPOT')})&0xFF) << {cfg_shift(xlen, 0)}",
        f"#define PMPREGION_LXWR_{unlocked}   (({lxwr_expr(unlocked, 'PMP_NAPOT')})&0xFF) << {cfg_shift(xlen, 0)}",
        "",
        *_MPRV_DEFINES,
        "",
        regionstart_define(),
        *_mask_defines(xlen),
        "",
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        *_mprv_program_region(xlen, unlocked),
        "",
        VERIFICATION_SECTION_BANNER,
    ]
    index = 0
    for lock, name, first_banner in ((0, unlocked, 1), (1, locked, banner_indices[0])):
        if lock:
            lines.extend(["", *_mprv_program_region(xlen, name)])
        for mprv in (0, 1):
            index += 1
            banner = first_banner + mprv
            lines.extend(
                [
                    "",
                    (
                        f"// Test Case: {banner} : mstatus.MPRV = {mprv}, L = {lock}, "
                        f"mstatus.MPP = 00 and {perms} given to the PMP Region 0"
                    ),
                    "",
                    *_MPRV_SET_MPP_MPRV,
                ]
            )
            if mprv:
                lines.extend(["", "    li t0, (MPRV)", "    csrs mstatus, t0"])
            lines.extend(["", f"    PMP_VERIFICATION_RWX    TEST_FOR_EXECUTION, test_{index}"])
    lines.extend(_EXIT)
    return lines


def _mprv_file(xlen: Xlen, part: int) -> PmpFile:
    xwr, names, perms = (
        ("000", ("0000", "1000"), "No Permissions") if part == 1 else ("111", ("0111", "1111"), "XWR Permissions")
    )
    # The rv32 -01 file repeats banner indices 1 and 2 for its L=1 cases.
    banner_indices = (1, 2) if (part == 1 and xlen.bits == 32) else (3, 4)
    # The rv64 -02 file requires S rather than U.
    extension = "S" if (part == 2 and xlen.bits == 64) else "U"
    return PmpFile(
        filename=f"pmpu_mprv_check-0{part}.S",
        xlen=xlen,
        banner=_banner("// Coverpoints : cp_mprv for PMPU is partially covered in this file.\n", _mprv_test_cases(xwr)),
        required_extensions=(extension,),
        params=(_NUM_ENTRIES_PARAM,),
        sigupd=sigupd_count(4 * 3),
        body=tuple(_mprv_body(xlen, names, perms, banner_indices)),
        sig_strs=tuple(
            (f"test_{n}", test_case_str(n, f"pmpm_cfg_A_off_all_{op}"))
            for n, op in enumerate(("jalr", "sw", "lw"), start=1)
        ),
        data_align=4,
        data=tuple(_nop_region_data(_NAPOT_PAD)),
    )


#####################################################################
# na4_legal_lxwr: the six unlocked XWR encodings against an NA4 region.
#####################################################################

_NA4_CASES: list[tuple[str, int]] = [("0000", 5), ("0001", 4), ("0011", 3), ("0100", 2), ("0101", 1), ("0111", 0)]

_NA4_TEST_CASES = """\
// Test Cases  : Checking XWR controls accesses in matching NA4 region. G=0 Only
//               Configuring PMP in M mode and then switching to U mode.
//               with pmpcfg_i.L = 1, pmpcfg_i.A=NA4, all legal pmpcfg_i.XWR,
//               reasonable address in pmpaddr: making {lw, sw, jalr} at that
//               address, that address - 4, just beyond top of the region.
//               Observing proper access faults for restricted regions, and
//               accesses beyond the region and below the region should succeed
//               because the bckground region is set to RWX.
"""

_NA4_RV64_MACRO = r""".macro VERIFICATION_RWX ADDRESS TEST_CASE

    RVTEST_FENCEI

    // Execution Access Check
    LA (a4, \ADDRESS)
    LA(x1, 1f)                            // Store the return Address in x1
    \TEST_CASE\()_1:
    jalr ra, 0(a4)
    nop
1:
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)

    addi a4, a4, -4                     // REGIONSTART - 4
    LA(x1, 2f)                            // Store the return Address in x1
    \TEST_CASE\()_2:
    jalr ra, 0(a4)
    nop
2:
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)

    addi a4, a4, 8                      // REGIONSTART + 4
    LA(x1, 3f)                            // Store the return Address in x1
    \TEST_CASE\()_3:
    jalr ra, 0(a4)
    nop
3:
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)

    LI(a4, DOUBLE_NOP)                                              // Value to write (DOUBLE_NOP)
    // Load & Store Access Check
    LA(a5, \ADDRESS)                                         // Address to be verified

    \TEST_CASE\()_4:
    sw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_4, test_4_str)

    \TEST_CASE\()_5:
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_5, test_5_str)                                  // Signature update

    addi a5, a5, -4                                         // REGIONSTART - 4
    \TEST_CASE\()_6:
    sw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_6, test_6_str)

    \TEST_CASE\()_7:
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_7, test_7_str)

    addi a5, a5, 8                                          // REGIONSTART + 4                                            // Address to be verified
    \TEST_CASE\()_8:
    sw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_8, test_8_str)

    \TEST_CASE\()_9:
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_9, test_9_str)

.endm"""


def _na4_body(xlen: Xlen) -> list[str]:
    # rv32 uses the framework macro; rv64 defines its own.
    runner = "PMP_VERIFICATION_RWX_NA4_RV32" if xlen.bits == 32 else "VERIFICATION_RWX"
    lines = [
        *zero_pmp_regs(xlen),
        "",
        *_lxwr_defines(xlen, _NA4_CASES, "PMP_NA4  ", locked=False),
        "",
        "#define REGIONSTART            TEST_FOR_EXECUTION        // RAM_BASE_ADDR + PROGRAM_SIZE",
        "",
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        VERIFICATION_SECTION_BANNER,
    ]
    for n, (name, entry) in enumerate(_NA4_CASES, start=1):
        if n > 1:
            lines.append("")
        lines.append(case_banner(n, name, entry)[1])
        lines.append("")
        lines.extend(set_pmpaddr_plain(entry, addr_reg="x4"))
        lines.extend([f"    LI(x5, PMPREGION_LXWR_{name})", f"    csrw {cfg_csr(xlen, entry)}, x5"])
        lines.extend(_lower_mode_run(runner, n))
    # The last case never returns to M mode and there is no `j exit`.
    del lines[-1]
    lines.append("exit:")
    return lines


def _na4_file(xlen: Xlen) -> PmpFile:
    ops = (
        "jalr_address",
        "jalr_address-4",
        "jalr_address+4",
        "sw_address",
        "lw_address",
        "sw_address-4",
        "lw_address-4",
        "sw_address+4",
        "lw_address+4",
    )
    # The rv32 file reports the M-mode coverpoint names, and requires S rather than U.
    prefix = "pmpm" if xlen.bits == 32 else "pmpu"
    extension = "S" if xlen.bits == 32 else "U"
    return PmpFile(
        filename="pmpu_na4_legal_lxwr.S",
        xlen=xlen,
        banner=_banner("// Coverpoints : cp_cfg_A_na4 for PMPU is fully covered in this test file.\n", _NA4_TEST_CASES),
        required_extensions=(extension,),
        params=(_NUM_ENTRIES_PARAM, "PMP_NA4_SUPPORTED: true"),
        sigupd=sigupd_count(len(_NA4_CASES) * len(ops)),
        macro_blocks=() if xlen.bits == 32 else (_NA4_RV64_MACRO,),
        body=tuple(_na4_body(xlen)),
        sig_strs=tuple(
            (f"test_{n}", test_case_str(n, f"{prefix}_cfg_A_off_all_{op}")) for n, op in enumerate(ops, start=1)
        ),
        data_align=4,
        data=tuple(_jr_region_data("((1<<(UDB_PMP_GRANULARITY))>>2)")),
    )


#####################################################################
# napot_legal_lxwr-01/-02: one walk over six XWR encodings split
# across two files, accumulating configuration bytes per pmpcfg CSR.
#####################################################################

_NAPOT_TEST_CASES = """\
// Test Cases  : Checking XWR controls accesses in matching NAPOT region. Configuring
//               PMP in M mode and then switching to U mode. For a standard region with
//               pmpcfg_i.L = {0/1}, pmpcfg_i.A=NAPOT, all legal pmpcfg_i.XWR, making
//               {lw, sw, jalr} at that start of region, start - 4, start + 4, highest
//               word in region, just beyond top of the region. Observing proper access
//               faults for restricted regions, and accesses beyond and below the region
//               should succeed because of background region with RWX permissions.
"""

#: The six cases in walk order; each entry lists the names OR-ed into its pmpcfg CSR.
_NAPOT_CASES: list[tuple[str, int, list[str], str]] = [
    ("1000", 5, ["1000"], "No Permissions"),
    ("1001", 4, ["1000", "1001"], "R Permissions"),
    ("1011", 3, ["1011"], "WR Permissions"),
    ("1100", 2, ["1011", "1100"], "X Permissions"),
    ("1101", 1, ["1011", "1100", "1101"], "XR Permissions"),
    ("1111", 0, ["1011", "1100", "1101", "1111"], "XWR Permissions"),
]


def _napot_g_define(xlen: Xlen) -> str:
    # rv64 spells the shift amount without spaces.
    plus = "UDB_PMP_GRANULARITY + 1" if xlen.bits == 32 else "UDB_PMP_GRANULARITY+1"
    return "\n".join(
        [
            "#if UDB_PMP_GRANULARITY != 2",
            "  #define g   (1 << (UDB_PMP_GRANULARITY))",
            "#else",
            f"  #define g   (1 << ({plus}))",
            "#endif",
        ]
    )


def _napot_jalr_check(index: int, advance: list[str], label: int) -> list[str]:
    return [
        *advance,
        f"    LA(x1, {label}f)                          // Store the return Address in x1",
        f"    \\TEST_CASE\\()_{index}:",
        "    jalr ra, 0(a4)",
        "    nop",
        "    nop",
        f"{label}:",
        "    nop",
        "    nop",
        f"    RVTEST_SIGUPD(x2, x5, x4, a4, \\TEST_CASE\\()_{index}, test_{index}_str)",
    ]


def _napot_macro(xlen: Xlen) -> str:
    nop_value = "NOP" if xlen.bits == 32 else "DOUBLE_NOP"
    advances = [
        [],
        ["    addi a4, a4, -4                     // REGIONSTART - 4"],
        ["    addi a4, a4, 8                      // REGIONSTART + 4"],
        ["    li t0, (g-8)", "    add a4, a4, t0                  // REGIONSTART + g - 4"],
        ["    addi a4, a4, 4                      // REGIONSTART + g"],
    ]
    lines = [
        ".macro VERIFICATION_RWX ADDRESS TEST_CASE",
        "",
        "    RVTEST_FENCEI",
        "",
        "    // Execution Access Check",
        "    LA (a4, \\ADDRESS)",
    ]
    for n, advance in enumerate(advances):
        if n:
            lines.append("")
        lines.extend(_napot_jalr_check(17 + n, advance, 1 + n))
    lines.extend(
        [
            "",
            f"    LI(a4, {nop_value})                                             // Value to write ({nop_value})",
            "    // Store Access Check",
            "    LA(a5, \\ADDRESS)                                        // Address to be verified",
        ]
    )
    store_advances = [
        [],
        [],
        [],
        ["    addi a5, a5, -4                                         // REGIONSTART - 4"],
        ["    addi a5, a5, 8                                          // REGIONSTART + 4"],
        ["    li t0, (g-8)", "    add a5, a5, t0                                      // REGIONSTART + g - 4"],
        ["    addi a5, a5, 4                                          // REGIONSTART + g"],
    ]
    for n, advance in enumerate(store_advances, start=1):
        lines.append("")
        if advance:
            lines.extend([*advance, ""])
        lines.extend(_access_check(n, "sb" if n == 1 else "sh" if n == 2 else "sw", extra_nops=1))
    lines.extend(["", "    LA(a5, \\ADDRESS)                                        // Address to be verified"])
    load_steps: list[tuple[str, list[str]]] = [
        ("lb", []),
        ("lbu", []),
        ("lh", []),
        ("lhu", []),
        ("lw", []),
        ("lw", ["    addi a5, a5, -4                                         // REGIONSTART - 4"]),
        ("lw", ["    addi a5, a5, 8                                          // REGIONSTART + 4"]),
        ("lw", ["    li t0, (g-8)", "    add a5, a5, t0                                      // REGIONSTART + g - 4"]),
        ("lw", ["    addi a5, a5, 4                                          // REGIONSTART + g"]),
    ]
    for n, (insn, advance) in enumerate(load_steps, start=8):
        lines.append("")
        if advance:
            lines.extend([*advance, ""])
        check = _access_check(n, insn, extra_nops=1)
        if not (xlen.bits == 64 and n == 16):
            check[-1] += "                                   // Signature update"
        lines.extend(check)
    if xlen.bits == 64:
        lines.extend(["", "    LA(a5, \\ADDRESS)"])
        for n, insn in ((22, "sd"), (23, "ld"), (24, "lwu")):
            lines.append("")
            check = _access_check(n, insn, extra_nops=1)
            if n != 22:
                check[-1] += "                                    // Signature update"
            lines.extend(check)
    lines.extend(["", ".endm"])
    return "\n".join(lines)


def _napot_body(xlen: Xlen, part: int) -> list[str]:
    # rv64 -01 uses the framework macro; the other three files define their own.
    runner = "PMP_VERIFICATION_RWX_NAPOT" if (xlen.bits == 64 and part == 1) else "VERIFICATION_RWX"
    lines = [
        *zero_pmp_regs(xlen),
        "",
        *_lxwr_defines(xlen, [(name, entry) for name, entry, _, _ in _NAPOT_CASES], "PMP_NAPOT", locked=False),
        "",
        regionstart_define(),
        *_mask_defines(xlen),
        "",
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        "",
        VERIFICATION_SECTION_BANNER,
    ]
    cases = _NAPOT_CASES[:3] if part == 1 else _NAPOT_CASES[3:]
    for n, (name, entry, accumulated, perms) in enumerate(cases, start=1 if part == 1 else 4):
        if n not in (1, 4):
            lines.append("")
        # The rv32 banners drop the `L -> b and` clause the rv64 ones keep.
        clause = "" if xlen.bits == 32 else f"L -> {name[0]} and "
        space = " " if xlen.bits == 32 else ""
        lines.append(f"// Test Case: {n} : {space}{clause}{perms} given to the PMP Region {entry}")
        lines.append("")
        lines.extend(set_pmpaddr_napot(entry, addr_reg="x5", tmp_reg="x6"))
        value = "|".join(f"PMPREGION_LXWR_{acc}" for acc in accumulated)
        lines.extend(["", f"    LI(t1, {value})", f"    csrw {cfg_csr(xlen, entry)}, t1"])
        lines.extend(_lower_mode_run(runner, n))
    lines.extend(_EXIT[1:])
    return lines


def _napot_file(xlen: Xlen, part: int) -> PmpFile:
    ops = [
        "sb_address",
        "sh_address",
        "sw_address",
        "sw_address-4",
        "sw_address+4",
        "sw_address+g-4",
        "sw_address+g",
        "lb_address",
        "lbu_address",
        "lh_address",
        "lhu_address",
        "lw_address",
        "lw_address-4",
        "lw_address+4",
        "lw_address+g-4",
        "lw_address+g",
        "jalr_address",
        "jalr_address-4",
        "jalr_address+4",
        "jalr_address+g-4",
        "jalr_address+g",
    ]
    if xlen.bits == 64:
        ops += ["sd_address", "ld_address", "lwu_address"]
    # The rv32 files report the PMPS coverpoint names, and their jalr strings repeat the load indices.
    prefix = "pmps" if xlen.bits == 32 else "pmpu"
    reported = list(range(1, len(ops) + 1))
    if xlen.bits == 32:
        reported[16:21] = [16, 13, 14, 15, 16]
    strs = []
    for n, (op, shown) in enumerate(zip(ops, reported), start=1):
        # The rv64 sd/ld/lwu strings pad their tag one column wider than the rest.
        width = 9 if n <= 21 else 10
        strs.append((f"test_{n}", test_case_str(shown, f"{prefix}_napot_legal_lwxr_{op}", width)))
    # rv64 -01 is the only file whose coverpoint line lists cp_cfg_A_napot as partially covered.
    if xlen.bits == 64 and part == 1:
        coverpoints = (
            "// Coverpoints : cp_cfg_X, cp_cfg_A_napot and cp_cfg_RW from PMPU are partially covered in this\n"
            "//                 test file.\n"
        )
    else:
        coverpoints = (
            "// Coverpoints : cp_cfg_X and cp_cfg_RW from PMPU are partially covered in this\n"
            "//                 test file. cp_cfg_A_napot is fully covered.\n"
        )
    macros = [_napot_g_define(xlen)]
    if not (xlen.bits == 64 and part == 1):
        macros.append(_napot_macro(xlen))
    return PmpFile(
        filename=f"pmpu_napot_legal_lxwr-0{part}.S",
        xlen=xlen,
        banner=_banner(coverpoints, _NAPOT_TEST_CASES),
        required_extensions=("U",),
        params=(_NUM_ENTRIES_PARAM, "PMP_NAPOT_SUPPORTED: true"),
        sigupd=sigupd_count(3 * len(ops)),
        macro_blocks=tuple(macros),
        body=tuple(_napot_body(xlen, part)),
        sig_strs=tuple(strs),
        data_align=4,
        data=tuple(_jr_region_data("(g>>2)")),
    )


#####################################################################
# tor_legal_lxwr-01/-02: one granule-sized TOR region, six XWR
# encodings split across two files.
#####################################################################

_TOR_TEST_CASES = """\
// Test Cases  : Configuring PMP in M mode and then switching to U mode.
//               Checking XWR controls accesses in matching TOR region. With
//               pmpcfg_i.L =1, pmpcfg_i.A = TOR, all legal pmpcfg_i.XWR,
//               default TOR region, address-g in pmpaddr_i-1: making {lw,sw,jalr}
//               address, address-4, address-g, address-g-4.  Observing proper
//               access faults for restricted regions.
"""

#: (LXWR name, top PMP entry, permission name) for the six cases, in walk order.
_TOR_CASES: list[tuple[str, int, str]] = [
    ("0000", 5, "No Permissions"),
    ("0001", 3, "R Permissions"),
    ("0011", 1, "WR Permissions"),
    ("0100", 5, "X Permissions"),
    ("0101", 3, "RX Permissions"),
    ("0111", 1, "XWR Permissions"),
]


def _tor_body(xlen: Xlen, part: int) -> list[str]:
    cases = _TOR_CASES[:3] if part == 1 else _TOR_CASES[3:]
    lines = [
        *zero_pmp_regs(xlen),
        "",
        *_lxwr_defines(xlen, [(name, entry) for name, entry, _ in cases], "PMP_TOR  ", locked=False),
        "#define REGIONSTART            TEST_FOR_EXECUTION        // RAM_BASE_ADDR + PROGRAM_SIZE",
        "",
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        VERIFICATION_SECTION_BANNER,
    ]
    for n, (name, entry, perms) in enumerate(cases, start=1 if part == 1 else 4):
        if n not in (1, 4):
            lines.append("")
        lines.append(f"// Test Case: {n} : L -> 0 and {perms} given to the PMP Region {entry}")
        lines.extend(
            [
                "",
                "    LA(x6, REGIONSTART)",
                "    li t0, g",
                "    add x6, x6, t0",
                "    srl x6, x6, PMP_SHIFT",
                f"    csrw pmpaddr{entry}, x6",
                "    LA(x5, REGIONSTART)",
                "    srl x5, x5, PMP_SHIFT",
                f"    csrw pmpaddr{entry - 1}, x5",
                f"    LI(x4, PMPREGION_LXWR_{name})",
                f"    csrw {cfg_csr(xlen, entry)}, x4",
            ]
        )
        lines.extend(_lower_mode_run("PMP_VERIFICATION_RWX_LEGAL", n))
    lines.extend(_EXIT)
    return lines


def _tor_file(xlen: Xlen, part: int) -> PmpFile:
    ops = [f"{insn}_address{suffix}" for insn in ("jalr", "sw", "lw") for suffix in ("", "-4", "+4", "+g-4", "+g")]
    return PmpFile(
        filename=f"pmpu_tor_legal_lxwr-0{part}.S",
        xlen=xlen,
        copyright=_COPYRIGHT_QUALCOMM if (xlen.bits == 32 and part == 1) else _COPYRIGHT,
        banner=_banner(
            "// Coverpoints : cp_cfg_A_tor for PMPU is partially covered in this test file.\n", _TOR_TEST_CASES
        ),
        required_extensions=("U",),
        params=(_NUM_ENTRIES_PARAM, "PMP_TOR_SUPPORTED: true"),
        sigupd=sigupd_count(3 * len(ops)),
        pre_main=("#define g    (1<<(UDB_PMP_GRANULARITY))",),
        body=tuple(_tor_body(xlen, part)),
        sig_strs=tuple((f"test_{n}", test_case_str(n, f"cp_cfg_A_tor_{op}")) for n, op in enumerate(ops, start=1)),
        data_align=4,
        data=tuple(_jr_region_data("((1<<(UDB_PMP_GRANULARITY))>>2)")),
    )


@add_pmp_suite("PMPU")
def build() -> list[PmpFile]:
    """Eleven files per XLEN: A=OFF, XWR walks, CSR access, MPRV, and NA4/NAPOT/TOR walks."""
    files: list[PmpFile] = []
    for xlen in XLENS.values():
        files.append(_a_off_file(xlen))
        files.append(_xwr_file(xlen, unlocked=False))
        files.append(_xwr_file(xlen, unlocked=True))
        files.append(_csr_access_file(xlen))
        files.extend(_mprv_file(xlen, part) for part in (1, 2))
        files.append(_na4_file(xlen))
        files.extend(_napot_file(xlen, part) for part in (1, 2))
        files.extend(_tor_file(xlen, part) for part in (1, 2))
    return files
