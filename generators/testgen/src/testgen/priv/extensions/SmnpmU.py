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
    alloc_pm_regs_paired,
    data_pm_lo_page,
    enable_envcfg_cbo_sse,
    enable_fp_vector_state,
    free_pm_regs,
    jalr_pad_asm,
    pass_a_all_instructions,
    pass_c_misaligned,
    pass_e_jalr,
    pass_f_fault_address,
    set_pmm_field,
)
from testgen.priv.registry import add_priv_test_generator

COVERGROUP = "SmnpmU_cg"


@add_priv_test_generator(
    "SmnpmU",
    required_extensions=["Smnpm"],
    forbidden_extensions=["S"],
    march_extensions=["I", "A", "F", "D", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz"],
    extra_defines=["#define RVTEST_ALLOW_OOS_FETCH_EPC"],
)
def make_smnpmu(test_data: TestData) -> list[TestChunk]:
    regs = alloc_pm_regs_paired(test_data)

    tc = test_data.begin_test_chunk()
    lines = [
        ".pushsection .data",
        *data_pm_lo_page(),
        ".popsection",
        *jalr_pad_asm(regs),
        *enable_envcfg_cbo_sse(regs, csr="menvcfg", tsbi=True),
        *enable_fp_vector_state(regs, tsbi=True),
    ]

    for pmm, pmlen, label in PMM_CONFIGS:
        prefix = f"{label}_bare"
        lines.extend(
            [
                comment_banner(f"PMM={pmm:#04b} (PMLEN={pmlen}), physical addresses"),
                *set_pmm_field("menvcfg", pmm, pmlen, regs.tmp, tsbi=True),
                f"LA(x{regs.base}, pm_lo_page)",
                *pass_a_all_instructions(None, prefix, test_data, regs, COVERGROUP),
                *pass_c_misaligned(None, prefix, test_data, regs, COVERGROUP),
                *pass_e_jalr(None, prefix, test_data, regs, COVERGROUP),
                *pass_f_fault_address(None, prefix, test_data, regs, COVERGROUP),
            ]
        )

    lines.extend(set_pmm_field("menvcfg", 0b00, 0, regs.tmp, tsbi=True))
    tc.code = lines
    chunks = [test_data.end_test_chunk()]

    free_pm_regs(test_data, regs)
    return chunks
