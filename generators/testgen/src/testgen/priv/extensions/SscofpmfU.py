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
    coverpoint = "cp_lcofi_u"
    ######################################

    LCOFI_BIT = 1 << 13
    SIE_BIT = 0x2

    r_val, r_temp = test_data.int_regs.get_registers(2, exclude_regs=[0, 31])

    lines = [
        comment_banner(
            coverpoint,
            "Interrupt pending and enable, mode = U.\n"
            "mideleg.LCOFI=1 held fixed (required to reach U-mode with LCOFI\n"
            "delegated below M), sstatus.SIE=1 held fixed per testplan; sweep is\n"
            "sip.LCOFIP x sie.LCOFIE. sip/sie are only accessible from M or\n"
            "S-mode, so writes stay in M-mode; only the idle-wait executes at\n"
            "privilege U.\n",
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
            binname = f"lcofi_u_lcofip_{lcofip}_lcofie_{lcofie}"
            lines.extend(
                [
                    "",
                    f"# Testcase: sip.LCOFIP={lcofip}, sie.LCOFIE={lcofie}, mode=U",
                ]
            )

            if lcofip:
                lines.extend(
                    [
                        f"LI(x{r_val}, {hex(LCOFI_BIT)})",
                        f"csrs sip, x{r_val}   # set sip.LCOFIP directly (still M-mode)",
                    ]
                )
            else:
                lines.append("csrw RVMODEL_MHPMCOUNTER, zero   # keep counter clear -- no overflow")

            lines.extend(
                [
                    f"LI(x{r_temp}, {hex(LCOFI_BIT)})",
                    f"{'csrs' if lcofie else 'csrc'} sie, x{r_temp}   # sie.LCOFIE = {lcofie} (still M-mode)",
                    "",
                    test_data.add_testcase(binname, coverpoint, covergroup),
                    "    # sstatus.SIE=1 and mideleg.LCOFI=1 held fixed; only sie.LCOFIE",
                    "    # gates the trap given sip.LCOFIP. Fires during the idle window",
                    "    # below if LCOFIP=1 & LCOFIE=1; else falls through once the",
                    "    # countdown expires. sip/sie writes stay in M-mode above --",
                    "    # only the idle-wait itself runs at privilege U.",
                    "RVTEST_TSBI_GOTO_UMODE",
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
