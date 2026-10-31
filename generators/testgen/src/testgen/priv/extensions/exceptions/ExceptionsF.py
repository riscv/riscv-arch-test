##################################
# priv/extensions/exceptions/ExceptionsF.py
#
# ExceptionsF extension exception test generator.
# huahuang@hmc.edu Apr 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ExceptionsF test generator."""

from typing import Literal, NamedTuple

from testgen.asm.csr import gen_csr_read_sigupd, gen_csr_write_sigupd
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

# Values preset before each FS test, so a wrongly executed instruction changes them.
FD_MARKER = 0x0BADF00D
RD_MARKER = 0xB0BACAFE  # also the integer source; fcvt.s.w cannot convert it exactly (NX)
STORE_PATTERN = 0x0C0DE000
FCSR_PRESET = 0x8A  # frm = RMM, fflags = DZ|UF: each write form tested below changes it


class _FpOp(NamedTuple):
    """A floating-point instruction for the mstatus.FS tests."""

    name: str
    asm: str
    result: Literal["f", "x", "mem"]  # fd and fflags, rd and fflags, or stored memory
    guards: tuple[str, ...] = ()
    arch: str | None = None  # extension that only this instruction needs
    store_words: int = 0
    fs_off_only: bool = False


def _fp_ops(fd: int, rd: int, addr: int, snan_s: int, neg: int, zero: int, snan_d: int, snan_h: int) -> list[_FpOp]:
    """Instructions for the mstatus.FS tests. Arithmetic operands raise a flag if the instruction executes."""
    d = ("#ifdef D_SUPPORTED",)
    zfhmin = ("#ifdef ZFHMIN_SUPPORTED",)
    zfh = ("#ifdef ZFH_SUPPORTED",)
    # Sail does not support Q, so Q instructions are only tested where they must trap.
    q = ("#ifdef Q_SUPPORTED", "#if __riscv_xlen == 64")
    zcd = ("#ifdef ZCD_SUPPORTED",)
    zcf = ("#ifdef ZCF_SUPPORTED", "#if __riscv_xlen == 32")
    zfa = ("#ifdef ZFA_SUPPORTED",)
    zfa_d_rv32 = ("#ifdef ZFA_SUPPORTED", "#ifdef D_SUPPORTED", "#if __riscv_xlen == 32")
    return [
        _FpOp("fsw", f"fsw f{neg}, 0(x{addr})", "mem", store_words=1),
        _FpOp("flw", f"flw f{fd}, 0(x{addr})", "f"),
        _FpOp("fadd.s", f"fadd.s f{fd}, f{snan_s}, f{neg}", "f"),
        _FpOp("fsub.s", f"fsub.s f{fd}, f{snan_s}, f{neg}", "f"),
        _FpOp("fmul.s", f"fmul.s f{fd}, f{snan_s}, f{neg}", "f"),
        _FpOp("fdiv.s", f"fdiv.s f{fd}, f{neg}, f{zero}", "f"),
        _FpOp("fsgnj.s", f"fsgnj.s f{fd}, f{neg}, f{snan_s}", "f"),
        _FpOp("fmin.s", f"fmin.s f{fd}, f{snan_s}, f{neg}", "f"),
        _FpOp("fcvt.w.s", f"fcvt.w.s x{rd}, f{snan_s}", "x"),
        _FpOp("fcvt.s.w", f"fcvt.s.w f{fd}, x{rd}", "f"),
        _FpOp("fmadd.s", f"fmadd.s f{fd}, f{snan_s}, f{neg}, f{neg}", "f"),
        _FpOp("fsqrt.s", f"fsqrt.s f{fd}, f{neg}", "f"),
        _FpOp("feq.s", f"feq.s x{rd}, f{snan_s}, f{neg}", "x"),
        _FpOp("fmv.x.w", f"fmv.x.w x{rd}, f{snan_s}", "x"),
        _FpOp("fmv.w.x", f"fmv.w.x f{fd}, x{rd}", "f"),
        _FpOp("fclass.s", f"fclass.s x{rd}, f{snan_s}", "x"),
        _FpOp("fcvt.s.d", f"fcvt.s.d f{fd}, f{snan_d}", "f", d),
        _FpOp("fld", f"fld f{fd}, 0(x{addr})", "f", d),
        _FpOp("fsd", f"fsd f{neg}, 0(x{addr})", "mem", d, store_words=2),
        _FpOp("fadd.d", f"fadd.d f{fd}, f{snan_d}, f{snan_d}", "f", d),
        _FpOp("fcvt.d.s", f"fcvt.d.s f{fd}, f{snan_s}", "f", d),
        _FpOp("flh", f"flh f{fd}, 0(x{addr})", "f", zfhmin),
        _FpOp("fsh", f"fsh f{neg}, 0(x{addr})", "mem", zfhmin, store_words=1),
        _FpOp("fadd.h", f"fadd.h f{fd}, f{snan_h}, f{snan_h}", "f", zfh),
        _FpOp("flq", f"flq f{fd}, 0(x{addr})", "f", q, "q", fs_off_only=True),
        _FpOp("fsq", f"fsq f{neg}, 0(x{addr})", "mem", q, "q", store_words=4, fs_off_only=True),
        _FpOp("fadd.q", f"fadd.q f{fd}, f{neg}, f{neg}", "f", q, "q", fs_off_only=True),
        _FpOp("c.fld", f"c.fld f{fd}, 0(x{addr})", "f", zcd, "zcd"),
        _FpOp("c.fsd", f"c.fsd f{neg}, 0(x{addr})", "mem", zcd, "zcd", store_words=2),
        _FpOp("c.fldsp", f"c.fldsp f{fd}, 0(sp)", "f", zcd, "zcd"),
        _FpOp("c.fsdsp", f"c.fsdsp f{neg}, 0(sp)", "mem", zcd, "zcd", store_words=2),
        _FpOp("c.flw", f"c.flw f{fd}, 0(x{addr})", "f", zcf, "zcf"),
        _FpOp("c.fsw", f"c.fsw f{neg}, 0(x{addr})", "mem", zcf, "zcf", store_words=1),
        _FpOp("c.flwsp", f"c.flwsp f{fd}, 0(sp)", "f", zcf, "zcf"),
        _FpOp("c.fswsp", f"c.fswsp f{neg}, 0(sp)", "mem", zcf, "zcf", store_words=1),
        _FpOp("fround.s", f"fround.s f{fd}, f{snan_s}", "f", zfa),
        _FpOp("fli.s", f"fli.s f{fd}, 2.5", "f", zfa),
        _FpOp("fmvh.x.d_32", f"fmvh.x.d x{rd}, f{snan_d}", "x", zfa_d_rv32),
        _FpOp("fmvp.d.x_32", f"fmvp.d.x f{fd}, x{rd}, x{rd}", "f", zfa_d_rv32),
    ]


def add_fp_instructions(
    clear_mask_reg: int,
    set_mask_reg: int,
    fs_val: int,
    test_data: TestData,
    coverpoint: str,
    covergroup: str,
) -> list[str]:
    # Compressed loads and stores need x8-x15 and f8-f15.
    addr_reg = test_data.int_regs.get_register(reg_range=list(range(8, 16)))
    rd_reg, temp_reg = test_data.int_regs.get_registers(2)
    fd_reg, neg_reg = test_data.float_regs.get_registers(2, reg_range=list(range(8, 16)))
    snan_s_reg, zero_reg, snan_d_reg, snan_h_reg = test_data.float_regs.get_registers(4)

    t_lines = [
        f"LA(x{addr_reg}, scratch)",
        f"LI(x{temp_reg}, 0x7F800001)",
        f"fmv.w.x f{snan_s_reg}, x{temp_reg} # single signaling NaN",
        f"LI(x{temp_reg}, 0xBF800000)",
        f"fmv.w.x f{neg_reg}, x{temp_reg} # -1.0",
        f"fmv.w.x f{zero_reg}, x0 # +0.0",
        "#ifdef D_SUPPORTED",
        f"LI(x{temp_reg}, 1)",
        f"sw x{temp_reg}, 0(x{addr_reg})",
        f"LI(x{temp_reg}, 0x7FF00000)",
        f"sw x{temp_reg}, 4(x{addr_reg})",
        f"fld f{snan_d_reg}, 0(x{addr_reg}) # double signaling NaN",
        "#endif",
        "#ifdef ZFH_SUPPORTED",
        f"LI(x{temp_reg}, 0x7C01)",
        f"fmv.h.x f{snan_h_reg}, x{temp_reg} # half signaling NaN",
        "#endif",
    ]

    for op in _fp_ops(fd_reg, rd_reg, addr_reg, snan_s_reg, neg_reg, zero_reg, snan_d_reg, snan_h_reg):
        if op.fs_off_only and fs_val != 0:
            continue
        uses_sp = "(sp)" in op.asm
        t_lines.extend(
            [
                "",
                *op.guards,
                f"LI(x{rd_reg}, {RD_MARKER:#x})",
                f"LI(x{temp_reg}, {FD_MARKER:#x})",
                f"fmv.w.x f{fd_reg}, x{temp_reg}",
                "csrw fflags, x0",
            ]
        )
        if op.store_words:
            t_lines.append(f"LI(x{temp_reg}, {STORE_PATTERN:#x})")
            t_lines.extend(f"sw x{temp_reg}, {4 * i}(x{addr_reg})" for i in range(op.store_words))
        t_lines.extend(
            [
                tsbi_call(f"csrc mstatus, x{clear_mask_reg}"),
                tsbi_call(f"csrs mstatus, x{set_mask_reg}"),
            ]
        )
        if uses_sp:
            t_lines.extend([f"mv x{temp_reg}, sp", "LA(sp, scratch)"])
        t_lines.append(test_data.add_testcase(f"{op.name}_{fs_val}_{coverpoint[2:]}", coverpoint, covergroup))
        if op.arch is None:
            t_lines.append(op.asm)
        else:
            t_lines.extend([".option push", f".option arch, +{op.arch}", op.asm])
            if op.asm.startswith("c."):
                t_lines.append("c.nop # keep the code 4-byte aligned")
            t_lines.append(".option pop")
        if uses_sp:
            t_lines.append(f"mv sp, x{temp_reg}")
        if fs_val == 0:
            t_lines.append(tsbi_call(f"csrs mstatus, x{clear_mask_reg}"))  # FS on, so the checks can read FP state
        if op.result == "f":
            t_lines.append(write_sigupd(fd_reg, test_data, "float"))
        elif op.result == "x":
            t_lines.extend([write_sigupd(rd_reg, test_data), write_sigupd(None, test_data, "fflags")])
        else:
            for i in range(op.store_words):
                t_lines.extend([f"lw x{temp_reg}, {4 * i}(x{addr_reg})", write_sigupd(temp_reg, test_data)])
        t_lines.extend(["#endif"] * len(op.guards))

    test_data.int_regs.return_registers([addr_reg, rd_reg, temp_reg])
    test_data.float_regs.return_registers([fd_reg, neg_reg, snan_s_reg, zero_reg, snan_d_reg, snan_h_reg])
    return t_lines


def add_csr_instructions(
    clear_mask_reg: int,
    set_mask_reg: int,
    frm_reg: int,
    fs_val: int,
    test_data: TestData,
    coverpoint: str,
    covergroup: str,
) -> list[str]:
    check_reg = test_data.int_regs.get_register()

    t_lines = [
        tsbi_call(f"csrc mstatus, x{clear_mask_reg}"),
        tsbi_call(f"csrs mstatus, x{set_mask_reg}"),
        f"LI(x{check_reg}, 0)",
        test_data.add_testcase(f"csrw_fcsr_zero_{fs_val}_{coverpoint[2:]}", coverpoint, covergroup),
        gen_csr_write_sigupd(check_reg, "fcsr", test_data),
        "",
        tsbi_call(f"csrc mstatus, x{clear_mask_reg}"),
        tsbi_call(f"csrs mstatus, x{set_mask_reg}"),
        f"LI(x{check_reg}, -1)",
        test_data.add_testcase(f"csrrs_fcsr_{fs_val}_{coverpoint[2:]}", coverpoint, covergroup),
        f"csrrs x{check_reg}, fcsr, x{check_reg}",
        gen_csr_read_sigupd(check_reg, ("fcsr", None), test_data),
        "",
        tsbi_call(f"csrc mstatus, x{clear_mask_reg}"),
        tsbi_call(f"csrs mstatus, x{set_mask_reg}"),
        f"LI(x{check_reg}, -1)",
        test_data.add_testcase(f"csrrc_fcsr_{fs_val}_{coverpoint[2:]}", coverpoint, covergroup),
        f"csrrc x{check_reg}, fcsr, x{check_reg}",
        gen_csr_read_sigupd(check_reg, ("fcsr", None), test_data),
        "",
        tsbi_call(f"csrc mstatus, x{clear_mask_reg}"),
        tsbi_call(f"csrs mstatus, x{set_mask_reg}"),
        f"LI(x{check_reg}, 0)",
        test_data.add_testcase(f"csrw_frm_zero_{fs_val}_{coverpoint[2:]}", coverpoint, covergroup),
        gen_csr_write_sigupd(check_reg, "frm", test_data),
        "",
        tsbi_call(f"csrc mstatus, x{clear_mask_reg}"),
        tsbi_call(f"csrs mstatus, x{set_mask_reg}"),
        # frm is 0 here, from the csrw above, so this sets it to RMM
        test_data.add_testcase(f"csrrs_frm_{fs_val}_{coverpoint[2:]}", coverpoint, covergroup),
        f"csrrs x{check_reg}, frm, x{frm_reg}",
        gen_csr_read_sigupd(check_reg, ("frm", None), test_data),
        "",
        tsbi_call(f"csrc mstatus, x{clear_mask_reg}"),
        tsbi_call(f"csrs mstatus, x{set_mask_reg}"),
        # and this clears it back to 0
        test_data.add_testcase(f"csrrc_frm_{fs_val}_{coverpoint[2:]}", coverpoint, covergroup),
        f"csrrc x{check_reg}, frm, x{frm_reg}",
        gen_csr_read_sigupd(check_reg, ("frm", None), test_data),
        "",
        tsbi_call(f"csrc mstatus, x{clear_mask_reg}"),
        tsbi_call(f"csrs mstatus, x{set_mask_reg}"),
        f"LI(x{check_reg}, 0)",
        test_data.add_testcase(f"csrw_fflags_zero_{fs_val}_{coverpoint[2:]}", coverpoint, covergroup),
        gen_csr_write_sigupd(check_reg, "fflags", test_data),
        "",
        tsbi_call(f"csrc mstatus, x{clear_mask_reg}"),
        tsbi_call(f"csrs mstatus, x{set_mask_reg}"),
        f"LI(x{check_reg}, -1)",
        test_data.add_testcase(f"csrrs_fflags_{fs_val}_{coverpoint[2:]}", coverpoint, covergroup),
        f"csrrs x{check_reg}, fflags, x{check_reg}",
        gen_csr_read_sigupd(check_reg, ("fflags", None), test_data),
        "",
        tsbi_call(f"csrc mstatus, x{clear_mask_reg}"),
        tsbi_call(f"csrs mstatus, x{set_mask_reg}"),
        f"LI(x{check_reg}, -1)",
        test_data.add_testcase(f"csrrc_fflags_{fs_val}_{coverpoint[2:]}", coverpoint, covergroup),
        f"csrrc x{check_reg}, fflags, x{check_reg}",
        gen_csr_read_sigupd(check_reg, ("fflags", None), test_data),
    ]

    test_data.int_regs.return_register(check_reg)
    return t_lines


def add_fp_load_misaligned_test(
    op: str,
    offset: int,
    test_data: TestData,
    coverpoint: str,
    covergroup: str,
) -> list[str]:
    """Generate a single load-misaligned testcase."""
    addr_reg = test_data.int_regs.get_register()
    check_reg = test_data.float_regs.get_register()

    t_lines: list[str] = [
        f"LI(x{addr_reg}, 0xBEE{offset}CAFE)",
        f"fcvt.s.w f{check_reg}, x{addr_reg}",
        f"LA(x{addr_reg}, scratch)",
        f"addi x{addr_reg}, x{addr_reg}, {offset}",
    ]
    t_lines.extend(
        [
            test_data.add_testcase(f"{op}_off{offset}", coverpoint, covergroup),
            f"{op} f{check_reg}, 0(x{addr_reg})",
            write_sigupd(check_reg, test_data, sig_type="float"),
        ]
    )

    test_data.int_regs.return_register(addr_reg)
    test_data.float_regs.return_register(check_reg)
    return t_lines


def add_fp_store_misaligned_test(
    op: str,
    offset: int,
    test_data: TestData,
    coverpoint: str,
    covergroup: str,
) -> list[str]:
    addr_reg, check_reg = test_data.int_regs.get_registers(2)
    data_reg = test_data.float_regs.get_register()

    t_lines = [
        f"LI(x{check_reg}, 0xBEE{offset}CAFE)",
        f"fcvt.s.w f{data_reg}, x{check_reg}",
        f"LA(x{addr_reg}, scratch)",
        f"addi x{addr_reg}, x{addr_reg}, {offset}",
        test_data.add_testcase(f"{op}_off{offset}", coverpoint, covergroup),
        f"{op} f{data_reg}, 0(x{addr_reg})",
        # Read back scratch memory to verify store result
        f"LA(x{addr_reg}, scratch)",
    ]
    t_lines += [
        line
        for word_off in range(0, 24, 4)
        for line in (
            f"lw x{check_reg}, {word_off}(x{addr_reg})",
            write_sigupd(check_reg, test_data),
        )
    ]

    test_data.int_regs.return_registers([addr_reg, check_reg])
    test_data.float_regs.return_register(data_reg)
    return t_lines


def _generate_mstatus_fs_illegal_instr_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "Exceptions_F_cg", "cp_mstatus_fs_illegal_instr"
    clear_mask_reg, frm_reg, set_mask_reg = test_data.int_regs.get_registers(3)

    lines = [
        comment_banner(
            coverpoint,
            "Test that illegal instructions trap when mstatus.fs is set to 0 (Off)",
        ),
        f"LI(x{clear_mask_reg}, 0x6000) # MSTATUS_FS mask",
        f"LI(x{set_mask_reg}, 0) # MSTATUS_FS = Off",
        f"LI(x{frm_reg}, 0)",
    ]

    lines.extend(add_fp_instructions(clear_mask_reg, set_mask_reg, 0, test_data, coverpoint, covergroup))
    test_data.int_regs.return_registers([clear_mask_reg, frm_reg, set_mask_reg])
    return lines


def _generate_mstatus_fs_csr_access_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "Exceptions_F_cg", "cp_mstatus_fs_csr_access"
    mstatus_fs_mask_reg, check_reg = test_data.int_regs.get_registers(2)

    lines = [
        comment_banner(
            coverpoint,
            "Test that access to floating point CSRs trap when mstatus.fs is set to 0 (Off)",
        ),
        f"LI(x{mstatus_fs_mask_reg}, 0x6000) # MSTATUS_FS mask",
    ]

    for csr in ["fcsr", "frm", "fflags"]:
        # csrrsi and csrrci with uimm=0 only read the CSR, but must still trap.
        accesses = [
            ("csrr", f"csrr x{check_reg}, {csr}"),
            ("csrw", f"csrw {csr}, x{check_reg}"),
            ("csrc", f"csrc {csr}, x{check_reg}"),
            ("csrs", f"csrs {csr}, x{check_reg}"),
            ("csrrwi", f"csrrwi x{check_reg}, {csr}, 1"),
            ("csrrsi", f"csrrsi x{check_reg}, {csr}, 0"),
            ("csrrci", f"csrrci x{check_reg}, {csr}, 0"),
        ]
        for csr_instr, asm in accesses:
            lines.extend(
                [
                    f"LI(x{check_reg}, {FCSR_PRESET:#x})",
                    f"csrw fcsr, x{check_reg}",
                    tsbi_call(f"csrc mstatus, x{mstatus_fs_mask_reg}"),
                    f"LI(x{check_reg}, -1)",
                    test_data.add_testcase(f"{csr_instr}_{csr}_00_{coverpoint[2:]}", coverpoint, covergroup),
                    asm,
                    "# Need to enable mstatus.FS so that the csrs can be accessed",
                    tsbi_call(f"csrs mstatus, x{mstatus_fs_mask_reg}"),
                ]
            )
            if asm.startswith(("csrr ", "csrrwi", "csrrsi", "csrrci")):
                lines.append(write_sigupd(check_reg, test_data))
            lines.append(gen_csr_read_sigupd(check_reg, (csr, None), test_data))

    test_data.int_regs.return_registers([mstatus_fs_mask_reg, check_reg])
    return lines


def _generate_mstatus_fs_legal_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "Exceptions_F_cg", "cp_mstatus_fs_legal"
    clear_mask_reg, frm_reg, set_mask_reg = test_data.int_regs.get_registers(3)

    lines = [
        comment_banner(coverpoint, "Test that instructions execute correctly when mstatus.fs is set to 1 (Clean)\n"),
        f"LI(x{clear_mask_reg}, 0x6000) # MSTATUS_FS mask",
        # rs1 for the csrrs/csrrc frm cases below. Must be non-zero, or they set and clear
        # nothing, and must leave frm legal: 5-7 are reserved rounding modes.
        f"LI(x{frm_reg}, 0b100) # frm = RMM, a legal rounding mode",
    ]

    for i in range(1, 4):
        lines.append(f"LI(x{set_mask_reg}, {i << 13}) # mstatus.FS = {i}")
        lines.extend(add_csr_instructions(clear_mask_reg, set_mask_reg, frm_reg, i, test_data, coverpoint, covergroup))
        lines.extend(add_fp_instructions(clear_mask_reg, set_mask_reg, i, test_data, coverpoint, covergroup))
    test_data.int_regs.return_registers([clear_mask_reg, frm_reg, set_mask_reg])
    return lines


def _generate_load_address_misaligned_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "Exceptions_F_cg", "cp_load_address_misaligned"

    lines = [
        comment_banner(
            coverpoint,
            "Test load instructions on misaligned addresses to check for traps\nTesting all offsets upto 16",
        ),
    ]

    for offset in range(16):
        lines.append(f"\n# Testcase: flw with offset {offset} (LSBs: {offset:04b})")
        lines.extend(add_fp_load_misaligned_test("flw", offset, test_data, coverpoint, covergroup))

        lines.append("#ifdef D_SUPPORTED")
        lines.append(f"\n# Testcase: fld with offset {offset} (LSBs: {offset:04b})")
        lines.extend(add_fp_load_misaligned_test("fld", offset, test_data, coverpoint, covergroup))
        lines.append("#endif\n")

        lines.append("#ifdef ZFHMIN_SUPPORTED")
        lines.append(f"\n# Testcase: flh with offset {offset} (LSBs: {offset:04b})")
        lines.extend(add_fp_load_misaligned_test("flh", offset, test_data, coverpoint, covergroup))
        lines.append("#endif")

        # lines.append("#ifdef Q_SUPPORTED")
        # lines.append(f"\n# Testcase: flq with offset {offset} (LSBs: {offset:04b})")
        # lines.extend(add_fp_load_misaligned_test("flq", offset, test_data, coverpoint, covergroup))
        # lines.append("#endif")

    return lines


def _generate_load_access_fault_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "Exceptions_F_cg", "cp_load_access_fault"

    lines = [
        comment_banner(
            coverpoint,
            "Test load instructions on access fault addresses to check for traps",
        ),
    ]
    addr_reg = test_data.int_regs.get_register()
    check_reg = test_data.float_regs.get_register()

    lines.append("#ifdef RVMODEL_ACCESS_FAULT_ADDRESS")
    lines.extend(
        [
            f"LI(x{addr_reg}, 0xBEE1CAFE)",
            f"fcvt.s.w f{check_reg}, x{addr_reg}",
            f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
        ]
    )
    lines.extend(
        [
            test_data.add_testcase("flw_fault", coverpoint, covergroup),
            f"flw f{check_reg}, 0(x{addr_reg})",
        ]
    )

    lines.extend(
        [
            "#ifdef D_SUPPORTED",
            test_data.add_testcase("fld_fault", coverpoint, covergroup),
            f"fld f{check_reg}, 0(x{addr_reg})",
            "",
            "#endif",
            "",
        ]
    )

    lines.extend(
        [
            "#ifdef ZFHMIN_SUPPORTED",
            test_data.add_testcase("flh_fault", coverpoint, covergroup),
            f"flh f{check_reg}, 0(x{addr_reg})",
            "#endif",
            "",
        ]
    )

    lines.extend(
        [
            # "#ifdef Q_SUPPORTED",
            # test_data.add_testcase("flq_fault", coverpoint, covergroup),
            # f"flq f{check_reg}, 0(x{addr_reg})",
            # "nop",
            # "",
            # "#endif",
            "#endif // RVMODEL_ACCESS_FAULT_ADDRESS",
            "",
        ]
    )
    test_data.int_regs.return_register(addr_reg)
    test_data.float_regs.return_register(check_reg)
    return lines


def _generate_store_address_misaligned_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "Exceptions_F_cg", "cp_store_address_misaligned"

    lines = [
        comment_banner(
            coverpoint,
            "Test store instructions on misaligned addresses to check for traps\nTesting all offsets upto 16",
        ),
    ]

    for offset in range(16):
        lines.append(f"\n# Testcase: fsw with offset {offset} (LSBs: {offset:04b})")
        lines.extend(add_fp_store_misaligned_test("fsw", offset, test_data, coverpoint, covergroup))

        lines.append("#ifdef D_SUPPORTED")
        lines.append(f"\n# Testcase: fsd with offset {offset} (LSBs: {offset:04b})")
        lines.extend(add_fp_store_misaligned_test("fsd", offset, test_data, coverpoint, covergroup))
        lines.append("#endif\n")

        lines.append("#ifdef ZFHMIN_SUPPORTED")
        lines.append(f"\n# Testcase: fsh with offset {offset} (LSBs: {offset:04b})")
        lines.extend(add_fp_store_misaligned_test("fsh", offset, test_data, coverpoint, covergroup))
        lines.append("#endif")

        # lines.append("#ifdef Q_SUPPORTED")
        # lines.append(f"\n# Testcase: fsq with offset {offset} (LSBs: {offset:04b})")
        # lines.extend(add_fp_store_misaligned_test("fsq", offset, test_data, coverpoint, covergroup))
        # lines.append("#endif")

    return lines


def _generate_store_access_fault_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "Exceptions_F_cg", "cp_store_access_fault"

    lines = [
        comment_banner(
            coverpoint,
            "Test store instructions on access fault addresses to check for traps",
        ),
    ]

    addr_reg = test_data.int_regs.get_register()
    data_reg = test_data.float_regs.get_register()

    lines.append("#ifdef RVMODEL_ACCESS_FAULT_ADDRESS")
    lines.extend(
        [
            f"LI(x{addr_reg}, 0xBEE1CAFE)",
            f"fcvt.s.w f{data_reg}, x{addr_reg}",
            f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
        ]
    )
    lines.extend(
        [
            test_data.add_testcase("fsw_fault", coverpoint, covergroup),
            f"fsw f{data_reg}, 0(x{addr_reg})",
        ]
    )

    lines.extend(
        [
            "",
            "#ifdef D_SUPPORTED",
            test_data.add_testcase("fsd_fault", coverpoint, covergroup),
            f"fsd f{data_reg}, 0(x{addr_reg})",
            "#endif",
        ]
    )

    lines.extend(
        [
            "#ifdef ZFHMIN_SUPPORTED",
            test_data.add_testcase("fsh_fault", coverpoint, covergroup),
            f"fsh f{data_reg}, 0(x{addr_reg})",
            "#endif",
        ]
    )

    lines.extend(
        [
            # "#ifdef Q_SUPPORTED",
            # test_data.add_testcase("fsq_fault", coverpoint, covergroup),
            # f"fsq f{data_reg}, 0(x{addr_reg})",
            # "nop",
            # "",
            # "#endif",
            "#endif // RVMODEL_ACCESS_FAULT_ADDRESS",
            "",
        ]
    )
    test_data.int_regs.return_register(addr_reg)
    test_data.float_regs.return_register(data_reg)
    return lines


@add_priv_test_generator(
    "Exceptions",
    required_extensions=["F", ["Sm", "U"]],
    march_extensions=["Zfa", "D", "Zfhmin", "Zfh"],
)
def make_exceptionsf(test_data: TestData) -> list[TestChunk]:
    """Main entry point for F exception test generation."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk("F")

    # initialize fp registers
    init_reg = test_data.int_regs.get_register()
    for i in range(32):
        tc.code.extend(
            [
                f"LI(x{init_reg}, {i + 1})",
                f"fcvt.s.w f{i}, x{init_reg}",
            ]
        )
    test_data.int_regs.return_register(init_reg)

    tc.code.extend(_generate_mstatus_fs_illegal_instr_tests(test_data))
    tc.code.extend(_generate_mstatus_fs_csr_access_tests(test_data))
    tc.code.extend(_generate_mstatus_fs_legal_tests(test_data))
    tc.code.extend(_generate_load_address_misaligned_tests(test_data))
    tc.code.extend(_generate_load_access_fault_tests(test_data))
    tc.code.extend(_generate_store_address_misaligned_tests(test_data))
    tc.code.extend(_generate_store_access_fault_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
