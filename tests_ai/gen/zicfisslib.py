# SPDX-License-Identifier: Apache-2.0
"""Helpers for the Zicfiss rule-derived tests (gen_Zicfiss.py).

Encodings of the shadow-stack instructions (emitted as .word/.hword so the tests assemble without Zicfiss in
MARCH, and because the encodings are the legal xtval of an illegal- or virtual-instruction trap), the SSE enables,
and S-mode paging (hmem.PT) with an optional user alias of the code region.

Paging layout (S-level single-stage, satp = Sv39 on RV64, Sv32 on RV32):
  - the test image is identity mapped by two root-level superpages without U (S-mode code, data, handlers);
  - for U-mode code, the code region is mapped a second time at ALIAS with U=1 and registered in the S save area,
    so RVTEST_TSBI_GOTO_UMODE/GOTO_SMODE resume in the mapping the new mode can fetch from (TSBI_RELOCATE_EPC);
  - test page i is at VA0 + i*4 KiB, mapped to its own 4 KiB data page with the requested permissions.
The satp MODE is probed at run time (vm_either); a hart without it skips the paged part.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aigen import X
from hmem import PT, XP, A, D, MemTest, R, U, V, W, both

if TYPE_CHECKING:
    from collections.abc import Callable

    from aigen import Expect, TestFile, Value

ILLEGAL, VIRTUAL, SWCHECK = 2, 22, 18
INSN_AF, LOAD_AF, STORE_AF = 1, 5, 7
INSN_PF, LOAD_PF, STORE_PF = 12, 13, 15
LOAD_MIS, STORE_MIS = 4, 6
STORE_GPF = 23
SS_FAULT = 3  # xtval of a shadow-stack software-check exception

H = "defined(H_SUPPORTED)"
ZC = "defined(ZCMOP_SUPPORTED)"
SSE = 0x8  # menvcfg/senvcfg/henvcfg bit 3
MENVCFG, SENVCFG, HENVCFG, SSP = 0x30A, 0x10A, 0x60A, 0x011
SATP, VSATP, HGATP = 0x180, 0x280, 0x680
SUM, MXR = 1 << 18, 1 << 19

XB = X(4, 8)  # XLEN/8
VA0 = {32: 0x2000_0000, 64: 0x4000_0000}
ALIAS = {32: 0x6000_0000, 64: 0x1_0000_0000}
SPSHIFT = {32: 22, 64: 30}
SCHEME = {32: "sv32", 64: "sv39"}

# PTE permissions
SS = V | W | A | D  # xwr = 010: shadow-stack page
RO = V | R | A | D
RW = V | R | W | A | D
RX = V | R | XP | A | D
XO = V | XP | A | D
RWX = V | R | W | XP | A | D
INVALID = 0


# ---------------------------------------------------------------- encodings
RN = {f"x{i}": i for i in range(32)} | {"a0": 10, "a1": 11, "a2": 12}


def r(reg: str | int) -> int:
    return reg if isinstance(reg, int) else RN[reg]


def mop_rr7(rd: str | int, rs1: str | int, rs2: str | int) -> int:
    return 0xCE004073 | (r(rs2) << 20) | (r(rs1) << 15) | (r(rd) << 7)


def mop_r(n: int, rd: str | int, rs1: str | int) -> int:
    """mop.r.n: 1 n4 00 n3 n2 0111 n1 n0 rs1 100 rd 1110011."""
    hi = (1 << 11) | (((n >> 4) & 1) << 10) | (((n >> 3) & 1) << 7) | (((n >> 2) & 1) << 6) | (0b0111 << 2) | (n & 3)
    return (hi << 20) | (r(rs1) << 15) | (4 << 12) | (r(rd) << 7) | 0x73


def sspush(rs2: str | int) -> int:
    return mop_rr7(0, 0, rs2)


def sspopchk(rs1: str | int) -> int:
    return mop_r(28, 0, rs1)


def ssrdp(rd: str | int) -> int:
    return mop_r(28, rd, 0)


def c_mop(n: int) -> int:
    """c.mop.n (n odd, 1..15): 011 0 0 n[3:1] 1 00000 01."""
    return 0x6081 | (((n >> 1) & 7) << 8)


C_SSPUSH = c_mop(1)  # c.sspush x1
C_SSPOPCHK = c_mop(5)  # c.sspopchk x5


def amo(f5: int, width: str, rd: str | int, rs1: str | int, rs2: str | int, aq: int = 0, rl: int = 0) -> int:
    f3 = {"w": 2, "d": 3}[width]
    return (f5 << 27) | (aq << 26) | (rl << 25) | (r(rs2) << 20) | (r(rs1) << 15) | (f3 << 12) | (r(rd) << 7) | 0x2F


def ssamoswap(width: str, rd: str | int, rs1: str | int, rs2: str | int, aq: int = 0, rl: int = 0) -> int:
    return amo(0b01001, width, rd, rs1, rs2, aq, rl)


def amo_tf(e: int) -> int:
    """Transformed AMO for htinst/mtinst: the rs1 field holds the address offset, 0 for AMOs."""
    return e & ~(0x1F << 15)


CBO = {"cbo.inval": 0x0000200F, "cbo.clean": 0x0010200F, "cbo.flush": 0x0020200F, "cbo.zero": 0x0040200F}


def cbo(name: str, rs1: str | int) -> int:
    return CBO[name] | (r(rs1) << 15)


def word(e: int, note: str) -> str:
    return f".word {hex(e)}  // {note}"


def hword(e: int, note: str) -> list[str]:
    """A 16-bit instruction followed by c.nop, so the code after it stays 4-byte aligned."""
    return [f".hword {hex(e)}  // {note}", ".hword 0x0001  // c.nop (realign)"]


def ins(e: int, note: str) -> list[str]:
    """Lines for an instruction encoding (32-bit or compressed)."""
    return hword(e, note) if e < 0x10000 and (e & 3) != 3 else [word(e, note)]


def illegal_tval(e: int) -> list[Value]:
    return [0, e]


# ---------------------------------------------------------------- enables
def menv_sse(t: TestFile, on: bool) -> None:
    t.comment(f"menvcfg.SSE = {int(on)} (T-SBI)")
    t.tsbi_csr("SET" if on else "CLEAR", "MENVCFG", imm=SSE)


def senv_sse(t: TestFile, on: bool) -> None:
    t.comment(f"senvcfg.SSE = {int(on)}")
    t.li("x5", SSE)
    t.emit(f"{'csrs' if on else 'csrc'} {hex(SENVCFG)}, x5  // senvcfg")


def henv_sse(t: TestFile, on: bool) -> None:
    t.comment(f"henvcfg.SSE = {int(on)}")
    t.li("x5", SSE)
    t.emit(f"{'csrs' if on else 'csrc'} {hex(HENVCFG)}, x5  // henvcfg")


def set_ssp(t: TestFile, value: Value, note: str = "", reg: str = "x6") -> None:
    """S-mode (or current mode) write of ssp; needs ssp access in the current mode."""
    t.load(reg, value, note or "ssp value")
    t.emit(f"csrw {hex(SSP)}, {reg}  // ssp")


def read_ssp(t: TestFile, reg: str) -> None:
    t.emit(f"csrr {reg}, {hex(SSP)}  // ssp")


def sstatus_bits(t: TestFile, bits: int, on: bool, csr: str = "sstatus") -> None:
    t.li("x5", bits)
    t.emit(f"{'csrs' if on else 'csrc'} {csr}, x5")


# ---------------------------------------------------------------- paging
def va(i: int, off: int = 0) -> X:
    return X(VA0[32] + i * 0x1000 + off, VA0[64] + i * 0x1000 + off)


class Map:
    """One test page: a data page (name) mapped at VA0 + idx*4K with perms (None: invalid PTE)."""

    def __init__(self, name: str, perms: int | None, contents: dict | None = None, extra: X | None = None) -> None:
        self.name, self.perms, self.contents, self.extra = name, perms, contents or {}, extra


def vm_setup(t: MemTest, maps: list[Map], user: bool = False, root: str = "satp", tag: str = "") -> None:
    """Build an S-level page table with the identity map, the pages of maps (index = position) and, with user,
    the U alias of the code region, then write satp (or vsatp with root="vsatp", for VS-mode code). The table
    root is chosen per XLEN. Clobbers x5-x9. Reading the satp MODE back (vm_either) tells whether the hart
    supports it."""
    for m in maps:
        t.page(m.name + tag, m.contents)

    def body(xlen: int) -> None:
        pt = PT(t, f"{root}{tag}{xlen}", SCHEME[xlen], xlen)
        pt.identity(V | R | W | XP | A | D, 2)
        if root == "satp":
            low_io(t, pt, xlen)
        if user:
            sh = SPSHIFT[xlen]
            t.comment(f"U alias of the code region at {hex(ALIAS[xlen])}")
            for k in range(2):
                tgt = "rvtest_code_begin" if k == 0 else f"rvtest_code_begin+{hex(k << sh)}"
                pt.leaf(ALIAS[xlen] + (k << sh), tgt, V | R | W | XP | A | D | U, level=len(pt.geo) - 1)
        for i, m in enumerate(maps):
            a = VA0[xlen] + i * 0x1000
            if m.perms is None:
                pt.raw(a, 0, note=f"({m.name}: invalid)")
            elif m.extra is not None and m.extra.at(xlen):
                pt.leaf(a, f"ai_pg_{m.name}{tag}", m.perms, note=f"({m.name})")
                pt.pte_addr(a, len(pt.geo) - 1)
                t.emit("LREG x6, 0(x8)")
                t.emit(f"li x7, {hex(m.extra.num(xlen))}")
                t.emit("or x6, x6, x7")
                t.emit("SREG x6, 0(x8)")
            else:
                pt.leaf(a, f"ai_pg_{m.name}{tag}", m.perms, note=f"({m.name})")
        if user:
            sh = SPSHIFT[xlen]
            t.comment("register the U alias in the S save area (as SAVE_AREA_SETUP does)")
            t.la("x6", "rvtest_code_begin")
            t.emit(f"slli x6, x6, {xlen - sh}")
            t.emit(f"srli x6, x6, {xlen - sh}")
            t.emit(f"li x7, {hex(ALIAS[xlen])}")
            t.emit("or x6, x6, x7")
            t.la("x7", "Mtramptbl_sv")
            t.emit("SREG x6, code_bgn_off+sv_area_sz(x7)")
        pt.atp("x6")
        t.emit(f"csrw {hex(SATP if root == 'satp' else VSATP)}, x6  // {root}")

    both(t, body)
    t.emit("sfence.vma" if root == "satp" else ".word 0x22000073  // hfence.vvma")
    t.vm_user = user  # type: ignore[attr-defined]


def low_io(t: MemTest, pt: PT, xlen: int) -> None:
    """Identity map VAs below VA0 (RW, no X, no U) so the framework's failure reporter can still reach MMIO devices
    (e.g. a UART at 0x10000000) from S-mode while the test's map is on."""
    t.comment("identity map low memory (MMIO for the failure reporter), RW, no X/U")
    if xlen == 64:
        t.emit(f"li x6, {hex(V | R | W | A | D)}  // gigapage 0")
        t.la("x8", pt.root)
        t.emit("SREG x6, 0(x8)")
        return
    n = VA0[32] >> 22
    loop = t.label("lowio")
    t.la("x8", pt.root)
    t.emit(f"li x6, {hex(V | R | W | A | D)}")
    t.emit(f"li x9, {n}")
    t.emit(f"{loop}:", 0)
    t.emit("SREG x6, 0(x8)", n)
    t.emit("addi x8, x8, 4", n)
    t.emit("li x7, 0x100000", n)
    t.emit("add x6, x6, x7", n)
    t.emit("addi x9, x9, -1", n)
    t.emit(f"bnez x9, {loop}", n)


def vm_off(t: MemTest, root: str = "satp") -> None:
    t.comment(f"{root} = Bare; unregister the U alias")
    t.emit(f"csrw {hex(SATP if root == 'satp' else VSATP)}, x0")
    t.emit("sfence.vma" if root == "satp" else ".word 0x22000073  // hfence.vvma")
    if getattr(t, "vm_user", False):
        t.la("x7", "Mtramptbl_sv")
        t.emit("LREG x6, code_bgn_off(x7)")
        t.emit("SREG x6, code_bgn_off+sv_area_sz(x7)")
    t.vm_user = False  # type: ignore[attr-defined]


def vm_either(t: TestFile, body: Callable[[], object], root: str = "satp") -> None:
    """Run body only if the satp (vsatp) MODE written by vm_setup took effect (the hart supports it)."""
    t.emit(f"csrr x9, {hex(SATP if root == 'satp' else VSATP)}  // probe: MODE accepted?")
    with t.rv64_only():
        t.emit("srli x9, x9, 60")
    with t.rv32_only():
        t.emit("srli x9, x9, 31")
    t.either("x9", body, lambda: t.comment("paging MODE not supported: skipped"))


# ---------------------------------------------------------------- windows
def uwin(t: TestFile, lines: list[str], expect: Expect, desc: str, tval: Expect | None = None) -> str:
    """A U-mode trap window while the S-level map is on: U-mode is entered and left through T-SBI GOTOs, which
    run U code in the registered U alias. When a trap is certain, xepc is checked against the alias address."""
    lab = t.label("in_U")
    t.allow(1)
    t.emit("RVTEST_TSBI_GOTO_UMODE", 120)
    t.emit(f"{lab}:", 0)
    for ln in lines:
        t.emit(ln)
    t.emit("RVTEST_TSBI_GOTO_SMODE", 120)
    alts = expect if isinstance(expect, list) else [expect]
    t.outcome(expect, lab, f"{desc} in U-mode", tval, epc=False, origin="U")
    if "ok" not in alts:
        t.emit("AI_LOG(x15, TRAPLOG_EPC)", 10)
        for xlen in (32, 64):
            with t.only_if(f"__riscv_xlen == {xlen}"):
                sh = SPSHIFT[xlen]
                t.la("x13", "rvtest_code_begin")
                t.emit(f"srli x13, x13, {sh}")
                t.emit(f"slli x13, x13, {sh}")
                t.emit(f"li x14, {hex(ALIAS[xlen])}")
                t.emit("sub x15, x15, x14")
                t.emit("add x15, x15, x13")
        t.check("x15", lab, lab, f"{desc} in U-mode: xepc is the trapping instruction (in the U alias)")
    return lab


def win(t: TestFile, mode: str, lines: list[str], expect: Expect, desc: str, tval: Expect | None = None) -> str:
    if mode == "U" and getattr(t, "vm_user", False):
        return uwin(t, lines, expect, desc, tval)
    return t.window(mode, lines, expect, desc, tval)


def phys_load(t: TestFile, sym: str, off: int | X, reg: str) -> None:
    """reg = the XLEN-bit word at physical address sym+off (T-SBI load in M-mode, untranslated)."""
    o = off if isinstance(off, X) else X(off, off)
    with t.rv64_only():
        t.la("a1", f"{sym}+{o.num(64)}")
        t.emit("RVTEST_TSBI_LD", 120)
    with t.rv32_only():
        t.la("a1", f"{sym}+{o.num(32)}")
        t.emit("RVTEST_TSBI_LW", 120)
    if reg != "a0":
        t.emit(f"mv {reg}, a0")


def page_bytes(t: MemTest, name: str) -> bytearray:
    _, c = t.pages[f"ai_pg_{name}"]
    data = bytearray(4096)
    for o, (s, v) in c.items():
        data[o : o + s] = (v & ((1 << (8 * s)) - 1)).to_bytes(s, "little")
    return data


def xword(data: bytes | bytearray, off: int | X) -> X:
    """The XLEN-bit little-endian word at off in data, per XLEN."""
    o = off if isinstance(off, X) else X(off, off)
    return X(
        int.from_bytes(data[o.num(32) : o.num(32) + 4], "little"),
        int.from_bytes(data[o.num(64) : o.num(64) + 8], "little"),
    )


def mem_check(t: MemTest, page: str, off: int | X, expect: Value, lab: str, desc: str) -> None:
    phys_load(t, f"ai_pg_{page}", off, "a0")
    t.check("a0", expect, lab, desc)


def ssp_check(t: TestFile, expect: Value, lab: str, desc: str) -> None:
    read_ssp(t, "x7")
    t.check("x7", expect, lab, desc)
