##################################
# priv/extensions/SscofpmfS.py
# Written by: Ayesha Anwar, ayesha.anwaar2005@gmail.com
# Sscofpmf S-mode test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

from collections.abc import Callable

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.SscofpmfCommon import _csr_access, _scountovf_access, generate_sscofpmf_suite
from testgen.priv.registry import add_priv_test_generator


def _generate_lcofi_sip_s_tests(test_data: TestData) -> list[str]:
    """cp_lcofi_sip_s: Interrupt from sip.LCOFI, running in S-mode.

    sstatus.SIE=1 (fixed), mideleg.LCOFI=1, sweep sie.LCOFIE x sip.LCOFIP.
    sie/sip are restricted views of mie/mip, so setup happens directly on
    mie/mip/mstatus in M-mode (matches InterruptsS/U pattern) before
    switching down, to avoid nested traps mid-switch.
    """
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_lcofi_sip_s"
    ######################################

    LCOFI_BIT = 1 << 13  # mip/mie/sip/sie bit 13
    SIE_BIT = 0x2  # mstatus/sstatus bit 1

    r_val, r_temp = test_data.int_regs.get_registers(2, exclude_regs=[0, 31])

    lines = [
        comment_banner(
            coverpoint,
            "Interrupt from sip.LCOFI, running in S-mode.\n"
            "sstatus.SIE=1 (fixed), mideleg.LCOFI=1, sweep sie.LCOFIE x sip.LCOFIP.\n"
            "sie/sip alias mie/mip bit 13, so setup is direct M-mode CSR writes\n"
            "(matches InterruptsS/U pattern) before switching to S-mode.",
        ),
        "",
        "# === M-MODE SETUP ===",
        "csrw mip, zero      # clear all pending",
        "csrw mie, zero      # disable all interrupts",
        f"LI(x{r_val}, {hex(LCOFI_BIT)})",
        f"csrs mideleg, x{r_val}   # delegate LCOFI to S-mode",
        f"csrsi mstatus, {hex(SIE_BIT)}   # mstatus.SIE = 1 (== sstatus.SIE)",
    ]

    for lcofie in [0, 1]:
        for lcofip in [0, 1]:
            binname = f"lcofi_sip_s_lcofie_{lcofie}_lcofip_{lcofip}"
            lines.extend(
                [
                    "",
                    f"# Testcase: sie.LCOFIE={lcofie}, sip.LCOFIP={lcofip}",
                    f"LI(x{r_temp}, {hex(LCOFI_BIT)})",
                    f"{'csrs' if lcofie else 'csrc'} mie, x{r_temp}   # sie.LCOFIE = {lcofie}",
                    f"{'csrs' if lcofip else 'csrc'} mip, x{r_temp}   # sip.LCOFIP = {lcofip}",
                    "",
                    test_data.add_testcase(binname, coverpoint, covergroup),
                    "RVTEST_GOTO_LOWER_MODE Smode",
                    f"    RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})",
                    "RVTEST_GOTO_MMODE",
                    "",
                    f"csrc mip, x{r_temp}   # clear LCOFIP for next iteration",
                    f"csrc mie, x{r_temp}   # clear LCOFIE for next iteration",
                ]
            )

    lines.extend(
        [
            "",
            "# === M-MODE CLEANUP ===",
            f"csrc mideleg, x{r_val}   # remove delegation",
            f"csrci mstatus, {hex(SIE_BIT)}   # mstatus.SIE = 0",
        ]
    )

    test_data.int_regs.return_registers([r_val, r_temp])
    return lines


def _generate_lcofip_hw_only_s_tests(test_data: TestData) -> list[str]:
    """cp_lcofip_hw_only: counter overflow (LCOFIP) only results from hardware
    increments of counter registers, not software writes to OF -- S-mode only.

    Software-setting RVMODEL_MHPMEVENT's OF bit directly must NOT assert
    mip.LCOFIP; only a genuine hardware wraparound should. All CSR access
    from S-mode goes through SBI per _csr_access, matching cp_sscofpmf_access.
    """
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_lcofip_hw_only"
    ######################################

    OF_BIT = 1 << 63  # RVMODEL_MHPMEVENT bit 63

    r_val, r_temp = test_data.int_regs.get_registers(2, exclude_regs=[0, 31])

    lines = [
        comment_banner(
            coverpoint,
            "Counter overflow (LCOFIP) only results from hardware increments\n"
            "of counter registers -- S-mode only. Software-set/clear the OF bit\n"
            "in RVMODEL_MHPMEVENT directly (no HW increments in between) and\n"
            "confirm mip.LCOFIP stays 0 in both cases. All access from S-mode\n"
            "routed via SBI (RVMODEL_MHPMEVENT and mip are M-mode CSRs).",
        ),
        "",
        "# === M-MODE SETUP ===",
        "csrw mip, zero   # clear pending",
        "csrw mie, zero   # disable interrupts",
        "RVTEST_GOTO_LOWER_MODE Smode",
        f"    LI(x{r_val}, {hex(OF_BIT)})",
        "",
        "    # Testcase: software-set OF bit directly (no HW increment)",
        f"    {_csr_access(f'csrs RVMODEL_MHPMEVENT, x{r_val}   # software-set OF bit', 'S')}",
        "",
        f"    {test_data.add_testcase('lcofip_hw_only_s_set_of', coverpoint, covergroup)}",
        f"    RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})   # wait for RVMODEL_INTERRUPT_LATENCY",
        f"    {_csr_access(f'csrr x{r_temp}, mip   # sample point -- LCOFIP must read 0', 'S')}",
        "",
        "    # Testcase: software-clear OF bit directly (no HW increment)",
        f"    {_csr_access(f'csrc RVMODEL_MHPMEVENT, x{r_val}   # software-clear OF bit', 'S')}",
        "",
        f"    {test_data.add_testcase('lcofip_hw_only_s_clear_of', coverpoint, covergroup)}",
        f"    RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})   # wait for RVMODEL_INTERRUPT_LATENCY",
        f"    {_csr_access(f'csrr x{r_temp}, mip   # sample point -- LCOFIP must still read 0', 'S')}",
        "RVTEST_GOTO_MMODE",
    ]

    test_data.int_regs.return_registers([r_val, r_temp])
    return lines


def _generate_scountovf_shadow_s_tests(test_data: TestData) -> list[str]:
    """cp_scountovf_shadow: scountovf shadows OF bits of mhpmevent3:31 -- S-mode only.

    From S-mode: mcounteren = all 1s (fixed). Write OF patterns
    (all_0s, all_1s, walking_1s) across mhpmevent3...31.OF, read scountovf,
    confirm it matches the 1s in the OF fields.
    """
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_scountovf_shadow"
    ######################################

    MHPMEVENTH_CSRS = [f"CSR_MHPMEVENT{n}H" for n in range(3, 32)]  # RV32: 29 registers
    MHPMEVENT_CSRS = [f"CSR_MHPMEVENT{n}" for n in range(3, 32)]  # RV64: 29 registers

    r_mcounteren = test_data.int_regs.get_register(exclude_regs=[0, 31])

    lines = [
        comment_banner(
            coverpoint,
            "scountovf shadows OF bits of mhpmevent3:31 -- S-mode only.\n"
            "mcounteren = all 1s (fixed, set once via SBI). Write OF patterns\n"
            "(all_0s, all_1s, walking_1s) across mhpmevent3...31.OF, read\n"
            "scountovf, confirm it matches the 1s in the OF fields.\n"
            "mhpmevent writes go via SBI from S-mode; scountovf is read\n"
            "natively (S-mode-accessible CSR, addr[9:8]=01).",
        ),
        "",
        "RVTEST_GOTO_LOWER_MODE Smode",
        f"    LI(x{r_mcounteren}, -1)",
        f"    {_csr_access(f'csrw mcounteren, x{r_mcounteren}   # mcounteren = all 1s (fixed for this coverpoint)', 'S')}",
        "",
    ]

    test_data.int_regs.return_registers([r_mcounteren])

    def emit_pattern(pattern_name: str, of_bit_fn: Callable[[int], int]) -> None:
        r_of_bit, r_scountovf = test_data.int_regs.get_registers(2, exclude_regs=[0, 31])

        lines.append("    #if __riscv_xlen == 32")
        lines.append(f"    LI(x{r_of_bit}, {1 << 31})   # OF bit (bit 31 of mhpmeventh, RV32)")
        lines.append(f"    # --- Write OF pattern: {pattern_name} across mhpmeventh3..31 (RV32) ---")
        for i, csr_name in enumerate(MHPMEVENTH_CSRS):
            set_bit = of_bit_fn(i)
            op = "csrs" if set_bit else "csrc"
            action = "set" if set_bit else "clear"
            instr = f"{op} {csr_name}, x{r_of_bit}   # {action} OF bit -- {csr_name}"
            lines.append(f"    {_csr_access(instr, 'S')}")
        lines.append("    #else")
        lines.append(f"    LI(x{r_of_bit}, {1 << 63})   # OF bit (bit 63 of mhpmevent, RV64)")
        lines.append(f"    # --- Write OF pattern: {pattern_name} across mhpmevent3..31 (RV64) ---")
        for i, csr_name in enumerate(MHPMEVENT_CSRS):
            set_bit = of_bit_fn(i)
            op = "csrs" if set_bit else "csrc"
            action = "set" if set_bit else "clear"
            instr = f"{op} {csr_name}, x{r_of_bit}   # {action} OF bit -- {csr_name}"
            lines.append(f"    {_csr_access(instr, 'S')}")
        lines.append("    #endif")
        lines.append("")

        test_data.int_regs.return_registers([r_of_bit])

        binname = f"scountovf_shadow_s_{pattern_name}"
        lines.append(f"    {test_data.add_testcase(binname, coverpoint, covergroup)}")
        lines.append(
            f"    {_scountovf_access(f'csrr x{r_scountovf}, scountovf   # sample point -- must match OF pattern', 'S')}"
        )
        lines.append("")

        test_data.int_regs.return_registers([r_scountovf])

    # --- all_0s: every OF bit clear ---
    emit_pattern("all_0s", lambda i: 0)

    # --- all_1s: every OF bit set ---
    emit_pattern("all_1s", lambda i: 1)

    # --- walking_1s: exactly one OF bit set at a time, across all 29 positions ---
    for walk_idx in range(29):
        emit_pattern(f"walking1_{walk_idx}", lambda i, w=walk_idx: 1 if i == w else 0)

    lines.append("RVTEST_GOTO_MMODE")

    return lines


@add_priv_test_generator(
    "SscofpmfS",
    required_extensions=["S", "Sscofpmf"],
    march_extensions=[],
    extra_defines=[
        "#define RVTEST_TEMP_BOOT_TO_S",
    ],
)
def make_sscofpmfs(test_data: TestData) -> list[TestChunk]:
    """Generate tests for the SscofpmfS performance-counter-overflow testsuite."""
    tc = test_data.begin_test_chunk()
    tc.code.extend(_generate_lcofi_sip_s_tests(test_data))
    tc.code.extend(_generate_lcofip_hw_only_s_tests(test_data))
    tc.code.extend(_generate_scountovf_shadow_s_tests(test_data))
    return generate_sscofpmf_suite(test_data, "S")
