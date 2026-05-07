##################################
# priv/extensions/ExceptionsF.py
#
# ExceptionsF extension exception test generator.
# huahuang@hmc.edu Apr 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ExceptionsF test generator."""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def add_fp_instructions(
    clear_mask_reg: int,
    set_mask_reg: int,
    frm_reg: int,
    fs_val: int,
    test_data: TestData,
    coverpoint: str,
    covergroup: str,
    bad_frm: bool = False,
) -> list[str]:
    int_reg1, int_reg2 = test_data.int_regs.get_registers(2)
    dest_fp_reg, source_reg1, source_reg2, source_reg3 = test_data.float_regs.get_registers(4)
    t_lines = []
    ops = [
        "fsw",
        "flw",
        "fadd.s",
        "fsub.s",
        "fmul.s",
        "fdiv.s",
        "fcvt.w.s",
        "fcvt.s.w",
        "fcvt.s.d",
        "fmadd.s",
        "fsqrt.s",
        "fsgnj.s",
        "feq.s",
        "fmv.x.w",
        "fmv.w.x",
        "fclass.s",
        "fmin.s",
    ]
    for op in ops:
        if op in ("fsw", "flw"):
            addr_setup = [f"LA(x{int_reg2}, scratch)", f"addi x{int_reg2}, x{int_reg2}, 2"]
        else:
            addr_setup = [f"LI(x{int_reg2}, 0xB0BACAFE)"]
        t_lines.extend(
            [
                test_data.add_testcase(f"{op}_{fs_val}_{coverpoint[2:]}", coverpoint, covergroup),
                f"csrc mstatus, x{clear_mask_reg}",
                f"csrs mstatus, x{set_mask_reg}",
            ]
        )
        if bad_frm:
            t_lines.extend([f"csrw frm, x{frm_reg}", "nop"])
        t_lines.extend(addr_setup)
        if op == "fsw":
            t_lines.extend(
                [
                    f"{op} f{source_reg1}, 0(x{int_reg2})",
                    "nop",
                    write_sigupd(source_reg1, test_data),
                ]
            )
        elif op == "flw":
            t_lines.extend(
                [
                    f"{op} f{source_reg2}, 0(x{int_reg2})",
                    "nop",
                    write_sigupd(source_reg2, test_data),
                ]
            )
        elif op in ["fadd.s", "fsub.s", "fmul.s", "fdiv.s", "fsgnj.s", "fmin.s"]:
            inst = f"{op} f{dest_fp_reg}, f{source_reg1}, f{source_reg2}"
            if bad_frm and op in ("fadd.s", "fsub.s", "fmul.s", "fdiv.s"):
                inst = f"{inst}, rne"
            t_lines.extend(
                [
                    inst,
                    "nop",
                    write_sigupd(dest_fp_reg, test_data),
                ]
            )
        elif op in ["fcvt.w.s", "fmv.x.w", "fclass.s"]:
            inst = f"{op} x{int_reg1}, f{source_reg1}"
            if bad_frm and op == "fcvt.w.s":
                inst = f"{inst}, rne"
            t_lines.extend(
                [
                    inst,
                    "nop",
                    write_sigupd(int_reg1, test_data),
                ]
            )
        elif op in ["fcvt.s.w", "fmv.w.x"]:
            inst = f"{op} f{dest_fp_reg}, x{int_reg1}"
            if bad_frm and op == "fcvt.s.w":
                inst = f"{inst}, rne"
            t_lines.extend(
                [
                    inst,
                    "nop",
                    write_sigupd(dest_fp_reg, test_data),
                ]
            )
        elif op in ["fcvt.s.d", "fsqrt.s"]:
            inst = f"{op} f{dest_fp_reg}, f{source_reg1}"
            if bad_frm:
                inst = f"{inst}, rne"
            t_lines.extend(
                [
                    inst,
                    "nop",
                    write_sigupd(dest_fp_reg, test_data),
                ]
            )
        elif op in ["fmadd.s"]:
            inst = f"{op} f{dest_fp_reg}, f{source_reg1}, f{source_reg2}, f{source_reg3}"
            if bad_frm:
                inst = f"{inst}, rne"
            t_lines.extend(
                [
                    inst,
                    "nop",
                    write_sigupd(dest_fp_reg, test_data),
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

    t_lines.extend(["#ifdef ZFA_SUPPORTED"])
    zfa_ops = ["fround.s", "fli.s"]
    for op in zfa_ops:
        t_lines.extend(
            [
                test_data.add_testcase(f"{op}_{fs_val}_{coverpoint[2:]}", coverpoint, covergroup),
                f"csrc mstatus, x{clear_mask_reg}",
                f"csrs mstatus, x{set_mask_reg}",
            ]
        )
        if bad_frm:
            t_lines.extend([f"csrw frm, x{frm_reg}", "nop"])
        if op == "fround.s":
            inst = f"{op} f{dest_fp_reg}, f{source_reg1}"
            if bad_frm:
                inst = f"{inst}, rne"
            t_lines.extend(
                [
                    inst,
                    "nop",
                    write_sigupd(dest_fp_reg, test_data),
                ]
            )
        elif op == "fli.s":
            t_lines.extend(
                [
                    f"{op} f{dest_fp_reg}, 2.5",
                    "nop",
                    write_sigupd(dest_fp_reg, test_data),
                ]
            )
    t_lines.append("#endif")

    op32 = ["fmv.x.w", "fmvh.x.d", "fmvp.d.x"]
    t_lines.append("#if __riscv_xlen == 32")
    for op in op32:
        t_lines.extend(
            [
                test_data.add_testcase(f"{op}_32_{fs_val}_{coverpoint[2:]}", coverpoint, covergroup),
                f"csrc mstatus, x{clear_mask_reg}",
                f"csrs mstatus, x{set_mask_reg}",
            ]
        )
        if bad_frm:
            t_lines.extend([f"csrw frm, x{frm_reg}", "nop"])

        if op == "fmv.x.w":
            t_lines.extend(
                [
                    f"{op} x{int_reg1}, f{source_reg1}",
                    "nop",
                    write_sigupd(int_reg1, test_data),
                ]
            )
        elif op == "fmvh.x.d":
            t_lines.extend([f"{op} x{int_reg1}, f{source_reg1}", "nop"])
            if bad_frm:
                t_lines.append(f"LI(x{int_reg1}, 0)")
            t_lines.append(write_sigupd(int_reg1, test_data))
        elif op == "fmvp.d.x":
            t_lines.extend(
                [
                    f"{op} f{dest_fp_reg}, x{int_reg1}, x{int_reg2}",
                    "nop",
                    write_sigupd(dest_fp_reg, test_data),
                ]
            )
    t_lines.append("#endif")

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
    bad_frm: bool = False,
) -> list[str]:
    check_reg = test_data.int_regs.get_register()

    t_lines = [
        test_data.add_testcase(f"csr_{fs_val}_{coverpoint[2:]}", coverpoint, covergroup),
    ]
    if fs_val == 1:
        t_lines.extend(
            [
                f"LI(x{check_reg}, 0)",
                f"csrw fcsr, x{check_reg}",
                "nop",
            ]
        )
    t_lines.extend(
        [
            f"csrc mstatus, x{clear_mask_reg}",
            "nop",
            f"csrs mstatus, x{set_mask_reg}",
            "nop",
            f"csrw frm, x{frm_reg}",
            "nop",
        ]
    )
    if not bad_frm:
        t_lines.extend(
            [
                f"csrc mstatus, x{clear_mask_reg}",
                "nop",
                f"csrs mstatus, x{set_mask_reg}",
                "nop",
            ]
        )

    t_lines.extend(
        [
            f"csrrw x{check_reg}, fcsr, x0",
            "nop",
            write_sigupd(check_reg, test_data),
            f"csrw frm, x{frm_reg}",
            "nop",
        ]
    )
    if not bad_frm:
        t_lines.extend(
            [
                f"csrc mstatus, x{clear_mask_reg}",
                "nop",
                f"csrs mstatus, x{set_mask_reg}",
                "nop",
            ]
        )

    t_lines.extend(
        [
            f"csrrw x{check_reg}, frm, x{frm_reg}",
            "nop",
            write_sigupd(check_reg, test_data),
        ]
    )
    if bad_frm:
        t_lines.extend(
            [
                f"slli x{check_reg}, x{frm_reg}, 5",
                f"csrw fcsr, x{check_reg}",
                "nop",
            ]
        )
    else:
        t_lines.extend(
            [
                f"csrw frm, x{frm_reg}",
                "nop",
            ]
        )
    if not bad_frm:
        t_lines.extend(
            [
                f"csrc mstatus, x{clear_mask_reg}",
                "nop",
                f"csrs mstatus, x{set_mask_reg}",
                "nop",
            ]
        )

    t_lines.extend(
        [
            f"csrrw x{check_reg}, fflags, x0",
            "nop",
            write_sigupd(check_reg, test_data),
        ]
    )
    if bad_frm:
        t_lines.extend(
            [
                f"slli x{check_reg}, x{frm_reg}, 5",
                f"csrw fcsr, x{check_reg}",
                "nop",
            ]
        )
    else:
        t_lines.extend(
            [
                f"csrc mstatus, x{clear_mask_reg}",
                "nop",
                f"csrs mstatus, x{set_mask_reg}",
                "nop",
            ]
        )

    csr_rs_reg = "x0" if bad_frm else f"x{check_reg}"
    t_lines.extend(
        [
            f"csrrs x{check_reg}, fcsr, {csr_rs_reg}",
            "nop",
            write_sigupd(check_reg, test_data),
        ]
    )
    if bad_frm:
        t_lines.extend(
            [
                f"csrw frm, x{frm_reg}",
                "nop",
            ]
        )
    else:
        t_lines.extend(
            [
                f"csrc mstatus, x{clear_mask_reg}",
                "nop",
                f"csrs mstatus, x{set_mask_reg}",
                "nop",
            ]
        )

    t_lines.extend(
        [
            f"csrrs x{check_reg}, fflags, x{check_reg}",
            "nop",
            write_sigupd(check_reg, test_data),
        ]
    )
    if bad_frm:
        t_lines.extend(
            [
                f"csrw frm, x{frm_reg}",
                "nop",
            ]
        )
    else:
        t_lines.extend(
            [
                f"csrc mstatus, x{clear_mask_reg}",
                "nop",
                f"csrs mstatus, x{set_mask_reg}",
                "nop",
            ]
        )

    t_lines.extend(
        [
            f"csrrs x{check_reg}, frm, x{frm_reg}",
            "nop",
            write_sigupd(check_reg, test_data),
        ]
    )
    if bad_frm:
        t_lines.extend(
            [
                f"csrw frm, x{frm_reg}",
                "nop",
            ]
        )
    else:
        t_lines.extend(
            [
                f"csrc mstatus, x{clear_mask_reg}",
                "nop",
                f"csrs mstatus, x{set_mask_reg}",
                "nop",
            ]
        )

    csr_rc_reg = "x0" if bad_frm else f"x{check_reg}"
    t_lines.extend(
        [
            f"csrrc x{check_reg}, fcsr, {csr_rc_reg}",
            "nop",
            write_sigupd(check_reg, test_data),
        ]
    )
    t_lines.extend(
        [
            f"csrw frm, x{frm_reg}",
            "nop",
        ]
    )
    if not bad_frm:
        t_lines.extend(
            [
                f"csrc mstatus, x{clear_mask_reg}",
                "nop",
                f"csrs mstatus, x{set_mask_reg}",
                "nop",
            ]
        )

    t_lines.extend(
        [
            f"csrrc x{check_reg}, fcsr, {csr_rc_reg}",
            "nop",
            write_sigupd(check_reg, test_data),
        ]
    )
    t_lines.extend(
        [
            f"csrw frm, x{frm_reg}",
            "nop",
        ]
    )
    if not bad_frm:
        t_lines.extend(
            [
                f"csrc mstatus, x{clear_mask_reg}",
                "nop",
                f"csrs mstatus, x{set_mask_reg}",
                "nop",
            ]
        )

    t_lines.extend(
        [
            f"csrrc x{check_reg}, frm, x{frm_reg}",
            "nop",
            write_sigupd(check_reg, test_data),
        ]
    )
    t_lines.extend(
        [
            f"csrw frm, x{frm_reg}",
            "nop",
        ]
    )
    if not bad_frm:
        t_lines.extend(
            [
                f"csrc mstatus, x{clear_mask_reg}",
                "nop",
                f"csrs mstatus, x{set_mask_reg}",
                "nop",
            ]
        )

    t_lines.extend(
        [
            f"csrrc x{check_reg}, fflags, x{check_reg}",
            "nop",
            write_sigupd(check_reg, test_data),
        ]
    )

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
    addr_reg = test_data.int_regs.get_register()
    data_reg = test_data.float_regs.get_register()

    t_lines = [
        f"LA(x{addr_reg}, scratch)",
        f"addi x{addr_reg}, x{addr_reg}, {offset}",
        test_data.add_testcase(f"{op}_off{offset}", coverpoint, covergroup),
        f"{op} f{data_reg}, 0(x{addr_reg})",
        "nop",
        write_sigupd(data_reg, test_data),
    ]

    test_data.int_regs.return_register(addr_reg)
    test_data.float_regs.return_register(data_reg)
    return t_lines


def _generate_mstatus_fs_illegal_instr_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsF_cg", "cp_mstatus_fs_illegal_instr"
    clear_mask_reg, fs_reg, frm_reg, set_mask_reg = test_data.int_regs.get_registers(4)

    lines = [
        comment_banner(
            coverpoint,
            "Test that illegal instructions trap when mstatus.fs is set to 0 (Off)\n"
            "and do not trap when mstatus.fs is set to 1 (Clean)",
        ),
        f"LI(x{clear_mask_reg}, 0x6000)",  # MSTATUS_FS mask
        f"LI(x{fs_reg}, 0)",
        f"LI(x{frm_reg}, 0)",
        f"slli x{set_mask_reg}, x{fs_reg}, 13",
    ]

    lines.extend(add_fp_instructions(clear_mask_reg, set_mask_reg, frm_reg, 0, test_data, coverpoint, covergroup))
    test_data.int_regs.return_registers([clear_mask_reg, fs_reg, frm_reg, set_mask_reg])
    return lines


def _generate_mstatus_fs_csr_write_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsF_cg", "cp_mstatus_fs_csr_write"
    clear_mask_reg, fs_reg, frm_reg, set_mask_reg = test_data.int_regs.get_registers(4)

    lines = [
        comment_banner(
            coverpoint,
            "Test that illegal instructions trap when mstatus.fs is set to 0 (Off)\n"
            "and do not trap when mstatus.fs is set to 1 (Clean)",
        ),
        f"LI(x{clear_mask_reg}, 0x6000)",  # MSTATUS_FS mask
        f"LI(x{fs_reg}, 0)",
        f"LI(x{frm_reg}, 0)",
        f"slli x{set_mask_reg}, x{fs_reg}, 13",
    ]

    lines.extend(add_csr_instructions(clear_mask_reg, set_mask_reg, frm_reg, 0, test_data, coverpoint, covergroup))
    test_data.int_regs.return_registers([clear_mask_reg, fs_reg, frm_reg, set_mask_reg])
    return lines


def _generate_mstatus_fs_legal_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsF_cg", "cp_mstatus_fs_legal"
    clear_mask_reg, fs_reg, frm_reg, set_mask_reg = test_data.int_regs.get_registers(4)

    lines = [
        comment_banner(
            coverpoint,
            "Test that instructions execute correctly when mstatus.fs is set to 1 (Clean)\n"
            "and that mstatus.fs updates to 2 (Dirty) when an F instruction is executed",
        ),
        f"LI(x{clear_mask_reg}, 0x6000)",  # MSTATUS_FS mask
        f"LI(x{frm_reg}, 0)",
    ]
    for i in range(1, 4):
        lines.extend(
            [
                f"LI(x{fs_reg}, {i})",
                f"slli x{set_mask_reg}, x{fs_reg}, 13",
            ]
        )
        lines.extend(add_csr_instructions(clear_mask_reg, set_mask_reg, frm_reg, i, test_data, coverpoint, covergroup))
        lines.extend(
            [
                f"LI(x{fs_reg}, {i})",
                f"slli x{set_mask_reg}, x{fs_reg}, 13",
            ]
        )
        lines.extend(add_fp_instructions(clear_mask_reg, set_mask_reg, frm_reg, i, test_data, coverpoint, covergroup))
    test_data.int_regs.return_registers([clear_mask_reg, fs_reg, frm_reg, set_mask_reg])
    return lines


def _generate_illegal_frm_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsF_cg", "cp_badfrm"
    clear_mask_reg, fs_reg, frm_reg, set_mask_reg = test_data.int_regs.get_registers(4)
    lines = [
        comment_banner(
            coverpoint,
            "Reserved frm values 5–7 in fcsr with mstatus.FS enabled (nonzero).\n"
            "Covers cp_badfrm: instrs × mstatus_FS_nonzero × frm_illegal.",
        ),
        f"LI(x{clear_mask_reg}, 0x6000)",  # MSTATUS_FS mask
    ]
    for illegal_frm in range(5, 8):
        lines.extend(
            [
                f"LI(x{frm_reg}, {illegal_frm})",
                f"LI(x{fs_reg}, 3)",
                f"slli x{set_mask_reg}, x{fs_reg}, 13",
            ]
        )
        lines.extend(
            add_csr_instructions(
                clear_mask_reg, set_mask_reg, frm_reg, illegal_frm, test_data, coverpoint, covergroup, bad_frm=True
            )
        )
        lines.extend(
            [
                f"LI(x{frm_reg}, {illegal_frm})",
                f"LI(x{fs_reg}, 3)",
                f"slli x{set_mask_reg}, x{fs_reg}, 13",
            ]
        )
        lines.extend(
            add_fp_instructions(
                clear_mask_reg, set_mask_reg, frm_reg, illegal_frm, test_data, coverpoint, covergroup, bad_frm=True
            )
        )
    test_data.int_regs.return_registers([clear_mask_reg, fs_reg, frm_reg, set_mask_reg])
    return lines


def _generate_load_address_misaligned_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsF_cg", "cp_load_address_misaligned"

    lines = [
        comment_banner(
            coverpoint,
            "Test load instructions on misaligned addresses to check for traps\n"
            "Testing all offsets upto MISALIGNED_MAX_LOAD_STORE_GRANULE_SIZE+1",
        ),
    ]
    load_ops = ["flw"]

    for offset in range(16):
        for op in load_ops:
            lines.append(f"\n# Testcase: {op} with offset {offset} (LSBs: {offset:03b})")
            lines.extend(add_fp_load_misaligned_test(op, offset, test_data, coverpoint, covergroup))

        lines.append("#ifdef D_SUPPORTED")
        for op in ["fld"]:
            lines.append(f"\n# Testcase: {op} with offset {offset} (LSBs: {offset:03b})")
            lines.extend(add_fp_load_misaligned_test(op, offset, test_data, coverpoint, covergroup))
        lines.append("#endif\n")

        lines.extend(["#ifdef ZFHMIN_SUPPORTED"])
        for op in ["flh"]:
            lines.append(f"\n# Testcase: {op} with offset {offset} (LSBs: {offset:03b})")
            lines.extend(add_fp_load_misaligned_test(op, offset, test_data, coverpoint, covergroup))
        lines.append("#endif")

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

    load_ops = ["flw"]

    for op in load_ops:
        lines.append(f"\n# Testcase: {op} access fault")
        lines.append(f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)")
        lines.extend(
            [
                test_data.add_testcase(f"{op}_fault", coverpoint, covergroup),
                f"{op} f{check_reg}, 0(x{addr_reg})",
                "nop",
                write_sigupd(check_reg, test_data),
            ]
        )

    lines.extend(["", "#ifdef D_SUPPORTED"])
    for op in ["fld"]:
        lines.append(f"\n# Testcase: {op} access fault")
        lines.append(f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)")
        lines.extend(
            [
                test_data.add_testcase(f"{op}_fault", coverpoint, covergroup),
                f"{op} f{check_reg}, 0(x{addr_reg})",
                "nop",
                write_sigupd(check_reg, test_data),
            ]
        )
    lines.extend(["", "#endif\n"])
    lines.extend(["#ifdef ZFHMIN_SUPPORTED"])
    for op in ["flh"]:
        lines.append(f"\n# Testcase: {op} access fault")
        lines.append(f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)")
        lines.extend(
            [
                test_data.add_testcase(f"{op}_fault", coverpoint, covergroup),
                f"{op} f{check_reg}, 0(x{addr_reg})",
                "nop",
                write_sigupd(check_reg, test_data),
            ]
        )
    lines.extend(["", "#endif", "#endif", ""])
    test_data.int_regs.return_register(addr_reg)
    test_data.float_regs.return_register(check_reg)
    return lines


def _generate_store_address_misaligned_tests(test_data: TestData) -> list[str]:
    covergroup, coverpoint = "ExceptionsF_cg", "cp_store_address_misaligned"

    lines = [
        comment_banner(
            coverpoint,
            "Test store instructions on misaligned addresses to check for traps\n"
            "Testing all offsets upto MISALIGNED_MAX_LOAD_STORE_GRANULE_SIZE+1",
        ),
    ]
    store_ops = ["fsw"]

    for offset in range(16):
        for op in store_ops:
            lines.append(f"\n# Testcase: {op} with offset {offset} (LSBs: {offset:03b})")
            lines.extend(add_fp_store_misaligned_test(op, offset, test_data, coverpoint, covergroup))

        lines.append("#ifdef D_SUPPORTED")
        for op in ["fsd"]:
            lines.append(f"\n# Testcase: {op} with offset {offset} (LSBs: {offset:03b})")
            lines.extend(add_fp_store_misaligned_test(op, offset, test_data, coverpoint, covergroup))
        lines.append("#endif\n")

        lines.extend(["#ifdef ZFHMIN_SUPPORTED"])
        for op in ["fsh"]:
            lines.append(f"\n# Testcase: {op} with offset {offset} (LSBs: {offset:03b})")
            lines.extend(add_fp_store_misaligned_test(op, offset, test_data, coverpoint, covergroup))
        lines.append("#endif")

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

    store_ops = ["fsw"]

    for op in store_ops:
        lines.append(f"\n# Testcase: {op} access fault")
        lines.append(f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)")
        lines.extend(
            [
                test_data.add_testcase(f"{op}_fault", coverpoint, covergroup),
                f"{op} f{data_reg}, 0(x{addr_reg})",
                "nop",
                write_sigupd(data_reg, test_data),
            ]
        )

    lines.extend(["", "#ifdef D_SUPPORTED"])
    for op in ["fsd"]:
        lines.append(f"\n# Testcase: {op} access fault")
        lines.append(f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)")
        lines.extend(
            [
                test_data.add_testcase(f"{op}_fault", coverpoint, covergroup),
                f"{op} f{data_reg}, 0(x{addr_reg})",
                "nop",
                write_sigupd(data_reg, test_data),
            ]
        )
    lines.extend(["", "#endif\n"])
    lines.extend(["#ifdef ZFHMIN_SUPPORTED"])
    for op in ["fsh"]:
        lines.append(f"\n# Testcase: {op} access fault")
        lines.append(f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)")
        lines.extend(
            [
                test_data.add_testcase(f"{op}_fault", coverpoint, covergroup),
                f"{op} f{data_reg}, 0(x{addr_reg})",
                "nop",
                write_sigupd(data_reg, test_data),
            ]
        )
    lines.extend(["", "#endif", "#endif", ""])
    test_data.int_regs.return_register(addr_reg)
    test_data.float_regs.return_register(data_reg)
    return lines


@add_priv_test_generator(
    "ExceptionsF",
    required_extensions=["I", "Zicsr", "F", "Sm"],
    march_extensions=["Zfa", "D", "Zfhmin"],
)
def make_exceptionsf(test_data: TestData) -> list[str]:
    """Main entry point for F exception test generation."""

    lines = [
        "li t0,0x4000",
        "csrs mstatus, t0",
        "csrw frm, 0",
        "la      t5, scratch",
        "",
        "li     t1, 0xDEADBEEF",
        "sw     t1, 0(t5)",
        "sw     t1, 4(t5)",
        "sw     t1, 8(t5)",
        "sw     t1, 12(t5)",
        "",
    ]

    # initialize fp registers
    for i in range(15):
        lines.extend(
            [
                f"li t0, {i + 1}",
                f"fcvt.s.w f{i}, t0",
            ]
        )

    lines.extend(_generate_mstatus_fs_illegal_instr_tests(test_data))
    lines.extend(_generate_mstatus_fs_csr_write_tests(test_data))
    lines.extend(_generate_illegal_frm_tests(test_data))
    lines.extend(_generate_mstatus_fs_legal_tests(test_data))
    lines.extend(_generate_load_address_misaligned_tests(test_data))
    lines.extend(_generate_load_access_fault_tests(test_data))
    lines.extend(_generate_store_address_misaligned_tests(test_data))
    lines.extend(_generate_store_access_fault_tests(test_data))
    return lines
