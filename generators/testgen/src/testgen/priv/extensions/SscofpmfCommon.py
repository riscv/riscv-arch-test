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
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk

_FIXED_TSBI_ALIASES = {
    "RVMODEL_MHPMEVENT": "0x323",  # mhpmevent3
    "RVMODEL_MHPMCOUNTER": "0xb03",  # mhpmcounter3
    "scountovf": "0xda0",
}

_MHPMEVENT_RE = re.compile(r"\bCSR_MHPMEVENT(\d+)(H)?\b")
_MHPMCOUNTER_RE = re.compile(r"\bCSR_MHPMCOUNTER(\d+)(H)?\b")


def _resolve_tsbi_csr(instr: str) -> str:
    """Substitute Sscofpmf CSR names/macros with literal hex addresses for tsbi_call()."""
    for macro, hexaddr in _FIXED_TSBI_ALIASES.items():
        instr = instr.replace(macro, hexaddr)

    def _sub_mhpmevent(m: re.Match) -> str:
        n = int(m.group(1))
        base = 0x720 if m.group(2) else 0x320  # ...H = mhpmeventh (RV32 OF-bit high half)
        return hex(base + n)

    def _sub_mhpmcounter(m: re.Match) -> str:
        n = int(m.group(1))
        base = 0xB80 if m.group(2) else 0xB00  # ...H = mhpmcounterh (RV32 counter high half)
        return hex(base + n)

    instr = _MHPMEVENT_RE.sub(_sub_mhpmevent, instr)
    return _MHPMCOUNTER_RE.sub(_sub_mhpmcounter, instr)


_S_ACCESSIBLE_CSRS = ("sip", "sie", "sstatus", "scountovf")


def _csr_access(instr: str, mode: str) -> str:
    """Direct at Sm, and at S for sip/sie/sstatus/scountovf. Everything else via T-SBI."""
    if mode == "Sm":
        return instr
    code = instr.split("#", 1)[0]
    if mode == "S" and any(re.search(rf"\b{name}\b", code) for name in _S_ACCESSIBLE_CSRS):
        return instr
    return tsbi_call(_resolve_tsbi_csr(instr))


# Every T-SBI call runs the M-mode handler, and a call from U is delegated through S
# first, so counting must be inhibited in every mode above the one under test or the
# counter would also count the round trip instead of just the workload.
_HIGHER_MODE_INHIBITS = {"Sm": 0, "S": 1 << 62, "U": (1 << 62) | (1 << 61)}
_HIGHER_MODE_INHIBITS_32 = {mode: bits >> 32 for mode, bits in _HIGHER_MODE_INHIBITS.items()}


def nonzero_not_all_ones(reg: int, scratch: int) -> list[str]:
    """Reduce x{reg} in place to a 0/1 "nonzero and not all-1s" boolean; raw hpmcounter
    values aren't reproducible across the signature/self-check build split."""
    return [
        f"snez x{scratch}, x{reg}          # x{scratch} = (val != 0)",
        f"addi x{reg}, x{reg}, 1            # x{reg} = val + 1 (wraps to 0 iff val was all-1s)",
        f"seqz x{reg}, x{reg}               # x{reg} = (val was all-1s)",
        f"xori x{reg}, x{reg}, 1            # x{reg} = NOT(val was all-1s)",
        f"and x{reg}, x{reg}, x{scratch}    # x{reg} = nonzero AND not all-1s",
    ]


_INHIBIT_MODE_SUFFIX = {"Sm": "mmode", "S": "smode", "U": "umode"}


def _generate_xinh_inhibits_tests(test_data: TestData, priv_mode: str) -> list[str]:
    _INHIBIT_BIT_POS = {"Sm": 62, "S": 61, "U": 60}
    _INHIBIT_PREFIX = {"Sm": "m", "S": "s", "U": "u"}

    covergroup = "Sscofpmf_cg"
    inh_prefix = _INHIBIT_PREFIX[priv_mode]
    coverpoint = f"cp_{inh_prefix}inh_inhibits_{_INHIBIT_MODE_SUFFIX[priv_mode]}"
    inh_bit_pos = _INHIBIT_BIT_POS[priv_mode]
    inh_bit_pos_32 = inh_bit_pos - 32  # RV32 position within mhpmevent3h

    r_val, r_temp = test_data.int_regs.get_registers(2, exclude_regs=[0, 31])

    higher_inhibits = _HIGHER_MODE_INHIBITS[priv_mode]
    higher_inhibits_32 = _HIGHER_MODE_INHIBITS_32[priv_mode]

    lines = [
        comment_banner(
            coverpoint,
            f"{inh_prefix.upper()}INH bit (mhpmevent[{inh_bit_pos}]) inhibits counting in {priv_mode}-mode.\n"
            "Counting stays inhibited in the modes above the one under test, so the counter\n"
            "only ever reflects the workload and never the T-SBI round trip that reaches the\n"
            "M-level counter CSRs.",
        ),
        "",
        _csr_access("csrw mie, zero   # disable interrupts before toggle/sweep", priv_mode),
        "",
    ]
    indent = ""

    # --- individual 0/1 single-bit toggle ---
    for inh_val in [0, 1]:
        binname = f"{inh_prefix}inh_{inh_val}_{priv_mode.lower()}"
        lines.extend(
            [
                f"{indent}# Testcase: {inh_prefix}inh = {inh_val}",
                f"{indent}#if __riscv_xlen == 32",
                f"{indent}LI(x{r_val}, RVMODEL_MHPMEVENT_VAL)",
                f"{indent}{_csr_access(f'csrw RVMODEL_MHPMEVENT, x{r_val}', priv_mode)}",
                f"{indent}LI(x{r_val}, {hex(higher_inhibits_32 | (inh_val << inh_bit_pos_32))})",
                f"{indent}{_csr_access(f'csrw CSR_MHPMEVENT3H, x{r_val}', priv_mode)}",
                f"{indent}#else",
                f"{indent}LI(x{r_val}, RVMODEL_MHPMEVENT_VAL | {hex(higher_inhibits | (inh_val << inh_bit_pos))})",
                f"{indent}{_csr_access(f'csrw RVMODEL_MHPMEVENT, x{r_val}', priv_mode)}",
                f"{indent}#endif",
                f"{indent}{_csr_access('csrw RVMODEL_MHPMCOUNTER, zero', priv_mode)}",
                "",
                f"{indent}LA(x{r_temp}, scratch)",
                f"{indent}RVMODEL_MHPMEVENT_CODE(x{r_temp}, x{r_val})",
                "",
                f"{indent}{test_data.add_testcase(binname, coverpoint, covergroup)}",
                f"{indent}{_csr_access(f'csrr x{r_temp}, RVMODEL_MHPMCOUNTER', priv_mode)}",
                # Normalize to nonzero/zero: counter must be nonzero iff xinh=0, regardless of
                # how many events a given model counted.
                f"{indent}snez x{r_temp}, x{r_temp}",
                f"{indent}{write_sigupd(r_temp, test_data)}",
                "",
            ]
        )

    lines.extend(
        [
            f"{indent}LI(x{r_val}, RVMODEL_MHPMEVENT_VAL)",
            f"{indent}{_csr_access(f'csrw RVMODEL_MHPMEVENT, x{r_val}', priv_mode)}",
            f"{indent}#if __riscv_xlen == 32",
            f"{indent}{_csr_access('csrw CSR_MHPMEVENT3H, zero', priv_mode)}",
            f"{indent}#endif",
            "",
        ]
    )

    r_hval = test_data.int_regs.get_register(exclude_regs=[0, 31])
    lines.append(f"{indent}#if __riscv_xlen == 32")
    for combo in range(32):
        binname = f"xinh_combo_{combo:05b}_{priv_mode.lower()}_rv32"
        lines.extend(
            [
                f"{indent}LI(x{r_val}, RVMODEL_MHPMEVENT_VAL)",
                f"{indent}{_csr_access(f'csrw RVMODEL_MHPMEVENT, x{r_val}', priv_mode)}",
                f"{indent}LI(x{r_hval}, {combo} << 26)",  # 58-32 = 26
                f"{indent}{_csr_access(f'csrw CSR_MHPMEVENT3H, x{r_hval}', priv_mode)}",
                f"{indent}{_csr_access('csrw RVMODEL_MHPMCOUNTER, zero', priv_mode)}",
                "",
                f"{indent}{test_data.add_testcase(binname, coverpoint, covergroup)}",
                f"{indent}{_csr_access(f'csrr x{r_temp}, CSR_MHPMEVENT3H', priv_mode)}",
                # VSINH/VUINH are hardwired 0 on Sail (no H support), so mask them out of the checked value.
                f"{indent}LI(x{r_hval}, 0xF3FFFFFF)   # clear bits 27:26 (VSINH/VUINH) -- H unsupported by Sail",
                f"{indent}and x{r_temp}, x{r_temp}, x{r_hval}",
                f"{indent}{write_sigupd(r_temp, test_data)}",
                "",
            ]
        )
    lines.append(f"{indent}#else")
    for combo in range(32):
        binname = f"xinh_combo_{combo:05b}_{priv_mode.lower()}_rv64"
        lines.extend(
            [
                f"{indent}LI(x{r_val}, RVMODEL_MHPMEVENT_VAL | ({combo} << 58))",
                f"{indent}{_csr_access(f'csrw RVMODEL_MHPMEVENT, x{r_val}', priv_mode)}",
                f"{indent}{_csr_access('csrw RVMODEL_MHPMCOUNTER, zero', priv_mode)}",
                "",
                f"{indent}{test_data.add_testcase(binname, coverpoint, covergroup)}",
                f"{indent}{_csr_access(f'csrr x{r_temp}, RVMODEL_MHPMEVENT', priv_mode)}",
                # VSINH/VUINH are hardwired 0 on Sail (no H support), so mask them out of the checked value.
                f"{indent}LI(x{r_val}, 0xF3FFFFFFFFFFFFFF)   # clear bits 59:58 (VSINH/VUINH) -- H unsupported by Sail",
                f"{indent}and x{r_temp}, x{r_temp}, x{r_val}",
                f"{indent}{write_sigupd(r_temp, test_data)}",
                "",
            ]
        )
    lines.append(f"{indent}#endif")
    lines.extend(
        [
            f"{indent}{_csr_access('csrw RVMODEL_MHPMEVENT, zero', priv_mode)}",
            f"{indent}#if __riscv_xlen == 32",
            f"{indent}{_csr_access('csrw CSR_MHPMEVENT3H, zero', priv_mode)}",
            f"{indent}#endif",
            f"{indent}{_csr_access('csrw RVMODEL_MHPMCOUNTER, zero', priv_mode)}",
            "",
        ]
    )
    test_data.int_regs.return_registers([r_hval])
    test_data.int_regs.return_registers([r_val, r_temp])
    return lines


def write_event_pattern(r_val: int, r_hval: int, inhibit_pattern: int, priv_mode: str) -> list[str]:
    """Write RVMODEL_MHPMEVENT_VAL with the MINH/SINH/UINH/VSINH/VUINH pattern at bits
    62:58, OF=0. LI truncates to 32 bits on RV32, so the pattern never reaches the event
    high half through the RV64 form -- split the write across both halves there."""
    return [
        "#if __riscv_xlen == 32",
        f"LI(x{r_val}, RVMODEL_MHPMEVENT_VAL)",
        _csr_access(f"csrw RVMODEL_MHPMEVENT, x{r_val}", priv_mode),
        f"LI(x{r_hval}, {inhibit_pattern} << 26)   # 58-32 = 26",
        _csr_access(f"csrw CSR_MHPMEVENT3H, x{r_hval}", priv_mode),
        "#else",
        f"LI(x{r_val}, RVMODEL_MHPMEVENT_VAL | ({inhibit_pattern} << 58))   # OF starts at 0",
        _csr_access(f"csrw RVMODEL_MHPMEVENT, x{r_val}", priv_mode),
        "#endif",
    ]


def write_counter_all_ones(r_temp: int, priv_mode: str) -> list[str]:
    """Preload the logical 64-bit counter to all-1s so the next counted event overflows.
    On RV32 the counter is really two 32-bit halves; the high half must also be set or
    the 64-bit counter can't wrap."""
    return [
        f"LI(x{r_temp}, -1)",
        _csr_access(f"csrw RVMODEL_MHPMCOUNTER, x{r_temp}   # all 1s -> next count overflows", priv_mode),
        "#if __riscv_xlen == 32",
        _csr_access(f"csrw CSR_MHPMCOUNTER3H, x{r_temp}   # high half must also be all 1s", priv_mode),
        "#endif",
    ]


def prime_counter_overflow(r_val: int, r_hval: int, r_temp: int, r_addr: int, priv_mode: str) -> list[str]:
    """Overflow RVMODEL_MHPMCOUNTER (OF 0 -> 1, raising LCOFIP). The counter is left at
    all 1s, so one counted event wraps it; the workload is what supplies that event on a
    model that counts. These coverpoints require an all-zero inhibit pattern, so below M
    the T-SBI round trip that writes the counter is counted too and may itself supply the
    wrapping event -- either way OF is set and LCOFIP pends before the sample point."""
    return [
        *write_event_pattern(r_val, r_hval, 0, priv_mode),
        *write_counter_all_ones(r_temp, priv_mode),
        f"LA(x{r_addr}, scratch)",
        f"RVMODEL_MHPMEVENT_CODE(x{r_addr}, x{r_val})",
    ]


# MINH/SINH/UINH/VSINH/VUINH patterns crossed by mhpmevent_inhibits_pattern_state:
# none set, M+S+U set, and each of MINH/SINH/UINH alone.
_INHIBIT_PATTERNS = [
    0b00000,
    0b11100,
    0b10000,
    0b01000,
    0b00100,
]


def _generate_of_set_on_overflow_tests(test_data: TestData, priv_mode: str) -> list[str]:
    """cp_of_set_on_overflow: OF bit is set when hpmcounter overflows."""
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_of_set_on_overflow"
    ######################################

    r_val, r_temp, r_lcofip, r_addr, r_bool, r_hval = test_data.int_regs.get_registers(6, exclude_regs=[0, 31])

    def read_event_config_bits() -> list[str]:
        """Read back OF + the 5-bit inhibit/event-index field into x{r_temp}, masked to
        just those bits. On RV32 they live in mhpmevent3h[31:26] (LI truncates to 32
        bits, so the RV64 form can't reach them there); on RV64 they're
        mhpmevent3[63:58], whose low 58 bits carry uncontrolled noise that (like
        hpmcounter) drifts with total retired-instruction count and so differs between
        the -DSIGNATURE reference pass and the final self-checking pass -- mask those
        out before signing off, since comparing them via write_sigupd is not
        reproducible."""
        return [
            "#if __riscv_xlen == 32",
            _csr_access(f"csrr x{r_temp}, CSR_MHPMEVENT3H   # sample point for mhpmevent_of", priv_mode),
            f"LI(x{r_bool}, 0xFC000000)   # keep only OF + the 5-bit inhibit field (bits 31:26)",
            f"and x{r_temp}, x{r_temp}, x{r_bool}",
            "#else",
            _csr_access(f"csrr x{r_temp}, RVMODEL_MHPMEVENT   # sample point for mhpmevent_of", priv_mode),
            f"LI(x{r_bool}, 0xFC00000000000000)   # keep only OF + the 5-bit inhibit field (bits 63:58)",
            f"and x{r_temp}, x{r_temp}, x{r_bool}",
            "#endif",
        ]

    # S reaches LCOFIP through its own sip/sie; Sm (and U without S) through mip/mie.
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

    for inhibit_pattern in _INHIBIT_PATTERNS:
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
                    _csr_access("csrw sip, zero   # clear LCOFIP", priv_mode),
                    _csr_access("csrw sie, zero   # disable interrupts (clear LCOFIE)", priv_mode),
                    "#else",
                    _csr_access("csrw mip, zero   # clear LCOFIP", priv_mode),
                    _csr_access("csrw mie, zero   # disable interrupts (clear LCOFIE)", priv_mode),
                    "#endif",
                ]
            )
        else:
            lines.extend(
                [
                    _csr_access(f"csrw {pending_csr}, zero   # clear LCOFIP", priv_mode),
                    _csr_access(f"csrw {enable_csr}, zero   # disable interrupts (clear LCOFIE)", priv_mode),
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
                    f"csrr x{r_temp}, RVMODEL_MHPMCOUNTER   # sample point for hpmcounter_nonzero/non-all-1s",
                    *nonzero_not_all_ones(r_temp, r_bool),
                    write_sigupd(r_temp, test_data),
                    "",
                    f"RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})   # wait for RVMODEL_INTERRUPT_LATENCY",
                    f"csrr x{r_lcofip}, {lcofip_csr}   # sample point for lcofip",
                    write_sigupd(r_lcofip, test_data),
                ]
            )

        else:
            mhpmcounter_read = f"csrr x{r_temp}, RVMODEL_MHPMCOUNTER   # sample point for hpmcounter_nonzero/non-all-1s"

            lines.extend(
                [
                    f"# RVMODEL_MHPMEVENT/RVMODEL_MHPMCOUNTER writes go via T-SBI from {priv_mode}-mode, per spec",
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
                    _csr_access(mhpmcounter_read, priv_mode),
                    *nonzero_not_all_ones(r_temp, r_bool),
                    write_sigupd(r_temp, test_data),
                    "",
                    f"RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})   # wait for RVMODEL_INTERRUPT_LATENCY",
                ]
            )

            if priv_mode == "U":
                lines.extend(
                    [
                        "#ifdef S_SUPPORTED",
                        _csr_access(f"csrr x{r_lcofip}, sip   # sample point for lcofip", priv_mode),
                        "#else",
                        _csr_access(f"csrr x{r_lcofip}, mip   # sample point for lcofip", priv_mode),
                        "#endif",
                        write_sigupd(r_lcofip, test_data),
                    ]
                )
            else:
                lines.extend(
                    [
                        _csr_access(f"csrr x{r_lcofip}, {lcofip_csr}   # sample point for lcofip", priv_mode),
                        write_sigupd(r_lcofip, test_data),
                    ]
                )

    test_data.int_regs.return_registers([r_val, r_temp, r_lcofip, r_addr, r_bool, r_hval])

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
            "A software write of RVMODEL_MHPMCOUNTER, however extreme, must never set OF --\n"
            f"only a hardware counter increment through overflow may. mode = {priv_mode}.",
        ),
        "",
        _csr_access("csrw mie, zero   # disable interrupts", priv_mode),
        _csr_access("csrw RVMODEL_MHPMEVENT, zero", priv_mode),
        "",
    ]

    for step_name, load_val in [("all_1s", -1), ("all_0s", 0)]:
        binname = f"overflow_hw_only_{priv_mode.lower()}_{step_name}"
        lines.extend(
            [
                f"# Testcase: software write RVMODEL_MHPMCOUNTER = {step_name}, mode = {priv_mode}",
                f"LI(x{r_val}, {load_val})",
                _csr_access(f"csrw RVMODEL_MHPMCOUNTER, x{r_val}", priv_mode),
                "",
                test_data.add_testcase(binname, coverpoint, covergroup),
                "#if __riscv_xlen == 32",
                _csr_access(f"csrr x{r_of}, CSR_MHPMEVENT3H   # sample point -- OF must read 0", priv_mode),
                f"srli x{r_of}, x{r_of}, 31   # OF (bit 31 of the H-half) -> bit 0",
                "#else",
                _csr_access(f"csrr x{r_of}, RVMODEL_MHPMEVENT   # sample point -- OF must read 0", priv_mode),
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
        """Software-set/clear OF directly. LI truncates 1<<63 to 0 on RV32, so OF
        (mhpmevent3h[31] there) needs its own RV32 form."""
        return [
            "#if __riscv_xlen == 32",
            f"LI(x{r_val}, {hex(1 << 31)})",
            _csr_access(f"{op} CSR_MHPMEVENT3H, x{r_val}   # {desc}", priv_mode),
            "#else",
            f"LI(x{r_val}, {hex(1 << 63)})",
            _csr_access(f"{op} RVMODEL_MHPMEVENT, x{r_val}   # {desc}", priv_mode),
            "#endif",
        ]

    def readback(expect_desc: str) -> list[str]:
        """LCOFIP readback per testplan: sip for S (or U w/ S_SUPPORTED),
        mip for Sm (or U w/o S_SUPPORTED). Only LCOFIP goes to the signature."""
        if priv_mode == "Sm":
            read = [_csr_access(f"csrr x{r_temp}, mip   # sample point -- LCOFIP {expect_desc}", priv_mode)]
        elif priv_mode == "S":
            read = [_csr_access(f"csrr x{r_temp}, sip   # sample point -- LCOFIP {expect_desc}", priv_mode)]
        else:  # priv_mode == "U": sip if S_SUPPORTED, else mip
            read = [
                "#ifdef S_SUPPORTED",
                _csr_access(f"csrr x{r_temp}, sip   # sample point -- LCOFIP {expect_desc}", priv_mode),
                "#else",
                _csr_access(f"csrr x{r_temp}, mip   # sample point -- LCOFIP {expect_desc}", priv_mode),
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
        _csr_access("csrw mie, zero   # disable interrupts", priv_mode),
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

    indent = ""

    for of_name, of_bit_fn in of_patterns.items():
        r_of_bit = test_data.int_regs.get_register(exclude_regs=[0, 31])

        lines.append(f"{indent}#if __riscv_xlen == 32")
        lines.append(f"{indent}LI(x{r_of_bit}, {1 << 31})   # OF bit (bit 31 of mhpmeventh, RV32)")
        lines.append(f"{indent}# --- Write OF pattern: {of_name} across mhpmeventh3..31 (RV32) ---")
        for i, csr_name in enumerate(MHPMEVENTH_CSRS):
            op = "csrs" if of_bit_fn(i) else "csrc"
            lines.append(
                f"{indent}"
                + _csr_access(
                    f"{op} {csr_name}, x{r_of_bit}   # {'set' if of_bit_fn(i) else 'clear'} OF bit -- {csr_name}", mode
                )
            )
        lines.append(f"{indent}#else")
        lines.append(f"{indent}LI(x{r_of_bit}, {1 << 63})   # OF bit (bit 63 of mhpmevent, RV64)")
        lines.append(f"{indent}# --- Write OF pattern: {of_name} across mhpmevent3..31 (RV64) ---")
        for i, csr_name in enumerate(MHPMEVENT_CSRS):
            op = "csrs" if of_bit_fn(i) else "csrc"
            lines.append(
                f"{indent}"
                + _csr_access(
                    f"{op} {csr_name}, x{r_of_bit}   # {'set' if of_bit_fn(i) else 'clear'} OF bit -- {csr_name}", mode
                )
            )
        lines.append(f"{indent}#endif")
        lines.append("")

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
            lines.append(_csr_access(f"csrr x{r_scountovf}, scountovf   # sample point", mode))
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
                        f"{indent}{_csr_access(f'csrw mcounteren, x{r_mcounteren}', mode)}",
                        f"{indent}{test_data.add_testcase(binname, walk_coverpoint, covergroup)}",
                        f"{indent}{_csr_access(f'csrr x{r_scountovf}, scountovf   # sample point', mode)}",
                        f"{indent}{write_sigupd(r_scountovf, test_data)}",
                        "",
                    ]
                )

            for bit in range(3, 32):
                binname = f"mcounteren_walk_bit_{bit}"
                lines.extend(
                    [
                        f"{indent}LI(x{r_mcounteren}, {1 << bit})",
                        f"{indent}{_csr_access(f'csrw mcounteren, x{r_mcounteren}', mode)}",
                        f"{indent}{test_data.add_testcase(binname, walk_coverpoint, covergroup)}",
                        f"{indent}{_csr_access(f'csrr x{r_scountovf}, scountovf   # sample point', mode)}",
                        f"{indent}{write_sigupd(r_scountovf, test_data)}",
                        "",
                    ]
                )

            lines.append(f"{indent}{_csr_access('csrw mcounteren, zero', mode)}")
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

    if mode == "Sm":  # mhpmeventh3..31 sweep is M-mode only per spec
        lines.append("#if __riscv_xlen == 32")
        for n in range(3, 32):
            emit_accesses(f"CSR_MHPMEVENT{n}H")
        lines.append("#endif")

    test_data.int_regs.return_registers([r_val])
    return lines


def _generate_scountovf_shadow_tests(test_data: TestData, priv_mode: str) -> list[str]:
    if priv_mode == "U":
        return []

    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_scountovf_shadow"
    ######################################

    MHPMEVENTH_CSRS = [f"CSR_MHPMEVENT{n}H" for n in range(3, 32)]  # RV32: 29 registers
    MHPMEVENT_CSRS = [f"CSR_MHPMEVENT{n}" for n in range(3, 32)]  # RV64: 29 registers

    indent = ""

    lines = [
        comment_banner(
            coverpoint,
            f"scountovf shadows OF bits of mhpmevent3:31, mode = {priv_mode}.\n"
            "mcounteren = all 1s (fixed for this coverpoint). Write patterns to\n"
            "mhpmevent3...31.OF: all 0s, all 1s, walking 1s. Read scountovf.\n",
        ),
        "",
    ]

    r_mcounteren = test_data.int_regs.get_register(exclude_regs=[0, 31])
    lines.extend(
        [
            f"{indent}LI(x{r_mcounteren}, -1)",
            f"{indent}{_csr_access(f'csrw mcounteren, x{r_mcounteren}   # mcounteren = all 1s (fixed for this coverpoint)', priv_mode)}",
            "",
        ]
    )
    test_data.int_regs.return_registers([r_mcounteren])

    def emit_pattern(pattern_name: str, of_bit_fn: Callable[[int], int]) -> None:
        r_of_bit, r_scountovf = test_data.int_regs.get_registers(2, exclude_regs=[0, 31])

        lines.append(f"{indent}#if __riscv_xlen == 32")
        lines.append(f"{indent}LI(x{r_of_bit}, {1 << 31})   # OF bit (bit 31 of mhpmeventh, RV32)")
        lines.append(f"{indent}# --- Write OF pattern: {pattern_name} across mhpmeventh3..31 (RV32) ---")
        for i, csr_name in enumerate(MHPMEVENTH_CSRS):
            set_bit = of_bit_fn(i)
            op = "csrs" if set_bit else "csrc"
            action = "set" if set_bit else "clear"
            instr = f"{op} {csr_name}, x{r_of_bit}   # {action} OF bit -- {csr_name}"
            lines.append(f"{indent}{_csr_access(instr, priv_mode)}")
        lines.append(f"{indent}#else")
        lines.append(f"{indent}LI(x{r_of_bit}, {1 << 63})   # OF bit (bit 63 of mhpmevent, RV64)")
        lines.append(f"{indent}# --- Write OF pattern: {pattern_name} across mhpmevent3..31 (RV64) ---")
        for i, csr_name in enumerate(MHPMEVENT_CSRS):
            set_bit = of_bit_fn(i)
            op = "csrs" if set_bit else "csrc"
            action = "set" if set_bit else "clear"
            instr = f"{op} {csr_name}, x{r_of_bit}   # {action} OF bit -- {csr_name}"
            lines.append(f"{indent}{_csr_access(instr, priv_mode)}")
        lines.append(f"{indent}#endif")
        lines.append("")

        test_data.int_regs.return_registers([r_of_bit])

        binname = f"scountovf_shadow_{priv_mode.lower()}_{pattern_name}"
        lines.append(f"{indent}{test_data.add_testcase(binname, coverpoint, covergroup)}")
        lines.append(
            f"{indent}{_csr_access(f'csrr x{r_scountovf}, scountovf   # sample point -- must match OF pattern', priv_mode)}"
        )
        lines.append(f"{indent}{write_sigupd(r_scountovf, test_data)}")
        lines.append("")

        test_data.int_regs.return_registers([r_scountovf])

    # --- all_0s: every OF bit clear ---
    emit_pattern("all_0s", lambda i: 0)

    # --- all_1s: every OF bit set ---
    emit_pattern("all_1s", lambda i: 1)

    # --- walking_1s: exactly one OF bit set at a time, across all 29 positions ---
    for walk_idx in range(29):
        emit_pattern(f"walking1_{walk_idx}", lambda i, w=walk_idx: 1 if i == w else 0)

    return lines


def generate_sscofpmf_suite(test_data: TestData, mode: str) -> list[TestChunk]:
    """Assemble the full Sscofpmf suite for ``mode`` ("Sm"/"S"/"U") as a test chunk."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()
    tc.code.extend(_generate_xinh_inhibits_tests(test_data, mode))
    tc.code.extend(_generate_of_set_on_overflow_tests(test_data, mode))
    tc.code.extend(_generate_overflow_hw_only_tests(test_data, mode))
    tc.code.extend(_generate_lcofip_hw_only_tests(test_data, mode))
    tc.code.extend(_generate_scountovf_mcounteren_tests(test_data, mode))
    tc.code.extend(_generate_sscofpmf_access_tests(test_data, mode))
    tc.code.extend(_generate_scountovf_shadow_tests(test_data, mode))
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
