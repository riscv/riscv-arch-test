#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate tests_ai/Smrnmi: one test per normative rule about Smrnmi (src/priv/smrnmi.adoc).

Every test boots to M-mode (helpers in smrnmilib.py). No ACT configuration can raise an RNMI, and software cannot
clear mnstatus.NMIE, which the framework boot sets. The tests cover what is observable with NMIE = 1: the four CSRs,
their access and WARL rules, the set-only NMIE bit, and MNRET (privilege, return PC, MNPP/MNPV/MNPELP, MPRV, NMIE).
"""

from __future__ import annotations

import os
import sys
from contextlib import ExitStack
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent))
from aigen import TestFile, X
from hlib import FORMS, form_value, window_tsbi
from smrnmilib import (
    BREAKPOINT,
    CSR,
    CSRN,
    HSTATUS_VTSR,
    ILLEGAL,
    ISSUE,
    LPE,
    MLPE,
    MNPELP,
    MNPP_SH,
    MNPV,
    MNRET,
    MODES,
    MSTATUS_MIE,
    MSTATUS_MPIE,
    MSTATUS_MPRV,
    MSTATUS_TSR,
    NMIE,
    REQ,
    SRC,
    SWCHECK,
    H,
    enc_csr,
    misa_c,
    mnret_land,
    mnstatus_val,
    mode_cond,
    mpelp_from_log,
    new,
    read_mnstatus,
    set_mpp,
    set_mpv,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

SUITE = "Smrnmi"
MUT = os.environ.get("AI_MUTANT", "")  # mutate.py: model a plausible bug in the expectations

MUTANTS = {
    "csr_lower_access": "mnscratch is readable from S-mode",
    "mnret_s_legal": "MNRET executes in S-mode (treated like SRET)",
    "mnret_vs_virtual": "MNRET in VS-mode raises virtual-instruction instead of illegal-instruction",
    "mnret_nop": "MNRET falls through to the next instruction",
    "mnret_uses_mepc": "MNRET returns to mepc",
    "mnret_uses_mpp": "MNRET returns to the mode in mstatus.MPP",
    "mnret_mret_side_effects": "MNRET to M-mode updates mstatus like MRET (MIE = MPIE, MPP = U)",
    "mnret_mnpp_to_u": "MNRET sets MNPP to U (like MRET does MPP)",
    "mnret_clears_mprv_to_m": "MNRET to M-mode clears mstatus.MPRV",
    "mnret_keeps_mprv": "MNRET to U-mode leaves mstatus.MPRV set",
    "nmie_clearable": "csrc mnstatus, NMIE clears NMIE",
    "nmie_write_ignored": "a write to mnstatus that tries to clear NMIE is ignored entirely",
    "mnpp_holds_2": "MNPP holds the reserved value 2",
    "mnpv_ignored": "MNRET with MNPV = 1 and MNPP = S returns to HS-mode",
    "mnpv_m": "MNRET with MNPP = M and MNPV = 1 returns to VS-mode",
    "mnpelp_ro0": "mnstatus.MNPELP is read-only zero",
    "elp_ignores_lpe": "MNRET sets ELP = MNPELP regardless of the target mode's LPE",
    "elp_u_menvcfg": "MNRET to U-mode takes ULPE from menvcfg.LPE when S-mode exists",
    "elp_never": "MNRET never sets ELP",
    "elp_vu_henvcfg": "MNRET to VU-mode takes VULPE from henvcfg.LPE",
    "mnscratch_32bit": "mnscratch holds only 32 bits (RV64)",
    "mnscratch_csrrc_as_csrrs": "csrrc on mnscratch sets the bits",
    "mnepc_bit0_kept": "mnepc[0] is writable",
    "mnepc_bit1_unmasked": "mnepc[1] reads 1 while IALIGN = 32",
    "mnepc_bit1_lost": "mnepc[1] written while IALIGN = 32 is lost",
    "mnepc_32bit": "mnepc holds only 32 bits (RV64 canonical high addresses lost)",
    "mnepc_invalid_to_valid": "an invalid address written to mnepc becomes a valid one",
}


def mut(name: str) -> bool:
    assert name in MUTANTS, name
    return name == MUT


def tf(rule: str, required: list[str] | None = None, rv64: bool = False) -> TestFile:
    return new(SUITE, rule, required, rv64)


def iter_modes(t: TestFile, modes: tuple[str, ...]) -> Iterator[str]:
    """Yield each mode inside its preprocessor guard (S, U, H)."""
    for m in modes:
        c = mode_cond(m)
        if c:
            with t.only_if(c):
                yield m
        else:
            yield m


def lower_window(t: TestFile, mode: str, lines: list[str], expect: object, desc: str, tval: object = None) -> str:
    """Trap window in a mode below M: S/U entered with mret, VS/VU with a T-SBI GOTO."""
    if mode in ("VS", "VU"):
        return window_tsbi(t, mode, lines, expect, desc, tval)  # type: ignore[arg-type]
    return t.window(mode, lines, expect, desc, tval)  # type: ignore[arg-type]


def here(t: TestFile) -> str:
    """A label at the current point, for checks that follow no single instruction under test."""
    lab = t.label("chk")
    t.emit(f"{lab}:", 0)
    return lab


def csrn(name: str) -> str:
    return f"{hex(CSR[name])}"


# ---------------------------------------------------------------- Smrnmi_csrs
def t_csrs() -> TestFile:
    t = tf("Smrnmi_csrs")
    t.describe(
        rule_text="The extension adds four new CSRs (`mnepc`, `mncause`, `mnstatus`, and `mnscratch`) to hold the "
        "interrupted state",
        source=SRC,
        context="The four CSRs are at 0x740 (mnscratch), 0x741 (mnepc), 0x742 (mncause) and 0x744 (mnstatus): "
        "read-write M-level addresses (bits 11:10 = 01, 9:8 = 11), so lower modes cannot access them. mncause "
        "holds the reason for an RNMI; its value after reset and after a software write is not constrained, so "
        "only its accessibility is checked. mnstatus writes keep NMIE = 1 (attempts to clear it are tested in "
        "mnstatus_nmie_set_clear).",
        plan="1. In M-mode, every CSR instruction form (csrrs/csrrsi with x0/0 = read; csrrw rd=x0; csrrw; csrrs, "
        "csrrc with rs1!=x0; csrrwi; csrrci) on each of the four CSRs completes without a trap.\n"
        "2. From S-mode and U-mode (and VS-mode and VU-mode with H), a read (csrrs rs1=x0) and a write "
        "(csrrw rd=x0) of each CSR raise illegal-instruction, with xtval = 0 or the instruction bits, from that "
        "mode.",
    )
    for name, num in CSR.items():
        t.comment(f"M-mode accesses to {name}")
        for asm, f3, rd, rs1, kind, _ in FORMS:
            imm = rs1
            if name == "mnstatus":
                # keep NMIE set: write NMIE | MNPP=M, set NMIE, clear nothing, write immediate NMIE, clear reserved bits
                xval = {1: NMIE | (3 << MNPP_SH), 2: NMIE, 3: 0}.get(f3, 0)
                if f3 == 5:
                    imm = NMIE
            elif name == "mnepc":
                xval = None  # a code address
            else:
                xval = t.rand(31) & ~3
            if f3 in (1, 2, 3) and rs1 == 6:
                if xval is None:
                    t.la("x6", "rvtest_code_begin")
                else:
                    t.li("x6", xval)
            line = asm.format(c=hex(num))
            if f3 in (5, 7) and imm != rs1:
                line = line.replace(f"{rs1:#x}", f"{imm:#x}")
            t.window("M", [f"{line}  // {name}"], "ok", f"{kind} of {name}")
    lower = ("S", "U", "VS", "VU")
    for mode in iter_modes(t, lower):
        for name, num in CSR.items():
            for asm, f3, rd, rs1, kind, _ in (FORMS[0], FORMS[1]):
                if rs1 == 6:
                    t.li("x6", NMIE if name == "mnstatus" else 0)
                e = enc_csr(num, f3, rd, rs1)
                exp = "ok" if (mut("csr_lower_access") and name == "mnscratch" and mode == "S" and f3 == 2) else ILLEGAL
                lower_window(t, mode, [f"{asm.format(c=hex(num))}  // {name}"], exp, f"{kind} of {name}", [0, e])
    return t


# ---------------------------------------------------------------- MNRET
def t_mnret_exist() -> TestFile:
    t = tf("mnret_exist")
    t.describe(
        rule_text="one new instruction, MNRET, to resume from the RNMI handler.",
        source=SRC,
        context="MNRET (0x70200073) returns to mnepc in the mode given by mnstatus.MNPP. It is legal with NMIE = 1 "
        f"(only reached by software here). MRET in an RNMI handler is also legal ({ISSUE}2240).",
        plan="1. In M-mode, MNRET with mnepc = L and MNPP = M does not trap and resumes at L: `auipc x7, 0` at L "
        "reads L. mepc points at a decoy W after the MNRET, so a fall-through (MNRET as a no-op) or a return "
        "through mepc lands at W instead.\n"
        "2. The same from a backward-placed target is not needed: the return address comes from mnepc only.",
    )
    if mut("mnret_nop"):
        # expect the fall-through: x7 = W = L - 8
        lab = t.label("L")
        t.allow(1)
        t.la("x14", lab)
        t.emit(f"csrw {csrn('mnepc')}, x14")
        t.li("x14", mnstatus_val("M"))
        t.emit(f"csrw {csrn('mnstatus')}, x14")
        t.emit(f".word {hex(MNRET)}")
        w = t.label("W")
        t.emit(f"{w}:", 0)
        t.emit("auipc x7, 0")
        t.emit(f"{lab}:", 0)
        t.emit("nop")
        t.outcome("ok", lab, "MNRET in M-mode")
        t.la("x6", w)
        t.emit("sub x7, x7, x6")
        t.emit("addi x7, x7, 1")  # any value: a correct MNRET leaves x7 from before
        t.check("x7", 1, lab, "mutant: MNRET falls through")
        return t
    mnret_land(t, "M", "MNRET in M-mode with mnepc = L, MNPP = M")
    return t


def t_mnret_mode() -> TestFile:
    t = tf("mnret_mode")
    t.describe(
        rule_text="MNRET is an M-mode-only instruction",
        source=SRC,
        context="Below M-mode MNRET is an illegal instruction. From VS and VU it is illegal-instruction too, not "
        "virtual-instruction: it is not allowed in HS-mode or U-mode either (hypervisor.adoc, virtual-instruction "
        "exceptions). A design that treats MNRET like SRET might allow it in S-mode or gate it on mstatus.TSR / "
        "hstatus.VTSR.",
        plan="Before each case, mnepc = the instruction after the MNRET and MNPP = M, so a design that executes "
        "MNRET below M-mode continues there in M-mode without a trap.\n"
        "1. M-mode: MNRET does not trap.\n"
        "2. S-mode with mstatus.TSR = 0 and with TSR = 1, U-mode, VS-mode with hstatus.VTSR = 0 and 1, and "
        "VU-mode: MNRET raises illegal-instruction (cause 2) from that mode, with xepc = the MNRET and xtval = 0 "
        "or 0x70200073.",
    )
    cases = [("M", None), ("S", 0), ("S", 1), ("U", None), ("VS", 0), ("VS", 1), ("VU", None)]
    for mode, tsr in cases:
        c = mode_cond(mode)
        with ExitStack() as stack:
            if c:
                stack.enter_context(t.only_if(c))
            nxt = t.label("after")
            if mode == "S" and tsr is not None:
                t.li("x14", MSTATUS_TSR)
                t.emit(f"{'csrs' if tsr else 'csrc'} mstatus, x14  // mstatus.TSR = {tsr}")
            if mode == "VS" and tsr is not None:
                t.li("x14", HSTATUS_VTSR)
                t.emit(f"{'csrs' if tsr else 'csrc'} {hex(CSRN['hstatus'])}, x14  // hstatus.VTSR = {tsr}")
            t.la("x14", nxt)
            t.emit(f"csrw {csrn('mnepc')}, x14  // mnepc = the next instruction")
            t.li("x14", mnstatus_val("M"))
            t.emit(f"csrw {csrn('mnstatus')}, x14  // MNPP = M")
            lines = [f".word {hex(MNRET)}  // mnret", f"{nxt}:", "nop"]
            desc = "MNRET" + (
                f" with {'mstatus.TSR' if mode == 'S' else 'hstatus.VTSR'} = {tsr}" if tsr is not None else ""
            )
            if mode == "M":
                t.window("M", lines, "ok", desc)
            else:
                exp: object = ILLEGAL
                if mut("mnret_s_legal") and mode == "S" and tsr == 0:
                    exp = "ok"
                if mut("mnret_vs_virtual") and mode == "VS":
                    exp = 22
                lower_window(t, mode, lines, exp, desc, [0, MNRET])
            if tsr:
                t.li("x14", MSTATUS_TSR)
                if mode == "S":
                    t.emit("csrc mstatus, x14")
                else:
                    t.emit(f"csrc {hex(CSRN['hstatus'])}, x14")
    return t


def t_rnmi_resume() -> TestFile:
    t = tf("rnmi_resume")
    t.describe(
        rule_text="The RNMI handler can resume original execution using the new MNRET instruction, which restores "
        "the PC from `mnepc`, the privilege mode from `mnstatus`, and also sets `mnstatus`.NMIE, which re-enables "
        "interrupts.",
        source=SRC,
        context="MNRET uses only mnepc and mnstatus: mepc, mstatus.MPP and mstatus.MPV must not matter, and the "
        "interrupted context's mstatus is left intact (the point of a resumable NMI is that mepc, mcause and "
        "mstatus survive). The NMIE part is tested in mnret_restore.",
        issues=f'{ISSUE}1503: MNRET leaves MNPP unchanged (aswaterman: "Because the spec is silent on the matter, '
        'the implication is that MNPP is left unchanged.").',
        plan="For each target mode (M; S and U when implemented; VS and VU with H), with mnepc = L and "
        "mnstatus.MNPP/MNPV naming the mode:\n"
        "1. Negative dependencies: mepc points at a decoy W after the MNRET, mstatus.MPP names a different mode "
        "(U for an M target, M for the others) and mstatus.MPV = NOT MNPV (H).\n"
        "2. MNRET resumes at L (`auipc x7, 0` there reads L) in the target mode: `csrr mstatus` at L+4 does not trap "
        "in M-mode and raises illegal-instruction from the target mode (xPP/xPV in the log) below M.\n"
        "3. After the return to M-mode, mnstatus.MNPP and MNPV still hold the values written (MNRET does not "
        "change them, #1503).\n"
        "4. M target: mstatus right after MNRET equals mstatus before it (MIE = 0, MPIE = 1, MPP = U set up to "
        "differ from what an MRET would leave), ignoring MPRV and the Smdbltrp/Ssdbltrp MDT/SDT bits.",
    )
    sdt, mdt = 1 << 24, 1 << 42
    keep = X(((1 << 32) - 1) & ~(MSTATUS_MPRV | sdt), ((1 << 64) - 1) & ~(MSTATUS_MPRV | sdt | mdt))
    for mode in iter_modes(t, ("M", "S", "U", "VS", "VU")):
        pp, pv, _ = MODES[mode]
        target = mode
        if mut("mnret_uses_mpp") and mode == "S":
            target = "M"
        if mode == "M":
            with t.only_if("defined(U_SUPPORTED)"):
                set_mpp(t, "U")
            t.li("x14", MSTATUS_MIE)
            t.emit("csrc mstatus, x14  // MIE = 0")
            t.li("x14", MSTATUS_MPIE)
            t.emit("csrs mstatus, x14  // MPIE = 1")
        else:
            set_mpp(t, "M")
        with t.only_if(H):
            set_mpv(t, not pv)
        t.emit("csrr x9, mstatus  // mstatus before MNRET")
        if mut("mnret_uses_mepc") and mode == "M":
            lab = t.label("L")
            t.allow(1)
            t.la("x14", lab)
            t.emit(f"csrw {csrn('mnepc')}, x14")
            t.li("x14", mnstatus_val("M"))
            t.emit(f"csrw {csrn('mnstatus')}, x14")
            w = t.label("W")
            t.la("x14", w)
            t.emit("csrw mepc, x14")
            t.emit(f".word {hex(MNRET)}")
            t.emit(f"{w}:", 0)
            t.emit("auipc x7, 0")
            t.emit(f"{lab}:", 0)
            t.emit("nop")
            t.outcome("ok", lab, "MNRET")
            t.la("x6", w)
            t.emit("sub x7, x7, x6")
            t.check("x7", 0, lab, "mutant: MNRET returns to mepc = W")
        else:
            mnret_land(t, mode, f"MNRET with MNPP = {pp}, MNPV = {pv}", expect_mode=target)
        if mode == "M":
            t.emit("xor x8, x8, x9  // mstatus after ^ before")
            exp = 0
            if mut("mnret_mret_side_effects"):
                exp = MSTATUS_MIE  # MIE <- MPIE (= 1)
            t.check_masked("x8", keep, exp, here(t), "mstatus unchanged by MNRET to M-mode (except MPRV/SDT/MDT)")
        read_mnstatus(t)
        exp_pp = 0 if mut("mnret_mnpp_to_u") else (pp << MNPP_SH)
        t.check_masked("x7", 3 << MNPP_SH, exp_pp, here(t), f"MNPP after MNRET to {mode}-mode is unchanged")
        with t.only_if(H):
            t.check_masked("x7", MNPV, MNPV if pv else 0, here(t), f"MNPV after MNRET to {mode}-mode is unchanged")
    with t.only_if(H):
        set_mpv(t, False)
    set_mpp(t, "M")
    return t


def t_mnret_restore() -> TestFile:
    t = tf("mnret_restore")
    t.describe(
        rule_text="This instruction also sets `mnstatus`.NMIE.",
        source=SRC,
        context="NMIE is 1 throughout (the framework boot sets it and software cannot clear it), so MNRET's setting "
        "of NMIE is visible only as NMIE = 1 afterwards. Each MNRET is preceded by an mnstatus write with NMIE = 0 "
        "(an attempt to clear it, which has no effect); a design that let the write clear NMIE must still have "
        "NMIE = 1 after the MNRET. NMIE = 1 is also shown by behavior: an exception in M-mode afterwards reaches the "
        "ordinary M-mode handler (with NMIE = 0 it would go to the RNMI exception handler).",
        plan="For each target mode (M; S and U when implemented; VS and VU with H):\n"
        "1. mnstatus = MNPP/MNPV of the mode with NMIE = 0 written, mnepc = L, MNRET: resumes at L in that mode.\n"
        "2. Back in M-mode, mnstatus.NMIE reads 1.\n"
        "3. An ebreak in M-mode traps to the M-mode trap handler (cause 3, logged).",
    )
    for mode in iter_modes(t, ("M", "S", "U", "VS", "VU")):
        mnret_land(t, mode, f"MNRET to {mode}-mode after writing NMIE = 0", nmie=False)
        read_mnstatus(t)
        t.check_masked("x7", NMIE, NMIE, here(t), f"NMIE = 1 after MNRET to {mode}-mode")
        t.window("M", ["ebreak"], BREAKPOINT, f"ebreak after MNRET to {mode}-mode (the M-mode handler takes it)")
    return t


def t_mnret_mprv() -> TestFile:
    t = tf("mnret_mprv")
    t.describe(
        rule_text="If MNRET changes the privilege mode to a mode less privileged than M, it also sets `mstatus`.MPRV "
        "to 0.",
        source=SRC,
        context="MPRV exists only with U-mode (read-only 0 otherwise), so the file does nothing on M-only harts. "
        "MPRV is cleared on the new mode (MNPP), not on mstatus.MPP. With MPRV = 1 in M-mode, MPP is set to "
        "M while memory is accessed, so the test's own loads and stores are unaffected; for the M-target case MPP = U "
        "is set only across the MNRET (no memory access until MPRV is cleared again).",
        plan="1. MPRV = 1, MPP = U, MNRET to M-mode: MPRV is still 1 right after MNRET (read by "
        "`csrr mstatus` at the landing point), then it is cleared.\n"
        "2. MPRV = 1, MPP = M, MNRET to S, U, VS and VU (when implemented): the privilege probe in that mode traps to "
        "M-mode, and the mstatus saved by the trap handler on entry (the trap log) has MPRV = 0. (Reading mstatus after "
        "the return to M-mode would not do: the handler's MRET to the lower mode clears MPRV itself.) MPP = M ensures a design that clears MPRV based on MPP rather than the new mode fails.",
    )
    # MPRV is read-only 0 without U-mode, so every case needs U
    with t.only_if("defined(U_SUPPORTED)"):
        for mode in iter_modes(t, ("M", "S", "U", "VS", "VU")):
            set_mpp(t, "U" if mode == "M" else "M")
            pre = [f"li x14, {MSTATUS_MPRV}", "csrs mstatus, x14  // MPRV = 1"]
            after = [f"li x14, {MSTATUS_MPRV}", "csrc mstatus, x14  // MPRV = 0 at once"] if mode == "M" else None
            mnret_land(t, mode, f"MNRET to {mode}-mode with MPRV = 1", after=after, pre=pre)
            if mode == "M":
                set_mpp(t, "M")
                t.emit("srli x8, x8, 17")
                t.emit("andi x8, x8, 1")
                t.check("x8", 0 if mut("mnret_clears_mprv_to_m") else 1, here(t), "MPRV still 1 after MNRET to M-mode")
            else:
                # mstatus saved at entry to the probe's trap: before the handler's MRET, which clears MPRV itself
                t.emit("AI_LOG(x8, TRAPLOG_STATUS)", 10)
                t.emit("srli x8, x8, 17")
                t.emit("andi x8, x8, 1")
                exp = 1 if (mut("mnret_keeps_mprv") and mode == "U") else 0
                t.check("x8", exp, here(t), f"MPRV = 0 in {mode}-mode after MNRET (mstatus at the probe's trap)")
                t.li("x14", MSTATUS_MPRV)
                t.emit("csrc mstatus, x14")
    return t


def t_mnret_zicfilp() -> TestFile:
    t = tf("mnret_Zicfilp", REQ + ["Zicfilp"])
    t.describe(
        rule_text="If the Zicfilp extension is implemented, then if the new privileged mode is __y__, MNRET sets "
        "`ELP` to the logical AND of __y__LPE (see <<FCFIACT>>) and `mnstatus`.MNPELP.",
        source=SRC,
        context="xLPE (cfi.adoc, FCFIACT): M = mseccfg.MLPE; S/HS = menvcfg.LPE; VS = henvcfg.LPE; U and VU = "
        "senvcfg.LPE when S-mode exists, otherwise U = menvcfg.LPE. ELP is observed at the MNRET target: the "
        "target is an ebreak, followed by a 4-byte-aligned `lpad 0` (auipc x0, 0). With ELP = 1 the ebreak is not a "
        "landing pad and raises a software-check exception (cause 18, xtval 0 or 2) with MPELP = 1 in the trap "
        "handler's saved mstatus; with ELP = 0 the ebreak takes a breakpoint (cause 3) with MPELP = 0. Either way "
        "the handler resumes at the lpad, which an MRET restoring ELP = 1 needs.",
        plan="For each target mode y (M; S and U when implemented; VS and VU with H):\n"
        "1. yLPE = 1, MNPELP = 1: software-check, MPELP = 1.\n"
        "2. yLPE = 1, MNPELP = 0: breakpoint, MPELP = 0.\n"
        "3. yLPE = 0, MNPELP = 1, with the LPE bit of a different mode set (menvcfg.LPE for M, VS and U with S; "
        "mseccfg.MLPE for S and for U without S; henvcfg.LPE for VU): breakpoint, MPELP = 0.\n"
        "Every LPE bit is cleared again after each case.",
    )
    env = {"M": ("mseccfg", MLPE), "S": ("menvcfg", LPE), "VS": ("henvcfg", LPE)}

    def lpe_of(y: str) -> list[tuple[str, int, str | None]]:
        """(csr, bit, condition) choices for yLPE."""
        if y in env:
            return [(env[y][0], env[y][1], None)]
        return [("senvcfg", LPE, "defined(S_SUPPORTED)"), ("menvcfg", LPE, "!defined(S_SUPPORTED)")]

    # another mode's LPE bit, set in the yLPE = 0 cases: U uses mseccfg.MLPE on harts without S (where menvcfg.LPE
    # is ULPE itself); VU uses henvcfg.LPE (the guest supervisor's enable, not VU's)
    other = {
        "M": ("menvcfg", LPE),
        "S": ("mseccfg", MLPE),
        "VS": ("menvcfg", LPE),
        "U": ("menvcfg", LPE),
        "VU": ("henvcfg", LPE),
    }

    def setbit(csr: str, bit: int, on: bool) -> None:
        t.li("x14", bit)
        t.emit(f"{'csrs' if on else 'csrc'} {hex(CSRN[csr])}, x14  // {csr} {'|=' if on else '&= ~'} {bit:#x}")

    def clear_all() -> None:
        setbit("mseccfg", MLPE, False)
        with t.only_if("defined(S_SUPPORTED) || defined(U_SUPPORTED)"):
            setbit("menvcfg", LPE, False)
        with t.only_if("defined(S_SUPPORTED)"):
            setbit("senvcfg", LPE, False)
        with t.only_if(H):
            setbit("henvcfg", LPE, False)

    def case(y: str, ylpe: bool, mnpelp: bool, use_other: bool) -> None:
        elp = ylpe and mnpelp
        if mut("elp_ignores_lpe"):
            elp = mnpelp
        if mut("elp_never"):
            elp = False
        for csr, bit, cond in lpe_of(y):
            ctx = t.only_if(cond) if cond else None
            if ctx:
                ctx.__enter__()
            exp_elp = elp
            if mut("elp_u_menvcfg") and y == "U" and csr == "senvcfg":
                exp_elp = mnpelp and use_other  # models ULPE = menvcfg.LPE
            if mut("elp_vu_henvcfg") and y == "VU" and use_other:
                exp_elp = mnpelp  # models VULPE = henvcfg.LPE
            if ylpe:
                setbit(csr, bit, True)
            if use_other:
                ocsr, obit = other[y]
                if ocsr == csr:  # U without S: ULPE is menvcfg.LPE
                    ocsr, obit = "mseccfg", MLPE
                if ocsr != csr:
                    if ocsr == "menvcfg":
                        with t.only_if("defined(U_SUPPORTED)"):
                            setbit(ocsr, obit, True)
                    else:
                        setbit(ocsr, obit, True)
            fld = "MLPE" if csr == "mseccfg" else "LPE"
            onote = ("mseccfg.MLPE" if other[y][0] == csr else f"{other[y][0]}.LPE") + " = 1"
            body(y, mnpelp, exp_elp, f"{y}LPE = {csr}.{fld} = {int(ylpe)}" + (f", {onote}" if use_other else ""))
            clear_all()
            if ctx:
                ctx.__exit__(None, None, None)

    def body(y: str, mnpelp: bool, elp: bool, what: str) -> None:
        tgt, lp, cont = t.label("tgt"), t.label("lp"), t.label("cont")
        t.allow(1)
        t.la("x14", tgt)
        t.emit(f"csrw {csrn('mnepc')}, x14")
        t.li("x14", mnstatus_val(y, MNPELP if mnpelp else 0))
        t.emit(f"csrw {csrn('mnstatus')}, x14  // MNPP/MNPV of {y}, MNPELP = {int(mnpelp)}")
        t.emit(f".word {hex(MNRET)}  // mnret")
        t.emit(f"j {cont}  // not reached")
        t.emit(".p2align 2", 0)
        t.emit(f"{tgt}:", 0)
        t.emit("ebreak  // MNRET target: not a landing pad")
        t.emit(f"{lp}:", 0)
        t.emit("auipc x0, 0  // lpad 0: the handler resumes here")
        t.emit(f"{cont}:", 0)
        if y != "M":
            t.emit("RVTEST_TSBI_GOTO_MMODE", 120)
        d = f"MNRET to {y}-mode, MNPELP = {int(mnpelp)}, {what}"
        if elp:
            t.outcome(SWCHECK, tgt, f"{d}: ELP = 1", [0, 2], origin=y)
        else:
            t.outcome(BREAKPOINT, tgt, f"{d}: ELP = 0", None, origin=y)
        mpelp_from_log(t, "x8")
        t.check("x8", 1 if elp else 0, tgt, f"{d}: MPELP saved by the trap at the target")

    for y in iter_modes(t, ("M", "S", "U", "VS", "VU")):
        case(y, True, True, False)
        case(y, True, False, False)
        case(y, False, True, True)
    return t


# ---------------------------------------------------------------- mnstatus
def t_nmie_set_clear() -> TestFile:
    t = tf("mnstatus_nmie_set_clear")
    t.describe(
        rule_text="Software can set NMIE to 1, but attempts to clear NMIE have no effect.",
        source=SRC,
        context="NMIE is 1 from the framework boot. Only the no-effect half is observable without an RNMI: every "
        "write form that would clear NMIE leaves it 1, while the rest of the write still takes effect (MNPP). The rule "
        "is read per field, as for other CSR fields: the attempt to clear NMIE has no effect, not the whole write "
        "(mnstatus would otherwise be unwritable by csrw without NMIE, and the RNMI handler sets MNPP with ordinary "
        "writes). NMIE = 1 "
        "is also checked by behavior: an M-mode exception still reaches the ordinary trap handler (with NMIE = 0 it "
        "would go to the RNMI exception handler).",
        plan="1. csrrc x7 with rs1 = NMIE; csrrci 8; csrrw x7 with NMIE = 0 and MNPP = S (U on harts without S, "
        "M without U); csrrwi 0; csrrw x0 with 0: rd (where written) has NMIE = 1 and NMIE reads 1 afterwards.\n"
        "2. The csrrw with MNPP = S/U/M and NMIE = 0 still writes MNPP.\n"
        "3. Set forms (csrrs with NMIE, csrrsi 8, csrrw with NMIE = 1) and read forms (csrrs/csrrsi with x0/0) leave "
        "NMIE = 1.\n"
        "4. An ebreak in M-mode after the clear attempts is taken by the M-mode handler (cause 3).",
    )
    low = [
        ("S", "defined(S_SUPPORTED)"),
        ("U", "defined(U_SUPPORTED) && !defined(S_SUPPORTED)"),
        ("M", "!defined(U_SUPPORTED)"),
    ]
    ops = [
        ("csrrc x7, {c}, x6", NMIE, "csrrc rs1 = NMIE", True),
        ("csrrci x7, {c}, 8", None, "csrrci uimm = 8", True),
        ("csrrw x7, {c}, x6", "mnpp", "csrrw NMIE = 0, MNPP = lowest mode", True),
        ("csrrwi x7, {c}, 0", None, "csrrwi uimm = 0", True),
        ("csrrw x0, {c}, x6", 0, "csrrw rd = x0 with 0", False),
        ("csrrs x7, {c}, x6", NMIE, "csrrs rs1 = NMIE", True),
        ("csrrsi x7, {c}, 8", None, "csrrsi uimm = 8", True),
        ("csrrw x7, {c}, x6", NMIE | (3 << MNPP_SH), "csrrw NMIE = 1, MNPP = M", True),
        ("csrrs x7, {c}, x0", None, "csrrs rs1 = x0", True),
        ("csrrsi x7, {c}, 0", None, "csrrsi uimm = 0", True),
    ]
    for asm, val, desc, has_rd in ops:
        lab = t.label("op")
        if val == "mnpp":
            for m, cond in low:
                with t.only_if(cond):
                    t.li("x6", MODES[m][0] << MNPP_SH)
        elif val is not None:
            t.li("x6", val)
        t.emit(f"{lab}:", 0)
        t.emit(asm.format(c=csrn("mnstatus")) + "  // mnstatus")
        if has_rd:
            t.check_masked("x7", NMIE, NMIE, lab, f"{desc}: old value has NMIE = 1")
        read_mnstatus(t, "x8")
        clear = asm.startswith(("csrrc", "csrrci")) or (val in (0, "mnpp") or asm.startswith("csrrwi"))
        exp = 0 if (mut("nmie_clearable") and asm.startswith("csrrc ")) else NMIE
        t.check_masked("x8", NMIE, exp, lab, f"{desc}: NMIE reads 1 afterwards" + (" (clear attempt)" if clear else ""))
        if val == "mnpp":
            for m, cond in low:
                with t.only_if(cond):
                    e = (3 << MNPP_SH) if mut("nmie_write_ignored") else (MODES[m][0] << MNPP_SH)
                    t.check_masked("x8", 3 << MNPP_SH, e, lab, f"{desc}: MNPP written ({m})")
    t.window("M", ["ebreak"], BREAKPOINT, "ebreak after the NMIE clear attempts (the M-mode handler takes it)")
    return t


def mnpp_legal(v: int) -> list[tuple[str, list[int]]]:
    """(condition, legal MNPP read-back values) after writing v (WARL, any legal value for an illegal one)."""
    if v == 3:
        return [("1", [3])]
    if v == 1:
        return [
            ("defined(S_SUPPORTED)", [1]),
            ("defined(U_SUPPORTED) && !defined(S_SUPPORTED)", [0, 3]),
            ("!defined(U_SUPPORTED)", [3]),
        ]
    if v == 0:
        return [("defined(U_SUPPORTED)", [0]), ("!defined(U_SUPPORTED)", [3])]
    return [
        ("defined(S_SUPPORTED)", [0, 1, 3]),
        ("defined(U_SUPPORTED) && !defined(S_SUPPORTED)", [0, 3]),
        ("!defined(U_SUPPORTED)", [3]),
    ]


def t_mnpp() -> TestFile:
    t = tf("mnstatus_mnpp_op")
    t.describe(
        rule_text="The `mnstatus` CSR holds a two-bit field, MNPP, which on entry to the RNMI trap handler holds the "
        "privilege mode of the interrupted context, encoded in the same manner as `mstatus`.MPP.",
        source=SRC,
        context="The entry half needs an RNMI, which no configuration can raise. The field itself is tested. The spec "
        'does not call MNPP WARL or software-writable; that is inferred from "encoded in the same manner as '
        'mstatus.MPP" and from MNRET, which returns to the mode MNPP names (an RNMI handler or reset code must be able '
        "to set it). Like MPP it is WARL and holds M and every implemented lower mode, encoded 3 = M, 1 = S, 0 = U; writing an "
        "unimplemented mode or the reserved value 2 leaves some legal value. The encoding is also shown through "
        "MNRET (rnmi_resume sweeps every mode).",
        issues=f"{ISSUE}2585: the mapping of an illegal MPP/MNPP value (2) to a legal one is not architecturally "
        "defined (allenjbaum), so any implemented mode is accepted.",
        plan="1. Write MNPP = 3, 1, 0, 2 (csrw, with NMIE = 1), each followed by a read: 3 reads 3; 1 reads 1 with "
        "S-mode (otherwise a legal mode); 0 reads 0 with U-mode (otherwise 3); 2 reads a legal mode (0, 1, 3 as "
        "implemented).\n"
        "2. csrrs/csrrc of single MNPP bits from MNPP = 3: csrrc of bit 12 gives 1 (S) or a legal mode; csrrs of bit "
        "12 from MNPP = 0 (U) gives 2 written: a legal mode.\n"
        "3. MNPP = 1 (S, when implemented) then MNRET resumes in S-mode, and MNPP = 0 (U) in U-mode.",
    )
    mask = 3 << MNPP_SH

    def check_legal(v: int, desc: str) -> None:
        for cond, vals in mnpp_legal(v):
            with t.only_if(cond):
                ev = [x << MNPP_SH for x in vals]
                if mut("mnpp_holds_2") and v == 2:
                    ev = [2 << MNPP_SH]
                t.check_masked("x7", mask, ev if len(ev) > 1 else ev[0], here(t), desc)

    for v in (3, 1, 0, 2):
        t.li("x6", NMIE | (v << MNPP_SH))
        t.emit(f"csrw {csrn('mnstatus')}, x6  // MNPP = {v}")
        read_mnstatus(t)
        check_legal(v, f"MNPP written {v}")
    t.li("x6", NMIE | (3 << MNPP_SH))
    t.emit(f"csrw {csrn('mnstatus')}, x6  // MNPP = 3")
    t.li("x6", 1 << 12)
    t.emit(f"csrrc x0, {csrn('mnstatus')}, x6  // clear MNPP[1]: 1 written")
    read_mnstatus(t)
    check_legal(1, "csrrc of MNPP[1] from MNPP = 3 (1 written)")
    t.li("x6", 3 << MNPP_SH)
    t.emit(f"csrc {csrn('mnstatus')}, x6  // MNPP = 0 written")
    t.li("x6", 1 << 12)
    t.emit(f"csrrs x0, {csrn('mnstatus')}, x6  // set MNPP[1] from 0 (or the legal value read): writes 2 or 3")
    read_mnstatus(t)
    # from U (0) the set gives 2 (reserved); from M (3) on an M-only hart it gives 3
    for cond, vals in mnpp_legal(2):
        with t.only_if(cond):
            t.check_masked(
                "x7",
                mask,
                [x << MNPP_SH for x in vals] if len(vals) > 1 else vals[0] << MNPP_SH,
                here(t),
                "csrrs of MNPP[1] (2 written)",
            )
    for mode in iter_modes(t, ("S", "U")):
        mnret_land(t, mode, f"MNPP = {MODES[mode][0]}", wrong_mepc=False)
    return t


def t_mnpv() -> TestFile:
    t = tf("mnstatus_mnpv_op", REQ + ["H"])
    t.describe(
        rule_text="If the H extension is also implemented, `mnstatus` also holds a one-bit field, MNPV, which on "
        "entry to the RNMI trap handler holds the virtualization mode of the interrupted context, encoded in the same "
        "manner as `mstatus`.MPV.",
        source=SRC,
        context="The entry half needs an RNMI. The field is tested through software writes and MNRET: with "
        "MNPP = S or U, MNPV = 1 returns to VS or VU and MNPV = 0 to HS or U. With MNPP = M there is no virtual "
        "M-mode, so MNRET returns to M-mode (V = 0), as MRET does with MPP = M.",
        issues=f"{ISSUE}2899: MNPV exists only with H.",
        plan="1. MNPV = 1 with MNPP = S reads 1; MNPV = 0 reads 0; MNPV = 1 with MNPP = U reads 1.\n"
        "2. MNRET with MNPP = S: MNPV = 1 resumes in VS-mode, MNPV = 0 in HS-mode (with mstatus.MPV = 1, which "
        "must not matter).\n"
        "3. MNRET with MNPP = U: MNPV = 1 resumes in VU-mode, MNPV = 0 in U-mode (mstatus.MPV = 1).\n"
        "4. MNRET with MNPP = M and MNPV = 1 resumes in M-mode.",
    )
    for pp, pv in ((1, 1), (1, 0), (0, 1)):
        t.li("x6", NMIE | (pp << MNPP_SH) | (MNPV if pv else 0))
        t.emit(f"csrw {csrn('mnstatus')}, x6  // MNPP = {pp}, MNPV = {pv}")
        read_mnstatus(t)
        t.check_masked("x7", MNPV, MNPV if pv else 0, here(t), f"MNPV written {pv} (MNPP = {pp})")
    set_mpv(t, True)
    for mode in ("VS", "S", "VU", "U"):
        exp = mode
        if mut("mnpv_ignored") and mode == "VS":
            exp = "S"
        mnret_land(t, mode, f"MNRET with MNPP = {MODES[mode][0]}, MNPV = {MODES[mode][1]}", expect_mode=exp)
        set_mpv(t, True)
    set_mpv(t, False)
    mnret_land(t, "M", "MNRET with MNPP = M, MNPV = 1", extra=MNPV, expect_mode="VS" if mut("mnpv_m") else "M")
    return t


def t_mnpelp() -> TestFile:
    t = tf("mnstatus_mnpelp_op", REQ + ["Zicfilp"])
    t.describe(
        rule_text="If the Zicfilp extension is implemented, `mnstatus` also holds the MNPELP field, which on entry to "
        "the RNMI trap handler holds the previous `ELP` state.",
        source=SRC,
        context="The entry half needs an RNMI. MNPELP (bit 9) holds a value: it is written by software and read "
        "back, whatever mseccfg.MLPE (like MPELP, which is writable whatever MLPE: "
        f"{ISSUE}3331). MNRET's use of it is tested in mnret_Zicfilp.",
        plan="With mseccfg.MLPE = 0 and then 1: MNPELP written 1 reads 1, written 0 reads 0 (csrw), and csrrs/csrrc "
        "of bit 9 set and clear it.",
    )
    for mlpe in (0, 1):
        t.li("x14", MLPE)
        t.emit(f"{'csrs' if mlpe else 'csrc'} {hex(CSRN['mseccfg'])}, x14  // mseccfg.MLPE = {mlpe}")
        for v in (1, 0):
            t.li("x6", NMIE | (3 << MNPP_SH) | (MNPELP if v else 0))
            t.emit(f"csrw {csrn('mnstatus')}, x6  // MNPELP = {v}")
            read_mnstatus(t)
            e = 0 if mut("mnpelp_ro0") else (MNPELP if v else 0)
            t.check_masked("x7", MNPELP, e, here(t), f"MNPELP written {v} (csrw), MLPE = {mlpe}")
        t.li("x6", MNPELP)
        t.emit(f"csrs {csrn('mnstatus')}, x6")
        read_mnstatus(t)
        t.check_masked("x7", MNPELP, 0 if mut("mnpelp_ro0") else MNPELP, here(t), f"csrs MNPELP, MLPE = {mlpe}")
        t.emit(f"csrc {csrn('mnstatus')}, x6")
        read_mnstatus(t)
        t.check_masked("x7", MNPELP, 0, here(t), f"csrc MNPELP, MLPE = {mlpe}")
    t.li("x14", MLPE)
    t.emit(f"csrc {hex(CSRN['mseccfg'])}, x14")
    return t


# ---------------------------------------------------------------- mnscratch
EDGES = {
    32: [
        0,
        1,
        2,
        (1 << 32) - 1,
        (1 << 32) - 2,
        1 << 31,
        (1 << 31) + 1,
        (1 << 31) - 1,
        (1 << 31) - 2,
        1 << 16,
        (1 << 16) - 1,
        0x55555555,
        0xAAAAAAAA,
    ],
    64: [
        0,
        1,
        2,
        (1 << 64) - 1,
        (1 << 64) - 2,
        1 << 63,
        (1 << 63) + 1,
        (1 << 63) - 1,
        (1 << 63) - 2,
        1 << 32,
        (1 << 32) - 1,
        0x5555555555555555,
        0xAAAAAAAAAAAAAAAA,
    ],
}


def t_mnscratch() -> TestFile:
    t = tf("mnscratch_sz_acc_op")
    t.describe(
        rule_text="The `mnscratch` CSR holds an MXLEN-bit read-write register which enables the RNMI trap handler to "
        "save and restore the context that was interrupted.",
        source=SRC,
        context="mnscratch has no WARL restriction: every MXLEN-bit value is held. Access from lower modes is in "
        "Smrnmi_csrs.",
        plan="1. csrw then csrr of 0, 1, 2, -1, -2, MIN, MIN+1, MAX, MAX-1, 2^(XLEN/2), 2^(XLEN/2)-1, 0x55.., 0xAA.. "
        "and two random values reads each back exactly.\n"
        "2. All eight CSR forms from a random old value with a random rs1 (uimm 0x15 for the immediate forms): rd "
        "gets the old value, and the CSR holds old (read forms), rs1/uimm (csrrw/csrrwi), old | src (csrrs/csrrsi) or "
        "old & ~src (csrrc/csrrci).",
    )
    vals = [X(a, b) for a, b in zip(EDGES[32], EDGES[64])] + [t.rand_x(), t.rand_x()]
    for v in vals:
        t.load("x6", v)
        t.emit(f"csrw {csrn('mnscratch')}, x6")
        t.emit(f"csrr x7, {csrn('mnscratch')}")
        exp = v
        if mut("mnscratch_32bit"):
            exp = X(v.v32, int(v.v64) & 0xFFFFFFFF)  # type: ignore[arg-type]
        t.check("x7", exp, here(t), f"mnscratch = {v.v32:#x} / {v.v64:#x}")
    for asm, f3, rd, rs1, kind, _ in FORMS:
        old, rs = t.rand_x(), t.rand_x()
        t.load("x8", old, "old value")
        t.emit(f"csrw {csrn('mnscratch')}, x8")
        if rs1 == 6:
            t.load("x6", rs, "rs1")
        lab = t.label("form")
        t.emit(f"{lab}:", 0)
        t.emit(asm.format(c=csrn("mnscratch")) + "  // mnscratch")
        new32 = form_value((asm, f3, rd, rs1, kind, True), int(old.v32), int(rs.v32), 32)[1]
        new64 = form_value((asm, f3, rd, rs1, kind, True), int(old.v64), int(rs.v64), 64)[1]
        if mut("mnscratch_csrrc_as_csrrs") and f3 == 3:
            new32, new64 = int(old.v32) | int(rs.v32), int(old.v64) | int(rs.v64)
        if rd:
            t.check("x7", old, lab, f"{kind}: rd = old value")
        t.emit(f"csrr x7, {csrn('mnscratch')}")
        t.check("x7", X(new32, new64), lab, f"{kind}: new value")
    return t


# ---------------------------------------------------------------- mnepc
def c_either(t: TestFile, on: Callable[[], object], off: Callable[[], object]) -> None:
    """Branch on the current misa.C (IALIGN = 16 when set)."""
    misa_c(t, "x1")
    t.either("x1", on, off)


def base_l(t: TestFile, reg: str = "x9") -> None:
    """reg = L', the address of this test's code (rvtest_code_begin) with bits 10:0 cleared: a valid address, and so
    is L' with any of bits 10:2 set (it stays below 2^bitlen(L))."""
    t.la(reg, "rvtest_code_begin")
    t.emit(f"srli {reg}, {reg}, 11")
    t.emit(f"slli {reg}, {reg}, 11")


def wr_rd_mnepc(t: TestFile, src: str = "x6") -> None:
    t.emit(f"csrw {csrn('mnepc')}, {src}")
    t.emit(f"csrr x7, {csrn('mnepc')}")


def check_rel(t: TestFile, exp: int, desc: str, base: str = "x9") -> None:
    """x7 ^ base must be exp."""
    t.emit(f"xor x7, x7, {base}")
    t.check("x7", exp, here(t), desc)


def sv_probe(t: TestFile, mode: int, reg: str = "x8") -> None:
    """reg = 1 when satp.MODE = mode is supported (an unsupported MODE write has no effect); satp restored. RV64,
    S-mode."""
    t.emit("csrr x14, satp")
    t.load(reg, X(0, mode << 60), f"satp.MODE = {mode}")
    t.emit(f"csrw satp, {reg}")
    t.emit(f"csrr {reg}, satp")
    t.emit("csrw satp, x14")
    t.emit(f"srli {reg}, {reg}, 60")
    t.emit(f"addi {reg}, {reg}, -{mode}")
    t.emit(f"seqz {reg}, {reg}")


SV = {8: 39, 9: 48, 10: 57}


def sv32_probe(t: TestFile, reg: str = "x8") -> None:
    """reg = 1 when satp.MODE = Sv32 is supported; satp restored. RV32, S-mode."""
    t.emit("csrr x14, satp")
    t.li(reg, -(1 << 31))
    t.emit(f"csrw satp, {reg}")
    t.emit(f"csrr {reg}, satp")
    t.emit("csrw satp, x14")
    t.emit(f"srli {reg}, {reg}, 31")


def canon(t: TestFile, va: int, n: int) -> int:
    v = t.rand(va - 2) << 2 if n < 0 else n
    v &= (1 << va) - 1
    if v >> (va - 1):
        v |= ((1 << 64) - 1) ^ ((1 << va) - 1)
    return v


def t_mnepc_sz() -> TestFile:
    t = tf("mnepc_sz_acc_op")
    t.describe(
        rule_text="The `mnepc` CSR is an MXLEN-bit read-write register which on entry to the RNMI trap handler holds "
        "the PC of the instruction that took the interrupt.",
        source=SRC,
        context="The entry half needs an RNMI. Read-write access is tested with valid, 4-byte-aligned addresses "
        "(mnepc_warl and mnepc_bit0/ialign cover the WARL and low-bit rules). L' is the test's code address with bits "
        "10:0 cleared; L' with any of bits 10:2 set is also a valid address.",
        plan="1. All eight CSR forms from old = L' | d1 with rs1 = L' | d2 (csrrw) or d2 (csrrs/csrrc), uimm 0x14: rd "
        "gets the old value and the CSR holds the form's result (d1, d2 random multiples of 4 below 2^11).\n"
        "2. RV32 with Sv32 (satp probe; every 32-bit address is then valid): 0xFFFFFFFC and 0x80000000 read back "
        "exactly.\n"
        "3. RV64 with Sv39 (probed through satp): 0xFFFFFFC000000000 | random (an MXLEN-bit, canonical address) "
        "reads back exactly.",
    )
    base_l(t)
    for asm, f3, rd, rs1, kind, _ in FORMS:
        d1, d2 = t.rand(9) << 2, t.rand(9) << 2
        u = 0x14
        line = asm.format(c=csrn("mnepc")).replace("0x15", hex(u))
        t.li("x8", d1)
        t.emit("or x8, x8, x9  // old = L' | d1")
        t.emit(f"csrw {csrn('mnepc')}, x8")
        if f3 == 1:
            t.li("x6", d2)
            t.emit("or x6, x6, x9  // rs1 = L' | d2")
        elif rs1 == 6:
            t.li("x6", d2)
        lab = t.label("form")
        t.emit(f"{lab}:", 0)
        t.emit(line + "  // mnepc")
        if rd:
            t.emit("xor x7, x7, x9")
            t.check("x7", d1, lab, f"{kind}: rd = old value (xor L')")
        t.emit(f"csrr x7, {csrn('mnepc')}")
        imm = u if f3 in (5, 7) else (0 if f3 == 6 else None)
        src = d2 if f3 in (1, 2, 3) and rs1 == 6 else imm or 0
        if f3 == 5:  # absolute value
            t.check("x7", u, lab, f"{kind}: mnepc = uimm")
            continue
        new = {1: d2, 2: d1 | src, 6: d1 | src, 3: d1 & ~src, 7: d1 & ~src}.get(f3, d1)
        if f3 == 2 and rs1 == 0:
            new = d1
        check_rel(t, new, f"{kind}: new value (xor L')")
    with t.rv32_only(), t.only_if("defined(S_SUPPORTED)"):
        sv32_probe(t)

        def sv32() -> None:
            for v in (0xFFFFFFFC, 0x80000000):
                t.li("x6", v - (1 << 32) if v >> 31 else v)
                wr_rd_mnepc(t)
                t.check("x7", v, here(t), f"mnepc = {v:#x} (Sv32)")

        t.either("x8", sv32, lambda: None)
    with t.rv64_only(), t.only_if("defined(S_SUPPORTED)"):
        sv_probe(t, 8)

        def sv39() -> None:
            v = 0xFFFFFFC000000000 | (t.rand(36) << 2)
            t.load("x6", X(0, v))
            wr_rd_mnepc(t)
            exp = v & 0xFFFFFFFF if mut("mnepc_32bit") else v
            t.check("x7", X(0, exp), here(t), f"mnepc = {v:#x} (Sv39 canonical)")

        t.either("x8", sv39, lambda: None)
    return t


def t_mnepc_warl() -> TestFile:
    t = tf("mnepc_warl")
    t.describe(
        rule_text="`mnepc` is a *WARL* register that must be able to hold all valid virtual addresses.",
        source=SRC,
        context="Valid addresses: physical addresses below the PA width (the test uses its own code address L' with "
        "bits 10:2 varied, the data-section address and small addresses: all below 2^bitlen(L)) and, for each "
        "virtual-memory mode the hart supports (Sv32 on RV32: every 32-bit value) (probed by writing satp.MODE in M-mode; an unsupported MODE write has no effect), "
        "every address canonical in that mode. Values are 4-byte aligned so IALIGN does not matter, except bit-1 "
        "cases that run only while IALIGN = 16 (misa.C = 1, or Zca without C).",
        plan="1. 0, 4, three L' | random(10:2) values and the data-section address read back exactly; with IALIGN = 16, "
        "L' | 2.\n"
        "2. RV32 with Sv32 (satp probe): 0x7FFFFFFC, 0x80000000, 0xFFFFFFFC, 0x55555554, 0xAAAAAAA8 and two random "
        "aligned values read back exactly; with IALIGN = 16, 0xAAAAAAAA and 0x55555556 too.\n"
        "3. RV64 with Sv39 / Sv48 / Sv57: the top and bottom canonical halves' edges (2^(VA-1)-4, -2^(VA-1), "
        "-4) and a random canonical address read back exactly.",
    )
    for v in (0, 4):
        t.li("x6", v)
        wr_rd_mnepc(t)
        t.check("x7", v, here(t), f"mnepc = {v}")
    base_l(t)
    for _ in range(3):
        d = t.rand(9) << 2
        t.li("x6", d)
        t.emit("or x6, x6, x9")
        wr_rd_mnepc(t)
        check_rel(t, d, f"mnepc = L' | {d:#x}")
    t.la("x6", "ai_table")
    wr_rd_mnepc(t)
    t.emit("xor x7, x7, x6")
    t.check("x7", 0, here(t), "mnepc = the data-section address")

    def c_on_l() -> None:
        t.emit("ori x6, x9, 2")
        wr_rd_mnepc(t)
        check_rel(t, 2, "mnepc = L' | 2 (IALIGN = 16)")

    c_either(t, c_on_l, lambda: None)
    with t.rv32_only(), t.only_if("defined(S_SUPPORTED)"):
        sv32_probe(t)

        def sv32() -> None:
            vals = [0x7FFFFFFC, 0x80000000, 0xFFFFFFFC, 0x55555554, 0xAAAAAAA8, t.rand(30) << 2, t.rand(30) << 2]
            for v in vals:
                t.load("x6", X(v, 0))
                wr_rd_mnepc(t)
                t.check("x7", X(v, 0), here(t), f"mnepc = {v:#x} (Sv32: every 32-bit address is valid)")

            def c_on() -> None:
                for v in (0xAAAAAAAA, 0x55555556):
                    t.load("x6", X(v, 0))
                    wr_rd_mnepc(t)
                    t.check("x7", X(v, 0), here(t), f"mnepc = {v:#x} (Sv32, IALIGN = 16)")

            c_either(t, c_on, lambda: None)

        t.either("x8", sv32, lambda: None)
    with t.rv64_only(), t.only_if("defined(S_SUPPORTED)"):
        for mode, va in SV.items():
            sv_probe(t, mode)

            def sv(va: int = va) -> None:
                for v in ((1 << (va - 1)) - 4, canon(t, va, 1 << (va - 1)), (1 << 64) - 4, canon(t, va, -1)):
                    t.load("x6", X(0, v))
                    wr_rd_mnepc(t)
                    exp = v & 0xFFFFFFFF if mut("mnepc_32bit") else v
                    t.check("x7", X(0, exp), here(t), f"mnepc = {v:#x} (Sv{va} canonical)")

            t.either("x8", sv, lambda: None)
    return t


def t_mnepc_invalid() -> TestFile:
    t = tf("mnepc_invalid_convert", rv64=True)
    t.describe(
        rule_text="Prior to writing `mnepc`, implementations may convert an invalid address into some other invalid "
        "address that `mnepc` is capable of holding.",
        source=SRC,
        context="RV64 only: on RV32 no value is invalid under every configuration (with Sv32 every 32-bit address is "
        "valid, and physical addresses may be wider than 32 bits). The written values are invalid under every "
        "configuration: bits 63:57 differ from bit 56 (not canonical for Sv57, so neither for Sv39/Sv48) and the "
        "value is at least 2^59 (above any physical or Sv57x4 guest-physical address). What is read back may differ but must still be "
        "invalid. The test cannot know the hart's exact valid set, so it checks a necessary condition: the value "
        "read back is not below 2^bitlen(L) (L = this test's code address, a valid physical address, so everything "
        "below 2^bitlen(L) is a valid address) and, when Sv39 is supported (satp probe), is not Sv39-canonical (Sv39 "
        "canonical addresses are valid in every Sv mode).",
        plan="Write 0x4000.. | random, 0x8000.. | random (bit 56 = 0), 0xFE00.. | random and "
        "0x5555555555555554; for each value r read back:\n"
        "1. r & ~(2^bitlen(L) - 1) != 0 (r is not a small physical address).\n"
        "2. With Sv39: r[63:38] is neither all zeros nor all ones.",
    )
    t.la("x9", "rvtest_code_begin")
    for sh in (1, 2, 4, 8, 16, 32):
        t.emit(f"srli x6, x9, {sh}")
        t.emit("or x9, x9, x6")
    t.emit("not x9, x9  // ~(2^bitlen(L) - 1)")
    t.li("x1", 0)
    with t.only_if("defined(S_SUPPORTED)"):
        sv_probe(t, 8, "x1")
    t.emit("xori x1, x1, 1  // x1 = 1 when Sv39 is not supported")
    r56 = lambda: t.rand(54) << 2
    vals = [
        0x4000000000000000 | r56(),
        0x8000000000000000 | (r56() & ((1 << 56) - 1)),
        0xFE00000000000000 | (t.rand(40) << 2),
        0x5555555555555554,
    ]
    for v in vals:
        t.load("x6", X(0, v))
        wr_rd_mnepc(t)
        t.emit("and x8, x7, x9")
        t.emit("snez x8, x8  // not a small physical address")
        t.emit("srai x6, x7, 38")
        t.emit("addi x6, x6, 1")
        t.emit("sltiu x6, x6, 2  // Sv39-canonical")
        t.emit("xori x6, x6, 1")
        t.emit("or x6, x6, x1")
        t.emit("and x8, x8, x6")
        if mut("mnepc_invalid_to_valid"):
            t.emit("xori x8, x8, 1")
        t.check_bool("x8", here(t), f"mnepc written {v:#x} reads back an invalid address")
    return t


def t_mnepc_bit0() -> TestFile:
    t = tf("mnepc_bit0")
    t.describe(
        rule_text="The low bit of `mnepc` (`mnepc[0]`) is always zero.",
        source=SRC,
        context="Bit 1 follows IALIGN (misa.C, read at run time): with misa.C = 1 it is kept, with misa.C = 0 it "
        "reads 0.",
        plan="1. csrw L'|1 reads L'; L'|3 reads L'|2 (misa.C = 1) or L'.\n"
        "2. csrrwi 1 reads 0; csrrwi 0x1F reads 0x1E (misa.C = 1) or 0x1C.\n"
        "3. csrrsi 1 on mnepc = L' leaves L' (and rd = L').\n"
        "4. RV32: 0xFFFFFFFF reads 0xFFFFFFFE (misa.C = 1) or 0xFFFFFFFC.\n"
        "5. MNRET with mnepc written L+1 (L a 4-byte-aligned code label) resumes at L without a trap (the implicit "
        "read sees bit 0 = 0).",
    )
    base_l(t)
    b0 = 1 if mut("mnepc_bit0_kept") else 0
    t.emit("ori x6, x9, 1")
    wr_rd_mnepc(t)
    check_rel(t, b0, "mnepc = L' | 1")
    t.li("x6", 0)
    t.emit(f"csrrwi x0, {csrn('mnepc')}, 1")
    t.emit(f"csrr x7, {csrn('mnepc')}")
    t.check("x7", b0, here(t), "csrrwi mnepc, 1")
    t.emit(f"csrw {csrn('mnepc')}, x9")
    t.emit(f"csrrsi x7, {csrn('mnepc')}, 1")
    t.emit("xor x7, x7, x9")
    t.check("x7", 0, here(t), "csrrsi mnepc, 1: rd = L'")
    t.emit(f"csrr x7, {csrn('mnepc')}")
    check_rel(t, b0, "csrrsi mnepc, 1: mnepc = L'")

    def ialign(c: bool) -> None:
        keep = 2 if c else 0
        t.emit("ori x6, x9, 3")
        wr_rd_mnepc(t)
        check_rel(t, keep | b0, f"mnepc = L' | 3 (misa.C = {int(c)})")
        t.emit(f"csrrwi x0, {csrn('mnepc')}, 0x1F")
        t.emit(f"csrr x7, {csrn('mnepc')}")
        t.check("x7", 0x1C | keep | b0, here(t), f"csrrwi mnepc, 0x1F (misa.C = {int(c)})")
        with t.rv32_only():
            t.li("x6", -1)
            wr_rd_mnepc(t)
            t.check("x7", X(0xFFFFFFFC | keep | b0, 0), here(t), f"mnepc = 0xFFFFFFFF (misa.C = {int(c)})")

    c_either(t, lambda: ialign(True), lambda: ialign(False))
    # MNRET through mnepc = L + 1
    lab, cont = t.label("L"), t.label("cont")
    t.allow(1)
    t.la("x14", lab)
    t.emit("addi x14, x14, 1")
    t.emit(f"csrw {csrn('mnepc')}, x14  // mnepc = L + 1")
    t.li("x14", mnstatus_val("M"))
    t.emit(f"csrw {csrn('mnstatus')}, x14")
    t.emit(f".word {hex(MNRET)}")
    t.emit("auipc x7, 0  // not reached")
    t.emit(f"j {cont}")
    t.emit(".p2align 2", 0)
    t.emit(f"{lab}:", 0)
    t.emit("auipc x7, 0")
    t.emit(f"{cont}:", 0)
    t.outcome("ok", lab, "MNRET with mnepc written L + 1")
    t.la("x6", lab)
    t.emit("sub x7, x7, x6")
    t.check("x7", 0, lab, "MNRET with mnepc written L + 1 resumes at L")
    return t


def mnret_m_to(t: TestFile, lab: str, desc: str) -> None:
    """MNRET (MNPP = M) with mnepc already set; must resume at the 4-byte-aligned label lab without a trap."""
    cont = t.label("cont")
    t.allow(1)
    t.li("x14", mnstatus_val("M"))
    t.emit(f"csrw {csrn('mnstatus')}, x14")
    t.emit(f".word {hex(MNRET)}")
    t.emit("auipc x7, 0  // not reached")
    t.emit(f"j {cont}")
    t.emit(".p2align 2", 0)
    t.emit(f"{lab}:", 0)
    t.emit("auipc x7, 0")
    t.emit("nop")
    t.emit("nop")
    t.emit(f"{cont}:", 0)
    t.outcome("ok", lab, desc)
    t.la("x6", lab)
    t.emit("sub x7, x7, x6")
    t.check("x7", 0, lab, f"{desc}: resumes at L")


def t_mnepc_ialign32() -> TestFile:
    t = tf("mnepc_ialign32")
    t.describe(
        rule_text="On implementations that support only IALIGN=32, the two low bits (`mnepc[1:0]`) are always zero.",
        source=SRC,
        context="Runs only on harts without C or Zca (IALIGN = 32 only); the file passes trivially elsewhere.",
        plan="1. csrw L'|2, L'|3 read L'; csrrwi 0x16 reads 0x14; csrrsi 2 on L' leaves L'.\n"
        "2. MNRET with mnepc written L + 2 resumes at L without a trap.",
    )
    with t.only_if("!defined(C_SUPPORTED) && !defined(ZCA_SUPPORTED)"):
        base_l(t)
        for v in (2, 3):
            t.emit(f"ori x6, x9, {v}")
            wr_rd_mnepc(t)
            check_rel(t, 0, f"mnepc = L' | {v}")
        t.emit(f"csrrwi x0, {csrn('mnepc')}, 0x16")
        t.emit(f"csrr x7, {csrn('mnepc')}")
        t.check("x7", 0x14, here(t), "csrrwi mnepc, 0x16")
        t.emit(f"csrw {csrn('mnepc')}, x9")
        t.emit(f"csrsi {csrn('mnepc')}, 2")
        t.emit(f"csrr x7, {csrn('mnepc')}")
        check_rel(t, 0, "csrsi mnepc, 2 on L'")
        lab = t.label("L")
        t.la("x14", lab)
        t.emit("addi x14, x14, 2")
        t.emit(f"csrw {csrn('mnepc')}, x14  // mnepc = L + 2")
        mnret_m_to(t, lab, "MNRET with mnepc written L + 2")
    return t


def misa_c_writable(t: TestFile, body: Callable[[], object], note: str) -> None:
    """Under C_SUPPORTED, with misa.C = 1 at entry: save misa in x8, clear misa.C (at a 4-byte boundary), and run
    body only when the clear took effect (misa.C writable); restore misa afterwards."""
    with t.only_if("defined(C_SUPPORTED)"):
        t.emit("csrr x8, misa  // saved misa")
        t.emit("andi x1, x8, 4")

        def run() -> None:
            t.li("x6", 4)
            t.emit(".p2align 2", 0)
            t.emit("csrc misa, x6  // clear misa.C: IALIGN = 32")
            misa_c(t, "x1")
            t.emit("seqz x1, x1  // 1 when misa.C was cleared")
            t.either("x1", body, lambda: None)
            t.emit("csrw misa, x8  // restore misa")

        t.either("x1", run, lambda: None)
        t.comment(note)


def set_c(t: TestFile, on: bool) -> None:
    t.li("x6", 4)
    t.emit(".p2align 2", 0)
    t.emit(f"{'csrs' if on else 'csrc'} misa, x6  // misa.C = {int(on)}")


def t_mnepc_ialign_mask() -> TestFile:
    t = tf("mnepc_ialign_mask")
    t.describe(
        rule_text="If an implementation allows IALIGN to be either 16 or 32 (by changing CSR `misa`, for example), "
        "then, whenever IALIGN=32, bit `mnepc[1]` is masked on reads so that it appears to be 0. This masking occurs "
        "also for the implicit read by the MNRET instruction.",
        source=SRC,
        context="Needs a writable misa.C (probed: clear it and read misa back); the file does nothing otherwise. "
        "While misa.C = 0 the code is 4-byte instructions at 4-byte boundaries (MARCH has no C).",
        plan="1. With misa.C = 1, mnepc = L + 2 (L a 4-byte-aligned code label).\n"
        "2. Clear misa.C: mnepc reads L (bit 1 masked) by csrr and by csrrs/csrrsi with x0/0.\n"
        "3. MNRET (MNPP = M) resumes at L, the masked value, without an instruction-address-misaligned trap.",
    )
    lab = t.label("L")

    def body() -> None:
        t.emit(f"csrr x7, {csrn('mnepc')}")
        t.la("x6", lab)
        t.emit("sub x7, x7, x6")
        t.check("x7", 2 if mut("mnepc_bit1_unmasked") else 0, here(t), "csrr mnepc with IALIGN = 32 (L + 2 written)")
        t.emit(f"csrrsi x7, {csrn('mnepc')}, 0")
        t.emit("sub x7, x7, x6")
        t.check("x7", 0, here(t), "csrrsi mnepc, 0 with IALIGN = 32")
        mnret_m_to(t, lab, "MNRET with mnepc = L + 2 and IALIGN = 32")

    with t.only_if("defined(C_SUPPORTED)"):
        t.la("x6", lab)
        t.emit("addi x6, x6, 2")
        t.emit(f"csrw {csrn('mnepc')}, x6  // mnepc = L + 2 (misa.C = 1)")
    misa_c_writable(t, body, "end of the misa.C = 0 part")
    return t


def t_mnepc_bit1() -> TestFile:
    t = tf("mnepc_bit1_writable")
    t.describe(
        rule_text="Though masked, `mnepc[1]` remains writable when IALIGN=32.",
        source=SRC,
        context="Needs a writable misa.C (probed); the file does nothing otherwise.",
        plan="1. misa.C = 1: mnepc = L' + 2. Clear misa.C, set it again: mnepc reads L' + 2 (bit 1 kept while "
        "masked).\n"
        "2. misa.C = 0: write mnepc = L' + 2 (reads L'), set misa.C: reads L' + 2 (bit 1 written while masked).\n"
        "3. misa.C = 0: write mnepc = L' (bit 1 = 0), set misa.C: reads L'.\n"
        "4. misa.C = 0: csrrsi 2 on mnepc = L', set misa.C: reads L' + 2.",
    )

    def body() -> None:
        # C is clear here; mnepc holds L' + 2 written with C set
        set_c(t, True)
        t.emit(f"csrr x7, {csrn('mnepc')}")
        check_rel(t, 0 if mut("mnepc_bit1_lost") else 2, "L' + 2 written with misa.C = 1, misa.C cleared and set")
        for wr, exp, desc in (("ori x6, x9, 2", 2, "L' + 2"), ("mv x6, x9", 0, "L'"), (None, 2, "csrrsi 2 on L'")):
            set_c(t, False)
            if wr:
                t.emit(wr)
                wr_rd_mnepc(t)
                check_rel(t, 0, f"mnepc = {desc} written with misa.C = 0 reads L'")
            else:
                t.emit(f"csrw {csrn('mnepc')}, x9")
                t.emit(f"csrsi {csrn('mnepc')}, 2")
            set_c(t, True)
            t.emit(f"csrr x7, {csrn('mnepc')}")
            e = 0 if (mut("mnepc_bit1_lost") and exp) else exp
            check_rel(t, e, f"mnepc = {desc} written with misa.C = 0, then misa.C = 1")
        set_c(t, False)  # misa_c_writable restores misa

    with t.only_if("defined(C_SUPPORTED)"):
        base_l(t)
        t.emit("ori x6, x9, 2")
        t.emit(f"csrw {csrn('mnepc')}, x6  // mnepc = L' + 2 (misa.C = 1)")
    misa_c_writable(t, body, "end of the misa.C part")
    return t


def gen() -> list[TestFile]:
    return [
        t_csrs(),
        t_mnret_exist(),
        t_mnret_mode(),
        t_rnmi_resume(),
        t_mnret_restore(),
        t_mnret_mprv(),
        t_mnret_zicfilp(),
        t_nmie_set_clear(),
        t_mnpp(),
        t_mnpv(),
        t_mnpelp(),
        t_mnscratch(),
        t_mnepc_sz(),
        t_mnepc_warl(),
        t_mnepc_invalid(),
        t_mnepc_bit0(),
        t_mnepc_ialign32(),
        t_mnepc_ialign_mask(),
        t_mnepc_bit1(),
    ]


def main() -> None:
    for t in gen():
        p = t.write()
        print(f"{p.relative_to(p.parents[2])}: ~{t.ninst} instructions")


if __name__ == "__main__":
    main()
