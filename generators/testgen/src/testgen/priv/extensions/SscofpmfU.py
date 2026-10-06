##################################
# priv/extensions/SscofpmfU.py
# Written by: Ayesha Anwar, ayesha.anwaar2005@gmail.com
# Sscofpmf U-mode test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.SscofpmfCommon import MACRO_CHECKS, csr_access
from testgen.priv.extensions.SscofpmfSuite import generate_sscofpmf_suite
from testgen.priv.registry import add_priv_test_generator


def _generate_lcofi_sip_u_tests(test_data: TestData) -> list[str]:
    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_lcofi_sip_u"
    ######################################

    LCOFI_BIT = 1 << 13
    SIE_BIT = 0x2

    r_val, r_temp = test_data.int_regs.get_registers(2, exclude_regs=[0, 31])

    lines = [
        comment_banner(
            coverpoint,
            "Interrupt pending and enable, mode = U.\n"
            "mideleg.LCOFI=1 (from the boot setup) and sstatus.SIE=0 held fixed;\n"
            "sweep sip.LCOFIP x sie.LCOFIE.\n"
            "Sample point is the T-SBI delegate's sret back to U (sstatus.SPP=0).\n",
        ),
        "",
        csr_access("csrw sie, zero      # disable all S-mode interrupts", "U"),
        csr_access("csrw RVMODEL_MHPMEVENT, zero", "U"),
        f"LI(x{r_val}, {hex(SIE_BIT)})",
        csr_access(f"csrc sstatus, x{r_val}   # sstatus.SIE = 0 ", "U"),
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

            lines.append(f"LI(x{r_val}, {hex(LCOFI_BIT)})")
            if lcofip:
                lines.append(csr_access(f"csrs sip, x{r_val}   # sip.LCOFIP = 1", "U"))
            else:
                lines.extend(
                    [
                        csr_access("csrw RVMODEL_MHPMCOUNTER, zero   # no overflow", "U"),
                        csr_access(f"csrc sip, x{r_val}   # sip.LCOFIP = 0", "U"),
                    ]
                )

            lines.extend(
                [
                    f"LI(x{r_temp}, {hex(LCOFI_BIT)})",
                    test_data.add_testcase(binname, coverpoint, covergroup),
                    csr_access(f"{'csrs' if lcofie else 'csrc'} sie, x{r_temp}   # sie.LCOFIE = {lcofie}", "U"),
                    "",
                    f"RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})",
                    "",
                    (csr_access(f"csrc sip, x{r_temp}   # clear LCOFIP", "U") if lcofip else ""),
                    csr_access("csrw sie, zero        # clear LCOFIE", "U"),
                ]
            )

    lines.extend(
        [
            "",
            f"LI(x{r_temp}, {hex(LCOFI_BIT)})",
            csr_access(f"csrc sip, x{r_temp}      # clear LCOFIP", "U"),
            csr_access(f"csrc sie, x{r_temp}      # clear LCOFIE", "U"),
            f"LI(x{r_val}, {hex(SIE_BIT)})",
            csr_access(f"csrc sstatus, x{r_val}   # clear sstatus.SIE", "U"),
            csr_access("csrw RVMODEL_MHPMCOUNTER, zero", "U"),
            csr_access("csrw RVMODEL_MHPMEVENT, zero", "U"),
        ]
    )

    test_data.int_regs.return_registers([r_val, r_temp])
    return lines


@add_priv_test_generator(
    "SscofpmfU",
    required_extensions=["U", "Sscofpmf"],
)
def make_sscofpmfu(test_data: TestData) -> list[TestChunk]:
    """Generate tests for the SscofpmfU performance-counter-overflow testsuite."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk(split_name="interrupt")
    tc.code.extend(MACRO_CHECKS)
    tc.code.extend(_generate_lcofi_sip_u_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())
    test_chunks.extend(generate_sscofpmf_suite(test_data, "U"))
    return test_chunks
