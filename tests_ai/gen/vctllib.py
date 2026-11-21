# SPDX-License-Identifier: Apache-2.0
"""Helpers for the vector control rule-derived tests (gen_Vctl.py, tests in tests_ai/V).

Implementation parameters (VLEN, ELEN, supported SEW/LMUL) are never assumed: VLEN comes from vlenb at run time,
VLMAX values are computed from it in the test, and ELEN >= 64 is taken from the Zve64x extension macro (ELEN 32
otherwise). Tests store vector registers with whole-register stores (vs1r.v, which do not depend on vtype) into a
scratch buffer and check elements with scalar loads.

Trap windows: vwin() permits one trap around a vector or CSR instruction and, for an illegal-instruction trap,
accepts xtval = 0 or the instruction's own bits (read from memory at run time, so no encoder is needed).

Register use: x6-x9 and x1 are operands; x13-x15 hold trap-window results; x10-x12 are T-SBI arguments.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent))
from aigen import NO_TRAP, ORIGIN, POOL_TRAP, TestFile, X

if TYPE_CHECKING:
    from collections.abc import Callable

    from aigen import Expect

VC = "src/unpriv/vector-common.adoc"
VST = "src/unpriv/v-st-ext.adoc"
ZVE32X = "src/unpriv/zve32x.adoc"
MAC = "src/priv/machine.adoc"
ISSUE = "https://github.com/riscv/riscv-isa-manual/issues/"

MARCH = "rv${XLEN}i_zicsr_zifencei_zve32x"
MARCH_D = "rv${XLEN}ifd_zicsr_zifencei_zve64d"
MARCH_V = "rv${XLEN}i_zicsr_zifencei_zve64x"
REQ = ["I", "Zve32x"]
E64 = "defined(ZVE64X_SUPPORTED)"  # ELEN >= 64 (SEW=64 supported)
ILLEGAL = 2
LOAD_PF, STORE_PF = 13, 15

CSR = {"vstart": 0x008, "vxsat": 0x009, "vxrm": 0x00A, "vcsr": 0x00F, "vl": 0xC20, "vtype": 0xC21, "vlenb": 0xC22}
VILL = X(1 << 31, 1 << 63)
SEW_CODE = {8: 0, 16: 1, 32: 2, 64: 3}
LMUL_CODE = {"m1": 0, "m2": 1, "m4": 2, "m8": 3, "mf8": 5, "mf4": 6, "mf2": 7}
# LMUL as a power of two
LMUL_LOG = {"m1": 0, "m2": 1, "m4": 2, "m8": 3, "mf8": -3, "mf4": -2, "mf2": -1}
SEW_LOG = {8: 3, 16: 4, 32: 5, 64: 6}
VS_MASK = 3 << 9
VS_OFF, VS_INIT, VS_CLEAN, VS_DIRTY = 0, 1 << 9, 2 << 9, 3 << 9
SD = X(1 << 31, 1 << 63)
BUF = "vctl_buf"  # scratch buffer for whole-register stores (one register of up to VLEN = 2^16 bits)
BUF2 = "vctl_buf2"


def vtypei(sew: int, lmul: str = "m1", ta: int = 0, ma: int = 0) -> int:
    return LMUL_CODE[lmul] | (SEW_CODE[sew] << 3) | (ta << 6) | (ma << 7)


def vt(sew: int, lmul: str = "m1", ta: int = 0, ma: int = 0) -> str:
    """Assembler vtype operand."""
    return f"e{sew}, {lmul}, {'ta' if ta else 'tu'}, {'ma' if ma else 'mu'}"


class VTest(TestFile):
    """A TestFile with the scratch buffers in its data section."""

    def __init__(self, suite: str, rule: str, **kw: object) -> None:
        kw.setdefault("march", MARCH)
        kw.setdefault("pool", POOL_TRAP)
        req = kw.pop("required", REQ)
        super().__init__(suite, rule, required=req, **kw)  # type: ignore[arg-type]
        self.bufs = True

    def render(self) -> str:
        if self.bufs:
            self.extra_data = [
                "  // scratch buffers for whole-register stores (vctllib.py)",
                "  .p2align 6",
                f"{BUF}:",
                "  .fill 8192, 1, 0",
                f"{BUF2}:",
                "  .fill 8192, 1, 0",
                *self.extra_data,
            ]
        return super().render()


# ---------------------------------------------------------------- run-time quantities
def vlmax(t: TestFile, reg: str, sew: int, lmul: str) -> None:
    """reg = LMUL*VLEN/SEW computed from vlenb (no vsetvli)."""
    t.emit(f"csrr {reg}, vlenb")
    s = 3 + LMUL_LOG[lmul] - SEW_LOG[sew]  # vlenb * 8 * LMUL / SEW
    if s > 0:
        t.emit(f"slli {reg}, {reg}, {s}")
    elif s < 0:
        t.emit(f"srli {reg}, {reg}, {-s}")


def vset(t: TestFile, rd: str, avl: str | int, sew: int, lmul: str = "m1", ta: int = 0, ma: int = 0) -> None:
    """vsetvli rd, avl (a register) or vsetivli rd, avl (an int)."""
    if isinstance(avl, int):
        t.emit(f"vsetivli {rd}, {avl}, {vt(sew, lmul, ta, ma)}")
    else:
        t.emit(f"vsetvli {rd}, {avl}, {vt(sew, lmul, ta, ma)}")


def vset_max(t: TestFile, sew: int, lmul: str = "m1", ta: int = 0, ma: int = 0, rd: str = "x5") -> None:
    t.emit(f"vsetvli {rd}, x0, {vt(sew, lmul, ta, ma)}")


def fill(t: TestFile, vreg: str, byte: int, reg: str = "x6") -> None:
    """Every byte of vreg = byte (e8, m1, VLMAX; leaves vtype = e8 m1 tu mu, vl = VLMAX)."""
    vset_max(t, 8, "m1")
    t.li(reg, byte)
    t.emit(f"vmv.v.x {vreg}, {reg}")


def iota(t: TestFile, vreg: str, sew: int, lmul: str = "m1", add: int = 0, reg: str = "x6") -> None:
    """Element i of the group at vreg = i + add, with SEW/LMUL at VLMAX (leaves that vtype, tu mu)."""
    vset_max(t, sew, lmul)
    t.emit(f"vid.v {vreg}")
    if add:
        t.li(reg, add)
        t.emit(f"vadd.vx {vreg}, {vreg}, {reg}")


def store(t: TestFile, vreg: str, buf: str = BUF, areg: str = "x6") -> None:
    """Whole-register store of vreg to buf (independent of vtype)."""
    t.la(areg, buf)
    t.emit(f"vs1r.v {vreg}, ({areg})")


LD = {8: "lbu", 16: "lhu"}


def ld_elem(t: TestFile, dst: str, sew: int, off: int | str, buf: str = BUF, areg: str = "x6") -> None:
    """dst = element at byte offset off (an int, or a register holding it) of buf, zero-extended (SEW <= 32;
    on RV32, SEW=32 is the full register)."""
    t.la(areg, buf)
    if isinstance(off, str):
        t.emit(f"add {areg}, {areg}, {off}")
        off = 0
    if sew in LD:
        t.emit(f"{LD[sew]} {dst}, {off}({areg})")
    elif sew == 32:
        t.emit("#if __riscv_xlen == 64", 0)
        t.emit(f"lwu {dst}, {off}({areg})")
        t.emit("#else", 0)
        t.emit(f"lw {dst}, {off}({areg})")
        t.emit("#endif", 0)
    else:
        raise ValueError(sew)


def ones(sew: int) -> int:
    return (1 << sew) - 1


def check_agn(t: TestFile, reg: str, old: int | str, sew: int, lab: str, desc: str, tmp: str = "x9") -> None:
    """reg (an element zero-extended to XLEN) is old (an int, or a register) or all ones at SEW (agnostic)."""
    if isinstance(old, int):
        t.check(reg, [old, ones(sew)] if old != ones(sew) else old, lab, desc + " (agnostic: old value or all 1s)")
        return
    t.emit(f"xor {tmp}, {reg}, {old}")
    t.emit(f"seqz {tmp}, {tmp}")
    t.load("x5", ones(sew), "all ones at SEW")
    t.emit(f"xor x5, x5, {reg}")
    t.emit("seqz x5, x5")
    t.emit(f"or {tmp}, {tmp}, x5")
    t.check_bool(tmp, lab, desc + " (agnostic: old value or all 1s)")


# ---------------------------------------------------------------- trap windows
def tval_insn_check(t: TestFile, lab: str, desc: str) -> None:
    """After a trap: xtval is 0 or the bits of the instruction at lab (illegal instruction). Clobbers x13-x15."""
    t.emit("AI_LOG(x15, TRAPLOG_TVAL)", 10)
    t.la("x14", lab)
    t.emit("#if __riscv_xlen == 64", 0)
    t.emit("lwu x14, 0(x14)")
    t.emit("#else", 0)
    t.emit("lw x14, 0(x14)")
    t.emit("#endif", 0)
    t.emit("xor x14, x14, x15")
    t.emit("seqz x14, x14  // xtval == instruction bits")
    t.emit("seqz x15, x15  // xtval == 0")
    t.emit("or x15, x15, x14")
    t.check_bool("x15", lab, f"{desc}: xtval is 0 or the instruction bits")


def vwin(
    t: TestFile,
    lines: list[str],
    expect: Expect,
    desc: str,
    mode: str | None = None,
    tval: Expect | None = None,
    flag: str | None = None,
) -> str:
    """Trap window around lines (the first is the instruction under test) in `mode` (default: the current mode;
    in an unprivileged test that is the lowest mode, so the origin is not checked). For an illegal-instruction
    trap, xtval must be 0 or the instruction bits. flag: a register set to 1 if a trap was taken, else 0."""
    lab = t.label("w")
    t.allow(1)
    enter = mode is not None and mode != t.cur
    if enter and mode is not None:
        t.enter(mode)
    t.emit(f"{lab}:", 0)
    for ln in lines:
        t.emit(ln)
    if enter:
        t.leave()
    alts = expect if isinstance(expect, list) else [expect]
    causes = [a for a in alts if a != "ok"]
    origin = (mode or t.cur) if t.boot else None
    t.outcome(expect, lab, f"{desc}" + (f" in {mode}-mode" if mode else ""), tval, origin=None)
    # x13 = number of traps (0 or 1), x14 = cause or -1
    if flag:
        t.emit(f"mv {flag}, x13  // 1: trapped")
    if not causes:
        return lab
    if ILLEGAL in causes and tval is None:
        if len(causes) > 1:
            t.emit("addi x15, x14, -2")
            t.emit("seqz x15, x15")
            t.either("x15", lambda: tval_insn_check(t, lab, desc), lambda: None)
        elif "ok" in alts:
            t.either("x13", lambda: tval_insn_check(t, lab, desc), lambda: None)
        else:
            tval_insn_check(t, lab, desc)
    if origin:

        def chk() -> None:
            t.emit("AI_ORIGIN", 25)
            t.check("x15", ORIGIN[origin], lab, f"{desc}: xPP/xPV record the mode the trap came from")

        if "ok" in alts:
            t.either("x13", chk, lambda: None)
        else:
            chk()
    return lab


def csr_forms(csr: str) -> list[tuple[str, int, str, bool]]:
    """(asm, csr, description, writes) for the eight CSR instruction forms; x6 holds the register source."""
    c = hex(CSR[csr])
    return [
        (f"csrrs x7, {c}, x0", CSR[csr], "csrrs rs1=x0 (read)", False),
        (f"csrrw x0, {c}, x6", CSR[csr], "csrrw rd=x0 (write)", True),
        (f"csrrw x7, {c}, x6", CSR[csr], "csrrw (swap)", True),
        (f"csrrs x7, {c}, x6", CSR[csr], "csrrs rs1!=x0 (set)", True),
        (f"csrrc x7, {c}, x6", CSR[csr], "csrrc rs1!=x0 (clear)", True),
        (f"csrrwi x7, {c}, 1", CSR[csr], "csrrwi (write immediate 1)", True),
        (f"csrrsi x7, {c}, 0", CSR[csr], "csrrsi uimm=0 (read)", False),
        (f"csrrci x7, {c}, 1", CSR[csr], "csrrci uimm!=0 (clear immediate 1)", True),
    ]


# ---------------------------------------------------------------- privileged helpers (S-boot tests)
def set_vs(t: TestFile, vs: int, reg: str = "x6") -> None:
    """sstatus.VS = vs (S-mode)."""
    t.li(reg, VS_MASK)
    t.emit(f"csrc sstatus, {reg}")
    if vs:
        t.li(reg, vs)
        t.emit(f"csrs sstatus, {reg}")


def set_mvs(t: TestFile, vs: int, reg: str = "x6") -> None:
    """mstatus.VS = vs (M-mode)."""
    t.li(reg, VS_MASK)
    t.emit(f"csrc mstatus, {reg}")
    if vs:
        t.li(reg, vs)
        t.emit(f"csrs mstatus, {reg}")


def read_vs(t: TestFile, reg: str, csr: str = "sstatus") -> None:
    t.emit(f"csrr {reg}, {csr}")
    t.emit(f"srli {reg}, {reg}, 9")
    t.emit(f"andi {reg}, {reg}, 3")


def both_xlen(t: TestFile, body: Callable[[int], object]) -> None:
    with t.rv64_only():
        body(64)
    with t.rv32_only():
        body(32)


__all__ = ["NO_TRAP"]
