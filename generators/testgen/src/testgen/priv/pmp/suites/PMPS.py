##################################
# priv/pmp/suites/PMPS.py
#
# PMPS: PMP enforcement of supervisor-mode accesses.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMPS suite: PMP configured in M mode, then checked from S mode."""

from __future__ import annotations

from testgen.priv.pmp import add_pmp_suite
from testgen.priv.pmp.macros import cfg_csr, cfg_shift, set_pmpaddr_napot, sigupd_count, template, zero_pmp_regs
from testgen.priv.pmp.model import XLENS, PmpFile, Xlen

_HEADING = """\
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
"""

#: PMP permission bits in LXWR mnemonic order, and in written-expression order.
_LXWR_BITS = ("PMP_L", "PMP_X", "PMP_W", "PMP_R")
_LXWR_ORDER = ("PMP_L", "PMP_R", "PMP_W", "PMP_X")

#: Permission names used in the `// Test Case:` banners, by XWR bits.
_PERMS = {
    "000": "No Permissions",
    "001": "R Permissions",
    "011": "WR Permissions",
    "100": "X Permissions",
    "101": "XR Permissions",
    "111": "XWR Permissions",
}

#: The six legal XWR encodings, most permissive parked in the lowest PMP entry.
_LEGAL_XWR = ("000", "001", "011", "100", "101", "111")
_LEGAL_ENTRIES = (5, 4, 3, 2, 1, 0)

_REGION = "TEST_FOR_EXECUTION"
_VERIFICATION_SECTION = "//                                            Verification Section"

_EXIT = [
    "",
    "    j exit                                                        // Verification Complete, exit the test",
    "",
    "exit:",
]

_RETURN_INSTRUCTION = [
    "RETURN_INSTRUCTION:",
    "    nop",
    "    nop",
    (
        "    jr ra                                                        "
        "// Get back to the point from where TEST_FOR_EXECUTION was called."
    ),
]

#: The NAPOT mask helpers, spelled with and without spaces around the `- 3`.
_MASK_DEFINES_SPACED = [
    "#if UDB_PMP_GRANULARITY != 2",
    "    #define PMP_MASK            ~((1 << (UDB_PMP_GRANULARITY - 3))-1)",
    "    #define PMP_REGION_SIZE     (1 << (UDB_PMP_GRANULARITY - 3)) - 1",
    "#else",
    "    #define PMP_MASK            ~0",
    "    #define PMP_REGION_SIZE     0",
    "#endif",
]
_MASK_DEFINES_TIGHT = [
    line.replace("UDB_PMP_GRANULARITY - 3", "UDB_PMP_GRANULARITY-3") for line in _MASK_DEFINES_SPACED
]

#: `g`, the PMP region size, defined either by the two-branch NAPOT form or in one line.
_G_DEFINES = [
    "#if UDB_PMP_GRANULARITY != 2",
    "  #define g   (1 << (UDB_PMP_GRANULARITY))",
    "#else",
    "  #define g   (1 << (UDB_PMP_GRANULARITY + 1))",
    "#endif",
]
_G_DEFINE_TOR = "#define g    (1<<(UDB_PMP_GRANULARITY))"


def _banner(tail: str) -> str:
    """One file's comment banner: the shared heading plus its Coverpoints/Test Cases text."""
    return f"\n{_HEADING}{tail}"


def _mask_defines(xlen: Xlen, tight: bool) -> list[str]:
    return _MASK_DEFINES_TIGHT if tight and xlen.bits == 64 else _MASK_DEFINES_SPACED


def _zero_regs(xlen: Xlen, *, say_all: bool = True) -> list[str]:
    lines = zero_pmp_regs(xlen)
    if not say_all:
        lines = [line.replace("SET ALL ", "SET ") for line in lines]
    return lines


def _perm_expr(code: str, amode: str, *, with_l: bool = True) -> str:
    """Column-aligned `PMP_L|PMP_R|PMP_W|PMP_X|<amode>` expression for an LXWR code."""
    present = {bit for bit, ch in zip(_LXWR_BITS, code, strict=True) if ch == "1"}
    if not with_l:
        present.discard("PMP_L")
    return "".join(f"{bit}|" if bit in present else " " * (len(bit) + 1) for bit in _LXWR_ORDER) + amode


def _lxwr_define(xlen: Xlen, code: str, entry: int, amode: str, *, with_l: bool = True, outer: bool = True) -> str:
    """One `#define PMPREGION_LXWR_<code>` line."""
    expr = f"(({_perm_expr(code, amode, with_l=with_l)})&0xFF) << {cfg_shift(xlen, entry)}"
    return f"#define PMPREGION_LXWR_{code} (({expr}))" if outer else f"#define PMPREGION_LXWR_{code} ({expr})"


def _case_banner(index: int, lbit: str, xwr: str, entry: int, perms: dict[str, str] = _PERMS) -> list[str]:
    return ["", f"// Test Case: {index} : L -> {lbit} and {perms[xwr]} given to the PMP Region {entry}", ""]


def _goto_smode(macro: str, label: str, *, back_to_mmode: bool = True) -> list[str]:
    """Drop to S mode, run one verification macro, and (usually) return to M mode."""
    lines = [
        "    RVTEST_SFENCE_VMA_IF_SUPPORTED",
        "    RVTEST_GOTO_LOWER_MODE    Smode        // SWITCH TO S-mode",
        f"    {macro}    {_REGION}, {label}",
    ]
    if back_to_mmode:
        lines.append("    RVTEST_GOTO_MMODE")
    return lines


def _sig_strs(
    names: list[str], prefix: str, *, width: int = 0, indices: list[int] | None = None
) -> list[tuple[str, str]]:
    """`(label, message)` pairs, one per reporting string."""
    numbers = indices or list(range(1, len(names) + 1))
    return [
        (f"test_{n}", f"{f'test: {shown};':<{width}} cp: {prefix}{name}")
        for n, (shown, name) in enumerate(zip(numbers, names, strict=True), start=1)
    ]


def _exec_region(
    pad: tuple[str, str],
    region: tuple[str, str],
    *,
    grain_align: bool = True,
    pad_label: bool = True,
) -> list[str]:
    """The data-section blob: a pad `.rept` then the TEST_FOR_EXECUTION `.rept`."""
    lines = [".p2align 12"]
    for count_and_insn, label in ((pad, "TEST_FOR_EXECUTION_0:" if pad_label else None), (region, f"{_REGION}:")):
        if grain_align:
            lines.append(".p2align (UDB_PMP_GRANULARITY)")
        if label is not None:
            lines.append(label)
        count, insn = count_and_insn
        lines.extend([f"    .rept {count}", f"    {insn}", "    .endr", ""])
    lines.extend(_RETURN_INSTRUCTION)
    return lines


#####################################################################
# pmps_cfg_A_off: A=OFF never matches, so an all-ones pmpaddr0 with
# XWR=000 must not block anything.
#####################################################################

_A_OFF_TAIL = """\
//
// Coverpoints : cp_cfg_A_off for PMPS is fully covered in this test file.
//
// Test Cases  : Checking that A=OFF never matches a region. Configuring
//                 PMP in M and switching to S mode. For pmpaddr with all 1s
//                 pmpcfg.L=0, pmpcfg.A=OFF, pmpcfg.XWR=000. Fetching, reading
//                 and writing from that region. Should succeed because region
//                 is off even though inaccessible.
"""

#: `.rept` count of the pad that pushes the region onto the next granule boundary.
_GRANULE_PAD = (
    "(1 << (UDB_PMP_GRANULARITY - 2))              // one PMP granule of return-instruction fillers: "
    "places the region on the next granule boundary (= PMP_REGION_START at coverage grain 2), "
    "grain-aligned at larger grains"
)


def _cfg_a_off_file(xlen: Xlen) -> PmpFile:
    body = [
        *_zero_regs(xlen),
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        "    LA(x4, -1)",
        "    // Putting all 1s in pmpaddr0",
        "    csrw pmpaddr0, x4",
        "",
        _VERIFICATION_SECTION,
        "// Test Case: 1 -- No Permissions given to the PMP Region 0",
        "",
        "    csrw pmpcfg0, x0        // pmp0cfg0.L = 0, pmp0cfg0.A = OFF and pmp0cfg0.WXR = 000",
        "",
        *_goto_smode("PMP_VERIFICATION_RWX", "test_1"),
        *_EXIT,
    ]
    # The rv64 strings are named pmpm_ where the rv32 ones are named pmps_.
    prefix = "pmps_cfg_A_off_all_" if xlen.bits == 32 else "pmpm_cfg_A_off_all_"
    return PmpFile(
        filename="pmps_cfg_A_off.S",
        xlen=xlen,
        banner=_banner(_A_OFF_TAIL),
        required_extensions=("S",),
        params=("NUM_PMP_ENTRIES: '>0'",),
        sigupd=sigupd_count(3),
        body=tuple(body),
        sig_strs=tuple(_sig_strs(["jalr", "sw", "lw"], prefix)),
        data_align=4 if xlen.bits == 64 else None,
        # Only the rv64 file grain-aligns the two blobs.
        data=tuple(
            _exec_region(
                (_GRANULE_PAD, "jr ra"),
                ("(1<<(UDB_PMP_GRANULARITY))", "nop"),
                grain_align=xlen.bits == 64,
            )
        ),
    )


#####################################################################
# pmps_cfg_XWR{,_unlocked}: every legal XWR against one NAPOT region,
# locked in the first file and unlocked in the second.
#####################################################################

_XWR_TAIL = """\
// Coverpoints : cp_cfg_X and cp_cfg_RW from PMPS are partially covered in this
//                 test file.{note}
//
// Test Cases  : Checking that X alone determines execute access and WR bits control
//               write/read access for every type of load and store. Configuring
//               PMP in M mode and then switching to S mode. For a standard region with
//               pmpcfg_i.L = {lbit}, pmpcfg_i.A=NAPOT, all legal pmpcfg_i.XWR, making
//               {{lw, sw, jalr}} at that start of region.
"""

_XWR_UNLOCKED_NOTE = """ (unlocked pmpcfg_i.L=0 XWR combinations; the locked
//                 combinations are covered by pmps_cfg_XWR.S)."""

_XWR_OPS = {
    32: ["jalr", "sb", "sh", "sw", "lb", "lbu", "lh", "lhu", "lw"],
    64: ["jalr", "sb", "sh", "sw", "sd", "lb", "lbu", "lh", "lhu", "lw", "lwu", "ld"],
}


def _cfg_xwr_file(xlen: Xlen, locked: bool) -> PmpFile:
    stem = "pmps_cfg_XWR" if locked else "pmps_cfg_XWR_unlocked"
    lbit = "1" if locked else "0"
    # Only the rv64 unlocked file drops the outer parenthesis pair from its #defines.
    outer = locked or xlen.bits == 32
    body = [
        *_zero_regs(xlen, say_all=False),
        "",
        *(
            _lxwr_define(xlen, f"{lbit}{xwr}", entry, "PMP_NAPOT", with_l=locked, outer=outer)
            for xwr, entry in zip(_LEGAL_XWR, _LEGAL_ENTRIES, strict=True)
        ),
        "",
        f"#define REGIONSTART            {_REGION}    // RAM_BASE_ADDR + PROGRAM_SIZE",
        *_mask_defines(xlen, tight=True),
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        _VERIFICATION_SECTION,
    ]
    for n, (xwr, entry) in enumerate(zip(_LEGAL_XWR, _LEGAL_ENTRIES, strict=True), start=1):
        body.extend(_case_banner(n, lbit, xwr, entry))
        body.extend(set_pmpaddr_napot(entry))
        body.extend(["", f"    LI(t1, PMPREGION_LXWR_{lbit}{xwr})", f"    csrw {cfg_csr(xlen, entry)}, t1", ""])
        body.extend(_goto_smode("VERIFICATION_RWX", f"test_{n}"))
    body.extend(_EXIT)
    return PmpFile(
        filename=f"{stem}.S",
        xlen=xlen,
        banner=_banner(_XWR_TAIL.format(note=_XWR_UNLOCKED_NOTE if not locked and xlen.bits == 64 else "", lbit=lbit)),
        required_extensions=("S",),
        params=("NUM_PMP_ENTRIES: '>0'",),
        sigupd=sigupd_count(len(_LEGAL_XWR) * len(_XWR_OPS[xlen.bits])),
        macro_blocks=(template(f"pmps_cfg_xwr_rwx{xlen.bits}"),),
        body=tuple(body),
        sig_strs=tuple(_sig_strs(_XWR_OPS[xlen.bits], f"{stem}.S_")),
        data_align=4,
        data=tuple(_exec_region((_GRANULE_PAD, "jr ra"), ("(1<<(UDB_PMP_GRANULARITY))", "nop"))),
    )


#####################################################################
# pmps_csr_access: every pmpaddr and pmpcfg CSR written from S mode.
#####################################################################

_CSR_ACCESS_TAIL = """\
{lead}// Coverpoints : cp_pmpaddr_access_{mode} and cp_pmpcfg_access_{mode} are fully covered in
//                 this test file.
//
// Test Cases  : Test pmpcfg and pmpaddr access from S-mode. Trying to write
//               all 64 pmpaddr and 16 pmpcfg registers. Should throw illegal
//               instruction faults because PMP CSRs are only accessible to
//               M-mode.
{tail}"""


def _csr_walk(csr_var: str, first: str, count: int, label: str) -> list[str]:
    """Write all ones into every CSR of one bank from S mode, checking each trap."""
    return [
        f"    .set {csr_var}, {first}",
        f"    .rept {count}",
        "    RVTEST_GOTO_LOWER_MODE    Smode        // SWITCH TO S-mode",
        "    99:",
        f"    RVTEST_SIGUPD_CSR_WRITE({csr_var}, x4, 99b, {label})",
        "    nop",
        "    RVTEST_GOTO_MMODE",
        f"    .set {csr_var}, {csr_var}+1",
        "    .endr",
    ]


def _csr_access_file(xlen: Xlen) -> PmpFile:
    body = [
        "",
        "// Trying to access PMP CSRs in S-mode by writing all 1s.",
        "",
        "    // Value to write in PMP CSRs in S-mode",
        "    LA(x4, -1)",
        "",
        *_csr_walk("pmpaddri", "CSR_PMPADDR0", 64, "test_1_str"),
        "",
        *_csr_walk("pmpcfgi", "CSR_PMPCFG0", 16, "test_2_str"),
        "",
        "    j exit                                                        // Verification Complete, exit the test",
        "",
        ".p2align 10",
        ".p2align (UDB_PMP_GRANULARITY)",
        *_RETURN_INSTRUCTION,
        "",
        "exit:",
    ]
    # The rv64 banner names the U-mode coverpoints even though the test stays in S mode.
    return PmpFile(
        filename="pmps_csr_access.S",
        xlen=xlen,
        banner=_banner(
            _CSR_ACCESS_TAIL.format(
                lead="//\n" if xlen.bits == 32 else "",
                mode="s" if xlen.bits == 32 else "u",
                tail="" if xlen.bits == 32 else "//\n",
            )
        ),
        required_extensions=("S",),
        params=("NUM_PMP_ENTRIES: '>0'",),
        sigupd=sigupd_count(64 + 16),
        pre_main=("RVTEST_PMP_SET_BACKGROUND x4",),
        body=tuple(body),
        sig_strs=(
            ("test_1", "test: 1; cp: cp_pmpaddr_access_s"),
            ("test_2", "test: 2; cp: cp_pmpcfg_access_s"),
        ),
        data_align=4,
    )


#####################################################################
# pmps_mprv_check-0{1,2}: mstatus.MPRV/MPP make M-mode data accesses
# use S-mode PMP permissions.
#####################################################################

_MPRV_TAIL = """\
{gap}
// Coverpoints : cp_mprv for PMPS is partially covered in this file.
//
// Test Cases  : Checking L bit doesn't matter with MPRV setting to lower privilege
//                 mode. Configuring PMP in M-mode. Setting mstatus.MPRV = {{0/1}},
//                 mstatus.MPP = {{11 / 01}}. While staying in M-mode doing {{lw/sw/jalr}}
//                 with pmpcfg_i.L={{0/1}}, XWR = {xwr}. Observing access faults for
//                 restricted execution regions even with L = 0 in effective S mode.
{tail}"""

_MPRV_PAD = (
    "PMP_NAPOT_REGION_PAD_WORDS  // NAPOT-safe fillers: places the region at PMP_NAPOT_REGION_START "
    "(matches cp_mprv_*'s standard_region requirement)"
)


def _mprv_define(code: str) -> str:
    """The mprv files write their configuration byte without the outer parentheses."""
    return f"#define PMPREGION_LXWR_{code}   (({_perm_expr(code, 'PMP_NAPOT')})&0xFF) << PMP0_CFG_SHIFT"


def _mprv_program_region(code: str) -> list[str]:
    return [
        "//-------------------------------------",
        *set_pmpaddr_napot(0),
        "",
        f"    LI(x4, PMPREGION_LXWR_{code})",
        "    csrw pmpcfg0, x4",
        "    RVTEST_SFENCE_VMA_IF_SUPPORTED",
        "//-------------------------------------",
        "",
    ]


def _mprv_case(index: int, mprv: int, lbit: int, perms: str, first_label: int) -> list[str]:
    """One MPRV/MPP setting checked with an execute, a store and a load."""
    clear = "MPRV|M_MODE" if mprv == 0 else "M_MODE|MPRV"
    set_bits = "S_MODE" if mprv == 0 else "MPRV|S_MODE"
    lines = [
        (
            f"// Test Case: {index} : mstatus.MPRV = {mprv}, L = {lbit}, "
            f"mstatus.MPP = 01 and {perms} given to the PMP Region 0"
        ),
        "",
        f"    li t0, ({clear})        // Initialize mstatus.MPRV & mstatus.MPP",
        "    csrc mstatus, t0",
    ]
    for n, macro in enumerate(("VERIFICATION_X", "VERIFICATION_W", "VERIFICATION_R")):
        lines.extend(
            [
                "",
                f"    li t0, ({set_bits})",
                "    csrs mstatus, t0",
                "",
                f"    {macro}    {_REGION}, test_{first_label + n}",
            ]
        )
    lines.append("")
    return lines


def _mprv_file(xlen: Xlen, part: int) -> PmpFile:
    xwr = "000" if part == 1 else "111"
    perms = _PERMS[xwr]
    body = [
        *_zero_regs(xlen),
        "",
        _mprv_define(f"1{xwr}"),
        _mprv_define(f"0{xwr}"),
        "",
        "#define MPRV                    (1 << 17)",
        "#define S_MODE                    (1 << 11)",
        "#define M_MODE                    (3 << 11)",
        "",
        f"#define REGIONSTART            {_REGION}    // RAM_BASE_ADDR + PROGRAM_SIZE",
        *_mask_defines(xlen, tight=True),
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        *_mprv_program_region(f"0{xwr}"),
        _VERIFICATION_SECTION,
        *_mprv_case(1, 0, 0, perms, 1),
        *_mprv_case(2, 1, 0, perms, 4),
        *_mprv_program_region(f"1{xwr}"),
        *_mprv_case(3, 0, 1, perms, 7),
        *_mprv_case(4, 1, 1, perms, 10),
    ]
    body.extend(_EXIT[1:])
    # The rv32 -01 banner breaks the comment block with a bare blank line.
    gap = "" if (part == 1 and xlen.bits == 32) else "//"
    return PmpFile(
        filename=f"pmps_mprv_check-0{part}.S",
        xlen=xlen,
        banner=_banner(_MPRV_TAIL.format(gap=gap, xwr=xwr, tail="\n" if (part == 1 and xlen.bits == 32) else "")),
        required_extensions=("S",),
        params=("NUM_PMP_ENTRIES: '>0'",),
        sigupd=sigupd_count(12),
        macro_blocks=(template("pmps_mprv_macros"),),
        body=tuple(body),
        sig_strs=tuple(_sig_strs(["jalr", "sw", "lw"], "pmpm_cfg_A_off_all_")),
        data_align=4,
        data=tuple(_exec_region((_MPRV_PAD, "jr ra"), ("(1<<(UDB_PMP_GRANULARITY))", "nop"))),
    )


#####################################################################
# pmps_na4_legal_lxwr: every legal XWR against an unlocked NA4 region.
#####################################################################

_NA4_TAIL = """\
//
// Coverpoints : cp_cfg_A_na4 for PMPS is fully covered in this test file.
//
// Test Cases  : Checking XWR controls accesses in matching NA4 region. G=0 Only
//               Configuring PMP in M mode and then switching to S mode.
//               with pmpcfg_i.L = 1, pmpcfg_i.A=NA4, all legal pmpcfg_i.XWR,
//               reasonable address in pmpaddr: making {lw, sw, jalr} at that
//               address, that address - 4, just beyond top of the region.
//               Observing proper access faults for restricted regions, and
//               accesses beyond the region and below the region should succeed
//               because the bckground region is set to RWX.
"""

_NA4_OPS = [
    "jalr_address",
    "jalr_address-4",
    "jalr_address+4",
    "sw_address",
    "lw_address",
    "sw_address-4",
    "lw_address-4",
    "sw_address+4",
    "lw_address+4",
]

_GRAIN_REPT = "((1<<(UDB_PMP_GRANULARITY))>>2)"


def _na4_file(xlen: Xlen) -> PmpFile:
    macro = "PMP_VERIFICATION_RWX_NA4_RV32" if xlen.bits == 32 else "VERIFICATION_RWX"
    body = [
        *_zero_regs(xlen),
        "",
        *(
            _lxwr_define(xlen, f"0{xwr}", entry, "PMP_NA4  ", with_l=False)
            for xwr, entry in zip(_LEGAL_XWR, _LEGAL_ENTRIES, strict=True)
        ),
        "",
        f"#define REGIONSTART            {_REGION}        // RAM_BASE_ADDR + PROGRAM_SIZE",
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        _VERIFICATION_SECTION,
    ]
    for n, (xwr, entry) in enumerate(zip(_LEGAL_XWR, _LEGAL_ENTRIES, strict=True), start=1):
        body.extend(_case_banner(n, "0", xwr, entry))
        body.extend(
            [
                "    LA(x4, REGIONSTART)",
                "    srl x4, x4, PMP_SHIFT",
                f"    csrw pmpaddr{entry}, x4",
                f"    LI(x5, PMPREGION_LXWR_0{xwr})",
                f"    csrw {cfg_csr(xlen, entry)}, x5",
                "",
            ]
        )
        # The last case never returns to M mode and the file has no `j exit`.
        body.extend(_goto_smode(macro, f"test_{n}", back_to_mmode=n < len(_LEGAL_XWR)))
    body.extend(["", "exit:"])
    # The rv32 strings are named pmpm_ where the rv64 ones are named pmps_.
    prefix = "pmpm_cfg_A_off_all_" if xlen.bits == 32 else "pmps_cfg_A_off_all_"
    return PmpFile(
        filename="pmps_na4_legal_lxwr.S",
        xlen=xlen,
        banner=_banner(_NA4_TAIL),
        required_extensions=("S",),
        params=("NUM_PMP_ENTRIES: '>0'", "PMP_NA4_SUPPORTED: true"),
        sigupd=sigupd_count(len(_LEGAL_XWR) * 9),
        macro_blocks=(template("pmps_na4_rwx64"),) if xlen.bits == 64 else (),
        body=tuple(body),
        sig_strs=tuple(_sig_strs(_NA4_OPS, prefix)),
        data_align=4,
        data=tuple(_exec_region((_GRAIN_REPT, "jr ra"), (_GRAIN_REPT, "jr ra"))),
    )


#####################################################################
# pmps_napot_legal_lxwr-0{1,2}: the six-case NAPOT walk, split across
# two files that share one set of #defines.
#####################################################################

_NAPOT_TAIL = """\
//
// Coverpoints : {coverpoints}
//
// Test Cases  : Checking XWR controls accesses in matching NAPOT region. Configuring
//               PMP in M mode and then switching to S mode. For a standard region with
//               pmpcfg_i.L = {{0/1}}, pmpcfg_i.A=NAPOT, all legal pmpcfg_i.XWR, making
//               {{lw, sw, jalr}} at that start of region, start - 4, start + 4, highest
//               word in region, just beyond top of the region. Observing proper access
//               faults for restricted regions, and accesses beyond and below the region
//               should succeed because of background region with RWX permissions.
{tail}"""

_NAPOT_COVERPOINTS = {
    32: "cp_cfg_X, cp_cfg_A_napot and cp_cfg_RW from PMPS are partially covered in this\n//                 test file.",
    64: "cp_cfg_X and cp_cfg_RW from PMPS are partially covered in this\n"
    "//                 test file. cp_cfg_A_napot is fully covered.",
}

#: The value written to pmpcfg for each of the six cases: entries sharing one
#: pmpcfg CSR accumulate, so later cases re-OR the earlier codes.
_NAPOT_CFG_VALUES = [
    ["1000"],
    ["1000", "1001"],
    ["1011"],
    ["1011", "1100"],
    ["1011", "1100", "1101"],
    ["1011", "1100", "1101", "1111"],
]

_NAPOT_OPS = [
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

_NAPOT_OPS_RV64 = ["sd_address", "ld_address", "lwu_address"]

#: The rv32 file reports the wrong index for its last five strings.
_NAPOT_INDICES_RV32 = [*range(1, 17), 16, 13, 14, 15, 16]


def _napot_sig_strs(xlen: Xlen) -> list[tuple[str, str]]:
    prefix = "pmps_napot_legal_lwxr_"
    if xlen.bits == 32:
        return _sig_strs(_NAPOT_OPS, prefix, width=9, indices=_NAPOT_INDICES_RV32)
    strs = _sig_strs(_NAPOT_OPS, prefix, width=9)
    # test_24 reports the pmpu_ coverpoint name, and the last three pad to a wider tag.
    for n, name in enumerate(_NAPOT_OPS_RV64, start=22):
        family = "pmpu_napot_legal_lwxr_" if name == "lwu_address" else prefix
        strs.append((f"test_{n}", f"{f'test: {n};':<10} cp: {family}{name}"))
    return strs


def _napot_file(xlen: Xlen, part: int) -> PmpFile:
    # Only the rv64 -01 file carries its own copy of the verification macro.
    local_macro = xlen.bits == 64 and part == 1
    macro = "VERIFICATION_RWX" if local_macro else "PMP_VERIFICATION_RWX_NAPOT"
    cases = range(1, 4) if part == 1 else range(4, 7)
    body = [
        *_zero_regs(xlen, say_all=False),
        "",
        *(
            _lxwr_define(xlen, f"1{xwr}", entry, "PMP_NAPOT", with_l=False)
            for xwr, entry in zip(_LEGAL_XWR, _LEGAL_ENTRIES, strict=True)
        ),
        "",
        f"#define REGIONSTART            {_REGION}    // RAM_BASE_ADDR + PROGRAM_SIZE",
        *_mask_defines(xlen, tight=False),
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        _VERIFICATION_SECTION,
    ]
    for n in cases:
        xwr, entry = _LEGAL_XWR[n - 1], _LEGAL_ENTRIES[n - 1]
        value = "|".join(f"PMPREGION_LXWR_{code}" for code in _NAPOT_CFG_VALUES[n - 1])
        body.extend(_case_banner(n, "1", xwr, entry))
        body.extend(set_pmpaddr_napot(entry))
        body.extend(["", f"    LI(t1, {value})", f"    csrw {cfg_csr(xlen, entry)}, t1", ""])
        body.extend(_goto_smode(macro, f"test_{n}"))
    body.extend(_EXIT)
    macros = [_G_DEFINES]
    return PmpFile(
        filename=f"pmps_napot_legal_lxwr-0{part}.S",
        xlen=xlen,
        banner=_banner(
            _NAPOT_TAIL.format(coverpoints=_NAPOT_COVERPOINTS[xlen.bits], tail="//\n" if xlen.bits == 32 else "")
        ),
        required_extensions=("S",),
        params=("NUM_PMP_ENTRIES: '>0'", "PMP_NAPOT_SUPPORTED: true"),
        sigupd=sigupd_count(len(cases) * (21 if xlen.bits == 32 else 24)),
        macro_blocks=tuple(
            ["\n".join(block) for block in macros] + ([template("pmps_napot_rwx64")] if local_macro else [])
        ),
        body=tuple(body),
        sig_strs=tuple(_napot_sig_strs(xlen)),
        data_align=4,
        # The rv32 -02 file lost the label on its pad blob.
        data=tuple(
            _exec_region(("(g>>2)", "jr ra"), ("(g>>2)", "jr ra"), pad_label=not (xlen.bits == 32 and part == 2))
        ),
    )


#####################################################################
# pmps_tor_legal_lxwr-0{1,2}: the six-case TOR walk, split across two
# files, each region bounded by a pair of pmpaddr CSRs.
#####################################################################

_TOR_TAIL = """\
//
// Coverpoints : cp_cfg_A_tor for PMPS is partially covered in this test file.
//
// Test Cases  : Configuring PMP in M mode and then switching to S mode.
//               Checking XWR controls accesses in matching TOR region. With
//               pmpcfg_i.L =1, pmpcfg_i.A = TOR, all legal pmpcfg_i.XWR,
//               default TOR region, address-g in pmpaddr_i-1: making {{lw,sw,jalr}}
//               address, address-4, address-g, address-g-4.  Observing proper
//               access faults for restricted regions.
{tail}"""

#: TOR spells the XR case "RX".
_TOR_PERMS = {**_PERMS, "101": "RX Permissions"}

#: Each TOR region needs two pmpaddr CSRs, so only every other entry is configured.
_TOR_ENTRIES = (5, 3, 1)

_TOR_OFFSETS = ["address", "address-4", "address+4", "address+g-4", "address+g"]


def _tor_sig_strs(xlen: Xlen, part: int) -> list[tuple[str, str]]:
    # The rv64 -01 file lists jalr first and pads its tags to a narrower column.
    if xlen.bits == 64 and part == 1:
        order, width = ("jalr", "sw", "lw"), 0
    else:
        order, width = ("sw", "lw", "jalr"), 9
    names = [f"{op}_{offset}" for op in order for offset in _TOR_OFFSETS]
    return _sig_strs(names, "cp_cfg_A_tor_", width=width)


def _tor_file(xlen: Xlen, part: int) -> PmpFile:
    # Only the rv64 -01 file uses the framework macro; the rest carry a local copy.
    local_macro = not (xlen.bits == 64 and part == 1)
    macro = "VERIFICATION_RWX" if local_macro else "PMP_VERIFICATION_RWX_LEGAL"
    codes = _LEGAL_XWR[:3] if part == 1 else _LEGAL_XWR[3:]
    body = [
        *_zero_regs(xlen),
        "",
        *(
            _lxwr_define(xlen, f"0{xwr}", entry, "PMP_TOR  ", with_l=False)
            for xwr, entry in zip(codes, _TOR_ENTRIES, strict=True)
        ),
        "",
        f"#define REGIONSTART            {_REGION}        // RAM_BASE_ADDR + PROGRAM_SIZE",
        "",
        "",
        "    RVTEST_PMP_SET_BACKGROUND x4",
        "",
        _VERIFICATION_SECTION,
    ]
    for i, (xwr, entry) in enumerate(zip(codes, _TOR_ENTRIES, strict=True)):
        n = i + 1 + (part - 1) * 3
        body.extend(_case_banner(n, "0", xwr, entry, _TOR_PERMS))
        body.extend(
            [
                "    LA(x6, REGIONSTART)",
                "    li t0, g",
                "    add x6, x6, t0",
                "    srl x6, x6, PMP_SHIFT",
                f"    csrw pmpaddr{entry}, x6",
                "    LA(x5, REGIONSTART)",
                "    srl x5, x5, PMP_SHIFT",
                f"    csrw pmpaddr{entry - 1}, x5",
                f"    LI(x4, PMPREGION_LXWR_0{xwr})",
                f"    csrw {cfg_csr(xlen, entry)}, x4",
                "",
            ]
        )
        body.extend(_goto_smode(macro, f"test_{n}"))
    body.extend(_EXIT)
    return PmpFile(
        filename=f"pmps_tor_legal_lxwr-0{part}.S",
        xlen=xlen,
        banner=_banner(_TOR_TAIL.format(tail="//\n" if xlen.bits == 32 else "")),
        required_extensions=("S",),
        params=("NUM_PMP_ENTRIES: '>0'", "PMP_TOR_SUPPORTED: true"),
        sigupd=sigupd_count(len(codes) * 15),
        macro_blocks=(_G_DEFINE_TOR, *((template(f"pmps_tor_rwx{xlen.bits}"),) if local_macro else ())),
        body=tuple(body),
        sig_strs=tuple(_tor_sig_strs(xlen, part)),
        data_align=4,
        data=tuple(_exec_region((_GRAIN_REPT, "jr ra"), (_GRAIN_REPT, "jr ra"))),
    )


@add_pmp_suite("PMPS")
def build() -> list[PmpFile]:
    """Every PMPS file, for both XLENs."""
    specs: list[PmpFile] = []
    for xlen in XLENS.values():
        specs.append(_cfg_a_off_file(xlen))
        specs.extend(_cfg_xwr_file(xlen, locked) for locked in (True, False))
        specs.append(_csr_access_file(xlen))
        specs.extend(_mprv_file(xlen, part) for part in (1, 2))
        specs.append(_na4_file(xlen))
        specs.extend(_napot_file(xlen, part) for part in (1, 2))
        specs.extend(_tor_file(xlen, part) for part in (1, 2))
    return specs
