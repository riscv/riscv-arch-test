##################################
# priv/extensions/Za64rs.py
#
# Za64rs privileged extension test generator.
# ammarahwakeel9@gmail.com UET (April 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

"""Za64rs extension test generator.
Reservation sets are contiguous, naturally aligned, and at most 64 bytes.
RVA23U64 profile requires LR/SC to execute in U-mode.
"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _generate_za64rs_tests(test_data: TestData) -> list[str]:
    covergroup = "Za64rs_cg"
    coverpoint_success = "cp_za64rs_success"
    coverpoint_fail = "cp_za64rs_fail"

    base_reg, src_reg, dest_reg, temp_reg = test_data.int_regs.get_registers(4, exclude_regs=[0, 5, 6, 7, 9])

    lines = [
        comment_banner(
            "cp_za64rs",
            "Za64rs: Reservation set size test",
        ),
        "#if __riscv_xlen == 64",
        "",
        f"LA(x{base_reg}, scratch)",
        f"LI(x{temp_reg}, 127)",
        f"add x{base_reg}, x{base_reg}, x{temp_reg}",
        f"not x{temp_reg}, x{temp_reg}",
        f"and x{base_reg}, x{base_reg}, x{temp_reg}",
        "",
        f"LI(x{src_reg}, 0xA5A5A5A5)",
        "",
    ]

    for offset in range(0, 64, 4):
        binname = f"offset_{offset}"
        lines.extend(
            [
                f"# Testcase: offset={offset} — expect sc_success (within reservation set)",
                "RVTEST_GOTO_LOWER_MODE Umode",
                test_data.add_testcase(binname, coverpoint_success, covergroup),
                f"addi x{temp_reg}, x{base_reg}, {offset}",
                f"lr.w x{dest_reg}, (x{base_reg})",
                f"sc.w x{dest_reg}, x{src_reg}, (x{temp_reg})",
                "RVTEST_GOTO_MMODE",
                write_sigupd(dest_reg, test_data),
                "",
            ]
        )

    lines.extend(
        [
            "# Testcase: offset=64 — expect sc_fail (outside reservation set)",
            "RVTEST_GOTO_LOWER_MODE Umode",
            test_data.add_testcase("offset_64", coverpoint_fail, covergroup),
            f"addi x{temp_reg}, x{base_reg}, 64",
            f"lr.w x{dest_reg}, (x{base_reg})",
            f"sc.w x{dest_reg}, x{src_reg}, (x{temp_reg})",
            "RVTEST_GOTO_MMODE",
            write_sigupd(dest_reg, test_data),
            "",
        ]
    )

    lines.append("#endif")

    test_data.int_regs.return_registers([base_reg, src_reg, dest_reg, temp_reg])
    return lines


@add_priv_test_generator(
    "Za64rs",
    required_extensions=["Sm", "U", "I", "Zalrsc", "Za64rs", "Zicsr"],
    march_extensions=["I", "Zalrsc", "Zicsr"],
)
def make_za64rs(test_data: TestData) -> list[str]:
    """Generate tests for Za64rs reservation-set size extension."""
    lines: list[str] = []
    lines.extend(_generate_za64rs_tests(test_data))
    return lines
