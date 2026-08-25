##################################
# S.py
#
# S supervisor mode privileged extension test generator.
# David_Harris@hmc.edu 1 March 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""S supervisor privileged extension test generator."""

from testgen.asm.csr import csr_access_test, csr_walk_test, gen_csr_read_sigupd, gen_csr_write_sigupd
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.constants import INDENT
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

# Standard S-mode CSRs, shared with the Sm suite (cp_scsr_from_m)
# Format: (CSR Name, Mask).  Mask specifies a set of bits to check

# Create bit masks.  WPRI fields should be 0 to ignore reads.

# sstatus bit mask
S_SSTATUS_MASK = (
    (1 << 1)  # SIE:  Supervisor Interrupt Enable
    | (1 << 5)  # SPIE: Supervisor Previous Interrupt Enable
    | (0 << 6)  # UBE not yet supported by Sail; test in Endian
    | (1 << 8)  # SPP:  Supervisor Previous Privilege
    | (3 << 9)  # VS:   Vector Status
    | (3 << 13)  # FS:   Floating-Point Status
    | (3 << 15)  # XS:   Custom Extension Status
    | (1 << 18)  # SUM:  Supervisor User Memory Access
    | (1 << 19)  # MXR:  Make eXecutable Readable
    | (1 << 23)  # SPELP: Supervisor Previous Expect Landing Pad
    | (0 << 24)  # SDT: not yet supported by Sail; TODO change to 1 when Ssdbltrp implemented
    | (1 << 31)  # SD for RV32 (probably shouldn't be tested for RV64, but seems to work ok)
    | (0 << 32)  # UXL:  User-Mode XLEN not changeable in Sail yet; should be tested in Xlen suite
    | (1 << 63)  # SD for RV64
)

S_CSRS = [
    ("sstatus", S_SSTATUS_MASK),
    # cp_scause is tested separately. WLRL fields can't be managed with masks.
    # stvec.MODE[1] must be 0. Legal values for BASE are hard to describe with a reference model
    ("stvec", 0b10),
    ("scounteren", None),
    ("sscratch", None),
    ("sip", 0xFFFF),  # only test standard non-reserved portion
    ("sie", 0xFFFF),  # only test standard non-reserved portion
]
# skip walking 1s on this because valid virtual addresses is not described adequately
S_CSRS_NOWALK = [
    ("sepc", None),  # only has to be able to hold all valid virtual addresses
    ("stval", None),  # only has to be able to hold all valid virtual addresses and 0
]
# senvcfg CBIE/PMM reserved values are handled with warl_fields in the walk test below
S_CSR_SENVCFG = ("senvcfg", None)


def _generate_scause_tests(test_data: TestData) -> list[str]:
    """Generate tests for scause CSR."""
    covergroup = "S_scause_cg"
    save_reg, check_reg, temp_reg = test_data.int_regs.get_registers(3)

    ######################################
    coverpoint = "cp_scause_write_exception"
    ######################################
    lines = [
        comment_banner(
            coverpoint,
            "with interrupt = 0: test writing each exception cause",
        ),
        f"csrr x{save_reg}, scause     # save CSR before testing it",
    ]

    for i in range(32):
        gated = i in {10, 11, 14, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31}
        if gated:
            lines.append("#ifdef S1P12P0_OR_LATER_SUPPORTED")
        lines.extend(
            [
                "",
                f"# Testcase: set scause to exception cause {i}",
                f"LI(x{check_reg}, {i})",
                test_data.add_testcase(f"b_{i}", coverpoint, covergroup),
                gen_csr_write_sigupd(check_reg, "scause", test_data),
            ]
        )
        if gated:
            lines.append("#endif")

    ######################################
    coverpoint = "cp_scause_write_interrupt"
    ######################################

    lines.extend(
        [
            comment_banner(
                coverpoint,
                "with interrupt = 1: test writing each interrupt cause",
            ),
            f"SET_MSB(x{temp_reg})  # set x{temp_reg} to have msb = 1 for interrupt tests",
        ]
    )

    for i in range(32):
        gated = i in {0, 2, 4, 6, 8, 10, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31}
        if gated:
            lines.append("#ifdef S1P12P0_OR_LATER_SUPPORTED")
        lines.extend(
            [
                "",
                f"# Testcase: set scause to interrupt cause {i}",
                f"LI(x{check_reg}, {i})",
                f"or x{check_reg}, x{check_reg}, x{temp_reg}          # set interrupt bit",
                test_data.add_testcase(f"b_{i}", coverpoint, covergroup),
                gen_csr_write_sigupd(check_reg, "scause", test_data),
            ]
        )
        if gated:
            lines.append("#endif")

    lines.append(f"\ncsrw scause, x{save_reg}       # restore CSR")

    test_data.int_regs.return_registers([save_reg, check_reg, temp_reg])
    return lines


def _generate_sstatus_sd_tests(test_data: TestData) -> list[str]:
    """Generate sstatus SD field write tests."""
    ######################################
    covergroup = "S_sstatus_cg"
    coverpoint = "cp_sstatus_sd_write"
    ######################################
    save_reg, check_reg, reg1, reg2, reg3 = test_data.int_regs.get_registers(5)

    lines = [
        comment_banner(
            coverpoint,
            "Write all combinations of sstatus.SD = {0/1}, FS/XS/VS = {00, 01, 10, 11}\n"
            "sstatus.SD is read-only, so nothing should happen",
        ),
        "",
        "# Setup",
        f"SET_MSB(x{reg1}) # put a 1 in the msb of x{reg1} (XLEN-1)",
        f"csrr x{save_reg}, sstatus        # read and save sstatus",
        f"{INDENT}# set up x{reg3} with sstatus except SD, FS, XS, VS cleared",
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
                    lines.extend(
                        [
                            "",
                            f"# Testcase: set sstatus to sd = {sd}, fs = {fs:02b}, xs = {xs:02b}, vs = {vs:02b}",
                            f"LI(x{check_reg}, 0x{fields:08x})  # fs = {fs:02b} xs = {xs:02b} vs = {vs:02b}",
                        ]
                    )
                    if sd == 1:
                        lines.append(f"or x{check_reg}, x{check_reg}, x{reg1}      # set SD bit")
                    lines.extend(
                        [
                            f"or x{check_reg}, x{check_reg}, x{reg3}   # value to write to sstatus with SD/FS/XS/VS bits set/clear",
                            test_data.add_testcase(binname, coverpoint, covergroup),
                            gen_csr_write_sigupd(check_reg, "sstatus", test_data),
                        ]
                    )

    lines.append(f"\ncsrw sstatus, x{save_reg}    # restore CSR")

    coverpoint = "cp_sxlen_ge_uxlen"  # For SS1P13 extension.
    lines.extend(
        [
            "",
            "#ifdef S1P13P0_OR_LATER_SUPPORTED",
            "#if __riscv_xlen == 64",
            comment_banner(
                coverpoint,
                "Ss1p13: from S-mode attempt to set sstatus.UXL = 1 and UXL = 2.\n"
                "UXL=2 must be silently rejected when SXLEN=32 (UXLEN <= SXLEN).",
            ),
            f"csrr x{save_reg}, sstatus",
            "",
        ]
    )

    for uxl, label in ((1, "uxlen32"), (2, "uxlen64")):
        lines.extend(
            [
                "",
                f"# Testcase: Ss1p13 attempt to set sstatus.UXL = {uxl} ({label})",
                f"csrr x{check_reg}, sstatus                     # read current sstatus into GPR",
                f"LI(x{reg2}, {~(3 << 32) & 0xFFFFFFFFFFFFFFFF})  # mask to clear UXL bits [33:32]",
                f"and x{check_reg}, x{check_reg}, x{reg2}         # clear UXL bits [33:32]",
                f"LI(x{reg2}, {uxl << 32})                        # UXL={uxl} shifted into position [33:32]",
                f"or x{check_reg}, x{check_reg}, x{reg2}          # OR in desired UXL value",
                test_data.add_testcase(f"uxl_attempt_{uxl}", coverpoint, covergroup),
                gen_csr_write_sigupd(check_reg, "sstatus", test_data),
            ]
        )

    lines.extend(
        [
            "",
            f"csrw sstatus, x{save_reg}        # restore sstatus after Ss1p13 UXL tests",
            "#endif // UDB_MXLEN_64",
            "#endif // S1P13P0_OR_LATER_SUPPORTED",
        ]
    )

    test_data.int_regs.return_registers([save_reg, check_reg, reg1, reg2, reg3])
    return lines


def _generate_priv_inst_tests(test_data: TestData) -> list[str]:
    """Generate ecall and ebreak and mret and sfence.vma tests."""
    ######################################
    covergroup = "S_sprivinst_cg"
    coverpoint = "cp_sprivinst"
    ######################################

    lines = [
        comment_banner(
            coverpoint,
            "Executing ecall and ebreak and mret should cause an exception",
        ),
        "",
        # ecall test
        "# Testcase: ecall instruction",
        test_data.add_testcase("ecall", coverpoint, covergroup),
        "RVTEST_TSBI_ECALL_TEST  # test ecall to execution environment that just returns",
        "# ecall returns xepc in a0 (x10).  Store a0 in signature as proof ecall took place.",
        write_sigupd(10, test_data),
        "",
        # ebreak test
        "# Testcase: ebreak instruction",
        test_data.add_testcase("ebreak", coverpoint, covergroup),
        "ebreak              # test ebreak instruction",
        "",
        # mret test
        "# Testcase: mret instruction",
        test_data.add_testcase("mret", coverpoint, covergroup),
        "mret                # test mret instruction",
        "",
        # sfence.vma test
        "# Testcase: sfence.vma instruction",
        test_data.add_testcase("sfence_vma", coverpoint, covergroup),
        "sfence.vma          # test sfence.vma instruction",
    ]

    return lines


def _generate_srets_tests(test_data: TestData) -> list[str]:
    """Generate sret from S-mode with spp, spie, sie sweep (no TSR: that needs M-mode and lives in Sm)."""
    ######################################
    covergroup = "S_sprivinst_cg"
    coverpoint = "cp_sret_s"
    ######################################
    save_reg, check_reg, reg1, reg2, reg3 = test_data.int_regs.get_registers(5)

    lines = [
        comment_banner(
            coverpoint,
            "Execute sret from S-mode while sweeping cross-product of sstatus.spp, spie, sie\n"
            "Go to S or U mode depending on SPP.  SIE <- SPIE.  SPIE <- 1.  "
            "MPRV <- 0. SPP <- 0 (U-mode).",
        ),
        "",
        "# Setup",
        f"csrr x{save_reg}, sstatus        # read and save sstatus",
        f"{INDENT}# set up x{reg1} with sstatus except SPP, SPIE, SIE cleared",
        f"LI(x{reg2}, 0x122)          # x{reg2} has all SPP, SPIE, SIE bits set (bits [8], [5], [1] respectively)",
        f"not x{reg2}, x{reg2}              # x{reg2} has all but SPP, SPIE, SIE bits set",
        f"and x{reg1}, x{save_reg}, x{reg2}          # clear SPP, SPIE, SIE bits",
    ]

    for spp in (0, 1):
        for spie in (0, 1):
            for sie in (0, 1):
                binname = f"spp_{spp}_spie_{spie}_sie_{sie}"
                fields = (spp << 8) | (spie << 5) | (sie << 1)

                lines.extend(
                    [
                        "",
                        f"# Testcase: sret from s-mode with spp = {spp}, spie = {spie}, sie = {sie}",
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
                        "RVTEST_TSBI_GOTO_SMODE # return to supervisor mode",
                        # Test sstatus was updated properly.  x{reg3} is free again (sepc consumed it), so
                        # reuse it for the mask; split the load because the mask has bits above 31.
                        "#if __riscv_xlen == 64",
                        f"LI(x{reg3}, {S_SSTATUS_MASK:#x})    # sstatus mask",
                        "#else",
                        f"LI(x{reg3}, {S_SSTATUS_MASK & 0xFFFFFFFF:#x})    # sstatus mask (low 32 bits)",
                        "#endif",
                        gen_csr_read_sigupd(check_reg, ("sstatus", S_SSTATUS_MASK), test_data, reg3),
                    ]
                )

    lines.append(f"\ncsrw sstatus, x{save_reg}    # restore CSR")
    test_data.int_regs.return_registers([save_reg, check_reg, reg1, reg2, reg3])
    return lines


def _generate_scsr_tests(test_data: TestData, test_chunks: list[TestChunk]) -> None:
    """Generate CSR tests, one test chunk per CSR so they can be split across files."""
    covergroup = "S_scsr_cg"

    # Floating-point CSRs
    csrf = [("fflags", None), ("frm", None), ("fcsr", None)]
    # Vector CSRs
    csrv = [
        ("vstart", None),
        ("vxsat", None),
        ("vxrm", None),
        ("vcsr", None),
        ("vl", None),
        ("vtype", None),
        ("vlenb", None),
    ]

    ######################################
    coverpoint = "cp_scsr_access"
    ######################################
    tc = test_data.new_test_chunk(test_chunks, "scsr")
    tc.section_header = comment_banner(
        coverpoint,
        "Read, write all 1s, write all 0s, set all 1s, set all 0s, restore all S-mode CSRs",
    )

    for csr in S_CSRS + S_CSRS_NOWALK:
        tc = test_data.new_test_chunk(test_chunks)
        tc.code.extend(csr_access_test(test_data, csr, covergroup, coverpoint))

    tc = test_data.new_test_chunk(test_chunks)
    tc.code.extend(["", "#ifdef S1P12P0_OR_LATER_SUPPORTED"])
    tc.code.extend(csr_access_test(test_data, S_CSR_SENVCFG, covergroup, coverpoint))
    tc.code.extend(["", "#endif"])

    ######################################
    coverpoint = "cp_ucsr_from_s"
    ######################################
    tc = test_data.new_test_chunk(test_chunks)
    tc.section_header = comment_banner(
        coverpoint,
        "Read, write all 1s, write all 0s, set all 1s, set all 0s, restore all U-mode CSRs from S-mode",
    )

    # The #ifdef guard has to stay in one chunk, so all F (and all V) CSRs share a chunk.
    tc = test_data.new_test_chunk(test_chunks)
    tc.code.extend(["", "#ifdef F_SUPPORTED"])
    for csr in csrf:
        tc.code.extend(csr_access_test(test_data, csr, covergroup, coverpoint))
    tc.code.extend(["", "#endif"])

    tc = test_data.new_test_chunk(test_chunks)
    tc.code.extend(["", "#ifdef V_SUPPORTED"])
    for csr in csrv:
        tc.code.extend(csr_access_test(test_data, csr, covergroup, coverpoint))
    tc.code.extend(["", "#endif"])

    ######################################
    coverpoint = "cp_scsrwalk"
    ######################################
    tc = test_data.new_test_chunk(test_chunks)
    tc.section_header = comment_banner(
        coverpoint,
        "Set and clear each bit individually in all writable S-mode CSRs",
    )

    for csr in S_CSRS:
        tc = test_data.new_test_chunk(test_chunks)
        tc.code.extend(csr_walk_test(test_data, csr, covergroup, coverpoint))

    tc = test_data.new_test_chunk(test_chunks)
    tc.code.extend(["", "#ifdef S1P12P0_OR_LATER_SUPPORTED"])
    # senvcfg.CBIE (bits 5:4) and senvcfg.PMM (bits 33:32) are WARL fields with reserved
    # values 0b10 and 0b01 respectively. Walk iterations that write a reserved value may
    # legalize to any legal value, so those iterations check that the field is legal
    # instead of exact-matching the reference model.
    warl_fields = [("cbie", 4, 2, 0b10), ("pmm", 32, 2, 0b01)]
    tc.code.extend(csr_walk_test(test_data, S_CSR_SENVCFG, covergroup, coverpoint, warl_fields=warl_fields))
    tc.code.extend(["", "#endif"])

    # cp_csr_satp waived because behavior of other fields is UNSPECIFIED when satp.MODE = Bare
    # ######################################
    # coverpoint = "cp_csr_satp"
    # ######################################
    # lines.append(
    #     comment_banner(
    #         coverpoint,
    #         "Set and clear each bit individually in satp, excluding satp.mode",
    #     ),
    # )

    # walk_reg, mask_reg, check_reg = test_data.int_regs.get_registers(3)

    # lines.extend(
    #     [
    #         "# CSR Walk Tests for satp",
    #         "csrw satp, zero      # set satp to 0 to start with",
    #         f"LI(x{mask_reg}, -1)     # x{mask_reg} = all 1s for walking bit tests",
    #         f"srli x{mask_reg}, x{mask_reg}, 4    # change 4 msbs to 0s to exclude satp.mode from RV64 walk tests",
    #         f"LI(x{walk_reg}, 7)   # 111",
    #         f"slli x{walk_reg}, x{walk_reg}, 28   # bits 30:28 = 111",
    #         f"or x{mask_reg}, x{mask_reg}, x{walk_reg}    # x{mask_reg} = all 1s except satp.MODE (bits 63:60 for RV64 or 31 for RV32)",
    #         f"LI(x{walk_reg}, 1) # initialize walking 1",
    #     ]
    # )
    # for i in range(60):
    #     lines.extend(
    #         [
    #             "",
    #             f"csrs satp, x{walk_reg}    # set bit {i} in satp",
    #             test_data.add_testcase(f"bit_{i}_set", coverpoint, covergroup),
    #             gen_csr_read_sigupd(check_reg, ("satp", None), test_data),
    #             f"csrc satp, x{walk_reg}    # clear bit {i} in satp",
    #             test_data.add_testcase(f"bit_{i}_clr", coverpoint, covergroup),
    #             gen_csr_read_sigupd(check_reg, ("satp", None), test_data),
    #             f"slli x{walk_reg}, x{walk_reg}, 1   # shift to next bit",
    #             f"and x{walk_reg}, x{walk_reg}, x{mask_reg}    # mask out mode bits",
    #         ]
    #     )

    # test_data.int_regs.return_registers([walk_reg, mask_reg, check_reg])

    ######################################
    coverpoint = "cp_csr_insufficient_priv"
    ######################################

    tc = test_data.new_test_chunk(test_chunks, "scsr_insufficient_priv")
    tc.section_header = comment_banner(
        coverpoint,
        "Attempt to read debug and machine mode registers.  Should throw illegal instruction",
    )

    for csr in (
        list(range(0x300, 0x400))
        + list(range(0x700, 0x7AA))  # exclude 0x7AA mscontext, which is accessible from S-mode
        + list(range(0x7AB, 0x800))
        + list(range(0xB00, 0xC00))
        + list(range(0xF00, 0x1000))
    ):
        tc = test_data.new_test_chunk(test_chunks, "scsr_insufficient_priv")
        tc.code.extend(
            [
                "",
                f"# Testcase: attempt to access CSR 0x{csr:03x}",
                test_data.add_testcase(f"{csr}", coverpoint, covergroup),
                f"csrr t0, 0x{csr:03x}    # attempt to read higher-privilege CSR {csr:03x}; should get illegal instruction",
            ]
        )

    ######################################
    coverpoint = "cp_csr_ro"
    ######################################

    tc = test_data.new_test_chunk(test_chunks, "scsr_ro")
    tc.section_header = comment_banner(
        coverpoint,
        "Attempt to write read-only CSRs.  Should throw illegal instruction",
    )

    for csr in range(0xC00, 0xF00):
        tc = test_data.new_test_chunk(test_chunks)
        r1 = test_data.int_regs.get_register()
        tc.code.extend(
            [
                "",
                f"# Testcase: attempt to access CSR 0x{csr:03x}",
                test_data.add_testcase(f"{csr}", coverpoint, covergroup),
                f"LI(x{r1}, -1)          # x{r1} = all 1s",
                f"csrw 0x{csr:03x}, x{r1}    # attempt to write read-only CSR {csr:03x}; should get illegal instruction",
            ]
        )
        test_data.int_regs.return_register(r1)


@add_priv_test_generator(
    "S",
    required_extensions=["S"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_s(test_data: TestData) -> list[TestChunk]:
    """Generate tests for S supervisor-mode testsuite."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()

    tc.code.extend(_generate_srets_tests(test_data))
    tc.code.extend(_generate_scause_tests(test_data))
    tc.code.extend(_generate_sstatus_sd_tests(test_data))
    tc.code.extend(_generate_priv_inst_tests(test_data))

    _generate_scsr_tests(test_data, test_chunks)
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
