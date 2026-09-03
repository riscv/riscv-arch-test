##################################
# priv/extensions/SscofpmfS.py
# Written by: Ayesha Anwar, ayesha.anwaar2005@gmail.com
# Sscofpmf S-mode test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.asm.interrupts import clr_stimer_mmode, set_stimer_mmode
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.SscofpmfCommon import generate_sscofpmf_suite
from testgen.priv.registry import add_priv_test_generator


def _generate_lcofi_sip_s_tests(test_data: TestData) -> list[str]:
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_lcofi_s"
    ######################################

    LCOFI_BIT = 1 << 13
    SIE_BIT = 0x2

    r_val, r_temp = test_data.int_regs.get_registers(2, exclude_regs=[0, 31])

    lines = [
        comment_banner(
            coverpoint,
            "Interrupt pending and enable, mode = S.\n"
            "mideleg.LCOFI=1 held fixed (required to reach S-mode with LCOFI\n"
            "visible), sstatus.SIE=1 held fixed per testplan; sweep is\n"
            "sip.LCOFIP x sie.LCOFIE.\n",
        ),
        "",
        "# === M-MODE SETUP ===",
        "csrw mip, zero      # clear all pending",
        "csrw mie, zero      # disable all interrupts",
        "csrw RVMODEL_MHPMEVENT, zero",
        f"LI(x{r_val}, {hex(LCOFI_BIT)})",
        f"csrs mideleg, x{r_val}   # mideleg.LCOFI = 1 (fixed)",
        f"LI(x{r_val}, {hex(SIE_BIT)})",
        f"csrs mstatus, x{r_val}   # sstatus.SIE = 1 (fixed, via mstatus)",
    ]

    for lcofip in [0, 1]:
        for lcofie in [0, 1]:
            binname = f"lcofi_s_lcofip_{lcofip}_lcofie_{lcofie}"
            lines.extend(
                [
                    "",
                    f"# Testcase: sip.LCOFIP={lcofip}, sie.LCOFIE={lcofie}, mode=S",
                ]
            )

            if lcofip:
                lines.extend(
                    [
                        f"LI(x{r_val}, {hex(LCOFI_BIT)})",
                        f"csrs sip, x{r_val}   # set sip.LCOFIP directly",
                    ]
                )
            else:
                lines.append("csrw RVMODEL_MHPMCOUNTER, zero   # keep counter clear -- no overflow")

            lines.extend(
                [
                    f"LI(x{r_temp}, {hex(LCOFI_BIT)})",
                    f"{'csrs' if lcofie else 'csrc'} sie, x{r_temp}   # sie.LCOFIE = {lcofie}",
                    "",
                    test_data.add_testcase(binname, coverpoint, covergroup),
                    "    # sstatus.SIE=1 and mideleg.LCOFI=1 held fixed; only sie.LCOFIE",
                    "    # gates the trap given sip.LCOFIP. Fires during the idle window",
                    "RVTEST_TSBI_GOTO_SMODE",
                    f"    RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})",
                    "RVTEST_GOTO_MMODE",
                    "",
                    f"csrc sip, x{r_temp}   # clear LCOFIP for next iteration (if it latched)" if lcofip else "",
                    "csrw sie, zero        # disable LCOFIE before next iteration",
                ]
            )

    lines.extend(
        [
            "",
            "# === M-MODE CLEANUP ===",
            f"LI(x{r_temp}, {hex(LCOFI_BIT)})",
            f"csrc sip, x{r_temp}      # clear LCOFIP",
            f"csrc sie, x{r_temp}      # clear LCOFIE",
            f"csrc mideleg, x{r_temp}  # clear mideleg.LCOFI",
            f"LI(x{r_val}, {hex(SIE_BIT)})",
            f"csrc mstatus, x{r_val}   # clear sstatus.SIE (via mstatus)",
            "csrw RVMODEL_MHPMCOUNTER, zero",
            "csrw RVMODEL_MHPMEVENT, zero",
        ]
    )

    test_data.int_regs.return_registers([r_val, r_temp])
    return lines


def _generate_lcofip_priority_s_tests(test_data: TestData) -> list[str]:

    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_lcofip_priority_s"
    ######################################

    SSI_BIT = 1 << 1
    STI_BIT = 1 << 5
    SEI_BIT = 1 << 9
    LCOFI_BIT = 1 << 13
    SIE_BIT = 0x2  # mstatus/sstatus bit 1
    DELEG_MASK = SSI_BIT | STI_BIT | SEI_BIT | LCOFI_BIT  # 0x2222

    r_val, r_temp, r_temp2, r_scratch = test_data.int_regs.get_registers(4, exclude_regs=[0, 31])

    lines = [
        comment_banner(
            coverpoint,
            (
                "Priority of LCOFI interrupt in S-mode (4 cases).\n"
                "sstatus.SIE=1, sie=all 0s.\n"
                "sip = 1 in LCOFIP (via real counter overflow, not a direct\n"
                "write -- see cp_lcofi_sip_s) and one of {SEIP,STIP,SSIP,none}.\n"
                "sie = all 1s. Highest priority interrupt fires; LCOFIP only\n"
                "fires if none of the others are pending (lowest priority)."
            ),
        ),
        "",
        "# === M-MODE SETUP ===",
        "csrw mip, zero      # clear all pending",
        "csrw mie, zero      # disable all interrupts",
        "csrw RVMODEL_MHPMEVENT, zero",
        f"LI(x{r_val}, {hex(DELEG_MASK)})",
        f"csrs mideleg, x{r_val}   # delegate SSI|STI|SEI|LCOFI to S-mode",
        f"csrsi mstatus, {hex(SIE_BIT)}   # mstatus.SIE = 1 (== sstatus.SIE)",
    ]

    other_interrupts = [
        "seip",
        "stip",
        "ssip",
        "none",
    ]

    for other_int in other_interrupts:
        binname = f"lcofip_priority_s_{other_int}"

        lines.extend(
            [
                "",
                f"# Testcase: competing interrupt = {other_int}",
                f"LI(x{r_val}, RVMODEL_MHPMEVENT_VAL)   # select a real event",
                f"csrw RVMODEL_MHPMEVENT, x{r_val}",
                f"LI(x{r_scratch}, -1)",
                f"csrw RVMODEL_MHPMCOUNTER, x{r_scratch}   # all 1s -> next count overflows",
                f"LA(x{r_temp}, scratch)",
                "# Incrementing RVMODEL_MHPMCOUNTER in DUT specific way",
                f"RVMODEL_MHPMEVENT_CODE(x{r_temp}, x{r_scratch})",
                f"RVMODEL_MHPMEVENT_CODE(x{r_temp}, x{r_scratch})   # run at least twice per spec",
            ]
        )

        if other_int == "seip":
            lines.append("RVTEST_SET_SEXT_INT")

        elif other_int == "stip":
            lines.extend(set_stimer_mmode(r_temp2))

        elif other_int == "ssip":
            lines.extend(
                [
                    f"LI(x{r_temp2}, {hex(SSI_BIT)})",
                    f"csrs mip, x{r_temp2}   # mip.SSIP = 1 (directly writable, unlike LCOFIP)",
                ]
            )

        # "none" -- no competing interrupt triggered

        lines.extend(
            [
                f"LI(x{r_temp}, -1)",
                f"csrs mie, x{r_temp}   # sie = all 1s (LCOFIE + SSIE/STIE/SEIE)",
                "",
                test_data.add_testcase(binname, coverpoint, covergroup),
                # -------------------------------------------------
                # Sample MHPMEVENT and dump it to the signature.
                # r_val is free again here -- overwrites the event
                # value we set above, which is fine since we're
                # done using it for the counter-priming block.
                # -------------------------------------------------
                f"csrr x{r_val}, RVMODEL_MHPMEVENT   # sample point for mhpmevent_of",
                write_sigupd(r_val, test_data),
                f"csrr x{r_scratch}, RVMODEL_MHPMCOUNTER   # sample point for hpmcounter_nonzero/non-all-1s",
                write_sigupd(r_scratch, test_data),
                "",
                "# Enter S-mode (interrupt fires immediately or on timer maturity)",
                "RVTEST_GOTO_LOWER_MODE Smode",
                f"RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})",
                f"csrr x{r_temp2}, sip   # sample point for lcofip priority outcome",
                write_sigupd(r_temp2, test_data),
                "RVTEST_GOTO_MMODE",
                "",
            ]
        )

        if other_int == "seip":
            lines.append("RVTEST_CLR_SEXT_INT")

        elif other_int == "stip":
            lines.extend(clr_stimer_mmode(r_temp2))

        elif other_int == "ssip":
            lines.extend(
                [
                    f"LI(x{r_temp2}, {hex(SSI_BIT)})",
                    f"csrc mip, x{r_temp2}",
                ]
            )

        lines.extend(
            [
                "csrw RVMODEL_MHPMCOUNTER, zero   # reset counter before next iteration",
                "csrw RVMODEL_MHPMEVENT, zero",
                "csrw mie, zero   # disable all before next iteration",
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

    test_data.int_regs.return_registers([r_val, r_temp, r_temp2, r_scratch])

    return lines


@add_priv_test_generator(
    "SscofpmfS",
    required_extensions=["S", "Sscofpmf"],
    march_extensions=[],
    extra_defines=[],
)
def make_sscofpmfs(test_data: TestData) -> list[TestChunk]:
    """Generate tests for the SscofpmfS performance-counter-overflow testsuite."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()
    tc.code.extend(_generate_lcofi_sip_s_tests(test_data))
    tc.code.extend(_generate_lcofip_priority_s_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())
    test_chunks.extend(generate_sscofpmf_suite(test_data, "S"))
    return test_chunks
