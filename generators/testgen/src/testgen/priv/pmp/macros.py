##################################
# priv/pmp/macros.py
#
# Shared assembly building blocks for the pure PMP suite generators.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Assembly fragments shared by the ``tests/priv/pmp`` suites.

Long verbatim assembly lives in ``pmp_templates/*.S`` and is loaded with
:func:`template`; this module holds the short blocks that are cheaper to build
from their parameters than to store once per variant.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from testgen.priv.pmp.model import Xlen

_TEMPLATE_DIR = Path(__file__).parent / "pmp_templates"


def template(name: str) -> str:
    """Read one verbatim assembly template from ``pmp_templates/``."""
    return (_TEMPLATE_DIR / f"{name}.S").read_text()


def zero_pmp_regs(xlen: Xlen) -> list[str]:
    """Clear every implemented pmpcfg and pmpaddr CSR."""
    return [
        "    // Loop to SET ALL pmpcfg REGs to zero",
        "    .set pmpcfgi, CSR_PMPCFG0",
        f"    .rept {xlen.cfg_rept}",
        "    csrw pmpcfgi , x0",
        f"    .set pmpcfgi, pmpcfgi+{xlen.cfg_step}",
        "    .endr",
        "",
        "    // Loop to SET ALL pmpaddr REGs to zero",
        "    .set pmpaddri, CSR_PMPADDR0",
        "    .rept UDB_NUM_PMP_ENTRIES",
        "    csrw pmpaddri, x0",
        "    .set pmpaddri, pmpaddri+1",
        "    .endr",
    ]


def cfg_csr(xlen: Xlen, entry: int) -> str:
    """Name of the pmpcfg CSR holding ``entry``'s configuration byte."""
    return f"pmpcfg{(entry // xlen.cfgs_per_reg) * xlen.cfg_step}"


def cfg_shift(xlen: Xlen, entry: int) -> str:
    """Name of the shift constant placing ``entry``'s byte inside its pmpcfg CSR."""
    return f"PMP{entry % xlen.cfgs_per_reg}_CFG_SHIFT"


#: PMP permission bits in the order they appear in the LXWR mnemonic.
_LXWR_BITS = ("PMP_L", "PMP_X", "PMP_W", "PMP_R")
#: ... and in the order they are written in the generated #define expressions.
_LXWR_ORDER = ("PMP_L", "PMP_R", "PMP_W", "PMP_X")


def lxwr_expr(lxwr: str, amode: str) -> str:
    """Column-aligned ``PMP_L|PMP_R|PMP_W|PMP_X|<amode>`` expression for an LXWR code.

    ``lxwr`` is the four-character L/X/W/R bit string used in the test names,
    e.g. ``"1011"`` = locked, no execute, write, read.
    """
    present = {bit for bit, ch in zip(_LXWR_BITS, lxwr, strict=True) if ch == "1"}
    fields = [f"{bit}|" if bit in present else " " * (len(bit) + 1) for bit in _LXWR_ORDER]
    return "".join(fields) + amode


def lxwr_defines(xlen: Xlen, cases: list[tuple[str, int]], amode: str) -> list[str]:
    """``#define PMPREGION_LXWR_<bits>`` lines, one per (LXWR code, PMP entry) case."""
    return [
        f"#define PMPREGION_LXWR_{lxwr} (((({lxwr_expr(lxwr, amode)})&0xFF) << {cfg_shift(xlen, entry)}))"
        for lxwr, entry in cases
    ]


#: Human-readable permission names for the `// Test Case:` banner comments.
LXWR_PERM_NAMES: dict[str, str] = {
    "000": "No Permissions",
    "001": "R Permissions",
    "011": "WR Permissions",
    "100": "X Permissions",
    "101": "XR Permissions",
    "111": "XWR Permissions",
}


def case_banner(index: int, lxwr: str, entry: int) -> list[str]:
    """The ``// Test Case: n : L -> b and <perms> given to the PMP Region e`` comment."""
    perms = LXWR_PERM_NAMES.get(lxwr[1:], f"{lxwr[1:]} Permissions")
    return ["", f"// Test Case: {index} : L -> {lxwr[0]} and {perms} given to the PMP Region {entry}"]


def set_pmpaddr_napot(entry: int, addr_reg: str = "x5", tmp_reg: str = "x6") -> list[str]:
    """Program ``pmpaddr<entry>`` with the NAPOT encoding of REGIONSTART."""
    return [
        f"    LA({addr_reg}, REGIONSTART)",
        f"    srl {addr_reg}, {addr_reg}, PMP_SHIFT",
        f"    LI({tmp_reg}, PMP_MASK)",
        f"    and {addr_reg}, {addr_reg}, {tmp_reg}",
        f"    LI({tmp_reg}, PMP_REGION_SIZE)",
        f"    or {addr_reg}, {addr_reg}, {tmp_reg}",
        f"    csrw pmpaddr{entry}, {addr_reg}",
    ]


def set_pmpaddr_plain(entry: int, addr_reg: str = "x4") -> list[str]:
    """Program ``pmpaddr<entry>`` with REGIONSTART for NA4/TOR (no size encoding)."""
    return [
        f"    LA({addr_reg}, REGIONSTART)",
        f"    srl {addr_reg}, {addr_reg}, PMP_SHIFT",
        f"    csrw pmpaddr{entry}, {addr_reg}",
    ]


#: NAPOT address-mask helper defines, needed wherever `set_pmpaddr_napot` is used.
NAPOT_MASK_DEFINES = [
    "#if UDB_PMP_GRANULARITY != 2",
    "    #define PMP_MASK            ~((1 << (UDB_PMP_GRANULARITY - 3))-1)",
    "    #define PMP_REGION_SIZE     (1 << (UDB_PMP_GRANULARITY - 3)) - 1",
    "#else",
    "    #define PMP_MASK            ~0",
    "    #define PMP_REGION_SIZE     0",
    "#endif",
]

#: The region-under-test lives in the executable data blob emitted by the data section.
REGIONSTART_DEFINE = "#define REGIONSTART            TEST_FOR_EXECUTION    // RAM_BASE_ADDR + PROGRAM_SIZE"

VERIFICATION_SECTION_BANNER = "//                                            Verification Section"


def lxwr_napot_body(
    xlen: Xlen,
    cases: list[tuple[str, int]],
    *,
    extra_setup: list[str] | None = None,
    runner: str = "VERIFICATION_RWX    TEST_FOR_EXECUTION",
    runner_for: Callable[[int, str, int], str] | None = None,
) -> list[str]:
    """Body shared by the "walk every legal LXWR against one locked NAPOT region" tests.

    Clears the PMP CSRs, defines one ``PMPREGION_LXWR_*`` constant per case, sets a
    permissive background region, and then runs ``runner`` once per case with that
    case's configuration byte installed in its PMP entry. ``runner_for(n, lxwr, entry)``
    overrides ``runner`` per case for suites whose permitted cases use a different macro.
    """
    lines = [*zero_pmp_regs(xlen)]
    if extra_setup:
        lines.extend(extra_setup)
    lines.extend(["", *lxwr_defines(xlen, cases, "PMP_NAPOT")])
    lines.extend(["", REGIONSTART_DEFINE, *NAPOT_MASK_DEFINES])
    lines.extend(["", "    RVTEST_PMP_SET_BACKGROUND x4", "", VERIFICATION_SECTION_BANNER])
    for n, (lxwr, entry) in enumerate(cases, start=1):
        lines.extend(case_banner(n, lxwr, entry))
        lines.append("")
        lines.extend(set_pmpaddr_napot(entry))
        lines.extend(["", f"    LI(x4, PMPREGION_LXWR_{lxwr})", f"    csrw {cfg_csr(xlen, entry)}, x4"])
        this_runner = runner_for(n, lxwr, entry) if runner_for else runner
        lines.extend(["", "    RVTEST_SFENCE_VMA_IF_SUPPORTED", f"    {this_runner}, test_{n}"])
    lines.extend(["", "    j exit                  // Verification Complete, exit the test", "", "exit:"])
    return lines


#: The six legal (L=1) LXWR encodings, each parked in its own PMP entry so that the
#: most permissive one has the highest priority.
LOCKED_LXWR_CASES: list[tuple[str, int]] = [
    ("1000", 5),
    ("1001", 4),
    ("1011", 3),
    ("1100", 2),
    ("1101", 1),
    ("1111", 0),
]


#: Slack added to every computed SIGUPD_COUNT before rounding, so that a test whose
#: trap behaviour differs slightly between models still has room in the signature.
_SIGUPD_MARGIN = 10


def sigupd_count(updates: int) -> int:
    """Signature-region size for a test that performs ``updates`` RVTEST_SIGUPD calls."""
    return ((updates + _SIGUPD_MARGIN + 9) // 10) * 10


def test_case_str(index: int, coverpoint: str, tag_width: int = 0) -> str:
    """Reporting string for one testcase: ``test: <n>; cp: <coverpoint>``.

    ``tag_width`` pads the ``test: <n>;`` tag to a fixed column, which several suites
    do so that the ``cp:`` fields line up once the index reaches two digits. The exact
    spacing is part of the string literal, so it must match the hand-written original.
    """
    return f"{f'test: {index};':<{tag_width}} cp: {coverpoint}"
