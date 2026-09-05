##################################
# ZicntrU.py
#
# ZicntrU privileged extension test generator.
# ellyu@g.hmc.edu March 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZicntrU extension test generator: counter access from U-mode, with mcounteren written via T-SBI."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZicntrCommon import counter_inc_inaccessible_tests, counteren_walk_tests
from testgen.priv.registry import add_priv_test_generator

covergroup = "ZicntrU_cg"


@add_priv_test_generator(
    "ZicntrU",
    required_extensions=["U", "Zicntr"],
    march_extensions=["Zicntr", "Zihpm"],
)
def make_zicntru(test_data: TestData) -> list[TestChunk]:
    """Generate tests for ZicntrU coverpoints"""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()
    tc.code.extend(
        counteren_walk_tests(
            test_data,
            covergroup,
            "cp_mcounteren_access_u",
            "Write walking 1s and 0s to mcounteren via T-SBI.  Read from corresponding counter and counterh in U-mode",
            csrs=["mcounteren"],
            run_mode="U",
            read_mode="U",
        )
    )
    tc.code.extend(counter_inc_inaccessible_tests(test_data, covergroup, "U"))
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
