##################################
# priv/extensions/SmnpmU.py
#
# SmnpmU privileged extension test generator.
# Author : Umer Shahid & Ammarah Wakeel email:ammarahwakeel9@gmail.com (UET, JULY 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

from __future__ import annotations

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZpmCommon import (
    CP_UXL_CLEAR,
    PMM_CONFIGS,
    Regs,
    alloc_pm_regs_paired,
    data_pm_lo_page,
    enable_cascaded_envcfg_cbo_sse,
    enable_fp_vector_state,
    free_pm_regs,
    jalr_pad_asm,
    pass_a_all_instructions,
    pass_c_misaligned,
    pass_clear_on_xlen_change,
    pass_e_jalr,
    pass_f_fault_address,
    set_pmm_field,
)
from testgen.priv.registry import add_priv_test_generator

COVERGROUP = "SmnpmU_cg"
_MENVCFG_PMM = 32
_MSTATUS_UXL_SHIFT = 32


def _emit_file(td: TestData, regs: Regs) -> list[str]:
    lines = [
        ".pushsection .data",
        *data_pm_lo_page(),
        ".popsection",
        *jalr_pad_asm(regs),
    ]

    lines += enable_cascaded_envcfg_cbo_sse(regs)
    lines += enable_fp_vector_state(regs)

    for pmm, pmlen, label in PMM_CONFIGS:
        prefix = f"{label}_bare"
        lines.append(comment_banner(f"PMM={pmm:#04b} (PMLEN={pmlen}), physical addresses"))
        lines += ["RVTEST_GOTO_MMODE"] + set_pmm_field("menvcfg", _MENVCFG_PMM, 0b00, 0, regs.tmp)
        lines += ["RVTEST_TSBI_GOTO_UMODE", f"LA(x{regs.base}, pm_lo_page)"]

        lines += pass_a_all_instructions(None, prefix, td, regs, COVERGROUP)
        lines += pass_c_misaligned(None, prefix, td, regs, COVERGROUP)
        lines += pass_e_jalr(None, prefix, td, regs, COVERGROUP)
        lines += pass_f_fault_address(None, prefix, td, regs, COVERGROUP)
        lines += pass_clear_on_xlen_change(
            None,
            prefix,
            td,
            regs,
            cp=CP_UXL_CLEAR,
            cg=COVERGROUP,
            pmm_csr="menvcfg",
            pmm_shift=_MENVCFG_PMM,
            status_csr="mstatus",
            status_shift=_MSTATUS_UXL_SHIFT,
            ifdef_guard="UDB_UXLEN_64",
        )

    lines += ["RVTEST_GOTO_MMODE"] + set_pmm_field("menvcfg", _MENVCFG_PMM, 0b00, 0, regs.tmp)
    return lines


@add_priv_test_generator(
    "SmnpmU",
    required_extensions=["Smnpm", "Zicsr", "U"],
    march_extensions=["I", "A", "F", "D", "C", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz"],
)
def make_smnpmu(td: TestData) -> list[TestChunk]:
    regs = alloc_pm_regs_paired(td)

    tc = td.begin_test_chunk()
    tc.code = _emit_file(td, regs)
    chunks = [td.end_test_chunk()]

    free_pm_regs(td, regs)
    return chunks
