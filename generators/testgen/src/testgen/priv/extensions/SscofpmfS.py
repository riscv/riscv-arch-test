##################################
# priv/extensions/SscofpmfS.py
# Written by: Ayesha Anwar, ayesha.anwaar2005@gmail.com
# Sscofpmf S-mode test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

from collections.abc import Callable

from testgen.asm.helpers import comment_banner
from testgen.asm.interrupts import clr_stimer_mmode, set_stimer_mmode
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.SscofpmfCommon import _csr_access, generate_sscofpmf_suite
from testgen.priv.registry import add_priv_test_generator

# _scountovf_access


def _generate_lcofi_sip_s_tests(test_data: TestData) -> list[str]:
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_lcofi_sip_s"
    ######################################

    LCOFI_BIT = 1 << 13  # mip/mie/sip/sie bit 13
    SIE_BIT = 0x2  # mstatus/sstatus bit 1

    r_val, r_temp, r_scratch = test_data.int_regs.get_registers(3, exclude_regs=[0, 31])

    lines = [
        comment_banner(
            coverpoint,
            (
                "mip.LCOFIP (and its delegated sip.LCOFIP view) is a read-only\n"
                "shadow of the OR of mhpmeventN.OF bits (WARL on direct writes), so\n"
                "LCOFIP=1 is driven via a real counter overflow rather than\n"
                "csrs mip, LCOFI_BIT -- a direct write is a silent no-op and never\n"
                "actually latches the pending bit."
            ),
        ),
        "",
        "# === M-MODE SETUP ===",
        "csrw mip, zero      # clear all pending",
        "csrw mie, zero      # disable all interrupts",
        "csrw RVMODEL_MHPMEVENT, zero",
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
                ]
            )

            if lcofip:
                lines.extend(
                    [
                        f"LI(x{r_scratch}, -1)",
                        f"csrw RVMODEL_MHPMCOUNTER, x{r_scratch}   # all 1s -> next count overflows",
                        f"LA(x{r_temp}, scratch)",
                        "# Incrementing RVMODEL_MHPMCOUNTER in DUT specific way",
                        f"RVMODEL_MHPMEVENT_CODE(x{r_temp}, x{r_scratch})",
                        f"RVMODEL_MHPMEVENT_CODE(x{r_temp}, x{r_scratch})   # run at least twice per spec",
                        f"csrr x{r_scratch}, mip   # readback -- confirm LCOFIP actually latched from OF",
                    ]
                )
            else:
                lines.append("csrw RVMODEL_MHPMCOUNTER, zero   # keep counter clear -- no overflow")

            lines.extend(
                [
                    f"LI(x{r_temp}, {hex(LCOFI_BIT)})",
                    f"{'csrs' if lcofie else 'csrc'} mie, x{r_temp}   # sie.LCOFIE = {lcofie}",
                    "",
                    test_data.add_testcase(binname, coverpoint, covergroup),
                    "RVTEST_TSBI_GOTO_SMODE",
                    f"    RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})",
                    "RVTEST_GOTO_MMODE",
                    "",
                    "csrw RVMODEL_MHPMCOUNTER, zero   # reset counter before next iteration",
                    "csrw RVMODEL_MHPMEVENT, zero",
                    f"csrc mie, x{r_val}   # clear LCOFIE for next iteration",
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

    test_data.int_regs.return_registers([r_val, r_temp, r_scratch])
    return lines


def _generate_lcofip_hw_only_s_tests(test_data: TestData) -> list[str]:
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_lcofip_hw_only"
    ######################################

    OF_BIT = 1 << 63  # RVMODEL_MHPMEVENT bit 63

    r_val, r_temp = test_data.int_regs.get_registers(2, exclude_regs=[0, 31])

    lines = [
        comment_banner(
            coverpoint,
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
        lines.append(f"    csrr x{r_scountovf}, scountovf   # sample point -- must match OF pattern")
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


def _generate_lcofip_priority_s_tests(test_data: TestData) -> list[str]:
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_lcofip_priority"
    priv_mode = "S"
    ######################################

    LCOFI_DELEG_BIT = 1 << 13  # mideleg bit 13
    SIE_BIT = 0x2  # sstatus bit 1

    DELEGABLE_MIDELEG_BIT = {
        "seip": 1 << 9,  # SEIP
        "stip": 1 << 5,  # STIP
        "ssip": 1 << 0,  # SSIP
    }

    r1, r_scratch, r_temp = test_data.int_regs.get_registers(3, exclude_regs=[0, 31])

    lines = [
        comment_banner(
            coverpoint,
            (
                "Priority of LCOFI interrupt, mode = S.\n"
                "Per testplan: sstatus.SIE=1, sie=0s, sip=LCOFIP + one of\n"
                "{SEIP,STIP,SSIP,none}, then sie=all 1s (trigger). Only S-delegable\n"
                "causes compete here -- MEIP/MTIP/MSIP cannot be delegated, so they\n"
                "never contend with LCOFI for S-mode's destination.\n"
            ),
        ),
        "",
    ]

    other_interrupts = ["seip", "stip", "ssip", "none"]

    for other_int in other_interrupts:
        binname = f"lcofip_priority_s_{other_int}"

        lines.extend(
            [
                "",
                "# === M-MODE SETUP ===",
                f"# Testcase: competing interrupt = {other_int}, mode = S",
                "csrw mie, zero      # disable all interrupts first",
                "csrw RVMODEL_MHPMEVENT, zero",
                "",
                "# --- Drive mip.LCOFIP pending via a real counter overflow ---",
                f"LI(x{r_scratch}, -1)",
                f"csrw RVMODEL_MHPMCOUNTER, x{r_scratch}   # all 1s -> next count overflows",
                f"LA(x{r_temp}, scratch)",
                "# Incrementing RVMODEL_MHPMCOUNTER in DUT specific way",
                f"RVMODEL_MHPMEVENT_CODE(x{r_temp}, x{r_scratch})",
                f"RVMODEL_MHPMEVENT_CODE(x{r_temp}, x{r_scratch})   # run at least twice per spec",
                f"csrr x{r_scratch}, mip   # readback -- confirm LCOFIP actually latched from OF",
                "",
                f"LI(x{r_scratch}, {hex(LCOFI_DELEG_BIT)})",
                f"csrs mideleg, x{r_scratch}   # delegate LCOFI to S-mode",
            ]
        )

        if other_int == "seip":
            lines.append("RVTEST_SET_SEXT_INT")
        elif other_int == "stip":
            lines.extend(set_stimer_mmode(r_scratch))
        elif other_int == "ssip":
            lines.extend([f"LI(x{r1}, 0x2)", f"csrs mip, x{r1}   # mip.SSIP = 1"])
        # "none" -- no competing interrupt triggered

        if other_int in DELEGABLE_MIDELEG_BIT:
            bit = DELEGABLE_MIDELEG_BIT[other_int]
            lines.extend(
                [
                    f"LI(x{r_scratch}, {hex(bit)})",
                    (
                        f"csrs mideleg, x{r_scratch}   # also delegate {other_int} "
                        "so it competes with LCOFI for S-mode's destination"
                    ),
                ]
            )

        lines.extend(
            [
                "",
                f"RVTEST_GOTO_LOWER_MODE {priv_mode}mode",
                f"    LI(x{r_temp}, {hex(SIE_BIT)})",
                f"    csrs sstatus, x{r_temp}   # sstatus.SIE = 1",
                "    csrw sie, zero            # sie = 0s",
                f"    LI(x{r_temp}, -1)",
                "    csrw sie, x" + str(r_temp) + "   # sie = all 1s -- fires immediately (SIE already 1)",
                "",
                f"    {test_data.add_testcase(binname, coverpoint, covergroup)}",
                "    nop",
                "    nop",
                "    nop",
                "    nop",
                "RVTEST_GOTO_MMODE",
            ]
        )

        # Cleanup -- back in M-mode
        if other_int == "seip":
            lines.append("RVTEST_CLR_SEXT_INT")
        elif other_int == "stip":
            lines.extend(clr_stimer_mmode(r_scratch))
        elif other_int == "ssip":
            lines.extend([f"LI(x{r1}, 0x2)", f"csrc mip, x{r1}"])

        if other_int in DELEGABLE_MIDELEG_BIT:
            bit = DELEGABLE_MIDELEG_BIT[other_int]
            lines.extend(
                [
                    f"LI(x{r_scratch}, {hex(bit)})",
                    f"csrc mideleg, x{r_scratch}   # {other_int} stays M-mode by default",
                ]
            )

        lines.extend(
            [
                f"LI(x{r_scratch}, {hex(LCOFI_DELEG_BIT)})",
                "csrc mideleg, x" + str(r_scratch) + "   # LCOFI stays M-mode by default",
                "csrw RVMODEL_MHPMCOUNTER, zero   # reset counter -- clears LCOFIP's overflow source",
                "csrw RVMODEL_MHPMEVENT, zero",
                "csrw mie, zero",
            ]
        )

    test_data.int_regs.return_registers([r1, r_scratch, r_temp])
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
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()
    tc.code.extend(_generate_lcofi_sip_s_tests(test_data))
    tc.code.extend(_generate_lcofip_hw_only_s_tests(test_data))
    tc.code.extend(_generate_scountovf_shadow_s_tests(test_data))
    tc.code.extend(_generate_lcofip_priority_s_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())
    test_chunks.extend(generate_sscofpmf_suite(test_data, "S"))
    return test_chunks
