##################################
# priv/extensions/ExceptionsF.py
#
# ExceptionsF extension exception test generator.
# huahuang@hmc.edu Apr 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ExceptionsF test generator."""

from testgen.asm.csr import gen_csr_read_sigupd, gen_csr_write_sigupd
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def add_fp_instructions(
    clear_mask_reg: int,
    set_mask_reg: int,
    fs_val: int,
    test_data: TestData,
    coverpoint: str,
    covergroup: str,
) -> list[str]:
    int_reg1, int_reg2 = test_data.int_regs.get_registers(2)
    dest_fp_reg, source_reg1, source_reg2, source_reg3 = test_data.float_regs.get_registers(4)
    t_lines = []
    t_lines.extend(
        [
            test_data.add_testcase(f"fsw_{fs_val}_{coverpoint[2:]}", coverpoint, covergroup),
            f"csrc mstatus, x{clear_mask_reg}",
            f"csrs mstatus, x{set_mask_reg}",
            f"LA(x{int_reg2}, scratch)",
            f"addi x{int_reg2}, x{int_reg2}, 2",
            f"fsw f{source_reg1}, 0(x{int_reg2})",
            "nop",
            write_sigupd(source_reg1, test_data, "float"),
            test_data.add_testcase(f"flw_{fs_val}_{coverpoint[2:]}", coverpoint, covergroup),
            f"csrc mstatus, x{clear_mask_reg}",
            f"csrs mstatus, x{set_mask_reg}",
            f"LA(x{int_reg2}, scratch)",
            f"addi x{int_reg2}, x{int_reg2}, 2",
            f"flw f{source_reg2}, 0(x{int_reg2})",
            "nop",
            write_sigupd(source_reg2, test_data, "float"),
        ]
    )

    ops = [
        "fadd.s",
        "fsub.s",
        "fmul.s",
        "fdiv.s",
        "fsgnj.s",
        "fmin.s",
        "fcvt.w.s",
        "fcvt.s.w",
        "fmadd.s",
        "fsqrt.s",
        "feq.s",
        "fmv.x.w",
        "fmv.w.x",
        "fclass.s",
    ]

    for op in ops:
        t_lines.extend(
            [
                f"LI(x{int_reg2}, 0xB0BACAFE)",
                f"csrc mstatus, x{clear_mask_reg}",
                f"csrs mstatus, x{set_mask_reg}",
                test_data.add_testcase(f"{op}_{fs_val}_{coverpoint[2:]}", coverpoint, covergroup),
            ]
        )
        if op in ["fadd.s", "fsub.s", "fmul.s", "fdiv.s", "fsgnj.s", "fmin.s"]:
            t_lines.extend(
                [
                    f"{op} f{dest_fp_reg}, f{source_reg1}, f{source_reg2}",
                    "nop",
                    write_sigupd(dest_fp_reg, test_data, "float"),
                ]
            )
        elif op in ["fcvt.w.s", "fmv.x.w", "fclass.s"]:
            t_lines.extend(
                [
                    f"{op} x{int_reg1}, f{source_reg1}",
                    "nop",
                    write_sigupd(int_reg1, test_data),
                ]
            )
        elif op in ["fcvt.s.w", "fmv.w.x"]:
            t_lines.extend(
                [
                    f"{op} f{dest_fp_reg}, x{int_reg1}",
                    "nop",
                    write_sigupd(dest_fp_reg, test_data, "float"),
                ]
            )
        elif op in ["fsqrt.s"]:
            t_lines.extend(
                [
                    f"{op} f{dest_fp_reg}, f{source_reg1}",
                    "nop",
                    write_sigupd(dest_fp_reg, test_data, "float"),
                ]
            )
        elif op in ["fmadd.s"]:
            t_lines.extend(
                [
                    f"{op} f{dest_fp_reg}, f{source_reg1}, f{source_reg2}, f{source_reg3}",
                    "nop",
                    write_sigupd(dest_fp_reg, test_data, "float"),
                ]
            )
        elif op in ["feq.s"]:
            t_lines.extend(
                [
                    f"{op} x{int_reg1}, f{source_reg1}, f{source_reg2}",
                    "nop",
                    write_sigupd(int_reg1, test_data),
                ]
            )

    t_lines.append("#ifdef D_SUPPORTED")
    t_lines.extend(
        [
            test_data.add_testcase(f"fcvt.s.d_{fs_val}_{coverpoint[2:]}", coverpoint, covergroup),
            f"csrc mstatus, x{clear_mask_reg}",
            f"csrs mstatus, x{set_mask_reg}",
            f"LI(x{int_reg2}, 0xB0BACAFE)",
            f"fcvt.s.d f{dest_fp_reg}, f{source_reg1}",
            "nop",
            write_sigupd(dest_fp_reg, test_data, "float"),
        ]
    )
    t_lines.append("#endif")

    t_lines.append("#ifdef ZFA_SUPPORTED")
    zfa_ops = ["fround.s", "fli.s"]
    for op in zfa_ops:
        t_lines.extend(
            [
                test_data.add_testcase(f"{op}_{fs_val}_{coverpoint[2:]}", coverpoint, covergroup),
                f"csrc mstatus, x{clear_mask_reg}",
                f"csrs mstatus, x{set_mask_reg}",
            ]
        )
        if op == "fround.s":
            t_lines.extend(
                [
                    f"{op} f{dest_fp_reg}, f{source_reg1}",
                    "nop",
                    write_sigupd(dest_fp_reg, test_data, "float"),
                ]
            )
        elif op == "fli.s":
            t_lines.extend(
                [
                    f"{op} f{dest_fp_reg}, 2.5",
                    "nop",
                    write_sigupd(dest_fp_reg, test_data, "float"),
                ]
            )
    op32 = ["fmvh.x.d", "fmvp.d.x"]
    t_lines.append("#if __riscv_xlen == 32")
    t_lines.append("#ifdef D_SUPPORTED")
    for op in op32:
        t_lines.extend(
            [
                test_data.add_testcase(f"{op}_32_{fs_val}_{coverpoint[2:]}", coverpoint, covergroup),
                f"csrc mstatus, x{clear_mask_reg}",
                f"csrs mstatus, x{set_mask_reg}",
            ]
        )
        if op == "fmvh.x.d":
            t_lines.extend(
                [
                    f"{op} x{int_reg1}, f{source_reg1}",
                    "nop",
                    write_sigupd(int_reg1, test_data),
                ]
            )
        elif op == "fmvp.d.x":
            t_lines.extend(
                [
                    f"{op} f{dest_fp_reg}, x{int_reg1}, x{int_reg2}",
                    "nop",
                    write_sigupd(dest_fp_reg, test_data, "float"),
                ]
            )
    t_lines.append("#endif // D_SUPPORTED")
    t_lines.append("#endif // __riscv_xlen == 32")
    t_lines.append("#endif // ZFA_SUPPORTED")

    test_data.int_regs.return_registers([int_reg1, int_reg2])
    test_data.float_regs.return_registers([dest_fp_reg, source_reg1, source_reg2, source_reg3])
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
        f"csrc mstatus, x{clear_mask_reg}",
        f"csrs mstatus, x{set_mask_reg}",
        f"LI(x{check_reg}, 0)",
        test_data.add_testcase(f"csrw_fcsr_zero_{fs_val}_{coverpoint[2:]}", coverpoint, covergroup),
        gen_csr_write_sigupd(check_reg, "fcsr", test_data),
        f"csrc mstatus, x{clear_mask_reg}",
        f"csrs mstatus, x{set_mask_reg}",
        f"LI(x{check_reg}, -1)",
        test_data.add_testcase(f"csrrs_fcsr_{fs_val}_{coverpoint[2:]}", coverpoint, covergroup),
        f"CSRRS(x{check_reg}, fcsr, x{check_reg})",
        gen_csr_read_sigupd(check_reg, ("fcsr", None), test_data),
        f"csrc mstatus, x{clear_mask_reg}",
        f"csrs mstatus, x{set_mask_reg}",
        f"LI(x{check_reg}, -1)",
        test_data.add_testcase(f"csrrc_fcsr_{fs_val}_{coverpoint[2:]}", coverpoint, covergroup),
        f"CSRRC(x{check_reg}, fcsr, x{check_reg})",
        gen_csr_read_sigupd(check_reg, ("fcsr", None), test_data),
        "",
        f"csrc mstatus, x{clear_mask_reg}",
        f"csrs mstatus, x{set_mask_reg}",
        f"LI(x{check_reg}, 0)",
        test_data.add_testcase(f"csrw_frm_zero_{fs_val}_{coverpoint[2:]}", coverpoint, covergroup),
        gen_csr_write_sigupd(check_reg, "frm", test_data),
        f"csrc mstatus, x{clear_mask_reg}",
        f"csrs mstatus, x{set_mask_reg}",
        f"LI(x{check_reg}, -1)",
        test_data.add_testcase(f"csrrs_frm_{fs_val}_{coverpoint[2:]}", coverpoint, covergroup),
        f"CSRRS(x{check_reg}, frm, x{frm_reg})",
        gen_csr_read_sigupd(check_reg, ("frm", None), test_data),
        f"csrc mstatus, x{clear_mask_reg}",
        f"csrs mstatus, x{set_mask_reg}",
        f"LI(x{check_reg}, 0)",
        test_data.add_testcase(f"csrrc_frm_{fs_val}_{coverpoint[2:]}", coverpoint, covergroup),
        f"CSRRC(x{check_reg}, frm, x{frm_reg})",
        gen_csr_read_sigupd(check_reg, ("frm", None), test_data),
        "",
        f"LI(x{check_reg}, 0)",
        f"csrc mstatus, x{clear_mask_reg}",
        f"csrs mstatus, x{set_mask_reg}",
        f"LI(x{check_reg}, 0)",
        test_data.add_testcase(f"csrw_fflags_zero_{fs_val}_{coverpoint[2:]}", coverpoint, covergroup),
        gen_csr_write_sigupd(check_reg, "fflags", test_data),
        f"csrc mstatus, x{clear_mask_reg}",
        f"csrs mstatus, x{set_mask_reg}",
        f"LI(x{check_reg}, -1)",
        test_data.add_testcase(f"csrrs_fflags_{fs_val}_{coverpoint[2:]}", coverpoint, covergroup),
        f"CSRRS(x{check_reg}, fflags, x{check_reg})",
        gen_csr_read_sigupd(check_reg, ("fflags", None), test_data),
        f"csrc mstatus, x{clear_mask_reg}",
        f"csrs mstatus, x{set_mask_reg}",
        f"LI(x{check_reg}, -1)",
        test_data.add_testcase(f"csrrc_fflags_{fs_val}_{coverpoint[2:]}", coverpoint, covergroup),
        f"CSRRC(x{check_reg}, fflags, x{check_reg})",
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
            "nop",
            write_sigupd(check_reg, test_data),
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
    addr_reg, check_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])
    data_reg = test_data.float_regs.get_register()

    t_lines = [
        f"LI(x{check_reg}, 0xBEE{offset}CAFE)",
        f"fcvt.s.w f{data_reg}, x{check_reg}",
        f"LA(x{addr_reg}, scratch)",
        f"addi x{addr_reg}, x{addr_reg}, {offset}",
        test_data.add_testcase(f"{op}_off{offset}", coverpoint, covergroup),
        f"{op} f{data_reg}, 0(x{addr_reg})",
        "nop",
        # Read back scratch memory to verify store result
        f"LA(x{addr_reg}, scratch)",
        f"lw x{check_reg}, 0(x{addr_reg})",
        write_sigupd(check_reg, test_data),
        f"lw x{check_reg}, 4(x{addr_reg})",
        write_sigupd(check_reg, test_data),
        f"lw x{check_reg}, 8(x{addr_reg})",
        write_sigupd(check_reg, test_data),
        f"lw x{check_reg}, 12(x{addr_reg})",
        write_sigupd(check_reg, test_data),
    ]

    test_data.int_regs.return_registers([addr_reg, check_reg])
    test_data.float_regs.return_register(data_reg)
    return t_lines


def _generate_mstatus_fs_illegal_instr_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsF_cg", "cp_mstatus_fs_illegal_instr"
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


def _generate_mstatus_fs_csr_write_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsF_cg", "cp_mstatus_fs_csr_write"
    clear_mask_reg, frm_reg, set_mask_reg = test_data.int_regs.get_registers(3)

    lines = [
        comment_banner(
            coverpoint,
            "Test that access to floating point CSRs trap when mstatus.fs is set to 0 (Off)",
        ),
        f"LI(x{clear_mask_reg}, 0x6000) # MSTATUS_FS mask",
        f"LI(x{set_mask_reg}, 0) # MSTATUS_FS = Off",
        f"LI(x{frm_reg}, 0)",
    ]

    lines.extend(add_csr_instructions(clear_mask_reg, set_mask_reg, frm_reg, 0, test_data, coverpoint, covergroup))
    test_data.int_regs.return_registers([clear_mask_reg, frm_reg, set_mask_reg])
    return lines


def _generate_mstatus_fs_legal_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsF_cg", "cp_mstatus_fs_legal"
    clear_mask_reg, frm_reg, set_mask_reg = test_data.int_regs.get_registers(3)

    lines = [
        comment_banner(coverpoint, "Test that instructions execute correctly when mstatus.fs is set to 1 (Clean)\n"),
        f"LI(x{clear_mask_reg}, 0x6000) # MSTATUS_FS mask",
        f"LI(x{frm_reg}, 0)",
    ]

    for i in range(1, 4):
        lines.append(f"LI(x{set_mask_reg}, {i << 13}) # mstatus.FS = {i}")
        lines.extend(add_csr_instructions(clear_mask_reg, set_mask_reg, frm_reg, i, test_data, coverpoint, covergroup))
        lines.extend(add_fp_instructions(clear_mask_reg, set_mask_reg, i, test_data, coverpoint, covergroup))
    test_data.int_regs.return_registers([clear_mask_reg, frm_reg, set_mask_reg])
    return lines


def _generate_load_address_misaligned_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsF_cg", "cp_load_address_misaligned"

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
    covergroup, coverpoint = "ExceptionsF_cg", "cp_load_access_fault"

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
            "nop",
        ]
    )

    lines.extend(
        [
            "#ifdef D_SUPPORTED",
            test_data.add_testcase("fld_fault", coverpoint, covergroup),
            f"fld f{check_reg}, 0(x{addr_reg})",
            "nop",
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
            "nop",
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
    covergroup, coverpoint = "ExceptionsF_cg", "cp_store_address_misaligned"

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
    covergroup, coverpoint = "ExceptionsF_cg", "cp_store_access_fault"

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
            "nop",
        ]
    )

    lines.extend(
        [
            "",
            "#ifdef D_SUPPORTED",
            test_data.add_testcase("fsd_fault", coverpoint, covergroup),
            f"fsd f{data_reg}, 0(x{addr_reg})",
            "nop",
            "#endif",
        ]
    )

    lines.extend(
        [
            "#ifdef ZFHMIN_SUPPORTED",
            test_data.add_testcase("fsh_fault", coverpoint, covergroup),
            f"fsh f{data_reg}, 0(x{addr_reg})",
            "nop",
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
    "ExceptionsF",
    required_extensions=[
        "F",
        "Sm",
    ],  # Some priv mode is needed to set up trap handler.  Generalize so that this could run in U mode in the future.  Applies to many other Exceptions tests.
    march_extensions=["Zfa", "D", "Zfhmin"],
)
def make_exceptionsf(test_data: TestData) -> list[str]:
    """Main entry point for F exception test generation."""

    lines = []

    # initialize fp registers
    for i in range(32):
        lines.extend(
            [
                f"li t0, {i + 1}",
                f"fcvt.s.w f{i}, t0",
            ]
        )

    lines.extend(_generate_mstatus_fs_illegal_instr_tests(test_data))
    lines.extend(_generate_mstatus_fs_csr_write_tests(test_data))
    lines.extend(_generate_mstatus_fs_legal_tests(test_data))
    lines.extend(_generate_load_address_misaligned_tests(test_data))
    lines.extend(_generate_load_access_fault_tests(test_data))
    lines.extend(_generate_store_address_misaligned_tests(test_data))
    lines.extend(_generate_store_access_fault_tests(test_data))
    return lines
