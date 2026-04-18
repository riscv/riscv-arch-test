##################################
# priv/extensions/Ssu64xl.py
#
# Zic64bzicboz privileged extension test generator.
# ammarahwakeel9@gmail.com UET (April 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

"""Zic64bZicboz extension test generator.
Zic64b : Cache blocks must be 64 bytes in size, naturally aligned.
Zicboz : Cache-Block Zero instruction (cbo.zero).
RVA23U64 profile: 64-bit only, user-mode execution environment.
"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator

_OFFSETS: list[int] = list(range(0, 61, 4)) + [64]
_SAMPLE_OFFSETS: list[int] = [0, 60, 64, 124]


def _generate_zic64b_tests(test_data: TestData) -> list[str]:
    """Generate cp_zic64bzicboz tests for Zic64bZicboz (U-mode only)."""

    covergroup = "Zic64bzicboz_cg"
    coverpoint = "cp_zic64bzicboz"

    base_reg, tmp_reg, val_reg, envcfg_reg = test_data.int_regs.get_registers(4, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "Zic64b + Zicboz (RVA23U64): 64-byte cache blocks.\n"
            "Test cbo.zero (U-mode) at offsets 0..60 & 64 on 128B all-1s buffer; verify via signature.",
        ),
        "",
        "#if __riscv_xlen == 64",
        "",
        "#ifdef ZICBOZ_SUPPORTED",
        "",
    ]

    lines.extend(
        [
            "RVTEST_GOTO_MMODE",
            "",
            f"LI(x{envcfg_reg}, 128)               # bit 7 = CBZE for both CSRs",
            f"csrw menvcfg, x{envcfg_reg}",
            f"csrw senvcfg, x{envcfg_reg}",
            "",
            f"LA(x{base_reg}, scratch)",
            f"LI(x{tmp_reg}, 63)",
            f"add  x{base_reg}, x{base_reg}, x{tmp_reg}",
            f"not  x{tmp_reg}, x{tmp_reg}",
            f"and  x{base_reg}, x{base_reg}, x{tmp_reg}    # base_reg now 64-byte aligned",
            "",
            "RVTEST_GOTO_LOWER_MODE Umode",
            "",
        ]
    )

    for offset in _OFFSETS:
        binname = f"offset_{offset}"

        lines.extend(
            [
                "RVTEST_GOTO_MMODE",
                f"csrw menvcfg, x{envcfg_reg}",
                f"csrw senvcfg, x{envcfg_reg}",
                "RVTEST_GOTO_LOWER_MODE Umode",
                "",
                f"LI(x{val_reg}, -1)",
            ]
        )

        for word_off in range(0, 128, 4):
            lines.append(f"sw   x{val_reg}, {word_off}(x{base_reg})")

        lines.extend(
            [
                "",
                f"# Step 2: rs1 = base + {offset}, execute cbo.zero",
                f"LI(x{tmp_reg}, {offset})",
                f"add  x{tmp_reg}, x{base_reg}, x{tmp_reg}   # tmp_reg = base + {offset}",
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

    lines.extend(
        [
            "RVTEST_GOTO_MMODE",
            "",
            "#endif  // ZICBOZ_SUPPORTED",
            "#endif  // __riscv_xlen == 64",
            "",
        ]
    )

    test_data.int_regs.return_registers([base_reg, tmp_reg, val_reg, envcfg_reg])
    return lines


@add_priv_test_generator(
    "Zic64bzicboz",
    required_extensions=["I", "Zicsr", "Zicboz", "Zic64b", "U"],
    march_extensions=["I", "Zicsr", "Zicboz"],
)
def make_zic64bzicboz(test_data: TestData) -> list[str]:
    """Generate tests for the Zic64bZicboz extension (RVA23U64 profile)."""
    lines: list[str] = []
    lines.extend(_generate_zic64b_tests(test_data))
    return lines
