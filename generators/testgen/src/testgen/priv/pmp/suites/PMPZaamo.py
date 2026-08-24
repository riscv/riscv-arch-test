##################################
# priv/pmp/suites/PMPZaamo.py
#
# PMPZaamo: PMP enforcement of atomic memory operations.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMPZaamo suite: WR bits control every Zaamo atomic memory operation."""

from __future__ import annotations

from testgen.priv.pmp import add_pmp_suite
from testgen.priv.pmp.macros import LOCKED_LXWR_CASES, lxwr_napot_body, sigupd_count, template, test_case_str

#: Width the `test: <n>;` tag is padded to in this suite's reporting strings.
_TAG_WIDTH = 9
from testgen.priv.pmp.model import XLENS, PmpFile, Xlen

_BANNER = """
// Title           : Comprehensive PMP (Physical Memory Protection) Verification
// Authors         : Umer Shahid, Allen Baum, David Harris
//                  Muhammad Abdullah, Hamza Ali, Muhammad Zain
//
// Description : This test verifies the functionality and enforcement of
//               Physical Memory Protection (PMP) configurations in RISC-V
//               systems. It specifically tests the Read, Write and Execute
//               permissions for a designated memory region, ensuring that
//               the PMP settings are correctly applied and that the system
//               behaves as expected when accessing this region.
//
// Coverpoints : cp_cfg_RW for PMPZaamo is fully covered in this test file.
//
// Test Cases  : Checking that WR bits control access for every AMO instruction.
//                 Attempt every AMO with pmpcfg_i.L=1 and all legal pmpcfg_i.XWR,
//                 observing proper access faults for restricted regions.
"""

#: AMO mnemonics in the order the hand-written macro issues them.
_AMOS = ("amoadd", "amoand", "amoor", "amoxor", "amomax", "amomaxu", "amomin", "amominu", "amoswap")


def _widths(xlen: Xlen) -> tuple[str, ...]:
    return ("w", "d") if xlen.bits == 64 else ("w",)


def _ops(xlen: Xlen) -> list[tuple[str, str]]:
    """(mnemonic, width) pairs in issue order: every AMO at every supported width."""
    return [(amo, width) for amo in _AMOS for width in _widths(xlen)]


def _macro(xlen: Xlen) -> str:
    fill = "DOUBLE_NOP" if xlen.bits == 64 else "NOP"
    lines = [
        ".macro VERIFICATION_RWX ADDRESS TEST_CASE",
        "",
        f"    LI(a6, {fill})",
        "    LA(a5, \\ADDRESS)                                         // Address to be verified",
    ]
    for n, (amo, width) in enumerate(_ops(xlen), start=1):
        lines.extend(
            [
                "",
                f"    \\TEST_CASE\\()_{n}:",
                f"    {amo}.{width} a4, a6, (a5)",
                "    nop",
                "    nop",
                f"    RVTEST_SIGUPD(x2, x5, x4, a4, \\TEST_CASE\\()_{n}, test_{n}_str)   // Signature update",
            ]
        )
    lines.extend(["", ".endm"])
    return "\n".join(lines)


def _sig_strs(xlen: Xlen) -> tuple[tuple[str, str], ...]:
    # RV32 names the coverpoint without a width suffix; RV64 appends _w / _d.
    suffixed = xlen.bits == 64
    return tuple(
        (f"test_{n}", test_case_str(n, f"pmpzaamo_cfg_wr_{amo}{'_' + width if suffixed else ''}", _TAG_WIDTH))
        for n, (amo, width) in enumerate(_ops(xlen), start=1)
    )


@add_pmp_suite("PMPZaamo")
def build() -> list[PmpFile]:
    """One file per XLEN running every AMO against each legal locked NAPOT configuration."""
    return [
        PmpFile(
            filename="pmpzaamo_cfg_wr.S",
            xlen=xlen,
            banner=_BANNER,
            required_extensions=("Zaamo", "Sm"),
            params=("NUM_PMP_ENTRIES: '>0'",),
            march=f"rv{xlen.bits}i_zicsr_zifencei_zaamo",
            sigupd=sigupd_count(len(LOCKED_LXWR_CASES) * len(_sig_strs(xlen))),
            macro_blocks=(_macro(xlen),),
            body=tuple(lxwr_napot_body(xlen, LOCKED_LXWR_CASES)),
            sig_strs=_sig_strs(xlen),
            data_align=4,
            data=tuple(template("exec_region_nopad").strip("\n").splitlines()),
        )
        for xlen in XLENS.values()
    ]
