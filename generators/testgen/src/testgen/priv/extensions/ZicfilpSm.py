##################################
# priv/extensions/ZicfilpSm.py
#
# ZicfilpSm landing pad tests: run in M-mode, plus M-mode trap entry and MRET behavior.
# umer@riscv.org Sep 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZicfilpSm privileged extension test generator for machine mode."""

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

covergroup = "ZicfilpSm_cg"


@add_priv_test_generator(
    "ZicfilpSm",
    required_extensions=["Sm", "Zicfilp"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_zicfilpsm(test_data: TestData) -> list[TestChunk]:
    """Generate Zicfilp landing pad tests in M-mode."""
    return [
        *make_zicfilp_tests(test_data, "M", covergroup),
        elp_state_preservation_tests(test_data, "M", covergroup),
        trap_entry_tests(test_data, "M", covergroup),
        guarded_trap_entry_tests(test_data, "M", covergroup),
        trap_return_tests(test_data, "M", covergroup),
    ]
