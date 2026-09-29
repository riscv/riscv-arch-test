##################################
# Shvstvecd.py
#
# Shvstvecd extension test generator: vstvec holds MODE = Direct with 4-byte-aligned BASE values.
# David_Harris@hmc.edu 24 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shvstvecd extension test generator: vstvec holds MODE = Direct with every valid 4-byte-aligned address."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.PrivCommon import addr_csr_tests
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "Shvstvecd",
    required_extensions=["H", "Shvstvecd"],
    extra_defines=["#define BOOT_TO_SMODE"],
    # VS and VU traps need the visible trap handler
    params=["TIME_CSR_IMPLEMENTED: true"],
)
def make_shvstvecd(test_data: TestData) -> list[TestChunk]:
    """Generate tests for Shvstvecd coverpoints."""
    test_chunks: list[TestChunk] = []
    addr_csr_tests(test_data, test_chunks, {"vstvec": (0b11, {})}, "Shvstvecd_cg", "vstvec_addr")
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
