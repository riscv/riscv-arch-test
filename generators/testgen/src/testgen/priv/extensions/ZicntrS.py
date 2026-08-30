##################################
# ZicntrS.py
#
# ZicntrS privileged extension test generator.
# ellyu@g.hmc.edu March 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZicntrS extension test generator: counter access from S/U-mode"""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZicntrCommon import counter_inc_inaccessible_tests, counteren_walk_tests
from testgen.priv.registry import add_priv_test_generator

covergroup = "ZicntrS_cg"


@add_priv_test_generator(
    "ZicntrS",
    required_extensions=["S", "Zicntr"],
    march_extensions=["Zicntr", "Zihpm"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_zicntrs(test_data: TestData) -> list[TestChunk]:
    """Generate tests for ZicntrS coverpoints"""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()

    tc.code.extend(
        counteren_walk_tests(
            test_data,
            covergroup,
            "cp_mcounteren_access_s",
            "Write walking 1s and 0s to mcounteren via T-SBI.  Read from corresponding counter and counterh in S-mode",
            csrs=["mcounteren"],
            run_mode="S",
            read_mode="S",
        )
    )
    tc.code.extend(
        counteren_walk_tests(
            test_data,
            covergroup,
            "cp_scounteren_access_s",
            "Write walking 1s and 0s to scounteren with mcounteren = all 1s.  Read from corresponding counter and counterh in S-mode",
            csrs=["scounteren"],
            run_mode="S",
            read_mode="S",
            mcounteren_settings=("ones",),
        )
    )
    tc.code.extend(
        counteren_walk_tests(
            test_data,
            covergroup,
            "cp_scounteren_access_u",
            "Write walking 1s and 0s to scounteren with mcounteren = all 1s.  Read from corresponding counter and counterh in U-mode",
            csrs=["scounteren"],
            run_mode="S",
            read_mode="U",
            mcounteren_settings=("ones",),
        )
    )
    tc.code.extend(
        counteren_walk_tests(
            test_data,
            covergroup,
            "cp_mcounteren_access_u",
            "Write walking 1s and 0s to both mcounteren (via T-SBI) and scounteren (same value in each).  Read from corresponding counter and counterh in U-mode",
            csrs=["mcounteren", "scounteren"],
            run_mode="S",
            read_mode="U",
        )
    )
    tc.code.extend(counter_inc_inaccessible_tests(test_data, covergroup, "S"))
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
