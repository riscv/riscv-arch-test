##################################
# priv/extensions/SmnpmU.py
#
# SmnpmU privileged extension test generator.
# Author : David Harris, Umer Shahid & Ammarah Wakeel email:ammarahwakeel9@gmail.com (UET, JULY 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZpmCommon import (
    EDGE_CASES,
    PMM_CONFIGS,
    SPLITS,
    data_page,
    generate_edge_case_tests,
    generate_instruction_sweep_tests,
    set_pmm_field,
)
from testgen.priv.registry import add_priv_test_generator

COVERGROUP = "SmnpmU_cg"


@add_priv_test_generator(
    "SmnpmU",
    required_extensions=["Smnpm"],
    forbidden_extensions=["S"],
    march_extensions=["I", "A", "F", "D", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz"],
)
def make_smnpmu(test_data: TestData) -> list[TestChunk]:
    chunks = []
    for pmm, pmlen, label in PMM_CONFIGS:
        # Each PMM setting is split into three files to keep every test under 100k instructions.
        # sweep_lowtags and sweep_hightags run every load, store, AMO, CBO and vector instruction through
        # a tagged pointer: the first with tags that leave bit 63 clear, the second with tags that set it.
        # edgecases holds the remaining checks, such as misaligned accesses, JALR, access faults and MXR.
        for split, uppers in SPLITS:
            tc = test_data.begin_test_chunk(split_name=f"{label}_{split}")
            tc.raw_data.extend(data_page("pm_lo_page"))
            prefix = f"{label}_bare"
            lines = [
                comment_banner(f"PMM={pmm:#04b} (PMLEN={pmlen}), physical addresses, {split}"),
                *set_pmm_field("menvcfg", pmm, pmlen, test_data, tsbi=True),
                *generate_instruction_sweep_tests(prefix, test_data, COVERGROUP, uppers),
            ]
            if split == EDGE_CASES:
                lines.extend(generate_edge_case_tests(prefix, test_data, COVERGROUP))
            lines.extend(set_pmm_field("menvcfg", 0b00, 0, test_data, tsbi=True))
            tc.code = lines
            chunks.append(test_data.end_test_chunk())
    return chunks
