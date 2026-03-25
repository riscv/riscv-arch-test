##################################
# SmF.py
#
# SmF floating-point from machine mode privileged extension test generator.
# David_Harris@hmc.edu 1 March 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""SmF privileged extension test generator."""

from testgen.asm.csr import gen_csr_read_sigupd
from testgen.asm.helpers import comment_banner, load_float_reg
from testgen.constants import INDENT
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _gen_fs_init(fs: int, temp_reg: int) -> str:
    """Initialize mstatus.FS"""
    lines = [
        f"LI(x{temp_reg}, {3 << 13})  # 11 in bits 14:13",
        f"CSRC(mstatus, x{temp_reg}) # Clear mstatus.FS=00",
        f"LI(x{temp_reg}, {fs << 13})  # put fs in bits 14:13",
        f"CSRS(mstatus, x{temp_reg}) # Set mstatus.FS to {fs}",
    ]
    return "\n".join(lines)


def _generate_smfcsr_tests(test_data: TestData) -> list[str]:
    """Generate CSR tests."""
    covergroup = "SmF_fcsr_cg"

    # fp CSRs
    csrs = ["fcsr", "frm", "fflags"]
    lines = []

    ######################################
    coverpoint = "cp_fcsr_access"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "Read, write all 1s, write all 0s, set all 1s, set all 0s, restore all fp CSRs from machine mode with different mstatus.FS",
        )
    )

    ones_reg, check_reg, scratch_reg, temp_reg, save_reg = test_data.int_regs.get_registers(5, exclude_regs=[0])
    lines.append(f"LI(x{ones_reg}, -1)\n")

    for fs in range(4):
        coverpoint_full = f"{coverpoint}_fs{fs}"
        for csr in csrs:
            lines.extend(
                [
                    f"# Testcase: {csr} access with mstatus.FS={fs}: write 1s",
                    _gen_fs_init(fs, temp_reg),
                    f"CSRR(x{save_reg}, {csr})    # Save CSR",
                    test_data.add_testcase(f"{csr}_csrrw1", coverpoint_full, covergroup),
                    f"CSRW({csr}, x{ones_reg})    # Write all 1s to CSR",
                    gen_csr_read_sigupd(check_reg, "mstatus", test_data),
                    gen_csr_read_sigupd(check_reg, csr, test_data),
                    "",
                    f"# Testcase: {csr} access with mstatus.FS={fs}: write 0s",
                    _gen_fs_init(fs, temp_reg),
                    test_data.add_testcase(f"{csr}_csrrw0", coverpoint_full, covergroup),
                    f"CSRW({csr}, zero)   # Write all 0s to CSR",
                    gen_csr_read_sigupd(check_reg, "mstatus", test_data),
                    gen_csr_read_sigupd(check_reg, csr, test_data),
                    "",
                    f"# Testcase: {csr} access with mstatus.FS={fs}: set all bits",
                    _gen_fs_init(fs, temp_reg),
                    test_data.add_testcase(f"{csr}_csrs_all", coverpoint_full, covergroup),
                    f"CSRS({csr}, x{ones_reg})    # Set all CSR bits",
                    gen_csr_read_sigupd(check_reg, "mstatus", test_data),
                    gen_csr_read_sigupd(check_reg, csr, test_data),
                    "",
                    f"# Testcase: {csr} access with mstatus.FS={fs}: clear all bits",
                    _gen_fs_init(fs, temp_reg),
                    test_data.add_testcase(f"{csr}_csrrc_all", coverpoint_full, covergroup),
                    f"CSRC({csr}, x{ones_reg})    # Clear all CSR bits",
                    gen_csr_read_sigupd(check_reg, "mstatus", test_data),
                    gen_csr_read_sigupd(check_reg, csr, test_data),
                    f"CSRW({csr}, x{save_reg})       # Restore CSR",
                    "",
                ]
            )

    ######################################
    coverpoint = "cp_mstatus_FS_transition"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "Attempt different types of fp instructions crossed with values of mstatus.FS",
        )
    )

    insns = [
        f"fsw f1, 0(x{scratch_reg})",
        f"flw f0, 0(x{scratch_reg})",
        "fadd.s f0, f1, f2",
        "fsub.s f0, f1, f2",
        "fmul.s f0, f1, f2",
        "fdiv.s f0, f1, f2",
        "fcvt.s.w f0, x0",
        f"fcvt.w.s x{temp_reg}, f0",
        "fmadd.s f0, f1, f2, f3",
        "fsqrt.s f0, f1",
        "fsgnj.s f0, f1, f2",
        f"feq.s x{temp_reg}, f1, f2",
        f"fmv.x.w x{temp_reg}, f1",
        f"fmv.w.x f0, x{temp_reg}",
        f"fclass.s x{temp_reg}, f3",
        "fmin.s f0, f1, f2",
        f"add x{temp_reg}, x{temp_reg}, x{temp_reg}",
        f"csrr x{temp_reg}, fcsr",
        f"csrr x{temp_reg}, frm",
        f"csrr x{temp_reg}, fflags",
        f"csrrw x{temp_reg}, fcsr, x{temp_reg}",
        f"csrrw x{temp_reg}, frm, x{temp_reg}",
        f"csrrw x{temp_reg}, fflags, x{temp_reg}",
        f"csrrs x{temp_reg}, fcsr, x{temp_reg}",
        f"csrrs x{temp_reg}, frm, x{temp_reg}",
        f"csrrs x{temp_reg}, fflags, x{temp_reg}",
        f"csrrc x{temp_reg}, fcsr, x{temp_reg}",
        f"csrrc x{temp_reg}, frm, x{temp_reg}",
        f"csrrc x{temp_reg}, fflags, x{temp_reg}",
    ]

    lines.extend(
        [
            f"{INDENT}# set up for {coverpoint}",
            f"LA(x{scratch_reg}, scratch)  # pointer to scratch register",
            load_float_reg("1.0", 1, 0x3F800000, test_data, "single"),
            load_float_reg("3.0", 2, 0x40400000, test_data, "single"),
            load_float_reg("tiny", 3, 0x00800000, test_data, "single"),
        ]
    )

    for fs in range(4):
        coverpoint_full = f"{coverpoint}_fs{fs}"
        for insn in insns:
            lines.extend(
                [
                    "",
                    f"# Testcase: {insn} with mstatus.FS={fs}",
                    _gen_fs_init(fs, temp_reg),
                    test_data.add_testcase(f"{insn}", coverpoint_full, covergroup),
                    f"{insn} # execute instruction with mstatus.FS={fs}",
                    gen_csr_read_sigupd(temp_reg, "mstatus", test_data),
                ]
            )
        lines.append("\n#ifdef D_SUPPORTED")
        for insn in ["fcvt.s.d f0, f1"]:
            lines.extend(
                [
                    "",
                    f"# Testcase: {insn} with mstatus.FS={fs}",
                    _gen_fs_init(fs, temp_reg),
                    test_data.add_testcase(f"{insn}", coverpoint_full, covergroup),
                    f"{insn} # execute instruction with mstatus.FS={fs}",
                    gen_csr_read_sigupd(temp_reg, "mstatus", test_data),
                ]
            )
        lines.extend(
            [
                "",
                "#if __riscv_xlen == 32",
                "#ifdef ZFA_SUPPORTED",
            ]
        )
        for insn in [f"fmvh.x.d x{temp_reg}, f1", f"fmvp.d.x f0, x{temp_reg}, x{temp_reg}"]:
            lines.extend(
                [
                    "",
                    f"# Testcase: {insn} with mstatus.FS={fs}",
                    _gen_fs_init(fs, temp_reg),
                    test_data.add_testcase(f"{insn}", coverpoint_full, covergroup),
                    f"{insn} # execute instruction with mstatus.FS={fs}",
                    gen_csr_read_sigupd(temp_reg, "mstatus", test_data),
                ]
            )
        lines.extend(
            [
                "",
                "#endif",
                "#endif",
                "#endif",
                "",
                "#ifdef ZFA_SUPPORTED",
            ]
        )
        for insn in ["fli.s f0, 0.5", "fround.s f0, f3, rup"]:
            lines.extend(
                [
                    "",
                    _gen_fs_init(fs, temp_reg),
                    test_data.add_testcase(f"{insn}", coverpoint_full, covergroup),
                    f"{insn} # execute instruction with mstatus.FS={fs}",
                    gen_csr_read_sigupd(temp_reg, "mstatus", test_data),
                ]
            )
        lines.append("\n#endif")

    test_data.int_regs.return_registers([ones_reg, check_reg, temp_reg, scratch_reg, save_reg])

    return lines


@add_priv_test_generator("SmF", required_extensions=["Sm", "U", "F", "Zicsr"], march_extensions=["F", "D", "Zfa"])
def make_smf(test_data: TestData) -> list[str]:
    """Generate tests for SmF machine-mode floating-point testsuite."""
    lines: list[str] = []

    lines.extend(_generate_smfcsr_tests(test_data))

    return lines
