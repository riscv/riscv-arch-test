# SPDX-License-Identifier: Apache-2.0
"""Helpers for the state-enable suites (gen_Smstateen.py): tests_ai/Smstateen and tests_ai/Ssstateen.

The stateen CSRs (mstateen0-3, hstateen0-3, sstateen0-3; mstateen0h-3h and hstateen0h-3h on RV32) gate access
to other state. Which bits are writable, read-only zero or read-only one is WARL and implementation-specific, and
the controlled state (siselect, stopi, scontext, srmcfg, jvt, ...) may or may not be implemented. These helpers
therefore probe at run time and compute every expected trap cause from the stateen bits actually read back:

  x6 = the effective machine-level enable of the state under test (mstateen bit AND "the state exists",
       where "exists" is an S-mode probe at the boot configuration)
  x8 = the hstateen bit (H only), x9 = the sstateen bit (user-level state only)

dyn_window() runs one access in a trap window and checks its outcome against the cause the spec gives for those
bits (smstateen.adoc and the HS-qualified rule of hypervisor.adoc):

  mode  state level  no trap when   otherwise
  S     any          m              illegal
  U     user (jvt)   m & s          illegal
  U     S/H          never          illegal
  VS    user, S      m & h          virtual if m, else illegal
  VS    H, S-noV     never          virtual if m, else illegal
  VU    user         m & h & s      virtual if m, else illegal
  VU    S, H         never          virtual if m, else illegal

"S-noV" is supervisor state that VS-mode can never access (srmcfg, sctrdepth, stopei with hstatus.VGEIN=0).
Registers: x1 and x7 are scratch (x7 is also the CSR source operand), x6/x8/x9 as above; windows use x13-x15.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent))
from aigen import POOL_TRAP, TestFile

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from contextlib import AbstractContextManager

MUT = os.environ.get("AI_MUTANT", "")  # gen_Smstateen.py mutants: plausible bugs in the expectations
SM = "src/priv/smstateen.adoc"
ISSUE = "https://github.com/riscv/riscv-isa-manual/issues/"
MARCH = "rv${XLEN}i_zicsr_zifencei"
H = "defined(H_SUPPORTED)"
S = "defined(S_SUPPORTED)"
RV32 = "__riscv_xlen == 32"
RV64 = "__riscv_xlen == 64"
ILLEGAL, VIRTUAL = 2, 22

# mstateen0 bit positions (smstateen.adoc register diagrams)
BIT = {
    "C": 0,
    "FCSR": 1,
    "JVT": 2,
    "CTR": 54,
    "SRMCFG": 55,
    "P1P13": 56,
    "CONTEXT": 57,
    "IMSIC": 58,
    "AIA": 59,
    "CSRIND": 60,
    "ENVCFG": 62,
    "SE0": 63,
}
M0_DEF = sum(1 << b for b in BIT.values())
H0_DEF = M0_DEF & ~((1 << 55) | (1 << 56))  # hstateen0 has no SRMCFG or P1P13 bit (WPRI)
S0_DEF = 0b111  # sstateen0: C, FCSR, JVT
N_DEF = 1 << 63  # mstateen1-3 and hstateen1-3: only bit 63 (SE) is defined; sstateen1-3: none
ONES = (1 << 64) - 1

BASE = {"m": 0x30C, "h": 0x60C, "s": 0x10C}  # stateenN = BASE + N; the RV32 high half is BASE + 0x10 + N


def defined(kind: str, n: int) -> int:
    """Defined bits of a stateen CSR (64-bit view)."""
    if kind == "s":
        return S0_DEF if n == 0 else 0
    if n:
        return N_DEF
    return M0_DEF if kind == "m" else H0_DEF


def cname(kind: str, n: int, high: bool = False) -> str:
    return f"{kind}stateen{n}{'h' if high else ''}"


def cnum(kind: str, n: int, high: bool = False) -> int:
    return BASE[kind] + n + (0x10 if high else 0)


def enc_csr(csr: int, f3: int, rd: int, rs1: int) -> int:
    return (csr << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | 0x73


# ---------------------------------------------------------------- controlled state
class Res:
    """One piece of state controlled by a stateen bit, reached by a CSR read (or an instruction encoding).

    level: "U" user state (sstateen applies), "S" supervisor state VS-mode may access (on its VS substitute),
    "SnoV" supervisor state VS-mode never accesses, "H" hypervisor or VS CSR."""

    def __init__(
        self,
        name: str,
        csr: int | None,
        level: str,
        m: tuple[int, int],
        h: tuple[int, int] | None,
        s: tuple[int, int] | None = None,
        cond: str | None = None,
        insn: int | None = None,
    ) -> None:
        self.name, self.csr, self.level, self.m, self.h, self.s, self.cond = name, csr, level, m, h, s, cond
        self.insn = insn

    def read(self) -> tuple[str, int]:
        """(assembly line, encoding) of a read (csrrs x1, csr, x0), or of the instruction itself."""
        if self.insn is not None:
            return f".word {hex(self.insn)}  // {self.name}", self.insn
        assert self.csr is not None
        return f"csrrs x1, {hex(self.csr)}, x0  // read {self.name}", enc_csr(self.csr, 2, 1, 0)


def _res() -> dict[str, Res]:
    r = {
        "senvcfg": Res("senvcfg", 0x10A, "S", (0, 62), (0, 62)),
        "henvcfg": Res("henvcfg", 0x60A, "H", (0, 62), None, cond=H),
        "henvcfgh": Res("henvcfgh", 0x61A, "H", (0, 62), None, cond=f"{H} && {RV32}"),
        "siselect": Res("siselect", 0x150, "S", (0, 60), (0, 60)),
        "vsiselect": Res("vsiselect", 0x250, "H", (0, 60), None, cond=H),
        "stopi": Res("stopi", 0xDB0, "S", (0, 59), (0, 59)),
        "hvictl": Res("hvictl", 0x609, "H", (0, 59), None, cond=H),
        "stopei": Res("stopei", 0x15C, "SnoV", (0, 58), (0, 58)),
        "scontext": Res("scontext", 0x5A8, "S", (0, 57), (0, 57)),
        "hcontext": Res("hcontext", 0x6A8, "H", (0, 57), None, cond=H),
        "hedelegh": Res("hedelegh", 0x612, "H", (0, 56), None, cond=f"{H} && {RV32}"),
        "srmcfg": Res("srmcfg", 0x181, "SnoV", (0, 55), None),
        "sctrctl": Res("sctrctl", 0x14E, "S", (0, 54), (0, 54)),
        "sctrstatus": Res("sctrstatus", 0x14F, "S", (0, 54), (0, 54)),
        "sctrdepth": Res("sctrdepth", 0x15F, "SnoV", (0, 54), (0, 54)),
        "vsctrctl": Res("vsctrctl", 0x24E, "H", (0, 54), None, cond=H),
        "sctrclr": Res("sctrclr", None, "S", (0, 54), (0, 54), insn=0x10400073),
        "jvt": Res("jvt", 0x017, "U", (0, 2), (0, 2), (0, 2)),
        "fcsr": Res("fcsr", 0x003, "U", (0, 1), (0, 1), (0, 1), cond="!defined(F_SUPPORTED)"),
    }
    for n in range(4):
        r[f"sstateen{n}"] = Res(f"sstateen{n}", cnum("s", n), "S", (n, 63), (n, 63))
        r[f"hstateen{n}"] = Res(f"hstateen{n}", cnum("h", n), "H", (n, 63), None, cond=H)
        r[f"hstateen{n}h"] = Res(f"hstateen{n}h", cnum("h", n, True), "H", (n, 63), None, cond=f"{H} && {RV32}")
    return r


RES = _res()


# ---------------------------------------------------------------- test files
def new(suite: str, rule: str, required: list[str], boot: str, suffix: str = "", rv64: bool = False) -> TestFile:
    return TestFile(suite, rule, required=required, march=MARCH, boot=boot, pool=POOL_TRAP, suffix=suffix, rv64=rv64)


def word(t: TestFile, stem: str) -> str:
    """A zeroed 8-byte data word (for probe results and CSR snapshots); returns its label."""
    lab = t.label(stem)
    t.extra_data += ["  .p2align 3", f"{lab}: .dword 0"]
    return lab


def cond(t: TestFile, c: str | None) -> AbstractContextManager[None]:
    import contextlib

    return t.only_if(c) if c else contextlib.nullcontext()


# ---------------------------------------------------------------- stateen bit access
def _half(b: int) -> tuple[bool, int]:
    """(in the RV32 high CSR, shift within the RV32 half) of a 64-bit bit position."""
    return b >= 32, b % 32


def bit_op(t: TestFile, kind: str, n: int, b: int, on: bool) -> None:
    """Set or clear bit b of kind-stateen-n. mstateen goes through T-SBI unless the test runs in M-mode."""
    t.comment(f"{cname(kind, n)}[{b}] = {int(on)}")
    via_tsbi = kind == "m" and t.cur != "M"
    for xlen in (64, 32):
        hi, sh = (False, b) if xlen == 64 else _half(b)
        if kind == "s" and hi:
            continue
        with t.only_if(f"__riscv_xlen == {xlen}"):
            if via_tsbi:
                t.li("a1", 1)
                if sh:
                    t.emit(f"slli a1, a1, {sh}")
                t.tsbi_csr("SET" if on else "CLEAR", cname(kind, n, hi).upper(), "a1")
            else:
                t.li("x1", 1)
                if sh:
                    t.emit(f"slli x1, x1, {sh}")
                t.emit(f"{'csrs' if on else 'csrc'} {hex(cnum(kind, n, hi))}, x1  // {cname(kind, n, hi)}")


def read_bit(t: TestFile, kind: str, n: int, b: int, dst: str) -> None:
    """dst = bit b of kind-stateen-n (0 or 1)."""
    via_tsbi = kind == "m" and t.cur != "M"
    for xlen in (64, 32):
        hi, sh = (False, b) if xlen == 64 else _half(b)
        with t.only_if(f"__riscv_xlen == {xlen}"):
            if kind == "s" and hi:
                t.emit(f"li {dst}, 0")
                continue
            if via_tsbi:
                t.tsbi_csr("READ", cname(kind, n, hi).upper())
                t.emit(f"srli {dst}, a0, {sh}")
            else:
                t.emit(f"csrr {dst}, {hex(cnum(kind, n, hi))}  // {cname(kind, n, hi)}")
                if sh:
                    t.emit(f"srli {dst}, {dst}, {sh}")
            t.emit(f"andi {dst}, {dst}, 1")


def snap(t: TestFile, kind: str, n: int) -> str:
    """Save kind-stateen-n (both RV32 halves) to a data word; returns the label."""
    lab = word(t, f"snap_{kind}{n}")
    via_tsbi = kind == "m" and t.cur != "M"
    halves = [(False, 0)] + ([] if kind == "s" else [(True, 4)])
    for xlen in (64, 32):
        with t.only_if(f"__riscv_xlen == {xlen}"):
            for hi, off in halves if xlen == 32 else [(False, 0)]:
                if via_tsbi:
                    t.tsbi_csr("READ", cname(kind, n, hi).upper())
                    t.la("x1", lab)
                    t.emit(f"SREG a0, {off}(x1)")
                else:
                    t.emit(f"csrr x7, {hex(cnum(kind, n, hi))}  // {cname(kind, n, hi)}")
                    t.la("x1", lab)
                    t.emit(f"SREG x7, {off}(x1)")
    return lab


def restore(t: TestFile, kind: str, n: int, lab: str) -> None:
    """Write kind-stateen-n back from snap()'s word (on RV32 the high half first)."""
    t.comment(f"restore {cname(kind, n)}")
    via_tsbi = kind == "m" and t.cur != "M"
    halves = [(False, 0)] + ([] if kind == "s" else [(True, 4)])
    for xlen in (64, 32):
        with t.only_if(f"__riscv_xlen == {xlen}"):
            for hi, off in reversed(halves) if xlen == 32 else [(False, 0)]:
                t.la("x1", lab)
                if via_tsbi:
                    t.emit(f"LREG a1, {off}(x1)")
                    t.tsbi_csr("WRITE", cname(kind, n, hi).upper(), "a1")
                else:
                    t.emit(f"LREG x7, {off}(x1)")
                    t.emit(f"csrw {hex(cnum(kind, n, hi))}, x7  // {cname(kind, n, hi)}")


def write64(t: TestFile, kind: str, n: int, value: int) -> None:
    """Write a 64-bit constant to kind-stateen-n (direct CSR access: M-mode, or h/s from HS). Clobbers x5 only."""
    assert not (kind == "m" and t.cur != "M")
    for xlen in (64, 32):
        with t.only_if(f"__riscv_xlen == {xlen}"):
            if xlen == 64:
                t.load("x5", value, f"{cname(kind, n)} value")
                t.emit(f"csrw {hex(cnum(kind, n))}, x5  // {cname(kind, n)}")
            else:
                if kind != "s":
                    t.load("x5", value >> 32, f"{cname(kind, n, True)} value")
                    t.emit(f"csrw {hex(cnum(kind, n, True))}, x5  // {cname(kind, n, True)}")
                t.load("x5", value & 0xFFFFFFFF, f"{cname(kind, n)} value")
                t.emit(f"csrw {hex(cnum(kind, n))}, x5  // {cname(kind, n)}")


def m_write64(t: TestFile, n: int, value: int) -> None:
    """Write a 64-bit constant to mstateen-n, directly in M-mode or through T-SBI."""
    if t.cur == "M":
        write64(t, "m", n, value)
        return
    for xlen in (64, 32):
        with t.only_if(f"__riscv_xlen == {xlen}"):
            if xlen == 64:
                t.load("a1", value, f"mstateen{n} value")
                t.tsbi_csr("WRITE", f"MSTATEEN{n}", "a1")
            else:
                t.load("a1", value >> 32, f"mstateen{n}h value")
                t.tsbi_csr("WRITE", f"MSTATEEN{n}H", "a1")
                t.load("a1", value & 0xFFFFFFFF, f"mstateen{n} value")
                t.tsbi_csr("WRITE", f"MSTATEEN{n}", "a1")


def read64(t: TestFile, kind: str, n: int, lo: str, hi: str) -> None:
    """lo = kind-stateen-n (RV64: the whole CSR); on RV32 hi = its high half (0 for sstateen)."""
    via_tsbi = kind == "m" and t.cur != "M"
    for xlen in (64, 32):
        with t.only_if(f"__riscv_xlen == {xlen}"):
            for h, reg in [(False, lo)] + ([(True, hi)] if xlen == 32 else []):
                if h and kind == "s":
                    t.emit(f"li {reg}, 0")
                elif via_tsbi:
                    t.tsbi_csr("READ", cname(kind, n, h).upper())
                    t.emit(f"mv {reg}, a0")
                else:
                    t.emit(f"csrr {reg}, {hex(cnum(kind, n, h))}  // {cname(kind, n, h)}")


def check64_masked(t: TestFile, lo: str, hi: str, mask: int, expected: int, desc: str, has_hi: bool = True) -> None:
    """Check (value & mask) == (expected & mask) for a 64-bit value held in lo (RV64) or lo/hi (RV32)."""
    lab = t.label("chk")
    t.emit(f"{lab}:", 0)
    with t.rv64_only():
        t.check_masked(lo, mask, expected & mask, lab, desc)
    with t.rv32_only():
        t.check_masked(lo, mask & 0xFFFFFFFF, expected & mask & 0xFFFFFFFF, lab, f"{desc} (low half)")
        if has_hi:
            t.check_masked(hi, mask >> 32, (expected & mask) >> 32, lab, f"{desc} (high half)")


def check_subset(t: TestFile, a: tuple[str, str], b: tuple[str, str], desc: str, has_hi: bool = True) -> None:
    """Check (a & ~b) == 0 for 64-bit values in register pairs (RV64 uses the first register). Clobbers x1."""
    lab = t.label("sub")
    t.emit(f"{lab}:", 0)
    t.emit(f"not x1, {b[0]}")
    t.emit(f"and x1, x1, {a[0]}")
    with t.rv32_only():
        if has_hi:
            t.emit(f"not x5, {b[1]}")
            t.emit(f"and x5, x5, {a[1]}")
            t.emit("or x1, x1, x5")
    t.emit("seqz x1, x1")
    t.check_bool("x1", lab, desc)


# ---------------------------------------------------------------- probes and dynamic windows
def probe(t: TestFile, mode: str, line: str, enc: int, desc: str) -> str:
    """Run one access in `mode` (from the current mode) in a window that permits illegal-instruction, and store
    1 (no trap) or 0 (trap) in a data word. Returns the word's label."""
    lab = word(t, "avail")
    alts: list = ["ok", ILLEGAL] if mode in ("S", "M", "U") else ["ok", ILLEGAL, VIRTUAL]
    t.window(mode, [line], alts, f"probe: {desc}", [0, enc])
    t.emit("addi x7, x14, 1")
    t.emit("seqz x7, x7")
    t.la("x1", lab)
    t.emit("SREG x7, 0(x1)")
    return lab


def probe_res(t: TestFile, r: Res, mode: str = "S") -> str:
    line, enc = r.read()
    return probe(t, mode, line, enc, f"{r.name} accessible in {mode}-mode at the boot configuration")


def load_word(t: TestFile, reg: str, lab: str) -> None:
    t.la(reg, lab)
    t.emit(f"LREG {reg}, 0({reg})")


def predict(t: TestFile, mode: str, level: str, vgate: str | None = None) -> None:
    """x1 = the expected AI_OUTCOME x14 (-1 for no trap, else the cause) of an access from `mode` to state of
    `level`, given x6 = m, x8 = h, x9 = s (each 0 or 1). Clobbers x7."""
    if mode in ("M", "S"):
        ok: list[str] | None = ["x6"]
        if MUT == "hs_gated_by_h" and mode == "S" and level in ("U", "S"):
            ok = ["x6", "x8"]
    elif mode == "U":
        ok = ["x6", "x9"] if level == "U" else None
        if ok and MUT == "u_ignores_sstateen":
            ok = ["x6"]
        if ok and MUT == "u_ignores_mstateen":  # with sweep() keeping x9 = the sstateen bit set before m cleared
            ok = ["x9"]
    elif mode == "VS":
        ok = ["x6", "x8"] if level in ("U", "S") else None
        if ok and MUT == "vs_ignores_hstateen":
            ok = ["x6"]
        if MUT == "vs_snov_allowed" and level == "SnoV":
            ok = ["x6", "x8"]
        if ok and vgate:  # VS access also needs a condition probed at run time (stopei: a valid hstatus.VGEIN)
            load_word(t, "x15", vgate)
            ok = [*ok, "x15"]
    else:  # VU
        ok = ["x6", "x8", "x9"] if level == "U" else None
        if ok and MUT == "vu_ignores_sstateen":
            ok = ["x6", "x8"]
    if ok:
        t.emit(f"mv x1, {ok[0]}")
        for r in ok[1:]:
            t.emit(f"and x1, x1, {r}")
        t.emit("neg x1, x1")
    else:
        t.emit("li x1, 0")
    virt = mode in ("VS", "VU")
    if virt and MUT == "virtual_as_illegal":
        virt = False
    if virt and MUT == "m0_virtual":
        t.li("x7", VIRTUAL)
    elif virt:
        # 2 + 20*m: virtual-instruction (22) when the access is HS-qualified (m=1), else illegal (2)
        t.emit("slli x7, x6, 2")
        t.emit("add x7, x7, x6")
        t.emit("slli x7, x7, 2")
        t.emit(f"addi x7, x7, {ILLEGAL}")
        if MUT == "vu_sstateen_illegal" and mode == "VU" and level == "U":
            # a VU access blocked only by sstateen raises illegal-instruction: subtract 20 when m & h & ~s
            t.emit("xori x5, x9, 1")
            t.emit("and x5, x5, x8")
            t.emit("and x5, x5, x6")
            t.emit("slli x15, x5, 2")
            t.emit("add x15, x15, x5")
            t.emit("slli x15, x15, 2")
            t.emit("sub x7, x7, x15")
    else:
        t.li("x7", ILLEGAL)
    t.emit("or x1, x1, x7")


def possible(mode: str, level: str) -> list:
    if mode in ("M", "S"):
        return ["ok", ILLEGAL]
    if mode == "U":
        return ["ok", ILLEGAL] if level == "U" else [ILLEGAL]
    if (mode == "VS" and level in ("U", "S")) or (mode == "VU" and level == "U"):
        return ["ok", ILLEGAL, VIRTUAL]
    return [ILLEGAL, VIRTUAL]


def dyn_window(
    t: TestFile,
    mode: str,
    line: str,
    enc: int,
    level: str,
    desc: str,
    pre: Sequence[str] = (),
    vgate: str | None = None,
) -> str:
    """One access in `mode` in a trap window; its outcome must be the cause predict() gives for x6/x8/x9.
    A trap must leave xepc at the instruction, xtval 0 or the instruction bits, and xPP/xPV naming `mode`."""
    alts = possible(mode, level)
    if alts == [ILLEGAL]:
        return t.window(mode, [line], ILLEGAL, desc, [0, enc])
    lab = t.label(f"in_{mode}")
    for p in pre:
        t.emit(p)
    t.allow(1)
    if mode != t.cur:
        t.enter(mode)
    t.emit(f"{lab}:", 0)
    t.emit(line)
    if mode != t.cur:
        t.leave()
    t.emit("AI_OUTCOME", 20)
    full = f"{desc} in {mode}-mode"
    predict(t, mode, level, vgate)
    t.emit("xor x1, x1, x14")
    t.emit("seqz x1, x1")
    t.check_bool(
        "x1",
        lab,
        f"{full}: outcome is the one the stateen bits give (m=x6, h=x8, s=x9: no trap, 2 illegal or 22 virtual)",
    )
    t.check("x13", [0, 1], lab, f"{full}: number of traps")
    skip, done = t.label("notrap"), t.label("checked")
    t.emit("li x5, -1")
    t.emit(f"beq x14, x5, {skip}")
    first = len(t.table)
    t.emit("AI_LOG(x15, TRAPLOG_EPC)", 10)
    t.check("x15", lab, lab, f"{full}: xepc is the trapping instruction")
    t.emit("AI_LOG(x15, TRAPLOG_TVAL)", 10)
    t.check("x15", [0, enc], lab, f"{full}: xtval is 0 or the instruction bits")
    t.emit("AI_ORIGIN", 25)
    t.check("x15", {"U": 0, "S": 1, "M": 3, "VU": 4, "VS": 5}[mode], lab, f"{full}: xPP/xPV record {mode}-mode")
    t.emit(f"j {done}")
    t.emit(f"{skip}:", 0)
    t.code += t._skip_lines(first, len(t.table))
    t.emit(f"{done}:", 0)
    return lab


# ---------------------------------------------------------------- gating sweeps
def load_m(t: TestFile, r: Res, avail: str, smstateen: bool) -> None:
    """x6 = effective machine-level enable: the mstateen bit (Smstateen tests) AND the boot-time probe."""
    if smstateen:
        read_bit(t, "m", r.m[0], r.m[1], "x6")
        load_word(t, "x7", avail)
        t.emit("and x6, x6, x7")
    else:
        load_word(t, "x6", avail)


def load_hs(t: TestFile, r: Res) -> None:
    """x8 = the hstateen bit (H only; 1 when the state has none), x9 = the sstateen bit (user state; else 1)."""
    t.li("x8", 1)
    if r.h:
        with t.only_if(H):
            read_bit(t, "h", r.h[0], r.h[1], "x8")
    t.li("x9", 1)
    if r.s:
        read_bit(t, "s", r.s[0], r.s[1], "x9")


def windows(t: TestFile, r: Res, modes: Sequence[str], desc: str) -> None:
    line, enc = r.read()
    vg = getattr(r, "vgate", None)
    for mode in modes:
        if mode in ("VS", "VU"):
            with t.only_if(H):
                dyn_window(t, mode, line, enc, r.level, f"{r.name}: {desc}", vgate=vg)
        else:
            dyn_window(t, mode, line, enc, r.level, f"{r.name}: {desc}")


MODES = ("S", "U", "VS", "VU")


def sweep(
    t: TestFile,
    r: Res,
    vary: str,
    *,
    smstateen: bool,
    states: Sequence[int] = (1, 0, 1),
    modes: Sequence[str] = MODES,
    avail: str | None = None,
    extra: Callable[[int], None] | None = None,
    bit: tuple[int, int] | None = None,
) -> str:
    """Gate sweep of one resource: probe it at the boot configuration, then set the stateen bit `vary` ('m', 'h'
    or 's') to each of `states` and access the state from each mode. Expectations use the bits read back, so
    read-only bits are handled. extra(state) runs more windows after each state's. Returns the probe label."""
    with cond(t, r.cond):
        t.blank()
        t.comment(f"---- {r.name}: sweep of the {vary}stateen bit")
        if avail is None:
            avail = probe_res(t, r)
        if smstateen:
            # A writable or read-only-one mstateen bit implies the state is implemented (unimplemented-state
            # bits are read-only zero), so the boot probe must have succeeded: check avail | !m.
            read_bit(t, "m", r.m[0], r.m[1], "x6")
            load_word(t, "x7", avail)
            t.emit("xori x6, x6, 1")
            t.emit("or x6, x6, x7")
            lab = t.label("impl")
            t.emit(f"{lab}:", 0)
            t.check_bool("x6", lab, f"{r.name}: mstateen bit {r.m[1]} is 1 only if {r.name} is accessible from S-mode")
        load_m(t, r, avail, smstateen)
        load_hs(t, r)
        kind_bit = bit or {"m": r.m, "h": r.h, "s": r.s}[vary]
        assert kind_bit is not None
        for st in states:
            if vary == "h":
                with t.only_if(H):
                    bit_op(t, "h", kind_bit[0], kind_bit[1], bool(st))
                    read_bit(t, "h", kind_bit[0], kind_bit[1], "x8")
            elif vary == "s":
                bit_op(t, "s", kind_bit[0], kind_bit[1], bool(st))
                read_bit(t, "s", kind_bit[0], kind_bit[1], "x9")
            else:
                bit_op(t, "m", kind_bit[0], kind_bit[1], bool(st))
                load_m(t, r, avail, smstateen)
                if (st or kind_bit[1] != 63) and not (MUT == "u_ignores_mstateen" and not st):
                    # Lower-level bits may change with the mstateen bit (they read zero while it is 0). With
                    # mstateenN[63] cleared, hstateenN/sstateenN cannot be read from S-mode; they do not
                    # matter then (m=0 decides) unless bit 63 is read-only one, which the H extension's
                    # mstateen_bit_63_roz leaves possible only as RO1 with hstateen still readable.
                    load_hs(t, r)
            windows(t, r, modes, f"{vary}stateen{kind_bit[0]}[{kind_bit[1]}] written {st}")
            if extra:
                extra(st)
    return avail
