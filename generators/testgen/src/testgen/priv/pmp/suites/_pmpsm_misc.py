##################################
# priv/pmp/suites/_pmpsm_misc.py
#
# PMPSm: the non-pmpcfg_walk, non-cfg_* families of the machine-mode PMP suite.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMPSm families other than ``cfg_*`` and ``pmpcfg_walk``."""

from __future__ import annotations

from testgen.priv.pmp.macros import (
    LOCKED_LXWR_CASES,
    LXWR_PERM_NAMES,
    NAPOT_MASK_DEFINES,
    cfg_csr,
    cfg_shift,
    lxwr_defines,
    sigupd_count,
    template,
    test_case_str,
)
from testgen.priv.pmp.model import XLENS, PmpFile, Xlen

#####################################################################
# Banners
#####################################################################

_COPYRIGHT_LINE = "// Copyright (C) 2025 Harvey Mudd College & Oklahoma State University, UET Lahore, Habib University"
_QUALCOMM_LINE = "// Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries."


def _copyright(qualcomm: bool = False) -> tuple[str, ...]:
    lines = [_COPYRIGHT_LINE]
    if qualcomm:
        lines.append(_QUALCOMM_LINE)
    lines.extend(["// SPDX-License-Identifier: Apache-2.0", "//"])
    return tuple(lines)


_STANDARD_DESCRIPTION = """\
// Description : This test verifies the functionality and enforcement of
//               Physical Memory Protection (PMP) configurations in RISC-V
//               systems. It specifically tests the Read, Write, and Execute
//               permissions for a designated memory region, ensuring that
//               the PMP settings are correctly applied and that the system
//               behaves as expected when accessing this region.
//
"""

_AUTHORS = ("Umer Shahid, Allen Baum, David Harris", "Muhammad Abdullah, Hamza Ali, Muhammad Zain")


def _heading(title: str, description: str, *, wide: bool, carlin: bool = False) -> str:
    """Title/Authors/Description block; ``wide`` is the rv64 column layout."""
    label = 16 if wide else 13
    indent = 18 if wide else 16
    lines = [
        f"// {'Title':<{label}}: {title}",
        f"// {'Authors':<{label}}: {_AUTHORS[0]}",
        f"//{'':<{indent}}{_AUTHORS[1]}",
    ]
    if carlin:
        lines.append(f"//{'':<{indent}}Jordan Carlin")
    lines.extend(["//", description.rstrip("\n")])
    return "\n".join(lines) + "\n"


def _banner(heading: str, coverpoints: str, test_cases: str) -> str:
    """One file's full comment banner."""
    return f"{heading}{coverpoints}{test_cases}"


#####################################################################
# Shared assembly fragments
#####################################################################

#: `// ... Verification Section` banner; the rv64 files indent it two columns further.
_VERIF_BANNER = {32: f"//{'':<42}Verification Section", 64: f"//{'':<44}Verification Section"}

_RETURN_TRAMPOLINE = [
    "RETURN_INSTRUCTION:",
    "    nop",
    "    nop",
    f"    jr ra{'':<56}// Get back to the point from where TEST_FOR_EXECUTION was called.",
]

#: The `g` (granule size) define, in the two spellings the suite uses.
_G_IF_BLOCK = """\
#if UDB_PMP_GRANULARITY != 2
  #define g   (1 << (UDB_PMP_GRANULARITY))
#else
  #define g   (1 << (UDB_PMP_GRANULARITY + 1))
#endif
"""
_G_PLAIN = "#define g    (1<<(UDB_PMP_GRANULARITY))"

_PAD_COMMENT = {
    32: "// one PMP granule of jr-ra fillers: puts TEST_FOR_EXECUTION on the next granule boundary (= PMP_REGION_START at coverage grain 2), while staying naturally aligned for NAPOT at larger grains",
    64: "// one PMP granule of return-instruction fillers: places the region on the next granule boundary (= PMP_REGION_START at coverage grain 2), grain-aligned at larger grains",
}

_NAPOT_PAD_COMMENT = "// NAPOT region must be 8-byte aligned at grain 2 -> region at 0x80005008 (pmpaddr=STANDARD_REGION). A 4-byte pad (0x80005004) yields a 16-byte NAPOT covering the pad -> hang."

_ALL_ENTRIES_PAD_COMMENT = "// g_napot-byte pad -> NAPOT region-under-test at 0x80005008 (PMP_NAPOT_REGION_START); pmpaddr matches STANDARD_REGION, region does not cover the pad"


def _exec_region(
    *,
    pad_rept: str,
    pad_comment: str = "",
    comment_col: int = 56,
    pad_insn: str = "jr ra",
    top_align: bool = True,
    mid_align: bool = False,
    body_rept: str = "(1<<(UDB_PMP_GRANULARITY))",
    body_insn: str = "nop",
    blank_after_top: bool = False,
) -> list[str]:
    """`TEST_FOR_EXECUTION_0` pad, the region under test, and the return trampoline."""
    lines = [".p2align 12"]
    if top_align:
        lines.append(".p2align (UDB_PMP_GRANULARITY)")
    if blank_after_top:
        lines.append("")
    rept = f"    .rept {pad_rept}"
    if pad_comment:
        rept = f"{rept:<{comment_col}}{pad_comment}"
    lines.extend(["TEST_FOR_EXECUTION_0:", rept, f"    {pad_insn}", "    .endr", ""])
    if mid_align:
        lines.append(".p2align (UDB_PMP_GRANULARITY)")
    lines.extend(
        [
            "TEST_FOR_EXECUTION:",
            f"    .rept {body_rept}",
            f"    {body_insn}",
            "    .endr",
            "",
            *_RETURN_TRAMPOLINE,
        ]
    )
    return lines


def _zero_regs(xlen: Xlen, *, tight: bool = False) -> list[str]:
    """Clear every implemented pmpcfg and pmpaddr CSR."""
    cfg_head = "// Zero all pmpcfg registers" if tight else "// Loop to SET ALL pmpcfg REGs to zero"
    addr_head = "// Zero all pmpaddr registers" if tight else "// Loop to SET ALL pmpaddr REGs to zero"
    return [
        f"    {cfg_head}",
        "    .set pmpcfgi, CSR_PMPCFG0",
        f"    .rept {xlen.cfg_rept}",
        f"    csrw pmpcfgi{'' if tight else ' '}, x0",
        f"    .set pmpcfgi, pmpcfgi+{xlen.cfg_step}",
        "    .endr",
        "",
        f"    {addr_head}",
        "    .set pmpaddri, CSR_PMPADDR0",
        "    .rept UDB_NUM_PMP_ENTRIES",
        "    csrw pmpaddri, x0",
        "    .set pmpaddri, pmpaddri+1",
        "    .endr",
    ]


def _napot_addr(entry: int, *, tight: bool = False) -> list[str]:
    """Program pmpaddr<entry> with the NAPOT encoding of REGIONSTART."""
    sep = "," if tight else ", "
    return [
        "    LA(x5, REGIONSTART)",
        "    srl x5, x5, PMP_SHIFT",
        f"    LI(x6{sep}PMP_MASK)",
        "    and x5, x5, x6",
        f"    LI(x6{sep}PMP_REGION_SIZE)",
        "    or x5, x5, x6",
        f"    csrw pmpaddr{entry}, x5",
    ]


def _case_comment(index: int, lxwr: str, entry: int) -> str:
    perms = LXWR_PERM_NAMES.get(lxwr[1:], f"{lxwr[1:]} Permissions")
    return f"// Test Case: {index} : L -> {lxwr[0]} and {perms} given to the PMP Region {entry}"


def _params(amode: str | None = None) -> tuple[str, ...]:
    params = ["NUM_PMP_ENTRIES: '>0'"]
    if amode is not None:
        params.append(f"PMP_{amode.upper()}_SUPPORTED: true")
    return tuple(params)


#####################################################################
# pmpsm_grain / pmpsm_grain_check: pmpaddr readback versus the grain
#####################################################################

_GRAIN_MODE_DEFINES = {
    32: [
        "#define PMPREGION_OFF       ((((     PMP_R|PMP_W|PMP_X)            &0xFF) << PMP0_CFG_SHIFT))",
        "#define PMPREGION_NAPOT     ((((     PMP_R|PMP_W|PMP_X |PMP_NAPOT) &0xFF) << PMP0_CFG_SHIFT))",
        "#define PMPREGION_TOR       ((((     PMP_R|PMP_W|PMP_X |PMP_TOR)   &0xFF) << PMP0_CFG_SHIFT))",
    ],
    64: [
        "#define PMPREGION_OFF          ((((     PMP_R|PMP_W|PMP_X)               &0xFF) << PMP0_CFG_SHIFT))",
        "#define PMPREGION_NAPOT     ((((     PMP_R|PMP_W|PMP_X |PMP_NAPOT) &0xFF) << PMP0_CFG_SHIFT))",
        "#define PMPREGION_TOR          ((((     PMP_R|PMP_W|PMP_X |PMP_TOR)   &0xFF) << PMP0_CFG_SHIFT))",
    ],
}

#: (pattern name, value written to pmpaddr0) per XLEN.
_GRAIN_PATTERNS = {
    32: [("all 0s", "0"), ("all 1s", "-1"), ("checkerboard", "0xAAAAAAAA")],
    64: [("all 0s", "0"), ("all 1s", "-1"), ("checkerboard", "CHECKERBOARD")],
}

#: The group banners spell the checkerboard pattern out; the write comments do not.
_GRAIN_BANNER_PATTERN = {"checkerboard": "checkerboard pattern(1010...)"}

_GRAIN_READBACKS = ("OFF", "NAPOT", "TOR")

_GRAIN_HEADING = """\
// Description : This test verifies PMP address grain readback behavior.
//               It writes pmpaddr0 in OFF and NAPOT modes, changes the
//               address-matching mode, and checks the grain-controlled
//               low pmpaddr bits.
//
"""

_GRAIN_CHECK_HEADING = """\
// Description : This test verifies PMP address grain discovery.
//               It writes ones to pmpaddr0 with pmpcfg0 set to OFF and
//               checks the low bits needed to identify the grain.
//
"""


def _grain_test_cases(xlen: Xlen) -> str:
    pad = 16 if xlen.bits == 64 else 14
    return (
        "// Test case  : Checking that low bits read as 0/1s depending on grain and address\n"
        f"//{'':<{pad}}matching mode. Set up pmpcfg0.L = 0, pmpcfg.A = {{OFF/NAPOT}}, write\n"
        f"//{'':<{pad}}pmpaddr0 = {{all 0s / all 1s / checkerboard}}. Change pmpcfg.A to\n"
        f"//{'':<{pad}}{{OFF/TOR/NAPOT}} and read back pmpaddr0. Bottom G-1 bits always read\n"
        f"//{'':<{pad}}as 1s in NAPOT. Bottom G bits read as 0s in TOR/OFF.\n"
    )


def _grain_check_test_cases(xlen: Xlen) -> str:
    pad = 16 if xlen.bits == 64 else 14
    tail = "//\n" if xlen.bits == 64 else ""
    return (
        "// Test case  : Checking that granularity matches expectations. We write 0\n"
        f"//{'':<{pad}}to pmpcfg0, all 1s to pmpaddr0, and then read back pmpaddr0.\n"
        f"//{'':<{pad}}Index of least-significant bit set should be G.\n" + tail
    )


def _grain_readback(index: int, pattern: str, write_mode: str, value: str, read_mode: str) -> list[str]:
    """One write-then-read-back pair, with its signature update."""
    # "Read back in  TOR" keeps its doubled space only in the first group.
    gap = "  " if index == 3 else " "
    return [
        f"// Write {pattern} in {write_mode}",
        "",
        f"    LI(x6, PMPREGION_{write_mode})",
        "    csrw pmpcfg0, x6",
        f"    LI(x6, {value})",
        "    csrw pmpaddr0, x6",
        "",
        f"// Read back in{gap}{read_mode}",
        "",
        f"    LI(x6, PMPREGION_{read_mode})",
        "    csrw pmpcfg0, x6",
        f"    test_{index}:",
        "        csrr x7, pmpaddr0",
        "        and x7, x7, t3",
        f"        RVTEST_SIGUPD(x2, x5, x4, x7, test_{index}, test_{index}_str)",
        "",
    ]


def _grain_body(xlen: Xlen) -> list[str]:
    lines = [*_zero_regs(xlen), ""]
    lines.extend(_GRAIN_MODE_DEFINES[xlen.bits])
    lines.extend(["", "#define PMP_GRAIN_MASK     ((1 << (UDB_PMP_GRANULARITY - 2)) - 1)", ""])
    if xlen.bits == 64:
        lines.append("#define REGIONSTART            TEST_FOR_EXECUTION        // RAM_BASE_ADDR + PROGRAM_SIZE")
        lines.append("#define CHECKERBOARD        0xAAAAAAAAAAAAAAAA")
    else:
        lines.append("#define REGIONSTART         TEST_FOR_EXECUTION")
    lines.extend(
        [
            "",
            "",
            "    RVTEST_PMP_SET_BACKGROUND x4",
            "",
            "    LA(x4, REGIONSTART)",
            "    srl x4, x4, PMP_SHIFT",
            f"    csrw{'     ' if xlen.bits == 64 else ' '}pmpaddr0, x4",
            "",
            "    LI(t3, PMP_GRAIN_MASK)",
            f"{'':<48}//Verification Section",
        ]
    )
    index = 0
    case = 0
    for pattern, value in _GRAIN_PATTERNS[xlen.bits]:
        for write_mode in ("NAPOT", "OFF"):
            case += 1
            indent = "    " if (case == 1 and xlen.bits == 64) else ""
            lines.append(
                f"{indent}// Test Case {case}: Writing {_GRAIN_BANNER_PATTERN.get(pattern, pattern)}"
                f" in pmpaddr0 when A = {write_mode}"
                " and read back when A= {OFF,NAPOT,TOR}"
            )
            for read_mode in _GRAIN_READBACKS:
                index += 1
                block = _grain_readback(index, pattern, write_mode, value, read_mode)
                if read_mode == "TOR":
                    lines.extend(["#ifdef UDB_PMP_TOR_SUPPORTED", "", *block, "#endif", ""])
                else:
                    lines.extend(["", *block])
    lines.append("    RVTEST_GOTO_MMODE")
    return lines


def _grain_file(xlen: Xlen) -> PmpFile:
    patterns = {"all 0s": "zeros", "all 1s": "ones", "checkerboard": "checkerboard"}
    strs = [
        (f"test_{n}", f"write {patterns[pattern]} with A={write}, read back with A={read}; cp: cp_grain")
        for n, (pattern, write, read) in enumerate(
            (
                (pattern, write, read)
                for pattern, _ in _GRAIN_PATTERNS[64]
                for write in ("NAPOT", "OFF")
                for read in _GRAIN_READBACKS
            ),
            start=1,
        )
    ]
    return PmpFile(
        filename="pmpsm_grain.S",
        xlen=xlen,
        copyright=_copyright(qualcomm=True),
        banner=_banner(
            _heading("PMP address grain readback verification", _GRAIN_HEADING, wide=xlen.bits == 64, carlin=True),
            "// Coverpoints: cp_grain for PMPSm is fully covered in this test file.\n//\n",
            _grain_test_cases(xlen),
        ),
        required_extensions=("Sm",),
        params=_params(),
        priv_test=False,
        sigupd=sigupd_count(18),
        body=tuple(_grain_body(xlen)),
        sig_strs=tuple(strs),
        data_align=4 if xlen.bits == 32 else None,
        data=tuple(
            template("exec_region_pad_granule").strip("\n").splitlines()
            if xlen.bits == 64
            else _exec_region(
                pad_rept="(1 << (UDB_PMP_GRANULARITY - 2))", pad_comment=_PAD_COMMENT[32], top_align=False
            )
        ),
    )


def _grain_check_body(xlen: Xlen) -> list[str]:
    lines = [*_zero_regs(xlen), "", ""]
    if xlen.bits == 64:
        lines.append("#define REGIONSTART            TEST_FOR_EXECUTION        // RAM_BASE_ADDR + PROGRAM_SIZE")
    else:
        lines.append("#define REGIONSTART         TEST_FOR_EXECUTION")
    lines.extend(
        [
            "",
            "    RVTEST_PMP_SET_BACKGROUND x4",
            "",
            f"    LA(x4, {'REGIONSTART' if xlen.bits == 64 else 'TEST_FOR_EXECUTION'})",
            "    srl x4, x4, PMP_SHIFT",
            f"    csrw{' ' if xlen.bits == 64 else '    '}pmpaddr0, x4",
            "",
            _VERIF_BANNER[xlen.bits],
            "// Test Case: Write 0 to pmpcfg0, all 1s to pmpaddr0, read back pmpaddr0.",
            "",
            "    LI(x6, 0)",
            "    csrw pmpcfg0, x6",
            "    LI(x6, -1)",
            "    csrw pmpaddr0, x6",
            "    LI(t3, PMP_GRAIN_CHECK_MASK)",
            "    test_0:",
            "        csrr x7, pmpaddr0",
            "        and x7, x7, t3",
            "        RVTEST_SIGUPD(x2, x5, x4, x7, test_0, test_0_str)",
            "",
        ]
    )
    if xlen.bits == 64:
        lines.append("    RVTEST_GOTO_MMODE")
    return lines


def _grain_check_file(xlen: Xlen) -> PmpFile:
    return PmpFile(
        filename="pmpsm_grain_check.S",
        xlen=xlen,
        copyright=_copyright(qualcomm=True),
        banner=_banner(
            _heading(
                "PMP address grain discovery verification", _GRAIN_CHECK_HEADING, wide=xlen.bits == 64, carlin=True
            ),
            "// Coverpoints: cp_grain_check for PMPSm is fully covered in this test file.\n//\n",
            _grain_check_test_cases(xlen),
        ),
        required_extensions=("Sm",),
        params=_params(),
        priv_test=False,
        sigupd=sigupd_count(1),
        post_include_defines=("#define PMP_GRAIN_CHECK_MASK ((1 << (UDB_PMP_GRANULARITY - 1)) - 1)",),
        body=tuple(_grain_check_body(xlen)),
        sig_strs=(("test_0", "write ones to pmpaddr0 and check grain low bits; cp: cp_grain_check"),),
        data_align=4 if xlen.bits == 32 else None,
        data=tuple(
            template("exec_region_pad_granule").strip("\n").splitlines()
            if xlen.bits == 64
            else _exec_region(
                pad_rept="(1 << (UDB_PMP_GRANULARITY - 2))", pad_comment=_PAD_COMMENT[32], top_align=False
            )
        ),
    )


#####################################################################
# pmpsm_pmpaddr_upper: the architecturally zero high pmpaddr bits
#####################################################################

_PMPADDR_UPPER_HEADING = """\
// Description : This test verifies the architecturally fixed upper bits of RV64
//               pmpaddr CSRs. It writes ones to implemented pmpaddr CSRs and
//               checks bits 63:54 read back as zero.
//
"""

_PMPADDR_UPPER_BODY = [
    "    RVTEST_GOTO_MMODE",
    "",
    "    // -----------------------------------------------------------------------",
    "    // Verify upper 10 pmpaddr bits remain zero after writing ones",
    "    // -----------------------------------------------------------------------",
    "    LI(t0, -1)",
    "    LI(t1, 0xFFC0000000000000)",
    "    .set pmpaddri, CSR_PMPADDR0",
    "    .rept UDB_NUM_PMP_ENTRIES",
    "1:  csrw pmpaddri, t0",
    "    csrr t2, pmpaddri",
    "    and t2, t2, t1",
    "    RVTEST_SIGUPD(x2, x5, x4, t2, 1b, test_0_str)",
    "    .set pmpaddri, pmpaddri+1",
    "    .endr",
    "",
    "    RVTEST_GOTO_MMODE",
]


def _pmpaddr_upper_file() -> PmpFile:
    return PmpFile(
        filename="pmpsm_pmpaddr_upper.S",
        xlen=XLENS[64],
        copyright=_copyright(qualcomm=True),
        banner=_banner(
            _heading("PMP address upper-bits verification", _PMPADDR_UPPER_HEADING, wide=True, carlin=True),
            "// Coverpoints : cp_pmpaddr_upper_zero for PMPSm is fully covered in\n//               this test file.\n//\n",
            "// Test Cases  : Write ones to pmpaddr CSRs and check bits 63:54 read back as zero.\n",
        ),
        required_extensions=("Sm",),
        params=_params(),
        sigupd=sigupd_count(64),
        body=tuple(_PMPADDR_UPPER_BODY),
        sig_strs=(("test_0", "write ones to pmpaddr CSRs and check bits 63:54 are zero; cp: cp_pmpaddr_upper_zero"),),
    )


#####################################################################
# pmpsm_{na4,napot,tor}_legal_l*wr: every legal locked LXWR against
# one region in each address mode
#####################################################################

_LEGAL_COVERPOINTS = {
    "na4": "// Coverpoints : cp_cfg_A_na4 for PMPM is fully covered in this test file.\n//\n",
    "napot": {
        32: "// Coverpoints : cp_cfg_A_napot, cp_cfg_X and cp_cfg_RW for PMPM are fully covered\n//               in this test file.\n//\n",
        64: "// Coverpoints : cp_cfg_A_napot, cp_cfg_X and cp_cfg_RW for PMPM are fully covered\n//                 in this test file.\n//\n",
    },
    "tor": "// Coverpoints : cp_cfg_A_tor for PMPM is partially covered in this test file.\n//\n",
}

_NA4_TEST_CASES = """\
// Test Cases  : Checking XWR controls accesses in matching NA4 region. G=0 Only
//               with pmpcfg_i.L = 1, pmpcfg_i.A=NA4, all legal pmpcfg_i.XWR,
//               reasonable address in pmpaddr: making {lw, sw, jalr} at that
//               address, that address - 4, just beyond top of the region.
//               Observing proper access faults for restricted regions, and
//               accesses beyond the region and below the region should succeed
//               because the bckground region is set to RWX.
"""

_TOR_TEST_CASES = """\
// Test Cases  : Checking XWR controls accesses in matching TOR region. With
//               pmpcfg_i.L =1, pmpcfg_i.A = TOR, all legal pmpcfg_i.XWR,
//               default TOR region, address-g in pmpaddr_i-1: making {lw,sw,jalr}
//               address, address-4, address-g, address-g-4.  Observing proper
//               access faults for restricted regions.
"""


def _napot_test_cases(xlen: Xlen) -> str:
    pad = 17 if xlen.bits == 64 else 15
    return (
        "// Test Cases  : Checking XWR controls accesses in matching NAPOT region. For a\n"
        f"//{'':<{pad}}standard region with pmpcfg_i.L = 1, pmpcfg_i.A=NAPOT, all\n"
        f"//{'':<{pad}}legal pmpcfg_i.XWR: making {{lw, sw, jalr}} at that start of region,\n"
        f"//{'':<{pad}}start - 4, start + 4, highest word in region, just beyond top\n"
        f"//{'':<{pad}}of the region. Observing proper access faults for restricted\n"
        f"//{'':<{pad}}regions, and accesses beyond the region and below the region\n"
        f"//{'':<{pad}}should succeed because the bckground region is set to RWX.\n"
    )


#: NA4 reports its coverpoints under different names on the two XLENs.
_NA4_SIG_STRS = {
    32: ["pmpm_aligned_sw_address", "pmpm_aligned_lw_address"],
    64: ["cp_cfg_A_na4_sw_address", "cp_cfg_A_na4_lw_address"],
}

_NAPOT_SIG_STRS = {
    32: [
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
    ],
    64: [
        "sb_address",
        "sh_address",
        "sw_address",
        "sd_address",
        "sw_address-4",
        "sw_address+4",
        "sw_address+g-4",
        "sw_address+g",
        "lb_address",
        "lbu_address",
        "lh_address",
        "lhu_address",
        "lw_address",
        "lwu_address",
        "ld_address",
        "lw_address-4",
        "lw_address+4",
        "lw_address+g-4",
        "lw_address+g",
        "x_address",
        "x_address-4",
        "x_address+4",
        "x_address+g-4",
        "x_address+g",
    ],
}

_TOR_SIG_STRS = [
    "sw_address",
    "sw_address-4",
    "sw_address+4",
    "sw_address+g-4",
    "sw_address+g",
    "lw_address",
    "lw_address-4",
    "lw_address+4",
    "lw_address+g-4",
    "lw_address+g",
]

#: NA4/NAPOT/TOR entry assignment: the most permissive case gets the highest priority.
_TOR_CASES = [("1000", 5), ("1001", 3), ("1011", 1), ("1100", 5), ("1101", 3), ("1111", 1)]

#: Copy-pasted "No Permissions" banner on the LXWR=1101 case of the na4 files.
_NA4_BANNER_OVERRIDE = {5: "No Permissions"}

#: Copy-pasted permission names in the tor files' case banners.
_TOR_PERM_NAMES = {"1000": "No", "1001": "R", "1011": "WR", "1100": "X", "1101": "RX", "1111": "XWR"}


def _na4_body(xlen: Xlen) -> list[str]:
    lines = [*_zero_regs(xlen), ""]
    lines.extend(lxwr_defines(xlen, LOCKED_LXWR_CASES, "PMP_NA4  "))
    lines.append("")
    if xlen.bits == 64:
        lines.append("#define REGIONSTART        TEST_FOR_EXECUTION        // RAM_BASE_ADDR + PROGRAM_SIZE")
    else:
        lines.append("#define REGIONSTART     TEST_FOR_EXECUTION")
    lines.extend(["", "    RVTEST_PMP_SET_BACKGROUND x4"])
    if xlen.bits == 32:
        lines.append("")
    lines.append(_VERIF_BANNER[xlen.bits])
    sep = "," if xlen.bits == 64 else ", "
    for n, (lxwr, entry) in enumerate(LOCKED_LXWR_CASES, start=1):
        perms = _NA4_BANNER_OVERRIDE.get(n)
        banner = (
            f"// Test Case: {n} : L -> {lxwr[0]} and {perms} given to the PMP Region {entry}"
            if perms
            else _case_comment(n, lxwr, entry)
        )
        lines.extend(
            [
                banner,
                "",
                "    LA(x5, REGIONSTART)",
                "    srl x5, x5, PMP_SHIFT",
                f"    csrw pmpaddr{entry}, x5",
                "",
                f"    LI(x4, PMPREGION_LXWR_{lxwr})",
                f"    csrw {cfg_csr(xlen, entry)}, x4",
                "",
                "    RVTEST_SFENCE_VMA_IF_SUPPORTED",
                f"    VERIFICATION_RWX    TEST_FOR_EXECUTION{sep}test_{n}",
                "",
            ]
        )
    return lines[:-1]


def _na4_file(xlen: Xlen) -> PmpFile:
    return PmpFile(
        filename="pmpsm_na4_legal_lwxr.S",
        xlen=xlen,
        copyright=_copyright(),
        banner=_banner(
            _heading(
                "Comprehensive PMP (Physical Memory Protection) Verification",
                _STANDARD_DESCRIPTION,
                wide=xlen.bits == 64,
            ),
            _LEGAL_COVERPOINTS["na4"],
            _NA4_TEST_CASES + "\n",
        ),
        required_extensions=("Sm",),
        params=_params("na4"),
        priv_test=False,
        sigupd=sigupd_count(len(LOCKED_LXWR_CASES) * 6),
        macro_blocks=(template(f"pmpsm_misc_rwx_na4_{xlen.bits}"),),
        body=tuple(_na4_body(xlen)),
        sig_strs=tuple(
            (f"test_{n}", test_case_str(n, f"{_NA4_SIG_STRS[xlen.bits][(n - 1) % 2]}{suffix}"))
            for n, suffix in enumerate(("", "", "-4", "-4", "+4", "+4"), start=1)
        ),
        data_align=4,
        data=tuple(
            _exec_region(
                pad_rept="(1 << (UDB_PMP_GRANULARITY - 2))",
                pad_comment=_PAD_COMMENT[xlen.bits],
                mid_align=xlen.bits == 32,
            )
        ),
    )


def _napot_body(xlen: Xlen, cases: list[tuple[str, int]], *, first: int, exit_label: bool) -> list[str]:
    tight = xlen.bits == 32
    lines = [*_zero_regs(xlen), ""]
    lines.extend(lxwr_defines(xlen, LOCKED_LXWR_CASES, "PMP_NAPOT"))
    lines.append("")
    if xlen.bits == 64:
        lines.append("#define REGIONSTART            TEST_FOR_EXECUTION    // RAM_BASE_ADDR + PROGRAM_SIZE")
    else:
        lines.append("#define REGIONSTART         TEST_FOR_EXECUTION")
    lines.extend(NAPOT_MASK_DEFINES)
    lines.extend(["", "    RVTEST_PMP_SET_BACKGROUND x4", "", _VERIF_BANNER[xlen.bits]])
    runner = "VERIFICATION_RWX" if xlen.bits == 32 else "PMP_VERIFICATION_RWX_NAPOT_SM_RV64"
    for offset, (lxwr, entry) in enumerate(cases):
        n = first + offset
        lines.extend(
            [
                _case_comment(n, lxwr, entry),
                "",
                *_napot_addr(entry, tight=tight),
                "",
                f"    LI(x4, PMPREGION_LXWR_{lxwr})",
                f"    csrw {cfg_csr(xlen, entry)}, x4",
                "",
                "    RVTEST_SFENCE_VMA_IF_SUPPORTED",
                f"    {runner}    TEST_FOR_EXECUTION, test_{n}",
                "",
            ]
        )
    if exit_label:
        lines.extend([f"{'    j exit':<66}// Verification Complete, exit the test", "", "", "exit:"])
    else:
        lines = lines[:-1]
    return lines


def _napot_file(xlen: Xlen, *, part: int | None = None) -> PmpFile:
    cases = LOCKED_LXWR_CASES if part is None else LOCKED_LXWR_CASES[3 * (part - 1) : 3 * part]
    first = 1 if part is None else 3 * (part - 1) + 1
    stem = "pmpsm_napot_legal_lwxr.S" if part is None else f"pmpsm_napot_legal_lxwr-{part:02d}.S"
    coverpoints = _NAPOT_SIG_STRS[xlen.bits]
    prefix = "pmpm_aligned" if xlen.bits == 32 else "cp_cfg_A_napot"
    return PmpFile(
        filename=stem,
        xlen=xlen,
        copyright=_copyright(),
        banner=_banner(
            _heading(
                "Comprehensive PMP (Physical Memory Protection) Verification",
                _STANDARD_DESCRIPTION,
                wide=xlen.bits == 64,
            ),
            _LEGAL_COVERPOINTS["napot"][xlen.bits],
            _napot_test_cases(xlen) + ("\n" if xlen.bits == 32 else ""),
        ),
        required_extensions=("Sm",),
        params=_params("napot"),
        priv_test=False,
        sigupd=sigupd_count(len(cases) * len(coverpoints)),
        macro_blocks=((_G_IF_BLOCK,) if xlen.bits == 64 else (_G_IF_BLOCK, template("pmpsm_misc_rwx_napot_32"))),
        body=tuple(_napot_body(xlen, cases, first=first, exit_label=part == 1)),
        sig_strs=tuple(
            (f"test_{n}", test_case_str(n, f"{prefix}_{cp}", 9)) for n, cp in enumerate(coverpoints, start=1)
        ),
        data_align=10 if xlen.bits == 32 else 4,
        data=tuple(
            _exec_region(
                pad_rept="(g>>2)",
                pad_comment=_NAPOT_PAD_COMMENT,
                comment_col=57,
                pad_insn="nop" if xlen.bits == 32 else "jr ra",
                mid_align=xlen.bits == 32,
                blank_after_top=xlen.bits == 32,
            )
        ),
    )


_TOR_SETUP = [
    "    LA(x4, TEST_FOR_EXECUTION)",
    "    LI(t0, g)",
    "    add x5, x4, t0",
    "    srl x4, x4, PMP_SHIFT",
    "    srl x5, x5, PMP_SHIFT",
    "",
    "    .set pmpaddri, CSR_PMPADDR0",
    "    .rept 3",
    "    csrw pmpaddri, x4",
    "    .set pmpaddri, pmpaddri+1",
    "    csrw pmpaddri, x5",
    "    .set pmpaddri, pmpaddri+1",
    "    .endr",
]


def _tor_body(xlen: Xlen, part: int) -> list[str]:
    cases = _TOR_CASES[3 * (part - 1) : 3 * part]
    lines = [*_zero_regs(xlen), ""]
    lines.extend(lxwr_defines(xlen, cases, "PMP_TOR  "))
    if xlen.bits == 64:
        lines.append("#define REGIONSTART            TEST_FOR_EXECUTION        // RAM_BASE_ADDR + PROGRAM_SIZE")
    else:
        lines.append("#define REGIONSTART         TEST_FOR_EXECUTION")
    # The -02 files use the rv64 column for their Verification Section banner on both XLENs.
    lines.extend(["", "    RVTEST_PMP_SET_BACKGROUND x4", "", *_TOR_SETUP])
    lines.append(_VERIF_BANNER[64] if part == 2 else _VERIF_BANNER[xlen.bits])
    if part == 2:
        lines.append("")
    for offset, (lxwr, entry) in enumerate(cases):
        n = 3 * (part - 1) + offset + 1
        lines.extend(
            [
                f"// Test Case: {n} : L -> {lxwr[0]} and {_TOR_PERM_NAMES[lxwr]} Permissions given to the PMP Region {entry}",
                "",
                "    LA(x6, TEST_FOR_EXECUTION)",
                "    LI(t0, g)",
                "    add x6, x6, t0",
                "    srl x6, x6, PMP_SHIFT",
                f"    csrw pmpaddr{entry}, x6",
                "    LA(x5, TEST_FOR_EXECUTION)",
                "    srl x5, x5, PMP_SHIFT",
                f"    csrw pmpaddr{entry - 1}, x5",
                "",
                f"    LI(x4, PMPREGION_LXWR_{lxwr})",
                f"    csrw {cfg_csr(xlen, entry)}, x4",
                "",
                "    RVTEST_SFENCE_VMA_IF_SUPPORTED",
                f"    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_{n}",
                "",
            ]
        )
    return lines[:-1]


def _tor_file(xlen: Xlen, part: int) -> PmpFile:
    stem = "lwxr" if xlen.bits == 32 else "lxwr"
    qualcomm = (part == 2) if xlen.bits == 32 else (part == 1)
    prefix = "pmpm_aligned" if xlen.bits == 32 else "cp_cfg_A_tor"
    return PmpFile(
        filename=f"pmpsm_tor_legal_{stem}-{part:02d}.S",
        xlen=xlen,
        copyright=_copyright(qualcomm=qualcomm),
        banner=_banner(
            _heading(
                "Comprehensive PMP (Physical Memory Protection) Verification",
                _STANDARD_DESCRIPTION,
                wide=xlen.bits == 64,
            ),
            _LEGAL_COVERPOINTS["tor"],
            _TOR_TEST_CASES + ("//\n" if xlen.bits == 64 else ""),
        ),
        required_extensions=("Sm",),
        params=_params("tor"),
        priv_test=False,
        sigupd=sigupd_count(3 * len(_TOR_SIG_STRS)),
        macro_blocks=(_G_PLAIN, template(f"pmpsm_misc_rwx_tor_{xlen.bits}")),
        body=tuple(_tor_body(xlen, part)),
        sig_strs=tuple(
            (f"test_{n}", test_case_str(n, f"{prefix}_{cp}", 9)) for n, cp in enumerate(_TOR_SIG_STRS, start=1)
        ),
        data_align=4,
        data=tuple(
            _exec_region(
                pad_rept="((1<<(UDB_PMP_GRANULARITY))>>2)",
                mid_align=True,
                body_rept="((1<<(UDB_PMP_GRANULARITY))>>2)",
                body_insn="jr ra",
            )
        ),
    )


#####################################################################
# pmpsm_priority / pmpsm_priority_off: overlapping regions
#####################################################################

_PRIORITY_PRE_MAIN = """\
#if UDB_PMP_GRANULARITY > 3
  #define NAPOT_REGION_SIZE     (1 << (UDB_PMP_GRANULARITY))
  #define NAPOT_PRIORITY_ALIGN  (UDB_PMP_GRANULARITY + 6)
#else
  #define NAPOT_REGION_SIZE     (1 << (UDB_PMP_GRANULARITY + 1))
  #define NAPOT_PRIORITY_ALIGN  (UDB_PMP_GRANULARITY + 7)
#endif
"""

_PRIORITY_OFF_PRE_MAIN = """\
#if UDB_PMP_GRANULARITY > 3
  #define NAPOT_REGION_SIZE         (1 << (UDB_PMP_GRANULARITY))
  #define NAPOT_ADDR_TRAILING_ONES  ((1 << (UDB_PMP_GRANULARITY - 3)) - 1)
#else
  #define NAPOT_REGION_SIZE         (1 << (UDB_PMP_GRANULARITY + 1))
  #define NAPOT_ADDR_TRAILING_ONES  0
#endif
"""

_PRIORITY_TEST_CASES = {
    32: """\
// Test Cases  :  Testing that first matching region has priority to determining
//                XWR. Set up 7 overlapping NAPOT regions all based at REGIONSTART
//                with sizes NAPOT_REGION_SIZE, 2x, 4x, 8x, 16x, 32x, 64x. Region 0
//                is smallest and highest priority. Cycle through the 6 legal XWR
//                values across regions 0-5; region 6 has no permissions. Make
//                {lw, sw, jalr} to the last word of each region. Access fault if
//                the matching region prohibits access.
//
""",
    64: """\
// Test Cases  :  Testing that first matching region has priority to determine
//                XWR. Set up 7 overlapping NAPOT regions all based at REGIONSTART
//                with sizes NAPOT_REGION_SIZE, 2x, 4x, 8x, 16x, 32x, 64x. Region 0
//                is smallest and highest priority. Cycle through the 6 legal XWR
//                values across regions 0-5; region 6 has no permissions. Make
//                {lw, sw, jalr} to the last word of each region. Access fault if
//                the matching region prohibits access.

""",
}

_PRIORITY_OFF_TEST_CASES = """\
// Test Cases  :  Testing that an OFF region does not match, and the first matching
//                region takes priority.
//                pmp0cfg0.L=1, pmpcfg0.A=OFF, pmpcfg0.XWR=000, pmpaddr0 = REGIONSTART
//                pmp1cfg0.L=1, pmpcfg1.A=NAPOT, pmpcfg1.XWR=101, pmpaddr1 = NAPOT(REGIONSTART, NAPOT_REGION_SIZE)
//                pmp2cfg0.L=1, pmpcfg2.A=OFF, pmpcfg2.XWR=000, pmpaddr2 = REGIONSTART
//                pmp3cfg0.L=1, pmpcfg3.A=NAPOT, pmpcfg3.XWR=111, pmpaddr3 = NAPOT(REGIONSTART, NAPOT_REGION_SIZE)
//                {lw, sw, jalr} to some address at REGIONSTART. It should succeed on
//                X and R but not W because it hits region 1.

"""

#: Entry -> LXWR code, walking the six legal encodings and then repeating L-only.
_PRIORITY_ENTRIES = [("1000", 0), ("1101", 1), ("1011", 2), ("1100", 3), ("1001", 4), ("1111", 5), ("1000_6", 6)]

#: Permission name shown in each `// Test Case:` banner.
_PRIORITY_PERMS = ["No", "XR", "WR", "X", "R", "XWR", "No"]

_PRIORITY_REGION_COMMENT = "// 64*NAPOT_REGION_SIZE bytes: covers the largest overlapping region"

_PRIORITY_REGION_SETUP = [
    "    // Set 7 overlapping NAPOT regions all based at TEST_FOR_EXECUTION, with",
    "    // sizes NAPOT_REGION_SIZE, 2x, 4x, 8x, 16x, 32x, 64x.",
    "    // pmpaddr[i] = (REGIONSTART >> 2) | ((1<<i) * NAPOT_REGION_SIZE/8 - 1)",
    "    LA(x5, TEST_FOR_EXECUTION)",
    "    srl x5, x5, PMP_SHIFT",
    "    .set i, 0",
    "    .set pmpaddri, CSR_PMPADDR0",
    "    .rept 7",
    "    LI(x6, (1 << i) * (NAPOT_REGION_SIZE / 8) - 1)",
    "    or x6, x5, x6",
    "    csrw pmpaddri, x6",
    "    .set i, i+1",
    "    .set pmpaddri, pmpaddri+1",
    "    .endr",
]


def _priority_defines(xlen: Xlen) -> list[str]:
    """One `PMPREGION_LXWR_*` per overlapping region, in ascending entry order."""
    width = 22 if xlen.bits == 32 else 20
    lines = []
    for lxwr, entry in _PRIORITY_ENTRIES:
        code = lxwr.split("_")[0]
        expr = lxwr_defines(xlen, [(code, entry)], "PMP_NAPOT")[0].split(" ", 2)[2]
        if lxwr == "1000_6" and xlen.bits == 64:
            expr = expr.replace("PMP_L|                  PMP_NAPOT", "PMP_L|                PMP_NAPOT")
        name = f"#define PMPREGION_LXWR_{lxwr} "
        lines.append(f"{name:<{width + 8}}{expr}")
    return lines


def _priority_body(xlen: Xlen) -> list[str]:
    lines = [*_zero_regs(xlen), ""]
    lines.extend(_priority_defines(xlen))
    lines.extend(["", "    RVTEST_PMP_SET_BACKGROUND x4", "", *_PRIORITY_REGION_SETUP, ""])
    if xlen.bits == 64:
        names = "|".join(f"PMPREGION_LXWR_{lxwr}" for lxwr, _ in reversed(_PRIORITY_ENTRIES))
        lines.extend(
            ["    // Set NAPOT cfg for all 7 regions in pmpcfg0", f"    LI(x4, ({names}))", "    csrw pmpcfg0, x4"]
        )
    else:
        low = "|".join(f"PMPREGION_LXWR_{lxwr}" for lxwr, entry in reversed(_PRIORITY_ENTRIES) if entry < 4)
        high = "|".join(f"PMPREGION_LXWR_{lxwr}" for lxwr, entry in reversed(_PRIORITY_ENTRIES) if entry >= 4)
        lines.extend(
            [
                "    // Set NAPOT cfg for all 7 regions, cycling through the 6 legal XWR values.",
                f"    LI(x4, ({low}))",
                "    csrw pmpcfg0, x4",
                f"    LI(x5, ({high}))",
                "    csrw pmpcfg1, x5",
            ]
        )
    lines.extend(["    RVTEST_SFENCE_VMA_IF_SUPPORTED", "", _VERIF_BANNER[xlen.bits]])
    for n, perms in enumerate(_PRIORITY_PERMS, start=1):
        size = 1 << (n - 1)
        lines.extend(
            [
                f"// Test Case: {n} : Accessing at end of region {n - 1} (size {size}x) with {perms} Permissions",
                "",
                f"    VERIFICATION_RWX   (TEST_FOR_EXECUTION + {size}*NAPOT_REGION_SIZE - 4), test_{n}",
                "",
            ]
        )
    return lines[:-1]


def _priority_file(xlen: Xlen) -> PmpFile:
    return PmpFile(
        filename="pmpsm_priority.S",
        xlen=xlen,
        copyright=_copyright(),
        banner=_banner(
            _heading(
                "Comprehensive PMP (Physical Memory Protection) Verification",
                _STANDARD_DESCRIPTION,
                wide=xlen.bits == 64,
            ),
            "// Coverpoints :  cp_priority for PMPM is fully covered in this file.\n//\n",
            _PRIORITY_TEST_CASES[xlen.bits],
        ),
        required_extensions=("Sm",),
        params=_params(),
        priv_test=False,
        sigupd=sigupd_count(21),
        macro_blocks=(_PRIORITY_PRE_MAIN, template(f"pmpsm_misc_rwx_priority_{xlen.bits}")),
        body=tuple(_priority_body(xlen)),
        sig_strs=(
            ("test_1", test_case_str(1, "pmpm_priority_sw")),
            ("test_2", test_case_str(2, "pmpm_priority_lw")),
            ("test_3", test_case_str(3, "pmpm_priority_jalr")),
        ),
        data_align=4,
        data=(
            ".p2align 12",
            "TEST_FOR_EXECUTION_0:",
            f"    jr ra{'':<56}// return pad before the aligned NAPOT priority region",
            "",
            ".p2align NAPOT_PRIORITY_ALIGN",
            "TEST_FOR_EXECUTION:",
            f"{'    .rept (16*NAPOT_REGION_SIZE)':<64}{_PRIORITY_REGION_COMMENT}",
            "    nop",
            "    .endr",
            "",
            *_RETURN_TRAMPOLINE,
        ),
    )


_PRIORITY_OFF_DEFINES = [
    "#define PMPREGION0_LXWR_1000 ((((PMP_L                            )&0xFF) << PMP0_CFG_SHIFT))",
    "#define PMPREGION1_LXWR_1101 ((((PMP_L|PMP_R|      PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT))",
    "#define PMPREGION2_LXWR_1000 ((((PMP_L                            )&0xFF) << PMP2_CFG_SHIFT))",
    "#define PMPREGION3_LXWR_1111 ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT))",
]


def _priority_off_body(xlen: Xlen) -> list[str]:
    return [
        *_zero_regs(xlen),
        "",
        *_PRIORITY_OFF_DEFINES,
        "",
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        "    // pmpaddr0 and pmpaddr2: OFF regions",
        "    // pmpaddr1 and pmpaddr3: NAPOT regions of size NAPOT_REGION_SIZE covering REGIONSTART.",
        "    LA(x5, TEST_FOR_EXECUTION)",
        "    srl x5, x5, PMP_SHIFT",
        "    csrw pmpaddr0, x5",
        "    csrw pmpaddr2, x5",
        "",
        "    LI(x6, NAPOT_ADDR_TRAILING_ONES)",
        "    or x5, x5, x6",
        "    csrw pmpaddr1, x5",
        "    csrw pmpaddr3, x5",
        "",
        _VERIF_BANNER[xlen.bits],
        "// Test Case: 1 : OFF region does not match, and the first matching region takes priority.",
        "",
        "    // Setting pmpcfg0.L = 1, pmpcfg0.A = {NAPOT,OFF,NAPOT,OFF}, pmpcfg0.XWR = {111,000,101,000}",
        "    LI(x4, PMPREGION3_LXWR_1111|PMPREGION2_LXWR_1000|PMPREGION1_LXWR_1101|PMPREGION0_LXWR_1000)",
        "    csrw pmpcfg0, x4",
        "",
        "    RVTEST_SFENCE_VMA_IF_SUPPORTED",
        "    VERIFICATION_RWX   TEST_FOR_EXECUTION, test_1",
    ]


def _priority_off_file(xlen: Xlen) -> PmpFile:
    strs = [
        ("test_1", test_case_str(1, "pmpm_priority_off_sw")),
        ("test_2", test_case_str(2, "pmpm_priority_off_lw")),
    ]
    if xlen.bits == 32:
        # The jalr string repeats index 2.
        strs.append(("test_3", test_case_str(2, "pmpm_priority_off_jalr")))
    return PmpFile(
        filename="pmpsm_priority_off.S",
        xlen=xlen,
        copyright=_copyright(),
        banner=_banner(
            _heading(
                "Comprehensive PMP (Physical Memory Protection) Verification",
                _STANDARD_DESCRIPTION,
                wide=xlen.bits == 64,
            ),
            "// Coverpoints :  cp_priority_off for PMPM is fully covered in this file.\n//\n",
            _PRIORITY_OFF_TEST_CASES,
        ),
        required_extensions=("Sm",),
        params=_params(),
        priv_test=False,
        sigupd=sigupd_count(len(strs)),
        macro_blocks=(_PRIORITY_OFF_PRE_MAIN, template(f"pmpsm_misc_rwx_priority_off_{xlen.bits}")),
        body=tuple(_priority_off_body(xlen)),
        sig_strs=tuple(strs),
        data_align=4,
        data=tuple(
            _exec_region(
                pad_rept="PMP_NAPOT_REGION_PAD_WORDS",
                pad_comment="// NAPOT-safe return fillers: puts TEST_FOR_EXECUTION at PMP_NAPOT_REGION_START",
                top_align=False,
            )
        ),
    )


#####################################################################
# pmpsm_all_entries_check: every PMP entry enforces load/store access
#####################################################################

_ALL_ENTRIES_CFG = "((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF)"

_ALL_ENTRIES_TEST_CASES = {
    32: """\
// Test Cases  : Checking all (64-PMP_writable_regs) PMP registers affect load/store
//               access. Just basic checks since bottom PMP_writable_regs have been
//               tested thoroughly. 64 Regions Only, With pmpcfg.L=1, pmpcfg.XWR=101,
//               attempt to lw and sw to each standard region. Read should succeed and
//               write should fail, proving all PMP entries are usable.
//
""",
    64: """\
// Test Cases  : Checking all (NUM_PMPS - PMP_writable_regs) PMP registers affect
//               load/store access. Just basic checks since bottom PMP_writable_regs
//               have been tested thoroughly. With pmpcfg.L=1, pmpcfg.XWR=101,
//               attempt to lw and sw to each standard region. Read should succeed
//               and write should fail, proving all PMP entries are usable.
//               Supports UDB_NUM_PMP_ENTRIES = 16 or 64.
""",
}

_ALL_ENTRIES_BACKGROUND = [
    "    // Background (catch-all) region: use the highest-numbered usable PMP entry",
    "    // so that all lower entries take priority over it.",
    "    RVTEST_PMP_SET_BACKGROUND x4",
]

_ALL_ENTRIES_CFG_COMMENT = """\
// ---------------------------------------------------------------------------
// Region configuration bit patterns.
//
// In RV64 each pmpcfgN CSR holds 8 PMP entries (one byte each).
// The PMPn_CFG_SHIFT macros select the correct byte within the CSR.
//
// Background / catch-all region (last pmpaddr entry, always RWX+L):
//   16-PMP : pmpaddr15  controlled by pmpcfg2 byte 7 (PMP7_CFG_SHIFT)
//   64-PMP : pmpaddr63  controlled by pmpcfg14 byte 7 (PMP7_CFG_SHIFT)
//
// Test regions all use L=1, R=1, X=1, W=0 (NAPOT) — read+execute, no write.
// ---------------------------------------------------------------------------
"""

_ALL_ENTRIES_ADDR_HELPERS = [
    "// ---------------------------------------------------------------------------",
    "// Address helpers",
    "// ---------------------------------------------------------------------------",
    "#define REGIONSTART     TEST_FOR_EXECUTION      // RAM_BASE_ADDR + PROGRAM_SIZE",
    "",
    "#if UDB_PMP_GRANULARITY != 2",
    "    #define PMP_MASK        ~((1 << (UDB_PMP_GRANULARITY - 3))-1)",
    "    #define PMP_REGION_SIZE (1 << (UDB_PMP_GRANULARITY - 3)) - 1",
    "#else",
    "    #define PMP_MASK        ~0",
    "    #define PMP_REGION_SIZE 0",
    "#endif",
    "",
    "// ---------------------------------------------------------------------------",
    "// SET_PMP_ENTRY  ADDR_REG, CFG_REG, CFG_BITS",
    "//   Encodes REGIONSTART in NAPOT format, writes pmpaddr, then writes pmpcfg.",
    "// ---------------------------------------------------------------------------",
]


def _all_entries_define(xlen: Xlen, entry: int) -> str:
    name = f"PMP_REGION_{entry}"
    pad = f"{name:<16}" if xlen.bits == 64 else f"{name}       "
    return f"#define {pad}{_ALL_ENTRIES_CFG} << {cfg_shift(xlen, entry)}"


def _all_entries_64_pre_main() -> list[str]:
    lines = [*_ALL_ENTRIES_CFG_COMMENT.strip("\n").splitlines(), "", ""]
    lines.append("// Slots 0-15. Slot 15 is tested only on 64-PMP systems; on 16-PMP")
    lines.append("// systems, slot 15 is reserved as the background region.")
    lines.extend(_all_entries_define(XLENS[64], e) for e in range(15, -1, -1))
    lines.extend(["", "// Slots 16-62 (64-PMP only)", "#if UDB_NUM_PMP_ENTRIES == 64"])
    lines.extend(_all_entries_define(XLENS[64], e) for e in range(62, 15, -1))
    lines.extend(["#endif  // UDB_NUM_PMP_ENTRIES == 64", ""])
    lines.extend(_ALL_ENTRIES_ADDR_HELPERS)
    lines.extend(template("pmpsm_misc_set_pmp_entry_64").strip("\n").splitlines())
    lines.extend(
        [
            "",
            "",
            "// ===========================================================================",
            "// main",
            "// ===========================================================================",
        ]
    )
    return lines


def _all_entries_64_body() -> list[str]:
    xlen = XLENS[64]
    lines = [*_zero_regs(xlen, tight=True), "", *_ALL_ENTRIES_BACKGROUND, ""]
    lines.extend(
        [
            "// ===========================================================================",
            "// TEST CASES — 64-PMP ONLY (slots 16-62, then 15-0; test cases 1-63)",
            "// Slot 63 is the background region.",
            "// ===========================================================================",
            "#if UDB_NUM_PMP_ENTRIES == 64",
            "",
        ]
    )
    for n, slot in enumerate(range(62, -1, -1), start=1):
        lines.extend(
            [
                f"// Test Case: {n} — slot {slot}, {cfg_csr(xlen, slot)}",
                f"    SET_PMP_ENTRY pmpaddr{slot}, {cfg_csr(xlen, slot)}, PMP_REGION_{slot}",
                "    RVTEST_SFENCE_VMA_IF_SUPPORTED",
                f"    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_{n}",
                "",
            ]
        )
    lines.extend(
        [
            "#endif  // UDB_NUM_PMP_ENTRIES == 64",
            "",
            "// ===========================================================================",
            "// TEST CASES — 16-PMP ONLY (slots 14-0, test cases 1-15)",
            "// slot 15 is the background region; we test slots 14 down to 0.",
            "// pmpcfg2 covers pmpaddr8-15  (RV64: one 64-bit CSR = 8 entries)",
            "// pmpcfg0 covers pmpaddr0-7",
            "// ===========================================================================",
            "#if UDB_NUM_PMP_ENTRIES == 16",
            "",
        ]
    )
    for n, slot in enumerate(range(14, -1, -1), start=1):
        lines.extend(
            [
                f"// Test Case: {n} — slot {slot}, {cfg_csr(xlen, slot)}",
                f"    SET_PMP_ENTRY pmpaddr{slot}, {cfg_csr(xlen, slot)}, PMP_REGION_{slot}",
                "    RVTEST_SFENCE_VMA_IF_SUPPORTED",
                f"    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_{n}",
                "",
            ]
        )
    lines.extend(["#endif  // UDB_NUM_PMP_ENTRIES == 16", "", "", "exit:"])
    return lines


def _all_entries_32_body() -> list[str]:
    xlen = XLENS[32]
    lines = [*_zero_regs(xlen), ""]
    lines.extend(_all_entries_define(xlen, e) for e in range(62, -1, -1))
    lines.extend(
        [
            "",
            "#define REGIONSTART         TEST_FOR_EXECUTION      // RAM_BASE_ADDR + PROGRAM_SIZE",
            "#if UDB_PMP_GRANULARITY != 2",
            "    #define PMP_MASK            ~((1 << (UDB_PMP_GRANULARITY - 3))-1)",
            "    #define PMP_REGION_SIZE     (1 << (UDB_PMP_GRANULARITY - 3)) - 1",
            "#else",
            "    #define PMP_MASK            ~0",
            "    #define PMP_REGION_SIZE     0",
            "#endif",
            "",
            *_ALL_ENTRIES_BACKGROUND,
            "",
            "#if UDB_NUM_PMP_ENTRIES == 64",
            _VERIF_BANNER[32],
        ]
    )
    for n, slot in enumerate(range(62, -1, -1), start=1):
        # Only the first three cases spell out the permissions.
        perms = " L -> 1 and XR Permissions given to the" if n <= 3 else ""
        lines.extend(
            [
                f"// Test Case: {n} :{perms} PMP Region {slot}",
                *_napot_addr(slot),
                f"    LI(x4, PMP_REGION_{slot})",
                f"    csrw {cfg_csr(xlen, slot)}, x4",
                "    RVTEST_SFENCE_VMA_IF_SUPPORTED",
                f"    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_{n}",
                "",
            ]
        )
        if slot == 15:
            lines.extend(["#endif", ""])
    return lines[:-1]


def _all_entries_file(xlen: Xlen) -> PmpFile:
    coverpoints = (
        "// Coverpoints : cp_pmp64 for PMPSM is completely covered in this test file.\n//\n"
        if xlen.bits == 32
        else "// Coverpoints : cp_pmp64 for PMPM is partially covered in this test file.\n//\n"
    )
    # rv32 reports sw first, rv64 reports lw first.
    order = ("sw", "lw") if xlen.bits == 32 else ("lw", "sw")
    return PmpFile(
        filename="pmpsm_all_entries_check.S",
        xlen=xlen,
        copyright=_copyright(),
        banner=_banner(
            _heading("Comprehensive PMP (Physical Memory Protection) Verification", _STANDARD_DESCRIPTION, wide=False),
            coverpoints,
            _ALL_ENTRIES_TEST_CASES[xlen.bits],
        ),
        required_extensions=("Sm",),
        params=_params(),
        priv_test=False,
        sigupd=sigupd_count(126),
        macro_blocks=(
            (template("pmpsm_misc_rwx_all_entries_32"),)
            if xlen.bits == 32
            else (_G_IF_BLOCK, template("pmpsm_misc_rwx_all_entries_64"))
        ),
        pre_main=() if xlen.bits == 32 else tuple(_all_entries_64_pre_main()),
        body=tuple(_all_entries_32_body() if xlen.bits == 32 else _all_entries_64_body()),
        sig_strs=tuple((f"test_{n}", test_case_str(n, f"cp_pmpm64_{name}")) for n, name in enumerate(order, start=1)),
        data_align=4,
        data=tuple(
            _exec_region(
                pad_rept="PMP_NAPOT_REGION_PAD_WORDS",
                pad_comment=_ALL_ENTRIES_PAD_COMMENT,
                comment_col=39,
                mid_align=True,
            )
        ),
    )


#####################################################################


def build_misc_files() -> list[PmpFile]:
    """Every PMPSm file outside the cfg_* and pmpcfg_walk families, for both XLENs."""
    rv32, rv64 = XLENS[32], XLENS[64]
    specs: list[PmpFile] = []
    for xlen in (rv32, rv64):
        specs.append(_all_entries_file(xlen))
        specs.append(_grain_file(xlen))
        specs.append(_grain_check_file(xlen))
        specs.append(_na4_file(xlen))
        specs.append(_priority_file(xlen))
        specs.append(_priority_off_file(xlen))
        specs.extend(_tor_file(xlen, part) for part in (1, 2))
    specs.append(_napot_file(rv32))
    specs.extend(_napot_file(rv64, part=part) for part in (1, 2))
    specs.append(_pmpaddr_upper_file())
    return specs
