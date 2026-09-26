##################################
# ZicntrHSm.py
#
# ZicntrHSm privileged extension test generator: counter reads and htimedelta observed from M-mode.
# David_Harris@hmc.edu 24 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZicntrHSm extension test generator: M-mode counter reads under walking mcounteren, hcounteren and scounteren."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZicntrCommon import counteren_walk_tests, htimedelta_tests
from testgen.priv.registry import add_priv_test_generator

_CG = "ZicntrHSm_cg"


@add_priv_test_generator(
    "ZicntrHSm",
    required_extensions=["Sm", "H", "Zicntr"],
    extra_defines=["#define BOOT_TO_MMODE"],
    # VS and VU traps need the visible trap handler
    params=["TIME_CSR_IMPLEMENTED: true"],
)
def make_zicntrhsm(test_data: TestData) -> list[TestChunk]:
    """Generate tests for ZicntrHSm coverpoints."""
    test_chunks: list[TestChunk] = []
    tc = test_data.new_test_chunk(test_chunks)
    tc.code.extend(
        counteren_walk_tests(
            test_data,
            _CG,
            "cp_mhscounteren_access_m",
            "Write walking 1s and 0s to mcounteren, hcounteren and scounteren (same value in each).\n"
            "Read from corresponding counter and counterh in M-mode",
            csrs=["mcounteren", "hcounteren", "scounteren"],
            mode="M",
        )
    )
    tc = test_data.new_test_chunk(test_chunks)
    tc.code.extend(htimedelta_tests(test_data, _CG, "M"))
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
