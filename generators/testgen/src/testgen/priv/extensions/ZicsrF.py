##################################
# ZicsrF.py
#
# Unprivileged floating-point fcsr tests
# David_Harris@hmc.edu 19 Feb 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Unprivileged floating-point fcsr tests generator."""

from collections.abc import Callable
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


def _guarded(test_data: TestData, condition: str, build: Callable[[], list[str]]) -> list[str]:
    """Emit build()'s lines under a preprocessor condition.

    When the condition is false, the data pointer skips the test data that the block would have loaded.
    """
    assert test_data.test_chunk is not None, "No active test chunk — call begin_test_chunk() first"
    first_value = len(test_data.test_chunk.data_values)
    body = build()
    loads = len(test_data.test_chunk.data_values) - first_value
    lines = ["", f"#if {condition}", *body]
    if loads:
        data_reg = test_data.int_regs.data_reg
        lines.extend(
            [
                "#else",
                f"{INDENT}# increment data pointer to skip over these tests",
                f"addi x{data_reg}, x{data_reg}, {loads * test_data.flen // 8}",
            ]
        )
    lines.append("#endif")
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
            "Check underflow flag is determined after rounding (f-st-ext.adoc:188).\n"
            "Each operand set is run under all five static rounding modes. Depending on the mode, the result\n"
            "is tiny before rounding but not after (UF = 0), or tiny after rounding even when the delivered\n"
            "result is +/-2^emin (UF = 1).\n"
            "fmul_emin_*: 2^emin * (1 - 2^-p) is tiny after rounding in every mode, so UF = 1 even where the\n"
            "delivered result is +/-2^emin.\n"
            "fdiv_*: (2 - 2^-(p-2)) * 2^emin / (2 - 2^-(p-1)) rounds to +/-2^emin only when rounding away from zero,\n"
            "with UF = 1. A quotient of p-bit significands never lies within 2^-p of 1 unless it is exact, so\n"
            "fdiv cannot produce a result that is tiny before rounding but not after.",
        )
    )

    lines.extend(_tininess_cases(test_data, "fma_s", "fmadd.s", [0x3F00FBFF, 0x80000001, 0x807FFFFF], "single"))
    lines.extend(_tininess_cases(test_data, "fmul_s", "fmul.s", [0x00800001, 0x3F7FFFFE], "single"))
    lines.extend(_tininess_cases(test_data, "fmul_emin_s", "fmul.s", [0x00800000, 0x3F7FFFFF], "single"))
    lines.extend(_tininess_cases(test_data, "fdiv_s", "fdiv.s", [0x00FFFFFE, 0x3FFFFFFF], "single"))
    lines.extend(
        _guarded(
            test_data,
            "defined(D_SUPPORTED)",
            lambda: [
                *_tininess_cases(
                    test_data,
                    "fma_d",
                    "fmadd.d",
                    [0x802FFFFFFFBFFEFF, 0x000FFFFFFFFFFFFE, 0x0010000000000000],
                    "double",
                ),
                *_tininess_cases(test_data, "fmul_d", "fmul.d", [0x0010000000000001, 0xBFEFFFFFFFFFFFFE], "double"),
                *_tininess_cases(test_data, "fcvt_s_d", "fcvt.s.d", [0xB80FFFFFFFFDFEFF], "double"),
                *_tininess_cases(
                    test_data, "fmul_emin_d", "fmul.d", [0x8010000000000000, 0x3FEFFFFFFFFFFFFF], "double"
                ),
                *_tininess_cases(test_data, "fdiv_d", "fdiv.d", [0x801FFFFFFFFFFFFE, 0x3FFFFFFFFFFFFFFF], "double"),
            ],
        )
    )
    # Quads are not yet supported by Sail, and load_float_reg only writes out 8 bytes without Q.
    # Add these operand sets under #ifdef Q_SUPPORTED once support is ready:
    #   fma_q    fmadd.q  0x3F9800000000000001FFFFFFFF7FFFFE, 0x00000000000000000000000000000001,
    #                     0x80010000000000000000000000000000
    #   fmul_q   fmul.q   0x0000FFFFFFFFFFFFFFFFFFFFFFFFFFFF, 0x3FFF0000000000000000000000000001
    #   fcvt_s_q fcvt.s.q 0x3F80FFFFFFFE0000000000FFFFFFFFFF
    lines.extend(
        _guarded(
            test_data,
            "defined(ZFH_SUPPORTED)",
            lambda: [
                *_tininess_cases(test_data, "fma_h", "fmadd.h", [0x0BC7, 0x03FF, 0x8400], "half"),
                # 0x0401 * 0x3BFE = (1 - 2^-20) * 2^-14: rounds to 2^-14 at 11 bits under RNE, RUP and RMM
                *_tininess_cases(test_data, "fmul_h", "fmul.h", [0x0401, 0x3BFE], "half"),
                *_tininess_cases(test_data, "fmul_emin_h", "fmul.h", [0x0400, 0x3BFF], "half"),
                *_tininess_cases(test_data, "fdiv_h", "fdiv.h", [0x07FE, 0x3FFF], "half"),
            ],
        )
    )
    lines.extend(
        _guarded(
            test_data,
            "defined(ZFHMIN_SUPPORTED)",
            lambda: _tininess_cases(test_data, "fcvt_h_s", "fcvt.h.s", [0x387FF000], "single"),
        )
    )

    test_data.int_regs.return_registers([r1])

    return lines


def _generate_frm_reserved_static_rm(test_data: TestData) -> list[str]:
    """Static rounding modes execute normally while frm holds a reserved value."""
    ######################################
    covergroup = "ZicsrF_cg"
    coverpoint = "cp_frm_reserved_static_rm"
    ######################################

    one, neg_one, a1, a2, a3, dest = test_data.float_regs.get_registers(6)
    # Each (augend, addend) pair is an inexact sum; the three results together differ in every rounding mode:
    #   RNE (1+2u, -1, 1)  RTZ (1+u, -1, 1)  RDN (1+u, -1-u, 1)  RUP (1+2u, -1, 1+u)  RMM (1+2u, -1-u, 1)
    # where u = 2^-23.
    adds = (("tie_odd", one, a1), ("tie_even_neg", neg_one, a2), ("quarter_ulp", one, a3))
    lines = [
        comment_banner(
            coverpoint,
            "Set frm to each reserved value (5-7) and execute fadd.s with each static rounding mode.\n"
            "Only dynamic rounding depends on frm, so none of these trap.\n"
            "Three adds per mode: 1 + 1.5*2^-23 (a tie between 1+2^-23 and 1+2^-22), -1 - 2^-24 (a tie\n"
            "between -1 and -1-2^-23) and 1 + 2^-25 (below half an ulp). Together their results differ\n"
            "in every rounding mode.",
        ),
        load_float_reg("1.0", one, 0x3F800000, test_data, "single"),
        load_float_reg("-1.0", neg_one, 0xBF800000, test_data, "single"),
        load_float_reg("1.5*2^-23", a1, 0x34400000, test_data, "single"),
        load_float_reg("-2^-24", a2, 0xB3800000, test_data, "single"),
        load_float_reg("2^-25", a3, 0x33000000, test_data, "single"),
    ]
    for frm in (5, 6, 7):
        lines.append(f"csrwi frm, {frm}        # reserved rounding mode")
        for rm in STATIC_RMS:
            for name, fs1, fs2 in adds:
                lines.extend(
                    [
                        "",
                        "csrwi fflags, 0 # reset flags",
                        test_data.add_testcase(f"frm{frm}_{rm}_{name}", coverpoint, covergroup),
                        f"fadd.s f{dest}, f{fs1}, f{fs2}, {rm}",
                        write_sigupd(dest, test_data, "float"),
                    ]
                )
    lines.append("csrwi frm, 0        # back to a legal rounding mode")
    test_data.float_regs.return_registers([one, neg_one, a1, a2, a3, dest])
    return lines


def _fma_cases(
    test_data: TestData,
    p: str,
    load_type: Literal["single", "double", "half"],
    *,
    inf: int,
    qnan: int,
    snan: int,
    one: int,
    a: int,
    b: int,
    product: int,
    neg_product: int,
) -> list[str]:
    """FMA special cases in precision p, given that precision's encodings.

    a = 1 + 2^-k and b = 1 - 2^-k, so a*b = product = 1 - 2^-2k is exact; neg_product is -product.
    """
    covergroup = "ZicsrF_cg"
    ops = ("fmadd", "fmsub", "fnmadd", "fnmsub")
    fs1, fs2, fs3, fd = test_data.float_regs.get_registers(4)

    coverpoint = f"cp_fma_inf_zero_{p}"
    lines = [
        comment_banner(
            coverpoint,
            "Each FMA with multiplicands +inf and +0 and a quiet NaN, signaling NaN or finite addend.\n"
            "The result is the canonical NaN and NV is set, even for a quiet NaN addend (f-st-ext.adoc:310-312).",
        )
    ]
    for op in ops:
        for name, addend in (("qnan", qnan), ("snan", snan), ("one", one)):
            lines.extend(
                [
                    "",
                    load_float_reg("+inf", fs1, inf, test_data, load_type),
                    load_float_reg("+0", fs2, 0, test_data, load_type),
                    load_float_reg(name, fs3, addend, test_data, load_type),
                    "csrwi fflags, 0 # reset flags",
                    test_data.add_testcase(f"{op}_{name}", coverpoint, covergroup),
                    f"{op}.{p} f{fd}, f{fs1}, f{fs2}, f{fs3}, rne",
                    write_sigupd(fd, test_data, "float"),
                ]
            )

    coverpoint = f"cp_fma_exact_zero_{p}"
    lines.append(
        comment_banner(
            coverpoint,
            "Each FMA with (1 + 2^-k)(1 - 2^-k) = 1 - 2^-2k exact, and an addend that cancels the product.\n"
            "An exact zero sum is +0 in every rounding mode except RDN, where it is -0 (IEEE 754-2008 6.3).\n"
            "fnmadd and fnmsub negate the product, not the sum, so they follow the same rule\n"
            "(f-st-ext.adoc:284-290).",
        )
    )
    for op in ops:
        # fmadd and fnmadd add -(+/-a*b); fmsub and fnmsub add +(+/-a*b)
        addend = neg_product if op in ("fmadd", "fnmadd") else product
        lines.extend(
            [
                "",
                load_float_reg("1 + 2^-k", fs1, a, test_data, load_type),
                load_float_reg("1 - 2^-k", fs2, b, test_data, load_type),
                load_float_reg("cancelling addend", fs3, addend, test_data, load_type),
            ]
        )
        for rm in STATIC_RMS:
            lines.extend(
                [
                    "",
                    "csrwi fflags, 0 # reset flags",
                    test_data.add_testcase(f"{op}_{rm}", coverpoint, covergroup),
                    f"{op}.{p} f{fd}, f{fs1}, f{fs2}, f{fs3}, {rm}",
                    write_sigupd(fd, test_data, "float"),
                ]
            )

    test_data.float_regs.return_registers([fs1, fs2, fs3, fd])
    return lines


def _generate_fma(test_data: TestData) -> list[str]:
    """FMA special cases in single, double and half precision."""
    lines = _fma_cases(
        test_data,
        "s",
        "single",
        inf=0x7F800000,
        qnan=0x7FC00000,
        snan=0x7F800001,
        one=0x3F800000,
        a=0x3F800800,  # 1 + 2^-12
        b=0x3F7FF000,  # 1 - 2^-12
        product=0x3F7FFFFF,  # 1 - 2^-24
        neg_product=0xBF7FFFFF,
    )
    lines.extend(
        _guarded(
            test_data,
            "defined(D_SUPPORTED)",
            lambda: _fma_cases(
                test_data,
                "d",
                "double",
                inf=0x7FF0000000000000,
                qnan=0x7FF8000000000000,
                snan=0x7FF0000000000001,
                one=0x3FF0000000000000,
                a=0x3FF0000004000000,  # 1 + 2^-26
                b=0x3FEFFFFFF8000000,  # 1 - 2^-26
                product=0x3FEFFFFFFFFFFFFE,  # 1 - 2^-52
                neg_product=0xBFEFFFFFFFFFFFFE,
            ),
        )
    )
    lines.extend(
        _guarded(
            test_data,
            "defined(ZFH_SUPPORTED)",
            lambda: _fma_cases(
                test_data,
                "h",
                "half",
                inf=0x7C00,
                qnan=0x7E00,
                snan=0x7C01,
                one=0x3C00,
                a=0x3C20,  # 1 + 2^-5
                b=0x3BC0,  # 1 - 2^-5
                product=0x3BFE,  # 1 - 2^-10
                neg_product=0xBBFE,
            ),
        )
    )
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
    tc = test_data.begin_test_chunk("fma")
    tc.code.extend(_generate_fma(test_data))
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
