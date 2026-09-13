##################################
# priv/extensions/ZawrsSm.py
#
# ZawrsSm privileged extension test generator.
# ellyu@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################


"""ZawrsSm privileged extension test generator for machine-mode."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZawrsCommon import (
    wrs_no_mie_helper,
    wrs_no_res_helper,
    wrs_resume_helper,
    wrs_timeout_helper,
)
from testgen.priv.registry import add_priv_test_generator

covergroup = "ZawrsSm_cg"


@add_priv_test_generator(
    "ZawrsSm",
    required_extensions=["Sm", "Zawrs", "Zalrsc"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_zawrssm(test_data: TestData) -> list[TestChunk]:
    """Generate tests for ZawrsSm WRS instructions at machine-mode."""

    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()
    tc.code.extend(wrs_no_res_helper(test_data, "M", covergroup))
    tc.code.extend(wrs_timeout_helper(test_data, "M", covergroup, timeout="short"))
    tc.code.extend(wrs_resume_helper(test_data, "M", covergroup))
    tc.code.extend(wrs_no_mie_helper(test_data, "M", covergroup))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
