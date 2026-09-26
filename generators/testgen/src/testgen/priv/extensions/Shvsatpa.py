##################################
# Shvsatpa.py
#
# Shvsatpa extension test generator: vsatp supports every MODE that satp supports.
# David_Harris@hmc.edu 24 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shvsatpa extension test generator: vsatp supports every MODE that satp supports."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.HCommon import atp_mode_test
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "Shvsatpa",
    required_extensions=["H", "Shvsatpa"],
    extra_defines=["#define BOOT_TO_SMODE"],
    # VS and VU traps need the visible trap handler
    params=["TIME_CSR_IMPLEMENTED: true"],
)
def make_shvsatpa(test_data: TestData) -> list[TestChunk]:
    """Generate tests for Shvsatpa coverpoints."""
    tc = test_data.begin_test_chunk()
    tc.code.extend(atp_mode_test(test_data, "vsatp", "Shvsatpa_cg", "cp_shvsatpa"))
    return [test_data.end_test_chunk()]
