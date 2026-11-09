# SPDX-License-Identifier: Apache-2.0
"""Shared helpers for the Sm and PMP rule-derived suites (gen_Sm.py, pmplib.py).

Every test boots to M-mode (boot="M") and requires Sm. Lower modes are entered with MRET (or SRET) and left
with a T-SBI GOTO. Optional features are probed at run time; the configuration inputs are only the
X_SUPPORTED macros, __riscv_xlen and the DUT's rvmodel_macros.h addresses.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent))
from aigen import POOL_TRAP, TestFile, X

if TYPE_CHECKING:
    from collections.abc import Callable

    from aigen import Expect, Value

    Form = tuple[str, int, int, int, str]  # CSR instruction form (asm template, funct3, rd, rs1/uimm, kind)

ISSUE = "https://github.com/riscv/riscv-isa-manual/issues/"
MARCH = "rv${XLEN}i_zicsr_zifencei"
REQ = ["I", "Sm"]
S = "defined(S_SUPPORTED)"
U = "defined(U_SUPPORTED)"
NO_S = "!defined(S_SUPPORTED)"
NO_U = "!defined(U_SUPPORTED)"
RV64 = "__riscv_xlen == 64"
RV32 = "__riscv_xlen == 32"
ALL = X((1 << 32) - 1, (1 << 64) - 1)
MSB = X(1 << 31, 1 << 63)
MODE_COND = {"M": None, "S": S, "U": U}

# mstatus fields
SIE, MIE, SPIE, UBE, MPIE, SPP = 1 << 1, 1 << 3, 1 << 5, 1 << 6, 1 << 7, 1 << 8
VS, MPP, FS, XS = 3 << 9, 3 << 11, 3 << 13, 3 << 15
MPRV, SUM, MXR, TVM, TW, TSR = 1 << 17, 1 << 18, 1 << 19, 1 << 20, 1 << 21, 1 << 22


def mut() -> str:
    """The mutant being generated (mutate.py sets AI_MUTANT), read at call time."""
    return os.environ.get("AI_MUTANT", "")


def icause(c: int) -> X:
    return X((1 << 31) | c, (1 << 63) | c)


def _rules() -> dict[str, dict[str, str]]:
    return RULES


def rule_text(rule: str) -> tuple[str, str]:
    r = _rules()[rule]
    return r["text"], r["src"]


def new(
    suite: str,
    rule: str,
    required: list[str] | None = None,
    march: str = MARCH,
    rv64: bool = False,
    pool: list[str] | None = None,
) -> TestFile:
    return TestFile(
        suite, rule, required=list(required or REQ), march=march, boot="M", pool=list(pool or POOL_TRAP), rv64=rv64
    )


def describe(t: TestFile, plan: str, context: str = "", issues: str = "", rule: str | None = None) -> None:
    text, src = rule_text(rule or t.rule)
    t.describe(rule_text=text, source=src, context=context, issues=issues, plan=plan)


def guard(t: TestFile, cond: str | None, body: Callable[[], object]) -> None:
    if cond:
        with t.only_if(cond):
            body()
    else:
        body()


def each_mode(t: TestFile, body: Callable[[str], object], modes: tuple[str, ...] = ("M", "S", "U")) -> None:
    """Run body(mode) for each mode the hart implements (S and U under #if)."""
    for m in modes:
        guard(t, MODE_COND[m], lambda m=m: body(m))


# ---------------------------------------------------------------- encodings
def enc_csr(csr: int, f3: int, rd: int, rs1: int) -> int:
    return (csr << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | 0x73


# CSR instruction forms: (asm template, funct3, rd, rs1-or-uimm, kind). rd x7, rs x6, uimm 0x15.
FORMS = [
    ("csrrs x7, {c}, x0", 2, 7, 0, "read (csrrs rs1=x0)"),
    ("csrrw x0, {c}, x6", 1, 0, 6, "write (csrrw rd=x0)"),
    ("csrrw x7, {c}, x6", 1, 7, 6, "swap (csrrw)"),
    ("csrrs x7, {c}, x6", 2, 7, 6, "set (csrrs)"),
    ("csrrc x7, {c}, x6", 3, 7, 6, "clear (csrrc)"),
    ("csrrwi x7, {c}, 0x15", 5, 7, 0x15, "write immediate (csrrwi)"),
    ("csrrsi x7, {c}, 0", 6, 7, 0, "read (csrrsi uimm=0)"),
    ("csrrci x7, {c}, 0x15", 7, 7, 0x15, "clear immediate (csrrci)"),
]
READ_FORMS = [f for f in FORMS if f[4].startswith("read")]
WRITE_FORMS = [f for f in FORMS if not f[4].startswith("read")]


def csr_window(t: TestFile, mode: str, csr: int, name: str, form: Form, expect: str, desc: str) -> str:
    """One CSR instruction (by number) in `mode` in a trap window; expect 'ok', 'illegal', or 'reserved' (a CSR that
    does not exist: the access is a reserved instruction, so it may succeed or raise illegal instruction; Ssstrict
    requires the trap and is tested in its own suite)."""
    asm, f3, rd, rs1, kind = form
    tval = None if expect == "ok" else [0, enc_csr(csr, f3, rd, rs1)]
    cause: str | int | list = {"ok": "ok", "illegal": 2, "reserved": ["ok", 2]}[expect]
    return t.window(mode, [asm.format(c=hex(csr)) + f"  // {name}"], cause, f"{kind} of {name} ({desc})", tval)


def word_window(
    t: TestFile,
    mode: str,
    e: int,
    note: str,
    expect: Expect,
    desc: str,
    tval: Expect | None = "auto",
    more: tuple[str, ...] = (),
) -> str:
    """A .word-encoded instruction in a window. tval 'auto': [0, encoding] for illegal instruction."""
    if tval == "auto":
        alts = expect if isinstance(expect, list) else [expect]
        tval = [0, e] if 2 in alts else None
    return t.window(mode, [f".word {hex(e)}  // {note}", *more], expect, desc, tval)


# ---------------------------------------------------------------- small code helpers
def wait(t: TestFile, n: int = 200, reg: str = "x15") -> None:
    """Bounded idle loop (no checks inside), e.g. to let an interrupt arrive."""
    loop = t.label("idle")
    t.emit(f"LI({reg}, {n})", 2)
    t.emit(f"{loop}:", 0)
    t.emit(f"addi {reg}, {reg}, -1", n)
    t.emit(f"bnez {reg}, {loop}", n)


def poll_mip(t: TestFile, bit: int, until: int, n: int = 200, reg: str = "x15", tmp: str = "x5") -> None:
    """Read mip until bit == until or n reads pass (bounded wait, no checks)."""
    loop, done = t.label("poll"), t.label("polled")
    t.emit(f"LI({reg}, {n})", 2)
    t.emit(f"{loop}:", 0)
    t.emit(f"csrr {tmp}, mip", n)
    t.emit(f"srli {tmp}, {tmp}, {bit}", n)
    t.emit(f"andi {tmp}, {tmp}, 1", n)
    t.emit(f"{'bnez' if until else 'beqz'} {tmp}, {done}", n)
    t.emit(f"addi {reg}, {reg}, -1", n)
    t.emit(f"bnez {reg}, {loop}", n)
    t.emit(f"{done}:", 0)


def log_word(t: TestFile, reg: str, word: str, back: int = 0) -> None:
    """reg = word (TRAPLOG_*) of the trap log entry `back` traps before the last one. Uses x4, x5."""
    t.emit("LA(x4, rvtest_trap_count)", 2)
    t.emit("LREG x5, 0(x4)")
    t.emit(f"addi x5, x5, {-1 - back}")
    t.emit("andi x5, x5, RVTEST_TRAP_LOG_N-1")
    t.emit("slli x5, x5, TRAPLOG_ENTRY_SHIFT")
    t.emit("LA(x4, rvtest_trap_log)", 2)
    t.emit("add x4, x4, x5")
    t.emit(f"LREG {reg}, ({word})*REGWIDTH(x4)")


def check_handler(t: TestFile, mode: str, lab: str, desc: str, back: int = 0) -> None:
    """The (back-th last) trap was taken by the `mode` handler (M or S)."""
    log_word(t, "x15", "TRAPLOG_VECT", back)
    t.emit("andi x15, x15, 3")
    t.check("x15", {"M": 3, "S": 1}[mode], lab, f"{desc}: taken in {mode}-mode (handler mode 3 M, 1 S)")


def check_log(t: TestFile, word: str, mask: Value, expected: Expect, lab: str, desc: str, back: int = 0) -> None:
    log_word(t, "x15", word, back)
    t.check_masked("x15", mask, expected, lab, desc)


def csr_bits(t: TestFile, csr: str, bits: Value, on: bool, tmp: str = "x5") -> None:
    if isinstance(bits, int) and 0 <= bits < 32:
        t.emit(f"csr{'s' if on else 'c'}i {csr}, {bits}")
        return
    if isinstance(bits, int):
        t.li(tmp, bits)
    else:
        t.load(tmp, bits)
    t.emit(f"csr{'s' if on else 'c'} {csr}, {tmp}")


def probe_bits(t: TestFile, reg: str, csr: str, mask: Value) -> None:
    """Try to set `mask` in csr and leave in reg the bits that read back as 1 (csr keeps them set)."""
    if isinstance(mask, int):
        t.li(reg, mask)
    else:
        t.load(reg, mask)
    t.emit(f"csrs {csr}, {reg}")
    t.emit(f"csrr x5, {csr}")
    t.emit(f"and {reg}, {reg}, x5")


# ---------------------------------------------------------------- interrupt sources
class Src:
    """A machine-visible interrupt source that M-mode can raise and clear."""

    def __init__(self, name: str, cause: int, cond: str, set_: list[str], clr: list[str], sw: bool) -> None:
        self.name, self.cause, self.cond, self.set, self.clr, self.sw = name, cause, cond, set_, clr, sw

    def raise_(self, t: TestFile) -> None:
        for ln in self.set:
            t.emit(ln, 30)
        if not self.sw:
            poll_mip(t, self.cause, 1)

    def clear(self, t: TestFile) -> None:
        for ln in self.clr:
            t.emit(ln, 30)
        if not self.sw:
            poll_mip(t, self.cause, 0)


# mip.SSIP/STIP/SEIP are software-writable in mip from M-mode (STIP only without an active stimecmp: tests
# that use STI clear menvcfg.STCE first). MSI, MTI and MEI come from the platform (rvmodel_macros.h).
SRC = {
    "SSI": Src("SSI", 1, S, ["csrsi mip, 2"], ["csrci mip, 2"], True),
    "STI": Src("STI", 5, S, ["LI(x5, 0x20)", "csrs mip, x5"], ["LI(x5, 0x20)", "csrc mip, x5"], True),
    "SEI": Src("SEI", 9, S, ["LI(x5, 0x200)", "csrs mip, x5"], ["LI(x5, 0x200)", "csrc mip, x5"], True),
    "MSI": Src("MSI", 3, "defined(RVMODEL_MSIP_ADDRESS)", ["RVTEST_SET_MSW_INT_M"], ["RVTEST_CLR_MSW_INT_M"], False),
    "MTI": Src(
        "MTI", 7, "defined(RVMODEL_MTIMECMP_ADDRESS)", ["RVTEST_SET_MTIME_INT_M"], ["RVTEST_CLR_MTIME_INT_M"], False
    ),
    "MEI": Src("MEI", 11, "defined(RVMODEL_SET_MEXT_INT)", ["RVTEST_SET_MEXT_INT_M"], ["RVTEST_CLR_MEXT_INT_M"], False),
}


def stce_off(t: TestFile) -> None:
    """With Sstc, clear menvcfg.STCE so that mip.STIP is the software-writable bit (Sstc suite owns STCE=1)."""
    with t.only_if("defined(SSTC_SUPPORTED)"):
        with t.rv64_only():
            t.emit("LI(x5, 1)", 2)
            t.emit("slli x5, x5, 63")
            t.emit("csrc menvcfg, x5")
        with t.rv32_only():
            t.emit("LI(x5, 0x80000000)", 2)
            t.emit("csrc menvcfgh, x5")


def satp_probe(t: TestFile, reg: str) -> None:
    """reg = 1 if satp.MODE is writable (some translation mode is supported), else 0. Leaves satp = 0.
    Writes each nonzero MODE encoding (Sv32 on RV32; Sv39, Sv48, Sv57 on RV64) and keeps any that reads back."""
    with t.only_if(S):
        with t.rv64_only():
            t.emit(f"li {reg}, 0")
            for m in (8, 9, 10):
                t.emit(f"LI(x5, {m})", 2)
                t.emit("slli x5, x5, 60")
                t.emit("csrw satp, x5")
                t.emit("csrr x5, satp")
                t.emit("srli x5, x5, 60")
                t.emit("snez x5, x5")
                t.emit(f"or {reg}, {reg}, x5")
        with t.rv32_only():
            t.emit("LI(x5, 0x80000000)", 2)
            t.emit("csrw satp, x5")
            t.emit(f"csrr {reg}, satp")
            t.emit(f"srli {reg}, {reg}, 31")
        t.emit("csrw satp, x0")
    with t.only_if(NO_S):
        t.emit(f"li {reg}, 0")


def win(
    t: TestFile,
    mode: str,
    lines: list[str],
    expect: Expect,
    desc: str,
    tval: Expect | None = None,
    origin: str | None = None,
) -> str:
    """TestFile.window, except that the string "LAB" in tval stands for the window's own label (e.g. xtval = the
    address of an ebreak)."""
    lab = t.label(f"in_{mode}")
    if tval is not None:
        tv = tval if isinstance(tval, list) else [tval]
        tval = [lab if v == "LAB" else v for v in tv]
    t.allow(1)
    if mode != t.cur:
        t.enter(mode)
    t.emit(f"{lab}:", 0)
    for ln in lines:
        t.emit(ln)
    if mode != t.cur:
        t.leave()
    t.outcome(expect, lab, f"{desc} in {mode}-mode", tval, origin=origin or mode)
    return lab


EBREAK = ".word 0x00100073  // ebreak"
EBREAK_ENC = 0x00100073


def _skip(t: TestFile, lo: int, hi: int) -> list[str]:
    """AI_SKIP over table entries lo..hi-1 whatever their preprocessor conditions: one AI_SKIP per distinct set of
    conditions beyond the ones already in force, each under its own #if."""
    groups: dict[tuple[str, ...], int] = {}
    for _, conds in t.table[lo:hi]:
        extra = tuple(c for c in conds if c not in t._conds)
        groups[extra] = groups.get(extra, 0) + 1
    out = []
    for conds, n in groups.items():
        if conds:
            out.append("#if " + " && ".join(f"({c})" for c in conds))
        out.append(f"  AI_SKIP({n})")
        if conds:
            out.append("#endif")
    return out


def either(t: TestFile, reg: str, if_set: Callable[[], object], if_clear: Callable[[], object]) -> None:
    """TestFile.either, except that either branch may hold table entries under extra #if conditions (e.g. a mode
    guard inside a run-time branch): the skips are emitted per condition set."""
    clear, done = t.label("clear"), t.label("done")
    t.emit(f"beqz {reg}, {clear}")
    a = len(t.table)
    if_set()
    b = len(t.table)
    hole = len(t.code)
    t.code.append("")
    t.emit(f"j {done}")
    t.emit(f"{clear}:", 0)
    t.code += _skip(t, a, b)
    if_clear()
    t.code[hole] = "\n".join(_skip(t, b, len(t.table)))
    t.emit(f"{done}:", 0)


# Rule text and source of every rule tested, from riscv-isa-manual upstream/main a5d22968 (tests_ai/gen/norm_rules.py).
RULES: dict[str, dict[str, str]] = {
    "Zmmul_misa_m": {
        "src": "src/priv/machine.adoc",
        "text": "if the zmmul extension is supported then the multiply instructions it specifies are supported irrespective of the value of the m bit.",
    },
    "cycle_instret_hpmcounter_op_rdonly": {
        "src": "src/priv/machine.adoc",
        "text": "The cycle, instret, and `hpmcounter__n__` CSRs are read-only shadows of mcycle, minstret, and `mhpmcounter__n__`, respectively.",
    },
    "ebreak_debugger_transfer_op": {
        "src": "src/priv/machine.adoc",
        "text": "The EBREAK instruction is used by debuggers to cause control to be transferred back to a debugging environment. Unless overridden by an external debug environment, EBREAK raises a breakpoint exception and performs no other operation.",
    },
    "ecall_ebreak_epc_value": {
        "src": "src/priv/machine.adoc",
        "text": "ECALL and EBREAK cause the receiving privilege mode\u2019s `epc` register to be set to the address of the ECALL or EBREAK instruction itself, _not_ the address of the following instruction.",
    },
    "ecall_priv_mode_op": {
        "src": "src/priv/machine.adoc",
        "text": "The ECALL instruction is used to make a request to the supporting execution environment. When executed in U-mode, S-mode, or M-mode, it generates an environment-call-from-U-mode exception, environment-call-from-S-mode exception, or environment-call-from-M-mode exception, respectively, and performs no other operation.",
    },
    "intr_m_mode_highest_pri": {
        "src": "src/priv/machine.adoc",
        "text": "Interrupts to M-mode take priority over any interrupts to lower privilege modes.",
    },
    "intr_m_mode_pri": {
        "src": "src/priv/machine.adoc",
        "text": "Multiple simultaneous interrupts destined for M-mode are handled in the following decreasing priority order: MEI, MSI, MTI, SEI, SSI, STI, LCOFI.",
    },
    "intr_mip_mie_op": {
        "src": "src/priv/machine.adoc",
        "text": "An interrupt _i_ will trap to M-mode (causing the privilege mode to change to M-mode) if all of the following are true: (a) either the current privilege mode is M and the mie bit in the mstatus register is set, or the current privilege mode has less privilege than M-mode; (b) bit _i_ is set in both mip and mie; and (c) if register mideleg exists, bit _i_ is not set in mideleg.",
    },
    "intr_mip_mie_xret_csrwr": {
        "src": "src/priv/machine.adoc",
        "text": "be evaluated immediately following the execution of an __x__RET instruction or an explicit write to a CSR on which these interrupt trap conditions expressly depend (including mip, mie, mstatus, and mideleg).",
    },
    "intr_sei_op": {
        "src": "src/priv/machine.adoc",
        "text": "Supervisor-level external interrupts are made pending based on the logical-OR of the software-writable seip bit and the signal from the external interrupt controller.",
    },
    "marchid_always_rd": {
        "src": "src/priv/machine.adoc",
        "text": "This register must be readable in any implementation, but a value of 0 can be returned to indicate the field is not implemented.",
    },
    "marchid_sz_acc_op": {
        "src": "src/priv/machine.adoc",
        "text": "The marchid CSR is an MXLEN-bit read-only register encoding the base microarchitecture of the hart.",
    },
    "mcause_exccode_ld_ldrsv": {
        "src": "src/priv/machine.adoc",
        "text": "Note that load and load-reserved instructions generate load exceptions",
    },
    "mcause_exccode_st_sc_amo": {
        "src": "src/priv/machine.adoc",
        "text": "store, store-conditional, and AMO instructions generate store/AMO exceptions.",
    },
    "mcause_exccode_wlrl": {
        "src": "src/priv/machine.adoc",
        "text": "The Exception Code is a *WLRL* field, so is only guaranteed to hold supported exception codes.",
    },
    "mcause_intr_op": {
        "src": "src/priv/machine.adoc",
        "text": "The Interrupt bit in the `mcause` register is set if the trap was caused by an interrupt.",
    },
    "mcause_op": {
        "src": "src/priv/machine.adoc",
        "text": "When a trap is taken into M-mode, `mcause` is written with a code indicating the event that caused the trap. Otherwise, `mcause` is never written by the implementation, though it may be explicitly written by software.",
    },
    "mcause_sz_acc": {
        "src": "src/priv/machine.adoc",
        "text": "The `mcause` register is an MXLEN-bit read-write register",
    },
    "mconfigptr_align": {
        "src": "src/priv/machine.adoc",
        "text": "The pointer alignment in bits must be no smaller than MXLEN: i.e., if MXLEN is 8{times}__n__, then `mconfigptr`[log~2~n-1:0] must be zero.",
    },
    "mconfigptr_mandatory": {"src": "src/priv/machine.adoc", "text": "The `mconfigptr` register must be implemented"},
    "mconfigptr_sz_acc": {
        "src": "src/priv/machine.adoc",
        "text": "The `mconfigptr` register is an MXLEN-bit read-only CSR formatted as shown in <<norm:mconfigptr_enc_img>>",
    },
    "mcounteren_clr_ill_inst_exc": {
        "src": "src/priv/machine.adoc",
        "text": "When the cy, tm, ir, or HPM__n__ bit in the mcounteren register is clear, attempts to read the cycle, time, instret, or `hpmcounter__n__` register while executing in S-mode or U-mode will cause an illegal-instruction exception.",
    },
    "mcounteren_inc_inaccessible": {
        "src": "src/priv/machine.adoc",
        "text": "The settings in this register only control accessibility. The act of reading or writing this register does not affect the underlying counters, which continue to increment even when not accessible.",
    },
    "mcounteren_set_nxt_priv": {
        "src": "src/priv/machine.adoc",
        "text": "When one of these bits is set, access to the corresponding register is permitted in the next implemented privilege mode (S-mode if implemented, otherwise U-mode).",
    },
    "mcounteren_sz": {
        "src": "src/priv/machine.adoc",
        "text": "The counter-enable mcounteren register is a 32-bit register",
    },
    "mcountinhibit_clear_op": {
        "src": "src/priv/machine.adoc",
        "text": "When the cy, ir, or HPM__n__ bit in the mcountinhibit register is clear, the mcycle, minstret, or `mhpmcounter__n__` register increments as usual. When the cy, ir, or HPM__n__ bit is set, the corresponding counter does not increment.",
    },
    "mcountinhibit_not_impl": {
        "src": "src/priv/machine.adoc",
        "text": "If the mcountinhibit register is not implemented, the implementation behaves as though the register were set to zero.",
    },
    "mcountinhibit_only_inc": {
        "src": "src/priv/machine.adoc",
        "text": "The settings in this register only control whether the counters increment; their accessibility is not affected by the setting of this register.",
    },
    "mcountinhibit_sz_warl": {
        "src": "src/priv/machine.adoc",
        "text": "The counter-inhibit register mcountinhibit is a 32-bit *WARL* register that controls which of the hardware performance-monitoring counters increment.",
    },
    "mcycle_minstret_sz": {
        "src": "src/priv/machine.adoc",
        "text": "The mcycle and minstret registers have 64-bit precision on all RV32 and RV64 harts.",
    },
    "mcycle_minstret_wr": {
        "src": "src/priv/machine.adoc",
        "text": "Any CSR write takes effect after the writing instruction has otherwise completed.",
    },
    "mcycleh_minstreth_mhpmh_op": {
        "src": "src/priv/machine.adoc",
        "text": "reads of the mcycleh, minstreth, `mhpmcounter__n__h`, and `mhpmevent__n__h` CSRs return bits 63-32 of the corresponding register, and writes change only bits 63-32.",
    },
    "medeleg_16_rdonly0": {
        "src": "src/priv/machine.adoc",
        "text": "The medeleg[16] is read-only zero as double trap is not delegatable.",
    },
    "medeleg_mideleg_delegate_op": {
        "src": "src/priv/machine.adoc",
        "text": "setting a bit in medeleg or mideleg will delegate the corresponding trap, when occurring in S-mode or U-mode, to the S-mode trap handler.",
    },
    "medeleg_mideleg_mandatory_s_mode": {
        "src": "src/priv/machine.adoc",
        "text": "In harts with S-mode, the `medeleg` and `mideleg` registers must exist",
    },
    "medeleg_mideleg_warl": {
        "src": "src/priv/machine.adoc",
        "text": "An implementation can choose to subset the delegatable traps, with the supported delegatable bits found by writing one to every bit location, then reading back the value in medeleg or mideleg to see which bit positions hold a one.",
    },
    "medeleg_no_rd1": {
        "src": "src/priv/machine.adoc",
        "text": "An implementation shall not have any bits of medeleg be read-only one",
    },
    "medeleg_when_rd0": {
        "src": "src/priv/machine.adoc",
        "text": "For exceptions that cannot occur in less privileged modes, the corresponding medeleg bits should be read-only zero. In particular, medeleg[11] is read-only zero.",
    },
    "medelegh_omit_xlen64": {
        "src": "src/priv/machine.adoc",
        "text": "The medelegh register does not exist when XLEN=64.",
    },
    "medelegh_sz_acc_enc_xlen32": {
        "src": "src/priv/machine.adoc",
        "text": "When XLEN=32, medelegh is a 32-bit read/write register that aliases bits 63:32 of medeleg.",
    },
    "menvcfg_adue_henvcfg_adue_rdonly0": {
        "src": "src/priv/machine.adoc",
        "text": "for implementations with the hypervisor extension, `henvcfg`.ADUE is read-only zero if `menvcfg`.ADUE is zero.",
    },
    "menvcfg_adue_rdonly0": {
        "src": "src/priv/machine.adoc",
        "text": "If Svadu is not implemented, ADUE is read-only zero.",
    },
    "menvcfg_cbcfe_op": {
        "src": "src/priv/machine.adoc",
        "text": "The Zicbom extension adds the `CBCFE` (Cache Block Clean and Flush instruction Enable) field to `menvcfg`. When the `CBCFE` field is set to 1, it enables execution of the cache block clean instruction (`CBO.CLEAN`) and the cache block flush instruction (`CBO.FLUSH`) in modes less privileged than M. Otherwise, these instructions raise an illegal-instruction exception in modes less privileged than M.",
    },
    "menvcfg_cbcfe_rdonly0": {
        "src": "src/priv/machine.adoc",
        "text": "When the Zicbom extension is not implemented, `CBCFE` is read-only zero.",
    },
    "menvcfg_cbie_rdonly0": {
        "src": "src/priv/machine.adoc",
        "text": "When the Zicbom extension is not implemented, `CBIE` is read-only zero.",
    },
    "menvcfg_cbie_warl_op": {
        "src": "src/priv/machine.adoc",
        "text": "The Zicbom extension adds the `CBIE` (Cache Block Invalidate instruction Enable) WARL field to `menvcfg` to control execution of the cache block invalidate instruction (`CBO.INVAL`) in modes less privileged than M. When `CBIE` is set to `0b00`, the instruction raises an illegal-instruction exception in modes less privileged than M.",
    },
    "menvcfg_cbze_op": {
        "src": "src/priv/machine.adoc",
        "text": "The Zicboz extension adds the `CBZE` (Cache Block Zero instruction enable) field to `menvcfg`. When the `CBZE` field is set to 1, it enables execution of the cache block zero instruction, `CBO.ZERO`, in modes less privileged than M. Otherwise, the instruction raises an illegal-instruction exception in modes less privileged than M.",
    },
    "menvcfg_cbze_rdonly0": {
        "src": "src/priv/machine.adoc",
        "text": "When the Zicboz extension is not implemented, `CBZE` is read-only zero.",
    },
    "menvcfg_cde_rdonly0": {
        "src": "src/priv/machine.adoc",
        "text": "If Smcdeleg is not implemented, CDE is read-only zero.",
    },
    "menvcfg_mandatory_u_mode": {
        "src": "src/priv/machine.adoc",
        "text": "In harts with U-mode, `menvcfg` must be implemented, but all `WARL` fields may be read-only zero.",
    },
    "menvcfg_menvcfgh_no_u_mode": {
        "src": "src/priv/machine.adoc",
        "text": "If U-mode is not supported, then registers `menvcfg` and `menvcfgh` do not exist.",
    },
    "menvcfg_pbmte_henvcfg_pbmte_rdonly0": {
        "src": "src/priv/machine.adoc",
        "text": "for implementations with the hypervisor extension, `henvcfg`.PBMTE is read-only zero if `menvcfg`.PBMTE is zero.",
    },
    "menvcfg_pbmte_rdonly0": {
        "src": "src/priv/machine.adoc",
        "text": "If Svpbmt is not implemented, PBMTE is read-only zero.",
    },
    "menvcfgh_sz_acc_op": {
        "src": "src/priv/machine.adoc",
        "text": "When XLEN=32, `menvcfgh` is a 32-bit read/write register that aliases bits 63:32 of `menvcfg`. The `menvcfgh` register does not exist when XLEN=64.",
    },
    "mepc_align": {
        "src": "src/priv/machine.adoc",
        "text": "The low bit of `mepc` (`mepc[0]`) is always zero. On implementations that support only IALIGN=32, the two low bits (`mepc[1:0]`) are always zero.",
    },
    "mepc_bit1_dyn_ialign_op": {
        "src": "src/priv/machine.adoc",
        "text": "If an implementation allows IALIGN to be either 16 or 32 (by changing CSR `misa`, for example), then, whenever IALIGN=32, bit `mepc[1]` is masked on reads so that it appears to be 0. This masking occurs also for the implicit read by the MRET instruction. Though masked, `mepc[1]` remains writable when IALIGN=32.",
    },
    "mepc_op": {
        "src": "src/priv/machine.adoc",
        "text": "When a trap is taken into M-mode, `mepc` is written with the virtual address of the instruction that was interrupted or that encountered the exception. Otherwise, `mepc` is never written by the implementation, though it may be explicitly written by software.",
    },
    "mepc_varlen_wr": {
        "src": "src/priv/machine.adoc",
        "text": "`mepc` will point to the beginning of the instruction.",
    },
    "mepc_warl": {
        "src": "src/priv/machine.adoc",
        "text": "`mepc` is a *WARL* register that must be implemented and must be able to hold all valid virtual addresses. It need not be capable of holding all possible invalid addresses.",
    },
    "mhartid_always_rd": {
        "src": "src/priv/machine.adoc",
        "text": "This register must be readable in any implementation.",
    },
    "mhartid_sz_acc_op": {
        "src": "src/priv/machine.adoc",
        "text": "The mhartid CSR is an MXLEN-bit read-only register containing the integer ID of the hardware thread running the code.",
    },
    "mhpmevent_enc": {
        "src": "src/priv/machine.adoc",
        "text": 'The meaning of these events is defined by the platform, but event 0 is defined to mean "`no event.`"',
    },
    "mideleg_no_rd1": {
        "src": "src/priv/machine.adoc",
        "text": "an implementation shall not fix as read-only one any bits of mideleg corresponding to machine-level interrupts",
    },
    "mie_bits_rdonly0": {
        "src": "src/priv/machine.adoc",
        "text": "Bits of mie that are not writable must be read-only zero.",
    },
    "mie_bits_wr": {
        "src": "src/priv/machine.adoc",
        "text": "A bit in mie must be writable if the corresponding interrupt can ever become pending.",
    },
    "mimpid_always_rd": {
        "src": "src/priv/machine.adoc",
        "text": "This register must be readable in any implementation, but a value of 0 can be returned to indicate that the field is not implemented.",
    },
    "mimpid_op": {
        "src": "src/priv/machine.adoc",
        "text": "The mimpid CSR provides a unique encoding of the version of the processor implementation.",
    },
    "mip_bits_wr_op": {
        "src": "src/priv/machine.adoc",
        "text": "When bit _i_ in mip is writable, a pending interrupt _i_ can be cleared by writing 0 to this bit.",
    },
    "mip_meip_rdonly": {
        "src": "src/priv/machine.adoc",
        "text": "meip is read-only in mip, and is set and cleared by a platform-specific interrupt controller.",
    },
    "mip_msip_rdonly": {
        "src": "src/priv/machine.adoc",
        "text": "msip is read-only in mip, and is written by accesses to memory-mapped control registers, which are used to provide machine-level interprocessor interrupts.",
    },
    "mip_mtip_rdonly": {
        "src": "src/priv/machine.adoc",
        "text": "mtip is read-only in the mip register, and is cleared by writing to the memory-mapped machine-mode timer compare register.",
    },
    "mip_seip_acc": {"src": "src/priv/machine.adoc", "text": "seip is writable in mip"},
    "mip_seip_rdcsr": {
        "src": "src/priv/machine.adoc",
        "text": "When mip is read with a CSR instruction, the value of the seip bit returned in the _rd_ destination register is the logical-OR of the software-writable bit and the interrupt signal from the interrupt controller",
    },
    "mip_seip_wrcsr": {
        "src": "src/priv/machine.adoc",
        "text": "the signal from the interrupt controller is not used to calculate the value written to seip. Only the software-writable seip bit participates in the read-modify-write sequence of a csrrs or csrrc instruction.",
    },
    "mip_ssip_acc": {"src": "src/priv/machine.adoc", "text": "ssip is writable in mip"},
    "mip_stip_no_stimecmp_acc": {
        "src": "src/priv/machine.adoc",
        "text": "If the stimecmp register is not implemented, stip is writable in mip",
    },
    "mip_stip_no_stimecmp_mmode_write": {
        "src": "src/priv/machine.adoc",
        "text": "may be written by M-mode software to deliver timer interrupts to S-mode.",
    },
    "mip_sxip_mie_sxie_rdonly0": {
        "src": "src/priv/machine.adoc",
        "text": "If supervisor mode is not implemented, bits seip, stip, and ssip of mip and seie, stie, and ssie of mie are read-only zeros.",
    },
    "misa_B_op": {
        "src": "src/priv/machine.adoc",
        "text": "When the b bit is 1, the implementation supports the instructions provided by the zba, zbb, and zbs extensions.",
    },
    "misa_acc": {"src": "src/priv/machine.adoc", "text": "The misa CSR is a *WARL* read-write register"},
    "misa_always_rd": {"src": "src/priv/machine.adoc", "text": "This register must be readable in any implementation"},
    "misa_e_acc": {"src": "src/priv/machine.adoc", "text": "The e bit is read-only."},
    "misa_e_not_i": {
        "src": "src/priv/machine.adoc",
        "text": "Unless misa is all read-only zero, the e bit always reads as the complement of the i bit.",
    },
    "misa_extensions_dependencies": {
        "src": "src/priv/machine.adoc",
        "text": "If an ISA feature _x_ depends on an ISA feature _y_, then attempting to enable feature _x_ but disable feature _y_ results in both features being disabled.",
    },
    "misa_extensions_disabling": {
        "src": "src/priv/machine.adoc",
        "text": "When a standard extension is disabled by clearing its bit in misa, the instructions and CSRs defined or modified by the extension revert to their defined or reserved behaviors as if the extension is not implemented.",
    },
    "misa_extensions_reset_maximal": {
        "src": "src/priv/machine.adoc",
        "text": "At reset, the Extensions field shall contain the maximal set of supported extensions, and i shall be selected over e if both are available.",
    },
    "misa_extensions_rsv_ret_0": {
        "src": "src/priv/machine.adoc",
        "text": "All bits that are reserved for future use must return zero when read.",
    },
    "misa_i_op": {"src": "src/priv/machine.adoc", "text": "The i bit will be set for the RV32I and RV64I base ISAs"},
    "misa_inc_ialign": {
        "src": "src/priv/machine.adoc",
        "text": "Writing misa may increase IALIGN, e.g., by disabling the c extension. If an instruction that would write misa increases IALIGN, and the subsequent instruction's address is not IALIGN-bit aligned, the write to misa is suppressed, leaving misa unchanged.",
    },
    "misa_m_op": {
        "src": "src/priv/machine.adoc",
        "text": "When the m bit is 1, the implementation supports all multiply and division instructions defined by the m extension.",
    },
    "misa_mxl_acc": {"src": "src/priv/machine.adoc", "text": "The mxl field is read-only."},
    "misa_mxl_op_nz": {
        "src": "src/priv/machine.adoc",
        "text": "If misa is nonzero, the mxl field indicates the effective XLEN in M-mode, a constant termed _MXLEN_.",
    },
    "misa_s_op": {
        "src": "src/priv/machine.adoc",
        "text": "When the s bit is 1, the implementation supports supervisor mode.",
    },
    "misa_u_op": {
        "src": "src/priv/machine.adoc",
        "text": "When the u bit is 1, the implementation supports user mode.",
    },
    "mret_presence": {"src": "src/priv/machine.adoc", "text": "MRET is always provided."},
    "mscratch_sz_acc": {
        "src": "src/priv/machine.adoc",
        "text": "The `mscratch` register is an MXLEN-bit read/write register dedicated for use by machine mode. The `mscratch` register must be implemented.",
    },
    "mseccfg_mmwp_op_warl": {
        "src": "src/priv/machine.adoc",
        "text": "The `mseccfg.MMWP` (Machine-Mode Allowlist Policy) is a WARL field. This field changes the default PMP policy for Machine mode when accessing memory regions that don't have a matching PMP rule. This is a sticky bit, meaning that once set it cannot be unset until a *PMP reset*. When set it changes the default PMP policy for M-mode when accessing memory regions that don\u2019t have a matching *PMP rule*, to *denied* instead of *ignored*.",
    },
    "mseccfg_presence": {
        "src": "src/priv/machine.adoc",
        "text": "It exists if any extension that adds a field to `mseccfg` is implemented. Otherwise, it is reserved.",
    },
    "mseccfg_rlb_op_warl": {
        "src": "src/priv/machine.adoc",
        "text": "`mseccfg.RLB` (Rule Locking Bypass) is a WARL field that provides a mechanism to temporarily modify *Locked* PMP rules. When `mseccfg.RLB` is 1, locked PMP rules may be removed or modified. When `mseccfg.RLB` is 0 and `pmpcfg.L` is 1 in any rule or entry (including disabled entries), then `mseccfg.RLB` remains 0 and any further modifications to `mseccfg.RLB` are ignored until a *PMP reset*.",
    },
    "mseccfg_sseed_rdonly0": {
        "src": "src/priv/machine.adoc",
        "text": "If Zkr or S-mode is not implemented, `SSEED` is read-only zero.",
    },
    "mseccfg_sseed_sorhs_mode_op": {
        "src": "src/priv/machine.adoc",
        "text": "When `SSEED` is 0, access to the `seed` CSR from S-/HS-mode raises an illegal-instruction exception. When `SSEED` is 1, read-write access to the `seed` CSR from S-/HS-mode is allowed; all other types of accesses raise an illegal-instruction exception.",
    },
    "mseccfg_useed_rdonly0": {
        "src": "src/priv/machine.adoc",
        "text": "If Zkr or U-mode is not implemented, `USEED` is read-only zero.",
    },
    "mseccfg_useed_u_mode_op": {
        "src": "src/priv/machine.adoc",
        "text": "When `USEED` is 0, access to the `seed` CSR in U-mode raises an illegal-instruction exception. When `USEED` is 1, read-write access to the `seed` CSR from U-mode is allowed; all other types of accesses raise an illegal-instruction exception.",
    },
    "mseccfgh_presence": {
        "src": "src/priv/machine.adoc",
        "text": "Register `mseccfgh` exists when XLEN=32 and `mseccfg` is implemented; it does not exist when XLEN=64.",
    },
    "msip_enc": {
        "src": "src/priv/machine.adoc",
        "text": "bits 31{endash}1 read as zero and bit 0 contains the msip bit.",
    },
    "mstatus_fs_acc1": {
        "src": "src/priv/machine.adoc",
        "text": "If the f extension is implemented, the fs field shall not be read-only zero.",
    },
    "mstatus_fs_acc2": {
        "src": "src/priv/machine.adoc",
        "text": "If neither the f extension nor S-mode is implemented, then fs is read-only zero.",
    },
    "mstatus_fs_rdonly0_s_no_F": {
        "src": "src/priv/machine.adoc",
        "text": "If S-mode is implemented but the f extension is not, fs may optionally be read-only zero.",
    },
    "mstatus_fs_vs_xs_off_op": {
        "src": "src/priv/machine.adoc",
        "text": "When an extension's status is set to Off, any instruction that attempts to read or write the corresponding state will cause an illegal-instruction exception.",
    },
    "mstatus_fs_vs_xs_update_indep_priv": {
        "src": "src/priv/machine.adoc",
        "text": "The status fields are also updated during execution of instructions, regardless of privilege mode.",
    },
    "mstatus_fs_wr": {
        "src": "src/priv/machine.adoc",
        "text": "Changing the setting of fs has no effect on the contents of the floating-point register state. In particular, setting fs=Off does not destroy the state, nor does setting fs=Initial clear the contents.",
    },
    "mstatus_mbe_op": {
        "src": "src/priv/machine.adoc",
        "text": "mbe controls whether non-instruction-fetch memory accesses made from M-mode (assuming mstatus[mprv]=0) are little-endian (mbe=0) or big-endian (mbe=1).",
    },
    "mstatus_mie_sie_op": {
        "src": "src/priv/machine.adoc",
        "text": "When a hart is executing in privilege mode _x_, interrupts are globally enabled when __x__IE=1 and globally disabled when __x__IE=0.",
    },
    "mstatus_mprv_clr_mret_sret_less_priv": {
        "src": "src/priv/machine.adoc",
        "text": "An mret or sret instruction that changes the privilege mode to a mode less privileged than M also sets mprv=0.",
    },
    "mstatus_mprv_inst_xlat_op": {
        "src": "src/priv/machine.adoc",
        "text": "Instruction address-translation and protection are unaffected by the setting of mprv.",
    },
    "mstatus_mprv_ldst_op": {
        "src": "src/priv/machine.adoc",
        "text": "When mprv=0, explicit memory accesses behave as normal, using the translation and protection mechanisms of the current privilege mode. When mprv=1, load and store memory addresses are translated and protected, and endianness is applied, as though the current privilege mode were set to mpp.",
    },
    "mstatus_mprv_rdonly0_no_umode": {
        "src": "src/priv/machine.adoc",
        "text": "mprv is read-only 0 if U-mode is not supported; otherwise, it must be writable.",
    },
    "mstatus_mxr_rdonly0_no_smode": {
        "src": "src/priv/machine.adoc",
        "text": "mxr is read-only 0 if S-mode is not supported or if satp[mode] is read-only 0; otherwise, it must be writable.",
    },
    "mstatus_mxr_sum_op_acc_fault": {
        "src": "src/priv/machine.adoc",
        "text": "The mxr and sum mechanisms only affect the interpretation of permissions encoded in page-table entries. In particular, they have no impact on whether access-fault exceptions are raised due to PMAs or PMP.",
    },
    "mstatus_sbe_op": {
        "src": "src/priv/machine.adoc",
        "text": "If S-mode is not supported, sbe is read-only 0. Otherwise, sbe controls whether explicit load and store memory accesses made from S-mode are little-endian (sbe=0) or big-endian (sbe=1).",
    },
    "mstatus_sd_acc": {"src": "src/priv/machine.adoc", "text": "The sd bit is a read-only bit"},
    "mstatus_sd_formula": {
        "src": "src/priv/machine.adoc",
        "text": "The sd bit is read-only and is set when either the fs, vs, or xs bits encode a Dirty state (i.e., sd=(fs==0b11 OR xs==0b11 OR vs==0b11)).",
    },
    "mstatus_sd_rdonly0": {
        "src": "src/priv/machine.adoc",
        "text": "If fs, vs, and xs are all read-only zero, then sd is also always zero.",
    },
    "mstatus_sie_spie_rdonly0": {
        "src": "src/priv/machine.adoc",
        "text": "mie and mpie must be writable. If supervisor mode is not implemented, then sie and spie are read-only 0; otherwise, they must be writable.",
    },
    "mstatus_sum_rdonly0": {
        "src": "src/priv/machine.adoc",
        "text": "sum is read-only 0 if S-mode is not supported or if satp[mode] is read-only 0; otherwise, it must be writable.",
    },
    "mstatus_sxl_acc_mxlen64": {
        "src": "src/priv/machine.adoc",
        "text": "When MXLEN=64, if S-mode is not supported, then sxl is read-only zero. Otherwise, it is a *WARL* field that encodes the current value of SXLEN.",
    },
    "mstatus_tsr_acc": {
        "src": "src/priv/machine.adoc",
        "text": "tsr is read-only 0 when S-mode is not supported; otherwise, it must be writable.",
    },
    "mstatus_tsr_op": {
        "src": "src/priv/machine.adoc",
        "text": "When tsr=1, attempts to execute sret while executing in S-mode will raise an illegal-instruction exception. When tsr=0, this operation is permitted in S-mode.",
    },
    "mstatus_tvm_acc": {
        "src": "src/priv/machine.adoc",
        "text": "tvm is read-only 0 when S-mode is not supported or if satp[mode] is read-only 0; otherwise, it must be writable.",
    },
    "mstatus_tvm_op": {
        "src": "src/priv/machine.adoc",
        "text": "When tvm=1, attempts to read or write the satp CSR or execute an sfence.vma or sinval.vma instruction while executing in S-mode will raise an illegal-instruction exception. When tvm=0, these operations are permitted in S-mode.",
    },
    "mstatus_tw_acc": {
        "src": "src/priv/machine.adoc",
        "text": "tw is read-only 0 when there are no modes less privileged than M; otherwise, it must be writable.",
    },
    "mstatus_tw_op": {
        "src": "src/priv/machine.adoc",
        "text": "When tw=0, the wfi instruction may execute in modes less privileged than M when not prevented for some other reason. When tw=1, then if wfi is executed in any less-privileged mode, and it does not complete within an implementation-specific, bounded time limit, the wfi instruction causes an illegal-instruction exception.",
    },
    "mstatus_tw_umode_op": {
        "src": "src/priv/machine.adoc",
        "text": "When S-mode is implemented, then executing wfi in U-mode causes an illegal-instruction exception, regardless of the value of the tw bit, unless the instruction completes within an implementation-specific, bounded time limit.",
    },
    "mstatus_ube_op": {
        "src": "src/priv/machine.adoc",
        "text": "If U-mode is not supported, ube is read-only 0. Otherwise, UBE controls whether explicit load and store memory accesses made from U-mode are little-endian (ube=0) or big-endian (ube=1).",
    },
    "mstatus_uxl_acc_mxlen64": {
        "src": "src/priv/machine.adoc",
        "text": "When MXLEN=64, if U-mode is not supported, then uxl is read-only zero. Otherwise, it is a *WARL* field that encodes the current value of UXLEN.",
    },
    "mstatus_uxl_legal_vals_smode": {
        "src": "src/priv/machine.adoc",
        "text": "If S-mode is implemented, the set of legal values that the uxl field may assume excludes those that would cause UXLEN to be greater than SXLEN.",
    },
    "mstatus_vs_acc1": {
        "src": "src/priv/machine.adoc",
        "text": "If the `v` registers are implemented, the vs field shall not be read-only zero.",
    },
    "mstatus_vs_acc2": {
        "src": "src/priv/machine.adoc",
        "text": "If neither the `v` registers nor S-mode is implemented, then vs is read-only zero.",
    },
    "mstatus_vs_rdonly0_s_no_V": {
        "src": "src/priv/machine.adoc",
        "text": "If S-mode is implemented but the `v` registers are not, vs may optionally be read-only zero.",
    },
    "mstatus_vs_wr": {
        "src": "src/priv/machine.adoc",
        "text": "the setting of VS has no effect on the contents of the vector register state.",
    },
    "mstatus_xie_intr_en_dis": {
        "src": "src/priv/machine.adoc",
        "text": "Interrupts for lower-privilege modes, __w__<__x__, are always globally disabled regardless of the setting of any global __w__IE bit for the lower-privilege mode. Interrupts for higher-privilege modes, __y__>__x__, are always globally enabled regardless of the setting of the global __y__IE bit for the higher-privilege mode.",
    },
    "mstatus_xpie_xie_xpp_trap_op": {
        "src": "src/priv/machine.adoc",
        "text": "When a trap is taken from privilege mode _y_ into privilege mode _x_, __x__PIE is set to the value of __x__IE; __x__IE is set to 0; and __x__PP is set to _y_.",
    },
    "mstatus_xpp_rdonly0": {
        "src": "src/priv/machine.adoc",
        "text": "If privilege mode _x_ is not implemented, then __x__PP must be read-only 0.",
    },
    "mstatus_xpp_warl": {
        "src": "src/priv/machine.adoc",
        "text": "__x__PP fields are *WARL* fields that can hold only privilege mode _x_ and any implemented privilege mode lower than _x_.",
    },
    "mstatus_xret_op": {
        "src": "src/priv/machine.adoc",
        "text": "When executing an __x__RET instruction, supposing __x__PP holds the value _y_, __x__IE is set to __x__PIE; the privilege mode is changed to _y_; __x__PIE is set to 1; and __x__PP is set to the least-privileged supported mode (U if U-mode is implemented, else M). If __y__{ne}M, __x__RET also sets mprv=0.",
    },
    "mtime_intr_pending": {
        "src": "src/priv/machine.adoc",
        "text": "A machine timer interrupt becomes pending whenever `mtime` contains a value greater than or equal to `mtimecmp`, treating the values as unsigned integers. The interrupt remains posted until `mtimecmp` becomes greater than `mtime`",
    },
    "mtime_intr_taken": {
        "src": "src/priv/machine.adoc",
        "text": "The interrupt will only be taken if interrupts are enabled and the MTIE bit is set in the `mie` register.",
    },
    "mtime_mtimecmp_rv64_wr": {
        "src": "src/priv/machine.adoc",
        "text": "For RV64, naturally aligned 64-bit memory accesses to the `mtime` and `mtimecmp` registers are additionally supported and are atomic.",
    },
    "mtime_op": {"src": "src/priv/machine.adoc", "text": "`mtime` must increment at constant frequency"},
    "mtimecmp_rv32_wr": {
        "src": "src/priv/machine.adoc",
        "text": "In RV32, memory-mapped writes to `mtimecmp` modify only one 32-bit part of the register.",
    },
    "mtval_ebreak_op": {
        "src": "src/priv/machine.adoc",
        "text": "On a breakpoint exception raised by an EBREAK or C.EBREAK instruction, `mtval` is written with either zero or the virtual address of the instruction.",
    },
    "mtval_ill_instr_exc_in_low_bits": {
        "src": "src/priv/machine.adoc",
        "text": "On an illegal-instruction exception, the instruction bits are zero-extended and loaded into mtval.",
    },
    "mtval_op": {
        "src": "src/priv/machine.adoc",
        "text": "When a trap is taken into M-mode, `mtval` is either set to zero or written with exception-specific information to assist software in handling the trap. Otherwise, `mtval` is never written by the implementation, though it may be explicitly written by software.",
    },
    "mtval_other_traps_zero": {"src": "src/priv/machine.adoc", "text": "For other traps, `mtval` is set to zero"},
    "mtval_vaddr_wr_faulting_addr": {
        "src": "src/priv/machine.adoc",
        "text": "If `mtval` is written with a nonzero value when a breakpoint, address-misaligned, access-fault, page-fault, or hardware-error exception occurs on an instruction fetch, load, or store, then `mtval` will contain the faulting virtual address.",
    },
    "mtval_vaddr_wr_misaligned_addr": {
        "src": "src/priv/machine.adoc",
        "text": "If `mtval` is written with a nonzero value when a misaligned load or store causes an access-fault, page-fault, or hardware-error exception, then `mtval` will contain the virtual address of the portion of the access that caused the fault.",
    },
    "mtval_varlen_wr": {
        "src": "src/priv/machine.adoc",
        "text": "If `mtval` is written with a nonzero value when an instruction access-fault, page-fault, or hardware-error exception occurs on a hart with variable-length instructions, then `mtval` will contain the virtual address of the portion of the instruction that caused the fault",
    },
    "mtval_warl": {"src": "src/priv/machine.adoc", "text": "If `mtval` is not read-only zero, it is a *WARL* register"},
    "mtvec_mode_direct_op": {
        "src": "src/priv/machine.adoc",
        "text": "When mode=Direct, all traps into machine mode cause the `pc` to be set to the address in the base field.",
    },
    "mtvec_mode_enc": {
        "src": "src/priv/machine.adoc",
        "text": '.Encoding of mtvec[mode] field [%autowidth,float="center",align="center",cols=">,^,<",options="header"] |=== |Value |Name |Description |0 |Direct |All traps set `pc` to base. |1 |Vectored |Asynchronous interrupts set `pc` to base+4{times}cause. |{ge}2 |-- |_Reserved_ |===',
    },
    "mtvec_mode_vectored_op": {
        "src": "src/priv/machine.adoc",
        "text": "When mode=Vectored, all synchronous exceptions into machine mode cause the `pc` to be set to the address in the base field, whereas interrupts cause the `pc` to be set to the address in the base field plus four times the interrupt cause number.",
    },
    "mvendorid_always_rd": {
        "src": "src/priv/machine.adoc",
        "text": "This register must be readable in any implementation, but a value of 0 can be returned to indicate the field is not implemented or that this is a non-commercial implementation.",
    },
    "mvendorid_sz_acc_op": {
        "src": "src/priv/machine.adoc",
        "text": "The mvendorid CSR is a 32-bit read-only register providing the JEDEC manufacturer ID of the provider of the core.",
    },
    "pmp_a_field_napot_na4": {
        "src": "src/priv/machine.adoc",
        "text": "naturally aligned power-of-2 regions (NAPOT), including the special case of naturally aligned four-byte regions (NA4);",
    },
    "pmp_a_field_off": {
        "src": "src/priv/machine.adoc",
        "text": "When A=0, this PMP entry is disabled and matches no addresses.",
    },
    "pmp_a_field_tor": {
        "src": "src/priv/machine.adoc",
        "text": "If TOR is selected, the associated address register forms the top of the address range, and the preceding PMP address register forms the bottom of the address range. If PMP entry __i__'s A field is set to TOR, the entry matches any address _y_ such that `pmpaddr~i-1~`{le}__y__<``pmpaddr~i~`` (irrespective of the value of `pmpcfg~i-1~`). If PMP entry 0's A field is set to TOR, zero is used for the lower bound, and so it matches any address `y<pmpaddr~0~`.",
    },
    "pmp_access_fault_exception": {
        "src": "src/priv/machine.adoc",
        "text": "Failed memory operations generate an instruction, load, or store access-fault exception.",
    },
    "pmp_addr_encoding": {
        "src": "src/priv/machine.adoc",
        "text": "Each PMP address register encodes bits 33-2 of a 34-bit physical address for RV32, as shown in <<pmpaddr-rv32>>. For RV64, each PMP address register encodes bits 55-2 of a 56-bit physical address, as shown in <<pmpaddr-rv64>>.",
    },
    "pmp_addr_retention_on_mode_change": {
        "src": "src/priv/machine.adoc",
        "text": "Although changing pmpcfg~i~.A[1] affects the value read from pmpaddr~i~, it does not affect the underlying value stored in that register\u2014in particular, pmpaddr~i~[G-1] retains its original value when pmpcfg~i~.A is changed from NAPOT to TOR/OFF then back to NAPOT.",
    },
    "pmp_addr_warl": {
        "src": "src/priv/machine.adoc",
        "text": "Not all physical address bits may be implemented, and so the `pmpaddr` registers are *WARL*.",
    },
    "pmp_cbm_fault": {
        "src": "src/priv/machine.adoc",
        "text": "The permissions required for a cache-block management instruction to access a PMP region are defined in <<cmo>>; when such access is not permitted, the instruction raises a store access-fault exception.",
    },
    "pmp_cfg_permissions": {
        "src": "src/priv/machine.adoc",
        "text": "<<pmpcfg>> shows the layout of a PMP configuration register. The R, W, and X bits, when set, indicate that the PMP entry permits read, write, and instruction execution, respectively. When one of these bits is clear, the corresponding access type is denied.",
    },
    "pmp_cfg_rv32_layout": {
        "src": "src/priv/machine.adoc",
        "text": "For RV32, sixteen CSRs, `pmpcfg0`\u2013`pmpcfg15`, hold the configurations `pmp0cfg`\u2013`pmp63cfg` for the 64 PMP entries, as shown in <<pmpcfg-rv32>>.",
    },
    "pmp_cfg_rv64_illegal": {
        "src": "src/priv/machine.adoc",
        "text": "For RV64, the odd-numbered configuration registers, `pmpcfg1`, `pmpcfg3`, \u2026, `pmpcfg15`, are illegal.",
    },
    "pmp_cfg_rv64_layout": {
        "src": "src/priv/machine.adoc",
        "text": "For RV64, eight even-numbered CSRs, `pmpcfg0`, `pmpcfg2`, \u2026, `pmpcfg14`, hold the configurations for the 64 PMP entries, as shown in <<pmpcfg-rv64>>.",
    },
    "pmp_check_priv_modes": {
        "src": "src/priv/machine.adoc",
        "text": "PMP checks are applied to all accesses whose effective privilege mode is S or U, including instruction fetches and data accesses in S and U mode, and data accesses in M-mode when the MPRV bit in `mstatus` is set and the MPP field in `mstatus` contains S or U.",
    },
    "pmp_csr_mode": {"src": "src/priv/machine.adoc", "text": "PMP CSRs are only accessible to M-mode."},
    "pmp_entry_priority": {
        "src": "src/priv/machine.adoc",
        "text": "PMP entries are statically prioritized. The lowest-numbered PMP entry that matches any byte of a memory operation determines whether that operation succeeds or fails.",
    },
    "pmp_exec_fault": {
        "src": "src/priv/machine.adoc",
        "text": "Attempting to fetch an instruction from a PMP region that does not have execute permissions raises an instruction access-fault exception.",
    },
    "pmp_full_match_required": {
        "src": "src/priv/machine.adoc",
        "text": "The matching PMP entry must match all bytes of a memory operation, or the operation fails, irrespective of the L, R, W, and X bits.",
    },
    "pmp_l_bit_function": {
        "src": "src/priv/machine.adoc",
        "text": "The L bit indicates that the PMP entry is locked, i.e., writes to the configuration register and associated address registers are ignored.",
    },
    "pmp_l_bit_m_mode_enforcement": {
        "src": "src/priv/machine.adoc",
        "text": "In addition to locking the PMP entry, the L bit indicates whether the R/W/X permissions are additionally enforced on M-mode accesses. When the L bit is set, these permissions are enforced for all privilege modes. When the L bit is clear, any M-mode access matching the PMP entry will succeed; the R/W/X permissions apply only to S and U modes.",
    },
    "pmp_l_bit_write_protection": {
        "src": "src/priv/machine.adoc",
        "text": "If PMP entry _i_ is locked, writes to ``pmp``__i__``cfg`` and ``pmpaddr``__i__ are ignored. Additionally, if PMP entry _i_ is locked and ``pmp``__i__``cfg.A`` is set to TOR, writes to ``pmpaddr``__i__-1 are ignored.",
    },
    "pmp_load_fault": {
        "src": "src/priv/machine.adoc",
        "text": "Attempting to execute a load or load-reserved instruction that accesses a physical address within a PMP region without read permissions raises a load access-fault exception.",
    },
    "pmp_locked_until_reset": {
        "src": "src/priv/machine.adoc",
        "text": "Locked PMP entries remain locked until the hart is reset.",
    },
    "pmp_misaligned_access_behavior": {
        "src": "src/priv/machine.adoc",
        "text": "On some implementations, misaligned loads, stores, and instruction fetches may be decomposed into multiple memory operations, some of which may succeed before an access-fault exception occurs, as described in the RVWMO specification. PMP checking is performed on each memory operation independently.",
    },
    "pmp_mmode_locking": {
        "src": "src/priv/machine.adoc",
        "text": "Optionally, PMP checks may additionally apply to M-mode accesses, in which case the PMP registers themselves are locked, so that even M-mode software cannot change them until the hart is reset.",
    },
    "pmp_na4_select_restriction": {
        "src": "src/priv/machine.adoc",
        "text": "When G {ge} 1, the NA4 mode is not selectable.",
    },
    "pmp_napot_addr_read_mask": {
        "src": "src/priv/machine.adoc",
        "text": "When G {ge} 2 and pmpcfg~i~.A[1] is set, i.e. the mode is NAPOT, then bits pmpaddr~i~[G-2:0] read as all ones.",
    },
    "pmp_napot_encoding_low_bits": {
        "src": "src/priv/machine.adoc",
        "text": "NAPOT ranges make use of the low-order bits of the associated address register to encode the size of the range, as shown in <<pmpcfg-napot>>.",
    },
    "pmp_no_entry_match": {
        "src": "src/priv/machine.adoc",
        "text": "If no PMP entry matches an M-mode memory operation, the operation succeeds. If no PMP entry matches an S-mode or U-mode memory operation, the operation fails if at least one PMP entry is implemented and succeeds otherwise.",
    },
    "pmp_region_granularity_g": {
        "src": "src/priv/machine.adoc",
        "text": "Although the PMP mechanism supports regions as small as four bytes, platforms may specify coarser PMP regions. In general, the PMP grain is 2^G+2^ bytes and must be the same across all PMP regions.",
    },
    "pmp_rw01_rsv": {
        "src": "src/priv/machine.adoc",
        "text": "If `mseccfg.MML` is not set, the combination of `pmpcfg.RW=01` remains reserved for future standard use.",
    },
    "pmp_rwx_check": {
        "src": "src/priv/machine.adoc",
        "text": "If a PMP entry matches all bytes of a memory operation, then the L, R, W, and X bits determine whether the operation succeeds or fails. If the L bit is clear and the privilege mode of the access is M, the operation succeeds. Otherwise, if the L bit is set or the privilege mode of the access is S or U, then the operation succeeds only if the R, W, or X bit corresponding to the access type is set.",
    },
    "pmp_rwx_warl": {
        "src": "src/priv/machine.adoc",
        "text": "The R, W, and X fields form a collective *WARL* field for which the combinations with R=0 and W=1 are reserved.",
    },
    "pmp_store_fault": {
        "src": "src/priv/machine.adoc",
        "text": "Attempting to execute a store, store-conditional, AMO, or cache-block zero instruction that accesses a physical address within a PMP region without write permissions raises a store access-fault exception.",
    },
    "pmp_tor_off_addr_read_mask": {
        "src": "src/priv/machine.adoc",
        "text": "When G {ge} 1 and pmpcfg~i~.A[1] is clear, i.e. the mode is OFF or TOR, then bits pmpaddr~i~[G-1:0] read as all zeros. Bits pmpaddr~i~[G-1:0] do not affect the TOR address-matching logic.",
    },
    "pmp_violation_precise_trap": {
        "src": "src/priv/machine.adoc",
        "text": "PMP violations are always trapped precisely at the processor.",
    },
    "sret_presence": {
        "src": "src/priv/machine.adoc",
        "text": "SRET must be provided if supervisor mode is supported, and should raise an illegal-instruction exception otherwise.",
    },
    "time_op_rdonly": {
        "src": "src/priv/machine.adoc",
        "text": "The time CSR is a read-only shadow of the memory-mapped mtime register.",
    },
    "trap_def_m_mode": {
        "src": "src/priv/machine.adoc",
        "text": "By default, all traps at any privilege level are handled in machine mode",
    },
    "trap_del_intr_priv_lvl": {
        "src": "src/priv/machine.adoc",
        "text": "Delegated interrupts result in the interrupt being masked at the delegator privilege level. For example, if the supervisor timer interrupt (STI) is delegated to S-mode by setting mideleg[5], STIs will not be taken when executing in M-mode. By contrast, if mideleg[5] is clear, STIs can be taken in any mode and regardless of current mode will transfer control to M-mode.",
    },
    "trap_del_s_mode_no_m_mode": {
        "src": "src/priv/machine.adoc",
        "text": "The mcause, mepc, and mtval registers and the mpp and mpie fields of mstatus are not written.",
    },
    "trap_del_s_mode_op": {
        "src": "src/priv/machine.adoc",
        "text": "When a trap is delegated to S-mode, the scause register is written with the trap cause; the sepc register is written with the virtual address of the instruction that took the trap; the stval register is written with an exception-specific datum; the spp field of mstatus is written with the active privilege mode at the time of the trap; the spie field of mstatus is written with the value of the sie field at the time of the trap; and the sie field of mstatus is cleared.",
    },
    "trap_horiz": {
        "src": "src/priv/machine.adoc",
        "text": "traps may be taken horizontally. Using the same example, if M-mode has delegated illegal-instruction exceptions to S-mode, and S-mode software later executes an illegal instruction, the trap is taken in S-mode.",
    },
    "trap_never_trans_lower": {
        "src": "src/priv/machine.adoc",
        "text": "Traps never transition from a more-privileged mode to a less-privileged mode. For example, if M-mode has delegated illegal-instruction exceptions to S-mode, and M-mode software later executes an illegal instruction, the trap is taken in M-mode, rather than being delegated to S-mode.",
    },
    "wfi_all_privileged_modes": {"src": "src/priv/machine.adoc", "text": "WFI is available in all privileged modes"},
    "wfi_intr_dis": {
        "src": "src/priv/machine.adoc",
        "text": "The WFI instruction can also be executed when interrupts are disabled.",
    },
    "wfi_no_intr_pc": {
        "src": "src/priv/machine.adoc",
        "text": "If the event that causes the hart to resume execution does not cause an interrupt to be taken, execution will resume at `pc` + 4",
    },
    "wfi_resume_any_priv": {
        "src": "src/priv/machine.adoc",
        "text": "WFI is also required to resume execution for locally enabled interrupts pending at any privilege level, regardless of the global interrupt enable at each privilege level.",
    },
    "wfi_unaffected_conditions": {
        "src": "src/priv/machine.adoc",
        "text": "The operation of WFI must be unaffected by the global interrupt bits in `mstatus` (MIE and SIE) and the delegation register `mideleg` (i.e., the hart must resume if a locally enabled interrupt becomes pending, even if it has been delegated to a less-privileged mode), but should honor the individual interrupt enables (e.g, MTIE) (i.e., implementations should avoid resuming the hart if the interrupt is pending but not locally enabled).",
    },
    "xret_in_higher_mode": {
        "src": "src/priv/machine.adoc",
        "text": "An __x__RET instruction can be executed in privilege mode _x_ or higher, where executing a lower-privilege __x__RET instruction will pop the relevant lower-privilege interrupt enable and privilege mode stack.",
    },
    "xret_in_lower_mode": {
        "src": "src/priv/machine.adoc",
        "text": "Attempting to execute an __x__RET instruction in a mode less privileged than _x_ will raise an illegal-instruction exception.",
    },
    "xret_op": {
        "src": "src/priv/machine.adoc",
        "text": "In addition to manipulating the privilege stack as described in <<privstack>>, __x__RET sets the `pc` to the value stored in the `__x__epc` register.",
    },
}
