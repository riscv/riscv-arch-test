##################################
# priv/extensions/ZicfilpS.py
#
# ZicfilpS landing pad tests: run in S-mode, plus S-mode trap entry and SRET behavior.
# umer@riscv.org Sep 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZicfilpS privileged extension test generator for supervisor mode."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZicfilpCommon import (
    elp_state_preservation_tests,
    guarded_trap_entry_tests,
    make_zicfilp_tests,
    trap_entry_tests,
    trap_return_tests,
)
from testgen.priv.registry import add_priv_test_generator

covergroup = "ZicfilpS_cg"


@add_priv_test_generator(
    "ZicfilpS",
    required_extensions=["S", "Zicfilp"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_zicfilps(test_data: TestData) -> list[TestChunk]:
    """Generate Zicfilp landing pad tests in S-mode."""
    return [
        *make_zicfilp_tests(test_data, "S", covergroup),
        trap_entry_tests(test_data, "S", covergroup),
        guarded_trap_entry_tests(test_data, "S", covergroup),
        elp_state_preservation_tests(test_data, "S", covergroup),
        trap_return_tests(test_data, "S", covergroup),
    ]
