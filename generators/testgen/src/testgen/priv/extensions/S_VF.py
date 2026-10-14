##################################
# priv/extensions/S_VF.py
#
# S_VF privileged test generator.
# Vector floating-point interactions with sstatus.FS state transitions.
# Part of the S suite: S_VF-NN.S in tests/priv/S, run only when Zve32f is also supported.
# David_Harris@hmc.edu 11 October 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""S_VF privileged test generator: vector-FP × sstatus.FS state."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.VFCommon import gen_vf_tests
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "S",
    required_extensions=["S", "Zve32f"],
    extra_defines=[
        "#define RVTEST_VECTOR",
        "#define RVTEST_SEW 0",
        "#define VDSEW 0",
        "#define BOOT_TO_SMODE",
    ],
)
def make_svf(test_data: TestData) -> list[TestChunk]:
    """Generate S_VF tests (vector-FP x sstatus.FS state)."""
    return gen_vf_tests(test_data, "S", "S_VF_cg")
