##################################
# priv/extensions/ZicfilpU.py
#
# ZicfilpU landing pad tests: run in U-mode, using T-SBI calls for senvcfg/menvcfg.
# umer@riscv.org Sep 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZicfilpU privileged extension test generator for user mode."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZicfilpCommon import make_zicfilp_tests
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "ZicfilpU",
    required_extensions=["U", "Zicfilp"],
)
def make_zicfilpu(test_data: TestData) -> list[TestChunk]:
    """Generate Zicfilp landing pad tests in U-mode."""
    return make_zicfilp_tests(test_data, "U", "ZicfilpU_cg")
