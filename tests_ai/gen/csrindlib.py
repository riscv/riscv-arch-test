# SPDX-License-Identifier: Apache-2.0
"""Shared helpers for the Smcsrind and Sscsrind rule-derived tests (gen_Smcsrind.py).

CSRs are named by number (CSR_* macros from encoding.h), so the tests assemble with MARCH rv${XLEN}i_zicsr and the
encodings are also the legal xtval values of an illegal- or virtual-instruction trap. Accesses that may trap run in
trap windows (aigen.TestFile.window); M-level CSRs that T-SBI lacks are reached only from M-boot (_Sm, or Smcsrind)
files.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent))
from aigen import TestFile, X

if TYPE_CHECKING:
    from aigen import Expect, Value

ISSUE = "https://github.com/riscv/riscv-isa-manual/issues/"
CSRIND = "src/priv/smcsrind.adoc"
STATEEN = "src/priv/smstateen.adoc"
MARCH = "rv${XLEN}i_zicsr_zifencei"
MUT = os.environ.get("AI_MUTANT", "")

ILLEGAL, VIRTUAL = 2, 22
H = "defined(H_SUPPORTED)"
SMAIA = "defined(SMAIA_SUPPORTED)"
SSAIA = "defined(SSAIA_SUPPORTED)"
SSCTR = "defined(SSCTR_SUPPORTED)"
SMSTATEEN = "defined(SMSTATEEN_SUPPORTED)"

# name -> (number, encoding.h macro)
CSRS: dict[str, int] = {
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
    "miselect": 0x350,
    "mireg": 0x351,
    "mireg2": 0x352,
    "mireg3": 0x353,
    "mireg4": 0x355,
    "mireg5": 0x356,
    "mireg6": 0x357,
}
SIREGS = ["sireg", "sireg2", "sireg3", "sireg4", "sireg5", "sireg6"]
VSIREGS = ["v" + r for r in SIREGS]
MIREGS = ["m" + r[1:] for r in SIREGS]
S_SET = ["siselect", *SIREGS]
VS_SET = ["vsiselect", *VSIREGS]
M_SET = ["miselect", *MIREGS]


def macro(csr: str) -> str:
    return f"CSR_{csr.upper()}"


# Select values reserved for standard use and allocated to no extension: AIA has 0x30-0x3F and 0x70-0xFF,
# Smcdeleg 0x40-0x5F, Smctr 0x200-0x2FF.
RESERVED_SEL = [0x000, 0x001, 0x02F, 0x060, 0x06F, 0x100, 0x1FF, 0x300, 0xFFF]
# A spread of vsiselect values covering reserved and every allocated range, for "regardless of vsiselect" sweeps.
SWEEP_SEL = [0x000, 0x030, 0x040, 0x070, 0x200, 0xFFF]


def msb(xlen: int) -> int:
    return 1 << (xlen - 1)


MSB = X(1 << 31, 1 << 63)

# CSR instruction forms: (asm template, funct3, rd, rs1-or-uimm, kind). rd x7, rs x6, uimm 0x15.
Form = tuple[str, int, int, int, str]
FORMS: list[Form] = [
    ("csrrs x7, {c}, x0", 2, 7, 0, "read (csrrs rs1=x0)"),
    ("csrrw x0, {c}, x6", 1, 0, 6, "write (csrrw rd=x0)"),
    ("csrrw x7, {c}, x6", 1, 7, 6, "swap (csrrw)"),
    ("csrrs x7, {c}, x6", 2, 7, 6, "set (csrrs)"),
    ("csrrc x7, {c}, x6", 3, 7, 6, "clear (csrrc)"),
    ("csrrwi x7, {c}, 0x15", 5, 7, 0x15, "write immediate (csrrwi)"),
    ("csrrsi x7, {c}, 0", 6, 7, 0, "read (csrrsi uimm=0)"),
    ("csrrci x7, {c}, 0x15", 7, 7, 0x15, "clear immediate (csrrci)"),
]
RW_FORMS = [FORMS[0], FORMS[1]]  # one read and one write
# Forms that do not write the CSR (rs1=x0 or uimm=0)
READ_FORMS: list[Form] = [
    ("csrrs x7, {c}, x0", 2, 7, 0, "csrrs rs1=x0"),
    ("csrrc x7, {c}, x0", 3, 7, 0, "csrrc rs1=x0"),
    ("csrrsi x7, {c}, 0", 6, 7, 0, "csrrsi uimm=0"),
    ("csrrci x7, {c}, 0", 7, 7, 0, "csrrci uimm=0"),
]


def enc(csr: int, f3: int, rd: int, rs1: int) -> int:
    return (csr << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | 0x73


def form_value(form: Form, old: int, rs: int, width: int) -> tuple[int | None, int]:
    """(rd, new) for a CSR form on a register of `width` bits holding old, with rs in x6."""
    _, f3, rd, rs1, _ = form
    m = (1 << width) - 1
    src = (rs if rs1 == 6 else 0) if f3 in (1, 2, 3) else rs1
    new = {1: src, 5: src, 2: old | src, 6: old | src, 3: old & ~src, 7: old & ~src}[f3] & m
    return (old if rd else None), new


def access(t: TestFile, mode: str, csr: str, form: Form, expect: Expect, desc: str) -> str:
    """One CSR instruction on csr in `mode` inside a trap window. expect: "ok", a cause, or a list of legal
    outcomes. Faulting instructions accept xtval = 0 or the instruction bits."""
    asm, f3, rd, rs1, kind = form
    alts = expect if isinstance(expect, list) else [expect]
    tval: list[Value] | None = None if alts == ["ok"] else [0, enc(CSRS[csr], f3, rd, rs1)]
    return t.window(mode, [asm.format(c=macro(csr))], expect, f"{kind} of {csr} ({desc})", tval)


def sweep(t: TestFile, mode: str, csrs: list[str], forms: list[Form], expect: Expect, desc: str) -> None:
    for c in csrs:
        for f in forms:
            if f[3] == 6 and f[1] in (1, 2, 3):
                t.load("x6", t.rand_x(), "rs1 value")
            access(t, mode, c, f, expect, desc)


def eq_check(t: TestFile, a: str, b: str, lab: str, desc: str, tmp: str = "x8") -> None:
    """Check registers a and b are equal (a dynamic expectation): tmp = (a == b)."""
    t.emit(f"xor {tmp}, {a}, {b}")
    t.emit(f"seqz {tmp}, {tmp}")
    t.check_bool(tmp, lab, desc)


def ne_check(t: TestFile, a: str, b: str, lab: str, desc: str, tmp: str = "x8") -> None:
    t.emit(f"xor {tmp}, {a}, {b}")
    t.emit(f"snez {tmp}, {tmp}")
    t.check_bool(tmp, lab, desc)


# ---------------------------------------------------------------- stateen bit 60 (CSRIND)
def m_csrind(t: TestFile, on: bool) -> None:
    """M-mode (T-SBI) set or clear mstateen0.CSRIND (bit 60; mstateen0h bit 28 on RV32)."""
    op = "SET" if on else "CLEAR"
    t.comment(f"mstateen0.CSRIND = {int(on)} (T-SBI)")
    with t.rv64_only():
        t.li("a1", 1)
        t.emit("slli a1, a1, 60")
        t.tsbi_csr(op, "MSTATEEN0", "a1")
    with t.rv32_only():
        t.li("a1", 1 << 28)
        t.tsbi_csr(op, "MSTATEEN0H", "a1")


def m_csrind_direct(t: TestFile, on: bool, reg: str = "x6") -> None:
    """M-mode csrs/csrc of mstateen0.CSRIND (in an M-boot test)."""
    op = "csrs" if on else "csrc"
    t.comment(f"mstateen0.CSRIND = {int(on)}")
    with t.rv64_only():
        t.li(reg, 1)
        t.emit(f"slli {reg}, {reg}, 60")
        t.emit(f"{op} {macro('mstateen0')}, {reg}")
    with t.rv32_only():
        t.li(reg, 1 << 28)
        t.emit(f"{op} {macro('mstateen0h')}, {reg}")


def m_read_csrind(t: TestFile, reg: str) -> None:
    """reg = mstateen0.CSRIND (T-SBI read)."""
    with t.rv64_only():
        t.tsbi_csr("READ", "MSTATEEN0")
        t.emit(f"srli {reg}, a0, 60")
    with t.rv32_only():
        t.tsbi_csr("READ", "MSTATEEN0H")
        t.emit(f"srli {reg}, a0, 28")
    t.emit(f"andi {reg}, {reg}, 1")


def h_csrind(t: TestFile, on: bool, reg: str = "x6") -> None:
    """HS-mode csrs/csrc of hstateen0.CSRIND (bit 60; hstateen0h bit 28 on RV32)."""
    op = "csrs" if on else "csrc"
    t.comment(f"hstateen0.CSRIND = {int(on)}")
    with t.rv64_only():
        t.li(reg, 1)
        t.emit(f"slli {reg}, {reg}, 60")
        t.emit(f"{op} CSR_HSTATEEN0, {reg}")
    with t.rv32_only():
        t.li(reg, 1 << 28)
        t.emit(f"{op} CSR_HSTATEEN0H, {reg}")


def h_read_csrind(t: TestFile, reg: str) -> None:
    with t.rv64_only():
        t.emit(f"csrr {reg}, CSR_HSTATEEN0")
        t.emit(f"srli {reg}, {reg}, 60")
    with t.rv32_only():
        t.emit(f"csrr {reg}, CSR_HSTATEEN0H")
        t.emit(f"srli {reg}, {reg}, 28")
    t.emit(f"andi {reg}, {reg}, 1")


def h_probe(t: TestFile, reg: str) -> None:
    """HS-mode: set, then clear hstateen0.CSRIND; reg = 1 when it read 1 and then 0 (writable both ways). The bit
    is left clear. Uses x6."""
    h_csrind(t, True)
    h_read_csrind(t, reg)
    h_csrind(t, False)
    h_read_csrind(t, "x6")
    t.emit("xori x6, x6, 1")
    t.emit(f"and {reg}, {reg}, x6")


def set_sel(t: TestFile, csr: str, value: int | X, reg: str = "x6") -> None:
    """Write a select CSR from the current mode."""
    if isinstance(value, int) and -2048 <= value < 2048:
        t.emit(f"li {reg}, {value}")
    else:
        t.load(reg, value, f"{csr} value")
    t.emit(f"csrw {macro(csr)}, {reg}")
