##################################
# ZicsrF.py
#
# Unprivileged floating-point fcsr tests
# David_Harris@hmc.edu 19 Feb 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Unprivileged floating-point fcsr tests generator."""

from collections.abc import Callable
from dataclasses import dataclass
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


def _guarded(test_data: TestData, condition: str | None, build: Callable[[], list[str]]) -> list[str]:
    """Emit build()'s lines under a preprocessor condition.

    When the condition is false, the data pointer skips the test data that the block would have loaded.
    """
    if condition is None:
        return build()
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


# Preprocessor conditions for the extensions each directed group needs (F is always present)
D = "defined(D_SUPPORTED)"
ZFH = "defined(ZFH_SUPPORTED)"
ZFHMIN = "defined(ZFHMIN_SUPPORTED)"  # Zfh implies Zfhmin
ZFBFMIN = "defined(ZFBFMIN_SUPPORTED)"
ZFA = "defined(ZFA_SUPPORTED)"
RV64 = "__riscv_xlen == 64"

FloatLoadType = Literal["single", "double", "half"]


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
            D,
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
            ZFH,
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
            ZFHMIN,
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


######################################
# Directed FP edge cases
#
# These complement the F, D, Zfh, Zfbfmin and Zfa suites with operand sets whose results depend on
# the rounding mode, run under every static rounding mode. Crossing them with every rounding mode in
# those suites would multiply their size.
######################################


@dataclass(frozen=True)
class DirectedCase:
    """One operand set: its coverpoint bin, the instruction under test and its source operands."""

    bin: str
    mnemonic: str
    operands: tuple[int, ...]


@dataclass(frozen=True)
class DirectedGroup:
    """Directed cases that share a coverpoint, a preprocessor guard and an operand format.

    Each case runs once per rounding mode in rms; the testcase bin gets an _<rm> suffix when there is more than one.
    Integer operands are signed values loaded with LI. The result goes to an integer register when int_result is set.
    """

    coverpoint: str
    description: str
    guard: str | None
    load_type: FloatLoadType | Literal["int"]
    cases: tuple[DirectedCase, ...]
    rms: tuple[str, ...] = STATIC_RMS
    int_result: bool = False


def _directed_group(test_data: TestData, group: DirectedGroup) -> list[str]:
    """Emit one directed group: load each operand set, then run it under each rounding mode."""
    covergroup = "ZicsrF_cg"

    def build() -> list[str]:
        num_sources = max(len(case.operands) for case in group.cases)
        load_type = group.load_type
        int_sources = load_type == "int"
        sources = (test_data.int_regs if int_sources else test_data.float_regs).get_registers(num_sources)
        dest = test_data.int_regs.get_register() if group.int_result else test_data.float_regs.get_register()
        src_prefix = "x" if int_sources else "f"
        dest_prefix = "x" if group.int_result else "f"
        lines: list[str] = []
        for case in group.cases:
            lines.append("")
            for name, reg, val in zip("abc", sources, case.operands):
                if load_type == "int":
                    lines.append(f"LI(x{reg}, {val})           # load {name}: x{reg} = {val}")
                else:
                    lines.append(load_float_reg(name, reg, val, test_data, load_type))
            operands = ", ".join(f"{src_prefix}{reg}" for reg in sources[: len(case.operands)])
            for rm in group.rms:
                bin_name = case.bin if len(group.rms) == 1 else f"{case.bin}_{rm}"
                lines.extend(
                    [
                        "",
                        "csrwi fflags, 0 # reset flags",
                        test_data.add_testcase(bin_name, group.coverpoint, covergroup),
                        f"{case.mnemonic} {dest_prefix}{dest}, {operands}, {rm}",
                    ]
                )
                if group.int_result:
                    lines.append(write_sigupd(dest, test_data, "int"))
                    lines.append(write_sigupd(None, test_data, "fflags"))
                else:
                    lines.append(write_sigupd(dest, test_data, "float"))
        (test_data.int_regs if int_sources else test_data.float_regs).return_registers(sources)
        (test_data.int_regs if group.int_result else test_data.float_regs).return_register(dest)
        return lines

    return [comment_banner(group.coverpoint, group.description), *_guarded(test_data, group.guard, build)]


@dataclass(frozen=True)
class FmaFormat:
    """FMA operands in one precision. a = 1 + 2^-k and b = 1 - 2^-k, so a*b = 1 - 2^-2k is exact."""

    p: str
    guard: str | None
    load_type: FloatLoadType
    sign: int
    inf: int
    qnan: int
    snan: int
    one: int
    a: int
    b: int
    ab: int


_FMA_FORMATS = (
    FmaFormat(
        "s", None, "single", 1 << 31, 0x7F800000, 0x7FC00000, 0x7F800001, 0x3F800000, 0x3F800800, 0x3F7FF000, 0x3F7FFFFF
    ),
    FmaFormat(
        "d",
        D,
        "double",
        1 << 63,
        0x7FF0000000000000,
        0x7FF8000000000000,
        0x7FF0000000000001,
        0x3FF0000000000000,
        0x3FF0000004000000,
        0x3FEFFFFFF8000000,
        0x3FEFFFFFFFFFFFFE,
    ),
    FmaFormat("h", ZFH, "half", 1 << 15, 0x7C00, 0x7E00, 0x7C01, 0x3C00, 0x3C20, 0x3BC0, 0x3BFE),
)
_FMA_OPS = ("fmadd", "fmsub", "fnmadd", "fnmsub")
# Addend sign that cancels the product: fmadd and fnmadd add -(+/-a*b); fmsub and fnmsub add +(+/-a*b)
_FMA_CANCEL_NEG_ADDEND = {"fmadd": True, "fmsub": False, "fnmadd": True, "fnmsub": False}


def _fma_groups() -> list[DirectedGroup]:
    groups = []
    for fmt in _FMA_FORMATS:
        p = fmt.p
        addends = (("qnan", fmt.qnan), ("snan", fmt.snan), ("one", fmt.one))
        groups.append(
            DirectedGroup(
                f"cp_fma_inf_zero_{p}",
                "Each FMA with multiplicands +inf and +0 and a quiet NaN, signaling NaN or finite addend.\n"
                "The result is the canonical NaN and NV is set, even for a quiet NaN addend (f-st-ext.adoc:310-312).",
                fmt.guard,
                fmt.load_type,
                tuple(
                    DirectedCase(f"{op}_{name}", f"{op}.{p}", (fmt.inf, 0, addend))
                    for op in _FMA_OPS
                    for name, addend in addends
                ),
                rms=("rne",),
            )
        )
        groups.append(
            DirectedGroup(
                f"cp_fma_exact_zero_{p}",
                "Each FMA with (1 + 2^-k)(1 - 2^-k) = 1 - 2^-2k exact, and an addend that cancels the product.\n"
                "An exact zero sum is +0 in every rounding mode except RDN, where it is -0 (IEEE 754-2008 6.3).\n"
                "fnmadd and fnmsub negate the product, not the sum, so they follow the same rule\n"
                "(f-st-ext.adoc:284-290).",
                fmt.guard,
                fmt.load_type,
                tuple(
                    DirectedCase(
                        op, f"{op}.{p}", (fmt.a, fmt.b, fmt.ab | (fmt.sign if _FMA_CANCEL_NEG_ADDEND[op] else 0))
                    )
                    for op in _FMA_OPS
                ),
            )
        )
    return groups


_NARROWING_DESCRIPTION = (
    "Narrowing conversion at the destination's overflow threshold (max + 1/2 ulp, and one source ulp\n"
    "below it, negated), at halfway ties (+/-(1 + 1/2 ulp)) and 3/4 ulp above 1, and at the tininess boundary:\n"
    "2^emin * (1 - 2^-(p+1)) rounds to 2^emin at p bits (UF = 0 under RNE, RUP, RMM), while one source ulp\n"
    "below it is tiny after rounding but delivers 2^emin under RNE and RMM (UF = 1). Each value runs under every\n"
    "static rounding mode; together the results differ in every mode."
)


def _narrowing_cases(mnemonic: str, values: tuple[int, ...], names: tuple[str, ...]) -> tuple[DirectedCase, ...]:
    return tuple(DirectedCase(name, mnemonic, (val,)) for name, val in zip(names, values, strict=True))


_NARROWING_NAMES = ("ovf_tie", "ovf_below_neg", "tie_pos", "tie_neg", "above_half", "tiny_tie", "tiny_below")

_INT_DESCRIPTION = (
    "Integer to floating-point conversion of values that round in the destination precision. Signed: +/- a tie\n"
    "with an even lower neighbour and a value 3/4 ulp above a representable one. Unsigned: ties with an even and an\n"
    "odd lower neighbour and a value 1/4 ulp above. Half precision also converts the overflow threshold\n"
    "65520 = max + 1/2 ulp and the integer 65519 below it. Each runs under every static rounding mode\n"
    "(f-st-ext.adoc:339-340); together the results differ in every mode that the signedness allows."
)


def _int_cases(mnemonic: str, values: tuple[int, ...]) -> tuple[DirectedCase, ...]:
    """Name signed values tie_pos, tie_neg, above_half and unsigned ones tie_even, tie_odd, quarter_ulp.

    Two further values, for half precision, are the overflow threshold and the integer below it.
    """
    signed = mnemonic.split(".")[-1] in ("w", "l")
    names = ("tie_pos", "tie_neg", "above_half") if signed else ("tie_even", "tie_odd", "quarter_ulp")
    names += ("ovf_tie", "ovf_below_neg" if signed else "ovf_below")
    return tuple(DirectedCase(name, mnemonic, (val,)) for name, val in zip(names, values, strict=False))


def _cvt_groups() -> list[DirectedGroup]:
    return [
        DirectedGroup(
            "cp_fcvt_s_d_rounding",
            _NARROWING_DESCRIPTION,
            D,
            "double",
            _narrowing_cases(
                "fcvt.s.d",
                (
                    0x47EFFFFFF0000000,
                    0xC7EFFFFFEFFFFFFF,
                    0x3FF0000010000000,
                    0xBFF0000010000000,
                    0x3FF0000018000000,
                    0x380FFFFFF0000000,
                    0x380FFFFFEFFFFFFF,
                ),
                _NARROWING_NAMES,
            ),
        ),
        DirectedGroup(
            "cp_fcvt_h_s_rounding",
            _NARROWING_DESCRIPTION + "\nThe tiny_tie value is cp_underflow_after_rounding_fcvt_h_s.",
            ZFHMIN,
            "single",
            _narrowing_cases(
                "fcvt.h.s",
                (0x477FF000, 0xC77FEFFF, 0x3F801000, 0xBF801000, 0x3F801800, 0x387FEFFF),
                tuple(name for name in _NARROWING_NAMES if name != "tiny_tie"),
            ),
        ),
        DirectedGroup(
            "cp_fcvt_h_d_rounding",
            _NARROWING_DESCRIPTION,
            f"{D} && {ZFHMIN}",
            "double",
            _narrowing_cases(
                "fcvt.h.d",
                (
                    0x40EFFE0000000000,
                    0xC0EFFDFFFFFFFFFF,
                    0x3FF0020000000000,
                    0xBFF0020000000000,
                    0x3FF0030000000000,
                    0x3F0FFE0000000000,
                    0x3F0FFDFFFFFFFFFF,
                ),
                _NARROWING_NAMES,
            ),
        ),
        DirectedGroup(
            "cp_fcvt_bf16_s_rounding",
            _NARROWING_DESCRIPTION + "\nBF16 detects tininess after rounding (zfbfmin.adoc:73).",
            ZFBFMIN,
            "single",
            _narrowing_cases(
                "fcvt.bf16.s",
                (0x7F7F8000, 0xFF7F7FFF, 0x3F808000, 0xBF808000, 0x3F80C000, 0x007FC000, 0x007FBFFF),
                _NARROWING_NAMES,
            ),
        ),
        DirectedGroup(
            "cp_fcvt_s_w_rounding",
            _INT_DESCRIPTION,
            None,
            "int",
            _int_cases("fcvt.s.w", (2**24 + 1, -(2**24 + 1), 2**25 + 3)),
        ),
        DirectedGroup(
            "cp_fcvt_s_wu_rounding",
            _INT_DESCRIPTION,
            None,
            "int",
            _int_cases("fcvt.s.wu", (2**24 + 1, 2**24 + 3, 2**25 + 1)),
        ),
        DirectedGroup(
            "cp_fcvt_s_l_rounding",
            _INT_DESCRIPTION,
            RV64,
            "int",
            _int_cases("fcvt.s.l", (2**40 + 2**16, -(2**40 + 2**16), 2**41 + 3 * 2**16)),
        ),
        DirectedGroup(
            "cp_fcvt_s_lu_rounding",
            _INT_DESCRIPTION,
            RV64,
            "int",
            _int_cases("fcvt.s.lu", (2**40 + 2**16, 2**40 + 3 * 2**16, 2**41 + 2**16)),
        ),
        DirectedGroup(
            "cp_fcvt_d_l_rounding",
            _INT_DESCRIPTION,
            f"{RV64} && {D}",
            "int",
            _int_cases("fcvt.d.l", (2**53 + 1, -(2**53 + 1), 2**54 + 3)),
        ),
        DirectedGroup(
            "cp_fcvt_d_lu_rounding",
            _INT_DESCRIPTION,
            f"{RV64} && {D}",
            "int",
            _int_cases("fcvt.d.lu", (2**53 + 1, 2**53 + 3, 2**54 + 1)),
        ),
        DirectedGroup(
            "cp_fcvt_h_w_rounding",
            _INT_DESCRIPTION,
            ZFH,
            "int",
            _int_cases("fcvt.h.w", (2**11 + 1, -(2**11 + 1), 2**12 + 3, 65520, -65519)),
        ),
        DirectedGroup(
            "cp_fcvt_h_wu_rounding",
            _INT_DESCRIPTION,
            ZFH,
            "int",
            _int_cases("fcvt.h.wu", (2**11 + 1, 2**11 + 3, 2**12 + 1, 65520, 65519)),
        ),
        DirectedGroup(
            "cp_fcvt_h_l_rounding",
            _INT_DESCRIPTION,
            f"{RV64} && {ZFH}",
            "int",
            _int_cases("fcvt.h.l", (2**11 + 1, -(2**11 + 1), 2**12 + 3)),
        ),
        DirectedGroup(
            "cp_fcvt_h_lu_rounding",
            _INT_DESCRIPTION,
            f"{RV64} && {ZFH}",
            "int",
            _int_cases("fcvt.h.lu", (2**11 + 1, 2**11 + 3, 2**12 + 1)),
        ),
    ]


# fround/froundnx operands: 2.5 and -2.5 (ties), 2^(p-3) + 0.75 (3/4 of the lowest integer bit's
# fraction, at the last fraction bit) and -0.5 (rounds to -0 or -1)
_FROUND_VALUES: dict[str, tuple[str | None, FloatLoadType, tuple[int, ...]]] = {
    "s": (None, "single", (0x40200000, 0xC0200000, 0x4A000003, 0xBF000000)),
    "d": (D, "double", (0x4004000000000000, 0xC004000000000000, 0x4310000000000003, 0xBFE0000000000000)),
    "h": (ZFH, "half", (0x4100, 0xC100, 0x5C03, 0xB800)),
}
_FROUND_NAMES = ("tie_pos", "tie_neg", "above_half", "neg_half")

# fcvtmod.w.d operands: 2^31, -2^31-1, 2^31-0.5, -2^31-0.5, 2^32+5, -(2^32+5), 2^32+2^31+0.25, 1.5*2^84, -0.75,
# +inf, -inf, qNaN, sNaN
_FCVTMOD_VALUES = (
    ("p2_31", 0x41E0000000000000),
    ("m2_31_m1", 0xC1E0000000200000),
    ("p2_31_mhalf", 0x41DFFFFFFFE00000),
    ("m2_31_mhalf", 0xC1E0000000100000),
    ("p2_32_p5", 0x41F0000000500000),
    ("m2_32_m5", 0xC1F0000000500000),
    ("p3_2_31_frac", 0x41F8000000040000),
    ("big", 0x4538000000000000),
    ("m0_75", 0xBFE8000000000000),
    ("pinf", 0x7FF0000000000000),
    ("minf", 0xFFF0000000000000),
    ("qnan", 0x7FF8000000000000),
    ("snan", 0x7FF0000000000001),
)


def _zfa_groups() -> list[DirectedGroup]:
    groups = []
    for p, (guard, load_type, values) in _FROUND_VALUES.items():
        groups.append(
            DirectedGroup(
                f"cp_fround_{p}",
                "fround and froundnx at halfway and fractional values under every static rounding mode.\n"
                "Only froundnx sets NX (zfa.adoc:138-150). -0.5 rounds to -0 except under RDN and RMM.",
                f"{ZFA} && {guard}" if guard else ZFA,
                load_type,
                tuple(
                    DirectedCase(f"{op}_{name}", f"{op}.{p}", (val,))
                    for op in ("fround", "froundnx")
                    for name, val in zip(_FROUND_NAMES, values, strict=True)
                ),
            )
        )
    groups.append(
        DirectedGroup(
            "cp_fcvtmod_w_d",
            "fcvtmod.w.d keeps bits 31:0 of the truncated, unbounded integer, sign-extended; +/-inf and NaN give 0.\n"
            "Flags are those of fcvt.w.d: NV when out of range, else NX when inexact (zfa.adoc:176-186).",
            f"{ZFA} && {D}",
            "double",
            tuple(DirectedCase(name, "fcvtmod.w.d", (val,)) for name, val in _FCVTMOD_VALUES),
            rms=("rtz",),
            int_result=True,
        )
    )
    return groups


def _directed_chunk(test_data: TestData, split_name: str, groups: list[DirectedGroup]) -> TestChunk:
    tc = test_data.begin_test_chunk(split_name)
    for group in groups:
        tc.code.extend(_directed_group(test_data, group))
    return test_data.end_test_chunk()


@add_priv_test_generator(
    "ZicsrF",
    required_extensions=["Zicsr", "F"],
    march_extensions=["F", "D", "Zfh", "Zfa", "Zfbfmin"],
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
    test_chunks.append(_directed_chunk(test_data, "fma", _fma_groups()))
    test_chunks.append(_directed_chunk(test_data, "cvt", _cvt_groups()))
    test_chunks.append(_directed_chunk(test_data, "zfa", _zfa_groups()))
    return test_chunks
