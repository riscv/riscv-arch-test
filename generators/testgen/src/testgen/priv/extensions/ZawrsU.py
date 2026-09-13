##################################
# priv/extensions/ZawrsU.py
#
# ZawrsU privileged extension test generator.
# ellyu@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZawrsU privileged extension test generator for user-mode."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZawrsCommon import (
    wrs_no_mie_helper,
    wrs_no_res_helper,
    wrs_resume_helper,
    wrs_timeout_helper,
)
from testgen.priv.registry import add_priv_test_generator

covergroup = "ZawrsU_cg"


@add_priv_test_generator(
    "ZawrsU",
    required_extensions=["U", "Zawrs", "Zalrsc"],
)
def make_zawrsu(test_data: TestData) -> list[TestChunk]:
    """Generate tests for Zawrs WRS instructions at user-mode."""

    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()
    tc.code.extend(wrs_no_res_helper(test_data, "U", covergroup))
    tc.code.extend(wrs_timeout_helper(test_data, "U", covergroup, timeout="short"))
    tc.code.extend(wrs_timeout_helper(test_data, "U", covergroup, timeout="no"))
    tc.code.extend(wrs_no_mie_helper(test_data, "U", covergroup))
    tc.code.extend(wrs_resume_helper(test_data, "U", covergroup))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
