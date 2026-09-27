##################################
# priv/extensions/Smmpm.py
#
# Smmpm privileged extension test generator.
# Author : Umer Shahid & Ammarah Wakeel email:ammarahwakeel9@gmail.com (UET, JULY 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZpmCommon import (
    PMM_CONFIGS,
    generate_csr_write_tests,
    generate_fault_address_tests,
    generate_instruction_sweep_tests,
    generate_jalr_tests,
    generate_misaligned_tests,
    generate_mprv_tests,
    generate_mxr_tests,
    mprv_data_section,
    set_mxr,
    set_pmm_field,
)
from testgen.priv.registry import add_priv_test_generator

COVERGROUP = "Smmpm_cg"
_CSR_TARGETS = ["mepc", "mscratch"]


@add_priv_test_generator(
    "Smmpm",
    required_extensions=["Smmpm"],
    march_extensions=["I", "A", "F", "D", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz"],
    extra_defines=["#define BOOT_TO_MMODE", "#define RVTEST_ALLOW_OOS_FETCH_EPC"],
)
def make_smmpm(test_data: TestData) -> list[TestChunk]:
    tc = test_data.begin_test_chunk()
    lines = [
        *mprv_data_section(),
        comment_banner(
            "Smmpm pointer masking -- M-mode only",
            "mseccfg.PMM is programmed from M-mode; every probe also runs in M-mode.",
        ),
        "",
    ]
    for pmm, pmlen, label in PMM_CONFIGS:
        prefix = f"{label}_mmode"
        lines.extend(
            [
                comment_banner(f"PMM={pmm:#04b} (PMLEN={pmlen}), M-mode"),
                *set_pmm_field("mseccfg", pmm, pmlen, test_data),
                "#ifdef S_SUPPORTED",
                *set_mxr(False, test_data, "mstatus"),
                "#endif // S_SUPPORTED",
                *generate_instruction_sweep_tests(prefix, test_data, COVERGROUP),
                *generate_misaligned_tests(prefix, test_data, COVERGROUP),
                *generate_jalr_tests(prefix, test_data, COVERGROUP),
                *generate_fault_address_tests(prefix, test_data, COVERGROUP),
                "#ifdef S_SUPPORTED",
                *generate_mxr_tests(prefix, test_data, COVERGROUP, status_csr="mstatus"),
                *set_mxr(False, test_data, "mstatus"),
                "#endif // S_SUPPORTED",
                *generate_csr_write_tests(prefix, pmlen, test_data, COVERGROUP, _CSR_TARGETS),
            ]
        )

    lines.extend(
        [
            # MPRV test using nested loop structure from testplan
            # Only tests Bare and Sv39 modes with limited upper bit patterns
            *generate_mprv_tests(test_data, COVERGROUP),
            *set_pmm_field("mseccfg", 0b00, 0, test_data),
            "#ifdef S_SUPPORTED",
            *set_mxr(False, test_data, "mstatus"),
            "#endif // S_SUPPORTED",
        ]
    )
    tc.code = lines
    chunks = [test_data.end_test_chunk()]
    return chunks
