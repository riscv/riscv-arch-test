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
    EDGE_CASES,
    PMM_CONFIGS,
    SPLITS,
    generate_csr_write_tests,
    generate_edge_case_tests,
    generate_instruction_sweep_tests,
    generate_mprv_mpp_m_tests,
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
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_smmpm(test_data: TestData) -> list[TestChunk]:
    chunks = []
    for pmm, pmlen, label in PMM_CONFIGS:
        # Each PMM setting is split into three files to keep every test under 100k instructions.
        # sweep_lowtags and sweep_hightags run every load, store, AMO, CBO and vector instruction through
        # a tagged pointer: the first with tags that leave bit 63 clear, the second with tags that set it.
        # edgecases holds the remaining checks, such as misaligned accesses, JALR, access faults and MXR.
        for split, uppers in SPLITS:
            tc = test_data.begin_test_chunk(split_name=f"{label}_{split}")
            tc.raw_data.extend(mprv_data_section())
            prefix = f"{label}_mmode"
            lines = [
                comment_banner(
                    f"Smmpm pointer masking -- M-mode only, PMM={pmm:#04b} (PMLEN={pmlen}), {split}",
                    "mseccfg.PMM is programmed from M-mode; every probe also runs in M-mode.",
                ),
                "",
                *set_pmm_field("mseccfg", pmm, pmlen, test_data),
                "#ifdef S_SUPPORTED",
                *set_mxr(False, test_data, "mstatus"),
                "#endif // S_SUPPORTED",
                *generate_instruction_sweep_tests(prefix, test_data, COVERGROUP, uppers),
            ]
            if split == EDGE_CASES:
                lines.extend(
                    [
                        *generate_edge_case_tests(
                            prefix,
                            test_data,
                            COVERGROUP,
                            status_csr="mstatus",
                            status_guard="S_SUPPORTED",
                        ),
                        *generate_csr_write_tests(prefix, pmlen, test_data, COVERGROUP, _CSR_TARGETS),
                    ]
                )
            lines.extend(set_pmm_field("mseccfg", 0b00, 0, test_data))
            tc.code = lines
            chunks.append(test_data.end_test_chunk())

    # MPRV with MPP=M only: the effective privilege stays M, so mseccfg.PMM
    # governs. The MPP=U and MPP=S cases are governed by senvcfg.PMM and
    # menvcfg.PMM, which come from Ssnpm and Smnpm, and live in SsnpmSm and
    # SmnpmSSm.
    tc = test_data.begin_test_chunk(split_name="mprv")
    tc.raw_data.extend(mprv_data_section())
    tc.code = [
        *generate_mprv_mpp_m_tests(test_data, COVERGROUP),
        *set_pmm_field("mseccfg", 0b00, 0, test_data),
        "#ifdef S_SUPPORTED",
        *set_mxr(False, test_data, "mstatus"),
        "#endif // S_SUPPORTED",
    ]
    chunks.append(test_data.end_test_chunk())
    return chunks
