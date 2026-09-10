##################################
# Sstvecd.py
#
# Sstvecd extension test generator.
# Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com 22 April 2026
# SPDX-License-Identifier: Apache-2.0
##################################
from testgen.asm.csr import csr_walk_test
from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator


def _generate_stvec_mode_tests(test_data: TestData) -> list[str]:
    covergroup = "Sstvecd_cg"
    coverpoint = "cp_stvec_mode"

    lines = [
        comment_banner(
            coverpoint,
            "Write stvec with MODE=Direct (0) and walking 1s through BASE field.\n"
            "Runs in S-mode, which the suite boots into, so priv_mode_s is sampled in the cross.\n"
            "MODE bits[1:0] are kept 0 throughout to satisfy stvec_mode 'direct' bin.\n"
            "Walking 1s use csrs (csrrs) — csrrc/walking 0s not needed per CTP.\n"
            "stvec is cleared via csrw zero before each csrs so the OR result is\n"
            "exactly the walking-1 pattern.",
        ),
        "",
    ]

    # MODE bits [1:0] must stay 0; only walking 1s are needed per CTP.
    lines.extend(csr_walk_test(test_data, ("stvec", None), covergroup, coverpoint, start_bit=2, walk_zeros=False))

    return lines


@add_priv_test_generator(
    "Sstvecd",
    required_extensions=["S"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_sstvecd(test_data: TestData) -> list[TestChunk]:
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()
    tc.code.extend(_generate_stvec_mode_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
