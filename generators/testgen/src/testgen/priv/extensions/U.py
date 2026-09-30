##################################
# U.py
#
# U user mode privileged extension test generator.
# David_Harris@hmc.edu 1 March 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""U privileged extension test generator."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.PrivCommon import csr_insufficient_priv_tests, csr_ro_write_tests, priv_inst_trap_tests
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "U",
    required_extensions=["U"],
)
def make_u(test_data: TestData) -> list[TestChunk]:
    """Generate tests for U user-mode testsuite."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()

    tc.code.extend(
        priv_inst_trap_tests(
            test_data,
            "U_uprivinst_cg",
            "cp_uprivinst",
            "Execute privileged instructions",
            ["ebreak", "mret", "sret"],
        )
    )
    csr_insufficient_priv_tests(
        test_data,
        test_chunks,
        "U_ucsr_cg",
        [range(0x100, 0x400), range(0x500, 0x800), range(0x900, 0xC00), range(0xD00, 0x1000)],
        "ucsr",
        "Attempt to read non-user-mode registers.  Should throw illegal instruction",
    )
    csr_ro_write_tests(test_data, test_chunks, "U_ucsr_cg", [range(0xC00, 0xD00)], "ucsr_ro")

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
