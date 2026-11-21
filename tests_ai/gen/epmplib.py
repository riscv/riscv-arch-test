# SPDX-License-Identifier: Apache-2.0
"""Helpers for the Smepmp suite (gen_Smepmp.py).

mseccfg.MML is sticky until reset and takes execute permission away from M-mode everywhere except in M-mode-only
or locked shared rules with X, so every MML test is a one-shot file that first gives the test image locked
M-mode rules. Layout (from link.ld, which every ACT DUT shares): code from rvtest_entry_point up to the data
section (`scratch`, 16 KiB aligned), data and stack up to __stack_top, then .text.rvmodel from the next 4 KiB
boundary up to _end. Entries:

  0, 1, 7, 8-15  test entries (NAPOT 4 KiB pages P0-P7 of epmp_pages, in the data section, filled with `ret`)
  2              the U page: one 4 KiB code page that S- and U-mode run in, L=0 R+X (S/U-only); the M handler
                 reads the trapping instruction there through MPRV, so it needs R as well as X
  3 (OFF) + 4    TOR [rvtest_entry_point, scratch): L=1 R+X, M-mode code (the test and its trap handlers)
  5 (OFF) + 6    TOR [round_up(__stack_top, 4 KiB), _end): L=1 R+X, the .text.rvmodel code

Data has no rule: with MMWP=0 M-mode reads and writes it by default, also with MML=1. These rules are written with
MML=0 (they are legal encodings then), and MML is set afterwards.

S/U-mode accesses run in the U page: M-mode sets x9 to a continuation label and MRETs into a snippet there; the
snippet ends with a jump to the last 8 bytes of the page, a T-SBI GOTO_MMODE (li a0, 1; ecall), whose return lands
on the first word of the next page, which is M-mode code that jumps to x9.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aigen import X
from dbltrplib import skip_lines

if TYPE_CHECKING:
    from collections.abc import Callable

    from aigen import Expect, TestFile

RET = 0x00008067
NPAGES = 8
TEST_ENTRIES = [0, 1, 7, 8, 9, 10, 11, 12]  # entry used for page Pi
MSECCFG = 0x747
MML, MMWP, RLB = 1, 2, 4
S_OK = "defined(S_SUPPORTED)"
U_OK = "defined(U_SUPPORTED)"
H = "defined(H_SUPPORTED)"
CAUSE = {"r": 5, "w": 7, "x": 1}

# Truth table with MML=1: (L, R, W, X) -> (M-mode permissions, S/U-mode permissions)
TABLE = {
    (0, 0, 0, 0): ("", ""),
    (0, 0, 0, 1): ("", "x"),
    (0, 0, 1, 0): ("rw", "r"),
    (0, 0, 1, 1): ("rw", "rw"),
    (0, 1, 0, 0): ("", "r"),
    (0, 1, 0, 1): ("", "rx"),
    (0, 1, 1, 0): ("", "rw"),
    (0, 1, 1, 1): ("", "rwx"),
    (1, 0, 0, 0): ("", ""),
    (1, 0, 0, 1): ("x", ""),
    (1, 0, 1, 0): ("x", "x"),
    (1, 0, 1, 1): ("rx", "x"),
    (1, 1, 0, 0): ("r", ""),
    (1, 1, 0, 1): ("rx", ""),
    (1, 1, 1, 0): ("rw", ""),
    (1, 1, 1, 1): ("r", "r"),
}
NOMATCH = ("rw", "")  # MML=1, MMWP=0, no matching rule


def lrwx(code: str) -> tuple[int, int, int, int]:
    """'1011' -> (1, 0, 1, 1)."""
    return tuple(int(c) for c in code)  # type: ignore[return-value]


def cfg_byte(code: str, a: int = 3) -> int:
    l, r, w, x = lrwx(code)
    return (l << 7) | (a << 3) | (x << 2) | (w << 1) | r


def cfg_loc(entry: int) -> tuple[X, X]:
    """(pmpcfg CSR number, bit shift) of an entry's byte for RV32 and RV64."""
    return X(0x3A0 + entry // 4, 0x3A0 + 2 * (entry // 8)), X(8 * (entry % 4), 8 * (entry % 8))


class Epmp:
    """One Smepmp test: setup, U page, and access windows."""

    def __init__(self, t: TestFile) -> None:
        self.t = t
        self.upage: list[str] = []
        self.pre: list[tuple[int, str]] = []  # (page, LRWX) rules written before MML is set
        t.extra_data += [
            "  .p2align 12",
            "epmp_pages:",
            f"  .fill {NPAGES * 1024}, 4, {hex(RET)}",
            "  .p2align 3",
            "epmp_rlb: .dword 0",
        ]

    # ------------------------------------------------------------ CSR helpers
    def page(self, reg: str, i: int) -> None:
        t = self.t
        t.emit(f"LA({reg}, epmp_pages)", 2)
        if i:
            t.emit(f"li x5, {i}")
            t.emit("slli x5, x5, 12")
            t.emit(f"add {reg}, {reg}, x5")

    def set_cfg(self, entry: int, byte: int, note: str = "") -> None:
        """Change one entry's pmpcfg byte with a csrc then a csrs (the other entries of the CSR keep their values).
        Clobbers x5 and x8."""
        t = self.t
        csr, sh = cfg_loc(entry)
        for xlen, cond in ((32, "__riscv_xlen == 32"), (64, "__riscv_xlen == 64")):
            with t.only_if(cond):
                c, s = csr.num(xlen), sh.num(xlen)
                t.emit("li x8, 0xff")
                t.emit(f"slli x8, x8, {s}")
                t.emit(f"csrc {hex(c)}, x8  // entry {entry} OFF")
                if byte:
                    t.emit(f"li x8, {byte}")
                    t.emit(f"slli x8, x8, {s}")
                    t.emit(f"csrs {hex(c)}, x8  // entry {entry} = {hex(byte)} {note}")
        self.fence()

    def write_cfg_byte(self, entry: int, byte: int, note: str = "") -> None:
        """One csrw of the entry's pmpcfg register: every other byte as read, this entry's byte = byte.
        Clobbers x5, x8."""
        t = self.t
        csr, sh = cfg_loc(entry)
        for xlen, cond in ((32, "__riscv_xlen == 32"), (64, "__riscv_xlen == 64")):
            with t.only_if(cond):
                c, s = csr.num(xlen), sh.num(xlen)
                t.emit(f"csrr x8, {hex(c)}")
                t.emit("li x5, 0xff")
                t.emit(f"slli x5, x5, {s}")
                t.emit("not x5, x5")
                t.emit("and x8, x8, x5")
                t.emit(f"li x5, {byte}")
                t.emit(f"slli x5, x5, {s}")
                t.emit("or x8, x8, x5")
                t.emit(f"csrw {hex(c)}, x8  // entry {entry} = {hex(byte)} {note}")
        self.fence()

    def read_cfg(self, reg: str, entry: int) -> None:
        """reg = the entry's pmpcfg byte."""
        t = self.t
        csr, sh = cfg_loc(entry)
        for xlen, cond in ((32, "__riscv_xlen == 32"), (64, "__riscv_xlen == 64")):
            with t.only_if(cond):
                t.emit(f"csrr {reg}, {hex(csr.num(xlen))}")
                t.emit(f"srli {reg}, {reg}, {sh.num(xlen)}")
        t.emit(f"andi {reg}, {reg}, 0xff")

    def napot(self, entry: int, page: int) -> None:
        """pmpaddr[entry] = NAPOT 4 KiB at page P[page]. Clobbers x5, x8."""
        t = self.t
        self.page("x8", page)
        t.emit("srli x8, x8, 2")
        t.emit("ori x8, x8, 0x1ff")
        t.emit(f"csrw {hex(0x3B0 + entry)}, x8  // pmpaddr{entry} = NAPOT 4 KiB at P{page}")

    def rule(self, page: int, code: str, note: str = "") -> int:
        """Make the test entry of page `page` a NAPOT rule with LRWX = code; returns the entry."""
        e = TEST_ENTRIES[page]
        self.napot(e, page)
        self.set_cfg(e, cfg_byte(code), f"LRWX={code} {note}".strip())
        return e

    def fence(self) -> None:
        with self.t.only_if(S_OK):
            self.t.emit("sfence.vma x0, x0")

    # ------------------------------------------------------------ setup
    def setup(
        self, body: Callable[[], None], mml: bool = True, keep_rlb: bool = False, require_mml: bool = True
    ) -> None:
        """Probe, give the image its M-mode rules, set MML (unless mml=False), and run body when the hart
        qualifies (entries 1-15 OFF and unlocked, entry 0 unlocked, MML = MMWP = 0, 16 entries, G <= 10, TOR and
        NAPOT). RLB is probed (epmp_rlb = 1 when it can be set) and cleared before body unless keep_rlb. With
        require_mml, body runs only when MML reads 1 after it is set (mseccfg_fields_exist checks that it does);
        with mml=False, MML is left 0 and body sets it."""
        t = self.t
        t.comment("---- Smepmp setup: probes")
        t.emit("li x1, 1  // x1: the hart qualifies")
        t.emit("li x6, 0x01010101")
        with t.rv64_only():
            t.emit("slli x5, x6, 32")
            t.emit("or x6, x6, x5")
        t.emit("slli x6, x6, 7  // L bit of every entry")
        t.emit("csrr x7, pmpcfg0")
        t.emit("and x5, x7, x6  // locked entries")
        t.emit("srli x7, x7, 8  // entries above 0")
        t.emit("or x7, x7, x5")
        with t.rv32_only():
            t.emit("csrr x5, pmpcfg1")
            t.emit("or x7, x7, x5")
            t.emit("csrr x5, pmpcfg3")
            t.emit("or x7, x7, x5")
        t.emit("csrr x5, pmpcfg2")
        t.emit("or x7, x7, x5")
        t.emit("seqz x7, x7")
        t.emit("and x1, x1, x7  // entries 1-15 OFF, none locked")
        t.emit(f"csrr x7, {hex(MSECCFG)}")
        t.emit(f"andi x7, x7, {MML | MMWP}")
        t.emit("seqz x7, x7")
        t.emit("and x1, x1, x7  // MML = MMWP = 0")
        t.emit("li x7, -1")
        t.emit("csrw pmpaddr15, x7")
        t.emit("csrr x7, pmpaddr15")
        t.emit("csrw pmpaddr15, x0")
        t.emit("snez x5, x7")
        t.emit("and x1, x1, x5  // entry 15 implemented")
        t.emit("addi x5, x7, -1")
        t.emit("xor x5, x5, x7")
        t.emit("srli x5, x5, 1  // 2^G - 1")
        t.emit("srli x5, x5, 10")
        t.emit("seqz x5, x5")
        t.emit("and x1, x1, x5  // G <= 10: 4 KiB regions")
        for a, name in ((1, "TOR"), (3, "NAPOT")):
            csr, sh = cfg_loc(15)
            for xlen, cond in ((32, "__riscv_xlen == 32"), (64, "__riscv_xlen == 64")):
                with t.only_if(cond):
                    c, s = csr.num(xlen), sh.num(xlen)
                    t.emit(f"li x7, {a << 3}")
                    t.emit(f"slli x7, x7, {s}")
                    t.emit(f"csrs {hex(c)}, x7")
                    t.emit(f"csrr x5, {hex(c)}")
                    t.emit(f"csrc {hex(c)}, x7")
                    t.emit(f"srli x5, x5, {s + 3}")
            t.emit("andi x5, x5, 3")
            t.emit(f"addi x5, x5, {-a}")
            t.emit("seqz x5, x5")
            t.emit(f"and x1, x1, x5  // {name} supported")

        def qualified() -> None:
            t.comment("RLB: probe while no entry is locked")
            t.emit(f"csrsi {hex(MSECCFG)}, {RLB}")
            t.emit(f"csrr x7, {hex(MSECCFG)}")
            t.emit("srli x7, x7, 2")
            t.emit("andi x7, x7, 1")
            t.emit("LA(x8, epmp_rlb)", 2)
            t.emit("SREG x7, 0(x8)")
            t.comment("M-mode rules for the image (entries 2-6), written with MML=0")
            t.emit("LA(x8, epmp_upage)", 2)
            t.emit("srli x8, x8, 2")
            t.emit("ori x8, x8, 0x1ff")
            t.emit("csrw pmpaddr2, x8  // U page, NAPOT 4 KiB")
            t.emit("LA(x8, rvtest_entry_point)", 2)
            t.emit("srli x8, x8, 2")
            t.emit("csrw pmpaddr3, x8")
            t.emit("LA(x8, scratch)", 2)
            t.emit("srli x8, x8, 2")
            t.emit("csrw pmpaddr4, x8  // code: [rvtest_entry_point, scratch)")
            t.emit("LA(x8, __stack_top)", 2)
            t.emit("li x5, 0xfff")
            t.emit("add x8, x8, x5")
            t.emit("not x5, x5")
            t.emit("and x8, x8, x5")
            t.emit("srli x8, x8, 2")
            t.emit("csrw pmpaddr5, x8")
            t.emit("LA(x8, _end)", 2)
            t.emit("srli x8, x8, 2")
            t.emit("csrw pmpaddr6, x8  // .text.rvmodel: [round_up(__stack_top), _end)")
            upage = cfg_byte("0101")
            code = cfg_byte("1101", a=1)
            with t.rv64_only():
                t.emit(f"LI(x8, {hex((code << 48) | (code << 32) | (upage << 16))})", 2)
                t.emit("csrw pmpcfg0, x8  // entries 0, 1, 3, 5, 7 OFF; 2 U page; 4 and 6 locked M code")
            with t.rv32_only():
                t.emit(f"LI(x8, {hex((code << 16) | code)})", 2)
                t.emit("csrw pmpcfg1, x8  // entries 4 and 6 locked M code")
                t.emit(f"LI(x8, {hex(upage << 16)})", 2)
                t.emit("csrw pmpcfg0, x8  // entries 0, 1, 3 OFF; 2 U page")
            self.fence()
            for page, code in self.pre:
                t.comment(f"rule written before MML: P{page} LRWX={code}")
                self.rule(page, code)
            if not keep_rlb:
                t.emit(f"csrci {hex(MSECCFG)}, {RLB}  // RLB = 0")
            if not mml:
                body()
                return
            t.comment("mseccfg.MML = 1 (sticky until reset)")
            t.emit(f"csrsi {hex(MSECCFG)}, {MML}")
            self.fence()
            if not require_mml:
                body()
                return
            t.emit(f"csrr x1, {hex(MSECCFG)}")
            t.emit("andi x1, x1, 1")
            either(t, "x1", body, lambda: t.comment("MML reads 0 (see mseccfg_fields_exist): nothing tested"))

        either(t, "x1", qualified, lambda: t.comment("hart does not qualify: nothing tested"))

    def rlb(self, reg: str) -> None:
        """reg = 1 when RLB could be set before any rule was locked."""
        self.t.emit(f"LA({reg}, epmp_rlb)", 2)
        self.t.emit(f"LREG {reg}, 0({reg})")

    def finish(self) -> None:
        """Append the U page (call last)."""
        t = self.t
        end = t.label("upage_end")
        t.emit(f"j {end}")
        t.code += [
            "  .option push",
            "  .option norvc",
            "  .option norelax",
            "  .p2align 12",
            "epmp_upage:",
            *self.upage,
            "  .skip 4088 - (. - epmp_upage)",
            "epmp_uexit:",
            "  li a0, TSBI_GOTO_MMODE",
            "  ecall  // last word of the U page; GOTO_MMODE returns to the next word, M-mode code",
            "epmp_uafter:",
            "  auipc x0, 0",
            "  jr x9",
            "  .option pop",
        ]
        t.emit(f"{end}:", 0)
        assert sum(1 for ln in self.upage if not ln.endswith(":")) * 4 < 4000, "U page overflow"

    # ------------------------------------------------------------ accesses
    def access(self, mode: str, kind: str, page: int, ok: bool, desc: str) -> None:
        """One load (r), store (w) or fetch (x) of page P[page] in `mode` (M, S, U) inside a trap window. ok: the
        access is permitted; otherwise an access fault with xtval 0 or the address (and xepc the target for a
        fetch). Stores write the page's own `ret` word."""
        t = self.t
        self.page("x6", page)
        t.li("x7", RET)
        line = {"r": "lw x8, 0(x6)", "w": "sw x7, 0(x6)", "x": "jalr ra, 0(x6)"}[kind]
        expect: Expect = "ok" if ok else CAUSE[kind]
        what = {"r": "load", "w": "store", "x": "fetch"}[kind]
        full = f"{mode}-mode {what} of P{page} ({desc})"
        if mode == "M":
            lab = t.label("m")
            t.allow(1)
            t.emit(f"{lab}:", 0)
            t.emit(line)
            t.outcome(expect, lab, full, epc=kind != "x", origin="M")
        else:
            snip, cont = t.label(f"u{mode}"), t.label("cont")
            t.allow(1)
            t.emit(f"LA(x9, {cont})", 2)
            t.emit(f"LA(x8, {snip})", 2)
            t.emit("csrw mepc, x8")
            t.li("x8", 0x1800)
            t.emit("csrc mstatus, x8  // MPP = U")
            if mode == "S":
                t.li("x8", 0x800)
                t.emit("csrs mstatus, x8  // MPP = S")
            with t.only_if(H):
                with t.rv64_only():
                    t.emit("li x8, 1")
                    t.emit("slli x8, x8, 39")
                    t.emit("csrc mstatus, x8  // MPV = 0")
                with t.rv32_only():
                    t.emit("li x8, 0x80")
                    t.emit("csrc 0x310, x8  // mstatush.MPV = 0")
            t.emit("mret  // into the U page")
            t.emit(f"{cont}:", 0)
            self.upage += [f"{snip}:", f"  {line}", "  j epmp_uexit"]
            t.outcome(expect, snip, full, epc=kind != "x", origin=mode)
        if not ok:
            self.addr_checks(kind, full)

    def addr_checks(self, kind: str, desc: str) -> None:
        """After a fault: xtval is 0 or x6, and for a fetch xepc is x6."""
        t = self.t
        lab = t.label("tv")
        t.emit(f"{lab}:", 0)
        t.emit("AI_LOG(x15, TRAPLOG_TVAL)", 10)
        t.emit("xor x14, x15, x6")
        t.emit("seqz x14, x14")
        t.emit("seqz x15, x15")
        t.emit("or x15, x15, x14")
        t.check("x15", 1, lab, f"{desc}: xtval is 0 or the address")
        if kind == "x":
            t.emit("AI_LOG(x15, TRAPLOG_EPC)", 10)
            t.emit("sub x15, x15, x6")
            t.check("x15", 0, lab, f"{desc}: xepc is the fetch target (difference)")

    def matrix(self, page: int, perms: tuple[str, str], desc: str, modes: tuple[str, ...] = ("M", "S", "U")) -> None:
        """Load, store and fetch of P[page] from each mode, permitted exactly when the kind is in perms (M-mode
        permissions, S/U-mode permissions). S and U run only when present."""
        for mode in modes:
            p = perms[0] if mode == "M" else perms[1]
            cond = {"M": None, "S": S_OK, "U": U_OK}[mode]
            if cond:
                with self.t.only_if(cond):
                    for k in "rwx":
                        self.access(mode, k, page, k in p, desc)
            else:
                for k in "rwx":
                    self.access(mode, k, page, k in p, desc)


def either(t: TestFile, reg: str, if_set: Callable[[], object], if_clear: Callable[[], object]) -> None:
    """TestFile.either, except that either branch may hold table entries under extra #if conditions (mode guards
    inside a run-time branch): the skips are emitted per condition set."""
    clear, done = t.label("clear"), t.label("done")
    t.emit(f"beqz {reg}, {clear}")
    a = len(t.table)
    if_set()
    b = len(t.table)
    hole = len(t.code)
    t.code.append("")
    t.emit(f"j {done}")
    t.emit(f"{clear}:", 0)
    t.code += skip_lines(t, a, b)
    if_clear()
    t.code[hole] = "\n".join(skip_lines(t, b, len(t.table)))
    t.emit(f"{done}:", 0)
