##################################
# priv/extensions/Smmpm.py
#
# Smmpm privileged extension test generator.
# Author : Umer Shahid & Ammarah Wakeel  email:ammarahwakeel9@gmail.com (UET, JULY 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

from __future__ import annotations

from testgen.asm.csr import gen_csr_write_sigupd
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZpmCommon import (
    CP_CSR,
    CP_MPRV,
    LEVELS_BELOW_ROOT,
    PMM_CONFIGS,
    UPPER_PATTERNS,
    VALUE_OLD,
    Regs,
    _fixed,
    _guard_close,
    _guard_open,
    _li,
    _sentinel,
    _tid,
    pass_a_all_instructions,
    pass_c_misaligned,
    pass_d_mxr,
    pass_e_jalr,
    pass_f_fault_address,
    set_mxr,
)
from testgen.priv.registry import add_priv_test_generator

COVERGROUP = "Smmpm_cg"
_MSECCFG_PMM = 32
_MSTATUS_MPRV = 1 << 17
_MSTATUS_SUM = 1 << 18
_MSTATUS_MPP_SHIFT = 11
_MPP_U, _MPP_S = 0b00, 0b01
_CSR_TARGETS = ["mepc", "mscratch"]

_SATP_MODES = ["bare", "sv39", "sv48", "sv57"]
_SATP_GUARD = {"bare": None, "sv39": "SV39_SUPPORTED", "sv48": "SV48_SUPPORTED", "sv57": "SV57_SUPPORTED"}
_NONLEAF_PERMS = "PTE_V"
_MPRV_LEAF_PERMS = "PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V"
_MPRV_VA = 0x0000_0020_0000_0000


def _set_pmm(val: int, pmlen: int, tmp: int) -> list[str]:
    mask = 0b11 << _MSECCFG_PMM
    return [
        f"# mseccfg.PMM={val:#04b} PMLEN={pmlen}",
        _li(tmp, mask),
        f"csrc mseccfg, x{tmp}",
        _li(tmp, val << _MSECCFG_PMM),
        f"csrs mseccfg, x{tmp}",
    ]


def _set_mprv(enable: bool, mpp: int, tmp: int) -> list[str]:
    if enable:
        return [
            _li(tmp, 0b11 << _MSTATUS_MPP_SHIFT),
            f"csrc mstatus, x{tmp}",
            _li(tmp, mpp << _MSTATUS_MPP_SHIFT),
            f"csrs mstatus, x{tmp}",
            _li(tmp, _MSTATUS_MPRV),
            f"csrs mstatus, x{tmp}",
        ]
    return [_li(tmp, _MSTATUS_MPRV), f"csrc mstatus, x{tmp}"]


def _set_sum(enable: bool, tmp: int) -> list[str]:
    op = "csrs" if enable else "csrc"
    return [f"# mstatus.SUM = {int(enable)}", _li(tmp, _MSTATUS_SUM), f"{op} mstatus, x{tmp}"]


def _write_pte(table_label: str, vpn_index: int, target_label: str, perms: str) -> list[str]:
    return [
        f"LA(x6, {table_label})",
        f"LI(x7, {vpn_index * 8})",
        "add x6, x6, x7",
        f"LA(x8, {target_label})",
        f"LI(x7, {perms})",
        "or x8, x8, x7",
        "sd x8, 0(x6)",
    ]


def _mprv_pte_chain(mode: str, va: int) -> list[str]:
    if mode == "bare":
        return []
    vpn_shifts = {"sv39": [30, 21, 12], "sv48": [39, 30, 21, 12], "sv57": [48, 39, 30, 21, 12]}
    vpn_indices = [(va >> s) & 0x1FF for s in vpn_shifts[mode]]
    lines = [f"# {mode.upper()}: PTE chain for VA {hex(va)}"]
    current = "rvtest_Sroot_pg_tbl"
    for i, vpn in enumerate(vpn_indices[:-1]):
        nxt = f"rvtest_mprv_slvl{len(vpn_indices) - 2 - i}_pg_tbl_{mode}"
        lines += _write_pte(current, vpn, nxt, _NONLEAF_PERMS)
        current = nxt
    lines += _write_pte(current, vpn_indices[-1], "mprv_page", _MPRV_LEAF_PERMS)
    return lines


def _probe_mprv_load(mn: str, mpp: int, tid: str, td: TestData, regs: Regs) -> list[str]:

    return [
        f"LA(x{regs.tmp}, mprv_page)",
        _li(regs.data, VALUE_OLD),
        f"sd x{regs.data}, 0(x{regs.tmp})   # seed, MPRV=0: untranslated physical write",
        *_sentinel(regs),
        td.add_testcase(tid, CP_MPRV, COVERGROUP),
        *_set_mprv(True, mpp, regs.tmp),
        *_fixed(f"{mn} x{regs.chk}, 0(x{regs.a})"),
        *_set_mprv(False, 0, regs.tmp),
        write_sigupd(regs.chk, td),
    ]


def _probe_mprv_store(mn: str, readback: str, mpp: int, tid: str, td: TestData, regs: Regs) -> list[str]:
    return [
        f"LA(x{regs.tmp}, mprv_page)",
        _li(regs.data, VALUE_OLD),
        f"sd x{regs.data}, 0(x{regs.tmp})   # seed, MPRV=0: untranslated physical write",
        _li(regs.data, 0xA5A5_A5A5_A5A5_A5A5),
        td.add_testcase(tid, CP_MPRV, COVERGROUP),
        *_set_mprv(True, mpp, regs.tmp),
        *_fixed(f"{mn} x{regs.data}, 0(x{regs.a})"),
        *_set_mprv(False, 0, regs.tmp),
        f"LA(x{regs.tmp}, mprv_page)",
        *_fixed(f"{readback} x{regs.chk}, 0(x{regs.tmp})   # read back physically, MPRV=0"),
        write_sigupd(regs.chk, td),
    ]


def _mprv_mpp_probes(prefix: str, mpp_label: str, mpp_val: int, td: TestData, regs: Regs) -> list[str]:
    lines = []
    for upper in UPPER_PATTERNS:
        lines += [_li(regs.tmp, upper << 48), f"or x{regs.a}, x{regs.base}, x{regs.tmp}"]
        base = f"{prefix}_{mpp_label}"
        lines += _probe_mprv_load("lw", mpp_val, _tid(base, upper, "lw"), td, regs)
        lines += _probe_mprv_store("sw", "lw", mpp_val, _tid(base, upper, "sw"), td, regs)
    return lines


def _pass_h_mprv(td: TestData, regs: Regs) -> list[str]:
    """MPRV=1 with MPP={U,S} across all satp modes"""
    lines = [comment_banner("MPRV=1 uses MPP's translation/protection"), f"csrr x{regs.tmp2}, mstatus   # snapshot"]
    lines += _set_sum(True, regs.tmp)
    for mode in _SATP_MODES:
        guard = _SATP_GUARD[mode]
        lines += _guard_open(guard)
        if mode == "bare":
            lines.append(f"LA(x{regs.base}, mprv_page)")
        else:
            lines += _mprv_pte_chain(mode, _MPRV_VA)
            lines += ["sfence.vma", f"SATP_SETUP_RV64({mode})", "sfence.vma", _li(regs.base, _MPRV_VA)]
        for pmm, pmlen, label in PMM_CONFIGS:
            prefix = f"{label}_{mode}_mprv"
            lines += ["RVTEST_GOTO_MMODE", *_set_pmm(pmm, pmlen, regs.tmp)]
            lines += _guard_open("U_SUPPORTED")
            lines += _mprv_mpp_probes(prefix, "u", _MPP_U, td, regs)
            lines += _guard_close("U_SUPPORTED")
            lines += _guard_open("S_SUPPORTED")
            lines += _mprv_mpp_probes(prefix, "s", _MPP_S, td, regs)
            lines += _guard_close("S_SUPPORTED")
        if mode != "bare":
            lines += ["RVTEST_GOTO_MMODE", "csrwi satp, 0", "sfence.vma"]
        lines += _guard_close(guard)
    lines.append(f"csrw mstatus, x{regs.tmp2}   # restore")
    lines.append(f"LA(x{regs.base}, pm_lo_page)")
    return lines


def _data_section() -> list[str]:
    lines = [
        ".pushsection .data",
        ".p2align 12",
        f"pm_lo_page: .dword {hex(VALUE_OLD)}",
        ".zero 4088",
        ".p2align 12",
        f"mprv_page: .dword {hex(VALUE_OLD)}",
        ".zero 4088",
    ]
    for mode, guard in [("sv39", "SV39_SUPPORTED"), ("sv48", "SV48_SUPPORTED"), ("sv57", "SV57_SUPPORTED")]:
        lines.append(f"#ifdef {guard}")
        for level in range(LEVELS_BELOW_ROOT[mode]):
            lines += [".p2align 12", f"rvtest_mprv_slvl{level}_pg_tbl_{mode}: .zero 4096"]
        lines.append(f"#endif // {guard}")
    lines.append(".popsection")
    return lines


def _emit_file(td: TestData, regs: Regs) -> list[str]:
    lines = _data_section()
    lines += [
        comment_banner(
            "Smmpm pointer masking -- M-mode only",
            "mseccfg.PMM is programmed from M-mode; every probe also runs in M-mode.",
        ),
        "",
        "j pm_jalr_pad_end",
        "pm_jalr_pad:",
        f"addi x{regs.chk}, x{regs.chk}, 1",
        "jr ra",
        "pm_jalr_pad_end:",
        "RVTEST_GOTO_MMODE",
        "",
        "# FP and vector state must be enabled for the FP/vector probes to be legal.",
        _li(regs.tmp, (3 << 13) | (3 << 9)),
        f"csrs mstatus, x{regs.tmp}",
    ]

    for pmm, pmlen, label in PMM_CONFIGS:
        prefix = f"{label}_mmode"
        lines.append(comment_banner(f"PMM={pmm:#04b} (PMLEN={pmlen}), M-mode"))
        lines += ["RVTEST_GOTO_MMODE"] + _set_pmm(pmm, pmlen, regs.tmp)
        # FIX: must reset via mstatus explicitly -- set_mxr's default
        # status_csr is "sstatus", which is Ssnpm's convention, not Smmpm's.
        lines += _guard_open("S_SUPPORTED") + set_mxr(False, regs.tmp, "mstatus") + _guard_close("S_SUPPORTED")
        lines += [f"LA(x{regs.base}, pm_lo_page)"]

        lines += pass_a_all_instructions(None, prefix, td, regs, COVERGROUP)
        lines += pass_c_misaligned(None, prefix, td, regs, COVERGROUP)
        lines += pass_e_jalr(None, prefix, td, regs, COVERGROUP)
        lines += pass_f_fault_address(None, prefix, td, regs, COVERGROUP)

        lines += _guard_open("S_SUPPORTED")
        lines += pass_d_mxr(
            None,
            prefix,
            td,
            regs,
            COVERGROUP,
            goto_target_mode="",  # Smmpm never leaves M-mode
            status_csr="mstatus",
        )
        lines += set_mxr(False, regs.tmp, "mstatus")
        lines += _guard_close("S_SUPPORTED")

        lines.append(comment_banner(f"{prefix}: CSR writes must not be pointer-masked"))
        pattern = ((1 << pmlen) - 1) << (64 - pmlen) | 0x1234_5678
        for csr in _CSR_TARGETS:
            lines += [
                f"csrr x{regs.tmp}, {csr}   # save the framework's value before clobbering it",
                _li(regs.chk, pattern),
                td.add_testcase(f"{prefix}_csrsw_{csr}", CP_CSR, COVERGROUP),
                gen_csr_write_sigupd(regs.chk, csr, td),
                f"csrw {csr}, x{regs.tmp}   # restore before any later trap needs this CSR",
            ]

    lines += _pass_h_mprv(td, regs)
    lines += ["RVTEST_GOTO_MMODE", *_set_pmm(0b00, 0, regs.tmp)]
    lines += _guard_open("S_SUPPORTED") + set_mxr(False, regs.tmp, "mstatus") + _guard_close("S_SUPPORTED")
    return lines


@add_priv_test_generator(
    "Smmpm",
    required_extensions=["Smmpm", "Zicsr", "M"],
    march_extensions=["I", "A", "F", "D", "C", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz"],
)
def make_smmpm(td: TestData) -> list[TestChunk]:
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
