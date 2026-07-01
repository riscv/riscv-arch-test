##################################
# priv/extensions/ExceptionsH.py
#
# ExceptionsH test generator
# ellyu@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

# This test currently assumes that M mode is supported
"""Exceptions H extension test generator."""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.extensions.ExceptionsCommon import (
    add_load_misaligned_test,
    add_store_misaligned_test,
)
from testgen.priv.registry import add_priv_test_generator

_CG = "ExceptionsH_cg"


def _generate_hedeleg_tests(test_data: TestData) -> list[str]:
    """Generate hedeleg exceptions test

    Attempt {instruction/load/store access fault, instruction/load/store misaligned fault, illegal instruction, ebreak}
    crossed with privilege mode M/HS/VS/VU/U
    crossed with medeleg = {0s/1111_0000_1011_0111_1111_111?}
    crossed with hedeleg = {0s/ 0000_11?0_1?11_0001_1111_111?/(walking 1s in hedeleg[8:1])}
    """

    covergroup, coverpoint = _CG, "cp_hedeleg"

    lines = [
        comment_banner(coverpoint, _generate_hedeleg_tests.__doc__),
    ]

    r_temp = test_data.int_regs.get_register(exclude_regs=[])

    priv_mode = ["M", "HS", "U", "VS", "VU"]
    hval_list = ["all", "zero", 1, 2, 3, 4, 5, 6, 7, 8]

    for priv in priv_mode:
        for medeleg_val in [0, 1]:
            for hedeleg_val in hval_list:
                lines.extend(
                    [
                        "# Setup in M mode",
                    ]
                )
                if medeleg_val == 0:
                    lines.extend(
                        [
                            "# Clear medeleg",
                            "CSRW(medeleg, zero)",
                        ]
                    )
                else:
                    lines.extend(
                        [
                            "# medeleg: Delegate all delegatable exceptions to HS mode",
                            f"LI(x{r_temp}, 0xF0D7FE)",
                            f"CSRS(medeleg, x{r_temp})",
                        ]
                    )
                if hedeleg_val == "zero":
                    lines.extend(
                        [
                            "# Clear hedeleg",
                            "CSRW(hedeleg, zero)",
                        ]
                    )
                elif hedeleg_val == "all":
                    lines.extend(
                        [
                            "# hedeleg: Delegate all delegatable exceptions to VS mode",
                            f"LI(x{r_temp}, 0x0CD1FE)",
                            f"CSRS(hedeleg, x{r_temp})",
                        ]
                    )
                else:
                    lines.extend(
                        [
                            "# Clear hedeleg first",
                            "CSRW(hedeleg, zero)",
                            "# set hedeleg bit based on bins",
                            f"LI(x{r_temp}, 1<<{hedeleg_val})",
                            f"CSRS(hedeleg, x{r_temp})",
                        ]
                    )
                if priv != "M":
                    lines.append(f"RVTEST_GOTO_LOWER_MODE {priv}mode")
                bin_name = f"mode_{priv}_medeleg_{medeleg_val}_hedeleg_{hedeleg_val}"
                lines.extend(
                    [
                        "# perform instruction access fault",
                        "#ifdef RVMODEL_ACCESS_FAULT_ADDRESS",
                        f"LA(x{r_temp}, RVMODEL_ACCESS_FAULT_ADDRESS)",
                        "LI(x4, 0xACCE)",  # trap handler checks x4 and returns via x1 (ra) instead of mepc
                        test_data.add_testcase(f"{bin_name}_instr_access_fault", coverpoint, covergroup),
                        f"jalr x1, 0(x{r_temp})",
                        "nop",
                        "#endif",
                        "",
                        "# perform load access fault",
                        "#ifdef RVMODEL_ACCESS_FAULT_ADDRESS",
                        f"LA(x{r_temp}, RVMODEL_ACCESS_FAULT_ADDRESS)",
                        test_data.add_testcase(f"{bin_name}_load_access_fault", coverpoint, covergroup),
                        f"lw x{r_temp}, 0(x{r_temp})",
                        "nop",
                        "#endif",
                        "",
                        "# perform store access fault",
                        "#ifdef RVMODEL_ACCESS_FAULT_ADDRESS",
                        f"LA(x{r_temp}, RVMODEL_ACCESS_FAULT_ADDRESS)",
                        test_data.add_testcase(f"{bin_name}_store_access_fault", coverpoint, covergroup),
                        f"sw x{r_temp}, 0(x{r_temp})",
                        "nop",
                        "#endif",
                        "",
                        "# perform instruction adr misaligned exception",
                        test_data.add_testcase(f"{bin_name}_instr_misaligned", coverpoint, covergroup),
                        "jal x0, .+6",
                        "# jal by 6 lands in the upper half of the next instruction (0x0001 -> c.nop)",
                        "addi x0, x2, 0",
                        "nop",
                        "",
                        "# perform load address misaligned exception",
                        f"LA(x{r_temp}, scratch)",
                        f"addi x{r_temp}, x{r_temp}, 1",
                        test_data.add_testcase(f"{bin_name}_load_misaligned", coverpoint, covergroup),
                        f"lw x{r_temp}, 0(x{r_temp})",
                        "nop",
                        "",
                        "# perform store address misaligned exception",
                        f"LA(x{r_temp}, scratch)",
                        f"addi x{r_temp}, x{r_temp}, 1",
                        test_data.add_testcase(f"{bin_name}_store_misaligned", coverpoint, covergroup),
                        f"sw x{r_temp}, 0(x{r_temp})",
                        "nop",
                        "",
                        "# perform illegal instruction exception",
                        ".align 2",
                        test_data.add_testcase(f"{bin_name}_illegal", coverpoint, covergroup),
                        ".word 0x00000000",
                        "nop",
                        "",
                        "# Trigger ebreak exception",
                        test_data.add_testcase(f"{bin_name}_ebreak", coverpoint, covergroup),
                        "ebreak",
                        "nop",
                        "",
                    ]
                )
                if priv != "M":
                    lines.extend(
                        [
                            "# Return to M mode",
                            "RVTEST_GOTO_MMODE",
                        ]
                    )

    test_data.int_regs.return_register(r_temp)
    return lines


def _generate_ecall_to_vs_tests(test_data: TestData) -> list[str]:
    """Generate ecall to VS mode tests

    Delegate ecalls from VU to VS with medeleg and hedeleg.
    Make ecall from VU to VS.

    """

    covergroup, coverpoint = _CG, "cp_ecall_to_vs"

    r_temp = test_data.int_regs.get_register(exclude_regs=[])

    lines = [
        comment_banner(coverpoint, _generate_ecall_to_vs_tests.__doc__),
    ]

    lines.extend(
        [
            "# Set medeleg and hedeleg from M mode",
            f"LI(x{r_temp}, 0x100)",
            f"CSRS(medeleg, x{r_temp})",
            f"CSRS(hedeleg, x{r_temp})",
            "",
            test_data.add_testcase("VU_to_VS", coverpoint, covergroup),
            "RVTEST_GOTO_LOWER_MODE VUmode",
            "ecall",
            "nop",
            "# Return to M mode (ecall is delegated here, so use the illegal-instruction path)",
            "RVTEST_GOTO_DELEGATED_MMODE",
        ]
    )

    test_data.int_regs.return_register(r_temp)
    return lines


def _generate_ecall_to_hs_tests(test_data: TestData) -> list[str]:
    """Generate ecall to HS mode tests

    Delegate ecalls from {U, VS, VU} to HS with medeleg with hedeleg = 0.
    Make ecall to HS cross with hstatus.SPVP={0/1}.

    """

    covergroup, coverpoint = _CG, "cp_ecall_to_hs"

    r_temp = test_data.int_regs.get_register(exclude_regs=[])

    lines = [
        comment_banner(coverpoint, _generate_ecall_to_hs_tests.__doc__),
    ]

    priv_mode = [("U", 0x100), ("VS", 0x400), ("VU", 0x100)]

    for priv, deleg_bit in priv_mode:
        for spvp in [0, 1]:
            binname = f"mode_{priv}_SPVP_{spvp}"
            lines.extend(
                [
                    "# --- M mode setup ---",
                    f"# Set medeleg for ecall from {priv} mode",
                    f"LI(x{r_temp}, {deleg_bit})",
                    f"CSRS(medeleg, x{r_temp})",
                    "",
                    "# Clear hedeleg",
                    "CSRW(hedeleg, zero)",
                    "",
                    "# Write hstatus.SPVP based on bins",
                    f"LI(x{r_temp}, 0x100) # SPVP bit",
                    f"{'CSRS' if spvp else 'CSRC'}(hstatus, x{r_temp})",
                    "",
                    test_data.add_testcase(binname, coverpoint, covergroup),
                    "# Go down to the corresponding priv mode based on bins",
                    f"RVTEST_GOTO_LOWER_MODE {priv}mode",
                    "ecall",
                    "nop",
                    "# Return to M mode (ecall is delegated here, so use the illegal-instruction path)",
                    "RVTEST_GOTO_DELEGATED_MMODE",
                ]
            )

    test_data.int_regs.return_register(r_temp)

    return lines


def _generate_ecall_to_m_tests(test_data: TestData) -> list[str]:
    """Generate ecall to M mode tests

    No delegation of ecalls.  Make ecall from M/HS/U/VS/VU to M.
    """

    covergroup, coverpoint = _CG, "cp_ecall_to_m"

    lines = [
        comment_banner(coverpoint, _generate_ecall_to_m_tests.__doc__),
    ]

    priv_mode = ["M", "HS", "U", "VS", "VU"]

    for priv in priv_mode:
        binname = f"mode_{priv}"
        lines.extend(
            [
                "# --- M mode setup ---",
                "# Clear medeleg",
                "CSRW(medeleg, zero)",
                "",
                test_data.add_testcase(binname, coverpoint, covergroup),
            ]
        )
        if priv != "M":
            lines.append(f"RVTEST_GOTO_LOWER_MODE {priv}mode")
        lines.extend(
            [
                "ecall",
                "nop",
            ]
        )
        if priv != "M":
            lines.extend(
                [
                    "# Return to M mode",
                    "RVTEST_GOTO_MMODE",
                ]
            )

    return lines


def _generate_ebreak_to_m_tests(test_data: TestData) -> list[str]:
    """Generate ebreak to M mode tests

    No delegation of ebreak.  Make ebreak from M/HS/U/VS/VU to M.
    """

    covergroup, coverpoint = _CG, "cp_ebreak_to_m"

    lines = [
        comment_banner(coverpoint, _generate_ebreak_to_m_tests.__doc__),
    ]

    priv_mode = ["M", "HS", "U", "VS", "VU"]

    for priv in priv_mode:
        binname = f"mode_{priv}"
        lines.extend(
            [
                "# --- M mode setup ---",
                "# Clear medeleg",
                "CSRW(medeleg, zero)",
                "",
                test_data.add_testcase(binname, coverpoint, covergroup),
            ]
        )
        if priv != "M":
            lines.append(f"RVTEST_GOTO_LOWER_MODE {priv}mode")
        lines.extend(
            [
                "ebreak",
                "nop",
            ]
        )
        if priv != "M":
            lines.extend(
                [
                    "# Return to M mode",
                    "RVTEST_GOTO_MMODE",
                ]
            )

    return lines


def _generate_vstvec_tests(test_data: TestData) -> list[str]:
    """Generate vstvec tests

    Delegate ecall from {VU, VS} to VS with medeleg and hedeleg.
    Point vstvec to a different trap handler than stvec.
    Make ecall to VS from VU/VS
    """

    covergroup, coverpoint = _CG, "cp_vstvec"

    r_temp = test_data.int_regs.get_register(exclude_regs=[])

    lines = [
        comment_banner(coverpoint, _generate_vstvec_tests.__doc__),
    ]

    ############# need to fix still ######################
    lines.extend(
        [
            "# Set medeleg and hedeleg from M mode",
            f"LI(x{r_temp}, 0x100)",
            f"CSRS(medeleg, x{r_temp})",
            f"CSRS(hedeleg, x{r_temp})",
            "",
            test_data.add_testcase("VU_to_VS", coverpoint, covergroup),
            "RVTEST_GOTO_LOWER_MODE VUmode",
            "ecall",
            "nop",
            "# Return to M mode (ecall is delegated here, so use the illegal-instruction path)",
            "RVTEST_GOTO_DELEGATED_MMODE",
        ]
    )

    test_data.int_regs.return_register(r_temp)

    return lines


def _generate_priority_tests(test_data: TestData) -> list[str]:
    """Generate ExceptionsH priority tests

    Execute {hlv.w / hsv.w} x {legal/illegal address} x {addr[1:0] = 00/01} x {priv=M/HS/U/VS/VU} x hstatus.HU={0/1}
    to cause all combinations of illegal, virtual, access fault, misaligned
    """
    covergroup, coverpoint = _CG, "cp_priority"
    r_temp, r_address = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, _generate_priority_tests.__doc__),
    ]

    priv_mode = ["M", "HS", "U", "VS", "VU"]
    instr = ["hlv.w", "hsv.w"]
    adr_list = ["scratch", "RVMODEL_ACCESS_FAULT_ADDRESS"]

    #### need to work on - need to know what to set medeleg and hedeleg ####
    #### I think - no need to read back after store since this is just testing exceptions priorities ####

    for hInstr in instr:
        for address in adr_list:
            for offset in [0, 1]:
                for priv in priv_mode:
                    for hstatus_HU in [0, 1]:
                        address_name = "legal" if (address == "scratch") else "illegal"
                        binname = f"{hInstr}_{address_name}Address_Offset{offset}_{priv}_hstatusHU_{hstatus_HU}"

                        lines.extend(
                            [
                                "# --- M mode setup ---",
                                "# Clear medeleg and hedeleg",
                                "CSRW(medeleg, zero)",
                                "CSRW(hedeleg, zero)",
                                "# Write to hstatus.HU based on bins",
                                f"LI(x{r_temp}, 0x200) # HU bit",
                                f"{'CSRS' if hstatus_HU else 'CSRC'}(hstatus, x{r_temp})",
                                "",
                            ]
                        )

                        lines.extend(
                            [
                                "# set up the address",
                                f"LA(x{r_address}, {address})",
                                f"addi x{r_address}, x{r_address}, {offset}",
                            ]
                        )

                        if hInstr == "hsv.w":
                            lines.extend(["# Set up the value to load", f"LI(x{r_temp}, 0xDEADBEEF)"])

                        lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
                        if priv != "M":
                            lines.append(f"RVTEST_GOTO_LOWER_MODE {priv}mode")
                        lines.extend(
                            [
                                "# Execute the instr based on bins",
                                f"{hInstr} x{r_temp}, (x{r_address})",
                                "",
                            ]
                        )
                        if priv != "M":
                            lines.extend(
                                [
                                    "# Return to M mode",
                                    "RVTEST_GOTO_MMODE",
                                ]
                            )

    test_data.int_regs.return_registers([r_temp, r_address])
    return lines


def _generate_virtual_instruction_vs_tests(test_data: TestData) -> list[str]:
    """Generate virtual instructions Exceptions from VS mode

    read instret with hcounteren[2] = 0, mcounteren[2] = 1
    execute hlv.w, hlvx.wu, hsv.w, hfence.vvma, hfence.gvma
    read vstval, htval
    with mstatus.TVM = 0, read satp, vsatp
    wfi with hstatus.VTW=1, mstatus.TW=0, no interrupt firing
    sret with hstatus.VTSR=1
    {sfence.vma, sinval.vma, read satp} with hstatus.VTVM=1
    RV32 only:
    access instreth with hcounteren[2] = 0, mcounteren[2] = 1
    read hedelegh
    """

    covergroup, coverpoint = _CG, "cp_virtual_instruction_vs"
    r_temp, r_address = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, _generate_virtual_instruction_vs_tests.__doc__),
    ]

    lines.extend(
        [
            "# Read instret with hcounteren[2] = 0, mcounteren[2] = 1",
            "# set up in M mode",
            f"LI(x{r_temp}, 0x2) # IR bit",
            f"CSRC(hcounteren, x{r_temp})",
            f"CSRS(mcounteren, x{r_temp})",
            "",
            test_data.add_testcase("instret", coverpoint, covergroup),
            "# Go to VS mode to execute the instruction",
            "RVTEST_GOTO_LOWER_MODE VSmode",
            f"csrr x{r_temp}, instret",
            "#if __riscv_xlen == 32",
            f"csrr x{r_temp}, instreth",
            "#endif",
        ]
    )

    lines.extend(
        [
            "# execute hlv.w, hlvx.wu, hsv.w, hfence.vvma, hfence.gvma",
            "",
            f"LA(x{r_address}, scratch)",
            test_data.add_testcase("hlv", coverpoint, covergroup),
            f"hlv.w x{r_temp}, (x{r_address})",
            "",
            test_data.add_testcase("hlvx", coverpoint, covergroup),
            f"hlvx.wu x{r_temp}, (x{r_address})",
            "",
            test_data.add_testcase("hsv", coverpoint, covergroup),
            f"LI(x{r_temp}, 0xBAD)",
            f"hsv.w x{r_temp}, (x{r_address})",
            "",
            test_data.add_testcase("hfence_vvma", coverpoint, covergroup),
            "hfence.vvma",
            "",
            test_data.add_testcase("hfence_gvma", coverpoint, covergroup),
            "hfence.gvma",
            "",
        ]
    )

    lines.extend(
        [
            "# read vstval, htval",
            "",
            test_data.add_testcase("vstval", coverpoint, covergroup),
            f"csrr x{r_temp}, vstval",
            "",
            test_data.add_testcase("htval", coverpoint, covergroup),
            f"csrr x{r_temp}, htval",
            "",
        ]
    )

    lines.extend(
        [
            "# with mstatus.TVM = 0, read satp, vsatp",
            "RVTEST_GOTO_MMODE",
            f"LI(x{r_temp}, 0x100000) # TVM bit",
            f"CSRC(mstatus, x{r_temp})",
            "RVTEST_GOTO_LOWER_MODE VSmode",
            test_data.add_testcase("satp", coverpoint, covergroup),
            f"csrr x{r_temp}, satp",
            test_data.add_testcase("vsatp", coverpoint, covergroup),
            f"csrr x{r_temp}, vsatp",
            "",
        ]
    )

    lines.extend(
        [
            "# wfi with hstatus.VTW=1, mstatus.TW=0",
            "RVTEST_GOTO_MMODE",
            f"LI(x{r_temp}, 0x200000) # TW bit",
            f"CSRC(mstatus, x{r_temp})",
            f"CSRS(hstatus, x{r_temp})",
            "",
            "RVTEST_GOTO_LOWER_MODE VSmode",
            test_data.add_testcase("wfi", coverpoint, covergroup),
            "wfi",
        ]
    )

    lines.extend(
        [
            "# sret with hstatus.VTSR=1",
            "RVTEST_GOTO_MMODE",
            f"LI(x{r_temp}, 0x400000) # VTSR bit",
            f"CSRS(hstatus, x{r_temp})",
            "",
            "RVTEST_GOTO_LOWER_MODE VSmode",
            test_data.add_testcase("sret", coverpoint, covergroup),
            "sret",
            "nop",
        ]
    )

    lines.extend(
        [
            "# {sfence.vma, sinval.vma, read satp} with hstatus.VTVM=1",
            "RVTEST_GOTO_MMODE",
            f"LI(x{r_temp}, 0x100000) # VTVM bit",
            f"CSRS(hstatus, x{r_temp})",
            "",
            "RVTEST_GOTO_LOWER_MODE VSmode",
            test_data.add_testcase("sfence.vma", coverpoint, covergroup),
            "sfence.vma",
            "",
            "#ifdef SVINVAL_SUPPORTED",
            test_data.add_testcase("sinval.vma", coverpoint, covergroup),
            "sinval.vma zero, zero",
            "#endif",
            "",
            test_data.add_testcase("VTVMsatp", coverpoint, covergroup),
            f"csrr x{r_temp}, satp",
            "",
        ]
    )

    lines.extend(
        [
            "#if __riscv_xlen == 32",
            "# read hedelegh",
            f"csrr x{r_temp}, hedelegh",
            "#endif",
        ]
    )

    test_data.int_regs.return_registers([r_temp, r_address])

    return lines


def _generate_virtual_instruction_vu_tests(test_data: TestData) -> list[str]:
    """Generate virtual instruction exception test in VU mode

    In VU mode:
    read instret with hcounteren[2] = 0, scounteren[2] = 1, mcounteren[2] = 1
    read instret with hcounteren[2] = 1, scounteren[2] = 0, mcounteren[2] = 1
    execute hlv.w, hlvx.wu, hsv.w, hfence.vvma, hfence.gvma
    read vstval, htval
    read stval
    with mstatus.TVM = 0, read satp, vsatp
    wfi with mstatus.TW=0, no interrupt firing
    execute sret, sfence.vma
    RV32 only:
        read instreth with hcounteren[2] = 0, scounteren[2] = 1, mcounteren[2] = 1
        read instreth with hcounteren[2] = 1, scounteren[2] = 0, mcounteren[2] = 1
        read hedelegh
    """

    covergroup, coverpoint = _CG, "cp_virtual_instruction_vu"
    r_temp, r_address = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, _generate_virtual_instruction_vu_tests.__doc__),
    ]

    lines.extend(
        [
            "# read instret with hcounteren[2] = 0, scounteren[2] = 1, mcounteren[2] = 1",
            "# set up in M mode",
            f"LI(x{r_temp}, 0x2) # IR bit",
            f"CSRC(hcounteren, x{r_temp})",
            f"CSRS(scounteren, x{r_temp})",
            f"CSRS(mcounteren, x{r_temp})",
            "",
            test_data.add_testcase("instret_scounteren_1_hcouonteren_0", coverpoint, covergroup),
            "# Go to VU mode to execute the instruction",
            "RVTEST_GOTO_LOWER_MODE VUmode",
            f"csrr x{r_temp}, instret",
            "#if __riscv_xlen == 32",
            f"csrr x{r_temp}, instreth",
            "#endif",
            "# Return to M mode",
            "RVTEST_GOTO_MMODE",
            "",
            "# read instret with hcounteren[2] = 1, scounteren[2] = 0, mcounteren[2] = 1",
            "# set up in M mode",
            f"LI(x{r_temp}, 0x2) # IR bit",
            f"CSRS(hcounteren, x{r_temp})",
            f"CSRC(scounteren, x{r_temp})",
            f"CSRS(mcounteren, x{r_temp})",
            "",
            test_data.add_testcase("instret_scounteren_0_hcouonteren_1", coverpoint, covergroup),
            "# Go to VU mode to execute the instruction",
            "RVTEST_GOTO_LOWER_MODE VUmode",
            f"csrr x{r_temp}, instret",
            "#if __riscv_xlen == 32",
            f"csrr x{r_temp}, instreth",
            "#endif",
            "",
        ]
    )

    lines.extend(
        [
            "# execute hlv.w, hlvx.wu, hsv.w, hfence.vvma, hfence.gvma",
            "",
            f"LA(x{r_address}, scratch)",
            test_data.add_testcase("hlv", coverpoint, covergroup),
            f"hlv.w x{r_temp}, (x{r_address})",
            "",
            test_data.add_testcase("hlvx", coverpoint, covergroup),
            f"hlvx.wu x{r_temp}, (x{r_address})",
            "",
            test_data.add_testcase("hsv", coverpoint, covergroup),
            f"LI(x{r_temp}, 0xBAD)",
            f"hsv.w x{r_temp}, (x{r_address})",
            "",
            test_data.add_testcase("hfence_vvma", coverpoint, covergroup),
            "hfence.vvma",
            "",
            test_data.add_testcase("hfence_gvma", coverpoint, covergroup),
            "hfence.gvma",
            "",
        ]
    )

    lines.extend(
        [
            "# read vstval, htval, stval",
            "",
            test_data.add_testcase("vstval", coverpoint, covergroup),
            f"csrr x{r_temp}, vstval",
            "",
            test_data.add_testcase("htval", coverpoint, covergroup),
            f"csrr x{r_temp}, htval",
            "",
            test_data.add_testcase("stval", coverpoint, covergroup),
            f"csrr x{r_temp}, stval",
            "",
        ]
    )

    lines.extend(
        [
            "# with mstatus.TVM = 0, read satp, vsatp",
            "RVTEST_GOTO_MMODE",
            f"LI(x{r_temp}, 0x100000) # TVM bit",
            f"CSRC(mstatus, x{r_temp})",
            "RVTEST_GOTO_LOWER_MODE VUmode",
            test_data.add_testcase("satp", coverpoint, covergroup),
            f"csrr x{r_temp}, satp",
            test_data.add_testcase("vsatp", coverpoint, covergroup),
            f"csrr x{r_temp}, vsatp",
            "",
        ]
    )

    lines.extend(
        [
            "# wfi with mstatus.TW=0",
            "RVTEST_GOTO_MMODE",
            f"LI(x{r_temp}, 0x200000) # TW bit",
            f"CSRC(mstatus, x{r_temp})",
            "",
            "RVTEST_GOTO_LOWER_MODE VUmode",
            test_data.add_testcase("wfi", coverpoint, covergroup),
            "wfi",
        ]
    )

    lines.extend(
        [
            "# Execute sret, sfence.vma",
            test_data.add_testcase("sret", coverpoint, covergroup),
            "sret",
            test_data.add_testcase("sfence_vma", coverpoint, covergroup),
            "sfence.vma",
        ]
    )
    test_data.int_regs.return_registers([r_temp, r_address])

    return lines


def _generate_loadstore_priv_tests(test_data: TestData) -> list[str]:
    """Generate load/store Hypervisor tests

    In each privilege mode {M/HS/VS/U/VU} with hstatus.HU={0/1},
    attempt {HLV.W, HLVX.W, HSV.W} from scratch memory
    5 x 2 x 3 bins
    """

    covergroup, coverpoint = _CG, "cp_loadstore_priv"
    r_temp, r_address = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, _generate_loadstore_priv_tests.__doc__),
    ]

    priv_mode = ["M", "HS", "U", "VS", "VU"]
    instr = ["hlv.w", "hlvx.wu", "hsv.w"]

    for priv in priv_mode:
        for hu_val in [0, 1]:
            for hInstr in instr:
                binname = f"{hInstr}_{priv}_hstatusHU_{hu_val}"

                lines.extend(
                    [
                        "# --- M mode setup ---",
                        "# Clear medeleg and hedeleg",
                        "CSRW(medeleg, zero)",
                        "CSRW(hedeleg, zero)",
                        "# Write to hstatus.HU based on bins",
                        f"LI(x{r_temp}, 0x200) # HU bit",
                        f"{'CSRS' if hu_val else 'CSRC'}(hstatus, x{r_temp})",
                        "",
                        f"LA(x{r_address}, scratch)",
                    ]
                )

                if hInstr == "hsv.w":
                    lines.extend(["# Set up the value to load", f"LI(x{r_temp}, 0xDEADBEEF)"])

                lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
                if priv != "M":
                    lines.append(f"RVTEST_GOTO_LOWER_MODE {priv}mode")
                lines.extend(
                    [
                        "# Execute the instr based on bins",
                        f"{hInstr} x{r_temp}, (x{r_address})",
                        "",
                    ]
                )

                if priv != "M":
                    lines.extend(
                        [
                            "# Return to M mode",
                            "RVTEST_GOTO_MMODE",
                        ]
                    )

    test_data.int_regs.return_registers([r_temp, r_address])
    return lines


def _generate_hfence_priv_tests(test_data: TestData) -> list[str]:
    """Generate hfence priv test

    In each privilege mode {M/HS/VS/U/VU} with mstatus.TVM={0/1}, hstatus.VTVM = {0/1},
    attempt {sfence.vma, hfence.vvma, hfence.gvma}
    5 x 2 x 2 x 3 bins
    """

    covergroup, coverpoint = _CG, "cp_hfence_priv"
    r_temp = test_data.int_regs.get_register(exclude_regs=[])

    lines = [
        comment_banner(coverpoint, _generate_hfence_priv_tests.__doc__),
    ]

    priv_mode = ["M", "HS", "U", "VS", "VU"]
    instr = ["sfence.vma", "hfence.vvma", "hfence.gvma"]

    for priv in priv_mode:
        for tvm_val in [0, 1]:
            for vtvm_val in [0, 1]:
                for fInstr in instr:
                    binname = f"{fInstr}_{priv}_mstatusTVM_{tvm_val}_hstatusVTVM_{vtvm_val}"

                    lines.extend(
                        [
                            "# --- M mode setup ---",
                            "# Clear medeleg and hedeleg",
                            "CSRW(medeleg, zero)",
                            "CSRW(hedeleg, zero)",
                            "# Write to hstatus.VTVM based on bins",
                            f"LI(x{r_temp}, 0x100000) # VTVM/TVM bit",
                            f"{'CSRS' if vtvm_val else 'CSRC'}(hstatus, x{r_temp})",
                            "",
                            "# Write to mstatus.TVM based on bins",
                            f"{'CSRS' if tvm_val else 'CSRC'}(mstatus, x{r_temp})",
                            "",
                        ]
                    )

                    lines.append(test_data.add_testcase(binname, coverpoint, covergroup))
                    if priv != "M":
                        lines.append(f"RVTEST_GOTO_LOWER_MODE {priv}mode")
                    lines.extend(
                        [
                            "# Execute the instr based on bins",
                            f"{fInstr}",
                            "",
                        ]
                    )
                    if priv != "M":
                        lines.extend(
                            [
                                "# Return to M mode",
                                "RVTEST_GOTO_MMODE",
                            ]
                        )
    test_data.int_regs.return_register(r_temp)

    return lines


# skipped all the identity page table stuff because I am not sure about how to set it up
# set virtual address to map to the same place as physical address


def _generate_hlv_address_misaligned_tests(test_data: TestData) -> list[str]:
    """Generate M mode hlv address misaligned test

    In M mode with identity page tables set up and XR permission,
    attempt hlv.{b, bu, h, hu, w} and hlvx.{hu, wu} on address with every combination of three lsbs:000-111.
    RV64:
    also hlv.d and hlv.wu

    RV32: 7 instr x 8 lsb
    RV64: 9 instr x 8 lsb
    """

    covergroup, coverpoint = _CG, "cp_hlv_address_misaligned"

    lines = [
        comment_banner(coverpoint, _generate_hlv_address_misaligned_tests.__doc__),
    ]

    ######### USE MACRO HERE TO SET UP IDENTITY PAGE TABLE #########
    # TODO

    ################# NOW TEST THE INSTRUCTIONS #####################
    load_ops = ["hlv.b", "hlv.bu", "hlv.h", "hlv.hu", "hlv.w", "hlvx.hu", "hlvx.wu"]

    for offset in range(8):
        for op in load_ops:
            lines.append(f"\n# Testcase: {op} with offset {offset} (LSBs: {offset:03b})")
            lines.extend(add_load_misaligned_test(op, offset, test_data, coverpoint, covergroup))

        lines.append("#if __riscv_xlen == 64")
        for op in ["hlv.d", "hlv.wu"]:
            lines.append(f"\n# Testcase: {op} with offset {offset} (LSBs: {offset:03b})")
            lines.extend(add_load_misaligned_test(op, offset, test_data, coverpoint, covergroup))
        lines.append("#endif")

    return lines


def _generate_hlv_access_fault_tests(test_data: TestData) -> list[str]:
    """Generate M mode hlv access fault test

    In M mode with identity page tables set up and XR permission,
    attempt hlv.{b, bu, h, hu, w} and hlvx.{hu, wu} from illegal address (parameterized).
    RV64:
    also hlv.d and hlv.wu

    RV32: 7 instr
    RV64: 9 instr
    """

    covergroup, coverpoint = _CG, "cp_hlv_access_fault"
    r_temp, r_address = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, _generate_hlv_access_fault_tests.__doc__),
    ]

    ######### USE MACRO HERE TO SET UP IDENTITY PAGE TABLE #########
    # TODO

    ################# NOW TEST THE INSTRUCTIONS #####################
    load_ops = ["hlv.b", "hlv.bu", "hlv.h", "hlv.hu", "hlv.w", "hlvx.hu", "hlvx.wu"]

    for op in load_ops:
        lines.append(f"\n# Testcase: {op} access fault")
        lines.append(f"LA(x{r_address}, RVMODEL_ACCESS_FAULT_ADDRESS)")
        lines.extend(
            [
                test_data.add_testcase(f"{op}_fault", coverpoint, covergroup),
                f"{op} x{r_temp}, 0(x{r_address})",
                "nop",
            ]
        )
    lines.extend(["", "#if __riscv_xlen == 64"])
    for op in ["hlv.d", "hlv.wu"]:
        lines.append(f"\n# Testcase: {op} access fault")
        lines.append(f"LA(x{r_address}, RVMODEL_ACCESS_FAULT_ADDRESS)")
        lines.extend(
            [
                test_data.add_testcase(f"{op}_fault", coverpoint, covergroup),
                f"{op} x{r_temp}, 0(x{r_address})",
                "nop",
            ]
        )
    test_data.int_regs.return_registers([r_temp, r_address])
    return lines


def _generate_hsv_address_misaligned_tests(test_data: TestData) -> list[str]:
    """Generate M mode hsv address misaligned test

    In M mode with identity page tables set up and WR permission,
    attempt hsv.{b, h, w} on address with every combination of three lsbs:000-111.
    For RV64, also hsv.d.

    RV32: 3 instr x 8 lsb
    RV64: 4 instr x 8 lsb
    """

    covergroup, coverpoint = _CG, "cp_hsv_address_misaligned"

    lines = [
        comment_banner(coverpoint, _generate_hsv_address_misaligned_tests.__doc__),
    ]

    ######### USE MACRO HERE TO SET UP IDENTITY PAGE TABLE #########
    # TODO

    ################# NOW TEST THE INSTRUCTIONS #####################
    store_ops = ["hsv.b", "hsv.h", "hsv.w"]

    for offset in range(8):
        for op in store_ops:
            lines.append(f"\n# Testcase: {op} with offset {offset} (LSBs: {offset:03b})")
            lines.extend(add_store_misaligned_test(op, offset, test_data, coverpoint, covergroup))

        lines.append("#if __riscv_xlen == 64")
        lines.append(f"\n# Testcase: hsv.d with offset {offset} (LSBs: {offset:03b})")
        lines.extend(add_store_misaligned_test("hsv.d", offset, test_data, coverpoint, covergroup))
        lines.append("#endif")

    return lines


def _generate_hsv_access_fault_tests(test_data: TestData) -> list[str]:
    """Generate M mode hsv access fault test

    In M mode with identity page tables set up and WR permission,
    attempt hsv.{b, h, w} from an illegal address (parameterized).
    For RV64, also hsv.d.

    RV32: 3 instr
    RV64: 4 instr
    """

    covergroup, coverpoint = _CG, "cp_hsv_access_fault"
    r_temp, r_address = test_data.int_regs.get_registers(2, exclude_regs=[0])

    lines = [
        comment_banner(coverpoint, _generate_hsv_access_fault_tests.__doc__),
    ]

    ######### USE MACRO HERE TO SET UP IDENTITY PAGE TABLE #########
    # TODO

    ################# NOW TEST THE INSTRUCTIONS #####################
    store_ops = ["hsv.b", "hsv.h", "hsv.w"]
    test_values = {"hsv.b": "0xAB", "hsv.h": "0xBEAD", "hsv.w": "0xADDEDCAB", "hsv.d": "0xADDEDCABADDEDCAB"}

    for op in store_ops:
        lines.extend(
            [
                f"\n# Testcase: {op} access fault",
                f"LI(x{r_address}, RVMODEL_ACCESS_FAULT_ADDRESS)",
                f"LI(x{r_temp}, {test_values[op]})",
                test_data.add_testcase(f"{op}_fault", coverpoint, covergroup),
                f"{op} x{r_temp}, 0(x{r_address})",
                "nop",
            ]
        )

    lines.extend(
        [
            "",
            "#if __riscv_xlen == 64",
            "\n# Testcase: hsv.d access fault",
            f"LI(x{r_address}, RVMODEL_ACCESS_FAULT_ADDRESS)",
            f"LI(x{r_temp}, {test_values['hsv.d']})",
            test_data.add_testcase("hsv.d_fault", coverpoint, covergroup),
            f"sd x{r_temp}, 0(x{r_address})",
            "nop",
            "",
            "#endif",
            "#endif",
        ]
    )

    test_data.int_regs.return_registers([r_address, r_temp])
    return lines


# would it be better to condence all the following into one coverpoint


def _generate_xtinst_instr_misaligned_tests(test_data: TestData) -> list[str]:
    """Generate xtinst instruction misaligned tests

    From VS mode with medeleg = {0s/1s}, hedeleg = 0,
    0xDEADBEEF written to mtinst and mtval2, jump to misaligned address.
    2 bins
    """
    covergroup, coverpoint = _CG, "cp_xtinst_instr_misaligned"
    r_temp = test_data.int_regs.get_register(exclude_regs=[])

    lines = [
        comment_banner(coverpoint, _generate_xtinst_instr_misaligned_tests.__doc__),
    ]

    for medeleg_val in [0, 1]:
        lines.extend(
            [
                "# Setup in M mode",
                "# Initialize mtinst, mtval2, and htinst",
                f"LI(x{r_temp}, 0xDEADBEEF)",
                f"CSRW(mtinst, x{r_temp})",
                f"CSRW(htinst, x{r_temp})",
                f"CSRW(mtval2, x{r_temp})",
                "",
                "# Clear hedeleg",
                "CSRW(hedeleg, zero)",
                "",
                "# Write to medeleg based on bins",
                f"LI(x{r_temp}, -1)",
                f"{'CSRS' if medeleg_val else 'CSRC'}(medeleg, x{r_temp})",
                "RVTEST_GOTO_LOWER_MODE VSmode",
            ]
        )

        lines.extend(
            [
                "# perform instruction adr misaligned exception",
                test_data.add_testcase(f"medeleg{medeleg_val}", coverpoint, covergroup),
                "jal x0, .+6",
                "# jal by 6 lands in the upper half of the next instruction (0x0001 -> c.nop)",
                "addi x0, x2, 0",
                "nop",
                "",
                "RVTEST_GOTO_MMODE",
            ]
        )
    test_data.int_regs.return_register(r_temp)

    return lines


def _generate_xtinst_instr_access_tests(test_data: TestData) -> list[str]:
    """Generate xtinst instruction access tests

    From VS mode with medeleg = {0/1}, hedeleg = 0,
    0xDEADBEEF written to mtinst and mtval2, jump to access fault address
    2 bins
    """
    covergroup, coverpoint = _CG, "cp_xtinst_instr_access"
    r_temp = test_data.int_regs.get_register(exclude_regs=[])

    lines = [
        comment_banner(coverpoint, _generate_xtinst_instr_access_tests.__doc__),
    ]

    for medeleg_val in [0, 1]:
        lines.extend(
            [
                "# Setup in M mode",
                "# Initialize mtinst, mtval2, and htinst",
                f"LI(x{r_temp}, 0xDEADBEEF)",
                f"CSRW(mtinst, x{r_temp})",
                f"CSRW(htinst, x{r_temp})",
                f"CSRW(mtval2, x{r_temp})",
                "",
                "# Clear hedeleg",
                "CSRW(hedeleg, zero)",
                "",
                "# Write to medeleg based on bins",
                f"LI(x{r_temp}, -1)",
                f"{'CSRS' if medeleg_val else 'CSRC'}(medeleg, x{r_temp})",
                "RVTEST_GOTO_LOWER_MODE VSmode",
            ]
        )

        lines.extend(
            [
                "# perform instruction access fault",
                "#ifdef RVMODEL_ACCESS_FAULT_ADDRESS",
                f"LA(x{r_temp}, RVMODEL_ACCESS_FAULT_ADDRESS)",
                "LI(x4, 0xACCE)",  # trap handler checks x4 and returns via x1 (ra) instead of mepc
                test_data.add_testcase(f"medeleg{medeleg_val}", coverpoint, covergroup),
                f"jalr x1, 0(x{r_temp})",
                "nop",
                "#endif",
                "",
                "RVTEST_GOTO_MMODE",
            ]
        )
    test_data.int_regs.return_register(r_temp)

    return lines


def _generate_xtinst_illegal_instr_tests(test_data: TestData) -> list[str]:
    """Generate xtinst illegal instruction tests

    From VS mode with medeleg = {0/1}, hedeleg = 0, execute illegal instruction all 0s
    2 bins
    """
    covergroup, coverpoint = _CG, "cp_xtinst_illegal_instr"
    r_temp = test_data.int_regs.get_register(exclude_regs=[])

    lines = [
        comment_banner(coverpoint, _generate_xtinst_illegal_instr_tests.__doc__),
    ]

    for medeleg_val in [0, 1]:
        lines.extend(
            [
                "# Setup in M mode",
                "# Initialize mtinst, mtval2, and htinst",
                f"LI(x{r_temp}, 0xDEADBEEF)",
                f"CSRW(mtinst, x{r_temp})",
                f"CSRW(htinst, x{r_temp})",
                f"CSRW(mtval2, x{r_temp})",
                "",
                "# Clear hedeleg",
                "CSRW(hedeleg, zero)",
                "",
                "# Write to medeleg based on bins",
                f"LI(x{r_temp}, -1)",
                f"{'CSRS' if medeleg_val else 'CSRC'}(medeleg, x{r_temp})",
                "RVTEST_GOTO_LOWER_MODE VSmode",
            ]
        )

        lines.extend(
            [
                "# perform illegal instruction exception",
                ".align 2",
                test_data.add_testcase(f"medeleg{medeleg_val}", coverpoint, covergroup),
                ".word 0x00000000",
                "nop",
                "",
                "RVTEST_GOTO_MMODE",
            ]
        )
    test_data.int_regs.return_register(r_temp)

    return lines


def _generate_xtinst_breakpoint_tests(test_data: TestData) -> list[str]:
    """Generate xtinst breakpoint tests

    From VS mode with medeleg = {0/1}, hedeleg = 0, execute ebreak
    2 bins
    """
    covergroup, coverpoint = _CG, "cp_xtinst_breakpoint"
    r_temp = test_data.int_regs.get_register(exclude_regs=[])

    lines = [
        comment_banner(coverpoint, _generate_xtinst_breakpoint_tests.__doc__),
    ]

    for medeleg_val in [0, 1]:
        lines.extend(
            [
                "# Setup in M mode",
                "# Initialize mtinst, mtval2, and htinst",
                f"LI(x{r_temp}, 0xDEADBEEF)",
                f"CSRW(mtinst, x{r_temp})",
                f"CSRW(htinst, x{r_temp})",
                f"CSRW(mtval2, x{r_temp})",
                "",
                "# Clear hedeleg",
                "CSRW(hedeleg, zero)",
                "",
                "# Write to medeleg based on bins",
                f"LI(x{r_temp}, -1)",
                f"{'CSRS' if medeleg_val else 'CSRC'}(medeleg, x{r_temp})",
                "RVTEST_GOTO_LOWER_MODE VSmode",
            ]
        )

        lines.extend(
            [
                "# Trigger ebreak exception",
                test_data.add_testcase(f"medeleg{medeleg_val}", coverpoint, covergroup),
                "ebreak",
                "nop",
                "",
                "RVTEST_GOTO_MMODE",
            ]
        )
    test_data.int_regs.return_register(r_temp)

    return lines


def _generate_xtinst_virt_instr_tests(test_data: TestData) -> list[str]:
    """Generate xtinst virtual instruction exception tests

    From VS mode with medeleg = {0/1}, hedeleg = 0, csrr vstval
    2 bins
    """
    covergroup, coverpoint = _CG, "cp_xtinst_virt_instr"
    r_temp = test_data.int_regs.get_register(exclude_regs=[])

    lines = [
        comment_banner(coverpoint, _generate_xtinst_virt_instr_tests.__doc__),
    ]

    for medeleg_val in [0, 1]:
        lines.extend(
            [
                "# Setup in M mode",
                "# Initialize mtinst, mtval2, and htinst",
                f"LI(x{r_temp}, 0xDEADBEEF)",
                f"CSRW(mtinst, x{r_temp})",
                f"CSRW(htinst, x{r_temp})",
                f"CSRW(mtval2, x{r_temp})",
                "",
                "# Clear hedeleg",
                "CSRW(hedeleg, zero)",
                "",
                "# Write to medeleg based on bins",
                f"LI(x{r_temp}, -1)",
                f"{'CSRS' if medeleg_val else 'CSRC'}(medeleg, x{r_temp})",
                "RVTEST_GOTO_LOWER_MODE VSmode",
            ]
        )

        lines.extend(
            [
                "# Trigger virtual instruction exception",
                test_data.add_testcase(f"medeleg{medeleg_val}", coverpoint, covergroup),
                f"csrr x{r_temp}, vstval",
                "nop",
                "",
                "RVTEST_GOTO_MMODE",
            ]
        )
    test_data.int_regs.return_register(r_temp)

    return lines


def _generate_xtinst_load_misaligned_tests(test_data: TestData) -> list[str]:
    """Generate xtinst load misaligned exception tests

    From VS mode with medeleg = {0/1}, hedeleg = 0, execute misaligned load
    2 bins
    """
    covergroup, coverpoint = _CG, "cp_xtinst_load_misaligned"
    r_temp = test_data.int_regs.get_register(exclude_regs=[])

    lines = [
        comment_banner(coverpoint, _generate_xtinst_load_misaligned_tests.__doc__),
    ]

    for medeleg_val in [0, 1]:
        lines.extend(
            [
                "# Setup in M mode",
                "# Initialize mtinst, mtval2, and htinst",
                f"LI(x{r_temp}, 0xDEADBEEF)",
                f"CSRW(mtinst, x{r_temp})",
                f"CSRW(htinst, x{r_temp})",
                f"CSRW(mtval2, x{r_temp})",
                "",
                "# Clear hedeleg",
                "CSRW(hedeleg, zero)",
                "",
                "# Write to medeleg based on bins",
                f"LI(x{r_temp}, -1)",
                f"{'CSRS' if medeleg_val else 'CSRC'}(medeleg, x{r_temp})",
                "RVTEST_GOTO_LOWER_MODE VSmode",
            ]
        )

        lines.extend(
            [
                "# perform load address misaligned exception",
                f"LA(x{r_temp}, scratch)",
                f"addi x{r_temp}, x{r_temp}, 1",
                test_data.add_testcase(f"medeleg{medeleg_val}", coverpoint, covergroup),
                f"lw x{r_temp}, 0(x{r_temp})",
                "nop",
                "",
                "RVTEST_GOTO_MMODE",
            ]
        )
    test_data.int_regs.return_register(r_temp)

    return lines


def _generate_xtinst_load_access_tests(test_data: TestData) -> list[str]:
    """Generate xtinst load access fault tests

    From VS mode with medeleg = {0/1}, hedeleg = 0, execute load access fault
    2 bins
    """
    covergroup, coverpoint = _CG, "cp_xtinst_load_access"
    r_temp = test_data.int_regs.get_register(exclude_regs=[])

    lines = [
        comment_banner(coverpoint, _generate_xtinst_load_access_tests.__doc__),
    ]

    for medeleg_val in [0, 1]:
        lines.extend(
            [
                "# Setup in M mode",
                "# Initialize mtinst, mtval2, and htinst",
                f"LI(x{r_temp}, 0xDEADBEEF)",
                f"CSRW(mtinst, x{r_temp})",
                f"CSRW(htinst, x{r_temp})",
                f"CSRW(mtval2, x{r_temp})",
                "",
                "# Clear hedeleg",
                "CSRW(hedeleg, zero)",
                "",
                "# Write to medeleg based on bins",
                f"LI(x{r_temp}, -1)",
                f"{'CSRS' if medeleg_val else 'CSRC'}(medeleg, x{r_temp})",
                "RVTEST_GOTO_LOWER_MODE VSmode",
            ]
        )

        lines.extend(
            [
                "# perform load access fault",
                "#ifdef RVMODEL_ACCESS_FAULT_ADDRESS",
                f"LA(x{r_temp}, RVMODEL_ACCESS_FAULT_ADDRESS)",
                test_data.add_testcase(f"medeleg{medeleg_val}", coverpoint, covergroup),
                f"lw x{r_temp}, 0(x{r_temp})",
                "nop",
                "#endif",
                "",
                "RVTEST_GOTO_MMODE",
            ]
        )
    test_data.int_regs.return_register(r_temp)

    return lines


def _generate_xtinst_store_misaligned_tests(test_data: TestData) -> list[str]:
    """Generate xtinst store misaligned exceptions tests

    From VS mode with medeleg = {0/1}, hedeleg = 0, execute misaligned store
    2 bins
    """
    covergroup, coverpoint = _CG, "cp_xtinst_store_misaligned"
    r_temp = test_data.int_regs.get_register(exclude_regs=[])

    lines = [
        comment_banner(coverpoint, _generate_xtinst_store_misaligned_tests.__doc__),
    ]

    for medeleg_val in [0, 1]:
        lines.extend(
            [
                "# Setup in M mode",
                "# Initialize mtinst, mtval2, and htinst",
                f"LI(x{r_temp}, 0xDEADBEEF)",
                f"CSRW(mtinst, x{r_temp})",
                f"CSRW(htinst, x{r_temp})",
                f"CSRW(mtval2, x{r_temp})",
                "",
                "# Clear hedeleg",
                "CSRW(hedeleg, zero)",
                "",
                "# Write to medeleg based on bins",
                f"LI(x{r_temp}, -1)",
                f"{'CSRS' if medeleg_val else 'CSRC'}(medeleg, x{r_temp})",
                "RVTEST_GOTO_LOWER_MODE VSmode",
            ]
        )

        lines.extend(
            [
                "# perform store address misaligned exception",
                f"LA(x{r_temp}, scratch)",
                f"addi x{r_temp}, x{r_temp}, 1",
                test_data.add_testcase(f"medeleg{medeleg_val}", coverpoint, covergroup),
                f"sw x{r_temp}, 0(x{r_temp})",
                "nop",
                "",
                "RVTEST_GOTO_MMODE",
            ]
        )
    test_data.int_regs.return_register(r_temp)

    return lines


def _generate_xtinst_store_access_tests(test_data: TestData) -> list[str]:
    """Generate xtinst store access fault tests

    From VS mode with medeleg = {0/1}, hedeleg = 0, execute store access fault
    2 bins
    """
    covergroup, coverpoint = _CG, "cp_xtinst_store_access"
    r_temp = test_data.int_regs.get_register(exclude_regs=[])

    lines = [
        comment_banner(coverpoint, _generate_xtinst_store_access_tests.__doc__),
    ]

    for medeleg_val in [0, 1]:
        lines.extend(
            [
                "# Setup in M mode",
                "# Initialize mtinst, mtval2, and htinst",
                f"LI(x{r_temp}, 0xDEADBEEF)",
                f"CSRW(mtinst, x{r_temp})",
                f"CSRW(htinst, x{r_temp})",
                f"CSRW(mtval2, x{r_temp})",
                "",
                "# Clear hedeleg",
                "CSRW(hedeleg, zero)",
                "",
                "# Write to medeleg based on bins",
                f"LI(x{r_temp}, -1)",
                f"{'CSRS' if medeleg_val else 'CSRC'}(medeleg, x{r_temp})",
                "RVTEST_GOTO_LOWER_MODE VSmode",
            ]
        )

        lines.extend(
            [
                "# perform store access fault",
                "#ifdef RVMODEL_ACCESS_FAULT_ADDRESS",
                f"LA(x{r_temp}, RVMODEL_ACCESS_FAULT_ADDRESS)",
                test_data.add_testcase(f"medeleg{medeleg_val}", coverpoint, covergroup),
                f"sw x{r_temp}, 0(x{r_temp})",
                "nop",
                "#endif",
                "",
                "RVTEST_GOTO_MMODE",
            ]
        )
    test_data.int_regs.return_register(r_temp)

    return lines


def _generate_xtinst_ecall_tests(test_data: TestData) -> list[str]:
    """Generate xtinst ecall tests

    From VS mode with medeleg = {0/1}, hedeleg = 0, execute ecall
    2 bins
    """
    covergroup, coverpoint = _CG, "cp_xtinst_ecall"
    r_temp = test_data.int_regs.get_register(exclude_regs=[])

    lines = [
        comment_banner(coverpoint, _generate_xtinst_ecall_tests.__doc__),
    ]

    for medeleg_val in [0, 1]:
        lines.extend(
            [
                "# Setup in M mode",
                "# Initialize mtinst, mtval2, and htinst",
                f"LI(x{r_temp}, 0xDEADBEEF)",
                f"CSRW(mtinst, x{r_temp})",
                f"CSRW(htinst, x{r_temp})",
                f"CSRW(mtval2, x{r_temp})",
                "",
                "# Clear hedeleg",
                "CSRW(hedeleg, zero)",
                "",
                "# Write to medeleg based on bins",
                f"LI(x{r_temp}, -1)",
                f"{'CSRS' if medeleg_val else 'CSRC'}(medeleg, x{r_temp})",
                "RVTEST_GOTO_LOWER_MODE VSmode",
            ]
        )

        lines.extend(
            [
                "# execute ecall",
                test_data.add_testcase(f"medeleg{medeleg_val}", coverpoint, covergroup),
                "ecall",
                "nop",
                "",
                "RVTEST_GOTO_MMODE",
            ]
        )
    test_data.int_regs.return_register(r_temp)

    return lines


@add_priv_test_generator(
    "ExceptionsH",
    required_extensions=["S", "H"],
    march_extensions=["H", "Svinval"],
)
def make_exceptionsh(test_data: TestData) -> list[str]:
    """Main entry point for Hypervisor extension exception test generation (refactored)."""
    lines: list[str] = [
        "CSRW(medeleg, zero)",
    ]

    lines.extend(_generate_hedeleg_tests(test_data))
    lines.extend(_generate_ecall_to_vs_tests(test_data))
    lines.extend(_generate_ecall_to_hs_tests(test_data))
    lines.extend(_generate_ecall_to_m_tests(test_data))
    lines.extend(_generate_ebreak_to_m_tests(test_data))

    lines.extend(_generate_vstvec_tests(test_data))
    lines.extend(_generate_priority_tests(test_data))
    lines.extend(_generate_virtual_instruction_vs_tests(test_data))
    lines.extend(_generate_virtual_instruction_vu_tests(test_data))

    lines.extend(_generate_loadstore_priv_tests(test_data))
    lines.extend(_generate_hfence_priv_tests(test_data))

    lines.extend(_generate_xtinst_instr_misaligned_tests(test_data))
    lines.extend(_generate_xtinst_instr_access_tests(test_data))
    lines.extend(_generate_xtinst_illegal_instr_tests(test_data))
    lines.extend(_generate_xtinst_breakpoint_tests(test_data))
    lines.extend(_generate_xtinst_virt_instr_tests(test_data))
    lines.extend(_generate_xtinst_load_misaligned_tests(test_data))
    lines.extend(_generate_xtinst_load_access_tests(test_data))
    lines.extend(_generate_xtinst_store_misaligned_tests(test_data))
    lines.extend(_generate_xtinst_store_access_tests(test_data))
    lines.extend(_generate_xtinst_ecall_tests(test_data))

    return lines
