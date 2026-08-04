##################################
# priv/extensions/SmnpmU.py
#
# SmnpmU privileged extension test generator.
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
    _li,
    enable_cascaded_envcfg_cbo_sse,
    pass_a_all_instructions,
    pass_c_misaligned,
    pass_clear_on_xlen_change,
    pass_e_jalr,
    pass_f_fault_address,
)
from testgen.priv.registry import add_priv_test_generator

COVERGROUP = "SmnpmU_cg"

_MENVCFG_PMM = 32
_MSTATUS_UXL_SHIFT = 32
_MSTATUS_FS_DIRTY = 3 << 13
_MSTATUS_VS_DIRTY = 3 << 9


def _set_pmm(val: int, pmlen: int, tmp: int) -> list[str]:
    mask = 0b11 << _MENVCFG_PMM
    return [
        f"# menvcfg.PMM={val:#04b} PMLEN={pmlen}",
        _li(tmp, mask),
        f"csrc menvcfg, x{tmp}",
        _li(tmp, val << _MENVCFG_PMM),
        f"csrs menvcfg, x{tmp}",
    ]


def _emit_file(td: TestData, regs: Regs) -> list[str]:
    lines = [
        ".pushsection .data",
        ".p2align 12",
        f"pm_lo_page: .dword {hex(VALUE_OLD)}",
        ".zero 4088",
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

    for pmm, pmlen, label in PMM_CONFIGS:
        prefix = f"{label}_bare"
        lines.append(comment_banner(f"PMM={pmm:#04b} (PMLEN={pmlen}), physical addresses"))
        lines += ["RVTEST_GOTO_MMODE"] + _set_pmm(pmm, pmlen, regs.tmp)
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

    lines += ["RVTEST_GOTO_MMODE", *_set_pmm(0b00, 0, regs.tmp)]
    return lines


@add_priv_test_generator(
    "SmnpmU",
    required_extensions=["Smnpm", "Zicsr", "U"],
    march_extensions=["I", "A", "F", "D", "C", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz"],
)
def make_smnpmu(td: TestData) -> list[TestChunk]:
    a, data, chk, tmp = td.int_regs.get_registers(4, reg_range=list(range(8, 16)))
    tmp2, base = td.int_regs.get_registers(2)
    fp, fp_c = td.float_regs.get_register(), td.float_regs.get_register(reg_range=list(range(8, 16)))
    regs = Regs(base=base, a=a, data=data, chk=chk, tmp=tmp, tmp2=tmp2, fp=fp, fp_c=fp_c)

    tc = td.begin_test_chunk()
    tc.code = _emit_file(td, regs)
    chunks = [td.end_test_chunk()]

    td.int_regs.return_registers([base, a, data, chk, tmp, tmp2])
    td.float_regs.return_registers([fp, fp_c])
    return chunks
