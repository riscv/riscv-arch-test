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
from testgen.priv.registry import add_priv_test_generator


def _generate_stvec_mode_tests(test_data: TestData) -> list[str]:
    covergroup = "Sstvecd_cg"
    coverpoint = "cp_stvec_mode"

    lines = [
        comment_banner(
            coverpoint,
            "Write stvec with MODE=Direct (0) and walking 1s through BASE field.\n"
            "Must execute in S-mode so that priv_mode_s is sampled in the cross.\n"
            "MODE bits[1:0] are kept 0 throughout to satisfy stvec_mode 'direct' bin.\n"
            "Walking 1s use CSRS (CSRRS) — csrrc/walking 0s not needed per CTP.\n"
            "stvec is cleared via CSRW zero before each CSRS so the OR result is\n"
            "exactly the walking-1 pattern.",
        ),
        "RVTEST_GOTO_LOWER_MODE Smode  # switch to S-mode before walking stvec",
        "",
    ]

    # MODE bits [1:0] must stay 0; only walking 1s are needed per CTP.
    lines.extend(csr_walk_test(test_data, ("stvec", None), covergroup, coverpoint, start_bit=2, walk_zeros=False))

    lines.extend(
        [
            "",
            "RVTEST_GOTO_MMODE       # return to M-mode after test",
        ]
    )

    return lines


@add_priv_test_generator("Sstvecd", required_extensions=["S"])
def make_sstvecd(test_data: TestData) -> list[str]:
    lines: list[str] = []
    lines.extend(_generate_stvec_mode_tests(test_data))
    return lines
