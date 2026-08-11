##################################
# priv/extensions/SscofpmfCommon.py
# Written by: Ayesha Anwar, ayesha.anwaar2005@gmail.com
# Sscofpmf (HPM counter overflow/interrupt) shared test-case generators.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared Sscofpmf test-case generators, called with priv_mode in {"Sm", "S", "U"}."""

# In SscofpmfCommon.py
import re

from testgen.asm.csr import csr_walk_test
from testgen.asm.helpers import comment_banner
from testgen.asm.interrupts import clr_mtimer_int, clr_stimer_mmode, set_mtimer_int, set_stimer_mmode
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk

_FIXED_TSBI_ALIASES = {
    "RVMODEL_MHPMEVENT": "0x323",  # mhpmevent3
    "RVMODEL_MHPMCOUNTER": "0xb03",  # mhpmcounter3
    "scountovf": "0xda0",
}

_MHPMEVENT_RE = re.compile(r"\bCSR_MHPMEVENT(\d+)(H)?\b")


def _resolve_tsbi_csr(instr: str) -> str:
    """Substitute Sscofpmf CSR names/macros with literal hex addresses for tsbi_call()."""
    for macro, hexaddr in _FIXED_TSBI_ALIASES.items():
        instr = instr.replace(macro, hexaddr)

    def _sub_mhpmevent(m: re.Match) -> str:
        n = int(m.group(1))
        base = 0x720 if m.group(2) else 0x320  # ...H = mhpmeventh (RV32 OF-bit high half)
        return hex(base + n)

    return _MHPMEVENT_RE.sub(_sub_mhpmevent, instr)


def _csr_access(instr: str, mode: str) -> str:
    """Access a (currently M-only) CSR directly in Sm, or via T-SBI call from S/U."""
    if mode == "Sm":
        return instr
    return tsbi_call(_resolve_tsbi_csr(instr))


def _mode_suffix(mode: str) -> str:
    return mode.lower()


def _generate_xinh_inhibits_tests(test_data: TestData, priv_mode: str) -> list[str]:
    """cp_xinh_inhibits_xmode: xINH bit inhibits counting in (M/S/U)-mode.

    x tracks priv_mode: MINH(bit 62) for Sm, SINH(bit 61) for S, UINH(bit 60) for U.
    """
    _INHIBIT_BIT_POS = {"Sm": 62, "S": 61, "U": 60}  # MINH, SINH, UINH in mhpmevent[62:58]
    _INHIBIT_PREFIX = {"Sm": "m", "S": "s", "U": "u"}

    ######################################
    covergroup = "Sscofpmf_cg"
    inh_prefix = _INHIBIT_PREFIX[priv_mode]
    coverpoint = f"cp_{inh_prefix}inh_inhibits_{priv_mode.lower()}mode"
    inh_bit_pos = _INHIBIT_BIT_POS[priv_mode]
    ######################################

    r_val, r_temp = test_data.int_regs.get_registers(2, exclude_regs=[0, 31])

    lines = [
        comment_banner(
            coverpoint,
            f"{inh_prefix.upper()}INH bit (mhpmevent[{inh_bit_pos}]) inhibits counting in "
            f"{priv_mode}-mode.\n"
            "No mip/mie involvement here, so no interrupt/T-SBI ordering hazard;\n"
            "mode switch simply wraps the SBI-mediated CSR accesses per spec.",
        ),
        "",
    ]

    if priv_mode != "Sm":
        lines.append(f"RVTEST_GOTO_LOWER_MODE {priv_mode}mode")
    indent = "" if priv_mode == "Sm" else "    "

    for inh_val in [0, 1]:
        binname = f"{inh_prefix}inh_{inh_val}_{priv_mode.lower()}"

        lines.extend(
            [
                f"{indent}# Testcase: {inh_prefix}inh = {inh_val}",
                f"{indent}LI(x{r_val}, RVMODEL_MHPMEVENT_VAL | {inh_val} << {inh_bit_pos})",
                f"{indent}{_csr_access(f'csrw RVMODEL_MHPMEVENT, x{r_val}', priv_mode)}",
                f"{indent}{_csr_access('csrw RVMODEL_MHPMCOUNTER, zero   # reset counter to 0 before running', priv_mode)}",
                "",
                f"{indent}LA(x{r_temp}, scratch)",
                f"{indent}# Incrementing RVMODEL_MHPMCOUNTER in DUT specific way",
                f"{indent}RVMODEL_MHPMEVENT_CODE(x{r_temp}, x{r_val})",
                "",
                f"{indent}{test_data.add_testcase(binname, coverpoint, covergroup)}",
                f"{indent}{_csr_access(f'csrr x{r_temp}, RVMODEL_MHPMCOUNTER   # sample point for hpmcounter_nonzero', priv_mode)}",
                "",
            ]
        )

    if priv_mode != "Sm":
        lines.append("RVTEST_GOTO_MMODE")

    test_data.int_regs.return_registers([r_val, r_temp])
    return lines


def _generate_of_set_on_overflow_tests(test_data: TestData, priv_mode: str) -> list[str]:
    """cp_of_set_on_overflow: OF bit is set when hpmcounter overflows."""
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_of_set_on_overflow"
    ######################################

    r_val, r_temp, r_lcofip, r_addr = test_data.int_regs.get_registers(4, exclude_regs=[0, 31])

    lines = [
        comment_banner(
            coverpoint,
            "OF bit is set when hpmcounter overflows.\n",
        ),
        "",
    ]

    for of_initial in [0, 1]:
        binname = f"of_overflow_{priv_mode.lower()}_of_{of_initial}"

        lines.extend(
            [
                "",
                "# === M-MODE SETUP ===",
                f"# Testcase: mode = {priv_mode}, OF initial = {of_initial}",
                "csrw mip, zero   # clear LCOFIP and other pending bits (direct, M-mode)",
                "csrw mie, zero   # disable interrupts (direct, M-mode)",
                f"LI(x{r_val}, RVMODEL_MHPMEVENT_VAL | (0b11100 << 58) | ({of_initial} << 63))",
            ]
        )

        if priv_mode == "Sm":
            lines.extend(
                [
                    f"csrw RVMODEL_MHPMEVENT, x{r_val}",
                    f"LI(x{r_temp}, -1)",
                    f"csrw RVMODEL_MHPMCOUNTER, x{r_temp}   # all 1s -> next count overflows",
                    "",
                    f"LA(x{r_addr}, scratch)",
                    "# Incrementing RVMODEL_MHPMCOUNTER in DUT specific way",
                    f"RVMODEL_MHPMEVENT_CODE(x{r_addr}, x{r_val})",
                    f"RVMODEL_MHPMEVENT_CODE(x{r_addr}, x{r_val})   # run at least twice per spec",
                    "",
                    test_data.add_testcase(binname, coverpoint, covergroup),
                    f"csrr x{r_temp}, RVMODEL_MHPMEVENT   # sample point for mhpmevent_of",
                    f"csrr x{r_temp}, RVMODEL_MHPMCOUNTER   # sample point for hpmcounter_nonzero/non-all-1s",
                    "",
                    f"RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})   # wait for RVMODEL_INTERRUPT_LATENCY",
                    f"csrr x{r_lcofip}, mip   # sample point for mip_lcofip",
                ]
            )
        else:
            lines.extend(
                [
                    f"# RVMODEL_MHPMEVENT/RVMODEL_MHPMCOUNTER writes go via SBI from {priv_mode}-mode, per spec",
                    test_data.add_testcase(binname, coverpoint, covergroup),
                    f"RVTEST_GOTO_LOWER_MODE {priv_mode}mode",
                    f"    {_csr_access(f'csrw RVMODEL_MHPMEVENT, x{r_val}', priv_mode)}",
                    f"    LI(x{r_temp}, -1)",
                    f"    {_csr_access(f'csrw RVMODEL_MHPMCOUNTER, x{r_temp}   # all 1s -> next count overflows', priv_mode)}",
                    "",
                    f"    LA(x{r_addr}, scratch)",
                    "    # Incrementing RVMODEL_MHPMCOUNTER in DUT specific way",
                    f"    RVMODEL_MHPMEVENT_CODE(x{r_addr}, x{r_val})",
                    f"    RVMODEL_MHPMEVENT_CODE(x{r_addr}, x{r_val})   # run at least twice per spec",
                    "",
                    f"    {_csr_access(f'csrr x{r_temp}, RVMODEL_MHPMEVENT   # sample point for mhpmevent_of', priv_mode)}",
                    f"    {_csr_access(f'csrr x{r_temp}, RVMODEL_MHPMCOUNTER   # sample point for hpmcounter_nonzero/non-all-1s', priv_mode)}",
                    "",
                    f"    RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})   # wait for RVMODEL_INTERRUPT_LATENCY",
                    "RVTEST_GOTO_MMODE",
                    f"csrr x{r_lcofip}, mip   # sample point for mip_lcofip (direct, back in M-mode)",
                ]
            )

    test_data.int_regs.return_registers([r_val, r_temp, r_lcofip, r_addr])
    return lines


def _generate_overflow_hw_only_tests(test_data: TestData, priv_mode: str) -> list[str]:
    """cp_overflow_hw_only: OF only set by hardware increments, not software writes."""
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_overflow_hw_only"
    ######################################

    r_val, r_of = test_data.int_regs.get_registers(2, exclude_regs=[0, 31])

    lines = [
        comment_banner(
            coverpoint,
        ),
        "",
        "# === M-MODE SETUP ===",
        "csrw mip, zero   # clear LCOFIE (direct, M-mode)",
        "csrw mie, zero   # disable interrupts (direct, M-mode)",
        "",
    ]

    if priv_mode == "Sm":
        lines.append("csrw RVMODEL_MHPMEVENT, zero")
    else:
        lines.append(f"RVTEST_GOTO_LOWER_MODE {priv_mode}mode")
        lines.append(f"    {_csr_access('csrw RVMODEL_MHPMEVENT, zero', priv_mode)}")

    for step_name, load_val in [("all_1s", -1), ("all_0s", 0)]:
        binname = f"overflow_hw_only_{priv_mode.lower()}_{step_name}"
        indent = "" if priv_mode == "Sm" else "    "
        lines.extend(
            [
                f"{indent}# Testcase: software write RVMODEL_MHPMCOUNTER = {step_name}, mode = {priv_mode}",
                f"{indent}LI(x{r_val}, {load_val})",
                f"{indent}{_csr_access(f'csrw RVMODEL_MHPMCOUNTER, x{r_val}', priv_mode)}",
                "",
                f"{indent}{test_data.add_testcase(binname, coverpoint, covergroup)}",
                f"{indent}{_csr_access(f'csrr x{r_of}, RVMODEL_MHPMEVENT   # sample point -- OF (bit 63) must read 0', priv_mode)}",
                "",
            ]
        )

    if priv_mode != "Sm":
        lines.append("RVTEST_GOTO_MMODE")

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
    if mode == "U":
        return []

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

    def emit_accesses(csr_name: str, indent: str = "") -> None:
        for access in access_types:
            binname = f"sscofpmf_access_{csr_name}_{access}_{_mode_suffix(mode)}"
            lines.append(f"{indent}{test_data.add_testcase(binname, coverpoint, covergroup)}")

            if access == "read":
                lines.append(f"{indent}csrr x{r_val}, {csr_name}")
            elif access == "write_ones":
                lines.extend([f"{indent}LI(x{r_val}, -1)", f"{indent}csrw {csr_name}, x{r_val}"])
            elif access == "write_zeros":
                lines.append(f"{indent}csrw {csr_name}, zero")
            elif access == "set":
                lines.extend([f"{indent}LI(x{r_val}, -1)", f"{indent}csrs {csr_name}, x{r_val}"])
            elif access == "clear":
                lines.extend([f"{indent}LI(x{r_val}, -1)", f"{indent}csrc {csr_name}, x{r_val}"])
            lines.append("")

    if mode == "Sm":
        emit_accesses("scountovf")
    else:  # mode == "S"
        lines.append("RVTEST_GOTO_LOWER_MODE Smode")
        emit_accesses("scountovf", indent="    ")
        lines.append("RVTEST_GOTO_MMODE")

    if mode == "Sm":  # mhpmeventh3..31 sweep is M-mode only per spec
        lines.append("#if __riscv_xlen == 32")
        for n in range(3, 32):
            emit_accesses(f"CSR_MHPMEVENT{n}H")
        lines.append("#endif")

    test_data.int_regs.return_registers([r_val])
    return lines


def _generate_lcofi_tests(test_data: TestData, priv_mode: str) -> list[str]:
    if priv_mode == "Sm":
        return []

    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_lcofi"
    ######################################

    LCOFI_BIT = 1 << 13  # mip/mie/mideleg bit 13
    MIE_BIT = 0x8  # mstatus bit 3
    SIE_BIT = 0x2  # mstatus bit 1

    r_val, r_temp = test_data.int_regs.get_registers(2, exclude_regs=[0, 31])

    lines = [
        comment_banner(
            coverpoint,
            f"Interrupt pending and enable, mode = {priv_mode}.\n",
        ),
        "",
        "# === M-MODE SETUP ===",
        "csrw mip, zero      # clear all pending",
        "csrw mie, zero      # disable all interrupts",
        f"LI(x{r_val}, {hex(MIE_BIT)})",
        f"csrc mstatus, x{r_val}   # mstatus.MIE = 0",
        f"LI(x{r_val}, {hex(SIE_BIT)})",
        f"csrs mstatus, x{r_val}   # mstatus.SIE = 1",
    ]

    for lcofip in [0, 1]:
        for lcofie in [0, 1]:
            for mideleg_bit in [0, 1]:
                binname = f"lcofi_{priv_mode.lower()}_lcofip_{lcofip}_lcofie_{lcofie}_mideleg_{mideleg_bit}"
                lines.extend(
                    [
                        "",
                        (
                            f"# Testcase: mip.LCOFIP={lcofip}, mie.LCOFIE={lcofie}, "
                            f"mideleg.LCOFI={mideleg_bit}, mode={priv_mode}"
                        ),
                        f"LI(x{r_temp}, {hex(LCOFI_BIT)})",
                        f"{'csrs' if lcofip else 'csrc'} mip, x{r_temp}   # mip.LCOFIP = {lcofip}",
                        f"{'csrs' if lcofie else 'csrc'} mie, x{r_temp}   # mie.LCOFIE = {lcofie}",
                        f"{'csrs' if mideleg_bit else 'csrc'} mideleg, x{r_temp}   # mideleg.LCOFI = {mideleg_bit}",
                        "",
                        test_data.add_testcase(binname, coverpoint, covergroup),
                        f"RVTEST_GOTO_LOWER_MODE {priv_mode}mode",
                        "    # Fires here immediately if LCOFIP=1 & LCOFIE=1; else falls through.",
                        "    nop",
                        "    nop",
                        "    nop",
                        "    nop",
                        "RVTEST_GOTO_MMODE",
                    ]
                )

    lines.extend(
        [
            "",
            "# === M-MODE CLEANUP ===",
            f"LI(x{r_temp}, {hex(LCOFI_BIT)})",
            f"csrc mip, x{r_temp}      # clear LCOFIP",
            f"csrc mie, x{r_temp}      # clear LCOFIE",
            f"csrc mideleg, x{r_temp}  # clear mideleg.LCOFI",
            f"LI(x{r_val}, {hex(SIE_BIT)})",
            f"csrc mstatus, x{r_val}   # mstatus.SIE = 0",
        ]
    )

    test_data.int_regs.return_registers([r_val, r_temp])
    return lines


def _generate_lcofip_priority_tests(test_data: TestData, priv_mode: str) -> list[str]:
    """cp_lcofip_priority: priority of LCOFI interrupt."""
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_lcofip_priority"
    ######################################

    LCOFIP_BIT = 1 << 13  # mip bit 13
    MIE_BIT = 0x8  # mstatus bit 3
    MPIE_BIT = 0x80  # mstatus bit 7

    r1, r_mtime, r_mtimecmp, r_temp, r_temp2, r_scratch = test_data.int_regs.get_registers(6, exclude_regs=[0, 31])

    lines = [
        comment_banner(
            coverpoint,
            f"Priority of LCOFI interrupt (mode = {priv_mode}; 7 competing interrupts).\n",
        ),
        "",
    ]

    other_interrupts = ["meip", "mtip", "msip", "seip", "stip", "ssip", "none"]

    for other_int in other_interrupts:
        binname = f"lcofip_priority_{priv_mode.lower()}_{other_int}"

        lines.extend(
            [
                "",
                "# === M-MODE SETUP ===",
                f"# Testcase: competing interrupt = {other_int}, mode = {priv_mode}",
                "csrw mie, zero      # disable all interrupts first",
                "csrci mstatus, 0x8  # MIE=0 (set later: direct for Sm, via MPIE for S/U)",
                "csrsi mstatus, 0x2  # SIE",
                f"LI(x{r_scratch}, {hex(LCOFIP_BIT)})",
                f"csrs mip, x{r_scratch}   # set mip.LCOFIP directly",
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
            lines.extend([f"LI(x{r1}, 0x2)", f"csrs mip, x{r1}"])
        # "none" -- no competing interrupt triggered

        lines.extend(
            [
                f"LI(x{r_temp}, -1)",
                f"csrw mie, x{r_temp}   # mie = all 1s; MIE still 0, safe while in M-mode",
            ]
        )

        if priv_mode == "Sm":
            lines.extend(
                [
                    f"LI(x{r_temp2}, {hex(MIE_BIT)})",
                    f"csrs mstatus, x{r_temp2}   # MIE=1 -- fires immediately, still in M-mode",
                    "",
                    test_data.add_testcase(binname, coverpoint, covergroup),
                    "    nop",
                    "    nop",
                    "    nop",
                    "    nop",
                ]
            )
        else:
            lines.extend(
                [
                    f"LI(x{r_temp2}, {hex(MPIE_BIT)})",
                    f"csrs mstatus, x{r_temp2}   # MPIE=1 -> mret sets MIE=1 only after landing in {priv_mode}mode",
                    "",
                    test_data.add_testcase(binname, coverpoint, covergroup),
                    f"RVTEST_GOTO_LOWER_MODE {priv_mode}mode",
                    "    nop",
                    "    nop",
                    "    nop",
                    "    nop",
                    "RVTEST_GOTO_MMODE",
                ]
            )

        # Cleanup -- back in M-mode
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
            lines.extend([f"LI(x{r1}, 0x2)", f"csrc mip, x{r1}"])

        lines.extend(
            [
                f"LI(x{r_scratch}, {hex(LCOFIP_BIT)})",
                f"csrc mip, x{r_scratch}   # clear LCOFIP for next iteration",
                "csrw mie, zero",
            ]
        )

    test_data.int_regs.return_registers([r1, r_mtime, r_mtimecmp, r_temp, r_temp2, r_scratch])
    return lines


def generate_sscofpmf_suite(test_data: TestData, mode: str) -> list[TestChunk]:
    """Assemble the full Sscofpmf suite for ``mode`` ("Sm"/"S"/"U") as a test chunk."""
    tc = test_data.begin_test_chunk()
    tc.code.extend(_generate_xinh_inhibits_tests(test_data, mode))
    tc.code.extend(_generate_of_set_on_overflow_tests(test_data, mode))
    tc.code.extend(_generate_overflow_hw_only_tests(test_data, mode))
    tc.code.extend(_generate_scountovf_mcounteren_tests(test_data, mode))
    tc.code.extend(_generate_sscofpmf_access_tests(test_data, mode))
    tc.code.extend(_generate_lcofi_tests(test_data, mode))
    tc.code.extend(_generate_lcofip_priority_tests(test_data, mode))
    return [test_data.end_test_chunk()]
