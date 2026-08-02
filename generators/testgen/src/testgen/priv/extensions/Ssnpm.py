##################################
# priv/extensions/Ssnpm.py
#
# Ssnpm privileged extension test generator.
# Author : Umer Shahid & Ammarah Wakeel  email:ammarahwakeel9@gmail.com (UET, JULY 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

from __future__ import annotations

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZpmCommon import (
    CP_UXL_CLEAR,
    PMM_CONFIGS,
    VALUE_OLD,
    Regs,
    _grant_umode_access_to_identity_map_asm,
    _li,
    _pte_chain_asm,
    enable_cascaded_envcfg_cbo_sse,
    pass_a_all_instructions,
    pass_b_sign_extension,
    pass_c_misaligned,
    pass_clear_on_xlen_change,
    pass_d_mxr,
    pass_e_jalr,
    pass_f_fault_address,
    set_mxr,
)
from testgen.priv.registry import add_priv_test_generator

COVERGROUP = "Ssnpm_cg"

_SENVCFG_PMM = 32
_MSTATUS_FS_DIRTY = 3 << 13
_MSTATUS_VS_DIRTY = 3 << 9
_MODES = ["bare", "sv39", "sv48", "sv57"]
_GUARDS = {m: None if m == "bare" else f"{m.upper()}_SUPPORTED" for m in _MODES}
_LEVELS = {"sv39": 2, "sv48": 3, "sv57": 4}
_HIGH_VA = {"sv39": 0xFFFF_FFC0_0000_0000, "sv48": 0xFFFF_8000_0000_0000, "sv57": 0xFFFF_8000_0000_0000}


def _set_pmm(val: int, pmlen: int, tmp: int) -> list[str]:
    mask = 0b11 << _SENVCFG_PMM
    return [
        f"# senvcfg.PMM={val:#04b} PMLEN={pmlen}",
        _li(tmp, mask),
        f"csrc senvcfg, x{tmp}",
        _li(tmp, val << _SENVCFG_PMM),
        f"csrs senvcfg, x{tmp}",
    ]


def _emit_mode(mode: str, td: TestData, regs: Regs) -> list[str]:
    guard, is_bare = _GUARDS[mode], mode == "bare"
    lines = [] if not guard else [f"#ifdef {guard}"]
    lines += [".pushsection .data", ".p2align 12", f"pm_lo_page: .dword {hex(VALUE_OLD)}", ".zero 4088"]
    if not is_bare:
        lines += [".p2align 12", f"pm_hi_page: .dword {hex(VALUE_OLD)}", ".zero 4088"]
        for i in range(_LEVELS[mode]):
            lines += [".p2align 12", f"rvtest_slvl{i}_pg_tbl: .zero 4096"]
    lines += [
        ".popsection",
        "j pm_jalr_pad_end",
        "pm_jalr_pad:",
        f"addi x{regs.chk}, x{regs.chk}, 1",
        "jr ra",
        "pm_jalr_pad_end:",
        "RVTEST_GOTO_MMODE",
        "",
    ]

    lines += enable_cascaded_envcfg_cbo_sse(regs)
    lines += [
        "",
        "# FP and vector state must be enabled for the FP/vector probes to be legal.",
        _li(regs.tmp, _MSTATUS_FS_DIRTY | _MSTATUS_VS_DIRTY),
        f"csrs mstatus, x{regs.tmp}",
    ]

    if not is_bare:
        lines += ["", *_grant_umode_access_to_identity_map_asm(mode, regs)]
        lines += ["", *_pte_chain_asm(mode, _HIGH_VA[mode], "pm_hi_page")]
        lines += ["sfence.vma", f"SATP_SETUP_RV64({mode})", "sfence.vma"]

    lines += [
        "",
        "# Take every trap in M-mode: U-mode code running under an active satp",
        "# needs PTE_U on the page it executes from, and S-mode may not fetch",
        "# from a U=1 page, so an S-mode handler there would trap forever.",
        f"csrr x{regs.tmp2}, medeleg      # stash the framework's delegation mask",
        "csrw medeleg, zero",
    ]

    for pmm, pmlen, label in PMM_CONFIGS:
        prefix = f"{label}_{mode}"
        lines.append(comment_banner(f"PMM={pmm:#04b} (PMLEN={pmlen}), satp={mode.upper()}"))
        lines += ["RVTEST_GOTO_MMODE"] + _set_pmm(pmm, pmlen, regs.tmp) + set_mxr(False, regs.tmp)
        lines += ["RVTEST_TSBI_GOTO_UMODE", f"LA(x{regs.base}, pm_lo_page)"]

        lines += pass_a_all_instructions(None, prefix, td, regs, COVERGROUP)
        if not is_bare:
            lines += pass_b_sign_extension(None, prefix, mode, td, regs, COVERGROUP)
        lines += pass_c_misaligned(None, prefix, td, regs, COVERGROUP)
        lines += pass_e_jalr(None, prefix, td, regs, COVERGROUP, mxr=0)
        lines += pass_f_fault_address(None, prefix, td, regs, COVERGROUP)
        lines += pass_d_mxr(None, prefix, td, regs, COVERGROUP)
        lines += pass_e_jalr(None, prefix, td, regs, COVERGROUP, mxr=1)

        lines += ["RVTEST_GOTO_MMODE", *set_mxr(False, regs.tmp)]
        lines += pass_clear_on_xlen_change(
            None,
            prefix,
            td,
            regs,
            cp=CP_UXL_CLEAR,
            cg=COVERGROUP,
            pmm_csr="senvcfg",
            pmm_shift=32,
            status_csr="sstatus",
            status_shift=32,
            ifdef_guard="UDB_UXLEN_64",
        )

    lines += ["RVTEST_GOTO_MMODE"]
    lines += _set_pmm(0b00, 0, regs.tmp)
    lines += set_mxr(False, regs.tmp)
    lines += ["csrwi satp, 0", "sfence.vma", f"csrw medeleg, x{regs.tmp2}   # restore the framework's delegation mask"]
    if guard:
        lines.append(f"#endif // {guard}")
    return lines


@add_priv_test_generator(
    "Ssnpm",
    required_extensions=["Ssnpm", "Zicsr", "S", "U"],
    march_extensions=["I", "A", "F", "D", "C", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz"],
)
def make_ssnpm(td: TestData) -> list[TestChunk]:
    a, data, chk, tmp = td.int_regs.get_registers(4, reg_range=list(range(8, 16)))
    tmp2, base = td.int_regs.get_registers(2)
    fp, fp_c = td.float_regs.get_register(), td.float_regs.get_register(reg_range=list(range(8, 16)))
    regs = Regs(base=base, a=a, data=data, chk=chk, tmp=tmp, tmp2=tmp2, fp=fp, fp_c=fp_c)

    chunks = []
    for mode in _MODES:
        tc = td.begin_test_chunk(split_name=mode)
        tc.code = _emit_mode(mode, td, regs)
        chunks.append(td.end_test_chunk())

    td.int_regs.return_registers([base, a, data, chk, tmp, tmp2])
    td.float_regs.return_registers([fp, fp_c])
    return chunks
