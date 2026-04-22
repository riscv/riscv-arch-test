from testgen.asm.csr import csr_walk_test
from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _generate_stvec_mode_tests(test_data: TestData) -> list[str]:
    ######################################
    covergroup = "Sstvecd_cg"
    coverpoint = "cp_stvec_mode"
    ######################################

    lines = [
        comment_banner(
            coverpoint,
            "Write stvec with MODE=Direct (0) and walking 1s/0s through BASE field.\n"
            "Must execute in S-mode so that priv_mode_s is sampled in the cross.",
        ),
        "RVTEST_GOTO_LOWER_MODE Smode  # switch to S-mode before walking stvec",
        "",
    ]

    lines.extend(csr_walk_test(test_data, "stvec", covergroup, coverpoint))

    lines.extend(
        [
            "",
            "RVTEST_GOTO_MMODE       # return to M-mode after test",
        ]
    )

    return lines


@add_priv_test_generator("Sstvecd", required_extensions=["S", "Zicsr"])
def make_sstvecd(test_data: TestData) -> list[str]:
    lines: list[str] = []
    lines.extend(_generate_stvec_mode_tests(test_data))
    return lines
