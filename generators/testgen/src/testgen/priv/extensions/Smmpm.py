##################################
# priv/extensions/Smmpm.py
#
# Smmpm privileged extension test generator.
# Author : Umer Shahid & Ammarah Wakeel email:ammarahwakeel9@gmail.com (UET, JULY 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

from __future__ import annotations

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZpmCommon import (
    PMM_CONFIGS,
    Regs,
    alloc_pm_regs_paired,
    enable_fp_vector_state,
    free_pm_regs,
    jalr_pad_asm,
    mprv_data_section,
    pass_a_all_instructions,
    pass_c_misaligned,
    pass_d_mxr,
    pass_e_jalr,
    pass_f_fault_address,
    pass_g_csr_writes,
    pass_h_mprv,
    set_mxr,
    set_pmm_field,
)
from testgen.priv.registry import add_priv_test_generator

COVERGROUP = "Smmpm_cg"
_MSECCFG_PMM = 32
_CSR_TARGETS = ["mepc", "mscratch"]


def _emit_file(td: TestData, regs: Regs) -> list[str]:
    lines = mprv_data_section()
    lines += [
        comment_banner(
            "Smmpm pointer masking -- M-mode only",
            "mseccfg.PMM is programmed from M-mode; every probe also runs in M-mode.",
        ),
        "",
        *jalr_pad_asm(regs),
    ]
    lines += enable_fp_vector_state(regs)

    for pmm, pmlen, label in PMM_CONFIGS:
        prefix = f"{label}_mmode"
        lines.append(comment_banner(f"PMM={pmm:#04b} (PMLEN={pmlen}), M-mode"))
        lines += set_pmm_field("mseccfg", _MSECCFG_PMM, pmm, pmlen, regs.tmp)

        lines.append("#ifdef S_SUPPORTED")
        lines += set_mxr(False, regs.tmp, "mstatus")
        lines.append("#endif // S_SUPPORTED")

        lines += [f"LA(x{regs.base}, pm_lo_page)"]
        lines += pass_a_all_instructions(None, prefix, td, regs, COVERGROUP)
        lines += pass_c_misaligned(None, prefix, td, regs, COVERGROUP)
        lines += pass_e_jalr(None, prefix, td, regs, COVERGROUP)
        lines += pass_f_fault_address(None, prefix, td, regs, COVERGROUP)

        lines.append("#ifdef S_SUPPORTED")
        lines += pass_d_mxr(
            None,
            prefix,
            td,
            regs,
            COVERGROUP,
            goto_target_mode="",
            status_csr="mstatus",
        )
        lines += set_mxr(False, regs.tmp, "mstatus")
        lines.append("#endif // S_SUPPORTED")

        lines += pass_g_csr_writes(prefix, pmlen, td, regs, COVERGROUP, _CSR_TARGETS)

    lines += pass_h_mprv(td, regs, COVERGROUP, "mseccfg", _MSECCFG_PMM)
    lines += set_pmm_field("mseccfg", _MSECCFG_PMM, 0b00, 0, regs.tmp)
    lines.append("#ifdef S_SUPPORTED")
    lines += set_mxr(False, regs.tmp, "mstatus")
    lines.append("#endif // S_SUPPORTED")
    return lines


@add_priv_test_generator(
    "Smmpm",
    required_extensions=["Smmpm"],
    march_extensions=["S", "U", "I", "A", "F", "D", "C", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz"],
)
def make_smmpm(td: TestData) -> list[TestChunk]:
    regs = alloc_pm_regs_paired(td)

    tc = td.begin_test_chunk()
    tc.code = _emit_file(td, regs)
    chunks = [td.end_test_chunk()]

    free_pm_regs(td, regs)
    return chunks
