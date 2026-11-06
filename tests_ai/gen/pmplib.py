# SPDX-License-Identifier: Apache-2.0
"""PMP rule-derived tests (tests_ai/PMP), generated through gen_Sm.py.

Layout used by every test that programs PMP:
- pmp_buf: four 4 KiB pages P0-P3 (16 KiB aligned), filled with `ret` instructions so any word can be fetched.
- The framework's entry 0 (U-mode access to everything, TOR or NAPOT RWX) is saved and copied to entry 7, which
  becomes the lowest-priority background; entry 6 is OFF with pmpaddr6 = 0 (the TOR base of entry 7). Entries 0-5
  are the entries under test. Everything is restored (and SFENCE.VMA executed on S-mode harts) at the end.
- The PMP grain is probed on entry 7 (pmpaddr7 read back with A = OFF after writing all ones): z = 2^G - 1. Tests
  that need page-sized regions run when entry 7 is implemented and G <= 10 (a 4 KiB region is legal); sub-page
  cases need G = 0 (z = 0). Expected outcomes come from a reference model of the matching rules (model()).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from typing import TYPE_CHECKING

import smlib as L
from aigen import TestFile, X
from smlib import MPP, MPRV, MXR, NO_U, SUM, S, U, describe, guard, mut, new

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from aigen import Expect


PAGE = 4096
RET = 0x00008067
A = {"OFF": 0, "TOR": 1, "NA4": 2, "NAPOT": 3}
CAUSE = {"r": 5, "w": 7, "x": 1}
REQ_U = ["I", "Sm", "U"]
CBO = {"inval": 0, "clean": 1, "flush": 2, "zero": 4}

MUTANTS = {
    "pmp_highest_wins": "the highest-numbered matching PMP entry decides",
    "pmp_partial_ok": "an entry that matches only some bytes of an access decides it by its permissions",
    "pmp_m_enforced": "R/W/X of an unlocked entry also restrict M-mode",
    "pmp_lock_ignored": "L = 1 does not restrict M-mode",
    "pmp_tor_inclusive": "a TOR entry also matches its top address",
    "pmp_napot_half": "a NAPOT entry covers half its encoded size",
    "pmp_nomatch_allows": "S/U accesses that match no entry succeed",
    "pmp_x_from_r": "R permission also allows execution",
    "pmp_w_without_r": "R = 0, W = 1 is stored in pmpcfg as written",
    "pmp_off_matches": "an OFF entry still matches its address",
    "pmp_mprv_ignored": "MPRV = 1 does not apply PMP to M-mode loads and stores",
    "pmp_mprv_fetch": "MPRV = 1 also applies to instruction fetch",
    "pmp_mxr_bypass": "MXR = 1 lets S-mode load from an execute-only PMP region",
    "pmp_napot_mask_wrong": "NAPOT pmpaddr reads with bits G-1:0 set (not G-2:0)",
    "pmp_tor_mask_wrong": "TOR/OFF pmpaddr reads with the grain bits as stored",
    "pmp_retention_lost": "pmpaddr[G-1] is lost when A changes from NAPOT to OFF",
    "pmp_lock_addr_writable": "pmpaddr of a locked entry is writable",
    "pmp_tor_base_writable": "pmpaddr(i-1) stays writable when entry i is locked TOR",
    "pmp_csr_s_access": "S-mode can read pmpcfg0",
    "pmp_mis_tval_start": "a misaligned access fault may only report its start address (never the faulting part)",
    "pmp_fetch_tval_start": "a fetch fault on an instruction's second half reports the instruction address",
    "pmp_rlb_sticky_ignored": "RLB can be set after an entry is locked",
    "pmp_mmwp_ignored": "MMWP = 1 does not deny M-mode accesses that match no entry",
    "pmp_cbm_noperm_ok": "a cache-block management instruction succeeds on a region without permissions",
    "pmp_store_lands": "a store that raises a PMP access fault still writes memory",
    "pmp_layout_shift": "pmp12cfg and pmp13cfg are swapped in the pmpcfg layout",
}


@dataclass
class E:
    """A PMP entry under test. lo/hi are byte offsets from pmp_buf (hi exclusive). TOR entries take lo from the
    preceding entry's address register (which must be OFF); base0 = TOR entry 0 (base 0); top_all = the top is
    the end of the address space."""

    a: str
    lo: int = 0
    hi: int = 0
    perm: str = ""
    lock: bool = False
    base0: bool = False
    top_all: bool = False

    def cfg(self) -> int:
        p = (("x" in self.perm) << 2) | (("w" in self.perm) << 1) | ("r" in self.perm)
        return (self.lock << 7) | (A[self.a] << 3) | p


BIG = 1 << 40


def model(entries: Sequence[E | None], mode: str, off: int, size: int, kind: str, bg: bool = True) -> str | int:
    """Expected outcome ("ok" or the access-fault cause) of an access of `size` bytes at pmp_buf+off."""
    m = mut()
    order = list(enumerate(entries))
    if m == "pmp_highest_wins":
        order = order[::-1]
    for _, e in order:
        if e is None or (e.a == "OFF" and m != "pmp_off_matches"):
            continue
        if e.a == "OFF" and e.hi == 0:
            continue
        lo = -BIG if e.base0 else e.lo
        hi = BIG if e.top_all else e.hi
        if m == "pmp_tor_inclusive" and e.a == "TOR":
            hi += 4
        if m == "pmp_napot_half" and e.a == "NAPOT":
            hi = lo + (hi - lo) // 2
        if not (off < hi and off + size > lo):
            continue
        full = lo <= off and off + size <= hi
        if not full and m != "pmp_partial_ok":
            return CAUSE[kind]
        locked = e.lock and m != "pmp_lock_ignored"
        if mode == "M" and not locked and m != "pmp_m_enforced":
            return "ok"
        perm = e.perm + ("x" if m == "pmp_x_from_r" and "r" in e.perm else "")
        return "ok" if kind in perm else CAUSE[kind]
    if bg or mode == "M" or m == "pmp_nomatch_allows":
        return "ok"
    return CAUSE[kind]


# ---------------------------------------------------------------- data and setup
def buffer(t: TestFile, overrides: dict[int, int] | None = None) -> None:
    """pmp_buf: 4 pages of `ret` words (16 KiB aligned), with optional word overrides {offset: value}."""
    ov = overrides or {}
    out = [".p2align 14", "pmp_buf:"]
    pos = 0
    for off in sorted(ov):
        if off > pos:
            out.append(f"  .rept {(off - pos) // 4}\n  .word {hex(RET)}\n  .endr")
        out.append(f"  .word {hex(ov[off])}")
        pos = off + 4
    if pos < 4 * PAGE:
        out.append(f"  .rept {(4 * PAGE - pos) // 4}\n  .word {hex(RET)}\n  .endr")
    out += [
        ".p2align 3",
        "pmp_save: .fill 10, 8, 0",
        "pmp_ok: .dword 0",
        "pmp_z: .dword 0",
        "pmp_tor: .dword 0",
        "pmp_csr: .dword 0",
    ]
    t.extra_data += out


def sfence(t: TestFile) -> None:
    with t.only_if(S):
        t.emit("sfence.vma x0, x0")


def save(t: TestFile) -> None:
    t.la("x8", "pmp_save")
    t.emit("csrr x7, pmpcfg0")
    t.emit("SREG x7, 0(x8)")
    with t.rv32_only():
        t.emit("csrr x7, pmpcfg1")
        t.emit("SREG x7, 8(x8)")
    for i in range(8):
        t.emit(f"csrr x7, pmpaddr{i}")
        t.emit(f"SREG x7, {16 + 8 * i}(x8)")


def restore(t: TestFile) -> None:
    t.la("x8", "pmp_save")
    for i in range(8):
        t.emit(f"LREG x7, {16 + 8 * i}(x8)")
        t.emit(f"csrw pmpaddr{i}, x7")
    t.emit("LREG x7, 0(x8)")
    t.emit("csrw pmpcfg0, x7")
    with t.rv32_only():
        t.emit("LREG x7, 8(x8)")
        t.emit("csrw pmpcfg1, x7")
    sfence(t)


def cfgs_off(t: TestFile) -> None:
    """All of entries 0-7 OFF (locked entries keep their configuration)."""
    t.emit("csrw pmpcfg0, x0")
    with t.rv32_only():
        t.emit("csrw pmpcfg1, x0")


def probe(t: TestFile, need_u: bool = True) -> None:
    """Save the PMP state, then probe entry 7: pmp_ok = entries 1-7 OFF and no entry locked, entry 7 implemented, G <= 10 and U-mode
    exists; pmp_z = 2^G - 1; pmp_tor = TOR selectable (on entry 5). Leaves entries 5 and 7 OFF with address 0.
    A hart without PMP entries may not implement the PMP CSRs at all: the first access is in a trap window, and
    pmp_csr = 1 only if it did not trap."""
    skip = t.label("busy")
    t.la("x8", "rvtest_trap_count")
    t.emit("LREG x9, 0(x8)")
    t.window("M", ["csrrs x7, pmpcfg0, x0"], ["ok", 2], "pmpcfg0 probe", [0, L.enc_csr(0x3A0, 2, 7, 0)])
    t.la("x8", "rvtest_trap_count")
    t.emit("LREG x7, 0(x8)")
    t.emit("sub x7, x7, x9")
    t.emit("seqz x7, x7")
    t.la("x8", "pmp_csr")
    t.emit("SREG x7, 0(x8)")
    t.emit(f"beqz x7, {skip}  // no PMP CSRs")
    save(t)
    # No table loads after the first branch: a skipped path must not shift the table pointer.
    t.emit("li x6, 0x01010101")
    with t.rv64_only():
        t.emit("slli x5, x6, 32")
        t.emit("or x6, x6, x5")
    t.emit("slli x6, x6, 7  // L bit of every entry")
    t.emit("csrr x7, pmpcfg0")
    t.emit("and x5, x7, x6  // locked entries")
    t.emit("srli x7, x7, 8  // entries above 0 (the framework uses only entry 0)")
    t.emit("or x7, x7, x5")
    with t.rv32_only():
        t.emit("csrr x5, pmpcfg1")
        t.emit("or x7, x7, x5")
    t.emit(f"bnez x7, {skip}  // entries 1-7 must be OFF, and no entry locked")
    t.emit("li x6, -1")
    t.emit("csrw pmpaddr7, x6")
    t.emit("csrr x6, pmpaddr7")
    t.emit("csrw pmpaddr7, x0")
    t.emit("addi x7, x6, -1")
    t.emit("xor x7, x7, x6")
    t.emit("srli x7, x7, 1  // z = 2^G - 1")
    t.la("x8", "pmp_z")
    t.emit("SREG x7, 0(x8)")
    t.emit("srli x7, x7, 10")
    t.emit("seqz x7, x7  // G <= 10")
    t.emit("snez x6, x6  // entry 7 implemented")
    t.emit("and x7, x7, x6")
    if need_u:
        with t.only_if(NO_U):
            t.emit("li x7, 0")
    t.la("x8", "pmp_ok")
    t.emit("SREG x7, 0(x8)")
    # TOR selectable? (entry 5, pmpaddr4 = pmpaddr5 = 0, no permissions: matches nothing)
    t.emit("csrw pmpaddr5, x0")
    with t.rv64_only():
        t.emit("csrr x9, pmpaddr4")
        t.emit("csrw pmpaddr4, x0")
        t.emit("li x6, 8")
        t.emit("slli x6, x6, 40")
        t.emit("csrs pmpcfg0, x6")
        t.emit("csrr x7, pmpcfg0")
        t.emit("csrc pmpcfg0, x6")
        t.emit("srli x7, x7, 43")
    with t.rv32_only():
        t.emit("csrr x9, pmpaddr4")
        t.emit("csrw pmpaddr4, x0")
        t.emit("li x6, 0x800")
        t.emit("csrs pmpcfg1, x6")
        t.emit("csrr x7, pmpcfg1")
        t.emit("csrc pmpcfg1, x6")
        t.emit("srli x7, x7, 11")
    t.emit("csrw pmpaddr4, x9")
    t.emit("andi x7, x7, 3")
    t.emit("addi x7, x7, -1")
    t.emit("seqz x7, x7")
    t.la("x8", "pmp_tor")
    t.emit("SREG x7, 0(x8)")
    t.emit(f"{skip}:", 0)


def flag(t: TestFile, reg: str, sym: str) -> None:
    t.la(reg, sym)
    t.emit(f"LREG {reg}, 0({reg})")


def program(t: TestFile, entries: Sequence[E | None], bg: bool = True) -> None:
    """Program entries 0..len-1 (and the background entry 7 when bg). Runs in M-mode."""
    assert len(entries) <= (6 if bg else 8)
    addr: dict[int, tuple] = {}
    for i, e in enumerate(entries):
        if e is None:
            continue
        if e.a == "TOR" and not e.base0:
            prev = entries[i - 1]
            assert i > 0 and (prev is None or prev.a == "OFF"), "TOR base must be an OFF entry"
            addr[i - 1] = ("tor", e.lo)
        if e.a == "TOR":
            addr[i] = ("all",) if e.top_all else ("tor", e.hi)
        elif e.a == "NAPOT":
            size = e.hi - e.lo
            assert size >= 8 and size & (size - 1) == 0 and e.lo % size == 0
            addr[i] = ("napot", e.lo, size)
        elif e.a == "NA4":
            addr[i] = ("tor", e.lo)
        elif e.hi:
            addr.setdefault(i, ("napot", e.lo, e.hi - e.lo))
    cfgs_off(t)
    for i in range(8):
        v = addr.get(i)
        if i == 7 and bg:
            t.la("x8", "pmp_save")
            t.emit("LREG x7, 16(x8)  // the framework's pmpaddr0")
            t.emit("csrw pmpaddr7, x7")
            continue
        if v is None:
            t.emit(f"csrw pmpaddr{i}, x0")
        elif v[0] == "all":
            t.emit("li x7, -1")
            t.emit(f"csrw pmpaddr{i}, x7")
        else:
            t.la("x7", f"pmp_buf+{v[1]}")
            t.emit("srli x7, x7, 2")
            if v[0] == "napot":
                t.emit(f"addi x7, x7, {v[2] // 8 - 1}")
            t.emit(f"csrw pmpaddr{i}, x7")
    static = sum((e.cfg() if e else 0) << (8 * i) for i, e in enumerate(entries))
    with t.rv64_only():
        t.load("x6", X(0, static))
        if bg:
            t.la("x8", "pmp_save")
            t.emit("LREG x7, 0(x8)")
            t.emit("andi x7, x7, 0xFF")
            t.emit("slli x7, x7, 56")
            t.emit("or x6, x6, x7")
        t.emit("csrw pmpcfg0, x6")
    with t.rv32_only():
        t.load("x6", X(static & 0xFFFFFFFF, 0))
        t.emit("csrw pmpcfg0, x6")
        t.load("x6", X(static >> 32, 0))
        if bg:
            t.la("x8", "pmp_save")
            t.emit("LREG x7, 0(x8)")
            t.emit("andi x7, x7, 0xFF")
            t.emit("slli x7, x7, 24")
            t.emit("or x6, x6, x7")
        t.emit("csrw pmpcfg1, x6")
    sfence(t)


def access(t: TestFile, mode: str, kind: str, off: int, exp: Expect, desc: str, size: int = 4) -> None:
    """One access of `kind` (r: lw, w: sw, x: jalr to a `ret`) at pmp_buf+off in `mode`; exp from model()."""
    sym = f"pmp_buf+{off}"
    tval = [0, sym]
    if kind == "w":
        t.li("x7", RET)
    t.la("x8", sym)
    if kind == "x":
        lab = t.label("fetch")
        t.allow(1)
        if mode != t.cur:
            t.enter(mode)
        t.emit(f"{lab}:", 0)
        t.emit("jalr x1, 0(x8)")
        if mode != t.cur:
            t.leave()
        fetch_outcome(t, exp, lab, sym, f"{desc}: fetch at P+{off:#x} in {mode}-mode", tval, mode)
        return
    insn = {"r": {4: "lw x7, 0(x8)", 8: "ld x7, 0(x8)"}, "w": {4: "sw x7, 0(x8)", 8: "sd x7, 0(x8)"}}[kind][size]
    L.win(t, mode, [insn], exp, f"{desc}: {insn.split()[0]} at P+{off:#x}", tval)


def fetch_outcome(t: TestFile, exp: Expect, lab: str, target: str, desc: str, tval: Expect | None, mode: str) -> None:
    """Outcome of a jump: on an instruction access fault, xepc must be the target (not the jump)."""
    t.outcome(exp, lab, desc, tval, epc=False, origin=mode)
    if exp != "ok":
        L.log_word(t, "x15", "TRAPLOG_EPC")
        t.check("x15", target, lab, f"{desc}: xepc is the fetch target")


def sweep(
    t: TestFile,
    entries: Sequence[E | None],
    points: list[tuple[int, str]],
    modes: tuple[str, ...] = ("M", "S", "U"),
    desc: str = "",
    bg: bool = True,
) -> None:
    """For each (offset, kinds) point and mode: an access whose expected outcome comes from model()."""
    for mode in modes:

        def body(mode: str = mode) -> None:
            for off, kinds in points:
                for k in kinds:
                    access(t, mode, k, off, model(entries, mode, off, 4, k, bg), desc)

        guard(t, L.MODE_COND[mode], body)


def pmp_test(
    t: TestFile, body: Callable[[], object], need: str = "pmp_ok", extra: list[str] | None = None, need_u: bool = True
) -> None:
    """Probe, run body() when the probe allows (and every flag in extra), and restore."""
    probe(t, need_u)
    flag(t, "x9", need)
    for f in extra or []:
        flag(t, "x6", f)
        t.emit("and x9, x9, x6")

    def run() -> None:
        body()
        restore(t)

    L.either(t, "x9", run, lambda: restore_if_csrs(t))


def restore_if_csrs(t: TestFile) -> None:
    """restore() on harts whose PMP CSRs exist (the probe saved them)."""
    skip = t.label("nopmp")
    flag(t, "x9", "pmp_csr")
    t.emit(f"beqz x9, {skip}")
    restore(t)
    t.emit(f"{skip}:", 0)


def zflag(t: TestFile, reg: str, max_g: int = 0) -> None:
    """reg = 1 if G <= max_g."""
    flag(t, reg, "pmp_z")
    t.emit(f"srli {reg}, {reg}, {max_g}")
    t.emit(f"seqz {reg}, {reg}")


def cbo(op: str, rs1: int = 8) -> int:
    return (CBO[op] << 20) | (rs1 << 15) | (2 << 12) | 0x0F


def set_cfg_byte(t: TestFile, entry: int, value: int | None) -> None:
    """Clear entry's pmpcfg byte, then set it to value (if not None)."""
    with t.rv64_only():
        t.load("x5", X(0, 0xFF << (8 * entry)))
        t.emit("csrc pmpcfg0, x5")
        if value:
            t.load("x5", X(0, value << (8 * entry)))
            t.emit("csrs pmpcfg0, x5")
    with t.rv32_only():
        reg = f"pmpcfg{entry // 4}"
        t.load("x5", X(0xFF << (8 * (entry % 4)), 0))
        t.emit(f"csrc {reg}, x5")
        if value:
            t.load("x5", X(value << (8 * (entry % 4)), 0))
            t.emit(f"csrs {reg}, x5")


def read_cfg_byte(t: TestFile, reg: str, entry: int) -> None:
    with t.rv64_only():
        t.emit(f"csrr {reg}, pmpcfg0")
        t.emit(f"srli {reg}, {reg}, {8 * entry}")
    with t.rv32_only():
        t.emit(f"csrr {reg}, pmpcfg{entry // 4}")
        t.emit(f"srli {reg}, {reg}, {8 * (entry % 4)}")
    t.emit(f"andi {reg}, {reg}, 0xFF")


# ---------------------------------------------------------------- tests
CTX = (
    "Entries 0-5 are programmed by the test; entry 7 holds a copy of the framework's RWX background entry (lowest "
    "priority), so addresses outside the regions under test stay accessible to S and U. Regions are pages of a "
    "16 KiB-aligned buffer P (P0-P3 = P+0x0000..P+0x3fff) filled with `ret`, so fetches are jalr to a ret. The "
    "test runs when PMP entry 7 is implemented, U-mode exists and the grain G <= 10. Faults have xtval 0 or the "
    "address; a fetch fault has xepc = the target."
)
NOBG = (
    "entry 7 holds a copy of the framework's RWX background entry (lowest priority), so addresses outside the "
    "regions under test stay accessible to S and U"
)


def gen(suite: str) -> list[TestFile]:
    tests: list[TestFile] = []

    def nt(
        rule: str, req: list[str] | None = None, rv64: bool = False, overrides: dict[int, int] | None = None
    ) -> TestFile:
        t = new(suite, rule, req or REQ_U, rv64=rv64, pool=["x6", "x7", "x8", "x9"])
        buffer(t, overrides)
        return t

    # ---- pmp_csr_mode ----
    t = new(suite, "pmp_csr_mode")
    describe(
        t,
        context="A hart with no PMP entries may leave the PMP CSRs unimplemented, so an M-mode read may trap.",
        plan="1. In S and U: every CSR instruction form on pmpcfg0 and pmpaddr0 raises illegal "
        "instruction.\n2. In M-mode a read does not trap, or (no PMP) raises illegal instruction.",
    )
    t.li("x6", 0)
    for num, name in ((0x3A0, "pmpcfg0"), (0x3B0, "pmpaddr0")):
        t.window(
            "M",
            [f"csrrs x7, {hex(num)}, x0  // {name}"],
            ["ok", 2],
            f"read of {name} (absent without PMP)",
            [0, L.enc_csr(num, 2, 7, 0)],
        )
        for mode in ("S", "U"):

            def m(mode: str = mode, num: int = num, name: str = name) -> None:
                for f in L.FORMS:
                    exp = "ok" if (mut() == "pmp_csr_s_access" and mode == "S" and f in L.READ_FORMS) else "illegal"
                    L.csr_window(t, mode, num, name, f, exp, "below M")

            guard(t, L.MODE_COND[mode], m)
    tests.append(t)

    # ---- pmp_cfg_rv64_illegal ----
    t = new(suite, "pmp_cfg_rv64_illegal", rv64=True)
    describe(
        t,
        context="RV64 only.",
        plan="1. Reading or writing pmpcfg1, pmpcfg3, pmpcfg5 and pmpcfg15 raises illegal instruction in M-mode.",
    )
    t.li("x6", 0)
    for n in (1, 3, 5, 15):
        for f in (L.FORMS[0], L.FORMS[1]):
            L.csr_window(t, "M", 0x3A0 + n, f"pmpcfg{n}", f, "illegal", "RV64")
    tests.append(t)

    # ---- address register WARL behavior ----
    addr_ctx = (
        "Entry 7 is used with no permissions (it is below the framework's entry 0, so nothing changes for "
        "S and U). With A = OFF, writing all ones reads back r, whose trailing zeros are the grain G "
        "(z = 2^G - 1 = (r ^ (r - 1)) >> 1). Checks are branch-free over z. The test runs when entry 7 is "
        "implemented (and free), U-mode exists and G <= 10."
    )

    def addr_body(t: TestFile, which: str) -> None:
        t.emit("li x6, -1")
        t.emit("csrw pmpaddr7, x6")
        t.emit("csrr x9, pmpaddr7  // r")
        t.emit("addi x8, x9, -1")
        t.emit("xor x8, x8, x9")
        t.emit("srli x8, x8, 1  // z = 2^G - 1")
        lab = t.label(which)
        t.emit(f"{lab}:", 0)
        if which == "napot":
            set_cfg_byte(t, 7, 0x18)
            t.emit("li x6, -1")
            t.emit("csrw pmpaddr7, x6")
            t.emit("csrr x7, pmpaddr7")
            t.emit("or x6, x9, x8  // r | z: bit G-1 as written (1), bits G-2:0 forced to 1")
            t.emit("xor x7, x7, x6")
            t.check("x7", 0, lab, "NAPOT, all ones written: pmpaddr reads r | z")
            t.emit("addi x6, x8, 1")
            t.emit("srli x6, x6, 1  // 2^(G-1), or 0 when G = 0")
            t.emit("not x6, x6")
            t.emit("csrw pmpaddr7, x6  // all ones except bit G-1")
            t.emit("csrr x7, pmpaddr7")
            t.emit("srli x6, x8, 1")
            if mut() == "pmp_napot_mask_wrong":
                t.emit("mv x6, x8")
            t.emit("or x6, x6, x9  // r | (z >> 1)")
            t.emit("xor x7, x7, x6")
            t.check("x7", 0, lab, "NAPOT, bit G-1 written 0: pmpaddr reads r | (z >> 1) (bits G-2:0 read as ones)")
        elif which == "tor":
            for a, nm in ((0x08, "TOR"), (None, "OFF")):
                set_cfg_byte(t, 7, a)
                t.emit("csrr x7, pmpaddr7")
                if mut() == "pmp_tor_mask_wrong":
                    t.emit("or x7, x7, x8")
                t.emit("and x7, x7, x8")
                t.check("x7", 0, lab, f"{nm}: pmpaddr bits G-1:0 read as zeros")
        elif which == "retention":

            def leg(mid: int | None, name: str) -> None:
                for g1, note in ((0, "0"), (1, "1")):
                    set_cfg_byte(t, 7, 0x18)
                    t.emit("li x6, -1")
                    if not g1:
                        t.emit("addi x5, x8, 1")
                        t.emit("srli x5, x5, 1  // 2^(G-1), or 0 when G = 0")
                        t.emit("not x5, x5")
                        t.emit("and x6, x6, x5")
                    t.emit("csrw pmpaddr7, x6  // written with A = NAPOT")
                    set_cfg_byte(t, 7, mid)
                    set_cfg_byte(t, 7, 0x18)
                    t.emit("csrr x7, pmpaddr7")
                    if g1 and mut() != "pmp_retention_lost":
                        t.emit("or x5, x9, x8  // r | z")
                    else:
                        t.emit("srli x5, x8, 1")
                        t.emit("or x5, x5, x9  // r | (z >> 1)")
                    t.emit("xor x7, x7, x5")
                    t.check("x7", 0, lab, f"NAPOT -> {name} -> NAPOT keeps pmpaddr[G-1] = {note}")

            leg(None, "OFF")
            flag(t, "x6", "pmp_tor")
            L.either(t, "x6", lambda: leg(0x08, "TOR"), lambda: None)
        elif which == "na4":
            set_cfg_byte(t, 7, 0x10)
            read_cfg_byte(t, "x7", 7)
            t.emit("srli x7, x7, 3")
            t.emit("andi x7, x7, 3")
            t.emit("addi x7, x7, -2")
            t.emit("snez x7, x7  // A != NA4")
            t.emit("seqz x6, x8  // G = 0")
            t.emit("or x7, x7, x6")
            t.check_bool("x7", lab, "with G >= 1, A = NA4 is not selectable")
        elif which == "grain":
            t.emit("li x6, -1")
            t.emit("csrw pmpaddr5, x6")
            t.emit("csrr x7, pmpaddr5")
            t.emit("csrw pmpaddr5, x0")
            t.emit("addi x6, x7, -1")
            t.emit("xor x6, x6, x7")
            t.emit("srli x6, x6, 1")
            t.emit("xor x6, x6, x8")
            t.check("x6", 0, lab, "entries 5 and 7 have the same grain")
        elif which == "encoding":
            with t.rv64_only():
                t.emit("srli x7, x9, 54")
                t.check("x7", 0, lab, "RV64 pmpaddr bits 63:54 read 0 (it holds address bits 55:2)")
            t.emit("csrw pmpaddr7, x0")
            t.emit("csrr x7, pmpaddr7")
            t.check("x7", 0, lab, "pmpaddr reads 0 after writing 0")
        elif which == "warl":
            for pat in (X(0x55555555, 0x5555555555555555), X(0xAAAAAAAA, 0xAAAAAAAAAAAAAAAA)):
                t.load("x6", pat)
                t.emit("csrw pmpaddr7, x6")
                t.emit("csrr x7, pmpaddr7")
                t.emit("and x6, x6, x9")
                t.emit("xor x7, x7, x6")
                t.check("x7", 0, lab, "pmpaddr holds exactly the implemented bits of the value written")
        set_cfg_byte(t, 7, None)
        t.emit("csrw pmpaddr7, x0")

    for rule, which, plan in (
        ("pmp_tor_off_addr_read_mask", "tor", "1. With A = TOR and with A = OFF, pmpaddr bits G-1:0 read 0."),
        (
            "pmp_napot_addr_read_mask",
            "napot",
            (
                "1. With A = NAPOT: writing all ones reads r | z, and writing all ones "
                "except bit G-1 reads r | (z >> 1): bits G-2:0 read as ones, bit G-1 as written."
            ),
        ),
        (
            "pmp_addr_retention_on_mode_change",
            "retention",
            (
                "1. With A = NAPOT write all ones except bit G-1, switch "
                "to OFF and back to NAPOT: reads r | (z >> 1).\n2. The same with all ones: reads r | z (bit G-1 kept).\n"
                "3. Both again through TOR instead of OFF (when TOR is selectable; entry 7 has no permissions)."
            ),
        ),
        ("pmp_na4_select_restriction", "na4", "1. Writing A = NA4: when G >= 1 the A field does not read NA4."),
        ("pmp_region_granularity_g", "grain", "1. The grain probed on entry 5 equals the one on entry 7."),
        (
            "pmp_addr_encoding",
            "encoding",
            ("1. RV64: after writing all ones, pmpaddr[63:54] = 0.\n2. pmpaddr reads 0 after writing 0."),
        ),
        (
            "pmp_addr_warl",
            "warl",
            ("1. Writing 0x55..55 and 0xAA..AA reads back the value AND r (the implemented bits)."),
        ),
    ):
        t = nt(rule, ["I", "Sm"])
        describe(t, context=addr_ctx.replace("U-mode exists and ", ""), plan=plan)
        pmp_test(t, lambda t=t, which=which: addr_body(t, which), need_u=False)
        tests.append(t)

    # ---- pmp_rwx_warl / pmp_rw01_rsv ----
    for rule in ("pmp_rwx_warl", "pmp_rw01_rsv"):
        t = nt(rule, ["I", "Sm"])
        describe(
            t,
            context="Entry 7 (A = OFF, so it matches nothing) is written. mseccfg.MML is 0 (its reset value; no test "
            "sets it).",
            plan="1. Writing R = 0, W = 1 (with X = 0 and 1) into pmp7cfg never reads back R = 0, W = 1.",
        )

        def rw(t: TestFile = t) -> None:
            for x in (0, 1):
                lab = t.label("rw")
                t.emit(f"{lab}:", 0)
                set_cfg_byte(t, 7, 0x2 | (x << 2))
                read_cfg_byte(t, "x7", 7)
                t.emit("andi x7, x7, 3")
                t.emit("addi x7, x7, -2")
                t.emit("seqz x7, x7" if mut() == "pmp_w_without_r" else "snez x7, x7")
                t.check_bool("x7", lab, f"R=0, W=1, X={x} is not held")
            set_cfg_byte(t, 7, None)

        pmp_test(t, rw, need_u=False)
        tests.append(t)

    # ---- permission sweeps ----
    combos = ["", "r", "x", "rx", "rw", "rwx"]

    def extra(t: TestFile, ents: list[E]) -> None:
        """lr.w (Zalrsc) and amoadd.w (Zaamo) on each region from S and U."""
        for i, e in enumerate(ents):
            off = PAGE * (i + 1) + 0x20
            for mode in ("S", "U"):

                def m(mode: str = mode, off: int = off, e: E = e) -> None:
                    for enc, note, kind, cond in (
                        (
                            (0x02 << 27) | (8 << 15) | (2 << 12) | (7 << 7) | 0x2F,
                            "lr.w x7, (x8)",
                            "r",
                            "defined(ZALRSC_SUPPORTED)",
                        ),
                        (
                            (7 << 20) | (8 << 15) | (2 << 12) | (7 << 7) | 0x2F,
                            "amoadd.w x7, x7, (x8)",
                            "w",
                            "defined(ZAAMO_SUPPORTED)",
                        ),
                    ):
                        with t.only_if(cond):
                            t.li("x7", 0)
                            t.la("x8", f"pmp_buf+{off}")
                            L.word_window(
                                t,
                                mode,
                                enc,
                                note,
                                model(ents, mode, off, 4, kind),
                                f"{note} on {e.perm or '-'}",
                                [0, f"pmp_buf+{off}"],
                            )

                guard(t, L.MODE_COND[mode], m)

    def perm_rule(rule: str, kinds: str, plan: str, more: bool = False) -> None:
        t = nt(rule)
        describe(t, context=CTX, plan=plan)

        def body() -> None:
            for half in (combos[:3], combos[3:]):
                ents = [E("NAPOT", PAGE * (i + 1), PAGE * (i + 2), p) for i, p in enumerate(half)]
                program(t, ents)
                pts = [(PAGE * (i + 1) + 0x10, kinds) for i in range(len(half))]
                sweep(t, ents, pts, desc="/".join(p or "-" for p in half))
                if more:
                    extra(t, ents)

        pmp_test(t, body)
        tests.append(t)

    perm_rule(
        "pmp_load_fault",
        "r",
        "1. Regions with R/W/X = none, R, X, RX, RW, RWX: lw (and lr.w with Zalrsc) in "
        "S and U raises load access fault (5) exactly where R = 0; in M-mode (L = 0) lw succeeds.",
        True,
    )
    perm_rule(
        "pmp_store_fault",
        "w",
        "1. The same regions: sw (and amoadd.w with Zaamo) in S and U raises store/AMO "
        "access fault (7) exactly where W = 0; in M-mode sw succeeds.",
        True,
    )
    perm_rule(
        "pmp_exec_fault",
        "x",
        "1. The same regions: a jump to a ret in S and U raises instruction access fault "
        "(1, xepc = the target) exactly where X = 0; M-mode succeeds.",
    )
    perm_rule(
        "pmp_rwx_check",
        "rwx",
        "1. Each region gets a load, store and fetch from M, S and U: with L = 0, M "
        "always succeeds and S/U succeed exactly when the matching permission bit is set.",
    )
    perm_rule("pmp_cfg_permissions", "rwx", "1. As pmp_rwx_check: R, W and X each permit only their own access type.")
    perm_rule(
        "pmp_access_fault_exception",
        "rwx",
        "1. Each denied access raises the access fault for its type: instruction (1), load (5), store/AMO (7).",
    )

    # ---- cache-block operations ----
    t = nt("pmp_cbm_fault", [*REQ_U, "S", "Zicbom"])
    describe(
        t,
        context=CTX + " menvcfg/senvcfg CBCFE and CBIE (= 11) are set so the instructions execute in S and U. A "
        "cache-block management instruction is permitted when a load or a store to the block would be "
        "(cmo.adoc cbm_access); when only a fetch would be, it is UNSPECIFIED; otherwise it raises store/AMO access "
        "fault (7) with xtval = rs1.",
        plan="1. cbo.clean, cbo.flush and cbo.inval in S and U on regions with no permissions (fault), R (ok), X "
        "(ok or fault) and RW (ok).",
    )

    def cbm_body() -> None:
        t.li("x6", 0x70)
        t.emit("csrs menvcfg, x6")
        t.emit("csrs senvcfg, x6")
        regions = ["", "r", "x", "rw"]
        ents = [E("NAPOT", PAGE * i, PAGE * (i + 1), p) for i, p in enumerate(regions)]
        program(t, ents)
        for i, p in enumerate(regions):
            off = PAGE * i + 0x40
            for mode in ("S", "U"):
                for op in ("clean", "flush", "inval"):
                    if "r" in p or "w" in p:
                        exp = "ok"
                    elif "x" in p:
                        exp = ["ok", 7]
                    else:
                        exp = "ok" if mut() == "pmp_cbm_noperm_ok" else 7
                    t.la("x8", f"pmp_buf+{off}")
                    L.word_window(
                        t, mode, cbo(op), f"cbo.{op} (x8)", exp, f"cbo.{op} on {p or '-'}", [0, f"pmp_buf+{off}"]
                    )
        t.li("x6", 0x70)
        t.emit("csrc menvcfg, x6")

    pmp_test(t, cbm_body)
    tests.append(t)

    # ---- address matching ----
    t = nt("pmp_a_field_off")
    describe(
        t,
        context=CTX,
        plan="1. Entry 0 OFF with pmpaddr0 holding the NAPOT encoding of P1, no permissions: S/U "
        "load, store and fetch in P1 succeed (the background matches).\n2. The same entry with A = NAPOT: they "
        "fault.",
    )

    def off_body() -> None:
        for a in ("OFF", "NAPOT"):
            ents = [E(a, PAGE, 2 * PAGE, "")]
            program(t, ents)
            sweep(t, ents, [(PAGE + 8, "rwx")], ("S", "U"), desc=f"A = {a}")

    pmp_test(t, off_body)
    tests.append(t)

    t = nt("pmp_a_field_tor")
    describe(
        t,
        context=CTX + " Needs TOR (probed on entry 5). Entry 0's configuration holds R = W = X = 1 with A = OFF, "
        "which must not matter to entry 1.",
        plan="1. Entry 1 TOR from pmpaddr0 = P1 to pmpaddr1 = P3, no permissions: accesses at P1 - 4 and P3 "
        "succeed; at P1, P2 + 4 and P3 - 4 S/U accesses fault and M-mode ones succeed.\n2. Entry 0 TOR (base 0) up "
        "to P2 with R and X: S/U stores below P2 (P0, P1) fault, a store at P2 succeeds, loads and fetches below "
        "P2 succeed.",
    )

    def tor_body() -> None:
        ents = [E("OFF", perm="rwx"), E("TOR", PAGE, 3 * PAGE, "")]
        program(t, ents)
        sweep(
            t,
            ents,
            [(PAGE - 4, "rw"), (PAGE, "rwx"), (2 * PAGE + 4, "r"), (3 * PAGE - 4, "rwx"), (3 * PAGE, "rw")],
            ("M", "S", "U"),
            desc="TOR [P1, P3)",
        )
        ents = [E("TOR", 0, 2 * PAGE, "rx", base0=True)]
        program(t, ents)
        sweep(
            t,
            ents,
            [(0x10, "w"), (PAGE + 0x10, "wrx"), (2 * PAGE - 4, "w"), (2 * PAGE, "w")],
            ("S", "U"),
            desc="TOR [0, P2) RX",
        )

    pmp_test(t, tor_body, extra=["pmp_tor"])
    tests.append(t)

    for rule, plan in (
        (
            "pmp_a_field_napot_na4",
            (
                "1. NAPOT regions of 4 KiB (P1, none), 8 KiB (P2-P3, R) and 16 KiB (P0-P3, RW, "
                "lowest priority): S/U accesses just inside and outside each boundary.\n2. With G = 0: an NA4 region (one "
                "word) and an 8-byte NAPOT region, no permissions: the words inside fault in U-mode, their neighbours "
                "do not."
            ),
        ),
        (
            "pmp_napot_encoding_low_bits",
            (
                "1. As pmp_a_field_napot_na4: the number of trailing ones in pmpaddr sets "
                "the NAPOT size (8 bytes to 16 KiB)."
            ),
        ),
    ):
        t = nt(rule)
        describe(t, context=CTX, plan=plan)

        def napot_body(t: TestFile = t) -> None:
            ents = [E("NAPOT", PAGE, 2 * PAGE, ""), E("NAPOT", 2 * PAGE, 4 * PAGE, "r"), E("NAPOT", 0, 4 * PAGE, "rw")]
            program(t, ents)
            pts = [
                (0, "rw"),
                (PAGE - 4, "rw"),
                (PAGE, "rw"),
                (2 * PAGE - 4, "rw"),
                (2 * PAGE, "rw"),
                (3 * PAGE + 0x100, "rw"),
                (4 * PAGE - 4, "rw"),
            ]
            sweep(t, ents, pts, ("S", "U"), desc="NAPOT 4K/8K/16K")
            zflag(t, "x9", 0)

            def fine() -> None:
                ents2 = [E("NA4", PAGE + 0x10, PAGE + 0x14, ""), E("NAPOT", PAGE + 0x20, PAGE + 0x28, "")]
                program(t, ents2)
                pts2 = [(PAGE + o, "rw") for o in (0xC, 0x10, 0x14, 0x1C, 0x20, 0x24, 0x28)]
                sweep(t, ents2, pts2, ("U",), desc="NA4 and NAPOT-8")

            L.either(t, "x9", fine, lambda: None)

        pmp_test(t, napot_body)
        tests.append(t)

    t = nt("pmp_entry_priority")
    describe(
        t,
        context=CTX,
        plan="1. Entry 0 (P1, R only) over entry 1 (P0-P3 NAPOT, RW): a store to P1 faults, to P2 succeeds.\n2. Entry "
        "0 (P1, RW) over entry 1 (P0-P3, no permissions): a store and a load in P1 succeed, in P2 fault.",
    )

    def pri_body() -> None:
        for p0, p1 in (("r", "rw"), ("rw", "")):
            ents = [E("NAPOT", PAGE, 2 * PAGE, p0), E("NAPOT", 0, 4 * PAGE, p1)]
            program(t, ents)
            sweep(
                t,
                ents,
                [(PAGE + 0x30, "rw"), (2 * PAGE + 0x30, "rw")],
                ("S", "U"),
                desc=f"{p0 or '-'} over {p1 or '-'}",
            )

    pmp_test(t, pri_body)
    tests.append(t)

    t = nt("pmp_full_match_required")
    describe(
        t,
        context=CTX + " Needs G = 0 (NA4 regions). An entry that matches only part of an access makes it fail even "
        "when its permissions would allow it.",
        plan="1. Entry 0 NA4 at P1+4 (RWX) over entry 1 NAPOT P1 (none): lw at P1+4 succeeds; lw at P1 faults (S/U); "
        "RV64 ld/sd at P1 (bytes P1..P1+7) fault in S, U and M-mode (a partial match fails irrespective of L, R, W, "
        "X).\n2. Entry 0 NA4 at P1+4 (none) over entry 1 NAPOT P1 (RWX): RV64 ld/sd at P1 fault in every mode; lw at "
        "P1 succeeds.\n3. A misaligned lw at P1+2 in case 1 raises address-misaligned or load access fault in S/U "
        "(M-mode may also complete it as two accesses that each match fully).",
    )

    def full_body() -> None:
        zflag(t, "x9", 0)

        def fine() -> None:
            for p0, p1 in (("rwx", ""), ("", "rwx")):
                ents = [E("NA4", PAGE + 4, PAGE + 8, p0), E("NAPOT", PAGE, 2 * PAGE, p1)]
                program(t, ents)
                d = f"NA4 {p0 or '-'} over {p1 or '-'}"
                for mode in ("M", "S", "U"):

                    def m(mode: str = mode, ents: list[E] = ents, d: str = d, p0: str = p0) -> None:
                        for off in (PAGE, PAGE + 4):
                            access(t, mode, "r", off, model(ents, mode, off, 4, "r"), d)
                        with t.rv64_only():
                            for k in ("r", "w"):
                                access(t, mode, k, PAGE, model(ents, mode, PAGE, 8, k), d, size=8)
                        if p0:
                            t.la("x8", f"pmp_buf+{PAGE + 2}")
                            L.win(
                                t,
                                mode,
                                ["lw x7, 0(x8)"],
                                ["ok", 4, 5] if mode == "M" else [4, 5],
                                "misaligned lw across the NA4 boundary",
                                [0, f"pmp_buf+{PAGE + 2}", f"pmp_buf+{PAGE + 4}"],
                            )

                    guard(t, L.MODE_COND[mode], m)

        L.either(t, "x9", fine, lambda: None)

    pmp_test(t, full_body)
    tests.append(t)

    t = nt("pmp_no_entry_match")
    describe(
        t,
        context=CTX.replace(NOBG, "the background is replaced by two TOR entries with RWX that leave P1 unmatched")
        + " Needs TOR.",
        plan="1. Entries 0 (TOR [0, P1)) and 2 (TOR [P2, top)), RWX; nothing matches P1.\n2. Loads, stores and "
        "fetches in P1: S and U fault; M-mode succeeds.\n3. P0 and P2 stay accessible.",
    )

    def nm_body() -> None:
        ents = [E("TOR", 0, PAGE, "rwx", base0=True), E("OFF"), E("TOR", 2 * PAGE, 0, "rwx", top_all=True)]
        program(t, ents, bg=False)
        sweep(
            t,
            ents,
            [(PAGE + 0x40, "rwx"), (PAGE - 4, "rw"), (2 * PAGE, "rw")],
            ("M", "S", "U"),
            desc="hole at P1",
            bg=False,
        )

    pmp_test(t, nm_body, extra=["pmp_tor"])
    tests.append(t)

    # ---- MPRV ----
    for rule, plan in (
        (
            "pmp_check_priv_modes",
            (
                "1. P1 without permissions (L = 0): M-mode loads and stores succeed; with MPRV = 1 "
                "and MPP = U or S they fault (5/7); with MPRV = 1 and MPP = M they succeed.\n2. S and U accesses fault."
            ),
        ),
        (
            "mstatus_mprv_ldst_op",
            (
                "1. As pmp_check_priv_modes: MPRV = 1 makes M-mode loads and stores use the "
                "protection of MPP (U, S); MPP = M behaves as MPRV = 0."
            ),
        ),
        (
            "mstatus_mprv_inst_xlat_op",
            ("1. P1 without permissions: with MPRV = 1 and MPP = U (and S), M-mode fetches from P1 still succeed."),
        ),
    ):
        t = nt(rule)
        describe(
            t,
            context=CTX + " MPRV is cleared after each access, and MPP is set again for every case (a trap "
            "from M-mode and its MRET leave MPP = U).",
            plan=plan,
        )

        def mprv_body(t: TestFile = t, rule: str = rule) -> None:
            ents = [E("NAPOT", PAGE, 2 * PAGE, "")]
            program(t, ents)
            kinds = "x" if rule == "mstatus_mprv_inst_xlat_op" else "rw"
            for mpp, cond in ((0, U), (1, S), (3, None)):

                def c(mpp: int = mpp) -> None:
                    for k in kinds:
                        if k == "x":
                            exp = 1 if (mut() == "pmp_mprv_fetch" and mpp != 3) else "ok"
                        else:
                            exp = model(ents, "M" if mpp == 3 else "U", PAGE + 0x50, 4, k)
                            if mut() == "pmp_mprv_ignored":
                                exp = "ok"
                        L.csr_bits(t, "mstatus", MPP, False)
                        if mpp:
                            t.li("x5", mpp << 11)
                            t.emit("csrs mstatus, x5")
                        t.li("x5", MPRV)
                        t.emit("csrs mstatus, x5")
                        access(t, "M", k, PAGE + 0x50, exp, f"MPRV = 1, MPP = {mpp}")
                        t.li("x5", MPRV)
                        t.emit("csrc mstatus, x5")

                guard(t, cond, c)
            if rule != "mstatus_mprv_inst_xlat_op":
                sweep(t, ents, [(PAGE + 0x50, "rw")], ("M", "S", "U"), desc="MPRV = 0")

        pmp_test(t, mprv_body)
        tests.append(t)

    t = nt("mstatus_mxr_sum_op_acc_fault", [*REQ_U, "S"])
    describe(
        t,
        context=CTX + " Translation is off (satp = Bare).",
        plan="1. P1 execute-only, P2 with no permissions: with MXR = 1 and SUM = 1, S-mode and U-mode loads from "
        "P1 and P2 and stores to P2 still raise access faults.",
    )

    def mxr_body() -> None:
        ents = [E("NAPOT", PAGE, 2 * PAGE, "x"), E("NAPOT", 2 * PAGE, 3 * PAGE, "")]
        program(t, ents)
        t.li("x5", MXR | SUM)
        t.emit("csrs mstatus, x5")
        for mode in ("S", "U"):
            for off, k in ((PAGE + 0x60, "r"), (2 * PAGE + 0x60, "r"), (2 * PAGE + 0x60, "w")):
                exp = model(ents, mode, off, 4, k)
                if mut() == "pmp_mxr_bypass" and off < 2 * PAGE:
                    exp = "ok"
                access(t, mode, k, off, exp, "MXR = SUM = 1")
        t.li("x5", MXR | SUM)
        t.emit("csrc mstatus, x5")

    pmp_test(t, mxr_body)
    tests.append(t)

    # ---- misaligned accesses and fetches across a PMP boundary ----
    mis_ctx = (
        CTX + " The second part of the access is in a region without permissions, so the access cannot "
        "complete: it raises address-misaligned (xtval 0 or the access address) or an access fault (xtval 0 "
        "or the address of the faulting portion: P2 when the access is split, the access address when it is "
        "performed undivided, since then the whole access is the portion that faulted)."
    )

    def mis_body(t: TestFile) -> None:
        ents = [E("NAPOT", PAGE, 2 * PAGE, "rw"), E("NAPOT", 2 * PAGE, 3 * PAGE, "")]
        program(t, ents)
        a, b = f"pmp_buf+{2 * PAGE - 2}", f"pmp_buf+{2 * PAGE}"
        for mode in ("S", "U"):

            def m(mode: str = mode) -> None:
                for insn, misal, af in (("lw x7, 0(x8)", 4, 5), ("sw x7, 0(x8)", 6, 7)):
                    t.li("x7", RET)
                    t.la("x8", a)
                    lab = t.label("misal")
                    t.allow(1)
                    t.enter(mode)
                    t.emit(f"{lab}:", 0)
                    t.emit(insn)
                    t.leave()
                    t.emit("AI_OUTCOME", 20)
                    t.check("x13", 1, lab, f"{insn.split()[0]} across P1/P2 in {mode}: one trap")
                    L.log_word(t, "x6", "TRAPLOG_TVAL")
                    t.la("x8", a)
                    t.emit("sub x8, x6, x8")
                    t.emit("seqz x8, x8")
                    t.emit("seqz x9, x6")
                    t.emit("or x8, x8, x9  // tval in {0, start}")
                    t.emit(f"addi x9, x14, -{misal}")
                    t.emit("seqz x9, x9")
                    t.emit("and x8, x8, x9  // misaligned with a legal tval")
                    t.la("x9", b)
                    t.emit("sub x9, x6, x9")
                    t.emit("seqz x9, x9")
                    if mut() == "pmp_mis_tval_start":
                        t.emit("li x9, 0")
                    t.la("x5", a)
                    t.emit("sub x5, x6, x5")
                    t.emit("seqz x5, x5")
                    t.emit("or x9, x9, x5  // an undivided access: the whole access is the faulting portion")
                    t.emit("seqz x6, x6")
                    t.emit("or x9, x9, x6  // tval in {0, start, P2}")
                    t.emit(f"addi x6, x14, -{af}")
                    t.emit("seqz x6, x6")
                    t.emit("and x9, x9, x6  // access fault with a legal tval")
                    t.emit("or x8, x8, x9")
                    t.check_bool(
                        "x8",
                        lab,
                        f"{insn.split()[0]} across P1/P2 in {mode}: misaligned with xtval 0 or "
                        "the start, or access fault with xtval 0, the start or P2",
                    )
                    if insn.startswith("sw"):
                        t.la("x8", b)
                        t.emit("lw x7, 0(x8)")
                        t.check("x7", RET, lab, "the denied part (P2) was not written")

            guard(t, L.MODE_COND[mode], m)

    for rule, plan in (
        (
            "pmp_misaligned_access_behavior",
            (
                "1. P1 RW, P2 none: lw and sw at P2 - 2 in S and U raise misaligned (4/6) "
                "with xtval 0 or P2 - 2, or access fault (5/7) with xtval 0, P2 - 2 or P2; they never complete.\n"
                "2. After the faulting sw, the word at P2 (read in M-mode) is unchanged."
            ),
        ),
        (
            "mtval_vaddr_wr_misaligned_addr",
            (
                "1. As pmp_misaligned_access_behavior: when the misaligned lw/sw raises an "
                "access fault, a nonzero mtval is the address of a faulting portion: P2 (split access) or P2 - 2 "
                "(undivided access), not any other address."
            ),
        ),
    ):
        t = nt(rule)
        describe(t, context=mis_ctx, plan=plan)
        pmp_test(t, lambda t=t: mis_body(t))
        tests.append(t)

    for rule in ("mtval_varlen_wr", "mepc_varlen_wr"):
        t = nt(rule, overrides={2 * PAGE - 4: 0x80670000, 2 * PAGE: 0x00000000})
        describe(
            t,
            context=CTX + " Needs C (IALIGN = 16): a 32-bit ret straddles P1/P2 (its low half is the last halfword "
            "of P1, its high half the first halfword of P2).",
            plan="1. P1 RWX, P2 RX: a jump to P2 - 2 in S and U executes the ret (control).\n2. P1 RWX, P2 R only: the "
            "jump raises instruction access fault with mepc = P2 - 2 (the instruction) and mtval = 0 or P2 (the "
            "faulting portion).",
        )

        def vl_body(t: TestFile = t) -> None:
            for p2 in ("rx", "r"):
                ents = [E("NAPOT", PAGE, 2 * PAGE, "rwx"), E("NAPOT", 2 * PAGE, 3 * PAGE, p2)]
                program(t, ents)
                for mode in ("S", "U"):

                    def m(mode: str = mode, p2: str = p2) -> None:
                        tgt = f"pmp_buf+{2 * PAGE - 2}"
                        t.la("x8", tgt)
                        lab = t.label("vl")
                        t.allow(1)
                        t.enter(mode)
                        t.emit(f"{lab}:", 0)
                        t.emit("jalr x1, 0(x8)")
                        t.leave()
                        tv = [0, tgt if mut() == "pmp_fetch_tval_start" else f"pmp_buf+{2 * PAGE}"]
                        fetch_outcome(
                            t, "ok" if "x" in p2 else 1, lab, tgt, f"fetch across P1/P2 ({p2}) in {mode}-mode", tv, mode
                        )

                    guard(t, L.MODE_COND[mode], m)

        with t.only_if("defined(C_SUPPORTED)"):
            pmp_test(t, vl_body)
        tests.append(t)

    # ---- locking (at the end of each test: locks last until reset) ----
    lock_ctx = (
        CTX + " Locks cannot be undone, so they are set last. Entry 5 is NAPOT P1 with R only and entry 4 "
        "TOR [P2, P3) with RW (its base pmpaddr3 = P2, entry 3 OFF), both L = 1. The final restore puts the "
        "framework's entry 0 back, which matches everything first, so the end-of-test code is unaffected. With "
        "Smepmp the test runs only when mseccfg.RLB = 0 (its reset value)."
    )

    def lock_setup(t: TestFile) -> list[E | None]:
        ents: list[E | None] = [
            None,
            None,
            None,
            E("OFF"),
            E("TOR", 2 * PAGE, 3 * PAGE, "rw", lock=True),
            E("NAPOT", PAGE, 2 * PAGE, "r", lock=True),
        ]
        program(t, ents)
        return ents

    def rlb_zero(t: TestFile) -> None:
        with t.only_if("defined(SMEPMP_SUPPORTED)"):
            t.emit("csrr x6, 0x747")
            t.emit("andi x6, x6, 4")
            t.emit("seqz x6, x6")
            t.la("x8", "pmp_ok")
            t.emit("LREG x7, 0(x8)")
            t.emit("and x7, x7, x6")
            t.emit("SREG x7, 0(x8)")

    for rule, plan in (
        (
            "pmp_l_bit_m_mode_enforcement",
            (
                "1. M-mode: load in P1 succeeds, store and fetch in P1 fault; load and store "
                "in P2 succeed, fetch faults.\n2. S and U see the same permissions."
            ),
        ),
        ("pmp_mmode_locking", "1. As pmp_l_bit_m_mode_enforcement: locked entries apply to M-mode."),
        (
            "pmp_l_bit_function",
            (
                "1. Writes to pmp5cfg (clearing L, setting A = NAPOT with W) and to pmpaddr5 are "
                "ignored; an M-mode store to P1 still faults."
            ),
        ),
        (
            "pmp_locked_until_reset",
            (
                "1. After locking, M-mode writes of 0 to pmpcfg are ignored for the locked "
                "entries, which keep enforcing (an M-mode store to P1 and a fetch from P2 still fault)."
            ),
        ),
        (
            "pmp_l_bit_write_protection",
            (
                "1. Writes to pmpaddr5 and pmpaddr4 are ignored.\n2. Entry 4 is locked TOR, so "
                "writes to pmpaddr3 are ignored too; pmpaddr2 stays writable.\n3. A pmpcfg write that clears "
                "pmp4cfg/pmp5cfg and sets pmp6cfg = R leaves the locked bytes unchanged and writes pmp6cfg."
            ),
        ),
    ):
        t = nt(rule, ["I", "Sm"])
        describe(t, context=lock_ctx.replace("U-mode exists and ", ""), plan=plan)

        def lk(t: TestFile = t, rule: str = rule) -> None:
            ents = lock_setup(t)
            if rule in ("pmp_l_bit_m_mode_enforcement", "pmp_mmode_locking"):
                sweep(t, ents, [(PAGE + 0x70, "rwx"), (2 * PAGE + 0x70, "rwx")], ("M", "S", "U"), desc="locked")
            elif rule == "pmp_l_bit_function":
                lab = t.label("lf")
                t.emit("csrr x9, pmpaddr5")
                read_cfg_byte(t, "x8", 5)
                t.emit(f"{lab}:", 0)
                set_cfg_byte(t, 5, 0x1B)
                read_cfg_byte(t, "x7", 5)
                t.emit("sub x7, x7, x8")
                t.check("x7", 0, lab, "pmp5cfg unchanged")
                t.emit("li x6, -1")
                t.emit("csrw pmpaddr5, x6")
                t.emit("csrr x7, pmpaddr5")
                t.emit("sub x7, x7, x9")
                t.check("x7", 0, lab, "pmpaddr5 unchanged")
                access(t, "M", "w", PAGE + 0x70, model(ents, "M", PAGE + 0x70, 4, "w"), "after write attempts")
            elif rule == "pmp_locked_until_reset":
                cfgs_off(t)
                sfence(t)
                access(t, "M", "w", PAGE + 0x70, model(ents, "M", PAGE + 0x70, 4, "w"), "after writing pmpcfg = 0")
                access(
                    t, "M", "x", 2 * PAGE + 0x70, model(ents, "M", 2 * PAGE + 0x70, 4, "x"), "after writing pmpcfg = 0"
                )
            else:
                lab = t.label("wp")
                t.emit(f"{lab}:", 0)
                for i in (5, 4, 3, 2):
                    t.emit(f"csrr x9, pmpaddr{i}")
                    t.emit("LI(x6, 4096)", 2)
                    t.emit("add x6, x9, x6")
                    t.emit(f"csrw pmpaddr{i}, x6")
                    t.emit(f"csrr x7, pmpaddr{i}")
                    t.emit("sub x7, x7, x9")
                    locked = i >= 3
                    if mut() == "pmp_lock_addr_writable" and i == 5:
                        locked = False
                    if mut() == "pmp_tor_base_writable" and i == 3:
                        locked = False
                    t.check(
                        "x7", 0 if locked else 4096, lab, f"pmpaddr{i} {'unchanged (locked)' if locked else 'writable'}"
                    )
                    t.emit(f"csrw pmpaddr{i}, x9")
                read_cfg_byte(t, "x8", 4)
                read_cfg_byte(t, "x9", 5)
                t.emit("slli x9, x9, 8")
                t.emit("or x8, x8, x9  // locked pmp4cfg/pmp5cfg")
                t.emit("li x6, 1")
                with t.rv64_only():
                    t.emit("slli x6, x6, 48")
                    t.emit("csrw pmpcfg0, x6  // L cleared in bytes 4 and 5, byte 6 = R")
                with t.rv32_only():
                    t.emit("slli x6, x6, 16")
                    t.emit("csrw pmpcfg1, x6  // L cleared in bytes 0 and 1 (entries 4, 5), byte 2 = R")
                read_cfg_byte(t, "x7", 4)
                read_cfg_byte(t, "x9", 5)
                t.emit("slli x9, x9, 8")
                t.emit("or x7, x7, x9")
                t.emit("sub x7, x7, x8")
                t.check("x7", 0, lab, "locked pmp4cfg and pmp5cfg unchanged by a pmpcfg write")
                read_cfg_byte(t, "x7", 6)
                t.check("x7", 1, lab, "the unlocked pmp6cfg in the same pmpcfg register is written")
                set_cfg_byte(t, 6, None)

        probe(t, need_u=False)
        rlb_zero(t)
        flag(t, "x9", "pmp_ok")
        L.either(t, "x9", lambda t=t, lk=lk: (lk(), restore(t)), lambda t=t: restore_if_csrs(t))
        tests.append(t)

    # ---- Smepmp ----
    t = nt("mseccfg_rlb_op_warl", [*REQ_U, "Smepmp"])
    describe(
        t,
        context=CTX + " RLB is WARL; the RLB = 1 cases run when RLB is 0 at the start and reads back 1 after being "
        "set. Locks are set last.",
        plan="1. No entry locked, RLB = 1: lock entry 5 (NAPOT P1, R); pmpaddr5 can still be written, and L can be "
        "cleared.\n2. RLB = 0, then lock entry 5 again: writing RLB = 1 is ignored (RLB reads 0) and pmpaddr5 can no "
        "longer be written.",
    )

    def rlb_body() -> None:
        t.emit("csrr x6, 0x747")
        t.emit("andi x6, x6, 4")
        t.emit("seqz x9, x6")
        t.emit("csrsi 0x747, 4  // RLB = 1")
        t.emit("csrr x6, 0x747")
        t.emit("andi x6, x6, 4")
        t.emit("snez x6, x6")
        t.emit("and x9, x9, x6")

        def with_rlb() -> None:
            ents: list[E | None] = [None] * 5 + [E("NAPOT", PAGE, 2 * PAGE, "r", lock=True)]
            program(t, ents)
            lab = t.label("rlb")
            t.emit("csrr x9, pmpaddr5")
            t.emit("LI(x6, 4096)", 2)
            t.emit("add x6, x9, x6")
            t.emit(f"{lab}:", 0)
            t.emit("csrw pmpaddr5, x6")
            t.emit("csrr x7, pmpaddr5")
            t.emit("sub x7, x7, x9")
            t.check("x7", 4096, lab, "locked pmpaddr5 writable with RLB = 1")
            cfgs_off(t)
            read_cfg_byte(t, "x7", 5)
            t.emit("srli x7, x7, 7")
            t.check("x7", 0, lab, "L of entry 5 cleared with RLB = 1")
            t.emit("csrci 0x747, 4  // RLB = 0")
            program(t, ents)
            t.emit("csrsi 0x747, 4")
            t.emit("csrr x7, 0x747")
            t.emit("andi x7, x7, 4")
            t.check("x7", 4 if mut() == "pmp_rlb_sticky_ignored" else 0, lab, "RLB stays 0 once an entry is locked")
            t.emit("csrr x9, pmpaddr5")
            t.emit("LI(x6, 4096)", 2)
            t.emit("add x6, x9, x6")
            t.emit("csrw pmpaddr5, x6")
            t.emit("csrr x7, pmpaddr5")
            t.emit("sub x7, x7, x9")
            t.check("x7", 0, lab, "locked pmpaddr5 not writable with RLB = 0")

        L.either(t, "x9", with_rlb, lambda: t.emit("csrci 0x747, 4"))

    pmp_test(t, rlb_body)
    tests.append(t)

    t = nt("mseccfg_mmwp_op_warl", [*REQ_U, "Smepmp"])
    describe(
        t,
        context=CTX.replace(NOBG, "two TOR entries (RWX) cover everything except P1") + " Needs TOR. MMWP is sticky, "
        "so it is set last; the restored framework entry 0 matches every address, so the end-of-test code is "
        "unaffected.",
        plan="1. MMWP = 0: M-mode load and store in P1 (no matching entry) succeed.\n2. Set MMWP: if it reads back 1, "
        "M-mode load and store in P1 fault, accesses elsewhere succeed, and clearing MMWP has no effect.",
    )

    def mmwp_body() -> None:
        ents = [E("TOR", 0, PAGE, "rwx", base0=True), E("OFF"), E("TOR", 2 * PAGE, 0, "rwx", top_all=True)]
        program(t, ents, bg=False)
        for k in "rw":
            access(t, "M", k, PAGE + 0x80, "ok", "MMWP = 0")
        t.emit("csrsi 0x747, 2")
        t.emit("csrr x9, 0x747")
        t.emit("andi x9, x9, 2")

        def on() -> None:
            for k in "rw":
                access(t, "M", k, PAGE + 0x80, "ok" if mut() == "pmp_mmwp_ignored" else CAUSE[k], "MMWP = 1, no match")
            access(t, "M", "r", 2 * PAGE + 0x80, "ok", "MMWP = 1, matched")
            lab = t.label("st")
            t.emit(f"{lab}:", 0)
            t.emit("csrci 0x747, 2")
            t.emit("csrr x7, 0x747")
            t.check_masked("x7", 2, 2, lab, "MMWP is sticky")

        L.either(t, "x9", on, lambda: None)

    pmp_test(t, mmwp_body, extra=["pmp_tor"])
    tests.append(t)

    # ---- precise traps ----
    t = nt("pmp_violation_precise_trap")
    describe(
        t,
        context=CTX,
        plan="1. P1 R only: a U/S store to P1 faults and memory keeps its old value (read back in "
        "M-mode).\n2. P2 without permissions: a U/S load from P2 faults and leaves its destination register "
        "unchanged.",
    )

    def precise() -> None:
        ents = [E("NAPOT", PAGE, 2 * PAGE, "r"), E("NAPOT", 2 * PAGE, 3 * PAGE, "")]
        program(t, ents)
        for mode in ("S", "U"):

            def m(mode: str = mode) -> None:
                t.li("x7", 0x5A5)
                t.la("x8", f"pmp_buf+{PAGE + 0x90}")
                lab = L.win(t, mode, ["sw x7, 0(x8)"], 7, "store to an R-only region", [0, f"pmp_buf+{PAGE + 0x90}"])
                t.la("x8", f"pmp_buf+{PAGE + 0x90}")
                t.emit("lw x7, 0(x8)")
                t.check(
                    "x7", 0x5A5 if mut() == "pmp_store_lands" else RET, lab, "memory unchanged by the faulting store"
                )
                t.li("x7", 0x123)
                t.la("x8", f"pmp_buf+{2 * PAGE + 0x90}")
                lab = L.win(
                    t, mode, ["lw x7, 0(x8)"], 5, "load from a no-permission region", [0, f"pmp_buf+{2 * PAGE + 0x90}"]
                )
                t.check("x7", 0x123, lab, "destination unchanged by the faulting load")

            guard(t, L.MODE_COND[mode], m)

    pmp_test(t, precise)
    tests.append(t)

    # ---- pmpcfg layout for entries 8-15 ----
    for rule, xl in (("pmp_cfg_rv32_layout", 32), ("pmp_cfg_rv64_layout", 64)):
        t = nt(rule)
        t.extra_data += ["pmp_save2: .fill 10, 8, 0", "pmp_hi_ok: .dword 0"]
        describe(
            t,
            context=CTX.replace(
                "Entries 0-5 are programmed by the test; entry 7 holds",
                "Entries 0-7 are OFF and entries 8-13 are programmed by the test; entry 15 holds",
            )
            + " Needs 16 entries (pmpaddr15 implemented, entries 8-15 free). "
            + (
                "RV32 only: entries 8-11 are in pmpcfg2 and 12-15 in pmpcfg3."
                if xl == 32
                else "RV64 only: entries 8-15 are in pmpcfg2."
            ),
            plan="1. Entries 8 (P0, X), 9 (P1, none), 12 (P2, R) and 13 (P3, RW), each NAPOT, written through the "
            "pmpcfg byte of its index: S and U loads, stores and fetches in P0-P3 follow those permissions.",
        )

        def layout(t: TestFile = t, xl: int = xl) -> None:
            t.la("x8", "pmp_save2")
            t.emit("csrr x7, pmpcfg2")
            t.emit("SREG x7, 0(x8)")
            if xl == 32:
                t.emit("csrr x7, pmpcfg3")
                t.emit("SREG x7, 8(x8)")
            for i in range(8, 16):
                t.emit(f"csrr x7, pmpaddr{i}")
                t.emit(f"SREG x7, {16 + 8 * (i - 8)}(x8)")
            t.emit("csrr x7, pmpcfg2")
            if xl == 32:
                t.emit("csrr x6, pmpcfg3")
                t.emit("or x7, x7, x6")
            t.emit("seqz x9, x7  // entries 8-15 free")
            t.emit("li x6, -1")
            t.emit("csrw pmpaddr15, x6")
            t.emit("csrr x6, pmpaddr15")
            t.emit("snez x6, x6")
            t.emit("and x9, x9, x6")
            ents: list[E | None] = [None] * 15
            ents[8] = E("NAPOT", 0, PAGE, "x")
            ents[9] = E("NAPOT", PAGE, 2 * PAGE, "")
            ents[12] = E("NAPOT", 2 * PAGE, 3 * PAGE, "r")
            ents[13] = E("NAPOT", 3 * PAGE, 4 * PAGE, "rw")

            def run() -> None:
                cfgs_off(t)
                for i in (8, 9, 12, 13):
                    e = ents[i]
                    assert e is not None
                    t.la("x7", f"pmp_buf+{e.lo}")
                    t.emit("srli x7, x7, 2")
                    t.emit(f"addi x7, x7, {(e.hi - e.lo) // 8 - 1}")
                    t.emit(f"csrw pmpaddr{i}, x7")
                t.emit("csrw pmpaddr14, x0")
                t.la("x8", "pmp_save")
                t.emit("LREG x7, 16(x8)")
                t.emit("csrw pmpaddr15, x7")
                static = sum(e.cfg() << (8 * (i - 8)) for i, e in enumerate(ents) if e is not None)
                t.emit("LREG x7, 0(x8)")
                t.emit("andi x7, x7, 0xFF  // the framework's entry 0 configuration")
                if xl == 64:
                    t.load("x6", X(0, static))
                    t.emit("slli x7, x7, 56")
                    t.emit("or x6, x6, x7")
                    t.emit("csrw pmpcfg2, x6")
                else:
                    t.load("x6", X(static & 0xFFFFFFFF, 0))
                    t.emit("csrw pmpcfg2, x6")
                    t.load("x6", X(static >> 32, 0))
                    t.emit("slli x7, x7, 24")
                    t.emit("or x6, x6, x7")
                    t.emit("csrw pmpcfg3, x6")
                sfence(t)
                if mut() == "pmp_layout_shift":  # the hardware applies pmp12cfg and pmp13cfg to each other's entry
                    e12, e13 = ents[12], ents[13]
                    assert e12 is not None and e13 is not None
                    ents[12] = E(e12.a, e12.lo, e12.hi, e13.perm)
                    ents[13] = E(e13.a, e13.lo, e13.hi, e12.perm)
                sweep(
                    t,
                    ents,
                    [(0x10, "rwx"), (PAGE + 0x10, "rwx"), (2 * PAGE + 0x10, "rwx"), (3 * PAGE + 0x10, "rwx")],
                    ("S", "U"),
                    desc="entries 8-13",
                )
                t.la("x8", "pmp_save2")
                for i in range(8, 16):
                    t.emit(f"LREG x7, {16 + 8 * (i - 8)}(x8)")
                    t.emit(f"csrw pmpaddr{i}, x7")
                t.emit("LREG x7, 0(x8)")
                t.emit("csrw pmpcfg2, x7")
                if xl == 32:
                    t.emit("LREG x7, 8(x8)")
                    t.emit("csrw pmpcfg3, x7")

            L.either(t, "x9", run, lambda: None)

        with t.only_if(f"__riscv_xlen == {xl}"):
            pmp_test(t, layout)
        tests.append(t)
    return tests
