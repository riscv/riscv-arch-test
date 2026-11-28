# SPDX-License-Identifier: Apache-2.0
"""Shared helpers for the Zicfilp rule-derived tests (gen_Zicfilp.py).

The central primitive is land(): in a trap window, run a control transfer (jalr, c.jr, c.jalr, jal, a taken
branch, or straight-line fall-through) to a target block, and check the outcome. The target block is

    tgt:  <instruction(s) under test>      (4-byte aligned, or at 2 mod 4 with a c.nop in front)
    land: auipc x0, 0                      (lpad 0, 4-byte aligned: the recovery landing pad)

A trap at the target resumes at `land` (rvtest_trap_resume), so the handler's xret, which restores ELP from
xPELP, always returns to a valid landing pad. The resume address is cleared again right after `land`.
Landing pads are written as `auipc x0, <label>` (the lpad encoding), so MARCH needs no Zicfilp, and compressed
instructions are written as .hword encodings, so MARCH needs no C.

ELP itself is not readable. It is observed three ways: a software-check exception (cause 18) at a non-lpad
target, the xPELP bit a trap saves (read from the trap log's xstatus words), and an xRET that restores it.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent))
from aigen import POOL_TRAP, TestFile, X

if TYPE_CHECKING:
    from aigen import Expect, Value

ISSUE = "https://github.com/riscv/riscv-isa-manual/issues/"
UNPRIV = "src/unpriv/cfi.adoc"
PRIV = "src/priv/cfi.adoc"
MAC = "src/priv/machine.adoc"
SUP = "src/priv/supervisor.adoc"
HYP = "src/priv/hypervisor.adoc"
MARCH = "rv${XLEN}i_zicsr_zifencei"
REQ_S = ["I", "S", "Zicfilp"]  # boots to S-mode
REQ_M = ["I", "Sm", "Zicfilp"]  # boots to M-mode (_Sm files)
REQ_MU = ["I", "U", "Sm", "Zicfilp"]  # M-mode files that also need U (menvcfg exists only with U)
H = "defined(H_SUPPORTED)"
ZCA = "defined(ZCA_SUPPORTED)"
S_IMPL = "defined(S_SUPPORTED)"
MUT = os.environ.get("AI_MUTANT", "")

SWCHK, BRK, IACC, ILL, VIRT = 18, 3, 1, 2, 22
LP_TVAL: list = [0, 2]  # xtval of a landing-pad fault: 2, or 0 ("no information provided")
SPELP = 1 << 23
MPELP64 = 1 << 41
MPELP_H = 1 << 9  # mstatush.MPELP (RV32)
MPV64 = 1 << 39
MPV_H = 1 << 7  # mstatush.MPV (RV32)
MLPE = 1 << 10  # mseccfg.MLPE
LPE = 1 << 2  # menvcfg/senvcfg/henvcfg.LPE
SPP, SPIE, SIE = 1 << 8, 1 << 5, 1 << 1
CSR = {
    "senvcfg": 0x10A,
    "henvcfg": 0x60A,
    "hstatus": 0x600,
    "vsstatus": 0x200,
    "hedeleg": 0x602,
    "hvip": 0x645,
    "hie": 0x604,
    "mseccfg": 0x747,
    "menvcfg": 0x30A,
    "mstatush": 0x310,
}
ORIGIN_OK = {"U": [1, 3], "S": [1, 3], "M": [3], "VU": [1, 3], "VS": [1, 3]}  # handler modes (log VECT), hedeleg=0


def lpad(label: int) -> str:
    return f"auipc x0, {label:#x}  // lpad {label:#x}"


def lpad_enc(label: int) -> int:
    return (label << 12) | 0x17


# ---------------------------------------------------------------- control transfers
@dataclass
class J:
    """A control transfer to the target. kind: jalr, c.jr, c.jalr, jal, c.j, c.jal, beq (taken), seq (fall-through
    with no transfer), or none. For jalr, rs1 holds tgt - imm (+1 when odd: jalr clears bit 0)."""

    kind: str
    rd: int = 0
    rs1: int = 6
    imm: int = 0
    odd: bool = False

    def text(self) -> str:
        if self.kind == "jalr":
            return f"jalr x{self.rd}, {self.imm}(x{self.rs1})" + (" [rs1+imm odd]" if self.odd else "")
        if self.kind in ("c.jr", "c.jalr"):
            return f"{self.kind} x{self.rs1}"
        if self.kind in ("jal",):
            return f"jal x{self.rd}"
        return self.kind

    @property
    def compressed(self) -> bool:
        return self.kind in ("c.jr", "c.jalr", "c.j", "c.jal")


def sets_elp(j: J) -> bool:
    """is_lp_expected (cfi.adoc, Landing pad expected determination), with the mutants that model wrong decodes."""
    if j.kind not in ("jalr", "c.jr", "c.jalr"):
        return MUT == "direct_sets_elp" and j.kind in ("jal", "c.jal")
    exempt = {1, 5, 7}
    if MUT == "x7_sets_elp":
        exempt = {1, 5}
    if MUT == "x5_sets_elp":
        exempt = {1, 7}
    if MUT == "x6_exempt":
        exempt = {1, 5, 6, 7}
    if MUT == "c_jr_no_elp" and j.compressed:
        return False
    if MUT == "rd_link_exempt" and j.kind == "jalr" and j.rd in (1, 5):
        return False
    return j.rs1 not in exempt


# ---------------------------------------------------------------- targets
@dataclass
class T:
    """Instruction(s) at the target. size: bytes of `lines` (multiple of 2). misalign: put the target at 2 mod 4
    (needs C). lp: the landing-pad label when the first instruction is an lpad, else None. traps: the cause the
    first instruction raises when it executes (no landing-pad fault), else "ok"."""

    lines: list[str]
    note: str
    size: int = 4
    misalign: bool = False
    lp: int | None = None
    traps: Expect = "ok"
    tval: Expect | None = None  # legal xtval values of `traps` ("TGT0": 0 or the trapping instruction)
    check: list = field(default_factory=list)  # (reg, value, desc) checks after the window
    second: bool = False  # the trap (traps/tval) is at the instruction labeled SECOND, not the first


def nonlp(note: str = "nop (addi x0, x0, 0), not an lpad") -> T:
    return T(["addi x0, x0, 0  // not an lpad"], note)


def lp(label: int, misalign: bool = False) -> T:
    return T([lpad(label)], f"lpad {label:#x}" + (" at 2 mod 4" if misalign else ""), misalign=misalign, lp=label)


def ebreak() -> T:
    return T(["ebreak"], "ebreak", traps=BRK, tval="TGT0")


def lp_faults(tg: T, x7: int | None) -> bool:
    """Whether a target faults when ELP=LP_EXPECTED (cfi.adoc, Zicfilp_elp_lpad_expected)."""
    if tg.lp is None:
        return MUT != "any_insn_ok"
    if tg.misalign:
        return MUT != "no_align_check"
    if tg.lp == 0:
        return MUT == "lpl0_checks" and (x7 or 0) >> 12 & 0xFFFFF != 0
    lab = ((x7 or 0) >> 12) & 0xFFFFF
    if MUT == "label_wrong_field":
        lab = (x7 or 0) & 0xFFFFF  # x7[19:0] instead of x7[31:12]
    return tg.lp != lab


# ---------------------------------------------------------------- the land() window
def set_resume(t: TestFile, lab: str) -> None:
    t.emit(f"LA(x4, {lab})", 2)
    t.emit("LA(x5, rvtest_trap_resume)", 2)
    t.emit("SREG x4, 0(x5)  // a trap at the target resumes at the recovery lpad")


def clear_resume(t: TestFile) -> None:
    t.emit("LA(x4, rvtest_trap_resume)", 2)
    t.emit("SREG x0, 0(x4)")


def emit_jump(t: TestFile, j: J, tgt: str) -> None:
    """Emit the control transfer to tgt (the address register is already set up for indirect kinds). Keeps the
    stream 4-byte aligned: a 2-byte transfer is followed by an unexecuted c.nop."""
    if j.kind == "jalr":
        t.emit(f"jalr x{j.rd}, {j.imm}(x{j.rs1})")
    elif j.kind == "c.jr":
        t.emit(f".hword {0x8002 | (j.rs1 << 7):#x}  // c.jr x{j.rs1}")
    elif j.kind == "c.jalr":
        t.emit(f".hword {0x9002 | (j.rs1 << 7):#x}  // c.jalr x{j.rs1}")
    elif j.kind == "jal":
        t.emit(f"jal x{j.rd}, {tgt}")
    elif j.kind in ("c.j", "c.jal"):
        t.emit(".option push", 0)
        t.emit(".option rvc", 0)
        t.emit(f"{j.kind} {tgt}")
        t.emit(".option pop", 0)
    elif j.kind == "beq":
        t.emit(f"beq x0, x0, {tgt}")
    elif j.kind in ("seq", "none"):
        return
    else:
        raise ValueError(j.kind)
    if j.compressed:
        t.emit(".hword 0x0001  // c.nop (not executed): realign", 0)


def setup_jump(t: TestFile, j: J, tgt: str) -> None:
    if j.kind in ("jalr", "c.jr", "c.jalr"):
        r = f"x{j.rs1}"
        t.emit(f"LA({r}, {tgt})", 2)
        adj = -j.imm + (1 if j.odd else 0)
        while adj:
            step = max(-2048, min(2047, adj))
            t.emit(f"addi {r}, {r}, {step}")
            adj -= step


def emit_target(t: TestFile, tg: T, tgt: str, landl: str, sec: str = "", data: str = "") -> None:
    if tg.misalign:
        t.emit(".hword 0x0001  // c.nop: the target is at 2 mod 4", 1)
    t.emit(f"{tgt}:", 0)
    for ln in tg.lines:
        ln = ln.replace("LAND", landl).replace("SECOND", sec).replace("DATAW", data)
        t.emit(ln, 0 if ln.endswith(":") else 1)
    if (tg.size + (2 if tg.misalign else 0)) % 4:
        t.emit(".hword 0x0001  // c.nop: realign", 1)
    t.emit(f"{landl}:", 0)
    t.emit("auipc x0, 0  // lpad 0: recovery landing pad (4-byte aligned)")


def pelp_of_last_trap(t: TestFile, reg: str = "x14") -> None:
    """reg = the xPELP bit saved by the last logged trap: mstatus.MPELP (mstatush on RV32) when the M-mode handler
    took it, sstatus.SPELP (vsstatus for the VS handler) otherwise. Clobbers x4, x5, x15."""
    notm = t.label("notm")
    t.emit("AI_LOG(x15, TRAPLOG_VECT)", 10)
    t.emit("andi x15, x15, 3")
    t.emit(f"LREG {reg}, TRAPLOG_STATUS*REGWIDTH(x4)")
    t.emit(f"srli {reg}, {reg}, 23  // SPELP")
    t.emit("li x5, 3")
    t.emit(f"bne x15, x5, {notm}")
    t.emit("#if __riscv_xlen == 64", 0)
    t.emit(f"LREG {reg}, TRAPLOG_STATUS*REGWIDTH(x4)")
    t.emit(f"srli {reg}, {reg}, 41  // mstatus.MPELP")
    t.emit("#else", 0)
    t.emit(f"LREG {reg}, TRAPLOG_STATUS2*REGWIDTH(x4)")
    t.emit(f"srli {reg}, {reg}, 9  // mstatush.MPELP")
    t.emit("#endif", 0)
    t.emit(f"{notm}:", 0)
    t.emit(f"andi {reg}, {reg}, 1")


def check_pelp(t: TestFile, value: int, lab: str, desc: str) -> None:
    pelp_of_last_trap(t)
    t.check("x14", value, lab, f"{desc}: xPELP saved by the trap")


def check_handler(t: TestFile, modes: list, lab: str, desc: str) -> None:
    """The last trap was taken by a handler in one of modes (3 M, 1 S/HS, 2 VS)."""
    t.emit("AI_LOG(x15, TRAPLOG_VECT)", 10)
    t.emit("andi x15, x15, 3")
    t.check("x15", modes, lab, f"{desc}: handler mode (3 M, 1 S/HS, 2 VS)")


def land(
    t: TestFile,
    mode: str,
    j: J,
    tg: T,
    expect: Expect,
    desc: str,
    *,
    x7: Value | None = None,
    pelp: int | None = None,
    pre: list[str] | tuple = (),
    late: list[str] | tuple = (),
    post: list[str] | tuple = (),
    tval: Expect | None = None,
    handler: list | None = None,
    link: tuple | None = None,
) -> str:
    """One case: in `mode`, transfer control with j to target tg, inside a trap window. expect: "ok" or a cause
    (or a list of alternatives). A trap must be at the target (xepc = tgt), with xtval in tval (default: {0, 2}
    for cause 18, the target's own tval otherwise) and come from `mode`. pelp: the xPELP the trap must save.
    x7: value (int or X) loaded into x7 before the transfer (the expected landing-pad label in bits 31:12).
    Returns the target label."""
    tgt, landl, jl, sec = t.label("tgt"), t.label("land"), t.label("jump"), t.label("second")
    t.comment(f"{desc}: {j.text()} -> {tg.note} in {mode}-mode")
    set_resume(t, landl)
    t.allow(1)
    if mode != t.cur:
        t.enter(mode)
    for ln in pre:
        t.emit(ln)
    if x7 is not None:
        t.load("x7", x7, "x7: expected landing-pad label in bits 31:12")
    setup_jump(t, j, tgt)
    for ln in late:
        t.emit(ln)
    t.emit(f"{jl}:", 0)
    emit_jump(t, j, tgt)
    emit_target(t, tg, tgt, landl, sec, data_word(t))
    for ln in post:
        t.emit(ln)
    clear_resume(t)
    if mode != t.cur:
        t.leave()
    alts = expect if isinstance(expect, list) else [expect]
    if tval is None:
        if SWCHK in alts:
            tval = LP_TVAL if MUT != "tval_target" else [tgt]
        elif tg.tval == "TGT0":
            tval = [0, sec if tg.second else tgt]
        elif tg.tval is not None:
            tval = tg.tval
    epc_lab = sec if tg.second and SWCHK not in alts else tgt
    if MUT == "epc_at_jump" and SWCHK in alts and j.kind not in ("seq", "none"):
        epc_lab = jl
    t.outcome(expect, epc_lab, f"{desc} ({j.text()} -> {tg.note}) in {mode}-mode", tval, origin=mode)
    single = [a for a in alts if a != "ok"]
    if pelp is not None and len(alts) == 1 and single:
        check_pelp(t, pelp, tgt, f"{desc} in {mode}-mode")
    if handler is not None and len(alts) == 1 and single:
        check_handler(t, handler, tgt, f"{desc} in {mode}-mode")
    for reg, val, d in tg.check:
        if val == "DATAW0":
            t.emit(f"LA(x4, {data_word(t)})", 2)
            t.emit(f"LREG {reg}, 0(x4)")
            val = DATA0
        t.check(reg, val, tgt, f"{desc} in {mode}-mode: {d}")
    if link is not None:
        reg, size = link
        t.check(reg, f"{jl}+{size}", tgt, f"{desc} in {mode}-mode: the jump wrote its link register ({reg})")
    return tgt


DATA0 = 0x13579BDF


def data_word(t: TestFile) -> str:
    """A scratch word in the data section, holding DATA0 (target loads and stores use it)."""
    name = f"{t.rule.replace('-', '_')}_dataw"
    if not any(name in ln for ln in t.extra_data):
        t.extra_data += ["  .p2align 3", f"{name}:", f"  .dword {DATA0:#x}"]
    return name


def lp_case(
    t: TestFile,
    mode: str,
    j: J,
    tg: T,
    desc: str,
    enforced: bool = True,
    x7: int | None = None,
    pelp_check: bool = True,
) -> str:
    """land() with the expected outcome from the rules: a landing-pad fault when the transfer sets ELP, Zicfilp is
    enforced in mode, and the target is not a matching, aligned lpad; otherwise the target's own outcome."""
    elp = enforced and sets_elp(j)
    if elp and lp_faults(tg, x7):
        exp: Expect = SWCHK
        pelp = 1 if MUT != "pelp_not_saved" else 0
    else:
        exp = tg.traps
        pelp = 0 if exp != "ok" else None
        if MUT == "elp_leaks_disabled" and not enforced and sets_elp(j) and exp != "ok":
            pelp = 1
    xv = None if x7 is None else X(x7 & 0xFFFFFFFF, x7 & 0xFFFFFFFFFFFFFFFF)
    return land(t, mode, j, tg, exp, desc, x7=xv, pelp=pelp if pelp_check else None)


# ---------------------------------------------------------------- enables
def menvcfg_lpe(t: TestFile, on: bool) -> None:
    """menvcfg.LPE from S (T-SBI) or M (direct)."""
    t.comment(f"menvcfg.LPE = {int(on)}")
    if t.cur == "M":
        t.emit(f"{'csrsi' if on else 'csrci'} {CSR['menvcfg']:#x}, {LPE}  // menvcfg")
    else:
        t.tsbi_csr("SET" if on else "CLEAR", "MENVCFG", imm=LPE)


def senvcfg_lpe(t: TestFile, on: bool) -> None:
    t.comment(f"senvcfg.LPE = {int(on)}")
    t.emit(f"{'csrsi' if on else 'csrci'} {CSR['senvcfg']:#x}, {LPE}  // senvcfg")


def henvcfg_lpe(t: TestFile, on: bool) -> None:
    t.comment(f"henvcfg.LPE = {int(on)}")
    t.emit(f"{'csrsi' if on else 'csrci'} {CSR['henvcfg']:#x}, {LPE}  // henvcfg")


def mlpe(t: TestFile, on: bool) -> None:
    t.comment(f"mseccfg.MLPE = {int(on)}")
    t.li("x5", MLPE)
    t.emit(f"{'csrs' if on else 'csrc'} {CSR['mseccfg']:#x}, x5  // mseccfg")


def s_enables(t: TestFile, s: bool, u: bool, vs: bool | None = None) -> None:
    """From S-mode: menvcfg.LPE (S), senvcfg.LPE (U and VU), henvcfg.LPE (VS, with H)."""
    menvcfg_lpe(t, s)
    senvcfg_lpe(t, u)
    if vs is not None:
        with t.only_if(H):
            henvcfg_lpe(t, vs)


def s_teardown(t: TestFile) -> None:
    s_enables(t, False, False, False)


def new(suite: str, rule: str, *, sm: bool = False, required: list[str] | None = None) -> TestFile:
    """A test that boots to S-mode, or (sm) its M-mode _Sm part."""
    req = required or (REQ_M if sm else REQ_S)
    return TestFile(
        suite, rule, required=req, march=MARCH, boot="M" if sm else "S", suffix="_Sm" if sm else "", pool=POOL_TRAP
    )


# ---------------------------------------------------------------- the enable model (cfi.adoc, FCFIACT)
def enforced(mode: str, en: dict, s_impl: bool = True) -> bool:
    """xLPE for mode, from the enables en = {mlpe, menvcfg, senvcfg, henvcfg} (missing keys are 0). Mutants model
    a hart that reads the wrong enable."""
    g = lambda k: bool(en.get(k, 0))
    if mode == "M":
        if MUT == "mlpe_ignored":
            return g("menvcfg")
        return g("mlpe")
    if MUT == "mlpe_enables_all" and g("mlpe"):
        return True
    if mode == "S":
        return g("senvcfg") if MUT == "senvcfg_enables_s" else g("menvcfg")
    if mode == "U":
        if not s_impl:
            return g("menvcfg")
        return g("menvcfg") if MUT == "menvcfg_enables_u" else g("senvcfg")
    if mode == "VS":
        return g("menvcfg") if MUT == "henvcfg_ignored" else g("henvcfg")
    if mode == "VU":
        return g("henvcfg") if MUT == "vu_uses_henvcfg" else g("senvcfg")
    raise ValueError(mode)


def rep_cases(t: TestFile, mode: str, on: bool, tag: str, short: bool = False) -> None:
    """Representative landing-pad cases in mode, where Zicfilp is enforced iff on: an indirect jump and call to a
    non-lpad (fault iff on), to lpad 0 and to a matching labeled lpad (no fault), to a mismatched labeled lpad and
    (with C) a misaligned lpad (fault iff on), a software-guarded jump and a return (no fault), and an indirect
    jump to ebreak (cause 18 with xPELP=1 iff on, else a breakpoint with xPELP=0: ELP is not even set)."""
    lab = 0x2A5C3
    lp_case(t, mode, J("jalr", 0, 6), nonlp(), f"{tag}: indirect jump", on)
    lp_case(t, mode, J("jalr", 1, 8), nonlp(), f"{tag}: indirect call", on)
    lp_case(t, mode, J("jalr", 0, 6), ebreak(), f"{tag}: indirect jump to ebreak", on)
    if short:
        return
    lp_case(t, mode, J("jalr", 0, 9), lp(0), f"{tag}: lpad 0", on)
    lp_case(t, mode, J("jalr", 0, 6), lp(lab), f"{tag}: matching label", on, x7=lab << 12)
    lp_case(t, mode, J("jalr", 0, 6), lp(lab), f"{tag}: mismatched label", on, x7=(lab ^ 0x10) << 12)
    lp_case(t, mode, J("jalr", 0, 7), nonlp(), f"{tag}: software-guarded jump (x7)", on)
    lp_case(t, mode, J("jalr", 0, 1), nonlp(), f"{tag}: return (x1)", on)
    with t.only_if(ZCA):
        lp_case(t, mode, J("jalr", 0, 6), lp(0, misalign=True), f"{tag}: misaligned lpad", on)


# ---------------------------------------------------------------- M-mode state helpers (cur = M)
def m_set(t: TestFile, csr: str, bits: int, on: bool, note: str = "") -> None:
    t.comment(note or f"{csr} {'|=' if on else '&= ~'} {bits:#x}")
    t.li("x5", bits) if bits < (1 << 31) else t.load("x5", bits)
    t.emit(f"{'csrs' if on else 'csrc'} {csr}, x5")


def mpelp_set(t: TestFile, on: bool) -> None:
    """M-mode: mstatus.MPELP (mstatush on RV32)."""
    t.comment(f"mstatus.MPELP = {int(on)}")
    with t.rv64_only():
        t.li("x5", 1)
        t.emit("slli x5, x5, 41")
        t.emit(f"{'csrs' if on else 'csrc'} mstatus, x5")
    with t.rv32_only():
        t.li("x5", MPELP_H)
        t.emit(f"{'csrs' if on else 'csrc'} {CSR['mstatush']:#x}, x5  // mstatush")


def mpelp_read(t: TestFile, reg: str) -> None:
    with t.rv64_only():
        t.emit(f"csrr {reg}, mstatus")
        t.emit(f"srli {reg}, {reg}, 41")
    with t.rv32_only():
        t.emit(f"csrr {reg}, {CSR['mstatush']:#x}  // mstatush")
        t.emit(f"srli {reg}, {reg}, 9")
    t.emit(f"andi {reg}, {reg}, 1")


def mpv_set(t: TestFile, on: bool) -> None:
    with t.rv64_only():
        t.li("x5", 1)
        t.emit("slli x5, x5, 39")
        t.emit(f"{'csrs' if on else 'csrc'} mstatus, x5  // MPV")
    with t.rv32_only():
        t.li("x5", MPV_H)
        t.emit(f"{'csrs' if on else 'csrc'} {CSR['mstatush']:#x}, x5  // mstatush.MPV")


def save_csr(t: TestFile, csr: str, slot: str) -> None:
    """Save a CSR (current mode) to a data word."""
    if not any(f"{slot}:" in ln for ln in t.extra_data):
        t.extra_data += ["  .p2align 3", f"{slot}:", "  .dword 0"]
    t.emit(f"csrr x5, {csr}")
    t.emit(f"LA(x4, {slot})", 2)
    t.emit("SREG x5, 0(x4)")


def restore_csr(t: TestFile, csr: str, slot: str) -> None:
    t.emit(f"LA(x4, {slot})", 2)
    t.emit("LREG x5, 0(x4)")
    t.emit(f"csrw {csr}, x5")


# ---------------------------------------------------------------- xRET into a target
def xret_case(
    t: TestFile,
    kind: str,
    y: str,
    xpelp: int,
    tg: T,
    expect: Expect,
    desc: str,
    *,
    frm: str | None = None,
    after_pelp: bool = False,
    x7: Value | None = None,
    pelp: int | None = None,
) -> str:
    """Execute kind (sret or mret) in mode frm (default t.cur; VS is entered first) with xPELP = xpelp and the
    previous mode y, returning to target tg. expect: the outcome at the target (cause 18 when ELP is restored to
    LP_EXPECTED and tg is not a valid lpad). after_pelp: y == frm, check that xPELP reads 0 after the xret."""
    frm = frm or t.cur
    tgt, landl, sec = t.label("tgt"), t.label("land"), t.label("second")
    t.comment(f"{desc}: {kind} in {frm}-mode to {y}-mode with xPELP={xpelp} -> {tg.note}")
    set_resume(t, landl)
    t.allow(1)
    if frm != t.cur:
        t.enter(frm)
    if x7 is not None:
        t.load("x7", x7, "x7: expected landing-pad label in bits 31:12")
    t.emit(f"LA(x6, {tgt})", 2)
    if kind == "mret":
        assert frm == "M"
        t.emit("csrw mepc, x6")
        t.li("x6", 0x1800)
        t.emit("csrc mstatus, x6  // MPP = U")
        mpp = {"M": 0x1800, "S": 0x800, "VS": 0x800, "U": 0, "VU": 0}[y]
        if mpp:
            t.li("x6", mpp)
            t.emit(f"csrs mstatus, x6  // MPP = {y}")
        with t.only_if(H):
            mpv_set(t, y in ("VS", "VU"))
        mpelp_set(t, bool(xpelp))
    else:
        t.emit("csrw sepc, x6")
        t.li("x6", SPP)
        t.emit(f"{'csrs' if y in ('S', 'VS') else 'csrc'} sstatus, x6  // SPP")
        if frm in ("S", "M"):
            with t.only_if(H):
                t.li("x6", 1 << 7)
                t.emit(f"{'csrs' if y in ('VS', 'VU') else 'csrc'} {CSR['hstatus']:#x}, x6  // hstatus.SPV")
        t.li("x6", SPELP)
        t.emit(f"{'csrs' if xpelp else 'csrc'} sstatus, x6  // SPELP = {xpelp}")
    lab = t.label("xret")
    t.emit(f"{lab}:", 0)
    t.emit(kind)
    emit_target(t, tg, tgt, landl, sec, data_word(t) if any("DATAW" in ln for ln in tg.lines) else "")
    if after_pelp:
        if kind == "mret":
            mpelp_read(t, "x9")
        else:
            t.emit("csrr x9, sstatus")
            t.emit("srli x9, x9, 23")
            t.emit("andi x9, x9, 1")
    clear_resume(t)
    back = y != t.cur
    if back:
        t.leave()
    alts = expect if isinstance(expect, list) else [expect]
    tval = None
    if SWCHK in alts:
        tval = LP_TVAL if MUT != "tval_target" else [tgt]
    elif tg.tval == "TGT0":
        tval = [0, sec if tg.second else tgt]
    epc = sec if tg.second and SWCHK not in alts else tgt
    t.outcome(expect, epc, f"{desc} ({kind} from {frm} to {y}, xPELP={xpelp}, -> {tg.note})", tval, origin=y)
    if pelp is not None and len(alts) == 1 and alts[0] != "ok":
        check_pelp(t, pelp, tgt, desc)
    if after_pelp:
        exp = 1 if (MUT == "xret_keeps_pelp" and xpelp) else 0
        t.check("x9", exp, lab, f"{desc}: {kind} sets xPELP to NO_LP_EXPECTED (0)")
    return tgt


def xret_expect(y: str, xpelp: int, tg: T, en: dict, s_impl: bool = True, frm: str = "S") -> Expect:
    """Expected outcome at an xRET target (cfi.adoc, Zicfilp_pelp_trap_return)."""
    on = enforced(y, en, s_impl)
    if MUT == "xret_uses_cur_lpe":
        on = enforced(frm, en, s_impl)
    elp = xpelp and (on or MUT == "xret_ignores_lpe")
    if MUT == "xret_no_restore":
        elp = 0
    if elp and lp_faults(tg, None):
        return SWCHK
    return tg.traps
