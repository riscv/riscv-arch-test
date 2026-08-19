##################################
# priv/extensions/SscofpmfSm.py
# Written by: Ayesha Anwar, ayesha.anwaar2005@gmail.com
# Sscofpmf M-mode test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import comment_banner
from testgen.asm.interrupts import clr_mtimer_int, clr_stimer_mmode, set_mtimer_int, set_stimer_mmode
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

    r_val, r_temp, r_addr = test_data.int_regs.get_registers(3, exclude_regs=[0, 31])

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
                            f"LI(x{r_val}, -1)",
                            f"csrw RVMODEL_MHPMCOUNTER, x{r_val}   # all 1s -> next count overflows",
                            "",
                            f"LA(x{r_addr}, scratch)",
                            "# Incrementing RVMODEL_MHPMCOUNTER in DUT specific way",
                            f"RVMODEL_MHPMEVENT_CODE(x{r_addr}, x{r_val})",
                            f"RVMODEL_MHPMEVENT_CODE(x{r_addr}, x{r_val})   # run at least twice per spec",
                            f"csrr x{r_val}, mip   # readback -- confirm LCOFIP actually latched from OF",
                        ]
                    )
                else:
                    lines.append("csrw RVMODEL_MHPMCOUNTER, zero   # keep counter clear -- no overflow")

                lines.extend(
                    [
                        f"LI(x{r_temp}, {hex(LCOFI_BIT)})",
                        f"{'csrs' if lcofie else 'csrc'} mie, x{r_temp}   # mie.LCOFIE = {lcofie}",
                        f"{'csrs' if mideleg_bit else 'csrc'} mideleg, x{r_temp}   # mideleg.LCOFI = {mideleg_bit}",
                        "",
                        test_data.add_testcase(binname, coverpoint, covergroup),
                        "    # Stays in M-mode throughout. mideleg only affects delegation to a",
                        "    # lower mode, so it does not gate M-mode trap-taking here; only",
                        "    # mstatus.MIE (fixed 1) and mie.LCOFIE actually gate the trap.",
                        "    # Fires immediately if LCOFIP=1 & LCOFIE=1; else falls through.",
                        "    nop",
                        "    nop",
                        "    nop",
                        "    nop",
                        "",
                        f"LI(x{r_val}, -1)" if not lcofip else "",
                        (
                            f"csrw RVMODEL_MHPMCOUNTER, x{r_val}"
                            if not lcofip
                            else "csrw RVMODEL_MHPMCOUNTER, zero   # reset counter before next iteration"
                        ),
                        f"csrc mip, x{r_temp}   # clear LCOFIP for next iteration (if it latched)" if lcofip else "",
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

    test_data.int_regs.return_registers([r_val, r_temp, r_addr])
    return lines


def _generate_lcofip_priority_sm_tests(test_data: TestData) -> list[str]:
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_lcofip_priority_m"
    ######################################

    MIE_BIT = 0x8  # mstatus bit 3

    r1, r_mtime, r_mtimecmp, r_temp, r_temp2, r_scratch = test_data.int_regs.get_registers(6, exclude_regs=[0, 31])

    lines = [
        comment_banner(
            coverpoint,
            (
                "Priority of LCOFI interrupt, mode = M.\n"
                "Per testplan: mstatus.MIE=1, mie=all 0s, mip=LCOFIP + one of\n"
                "{MEIP,MTIP,MSIP,SEIP,STIP,SSIP,none}, then mie=all 1s (trigger).\n"
                "mip.LCOFIP is a read-only shadow of the OR of mhpmeventN.OF bits\n"
                "(WARL on direct writes), so it is driven via a real counter\n"
                "overflow rather than csrs mip, LCOFIP_BIT -- a direct write is a\n"
                "silent no-op."
            ),
        ),
        "",
    ]

    other_interrupts = ["meip", "mtip", "msip", "seip", "stip", "ssip", "none"]

    for other_int in other_interrupts:
        binname = f"lcofip_priority_sm_{other_int}"

        lines.extend(
            [
                "",
                "# === M-MODE SETUP ===",
                f"# Testcase: competing interrupt = {other_int}, mode = M",
                f"LI(x{r_temp}, {hex(MIE_BIT)})",
                f"csrs mstatus, x{r_temp}   # mstatus.MIE = 1",
                "csrw mie, zero            # mie = all 0s",
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
            lines.extend([f"LI(x{r1}, 0x2)", f"csrs mip, x{r1}   # mip.SSIP = 1"])
        # "none" -- no competing interrupt triggered

        lines.extend(
            [
                "",
                f"LI(x{r_temp}, -1)",
                f"csrw mie, x{r_temp}   # mie = all 1s -- fires immediately (MIE already 1)",
                "",
                test_data.add_testcase(binname, coverpoint, covergroup),
                "    nop",
                "    nop",
                "    nop",
                "    nop",
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
                "csrw RVMODEL_MHPMCOUNTER, zero   # reset counter -- clears LCOFIP's overflow source",
                "csrw RVMODEL_MHPMEVENT, zero",
                "csrw mie, zero",
                f"LI(x{r_temp}, {hex(MIE_BIT)})",
                f"csrc mstatus, x{r_temp}   # mstatus.MIE = 0",
            ]
        )

    test_data.int_regs.return_registers([r1, r_mtime, r_mtimecmp, r_temp, r_temp2, r_scratch])
    return lines


@add_priv_test_generator(
    "SscofpmfSm",
    required_extensions=["Sm", "Sscofpmf"],
    march_extensions=[],
    extra_defines=[],
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
