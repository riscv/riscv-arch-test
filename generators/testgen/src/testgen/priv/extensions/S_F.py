##################################
# priv/extensions/S_F.py
#
# S_F floating-point from supervisor mode privileged extension test generator.
# Part of the S suite: S_F-NN.S in tests/priv/S, run only when F is also supported.
# David_Harris@hmc.edu 11 October 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""S_F test generator: floating-point CSRs and sstatus.FS in S-mode, part of the S suite."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.FCommon import gen_fcsr_tests
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "S",
    required_extensions=["S", "F"],
    march_extensions=["F", "D", "Zfa"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_sf(test_data: TestData) -> list[TestChunk]:
    """Generate tests for S_F supervisor-mode floating-point testsuite."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk("F")

    tc.code.extend(gen_fcsr_tests(test_data, "S", "S_F_cg"))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
