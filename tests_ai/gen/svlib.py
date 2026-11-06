# SPDX-License-Identifier: Apache-2.0
"""Helpers for the supervisor virtual-memory rule-derived tests (gen_Sv.py).

Tests boot to S-mode and build their page tables at run time in the data section (hmem.MemTest). Each table
identity-maps the test image with S-mode superpages (4 MiB on Sv32, 1 GiB on Sv39/48/57, through pointer tables
on Sv48/57), so S-mode code, the trap handlers and the data keep working once satp is written. A second, user
alias maps the image again DELTA higher with U=1 for U-mode code; it is registered with the framework (the S
save area's code_bgn) so T-SBI GOTOs move between the two views (TSBI_RELOCATE_EPC in rvtest_trap_handler.h).
Test pages are mapped at constant virtual addresses away from the image, so every expected xtval is a constant.

Every data page holds sig(id) at offset 0 and, at EXEC_OFF, "addi x7, x0, id; jalr x0, 0(x1)", so a fetch through
any mapping shows which physical page ran (x7 = id) and returns to the caller.

This module holds no expectations; gen_Sv.py owns them (and the mutants).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

sys.path.insert(0, str(Path(__file__).parent))
from aigen import NO_TRAP, ORIGIN, TestFile, X, xv
from hmem import MemTest, sig

if TYPE_CHECKING:
    from aigen import Expect, Value

ISSUE = "https://github.com/riscv/riscv-isa-manual/issues/"
SUP = "src/priv/supervisor.adoc"
MAC = "src/priv/machine.adoc"
MARCH = "rv${XLEN}i_zicsr_zifencei"

V, R, W, XP, U, G, A, D = 1, 2, 4, 8, 16, 32, 64, 128
RWX = R | W | XP
LEAF = V | RWX | A | D  # supervisor leaf with every permission
ULEAF = LEAF | U
N_BIT = 1 << 63
PBMT_NC, PBMT_IO, PBMT_RSV = 1 << 61, 2 << 61, 3 << 61

LOAD_PF, STORE_PF, INSN_PF = 13, 15, 12
LOAD_AF, STORE_AF, INSN_AF = 5, 7, 1
ILLEGAL, VIRTUAL = 2, 22
PF = {"load": LOAD_PF, "store": STORE_PF, "fetch": INSN_PF, "amo": STORE_PF}
AF = {"load": LOAD_AF, "store": STORE_AF, "fetch": INSN_AF, "amo": STORE_AF}

# (shift, index bits) of each level from the root down
GEO = {
    "sv32": [(22, 10), (12, 10)],
    "sv39": [(30, 9), (21, 9), (12, 9)],
    "sv48": [(39, 9), (30, 9), (21, 9), (12, 9)],
    "sv57": [(48, 9), (39, 9), (30, 9), (21, 9), (12, 9)],
}
MODE = {"sv32": 1, "sv39": 8, "sv48": 9, "sv57": 10}
VABITS = {"sv32": 32, "sv39": 39, "sv48": 48, "sv57": 57}
EXT = {"sv32": "Sv32", "sv39": "Sv39", "sv48": "Sv48", "sv57": "Sv57"}
BASE = {32: "sv32", 64: "sv39"}  # the scheme scheme-independent tests use (probed at run time)
VA_T = {32: 0x2000_0000, 64: 0x4000_0000}  # 4 KiB test pages
DELTA = {32: 0x1000_0000, 64: 1 << 32}  # user alias of the image = PA + DELTA
IMG = 0x8000_0000  # where every configuration links the image (only the upper-level path assumes it)
EXEC_OFF = 0x100
IO_VA = 0x1000_0000  # console MMIO of every configuration (rvmodel_macros.h)

SFENCE = "sfence.vma x0, x0"
CSR_SATP = 0x180
SUM, MXR, SPP = 1 << 18, 1 << 19, 1 << 8
# menvcfg bits (RV64 menvcfg / RV32 menvcfgh bit - 32)
ADUE_BIT, PBMTE_BIT = 61, 62
CBCFE, CBZE = 1 << 6, 1 << 7


def xl(scheme: str) -> int:
    return 32 if scheme == "sv32" else 64


def addi_x7(imm: int) -> int:
    return (imm << 20) | (7 << 7) | 0x13


JALR_RET = 0x00008067  # jalr x0, 0(x1)


def canon(va: int, bits: int) -> int:
    """Sign-extend a bits-wide virtual address to 64 bits (as an unsigned 64-bit value)."""
    va &= (1 << bits) - 1
    if va >> (bits - 1):
        va |= ((1 << 64) - 1) ^ ((1 << bits) - 1)
    return va


# ---------------------------------------------------------------- test file with data blocks
class SvTest(MemTest):
    """MemTest whose pages also carry an executable stub at EXEC_OFF, plus naturally aligned blocks of pages."""

    def __init__(self, *a: Any, **kw: Any) -> None:  # noqa: ANN401 (TestFile's arguments, passed through)
        super().__init__(*a, **kw)
        self.blocks: dict[str, tuple[int, int, int]] = {}  # label -> (align log2, npages, first id)
        self._nid = 0

    def _new_id(self) -> int:
        self._nid += 1
        return self._nid

    def page(self, name: str, contents: dict[int, tuple[int, int]] | None = None) -> str:
        lab = f"ai_pg_{name}"
        if lab not in self.pages:
            pid = self._new_id()
            c = {0: (8, sig(pid)), EXEC_OFF: (4, addi_x7(pid)), EXEC_OFF + 4: (4, JALR_RET)}
            c.update(contents or {})
            self.pages[lab] = (pid, c)
        return lab

    def page_id(self, name: str) -> int:
        return self.pages[f"ai_pg_{name}"][0]

    def block(self, name: str, npages: int, align_log2: int) -> str:
        """npages contiguous pages aligned to 2^align_log2; page j has id block_id(name, j)."""
        lab = f"ai_blk_{name}"
        if lab not in self.blocks:
            first = self._nid + 1
            self._nid += npages
            self.blocks[lab] = (align_log2, npages, first)
        return lab

    def block_id(self, name: str, j: int) -> int:
        return self.blocks[f"ai_blk_{name}"][2] + j

    def _block_data(self) -> list[str]:
        out = []
        for lab, (al, n, first) in self.blocks.items():
            out += [f"  .p2align {al}", f"{lab}:"]
            for j in range(n):
                pid = first + j
                data = bytearray(4096)
                data[0:8] = sig(pid).to_bytes(8, "little")
                data[EXEC_OFF : EXEC_OFF + 4] = addi_x7(pid).to_bytes(4, "little")
                data[EXEC_OFF + 4 : EXEC_OFF + 8] = JALR_RET.to_bytes(4, "little")
                end = (EXEC_OFF + 8 + 15) // 16 * 16
                for i in range(0, end, 16):
                    out.append("  .byte " + ", ".join(f"0x{b:02x}" for b in data[i : i + 16]))
                out.append(f"  .fill {4096 - end}, 1, 0")
        return out

    def render(self) -> str:
        self.extra_data = ["  // page tables and data pages (svlib.py)", *self._extra_data(), *self._block_data()]
        return TestFile.render(self)


def lsig(pid: int) -> int:
    """What lw (sign-extended, always positive here) reads at offset 0 of page pid."""
    return sig(pid) & 0xFFFFFFFF


# ---------------------------------------------------------------- page tables
class SvPT:
    """An S-stage page table for one scheme, built at run time inside an XLEN-specific block."""

    def __init__(self, t: SvTest, name: str, scheme: str) -> None:
        self.t, self.name, self.scheme = t, name, scheme
        self.geo = GEO[scheme]
        self.xlen = xl(scheme)
        self.pte = 4 if scheme == "sv32" else 8
        self.root = t.pt_table(f"{name}_root")
        self.children: dict[tuple[str, int], str] = {}
        self.delta = DELTA[self.xlen]
        self.va_t = VA_T[self.xlen]
        # depth of the table whose leaves identity-map the image (4 MiB / 1 GiB pages)
        self.id_depth = {"sv32": 0, "sv39": 0, "sv48": 1, "sv57": 2}[scheme]

    @property
    def levels(self) -> int:
        return len(self.geo)

    def depth(self, level: int) -> int:
        """Table depth (0 = root) of the PTEs that map pages of `level` (0 = 4 KiB)."""
        return self.levels - 1 - level

    def idx(self, addr: int, depth: int) -> int:
        shift, bits = self.geo[depth]
        return (addr >> shift) & ((1 << bits) - 1)

    def _store(self, tab: str, idx: int, reg: str = "x6") -> None:
        t = self.t
        t.la("x8", tab)
        t.emit(f"li x7, {idx * self.pte}")
        t.emit("add x8, x8, x7")
        t.emit(f"SREG {reg}, 0(x8)")

    def pointer(self, addr: int, depth: int) -> str:
        """Ensure pointer PTEs for addr down to the table at `depth`; return that table's label."""
        tab = self.root
        for lvl in range(depth):
            key = (tab, self.idx(addr, lvl))
            if key not in self.children:
                child = self.t.pt_table(f"{self.name}_t{len(self.children) + 1}")
                self.children[key] = child
                self.t.la("x6", child)
                self.t.emit("srli x6, x6, 12")
                self.t.emit("slli x6, x6, 10")
                self.t.emit("ori x6, x6, 1  // V: pointer")
                self._store(tab, key[1])
            tab = self.children[key]
        return tab

    def table_of(self, addr: int, depth: int) -> str:
        return self.pointer(addr, depth)

    def leaf(
        self,
        addr: int,
        target: str | int,
        perms: int,
        level: int = 0,
        ppn_add: int = 0,
        note: str = "",
    ) -> None:
        """Map addr to target (label or constant address) with a leaf at `level` (0 = 4 KiB). The PPN is the
        target's, aligned to the page size, plus ppn_add (to build misaligned superpages). perms may hold high
        bits (N, PBMT, reserved) on RV64."""
        t = self.t
        depth = self.depth(level)
        tab = self.pointer(addr, depth)
        shift = self.geo[depth][0]
        tname = target if isinstance(target, str) else hex(target)
        t.comment(f"{self.name}: {hex(addr)} -> {tname} level {level} pte bits {hex(perms)} {note}")
        if isinstance(target, str):
            t.la("x6", target)
            t.emit(f"srli x6, x6, {shift}")
            t.emit(f"slli x6, x6, {shift - 2}")
        else:
            t.emit(f"li x6, {hex((target >> shift) << (shift - 2))}")
        if ppn_add:
            t.emit(f"li x7, {hex(ppn_add << 10)}")
            t.emit("add x6, x6, x7")
        t.emit(f"li x7, {hex(perms)}")
        t.emit("or x6, x6, x7")
        self._store(tab, self.idx(addr, depth))

    def leaf_napot(self, addr: int, target: str, perms: int, low: int, nbits: int = 4) -> None:
        """4 KiB-level leaf for addr whose PPN is target's with its low nbits replaced by `low` (Svnapot)."""
        t = self.t
        tab = self.pointer(addr, self.depth(0))
        t.comment(f"{self.name}: {hex(addr)} -> {target} PPN[{nbits - 1}:0]={bin(low)} pte bits {hex(perms)}")
        t.la("x6", target)
        t.emit(f"srli x6, x6, {12 + nbits}")
        t.emit(f"slli x6, x6, {nbits}")
        if low:
            t.emit(f"ori x6, x6, {low}")
        t.emit("slli x6, x6, 10")
        t.emit(f"li x7, {hex(perms)}")
        t.emit("or x6, x6, x7")
        self._store(tab, self.idx(addr, self.depth(0)))

    def raw(self, addr: int, value: int, level: int = 0, note: str = "") -> None:
        tab = self.pointer(addr, self.depth(level))
        self.t.comment(f"{self.name}: raw PTE {hex(value)} for {hex(addr)} level {level} {note}")
        self.t.emit(f"li x6, {hex(value)}")
        self._store(tab, self.idx(addr, self.depth(level)))

    def leaf_rt(self, lab: str, target: str, perms: int) -> None:
        """Map the VA equal to label lab's run-time address to target (4 KiB leaf) through a fresh chain of
        tables. lab's root slot must not be used by anything else (no identity map in this table)."""
        t = self.t
        t.comment(f"{self.name}: {lab} (run-time address) -> {target} perms {hex(perms)}")
        tab = self.root
        child = ""
        for depth in range(self.levels):
            shift, bits = self.geo[depth]
            t.la("x9", lab)
            t.emit(f"srli x9, x9, {shift}")
            t.emit(f"slli x9, x9, {self.xlen - bits}")
            t.emit(f"srli x9, x9, {self.xlen - bits}")
            t.emit(f"slli x9, x9, {2 if self.pte == 4 else 3}")
            if depth < self.levels - 1:
                child = t.pt_table(f"{self.name}_r{depth}")
                t.la("x6", child)
                t.emit("srli x6, x6, 12")
                t.emit("slli x6, x6, 10")
                t.emit("ori x6, x6, 1")
            else:
                t.la("x6", target)
                t.emit("srli x6, x6, 12")
                t.emit("slli x6, x6, 10")
                t.emit(f"li x7, {hex(perms)}")
                t.emit("or x6, x6, x7")
            t.la("x8", tab)
            t.emit("add x8, x8, x9")
            t.emit("SREG x6, 0(x8)")
            if depth < self.levels - 1:
                tab = child

    def pte_addr(self, addr: int, depth: int, reg: str = "x8") -> None:
        """reg = address of the PTE for addr in the table at `depth` (which must exist). Clobbers x7."""
        tab = self.pointer(addr, depth)
        self.t.la(reg, tab)
        self.t.emit(f"li x7, {self.idx(addr, depth) * self.pte}")
        self.t.emit(f"add {reg}, {reg}, x7")

    def modify(self, addr: int, depth: int, set_bits: int = 0, clear_bits: int = 0, note: str = "") -> None:
        """Read-modify-write the PTE for addr at `depth` (leaf or pointer)."""
        t = self.t
        t.comment(
            f"{self.name}: PTE for {hex(addr)} at depth {depth}: set {hex(set_bits)} clear {hex(clear_bits)} {note}"
        )
        self.pte_addr(addr, depth)
        t.emit("LREG x6, 0(x8)")
        if clear_bits:
            t.emit(f"li x7, {hex(clear_bits)}")
            t.emit("not x7, x7")
            t.emit("and x6, x6, x7")
        if set_bits:
            t.emit(f"li x7, {hex(set_bits)}")
            t.emit("or x6, x6, x7")
        t.emit("SREG x6, 0(x8)")

    def read_pte(self, addr: int, depth: int, reg: str) -> None:
        """reg = the PTE for addr at `depth` (S-mode load through the identity map)."""
        self.pte_addr(addr, depth)
        self.t.emit(f"LREG {reg}, 0(x8)")

    def _image_slots(self, perms: int, delta: int, n: int, note: str) -> None:
        t = self.t
        tab = self.pointer(IMG, self.id_depth)
        shift, bits = self.geo[self.id_depth]
        t.comment(f"{self.name}: {note}")
        for k in range(n):
            t.la("x6", "rvtest_entry_point")
            t.emit(f"srli x6, x6, {shift}")
            if k:
                t.emit(f"addi x6, x6, {k}")
            t.emit(f"slli x7, x6, {shift - 2}")
            t.emit(f"li x9, {hex(perms)}")
            t.emit("or x7, x7, x9")
            if delta:
                t.emit(f"li x9, {hex(delta >> shift)}")
                t.emit("add x6, x6, x9")
            t.emit(f"slli x6, x6, {self.xlen - bits}")
            t.emit(f"srli x6, x6, {self.xlen - bits}")
            t.la("x8", tab)
            t.emit(f"slli x6, x6, {2 if self.pte == 4 else 3}")
            t.emit("add x8, x8, x6")
            t.emit("SREG x7, 0(x8)")

    def identity(self, perms: int = LEAF) -> None:
        self._image_slots(perms, 0, 2, f"identity map the image with two superpages at depth {self.id_depth}")
        # The failure reporter writes the DUT's console from the failing mode, with satp still active; every
        # configuration's console is at 0x10000000-0x1001ffff, so identity-map that superpage (RW, not X).
        self.leaf(IO_VA, IO_VA, V | R | W | A | D, level=1, note="console MMIO for the failure reporter")

    def user_alias(self, perms: int = ULEAF) -> None:
        self._image_slots(perms, self.delta, 2, f"user alias of the image at PA + {hex(self.delta)}")

    def atp(self, reg: str = "x6", asid: int = 0) -> None:
        """reg = satp selecting this table. Clobbers x7."""
        t = self.t
        t.la(reg, self.root)
        t.emit(f"srli {reg}, {reg}, 12")
        if self.xlen == 64:
            t.emit(f"li x7, {hex((MODE[self.scheme] << 60) | (asid << 44))}")
        else:
            t.emit(f"li x7, {hex((1 << 31) | (asid << 22))}")
        t.emit(f"or {reg}, {reg}, x7")

    def on(self, asid: int = 0, fence: bool = True) -> None:
        self.atp("x6", asid)
        self.t.emit("csrw satp, x6")
        if fence:
            self.t.emit(SFENCE)


# ---------------------------------------------------------------- run-time setup
def register_alias(t: SvTest, pt: SvPT) -> None:
    """Register the user alias of the code region with the framework (S save area code_bgn)."""
    t.comment("register the user alias of the code region for T-SBI GOTOs (TSBI_RELOCATE_EPC)")
    t.la("x6", "Mtramptbl_sv")
    t.emit("li x7, sv_area_sz")
    t.emit("add x6, x6, x7")
    t.la("x7", "rvtest_code_begin")
    t.emit(f"li x8, {hex(pt.delta)}")
    t.emit("add x7, x7, x8")
    t.emit("SREG x7, code_bgn_off(x6)")


def unregister_alias(t: SvTest) -> None:
    t.la("x6", "Mtramptbl_sv")
    t.emit("li x7, sv_area_sz")
    t.emit("add x6, x6, x7")
    t.la("x7", "rvtest_code_begin")
    t.emit("SREG x7, code_bgn_off(x6)")


def satp_off(t: SvTest) -> None:
    t.comment("satp = Bare")
    t.emit("csrw satp, x0")
    t.emit(SFENCE)


def probe(t: SvTest, pt: SvPT, reg: str = "x1") -> None:
    """reg = 1 if satp accepts pt's MODE (written with pt's root, which must identity-map the image).
    satp is left Bare. Clobbers x6, x7."""
    t.comment(f"probe: does satp accept {pt.scheme}?")
    pt.atp("x6")
    t.emit("csrw satp, x6")
    t.emit(f"csrr {reg}, satp")
    t.emit("csrw satp, x0")
    t.emit(SFENCE)
    if pt.xlen == 64:
        t.emit(f"srli {reg}, {reg}, 60")
        t.emit(f"addi {reg}, {reg}, -{MODE[pt.scheme]}")
        t.emit(f"seqz {reg}, {reg}")
    else:
        t.emit(f"srli {reg}, {reg}, 31")


def sstatus_bits(t: SvTest, mask: int, on: bool, note: str = "") -> None:
    t.emit(f"li x7, {hex(mask)}")
    t.emit(f"{'csrs' if on else 'csrc'} sstatus, x7  // {note or hex(mask)} = {int(on)}")


def menvcfg_bit(t: SvTest, xlen: int, bit: int, on: bool) -> None:
    """T-SBI set/clear of menvcfg bit `bit` (0..63); RV32 uses menvcfgh for bits >= 32."""
    op = "SET" if on else "CLEAR"
    t.comment(f"menvcfg bit {bit} = {int(on)}")
    if xlen == 64 or bit < 32:
        t.emit(f"li a1, {hex(1 << bit)}")
        t.tsbi_csr(op, "MENVCFG", "a1")
    else:
        t.emit(f"li a1, {hex(1 << (bit - 32))}")
        t.tsbi_csr(op, "MENVCFGH", "a1")


def menvcfg_get(t: SvTest, xlen: int, bit: int, reg: str) -> None:
    """reg = menvcfg bit `bit` (T-SBI read)."""
    if xlen == 64 or bit < 32:
        t.tsbi_csr("READ", "MENVCFG")
        b = bit
    else:
        t.tsbi_csr("READ", "MENVCFGH")
        b = bit - 32
    t.emit(f"srli {reg}, a0, {b}")
    t.emit(f"andi {reg}, {reg}, 1")


# ---------------------------------------------------------------- trap windows
def outcome(
    t: SvTest,
    expect: Expect,
    lab: str,
    desc: str,
    epc: Value | None = None,
    tval: Expect | None = None,
    origin: str | None = None,
) -> None:
    """Close the window opened by t.allow() and check its outcome (as TestFile.outcome), with xepc checked
    against `epc` (a label, a 'label+offset' string, or a constant) instead of the window's label."""
    alts = expect if isinstance(expect, list) else [expect]
    oks = "ok" in alts
    causes = [a for a in alts if a != "ok"]
    t.emit("AI_OUTCOME", 20)
    t.check("x13", [0, 1] if oks and causes else (0 if oks else 1), lab, f"{desc}: number of traps")
    t.check(
        "x14", [NO_TRAP if a == "ok" else a for a in alts], lab, f"{desc}: outcome (xcause, or all ones for no trap)"
    )
    if not causes or not (epc is not None or tval is not None or origin):
        return
    skip, done = t.label("notrap"), t.label("checked")
    if oks:
        t.emit("li x5, -1")
        t.emit(f"beq x14, x5, {skip}")
    first = len(t.table)
    if epc is not None:
        t.emit("AI_LOG(x15, TRAPLOG_EPC)", 10)
        t.check("x15", epc, lab, f"{desc}: xepc is the faulting instruction")
    if tval is not None:
        t.emit("AI_LOG(x15, TRAPLOG_TVAL)", 10)
        t.check("x15", tval, lab, f"{desc}: xtval is one of its legal values")
    if origin:
        t.emit("AI_ORIGIN", 25)
        t.check("x15", ORIGIN[origin], lab, f"{desc}: xPP records the mode the trap came from (0 U, 1 S, 3 M)")
    if oks:
        t.emit(f"j {done}")
        t.emit(f"{skip}:", 0)
        t.code += t._skip_lines(first, len(t.table))
        t.emit(f"{done}:", 0)


def enter_u_alias(t: SvTest, pt: SvPT, lab: str) -> None:
    """sret from S-mode to U-mode at the user alias of lab (clobbers x5, x14; keeps x13)."""
    t.la("x14", lab)
    t.emit(f"li x5, {hex(pt.delta)}")
    t.emit("add x14, x14, x5")
    t.emit("csrw sepc, x14")
    t.emit("li x14, 0x100")
    t.emit("csrc sstatus, x14  // SPP = U")
    t.emit("#ifdef H_SUPPORTED", 0)
    t.emit("LI(x14, HSTATUS_SPV)", 2)
    t.emit("csrc 0x600, x14  // hstatus.SPV = 0", 1)
    t.emit("#endif", 0)
    t.emit("sret")


def win(
    t: SvTest,
    pt: SvPT | None,
    mode: str,
    lines: list[str],
    expect: Expect,
    desc: str,
    tval: Expect | None = None,
    epc: Value | None | str = "insn",
    pre: list[str] | tuple = (),
) -> str:
    """Run lines in `mode` (S, or U through the user alias of pt; with pt=None U runs at the physical address,
    for Bare) in a trap window. The first line is the instruction under test; epc="insn" expects xepc there
    (in the view the mode executes from); pass a constant for fetch faults. Returns the label."""
    lab = t.label(f"in_{mode}")
    t.allow(1)
    if mode == "U":
        if pt is not None:
            enter_u_alias(t, pt, lab)
        else:
            t.enter("U")
    for ln in pre:
        t.emit(ln)
    t.emit(f"{lab}:", 0)
    for ln in lines:
        t.emit(ln)
    if mode == "U":
        t.leave()
    if epc == "insn":
        epc = f"{lab}+{hex(pt.delta)}" if (mode == "U" and pt is not None) else lab
    outcome(t, expect, lab, f"{desc} in {mode}-mode", epc, tval, origin=mode)
    return lab


# instruction encodings (no extension needed in MARCH)
def enc_r(f7: int, rs2: int, rs1: int, f3: int, rd: int, op: int) -> int:
    return (f7 << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | op


def lr_w(rd: int, rs1: int) -> int:
    return enc_r(0x08, 0, rs1, 2, rd, 0x2F)


def sc_w(rd: int, rs1: int, rs2: int) -> int:
    return enc_r(0x0C, rs2, rs1, 2, rd, 0x2F)


def amoadd_w(rd: int, rs1: int, rs2: int) -> int:
    return enc_r(0x00, rs2, rs1, 2, rd, 0x2F)


def cbo(op: str, rs1: int) -> int:
    f12 = {"inval": 0, "clean": 1, "flush": 2, "zero": 4}[op]
    return (f12 << 20) | (rs1 << 15) | (2 << 12) | 0x0F


def sinval_vma(rs1: int = 0, rs2: int = 0) -> int:
    return 0x16000073 | (rs2 << 20) | (rs1 << 15)


SFENCE_W_INVAL = 0x18000073
SFENCE_INVAL_IR = 0x18100073


def hinval_vvma(rs1: int = 0, rs2: int = 0) -> int:
    return 0x26000073 | (rs2 << 20) | (rs1 << 15)


def hinval_gvma(rs1: int = 0, rs2: int = 0) -> int:
    return 0x66000073 | (rs2 << 20) | (rs1 << 15)


def sfence_vma(rs1: int = 0, rs2: int = 0) -> int:
    return 0x12000073 | (rs2 << 20) | (rs1 << 15)


def word(e: int, note: str) -> str:
    return f".word {hex(e)}  // {note}"


def both(t: SvTest, body) -> None:  # noqa: ANN001
    with t.rv64_only():
        body(64)
    with t.rv32_only():
        body(32)


def xpair(f) -> X:  # noqa: ANN001
    return X(f(32), f(64))


def tv(v: Value) -> X:
    return xv(v)


def guard(t: SvTest, reg: str, body) -> None:  # noqa: ANN001
    """Run body only when reg is nonzero. Like TestFile.either with an empty else, but the skip over body's
    table entries can be large (AI_SKIP's addi immediate cannot), and the branch reaches any distance."""
    clear, done, go = t.label("skip"), t.label("guarded"), t.label("go")
    t.emit(f"bnez {reg}, {go}")
    t.emit(f"j {clear}")
    t.emit(f"{go}:", 0)
    a = len(t.table)
    body()
    b = len(t.table)
    t.emit(f"j {done}")
    t.emit(f"{clear}:", 0)
    for ln in t._skip_lines(a, b):
        s = ln.strip()
        if s.startswith("AI_SKIP("):
            n = s[len("AI_SKIP(") : -1]
            t.code.append(f"  li x5, ({n})*REGWIDTH")
            t.code.append("  add x3, x3, x5")
        else:
            t.code.append(ln)
    t.emit(f"{done}:", 0)
