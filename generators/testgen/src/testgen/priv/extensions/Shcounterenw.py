##################################
# Shcounterenw.py
#
# Shcounterenw extension test generator: hcounteren bits are writable for implemented hpmcounters.
# David_Harris@hmc.edu 24 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shcounterenw extension test generator: hcounteren bits are writable for implemented hpmcounters."""

from testgen.asm.csr import csr_access_test, csr_walk_test
from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

_CG = "Shcounterenw_cg"
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
