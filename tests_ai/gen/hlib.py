# SPDX-License-Identifier: Apache-2.0
"""Shared helpers for the hypervisor (H) rule-derived tests (gen_H.py and h_*.py).

Tests boot to HS-mode. VS, VU and U are entered with sret (TestFile.enter) or a T-SBI GOTO, M-level
CSRs are reached through T-SBI, and traps are checked in the framework trap log. CSRs are named by
number in the assembly, so the tests assemble without the H extension in MARCH; hypervisor
instructions are emitted as .word encodings for the same reason, and because the encodings are also
the legal xtval values of an illegal- or virtual-instruction trap.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent))
from aigen import POOL_TRAP, TestFile, X

if TYPE_CHECKING:
    from collections.abc import Sequence

    from aigen import Expect, TestFileOptions, Value
    from typing_extensions import Unpack

SUITE = "H"
ISSUE = "https://github.com/riscv/riscv-isa-manual/issues/"
REQ = ["I", "S", "H"]
MARCH = "rv${XLEN}i_zicsr_zifencei"
HYP = "src/priv/hypervisor.adoc"
MUT = os.environ.get("AI_MUTANT", "")  # mutate.py: model a plausible bug in the expectations

ILLEGAL, VIRTUAL = 2, 22
BREAKPOINT, ECALL_U, ECALL_HS, ECALL_VS = 3, 8, 9, 10
INT = X(1 << 31, 1 << 63)  # interrupt bit of xcause


def icause(code: int) -> X:
    return X((1 << 31) | code, (1 << 63) | code)


# ---------------------------------------------------------------- CSRs
# name: (number, class, condition or None)
#   class H: hypervisor CSR; VS: VS CSR; S: supervisor CSR with a VS substitute; SN: supervisor CSR
#   without a VS substitute; M: machine CSR; U: unprivileged read-only CSR.
S1P12 = "defined(S1P12P0_OR_LATER_SUPPORTED)"
CSRS: dict[str, tuple[int, str, str | None]] = {
    "hstatus": (0x600, "H", None),
    "hedeleg": (0x602, "H", None),
    "hideleg": (0x603, "H", None),
    "hie": (0x604, "H", None),
    "htimedelta": (0x605, "H", None),
    "hcounteren": (0x606, "H", None),
    "hgeie": (0x607, "H", None),
    "henvcfg": (0x60A, "H", S1P12),
    "hedelegh": (0x612, "H", "__riscv_xlen == 32"),
    "htimedeltah": (0x615, "H", "__riscv_xlen == 32"),
    "henvcfgh": (0x61A, "H", f"__riscv_xlen == 32 && {S1P12}"),
    "htval": (0x643, "H", None),
    "hip": (0x644, "H", None),
    "hvip": (0x645, "H", None),
    "htinst": (0x64A, "H", None),
    "hgatp": (0x680, "H", None),
    "hgeip": (0xE12, "H", None),
    "vsstatus": (0x200, "VS", None),
    "vsie": (0x204, "VS", None),
    "vstvec": (0x205, "VS", None),
    "vsscratch": (0x240, "VS", None),
    "vsepc": (0x241, "VS", None),
    "vscause": (0x242, "VS", None),
    "vstval": (0x243, "VS", None),
    "vsip": (0x244, "VS", None),
    "vsatp": (0x280, "VS", None),
    "sstatus": (0x100, "S", None),
    "sie": (0x104, "S", None),
    "stvec": (0x105, "S", None),
    "scounteren": (0x106, "SN", None),
    "senvcfg": (0x10A, "SN", S1P12),
    "sscratch": (0x140, "S", None),
    "sepc": (0x141, "S", None),
    "scause": (0x142, "S", None),
    "stval": (0x143, "S", None),
    "sip": (0x144, "S", None),
    "satp": (0x180, "S", None),
    "mstatus": (0x300, "M", None),
    "misa": (0x301, "M", None),
    "medeleg": (0x302, "M", None),
    "mideleg": (0x303, "M", None),
    "mie": (0x304, "M", None),
    "mtvec": (0x305, "M", None),
    "mcounteren": (0x306, "M", None),
    "mscratch": (0x340, "M", None),
    "mepc": (0x341, "M", None),
    "mcause": (0x342, "M", None),
    "mtval": (0x343, "M", None),
    "mip": (0x344, "M", None),
    "mtinst": (0x34A, "M", None),
    "mtval2": (0x34B, "M", None),
    "mhartid": (0xF14, "M", None),
    "sstateen0": (0x10C, "SN", "defined(SSSTATEEN_SUPPORTED)"),
    "cycle": (0xC00, "U", None),
    "time": (0xC01, "U", None),
    "instret": (0xC02, "U", None),
}
READ_ONLY = {"hgeip", "mhartid"}  # writes are illegal in every mode (read-only CSR address or rule)
VS_OF = {
    "sstatus": "vsstatus",
    "sie": "vsie",
    "stvec": "vstvec",
    "sscratch": "vsscratch",
    "sepc": "vsepc",
    "scause": "vscause",
    "stval": "vstval",
    "sip": "vsip",
    "satp": "vsatp",
}


def csr_num(name: str) -> int:
    return CSRS[name][0]


def enc_csr(csr: int, f3: int, rd: int, rs1: int) -> int:
    return (csr << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | 0x73


# CSR instruction forms: (asm template, funct3, rd, rs1-or-uimm, kind, writes). rd x7, rs x6, uimm 0x15 or 0.
if TYPE_CHECKING:
    Form = tuple[str, int, int, int, str, bool]
FORMS: list[Form] = [
    ("csrrs x7, {c}, x0", 2, 7, 0, "read (csrrs rs1=x0)", False),
    ("csrrw x0, {c}, x6", 1, 0, 6, "write (csrrw rd=x0)", True),
    ("csrrw x7, {c}, x6", 1, 7, 6, "swap (csrrw)", True),
    ("csrrs x7, {c}, x6", 2, 7, 6, "set (csrrs rs1!=x0)", True),
    ("csrrc x7, {c}, x6", 3, 7, 6, "clear (csrrc rs1!=x0)", True),
    ("csrrwi x7, {c}, 0x15", 5, 7, 0x15, "write immediate (csrrwi)", True),
    ("csrrsi x7, {c}, 0", 6, 7, 0, "read (csrrsi uimm=0)", False),
    ("csrrci x7, {c}, 0x15", 7, 7, 0x15, "clear immediate (csrrci uimm!=0)", True),
]
READS = [f for f in FORMS if not f[5]]
WRITES = [f for f in FORMS if f[5]]


def form_value(form: Form, old: int, rs: int, width: int) -> tuple[int | None, int]:
    """(rd, new) for a CSR form on a register of `width` bits holding old, with rs in x6."""
    _, f3, rd, rs1, _, _ = form
    m = (1 << width) - 1
    src = (rs if rs1 == 6 else 0) if f3 in (1, 2, 3) else rs1
    new = {1: src, 5: src, 2: old | src, 6: old | src, 3: old & ~src, 7: old & ~src}[f3] & m
    return (old if rd else None), new


CAUSE = {"ok": "ok", "illegal": ILLEGAL, "virtual": VIRTUAL}


def csr_window(t: TestFile, mode: str, name: str, form: Form, expect: str, desc: str) -> str:
    """Execute one CSR instruction on CSR `name` in `mode` (S for HS, U, VS, VU) in a trap window and check
    the outcome: ok, illegal (2) or virtual (22). A trap must leave xtval = 0 or the instruction bits.
    x6 must hold the source value for register forms. Returns the label of the instruction."""
    asm, f3, rd, rs1, kind, _ = form
    num = csr_num(name)
    cause = CAUSE[expect]
    tval: list[Value] | None = None if expect == "ok" else [0, enc_csr(num, f3, rd, rs1)]
    return t.window(mode, [asm.format(c=hex(num)) + f"  // {name}"], cause, f"{kind} of {name} ({desc})", tval)


def access_expect(name: str, mode: str, write: bool) -> str:
    """Expected outcome of accessing CSR `name` from `mode` with all enables set and mstatus.TVM=0
    (hypervisor.adoc, virtual-instruction rules; Zicsr read-only rule)."""
    cls = CSRS[name][1]
    if write and name in READ_ONLY:
        return "illegal"  # not allowed in HS-mode either, so not HS-qualified
    if cls in ("H", "VS"):
        return {"S": "ok", "U": "illegal", "VS": "virtual", "VU": "virtual"}[mode]
    if cls == "S" or cls == "SN":
        return {"S": "ok", "U": "illegal", "VS": "ok", "VU": "virtual"}[mode]
    if cls == "M":
        return "illegal"
    raise ValueError(name)


# ---------------------------------------------------------------- instructions
SRET, MRET, WFI = 0x10200073, 0x30200073, 0x10500073


def sfence_vma(rs1: int = 0, rs2: int = 0) -> int:
    return 0x12000073 | (rs2 << 20) | (rs1 << 15)


def sinval_vma(rs1: int = 0, rs2: int = 0) -> int:
    return 0x16000073 | (rs2 << 20) | (rs1 << 15)


def hfence_vvma(rs1: int = 0, rs2: int = 0) -> int:
    return 0x22000073 | (rs2 << 20) | (rs1 << 15)


def hfence_gvma(rs1: int = 0, rs2: int = 0) -> int:
    return 0x62000073 | (rs2 << 20) | (rs1 << 15)


def hinval_vvma(rs1: int = 0, rs2: int = 0) -> int:
    return 0x26000073 | (rs2 << 20) | (rs1 << 15)


def hinval_gvma(rs1: int = 0, rs2: int = 0) -> int:
    return 0x66000073 | (rs2 << 20) | (rs1 << 15)


# HLV/HLVX/HSV: name -> (funct7, rs2 field or None for stores, bytes, signed, xlen64 only)
HLSV = {
    "hlv.b": (0x30, 0, 1, True, False),
    "hlv.bu": (0x30, 1, 1, False, False),
    "hlv.h": (0x32, 0, 2, True, False),
    "hlv.hu": (0x32, 1, 2, False, False),
    "hlvx.hu": (0x32, 3, 2, False, False),
    "hlv.w": (0x34, 0, 4, True, False),
    "hlvx.wu": (0x34, 3, 4, False, False),
    "hlv.wu": (0x34, 1, 4, False, True),
    "hlv.d": (0x36, 0, 8, True, True),
    "hsv.b": (0x31, None, 1, False, False),
    "hsv.h": (0x33, None, 2, False, False),
    "hsv.w": (0x35, None, 4, False, False),
    "hsv.d": (0x37, None, 8, False, True),
}
RN = {f"x{i}": i for i in range(32)} | {"a0": 10, "a1": 11, "a2": 12}


def hlsv(name: str, rd: str, rs1: str, rs2: str = "x0") -> tuple[str, int]:
    """(.word line, encoding) of a hypervisor load (rd <- [rs1]) or store ([rs1] <- rs2)."""
    f7, sub, _, _, _ = HLSV[name]
    if sub is None:
        e = (f7 << 25) | (RN[rs2] << 20) | (RN[rs1] << 15) | (4 << 12) | 0x73
        return f".word {hex(e)}  // {name} {rs2}, ({rs1})", e
    e = (f7 << 25) | (sub << 20) | (RN[rs1] << 15) | (4 << 12) | (RN[rd] << 7) | 0x73
    return f".word {hex(e)}  // {name} {rd}, ({rs1})", e


def word(e: int, note: str) -> str:
    return f".word {hex(e)}  // {note}"


def insn_window(t: TestFile, mode: str, e: int, note: str, expect: Expect, desc: str, more: Sequence[str] = ()) -> str:
    """Execute one instruction (encoding e) in `mode` in a trap window. Illegal and virtual traps must leave
    xtval = 0 or the instruction bits."""
    alts = expect if isinstance(expect, list) else [expect]
    tval = [0, e] if any(a in (ILLEGAL, VIRTUAL) for a in alts) else None
    return t.window(mode, [word(e, note), *more], expect, f"{note} ({desc})", tval)


# ---------------------------------------------------------------- state helpers
def new(rule: str, required: list[str] = REQ, **kw: Unpack[TestFileOptions]) -> TestFile:
    kw.setdefault("boot", "S")
    kw.setdefault("pool", POOL_TRAP)
    kw.setdefault("march", MARCH)
    return TestFile(SUITE, rule, required=required, **kw)


def hs_bits(t: TestFile, name: str, bits: int, on: bool, note: str = "") -> None:
    """HS-mode csrs/csrc of `bits` (a 32-bit signed-safe value) in CSR `name`."""
    t.comment(note or f"{name} {'|=' if on else '&= ~'}{hex(bits)}")
    t.li("x7", bits)
    t.emit(f"{'csrs' if on else 'csrc'} {hex(csr_num(name))}, x7  // {name}")


def hs_write(t: TestFile, name: str, value: Value, note: str = "") -> None:
    t.load("x7", value, note or f"{name} value")
    t.emit(f"csrw {hex(csr_num(name))}, x7  // {name}")


def hs_read(t: TestFile, reg: str, name: str) -> None:
    t.emit(f"csrr {reg}, {hex(csr_num(name))}  // {name}")


def m_bits(t: TestFile, name: str, bits: int, on: bool, note: str = "") -> None:
    """M-mode (T-SBI) set or clear of `bits` in M-level CSR `name`."""
    t.comment(note or f"M-mode: {name} {'|=' if on else '&= ~'}{hex(bits)}")
    t.tsbi_csr("SET" if on else "CLEAR", name.upper(), imm=bits)


def m_read(t: TestFile, name: str) -> None:
    """a0 = M-level CSR `name` (T-SBI)."""
    t.tsbi_csr("READ", name.upper())


MSTATUS_TVM, MSTATUS_TW, MSTATUS_TSR = 1 << 20, 1 << 21, 1 << 22
HSTATUS = {
    "VSBE": 1 << 5,
    "GVA": 1 << 6,
    "SPV": 1 << 7,
    "SPVP": 1 << 8,
    "HU": 1 << 9,
    "VTVM": 1 << 20,
    "VTW": 1 << 21,
    "VTSR": 1 << 22,
}


def enter_tsbi(t: TestFile, mode: str) -> None:
    """Enter VS or VU from HS (or M) through a T-SBI GOTO, which needs no sret (for mstatus.TSR=1)."""
    t.emit(f"RVTEST_TSBI_GOTO_{mode}MODE", 120)


def window_tsbi(t: TestFile, mode: str, lines: list[str], expect: Expect, desc: str, tval: Expect | None = None) -> str:
    """Like TestFile.window, but enters `mode` with a T-SBI GOTO instead of sret."""
    lab = t.label(f"in_{mode}")
    t.allow(1)
    enter_tsbi(t, mode)
    t.emit(f"{lab}:", 0)
    for ln in lines:
        t.emit(ln)
    t.leave()
    t.outcome(expect, lab, f"{desc} in {mode}-mode", tval, origin=mode)
    return lab


def delay(t: TestFile, n: int = 50) -> None:
    loop = t.label("delay")
    t.li("x9", n)
    t.emit(f"{loop}:", 0)
    t.emit("addi x9, x9, -1", n)
    t.emit(f"bnez x9, {loop}", n)
