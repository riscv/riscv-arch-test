##################################
# priv/pmp/suites/PMPZicbo.py
#
# PMPZicbo: PMP enforcement of cache-block operations and prefetch hints.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMPZicbo suite: WR bits control cbo.*, and prefetch.* never faults."""

from __future__ import annotations

from testgen.priv.pmp import add_pmp_suite
from testgen.priv.pmp.macros import (
    LOCKED_LXWR_CASES,
    PAGE_NAPOT_MASK_DEFINES,
    VERIFICATION_SECTION_BANNER,
    cfg_csr,
    cfg_shift,
    lxwr_expr,
    lxwr_napot_body,
    regionstart_define,
    set_pmpaddr_napot,
    sigupd_count,
    template,
    test_case_str,
    zero_pmp_regs,
)
from testgen.priv.pmp.model import XLENS, PmpFile, Xlen

#: Width the `test: <n>;` tag is padded to in this suite's reporting strings.
_TAG_WIDTH = 9

#: Both files put the region under test in the first of the two executable blobs.
_REGION = "TEST_FOR_EXECUTION_1"

#: The PMP entry every cbo_wr file configures.
_CBO_ENTRY = 0

_BANNER_CBO = """
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
// Coverpoints : cp_cbo for PMPZicbo is partially covered in this test file.
//
// Test Cases  : Checking that WR bits control access for cbo.*. Attempting all
//                 {{cbo.zero, cbo.flush, cbo.clean, cbo.inval}} with pmpcfg_i.L=1,
//                 pmpcfg_i.WR = {wr}, Observing proper access faults for restricted
//                 read/write regions.
"""

_BANNER_PREFETCH = """
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
// Coverpoints : cp_prefetch for PMPZicbo is partially covered in this test file.
//
// Test Cases  : Check that XWR bits control access for prefetch.
//                 Attempt {prefetch.i/w/r} with pmpcfg_i.L=1, legal pmpcfg_i.XWR,
//                 at start of 4 KB region plenty long to encompass a cache line.
//                 No exceptions should be raised.
"""

#: menvcfg.CBIE, CBCFE and CBZE must all be enabled for cbo.* to be legal at all.
_MENVCFG_DEFINE = (
    "#define MENVCFG                    0xF0                                    // menvcfg.CBIE, CBCFE, CBZE = 1"
)


def _enable_cbo(scratch_reg: str) -> list[str]:
    """Set the menvcfg bits that permit cache-block operations."""
    return [f"    li {scratch_reg}, MENVCFG", f"    csrrs zero, menvcfg, {scratch_reg}"]


#: The three cbo_wr files as (file number, LXWR code).
_CBO_FILES: tuple[tuple[int, str], ...] = ((1, "1000"), (2, "1001"), (3, "1011"))

#: Scratch register used to set menvcfg: a4 in rv32 files 1 and 3, t0 elsewhere.
_MENVCFG_REG: dict[tuple[int, int], str] = {(32, 1): "a4", (32, 3): "a4"}

#: Files that return to M-mode before exiting.
_GOTO_MMODE_FILES: set[tuple[int, int]] = {(64, 2)}


def _cbo_body(xlen: Xlen, number: int, lxwr: str) -> list[str]:
    """One locked NAPOT region, then all four cbo.* operations against it."""
    lines = [*zero_pmp_regs(xlen)]
    cfg_expr = f"(((({lxwr_expr(lxwr, 'PMP_NAPOT')})&0xFF)   << {cfg_shift(xlen, _CBO_ENTRY)}))"
    lines.extend(["", f"#define PMPCFG_{_CBO_ENTRY} {cfg_expr}"])
    lines.extend(["", regionstart_define(_REGION), *PAGE_NAPOT_MASK_DEFINES])
    lines.extend(["", _MENVCFG_DEFINE])
    lines.extend(["", "    RVTEST_PMP_SET_BACKGROUND x4"])
    lines.extend(["", *_enable_cbo(_MENVCFG_REG.get((xlen.bits, number), "t0"))])
    lines.extend(
        [
            "",
            VERIFICATION_SECTION_BANNER,
            f"// Test Case: {number} : {{cbo.zero, cbo.flush, cbo.clean, cbo.inval}} for XWR-{lxwr[1:]}",
            "",
        ]
    )
    lines.extend(set_pmpaddr_napot(_CBO_ENTRY, addr_reg="x4", tmp_reg="x6"))
    lines.extend(["", f"    LI(x4, PMPCFG_{_CBO_ENTRY})", f"    csrw {cfg_csr(xlen, _CBO_ENTRY)}, x4"])
    lines.extend(["", "    RVTEST_SFENCE_VMA_IF_SUPPORTED", f"    PMP_VERIFICATION_CBO    {_REGION}, test_1"])
    if (xlen.bits, number) in _GOTO_MMODE_FILES:
        lines.extend(["", "    RVTEST_GOTO_MMODE"])
    lines.extend(["", "    j exit                  // Verification Complete, exit the test", "", "exit:"])
    return lines


_CBO_OPS = ("zero", "clean", "flush", "inval")

_CBO_SIG_STRS = tuple(
    (f"test_{n}", test_case_str(n, f"pmpzicbo_cbo_{op}", _TAG_WIDTH)) for n, op in enumerate(_CBO_OPS, start=1)
)

_PREFETCH_HINTS = ("i", "r", "w")

_PREFETCH_SIG_STRS = tuple(
    (f"test_{n}", test_case_str(n, f"pmpzicbo_prefetch_{hint}", _TAG_WIDTH))
    for n, hint in enumerate(_PREFETCH_HINTS, start=1)
)


def _prefetch_macro() -> str:
    """All three prefetch hints against one address, each result recorded separately."""
    lines = [
        ".macro VERIFICATION_RWX ADDRESS TEST_CASE",
        "",
        "    // Address must be aligned to the cache block",
        "    LA(t0, \\ADDRESS)",
    ]
    for n, hint in enumerate(_PREFETCH_HINTS, start=1):
        lines.extend(
            [
                f"    \\TEST_CASE\\()_{n}:",
                f"    prefetch.{hint} 0(t0)",
                "    nop",
                f"    RVTEST_SIGUPD(x2, x5, x4, a4, \\TEST_CASE\\()_{n}, test_{n}_str)",
                "",
            ]
        )
    lines.append(".endm")
    return "\n".join(lines)


@add_pmp_suite("PMPZicbo")
def build() -> list[PmpFile]:
    """Three cbo_wr files per XLEN plus one prefetch walk over every legal LXWR."""
    specs: list[PmpFile] = []
    for xlen in XLENS.values():
        specs.extend(
            PmpFile(
                filename=f"pmpzicbo_cbo_wr_{number:02d}.S",
                xlen=xlen,
                banner=_BANNER_CBO.format(wr=lxwr[2:]),
                required_extensions=("Sm", "Zicbom", "Zicboz"),
                params=("NUM_PMP_ENTRIES: '>0'",),
                march=f"rv{xlen.bits}i_zicsr_zifencei_zicbom_zicboz",
                sigupd=sigupd_count(len(_CBO_SIG_STRS)),
                body=tuple(_cbo_body(xlen, number, lxwr)),
                sig_strs=_CBO_SIG_STRS,
                data=tuple(template("exec_region_pair").strip("\n").splitlines()),
            )
            for number, lxwr in _CBO_FILES
        )
        specs.append(
            PmpFile(
                filename="pmpzicbo_prefetch.S",
                xlen=xlen,
                banner=_BANNER_PREFETCH,
                required_extensions=("Sm", "Zicbop"),
                params=("NUM_PMP_ENTRIES: '>0'",),
                march=f"rv{xlen.bits}i_zicsr_zifencei_zicbop",
                sigupd=sigupd_count(len(LOCKED_LXWR_CASES) * len(_PREFETCH_SIG_STRS)),
                macro_blocks=(_prefetch_macro(),),
                body=tuple(
                    lxwr_napot_body(
                        xlen,
                        LOCKED_LXWR_CASES,
                        region=_REGION,
                        mask_defines=PAGE_NAPOT_MASK_DEFINES,
                        extra_defines=[_MENVCFG_DEFINE],
                        post_background=_enable_cbo("t0"),
                        addr_reg="x4",
                        tmp_reg="x6",
                        name_entry=False,
                    )
                ),
                sig_strs=_PREFETCH_SIG_STRS,
                data_align=4,
                data=tuple(template("exec_region_pair").strip("\n").splitlines()),
            )
        )
    return specs
