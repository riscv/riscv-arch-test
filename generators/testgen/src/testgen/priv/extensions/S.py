##################################
# S.py
#
# S supervisor mode privileged extension test generator.
# David_Harris@hmc.edu 1 March 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""S supervisor privileged extension test generator."""

from random import seed

from testgen.asm.csr import csr_access_test, csr_walk_test, gen_csr_read_sigupd, gen_csr_write_sigupd
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _generate_scause_tests(test_data: TestData) -> list[str]:
    """Generate tests for scause CSR."""
    covergroup = "S_scause_cg"
    save_reg, check_reg, temp_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    ######################################
    coverpoint = "cp_scause_write_exception"
    ######################################
    lines = [
        "",
        f"CSRR(x{save_reg}, scause)     # save CSR before testing it",
        comment_banner(
            coverpoint,
            "with interrupt = 0: test writing each exception cause",
        ),
    ]

    for i in range(24):
        if i in {14, 17}:  # skip reserved causes
            continue
        lines.extend(
            [
                f"    LI(x{check_reg}, {i})           # exception cause {i}",
                test_data.add_testcase(f"b_{i}", coverpoint, covergroup),
                gen_csr_write_sigupd(check_reg, "scause", test_data),
            ]
        )

    ######################################
    coverpoint = "cp_scause_write_interrupt"
    ######################################

    lines.extend(
        [
            comment_banner(
                coverpoint,
                "with interrupt = 1: test writing each interrupt cause",
            ),
            f"    SET_MSB(x{temp_reg})  # set x{temp_reg} to have msb = 1 for interrupt tests",
        ]
    )

    for i in range(14):
        if i in {0, 4, 8}:  # skip reserved causes
            continue
        lines.extend(
            [
                f"    LI(x{check_reg}, {i})           # interrupt cause {i}",
                f"    or x{check_reg}, x{check_reg}, x{temp_reg}          # set interrupt bit",
                test_data.add_testcase(f"b_{i}", coverpoint, covergroup),
                gen_csr_write_sigupd(check_reg, "scause", test_data),
            ]
        )

    lines.append(f"\n    CSRW(scause, x{save_reg})       # restore CSR")

    test_data.int_regs.return_registers([save_reg, check_reg, temp_reg])
    return lines


def _generate_sstatus_sd_tests(test_data: TestData) -> list[str]:
    """Generate sstatus SD field write tests."""
    ######################################
    covergroup = "S_sstatus_cg"
    coverpoint = "cp_sstatus_sd_write"
    ######################################
    save_reg, check_reg, reg1, reg2, reg3 = test_data.int_regs.get_registers(5, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "Write all combinations of sstatus.SD = {0/1}, FS/XS/VS = {00, 01, 10, 11}\n"
            "sstatus.SD is read-only, so nothing should happen",
        ),
        "",
        f"SET_MSB(x{reg1}) # put a 1 in the msb of x{reg1} (XLEN-1)",
        f"CSRR(x{save_reg}, sstatus)        # read and save sstatus",
        f"# set up x{reg3} with sstatus except SD, FS, XS, VS cleared",
        f"not x{reg2}, x{reg1}              # x{reg2} has all but msb set",
        f"and x{reg3}, x{save_reg}, x{reg2} # clear SD bit",
        f"LI(x{reg2}, 0x1E600)              # x{reg2} has all FS, XS, VS bits set (bits [14:13], [16:15], [10:9], respectively)",
        f"not x{reg2}, x{reg2}              # x{reg2} has all but FS, XS, VS bits set",
        f"and x{reg3}, x{reg3}, x{reg2}     # clear FS, XS, VS bits",
    ]

    for sd in (0, 1):
        for fs in range(4):
            for xs in range(4):
                for vs in range(4):
                    binname = f"sd_{sd}_fs_{fs:02b}_xs_{xs:02b}_vs_{vs:02b}"
                    fields = fs << 13 | xs << 15 | vs << 9
                    lines.append(f"    LI(x{check_reg}, 0x{fields:08x})  # fs = {fs:02b} xs = {xs:02b} vs = {vs:02b}")
                    if sd == 1:
                        lines.append(f"    or x{check_reg}, x{check_reg}, x{reg1}      # set SD bit")
                    lines.extend(
                        [
                            f"    or x{check_reg}, x{check_reg}, x{reg3}   # value to write to sstatus with SD/FS/XS/VS bits set/clear",
                            test_data.add_testcase(binname, coverpoint, covergroup),
                            gen_csr_write_sigupd(check_reg, "sstatus", test_data),
                        ]
                    )
    lines.append(f"\n    CSRW(sstatus, x{save_reg})    # restore CSR")
    test_data.int_regs.return_registers([save_reg, check_reg, reg1, reg2, reg3])
    return lines


def _generate_priv_inst_tests(test_data: TestData) -> list[str]:
    """Generate ecall and ebreak and mret tests."""
    ######################################
    covergroup = "S_sprivinst_cg"
    coverpoint = "cp_sprivinst"
    ######################################

    lines = [
        comment_banner(
            coverpoint,
            "Executing ecall and ebreak and mret should cause an exception",
        ),
        # ecall test
        test_data.add_testcase("ecall", coverpoint, covergroup),
        "    ecall                 # test ecall instruction",
        "    nop                 # trap handler skips following instruction so this should not be executed",
        # ebreak test
        test_data.add_testcase("ebreak", coverpoint, covergroup),
        "    ebreak                # test ebreak instruction",
        "    nop                 # trap handler skips following instruction so this should not be executed",
        # mret test
        test_data.add_testcase("mret", coverpoint, covergroup),
        "    mret                  # test mret instruction",
        "    nop                 # trap handler skips following instruction so this should not be executed",
    ]

    return lines


def _generate_mretm_tests(test_data: TestData) -> list[str]:
    """Generate mret from M-mode with mpp, mprv, mpie, mie sweep."""
    ######################################
    covergroup = "S_sprivinst_cg"
    coverpoint = "cp_mret_m"
    ######################################
    save_reg, check_reg, reg1, reg2, reg3 = test_data.int_regs.get_registers(5, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "Execute mret while sweeping cross-product of mpp, mprv, mpie, mie",
        ),
        "",
        f"CSRR(x{save_reg}, mstatus)        # read and save mstatus",
        f"# set up x{reg1} with mstatus except MPP, MPRV, MPIE, MIE cleared",
        f"LI(x{reg2}, 0x21888)          # x{reg2} has all MPP, MPRV, MPIE, MIE bits set (bits [12:11], [17], [7], [3], respectively)",
        f"not x{reg2}, x{reg2}              # x{reg2} has all but MPP, MPRV, MPIE, MIE bits set",
        f"and x{reg1}, x{save_reg}, x{reg2}          # clear MPP, MPRV, MPIE, MIE bits",
    ]

    for mpp in (0, 1, 3):  # all modes
        for mprv in (0, 1):
            for mpie in (0, 1):
                for mie in (0, 1):
                    binname = f"mpp_{mpp:02b}_mprv_{mprv}_mpie_{mpie}_mie_{mie}"
                    fields = (mpp << 11) | (mprv << 17) | (mpie << 7) | (mie << 3)

                    lines.extend(
                        [
                            # Test the write value
                            f"    LI(x{check_reg}, 0x{fields:08x})  # mpp = {mpp:02b} mprv = {mprv} mpie = {mpie} mie = {mie}",
                            f"    or x{check_reg}, x{check_reg}, x{reg1}          # value to write to mstatus with MPP/MPRV/MPIE/MIE bits set/clear",
                            f"    LA(x{reg3}, 1f)             # return address after mret",
                            f"    CSRW(mepc, x{reg3})          # set mepc to return address",
                            f"    CSRW(mstatus, x{check_reg})       # write mstatus with MPP/MPRV/MPIE/MIE bits set/clear",
                            test_data.add_testcase(f"{binname}_wval", coverpoint, covergroup),
                            "    mret                   # test mret instruction",
                            f"   addi x{check_reg}, zero, -1              # should not be executed",
                            "1:                         # mret should return to here",
                            "    RVTEST_GOTO_MMODE      # make sure we return to machine mode",
                            write_sigupd(check_reg, test_data),
                            # Test mstatus was updated properly
                            gen_csr_read_sigupd(check_reg, "mstatus", test_data),
                        ]
                    )

    lines.append(f"\n    CSRW(mstatus, x{save_reg})    # restore CSR")
    test_data.int_regs.return_registers([save_reg, check_reg, reg1, reg2, reg3])
    return lines


def _generate_sretm_tests(test_data: TestData) -> list[str]:
    """Generate sret from M-mode with spp, mprv, spie, sie, tsr sweep."""
    ######################################
    covergroup = "S_sprivinst_cg"
    coverpoint = "cp_sret_m"
    ######################################
    save_reg, check_reg, reg1, reg2, reg3 = test_data.int_regs.get_registers(5, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "Execute sret while sweeping cross-product of mprv, spp, spie, sie, tsr\n"
            "Go to S or U mode depending on SPP.  SIE <- SPIE.  SPIE <- 1.  "
            "MPRV <- 0. SPP <- 0 (U-mode).  TSR has no effect.",
        ),
        "",
        f"CSRR(x{save_reg}, mstatus)        # read and save mstatus",
        f"# set up x{reg1} with mstatus except MPRV, SPP, SPIE, SIE, TSR cleared",
        f"LI(x{reg2}, 0x420122)          # x{reg2} has all MPRV, SPP, SPIE, SIE, TSR bits set (bits [17], [8], [5], [1], [22] respectively)",
        f"not x{reg2}, x{reg2}              # x{reg2} has all but MPRV, SPP, SPIE, SIE, TSR bits set",
        f"and x{reg1}, x{save_reg}, x{reg2}          # clear MPRV, SPP, SPIE, SIE, TSR bits",
    ]

    for spp in (0, 1):
        for mprv in (0, 1):
            for spie in (0, 1):
                for sie in (0, 1):
                    for tsr in (0, 1):
                        binname = f"spp_{spp}_mprv_{mprv}_spie_{spie}_sie_{sie}_tsr_{tsr}"
                        fields = (mprv << 17) | (spp << 8) | (spie << 5) | (sie << 1) | (tsr << 22)

                        lines.extend(
                            [
                                # Test the write value
                                f"    LI(x{check_reg}, 0x{fields:08x}) # mprv = {mprv} spp = {spp} spie = {spie} sie = {sie} tsr = {tsr}",
                                f"    or x{check_reg}, x{check_reg}, x{reg1}          # value to write to mstatus with MPRV/SPP/SPIE/SIE/TSR bits set/clear",
                                f"    LA(x{reg3}, 1f)             # return address after sret",
                                f"    CSRW(sepc, x{reg3})          # set sepc to return address (if S mode exists).",
                                f"    CSRW(mstatus, x{check_reg})       # write mstatus with MPRV/SPP/SPIE/SIE/TSR bits set/clear",
                                test_data.add_testcase(f"{binname}_wval", coverpoint, covergroup),
                                "    sret                   # test sret instruction, expect illegal instruction if S mode is not supported",
                                f"   addi x{check_reg}, zero, -1              # should not be executed",
                                "1:                         # sret should return to here",
                                write_sigupd(check_reg, test_data),
                                "    RVTEST_GOTO_MMODE      # make sure we return to machine mode",
                                # Test mstatus was updated properly
                                gen_csr_read_sigupd(check_reg, "mstatus", test_data),
                            ]
                        )

    lines.append(f"\n    CSRW(mstatus, x{save_reg})    # restore CSR")
    test_data.int_regs.return_registers([save_reg, check_reg, reg1, reg2, reg3])
    return lines


def _generate_srets_tests(test_data: TestData) -> list[str]:
    """Generate sret from S-mode with spp, mprv, spie, sie, tsr sweep."""
    ######################################
    covergroup = "S_sprivinst_cg"
    coverpoint = "cp_sret_s"
    ######################################
    seed(0)  # fixed seed for deterministic register allocation across runs
    save_reg, check_reg, reg1, reg2, reg3 = test_data.int_regs.get_registers(5, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "Execute sret from S-mode while sweeping cross-product of sstatus.spp, spie, sie; mstatus.tsr\n"
            "Go to S or U mode depending on SPP.  SIE <- SPIE.  SPIE <- 1.  "
            "MPRV <- 0. SPP <- 0 (U-mode).  TSR causes illegal instruction.",
        ),
        "",
        f"CSRR(x{save_reg}, sstatus)        # read and save sstatus",
        f"# set up x{reg1} with sstatus except SPP, SPIE, SIE cleared",
        f"LI(x{reg2}, 0x122)          # x{reg2} has all SPP, SPIE, SIE bits set (bits [8], [5], [1] respectively)",
        f"not x{reg2}, x{reg2}              # x{reg2} has all but SPP, SPIE, SIE bits set",
        f"and x{reg1}, x{save_reg}, x{reg2}          # clear SPP, SPIE, SIE bits",
    ]

    for tsr in (1, 0):
        lines.extend(
            [
                # Set mstatus.TSR from M-mode
                "\tRVTEST_GOTO_MMODE      # enter machine mode for twiddling mstatus.TSR",
                f"\tLI(x{check_reg}, {1 << 22})  # mstatus.TSR bit",
            ]
        )

        if tsr == 1:
            lines.append(f"\tCSRS(mstatus, x{check_reg})          # set TSR bit")
        else:
            lines.append(f"\tCSRC(mstatus, x{check_reg})          # clear TSR bit")
        lines.append("\tRVTEST_GOTO_LOWER_MODE Smode # return to supervisor mode to execute sret tests")

        for spp in (0, 1):
            for spie in (0, 1):
                for sie in (0, 1):
                    binname = f"spp_{spp}_spie_{spie}_sie_{sie}_tsr_{tsr}"
                    fields = (spp << 8) | (spie << 5) | (sie << 1)

                    lines.extend(
                        [
                            # Test the write value
                            f"    LI(x{check_reg}, 0x{fields:08x}) # spp = {spp} spie = {spie} sie = {sie}",
                            f"    or x{check_reg}, x{check_reg}, x{reg1}          # value to write to sstatus with SPP/SPIE/SIE bits set/clear",
                            f"    LA(x{reg3}, 1f)             # return address after sret",
                            f"    CSRW(sepc, x{reg3})          # set sepc to return address.",
                            f"    CSRW(sstatus, x{check_reg})       # write sstatus with SPP/SPIE/SIE bits set/clear",
                            test_data.add_testcase(f"{binname}_wval", coverpoint, covergroup),
                            "    sret                   # test sret instruction",
                            f"   addi x{check_reg}, zero, -1              # should not be executed",  # should not be executed
                            "1:                         # sret should return to here",
                            write_sigupd(check_reg, test_data),
                            "    RVTEST_GOTO_MMODE      # We might be coming from U-mode, so to get back to S-mode, macros may have to go through M",
                            "    RVTEST_GOTO_LOWER_MODE Smode      # make sure we return to supervisor mode",
                            # Test sstatus was updated properly
                            gen_csr_read_sigupd(check_reg, "sstatus", test_data),
                        ]
                    )

    lines.append(f"\n    CSRW(sstatus, x{save_reg})    # restore CSR")
    test_data.int_regs.return_registers([save_reg, check_reg, reg1, reg2, reg3])
    return lines


def _generate_scsr_tests(test_data: TestData) -> list[str]:
    """Generate CSR tests"""
    covergroup = "S_scsr_cg"

    # Standard S-mode CSRs
    csrs = ["sstatus", "scause", "sie", "stvec", "scounteren", "senvcfg", "sscratch", "sepc", "stval", "sip"]

    ######################################
    coverpoint = "cp_scsr_access"
    ######################################
    lines = [
        comment_banner(
            coverpoint,
            "Read, write all 1s, write all 0s, set all 1s, set all 0s, restore all S-mode CSRs",
        ),
    ]

    for csr in csrs:
        lines.extend(csr_access_test(test_data, csr, covergroup, coverpoint))

    ######################################
    coverpoint = "cp_ucsr_from_s"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "Read, write all 1s, write all 0s, set all 1s, set all 0s, restore all U-mode CSRs from S-mode",
        ),
    )

    lines.extend(["#ifdef F_SUPPORTED"])
    for csr in ["fflags", "frm", "fcsr"]:
        lines.extend(csr_access_test(test_data, csr, covergroup, coverpoint))
    lines.extend(["#endif"])

    lines.extend(["#ifdef V_SUPPORTED"])
    for csr in ["vstart", "vxsat", "vxrm", "vcsr", "vl", "vtype", "vlenb"]:
        lines.extend(csr_access_test(test_data, csr, covergroup, coverpoint))
    lines.extend(["#endif"])

    ######################################
    coverpoint = "cp_scsrwalk"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "Set and clear each bit individually in all writable S-mode CSRs",
        ),
    )

    for csr in csrs:
        lines.extend(csr_walk_test(test_data, csr, covergroup, coverpoint))

    ######################################
    coverpoint = "cp_csr_satp"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "Set and clear each bit individually in satp, excluding satp.mode",
        ),
    )

    walk_reg, mask_reg, check_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    lines.extend(
        [
            "\tcsrw satp, zero      # set satp to 0 to start with",
            f"\tLI(x{mask_reg}, -1)     # x{mask_reg} = all 1s for walking bit tests",
            f"\tsrli x{mask_reg}, x{mask_reg}, 4    # change 4 msbs to 0s to exclude satp.mode from RV64 walk tests",
            f"\tLI(x{walk_reg}, 7)   # 111",
            f"\tslli x{walk_reg}, x{walk_reg}, 28   # bits 30:28 = 111",
            f"\tor x{mask_reg}, x{mask_reg}, x{walk_reg}    # x{mask_reg} = all 1s except satp.MODE (bits 63:60 for RV64 or 31 for RV32)",
            f"\tLI(x{walk_reg}, 1) # initialize walking 1",
        ]
    )
    for i in range(60):
        lines.extend(
            [
                f"\tcsrs satp, x{walk_reg}    # set bit {i} in satp",
                test_data.add_testcase(f"bit_{i}_set", coverpoint, covergroup),
                gen_csr_read_sigupd(check_reg, "satp", test_data),
                f"\tcsrc satp, x{walk_reg}    # clear bit {i} in satp",
                test_data.add_testcase(f"bit_{i}_clr", coverpoint, covergroup),
                gen_csr_read_sigupd(check_reg, "satp", test_data),
                f"\tslli x{walk_reg}, x{walk_reg}, 1   # shift to next bit",
                f"\tand x{walk_reg}, x{walk_reg}, x{mask_reg}    # mask out mode bits",
            ]
        )

    test_data.int_regs.return_registers([walk_reg, mask_reg, check_reg])

    ######################################
    coverpoint = "cp_csr_insufficient_priv"
    ######################################

    lines.append(
        comment_banner(
            coverpoint,
            "Attempt to read debug and machine mode registers.  Should throw illegal instruction",
        ),
    )
    for csr in (
        list(range(0x300, 0x400)) + list(range(0x700, 0x800)) + list(range(0xB00, 0xC00)) + list(range(0xF00, 0x1000))
    ):
        lines.extend(
            [
                test_data.add_testcase(f"{csr}", coverpoint, covergroup),
                f"\tCSRR(t0, 0x{csr:03x})    # attempt to read higher-privilege CSR {csr:03x}; should get illegal instruction",
            ]
        )

    ######################################
    coverpoint = "cp_csr_ro"
    ######################################

    lines.append(
        comment_banner(
            coverpoint,
            "Attempt to write read-only CSRs.  Should throw illegal instruction",
        ),
    )
    r1 = test_data.int_regs.get_register(exclude_regs=[0])

    lines.append(f"\tLI(x{r1}, -1)          # x{r1} = all 1s\n")
    for csr in range(0xC00, 0xF00):
        lines.extend(
            [
                test_data.add_testcase(f"{csr}", coverpoint, covergroup),
                f"\tCSRW(0x{csr:03x}, x{r1})    # attempt to write read-only CSR {csr:03x}; should get illegal instruction\n",
            ]
        )
    test_data.int_regs.return_register(r1)

    ######################################
    coverpoint = "cp_scsr_from_m"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "Read, write all 1s, write all 0s, set all 1s, set all 0s, restore all S-mode CSRs from M-mode",
        ),
    )

    lines.append("\tRVTEST_GOTO_MMODE      # enter machine mode for testing S-mode CSRs from M-mode\n")
    for csr in csrs:
        lines.extend(csr_access_test(test_data, csr, covergroup, coverpoint))

    ######################################
    coverpoint = "cp_shadow"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "Check that values written to shadowed registers are consistent between machine and supervisor mode",
        ),
    )
    r1, r2 = test_data.int_regs.get_registers(2, exclude_regs=[0])
    lines.append(f"\tLI(x{r1}, -1)          # x{r1} = all 1s for writing to shadowed registers\n")
    lines.append(_add_shadow(r1, r2, "mstatus", "sstatus", coverpoint, covergroup, test_data))
    lines.append(_add_shadow(r1, r2, "mie", "sie", coverpoint, covergroup, test_data))
    lines.append(_add_shadow(r1, r2, "mip", "sip", coverpoint, covergroup, test_data))
    lines.append(_add_shadow(r1, r2, "sstatus", "mstatus", coverpoint, covergroup, test_data))
    lines.append(_add_shadow(r1, r2, "sie", "mie", coverpoint, covergroup, test_data))
    lines.append(_add_shadow(r1, r2, "sip", "mip", coverpoint, covergroup, test_data))
    test_data.int_regs.return_registers([r1, r2])

    return lines


def _add_shadow(r1: int, r2: int, wreg: str, rreg: str, coverpoint: str, covergroup: str, test_data: TestData) -> str:
    """Helper function to generate shadow CSR test lines for writing wreg and reading rreg."""
    return str.join(
        "\n",
        [
            f"\tcsrw {wreg}, x{r1}       # write all 1s to {wreg}",
            test_data.add_testcase(f"{wreg}_{rreg}_1s", coverpoint, covergroup),
            gen_csr_read_sigupd(r2, rreg, test_data),
            f"\tcsrw {wreg}, x0       # write all 0s to {wreg}",
            test_data.add_testcase(f"{wreg}_{rreg}_0s", coverpoint, covergroup),
            gen_csr_read_sigupd(r2, rreg, test_data),
            "",
        ],
    )


@add_priv_test_generator("S", required_extensions=["Sm", "S", "Zicsr"])
def make_s(test_data: TestData) -> list[str]:
    """Generate tests for S supervisor-mode testsuite."""
    lines: list[str] = []

    lines.extend(["\t# Run some tests in machine mode"])
    lines.extend(_generate_mretm_tests(test_data))
    lines.extend(_generate_sretm_tests(test_data))
    lines.extend(_generate_srets_tests(test_data))
    lines.extend(["\tRVTEST_GOTO_MMODE  # Get back to machine mode to prepare to go to supervisor mode"])
    lines.extend(["\tRVTEST_GOTO_LOWER_MODE Smode  # Run most tests in supervisor mode"])
    lines.extend(_generate_scause_tests(test_data))
    lines.extend(_generate_sstatus_sd_tests(test_data))
    lines.extend(_generate_priv_inst_tests(test_data))
    lines.extend(_generate_scsr_tests(test_data))

    return lines
