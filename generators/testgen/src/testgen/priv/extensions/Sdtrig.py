##################################
# Sdtrig.py
#
# Sdtrig groups H and HSm: triggers in VS-mode and VU-mode, guest breakpoint delegation, the H-only textra selects and
# hcontext.
# David_Harris@hmc.edu 19 October 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Sdtrig group H and HSm test generators.

Group H boots to HS-mode and enters VS-mode and VU-mode from HS-mode, arming triggers through T-SBI as SdtrigS and
SdtrigU do.  Unless a case says otherwise, guest breakpoints are taken into VS-mode (medeleg[3] = hedeleg[3] = 1) with
vsstatus.SIE = 1: with that delegation the Sdtrig re-entrancy rule suppresses VS-mode triggers while vsstatus.SIE is 0,
and never suppresses VU-mode triggers.  The delegation cases also take guest breakpoints into HS-mode.

Group HSm needs M-mode: it boots to M-mode, where medeleg = mideleg = 0, and enters the guest from M-mode.  Its
delegation cases take guest breakpoints into M-mode.  itrigger and etrigger fire before the first instruction of the
handler of the trap they match, so their tests delegate an SSI or a virtual-instruction exception from the guest to
HS-mode, and the breakpoint is taken into M-mode, where no re-entrancy option suppresses it.

The textra cases arm an icount trigger (count = 1) whose breakpoint is taken on a marker instruction, and run under the
translation their select needs: hgatp = Sv39x4/Sv32x4 with a VMID for mhselect = 2/6, and vsatp = Sv39/Sv32 with an
ASID for sselect = 2.  satp, vsatp and hgatp never hold MODE = Bare with a nonzero ASID or VMID, whose effect is
UNSPECIFIED.
"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.random import random_int
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.HCommon import ATP_GATE
from testgen.priv.extensions.InterruptsCommon import guard_symbol
from testgen.priv.extensions.SdtrigCommon import (
    _TEXTRA_ASID_CASES,
    MODE_PRIVBIT,
    SDTRIG_DEFINES,
    SDTRIG_IMPRECISE_XEPC,
    TRIGGERS,
    _add_tc,
    _cause_interrupt,
    _clear_interrupt,
    _close_gates,
    _config_etrigger,
    _config_icount,
    _config_itrigger,
    _config_mcontrol6,
    _csr_access,
    _disable_trigger,
    _fire_guards,
    _fire_supported_trigger,
    _mode_writable,
    _select_trigger,
    _set_itrigger_delegation,
    _set_medeleg,
    _sign_trap_count,
    _svalue,
    _textra_expr,
    _with_trap_counts,
    _xlen_li_expr,
    _xsl_ifdefs,
)
from testgen.priv.extensions.sv.generate import guest_translation_setup, guest_translation_teardown, per_xlen
from testgen.priv.registry import add_priv_test_generator

CG_H = "Sdtrig_H_cg"
CG_HSM = "Sdtrig_HSm_cg"
GUESTS = ("Vs", "Vu")
_GOTO = {"Vs": "RVTEST_TSBI_GOTO_VSMODE", "Vu": "RVTEST_TSBI_GOTO_VUMODE"}
_ALL_PRIV = 0b11111
_BREAKPOINT = 3
_SSI_CODE = 1
_VIRTUAL_INSTRUCTION = 22
# An icount trigger armed with count = 1 counts the instruction after the T-SBI return and is taken before the
# marker. Coverage samples the marker by its encoding when the trigger does not fire. norvc keeps it 32 bits.
_MARKER = [
    ".option push",
    ".option norvc",
    "addi x0, x0, 0x5a # marker: an icount breakpoint is taken here",
    ".option pop",
]
# Every case gets its registers here, as SdtrigCommon does, clear of sp and the trap handler's temporaries
_REG_RANGE = list(range(8, 16))

# mhselect = 1/5 compares {mhvalue, mhselect[2]} with the low bits of mcontext. The contexts are limited to the bits
# that both mcontext (DBG_HCONTEXT_WIDTH) and {mhvalue, mhselect[2]} (MHVALUE_LEN + 1) implement.
_MCTX_MASK = "(((1 << UDB_DBG_HCONTEXT_WIDTH) - 1) & ((2 << UDB_SDTRIG_TEXTRA_MHVALUE_LEN) - 1))"
_MCTX_CONTEXTS = (("even", f"(0x2AAA & {_MCTX_MASK})"), ("odd", f"(0x2AAB & {_MCTX_MASK})"))
# mhselect = 2/6 compares the low VMIDMAX bits of {mhvalue, mhselect[2]} with hgatp.VMID. An even and an odd VMID in
# the bits that both hgatp.VMID and {mhvalue, mhselect[2]} implement.
_VMID_MASK = "(((1 << UDB_VMID_WIDTH) - 1) & ((2 << UDB_SDTRIG_TEXTRA_MHVALUE_LEN) - 1))"
_VMIDS = (("even", f"({_VMID_MASK} - 1)"), ("odd", _VMID_MASK))
_VSATP_ASID = "((1 << UDB_ASID_WIDTH) - 2)"
# The hart matches on the context and implements the bits to compare; VMID and ASID also need a paged hgatp or vsatp
_MCTX_GATE = (
    "#if defined(UDB_SDTRIG_TEXTRA_MHSELECT_MCONTEXT_MATCH) && UDB_SDTRIG_TEXTRA_MHVALUE_LEN > 0 && "
    "UDB_DBG_HCONTEXT_WIDTH > 0"
)
_VMID_GATE = (
    f"#if ({ATP_GATE['hgatp']}) && defined(UDB_SDTRIG_TEXTRA_MHSELECT_VMID_MATCH) && "
    "UDB_SDTRIG_TEXTRA_MHVALUE_LEN > 0 && UDB_VMID_WIDTH >= 2"
)
_ASID_GATE = (
    f"#if ({ATP_GATE['vsatp']}) && defined(UDB_SDTRIG_TEXTRA_SSELECT_ASID_MATCH) && UDB_ASID_WIDTH >= 2 && "
    "UDB_SDTRIG_TEXTRA_SVALUE_LEN >= UDB_ASID_WIDTH"
)


def _mhselect_cases(odd: bool) -> list[tuple[str, int, int]]:
    """(case, mhselect, mhvalue xor) for a context whose bit 0 is odd: the matching select, the other select, and
    the matching select with mhvalue bit 0 flipped."""
    own, other = (5, 1) if odd else (1, 5)
    return [(f"sel{own}_match", own, 0), (f"sel{other}_bit0", other, 0), (f"sel{own}_mhvalue", own, 1)]


def _mhselect_tdata3(reg: int, mhselect: int, context: str, flip: int) -> list[str]:
    """tdata3 with mhselect and mhvalue = (context >> 1) ^ flip, so {mhvalue, mhselect[2]} = context exactly when
    mhselect[2] = context[0] and flip = 0."""
    mhvalue = f"((({context}) >> 1) ^ {flip})"
    return _xlen_li_expr(
        reg, _textra_expr(32, mhselect=mhselect, mhvalue=mhvalue), _textra_expr(64, mhselect=mhselect, mhvalue=mhvalue)
    )


def _enter_guest(mode: str, reg: int, hedeleg: int = 1) -> list[str]:
    """From HS-mode or M-mode, set hedeleg[3] (1: guest breakpoints are taken into VS-mode) and vsstatus.SIE = 1, so
    VS-mode triggers are not suppressed, and enter ``mode``."""
    return [
        f"LI(x{reg}, 0x{1 << _BREAKPOINT:x})",
        f"{'csrs' if hedeleg else 'csrc'} hedeleg, x{reg} # hedeleg[3]={hedeleg}",
        "csrsi vsstatus, 0x2 # vsstatus.SIE=1",
        _GOTO[mode],
    ]


def _leave_guest(reg: int, base: str = "S") -> list[str]:
    """Return to ``base`` mode (HS-mode or M-mode) and restore hedeleg[3] = 0 and vsstatus.SIE = 0."""
    return [
        f"RVTEST_TSBI_GOTO_{base}MODE",
        "csrci vsstatus, 0x2",
        f"LI(x{reg}, 0x{1 << _BREAKPOINT:x})",
        f"csrc hedeleg, x{reg}",
    ]


def _own_and_others(mode: str) -> tuple[tuple[str, int], tuple[str, int]]:
    """(case, privbits): only the guest mode's vs/vu bit, then every other mode bit (m, s, u and the other guest's)."""
    own = MODE_PRIVBIT[mode]
    return ("own", own), ("others", _ALL_PRIV ^ own)


### Generators


def _mcontrol6_mode_tests(test_data: TestData) -> list[TestChunk]:
    """cp_mcontrol6_vs/vu: an mcontrol6 store trigger in VS-mode and VU-mode with only its vs/vu bit set, then with
    every other mode bit set."""
    chunks: list[TestChunk] = []
    cfg_reg, addr_reg, data_reg, temp_reg = test_data.int_regs.get_registers(4, reg_range=_REG_RANGE)
    lines = test_data.new_test_chunk(chunks, "H_mcontrol6").code
    for mode in GUESTS:
        m = mode.lower()
        own, others = _own_and_others(mode)
        lines.extend(
            [
                comment_banner(
                    f"cp_mcontrol6_{m}",
                    f"mcontrol6 store address trigger on scratch in {mode.upper()}-mode with tdata1.{m} = 1 and the\n"
                    f"other mode bits 0, then with tdata1.{m} = 0 and the other mode bits 1. The breakpoint is taken\n"
                    "into VS-mode only in the first case",
                ),
                *_enter_guest(mode, temp_reg),
            ]
        )
        for trig_num in TRIGGERS:
            gates = [f"\n#ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_{trig_num}", *_xsl_ifdefs(0b010)]
            lines.extend([*gates, *_select_trigger(cfg_reg, trig_num, mode)])
            for name, priv in (own, others):
                case = [
                    _add_tc(test_data, f"trig_num_{trig_num}_{name}", f"cp_mcontrol6_{m}", CG_H),
                    *_config_mcontrol6(cfg_reg, trig_num, "scratch", mode, privbits=priv, xsl=0b010),
                    f"LA(x{addr_reg}, scratch)",
                    f"LI(x{data_reg}, 0x{random_int(32, signed=False):x})",
                    f"sw x{data_reg}, 0(x{addr_reg}) # breakpoint iff tdata1.{m} = 1",
                    "nop # spacer (an address match may fire after the store)",
                    *_disable_trigger(mode),
                    *_sign_trap_count(temp_reg, test_data),
                ]
                if name == "own":
                    case = [f"#ifdef {_mode_writable(mode)}", *case, f"#endif // {_mode_writable(mode)}"]
                lines.extend(case)
            lines.extend(_close_gates([g.strip() for g in gates]))
        lines.extend(_leave_guest(temp_reg))
    test_data.int_regs.return_registers([cfg_reg, addr_reg, data_reg, temp_reg])
    chunks.append(test_data.end_test_chunk())
    return chunks


def _icount_mode_tests(test_data: TestData) -> list[TestChunk]:
    """cp_icount_vs/vu: an icount trigger (count = 1) in VS-mode and VU-mode with only its vs/vu bit set, then with
    every other mode bit set."""
    chunks: list[TestChunk] = []
    cfg_reg, temp_reg = test_data.int_regs.get_registers(2, reg_range=_REG_RANGE)
    lines = test_data.new_test_chunk(chunks, "H_icount").code
    for mode in GUESTS:
        m = mode.lower()
        own, others = _own_and_others(mode)
        lines.extend(
            [
                comment_banner(
                    f"cp_icount_{m}",
                    f"icount trigger (count = 1) in {mode.upper()}-mode with tdata1.{m} = 1 and the other mode bits 0,\n"
                    f"then with tdata1.{m} = 0 and the other mode bits 1. The breakpoint is taken into VS-mode on the\n"
                    "marker only in the first case",
                ),
                *_enter_guest(mode, temp_reg),
            ]
        )
        for trig_num in TRIGGERS:
            lines.extend(
                [
                    f"\n#ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_{trig_num}",
                    *_select_trigger(cfg_reg, trig_num, mode),
                ]
            )
            for name, priv in (own, others):
                case = [
                    _add_tc(test_data, f"trig_num_{trig_num}_{name}", f"cp_icount_{m}", CG_H),
                    *_config_icount(cfg_reg, trig_num, 1, mode, privbits=priv),
                    f"nop # counted when tdata1.{m} = 1",
                    *_MARKER,
                    *_disable_trigger(mode),
                    *_sign_trap_count(temp_reg, test_data),
                ]
                if name == "own":
                    case = [f"#ifdef {_mode_writable(mode)}", *case, f"#endif // {_mode_writable(mode)}"]
                lines.extend(case)
            lines.append(f"#endif // UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_{trig_num}")
        lines.extend(_leave_guest(temp_reg))
    test_data.int_regs.return_registers([cfg_reg, temp_reg])
    chunks.append(test_data.end_test_chunk())
    return chunks


def _delegate_tests(test_data: TestData, group: str) -> list[TestChunk]:
    """cp_breakpoint_delegate_vs/vu: mcontrol6 and icount breakpoints from VS-mode and VU-mode. Group H takes them
    into HS-mode (hedeleg[3] = 0) and VS-mode (hedeleg[3] = 1) with medeleg[3] = 1 as booted; group HSm boots to
    M-mode with medeleg = 0 and takes them into M-mode."""
    chunks: list[TestChunk] = []
    cfg_reg, addr_reg, data_reg, temp_reg = test_data.int_regs.get_registers(4, reg_range=_REG_RANGE)
    lines = test_data.new_test_chunk(chunks, f"{group}_delegate").code
    if group == "H":
        covergroup, base, routes = CG_H, "S", ((0, "HS"), (1, "VS"))
        note = (
            "into HS-mode with hedeleg[3] = 0 and into VS-mode with hedeleg[3] = 1 (into M-mode on a hart that\n"
            "hard-wires medeleg[3] to 0). In HS-mode"
        )
    else:
        covergroup, base, routes = CG_HSM, "M", ((0, "M"),)
        note = "into M-mode with medeleg[3] = 0. In M-mode"
    for mode in GUESTS:
        m = mode.lower()
        lines.append(
            comment_banner(
                f"cp_breakpoint_delegate_{m}",
                f"mcontrol6 (store address) and icount (count = 1) breakpoints from {mode.upper()}-mode, taken\n"
                f"{note} the trap sets GVA for the mcontrol6 breakpoint, whose tval is the guest\n"
                "virtual address, and clears it for icount, which writes tval = 0",
            )
        )
        for hedeleg, target in routes:
            lines.extend(
                [f"\n# breakpoints from {mode.upper()}-mode into {target}-mode", *_enter_guest(mode, temp_reg, hedeleg)]
            )
            for trig_num in TRIGGERS:
                for trig_type in ("mcontrol6", "icount"):
                    guards = _fire_guards(trig_type, trig_num, mode)
                    lines.extend(
                        [
                            *guards,
                            *_select_trigger(cfg_reg, trig_num, mode),
                            _add_tc(
                                test_data,
                                f"trig_num_{trig_num}_{trig_type}_{target.lower()}",
                                f"cp_breakpoint_delegate_{m}",
                                covergroup,
                            ),
                            *_fire_supported_trigger(trig_type, trig_num, mode, cfg_reg, addr_reg, data_reg),
                            *_sign_trap_count(data_reg, test_data),
                            *_close_gates(guards),
                        ]
                    )
            lines.extend(_leave_guest(temp_reg, base))
    test_data.int_regs.return_registers([cfg_reg, addr_reg, data_reg, temp_reg])
    chunks.append(test_data.end_test_chunk())
    return chunks


def _trap_trigger_tests(test_data: TestData) -> list[TestChunk]:
    """cp_itrigger_vs/vu and cp_etrigger_vs/vu: itrigger on SSI and etrigger on virtual instruction, armed in M-mode,
    with the trap taken from VS-mode or VU-mode into HS-mode. Group HSm boots to M-mode with medeleg = mideleg = 0, so
    the breakpoint is taken into M-mode; mideleg[1] and medeleg[22] are set for these tests to take the SSI and the
    virtual-instruction exception into HS-mode."""
    chunks: list[TestChunk] = []
    cfg_reg, data_reg, temp_reg = test_data.int_regs.get_registers(3, reg_range=_REG_RANGE)
    lines = test_data.new_test_chunk(chunks, "HSm_trap_triggers").code
    ssi_guard = guard_symbol("SSI")
    lines.extend(
        [
            comment_banner(
                "cp_itrigger_vs, cp_itrigger_vu, cp_etrigger_vs, cp_etrigger_vu",
                "itrigger selecting SSI and etrigger selecting virtual instruction, armed in M-mode with medeleg[3] = 0,\n"
                "with only the guest mode's vs/vu bit set and then with every other mode bit set. The SSI is taken\n"
                "from the guest into HS-mode as the T-SBI call enters it, and the virtual instruction is a read of\n"
                "hstatus in the guest. The trigger fires into M-mode before the first HS handler instruction only\n"
                "in the first case",
            ),
        ]
    )
    for mode in GUESTS:
        m = mode.lower()
        cases = _own_and_others(mode)
        for trig_num in TRIGGERS:
            lines.extend(
                [
                    f"\n#ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_{trig_num}",
                    f"#ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_INTERRUPTS_{_SSI_CODE}",
                    f"#ifdef {ssi_guard}",
                    f"#ifdef UDB_MIDELEG_DELEGATABLE_{_SSI_CODE}",
                    *_set_itrigger_delegation(_SSI_CODE, 1, temp_reg),
                    *_select_trigger(cfg_reg, trig_num, "Sm"),
                ]
            )
            for name, priv in cases:
                case = [
                    _add_tc(test_data, f"trig_num_{trig_num}_{name}", f"cp_itrigger_{m}", CG_HSM),
                    *_config_itrigger(cfg_reg, trig_num, 1 << _SSI_CODE, "Sm", privbits=priv),
                    *_cause_interrupt(_SSI_CODE, "Sm", temp_reg),
                    f"{_GOTO[mode]} # the SSI is taken from {mode.upper()}-mode into HS-mode",
                    "nop # spacer",
                    "RVTEST_TSBI_GOTO_MMODE",
                    *_clear_interrupt(_SSI_CODE, "Sm"),
                    f"LI(x{temp_reg}, 0x{1 << _SSI_CODE:x})",
                    f"csrc mie, x{temp_reg} # SSIE=0",
                    *_disable_trigger("Sm"),
                    *_sign_trap_count(temp_reg, test_data),
                ]
                if name == "own":
                    case = [f"#ifdef {_mode_writable(mode)}", *case, f"#endif // {_mode_writable(mode)}"]
                lines.extend(case)
            lines.extend(
                [
                    *_set_itrigger_delegation(_SSI_CODE, 0, temp_reg),
                    f"#endif // UDB_MIDELEG_DELEGATABLE_{_SSI_CODE}",
                    f"#endif // {ssi_guard}",
                    f"#endif // UDB_SDTRIG_ITRIGGER_SUPPORTED_INTERRUPTS_{_SSI_CODE}",
                    f"#endif // UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_{trig_num}",
                ]
            )
        for trig_num in TRIGGERS:
            lines.extend(
                [
                    f"\n#ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_{trig_num}",
                    f"#ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_{_VIRTUAL_INSTRUCTION}",
                    f"#ifdef UDB_MEDELEG_DELEGATABLE_{_VIRTUAL_INSTRUCTION}",
                    *_set_medeleg(temp_reg, _VIRTUAL_INSTRUCTION, True),
                    *_select_trigger(cfg_reg, trig_num, "Sm"),
                ]
            )
            for name, priv in cases:
                case = [
                    _add_tc(test_data, f"trig_num_{trig_num}_{name}", f"cp_etrigger_{m}", CG_HSM),
                    *_config_etrigger(cfg_reg, trig_num, 1 << _VIRTUAL_INSTRUCTION, "Sm", privbits=priv),
                    _GOTO[mode],
                    f"csrr x{data_reg}, hstatus # virtual instruction from {mode.upper()}-mode, taken into HS-mode",
                    "RVTEST_TSBI_GOTO_MMODE",
                    *_disable_trigger("Sm"),
                    *_sign_trap_count(temp_reg, test_data),
                ]
                if name == "own":
                    case = [f"#ifdef {_mode_writable(mode)}", *case, f"#endif // {_mode_writable(mode)}"]
                lines.extend(case)
            lines.extend(
                [
                    *_set_medeleg(temp_reg, _VIRTUAL_INSTRUCTION, False),
                    f"#endif // UDB_MEDELEG_DELEGATABLE_{_VIRTUAL_INSTRUCTION}",
                    f"#endif // UDB_SDTRIG_ETRIGGER_SUPPORTED_EXCEPTIONS_{_VIRTUAL_INSTRUCTION}",
                    f"#endif // UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_{trig_num}",
                ]
            )
    test_data.int_regs.return_registers([cfg_reg, data_reg, temp_reg])
    chunks.append(test_data.end_test_chunk())
    return chunks


def _icount_textra_cases(
    test_data: TestData, mode: str, binname: str, coverpoint: str, tdata3: list[str], regs: tuple[int, int], sign: bool
) -> list[str]:
    """Arm an icount trigger (count = 1) for ``mode`` with tdata3 on each trigger, run to the marker, and disarm it."""
    cfg_reg, temp_reg = regs
    lines: list[str] = []
    for trig_num in TRIGGERS:
        lines.extend(
            [
                f"#ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_{trig_num}",
                *_select_trigger(cfg_reg, trig_num, mode),
                _add_tc(test_data, f"trig_num_{trig_num}_{binname}", coverpoint, CG_H),
                *_config_icount(cfg_reg, trig_num, 1, mode, tdata3=tdata3),
                "nop # counted",
                *_MARKER,
                *_disable_trigger(mode),
                *(_sign_trap_count(temp_reg, test_data) if sign else []),
                f"#endif // UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_{trig_num}",
            ]
        )
    return lines


def _textra_tests(test_data: TestData) -> list[TestChunk]:
    """cp_textra_mctx_sel, cp_textra_vmid_sel and cp_textra_vsatp_asid in VS-mode and VU-mode."""
    chunks: list[TestChunk] = []
    cfg_reg, temp_reg, ctx_reg = test_data.int_regs.get_registers(3, reg_range=_REG_RANGE)
    regs = (cfg_reg, temp_reg)

    ######################################
    coverpoint = "cp_textra_mctx_sel"
    ######################################
    lines = test_data.new_test_chunk(chunks, "H_textra_mctx").code
    lines.extend(
        [
            comment_banner(
                coverpoint,
                "textra mhselect = 1 and 5: icount fires in VS-mode and VU-mode only when {mhvalue, mhselect[2]}\n"
                "equals the low bits of mcontext, for an even and an odd mcontext",
            ),
            _MCTX_GATE,
        ]
    )
    for mode in GUESTS:
        lines.extend([f"#ifdef {_mode_writable(mode)}", *_enter_guest(mode, temp_reg)])
        for ctx_name, ctx in _MCTX_CONTEXTS:
            lines.extend(
                [f"LI(x{ctx_reg}, {ctx})", _csr_access(f"csrw mcontext, x{ctx_reg} # {ctx_name} mcontext", mode)]
            )
            for case, mhselect, flip in _mhselect_cases(ctx_name == "odd"):
                lines.extend(
                    _icount_textra_cases(
                        test_data,
                        mode,
                        f"{mode.lower()}_{ctx_name}_{case}",
                        coverpoint,
                        _mhselect_tdata3(cfg_reg, mhselect, ctx, flip),
                        regs,
                        sign=True,
                    )
                )
        lines.extend(
            [
                _csr_access("csrw mcontext, x0 # clear the test context", mode),
                *_leave_guest(temp_reg),
                f"#endif // {_mode_writable(mode)}",
            ]
        )
    lines.append("#endif // mcontext textra match")

    ######################################
    coverpoint = "cp_textra_vmid_sel"
    ######################################
    lines = test_data.new_test_chunk(chunks, "H_textra_vmid").code
    lines.extend(
        [
            comment_banner(
                coverpoint,
                "textra mhselect = 2 and 6: icount fires in VS-mode and VU-mode only when {mhvalue, mhselect[2]}\n"
                "equals hgatp.VMID, for an even and an odd VMID. hgatp identity maps the test image",
            ),
            _VMID_GATE,
            *per_xlen(lambda g, _: guest_translation_setup(test_data, g, None, "VSmode")),
        ]
    )
    for vmid_name, vmid in _VMIDS:
        lines.extend(
            [
                *_xlen_li_expr(ctx_reg, "(0x7F << 22)", "(0x3FFF << 44)"),
                f"csrc hgatp, x{ctx_reg}",
                *_xlen_li_expr(ctx_reg, f"({vmid} << 22)", f"({vmid} << 44)"),
                f"csrs hgatp, x{ctx_reg} # hgatp.VMID = {vmid_name} VMID",
                "hfence.gvma",
            ]
        )
        for mode in GUESTS:
            lines.extend([f"#ifdef {_mode_writable(mode)}", *_enter_guest(mode, temp_reg)])
            for case, mhselect, flip in _mhselect_cases(vmid_name == "odd"):
                lines.extend(
                    _icount_textra_cases(
                        test_data,
                        mode,
                        f"{mode.lower()}_{vmid_name}_{case.replace('sel1', 'sel2').replace('sel5', 'sel6')}",
                        coverpoint,
                        _mhselect_tdata3(cfg_reg, mhselect + 1, vmid, flip),
                        regs,
                        sign=True,
                    )
                )
            lines.extend([*_leave_guest(temp_reg), f"#endif // {_mode_writable(mode)}"])
    lines.extend([*guest_translation_teardown(test_data), "#endif // hgatp Sv39x4/Sv32x4, VMID"])

    ######################################
    coverpoint = "cp_textra_vsatp_asid"
    ######################################
    lines = test_data.new_test_chunk(chunks, "H_textra_asid").code
    lines.extend(
        [
            comment_banner(
                coverpoint,
                "textra sselect = 2: icount fires in VS-mode and VU-mode only when the low ASIDMAX bits of svalue\n"
                "equal vsatp.ASID = X (satp.ASID = 0). vsatp identity maps the test image. VU-mode cannot write the\n"
                "signature through that supervisor map, so its trap count is signed in HS-mode",
            ),
            _ASID_GATE,
        ]
    )
    for mode in GUESTS:
        priv_mode = f"{mode.upper()}mode"
        lines.extend(
            [
                f"#ifdef {_mode_writable(mode)}",
                *per_xlen(lambda _, vs, priv=priv_mode: guest_translation_setup(test_data, None, vs, priv)),
                *_xlen_li_expr(ctx_reg, f"({_VSATP_ASID} << 22)", f"({_VSATP_ASID} << 44)"),
                f"csrs vsatp, x{ctx_reg} # vsatp.ASID = X",
                "hfence.vvma",
                *_enter_guest(mode, temp_reg),
            ]
        )
        for case_name, sv, masked in _TEXTRA_ASID_CASES:
            sv64 = sv.replace("ASIDMAX", "16").replace("X", _VSATP_ASID)
            sv32 = sv.replace("ASIDMAX", "9").replace("X", _VSATP_ASID)
            tdata3 = _xlen_li_expr(
                cfg_reg,
                _textra_expr(32, sselect=2, svalue=_svalue(sv32), sbytemask=0x3 if masked else 0),
                _textra_expr(64, sselect=2, svalue=_svalue(sv64), sbytemask=0xF if masked else 0),
            )
            lines.extend(
                _icount_textra_cases(
                    test_data, mode, f"{mode.lower()}_svalue_{case_name}", coverpoint, tdata3, regs, sign=mode == "Vs"
                )
            )
        lines.extend(_leave_guest(temp_reg))
        if mode == "Vu":
            # its own label: the last case's label is inside the guard of the highest trigger
            lines.extend(
                [_add_tc(test_data, "vu_trap_count", coverpoint, CG_H), *_sign_trap_count(temp_reg, test_data)]
            )
        lines.extend([*guest_translation_teardown(test_data), f"#endif // {_mode_writable(mode)}"])
    lines.append("#endif // vsatp Sv39/Sv32, ASID")

    test_data.int_regs.return_registers([cfg_reg, temp_reg, ctx_reg])
    chunks.append(test_data.end_test_chunk())
    return chunks


def _hcontext_tests(test_data: TestData, group: str) -> list[TestChunk]:
    """cp_hcontext_hs (group H) and cp_hcontext_m (group HSm): hcontext is an alias of mcontext. Reads are checked in
    the low UDB_DBG_HCONTEXT_WIDTH bits, because an implementation may tie the upper bits to 0."""
    chunks: list[TestChunk] = []
    rs, rd, mask = test_data.int_regs.get_registers(3, reg_range=_REG_RANGE)
    lines = test_data.new_test_chunk(chunks, f"{group}_hcontext").code

    def check() -> list[str]:
        return [f"and x{rd}, x{rd}, x{mask} # implemented hcontext bits", write_sigupd(rd, test_data)]

    lines.extend(
        [
            "#if defined(UDB_HCONTEXT_IMPLEMENTED) && UDB_DBG_HCONTEXT_WIDTH > 0",
            f"LI(x{mask}, ((1 << UDB_DBG_HCONTEXT_WIDTH) - 1))",
        ]
    )
    if group == "H":
        lines.insert(
            0,
            comment_banner(
                "cp_hcontext_hs",
                "Write hcontext in HS-mode and read hcontext and mcontext (T-SBI); write mcontext (T-SBI) and read hcontext",
            ),
        )
        for name, value in (("ones", "-1"), ("random", f"0x{random_int(14, signed=False):x}")):
            lines.extend(
                [
                    f"LI(x{rs}, {value})",
                    _add_tc(test_data, f"csrw_{name}", "cp_hcontext_hs", CG_H),
                    f"csrw hcontext, x{rs}",
                    f"csrr x{rd}, hcontext",
                    *check(),
                    _csr_access(f"csrr x{rd}, mcontext # the hcontext field of mcontext", "S"),
                    *check(),
                ]
            )
        lines.extend(
            [
                f"LI(x{rs}, 0x{random_int(14, signed=False):x})",
                _csr_access(f"csrw mcontext, x{rs}", "S"),
                _add_tc(test_data, "csrr_after_mcontext_write", "cp_hcontext_hs", CG_H),
                f"csrr x{rd}, hcontext",
                *check(),
                _csr_access("csrw mcontext, x0 # clear the test context", "S"),
            ]
        )
    else:
        lines.insert(
            0, comment_banner("cp_hcontext_m", "Write hcontext in M-mode and read mcontext, then read hcontext")
        )
        lines.extend(
            [
                f"LI(x{rs}, 0x{random_int(14, signed=False):x})",
                _add_tc(test_data, "csrw", "cp_hcontext_m", CG_HSM),
                f"csrw hcontext, x{rs}",
                f"csrr x{rd}, mcontext",
                *check(),
                _add_tc(test_data, "csrr", "cp_hcontext_m", CG_HSM),
                f"csrr x{rd}, hcontext",
                *check(),
                "csrw mcontext, x0 # clear the test context",
            ]
        )
    lines.append("#endif // UDB_HCONTEXT_IMPLEMENTED")
    test_data.int_regs.return_registers([rs, rd, mask])
    chunks.append(test_data.end_test_chunk())
    return chunks


# ── Registration ───────────────────────────────────────────────────────────
# Each section is its own generator, as in SdtrigCommon. The sections that fire mcontrol6 triggers skip xEPC on
# breakpoints (SDTRIG_IMPRECISE_XEPC), because where an address match fires is the implementation's choice.

_H_REQUIRED: list[str | list[str]] = ["S", "H", "Sdtrig"]
_H_DEFINES = [*SDTRIG_DEFINES, "#define BOOT_TO_SMODE"]
# Sm tests are not part of a certificate without Sm (EXCLUDE_SM)
_HSM_REQUIRED: list[str | list[str]] = ["Sm", "H", "Sdtrig"]
_HSM_DEFINES = [*SDTRIG_DEFINES, "#define BOOT_TO_MMODE"]
_MARCH = ["H"]


@add_priv_test_generator(
    "Sdtrig",
    required_extensions=_H_REQUIRED,
    march_extensions=_MARCH,
    extra_defines=[*_H_DEFINES, SDTRIG_IMPRECISE_XEPC],
)
def make_sdtrig_h_mcontrol6(test_data: TestData) -> list[TestChunk]:
    """mcontrol6 triggers in VS-mode and VU-mode."""
    return _with_trap_counts(_mcontrol6_mode_tests(test_data))


@add_priv_test_generator("Sdtrig", required_extensions=_H_REQUIRED, march_extensions=_MARCH, extra_defines=_H_DEFINES)
def make_sdtrig_h_icount(test_data: TestData) -> list[TestChunk]:
    """icount triggers in VS-mode and VU-mode."""
    return _with_trap_counts(_icount_mode_tests(test_data))


@add_priv_test_generator(
    "Sdtrig",
    required_extensions=_H_REQUIRED,
    march_extensions=_MARCH,
    extra_defines=[*_H_DEFINES, SDTRIG_IMPRECISE_XEPC],
)
def make_sdtrig_h_delegate(test_data: TestData) -> list[TestChunk]:
    """Guest breakpoints taken into HS-mode and VS-mode."""
    return _with_trap_counts(_delegate_tests(test_data, "H"))


@add_priv_test_generator("Sdtrig", required_extensions=_H_REQUIRED, march_extensions=_MARCH, extra_defines=_H_DEFINES)
def make_sdtrig_h_textra(test_data: TestData) -> list[TestChunk]:
    """textra mcontext, VMID and vsatp ASID selects in VS-mode and VU-mode."""
    return _with_trap_counts(_textra_tests(test_data))


@add_priv_test_generator("Sdtrig", required_extensions=_H_REQUIRED, march_extensions=_MARCH, extra_defines=_H_DEFINES)
def make_sdtrig_h_hcontext(test_data: TestData) -> list[TestChunk]:
    """hcontext as an alias of mcontext, from HS-mode."""
    return _with_trap_counts(_hcontext_tests(test_data, "H"))


@add_priv_test_generator(
    "Sdtrig",
    required_extensions=_HSM_REQUIRED,
    march_extensions=_MARCH,
    extra_defines=[*_HSM_DEFINES, SDTRIG_IMPRECISE_XEPC],
)
def make_sdtrig_hsm_delegate(test_data: TestData) -> list[TestChunk]:
    """Guest breakpoints taken into M-mode."""
    return _with_trap_counts(_delegate_tests(test_data, "HSm"))


@add_priv_test_generator(
    "Sdtrig", required_extensions=_HSM_REQUIRED, march_extensions=_MARCH, extra_defines=_HSM_DEFINES
)
def make_sdtrig_hsm_trap_triggers(test_data: TestData) -> list[TestChunk]:
    """itrigger and etrigger on traps taken from VS-mode and VU-mode."""
    return _with_trap_counts(_trap_trigger_tests(test_data))


@add_priv_test_generator(
    "Sdtrig", required_extensions=_HSM_REQUIRED, march_extensions=_MARCH, extra_defines=_HSM_DEFINES
)
def make_sdtrig_hsm_hcontext(test_data: TestData) -> list[TestChunk]:
    """hcontext as an alias of mcontext, from M-mode."""
    return _with_trap_counts(_hcontext_tests(test_data, "HSm"))
