# SPDX-License-Identifier: Apache-2.0
"""Helpers for the Sdtrig suite (gen_Sdtrig.py): trigger CSR access from M-mode or through T-SBI, run-time trigger
probing, breakpoint windows that accept every legal trigger timing, and the trap-log readers the suite needs.

Everything about the trigger module is probed at run time: a test looks for a trigger (among the first NPROBE) whose
tdata1 keeps the requested configuration after a WARL write, and passes vacuously when none does. No UDB parameter
is used. Probing uses no table entries, so a run-time branch can skip it without unbalancing the table.

Field positions are from xml/hwbp_registers.xml (riscv-debug-spec PR 1220, afd3901).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aigen import NO_TRAP, ORIGIN, TestFile, X

if TYPE_CHECKING:
    from collections.abc import Callable

    from aigen import Expect

# ---------------------------------------------------------------- CSRs and fields
CSR = {
    "tselect": "CSR_TSELECT",
    "tdata1": "CSR_TDATA1",
    "tdata2": "CSR_TDATA2",
    "tdata3": "CSR_TDATA3",
    "tinfo": "CSR_TINFO",
    "tcontrol": "CSR_TCONTROL",
    "mcontext": "CSR_MCONTEXT",
    "scontext": "CSR_SCONTEXT",
    "hcontext": "0x6a8",
    "mscontext": "CSR_MSCONTEXT",
}
NPROBE = 4  # triggers searched for a usable one

# mcontrol6 (type 6)
MC6 = 6
UNCERTAIN, HIT1, VS, VU, HIT0, SELECT = 1 << 26, 1 << 25, 1 << 24, 1 << 23, 1 << 22, 1 << 21
CHAIN, M, UNCERTAINEN, S, U, EXEC, STORE, LOAD = 1 << 11, 1 << 6, 1 << 5, 1 << 4, 1 << 3, 4, 2, 1
MODEBITS6 = {"M": M, "S": S, "U": U, "VS": VS, "VU": VU}


def SIZE(s: int) -> int:
    return s << 16


def ACTION(a: int) -> int:
    return a << 12


def MATCH(m: int) -> int:
    return m << 7


MC6_MASK = VS | VU | SELECT | (7 << 16) | (0xF << 12) | CHAIN | (0xF << 7) | M | UNCERTAINEN | S | U | 7
# icount (type 3)
IC = 3
IC_VS, IC_VU, IC_HIT, IC_M, IC_PENDING, IC_S, IC_U = 1 << 26, 1 << 25, 1 << 24, 1 << 9, 1 << 8, 1 << 7, 1 << 6
MODEBITS_IC = {"M": IC_M, "S": IC_S, "U": IC_U, "VS": IC_VS, "VU": IC_VU}


def COUNT(n: int) -> int:
    return n << 10


IC_MASK = IC_VS | IC_VU | (0x3FFF << 10) | IC_M | IC_S | IC_U | 0x3F
# itrigger (4) / etrigger (5): hit at XLEN-6, vs 12, vu 11, nmi 10 (itrigger), m 9, s 7, u 6, action 5:0
IT, ET, TMEXT = 4, 5, 7
IE_VS, IE_VU, IE_NMI, IE_M, IE_S, IE_U = 1 << 12, 1 << 11, 1 << 10, 1 << 9, 1 << 7, 1 << 6
MODEBITS_IE = {"M": IE_M, "S": IE_S, "U": IE_U, "VS": IE_VS, "VU": IE_VU}
IE_MASK = IE_VS | IE_VU | IE_NMI | IE_M | IE_S | IE_U | 0x3F
IE_HIT = X(1 << 26, 1 << 58)
DMODE = X(1 << 27, 1 << 59)
TYPE_SHIFT = "(__riscv_xlen-4)"
TYPE_MASK = X(0xF << 28, 0xF << 60)


def TYPE(n: int) -> X:
    return X(n << 28, n << 60)


def tdata1(typ: int, low: int) -> X:
    return X((typ << 28) | low, (typ << 60) | low)


BREAKPOINT = 3
H = "defined(H_SUPPORTED)"
S_OK = "defined(S_SUPPORTED)"
U_OK = "defined(U_SUPPORTED)"


class SdFile(TestFile):
    """A TestFile that can define SDTRIG_XEPC_IN_VECTOR before the framework headers: the M-mode handler then
    returns to an S trap vector without advancing xepc, so an itrigger/etrigger breakpoint taken to M before the
    first instruction of the S handler lets the S handler run for the original trap."""

    def __init__(self, *a: object, vector: bool = False, **kw: object) -> None:
        super().__init__(*a, **kw)  # type: ignore[arg-type]
        self.vector = vector

    def render(self) -> str:
        s = super().render()
        if self.vector:
            s = s.replace("#define SIGUPD_COUNT 0\n", "#define SIGUPD_COUNT 0\n#define SDTRIG_XEPC_IN_VECTOR\n", 1)
        return s


# ---------------------------------------------------------------- CSR access
class Acc:
    """Trigger-CSR access: direct in an M-boot test, through T-SBI in an S-boot test. T-SBI clobbers a0/a1; the
    handler restores x1 and x6-x9."""

    def __init__(self, t: TestFile) -> None:
        self.t = t
        self.m = t.boot == "M"

    def w(self, csr: str, reg: str) -> None:
        if self.m:
            self.t.emit(f"csrw {CSR[csr]}, {reg}")
        else:
            self.t.tsbi_csr("WRITE", csr, reg)

    def s(self, csr: str, reg: str) -> None:
        if self.m:
            self.t.emit(f"csrs {CSR[csr]}, {reg}")
        else:
            self.t.tsbi_csr("SET", csr, reg)

    def c(self, csr: str, reg: str) -> None:
        if self.m:
            self.t.emit(f"csrc {CSR[csr]}, {reg}")
        else:
            self.t.tsbi_csr("CLEAR", csr, reg)

    def r(self, dst: str, csr: str) -> None:
        if self.m:
            self.t.emit(f"csrr {dst}, {CSR[csr]}")
        else:
            self.t.tsbi_csr("READ", csr)
            self.t.emit(f"mv {dst}, a0")

    def w0(self, csr: str) -> None:
        if self.m:
            self.t.emit(f"csrw {CSR[csr]}, x0")
        else:
            self.t.tsbi_csr("WRITE", csr, imm=0)


def mk(t: TestFile, reg: str, typ: int, low: int, tmp: str = "x5", hi: X | None = None) -> None:
    """reg = a tdata1 value of type typ with the low field bits `low` (< 2^27), built without the table.
    hi: DMODE or IE_HIT, ORed in."""
    t.emit(f"li {reg}, {typ}")
    t.emit(f"slli {reg}, {reg}, {TYPE_SHIFT}")
    if low:
        t.emit(f"LI({tmp}, {low:#x})", 2)
        t.emit(f"or {reg}, {reg}, {tmp}")
    if hi is not None:
        assert hi in (DMODE, IE_HIT)
        t.emit(f"li {tmp}, 1")
        t.emit(f"slli {tmp}, {tmp}, {'(__riscv_xlen-5)' if hi == DMODE else '(__riscv_xlen-6)'}")
        t.emit(f"or {reg}, {reg}, {tmp}")


def mask_of(typ: int) -> int:
    return {MC6: MC6_MASK, IC: IC_MASK, IT: IE_MASK, ET: IE_MASK}.get(typ, 0)


def set_t2(t: TestFile, t2: str | list[str] | int, reg: str = "x8") -> None:
    """reg = a tdata2 value: a label expression (LA), a small constant, or assembly lines that set x8."""
    if isinstance(t2, list):
        assert reg == "x8"
        for ln in t2:
            t.emit(ln)
    elif isinstance(t2, int):
        t.emit(f"LI({reg}, {t2:#x})", 2)
    else:
        t.emit(f"LA({reg}, {t2})", 2)


# ---------------------------------------------------------------- probing
def probe(
    t: TestFile,
    acc: Acc,
    cfgs: list[tuple[int, int]],
    tdata2: list[str | list[str] | int | None] | None = None,
    found: str = "x1",
    n: int = NPROBE,
    masks: list[int] | None = None,
) -> None:
    """Find the first i < n such that triggers i, i+1, ... accept cfgs[0], cfgs[1], ... (type and the bits of the
    type's mask read back as written, after tdata1=0 and tdata2 = tdata2[k], or tdata2 left alone for None).
    found = i+1, or 0 when there is none. Every probed trigger is left disabled (tdata1 = 0). tselect is left
    pointing anywhere. Uses x5-x9 and no table entries."""
    t2s = tdata2 or [None] * len(cfgs)
    masks = masks or [mask_of(typ) for typ, _ in cfgs]
    done = t.label("probed")
    t.comment(
        f"probe: first trigger index i < {n} whose triggers accept " + ", ".join(f"type {a} {b:#x}" for a, b in cfgs)
    )
    t.emit(f"li {found}, 0")
    for i in range(n):
        nxt = t.label(f"probe_next{i}")
        for k, (typ, low) in enumerate(cfgs):
            t.emit(f"li x6, {i + k}")
            acc.w("tselect", "x6")
            acc.r("x7", "tselect")
            t.emit(f"bne x7, x6, {done}  // triggers are contiguous from 0: a missing index ends the search")
            acc.w0("tdata1")
            if t2s[k] is not None:
                set_t2(t, t2s[k])  # type: ignore[arg-type]
                acc.w("tdata2", "x8")
            mk(t, "x8", typ, low)
            acc.w("tdata1", "x8")
            acc.r("x7", "tdata1")
            acc.w0("tdata1")
            mk(t, "x9", 0xF, masks[k])  # type field and the configured bits
            t.emit("and x7, x7, x9")
            t.emit(f"bne x7, x8, {nxt}")
        t.emit(f"li {found}, {i + 1}")
        t.emit(f"j {done}")
        t.emit(f"{nxt}:", 0)
    t.emit(f"{done}:", 0)


def select(t: TestFile, acc: Acc, found: str = "x1", k: int = 0) -> None:
    """tselect = found - 1 + k."""
    t.emit(f"addi x6, {found}, {k - 1}")
    acc.w("tselect", "x6")


def arm(
    t: TestFile,
    acc: Acc,
    typ: int,
    low: int,
    t2: str | list[str] | int | None = None,
    found: str = "x1",
    k: int = 0,
    hi: X | None = None,
) -> None:
    """Select trigger found-1+k and program it as the spec recommends: tdata1 = 0, tdata2, tdata1 = config."""
    select(t, acc, found, k)
    acc.w0("tdata1")
    if t2 is not None:
        set_t2(t, t2)
        acc.w("tdata2", "x8")
    mk(t, "x8", typ, low, hi=hi)
    acc.w("tdata1", "x8")


def disarm(t: TestFile, acc: Acc, found: str = "x1", k: int = 0) -> None:
    select(t, acc, found, k)
    acc.w0("tdata1")


def read_tdata1(t: TestFile, acc: Acc, dst: str, found: str = "x1", k: int = 0) -> None:
    select(t, acc, found, k)
    acc.r(dst, "tdata1")


def hit6(t: TestFile, dst: str, src: str) -> None:
    """dst = mcontrol6 {hit1, hit0} from tdata1 value src (dst may equal src; uses x5)."""
    t.emit(f"srli x5, {src}, 24")
    t.emit("andi x5, x5, 2  // hit1 (bit 25) -> bit 1")
    t.emit(f"srli {dst}, {src}, 22")
    t.emit(f"andi {dst}, {dst}, 1  // hit0 (bit 22)")
    t.emit(f"or {dst}, {dst}, x5")


# ---------------------------------------------------------------- trap log
def resume(t: TestFile, lab: str) -> None:
    """The next logged trap resumes at lab (rvtest_trap_resume)."""
    t.emit(f"LA(x4, {lab})", 2)
    t.emit("LA(x5, rvtest_trap_resume)", 2)
    t.emit("SREG x4, 0(x5)")


def clear_resume(t: TestFile) -> None:
    t.emit("LA(x4, rvtest_trap_resume)", 2)
    t.emit("SREG x0, 0(x4)")


def log(t: TestFile, reg: str, word: str, back: int = 0) -> None:
    """reg = word TRAPLOG_<word> of the last logged trap (back=0) or of an earlier one (back=1, 2, 3). Uses x4/x5."""
    if back == 0:
        t.emit(f"AI_LOG({reg}, TRAPLOG_{word})", 10)
        return
    t.emit("LA(x4, rvtest_trap_count)", 2)
    t.emit("LREG x5, 0(x4)")
    t.emit(f"addi x5, x5, {-1 - back}")
    t.emit("andi x5, x5, RVTEST_TRAP_LOG_N-1")
    t.emit("slli x5, x5, TRAPLOG_ENTRY_SHIFT")
    t.emit("LA(x4, rvtest_trap_log)", 2)
    t.emit("add x4, x4, x5")
    t.emit(f"LREG {reg}, TRAPLOG_{word}*REGWIDTH(x4)")


def handler(t: TestFile, reg: str, back: int = 0) -> None:
    """reg = the mode of the handler that logged the trap: 3 M, 1 S/HS, 2 VS."""
    log(t, reg, "VECT", back)
    t.emit(f"andi {reg}, {reg}, 3")


def origin(t: TestFile, back: int = 0) -> None:
    """x15 = the mode a logged trap came from (as AI_ORIGIN, for entry `back`). Clobbers x13/x14."""
    if back == 0:
        t.emit("AI_ORIGIN", 25)
        return
    # point AI_LOG's entry computation at an older entry: temporarily decrement rvtest_trap_count
    t.emit("LA(x4, rvtest_trap_count)", 2)
    t.emit("LREG x5, 0(x4)")
    t.emit(f"addi x5, x5, {-back}")
    t.emit("SREG x5, 0(x4)")
    t.emit("AI_ORIGIN", 25)
    t.emit("LA(x4, rvtest_trap_count)", 2)
    t.emit("LREG x5, 0(x4)")
    t.emit(f"addi x5, x5, {back}")
    t.emit("SREG x5, 0(x4)")


# ---------------------------------------------------------------- breakpoint windows
def fire(
    t: TestFile,
    mode: str,
    body: list[str],
    expect: bool | None,
    desc: str,
    tval: Expect | tuple[str, int] | None = None,
    epc: str | None = "range",
    off: str | None = None,
) -> tuple[str, str]:
    """Run body in `mode` (entered from t.cur) with up to one trap permitted; a trap resumes at the end of body.

    expect: True (exactly one breakpoint), False (no trap) or None (either). For a breakpoint the log is checked:
    cause 3, it came from `mode`, xtval is one of tval (when given; (address, n) means 0 or any of the n bytes
    from address, the bytes an access touched) and xepc is
      "range": anywhere from the first instruction of body to its end (a trigger may fire before the instruction
               that matched or after it and later instructions retired),
      a label: exactly that address, or None: not checked.
    off: a register that receives xepc - (address of the first body instruction), or -1 when there was no trap
    (for later consistency checks). Returns (first-instruction label, end label)."""
    lab, end = t.label(f"at_{mode}"), t.label("end")
    if mode == "S" and t.cur == "S":
        t.emit("csrsi sstatus, 2  // SIE = 1 (sie = 0): an xret from a lower-mode window may have cleared it")
    resume(t, end)
    t.allow(1)
    if mode != t.cur:
        t.enter(mode)
    t.emit(f"{lab}:", 0)
    for ln in body:
        t.emit(ln)
    t.emit(f"{end}:", 0)
    if mode != t.cur:
        t.leave()
    clear_resume(t)
    t.emit("AI_OUTCOME", 20)
    full = f"{desc} in {mode}-mode"
    if expect is None:
        t.check("x13", [0, 1], lab, f"{full}: number of traps")
        t.check("x14", [NO_TRAP, BREAKPOINT], lab, f"{full}: outcome (breakpoint, or all ones for no trap)")
    else:
        t.check("x13", int(expect), lab, f"{full}: number of traps")
        t.check("x14", BREAKPOINT if expect else NO_TRAP, lab, f"{full}: outcome (breakpoint, or all ones for no trap)")
    if off:
        t.emit(f"li {off}, -1")
    if expect is False:
        return lab, end
    skip, done = t.label("notrap"), t.label("checked")
    if expect is None:
        t.emit("li x5, -1")
        t.emit(f"beq x14, x5, {skip}")
    first = len(t.table)
    t.emit("AI_LOG(x15, TRAPLOG_EPC)", 10)
    if off:
        t.emit(f"LA(x13, {lab})", 2)
        t.emit(f"sub {off}, x15, x13")
    if epc == "range":
        t.emit(f"LA(x13, {lab})", 2)
        t.emit("sub x15, x15, x13  // xepc - first")
        t.emit(f"LA(x14, {end})", 2)
        t.emit("sub x14, x14, x13  // end - first")
        t.emit("sltu x15, x14, x15")
        t.emit("xori x15, x15, 1")
        t.check_bool("x15", lab, f"{full}: first <= xepc <= end of the window (before or after the matching insn)")
    elif epc is not None:
        t.check("x15", epc, lab, f"{full}: xepc is {epc}")
    if isinstance(tval, tuple):
        addr, nbytes = tval
        t.emit("AI_LOG(x15, TRAPLOG_TVAL)", 10)
        t.emit(f"LA(x13, {addr})", 2)
        t.emit("sub x14, x15, x13  // xtval - address")
        t.emit(f"sltiu x14, x14, {nbytes}  // address <= xtval < address + size")
        t.emit("seqz x15, x15")
        t.emit("or x15, x15, x14")
        t.check_bool("x15", lab, f"{full}: xtval is 0 or one of the {nbytes} bytes accessed")
    elif tval is not None:
        t.emit("AI_LOG(x15, TRAPLOG_TVAL)", 10)
        t.check("x15", tval, lab, f"{full}: xtval is one of its legal values")
    t.emit("AI_ORIGIN", 25)
    t.check("x15", ORIGIN[mode], lab, f"{full}: the breakpoint came from {mode}-mode (0 U, 1 S, 3 M, 4 VU, 5 VS)")
    if expect is None:
        t.emit(f"j {done}")
        t.emit(f"{skip}:", 0)
        t.code += t._skip_lines(first, len(t.table))
        t.emit(f"{done}:", 0)
    return lab, end


def hit_epc_ok(t: TestFile, hit: str, off: str, ilen: int = 4) -> None:
    """x15 = 1 when the mcontrol6 hit field (in reg hit) agrees with xepc - first (in reg off), where the matching
    instruction is the first of the window and ilen bytes long: hit=1 (before) needs off=0, hit=3 (immediately
    after) off=ilen, hit=2 (after) off > ilen; hit=0 (not implemented) passes. Uses x5, x13, x14."""
    t.emit(f"seqz x15, {hit}  // hit = 0: nothing to check")
    t.emit(f"addi x13, {hit}, -1")
    t.emit("seqz x13, x13")
    t.emit(f"seqz x14, {off}")
    t.emit("and x13, x13, x14  // hit = 1 and xepc = first")
    t.emit("or x15, x15, x13")
    t.emit(f"addi x13, {hit}, -3")
    t.emit("seqz x13, x13")
    t.emit(f"addi x14, {off}, -{ilen}")
    t.emit("seqz x14, x14")
    t.emit("and x13, x13, x14  // hit = 3 and xepc = first + ilen")
    t.emit("or x15, x15, x13")
    t.emit(f"addi x13, {hit}, -2")
    t.emit("seqz x13, x13")
    t.emit(f"li x5, {ilen}")
    t.emit(f"slt x14, x5, {off}")
    t.emit("and x13, x13, x14  // hit = 2 and xepc beyond the next instruction")
    t.emit("or x15, x15, x13")


# ---------------------------------------------------------------- modes and enables
def m_prologue(t: TestFile) -> None:
    """M-boot tests: no interrupt is enabled (mie = 0), and mstatus.MIE = 1 so M-mode triggers are armed on harts
    that suppress action=0 triggers while MIE = 0. medeleg = mideleg = 0 (the M boot already has them 0)."""
    t.comment("mie = 0, mstatus.MIE = 1: M-mode triggers are armed on harts that gate them with MIE")
    t.emit("csrw mie, x0")
    with t.only_if(S_OK):
        t.emit("csrw medeleg, x0")
        t.emit("csrw mideleg, x0")
    t.emit("csrsi mstatus, 8")


def s_prologue(t: TestFile) -> None:
    """S-boot tests: no S-level interrupt is enabled (sie = 0), so sstatus.SIE can be set to arm S-mode triggers on
    harts that suppress them while SIE = 0 (breakpoints delegated with medeleg[3] = 1)."""
    t.comment("sie = 0, sstatus.SIE = 1: S-mode triggers are armed on harts that gate them with SIE")
    t.emit("csrw sie, x0")
    t.emit("csrsi sstatus, 2")


def has_csr(t: TestFile, csr: str, flag: str) -> None:
    """flag = 1 when csr reads without a trap in the current mode (illegal instruction otherwise). Uses a trap
    window (x13-x15)."""
    lab = t.label(f"has_{csr}")
    t.allow(1)
    t.emit(f"{lab}:", 0)
    t.emit(f"csrr x5, {CSR[csr]}")
    t.outcome(["ok", 2], lab, f"{csr} read (optional CSR)")
    t.emit("addi x14, x14, 1")
    t.emit(f"seqz {flag}, x14")


def either(t: TestFile, reg: str, if_set: Callable[[], object], if_clear: Callable[[], object] | None = None) -> None:
    """TestFile.either, except that either branch may hold table entries under extra #if conditions."""
    clear, done = t.label("clear"), t.label("done")
    t.emit(f"beqz {reg}, {clear}")
    a = len(t.table)
    if_set()
    b = len(t.table)
    hole = len(t.code)
    t.code.append("")
    t.emit(f"j {done}")
    t.emit(f"{clear}:", 0)
    t.code += skip(t, a, b)
    if if_clear:
        if_clear()
    t.code[hole] = "\n".join(skip(t, b, len(t.table)))
    t.emit(f"{done}:", 0)


def skip(t: TestFile, lo: int, hi: int) -> list[str]:
    """AI_SKIP over table entries lo..hi-1, grouped by their extra preprocessor conditions."""
    groups: dict[tuple[str, ...], int] = {}
    for _, conds in t.table[lo:hi]:
        extra = tuple(c for c in conds if c not in t._conds)
        groups[extra] = groups.get(extra, 0) + 1
    out = []
    for conds, n in groups.items():
        if conds:
            out.append("#if " + " && ".join(f"({c})" for c in conds))
        out.append(f"  AI_SKIP({n})" if n * 8 < 2048 else f"  AI_SKIP_BIG({n})")
        if conds:
            out.append("#endif")
    return out
