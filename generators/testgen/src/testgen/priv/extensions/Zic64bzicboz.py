##################################
# priv/extensions/Zic64bzicboz.py
#
# Zic64bzicboz privileged extension test generator.
# Ammarah Wakeel  email:ammarahwakeel9@gmail.com (UET, April 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

"""Zic64bZicboz extension test generator.
Zic64b : Cache blocks must be 64 bytes in size, naturally aligned.
Zicboz : Cache-Block Zero instruction (cbo.zero).
"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator

_OFFSETS: list[int] = list(range(0, 65, 4))
_SAMPLE_OFFSETS: list[int] = [0, 60, 64, 124]


def _generate_zic64b_tests(test_data: TestData) -> list[str]:
    """Generate cp_zic64bzicboz tests for Zic64bZicboz."""

    covergroup = "Zic64bzicboz_cg"
    coverpoint = "cp_zi64cb"

    base_reg, tmp_reg, val_reg = test_data.int_regs.get_registers(3)

    lines = [
        comment_banner(
            f"{coverpoint}",
            "Zic64b + Zicboz: 64-byte cache blocks.\n"
            "Test cbo.zero at offsets 0..64 on 128B all-1s buffer; verify via signature.",
        ),
        "",
        f"LA(x{base_reg}, scratch)",
        "",
    ]

    for offset in _OFFSETS:
        binname = f"offset_{offset}"

        lines.append(f"LI(x{val_reg}, -1)")

        for word_off in range(0, 128, 4):
            lines.append(f"sw   x{val_reg}, {word_off}(x{base_reg})")

        lines.extend(
            [
                "",
                f"# rs1 = base + {offset}, execute cbo.zero",
                f"addi x{tmp_reg}, x{base_reg}, {offset}",
                test_data.add_testcase(binname, coverpoint, covergroup),
                f"cbo.zero  0(x{tmp_reg})",
                "",
            ]
        )

        for sample_off in _SAMPLE_OFFSETS:
            lines.extend(
                [
                    f"lw   x{val_reg}, {sample_off}(x{base_reg})",
                    write_sigupd(val_reg, test_data),
                ]
            )

        lines.append("")

    test_data.int_regs.return_registers([base_reg, tmp_reg, val_reg])
    return lines


@add_priv_test_generator(
    "Zic64bzicboz",
    required_extensions=["Zicboz", "Zic64b"],
)
def make_zic64bzicboz(test_data: TestData) -> list[str]:
    """Generate tests for the Zic64bZicboz extension."""
    lines: list[str] = []
    lines.extend(_generate_zic64b_tests(test_data))
    return lines
