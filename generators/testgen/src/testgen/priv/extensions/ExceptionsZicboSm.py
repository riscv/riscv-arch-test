##################################
# ExceptionsZicboSm.py
#
# ExceptionsZicboSm privileged extension test generator.
# aman.murad@10xengineers.ai August 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Zicbo extension exception test generator (machine-mode only)."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ExceptionsZicboCommon import emit_suite
from testgen.priv.registry import add_priv_test_generator

_CG = "ExceptionsZicboSm_cg"


@add_priv_test_generator(
    "ExceptionsZicboSm",
    required_extensions=["Sm", ["Zicbom", "Zicboz", "Zicbop"]],
    march_extensions=["Zicbom", "Zicboz", "Zicbop"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_exceptionszicbosm(test_data: TestData) -> list[TestChunk]:
    """Generate tests for ExceptionsZicboSm coverpoints."""
    return emit_suite(test_data, _CG, mode="Sm")
