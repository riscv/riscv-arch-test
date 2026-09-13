##################################
# priv/extensions/SmnpmS.py
#
# SmnpmS privileged extension test generator.
# Author : David Harris, Umer Shahid & Ammarah Wakeel email:ammarahwakeel9@gmail.com (UET, JULY 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

from __future__ import annotations

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZpmCommon import (
    _LEAF_PERMS_S,
    HIGH_VA,
    MODE_GUARDS,
    MODES,
    PMM_CONFIGS,
    Regs,
    _pte_chain_asm,
    alloc_pm_regs_paired,
    data_pm_hi_page,
    data_pm_lo_page,
    data_slvl_tables,
    enable_envcfg_cbo_sse,
    enable_fp_vector_state,
    free_pm_regs,
    jalr_pad_asm,
    pass_a_all_instructions,
    pass_b_sign_extension,
    pass_c_misaligned,
    pass_d_mxr,
    pass_e_jalr,
    pass_f_fault_address,
    pass_g_csr_writes,
    satp_clear,
    satp_setup,
    set_mxr,
    set_pmm_field,
)
from testgen.priv.registry import add_priv_test_generator

COVERGROUP = "SmnpmS_cg"
_MENVCFG_PMM = 32


def _emit_mode(mode: str, td: TestData, regs: Regs) -> list[str]:
    guard, is_bare = MODE_GUARDS[mode], mode == "bare"
    lines = [] if not guard else [f"#ifdef {guard}"]
    lines += [
        ".pushsection .data",
        *data_pm_lo_page(),
    ]
    if not is_bare:
        lines += data_pm_hi_page()
        lines += data_slvl_tables(mode)
    lines += [
        ".popsection",
        *jalr_pad_asm(regs),
    ]

    lines += enable_envcfg_cbo_sse(regs, "menvcfg", tsbi=True)
    lines += enable_fp_vector_state(regs, status_csr="sstatus")

    if not is_bare:
        lines += _pte_chain_asm(mode, HIGH_VA[mode], "pm_hi_page", _LEAF_PERMS_S)
        lines += satp_setup(mode, regs)

    for pmm, pmlen, label in PMM_CONFIGS:
        prefix = f"{label}_{mode}"
        lines += set_pmm_field("menvcfg", _MENVCFG_PMM, pmm, pmlen, regs.tmp, tsbi=True)
        lines += [f"LA(x{regs.base}, pm_lo_page)"]

        lines += pass_a_all_instructions(None, prefix, td, regs, COVERGROUP)
        if not is_bare:
            lines += pass_b_sign_extension(None, prefix, mode, td, regs, COVERGROUP)
        lines += pass_c_misaligned(None, prefix, td, regs, COVERGROUP)
        lines += pass_e_jalr(None, prefix, td, regs, COVERGROUP, mxr=0)
        lines += pass_f_fault_address(None, prefix, td, regs, COVERGROUP)
        lines += pass_d_mxr(None, prefix, td, regs, COVERGROUP)
        lines += pass_e_jalr(None, prefix, td, regs, COVERGROUP, mxr=1)

        lines += set_mxr(False, regs.tmp)

        lines += pass_g_csr_writes(prefix, pmlen, td, regs, COVERGROUP, ["sepc", "sscratch"])

    lines += set_pmm_field("menvcfg", _MENVCFG_PMM, 0b00, 0, regs.tmp, tsbi=True)
    lines += set_mxr(False, regs.tmp)
    if not is_bare:
        lines += satp_clear(regs)
    if guard:
        lines.append(f"#endif // {guard}")
    return lines


@add_priv_test_generator(
    "SmnpmS",
    required_extensions=["Smnpm", "S"],
    march_extensions=["I", "A", "F", "D", "C", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz"],
    extra_defines=["#define BOOT_TO_SMODE", "#define RVTEST_ALLOW_OOS_FETCH_EPC"],
)
def make_smnpms(td: TestData) -> list[TestChunk]:
    regs = alloc_pm_regs_paired(td)

    chunks = []
    for mode in MODES:
        tc = td.begin_test_chunk(split_name=mode)
        tc.code = _emit_mode(mode, td, regs)
        chunks.append(td.end_test_chunk())

    free_pm_regs(td, regs)
    return chunks
