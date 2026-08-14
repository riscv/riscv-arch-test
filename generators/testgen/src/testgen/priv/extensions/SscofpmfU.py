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

    r_val, r_temp = test_data.int_regs.get_registers(2, exclude_regs=[0, 31])

    lines = [
        comment_banner(
            coverpoint,
        ),
        "",
        "# === M-MODE SETUP ===",
        "csrw mip, zero      # clear all pending",
        "csrw mie, zero      # disable all interrupts",
        f"LI(x{r_val}, {hex(LCOFI_BIT)})",
        f"csrs mideleg, x{r_val}   # delegate LCOFI to S-mode",
        f"csrci mstatus, {hex(SIE_BIT)}   # mstatus.SIE = 0 (== sstatus.SIE)",
    ]

    for lcofie in [0, 1]:
        for lcofip in [0, 1]:
            binname = f"lcofi_sip_u_lcofie_{lcofie}_lcofip_{lcofip}"
            lines.extend(
                [
                    "",
                    f"# Testcase: sie.LCOFIE={lcofie}, sip.LCOFIP={lcofip}",
                    f"LI(x{r_temp}, {hex(LCOFI_BIT)})",
                    f"{'csrs' if lcofie else 'csrc'} mie, x{r_temp}   # sie.LCOFIE = {lcofie}",
                    f"{'csrs' if lcofip else 'csrc'} mip, x{r_temp}   # sip.LCOFIP = {lcofip}",
                    "",
                    test_data.add_testcase(binname, coverpoint, covergroup),
                    "RVTEST_GOTO_LOWER_MODE Umode",
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
        ]
    )

    test_data.int_regs.return_registers([r_val, r_temp])
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
