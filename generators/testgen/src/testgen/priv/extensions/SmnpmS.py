##################################
# priv/extensions/SmnpmS.py
#
# SmnpmS privileged extension test generator.
# Author : Umer Shahid & Ammarah Wakeel email:ammarahwakeel9@gmail.com (UET, JULY 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

from __future__ import annotations

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZpmCommon import (
    _LEAF_PERMS_S,
    CP_SXL_CLEAR,
    HIGH_VA,
    MODE_GUARDS,
    MODES,
    PMM_CONFIGS,
    Regs,
    _pte_chain_asm,
    data_pm_hi_page,
    data_pm_lo_page,
    data_slvl_tables,
    enable_envcfg_cbo_sse,
    enable_fp_vector_state,
    jalr_pad_asm,
    pass_a_all_instructions,
    pass_b_sign_extension,
    pass_c_misaligned,
    pass_clear_on_xlen_change,
    pass_d_mxr,
    pass_e_jalr,
    pass_f_fault_address,
    pass_g_csr_writes,
    set_mxr,
    set_pmm_field,
)
from testgen.priv.registry import add_priv_test_generator

COVERGROUP = "SmnpmS_cg"
_MENVCFG_PMM = 32


def _set_pmm(val: int, pmlen: int, tmp: int) -> list[str]:
    return set_pmm_field("menvcfg", _MENVCFG_PMM, val, pmlen, tmp)


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

    lines += enable_envcfg_cbo_sse(regs, "menvcfg")
    lines += enable_fp_vector_state(regs)

    if not is_bare:
        lines += _pte_chain_asm(mode, HIGH_VA[mode], "pm_hi_page", _LEAF_PERMS_S)
        lines += ["sfence.vma", f"SATP_SETUP_RV64({mode})", "sfence.vma"]

    for pmm, pmlen, label in PMM_CONFIGS:
        prefix = f"{label}_{mode}"
        lines += ["RVTEST_GOTO_MMODE"] + _set_pmm(pmm, pmlen, regs.tmp)
        lines += ["RVTEST_TSBI_GOTO_SMODE", f"LA(x{regs.base}, pm_lo_page)"]

        lines += pass_a_all_instructions(None, prefix, td, regs, COVERGROUP)
        if not is_bare:
            lines += pass_b_sign_extension(None, prefix, mode, td, regs, COVERGROUP)
        lines += pass_c_misaligned(None, prefix, td, regs, COVERGROUP)
        lines += pass_e_jalr(None, prefix, td, regs, COVERGROUP, mxr=0)
        lines += pass_f_fault_address(None, prefix, td, regs, COVERGROUP)
        lines += pass_d_mxr(
            None,
            prefix,
            td,
            regs,
            COVERGROUP,
            goto_target_mode="RVTEST_TSBI_GOTO_SMODE",
            status_csr="mstatus",
        )
        lines += pass_e_jalr(None, prefix, td, regs, COVERGROUP, mxr=1)

        lines += ["RVTEST_GOTO_MMODE", *set_mxr(False, regs.tmp, "mstatus")]
        lines += ["RVTEST_TSBI_GOTO_SMODE"]

        lines += pass_g_csr_writes(prefix, pmlen, td, regs, COVERGROUP, ["sepc", "sscratch"])

        lines.append("RVTEST_GOTO_MMODE")
        lines += pass_clear_on_xlen_change(
            None,
            prefix,
            td,
            regs,
            cp=CP_SXL_CLEAR,
            cg=COVERGROUP,
            pmm_csr="menvcfg",
            pmm_shift=32,
            status_csr="mstatus",
            status_shift=34,
        )

    lines += ["RVTEST_GOTO_MMODE"] + _set_pmm(0b00, 0, regs.tmp)
    lines += [*set_mxr(False, regs.tmp, "mstatus"), "csrwi satp, 0", "sfence.vma"]
    if guard:
        lines.append(f"#endif // {guard}")
    return lines


@add_priv_test_generator(
    "SmnpmS",
    required_extensions=["Smnpm", "Zicsr", "S"],
    march_extensions=["I", "A", "F", "D", "C", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz"],
)
def make_smnpms(td: TestData) -> list[TestChunk]:

    dest_pair, source_pair = td.int_regs.get_registers(2, reg_range=[8, 14])
    a = td.int_regs.get_registers(1, reg_range=[9, 13, 15])[0]
    tmp, tmp2, base = td.int_regs.get_registers(3)
    chk = dest_pair
    data = source_pair

    fp, fp_c = (
        td.float_regs.get_register(),
        td.float_regs.get_register(reg_range=list(range(8, 16))),
    )

    regs = Regs(
        base=base,
        a=a,
        data=data,
        chk=chk,
        tmp=tmp,
        tmp2=tmp2,
        fp=fp,
        fp_c=fp_c,
        dest_pair=dest_pair,
        source_pair=source_pair,
    )

    chunks = []
    for mode in MODES:
        tc = td.begin_test_chunk(split_name=mode)
        tc.code = _emit_mode(mode, td, regs)
        chunks.append(td.end_test_chunk())

    td.int_regs.return_registers([dest_pair, source_pair, a, tmp, tmp2, base])
    td.float_regs.return_registers([fp, fp_c])
    return chunks
