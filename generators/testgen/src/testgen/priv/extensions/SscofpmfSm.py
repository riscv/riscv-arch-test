##################################
# priv/extensions/SscofpmfSm.py
# Written by: Ayesha Anwar, ayesha.anwaar2005@gmail.com
# Sscofpmf M-mode test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.asm.interrupts import clr_mtimer_int, set_mtimer_int
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.SscofpmfCommon import generate_sscofpmf_suite
from testgen.priv.registry import add_priv_test_generator


def _generate_lcofi_m_tests(test_data: TestData) -> list[str]:
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_lcofi_m"
    ######################################

    LCOFI_BIT = 1 << 13
    MIE_BIT = 0x8
    SIE_BIT = 0x2

    r_val, r_temp = test_data.int_regs.get_registers(2, exclude_regs=[0, 31])

    lines = [
        comment_banner(
            coverpoint,
            "Interrupt pending and enable, mode = M.\n"
            "mstatus.MIE=1, mstatus.SIE=1 held fixed per testplan; sweep is\n"
            "mip.LCOFIP x mie.LCOFIE x mideleg.LCOFI.\n",
        ),
        "",
        "# === M-MODE SETUP ===",
        "csrw mip, zero      # clear all pending",
        "csrw mie, zero      # disable all interrupts",
        "csrw RVMODEL_MHPMEVENT, zero",
        f"LI(x{r_val}, {hex(MIE_BIT)})",
        f"csrs mstatus, x{r_val}   # mstatus.MIE = 1 (fixed)",
        f"LI(x{r_val}, {hex(SIE_BIT)})",
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
                            f"LI(x{r_val}, {hex(LCOFI_BIT)})",
                            f"csrs mip, x{r_val}   # set mip.LCOFIP directly",
                        ]
                    )
                else:
                    lines.append("csrw RVMODEL_MHPMCOUNTER, zero   # keep counter clear -- no overflow")

                lines.extend(
                    [
                        f"LI(x{r_temp}, {hex(LCOFI_BIT)})",
                        f"{'csrs' if mideleg_bit else 'csrc'} mideleg, x{r_temp}   # mideleg.LCOFI = {mideleg_bit}",
                        f"{'csrs' if lcofie else 'csrc'} mie, x{r_temp}   # mie.LCOFIE = {lcofie}",
                        "",
                        test_data.add_testcase(binname, coverpoint, covergroup),
                        "    # Stays in M-mode throughout. mideleg only affects delegation to a",
                        "    # lower mode, so it does not gate M-mode trap-taking here; only",
                        "    # mstatus.MIE (fixed 1) and mie.LCOFIE actually gate the trap.",
                        "    # Fires during the idle window below if LCOFIP=1 & LCOFIE=1; else",
                        "    # falls through once the countdown expires.",
                        f"RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})",
                        "",
                        f"csrc mip, x{r_temp}   # clear LCOFIP for next iteration (if it latched)" if lcofip else "",
                        "csrw mie, zero        # disable LCOFIE before next iteration",
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
            f"LI(x{r_val}, {hex(MIE_BIT | SIE_BIT)})",
            f"csrc mstatus, x{r_val}   # clear mstatus.MIE and mstatus.SIE",
            "csrw RVMODEL_MHPMCOUNTER, zero",
            "csrw RVMODEL_MHPMEVENT, zero",
        ]
    )

    test_data.int_regs.return_registers([r_val, r_temp])
    return lines


def _generate_lcofip_priority_sm_tests(test_data: TestData) -> list[str]:
    """cp_lcofip_priority: priority of LCOFI interrupt."""
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_lcofip_priority"
    ######################################

    r_mtime, r_mtimecmp, r_val, r_temp, r_temp2, r_addr = test_data.int_regs.get_registers(6, exclude_regs=[0, 31])

    lines = [
        comment_banner(
            coverpoint,
            "LCOFI priority with MEIP, MTIP, MSIP, or no other pending interrupt.\n"
            "LCOFIP is set by actual hpmcounter overflow. Highest-priority interrupt fires;\n"
            "LCOFI fires only when no other interrupt is pending.",
        ),
        "",
        "# Setup: mstatus.MIE=1, mstatus.SIE=1",
        "csrsi mstatus, 0x8   # MIE",
        "csrsi mstatus, 0x2   # SIE",
        "csrw mie, zero      # mie = all 0s initially",
        "",
    ]

    other_interrupts = [
        "meip",
        "mtip",
        "msip",
        "none",
    ]

    for other_int in other_interrupts:
        binname = f"lcofip_priority_{other_int}"

        lines.extend(
            [
                f"# Testcase: competing interrupt = {other_int}",
                "csrw mip, zero   # clear LCOFIP and other pending bits",
                "csrw mie, zero   # disable interrupts (clear LCOFIE)",
                f"LI(x{r_val}, RVMODEL_MHPMEVENT_VAL)   # event_index = 0, OF starts at 0",
                f"csrw RVMODEL_MHPMEVENT, x{r_val}",
                f"LI(x{r_temp}, -1)",
                f"csrw RVMODEL_MHPMCOUNTER, x{r_temp}   # all 1s -> next count overflows",
                "",
                f"LA(x{r_addr}, scratch)",
                "# Overflow must occur only via RVMODEL_MHPMEVENT_CODE; run at least twice per spec",
                f"RVMODEL_MHPMEVENT_CODE(x{r_addr}, x{r_val})",
                f"RVMODEL_MHPMEVENT_CODE(x{r_addr}, x{r_val})   # this sets LCOFIP via a real overflow",
                "",
            ]
        )

        if other_int == "meip":
            lines.append("RVTEST_SET_MEXT_INT")

        elif other_int == "mtip":
            lines.extend(
                set_mtimer_int(
                    r_mtime,
                    r_mtimecmp,
                    r_temp,
                    r_temp2,
                )
            )

        elif other_int == "msip":
            lines.append("RVTEST_SET_MSW_INT")

        lines.extend(
            [
                f"LI(x{r_temp}, -1)",
                f"csrw mie, x{r_temp}   # mie = all 1s",
                "",
                test_data.add_testcase(
                    binname,
                    coverpoint,
                    covergroup,
                ),
                f"csrr x{r_val}, RVMODEL_MHPMEVENT   # sample point for mhpmevent_of",
                write_sigupd(r_val, test_data),
                f"csrr x{r_temp}, RVMODEL_MHPMCOUNTER   # sample point for hpmcounter_nonzero/non-all-1s",
                write_sigupd(r_temp, test_data),
                "",
                f"RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})",
                "",
                f"csrr x{r_temp2}, mip   # sample point for lcofip priority outcome",
                write_sigupd(r_temp2, test_data),
                "",
            ]
        )

        if other_int == "meip":
            lines.append("RVTEST_CLR_MEXT_INT")

        elif other_int == "mtip":
            lines.extend(
                clr_mtimer_int(
                    r_temp,
                    r_mtimecmp,
                )
            )

        elif other_int == "msip":
            lines.append("RVTEST_CLR_MSW_INT")

        lines.extend(
            [
                "csrw mip, zero   # clear LCOFIP for next iteration",
                "csrw mie, zero",
                "",
            ]
        )

    test_data.int_regs.return_registers([r_mtime, r_mtimecmp, r_val, r_temp, r_temp2, r_addr])

    return lines


@add_priv_test_generator(
    "SscofpmfSm",
    required_extensions=["Sm", "Sscofpmf"],
    march_extensions=[],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_sscofpmfsm(test_data: TestData) -> list[TestChunk]:
    """Generate tests for the SscofpmfSm performance-counter-overflow testsuite."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()
    tc.code.extend(_generate_lcofi_m_tests(test_data))
    tc.code.extend(_generate_lcofip_priority_sm_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())
    test_chunks.extend(generate_sscofpmf_suite(test_data, "Sm"))
    return test_chunks
