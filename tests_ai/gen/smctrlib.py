# SPDX-License-Identifier: Apache-2.0
"""Helpers for the Smctr and Ssctr suites (control transfer records, src/priv/smctr.adoc).

Measurement pattern. CTR records every qualified transfer of an enabled mode, including the test's own branches,
so each measurement is bracketed:

    sctrctl = 0                  CTR inactive in S-mode
    anchor                       sctrstatus = 0 (WRPTR = 0, FROZEN = 0), then SCTRCLR (all entries 0)
    sctrctl = <configuration>
    <the transfers under test>   straight-line code, or a trap window
    sctrctl = 0
    read sctrstatus.WRPTR and the entries through siselect/sireg*

With WRPTR = 0 at the anchor, the k-th record after it (k = 0 for the first) is logical entry WRPTR - 1 - k as long
as fewer than depth records were made. Traps between two enabled modes also record the framework trap handler's own
transfers after the trap itself, so those tests check only the first records after the anchor.

The tests never call T-SBI between the anchor and the read-out: mctrctl is not in the T-SBI table and has no
specified reset value, so S-level tests cannot rely on mctrctl.M or mctrctl.MTE (recording of M-mode code, and of
external traps into M-mode).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, TypeVar

from aigen import POOL_TRAP, TestFile, X

if TYPE_CHECKING:
    from collections.abc import Callable

    from aigen import Expect

T = TypeVar("T")
SRC = "src/priv/smctr.adoc"
ISSUE = "https://github.com/riscv/riscv-isa-manual/issues/"
MARCH = "rv${XLEN}i_zicsr_zifencei"
H = "defined(H_SUPPORTED)"
C = "defined(ZCA_SUPPORTED)"
SSCOFPMF = "defined(SSCOFPMF_SUPPORTED)"
LCOF = "defined(SSCOFPMF_SUPPORTED) && defined(RVMODEL_MHPMEVENT_VAL)"
RV32_C = "__riscv_xlen == 32 && defined(ZCA_SUPPORTED)"

CSR = {
    "sctrctl": 0x14E,
    "sctrstatus": 0x14F,
    "sctrdepth": 0x15F,
    "vsctrctl": 0x24E,
    "mctrctl": 0x34E,
    "siselect": 0x150,
    "sireg": 0x151,
    "sireg2": 0x152,
    "sireg3": 0x153,
    "sireg4": 0x155,
    "sireg5": 0x156,
    "sireg6": 0x157,
    "vsiselect": 0x250,
    "vsireg": 0x251,
    "vsireg2": 0x252,
    "vsireg3": 0x253,
    "vsireg4": 0x255,
    "vsireg5": 0x256,
    "vsireg6": 0x257,
}
SIREGS = ["sireg", "sireg2", "sireg3", "sireg4", "sireg5", "sireg6"]
SCTRCLR = 0x10400073

# xctrctl fields
U, S, M = 0x1, 0x2, 0x4
RASEMU, STE, MTE, BPFRZ, LCOFIFRZ = 0x80, 0x100, 0x200, 0x800, 0x1000
EXCINH, INTRINH, TRETINH, NTBREN, TKBRINH = 1 << 33, 1 << 34, 1 << 35, 1 << 36, 1 << 37
INDCALLINH, DIRCALLINH, INDJMPINH, DIRJMPINH = 1 << 40, 1 << 41, 1 << 42, 1 << 43
CORSWAPINH, RETINH, INDLJMPINH, DIRLJMPINH = 1 << 44, 1 << 45, 1 << 46, 1 << 47
CUSTOM = 0xF << 60
FILTERS = {
    "EXCINH": EXCINH,
    "INTRINH": INTRINH,
    "TRETINH": TRETINH,
    "NTBREN": NTBREN,
    "TKBRINH": TKBRINH,
    "INDCALLINH": INDCALLINH,
    "DIRCALLINH": DIRCALLINH,
    "INDJMPINH": INDJMPINH,
    "DIRJMPINH": DIRJMPINH,
    "CORSWAPINH": CORSWAPINH,
    "RETINH": RETINH,
    "INDLJMPINH": INDLJMPINH,
    "DIRLJMPINH": DIRLJMPINH,
}
# Bits that are fields of mctrctl (all but WPRI); sctrctl and vsctrctl lack M (2) and MTE (9).
MFIELDS = U | S | M | RASEMU | STE | MTE | BPFRZ | LCOFIFRZ | sum(FILTERS.values()) | CUSTOM
SFIELDS = MFIELDS & ~(M | MTE)
# sctrstatus
FROZEN = 1 << 31
# ctrdata: TYPE 3:0, CCV 15, CC 31:16; bits 14:4 and 63:32 are WPRI
CTRDATA_WPRI = X(0x7FF0, 0xFFFFFFFF00007FF0)

# transfer types (ctrdata.TYPE)
T_EXC, T_INT, T_TRET, T_NTBR, T_TKBR = 1, 2, 3, 4, 5
T_INDCALL, T_DIRCALL, T_INDJMP, T_DIRJMP, T_CORSWAP, T_RET, T_INDLJMP, T_DIRLJMP = 8, 9, 10, 11, 12, 13, 14, 15

ILLEGAL, BREAK, VIRTUAL = 2, 3, 22
SSI_CAUSE = X((1 << 31) | 1, (1 << 63) | 1)
LCOFI_CAUSE = X((1 << 31) | 13, (1 << 63) | 13)
SPP = 0x100
SPIE = 0x20


def mut() -> str:
    """The active mutant (read at call time: mutate.py reloads only the generator module)."""
    return os.environ.get("AI_MUTANT", "")


def lo(v: int) -> X:
    """A 64-bit xctrctl value as written by each XLEN: RV32 reaches only bits 31:0."""
    return X(v & 0xFFFFFFFF, v)


def c(name: str) -> str:
    """CSR operand for the assembler (numbers, so older binutils without the CTR names also work)."""
    return f"0x{CSR[name]:03x}"


def new(
    suite: str, rule: str, required: list | None = None, boot: str = "S", rv64: bool = False, suffix: str = ""
) -> TestFile:
    t = TestFile(
        suite,
        rule,
        required=required or ["I", "S", "Ssctr"],
        boot=boot,
        pool=POOL_TRAP,
        march=MARCH,
        rv64=rv64,
        suffix=suffix,
    )
    t.comment("xctrctl reset values are UNSPECIFIED: stop recording in every mode the test can reach")
    if t.cur == "M":
        t.emit(f"csrw {c('mctrctl')}, x0  // mctrctl = 0 (sctrctl too)")
    else:
        off(t)
    t.emit("#ifdef H_SUPPORTED", 0)
    t.emit(f"csrw {c('vsctrctl')}, x0  // vsctrctl = 0")
    t.emit("#endif", 0)
    return t


# ---------------------------------------------------------------- CSR access
def wr(t: TestFile, name: str, value: int | X, reg: str = "x6", note: str = "") -> None:
    """csrw name, value. value may be an X pair or an int (64-bit xctrctl values are cut to bits 31:0 on RV32)."""
    note = note or f"{name} = {value if isinstance(value, X) else hex(value)}"
    if value == 0:
        t.emit(f"csrw {c(name)}, x0  // {note}")
        return
    if isinstance(value, int) and 0 <= value < 32:
        t.emit(f"csrwi {c(name)}, {value}  // {note}")
        return
    if isinstance(value, int) and -2048 <= value < 2048:
        t.emit(f"li {reg}, {value}")
    else:
        t.load(reg, value if isinstance(value, X) else lo(value), note)
    t.emit(f"csrw {c(name)}, {reg}  // {note}")


def rd(t: TestFile, reg: str, name: str) -> None:
    t.emit(f"csrr {reg}, {c(name)}  // {name}")


def sctrclr(t: TestFile) -> None:
    t.emit(f".word 0x{SCTRCLR:08x}  // sctrclr")


def anchor(t: TestFile) -> None:
    """WRPTR = 0, FROZEN = 0, all entries 0. CTR must be inactive (sctrctl = 0)."""
    t.emit(f"csrw {c('sctrstatus')}, x0  // sctrstatus = 0: WRPTR = 0, FROZEN = 0")
    sctrclr(t)


def off(t: TestFile, name: str = "sctrctl") -> None:
    t.emit(f"csrw {c(name)}, x0  // {name} = 0: stop recording")


def nrec(t: TestFile, reg: str = "x9") -> None:
    """reg = sctrstatus.WRPTR: after an anchor, the number of records made (fewer than depth)."""
    rd(t, reg, "sctrstatus")
    t.emit(f"andi {reg}, {reg}, 0xff  // WRPTR")


def check_n(t: TestFile, n: Expect, desc: str, reg: str = "x9") -> None:
    lab = t.label("n")
    t.emit(f"{lab}:", 0)
    nrec(t, reg)
    t.check(reg, n, lab, f"{desc}: number of records (sctrstatus.WRPTR after the anchor)")


def check_n_ge(t: TestFile, k: int, desc: str, reg: str = "x9") -> None:
    """At least k records since the anchor (branch-free predicate)."""
    lab = t.label("nge")
    t.emit(f"{lab}:", 0)
    nrec(t, reg)
    t.emit(f"sltiu {reg}, {reg}, {k}")
    t.emit(f"xori {reg}, {reg}, 1")
    t.check_bool(reg, lab, f"{desc}: at least {k} record(s) since the anchor")


def select(t: TestFile, logical: int | None = None, k: int | None = None, reg: str = "x9", vs: bool = False) -> None:
    """siselect = 0x200 + logical entry; with k, the k-th record after the anchor (WRPTR - 1 - k)."""
    sel = "vsiselect" if vs else "siselect"
    if logical is not None:
        t.emit(f"li {reg}, {0x200 + logical}")
    else:
        assert k is not None
        nrec(t, reg)
        t.emit(f"addi {reg}, {reg}, {0x200 - 1 - k}  // logical entry of record {k} after the anchor")
    t.emit(f"csrw {c(sel)}, {reg}  // {sel}")


def entry(t: TestFile, regs: tuple[str, str, str] = ("x6", "x7", "x8"), vs: bool = False) -> None:
    p = "vs" if vs else "s"
    for r, n in zip(regs, ("ireg", "ireg2", "ireg3")):
        t.emit(f"csrr {r}, {c(p + n)}  // {p + n}")


def check_entry(
    t: TestFile,
    desc: str,
    src: Expect | None = None,
    tgt: Expect | None = None,
    typ: int | None = None,
    logical: int | None = None,
    k: int | None = None,
    wpri: bool = True,
) -> str:
    """Read one entry and check it. src/tgt are expected PCs: a label (str) means a recorded transfer at that pc
    (ctrsource = pc | V, ctrtarget = pc, MISP free); 0 means a partial record (ctrsource = V only / ctrtarget PC 0).
    A list of raw values is checked as given. typ: ctrdata.TYPE is typ or 0 (TYPE optional)."""
    lab = t.label("ent")
    t.emit(f"{lab}:", 0)
    select(t, logical=logical, k=k)
    entry(t)
    where = f"logical entry {logical}" if logical is not None else f"record {k} after the anchor"
    if src is not None:
        exp = src if isinstance(src, list) else (1 if src == 0 else (f"{src}+1" if isinstance(src, str) else src))
        t.check("x6", exp, lab, f"{desc}: {where} ctrsource (PC | V=1)")
    if tgt is not None:
        if isinstance(tgt, list):
            exp_t = tgt
        elif tgt == 0:
            exp_t = [0, 1]
        else:
            exp_t = [tgt, f"{tgt}+1"]
        t.check("x7", exp_t, lab, f"{desc}: {where} ctrtarget (PC, MISP may be set)")
    if typ is not None:
        t.check_masked(
            "x8", 0xF, [0, typ], lab, f"{desc}: {where} ctrdata.TYPE is {typ} (or 0 if TYPE is unimplemented)"
        )
    if wpri:
        t.check_masked("x8", CTRDATA_WPRI, 0, lab, f"{desc}: {where} ctrdata WPRI bits read 0")
    return lab


def check_empty(t: TestFile, logical: int, desc: str) -> None:
    lab = t.label("empty")
    t.emit(f"{lab}:", 0)
    select(t, logical=logical)
    entry(t)
    t.emit("or x6, x6, x7")
    t.emit("or x6, x6, x8")
    t.check("x6", 0, lab, f"{desc}: logical entry {logical} reads 0 in ctrsource, ctrtarget and ctrdata")


def check_tgt_handler(t: TestFile, desc: str, tvec: str = "stvec", cause: int = 0, reg: str = "x7") -> None:
    """ctrtarget (in reg, from entry()) is the trap handler: xtvec.BASE, plus 4*cause for an interrupt in vectored
    mode. MISP is ignored. Clobbers x5, x9."""
    lab = t.label("tvec")
    t.emit(f"{lab}:", 0)
    t.emit(f"csrr x9, {tvec}")
    if cause:
        t.emit("andi x5, x9, 1  // vectored mode")
        t.emit("neg x5, x5")
        t.emit(f"andi x5, x5, {4 * cause}")
        t.emit("andi x9, x9, -4")
        t.emit("add x9, x9, x5")
    else:
        t.emit("andi x9, x9, -4")
    t.emit(f"andi {reg}, {reg}, -2  // drop MISP")
    t.emit(f"xor {reg}, {reg}, x9")
    t.emit(f"seqz {reg}, {reg}")
    t.check_bool(reg, lab, f"{desc}: ctrtarget is the {tvec} handler address")


def check_src_epc(t: TestFile, desc: str, reg: str = "x6") -> None:
    """ctrsource (in reg) is the logged trap's xepc | V. Clobbers x4, x5, x15."""
    lab = t.label("epc")
    t.emit(f"{lab}:", 0)
    t.emit("AI_LOG(x15, TRAPLOG_EPC)", 10)
    t.emit("ori x15, x15, 1")
    t.emit(f"xor {reg}, {reg}, x15")
    t.emit(f"seqz {reg}, {reg}")
    t.check_bool(reg, lab, f"{desc}: ctrsource is the interrupted pc (logged xepc) | V")


def not_first(t: TestFile, src: str, desc: str) -> None:
    """The first record after the anchor, if any, is not the transfer at label src: either no record was made, or
    the first one has another ctrsource. Clobbers x6-x9."""
    lab = t.label("notrec")
    t.emit(f"{lab}:", 0)
    nrec(t, "x8")
    t.emit("snez x9, x8  // 1 when a record exists")
    t.emit("addi x8, x8, 0x1ff  // 0x200 + WRPTR - 1: the first record")
    t.emit("neg x9, x9")
    t.emit("and x8, x8, x9")
    t.emit("not x9, x9")
    t.emit("andi x9, x9, 0x200")
    t.emit("or x8, x8, x9  // or logical entry 0 (zero since the anchor) when there is no record")
    t.emit(f"csrw {c('siselect')}, x8")
    t.emit(f"csrr x6, {c('sireg')}")
    t.la("x7", src)
    t.emit("ori x7, x7, 1")
    t.emit("xor x6, x6, x7")
    t.emit("snez x6, x6")
    t.check_bool("x6", lab, f"{desc}: the first record after the anchor is not the transfer at {src}")


# ---------------------------------------------------------------- run-time probes
def probe_ctl(t: TestFile, reg: str, bits: int, name: str = "sctrctl") -> None:
    """reg = bits of name that are implemented (write bits, read back, mask, then write 0). Uses x5."""
    t.load("x5", lo(bits), f"probe {name} bits")
    t.emit(f"csrw {c(name)}, x5")
    t.emit(f"csrr {reg}, {c(name)}")
    t.emit(f"and {reg}, {reg}, x5")
    t.emit(f"csrw {c(name)}, x0")


def depth_set(t: TestFile, enc: int, reg: str = "x9") -> None:
    """Write sctrdepth.DEPTH = enc and read back the legal value it became (reg = DEPTH)."""
    t.emit(f"li {reg}, {enc}")
    t.emit(f"csrw {c('sctrdepth')}, {reg}  // sctrdepth.DEPTH = {enc} (WARL)")
    t.emit(f"csrr {reg}, {c('sctrdepth')}")
    t.emit(f"andi {reg}, {reg}, 7")


def depth_pick(t: TestFile, largest: bool, reg: str = "x9") -> None:
    """Select the largest (or smallest) supported depth: write DEPTH = 4, 3, ... (or 0, 1, ...) until one reads back
    as written (a WARL write of an unsupported value may keep the old value). reg = the DEPTH selected. Uses x5;
    CTR must be inactive (the branches would be recorded)."""
    order = [4, 3, 2, 1, 0] if largest else [0, 1, 2, 3, 4]
    done = t.label("dsel")
    for i, e in enumerate(order):
        depth_set(t, e, reg)
        if i < len(order) - 1:
            t.emit(f"li x5, {e}")
            t.emit(f"beq {reg}, x5, {done}")
    t.emit(f"{done}:", 0)


def depth_entries(t: TestFile, dreg: str, out: str) -> None:
    """out = 16 << DEPTH (dreg)."""
    t.emit("li x5, 16")
    t.emit(f"sll {out}, x5, {dreg}  // depth = 16 << DEPTH")


# ---------------------------------------------------------------- transfers
class Xfer:
    """One control transfer emitted at a label, with its expected record."""

    def __init__(self, src: str, tgt: str | int, typ: int, desc: str) -> None:
        self.src, self.tgt, self.typ, self.desc = src, tgt, typ, desc


def jal(t: TestFile, rd: str, desc: str = "") -> Xfer:
    """jal rd over an illegal word to the following label: a taken jump whose target is not pc+4."""
    src, tgt = t.label("jal"), t.label("jalt")
    t.emit(f"{src}: jal {rd}, {tgt}")
    t.emit(".word 0  // not reached")
    t.emit(f"{tgt}:", 0)
    typ = T_DIRCALL if rd in ("x1", "x5", "ra", "t0") else (T_DIRJMP if rd in ("x0", "zero") else T_DIRLJMP)
    return Xfer(src, tgt, typ, desc or f"jal {rd}")


def jalr_type(rd: str, rs: str) -> int:
    link = {"x1", "x5"}
    if rd in link:
        return T_CORSWAP if rs in link and rs != rd else T_INDCALL
    if rd == "x0":
        return T_RET if rs in link else T_INDJMP
    return T_RET if rs in link else T_INDLJMP


def jalr(t: TestFile, rd: str, rs: str, desc: str = "") -> Xfer:
    """LA(rs, target); jalr rd, 0(rs) over an illegal word."""
    src, tgt = t.label("jalr"), t.label("jalrt")
    t.la(rs, tgt)
    t.emit(f"{src}: jalr {rd}, 0({rs})")
    t.emit(".word 0  // not reached")
    t.emit(f"{tgt}:", 0)
    return Xfer(src, tgt, jalr_type(rd, rs), desc or f"jalr {rd}, {rs}")


def branch(t: TestFile, op: str, a: int, b: int, ra: str = "x6", rb: str = "x7", desc: str = "") -> Xfer:
    """A taken conditional branch over an illegal word. Operands are loaded first."""
    src, tgt = t.label("br"), t.label("brt")
    t.li(ra, a)
    t.li(rb, b)
    t.emit(f"{src}: {op} {ra}, {rb}, {tgt}")
    t.emit(".word 0  // not reached")
    t.emit(f"{tgt}:", 0)
    return Xfer(src, tgt, T_TKBR, desc or f"taken {op} ({a}, {b})")


def nt_branch(t: TestFile, op: str, a: int, b: int, ra: str = "x6", rb: str = "x7", desc: str = "") -> Xfer:
    """A not-taken conditional branch; its taken target is an illegal word placed by nt_fixup()."""
    src, nxt = t.label("nt"), t.label("ntn")
    t.li(ra, a)
    t.li(rb, b)
    bad = t.label("ntbad")
    t.emit(f"{src}: {op} {ra}, {rb}, {bad}")
    t.emit(f"{nxt}:", 0)
    _NTBAD.setdefault(id(t), []).append(bad)
    return Xfer(src, nxt, T_NTBR, desc or f"not-taken {op} ({a}, {b})")


_NTBAD: dict[int, list[str]] = {}  # per test: the illegal words that wrongly taken branches land on


def nt_fixup(t: TestFile) -> None:
    """Emit the illegal words that wrongly taken branches land on (after recording is stopped)."""
    bads = _NTBAD.pop(id(t), [])
    if not bads:
        return
    skip = t.label("ntskip")
    t.emit(f"j {skip}")
    for b in bads:
        t.emit(f"{b}: .word 0  // a not-taken branch must not reach this")
    t.emit(f"{skip}:", 0)


def rvc(t: TestFile, lines: list[str]) -> None:
    t.emit(".option push", 0)
    t.emit(".option arch, +c", 0)
    for ln in lines:
        t.emit(ln)
    t.emit(".option pop", 0)


def c_jump(t: TestFile, kind: str, rs: str = "x6") -> Xfer:
    """Compressed jumps (caller wraps in only_if(C)). Each transfer is 2 bytes; a c.nop pads the pair to 4 bytes
    so later 4-byte code stays aligned. kind: c.j, c.jal (RV32), c.jr, c.jalr."""
    src, tgt = t.label("cj"), t.label("cjt")
    if kind in ("c.jr", "c.jalr"):
        t.la(rs, tgt)
        insn = f"{kind} {rs}"
        typ = (T_RET if rs in ("x1", "x5") else T_INDJMP) if kind == "c.jr" else T_CORSWAP if rs == "x5" else T_INDCALL
    else:
        insn = f"{kind} {tgt}"
        typ = T_DIRJMP if kind == "c.j" else T_DIRCALL
    rvc(t, [f"{src}: {insn}", "c.ebreak  // not reached", f"{tgt}: c.nop", "c.nop  // keeps 4-byte alignment"])
    return Xfer(src, tgt, typ, kind + (f" {rs}" if kind in ("c.jr", "c.jalr") else ""))


def c_branch(t: TestFile, kind: str, val: int, reg: str = "x8") -> Xfer:
    """c.beqz/c.bnez on x8 (a compressible register). Taken or not, depending on val."""
    src, tgt = t.label("cb"), t.label("cbt")
    t.li(reg, val)
    taken = (val == 0) == (kind == "c.beqz")
    if taken:
        rvc(t, [f"{src}: {kind} {reg}, {tgt}", "c.ebreak  // not reached", f"{tgt}: c.nop", "c.nop"])
        x = Xfer(src, tgt, T_TKBR, f"taken {kind} ({val})")
    else:
        bad = t.label("cbbad")
        rvc(t, [f"{src}: {kind} {reg}, {bad}", f"{tgt}: c.nop"])
        _NTBAD.setdefault(id(t), []).append(bad)
        x = Xfer(src, tgt, T_NTBR, f"not-taken {kind} ({val})")
    return x


def sret_s(t: TestFile, h: bool = True) -> Xfer:
    """sret from S-mode back to S-mode (SPP=S, SPV=0, SPIE=0) to the label after an illegal word."""
    src, tgt = t.label("sret"), t.label("srett")
    t.la("x6", tgt)
    t.emit("csrw sepc, x6")
    t.li("x6", SPP)
    t.emit("csrs sstatus, x6  // SPP = S")
    t.li("x6", SPIE)
    t.emit("csrc sstatus, x6  // SPIE = 0 (SIE stays 0 after the sret)")
    if h:
        t.emit("#ifdef H_SUPPORTED", 0)
        t.emit("LI(x6, HSTATUS_SPV)", 2)
        t.emit("csrc CSR_HSTATUS, x6  // SPV = 0")
        t.emit("#endif", 0)
    t.emit(f"{src}: sret")
    t.emit(".word 0  // not reached")
    t.emit(f"{tgt}:", 0)
    return Xfer(src, tgt, T_TRET, "sret S->S")


def mret_m(t: TestFile) -> Xfer:
    """mret from M-mode back to M-mode (MPP=M, MPV=0, MPIE=0)."""
    src, tgt = t.label("mret"), t.label("mrett")
    t.la("x6", tgt)
    t.emit("csrw mepc, x6")
    t.emit("LI(x6, MSTATUS_MPP)", 2)
    t.emit("csrs mstatus, x6  // MPP = M")
    t.li("x6", 0x80)
    t.emit("csrc mstatus, x6  // MPIE = 0")
    t.emit("#ifdef H_SUPPORTED", 0)
    t.emit("#if __riscv_xlen == 64", 0)
    t.emit("li x6, 1")
    t.emit("slli x6, x6, 39")
    t.emit("csrc mstatus, x6  // MPV = 0")
    t.emit("#else", 0)
    t.emit("li x6, 0x80")
    t.emit("csrc CSR_MSTATUSH, x6  // MPV = 0")
    t.emit("#endif", 0)
    t.emit("#endif", 0)
    t.emit(f"{src}: mret")
    t.emit(".word 0  // not reached")
    t.emit(f"{tgt}:", 0)
    return Xfer(src, tgt, T_TRET, "mret M->M")


def check_xfer(t: TestFile, x: Xfer, desc: str, logical: int | None = None, k: int | None = None) -> None:
    check_entry(t, f"{desc}: {x.desc}", src=x.src, tgt=x.tgt, typ=x.typ, logical=logical, k=k)


def record_s(
    t: TestFile, ctl: int | X, body: Callable[[], list[Xfer]], desc: str, expect: bool | list[bool] = True
) -> list[Xfer]:
    """In S-mode: anchor, sctrctl = ctl, run body's transfers, stop, then check that exactly the transfers marked
    True in expect were recorded, in order (logical 0 is the youngest)."""
    anchor(t)
    wr(t, "sctrctl", ctl, note="sctrctl = configuration")
    xs = body()
    off(t)
    nt_fixup(t)
    exp = expect if isinstance(expect, list) else [expect] * len(xs)
    rec = [x for x, e in zip(xs, exp) if e]
    if mut() == "drop_last_record" and rec:
        rec = rec[:-1]
    check_n(t, len(rec), desc)
    for i, x in enumerate(reversed(rec)):
        check_xfer(t, x, desc, logical=i)
    return xs


# ---------------------------------------------------------------- mode windows
def win(
    t: TestFile,
    mode: str,
    body: Callable[[], T],
    expect: Expect = "ok",
    desc: str = "",
    tval: Expect | None = None,
) -> tuple[T, str, str]:
    """A trap window that runs body() in `mode` (entered from t.cur with sret/mret, left with a T-SBI GOTO).
    Returns body's result, the window label (the sret that enters `mode` is at <label>-4) and the label just before
    the GOTO (its ecall is at <goto>+4)."""
    lab = t.label(f"in_{mode}")
    t.allow(1)
    if mode != t.cur:
        t.enter(mode)
    t.emit(f"{lab}:", 0)
    res = body()
    goto = t.label("goto")
    t.emit(f"{goto}:", 0)
    if mode != t.cur:
        t.leave()
    t.outcome(expect, lab, f"{desc} in {mode}-mode", tval, origin=mode)
    return res, lab, goto


def ebreak_win(
    t: TestFile, mode: str, desc: str, cause: Expect = BREAK, more: list[str] | None = None
) -> tuple[str, str]:
    """ebreak in `mode` inside a trap window (xtval 0 or the pc); in S/M-mode `more` follows (e.g. stop recording)."""
    lab = t.label(f"eb_{mode}")
    t.allow(1)
    if mode != t.cur:
        t.enter(mode)
    t.emit(f"{lab}: ebreak")
    for ln in more or []:
        t.emit(ln)
    goto = t.label("goto")
    t.emit(f"{goto}:", 0)
    if mode != t.cur:
        t.leave()
    t.outcome(cause, lab, f"{desc}: ebreak in {mode}-mode", [0, lab], origin=mode)
    return lab, goto


def hedeleg(t: TestFile, bit: int, on: bool) -> None:
    t.li("x6", 1 << bit)
    t.emit(f"{'csrs' if on else 'csrc'} CSR_HEDELEG, x6  // hedeleg[{bit}] = {int(on)}")


def medeleg(t: TestFile, bit: int, on: bool) -> None:
    t.li("x6", 1 << bit)
    t.emit(f"{'csrs' if on else 'csrc'} medeleg, x6  // medeleg[{bit}] = {int(on)}")


# Rule text (norm: tags in src/priv/smctr.adoc, riscv-isa-manual upstream/main 717aeca3).
RULES = {
    "ctr_depth": "The number of records that can be held in the buffer depends upon both the implementation (the maximum supported depth) and the CTR configuration (the software selected depth).",
    "Smctr_scope": "The machine-level extension, *Smctr*, encompasses all newly added Control Status Registers (CSRs), instructions, and behavior modifications for a hart across all privilege levels.",
    "Ssctr_transfer_steps": "The corresponding supervisor-level extension, *Ssctr*, is essentially identical to Smctr, except that it excludes machine-level CSRs and behaviors not intended to be directly accessible at the supervisor level.",
    "Smctr_Ssctr_depend": "Smctr and Ssctr depend on both the implementation of S-mode and the Sscsrind extension.",
    "Ssctr_mctrctl_sz_acc_op": "The `mctrctl` register is a 64-bit read/write register that enables and configures the CTR capability.",
    "mctrctl_mode_op": "Enable transfer recording in the selected privileged mode(s).",
    "mctrctl_rasemu_op": "Enables RAS (Return Address Stack) Emulation Mode.",
    "mctrctl_mte_op": "Enables recording of traps to M-mode when M=0.",
    "mctrctl_ste_op": "Enables recording of traps to S-mode when S=0.",
    "mctrctl_bpfrz_op": "Set `sctrstatus`.FROZEN on a breakpoint exception that traps to M-mode or S-mode.",
    "mctrctl_lcofifrz_op": "Set `sctrstatus`.FROZEN on local-counter-overflow interrupt (LCOFI) that traps to M-mode or S-mode.",
    "mctrctl_excinh_op": "Inhibit recording of exceptions.",
    "mctrctl_intrinh_op": "Inhibit recording of interrupts.",
    "mctrctl_tretinh_op": "Inhibit recording of trap returns.",
    "mctrctl_ntbren_op": "Enable recording of not-taken branches.",
    "mctrctl_tkbrinh_op": "Inhibit recording of taken branches.",
    "mctrctl_indcallinh_op": "Inhibit recording of indirect calls.",
    "mctrctl_dircallinh_op": "Inhibit recording of direct calls.",
    "mctrctl_indjmpinh_op": "Inhibit recording of indirect jumps (without linkage).",
    "mctrctl_dirjmpinh_op": "Inhibit recording of direct jumps (without linkage).",
    "mctrctl_corswapinh_op": "Inhibit recording of co-routine swaps.",
    "mctrctl_retinh_op": "Inhibit recording of function returns.",
    "mctrctl_indljmpinh_op": "Inhibit recording of other indirect jumps (with linkage).",
    "mctrctl_dirljmpinh_op": "Inhibit recording of other direct jumps (with linkage).",
    "mctrctl_custom_op": "WARL bits designated for custom use.",
    "mctrctl_impl": "All fields are optional except for M, S, U, and BPFRZ. All unimplemented fields are read-only 0, while all implemented fields are writable. If the Sscofpmf extension is implemented, LCOFIFRZ must be writable.",
    "Ssctr_sctrctl_op": "The `sctrctl` register provides supervisor mode access to a subset of `mctrctl`.",
    "Ssctr_sctrctl_acc": "Bits 2 and 9 in `sctrctl` are read-only 0. As a result, the M and MTE fields in `mctrctl` are not accessible through `sctrctl`. All other `mctrctl` fields are accessible through `sctrctl`.",
    "Ssctr_vsctrctl_sz_acc_op": "If the H extension is implemented, the `vsctrctl` register is a 64-bit read/write register that is VS-mode's version of supervisor register `sctrctl`. When V=1, `vsctrctl` substitutes for the usual `sctrctl`, so instructions that normally read or modify `sctrctl` actually access `vsctrctl` instead.",
    "vsctrctl_s_op": "Enable transfer recording in VS-mode.",
    "vsctrctl_u_op": "Enable transfer recording in VU-mode.",
    "vsctrctl_ste_op": "Enables recording of traps to VS-mode when S=0.",
    "vsctrctl_bpfrz_op": "Set `sctrstatus`.FROZEN on a breakpoint exception that traps to VS-mode.",
    "vsctrctl_lcofifrz_op": "Set `sctrstatus`.FROZEN on local-counter-overflow interrupt (LCOFI) that traps to VS-mode.",
    "sctrdepth": "The 32-bit `sctrdepth` register specifies the depth of the CTR buffer.",
    "sctrdepth_depth_warl": "WARL field that selects the depth of the CTR buffer.",
    "sctrdepth_depth_entries_op": "The depth of the CTR buffer dictates the number of entries to which the hardware records transfers. For a depth of N, the hardware records transfers to entries 0..N-1. All <<_entry_registers, Entry Registers>> read as '0' and are read-only when the selected entry is in the range N to 255. When the depth is increased, the newly accessible entries contain unspecified but legal values.",
    "sctrdepth_depth": "It is implementation-specific which DEPTH value(s) are supported.",
    "sctrdepth_mode": "Attempts to access `sctrdepth` from VS-mode or VU-mode raise a virtual-instruction exception, unless CTR state enable access restrictions apply.",
    "sctrstatus": "The 32-bit `sctrstatus` register grants access to CTR status information and is updated by the hardware whenever CTR is active. CTR is active when the current privilege mode is enabled for recording and CTR is not frozen.",
    "sctrstatus_wrptr": "WARL field that indicates the physical CTR buffer entry to be written next. It is incremented after new transfers are recorded (see <<Behavior>>), though there are exceptions when `__x__ctrctl`.RASEMU=1, see <<RAS (Return Address Stack) Emulation Mode>>. For a given CTR depth (where depth = 2^(DEPTH+4)^), WRPTR wraps to 0 on an increment when the value matches depth-1, and to depth-1 on a decrement when the value is 0. Bits above those needed to represent depth-1 (e.g., bits 7:4 for a depth of 16) are read-only 0. On depth changes, WRPTR holds an unspecified but legal value.",
    "sctrstatus_frozen_op": "Inhibit transfer recording.",
    "Ssctr_sctrstatus_acc": "Undefined bits in `sctrstatus` are WPRI. Status fields may be added by future extensions, and software should ignore but preserve any fields that it does not recognize. Undefined bits must be implemented as read-only 0, unless a custom extension is implemented and enabled",
    "siselect_acc_op": "The `siselect` index range 0x200 through 0x2FF is reserved for CTR logical entries 0 through 255. When `siselect` holds a value in this range, `sireg` provides access to `ctrsource`, `sireg2` provides access to `ctrtarget`, and `sireg3` provides access to `ctrdata`. `sireg4`, `sireg5`, and `sireg6` are read-only 0.",
    "vsiselect_op": "When `vsiselect` holds a value in 0x200..0x2FF, the `vsireg*` registers provide access to the same CTR entry register state as the analogous `sireg*` registers. There is not a separate set of entry registers for V=1.",
    "ctrsource_op": "The `ctrsource` register contains the source program counter, which is the `pc` of the recorded control transfer instruction, or the epc of the recorded trap.",
    "ctrsource_ctrtarget_ctrdata_vbit": "The valid (V) bit is set by the hardware when a transfer is recorded in the selected CTR buffer entry, and implies that data in `ctrsource`, `ctrtarget`, and `ctrdata` is valid for this entry.",
    "Ssctr_ctrsource_sz_acc_op": "`ctrsource` is an MXLEN-bit WARL register that must be able to hold all valid virtual or physical addresses that can serve as a `pc`. It need not be able to hold any invalid addresses; implementations may convert an invalid address into a valid address that the register is capable of holding. When XLEN < MXLEN, both explicit writes (by software) and implicit writes (for recorded transfers) will be zero-extended.",
    "ctrtarget_op": "The `ctrtarget` register contains the target (destination) program counter of the recorded transfer.",
    "ctrtarget_pc_next_br": "For a not-taken branch, `ctrtarget` holds the PC of the next sequential instruction following the branch.",
    "ctrtarget_misp": "The optional MISP bit is set by the hardware when the recorded transfer is an instruction whose target or taken/not-taken direction was mispredicted by the branch predictor. MISP is read-only 0 when not implemented.",
    "ctrtarget_sz_acc": "`ctrtarget` is an MXLEN-bit WARL register that must be able to hold all valid virtual or physical addresses that can serve as a `pc`. It need not be able to hold any invalid addresses; implementations may convert an invalid address into a valid address that the register is capable of holding. When XLEN < MXLEN, both explicit writes (by software) and implicit writes (by recorded transfers) will be zero-extended.",
    "ctrdata_sz_acc": "The `ctrdata` register contains metadata for the recorded transfer. This register must be implemented, though all fields within it are optional. Unimplemented fields are read-only 0. `ctrdata` is a 64-bit register.",
    "ctrdata_type": "Identifies the type of the control flow transfer recorded in the entry, using the encodings listed in xref:transfer-type-defs[xrefstyle=short]. Implementations that do not support this field will report 0.",
    "ctrdata_ccv": "Cycle Count Valid.",
    "ctrdata_cc": "Cycle Count, composed of the Cycle Count Exponent (CCE, in CC[15:12]) and Cycle Count Mantissa (CCM, in CC[11:0]).",
    "ctrdata_undef": "Undefined bits in `ctrdata` are WPRI. Undefined bits must be implemented as read-only 0, unless a <<_custom_extensions, custom extension>> is implemented and enabled.",
    "sctrclr_zero_entries_op": "Zeroes all CTR <<_entry_registers, Entry Registers>>, for all DEPTH values",
    "sctrclr_zero_cycle_counter_op": "Zeroes the CTR cycle counter and CCV",
    "sctrclr_acc": "Any read of `ctrsource`, `ctrtarget`, or `ctrdata` that follows SCTRCLR, such that it precedes the next qualified control transfer, will return the value 0. Further, the first recorded transfer following SCTRCLR will have `ctrdata`.CCV=0.",
    "sctrclr_exceptions": "SCTRCLR raises an illegal-instruction exception in U-mode, and a virtual-instruction exception in VU-mode, unless CTR state enable access restrictions apply.",
    "mstateen_ctr1": "When `mstateen0`.CTR=1, accesses to CTR register state behave as described in <<CSRs>> and <<Entry Registers>> above, while SCTRCLR behaves as described in <<Supervisor CTR Clear Instruction>>.",
    "mstateen_ctr0": "When `mstateen0`.CTR=0 and the privilege mode is less privileged than M-mode, the following operations raise an illegal-instruction exception:",
    "mstateen_ctr0_except_csr_access": "Attempts to access `sctrctl`, `vsctrctl`, `sctrdepth`, or `sctrstatus`",
    "mstateen_ctr0_except_indirect_access": "Attempts to access `sireg*` when `siselect` is in 0x200..0x2FF, or `vsireg*` when `vsiselect` is in 0x200..0x2FF",
    "mstateen_ctr0_except_sctrclr": "Execution of the SCTRCLR instruction",
    "mstateen_ctr0_qualified_transfer": "When `mstateen0`.CTR=0, qualified control transfers executed in privilege modes less privileged than M-mode will continue to implicitly update entry registers and `sctrstatus`.",
    "hstateen_ctr": "If the H extension is implemented and `mstateen0`.CTR=1, the `hstateen0`.CTR bit controls access to supervisor CTR state when V=1. This state includes `sctrctl` (really `vsctrctl`), `sctrstatus`, and `sireg*` (really `vsireg*`) when `siselect` (really `vsiselect`) is in 0x200..0x2FF. `hstateen0`.CTR is read-only 0 when `mstateen0`.CTR=0.",
    "hstateen_vs": "When `mstateen0`.CTR=1 and `hstateen0`.CTR=1, VS-mode accesses to supervisor CTR state behave as described in <<CSRs>> and <<Entry Registers>> above, while SCTRCLR behaves as described in <<Supervisor CTR Clear Instruction>>. When `mstateen0`.CTR=1 and `hstateen0`.CTR=0, both VS-mode accesses to supervisor CTR state and VS-mode execution of SCTRCLR raise a virtual-instruction exception.",
    "hstateen0_ctr0_v1_op": "When `hstateen0`.CTR=0, qualified control transfers executed while V=1 will continue to implicitly update entry registers and `sctrstatus`.",
    "ctr_behavior": "CTR records qualified control transfers. Control transfers are qualified if they meet the following criteria:",
    "ctr_behavior_criteria_priv_mode": "The current privilege mode is enabled",
    "ctr_behavior_criteria_transfer_type": "The transfer type is not inhibited",
    "ctr_behavior_criteria_not_frozen": "`sctrstatus`.FROZEN is not set",
    "ctr_behavior_criteria_retires": "The transfer completes/retires",
    "ctr_stack": "Such qualified transfers update the <<_entry_registers, Entry Registers>> at logical entry 0. As a result, older entries are pushed down the stack; the record previously in logical entry 0 moves to logical entry 1, the record in logical entry 1 moves to logical entry 2, and so on. If the CTR buffer is full, the oldest recorded entry (previously at entry depth-1) is lost.",
    "ctr_validbit": "Recorded transfers will set the `ctrsource`.V bit to 1, and will update all implemented record fields.",
    "ctr_trap_enabled": "Traps between enabled privilege modes are recorded as normal.",
    "ctr_trap_disabled_src": "Traps from a disabled privilege mode to an enabled privilege mode are partially recorded, such that the `ctrsource`.PC is 0.",
    "ctr_trap_disabled_tgt": "Traps from an enabled mode to a disabled mode, known as external traps, are not recorded by default.",
    "ctr_trapret_enabled": "Trap returns between enabled privilege modes are recorded as normal.",
    "ctr_trapret_to_disabled": "Trap returns from an enabled mode back to a disabled mode are partially recorded, such that `ctrtarget`.PC is 0.",
    "ctr_trapret_from_disabled": "Trap returns from a disabled mode to an enabled mode are not recorded.",
    "debug_recording_inhibited": "Recording in Debug Mode is always inhibited. Transfers into and out of Debug Mode are never recorded.",
    "ctr_trap_ee": "Recorded",
    "ctr_trap_ed": "External trap. Not recorded by default,",
    "ctr_trap_de": "Recorded, `ctrsource`.PC is 0.",
    "ctr_trap_dd": "Not recorded.",
    "ctr_trapret_ee": "Recorded.",
    "ctr_trapret_ed": "Recorded, `ctrtarget`.PC is 0.",
    "ctr_trapret_de": "Not recorded.",
    "ctr_trapret_dd": "Not recorded.",
    "exttrap_def": "External traps are traps from a privilege mode enabled for CTR recording to a privilege mode that is not enabled for CTR recording. The `__x__ctrctl`.__x__TE bits allow M-mode, S-mode, and VS-mode to be enabled for CTR recording separately. When the `__x__ctrctl`.__x__TE bits are clear, external traps are not recorded.",
    "exttrap_requirements": "External trap recording depends not only on the target mode, but on any intervening modes, which are modes that are more privileged than the source mode but less privileged than the target mode. Not only must the external trap enable bit for the target mode be set, but the external trap enable bit(s) for any intervening modes must also be set.",
    "exttrap_us": "`sctrctl`.STE",
    "exttrap_um": "`mctrctl`.MTE, `sctrctl`.STE",
    "exttrap_Sm": "`mctrctl`.MTE",
    "exttrap_vuvs": "`vsctrctl`.STE",
    "exttrap_vuhs": "`sctrctl`.STE, `vsctrctl`.STE",
    "exttrap_vum": "`mctrctl`.MTE, `sctrctl`.STE, `vsctrctl`.STE",
    "exttrap_vshs": "`sctrctl`.STE",
    "exttrap_vsm": "`mctrctl`.MTE, `sctrctl`.STE",
    "exttrap_ctrtarget0": "In records for external traps, the `ctrtarget`.PC is 0.",
    "exttrap_implreq": "If external trap recording is implemented, `mctrctl`.MTE and `sctrctl`.STE must be implemented, while `vsctrctl`.STE must be implemented if the H extension is implemented.",
    "ctr_ttf_default": "Default CTR behavior, when all transfer type filter bits (`__x__ctrctl`[47:32]) are unimplemented or 0, is to record all control transfers within enabled privileged modes. By setting transfer type filter bits, software can opt out of recording select transfer types, or opt into recording non-default operations. All transfer type filter bits are optional.",
    "ctr_ttype0": "_Not used by CTR_",
    "ctr_ttype1": "Exception",
    "ctr_ttype2": "Interrupt",
    "ctr_ttype3": "Trap return",
    "ctr_ttype4": "Not-taken branch",
    "ctr_ttype5": "Taken branch",
    "ctr_ttype8": "Indirect call",
    "ctr_ttype9": "Direct call",
    "ctr_ttype10": "Indirect jump (without linkage)",
    "ctr_ttype11": "Direct jump (without linkage)",
    "ctr_ttype12": "Co-routine swap",
    "ctr_ttype13": "Function return",
    "ctr_ttype14": "Other indirect jump (with linkage)",
    "ctr_ttype15": "Other direct jump (with linkage)",
    "ctr_various_jump_enc": "Encodings 8 through 15 refer to various encodings of jump instructions. The types are distinguished as described below.",
    "ctrdata_cc_supported": "The `ctrdata` register may optionally include a count of CPU cycles elapsed since the prior CTR record. The elapsed cycle count value is represented by the CC field, which has a 12-bit mantissa component (Cycle Count Mantissa, or CCM) and a 4-bit exponent component (Cycle Count Exponent, or CCE).",
    "ctr_ccounter_inc": "The elapsed cycle counter (CtrCycleCounter) increments at the same rate as the `mcycle` counter. Only cycles while CTR is active are counted, where active implies that the current privilege mode is enabled for recording and CTR is not frozen. If the CtrCycleCounter value is less than 4096, the CC field is encoded with CCE holding 0 and CCM holding CtrCycleCounter bits 11:0. Otherwise, CCE holds the index of the most significant one bit in the CtrCycleCounter value, minus 11, and CCM holds CtrCycleCounter bits CCE+10:CCE-1.",
    "ctr_ccounter_reset": "The CtrCycleCounter is reset on writes to `__x__ctrctl`, and on execution of SCTRCLR, to ensure that any accumulated cycle counts do not persist across a context switch.",
    "ctr_ccounter_impl": "An implementation that supports cycle counting must implement CCV and all CCM bits, but may implement 0..4 exponent bits in CCE.",
    "ctr_ccounter_cce_rdonly0": "Unimplemented CCE bits are read-only 0.",
    "ctr_ccounter_sat": "The CC value saturates when all implemented bits in CCM and CCE are 1.",
    "ctr_ccounter_ccv": "The CC value is valid only when the Cycle Count Valid (CCV) bit is set. If CCV=0, the CC value might not hold the correct count of elapsed active cycles since the last recorded transfer. The next record will have CCV=0 after a write to `__x__ctrctl`, or execution of SCTRCLR, since CtrCycleCounter is reset. CCV should additionally be cleared after any other implementation-specific scenarios where active cycles might not be counted in CtrCycleCounter.",
    "ctrctl_rasemu_op": "When the optional `__x__ctrctl`.RASEMU bit is implemented and set to 1, transfer recording behavior is altered to emulate the behavior of a return-address stack (RAS).",
    "sctrstatus_frozen_inhibit": "When `sctrstatus`.FROZEN=1, transfer recording is inhibited.",
    "sctrstatus_frozen_set": "When `sctrctl`.LCOFIFRZ=1 and a local-counter-overflow interrupt (LCOFI) traps (as a result of an HPM counter overflow) to M-mode or to S-mode, `sctrstatus`.FROZEN is set by hardware. This inhibits CTR recording until software clears FROZEN. The LCOFI trap itself is not recorded.",
    "ctr_freeze_bp": "Similarly, on a breakpoint exception that traps to M-mode or S-mode with `sctrctl`.BPFRZ=1, FROZEN is set by hardware. The breakpoint exception itself is not recorded.",
    "ctr_freeze_vs": "If the H extension is implemented, freeze behavior for LCOFIs and breakpoint exceptions that trap to VS-mode is determined by the LCOFIFRZ and BPFRZ values, respectively, in `vsctrctl`. This includes virtual LCOFIs pended by a hypervisor.",
    "ctr_custom_bits": "Any custom CTR extension must be associated with a non-zero value within the designated custom bits in `__x__ctrctl`. When the custom bits hold a non-zero value that enables a custom extension, the extension may alter standard CTR behavior, and may define new custom status fields within `sctrstatus` or the CTR <<_entry_registers, Entry Registers>>. All custom status fields, and standard status fields whose behavior is altered by the custom extension, must revert to standard behavior when the custom bits hold zero. This includes read-only 0 behavior for any bits undefined by any implemented standard extensions.",
}


# ---------------------------------------------------------------- traps between enabled modes
DEEP_NOTE = (
    "A trap into an enabled mode also records the framework trap handler's own transfers (about 20) after the "
    "trap itself, so these measurements first select the largest supported depth (DEPTH written 4, 3, ... until one reads back as written) and check the "
    "first records after the anchor only when that depth is at least 64 (DEPTH >= 2); with a smaller maximum "
    "depth the early records may have been overwritten, and only 'logical entry 0 is valid' (some record was made) is checked."
)


def deep(t: TestFile) -> None:
    """Select the largest supported depth."""
    depth_pick(t, largest=True, reg="x9")


def deep_checks(t: TestFile, checks: Callable[[], object], desc: str) -> None:
    """Run checks() when the depth is at least 64 (DEPTH >= 2), else only require some record."""
    rd(t, "x9", "sctrdepth")
    t.emit("andi x9, x9, 7")
    t.emit("sltiu x9, x9, 2")
    t.emit("xori x9, x9, 1  // depth >= 64")
    t.either("x9", checks, lambda: check_valid0(t, desc))


def check_valid0(t: TestFile, desc: str) -> None:
    """Some record was made since the anchor: logical entry 0 is valid (WRPTR alone could have wrapped to 0)."""
    lab = t.label("v0")
    t.emit(f"{lab}:", 0)
    select(t, logical=0)
    t.emit(f"csrr x6, {c('sireg')}")
    t.emit("andi x6, x6, 1")
    t.check("x6", 1, lab, f"{desc}: logical entry 0 is valid (at least one record since the SCTRCLR)")


# ---------------------------------------------------------------- transfer types
def type_probe(t: TestFile) -> None:
    """Record one jal x0 and store whether ctrdata.TYPE is implemented (TYPE != 0) at ctr_tsup; its TYPE is 11 or
    0. Uses x6-x9."""
    if "ctr_tsup" not in "".join(t.extra_data):
        t.extra_data.append(".p2align 3\nctr_tsup: .dword 0")
    anchor(t)
    wr(t, "sctrctl", S)
    j = jal(t, "x0", "TYPE probe: jal x0")
    off(t)
    lab = check_entry(t, "TYPE probe", src=j.src, tgt=j.tgt, typ=T_DIRJMP, logical=0)
    t.emit("andi x8, x8, 0xf")
    t.emit("snez x8, x8  // TYPE implemented")
    t.la("x9", "ctr_tsup")
    t.emit("SREG x8, 0(x9)")
    del lab


def typed(t: TestFile, checks: Callable[[bool], object]) -> None:
    """Branch on the TYPE probe: checks(True) expects exact TYPE values, checks(False) expects TYPE 0."""
    t.la("x9", "ctr_tsup")
    t.emit("LREG x9, 0(x9)")
    t.either("x9", lambda: checks(True), lambda: checks(False))


def check_typed_records(t: TestFile, recs: list[Xfer], desc: str, exact: bool) -> None:
    for i, x in enumerate(reversed(recs)):
        lab = check_entry(t, f"{desc}: {x.desc}", src=x.src, tgt=x.tgt, logical=i)
        want = x.typ if exact else 0
        t.check_masked(
            "x8",
            0xF,
            want,
            lab,
            f"{desc}: {x.desc}: ctrdata.TYPE is {want} "
            f"({'TYPE is implemented, as probed' if exact else 'TYPE reads 0 in the probe'})",
        )


def record_typed(
    t: TestFile, ctl: int | X, body: Callable[[], list[Xfer]], desc: str, expect: bool | list[bool] = True
) -> list[Xfer]:
    """record_s with exact TYPE checks against the TYPE probe (call type_probe first)."""
    anchor(t)
    wr(t, "sctrctl", ctl, note="sctrctl = configuration")
    xs = body()
    off(t)
    nt_fixup(t)
    exp = expect if isinstance(expect, list) else [expect] * len(xs)
    rec = [x for x, e in zip(xs, exp) if e]
    check_n(t, len(rec), desc)
    typed(t, lambda ex: check_typed_records(t, rec, desc, ex))
    return xs


# ---------------------------------------------------------------- interrupts
def ssi_pend(t: TestFile, on: bool) -> None:
    t.emit(f"{'csrsi' if on else 'csrci'} sip, 2  // sip.SSIP = {int(on)}")


def ssi_enable(t: TestFile, on: bool) -> None:
    t.emit(f"{'csrsi' if on else 'csrci'} sie, 2  // sie.SSIE = {int(on)}")


def s_interrupt(t: TestFile, desc: str, ctl: int | X, after: list[str] | None = None) -> str:
    """S-mode software interrupt taken in S-mode: SIE=0, SSIE=1, SSIP=1, anchor, sctrctl = ctl, then csrsi sstatus.SIE
    in a window. The interrupt is taken at the next instruction; `after` lines run after the handler returns
    (default: stop recording). Returns the window label."""
    t.emit("csrci sstatus, 2  // SIE = 0")
    ssi_enable(t, True)
    ssi_pend(t, True)
    anchor(t)
    wr(t, "sctrctl", ctl, note="sctrctl = configuration")
    lab = t.label("ssi")
    t.allow(1)
    t.emit(f"{lab}: csrsi sstatus, 2  // SIE = 1: the pending SSI is taken")
    t.emit("nop")
    t.emit("nop")
    for ln in after if after is not None else [f"csrw {c('sctrctl')}, x0  // stop recording"]:
        t.emit(ln)
    t.emit("csrci sstatus, 2")
    t.outcome(SSI_CAUSE, lab, f"{desc}: SSI in S-mode", epc=False, origin="S")
    ssi_pend(t, False)
    ssi_enable(t, False)
    return lab


def u_interrupt(t: TestFile, desc: str) -> tuple[str, str]:
    """An SSI pending and enabled (sie.SSIE=1, SIE=0) is taken right after entering U-mode (S-level interrupts are
    always enabled in U-mode). Returns (window label, goto label)."""
    t.emit("csrci sstatus, 2  // SIE = 0")
    ssi_enable(t, True)
    ssi_pend(t, True)
    lab = t.label("ussi")
    t.allow(1)
    t.enter("U")
    t.emit(f"{lab}: nop")
    t.emit("nop")
    t.emit("nop")
    goto = t.label("goto")
    t.emit(f"{goto}:", 0)
    t.leave()
    t.outcome(SSI_CAUSE, lab, f"{desc}: SSI taken in U-mode", epc=False, origin="U")
    ssi_pend(t, False)
    ssi_enable(t, False)
    return lab, goto


# ---------------------------------------------------------------- cycle counting
CYC_NOTE = (
    "Cycle counting is optional: a record's CC is checked only when its CCV is 1. CC is decoded as CCM when "
    "CCE = 0, else (4096 + CCM) << (CCE-1), and compared with cycle-CSR reads around the two records: at most "
    "the cycles between reads before the first and after the second record, and at least the cycles between "
    "reads just after the first and just before the second, less the encoding's granularity (2^(CCE-1)), "
    "unless CC is saturated (all implemented CC bits 1, probed by writing all ones to ctrdata.CC). A frozen "
    "interval inside the gap is subtracted from both bounds (its inner and outer cycle brackets). The delay "
    "between the records is straight-line nops, since a loop's branches would themselves be recorded."
)


def cyc_setup(t: TestFile) -> None:
    t.comment("mcounteren.CY = 1 so S-mode can read cycle")
    t.tsbi_csr("SET", "MCOUNTEREN", imm=1)
    if "ctr_cyc" not in "".join(t.extra_data):
        t.extra_data.append(".p2align 3\nctr_cyc: .dword 0, 0, 0, 0, 0, 0, 0, 0, 0, 0")


def cyc_save(t: TestFile, slot: int) -> None:
    """ctr_cyc[slot] = cycle (uses x5)."""
    t.emit("csrr x5, cycle")
    t.emit("LA(x4, ctr_cyc)", 2)
    t.emit(f"SREG x5, {slot}*REGWIDTH(x4)")


def cc_probe(t: TestFile, out: str = "x9") -> None:
    """out = ctrdata.CC bits that hold 1 after writing CCV|CC all ones to logical entry 0 (sctrctl must be 0).
    Stored at ctr_cyc[6]. Uses x4, x5, x6."""
    t.emit("li x6, 0x200")
    t.emit(f"csrw {c('siselect')}, x6")
    t.li("x6", -0x8000)  # bits XLEN-1:15 set: CCV and CC (and WPRI, read-only 0)
    t.emit(f"csrw {c('sireg3')}, x6")
    t.emit(f"csrr {out}, {c('sireg3')}")
    t.emit(f"srli {out}, {out}, 16")
    t.emit("li x5, 0xffff")  # pseudo li for 16 bits
    t.emit(f"and {out}, {out}, x5")
    t.emit("LA(x4, ctr_cyc)", 2)
    t.emit(f"SREG {out}, 6*REGWIDTH(x4)")
    t.emit(f"csrw {c('sireg3')}, x0")


def delay(t: TestFile, n: int) -> None:
    t.emit(f".rept {n}", 0)
    t.emit("nop", 0)
    t.emit(".endr", n)


def cc_decode(t: TestFile, data: str, out: str) -> None:
    """out = decoded CC of the ctrdata value in data; x6 = granularity (1 when CCE = 0, else 2^(CCE-1)).
    Clobbers x4, x5, x7."""
    t.emit(f"srli x7, {data}, 16")
    t.emit("li x5, 0xffff")
    t.emit("and x7, x7, x5  // CC")
    t.emit("srli x5, x7, 12  // CCE")
    t.emit("slli x6, x5, 12")
    t.emit(f"sub {out}, x7, x6  // CCM")
    t.emit("li x7, 4096")
    t.emit(f"add x7, x7, {out}")
    t.emit("addi x6, x5, -1")
    t.emit("sll x7, x7, x6  // (4096 + CCM) << (CCE-1)")
    t.emit("li x4, 1")
    t.emit("sll x6, x4, x6  // 2^(CCE-1)")
    t.emit("seqz x5, x5")
    t.emit("neg x5, x5  // all ones when CCE = 0")
    t.emit(f"and {out}, {out}, x5")
    t.emit("and x4, x4, x5")
    t.emit("not x5, x5")
    t.emit("and x7, x7, x5")
    t.emit("and x6, x6, x5")
    t.emit(f"or {out}, {out}, x7  // decoded CC")
    t.emit("or x6, x6, x4  // granularity")


def cc_check(t: TestFile, desc: str, frozen_slots: tuple[int, int] | None = None, frozen_lower: bool = True) -> None:
    """Check logical entry 0's CC against ctr_cyc[0..3] = cycles before A, after A, before B, after B. With
    frozen_slots (f0, f1), the frozen interval's inner bracket ctr_cyc[f0..f1] is subtracted from the upper bound
    and its outer bracket ctr_cyc[7..8] from the lower bound. Vacuous when CCV = 0."""
    lab = t.label("cc")
    t.emit(f"{lab}:", 0)
    select(t, logical=0)
    t.emit(f"csrr x8, {c('sireg3')}")
    cc_decode(t, "x8", "x9")
    t.emit("LA(x4, ctr_cyc)", 2)
    t.emit("LREG x7, 3*REGWIDTH(x4)")
    t.emit("LREG x5, 0*REGWIDTH(x4)")
    t.emit("sub x7, x7, x5  // outer bracket")
    if frozen_slots:
        a, b = frozen_slots
        t.emit(f"LREG x5, {b}*REGWIDTH(x4)")
        t.emit("sub x7, x7, x5")
        t.emit(f"LREG x5, {a}*REGWIDTH(x4)")
        t.emit("add x7, x7, x5  // minus the frozen interval (inner bracket of it)")
    t.emit("sltu x7, x7, x9  // decoded > upper bound: bad")
    t.emit("xori x1, x7, 1  // x1 = upper bound holds")
    t.emit("LREG x7, 2*REGWIDTH(x4)")
    t.emit("LREG x5, 1*REGWIDTH(x4)")
    t.emit("sub x7, x7, x5  // inner bracket")
    if frozen_slots and frozen_lower:
        t.emit("LREG x5, 8*REGWIDTH(x4)")
        t.emit("sub x7, x7, x5")
        t.emit("LREG x5, 7*REGWIDTH(x4)")
        t.emit("add x7, x7, x5  // minus the frozen interval (its outer bracket)")
    t.emit("add x6, x9, x6  // decoded + granularity")
    t.emit("sltu x7, x6, x7  // decoded + granularity < inner: bad")
    t.emit("xori x7, x7, 1")
    t.emit("srli x5, x8, 16")
    t.emit("li x6, 0xffff")
    t.emit("and x5, x5, x6")
    t.emit("LREG x6, 6*REGWIDTH(x4)  // implemented CC bits")
    t.emit("xor x5, x5, x6")
    t.emit("seqz x5, x5  // saturated")
    t.emit("or x7, x7, x5")
    t.emit("and x1, x1, x7  // both bounds hold")
    t.emit("srli x5, x8, 15")
    t.emit("andi x5, x5, 1")
    t.emit("xori x5, x5, 1  // CCV = 0")
    t.emit("or x1, x1, x5")
    t.check_bool("x1", lab, f"{desc}: CCV = 0, or the decoded CC lies within the cycle-CSR brackets (or saturated)")


def cc_pair(t: TestFile, gap: int, frozen: int = 0) -> None:
    """anchor; record A; delay gap nops (optionally with a frozen interval of `frozen` nops); record B. Saves the
    brackets in ctr_cyc. Leaves CTR stopped."""
    anchor(t)
    wr(t, "sctrctl", S)
    cyc_save(t, 0)
    jal(t, "x0", "A")
    cyc_save(t, 1)
    delay(t, gap)
    if frozen:
        rd(t, "x6", "sctrstatus")
        t.li("x7", 1)
        t.emit("slli x7, x7, 31")
        t.emit("or x7, x7, x6")
        cyc_save(t, 7)
        t.emit(f"csrw {c('sctrstatus')}, x7  // FROZEN = 1")
        cyc_save(t, 4)
        delay(t, frozen)
        cyc_save(t, 5)
        t.emit(f"csrw {c('sctrstatus')}, x6  // FROZEN = 0")
        cyc_save(t, 8)
    cyc_save(t, 2)
    jal(t, "x0", "B")
    cyc_save(t, 3)
    off(t)
