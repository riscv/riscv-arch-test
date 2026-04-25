##################################
# Sstvecd.py
#
# Sstvecd extension test generator.
# Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com 22 April 2026
# SPDX-License-Identifier: Apache-2.0
##################################
from testgen.asm.csr import gen_csr_read_sigupd
from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _generate_stvec_walk_tests(test_data: TestData, covergroup: str, coverpoint: str) -> list[str]:

    save_reg, temp_reg, walk_reg, check_reg = test_data.int_regs.get_registers(4)

    csr_name = "stvec"

    lines = [
        "",
        f"# CSR Walk Tests for {csr_name} with MODE=Direct (bits[1:0]=0) always",
        f"CSRR(x{save_reg}, {csr_name})          # Save CSR",
        f"LI(x{temp_reg}, -1)                    # x{temp_reg} = all 1s",
        f"andi x{temp_reg}, x{temp_reg}, -4      # clear bits[1:0]: MODE=0, all BASE bits set",
        f"LI(x{walk_reg}, 4)                     # start at bit 2 (skip MODE bits[1:0])",
    ]

    # Walking 1s: bits 2-31
    for i in range(2, 32):
        lines.extend(
            [
                "",
                f"CSRW({csr_name}, zero)              # clear all bits",
                f"CSRW({csr_name}, x{walk_reg})       # write walking 1 at bit {i}, MODE=0",
                test_data.add_testcase(f"{csr_name}_set_bit_{i}", coverpoint, covergroup),
                gen_csr_read_sigupd(check_reg, csr_name, test_data),
                f"slli x{walk_reg}, x{walk_reg}, 1   # walk the 1",
            ]
        )

    # Walking 1s: bits 32-63 (RV64 only)
    lines.append("\n#if __riscv_xlen == 64")
    for i in range(32, 64):
        lines.extend(
            [
                "",
                f"CSRW({csr_name}, zero)              # clear all bits",
                f"CSRW({csr_name}, x{walk_reg})       # write walking 1 at bit {i}, MODE=0",
                test_data.add_testcase(f"{csr_name}_set_bit_{i}", coverpoint, covergroup),
                gen_csr_read_sigupd(check_reg, csr_name, test_data),
                f"slli x{walk_reg}, x{walk_reg}, 1   # walk the 1",
            ]
        )
    lines.append("#endif\n")

    # Walking 0s: bits 2-31
    lines.append(f"LI(x{walk_reg}, 4)                 # reset walk_reg to bit 2 for walking 0s")
    for i in range(2, 32):
        lines.extend(
            [
                "",
                f"CSRW({csr_name}, x{temp_reg})       # set all BASE bits, MODE=0",
                f"CSRC({csr_name}, x{walk_reg})       # clear bit {i}, MODE stays 0",
                test_data.add_testcase(f"{csr_name}_clr_bit_{i}", coverpoint, covergroup),
                gen_csr_read_sigupd(check_reg, csr_name, test_data),
                f"slli x{walk_reg}, x{walk_reg}, 1   # walk the 1",
            ]
        )

    # Walking 0s: bits 32-63 (RV64 only)
    lines.append("\n#if __riscv_xlen == 64")
    for i in range(32, 64):
        lines.extend(
            [
                "",
                f"CSRW({csr_name}, x{temp_reg})       # set all BASE bits, MODE=0",
                f"CSRC({csr_name}, x{walk_reg})       # clear bit {i}, MODE stays 0",
                test_data.add_testcase(f"{csr_name}_clr_bit_{i}", coverpoint, covergroup),
                gen_csr_read_sigupd(check_reg, csr_name, test_data),
                f"slli x{walk_reg}, x{walk_reg}, 1   # walk the 1",
            ]
        )
    lines.append("#endif\n")

    lines.append(f"CSRW({csr_name}, x{save_reg})      # restore CSR")
    test_data.int_regs.return_registers([save_reg, temp_reg, walk_reg, check_reg])
    return lines


def _generate_stvec_mode_tests(test_data: TestData) -> list[str]:
    covergroup = "Sstvecd_cg"
    coverpoint = "cp_stvec_mode"

    lines = [
        comment_banner(
            coverpoint,
            "Write stvec with MODE=Direct (0) and walking 1s/0s through BASE field.\n"
            "Must execute in S-mode so that priv_mode_s is sampled in the cross.\n"
            "MODE bits[1:0] are kept 0 throughout to satisfy stvec_mode 'direct' bin.",
        ),
        "RVTEST_GOTO_LOWER_MODE Smode  # switch to S-mode before walking stvec",
        "",
    ]

    lines.extend(_generate_stvec_walk_tests(test_data, covergroup, coverpoint))

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
