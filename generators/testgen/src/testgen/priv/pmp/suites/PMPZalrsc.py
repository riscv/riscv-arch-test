##################################
# priv/pmp/suites/PMPZalrsc.py
#
# PMPZalrsc: PMP enforcement of load-reserved / store-conditional.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMPZalrsc suite: WR bits control LR/SC at every supported width."""

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
// Coverpoints : cp_cfg_RW for PMPZalrsc is fully covered in this test file.
//
// Test Cases  : Checking that WR bits control access for lr and sc. Attempt
//                 LR/SC pairs with pmpcfg_i.L=1 and all legal pmpcfg_i.XWR,
//                 observing proper access faults for restricted regions.
"""

#: Cases whose configuration permits both read and write, where LR/SC is expected to
#: succeed and so must run in the retry loop rather than the single-shot macro.
_SUCCESS_CASES = {"1011", "1111"}

_ADDR = "    LA(a5, \\ADDRESS)                                         // Address to be verified"
_RETRY_INIT = "    LI(t2, 100)                                              // Retry counter for constrained LR/SC loop"


def _widths(xlen: Xlen) -> tuple[str, ...]:
    return ("w", "d") if xlen.bits == 64 else ("w",)


def _fault_macro(xlen: Xlen) -> str:
    """LR/SC pairs that are expected to trap: each access checked on its own."""
    lines = [".macro VERIFICATION_RWX ADDRESS TEST_CASE"]
    for i, width in enumerate(_widths(xlen)):
        lr, sc = 2 * i + 1, 2 * i + 2
        lines.extend(
            [
                "",
                _ADDR,
                "",
                f"    \\TEST_CASE\\()_{lr}:",
                f"    lr.{width} a2, (a5)",
                "    nop",
                f"    RVTEST_SIGUPD(x2, x5, x4, a2, \\TEST_CASE\\()_{lr}, test_{lr}_str)",
                "",
                f"    \\TEST_CASE\\()_{sc}:",
                f"    sc.{width} a2, a2, (a5)",
                "    nop",
                f"    RVTEST_SIGUPD(x2, x5, x4, a2, \\TEST_CASE\\()_{sc}, test_{sc}_str)",
            ]
        )
    lines.extend(["", ".endm"])
    return "\n".join(lines)


def _success_macro(xlen: Xlen) -> str:
    """LR/SC pairs that are expected to succeed: bounded retry around each pair."""
    widths = _widths(xlen)
    # RV32 has a single width, so its labels carry no width tag.
    tag = {w: f"_{w}" if len(widths) > 1 else "" for w in widths}
    lines = [".macro VERIFICATION_RWX_SUCCESS ADDRESS TEST_CASE"]
    for i, width in enumerate(widths):
        lr, sc = 2 * i + 1, 2 * i + 2
        t = tag[width]
        lines.extend(
            [
                "",
                _ADDR,
                _RETRY_INIT,
                f"\\TEST_CASE\\(){t}_retry:",
                f"    \\TEST_CASE\\()_{lr}:",
                f"    lr.{width} a3, (a5)",
                f"    \\TEST_CASE\\()_{sc}:",
                f"    sc.{width} a2, a3, (a5)",
                f"    beqz a2, \\TEST_CASE\\(){t}_success                      // SC succeeded, skip retry",
                "    addi t2, t2, -1                                          // Decrement retry count",
                f"    bnez t2, \\TEST_CASE\\(){t}_retry                        // Retry LR/SC if not exhausted",
                f"\\TEST_CASE\\(){t}_success:",
                f"    RVTEST_SIGUPD(x2, x5, x4, a3, \\TEST_CASE\\()_{lr}, test_{lr}_str)",
                f"    RVTEST_SIGUPD(x2, x5, x4, a2, \\TEST_CASE\\()_{sc}, test_{sc}_str)",
            ]
        )
    lines.extend(["", ".endm"])
    return "\n".join(lines)


def _runner_for(_n: int, lxwr: str, _entry: int) -> str:
    macro = "VERIFICATION_RWX_SUCCESS" if lxwr in _SUCCESS_CASES else "VERIFICATION_RWX"
    return f"{macro}    TEST_FOR_EXECUTION"


def _sig_strs(xlen: Xlen) -> tuple[tuple[str, str], ...]:
    # "lr_f" and "sc_d" preserve the coverpoint names used by the hand-written test.
    names = ("lr_w", "sc_w", "lr_f", "sc_d")[: 2 * len(_widths(xlen))]
    return tuple(
        (f"test_{n}", test_case_str(n, f"pmpzalrc_cfg_wr_{name}", _TAG_WIDTH)) for n, name in enumerate(names, start=1)
    )


@add_pmp_suite("PMPZalrsc")
def build() -> list[PmpFile]:
    """One file per XLEN running LR/SC against each legal locked NAPOT configuration."""
    return [
        PmpFile(
            filename="pmpzalrsc_cfg_wr.S",
            xlen=xlen,
            banner=_BANNER,
            required_extensions=("Zalrsc", "Sm"),
            params=("NUM_PMP_ENTRIES: '>0'",),
            march=f"rv{xlen.bits}i_zicsr_zifencei_zalrsc",
            sigupd=sigupd_count(len(LOCKED_LXWR_CASES) * len(_sig_strs(xlen))),
            macro_blocks=(_fault_macro(xlen), _success_macro(xlen)),
            body=tuple(lxwr_napot_body(xlen, LOCKED_LXWR_CASES, runner_for=_runner_for)),
            sig_strs=_sig_strs(xlen),
            data_align=4,
            data=tuple(template("exec_region_pad_granule").strip("\n").splitlines()),
        )
        for xlen in XLENS.values()
    ]
