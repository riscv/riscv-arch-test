#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate tests_ai/S: one test per normative rule about supervisor mode.

Rules come from src/priv/supervisor.adoc (except the virtual-memory sections, Sstc, H, Sscofpmf, pointer masking,
Zicfilp/Zicfiss and Ssdbltrp, which other suites own) and the S-mode-visible supervisor rules of machine.adoc.
Tests boot to S-mode (HS-mode with H), reach M-level CSRs through T-SBI, enter U-mode with sret and check traps in
the framework trap log. Rules that need M-mode (mideleg, misa, satp probes from M, TSR, MPRV) are <rule>_Sm.S files
that boot to M and require Sm. Helpers are in slib.py.
"""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent))
import slib as L
from aigen import POOL_NO_TSBI, POOL_TRAP, TestFile, X, mask
from slib import (
    FS,
    ILLEGAL,
    MAC,
    NO_C,
    POOL_INT,
    S1P12,
    SD,
    SIE,
    SPIE,
    SPP,
    SRC,
    SUP,
    UBE,
    VS,
    WPRI,
    XS,
    C,
    H,
    icause,
)

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from aigen import Expect, Value

SUITE = "S"
ISSUE = L.ISSUE
REQ = ["I", "S"]
MARCH = "rv${XLEN}i_zicsr_zifencei"
MUT = os.environ.get("AI_MUTANT", "")  # mutate.py: model a plausible bug in the expectations

MUTANTS = {
    "spp_not_cleared": "SRET leaves sstatus.SPP unchanged instead of clearing it",
    "spp_from_u_is_s": "a trap from U-mode records SPP = 1",
    "u_needs_sie": "supervisor interrupts in U-mode are gated by sstatus.SIE",
    "s_ignores_sie": "supervisor interrupts in S-mode ignore sstatus.SIE",
    "sret_keeps_spie": "SRET leaves SPIE unchanged instead of setting it to 1",
    "trap_keeps_sie": "a trap into S-mode leaves SIE unchanged",
    "sstatus_shows_mpie": "sstatus bit 7 shows mstatus.MPIE",
    "sd_ignores_fs": "SD ignores a dirty FS",
    "sstatus_not_mstatus": "an M-mode write of mstatus.SPP is not visible in sstatus",
    "uxl_holds_reserved": "UXL holds the reserved value 3",
    "direct_vectors_interrupts": "Direct mode sends interrupts to BASE+4*cause",
    "vectored_exceptions": "Vectored mode sends exceptions to BASE+4*cause",
    "sti_over_ssi": "STI has priority over SSI",
    "ssi_over_sei": "SSI has priority over SEI",
    "late_evaluation": "an interrupt enabled by a CSR write is taken one instruction late",
    "stip_writable": "S-mode can clear sip.STIP",
    "seip_writable": "S-mode can clear sip.SEIP",
    "ssip_readonly": "sip.SSIP is not writable from S-mode",
    "sip_shows_undelegated": "sip shows an interrupt that mideleg does not delegate",
    "sie_ro_nonzero": "a non-writable sie bit reads 1",
    "scounteren_ignored": "U-mode counter reads ignore scounteren",
    "mcounteren_ignored_in_u": "U-mode counter reads ignore mcounteren",
    "scounteren_64bit": "scounteren holds bits 63:32 on RV64",
    "sepc_bit0_kept": "sepc[0] is writable",
    "sepc_written_by_m_trap": "a trap into M-mode also writes sepc",
    "scause_no_int_bit": "scause.Interrupt is not set for interrupts",
    "scause_4bit_code": "the scause exception code holds only bits 3:0",
    "stval_sign_extended": "illegal-instruction bits are sign-extended into stval",
    "stval_ecall_kept": "an ecall leaves stval unchanged",
    "stval_breakpoint_next": "a breakpoint writes the address of the next instruction into stval",
    "stval_16bit_with_next": "a 16-bit illegal instruction reports 32 bits (with the next parcel) in stval",
    "cbze_ignores_menvcfg": "U-mode CBO.ZERO is enabled by senvcfg.CBZE alone",
    "cbcfe_ignores_senvcfg": "U-mode CBO.CLEAN/FLUSH ignore senvcfg.CBCFE",
    "cbie_ignores_menvcfg": "U-mode CBO.INVAL is enabled by senvcfg.CBIE alone",
    "cbie_10_held": "senvcfg.CBIE holds the reserved value 10",
    "inval_ignores_s_flush": "U-mode CBO.INVAL invalidates (data reverts) when S-mode CBO.INVAL flushes",
    "tsr_ignored": "mstatus.TSR=1 does not trap SRET in S-mode",
    "tsr_traps_m": "mstatus.TSR=1 also traps SRET in M-mode",
    "sret_keeps_mprv": "SRET to S-mode leaves mstatus.MPRV set",
    "ecall_u_cause_9": "an ecall from U-mode reports cause 9",
    "trap_keeps_stval": "a delegated trap leaves stval unchanged",
    "wfi_u_must_complete": "U-mode WFI is expected to complete (it may legally raise illegal-instruction)",
    "wfi_needs_sie": "WFI with sstatus.SIE=0 traps (illegal) instead of resuming",
    "sum_ro0_with_vm": "SUM is read-only zero even when satp.MODE is writable",
    "warl_ro1": "sie bits that are not writable read as 1",
}


def new(
    rule: str, required: list[str] | None = None, pool: list[str] | None = None, boot: str = "S", rv64: bool = False
) -> TestFile:
    return TestFile(SUITE, rule, required=required or REQ, march=MARCH, pool=pool or POOL_TRAP, boot=boot, rv64=rv64)


def new_sm(rule: str, required: list[str] | None = None, pool: list[str] | None = None) -> TestFile:
    return TestFile(
        SUITE, rule, suffix="_Sm", required=(required or REQ) + ["Sm"], march=MARCH, boot="M", pool=pool or POOL_TRAP
    )


def win(
    t: TestFile,
    mode: str,
    lines: list[str],
    expect: Expect,
    desc: str,
    tval: Sequence[Value] | None = None,
    self_tval: bool = False,
    tsbi: bool = False,
    origin: str | None = None,
    pre: list[str] | None = None,
) -> str:
    """Run lines in mode (entered from t.cur with sret/mret, or a T-SBI GOTO when tsbi) inside a trap window and
    check the outcome. The first line is the instruction under test; self_tval adds its address to the legal
    xtval values. pre runs in mode before the label. Returns its label."""
    lab = t.label(f"in_{mode}")
    tv: list[Value] = list(tval or [])
    if self_tval:
        tv.append(lab)
    t.allow(1)
    if mode != t.cur:
        if tsbi:
            t.emit(f"RVTEST_TSBI_GOTO_{mode}MODE", 120)
        else:
            t.enter(mode)
    for ln in pre or []:
        t.emit(ln)
    t.emit(f"{lab}:", 0)
    for ln in lines:
        t.emit(ln)
    if mode != t.cur:
        t.leave()
    t.outcome(expect, lab, f"{desc} in {mode}-mode", tv or None, origin=origin or mode)
    return lab


@contextmanager
def discard(t: TestFile) -> Iterator[None]:
    """Drop everything emitted inside the block (for a section that a split file does not contain)."""
    n = (len(t.code), len(t.table), len(t.strings), t.ninst)
    yield
    del t.code[n[0] :], t.table[n[1] :], t.strings[n[2] :]
    t.ninst = n[3]


def word(e: int, note: str) -> str:
    return f".word {hex(e)}  // {note}"


def logged(t: TestFile, reg: str, w: str) -> None:
    """reg = word w (TRAPLOG_*) of the last logged trap."""
    t.emit(f"AI_LOG({reg}, {w})", 10)


def pred_eq(t: TestFile, dst: str, a: str, b: str) -> None:
    """dst = (a == b)."""
    t.emit(f"xor {dst}, {a}, {b}")
    t.emit(f"seqz {dst}, {dst}")


def sret_to(t: TestFile, mode: str, lab: str, spie: int | None = None) -> None:
    """From S-mode, sret to label lab in mode (S or U), optionally setting SPIE first. Uses x14."""
    t.la("x14", lab)
    t.emit("csrw sepc, x14")
    t.li("x14", SPP)
    t.emit(f"{'csrs' if mode == 'S' else 'csrc'} sstatus, x14")
    if spie is not None:
        t.li("x14", SPIE)
        t.emit(f"{'csrs' if spie else 'csrc'} sstatus, x14")
    t.emit(f"#if {H}", 0)
    t.emit("LI(x14, HSTATUS_SPV)", 2)
    t.emit("csrc CSR_HSTATUS, x14")
    t.emit("#endif", 0)
    t.emit("sret")


def quiet_sie(t: TestFile) -> None:
    t.comment("no supervisor interrupt enabled, sstatus.SIE = 0")
    t.emit("csrw sie, x0")
    L.bits(t, "sstatus", SIE, False)


# ======================================================================== sstatus
def gen_sstatus() -> list[TestFile]:
    tests = []
    SFORMS = [  # (asm, funct3, rd, rs1/uimm, kind); rd x7, rs x6
        ("csrrs x7, sstatus, x0", 2, 7, 0, "read (csrrs rs1=x0)"),
        ("csrrw x0, sstatus, x6", 1, 0, 6, "write (csrrw rd=x0)"),
        ("csrrw x7, sstatus, x6", 1, 7, 6, "swap (csrrw)"),
        ("csrrs x7, sstatus, x6", 2, 7, 6, "set (csrrs)"),
        ("csrrc x7, sstatus, x6", 3, 7, 6, "clear (csrrc)"),
        ("csrrwi x7, sstatus, 0x2", 5, 7, 0x2, "write immediate (csrrwi 0x2)"),
        ("csrrsi x7, sstatus, 0", 6, 7, 0, "read (csrrsi uimm=0)"),
        ("csrrci x7, sstatus, 0x2", 7, 7, 0x2, "clear immediate (csrrci 0x2)"),
    ]

    def sstatus_forms(t: TestFile, m: int, name: str) -> None:
        """Every CSR form on the always-writable bits m of sstatus. Register writes keep the other fields; csrrwi
        clears them, so sstatus is restored from x9 after each form."""
        for asm, f3, rd, src, kind in SFORMS:
            old = t.rng.randrange(0, 8)
            old = sum(b for i, b in enumerate([SIE, SPIE, SPP]) if old >> i & 1) & m
            new = sum(b for b in [SIE, SPIE, SPP] if t.rng.random() < 0.5) & m
            t.comment(f"{kind}: {name} old {hex(old)}, operand {hex(new)}")
            t.emit("csrw sstatus, x9")
            L.bits(t, "sstatus", m, False)
            if old:
                L.bits(t, "sstatus", old, True)
            if f3 == 1:  # csrrw: the operand keeps every other field
                t.emit("csrr x6, sstatus")
                t.li("x8", ~m)
                t.emit("and x6, x6, x8")
                if new:
                    t.li("x8", new)
                    t.emit("or x6, x6, x8")
            elif src == 6:
                t.li("x6", new)
            imm = src if f3 >= 5 else None
            operand = imm if imm is not None else (new if src == 6 else 0)
            res = {1: operand, 5: operand, 2: old | operand, 6: old | operand, 3: old & ~operand, 7: old & ~operand}[f3]
            res &= m
            lab = t.label("form")
            t.emit(f"{lab}:", 0)
            t.emit(asm)
            if rd:
                t.check_masked("x7", m, old, lab, f"{kind} of sstatus returns the old {name}")
            t.emit("csrr x7, sstatus")
            t.emit("csrw sstatus, x9")
            t.check_masked("x7", m, res, lab, f"{kind} of sstatus leaves {name} = {hex(res)}")

    # ---- sstatus ----
    t = new("sstatus", pool=POOL_TRAP)
    t.describe(
        source=SUP,
        rule_text="The sstatus register is an SXLEN-bit read/write register formatted as shown in "
        "<<sstatusreg-rv32>> when SXLEN=32 and <<sstatusreg>> when SXLEN=64. The sstatus register keeps track of "
        "the processor's current operating state.",
        context="Fields: SIE(1), SPIE(5), UBE(6), SPP(8), VS(10:9), FS(14:13), XS(16:15), SUM(18), MXR(19), "
        "SPELP(23), SDT(24), UXL(33:32, SXLEN=64) and SD(SXLEN-1); every other bit is WPRI. WPRI fields that an "
        "implementation does not furnish are read-only zero (csrs.adoc). machine.adoc: SIE and SPIE must be "
        "writable when S-mode exists (mstatus_sie_spie_rdonly0); FS shall not be read-only zero with F "
        "(mstatus_fs_acc1) and VS not with V (mstatus_vs_acc1); FS may track only Off and Dirty, so Initial or "
        "Clean may read back as Dirty (mstatus_fs_no_dirty_track); XS is read-only (mstatus_fs_vs_warl); "
        "SD = (FS==3 || VS==3 || XS==3) and is read-only (mstatus_sd_formula).",
        plan="1. Every CSR instruction form on SIE, SPIE and SPP (always writable) returns the old bits and leaves "
        "the bits the form defines; register-form writes carry the other fields unchanged, and sstatus is "
        "restored after each form.\n"
        "2. Writing ones to every WPRI bit (keeping the other fields) leaves them reading 0. SPELP and SDT are "
        "never written (they belong to Zicfilp and Ssdbltrp).\n"
        "3. With F: FS written 0 reads 0, written 3 reads 3, written 1 or 2 reads that value or 3. With V (or "
        "Zve*): the same for VS.\n"
        "4. XS is read-only: it reads the same after writes of 3 and 0.\n"
        "5. SD equals (FS==3 || VS==3 || XS==3) after each FS/VS write (with the other of FS/VS cleared, so each "
        "field alone drives SD), and writing 1 to SD with FS=VS=0 does not change it.",
    )
    quiet_sie(t)
    t.emit("csrr x9, sstatus  // original value, restored after each step")
    sstatus_forms(t, SIE | SPIE | SPP, "SIE/SPIE/SPP")
    t.comment("WPRI bits read zero")
    t.emit("csrr x6, sstatus")
    t.load("x7", WPRI, "WPRI bits")
    t.emit("or x6, x6, x7")
    lab = t.label("wpri")
    t.emit(f"{lab}:", 0)
    t.emit("csrw sstatus, x6")
    t.emit("csrr x7, sstatus")
    t.emit("csrw sstatus, x9")
    t.check_masked("x7", WPRI, 0, lab, "WPRI bits of sstatus read 0 after writing ones")

    def sd_check(note: str) -> None:
        """SD == (FS==3 || VS==3 || XS==3) for the current sstatus (x1 = any dirty, x7 = predicate)."""
        lab = t.label("sd")
        t.emit(f"{lab}:", 0)
        t.emit("csrr x6, sstatus")
        t.emit("li x1, 0")
        for shift, nm in ((13, "FS"), (9, "VS"), (15, "XS")):
            if MUT == "sd_ignores_fs" and nm == "FS":
                continue
            t.emit(f"srli x8, x6, {shift}")
            t.emit("andi x8, x8, 3")
            t.emit("addi x8, x8, -3")
            t.emit("seqz x8, x8")
            t.emit("or x1, x1, x8")
        t.emit("sltz x7, x6  // SD")
        pred_eq(t, "x7", "x7", "x1")
        t.check_bool("x7", lab, f"SD == (FS==3 || VS==3 || XS==3) {note}")

    def field_cases(field: int, shift: int, name: str, other: int) -> None:
        L.bits(t, "sstatus", other, False)  # isolate this field's contribution to SD
        for v in (0, 3, 1, 2, 0):
            t.comment(f"{name} = {v}")
            L.bits(t, "sstatus", field, False)
            if v:
                L.bits(t, "sstatus", v << shift, True)
            lab = t.label(name.lower())
            t.emit(f"{lab}:", 0)
            t.emit("csrr x7, sstatus")
            exp = [v << shift] if v in (0, 3) else [v << shift, 3 << shift]
            t.check_masked("x7", field, exp, lab, f"{name} written {v} reads a legal value")
            sd_check(f"after writing {name}={v}")

    with t.only_if("defined(F_SUPPORTED)"):
        field_cases(FS, 13, "FS", VS)
    with t.only_if("defined(V_SUPPORTED) || defined(ZVE32X_SUPPORTED)"):
        field_cases(VS, 9, "VS", FS)
    t.emit("csrw sstatus, x9")
    t.comment("XS is read-only")
    L.bits(t, "sstatus", XS, True)
    t.emit("csrr x7, sstatus")
    L.bits(t, "sstatus", XS, False)
    t.emit("csrr x8, sstatus")
    t.emit("xor x7, x7, x8")
    lab = t.label("xs")
    t.emit(f"{lab}:", 0)
    t.check_masked("x7", XS, 0, lab, "XS reads the same after writing 3 and 0 (read-only)")
    t.comment("SD is read-only: write 1 with FS=VS=0")
    L.bits(t, "sstatus", FS | VS, False)
    t.load("x6", SD, "SD")
    t.emit("csrs sstatus, x6")
    sd_check("after writing SD=1 with FS=VS=0")
    t.emit("csrw sstatus, x9")
    tests.append(t)

    # ---- mstatus_sie_spie_rdonly0 ----
    t = new("mstatus_sie_spie_rdonly0")
    t.describe(
        source=MAC,
        rule_text="mie and mpie must be writable. If supervisor mode is not implemented, then sie and spie are "
        "read-only 0; otherwise, they must be writable.",
        context="This S suite covers the S-mode part: with S-mode implemented, mstatus.SIE and mstatus.SPIE must "
        "be writable. They are reached as sstatus.SIE/SPIE from S-mode and as mstatus.SIE/SPIE from M-mode "
        "(T-SBI). mie/mpie are M-only.",
        plan="1. Every CSR instruction form on sstatus SIE and SPIE (with sie = 0, so no interrupt can be taken) "
        "returns the old bits and leaves the defined bits.\n"
        "2. M-mode (T-SBI) sets and clears mstatus.SIE and mstatus.SPIE; sstatus shows each value.",
    )
    quiet_sie(t)
    t.emit("csrr x9, sstatus")
    sstatus_forms(t, SIE | SPIE, "SIE/SPIE")
    for b, nm in ((SIE, "SIE"), (SPIE, "SPIE")):
        for on in (True, False, True, False):
            L.m_bits(t, "mstatus", b, on)
            lab = t.label("m")
            t.emit(f"{lab}:", 0)
            t.emit("csrr x7, sstatus")
            t.check_masked("x7", b, b if on else 0, lab, f"sstatus.{nm} after M-mode {'set' if on else 'clear'}")
    t.emit("csrw sstatus, x9")
    tests.append(t)

    # ---- sstatus_spp ----
    t = new("sstatus_spp")
    t.describe(
        source=SUP,
        rule_text="The SPP bit indicates the privilege level at which a hart was executing before entering "
        "supervisor mode. When a trap is taken, SPP is set to 0 if the trap originated from user mode, or 1 "
        "otherwise. When an SRET instruction is executed to return from the trap handler, the privilege level "
        "is set to user mode if the SPP bit is 0, or supervisor mode if the SPP bit is 1; SPP is then set to 0.",
        context="EBREAK traps are delegated to S-mode (medeleg[3]), so they are taken into S from S and U. The trap "
        "log records sstatus at handler entry; the window checks SPP through it (the mode the trap came from).",
        plan="Before each trap SPP is preset to the opposite of its expected value.\n"
        "1. From S-mode with SPP=0: EBREAK traps with SPP=1 (also with SPP preset 1).\n"
        "2. From U-mode entered by SRET (which leaves SPP=0) and from U-mode entered through T-SBI with SPP preset "
        "to 1: EBREAK traps with SPP=0.\n"
        "3. SRET with SPP=1 lands at sepc in S-mode: a read of sstatus does not trap there, and SPP reads 0.\n"
        "4. SRET with SPP=0 lands at sepc in U-mode: the same read of sstatus raises illegal-instruction from U.",
    )
    quiet_sie(t)
    for pre in (0, 1):
        L.bits(t, "sstatus", SPP, bool(pre))
        win(t, "S", ["ebreak"], L.BREAKPOINT, f"EBREAK with SPP preset {pre}", [0], self_tval=True)
        logged(t, "x15", "TRAPLOG_STATUS")
        lab = t.label("spp")
        t.emit(f"{lab}:", 0)
        t.check_masked("x15", SPP, SPP, lab, f"logged SPP after a trap from S-mode (SPP preset {pre})")
    win(
        t,
        "U",
        ["ebreak"],
        L.BREAKPOINT,
        "EBREAK (entered by SRET)",
        [0],
        self_tval=True,
        origin="S" if MUT == "spp_from_u_is_s" else None,
    )
    L.bits(t, "sstatus", SPP, True)
    win(
        t,
        "U",
        ["ebreak"],
        L.BREAKPOINT,
        "EBREAK (entered through T-SBI with SPP preset 1)",
        [0],
        self_tval=True,
        tsbi=True,
        origin="S" if MUT == "spp_from_u_is_s" else None,
    )
    t.comment("SRET with SPP=1 returns to S-mode and clears SPP")
    lab = t.label("srets")
    t.allow(1)
    sret_to(t, "S", lab)
    t.emit(f"{lab}:", 0)
    t.emit("csrr x7, sstatus")
    t.outcome("ok", lab, "read of sstatus after SRET with SPP=1 (must be in S-mode)")
    t.check_masked("x7", SPP, SPP if MUT == "spp_not_cleared" else 0, lab, "SPP after SRET with SPP=1")
    t.comment("SRET with SPP=0 returns to U-mode")
    lab = t.label("sretu")
    t.allow(1)
    sret_to(t, "U", lab)
    t.emit(f"{lab}:", 0)
    t.emit("csrr x7, sstatus")
    t.leave()
    t.outcome(
        ILLEGAL,
        lab,
        "read of sstatus after SRET with SPP=0 (must be in U-mode)",
        [0, L.enc_csr(0x100, 2, 7, 0)],
        origin="U",
    )
    tests.append(t)
    return tests


# ======================================================================== sstatus: interrupts and the stack
def interrupt_sweep(t: TestFile, src: str, cases: list[tuple[str, int, int, int]], what: str) -> None:
    """int_window for each (mode, SIE, enable, pending) case of interrupt src."""
    code = SRC[src]
    for mode, sie, en, pend in cases:
        u_ok = MUT != "u_needs_sie"
        s_ok = bool(sie) or MUT == "s_ignores_sie"
        taken = pend and en and (s_ok if mode == "S" else (sie or u_ok))
        L.int_window(
            t,
            [src],
            mode,
            sie,
            en,
            pend,
            icause(code) if taken else "ok",
            f"{what}: {src} in {mode}-mode, SIE={sie}, sie bit={en}, pending={pend}",
        )


def gen_sstatus_int() -> list[TestFile]:
    tests = []

    # ---- sstatus_sie ----
    t = new("sstatus_sie", pool=POOL_INT)
    t.describe(
        source=SUP,
        rule_text="The SIE bit enables or disables all interrupts in supervisor mode. When SIE is clear, interrupts "
        "are not taken while in supervisor mode. When the hart is running in user-mode, the value in SIE is "
        "ignored, and supervisor-level interrupts are enabled. The supervisor can disable individual interrupt "
        "sources using the sie CSR.",
        context="SSI, STI and SEI are delegated to S-mode by the framework (mideleg). Each implemented interrupt "
        "(its sie bit is writable, sie_acc) is used: SSI through sip.SSIP, STI through M-mode mip.STIP and SEI "
        "through the platform or M-mode mip.SEIP. The framework handler masks the taken interrupt in sie.",
        plan="For each implemented S-level interrupt, pending unless stated, in a trap window over a 50-iteration "
        "loop:\n"
        "1. S-mode: SIE=0 with the sie bit set: not taken; SIE=1: taken (SIE is set inside the window, so a held "
        "pending interrupt is taken when SIE is set); SIE=1 with the sie bit clear: not taken; SIE=1, not "
        "pending: not taken; SIE=0, sie bit clear: not taken.\n"
        "2. U-mode: SIE=0 and SIE=1 with the sie bit set: taken (SIE ignored); sie bit clear: not taken.\n"
        "STI and SEI run the S-mode SIE=0/SIE=1 cases and the U-mode SIE=0 case; SSI runs all of them.",
    )
    quiet_sie(t)
    cases = [
        ("S", 0, 1, 1),
        ("S", 1, 1, 1),
        ("S", 1, 0, 1),
        ("S", 1, 1, 0),
        ("S", 0, 0, 1),
        ("U", 0, 1, 1),
        ("U", 1, 1, 1),
        ("U", 0, 0, 1),
    ]
    short = [("S", 0, 1, 1), ("S", 1, 1, 1), ("U", 0, 1, 1)]
    for src in SRC:
        L.with_src(t, src, lambda src=src: interrupt_sweep(t, src, cases if src == "SSI" else short, "sstatus.SIE"))
    tests.append(t)

    # ---- mstatus_mie_sie_op ----
    t = new("mstatus_mie_sie_op", pool=POOL_INT)
    t.describe(
        source=MAC,
        rule_text="When a hart is executing in privilege mode x, interrupts are globally enabled when xIE=1 and "
        "globally disabled when xIE=0.",
        context="This S suite covers x = S: in S-mode, S-level interrupts are taken only when sstatus.SIE=1. The "
        "M-mode part (MIE) belongs to a machine-mode suite.",
        plan="For each implemented S-level interrupt, pending and enabled in sie: in S-mode with SIE=0 it is not "
        "taken; setting SIE=1 takes it; with SIE=1 and the interrupt not pending, nothing is taken.",
    )
    quiet_sie(t)
    for src in SRC:
        L.with_src(
            t,
            src,
            lambda src=src: interrupt_sweep(t, src, [("S", 0, 1, 1), ("S", 1, 1, 1), ("S", 1, 1, 0)], "global enable"),
        )
    tests.append(t)

    # ---- sstatus_spie ----
    t = new("sstatus_spie")
    t.describe(
        source=SUP,
        rule_text="The SPIE bit indicates whether supervisor interrupts were enabled prior to trapping into "
        "supervisor mode. When a trap is taken into supervisor mode, SPIE is set to SIE, and SIE is set to 0. "
        "When an SRET instruction is executed, SIE is set to SPIE, then SPIE is set to 1.",
        context="sie = 0 throughout, so setting SIE cannot cause an interrupt. The trap log records sstatus at "
        "handler entry. The framework handler returns with SRET.",
        plan="1. EBREAK from S-mode with SIE=0 and 1 (SPIE preset to the opposite): the logged sstatus has "
        "SPIE = old SIE and SIE = 0; after the handler's SRET, SIE = old SIE and SPIE = 1.\n"
        "2. EBREAK from U-mode entered with SIE=0 and 1 (SRET copies SPIE into SIE): the logged SPIE is U-mode's "
        "SIE, and SIE is 0.\n"
        "3. SRET to S-mode for the four (SPIE, SIE) pairs: afterwards SIE = old SPIE and SPIE = 1.",
    )
    quiet_sie(t)
    for old in (0, 1):
        L.bits(t, "sstatus", SIE, bool(old))
        L.bits(t, "sstatus", SPIE, not old)
        lab = win(t, "S", ["ebreak"], L.BREAKPOINT, f"EBREAK with SIE={old}", [0], self_tval=True)
        logged(t, "x15", "TRAPLOG_STATUS")
        exp_sie = SIE * old if MUT == "trap_keeps_sie" else 0
        t.check_masked(
            "x15", SIE | SPIE, (SPIE if old else 0) | exp_sie, lab, f"logged SPIE = old SIE ({old}) and SIE = 0"
        )
        t.emit("csrr x7, sstatus")
        t.check_masked(
            "x7", SIE | SPIE, (SIE if old else 0) | SPIE, lab, f"after the handler's SRET: SIE = {old}, SPIE = 1"
        )
        L.bits(t, "sstatus", SIE, False)
    for u in (0, 1):
        L.bits(t, "sstatus", SPIE, bool(u))
        L.bits(t, "sstatus", SIE, not u)
        lab = win(t, "U", ["ebreak"], L.BREAKPOINT, f"EBREAK from U-mode with SIE={u}", [0], self_tval=True)
        logged(t, "x15", "TRAPLOG_STATUS")
        t.check_masked("x15", SIE | SPIE, SPIE if u else 0, lab, f"logged SPIE = U-mode SIE ({u}) and SIE = 0")
        L.bits(t, "sstatus", SIE, False)
    for spie in (0, 1):
        for sie in (0, 1):
            t.comment(f"SRET with SPIE={spie}, SIE={sie}")
            L.bits(t, "sstatus", SIE, bool(sie))
            lab = t.label("sret")
            t.allow(1)
            sret_to(t, "S", lab, spie=spie)
            t.emit(f"{lab}:", 0)
            t.emit("csrr x7, sstatus")
            t.outcome("ok", lab, f"SRET with SPIE={spie}, SIE={sie}")
            exp = (SIE if spie else 0) | (SPIE if spie or MUT != "sret_keeps_spie" else 0)
            t.check_masked("x7", SIE | SPIE, exp, lab, f"after SRET with SPIE={spie}: SIE = {spie}, SPIE = 1")
            L.bits(t, "sstatus", SIE, False)
    tests.append(t)

    # ---- trap_del_s_mode_op ----
    t = new("trap_del_s_mode_op", pool=POOL_INT)
    t.describe(
        source=MAC,
        rule_text="When a trap is delegated to S-mode, the scause register is written with the trap cause; the sepc "
        "register is written with the virtual address of the instruction that took the trap; the stval register "
        "is written with an exception-specific datum; the spp field of mstatus is written with the active "
        "privilege mode at the time of the trap; the spie field of mstatus is written with the value of the sie "
        "field at the time of the trap; and the sie field of mstatus is cleared.",
        context="The framework delegates breakpoints (3), ecalls from U (8) and SSI/STI/SEI to S-mode. stval is "
        "0 or the instruction address for EBREAK (stval_op_breakpoint) and 0 for ECALL and interrupts "
        "(stval_op_other_traps). U-mode is entered through T-SBI so SPP can be preset to 1 (SRET would clear it); "
        "T-SBI's MRET leaves sstatus.SIE as S-mode set it.",
        plan="Before each trap: scause, sepc and stval hold other values, SPP is the opposite of the expected "
        "value, SIE=1 and SPIE=0 (sie = 0, so no interrupt is taken because of SIE).\n"
        "1. EBREAK from S and from U: cause 3, sepc = the EBREAK, stval 0 or the EBREAK address, SPP = 1 (S) or 0 "
        "(U), SPIE = 1, SIE = 0 (from the logged sstatus).\n"
        "2. ECALL from U (a T-SBI ECALL_TEST call): cause 8, sepc = the ECALL, stval 0, SPP 0, SPIE 1, SIE 0.\n"
        "3. For each implemented S-level interrupt taken in U-mode (entered with SIE=0 and SPIE preset 1, since "
        "SIE=1 would take it in S-mode): interrupt cause, stval 0, SPP 0, SPIE 0, SIE 0. Taken in S-mode (SPP preset 0, "
        "SPIE 0, SIE set in the window): SPP 1, SPIE 1, SIE 0.",
    )
    quiet_sie(t)

    def preset(spp: int, sie: int = 1) -> None:
        t.comment(f"preset: scause=13, sepc and stval junk, SPP={spp}, SIE={sie}, SPIE={1 - sie}")
        t.li("x6", 13)
        t.emit("csrw scause, x6")
        t.la("x6", "rvtest_data_begin")
        t.emit("csrw sepc, x6")
        t.emit("csrw stval, x6")
        L.bits(t, "sstatus", SPP, bool(spp))
        L.bits(t, "sstatus", SPIE, not sie)
        L.bits(t, "sstatus", SIE, bool(sie))

    def status_check(lab: str, spp: int, desc: str, spie: int = 1) -> None:
        logged(t, "x15", "TRAPLOG_STATUS")
        t.check_masked(
            "x15",
            SPP | SPIE | SIE,
            (SPP if spp else 0) | (SPIE if spie else 0),
            lab,
            f"{desc}: SPP={spp}, SPIE={spie}, SIE=0",
        )
        L.bits(t, "sstatus", SIE, False)

    preset(0)
    lab = win(t, "S", ["ebreak"], L.BREAKPOINT, "EBREAK", [0], self_tval=True)
    status_check(lab, 1, "EBREAK from S")
    preset(1)
    lab = win(t, "U", ["ebreak"], L.BREAKPOINT, "EBREAK", [0], self_tval=True, tsbi=True)
    status_check(lab, 0, "EBREAK from U")
    preset(1)
    lab = win(
        t,
        "U",
        ["ecall  // T-SBI ECALL_TEST"],
        L.ECALL_U,
        "ECALL",
        ["rvtest_data_begin"] if MUT == "trap_keeps_stval" else [0],
        tsbi=True,
        pre=["li a0, 0x73"],
    )
    status_check(lab, 0, "ECALL from U")

    def int_from_u(src: str) -> None:
        bit = 1 << SRC[src]
        preset(1, sie=0)  # SIE=1 would take the interrupt in S-mode
        L.bits(t, "sie", bit, True)
        L.raise_int(t, src)
        lab = t.label("intu")
        t.allow(1)
        t.emit("RVTEST_TSBI_GOTO_UMODE", 120)
        t.emit(f"{lab}:", 0)
        L.delay(t)
        t.leave()
        L.bits(t, "sie", bit, False)
        t.outcome(icause(SRC[src]), lab, f"{src} taken from U-mode", [0], epc=False, origin="U")
        status_check(lab, 0, f"{src} from U", spie=0)
        L.lower_int(t, src)

    def int_from_s(src: str) -> None:
        bit = 1 << SRC[src]
        preset(0, sie=0)  # SPIE preset 1; SIE is set inside the window
        L.bits(t, "sie", bit, True)
        L.raise_int(t, src)
        L.bits(t, "sstatus", SPIE, False)
        lab = t.label("ints")
        t.li("x6", SIE)
        t.allow(1)
        t.emit(f"{lab}:", 0)
        t.emit("csrs sstatus, x6")
        L.delay(t)
        L.bits(t, "sie", bit, False)
        t.outcome(icause(SRC[src]), lab, f"{src} taken from S-mode", [0], epc=False, origin="S")
        status_check(lab, 1, f"{src} from S")
        L.lower_int(t, src)

    for src in SRC:
        L.with_src(t, src, lambda src=src: int_from_u(src))
        L.with_src(t, src, lambda src=src: int_from_s(src))
    tests.append(t)
    return tests


def uxl_set(t: TestFile, v: int) -> None:
    t.comment(f"sstatus.UXL = {v}")
    t.li("x6", 3)
    t.emit("slli x6, x6, 32")
    t.emit("csrc sstatus, x6")
    t.li("x6", v)
    t.emit("slli x6, x6, 32")
    t.emit("csrs sstatus, x6")


def uxl32_probe(t: TestFile) -> None:
    """x7 = 1 if UXL holds 1 (UXLEN=32 supported); UXL is left at 1 in that case and 2 otherwise."""
    uxl_set(t, 1)
    t.emit("csrr x7, sstatus")
    t.emit("srli x7, x7, 32")
    t.emit("andi x7, x7, 3")
    t.emit("addi x7, x7, -1")
    t.emit("seqz x7, x7")


def uop(t: TestFile, a: int, b: int, lines: list[str], exp: Value, desc: str, mode_note: str) -> None:
    t.load("x6", a, "operand rs1")
    t.load("x7", b, "operand rs2")
    t.li("x8", 0x5A5)
    lab = win(t, "U", lines, "ok", f"{lines[0]} ({mode_note})")
    t.check("x8", exp, lab, desc)


# ======================================================================== sstatus: mstatus view, UXL, UBE, SUM
def gen_sstatus_view() -> list[TestFile]:
    tests = []
    MXR, SUM = L.MXR, L.SUM

    # ---- sstatus_subset_mstatus ----
    t = new("sstatus_subset_mstatus")
    t.describe(
        source=SUP,
        rule_text="The sstatus register is a subset of the mstatus register.",
        context="Note: in a straightforward implementation, reading or writing any field in sstatus is equivalent "
        "to reading or writing the homonymous field in mstatus. machine.adoc: a restricted view of mstatus "
        "appears as sstatus. The sstatus fields are SIE, SPIE, UBE, SPP, VS, FS, XS, SUM, MXR, SPELP, SDT, UXL and "
        "SD; the M-only fields (MIE, MPIE, MPP, MPRV, TVM, TW, TSR, ...) sit at WPRI positions of sstatus. "
        "mstatus is read and written through T-SBI (M-mode). An MRET (the T-SBI return) sets mstatus.MPIE=1 and "
        "MPP to the least-privileged mode, so after any T-SBI call mstatus.MPIE is 1.",
        plan="1. For SIE, SPIE, SPP, SUM, MXR, UBE, FS and VS, set then clear the field in sstatus: the M-mode read "
        "of mstatus shows the same field value as sstatus (SIE, SPIE and SPP must follow the write). On RV64 "
        "UXL agrees too. sie = 0, so SIE=1 takes no interrupt.\n"
        "2. M-mode sets and clears mstatus.SPP, SPIE and SUM: sstatus shows the M-mode value.\n"
        "3. M-only fields stay invisible: with mstatus.TW set by M-mode and mstatus.MPIE = 1, sstatus bits 7 "
        "(MPIE), 11-12 (MPP) and 21 (TW) read 0.\n"
        "4. Writing ones to every WPRI bit of sstatus leaves mstatus.MPRV, TVM, TW and TSR unchanged (0).",
    )
    quiet_sie(t)
    t.emit("csrr x9, sstatus")
    fields = [
        (SIE, "SIE", True),
        (SPIE, "SPIE", True),
        (SPP, "SPP", True),
        (SUM, "SUM", False),
        (MXR, "MXR", False),
        (UBE, "UBE", False),
        (FS, "FS", False),
        (VS, "VS", False),
    ]
    for f, nm, must in fields:
        for on in (True, False):
            L.bits(t, "sstatus", f, on)
            lab = t.label(nm.lower())
            t.emit(f"{lab}:", 0)
            t.emit("csrr x7, sstatus")
            if must:
                t.check_masked("x7", f, f if on else 0, lab, f"sstatus.{nm} after an S-mode {'set' if on else 'clear'}")
            t.tsbi_csr("READ", "MSTATUS")
            t.emit("xor x7, x7, a0")
            t.check_masked(
                "x7",
                f,
                0,
                lab,
                f"mstatus.{nm} (M-mode read) equals sstatus.{nm} after an S-mode {'set' if on else 'clear'}",
            )
    with t.rv64_only():
        lab = t.label("uxl")
        t.emit(f"{lab}:", 0)
        t.emit("csrr x7, sstatus")
        t.tsbi_csr("READ", "MSTATUS")
        t.emit("xor x7, x7, a0")
        t.check_masked("x7", L.UXL, 0, lab, "mstatus.UXL equals sstatus.UXL")
    for f, nm in ((SPP, "SPP"), (SPIE, "SPIE"), (SUM, "SUM")):
        for on in (True, False):
            L.m_bits(t, "mstatus", f, on)
            lab = t.label(f"m{nm.lower()}")
            t.emit(f"{lab}:", 0)
            t.emit("csrr x7, sstatus")
            if nm == "SUM":
                t.tsbi_csr("READ", "MSTATUS")
                t.emit("xor x7, x7, a0")
                t.check_masked(
                    "x7", f, 0, lab, f"sstatus.SUM equals mstatus.SUM after an M-mode {'set' if on else 'clear'}"
                )
            else:
                exp = 0 if (MUT == "sstatus_not_mstatus" and nm == "SPP") else (f if on else 0)
                t.check_masked("x7", f, exp, lab, f"sstatus.{nm} after an M-mode {'set' if on else 'clear'}")
    t.emit("csrw sstatus, x9")
    L.m_bits(t, "mstatus", L.TW, True)
    lab = t.label("monly")
    t.emit(f"{lab}:", 0)
    t.tsbi_csr("READ", "MSTATUS")
    t.emit("mv x8, a0")
    t.emit("csrr x7, sstatus")
    L.m_bits(t, "mstatus", L.TW, False)
    t.comment("x8 = mstatus (M-mode view, read during the T-SBI call: MPP = S there); x7 = sstatus")
    t.emit("srli x8, x8, 21")
    t.emit("andi x8, x8, 1")
    t.comment("TW is WARL: compare sstatus bit 21 with 0 whatever mstatus.TW holds")
    exp7 = L.MPIE if MUT == "sstatus_shows_mpie" else 0
    t.check_masked(
        "x7",
        L.MPIE | L.MPP | L.TW,
        exp7,
        lab,
        "sstatus bits 7 (MPIE=1), 12:11 (MPP) and 21 (TW) read 0 while mstatus.TW was set",
    )
    t.comment("sstatus WPRI writes do not reach mstatus.MPRV/TVM/TW/TSR")
    t.emit("csrr x6, sstatus")
    t.load("x7", WPRI, "WPRI bits")
    t.emit("or x6, x6, x7")
    t.emit("csrw sstatus, x6")
    t.emit("csrw sstatus, x9")
    lab = t.label("wpri")
    t.emit(f"{lab}:", 0)
    t.tsbi_csr("READ", "MSTATUS")
    t.check_masked(
        "a0",
        L.MPRV | L.TVM | L.TW | L.TSR,
        0,
        lab,
        "mstatus.MPRV/TVM/TW/TSR unchanged (0) after writing ones to sstatus WPRI bits",
    )
    tests.append(t)

    # ---- sstatus_uxl_sz ----
    t = new("sstatus_uxl_sz", rv64=True)
    t.describe(
        source=SUP,
        rule_text="When SXLEN=32, the UXL field does not exist, and UXLEN=32. When SXLEN=64, it is a WARL field "
        "that encodes the current value of UXLEN. In particular, an implementation may make UXL be a read-only "
        "field whose value always ensures that UXLEN=SXLEN.",
        context="UXL is sstatus[33:32], encoded like misa.MXL: 1 = 32, 2 = 64, 3 = 128 (reserved for RV128). "
        "machine.adoc: a read-only UXL ensures UXLEN=MXLEN or SXLEN, and its legal values exclude UXLEN > SXLEN "
        "(mstatus_uxl_legal_vals_smode). So with SXLEN=64 the legal values are 1 and 2, and 2 is always legal "
        "(a writable UXL has at least two legal values). The RV32 part (no UXL field) is not observable beyond "
        "the absent bits, so the file passes trivially on RV32.",
        plan="RV64 only. Write UXL = 0, 3, 1 and 2 (keeping the other fields): each read is 1 or 2, and writing 2 "
        "reads 2. UXL is left at 2.",
    )
    for v in (0, 3, 1, 2):
        lab = t.label("uxl")
        t.li("x6", 3)
        t.emit("slli x6, x6, 32")
        t.emit("csrc sstatus, x6")
        if v:
            t.li("x6", v)
            t.emit("slli x6, x6, 32")
            t.emit(f"{lab}:", 0)
            t.emit("csrs sstatus, x6")
        else:
            t.emit(f"{lab}:", 0)
        t.emit("csrr x7, sstatus")
        t.emit("srli x7, x7, 32")
        t.emit("andi x7, x7, 3")
        exp: Expect = [2] if v == 2 else [1, 2]
        if MUT == "uxl_holds_reserved" and v == 3:
            exp = [3]
        t.check("x7", exp, lab, f"UXL written {v} reads a legal value")
    tests.append(t)

    t = new("sstatus_uxl", rv64=True)
    t.describe(
        source=SUP,
        rule_text="The UXL field controls the value of XLEN for U-mode, termed UXLEN, which may differ from the "
        "value of XLEN for S-mode, termed SXLEN. The encoding of UXL is the same as that of the MXL field of "
        "misa, shown in <<norm:misa_mxl_enc>>.",
        context="MXL encoding: 1 = 32, 2 = 64. With UXLEN=32, RV64-only instructions such as ADDW are reserved in "
        "U-mode, and results are sign-extended from bit 31 (sstatus_uxl_behavior).",
        plan="RV64 only.\n"
        "1. UXL = 2 (UXLEN=64): in U-mode, ADD of 0xFFFFFFFF + 1 gives 0x1_00000000 and ADDW executes (0).\n"
        "2. If UXL holds 1 (UXLEN=32 supported): in U-mode the same ADD gives 0 (32-bit sum, sign-extended) and "
        "ADDW raises illegal-instruction. UXL is restored to 2.",
    )
    uxl_set(t, 2)
    uop(t, 0xFFFFFFFF, 1, ["add x8, x6, x7"], X(0, 1 << 32), "UXL=2: U-mode ADD is 64-bit", "UXL=2")
    uop(t, 0xFFFFFFFF, 1, ["addw x8, x6, x7"], 0, "UXL=2: U-mode ADDW executes", "UXL=2")
    uxl32_probe(t)

    def u32() -> None:
        uop(t, 0xFFFFFFFF, 1, ["add x8, x6, x7"], 0, "UXL=1: U-mode ADD is 32-bit and sign-extended", "UXL=1")
        win(
            t,
            "U",
            ["addw x8, x6, x7"],
            ILLEGAL,
            "ADDW with UXL=1 is reserved",
            [0, (7 << 20) | (6 << 15) | (8 << 7) | 0x3B],
        )

    t.either("x7", u32, lambda: t.comment("UXL is fixed at 2: UXLEN=32 is not supported"))
    uxl_set(t, 2)
    tests.append(t)
    return tests


def gen_uxl32() -> list[TestFile]:
    tests = []
    U32_CTX = (
        "Tests run with SXLEN=64. UXL is first written to 1; if it reads back 1 (UXLEN=32 is supported) the "
        "U-mode cases run, otherwise UXL is fixed at 2 and nothing is observable. Operands are loaded in "
        "S-mode with bits 63:32 set to other values, and results are read back in S-mode."
    )

    # ---- sstatus_uxl_behavior ----
    t = new("sstatus_uxl_behavior", rv64=True)
    t.describe(
        source=SUP,
        rule_text="If UXLEN≠SXLEN, instructions executed in the narrower mode must ignore source register operand "
        "bits above the configured XLEN, and must sign-extend results to fill the widest supported XLEN in the "
        "destination register.",
        context=U32_CTX,
        plan="RV64 only, when UXL can be 1. In U-mode with UXLEN=32:\n"
        "1. ADD, ADDI, SLLI and SRAI results with bit 31 set are sign-extended (0xFFFFFFFF80000000 and "
        "0xFFFFFFFFF8000000); ADDI x8, x8, 0 (not a HINT) sign-extends too.\n"
        "2. Upper source bits are ignored: SLT/SLTU/SLTIU compare the low 32 bits (results that differ from a "
        "64-bit compare), SRL/SRA shift the low 32 bits, SLL uses a 5-bit shift amount (33 shifts by 1), and BEQ "
        "on operands equal in bits 31:0 is taken.\n"
        "3. JAL writes the sign-extended 32-bit return address.\n"
        "UXL is restored to 2.",
    )
    uxl32_probe(t)
    M = (1 << 64) - 1

    def body() -> None:
        cases = [
            (0xDEADBEEF7FFFFFFF, 0x1234567800000001, ["add x8, x6, x7"], 0xFFFFFFFF80000000, "ADD sign-extends"),
            (0x000000017FFFFFFF, 0, ["addi x8, x6, 1"], 0xFFFFFFFF80000000, "ADDI ignores bit 32 and sign-extends"),
            (0x0000000040000000, 0, ["slli x8, x6, 1"], 0xFFFFFFFF80000000, "SLLI sign-extends"),
            (0x0000000080000000, 0, ["srai x8, x6, 4"], 0xFFFFFFFFF8000000, "SRAI shifts the 32-bit value"),
            (0xFFFFFFFF80000000, 0, ["srli x8, x6, 4"], 0x08000000, "SRLI shifts the 32-bit value"),
            (0x0000000080000000, 0xFFFFFFFF00000001, ["slt x8, x6, x7"], 1, "SLT compares bits 31:0 as signed"),
            (0xFFFFFFFF00000001, 0x0000000000000002, ["sltu x8, x6, x7"], 1, "SLTU compares bits 31:0"),
            (0xFFFFFFFF00000003, 0, ["sltiu x8, x6, 5"], 1, "SLTIU compares bits 31:0"),
            (0x1234567880000000, 0xFFFFFFFF00000004, ["srl x8, x6, x7"], 0x08000000, "SRL shifts bits 31:0"),
            (0x1234567880000000, 0xFFFFFFFF00000004, ["sra x8, x6, x7"], 0xFFFFFFFFF8000000, "SRA shifts bits 31:0"),
            (0xABCDEF0000000001, 0x21, ["sll x8, x6, x7"], 2, "SLL uses a 5-bit shift amount"),
        ]
        for a, b, lines, exp, desc in cases:
            uop(t, a, b, lines, X(0, exp & M), desc, "UXL=1")
        t.load("x8", X(0, 0x1234567880000000), "x8")
        lab = win(t, "U", ["addi x8, x8, 0"], "ok", "ADDI x8, x8, 0 (UXL=1)")
        t.check("x8", X(0, 0xFFFFFFFF80000000), lab, "ADDI x8, x8, 0 (not a HINT) sign-extends")
        t.load("x6", X(0, 0x1111111100000005), "rs1")
        t.load("x7", X(0, 0x2222222200000005), "rs2")
        t.li("x8", 0x5A5)
        tk = t.label("taken")
        lab = win(t, "U", [f"beq x6, x7, {tk}", "addi x8, x0, 1", f"{tk}:"], "ok", "BEQ (UXL=1)")
        t.check("x8", 0x5A5, lab, "BEQ compares bits 31:0 (taken)")
        rl = t.label("ret")
        lab = win(t, "U", [f"jal x8, {rl}", f"{rl}:"], "ok", "JAL (UXL=1)")
        t.la("x6", rl)
        t.emit("slli x6, x6, 32")
        t.emit("srai x6, x6, 32")
        pred_eq(t, "x7", "x6", "x8")
        t.check_bool("x7", lab, "JAL writes the sign-extended 32-bit return address")

    t.either("x7", body, lambda: t.comment("UXL is fixed at 2"))
    uxl_set(t, 2)
    tests.append(t)

    # ---- sstatus_uxl_addr_modulo ----
    t = new("sstatus_uxl_addr_modulo", rv64=True)
    t.describe(
        source=SUP,
        rule_text="If UXLEN < SXLEN, user-mode instruction-fetch addresses and load and store effective addresses "
        "are taken modulo 2^UXLEN.",
        context=U32_CTX + " The test image is in the lowest 4 GiB.",
        plan="RV64 only, when UXL can be 1. In U-mode with UXLEN=32 and base registers whose bits 63:32 are "
        "nonzero:\n"
        "1. LW from base = 0xA5A5A5A5_00000000 + address of a data word reads that word.\n"
        "2. SW to such a base writes the word (read back in S-mode).\n"
        "3. JALR to such a base reaches the target (the skipped instruction does not run).\n"
        "UXL is restored to 2.",
    )
    t.extra_data += [".balign 8", "s_uxl_word: .word 0x13579BDF, 0", "s_uxl_store: .word 0, 0"]
    uxl32_probe(t)

    def body2() -> None:
        t.load("x6", X(0, "s_uxl_word + 0xA5A5A5A500000000"), "base with bits 63:32 set")
        t.li("x8", 0)
        lab = win(t, "U", ["lw x8, 0(x6)"], "ok", "LW with a 64-bit base (UXL=1)")
        t.check("x8", X(0, 0x13579BDF), lab, "LW reads the word at the base modulo 2^32")
        t.load("x6", X(0, "s_uxl_store + 0x5A5A5A5A00000000"), "base with bits 63:32 set")
        t.load("x7", X(0, 0x2468ACE0), "store data")
        lab = win(t, "U", ["sw x7, 0(x6)"], "ok", "SW with a 64-bit base (UXL=1)")
        t.la("x6", "s_uxl_store")
        t.emit("lw x8, 0(x6)")
        t.check("x8", X(0, 0x2468ACE0), lab, "SW wrote the word at the base modulo 2^32")
        tg = t.label("tgt")
        t.load("x6", X(0, f"{tg} + 0x7E7E7E7E00000000"), "jump target with bits 63:32 set")
        t.la("x1", tg)  # a fetch fault would resume at ra
        t.li("x8", 0x5A5)
        lab = win(t, "U", ["jalr x0, 0(x6)", "addi x8, x0, 1", f"{tg}:"], "ok", "JALR to a 64-bit target (UXL=1)")
        t.check("x8", 0x5A5, lab, "JALR reached the target modulo 2^32")

    t.either("x7", body2, lambda: t.comment("UXL is fixed at 2"))
    uxl_set(t, 2)
    tests.append(t)

    # ---- hint_sxlen ----
    t = new("hint_sxlen", rv64=True)
    t.describe(
        source=SUP,
        rule_text="Some HINT instructions are encoded as integer computational instructions that overwrite their "
        "destination register with its current value, e.g., c.addi x8, 0. When such a HINT is executed with "
        "XLEN < SXLEN and bits SXLEN..XLEN of the destination register not all equal to bit XLEN-1, it is "
        "implementation-defined whether bits SXLEN..XLEN of the destination register are unchanged or are "
        "overwritten with copies of bit XLEN-1.",
        context=U32_CTX + " C.ADDI x8, 0 (0x0401) is a HINT and needs C (Zca).",
        plan="RV64 with C, when UXL can be 1: x8 = 0x12345678_80000000; C.ADDI x8, 0 in U-mode leaves x8 either "
        "unchanged or 0xFFFFFFFF_80000000, and takes no trap.",
    )
    with t.only_if(C):
        uxl32_probe(t)

        def body3() -> None:
            t.load("x8", X(0, 0x1234567880000000), "x8")
            lab = win(
                t,
                "U",
                [".hword 0x0401  // c.addi x8, 0 (HINT)", ".hword 0x0001  // c.nop"],
                "ok",
                "C.ADDI x8, 0 (UXL=1)",
            )
            t.check(
                "x8",
                [X(0, 0x1234567880000000), X(0, 0xFFFFFFFF80000000)],
                lab,
                "C.ADDI x8, 0 leaves bits 63:32 unchanged or copies of bit 31",
            )

        t.either("x7", body3, lambda: t.comment("UXL is fixed at 2"))
        uxl_set(t, 2)
    tests.append(t)
    return tests


def satp_probe(t: TestFile) -> None:
    """M-mode: x8 = OR of the MODE values that satp holds after writes of every non-Bare mode (0 when satp.MODE is
    read-only zero). satp is restored. M-mode accesses are not translated, so the probe writes are harmless."""
    t.comment("probe satp.MODE from M-mode (writes with an unsupported MODE are ignored)")
    t.emit("csrr x9, satp")
    t.li("x8", 0)
    with t.rv64_only():
        for m in (8, 9, 10, 11):
            t.li("x6", m)
            t.emit("slli x6, x6, 60")
            t.emit("csrw satp, x6")
            t.emit("csrr x7, satp")
            t.emit("srli x7, x7, 60")
            t.emit("or x8, x8, x7")
    with t.rv32_only():
        t.li("x6", 1)
        t.emit("slli x6, x6, 31")
        t.emit("csrw satp, x6")
        t.emit("csrr x7, satp")
        t.emit("srli x7, x7, 31")
        t.emit("or x8, x8, x7")
    t.emit("csrw satp, x9")


def gen_sum_ube() -> list[TestFile]:
    tests = []
    # ---- sstatus_sum_satp_mode (M part) ----
    t = new_sm("sstatus_sum_satp_mode")
    t.describe(
        source=SUP,
        rule_text="SUM is read-only 0 if satp.MODE is read-only 0.",
        context="machine.adoc completes the rule: SUM is read-only 0 if S-mode is not supported or if satp.MODE is "
        "read-only 0; otherwise, it must be writable (mstatus_sum_rdonly0). MXR follows the same rule "
        "(mstatus_mxr_rdonly0_no_smode). Whether satp.MODE is read-only zero is found by writing each non-Bare "
        "MODE from M-mode, where satp does not translate; this needs M-mode, so the test is an _Sm file.",
        plan="1. From M-mode, write satp with each non-Bare MODE (Sv39/48/57/64 on RV64, Sv32 on RV32) and note "
        "whether any is held; restore satp.\n"
        "2. Set sstatus.SUM and sstatus.MXR and read them back: each reads 1 if some MODE was held, else 0.\n"
        "3. Clear SUM and MXR.",
    )
    satp_probe(t)
    t.emit("snez x8, x8  // 1: satp.MODE is not read-only zero")
    for f, nm, sh in ((L.SUM, "SUM", 18), (L.MXR, "MXR", 19)):
        L.bits(t, "sstatus", f, True)
        lab = t.label(nm.lower())
        t.emit(f"{lab}:", 0)
        t.emit("csrr x7, sstatus")
        L.bits(t, "sstatus", f, False)
        t.emit(f"srli x7, x7, {sh}")
        t.emit("andi x7, x7, 1")
        if MUT == "sum_ro0_with_vm" and nm == "SUM":
            t.emit("li x7, 0")
        pred_eq(t, "x7", "x7", "x8")
        t.check_bool("x7", lab, f"{nm} is writable iff satp.MODE is not read-only zero")
    tests.append(t)

    # ---- UBE ----
    UBE_CTX = (
        "UBE is sstatus bit 6. It is probed by setting it: a read-only UBE equals S-mode's endianness, which "
        "is little-endian here (the test itself runs little-endian). When UBE cannot be set, no big-endian "
        "U-mode access exists to check."
    )
    DATA = [".balign 8", "s_ube_data: .dword 0x0123456789ABCDEF", "s_ube_store: .dword 0"]

    def ube_probe(t: TestFile) -> None:
        L.bits(t, "sstatus", UBE, True)
        t.emit("csrr x7, sstatus")
        L.bits(t, "sstatus", UBE, False)
        t.emit("srli x7, x7, 6")
        t.emit("andi x7, x7, 1")

    t = new("sstatus_ube")
    t.describe(
        source=SUP,
        rule_text="The UBE bit is a WARL field that controls the endianness of explicit memory accesses made from "
        "U-mode, which may differ from the endianness of memory accesses in S-mode. An implementation may make "
        "UBE be a read-only field that always specifies the same endianness as for S-mode.",
        context=UBE_CTX,
        plan="1. UBE written 0 reads 0 (0 is legal whether UBE is writable or fixed to S-mode's little-endian).\n"
        "2. UBE written 1 reads 0 or 1, through csrs and through csrw of the whole register.\n"
        "3. If it read 1, writing 0 reads 0 again, and the M-mode view (mstatus.UBE) agrees.",
    )
    t.emit("csrr x9, sstatus")
    L.bits(t, "sstatus", UBE, False)
    lab = t.label("ube0")
    t.emit(f"{lab}:", 0)
    t.emit("csrr x7, sstatus")
    t.check_masked("x7", UBE, 0, lab, "UBE written 0 reads 0")
    L.bits(t, "sstatus", UBE, True)
    lab = t.label("ube1")
    t.emit(f"{lab}:", 0)
    t.emit("csrr x7, sstatus")
    t.check_masked("x7", UBE, [0, UBE], lab, "UBE written 1 (csrs) reads 0 or 1")
    t.emit("ori x6, x9, 0x40")
    t.emit("csrw sstatus, x6")
    t.emit("csrr x7, sstatus")
    t.check_masked("x7", UBE, [0, UBE], lab, "UBE written 1 (csrw) reads 0 or 1")
    t.emit("srli x7, x7, 6")
    t.emit("andi x7, x7, 1")

    def ube_rw() -> None:
        t.tsbi_csr("READ", "MSTATUS")
        lab = t.label("ubem")
        t.emit(f"{lab}:", 0)
        t.check_masked("a0", UBE, UBE, lab, "mstatus.UBE (M-mode read) is 1 with sstatus.UBE=1")
        L.bits(t, "sstatus", UBE, False)
        t.emit("csrr x7, sstatus")
        t.check_masked("x7", UBE, 0, lab, "UBE written 0 again reads 0")

    t.either("x7", ube_rw, lambda: t.comment("UBE is read-only (little-endian)"))
    t.emit("csrw sstatus, x9")
    tests.append(t)

    t = new("sstatus_ube_endianness_op")
    t.extra_data += DATA
    t.describe(
        source=SUP,
        rule_text="UBE controls whether explicit load and store memory accesses made from U-mode are little-endian "
        "(UBE=0) or big-endian (UBE=1).",
        context=UBE_CTX + " The data doubleword holds 0x0123456789ABCDEF (bytes EF CD AB 89 67 45 23 01 in "
        "address order).",
        plan="If UBE can be set:\n"
        "1. UBE=1, U-mode loads: LW at offset 0 reads 0xEFCDAB89 (sign-extended), LW at 4 reads 0x67452301, LH "
        "0xEFCD (sign-extended), LHU 0xEFCD, LB 0xEF (sign-extended, one byte is unaffected); on RV64 LWU "
        "0xEFCDAB89 and LD 0xEFCDAB8967452301.\n"
        "2. UBE=1, U-mode stores: SW of 0x11223344 reads back 0x44332211 in S-mode, SH of 0x3344 reads 0x4433 "
        "(LHU), and on RV64 SD of 0x1122334455667788 reads 0x8877665544332211.\n"
        "3. UBE=0: U-mode LW reads 0x89ABCDEF. UBE=1 does not affect S-mode: an S-mode LW reads 0x89ABCDEF.",
    )
    ube_probe(t)

    def ube_ops() -> None:
        def uload(insn: str, off: int, exp: Value, desc: str) -> None:
            t.la("x6", "s_ube_data")
            t.li("x8", 0)
            lab = win(t, "U", [f"{insn} x8, {off}(x6)"], "ok", f"{insn.upper()} with UBE=1")
            t.check("x8", exp, lab, desc)

        L.bits(t, "sstatus", UBE, True)
        uload("lw", 0, X(0xEFCDAB89, 0xFFFFFFFFEFCDAB89), "U-mode LW at offset 0 is big-endian")
        uload("lw", 4, 0x67452301, "U-mode LW at offset 4 is big-endian")
        uload("lh", 0, X(0xFFFFEFCD, 0xFFFFFFFFFFFFEFCD), "U-mode LH is big-endian")
        uload("lhu", 0, 0xEFCD, "U-mode LHU is big-endian")
        uload("lb", 0, X(0xFFFFFFEF, 0xFFFFFFFFFFFFFFEF), "U-mode LB reads the byte")
        with t.rv64_only():
            uload("lwu", 0, X(0, 0xEFCDAB89), "U-mode LWU is big-endian")
            uload("ld", 0, X(0, 0xEFCDAB8967452301), "U-mode LD is big-endian")

        def ustore(insn: str, val: Value, rd_insn: str, exp: Value, desc: str) -> None:
            t.la("x6", "s_ube_store")
            t.emit("sw x0, 0(x6)")
            t.emit("sw x0, 4(x6)")
            t.load("x7", val, "store data")
            lab = win(t, "U", [f"{insn} x7, 0(x6)"], "ok", f"{insn.upper()} with UBE=1")
            t.emit(f"{rd_insn} x8, 0(x6)")
            t.check("x8", exp, lab, desc)

        ustore("sw", 0x11223344, "lw", 0x44332211, "U-mode SW is big-endian (S-mode LW reads it reversed)")
        ustore("sh", 0x3344, "lhu", 0x4433, "U-mode SH is big-endian")
        with t.rv64_only():
            ustore("sd", X(0, 0x1122334455667788), "ld", X(0, 0x8877665544332211), "U-mode SD is big-endian")
        lab = t.label("sload")
        t.la("x6", "s_ube_data")
        t.emit(f"{lab}:", 0)
        t.emit("lw x8, 0(x6)")
        t.check("x8", X(0x89ABCDEF, 0xFFFFFFFF89ABCDEF), lab, "S-mode LW with UBE=1 is little-endian")
        L.bits(t, "sstatus", UBE, False)

    t.either("x7", ube_ops, lambda: t.comment("UBE is read-only (little-endian)"))
    t.la("x6", "s_ube_data")
    t.li("x8", 0)
    lab = win(t, "U", ["lw x8, 0(x6)"], "ok", "LW with UBE=0")
    t.check("x8", X(0x89ABCDEF, 0xFFFFFFFF89ABCDEF), lab, "U-mode LW with UBE=0 is little-endian")
    tests.append(t)

    t = new("sstatus_ube_implicit")
    t.describe(
        source=SUP,
        rule_text="UBE has no effect on instruction fetches, which are implicit memory accesses that are always "
        "little-endian.",
        context=UBE_CTX,
        plan="If UBE can be set: with UBE=1, U-mode executes ADDI x8, x0, 0x123 and XORI x8, x8, 0x456 without a "
        "trap and x8 = 0x575 (a big-endian fetch would decode other instructions). The same with UBE=0.",
    )
    ube_probe(t)

    def impl(on: bool) -> None:
        if on:
            L.bits(t, "sstatus", UBE, True)
        t.li("x8", 0)
        lab = win(t, "U", ["addi x8, x0, 0x123", "xori x8, x8, 0x456"], "ok", f"U-mode code with UBE={int(on)}")
        t.check("x8", 0x575, lab, f"U-mode instructions fetched little-endian with UBE={int(on)}")
        L.bits(t, "sstatus", UBE, False)

    t.either("x7", lambda: impl(True), lambda: t.comment("UBE is read-only (little-endian)"))
    impl(False)
    tests.append(t)

    # ---- menvcfg_dte_sdt_rdonly0 ----
    t = new("menvcfg_dte_sdt_rdonly0")
    t.forbidden = ["Ssdbltrp"]
    t.describe(
        source=MAC,
        rule_text="When Ssdbltrp is not implemented sstatus.SDT, vsstatus.SDT, and henvcfg.DTE bits are read-only "
        "zero.",
        context="The test runs only on harts without Ssdbltrp. SDT is sstatus bit 24 (vsstatus too); DTE is "
        "henvcfg bit 59 (henvcfgh bit 27 on RV32). vsstatus and henvcfg exist only with H; henvcfg needs "
        "priv 1.12.",
        plan="1. Setting sstatus.SDT (csrs, then csrw of the whole register with bit 24 set) leaves it 0.\n"
        "2. With H: setting vsstatus.SDT and henvcfg.DTE from HS-mode leaves them 0.",
    )
    t.emit("csrr x9, sstatus")
    L.bits(t, "sstatus", L.SDT, True)
    lab = t.label("sdt")
    t.emit(f"{lab}:", 0)
    t.emit("csrr x7, sstatus")
    t.check_masked("x7", L.SDT, 0, lab, "sstatus.SDT reads 0 after csrs")
    t.li("x6", L.SDT)
    t.emit("or x6, x6, x9")
    t.emit("csrw sstatus, x6")
    t.emit("csrr x7, sstatus")
    t.emit("csrw sstatus, x9")
    t.check_masked("x7", L.SDT, 0, lab, "sstatus.SDT reads 0 after csrw")
    with t.only_if(H):
        t.li("x6", L.SDT)
        t.emit("csrs CSR_VSSTATUS, x6")
        t.emit("csrr x7, CSR_VSSTATUS")
        t.emit("csrc CSR_VSSTATUS, x6")
        t.check_masked("x7", L.SDT, 0, lab, "vsstatus.SDT reads 0 after csrs")
        with t.only_if(S1P12):
            with t.rv64_only():
                t.li("x6", 1)
                t.emit("slli x6, x6, 59")
                t.emit("csrs CSR_HENVCFG, x6")
                t.emit("csrr x7, CSR_HENVCFG")
                t.emit("csrc CSR_HENVCFG, x6")
                t.emit("srli x7, x7, 59")
            with t.rv32_only():
                t.li("x6", 1 << 27)
                t.emit("csrs CSR_HENVCFGH, x6")
                t.emit("csrr x7, CSR_HENVCFGH")
                t.emit("csrc CSR_HENVCFGH, x6")
                t.emit("srli x7, x7, 27")
            t.emit("andi x7, x7, 1")
            t.check("x7", 0, lab, "henvcfg.DTE reads 0 after csrs")
    tests.append(t)
    return tests


# ======================================================================== stvec
STVEC_DATA = [
    ".balign 4096",
    "s_tv_page: .word 0",
    ".balign 64",
    "s_tv_64: .word 0, 0, 0",
    "s_tv_end: .word 0",
    ".balign 8",
    "s_tv_save: .dword 0",
]
STVEC_CTX = (
    "The framework keeps its S-mode trap handler address in stvec. Values written by the test are read back "
    "and stvec is restored before any trap can be taken. Valid addresses are taken from the test's own "
    "data section."
)


def gen_stvec() -> list[TestFile]:
    tests = []

    def save(t: TestFile) -> None:
        t.emit("csrr x9, stvec  // framework value, restored before any trap")

    def restore(t: TestFile) -> None:
        t.emit("csrw stvec, x9")

    def direct_probe(t: TestFile) -> None:
        """x8 = 1 if stvec holds a Direct-mode value (written s_tv_page, MODE 0)."""
        t.la("x6", "s_tv_page")
        t.emit("csrw stvec, x6")
        t.emit("csrr x7, stvec")
        restore(t)
        pred_eq(t, "x8", "x6", "x7")

    # ---- stvec ----
    t = new("stvec")
    t.extra_data += STVEC_DATA
    t.describe(
        source=SUP,
        rule_text="The stvec register is an SXLEN-bit read/write register that holds trap vector configuration, "
        "consisting of a vector base address (BASE) and a vector mode (MODE).",
        context=STVEC_CTX + " Direct mode (MODE=0) is optional (Sstvecd); it is probed by writing a page-aligned "
        "data address with MODE=0.",
        plan="1. The framework's own value reads back after being rewritten.\n"
        "2. If Direct mode is held: every CSR instruction form with nonzero effect is checked on stvec (CSRRW "
        "with rd=x0 and rd!=x0, CSRRS/CSRRC with rs1=x0 and rs1!=x0, CSRRSI uimm=0, CSRRSI/CSRRCI with uimm=0x10), "
        "operating on a 4 KiB-aligned BASE with bit 8 or bit 4 toggled; each returns the old value and leaves "
        "the defined one.\n"
        "3. MODE reads 0 or 1 after writing BASE with MODE=1.\n"
        "stvec is restored after each step.",
    )
    save(t)
    lab = t.label("own")
    t.emit(f"{lab}:", 0)
    t.emit("csrw stvec, x9")
    t.emit("csrr x7, stvec")
    pred_eq(t, "x7", "x7", "x9")
    t.check_bool("x7", lab, "stvec reads back the framework's value")
    direct_probe(t)

    def forms() -> None:
        P = "s_tv_page"
        cases = [  # (asm, old, rs (x6), rd expected, new expected)
            ("csrrs x7, stvec, x0", P, None, P, P),
            ("csrrw x0, stvec, x6", P, f"{P}+0x100", None, f"{P}+0x100"),
            ("csrrw x7, stvec, x6", f"{P}+0x100", P, f"{P}+0x100", P),
            ("csrrs x7, stvec, x6", P, 0x100, P, f"{P}+0x100"),
            ("csrrc x7, stvec, x6", f"{P}+0x100", 0x100, f"{P}+0x100", P),
            ("csrrsi x7, stvec, 0", f"{P}+0x10", None, f"{P}+0x10", f"{P}+0x10"),
            ("csrrsi x7, stvec, 0x10", P, None, P, f"{P}+0x10"),
            ("csrrci x7, stvec, 0x10", f"{P}+0x10", None, f"{P}+0x10", P),
        ]
        for asm, old, rs, rd, newv in cases:
            t.comment(f"{asm}: old {old}")
            t.load("x6", old, "old value")
            t.emit("csrw stvec, x6")
            if rs is not None:
                t.load("x6", rs, "operand")
            lab = t.label("form")
            t.emit(f"{lab}:", 0)
            t.emit(asm)
            t.emit("csrr x8, stvec")
            restore(t)
            if rd is not None:
                t.check("x7", rd, lab, f"{asm} returns the old stvec")
            t.check("x8", newv, lab, f"{asm} leaves stvec = {newv}")

    t.either("x8", forms, lambda: t.comment("Direct mode is not supported"))
    t.la("x6", "s_tv_page")
    t.emit("ori x6, x6, 1")
    lab = t.label("vec")
    t.emit(f"{lab}:", 0)
    t.emit("csrw stvec, x6")
    t.emit("csrr x7, stvec")
    restore(t)
    t.emit("andi x7, x7, 3")
    t.check("x7", [0, 1], lab, "stvec.MODE reads 0 or 1 after writing MODE=1")
    tests.append(t)

    # ---- stvec_op ----
    t = new("stvec_op")
    t.extra_data += STVEC_DATA
    t.describe(
        source=SUP,
        rule_text="The BASE field in stvec is a WARL field that can hold any valid virtual or physical address, "
        "subject to the following alignment constraints: the address must be 4-byte aligned, and MODE settings "
        "other than Direct might impose additional alignment constraints on the value in the BASE field.",
        context=STVEC_CTX + " Translation is Bare in S-mode, so valid addresses are physical addresses of the test "
        "image. Additional alignment applies only to non-Direct modes, so Direct mode must hold every 4-byte "
        "aligned valid address.",
        plan="If Direct mode is held: stvec written with MODE=0 and BASE = each of several 4-byte-aligned "
        "addresses in the test image (a page start, +4, +8, +0x40, +0xFFC, a 64-byte-aligned word, the code and "
        "data section starts and the trap log) reads back exactly. stvec is restored after each write.",
    )
    save(t)
    direct_probe(t)
    addrs = [
        "s_tv_page",
        "s_tv_page+4",
        "s_tv_page+8",
        "s_tv_page+0x40",
        "s_tv_page+0xFFC",
        "s_tv_64+4",
        "s_tv_end",
        "rvtest_code_begin",
        "rvtest_data_begin",
        "rvtest_trap_log",
        "s_tv_save",
    ]

    def addr_cases() -> None:
        for a in addrs:
            t.load("x6", a, a)
            lab = t.label("base")
            t.emit(f"{lab}:", 0)
            t.emit("csrw stvec, x6")
            t.emit("csrr x7, stvec")
            restore(t)
            t.check("x7", a, lab, f"stvec holds BASE = {a} (Direct)")

    t.either("x8", addr_cases, lambda: t.comment("Direct mode is not supported"))
    tests.append(t)
    return tests


def gen_stvec_traps() -> list[TestFile]:
    """stvec_sz_base and stvec_mode_enc: traps through the framework trampoline in Direct and Vectored mode."""
    tests = []
    CTX = (
        "The framework's S-mode trap entry is a trampoline: BASE+4*k holds a jump to stub k, and every stub "
        "records which one ran in bits 10:6 of trap log word 0 (rvtest_trap_handler.h, sv_<MODE>vect). In "
        "Direct mode every trap enters stub 0; in Vectored mode an interrupt with cause k enters stub k. The "
        "test switches stvec.MODE while keeping the framework's BASE (the trampoline was written for both "
        "modes) and restores stvec at the end. The framework's own MODE (m0, from stvec at the start) shifts the "
        "recorded stub number. If the trampoline BASE is not held with the other MODE, that mode is not "
        "checked."
    )

    def vec_check(t: TestFile, code: int, lab: str, desc: str, m0: int, mode: int) -> None:
        logged(t, "x15", "TRAPLOG_VECT")
        t.emit("srli x15, x15, 6")
        t.emit("andi x15, x15, 0x1F")
        k = code if mode == 1 else 0
        if MUT == "direct_vectors_interrupts" and mode == 0 and code:
            k = code
        if MUT == "vectored_exceptions" and mode == 1 and not code:
            k = 3
        t.check("x15", X(L.vect(k, 32, m0), L.vect(k, 64, m0)), lab, desc)

    def set_mode(t: TestFile, mode: int) -> None:
        """stvec = framework BASE | mode. x8 = 1 if held."""
        t.la("x6", "s_tv_save")
        t.emit("LREG x7, 0(x6)")
        t.emit("andi x7, x7, -4")
        if mode:
            t.emit(f"ori x7, x7, {mode}")
        t.emit("csrw stvec, x7")
        t.emit("csrr x8, stvec")
        pred_eq(t, "x8", "x8", "x7")
        t.emit("bnez x8, 1f")
        t.emit("LREG x7, 0(x6)")
        t.emit("csrw stvec, x7  // not held: restore")
        t.emit("1:", 0)

    def restore(t: TestFile) -> None:
        t.la("x6", "s_tv_save")
        t.emit("LREG x7, 0(x6)")
        t.emit("csrw stvec, x7")

    def prologue(t: TestFile) -> None:
        quiet_sie(t)
        t.emit("csrr x7, stvec")
        t.la("x6", "s_tv_save")
        t.emit("SREG x7, 0(x6)")
        t.emit("andi x7, x7, 3  // m0: the framework's MODE")

    # ---- stvec_sz_base ----
    t = new("stvec_sz_base", pool=POOL_INT)
    t.extra_data += [".balign 8", "s_tv_save: .dword 0"]
    t.describe(
        source=SUP,
        rule_text="Note that the CSR contains only bits XLEN-1 through 2 of the address BASE. When used as an "
        "address, the lower two bits are filled with zeroes to obtain an XLEN-bit address that is always aligned "
        "on a 4-byte boundary.",
        context=CTX + " With MODE=1 the low two bits of stvec are 01, so an exception that used them as part of "
        "the address would start at BASE+1.",
        plan="1. Direct (MODE=0, if held): EBREAK traps and enters stub 0 (BASE).\n"
        "2. Vectored (MODE=1, if held): EBREAK traps and enters stub 0, i.e. BASE with bits 1:0 zero, not BASE+1.\n"
        "stvec is restored at the end.",
    )
    prologue(t)

    def sz(m0: int) -> None:
        for mode in (0, 1):
            set_mode(t, mode)

            def body(mode: int = mode) -> None:
                lab = win(t, "S", ["ebreak"], L.BREAKPOINT, f"EBREAK with stvec.MODE={mode}", [0], self_tval=True)
                vec_check(t, 0, lab, f"EBREAK with MODE={mode} enters BASE (stub 0)", m0, mode)

            t.either("x8", body, lambda mode=mode: t.comment(f"MODE={mode} not held with this BASE"))
            restore(t)

    t.either("x7", lambda: sz(1), lambda: sz(0))
    tests.append(t)

    # ---- stvec_mode_enc ----
    t = new("stvec_mode_enc", pool=POOL_INT)
    t.extra_data += [".balign 8", "s_tv_save: .dword 0"]
    t.describe(
        source=SUP,
        rule_text="Encoding of stvec MODE field: 0 Direct: all exceptions set pc to BASE. 1 Vectored: asynchronous "
        "interrupts set pc to BASE+4*cause. >=2 Reserved.",
        context=CTX + ' In Vectored mode exceptions still set pc to BASE (the Vectored row\'s "all exceptions" '
        "half is shared with Direct, and only asynchronous interrupts are offset). Interrupts: SSI (cause 1), STI "
        "(5) and SEI (9), each when implemented.",
        plan="1. Direct (if held): EBREAK and each implemented S-level interrupt (taken in S-mode with SIE=1) enter "
        "stub 0.\n"
        "2. Vectored (if held): EBREAK enters stub 0; SSI enters stub 1, STI stub 5 and SEI stub 9.\n"
        "stvec is restored at the end.",
    )
    prologue(t)

    def me(m0: int) -> None:
        for mode in (0, 1):
            set_mode(t, mode)

            def body(mode: int = mode) -> None:
                lab = win(t, "S", ["ebreak"], L.BREAKPOINT, f"EBREAK with stvec.MODE={mode}", [0], self_tval=True)
                vec_check(t, 0, lab, f"EBREAK with MODE={mode} enters BASE (stub 0)", m0, mode)
                for src, code in SRC.items():

                    def ib(src: str = src, code: int = code) -> None:
                        lab = L.int_window(t, [src], "S", 1, 1, 1, icause(code), f"{src} with stvec.MODE={mode}")
                        vec_check(t, code, lab, f"{src} with MODE={mode} enters stub {code if mode else 0}", m0, mode)

                    L.with_src(t, src, ib)

            t.either("x8", body, lambda mode=mode: t.comment(f"MODE={mode} not held with this BASE"))
            restore(t)

    t.either("x7", lambda: me(1), lambda: me(0))
    tests.append(t)
    return tests


# ======================================================================== sip / sie
INT_CTX = (
    "The framework delegates SSI, STI and SEI to S-mode (mideleg). An interrupt is implemented when its sie "
    "bit is writable (sie_acc); each test probes this and skips absent interrupts. SSI is raised through "
    "sip.SSIP, STI through M-mode mip.STIP (menvcfg.STCE=0) and SEI through the platform or M-mode "
    "mip.SEIP. The framework handler masks the taken interrupt in sie."
)


def multi_outcome(t: TestFile, causes: list[Value], lab: str, desc: str) -> None:
    """Close a window that must have taken len(causes) traps, in this order."""
    n = len(causes)
    t.emit("AI_OUTCOME", 20)
    t.check("x13", n, lab, f"{desc}: number of traps")
    for j, c in enumerate(causes):
        L.log_word(t, "x15", n - 1 - j, "TRAPLOG_CAUSE")
        t.check("x15", c, lab, f"{desc}: trap {j + 1} cause")


def gen_sip_sie() -> list[TestFile]:
    tests = []

    # ---- sip_sie ----
    t = new("sip_sie", pool=POOL_INT)
    t.describe(
        source=SUP,
        rule_text="The sip register is an SXLEN-bit read/write register containing information on pending "
        "interrupts, while sie is the corresponding SXLEN-bit read/write register containing interrupt enable "
        "bits. Interrupt cause number i (as reported in CSR scause) corresponds with bit i in both sip and sie. "
        "Bits 15:0 are allocated to standard interrupt causes only, while bits 16 and above are designated for "
        "platform use.",
        context=INT_CTX,
        plan="For each implemented S-level interrupt i (SSI 1, STI 5, SEI 9):\n"
        "1. Raising it sets sip bit i and no other of bits 1, 5, 9.\n"
        "2. With sie bit i set and SIE=1 in S-mode it is taken with scause = interrupt | i.\n"
        "3. With only a different sie bit set (all other standard bits 1, 5, 9) it is not taken.",
    )
    quiet_sie(t)
    for src, code in SRC.items():

        def body(src: str = src, code: int = code) -> None:
            L.raise_int(t, src)
            lab = t.label("sip")
            t.emit(f"{lab}:", 0)
            t.emit("csrr x7, sip")
            t.check_masked("x7", 0x222, 1 << code, lab, f"raising {src} sets sip bit {code} only (of 1, 5, 9)")
            others = 0x222 & ~(1 << code)
            t.li("x6", others)
            t.emit("csrs sie, x6")
            t.li("x6", SIE)
            t.allow(1)
            lab = t.label("other")
            t.emit(f"{lab}:", 0)
            t.emit("csrs sstatus, x6")
            L.delay(t)
            L.bits(t, "sstatus", SIE, False)
            t.emit("csrw sie, x0")
            t.outcome("ok", lab, f"{src} pending, only other sie bits set: not taken", epc=False, origin="S")
            L.lower_int(t, src)
            L.int_window(t, [src], "S", 1, 1, 1, icause(code), f"{src} with sie bit {code}")

        L.with_src(t, src, body)
    tests.append(t)

    # ---- sip_sie (M part): mideleg masks the views ----
    t = new_sm("sip_sie", pool=POOL_INT)
    t.describe(
        source=SUP,
        rule_text="The sip register is an SXLEN-bit read/write register containing information on pending "
        "interrupts, while sie is the corresponding SXLEN-bit read/write register containing interrupt enable "
        "bits. Interrupt cause number i corresponds with bit i in both sip and sie.",
        context="machine.adoc (untagged): restricted views of mip and mie appear as sip and sie. If an interrupt "
        "is delegated to S-mode by setting a bit in mideleg, it becomes visible in sip and is maskable using sie. "
        "Otherwise, the corresponding bits in sip and sie are read-only zero. This needs mideleg writes, so it is "
        "an _Sm file; the test runs in M-mode with mstatus.MIE=0, so nothing is taken. mideleg bits are WARL and "
        "probed; mip bits are probed for M-mode writability. With Smaia, mvien is cleared first (mvien[1]=1 would "
        "make sip.SSIP/sie.SSIE writable without mideleg).",
        plan="For SSIP (1), STIP (5) and SEIP (9), when M-mode can set the mip bit:\n"
        "1. mideleg bit clear, mip bit and mie bit set: sip and sie read 0 in that bit; S-level writes (csrc sip, "
        "csrc sie) leave mip and mie set.\n"
        "2. mideleg bit set (if writable): sip and sie read 1; csrc sie clears mie; csrs sie sets it again; for "
        "SSIP, csrc sip clears mip.\n"
        "3. mip, mie and mideleg bits are cleared.",
    )
    t.emit("csrr x9, mideleg")
    with t.only_if("defined(SMAIA_SUPPORTED)"):
        t.emit("csrw 0x308, x0  // mvien = 0: with Smaia, mvien bits can make sip/sie bits aliases without mideleg")
    for src, code in SRC.items():
        b = 1 << code

        def mbody(src: str = src, b: int = b, code: int = code) -> None:
            t.li("x6", b)
            t.emit("csrc mideleg, x6")
            t.emit("csrs mie, x6")
            lab = t.label("nodeleg")
            t.emit(f"{lab}:", 0)
            t.emit("csrr x7, sip")
            t.emit("csrr x8, sie")
            t.emit("or x7, x7, x8")
            exp = b if MUT == "sip_shows_undelegated" else 0
            t.check_masked("x7", b, exp, lab, f"mideleg bit clear: sip/sie bit {code} read 0 with mip/mie set")
            t.emit("csrc sie, x6")
            t.emit("csrc sip, x6")
            t.emit("csrr x7, mie")
            t.emit("csrr x8, mip")
            t.emit("and x7, x7, x8")
            t.check_masked("x7", b, b, lab, f"mideleg bit clear: S-level writes do not clear mie/mip bit {code}")
            t.emit("csrs mideleg, x6")
            t.emit("csrr x7, mideleg")
            t.emit("and x7, x7, x6")

            def deleg() -> None:
                lab = t.label("deleg")
                t.emit(f"{lab}:", 0)
                t.emit("csrr x7, sip")
                t.emit("csrr x8, sie")
                t.emit("and x7, x7, x8")
                t.check_masked("x7", b, b, lab, f"mideleg bit set: sip/sie bit {code} read 1")
                t.emit("csrc sie, x6")
                t.emit("csrr x7, mie")
                t.check_masked("x7", b, 0, lab, f"mideleg bit set: csrc sie clears mie bit {code}")
                t.emit("csrs sie, x6")
                t.emit("csrr x7, mie")
                t.check_masked("x7", b, b, lab, f"mideleg bit set: csrs sie sets mie bit {code}")
                if src == "SSI":
                    t.emit("csrc sip, x6")
                    t.emit("csrr x7, mip")
                    t.check_masked("x7", b, 0, lab, "mideleg.SSI set: csrc sip clears mip.SSIP")

            t.either("x7", deleg, lambda: t.comment("mideleg bit is read-only zero"))
            t.emit("csrc mip, x6")
            t.emit("csrc mie, x6")
            t.emit("csrc mideleg, x6")

        t.comment(f"{src}: can M-mode set mip bit {code}?")
        t.li("x6", b)
        if src == "STI":
            with t.only_if("defined(SSTC_SUPPORTED)"):
                with t.rv64_only():
                    t.li("x7", 1)
                    t.emit("slli x7, x7, 63")
                    t.emit("csrc menvcfg, x7  // STCE = 0: mip.STIP is writable")
                with t.rv32_only():
                    t.li("x7", 0x80000000)
                    t.emit("csrc menvcfgh, x7")
        t.emit("csrs mip, x6")
        t.emit("csrr x7, mip")
        t.emit("and x7, x7, x6")
        t.either("x7", mbody, lambda: t.comment("mip bit is not writable from M-mode"))
    t.emit("csrw mideleg, x9")
    tests.append(t)

    # ---- sie_sip_supervisor_strap ----
    t = new("sie_sip_supervisor_strap", pool=POOL_INT)
    t.describe(
        source=SUP,
        rule_text="An interrupt i will trap to S-mode if both of the following are true: (a) either the current "
        "privilege mode is S and the SIE bit in the sstatus register is set, or the current privilege mode has "
        "less privilege than S-mode; and (b) bit i is set in both sip and sie.",
        context=INT_CTX,
        plan="For each implemented S-level interrupt, all eight combinations of (SIE, sie bit, pending) in S-mode "
        "and in U-mode, in a trap window over a 50-iteration loop: taken iff pending and enabled and (S-mode with "
        "SIE=1, or U-mode).",
    )
    quiet_sie(t)
    allc = [(m, a, b, c) for m in ("S", "U") for a in (0, 1) for b in (0, 1) for c in (0, 1)]
    for src in SRC:
        L.with_src(t, src, lambda src=src: interrupt_sweep(t, src, allc, "trap condition"))
    tests.append(t)

    # ---- sie_sip_strap_time_constraint ----
    t = new("sie_sip_strap_time_constraint", pool=POOL_INT)
    t.describe(
        source=SUP,
        rule_text="These conditions for an interrupt trap to occur must be evaluated in a bounded amount of time "
        "from when an interrupt becomes, or ceases to be, pending in sip, and must also be evaluated immediately "
        "following the execution of an SRET instruction or an explicit write to a CSR on which these interrupt "
        "trap conditions expressly depend (including sip, sie and sstatus).",
        context=INT_CTX + ' "Immediately following" means the interrupt is taken before the next instruction '
        "executes, so sepc is the address of the instruction after the CSR write, or the SRET target.",
        plan="For each implemented S-level interrupt i:\n"
        "1. Pending and enabled in sie, S-mode with SIE=0: csrs sstatus.SIE traps with sepc = the next "
        "instruction.\n"
        "2. Pending, SIE=1: csrs sie bit i traps with sepc = the next instruction.\n"
        "3. SSI only: enabled, SIE=1: csrsi sip.SSIP traps with sepc = the next instruction.\n"
        "4. SRET to S-mode with SPIE=1 (pending, enabled): traps with sepc = the SRET target.\n"
        "5. SRET to U-mode (pending, enabled): traps from U with sepc = the SRET target.\n"
        "6. Ceases to be pending: raised then lowered (sip bit seen 0), enabled; setting SIE takes nothing.\n"
        "7. Becomes pending in a bounded time: enabled with SIE=1 in S-mode, raised inside the window: taken.",
    )
    quiet_sie(t)

    def tc(src: str) -> None:
        code = SRC[src]
        b = 1 << code
        cause = icause(code)
        late = MUT == "late_evaluation"

        def csr_write(setup: list[tuple[str, int, bool]], insn: list[str], desc: str) -> None:
            for csr, m, on in setup:
                L.bits(t, csr, m, on)
            L.raise_int(t, src)
            t.li("x6", SIE if "sstatus" in insn[0] else b)
            t.allow(1)
            nxt = t.label("next")
            nxt2 = nxt
            for ln in insn:
                t.emit(ln)
            t.emit(f"{nxt}:", 0)
            t.emit("nop")
            if late:
                nxt2 = t.label("next2")
                t.emit(f"{nxt2}:", 0)
            t.emit("nop")
            L.bits(t, "sstatus", SIE, False)
            t.emit("csrw sie, x0")
            t.outcome(cause, nxt2 if late else nxt, f"{src}: {desc}", [0], origin="S")
            L.lower_int(t, src)

        csr_write([("sie", b, True)], ["csrs sstatus, x6"], "csrs sstatus.SIE takes it before the next instruction")
        # 2: SIE=1 first (nothing enabled), then enable in sie
        L.raise_int(t, src)
        L.bits(t, "sstatus", SIE, True)
        t.li("x6", b)
        t.allow(1)
        nxt = t.label("next")
        t.emit("csrs sie, x6")
        t.emit(f"{nxt}:", 0)
        t.emit("nop")
        t.emit("nop")
        L.bits(t, "sstatus", SIE, False)
        t.emit("csrw sie, x0")
        t.outcome(cause, nxt, f"{src}: csrs sie takes it before the next instruction", [0], origin="S")
        L.lower_int(t, src)
        if src == "SSI":
            L.bits(t, "sie", b, True)
            L.bits(t, "sstatus", SIE, True)
            t.allow(1)
            nxt = t.label("next")
            t.emit("csrsi sip, 2")
            t.emit(f"{nxt}:", 0)
            t.emit("nop")
            t.emit("nop")
            L.bits(t, "sstatus", SIE, False)
            t.emit("csrw sie, x0")
            t.outcome(cause, nxt, "SSI: csrsi sip.SSIP takes it before the next instruction", [0], origin="S")
            t.emit("csrci sip, 2")
        for mode in ("S", "U"):
            L.bits(t, "sie", b, True)
            L.raise_int(t, src)
            tgt = t.label(f"tgt{mode}")
            t.allow(1)
            sret_to(t, mode, tgt, spie=1)
            t.emit(f"{tgt}:", 0)
            t.emit("nop")
            t.emit("nop")
            if mode == "U":
                t.leave()
            L.bits(t, "sstatus", SIE, False)
            t.emit("csrw sie, x0")
            t.outcome(cause, tgt, f"{src}: SRET to {mode}-mode takes it at the SRET target", [0], origin=mode)
            L.lower_int(t, src)
        # 6: ceases to be pending
        L.bits(t, "sie", b, True)
        L.raise_int(t, src)
        L.lower_int(t, src)
        t.li("x6", SIE)
        lab = t.label("ceased")
        t.allow(1)
        t.emit(f"{lab}:", 0)
        t.emit("csrs sstatus, x6")
        L.delay(t)
        L.bits(t, "sstatus", SIE, False)
        t.emit("csrw sie, x0")
        t.outcome("ok", lab, f"{src}: no longer pending, setting SIE takes nothing", epc=False, origin="S")
        # 7: becomes pending while enabled
        L.bits(t, "sie", b, True)
        L.bits(t, "sstatus", SIE, True)
        lab = t.label("becomes")
        t.allow(1)
        t.emit(f"{lab}:", 0)
        if src == "SSI":
            t.emit("csrsi sip, 2")
        elif src == "STI":
            t.emit("RVTEST_SET_STIME_INT_S", 130)
        else:
            t.emit("RVTEST_SET_SEXT_INT_S", 150)
        L.delay(t, 200)
        L.bits(t, "sstatus", SIE, False)
        t.emit("csrw sie, x0")
        t.outcome(
            cause, lab, f"{src}: becomes pending while enabled: taken within a bounded time", [0], epc=False, origin="S"
        )
        L.lower_int(t, src)

    for src in SRC:
        L.with_src(t, src, lambda src=src: tc(src))
    tests.append(t)
    return tests


def gen_sip_bits() -> list[TestFile]:
    tests = []
    STD = 0xFFFF & ~0x2222

    def ro_pending(t: TestFile, src: str, desc: str) -> None:
        """src (STI or SEI, raised by the execution environment) stays pending after S-mode writes of 0 to its
        read-only sip bit, and S-mode writes of 1 do not raise it."""
        code = SRC[src]
        b = 1 << code
        wr = (MUT == "stip_writable" and src == "STI") or (MUT == "seip_writable" and src == "SEI")
        L.raise_int(t, src)
        for asm in ("csrc sip, x6", "csrw sip, x0"):
            t.li("x6", b)
            lab = t.label("ro")
            t.emit(f"{lab}:", 0)
            t.emit(asm)
            L.delay(t, 20)
            t.emit("csrr x7, sip")
            t.check_masked("x7", b, 0 if wr else b, lab, f"{desc}: {asm} leaves sip bit {code} set (read-only)")
        L.int_window(t, [src], "S", 1, 1, 0, icause(code), f"{src} still pending after the writes")
        L.lower_int(t, src)
        t.li("x6", b)
        lab = t.label("ro1")
        t.emit(f"{lab}:", 0)
        t.emit("csrs sip, x6")
        L.delay(t, 20)
        t.emit("csrr x7, sip")
        t.check_masked("x7", b, 0, lab, f"{desc}: csrs sip does not set sip bit {code} (read-only)")

    # ---- sip_acc / sip_op ----
    t = new("sip_op", pool=POOL_INT)
    t.describe(
        source=SUP,
        rule_text="When bit i in sip is writable, a pending interrupt i can be cleared by writing 0 to this bit. If "
        "interrupt i can become pending but bit i in sip is read-only, the implementation must provide some "
        "other mechanism for clearing the pending interrupt (which may involve a call to the execution "
        "environment).",
        context=INT_CTX + " SSIP is writable in sip (sip_ssip_sie_ssie); STIP and SEIP are read-only in sip "
        "(sip_stip_sie_stie, sip_seip_sie_seie) and are cleared by the execution environment (T-SBI or the "
        "platform). LCOFIP belongs to Sscofpmf.",
        plan="1. SSI: set pending, enabled in sie with SIE=0; writing 0 to sip.SSIP clears it (sip reads 0), and "
        "setting SIE then takes nothing. Also with csrrw of 0 and csrrci.\n"
        "2. STI and SEI: S-mode writes of 0 (csrc, csrw) leave them pending and taken; the execution environment "
        "clears them (sip bit reads 0 afterwards).",
    )
    quiet_sie(t)

    def ssi_clear() -> None:
        for asm in ("csrci sip, 2", "csrw sip, x0", "csrrc x7, sip, x6"):
            L.bits(t, "sie", 2, True)
            L.raise_int(t, "SSI")
            t.li("x6", 2)
            lab = t.label("clr")
            t.emit(f"{lab}:", 0)
            t.emit(asm)
            t.emit("csrr x7, sip")
            t.check_masked("x7", 2, 2 if MUT == "ssip_readonly" else 0, lab, f"{asm} clears sip.SSIP")
            t.li("x6", SIE)
            t.allow(1)
            lab2 = t.label("noint")
            t.emit(f"{lab2}:", 0)
            t.emit("csrs sstatus, x6")
            L.delay(t)
            L.bits(t, "sstatus", SIE, False)
            t.emit("csrw sie, x0")
            t.outcome("ok", lab2, f"SSI cleared by {asm}: nothing taken with SIE=1", epc=False, origin="S")

    L.with_src(t, "SSI", ssi_clear)
    for src in ("STI", "SEI"):
        L.with_src(t, src, lambda src=src: ro_pending(t, src, f"{src}"))
    tests.append(t)

    # ---- sip_stip_sie_stie ----
    t = new("sip_stip_sie_stie", pool=POOL_INT)
    t.describe(
        source=SUP,
        rule_text="Bits sip.STIP and sie.STIE are the interrupt-pending and interrupt-enable bits for "
        "supervisor-level timer interrupts. If implemented, STIP is read-only in sip. When the Sstc extension is "
        "not implemented, STIP is set and cleared by the execution environment. When the Sstc extension is "
        "implemented, STIP reflects the timer interrupt signal resulting from stimecmp. ...",
        context=INT_CTX + " The Sstc part (stimecmp) is tested by the Sstc suite; here menvcfg.STCE=0 (boot "
        "value), so STIP behaves as without Sstc and the execution environment (M-mode mip.STIP through T-SBI) "
        "sets and clears it.",
        plan="If STI is implemented:\n"
        "1. M-mode sets mip.STIP: sip.STIP reads 1; S-mode csrc and csrw of sip leave it 1; csrs sip.STIP after "
        "M-mode clears it leaves it 0.\n"
        "2. sie.STIE is the enable: with STIP pending, STIE=1 and SIE=1 it is taken with cause 5; STIE=0 is not.\n"
        "3. M-mode clearing mip.STIP makes sip.STIP read 0.",
    )
    quiet_sie(t)

    def sti() -> None:
        ro_pending(t, "STI", "STIP")
        L.int_window(t, ["STI"], "S", 1, 0, 1, "ok", "STI pending with sie.STIE=0")

    L.with_src(t, "STI", sti)
    tests.append(t)

    # ---- sip_seip_sie_seie ----
    t = new("sip_seip_sie_seie", pool=POOL_INT)
    t.describe(
        source=SUP,
        rule_text="Bits sip.SEIP and sie.SEIE are the interrupt-pending and interrupt-enable bits for "
        "supervisor-level external interrupts. If implemented, SEIP is read-only in sip, and is set and cleared "
        "by the execution environment, typically through a platform-specific interrupt controller.",
        context=INT_CTX,
        plan="If SEI is implemented:\n"
        "1. The execution environment raises SEI: sip.SEIP reads 1; S-mode csrc and csrw of sip leave it 1; it is "
        "taken with cause 9 when sie.SEIE=1 and SIE=1.\n"
        "2. With sie.SEIE=0 it is not taken.\n"
        "3. After the environment clears it, sip.SEIP reads 0 and S-mode csrs sip.SEIP leaves it 0.",
    )
    quiet_sie(t)

    def sei() -> None:
        ro_pending(t, "SEI", "SEIP")
        L.int_window(t, ["SEI"], "S", 1, 0, 1, "ok", "SEI pending with sie.SEIE=0")

    L.with_src(t, "SEI", sei)
    tests.append(t)

    # ---- sip_ssip_sie_ssie ----
    t = new("sip_ssip_sie_ssie", pool=POOL_INT)
    t.describe(
        source=SUP,
        rule_text="Bits sip.SSIP and sie.SSIE are the interrupt-pending and interrupt-enable bits for "
        "supervisor-level software interrupts. If implemented, SSIP is writable in sip and may also be set to 1 "
        "by a platform-specific interrupt controller.",
        context=INT_CTX + " SSIP is bit 1; SSI is implemented when sie.SSIE is writable.",
        plan="If SSI is implemented:\n"
        "1. Every CSR instruction form on sip bit 1 (CSRRW with rd=x0 and rd!=x0, CSRRS/CSRRC with rs1=x0 and "
        "rs1!=x0, CSRRWI 2, CSRRSI 0 and 2, CSRRCI 2) returns the old SSIP and leaves the defined one (sie = 0).\n"
        "2. SSIP=1 with sie.SSIE=1 and SIE=1 is taken with cause 1; SSIE=0 is not taken.\n"
        "3. The framework's platform trigger (RVTEST_SET_SSW_INT_S: the platform controller if the DUT has one, "
        "otherwise mip.SSIP) also makes sip.SSIP read 1 and the interrupt taken.",
    )
    quiet_sie(t)

    def ssi() -> None:
        forms = [  # asm, old, x6, rd expected (None: not checked), new
            ("csrrs x7, sip, x0", 2, None, 2, 2),
            ("csrrw x0, sip, x6", 0, 2, None, 2),
            ("csrrw x7, sip, x6", 2, 0, 2, 0),
            ("csrrs x7, sip, x6", 0, 2, 0, 2),
            ("csrrc x7, sip, x6", 2, 2, 2, 0),
            ("csrrwi x7, sip, 2", 0, None, 0, 2),
            ("csrrsi x7, sip, 0", 2, None, 2, 2),
            ("csrrsi x7, sip, 2", 0, None, 0, 2),
            ("csrrci x7, sip, 2", 2, None, 2, 0),
        ]
        for asm, old, rs, rd, newv in forms:
            t.emit(f"csr{'s' if old else 'c'}i sip, 2")
            if rs is not None:
                t.li("x6", rs)
            lab = t.label("form")
            t.emit(f"{lab}:", 0)
            t.emit(asm)
            t.emit("csrr x8, sip")
            if rd is not None:
                t.check_masked("x7", 2, rd, lab, f"{asm} returns the old SSIP ({old})")
            exp = old if MUT == "ssip_readonly" else newv
            t.check_masked("x8", 2, exp, lab, f"{asm} leaves SSIP = {newv >> 1}")
        t.emit("csrci sip, 2")
        L.int_window(t, ["SSI"], "S", 1, 1, 1, icause(1), "SSIP set through sip")
        L.int_window(t, ["SSI"], "S", 1, 0, 1, "ok", "SSIP set, SSIE=0")
        t.comment("platform trigger")
        L.bits(t, "sie", 2, True)
        t.emit("RVTEST_SET_SSW_INT_S", 150)
        L.poll_sip(t, 2, 1)
        lab = t.label("plat")
        t.emit(f"{lab}:", 0)
        t.check_masked("x8", 2, 2, lab, "the platform SSI trigger sets sip.SSIP")
        t.li("x6", SIE)
        t.allow(1)
        t.emit("csrs sstatus, x6")
        L.delay(t)
        L.bits(t, "sstatus", SIE, False)
        t.emit("csrw sie, x0")
        t.outcome(icause(1), lab, "SSI from the platform trigger is taken", epc=False, origin="S")
        t.emit("RVTEST_CLR_SSW_INT_S", 150)
        t.emit("csrci sip, 2")

    L.with_src(t, "SSI", ssi)
    tests.append(t)

    # ---- sie_acc ----
    t = new("sie_acc", pool=POOL_INT)
    t.describe(
        source=SUP,
        rule_text="A bit in sie must be writable if the corresponding interrupt can ever become pending. Bits of "
        "sie that are not writable are read-only zero.",
        context=INT_CTX + " Here the interrupts are raised without probing first: if raising makes the sip bit "
        "read 1, the sie bit must be writable.",
        plan="1. For SSI, STI and SEI: raise it; if its sip bit reads 1, setting and clearing its sie bit reads back "
        "1 and 0. The interrupt is lowered.\n"
        "2. sie written with all ones then all zeros reads 0 (no read-only-one bit); after writing all ones, "
        "every bit that reads 1 clears again (writable).",
    )
    quiet_sie(t)
    for src, code in SRC.items():
        b = 1 << code
        t.comment(f"{src}: raise without probing")
        if src == "SSI":
            t.emit("csrsi sip, 2")
            L.poll_sip(t, b, 1)
        elif src == "STI":
            t.emit("RVTEST_SET_STIME_INT_S", 130)
            L.poll_sip(t, b, 1)
        else:
            t.emit("RVTEST_SET_SEXT_INT_S", 150)
            L.poll_sip(t, b, 1)
        t.emit("snez x8, x8  // pending seen")
        t.li("x6", b)
        t.emit("csrs sie, x6")
        t.emit("csrr x7, sie")
        t.emit("csrc sie, x6")
        t.emit(f"srli x7, x7, {code}")
        t.emit("andi x7, x7, 1")
        t.emit("seqz x6, x8")
        t.emit("or x7, x7, x6")
        lab = t.label("acc")
        t.emit(f"{lab}:", 0)
        t.check_bool("x7", lab, f"{src} became pending, so sie bit {code} is writable")
        t.emit("csrr x7, sie")
        t.check_masked("x7", b, 0, lab, f"sie bit {code} clears")
        if src == "SSI":
            t.emit("csrci sip, 2")
        elif src == "STI":
            t.emit("RVTEST_CLR_STIME_INT_S", 130)
        else:
            t.emit("RVTEST_CLR_SEXT_INT_S", 150)
        L.poll_sip(t, b, 0)
    t.li("x6", -1)
    t.emit("csrw sie, x6")
    t.emit("csrr x8, sie")
    t.emit("csrc sie, x8")
    t.emit("csrr x7, sie")
    lab = t.label("ro0")
    t.emit(f"{lab}:", 0)
    t.check("x7", 0, lab, "bits of sie that read 1 after writing ones clear again")
    t.emit("csrw sie, x0")
    t.emit("csrr x7, sie")
    t.check(
        "x7", 2 if MUT == "sie_ro_nonzero" else 0, lab, "sie written 0 reads 0 (non-writable bits are read-only zero)"
    )
    tests.append(t)

    # ---- sip_sie_bits_sz ----
    t = new("sip_sie_bits_sz")
    t.describe(
        source=SUP,
        rule_text="The standard portions (bits 15:0) of registers sip and sie are formatted as shown in Figures "
        "<<sipreg-standard>> and <<siereg-standard>> respectively.",
        context="In the figures, bits 15:0 hold only SSIP/SSIE (1), STIP/STIE (5), SEIP/SEIE (9) and "
        "LCOFIP/LCOFIE (13); the other standard bits are 0. With H, the VS-level and SGEI bits are in hip/hie, "
        "not sip/sie.",
        plan="1. sie written with all ones: bits 15:0 other than 1, 5, 9 and 13 read 0; sie is cleared.\n"
        "2. With sie = 0, sip written with all ones: bits 15:0 other than 1, 5, 9 and 13 read 0; sip is cleared.",
    )
    t.emit("csrw sie, x0")
    L.bits(t, "sstatus", SIE, False)
    for csr in ("sie", "sip"):
        lab = t.label(csr)
        t.li("x6", -1)
        t.emit(f"{lab}:", 0)
        t.emit(f"csrw {csr}, x6")
        t.emit(f"csrr x7, {csr}")
        t.emit(f"csrw {csr}, x0")
        t.check_masked("x7", STD, 0, lab, f"{csr} bits 15:0 other than 1, 5, 9, 13 read 0 after writing ones")
    tests.append(t)

    # ---- std_super_intr_impl ----
    t = new("std_super_intr_impl", pool=POOL_INT)
    t.describe(
        source=SUP,
        rule_text="Each standard interrupt type (SEI, STI, SSI, or LCOFI) might not be implemented, in which case "
        "the corresponding interrupt-pending and interrupt-enable bits are read-only zeros.",
        context=INT_CTX + " LCOFI belongs to Sscofpmf. An interrupt whose sie bit is read-only zero is treated as "
        "not implemented; its sip bit must then stay 0 when the test tries to raise it.",
        plan="For SSI, STI and SEI: if the sie bit is read-only zero, raising the interrupt leaves the sip bit 0 "
        "(checked after a 200-read wait); if it is writable, the interrupt is implemented and nothing more is "
        "required here (sie_acc, sip_sie).",
    )
    quiet_sie(t)
    for src, code in SRC.items():

        def absent(src: str = src, code: int = code) -> None:
            b = 1 << code
            if src == "SSI":
                t.emit("csrsi sip, 2")
            elif src == "STI":
                t.emit("RVTEST_SET_STIME_INT_S", 130)
            else:
                t.emit("RVTEST_SET_SEXT_INT_S", 150)
            L.poll_sip(t, b, 1)
            lab = t.label("absent")
            t.emit(f"{lab}:", 0)
            t.check("x8", 0, lab, f"{src} not implemented: sip bit {code} stays 0")

        L.probe_ie(t, src)
        t.either("x7", lambda src=src: t.comment(f"{src} implemented"), absent)
    tests.append(t)

    # ---- sip_sie_warl ----
    t = new("sip_sie_warl", pool=POOL_NO_TSBI)
    t.describe(
        source=SUP,
        rule_text="All bits in sip and sie are WARL fields.",
        context="Each bit is a separate WARL field: a writable bit holds what is written, and a read-only bit "
        "reads a fixed value. So for a write of v, the read is (v & W) | C, where C is the value read after "
        "writing zeros and W = (value read after writing ones) ^ C. Writes never trap. sie = 0 while sip is "
        "written, so no interrupt is taken.",
        plan="For sie, then sip: find C and W; then for five random values and 0x5555.../0xAAAA..., written with "
        "CSRRW, CSRRS (over the previous value) and CSRRC, the read equals the WARL prediction. Both are cleared "
        "at the end.",
    )
    t.emit("csrw sie, x0")
    L.bits(t, "sstatus", SIE, False)
    for csr in ("sie", "sip"):
        t.comment(f"{csr}: C = read after zeros (x13), W = read after ones ^ C (x14)")
        t.emit(f"csrw {csr}, x0")
        t.emit(f"csrr x13, {csr}")
        t.li("x6", -1)
        t.emit(f"csrw {csr}, x6")
        t.emit(f"csrr x14, {csr}")
        t.emit("xor x14, x14, x13")
        if MUT == "warl_ro1" and csr == "sie":
            t.emit("li x13, 4")
        vals = [t.rand_x() for _ in range(5)] + [X(0x55555555, 0x5555555555555555), X(0xAAAAAAAA, 0xAAAAAAAAAAAAAAAA)]
        for v in vals:
            for op in ("csrrw", "csrrs", "csrrc"):
                t.load("x6", v, "operand")
                t.emit(f"csrr x15, {csr}  // old")
                lab = t.label("warl")
                t.emit(f"{lab}:", 0)
                t.emit(f"{op} x0, {csr}, x6")
                t.emit(f"csrr x7, {csr}")
                if op == "csrrs":
                    t.emit("or x6, x6, x15")
                elif op == "csrrc":
                    t.emit("not x6, x6")
                    t.emit("and x6, x6, x15")
                t.emit("and x8, x6, x14")
                t.emit("not x9, x14")
                t.emit("and x9, x9, x13")
                t.emit("or x8, x8, x9")
                pred_eq(t, "x7", "x7", "x8")
                t.check_bool("x7", lab, f"{op} {csr}: the read equals (value & writable) | read-only bits")
        t.emit(f"csrw {csr}, x0")
    tests.append(t)

    # ---- sip_sie_priority_bit_order ----
    t = new("sip_sie_priority_bit_order", pool=POOL_INT)
    t.describe(
        source=SUP,
        rule_text="Multiple simultaneous interrupts destined for supervisor mode are handled in the following "
        "decreasing priority order: SEI, SSI, STI, LCOFI.",
        context=INT_CTX + " The framework handler masks each taken interrupt in sie and returns with SRET, which "
        "restores SIE=1, so the next one is taken at once; the trap log keeps the last four traps in order. "
        "LCOFI belongs to Sscofpmf.",
        plan="1. Each pair of implemented interrupts (SEI+SSI, SSI+STI, SEI+STI), pending and enabled, is taken "
        "in S-mode when SIE is set: two traps, higher priority first.\n"
        "2. All three: three traps in the order SEI, SSI, STI, in S-mode and in U-mode.",
    )
    quiet_sie(t)
    order = list(L.PRIO)
    if MUT == "sti_over_ssi":
        order = ["SEI", "STI", "SSI"]
    if MUT == "ssi_over_sei":
        order = ["SSI", "SEI", "STI"]

    def prio(srcs: list[str], mode: str) -> None:
        exp = [s for s in order if s in srcs]
        desc = f"{'+'.join(srcs)} pending in {mode}-mode"
        mask_ = sum(1 << SRC[s] for s in srcs)
        L.bits(t, "sie", mask_, True)
        for s_ in srcs:
            L.raise_int(t, s_)
        lab = t.label("prio")
        if mode == "S":
            t.li("x6", SIE)
            t.allow(len(srcs))
            t.emit(f"{lab}:", 0)
            t.emit("csrs sstatus, x6")
            L.delay(t)
        else:
            L.bits(t, "sstatus", SPIE, False)
            t.allow(len(srcs))
            t.enter("U")
            t.emit(f"{lab}:", 0)
            L.delay(t)
            t.leave()
        L.bits(t, "sstatus", SIE, False)
        t.emit("csrw sie, x0")
        multi_outcome(t, [icause(SRC[s_]) for s_ in exp], lab, desc)
        for s_ in srcs:
            L.lower_int(t, s_)

    for pair in (["SEI", "SSI"], ["SSI", "STI"], ["SEI", "STI"]):
        L.with_srcs(t, pair, lambda pair=pair: prio(pair, "S"))
    L.with_srcs(t, ["SEI", "SSI", "STI"], lambda: (prio(["SEI", "SSI", "STI"], "S"), prio(["SEI", "SSI", "STI"], "U")))
    tests.append(t)
    return tests


# ======================================================================== scounteren
CNT = {"cycle": (0xC00, 0), "time": (0xC01, 1), "instret": (0xC02, 2)}


def gen_scounteren() -> list[TestFile]:
    tests = []
    ZICNTR, ZIHPM = "defined(ZICNTR_SUPPORTED)", "defined(ZIHPM_SUPPORTED)"

    # ---- scounteren ----
    t = new("scounteren")
    t.describe(
        source=SUP,
        rule_text="The counter-enable (scounteren) CSR is a 32-bit register that controls the availability of the "
        "hardware performance monitoring counters to U-mode.",
        context="Bit 0 CY (cycle), 1 TM (time), 2 IR (instret), 3-31 HPM3-HPM31. A 32-bit register has no bits "
        "above 31, so on RV64 a read returns 0 in bits 63:32. scounteren_acc allows any bit to be read-only "
        "zero.",
        plan="1. RV64: scounteren written with all ones reads 0 in bits 63:32, and its bits 31:0 equal those read "
        "after writing 0xFFFFFFFF.\n"
        "2. Each bit that reads 1 after writing ones reads 0 after a write of that bit's complement (each bit is "
        "independent).\n"
        "scounteren is restored.",
    )
    t.emit("csrr x9, scounteren")
    t.li("x6", -1)
    t.emit("csrw scounteren, x6")
    t.emit("csrr x7, scounteren")
    lab = t.label("w")
    t.emit(f"{lab}:", 0)
    with t.rv64_only():
        t.emit("srli x8, x7, 32")
        t.check(
            "x8",
            0xFFFFFFFF if MUT == "scounteren_64bit" else 0,
            lab,
            "RV64: scounteren bits 63:32 read 0 after writing all ones",
        )
        t.li("x6", 0xFFFFFFFF)
        t.emit("slli x6, x6, 32")
        t.emit("srli x6, x6, 32")
        t.emit("csrw scounteren, x6")
        t.emit("csrr x8, scounteren")
        pred_eq(t, "x8", "x8", "x7")
        t.check_bool("x8", lab, "writing 0xFFFFFFFF gives the same value as writing all ones")
    for i in range(8):
        bit = t.rng.randrange(0, 32)
        t.li("x6", ~(1 << bit) if bit < 31 else 0x7FFFFFFF)
        t.emit("csrw scounteren, x6")
        t.emit("csrr x8, scounteren")
        t.emit(f"srli x8, x8, {bit}")
        t.emit("andi x8, x8, 1")
        t.check("x8", 0, lab, f"bit {bit} reads 0 after writing its complement")
    t.emit("csrw scounteren, x9")
    tests.append(t)

    # ---- scounteren_acc ----
    t = new("scounteren_acc")
    t.describe(
        source=SUP,
        rule_text="scounteren must be implemented. However, any of the bits may be read-only zero, indicating reads "
        "to the corresponding counter will cause an exception when executing in U-mode. Hence, they are "
        "effectively WARL fields.",
        context="Only read-only zero is allowed for a non-writable bit, so a write of v reads v & W, where W is the "
        "value read after writing all ones (bits 31:0).",
        plan="1. Every CSR form on scounteren in S-mode executes without a trap (trap window).\n"
        "2. scounteren written 0 reads 0.\n"
        "3. For six random 32-bit values written with CSRRW, CSRRS and CSRRC (over a known old value), the read "
        "equals the result masked with W. scounteren is restored.",
    )
    t.emit("csrr x9, scounteren")
    for asm in (
        "csrr x7, scounteren",
        "csrw scounteren, x9",
        "csrrs x7, scounteren, x0",
        "csrrc x7, scounteren, x0",
        "csrrsi x7, scounteren, 0",
        "csrrwi x7, scounteren, 0x5",
        "csrrci x7, scounteren, 0x5",
    ):
        win(t, "S", [asm], "ok", f"{asm} (scounteren must be implemented)")
    t.li("x6", -1)
    t.emit("csrw scounteren, x6")
    t.emit("csrr x1, scounteren  // W")
    t.emit("csrw scounteren, x0")
    t.emit("csrr x7, scounteren")
    lab = t.label("zero")
    t.emit(f"{lab}:", 0)
    t.check("x7", 0, lab, "scounteren written 0 reads 0 (no read-only-one bit)")
    for _ in range(6):
        old, v = t.rand(32), t.rand(32)
        for op in ("csrrw", "csrrs", "csrrc"):
            t.load("x6", old, "old")
            t.emit("csrw scounteren, x6")
            t.emit("csrr x8, scounteren  // old & W")
            t.load("x6", v, "operand")
            lab = t.label("acc")
            t.emit(f"{lab}:", 0)
            t.emit(f"{op} x0, scounteren, x6")
            t.emit("csrr x7, scounteren")
            if op == "csrrs":
                t.emit("or x6, x6, x8")
            elif op == "csrrc":
                t.emit("not x6, x6")
                t.emit("and x6, x6, x8")
            t.emit("and x6, x6, x1")
            pred_eq(t, "x7", "x7", "x6")
            t.check_bool("x7", lab, f"{op} scounteren reads the result masked with the writable bits")
    t.emit("csrw scounteren, x9")
    tests.append(t)

    # ---- scounteren_op ----
    def scop(part: str, suffix: str, hpms: range) -> TestFile:
        t = new("scounteren_op", required=["I", "S", "U"] + (["Zihpm"] if part == "hpm" else []))
        t.suffix = suffix
        t.describe(
            source=SUP,
            rule_text="When the CY, TM, IR, or HPMn bit in the scounteren register is clear, attempts to read the "
            "cycle, time, instret, or hpmcountern register while executing in U-mode will cause an "
            "illegal-instruction exception. When one of these bits is set, access to the corresponding register is "
            "permitted.",
            context="Note in supervisor.adoc: U-mode may only access a counter if the corresponding bits in scounteren "
            "and mcounteren are both set (machine.adoc mcounteren_clr_ill_inst_exc). mcounteren is written through "
            "T-SBI; both registers are WARL, so the expected outcome is computed from the values read back. cycle, "
            "time and instret need Zicntr; hpmcounter3-31 need Zihpm. On RV32 the high halves (cycleh, ...) are "
            "gated by the same bits.",
            plan="1. Zicntr: for cycle, time and instret (and their high halves on RV32), U-mode reads with "
            "(mcounteren, scounteren) = (all ones, all ones), (all ones, all but this bit), (all but this bit, all "
            "ones): permitted iff both bits read back 1, otherwise illegal-instruction (stval 0 or the "
            "instruction). The cases where the other bits are set check that no enable leaks between counters.\n"
            "Also (only this bit, only this bit), so a design that needs all enable bits set fails.\n"
            "2. Zihpm: for hpmcounter3-31 (and high halves on RV32), with mcounteren all ones, scounteren all ones, "
            "all but this bit, and only this bit: the same rule.\n"
            "3. scounteren does not gate S-mode: with scounteren = 0 and mcounteren all ones, S-mode reads of cycle, "
            "time and instret do not trap.\n"
            "mcounteren and scounteren are restored.",
        )
        t.doc["context"] += (
            " The rule is split over three files to keep each under the size limit: scounteren_op.S has parts 1 "
            "and 3 (cycle, time, instret), scounteren_op_hpm3.S and scounteren_op_hpm17.S have part 2 for "
            f"hpmcounter3-16 and 17-31. This file: {'parts 1 and 3' if part == 'cntr' else f'part 2, hpmcounter{hpms.start}-{hpms.stop - 1}'}."
        )
        t.extra_data += [".balign 8", "s_mcen: .dword 0"]
        t.emit("csrr x9, scounteren")
        t.tsbi_csr("READ", "MCOUNTEREN")
        t.la("x6", "s_mcen")
        t.emit("SREG a0, 0(x6)  // original mcounteren")

        def case(name: str, num: int, bit: int, mval: int | None, sval: int, note: str) -> None:
            t.comment(f"{name}: {note}")
            if mval is not None:
                t.load("a1", mval, "mcounteren")
                t.tsbi_csr("WRITE", "MCOUNTEREN", "a1")
                t.tsbi_csr("READ", "MCOUNTEREN")
            else:
                t.emit("mv a0, x1  // mcounteren, read once")
            t.load("x6", sval, "scounteren")
            t.emit("csrw scounteren, x6")
            t.emit("csrr x7, scounteren")
            if MUT == "scounteren_ignored":
                t.emit("li x7, -1")
            if MUT != "mcounteren_ignored_in_u":
                t.emit("and x7, x7, a0")
            t.emit(f"srli x7, x7, {bit}")
            t.emit("andi x7, x7, 1")
            insn = f"csrr x8, {hex(num)}  // {name}"
            enc = L.enc_csr(num, 2, 8, 0)
            t.either(
                "x7",
                lambda: win(t, "U", [insn], "ok", f"{name} with both enable bits set"),
                lambda: win(t, "U", [insn], ILLEGAL, f"{name} with an enable bit clear", [0, enc]),
            )

        ALL = 0xFFFFFFFF
        names = [(n, num, b) for n, (num, b) in CNT.items()]
        with t.only_if(ZICNTR) if part == "cntr" else discard(t):
            for n, num, b in names:
                others = ALL & ~(1 << b)
                for hi in (False, True):
                    cm = t.rv32_only() if hi else None
                    nm, nn = (n + "h", num + 0x80) if hi else (n, num)

                    def three(nm: str = nm, nn: int = nn, b: int = b, others: int = others) -> None:
                        case(nm, nn, b, ALL, ALL, "both set")
                        case(nm, nn, b, ALL, others, "scounteren bit clear, the others set")
                        case(nm, nn, b, others, ALL, "mcounteren bit clear, the others set")
                        case(nm, nn, b, 1 << b, 1 << b, "only this bit set in both")

                    if cm:
                        with cm:
                            three()
                    else:
                        three()
        with t.only_if(ZIHPM) if part == "hpm" else discard(t):
            t.load("a1", ALL, "mcounteren all ones")
            t.tsbi_csr("WRITE", "MCOUNTEREN", "a1")
            t.tsbi_csr("READ", "MCOUNTEREN")
            t.emit("mv x1, a0")
            for n in hpms:
                for hi in (False, True):
                    nm, nn = (f"hpmcounter{n}h", 0xC80 + n) if hi else (f"hpmcounter{n}", 0xC00 + n)

                    def two(nm: str = nm, nn: int = nn, n: int = n) -> None:
                        case(nm, nn, n, None, ALL, "both set")
                        case(nm, nn, n, None, ALL & ~(1 << n), "scounteren bit clear")
                        case(nm, nn, n, None, 1 << n, "only this scounteren bit set")

                    if hi:
                        with t.rv32_only():
                            two()
                    else:
                        two()
        with t.only_if(ZICNTR) if part == "cntr" else discard(t):
            t.load("a1", ALL, "mcounteren all ones")
            t.tsbi_csr("WRITE", "MCOUNTEREN", "a1")
            t.emit("csrw scounteren, x0")
            for n, num, b in names:
                t.comment(f"S-mode {n} with scounteren = 0: mcounteren decides (read back)")
                t.tsbi_csr("READ", "MCOUNTEREN")
                t.emit(f"srli x7, a0, {b}")
                t.emit("andi x7, x7, 1")
                insn = f"csrr x8, {hex(num)}  // {n}"
                enc = L.enc_csr(num, 2, 8, 0)
                t.either(
                    "x7",
                    lambda insn=insn, n=n: win(t, "S", [insn], "ok", f"{n} with scounteren = 0"),
                    lambda insn=insn, n=n, enc=enc: win(
                        t, "S", [insn], ILLEGAL, f"{n} with mcounteren bit clear", [0, enc]
                    ),
                )
        t.la("x6", "s_mcen")
        t.emit("LREG a1, 0(x6)")
        t.tsbi_csr("WRITE", "MCOUNTEREN", "a1")
        t.emit("csrw scounteren, x9")
        return t

    tests.append(scop("cntr", "", range(0)))
    tests.append(scop("hpm", "_hpm3", range(3, 17)))
    tests.append(scop("hpm", "_hpm17", range(17, 32)))
    return tests


# ======================================================================== sscratch, sepc, scause, stval
def gen_trap_csrs() -> list[TestFile]:
    tests = []
    DATA = [".balign 64", "s_d0: .dword 0, 0, 0, 0", "s_d1: .dword 0x0123456789ABCDEF, 0"]

    # ---- sscratch ----
    t = new("sscratch", pool=POOL_NO_TSBI)
    t.describe(
        source=SUP,
        rule_text="The sscratch CSR is an SXLEN-bit read/write register, dedicated for use by the supervisor.",
        context="The framework keeps its S-mode save-area pointer in sscratch, so each step writes sscratch, reads "
        "it, and restores the original value before checking (no trap can occur in between).",
        plan="Every CSR instruction form (CSRRW rd=x0 and rd!=x0, CSRRS/CSRRC rs1=x0 and rs1!=x0, CSRRWI, CSRRSI "
        "uimm=0 and !=0, CSRRCI) over full-width old values and operands: 0, all ones, 0x55.., 0xAA.., the "
        "sign bit, 1 and random values. Each returns the old value and leaves the defined value.",
    )
    t.emit("csrr x15, sscratch  // framework value")
    olds = [X(0, 0), X(0xFFFFFFFF, (1 << 64) - 1), X(0x55555555, 0x5555555555555555), X(0x80000000, 1 << 63)]
    olds += [t.rand_x() for _ in range(4)]
    # (form, funct3, source nonzero): csrrw0 has rd=x0 and rs1=x6; csrrs0 has rs1=x0; csrrsi0 has uimm=0
    forms = [
        ("csrrw", 1, True),
        ("csrrw0", 1, True),
        ("csrrs", 2, True),
        ("csrrs0", 2, False),
        ("csrrc", 3, True),
        ("csrrwi", 5, True),
        ("csrrsi", 6, True),
        ("csrrsi0", 6, False),
        ("csrrci", 7, True),
    ]
    for i, (fname, f3, nz) in enumerate(forms):
        for j in range(2):
            old = olds[(2 * i + j) % len(olds)]
            rs = X(0xAAAAAAAA, 0xAAAAAAAAAAAAAAAA) if j else t.rand_x()
            imm = 0x15 if nz else 0
            asm = {
                "csrrw": "csrrw x7, sscratch, x6",
                "csrrw0": "csrrw x0, sscratch, x6",
                "csrrs": "csrrs x7, sscratch, x6",
                "csrrs0": "csrrs x7, sscratch, x0",
                "csrrc": "csrrc x7, sscratch, x6",
                "csrrwi": f"csrrwi x7, sscratch, {imm}",
                "csrrsi": f"csrrsi x7, sscratch, {imm}",
                "csrrsi0": "csrrsi x7, sscratch, 0",
                "csrrci": f"csrrci x7, sscratch, {imm}",
            }[fname]
            res = []
            for xl in (32, 64):
                o, r = old.num(xl), rs.num(xl)
                src = r if f3 in (1, 2, 3) and nz else (imm if f3 >= 5 else 0)
                n = {1: src, 5: src, 2: o | src, 6: o | src, 3: o & ~src, 7: o & ~src}[f3]
                res.append(mask(n, xl))
            t.load("x8", old, "old")
            t.load("x6", rs, "operand")
            lab = t.label("ss")
            t.emit("csrw sscratch, x8")
            t.emit(f"{lab}:", 0)
            t.emit(asm)
            t.emit("csrr x9, sscratch")
            t.emit("csrw sscratch, x15")
            if fname != "csrrw0":
                t.check("x7", old, lab, f"{asm} returns the old sscratch")
            t.check("x9", X(*res), lab, f"{asm} leaves the defined value")
    tests.append(t)

    # ---- sepc ----
    SEPC_CTX = (
        "IALIGN is 16 when C (Zca) is implemented, else 32; the S suite assumes misa.C is not cleared, so "
        "with C, sepc[1] is held. sepc is WARL and only valid addresses must be held: values are addresses "
        "in the test image with low bits set."
    )
    t = new("sepc")
    t.extra_data += DATA
    t.describe(
        source=SUP,
        rule_text="sepc is an SXLEN-bit read/write CSR formatted as shown in <<epcreg>>. The low bit of sepc "
        "(sepc[0]) is always zero. On implementations that support only IALIGN=32, the two low bits (sepc[1:0]) "
        "are always zero.",
        context=SEPC_CTX,
        plan="1. CSRRW, CSRRS, CSRRC, CSRRSI and CSRRCI with operands touching bits 1:0 and 4:2 of a data address: "
        "each returns the old value and leaves the defined value with bit 0 cleared, and with bit 1 cleared too "
        "when C is not implemented.\n"
        "2. Writes of address+1, +2 and +3 read back address+0, +2, +2 (with C) or address (without C).",
    )
    base = "s_d0"

    def epc_mask(v: str, low: int) -> list:
        return [f"{v}+{low & ~1}"] if MUT != "sepc_bit0_kept" else [f"{v}+{low}"]

    for low in (1, 2, 3):
        t.load("x6", f"{base}+{low}", f"address + {low}")
        lab = t.label("epc")
        t.emit(f"{lab}:", 0)
        t.emit("csrw sepc, x6")
        t.emit("csrr x7, sepc")
        with t.only_if(C):
            t.check("x7", epc_mask(base, low), lab, f"sepc written address+{low} reads with bit 0 clear")
        with t.only_if(NO_C):
            t.check(
                "x7",
                base if MUT != "sepc_bit0_kept" else f"{base}+{low & 1}",
                lab,
                f"sepc written address+{low} reads with bits 1:0 clear (IALIGN=32)",
            )
    for asm, old, rs, newlow in (
        ("csrrw x7, sepc, x6", 8, 0x1E, 0x1E),
        ("csrrs x7, sepc, x6", 8, 0x13, 0x1B),
        ("csrrc x7, sepc, x6", 0x1C, 0x0C, 0x10),
        ("csrrsi x7, sepc, 0x7", 0x10, None, 0x17),
        ("csrrci x7, sepc, 0x1C", 0x1C, None, 0),
    ):
        t.load("x8", f"{base}+{old}", "old")
        t.emit("csrw sepc, x8")
        if rs is not None:
            t.load("x6", f"{base}+{rs}" if asm.startswith("csrrw") else rs, "operand")
        lab = t.label("form")
        t.emit(f"{lab}:", 0)
        t.emit(asm)
        t.emit("csrr x8, sepc")
        t.check("x7", f"{base}+{old}", lab, f"{asm} returns the old sepc")
        with t.only_if(C):
            t.check("x8", f"{base}+{newlow & ~1}", lab, f"{asm} leaves the defined value with bit 0 clear")
        with t.only_if(NO_C):
            t.check("x8", f"{base}+{newlow & ~3}", lab, f"{asm} leaves the defined value with bits 1:0 clear")
    tests.append(t)

    # ---- sepc_acc_invalid_addr ----
    t = new("sepc_acc_invalid_addr")
    t.extra_data += DATA
    t.describe(
        source=SUP,
        rule_text="sepc is a WARL register that must be able to hold all valid virtual addresses. It need not be "
        "capable of holding all possible invalid addresses. Prior to writing sepc, implementations may convert "
        "an invalid address into some other invalid address that sepc is capable of holding.",
        context="Translation is Bare in S-mode, so valid addresses are physical addresses of memory; the test uses "
        "addresses of its own code, data and signature, 4-byte aligned. Invalid addresses may be converted, so "
        "they are not checked.",
        plan="sepc written with each address (code start, a code label, data start, data words, the trap log and "
        "the signature start) reads it back exactly, through CSRRW and through a T-SBI call in between.",
    )
    here = t.label("here")
    t.emit(".p2align 2", 0)
    t.emit(f"{here}:", 0)
    for a in ("rvtest_code_begin", here, "rvtest_data_begin", "s_d0", "s_d1+8", "rvtest_trap_log", "rvtest_sig_begin"):
        t.load("x6", a, a)
        lab = t.label("va")
        t.emit(f"{lab}:", 0)
        t.emit("csrw sepc, x6")
        t.emit("csrr x7, sepc")
        t.check("x7", a, lab, f"sepc holds the valid address {a}")
    tests.append(t)

    # ---- sepc_op_trap_write ----
    t = new("sepc_op_trap_write", pool=POOL_INT)
    t.extra_data += DATA
    t.describe(
        source=SUP,
        rule_text="When a trap is taken into S-mode, sepc is written with the virtual address of the instruction "
        "that was interrupted or that encountered the exception. Otherwise, sepc is never written by the "
        "implementation, though it may be explicitly written by software.",
        context="Before each trap, sepc holds another address, so a missing write is seen. Traps into M-mode "
        "(T-SBI calls, and an ECALL from S, which the framework does not delegate) must not write sepc. The "
        "trap log records sepc at handler entry.",
        plan="1. EBREAK, an illegal instruction (UNIMP) and a misaligned LW (if it traps) in S-mode and U-mode, and "
        "an ECALL in U-mode: the logged sepc is the instruction's address.\n"
        "2. An implemented S-level interrupt taken in a loop in S-mode: the logged sepc is an address inside the "
        "loop.\n"
        "3. sepc = V; a T-SBI CSR read (a trap into M-mode) and an ECALL from S-mode (cause 9, taken in M-mode) "
        "leave sepc = V.",
    )
    quiet_sie(t)

    def junk() -> None:
        t.la("x6", "s_d1")
        t.emit("csrw sepc, x6")

    for mode in ("S", "U"):
        junk()
        win(t, mode, ["ebreak"], L.BREAKPOINT, "EBREAK", [0], self_tval=True)
        junk()
        win(t, mode, [word(L.UNIMP, "unimp")], ILLEGAL, "UNIMP", [0, L.UNIMP])
        junk()
        t.la("x6", "s_d0")
        win(t, mode, ["lw x7, 1(x6)"], ["ok", 4, 5], "misaligned LW", [0, "s_d0+1"])
    junk()
    win(t, "U", ["ecall"], L.ECALL_U, "ECALL", [0], pre=["li a0, 0x73"])

    def intr() -> None:
        junk()
        L.bits(t, "sie", 2, True)
        L.raise_int(t, "SSI")
        lo, hi = t.label("lo"), t.label("hi")
        t.li("x6", SIE)
        t.allow(1)
        t.emit(f"{lo}:", 0)
        t.emit("csrs sstatus, x6")
        L.delay(t)
        t.emit(f"{hi}:", 0)
        L.bits(t, "sstatus", SIE, False)
        t.emit("csrw sie, x0")
        t.outcome(icause(1), lo, "SSI in a loop", epc=False, origin="S")
        logged(t, "x15", "TRAPLOG_EPC")
        t.la("x6", lo)
        t.emit("sltu x7, x15, x6")
        t.la("x6", hi)
        t.emit("sltu x8, x6, x15")
        t.emit("or x7, x7, x8")
        t.emit("seqz x7, x7")
        t.check_bool("x7", lo, "sepc of the interrupt is inside the interrupted loop")
        t.emit("csrci sip, 2")

    L.with_src(t, "SSI", intr)
    junk()
    lab = t.label("mtrap")
    t.emit(f"{lab}:", 0)
    t.tsbi_csr("READ", "MSTATUS")
    t.emit("csrr x7, sepc")
    t.check("x7", lab if MUT == "sepc_written_by_m_trap" else "s_d1", lab, "a trap into M-mode (T-SBI) leaves sepc")
    junk()
    lab = win(t, "S", ["ecall"], L.ECALL_S, "ECALL (taken in M-mode)", [0], pre=["li a0, 0x73"])
    t.emit("csrr x7, sepc")
    t.check("x7", "s_d1", lab, "an ECALL from S-mode taken in M-mode leaves sepc")
    tests.append(t)
    return tests


def gen_cause_tval() -> list[TestFile]:
    tests = []
    DATA = [".balign 64", "s_d0: .dword 0, 0, 0, 0", "s_d1: .dword 0x0123456789ABCDEF, 0"]

    # ---- scause ----
    t = new("scause", pool=POOL_INT)
    t.describe(
        source=SUP,
        rule_text="The scause CSR is an SXLEN-bit read-write register formatted as shown in <<scausereg>>. When a "
        "trap is taken into S-mode, scause is written with a code indicating the event that caused the trap. "
        "Otherwise, scause is never written by the implementation, though it may be explicitly written by "
        "software.",
        context="scause is Interrupt (bit SXLEN-1) plus a WLRL Exception Code, so only legal values (codes in the "
        "scause table) are written. Traps into M-mode (T-SBI calls, an ECALL from S, which the framework does not "
        "delegate) are not traps into S-mode.",
        plan="1. Software writes of 0, 2, 3, 8, 13, interrupt|1, interrupt|5 and interrupt|9 read back.\n"
        "2. After an EBREAK in S-mode (preset scause = 13), the scause CSR reads 3; after an implemented S-level "
        "interrupt taken in S-mode, it reads interrupt | code.\n"
        "3. scause = 13; a T-SBI call and an ECALL from S-mode (both taken in M-mode) leave it 13.",
    )
    quiet_sie(t)
    for v in (0, 2, 3, 8, 13, icause(1), icause(5), icause(9)):
        t.load("x6", v, "scause value")
        lab = t.label("sc")
        t.emit(f"{lab}:", 0)
        t.emit("csrw scause, x6")
        t.emit("csrr x7, scause")
        t.check("x7", v, lab, "scause holds a written legal value")
    t.li("x6", 13)
    t.emit("csrw scause, x6")
    lab = win(t, "S", ["ebreak"], L.BREAKPOINT, "EBREAK", [0], self_tval=True)
    t.emit("csrr x7, scause")
    t.check("x7", 3, lab, "scause reads 3 after the EBREAK trap")
    for src, code in SRC.items():

        def b(src: str = src, code: int = code) -> None:
            lab = L.int_window(t, [src], "S", 1, 1, 1, icause(code), f"{src}")
            t.emit("csrr x7, scause")
            t.check("x7", icause(code), lab, f"scause reads interrupt | {code} after {src}")

        L.with_src(t, src, b)
    t.li("x6", 13)
    t.emit("csrw scause, x6")
    lab = t.label("m")
    t.emit(f"{lab}:", 0)
    t.tsbi_csr("READ", "MSTATUS")
    t.emit("csrr x7, scause")
    t.check("x7", 13, lab, "a trap into M-mode (T-SBI) leaves scause")
    lab = win(t, "S", ["ecall"], L.ECALL_S, "ECALL (taken in M-mode)", [0], pre=["li a0, 0x73"])
    t.emit("csrr x7, scause")
    t.check("x7", 13, lab, "an ECALL from S-mode taken in M-mode leaves scause")
    tests.append(t)

    # ---- scause_interrupt ----
    t = new("scause_interrupt", pool=POOL_INT)
    t.describe(
        source=SUP,
        rule_text="The Interrupt bit in the scause register is set if the trap was caused by an interrupt. The "
        "Exception Code field contains a code identifying the last exception or interrupt.",
        context=INT_CTX,
        plan="1. Each implemented S-level interrupt, taken in S-mode and in U-mode: scause = interrupt bit (SXLEN-1) "
        "| its code.\n"
        "2. EBREAK and an illegal instruction in S-mode, preceded by an interrupt (so the Interrupt bit was 1): "
        "scause = 3 and 2, Interrupt bit clear.",
    )
    quiet_sie(t)
    wrong = MUT == "scause_no_int_bit"
    for src, code in SRC.items():

        def b(src: str = src, code: int = code) -> None:
            for mode in ("S", "U"):
                L.int_window(t, [src], mode, 1, 1, 1, code if wrong else icause(code), f"{src} in {mode}-mode")
            win(t, "S", ["ebreak"], L.BREAKPOINT, f"EBREAK after {src}", [0], self_tval=True)
            L.int_window(t, [src], "S", 1, 1, 1, code if wrong else icause(code), f"{src} in S-mode")
            win(t, "S", [word(L.UNIMP, "unimp")], ILLEGAL, f"UNIMP after {src}", [0, L.UNIMP])

        L.with_src(t, src, b)
    tests.append(t)

    # ---- scause_exception_code_acc / _sz ----
    t = new("scause_exception_code_acc")
    t.describe(
        source=SUP,
        rule_text="The Exception Code is a WLRL field.",
        context="A WLRL field holds every legal value written to it; writes of illegal values may trap or be "
        "replaced, so only legal values are written. The legal values are the codes of the scause table: "
        "exceptions 0-9, 12, 13, 15, 18, 19 and interrupts 1, 5, 9, 13.",
        plan="Each legal code, with the Interrupt bit clear for exceptions and set for interrupts, written with CSRRW "
        "reads back exactly; then the same values through CSRRS/CSRRC from 0.",
    )
    legal = [c for c in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 13, 15, 18, 19)] + [icause(c) for c in (1, 5, 9, 13)]
    for v in legal:
        t.load("x6", v, "code")
        lab = t.label("wl")
        t.emit(f"{lab}:", 0)
        t.emit("csrw scause, x6")
        t.emit("csrr x7, scause")
        t.check("x7", v, lab, "scause holds a legal value written with CSRRW")
        t.emit("csrw scause, x0")
        t.emit("csrs scause, x6")
        t.emit("csrr x7, scause")
        t.check("x7", v, lab, "scause holds a legal value written with CSRRS")
        t.emit("csrc scause, x6")
        t.emit("csrr x7, scause")
        t.check("x7", 0, lab, "CSRRC of the same value clears scause")
    tests.append(t)

    t = new("scause_exception_code_sz")
    t.describe(
        source=SUP,
        rule_text="It is required to hold the values 0–31 (i.e., bits 4–0 must be implemented), but otherwise it "
        "is only guaranteed to hold supported exception codes.",
        context="The Interrupt bit is a separate read/write field, so the 32 codes are written with it clear and "
        "with it set.",
        plan="scause written with every code 0-31, with the Interrupt bit clear and set, reads back exactly.",
    )
    for intr in (0, 1):
        for c in range(32):
            v = X((1 << 31) | c, (1 << 63) | c) if intr else c
            t.load("x6", v, "value")
            lab = t.label("sz")
            t.emit(f"{lab}:", 0)
            t.emit("csrw scause, x6")
            t.emit("csrr x7, scause")
            exp = v
            if MUT == "scause_4bit_code" and c >= 16:
                exp = X((1 << 31) | (c & 15), (1 << 63) | (c & 15)) if intr else c & 15
            t.check("x7", exp, lab, f"scause holds code {c} with Interrupt={intr}")
    tests.append(t)

    # ---- scause_exccode_enc_tbl ----
    t = new("scause_exccode_enc_tbl", pool=POOL_INT)
    t.extra_data += DATA
    t.describe(
        source=SUP,
        rule_text="Supervisor cause (scause) register values after trap: Interrupt 1: 1 supervisor software, 5 "
        "supervisor timer, 9 supervisor external, 13 counter-overflow interrupt (others reserved or platform). "
        "Interrupt 0: 0 instruction address misaligned, 1 instruction access fault, 2 illegal instruction, 3 "
        "breakpoint, 4 load address misaligned, 5 load access fault, 6 store/AMO address misaligned, 7 store/AMO "
        "access fault, 8 environment call from U-mode, 9 environment call from S-mode, 12 instruction page "
        "fault, 13 load page fault, 15 store/AMO page fault, 18 software check, 19 hardware error.",
        context="Causes reachable from S/U-mode without virtual memory or a platform memory map: interrupts 1, 5, 9 "
        "(when implemented); exceptions 0 (only without C: a jump to a 2-byte-aligned target), 2, 3, 4 or 5 "
        "(misaligned load, if it traps), 6 or 7 (misaligned store) and 8. Cause 9 is not delegated by the "
        "framework (ECALL from S is checked in M-mode by ecall_priv_mode_op); page faults are tested by the Sv "
        "suite, counter overflow by Sscofpmf, 18 by Zicfilp/Zicfiss.",
        plan="1. UNIMP (cause 2) and EBREAK (3) in S and U; ECALL in U (8), with C.EBREAK (3) when C is "
        "implemented.\n"
        "2. Misaligned LW at +1 and SW at +2: no trap, or cause 4/5 and 6/7.\n"
        "3. Without C: JALR to a target with bit 1 set: cause 0.\n"
        "4. Each implemented S-level interrupt: cause interrupt | 1, 5 or 9.",
    )
    quiet_sie(t)
    for mode in ("S", "U"):
        win(t, mode, [word(L.UNIMP, "unimp")], ILLEGAL, "UNIMP", [0, L.UNIMP])
        win(t, mode, ["ebreak"], L.BREAKPOINT, "EBREAK", [0], self_tval=True)
        with t.only_if(C):
            win(
                t,
                mode,
                [".hword 0x9002  // c.ebreak", ".hword 0x0001  // c.nop"],
                L.BREAKPOINT,
                "C.EBREAK",
                [0],
                self_tval=True,
            )
        t.la("x6", "s_d0")
        win(t, mode, ["lw x7, 1(x6)"], ["ok", 4, 5], "misaligned LW", [0, "s_d0+1"])
        t.la("x6", "s_d0")
        win(t, mode, ["sw x7, 2(x6)"], ["ok", 6, 7], "misaligned SW", [0, "s_d0+2"])
    win(t, "U", ["ecall"], 9 if MUT == "ecall_u_cause_9" else L.ECALL_U, "ECALL", [0], pre=["li a0, 0x73"])
    with t.only_if(NO_C):
        tg = t.label("mtgt")
        t.la("x6", tg)
        t.la("x1", tg)
        win(t, "S", ["jalr x0, 2(x6)", "nop", f"{tg}:"], 0, "JALR to a 2-byte-aligned target", [0, f"{tg}+2"])
    for src, code in SRC.items():
        L.with_src(t, src, lambda src=src, code=code: L.int_window(t, [src], "S", 1, 1, 1, icause(code), f"{src}"))
    tests.append(t)

    # ---- stval ----
    t = new("stval")
    t.extra_data += DATA
    t.describe(
        source=SUP,
        rule_text="The stval CSR is an SXLEN-bit read-write register formatted as shown in <<stvalreg>>. When a "
        "trap is taken into S-mode, stval is written with exception-specific information to assist software in "
        "handling the trap. Otherwise, stval is never written by the implementation, though it may be explicitly "
        "written by software. The hardware platform will specify which exceptions must set stval informatively, "
        "which may unconditionally set it to zero, and which may exhibit either behavior, depending on the "
        "underlying event that caused the exception.",
        context="stval is WARL for addresses (stval_acc), so software writes use 0 and valid addresses. Which "
        "exceptions write nonzero values is platform-defined, so trap values are checked as 0 or the defined "
        "datum.",
        plan="1. CSRRW/CSRRS/CSRRC with 0 and valid addresses read back.\n"
        "2. An ECALL from U (preset stval = an address) writes the CSR: the stval CSR reads 0 afterwards.\n"
        "3. A trap into M-mode (T-SBI call, ECALL from S) leaves stval unchanged.",
    )
    for v in (0, "s_d0", "s_d1+8", "rvtest_code_begin"):
        t.load("x6", v, "value")
        lab = t.label("sv")
        t.emit(f"{lab}:", 0)
        t.emit("csrw stval, x6")
        t.emit("csrr x7, stval")
        t.check("x7", v, lab, f"stval holds {v}")
    t.la("x6", "s_d0")
    t.emit("csrw stval, x0")
    t.emit("csrs stval, x6")
    t.emit("csrr x7, stval")
    t.check("x7", "s_d0", lab, "CSRRS sets stval")
    t.emit("csrc stval, x6")
    t.emit("csrr x7, stval")
    t.check("x7", 0, lab, "CSRRC clears stval")
    t.la("x6", "s_d1")
    t.emit("csrw stval, x6")
    lab = win(t, "U", ["ecall"], L.ECALL_U, "ECALL", [0], pre=["li a0, 0x73"])
    t.emit("csrr x7, stval")
    t.check("x7", "s_d1" if MUT == "stval_ecall_kept" else 0, lab, "the stval CSR reads 0 after the ECALL trap")
    t.la("x6", "s_d1")
    t.emit("csrw stval, x6")
    lab = t.label("m")
    t.emit(f"{lab}:", 0)
    t.tsbi_csr("READ", "MSTATUS")
    t.emit("csrr x7, stval")
    t.check("x7", "s_d1", lab, "a trap into M-mode (T-SBI) leaves stval")
    lab = win(t, "S", ["ecall"], L.ECALL_S, "ECALL (taken in M-mode)", [0], pre=["li a0, 0x73"])
    t.emit("csrr x7, stval")
    t.check("x7", "s_d1", lab, "an ECALL from S-mode taken in M-mode leaves stval")
    tests.append(t)

    def preset_tval(t: TestFile) -> None:
        t.la("x6", "s_d1")
        t.emit("csrw stval, x6")

    # ---- stval_op_faulting_addr ----
    t = new("stval_op_faulting_addr")
    t.extra_data += DATA
    t.describe(
        source=SUP,
        rule_text="If stval is written with a nonzero value when a breakpoint, address-misaligned, access-fault, "
        "page-fault, or hardware-error exception occurs on an instruction fetch, load, or store, then stval will "
        "contain the faulting virtual address.",
        context="Reachable here: breakpoints (EBREAK, C.EBREAK: the faulting address is the instruction's), "
        "misaligned loads and stores (which may also succeed or raise an access fault) and, without C, "
        "misaligned instruction fetch targets. Page faults are tested by the Sv suite; access faults need a "
        "platform memory map. stval is preset to another address before each trap.",
        plan="In S-mode and U-mode: EBREAK (and C.EBREAK with C): stval 0 or the instruction's address. LW at "
        "+1, LH at +1, LW at +2 and SW at +1, +3 (offsets from an aligned word): no trap, or a misaligned/access "
        "fault with stval 0 or the access address. Without C: JALR to target+2: cause 0, stval 0 or target+2.",
    )
    bp = "stval_breakpoint_next"
    for mode in ("S", "U"):
        preset_tval(t)
        if bp == MUT:
            lab0 = t.label("bpn")
            win(t, mode, ["ebreak", f"{lab0}:"], L.BREAKPOINT, "EBREAK", [0, lab0])
        else:
            win(t, mode, ["ebreak"], L.BREAKPOINT, "EBREAK", [0], self_tval=True)
        with t.only_if(C):
            preset_tval(t)
            win(
                t,
                mode,
                [".hword 0x9002  // c.ebreak", ".hword 0x0001  // c.nop"],
                L.BREAKPOINT,
                "C.EBREAK",
                [0],
                self_tval=True,
            )
        for insn, off, exc in (
            ("lw x7", 1, [4, 5]),
            ("lh x7", 1, [4, 5]),
            ("lw x7", 2, [4, 5]),
            ("sw x7", 1, [6, 7]),
            ("sw x7", 3, [6, 7]),
        ):
            preset_tval(t)
            t.la("x6", "s_d0")
            alts: list[Value] = ["ok", *exc]
            win(
                t,
                mode,
                [f"{insn}, {off}(x6)"],
                alts,
                f"misaligned {insn.split()[0].upper()} at +{off}",
                [0, f"s_d0+{off}"],
            )
    with t.only_if(NO_C):
        tg = t.label("mtgt")
        preset_tval(t)
        t.la("x6", tg)
        t.la("x1", tg)
        win(t, "S", ["jalr x0, 2(x6)", "nop", f"{tg}:"], 0, "JALR to a 2-byte-aligned target", [0, f"{tg}+2"])
    tests.append(t)

    # ---- stval_op_breakpoint ----
    t = new("stval_op_breakpoint")
    t.extra_data += DATA
    t.describe(
        source=SUP,
        rule_text="On a breakpoint exception raised by an EBREAK or C.EBREAK instruction, stval is written with "
        "either zero or the virtual address of the instruction.",
        context="stval is preset to another address before each trap. C.EBREAK needs C (Zca); it is followed by "
        "C.NOP so the code stays aligned.",
        plan="EBREAK and C.EBREAK in S-mode and U-mode, twice each: cause 3, sepc and stval 0 or the instruction "
        "address.",
    )
    for mode in ("S", "U"):
        for _ in range(2):
            preset_tval(t)
            if bp == MUT:
                lab0 = t.label("bpn")
                win(t, mode, ["ebreak", f"{lab0}:"], L.BREAKPOINT, "EBREAK", [0, lab0])
            else:
                win(t, mode, ["ebreak"], L.BREAKPOINT, "EBREAK", [0], self_tval=True)
            with t.only_if(C):
                preset_tval(t)
                win(
                    t,
                    mode,
                    [".hword 0x9002  // c.ebreak", ".hword 0x0001  // c.nop"],
                    L.BREAKPOINT,
                    "C.EBREAK",
                    [0],
                    self_tval=True,
                )
    tests.append(t)

    # ---- stval_op_illegal_instr / _format ----
    ILL = [
        (L.UNIMP, "unimp (csrrw x0, cycle, x0)"),
        (0xC0101073, "csrrw x0, time, x0"),
        (L.enc_csr(0x300, 2, 7, 0), "csrr x7, mstatus"),
        (0xF1401073, "csrrw x0, mhartid, x0"),
        (0x30200073, "mret"),
    ]
    ILL_U = [(L.enc_csr(0x100, 2, 7, 0), "csrr x7, sstatus"), (L.SRET, "sret")]
    CD = "(defined(C_SUPPORTED) || defined(ZCA_SUPPORTED)) && defined(D_SUPPORTED)"
    t = new("stval_op_illegal_instr")
    t.extra_data += DATA
    t.describe(
        source=SUP,
        rule_text="The stval register can optionally also be used to return the faulting instruction bits on an "
        "illegal-instruction exception (sepc points to the faulting instruction in memory). If stval is written "
        "with a nonzero value when an illegal-instruction exception occurs, then stval will contain the shortest "
        "of: the actual faulting instruction, the first ILEN bits of the faulting instruction, the first SXLEN "
        "bits of the faulting instruction.",
        context="Here ILEN = 32 (no longer instructions), so stval is 0 or the instruction: 32 bits for a 32-bit "
        "instruction and 16 bits (not the following parcel) for a 16-bit one. The 16-bit case needs an encoding "
        "that must trap: reserved encodings (e.g. C.LWSP rd=x0) are UNSPECIFIED without Ssstrict, so it uses "
        "C.FLDSP f0, 0(sp) (0x2002) with sstatus.FS=Off (C and D), followed by C.NOP, so a 32-bit read would "
        "include 0x0001 in bits 31:16. stval is preset to an address before each trap.",
        plan="1. In S-mode and U-mode: UNIMP, CSRRW to time, M-level CSR reads/writes and MRET: stval 0 or the "
        "32-bit instruction; in U-mode also an S-level CSR read and SRET.\n"
        "2. With C and D, FS=Off: C.FLDSP (0x2002) in S and U: stval 0 or 0x2002. FS is set to Dirty afterwards.",
    )
    for mode in ("S", "U"):
        for e, nm in ILL + (ILL_U if mode == "U" else []):
            preset_tval(t)
            win(t, mode, [word(e, nm)], ILLEGAL, nm, [0, e])
        with t.only_if(CD):
            preset_tval(t)
            L.bits(t, "sstatus", FS, False)
            bad = [0, 0x00012002] if MUT == "stval_16bit_with_next" else [0, 0x2002]
            win(
                t,
                mode,
                [".hword 0x2002  // c.fldsp f0, 0(sp) with FS=Off", ".hword 0x0001  // c.nop"],
                ILLEGAL,
                "C.FLDSP with FS=Off",
                bad,
            )
            L.bits(t, "sstatus", FS, True)
    tests.append(t)

    t = new("stval_op_illegal_instr_format")
    t.extra_data += DATA
    t.describe(
        source=SUP,
        rule_text="On an illegal-instruction exception, the instruction bits are zero-extended and loaded into stval.",
        context="Instructions with bit 31 set distinguish zero- from sign-extension on RV64 (and the 16-bit case "
        "on both XLENs). stval may also be 0 (stval_op_illegal_instr).",
        plan="In S-mode and U-mode: UNIMP (0xC0001073), CSRRW to time (0xC0101073) and to mhartid (0xF1401073): "
        "stval 0 or the zero-extended bits. With C and D and sstatus.FS=Off, C.FLDSP (0x2002) and C.FSDSP "
        "(0xA002, bit 15 set), each followed by C.NOP, must trap (FP state off): stval 0 or the zero-extended 16 "
        "bits. FS is set to Dirty afterwards. (Reserved 16-bit encodings are UNSPECIFIED without Ssstrict, so "
        "they are not used.)",
    )
    for mode in ("S", "U"):
        for e, nm in ((L.UNIMP, "unimp"), (0xC0101073, "csrrw x0, time, x0"), (0xF1401073, "csrrw x0, mhartid, x0")):
            preset_tval(t)
            sx = X(e, e | 0xFFFFFFFF00000000)
            win(t, mode, [word(e, nm)], ILLEGAL, nm, [0, sx] if MUT == "stval_sign_extended" else [0, e])
        with t.only_if(CD):
            for h, nm in ((0x2002, "c.fldsp f0, 0(sp) with FS=Off"), (0xA002, "c.fsdsp f0, 0(sp) with FS=Off")):
                preset_tval(t)
                L.bits(t, "sstatus", FS, False)
                hx = (
                    [0, X(0xFFFF0000 | h, 0xFFFFFFFFFFFF0000 | h)]
                    if MUT == "stval_sign_extended" and h & 0x8000
                    else [0, h]
                )
                win(t, mode, [f".hword {hex(h)}  // {nm}", ".hword 0x0001  // c.nop"], ILLEGAL, nm, hx)
                L.bits(t, "sstatus", FS, True)
    tests.append(t)

    # ---- stval_op_other_traps ----
    t = new("stval_op_other_traps", pool=POOL_INT)
    t.extra_data += DATA
    t.describe(
        source=SUP,
        rule_text="For other traps, stval is set to zero, but a future standard may redefine stval's setting for "
        "other traps.",
        context="Other traps are those not listed for stval (address faults, breakpoints, illegal instructions, "
        "software checks): here ECALL from U-mode and interrupts. stval is preset to an address before each "
        "trap.",
        plan="1. ECALL from U-mode, twice: stval 0.\n"
        "2. Each implemented S-level interrupt taken in S-mode and in U-mode: stval 0.",
    )
    quiet_sie(t)
    for _ in range(2):
        preset_tval(t)
        win(t, "U", ["ecall"], L.ECALL_U, "ECALL", ["s_d1"] if MUT == "stval_ecall_kept" else [0], pre=["li a0, 0x73"])
    for src, code in SRC.items():

        def b(src: str = src, code: int = code) -> None:
            for mode in ("S", "U"):
                preset_tval(t)
                lab = L.int_window(t, [src], mode, 1, 1, 1, icause(code), f"{src} in {mode}-mode")
                logged(t, "x15", "TRAPLOG_TVAL")
                t.check("x15", 0, lab, f"stval is 0 after {src}")

        L.with_src(t, src, b)
    tests.append(t)

    # ---- stval_acc ----
    t = new("stval_acc")
    t.extra_data += DATA
    t.describe(
        source=SUP,
        rule_text="stval is a WARL register that must be able to hold all valid virtual addresses and the value 0. "
        "It need not be capable of holding all possible invalid addresses.",
        context="Translation is Bare in S-mode, so valid addresses are physical addresses of memory: the test's "
        "code, data, trap log and signature, at byte granularity.",
        plan="stval written with 0 and with addresses of code, data and the signature, including odd byte "
        "addresses, reads back exactly.",
    )
    for v in (
        0,
        "rvtest_code_begin",
        "rvtest_code_begin+1",
        "rvtest_data_begin+3",
        "s_d0+5",
        "s_d1+15",
        "rvtest_trap_log",
        "rvtest_sig_begin+7",
        0,
    ):
        t.load("x6", v, "value")
        lab = t.label("sv")
        t.emit(f"{lab}:", 0)
        t.emit("csrw stval, x6")
        t.emit("csrr x7, stval")
        t.check("x7", v, lab, f"stval holds {v}")
    tests.append(t)

    # ---- stval_instr_bits_sz ----
    t = new("stval_instr_bits_sz")
    t.extra_data += DATA
    t.describe(
        source=SUP,
        rule_text="If the feature to return the faulting instruction bits is implemented, stval must also be able "
        "to hold all values less than 2^N, where N is the smaller of SXLEN and ILEN.",
        context="ILEN = 32 here, so N = 32. The feature is probed with an illegal instruction (UNIMP in S-mode): a "
        "nonzero stval means it is implemented.",
        plan="Probe with UNIMP. If stval was nonzero: stval written with 0xFFFFFFFF, 0x80000000, 0x7FFFFFFF, "
        "0xC0001073, 1 and three random 32-bit values reads each back exactly (zero-extended on RV64).",
    )
    lab = win(t, "S", [word(L.UNIMP, "unimp")], ILLEGAL, "UNIMP (probe)", [0, L.UNIMP])
    t.emit("csrr x7, stval")
    t.emit("snez x7, x7")

    def sz() -> None:
        for v in [0xFFFFFFFF, 0x80000000, 0x7FFFFFFF, 0xC0001073, 1] + [t.rand(32) for _ in range(3)]:
            t.load("x6", X(v, v), "value < 2^32")
            lab = t.label("sv")
            t.emit(f"{lab}:", 0)
            t.emit("csrw stval, x6")
            t.emit("csrr x8, stval")
            t.check("x8", X(v, v), lab, f"stval holds {hex(v)}")

    t.either("x7", sz, lambda: t.comment("illegal-instruction stval is 0: the feature is not implemented"))
    tests.append(t)
    return tests


# ======================================================================== senvcfg
CBO_DATA = [".balign 4096", "s_cbo_blk: .fill 512, 8, 0x1111111111111111"]
ENV_CTX = (
    "senvcfg (0x10A) exists from privileged spec 1.12 (S1P12P0_OR_LATER_SUPPORTED). menvcfg is reached "
    "through T-SBI. The framework boots with menvcfg and senvcfg CBIE=11, CBCFE=1, CBZE=1; tests restore "
    "that. CBO instructions are .word encodings with rs1=x6 (CBO.ZERO 0x0040200F|rs1<<15, CBO.CLEAN "
    "0x0010200F|..., CBO.FLUSH 0x0020200F|..., CBO.INVAL 0x0000200F|...). Their operand is a 4 KiB-aligned, "
    "4 KiB data block used for nothing else, so it holds any cache block size up to 4 KiB."
)
FIELD = {"zero": (L.CBZE, 7), "clean": (L.CBCFE, 6), "flush": (L.CBCFE, 6), "inval": (L.CBIE, 4)}


def env_restore(t: TestFile) -> None:
    t.comment("restore menvcfg and senvcfg CBIE=11, CBCFE=1, CBZE=1")
    t.tsbi_csr("SET", "MENVCFG", imm=L.CBIE | L.CBCFE | L.CBZE)
    L.bits(t, "CSR_SENVCFG", L.CBIE | L.CBCFE | L.CBZE, True)


def cbo_case(t: TestFile, op: str, mval: int, sval: int, check_s: bool = True, data: bool = True) -> None:
    """menvcfg field = mval, senvcfg field = sval (shifted values), then op in S-mode (if check_s) and U-mode. The
    expected outcome is computed from the values read back (both fields are WARL)."""
    f, sh = FIELD[op]
    enc = L.cbo(op, 6)
    t.comment(f"CBO.{op.upper()}: menvcfg field {mval >> sh:#04b}, senvcfg field {sval >> sh:#04b}")
    t.tsbi_csr("CLEAR", "MENVCFG", imm=f)
    if mval:
        t.tsbi_csr("SET", "MENVCFG", imm=mval)
    t.tsbi_csr("READ", "MENVCFG")
    t.emit(f"srli x8, a0, {sh}")
    t.emit(f"andi x8, x8, {f >> sh}")
    L.bits(t, "CSR_SENVCFG", f, False)
    if sval:
        L.bits(t, "CSR_SENVCFG", sval, True)
    t.emit("csrr x7, CSR_SENVCFG")
    t.emit(f"srli x7, x7, {sh}")
    t.emit(f"andi x7, x7, {f >> sh}")
    if op == "inval":
        t.emit("snez x8, x8  // S-mode enabled: menvcfg.CBIE != 00")
        t.emit("andi x7, x7, 1  // senvcfg.CBIE is 01 or 11")
    if check_s:
        t.la("x6", "s_cbo_blk")
        t.either(
            "x8",
            lambda: win(t, "S", [word(enc, f"cbo.{op} (x6)")], "ok", f"CBO.{op.upper()} enabled by menvcfg"),
            lambda: win(
                t, "S", [word(enc, f"cbo.{op} (x6)")], ILLEGAL, f"CBO.{op.upper()} disabled by menvcfg", [0, enc]
            ),
        )
    if f"{'cbze' if op == 'zero' else 'cbie' if op == 'inval' else 'x'}_ignores_menvcfg" != MUT:
        t.emit("and x7, x7, x8")
    if MUT == "cbcfe_ignores_senvcfg" and op in ("clean", "flush"):
        t.emit("mv x7, x8")

    def ok() -> None:
        if op == "zero" and data:
            t.la("x6", "s_cbo_blk")
            t.li("x8", 0x5A5A)
            t.emit("SREG x8, 0(x6)")
        t.la("x6", "s_cbo_blk")
        lab = win(t, "U", [word(enc, f"cbo.{op} (x6)")], "ok", f"CBO.{op.upper()} enabled")
        if op == "zero" and data:
            t.emit("LREG x8, 0(x6)")
            t.check("x8", 0, lab, "U-mode CBO.ZERO zeroed the block")

    def bad() -> None:
        if op == "zero" and data:
            t.la("x6", "s_cbo_blk")
            t.li("x8", 0x5A5A)
            t.emit("SREG x8, 0(x6)")
        t.la("x6", "s_cbo_blk")
        lab = win(t, "U", [word(enc, f"cbo.{op} (x6)")], ILLEGAL, f"CBO.{op.upper()} disabled", [0, enc])
        if op == "zero" and data:
            t.emit("LREG x8, 0(x6)")
            t.check("x8", 0x5A5A, lab, "a trapping CBO.ZERO leaves the block")

    t.either("x7", ok, bad)


def gen_senvcfg() -> list[TestFile]:
    tests = []
    ZICBOZ, ZICBOM = "Zicboz", "Zicbom"

    # ---- senvcfg ----
    t = new("senvcfg")
    t.describe(
        source=SUP,
        rule_text="The senvcfg CSR is an SXLEN-bit read/write register, formatted as shown in <<senvcfg>>, that "
        "controls certain characteristics of the U-mode execution environment.",
        context=ENV_CTX + " Fields: FIOM (0), LPE (2), SSE (3), CBIE (5:4), CBCFE (6), CBZE (7), PMM (33:32, RV64); "
        "the other bits are WPRI (read-only zero when not furnished). LPE, SSE and PMM belong to Zicfilp, "
        "Zicfiss and Ssnpm and are never written. FIOM, CBCFE and CBZE are one-bit fields (each writable or "
        "read-only zero), so a write of v reads (v & W) | C, with W and C found by writing ones and zeros.",
        plan="1. Reads and writes of senvcfg in S-mode do not trap.\n"
        "2. Writing ones to every WPRI bit (keeping the other fields) reads them 0.\n"
        "3. FIOM, CBCFE and CBZE through CSRRW, CSRRS and CSRRC with every combination of the three bits: the "
        "read equals (v & W) | C.\n"
        "senvcfg is restored.",
    )
    with t.only_if(S1P12):
        win(t, "S", ["csrr x7, CSR_SENVCFG"], "ok", "read of senvcfg")
        t.emit("csrr x9, CSR_SENVCFG")
        win(t, "S", ["csrw CSR_SENVCFG, x9"], "ok", "write of senvcfg")
        t.emit("csrr x6, CSR_SENVCFG")
        t.load("x7", L.ENV_WPRI, "WPRI bits")
        t.emit("or x6, x6, x7")
        lab = t.label("wpri")
        t.emit(f"{lab}:", 0)
        t.emit("csrw CSR_SENVCFG, x6")
        t.emit("csrr x7, CSR_SENVCFG")
        t.emit("csrw CSR_SENVCFG, x9")
        t.check_masked("x7", L.ENV_WPRI, 0, lab, "WPRI bits of senvcfg read 0 after writing ones")
        B = L.FIOM | L.CBCFE | L.CBZE
        L.bits(t, "CSR_SENVCFG", B, False)
        t.emit("csrr x1, CSR_SENVCFG")
        t.li("x6", B)
        t.emit("and x1, x1, x6  // C")
        t.emit("csrs CSR_SENVCFG, x6")
        t.emit("csrr x8, CSR_SENVCFG")
        t.emit("and x8, x8, x6")
        t.emit("xor x8, x8, x1  // W")
        for v in range(8):
            val = (L.FIOM if v & 1 else 0) | (L.CBCFE if v & 2 else 0) | (L.CBZE if v & 4 else 0)
            for op in ("csrrw", "csrrs", "csrrc"):
                L.bits(t, "CSR_SENVCFG", B, op == "csrrc")
                if op == "csrrw":
                    t.emit("csrr x6, CSR_SENVCFG")
                    t.li("x7", ~B)
                    t.emit("and x6, x6, x7")
                    if val:
                        t.li("x7", val)
                        t.emit("or x6, x6, x7")
                else:
                    t.li("x6", val)
                lab = t.label("f")
                t.emit(f"{lab}:", 0)
                t.emit(f"{op} x0, CSR_SENVCFG, x6")
                t.emit("csrr x7, CSR_SENVCFG")
                exp_v = val if op != "csrrc" else (B & ~val)
                t.li("x6", exp_v)
                t.emit("and x6, x6, x8")
                t.emit("not x9, x8")
                t.emit("and x9, x9, x1")
                t.emit("or x6, x6, x9")
                t.li("x9", B)
                t.emit("and x7, x7, x9")
                pred_eq(t, "x7", "x7", "x6")
                t.check_bool("x7", lab, f"{op} with FIOM/CBCFE/CBZE = {v:03b}: read equals (v & W) | C")
        env_restore(t)
        L.bits(t, "CSR_SENVCFG", L.FIOM, False)
    tests.append(t)

    # ---- senvcfg_fiom_acc (M part) ----
    t = new_sm("senvcfg_fiom_acc")
    t.describe(
        source=SUP,
        rule_text="If satp.MODE is read-only zero (always Bare), the implementation may make FIOM read-only zero.",
        context="So when satp.MODE is not read-only zero, FIOM is a writable field. Whether satp.MODE is read-only "
        "zero is found by writing each non-Bare MODE from M-mode, where satp does not translate (an _Sm file).",
        plan="1. Probe satp.MODE from M-mode; restore satp.\n"
        "2. Set senvcfg.FIOM and read it: if some MODE was held, FIOM reads 1 (a read-only-zero FIOM is allowed "
        "only with a read-only-zero satp.MODE). Clear FIOM.",
    )
    with t.only_if(S1P12):
        satp_probe(t)
        t.emit("snez x8, x8")
        L.bits(t, "CSR_SENVCFG", L.FIOM, True)
        t.emit("csrr x7, CSR_SENVCFG")
        L.bits(t, "CSR_SENVCFG", L.FIOM, False)
        t.emit("andi x7, x7, 1")
        t.emit("seqz x8, x8")
        t.emit("or x7, x7, x8")
        lab = t.label("fiom")
        t.emit(f"{lab}:", 0)
        t.check_bool("x7", lab, "FIOM is writable unless satp.MODE is read-only zero")
    tests.append(t)

    # ---- CBZE ----
    def field_rw(t: TestFile, f: int, nm: str, vals: list[int]) -> None:
        for v in vals:
            L.bits(t, "CSR_SENVCFG", f, False)
            if v:
                L.bits(t, "CSR_SENVCFG", v, True)
            lab = t.label(nm.lower())
            t.emit(f"{lab}:", 0)
            t.emit("csrr x7, CSR_SENVCFG")
            t.check_masked("x7", f, v, lab, f"senvcfg.{nm} reads {hex(v)} after writing it")

    t = new("senvcfg_cbze", required=["I", "S", ZICBOZ])
    t.describe(
        source=SUP,
        rule_text="The Zicboz extension adds the CBZE (Cache Block Zero instruction enable) field to senvcfg.",
        context=ENV_CTX + " CBZE is bit 7.",
        plan="With Zicboz: senvcfg.CBZE set, cleared and set again reads 1, 0, 1 (through CSRRS/CSRRC); the other "
        "CBO fields are unchanged.",
    )
    with t.only_if(S1P12):
        field_rw(t, L.CBZE, "CBZE", [L.CBZE, 0, L.CBZE])
        t.emit("csrr x7, CSR_SENVCFG")
        lab = t.label("oth")
        t.emit(f"{lab}:", 0)
        t.check_masked(
            "x7",
            L.CBIE | L.CBCFE,
            [L.CBIE | L.CBCFE, 0, L.CBIE],
            lab,
            "CBIE/CBCFE are not changed by CBZE writes (boot value or read-only zero)",
        )
        env_restore(t)
    tests.append(t)

    t = new("senvcfg_cbze_op", required=["I", "S", "U", ZICBOZ])
    t.extra_data += CBO_DATA
    t.describe(
        source=SUP,
        rule_text="The CBZE field controls execution of the cache block zero instruction (CBO.ZERO) in U-mode.",
        context=ENV_CTX,
        plan="With menvcfg.CBZE=1: senvcfg.CBZE=1 lets U-mode CBO.ZERO execute and zero the block (a nonzero word "
        "is stored first); senvcfg.CBZE=0 makes it raise illegal-instruction (stval 0 or the instruction) and "
        "leave the word. Twice in each order.",
    )
    with t.only_if(S1P12):
        for sv in (1, 0, 1, 0):
            cbo_case(t, "zero", L.CBZE, L.CBZE * sv, check_s=False)
        env_restore(t)
    tests.append(t)

    t = new("senvcfg_cbze_umode_op", required=["I", "S", "U", ZICBOZ])
    t.extra_data += CBO_DATA
    t.describe(
        source=SUP,
        rule_text="Execution of CBO.ZERO in U-mode is enabled only if execution of the instruction is enabled for "
        "use in S-mode and CBZE is set to 1; otherwise, an illegal-instruction exception is raised.",
        context=ENV_CTX + " CBO.ZERO is enabled in S-mode by menvcfg.CBZE.",
        plan="For the four (menvcfg.CBZE, senvcfg.CBZE) pairs: S-mode CBO.ZERO executes iff menvcfg.CBZE=1; U-mode "
        "CBO.ZERO executes (and zeroes the block) iff both are 1, otherwise raises illegal-instruction and leaves "
        "the block. menvcfg.CBZE=0 with senvcfg.CBZE=1 checks that the S-level enable does not leak.",
    )
    with t.only_if(S1P12):
        for m in (1, 0):
            for sv in (1, 0):
                cbo_case(t, "zero", L.CBZE * m, L.CBZE * sv)
        env_restore(t)
    tests.append(t)

    t = new("senvcfg_cbze_rdonly0")
    t.forbidden = [ZICBOZ]
    t.describe(
        source=SUP,
        rule_text="When the Zicboz extension is not implemented, CBZE is read-only zero.",
        context="Runs only on harts without Zicboz. CBZE is senvcfg bit 7.",
        plan="senvcfg.CBZE written 1 with CSRRS and with CSRRW (whole register) reads 0.",
    )
    with t.only_if(S1P12):
        t.emit("csrr x9, CSR_SENVCFG")
        L.bits(t, "CSR_SENVCFG", L.CBZE, True)
        lab = t.label("ro")
        t.emit(f"{lab}:", 0)
        t.emit("csrr x7, CSR_SENVCFG")
        t.check_masked("x7", L.CBZE, 0, lab, "CBZE reads 0 after CSRRS")
        t.emit("ori x6, x9, 0x80")
        t.emit("csrw CSR_SENVCFG, x6")
        t.emit("csrr x7, CSR_SENVCFG")
        t.emit("csrw CSR_SENVCFG, x9")
        t.check_masked("x7", L.CBZE, 0, lab, "CBZE reads 0 after CSRRW")
    tests.append(t)

    # ---- CBCFE ----
    t = new("senvcfg_cbcfe", required=["I", "S", "U", ZICBOM])
    t.extra_data += CBO_DATA
    t.describe(
        source=SUP,
        rule_text="The Zicbom extension adds the CBCFE (Cache Block Clean and Flush instruction Enable) field to "
        "senvcfg to control execution of the CBO.CLEAN and CBO.FLUSH instructions in U-mode.",
        context=ENV_CTX + " CBCFE is bit 6.",
        plan="1. senvcfg.CBCFE set, cleared, set reads 1, 0, 1.\n"
        "2. With menvcfg.CBCFE=1: U-mode CBO.CLEAN and CBO.FLUSH execute with CBCFE=1 and raise "
        "illegal-instruction with CBCFE=0.",
    )
    with t.only_if(S1P12):
        field_rw(t, L.CBCFE, "CBCFE", [L.CBCFE, 0, L.CBCFE])
        for op in ("clean", "flush"):
            for sv in (1, 0):
                cbo_case(t, op, L.CBCFE, L.CBCFE * sv, check_s=False)
        env_restore(t)
    tests.append(t)

    t = new("senvcfg_cbcfe_umode_op", required=["I", "S", "U", ZICBOM])
    t.extra_data += CBO_DATA
    t.describe(
        source=SUP,
        rule_text="Execution of these instructions in U-mode is enabled only if execution of these instructions is "
        "enabled for use in S-mode and CBCFE is set to 1; otherwise, an illegal-instruction exception is raised.",
        context=ENV_CTX + " CBO.CLEAN/FLUSH are enabled in S-mode by menvcfg.CBCFE.",
        plan="For CBO.CLEAN and CBO.FLUSH and the four (menvcfg.CBCFE, senvcfg.CBCFE) pairs: S-mode executes iff "
        "menvcfg.CBCFE=1; U-mode executes iff both are 1, otherwise illegal-instruction (stval 0 or the "
        "instruction).",
    )
    with t.only_if(S1P12):
        for op in ("clean", "flush"):
            for m in (1, 0):
                for sv in (1, 0):
                    cbo_case(t, op, L.CBCFE * m, L.CBCFE * sv)
        env_restore(t)
    tests.append(t)

    t = new("senvcfg_cbcfe_rdonly0")
    t.forbidden = [ZICBOM]
    t.describe(
        source=SUP,
        rule_text="When the Zicbom extension is not implemented, CBCFE is read-only zero.",
        context="Runs only on harts without Zicbom. CBCFE is senvcfg bit 6.",
        plan="senvcfg.CBCFE written 1 with CSRRS and with CSRRW reads 0.",
    )
    with t.only_if(S1P12):
        t.emit("csrr x9, CSR_SENVCFG")
        L.bits(t, "CSR_SENVCFG", L.CBCFE, True)
        lab = t.label("ro")
        t.emit(f"{lab}:", 0)
        t.emit("csrr x7, CSR_SENVCFG")
        t.check_masked("x7", L.CBCFE, 0, lab, "CBCFE reads 0 after CSRRS")
        t.emit("ori x6, x9, 0x40")
        t.emit("csrw CSR_SENVCFG, x6")
        t.emit("csrr x7, CSR_SENVCFG")
        t.emit("csrw CSR_SENVCFG, x9")
        t.check_masked("x7", L.CBCFE, 0, lab, "CBCFE reads 0 after CSRRW")
    tests.append(t)

    # ---- CBIE ----
    t = new("senvcfg_cbie", required=["I", "S", ZICBOM])
    t.describe(
        source=SUP,
        rule_text="The Zicbom extension adds the CBIE (Cache Block Invalidate instruction Enable) WARL field to "
        "senvcfg to control execution of the CBO.INVAL instruction in U-mode.",
        context=ENV_CTX + " CBIE is bits 5:4: 00 illegal, 01 flush, 10 reserved, 11 invalidate. As a WARL field "
        "it reads a legal value (00, 01 or 11) after any write; which of them it holds is the implementation's "
        "choice (senvcfg_cbie_umode_op checks the behavior for the value read back).",
        plan="senvcfg.CBIE written 00, 01, 11, 01, 00 reads one of 00, 01, 11 each time, and CBCFE/CBZE keep their "
        "values.",
    )
    with t.only_if(S1P12):
        t.emit("csrr x9, CSR_SENVCFG")
        for v in (0, 1, 3, 1, 0):
            L.bits(t, "CSR_SENVCFG", L.CBIE, False)
            if v:
                L.bits(t, "CSR_SENVCFG", v << 4, True)
            lab = t.label("cbie")
            t.emit(f"{lab}:", 0)
            t.emit("csrr x7, CSR_SENVCFG")
            t.check_masked("x7", L.CBIE, [0, 0x10, 0x30], lab, f"CBIE written {v:02b} reads a legal value")
            t.emit("xor x7, x7, x9")
            t.check_masked("x7", L.CBCFE | L.CBZE, 0, lab, "CBCFE and CBZE unchanged")
        env_restore(t)
    tests.append(t)

    t = new("senvcfg_cbie_rsv", required=["I", "S", ZICBOM])
    t.describe(
        source=SUP,
        rule_text="The encoding 0b10 is reserved.",
        context=ENV_CTX + " CBIE is a WARL field, so writing the reserved 10 leaves a legal value.",
        plan="senvcfg.CBIE written 10 (through CSRRW of the whole register and through CSRRC/CSRRS from 11 and 00) "
        "reads 00, 01 or 11, never 10.",
    )
    with t.only_if(S1P12):
        t.emit("csrr x9, CSR_SENVCFG")
        for how in ("csrw", "from11", "from00"):
            if how == "csrw":
                t.li("x6", ~L.CBIE)
                t.emit("and x6, x6, x9")
                t.emit("ori x6, x6, 0x20")
                t.emit("csrw CSR_SENVCFG, x6")
            elif how == "from11":
                L.bits(t, "CSR_SENVCFG", L.CBIE, True)
                L.bits(t, "CSR_SENVCFG", 0x10, False)
            else:
                L.bits(t, "CSR_SENVCFG", L.CBIE, False)
                L.bits(t, "CSR_SENVCFG", 0x20, True)
            lab = t.label("rsv")
            t.emit(f"{lab}:", 0)
            t.emit("csrr x7, CSR_SENVCFG")
            legal = [0x20] if MUT == "cbie_10_held" else [0, 0x10, 0x30]
            t.check_masked("x7", L.CBIE, legal, lab, f"CBIE written 10 ({how}) does not read 10")
        t.emit("csrw CSR_SENVCFG, x9")
    tests.append(t)

    t = new("senvcfg_cbie_rdonly0")
    t.forbidden = [ZICBOM]
    t.describe(
        source=SUP,
        rule_text="When the Zicbom extension is not implemented, CBIE is read-only zero.",
        context="Runs only on harts without Zicbom. CBIE is senvcfg bits 5:4.",
        plan="senvcfg.CBIE written 11 and 01 (CSRRS, CSRRW) reads 00.",
    )
    with t.only_if(S1P12):
        t.emit("csrr x9, CSR_SENVCFG")
        for v in (0x30, 0x10):
            L.bits(t, "CSR_SENVCFG", v, True)
            lab = t.label("ro")
            t.emit(f"{lab}:", 0)
            t.emit("csrr x7, CSR_SENVCFG")
            t.check_masked("x7", L.CBIE, 0, lab, f"CBIE reads 00 after CSRRS of {v >> 4:02b}")
            t.emit(f"ori x6, x9, {v}")
            t.emit("csrw CSR_SENVCFG, x6")
            t.emit("csrr x7, CSR_SENVCFG")
            t.emit("csrw CSR_SENVCFG, x9")
            t.check_masked("x7", L.CBIE, 0, lab, f"CBIE reads 00 after CSRRW of {v >> 4:02b}")
    tests.append(t)

    t = new("senvcfg_cbie_umode_op", required=["I", "S", "U", ZICBOM])
    t.extra_data += CBO_DATA
    t.describe(
        source=SUP,
        rule_text="Execution of CBO.INVAL in U-mode is enabled only if execution of the instruction is enabled for "
        "use in S-mode and CBIE is set to 0b01 or 0b11; otherwise, an illegal-instruction exception is raised.",
        context=ENV_CTX + " CBO.INVAL is enabled in S-mode when menvcfg.CBIE is 01 or 11. Both CBIE fields are WARL, "
        "so the expected outcome uses the values read back.",
        plan="For menvcfg.CBIE and senvcfg.CBIE each written 00, 01 and 11 (nine pairs): S-mode CBO.INVAL executes "
        "iff menvcfg.CBIE != 00; U-mode CBO.INVAL executes iff menvcfg.CBIE != 00 and senvcfg.CBIE is 01 or 11, "
        "otherwise illegal-instruction (stval 0 or the instruction).",
    )
    with t.only_if(S1P12):
        for m in (3, 1, 0):
            for sv in (3, 1, 0):
                cbo_case(t, "inval", m << 4, sv << 4)
        env_restore(t)
    tests.append(t)

    t = new("cbo-inval_s_mode_enabled_op", required=["I", "S", "U", ZICBOM])
    t.extra_data += CBO_DATA
    t.describe(
        source=SUP,
        rule_text="If CBO.INVAL is enabled in S-mode to perform a flush operation, then when the instruction is "
        "enabled in U-mode it performs a flush operation, even if CBIE is set to 0b11. Otherwise, the "
        "instruction behaves as follows, depending on the CBIE encoding: 01 the instruction is executed and "
        "performs a flush operation; 11 the instruction is executed and performs an invalidate operation.",
        context=ENV_CTX + " A flush keeps the newest data; an invalidate may discard a dirty copy, so a later load "
        "reads either the newest data or the data in memory before the store. The block starts as "
        "0x1111111111111111 in memory; S-mode stores a new value, U-mode runs CBO.INVAL, and S-mode loads it back. "
        "CBIE values are those read back (WARL).",
        plan="For (menvcfg.CBIE, senvcfg.CBIE) written (01, 11), (01, 01), (11, 01), (11, 11), with a different new "
        "value each time: after the U-mode CBO.INVAL, the word reads the new value when either field reads 01 (a "
        "flush), and the new value or the value loaded before the store when both read 11 (an invalidate). If "
        "either field reads back 00 (WARL), the U-mode CBO.INVAL must raise illegal-instruction instead.",
    )
    with t.only_if(S1P12):
        for k, (m, sv) in enumerate(((1, 3), (1, 1), (3, 1), (3, 3))):
            enc = L.cbo("inval", 6)
            newv = [0x2222222222222222, 0x3333333333333333, 0x4444444444444444, 0x5555555555555555][k]
            t.comment(f"menvcfg.CBIE={m:02b}, senvcfg.CBIE={sv:02b}")
            t.tsbi_csr("CLEAR", "MENVCFG", imm=L.CBIE)
            t.tsbi_csr("SET", "MENVCFG", imm=m << 4)
            t.tsbi_csr("READ", "MENVCFG")
            t.emit("srli x8, a0, 4")
            t.emit("andi x8, x8, 3")
            L.bits(t, "CSR_SENVCFG", L.CBIE, False)
            L.bits(t, "CSR_SENVCFG", sv << 4, True)
            t.emit("csrr x7, CSR_SENVCFG")
            t.emit("srli x7, x7, 4")
            t.emit("andi x7, x7, 3")
            t.comment("x9 = enabled in U-mode: (m != 00) & (s is 01 or 11), from the values read back")
            t.emit("snez x9, x8")
            t.emit("andi x6, x7, 1")
            t.emit("and x9, x9, x6")
            t.comment("x7 = flush: (m == 01) | (s == 01)")
            t.emit("addi x8, x8, -1")
            t.emit("seqz x8, x8")
            t.emit("addi x7, x7, -1")
            t.emit("seqz x7, x7")
            if MUT != "inval_ignores_s_flush":
                t.emit("or x7, x7, x8")
            t.la("x6", "s_cbo_blk")
            t.emit("LREG x1, 0(x6)  // old data (the line is clean: never written, or flushed/invalidated)")

            def enabled(k: int = k, newv: int = newv, enc: int = enc) -> None:
                t.la("x6", "s_cbo_blk")
                t.load("x8", newv, "new data")
                t.emit("SREG x8, 0(x6)")
                lab = win(t, "U", [word(enc, "cbo.inval (x6)")], "ok", "CBO.INVAL")
                t.emit("LREG x9, 0(x6)")
                t.load("x8", newv, "new data")

                def flush() -> None:
                    t.check("x9", newv, lab, "CBO.INVAL performed a flush: the new data stays")

                def inval() -> None:
                    if MUT == "inval_ignores_s_flush":
                        t.emit("xor x9, x9, x1")
                        t.emit("seqz x9, x9")
                    else:
                        t.emit("xor x6, x9, x8")
                        t.emit("seqz x6, x6")
                        t.emit("xor x9, x9, x1")
                        t.emit("seqz x9, x9")
                        t.emit("or x9, x9, x6")
                    t.check_bool("x9", lab, "CBO.INVAL invalidated: the new data or the data before the store")

                t.either("x7", flush, inval)

            def disabled(enc: int = enc) -> None:
                t.la("x6", "s_cbo_blk")
                win(
                    t, "U", [word(enc, "cbo.inval (x6)")], ILLEGAL, "CBO.INVAL with a CBIE field read back 00", [0, enc]
                )

            t.either("x9", enabled, disabled)
        env_restore(t)
    tests.append(t)
    return tests


# ======================================================================== SRET, TSR, MPRV, WFI, ECALL
def gen_xret() -> list[TestFile]:
    tests = []

    # ---- sret_presence ----
    t = new("sret_presence", required=["I", "S", "U"])
    t.describe(
        source=MAC,
        rule_text="SRET must be provided if supervisor mode is supported, and should raise an illegal-instruction "
        "exception otherwise.",
        context="With S-mode (this suite), SRET executes in S-mode (mstatus.TSR=0, the boot value; TSR is cleared "
        "through T-SBI first). SRET returns to the mode in SPP at sepc. U-mode cannot execute SRET (it is a "
        "privileged instruction).",
        plan="1. SRET with SPP=1 in S-mode does not trap and lands at sepc in S-mode (a read of sstatus there does "
        "not trap).\n"
        "2. SRET with SPP=0 lands at sepc in U-mode (the same read raises illegal-instruction from U).\n"
        "3. SRET in U-mode raises illegal-instruction (stval 0 or the SRET bits).",
    )
    quiet_sie(t)
    L.m_bits(t, "mstatus", L.TSR, False)
    lab = t.label("ss")
    t.allow(1)
    sret_to(t, "S", lab)
    t.emit(f"{lab}:", 0)
    t.emit("csrr x7, sstatus")
    t.outcome("ok", lab, "SRET with SPP=1 lands in S-mode")
    lab = t.label("su")
    t.allow(1)
    sret_to(t, "U", lab)
    t.emit(f"{lab}:", 0)
    t.emit("csrr x7, sstatus")
    t.leave()
    t.outcome(ILLEGAL, lab, "SRET with SPP=0 lands in U-mode", [0, L.enc_csr(0x100, 2, 7, 0)], origin="U")
    win(t, "U", ["sret"], ILLEGAL, "SRET", [0, L.SRET])
    tests.append(t)

    # ---- mstatus_tsr_op (S part) ----
    t = new("mstatus_tsr_op")
    t.describe(
        source=MAC,
        rule_text="When tsr=1, attempts to execute sret while executing in S-mode will raise an illegal-instruction "
        "exception. When tsr=0, this operation is permitted in S-mode.",
        context="This S-boot file covers TSR=0, set through T-SBI. TSR=1 makes the framework's S-mode handler (which "
        "returns with SRET) unusable, so the TSR=1 part is in mstatus_tsr_op_Sm, where the trap goes to M-mode.",
        plan="With mstatus.TSR cleared by M-mode: SRET in S-mode with SPP=1 lands at sepc without a trap, three "
        "times with different SPIE values.",
    )
    quiet_sie(t)
    L.m_bits(t, "mstatus", L.TSR, False)
    for spie in (0, 1, 0):
        lab = t.label("s")
        t.allow(1)
        sret_to(t, "S", lab, spie=spie)
        t.emit(f"{lab}:", 0)
        t.emit("nop")
        t.outcome("ok", lab, f"SRET in S-mode with TSR=0 (SPIE={spie})")
        L.bits(t, "sstatus", SIE, False)
    tests.append(t)

    def tsr_m(t: TestFile, with_m: bool) -> None:
        """M-boot TSR cases. medeleg = 0 at an M boot, so illegal-instruction traps go to M-mode."""
        t.comment("TSR is WARL (must be writable with S-mode): probe")
        t.li("x6", L.TSR)
        t.emit("csrs mstatus, x6")
        t.emit("csrr x7, mstatus")
        t.emit("csrc mstatus, x6")
        t.emit("srli x7, x7, 22")
        t.emit("andi x7, x7, 1")

        def s_sret(tsr: int) -> None:
            t.comment(f"SRET in S-mode with TSR={tsr}")
            tg = t.label("tgt")
            t.la("x6", tg)
            t.emit("csrw sepc, x6")
            t.li("x6", SPP)
            t.emit("csrs mstatus, x6")
            with t.only_if(H):
                t.emit("LI(x6, HSTATUS_SPV)", 2)
                t.emit("csrc CSR_HSTATUS, x6")
            if tsr:
                t.li("x6", L.TSR)
                t.emit("csrs mstatus, x6")
            exp = ILLEGAL if tsr and MUT != "tsr_ignored" else "ok"
            win(t, "S", ["sret", f"{tg}:"], exp, f"SRET with TSR={tsr}", [0, L.SRET])
            t.li("x6", L.TSR)
            t.emit("csrc mstatus, x6")

        def body() -> None:
            s_sret(1)
            s_sret(0)
            s_sret(1)
            if with_m:
                t.comment("SRET in M-mode with TSR=1 is permitted")
                tg = t.label("mtgt")
                t.la("x6", tg)
                t.emit("csrw sepc, x6")
                t.li("x6", SPP)
                t.emit("csrs mstatus, x6")
                with t.only_if(H):
                    t.emit("LI(x6, HSTATUS_SPV)", 2)
                    t.emit("csrc CSR_HSTATUS, x6")
                t.li("x6", L.TSR)
                t.emit("csrs mstatus, x6")
                lab = t.label("msret")
                t.allow(1)
                t.emit(f"{lab}:", 0)
                t.emit("sret")
                t.emit(f"{tg}:", 0)
                t.emit("RVTEST_TSBI_GOTO_MMODE", 120)
                t.li("x6", L.TSR)
                t.emit("csrc mstatus, x6")
                t.outcome(
                    ILLEGAL if MUT == "tsr_traps_m" else "ok", lab, "SRET in M-mode with TSR=1", [0, L.SRET], origin="M"
                )
                t.li("x6", L.TSR)
                t.emit("csrs mstatus, x6")
                win(t, "U", ["sret"], ILLEGAL, "SRET with TSR=1", [0, L.SRET])
                t.li("x6", L.TSR)
                t.emit("csrc mstatus, x6")

        t.either("x7", body, lambda: t.comment("TSR is read-only zero"))

    t = new_sm("mstatus_tsr_op")
    t.describe(
        source=MAC,
        rule_text="When tsr=1, attempts to execute sret while executing in S-mode will raise an illegal-instruction "
        "exception. When tsr=0, this operation is permitted in S-mode.",
        context="TSR is mstatus bit 22 (WARL; must be writable with S-mode, mstatus_tsr_acc, probed anyway). The "
        "test boots to M-mode, where medeleg = 0, so the illegal-instruction trap is taken by the M-mode handler "
        "(the S-mode handler returns with SRET and could not run with TSR=1). The rule restricts the trap to "
        "S-mode: SRET in M-mode with TSR=1 is permitted (it returns to S-mode at sepc).",
        plan="1. S-mode SRET (SPP=1, sepc = the next instruction) with TSR=1 raises illegal-instruction from S "
        "(mepc = the SRET, mtval 0 or its bits); with TSR=0 it executes; then TSR=1 again.\n"
        "2. M-mode SRET with TSR=1 executes and lands in S-mode at sepc.\n"
        "3. U-mode SRET with TSR=1 raises illegal-instruction (as always in U-mode).",
    )
    tsr_m(t, True)
    tests.append(t)

    t = new_sm("sret_ill_inst_exc_rst")
    t.describe(
        source=MAC,
        rule_text="SRET should also raise an illegal-instruction exception when TSR=1 in mstatus, as described in "
        "<<virt-control>>.",
        context="Same mechanism as mstatus_tsr_op_Sm: the test boots to M-mode (medeleg = 0) so the trap is taken "
        "by the M-mode handler.",
        plan="S-mode SRET with TSR=1 raises illegal-instruction from S (mtval 0 or the SRET bits); with TSR=0 the "
        "same SRET executes; TSR=1 again traps.",
    )
    tsr_m(t, False)
    tests.append(t)

    # ---- mstatus_mprv_clr_mret_sret_less_priv (M part) ----
    t = new_sm("mstatus_mprv_clr_mret_sret_less_priv")
    t.describe(
        source=MAC,
        rule_text="An mret or sret instruction that changes the privilege mode to a mode less privileged than M "
        "also sets mprv=0.",
        context="SRET always returns to S or U, so it always clears MPRV. MPRV can only be 1 while in M-mode (any "
        "entry to S or U clears it), so the SRET is executed in M-mode. MPP is set to M first, so MPRV=1 has no "
        "effect on the M-mode accesses around it. The MRET part belongs to a machine-mode suite.",
        plan="1. In M-mode: MPP=M, MPRV=1, SPP=1, sepc = target: SRET lands in S-mode; back in M-mode (T-SBI), "
        "mstatus.MPRV reads 0.\n"
        "2. The same with SPP=0 (lands in U-mode).",
    )
    for spp, mode in ((1, "S"), (0, "U")):
        tg = t.label(f"tgt{mode}")
        t.la("x6", tg)
        t.emit("csrw sepc, x6")
        t.li("x6", SPP)
        t.emit(f"{'csrs' if spp else 'csrc'} mstatus, x6")
        with t.only_if(H):
            t.emit("LI(x6, HSTATUS_SPV)", 2)
            t.emit("csrc CSR_HSTATUS, x6")
        t.emit("LI(x6, MSTATUS_MPP)", 2)
        t.emit("csrs mstatus, x6  // MPP = M")
        t.emit("LI(x6, MSTATUS_MPRV)", 2)
        t.emit("csrs mstatus, x6")
        lab = t.label("sret")
        t.allow(1)
        t.emit(f"{lab}:", 0)
        t.emit("sret")
        t.emit(f"{tg}:", 0)
        t.emit("RVTEST_TSBI_GOTO_MMODE", 120)
        t.outcome("ok", lab, f"SRET from M-mode to {mode}-mode", origin="M")
        t.emit("csrr x7, mstatus")
        t.emit("LI(x6, MSTATUS_MPRV)", 2)
        t.emit("csrc mstatus, x6")
        t.check_masked(
            "x7", L.MPRV, L.MPRV if MUT == "sret_keeps_mprv" else 0, lab, f"mstatus.MPRV is 0 after SRET to {mode}-mode"
        )
    tests.append(t)

    # ---- mstatus_tw_umode_op ----
    t = new("mstatus_tw_umode_op", required=["I", "S", "U"])
    t.describe(
        source=MAC,
        rule_text="When S-mode is implemented, then executing wfi in U-mode causes an illegal-instruction "
        "exception, regardless of the value of the tw bit, unless the instruction completes within an "
        "implementation-specific, bounded time limit.",
        context="So a U-mode WFI either completes (a NOP, or a wait that ends) or raises illegal-instruction (stval "
        "0 or the WFI bits); it may not wait forever. No interrupt is pending or enabled, so nothing ends the "
        "wait except the time limit. mstatus.TW is set and cleared through T-SBI.",
        plan="U-mode WFI with TW=0 (twice) and TW=1 (twice): completes or raises illegal-instruction from U-mode.",
    )
    quiet_sie(t)
    for tw in (0, 1, 0, 1):
        L.m_bits(t, "mstatus", L.TW, bool(tw))
        exp: Expect = "ok" if MUT == "wfi_u_must_complete" else ["ok", ILLEGAL]
        win(t, "U", ["wfi"], exp, f"WFI with TW={tw}", [0, L.WFI])
    L.m_bits(t, "mstatus", L.TW, False)
    tests.append(t)

    # ---- wfi_unaffected_conditions ----
    t = new("wfi_unaffected_conditions", pool=POOL_INT)
    t.describe(
        source=MAC,
        rule_text="The operation of WFI must be unaffected by the global interrupt bits in mstatus (MIE and SIE) "
        "and the delegation register mideleg (i.e., the hart must resume if a locally enabled interrupt becomes "
        "pending, even if it has been delegated to a less-privileged mode), but should honor the individual "
        "interrupt enables (e.g, MTIE) (i.e., implementations should avoid resuming the hart if the interrupt is "
        "pending but not locally enabled).",
        context=INT_CTX + " This S suite covers SIE: in S-mode with SIE=0 and a pending interrupt enabled in sie, "
        "WFI must not wait forever and no interrupt is taken (globally disabled), so it completes at the next "
        "instruction. mstatus.TW=0 (cleared through T-SBI), so WFI may execute in S-mode. The mideleg part needs "
        "M-mode.",
        plan="For each implemented S-level interrupt: pending, enabled in sie, SIE=0: S-mode WFI completes "
        "without a trap; then the interrupt is taken when SIE is set (it stayed pending).",
    )
    quiet_sie(t)
    L.m_bits(t, "mstatus", L.TW, False)
    for src, code in SRC.items():

        def b(src: str = src, code: int = code) -> None:
            L.bits(t, "sie", 1 << code, True)
            L.raise_int(t, src)
            exp = ILLEGAL if MUT == "wfi_needs_sie" else "ok"
            win(t, "S", ["wfi"], exp, f"WFI with {src} pending, enabled in sie, SIE=0", [0, L.WFI])
            L.int_window(t, [src], "S", 1, 1, 0, icause(code), f"{src} after the WFI")
            L.lower_int(t, src)

        L.with_src(t, src, b)
    tests.append(t)

    # ---- ecall_priv_mode_op ----
    t = new("ecall_priv_mode_op", required=["I", "S", "U"])
    t.describe(
        source=MAC,
        rule_text="The ECALL instruction is used to make a request to the supporting execution environment. When "
        "executed in U-mode, S-mode, or M-mode, it generates an environment-call-from-U-mode exception, "
        "environment-call-from-S-mode exception, or environment-call-from-M-mode exception, respectively, and "
        "performs no other operation.",
        context="The framework delegates cause 8 to S-mode and takes cause 9 in M-mode. A test ECALL is the T-SBI "
        "ECALL_TEST call (a0 = 0x73), which the handlers log like any trap and return past, with a0 = the ECALL "
        "address. The M-mode case belongs to a machine-mode suite.",
        plan="1. U-mode ECALL: cause 8, sepc = the ECALL, stval 0, from U.\n"
        "2. S-mode ECALL: cause 9 (taken in M-mode), mepc = the ECALL, from S.\n"
        "3. No other operation: x6-x9 hold their values across each ECALL.",
    )
    for mode, cause in (("U", 9 if MUT == "ecall_u_cause_9" else L.ECALL_U), ("S", L.ECALL_S)):
        vals = [t.rand_x() for _ in range(4)]
        for r, v in zip(("x6", "x7", "x8", "x9"), vals):
            t.load(r, v, f"{r} before")
        lab = win(t, mode, ["ecall"], cause, "ECALL", [0], pre=["li a0, 0x73"])
        for r, v in zip(("x6", "x7", "x8", "x9"), vals):
            t.check(r, v, lab, f"{r} unchanged by the {mode}-mode ECALL")
    tests.append(t)
    return tests


def gen_mask_ialign() -> list[TestFile]:
    tests = []
    t = new_sm("sepc_op_mask_ialign32", required=["I", "S", "C"])
    t.extra_data += [".balign 64", "s_d0: .dword 0, 0"]
    t.describe(
        source=SUP,
        rule_text="If an implementation allows IALIGN to be either 16 or 32 (by changing CSR misa, for example), "
        "then, whenever IALIGN=32, bit sepc[1] is masked on reads so that it appears to be 0. This masking "
        "occurs also for the implicit read by the SRET instruction. Though masked, sepc[1] remains writable when "
        "IALIGN=32.",
        context="IALIGN changes when misa.C is cleared; that needs M-mode (an _Sm file). misa.C is WARL: the test "
        "probes whether it can be cleared. The test code has no compressed instructions and is 4-byte aligned, "
        "so clearing misa.C is not suppressed. SRET is executed in M-mode (allowed) and lands in S-mode.",
        plan="If misa.C can be cleared:\n"
        "1. With misa.C=0: sepc written address+2 reads address (bit 1 masked).\n"
        "2. SRET (SPP=1) with sepc = target+2 lands at target (the masked value), without a trap.\n"
        "3. Setting misa.C again: sepc reads address+2 (bit 1 was kept).\n"
        "misa is restored.",
    )
    t.emit("csrr x9, misa")
    t.li("x6", 4)
    t.emit("csrc misa, x6")
    t.emit("csrr x7, misa")
    t.emit("andi x7, x7, 4")
    t.emit("seqz x7, x7  // 1: misa.C cleared (IALIGN=32)")

    def body() -> None:
        t.la("x6", "s_d0+2")
        lab = t.label("rd")
        t.emit(f"{lab}:", 0)
        t.emit("csrw sepc, x6")
        t.emit("csrr x7, sepc")
        t.check("x7", "s_d0", lab, "IALIGN=32: sepc[1] reads 0")
        tg = t.label("tgt")
        t.la("x6", f"{tg}+2")
        t.emit("csrw sepc, x6")
        t.li("x6", SPP)
        t.emit("csrs mstatus, x6")
        with t.only_if(H):
            t.emit("LI(x6, HSTATUS_SPV)", 2)
            t.emit("csrc CSR_HSTATUS, x6")
        lab = t.label("sret")
        t.allow(1)
        t.emit(f"{lab}:", 0)
        t.emit("sret")
        t.emit(".p2align 2", 0)
        t.emit(f"{tg}:", 0)
        t.emit("nop")
        t.emit("RVTEST_TSBI_GOTO_MMODE", 120)
        t.outcome("ok", lab, "SRET with sepc = target+2 and IALIGN=32 lands at target", origin="M")
        t.la("x6", "s_d0+2")
        t.emit("csrw sepc, x6")
        t.li("x6", 4)
        t.emit("csrs misa, x6")
        t.emit("csrr x7, sepc")
        t.check("x7", "s_d0+2", lab, "with misa.C set again, sepc[1] reads 1 (it stayed writable)")

    t.either("x7", body, lambda: t.comment("misa.C cannot be cleared"))
    t.emit("csrw misa, x9")
    tests.append(t)
    return tests


def gen() -> list[TestFile]:
    return (
        gen_sstatus()
        + gen_sstatus_int()
        + gen_sstatus_view()
        + gen_uxl32()
        + gen_sum_ube()
        + gen_stvec()
        + gen_stvec_traps()
        + gen_sip_sie()
        + gen_sip_bits()
        + gen_scounteren()
        + gen_trap_csrs()
        + gen_cause_tval()
        + gen_senvcfg()
        + gen_xret()
        + gen_mask_ialign()
    )


if __name__ == "__main__":
    out = L
    ts = gen()
    for tf in ts:
        tf.write()
    print(f"wrote {len(ts)} tests to {Path(__file__).resolve().parents[1] / SUITE}")
