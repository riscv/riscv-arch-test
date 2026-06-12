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
from testgen.priv.registry import add_priv_test_generator

_CG = "ExceptionsH_cg"


# def _generate_hedeleg_tests(test_data: TestData) -> list[str]:

# covergroup, coverpoint = _CG, "cp_hedeleg"
# lines = [
#     comment_banner(coverpoint, _generate_hedeleg_tests.__doc__),
# ]

# # WIP

# return lines


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

    priv_mode = [("U", 0x100), ("VS", 0x200), ("VU", 0x100)]

    for priv, deleg_bit in priv_mode:
        for spvp in [0, 1]:
            binname = f"mode_{priv}_SPVP_{spvp}"
            lines.extend(
                [
                    "--- M mode setup ---",
                    f"# Set medeleg for ecall from {priv} mode",
                    f"LI(x{r_temp}, {deleg_bit})",
                    f"CSRS(medeleg, x{r_temp})",
                    "",
                    "# Clear hedelegCSRW(hedeleg, zero)",
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
                "--- M mode setup ---",
                "# Clear medelegCSRW(medeleg, zero)",
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
                "--- M mode setup ---",
                "# Clear medelegCSRW(medeleg, zero)",
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
                                "--- M mode setup ---",
                                "# Clear medeleg and hedelegCSRW(medeleg, zero)",
                                "CSRW(hedeleg, zero)",
                                f"# Write to hstatus.HU based on binsLI(x{r_temp}, 0x200) # HU bit",
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

                        lines.extend(test_data.add_testcase(binname, coverpoint, covergroup))
                        if priv != "M":
                            lines.append(f"RVTEST_GOTO_LOWER_MODE {priv}mode")
                        lines.extend(
                            [
                                f"# Execute the instr based on bins{hInstr} x{r_temp}, (x{r_address})",
                            ]
                        )

    test_data.int_regs.return_registers([r_temp, r_address])
    return lines


# def _generate_virtual_instruction_vs_tests(test_data: TestData) -> list[str]:
#     """Generate virtual instructions Exceptions from VS mode

#     read instret with hcounteren[2] = 0, mcounteren[2] = 1
#     execute hlv.w, hlvx.wu, hsv.w, hfence.vvma, hfence.gvma
#     read vstval, htval
#     with mstatus.TVM = 0, read satp, vsatp
#     wfi with hstatus.VTW=1, mstatus.TW=0, no interrupt firing
#     sret with hstatus.VTSR=1
#     {sfence.vma, sinval.vma, read satp} with hstatus.VTVM=1
#     RV32 only:
#     access instreth with hcounteren[2] = 0, mcounteren[2] = 1
#     read hedelegh
#     """

# covergroup, coverpoint = _CG, "cp_priority"
# r_temp, r_address = test_data.int_regs.get_registers(2, exclude_regs=[0])

# lines = [
#     comment_banner(coverpoint, _generate_priority_tests.__doc__),
# ]

# lines.append("#if __riscv_xlen == 64")

# return lines


@add_priv_test_generator(
    "ExceptionsH",
    required_extensions=["S", "H"],
    extra_defines=[],
)
def make_exceptionss(test_data: TestData) -> list[str]:
    """Main entry point for S-mode exception test generation (refactored)."""
    lines: list[str] = []

    ### not sure ###
    # lines.extend(_generate_hedeleg_tests(test_data))

    ### written ###
    lines.extend(_generate_ecall_to_vs_tests(test_data))
    lines.extend(_generate_ecall_to_hs_tests(test_data))
    lines.extend(_generate_ecall_to_m_tests(test_data))
    lines.extend(_generate_ebreak_to_m_tests(test_data))

    ### not sure ###
    lines.extend(_generate_vstvec_tests(test_data))
    lines.extend(_generate_priority_tests(test_data))

    return lines
