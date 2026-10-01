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
    PMM_CONFIGS,
    TAG_GROUPS,
    data_page,
    generate_fault_address_tests,
    generate_instruction_sweep_tests,
    generate_jalr_tests,
    generate_misaligned_tests,
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
        for part, uppers in enumerate(TAG_GROUPS, 1):
            tc = test_data.begin_test_chunk(split_name=f"{label}_part{part}")
            prefix = f"{label}_bare"
            lines = [
                ".pushsection .data",
                *data_page("pm_lo_page"),
                ".popsection",
                comment_banner(f"PMM={pmm:#04b} (PMLEN={pmlen}), physical addresses, part {part}"),
                *set_pmm_field("menvcfg", pmm, pmlen, test_data, tsbi=True),
                *generate_instruction_sweep_tests(prefix, test_data, COVERGROUP, uppers),
            ]
            if part == 1:
                lines.extend(
                    [
                        *generate_misaligned_tests(prefix, test_data, COVERGROUP),
                        *generate_jalr_tests(prefix, test_data, COVERGROUP),
                        *generate_fault_address_tests(prefix, test_data, COVERGROUP),
                    ]
                )
            lines.extend(set_pmm_field("menvcfg", 0b00, 0, test_data, tsbi=True))
            tc.code = lines
            chunks.append(test_data.end_test_chunk())
    return chunks
