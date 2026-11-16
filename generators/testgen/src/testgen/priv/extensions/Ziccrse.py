##################################
# priv/extensions/Ziccrse.py
#
# Ziccrse main-memory reservability test generator.
# David_Harris@hmc.edu 22 October 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Ziccrse extension test generator.

Main memory regions with the coherence and cacheability PMAs must support the RsrvEventual PMA: LR/SC is supported
and a constrained LR/SC loop eventually succeeds. The test runs one lr.w/sc.w pair on scratch in a constrained loop
that retries until the sc.w succeeds or the retry limit is reached, as the Zalrsc suite does, and records the sc.w
result, the value lr.w loaded and the value now in memory. Eventual success in the presence of other harts or agents
cannot be checked with a single hart.
"""

from testgen.asm.helpers import comment_banner, lrsc_retry_loop, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

_CG = "Ziccrse_cg"
_CP = "cp_ziccrse"


def _generate_ziccrse_tests(test_data: TestData) -> list[str]:
    base, src, sc_rd, loaded, retry = test_data.int_regs.get_registers(5)
    lines = [
        comment_banner(_CP, "lr.w and sc.w on scratch in a constrained loop until the sc.w succeeds"),
        f"LA(x{base}, scratch)",
        f"LI(x{loaded}, 0x13572468)",
        f"sw x{loaded}, 0(x{base})  # value for lr.w to load",
        f"LI(x{src}, 0x5A5A0F0F)  # value for sc.w to store",
    ]
    label = test_data.add_testcase("lr_w_sc_w", _CP, _CG)
    retry_start, retry_end = lrsc_retry_loop(test_data.current_testcase_label, retry, sc_rd)
    lines.extend(
        [
            *retry_start,
            f"lr.w x{loaded}, (x{base})",
            label,
            f"sc.w x{sc_rd}, x{src}, (x{base})",
            *retry_end,
            write_sigupd(sc_rd, test_data),
            write_sigupd(loaded, test_data),
            f"lw x{loaded}, 0(x{base})  # the value sc.w stored",
            write_sigupd(loaded, test_data),
        ]
    )
    test_data.int_regs.return_registers([base, src, sc_rd, loaded, retry])
    return lines


@add_priv_test_generator("Ziccrse", required_extensions=["Ziccrse", "Zalrsc"])
def make_ziccrse(test_data: TestData) -> list[TestChunk]:
    """Generate tests for the Ziccrse main-memory reservability extension."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()
    tc.code.extend(_generate_ziccrse_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
