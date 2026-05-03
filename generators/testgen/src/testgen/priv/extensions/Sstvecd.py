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
        "# Only walking 1s are needed — csrrc/walking 0s are not required per CTP.",
        f"CSRR(x{save_reg}, {csr_name})          # Save CSR",
        f"LI(x{walk_reg}, 4)                     # start at bit 2 (skip MODE bits[1:0])",
    ]

    # Walking 1s: bits 2-31
    # Use CSRS (= CSRRS) so the cross coverpoint csrop 'csrrs' bin is hit.
    # Pre-clear stvec with CSRW zero so the OR result is exactly the walking-1 value.
    for i in range(2, 32):
        lines.extend(
            [
                "",
                f"CSRW({csr_name}, zero)              # clear all bits (CSRRW, not sampled by csrop)",
                f"CSRS({csr_name}, x{walk_reg})       # SET bit {i} via CSRRS, MODE=0",
                test_data.add_testcase(f"{csr_name}_set_bit_{i}", coverpoint, covergroup),
                gen_csr_read_sigupd(check_reg, (csr_name, None), test_data),
                f"slli x{walk_reg}, x{walk_reg}, 1   # walk the 1",
            ]
        )

    # Walking 1s: bits 32-63 (RV64 only)
    lines.append("\n#if __riscv_xlen == 64")
    for i in range(32, 64):
        lines.extend(
            [
                "",
                f"CSRW({csr_name}, zero)              # clear all bits (CSRRW, not sampled by csrop)",
                f"CSRS({csr_name}, x{walk_reg})       # SET bit {i} via CSRRS, MODE=0",
                test_data.add_testcase(f"{csr_name}_set_bit_{i}", coverpoint, covergroup),
                gen_csr_read_sigupd(check_reg, (csr_name, None), test_data),
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
