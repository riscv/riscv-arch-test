##################################
# ExceptionsZicboU.py
#
# ExceptionsZicboU privileged extension test generator.
# ellyu@g.hmc.edu March 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Zicbo extension exception test generator."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.exceptions.ExceptionsZicboCommon import emit_suite
from testgen.priv.registry import add_priv_test_generator

_CG = "Exceptions_ZicboU_cg"


@add_priv_test_generator(
    "Exceptions",
    required_extensions=["U", ["Zicbom", "Zicboz", "Zicbop"]],
    march_extensions=["Zicbom", "Zicboz", "Zicbop"],
)
def make_exceptionszicbou(test_data: TestData) -> list[TestChunk]:
    """Generate tests for ExceptionsZicboU coverpoints."""
    return emit_suite(test_data, _CG, "U", "ZicboU")
