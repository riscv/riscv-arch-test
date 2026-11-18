##################################
# Sscounteren.py
# Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com 22 April 2026
# Scounteren supervisor counter-enable register test generator.
# SPDX-License-Identifier: Apache-2.0
##################################
from testgen.asm.csr import csr_access_test, csr_walk_test
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

_COVERGROUP = "Sscounterenw_cg"


def _generate_scounteren_tests(test_data: TestData) -> list[str]:
    """Generate tests for scounteren CSR."""
    coverpoint = "cp_scounteren_writable"
    lines = [
        comment_banner(
            coverpoint,
            "Set and clear each bit of the 32-bit scounteren CSR.",
        ),
        "",
    ]

    # scounteren is 32 bits. Readbacks stay full XLEN, so bits 63:32 must still be zero.
    lines.extend(csr_walk_test(test_data, ("scounteren", None), _COVERGROUP, coverpoint, end_bit=31))
    lines.extend(csr_access_test(test_data, ("scounteren", None), _COVERGROUP, coverpoint))
    return lines


def _generate_hpm_bit_tests(test_data: TestData) -> list[str]:
    """Require scounteren bit n to stick when mhpmcounter<n> is not read-only zero.

    The counter is probed in M-mode. The scounteren write and read run in S-mode, which is
    the mode that owns the register. A legal hart signs 0. A stuck bit signs n, so the
    signature failure names that counter even when the reference model treats it as
    read-only zero.
    """
    coverpoint = "cp_hpmcounter_scounteren"
    ones_reg, read_reg, bit_reg, sig_reg = test_data.int_regs.get_registers(4)
    lines = [
        comment_banner(
            coverpoint,
            "For each n in 3..31, write all ones to mhpmcounter<n> in M-mode and read it back.\n"
            "A read-only-zero counter does not constrain scounteren bit n. Otherwise, in S-mode,\n"
            "write all ones to scounteren and require bit n to read back 1.",
        ),
        "",
        "#ifdef ZIHPM_SUPPORTED",
    ]
    for n in range(3, 32):
        lines.extend(
            [
                test_data.add_testcase(f"hpm{n}", coverpoint, _COVERGROUP),
                "RVTEST_TSBI_GOTO_MMODE",
                f"LI(x{ones_reg}, -1)",
                f"csrw mhpmcounter{n}, x{ones_reg}",
                f"csrr x{read_reg}, mhpmcounter{n}",
                f"csrw mhpmcounter{n}, zero    # do not leave the counter at all ones",
                "RVTEST_TSBI_GOTO_SMODE",
                f"beqz x{read_reg}, 8f    # read-only zero: bit {n} is unconstrained",
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
                f"beq x{read_reg}, x{bit_reg}, 8f",
                f"LI(x{sig_reg}, {n})    # signature is the stuck counter index",
                "j 9f",
                "8:",
                f"LI(x{sig_reg}, 0)",
                "9:",
                write_sigupd(sig_reg, test_data),
            ]
        )
    lines.append("#endif // ZIHPM_SUPPORTED")
    test_data.int_regs.return_registers([ones_reg, read_reg, bit_reg, sig_reg])
    return lines


@add_priv_test_generator(
    "Sscounterenw",
    required_extensions=["Sscounterenw"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_scounterenw(test_data: TestData) -> list[TestChunk]:
    """Generate tests for Scounteren supervisor counter-enable register."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()
    tc.code.extend(_generate_scounteren_tests(test_data))
    tc.code.extend(_generate_hpm_bit_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
