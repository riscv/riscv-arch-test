##################################
# priv/extensions/Za64rs.py
#
# Za64rs privileged extension test generator.
# Written:  Ammarah Wakeel  email:ammarahwakeel9@gmail.com (UET, April 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

"""Za64rs extension test generator.
Reservation sets are contiguous, naturally aligned, and at most 64 bytes.
"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _generate_za64rs_tests(test_data: TestData) -> list[str]:
    covergroup = "Za64rs_cg"
    coverpoint = "cp_za64rs"

    base_reg, src_reg, dest_reg, temp_reg = test_data.int_regs.get_registers(4)

    lines = [
        comment_banner(
            f"{coverpoint}",
            "Za64rs: Reservation set size test",
        ),
        "",
        f"LA(x{base_reg}, scratch)",
        f"LI(x{src_reg}, 0xA5A5A5A5)",
        "",
    ]

    for offset in range(0, 65, 4):
        binname = f"offset_{offset}"
        lines.extend(
            [
                f"# Za64rs: sc.w at offset={offset} within reservation set",
                f"addi x{temp_reg}, x{base_reg}, {offset}",
                f"lr.w x{dest_reg}, (x{base_reg})",
                test_data.add_testcase(binname, coverpoint, covergroup),
                f"sc.w x{dest_reg}, x{src_reg}, (x{temp_reg})",
                write_sigupd(dest_reg, test_data),
                "",
            ]
        )

    test_data.int_regs.return_registers([base_reg, src_reg, dest_reg, temp_reg])
    return lines


@add_priv_test_generator(
    "Za64rs",
    required_extensions=["Zalrsc", "Za64rs"],
)
def make_za64rs(test_data: TestData) -> list[str]:
    """Generate tests for Za64rs reservation-set size extension."""
    lines: list[str] = []
    lines.extend(_generate_za64rs_tests(test_data))
    return lines
