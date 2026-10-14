##################################
# priv/extensions/S_V.py
#
# S_V privileged test generator.
# Vector CSR access, vsetvl* behavior, vill, vstart, sstatus.VS.
# Part of the S suite: S_V_*-NN.S in tests/priv/S, run only when Zve32x is also supported.
# David_Harris@hmc.edu 11 October 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""S_V privileged test generator: vector CSRs and vtype/vl/vstart behavior in S-mode."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.VCommon import gen_v_tests
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "S",
    required_extensions=["S", "Zve32x"],
    extra_defines=[
        "#define RVTEST_VECTOR",
        "#define RVTEST_SEW 0",
        "#define VDSEW 0",
        "#define BOOT_TO_SMODE",
    ],
)
def make_sv(test_data: TestData) -> list[TestChunk]:
    """Generate S_V tests (vector CSRs, vsetvl* behavior, vill, vstart, sstatus.VS)."""
    return gen_v_tests(test_data, "S", "S_V_cg")
