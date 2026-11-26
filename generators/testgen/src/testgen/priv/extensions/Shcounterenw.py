##################################
# Shcounterenw.py
#
# Shcounterenw extension test generator: hcounteren bits are writable for implemented hpmcounters.
# David_Harris@hmc.edu 24 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shcounterenw extension test generator: hcounteren bits are writable for implemented hpmcounters."""

from testgen.asm.csr import csr_access_test, csr_walk_test
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

_CG = "Shcounterenw_cg"
_SM_CG = "Shcounterenw_Sm_cg"
coverpoint = "cp_shcounterenw"


@add_priv_test_generator(
    "Shcounterenw",
    required_extensions=["H", "Shcounterenw"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_shcounterenw(test_data: TestData) -> list[TestChunk]:
    """Generate tests for Shcounterenw coverpoints, as Sscounterenw does for scounteren."""
    tc = test_data.begin_test_chunk()
    tc.code.extend(
        [
            comment_banner(
                coverpoint,
                "In HS-mode, set and clear each bit of hcounteren, then write all 1s and all 0s.  The bit of each\n"
                "hpmcounter that is not read-only zero must be writable; the reference model gives the other bits",
            ),
            *csr_walk_test(test_data, ("hcounteren", None), _CG, coverpoint),
            *csr_access_test(test_data, ("hcounteren", None), _CG, coverpoint),
        ]
    )
    return [test_data.end_test_chunk()]


def _hpm_probe_tests(test_data: TestData) -> list[str]:
    """For each hpmcounter n, check that hcounteren bit n is writable when mhpmcounter<n> is not read-only zero.

    The walk in cp_shcounterenw compares hcounteren with the reference model, whose implemented counters come from the
    configuration.  This probe finds the implemented counters on the hart itself: M-mode writes all ones to
    mhpmcounter<n> (both halves on RV32), whose event selector the boot clears, and reads it back.  A nonzero value means
    the counter is implemented, so HS-mode writes all ones to hcounteren and checks bit n.  A legal hart signs 0, and a
    stuck bit signs n.
    """
    ones, read, high, sig = test_data.int_regs.get_registers(4)
    cp = "cp_hpmcounter_hcounteren"
    lines = [
        comment_banner(
            cp,
            "For each n in 3-31, write all ones to mhpmcounter<n> in M-mode and read it back (OR both halves on RV32).\n"
            "If it is nonzero, write all ones to hcounteren in HS-mode and check that bit n reads 1",
        ),
        f"LI(x{ones}, -1)",
    ]
    for n in range(3, 32):
        lines.extend(
            [
                test_data.add_testcase(f"hpm{n}", cp, _SM_CG),
                f"csrw mhpmcounter{n}, x{ones}",
                f"csrr x{read}, mhpmcounter{n}",
                "#if __riscv_xlen == 32",
                f"csrw mhpmcounter{n}h, x{ones}",
                f"csrr x{high}, mhpmcounter{n}h",
                f"or x{read}, x{read}, x{high}",
                "#endif",
                f"LI(x{sig}, 0)",
                f"beqz x{read}, 1f  # read-only zero: hcounteren bit {n} may be read-only zero too",
                "RVTEST_TSBI_GOTO_SMODE",
                f"csrw hcounteren, x{ones}",
                f"csrr x{read}, hcounteren",
                f"srli x{read}, x{read}, {n}",
                f"andi x{read}, x{read}, 1",
                f"bnez x{read}, 2f",
                f"LI(x{sig}, {n})  # hcounteren bit {n} is stuck at 0",
                "2:",
                "csrw hcounteren, zero",
                "RVTEST_TSBI_GOTO_MMODE",
                "1:",
                f"csrw mhpmcounter{n}, zero",
                "#if __riscv_xlen == 32",
                f"csrw mhpmcounter{n}h, zero",
                "#endif",
                write_sigupd(sig, test_data),
            ]
        )
    lines.append(f"mv x{ones}, zero")
    test_data.int_regs.return_registers([ones, read, high, sig])
    return lines


@add_priv_test_generator(
    "Shcounterenw",
    required_extensions=["Sm", "H", "Shcounterenw"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_shcounterenw_sm(test_data: TestData) -> list[TestChunk]:
    """Generate the Sm group of Shcounterenw: probe the implemented hpmcounters from M-mode."""
    tc = test_data.begin_test_chunk("Sm")
    tc.code.extend(_hpm_probe_tests(test_data))
    return [test_data.end_test_chunk()]
