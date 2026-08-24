##################################
# priv/extensions/SscofpmfS.py
# Written by: Ayesha Anwar, ayesha.anwaar2005@gmail.com
# Sscofpmf S-mode test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import comment_banner
from testgen.asm.interrupts import clr_stimer_mmode, set_stimer_mmode
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.SscofpmfCommon import generate_sscofpmf_suite
from testgen.priv.registry import add_priv_test_generator


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


def _generate_lcofip_priority_s_tests(test_data: TestData) -> list[str]:
    """cp_lcofip_priority: priority of LCOFI interrupt in S-mode."""
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_lcofip_priority"
    ######################################

    LCOFIP_BIT = 1 << 13  # LCOFI
    SSIP_BIT = 1 << 1  # SSIP
    STIP_BIT = 1 << 5  # STIP
    SEIP_BIT = 1 << 9  # SEIP

    SIE_BIT = 0x2  # sstatus.SIE / mstatus.SIE

    S_MODE_INTERRUPT_BITS = LCOFIP_BIT | SSIP_BIT | STIP_BIT | SEIP_BIT

    r1, r_mtime, r_mtimecmp, r_temp, r_temp2, r_scratch = test_data.int_regs.get_registers(6, exclude_regs=[0, 31])

    lines = [
        comment_banner(
            coverpoint,
            "Priority of LCOFI interrupt in S-mode.\n"
            "mstatus.SIE=1 and the LCOFI, SEIP, STIP, and SSIP interrupts\n"
            "are delegated to S-mode. LCOFIP is pending together with one\n"
            "of {SEIP, STIP, SSIP, none}. The highest-priority pending\n"
            "S-mode interrupt fires; LCOFIP fires only when no competing\n"
            "S-mode interrupt is pending.",
        ),
        "",
        "# === M-MODE SETUP ===",
        "csrw mip, zero      # clear all pending interrupts",
        "csrw mie, zero      # disable all interrupts",
        "",
        "# Delegate LCOFI, SEIP, STIP and SSIP to S-mode",
        f"LI(x{r_temp}, {hex(S_MODE_INTERRUPT_BITS)})",
        f"csrs mideleg, x{r_temp}",
        "",
        "# Enable S-mode interrupt sources in mie.",
        "# These enables are inherited by the delegated S-mode interrupts.",
        f"csrs mie, x{r_temp}",
        "",
        "# Enable S-mode global interrupt enable.",
        f"LI(x{r_temp}, {hex(SIE_BIT)})",
        f"csrs mstatus, x{r_temp}   # mstatus.SIE = 1",
        "",
    ]

    other_interrupts = ["seip", "stip", "ssip", "none"]

    for other_int in other_interrupts:
        binname = f"lcofip_priority_s_{other_int}"

        lines.extend(
            [
                "",
                f"# Testcase: competing interrupt = {other_int}, mode = S",
                "",
                "# Set LCOFIP while still in M-mode.",
                f"LI(x{r_scratch}, {hex(LCOFIP_BIT)})",
                f"csrs mip, x{r_scratch}   # set LCOFIP",
            ]
        )

        if other_int == "seip":
            lines.append("RVTEST_SET_SEXT_INT")

        elif other_int == "stip":
            # This helper directly accesses mip and therefore must
            # execute while still in M-mode.
            lines.extend(
                set_stimer_mmode(
                    r_scratch,
                )
            )

        elif other_int == "ssip":
            lines.extend(
                [
                    f"LI(x{r1}, {hex(SSIP_BIT)})",
                    f"csrs mip, x{r1}   # set SSIP",
                ]
            )

        # "none" -- only LCOFIP is pending.

        lines.extend(
            [
                "",
                test_data.add_testcase(
                    binname,
                    coverpoint,
                    covergroup,
                ),
                "",
                "# Enter S-mode only for the actual interrupt-priority test.",
                "RVTEST_TSBI_GOTO_SMODE",
                "",
                "    # S-mode test body.",
                "    # Only delegated S-mode interrupts participate.",
                "    # LCOFIP competes with SEIP/STIP/SSIP according to priority.",
                f"    RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})",
                "",
                "# Return to M-mode so machine CSRs and pending bits can be cleared.",
                "RVTEST_GOTO_MMODE",
                "",
            ]
        )

        #
        # These operations must happen in M-mode.
        #
        if other_int == "seip":
            lines.append("RVTEST_CLR_SEXT_INT")

        elif other_int == "stip":
            lines.extend(
                clr_stimer_mmode(
                    r_scratch,
                )
            )

        elif other_int == "ssip":
            lines.extend(
                [
                    f"LI(x{r1}, {hex(SSIP_BIT)})",
                    f"csrc mip, x{r1}   # clear SSIP",
                ]
            )

        lines.extend(
            [
                f"LI(x{r_scratch}, {hex(LCOFIP_BIT)})",
                f"csrc mip, x{r_scratch}   # clear LCOFIP",
                "",
            ]
        )

    lines.extend(
        [
            "",
            "# === M-MODE CLEANUP ===",
            "csrw mie, zero",
            f"LI(x{r_temp}, {hex(S_MODE_INTERRUPT_BITS)})",
            f"csrc mideleg, x{r_temp}",
            f"LI(x{r_temp}, {hex(SIE_BIT)})",
            f"csrc mstatus, x{r_temp}   # clear mstatus.SIE",
            "csrw mip, zero",
        ]
    )

    test_data.int_regs.return_registers([r1, r_mtime, r_mtimecmp, r_temp, r_temp2, r_scratch])

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
    # tc.code.extend(_generate_lcofi_sip_s_tests(test_data))
    tc.code.extend(_generate_lcofip_priority_s_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())
    test_chunks.extend(generate_sscofpmf_suite(test_data, "S"))
    return test_chunks
