##################################
# Shgatpa.py
#
# Shgatpa extension test generator: hgatp supports Bare and SvNNx4 for each SvNN in satp.
# David_Harris@hmc.edu 24 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shgatpa extension test generator: hgatp supports Bare and SvNNx4 for each SvNN in satp."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.HCommon import atp_mode_test
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "Shgatpa",
    required_extensions=["H", "Shgatpa"],
    extra_defines=["#define BOOT_TO_SMODE"],
    # VS and VU traps need the visible trap handler
    params=["TIME_CSR_IMPLEMENTED: true"],
)
def make_shgatpa(test_data: TestData) -> list[TestChunk]:
    """Generate tests for Shgatpa coverpoints."""
    tc = test_data.begin_test_chunk()
    tc.code.extend(atp_mode_test(test_data, "hgatp", "Shgatpa_cg", "cp_shgatpa"))
    return [test_data.end_test_chunk()]
