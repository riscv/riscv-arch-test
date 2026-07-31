##################################
# priv/extensions/SscofpmfCommon.py
# Written by: Ayesha Anwar, ayesha.anwaar2005@gmail.com
# Sscofpmf (HPM counter overflow/interrupt) shared test-case generators.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared Sscofpmf test-case generators, called with priv_mode in {"Sm", "S", "U"}."""

from testgen.asm.csr import csr_walk_test
from testgen.asm.helpers import comment_banner
from testgen.asm.interrupts import clr_mtimer_int, clr_stimer_mmode, set_mtimer_int, set_stimer_mmode
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk


def _csr_access(instr: str, mode: str) -> str:
    """Access a (currently M-only) CSR directly in Sm, or via T-SBI call from S/U."""
    if mode == "Sm":
        return instr
    return tsbi_call(instr)


def _mode_suffix(mode: str) -> str:
    return mode.lower()


def _generate_minh_inhibits_tests(test_data: TestData, mode: str) -> list[str]:
    """cp_minh_inhibits_{mode}: minh bit inhibits counting."""
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = f"cp_minh_inhibits_{_mode_suffix(mode)}"
    ######################################

    r_val, r_temp = test_data.int_regs.get_registers(2, exclude_regs=[0, 31])

    lines = [
        comment_banner(
            coverpoint,
            "minh bit inhibits counting.\n"
            "RVMODEL_MHPMEVENT[55:0] = RVMODEL_MHPMEVENT_VAL, [62]=minh, [63]=0 (OF=0).\n"
            "RVMODEL_MHPMCOUNTER = 0, run RVMODEL_MHPMEVENT_CODE, check if nonzero.",
        ),
        "",
    ]

    for minh_val in [0, 1]:
        binname = f"minh_{minh_val}_{_mode_suffix(mode)}"

        lines.extend(
            [
                f"# Testcase: minh = {minh_val}, mode = {mode}",
                f"LI(x{r_val}, RVMODEL_MHPMEVENT_VAL | {minh_val} << 62)",
                _csr_access(f"csrw RVMODEL_MHPMEVENT, x{r_val}", mode),
                _csr_access("csrw RVMODEL_MHPMCOUNTER, zero   # reset counter to 0 before running", mode),
                "",
                f"LA(x{r_temp}, scratch)",
                "# Incrementing RVMODEL_MHPMCOUNTER in DUT specific way",
                f"RVMODEL_MHPMEVENT_CODE(x{r_temp}, x{r_val})",
                "",
                test_data.add_testcase(binname, coverpoint, covergroup),
                _csr_access(f"csrr x{r_temp}, RVMODEL_MHPMCOUNTER   # sample point for hpmcounter_nonzero", mode),
                "",
            ]
        )

    test_data.int_regs.return_registers([r_val, r_temp])
    return lines


def _generate_of_set_on_overflow_tests(test_data: TestData, mode: str) -> list[str]:
    """cp_of_set_on_overflow: OF bit is set when hpmcounter overflows."""
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_of_set_on_overflow"
    ######################################

    r_val, r_temp, r_lcofip, r_addr = test_data.int_regs.get_registers(4, exclude_regs=[0, 31])

    lines = [
        comment_banner(
            coverpoint,
            "OF bit is set when hpmcounter overflows.\n"
            "RVMODEL_MHPMEVENT[55:0] = VAL, [62:58] = 0b11100 (M/S/U guaranteed),\n"
            "[63] = OF (0/1). mip/mie cleared. Counter set to all 1s, run event code\n"
            "at least twice, check OF sets, counter isn't all 0s/1s, LCOFIP fires\n"
            "iff OF was initially 0.",
        ),
        "",
        "# Setup: disable interrupts globally for controlled testing",
        _csr_access("csrw mip, zero   # clear LCOFIP and other pending bits", mode),
        _csr_access("csrw mie, zero   # disable interrupts", mode),
        "",
    ]

    for of_initial in [0, 1]:
        binname = f"of_overflow_{_mode_suffix(mode)}_of_{of_initial}"

        lines.extend(
            [
                f"# Testcase: mode = {mode}, OF initial = {of_initial}",
                f"LI(x{r_val}, RVMODEL_MHPMEVENT_VAL | (0b11100 << 58) | ({of_initial} << 63))",
                _csr_access(f"csrw RVMODEL_MHPMEVENT, x{r_val}", mode),
                f"LI(x{r_temp}, -1)",
                _csr_access(f"csrw RVMODEL_MHPMCOUNTER, x{r_temp}   # all 1s -> next count overflows", mode),
                "",
                f"LA(x{r_addr}, scratch)",
                "# Incrementing RVMODEL_MHPMCOUNTER in DUT specific way",
                f"RVMODEL_MHPMEVENT_CODE(x{r_addr}, x{r_val})",
                f"RVMODEL_MHPMEVENT_CODE(x{r_addr}, x{r_val})   # run at least twice per spec",
                "",
                test_data.add_testcase(binname, coverpoint, covergroup),
                _csr_access(f"csrr x{r_temp}, RVMODEL_MHPMEVENT   # sample point for mhpmevent_of", mode),
                _csr_access(
                    f"csrr x{r_temp}, RVMODEL_MHPMCOUNTER   # sample point for hpmcounter_nonzero/non-all-1s", mode
                ),
                "",
                f"RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})   # wait for RVMODEL_INTERRUPT_LATENCY",
                _csr_access(f"csrr x{r_lcofip}, mip   # sample point for mip_lcofip", mode),
                "",
            ]
        )

    test_data.int_regs.return_registers([r_val, r_temp, r_lcofip, r_addr])
    return lines


def _generate_overflow_hw_only_tests(test_data: TestData, mode: str) -> list[str]:
    """cp_overflow_hw_only: OF only set by hardware increments, not software writes."""
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_overflow_hw_only"
    ######################################

    r_val, r_of = test_data.int_regs.get_registers(2, exclude_regs=[0, 31])

    lines = [
        comment_banner(
            coverpoint,
            "Counter overflow interrupt triggered by hardware counter increments,\n"
            "not software writes. RVMODEL_MHPMEVENT = 0, mip/mie cleared.\n"
            "Software-write the counter to all 1s then all 0s -- OF must stay 0\n"
            "in both cases, since OF should only latch on a genuine HW increment\n"
            "causing wraparound, not a direct CSR write.",
        ),
        "",
        _csr_access("csrw RVMODEL_MHPMEVENT, zero", mode),
        _csr_access("csrw mip, zero   # clear LCOFIE", mode),
        _csr_access("csrw mie, zero   # disable interrupts", mode),
        "",
    ]

    for step_name, load_val in [("all_1s", -1), ("all_0s", 0)]:
        binname = f"overflow_hw_only_{_mode_suffix(mode)}_{step_name}"
        lines.extend(
            [
                f"# Testcase: software write RVMODEL_MHPMCOUNTER = {step_name}, mode = {mode}",
                f"LI(x{r_val}, {load_val})",
                _csr_access(f"csrw RVMODEL_MHPMCOUNTER, x{r_val}", mode),
                "",
                test_data.add_testcase(binname, coverpoint, covergroup),
                _csr_access(f"csrr x{r_of}, RVMODEL_MHPMEVENT   # sample point -- OF (bit 63) must read 0", mode),
                "",
            ]
        )

    test_data.int_regs.return_registers([r_val, r_of])
    return lines


def _generate_scountovf_mcounteren_tests(test_data: TestData, mode: str) -> list[str]:
    """cp_scountovf_mcounteren: scountovf masked by mcounteren."""
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_scountovf_mcounteren"
    ######################################

    MHPMEVENTH_CSRS = [f"CSR_MHPMEVENT{n}H" for n in range(3, 32)]  # RV32: 29 registers
    MHPMEVENT_CSRS = [f"CSR_MHPMEVENT{n}" for n in range(3, 32)]  # RV64: 29 registers

    lines = [
        comment_banner(
            coverpoint,
            f"scountovf masked by mcounteren -- mode = {mode}.\n"
            "Write OF patterns (all_ones/checker_even/checker_odd) across\n"
            "mhpmevent3..31.OF, walk mcounteren, read scountovf.",
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
            op = "csrs" if of_bit_fn(i) else "csrc"
            lines.append(
                _csr_access(
                    f"{op} {csr_name}, x{r_of_bit}   # {'set' if of_bit_fn(i) else 'clear'} OF bit -- {csr_name}", mode
                )
            )
        lines.append("#else")
        lines.append(f"LI(x{r_of_bit}, {1 << 63})   # OF bit (bit 63 of mhpmevent, RV64)")
        lines.append(f"# --- Write OF pattern: {of_name} across mhpmevent3..31 (RV64) ---")
        for i, csr_name in enumerate(MHPMEVENT_CSRS):
            op = "csrs" if of_bit_fn(i) else "csrc"
            lines.append(
                _csr_access(
                    f"{op} {csr_name}, x{r_of_bit}   # {'set' if of_bit_fn(i) else 'clear'} OF bit -- {csr_name}", mode
                )
            )
        lines.append("#endif")
        lines.append("")

        test_data.int_regs.return_registers([r_of_bit])

        lines.extend(
            csr_walk_test(
                test_data,
                csr=("mcounteren", 0xFFFFFFF8),
                covergroup=covergroup,
                coverpoint=f"{coverpoint}_{of_name}_{_mode_suffix(mode)}",
                start_bit=3,
                walk_zeros=True,
            )
        )

        r_scountovf = test_data.int_regs.get_register(exclude_regs=[0, 31])
        lines.append(_csr_access(f"csrr x{r_scountovf}, scountovf   # sample point", mode))
        lines.append("")
        test_data.int_regs.return_registers([r_scountovf])

    return lines


def _generate_sscofpmf_access_tests(test_data: TestData, mode: str) -> list[str]:
    """cp_sscofpmf_access: read, write 1s, write 0s, set, clear on hpm CSRs."""
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_sscofpmf_access"
    ######################################

    access_types = ["read", "write_ones", "write_zeros", "set", "clear"]
    r_val = test_data.int_regs.get_register(exclude_regs=[0, 31])

    lines = [
        comment_banner(
            coverpoint,
            f"Attempt to read, write 1s, write 0s, set, clear from mode = {mode}:\n"
            "scountovf\nIf RV32: mhpmeventh3...31",
        ),
        "",
    ]

    def emit_accesses(csr_name: str) -> None:
        for access in access_types:
            binname = f"sscofpmf_access_{csr_name}_{access}_{_mode_suffix(mode)}"
            lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

            if access == "read":
                lines.append(_csr_access(f"csrr x{r_val}, {csr_name}", mode))
            elif access == "write_ones":
                lines.extend([f"LI(x{r_val}, -1)", _csr_access(f"csrw {csr_name}, x{r_val}", mode)])
            elif access == "write_zeros":
                lines.append(_csr_access(f"csrw {csr_name}, zero", mode))
            elif access == "set":
                lines.extend([f"LI(x{r_val}, -1)", _csr_access(f"csrs {csr_name}, x{r_val}", mode)])
            elif access == "clear":
                lines.extend([f"LI(x{r_val}, -1)", _csr_access(f"csrc {csr_name}, x{r_val}", mode)])
            lines.append("")

    emit_accesses("scountovf")

    lines.append("#if __riscv_xlen == 32")
    for n in range(3, 32):
        emit_accesses(f"CSR_MHPMEVENT{n}H")
    lines.append("#endif")

    test_data.int_regs.return_registers([r_val])
    return lines


def _generate_lcofip_priority_tests(test_data: TestData, mode: str) -> list[str]:
    """cp_lcofip_priority: priority of LCOFI interrupt."""
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_lcofip_priority"
    ######################################

    LCOFIP_BIT = 1 << 13  # mip bit 13, per coverpoints file: ins.current.csr[CSR_MIP][13]

    r1, r_mtime, r_mtimecmp, r_temp, r_temp2, r_scratch = test_data.int_regs.get_registers(6, exclude_regs=[0, 31])

    lines = [
        comment_banner(
            coverpoint,
            f"Priority of LCOFI interrupt (mode = {mode}; 7 interrupts).\n"
            "mstatus.MIE=1, mstatus.SIE=1, mie=all 0s.\n"
            "mip = 1 in LCOFIP and one of {MEIP,MTIP,MSIP,SEIP,STIP,SSIP,none}.\n"
            "mie = all 1s. Highest priority interrupt fires; LCOFIP only fires\n"
            "if none of the others are pending (lowest priority).",
        ),
        "",
        "# Setup: mstatus.MIE=1, mstatus.SIE=1",
        "csrsi mstatus, 0x8   # MIE",
        "csrsi mstatus, 0x2   # SIE",
        _csr_access("csrw mie, zero      # mie = all 0s initially", mode),
        "",
    ]

    other_interrupts = ["meip", "mtip", "msip", "seip", "stip", "ssip", "none"]

    for other_int in other_interrupts:
        binname = f"lcofip_priority_{_mode_suffix(mode)}_{other_int}"

        lines.append(f"# Testcase: competing interrupt = {other_int}, mode = {mode}")
        lines.extend(
            [
                f"LI(x{r_scratch}, {hex(LCOFIP_BIT)})",
                _csr_access(f"csrs mip, x{r_scratch}   # set mip.LCOFIP directly", mode),
            ]
        )

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
            lines.extend([f"LI(x{r1}, 0x2)", _csr_access(f"csrs mip, x{r1}", mode)])
        # "none" -- no competing interrupt triggered

        lines.extend(
            [
                f"LI(x{r_temp}, -1)",
                _csr_access(f"csrw mie, x{r_temp}   # mie = all 1s", mode),
                "",
                test_data.add_testcase(binname, coverpoint, covergroup),
                f"RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})",
                "",
            ]
        )

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
            lines.extend([f"LI(x{r1}, 0x2)", _csr_access(f"csrc mip, x{r1}", mode)])

        lines.extend(
            [
                f"LI(x{r_scratch}, {hex(LCOFIP_BIT)})",
                _csr_access(f"csrc mip, x{r_scratch}   # clear LCOFIP for next iteration", mode),
                _csr_access("csrw mie, zero", mode),
                "",
            ]
        )

    test_data.int_regs.return_registers([r1, r_mtime, r_mtimecmp, r_temp, r_temp2, r_scratch])
    return lines


def generate_sscofpmf_suite(test_data: TestData, mode: str) -> list[TestChunk]:
    """Assemble the full Sscofpmf suite for ``mode`` ("Sm"/"S"/"U") as a test chunk."""
    tc = test_data.begin_test_chunk()
    tc.code.extend(_generate_minh_inhibits_tests(test_data, mode))
    tc.code.extend(_generate_of_set_on_overflow_tests(test_data, mode))
    tc.code.extend(_generate_overflow_hw_only_tests(test_data, mode))
    tc.code.extend(_generate_scountovf_mcounteren_tests(test_data, mode))
    tc.code.extend(_generate_sscofpmf_access_tests(test_data, mode))
    tc.code.extend(_generate_lcofip_priority_tests(test_data, mode))
    return [test_data.end_test_chunk()]
