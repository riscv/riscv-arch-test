##################################
# SscounterenwSm.py
# Machine-mode probe for Sscounterenw: an implemented hpmcounter has a writable
# scounteren bit. RVA23 certification does not run Sm suites.
# SPDX-License-Identifier: Apache-2.0
##################################
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

_COVERGROUP = "SscounterenwSm_cg"


def _generate_hpm_bit_tests(test_data: TestData) -> list[str]:
    """Require scounteren bit n to stick when hpmcounter<n> is not read-only zero.

    The suite boots in M-mode. On RV32 the test ORs mhpmcounter<n> with mhpmcounter<n>h.
    A nonzero read enters S-mode for the scounteren check and then returns to M-mode.
    Both halves are cleared only after that check. A legal hart signs 0. A stuck bit signs n.
    """
    coverpoint = "cp_hpmcounter_scounteren"
    ones_reg, read_reg, bit_reg, sig_reg = test_data.int_regs.get_registers(4)
    lines = [
        comment_banner(
            coverpoint,
            "For each n in 3..31, write all ones to mhpmcounter<n> and read it back.\n"
            "On RV32 do the same for mhpmcounter<n>h and OR the two reads.\n"
            "A read-only-zero counter does not constrain scounteren bit n. Otherwise enter\n"
            "S-mode, write all ones to scounteren, and require bit n to read back 1.",
        ),
        "",
        "#ifdef ZIHPM_SUPPORTED",
    ]
    for n in range(3, 32):
        lines.extend(
            [
                test_data.add_testcase(f"hpm{n}", coverpoint, _COVERGROUP),
                f"LI(x{ones_reg}, -1)",
                f"csrw mhpmcounter{n}, x{ones_reg}",
                f"csrr x{read_reg}, mhpmcounter{n}",
                "#if __riscv_xlen == 32",
                f"csrw mhpmcounter{n}h, x{ones_reg}",
                f"csrr x{bit_reg}, mhpmcounter{n}h",
                f"or x{read_reg}, x{read_reg}, x{bit_reg}",
                "#endif",
                f"beqz x{read_reg}, 8f    # read-only zero: bit {n} is unconstrained",
                "RVTEST_TSBI_GOTO_SMODE",
                f"csrw scounteren, x{ones_reg}",
                f"csrr x{read_reg}, scounteren",
                # Shift, so bit 31 is not a sign-extended LI constant on RV64.
                # norvc keeps the slli/and pair visible to cp_hpmcounter_scounteren.
                ".option push",
                ".option norvc",
                f"LI(x{bit_reg}, 1)",
                f"slli x{bit_reg}, x{bit_reg}, {n}",
                f"and x{read_reg}, x{read_reg}, x{bit_reg}",
                ".option pop",
                f"beq x{read_reg}, x{bit_reg}, 9f",
                f"LI(x{sig_reg}, {n})    # signature is the stuck counter index",
                "j 2f",
                "9:",
                f"LI(x{sig_reg}, 0)",
                "2:",
                "RVTEST_TSBI_GOTO_MMODE",
                "j 3f",
                "8:",
                f"LI(x{sig_reg}, 0)",
                "3:",
                # Clear after the S-mode check. Coverage reads the counter while it is still nonzero.
                f"csrw mhpmcounter{n}, zero",
                "#if __riscv_xlen == 32",
                f"csrw mhpmcounter{n}h, zero",
                "#endif",
                write_sigupd(sig_reg, test_data),
            ]
        )
    lines.append("#endif // ZIHPM_SUPPORTED")
    test_data.int_regs.return_registers([ones_reg, read_reg, bit_reg, sig_reg])
    return lines


@add_priv_test_generator(
    "SscounterenwSm",
    required_extensions=["Sm", "Sscounterenw"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_scounterenw_sm(test_data: TestData) -> list[TestChunk]:
    """Probe implemented hpmcounters from M-mode and check scounteren in S-mode."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()
    tc.code.extend(_generate_hpm_bit_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
