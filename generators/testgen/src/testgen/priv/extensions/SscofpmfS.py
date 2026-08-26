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
    """cp_lcofip_priority: priority of LCOFI interrupt, executed in S-mode.

    Per testplan:
        sstatus.SIE = 1
        sie = 0s
        sip = 1 in LCOFIP and one of {SEIP, STIP, SSIP, none}
        sie = all 1s

    LCOFIP is a read-only shadow of mhpmeventN.OF (see
    _generate_lcofi_sip_s_tests) -- driven via a real counter overflow,
    not a direct CSR write. Mode transitions follow this file's existing
    per-iteration RVTEST_TSBI_GOTO_SMODE / RVTEST_GOTO_MMODE convention,
    not a one-time whole-suite boot.
    """
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_lcofip_priority"
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
                "RVTEST_TSBI_GOTO_SMODE",
                f"    RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})",
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
    extra_defines=[
        "#define RVTEST_TEMP_BOOT_TO_S",
    ],
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
