##################################
# ZicsrF.py
#
# Unprivileged floating-point fcsr tests
# David_Harris@hmc.edu 19 Feb 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Unprivileged floating-point fcsr tests generator."""

from typing import Literal

from testgen.asm.csr import csr_access_test, csr_walk_test, gen_csr_read_sigupd, gen_csr_write_sigupd
from testgen.asm.helpers import comment_banner, load_float_reg, write_sigupd
from testgen.constants import INDENT
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator


def _generate_fcsr_access(test_data: TestData) -> list[str]:
    """All types of accesses to all fcsrs."""
    ######################################
    covergroup = "ZicsrF_cg"
    coverpoint = "cp_fcsr_access"
    ######################################

    lines = [
        comment_banner(
            "cp_fcsr_access",
            "All types of accesses to all fcsrs",
        )
    ]

    csrf = [("fcsr", None), ("fflags", None), ("frm", None)]

    for csr in csrf:
        lines.extend(csr_access_test(test_data, csr, covergroup, coverpoint))

    return lines


def _generate_fcsr_walk(test_data: TestData) -> list[str]:
    """Walking ones in each fp CSR."""
    ######################################
    covergroup = "ZicsrF_cg"
    coverpoint = "cp_fcsr_walk"
    ######################################

    lines = [
        comment_banner(
            "cp_fcsr_walk",
            "Walking ones in each fp CSR",
        )
    ]

    csrf = [("fcsr", None), ("fflags", None), ("frm", None)]

    for csr in csrf:
        lines.extend(csr_walk_test(test_data, csr, covergroup, coverpoint))

    return lines


def _generate_fcsr_write(test_data: TestData) -> list[str]:
    """Writing to each fp CSR field."""
    ######################################
    covergroup = "ZicsrF_cg"
    coverpoint = "cp_fcsr_frm_write"
    ######################################

    r1 = test_data.int_regs.get_register()

    lines = [
        comment_banner(
            "cp_fcsr_frm_write",
            "Writing to fcsr.FRM and reading back frm",
        )
    ]

    for i in range(8):
        lines.extend(
            [
                "",
                f"# Testcase: write {i:03b} to fcsr.FRM",
                f"LI(x{r1}, {i << 5})           # write value {i << 5}",
                test_data.add_testcase(f"b_{i}_fcsr", coverpoint, covergroup),
                gen_csr_write_sigupd(r1, "fcsr", test_data),
                test_data.add_testcase(f"b_{i}_frm", coverpoint, covergroup),
                gen_csr_read_sigupd(r1, ("frm", None), test_data),
            ]
        )

    ######################################
    coverpoint = "cp_fcsr_fflags_write"
    ######################################

    lines.append(
        comment_banner(
            "cp_fcsr_fflags_write",
            "Writing to fcsr.FFLAGS and reading back fflags",
        )
    )

    for i in range(32):
        lines.extend(
            [
                "",
                f"# Testcase: write {i:05b} to fcsr.FFLAGS",
                f"LI(x{r1}, {i})           # write value {i}",
                test_data.add_testcase(f"b_{i}_fcsr", coverpoint, covergroup),
                gen_csr_write_sigupd(r1, "fcsr", test_data),
                test_data.add_testcase(f"b_{i}_fflags", coverpoint, covergroup),
                gen_csr_read_sigupd(r1, ("fflags", None), test_data),
            ]
        )

    ######################################
    coverpoint = "cp_frm_write"
    ######################################

    lines.append(
        comment_banner(
            "cp_frm_write",
            "Writing to frm and reading back fcsr",
        )
    )

    for i in range(8):
        lines.extend(
            [
                "",
                f"# Testcase: write {i:03b} to frm",
                f"LI(x{r1}, {i})           # write value {i}",
                test_data.add_testcase(f"b_{i}_frm", coverpoint, covergroup),
                gen_csr_write_sigupd(r1, "frm", test_data),
                test_data.add_testcase(f"b_{i}_fcsr", coverpoint, covergroup),
                gen_csr_read_sigupd(r1, ("fcsr", None), test_data),
            ]
        )
    ######################################
    coverpoint = "cp_fflags_write"
    ######################################

    lines.append(
        comment_banner(
            "cp_fflags_write",
            "Writing to fflags and reading back fcsr",
        )
    )

    for i in range(32):
        lines.extend(
            [
                "",
                f"# Testcase: write {i:05b} to fflags",
                f"LI(x{r1}, {i})           # write value {i}",
                test_data.add_testcase(f"b_{i}_fflags", coverpoint, covergroup),
                gen_csr_write_sigupd(r1, "fflags", test_data),
                test_data.add_testcase(f"b_{i}_fcsr", coverpoint, covergroup),
                gen_csr_read_sigupd(r1, ("fcsr", None), test_data),
            ]
        )

    ######################################
    coverpoint = "cp_fcsr_swap"
    ######################################

    lines.append(
        comment_banner(
            "cp_fcsr_swap",
            "csrrw/csrrs/csrrc with rd != x0 on fcsr, frm and fflags return the old value:\n"
            "fcsr in bits 7:0, frm in bits 2:0, fflags in bits 4:0, zeros above.\n"
            "fcsr is then read back to check the write.",
        )
    )

    r2, r3 = test_data.int_regs.get_registers(2)
    # (op, prior fcsr, rs1 value): each prior fcsr has nonzero frm and fflags fields
    swaps = [("csrrw", 0xB5, 0xF4A), ("csrrs", 0x6A, 0x125), ("csrrc", 0xFF, 0x1D6)]
    for csr in ("fcsr", "frm", "fflags"):
        for op, prior, val in swaps:
            lines.extend(
                [
                    "",
                    f"# Testcase: {op} on {csr} with fcsr = {prior:#04x} returns the old {csr}",
                    f"LI(x{r1}, {prior:#x})           # prior fcsr value",
                    f"csrw fcsr, x{r1}",
                    f"LI(x{r2}, {val:#x})           # {op} source value",
                    test_data.add_testcase(f"{op}_{csr}", coverpoint, covergroup),
                    f"{op} x{r3}, {csr}, x{r2}    # old {csr} -> x{r3}",
                    write_sigupd(r3, test_data, "int"),
                    test_data.add_testcase(f"{op}_{csr}_fcsr", coverpoint, covergroup),
                    gen_csr_read_sigupd(r3, ("fcsr", None), test_data),
                ]
            )

    test_data.int_regs.return_registers([r1, r2, r3])

    return lines


def make_op(
    mnemonic: str,
    fs1: int,
    fs2: int,
    test_data: TestData,
    coverpoint: str,
    covergroup: str,
    flag: str,
    comment: str,
) -> list[str]:
    """Helper to generate a fp instruction with a comment and check flags."""
    lines = [
        "",
        "csrwi fflags, 0 # reset flags",
        test_data.add_testcase(mnemonic, f"{coverpoint}_{flag}", covergroup),
        f"{mnemonic} f7, f{fs1}, f{fs2}           # {comment}",
        write_sigupd(7, test_data, "float"),
    ]
    return lines


STATIC_RMS = ("rne", "rtz", "rdn", "rup", "rmm")


def _tininess_cases(
    test_data: TestData,
    name: str,
    mnemonic: str,
    operands: list[int],
    fp_load_type: Literal["single", "double", "half"],
) -> list[str]:
    """Load one directed tininess operand set and run it under each static rounding mode."""
    covergroup = "ZicsrF_cg"
    coverpoint = f"cp_underflow_after_rounding_{name}"
    regs = [10, 11, 12][: len(operands)]
    lines = [""]
    lines.extend(load_float_reg(src, reg, val, test_data, fp_load_type) for src, reg, val in zip("abc", regs, operands))
    sources = ", ".join(f"f{reg}" for reg in regs)
    for rm in STATIC_RMS:
        lines.extend(
            [
                "",
                "csrwi fflags, 0 # reset flags",
                test_data.add_testcase(rm, coverpoint, covergroup),
                f"{mnemonic} f13, {sources}, {rm}",
                write_sigupd(13, test_data, "float"),
            ]
        )
    return lines


def _generate_instr_tests(test_data: TestData) -> list[str]:
    """Operations to set each flag."""
    ######################################
    covergroup = "ZicsrF_cg"
    coverpoint = "cp_fflags_set_m"
    ######################################

    r1 = test_data.int_regs.get_register()

    lines = [
        comment_banner(
            "cp_fflags_set_m_NV/DZ/OF/UF/NX",
            "Set each flag with different operations",
        )
    ]
    lines.extend(
        [
            "csrw fcsr, zero    # clear all flags and rounding mode before starting",
            load_float_reg("0.0", 10, 0x00000000, test_data, "single"),
            load_float_reg("1.0", 11, 0x3F800000, test_data, "single"),
            load_float_reg("3.0", 12, 0x40400000, test_data, "single"),
            load_float_reg("inf", 13, 0x7F800000, test_data, "single"),
            load_float_reg("tiny", 14, 0x00800000, test_data, "single"),
            load_float_reg("max", 15, 0x7F7FFFFF, test_data, "single"),
        ]
    )
    lines.extend(make_op("fsub.s", 13, 13, test_data, coverpoint, covergroup, "NV", "inf - inf sets invalid flag"))
    lines.extend(make_op("fdiv.s", 11, 10, test_data, coverpoint, covergroup, "DZ", "1 / 0  sets divide by zero"))
    lines.extend(make_op("fadd.s", 15, 15, test_data, coverpoint, covergroup, "OF", "big + big sets overflow flag"))
    lines.extend(make_op("fmul.s", 14, 14, test_data, coverpoint, covergroup, "UF", "tiny * tiny sets underflow flag"))
    lines.extend(make_op("fdiv.s", 11, 12, test_data, coverpoint, covergroup, "NX", "1 / 3 sets inexact flag"))

    lines.append(
        comment_banner(
            "cp_underflow_after_rounding_*",
            "Check underflow flag is determined after rounding.\n"
            "Each operand set is run under all five static rounding modes. Depending on the mode, the result\n"
            "is tiny before rounding but not after (UF = 0), or tiny after rounding even when the delivered\n"
            "result is +/-2^emin (UF = 1).",
        )
    )

    lines.extend(_tininess_cases(test_data, "fma_s", "fmadd.s", [0x3F00FBFF, 0x80000001, 0x807FFFFF], "single"))
    lines.extend(_tininess_cases(test_data, "fmul_s", "fmul.s", [0x00800001, 0x3F7FFFFE], "single"))
    lines.append("\n#ifdef D_SUPPORTED")
    lines.extend(
        _tininess_cases(
            test_data, "fma_d", "fmadd.d", [0x802FFFFFFFBFFEFF, 0x000FFFFFFFFFFFFE, 0x0010000000000000], "double"
        )
    )
    lines.extend(_tininess_cases(test_data, "fmul_d", "fmul.d", [0x0010000000000001, 0xBFEFFFFFFFFFFFFE], "double"))
    lines.extend(_tininess_cases(test_data, "fcvt_s_d", "fcvt.s.d", [0xB80FFFFFFFFDFEFF], "double"))
    lines.extend(
        [
            "#else",
            f"{INDENT}# increment data pointer to skip over these tests",
            f"addi x{test_data.int_regs.data_reg}, x{test_data.int_regs.data_reg}, {6 * test_data.flen // 8}",
            "#endif",
        ]
    )
    # Quads are not yet supported by Sail, and load_float_reg only writes out 8 bytes without Q.
    # Add these operand sets under #ifdef Q_SUPPORTED once support is ready:
    #   fma_q    fmadd.q  0x3F9800000000000001FFFFFFFF7FFFFE, 0x00000000000000000000000000000001,
    #                     0x80010000000000000000000000000000
    #   fmul_q   fmul.q   0x0000FFFFFFFFFFFFFFFFFFFFFFFFFFFF, 0x3FFF0000000000000000000000000001
    #   fcvt_s_q fcvt.s.q 0x3F80FFFFFFFE0000000000FFFFFFFFFF
    lines.append("\n#ifdef ZFH_SUPPORTED")
    lines.extend(_tininess_cases(test_data, "fma_h", "fmadd.h", [0x0BC7, 0x03FF, 0x8400], "half"))
    lines.extend(_tininess_cases(test_data, "fmul_h", "fmul.h", [0x0401, 0x3BFE], "half"))
    lines.extend(
        [
            "#else",
            f"{INDENT}# increment data pointer to skip over these tests",
            f"addi x{test_data.int_regs.data_reg}, x{test_data.int_regs.data_reg}, {5 * test_data.flen // 8}",
            "#endif",
            "\n#if defined(ZFHMIN_SUPPORTED) || defined(ZFH_SUPPORTED)",
        ]
    )
    lines.extend(_tininess_cases(test_data, "fcvt_h_s", "fcvt.h.s", [0x387FF000], "single"))
    lines.extend(
        [
            "#else",
            f"{INDENT}# increment data pointer to skip over these tests",
            f"addi x{test_data.int_regs.data_reg}, x{test_data.int_regs.data_reg}, {1 * test_data.flen // 8}",
            "#endif",
        ]
    )

    test_data.int_regs.return_registers([r1])

    return lines


def _generate_frm_reserved_static_rm(test_data: TestData) -> list[str]:
    """Static rounding modes execute normally while frm holds a reserved value."""
    ######################################
    covergroup = "ZicsrF_cg"
    coverpoint = "cp_frm_reserved_static_rm"
    ######################################

    lines = [
        comment_banner(
            coverpoint,
            "Set frm to each reserved value (5-7) and execute fadd.s with each static rounding mode.\n"
            "Only dynamic rounding depends on frm, so none of these trap.\n"
            "1.0 + 2^-24 is an exact tie, so each rounding mode gives its own result.",
        ),
        load_float_reg("1.0", 10, 0x3F800000, test_data, "single"),
        load_float_reg("2^-24", 11, 0x33800000, test_data, "single"),
    ]
    for frm in (5, 6, 7):
        lines.append(f"csrwi frm, {frm}        # reserved rounding mode")
        for rm in ("rne", "rtz", "rdn", "rup", "rmm"):
            lines.extend(
                [
                    "",
                    "csrwi fflags, 0 # reset flags",
                    test_data.add_testcase(f"frm{frm}_{rm}", coverpoint, covergroup),
                    f"fadd.s f7, f10, f11, {rm}",
                    write_sigupd(7, test_data, "float"),
                ]
            )
    lines.append("csrwi frm, 0        # back to a legal rounding mode")
    return lines


@add_priv_test_generator(
    "ZicsrF",
    required_extensions=["Zicsr", "F"],
    march_extensions=["F", "D", "Zfh"],
)
def make_zicsrf(test_data: TestData) -> list[TestChunk]:
    """Generate tests for ZicsrF unprivileged floating-point fcsr extension."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()

    tc.code.extend(_generate_fcsr_access(test_data))
    tc.code.extend(_generate_fcsr_walk(test_data))
    tc.code.extend(_generate_fcsr_write(test_data))
    tc.code.extend(_generate_instr_tests(test_data))
    tc.code.extend(_generate_frm_reserved_static_rm(test_data))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
