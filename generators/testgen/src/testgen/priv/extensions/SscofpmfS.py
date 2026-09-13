##################################
# priv/extensions/SscofpmfS.py
# Written by: Ayesha Anwar, ayesha.anwaar2005@gmail.com
# Sscofpmf S-mode test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.SscofpmfCommon import _csr_access, generate_sscofpmf_suite, prime_counter_overflow
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
        _csr_access("csrw RVMODEL_MHPMEVENT, zero", "S"),
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
                        _csr_access("csrw RVMODEL_MHPMCOUNTER, zero   # keep counter clear -- no overflow", "S"),
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
            _csr_access("csrw RVMODEL_MHPMCOUNTER, zero", "S"),
            _csr_access("csrw RVMODEL_MHPMEVENT, zero", "S"),
        ]
    )

    test_data.int_regs.return_registers([r_val, r_temp])
    return lines


def _generate_lcofip_priority_s_tests(test_data: TestData) -> list[str]:

    ######################################
    covergroup = "Sscofpmf_cg"
    coverpoint = "cp_lcofip_priority_s"
    ######################################

    LCOFI_BIT = 1 << 13
    SIE_BIT = 0x2  # mstatus/sstatus bit 1

    r_val, r_temp, r_temp2, r_addr = test_data.int_regs.get_registers(4, exclude_regs=[0, 31])

    lines = [
        comment_banner(
            coverpoint,
            (
                "Priority of LCOFI interrupt in S-mode (4 cases).\n"
                "sstatus.SIE=1; LCOFIP is raised by a real hpmcounter overflow through\n"
                "RVMODEL_MHPMEVENT_CODE, together with one of {SEIP,STIP,SSIP,none}.\n"
                "Each case holds with sie = all 0s (nothing fires), then with sie = all 1s:\n"
                "the competing interrupt fires first and LCOFI only after it (lowest priority).\n"
                "The competing interrupts are raised through the RVTEST_SET_*_INT_S macros;\n"
                "enables stay in sie, written only here."
            ),
        ),
        "",
        "csrw sie, zero      # disable all S-mode interrupts",
        _csr_access("csrw RVMODEL_MHPMEVENT, zero", "S"),
        f"csrsi sstatus, {hex(SIE_BIT)}   # sstatus.SIE = 1",
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
                "# RVMODEL_MHPMEVENT/RVMODEL_MHPMCOUNTER writes go via T-SBI from S-mode, per spec",
                *prime_counter_overflow(r_val, r_temp2, r_temp, r_addr, "S"),
                "# the overflow sets OF and raises LCOFIP; sie = 0, so nothing fires yet",
            ]
        )

        if other_int == "seip":
            lines.append("RVTEST_SET_SEXT_INT_S")

        elif other_int == "stip":
            lines.append("RVTEST_SET_STIME_INT_S")

        elif other_int == "ssip":
            lines.append("RVTEST_SET_SSW_INT_S")

        # "none" -- no competing interrupt triggered

        lines.extend(
            [
                "",
                test_data.add_testcase(f"{binname}_sie_off", coverpoint, covergroup),
                "# sie = all 0s: LCOFIP and the competing interrupt stay pending, nothing fires",
                f"RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})",
                "",
                f"LI(x{r_temp}, -1)",
                test_data.add_testcase(binname, coverpoint, covergroup),
                _csr_access(f"csrs sie, x{r_temp}   # sie = all 1s: competing interrupt fires first, then LCOFI", "S"),
                "",
                f"RVTEST_IDLE_FOR_INTERRUPT(x{r_temp})",
                f"csrr x{r_temp2}, sip   # sample point for lcofip priority outcome",
                write_sigupd(r_temp2, test_data),
                "",
            ]
        )

        if other_int == "seip":
            lines.append("RVTEST_CLR_SEXT_INT_S")

        elif other_int == "stip":
            lines.append("RVTEST_CLR_STIME_INT_S")

        elif other_int == "ssip":
            lines.append("RVTEST_CLR_SSW_INT_S")

        lines.extend(
            [
                f"LI(x{r_val}, {hex(LCOFI_BIT)})",
                f"csrc sip, x{r_val}   # clear LCOFIP for next iteration",
                "csrw sie, zero   # disable all before next iteration",
            ]
        )

    lines.extend(
        [
            "",
            f"csrci sstatus, {hex(SIE_BIT)}   # sstatus.SIE = 0",
            _csr_access("csrw RVMODEL_MHPMEVENT, zero   # stop counting, clear OF", "S"),
            "#if __riscv_xlen == 32",
            _csr_access("csrw CSR_MHPMEVENT3H, zero", "S"),
            "#endif",
            _csr_access("csrw RVMODEL_MHPMCOUNTER, zero", "S"),
        ]
    )

    test_data.int_regs.return_registers([r_val, r_temp, r_temp2, r_addr])

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
    tc = test_data.begin_test_chunk()
    tc.code.extend(_generate_lcofi_sip_s_tests(test_data))
    tc.code.extend(_generate_lcofip_priority_s_tests(test_data))
    test_chunks.append(test_data.end_test_chunk())
    test_chunks.extend(generate_sscofpmf_suite(test_data, "S"))
    return test_chunks
