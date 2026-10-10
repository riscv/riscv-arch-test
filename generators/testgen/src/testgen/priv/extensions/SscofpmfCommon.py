##################################
# priv/extensions/SscofpmfCommon.py
# Written by: Ayesha Anwar, ayesha.anwaar2005@gmail.com
# Sscofpmf (HPM counter overflow/interrupt) shared test-case generators.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared Sscofpmf test-case generators, called with priv_mode in {"Sm", "S", "U"}."""

import re
from collections.abc import Callable

from testgen.asm.csr import csr_walk_test
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk

_CSR_INSTR_RE = re.compile(r"\s*(csrr|csrw|csrs|csrc)\s+([^,\s]+)\s*,\s*([^,\s#]+)")

_S_ACCESSIBLE_CSRS = ("sip", "sie", "sstatus", "scountovf")


def _csr_number(csr: str) -> str:
    """A macro is used as is, and a CSR name becomes its CSR_* macro from encoding.h."""
    return csr if csr.startswith(("CSR_", "RVTEST_CSR_")) else f"CSR_{csr.upper()}"


def csr_access(instr: str, mode: str) -> str:
    """Direct at Sm, and at S for sip/sie/sstatus/scountovf. Everything else is a T-SBI call
    through the RVTEST_TSBI_CSR macros, which take the value in a1 and return a read in a0."""
    if mode == "Sm":
        return instr
    code = instr.split("#", 1)[0]
    if mode == "S" and any(re.search(rf"\b{name}\b", code) for name in _S_ACCESSIBLE_CSRS):
        return instr
    match = _CSR_INSTR_RE.match(code)
    if match is None:
        raise ValueError(f"Unsupported CSR instruction for T-SBI: {instr}")
    op, first, second = match.groups()
    if op == "csrr":
        lines = [f"RVTEST_TSBI_CSR_READ({_csr_number(second)})", f"mv {first}, a0"]
    else:
        tsbi = {
            "csrw": "RVTEST_TSBI_CSR_WRITE_A1({csr})",
            "csrs": "RVTEST_TSBI_CSR_ACCESS TSBI_CSR_SET({csr})",
            "csrc": "RVTEST_TSBI_CSR_ACCESS TSBI_CSR_CLEAR({csr})",
        }[op]
        lines = [f"mv a1, {second}", tsbi.format(csr=_csr_number(first))]
    return "\n".join([f"# T-SBI call: {instr.strip()}", *lines])


def clear_lcofip(r_tmp: int, priv_mode: str) -> list[str]:
    """Clear LCOFIP through sip when S exists and the suite runs below M, else through mip."""
    set_bit = f"LI(x{r_tmp}, {hex(1 << 13)})"
    if priv_mode == "Sm":
        return [set_bit, f"csrc mip, x{r_tmp}   # clear LCOFIP"]
    if priv_mode == "S":
        return [set_bit, f"csrc sip, x{r_tmp}   # clear LCOFIP"]
    return [
        set_bit,
        "#ifdef S_SUPPORTED",
        csr_access(f"csrc sip, x{r_tmp}   # clear LCOFIP", priv_mode),
        "#else",
        csr_access(f"csrc mip, x{r_tmp}   # clear LCOFIP", priv_mode),
        "#endif",
    ]


# Every T-SBI call runs the M-mode handler, and a call from U is delegated through S
# first, so counting must be inhibited in every mode above the one under test or the
# counter would also count the round trip instead of just the workload.
HIGHER_MODE_INHIBITS = {"Sm": 0, "S": 1 << 62, "U": (1 << 62) | (1 << 61)}
HIGHER_MODE_INHIBITS_32 = {mode: bits >> 32 for mode, bits in HIGHER_MODE_INHIBITS.items()}
HIGHER_MODE_PATTERN = {mode: bits >> 58 for mode, bits in HIGHER_MODE_INHIBITS.items()}

EVENT_VAL_HI = "(((RVMODEL_MHPMEVENT_VAL) >> 32) & 0xFFFFFF)"


def counted_since_all_ones(reg: int) -> list[str]:
    """Reduce x{reg}, a counter read after it was preset to all 1s, to 1 if it counted at
    least one event and 0 if it did not. The count itself is implementation-specific."""
    return [
        f"addi x{reg}, x{reg}, 1            # x{reg} = val + 1 (0 iff val is still all 1s)",
        f"snez x{reg}, x{reg}               # x{reg} = counted at least one event",
    ]


def write_event_pattern(r_val: int, r_hval: int, inhibit_pattern: int, priv_mode: str) -> list[str]:
    """Write RVMODEL_MHPMEVENT_VAL with the given MINH/SINH/UINH/VSINH/VUINH pattern and OF=0."""
    return [
        "#if __riscv_xlen == 32",
        f"LI(x{r_val}, RVMODEL_MHPMEVENT_VAL)",
        csr_access(f"csrw RVTEST_CSR_MHPMEVENT, x{r_val}", priv_mode),
        f"LI(x{r_hval}, {EVENT_VAL_HI} | ({inhibit_pattern} << 26))   # 58-32 = 26",
        csr_access(f"csrw RVTEST_CSR_MHPMEVENTH, x{r_hval}", priv_mode),
        "#else",
        f"LI(x{r_val}, RVMODEL_MHPMEVENT_VAL | ({inhibit_pattern} << 58))   # OF starts at 0",
        csr_access(f"csrw RVTEST_CSR_MHPMEVENT, x{r_val}", priv_mode),
        "#endif",
    ]


def write_counter_all_ones(r_temp: int, priv_mode: str) -> list[str]:
    return [
        f"LI(x{r_temp}, -1)",
        csr_access(f"csrw RVTEST_CSR_MHPMCOUNTER, x{r_temp}   # all 1s -> next count overflows", priv_mode),
        "#if __riscv_xlen == 32",
        csr_access(f"csrw RVTEST_CSR_MHPMCOUNTERH, x{r_temp}   # high half must also be all 1s", priv_mode),
        "#endif",
    ]


def prime_counter_overflow(r_val: int, r_hval: int, r_temp: int, r_addr: int, priv_mode: str) -> list[str]:
    """Overflow the counter in the mode under test, which sets OF and raises LCOFIP."""
    return [
        *write_event_pattern(r_val, r_hval, HIGHER_MODE_PATTERN[priv_mode], priv_mode),
        *write_counter_all_ones(r_temp, priv_mode),
        f"LA(x{r_addr}, scratch)",
        f"RVMODEL_MHPMEVENT_CODE(x{r_addr}, x{r_val})",
    ]


_INHIBIT_MODE_SUFFIX = {"Sm": "mmode", "S": "smode", "U": "umode"}


def _generate_xinh_inhibits_tests(
    test_data: TestData, priv_mode: str, combos: range = range(32), toggles: bool = True
) -> list[str]:
    """xINH toggles (when ``toggles``) and the MINH/SINH/UINH/VSINH/VUINH combinations in ``combos``."""
    _INHIBIT_BIT_POS = {"Sm": 62, "S": 61, "U": 60}
    _INHIBIT_PREFIX = {"Sm": "m", "S": "s", "U": "u"}

    covergroup = "Sscofpmf_cg"
    inh_prefix = _INHIBIT_PREFIX[priv_mode]
    coverpoint = f"cp_{inh_prefix}inh_inhibits_{_INHIBIT_MODE_SUFFIX[priv_mode]}"
    inh_bit_pos = _INHIBIT_BIT_POS[priv_mode]
    inh_bit_pos_32 = inh_bit_pos - 32

    r_val, r_temp = test_data.int_regs.get_registers(2, exclude_regs=[0, 31])

    higher_inhibits = HIGHER_MODE_INHIBITS[priv_mode]
    higher_inhibits_32 = HIGHER_MODE_INHIBITS_32[priv_mode]

    lines = [
        comment_banner(
            coverpoint,
            f"{inh_prefix.upper()}INH bit (mhpmevent[{inh_bit_pos}]) inhibits counting in {priv_mode}-mode.\n"
            "Counting stays inhibited in the modes above the one under test, so the counter\n"
            "only ever reflects the workload and never the T-SBI round trip that reaches the\n"
            "M-level counter CSRs.",
        ),
        "",
        csr_access("csrw mie, zero   # disable interrupts before toggle/sweep", priv_mode),
        "",
    ]
    indent = ""

    for inh_val in [0, 1] if toggles else []:
        binname = f"{inh_prefix}inh_{inh_val}_{priv_mode.lower()}"
        lines.extend(
            [
                f"{indent}# Testcase: {inh_prefix}inh = {inh_val}",
                f"{indent}#if __riscv_xlen == 32",
                f"{indent}LI(x{r_val}, RVMODEL_MHPMEVENT_VAL)",
                f"{indent}{csr_access(f'csrw RVTEST_CSR_MHPMEVENT, x{r_val}', priv_mode)}",
                f"{indent}LI(x{r_val}, {EVENT_VAL_HI} | {hex(higher_inhibits_32 | (inh_val << inh_bit_pos_32))})",
                f"{indent}{csr_access(f'csrw RVTEST_CSR_MHPMEVENTH, x{r_val}', priv_mode)}",
                f"{indent}#else",
                f"{indent}LI(x{r_val}, RVMODEL_MHPMEVENT_VAL | {hex(higher_inhibits | (inh_val << inh_bit_pos))})",
                f"{indent}{csr_access(f'csrw RVTEST_CSR_MHPMEVENT, x{r_val}', priv_mode)}",
                f"{indent}#endif",
                f"{indent}{csr_access('csrw RVTEST_CSR_MHPMCOUNTER, zero', priv_mode)}",
                "",
                f"{indent}LA(x{r_temp}, scratch)",
                f"{indent}RVMODEL_MHPMEVENT_CODE(x{r_temp}, x{r_val})",
                "",
                f"{indent}{test_data.add_testcase(binname, coverpoint, covergroup)}",
                f"{indent}{csr_access(f'csrr x{r_temp}, RVTEST_CSR_MHPMCOUNTER', priv_mode)}",
                f"{indent}snez x{r_temp}, x{r_temp}",
                f"{indent}{write_sigupd(r_temp, test_data)}",
                "",
            ]
        )

    lines.extend(
        [
            f"{indent}LI(x{r_val}, RVMODEL_MHPMEVENT_VAL)",
            f"{indent}{csr_access(f'csrw RVTEST_CSR_MHPMEVENT, x{r_val}', priv_mode)}",
            f"{indent}#if __riscv_xlen == 32",
            f"{indent}LI(x{r_val}, {EVENT_VAL_HI})",
            f"{indent}{csr_access(f'csrw RVTEST_CSR_MHPMEVENTH, x{r_val}', priv_mode)}",
            f"{indent}#endif",
            "",
        ]
    )

    r_hval = test_data.int_regs.get_register(exclude_regs=[0, 31])

    def combo_counts() -> list[str]:
        """In M-mode, run the workload so each combination checks that only MINH decides
        whether M-mode events count. Below M the T-SBI round trip would be counted, so the
        S and U suites check counting only in the single-bit toggles."""
        if priv_mode != "Sm":
            return []
        return [
            f"{indent}csrw RVTEST_CSR_MHPMCOUNTER, zero",
            f"{indent}LA(x{r_temp}, scratch)",
            f"{indent}RVMODEL_MHPMEVENT_CODE(x{r_temp}, x{r_hval})",
            f"{indent}csrr x{r_temp}, RVTEST_CSR_MHPMCOUNTER",
            f"{indent}snez x{r_temp}, x{r_temp}   # counted iff MINH = 0",
            f"{indent}{write_sigupd(r_temp, test_data)}",
        ]

    lines.append(f"{indent}#if __riscv_xlen == 32")
    for combo in combos:
        binname = f"xinh_combo_{combo:05b}_{priv_mode.lower()}_rv32"
        lines.extend(
            [
                f"{indent}LI(x{r_hval}, {EVENT_VAL_HI} | ({combo} << 26))",
                f"{indent}{csr_access(f'csrw RVTEST_CSR_MHPMEVENTH, x{r_hval}', priv_mode)}",
                "",
                f"{indent}{test_data.add_testcase(binname, coverpoint, covergroup)}",
                f"{indent}{csr_access(f'csrr x{r_temp}, RVTEST_CSR_MHPMEVENTH', priv_mode)}",
                # VSINH/VUINH are read-only zero without H, so check them only on an H hart.
                "#ifndef H_SUPPORTED",
                f"{indent}LI(x{r_hval}, 0xF3FFFFFF)   # clear bits 27:26 (VSINH/VUINH)",
                f"{indent}and x{r_temp}, x{r_temp}, x{r_hval}",
                "#endif",
                f"{indent}{write_sigupd(r_temp, test_data)}",
                *combo_counts(),
                "",
            ]
        )
    lines.append(f"{indent}#else")
    for combo in combos:
        binname = f"xinh_combo_{combo:05b}_{priv_mode.lower()}_rv64"
        lines.extend(
            [
                f"{indent}LI(x{r_val}, RVMODEL_MHPMEVENT_VAL | ({combo} << 58))",
                f"{indent}{csr_access(f'csrw RVTEST_CSR_MHPMEVENT, x{r_val}', priv_mode)}",
                "",
                f"{indent}{test_data.add_testcase(binname, coverpoint, covergroup)}",
                f"{indent}{csr_access(f'csrr x{r_temp}, RVTEST_CSR_MHPMEVENT', priv_mode)}",
                # VSINH/VUINH are read-only zero without H, so check them only on an H hart.
                "#ifndef H_SUPPORTED",
                f"{indent}LI(x{r_val}, 0xF3FFFFFFFFFFFFFF)   # clear bits 59:58 (VSINH/VUINH)",
                f"{indent}and x{r_temp}, x{r_temp}, x{r_val}",
                "#endif",
                f"{indent}{write_sigupd(r_temp, test_data)}",
                *combo_counts(),
                "",
            ]
        )
    lines.append(f"{indent}#endif")
    lines.extend(
        [
            f"{indent}{csr_access('csrw RVTEST_CSR_MHPMEVENT, zero', priv_mode)}",
            f"{indent}#if __riscv_xlen == 32",
            f"{indent}{csr_access('csrw RVTEST_CSR_MHPMEVENTH, zero', priv_mode)}",
            f"{indent}#endif",
            f"{indent}{csr_access('csrw RVTEST_CSR_MHPMCOUNTER, zero', priv_mode)}",
            "",
        ]
    )
    test_data.int_regs.return_registers([r_hval])
    test_data.int_regs.return_registers([r_val, r_temp])
    return lines


# Below M every pattern inhibits the modes above the one under test, so the T-SBI trap handler
# never counts.
_INHIBIT_PATTERNS = {
    "Sm": [0b00000, 0b11100, 0b10000, 0b01000, 0b00100],
    "S": [0b10000, 0b10100, 0b11000, 0b11100],
    "U": [0b11000, 0b11100],
}


def _generate_of_set_on_overflow_tests(test_data: TestData, priv_mode: str) -> list[str]:
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_of_set_on_overflow"
    ######################################

    r_val, r_temp, r_lcofip, r_addr, r_bool, r_hval = test_data.int_regs.get_registers(6, exclude_regs=[0, 31])

    def read_event_config_bits() -> list[str]:
        """Read OF and the 5-bit inhibit field into x{r_temp}, masked to those bits."""
        return [
            "#if __riscv_xlen == 32",
            csr_access(f"csrr x{r_temp}, RVTEST_CSR_MHPMEVENTH   # sample point for mhpmevent_of", priv_mode),
            f"LI(x{r_bool}, 0xFC000000)   # keep only OF + the 5-bit inhibit field (bits 31:26)",
            f"and x{r_temp}, x{r_temp}, x{r_bool}",
            "#else",
            csr_access(f"csrr x{r_temp}, RVTEST_CSR_MHPMEVENT   # sample point for mhpmevent_of", priv_mode),
            f"LI(x{r_bool}, 0xFC00000000000000)   # keep only OF + the 5-bit inhibit field (bits 63:58)",
            f"and x{r_temp}, x{r_temp}, x{r_bool}",
            "#endif",
        ]

    pending_csr, enable_csr = ("sip", "sie") if priv_mode == "S" else ("mip", "mie")
    lcofip_csr = pending_csr

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
                "# === M-MODE SETUP ===",
                f"# Testcase: mode = {priv_mode}, inhibit pattern = {inhibit_pattern:05b}, OF initial = 0",
            ]
        )

        if priv_mode == "U":
            lines.extend(
                [
                    "#ifdef S_SUPPORTED",
                    csr_access("csrw sip, zero   # clear LCOFIP", priv_mode),
                    csr_access("csrw sie, zero   # disable interrupts (clear LCOFIE)", priv_mode),
                    "#else",
                    csr_access("csrw mip, zero   # clear LCOFIP", priv_mode),
                    csr_access("csrw mie, zero   # disable interrupts (clear LCOFIE)", priv_mode),
                    "#endif",
                ]
            )
        else:
            lines.extend(
                [
                    csr_access(f"csrw {pending_csr}, zero   # clear LCOFIP", priv_mode),
                    csr_access(f"csrw {enable_csr}, zero   # disable interrupts (clear LCOFIE)", priv_mode),
                ]
            )

        if priv_mode == "Sm":
            lines.extend(
                [
                    *write_event_pattern(r_val, r_hval, inhibit_pattern, priv_mode),
                    *write_counter_all_ones(r_temp, priv_mode),
                    "",
                    f"LA(x{r_addr}, scratch)",
                    "# One counted event is enough to wrap the all-1s counter and set OF",
                    f"RVMODEL_MHPMEVENT_CODE(x{r_addr}, x{r_val})",
                    "",
                    test_data.add_testcase(binname, coverpoint, covergroup),
                    *read_event_config_bits(),
                    write_sigupd(r_temp, test_data),
                    f"csrr x{r_temp}, RVTEST_CSR_MHPMCOUNTER   # sample point: did the counter move off all 1s?",
                    *counted_since_all_ones(r_temp),
                    write_sigupd(r_temp, test_data),
                    "",
                    f"RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})   # wait for RVMODEL_INTERRUPT_LATENCY",
                    f"csrr x{r_lcofip}, {lcofip_csr}   # sample point for lcofip",
                    write_sigupd(r_lcofip, test_data),
                ]
            )

        else:
            mhpmcounter_read = (
                f"csrr x{r_temp}, RVTEST_CSR_MHPMCOUNTER   # sample point: did the counter move off all 1s?"
            )

            lines.extend(
                [
                    f"# RVTEST_CSR_MHPMEVENT/RVTEST_CSR_MHPMCOUNTER writes go via T-SBI from {priv_mode}-mode, per spec",
                    test_data.add_testcase(binname, coverpoint, covergroup),
                    *write_event_pattern(r_val, r_hval, inhibit_pattern, priv_mode),
                    *write_counter_all_ones(r_temp, priv_mode),
                    "",
                    f"LA(x{r_addr}, scratch)",
                    "# One counted event is enough to wrap the all-1s counter and set OF",
                    f"RVMODEL_MHPMEVENT_CODE(x{r_addr}, x{r_val})",
                    "",
                    *read_event_config_bits(),
                    write_sigupd(r_temp, test_data),
                    csr_access(mhpmcounter_read, priv_mode),
                    *counted_since_all_ones(r_temp),
                    write_sigupd(r_temp, test_data),
                    "",
                    f"RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})   # wait for RVMODEL_INTERRUPT_LATENCY",
                ]
            )

            if priv_mode == "U":
                lines.extend(
                    [
                        "#ifdef S_SUPPORTED",
                        csr_access(f"csrr x{r_lcofip}, sip   # sample point for lcofip", priv_mode),
                        "#else",
                        csr_access(f"csrr x{r_lcofip}, mip   # sample point for lcofip", priv_mode),
                        "#endif",
                        write_sigupd(r_lcofip, test_data),
                    ]
                )
            else:
                lines.extend(
                    [
                        csr_access(f"csrr x{r_lcofip}, {lcofip_csr}   # sample point for lcofip", priv_mode),
                        write_sigupd(r_lcofip, test_data),
                    ]
                )

    # OF already 1: the overflow must leave OF set and must not request LCOFI.
    already_set_coverpoint = "cp_of_already_set"
    if priv_mode == "U":
        lcofip_read = [
            "#ifdef S_SUPPORTED",
            csr_access(f"csrr x{r_lcofip}, sip   # sample point -- LCOFIP must stay 0", priv_mode),
            "#else",
            csr_access(f"csrr x{r_lcofip}, mip   # sample point -- LCOFIP must stay 0", priv_mode),
            "#endif",
        ]
    else:
        lcofip_read = [csr_access(f"csrr x{r_lcofip}, {lcofip_csr}   # sample point -- LCOFIP must stay 0", priv_mode)]
    lines.extend(
        [
            "",
            f"# Testcase: mode = {priv_mode}, inhibit pattern = {HIGHER_MODE_PATTERN[priv_mode]:05b}, OF initial = 1",
            csr_access("csrw mie, zero   # disable interrupts", priv_mode),
            "#if __riscv_xlen == 32",
            f"LI(x{r_val}, RVMODEL_MHPMEVENT_VAL)",
            csr_access(f"csrw RVTEST_CSR_MHPMEVENT, x{r_val}", priv_mode),
            f"LI(x{r_hval}, {EVENT_VAL_HI} | {hex((1 << 31) | HIGHER_MODE_INHIBITS_32[priv_mode])})   # OF = 1",
            csr_access(f"csrw RVTEST_CSR_MHPMEVENTH, x{r_hval}", priv_mode),
            "#else",
            f"LI(x{r_val}, RVMODEL_MHPMEVENT_VAL | {hex((1 << 63) | HIGHER_MODE_INHIBITS[priv_mode])})   # OF = 1",
            csr_access(f"csrw RVTEST_CSR_MHPMEVENT, x{r_val}", priv_mode),
            "#endif",
            *write_counter_all_ones(r_temp, priv_mode),
            *clear_lcofip(r_temp, priv_mode),
            "",
            f"LA(x{r_addr}, scratch)",
            f"RVMODEL_MHPMEVENT_CODE(x{r_addr}, x{r_val})",
            f"RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})   # wait for RVMODEL_INTERRUPT_LATENCY",
            "",
            test_data.add_testcase(
                f"of_overflow_{priv_mode.lower()}_of_already_set", already_set_coverpoint, covergroup
            ),
            *read_event_config_bits(),
            write_sigupd(r_temp, test_data),
            csr_access(
                f"csrr x{r_temp}, RVTEST_CSR_MHPMCOUNTER   # sample point: did the counter move off all 1s?", priv_mode
            ),
            *counted_since_all_ones(r_temp),
            write_sigupd(r_temp, test_data),
            *lcofip_read,
            f"srli x{r_lcofip}, x{r_lcofip}, 13",
            f"andi x{r_lcofip}, x{r_lcofip}, 1   # isolate LCOFIP",
            write_sigupd(r_lcofip, test_data),
        ]
    )

    test_data.int_regs.return_registers([r_val, r_temp, r_lcofip, r_addr, r_bool, r_hval])

    return lines


def _generate_overflow_hw_only_tests(test_data: TestData, priv_mode: str) -> list[str]:
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_overflow_hw_only"
    ######################################

    r_val, r_of = test_data.int_regs.get_registers(2, exclude_regs=[0, 31])

    lines = [
        comment_banner(
            coverpoint,
            "A software write of RVTEST_CSR_MHPMCOUNTER, however extreme, must never set OF --\n"
            f"only a hardware counter increment through overflow may. mode = {priv_mode}.",
        ),
        "",
        csr_access("csrw mie, zero   # disable interrupts", priv_mode),
        csr_access("csrw RVTEST_CSR_MHPMEVENT, zero", priv_mode),
        "#if __riscv_xlen == 32",
        csr_access("csrw RVTEST_CSR_MHPMEVENTH, zero   # clear OF and xINH left by earlier tests", priv_mode),
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
                csr_access(f"csrw RVTEST_CSR_MHPMCOUNTER, x{r_val}", priv_mode),
                "",
                test_data.add_testcase(binname, coverpoint, covergroup),
                "#if __riscv_xlen == 32",
                csr_access(f"csrr x{r_of}, RVTEST_CSR_MHPMEVENTH   # sample point -- OF must read 0", priv_mode),
                f"srli x{r_of}, x{r_of}, 31   # OF (bit 31 of the H-half) -> bit 0",
                "#else",
                csr_access(f"csrr x{r_of}, RVTEST_CSR_MHPMEVENT   # sample point -- OF must read 0", priv_mode),
                f"srli x{r_of}, x{r_of}, 63   # OF (bit 63) -> bit 0",
                "#endif",
                write_sigupd(r_of, test_data),
                "",
            ]
        )

    test_data.int_regs.return_registers([r_val, r_of])
    return lines


def _generate_lcofip_hw_only_tests(test_data: TestData, priv_mode: str) -> list[str]:
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_lcofip_hw_only"
    ######################################

    r_val, r_temp = test_data.int_regs.get_registers(2, exclude_regs=[0, 31])

    def set_of(op: str, desc: str) -> list[str]:
        return [
            "#if __riscv_xlen == 32",
            f"LI(x{r_val}, {hex(1 << 31)})",
            csr_access(f"{op} RVTEST_CSR_MHPMEVENTH, x{r_val}   # {desc}", priv_mode),
            "#else",
            f"LI(x{r_val}, {hex(1 << 63)})",
            csr_access(f"{op} RVTEST_CSR_MHPMEVENT, x{r_val}   # {desc}", priv_mode),
            "#endif",
        ]

    def readback(expect_desc: str) -> list[str]:
        """Read LCOFIP through sip at S (or U with S), else through mip."""
        if priv_mode == "Sm":
            read = [csr_access(f"csrr x{r_temp}, mip   # sample point -- LCOFIP {expect_desc}", priv_mode)]
        elif priv_mode == "S":
            read = [csr_access(f"csrr x{r_temp}, sip   # sample point -- LCOFIP {expect_desc}", priv_mode)]
        else:
            read = [
                "#ifdef S_SUPPORTED",
                csr_access(f"csrr x{r_temp}, sip   # sample point -- LCOFIP {expect_desc}", priv_mode),
                "#else",
                csr_access(f"csrr x{r_temp}, mip   # sample point -- LCOFIP {expect_desc}", priv_mode),
                "#endif",
            ]
        return [
            *read,
            f"srli x{r_temp}, x{r_temp}, 13",
            f"andi x{r_temp}, x{r_temp}, 1   # isolate LCOFIP",
            write_sigupd(r_temp, test_data),
        ]

    lines = [
        comment_banner(
            coverpoint,
            (
                "OF being set by software alone must never make LCOFIP pend --\n"
                "only a real hardware counter-register increment through overflow\n"
                "may set OF (and therefore LCOFIP). No pending/enable sweep here:\n"
                "this coverpoint tests the absence of a software-only path to LCOFIP.\n"
                f"mode = {priv_mode}."
            ),
        ),
        "",
        csr_access("csrw mie, zero   # disable interrupts", priv_mode),
        # A real overflow earlier leaves LCOFIP pending on a counting hart.
        *clear_lcofip(r_temp, priv_mode),
        "",
        "# Testcase: software-set OF bit directly (no HW increment)",
        *set_of("csrs", "software-set OF bit"),
        "",
        test_data.add_testcase(f"lcofip_hw_only_{priv_mode.lower()}_set_of", coverpoint, covergroup),
        f"RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})   # wait for RVMODEL_INTERRUPT_LATENCY",
    ]
    lines.extend(readback("must read 0"))

    lines.extend(
        [
            "",
            "# Testcase: software-clear OF bit directly (no HW increment)",
            *set_of("csrc", "software-clear OF bit"),
            "",
            test_data.add_testcase(f"lcofip_hw_only_{priv_mode.lower()}_clear_of", coverpoint, covergroup),
            f"RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})   # wait for RVMODEL_INTERRUPT_LATENCY",
        ]
    )
    lines.extend(readback("must still read 0"))

    test_data.int_regs.return_registers([r_val, r_temp])
    return lines


NUM_OF_BITS = 29  # mhpmevent3..31


def unknown_of_state() -> list[int | None]:
    """OF state for write_of_pattern() when earlier tests may have changed OF."""
    return [None] * NUM_OF_BITS


def boot_of_state() -> list[int | None]:
    """OF state for write_of_pattern() at the start of a test file: rvtest_setup.h clears
    mhpmevent3..31, and the RV32 high halves that hold OF, at every boot."""
    return [0] * NUM_OF_BITS


def write_of_pattern(
    r_of_bit: int, pattern_name: str, of_bit_fn: Callable[[int], int], mode: str, of_state: list[int | None]
) -> list[str]:
    """Set or clear OF in mhpmevent3..31 per of_bit_fn(counter - 3). of_state holds the OF value
    last written to each counter (None if unknown) and is updated in place, so only the counters
    whose OF changes are written. Below M each write is a T-SBI call."""
    changes = [(i, of_bit_fn(i)) for i in range(NUM_OF_BITS) if of_state[i] != of_bit_fn(i)]
    of_state[:] = [of_bit_fn(i) for i in range(NUM_OF_BITS)]

    def writes(csr_suffix: str, of_bit: int, desc: str) -> list[str]:
        lines = [f"LI(x{r_of_bit}, {hex(of_bit)})   # OF bit ({desc})"]
        for i, of in changes:
            op, action = ("csrs", "set") if of else ("csrc", "clear")
            lines.append(csr_access(f"{op} CSR_MHPMEVENT{i + 3}{csr_suffix}, x{r_of_bit}   # {action} OF", mode))
        return lines

    return [
        f"# --- Write OF pattern: {pattern_name} across mhpmevent3..31 ---",
        "#if __riscv_xlen == 32",
        *writes("H", 1 << 31, "bit 31 of mhpmeventh, RV32"),
        "#else",
        *writes("", 1 << 63, "bit 63 of mhpmevent, RV64"),
        "#endif",
        "",
    ]


MCOUNTEREN_OF_PATTERNS: dict[str, Callable[[int], int]] = {
    "all_ones": lambda i: 1,
    "checker_even": lambda i: 1 if i % 2 == 0 else 0,
    "checker_odd": lambda i: 1 if i % 2 == 1 else 0,
}


def _generate_scountovf_mcounteren_tests(
    test_data: TestData, mode: str, of_state: list[int | None], of_names: list[str]
) -> list[str]:
    ######################################
    covergroup = "Sscofpmf_cg"
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

    indent = ""

    for of_name in of_names:
        of_bit_fn = MCOUNTEREN_OF_PATTERNS[of_name]
        r_of_bit = test_data.int_regs.get_register(exclude_regs=[0, 31])
        lines.extend(write_of_pattern(r_of_bit, of_name, of_bit_fn, mode, of_state))
        test_data.int_regs.return_registers([r_of_bit])

        walk_coverpoint = f"{coverpoint}_{of_name}_{mode.lower()}"

        if mode == "Sm":
            lines.extend(
                csr_walk_test(
                    test_data,
                    csr=("mcounteren", 0xFFFFFFF8),
                    covergroup=covergroup,
                    coverpoint=walk_coverpoint,
                    start_bit=3,
                    walk_zeros=True,
                )
            )

            r_scountovf = test_data.int_regs.get_register(exclude_regs=[0, 31])
            lines.append(test_data.add_testcase(f"scountovf_{of_name}_{mode.lower()}", coverpoint, covergroup))
            lines.append(csr_access(f"csrr x{r_scountovf}, scountovf   # sample point", mode))
            lines.append(write_sigupd(r_scountovf, test_data))
            lines.append("")
            test_data.int_regs.return_registers([r_scountovf])
        else:
            r_mcounteren, r_scountovf = test_data.int_regs.get_registers(2, exclude_regs=[0, 31])

            for state_name, val in [("all_zeros", 0), ("all_ones", 0xFFFFFFF8)]:
                binname = f"mcounteren_{state_name}"
                lines.extend(
                    [
                        f"{indent}LI(x{r_mcounteren}, {hex(val)})",
                        f"{indent}{csr_access(f'csrw mcounteren, x{r_mcounteren}', mode)}",
                        f"{indent}{test_data.add_testcase(binname, walk_coverpoint, covergroup)}",
                        f"{indent}{csr_access(f'csrr x{r_scountovf}, scountovf   # sample point', mode)}",
                        f"{indent}{write_sigupd(r_scountovf, test_data)}",
                        "",
                    ]
                )

            for bit in range(3, 32):
                binname = f"mcounteren_walk_bit_{bit}"
                lines.extend(
                    [
                        f"{indent}LI(x{r_mcounteren}, {1 << bit})",
                        f"{indent}{csr_access(f'csrw mcounteren, x{r_mcounteren}', mode)}",
                        f"{indent}{test_data.add_testcase(binname, walk_coverpoint, covergroup)}",
                        f"{indent}{csr_access(f'csrr x{r_scountovf}, scountovf   # sample point', mode)}",
                        f"{indent}{write_sigupd(r_scountovf, test_data)}",
                        "",
                    ]
                )

            lines.append(f"{indent}{csr_access('csrw mcounteren, zero', mode)}")
            lines.append("")
            test_data.int_regs.return_registers([r_mcounteren, r_scountovf])

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

    def emit_accesses(csr_name: str) -> None:
        for access in access_types:
            binname = f"sscofpmf_access_{csr_name}_{access}_{mode.lower()}"
            lines.append(test_data.add_testcase(binname, coverpoint, covergroup))

            if access == "read":
                lines.append(csr_access(f"csrr x{r_val}, {csr_name}", mode))
            elif access == "write_ones":
                lines.extend([f"LI(x{r_val}, -1)", csr_access(f"csrw {csr_name}, x{r_val}", mode)])
            elif access == "write_zeros":
                lines.append(csr_access(f"csrw {csr_name}, zero", mode))
            elif access == "set":
                lines.extend([f"LI(x{r_val}, -1)", csr_access(f"csrs {csr_name}, x{r_val}", mode)])
            elif access == "clear":
                lines.extend([f"LI(x{r_val}, -1)", csr_access(f"csrc {csr_name}, x{r_val}", mode)])
            lines.append("")

    emit_accesses("scountovf")

    if mode == "Sm":  # mhpmeventh3..31 sweep is M-mode only per spec
        lines.append("#if __riscv_xlen == 32")
        for n in range(3, 32):
            emit_accesses(f"CSR_MHPMEVENT{n}H")
        lines.append("#endif")

    test_data.int_regs.return_registers([r_val])
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
    of_state: list[int | None],
    patterns: list[tuple[str, Callable[[int], int]]],
) -> list[str]:
    if priv_mode == "U":
        return []

    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_scountovf_shadow"
    ######################################

    indent = ""

    lines = [
        comment_banner(
            coverpoint,
            f"scountovf shadows OF bits of mhpmevent3:31, mode = {priv_mode}.\n"
            "mcounteren = all 1s (fixed for this coverpoint). Write patterns to\n"
            "mhpmevent3...31.OF: all 0s, walking 1s, all 1s. Read scountovf.\n",
        ),
        "",
    ]

    r_mcounteren = test_data.int_regs.get_register(exclude_regs=[0, 31])
    lines.extend(
        [
            f"{indent}LI(x{r_mcounteren}, -1)",
            f"{indent}{csr_access(f'csrw mcounteren, x{r_mcounteren}   # mcounteren = all 1s (fixed for this coverpoint)', priv_mode)}",
            "",
        ]
    )
    test_data.int_regs.return_registers([r_mcounteren])

    def emit_pattern(pattern_name: str, of_bit_fn: Callable[[int], int]) -> None:
        r_of_bit, r_scountovf = test_data.int_regs.get_registers(2, exclude_regs=[0, 31])
        lines.extend(write_of_pattern(r_of_bit, pattern_name, of_bit_fn, priv_mode, of_state))
        test_data.int_regs.return_registers([r_of_bit])

        binname = f"scountovf_shadow_{priv_mode.lower()}_{pattern_name}"
        lines.append(f"{indent}{test_data.add_testcase(binname, coverpoint, covergroup)}")
        lines.append(
            f"{indent}{csr_access(f'csrr x{r_scountovf}, scountovf   # sample point -- must match OF pattern', priv_mode)}"
        )
        lines.append(f"{indent}{write_sigupd(r_scountovf, test_data)}")
        lines.append("")

        test_data.int_regs.return_registers([r_scountovf])

    for pattern_name, of_bit_fn in patterns:
        emit_pattern(pattern_name, of_bit_fn)

    return lines


def generate_sscofpmf_suite(test_data: TestData, mode: str) -> list[TestChunk]:
    """Assemble the shared Sscofpmf tests for ``mode`` ("Sm"/"S"/"U").

    Sm accesses the CSRs directly, so its tests stay together. Below M every access to an
    M-level CSR is a T-SBI call, so the S and U tests are split into small named test files."""
    test_chunks: list[TestChunk] = []

    if mode == "Sm":
        of_state = unknown_of_state()
        tc = test_data.begin_test_chunk()
        tc.code.extend(_generate_xinh_inhibits_tests(test_data, mode))
        tc.code.extend(_generate_of_set_on_overflow_tests(test_data, mode))
        tc.code.extend(_generate_overflow_hw_only_tests(test_data, mode))
        tc.code.extend(_generate_lcofip_hw_only_tests(test_data, mode))
        tc.code.extend(_generate_scountovf_mcounteren_tests(test_data, mode, of_state, list(MCOUNTEREN_OF_PATTERNS)))
        tc.code.extend(_generate_sscofpmf_access_tests(test_data, mode))
        for patterns in SHADOW_PATTERNS.values():
            tc.code.extend(_generate_scountovf_shadow_tests(test_data, mode, of_state, patterns))
        test_chunks.append(test_data.end_test_chunk())
        return test_chunks

    tc = test_data.begin_test_chunk(split_name="inhibit_lo")
    tc.code.extend(_generate_xinh_inhibits_tests(test_data, mode, combos=range(16)))
    test_chunks.append(test_data.end_test_chunk())

    tc = test_data.begin_test_chunk(split_name="inhibit_hi")
    tc.code.extend(_generate_xinh_inhibits_tests(test_data, mode, combos=range(16, 32), toggles=False))
    test_chunks.append(test_data.end_test_chunk())

    tc = test_data.begin_test_chunk(split_name="overflow")
    tc.code.extend(_generate_of_set_on_overflow_tests(test_data, mode))
    tc.code.extend(_generate_overflow_hw_only_tests(test_data, mode))
    tc.code.extend(_generate_lcofip_hw_only_tests(test_data, mode))
    test_chunks.append(test_data.end_test_chunk())

    if mode == "U":  # scountovf is not accessible from U, so the scountovf tests are S-only
        return test_chunks

    for of_name in MCOUNTEREN_OF_PATTERNS:
        tc = test_data.begin_test_chunk(split_name=f"mcounteren_{of_name}")
        tc.code.extend(_generate_scountovf_mcounteren_tests(test_data, mode, boot_of_state(), [of_name]))
        test_chunks.append(test_data.end_test_chunk())

    tc = test_data.begin_test_chunk(split_name="access")
    tc.code.extend(_generate_sscofpmf_access_tests(test_data, mode))
    test_chunks.append(test_data.end_test_chunk())

    for split_name, patterns in SHADOW_PATTERNS.items():
        tc = test_data.begin_test_chunk(split_name=split_name)
        tc.code.extend(_generate_scountovf_shadow_tests(test_data, mode, boot_of_state(), patterns))
        test_chunks.append(test_data.end_test_chunk())
    return test_chunks
