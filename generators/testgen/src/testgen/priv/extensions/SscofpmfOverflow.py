##################################
# priv/extensions/SscofpmfOverflow.py
# Written by: Ayesha Anwar, ayesha.anwaar2005@gmail.com
# Sscofpmf counter-overflow (OF and LCOFIP) test-case generators.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Sscofpmf OF and LCOFIP tests driven by a counter overflow, called with priv_mode in {"Sm", "S", "U"}."""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.priv.extensions.SscofpmfCommon import (
    EVENT_VAL_HI,
    clear_lcofip,
    counted_since_all_ones,
    csr_access,
    write_counter_all_ones,
    write_event_pattern,
)

# MINH/SINH/UINH/VSINH/VUINH patterns crossed by mhpmevent_inhibits_pattern_state:
# none set, M+S+U set, and each of MINH/SINH/UINH alone.
_INHIBIT_PATTERNS = [
    0b00000,
    0b11100,
    0b10000,
    0b01000,
    0b00100,
]


def generate_of_set_on_overflow_tests(test_data: TestData, priv_mode: str) -> list[str]:
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
            csr_access(f"csrr x{r_temp}, CSR_MHPMEVENT3H   # sample point for mhpmevent_of", priv_mode),
            f"LI(x{r_bool}, 0xFC000000)   # keep only OF + the 5-bit inhibit field (bits 31:26)",
            f"and x{r_temp}, x{r_temp}, x{r_bool}",
            "#else",
            csr_access(f"csrr x{r_temp}, RVMODEL_MHPMEVENT   # sample point for mhpmevent_of", priv_mode),
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
                    f"csrr x{r_temp}, RVMODEL_MHPMCOUNTER   # sample point: did the counter move off all 1s?",
                    *counted_since_all_ones(r_temp),
                    write_sigupd(r_temp, test_data),
                    "",
                    f"RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})   # wait for RVMODEL_INTERRUPT_LATENCY",
                    f"csrr x{r_lcofip}, {lcofip_csr}   # sample point for lcofip",
                    write_sigupd(r_lcofip, test_data),
                ]
            )

        else:
            mhpmcounter_read = f"csrr x{r_temp}, RVMODEL_MHPMCOUNTER   # sample point: did the counter move off all 1s?"

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

    # OF already 1: the overflow must leave OF set and must not request LCOFI
    # (norm:count_overflow_interrupt). OF is set together with the event code, before
    # the counter is preset, so an overflow caused by the T-SBI round trip below M
    # cannot raise LCOFIP either.
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
            f"# Testcase: mode = {priv_mode}, inhibit pattern = 00000, OF initial = 1",
            csr_access("csrw mie, zero   # disable interrupts", priv_mode),
            "#if __riscv_xlen == 32",
            f"LI(x{r_val}, RVMODEL_MHPMEVENT_VAL)",
            csr_access(f"csrw RVMODEL_MHPMEVENT, x{r_val}", priv_mode),
            f"LI(x{r_hval}, {EVENT_VAL_HI} | {hex(1 << 31)})   # OF = 1, no inhibits",
            csr_access(f"csrw CSR_MHPMEVENT3H, x{r_hval}", priv_mode),
            "#else",
            f"LI(x{r_val}, RVMODEL_MHPMEVENT_VAL | {hex(1 << 63)})   # OF = 1, no inhibits",
            csr_access(f"csrw RVMODEL_MHPMEVENT, x{r_val}", priv_mode),
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
                f"csrr x{r_temp}, RVMODEL_MHPMCOUNTER   # sample point: did the counter move off all 1s?", priv_mode
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


def generate_overflow_hw_only_tests(test_data: TestData, priv_mode: str) -> list[str]:
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
        csr_access("csrw mie, zero   # disable interrupts", priv_mode),
        csr_access("csrw RVMODEL_MHPMEVENT, zero", priv_mode),
        "#if __riscv_xlen == 32",
        csr_access("csrw CSR_MHPMEVENT3H, zero   # clear OF and xINH left by earlier tests", priv_mode),
        "#endif",
        # A real overflow in the previous tests leaves LCOFIP pending on a counting hart.
        *clear_lcofip(r_val, priv_mode),
        "",
    ]

    for step_name, load_val in [("all_1s", -1), ("all_0s", 0)]:
        binname = f"overflow_hw_only_{priv_mode.lower()}_{step_name}"
        lines.extend(
            [
                f"# Testcase: software write RVMODEL_MHPMCOUNTER = {step_name}, mode = {priv_mode}",
                f"LI(x{r_val}, {load_val})",
                csr_access(f"csrw RVMODEL_MHPMCOUNTER, x{r_val}", priv_mode),
                "",
                test_data.add_testcase(binname, coverpoint, covergroup),
                "#if __riscv_xlen == 32",
                csr_access(f"csrr x{r_of}, CSR_MHPMEVENT3H   # sample point -- OF must read 0", priv_mode),
                f"srli x{r_of}, x{r_of}, 31   # OF (bit 31 of the H-half) -> bit 0",
                "#else",
                csr_access(f"csrr x{r_of}, RVMODEL_MHPMEVENT   # sample point -- OF must read 0", priv_mode),
                f"srli x{r_of}, x{r_of}, 63   # OF (bit 63) -> bit 0",
                "#endif",
                write_sigupd(r_of, test_data),
                "",
            ]
        )

    test_data.int_regs.return_registers([r_val, r_of])
    return lines


def generate_lcofip_hw_only_tests(test_data: TestData, priv_mode: str) -> list[str]:
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
            csr_access(f"{op} CSR_MHPMEVENT3H, x{r_val}   # {desc}", priv_mode),
            "#else",
            f"LI(x{r_val}, {hex(1 << 63)})",
            csr_access(f"{op} RVMODEL_MHPMEVENT, x{r_val}   # {desc}", priv_mode),
            "#endif",
        ]

    def readback(expect_desc: str) -> list[str]:
        """LCOFIP readback per testplan: sip for S (or U w/ S_SUPPORTED),
        mip for Sm (or U w/o S_SUPPORTED). Only LCOFIP goes to the signature."""
        if priv_mode == "Sm":
            read = [csr_access(f"csrr x{r_temp}, mip   # sample point -- LCOFIP {expect_desc}", priv_mode)]
        elif priv_mode == "S":
            read = [csr_access(f"csrr x{r_temp}, sip   # sample point -- LCOFIP {expect_desc}", priv_mode)]
        else:  # priv_mode == "U": sip if S_SUPPORTED, else mip
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
        # A real overflow earlier leaves LCOFIP pending on a counting hart; clear it so
        # the readbacks below show whether the software OF write raised it.
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
