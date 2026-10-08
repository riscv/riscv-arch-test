##################################
# priv/extensions/SscofpmfS.py
# Written by: Ayesha Anwar, ayesha.anwaar2005@gmail.com
# Sscofpmf S-mode test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.SscofpmfCommon import (
    csr_access,
    generate_sscofpmf_suite,
)
from testgen.priv.registry import add_priv_test_generator


def _generate_lcofi_sip_s_tests(test_data: TestData) -> list[str]:
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_lcofi_sip_s"
    ######################################

    LCOFI_BIT = 1 << 13
    SIE_BIT = 0x2

    r_val, r_temp = test_data.int_regs.get_registers(2, exclude_regs=[0, 31])
    lines = [
        comment_banner(
            coverpoint,
            "Interrupt pending and enable, mode = S.\n"
            "mideleg.LCOFI=1 from the boot-to-S setup (required to reach S-mode with\n"
            "LCOFI visible), sstatus.SIE=1 held fixed per testplan; sweep is\n"
            "sip.LCOFIP x sie.LCOFIE.\n",
        ),
        "",
        "csrw sie, zero      # disable all S-mode interrupts",
        csr_access("csrw RVTEST_CSR_MHPMEVENT, zero", "S"),
        f"LI(x{r_val}, {hex(SIE_BIT)})",
        f"csrs sstatus, x{r_val}   # sstatus.SIE = 1 (fixed)",
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

            lines.append(f"LI(x{r_val}, {hex(LCOFI_BIT)})")
            if lcofip:
                lines.append(f"csrs sip, x{r_val}   # set sip.LCOFIP directly")
            else:
                lines.extend(
                    [
                        csr_access("csrw RVTEST_CSR_MHPMCOUNTER, zero   # keep counter clear -- no overflow", "S"),
                        f"csrc sip, x{r_val}   # explicitly hold sip.LCOFIP = 0 (touch it so it samples)",
                    ]
                )

            lines.extend(
                [
                    f"LI(x{r_temp}, {hex(LCOFI_BIT)})",
                    f"{'csrs' if lcofie else 'csrc'} sie, x{r_temp}   # sie.LCOFIE = {lcofie}",
                    "",
                    test_data.add_testcase(binname, coverpoint, covergroup),
                    # sstatus.SIE=1 and mideleg.LCOFI=1 held fixed; only sie.LCOFIE gates the
                    # trap given sip.LCOFIP. Fires during the idle window below if both are set.
                    f"RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})",
                    "",
                    f"csrc sip, x{r_temp}   # clear LCOFIP for next iteration (if it latched)" if lcofip else "",
                    "csrw sie, zero        # disable LCOFIE before next iteration",
                ]
            )

    lines.extend(
        [
            "",
            f"LI(x{r_temp}, {hex(LCOFI_BIT)})",
            f"csrc sip, x{r_temp}      # clear LCOFIP",
            f"csrc sie, x{r_temp}      # clear LCOFIE",
            f"LI(x{r_val}, {hex(SIE_BIT)})",
            f"csrc sstatus, x{r_val}   # clear sstatus.SIE",
            csr_access("csrw RVTEST_CSR_MHPMCOUNTER, zero", "S"),
            csr_access("csrw RVTEST_CSR_MHPMEVENT, zero", "S"),
        ]
    )

    test_data.int_regs.return_registers([r_val, r_temp])
    return lines


@add_priv_test_generator(
    "SscofpmfS",
    required_extensions=["S", "Sscofpmf"],
    march_extensions=[],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_sscofpmfs(test_data: TestData) -> list[TestChunk]:
    """Generate tests for the SscofpmfS performance-counter-overflow testsuite."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk(split_name="interrupt")
    tc.code.extend(_generate_lcofi_sip_s_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())
    test_chunks.extend(generate_sscofpmf_suite(test_data, "S"))
    return test_chunks
