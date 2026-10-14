##################################
# priv/extensions/U_VF.py
#
# U_VF privileged test generator.
# Vector floating-point interactions with xstatus.FS state transitions, with the status CSR reached through T-SBI.
# Part of the U suite: U_VF-NN.S in tests/priv/U, run only when Zve32f is also supported.
# David_Harris@hmc.edu 11 October 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""U_VF privileged test generator: vector-FP × mstatus.FS state in U-mode."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.VFCommon import gen_vf_tests
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "U",
    required_extensions=["U", "Zve32f"],
    extra_defines=[
        "#define RVTEST_VECTOR",
        "#define RVTEST_SEW 0",
        "#define VDSEW 0",
    ],
)
def make_u_vf(test_data: TestData) -> list[TestChunk]:
    """Generate U_VF tests (vector-FP x mstatus.FS state from U-mode)."""
    return gen_vf_tests(test_data, "U", "U_VF_cg")
