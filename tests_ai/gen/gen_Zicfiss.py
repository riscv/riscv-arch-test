#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate tests_ai/Zicfiss: one test per normative rule about Zicfiss (shadow stacks).

Rules come from the Zicfiss part of src/unpriv/cfi.adoc and src/priv/cfi.adoc, and from the SSE fields of
menvcfg (machine.adoc), senvcfg (supervisor.adoc) and henvcfg (hypervisor.adoc), plus the software-check xtval
encodings. Tests boot to S-mode (M-mode parts are _Sm files that boot to M), turn the SSE enables on through
T-SBI (menvcfg) and S-mode CSR writes (senvcfg, henvcfg), and enter U, VS and VU with sret or T-SBI GOTOs.
Shadow-stack memory accesses need S-level translation: tests that make them build an Sv39/Sv32 page table
(zicfisslib.vm_setup) and run U-mode code in a U alias of the code region. Traps are checked in the trap log.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

sys.path.insert(0, str(Path(__file__).parent))
from aigen import POOL_TRAP, X, mask
from hmem import A, D, MemTest, V, W
from zicfisslib import (
    C_SSPOPCHK,
    C_SSPUSH,
    HENVCFG,
    ILLEGAL,
    INSN_AF,
    INSN_PF,
    LOAD_PF,
    MXR,
    RO,
    RW,
    RWX,
    RX,
    SENVCFG,
    SS,
    SS_FAULT,
    SSE,
    SSP,
    STORE_AF,
    STORE_GPF,
    STORE_MIS,
    STORE_PF,
    SUM,
    SWCHECK,
    VIRTUAL,
    XB,
    XO,
    ZC,
    H,
    Map,
    U,
    amo,
    amo_tf,
    c_mop,
    cbo,
    henv_sse,
    hword,
    mem_check,
    menv_sse,
    mop_r,
    mop_rr7,
    page_bytes,
    read_ssp,
    senv_sse,
    set_ssp,
    ssamoswap,
    ssp_check,
    sspopchk,
    sspush,
    ssrdp,
    va,
    vm_either,
    vm_off,
    vm_setup,
    word,
    xword,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from aigen import Expect, Value

SUITE = "Zicfiss"
T = TypeVar("T")
ISSUE = "https://github.com/riscv/riscv-isa-manual/issues/"
REQ = ["I", "S", "Zicfiss"]
REQ_M = ["I", "S", "Sm", "Zicfiss"]
MARCH = "rv${XLEN}i_zicsr_zifencei"
UCFI = "src/unpriv/cfi.adoc"
PCFI = "src/priv/cfi.adoc"
MAC = "src/priv/machine.adoc"
SUP = "src/priv/supervisor.adoc"
HYP = "src/priv/hypervisor.adoc"
MUT = os.environ.get("AI_MUTANT", "")  # mutate.py: model a plausible bug in the expectations

MUTANTS = {
    "ssp_low_writable": "ssp bits 1:0 are writable",
    "ssp_32bit": "ssp keeps only 32 bits on RV64",
    "u_ignores_senvcfg": "U-mode may access ssp with senvcfg.SSE=0",
    "vs_illegal": "VS-mode access to ssp with henvcfg.SSE=0 raises illegal- instead of virtual-instruction",
    "menvcfg0_virtual": "VS/VU-mode access to ssp with menvcfg.SSE=0 raises virtual-instruction",
    "vu_ignores_henvcfg": "VU-mode xSSE is senvcfg.SSE even when henvcfg.SSE=0 (senvcfg.SSE not read-only zero)",
    "ssrdp_inactive_ssp": "ssrdp returns ssp when Zicfiss is inactive",
    "mop_ssrdp": "mop.r.28 with rs1!=x0 and rd!=x0 returns ssp (decoded as ssrdp)",
    "push_no_decrement": "sspush stores at ssp without decrementing it",
    "push_store_old_top": "sspush stores at the old ssp, then decrements",
    "push_decrement_on_fault": "a faulting sspush still decrements ssp",
    "pop_no_increment": "sspopchk does not increment ssp",
    "pop_increment_on_mismatch": "sspopchk increments ssp even when the check fails",
    "pop_32bit_compare": "sspopchk compares only the low 32 bits on RV64",
    "pop_checks_x1": "sspopchk x5 compares x1",
    "swcheck_tval0": "the shadow-stack software check writes xtval = 0",
    "swcheck_cause_illegal": "a sspopchk mismatch raises illegal-instruction",
    "pop_fault_as_load": "sspopchk memory faults are reported as load faults (13/5)",
    "swcheck_over_af": "the software check outranks an access fault",
    "ssamoswap_w_zext": "ssamoswap.w zero-extends its result on RV64",
    "ssamoswap_misaligned_ok": "a misaligned ssamoswap succeeds (misaligned atomicity granule applied)",
    "ss_store_pf": "an ordinary store to an SS page raises a store/AMO page fault",
    "ss_store_ok": "an ordinary store to an SS page succeeds",
    "ss_load_faults": "loads from an SS page raise a load access fault",
    "ss_fetch_pf": "a fetch from an SS page raises an instruction page fault",
    "ss_cbo_ok": "CBO instructions on an SS page do not fault",
    "rw_page_ok": "shadow-stack instructions may access an RW page",
    "ro_page_af": "shadow-stack instructions on a read-only page raise an access fault",
    "bare_ok": "shadow-stack instructions with satp.MODE=Bare access memory",
    "sse0_ss_page": "xwr=010 stays an SS page when menvcfg.SSE=0",
    "senvcfg0_reserves_pte": "senvcfg.SSE=0 makes xwr=010 reserved for U-mode",
    "henvcfg0_ss_page": "xwr=010 stays an SS page in VS-stage tables when henvcfg.SSE=0",
    "sse0_ssamoswap_ok": "ssamoswap does not trap when menvcfg.SSE=0",
    "senvcfg0_ssamoswap_virtual": "ssamoswap in U-mode with senvcfg.SSE=0 raises virtual-instruction",
    "vu_ssamoswap_illegal": "ssamoswap in VU-mode with senvcfg.SSE=0 raises illegal-instruction",
    "rdonly0_writable": "senvcfg.SSE is writable while menvcfg.SSE=0",
    "m_ssamoswap_ok": "M-mode ssamoswap accesses memory",
    "misaligned_ssp_ok": "sspush/sspopchk with an ssp that is not XLEN-aligned access memory",
    "pbmt_io_ok": "shadow-stack instructions access a PBMT=IO page",
    "gstage_r_ok": "a G-stage read-only page is enough for shadow-stack instructions",
    "swcheck_not_delegated": "a software check with medeleg[18]=0 is taken in S-mode",
    "mprv_ssamoswap_af": "M-mode ssamoswap with MPRV=1, MPP=S raises an access fault",
    "sum_ignored": "S-mode shadow-stack accesses to U pages succeed with SUM=0",
    "mxr_needed": "loads from an SS page need MXR=1",
    "c_mop_writes": "c.sspush with SSE=0 still pushes",
}


# ---------------------------------------------------------------- helpers
def new(
    rule: str,
    required: list[str] = REQ,
    *,
    boot: str = "S",
    suffix: str = "",
    rv64: bool = False,
    forbidden: list[str] | None = None,
) -> MemTest:
    return MemTest(
        SUITE,
        rule,
        required=required,
        boot=boot,
        pool=POOL_TRAP,
        march=MARCH,
        suffix=suffix,
        rv64=rv64,
        forbidden=forbidden,
    )


def mut(name: str, good: T, bad: T) -> T:
    """The expectation, or the mutant's when AI_MUTANT is name."""
    return bad if name == MUT else good


def enc_csr(csr: int, f3: int, rd: int, rs1: int) -> int:
    return (csr << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | 0x73


# CSR instruction forms on ssp: (asm, funct3, rd, rs1-or-uimm, kind, writes). rd x7, rs x6. The immediates (0x19)
# leave bit 2 alone, which is read-only zero on some RV64 harts (ssp_field_1_0).
if TYPE_CHECKING:
    Form = tuple[str, int, int, int, str, bool]
FORMS: list[Form] = [
    ("csrrs x7, 0x011, x0", 2, 7, 0, "read (csrrs rs1=x0)", False),
    ("csrrw x0, 0x011, x6", 1, 0, 6, "write (csrrw rd=x0)", True),
    ("csrrw x7, 0x011, x6", 1, 7, 6, "swap (csrrw)", True),
    ("csrrs x7, 0x011, x6", 2, 7, 6, "set (csrrs rs1!=x0)", True),
    ("csrrc x7, 0x011, x6", 3, 7, 6, "clear (csrrc rs1!=x0)", True),
    ("csrrwi x7, 0x011, 0x19", 5, 7, 0x19, "write immediate (csrrwi)", True),
    ("csrrsi x7, 0x011, 0", 6, 7, 0, "read (csrrsi uimm=0)", False),
    ("csrrci x7, 0x011, 0x19", 7, 7, 0x19, "clear immediate (csrrci uimm!=0)", True),
]
READ, WRITE = FORMS[0], FORMS[1]


def form_value(form: Form, old: int, rs: int, width: int) -> tuple[int | None, int]:
    _, f3, rd, rs1, _, _ = form
    m = (1 << width) - 1
    src = (rs if rs1 == 6 else 0) if f3 in (1, 2, 3) else rs1
    new = {1: src, 5: src, 2: old | src, 6: old | src, 3: old & ~src, 7: old & ~src}[f3] & m
    return (old if rd else None), new


def lowmask(xlen: int) -> int:
    """Bits of ssp that every hart implements (RV64 bit 2 may be read-only zero)."""
    return mask(~3 if xlen == 32 else ~7, xlen)


def held(v: int, xlen: int) -> int:
    """The value ssp holds after a write of v (v has bit 2 clear on RV64)."""
    if MUT == "ssp_low_writable":
        return mask(v, xlen)
    if MUT == "ssp_32bit" and xlen == 64:
        return v & 0xFFFFFFFC
    return mask(v, xlen) & ~3


def rand_ssp(t: MemTest) -> X:
    return X(t.rand(32) & lowmask(32) | (t.rand(1) << 2), t.rand(64) & lowmask(64))


CAUSE = {"ok": "ok", "illegal": ILLEGAL, "virtual": VIRTUAL}


def ssp_access(t: MemTest, mode: str, form: Form, expect: str, desc: str) -> str:
    asm, f3, rd, rs1, kind, _ = form
    tval: list[Value] | None = None if expect == "ok" else [0, enc_csr(SSP, f3, rd, rs1)]
    return win(t, mode, [asm + "  // ssp"], CAUSE[expect], f"{kind} of ssp ({desc})", tval)


def win(
    t: MemTest,
    mode: str,
    lines: list[str],
    expect: Expect,
    desc: str,
    tval: Expect | None = None,
    pre: Callable[[], object] | None = None,
    epc: Value | None = None,
) -> str:
    """Run lines in mode inside a trap window (U through the U alias while the S-level map with a U alias is on).
    pre runs in mode before the labeled instruction (e.g. to set x5, which AI_ALLOW clobbers). epc overrides the
    expected xepc (a fetch fault reports the target)."""
    alias = mode == "U" and getattr(t, "vm_user", False)
    lab = t.label(f"in_{mode}")
    t.allow(1)
    if alias:
        t.emit("RVTEST_TSBI_GOTO_UMODE", 120)
    elif mode != t.cur:
        t.enter(mode)
    if pre:
        pre()
    t.emit(f"{lab}:", 0)
    for ln in lines:
        t.emit(ln)
    if alias:
        t.emit("RVTEST_TSBI_GOTO_SMODE", 120)
    elif mode != t.cur:
        t.leave()
    alts = expect if isinstance(expect, list) else [expect]
    certain = "ok" not in alts
    t.outcome(expect, lab, f"{desc} in {mode}-mode", tval, epc=not alias and epc is None, origin=mode)
    if certain and (alias or epc is not None):
        t.emit("AI_LOG(x15, TRAPLOG_EPC)", 10)
        if alias and epc is None:
            from zicfisslib import ALIAS, SPSHIFT

            for xlen in (32, 64):
                with t.only_if(f"__riscv_xlen == {xlen}"):
                    t.la("x13", "rvtest_code_begin")
                    t.emit(f"srli x13, x13, {SPSHIFT[xlen]}")
                    t.emit(f"slli x13, x13, {SPSHIFT[xlen]}")
                    t.emit(f"li x14, {hex(ALIAS[xlen])}")
                    t.emit("sub x15, x15, x14")
                    t.emit("add x15, x15, x13")
        t.check("x15", lab if epc is None else epc, lab, f"{desc} in {mode}-mode: xepc")
    return lab


def run(t: MemTest, mode: str, lines: list[str], pre: Callable[[], object] | None = None) -> str:
    """Run lines in mode with no trap permitted (an unexpected trap fails the test)."""
    alias = mode == "U" and getattr(t, "vm_user", False)
    lab = t.label(f"run_{mode}")
    if alias:
        t.emit("RVTEST_TSBI_GOTO_UMODE", 120)
    elif mode != t.cur:
        t.enter(mode)
    if pre:
        pre()
    t.emit(f"{lab}:", 0)
    for ln in lines:
        t.emit(ln)
    if alias:
        t.emit("RVTEST_TSBI_GOTO_SMODE", 120)
    elif mode != t.cur:
        t.leave()
    return lab


def enables(t: MemTest, m: int, s: int, h: int | None = None) -> None:
    """menvcfg.SSE = m, senvcfg.SSE = s and (with H, when h is given) henvcfg.SSE = h. senvcfg/henvcfg are written
    while menvcfg.SSE=1, since they are read-only zero otherwise."""
    menv_sse(t, True)
    senv_sse(t, bool(s))
    if h is not None:
        with t.only_if(H):
            henv_sse(t, bool(h))
    if not m:
        menv_sse(t, False)


def teardown(t: MemTest) -> None:
    t.comment("teardown: SSE enables off")
    menv_sse(t, True)
    senv_sse(t, False)
    with t.only_if(H):
        henv_sse(t, False)
    menv_sse(t, False)


def xs(v32: int, v64: int | None = None) -> X:
    return X(v32 & 0xFFFFFFFF, (v32 if v64 is None else v64) & ((1 << 64) - 1))


EDGES = [
    X(0, 0),
    X(0xFFFFFFFF, (1 << 64) - 1),
    X(0x80000000, 1 << 63),
    X(0x55555555, 0x5555555555555555),
    X(0xAAAAAAAA, 0xAAAAAAAAAAAAAAAA),
    X(1, 1),
    X(0x7FFFFFFF, (1 << 63) - 1),
]


def pre_load(t: MemTest, reg: str, v: Value, note: str = "") -> Callable[[], object]:
    return lambda: t.load(reg, v, note)


def guard_page(t: MemTest, base: int = 0x700, n: int = 64, seed: int = 0) -> dict:
    """Page contents: n 8-byte guard words from base, each distinct."""
    return {
        base + 8 * i: (8, 0x6A09E667F3BCC908 ^ (0x9E3779B97F4A7C15 * (i + 1 + seed)) & ((1 << 64) - 1))
        for i in range(n)
    }


# Tests go below, grouped by area. Each section appends to the list it is given.
TESTS: list[Callable[[list], None]] = []


def section(f: Callable[[list], None]) -> Callable[[list], None]:
    TESTS.append(f)
    return f


def ssp_expect(mode: str, m: int, s: int, h: int) -> str:
    """Outcome of an ssp access in mode (Zicfiss_ssp_csr and its bullets; henvcfg_sse_op: with V=1 and
    henvcfg.SSE=0, senvcfg.SSE is read-only zero, #2424)."""
    if mode == "M":
        return "ok"
    if not m:
        return mut("menvcfg0_virtual", "illegal", "virtual" if mode in ("VS", "VU") else "illegal")
    if mode == "U":
        return "ok" if s or MUT == "u_ignores_senvcfg" else "illegal"
    if mode == "VS":
        return "ok" if h else mut("vs_illegal", "virtual", "illegal")
    if mode == "VU":
        eff = s if MUT == "vu_ignores_henvcfg" else (s and h)
        return "ok" if eff else "virtual"
    return "ok"


def form_case(t: MemTest, mode: str, form: Form, desc: str, expect: str = "ok") -> None:
    """One CSR form on ssp in mode with random old and source values; when it succeeds, check rd and the value ssp
    holds afterwards (read in S-mode)."""
    old = X(t.rand(32), t.rand(64) & ~4)
    rs = X(t.rand(32), t.rand(64) & ~4)
    set_ssp(t, old, "old ssp")
    t.load("x6", rs, "rs1 value")
    t.li("x7", 0x5A)
    lab = ssp_access(t, mode, form, expect, desc)
    r32, n32 = form_value(form, old.num(32), rs.num(32), 32)
    r64, n64 = form_value(form, old.num(64), rs.num(64), 64)
    if expect != "ok":
        n32, n64 = old.num(32), old.num(64)
    elif r32 is not None and r64 is not None:
        t.check("x7", X(held(r32, 32), held(r64, 64)), lab, f"{form[4]} of ssp in {mode}-mode returns the old value")
    ssp_check(t, X(held(n32, 32), held(n64, 64)), lab, f"ssp after {form[4]} in {mode}-mode ({desc})")


ISSUE_2424 = (
    f'{ISSUE}2424: "When henvcfg.sse is 0 and V is 1, senvcfg.sse is read only zero. A read only zero CSR field '
    'cannot be written to and returns 0 on read by both hardware and software" (ved-rivos). So VU-mode with '
    "henvcfg.SSE=0 sees senvcfg.SSE=0 whatever HS-mode wrote."
)
ISSUE_2708 = (
    f"{ISSUE}2708: the bullets apply in order; with menvcfg.SSE=0 the exception is illegal-instruction in VS and "
    'VU too, "not a virtual instruction" (ved-rivos).'
)


@section
def csr_tests(tests: list) -> None:
    # ---- ssp_op ----
    t = new("ssp_op")
    t.describe(
        source=UCFI,
        rule_text="The ssp CSR is an unprivileged read-write (URW) CSR that reads and writes XLEN low order bits of "
        "the shadow stack pointer.",
        context="Access below M-mode is gated by menvcfg/senvcfg/henvcfg.SSE (Zicfiss_ssp_csr), so all three are set. "
        "Bits 1:0 are read-only zero, and on RV64 bit 2 may be (ssp_field_1_0): values written here keep RV64 bit 2 "
        "clear, and expectations clear bits 1:0.",
        plan="1. S-mode: every CSR instruction form (csrrw with rd=x0 and rd!=x0, csrrs/csrrc with rs1=x0 and rs1!=x0, "
        "csrrwi, csrrsi with uimm=0, csrrci) on random old and source values returns the old value and leaves the "
        "value the form defines.\n"
        "2. U-mode: the read, swap, set, clear and immediate forms, with the result read back in S-mode.\n"
        "3. One register for every mode: a value written in S-mode is read in U-mode, and the reverse.\n"
        "4. With H: the swap form in VS-mode and VU-mode, read back in HS-mode.",
    )
    enables(t, 1, 1, 1)
    for form in FORMS:
        form_case(t, "S", form, "every SSE enable set")
    for i in (0, 2, 3, 4, 5, 7):
        form_case(t, "U", FORMS[i], "every SSE enable set")
    v = X(t.rand(32) & ~3, t.rand(64) & ~7)
    set_ssp(t, v, "written in S-mode")
    lab = run(t, "U", ["csrr x7, 0x011  // ssp"])
    t.check("x7", v, lab, "U-mode reads the ssp value S-mode wrote")
    v = X(t.rand(32) & ~3, t.rand(64) & ~7)
    lab = run(t, "U", ["csrw 0x011, x6  // ssp"], pre=pre_load(t, "x6", v, "written in U-mode"))
    ssp_check(t, v, lab, "S-mode reads the ssp value U-mode wrote")
    with t.only_if(H):
        for mode in ("VS", "VU"):
            form_case(t, mode, FORMS[2], "every SSE enable set")
    teardown(t)
    tests.append(t)

    # ---- ssp_addr ----
    t = new("ssp_addr")
    t.describe(
        source=UCFI,
        rule_text="The CSR address is 0x011.",
        context="CSR 0x011 must be the shadow stack pointer that the shadow-stack instructions use: ssrdp moves ssp to "
        "a register (ssrdp_read).",
        plan="1. S-mode: write CSR 0x011 with edge and random values; ssrdp returns each value (bits 1:0, and RV64 "
        "bit 2, are cleared in the values).\n"
        "2. U-mode writes CSR 0x011; ssrdp in S-mode returns the value. S-mode writes CSR 0x011; ssrdp in U-mode "
        "returns it.\n"
        "3. ssrdp after csrrs/csrrc on CSR 0x011 sees the modified value.",
    )
    enables(t, 1, 1)
    vals = [X(e.num(32) & ~3, e.num(64) & ~7) for e in EDGES] + [X(t.rand(32) & ~3, t.rand(64) & ~7) for _ in range(3)]
    for v in vals:
        set_ssp(t, v)
        lab = run(t, "S", [word(ssrdp("x7"), "ssrdp x7")])
        t.check("x7", v, lab, "ssrdp returns the value written to CSR 0x011")
    v = vals[-1]
    lab = run(t, "U", ["csrw 0x011, x8  // ssp"], pre=pre_load(t, "x8", v))
    t.emit(word(ssrdp("x7"), "ssrdp x7"))
    t.check("x7", v, lab, "ssrdp in S-mode returns the value U-mode wrote to CSR 0x011")
    v = vals[-2]
    set_ssp(t, v)
    lab = run(t, "U", [word(ssrdp("x7"), "ssrdp x7")])
    t.check("x7", v, lab, "ssrdp in U-mode returns the value S-mode wrote to CSR 0x011")
    t.li("x6", 0x30)
    t.emit("csrs 0x011, x6")
    t.emit(word(ssrdp("x8"), "ssrdp x8"))
    lab = t.label("rs")
    t.emit(f"{lab}:", 0)
    t.check("x8", X(v.num(32) | 0x30, v.num(64) | 0x30), lab, "ssrdp after csrs 0x011, 0x30")
    t.emit("csrc 0x011, x6")
    t.emit(word(ssrdp("x8"), "ssrdp x8"))
    t.check("x8", X(v.num(32) & ~0x30, v.num(64) & ~0x30), lab, "ssrdp after csrc 0x011, 0x30")
    teardown(t)
    tests.append(t)

    # ---- ssp_sz ----
    t = new("ssp_sz")
    t.describe(
        source=UCFI,
        rule_text="There is no high CSR defined as the ssp is always as wide as the XLEN of the current privilege mode.",
        context="ssp holds XLEN bits (bits 1:0 read-only zero; RV64 bit 2 may be read-only zero, ssp_field_1_0), so "
        "the checks cover bits XLEN-1:3 on RV64 and XLEN-1:2 on RV32.",
        plan="1. Write edge values (0, all ones, MSB only, 0x55.., 0xAA.., 1, MAX) and random values in S-mode; every "
        "implemented bit reads back, including bits 63:32 on RV64.\n"
        "2. RV64: set and clear bit 63 and bit 32 with csrrs/csrrc; only that bit changes.\n"
        "3. U-mode writes all ones; S-mode reads all the implemented bits set.",
    )
    enables(t, 1, 1)
    lm = X(mask(~3, 32), mask(~7, 64))
    for v in EDGES + [t.rand_x() for _ in range(3)]:
        set_ssp(t, v)
        lab = t.label("rd")
        t.emit(f"{lab}:", 0)
        read_ssp(t, "x7")
        exp = X(held(v.num(32), 32) & lm.num(32), held(v.num(64) & ~4, 64) & lm.num(64))
        t.check_masked("x7", lm, exp, lab, "ssp holds every implemented bit written")
    with t.rv64_only():
        base = t.rand(64) & ~7
        set_ssp(t, X(0, base & ~((1 << 63) | (1 << 32))))
        for bit in (63, 32):
            t.li("x6", 1)
            t.emit(f"slli x6, x6, {bit}")
            lab = t.label("bit")
            t.emit(f"{lab}:", 0)
            t.emit("csrs 0x011, x6")
            read_ssp(t, "x7")
            exp = held(base & ~((1 << 63) | (1 << 32)) | (1 << bit), 64)
            t.check("x7", X(0, exp), lab, f"csrs sets ssp bit {bit} only")
            t.emit("csrc 0x011, x6")
            read_ssp(t, "x7")
            t.check("x7", X(0, held(base & ~((1 << 63) | (1 << 32)), 64)), lab, f"csrc clears ssp bit {bit} only")
    lab = run(t, "U", ["csrw 0x011, x6  // ssp"], pre=lambda: t.li("x6", -1))
    read_ssp(t, "x7")
    t.check_masked(
        "x7",
        lm,
        X(held(0xFFFFFFFF, 32) & lm.num(32), held((1 << 64) - 1, 64) & lm.num(64)),
        lab,
        "ssp written to all ones in U-mode holds every implemented bit",
    )
    teardown(t)
    tests.append(t)

    # ---- ssp_field_1_0 ----
    t = new("ssp_field_1_0")
    t.describe(
        source=UCFI,
        rule_text="The bits 1:0 of ssp are read-only zero. If the UXLEN or SXLEN may never be 32, then the bit 2 is "
        "also read-only zero.",
        context="On RV32, UXLEN and SXLEN are 32, so bit 2 is writable. On RV64, bit 2 is writable only if UXLEN or "
        "SXLEN can be 32; the test probes mstatus.UXL (writing UXL=1 and reading it back, in M-mode through T-SBI). If "
        "UXL can be 32, bit 2 must hold a written 1; otherwise (SXL is not probed, as S-mode runs the test) bit 2 may "
        "read 0 or 1.",
        plan="1. Bits 1:0 read 0 after csrw of all ones, csrrs of 3, csrrwi of 0x1B and csrrsi of 3, in S-mode, and "
        "after a U-mode csrw of 0x13.\n"
        "2. The other written bits are kept (bits 1:0 are read-only, not the whole register).\n"
        "3. RV32: bit 2 is writable (set with csrrsi 4, cleared with csrrci 4).\n"
        "4. RV64: probe mstatus.UXL; if it can be 1 (32-bit U-mode), bit 2 is writable; otherwise it reads 0 or the "
        'written 1 (SXL is not probed; the rule\'s "UXLEN or SXLEN may never be 32" is read as "neither can be 32").',
    )
    enables(t, 1, 1)
    low = 3 if MUT == "ssp_low_writable" else 0
    cases = [
        ("csrw 0x011, x6", lambda: t.li("x6", -1), "csrw all ones"),
        ("csrrs x0, 0x011, x6", lambda: t.li("x6", 3), "csrrs 3"),
        ("csrrwi x0, 0x011, 0x1B", None, "csrrwi 0x1B"),
        ("csrrsi x0, 0x011, 3", None, "csrrsi 3"),
    ]
    for asm, setup, note in cases:
        t.emit("csrw 0x011, x0")
        if setup:
            setup()
        lab = t.label("lo")
        t.emit(f"{lab}:", 0)
        t.emit(asm + "  // ssp")
        read_ssp(t, "x7")
        t.check_masked("x7", 3, low, lab, f"ssp bits 1:0 after {note} in S-mode")
        if note == "csrrwi 0x1B":
            t.check_masked("x7", 0x18, 0x18, lab, "csrrwi 0x1B keeps bits 4:3 (only bits 1:0 are read-only)")
    lab = run(t, "U", ["csrw 0x011, x6  // ssp"], pre=lambda: t.li("x6", 0x13))
    read_ssp(t, "x7")
    t.check_masked("x7", 0x13, 0x10 | low, lab, "ssp bits 1:0 after a U-mode csrw of 0x13")
    with t.rv32_only():
        t.emit("csrw 0x011, x0")
        lab = t.label("b2")
        t.emit(f"{lab}:", 0)
        t.emit("csrrsi x0, 0x011, 4")
        read_ssp(t, "x7")
        t.check("x7", 4, lab, "RV32: ssp bit 2 is writable (set)")
        t.emit("csrrci x0, 0x011, 4")
        read_ssp(t, "x7")
        t.check("x7", 0, lab, "RV32: ssp bit 2 is writable (cleared)")
    with t.rv64_only():
        t.comment("probe mstatus.UXL: can U-mode be 32-bit?")
        t.tsbi_csr("READ", "MSTATUS")
        t.emit("mv x8, a0")
        t.li("a1", 1)
        t.emit("slli a1, a1, 33")
        t.tsbi_csr("CLEAR", "MSTATUS", "a1")
        t.li("a1", 1)
        t.emit("slli a1, a1, 32")
        t.tsbi_csr("SET", "MSTATUS", "a1")
        t.tsbi_csr("READ", "MSTATUS")
        t.emit("srli x9, a0, 32")
        t.emit("andi x9, x9, 3")
        t.emit("addi x9, x9, -1")
        t.emit("seqz x9, x9  // x9 = 1: UXL can be 1 (32-bit)")
        t.comment("restore mstatus.UXL")
        t.li("a1", 3)
        t.emit("slli a1, a1, 32")
        t.tsbi_csr("CLEAR", "MSTATUS", "a1")
        t.emit("and a1, a1, x8")
        t.tsbi_csr("SET", "MSTATUS", "a1")
        t.emit("csrw 0x011, x0")
        t.emit("csrrsi x0, 0x011, 4")
        read_ssp(t, "x7")
        lab = t.label("b2")
        t.emit(f"{lab}:", 0)

        def must() -> None:
            t.check("x7", 4, lab, "RV64 with UXL=32 possible: ssp bit 2 is writable")

        def may() -> None:
            t.check("x7", [0, 4], lab, "RV64, UXL fixed at 64: ssp bit 2 reads 0 (read-only zero) or the written 1")

        t.either("x9", must, may)
    teardown(t)
    tests.append(t)

    # ---- Zicfiss_ssp_csr (overview: the whole decision list) ----
    t = new("Zicfiss_ssp_csr")
    t.describe(
        source=PCFI,
        rule_text="Attempts to access the ssp CSR may result in either an illegal-instruction exception or a "
        "virtual-instruction exception, contingent upon the state of the envcfg[sse] fields.",
        context="The conditions are the bullets Zicfiss_m_menvcfg_sse, Zicfiss_u_senvcfg_sse, Zicfiss_vs_henvcfg_sse, "
        "Zicfiss_vu_senvcfg_sse and Zicfiss_sse_access, applied in order. With V=1 and henvcfg.SSE=0, senvcfg.SSE is "
        "read-only zero (henvcfg_sse_op), so VU-mode then also sees senvcfg.SSE=0.",
        issues=ISSUE_2708 + "\n" + ISSUE_2424,
        plan="1. Sweep menvcfg.SSE, senvcfg.SSE and henvcfg.SSE over all eight combinations. senvcfg/henvcfg are "
        "written while menvcfg.SSE=1 (they are read-only zero otherwise), then menvcfg.SSE is set as the case needs.\n"
        "2. In each combination, read ssp (csrrs rs1=x0) in S, U and, with H, VS and VU; expect: below M with "
        "menvcfg.SSE=0 illegal; U with senvcfg.SSE=0 illegal; VS with henvcfg.SSE=0 virtual; VU with senvcfg.SSE=0 "
        "(or henvcfg.SSE=0) virtual; otherwise allowed. Illegal and virtual traps leave xtval 0 or the instruction "
        "bits.\n"
        "3. In each combination, write ssp (csrrw rd=x0) in U-mode; a denied write leaves ssp unchanged.",
    )
    for m in (0, 1):
        for s in (0, 1):
            for h in (0, 1):
                desc = f"menvcfg.SSE={m}, senvcfg.SSE={s}, henvcfg.SSE={h}"
                t.comment(desc)
                enables(t, 1, s, h)
                set_ssp(t, X(0x1000, 0x1000), "known value")
                if not m:
                    menv_sse(t, False)
                for mode in ("S", "U"):
                    ssp_access(t, mode, READ, ssp_expect(mode, m, s, h), desc)
                with t.only_if(H):
                    for mode in ("VS", "VU"):
                        ssp_access(t, mode, READ, ssp_expect(mode, m, s, h), desc)
                t.li("x6", 0x2000)
                ex = ssp_expect("U", m, s, h)
                lab = ssp_access(t, "U", WRITE, ex, desc)
                menv_sse(t, True)
                ssp_check(t, 0x2000 if ex == "ok" else 0x1000, lab, f"ssp after a U-mode write ({desc})")
    teardown(t)
    tests.append(t)

    # ---- Zicfiss_m_menvcfg_sse ----
    t = new("Zicfiss_m_menvcfg_sse")
    t.describe(
        source=PCFI,
        rule_text="If the privilege mode is less than M and menvcfg[sse] is 0, an illegal-instruction exception is "
        "raised.",
        context="This bullet comes first, so it applies in VS and VU too (illegal, not virtual). senvcfg.SSE and "
        "henvcfg.SSE are read-only zero while menvcfg.SSE=0 (menvcfg_sse_rdonly0).",
        issues=ISSUE_2708,
        plan="1. menvcfg.SSE=0 (senvcfg.SSE and henvcfg.SSE were set while it was 1): every CSR form on ssp in "
        "S-mode raises illegal-instruction (xtval 0 or the instruction bits), and ssp is unchanged.\n"
        "2. The read and write forms raise illegal-instruction in U-mode and, with H, in VS and VU (not "
        "virtual-instruction).\n"
        "3. Transitions: setting menvcfg.SSE makes the S-mode read succeed; clearing it again makes it trap.",
    )
    enables(t, 1, 1, 1)
    set_ssp(t, X(0x3330, 0x3330), "known value")
    menv_sse(t, False)
    for form in FORMS:
        t.li("x6", 0x440)
        ssp_access(t, "S", form, "illegal", "menvcfg.SSE=0")
    for form in (READ, WRITE):
        t.li("x6", 0x440)
        ssp_access(t, "U", form, "illegal", "menvcfg.SSE=0, senvcfg.SSE set earlier")
    with t.only_if(H):
        for mode in ("VS", "VU"):
            for form in (READ, WRITE):
                t.li("x6", 0x440)
                ssp_access(t, mode, form, ssp_expect(mode, 0, 1, 1), "menvcfg.SSE=0, henvcfg.SSE set earlier")
    menv_sse(t, True)
    lab = ssp_access(t, "S", READ, "ok", "menvcfg.SSE set again")
    t.check("x7", 0x3330, lab, "ssp kept its value through the denied writes")
    menv_sse(t, False)
    ssp_access(t, "S", READ, "illegal", "menvcfg.SSE cleared again")
    teardown(t)
    tests.append(t)

    # ---- Zicfiss_u_senvcfg_sse ----
    t = new("Zicfiss_u_senvcfg_sse")
    t.describe(
        source=PCFI,
        rule_text="Otherwise, if in U-mode and senvcfg[sse] is 0, an illegal-instruction exception is raised.",
        context="menvcfg.SSE=1, so the first bullet does not apply. senvcfg.SSE does not gate S-mode.",
        plan="1. menvcfg.SSE=1, senvcfg.SSE=0 (henvcfg.SSE=1 with H, which must not matter): every CSR form on ssp "
        "in U-mode raises illegal-instruction (xtval 0 or the instruction bits); ssp is unchanged.\n"
        "2. S-mode reads and writes still succeed (negative dependency).\n"
        "3. Transitions: senvcfg.SSE=1 makes the U-mode read succeed; clearing it makes it trap again.",
    )
    enables(t, 1, 0, 1)
    set_ssp(t, X(0x5550, 0x5550), "known value")
    for form in FORMS:
        t.li("x6", 0x660)
        ssp_access(t, "U", form, ssp_expect("U", 1, 0, 1), "menvcfg.SSE=1, senvcfg.SSE=0")
    lab = ssp_access(t, "S", READ, "ok", "senvcfg.SSE=0 does not gate S-mode")
    t.check("x7", 0x5550 if MUT != "u_ignores_senvcfg" else 0x660, lab, "ssp unchanged by the denied U-mode writes")
    form_case(t, "S", FORMS[2], "senvcfg.SSE=0")
    senv_sse(t, True)
    ssp_access(t, "U", READ, "ok", "senvcfg.SSE set")
    senv_sse(t, False)
    ssp_access(t, "U", READ, ssp_expect("U", 1, 0, 1), "senvcfg.SSE cleared again")
    teardown(t)
    tests.append(t)

    # ---- Zicfiss_vs_henvcfg_sse ----
    t = new("Zicfiss_vs_henvcfg_sse", ["I", "S", "H", "Zicfiss"])
    t.describe(
        source=PCFI,
        rule_text="Otherwise, if in VS-mode and henvcfg[sse] is 0, a virtual-instruction exception is raised.",
        context="menvcfg.SSE=1. henvcfg.SSE does not gate HS-mode or VU-mode's senvcfg check (VU is covered by "
        "Zicfiss_vu_senvcfg_sse).",
        plan="1. menvcfg.SSE=1, henvcfg.SSE=0, senvcfg.SSE=1: every CSR form on ssp in VS-mode raises "
        "virtual-instruction (xtval 0 or the instruction bits); ssp is unchanged.\n"
        "2. The same with senvcfg.SSE=0.\n"
        "3. HS-mode access still succeeds (negative dependency).\n"
        "4. Transitions: henvcfg.SSE=1 makes the VS-mode read and write succeed; clearing it makes them trap again.",
    )
    enables(t, 1, 1, 0)
    set_ssp(t, X(0x7770, 0x7770), "known value")
    for form in FORMS:
        t.li("x6", 0x880)
        ssp_access(t, "VS", form, ssp_expect("VS", 1, 1, 0), "menvcfg.SSE=1, henvcfg.SSE=0, senvcfg.SSE=1")
    senv_sse(t, False)
    for form in (READ, WRITE):
        t.li("x6", 0x880)
        ssp_access(t, "VS", form, ssp_expect("VS", 1, 0, 0), "henvcfg.SSE=0, senvcfg.SSE=0")
    lab = ssp_access(t, "S", READ, "ok", "henvcfg.SSE=0 does not gate HS-mode")
    t.check("x7", 0x7770, lab, "ssp unchanged by the denied VS-mode writes")
    henv_sse(t, True)
    form_case(t, "VS", FORMS[2], "henvcfg.SSE set")
    henv_sse(t, False)
    ssp_access(t, "VS", READ, ssp_expect("VS", 1, 0, 0), "henvcfg.SSE cleared again")
    teardown(t)
    tests.append(t)

    # ---- Zicfiss_vu_senvcfg_sse ----
    t = new("Zicfiss_vu_senvcfg_sse", ["I", "S", "H", "Zicfiss"])
    t.describe(
        source=PCFI,
        rule_text="Otherwise, if in VU-mode and senvcfg[sse] is 0, a virtual-instruction exception is raised.",
        context="menvcfg.SSE=1. With V=1 and henvcfg.SSE=0, senvcfg.SSE is read-only zero (henvcfg_sse_op), so VU-mode "
        "also raises virtual-instruction when HS-mode set senvcfg.SSE but henvcfg.SSE=0.",
        issues=ISSUE_2424,
        plan="1. menvcfg.SSE=1, henvcfg.SSE=1, senvcfg.SSE=0: every CSR form on ssp in VU-mode raises "
        "virtual-instruction (xtval 0 or the instruction bits); ssp is unchanged.\n"
        "2. U-mode (V=0) with the same enables raises illegal-instruction instead (the U bullet).\n"
        "3. senvcfg.SSE=1: VU-mode reads and writes succeed.\n"
        "4. senvcfg.SSE=1 but henvcfg.SSE=0: VU-mode raises virtual-instruction (senvcfg.SSE reads zero when V=1).",
    )
    enables(t, 1, 0, 1)
    set_ssp(t, X(0x9990, 0x9990), "known value")
    for form in FORMS:
        t.li("x6", 0xAA0)
        ssp_access(t, "VU", form, ssp_expect("VU", 1, 0, 1), "menvcfg.SSE=1, henvcfg.SSE=1, senvcfg.SSE=0")
    ssp_access(t, "U", READ, ssp_expect("U", 1, 0, 1), "senvcfg.SSE=0, V=0")
    lab = ssp_access(t, "S", READ, "ok", "HS-mode")
    t.check("x7", 0x9990, lab, "ssp unchanged by the denied VU-mode writes")
    senv_sse(t, True)
    form_case(t, "VU", FORMS[2], "senvcfg.SSE=1, henvcfg.SSE=1")
    henv_sse(t, False)
    for form in (READ, WRITE):
        t.li("x6", 0xAA0)
        ssp_access(t, "VU", form, ssp_expect("VU", 1, 1, 0), "senvcfg.SSE=1 written by HS-mode, henvcfg.SSE=0")
    teardown(t)
    tests.append(t)

    # ---- Zicfiss_sse_access ----
    t = new("Zicfiss_sse_access")
    t.describe(
        source=PCFI,
        rule_text="Otherwise, the access is allowed.",
        context="With menvcfg.SSE, senvcfg.SSE and henvcfg.SSE set, no bullet applies in any mode below M. M-mode "
        "access is in Zicfiss_sse_access_Sm.",
        plan="1. All enables set: every CSR form on ssp succeeds in S-mode and U-mode, with the old value returned "
        "and the new value held.\n"
        "2. With H: every form in VS-mode and VU-mode.\n"
        "3. Only the needed enable: S-mode with senvcfg.SSE=0 and henvcfg.SSE=0; U-mode with henvcfg.SSE=0; VS-mode "
        "with senvcfg.SSE=0.",
    )
    enables(t, 1, 1, 1)
    for mode in ("S", "U"):
        for form in FORMS:
            form_case(t, mode, form, "every SSE enable set")
    with t.only_if(H):
        for mode in ("VS", "VU"):
            for form in FORMS:
                form_case(t, mode, form, "every SSE enable set")
    enables(t, 1, 0, 0)
    form_case(t, "S", FORMS[2], "only menvcfg.SSE set")
    enables(t, 1, 1, 0)
    form_case(t, "U", FORMS[2], "menvcfg.SSE and senvcfg.SSE set, henvcfg.SSE=0")
    with t.only_if(H):
        enables(t, 1, 0, 1)
        form_case(t, "VS", FORMS[2], "menvcfg.SSE and henvcfg.SSE set, senvcfg.SSE=0")
    teardown(t)
    tests.append(t)

    # ---- Zicfiss_sse_access_Sm ----
    t = new("Zicfiss_sse_access", REQ_M, boot="M", suffix="_Sm")
    t.describe(
        source=PCFI,
        rule_text="Otherwise, the access is allowed.",
        context="M-mode part: no bullet applies at privilege M, whatever menvcfg.SSE is (xSSE is 0 in M-mode, but ssp "
        "access is not gated by it).",
        plan="1. menvcfg.SSE=0: every CSR form on ssp in M-mode succeeds, with the old value returned and the new "
        "value held.\n"
        "2. menvcfg.SSE=1: the swap and set forms succeed.",
    )
    t.li("x6", SSE)
    t.emit("csrc menvcfg, x6")
    for form in FORMS:
        form_case_m(t, form, "menvcfg.SSE=0")
    t.li("x6", SSE)
    t.emit("csrs menvcfg, x6")
    for form in (FORMS[2], FORMS[3]):
        form_case_m(t, form, "menvcfg.SSE=1")
    t.li("x6", SSE)
    t.emit("csrc menvcfg, x6")
    tests.append(t)


def form_case_m(t: MemTest, form: Form, desc: str) -> None:
    old = X(t.rand(32), t.rand(64) & ~4)
    rs = X(t.rand(32), t.rand(64) & ~4)
    t.load("x6", old, "old ssp")
    t.emit("csrw 0x011, x6")
    t.load("x6", rs, "rs1 value")
    lab = t.window("M", [form[0] + "  // ssp"], "ok", f"{form[4]} of ssp ({desc})")
    r32, n32 = form_value(form, old.num(32), rs.num(32), 32)
    r64, n64 = form_value(form, old.num(64), rs.num(64), 64)
    if r32 is not None and r64 is not None:
        t.check("x7", X(held(r32, 32), held(r64, 64)), lab, f"{form[4]} of ssp in M-mode returns the old value")
    t.emit("csrr x7, 0x011")
    t.check("x7", X(held(n32, 32), held(n64, 64)), lab, f"ssp after {form[4]} in M-mode ({desc})")


def xsub(a: X, b: X | int) -> X:
    b = b if isinstance(b, X) else X(b, b)
    return X(mask(a.num(32) - b.num(32), 32), mask(a.num(64) - b.num(64), 64))


def xadd(a: X, b: X | int) -> X:
    b = b if isinstance(b, X) else X(b, b)
    return X(mask(a.num(32) + b.num(32), 32), mask(a.num(64) + b.num(64), 64))


def xmul(b: X, k: int) -> X:
    return X(b.num(32) * k, b.num(64) * k)


TOP = 0x800  # initial ssp offset in a shadow-stack page


def phys_load_w(t: MemTest, sym: str, off: int | X, reg: str) -> None:
    """reg = the 32-bit word at physical address sym+off, zero-extended (T-SBI lw in M-mode)."""
    o = off if isinstance(off, X) else X(off, off)
    with t.rv64_only():
        t.la("a1", f"{sym}+{o.num(64)}")
        t.emit("RVTEST_TSBI_LW", 120)
        t.emit("slli a0, a0, 32")
        t.emit("srli a0, a0, 32")
    with t.rv32_only():
        t.la("a1", f"{sym}+{o.num(32)}")
        t.emit("RVTEST_TSBI_LW", 120)
    if reg != "a0":
        t.emit(f"mv {reg}, a0")


def fixture(t: MemTest, extra: list[Map] | None = None, user: bool = True, ss_contents: dict | None = None) -> dict:
    """S-level map with an SS page for S-mode ("ss", U=0) and one for U-mode ("ssu", U=1), plus extra pages, and a
    U alias of the code. Returns {name: page index}."""
    maps = [Map("ss", SS, ss_contents or guard_page(t)), Map("ssu", SS | U, ss_contents or guard_page(t, seed=1))]
    maps += extra or []
    vm_setup(t, maps, user=user)
    return {m.name: i for i, m in enumerate(maps)}


def link_pre(
    t: MemTest, mode: str, link: str, value: Value, other: tuple[str, Value] | None = None
) -> Callable[[], object] | None:
    """Load the link register (and other, a second register). x5 is clobbered by AI_ALLOW and table loads cannot
    run in U-mode through the alias, so x5 is loaded from x8 or x9 (set beforehand) in the mode under test; x1 is set
    beforehand."""
    moves = []
    regs = [(link, value, "x8")] + ([(other[0], other[1], "x9")] if other else [])
    for reg, v, tmp in regs:
        if reg == "x5":
            t.load(tmp, v, "value for x5")
            moves.append(f"mv x5, {tmp}")
        else:
            t.load(reg, v, f"value for {reg}")
    if not moves:
        return None
    return lambda: [t.emit(m) for m in moves]


def ss_lines(insn: str, link: str = "x1") -> list[str]:
    if insn == "sspush":
        return [word(sspush(link), f"sspush {link}")]
    if insn == "sspopchk":
        return [word(sspopchk(link), f"sspopchk {link}")]
    if insn == "c.sspush":
        return hword(C_SSPUSH, "c.sspush x1")
    if insn == "c.sspopchk":
        return hword(C_SSPOPCHK, "c.sspopchk x5")
    raise ValueError(insn)


def ss_op(
    t: MemTest,
    mode: str,
    insn: str,
    link: str,
    value: Value,
    expect: Expect,
    desc: str,
    tval: Expect | None = None,
    other: tuple[str, Value] | None = None,
) -> str:
    """One shadow-stack push or pop in mode with link register link = value (inside a trap window unless it must
    succeed). other = (register, value) sets the other link register."""
    pre = link_pre(t, mode, link, value, other)
    lines = ss_lines(insn, link)
    if expect == "ok":
        return run(t, mode, lines, pre=pre)
    return win(t, mode, lines, expect, desc, tval, pre=pre)


def preset_tval(t: MemTest, v: int = 0x7F0) -> None:
    t.comment("preset stval, so a trap that does not write it is seen")
    t.li("x6", v)
    t.emit("csrw stval, x6")


def sw_tval() -> int:
    return mut("swcheck_tval0", SS_FAULT, 0)


def sw_cause() -> int:
    return mut("swcheck_cause_illegal", SWCHECK, ILLEGAL)


def store_cause(c: Expect) -> Expect:
    """Cause of a shadow-stack instruction's memory fault (ss_fault_exception_code), or the mutant's."""
    if MUT == "pop_fault_as_load" and isinstance(c, int):
        return {STORE_AF: 5, STORE_PF: LOAD_PF}.get(c, c)
    return c


def pop_values(t: MemTest, page: str, n: int, top: int = TOP) -> list[X]:
    data = page_bytes(t, page)
    return [xword(data, X(top + 4 * k, top + 8 * k)) for k in range(n)]


def pop_contents(seed: int) -> dict:
    """SS page contents for pops: distinct 8-byte words from 0x7C0, including an entry whose two halves are equal
    pairs that differ only above bit 31 (see pop tests)."""
    c = {
        0x7C0 + 8 * i: (8, (0x0123456789ABCDEF * (i + 3 + seed) ^ 0xF0E1D2C3B4A59687) & ((1 << 64) - 1))
        for i in range(16)
    }
    return c


@section
def insn_tests(tests: list) -> None:
    # ---- Zicfiss_enc ----
    t = new("Zicfiss_enc")
    t.describe(
        source=UCFI,
        rule_text="The zicfiss instructions, except ssamoswap.w and ssamoswap.d, are encoded using a subset of "
        "May-Be-Operation instructions defined by the zimop and zcmop extensions.",
        context="Only the listed subset is Zicfiss: sspush is mop.rr.7 with rd=x0, rs1=x0, rs2=x1/x5; sspopchk is "
        "mop.r.28 with rd=x0, rs1=x1/x5; ssrdp is mop.r.28 with rs1=x0, rd!=x0; c.sspush is c.mop.1 and c.sspopchk "
        "c.mop.5. Other encodings of mop.rr.7 and mop.r.28, and other MOPs, keep their Zimop/Zcmop behavior (write 0 "
        "to rd; c.mop.n writes nothing) even while Zicfiss is active. satp is Bare, so a hart that wrongly treated one "
        "of them as a shadow-stack access would raise a store/AMO access fault, which the test does not permit.",
        plan="1. menvcfg.SSE=senvcfg.SSE=1, ssp holds a known value. In S-mode and U-mode, execute: mop.r.28 with "
        "rd=x7, rs1=x6 (not ssrdp: rs1!=x0); mop.rr.7 with rd=x7, rs2=x1 (not sspush: rd!=x0); mop.r.27 and mop.r.29 "
        "with rd=x7; each writes 0 to x7 (preset nonzero).\n"
        "2. No-op encodings next to the Zicfiss ones: mop.r.28 with rd=x0 and rs1=x6 or x0; mop.rr.7 with rd=x0 and "
        "rs1=x6 or rs2=x6; mop.r.27/mop.r.29 with rd=x0, rs1=x1/x5; mop.rr.6 with rs2=x1. None traps, and ssp is "
        "unchanged.\n"
        "3. With Zcmop: c.mop.3 and c.mop.7 change no register (x1, x5 and ssp checked).",
    )
    enables(t, 1, 1)
    sp = X(0x12345670 & ~3, 0x123456789ABCDEF0 & ~7)
    set_ssp(t, sp, "ssp")
    zero_ops = [
        (mop_r(28, "x7", "x6"), "mop.r.28 x7, x6 (rs1!=x0: not ssrdp)"),
        (mop_rr7("x7", "x0", "x1"), "mop.rr.7 x7, x0, x1 (rd!=x0: not sspush)"),
        (mop_rr7("x7", "x6", "x5"), "mop.rr.7 x7, x6, x5"),
        (mop_r(27, "x7", "x0"), "mop.r.27 x7, x0"),
        (mop_r(29, "x7", "x0"), "mop.r.29 x7, x0"),
    ]
    nops = [
        (mop_r(28, "x0", "x6"), "mop.r.28 x0, x6 (rs1 not x1/x5: not sspopchk)"),
        (mop_r(28, "x0", "x0"), "mop.r.28 x0, x0 (ssrdp with rd=x0 is not supported: a no-op)"),
        (mop_rr7("x0", "x6", "x1"), "mop.rr.7 x0, x6, x1 (rs1!=x0: not sspush)"),
        (mop_rr7("x0", "x0", "x6"), "mop.rr.7 x0, x0, x6 (rs2 not x1/x5: not sspush)"),
        (mop_r(27, "x0", "x1"), "mop.r.27 x0, x1"),
        (mop_r(29, "x0", "x5"), "mop.r.29 x0, x5"),
        (mop_rr7("x0", "x0", "x1") ^ (1 << 30), "mop.rr.3 x0, x0, x1"),
    ]
    for mode in ("S", "U"):
        for e, note in zero_ops:
            t.li("x6", 0x40)
            t.li("x7", 0x3C)
            lab = run(t, mode, [word(e, note)])
            exp = sp if (MUT == "mop_ssrdp" and e == zero_ops[0][0]) else 0
            t.check("x7", exp, lab, f"{note} in {mode}-mode writes 0 to rd")
            ssp_check(t, sp, lab, f"{note} in {mode}-mode leaves ssp unchanged")
        for e, note in nops:
            t.li("x6", 0x40)
            t.li("x1", 0x11)
            lab = run(t, mode, [word(e, note)])
            ssp_check(t, sp, lab, f"{note} in {mode}-mode: no trap, ssp unchanged")
    with t.only_if(ZC):
        for mode in ("S", "U"):
            for n in (3, 7):
                t.li("x1", 0x111)
                lab = run(t, mode, [*hword(c_mop(n), f"c.mop.{n}"), "mv x7, x5"], pre=lambda: t.li("x5", 0x555))
                t.check("x1", 0x111, lab, f"c.mop.{n} in {mode}-mode leaves x1")
                t.check("x7", 0x555, lab, f"c.mop.{n} in {mode}-mode leaves x5")
                ssp_check(t, sp, lab, f"c.mop.{n} in {mode}-mode leaves ssp unchanged")
    teardown(t)
    tests.append(t)

    # ---- Zicfiss_ssrdp_enc ----
    t = new("Zicfiss_ssrdp_enc")
    t.describe(
        source=UCFI,
        rule_text="ssrdp - encoded using mop.r.28",
        context="ssrdp rd is mop.r.28 with rs1=x0 (0xCDC04073 | rd << 7). While Zicfiss is active it moves ssp to rd.",
        plan="1. menvcfg.SSE=senvcfg.SSE=1. ssrdp with rd = x1, x6, x7, x8, x9 in S-mode returns ssp (a different "
        "random value each time).\n"
        "2. The same in U-mode with rd = x1 and x9.\n"
        "3. The neighbor encoding with rs1=x1 and rd!=x0 (mop.r.28, not ssrdp) writes 0.",
    )
    enables(t, 1, 1)
    for mode, rds in (("S", ["x1", "x6", "x7", "x8", "x9"]), ("U", ["x1", "x9"])):
        for rd in rds:
            v = X(t.rand(32) & ~3, t.rand(64) & ~7)
            set_ssp(t, v)
            t.li(rd, 0x77)
            lab = run(t, mode, [word(ssrdp(rd), f"ssrdp {rd}")])
            t.check(rd, mut("ssrdp_inactive_ssp", v, v), lab, f"ssrdp {rd} in {mode}-mode returns ssp")
    t.li("x7", 0x77)
    lab = run(t, "S", [word(mop_r(28, "x7", "x1"), "mop.r.28 x7, x1 (not ssrdp)")])
    t.check("x7", 0, lab, "mop.r.28 with rs1=x1, rd=x7 is not ssrdp: writes 0")
    teardown(t)
    tests.append(t)

    # ---- ssrdp_read ----
    t = new("ssrdp_read")
    t.describe(
        source=UCFI,
        rule_text="The ssrdp instruction is provided to move the contents of ssp to a destination register.",
        context="The operation listing: if xSSE == 1, X(dst) = ssp, else X(dst) = 0. xSSE is menvcfg.SSE in S, "
        "senvcfg.SSE in U and VU, henvcfg.SSE in VS (and senvcfg.SSE reads zero in VU while henvcfg.SSE=0). ssrdp "
        "makes no memory access, so satp stays Bare. M-mode (xSSE=0) is in ssrdp_read_Sm.",
        issues=ISSUE_2424,
        plan="1. All enables set: ssrdp returns ssp for edge and random values in S-mode, and for one value each in "
        "U, VS and VU.\n"
        "2. Inactive: ssrdp writes 0 (rd preset nonzero) in S with menvcfg.SSE=0, U with senvcfg.SSE=0, VS with "
        "henvcfg.SSE=0, VU with senvcfg.SSE=0, and VU with senvcfg.SSE=1 but henvcfg.SSE=0.\n"
        "3. Active again: ssrdp returns ssp.",
    )
    enables(t, 1, 1, 1)
    for v in [X(e.num(32) & ~3, e.num(64) & ~7) for e in EDGES] + [X(t.rand(32) & ~3, t.rand(64) & ~7)]:
        set_ssp(t, v)
        lab = run(t, "S", [word(ssrdp("x7"), "ssrdp x7")])
        t.check("x7", v, lab, "ssrdp in S-mode returns ssp")
    modes = [("U", None), ("VS", H), ("VU", H)]
    for mode, cond in modes:
        v = X(t.rand(32) & ~3, t.rand(64) & ~7)

        def active(mode: str = mode, v: X = v) -> None:
            set_ssp(t, v)
            t.li("x7", 0x77)
            lab = run(t, mode, [word(ssrdp("x7"), "ssrdp x7")])
            t.check("x7", v, lab, f"ssrdp in {mode}-mode returns ssp (all enables set)")

        if cond:
            with t.only_if(cond):
                active()
        else:
            active()
    sp = X(0x2468ACE0, 0x2468ACE013579BD8)
    set_ssp(t, sp)
    inactive = [("S", 0, 1, 1, None), ("U", 1, 0, 1, None), ("VS", 1, 1, 0, H), ("VU", 1, 0, 1, H), ("VU", 1, 1, 0, H)]
    for mode, m, s, h, cond in inactive:
        desc = f"menvcfg.SSE={m}, senvcfg.SSE={s}, henvcfg.SSE={h}"

        def case(mode: str = mode, m: int = m, s: int = s, h: int = h, desc: str = desc) -> None:
            enables(t, m, s, h)
            t.li("x7", 0x77)
            lab = run(t, mode, [word(ssrdp("x7"), "ssrdp x7")])
            exp = sp if MUT == "ssrdp_inactive_ssp" else 0
            if mode == "VU" and s and not h and MUT == "vu_ignores_henvcfg":
                exp = sp
            t.check("x7", exp, lab, f"ssrdp in {mode}-mode with Zicfiss inactive ({desc}) writes 0")

        if cond:
            with t.only_if(cond):
                case()
        else:
            case()
    enables(t, 1, 1, 1)
    lab = run(t, "S", [word(ssrdp("x7"), "ssrdp x7")])
    t.check("x7", sp, lab, "ssrdp in S-mode returns ssp again once active")
    teardown(t)
    tests.append(t)

    # ---- ssrdp_read_Sm ----
    t = new("ssrdp_read", REQ_M, boot="M", suffix="_Sm")
    t.describe(
        source=UCFI,
        rule_text="The ssrdp instruction is provided to move the contents of ssp to a destination register.",
        context="M-mode part. xSSE is 0 in M-mode (the xSSE table: M -> 0), so ssrdp writes 0 there, whatever "
        "menvcfg.SSE is.",
        issues=f"{ISSUE}1534: in M-mode the Zicfiss instructions execute as MOPs (ved-rivos).",
        plan="1. ssp = a nonzero value (M-mode write). ssrdp in M-mode writes 0 to rd (preset nonzero), with "
        "menvcfg.SSE=0 and with menvcfg.SSE=1.\n"
        "2. ssp still holds its value (csrr in M-mode).",
    )
    sp = X(0x13579BD8, 0x13579BDF2468ACE8 & ~7)
    t.load("x6", sp, "ssp")
    t.emit("csrw 0x011, x6")
    for on in (0, 1):
        t.li("x6", SSE)
        t.emit(f"{'csrs' if on else 'csrc'} menvcfg, x6")
        t.li("x7", 0x77)
        lab = t.window("M", [word(ssrdp("x7"), "ssrdp x7")], "ok", f"ssrdp with menvcfg.SSE={on}")
        t.check("x7", mut("ssrdp_inactive_ssp", 0, sp), lab, f"ssrdp in M-mode writes 0 (menvcfg.SSE={on})")
    t.emit("csrr x7, 0x011")
    t.check("x7", sp, lab, "ssp unchanged")
    t.li("x6", SSE)
    t.emit("csrc menvcfg, x6")
    tests.append(t)

    # ---- ss_push ----
    t = new("ss_push")
    t.describe(
        source=UCFI,
        rule_text="A shadow stack push operation is defined as decrement of the ssp by XLEN/8 followed by a store of "
        "the value in the link register to memory at the new top of the shadow stack.",
        context="Shadow-stack accesses need S-level translation and an SS page (xwr=010). The test maps an SS page "
        "for S-mode and a U=1 SS page for U-mode (Sv39/Sv32, probed), with ssp at offset 0x800. The page is preset with "
        "distinct guard words. Stored words are read back untranslated through T-SBI.",
        plan="1. S-mode: four pushes (sspush x1, sspush x5, alternating) of edge values (0, all ones, MSB, "
        "0x55..). After each, ssp has dropped by XLEN/8 and the word at the new top holds the link value.\n"
        "2. Afterwards the guard words at the original top and below the last push are unchanged.\n"
        "3. U-mode: two pushes on the U SS page, checked the same way.\n"
        "4. With Zcmop: c.sspush x1 pushes the same way.",
    )
    enables(t, 1, 1)
    ix = fixture(t)

    def pushes(mode: str, page: str, vals: list[X], insns: list[tuple[str, str]], at: int = TOP) -> None:
        top = va(ix[page], at)
        set_ssp(t, top, f"ssp = top of {page}")
        guard = page_bytes(t, page)
        for k, (v, (insn, link)) in enumerate(zip(vals, insns), 1):
            lab = ss_op(t, mode, insn, link, v, "ok", "")
            new_top = xsub(top, xmul(XB, k))
            ssp_check(
                t,
                top if MUT == "push_no_decrement" else new_top,
                lab,
                f"{insn} {link} #{k} in {mode}-mode: ssp dropped by XLEN/8",
            )
            off = xsub(X(at, at), xmul(XB, k - 1 if MUT == "push_store_old_top" else k))
            mem_check(t, page, off, v, lab, f"{insn} {link} #{k} in {mode}-mode stored the link value at the new top")
        lab = t.label("guard")
        t.emit(f"{lab}:", 0)
        mem_check(t, page, at, xword(guard, at), lab, f"{mode}-mode pushes left the word at the original top")
        below = xsub(X(at, at), xmul(XB, len(vals) + 1))
        mem_check(t, page, below, xword(guard, below), lab, f"{mode}-mode pushes left the word below the last push")

    def main_body1() -> None:
        pushes("S", "ss", EDGES[:4], [("sspush", "x1"), ("sspush", "x5"), ("sspush", "x1"), ("sspush", "x5")])
        pushes("U", "ssu", [t.rand_x(), t.rand_x()], [("sspush", "x5"), ("sspush", "x1")])

    vm_either(t, main_body1)
    with t.only_if(ZC):
        vm_either(t, lambda: pushes("S", "ss", [t.rand_x()], [("c.sspush", "x1")], at=0x780))
    vm_off(t)
    teardown(t)
    tests.append(t)


@section
def push_pop_tests(tests: list) -> None:
    # ---- sspush_c-sspush_instr ----
    t = new("sspush_c-sspush_instr")
    t.describe(
        source=UCFI,
        rule_text="The sspush instruction and its compressed form c.sspush can be used to push a link register on the "
        "shadow stack. The sspush and c.sspush instructions perform a store identically to the existing store "
        "instructions, with the difference that the base is implicitly ssp and the width is implicitly XLEN.",
        context="A store of XLEN bits at ssp - XLEN/8 (ss_push): little-endian, touching only those bytes, translated "
        "and checked like a store (U/SUM, invalid PTE), with faults reported as store/AMO faults "
        "(ss_fault_exception_code). Pages: SS for S, SS+U for U, an invalid PTE. Memory is read back untranslated "
        "through T-SBI in 32-bit words.",
        plan="1. S-mode sspush x1 of a value with distinct bytes: the 32-bit words at the slot hold its low and (RV64) "
        "high halves in little-endian order; the words just above and below the slot are unchanged.\n"
        "2. Base is ssp: two different ssp values put the store at each one's slot.\n"
        "3. Store-like translation: sspush on an invalid PTE raises a store/AMO page fault (15), xtval 0 or the slot "
        "address. From S-mode on the U=1 SS page with sstatus.SUM=0: store/AMO page fault; with SUM=1 it succeeds. "
        "From U-mode on the S-mode SS page (U=0): store/AMO page fault.\n"
        "4. With Zcmop: c.sspush x1 stores the same bytes, and faults the same way on the invalid PTE.",
    )
    enables(t, 1, 1)
    ix = fixture(t, [Map("inv", None)])
    val = X(0x8899AABB, 0x1122334455667788)
    other = X(0x0F1E2D3C, 0x0F1E2D3C4B5A6978)

    def bytes_case(mode: str, page: str, insn: str, at: int, v: X) -> None:
        top = va(ix[page], at)
        guard = page_bytes(t, page)
        set_ssp(t, top)
        lab = ss_op(t, mode, insn, "x1", v, "ok", "")
        slot = X(at - 4, at - 8)
        phys_load_w(t, f"ai_pg_{page}", slot, "a0")
        t.check(
            "a0",
            X(v.num(32), v.num(64) & 0xFFFFFFFF),
            lab,
            f"{insn} in {mode}-mode: low word at the slot (little-endian)",
        )
        with t.rv64_only():
            phys_load_w(t, f"ai_pg_{page}", at - 8 + 4, "a0")
            t.check("a0", X(0, v.num(64) >> 32), lab, f"{insn} in {mode}-mode: high word (RV64) at slot+4")
        phys_load_w(t, f"ai_pg_{page}", X(at, at), "a0")
        t.check(
            "a0",
            int.from_bytes(guard[at : at + 4], "little"),
            lab,
            f"{insn} in {mode}-mode: word above the slot unchanged",
        )
        below = X(at - 8, at - 12)
        phys_load_w(t, f"ai_pg_{page}", below, "a0")
        t.check(
            "a0",
            X(int.from_bytes(guard[at - 8 : at - 4], "little"), int.from_bytes(guard[at - 12 : at - 8], "little")),
            lab,
            f"{insn} in {mode}-mode: word below the slot unchanged",
        )

    def main_body2() -> None:
        bytes_case("S", "ss", "sspush", 0x800, val)
        bytes_case("S", "ss", "sspush", 0x880, other)
        set_ssp(t, va(ix["inv"], TOP))
        ss_op(
            t,
            "S",
            "sspush",
            "x1",
            val,
            store_cause(STORE_PF),
            "sspush through an invalid PTE",
            [0, xsub(va(ix["inv"], TOP), XB)],
        )
        set_ssp(t, va(ix["ssu"], TOP))
        ss_op(
            t,
            "S",
            "sspush",
            "x1",
            val,
            mut("sum_ignored", STORE_PF, "ok"),
            "sspush on a U=1 SS page with SUM=0",
            [0, xsub(va(ix["ssu"], TOP), XB)],
        )
        t.li("x6", SUM)
        t.emit("csrs sstatus, x6  // SUM=1")
        set_ssp(t, va(ix["ssu"], 0x900))
        lab = ss_op(t, "S", "sspush", "x1", val, "ok", "")
        mem_check(t, "ssu", X(0x900 - 4, 0x900 - 8), val, lab, "S-mode sspush on a U=1 SS page with SUM=1 stores")
        t.li("x6", SUM)
        t.emit("csrc sstatus, x6  // SUM=0")
        set_ssp(t, va(ix["ss"], TOP))
        ss_op(t, "U", "sspush", "x1", val, STORE_PF, "sspush on a U=0 SS page", [0, xsub(va(ix["ss"], TOP), XB)])
        bytes_case("U", "ssu", "sspush", 0x800, other)

    vm_either(t, main_body2)

    def c_body() -> None:
        bytes_case("S", "ss", "c.sspush", 0x780, other)
        set_ssp(t, va(ix["inv"], TOP))
        ss_op(
            t,
            "S",
            "c.sspush",
            "x1",
            val,
            STORE_PF,
            "c.sspush through an invalid PTE",
            [0, xsub(va(ix["inv"], TOP), XB)],
        )

    with t.only_if(ZC):
        vm_either(t, c_body)
    vm_off(t)
    teardown(t)
    tests.append(t)

    # ---- sspush_c-sspush_decrement ----
    t = new("sspush_c-sspush_decrement")
    t.describe(
        source=UCFI,
        rule_text="The ssp is decremented by sspush and c.sspush only if the store to the shadow stack completes "
        "successfully.",
        context="Failing stores: invalid PTE and read-only page (store/AMO page fault), RW page (store/AMO access "
        "fault, ssmp_ss_page_illegal_access).",
        plan="1. S-mode sspush x1 on an invalid PTE, a read-only page and an RW page: each traps and ssp is "
        "unchanged.\n"
        "2. A successful push right after decrements ssp by XLEN/8.\n"
        "3. U-mode: sspush x5 on the S-mode (U=0) SS page traps and leaves ssp; on the U SS page it decrements.\n"
        "4. With Zcmop: c.sspush on the invalid PTE leaves ssp; on the SS page it decrements.",
    )
    enables(t, 1, 1)
    ix = fixture(t, [Map("inv", None), Map("ro", RO), Map("rw", RW)])

    def fail(mode: str, page: str, insn: str, link: str, cause: int, note: str) -> None:
        top = va(ix[page], TOP)
        set_ssp(t, top)
        lab = ss_op(t, mode, insn, link, t.rand_x(), cause, f"{insn} {note}", [0, xsub(top, XB)])
        ssp_check(
            t,
            xsub(top, XB) if MUT == "push_decrement_on_fault" else top,
            lab,
            f"{insn} {link} {note} in {mode}-mode leaves ssp unchanged",
        )

    def ok(mode: str, page: str, insn: str, link: str) -> None:
        top = va(ix[page], TOP)
        set_ssp(t, top)
        lab = ss_op(t, mode, insn, link, t.rand_x(), "ok", "")
        ssp_check(t, xsub(top, XB), lab, f"a successful {insn} {link} in {mode}-mode decrements ssp")

    def main_body3() -> None:
        fail("S", "inv", "sspush", "x1", STORE_PF, "through an invalid PTE")
        fail("S", "ro", "sspush", "x5", STORE_PF, "on a read-only page")
        fail("S", "rw", "sspush", "x1", STORE_AF, "on an RW page")
        ok("S", "ss", "sspush", "x1")
        fail("U", "ss", "sspush", "x5", STORE_PF, "on a U=0 page")
        ok("U", "ssu", "sspush", "x5")

    vm_either(t, main_body3)
    with t.only_if(ZC):
        vm_either(
            t,
            lambda: (
                fail("S", "inv", "c.sspush", "x1", STORE_PF, "through an invalid PTE"),
                ok("S", "ss", "c.sspush", "x1"),
            ),
        )
    vm_off(t)
    teardown(t)
    tests.append(t)

    # ---- ss_pop ----
    t = new("ss_pop")
    t.describe(
        source=UCFI,
        rule_text="A shadow stack pop operation is defined as an XLEN wide read from the current top of the shadow "
        "stack followed by an increment of the ssp by XLEN/8.",
        context="The SS pages are preset with distinct XLEN-bit words from offset 0x7C0. sspopchk pops the word at "
        "ssp and compares it with the link register; with a matching link value the pop completes.",
        plan="1. S-mode: four pops (sspopchk x1, sspopchk x5, alternating) from offset 0x800 with link values equal to "
        "the words there. After each, ssp has risen by XLEN/8.\n"
        "2. A pop reads, not writes: the popped words are unchanged in memory.\n"
        "3. A push followed by a pop of the same value returns ssp to where it was.\n"
        "4. U-mode: two pops on the U SS page.\n"
        "5. With Zcmop: c.sspopchk x5 pops the same way.",
    )
    enables(t, 1, 1)
    ix = fixture(t, ss_contents=pop_contents(0))

    def pops(mode: str, page: str, n: int, insns: list[tuple[str, str]], at: int = TOP) -> None:
        top = va(ix[page], at)
        set_ssp(t, top)
        vals = pop_values(t, page, n, at)
        for k, (v, (insn, link)) in enumerate(zip(vals, insns), 1):
            lab = ss_op(t, mode, insn, link, v, "ok", "")
            ssp_check(
                t,
                top if MUT == "pop_no_increment" else xadd(top, xmul(XB, k)),
                lab,
                f"{insn} {link} #{k} in {mode}-mode: ssp rose by XLEN/8",
            )
        lab = t.label("unchanged")
        t.emit(f"{lab}:", 0)
        mem_check(t, page, X(at, at), vals[0], lab, f"the first word popped in {mode}-mode is unchanged in memory")

    def main_body4() -> None:
        pops("S", "ss", 4, [("sspopchk", "x1"), ("sspopchk", "x5"), ("sspopchk", "x1"), ("sspopchk", "x5")])
        top = va(ix["ss"], 0x840)
        set_ssp(t, top)
        v = t.rand_x()
        ss_op(t, "S", "sspush", "x1", v, "ok", "")
        lab = ss_op(t, "S", "sspopchk", "x5", v, "ok", "")
        ssp_check(t, top, lab, "sspush then sspopchk of the same value restores ssp")
        pops("U", "ssu", 2, [("sspopchk", "x5"), ("sspopchk", "x1")])

    vm_either(t, main_body4)
    with t.only_if(ZC):
        vm_either(t, lambda: pops("S", "ss", 2, [("c.sspopchk", "x5"), ("c.sspopchk", "x5")], at=0x7D0))
    vm_off(t)
    teardown(t)
    tests.append(t)

    # ---- sspopchk_shadow_return_pop ----
    t = new("sspopchk_shadow_return_pop")
    t.describe(
        source=UCFI,
        rule_text="The sspopchk instruction, and its compressed form c.sspopchk, can be used to pop the shadow return "
        "address value from the shadow stack and check that the value matches the contents of the link register, and "
        'if not cause a software-check exception with xtval set to "shadow stack fault (code=3)".',
        context="The comparison is bitwise over XLEN bits. A software check is cause 18; stval is preset to another "
        "value, so a trap that does not write it is seen. Software checks are delegated to S-mode by the framework, "
        "so U-mode checks are taken there too.",
        plan="1. S-mode: sspopchk x1 with a matching value pops (ssp rises).\n"
        "2. Mismatches, each raising cause 18 with stval = 3: the link value differs in bit 0, in the MSB, only in "
        "bit 32 (RV64: the low halves match), or is the value of the next slot.\n"
        "3. The checked register is the instruction's: sspopchk x1 with x5 matching and x1 not traps; sspopchk x5 "
        "with x5 matching and x1 not pops.\n"
        "4. U-mode: a mismatch raises cause 18 with stval = 3; a match pops.\n"
        "5. With Zcmop: c.sspopchk (x5) matching pops, mismatching raises cause 18 with stval = 3.",
    )
    enables(t, 1, 1)
    ix = fixture(t, ss_contents=pop_contents(1))

    def check_case(
        mode: str,
        page: str,
        insn: str,
        link: str,
        at: int,
        delta: X | None,
        desc: str,
        other: tuple[str, X] | None = None,
    ) -> None:
        top = va(ix[page], at)
        set_ssp(t, top)
        v = pop_values(t, page, 1, at)[0]
        link_v = v if delta is None else X(v.num(32) ^ delta.num(32), v.num(64) ^ delta.num(64))
        ok_case = delta is None
        if delta is not None and MUT == "pop_32bit_compare" and delta.num(64) >> 32 and not delta.num(64) & 0xFFFFFFFF:
            ok_case = True
        if MUT == "pop_checks_x1" and other is not None and link == "x5":
            ok_case = not ok_case
        preset_tval(t)
        if ok_case:
            lab = ss_op(t, mode, insn, link, link_v, "ok", "", other=other)
            ssp_check(t, xadd(top, XB), lab, f"{insn} {link} in {mode}-mode with {desc}: pops")
        else:
            lab = ss_op(t, mode, insn, link, link_v, sw_cause(), f"{insn} {link} with {desc}", sw_tval(), other=other)
            ssp_check(t, top, lab, f"{insn} {link} in {mode}-mode with {desc}: no pop")

    def main_body5() -> None:
        check_case("S", "ss", "sspopchk", "x1", 0x800, None, "a matching link value")
        check_case("S", "ss", "sspopchk", "x1", 0x800, X(1, 1), "bit 0 different")
        check_case("S", "ss", "sspopchk", "x5", 0x800, X(1 << 31, 1 << 63), "the MSB different")
        with t.rv64_only():
            check_case("S", "ss", "sspopchk", "x1", 0x800, X(0, 1 << 32), "only bit 32 different")
        v_next = pop_values(t, "ss", 2, 0x800)[1]
        top = va(ix["ss"], 0x800)
        set_ssp(t, top)
        preset_tval(t)
        lab = ss_op(t, "S", "sspopchk", "x1", v_next, sw_cause(), "sspopchk with the next slot's value", sw_tval())
        ssp_check(t, top, lab, "sspopchk with the next slot's value: no pop")
        v = pop_values(t, "ss", 1, 0x810)[0]
        check_case("S", "ss", "sspopchk", "x1", 0x810, X(0x10, 0x10), "x1 mismatching while x5 matches", ("x5", v))
        check_case(
            "S",
            "ss",
            "sspopchk",
            "x5",
            0x810,
            None,
            "x5 matching while x1 does not",
            ("x1", X(v.num(32) ^ 2, v.num(64) ^ 2)),
        )
        check_case("U", "ssu", "sspopchk", "x5", 0x800, X(0x80, 0x80), "bit 7 different")
        check_case("U", "ssu", "sspopchk", "x1", 0x800, None, "a matching link value")

    vm_either(t, main_body5)
    with t.only_if(ZC):
        vm_either(
            t,
            lambda: (
                check_case("S", "ss", "c.sspopchk", "x5", 0x7E0, X(4, 4), "bit 2 different"),
                check_case("S", "ss", "c.sspopchk", "x5", 0x7E0, None, "a matching link value"),
            ),
        )
    vm_off(t)
    teardown(t)
    tests.append(t)

    # ---- sspopchk_load_op ----
    t = new("sspopchk_load_op")
    t.describe(
        source=UCFI,
        rule_text="The sspopchk and c.sspopchk instructions perform a load identically to the existing load "
        "instructions, with the difference that the base is implicitly ssp and the width is implicitly XLEN.",
        context="The load reads XLEN bits at ssp. It is translated and protection-checked like a load (U/SUM, invalid "
        "PTE), but its faults are reported as store/AMO faults (ss_fault_exception_code). MXR does not matter: an "
        "SS page is always readable.",
        plan="1. Width: on RV64 a link value matching only the low 32 bits of the word at ssp raises the software "
        "check; matching all XLEN bits pops. Base: the word at ssp (not ssp - XLEN/8) is compared.\n"
        "2. Translation like a load: an invalid PTE raises a store/AMO page fault (15), xtval 0 or ssp. S-mode on the "
        "U=1 SS page with SUM=0: store/AMO page fault; with SUM=1 the pop succeeds. U-mode on the U=0 SS page: "
        "store/AMO page fault.\n"
        "3. sstatus.MXR=1 and MXR=0 both allow the pop.\n"
        "4. With Zcmop: c.sspopchk faults the same way on the invalid PTE.",
    )
    enables(t, 1, 1)
    ix = fixture(t, [Map("inv", None)], ss_contents=pop_contents(2))

    def pop_ok(mode: str, page: str, at: int, note: str, insn: str = "sspopchk", link: str = "x1") -> None:
        top = va(ix[page], at)
        set_ssp(t, top)
        v = pop_values(t, page, 1, at)[0]
        lab = ss_op(t, mode, insn, link, v, "ok", "")
        ssp_check(t, xadd(top, XB), lab, f"{insn} in {mode}-mode {note}: pops")

    def pop_fault(
        mode: str, page: str, at: int, cause: Expect, note: str, insn: str = "sspopchk", link: str = "x1"
    ) -> None:
        top = va(ix[page], at)
        set_ssp(t, top)
        v = pop_values(t, page, 1, at)[0] if page != "inv" else X(0, 0)
        lab = ss_op(t, mode, insn, link, v, cause, f"{insn} {note}", [0, top] if cause != SWCHECK else SS_FAULT)
        ssp_check(t, top, lab, f"{insn} in {mode}-mode {note}: ssp unchanged")

    def main_body6() -> None:
        with t.rv64_only():
            top = va(ix["ss"], 0x800)
            v = pop_values(t, "ss", 1, 0x800)[0]
            set_ssp(t, top)
            preset_tval(t)
            ex = "ok" if MUT == "pop_32bit_compare" else SWCHECK
            lab = ss_op(
                t,
                "S",
                "sspopchk",
                "x1",
                X(0, v.num(64) ^ (0xFF << 40)),
                ex,
                "link matching only the low 32 bits",
                None if ex == "ok" else SS_FAULT,
            )
            if ex != "ok":
                ssp_check(t, top, lab, "sspopchk compares all 64 bits: no pop")
        set_ssp(t, xadd(va(ix["ss"], 0x800), XB))
        prev = pop_values(t, "ss", 1, 0x800)[0]
        preset_tval(t)
        ss_op(t, "S", "sspopchk", "x1", prev, SWCHECK, "link = the word at ssp - XLEN/8 (wrong base)", SS_FAULT)
        pop_ok("S", "ss", 0x800, "with the word at ssp")
        pop_fault("S", "inv", TOP, store_cause(STORE_PF), "through an invalid PTE")
        pop_fault("S", "ssu", TOP, mut("sum_ignored", store_cause(STORE_PF), "ok"), "on a U=1 SS page with SUM=0")
        t.li("x6", SUM)
        t.emit("csrs sstatus, x6  // SUM=1")
        pop_ok("S", "ssu", 0x820, "on a U=1 SS page with SUM=1")
        t.li("x6", SUM)
        t.emit("csrc sstatus, x6  // SUM=0")
        pop_fault("U", "ss", TOP, store_cause(STORE_PF), "on a U=0 SS page")
        t.li("x6", MXR)
        t.emit("csrs sstatus, x6  // MXR=1")
        pop_ok("S", "ss", 0x830, "with MXR=1")
        t.li("x6", MXR)
        t.emit("csrc sstatus, x6  // MXR=0")
        pop_ok("U", "ssu", 0x830, "with MXR=0")

    vm_either(t, main_body6)
    with t.only_if(ZC):
        vm_either(
            t, lambda: pop_fault("S", "inv", TOP, store_cause(STORE_PF), "through an invalid PTE", "c.sspopchk", "x5")
        )
    vm_off(t)
    teardown(t)
    tests.append(t)

    # ---- sspop_exception ----
    t = new("sspop_exception")
    t.describe(
        source=UCFI,
        rule_text="If the value loaded from the address in ssp does not match the value in rs1, a software-check "
        'exception (cause=18) is raised with xtval set to "shadow stack fault (code=3)". The software-check '
        "exception caused by sspopchk or c.sspopchk is lower in priority than a load/store/AMO access-fault exception.",
        context="An access fault is raised when a shadow-stack instruction accesses a page that is neither SS nor "
        "read-only (ssmp_ss_page_illegal_access) or an RV64 ssp that is not 8-byte aligned (ssp_xlen_aligned); a "
        "read-only page gives a store/AMO page fault, which also prevents the comparison. stval is preset.",
        plan="1. Mismatch on an SS page: cause 18, stval = 3, xepc = the sspopchk, in S and U.\n"
        "2. Priority: sspopchk on an RW page whose word does not match the link register raises a store/AMO access "
        "fault (7), not the software check; the same on an RWX page and with the link value matching the word.\n"
        "3. On a read-only page with a mismatching link value: store/AMO page fault (15).\n"
        "4. With Zcmop: c.sspopchk on the RW page with a mismatch raises the access fault.",
    )
    enables(t, 1, 1)
    rwc = pop_contents(3)
    ix = fixture(t, [Map("rw", RW, rwc), Map("rwx", RWX, rwc), Map("ro", RO, rwc)], ss_contents=pop_contents(3))

    def case(mode: str, page: str, link: str, match: bool, cause: int, note: str, insn: str = "sspopchk") -> None:
        top = va(ix[page], TOP)
        set_ssp(t, top)
        v = pop_values(t, page, 1)[0]
        lv = v if match else X(v.num(32) ^ 0x100, v.num(64) ^ 0x100)
        preset_tval(t)
        if cause == STORE_AF and MUT == "swcheck_over_af" and not match:
            cause = SWCHECK
        tv: Expect = sw_tval() if cause == SWCHECK else [0, top]
        ss_op(t, mode, insn, link, lv, sw_cause() if cause == SWCHECK else store_cause(cause), f"{insn} {note}", tv)

    def main_body7() -> None:
        case("S", "ss", "x1", False, SWCHECK, "mismatch on an SS page")
        case("U", "ssu", "x5", False, SWCHECK, "mismatch on an SS page")
        case("S", "rw", "x1", False, mut("rw_page_ok", STORE_AF, SWCHECK), "mismatch on an RW page")
        case("S", "rwx", "x5", False, STORE_AF, "mismatch on an RWX page")
        case("S", "rw", "x5", True, STORE_AF, "match on an RW page")
        case("S", "ro", "x1", False, mut("ro_page_af", STORE_PF, STORE_AF), "mismatch on a read-only page")

    vm_either(t, main_body7)
    with t.only_if(ZC):
        vm_either(t, lambda: case("S", "rw", "x5", False, STORE_AF, "mismatch on an RW page", "c.sspopchk"))
    vm_off(t)
    teardown(t)
    tests.append(t)

    # ---- sspop_increment ----
    t = new("sspop_increment")
    t.describe(
        source=UCFI,
        rule_text="The ssp is incremented by sspopchk and c.sspopchk only if the load from the shadow stack completes "
        "successfully and no software-check exception is raised.",
        plan="1. S-mode sspopchk with a mismatch (software check), through an invalid PTE (store/AMO page fault), on "
        "an RW page (store/AMO access fault) and on a read-only page (store/AMO page fault): ssp unchanged each time.\n"
        "2. A matching pop right after: ssp rises by XLEN/8.\n"
        "3. U-mode: a mismatch leaves ssp; a match increments it.\n"
        "4. With Zcmop: c.sspopchk with a mismatch leaves ssp; with a match increments it.",
    )
    enables(t, 1, 1)
    c4 = pop_contents(4)
    ix = fixture(t, [Map("inv", None), Map("rw", RW, c4), Map("ro", RO, c4)], ss_contents=c4)

    def inc_case(mode: str, page: str, insn: str, link: str, match: bool, cause: Expect, note: str) -> None:
        top = va(ix[page], TOP)
        set_ssp(t, top)
        v = pop_values(t, page, 1)[0] if page != "inv" else X(0x1234, 0x1234)
        lv = v if match else X(v.num(32) ^ 8, v.num(64) ^ 8)
        tv: Expect = SS_FAULT if cause == SWCHECK else [0, top]
        lab = ss_op(t, mode, insn, link, lv, cause, f"{insn} {note}", tv)
        if cause == "ok":
            ssp_check(
                t,
                top if MUT == "pop_no_increment" else xadd(top, XB),
                lab,
                f"{insn} in {mode}-mode {note}: ssp incremented",
            )
        else:
            bad = MUT == "pop_increment_on_mismatch" and cause == SWCHECK
            ssp_check(t, xadd(top, XB) if bad else top, lab, f"{insn} in {mode}-mode {note}: ssp unchanged")

    def main_body8() -> None:
        inc_case("S", "ss", "sspopchk", "x1", False, SWCHECK, "with a mismatch")
        inc_case("S", "inv", "sspopchk", "x5", True, STORE_PF, "through an invalid PTE")
        inc_case("S", "rw", "sspopchk", "x1", True, STORE_AF, "on an RW page")
        inc_case("S", "ro", "sspopchk", "x5", True, STORE_PF, "on a read-only page")
        inc_case("S", "ss", "sspopchk", "x5", True, "ok", "with a match")
        inc_case("U", "ssu", "sspopchk", "x1", False, SWCHECK, "with a mismatch")
        inc_case("U", "ssu", "sspopchk", "x1", True, "ok", "with a match")

    vm_either(t, main_body8)
    with t.only_if(ZC):
        vm_either(
            t,
            lambda: (
                inc_case("S", "ss", "c.sspopchk", "x5", False, SWCHECK, "with a mismatch"),
                inc_case("S", "ss", "c.sspopchk", "x5", True, "ok", "with a match"),
            ),
        )
    vm_off(t)
    teardown(t)
    tests.append(t)


@section
def enc_swap_tests(tests: list) -> None:
    # ---- Zicfiss_sspush_enc ----
    t = new("Zicfiss_sspush_enc")
    t.describe(
        source=UCFI,
        rule_text="sspush x1 and sspush x5 - encoded using mop.rr.7",
        context="sspush rs2 is mop.rr.7 with rd=x0, rs1=x0: 0xCE104073 (x1) and 0xCE504073 (x5). Each pushes its own "
        "rs2 register.",
        plan="1. S-mode, x1 and x5 holding different values: 0xCE104073 pushes x1's value, 0xCE504073 pushes x5's "
        "value; ssp drops by XLEN/8 each time.\n"
        "2. The same in U-mode.",
    )
    enables(t, 1, 1)
    ix = fixture(t)

    def body1() -> None:
        for mode, page in (("S", "ss"), ("U", "ssu")):
            top = va(ix[page], TOP)
            set_ssp(t, top)
            for k, link in enumerate(("x1", "x5"), 1):
                v, w = t.rand_x(), t.rand_x()
                lab = ss_op(t, mode, "sspush", link, v, "ok", "", other=("x5" if link == "x1" else "x1", w))
                ssp_check(
                    t, xsub(top, xmul(XB, k)), lab, f"sspush {link} ({hex(sspush(link))}) in {mode}-mode moves ssp"
                )
                mem_check(
                    t,
                    page,
                    xsub(X(TOP, TOP), xmul(XB, k)),
                    v,
                    lab,
                    f"sspush {link} ({hex(sspush(link))}) in {mode}-mode pushes {link}, not the other link register",
                )

    vm_either(t, body1)
    vm_off(t)
    teardown(t)
    tests.append(t)

    # ---- Zicfiss_c-sspush_enc ----
    t = new("Zicfiss_c-sspush_enc", ["I", "S", "Zicfiss", "Zcmop"])
    t.describe(
        source=UCFI,
        rule_text="c.sspush x1 - encoded using c.mop.1",
        context="c.mop.1 is 0x6081. While Zicfiss is active it is c.sspush x1, which expands to sspush x1.",
        plan="1. S-mode, x1 and x5 holding different values: 0x6081 pushes x1's value and drops ssp by XLEN/8.\n"
        "2. The same in U-mode.\n"
        "3. The next compressed MOP, c.mop.3, pushes nothing (ssp unchanged).",
    )
    enables(t, 1, 1)
    ix = fixture(t)

    def body2() -> None:
        for mode, page in (("S", "ss"), ("U", "ssu")):
            top = va(ix[page], TOP)
            set_ssp(t, top)
            v, w = t.rand_x(), t.rand_x()
            lab = ss_op(t, mode, "c.sspush", "x1", v, "ok", "", other=("x5", w))
            ssp_check(t, xsub(top, XB), lab, f"c.sspush (0x6081) in {mode}-mode moves ssp")
            mem_check(t, page, X(TOP - 4, TOP - 8), v, lab, f"c.sspush (0x6081) in {mode}-mode pushes x1")
            lab = run(t, mode, hword(c_mop(3), "c.mop.3"))
            ssp_check(t, xsub(top, XB), lab, f"c.mop.3 in {mode}-mode pushes nothing")

    vm_either(t, body2)
    vm_off(t)
    teardown(t)
    tests.append(t)

    # ---- Zicfiss_sspopchk_enc ----
    t = new("Zicfiss_sspopchk_enc")
    t.describe(
        source=UCFI,
        rule_text="sspopchk x1 and sspopchk x5 - encoded using mop.r.28",
        context="sspopchk rs1 is mop.r.28 with rd=x0: 0xCDC0C073 (x1) and 0xCDC2C073 (x5). Each compares its own rs1 "
        "register with the popped value.",
        plan="1. S-mode: 0xCDC0C073 with x1 matching the top word (x5 not) pops; with x5 matching and x1 not, it raises "
        "the software check (cause 18, stval 3).\n"
        "2. 0xCDC2C073 with x5 matching (x1 not) pops; with x1 matching and x5 not, it raises the software check.\n"
        "3. U-mode: both encodings pop with their own register matching.",
    )
    enables(t, 1, 1)
    ix = fixture(t, ss_contents=pop_contents(5))

    def body3() -> None:
        for mode, page in (("S", "ss"), ("U", "ssu")):
            for link, oth in (("x1", "x5"), ("x5", "x1")):
                top = va(ix[page], TOP)
                v = pop_values(t, page, 1)[0]
                bad = X(v.num(32) ^ 0x40, v.num(64) ^ 0x40)
                if mode == "S":
                    set_ssp(t, top)
                    preset_tval(t)
                    ex = SWCHECK if not (MUT == "pop_checks_x1" and link == "x5") else "ok"
                    lab = ss_op(
                        t,
                        mode,
                        "sspopchk",
                        link,
                        bad,
                        ex,
                        f"sspopchk {link} with only {oth} matching",
                        None if ex == "ok" else SS_FAULT,
                        other=(oth, v),
                    )
                    if ex != "ok":
                        ssp_check(t, top, lab, f"sspopchk {link} with only {oth} matching does not pop")
                set_ssp(t, top)
                ex = "ok" if not (MUT == "pop_checks_x1" and link == "x5") else SWCHECK
                lab = ss_op(
                    t,
                    mode,
                    "sspopchk",
                    link,
                    v,
                    ex,
                    f"sspopchk {link} with {link} matching",
                    None if ex == "ok" else SS_FAULT,
                    other=(oth, bad),
                )
                ssp_check(
                    t,
                    xadd(top, XB) if ex == "ok" else top,
                    lab,
                    f"sspopchk {link} ({hex(sspopchk(link))}) in {mode}-mode pops when {link} matches",
                )

    vm_either(t, body3)
    vm_off(t)
    teardown(t)
    tests.append(t)

    # ---- Zicfiss_c-sspopchk_enc ----
    t = new("Zicfiss_c-sspopchk_enc", ["I", "S", "Zicfiss", "Zcmop"])
    t.describe(
        source=UCFI,
        rule_text="c.sspopchk x5 - encoded using c.mop.5",
        context="c.mop.5 is 0x6281. While Zicfiss is active it is c.sspopchk x5, which expands to sspopchk x5.",
        plan="1. S-mode: 0x6281 with x5 matching the top word (x1 not) pops.\n"
        "2. With x1 matching and x5 not, it raises the software check (cause 18, stval 3) and does not pop.\n"
        "3. U-mode: 0x6281 with x5 matching pops.\n"
        "4. The next compressed MOP, c.mop.7, pops nothing.",
    )
    enables(t, 1, 1)
    ix = fixture(t, ss_contents=pop_contents(6))

    def body4() -> None:
        for mode, page in (("S", "ss"), ("U", "ssu")):
            top = va(ix[page], TOP)
            v = pop_values(t, page, 1)[0]
            bad = X(v.num(32) ^ 0x40, v.num(64) ^ 0x40)
            set_ssp(t, top)
            ex = "ok" if MUT != "pop_checks_x1" else SWCHECK
            lab = ss_op(
                t,
                mode,
                "c.sspopchk",
                "x5",
                v,
                ex,
                "c.sspopchk with x5 matching",
                None if ex == "ok" else SS_FAULT,
                other=("x1", bad),
            )
            ssp_check(
                t, xadd(top, XB) if ex == "ok" else top, lab, f"c.sspopchk (0x6281) in {mode}-mode pops when x5 matches"
            )
            if mode == "S":
                set_ssp(t, top)
                preset_tval(t)
                ex = SWCHECK if MUT != "pop_checks_x1" else "ok"
                lab = ss_op(
                    t,
                    mode,
                    "c.sspopchk",
                    "x5",
                    bad,
                    ex,
                    "c.sspopchk with only x1 matching",
                    None if ex == "ok" else SS_FAULT,
                    other=("x1", v),
                )
                if ex != "ok":
                    ssp_check(t, top, lab, "c.sspopchk with only x1 matching does not pop")
                set_ssp(t, top)
                lab = run(t, mode, hword(c_mop(7), "c.mop.7"))
                ssp_check(t, top, lab, "c.mop.7 pops nothing")

    vm_either(t, body4)
    vm_off(t)
    teardown(t)
    tests.append(t)

    # ---- rv32_ssamoswap-w_op ----
    t = new("rv32_ssamoswap-w_op")
    t.describe(
        source=UCFI,
        rule_text="For RV32, ssamoswap.w atomically loads a 32-bit data value from address of a shadow stack location "
        "in rs1, puts the loaded value into register rd, and stores the 32-bit value held in rs2 to the original "
        "address in rs1. ssamoswap.d (RV64 only) is similar to ssamoswap.w but operates on 64-bit data values.",
        context="So the test runs ssamoswap.w on RV32 and ssamoswap.d on RV64 (an XLEN-wide swap), on SS pages. The "
        "pseudocode reads rs1 and rs2 before writing rd (#3433), so rd may alias either source. ssamoswap does not "
        "use ssp. RV64 ssamoswap.w is in rv64_ssamoswap-w_op.",
        issues=f"{ISSUE.replace('issues', 'pull')}3433: the SSAMOSWAP pseudocode writes rd last, so rd = rs1 or "
        "rd = rs2 still swaps with the original address and value.",
        plan="1. S-mode, on the SS page: swap edge and random values at several aligned offsets; rd gets the old word "
        "and memory holds rs2 (read back untranslated). aq/rl = 00, 01, 10, 11.\n"
        "2. rd = x0: memory is still written. rd = rs2 and rd = rs1: rd gets the old word and memory at the original "
        "address holds the original rs2.\n"
        "3. ssp is not used: ssp is unchanged and points elsewhere.\n"
        "4. U-mode on the U SS page: one swap.",
    )
    enables(t, 1, 1)
    sc = pop_contents(7)
    ix = fixture(t, ss_contents=sc)

    def body5() -> None:
        sp = va(ix["ss"], 0x100)
        set_ssp(t, sp, "ssp elsewhere")
        offs = [0x800, 0x808, 0x810, 0x818, 0x820, 0x828, 0x830, 0x838, 0x840]
        for i, v in enumerate(EDGES[:4] + [t.rand_x()]):
            swap1(t, ix, "S", "ss", offs[i], "x7", "x6", "x8", v, aq=i & 1, rl=(i >> 1) & 1)
        swap1(t, ix, "S", "ss", offs[5], "x0", "x6", "x8", t.rand_x())
        swap1(t, ix, "S", "ss", offs[6], "x8", "x6", "x8", t.rand_x())
        swap1(t, ix, "S", "ss", offs[7], "x6", "x6", "x8", t.rand_x())
        lab = t.label("ssp")
        t.emit(f"{lab}:", 0)
        ssp_check(t, sp, lab, "ssamoswap does not use or change ssp")
        swap1(t, ix, "U", "ssu", 0x880, "x7", "x6", "x8", t.rand_x())

    vm_either(t, body5)
    vm_off(t)
    teardown(t)
    tests.append(t)

    # ---- rv64_ssamoswap-w_op ----
    t = new("rv64_ssamoswap-w_op", rv64=True)
    t.describe(
        source=UCFI,
        rule_text="For RV64, ssamoswap.w atomically loads a 32-bit data value from address of a shadow stack location "
        "in rs1, sign-extends the loaded value and puts it in rd, and stores the lower 32 bits of the value held in rs2 "
        "to the original address in rs1.",
        context="RV64 only. The SS page is preset with words whose bit 31 is set or clear; the swaps use word-aligned "
        "addresses, including ones that are not doubleword aligned.",
        plan="1. S-mode ssamoswap.w on the SS page at offsets 0 and 4 of a doubleword: rd is the old 32-bit word, "
        "sign-extended (bit 31 set and clear).\n"
        "2. Memory: the 4 bytes hold rs2[31:0]; the other half of the doubleword is unchanged (rs2's upper half is "
        "not stored).\n"
        "3. rd = rs2 alias. U-mode: one swap on the U SS page.",
    )
    enables(t, 1, 1)
    c = {
        0x800: (4, 0x89ABCDEF),
        0x804: (4, 0x12345678),
        0x808: (4, 0xF0F0F0F0),
        0x80C: (4, 0x7F0F0F0F),
        0x810: (4, 0xDEADBEEF),
        0x814: (4, 0x0BADF00D),
    }
    ix = fixture(t, ss_contents=c)

    def sw(mode: str, page: str, off: int, rd: str, rs2: str, val: int) -> None:
        addr = va(ix[page], off)
        old = c[off][1]
        other = c[off ^ 4][1]
        t.load("x6", addr, "address")
        t.load(rs2, X(0, val), "rs2")
        e = ssamoswap("w", rd, "x6", rs2)
        lab = t.label(f"swapw_{mode}")
        if mode == "U":
            t.emit("RVTEST_TSBI_GOTO_UMODE", 120)
        t.emit(f"{lab}:", 0)
        t.emit(word(e, f"ssamoswap.w {rd}, {rs2}, (x6)"))
        if mode == "U":
            t.emit("RVTEST_TSBI_GOTO_SMODE", 120)
        exp = old if MUT == "ssamoswap_w_zext" else (old | (0xFFFFFFFF << 32) if old >> 31 else old)
        t.check(rd, X(0, exp), lab, f"ssamoswap.w in {mode}-mode returns the old word sign-extended")
        phys_load_w(t, f"ai_pg_{page}", off, "a0")
        t.check("a0", X(0, val & 0xFFFFFFFF), lab, f"ssamoswap.w in {mode}-mode stores rs2[31:0]")
        phys_load_w(t, f"ai_pg_{page}", off ^ 4, "a0")
        t.check("a0", X(0, other), lab, f"ssamoswap.w in {mode}-mode leaves the other half of the doubleword")
        c[off] = (4, val & 0xFFFFFFFF)

    def body6() -> None:
        sw("S", "ss", 0x800, "x7", "x8", 0xA5A5A5A5_5A5A5A5A)
        sw("S", "ss", 0x804, "x7", "x8", 0x00000001_80000001)
        sw("S", "ss", 0x808, "x8", "x8", 0xFFFFFFFF_00000002)
        sw("S", "ss", 0x80C, "x9", "x8", 0x13579BDF_2468ACE0)
        sw("U", "ssu", 0x810, "x7", "x8", 0x8000_0000_7FFF_FFFF)

    # the U page needs the same contents
    vm_either(t, body6)
    vm_off(t)
    teardown(t)
    tests.append(t)

    # ---- ssamoswap_address ----
    t = new("ssamoswap_address")
    t.describe(
        source=UCFI,
        rule_text="Just as for AMOs in the a extension, ssamoswap.w or ssamoswap.d requires that the address held in "
        "rs1 be naturally aligned to the size of the operand (i.e., 8-byte aligned for doublewords, and 4-byte "
        "aligned for words). The same exception options apply if the address is not naturally aligned.",
        context="A misaligned AMO raises a store/AMO address-misaligned (6) or store/AMO access-fault (7) exception, "
        "xtval 0 or the address. The misaligned atomicity granule does not apply to ssamoswap (#3425, PR #3426), so "
        "even an address inside a 16-byte granule must trap.",
        issues=f"{ISSUE}3425 (closed by PR 3426): the misaligned atomicity granule PMA applies only to AMOs of Zaamo, "
        "Zabha and Zacas, not to ssamoswap, which requires natural alignment.",
        plan="1. S-mode ssamoswap.w at offsets 1, 2 and 3 from a word boundary, all inside one 16-byte granule: cause "
        "6 or 7, xtval 0 or the address; rd unchanged.\n"
        "2. RV64 ssamoswap.d at offsets 1, 4 and 7 from a doubleword boundary: cause 6 or 7.\n"
        "3. The aligned swap at the same location succeeds (positive control).\n"
        "4. U-mode: ssamoswap.w at offset 2 traps the same way.",
    )
    enables(t, 1, 1)
    ix = fixture(t)

    def misal(mode: str, page: str, off: int, width: str) -> None:
        addr = va(ix[page], off)
        t.load("x6", addr, "misaligned address")
        t.li("x7", 0x77)
        t.li("x8", 0x88)
        e = ssamoswap(width, "x7", "x6", "x8")
        ex: Expect = "ok" if MUT == "ssamoswap_misaligned_ok" else [STORE_MIS, STORE_AF]
        lab = win(
            t,
            mode,
            [word(e, f"ssamoswap.{width} x7, x8, (x6)")],
            ex,
            f"ssamoswap.{width} at offset {off & 7} from alignment",
            None if ex == "ok" else [0, addr],
        )
        if ex != "ok":
            t.check("x7", 0x77, lab, f"misaligned ssamoswap.{width} in {mode}-mode leaves rd")

    def body7() -> None:
        for o in (0x901, 0x902, 0x903):
            misal("S", "ss", o, "w")
        with t.rv64_only():
            for o in (0x901, 0x904, 0x907):
                misal("S", "ss", o, "d")
        misal("U", "ssu", 0x902, "w")
        t.load("x6", va(ix["ss"], 0x900), "aligned address")
        t.li("x8", 0x88)
        lab = run(t, "S", [word(ssamoswap("w", "x7", "x6", "x8"), "ssamoswap.w x7, x8, (x6)")])
        mem_check_w(t, "ss", 0x900, 0x88, lab, "the aligned ssamoswap.w succeeds")

    vm_either(t, body7)
    vm_off(t)
    teardown(t)
    tests.append(t)


def mem_check_w(t: MemTest, page: str, off: int, expect: int, lab: str, desc: str) -> None:
    phys_load_w(t, f"ai_pg_{page}", off, "a0")
    t.check("a0", expect, lab, desc)


def swap1(
    t: MemTest, ix: dict, mode: str, page: str, off: int, rd: str, rs1: str, rs2: str, val: X, aq: int = 0, rl: int = 0
) -> None:
    """One XLEN-wide ssamoswap (ssamoswap.w on RV32, ssamoswap.d on RV64) at page+off; rd = the old word, memory
    = rs2 (when rd aliases rs1 or rs2, the original rs1/rs2 values)."""
    addr = va(ix[page], off)
    data = page_bytes(t, page)
    old = xword(data, off)
    t.load(rs1, addr, "address")
    if rs2 != rs1:
        t.load(rs2, val, "rs2")
    lab = t.label(f"swap_{mode}")
    if mode == "U":
        t.emit("RVTEST_TSBI_GOTO_UMODE", 120)
    t.emit(f"{lab}:", 0)
    for xl, w in ((32, "w"), (64, "d")):
        with t.only_if(f"__riscv_xlen == {xl}"):
            t.emit(word(ssamoswap(w, rd, rs1, rs2, aq, rl), f"ssamoswap.{w} {rd}, {rs2}, ({rs1}) aq={aq} rl={rl}"))
    if mode == "U":
        t.emit("RVTEST_TSBI_GOTO_SMODE", 120)
    if rd != "x0":
        t.check(rd, old, lab, f"ssamoswap in {mode}-mode (rd={rd}, rs1={rs1}, rs2={rs2}) returns the old word")
    stored = val if rs2 != rs1 else addr
    mem_check(t, page, off, stored, lab, f"ssamoswap in {mode}-mode (rd={rd}, rs1={rs1}, rs2={rs2}) stores rs2")


LOADS = [("lb", 1, True), ("lbu", 1, False), ("lh", 2, True), ("lhu", 2, False), ("lw", 4, True)]
LOADS64 = [("lwu", 4, False), ("ld", 8, True)]
STORES = [("sb", 1), ("sh", 2), ("sw", 4)]


def ld_val(data: bytes | bytearray, off: int, size: int, signed: bool, xlen: int) -> int:
    v = int.from_bytes(data[off : off + size], "little")
    if signed and v >> (8 * size - 1):
        v -= 1 << (8 * size)
    return v & ((1 << xlen) - 1)


def amo_w(name: str, rd: str, rs1: str, rs2: str, width: str = "w") -> tuple[int, str]:
    f5 = {"amoswap": 0b00001, "amoadd": 0b00000, "amoor": 0b01000, "lr": 0b00010, "sc": 0b00011}[name]
    e = amo(f5, width, rd, rs1, "x0" if name == "lr" else rs2)
    return e, f"{name}.{width} {rd}, {'' if name == 'lr' else rs2 + ', '}({rs1})"


def ss_mem_insns(rs1: str = "x6") -> list[tuple[str, list[str], int, X]]:
    """(name, lines, encoding, address offset from ssp/rs1) of each shadow-stack memory instruction; ssp and rs1
    point at the same address. Compressed ones are listed separately (zc_mem_insns)."""
    return [
        ("sspush x1", [word(sspush("x1"), "sspush x1")], sspush("x1"), xsub(X(0, 0), XB)),
        ("sspopchk x1", [word(sspopchk("x1"), "sspopchk x1")], sspopchk("x1"), X(0, 0)),
        ("ssamoswap", [], 0, X(0, 0)),
    ]


def swap_line(rd: str = "x7", rs1: str = "x6", rs2: str = "x8") -> list[str]:
    """XLEN-wide ssamoswap lines (ssamoswap.w on RV32, ssamoswap.d on RV64)."""
    return [
        "#if __riscv_xlen == 64",
        word(ssamoswap("d", rd, rs1, rs2), f"ssamoswap.d {rd}, {rs2}, ({rs1})"),
        "#else",
        word(ssamoswap("w", rd, rs1, rs2), f"ssamoswap.w {rd}, {rs2}, ({rs1})"),
        "#endif",
    ]


def ss_fault_all(
    t: MemTest, mode: str, ix: dict, page: str, cause: Expect, note: str, comp: bool = False, check_mem: bool = True
) -> None:
    """Every shadow-stack memory instruction (sspush x1, sspopchk x1, XLEN-wide ssamoswap; with comp, c.sspush and
    c.sspopchk) at page+TOP in mode: each raises cause (xtval 0 or the address); ssp, rd and memory unchanged."""
    top = va(ix[page], TOP)
    data = page_bytes(t, page)
    insns = [("c.sspush", "x1"), ("c.sspopchk", "x5")] if comp else [("sspush", "x1"), ("sspopchk", "x1"), ("swap", "")]
    for insn, link in insns:
        set_ssp(t, top)
        t.load("x6", top, "rs1 = the same address")
        if insn == "swap":
            t.li("x7", 0x77)
            t.load("x8", t.rand_x(), "rs2")
            lab = win(t, mode, swap_line(), cause, f"ssamoswap {note}", [0, top])
            if cause != "ok":
                t.check("x7", 0x77, lab, f"ssamoswap {note} in {mode}-mode leaves rd")
        else:
            addr = xsub(top, XB) if "push" in insn else top
            lab = ss_op(t, mode, insn, link, xword(data, TOP), cause, f"{insn} {link} {note}", [0, addr])
            if cause != "ok":
                ssp_check(t, top, lab, f"{insn} {note} in {mode}-mode leaves ssp")
        if check_mem and cause != "ok":
            off = X(TOP - 4, TOP - 8) if "push" in insn else X(TOP, TOP)
            mem_check(t, page, off, xword(data, off), lab, f"{insn} {note} in {mode}-mode leaves memory")


@section
def protection_tests(tests: list) -> None:
    # ---- ss_page_enc ----
    t = new("ss_page_enc")
    t.describe(
        source=PCFI,
        rule_text="The encoding R=0, W=1, and X=0, is defined to represent an SS page.",
        context="With menvcfg.SSE=1, a leaf PTE with xwr=010 is a shadow-stack page: shadow-stack instructions may "
        "read and write it, other instructions may only read it (ssmp_ss_load, ssmp_ss_page_access_fault, "
        "ssmp_ss_implicit_access_fault). Whether xwr=010 is an SS page or reserved depends on menvcfg.SSE (and "
        "henvcfg.SSE for VS-stage), not senvcfg.SSE (#2449).",
        issues=f'{ISSUE}2449: "the rule for whether the XWR=010 encoding is reserved in PTEs depends only on '
        'menvcfg.SSE or henvcfg.SSE depending on V. It does not depend on senvcfg.SSE"; an ld from an SS page with '
        "senvcfg.SSE=0 raises no page fault (ved-rivos).",
        plan="1. S-mode on an xwr=010 page (U=0): sspush, sspopchk and ssamoswap succeed; lw reads the pushed value; "
        "sw raises a store/AMO access fault (not a page fault); a fetch raises an instruction access fault.\n"
        "2. U-mode on an xwr=010 page with U=1: sspush, sspopchk and ssamoswap succeed and lw reads.\n"
        "3. senvcfg.SSE=0 (menvcfg.SSE=1): U-mode lw from the U=1 SS page still reads it (no page fault).",
    )
    enables(t, 1, 1)
    ix = fixture(t)

    def body8() -> None:
        for mode, page in (("S", "ss"), ("U", "ssu")):
            top = va(ix[page], TOP)
            set_ssp(t, top)
            v = t.rand_x()
            t.load("x1", v, "pushed value")
            t.load("x6", xsub(top, XB), "address of the pushed word")
            lab = run(t, mode, [word(sspush("x1"), "sspush x1"), "LREG x7, 0(x6)"])
            t.check("x7", v, lab, f"{mode}-mode: sspush to an xwr=010 page, then a load of the word, reads it")
            lab = run(t, mode, [word(sspopchk("x1"), "sspopchk x1")])
            ssp_check(t, top, lab, f"{mode}-mode: sspopchk from the xwr=010 page pops")
            t.load("x6", top, "address")
            w = t.rand_x()
            t.load("x8", w, "rs2")
            lab = run(t, mode, swap_line())
            mem_check(t, page, TOP, w, lab, f"{mode}-mode: ssamoswap writes the xwr=010 page")
        t.load("x6", va(ix["ss"], 0x900), "address")
        lab = win(
            t,
            "S",
            ["sw x8, 0(x6)"],
            mut("ss_store_pf", STORE_AF, STORE_PF),
            "sw to an xwr=010 page",
            [0, va(ix["ss"], 0x900)],
        )
        t.load("x6", va(ix["ss"], 0x900), "fetch target")
        win(
            t,
            "S",
            ["jalr x1, 0(x6)"],
            mut("ss_fetch_pf", INSN_AF, INSN_PF),
            "fetch from an xwr=010 page",
            [0, va(ix["ss"], 0x900)],
            epc=va(ix["ss"], 0x900),
        )
        senv_sse(t, False)
        t.load("x6", va(ix["ssu"], 0x700), "address")
        data = page_bytes(t, "ssu")
        ex = mut("senvcfg0_reserves_pte", "ok", LOAD_PF)
        lab = win(
            t,
            "U",
            ["LREG x7, 0(x6)"],
            ex,
            "load from a U=1 xwr=010 page with senvcfg.SSE=0",
            None if ex == "ok" else [0, va(ix["ssu"], 0x700)],
        )
        if ex == "ok":
            t.check("x7", xword(data, 0x700), lab, "U-mode load from an SS page with senvcfg.SSE=0 reads it")
        senv_sse(t, True)

    vm_either(t, body8)
    vm_off(t)
    teardown(t)
    tests.append(t)

    # ---- ssmp_menvcfg_sse ----
    t = new("ssmp_menvcfg_sse")
    t.describe(
        source=PCFI,
        rule_text="When menvcfg[sse]=0, this encoding remains reserved.",
        context="A reserved leaf encoding raises a page fault for the original access type. With menvcfg.SSE=0 the "
        "xwr=010 encoding is reserved in S-stage (and VS-stage) tables for every privilege mode below M. sfence.vma "
        "is executed after each change of menvcfg.SSE.",
        plan="1. menvcfg.SSE=0: S-mode lw from an xwr=010 page raises a load page fault (13), sw a store/AMO page fault "
        "(15), and a fetch an instruction page fault (12); xtval 0 or the address.\n"
        "2. U-mode lw from a U=1 xwr=010 page: load page fault.\n"
        "3. menvcfg.SSE=1 again: the same S-mode and U-mode loads read the page.",
    )
    enables(t, 1, 1)
    ix = fixture(t)

    def body9() -> None:
        data = {p: page_bytes(t, p) for p in ("ss", "ssu")}
        menv_sse(t, False)
        t.emit("sfence.vma")
        a = va(ix["ss"], 0x880)
        lf = mut("sse0_ss_page", LOAD_PF, "ok")
        t.load("x6", a, "address")
        win(
            t,
            "S",
            ["LREG x7, 0(x6)"],
            lf,
            "load from an xwr=010 page with menvcfg.SSE=0",
            None if lf == "ok" else [0, a],
        )
        t.load("x6", a, "address")
        win(
            t,
            "S",
            ["sw x8, 0(x6)"],
            mut("sse0_ss_page", STORE_PF, STORE_AF),
            "sw to an xwr=010 page with menvcfg.SSE=0",
            [0, a],
        )
        t.load("x6", a, "fetch target")
        win(
            t,
            "S",
            ["jalr x1, 0(x6)"],
            mut("sse0_ss_page", INSN_PF, INSN_AF),
            "fetch from an xwr=010 page with menvcfg.SSE=0",
            [0, a],
            epc=a,
        )
        au = va(ix["ssu"], 0x880)
        t.load("x6", au, "address")
        win(
            t,
            "U",
            ["LREG x7, 0(x6)"],
            lf,
            "load from a U=1 xwr=010 page with menvcfg.SSE=0",
            None if lf == "ok" else [0, au],
        )
        menv_sse(t, True)
        t.emit("sfence.vma")
        for mode, p, ad in (("S", "ss", a), ("U", "ssu", au)):
            t.load("x6", ad, "address")
            lab = run(t, mode, ["LREG x7, 0(x6)"])
            t.check("x7", xword(data[p], 0x880), lab, f"{mode}-mode load from the xwr=010 page with menvcfg.SSE=1")

    vm_either(t, body9)
    vm_off(t)
    teardown(t)
    tests.append(t)

    # ---- satp_mode_bare ----
    t = new("satp_mode_bare")
    t.describe(
        source=PCFI,
        rule_text="If satp[mode] (or vsatp[mode] when V=1) is set to Bare and the effective privilege mode is less "
        "than M, shadow stack instructions raise a store/AMO access-fault exception.",
        context="Zicfiss is active (menvcfg/senvcfg/henvcfg.SSE=1) and satp is Bare, so ssp and rs1 hold physical "
        "addresses of a data page. With H, vsatp and hgatp are Bare for VS/VU-mode.",
        issues=f"{ISSUE}2234: with satp.MODE=Bare, shadow-stack accesses raise store/AMO access faults (PR 2236 "
        'removed the "prohibited" wording).',
        plan="1. S-mode: sspush x1, sspopchk x1 and ssamoswap (XLEN-wide) raise a store/AMO access fault (7), xtval 0 "
        "or the address; ssp, rd and memory are unchanged.\n"
        "2. The same in U-mode.\n"
        "3. With Zcmop: c.sspush and c.sspopchk in S-mode.\n"
        "4. With H: the same three instructions in VS-mode and VU-mode with vsatp Bare; and in VS-mode with vsatp Bare "
        "while HS-mode's satp is Sv39/Sv32 (vsatp, not satp, decides when V=1).\n"
        "5. ssrdp (no memory access) still returns ssp.",
    )
    enables(t, 1, 1, 1)
    t.page("bare", guard_page(t))
    data = page_bytes(t, "bare")
    top = X(f"ai_pg_bare+{TOP}", f"ai_pg_bare+{TOP}")
    slot = X(f"ai_pg_bare+{TOP - 4}", f"ai_pg_bare+{TOP - 8}")

    def bare_case(mode: str, insn: str, link: str) -> None:
        t.la("x6", f"ai_pg_bare+{TOP}")
        t.emit("csrw 0x011, x6  // ssp = physical address")
        ex = mut("bare_ok", STORE_AF, "ok")
        if insn == "swap":
            t.li("x7", 0x77)
            t.load("x8", t.rand_x(), "rs2")
            lab = win(t, mode, swap_line(), ex, "ssamoswap with satp Bare", None if ex == "ok" else [0, top])
            t.check("x7", 0x77, lab, f"ssamoswap in {mode}-mode with Bare leaves rd")
        else:
            addr = slot if "push" in insn else top
            lab = ss_op(
                t,
                mode,
                insn,
                link,
                xword(data, TOP),
                ex,
                f"{insn} {link} with satp Bare",
                None if ex == "ok" else [0, addr],
            )
            ssp_check(t, top, lab, f"{insn} in {mode}-mode with Bare leaves ssp")
        off = X(TOP - 4, TOP - 8) if "push" in insn else X(TOP, TOP)
        mem_check(t, "bare", off, xword(data, off), lab, f"{insn} in {mode}-mode with Bare leaves memory")

    for mode, cond in (("S", None), ("U", None), ("VS", H), ("VU", H)):

        def all3(mode: str = mode) -> None:
            for insn, link in (("sspush", "x1"), ("sspopchk", "x5"), ("swap", "")):
                bare_case(mode, insn, link)

        if cond:
            with t.only_if(cond):
                all3()
        else:
            all3()
    with t.only_if(ZC):
        bare_case("S", "c.sspush", "x1")
        bare_case("S", "c.sspopchk", "x5")
    with t.only_if(H):
        t.comment("VS-mode: vsatp Bare decides, even with HS-mode's satp active (Sv39/Sv32)")
        fixture(t, user=False)
        vm_either(t, lambda: (bare_case("VS", "sspush", "x1"), bare_case("VS", "swap", "")))
        vm_off(t)
    t.la("x6", f"ai_pg_bare+{TOP}")
    t.emit("csrw 0x011, x6")
    lab = run(t, "S", [word(ssrdp("x7"), "ssrdp x7")])
    t.check("x7", top, lab, "ssrdp with satp Bare returns ssp")
    teardown(t)
    tests.append(t)

    # ---- ssmp_ssamoswap_Sm ----
    t = new("ssmp_ssamoswap", REQ_M, boot="M", suffix="_Sm")
    t.describe(
        source=PCFI,
        rule_text="When the effective privilege mode is M, memory access by an ssamoswap.w or ssamoswap.d instruction "
        "results in a store/AMO access-fault exception.",
        context="M-mode only. ssamoswap is not gated by menvcfg.SSE in M-mode (the checks are on the current privilege, "
        "#2420), so it reaches memory and faults whatever menvcfg.SSE is. With mstatus.MPRV=1 and MPP=S the "
        "effective privilege is S: the access is translated by satp and an SS page allows it (#2408, #2461). "
        "sspush and sspopchk are MOPs in M-mode and make no access even with MPRV=1 (#2467).",
        issues=f'{ISSUE}2408: "In machine mode samoswap can be invoked, including with mprv set to 1, and the '
        "instruction will make a memory access with effective privilege mode determined by priv, mprv, mpv, and "
        f'mpp." {ISSUE}2461: with effective privilege M, ssamoswap raises a store/AMO access fault. {ISSUE}2420: the '
        "privilege mode in the SSAMOSWAP pseudocode is the current, not the effective, one. "
        f"{ISSUE}2467: sspush/sspopchk become MOPs whenever privilege is M.",
        plan="1. M-mode, MPRV=0: ssamoswap.w (and RV64 ssamoswap.d) to a data page raise a store/AMO access fault (7), "
        "xtval 0 or the address, with menvcfg.SSE=0 and with menvcfg.SSE=1; rd and memory unchanged.\n"
        "2. MPRV=1, MPP=S, satp mapping an SS page, menvcfg.SSE=1: the XLEN-wide ssamoswap through the SS page "
        "succeeds (rd = old word, memory = rs2).\n"
        "3. MPRV=1, MPP=M: effective privilege M again: store/AMO access fault.\n"
        "4. MPRV=1, MPP=S, M-mode sspush x1 with ssp on the SS page: no access (memory unchanged).\n"
        "5. MPRV=1, MPP=S with menvcfg.SSE=0: not illegal (the enable checks use the current privilege, #2420), but "
        "the xwr=010 PTE is reserved for the S-level access: store/AMO page fault.",
    )
    t.page("mdata", guard_page(t))
    mdata = page_bytes(t, "mdata")
    MPRV, MPP = 1 << 17, 0x1800

    def m_swap(width: str, sse: int) -> None:
        t.la("x6", "ai_pg_mdata+0x800")
        t.li("x7", 0x77)
        t.load("x8", t.rand_x(), "rs2")
        e = ssamoswap(width, "x7", "x6", "x8")
        ex = mut("m_ssamoswap_ok", STORE_AF, "ok")
        lab = t.window(
            "M",
            [word(e, f"ssamoswap.{width} x7, x8, (x6)")],
            ex,
            f"ssamoswap.{width} in M-mode (menvcfg.SSE={sse})",
            None if ex == "ok" else [0, X("ai_pg_mdata+0x800", "ai_pg_mdata+0x800")],
        )
        t.check("x7", 0x77, lab, f"M-mode ssamoswap.{width} leaves rd")
        mem_check(t, "mdata", 0x800, xword(mdata, 0x800), lab, f"M-mode ssamoswap.{width} leaves memory")

    for sse in (0, 1):
        t.li("x6", SSE)
        t.emit(f"{'csrs' if sse else 'csrc'} menvcfg, x6")
        m_swap("w", sse)
        with t.rv64_only():
            m_swap("d", sse)
    ix = fixture(t, user=False)

    def mprv_body() -> None:
        sdata = page_bytes(t, "ss")
        a = va(ix["ss"], 0x880)
        w = t.rand_x()
        t.load("x6", a, "address")
        t.load("x8", w, "rs2")
        t.li("x9", MPRV)
        t.li("x5", MPP)
        t.emit("csrc mstatus, x5")
        t.li("x5", 0x800)
        t.emit("csrs mstatus, x5  // MPP = S")
        ex = mut("mprv_ssamoswap_af", "ok", STORE_AF)
        lab = t.label("mprv")
        t.allow(1)
        t.emit("csrs mstatus, x9  // MPRV=1")
        t.emit(f"{lab}:", 0)
        for ln in swap_line():
            t.emit(ln)
        t.emit("csrc mstatus, x9  // MPRV=0")
        t.outcome(ex, lab, "ssamoswap in M-mode with MPRV=1, MPP=S on an SS page", None if ex == "ok" else [0, a])
        if ex == "ok":
            t.check("x7", xword(sdata, 0x880), lab, "ssamoswap with MPRV=1, MPP=S returns the old word")
            mem_check(t, "ss", 0x880, w, lab, "ssamoswap with MPRV=1, MPP=S stores rs2 through satp")
        t.comment("MPRV=1, MPP=S, menvcfg.SSE=0: xwr=010 is reserved for the S-level access")
        t.li("x5", SSE)
        t.emit("csrc menvcfg, x5")
        t.emit("sfence.vma")
        t.load("x6", a, "address")
        lab = t.label("mprv0")
        t.allow(1)
        t.emit("csrs mstatus, x9  // MPRV=1")
        t.emit(f"{lab}:", 0)
        for ln in swap_line():
            t.emit(ln)
        t.emit("csrc mstatus, x9  // MPRV=0")
        t.outcome(
            mut("sse0_ss_page", STORE_PF, "ok"),
            lab,
            "ssamoswap in M-mode with MPRV=1, MPP=S, menvcfg.SSE=0 on an xwr=010 page (reserved)",
            [0, a] if MUT != "sse0_ss_page" else None,
        )
        t.li("x5", SSE)
        t.emit("csrs menvcfg, x5")
        t.emit("sfence.vma")
        t.comment("MPRV=1, MPP=M: effective privilege M")
        t.li("x5", MPP)
        t.emit("csrs mstatus, x5  // MPP = M")
        t.la("x6", "ai_pg_mdata+0x800")
        lab = t.label("mprvm")
        t.allow(1)
        t.emit("csrs mstatus, x9  // MPRV=1")
        t.emit(f"{lab}:", 0)
        for ln in swap_line():
            t.emit(ln)
        t.emit("csrc mstatus, x9  // MPRV=0")
        t.outcome(
            mut("m_ssamoswap_ok", STORE_AF, "ok"),
            lab,
            "ssamoswap in M-mode with MPRV=1, MPP=M",
            [0, X("ai_pg_mdata+0x800", "ai_pg_mdata+0x800")] if MUT != "m_ssamoswap_ok" else None,
        )
        t.comment("sspush in M-mode with MPRV=1, MPP=S: a MOP, no access")
        t.li("x5", MPP)
        t.emit("csrc mstatus, x5")
        t.li("x5", 0x800)
        t.emit("csrs mstatus, x5  // MPP = S")
        top = va(ix["ss"], TOP)
        t.load("x6", top, "ssp")
        t.emit("csrw 0x011, x6")
        t.load("x1", t.rand_x(), "x1")
        lab = t.label("mpush")
        t.emit("csrs mstatus, x9  // MPRV=1")
        t.emit(f"{lab}:", 0)
        t.emit(word(sspush("x1"), "sspush x1"))
        t.emit("csrc mstatus, x9  // MPRV=0")
        mem_check(
            t,
            "ss",
            X(TOP - 4, TOP - 8),
            xword(sdata, X(TOP - 4, TOP - 8)),
            lab,
            "M-mode sspush with MPRV=1 makes no access",
        )
        t.emit("csrr x7, 0x011")
        t.check("x7", top, lab, "M-mode sspush with MPRV=1 leaves ssp")

    vm_either(t, mprv_body)
    t.li("x5", MPP)
    t.emit("csrs mstatus, x5  // MPP = M")
    vm_off(t)
    t.li("x6", SSE)
    t.emit("csrc menvcfg, x6")
    tests.append(t)

    # ---- ssmp_ss_page_access_fault ----
    t = new("ssmp_ss_page_access_fault")
    t.describe(
        source=PCFI,
        rule_text="Memory mapped as an SS page cannot be written to by instructions other than ssamoswap.w, "
        "ssamoswap.d, sspush, and c.sspush. Attempts will raise a store/AMO access-fault exception.",
        context="The access fault is decided before the A/D-bit evaluation (#2380), so even an SS page with D=0 gives "
        "the access fault. Stores to the page are checked to leave memory unchanged (read untranslated).",
        issues=f"{ISSUE}2380: the shadow-stack access-fault check (translation step 7) comes before the A/D-bit "
        'evaluation (step 9), so "a store to a shadow-stack page will raise a store/AMO access fault before any A/D-bit '
        'evaluation" (ved-rivos).',
        plan="1. S-mode sb, sh, sw (and RV64 sd) to an SS page raise a store/AMO access fault (7), not a page fault; "
        "xtval 0 or the address; memory unchanged.\n"
        "2. With Zaamo: amoswap.w and amoor (XLEN) raise the access fault; rd unchanged.\n"
        "3. With Zalrsc: lr then sc to the SS page: sc raises the access fault, or fails (rd != 0) without writing.\n"
        "4. U-mode sw and sb to a U=1 SS page: access fault.\n"
        "5. An SS page with D=0 (A=1): sw raises the access fault (not a store page fault).\n"
        "6. sspush and ssamoswap to the same page succeed (positive control).",
    )
    enables(t, 1, 1)
    ix = fixture(t, [Map("ssnod", V | W | A)])
    ex = mut("ss_store_ok", mut("ss_store_pf", STORE_AF, STORE_PF), "ok")

    def st(mode: str, page: str, off: int, insn: str, size: int) -> None:
        a = va(ix[page], off)
        data = page_bytes(t, page)
        t.load("x6", a, "address")
        t.load("x8", t.rand_x(), "store data")
        lab = win(t, mode, [f"{insn} x8, 0(x6)"], ex, f"{insn} to an SS page", None if ex == "ok" else [0, a])
        mem_check(t, page, off, xword(data, off), lab, f"{insn} to an SS page in {mode}-mode leaves memory")

    def body10() -> None:
        for i, (insn, size) in enumerate(STORES):
            st("S", "ss", 0x900 + 0x10 * i, insn, size)
        with t.rv64_only():
            st("S", "ss", 0x940, "sd", 8)
        st("U", "ssu", 0x900, "sw", 4)
        st("U", "ssu", 0x910, "sb", 1)
        st("S", "ssnod", 0x900, "sw", 4)
        top = va(ix["ss"], TOP)
        set_ssp(t, top)
        lab = ss_op(t, "S", "sspush", "x1", t.rand_x(), "ok", "")
        ssp_check(t, xsub(top, XB), lab, "sspush to the same SS page succeeds")
        t.load("x6", va(ix["ss"], 0x980), "address")
        w = t.rand_x()
        t.load("x8", w, "rs2")
        lab = run(t, "S", swap_line())
        mem_check(t, "ss", 0x980, w, lab, "ssamoswap to the same SS page writes it")

    vm_either(t, body10)

    def amo_body() -> None:
        for name, width, off in (("amoswap", "w", 0xA00), ("amoor", None, 0xA10)):
            a = va(ix["ss"], off)
            data = page_bytes(t, "ss")
            t.load("x6", a, "address")
            t.li("x7", 0x77)
            t.li("x8", 0x5A)
            lines = []
            if width:
                e, note = amo_w(name, "x7", "x6", "x8", width)
                lines = [word(e, note)]
            else:
                lines = swap_line()  # placeholder replaced below
                e64, n64 = amo_w(name, "x7", "x6", "x8", "d")
                e32, n32 = amo_w(name, "x7", "x6", "x8", "w")
                lines = ["#if __riscv_xlen == 64", word(e64, n64), "#else", word(e32, n32), "#endif"]
            lab = win(t, "S", lines, ex, f"{name} to an SS page", None if ex == "ok" else [0, a])
            if ex != "ok":
                t.check("x7", 0x77, lab, f"{name} to an SS page leaves rd")
            mem_check(t, "ss", off, xword(data, off), lab, f"{name} to an SS page leaves memory")

    with t.only_if("defined(ZAAMO_SUPPORTED)"):
        vm_either(t, amo_body)

    def sc_body() -> None:
        a = va(ix["ss"], 0xA40)
        data = page_bytes(t, "ss")
        t.load("x6", a, "address")
        e_lr, n_lr = amo_w("lr", "x7", "x6", "x0", "w")
        e_sc, n_sc = amo_w("sc", "x9", "x6", "x8", "w")
        t.li("x8", 0x5A)
        t.li("x9", 0x99)
        lab = win(
            t,
            "S",
            [word(e_sc, n_sc)],
            ["ok", STORE_AF],
            "sc.w (after lr.w) to an SS page",
            [0, a],
            pre=lambda: t.emit(word(e_lr, n_lr)),
        )
        t.emit("snez x9, x9  // sc.w trapped (x9 kept) or failed (x9 != 0); 0 = it succeeded")
        t.check_bool("x9", lab, "sc.w to an SS page faults or fails")
        mem_check_w(
            t, "ss", 0xA40, int.from_bytes(data[0xA40:0xA44], "little"), lab, "sc.w to an SS page leaves memory"
        )

    with t.only_if("defined(ZALRSC_SUPPORTED)"):
        vm_either(t, sc_body)
    vm_off(t)
    teardown(t)
    tests.append(t)

    # ---- ssmp_ss_cache_block_access_fault ----
    t = new("ssmp_ss_cache_block_access_fault")
    t.describe(
        source=PCFI,
        rule_text="Access to a SS page using cache-block operation (cbo.*) instructions is not permitted. Such accesses "
        "will raise a store/AMO access-fault exception.",
        context="The framework enables the CBO instructions below M (menvcfg/senvcfg CBIE=11, CBCFE=1, CBZE=1). The "
        "address is 2 KiB aligned, so it is also the cache-block address.",
        plan="1. With Zicbom: cbo.clean, cbo.flush and cbo.inval to an SS page raise a store/AMO access fault (7), xtval "
        "0 or the address, in S-mode and U-mode.\n"
        "2. With Zicboz: cbo.zero raises the access fault and memory is unchanged.\n"
        "3. The same instructions to an RW page succeed (positive control; cbo.zero then reads 0).",
    )
    enables(t, 1, 1)
    ix = fixture(t, [Map("rw", RW | U)])
    exc = mut("ss_cbo_ok", STORE_AF, "ok")

    def cbo_case(names: list[str]) -> Callable[[], None]:
        def body11() -> None:
            for mode, page in (("S", "ss"), ("U", "ssu")):
                a = va(ix[page], 0x800)
                data = page_bytes(t, page)
                for n in names:
                    t.load("x6", a, "address")
                    lab = win(
                        t,
                        mode,
                        [word(cbo(n, "x6"), f"{n} (x6)")],
                        exc,
                        f"{n} on an SS page",
                        None if exc == "ok" else [0, a],
                    )
                    if n == "cbo.zero":
                        mem_check(
                            t,
                            page,
                            0x800,
                            xword(data, 0x800),
                            lab,
                            f"cbo.zero on an SS page in {mode}-mode leaves memory",
                        )
            for n in names:
                t.load("x6", va(ix["rw"], 0x800), "address")
                lab = run(t, "U", [word(cbo(n, "x6"), f"{n} (x6)")])
                if n == "cbo.zero":
                    mem_check(t, "rw", 0x800, 0, lab, "cbo.zero on an RW page zeroes it")

        return body11

    with t.only_if("defined(ZICBOM_SUPPORTED)"):
        vm_either(t, cbo_case(["cbo.clean", "cbo.flush", "cbo.inval"]))
    with t.only_if("defined(ZICBOZ_SUPPORTED)"):
        vm_either(t, cbo_case(["cbo.zero"]))
    vm_off(t)
    teardown(t)
    tests.append(t)

    # ---- ssmp_ss_implicit_access_fault ----
    t = new("ssmp_ss_implicit_access_fault")
    t.describe(
        source=PCFI,
        rule_text="Implicit accesses, including instruction fetches to an SS page, are not permitted. Such accesses "
        "will raise an access-fault exception appropriate to the access type.",
        context="Instruction fetch is the only implicit access subject to S-stage translation (note in the same "
        "section), so the appropriate exception is an instruction access fault (1). The fetch is made by jalr to the "
        "page; xepc is the target, and the handler returns through x1.",
        plan="1. S-mode jalr to an SS page (U=0): instruction access fault, xepc and xtval (0 or) the target.\n"
        "2. U-mode jalr to a U=1 SS page: instruction access fault.\n"
        "3. A target at another offset in the page, and with sstatus.MXR=1: still an access fault.",
    )
    enables(t, 1, 1)
    ix = fixture(t)

    def fetch(mode: str, page: str, off: int, note: str = "") -> None:
        a = va(ix[page], off)
        t.load("x6", a, "fetch target")
        win(
            t,
            mode,
            ["jalr x1, 0(x6)"],
            mut("ss_fetch_pf", INSN_AF, INSN_PF),
            f"fetch from an SS page{note}",
            [0, a],
            epc=a,
        )

    def body12() -> None:
        fetch("S", "ss", 0x800)
        fetch("U", "ssu", 0x800)
        fetch("S", "ss", 0x404)
        t.li("x6", MXR)
        t.emit("csrs sstatus, x6  // MXR=1")
        fetch("S", "ss", 0x900, " with MXR=1")
        t.li("x6", MXR)
        t.emit("csrc sstatus, x6  // MXR=0")

    vm_either(t, body12)
    vm_off(t)
    teardown(t)
    tests.append(t)

    # ---- ssmp_ss_load ----
    t = new("ssmp_ss_load")
    t.describe(
        source=PCFI,
        rule_text="However, the shadow stack is readable by all instructions that only load from memory.",
        context="MXR does not affect read access to an SS page (same section). The SS pages hold distinct bytes; "
        "expected values are the bytes, sign- or zero-extended per instruction.",
        plan="1. S-mode lb, lbu, lh, lhu, lw (RV64: lwu, ld) from an SS page with MXR=0 and MXR=1 return the "
        "page's bytes, sign- or zero-extended (the lwu word has bit 31 set).\n"
        "2. U-mode: the same loads from a U=1 SS page.\n"
        "3. S-mode lw from the U=1 SS page with SUM=1.\n"
        "4. With Zalrsc: lr.w (load-only) reads the SS page.",
    )
    enables(t, 1, 1)
    cont = {
        0x900 + 8 * i: (
            8,
            ((0x8091A2B3C4D5E6F7 * (i + 1) + 0x7F00FF00) ^ (0x80807F7F80807F7F if i & 1 else 0x7F7F80807F7F8080))
            & ((1 << 64) - 1),
        )
        for i in range(8)
    }
    cont[0x928] = (8, 0x7A5A3C1E_9B8D6F42)  # lwu/lw/ld at 0x928: bit 31 set, upper word positive
    ix = fixture(t, ss_contents=cont)

    def loads(mode: str, page: str, base: int, mxr: int) -> None:
        data = page_bytes(t, page)
        ex: Expect = "ok"
        if MUT == "ss_load_faults":
            ex = 5
        if MUT == "mxr_needed" and not mxr:
            ex = LOAD_PF
        for i, (insn, size, signed) in enumerate(LOADS):
            off = base + 3 * i if size == 1 else base + 2 * size * (i % 3)
            off -= off % size
            t.load("x6", va(ix[page], off), "address")
            t.li("x7", 0x7E)
            if ex == "ok":
                lab = run(t, mode, [f"{insn} x7, 0(x6)"])
            else:
                lab = win(t, mode, [f"{insn} x7, 0(x6)"], ex, insn)
                continue
            exp = X(ld_val(data, off, size, signed, 32), ld_val(data, off, size, signed, 64))
            t.check("x7", exp, lab, f"{insn} from an SS page in {mode}-mode (MXR={mxr})")

    def body13() -> None:
        for mxr in (0, 1):
            t.li("x6", MXR)
            t.emit(f"{'csrs' if mxr else 'csrc'} sstatus, x6  // MXR={mxr}")
            loads("S", "ss", 0x900 + 0x10 * mxr, mxr)
            loads("U", "ssu", 0x901 + 0x10 * mxr, mxr)
        with t.rv64_only():
            for mode, page in (("S", "ss"), ("U", "ssu")):
                data = page_bytes(t, page)
                for insn, size, signed in LOADS64:
                    t.load("x6", va(ix[page], 0x928), "address")
                    lab = run(t, mode, [f"{insn} x7, 0(x6)"])
                    t.check(
                        "x7", X(0, ld_val(data, 0x928, size, signed, 64)), lab, f"{insn} from an SS page in {mode}-mode"
                    )
        t.li("x6", MXR)
        t.emit("csrc sstatus, x6")
        t.li("x6", SUM)
        t.emit("csrs sstatus, x6  // SUM=1")
        data = page_bytes(t, "ssu")
        t.load("x6", va(ix["ssu"], 0x930), "address")
        lab = run(t, "S", ["lw x7, 0(x6)"])
        t.check(
            "x7",
            X(ld_val(data, 0x930, 4, True, 32), ld_val(data, 0x930, 4, True, 64)),
            lab,
            "S-mode lw from a U=1 SS page with SUM=1",
        )
        t.li("x6", SUM)
        t.emit("csrc sstatus, x6")

    vm_either(t, body13)

    def lr_body() -> None:
        data = page_bytes(t, "ss")
        t.load("x6", va(ix["ss"], 0x938), "address")
        e, n = amo_w("lr", "x7", "x6", "x0", "w")
        lab = run(t, "S", [word(e, n)])
        t.check(
            "x7", X(ld_val(data, 0x938, 4, True, 32), ld_val(data, 0x938, 4, True, 64)), lab, "lr.w from an SS page"
        )

    with t.only_if("defined(ZALRSC_SUPPORTED)"):
        vm_either(t, lr_body)
    vm_off(t)
    teardown(t)
    tests.append(t)

    # ---- ss_fault_exception_code ----
    t = new("ss_fault_exception_code")
    t.describe(
        source=PCFI,
        rule_text="If a shadow stack (SS) instruction raises an access-fault, page-fault, or guest-page-fault exception "
        "that is supposed to indicate the original instruction type (load or store/AMO), then the reported exception "
        "cause is respectively a store/AMO access fault (code 7), a store/AMO page fault (code 15), or a store/AMO "
        "guest-page fault (code 23).",
        context="This matters for sspopchk and c.sspopchk, which only read: their faults are store/AMO faults. "
        "Guest-page faults (23) are checked in active_g_stage_pte.",
        issues=f'{ISSUE}2477: "For shadow-stack instructions, the reported instruction type is always treated as a '
        'store/AMO, even for sspopchk, which only reads from memory."',
        plan="1. S-mode sspopchk x1 through an invalid PTE: store/AMO page fault (15), not a load page fault (13).\n"
        "2. sspopchk on a read-only page: 15. On an RW page: store/AMO access fault (7), not 5.\n"
        "3. S-mode sspopchk on a U=1 SS page with SUM=0: 15. U-mode sspopchk on a U=0 SS page: 15.\n"
        "4. sspush and ssamoswap through an invalid PTE: 15.\n"
        "5. With Zcmop: c.sspopchk through an invalid PTE: 15; on the RW page: 7.",
    )
    enables(t, 1, 1)
    c8 = pop_contents(8)
    ix = fixture(t, [Map("inv", None), Map("ro", RO, c8), Map("rw", RW, c8)], ss_contents=c8)

    def pf(mode: str, page: str, insn: str, link: str, cause: Expect, note: str) -> None:
        top = va(ix[page], TOP)
        set_ssp(t, top)
        v = pop_values(t, page, 1)[0] if page != "inv" else X(0, 0)
        if insn == "swap":
            t.load("x6", top, "address")
            win(t, mode, swap_line(), store_cause(cause), f"ssamoswap {note}", [0, top])
            return
        addr = xsub(top, XB) if "push" in insn else top
        ss_op(t, mode, insn, link, v, store_cause(cause) if "pop" in insn else cause, f"{insn} {note}", [0, addr])

    def body14() -> None:
        pf("S", "inv", "sspopchk", "x1", STORE_PF, "through an invalid PTE")
        pf("S", "ro", "sspopchk", "x5", STORE_PF, "on a read-only page")
        pf("S", "rw", "sspopchk", "x1", STORE_AF, "on an RW page")
        pf("S", "ssu", "sspopchk", "x1", mut("sum_ignored", STORE_PF, "ok"), "on a U=1 SS page with SUM=0")
        pf("U", "ss", "sspopchk", "x5", STORE_PF, "on a U=0 SS page")
        pf("S", "inv", "sspush", "x1", STORE_PF, "through an invalid PTE")
        pf("S", "inv", "swap", "", STORE_PF, "through an invalid PTE")

    vm_either(t, body14)
    with t.only_if(ZC):
        vm_either(
            t,
            lambda: (
                pf("S", "inv", "c.sspopchk", "x5", STORE_PF, "through an invalid PTE"),
                pf("S", "rw", "c.sspopchk", "x5", STORE_AF, "on an RW page"),
            ),
        )
    vm_off(t)
    teardown(t)
    tests.append(t)

    # ---- ssmp_ss_page_illegal_access ----
    t = new("ssmp_ss_page_illegal_access")
    t.describe(
        source=PCFI,
        rule_text="Should a shadow stack instruction access a page that is not designated as a shadow stack page and "
        "is not marked as read-only (pte.xwr=0b001), a store/AMO access-fault exception will be invoked.",
        context="Pages that are neither SS (010) nor read-only (001): RW (011), RWX (111), RX (101) and execute-only "
        "(100), all with A=D=1.",
        plan="1. S-mode sspush x1, sspopchk x1 and ssamoswap on RW, RWX, RX and X pages: store/AMO access fault (7), "
        "xtval 0 or the address; ssp, rd and memory unchanged.\n"
        "2. U-mode on a U=1 RW page: the same.\n"
        "3. With Zcmop: c.sspush and c.sspopchk on the RW page.",
    )
    enables(t, 1, 1)
    perms = [("rw", RW), ("rwx", RWX), ("rx", RX), ("xo", XO)]
    ix = fixture(
        t,
        [Map(n, p, guard_page(t, seed=k + 2)) for k, (n, p) in enumerate(perms)]
        + [Map("rwu", RW | U, guard_page(t, seed=9))],
    )
    exi = mut("rw_page_ok", STORE_AF, "ok")

    def body15() -> None:
        for n, _ in perms:
            ss_fault_all(
                t,
                "S",
                ix,
                n,
                exi if n in ("rw", "rwx") else STORE_AF,
                f"on an {n.upper()} page",
                check_mem=n in ("rw", "rwx"),
            )
        ss_fault_all(t, "U", ix, "rwu", exi, "on a U=1 RW page")

    vm_either(t, body15)
    with t.only_if(ZC):
        vm_either(t, lambda: ss_fault_all(t, "S", ix, "rw", exi, "on an RW page", comp=True))
    vm_off(t)
    teardown(t)
    tests.append(t)

    # ---- ssmp_ss_read_only_page ----
    t = new("ssmp_ss_read_only_page")
    t.describe(
        source=PCFI,
        rule_text="Conversely, if the page being accessed by a shadow stack instruction is a read-only page, a "
        "store/AMO page-fault exception will be triggered.",
        context="Read-only is xwr=001 (A=D=1). The page fault lets an OS implement copy-on-write of shadow stacks.",
        plan="1. S-mode sspush x1, sspopchk x1 and ssamoswap on a read-only page: store/AMO page fault (15), xtval 0 or "
        "the address; ssp, rd and memory unchanged.\n"
        "2. U-mode on a U=1 read-only page: the same.\n"
        "3. With sstatus.MXR=1: still 15.\n"
        "4. With Zcmop: c.sspush and c.sspopchk.",
    )
    enables(t, 1, 1)
    ix = fixture(t, [Map("ro", RO, guard_page(t, seed=3)), Map("rou", RO | U, guard_page(t, seed=4))])
    exr = mut("ro_page_af", STORE_PF, STORE_AF)

    def body16() -> None:
        ss_fault_all(t, "S", ix, "ro", exr, "on a read-only page")
        ss_fault_all(t, "U", ix, "rou", exr, "on a U=1 read-only page")
        t.li("x6", MXR)
        t.emit("csrs sstatus, x6  // MXR=1")
        ss_fault_all(t, "S", ix, "ro", exr, "on a read-only page with MXR=1", check_mem=False)
        t.li("x6", MXR)
        t.emit("csrc sstatus, x6")

    vm_either(t, body16)
    with t.only_if(ZC):
        vm_either(t, lambda: ss_fault_all(t, "S", ix, "ro", exr, "on a read-only page", comp=True))
    vm_off(t)
    teardown(t)
    tests.append(t)

    # ---- ssp_xlen_aligned ----
    t = new("ssp_xlen_aligned", rv64=True)
    t.describe(
        source=PCFI,
        rule_text="If the virtual address in ssp is not XLEN aligned, then the sspush, c.sspush, sspopchk and "
        "c.sspopchk instructions cause a store/AMO access-fault exception.",
        context="ssp bits 1:0 are read-only zero, so only RV64 with a writable ssp bit 2 can hold an ssp that is not "
        "XLEN aligned (ssp_field_1_0). The test probes bit 2; if it is read-only zero, nothing is left to test. RV32 "
        "passes trivially.",
        plan="1. Probe: write ssp = SS page + 0x804 and read it back.\n"
        "2. If bit 2 held: sspush x1 and sspopchk x1 (with a matching or mismatching link value) raise a store/AMO "
        "access fault (7), xtval 0 or the address (ssp - 8 for a push, ssp for a pop); ssp and memory unchanged. The "
        "access fault outranks the software check.\n"
        "3. With Zcmop: c.sspush and c.sspopchk the same way.",
    )
    enables(t, 1, 1)
    ix = fixture(t)

    def misal(comp: bool) -> Callable[[], None]:
        def run_cases() -> None:
            mis_top = va(ix["ss"], 0x804)
            data = page_bytes(t, "ss")
            exm = mut("misaligned_ssp_ok", STORE_AF, "ok")
            cases = (
                [("c.sspush", "x1"), ("c.sspopchk", "x5")]
                if comp
                else [("sspush", "x1"), ("sspopchk", "x1"), ("sspopchk", "x5")]
            )
            for k, (insn, link) in enumerate(cases):
                set_ssp(t, mis_top)
                addr = xsub(mis_top, XB) if "push" in insn else mis_top
                lv = X(0, int.from_bytes(data[0x804:0x80C], "little")) if k == 1 else X(0, 0x1234)
                lab = ss_op(
                    t, "S", insn, link, lv, exm, f"{insn} {link} with ssp = 8n+4", None if exm == "ok" else [0, addr]
                )
                if exm != "ok":
                    ssp_check(t, mis_top, lab, f"{insn} with a misaligned ssp leaves ssp")
                    off = 0x7FC if "push" in insn else 0x804
                    mem_check(
                        t,
                        "ss",
                        off,
                        X(0, int.from_bytes(data[off : off + 8], "little")),
                        lab,
                        f"{insn} with a misaligned ssp leaves memory",
                    )

        def probe() -> None:
            set_ssp(t, va(ix["ss"], 0x804))
            read_ssp(t, "x9")
            t.emit("andi x9, x9, 4  // bit 2 held?")
            t.either("x9", run_cases, lambda: t.comment("ssp bit 2 is read-only zero: ssp is always 8-byte aligned"))

        return probe

    vm_either(t, misal(False))
    with t.only_if(ZC):
        vm_either(t, misal(True))
    vm_off(t)
    teardown(t)
    tests.append(t)

    # ---- ssmp_ss_idempotent_memory ----
    t = new("ssmp_ss_idempotent_memory", ["I", "S", "Zicfiss", "Svpbmt"], rv64=True)
    t.describe(
        source=PCFI,
        rule_text="If the memory referenced by sspush, c.sspush, sspopchk, c.sspopchk, ssamoswap.w and ssamoswap.d "
        "instructions is not idempotent, then the instructions cause a store/AMO access-fault exception.",
        context="Non-idempotent memory is reached portably through Svpbmt: PBMT=IO makes a page non-idempotent I/O "
        "memory, PBMT=NC is idempotent. menvcfg.PBMTE is set. Svpbmt is RV64-only, so RV32 passes trivially.",
        plan="1. An SS page with PBMT=IO: S-mode sspush x1, sspopchk x1 and ssamoswap.d raise a store/AMO access fault "
        "(7), xtval 0 or the address; ssp and memory unchanged.\n"
        "2. U-mode on a U=1 SS page with PBMT=IO: the same.\n"
        "3. An SS page with PBMT=NC: sspush and sspopchk succeed (positive control).\n"
        "4. With Zcmop: c.sspush and c.sspopchk on the IO page.",
    )
    enables(t, 1, 1)
    t.comment("menvcfg.PBMTE = 1")
    t.li("a1", 1)
    t.emit("slli a1, a1, 62")
    t.tsbi_csr("SET", "MENVCFG", "a1")
    IO, NC = X(0, 2 << 61), X(0, 1 << 61)
    ix = fixture(
        t,
        [
            Map("io", SS, guard_page(t, seed=5), IO),
            Map("iou", SS | U, guard_page(t, seed=6), IO),
            Map("nc", SS, guard_page(t, seed=7), NC),
        ],
    )
    exn = mut("pbmt_io_ok", STORE_AF, "ok")

    def body17() -> None:
        ss_fault_all(t, "S", ix, "io", exn, "on a PBMT=IO SS page")
        ss_fault_all(t, "U", ix, "iou", exn, "on a U=1 PBMT=IO SS page")
        top = va(ix["nc"], TOP)
        set_ssp(t, top)
        v = t.rand_x()
        ss_op(t, "S", "sspush", "x1", v, "ok", "")
        lab = ss_op(t, "S", "sspopchk", "x5", v, "ok", "")
        ssp_check(t, top, lab, "sspush/sspopchk on a PBMT=NC SS page succeed")

    vm_either(t, body17)
    with t.only_if(ZC):
        vm_either(t, lambda: ss_fault_all(t, "S", ix, "io", exn, "on a PBMT=IO SS page", comp=True))
    vm_off(t)
    t.li("a1", 1)
    t.emit("slli a1, a1, 62")
    t.tsbi_csr("CLEAR", "MENVCFG", "a1")
    teardown(t)
    tests.append(t)


def hgatp_bare(t: MemTest) -> None:
    t.emit("csrw 0x680, x0  // hgatp = Bare")
    t.emit(".word 0x62000073  // hfence.gvma")


def vs_fixture(t: MemTest, extra: list[Map] | None = None) -> dict:
    """VS-stage map (vsatp, hgatp Bare) with an SS page "ss" (tag v: page ai_pg_ssv) and extra pages."""
    hgatp_bare(t)
    maps = [Map("ss", SS, pop_contents(10))] + (extra or [])
    vm_setup(t, maps, root="vsatp", tag="v")
    return {m.name: i for i, m in enumerate(maps)}


def ssamoswap_insn(rd: str = "x7", rs1: str = "x6", rs2: str = "x8") -> X:
    return X(ssamoswap("w", rd, rs1, rs2), ssamoswap("d", rd, rs1, rs2))


def swap_ill(t: MemTest, mode: str, cause: Expect, desc: str) -> None:
    """XLEN-wide ssamoswap in mode expecting cause (illegal, virtual, access fault or ok); rd unchanged on a trap."""
    e = ssamoswap_insn()
    t.li("x7", 0x77)
    t.la("x6", "ai_pg_ill+0x100")
    alts = cause if isinstance(cause, list) else [cause]
    tval: list[Value] | None = None
    if ILLEGAL in alts or VIRTUAL in alts:
        tval = [0, e]
    elif STORE_AF in alts:
        tval = [0, X("ai_pg_ill+0x100", "ai_pg_ill+0x100")]
    lab = win(t, mode, swap_line(), cause, desc, tval)
    if "ok" not in alts:
        t.check("x7", 0x77, lab, f"ssamoswap in {mode}-mode ({desc}) leaves rd")


def mop_checks(t: MemTest, mode: str, desc: str, comp: bool = False) -> None:
    """With Zicfiss inactive in mode (satp/vsatp Bare): ssrdp writes 0; sspush and sspopchk (with a mismatching link
    value) do nothing, so no trap (an executed one would raise a store/AMO access fault)."""
    if not comp:
        t.li("x7", 0x77)
        lab = run(t, mode, [word(ssrdp("x7"), "ssrdp x7")])
        t.check("x7", mut("ssrdp_inactive_ssp", 0, X(0x5550, 0x5550)), lab, f"ssrdp in {mode}-mode ({desc}) writes 0")
        t.li("x1", 0x1111)
        run(
            t,
            mode,
            [
                word(sspush("x1"), "sspush x1"),
                word(sspopchk("x1"), "sspopchk x1 (mismatch)"),
                word(sspush("x5"), "sspush x5"),
                word(sspopchk("x5"), "sspopchk x5"),
            ],
            pre=lambda: t.li("x5", 0x5555),
        )
    else:
        t.li("x1", 0x1111)
        run(
            t,
            mode,
            [*hword(C_SSPUSH, "c.sspush x1"), *hword(C_SSPOPCHK, "c.sspopchk x5 (mismatch)")],
            pre=lambda: t.li("x5", 0x5555),
        )


@section
def env_tests(tests: list) -> None:
    # ---- menvcfg_sse_rdonly0 ----
    t = new("menvcfg_sse_rdonly0")
    t.describe(
        source=MAC,
        rule_text="When menvcfg.SSE is 0, the henvcfg.SSE and senvcfg.SSE fields are read-only zero.",
        context="SSE is bit 3 of menvcfg, senvcfg and henvcfg. When menvcfg.SSE is set again, the fields' values are "
        "UNSPECIFIED until written (field modulation), so they are written before being read.",
        issues=f"{ISSUE}1509: xenvcfg masking (read-only zero) follows the CSR field-modulation rule.",
        plan="1. menvcfg.SSE=1: senvcfg.SSE (and henvcfg.SSE with H) can be set and cleared.\n"
        "2. Set both, then clear menvcfg.SSE: both read 0.\n"
        "3. While menvcfg.SSE=0, csrs and csrw of SSE=1 leave them reading 0, and the writes do not change the "
        "other bits of senvcfg/henvcfg.\n"
        "4. menvcfg.SSE=1 again: after a write of 1, they read 1.",
    )

    def rd(csr: int, reg: str) -> None:
        t.emit(f"csrr {reg}, {hex(csr)}")
        t.emit(f"andi {reg}, {reg}, {SSE}")

    def both_fields(fn: Callable[[int, str], None]) -> None:
        fn(SENVCFG, "senvcfg")
        with t.only_if(H):
            fn(HENVCFG, "henvcfg")

    menv_sse(t, True)
    for on in (1, 0, 1):

        def setclr(csr: int, name: str, on: int = on) -> None:
            t.li("x6", SSE)
            t.emit(f"{'csrs' if on else 'csrc'} {hex(csr)}, x6  // {name}")
            lab = t.label("rw")
            t.emit(f"{lab}:", 0)
            rd(csr, "x7")
            t.check("x7", SSE if on else 0, lab, f"{name}.SSE reads {on} after a write with menvcfg.SSE=1")

        both_fields(setclr)
    menv_sse(t, False)

    def zero(csr: int, name: str) -> None:
        lab = t.label("ro0")
        t.emit(f"{lab}:", 0)
        rd(csr, "x7")
        t.check("x7", 0, lab, f"{name}.SSE reads 0 after menvcfg.SSE is cleared")
        t.emit(f"csrr x9, {hex(csr)}")
        t.li("x6", SSE)
        t.emit(f"csrs {hex(csr)}, x6  // {name}.SSE = 1 (read-only zero)")
        rd(csr, "x7")
        t.check("x7", mut("rdonly0_writable", 0, SSE), lab, f"csrs {name}.SSE with menvcfg.SSE=0: still 0")
        t.emit(f"csrr x7, {hex(csr)}")
        t.emit("or x6, x9, x6")
        t.emit(f"csrw {hex(csr)}, x6  // csrw with SSE=1 and the other bits as read")
        t.emit(f"csrr x8, {hex(csr)}")
        t.emit("xor x8, x8, x9")
        t.check(
            "x8",
            mut("rdonly0_writable", 0, SSE),
            lab,
            f"csrw {name} with SSE=1 and menvcfg.SSE=0: the CSR reads as before (SSE 0, other bits unchanged)",
        )
        t.emit("xor x7, x7, x9")
        t.check("x7", mut("rdonly0_writable", 0, SSE), lab, f"csrs {name}.SSE left the other bits unchanged")

    both_fields(zero)
    menv_sse(t, True)

    def again(csr: int, name: str) -> None:
        t.li("x6", SSE)
        t.emit(f"csrs {hex(csr)}, x6")
        lab = t.label("again")
        t.emit(f"{lab}:", 0)
        rd(csr, "x7")
        t.check("x7", SSE, lab, f"{name}.SSE is writable again with menvcfg.SSE=1")

    both_fields(again)
    teardown(t)
    tests.append(t)

    # ---- menvcfg_sse_op_lead_in ----
    t = new("menvcfg_sse_op_lead_in")
    t.describe(
        source=MAC,
        rule_text="The Zicfiss extension adds the SSE field to menvcfg. When the SSE field is set to 1 the Zicfiss "
        "extension is activated in S-mode. When SSE field is 0, the following rules apply to privilege modes that are "
        "less than M:",
        context="Activated in S-mode: ssrdp returns ssp and sspush/sspopchk access the shadow stack. menvcfg.SSE alone "
        "does not activate U-mode (senvcfg.SSE does). The rules for SSE=0 are menvcfg_sse_op_list.",
        plan="1. menvcfg.SSE reads back 1 and 0 after M-mode writes (T-SBI).\n"
        "2. menvcfg.SSE=1, senvcfg.SSE=0: S-mode ssrdp returns ssp; S-mode sspush on an SS page pushes and sspopchk "
        "pops. U-mode ssrdp writes 0 (U not activated).\n"
        "3. menvcfg.SSE=0: S-mode ssrdp writes 0, and sspush/sspopchk make no access (no trap; the SS page is then "
        "reserved, so an access would fault). Re-enabled, ssp still holds its value.",
    )
    for on in (1, 0):
        menv_sse(t, bool(on))
        lab = t.label("menvcfg")
        t.emit(f"{lab}:", 0)
        t.tsbi_csr("READ", "MENVCFG")
        t.emit(f"andi a0, a0, {SSE}")
        t.check("a0", SSE if on else 0, lab, f"menvcfg.SSE reads {on}")
    enables(t, 1, 0)
    ix = fixture(t)

    def body18() -> None:
        top = va(ix["ss"], TOP)
        set_ssp(t, top)
        lab = run(t, "S", [word(ssrdp("x7"), "ssrdp x7")])
        t.check("x7", top, lab, "menvcfg.SSE=1: S-mode ssrdp returns ssp")
        v = t.rand_x()
        lab = ss_op(t, "S", "sspush", "x1", v, "ok", "")
        ssp_check(t, xsub(top, XB), lab, "menvcfg.SSE=1: S-mode sspush pushes")
        mem_check(t, "ss", X(TOP - 4, TOP - 8), v, lab, "menvcfg.SSE=1: S-mode sspush stores")
        lab = ss_op(t, "S", "sspopchk", "x5", v, "ok", "")
        ssp_check(t, top, lab, "menvcfg.SSE=1: S-mode sspopchk pops")
        t.li("x7", 0x77)
        lab = run(t, "U", [word(ssrdp("x7"), "ssrdp x7")])
        t.check("x7", 0, lab, "menvcfg.SSE=1, senvcfg.SSE=0: U-mode ssrdp writes 0")
        menv_sse(t, False)
        t.emit("sfence.vma")
        t.li("x7", 0x77)
        t.load("x1", t.rand_x(), "x1")
        lab = run(
            t,
            "S",
            [word(ssrdp("x7"), "ssrdp x7"), word(sspush("x1"), "sspush x1"), word(sspopchk("x1"), "sspopchk x1")],
        )
        t.check("x7", mut("ssrdp_inactive_ssp", 0, top), lab, "menvcfg.SSE=0: S-mode ssrdp writes 0")
        menv_sse(t, True)
        t.emit("sfence.vma")
        ssp_check(t, top, lab, "menvcfg.SSE=0: sspush/sspopchk left ssp")
        mem_check(t, "ss", X(TOP - 4, TOP - 8), v, lab, "menvcfg.SSE=0: sspush made no store")

    vm_either(t, body18)
    vm_off(t)
    teardown(t)
    tests.append(t)

    # ---- menvcfg_sse_op_list ----
    t = new("menvcfg_sse_op_list")
    t.describe(
        source=MAC,
        rule_text="* 32-bit Zicfiss instructions will revert to their behavior as defined by Zimop. * 16-bit Zicfiss "
        "instructions will revert to their behavior as defined by Zcmop. * The pte.xwr=0b010 encoding in VS/S-stage "
        "page tables becomes reserved. * SSAMOSWAP.W/D raises an illegal-instruction exception.",
        context="These apply below M with menvcfg.SSE=0 (senvcfg.SSE and henvcfg.SSE were set while it was 1 and are "
        "now read-only zero). Zimop: mop.r/mop.rr write 0 to rd and nothing else; Zcmop: c.mop writes nothing. satp is "
        "Bare for the MOP checks, so an instruction that wrongly accessed memory would raise an access fault.",
        issues=ISSUE_2708,
        plan="1. S, U and (with H) VS and VU: ssrdp writes 0; sspush x1/x5 and sspopchk x1/x5 with mismatching link "
        "values do nothing (no trap).\n"
        "2. With Zcmop: c.sspush and c.sspopchk (mismatching x5) do nothing, in S and U.\n"
        "3. ssamoswap raises illegal-instruction (xtval 0 or the instruction bits) in S, U, VS and VU (illegal, not "
        "virtual), and leaves rd.\n"
        "4. Paging on: S-mode lw from an xwr=010 page raises a load page fault.\n"
        "5. After menvcfg.SSE is set again, ssp holds the value it had (the MOPs did not change it).",
    )
    t.page("ill", guard_page(t))
    enables(t, 1, 1, 1)
    set_ssp(t, X(0x5550, 0x5550), "ssp")
    menv_sse(t, False)
    for mode, cond in (("S", None), ("U", None), ("VS", H), ("VU", H)):

        def per(mode: str = mode) -> None:
            mop_checks(t, mode, "menvcfg.SSE=0")
            swap_ill(
                t,
                mode,
                mut("sse0_ssamoswap_ok", ILLEGAL, "ok") if MUT != "menvcfg0_virtual" or mode in ("S", "U") else VIRTUAL,
                "menvcfg.SSE=0",
            )

        if cond:
            with t.only_if(cond):
                per()
        else:
            per()
    with t.only_if(ZC):
        for mode in ("S", "U"):
            mop_checks(t, mode, "menvcfg.SSE=0", comp=True)
    menv_sse(t, True)
    lab = t.label("ssp")
    t.emit(f"{lab}:", 0)
    ssp_check(t, mut("c_mop_writes", 0x5550, 0x5550 - 4), lab, "the MOPs left ssp")
    ix = fixture(t, user=False)

    def body19() -> None:
        menv_sse(t, False)
        t.emit("sfence.vma")
        a = va(ix["ss"], 0x900)
        t.load("x6", a, "address")
        ex = mut("sse0_ss_page", LOAD_PF, "ok")
        win(t, "S", ["lw x7, 0(x6)"], ex, "lw from an xwr=010 page with menvcfg.SSE=0", None if ex == "ok" else [0, a])
        menv_sse(t, True)

    vm_either(t, body19)
    vm_off(t)
    teardown(t)
    tests.append(t)

    # ---- senvcfg_sse_Zicfiss ----
    t = new("senvcfg_sse_Zicfiss")
    t.describe(
        source=SUP,
        rule_text="The Zicfiss extension adds the SSE field in senvcfg. When the SSE field is set to 1, the Zicfiss "
        "extension is activated in VU/U-mode. When the SSE field is 0, the Zicfiss extension remains inactive in "
        "VU/U-mode, and the following rules apply:",
        context='The rules: 32-bit Zicfiss instructions revert to Zimop, 16-bit ones to Zcmop, and "When menvcfg.SSE '
        "is one, SSAMOSWAP.W/D raises an illegal-instruction exception in U-mode and a virtual-instruction exception in "
        'VU-mode." satp and vsatp are Bare, so an active shadow-stack access raises a store/AMO access fault '
        "(satp_mode_bare), which shows activation without paging.",
        issues=f"{ISSUE}2424: VU-mode ssamoswap with senvcfg.SSE=0 raises virtual-instruction.",
        plan="1. menvcfg.SSE=1, henvcfg.SSE=1, senvcfg.SSE=0: U-mode and VU-mode ssrdp write 0; sspush/sspopchk (and "
        "with Zcmop c.sspush/c.sspopchk) do nothing.\n"
        "2. ssamoswap: illegal-instruction in U-mode, virtual-instruction in VU-mode (xtval 0 or the instruction bits).\n"
        "3. S-mode is unaffected: ssrdp returns ssp.\n"
        "4. senvcfg.SSE=1: U-mode and VU-mode ssrdp return ssp, and ssamoswap reaches memory (store/AMO access fault "
        "with satp/vsatp Bare).\n"
        "5. menvcfg.SSE=0: ssamoswap in VU-mode is illegal-instruction (the virtual case needs menvcfg.SSE=1).",
    )
    t.page("ill", guard_page(t))
    enables(t, 1, 0, 1)
    set_ssp(t, X(0x5550, 0x5550), "ssp")
    mop_checks(t, "U", "senvcfg.SSE=0")
    swap_ill(t, "U", mut("senvcfg0_ssamoswap_virtual", ILLEGAL, VIRTUAL), "senvcfg.SSE=0")
    with t.only_if(H):
        mop_checks(t, "VU", "senvcfg.SSE=0")
        swap_ill(t, "VU", mut("vu_ssamoswap_illegal", VIRTUAL, ILLEGAL), "senvcfg.SSE=0")
    with t.only_if(ZC):
        mop_checks(t, "U", "senvcfg.SSE=0", comp=True)
    lab = run(t, "S", [word(ssrdp("x7"), "ssrdp x7")])
    t.check("x7", 0x5550, lab, "senvcfg.SSE=0 does not affect S-mode: ssrdp returns ssp")
    senv_sse(t, True)
    for mode, cond in (("U", None), ("VU", H)):

        def act(mode: str = mode) -> None:
            t.li("x7", 0x77)
            lab = run(t, mode, [word(ssrdp("x7"), "ssrdp x7")])
            t.check("x7", 0x5550, lab, f"senvcfg.SSE=1: {mode}-mode ssrdp returns ssp")
            swap_ill(t, mode, STORE_AF, "senvcfg.SSE=1, Bare: ssamoswap reaches memory")

        if cond:
            with t.only_if(cond):
                act()
        else:
            act()
    with t.only_if(H):
        menv_sse(t, False)
        swap_ill(t, "VU", ILLEGAL, "menvcfg.SSE=0")
    teardown(t)
    tests.append(t)

    # ---- henvcfg_sse_op ----
    t = new("henvcfg_sse_op", ["I", "S", "H", "Zicfiss"])
    t.describe(
        source=HYP,
        rule_text="The Zicfiss extension adds the SSE field in henvcfg. If the SSE field is set to 1, the Zicfiss "
        "extension is activated in VS-mode. When the SSE field is 0, the Zicfiss extension remains inactive in VS-mode, "
        "and the following rules apply when V=1:",
        context="The rules: 32-bit Zicfiss instructions revert to Zimop, 16-bit ones to Zcmop; xwr=010 in VS-stage "
        "tables is reserved; senvcfg.SSE is read-only zero; with menvcfg.SSE=1, SSAMOSWAP raises virtual-instruction. "
        "vsatp and hgatp are Bare except for the VS-stage page-table case.",
        issues=ISSUE_2424 + f' {ISSUE}2077: "the following rules apply when V=1" (ved-rivos); MPRV/MPV do not '
        "affect accesses to the envcfg CSRs.",
        plan="1. menvcfg.SSE=1, senvcfg.SSE=1, henvcfg.SSE=0: VS-mode ssrdp writes 0, sspush/sspopchk (and with Zcmop "
        "c.sspush/c.sspopchk) do nothing.\n"
        "2. VS-mode and VU-mode ssamoswap raise virtual-instruction (xtval 0 or the instruction bits).\n"
        "3. senvcfg.SSE read in VS-mode is 0 though HS-mode set it; VU-mode ssrdp writes 0. A VS-mode clear of "
        "senvcfg.SSE does not change the bit HS-mode sees.\n"
        "4. VS-stage xwr=010 is reserved: a VS-mode lw from such a page raises a load page fault.\n"
        "5. henvcfg.SSE=1 (and senvcfg.SSE written again by HS-mode, as its V=1 view may be UNSPECIFIED after the "
        "change): VS-mode ssrdp returns ssp, the same lw reads the page, and VS-mode reads senvcfg.SSE=1.",
    )
    t.page("ill", guard_page(t))
    enables(t, 1, 1, 0)
    set_ssp(t, X(0x5550, 0x5550), "ssp")
    mop_checks(t, "VS", "henvcfg.SSE=0")
    with t.only_if(ZC):
        mop_checks(t, "VS", "henvcfg.SSE=0", comp=True)
    for mode in ("VS", "VU"):
        swap_ill(t, mode, VIRTUAL if MUT != "vu_ignores_henvcfg" or mode == "VS" else STORE_AF, "henvcfg.SSE=0")
    lab = run(t, "VS", ["csrr x7, 0x10A  // senvcfg"])
    t.emit(f"andi x7, x7, {SSE}")
    t.check("x7", mut("vu_ignores_henvcfg", 0, SSE), lab, "VS-mode reads senvcfg.SSE = 0 with henvcfg.SSE=0")
    t.li("x7", 0x77)
    lab = run(t, "VU", [word(ssrdp("x7"), "ssrdp x7")])
    t.check("x7", mut("vu_ignores_henvcfg", 0, 0x5550), lab, "VU-mode ssrdp with senvcfg.SSE=1, henvcfg.SSE=0 writes 0")
    lab = run(t, "VS", ["csrc 0x10A, x6  // senvcfg.SSE"], pre=lambda: t.li("x6", SSE))
    t.emit("csrr x7, 0x10A")
    t.emit(f"andi x7, x7, {SSE}")
    t.check("x7", SSE, lab, "a VS-mode clear of the read-only-zero senvcfg.SSE leaves HS-mode's bit")
    ix = vs_fixture(t)

    def body20() -> None:
        a = va(ix["ss"], 0x900)
        data = page_bytes(t, "ssv")
        t.load("x6", a, "address")
        ex = mut("henvcfg0_ss_page", LOAD_PF, "ok")
        win(
            t,
            "VS",
            ["lw x7, 0(x6)"],
            ex,
            "lw from a VS-stage xwr=010 page with henvcfg.SSE=0",
            None if ex == "ok" else [0, a],
        )
        henv_sse(t, True)
        senv_sse(t, True)  # rewritten: its V=1 view may be UNSPECIFIED after henvcfg.SSE changes (field modulation)
        t.emit(".word 0x22000073  // hfence.vvma")
        t.load("x6", a, "address")
        lab = run(t, "VS", ["lw x7, 0(x6)", word(ssrdp("x8"), "ssrdp x8"), "csrr x9, 0x10A  // senvcfg"])
        t.check(
            "x7",
            X(ld_val(data, 0x900, 4, True, 32), ld_val(data, 0x900, 4, True, 64)),
            lab,
            "henvcfg.SSE=1: VS-mode lw reads the VS-stage xwr=010 page",
        )
        t.check("x8", 0x5550, lab, "henvcfg.SSE=1: VS-mode ssrdp returns ssp")
        t.emit(f"andi x9, x9, {SSE}")
        t.check("x9", SSE, lab, "henvcfg.SSE=1: VS-mode reads senvcfg.SSE = 1")

    vm_either(t, body20, root="vsatp")
    vm_off(t, root="vsatp")
    teardown(t)
    tests.append(t)

    # ---- ssmp_henvcfg_sse ----
    t = new("ssmp_henvcfg_sse", ["I", "S", "H", "Zicfiss"])
    t.describe(
        source=PCFI,
        rule_text="Similarly, when V=1 and henvcfg[sse]=0, this encoding remains reserved at VS and VU levels.",
        context="VS-stage translation (vsatp Sv39/Sv32, hgatp Bare) maps an xwr=010 page for VS-mode. A reserved leaf "
        "raises a page fault for the access type, taken in HS-mode. henvcfg.SSE does not affect HS-mode (V=0) "
        "translation through satp. hfence.vvma follows each henvcfg.SSE change.",
        plan="1. henvcfg.SSE=0 (menvcfg.SSE=1): VS-mode lw from the VS-stage xwr=010 page raises a load page fault "
        "(13), sw a store/AMO page fault (15), a fetch an instruction page fault (12); xtval 0 or the address.\n"
        "2. HS-mode (V=0), satp mapping an xwr=010 page: sspush succeeds with henvcfg.SSE=0.\n"
        "3. henvcfg.SSE=1: the VS-mode lw reads the page and VS-mode sspush on it pushes.",
    )
    enables(t, 1, 1, 0)
    six = fixture(t, user=False)
    ix = vs_fixture(t)

    def body21() -> None:
        a = va(ix["ss"], 0x900)
        data = page_bytes(t, "ssv")
        lf = mut("henvcfg0_ss_page", LOAD_PF, "ok")
        t.load("x6", a, "address")
        win(
            t,
            "VS",
            ["lw x7, 0(x6)"],
            lf,
            "lw from a VS-stage xwr=010 page, henvcfg.SSE=0",
            None if lf == "ok" else [0, a],
        )
        t.load("x6", a, "address")
        win(
            t,
            "VS",
            ["sw x7, 0(x6)"],
            mut("henvcfg0_ss_page", STORE_PF, STORE_AF),
            "sw to a VS-stage xwr=010 page, henvcfg.SSE=0",
            [0, a],
        )
        t.load("x6", a, "fetch target")
        win(
            t,
            "VS",
            ["jalr x1, 0(x6)"],
            mut("henvcfg0_ss_page", INSN_PF, INSN_AF),
            "fetch from a VS-stage xwr=010 page, henvcfg.SSE=0",
            [0, a],
            epc=a,
        )
        top = va(six["ss"], TOP)
        set_ssp(t, top)
        lab = ss_op(t, "S", "sspush", "x1", t.rand_x(), "ok", "")
        ssp_check(t, xsub(top, XB), lab, "HS-mode sspush on an S-stage xwr=010 page with henvcfg.SSE=0")
        henv_sse(t, True)
        t.emit(".word 0x22000073  // hfence.vvma")
        t.load("x6", a, "address")
        lab = run(t, "VS", ["lw x7, 0(x6)"])
        t.check(
            "x7",
            X(ld_val(data, 0x900, 4, True, 32), ld_val(data, 0x900, 4, True, 64)),
            lab,
            "henvcfg.SSE=1: VS-mode lw reads the VS-stage xwr=010 page",
        )
        vtop = va(ix["ss"], TOP)
        set_ssp(t, vtop)
        v = t.rand_x()
        lab = ss_op(t, "VS", "sspush", "x1", v, "ok", "")
        ssp_check(t, xsub(vtop, XB), lab, "henvcfg.SSE=1: VS-mode sspush on the VS-stage xwr=010 page")
        mem_check(t, "ssv", X(TOP - 4, TOP - 8), v, lab, "henvcfg.SSE=1: VS-mode sspush stores")

    vm_either(t, lambda: vm_either(t, body21, root="vsatp"))
    vm_off(t, root="vsatp")
    vm_off(t)
    teardown(t)
    tests.append(t)

    # ---- stval_exception_info ----
    t = new("stval_exception_info")
    t.describe(
        source=SUP,
        rule_text="On a trap caused by a software-check exception, the stval register holds the cause for the "
        "exception. The following encodings are defined:",
        context="The list: 0 no information, 2 landing pad fault (Zicfilp), 3 shadow stack fault (Zicfiss). This suite "
        "checks code 3: a sspopchk mismatch taken in S/HS-mode (software checks are delegated to S-mode; with H, "
        "hedeleg is 0, so VS-mode ones are taken in HS-mode). stval is preset to another value before each trap.",
        plan="1. S-mode sspopchk mismatch: scause 18, stval 3.\n"
        "2. U-mode sspopchk mismatch: scause 18, stval 3.\n"
        "3. With Zcmop: c.sspopchk mismatch in S-mode: stval 3.\n"
        "4. With H: VS-mode sspopchk mismatch on a VS-stage SS page (henvcfg.SSE=1): taken in HS-mode, stval 3.",
    )
    enables(t, 1, 1, 1)
    ix = fixture(t, ss_contents=pop_contents(11))

    def mism(mode: str, page: str, insn: str, link: str, pg: str | None = None) -> None:
        top = va(ix[page], TOP)
        set_ssp(t, top)
        v = pop_values(t, pg or page, 1)[0]
        preset_tval(t, 0x5A0)
        ss_op(t, mode, insn, link, X(v.num(32) ^ 0x20, v.num(64) ^ 0x20), sw_cause(), f"{insn} mismatch", sw_tval())

    vm_either(t, lambda: (mism("S", "ss", "sspopchk", "x1"), mism("U", "ssu", "sspopchk", "x5")))
    with t.only_if(ZC):
        vm_either(t, lambda: mism("S", "ss", "c.sspopchk", "x5"))
    vm_off(t)
    with t.only_if(H):
        vix = vs_fixture(t)

        def vbody() -> None:
            top = va(vix["ss"], TOP)
            set_ssp(t, top)
            v = pop_values(t, "ssv", 1)[0]
            preset_tval(t, 0x5A0)
            ss_op(
                t,
                "VS",
                "sspopchk",
                "x1",
                X(v.num(32) ^ 0x20, v.num(64) ^ 0x20),
                sw_cause(),
                "sspopchk mismatch",
                sw_tval(),
            )

        vm_either(t, vbody, root="vsatp")
        vm_off(t, root="vsatp")
    teardown(t)
    tests.append(t)

    # ---- mtval_swchk_list_Sm ----
    t = new("mtval_swchk_list", REQ_M, boot="M", suffix="_Sm")
    t.describe(
        source=MAC,
        rule_text="* 0 - No information provided. * 2 - Landing Pad Fault. Defined by the Zicfilp extension "
        "(<<priv-forward>>). * 3 - Shadow Stack Fault. Defined by the Zicfiss extension (<<priv-backward>>).",
        context="mtval on a software-check exception taken in M-mode (mtval_swchk_lead_in). This suite checks code 3: "
        "with medeleg[18]=0, an S-mode sspopchk mismatch is taken in M-mode. The test boots to M, builds the S-level "
        "map, sets menvcfg.SSE and enters S-mode with mret. mtval is preset.",
        plan="1. medeleg[18]=0: S-mode sspopchk mismatch: taken in M-mode (handler mode M), mcause 18, mtval 3.\n"
        "2. With Zcmop: c.sspopchk mismatch: the same.\n"
        "3. A matching sspopchk in S-mode pops without a trap.",
    )
    t.li("x6", SSE)
    t.emit("csrs menvcfg, x6")
    t.li("x6", 1 << 18)
    t.emit("csrc medeleg, x6  // software checks to M-mode")
    ix = fixture(t, user=False, ss_contents=pop_contents(12))

    def mbody(insn: str, link: str) -> Callable[[], None]:
        def b() -> None:
            top = va(ix["ss"], TOP)
            t.load("x6", top, "ssp")
            t.emit("csrw 0x011, x6")
            v = pop_values(t, "ss", 1)[0]
            t.li("x6", 0x5A0)
            t.emit("csrw mtval, x6  // preset")
            lab = ss_op(
                t, "S", insn, link, X(v.num(32) ^ 0x200, v.num(64) ^ 0x200), sw_cause(), f"{insn} mismatch", sw_tval()
            )
            t.emit("AI_LOG(x15, TRAPLOG_VECT)", 10)
            t.emit("andi x15, x15, 3")
            t.check(
                "x15",
                mut("swcheck_not_delegated", 3, 1),
                lab,
                f"{insn} mismatch with medeleg[18]=0 is taken in M-mode (handler mode 3)",
            )
            if insn == "sspopchk":
                lab = ss_op(t, "S", insn, link, v, "ok", "")
                t.emit("csrr x7, 0x011")
                t.check("x7", xadd(top, XB), lab, "a matching sspopchk in S-mode pops")

        return b

    vm_either(t, mbody("sspopchk", "x1"))
    with t.only_if(ZC):
        vm_either(t, mbody("c.sspopchk", "x5"))
    vm_off(t)
    t.li("x6", SSE)
    t.emit("csrc menvcfg, x6")
    tests.append(t)

    # ---- Zicfiss_smode_xsse_Sm ----
    t = new("Zicfiss_smode_xsse", ["I", "Sm", "U", "Zicfiss"], boot="M", suffix="_Sm", forbidden=["S"])
    t.describe(
        source=PCFI,
        rule_text="When S-mode is not implemented, then xSSE is 0.",
        context="Only harts without S-mode select this file. With xSSE=0, ssrdp writes 0 and sspush/sspopchk are "
        "MOPs in M and U. SSAMOSWAP raises illegal-instruction when S-mode is not implemented (its pseudocode), in "
        "M-mode too. menvcfg.SSE (if writable) is set first: it must not activate anything. The ssp CSR is not "
        "used (its U-mode access rule without S-mode is #2708).",
        issues=f'{ISSUE}2708: without S-mode, "all instructions besides ssamoswap become mop, ssamoswap will raise '
        'an illegal-instruction exception" (ved-rivos).',
        plan="1. M-mode: ssrdp writes 0; sspush x1 and sspopchk x1 (mismatch) make no access and do not trap; "
        "ssamoswap raises illegal-instruction (xtval 0 or the instruction bits).\n"
        "2. U-mode: the same.",
    )
    t.page("ill", guard_page(t))
    t.li("x6", SSE)
    t.emit("csrs menvcfg, x6")
    for mode in ("M", "U"):
        t.li("x7", 0x77)
        t.li("x1", 0x1111)
        lab = win(
            t,
            mode,
            [word(ssrdp("x7"), "ssrdp x7"), word(sspush("x1"), "sspush x1"), word(sspopchk("x1"), "sspopchk x1")],
            "ok",
            "Zicfiss instructions without S-mode",
        )
        t.check("x7", mut("ssrdp_inactive_ssp", 0, 0x77), lab, f"ssrdp in {mode}-mode without S-mode writes 0")
        swap_ill(t, mode, mut("sse0_ssamoswap_ok", ILLEGAL, "ok"), "S-mode not implemented")
    t.li("x6", SSE)
    t.emit("csrc menvcfg, x6")
    tests.append(t)

    # ---- active_g_stage_pte ----
    t = new("active_g_stage_pte", ["I", "S", "H", "Zicfiss"])
    t.describe(
        source=PCFI,
        rule_text="When G-stage page tables are active, the shadow stack instructions that access memory require the "
        "G-stage page table to have read-write permission for the accessed memory; else a store/AMO guest-page-fault "
        "exception is raised.",
        context="VS-mode code runs with VS-stage (Sv39/Sv32) and G-stage (Sv39x4/Sv32x4) translation; both modes are "
        "probed. The test image is identity mapped in both stages. Each test page is an SS page (xwr=010) in the "
        "VS-stage, mapped to a guest physical page whose G-stage leaf has U plus RW, R, RX or W only (W only is "
        "reserved in G-stage). The fault is taken in HS-mode: xtval 0 or the guest virtual address, htval 0 or the "
        "GPA >> 2, GVA=1 when xtval is nonzero; htinst is 0 for sspush/sspopchk (no transformation, #1935, #2477) "
        "and 0 or the transformed AMO for ssamoswap.",
        issues=f'{ISSUE}1935: "For sspush/sspopchk/c.sspush/c.sspop instructions there are no transformations '
        "defined; these will write 0 to mtinst/htinst. The ssamoswap instruction follows the rules of AMO instruction "
        f'transformation." {ISSUE}2477: guest-page faults on the explicit access write htinst = 0.',
        plan="1. G-stage RW: VS-mode sspush x1 pushes, sspopchk x1 pops, ssamoswap swaps.\n"
        "2. G-stage R only, RX, and W only: sspush, sspopchk and ssamoswap raise a store/AMO guest-page fault (23) with "
        "the xtval, htval, GVA and htinst checks above; ssp unchanged.",
    )
    from hmem import G_OF, GPA_BASE, LEAF, PT, ULEAF, XP, R, atp_off, hgatp_on, memwin, vsatp_on

    enables(t, 1, 1, 1)
    gperms = [
        ("grw", V | R | W | A | D | U),
        ("gro", V | R | A | D | U),
        ("grx", V | R | XP | A | D | U),
        ("gwo", V | W | A | D | U),
    ]
    for n, _ in gperms:
        t.page(n, guard_page(t, seed=20))

    def build(xlen: int) -> None:
        g = PT(t, f"g{xlen}", G_OF[xlen], xlen)
        g.identity(ULEAF)
        vs = PT(t, f"vs{xlen}", SCHEMES[xlen], xlen)
        vs.identity(LEAF)
        for i, (n, p) in enumerate(gperms):
            gpa = GPA_BASE[xlen] + i * 0x1000
            vs.leaf(VA0x[xlen] + i * 0x1000, gpa, SS, note=f"-> GPA of {n}")
            g.leaf(gpa, f"ai_pg_{n}", p, note=f"({n})")
        hgatp_on(t, g)
        vsatp_on(t, vs)

    from hmem import both as hboth

    hboth(t, build)

    def gva(i: int, off: int) -> X:
        return va(i, off)

    def gpa(i: int, off: int) -> X:
        return X(GPA_BASE[32] + i * 0x1000 + off, GPA_BASE[64] + i * 0x1000 + off)

    def body22() -> None:
        top = gva(0, TOP)
        set_ssp(t, top)
        v = t.rand_x()
        lab = ss_op(t, "VS", "sspush", "x1", v, "ok", "")
        ssp_check(t, xsub(top, XB), lab, "G-stage RW: VS-mode sspush pushes")
        mem_check(t, "grw", X(TOP - 4, TOP - 8), v, lab, "G-stage RW: VS-mode sspush stores")
        lab = ss_op(t, "VS", "sspopchk", "x1", v, "ok", "")
        ssp_check(t, top, lab, "G-stage RW: VS-mode sspopchk pops")
        t.load("x6", gva(0, 0x900), "address")
        w = t.rand_x()
        t.load("x8", w, "rs2")
        lab = run(t, "VS", swap_line())
        mem_check(t, "grw", 0x900, w, lab, "G-stage RW: VS-mode ssamoswap swaps")
        for i, (n, _) in enumerate(gperms[1:], 1):
            ex = "ok" if (MUT == "gstage_r_ok" and n == "gro") else STORE_GPF
            for insn in ("sspush", "sspopchk", "swap"):
                tp = gva(i, TOP)
                set_ssp(t, tp)
                t.load("x6", tp, "address")
                t.load("x1", t.rand_x(), "x1")
                a = xsub(tp, XB) if insn == "sspush" else tp
                p = xsub(gpa(i, TOP), XB) if insn == "sspush" else gpa(i, TOP)
                if insn == "swap":
                    lines = swap_line()
                    e = ssamoswap_insn()
                    tinst: list[Value] = [0, X(amo_tf(e.num(32)), amo_tf(e.num(64)))]
                else:
                    lines = ss_lines(insn, "x1")
                    tinst = [0]
                extras = {
                    STORE_GPF: {
                        "tval": [0, a],
                        "gva": 1,
                        "tval2": [0, X(p.num(32) >> 2, p.num(64) >> 2)],
                        "tinst": tinst,
                    }
                }
                lab = memwin(t, "VS", lines, ex, f"{insn} through a G-stage {n[1:].upper()} page", extras)
                if ex != "ok":
                    ssp_check(t, tp, lab, f"{insn} with a G-stage guest-page fault leaves ssp")

    t.comment("probe: hgatp and vsatp MODE accepted?")
    t.emit("csrr x9, 0x680")
    t.emit("csrr x8, 0x280")
    with t.rv64_only():
        t.emit("srli x9, x9, 60")
        t.emit("srli x8, x8, 60")
    with t.rv32_only():
        t.emit("srli x9, x9, 31")
        t.emit("srli x8, x8, 31")
    t.emit("and x9, x9, x8")
    t.either("x9", body22, lambda: t.comment("G-stage or VS-stage MODE not supported: skipped"))
    atp_off(t)
    teardown(t)
    tests.append(t)


SCHEMES = {32: "sv32", 64: "sv39"}
VA0x = {32: 0x2000_0000, 64: 0x4000_0000}


# ==== SECTIONS ====


def gen() -> list:
    tests: list = []
    for f in TESTS:
        f(tests)
    rules = [t.rule + t.suffix for t in tests]
    dup = {r for r in rules if rules.count(r) > 1}
    assert not dup, f"duplicate rules: {dup}"
    return tests


def main() -> None:
    only = set(sys.argv[1:])
    for t in gen():
        if only and t.rule + t.suffix not in only and t.rule not in only:
            continue
        p = t.write()
        print(f"{p.relative_to(p.parents[2])}: ~{t.ninst} instructions")


if __name__ == "__main__":
    main()
