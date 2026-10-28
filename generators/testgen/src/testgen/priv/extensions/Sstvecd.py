##################################
# Sstvecd.py
#
# Sstvecd extension test generator.
# Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com 22 April 2026
# SPDX-License-Identifier: Apache-2.0
#
# Sstvecd writes stvec as Shvstvecd writes vstvec: every valid virtual address as walking 1s and
# walking 0s with MODE = Direct, and two known-valid physical addresses, the current pc and an
# address in the scratch area (PrivCommon.addr_csr_tests).  The S suite writes stvec the same way.
##################################
"""Sstvecd extension test generator: stvec holds MODE = Direct with every valid 4-byte-aligned address."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.PrivCommon import addr_csr_tests
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "Sstvecd",
    required_extensions=["S", "Sstvecd"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_sstvecd(test_data: TestData) -> list[TestChunk]:
    """Generate tests for Sstvecd coverpoints, as Shvstvecd does for vstvec."""
    test_chunks: list[TestChunk] = []
    addr_csr_tests(test_data, test_chunks, {"stvec": (0b11, {})}, "Sstvecd_cg", "stvec_addr")
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
