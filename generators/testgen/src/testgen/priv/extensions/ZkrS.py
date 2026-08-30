##################################
# priv/extensions/ZkrS.py
#
# ZkrS privileged test generator: the Zkr seed CSR tests in S-mode.
# Split from Zkr.py (jgong@hmc.edu Apr 2026) into per-mode suites.
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZkrS extension test generator: Zkr seed CSR coverpoints run in S-mode."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZkrCommon import (
    gen_seed_csrrw_tests,
    gen_seed_entropy_zero_non_es16_tests,
    gen_seed_illegal_csr_op_tests,
)
from testgen.priv.registry import add_priv_test_generator

_CG = "ZkrS_cg"


@add_priv_test_generator(
    "ZkrS",
    required_extensions=["Zkr", "S"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_zkrs(test_data: TestData) -> list[TestChunk]:
    """Generate the Zkr seed tests in S-mode."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()

    tc.code.extend(gen_seed_csrrw_tests(test_data, _CG, "S"))
    tc.code.extend(gen_seed_illegal_csr_op_tests(test_data, _CG, "S"))
    tc.code.extend(gen_seed_entropy_zero_non_es16_tests(test_data, _CG, "S"))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
