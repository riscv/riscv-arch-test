##################################
# priv/extensions/SscofpmfSm.py
# Written by: Ayesha Anwar, ayesha.anwaar2005@gmail.com
# Sscofpmf M-mode test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import comment_banner
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

    r_val, r_temp, r_idle = test_data.int_regs.get_registers(3, exclude_regs=[0, 31])

    lines = [
        comment_banner(
            coverpoint,
            "Interrupt pending and enable, mode = M.\n"
            "mstatus.MIE=1, mstatus.SIE=1 held fixed per testplan; sweep is\n"
            "mip.LCOFIP x mie.LCOFIE x mideleg.LCOFI.\n",
        ),
        "",
        "# === M-MODE SETUP ===",
        "csrw mip, zero      # clear all pending (sip may not exist in this suite)",
        "csrw mie, zero      # disable all interrupts",
        "csrw RVTEST_CSR_MHPMEVENT, zero",
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
                    lines.append("csrw RVTEST_CSR_MHPMCOUNTER, zero   # keep counter clear -- no overflow")

                lines.extend(
                    [
                        f"LI(x{r_temp}, {hex(LCOFI_BIT)})",
                        f"{'csrs' if mideleg_bit else 'csrc'} mideleg, x{r_temp}   # mideleg.LCOFI = {mideleg_bit}",
                        f"{'csrs' if lcofie else 'csrc'} mie, x{r_temp}   # mie.LCOFIE = {lcofie}",
                        "",
                        test_data.add_testcase(binname, coverpoint, covergroup),
                        "    # Stays in M-mode throughout. With mideleg.LCOFI=1, LCOFI is an",
                        "    # S-level interrupt and is never taken in M-mode, whatever mstatus.MIE",
                        "    # is. So the trap fires during the idle window below only if",
                        "    # LCOFIP=1, LCOFIE=1 and mideleg.LCOFI=0; else it falls through once",
                        "    # the countdown expires.",
                        f"RVTEST_IDLE_FOR_INTERRUPT(x{r_idle})",
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
            "csrw RVTEST_CSR_MHPMCOUNTER, zero",
            "csrw RVTEST_CSR_MHPMEVENT, zero",
        ]
    )

    test_data.int_regs.return_registers([r_val, r_temp, r_idle])
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
    test_chunks.append(test_data.end_test_chunk())
    test_chunks.extend(generate_sscofpmf_suite(test_data, "Sm"))
    return test_chunks
