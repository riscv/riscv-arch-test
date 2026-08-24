##################################
# priv/pmp/suites/PMPF.py
#
# PMPF: PMP enforcement of floating-point loads and stores.
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMPF suite: WR bits control every width of floating-point load and store."""

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
// Coverpoints : cp_cfg_RW for PMPF is fully covered in this test file.
//
// Test Cases  : Checking that WR bits control write/read access for every type of
//                 load and store. mstatus.FS = nonzero. Attempt all types of reads
//                  and writes with pmpcfg_i.L=1, all legal pmpcfg_i.XWR. Observing
//                 proper access faults for restricted read/write regions.
"""

# Only RV64 enables the FPU before the floating-point accesses; the RV32 test does
# not (preserved from the hand-written original).
_ENABLE_FPU = [
    "",
    "    // Enable the FPU: set mstatus.FS = 01 (Initial)",
    "    // mstatus bits 14:13 = FS. Value 0x00006000 sets FS=11 (Dirty), safe for all F ops.",
    "    li   x4, 0x00006000",
    "    csrs mstatus, x4        // set FS bits without disturbing anything else",
    "",
    "    // zero out fcsr so fflags start clean",
    "    fscsr x0",
]

_SIG_STRS = tuple(
    (f"test_{n}", test_case_str(n, f"pmpf_cfg_wr_{op}.S", _TAG_WIDTH))
    for n, op in enumerate(("fsh", "fsw", "fsd", "flh", "flw", "fld"), start=1)
)


def _body(xlen: Xlen) -> list[str]:
    # Only RV64 enables the FPU here; the RV32 original does not.
    return lxwr_napot_body(xlen, LOCKED_LXWR_CASES, extra_setup=_ENABLE_FPU if xlen.bits == 64 else None)


@add_pmp_suite("PMPF")
def build() -> list[PmpFile]:
    """One file per XLEN exercising floating-point access against a locked NAPOT region."""
    return [
        PmpFile(
            filename="pmpf_cfg_wr.S",
            xlen=xlen,
            banner=_BANNER,
            required_extensions=("F", "Sm"),
            params=("NUM_PMP_ENTRIES: '>0'",),
            march=f"rv{xlen.bits}ifd_zicsr_zifencei_zfhmin",
            sigupd=sigupd_count(len(LOCKED_LXWR_CASES) * len(_SIG_STRS)),
            macro_blocks=(template("pmpf_verification_rwx"),),
            body=tuple(_body(xlen)),
            sig_strs=_SIG_STRS,
            data_align=4,
            data=tuple(template("exec_region_pad_granule").strip("\n").splitlines()),
        )
        for xlen in XLENS.values()
    ]
