##################################
# Sscounteren.py
# Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com 22 April 2026
# Scounteren supervisor counter-enable register test generator.
# SPDX-License-Identifier: Apache-2.0
##################################
from testgen.asm.csr import csr_access_test, csr_walk_test
from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

_COVERGROUP = "Sscounterenw_cg"


def _generate_scounteren_tests(test_data: TestData) -> list[str]:
    """Generate tests for scounteren CSR."""
    coverpoint = "cp_scounteren_writable"
    lines = [
        comment_banner(
            coverpoint,
            "Set and clear each bit of the 32-bit scounteren CSR.",
        ),
        "",
    ]

    # scounteren is 32 bits. Readbacks stay full XLEN, so bits 63:32 must still be zero.
    lines.extend(csr_walk_test(test_data, ("scounteren", None), _COVERGROUP, coverpoint, end_bit=31))
    lines.extend(csr_access_test(test_data, ("scounteren", None), _COVERGROUP, coverpoint))
    return lines


@add_priv_test_generator(
    "Sscounterenw",
    required_extensions=["Sscounterenw"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_scounterenw(test_data: TestData) -> list[TestChunk]:
    """Generate the S-mode scounteren walk. The hpmcounter probe is SscounterenwSm."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()
    tc.code.extend(_generate_scounteren_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
