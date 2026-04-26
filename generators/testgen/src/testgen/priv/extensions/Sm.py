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


def gen_misa_dependencies(
    misa: str, mask: str, cpbin: str, comment: str, coverpoint: str, covergroup: str, test_data: TestData
) -> str:
    """Generate tests for misa dependencies."""
    r1, rmask, rfail = test_data.int_regs.get_registers(3)
    lines = [
        f"# Write {comment}. Error if this reads back the same.",
        f"LI(x{rfail}, {misa}) # Illegal value to write to misa and read back",
        f"LI(x{rmask}, {mask}) # bits to check",
        test_data.add_testcase(cpbin, coverpoint, covergroup),
        f"csrw misa, x{rfail} # attempt to write misa",
        f"csrr x{r1}, misa # read back",
        f"and x{r1}, x{r1}, x{rmask} # Mask off don't care bits",
        f"xor x{r1}, x{r1}, x{rfail} # Zero result means failing condition observed",
        f"seqz x{r1}, x{r1}  # 1 indicates illegal outcome.  Ref model should always produce 0",
        write_sigupd(r1, test_data),
        "",
    ]
    test_data.int_regs.return_registers([r1, rmask, rfail])
    return "\n".join(lines)


def _generate_mcause_tests(test_data: TestData) -> list[str]:
    """Generate tests for mcause CSR."""
    covergroup = "Sm_mcause_cg"
    save_reg, check_reg, temp_reg = test_data.int_regs.get_registers(3)

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
    save_reg, check_reg, reg1, reg2, reg3 = test_data.int_regs.get_registers(5)

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
    save_reg, check_reg, reg1, reg2, reg3 = test_data.int_regs.get_registers(5)

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
    save_reg, check_reg, reg1, reg2, reg3 = test_data.int_regs.get_registers(5)

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

    rmisasave, rmsb, rmsb2, rboth, rr = test_data.int_regs.get_registers(5)

    lines.extend(
        [
            "# Save misa",
            f"csrr x{rmisasave}, misa      # save misa",
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
            "",
            f"csrw misa, x{rmisasave}    # restore misa",
        ]
    )

    test_data.int_regs.return_registers([rmsb, rmsb2, rboth, rr])

    ######################################
    coverpoint = "cp_misa_dependencies"
    ######################################

    lines.append(
        comment_banner(
            coverpoint,
            "Attempt to write incompatible values to misa and check illegal combinations do not occur",
        ),
    )

    lines.extend(
        [
            gen_misa_dependencies(
                "0b00000000000000000100010000",
                "0b00000000000000000100010000",
                "i1e1",
                "I = 1, E = 1",
                coverpoint,
                covergroup,
                test_data,
            ),
            gen_misa_dependencies(
                "0b00000000000000000000000000",
                "0b00000000000000000000000000",
                "i0e0",
                "I = 0, E = 0",
                coverpoint,
                covergroup,
                test_data,
            ),
            gen_misa_dependencies(
                "0b00000000000000000000001000",
                "0b00000000000000000000101000",
                "f0d1",
                "F=0, D = 1",
                coverpoint,
                covergroup,
                test_data,
            ),
            gen_misa_dependencies(
                "0b00000000010000000000100000",
                "0b00000000010000000000101000",
                "f1d0q1",
                "F=1, D = 0, Q = 1",
                coverpoint,
                covergroup,
                test_data,
            ),
            gen_misa_dependencies(
                "0b00000001000000000000000000",
                "0b00000101000000000000000000",
                "s1u0",
                "S = 1, U = 0",
                coverpoint,
                covergroup,
                test_data,
            ),
            gen_misa_dependencies(
                "0b00000000000000000010000000",
                "0b00000001000000000010000000",
                "h1s0",
                "H = 1, S = 0",
                coverpoint,
                covergroup,
                test_data,
            ),
            gen_misa_dependencies(
                "0b00000001000000000010000000",
                "0b00000101000000000010000000",
                "h1s1u0",
                "H = 1, S = 1, U = 0",
                coverpoint,
                covergroup,
                test_data,
            ),
            f"csrw misa, x{rmisasave}    # restore misa",
        ]
    )

    ######################################
    coverpoint = "cp_misa_clear_c"
    ######################################

    lines.append(
        comment_banner(
            coverpoint,
            "Try to clear misa.C.  Should not change if PC is at 2-byte aligned address",
        ),
    )

    r1, r2, rc = test_data.int_regs.get_registers(3)

    lines.extend(
        [
            f"LI(x{rc}, 0b100)      # bitmask for C extension bit in misa",
            "",
            f"csrs misa, x{rc}     # set misa.C if possible",
            f"csrr x{r1}, misa          # read misa to check if misa.C was set",
            f"and x{r1}, x{r1}, x{rc} # mask off all but C bit",
            ".align 2 # 4-byte alignment",
            test_data.add_testcase("pc_1_0", coverpoint, covergroup),
            f"csrc misa, x{rc}      # attempt to clear misa.C with misa.C = 1 and PC 4-byte aligned",
            f"csrr x{r2}, misa          # read misa to check misa.C changed if writable",
            f"and x{r2}, x{r2}, x{rc} # mask off all but C bit",
            f"xor x{r2}, x{r2}, x{r1} # check if misa.C differed before and after clear attempt; might be 4 if misa.C is mutable because it is allowed to differ when PC is 4-byte aligned",
            write_sigupd(r2, test_data),
            "",
            "#ifdef ZCA_SUPPORTED",
            f"csrs misa, x{rc}     # set misa.C if possible",
            f"csrr x{r1}, misa          # read misa to check if misa.C was set",
            f"and x{r1}, x{r1}, x{rc} # mask off all but C bit",
            ".align 2 # 4-byte alignment",
            ".half 0x0001            # c.nop, can't write that directly because Zca not enabled for Sm",
            test_data.add_testcase("pc_1_1", coverpoint, covergroup),
            f"csrc misa, x{rc}      # attempt to clear misa.C with misa.C = 1 and PC 2-byte aligned",
            f"csrr x{r2}, misa          # read misa to check misa.C didn't change",
            ".align 2",
            f"and x{r2}, x{r2}, x{rc} # mask off all but C bit",
            f"xor x{r2}, x{r2}, x{r1} # check if misa.C differed before and after clear attempt; should be 0 because writing misa.C is not allowed to differ when PC is 2-byte aligned",
            write_sigupd(r2, test_data),
            "#endif",
            f"csrw misa, x{rmisasave}    # restore misa",
        ]
    )

    test_data.int_regs.return_registers([r1, r2, rc, rmisasave])

    lines.extend(
        [
            "",
            "#ifdef SM1P13_SUPPORTED",
        ]
    )

    ######################################
    coverpoint = "cp_misa_bv"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "Sm1p13: misa.B (bit 1) and misa.V (bit 21) correctness.\n"
            "Read, set, and clear each bit; read back and write to signature.",
        ),
    )

    rmisasave3, rb, rv, rr3 = test_data.int_regs.get_registers(4)

    lines.extend(
        [
            f"csrr x{rmisasave3}, misa       # save misa before Sm1p13 B/V tests",
            f"LI(x{rb}, 0x2)                 # bitmask for misa.B (bit 1)",
            f"LI(x{rv}, 0x200000)            # bitmask for misa.V (bit 21)",
            "",
            "# Set misa.B and read back",
            test_data.add_testcase("set_B", coverpoint, covergroup),
            f"csrs misa, x{rb}              # attempt to set misa.B",
            f"csrr x{rr3}, misa             # read back misa",
            f"and x{rr3}, x{rr3}, x{rb}     # isolate misa.B",
            write_sigupd(rr3, test_data),
            "",
            "# Clear misa.B and read back",
            test_data.add_testcase("clr_B", coverpoint, covergroup),
            f"csrc misa, x{rb}              # attempt to clear misa.B",
            f"csrr x{rr3}, misa             # read back misa",
            f"and x{rr3}, x{rr3}, x{rb}     # isolate misa.B",
            write_sigupd(rr3, test_data),
            "",
            "# Set misa.V and read back",
            test_data.add_testcase("set_V", coverpoint, covergroup),
            f"csrs misa, x{rv}              # attempt to set misa.V",
            f"csrr x{rr3}, misa             # read back misa",
            f"and x{rr3}, x{rr3}, x{rv}     # isolate misa.V",
            write_sigupd(rr3, test_data),
            "",
            "# Clear misa.V and read back",
            test_data.add_testcase("clr_V", coverpoint, covergroup),
            f"csrc misa, x{rv}              # attempt to clear misa.V",
            f"csrr x{rr3}, misa             # read back misa",
            f"and x{rr3}, x{rr3}, x{rv}     # isolate misa.V",
            write_sigupd(rr3, test_data),
            "",
            f"csrw misa, x{rmisasave3}      # restore misa after B/V tests",
        ]
    )

    test_data.int_regs.return_registers([rmisasave3, rb, rv, rr3])

    ######################################
    coverpoint = "cp_msip"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "Sm1p13: write all 1s / all 0s to memory-mapped msip register.\n"
            "Read back msip, wait, then read mip.MSIP; must reflect the written value.",
        ),
    )

    r_msip, r_msipaddr = test_data.int_regs.get_registers(2)

    lines.extend(
        [
            "#ifdef RVMODEL_MSIP_ADDRESS",
            f"LI(x{r_msipaddr}, RVMODEL_MSIP_ADDRESS)   # load address of memory-mapped msip register",
            "",
            "# Write 1 to msip (set MSIP) and check mip.MSIP is set",
            f"LI(x{r_msip}, 1)                         # value 1: assert msip",
            test_data.add_testcase("msip_mmio_1", coverpoint, covergroup),
            f"SW x{r_msip}, 0(x{r_msipaddr})           # write msip = 1 via memory-mapped I/O",
            f"LW x{r_msip}, 0(x{r_msipaddr})            # read back memory-mapped msip register",
            f"andi x{r_msip}, x{r_msip}, 1              # isolate bit 0",
            write_sigupd(r_msip, test_data),
            "RVTEST_IDLE_FOR_INTERRUPT",
            test_data.add_testcase("msip_set", coverpoint, covergroup),
            f"CSRR(x{r_msip}, mip)                     # read mip",
            f"srli x{r_msip}, x{r_msip}, 3            # shift mip.MSIP (bit 3) to bit 0",
            f"andi x{r_msip}, x{r_msip}, 1            # isolate mip.MSIP",
            write_sigupd(r_msip, test_data),
            "",
            "# Write 0 to msip (clear MSIP) and check mip.MSIP is clear",
            f"LI(x{r_msip}, 0)                         # value 0: deassert msip",
            test_data.add_testcase("msip_mmio_0", coverpoint, covergroup),
            f"SW x{r_msip}, 0(x{r_msipaddr})           # write msip = 0 via memory-mapped I/O",
            f"LW x{r_msip}, 0(x{r_msipaddr})            # read back memory-mapped msip register",
            f"andi x{r_msip}, x{r_msip}, 1              # isolate bit 0",
            write_sigupd(r_msip, test_data),
            "RVTEST_IDLE_FOR_INTERRUPT",
            test_data.add_testcase("msip_clear", coverpoint, covergroup),
            f"CSRR(x{r_msip}, mip)                     # read mip",
            f"srli x{r_msip}, x{r_msip}, 3            # shift mip.MSIP (bit 3) to bit 0",
            f"andi x{r_msip}, x{r_msip}, 1            # isolate mip.MSIP",
            write_sigupd(r_msip, test_data),
            "#endif // RVMODEL_MSIP_ADDRESS",
        ]
    )

    test_data.int_regs.return_registers([r_msip, r_msipaddr])

    ######################################
    coverpoint = "cp_medelegh"
    ######################################
    lines.append(
        comment_banner(
            coverpoint,
            "Sm1p13 RV32 only: write all 1s to medelegh and read back.\n"
            "The ref model determines which bits are writable; signature must match.",
        ),
    )

    r_medsave, r_medcheck = test_data.int_regs.get_registers(2)

    lines.extend(
        [
            "#if __riscv_xlen == 32",
            f"CSRR(x{r_medsave}, medelegh)   # save medelegh before testing",
            "",
            "# Write all 1s and all 0s to medelegh",
            f"LI(x{r_medcheck}, -1)          # x{r_medcheck} = all 1s",
            test_data.add_testcase("write_ones", coverpoint, covergroup),
            gen_csr_write_sigupd(r_medcheck, "medelegh", test_data),
            test_data.add_testcase("write_zeros", coverpoint, covergroup),
            gen_csr_write_sigupd(0, "medelegh", test_data),
            "",
            f"CSRW(medelegh, x{r_medsave})   # restore medelegh",
            "#endif // __riscv_xlen == 32",
        ]
    )

    test_data.int_regs.return_registers([r_medsave, r_medcheck])

    lines.append("#endif // SM1P13_SUPPORTED")

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

    r1, r2 = test_data.int_regs.get_registers(2)

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
            "Write mtime and read back time if supported",
        ),
    )
    lines.extend(
        [
            "#ifdef RVMODEL_MTIME_ADDRESS",
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
