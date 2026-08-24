##################################
# priv/pmp/suites/PMPZca.py
#
# PMPZca: PMP enforcement of compressed instruction fetches.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMPZca suite: PMP region boundaries versus 16-bit and misaligned 32-bit fetches."""

from __future__ import annotations

from testgen.priv.pmp import add_pmp_suite
from testgen.priv.pmp.macros import (
    LOCKED_LXWR_CASES,
    lxwr_napot_body,
    sigupd_count,
    template,
    test_case_str,
    zero_pmp_regs,
)
from testgen.priv.pmp.model import XLENS, PmpFile, Xlen

_COPYRIGHT = (
    "// Copyright (C) 2025 Harvey Mudd College & Oklahoma State University, UET Lahore, Habib University",
    "// SPDX-License-Identifier: Apache-2.0",
    "//",
)

_HEADING = """
// Title        : Comprehensive PMP (Physical Memory Protection) Verification
// Authors      : Umer Shahid, Allen Baum, David Harris
//                Muhammad Abdullah, Hamza Ali, Muhammad Zain
//
// Description : This test verifies the functionality and enforcement of
//               Physical Memory Protection (PMP) configurations in RISC-V
//               systems. It specifically tests the Read, Write, and Execute
//               permissions for a designated memory region, ensuring that
//               the PMP settings are correctly applied and that the system
//               behaves as expected when accessing this region.
//
"""


def _banner(coverpoints: str, test_cases: str) -> str:
    """Assemble one file's comment banner from the parts that vary between files."""
    return f"{_HEADING}{coverpoints}//\n{test_cases}"


def _extensions(xlen: Xlen) -> tuple[str, ...]:
    """Required extensions. Only the rv32 files list 'I' explicitly."""
    return ("I", "Zca", "Sm") if xlen.bits == 32 else ("Zca", "Sm")


def _march(xlen: Xlen) -> str:
    return f"rv{xlen.bits}i_zca_zicsr_zifencei"


#: Amode name -> the `PMP_<amode>` constant and the `# params:` gate it needs.
_AMODE_PARAM = {
    "na4": "PMP_NA4_SUPPORTED: true",
    "napot": "PMP_NAPOT_SUPPORTED: true",
    "tor": "PMP_TOR_SUPPORTED: true",
}


def _params(amode: str | None) -> tuple[str, ...]:
    """The NUM_PMP_ENTRIES gate every file needs, plus the address-mode gate."""
    params = ["NUM_PMP_ENTRIES: '>0'"]
    if amode is not None:
        params.append(_AMODE_PARAM[amode])
    return tuple(params)


#: NAPOT address-mask defines plus SIZE, whose parentheses balance at its .rept.
_CRET_NAPOT_DEFINES = [
    "#if UDB_PMP_GRANULARITY != 2",
    "    #define PMP_MASK            ~((1 << (UDB_PMP_GRANULARITY - 3))-1)",
    "    #define PMP_REGION_SIZE     (1 << (UDB_PMP_GRANULARITY - 3)) - 1",
    "    #define SIZE (1<<(UDB_PMP_GRANULARITY)",
    "#else",
    "    #define PMP_MASK            ~0",
    "    #define PMP_REGION_SIZE     0",
    "    #define SIZE (1<<(UDB_PMP_GRANULARITY+1)",
    "#endif",
]

_NAPOT_ADDR_MASKING = [
    "    LI(x6, PMP_MASK)",
    "    and x5, x5, x6",
    "    LI(x6, PMP_REGION_SIZE)",
    "    or x5, x5, x6",
]


def _cfg_define(name: str, perms: str, amode_const: str, shift: str) -> str:
    """One `#define PMP<n>CFG` line in this suite's column layout."""
    return f"#define PMP{name}CFG             (((({perms}|{amode_const})   &0xFF)   << {shift}))"


_XC_CALLS = [
    line
    for n in range(4)
    for line in ("", f"    //Test case{n + 1}", f"    PMP_VERIFICATION_X_C TEST_FOR_EXECUTION_{n}, test{n + 1}")
]

_EXIT = [
    "",
    "    j exit                                                      // Verification Complete, exit the test",
    "exit:",
]


def _cret_body(xlen: Xlen, amode: str) -> list[str]:
    """One PMP region around four c.ret instructions, each executed in turn."""
    # cret_napot uses the rv32 clearing loop on both XLENs.
    loop_xlen = XLENS[32] if (amode == "napot" and xlen.bits == 64) else xlen
    lines = [*zero_pmp_regs(loop_xlen), ""]
    if amode == "tor":
        # TOR's region is [pmpaddr0, pmpaddr1), so the configured entry is entry 1.
        lines.append(_cfg_define("1", "PMP_L|PMP_R|PMP_W|PMP_X", "PMP_TOR", "PMP1_CFG_SHIFT"))
    elif amode == "napot":
        lines.append("#define PMP0CFG             ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT))")
    else:
        lines.append(
            "#define PMP0CFG                 ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NA4  ) &0xFF)   << PMP0_CFG_SHIFT))"
        )
    lines.extend(["", "#define REGIONSTART             TEST_FOR_EXECUTION_1"])
    if amode == "napot":
        lines.extend(_CRET_NAPOT_DEFINES)
    lines.extend(["", "    RVTEST_PMP_SET_BACKGROUND x4", ""])
    lines.append("//                                          Verification Section")
    lines.append(f"// Test Case: {amode.upper()} Region with L->1 and XWR->111")
    lines.extend(["", "    LA(x5, REGIONSTART)", "    srl x5, x5, PMP_SHIFT"])
    if amode == "napot":
        lines.extend(_NAPOT_ADDR_MASKING)
    lines.append("    csrw pmpaddr0, x5")
    if amode == "tor":
        lines.extend(
            [
                "",
                "    LA(x5, REGIONSTART)",
                "    LI(x4, REGION_SIZE)",
                "    add x5, x5, x4",
                "    srl x5, x5, PMP_SHIFT",
                "    csrw pmpaddr1, x5",
            ]
        )
    cfg = "PMP1CFG" if amode == "tor" else "PMP0CFG"
    lines.extend(["", f"    LA(x4, {cfg})", "    csrw pmpcfg0, x4", "    RVTEST_SFENCE_VMA_IF_SUPPORTED"])
    lines.extend(_XC_CALLS)
    # rv64 na4 has no explicit exit.
    if not (amode == "na4" and xlen.bits == 64):
        lines.extend(_EXIT)
    return lines


def _cret_data(xlen: Xlen, amode: str) -> list[str]:
    """Four c.ret instructions straddling the region, plus the shared return trampoline."""
    skip = "0x806" if amode == "napot" else "0x802"
    skip_comment = (
        "                                                  "
        "// shifted +4B so REGIONSTART lands at PMP_NAPOT_REGION_START, not PMP_REGION_START"
        if amode == "napot"
        else ""
    )
    inside = "Compressed at the start of the region" if amode == "na4" else "Compressed return inside the region"
    lines = [
        f".p2align {11 if xlen.bits == 32 else 10}",
        f".skip ({skip}){skip_comment}",
        "TEST_FOR_EXECUTION_0:",
        "    ret                                                         // Compressed return just before the start of region",
        "",
        "TEST_FOR_EXECUTION_1:",
        f"    ret                                                         // {inside}",
    ]
    if amode != "na4":
        size = "(SIZE) -4 ) /2)" if amode == "napot" else "((1<<(UDB_PMP_GRANULARITY)) -4 ) /2)"
        lines.extend(
            [
                f"    .rept ({size}                     // (size of region - size of 2 returns) / size of nop",
                "    nop",
                "    .endr",
            ]
        )
    lines.extend(
        [
            "",
            "TEST_FOR_EXECUTION_2:",
            "    ret                                                         // Compressed return at the top of the region",
            "",
            "TEST_FOR_EXECUTION_3:",
            "    ret                                                         // Compressed return just above the region",
        ]
    )
    if amode != "na4":
        lines.append("    nop")
    lines.extend(
        [
            "",
            "RETURN_INSTRUCTION:",
            "    nop",
            "    nop",
            "    jr ra                                                       // Get back to the point from where TEST_FOR_EXECUTION was called.",
        ]
    )
    return lines


_CRET_TEST_CASES = """\
// Test Cases  : Checking that 16-bit fetches adjacent to a {mode} PMP boundary succeed.
//               Set up a standard {mode} PMP region with L=1, XWR = 111. Placing four
//               c.ret = c.jr ra statements just below, at bottom, at top, and just
//               above PMP region, half of which are on 16-bit boundaries.
//               Attempt jalr to each c.ret.
//
"""


def _cret_file(xlen: Xlen, amode: str) -> PmpFile:
    return PmpFile(
        filename=f"pmpzca_cret_{amode}.S",
        xlen=xlen,
        copyright=_COPYRIGHT,
        banner=_banner(
            f"// Coverpoints : cp_cret_{amode} for PMPZca is fully covered in this test file.\n",
            _CRET_TEST_CASES.format(mode=amode.upper()),
        ),
        required_extensions=_extensions(xlen),
        params=_params(amode),
        march=_march(xlen),
        priv_test=False,
        sigupd=sigupd_count(4),
        pre_main=("#define REGION_SIZE    (1<<(UDB_PMP_GRANULARITY))",) if amode == "tor" else (),
        body=tuple(_cret_body(xlen, amode)),
        # All three address modes report the napot coverpoint name.
        sig_strs=(("test_1", "test: 1; cp: pmpzca_cret_napot_execute"),),
        data_align=4 if (amode == "na4" and xlen.bits == 64) else None,
        data=tuple(_cret_data(xlen, amode)),
    )


#####################################################################
# The aligned_* / misaligned_* families: three consecutive PMP regions
# with an uncompressed jalr placed inside them (aligned) or straddling
# their boundaries (misaligned).
#####################################################################

_JALR = "    jalr x0, x1, 0"

_RETURN_TRAMPOLINE = [
    "RETURN_INSTRUCTION:",
    "    nop",
    "    nop",
    "    jr ra                                                       // Get back to the point from where TEST_FOR_EXECUTION was called.",
]

_GRAIN = "(1<<(UDB_PMP_GRANULARITY))"

#: Per address mode: the region-size expression used in the data section, the
#: `#define`s emitted before `main:`, and the PMP_* address-mode constant.
_REGION_SIZE_EXPR = {"na4": "4", "napot": "REGION_SIZE", "off": "NAPOT_REGION_SIZE", "tor": _GRAIN}

_NAPOT_PRE_MAIN = [
    "#if UDB_PMP_GRANULARITY != 2",
    "    #define REGION_SIZE  (1<<(UDB_PMP_GRANULARITY))",
    "#else",
    "    #define REGION_SIZE 8",
    "#endif",
]

_OFF_PRE_MAIN = [
    "#if UDB_PMP_GRANULARITY > 3",
    "  #define NAPOT_REGION_SIZE         (1 << (UDB_PMP_GRANULARITY))",
    "  #define NAPOT_ADDR_MASK           ~((1 << (UDB_PMP_GRANULARITY - 3)) - 1)",
    "  #define NAPOT_ADDR_TRAILING_ONES  ((1 << (UDB_PMP_GRANULARITY - 3)) - 1)",
    "#else",
    "  #define NAPOT_REGION_SIZE         (1 << (UDB_PMP_GRANULARITY + 1))",
    "  #define NAPOT_ADDR_MASK           ~0",
    "  #define NAPOT_ADDR_TRAILING_ONES  0",
    "#endif",
]

#: misaligned_off never masks its PMP addresses, so it defines only the size.
_MISALIGNED_OFF_PRE_MAIN = [
    "#if UDB_PMP_GRANULARITY > 3",
    "  #define NAPOT_REGION_SIZE         (1 << (UDB_PMP_GRANULARITY))",
    "#else",
    "  #define NAPOT_REGION_SIZE         (1 << (UDB_PMP_GRANULARITY + 1))",
    "#endif",
]

_REGION_NAPOT_DEFINES = [
    "#if UDB_PMP_GRANULARITY != 2",
    "    #define PMP_MASK            ~((1 << (UDB_PMP_GRANULARITY - 3))-1)",
    "    #define PMP_REGION_SIZE     (1 << (UDB_PMP_GRANULARITY - 3)) - 1",
    "#else",
    "    #define PMP_MASK            ~0",
    "    #define PMP_REGION_SIZE     0",
    "#endif",
]

_OFF_ADDR_MASKING = [
    "    LI(x6, NAPOT_ADDR_MASK)",
    "    and x5, x5, x6",
    "    LI(x6, NAPOT_ADDR_TRAILING_ONES)",
    "    or x5, x5, x6",
]


def _new_region_defines(size: str) -> list[str]:
    """`NEWREGION1..3`: the bases of the three consecutive regions."""
    return [
        "#define NEWREGION1          (REGIONSTART)",
        f"#define NEWREGION2          (REGIONSTART+{size})",
        f"#define NEWREGION3          (REGIONSTART+(2*{size}))",
    ]


def _pmpaddr_block(
    source: str,
    entry: int,
    *,
    offset: str | None = None,
    mask: list[str] | None = None,
    srl_sep: str = ", ",
) -> list[str]:
    """Program one pmpaddr CSR from a label, optionally offset and NAPOT-masked."""
    lines = [f"    LA(x5, {source})"]
    if offset is not None:
        lines.extend([f"    LI(x4, {offset})", "    add x5, x5, x4"])
    lines.append(f"    srl x5, x5{srl_sep}PMP_SHIFT")
    if mask:
        lines.extend(mask)
    lines.append(f"    csrw pmpaddr{entry}, x5")
    return lines


def _cfg_write(load: str, name: str) -> list[str]:
    return ["", f"    {load}(x4, {name})", "    csrw pmpcfg0, x4"]


def _xc_calls(calls: list[tuple[str, str]]) -> list[str]:
    lines = []
    for n, (target, label) in enumerate(calls, start=1):
        lines.extend(["", f"    // Test Case {n}: execute at {target}", f"    PMP_VERIFICATION_X_C {target}, {label}"])
    return lines


_AMODE_CONST = {"na4": "PMP_NA4", "napot": "PMP_NAPOT", "tor": "PMP_TOR", "off": None}
_FULL_PERMS = "PMP_L|PMP_R|PMP_W|PMP_X"


def _region_cfg_defines(amode: str) -> list[str]:
    """Three `#define PMP<n>CFG`: full, full, then locked-no-access (full for OFF)."""
    entries = (1, 2, 3) if amode == "tor" else (0, 1, 2)
    third = _FULL_PERMS if amode == "off" else "PMP_L"
    const = _AMODE_CONST[amode]
    # na4 and tor space the mask off from the closing paren.
    amp = ") &0xFF" if amode in ("na4", "tor") else ")&0xFF"
    lines = []
    for entry, perms in zip(entries, (_FULL_PERMS, _FULL_PERMS, third)):
        expr = perms if const is None else f"{perms}|{const}"
        lines.append(f"#define PMP{entry}CFG             (((({expr}{amp}) << PMP{entry}_CFG_SHIFT))")
    return lines


def _region_body(xlen: Xlen, amode: str, misaligned: bool, load: str, calls: list[tuple[str, str]]) -> list[str]:
    """Three consecutive PMP regions, then two (or four) execute attempts."""
    # misaligned_tor uses the rv64 clearing loop on both XLENs.
    loop_xlen = XLENS[64] if (amode == "tor" and misaligned and xlen.bits == 32) else xlen
    odd_srl = amode == "na4" and xlen.bits == 64
    srl_sep = " ," if odd_srl else ", "
    size = _REGION_SIZE_EXPR[amode]
    lines = [*zero_pmp_regs(loop_xlen), "", *_region_cfg_defines(amode), ""]
    region = "TEST_FOR_EXECUTION_0" if (amode == "na4" and misaligned) else "TEST_FOR_EXECUTION_1"
    lines.append(f"#define REGIONSTART             {region}")
    if amode == "napot":
        lines.extend(_REGION_NAPOT_DEFINES)
    if amode in ("napot", "off"):
        lines.extend(["", *_new_region_defines(size)])
    lines.extend(["", "    RVTEST_PMP_SET_BACKGROUND x4", ""])
    lines.append("//                                          Verification Section")
    lines.append(f"// Test Case: three consecutive {amode.upper()} regions, the third locked with XWR = 000")
    lines.append("")

    if amode == "tor":
        # TOR region n is [pmpaddr(n-1), pmpaddr(n)), so four addresses bound three regions.
        lines.extend(_pmpaddr_block("REGIONSTART", 0, srl_sep=srl_sep))
        for entry in (1, 2, 3):
            lines.append("")
            offset = "REGION_SIZE" if entry == 1 else f"{entry}*REGION_SIZE"
            lines.extend(_pmpaddr_block("REGIONSTART", entry, offset=offset, srl_sep=srl_sep))
            lines.extend(_cfg_write(load, f"PMP{entry}CFG"))
    elif amode == "na4":
        for entry in (0, 1, 2):
            if entry:
                lines.append("")
            offset = None if entry == 0 else ("REGION_SIZE" if entry == 1 else f"{entry}*REGION_SIZE")
            # Aligned na4 uses the odd separator only in its first block.
            sep = srl_sep if (misaligned or entry == 0) else ", "
            lines.extend(_pmpaddr_block("REGIONSTART", entry, offset=offset, srl_sep=sep))
            lines.extend(_cfg_write(load, f"PMP{entry}CFG"))
    else:
        mask = _NAPOT_ADDR_MASKING if amode == "napot" else ([] if misaligned else _OFF_ADDR_MASKING)
        for entry in (0, 1, 2):
            if entry:
                lines.append("")
            lines.extend(_pmpaddr_block(f"NEWREGION{entry + 1}", entry, mask=mask, srl_sep=srl_sep))
            if amode == "napot":
                lines.extend(_cfg_write(load, f"PMP{entry}CFG"))
        if amode == "off":
            lines.extend(_cfg_write(load, "PMP0CFG|PMP1CFG|PMP2CFG"))

    lines.append("    RVTEST_SFENCE_VMA_IF_SUPPORTED")
    lines.extend(_xc_calls(calls))
    lines.extend(
        [
            "",
            "    j exit                                                      // Verification Complete, exit the test",
            "",
        ]
    )
    # rv32 aligned_off keeps the return trampoline in the code section.
    if amode == "off" and not misaligned and xlen.bits == 32:
        lines.extend([*_RETURN_TRAMPOLINE, ""])
    lines.append("exit:")
    return lines


_STRADDLE_NOTE = [
    "// No .p2align here (and none before the later labels): the c.nop offsets above must survive",
    "// unrounded so these uncompressed jalr instructions land mid-word, genuinely straddling the",
    "// region boundary, instead of being pushed back onto the next grain-aligned boundary.",
]

_GRAIN_ALIGN = ".p2align (UDB_PMP_GRANULARITY)"


def _filler(count: str, instruction: str = "nop", repeats: int = 1) -> list[str]:
    return [f"    .rept {count}", *[f"    {instruction}"] * repeats, "    .endr"]


def _tail_count(xlen: Xlen, amode: str, *, misaligned: bool = False) -> str:
    """`.rept` count of the trailing filler region."""
    if amode == "tor":
        return _GRAIN
    # rv32 misaligned_napot writes the count without parentheses.
    if misaligned and xlen.bits == 32:
        return "REGION_SIZE"
    return "(REGION_SIZE)"


def _aligned_data(xlen: Xlen, amode: str) -> list[str]:
    """One uncompressed jalr inside each of the first two regions."""
    size = _REGION_SIZE_EXPR[amode]
    lines = [".p2align 12"]
    if amode == "off":
        lines.extend(
            [
                "TEST_FOR_EXECUTION_0:",
                *_filler("PMP_NAPOT_REGION_PAD_WORDS", "jalr x0, x1, 0"),
                "",
                "TEST_FOR_EXECUTION_1:",
                f"{_JALR}                                              // Uncompressed return inside the first region",
                *_filler(f"(({size} - 4) / 2)"),
                "",
                _GRAIN_ALIGN,
                "TEST_FOR_EXECUTION_2:",
                f"{_JALR}                                              // Uncompressed return inside the second region",
                *_filler(f"(({size} - 4) / 2)"),
            ]
        )
        # Only the rv64 file keeps the return trampoline in the data section.
        if xlen.bits == 64:
            lines.extend(["", *_RETURN_TRAMPOLINE])
        return lines

    lines.extend([_GRAIN_ALIGN, "TEST_FOR_EXECUTION_0:", _JALR])
    for n, where in ((1, "first"), (2, "second")):
        lines.extend(
            [
                "",
                _GRAIN_ALIGN,
                f"TEST_FOR_EXECUTION_{n}:",
                f"{_JALR}                                              // Uncompressed return inside the {where} region",
            ]
        )
        if amode != "na4":
            lines.extend(_filler(f"(({size} - 4) / 2)"))
    if amode != "na4":
        repeats = 2 if amode == "tor" else 1
        lines.extend(["", _GRAIN_ALIGN, "TEST_FOR_EXECUTION_3:", *_filler(_tail_count(xlen, amode), repeats=repeats)])
    lines.extend(["", *_RETURN_TRAMPOLINE])
    return lines


def _misaligned_data(xlen: Xlen, amode: str) -> list[str]:
    """An uncompressed jalr straddling the start and the end of the second region."""
    size = _REGION_SIZE_EXPR[amode]
    lines = [".p2align 12"]

    if amode == "na4":
        return [
            *lines,
            _GRAIN_ALIGN,
            "TEST_FOR_EXECUTION_X:",
            _JALR,
            "",
            _GRAIN_ALIGN,
            "TEST_FOR_EXECUTION_0:",
            "    c.nop                                                       // 2-byte filler: offsets _1/_2 so their jalr straddles the region boundary",
            "",
            *_STRADDLE_NOTE,
            "TEST_FOR_EXECUTION_1:",
            f"{_JALR}                                              // straddles the start of the 2nd region",
            "",
            "TEST_FOR_EXECUTION_2:",
            f"{_JALR}                                              // straddles the end of the 2nd region",
            "",
            *_RETURN_TRAMPOLINE,
        ]

    if amode == "off":
        lines.extend(["TEST_FOR_EXECUTION_0:", *_filler("PMP_NAPOT_REGION_PAD_WORDS", "jalr x0, x1, 0")])
    else:
        lines.extend([_GRAIN_ALIGN, "TEST_FOR_EXECUTION_0:", _JALR])
        if amode == "napot":
            lines.append(
                "    nop                                                         // NAPOT-safe filler: shifts REGIONSTART to PMP_NAPOT_REGION_START"
            )
        lines.append("")
        lines.append(_GRAIN_ALIGN)
    if amode == "off":
        lines.append("")
    lines.extend(["TEST_FOR_EXECUTION_1:", *_filler(f"(({size} / 2) -1)", "c.nop")])
    # misaligned_tor pads with uncompressed nops between _3 and _4; the others use c.nop.
    filler_3 = "nop" if amode == "tor" else "c.nop"
    lines.extend(
        [
            "",
            *_STRADDLE_NOTE,
            "TEST_FOR_EXECUTION_2:",
            f"{_JALR}                                              // straddles the start of the 2nd region",
            "",
            "TEST_FOR_EXECUTION_3:",
            *_filler(f"(({size} / 2) -2)", filler_3),
            "",
            "TEST_FOR_EXECUTION_4:",
            f"{_JALR}                                              // straddles the end of the 2nd region",
        ]
    )
    if amode != "off":
        lines.extend(["", _GRAIN_ALIGN, "TEST_FOR_EXECUTION_5:", *_filler(_tail_count(xlen, amode, misaligned=True))])
    lines.extend(["", *_RETURN_TRAMPOLINE])
    return lines


#: `LA` vs `LI` for the `#define PMP<n>CFG` constants, as (rv32, rv64) per (amode, misaligned).
_CFG_LOAD = {
    ("na4", False): ("LI", "LI"),
    ("na4", True): ("LI", "LI"),
    ("napot", False): ("LA", "LA"),
    ("napot", True): ("LA", "LA"),
    ("off", False): ("LI", "LI"),
    ("off", True): ("LI", "LI"),
    ("tor", False): ("LA", "LI"),
    ("tor", True): ("LI", "LI"),
}

#: Files whose data section opens with a `.p2align 4`, per (amode, misaligned, bits).
_DATA_ALIGNED = {
    ("napot", False, 64),
    ("off", False, 64),
    ("tor", False, 64),
    ("na4", True, 32),
    ("na4", True, 64),
    ("napot", True, 64),
    ("off", True, 32),
    ("off", True, 64),
    ("tor", True, 32),
    ("tor", True, 64),
}

#: Reporting string per file.
_ALIGNED_NA4_STR = "pmpzca_aligned_na4_region_execute"
_REGION_SIG_STR = {
    ("na4", False, 32): _ALIGNED_NA4_STR,
    ("na4", False, 64): _ALIGNED_NA4_STR,
    ("napot", False, 32): _ALIGNED_NA4_STR,
    ("napot", False, 64): "pmpzca_aligned_napot_region_execute",
    ("off", False, 32): "pmpzca_aligned_off_region_execute",
    ("off", False, 64): "pmpzca_aligned_off_region_execute",
    ("tor", False, 32): _ALIGNED_NA4_STR,
    ("tor", False, 64): "pmpzca_aligned_tor_region_execute",
    ("na4", True, 32): _ALIGNED_NA4_STR,
    ("na4", True, 64): "pmpzca_misaligned_na4_region_execute",
    ("napot", True, 32): _ALIGNED_NA4_STR,
    ("napot", True, 64): "pmpzca_misaligned_napot_execute",
    ("off", True, 32): _ALIGNED_NA4_STR,
    ("off", True, 64): "pmpzca_misaligned_off_execute",
    ("tor", True, 32): "pmpzca_misaligned_tor_start",
    ("tor", True, 64): "pmpzca_misaligned_tor_start",
}

_ALIGNED_CALLS = [("TEST_FOR_EXECUTION_1", "test_1"), ("TEST_FOR_EXECUTION_2", "test_2")]
_STRADDLE_CALLS = [("TEST_FOR_EXECUTION_2", "test_1"), ("TEST_FOR_EXECUTION_4", "test_2")]

_ALIGNED_TEST_CASES = """\
// Test Cases  : Setting up 3 standard consecutive {mode} PMP regions with L=1, XWR=111
//               (XWR = 000 for region 3). Place an uncompressed ret = jalr ra inside
//               first region and inside second region. Attempt jalr to each ret.
//
"""

_MISALIGNED_TEST_CASES = """\
// Test Cases  : Check that misaligned 32-bit fetches that cross a {mode} PMP boundary fail.
//               Setting up 3 standard consecutive {mode} PMP regions with L=1, XWR=111
//               (XWR = 000 for region 3). Place an uncompressed ret = jalr straddling the
//               start and end of the second regions. Attempt jalr to each ret.
//
"""


def _region_pre_main(amode: str, misaligned: bool) -> tuple[str, ...]:
    if amode == "na4":
        return ("#define REGION_SIZE     4",)
    if amode == "napot":
        return tuple(_NAPOT_PRE_MAIN)
    if amode == "tor":
        return ("#define REGION_SIZE (1<<(UDB_PMP_GRANULARITY))",)
    return tuple(_MISALIGNED_OFF_PRE_MAIN if misaligned else _OFF_PRE_MAIN)


def _region_file(xlen: Xlen, amode: str, misaligned: bool) -> PmpFile:
    key = (amode, misaligned)
    prefix = "misaligned" if misaligned else "aligned"
    if misaligned and amode == "napot":
        calls = [*_STRADDLE_CALLS, ("NEWREGION1", "test_3"), ("NEWREGION2", "test_4")]
    elif misaligned and amode != "na4":
        calls = _STRADDLE_CALLS
    else:
        calls = _ALIGNED_CALLS
    template = _MISALIGNED_TEST_CASES if misaligned else _ALIGNED_TEST_CASES
    return PmpFile(
        filename=f"pmpzca_{prefix}_{amode}.S",
        xlen=xlen,
        copyright=_COPYRIGHT,
        banner=_banner(
            f"// Coverpoints : cp_misaligned_{amode} for PMPZca is partially covered\n//               in this test file.\n",
            template.format(mode=amode.upper()),
        ),
        required_extensions=_extensions(xlen),
        params=_params(amode if amode != "off" else None),
        march=_march(xlen),
        priv_test=False,
        sigupd=sigupd_count(len(calls)),
        pre_main=_region_pre_main(amode, misaligned),
        body=tuple(_region_body(xlen, amode, misaligned, _CFG_LOAD[key][xlen.bits == 64], calls)),
        sig_strs=(("test_1", test_case_str(1, _REGION_SIG_STR[(amode, misaligned, xlen.bits)])),),
        data_align=4 if (amode, misaligned, xlen.bits) in _DATA_ALIGNED else None,
        data=tuple(_misaligned_data(xlen, amode) if misaligned else _aligned_data(xlen, amode)),
    )


#####################################################################
# pmpzca_legal_lwrx: every legal locked LXWR against compressed
# loads, stores and jumps.
#####################################################################

_LEGAL_TEST_CASES = """\
// Test Cases  : Check that WR bits control write/read access for every type of
//                 load and store. Attempt all types of reads and writes with
//                 pmpcfg_i.L=1, all legal pmpcfg_i.XWR. Observe proper access
//                 faults for restricted read/write regions
//
"""

#: Coverpoint name and reported index per XLEN.
_LEGAL_SIG_STRS = {
    32: (("sw", 1), ("lw", 1), ("c.swsp", 1), ("c.lwsp", 1)),
    64: (("sw", 1), ("lw", 2), ("c.jalr", 3), ("sd", 4), ("ld", 5)),
}


def _legal_lwrx_file(xlen: Xlen) -> PmpFile:
    return PmpFile(
        filename="pmpzca_legal_lwrx.S",
        xlen=xlen,
        copyright=_COPYRIGHT,
        banner=_banner(
            "// Coverpoints : cp_cfg_RW for PMPZca are fully covered in this test file.\n", _LEGAL_TEST_CASES
        ),
        required_extensions=_extensions(xlen),
        params=_params(None),
        march=_march(xlen),
        priv_test=False,
        sigupd=sigupd_count(len(LOCKED_LXWR_CASES) * len(_LEGAL_SIG_STRS[xlen.bits])),
        macro_blocks=(template(f"zca_legal_rwx{xlen.bits}"),),
        body=tuple(lxwr_napot_body(xlen, LOCKED_LXWR_CASES)),
        sig_strs=tuple(
            (f"test_{n}", test_case_str(index, f"pmpzca_legal_lxwr_{name}"))
            for n, (name, index) in enumerate(_LEGAL_SIG_STRS[xlen.bits], start=1)
        ),
        data_align=4 if xlen.bits == 64 else None,
        data=tuple(template("exec_region_cnop").strip("\n").splitlines()),
    )


#####################################################################
# pmpzc{b,d,f}_legal_*: the same LXWR walk driven by the compressed
# load/store subsets Zcb, Zcd and Zcf.
#####################################################################

_ZC_TEST_CASES = """\
// Test Cases  : Check that WR bits control write/read access for every type of
//                 load and store. Attempt all types of reads and writes with
//                 pmpcfg_i.L=1, all legal pmpcfg_i.XWR. Observe proper access
//                 faults for restricted read/write regions.
"""

#: Width the `test: <n>;` tag is padded to in these files' reporting strings.
_ZC_TAG_WIDTH = 9

#: Coverpoint suffixes per subset; every string is named `pmpzcb_*`.
_ZC_COVERPOINTS = {
    "zcb": ("c.sb", "c.lbu", "c.sh", "c.lhu", "c.sh", "c.shu"),
    "zcd": ("c.fsd", "c.fld"),
    "zcf": ("c.fsw", "c.flw"),
}

#: Enable mstatus.FS so the floating-point compressed forms are legal.
_ENABLE_FS = ["", "    li x4, 0x00006000", "    csrs mstatus, x4", "    fscsr x0"]


def _zc_body(xlen: Xlen, subset: str) -> list[str]:
    body = lxwr_napot_body(
        xlen,
        LOCKED_LXWR_CASES,
        extra_setup=_ENABLE_FS if subset != "zcb" else None,
        runner="VERIFICATION_RWX" if subset == "zcf" else f"PMP_VERIFICATION_X_{subset.upper()}",
    )
    if subset == "zcf":
        # Zcf opens with the rv64 clearing loop and derives every other CSR the rv32 way.
        body[: len(zero_pmp_regs(xlen))] = zero_pmp_regs(XLENS[64])
    return body


def _zc_file(xlen: Xlen, subset: str) -> PmpFile:
    coverpoints = _ZC_COVERPOINTS[subset]
    stem = "lxwr" if xlen.bits == 32 else "lwxr"
    return PmpFile(
        filename=f"pmp{subset}_legal_{stem}.S",
        xlen=xlen,
        banner=_banner("// Coverpoints : cp_cfg_RW for PMPZca are fully covered in this test file.\n", _ZC_TEST_CASES),
        required_extensions=(subset.capitalize(), "Sm"),
        params=_params(None),
        march=f"rv{xlen.bits}i_zicsr_zifencei_{subset}",
        sigupd=sigupd_count(len(LOCKED_LXWR_CASES) * len(coverpoints)),
        macro_blocks=(template("zcf_legal_rwx"),) if subset == "zcf" else (),
        body=tuple(_zc_body(xlen, subset)),
        sig_strs=tuple(
            (f"test_{n}", test_case_str(n, f"pmpzcb_cfg_wr_{cp}", _ZC_TAG_WIDTH))
            for n, cp in enumerate(coverpoints, start=1)
        ),
        data_align=4,
        data=tuple(template("exec_region_x_nop").strip("\n").splitlines()),
    )


@add_pmp_suite("PMPZca")
def build() -> list[PmpFile]:
    """Every PMPZca file, for both XLENs."""
    specs: list[PmpFile] = []
    for xlen in XLENS.values():
        specs.extend(_cret_file(xlen, amode) for amode in ("na4", "napot", "tor"))
        specs.extend(
            _region_file(xlen, amode, misaligned)
            for misaligned in (False, True)
            for amode in ("na4", "napot", "off", "tor")
        )
        specs.append(_legal_lwrx_file(xlen))
        specs.extend(_zc_file(xlen, subset) for subset in ("zcb", "zcd"))
    # Zcf is rv32-only.
    specs.append(_zc_file(XLENS[32], "zcf"))
    return specs
