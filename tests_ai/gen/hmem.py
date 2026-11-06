# SPDX-License-Identifier: Apache-2.0
"""Memory helpers for the H suite's address-translation tests (h_hlsv.py, h_gstage.py).

- MemTest: a TestFile that also emits page tables and data pages in the data section (aligned to 4 KiB, or
  16 KiB for G-stage root tables).
- PT: builds a page table at run time. Addresses the test sees (guest virtual and guest physical addresses)
  are constants chosen by the generator; only the physical pages behind them are labels, so every expected
  xtval/htval is a constant in the table.
- memwin(): a trap window that also checks the trap's GVA, htval/mtval2 and htinst/mtinst, per cause.

Layout used by the tests:
  RV64: G-stage Sv39x4, VS-stage Sv39. RV32: G-stage Sv32x4, VS-stage Sv32.
  The test image (rvtest_entry_point onward) is identity mapped by root-level superpages in each stage that
  needs it, so VS code and the VS view of the data run unchanged. Test pages live at constant GPAs/VAs away
  from the image.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import hlib
from aigen import NO_TRAP, ORIGIN, POOL_TRAP, TestFile, X, xv
from hlib import MARCH, REQ

if TYPE_CHECKING:
    from collections.abc import Callable

    from aigen import Expect, TestFileOptions, Value
    from typing_extensions import Unpack

V, R, W, XP, U, G, A, D = 1, 2, 4, 8, 16, 32, 64, 128
RWX = R | W | XP
LEAF = V | RWX | A | D  # supervisor leaf
ULEAF = LEAF | U  # user leaf (every G-stage leaf needs U)

LOAD_PF, STORE_PF, INSN_PF = 13, 15, 12
LOAD_GPF, STORE_GPF, INSN_GPF = 21, 23, 20
LOAD_MIS, STORE_MIS, LOAD_AF, STORE_AF = 4, 6, 5, 7
# Causes whose xtval may be 0 instead of the faulting address (no Sstvala assumed)
ZERO_TVAL_OK = {0, 1, 4, 5, 6, 7, 12, 13, 15, 20, 21, 23}

# Geometry: list of (shift, index bits) from the root down. 4-byte PTEs for the 32-bit schemes.
GEO = {
    "sv39x4": [(30, 11), (21, 9), (12, 9)],
    "sv48x4": [(39, 11), (30, 9), (21, 9), (12, 9)],
    "sv57x4": [(48, 11), (39, 9), (30, 9), (21, 9), (12, 9)],
    "sv32x4": [(22, 12), (12, 10)],
    "sv39": [(30, 9), (21, 9), (12, 9)],
    "sv48": [(39, 9), (30, 9), (21, 9), (12, 9)],
    "sv32": [(22, 10), (12, 10)],
}
MODE = {"sv39x4": 8, "sv48x4": 9, "sv57x4": 10, "sv32x4": 1, "sv39": 8, "sv48": 9, "sv32": 1}
G_OF = {64: "sv39x4", 32: "sv32x4"}
VS_OF = {64: "sv39", 32: "sv32"}

# Constant addresses (per XLEN). GPAs of test pages in the G-stage maps, and VAs of VS-stage maps.
GPA_BASE = {64: 0x1_4000_0000, 32: 0x4000_0000}
VA_BASE = {64: 0x4000_0000, 32: 0x2000_0000}

HFENCE_GVMA = ".word 0x62000073  // hfence.gvma x0, x0"
HFENCE_VVMA = ".word 0x22000073  // hfence.vvma x0, x0"


def sig(page_id: int) -> int:
    """The 64-bit signature at offset 0 of data page page_id (its low word is what RV32 reads)."""
    return ((0xC0DE0000 + page_id) << 32) | (0x5A5A0000 + page_id * 0x111)


def sig_x(page_id: int) -> X:
    s = sig(page_id)
    return X(s & 0xFFFFFFFF, s)


class MemTest(TestFile):
    """A TestFile with page tables and data pages in its data section."""

    def __init__(self, suite: str, rule: str, *, required: list, **kw: Unpack[TestFileOptions]) -> None:
        super().__init__(suite, rule, required=required, **kw)
        self.tables: dict[str, int] = {}  # label -> size
        self.pages: dict[str, tuple[int, dict[int, tuple[int, int]]]] = {}  # label -> (id, {off: (size, v)})

    def label(self, stem: str) -> str:
        # rule names such as hfence-vvma_* contain '-', which is not valid in an assembler label
        return super().label(stem).replace("-", "_")

    def pt_table(self, name: str, size: int = 4096) -> str:
        lab = f"ai_pt_{name}"
        self.tables.setdefault(lab, size)
        return lab

    def page(self, name: str, contents: dict[int, tuple[int, int]] | None = None) -> str:
        """A 4 KiB data page. Offset 0 holds sig(id) unless contents overrides it; contents maps an offset to
        (size in bytes, value), little-endian."""
        lab = f"ai_pg_{name}"
        if lab not in self.pages:
            pid = len(self.pages) + 1
            c = {0: (8, sig(pid))}
            c.update(contents or {})
            self.pages[lab] = (pid, c)
        return lab

    def page_id(self, name: str) -> int:
        return self.pages[f"ai_pg_{name}"][0]

    def _extra_data(self) -> list[str]:
        out = []
        for lab, size in sorted(self.tables.items(), key=lambda kv: -kv[1]):
            out += [f"  .p2align {14 if size > 4096 else 12}", f"{lab}:", f"  .fill {size}, 1, 0"]
        for lab, (_, c) in self.pages.items():
            data = bytearray(max([o + s for o, (s, _) in c.items()] + [64]))
            for o, (s, v) in c.items():
                data[o : o + s] = (v & ((1 << (8 * s)) - 1)).to_bytes(s, "little")
            out += ["  .p2align 12", f"{lab}:"]
            for i in range(0, len(data), 16):
                out.append("  .byte " + ", ".join(f"0x{b:02x}" for b in data[i : i + 16]))
            out.append(f"  .fill {4096 - len(data)}, 1, 0")
        return out

    def render(self) -> str:
        self.extra_data = ["  // page tables and data pages (hmem.py)", *self._extra_data()]
        return super().render()

    # ---------- trap window with GVA / tval2 / tinst checks per cause
    def outcome2(
        self,
        expect: Expect,
        lab: str,
        desc: str,
        extras: dict | None = None,
        epc: bool = True,
        origin: str | None = None,
        handler: str = "HS",
    ) -> None:
        """Close a window like TestFile.outcome. extras maps a cause to the checks made when that cause was
        taken: {"tval": Expect, "gva": 0/1, "tval2": Expect, "tinst": Expect}. handler is HS or M (where the
        GVA bit lives)."""
        alts = expect if isinstance(expect, list) else [expect]
        oks = "ok" in alts
        causes = [a for a in alts if a != "ok"]
        self.emit("AI_OUTCOME", 20)
        self.check("x13", [0, 1] if oks and causes else (0 if oks else 1), lab, f"{desc}: number of traps")
        self.check(
            "x14",
            [NO_TRAP if a == "ok" else a for a in alts],
            lab,
            f"{desc}: outcome (xcause, or all ones for no trap)",
        )
        if not causes:
            return
        skip, done = self.label("notrap"), self.label("checked")
        first = len(self.table)
        if oks:
            self.emit("li x5, -1")
            self.emit(f"beq x14, x5, {skip}")
        for c, ex in (extras or {}).items():
            if c not in causes:
                continue
            nxt = self.label("nextcause")
            a0 = len(self.table)
            if len(causes) > 1:
                self.load("x5", c, f"cause {c}")
                self.emit(f"bne x14, x5, {nxt}")
            if "tval" in ex:
                tv = ex["tval"] if isinstance(ex["tval"], list) else [ex["tval"]]
                if c in ZERO_TVAL_OK and not any(isinstance(v, int) and v == 0 for v in tv):
                    tv = [0, *tv]  # stval may be 0 unless Sstvala (supervisor.adoc stval_op_faulting_addr)
                self.emit("AI_LOG(x15, TRAPLOG_TVAL)", 10)
                self.check("x15", tv, lab, f"{desc}: cause {c}: xtval is one of its legal values")
            if "gva" in ex:
                self.gva_check(lab, desc, ex["gva"], handler, c)
            if "tval2" in ex:
                self.emit("AI_LOG(x15, TRAPLOG_TVAL2)", 10)
                self.check(
                    "x15",
                    ex["tval2"],
                    lab,
                    f"{desc}: cause {c}: {'htval' if handler == 'HS' else 'mtval2'} is 0 or the GPA >> 2",
                )
            if "tinst" in ex:
                self.emit("AI_LOG(x15, TRAPLOG_TINST)", 10)
                self.check(
                    "x15",
                    ex["tinst"],
                    lab,
                    f"{desc}: cause {c}: {'htinst' if handler == 'HS' else 'mtinst'} is a legal value",
                )
            if len(causes) > 1:
                self.emit(f"j {nxt}_end")
                self.emit(f"{nxt}:", 0)
                self.code += self._skip_lines(a0 + 1, len(self.table))
                self.emit(f"{nxt}_end:", 0)
        if epc:
            self.emit("AI_LOG(x15, TRAPLOG_EPC)", 10)
            self.check("x15", lab, lab, f"{desc}: xepc is the trapping instruction")
        if origin:
            self.emit("AI_ORIGIN", 25)
            self.check(
                "x15",
                ORIGIN[origin],
                lab,
                f"{desc}: xPP/xPV record the mode the trap came from (0 U, 1 S, 3 M, 4 VU, 5 VS)",
            )
        if oks:
            self.emit(f"j {done}")
            self.emit(f"{skip}:", 0)
            self.code += self._skip_lines(first, len(self.table))
            self.emit(f"{done}:", 0)

    def gva_check(self, lab: str, desc: str, gva: int, handler: str, c: int) -> None:
        if handler == "HS":
            self.emit("AI_LOG(x15, TRAPLOG_STATUS2)", 10)  # hstatus on entry
            self.emit("srli x15, x15, 6")
        else:
            with self.rv64_only():
                self.emit("AI_LOG(x15, TRAPLOG_STATUS)", 10)  # mstatus.GVA is bit 38
                self.emit("srli x15, x15, 38")
            with self.rv32_only():
                self.emit("AI_LOG(x15, TRAPLOG_STATUS2)", 10)  # mstatush.GVA is bit 6
                self.emit("srli x15, x15, 6")
        self.emit("andi x15, x15, 1")
        reg = "hstatus" if handler == "HS" else "mstatus"
        if gva != 1:
            self.check("x15", gva, lab, f"{desc}: cause {c}: {reg}.GVA = {gva}")
            return
        # GVA=1 is required only when a guest virtual address was written to xtval (xtval may be 0)
        self.emit("AI_LOG(x14, TRAPLOG_TVAL)", 10)
        self.emit("seqz x14, x14")
        self.emit("or x15, x15, x14")
        self.check_bool("x15", lab, f"{desc}: cause {c}: {reg}.GVA = 1, or xtval = 0")


def new(rule: str, required: list[str] = REQ, **kw: Unpack[TestFileOptions]) -> MemTest:
    kw.setdefault("boot", "S")
    kw.setdefault("pool", POOL_TRAP)
    kw.setdefault("march", MARCH)
    return MemTest(hlib.SUITE, rule, required=required, **kw)


def memwin(
    t: MemTest,
    mode: str,
    lines: list[str],
    expect: Expect,
    desc: str,
    extras: dict | None = None,
    origin: str | None = None,
    handler: str = "HS",
    epc: bool = True,
) -> str:
    """Run lines in mode (entered from t.cur with sret/mret when different) in a trap window; the first line
    is the instruction under test. See MemTest.outcome2."""
    lab = t.label(f"in_{mode}")
    t.allow(1)
    if mode != t.cur:
        t.enter(mode)
    t.emit(f"{lab}:", 0)
    for ln in lines:
        t.emit(ln)
    if mode != t.cur:
        t.leave()
    t.outcome2(expect, lab, f"{desc} in {mode}-mode", extras, epc=epc, origin=origin or mode, handler=handler)
    return lab


def memwin_tsbi(
    t: MemTest,
    mode: str,
    lines: list[str],
    expect: Expect,
    desc: str,
    extras: dict | None = None,
    handler: str = "M",
    epc: bool = True,
) -> str:
    """Like memwin, but enters VS or VU through a T-SBI GOTO (from M-mode or HS-mode) and returns with one."""
    lab = t.label(f"in_{mode}")
    t.allow(1)
    t.emit(f"RVTEST_TSBI_GOTO_{mode}MODE", 120)
    t.emit(f"{lab}:", 0)
    for ln in lines:
        t.emit(ln)
    t.leave()
    t.outcome2(expect, lab, f"{desc} in {mode}-mode", extras, epc=epc, origin=mode, handler=handler)
    return lab


def tval2_consistent(t: MemTest, lab: str, desc: str, gpa_minus_va: int = 0) -> None:
    """After a guest-page fault (certain): htval/mtval2 is 0, or (GPA of the exact faulting address) >> 2, where
    that GPA is xtval + gpa_minus_va (mtval2_htval_virtaddr). Clobbers x13-x15."""
    t.emit("AI_LOG(x13, TRAPLOG_TVAL)", 10)
    t.emit("AI_LOG(x14, TRAPLOG_TVAL2)", 10)
    if gpa_minus_va:
        t.emit(f"li x15, {hex(gpa_minus_va)}")
        t.emit("add x13, x13, x15")
    t.emit("srli x13, x13, 2")
    t.emit("xor x13, x13, x14")
    t.emit("seqz x13, x13  // htval == GPA(xtval) >> 2")
    t.emit("seqz x14, x14  // htval == 0")
    t.emit("or x15, x13, x14")
    t.emit("AI_LOG(x13, TRAPLOG_TVAL)", 10)
    t.emit("seqz x13, x13  // xtval == 0: nothing to correspond to")
    t.emit("or x15, x15, x13")
    t.check_bool("x15", lab, f"{desc}: htval/mtval2 is 0 or the GPA of the address in xtval, >> 2 (or xtval = 0)")


def pseudo_required(t: MemTest, lab: str, desc: str, pseudo: X) -> None:
    """After a guest-page fault on an implicit VS-stage access (certain): if htval/mtval2 is nonzero, htinst/mtinst
    must be the pseudoinstruction (H_trap_xtinst_guestpage). Clobbers x13-x15."""
    t.emit("AI_LOG(x13, TRAPLOG_TVAL2)", 10)
    t.emit("AI_LOG(x14, TRAPLOG_TINST)", 10)
    t.load("x15", pseudo, "required pseudoinstruction")
    t.emit("xor x14, x14, x15")
    t.emit("seqz x14, x14  // tinst == pseudo")
    t.emit("seqz x13, x13  // tval2 == 0")
    t.emit("or x15, x13, x14")
    t.check_bool("x15", lab, f"{desc}: with a nonzero htval/mtval2, htinst/mtinst is the pseudoinstruction")


# ---------------------------------------------------------------- page tables
class PT:
    """A page table built at run time inside an XLEN-specific block of the test (rv64_only / rv32_only)."""

    def __init__(self, t: MemTest, name: str, scheme: str, xlen: int, gpa_base: int | None = None) -> None:
        """gpa_base: the tables live at guest physical addresses gpa_base + i*4K (root first, then children in
        creation order) instead of at their own physical addresses; pointer PTEs and atp() then use those GPAs,
        and the caller maps them in G-stage (self.gpas)."""
        self.t, self.name, self.scheme, self.xlen = t, name, scheme, xlen
        self.geo = GEO[scheme]
        self.pte = xlen // 8
        self.root = t.pt_table(f"{name}_root", 16384 if scheme.endswith("x4") else 4096)
        self.children: dict[tuple[str, int], str] = {}
        self.gpa_base = gpa_base
        self.gpas: dict[str, int] = {} if gpa_base is None else {self.root: gpa_base}

    def _idx(self, addr: int, level: int) -> int:
        shift, bits = self.geo[level]
        return (addr >> shift) & ((1 << bits) - 1)

    def _store(self, table: str, idx: int) -> None:
        t = self.t
        t.la("x8", table)
        t.emit(f"li x7, {idx * self.pte}")
        t.emit("add x8, x8, x7")
        t.emit("SREG x6, 0(x8)")

    def pointer(self, addr: int, depth: int) -> str:
        """Ensure the non-leaf path for addr down to table `depth` (0 = root); return that table's label."""
        tab = self.root
        for lvl in range(depth):
            idx = self._idx(addr, lvl)
            key = (tab, idx)
            if key not in self.children:
                child = self.t.pt_table(f"{self.name}_t{len(self.children) + 1}")
                self.children[key] = child
                if self.gpa_base is not None:
                    self.gpas[child] = self.gpa_base + 0x1000 * len(self.gpas)
                    self.t.emit(f"li x6, {hex(self.gpas[child])}")
                else:
                    self.t.la("x6", child)
                self.t.emit("srli x6, x6, 12")
                self.t.emit("slli x6, x6, 10")
                self.t.emit("ori x6, x6, 1  // V: pointer")
                self._store(tab, idx)
            tab = self.children[key]
        return tab

    def leaf(self, addr: int, target: str | int, perms: int, level: int | None = None, note: str = "") -> None:
        """Map addr (constant) to target (a label, or a constant address) with perms at `level` (default: the
        4 KiB level). Overwrites an existing PTE."""
        t = self.t
        depth = len(self.geo) - 1 if level is None else len(self.geo) - 1 - level
        tab = self.pointer(addr, depth)
        shift = self.geo[depth][0]
        t.comment(
            f"{self.name}: {hex(addr)} -> {target if isinstance(target, str) else hex(target)} "
            f"perms {hex(perms)} {note}".rstrip()
        )
        if isinstance(target, str):
            t.la("x6", target)
            t.emit(f"srli x6, x6, {shift}")
            t.emit(f"slli x6, x6, {shift - 2}")
        else:  # a constant may be wider than XLEN (RV32 34-bit GPAs), so form the PPN field here
            t.emit(f"li x6, {hex((target >> shift) << (shift - 2))}")
        t.emit(f"li x7, {hex(perms)}")
        t.emit("or x6, x6, x7")
        self._store(tab, self._idx(addr, depth))

    def raw(self, addr: int, value: int, level: int | None = None, note: str = "") -> None:
        """Store a raw PTE value (e.g. invalid, reserved bits) for addr."""
        t = self.t
        depth = len(self.geo) - 1 if level is None else len(self.geo) - 1 - level
        tab = self.pointer(addr, depth)
        t.comment(f"{self.name}: raw PTE {hex(value)} for {hex(addr)} {note}".rstrip())
        t.emit(f"li x6, {hex(value)}")
        self._store(tab, self._idx(addr, depth))

    def leaf_runtime(self, lab: str, target: str, perms: int) -> None:
        """Map the guest address equal to label lab's physical address (known only at run time) to target, through
        a fresh chain of tables. The root entry for lab must not be used by anything else (no identity map)."""
        t = self.t
        tab = self.root
        n = len(self.geo)
        t.comment(f"{self.name}: {lab} (run-time address) -> {target} perms {hex(perms)}")
        for depth in range(n):
            shift, bitsn = self.geo[depth]
            t.la("x9", lab)
            t.emit(f"srli x9, x9, {shift}")
            t.emit(f"slli x9, x9, {self.xlen - bitsn}")
            t.emit(f"srli x9, x9, {self.xlen - bitsn}")
            t.emit(f"slli x9, x9, {2 if self.pte == 4 else 3}")
            if depth < n - 1:
                child = t.pt_table(f"{self.name}_r{len(self.children) + 1}")
                self.children[(tab, -1 - len(self.children))] = child
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
                child = tab  # the leaf level has no child table; the loop ends here
            t.la("x8", tab)
            t.emit("add x8, x8, x9")
            t.emit("SREG x6, 0(x8)")
            tab = child

    def pte_addr(self, addr: int, depth: int) -> str:
        """x8 = address of the PTE for addr in the table at `depth` (which must already exist)."""
        tab = self.pointer(addr, depth)
        self.t.la("x8", tab)
        self.t.emit(f"li x7, {self._idx(addr, depth) * self.pte}")
        self.t.emit("add x8, x8, x7")
        return tab

    def identity(self, perms: int, n: int = 2) -> None:
        """Identity map n root-level superpages starting at the one holding rvtest_entry_point."""
        t = self.t
        shift, bits = self.geo[0]
        t.comment(f"{self.name}: identity map the test image with {n} root-level superpages, perms {hex(perms)}")
        for k in range(n):
            t.la("x6", "rvtest_entry_point")
            t.emit(f"srli x6, x6, {shift}")
            if k:
                t.emit(f"addi x6, x6, {k}")
            t.emit(f"slli x7, x6, {shift - 2}")
            t.emit(f"li x9, {hex(perms)}")
            t.emit("or x7, x7, x9")
            t.emit(f"slli x6, x6, {self.xlen - bits}")  # keep the low `bits` bits (root index)
            t.emit(f"srli x6, x6, {self.xlen - bits}")
            t.la("x8", self.root)
            t.emit(f"slli x6, x6, {2 if self.pte == 4 else 3}")
            t.emit("add x8, x8, x6")
            t.emit("SREG x7, 0(x8)")

    def atp(self, reg: str = "x6", vmid_or_asid: int = 0) -> None:
        """reg = the hgatp/vsatp value selecting this table."""
        t = self.t
        if self.gpa_base is not None:
            t.emit(f"li {reg}, {hex(self.gpa_base >> 12)}")
        else:
            t.la(reg, self.root)
            t.emit(f"srli {reg}, {reg}, 12")
        if self.xlen == 64:
            t.emit(f"li x7, {hex((MODE[self.scheme] << 60) | (vmid_or_asid << 44))}")
        else:
            t.emit(f"li x7, {hex((MODE[self.scheme] << 31) | (vmid_or_asid << 22))}")
        t.emit(f"or {reg}, {reg}, x7")


def hgatp_on(t: MemTest, pt: PT, vmid: int = 0) -> None:
    pt.atp("x6", vmid)
    t.emit("csrw 0x680, x6  // hgatp")
    t.emit(HFENCE_GVMA)


def vsatp_on(t: MemTest, pt: PT, asid: int = 0) -> None:
    pt.atp("x6", asid)
    t.emit("csrw 0x280, x6  // vsatp")
    t.emit(HFENCE_VVMA)


def atp_off(t: MemTest) -> None:
    t.comment("hgatp = vsatp = Bare")
    t.emit("csrw 0x680, x0  // hgatp")
    t.emit("csrw 0x280, x0  // vsatp")
    t.emit(HFENCE_GVMA)
    t.emit(HFENCE_VVMA)


def fences(t: MemTest) -> None:
    t.emit(HFENCE_GVMA)
    t.emit(HFENCE_VVMA)


def bits(t: MemTest, csr: int, name: str, mask: int, on: bool) -> None:
    t.emit(f"li x7, {hex(mask)}")
    t.emit(f"{'csrs' if on else 'csrc'} {hex(csr)}, x7  // {name} {'|=' if on else '&= ~'} {hex(mask)}")


SPVP, HU_BIT, VSBE = 1 << 8, 1 << 9, 1 << 5
SUM, MXR = 1 << 18, 1 << 19


def spvp(t: MemTest, on: bool) -> None:
    bits(t, 0x600, "hstatus.SPVP", SPVP, on)


def s_sum(t: MemTest, on: bool) -> None:
    bits(t, 0x100, "sstatus.SUM", SUM, on)


def s_mxr(t: MemTest, on: bool) -> None:
    bits(t, 0x100, "sstatus.MXR", MXR, on)


def vs_sum(t: MemTest, on: bool) -> None:
    bits(t, 0x200, "vsstatus.SUM", SUM, on)


def vs_mxr(t: MemTest, on: bool) -> None:
    bits(t, 0x200, "vsstatus.MXR", MXR, on)


def both(t: MemTest, body: Callable[[int], object]) -> None:
    """Emit body(xlen) once under rv64_only and once under rv32_only."""
    with t.rv64_only():
        body(64)
    with t.rv32_only():
        body(32)


def xpair(f: Callable[[int], int | str]) -> X:
    """X(f(32), f(64))."""
    return X(f(32), f(64))


def tv(v: Value) -> X:
    return xv(v)
