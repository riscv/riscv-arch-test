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
    _PMM_FIELD_SHIFT,
    CP_SXL_CLEAR,
    CP_UXL_CLEAR,
    PMM_CONFIGS,
    Regs,
    _mprv_img_tables,
    alloc_pm_regs_paired,
    build_data_only_u_map_asm,
    enable_fp_vector_state,
    free_pm_regs,
    jalr_pad_asm,
    mprv_data_section,
    pass_a_all_instructions,
    pass_c_misaligned,
    pass_clear_on_xlen_change,
    pass_d_mxr,
    pass_e_jalr,
    pass_f_fault_address,
    pass_g_csr_writes,
    pass_i_mprv_mxr_pmm_loop,
    set_mxr,
    set_pmm_field,
)
from testgen.priv.registry import add_priv_test_generator

COVERGROUP = "Smmpm_cg"
_CSR_TARGETS = ["mepc", "mscratch"]
_MSTATUS_UXL_SHIFT = 32
_MSTATUS_SXL_SHIFT = 34


def _xlen_clear_checks(td: TestData, regs: Regs) -> list[str]:
    """Writing SXL or UXL to 32 must clear menvcfg.PMM, which governs S (SXL) or U without S (UXL).
    Checked from M-mode, whose own XLEN is unaffected; Ssnpm checks the senvcfg.PMM rule from S."""
    checks = [
        ("#ifdef S_SUPPORTED", "UDB_SXLEN_32", "sxl", CP_SXL_CLEAR, "menvcfg", _MSTATUS_SXL_SHIFT),
        ("#ifndef S_SUPPORTED", "UDB_UXLEN_32", "uxl", CP_UXL_CLEAR, "menvcfg", _MSTATUS_UXL_SHIFT),
    ]
    lines: list[str] = []
    for mode_guard, xlen_guard, tag, cp, pmm_csr, status_shift in checks:
        lines += ["#ifdef U_SUPPORTED", mode_guard, f"#ifdef {xlen_guard}"]
        for pmm, pmlen, label in PMM_CONFIGS:
            lines += set_pmm_field(pmm_csr, _PMM_FIELD_SHIFT, pmm, pmlen, regs.tmp)
            lines += pass_clear_on_xlen_change(
                None,
                f"{label}_{tag}",
                td,
                regs,
                cp=cp,
                cg=COVERGROUP,
                pmm_csr=pmm_csr,
                pmm_shift=_PMM_FIELD_SHIFT,
                status_csr="mstatus",
                status_shift=status_shift,
            )
        lines += set_pmm_field(pmm_csr, _PMM_FIELD_SHIFT, 0b00, 0, regs.tmp)
        lines += [f"#endif // {xlen_guard}", f"#endif // {mode_guard.split()[1]}", "#endif // U_SUPPORTED"]
    return lines


def _emit_file(td: TestData, regs: Regs, sv39_data_map: list[str]) -> list[str]:
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
        lines += set_pmm_field("mseccfg", _PMM_FIELD_SHIFT, pmm, pmlen, regs.tmp)
        lines.append("#ifdef S_SUPPORTED")
        lines += set_mxr(False, regs.tmp, "mstatus")
        lines.append("#endif // S_SUPPORTED")
        lines += [f"LA(x{regs.base}, pm_lo_page)"]
        lines += pass_a_all_instructions(None, prefix, td, regs, COVERGROUP)
        lines += pass_c_misaligned(None, prefix, td, regs, COVERGROUP)
        lines += pass_e_jalr(None, prefix, td, regs, COVERGROUP)
        lines += pass_f_fault_address(None, prefix, td, regs, COVERGROUP)
        lines.append("#ifdef S_SUPPORTED")
        lines += pass_d_mxr(None, prefix, td, regs, COVERGROUP, status_csr="mstatus")
        lines += set_mxr(False, regs.tmp, "mstatus")
        lines.append("#endif // S_SUPPORTED")
        lines += pass_g_csr_writes(prefix, pmlen, td, regs, COVERGROUP, _CSR_TARGETS)

    lines += _xlen_clear_checks(td, regs)

    # MPRV test using nested loop structure from testplan
    # Only tests Bare and Sv39 modes with limited upper bit patterns
    lines += pass_i_mprv_mxr_pmm_loop(td, regs, COVERGROUP, sv39_data_map, _PMM_FIELD_SHIFT)

    lines += set_pmm_field("mseccfg", _PMM_FIELD_SHIFT, 0b00, 0, regs.tmp)
    lines.append("#ifdef S_SUPPORTED")
    lines += set_mxr(False, regs.tmp, "mstatus")
    lines.append("#endif // S_SUPPORTED")
    return lines


@add_priv_test_generator(
    "Smmpm",
    required_extensions=["Smmpm"],
    march_extensions=["I", "A", "F", "D", "C", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz"],
    extra_defines=["#define BOOT_TO_MMODE", "#define RVTEST_ALLOW_OOS_FETCH_EPC"],
)
def make_smmpm(td: TestData) -> list[TestChunk]:
    # Build the sv39 data-only U-map ASM once, before regs claims the whole
    # register pool, so building it here avoids the register exhaustion.
    sv39_data_map = build_data_only_u_map_asm("sv39", _mprv_img_tables("sv39"), td)

    regs = alloc_pm_regs_paired(td)
    tc = td.begin_test_chunk()
    tc.code = _emit_file(td, regs, sv39_data_map)
    chunks = [td.end_test_chunk()]
    free_pm_regs(td, regs)
    return chunks
