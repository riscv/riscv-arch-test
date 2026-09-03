##################################
# priv/extensions/ZawrsS.py
#
# ZawrsS privileged extension test generator.
# ellyu@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZawrsS privileged extension test generator for S-mode (and H extension if supported)."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZawrsCommon import (
    wrs_no_mie_helper,
    wrs_no_res_helper,
    wrs_resume_helper,
    wrs_timeout_helper,
)
from testgen.priv.registry import add_priv_test_generator

covergroup = "ZawrsS_cg"


@add_priv_test_generator(
    "ZawrsS",
    required_extensions=["S", "Zawrs", "Zalrsc"],
    march_extensions=["H", "Zawrs", "Zalrsc"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_zawrss(test_data: TestData) -> list[TestChunk]:
    """Generate tests for ZawrsS WRS instructions at S-mode (and H if supported)."""

    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()
    tc.code.extend(wrs_no_res_helper(test_data, "S", covergroup))
    tc.code.extend(wrs_timeout_helper(test_data, "S", covergroup, timeout="short"))
    tc.code.extend(wrs_timeout_helper(test_data, "S", covergroup, timeout="no"))
    tc.code.extend(wrs_timeout_helper(test_data, "S", covergroup, timeout="no", virtualized=True))
    tc.code.extend(wrs_no_mie_helper(test_data, "S", covergroup))
    tc.code.extend(wrs_resume_helper(test_data, "S", covergroup))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
