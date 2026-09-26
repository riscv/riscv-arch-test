##################################
# priv/extensions/SmnpmS.py
#
# SmnpmS privileged extension test generator.
# Author : David Harris, Umer Shahid & Ammarah Wakeel email:ammarahwakeel9@gmail.com (UET, JULY 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZpmCommon import (
    _LEAF_PERMS_S,
    HIGH_VA,
    MODE_GUARDS,
    MODES,
    PMM_CONFIGS,
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


@add_priv_test_generator(
    "SmnpmS",
    required_extensions=["Smnpm", "S"],
    march_extensions=["I", "A", "F", "D", "C", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz"],
    extra_defines=["#define BOOT_TO_SMODE", "#define RVTEST_ALLOW_OOS_FETCH_EPC"],
)
def make_smnpms(test_data: TestData) -> list[TestChunk]:
    regs = alloc_pm_regs_paired(test_data)

    chunks = []
    for mode in MODES:
        tc = test_data.begin_test_chunk(split_name=mode)
        guard, is_bare = MODE_GUARDS[mode], mode == "bare"
        lines = [] if not guard else [f"#ifdef {guard}"]
        lines.extend([".pushsection .data", *data_pm_lo_page()])
        if not is_bare:
            lines.extend([*data_pm_hi_page(), *data_slvl_tables(mode)])
        lines.extend(
            [
                ".popsection",
                *jalr_pad_asm(regs),
                *enable_envcfg_cbo_sse(regs, "menvcfg", tsbi=True),
                *enable_fp_vector_state(regs, status_csr="sstatus"),
            ]
        )
        if not is_bare:
            lines.extend(
                [
                    *_pte_chain_asm(mode, HIGH_VA[mode], "pm_hi_page", _LEAF_PERMS_S),
                    *satp_setup(mode, regs),
                ]
            )

        for pmm, pmlen, label in PMM_CONFIGS:
            prefix = f"{label}_{mode}"
            lines.extend(
                [
                    *set_pmm_field("menvcfg", _MENVCFG_PMM, pmm, pmlen, regs.tmp, tsbi=True),
                    f"LA(x{regs.base}, pm_lo_page)",
                    *pass_a_all_instructions(None, prefix, test_data, regs, COVERGROUP),
                ]
            )
            if not is_bare:
                lines.extend(pass_b_sign_extension(None, prefix, mode, test_data, regs, COVERGROUP))
            lines.extend(
                [
                    *pass_c_misaligned(None, prefix, test_data, regs, COVERGROUP),
                    *pass_e_jalr(None, prefix, test_data, regs, COVERGROUP, mxr=0),
                    *pass_f_fault_address(None, prefix, test_data, regs, COVERGROUP),
                    *pass_d_mxr(None, prefix, test_data, regs, COVERGROUP),
                    *pass_e_jalr(None, prefix, test_data, regs, COVERGROUP, mxr=1),
                    *set_mxr(False, regs.tmp),
                    *pass_g_csr_writes(prefix, pmlen, test_data, regs, COVERGROUP, ["sepc", "sscratch"]),
                ]
            )

        lines.extend(
            [
                *set_pmm_field("menvcfg", _MENVCFG_PMM, 0b00, 0, regs.tmp, tsbi=True),
                *set_mxr(False, regs.tmp),
            ]
        )
        if not is_bare:
            lines.extend(satp_clear(regs))
        if guard:
            lines.append(f"#endif // {guard}")
        tc.code = lines
        chunks.append(test_data.end_test_chunk())

    free_pm_regs(test_data, regs)
    return chunks
