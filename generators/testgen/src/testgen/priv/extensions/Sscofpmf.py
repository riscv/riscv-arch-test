##################################
# priv/extensions/Sscofpmf.py
# Written by: Ayesha Anwar, ayesha.anwaar2005@gmail.com
# Sscofpmf (HPM counter overflow/interrupt) test generators for the Sm, S and U groups.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Sscofpmf test generators. Shared test-case generators are called with priv_mode in {"M", "S", "U"}."""

from collections.abc import Callable

from testgen.asm.csr import csr_access_test
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.asm.tsbi import tsbi_call_or_direct
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

# Covergroup group (and test file name prefix) for each privilege mode
_GROUP = {"M": "Sm", "S": "S", "U": "U"}


def _cg(priv_mode: str) -> str:
    return f"Sscofpmf_{_GROUP[priv_mode]}_cg"


def lcofip_access(priv_mode: str, instr: Callable[[str], str]) -> list[str]:
    """Emit instr(csr) for the CSR that holds LCOFIP: mip in M, sip in S, and in U sip if S_SUPPORTED, else mip."""
    if priv_mode == "M":
        return [tsbi_call_or_direct(instr("mip"), priv_mode)]
    if priv_mode == "S":
        return [tsbi_call_or_direct(instr("sip"), priv_mode)]
    return [
        "#ifdef S_SUPPORTED",
        tsbi_call_or_direct(instr("sip"), priv_mode),
        "#else",
        tsbi_call_or_direct(instr("mip"), priv_mode),
        "#endif",
    ]


def clear_lcofip(r_tmp: int, priv_mode: str) -> list[str]:
    return [
        f"LI(x{r_tmp}, MIP_LCOFIP)",
        *lcofip_access(priv_mode, lambda csr: f"csrc {csr}, x{r_tmp}   # clear LCOFIP"),
    ]


def generate_lcofi_sip_tests(test_data: TestData, priv_mode: str) -> list[str]:
    """Sweep sip.LCOFIP x sie.LCOFIE with sstatus.SIE fixed (1 in S, 0 in U)."""
    ######################################
    covergroup = _cg(priv_mode)
    coverpoint = f"cp_lcofi_sip_{priv_mode.lower()}"
    ######################################

    mode = priv_mode.lower()
    sie_set = priv_mode == "S"
    r_val, r_temp = test_data.int_regs.get_registers(2)
    lines = [
        comment_banner(
            coverpoint,
            f"Interrupt pending and enable, mode = {priv_mode}.\n"
            "mideleg.LCOFI=1 (from the boot setup) and "
            f"sstatus.SIE={int(sie_set)} held fixed;\n"
            "sweep sip.LCOFIP x sie.LCOFIE.\n",
        ),
        "",
        tsbi_call_or_direct("csrw sie, zero      # disable all S-mode interrupts", priv_mode),
        tsbi_call_or_direct("csrw RVTEST_CSR_MHPMEVENT, zero", priv_mode),
        f"LI(x{r_val}, SSTATUS_SIE)",
        tsbi_call_or_direct(
            f"{'csrs' if sie_set else 'csrc'} sstatus, x{r_val}   # sstatus.SIE = {int(sie_set)} (fixed)", priv_mode
        ),
    ]

    for lcofip in [0, 1]:
        for lcofie in [0, 1]:
            binname = f"lcofi_{mode}_lcofip_{lcofip}_lcofie_{lcofie}"
            lines.extend(
                [
                    "",
                    f"# Testcase: sip.LCOFIP={lcofip}, sie.LCOFIE={lcofie}, mode={priv_mode}",
                    f"LI(x{r_val}, MIP_LCOFIP)",
                ]
            )
            if lcofip:
                lines.append(tsbi_call_or_direct(f"csrs sip, x{r_val}   # sip.LCOFIP = 1", priv_mode))
            else:
                lines.extend(
                    [
                        tsbi_call_or_direct("csrw RVTEST_CSR_MHPMCOUNTER, zero   # no overflow", priv_mode),
                        tsbi_call_or_direct(f"csrc sip, x{r_val}   # sip.LCOFIP = 0", priv_mode),
                    ]
                )

            lines.extend(
                [
                    f"LI(x{r_temp}, MIP_LCOFIP)",
                    test_data.add_testcase(binname, coverpoint, covergroup),
                    tsbi_call_or_direct(
                        f"{'csrs' if lcofie else 'csrc'} sie, x{r_temp}   # sie.LCOFIE = {lcofie}", priv_mode
                    ),
                    "",
                    f"RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})",
                    "",
                    tsbi_call_or_direct(f"csrc sip, x{r_temp}   # clear LCOFIP", priv_mode) if lcofip else "",
                    tsbi_call_or_direct("csrw sie, zero        # clear LCOFIE", priv_mode),
                ]
            )

    lines.extend(
        [
            "",
            f"LI(x{r_temp}, MIP_LCOFIP)",
            tsbi_call_or_direct(f"csrc sip, x{r_temp}      # clear LCOFIP", priv_mode),
            tsbi_call_or_direct(f"csrc sie, x{r_temp}      # clear LCOFIE", priv_mode),
            f"LI(x{r_val}, SSTATUS_SIE)",
            tsbi_call_or_direct(f"csrc sstatus, x{r_val}   # clear sstatus.SIE", priv_mode),
            tsbi_call_or_direct("csrw RVTEST_CSR_MHPMCOUNTER, zero", priv_mode),
            tsbi_call_or_direct("csrw RVTEST_CSR_MHPMEVENT, zero", priv_mode),
        ]
    )

    test_data.int_regs.return_registers([r_val, r_temp])
    return lines


# Every T-SBI call runs the M-mode handler, and a call from U is delegated through S
# first, so counting must be inhibited in every mode above the one under test or the
# counter would also count the round trip instead of just the workload.
HIGHER_MODE_INHIBITS = {"M": 0, "S": 1 << 62, "U": (1 << 62) | (1 << 61)}
HIGHER_MODE_INHIBITS_32 = {mode: bits >> 32 for mode, bits in HIGHER_MODE_INHIBITS.items()}
HIGHER_MODE_PATTERN = {mode: bits >> 58 for mode, bits in HIGHER_MODE_INHIBITS.items()}

EVENT_VAL_HI = "(((RVMODEL_MHPMEVENT_VAL) >> 32) & 0xFFFFFF)"


def counted_since_preset(reg: int, r_preset: int) -> list[str]:
    """Reduce x{reg} to 1 if the counter moved off the preset in x{r_preset}, else 0."""
    return [
        f"xor x{reg}, x{reg}, x{r_preset}   # 0 iff the counter still holds the preset",
        f"snez x{reg}, x{reg}               # x{reg} = counted at least one event",
    ]


def write_event_pattern(r_val: int, r_hval: int, inhibit_pattern: int, priv_mode: str) -> list[str]:
    """Write RVMODEL_MHPMEVENT_VAL with the given MINH/SINH/UINH/VSINH/VUINH pattern and OF=0."""
    return [
        "#if __riscv_xlen == 32",
        f"LI(x{r_val}, RVMODEL_MHPMEVENT_VAL)",
        tsbi_call_or_direct(f"csrw RVTEST_CSR_MHPMEVENT, x{r_val}", priv_mode),
        f"LI(x{r_hval}, {EVENT_VAL_HI} | ({inhibit_pattern} << 26))   # 58-32 = 26",
        tsbi_call_or_direct(f"csrw RVTEST_CSR_MHPMEVENTH, x{r_hval}", priv_mode),
        "#else",
        f"LI(x{r_val}, RVMODEL_MHPMEVENT_VAL | ({inhibit_pattern} << 58))   # OF starts at 0",
        tsbi_call_or_direct(f"csrw RVTEST_CSR_MHPMEVENT, x{r_val}", priv_mode),
        "#endif",
    ]


# MINH, SINH, UINH, VSINH and VUINH: nothing counts in any mode.
INHIBIT_ALL_PATTERN = 0b11111


def write_counter_all_ones(r_val: int, r_hval: int, r_temp: int, priv_mode: str) -> list[str]:
    """Preset the counter to all 1s with counting inhibited in every mode. An event that
    counts every instruction would otherwise also count the preset writes: on RV32 the
    low half would wrap before the high half is written, and the counter would never
    overflow. The caller enables counting afterwards with write_event_pattern()."""
    return [
        *write_event_pattern(r_val, r_hval, INHIBIT_ALL_PATTERN, priv_mode),
        f"LI(x{r_temp}, -1)",
        tsbi_call_or_direct(f"csrw RVTEST_CSR_MHPMCOUNTER, x{r_temp}   # all 1s -> next count overflows", priv_mode),
        "#if __riscv_xlen == 32",
        tsbi_call_or_direct(f"csrw RVTEST_CSR_MHPMCOUNTERH, x{r_temp}   # high half must also be all 1s", priv_mode),
        "#endif",
    ]


def prime_counter_overflow(r_val: int, r_hval: int, r_temp: int, r_addr: int, priv_mode: str) -> list[str]:
    """Overflow the counter in the mode under test, which sets OF and raises LCOFIP."""
    return [
        *write_counter_all_ones(r_val, r_hval, r_temp, priv_mode),
        *write_event_pattern(r_val, r_hval, HIGHER_MODE_PATTERN[priv_mode], priv_mode),
        f"LA(x{r_addr}, scratch)",
        f"RVMODEL_MHPMEVENT_CODE(x{r_addr}, x{r_val})",
    ]


def combo_counts(priv_mode: str, r_temp: int, r_hval: int, test_data: TestData) -> list[str]:
    """In M-mode, run the workload so each combination checks that only MINH decides
    whether M-mode events count. Below M the T-SBI round trip would be counted, so the
    S and U suites check counting only in the single-bit toggles."""
    if priv_mode != "M":
        return []
    return [
        "csrw RVTEST_CSR_MHPMCOUNTER, zero",
        f"LA(x{r_temp}, scratch)",
        f"RVMODEL_MHPMEVENT_CODE(x{r_temp}, x{r_hval})",
        f"csrr x{r_temp}, RVTEST_CSR_MHPMCOUNTER",
        f"snez x{r_temp}, x{r_temp}   # counted iff MINH = 0",
        f"{write_sigupd(r_temp, test_data)}",
    ]


def _generate_xinh_inhibits_tests(
    test_data: TestData, priv_mode: str, combos: range = range(32), toggles: bool = True
) -> list[str]:
    """xINH toggles (when ``toggles``) and the MINH/SINH/UINH/VSINH/VUINH combinations in ``combos``."""

    covergroup = _cg(priv_mode)
    inh_prefix = priv_mode.lower()
    coverpoint = f"cp_{inh_prefix}inh_inhibits_{inh_prefix}mode"
    inh_bit_pos = {"M": 62, "S": 61, "U": 60}[priv_mode]
    inh_bit_pos_32 = inh_bit_pos - 32

    r_val, r_temp = test_data.int_regs.get_registers(2)

    higher_inhibits = HIGHER_MODE_INHIBITS[priv_mode]
    higher_inhibits_32 = HIGHER_MODE_INHIBITS_32[priv_mode]

    lines = [
        comment_banner(
            coverpoint,
            f"{priv_mode}INH bit (mhpmevent[{inh_bit_pos}]) inhibits counting in {priv_mode}-mode.\n"
            "Counting stays inhibited in the modes above the one under test, so the counter\n"
            "only ever reflects the workload and never the T-SBI round trip that reaches the\n"
            "M-level counter CSRs.",
        ),
        "",
        tsbi_call_or_direct("csrw mie, zero   # disable interrupts before toggle/sweep", priv_mode),
        "",
    ]

    # Toggle the xINH bit and test its effect
    for inh_val in [0, 1] if toggles else []:
        binname = f"{inh_prefix}inh_{inh_val}_{priv_mode.lower()}"
        lines.extend(
            [
                f"# Testcase: {inh_prefix}inh = {inh_val}",
                "#if __riscv_xlen == 32",
                f"LI(x{r_val}, RVMODEL_MHPMEVENT_VAL)",
                f"{tsbi_call_or_direct(f'csrw RVTEST_CSR_MHPMEVENT, x{r_val}', priv_mode)}",
                f"LI(x{r_val}, {EVENT_VAL_HI} | {hex(higher_inhibits_32 | (inh_val << inh_bit_pos_32))})",
                f"{tsbi_call_or_direct(f'csrw RVTEST_CSR_MHPMEVENTH, x{r_val}', priv_mode)}",
                "#else",
                f"LI(x{r_val}, RVMODEL_MHPMEVENT_VAL | {hex(higher_inhibits | (inh_val << inh_bit_pos))})",
                f"{tsbi_call_or_direct(f'csrw RVTEST_CSR_MHPMEVENT, x{r_val}', priv_mode)}",
                "#endif",
                f"{tsbi_call_or_direct('csrw RVTEST_CSR_MHPMCOUNTER, zero', priv_mode)}",
                "",
                f"LA(x{r_temp}, scratch)",
                f"RVMODEL_MHPMEVENT_CODE(x{r_temp}, x{r_val})",
                "",
                f"{test_data.add_testcase(binname, coverpoint, covergroup)}",
                f"{tsbi_call_or_direct(f'csrr x{r_temp}, RVTEST_CSR_MHPMCOUNTER', priv_mode)}",
                f"snez x{r_temp}, x{r_temp}",
                f"{write_sigupd(r_temp, test_data)}",
                "",
            ]
        )

    lines.extend(
        [
            f"LI(x{r_val}, RVMODEL_MHPMEVENT_VAL)",
            f"{tsbi_call_or_direct(f'csrw RVTEST_CSR_MHPMEVENT, x{r_val}', priv_mode)}",
            "#if __riscv_xlen == 32",
            f"LI(x{r_val}, {EVENT_VAL_HI})",
            f"{tsbi_call_or_direct(f'csrw RVTEST_CSR_MHPMEVENTH, x{r_val}', priv_mode)}",
            "#endif",
            "",
        ]
    )

    r_hval = test_data.int_regs.get_register()

    for combo in combos:
        binname = f"xinh_combo_{combo:05b}_{priv_mode.lower()}"
        lines.extend(
            [
                "#if __riscv_xlen == 32",
                f"LI(x{r_hval}, {EVENT_VAL_HI} | ({combo} << 26))",
                f"{tsbi_call_or_direct(f'csrw RVTEST_CSR_MHPMEVENTH, x{r_hval}', priv_mode)}",
                "#else",
                f"LI(x{r_val}, RVMODEL_MHPMEVENT_VAL | ({combo} << 58))",
                f"{tsbi_call_or_direct(f'csrw RVTEST_CSR_MHPMEVENT, x{r_val}', priv_mode)}",
                "#endif",
                "",
                f"{test_data.add_testcase(binname, coverpoint, covergroup)}",
                "#if __riscv_xlen == 32",
                f"{tsbi_call_or_direct(f'csrr x{r_temp}, RVTEST_CSR_MHPMEVENTH', priv_mode)}",
                "#else",
                f"{tsbi_call_or_direct(f'csrr x{r_temp}, RVTEST_CSR_MHPMEVENT', priv_mode)}",
                "#endif",
                f"{write_sigupd(r_temp, test_data)}",
                *combo_counts(priv_mode, r_temp, r_hval, test_data),
                "",
            ]
        )

    lines.extend(
        [
            f"{tsbi_call_or_direct('csrw RVTEST_CSR_MHPMEVENT, zero', priv_mode)}",
            "#if __riscv_xlen == 32",
            f"{tsbi_call_or_direct('csrw RVTEST_CSR_MHPMEVENTH, zero', priv_mode)}",
            "#endif",
            f"{tsbi_call_or_direct('csrw RVTEST_CSR_MHPMCOUNTER, zero', priv_mode)}",
            "",
        ]
    )
    test_data.int_regs.return_registers([r_hval])
    test_data.int_regs.return_registers([r_val, r_temp])
    return lines


# Below M every pattern inhibits the modes above the one under test, so the T-SBI trap handler
# never counts.
_INHIBIT_PATTERNS = {
    "M": [0b00000, 0b11100, 0b10000, 0b01000, 0b00100],
    "S": [0b10000, 0b10100, 0b11000, 0b11100],
    "U": [0b11000, 0b11100],
}


def read_event_config_bits(r_temp: int, priv_mode: str) -> list[str]:
    """Read OF and the 5-bit inhibit field into x{r_temp}, masked to those bits."""
    return [
        "#if __riscv_xlen == 32",
        tsbi_call_or_direct(f"csrr x{r_temp}, RVTEST_CSR_MHPMEVENTH   # sample point for mhpmevent_of", priv_mode),
        f"srli x{r_temp}, x{r_temp}, 26   # keep only OF + the 5-bit inhibit field (bits 31:26)",
        f"slli x{r_temp}, x{r_temp}, 26",
        "#else",
        tsbi_call_or_direct(f"csrr x{r_temp}, RVTEST_CSR_MHPMEVENT   # sample point for mhpmevent_of", priv_mode),
        f"srli x{r_temp}, x{r_temp}, 58   # keep only OF + the 5-bit inhibit field (bits 63:58)",
        f"slli x{r_temp}, x{r_temp}, 58",
        "#endif",
    ]


def _generate_of_set_on_overflow_tests(test_data: TestData, priv_mode: str) -> list[str]:
    ######################################
    covergroup = _cg(priv_mode)
    coverpoint = "cp_of_set_on_overflow"
    ######################################

    r_val, r_temp, r_lcofip, r_addr, r_hval, r_preset = test_data.int_regs.get_registers(6)

    pending_csr, enable_csr = ("sip", "sie") if priv_mode == "S" else ("mip", "mie")
    lcofip_read = lcofip_access(priv_mode, lambda csr: f"csrr x{r_lcofip}, {csr}   # sample point for lcofip")

    lines = [
        comment_banner(
            coverpoint,
            "OF bit is set when hpmcounter overflows (OF starts at 0, "
            "hardware must set it on the 0 -> 1 overflow edge).\n",
        ),
        "",
    ]

    for inhibit_pattern in _INHIBIT_PATTERNS[priv_mode]:
        binname = f"of_overflow_{priv_mode.lower()}_ei_{inhibit_pattern:05b}"

        lines.extend(
            [
                "",
                f"# Testcase: mode = {priv_mode}, inhibit pattern = {inhibit_pattern:05b}, OF initial = 0",
            ]
        )

        if priv_mode == "U":
            lines.extend(
                [
                    "#ifdef S_SUPPORTED",
                    tsbi_call_or_direct("csrw sip, zero   # clear LCOFIP", priv_mode),
                    tsbi_call_or_direct("csrw sie, zero   # disable interrupts (clear LCOFIE)", priv_mode),
                    "#else",
                    tsbi_call_or_direct("csrw mip, zero   # clear LCOFIP", priv_mode),
                    tsbi_call_or_direct("csrw mie, zero   # disable interrupts (clear LCOFIE)", priv_mode),
                    "#endif",
                ]
            )
        else:
            lines.extend(
                [
                    tsbi_call_or_direct(f"csrw {pending_csr}, zero   # clear LCOFIP", priv_mode),
                    tsbi_call_or_direct(f"csrw {enable_csr}, zero   # disable interrupts (clear LCOFIE)", priv_mode),
                ]
            )

        lines.extend(
            [
                *write_counter_all_ones(r_val, r_hval, r_temp, priv_mode),
                tsbi_call_or_direct(f"csrr x{r_preset}, RVTEST_CSR_MHPMCOUNTER   # preset as read back", priv_mode),
                *write_event_pattern(r_val, r_hval, inhibit_pattern, priv_mode),
                "",
                f"LA(x{r_addr}, scratch)",
                "# One counted event is enough to wrap the all-1s counter and set OF",
                f"RVMODEL_MHPMEVENT_CODE(x{r_addr}, x{r_val})",
                "",
                test_data.add_testcase(binname, coverpoint, covergroup),
                *read_event_config_bits(r_temp, priv_mode),
                write_sigupd(r_temp, test_data),
                tsbi_call_or_direct(
                    f"csrr x{r_temp}, RVTEST_CSR_MHPMCOUNTER   # sample point: did the counter move off the preset?",
                    priv_mode,
                ),
                *counted_since_preset(r_temp, r_preset),
                write_sigupd(r_temp, test_data),
                "",
                f"RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})   # wait for RVMODEL_INTERRUPT_LATENCY",
                *lcofip_read,
                write_sigupd(r_lcofip, test_data),
            ]
        )

    # OF already 1: the overflow must leave OF set and must not set LCOFIP.
    already_set_coverpoint = "cp_of_already_set"
    lines.extend(
        [
            "",
            f"# Testcase: mode = {priv_mode}, inhibit pattern = {HIGHER_MODE_PATTERN[priv_mode]:05b}, OF initial = 1",
            tsbi_call_or_direct("csrw mie, zero   # disable interrupts", priv_mode),
            *write_counter_all_ones(r_val, r_hval, r_temp, priv_mode),
            tsbi_call_or_direct(f"csrr x{r_preset}, RVTEST_CSR_MHPMCOUNTER   # preset as read back", priv_mode),
            *clear_lcofip(r_temp, priv_mode),
            "#if __riscv_xlen == 32",
            f"LI(x{r_val}, RVMODEL_MHPMEVENT_VAL)",
            tsbi_call_or_direct(f"csrw RVTEST_CSR_MHPMEVENT, x{r_val}", priv_mode),
            f"LI(x{r_hval}, {EVENT_VAL_HI} | {hex((1 << 31) | HIGHER_MODE_INHIBITS_32[priv_mode])})   # OF = 1",
            tsbi_call_or_direct(f"csrw RVTEST_CSR_MHPMEVENTH, x{r_hval}", priv_mode),
            "#else",
            f"LI(x{r_val}, RVMODEL_MHPMEVENT_VAL | {hex((1 << 63) | HIGHER_MODE_INHIBITS[priv_mode])})   # OF = 1",
            tsbi_call_or_direct(f"csrw RVTEST_CSR_MHPMEVENT, x{r_val}", priv_mode),
            "#endif",
            "# Counting starts here, after LCOFIP was cleared, so a wrongly raised LCOFIP stays visible",
            "",
            f"LA(x{r_addr}, scratch)",
            f"RVMODEL_MHPMEVENT_CODE(x{r_addr}, x{r_val})",
            f"RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})   # wait for RVMODEL_INTERRUPT_LATENCY",
            "",
            test_data.add_testcase(
                f"of_overflow_{priv_mode.lower()}_of_already_set", already_set_coverpoint, covergroup
            ),
            *read_event_config_bits(r_temp, priv_mode),
            write_sigupd(r_temp, test_data),
            tsbi_call_or_direct(
                f"csrr x{r_temp}, RVTEST_CSR_MHPMCOUNTER   # sample point: did the counter move off the preset?",
                priv_mode,
            ),
            *counted_since_preset(r_temp, r_preset),
            write_sigupd(r_temp, test_data),
            *lcofip_read,
            f"srli x{r_lcofip}, x{r_lcofip}, 13",
            f"andi x{r_lcofip}, x{r_lcofip}, 1   # isolate LCOFIP",
            write_sigupd(r_lcofip, test_data),
        ]
    )

    test_data.int_regs.return_registers([r_val, r_temp, r_lcofip, r_addr, r_hval, r_preset])

    return lines


def _generate_overflow_hw_only_tests(test_data: TestData, priv_mode: str) -> list[str]:
    ######################################
    covergroup = _cg(priv_mode)
    coverpoint = "cp_overflow_hw_only"
    ######################################

    r_val, r_of = test_data.int_regs.get_registers(2)

    lines = [
        comment_banner(
            coverpoint,
            "A software write of RVTEST_CSR_MHPMCOUNTER, however extreme, must never set OF --\n"
            f"only a hardware counter increment through overflow may. mode = {priv_mode}.",
        ),
        "",
        tsbi_call_or_direct("csrw mie, zero   # disable interrupts", priv_mode),
        tsbi_call_or_direct("csrw RVTEST_CSR_MHPMEVENT, zero", priv_mode),
        "#if __riscv_xlen == 32",
        tsbi_call_or_direct("csrw RVTEST_CSR_MHPMEVENTH, zero   # clear OF and xINH left by earlier tests", priv_mode),
        "#endif",
        # A real overflow in the previous tests leaves LCOFIP pending on a counting hart.
        *clear_lcofip(r_val, priv_mode),
        "",
    ]

    for step_name, load_val in [("all_1s", -1), ("all_0s", 0)]:
        binname = f"overflow_hw_only_{priv_mode.lower()}_{step_name}"
        lines.extend(
            [
                f"# Testcase: software write RVTEST_CSR_MHPMCOUNTER = {step_name}, mode = {priv_mode}",
                f"LI(x{r_val}, {load_val})",
                tsbi_call_or_direct(f"csrw RVTEST_CSR_MHPMCOUNTER, x{r_val}", priv_mode),
                "",
                test_data.add_testcase(binname, coverpoint, covergroup),
                "#if __riscv_xlen == 32",
                tsbi_call_or_direct(
                    f"csrr x{r_of}, RVTEST_CSR_MHPMEVENTH   # sample point -- OF must read 0", priv_mode
                ),
                f"srli x{r_of}, x{r_of}, 31   # OF (bit 31 of the H-half) -> bit 0",
                "#else",
                tsbi_call_or_direct(
                    f"csrr x{r_of}, RVTEST_CSR_MHPMEVENT   # sample point -- OF must read 0", priv_mode
                ),
                f"srli x{r_of}, x{r_of}, 63   # OF (bit 63) -> bit 0",
                "#endif",
                write_sigupd(r_of, test_data),
                "",
            ]
        )

    test_data.int_regs.return_registers([r_val, r_of])
    return lines


def set_of(r_val: int, priv_mode: str, op: str, desc: str) -> list[str]:
    return [
        "#if __riscv_xlen == 32",
        f"LI(x{r_val}, {hex(1 << 31)})",
        tsbi_call_or_direct(f"{op} RVTEST_CSR_MHPMEVENTH, x{r_val}   # {desc}", priv_mode),
        "#else",
        f"LI(x{r_val}, {hex(1 << 63)})",
        tsbi_call_or_direct(f"{op} RVTEST_CSR_MHPMEVENT, x{r_val}   # {desc}", priv_mode),
        "#endif",
    ]


def check_lcofip(r_temp: int, priv_mode: str, test_data: TestData, expect_desc: str) -> list[str]:
    return [
        *lcofip_access(priv_mode, lambda csr: f"csrr x{r_temp}, {csr}   # sample point -- LCOFIP {expect_desc}"),
        f"srli x{r_temp}, x{r_temp}, 13",
        f"andi x{r_temp}, x{r_temp}, 1   # isolate LCOFIP",
        write_sigupd(r_temp, test_data),
    ]


def _generate_lcofip_hw_only_tests(test_data: TestData, priv_mode: str) -> list[str]:
    ######################################
    covergroup = _cg(priv_mode)
    coverpoint = "cp_lcofip_hw_only"
    ######################################

    r_val, r_temp = test_data.int_regs.get_registers(2)

    lines = [
        comment_banner(
            coverpoint,
            (
                "OF being set by software alone must never make LCOFIP pending --\n"
                "only a real hardware counter-register increment through overflow\n"
                "may set OF (and therefore LCOFIP). No pending/enable sweep here:\n"
                "this coverpoint tests the absence of a software-only path to LCOFIP.\n"
                f"mode = {priv_mode}."
            ),
        ),
        "",
        tsbi_call_or_direct("csrw mie, zero   # disable interrupts", priv_mode),
        # A real overflow earlier leaves LCOFIP pending on a counting hart.
        *clear_lcofip(r_temp, priv_mode),
        "",
        "# Testcase: software-set OF bit directly (no HW increment)",
        *set_of(r_val, priv_mode, "csrs", "software-set OF bit"),
        "",
        test_data.add_testcase(f"lcofip_hw_only_{priv_mode.lower()}_set_of", coverpoint, covergroup),
        f"RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})   # wait for RVMODEL_INTERRUPT_LATENCY",
        *check_lcofip(r_temp, priv_mode, test_data, "must read 0"),
        "",
        "# Testcase: software-clear OF bit directly (no HW increment)",
        *set_of(r_val, priv_mode, "csrc", "software-clear OF bit"),
        "",
        test_data.add_testcase(f"lcofip_hw_only_{priv_mode.lower()}_clear_of", coverpoint, covergroup),
        f"RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})   # wait for RVMODEL_INTERRUPT_LATENCY",
        *check_lcofip(r_temp, priv_mode, test_data, "must still read 0"),
    ]

    test_data.int_regs.return_registers([r_val, r_temp])
    return lines


NUM_OF_BITS = 29  # mhpmevent3..31


def of_bit_writes(
    r_of_bit: int, changes: list[tuple[int, bool]], mode: str, csr_suffix: str, of_bit: int, desc: str
) -> list[str]:
    """Generate T-SBI calls to set or clear OF bits in mhpmevent3..31 based on changes."""
    lines = [f"LI(x{r_of_bit}, {hex(of_bit)})   # OF bit ({desc})"]
    for i, of in changes:
        op, action = ("csrs", "set") if of else ("csrc", "clear")
        lines.append(tsbi_call_or_direct(f"{op} CSR_MHPMEVENT{i + 3}{csr_suffix}, x{r_of_bit}   # {action} OF", mode))
    return lines


def write_of_pattern(
    r_of_bit: int, pattern_name: str, of_bit_fn: Callable[[int], int], mode: str, of_state: list[int]
) -> list[str]:
    """Set or clear OF in mhpmevent3..31 per of_bit_fn(counter - 3). of_state holds the OF value
    last written to each counter and is updated in place, so only the counters
    whose OF changes are written. Below M each write is a T-SBI call."""
    new_state = [of_bit_fn(i) for i in range(NUM_OF_BITS)]
    changes = [(i, bool(of)) for i, (of, old) in enumerate(zip(new_state, of_state)) if of != old]
    of_state[:] = new_state

    return [
        f"# --- Write OF pattern: {pattern_name} across mhpmevent3..31 ---",
        "#if __riscv_xlen == 32",
        *of_bit_writes(r_of_bit, changes, mode, "H", 1 << 31, "bit 31 of mhpmeventh, RV32"),
        "#else",
        *of_bit_writes(r_of_bit, changes, mode, "", 1 << 63, "bit 63 of mhpmevent, RV64"),
        "#endif",
        "",
    ]


MCOUNTEREN_OF_PATTERNS: dict[str, Callable[[int], int]] = {
    "all_ones": lambda _: 1,
    "checker_even": lambda i: 1 if i % 2 == 0 else 0,
    "checker_odd": lambda i: 1 if i % 2 == 1 else 0,
}


def _generate_scountovf_mcounteren_tests(test_data: TestData, mode: str, of_names: list[str]) -> list[str]:
    ######################################
    covergroup = _cg(mode)
    coverpoint = "cp_scountovf_mcounteren"
    ######################################

    lines = [
        comment_banner(
            coverpoint,
            f"scountovf masked by mcounteren -- mode = {mode}.\n"
            f"Write OF patterns ({'/'.join(of_names)}) across\n"
            "mhpmevent3..31.OF, walk mcounteren, read scountovf.",
        ),
        "",
    ]

    # rvtest_setup.h clears mhpmevent3..31 and the RV32 high halves at boot, so OF starts at 0.
    of_state = [0] * NUM_OF_BITS
    for of_name in of_names:
        of_bit_fn = MCOUNTEREN_OF_PATTERNS[of_name]
        r_of_bit = test_data.int_regs.get_register()
        lines.extend(write_of_pattern(r_of_bit, of_name, of_bit_fn, mode, of_state))
        test_data.int_regs.return_registers([r_of_bit])

        walk_coverpoint = f"{coverpoint}_{of_name}_{mode.lower()}"

        r_mcounteren, r_scountovf = test_data.int_regs.get_registers(2)

        for state_name, val in [("all_zeros", 0), ("all_ones", 0xFFFFFFF8)]:
            binname = f"mcounteren_{state_name}"
            lines.extend(
                [
                    f"LI(x{r_mcounteren}, {hex(val)})",
                    f"{tsbi_call_or_direct(f'csrw mcounteren, x{r_mcounteren}', mode)}",
                    f"{test_data.add_testcase(binname, walk_coverpoint, covergroup)}",
                    f"{tsbi_call_or_direct(f'csrr x{r_scountovf}, scountovf   # sample point', mode)}",
                    f"{write_sigupd(r_scountovf, test_data)}",
                    "",
                ]
            )

        for bit in range(3, 32):
            binname = f"mcounteren_walk_bit_{bit}"
            lines.extend(
                [
                    f"LI(x{r_mcounteren}, {1 << bit})",
                    f"{tsbi_call_or_direct(f'csrw mcounteren, x{r_mcounteren}', mode)}",
                    f"{test_data.add_testcase(binname, walk_coverpoint, covergroup)}",
                    f"{tsbi_call_or_direct(f'csrr x{r_scountovf}, scountovf   # sample point', mode)}",
                    f"{write_sigupd(r_scountovf, test_data)}",
                    "",
                ]
            )

        lines.append(f"{tsbi_call_or_direct('csrw mcounteren, zero', mode)}")
        lines.append("")
        test_data.int_regs.return_registers([r_mcounteren, r_scountovf])

    return lines


def _generate_sscofpmf_access_tests(test_data: TestData, mode: str) -> list[str]:
    ######################################
    covergroup = _cg(mode)
    coverpoint = "cp_sscofpmf_access"
    ######################################

    lines = [
        comment_banner(
            coverpoint,
            f"Attempt to read, write 1s, write 0s, set, clear from mode = {mode}:\n"
            "scountovf\nIf RV32: mhpmeventh3...31",
        ),
    ]
    lines.extend(csr_access_test(test_data, ("scountovf", None), covergroup, coverpoint))

    if mode == "M":  # mhpmeventh3..31 sweep is M-mode only
        lines.append("#if __riscv_xlen == 32")
        for n in range(3, 32):
            lines.extend(csr_access_test(test_data, (f"CSR_MHPMEVENT{n}H", None), covergroup, coverpoint))
        lines.append("#endif")

    return lines


def _walking_one(walk_idx: int) -> Callable[[int], int]:
    return lambda i: 1 if i == walk_idx else 0


# all_0s runs first so each walking pattern after it changes at most two OF bits.
SHADOW_PATTERNS: dict[str, list[tuple[str, Callable[[int], int]]]] = {
    "shadow_walk_lo": [("all_0s", lambda i: 0), *((f"walking1_{w}", _walking_one(w)) for w in range(15))],
    "shadow_walk_hi": [(f"walking1_{w}", _walking_one(w)) for w in range(15, NUM_OF_BITS)],
    "shadow_all_1s": [("all_1s", lambda i: 1)],
}


def _generate_scountovf_shadow_tests(
    test_data: TestData,
    priv_mode: str,
    patterns: list[tuple[str, Callable[[int], int]]],
) -> list[str]:
    if priv_mode == "U":
        return []

    ######################################
    covergroup = _cg(priv_mode)
    coverpoint = "cp_scountovf_shadow"
    ######################################

    # rvtest_setup.h clears mhpmevent3..31 and the RV32 high halves at boot, so OF starts at 0.
    of_state = [0] * NUM_OF_BITS
    r_mcounteren = test_data.int_regs.get_register()
    lines = [
        comment_banner(
            coverpoint,
            f"scountovf shadows OF bits of mhpmevent3:31, mode = {priv_mode}.\n"
            "mcounteren = all 1s (fixed for this coverpoint). Write patterns to\n"
            "mhpmevent3...31.OF: all 0s, walking 1s, all 1s. Read scountovf.\n",
        ),
        "",
        f"LI(x{r_mcounteren}, -1)",
        f"{tsbi_call_or_direct(f'csrw mcounteren, x{r_mcounteren}   # mcounteren = all 1s (fixed for this coverpoint)', priv_mode)}",
        "",
    ]
    test_data.int_regs.return_registers([r_mcounteren])

    def emit_pattern(pattern_name: str, of_bit_fn: Callable[[int], int]) -> None:
        r_of_bit, r_scountovf = test_data.int_regs.get_registers(2)
        binname = f"scountovf_shadow_{priv_mode.lower()}_{pattern_name}"
        lines.extend(
            [
                *write_of_pattern(r_of_bit, pattern_name, of_bit_fn, priv_mode, of_state),
                f"{test_data.add_testcase(binname, coverpoint, covergroup)}",
                f"{tsbi_call_or_direct(f'csrr x{r_scountovf}, scountovf   # sample point -- must match OF pattern', priv_mode)}",
                f"{write_sigupd(r_scountovf, test_data)}",
                "",
            ]
        )
        test_data.int_regs.return_registers([r_of_bit, r_scountovf])

    for pattern_name, of_bit_fn in patterns:
        emit_pattern(pattern_name, of_bit_fn)

    return lines


def generate_sscofpmf_suite(test_data: TestData, mode: str) -> list[TestChunk]:
    """Assemble the shared Sscofpmf tests for ``mode`` ("M"/"S"/"U")."""
    test_chunks: list[TestChunk] = []

    tc = test_data.begin_test_chunk(f"{_GROUP[mode]}_inhibit_lo")
    tc.code.extend(_generate_xinh_inhibits_tests(test_data, mode, combos=range(16)))
    test_chunks.append(test_data.end_test_chunk())

    tc = test_data.begin_test_chunk(f"{_GROUP[mode]}_inhibit_hi")
    tc.code.extend(_generate_xinh_inhibits_tests(test_data, mode, combos=range(16, 32), toggles=False))
    test_chunks.append(test_data.end_test_chunk())

    tc = test_data.begin_test_chunk(f"{_GROUP[mode]}_overflow")
    tc.code.extend(_generate_of_set_on_overflow_tests(test_data, mode))
    tc.code.extend(_generate_overflow_hw_only_tests(test_data, mode))
    tc.code.extend(_generate_lcofip_hw_only_tests(test_data, mode))
    test_chunks.append(test_data.end_test_chunk())

    if mode == "U":  # scountovf is not accessible from U, so the scountovf tests are S-only
        return test_chunks

    for of_name in MCOUNTEREN_OF_PATTERNS:
        tc = test_data.begin_test_chunk(f"{_GROUP[mode]}_mcounteren_{of_name}")
        tc.code.extend(_generate_scountovf_mcounteren_tests(test_data, mode, [of_name]))
        test_chunks.append(test_data.end_test_chunk())

    tc = test_data.begin_test_chunk(f"{_GROUP[mode]}_access")
    tc.code.extend(_generate_sscofpmf_access_tests(test_data, mode))
    test_chunks.append(test_data.end_test_chunk())

    for split_name, patterns in SHADOW_PATTERNS.items():
        tc = test_data.begin_test_chunk(f"{_GROUP[mode]}_{split_name}")
        tc.code.extend(_generate_scountovf_shadow_tests(test_data, mode, patterns))
        test_chunks.append(test_data.end_test_chunk())
    return test_chunks


def _generate_lcofi_m_tests(test_data: TestData) -> list[str]:
    ######################################
    covergroup = _cg("M")
    coverpoint = "cp_lcofi_m"
    ######################################

    r_val, r_temp, r_idle = test_data.int_regs.get_registers(3)

    lines = [
        comment_banner(
            coverpoint,
            "Interrupt pending and enable, mode = M.\n"
            "mstatus.MIE=1, mstatus.SIE=1 held fixed per testplan; sweep is\n"
            "mip.LCOFIP x mie.LCOFIE x mideleg.LCOFI.\n",
        ),
        "",
        "# === M-MODE SETUP ===",
        "csrw mip, zero      # clear all pending (sip may not exist in this suite)",
        "csrw mie, zero      # disable all interrupts",
        "csrw RVTEST_CSR_MHPMEVENT, zero",
        f"LI(x{r_val}, MSTATUS_MIE)",
        f"csrs mstatus, x{r_val}   # mstatus.MIE = 1 (fixed)",
        f"LI(x{r_val}, SSTATUS_SIE)",
        f"csrs mstatus, x{r_val}   # mstatus.SIE = 1 (fixed)",
    ]

    for lcofip in [0, 1]:
        for lcofie in [0, 1]:
            for mideleg_bit in [0, 1]:
                binname = f"lcofi_m_lcofip_{lcofip}_lcofie_{lcofie}_mideleg_{mideleg_bit}"
                lines.extend(
                    [
                        "",
                        (f"# Testcase: mip.LCOFIP={lcofip}, mie.LCOFIE={lcofie}, mideleg.LCOFI={mideleg_bit}, mode=M"),
                    ]
                )

                if lcofip:
                    lines.extend(
                        [
                            f"LI(x{r_val}, MIP_LCOFIP)",
                            f"csrs mip, x{r_val}   # set mip.LCOFIP directly",
                        ]
                    )
                else:
                    lines.append("csrw RVTEST_CSR_MHPMCOUNTER, zero   # keep counter clear -- no overflow")

                lines.extend(
                    [
                        f"LI(x{r_temp}, MIP_LCOFIP)",
                        f"{'csrs' if mideleg_bit else 'csrc'} mideleg, x{r_temp}   # mideleg.LCOFI = {mideleg_bit}",
                        f"{'csrs' if lcofie else 'csrc'} mie, x{r_temp}   # mie.LCOFIE = {lcofie}",
                        "",
                        test_data.add_testcase(binname, coverpoint, covergroup),
                        "    # Stays in M-mode throughout. With mideleg.LCOFI=1, LCOFI is an",
                        "    # S-level interrupt and is never taken in M-mode, whatever mstatus.MIE",
                        "    # is. So the trap fires during the idle window below only if",
                        "    # LCOFIP=1, LCOFIE=1 and mideleg.LCOFI=0; else it falls through once",
                        "    # the countdown expires.",
                        f"RVTEST_IDLE_FOR_INTERRUPT(x{r_idle})",
                        "",
                        f"csrc mip, x{r_temp}   # clear LCOFIP for next iteration (if it latched)" if lcofip else "",
                        "csrw mie, zero        # disable LCOFIE before next iteration",
                    ]
                )

    lines.extend(
        [
            "",
            "# === M-MODE CLEANUP ===",
            f"LI(x{r_temp}, MIP_LCOFIP)",
            f"csrc mip, x{r_temp}      # clear LCOFIP",
            f"csrc mie, x{r_temp}      # clear LCOFIE",
            f"csrc mideleg, x{r_temp}  # clear mideleg.LCOFI",
            f"LI(x{r_val}, MSTATUS_MIE | MSTATUS_SIE)",
            f"csrc mstatus, x{r_val}   # clear mstatus.MIE and mstatus.SIE",
            "csrw RVTEST_CSR_MHPMCOUNTER, zero",
            "csrw RVTEST_CSR_MHPMEVENT, zero",
        ]
    )

    test_data.int_regs.return_registers([r_val, r_temp, r_idle])
    return lines


def _generate_lcofip_priority_sm_tests(test_data: TestData) -> list[str]:
    ######################################
    covergroup = _cg("M")
    coverpoint = "cp_lcofip_priority_m"
    ######################################

    r_val, r_temp, r_temp2, r_addr = test_data.int_regs.get_registers(4)

    lines = [
        comment_banner(
            coverpoint,
            "LCOFI priority with MEIP, MTIP, MSIP, or no other pending interrupt.\n"
            "LCOFIP is raised by a real hpmcounter overflow through RVMODEL_MHPMEVENT_CODE.\n"
            "Each case holds with mie = all 0s (nothing fires), then with mie = all 1s:\n"
            "the competing interrupt fires first and LCOFI only after it.",
        ),
        "",
        "# Setup: mstatus.MIE=1, mstatus.SIE=1",
        "csrsi mstatus, MSTATUS_MIE   # MIE",
        "csrsi mstatus, MSTATUS_SIE   # SIE",
        "csrw mie, zero      # mie = all 0s initially",
        "",
    ]

    # Each competing interrupt is raised only where the platform implements it
    other_interrupts = {
        "meip": "UDB_MEI_INTR_IMPL",
        "mtip": "UDB_MTI_INTR_IMPL",
        "msip": "UDB_MSI_INTR_IMPL",
        "none": None,
    }

    for other_int, guard in other_interrupts.items():
        binname = f"lcofip_priority_{other_int}"

        if guard:
            lines.append(f"#ifdef {guard}")
        lines.extend(
            [
                f"# Testcase: competing interrupt = {other_int}",
                "csrw mip, zero   # clear LCOFIP and other pending bits",
                "csrw mie, zero   # disable interrupts (clear LCOFIE)",
                *prime_counter_overflow(r_val, r_temp2, r_temp, r_addr, "M"),
                "# the overflow sets OF and raises LCOFIP; mie = 0, so nothing fires yet",
                "",
            ]
        )

        if other_int == "meip":
            lines.append("RVTEST_SET_MEXT_INT_M")

        elif other_int == "mtip":
            lines.append("RVTEST_SET_MTIME_INT_M")

        elif other_int == "msip":
            lines.append("RVTEST_SET_MSW_INT_M")

        lines.extend(
            [
                "",
                test_data.add_testcase(
                    f"{binname}_mie_off",
                    coverpoint,
                    covergroup,
                ),
                "# mie = all 0s: LCOFIP and the competing interrupt stay pending, nothing fires",
                f"RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})",
                "",
                f"LI(x{r_temp}, -1)",
                test_data.add_testcase(
                    binname,
                    coverpoint,
                    covergroup,
                ),
                f"csrw mie, x{r_temp}   # mie = all 1s: competing interrupt fires first, then LCOFI",
                "",
                f"RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})",
                "",
                f"csrr x{r_temp2}, mip   # sample point for lcofip priority outcome",
                write_sigupd(r_temp2, test_data),
                "",
            ]
        )

        if other_int == "meip":
            lines.append("RVTEST_CLR_MEXT_INT_M")

        elif other_int == "mtip":
            lines.append("RVTEST_CLR_MTIME_INT_M")

        elif other_int == "msip":
            lines.append("RVTEST_CLR_MSW_INT_M")

        lines.extend(
            [
                "csrw mip, zero   # clear LCOFIP for next iteration",
                "csrw mie, zero",
            ]
        )
        if guard:
            lines.append("#endif")
        lines.append("")

    lines.extend(
        [
            "csrw RVTEST_CSR_MHPMEVENT, zero   # stop counting, clear OF",
            "#if __riscv_xlen == 32",
            "csrw RVTEST_CSR_MHPMEVENTH, zero",
            "#endif",
            "csrw RVTEST_CSR_MHPMCOUNTER, zero",
        ]
    )

    test_data.int_regs.return_registers([r_val, r_temp, r_temp2, r_addr])

    return lines


def _generate_lcofip_priority_s_tests(test_data: TestData) -> list[str]:

    ######################################
    covergroup = _cg("S")
    coverpoint = "cp_lcofip_priority_s"
    ######################################

    r_val, r_temp, r_temp2, r_addr = test_data.int_regs.get_registers(4)

    lines = [
        comment_banner(
            coverpoint,
            (
                "Priority of LCOFI interrupt in S-mode (4 cases).\n"
                "sstatus.SIE=1; LCOFIP is raised by a real hpmcounter overflow through\n"
                "RVMODEL_MHPMEVENT_CODE, together with one of {SEIP,STIP,SSIP,none}.\n"
                "Each case holds with sie = all 0s (nothing fires), then with sie = all 1s:\n"
                "the competing interrupt fires first and LCOFI only after it (lowest priority).\n"
                "The competing interrupts are raised through the RVTEST_SET_*_INT_S macros;\n"
                "enables stay in sie, written only here."
            ),
        ),
        "",
        "csrw sie, zero      # disable all S-mode interrupts",
        tsbi_call_or_direct("csrw RVTEST_CSR_MHPMEVENT, zero", "S"),
        "csrsi sstatus, SSTATUS_SIE   # sstatus.SIE = 1",
    ]

    # Each competing interrupt is raised only where the platform implements it
    other_interrupts = {
        "seip": "UDB_SEI_INTR_IMPL",
        "stip": "UDB_STI_INTR_IMPL",
        "ssip": "UDB_SSI_INTR_IMPL",
        "none": None,
    }

    for other_int, guard in other_interrupts.items():
        binname = f"lcofip_priority_s_{other_int}"

        lines.append("")
        if guard:
            lines.append(f"#ifdef {guard}")
        lines.extend(
            [
                f"# Testcase: competing interrupt = {other_int}",
                "# RVTEST_CSR_MHPMEVENT/RVTEST_CSR_MHPMCOUNTER writes go via T-SBI from S-mode, per spec",
                *prime_counter_overflow(r_val, r_temp2, r_temp, r_addr, "S"),
                "# the overflow sets OF and raises LCOFIP; sie = 0, so nothing fires yet",
            ]
        )

        if other_int == "seip":
            lines.append("RVTEST_SET_SEXT_INT_S")

        elif other_int == "stip":
            lines.append("RVTEST_SET_STIME_INT_S")

        elif other_int == "ssip":
            lines.append("RVTEST_SET_SSW_INT_S")

        lines.extend(
            [
                "",
                test_data.add_testcase(f"{binname}_sie_off", coverpoint, covergroup),
                "# sie = all 0s: LCOFIP and the competing interrupt stay pending, nothing fires",
                f"RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})",
                "",
                f"LI(x{r_temp}, -1)",
                test_data.add_testcase(binname, coverpoint, covergroup),
                tsbi_call_or_direct(
                    f"csrs sie, x{r_temp}   # sie = all 1s: competing interrupt fires first, then LCOFI", "S"
                ),
                "",
                f"RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})",
                f"csrr x{r_temp2}, sip   # sample point for lcofip priority outcome",
                write_sigupd(r_temp2, test_data),
                "",
            ]
        )

        if other_int == "seip":
            lines.append("RVTEST_CLR_SEXT_INT_S")

        elif other_int == "stip":
            lines.append("RVTEST_CLR_STIME_INT_S")

        elif other_int == "ssip":
            lines.append("RVTEST_CLR_SSW_INT_S")

        lines.extend(
            [
                f"LI(x{r_val}, MIP_LCOFIP)",
                f"csrc sip, x{r_val}   # clear LCOFIP for next iteration",
                "csrw sie, zero   # disable all before next iteration",
            ]
        )
        if guard:
            lines.append("#endif")

    lines.extend(
        [
            "",
            "csrci sstatus, SSTATUS_SIE   # sstatus.SIE = 0",
            tsbi_call_or_direct("csrw RVTEST_CSR_MHPMEVENT, zero   # stop counting, clear OF", "S"),
            "#if __riscv_xlen == 32",
            tsbi_call_or_direct("csrw RVTEST_CSR_MHPMEVENTH, zero", "S"),
            "#endif",
            tsbi_call_or_direct("csrw RVTEST_CSR_MHPMCOUNTER, zero", "S"),
        ]
    )

    test_data.int_regs.return_registers([r_val, r_temp, r_temp2, r_addr])

    return lines


@add_priv_test_generator(
    "Sscofpmf",
    required_extensions=["Sm", "Sscofpmf"],
    march_extensions=[],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_sscofpmfsm(test_data: TestData) -> list[TestChunk]:
    """Generate the Sscofpmf_Sm performance-counter-overflow tests, run in M-mode."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk("Sm_interrupt")
    tc.code.extend(_generate_lcofi_m_tests(test_data))
    tc.code.extend(_generate_lcofip_priority_sm_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())
    test_chunks.extend(generate_sscofpmf_suite(test_data, "M"))
    return test_chunks


@add_priv_test_generator(
    "Sscofpmf",
    required_extensions=["Sscofpmf"],
    march_extensions=[],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_sscofpmfs(test_data: TestData) -> list[TestChunk]:
    """Generate the Sscofpmf_S performance-counter-overflow tests, run in S-mode."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk("S_interrupt")
    tc.code.extend(generate_lcofi_sip_tests(test_data, "S"))
    tc.code.extend(_generate_lcofip_priority_s_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())
    test_chunks.extend(generate_sscofpmf_suite(test_data, "S"))
    return test_chunks


@add_priv_test_generator(
    "Sscofpmf",
    required_extensions=["Sscofpmf", "U"],
)
def make_sscofpmfu(test_data: TestData) -> list[TestChunk]:
    """Generate the Sscofpmf_U performance-counter-overflow tests, run in U-mode."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk("U_interrupt")
    tc.code.extend(generate_lcofi_sip_tests(test_data, "U"))
    test_chunks.append(test_data.end_test_chunk())
    test_chunks.extend(generate_sscofpmf_suite(test_data, "U"))
    return test_chunks
