##################################
# priv/extensions/sscofpmf.py
# Written by: Ayesha Anwar, ayesha.anwaar2005@gmail.com
# Sscofpmf privileged extension test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Sscofpmf privileged extension test generator (HPM counter overflow/interrupt)."""

from testgen.asm.csr import csr_walk_test
from testgen.asm.helpers import comment_banner
from testgen.asm.interrupts import clr_mtimer_int, clr_stimer_mmode, set_mtimer_int, set_stimer_mmode
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator


def _generate_minh_inhibits_mmode_tests(test_data: TestData) -> list[str]:
    """cp_minh_inhibits_mmode: minh bit inhibits counting in M-mode."""
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_minh_inhibits_mmode"
    ######################################

    r_val, r_temp = test_data.int_regs.get_registers(2, exclude_regs=[0, 31])

    lines = [
        comment_banner(
            "cp_minh_inhibits_mmode",
            "minh bit inhibits counting in M-mode.\n"
            "RVMODEL_MHPMEVENT[55:0] = RVMODEL_MHPMEVENT_VAL, [62]=minh, [63]=0 (OF=0).\n"
            "From M-mode: RVMODEL_MHPMCOUNTER = 0, run RVMODEL_MHPMEVENT_CODE, check if nonzero.",
        ),
        "",
    ]

    for minh_val in [0, 1]:
        binname = f"minh_{minh_val}"

        # Build RVMODEL_MHPMEVENT_VAL with OF=0 (bit 63), minh=minh_val (bit 62)
        lines.extend(
            [
                f"# Testcase: minh = {minh_val}",
                f"LI(x{r_val}, RVMODEL_MHPMEVENT_VAL | {minh_val} << 62)",
                f"CSRW(RVMODEL_MHPMEVENT, x{r_val})",
                "CSRW(RVMODEL_MHPMCOUNTER, zero)   # reset counter to 0 before running",
                "",
                "# Run in M-mode (no mode switch needed, already M-mode here)",
                "RVMODEL_MHPMEVENT_CODE",
                "",
                test_data.add_testcase(binname, coverpoint, covergroup),
                f"CSRR(x{r_temp}, RVMODEL_MHPMCOUNTER)   # sample point for hpmcounter_nonzero",
                "",
            ]
        )

    test_data.int_regs.return_registers([r_val, r_temp])
    return lines


def _generate_of_set_on_overflow_tests(test_data: TestData) -> list[str]:
    """cp_of_set_on_overflow: OF bit is set when hpmcounter overflows (M-mode only)."""
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_of_set_on_overflow"
    ######################################

    r_val, r_temp, r_lcofip = test_data.int_regs.get_registers(3, exclude_regs=[0, 31])

    lines = [
        comment_banner(
            "cp_of_set_on_overflow",
            "OF bit is set when hpmcounter overflows.\n"
            "RVMODEL_MHPMEVENT[55:0] = VAL, [62:58] = 0b11100 (M/S/U guaranteed),\n"
            "[63] = OF (0/1). mip/mie cleared. Counter set to all 1s, run event code\n"
            "at least twice, check OF sets, counter isn't all 0s/1s, LCOFIP fires\n"
            "iff OF was initially 0.",
        ),
        "",
        "# Setup: disable interrupts globally for controlled testing",
        "CSRW(mip, zero)   # clear LCOFIP and other pending bits",
        "CSRW(mie, zero)   # disable interrupts",
        "",
    ]

    for of_initial in [0, 1]:
        binname = f"of_overflow_mmode_of_{of_initial}"

        lines.extend(
            [
                f"# Testcase: M-mode, OF initial = {of_initial}",
                f"LI(x{r_val}, RVMODEL_MHPMEVENT_VAL | (0b11100 << 58) | ({of_initial} << 63))",
                f"CSRW(RVMODEL_MHPMEVENT, x{r_val})",
                f"LI(x{r_temp}, -1)",
                f"CSRW(RVMODEL_MHPMCOUNTER, x{r_temp})   # all 1s -> next count overflows",
                "",
                "RVMODEL_MHPMEVENT_CODE",
                "RVMODEL_MHPMEVENT_CODE   # run at least twice per spec",
                "",
                test_data.add_testcase(binname, coverpoint, covergroup),
                f"CSRR(x{r_temp}, RVMODEL_MHPMEVENT)   # sample point for mhpmevent_of",
                f"CSRR(x{r_temp}, RVMODEL_MHPMCOUNTER)   # sample point for hpmcounter_nonzero/non-all-1s",
                "",
                f"RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})   # wait for RVMODEL_INTERRUPT_LATENCY",
                f"CSRR(x{r_lcofip}, mip)   # sample point for mip_lcofip",
                "",
            ]
        )

    test_data.int_regs.return_registers([r_val, r_temp, r_lcofip])
    return lines


def _generate_overflow_hw_only_tests(test_data: TestData) -> list[str]:
    """cp_overflow_hw_only: OF only set by hardware increments, not software writes (M-mode only)."""
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_overflow_hw_only"
    ######################################

    r_val, r_of = test_data.int_regs.get_registers(2, exclude_regs=[0, 31])

    lines = [
        comment_banner(
            "cp_overflow_hw_only",
            "Counter overflow interrupt triggered by hardware counter increments,\n"
            "not software writes. RVMODEL_MHPMEVENT = 0, mip/mie cleared.\n"
            "Software-write the counter to all 1s then all 0s -- OF must stay 0\n"
            "in both cases, since OF should only latch on a genuine HW increment\n"
            "causing wraparound, not a direct CSR write.",
        ),
        "",
        "CSRW(RVMODEL_MHPMEVENT, zero)",
        "CSRW(mip, zero)   # clear LCOFIE",
        "CSRW(mie, zero)   # disable interrupts",
        "",
    ]

    for step_name, load_val in [("all_1s", -1), ("all_0s", 0)]:
        binname = f"overflow_hw_only_mmode_{step_name}"
        lines.extend(
            [
                f"# Testcase: software write RVMODEL_MHPMCOUNTER = {step_name}",
                f"LI(x{r_val}, {load_val})",
                f"CSRW(RVMODEL_MHPMCOUNTER, x{r_val})",
                "",
                test_data.add_testcase(binname, coverpoint, covergroup),
                f"CSRR(x{r_of}, RVMODEL_MHPMEVENT)   # sample point -- OF (bit 63) must read 0",
                "",
            ]
        )

    test_data.int_regs.return_registers([r_val, r_of])
    return lines


def _generate_scountovf_mcounteren_tests(test_data: TestData) -> list[str]:
    """cp_scountovf_mcounteren: scountovf masked by mcounteren (M-mode only)."""
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_scountovf_mcounteren"
    ######################################

    MHPMEVENTH_CSRS = [f"CSR_MHPMEVENTH{n}" for n in range(3, 32)]  # RV32: 29 registers
    MHPMEVENT_CSRS = [f"CSR_MHPMEVENT{n}" for n in range(3, 32)]  # RV64: 29 registers

    lines = [
        comment_banner(
            "cp_scountovf_mcounteren",
            "scountovf masked by mcounteren -- M-mode only for now.\n"
            "Write OF patterns (all_ones/checker_even/checker_odd) across\n"
            "mhpmevent3..31.OF, walk mcounteren, read scountovf. In M-mode,\n"
            "scountovf should equal the value written, regardless of mcounteren.",
        ),
        "",
    ]

    of_patterns = {
        "all_ones": lambda i: 1,
        "checker_even": lambda i: 1 if i % 2 == 0 else 0,
        "checker_odd": lambda i: 1 if i % 2 == 1 else 0,
    }

    for of_name, of_bit_fn in of_patterns.items():
        r_of_bit = test_data.int_regs.get_register(exclude_regs=[0, 31])

        lines.append("#if __riscv_xlen == 32")
        lines.append(f"LI(x{r_of_bit}, {1 << 31})   # OF bit (bit 31 of mhpmeventh, RV32)")
        lines.append(f"# --- Write OF pattern: {of_name} across mhpmeventh3..31 (RV32) ---")
        for i, csr_name in enumerate(MHPMEVENTH_CSRS):
            op = "CSRS" if of_bit_fn(i) else "CSRC"
            lines.append(f"{op}({csr_name}, x{r_of_bit})   # {'set' if of_bit_fn(i) else 'clear'} OF bit -- {csr_name}")
        lines.append("#else")
        lines.append(f"LI(x{r_of_bit}, {1 << 63})   # OF bit (bit 63 of mhpmevent, RV64)")
        lines.append(f"# --- Write OF pattern: {of_name} across mhpmevent3..31 (RV64) ---")
        for i, csr_name in enumerate(MHPMEVENT_CSRS):
            op = "CSRS" if of_bit_fn(i) else "CSRC"
            lines.append(f"{op}({csr_name}, x{r_of_bit})   # {'set' if of_bit_fn(i) else 'clear'} OF bit -- {csr_name}")
        lines.append("#endif")
        lines.append("")

        test_data.int_regs.return_registers([r_of_bit])

        lines.extend(
            csr_walk_test(
                test_data,
                csr=("mcounteren", 0xFFFFFFF8),
                covergroup=covergroup,
                coverpoint=f"{coverpoint}_{of_name}",
                start_bit=3,
                walk_zeros=True,
            )
        )

        # Acquire only for the final sample read
        r_scountovf = test_data.int_regs.get_register(exclude_regs=[0, 31])
        lines.append(f"CSRR(x{r_scountovf}, scountovf)   # sample point")
        lines.append("")
        test_data.int_regs.return_registers([r_scountovf])

    return lines


def _generate_sscofpmf_access_tests(test_data: TestData) -> list[str]:
    """cp_sscofpmf_access: read, write 1s, write 0s, set, clear on hpm CSRs."""
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_sscofpmf_access"
    ######################################

    access_types = ["read", "write_ones", "write_zeros", "set", "clear"]
    r_val = test_data.int_regs.get_register(exclude_regs=[0, 31])

    lines = [
        comment_banner(
            "cp_sscofpmf_access",
            "Attempt to read, write 1s, write 0s, set, clear:\nFrom M: scountovf\nIf RV32: from M: mhpmeventh3...31",
        ),
        "",
    ]

    def emit_accesses(csr_name: str) -> None:
        for access in access_types:
            binname = f"sscofpmf_access_{csr_name}_{access}"
            lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

            if access == "read":
                lines.append(f"CSRR(x{r_val}, {csr_name})")
            elif access == "write_ones":
                lines.extend([f"LI(x{r_val}, -1)", f"CSRW({csr_name}, x{r_val})"])
            elif access == "write_zeros":
                lines.append(f"CSRW({csr_name}, zero)")
            elif access == "set":
                lines.extend([f"LI(x{r_val}, -1)", f"CSRS({csr_name}, x{r_val})"])
            elif access == "clear":
                lines.extend([f"LI(x{r_val}, -1)", f"CSRC({csr_name}, x{r_val})"])
            lines.append("")

    emit_accesses("scountovf")

    lines.append("#if __riscv_xlen == 32")
    for n in range(3, 32):
        emit_accesses(f"CSR_MHPMEVENTH{n}")
    lines.append("#endif")

    test_data.int_regs.return_registers([r_val])
    return lines


def _generate_lcofip_priority_tests(test_data: TestData) -> list[str]:
    """cp_lcofip_priority: priority of LCOFI interrupt (M-mode only for now)."""
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_lcofip_priority"
    ######################################

    LCOFIP_BIT = 1 << 13  # mip bit 13, per coverpoints file: ins.current.csr[CSR_MIP][13]

    r1, r_mtime, r_mtimecmp, r_temp, r_temp2, r_scratch = test_data.int_regs.get_registers(6, exclude_regs=[0, 31])

    lines = [
        comment_banner(
            "cp_lcofip_priority",
            "Priority of LCOFI interrupt (M-mode only for now; 7 interrupts).\n"
            "mstatus.MIE=1, mstatus.SIE=1, mie=all 0s.\n"
            "mip = 1 in LCOFIP and one of {MEIP,MTIP,MSIP,SEIP,STIP,SSIP,none}.\n"
            "mie = all 1s. Highest priority interrupt fires; LCOFIP only fires\n"
            "if none of the others are pending (lowest priority).",
        ),
        "",
        "# Setup: mstatus.MIE=1, mstatus.SIE=1",
        "csrsi mstatus, 0x8   # MIE",
        "csrsi mstatus, 0x2   # SIE",
        "CSRW(mie, zero)      # mie = all 0s initially",
        "",
    ]

    other_interrupts = ["meip", "mtip", "msip", "seip", "stip", "ssip", "none"]

    for other_int in other_interrupts:
        binname = f"lcofip_priority_mmode_{other_int}"

        lines.append(f"# Testcase: competing interrupt = {other_int}")
        lines.extend(
            [
                f"LI(x{r_scratch}, {hex(LCOFIP_BIT)})",
                f"CSRS(mip, x{r_scratch})   # set mip.LCOFIP directly",
            ]
        )

        # Trigger the competing interrupt using confirmed macros/patterns
        if other_int == "meip":
            lines.append("RVTEST_SET_MEXT_INT")
        elif other_int == "mtip":
            lines.extend(set_mtimer_int(r_mtime, r_mtimecmp, r_temp, r_temp2))
        elif other_int == "msip":
            lines.append("RVTEST_SET_MSW_INT")
        elif other_int == "seip":
            lines.append("RVTEST_SET_SEXT_INT")
        elif other_int == "stip":
            lines.extend(set_stimer_mmode(r_scratch))
        elif other_int == "ssip":
            lines.extend([f"LI(x{r1}, 0x2)", f"CSRS(mip, x{r1})"])
        # "none" -- no competing interrupt triggered

        lines.extend(
            [
                f"LI(x{r_temp}, -1)",
                f"CSRW(mie, x{r_temp})   # mie = all 1s",
                "",
                test_data.add_testcase(binname, coverpoint, covergroup),
                f"RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})",
                "",
            ]
        )

        # Cleanup
        if other_int == "meip":
            lines.append("RVTEST_CLR_MEXT_INT")
        elif other_int == "mtip":
            lines.extend(clr_mtimer_int(r_temp, r_mtimecmp))
        elif other_int == "msip":
            lines.append("RVTEST_CLR_MSW_INT")
        elif other_int == "seip":
            lines.append("RVTEST_CLR_SEXT_INT")
        elif other_int == "stip":
            lines.extend(clr_stimer_mmode(r_scratch))
        elif other_int == "ssip":
            lines.extend([f"LI(x{r1}, 0x2)", f"CSRC(mip, x{r1})"])

        lines.extend(
            [
                f"LI(x{r_scratch}, {hex(LCOFIP_BIT)})",
                f"CSRC(mip, x{r_scratch})   # clear LCOFIP for next iteration",
                "CSRW(mie, zero)",
                "",
            ]
        )

    test_data.int_regs.return_registers([r1, r_mtime, r_mtimecmp, r_temp, r_temp2, r_scratch])
    return lines


@add_priv_test_generator("Sscofpmf", required_extensions=["Sscofpmf"])
def make_sscofpmf(test_data: TestData) -> list[TestChunk]:
    """Generate tests for Sscofpmf performance counter overflow/interrupt support."""
    tc = test_data.begin_test_chunk()
    tc.code.extend(_generate_minh_inhibits_mmode_tests(test_data))
    tc.code.extend(_generate_of_set_on_overflow_tests(test_data))
    tc.code.extend(_generate_overflow_hw_only_tests(test_data))
    tc.code.extend(_generate_scountovf_mcounteren_tests(test_data))
    tc.code.extend(_generate_sscofpmf_access_tests(test_data))
    tc.code.extend(_generate_lcofip_priority_tests(test_data))
    return [test_data.end_test_chunk()]
