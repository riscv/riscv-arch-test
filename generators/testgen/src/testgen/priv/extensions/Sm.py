##################################
# Sm.py
#
# Sm machine mode privileged extension test generator.
# jcarlin@hmc.edu Jan 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Sm privileged extension test generator."""

from testgen.asm.csr import cntr_access_test, csr_access_test, csr_walk_test, gen_csr_read_sigupd, gen_csr_write_sigupd
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.constants import INDENT
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator


def _generate_mcause_tests(test_data: TestData) -> list[str]:
    """Generate tests for mcause CSR."""
    covergroup = "Sm_mcause_cg"
    save_reg, check_reg, temp_reg = test_data.int_regs.get_registers(3, exclude_regs=[0])

    lines = [
        f"CSRR(x{save_reg}, mcause)     # save CSR before testing it",
        comment_banner(
            "cp_mcause_write_exception",
            "with interrupt = 0: test writing each exception cause",
        ),
    ]

    ######################################
    coverpoint = "cp_mcause_write_exception"
    ######################################
    for i in range(24):
        if i in {14, 17}:  # skip reserved causes
            continue
        lines.extend(
            [
                "",
                f"# exception cause {i}",
                f"LI(x{check_reg}, {i})",
                test_data.add_testcase(f"b_{i}", coverpoint, covergroup),
                gen_csr_write_sigupd(check_reg, "mcause", test_data),
            ]
        )

    lines.extend(
        [
            comment_banner(
                "cp_mcause_write_interrupt",
                "with interrupt = 1: test writing each interrupt cause",
            ),
            "",
            f"SET_MSB(x{temp_reg})  # set x{temp_reg} to have msb = 1 for interrupt tests",
        ]
    )

    ######################################
    coverpoint = "cp_mcause_write_interrupt"
    ######################################
    for i in range(14):
        if i in {0, 4, 8}:  # skip reserved causes
            continue
        lines.extend(
            [
                "",
                f"# interrupt cause {i}",
                f"LI(x{check_reg}, {i})",
                f"or x{check_reg}, x{check_reg}, x{temp_reg}          # set interrupt bit",
                test_data.add_testcase(f"b_{i}", coverpoint, covergroup),
                gen_csr_write_sigupd(check_reg, "mcause", test_data),
            ]
        )

    lines.append(f"\nCSRW(mcause, x{save_reg})       # restore CSR")

    test_data.int_regs.return_registers([save_reg, check_reg, temp_reg])
    return lines


def _generate_mstatus_sd_tests(test_data: TestData) -> list[str]:
    """Generate mstatus SD field write tests."""
    ######################################
    covergroup = "Sm_mstatus_cg"
    coverpoint = "cp_mstatus_sd_write"
    ######################################
    save_reg, check_reg, reg1, reg2, reg3 = test_data.int_regs.get_registers(5, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "Write all combinations of mstatus.SD = {0/1}, FS/XS/VS = {00, 01, 10, 11}\n"
            "mstatus.SD is read-only, so nothing should happen",
        ),
        "",
        f"SET_MSB(x{reg1}) # put a 1 in the msb of x{reg1} (XLEN-1)",
        f"CSRR(x{save_reg}, mstatus)        # read and save mstatus",
        f"{INDENT}# set up x{reg3} with mstatus except SD, FS, XS, VS cleared",
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
                    test_lines = [
                        "",
                        f"# fs = {fs:02b} xs = {xs:02b} vs = {vs:02b}",
                        f"LI(x{check_reg}, 0x{fields:08x})",
                    ]
                    if sd == 1:
                        test_lines.append(f"or x{check_reg}, x{check_reg}, x{reg1}      # set SD bit")
                    test_lines.extend(
                        [
                            f"or x{check_reg}, x{check_reg}, x{reg3}   # value to write to mstatus with SD/FS/XS/VS bits set/clear",
                            test_data.add_testcase(binname, coverpoint, covergroup),
                            gen_csr_write_sigupd(check_reg, "mstatus", test_data),
                        ]
                    )
                    lines.extend(test_lines)

    lines.append(f"\nCSRW(mstatus, x{save_reg})    # restore CSR")
    test_data.int_regs.return_registers([save_reg, check_reg, reg1, reg2, reg3])
    return lines


def _generate_priv_inst_tests(test_data: TestData) -> list[str]:
    """Generate ecall and ebreak tests."""
    ######################################
    covergroup = "Sm_mprivinst_cg"
    coverpoint = "cp_mprvinst"
    ######################################

    lines = [
        comment_banner(
            coverpoint,
            "Execute ecall and ebreak\nShould cause an exception",
        ),
        "",
        # ecall test
        test_data.add_testcase("ecall", coverpoint, covergroup),
        "ecall                 # test ecall instruction",
        "nop                   # this is skipped after trap handler returns",
        "",
        # ebreak test
        test_data.add_testcase("ebreak", coverpoint, covergroup),
        "ebreak                # test ebreak instruction",
        "nop                   # this is skipped after trap handler returns",
    ]

    return lines


def _generate_mret_tests(test_data: TestData) -> list[str]:
    """Generate mret tests with mpp, mprv, mpie, mie sweep."""
    ######################################
    covergroup = "Sm_mprivinst_cg"
    coverpoint = "cp_mret"
    ######################################
    save_reg, check_reg, reg1, reg2, reg3 = test_data.int_regs.get_registers(5, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "Execute mret while sweeping cross-product of mpp, mprv, mpie, mie",
        ),
        "",
        f"CSRR(x{save_reg}, mstatus)        # read and save mstatus",
        f"{INDENT}# set up x{reg1} with mstatus except MPP, MPRV, MPIE, MIE cleared",
        f"LI(x{reg2}, 0x21888)          # x{reg2} has all MPP, MPRV, MPIE, MIE bits set (bits [12:11], [17], [7], [3], respectively)",
        f"not x{reg2}, x{reg2}              # x{reg2} has all but MPP, MPRV, MPIE, MIE bits set",
        f"and x{reg1}, x{save_reg}, x{reg2}         # clear MPP, MPRV, MPIE, MIE bits",
    ]

    for mpp in (3,):  # only M-mode; this will expand in other tests
        for mprv in (0, 1):
            for mpie in (0, 1):
                for mie in (0, 1):
                    binname = f"mpp_{mpp:02b}_mprv_{mprv}_mpie_{mpie}_mie_{mie}"
                    fields = (mpp << 11) | (mprv << 17) | (mpie << 7) | (mie << 3)

                    lines.extend(
                        [
                            "",
                            # Test the write value
                            f"# mret with mpp = {mpp:02b} mprv = {mprv} mpie = {mpie} mie = {mie}",
                            f"LI(x{check_reg}, 0x{fields:08x})",
                            f"or x{check_reg}, x{check_reg}, x{reg1}         # value to write to mstatus with MPP/MPRV/MPIE/MIE bits set/clear",
                            f"LA(x{reg3}, 1f)              # return address after mret",
                            f"CSRW(mepc, x{reg3})          # set mepc to return address",
                            f"CSRW(mstatus, x{check_reg})       # write mstatus with MPP/MPRV/MPIE/MIE bits set/clear",
                            test_data.add_testcase(f"{binname}_wval", coverpoint, covergroup),
                            "mret                     # test mret instruction",
                            f"addi x{check_reg}, zero, -1       # should not be executed",
                            "1:                         # mret should return to here",
                            write_sigupd(check_reg, test_data),
                            # Test the read value
                            test_data.add_testcase(f"{binname}_rval", coverpoint, covergroup),
                            gen_csr_read_sigupd(check_reg, "mstatus", test_data),
                        ]
                    )

    lines.append(f"\nCSRW(mstatus, x{save_reg})    # restore CSR")
    test_data.int_regs.return_registers([save_reg, check_reg, reg1, reg2, reg3])
    return lines


def _generate_sret_tests(test_data: TestData) -> list[str]:
    """Generate sret tests with spp, mprv, spie, sie, tsr sweep."""
    ######################################
    covergroup = "Sm_mprivinst_cg"
    coverpoint = "cp_sret"
    ######################################
    save_reg, check_reg, reg1, reg2, reg3 = test_data.int_regs.get_registers(5, exclude_regs=[0])

    lines = [
        comment_banner(
            coverpoint,
            "Execute sret while sweeping cross-product of mprv, spp, spie, sie, tsr\n"
            "If S-mode is not implemented, sret should raise an illegal instruction exception\n"
            "Otherwise, go to S or U mode depending on SPP.  SIE <- SPIE.  SPIE <- 1.  "
            "MPRV <- 0. SPP <- 0 (U-mode).  TSR has no effect.",
        ),
        "",
        f"CSRR(x{save_reg}, mstatus)        # read and save mstatus",
        f"{INDENT}# set up x{reg1} with mstatus except MPRV, SPP, SPIE, SIE, TSR cleared",
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
                                "",
                                f"# sret with mprv = {mprv} spp = {spp} spie = {spie} sie = {sie} tsr = {tsr}",
                                # Test the write value
                                f"LI(x{check_reg}, 0x{fields:08x})",
                                f"or x{check_reg}, x{check_reg}, x{reg1}          # value to write to mstatus with MPRV/SPP/SPIE/SIE/TSR bits set/clear",
                                f"LA(x{reg3}, 1f)             # return address after sret",
                                f"CSRW(sepc, x{reg3})         # set sepc to return address. Note that sepc does not exist if S-mode is not implemented, and this test will break if writing it hangs",
                                f"CSRW(mstatus, x{check_reg})       # write mstatus with MPRV/SPP/SPIE/SIE/TSR bits set/clear",
                                test_data.add_testcase(f"{binname}_wval", coverpoint, covergroup),
                                "sret                    # test sret instruction",
                                f"addi x{check_reg}, zero, -1       # should not be executed",
                                "1:                        # sret should return to here",
                                write_sigupd(check_reg, test_data),
                                "RVTEST_GOTO_MMODE       # make sure we return to machine mode",
                                # Test the read value
                                test_data.add_testcase(f"{binname}_rval", coverpoint, covergroup),
                                gen_csr_read_sigupd(check_reg, "mstatus", test_data),
                            ]
                        )

    lines.append(f"\nCSRW(mstatus, x{save_reg})    # restore CSR")
    test_data.int_regs.return_registers([save_reg, check_reg, reg1, reg2, reg3])
    return lines


def _generate_mcsr_tests(test_data: TestData) -> list[str]:
    """Generate CSR tests"""
    covergroup = "Sm_mcsr_cg"

    # Standard M-mode CSRs
    csrs = [
        "mstatus",
        "medeleg",
        "mideleg",
        "mie",
        "mtvec",
        "mcounteren",
        "mscratch",
        "mepc",
        "mcause",
        "mtval",
        "mip",
        "menvcfg",
        "mcountinhibit",
        "mhpmevent3",
        "mhpmevent4",
        "mhpmevent5",
        "mhpmevent6",
        "mhpmevent7",
        "mhpmevent8",
        "mhpmevent9",
        "mhpmevent10",
        "mhpmevent11",
        "mhpmevent12",
        "mhpmevent13",
        "mhpmevent14",
        "mhpmevent15",
        "mhpmevent16",
        "mhpmevent17",
        "mhpmevent18",
        "mhpmevent19",
        "mhpmevent20",
        "mhpmevent21",
        "mhpmevent22",
        "mhpmevent23",
        "mhpmevent24",
        "mhpmevent25",
        "mhpmevent26",
        "mhpmevent27",
        "mhpmevent28",
        "mhpmevent29",
        "mhpmevent30",
        "mhpmevent31",
    ]
    # RV32-only high CSRs
    csrs32 = ["mstatush", "menvcfgh"]
    # Read-only CSRs
    csrsro = ["mvendorid", "mimpid", "marchid", "mhartid", "mconfigptr"]

    ######################################
    coverpoint = "cp_mcsr_access"
    ######################################
    lines = [
        comment_banner(
            coverpoint,
            "Read, write all 1s, write all 0s, set all 1s, set all 0s, restore all M-mode CSRs",
        ),
    ]

    for csr in csrs:
        lines.extend(csr_access_test(test_data, csr, covergroup, coverpoint))

    lines.append("\n#ifdef MSECCFG_SUPPORTED")
    lines.extend(csr_access_test(test_data, "mseccfg", covergroup, coverpoint))
    lines.append("#endif")

    lines.append("\n// Read-Only CSRs")
    for csr in csrsro:
        lines.extend(csr_access_test(test_data, csr, covergroup, coverpoint))

    lines.extend(
        [
            "",
            "// RV32-only h CSRs",
            "#if __riscv_xlen == 32",
        ]
    )
    for csr in csrs32:
        lines.extend(csr_access_test(test_data, csr, covergroup, coverpoint))

    lines.append("\n#ifdef MSECCFG_SUPPORTED")
    lines.extend(csr_access_test(test_data, "mseccfgh", covergroup, coverpoint))
    lines.extend(
        [
            "#endif",
            "#endif",
        ]
    )

    ######################################
    coverpoint = "cp_mcsrwalk"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "Set and clear each bit individually in all writable M-mode CSRs",
        ),
    )

    for csr in csrs:
        lines.extend(csr_walk_test(test_data, csr, covergroup, coverpoint))

    lines.extend(
        [
            "// RV32-only h CSRs",
            "#if __riscv_xlen == 32",
        ]
    )
    for csr in csrs32:
        lines.extend(csr_walk_test(test_data, csr, covergroup, coverpoint))
    lines.append("#endif")

    ######################################
    coverpoint = "cp_csr_insufficient_priv"
    ######################################

    lines.append(
        comment_banner(
            coverpoint,
            "Attempt to read debug-mode registers.  Should throw illegal instruction",
        ),
    )
    for csr in range(0x7B0, 0x7C0):
        lines.extend(
            [
                "",
                # Test the write value
                test_data.add_testcase(f"{csr}", coverpoint, covergroup),
                f"CSRR(t0, 0x{csr:03x})    # attempt to read debug-mode CSR {csr:03x}; should get illegal instruction",
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

    lines.append("\nLI(t0, -1)          # t0 = all 1s")
    for csr in range(0xC00, 0x1000):
        lines.extend(
            [
                "",
                test_data.add_testcase(f"{csr}", coverpoint, covergroup),
                f"CSRW(0x{csr:03x}, t0)    # attempt to write read-only CSR {csr:03x}; should get illegal instruction",
            ]
        )

    ######################################
    coverpoint = "cp_misa_mxl"
    ######################################

    lines.append(
        comment_banner(
            coverpoint,
            "Set, clear, write misa.MXL.  Should not change",
        ),
    )

    rmsb, rmsb2, rboth, rr = test_data.int_regs.get_registers(4, exclude_regs=[0])

    lines.extend(
        [
            "# Load 1s into msb and msb-1 corresponding to misa.MXL bitfields",
            f"LI(x{rmsb}, -1)           # all 1s",
            f"srli x{rmsb}, x{rmsb}, 1  # all 1s except msb = 0",
            f"not x{rmsb}, x{rmsb}      # 1 in msb (works regardless of XLEN)",
            f"srli x{rmsb2}, x{rmsb}, 1 # 1s in msb-1",
            f"or x{rboth}, x{rmsb}, x{rmsb2} # 1s in both msb and msb-1",
            "",
            test_data.add_testcase("csrc_11", coverpoint, covergroup),
            f"csrc misa, x{rboth}       # attempt to clear both MXL bits",
            f"csrr x{rr}, misa          # read misa to check MXL bits are unchanged",
            f"and x{rr}, x{rr}, x{rboth} # mask off bits below MXL",
            write_sigupd(rr, test_data),
            "",
            test_data.add_testcase("csrs_11", coverpoint, covergroup),
            f"csrs misa, x{rboth}       # attempt to set both MXL bits",
            f"csrr x{rr}, misa          # read misa to check MXL bits are unchanged",
            f"and x{rr}, x{rr}, x{rboth} # mask off bits below MXL",
            write_sigupd(rr, test_data),
            "",
            test_data.add_testcase("csrw_00", coverpoint, covergroup),
            "csrw misa, zero           # attempt to write 00 to MXL bits",
            f"csrr x{rr}, misa          # read misa to check MXL bits are unchanged",
            f"and x{rr}, x{rr}, x{rboth} # mask off bits below MXL",
            write_sigupd(rr, test_data),
            "",
            test_data.add_testcase("csrw_01", coverpoint, covergroup),
            f"csrw misa, x{rmsb2}       # attempt to write 01 to MXL bits",
            f"csrr x{rr}, misa          # read misa to check MXL bits are unchanged",
            f"and x{rr}, x{rr}, x{rboth} # mask off bits below MXL",
            write_sigupd(rr, test_data),
            "",
            test_data.add_testcase("csrw_10", coverpoint, covergroup),
            f"csrw misa, x{rmsb}        # attempt to write 10 to MXL bits",
            f"csrr x{rr}, misa          # read misa to check MXL bits are unchanged",
            f"and x{rr}, x{rr}, x{rboth} # mask off bits below MXL",
            write_sigupd(rr, test_data),
            "",
            test_data.add_testcase("csrw_11", coverpoint, covergroup),
            f"csrw misa, x{rboth}       # attempt to write 11 to MXL bits",
            f"csrr x{rr}, misa          # read misa to check MXL bits are unchanged",
            f"and x{rr}, x{rr}, x{rboth} # mask off bits below MXL",
            write_sigupd(rr, test_data),
        ]
    )

    test_data.int_regs.return_registers([rmsb, rmsb2, rboth, rr])

    return lines


def _generate_mcsr_cntr_tests(test_data: TestData) -> list[str]:
    """Generate CSR counter tests."""
    covergroup = "Sm_mcsr_cg"

    ######################################
    coverpoint = "cp_cntr_access"
    ######################################
    lines = []
    lines.append(
        comment_banner(
            coverpoint,
            "Read, write nonzero, write all 0s, set nonzero, set all 0s, restore all M-mode counters",
        ),
    )

    cntrs = [
        "mcycle",
        "minstret",
        "mhpmcounter3",
        "mhpmcounter4",
        "mhpmcounter5",
        "mhpmcounter6",
        "mhpmcounter7",
        "mhpmcounter8",
        "mhpmcounter9",
        "mhpmcounter10",
        "mhpmcounter11",
        "mhpmcounter12",
        "mhpmcounter13",
        "mhpmcounter14",
        "mhpmcounter15",
        "mhpmcounter16",
        "mhpmcounter17",
        "mhpmcounter18",
        "mhpmcounter19",
        "mhpmcounter20",
        "mhpmcounter21",
        "mhpmcounter22",
        "mhpmcounter23",
        "mhpmcounter24",
        "mhpmcounter25",
        "mhpmcounter26",
        "mhpmcounter27",
        "mhpmcounter28",
        "mhpmcounter29",
        "mhpmcounter30",
        "mhpmcounter31",
    ]
    # RV32-only high counters
    cntrsh = [
        "mcycleh",
        "minstreth",
        "mhpmcounter3h",
        "mhpmcounter4h",
        "mhpmcounter5h",
        "mhpmcounter6h",
        "mhpmcounter7h",
        "mhpmcounter8h",
        "mhpmcounter9h",
        "mhpmcounter10h",
        "mhpmcounter11h",
        "mhpmcounter12h",
        "mhpmcounter13h",
        "mhpmcounter14h",
        "mhpmcounter15h",
        "mhpmcounter16h",
        "mhpmcounter17h",
        "mhpmcounter18h",
        "mhpmcounter19h",
        "mhpmcounter20h",
        "mhpmcounter21h",
        "mhpmcounter22h",
        "mhpmcounter23h",
        "mhpmcounter24h",
        "mhpmcounter25h",
        "mhpmcounter26h",
        "mhpmcounter27h",
        "mhpmcounter28h",
        "mhpmcounter29h",
        "mhpmcounter30h",
        "mhpmcounter31h",
    ]
    for csr in cntrs:
        lines.extend(cntr_access_test(test_data, csr, covergroup, coverpoint))

    lines.extend(
        [
            "",
            "// RV32-only h CSRs",
            "#if __riscv_xlen == 32",
        ]
    )
    for csr in cntrsh:
        lines.extend(cntr_access_test(test_data, csr, covergroup, coverpoint))

    lines.append("#endif")

    r1, r2 = test_data.int_regs.get_registers(2, exclude_regs=[0])

    ######################################
    coverpoint = "cp_inhibit_mcycle"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "Inhibit mcycle",
        ),
    )
    lines.extend(
        [
            f"LI(x{r1}, 0b1)        # inhibit mcycle",
            f"CSRW(mcountinhibit, x{r1})        # inhibit mcycle",
            f"CSRR(x{r1}, mcycle)        # read mcycle",
            "nop\nnop\nnop\nnop\nnop\nnop # wait a bit",
            test_data.add_testcase("", coverpoint, covergroup),
            f"CSRR(x{r2}, mcycle)        # read mcycle again",
            f"sub x{r2}, x{r2}, x{r1}          # difference should be 0",
            write_sigupd(r2, test_data),
        ]
    )

    ######################################
    coverpoint = "cp_inhibit_minstret"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "Inhibit minstret",
        ),
    )
    lines.extend(
        [
            f"LI(x{r1}, 0b100)        # inhibit minstret",
            f"CSRW(mcountinhibit, x{r1})        # inhibit minstret",
            f"CSRR(x{r1}, minstret)        # read minstret",
            "nop\nnop\nnop\nnop\nnop\nnop # wait a bit",
            test_data.add_testcase("", coverpoint, covergroup),
            f"CSRR(x{r2}, minstret)        # read minstret again",
            f"sub x{r2}, x{r2}, x{r1}          # difference should be 0",
            write_sigupd(r2, test_data),
        ]
    )

    ######################################
    coverpoint = "cp_mtime_write"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "Write mtime and read back time",
        ),
    )
    lines.extend(
        [
            f"LI(x{r1}, 42)        # value to write to mtime",
            f"LA(x{r2}, RVMODEL_MTIME_ADDRESS)        # load address of mtime",
            f"SREG x{r1}, 0(x{r2})        # write mtime = 42 using memory-mapped I/O",
            test_data.add_testcase("", coverpoint, covergroup),
            f"CSRR(x{r2}, time)        # read time",
            f"sub x{r2}, x{r2}, x{r1}          # difference should be small",
            f"slti x{r2}, x{r2}, 10          # signature is 1 if difference < 10",
            write_sigupd(r2, test_data),
            "",
            "#if __riscv_xlen == 32",
            f"LI(x{r1}, 67)        # value to write to mtimeh",
            f"LA(x{r2}, RVMODEL_MTIME_ADDRESS)        # load address of mtimeh",
            f"SREG x{r1}, 4(x{r2})        # write mtimeh = 67 using memory-mapped I/O",
            test_data.add_testcase("h", coverpoint, covergroup),
            f"CSRR(x{r2}, timeh)        # read timeh",
            f"sub x{r2}, x{r2}, x{r1}          # difference should be zero",
            write_sigupd(r2, test_data),
            "#endif",
        ]
    )

    test_data.int_regs.return_registers([r1, r2])

    return lines


@add_priv_test_generator("Sm", required_extensions=["Sm", "Zicsr"])
def make_sm(test_data: TestData) -> list[str]:
    """Generate tests for Sm machine-mode testsuite."""
    lines: list[str] = []

    lines.extend(_generate_mcause_tests(test_data))
    lines.extend(_generate_mstatus_sd_tests(test_data))
    lines.extend(_generate_priv_inst_tests(test_data))
    lines.extend(_generate_mret_tests(test_data))
    lines.extend(_generate_sret_tests(test_data))
    lines.extend(_generate_mcsr_tests(test_data))
    lines.extend(_generate_mcsr_cntr_tests(test_data))

    return lines
