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
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.S import S_CSR_SENVCFG, S_CSRS, S_CSRS_NOWALK, S_SSTATUS_MASK
from testgen.priv.registry import add_priv_test_generator


def _gen_misa_dependencies(
    misa: str, mask: str, cpbin: str, comment: str, coverpoint: str, covergroup: str, test_data: TestData
) -> str:
    """Generate tests for misa dependencies."""
    r1, rmask, rfail, rorig = test_data.int_regs.get_registers(4)
    lines = [
        f"# Write {comment}. Error if this reads back the same.",
        f"csrr x{rorig}, misa # save original value of misa",
        f"LI(x{rfail}, {misa}) # Illegal value to write to misa and read back",
        f"LI(x{rmask}, {mask}) # bits to check",
        test_data.add_testcase(cpbin, coverpoint, covergroup),
        f"csrw misa, x{rfail} # attempt to write misa",
        f"csrr x{r1}, misa # read back",
        f"csrw misa, x{rorig} # restore original value of misa",
        f"and x{r1}, x{r1}, x{rmask} # Mask off don't care bits",
        f"xor x{r1}, x{r1}, x{rfail} # Zero result means failing condition observed",
        f"seqz x{r1}, x{r1}  # 1 indicates illegal outcome.  Ref model should always produce 0",
        write_sigupd(r1, test_data),
        "",
    ]
    test_data.int_regs.return_registers([r1, rmask, rfail, rorig])
    return "\n".join(lines)


def _generate_mcause_tests(test_data: TestData) -> list[str]:
    """Generate tests for mcause CSR."""
    covergroup = "Sm_mcause_cg"
    save_reg, check_reg, temp_reg = test_data.int_regs.get_registers(3)

    lines = [
        f"csrr x{save_reg}, mcause     # save CSR before testing it",
        comment_banner(
            "cp_mcause_write_exception",
            "with interrupt = 0: test writing each exception cause",
        ),
    ]

    ######################################
    coverpoint = "cp_mcause_write_exception"
    ######################################

    gated_exceptions = [
        (10, "#ifdef H_SUPPORTED"),  # ecall from VS-mode
        (14, "RESERVED"),
        (16, "#ifdef SMDBLTRP_SUPPORTED"),  # Double trap
        (17, "RESERVED"),
        (18, "#if defined(ZICFILP_SUPPORTED) || defined(ZICFISS_SUPPORTED)"),  # software check
        (19, "#ifdef SM1P13P0_OR_LATER_SUPPORTED"),  # hardware error
        (20, "#ifdef H_SUPPORTED"),  # instruction guest-page fault
        (21, "#ifdef H_SUPPORTED"),  # load guest-page fault
        (22, "#ifdef H_SUPPORTED"),  # virtual instruction
        (23, "#ifdef H_SUPPORTED"),  # store guest-page fault
    ]

    for i in range(24):
        gated = next((g for g in gated_exceptions if g[0] == i), None)
        if gated is not None and gated[1] == "RESERVED":
            lines.append(f"\n# Exception cause {i} is reserved")
        else:
            if gated is not None:
                lines.append(f"{gated[1]}")
            lines.extend(
                [
                    "",
                    f"# Testcase: set mcause to exception cause {i}",
                    f"LI(x{check_reg}, {i})",
                    test_data.add_testcase(f"b_{i}", coverpoint, covergroup),
                    gen_csr_write_sigupd(check_reg, "mcause", test_data),
                ]
            )
            if gated is not None:
                lines.append("#endif")

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

    lines.append(f"\ncsrw mcause, x{save_reg}       # restore CSR")

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
        f"csrr x{save_reg}, mstatus        # read and save mstatus",
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

    lines.append(f"\ncsrw mstatus, x{save_reg}    # restore CSR")
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
        "RVTEST_TSBI_ECALL_TEST  # test ecall to execution environment that just returns",
        "# ecall returns xepc in a0 (x10).  Store a0 in signature as proof ecall took place.",
        write_sigupd(10, test_data),
        "",
        # ebreak test
        test_data.add_testcase("ebreak", coverpoint, covergroup),
        "ebreak                # test ebreak instruction",
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
        f"csrr x{save_reg}, mstatus        # read and save mstatus",
        f"{INDENT}# set up x{reg1} with mstatus except MPP, MPRV, MPIE, MIE cleared",
        f"LI(x{reg2}, 0x21888)          # x{reg2} has all MPP, MPRV, MPIE, MIE bits set (bits [12:11], [17], [7], [3], respectively)",
        f"not x{reg2}, x{reg2}              # x{reg2} has all but MPP, MPRV, MPIE, MIE bits set",
        f"and x{reg1}, x{save_reg}, x{reg2}         # clear MPP, MPRV, MPIE, MIE bits",
    ]

    # MPP selects the mode mret returns to; the S and U cases only exist when those modes do
    mpp_guard = {3: None, 1: "S_SUPPORTED", 0: "U_SUPPORTED"}
    for mpp, guard in mpp_guard.items():
        if guard:
            lines.append("#ifdef guard")
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
                            f"csrw mepc, x{reg3}          # set mepc to return address",
                            f"csrw mstatus, x{check_reg}       # write mstatus with MPP/MPRV/MPIE/MIE bits set/clear",
                            test_data.add_testcase(f"{binname}_wval", coverpoint, covergroup),
                            "mret                     # test mret instruction",
                            f"addi x{check_reg}, zero, -1       # should not be executed",
                            "1:                         # mret should return to here",
                            write_sigupd(check_reg, test_data),
                            "RVTEST_TSBI_GOTO_MMODE       # mret may have returned to S or U mode; get back to M for the readback",
                            # Test the read value
                            test_data.add_testcase(f"{binname}_rval", coverpoint, covergroup),
                            gen_csr_read_sigupd(check_reg, ("mstatus", None), test_data),
                        ]
                    )
        if guard:
            lines.append("#endif // guard")

    lines.append(f"\ncsrw mstatus, x{save_reg}    # restore CSR")
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
        f"csrr x{save_reg}, mstatus        # read and save mstatus",
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
                                f"csrw sepc, x{reg3}         # set sepc to return address. Note that sepc does not exist if S-mode is not implemented, and this test will break if writing it hangs",
                                f"csrw mstatus, x{check_reg}       # write mstatus with MPRV/SPP/SPIE/SIE/TSR bits set/clear",
                                test_data.add_testcase(f"{binname}_wval", coverpoint, covergroup),
                                "sret                    # test sret instruction",
                                f"addi x{check_reg}, zero, -1       # should not be executed",
                                "1:                        # sret should return to here",
                                write_sigupd(check_reg, test_data),
                                "RVTEST_TSBI_GOTO_MMODE       # make sure we return to machine mode",
                                # Test the read value
                                test_data.add_testcase(f"{binname}_rval", coverpoint, covergroup),
                                gen_csr_read_sigupd(check_reg, ("mstatus", None), test_data),
                            ]
                        )

    lines.append(f"\ncsrw mstatus, x{save_reg}    # restore CSR")
    test_data.int_regs.return_registers([save_reg, check_reg, reg1, reg2, reg3])
    return lines


def _generate_sret_s_tests(test_data: TestData) -> list[str]:
    """Generate sret from S-mode with spp, spie, sie, tsr sweep (cp_sret_s)."""
    ######################################
    covergroup = "Sm_mprivinst_cg"
    coverpoint = "cp_sret_s"
    ######################################
    save_reg, check_reg, reg1, reg2, reg3 = test_data.int_regs.get_registers(5)

    lines = [
        "#ifdef S_SUPPORTED",
        comment_banner(
            coverpoint,
            "Execute sret from S-mode while sweeping cross-product of sstatus.spp, spie, sie; mstatus.tsr\n"
            "Go to S or U mode depending on SPP.  SIE <- SPIE.  SPIE <- 1.  "
            "MPRV <- 0. SPP <- 0 (U-mode).  TSR causes illegal instruction.",
        ),
        "",
        "# Setup",
        f"csrr x{save_reg}, sstatus        # read and save sstatus",
        "csrci medeleg, 1 << 2          # turn off delegating illegal instruction exceptions so TSR won't cause a trap loop on sret",
        f"{INDENT}# set up x{reg1} with sstatus except SPP, SPIE, SIE cleared",
        f"LI(x{reg2}, 0x122)          # x{reg2} has all SPP, SPIE, SIE bits set (bits [8], [5], [1] respectively)",
        f"not x{reg2}, x{reg2}              # x{reg2} has all but SPP, SPIE, SIE bits set",
        f"and x{reg1}, x{save_reg}, x{reg2}          # clear SPP, SPIE, SIE bits",
    ]

    for tsr in (1, 0):
        lines.extend(
            [
                # Set mstatus.TSR from M-mode
                "",
                "# Set mstatus.TSR",
                "RVTEST_TSBI_GOTO_MMODE      # enter machine mode for twiddling mstatus.TSR",
                f"LI(x{check_reg}, {1 << 22})  # mstatus.TSR bit",
            ]
        )

        if tsr == 1:
            lines.append(f"csrs mstatus, x{check_reg}          # set TSR bit")
        else:
            lines.append(f"csrc mstatus, x{check_reg}          # clear TSR bit")
        lines.append("RVTEST_TSBI_GOTO_SMODE # return to supervisor mode to execute sret tests")

        for spp in (0, 1):
            for spie in (0, 1):
                for sie in (0, 1):
                    binname = f"spp_{spp}_spie_{spie}_sie_{sie}_tsr_{tsr}"
                    fields = (spp << 8) | (spie << 5) | (sie << 1)

                    lines.extend(
                        [
                            "",
                            f"# Testcase: sret from s-mode with spp = {spp}, spie = {spie}, sie = {sie}, tsr = {tsr}",
                            # Test the write value
                            f"LI(x{check_reg}, 0x{fields:08x}) # spp = {spp} spie = {spie} sie = {sie}",
                            f"or x{check_reg}, x{check_reg}, x{reg1}          # value to write to sstatus with SPP/SPIE/SIE bits set/clear",
                            f"LA(x{reg3}, 1f)             # return address after sret",
                            f"csrw sepc, x{reg3}          # set sepc to return address.",
                            f"csrw sstatus, x{check_reg}       # write sstatus with SPP/SPIE/SIE bits set/clear",
                            test_data.add_testcase(f"{binname}_wval", coverpoint, covergroup),
                            "sret                   # test sret instruction",
                            f"addi x{check_reg}, zero, -1              # should not be executed",  # should not be executed
                            "1:                         # sret should return to here",
                            write_sigupd(check_reg, test_data),
                            "RVTEST_TSBI_GOTO_SMODE      # We might be coming from U-mode",
                            # Test sstatus was updated properly, masked the same way as the S suite's cp_sret_s.
                            # x{reg3} is free again (sepc consumed it); split the load because the mask has bits above 31.
                            "#if __riscv_xlen == 64",
                            f"LI(x{reg3}, {S_SSTATUS_MASK:#x})    # sstatus mask",
                            "#else",
                            f"LI(x{reg3}, {S_SSTATUS_MASK & 0xFFFFFFFF:#x})    # sstatus mask (low 32 bits)",
                            "#endif",
                            gen_csr_read_sigupd(check_reg, ("sstatus", S_SSTATUS_MASK), test_data, reg3),
                        ]
                    )

    lines.extend(
        [
            f"\ncsrw sstatus, x{save_reg}    # restore CSR",
            "RVTEST_TSBI_GOTO_MMODE      # back to M-mode to touch medeleg",
            "csrsi medeleg, 1 << 2          # restore delegating illegal instructions",
        ]
    )
    lines.append("#endif // S_SUPPORTED")
    test_data.int_regs.return_registers([save_reg, check_reg, reg1, reg2, reg3])
    return lines


def _add_shadow(
    r1: int,
    r2: int,
    rmask: int,
    rsave: int,
    wreg: str,
    rreg: str,
    mask: int,
    coverpoint: str,
    covergroup: str,
    test_data: TestData,
) -> str:
    """Generate shadow CSR test lines for writing wreg and reading rreg (direct CSR access, M-mode)."""
    return str.join(
        "\n",
        [
            "",
            f"# Testcase: shadow CSR test for writing {wreg} and reading {rreg} with mask 0x{mask:x}",
            f"LI(x{rmask}, 0x{mask:x}) # mask specifying bits to keep",
            f"csrr x{rsave}, {wreg}       # save original value of {wreg}",
            f"csrw {wreg}, x{r1}       # write many 1s to {wreg}",
            test_data.add_testcase(f"{wreg}_{rreg}_1s", coverpoint, covergroup),
            gen_csr_read_sigupd(r2, (rreg, mask), test_data, rmask),
            f"csrw {wreg}, x0       # write all 0s to {wreg}",
            test_data.add_testcase(f"{wreg}_{rreg}_0s", coverpoint, covergroup),
            gen_csr_read_sigupd(r2, (rreg, mask), test_data, rmask),
            f"csrw {wreg}, x{rsave}       # write back saved value of {wreg}",
        ],
    )


def _generate_mcsr_tests(test_data: TestData, test_chunks: list) -> None:
    """Generate CSR tests"""
    covergroup = "Sm_mcsr_cg"

    # Standard M-mode CSRs
    # Format: (CSR Name, Mask).  Mask specifies a set of bits to check
    mstatus_mask = (
        (1 << 1)  # SIE:  Supervisor Interrupt Enable
        | (1 << 3)  # MIE:  Machine Interrupt Enable
        | (1 << 5)  # SPIE: Supervisor Previous Interrupt Enable
        | (0 << 6)  # UBE not yet supported by Sail; test in Endian
        | (1 << 7)  # MPIE: Machine Previous Interrupt Enable
        | (1 << 8)  # SPP:  Supervisor Previous Privilege
        | (3 << 9)  # VS:   Vector Status
        | (3 << 11)  # MPP:  Machine Previous Privilege
        | (3 << 13)  # FS:   Floating-Point Status
        | (3 << 15)  # XS:   User-Mode Extension Status
        | (1 << 17)  # MPRV: Modify Privilege
        | (1 << 18)  # SUM:  Supervisor User Memory Access
        | (1 << 19)  # MXR:  Make eXecutable Readable
        | (1 << 20)  # TVM:  Trap Virtual Memory
        | (1 << 21)  # TW:   Timeout Wait
        | (1 << 22)  # TSR:  Trap SRET
        | (1 << 23)  # SPELP: Supervisor Previous Expect Landing Pad
        | (0 << 24)  # SDT: not yet supported by Sail; TODO change to 1 when Ssdbltrp implemented
        | (1 << 31)  # SD for RV32 (probably shouldn't be tested for RV64, but seems to work ok)
        | (0 << 32)  # UXL:  User-Mode XLEN not supported by Sail.  Test in xlen suite.
        | (0 << 34)  # SXL:  Supervisor-Mode XLEN  not supported by Sail.  Test in xlen suite.
        | (0 << 36)  # SBE not supported by Sail; test in Endian
        | (0 << 37)  # MBE not supported by Sail; test in Endian
        | (0 << 38)  # GVA not supported by Sail; TODO change to 1 when H is implemented
        | (0 << 39)  # MPV not supported by Sail; TODO change to 1 when H is implemented
        | (1 << 41)  # MPELP: Machine Previous Expect Landing Pad
        | (0 << 42)  # MDT:   not yet supported by Sail; TODO change to 1 when Smdbltrp implemented
        | (1 << 63)  # SD for RV64
    )
    mseccfg_mask = (
        (0 << 0)  # Smepmp MML not supported TODO: change these to 1 when Sail implements & boot code sets it up
        | (0 << 1)  # Smepmp MMWP not supported
        | (0 << 2)  # Smepmp RLB not supported
        | (1 << 8)  # USEED User mode seed access
        | (1 << 9)  # SSEED Supervisor mode seed access
        | (1 << 10)  # MLPE Machine landing pads enabled
        | (3 << 32)  # Pointer masking
    )
    menvcfg_mask = (
        (1 << 0)  # FIOM: Fence of I/O implies memory
        | (1 << 2)  # LPE: Landing Pad enable
        | (1 << 3)  # SSE: Shadow Stack Enable
        | (3 << 4)  # CBIE: Cache Block Invalidate Enable
        | (1 << 6)  # CBCFE: Cache Block Clean and Flush Enable
        | (1 << 7)  # CBZE: Cache Block Zero Enable
        | (3 << 32)  # PMM: Pointer Masking
        | (0 << 59)  # Double Trap not supported by Sail; TODO change to 1 when Smdbltrp implemented
        | (0 << 60)  # Counter Delegation Smcdeleg not supported by Sail; TODO change to 1 when Smcdeleg implemented
        | (1 << 61)  # ADUE: A/D
        | (1 << 62)  # PBMTE: Page-Based Memory Type Enable
        | (1 << 63)  # STCE: Supervisor Timer Compare Enable
    )

    csrm = [
        (
            "medeleg",
            0xDBBFE,
        ),  # mask off custom bits and reserved bits; instr misaligned [0] depends on ZCA_SUPPORTED so don't check it
        ("mideleg", 0xFFFF),  # limit to standard interrupt bits
        ("mie", 0xFFFF),  # limit to standard interrupt bits
        ("mtvec", 0b10),  # mtvec.MODE[1] must be 0. Legal values for BASE are hard to describe with a reference model
        ("mcounteren", None),
        ("mscratch", None),
        ("mepc", None),
        #        ("mcause", None), # WLRL fields can't be handled with masks.  Use cp_mcause_* instead
        ("mtval", None),
        ("mip", 0xFFFF),  # limit to standard interrupt bits
        # TODO: remove mcountinhibit mask when Sail gets parameters for writable bits
        ("mcountinhibit", 0b111),
        ("mhpmevent3", 0),  # mask all bits because they are WARL and can all be ROZ
        ("mhpmevent4", 0),  # mask all bits because they are WARL and can all be ROZ
        ("mhpmevent5", 0),  # mask all bits because they are WARL and can all be ROZ
        ("mhpmevent6", 0),  # mask all bits because they are WARL and can all be ROZ
        ("mhpmevent7", 0),  # mask all bits because they are WARL and can all be ROZ
        ("mhpmevent8", 0),  # mask all bits because they are WARL and can all be ROZ
        ("mhpmevent9", 0),  # mask all bits because they are WARL and can all be ROZ
        ("mhpmevent10", 0),  # mask all bits because they are WARL and can all be ROZ
        ("mhpmevent11", 0),  # mask all bits because they are WARL and can all be ROZ
        ("mhpmevent12", 0),  # mask all bits because they are WARL and can all be ROZ
        ("mhpmevent13", 0),  # mask all bits because they are WARL and can all be ROZ
        ("mhpmevent14", 0),  # mask all bits because they are WARL and can all be ROZ
        ("mhpmevent15", 0),  # mask all bits because they are WARL and can all be ROZ
        ("mhpmevent16", 0),  # mask all bits because they are WARL and can all be ROZ
        ("mhpmevent17", 0),  # mask all bits because they are WARL and can all be ROZ
        ("mhpmevent18", 0),  # mask all bits because they are WARL and can all be ROZ
        ("mhpmevent19", 0),  # mask all bits because they are WARL and can all be ROZ
        ("mhpmevent20", 0),  # mask all bits because they are WARL and can all be ROZ
        ("mhpmevent21", 0),  # mask all bits because they are WARL and can all be ROZ
        ("mhpmevent22", 0),  # mask all bits because they are WARL and can all be ROZ
        ("mhpmevent23", 0),  # mask all bits because they are WARL and can all be ROZ
        ("mhpmevent24", 0),  # mask all bits because they are WARL and can all be ROZ
        ("mhpmevent25", 0),  # mask all bits because they are WARL and can all be ROZ
        ("mhpmevent26", 0),  # mask all bits because they are WARL and can all be ROZ
        ("mhpmevent27", 0),  # mask all bits because they are WARL and can all be ROZ
        ("mhpmevent28", 0),  # mask all bits because they are WARL and can all be ROZ
        ("mhpmevent29", 0),  # mask all bits because they are WARL and can all be ROZ
        ("mhpmevent30", 0),  # mask all bits because they are WARL and can all be ROZ
        ("mhpmevent31", 0),  # mask all bits because they are WARL and can all be ROZ
    ]
    csr_menvcfg = ("menvcfg", menvcfg_mask)
    csr_mseccfg = ("mseccfg", mseccfg_mask)
    # RV32-only high CSRs
    csr_mstatush = ("mstatush", (mstatus_mask >> 32) & 0x7FFFFFFF)  # SD not in bit 31 of mstatush
    csr_menvcfgh = ("menvcfgh", menvcfg_mask >> 32)
    csr_mseccfgh = ("mseccfgh", mseccfg_mask >> 32)
    csr_medelegh = ("medelegh", 0x00000000)  # all bits are reserved or custom
    # Read-only CSRs
    csrmro = [("mvendorid", None), ("mimpid", None), ("marchid", None), ("mhartid", None), ("mconfigptr", None)]

    ######################################
    coverpoint = "cp_mcsr_access"
    coverpoint_masked = "cp_mcsr_access_masked"  # masked-write CSRs (see csraccesses_masked in Sm_coverage.svh)
    ######################################

    tc = test_data.new_test_chunk(test_chunks, "mcsr_access")

    tc.section_header = comment_banner(
        coverpoint,
        "Read, write all 1s, write all 0s, set all 1s, set all 0s, restore all M-mode CSRs",
    )

    tc = test_data.new_test_chunk(test_chunks)
    tc.code.extend(
        csr_access_test(test_data, ("mstatus", mstatus_mask), covergroup, coverpoint_masked, maskedwrites=True)
    )

    for csr in csrm:
        tc = test_data.new_test_chunk(test_chunks)
        tc.code.extend(csr_access_test(test_data, csr, covergroup, coverpoint))

    tc = test_data.new_test_chunk(test_chunks)
    tc.code.append("\n#ifdef SM1P12P0_OR_LATER_SUPPORTED")
    tc.code.extend(csr_access_test(test_data, csr_menvcfg, covergroup, coverpoint_masked, maskedwrites=True))
    tc.code.append("#endif")

    tc.code.append("\n#ifdef MSECCFG_SUPPORTED")
    tc.code.extend(csr_access_test(test_data, csr_mseccfg, covergroup, coverpoint_masked, maskedwrites=True))
    tc.code.append("#endif")

    tc.code.append("\n// Read-Only CSRs")
    for csr in csrmro:
        tc.code.extend(csr_access_test(test_data, csr, covergroup, coverpoint))

    tc.code.extend(
        [
            "",
            "// RV32-only h CSRs",
            "#if __riscv_xlen == 32",
        ]
    )

    tc.code.extend(csr_access_test(test_data, csr_mstatush, covergroup, coverpoint_masked, maskedwrites=True))

    tc.code.append("\n#ifdef SM1P12P0_OR_LATER_SUPPORTED")
    tc.code.extend(csr_access_test(test_data, csr_menvcfgh, covergroup, coverpoint_masked, maskedwrites=True))
    tc.code.append("#endif //  SM1P12P0_OR_LATER_SUPPORTED")
    tc.code.append("\n#ifdef MSECCFG_SUPPORTED")
    tc.code.extend(csr_access_test(test_data, csr_mseccfgh, covergroup, coverpoint_masked, maskedwrites=True))
    tc.code.append("#endif // MSECCFG")
    tc.code.append("\n#ifdef SM1P13P0_OR_LATER_SUPPORTED")
    tc.code.extend(csr_access_test(test_data, csr_medelegh, covergroup, coverpoint))
    tc.code.extend(
        [
            "#endif // SM1P13P0_OR_LATER_SUPPORTED",
            "#endif // xlen = 32",
        ]
    )

    ######################################
    coverpoint = "cp_mcsrwalk"
    coverpoint_masked = "cp_mcsrwalk_masked"  # masked-write CSRs (see cp_mcsrwalk_masked in Sm_coverage.svh)
    ######################################

    tc = test_data.new_test_chunk(test_chunks, "mcsr_walk")

    tc.section_header = comment_banner(
        coverpoint,
        "Set and clear each bit individually in all writable M-mode CSRs",
    )

    tc = test_data.new_test_chunk(test_chunks)
    # MPP: 0b10 is always reserved; 0b01 (S-mode) is only legal when the config has S-mode
    warl_fields = [("mpp", 11, 2, 0b10), ("mpp", 11, 2, 0b01, "S_SUPPORTED")]
    tc.code.extend(
        csr_walk_test(
            test_data,
            ("mstatus", mstatus_mask),
            covergroup,
            coverpoint_masked,
            warl_fields=warl_fields,
            maskedwrites=True,
        )
    )

    for csr in csrm:
        tc = test_data.new_test_chunk(test_chunks)
        tc.code.extend(csr_walk_test(test_data, csr, covergroup, coverpoint))

    tc.code.append("\n#ifdef SM1P12P0_OR_LATER_SUPPORTED")
    warl_fields = [("cbie", 4, 2, 0b10), ("pmm", 32, 2, 0b01)]
    tc.code.extend(
        csr_walk_test(test_data, csr_menvcfg, covergroup, coverpoint_masked, warl_fields=warl_fields, maskedwrites=True)
    )
    tc.code.append("#endif")

    tc.code.append("\n#ifdef MSECCFG_SUPPORTED")
    warl_fields = [("pmm", 32, 2, 0b01)]
    tc.code.extend(
        csr_walk_test(test_data, csr_mseccfg, covergroup, coverpoint_masked, warl_fields=warl_fields, maskedwrites=True)
    )
    tc.code.append("#endif")

    tc = test_data.new_test_chunk(test_chunks)
    tc.code.extend(
        [
            "// RV32-only h CSRs",
            "#if __riscv_xlen == 32",
        ]
    )

    tc.code.extend(csr_walk_test(test_data, csr_mstatush, covergroup, coverpoint_masked, maskedwrites=True))
    tc.code.append("\n#ifdef SM1P12P0_OR_LATER_SUPPORTED")
    tc.code.extend(csr_walk_test(test_data, csr_menvcfgh, covergroup, coverpoint_masked, maskedwrites=True))
    tc.code.append("#endif // SM1P12P0_OR_LATER_SUPPORTED")
    tc.code.append("\n#ifdef MSECCFG_SUPPORTED")
    tc.code.extend(csr_walk_test(test_data, csr_mseccfgh, covergroup, coverpoint_masked, maskedwrites=True))
    tc.code.append("#endif // MSECCFG")
    tc.code.append("\n#ifdef SM1P13P0_OR_LATER_SUPPORTED")
    tc.code.extend(csr_walk_test(test_data, csr_medelegh, covergroup, coverpoint))
    tc.code.append("#endif // MEDELEGH")
    tc.code.append("#endif // __riscv_xlen == 32")

    ######################################
    coverpoint = "cp_csr_insufficient_priv"
    ######################################

    tc = test_data.new_test_chunk(test_chunks, "csr_insufficient_priv")

    tc.section_header = comment_banner(
        coverpoint,
        "Attempt to read debug-mode registers.  Should throw illegal instruction",
    )
    temp_reg = test_data.int_regs.get_register()
    for csr in range(0x7B0, 0x7C0):
        tc.code.extend(
            [
                "",
                # Test the write value
                test_data.add_testcase(f"{csr}", coverpoint, covergroup),
                f"csrr x{temp_reg}, 0x{csr:03x}    # attempt to read debug-mode CSR {csr:03x}; should get illegal instruction",
            ]
        )
    test_data.int_regs.return_register(temp_reg)

    ######################################
    coverpoint = "cp_csr_ro"
    ######################################

    tc = test_data.new_test_chunk(test_chunks, "csr_ro")

    tc.section_header = comment_banner(
        coverpoint,
        "Attempt to write read-only CSRs.  Should throw illegal instruction",
    )

    for csr in range(0xC00, 0x1000):
        tc = test_data.new_test_chunk(test_chunks, "csr_ro")
        temp_reg = test_data.int_regs.get_register()
        tc.code.extend(
            [
                "",
                f"\nLI(x{temp_reg}, -1)          # x{temp_reg} = all 1s",
                test_data.add_testcase(f"{csr}", coverpoint, covergroup),
                f"csrw 0x{csr:03x}, x{temp_reg}    # attempt to write read-only CSR {csr:03x}; should get illegal instruction",
            ]
        )
        test_data.int_regs.return_register(temp_reg)

    ######################################
    coverpoint = "cp_scsr_from_m"
    ######################################
    tc = test_data.new_test_chunk(test_chunks, "scsr_from_m")
    tc.section_header = comment_banner(
        coverpoint,
        "Read, write all 1s, write all 0s, set all 1s, set all 0s, restore all S-mode CSRs from M-mode",
    )

    tc.code.append("#ifdef S_SUPPORTED")
    for csr in S_CSRS + S_CSRS_NOWALK:
        tc.code.extend(csr_access_test(test_data, csr, covergroup, coverpoint))
    tc.code.extend(["", "#ifdef S1P12P0_OR_LATER_SUPPORTED"])
    tc.code.extend(csr_access_test(test_data, S_CSR_SENVCFG, covergroup, coverpoint))
    tc.code.extend(["", "#endif // S1P12P0_OR_LATER_SUPPORTED"])
    tc.code.append("#endif // S_SUPPORTED")

    ######################################
    coverpoint = "cp_shadow"
    ######################################
    tc = test_data.new_test_chunk(test_chunks, "shadow")
    tc.section_header = comment_banner(
        coverpoint,
        "Check that values written to shadowed registers are consistent between machine and supervisor mode",
    )
    # Moved here from the S suite: the cp_shadow coverpoint samples a csrw of the M-mode CSR
    # immediately followed by a csrr of its S-mode shadow (and vice versa) in M-mode.
    r1, r2, rmask, rsave = test_data.int_regs.get_registers(4)
    tc.code.extend(
        [
            "#ifdef S_SUPPORTED",
            f"LI(x{r1}, 0x007FFFBF) # skip UBE, UXL bits which would cause weird behavior",
            _add_shadow(r1, r2, rmask, rsave, "mstatus", "sstatus", 0xCFFFFFFCF, coverpoint, covergroup, test_data),
            _add_shadow(r1, r2, rmask, rsave, "sstatus", "mstatus", 0xCFFFFFFCF, coverpoint, covergroup, test_data),
            f"LI(x{r1}, 0xFFFF) # all interrupts",
            _add_shadow(r1, r2, rmask, rsave, "mie", "sie", 0x3666, coverpoint, covergroup, test_data),
            _add_shadow(r1, r2, rmask, rsave, "mip", "sip", 0x3666, coverpoint, covergroup, test_data),
            _add_shadow(r1, r2, rmask, rsave, "sie", "mie", 0x3666, coverpoint, covergroup, test_data),
            _add_shadow(r1, r2, rmask, rsave, "sip", "mip", 0x3666, coverpoint, covergroup, test_data),
            "#endif // S_SUPPORTED",
        ]
    )
    test_data.int_regs.return_registers([r1, r2, rmask, rsave])

    ######################################
    coverpoint = "cp_misa_mxl"
    ######################################

    tc = test_data.new_test_chunk(test_chunks, "misa")

    tc.section_header = comment_banner(
        coverpoint,
        "Set, clear, write misa.MXL.  Should not change",
    )

    rmisasave, rmsb, rmsb2, rboth, rr = test_data.int_regs.get_registers(5)

    tc.code.extend(
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

    tc = test_data.new_test_chunk(test_chunks, "misa")

    tc.section_header = comment_banner(
        coverpoint,
        "Attempt to write incompatible values to misa and check illegal combinations do not occur",
    )

    tc.code.extend(
        [
            _gen_misa_dependencies(
                "0b00000000000000000100010000",
                "0b00000000000000000100010000",
                "i1e1",
                "I = 1, E = 1",
                coverpoint,
                covergroup,
                test_data,
            ),
            _gen_misa_dependencies(
                "0b00000000000000000000000000",
                "0b00000000000000000000000000",
                "i0e0",
                "I = 0, E = 0",
                coverpoint,
                covergroup,
                test_data,
            ),
            _gen_misa_dependencies(
                "0b00000000000000000000001000",
                "0b00000000000000000000101000",
                "f0d1",
                "F=0, D = 1",
                coverpoint,
                covergroup,
                test_data,
            ),
            _gen_misa_dependencies(
                "0b00000000010000000000100000",
                "0b00000000010000000000101000",
                "f1d0q1",
                "F=1, D = 0, Q = 1",
                coverpoint,
                covergroup,
                test_data,
            ),
            _gen_misa_dependencies(
                "0b00000001000000000000000000",
                "0b00000101000000000000000000",
                "s1u0",
                "S = 1, U = 0",
                coverpoint,
                covergroup,
                test_data,
            ),
            _gen_misa_dependencies(
                "0b00000000000000000010000000",
                "0b00000001000000000010000000",
                "h1s0",
                "H = 1, S = 0",
                coverpoint,
                covergroup,
                test_data,
            ),
            _gen_misa_dependencies(
                "0b00000001000000000010000000",
                "0b00000101000000000010000000",
                "h1s1u0",
                "H = 1, S = 1, U = 0",
                coverpoint,
                covergroup,
                test_data,
            ),
        ]
    )

    ######################################
    coverpoint = "cp_misa_clear_c"
    ######################################

    tc = test_data.new_test_chunk(test_chunks, "misa")

    tc.section_header = comment_banner(
        coverpoint,
        "Try to clear misa.C.  Should not change if PC is at 2-byte aligned address",
    )

    r1, r2, rc = test_data.int_regs.get_registers(3)

    tc.code.extend(
        [
            f"csrr x{rmisasave}, misa   # save misa",
            f"LI(x{rc}, 0b100)      # bitmask for C extension bit in misa",
            "",
            f"csrs misa, x{rc}     # set misa.C if possible",
            f"csrr x{r1}, misa          # read misa to check if misa.C was set",
            f"and x{r1}, x{r1}, x{rc} # mask off all but C bit",
            ".p2align 2 # 4-byte alignment",
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
            ".p2align 2 # 4-byte alignment",
            ".half 0x0001            # c.nop, can't write that directly because Zca not enabled for Sm",
            test_data.add_testcase("pc_1_1", coverpoint, covergroup),
            f"csrc misa, x{rc}      # attempt to clear misa.C with misa.C = 1 and PC 2-byte aligned",
            f"csrr x{r2}, misa          # read misa to check misa.C didn't change",
            ".p2align 2",
            f"and x{r2}, x{r2}, x{rc} # mask off all but C bit",
            f"xor x{r2}, x{r2}, x{r1} # check if misa.C differed before and after clear attempt; should be 0 because writing misa.C is not allowed to differ when PC is 2-byte aligned",
            write_sigupd(r2, test_data),
            "#endif",
            f"csrw misa, x{rmisasave}    # restore misa",
        ]
    )

    test_data.int_regs.return_registers([r1, r2, rc, rmisasave])

    ######################################
    coverpoint = "cp_misa_bv"
    ######################################

    tc = test_data.new_test_chunk(test_chunks, "misa")

    tc.section_header = comment_banner(
        coverpoint,
        "Sm1p13: misa.B (bit 1) and misa.V (bit 21) correctness.\n"
        "Read, set, and clear each bit; read back and write to signature.",
    )

    rmisasave3, rb, rv, rr3 = test_data.int_regs.get_registers(4)

    tc.code.append("#ifdef SM1P13P0_OR_LATER_SUPPORTED")

    tc.code.extend(
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

    tc.code.append(
        comment_banner(
            coverpoint,
            "Sm1p13: write all 1s / all 0s to memory-mapped msip register.\n"
            "Read back msip, wait, then read mip.MSIP; must reflect the written value.",
        ),
    )

    r_msip, r_msipaddr = test_data.int_regs.get_registers(2)

    tc.code.extend(
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
            f"RVTEST_IDLE_FOR_INTERRUPT(x{r_msip})",
            test_data.add_testcase("msip_set", coverpoint, covergroup),
            f"csrr x{r_msip}, mip                     # read mip",
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
            f"RVTEST_IDLE_FOR_INTERRUPT(x{r_msip})",
            test_data.add_testcase("msip_clear", coverpoint, covergroup),
            f"csrr x{r_msip}, mip                     # read mip",
            f"srli x{r_msip}, x{r_msip}, 3            # shift mip.MSIP (bit 3) to bit 0",
            f"andi x{r_msip}, x{r_msip}, 1            # isolate mip.MSIP",
            write_sigupd(r_msip, test_data),
            "#endif // RVMODEL_MSIP_ADDRESS",
        ]
    )

    test_data.int_regs.return_registers([r_msip, r_msipaddr])
    tc.code.append("#endif // SM1P13P0_OR_LATER_SUPPORTED")

    test_chunks.append(test_data.end_test_chunk())


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
        ("mcycle", None),
        ("minstret", None),
        ("mhpmcounter3", None),
        ("mhpmcounter4", None),
        ("mhpmcounter5", None),
        ("mhpmcounter6", None),
        ("mhpmcounter7", None),
        ("mhpmcounter8", None),
        ("mhpmcounter9", None),
        ("mhpmcounter10", None),
        ("mhpmcounter11", None),
        ("mhpmcounter12", None),
        ("mhpmcounter13", None),
        ("mhpmcounter14", None),
        ("mhpmcounter15", None),
        ("mhpmcounter16", None),
        ("mhpmcounter17", None),
        ("mhpmcounter18", None),
        ("mhpmcounter19", None),
        ("mhpmcounter20", None),
        ("mhpmcounter21", None),
        ("mhpmcounter22", None),
        ("mhpmcounter23", None),
        ("mhpmcounter24", None),
        ("mhpmcounter25", None),
        ("mhpmcounter26", None),
        ("mhpmcounter27", None),
        ("mhpmcounter28", None),
        ("mhpmcounter29", None),
        ("mhpmcounter30", None),
        ("mhpmcounter31", None),
    ]
    # RV32-only high counters
    cntrsh = [
        ("mcycleh", None),
        ("minstreth", None),
        ("mhpmcounter3h", None),
        ("mhpmcounter4h", None),
        ("mhpmcounter5h", None),
        ("mhpmcounter6h", None),
        ("mhpmcounter7h", None),
        ("mhpmcounter8h", None),
        ("mhpmcounter9h", None),
        ("mhpmcounter10h", None),
        ("mhpmcounter11h", None),
        ("mhpmcounter12h", None),
        ("mhpmcounter13h", None),
        ("mhpmcounter14h", None),
        ("mhpmcounter15h", None),
        ("mhpmcounter16h", None),
        ("mhpmcounter17h", None),
        ("mhpmcounter18h", None),
        ("mhpmcounter19h", None),
        ("mhpmcounter20h", None),
        ("mhpmcounter21h", None),
        ("mhpmcounter22h", None),
        ("mhpmcounter23h", None),
        ("mhpmcounter24h", None),
        ("mhpmcounter25h", None),
        ("mhpmcounter26h", None),
        ("mhpmcounter27h", None),
        ("mhpmcounter28h", None),
        ("mhpmcounter29h", None),
        ("mhpmcounter30h", None),
        ("mhpmcounter31h", None),
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
            f"csrw mcountinhibit, x{r1}        # inhibit mcycle",
            f"csrr x{r1}, mcycle        # read mcycle",
            "nop\nnop\nnop\nnop\nnop\nnop # wait a bit",
            test_data.add_testcase("", coverpoint, covergroup),
            f"csrr x{r2}, mcycle        # read mcycle again",
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
            f"csrw mcountinhibit, x{r1}        # inhibit minstret",
            f"csrr x{r1}, minstret        # read minstret",
            "nop\nnop\nnop\nnop\nnop\nnop # wait a bit",
            test_data.add_testcase("", coverpoint, covergroup),
            f"csrr x{r2}, minstret        # read minstret again",
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
            f"csrr x{r2}, time        # read time",
            f"sub x{r2}, x{r2}, x{r1}          # difference should be small",
            f"slti x{r2}, x{r2}, 10          # signature is 1 if difference < 10",
            write_sigupd(r2, test_data),
            "",
            "#if __riscv_xlen == 32",
            f"LI(x{r1}, 67)        # value to write to mtimeh",
            f"LA(x{r2}, RVMODEL_MTIME_ADDRESS)        # load address of mtimeh",
            f"SREG x{r1}, 4(x{r2})        # write mtimeh = 67 using memory-mapped I/O",
            test_data.add_testcase("h", coverpoint, covergroup),
            f"csrr x{r2}, timeh        # read timeh",
            f"sub x{r2}, x{r2}, x{r1}          # difference should be zero",
            write_sigupd(r2, test_data),
            "#endif",
            "#endif",
        ]
    )

    test_data.int_regs.return_registers([r1, r2])

    # Counter Wraparound Verification
    r_val, r_val2, r_temp, r_counter = test_data.int_regs.get_registers(4)

    # Re-enable all counters before trying to wrap them!
    lines.append("csrw mcountinhibit, x0    # Clear inhibit register")

    ######################################
    coverpoint = "cp_mcycle_wraparound"
    ######################################
    lines.append(comment_banner(coverpoint, "Write max value to mcycle and verify it wraps around cleanly"))

    lines.extend(
        [
            f"LI(x{r_temp}, -1)                    # Load all-ones",
            "#if __riscv_xlen == 32",
            f"csrw mcycleh, x{r_temp}             # Set upper 32 bits of mcycle to maximum (RV32 only)",
            "#endif",
            test_data.add_testcase("mcycle_wrap", coverpoint, covergroup),
            f"csrw mcycle, x{r_temp}             # Set mcycle to its maximum value",
            f"LI(x{r_counter}, 100)                # Wait loop for counter ticks",
            "1:",
            "nop",
            f"addi x{r_counter}, x{r_counter}, -1",
            f"bnez x{r_counter}, 1b",
            f"csrr x{r_val}, mcycle               # Read mcycle after the bounded wait",
            f"sltiu x{r_val}, x{r_val}, 1000       # Pass if mcycle wrapped to a small value",
            "#if __riscv_xlen == 32",
            f"csrr x{r_val2}, mcycleh             # Read upper 32 bits after the bounded wait",
            f"sltiu x{r_val2}, x{r_val2}, 1        # Pass if upper 32 bits wrapped to zero",
            f"and x{r_val}, x{r_val}, x{r_val2}    # Pass only if both wraparound conditions are met",
            "#endif",
            write_sigupd(r_val, test_data),
            "",
        ]
    )

    ######################################
    coverpoint = "cp_minstret_wraparound"
    ######################################
    lines.append(comment_banner(coverpoint, "Write max value to minstret and verify it wraps around cleanly"))

    lines.extend(
        [
            f"LI(x{r_temp}, -1)                    # Load all-ones",
            "#if __riscv_xlen == 32",
            f"csrw minstreth, x{r_temp}           # Set upper 32 bits of minstret to maximum (RV32 only)",
            "#endif",
            test_data.add_testcase("minstret_wrap", coverpoint, covergroup),
            f"csrw minstret, x{r_temp}            # Set minstret to its maximum value",
            "nop",
            f"csrr x{r_val}, minstret             # Read minstret after wraparound",
            "#if __riscv_xlen == 32",
            f"csrr x{r_val2}, minstreth           # Read upper 32 bits after wraparound",
            "#endif",
            write_sigupd(r_val, test_data),
            "#if __riscv_xlen == 32",
            write_sigupd(r_val2, test_data),
            "#endif",
            "",
        ]
    )

    ######################################
    coverpoint = "cp_mtime_wraparound"
    ######################################
    lines.append(comment_banner(coverpoint, "Write all-ones to memory-mapped mtime and verify it wraps around cleanly"))

    lines.extend(
        [
            "#ifdef RVMODEL_MTIME_ADDRESS",
            f"LA(x{r_temp}, RVMODEL_MTIME_ADDRESS) # base address of mtime",
            f"LI(x{r_val}, -1)                     # all-ones",
            "#if __riscv_xlen == 32",
            f"SREG x{r_val}, 4(x{r_temp})          # write all-ones to the upper half (RV32 only)",
            "#endif",
            test_data.add_testcase("mtime_wrap", coverpoint, covergroup),
            f"SREG x{r_val}, 0(x{r_temp})          # write all-ones to the base word; arms the counter",
            f"LI(x{r_counter}, RVMODEL_MAX_CYCLES_PER_TIMER_TICK * 2) # Wait loop for two timer ticks",
            "1:",
            "nop",
            f"addi x{r_counter}, x{r_counter}, -1",
            f"bnez x{r_counter}, 1b",
            f"LREG x{r_val2}, 0(x{r_temp})         # read raw lower half after the bounded wait",
            f"LI(x{r_counter}, 100000)            # threshold; too big for an sltiu immediate (12-bit signed)",
            f"sltu x{r_val}, x{r_val2}, x{r_counter}  # pass if mtime wrapped to a small value",
            "#if __riscv_xlen == 32",
            f"LREG x{r_val2}, 4(x{r_temp})         # read raw upper half after the bounded wait",
            f"sltiu x{r_val2}, x{r_val2}, 1         # pass if upper half wrapped to zero",
            f"and x{r_val}, x{r_val}, x{r_val2}     # pass only if both halves wrapped",
            "#endif",
            write_sigupd(r_val, test_data),
            "#endif",
            "",
        ]
    )

    test_data.int_regs.return_registers([r_val, r_val2, r_temp, r_counter])

    return lines


@add_priv_test_generator(
    "Sm",
    required_extensions=["Sm"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_sm(test_data: TestData) -> list[TestChunk]:
    """Generate tests for Sm machine-mode testsuite."""
    test_chunks: list[TestChunk] = []

    tc = test_data.begin_test_chunk("mcause")
    tc.code.extend(_generate_mcause_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())

    tc = test_data.begin_test_chunk("mstatus_sd")
    tc.code.extend(_generate_mstatus_sd_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())

    tc = test_data.begin_test_chunk("inst")
    tc.code.extend(_generate_priv_inst_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())

    tc = test_data.begin_test_chunk("xret")
    tc.code.extend(_generate_mret_tests(test_data))
    tc.code.extend(_generate_sret_tests(test_data))
    tc.code.extend(_generate_sret_s_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())

    tc = test_data.begin_test_chunk("mcsr_cntr")
    tc.code.extend(_generate_mcsr_cntr_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())

    _generate_mcsr_tests(test_data, test_chunks)

    return test_chunks
