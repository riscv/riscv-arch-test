##################################
# priv/extensions/SscofpmfU.py
# Written by: Ayesha Anwar, ayesha.anwaar2005@gmail.com
# Sscofpmf U-mode test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.SscofpmfCommon import generate_sscofpmf_suite
from testgen.priv.registry import add_priv_test_generator


def _generate_lcofi_sip_u_tests(test_data: TestData) -> list[str]:
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_lcofi_sip_u"
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
        f"csrsi mstatus, {hex(SIE_BIT)}",
    ]

    for lcofie in [0, 1]:
        for lcofip in [0, 1]:
            binname = f"lcofi_sip_u_lcofie_{lcofie}_lcofip_{lcofip}"
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
                    "RVTEST_TSBI_GOTO_UMODE",
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
            f"csrci mstatus, {hex(SIE_BIT)}   # mstatus.SIE = 0 -- restore, don't leak into next test",
        ]
    )

    test_data.int_regs.return_registers([r_val, r_temp, r_scratch])
    return lines


@add_priv_test_generator(
    "SscofpmfU",
    required_extensions=["U", "Sscofpmf"],
    march_extensions=[],
    extra_defines=[
        "#define RVTEST_TEMP_BOOT_TO_U",
    ],
)
def make_sscofpmfu(test_data: TestData) -> list[TestChunk]:
    """Generate tests for the SscofpmfU performance-counter-overflow testsuite."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()
    tc.code.extend(_generate_lcofi_sip_u_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())
    test_chunks.extend(generate_sscofpmf_suite(test_data, "U"))
    return test_chunks
