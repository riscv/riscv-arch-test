##################################
# ZicsrF.py
#
# Unprivileged floating-point fcsr tests
# David_Harris@hmc.edu 19 Feb 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Unprivileged floating-point fcsr tests generator."""

from testgen.asm.csr import csr_access_test, csr_walk_test, gen_csr_read_sigupd, gen_csr_write_sigupd
from testgen.asm.helpers import comment_banner, load_float_reg, write_sigupd
from testgen.data.state import TestData
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

    fcsrs = ["fcsr", "fflags", "frm"]

    for csr in fcsrs:
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

    fcsrs = ["fcsr", "fflags", "frm"]

    for csr in fcsrs:
        lines.extend(csr_walk_test(test_data, csr, covergroup, coverpoint))

    return lines


def _generate_fcsr_write(test_data: TestData) -> list[str]:
    """Writing to each fp CSR field."""
    ######################################
    covergroup = "ZicsrF_cg"
    coverpoint = "cp_fcsr_frm_write"
    ######################################

    r1 = test_data.int_regs.get_register(exclude_regs=[0])

    lines = [
        comment_banner(
            "cp_fcsr_frm_write",
            "Writing to fcsr.FRM and reading back frm",
        )
    ]

    for i in range(8):
        lines.extend(
            [
                test_data.add_testcase(coverpoint, f"b_{i}", covergroup),
                f"    LI(x{r1}, {i << 5})           # write value {i << 5}",
                gen_csr_write_sigupd(r1, "fcsr", test_data),
                gen_csr_read_sigupd(r1, "frm", test_data),
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
                test_data.add_testcase(coverpoint, f"b_{i}", covergroup),
                f"    LI(x{r1}, {i})           # write value {i}",
                gen_csr_write_sigupd(r1, "fcsr", test_data),
                gen_csr_read_sigupd(r1, "fflags", test_data),
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
                test_data.add_testcase(coverpoint, f"b_{i}", covergroup),
                f"    LI(x{r1}, {i})           # write value {i}",
                gen_csr_write_sigupd(r1, "frm", test_data),
                gen_csr_read_sigupd(r1, "fcsr", test_data),
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
                test_data.add_testcase(coverpoint, f"b_{i}", covergroup),
                f"    LI(x{r1}, {i})           # write value {i}",
                gen_csr_write_sigupd(r1, "fflags", test_data),
                gen_csr_read_sigupd(r1, "fcsr", test_data),
            ]
        )

    test_data.int_regs.return_registers([r1])

    return lines


def make_op(
    mnemonic: str,
    fs1: int,
    fs2: int,
    test_data: TestData,
    coverpoint: str,
    covergroup: str,
    coverbin: str,
    comment: str,
) -> list[str]:
    """Helper to generate a fp instruction with a comment and check flags."""
    lines = [
        test_data.add_testcase(coverpoint, coverbin, covergroup),
        "\tcsrwi fflags, 0 # reset flags",
        f"\t{mnemonic} f7, f{fs1}, f{fs2}           # {comment}",
        write_sigupd(7, test_data, "float"),
    ]
    return lines


def _generate_instr_tests(test_data: TestData) -> list[str]:
    """Operations to set each flag."""
    ######################################
    covergroup = "ZicsrF_cg"
    coverpoint = "cp_fflags_set_m"
    ######################################

    r1 = test_data.int_regs.get_register(exclude_regs=[0])

    lines = [
        comment_banner(
            "cp_fflags_set_m",
            "Set each flag with different operations",
        )
    ]
    lines.extend(
        [
            "\tCSRW(fcsr, zero)    # clear all flags and rounding mode before starting",
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

    ######################################
    coverpoint = "cp_underflow_after_rounding"
    ######################################

    lines.append(
        comment_banner(
            "cp_underflow_after_rounding",
            "Check underflow flag is determined after rounding",
        )
    )

    lines.extend(
        [
            test_data.add_testcase("cp_underflow_after_rounding_fma_s_rdn", "fmadd", covergroup),
            "\tcsrwi fflags, 0 # reset flags",
            load_float_reg("a", 10, 0x3F00FBFF, test_data, "single"),
            load_float_reg("b", 11, 0x80000001, test_data, "single"),
            load_float_reg("c", 12, 0x807FFFFF, test_data, "single"),
            "\tfmadd.s f13, f10, f11, f12, rdn",
            write_sigupd(13, test_data, "float"),
            test_data.add_testcase("cp_underflow_after_rounding_fmul_s_rup", "fmul", covergroup),
            "\tcsrwi fflags, 0 # reset flags",
            load_float_reg("a", 10, 0x00800001, test_data, "single"),
            load_float_reg("b", 11, 0x3F7FFFFE, test_data, "single"),
            "\tfmul.s f13, f10, f11, rup",
            write_sigupd(13, test_data, "float"),
            "\n#ifdef D_SUPPORTED",
            test_data.add_testcase("cp_underflow_after_rounding_fma_d_rup", "fmadd", covergroup),
            "\tcsrwi fflags, 0 # reset flags",
            load_float_reg("a", 10, 0x802FFFFFFFBFFEFF, test_data, "double"),
            load_float_reg("b", 11, 0x000FFFFFFFFFFFFE, test_data, "double"),
            load_float_reg("c", 12, 0x0010000000000000, test_data, "double"),
            "\tfmadd.d f13, f10, f11, f12, rup",
            write_sigupd(13, test_data, "float"),
            test_data.add_testcase("cp_underflow_after_rounding_fmul_d_rdn", "fmul", covergroup),
            "\tcsrwi fflags, 0 # reset flags",
            load_float_reg("a", 10, 0x0010000000000001, test_data, "double"),
            load_float_reg("b", 11, 0xBFEFFFFFFFFFFFFE, test_data, "double"),
            "\tfmul.d f13, f10, f11, rdn",
            write_sigupd(13, test_data, "float"),
            test_data.add_testcase("cp_underflow_after_rounding_fcvt_s_d_rne", "fcvt", covergroup),
            "\tcsrwi fflags, 0 # reset flags",
            load_float_reg("a", 10, 0xB80FFFFFFFFDFEFF, test_data, "double"),
            "\tfcvt.s.d f13, f10, rne",
            write_sigupd(13, test_data, "float"),
            "#else",
            "\t# increment data pointer to skip over these tests"
            f"\taddi {test_data.int_regs.data_reg}, {test_data.int_regs.data_reg}, {6 * test_data.flen}",
            "#endif",
            # Quads are not yet supported by Sail.  load_float_reg is only writing out 8 bytes
            # (without Q supported).  Comment out until support is ready.
            # f"\n#ifdef Q_SUPPORTED",
            # test_data.add_testcase("cp_underflow_after_rounding_fma_q_rdn", "fmadd", covergroup),
            # f"\tcsrwi fflags, 0 # reset flags",
            # load_float_reg("a", 10, 0x3F9800000000000001FFFFFFFF7FFFFE, test_data, "quad"),
            # load_float_reg("b", 11, 0x00000000000000000000000000000001, test_data, "quad"),
            # load_float_reg("c", 12, 0x80010000000000000000000000000000, test_data, "quad"),
            # f"\tfmadd.q f13, f10, f11, f12, rdn",
            # write_sigupd(13, test_data, "float"),
            # test_data.add_testcase("cp_underflow_after_rounding_fmul_q_rne", "fmul", covergroup),
            # f"\tcsrwi fflags, 0 # reset flags",
            # load_float_reg("a", 10, 0x0000FFFFFFFFFFFFFFFFFFFFFFFFFFFF, test_data, "quad"),
            # load_float_reg("b", 11, 0x3FFF0000000000000000000000000001, test_data, "quad"),
            # f"\tfmul.q f13, f10, f11, rne",
            # write_sigupd(13, test_data, "float"),
            # test_data.add_testcase("cp_underflow_after_rounding_fcvt_s_q_rup", "fcvt", covergroup),
            # f"\tcsrwi fflags, 0 # reset flags",
            # load_float_reg("a", 10, 0x3F80FFFFFFFE0000000000FFFFFFFFFF, test_data, "quad"),
            # f"\tfcvt.s.q f13, f10, rup",
            # write_sigupd(13, test_data, "float"),
            # f"#else",
            # "\t# increment data pointer to skip over these tests"
            # f"\taddi {test_data.int_regs.data_reg}, {test_data.int_regs.data_reg}, {6*test_data.flen}",
            # f"#endif",
            "\n#ifdef ZFH_SUPPORTED",
            test_data.add_testcase("cp_underflow_after_rounding_fma_h_rne", "fmadd", covergroup),
            "\tcsrwi fflags, 0 # reset flags",
            load_float_reg("a", 10, 0x0BC7, test_data, "half"),
            load_float_reg("b", 11, 0x03FF, test_data, "half"),
            load_float_reg("c", 12, 0x8400, test_data, "half"),
            "\tfmadd.h f13, f10, f11, f12, rne",
            write_sigupd(13, test_data, "float"),
            test_data.add_testcase("cp_underflow_after_rounding_fmul_h_rup", "fmul", covergroup),
            "\tcsrwi fflags, 0 # reset flags",
            load_float_reg("a", 10, 0x0401, test_data, "half"),
            load_float_reg("b", 11, 0x3BF8, test_data, "half"),
            "\tfmul.h f13, f10, f11, rup",
            write_sigupd(13, test_data, "float"),
            test_data.add_testcase("cp_underflow_after_rounding_fcvt_h_s_rne", "fcvt", covergroup),
            "\tcsrwi fflags, 0 # reset flags",
            load_float_reg("a", 10, 0x387FF000, test_data, "single"),
            "\tfcvt.h.s f13, f10, rne",
            write_sigupd(13, test_data, "float"),
            "#else",
            "\t# increment data pointer to skip over these tests"
            f"\taddi {test_data.int_regs.data_reg}, {test_data.int_regs.data_reg}, {6 * test_data.flen}",
            "#endif",
            "\n#ifdef ZFHMIN_SUPPORTED",
            test_data.add_testcase("cp_underflow_after_rounding_fcvt_h_s_rne_zfhmin", "fcvt", covergroup),
            "\tcsrwi fflags, 0 # reset flags",
            load_float_reg("a", 10, 0x387FF000, test_data, "single"),
            "\tfcvt.h.s f13, f10, rne",
            write_sigupd(13, test_data, "float"),
            "#else",
            "\t# increment data pointer to skip over these tests"
            f"\taddi {test_data.int_regs.data_reg}, {test_data.int_regs.data_reg}, {1 * test_data.flen}",
            "#endif",
        ]
    )

    test_data.int_regs.return_registers([r1])

    return lines


@add_priv_test_generator("ZicsrF", required_extensions=["Zicsr", "F"], march_extensions=["Zicsr", "F", "D", "Zfh"])
def make_zicsrf(test_data: TestData) -> list[str]:
    """Generate tests for ZicsrF unprivileged floating-point fcsr extension."""
    lines: list[str] = []

    lines.extend(_generate_fcsr_access(test_data))
    lines.extend(_generate_fcsr_walk(test_data))
    lines.extend(_generate_fcsr_write(test_data))
    lines.extend(_generate_instr_tests(test_data))

    return lines
