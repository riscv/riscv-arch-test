##################################
# priv/extensions/Ziccif.py
#
# Ziccif main-memory instruction-fetch test generator.
# David_Harris@hmc.edu 22 October 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Ziccif extension test generator.

Main memory regions with the coherence and cacheability PMAs must support instruction fetch, and naturally aligned
fetches of up to min(ILEN, XLEN) bits are atomic. The test fetches and executes an uncompressed add and, with Zca, a
compressed c.add from main memory and records their results. Fetch atomicity is only observable when another hart
or agent modifies the code being fetched, so a single-hart test cannot check it.
"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

_CG = "Ziccif_cg"
_CP = "cp_ziccif_fetch"


def _generate_ziccif_tests(test_data: TestData) -> list[str]:
    rs1, rs2, rd = test_data.int_regs.get_registers(3)
    lines = [
        comment_banner(_CP, "Fetch and execute an uncompressed add and, with Zca, a compressed c.add from main memory"),
        f"LI(x{rs1}, 0x12345678)",
        f"LI(x{rs2}, 0x0F0F0F0F)",
        test_data.add_testcase("add", _CP, _CG),
        f"add x{rd}, x{rs1}, x{rs2}  # three different registers, so this cannot assemble as c.add",
        write_sigupd(rd, test_data),
        "#ifdef ZCA_SUPPORTED",
        f"mv x{rd}, x{rs1}",
        test_data.add_testcase("c_add", _CP, _CG),
        f"c.add x{rd}, x{rs2}",
        write_sigupd(rd, test_data),
        "#endif",
    ]
    test_data.int_regs.return_registers([rs1, rs2, rd])
    return lines


@add_priv_test_generator("Ziccif", required_extensions=["Ziccif"], march_extensions=["Zca"])
def make_ziccif(test_data: TestData) -> list[TestChunk]:
    """Generate tests for the Ziccif main-memory instruction-fetch extension."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()
    tc.code.extend(_generate_ziccif_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
