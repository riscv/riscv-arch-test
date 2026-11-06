#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate tests_ai/Sstc: one test per normative rule about Sstc.

The Sstc chapter (src/priv/sstc.adoc) only declares the CSRs and the STCE bits; the behavior is
tagged where stimecmp, menvcfg, mip/sip and mcounteren are defined (supervisor.adoc, machine.adoc,
hypervisor.adoc). Tests boot to S-mode, use T-SBI for M-level CSRs (menvcfg, mcounteren, mip) and
M-mode accesses, and check expected traps and interrupts in the framework trap log (trap windows,
common/ai_macros.h).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent))
from aigen import POOL_TRAP, TestFile, X

if TYPE_CHECKING:
    from aigen import Expect, Value

SUITE = "Sstc"
ISSUE = "https://github.com/riscv/riscv-isa-manual/issues/"
REQ = ["I", "S", "Sstc"]
REQ_T = ["I", "S", "Sstc", "Zicntr"]  # tests that read time
MARCH = "rv${XLEN}i_zicsr_zifencei"
SUP = "src/priv/supervisor.adoc"
MAC = "src/priv/machine.adoc"
SSTC = "src/priv/sstc.adoc"

STIP = 0x20
SIE = 0x2
SPIE = 0x20
SPP = 0x100
MAX64 = (1 << 64) - 1
STI = X((1 << 31) | 5, (1 << 63) | 5)
CSR = {"stimecmp": 0x14D, "stimecmph": 0x15D, "vstimecmp": 0x24D, "vstimecmph": 0x25D}
H = "defined(H_SUPPORTED)"
MUT = os.environ.get("AI_MUTANT", "")  # mutate.py: model a plausible bug in the expectations

ISSUE_1636 = (
    f"{ISSUE}1636: when STCE changes, mip.STIP/sip.STIP takes an UNSPECIFIED value (the CSR "
    'field-modulation rule, quoted by ved-rivos): "If a write to one CSR changes the set of legal values allowed for a field '
    "of a second CSR ... the second CSR's field immediately gets an UNSPECIFIED value from among its new "
    'legal values." Tests write mip.STIP after clearing STCE before relying on it.'
)
ISSUE_1169 = f"{ISSUE}1169: stimecmp has no reset value, so every test writes it before use."
ISSUE_2237 = (
    f"{ISSUE}2237: all ones in stimecmp is not a sentinel that disables the timer; STIP is "
    "pending only when time >= stimecmp (\"that doesn't mean that the value 2^64-1 is a sentinel value "
    'that suppresses the interrupt from firing"). With time < 2^64-1 it reads 0.'
)
ISSUE_1985 = (
    f"{ISSUE}1985: with menvcfg.STCE=1 and henvcfg.STCE=0, stimecmp accesses from VS and VU "
    'raise virtual-instruction exceptions (jhauser-us: "All of the listed cases should raise a '
    'virtual-instruction exception").'
)
ISSUE_3329 = (
    f'{ISSUE}3329: the STCE=0 rule covers "stimecmp or vstimecmp"; the vstimecmp words were '
    "restored after an accidental drop."
)


# ---------------------------------------------------------------- helpers
def new(rule: str, required: list[str] = REQ) -> TestFile:
    return TestFile(SUITE, rule, required=required, march=MARCH, boot="S", pool=POOL_TRAP)


def stce(t: TestFile, on: bool) -> None:
    op = "SET" if on else "CLEAR"
    t.comment(f"menvcfg.STCE = {int(on)}")
    with t.rv64_only():
        t.li("a1", 1)
        t.emit("slli a1, a1, 63")
        t.tsbi_csr(op, "MENVCFG", "a1")
    with t.rv32_only():
        t.li("a1", 0x80000000)
        t.tsbi_csr(op, "MENVCFGH", "a1")


def tm(t: TestFile, on: bool) -> None:
    t.comment(f"mcounteren.TM = {int(on)}")
    t.tsbi_csr("SET" if on else "CLEAR", "MCOUNTEREN", imm=2)


def mip_stip(t: TestFile, on: bool) -> None:
    t.comment(f"M-mode write mip.STIP = {int(on)}")
    t.tsbi_csr("SET" if on else "CLEAR", "MIP", imm=STIP)


def cmp_s(t: TestFile, v: int, note: str = "") -> None:
    """S-mode write of a 64-bit constant to stimecmp (needs STCE=1, TM=1)."""
    with t.rv64_only():
        t.load("x6", v, note)
        t.emit("csrw stimecmp, x6")
    with t.rv32_only():
        t.load("x6", v >> 32, f"{note} (high half)" if note else "")
        t.emit("csrw stimecmph, x6")
        t.load("x6", v & 0xFFFFFFFF, f"{note} (low half)" if note else "")
        t.emit("csrw stimecmp, x6")


def cmp_m(t: TestFile, v: int, note: str = "") -> None:
    """M-mode (T-SBI) write of a 64-bit constant to stimecmp."""
    with t.rv64_only():
        t.load("a1", v, note)
        t.tsbi_csr("WRITE", "STIMECMP", "a1")
    with t.rv32_only():
        t.load("a1", v >> 32, f"{note} (high half)" if note else "")
        t.tsbi_csr("WRITE", "STIMECMPH", "a1")
        t.load("a1", v & 0xFFFFFFFF, f"{note} (low half)" if note else "")
        t.tsbi_csr("WRITE", "STIMECMP", "a1")


def cmp_now(t: TestFile, k: int) -> None:
    """S-mode write stimecmp = time + k*2^32 (k = 0 means the time just read)."""
    t.comment(f"stimecmp = time + {k}*2^32")
    with t.rv64_only():
        t.emit("csrr x6, time")
        if k:
            t.li("x7", k)
            t.emit("slli x7, x7, 32")
            t.emit("add x6, x6, x7")
        t.emit("csrw stimecmp, x6")
    with t.rv32_only():
        # k=0: read timeh first, so a low-half wrap between the reads leaves stimecmp <= time.
        # k>0: read time first, so a wrap leaves stimecmp > time (still not pending).
        if k:
            t.emit("csrr x7, time")
            t.emit("csrr x6, timeh")
            t.emit(f"addi x6, x6, {k}")
        else:
            t.emit("csrr x6, timeh")
            t.emit("csrr x7, time")
        t.emit("csrw stimecmph, x6")
        t.emit("csrw stimecmp, x7")


def poll_stip(t: TestFile, until: int, n: int = 500) -> None:
    """Read sip.STIP into x8 until it equals `until` or n reads pass (bounded wait, no checks inside).
    STIP need only reflect a comparison change eventually."""
    loop, done = t.label("wait"), t.label("waitdone")
    t.li("x9", n)
    t.emit(f"{loop}:", 0)
    t.emit("csrr x8, sip", n)
    t.emit(f"andi x8, x8, {STIP}", n)
    t.emit(f"{'bnez' if until else 'beqz'} x8, {done}", n)
    t.emit("addi x9, x9, -1", n)
    t.emit(f"bnez x9, {loop}", n)
    t.emit(f"{done}:", 0)


def expect_stip(t: TestFile, value: int, desc: str, settle: bool = True) -> None:
    """Check sip.STIP. A change to 1 or 0 is awaited; a steady value is watched for a glitch."""
    lab = t.label("stip")
    poll_stip(t, until=value if settle else 1 - value, n=500 if settle else 50)
    t.emit(f"{lab}:", 0)
    t.check("x8", STIP if value else 0, lab, f"sip.STIP after {desc}")


def expect_mip_stip(t: TestFile, value: int, desc: str) -> None:
    lab = t.label("mip")
    t.emit(f"{lab}:", 0)
    t.tsbi_csr("READ", "MIP")
    t.emit(f"andi a0, a0, {STIP}")
    t.check("a0", STIP if value else 0, lab, f"mip.STIP (M-mode read) after {desc}")


def enc(csr: int, f3: int, rd: int, rs1: int) -> int:
    return (csr << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | 0x73


# CSR instruction forms: (asm template, funct3, rd, rs1-or-uimm, kind). rd x7, rs x6, uimm 0x15.
Form = tuple[str, int, int, int, str]
FORMS: list[Form] = [
    ("csrrs x7, {c}, x0", 2, 7, 0, "read (csrrs rs1=x0)"),
    ("csrrw x0, {c}, x6", 1, 0, 6, "write (csrrw rd=x0)"),
    ("csrrw x7, {c}, x6", 1, 7, 6, "swap (csrrw)"),
    ("csrrs x7, {c}, x6", 2, 7, 6, "set (csrrs)"),
    ("csrrc x7, {c}, x6", 3, 7, 6, "clear (csrrc)"),
    ("csrrwi x7, {c}, 0x15", 5, 7, 0x15, "write immediate (csrrwi)"),
    ("csrrsi x7, {c}, 0", 6, 7, 0, "read (csrrsi uimm=0)"),
    ("csrrci x7, {c}, 0x15", 7, 7, 0x15, "clear immediate (csrrci)"),
]


def access(t: TestFile, mode: str, csr: str, form: Form, expect: str, desc: str) -> str:
    """Execute one CSR instruction in `mode` (S, U, VS, VU) in a trap window and check the
    outcome: 'ok' (no trap), 'illegal' (cause 2) or 'virtual' (cause 22). Faulting instructions accept
    xtval = 0 or the instruction bits. Returns the label of the instruction."""
    asm, f3, rd, rs1, kind = form
    cause = {"ok": "ok", "illegal": 2, "virtual": 22}[expect]
    tval: list[Value] | None = None if expect == "ok" else [0, enc(CSR[csr], f3, rd, rs1)]
    origin = "S" if MUT == "spp_wrong" and mode == "U" else mode
    return t.window(mode, [asm.format(c=csr)], cause, f"{kind} of {csr} ({desc})", tval, origin)


def mtimecmp(t: TestFile, v: int) -> None:
    """M-mode (T-SBI) stores of a 64-bit value to the platform mtimecmp (RVMODEL_MTIMECMP_ADDRESS)."""
    t.comment(f"mtimecmp = {'all ones' if v else '0'}")
    for off, word in ((0, v & 0xFFFFFFFF), (4, v >> 32)):
        t.emit(f"LI(a1, RVMODEL_MTIMECMP_ADDRESS + {off})", 2)
        t.load("a2", X(word, word), "mtimecmp word")
        t.emit("RVTEST_TSBI_SW", 120)


def h_guest_setup(t: TestFile, henv_stce: bool = True, htm: bool = True) -> None:
    """HS-mode: set henvcfg.STCE and hcounteren.TM as requested. Call inside only_if(H)."""
    op = "csrs" if henv_stce else "csrc"
    with t.rv64_only():
        t.li("x7", 1)
        t.emit("slli x7, x7, 63")
        t.emit(f"{op} CSR_HENVCFG, x7")
    with t.rv32_only():
        t.li("x7", 0x80000000)
        t.emit(f"{op} CSR_HENVCFGH, x7")
    t.li("x7", 2)
    t.emit(f"{'csrs' if htm else 'csrc'} CSR_HCOUNTEREN, x7")


def setup(t: TestFile) -> None:
    t.comment("setup: mcounteren.TM=1, menvcfg.STCE=1, stimecmp parked at all ones, sie.STIE=0")
    tm(t, True)
    stce(t, True)
    cmp_s(t, MAX64, "all ones")
    t.li("x6", STIP)
    t.emit("csrc sie, x6")
    t.blank()


def teardown(t: TestFile) -> None:
    t.blank()
    t.comment("teardown: sie.STIE=0, stimecmp all ones (M write), STCE=0, TM=1")
    t.li("x6", STIP)
    t.emit("csrc sie, x6")
    cmp_m(t, MAX64, "all ones")
    stce(t, False)
    tm(t, True)


def form_value(form: Form, old: int, rs: int, width: int) -> tuple[int | None, int]:
    """(rd, new) for a CSR form on a register of `width` bits holding old, with rs in x6."""
    _, f3, rd, rs1, _ = form
    m = (1 << width) - 1
    src = (rs if rs1 == 6 else 0) if f3 in (1, 2, 3) else rs1  # register forms read x6 or x0
    new = {1: src, 5: src, 2: old | src, 6: old | src, 3: old & ~src, 7: old & ~src}[f3] & m
    return (old if rd else None), new


def interrupt_case(t: TestFile, mode: str, sie: int, stie: int, pending: int) -> None:
    """Set sie.STIE, make STI pending or not, then run in `mode` with sstatus.SIE = sie and wait, in a
    trap window. STI is delegated to S (mideleg.STIP=1). In S-mode it is taken iff SIE=1 and STIE=1; in
    U-mode iff STIE=1, regardless of SIE. The handler masks sie.STIE when it takes the interrupt."""
    taken = pending and stie and (sie or (mode == "U" and MUT != "u_needs_sie"))
    desc = f"{mode}-mode, sstatus.SIE={sie}, sie.STIE={stie}, STI pending={pending}"
    t.comment(desc)
    t.li("x6", STIP)
    t.emit(f"{'csrs' if stie else 'csrc'} sie, x6")
    cmp_s(t, 0 if pending else MAX64, "0 (pending)" if pending else "all ones (not pending)")
    if pending:
        poll_stip(t, 1)
    lab = t.label(f"int{mode}")
    if mode == "S":
        t.li("x6", SIE)
        t.allow(1)
        t.emit(f"{lab}:", 0)
        if sie:
            t.emit("csrs sstatus, x6")
        poll_stip(t, 2, 50)  # a 50-iteration delay window
    else:
        t.li("x6", SPIE)
        t.emit(f"{'csrs' if sie else 'csrc'} sstatus, x6")  # sret copies SPIE into SIE
        t.allow(1)
        t.enter("U")
        t.emit(f"{lab}:", 0)
        loop = t.label("delay")
        t.li("x9", 50)
        t.emit(f"{loop}:", 0)
        t.emit("addi x9, x9, -1", 50)
        t.emit(f"bnez x9, {loop}", 50)
        t.leave()
    t.li("x6", SIE)
    t.emit("csrc sstatus, x6")
    t.li("x6", STIP)
    t.emit("csrc sie, x6")
    t.outcome(
        STI if taken else "ok",
        lab,
        f"{desc}: supervisor timer interrupt {'must be taken' if taken else 'must not be taken'}",
        epc=False,
        origin=mode,
    )


# ---------------------------------------------------------------- tests
def gen() -> list[TestFile]:
    tests = []

    # ---- stimecmp_exist ----
    t = new("stimecmp_exist")
    t.describe(
        source=SSTC,
        rule_text="This extension adds the S-level stimecmp CSR (<<stimecmp>>)",
        context="stimecmp (0x14D, and stimecmph 0x15D on RV32) is an SRW CSR. Access from below M-mode is "
        "gated by menvcfg.STCE and mcounteren.TM (menvcfg_stce_*, mcounteren_tm_*), so this test enables "
        "both.",
        issues=ISSUE_1169,
        plan="1. In S-mode, read and write stimecmp (and stimecmph on RV32) without a trap.\n"
        "2. Round trip from S-mode: write 0, all ones, 2^63 and three random 64-bit values and read them "
        "back.\n"
        "3. The S-mode and M-mode views agree: an S write is read back through T-SBI (M-mode), and an "
        "M-mode write is read back in S-mode.",
    )
    setup(t)
    access(t, "S", "stimecmp", FORMS[0], "ok", "STCE=1, TM=1")
    t.emit("li x6, 0")
    access(t, "S", "stimecmp", FORMS[1], "ok", "STCE=1, TM=1")
    with t.rv32_only():
        access(t, "S", "stimecmph", FORMS[0], "ok", "STCE=1, TM=1")
    values = [(0, "zero"), (MAX64, "all ones"), (1 << 63, "2^63")] + [(t.rand(64), "random") for _ in range(3)]
    for v, note in values:
        cmp_s(t, v, note)
        lab = t.label("rt")
        with t.rv64_only():
            t.emit(f"{lab}:", 0)
            t.emit("csrr x7, stimecmp")
            t.check("x7", v, lab, f"stimecmp reads back {note} written in S-mode")
        with t.rv32_only():
            t.emit(f"{lab}:", 0)
            t.emit("csrr x7, stimecmp")
            t.check("x7", v & 0xFFFFFFFF, lab, f"stimecmp reads back the low half of {note}")
            t.emit("csrr x7, stimecmph")
            t.check("x7", v >> 32, lab, f"stimecmph reads back the high half of {note}")
    last = values[-1][0]
    lab = t.label("mview")
    t.emit(f"{lab}:", 0)
    t.tsbi_csr("READ", "STIMECMP")
    with t.rv64_only():
        t.check("a0", last, lab, "M-mode read of stimecmp matches the S-mode write")
    with t.rv32_only():
        t.check("a0", last & 0xFFFFFFFF, lab, "M-mode read of stimecmp matches the S-mode write")
        t.tsbi_csr("READ", "STIMECMPH")
        t.check("a0", last >> 32, lab, "M-mode read of stimecmph matches the S-mode write")
    v = t.rand(64)
    cmp_m(t, v, "random, written by M-mode")
    lab = t.label("sview")
    t.emit(f"{lab}:", 0)
    t.emit("csrr x7, stimecmp")
    with t.rv64_only():
        t.check("x7", v, lab, "S-mode read of stimecmp matches the M-mode write")
    with t.rv32_only():
        t.check("x7", v & 0xFFFFFFFF, lab, "S-mode read of stimecmp matches the M-mode write")
        t.emit("csrr x7, stimecmph")
        t.check("x7", v >> 32, lab, "S-mode read of stimecmph matches the M-mode write")
    teardown(t)
    tests.append(t)

    # ---- stce_bit_exist ----
    t = new("stce_bit_exist")
    t.describe(
        source=SSTC,
        rule_text="This extension adds the STCE bit to the menvcfg (<<sec:menvcfg>>) and henvcfg "
        "(<<sec:henvcfg>>) CSRs.",
        context="STCE is menvcfg bit 63 (menvcfgh bit 31 on RV32) and henvcfg bit 63 (henvcfgh bit 31). "
        "henvcfg.STCE is read-only zero while menvcfg.STCE=0 (menvcfg_stce_zero_op), so it is tested with "
        "menvcfg.STCE=1.",
        issues=f"{ISSUE}1312: writes to henvcfg.STCE while it is read-only zero are ignored; when "
        "it becomes writable again its value is UNSPECIFIED, so the test writes it before reading.",
        plan="1. menvcfg.STCE can be set and cleared by M-mode (T-SBI), read back each time.\n"
        "2. With H, from HS-mode with menvcfg.STCE=1: henvcfg.STCE can be set and cleared, read back.",
    )
    for on in (True, False, True, False):
        stce(t, on)
        lab = t.label("menvcfg")
        t.emit(f"{lab}:", 0)
        with t.rv64_only():
            t.tsbi_csr("READ", "MENVCFG")
            t.emit("srli a0, a0, 63")
        with t.rv32_only():
            t.tsbi_csr("READ", "MENVCFGH")
            t.emit("srli a0, a0, 31")
        t.check("a0", int(on), lab, f"menvcfg.STCE reads {int(on)} after M-mode {'set' if on else 'clear'}")
    with t.only_if(H):
        stce(t, True)
        for on in (True, False, True, False):
            lab = t.label("henvcfg")
            with t.rv64_only():
                t.li("x6", 1)
                t.emit("slli x6, x6, 63")
                t.emit(f"{lab}:", 0)
                t.emit(f"{'csrs' if on else 'csrc'} CSR_HENVCFG, x6")
                t.emit("csrr x7, CSR_HENVCFG")
                t.emit("srli x7, x7, 63")
            with t.rv32_only():
                t.li("x6", 0x80000000)
                t.emit(f"{lab}:", 0)
                t.emit(f"{'csrs' if on else 'csrc'} CSR_HENVCFGH, x6")
                t.emit("csrr x7, CSR_HENVCFGH")
                t.emit("srli x7, x7, 31")
            t.check("x7", int(on), lab, f"henvcfg.STCE reads {int(on)} after HS-mode {'set' if on else 'clear'}")
        with t.rv64_only():
            t.li("x6", 1)
            t.emit("slli x6, x6, 63")
            t.emit("csrc CSR_HENVCFG, x6")
        with t.rv32_only():
            t.li("x6", 0x80000000)
            t.emit("csrc CSR_HENVCFGH, x6")
        stce(t, False)
    tests.append(t)

    # ---- menvcfg_stce_exists ----
    t = new("menvcfg_stce_exists")
    t.describe(
        source=MAC,
        rule_text="The Sstc extension adds the STCE (STimecmp Enable) bit to menvcfg CSR.",
        context="STCE is menvcfg bit 63; on RV32 it is bit 31 of menvcfgh. Writing STCE must not disturb "
        "the other menvcfg fields, which hold their (legal) values when rewritten.",
        plan="1. Toggle STCE with each M-mode write form (csrrw of the old value with STCE flipped, csrrs, "
        "csrrc) and read it back.\n"
        "2. After each write, the other bits of menvcfg (and of menvcfg on RV32, where STCE is in "
        "menvcfgh) equal their values before the write.",
    )
    for op, on in (("WRITE", True), ("WRITE", False), ("SET", True), ("CLEAR", False)):
        csr, bit = ("MENVCFG", 63), ("MENVCFGH", 31)
        t.comment(f"{op} menvcfg.STCE = {int(on)}")
        lab = t.label("stce")
        for c, b, cond in ((csr[0], csr[1], "__riscv_xlen == 64"), (bit[0], bit[1], "__riscv_xlen == 32")):
            with t.only_if(cond):
                t.tsbi_csr("READ", c)
                t.emit("mv x9, a0")  # old value
                t.li("x6", 1)
                t.emit(f"slli x6, x6, {b}")
                if op == "WRITE":
                    t.emit("or a1, x9, x6" if on else "not a1, x6")
                    if not on:
                        t.emit("and a1, a1, x9")
                    t.tsbi_csr("WRITE", c, "a1")
                else:
                    t.tsbi_csr(op, c, "x6")
                t.emit(f"{lab}:", 0)
                t.tsbi_csr("READ", c)
                t.emit("mv x7, a0")
                t.emit(f"srli x7, x7, {b}")
                t.check("x7", int(on), lab, f"menvcfg.STCE reads {int(on)} after M-mode {op}")
                t.emit("xor x7, a0, x9")
                t.emit("not x6, x6")
                t.emit("and x7, x7, x6")
                t.check("x7", 0, lab, f"other bits of {c.lower()} unchanged by the STCE {op}")
    with t.rv32_only():
        t.tsbi_csr("READ", "MENVCFG")
        t.emit("mv x9, a0")
        stce(t, True)
        lab = t.label("low")
        t.emit(f"{lab}:", 0)
        t.tsbi_csr("READ", "MENVCFG")
        t.emit("sub x7, a0, x9")
        t.check("x7", 0, lab, "RV32: setting menvcfgh.STCE leaves menvcfg unchanged")
        stce(t, False)
    tests.append(t)

    # ---- menvcfg_stce_enable_op ----
    t = new("menvcfg_stce_enable_op")
    t.describe(
        source=MAC,
        rule_text="The STCE bit enables stimecmp for S-mode when set to one.",
        context="Enabling means S-mode CSR instructions on stimecmp execute normally (mcounteren.TM=1) and "
        "the stimecmp comparison drives STIP (mip_stip_reflects_stimecmp).",
        issues=ISSUE_1169,
        plan="1. STCE=0 then STCE=1 with TM=1: the same S-mode read traps, then succeeds.\n"
        "2. With STCE=1, every CSR instruction form on stimecmp in S-mode (csrrw with rd=x0 and rd!=x0, "
        "csrrs/csrrc with rs1=x0 and rs1!=x0, csrrwi, csrrsi with uimm=0, csrrci) returns the old value "
        "and leaves the value the form defines; on RV32 also on stimecmph.\n"
        "3. With STCE=1 the comparison drives sip.STIP: stimecmp=0 gives STIP=1, all ones gives 0.\n"
        "4. Enabling is for S-mode only: with STCE=1 and TM=1, U-mode reads and writes still raise "
        "illegal-instruction, with scounteren.TM at 1 and 0 (a counter enable must not leak to stimecmp).\n"
        "5. With STCE=0, M-mode sets mip.STIP=1 and stimecmp is all ones; after STCE is set, STIP settles "
        "to 0 because it now reflects the comparison.",
    )
    setup(t)
    stce(t, False)
    access(t, "S", "stimecmp", FORMS[0], "illegal", "STCE=0, before enabling")
    stce(t, True)
    access(t, "S", "stimecmp", FORMS[0], "ok", "STCE=1, after enabling")
    for csr, conds in (("stimecmp", None), ("stimecmph", "__riscv_xlen == 32")):

        def body(csr: str) -> None:
            for form in FORMS:
                old = X(t.rand(32), t.rand(64))
                rs = X(t.rand(32), t.rand(64))
                t.comment(f"{form[4]} on {csr}")
                lab = t.label(f"{csr}_form")
                if csr == "stimecmp":
                    with t.rv64_only():
                        t.load("x7", old.num(64), "old value")
                    with t.rv32_only():
                        t.load("x7", old.num(32), "old value")
                else:
                    t.load("x7", old.num(32), "old value")
                t.emit(f"csrw {csr}, x7")
                t.load("x6", rs, "rs1 value")
                t.emit(f"{lab}:", 0)
                t.emit(form[0].format(c=csr))
                r32, n32 = form_value(form, old.num(32), rs.num(32), 32)
                r64, n64 = form_value(form, old.num(64), rs.num(64), 64)
                if r32 is not None and r64 is not None:
                    t.check("x7", X(r32, r64), lab, f"{form[4]} of {csr} returns the old value")
                t.emit(f"csrr x7, {csr}")
                t.check("x7", X(n32, n64), lab, f"{form[4]} of {csr} leaves the defined value")

        if conds:
            with t.only_if(conds):
                body(csr)
        else:
            body(csr)
    cmp_s(t, 0, "zero")
    expect_stip(t, 1, "stimecmp=0 with STCE=1")
    cmp_s(t, MAX64, "all ones")
    expect_stip(t, 0, "stimecmp=all ones with STCE=1")
    t.comment("STCE enables stimecmp for S-mode only: U-mode access still raises illegal-instruction")
    for stm in (1, 0):
        t.li("x6", 2)
        t.emit(f"{'csrs' if stm else 'csrc'} scounteren, x6")
        uexp = "ok" if MUT == "u_access_leak" and stm else "illegal"
        access(t, "U", "stimecmp", FORMS[0], uexp, f"STCE=1, TM=1, scounteren.TM={stm}")
        access(t, "U", "stimecmp", FORMS[1], uexp, f"STCE=1, TM=1, scounteren.TM={stm}")
    t.comment("a software-set mip.STIP does not survive enabling: with stimecmp all ones STIP settles to 0")
    stce(t, False)
    cmp_m(t, MAX64, "all ones")
    mip_stip(t, True)
    expect_stip(t, 1, "M-mode set mip.STIP with STCE=0")
    stce(t, True)
    expect_stip(
        t, int(MUT == "sticky_stip"), "setting STCE=1 with stimecmp all ones (STIP now reflects the comparison)"
    )
    teardown(t)
    tests.append(t)

    # ---- menvcfg_stce_zero_op ----
    t = new("menvcfg_stce_zero_op")
    t.describe(
        source=MAC,
        rule_text="When this extension is implemented and STCE in menvcfg is zero, an attempt to access "
        "stimecmp or vstimecmp in a mode other than M-mode raises an illegal-instruction exception, STCE in "
        "henvcfg is read-only zero, and STIP in mip and sip reverts to its defined behavior as if this "
        "extension is not implemented.",
        context="Without Sstc, mip.STIP is writable by M-mode, which uses it to deliver supervisor timer "
        "interrupts (mip_stip_no_stimecmp_acc, mip_stip_no_stimecmp_mmode_write); sip.STIP is read-only.",
        issues=ISSUE_1636 + "\n" + ISSUE_3329 + f"\n{ISSUE}1312: writes to the read-only henvcfg.STCE are ignored.",
        plan="1. With STCE=0 and mcounteren.TM swept over 0 and 1: every CSR instruction form on stimecmp "
        "in S-mode raises illegal-instruction (xtval 0 or the instruction bits); on RV32 also stimecmph; "
        "reads and writes from U-mode do too.\n"
        "2. M-mode (T-SBI) accesses still work: a write of a random value reads back.\n"
        "3. STIP reverts: M-mode sets and clears mip.STIP, and sip.STIP follows, with stimecmp at 0 and "
        "at all ones (the comparison no longer drives STIP).\n"
        "4. The reverted STIP still drives interrupts: with sstatus.SIE=1 and sie.STIE=1, no interrupt "
        "while mip.STIP=0 and stimecmp=0; an interrupt once M-mode sets mip.STIP.\n"
        "5. sip.STIP stays read-only from S-mode with STCE=0: csrrs/csrrc of sip do not flip it.\n"
        "6. With H: henvcfg.STCE was 1 before menvcfg.STCE was cleared and must now read 0, and still reads "
        "0 after HS-mode tries to set it; HS-mode access to vstimecmp and VS-mode access to stimecmp "
        "(henvcfg/hcounteren enabled) raise illegal-instruction, not virtual-instruction.",
    )
    setup(t)
    cmp_s(t, 0, "zero (comparison true)")
    with t.only_if(H):
        t.comment("henvcfg.STCE=1 while menvcfg.STCE=1, so clearing menvcfg.STCE must mask a stored 1")
        h_guest_setup(t)
    stce(t, False)
    for tmv in (1, 0):
        tm(t, bool(tmv))
        t.load("x6", t.rand_x(), "rs1 value")
        for form in FORMS:
            access(t, "S", "stimecmp", form, "illegal", f"STCE=0, TM={tmv}")
        with t.rv32_only():
            for form in (FORMS[0], FORMS[2]):
                access(t, "S", "stimecmph", form, "illegal", f"STCE=0, TM={tmv}")
        for form in (FORMS[0], FORMS[1]):
            access(t, "U", "stimecmp", form, "illegal", f"STCE=0, TM={tmv}")
        with t.only_if(H):
            access(t, "S", "vstimecmp", FORMS[0], "illegal", f"STCE=0, TM={tmv}, HS-mode")
            if tmv:
                # menvcfg.STCE=0 denies VS-mode too, with illegal- (not virtual-) instruction
                access(
                    t,
                    "VS",
                    "stimecmp",
                    FORMS[0],
                    "virtual" if MUT == "vs_virtual_stce0" else "illegal",
                    "STCE=0, TM=1, hcounteren.TM=1",
                )
    tm(t, True)
    v = t.rand(64)
    cmp_m(t, v, "random, M-mode write with STCE=0")
    lab = t.label("mrw")
    t.emit(f"{lab}:", 0)
    t.tsbi_csr("READ", "STIMECMP")
    with t.rv64_only():
        t.check("a0", v, lab, "M-mode stimecmp read/write works with STCE=0")
    with t.rv32_only():
        t.check("a0", v & 0xFFFFFFFF, lab, "M-mode stimecmp read/write works with STCE=0")
        t.tsbi_csr("READ", "STIMECMPH")
        t.check("a0", v >> 32, lab, "M-mode stimecmph read/write works with STCE=0")
    for cmpv, note in ((0, "stimecmp=0"), (MAX64, "stimecmp=all ones")):
        cmp_m(t, cmpv, note)
        for on in (False, True, False):
            mip_stip(t, on)
            expect_mip_stip(t, int(on), f"M-mode writes mip.STIP={int(on)} with STCE=0, {note}")
            expect_stip(t, int(on), f"M-mode writes mip.STIP={int(on)} with STCE=0, {note}", settle=False)
            t.li("x6", STIP)
            t.emit(f"{'csrc' if on else 'csrs'} sip, x6")
            expect_stip(t, int(on), f"S-mode tries to flip read-only sip.STIP={int(on)} with STCE=0", settle=False)
    t.comment("interrupt delivery through the reverted mip.STIP")
    cmp_m(t, 0, "zero")
    mip_stip(t, False)
    for on in (False, True):
        if on:
            mip_stip(t, True)
        t.li("x6", STIP)
        t.emit("csrs sie, x6")
        lab = t.label("int" if on else "noint")
        t.li("x6", SIE)
        t.allow(1)
        t.emit(f"{lab}:", 0)
        t.emit("csrs sstatus, x6")
        poll_stip(t, 2, 50)  # a 50-iteration delay window
        t.emit("csrc sstatus, x6")
        t.li("x6", STIP)
        t.emit("csrc sie, x6")
        if on:
            t.outcome(
                STI, lab, "interrupt taken once M-mode sets mip.STIP with STCE=0 (STIE=SIE=1)", epc=False, origin="S"
            )
        else:
            t.outcome("ok", lab, "no interrupt with STCE=0, mip.STIP=0 and stimecmp=0 (STIE=SIE=1)")
    mip_stip(t, False)
    with t.only_if(H):
        lab0 = t.label("henvcfg_masked")
        t.emit(f"{lab0}:", 0)
        with t.rv64_only():
            t.emit("csrr x7, CSR_HENVCFG")
            t.emit("srli x7, x7, 63")
        with t.rv32_only():
            t.emit("csrr x7, CSR_HENVCFGH")
            t.emit("srli x7, x7, 31")
        t.check("x7", 0, lab0, "henvcfg.STCE reads 0 after menvcfg.STCE is cleared with henvcfg.STCE=1")
        lab = t.label("henvcfg")
        with t.rv64_only():
            t.li("x6", 1)
            t.emit("slli x6, x6, 63")
            t.emit(f"{lab}:", 0)
            t.emit("csrs CSR_HENVCFG, x6")
            t.emit("csrr x7, CSR_HENVCFG")
            t.emit("srli x7, x7, 63")
        with t.rv32_only():
            t.li("x6", 0x80000000)
            t.emit(f"{lab}:", 0)
            t.emit("csrs CSR_HENVCFGH, x6")
            t.emit("csrr x7, CSR_HENVCFGH")
            t.emit("srli x7, x7, 31")
        t.check("x7", 0, lab, "henvcfg.STCE is read-only zero while menvcfg.STCE=0 (after HS-mode set)")
    teardown(t)
    tests.append(t)

    # ---- stimecmp_stimecmph_sz_acc ----
    t = new("stimecmp_stimecmph_sz_acc", REQ_T)
    t.describe(
        source=SUP,
        rule_text="The stimecmp CSR is a 64-bit register and has 64-bit precision on all RV32 and RV64 "
        "systems. In RV32 only, accesses to the stimecmp CSR access the low 32 bits, while accesses to the "
        "stimecmph CSR access the high 32 bits of stimecmp.",
        context="stimecmph exists only on RV32, so on RV64 its address is not a CSR and accessing it raises "
        "illegal-instruction.",
        plan="1. RV64: random 64-bit values round-trip through stimecmp, and stimecmph raises "
        "illegal-instruction.\n"
        "2. RV32: writing stimecmp leaves stimecmph unchanged and vice versa (random values).\n"
        "3. The comparison uses all 64 bits: stimecmp = time + 2^32 and time + 2^33 (equal low halves, "
        "larger high half) gives STIP=0; then lowering only the high half (RV32: a stimecmph write; RV64: "
        "a full write with the same low half) gives STIP=1.\n"
        "4. Unsigned 64-bit comparison: stimecmp = 2^63 gives STIP=0.",
    )
    setup(t)
    with t.rv64_only():
        for _ in range(3):
            v = t.rand(64)
            cmp_s(t, v, "random")
            lab = t.label("rt")
            t.emit(f"{lab}:", 0)
            t.emit("csrr x7, stimecmp")
            t.check("x7", v, lab, "stimecmp keeps all 64 bits")
        access(t, "S", "stimecmph", FORMS[0], "illegal", "RV64 has no stimecmph")
    with t.rv32_only():
        for first, second in (("stimecmp", "stimecmph"), ("stimecmph", "stimecmp")):
            a, b, c = t.rand(32), t.rand(32), t.rand(32)
            t.load("x6", a, f"{first} value")
            t.emit(f"csrw {first}, x6")
            t.load("x6", b, f"{second} value")
            t.emit(f"csrw {second}, x6")
            t.load("x6", c, f"new {first} value")
            lab = t.label("half")
            t.emit(f"{lab}:", 0)
            t.emit(f"csrw {first}, x6")
            t.emit(f"csrr x7, {second}")
            t.check("x7", b, lab, f"writing {first} leaves {second} unchanged")
            t.emit(f"csrr x7, {first}")
            t.check("x7", c, lab, f"{first} holds its own write")
    for k in (1, 2):
        cmp_now(t, k)
        expect_stip(t, 0, f"stimecmp = time + {k}*2^32 (same low half as time)")
    t.comment("lower only the high half back to time's: stimecmp = time just read, now <= time")
    with t.rv64_only():
        t.emit("csrr x6, stimecmp")
        t.li("x7", 2)
        t.emit("slli x7, x7, 32")
        t.emit("sub x6, x6, x7")
        t.emit("csrw stimecmp, x6")
    with t.rv32_only():
        t.emit("csrr x6, stimecmph")
        t.emit("addi x6, x6, -2")
        t.emit("csrw stimecmph, x6")
    expect_stip(t, 1, "lowering only the high half of stimecmp to time's high half")
    cmp_s(t, 1 << 63, "2^63")
    expect_stip(t, 0, "stimecmp = 2^63 (unsigned comparison)")
    teardown(t)
    tests.append(t)

    # ---- mip_sip_stip_op ----
    t = new("mip_sip_stip_op", REQ_T)
    t.describe(
        source=SUP,
        rule_text="A supervisor timer interrupt becomes pending, as reflected in the STIP bit in the mip "
        "and sip registers whenever time contains a value greater than or equal to stimecmp, treating the "
        "values as unsigned integers. If the result of this comparison changes, it is guaranteed to be "
        "reflected in STIP eventually, but not necessarily immediately. The interrupt remains posted until "
        "stimecmp becomes greater than time, typically as a result of writing stimecmp. The interrupt will "
        "be taken based on the standard interrupt enable and delegation rules.",
        context="The test boots to S-mode, where mideleg.STIP=1 delegates STI to S. An S-level interrupt "
        "is taken in S-mode when sstatus.SIE=1 and sie.STIE=1, and always (if sie.STIE=1) in U-mode, "
        'which is less privileged. "Eventually" is handled by polling STIP a bounded number of times '
        "before each check.",
        issues=ISSUE_1169 + "\n" + ISSUE_2237,
        plan="1. Comparison sweep, checked in sip.STIP and mip.STIP (M-mode read): stimecmp = 0, = time "
        "(just read, so <= time), = time + 2^32, = time + 2^40, = 2^63 (unsigned: not pending), = all "
        "ones.\n"
        "2. Remains posted: with stimecmp=0, STIP stays 1 across a delay, across reads, and after the "
        "interrupt is taken; it clears only when stimecmp is written above time.\n"
        "3. Enable rules: in S-mode, (sstatus.SIE, sie.STIE) in {00, 01, 10, 11} with STI pending, and 11 "
        "with STI not pending; in U-mode, the same sweep with SIE set through SPIE before sret. Taken "
        "exactly when pending, STIE=1 and (SIE=1 or U-mode); scause = interrupt | 5.",
    )
    setup(t)
    sweep = [
        ("0", 1),
        ("now", 1),
        ("+2^32", int(MUT == "compare_32bit")),
        ("+2^40", 0),
        ("2^63", int(MUT == "signed_compare")),
        ("ones", 0),
    ]
    for name, exp in sweep:
        if name == "0":
            cmp_s(t, 0, "zero")
        elif name == "now":
            cmp_now(t, 0)
        elif name == "+2^32":
            cmp_now(t, 1)
        elif name == "+2^40":
            cmp_now(t, 256)
        elif name == "2^63":
            cmp_s(t, 1 << 63, "2^63")
        else:
            cmp_s(t, MAX64, "all ones")
        expect_stip(t, exp, f"stimecmp = {name}")
        expect_mip_stip(t, exp, f"stimecmp = {name}")
    t.comment("remains posted")
    cmp_s(t, 0, "zero")
    expect_stip(t, 1, "stimecmp = 0")
    expect_stip(t, 1, "stimecmp = 0, after a further delay", settle=False)
    interrupt_case(t, "S", 1, 1, 1)
    expect_stip(t, 1, "taking the interrupt (stimecmp still 0)", settle=False)
    cmp_s(t, MAX64, "all ones")
    expect_stip(t, 0, "writing stimecmp above time")
    for mode in ("S", "U"):
        for sie, stie in ((0, 0), (0, 1), (1, 0), (1, 1)):
            interrupt_case(t, mode, sie, stie, 1)
        interrupt_case(t, mode, 1, 1, 0)
    teardown(t)
    tests.append(t)

    # ---- mip_sip_stip_op, M-mode part: delegation ----
    t = TestFile(
        SUITE, "mip_sip_stip_op", suffix="_Sm", required=["I", "S", "Sstc", "Sm"], march=MARCH, boot="M", pool=POOL_TRAP
    )
    t.describe(
        source=SUP,
        rule_text="A supervisor timer interrupt becomes pending, as reflected in the STIP bit in the mip "
        "and sip registers whenever time contains a value greater than or equal to stimecmp, treating the "
        "values as unsigned integers. ... The interrupt will be taken based on the standard interrupt "
        "enable and delegation rules.",
        context="This file covers the delegation part of the rule, which needs M-mode to change mideleg; "
        "mip_sip_stip_op.S covers the rest from S-mode. It is separate so RVA23 certification, which "
        "excludes Sm tests, still runs the S-mode part. An interrupt delegated to S (mideleg.STIP=1) is "
        "never taken in M-mode. One that is not delegated is taken in M when mie.STIE=1 and either the "
        "hart is in M with mstatus.MIE=1 or the hart is in S or U (M-level interrupts are then always "
        "enabled).",
        plan="With STCE=1 and stimecmp=0 (STI pending), each case in a trap window:\n"
        "1. mideleg.STIP=1: in M-mode with MIE=1 and mie.STIE=1, no interrupt.\n"
        "2. mideleg.STIP=0: in M-mode, taken iff MIE=1 and mie.STIE=1 (sweep of both).\n"
        "3. mideleg.STIP=0: in S-mode with sstatus.SIE=0 and in U-mode, taken into M (mcause = interrupt "
        "| 5) when mie.STIE=1, and not taken when mie.STIE=0.\n"
        "mideleg and mie are restored at the end.",
    )
    t.comment("STCE=1, stimecmp=0 (STI pending), save mideleg in x9")
    with t.rv64_only():
        t.li("x6", 1)
        t.emit("slli x6, x6, 63")
        t.emit("csrs menvcfg, x6")
    with t.rv32_only():
        t.li("x6", 0x80000000)
        t.emit("csrs menvcfgh, x6")
    t.emit("csrw stimecmp, x0")
    with t.rv32_only():
        t.emit("csrw stimecmph, x0")
    t.emit("csrr x9, mideleg")
    STI_M = X((1 << 31) | 5, (1 << 63) | 5)

    def m_case(mode: str, deleg: int, mie: int, stie: int) -> None:
        taken = (not deleg) and stie and (mie or mode != "M")
        desc = f"{mode}-mode, mideleg.STIP={deleg}, mstatus.MIE={mie}, mie.STIE={stie}"
        t.comment(desc)
        t.li("x6", STIP)
        t.emit(f"{'csrs' if deleg else 'csrc'} mideleg, x6")
        t.emit(f"{'csrs' if stie else 'csrc'} mie, x6")
        t.li("x6", SIE)
        t.emit("csrc sstatus, x6")
        lab = t.label(f"m_{mode}")
        t.allow(1)
        if mode != "M":
            t.enter(mode)  # the interrupt can be taken on entry to S or U
        t.emit(f"{lab}:", 0)
        if mode == "M" and mie:
            t.li("x6", 0x8)  # mstatus.MIE
            t.emit("csrs mstatus, x6")
        loop = t.label("delay")
        t.li("x6", 50)
        t.emit(f"{loop}:", 0)
        t.emit("addi x6, x6, -1", 50)
        t.emit(f"bnez x6, {loop}", 50)
        if mode != "M":
            t.leave()
        t.li("x6", 0x8)
        t.emit("csrc mstatus, x6")
        t.li("x6", STIP)
        t.emit("csrc mie, x6")
        t.outcome(
            STI_M if taken else "ok",
            lab,
            f"{desc}: STI {'must' if taken else 'must not'} be taken in M-mode",
            epc=False,
            origin=mode,
        )

    m_case("M", 1, 1, 1)
    for mie in (0, 1):
        for stie in (0, 1):
            m_case("M", 0, mie, stie)
    for mode in ("S", "U"):
        for stie in (0, 1):
            m_case(mode, 0, 0, stie)
    t.emit("csrw mideleg, x9")
    t.li("x6", -1)
    t.emit("csrw stimecmp, x6")
    with t.rv32_only():
        t.emit("csrw stimecmph, x6")
    tests.append(t)

    # ---- sip_stip_sie_stie ----
    t = new("sip_stip_sie_stie")
    t.describe(
        source=SUP,
        rule_text="Bits sip.STIP and sie.STIE are the interrupt-pending and interrupt-enable bits for "
        "supervisor-level timer interrupts. If implemented, STIP is read-only in sip. When the Sstc "
        "extension is not implemented, STIP is set and cleared by the execution environment. When the Sstc "
        "extension is implemented, STIP reflects the timer interrupt signal resulting from stimecmp. The "
        "sip.STIP bit, in response to timer interrupts generated by stimecmp, is set by writing stimecmp "
        "with a value that is less than or equal to time, and is cleared by writing stimecmp with a value "
        "greater than time.",
        context="With Sstc and STCE=1, sie.STIE must be writable because STI can become pending (sie_acc).",
        issues=ISSUE_2237,
        plan="1. sip.STIP is read-only from S-mode: csrrs, csrrc and csrrw of sip that try to flip STIP "
        "leave it unchanged, with STIP at 0 (stimecmp all ones) and at 1 (stimecmp 0).\n"
        "2. sie.STIE is writable: set and cleared, read back, without changing sip.STIP.\n"
        "3. Alternating writes of stimecmp = 0 and all ones set and clear sip.STIP each time.",
    )
    setup(t)
    for cmpv, cur in ((MAX64, 0), (0, 1)):
        cmp_s(t, cmpv, "all ones" if cur == 0 else "zero")
        expect_stip(t, cur, "stimecmp " + ("all ones" if cur == 0 else "0"))
        for op in ("csrs", "csrc", "csrw"):
            t.li("x6", STIP if (op != "csrw" or not cur) else 0)
            lab = t.label("sipwr")
            t.emit(f"{lab}:", 0)
            t.emit(f"{op} sip, x6")
            expect_stip(t, cur, f"S-mode {op} sip trying to flip STIP from {cur}", settle=False)
    for on in (1, 0, 1, 0):
        t.li("x6", STIP)
        lab = t.label("stie")
        t.emit(f"{lab}:", 0)
        t.emit(f"{'csrs' if on else 'csrc'} sie, x6")
        t.emit("csrr x7, sie")
        t.emit(f"andi x7, x7, {STIP}")
        t.check("x7", STIP * on, lab, f"sie.STIE reads {on}")
        expect_stip(t, 1, f"sie.STIE={on} (stimecmp still 0)", settle=False)
    for i in range(3):
        cmp_s(t, MAX64, "all ones")
        expect_stip(t, 0, f"write {i}: stimecmp all ones")
        cmp_s(t, 0, "zero")
        expect_stip(t, 1, f"write {i}: stimecmp 0")
    teardown(t)
    tests.append(t)

    # ---- mip_stip_stimecmp_acc ----
    t = new("mip_stip_stimecmp_acc")
    t.describe(
        source=MAC,
        rule_text="If the stimecmp (supervisor-mode timer compare) register is implemented, STIP is read-only in mip",
        context="This applies while menvcfg.STCE=1; with STCE=0, STIP reverts to being writable in mip "
        "(menvcfg_stce_zero_op).",
        plan="With STCE=1 and STIP at 0 (stimecmp all ones) and then at 1 (stimecmp 0), M-mode (T-SBI) "
        "tries to flip mip.STIP with csrrs, csrrc and csrrw (the read value with STIP inverted). After each "
        "write mip.STIP (M-mode read) and sip.STIP are unchanged.",
    )
    setup(t)
    for cmpv, cur in ((MAX64, 0), (0, 1)):
        cmp_s(t, cmpv, "all ones" if cur == 0 else "zero")
        expect_stip(t, cur, "stimecmp " + ("all ones" if cur == 0 else "0"))
        for op in ("SET", "CLEAR", "WRITE"):
            if op == "WRITE":
                t.tsbi_csr("READ", "MIP")
                t.emit(f"xori a1, a0, {STIP}")
                t.tsbi_csr("WRITE", "MIP", "a1")
            else:
                t.tsbi_csr(op, "MIP", imm=STIP)
            if MUT == "mip_stip_writable" and op == "SET":
                cur = 1
            expect_mip_stip(t, cur, f"M-mode {op} of mip.STIP with STIP={cur}")
            expect_stip(t, cur, f"M-mode {op} of mip.STIP with STIP={cur}", settle=False)
    teardown(t)
    tests.append(t)

    # ---- mip_stip_reflects_stimecmp ----
    t = new("mip_stip_reflects_stimecmp", REQ_T)
    t.describe(
        source=MAC,
        rule_text="[STIP in mip] reflects the supervisor-level timer interrupt signal resulting from stimecmp.",
        plan="1. mip.STIP (M-mode read through T-SBI) tracks the comparison for stimecmp written by M-mode "
        "(0, all ones, 2^63) and by S-mode (time, time + 2^32, 0, all ones), polling sip.STIP first so "
        "the change has propagated.\n"
        "2. The signal is the stimecmp one, not the machine timer's: with mtimecmp all ones, stimecmp=0 "
        "leaves MTIP 0; with mtimecmp=0, stimecmp all ones leaves STIP 0. mtimecmp is written through T-SBI "
        "stores to RVMODEL_MTIMECMP_ADDRESS (DUT configuration), and mie.MTIE is cleared first.",
    )
    setup(t)
    for who, name, exp in (
        ("M", "0", 1),
        ("M", "ones", 0),
        ("M", "0", 1),
        ("M", "2^63", 0),
        ("S", "now", 1),
        ("S", "+2^32", 0),
        ("S", "0", 1),
        ("S", "ones", 0),
    ):
        val = {"0": 0, "ones": MAX64, "2^63": 1 << 63}.get(name, 0)  # "now" and "+2^32" read time
        if who == "M":
            cmp_m(t, val, name)
        elif name == "now":
            cmp_now(t, 0)
        elif name == "+2^32":
            cmp_now(t, 1)
        else:
            cmp_s(t, val, name)
        poll_stip(t, exp)
        expect_mip_stip(t, exp, f"{who}-mode write stimecmp = {name}")
    with t.only_if("defined(RVMODEL_MTIMECMP_ADDRESS)"):
        t.comment("the two timers do not cross: mtimecmp all ones keeps MTIP 0 when stimecmp=0, and")
        t.comment("mtimecmp=0 (MTIP=1, mie.MTIE=0) does not set STIP when stimecmp is all ones")
        t.tsbi_csr("CLEAR", "MIE", imm=0x80)
        mtimecmp(t, MAX64)
        cmp_s(t, 0, "zero")
        poll_stip(t, 1)
        lab = t.label("mtip")
        t.emit(f"{lab}:", 0)
        t.tsbi_csr("READ", "MIP")
        t.emit("andi a0, a0, 0x80")
        t.check("a0", 0, lab, "mip.MTIP stays 0 with mtimecmp all ones while stimecmp=0 (STIP=1)")
        cmp_s(t, MAX64, "all ones")
        mtimecmp(t, 0)
        expect_stip(t, 0, "mtimecmp=0 with stimecmp all ones", settle=False)
        expect_mip_stip(t, 0, "mtimecmp=0 with stimecmp all ones")
        mtimecmp(t, MAX64)
    teardown(t)
    tests.append(t)

    # ---- mip_stip_stimecmp_clr ----
    t = new("mip_stip_stimecmp_clr", REQ_T)
    t.describe(
        source=MAC,
        rule_text="This timer interrupt signal is cleared by writing stimecmp with a value greater than "
        "the current time value.",
        plan="1. From STIP=1 (stimecmp=0), write stimecmp above time and check STIP clears in sip and mip: "
        "time + 2^32 and time + 2^40 (S-mode writes), 2^63 and all ones (M-mode writes). On RV32, also "
        "clear by writing only stimecmph above time's high half.\n"
        "2. Negatives: rewriting 0 or the current time does not clear STIP.",
    )
    setup(t)
    for how in ("+2^32", "+2^40", "M 2^63", "M ones", "rv32 high"):
        cmp_s(t, 0, "zero")
        expect_stip(t, 1, "stimecmp = 0")
        if how == "+2^32":
            cmp_now(t, 1)
        elif how == "+2^40":
            cmp_now(t, 256)
        elif how == "M 2^63":
            cmp_m(t, 1 << 63, "2^63")
        elif how == "M ones":
            cmp_m(t, MAX64, "all ones")
        else:
            with t.rv32_only():
                t.emit("csrr x6, timeh")
                t.emit("addi x6, x6, 1")
                t.emit("csrw stimecmph, x6")
            with t.rv64_only():
                cmp_now(t, 1)
        expect_stip(t, 0, f"writing stimecmp {how}")
        expect_mip_stip(t, 0, f"writing stimecmp {how}")
    cmp_s(t, 0, "zero")
    expect_stip(t, 1, "stimecmp = 0")
    cmp_s(t, 0, "zero again")
    expect_stip(t, 1, "rewriting stimecmp = 0", settle=False)
    cmp_now(t, 0)
    expect_stip(t, 1, "writing stimecmp = time (not greater)", settle=False)
    teardown(t)
    tests.append(t)

    # ---- mcounteren_tm_clr ----
    t = new("mcounteren_tm_clr")
    t.describe(
        source=MAC,
        rule_text="when the TM bit in the mcounteren register is clear, attempts to access the stimecmp or "
        "vstimecmp register while executing in a mode less privileged than M will cause an "
        "illegal-instruction exception.",
        context="This holds even with menvcfg.STCE=1. TM gates access only; the timer comparison keeps "
        "driving STIP. TM=0 also blocks the time CSR below M-mode (Zicntr), so this test does not read time.",
        plan="1. With STCE=1 and TM=0: every CSR instruction form on stimecmp in S-mode raises "
        "illegal-instruction (xtval 0 or the instruction bits); on RV32 also stimecmph; U-mode read and "
        "write too; with H, HS-mode access to vstimecmp, and VS-mode access with henvcfg.STCE=1 and "
        "hcounteren.TM=1 (illegal-instruction, not virtual-instruction).\n"
        "2. M-mode (T-SBI) accesses still work.\n"
        "3. Negative dependency: with TM=0, M-mode writes of stimecmp = 0 and all ones still set and clear "
        "sip.STIP.\n"
        "4. Setting TM=1 again makes the S-mode read succeed.",
    )
    setup(t)
    tm(t, False)
    t.load("x6", t.rand_x(), "rs1 value")
    for form in FORMS:
        access(t, "S", "stimecmp", form, "ok" if MUT == "tm_ignored" else "illegal", "STCE=1, TM=0")
    with t.rv32_only():
        for form in (FORMS[0], FORMS[2]):
            access(t, "S", "stimecmph", form, "illegal", "STCE=1, TM=0")
    for form in (FORMS[0], FORMS[1]):
        access(t, "U", "stimecmp", form, "illegal", "STCE=1, TM=0")
    with t.only_if(H):
        access(t, "S", "vstimecmp", FORMS[0], "illegal", "STCE=1, TM=0, HS-mode")
        h_guest_setup(t)
        access(t, "VS", "stimecmp", FORMS[0], "illegal", "STCE=1, TM=0, henvcfg.STCE=1, hcounteren.TM=1")
    v = t.rand(64)
    cmp_m(t, v, "random, M-mode write with TM=0")
    lab = t.label("mrw")
    t.emit(f"{lab}:", 0)
    t.tsbi_csr("READ", "STIMECMP")
    with t.rv64_only():
        t.check("a0", v, lab, "M-mode stimecmp read/write works with TM=0")
    with t.rv32_only():
        t.check("a0", v & 0xFFFFFFFF, lab, "M-mode stimecmp read/write works with TM=0")
    cmp_m(t, 0, "zero")
    expect_stip(t, 1, "M-mode stimecmp = 0 with TM=0")
    cmp_m(t, MAX64, "all ones")
    expect_stip(t, 0, "M-mode stimecmp = all ones with TM=0")
    tm(t, True)
    access(t, "S", "stimecmp", FORMS[0], "ok", "TM set again")
    teardown(t)
    tests.append(t)

    # ---- mcounteren_tm_set ----
    t = new("mcounteren_tm_set")
    t.describe(
        source=MAC,
        rule_text="When this bit is set, access to the stimecmp or vstimecmp register is permitted in "
        "S-mode if implemented, and access to the vstimecmp register (via stimecmp) is permitted in VS-mode "
        "if implemented and not otherwise prevented by the TM bit in hcounteren.",
        context='"Permitted" still requires menvcfg.STCE=1 (menvcfg_stce_zero_op). VS-mode access is '
        "also gated by henvcfg.STCE and hcounteren.TM; this test sets both.",
        issues=ISSUE_1985,
        plan="1. TM=0 then TM=1 (STCE=1): the S-mode read traps, then every CSR instruction form on "
        "stimecmp succeeds; on RV32 also stimecmph.\n"
        "2. With H: HS-mode access to vstimecmp succeeds; with henvcfg.STCE=1 and hcounteren.TM=1, VS-mode "
        "reads and writes of stimecmp succeed, and the write lands in vstimecmp, not stimecmp.\n"
        "3. Permission is for S-mode only: U-mode reads still raise illegal-instruction, with scounteren.TM "
        "at 1 and 0.",
    )
    setup(t)
    tm(t, False)
    access(t, "S", "stimecmp", FORMS[0], "illegal", "TM=0")
    tm(t, True)
    t.load("x6", t.rand_x(), "rs1 value")
    for form in FORMS:
        access(t, "S", "stimecmp", form, "ok", "STCE=1, TM=1")
    with t.rv32_only():
        for form in (FORMS[0], FORMS[2]):
            access(t, "S", "stimecmph", form, "ok", "STCE=1, TM=1")
    with t.only_if(H):
        access(t, "S", "vstimecmp", FORMS[0], "ok", "STCE=1, TM=1, HS-mode")
        t.comment("henvcfg.STCE=1, hcounteren.TM=1")
        h_guest_setup(t)
        sv, gv = t.rand(64), X(t.rand(32), t.rand(64))
        cmp_s(t, sv, "stimecmp value seen by HS-mode")
        t.load("x6", gv, "value VS-mode writes through stimecmp")
        lab = access(t, "VS", "stimecmp", FORMS[1], "ok", "STCE=1, TM=1, henvcfg.STCE=1, hcounteren.TM=1")
        t.emit("csrr x7, CSR_VSTIMECMP")
        with t.rv64_only():
            t.check("x7", gv.num(64), lab, "a VS-mode write of stimecmp lands in vstimecmp")
            t.emit("csrr x7, stimecmp")
            t.check("x7", sv, lab, "a VS-mode write of stimecmp leaves the HS stimecmp unchanged")
        with t.rv32_only():
            t.check("x7", gv.num(32), lab, "a VS-mode write of stimecmp lands in vstimecmp")
            t.emit("csrr x7, stimecmp")
            t.check("x7", sv & 0xFFFFFFFF, lab, "a VS-mode write of stimecmp leaves the HS stimecmp unchanged")
        access(t, "VS", "stimecmp", FORMS[0], "ok", "STCE=1, TM=1, henvcfg.STCE=1, hcounteren.TM=1")
    for stm in (1, 0):
        t.li("x7", 2)
        t.emit(f"{'csrs' if stm else 'csrc'} scounteren, x7")
        access(t, "U", "stimecmp", FORMS[0], "illegal", f"STCE=1, TM=1, scounteren.TM={stm}: S-mode only")
    teardown(t)
    tests.append(t)

    tests += gen_vs()
    return tests


# ---------------------------------------------------------------- VS level (H)
REQ_H = ["I", "S", "H", "Sstc"]
REQ_HT = ["I", "S", "H", "Sstc", "Zicntr"]  # VS-level tests that read time
HYP = "src/priv/hypervisor.adoc"
VSTIP = 0x40  # hip/mip/hvip/hie/hideleg bit 6
VSTI_HS = X((1 << 31) | 6, (1 << 63) | 6)  # VS-level timer interrupt taken in HS-mode
ISSUE_2040 = (
    f"{ISSUE}2040: VS-mode reaches vstimecmp only through the stimecmp address; hcounteren.TM gates that "
    "access, and vstimecmp's own address is not accessible from V=1 (radimkrcmar: \"vstimecmp CSR access in VS "
    'mode is not affected by the TM bit").'
)
ISSUE_1898 = (
    f"{ISSUE}1898: with mcounteren.TM=0, a VS-mode stimecmp access raises illegal-instruction, not "
    "virtual-instruction: the virtual-instruction rule covers instructions disabled by a supervisor or "
    'hypervisor CSR, "which clearly does not apply to an instruction being disabled by a machine CSR such as '
    'mcounteren" (gfavor).'
)
ISSUE_1636_VS = (
    f"{ISSUE}1636: when STCE changes, the timer-driven pending bit takes an UNSPECIFIED value until it is "
    "written; tests write hvip.VSTIP after changing STCE before relying on hip.VSTIP."
)
HTM_WARL = (
    "hcounteren bits may be read-only zero (hcounteren_warl). Tests set hcounteren.TM, read it back, and where it "
    "reads 0 expect VS-mode accesses to raise virtual-instruction instead."
)


def henv_stce(t: TestFile, on: bool) -> None:
    t.comment(f"henvcfg.STCE = {int(on)}")
    op = "csrs" if on else "csrc"
    with t.rv64_only():
        t.li("x7", 1)
        t.emit("slli x7, x7, 63")
        t.emit(f"{op} CSR_HENVCFG, x7")
    with t.rv32_only():
        t.li("x7", 0x80000000)
        t.emit(f"{op} CSR_HENVCFGH, x7")


def hbit(t: TestFile, csr: str, bit: int, on: bool, name: str) -> None:
    t.comment(f"{name} = {int(on)}")
    t.li("x7", bit)
    t.emit(f"{'csrs' if on else 'csrc'} {csr}, x7")


def htm(t: TestFile, on: bool) -> None:
    hbit(t, "CSR_HCOUNTEREN", 2, on, "hcounteren.TM")


def htm_probe(t: TestFile) -> None:
    """Set hcounteren.TM and leave its read-back value in x1: 2, or 0 if it is read-only zero."""
    htm(t, True)
    t.emit("csrr x1, CSR_HCOUNTEREN")
    t.emit("andi x1, x1, 2")


def hvip(t: TestFile, on: bool) -> None:
    hbit(t, "CSR_HVIP", VSTIP, on, "hvip.VSTIP")


def hideleg(t: TestFile, on: bool) -> None:
    hbit(t, "CSR_HIDELEG", VSTIP, on, "hideleg[6] (VS-level timer interrupt delegated to VS)")


def hie(t: TestFile, on: bool) -> None:
    """Set or clear hie.VSTIE. Setting it first clears sstatus.SIE: an sret into VS or VU copies SPIE (1) into
    HS-mode's SIE, and HS-mode must take the interrupt only inside a window that sets SIE itself."""
    if on:
        t.li("x7", SIE)
        t.emit("csrc sstatus, x7")
    hbit(t, "CSR_HIE", VSTIP, on, "hie.VSTIE")


def wr64(t: TestFile, lo: str, hi: str, v: int, note: str) -> None:
    """HS-mode write of a 64-bit constant to a CSR (lo) and, on RV32, its high half (hi), high half first."""
    with t.rv64_only():
        t.load("x6", v, note)
        t.emit(f"csrw {lo}, x6")
    with t.rv32_only():
        t.load("x6", v >> 32, f"{note} (high half)")
        t.emit(f"csrw {hi}, x6")
        t.load("x6", v & 0xFFFFFFFF, f"{note} (low half)")
        t.emit(f"csrw {lo}, x6")


def vcmp(t: TestFile, v: int, note: str) -> None:
    wr64(t, "CSR_VSTIMECMP", "CSR_VSTIMECMPH", v, f"vstimecmp = {note}")


def htd(t: TestFile, v: int, note: str) -> None:
    wr64(t, "CSR_HTIMEDELTA", "CSR_HTIMEDELTAH", v, f"htimedelta = {note}")


def vcmp_now(t: TestFile, k: int, delta: bool = True) -> None:
    """HS-mode write vstimecmp = time (+ htimedelta when delta) + k*2^32, truncated to 64 bits; k is a small
    signed integer. The time read order makes k <= 0 never in the future and k > 0 always in the future."""
    t.comment(f"vstimecmp = time{' + htimedelta' if delta else ''} + {k}*2^32")
    with t.rv64_only():
        t.emit("csrr x6, time")
        if delta:
            t.emit("csrr x7, CSR_HTIMEDELTA")
            t.emit("add x6, x6, x7")
        if k:
            t.li("x7", k)
            t.emit("slli x7, x7, 32")
            t.emit("add x6, x6, x7")
        t.emit("csrw CSR_VSTIMECMP, x6")
    with t.rv32_only():
        if k > 0:
            t.emit("csrr x7, time")
            t.emit("csrr x6, timeh")
        else:
            t.emit("csrr x6, timeh")
            t.emit("csrr x7, time")
        if delta:
            t.emit("csrr x8, CSR_HTIMEDELTA")
            t.emit("add x7, x7, x8")
            t.emit("sltu x8, x7, x8")  # carry out of the low half
            t.emit("add x6, x6, x8")
            t.emit("csrr x8, CSR_HTIMEDELTAH")
            t.emit("add x6, x6, x8")
        if k:
            t.emit(f"addi x6, x6, {k}")
        t.emit("csrw CSR_VSTIMECMPH, x6")
        t.emit("csrw CSR_VSTIMECMP, x7")


def poll_vstip(t: TestFile, until: int, n: int = 500) -> None:
    """Read hip.VSTIP into x8 until it equals `until` or n reads pass (bounded wait, no checks inside)."""
    loop, done = t.label("wait"), t.label("waitdone")
    t.li("x9", n)
    t.emit(f"{loop}:", 0)
    t.emit("csrr x8, CSR_HIP", n)
    t.emit(f"andi x8, x8, {VSTIP}", n)
    t.emit(f"{'bnez' if until else 'beqz'} x8, {done}", n)
    t.emit("addi x9, x9, -1", n)
    t.emit(f"bnez x9, {loop}", n)
    t.emit(f"{done}:", 0)


def expect_vstip(t: TestFile, value: int, desc: str, settle: bool = True, mview: bool = True) -> None:
    """Check hip.VSTIP (awaiting a change, or watching a steady value) and, when mview, mip.VSTIP read in
    M-mode, which aliases it."""
    lab = t.label("vstip")
    poll_vstip(t, until=value if settle else 1 - value, n=500 if settle else 50)
    t.emit(f"{lab}:", 0)
    t.check("x8", VSTIP if value else 0, lab, f"hip.VSTIP after {desc}")
    if mview:
        t.tsbi_csr("READ", "MIP")
        t.emit(f"andi a0, a0, {VSTIP}")
        t.check("a0", VSTIP if value else 0, lab, f"mip.VSTIP (M-mode read) after {desc}")


def vsetup(t: TestFile) -> None:
    setup(t)
    t.comment(
        "VS setup: henvcfg.STCE=1, hcounteren.TM=1, htimedelta=0, vstimecmp all ones, hvip.VSTIP=0, "
        "hie.VSTIE=0, hideleg[6]=0"
    )
    henv_stce(t, True)
    htm(t, True)
    htd(t, 0, "0")
    vcmp(t, MAX64, "all ones")
    hvip(t, False)
    hie(t, False)
    hideleg(t, False)
    t.blank()


def vteardown(t: TestFile) -> None:
    t.blank()
    t.comment("VS teardown")
    hie(t, False)
    hideleg(t, False)
    hvip(t, False)
    t.li("x6", SIE)
    t.emit("csrc CSR_VSSTATUS, x6")
    vcmp(t, MAX64, "all ones")
    htd(t, 0, "0")
    henv_stce(t, False)
    teardown(t)


def delay_window(t: TestFile, mode: str, expect: Expect, desc: str) -> str:
    """A trap window that enters `mode` (from HS) and waits 50 iterations there, for interrupt checks."""
    lab = t.label(f"int{mode}")
    t.allow(1)
    if mode != "S":
        t.enter(mode)
    t.emit(f"{lab}:", 0)
    loop = t.label("delay")
    t.li("x9", 50)
    t.emit(f"{loop}:", 0)
    t.emit("addi x9, x9, -1", 50)
    t.emit(f"bnez x9, {loop}", 50)
    if mode != "S":
        t.leave()
    t.outcome(expect, lab, desc, epc=False, origin=mode)
    return lab


def vs_int_case(t: TestFile, deleg: int, mode: str, sie: int, vstie: int, pending: int) -> None:
    """VS-level timer interrupt from vstimecmp (hvip.VSTIP=0) in `mode` (VS, VU or S for HS-mode), with
    hideleg[6] = deleg already set. sie is vsstatus.SIE for VS/VU and sstatus.SIE for HS."""
    if deleg:
        taken = pending and vstie and (mode == "VU" or (mode == "VS" and (sie or MUT == "vsti_ignores_vs_sie")))
    else:
        taken = pending and vstie and (mode != "S" or sie)
    where = {"S": "HS"}.get(mode, mode)
    sreg = "sstatus" if mode == "S" else "vsstatus"
    desc = f"{where}-mode, hideleg[6]={deleg}, {sreg}.SIE={sie}, hie.VSTIE={vstie}, VSTIP pending={pending}"
    t.comment(desc)
    vcmp(t, 0 if pending else MAX64, "0 (pending)" if pending else "all ones (not pending)")
    if pending:
        poll_vstip(t, 1)
    hie(t, bool(vstie))
    t.li("x6", SIE)
    if mode == "S":
        lab = t.label("intHS")
        t.allow(1)
        t.emit(f"{lab}:", 0)
        if sie:
            t.emit("csrs sstatus, x6")
        poll_vstip(t, 2, 50)  # a 50-iteration delay
        t.emit("csrc sstatus, x6")
        t.outcome(
            VSTI_HS if taken else "ok",
            lab,
            f"{desc}: VS-level timer interrupt {'must' if taken else 'must not'} be taken",
            epc=False,
            origin="S",
        )
    else:
        t.emit(f"{'csrs' if sie else 'csrc'} CSR_VSSTATUS, x6")
        lab = delay_window(
            t,
            mode,
            (STI if deleg else VSTI_HS) if taken else "ok",
            f"{desc}: VS-level timer interrupt {'must' if taken else 'must not'} be taken",
        )
        t.emit("csrc CSR_VSSTATUS, x6")
    if taken:
        t.emit("AI_LOG(x15, TRAPLOG_VECT)", 10)
        t.emit("andi x15, x15, 3")
        t.check(
            "x15", 2 if deleg else 1, lab, f"{desc}: taken in {'VS' if deleg else 'HS'}-mode (handler mode 2 VS, 1 HS)"
        )
    hie(t, False)


def vs_forms(t: TestFile, csr: str) -> None:
    """Every CSR instruction form on stimecmp (or stimecmph) in VS-mode, which operates on vstimecmp (or
    vstimecmph): returns the old value and leaves the value the form defines."""
    hcsr = {"stimecmp": "CSR_VSTIMECMP", "stimecmph": "CSR_VSTIMECMPH"}[csr]
    for form in FORMS:
        old = X(t.rand(32), t.rand(64))
        rs = X(t.rand(32), t.rand(64))
        t.comment(f"{form[4]} on {csr} in VS-mode")
        if csr == "stimecmp":
            with t.rv64_only():
                t.load("x7", old.num(64), "old vstimecmp")
            with t.rv32_only():
                t.load("x7", old.num(32), "old vstimecmp")
        else:
            t.load("x7", old.num(32), "old vstimecmph")
        t.emit(f"csrw {hcsr}, x7")
        t.load("x6", rs, "rs1 value")
        lab = access(t, "VS", csr, form, "ok", "henvcfg.STCE=1, hcounteren.TM=1")
        r32, n32 = form_value(form, old.num(32), rs.num(32), 32)
        r64, n64 = form_value(form, old.num(64), rs.num(64), 64)
        if r32 is not None and r64 is not None:
            t.check("x7", X(r32, r64), lab, f"{form[4]} of {csr} in VS-mode returns the old vstimecmp value")
        t.emit(f"csrr x7, {hcsr}")
        t.check("x7", X(n32, n64), lab, f"{form[4]} of {csr} in VS-mode leaves the defined value in vstimecmp")


def gen_vs() -> list[TestFile]:
    tests = []

    # ---- vstimecmp_exist ----
    t = new("vstimecmp_exist", REQ_H)
    t.describe(
        source=SSTC,
        rule_text="This extension adds the S-level stimecmp CSR (<<stimecmp>>) and the VS-level vstimecmp CSR "
        "(<<vstimecmp>>).",
        context="This file covers the VS-level CSR (stimecmp_exist covers stimecmp). vstimecmp (0x24D, and "
        "vstimecmph 0x25D on RV32) is an HS-mode CSR; VS-mode reaches it through the stimecmp address. The test "
        "sets every gate: menvcfg.STCE, mcounteren.TM, henvcfg.STCE and hcounteren.TM.",
        issues=ISSUE_1169 + "\n" + ISSUE_2040 + "\n" + HTM_WARL,
        plan="1. HS-mode reads and writes vstimecmp (and vstimecmph on RV32) without a trap.\n"
        "2. Round trip from HS-mode: 0, all ones, 2^63 and two random 64-bit values.\n"
        "3. VS-mode's stimecmp is vstimecmp: a VS-mode read of stimecmp returns what HS-mode wrote to "
        "vstimecmp, a VS-mode write lands in vstimecmp, and HS-mode's stimecmp is unchanged.\n"
        "4. vstimecmp's own address raises virtual-instruction from VS and VU (and vstimecmph from VS on RV32).",
    )
    vsetup(t)
    access(t, "S", "vstimecmp", FORMS[0], "ok", "HS-mode")
    t.emit("li x6, 0")
    access(t, "S", "vstimecmp", FORMS[1], "ok", "HS-mode")
    with t.rv32_only():
        access(t, "S", "vstimecmph", FORMS[0], "ok", "HS-mode")
    for v, note in [(0, "zero"), (MAX64, "all ones"), (1 << 63, "2^63")] + [(t.rand(64), "random") for _ in range(2)]:
        vcmp(t, v, note)
        lab = t.label("rt")
        t.emit(f"{lab}:", 0)
        t.emit("csrr x7, CSR_VSTIMECMP")
        t.check("x7", X(v & 0xFFFFFFFF, v), lab, f"vstimecmp round trip ({note})")
        with t.rv32_only():
            t.emit("csrr x7, CSR_VSTIMECMPH")
            t.check("x7", v >> 32, lab, f"vstimecmph round trip ({note})")
    sv, hv, gv = t.rand(64), t.rand(64), X(t.rand(32), t.rand(64))
    cmp_s(t, sv, "HS-mode stimecmp")
    vcmp(t, hv, "value VS-mode reads through stimecmp")
    htm_probe(t)

    def vs_view() -> None:
        lab = access(t, "VS", "stimecmp", FORMS[0], "ok", "all gates set")
        t.check("x7", X(hv & 0xFFFFFFFF, hv), lab, "VS-mode reads vstimecmp through stimecmp")
        t.load("x6", gv, "value VS-mode writes through stimecmp")
        lab = access(t, "VS", "stimecmp", FORMS[1], "ok", "all gates set")
        t.emit("csrr x7, CSR_VSTIMECMP")
        t.check("x7", gv, lab, "a VS-mode write of stimecmp lands in vstimecmp")
        t.emit("csrr x7, stimecmp")
        t.check("x7", X(sv & 0xFFFFFFFF, sv), lab, "a VS-mode write of stimecmp leaves HS-mode's stimecmp")

    t.either("x1", vs_view, lambda: access(t, "VS", "stimecmp", FORMS[0], "virtual", "hcounteren.TM read-only zero"))
    direct = "ok" if MUT == "vs_direct_vstimecmp_ok" else "virtual"
    for mode in ("VS", "VU"):
        access(t, mode, "vstimecmp", FORMS[0], direct, "vstimecmp's own address from V=1")
    with t.rv32_only():
        access(t, "VS", "vstimecmph", FORMS[0], "virtual", "vstimecmph's own address from V=1")
    vteardown(t)
    tests.append(t)

    # ---- vstimecmp_sz ----
    t = new("vstimecmp_sz", REQ_HT)
    t.describe(
        source=HYP,
        rule_text="The vstimecmp CSR is a 64-bit register and has 64-bit precision on all RV32 and RV64 systems.",
        context="VSTIP reflects time + htimedelta >= vstimecmp (hip_vstip_op), so 64-bit precision applies to "
        "both sides of the comparison.",
        issues=ISSUE_1169,
        plan="1. Three random 64-bit values round-trip through vstimecmp (both halves on RV32).\n"
        "2. The comparison uses all 64 bits: with htimedelta = 0 and with a random multiple of 2^32, vstimecmp = "
        "time + htimedelta + 2^32 and + 2^33 (equal low halves, larger high half) gives VSTIP=0; lowering only "
        "the high half to that of time + htimedelta gives VSTIP=1.\n"
        "3. Unsigned comparison: vstimecmp = 2^63 gives VSTIP=0.",
    )
    vsetup(t)
    for _ in range(3):
        v = t.rand(64)
        vcmp(t, v, "random")
        lab = t.label("rt")
        t.emit(f"{lab}:", 0)
        t.emit("csrr x7, CSR_VSTIMECMP")
        t.check("x7", X(v & 0xFFFFFFFF, v), lab, "vstimecmp keeps its value")
        with t.rv32_only():
            t.emit("csrr x7, CSR_VSTIMECMPH")
            t.check("x7", v >> 32, lab, "vstimecmph keeps its value")
    for delta in (0, (t.rand(20) | 1) << 32):
        htd(t, delta, f"{delta:#x}")
        for k in (1, 2):
            vcmp_now(t, k)
            expect_vstip(
                t,
                int(MUT == "vs_compare_32bit"),
                f"vstimecmp = time + htimedelta + {k}*2^32, htimedelta = {delta:#x}",
                mview=False,
            )
        t.comment("lower only the high half: vstimecmp = time + htimedelta as read, now <= time + htimedelta")
        with t.rv64_only():
            t.emit("csrr x6, CSR_VSTIMECMP")
            t.li("x7", 2)
            t.emit("slli x7, x7, 32")
            t.emit("sub x6, x6, x7")
            t.emit("csrw CSR_VSTIMECMP, x6")
        with t.rv32_only():
            t.emit("csrr x6, CSR_VSTIMECMPH")
            t.emit("addi x6, x6, -2")
            t.emit("csrw CSR_VSTIMECMPH, x6")
        expect_vstip(t, 1, f"lowering only the high half of vstimecmp, htimedelta = {delta:#x}")
    htd(t, 0, "0")
    vcmp(t, 1 << 63, "2^63")
    expect_vstip(t, 0, "vstimecmp = 2^63 (unsigned comparison)")
    vteardown(t)
    tests.append(t)

    # ---- vstimecmp_acc ----
    t = new("vstimecmp_acc", REQ_H)
    t.describe(
        source=HYP,
        rule_text="In RV32 only, accesses to the vstimecmp CSR access the low 32 bits, while accesses to the "
        "vstimecmph CSR access the high 32 bits of vstimecmp.",
        context="VS-mode reaches vstimecmp and vstimecmph through stimecmp and stimecmph. On RV64, "
        "vstimecmph and stimecmph do not exist, so accessing them is illegal in HS-mode and, because the "
        "instruction is not valid in HS-mode either (not HS-qualified), illegal rather than virtual in VS-mode.",
        issues=HTM_WARL,
        plan="1. RV32, HS-mode: writing vstimecmp leaves vstimecmph unchanged and vice versa (random values).\n"
        "2. RV32, VS-mode: a write through stimecmp changes only the low half of vstimecmp, and a write through "
        "stimecmph only the high half.\n"
        "3. RV64: HS-mode access to vstimecmph and VS-mode access to stimecmph raise illegal-instruction.",
    )
    vsetup(t)
    with t.rv32_only():
        for first, second in (("CSR_VSTIMECMP", "CSR_VSTIMECMPH"), ("CSR_VSTIMECMPH", "CSR_VSTIMECMP")):
            a, b, c = t.rand(32), t.rand(32), t.rand(32)
            t.load("x6", a, "first half")
            t.emit(f"csrw {first}, x6")
            t.load("x6", b, "other half")
            t.emit(f"csrw {second}, x6")
            t.load("x6", c, "new first half")
            lab = t.label("half")
            t.emit(f"{lab}:", 0)
            t.emit(f"csrw {first}, x6")
            t.emit(f"csrr x7, {second}")
            t.check("x7", b, lab, f"HS-mode write of {first[4:].lower()} leaves {second[4:].lower()} unchanged")
            t.emit(f"csrr x7, {first}")
            t.check("x7", c, lab, f"{first[4:].lower()} holds its own write")
        htm_probe(t)

        def vs_halves() -> None:
            for vcsr, own, other in (
                ("stimecmp", "CSR_VSTIMECMP", "CSR_VSTIMECMPH"),
                ("stimecmph", "CSR_VSTIMECMPH", "CSR_VSTIMECMP"),
            ):
                a, b, c = t.rand(32), t.rand(32), t.rand(32)
                t.load("x6", a, "half VS-mode writes")
                t.emit(f"csrw {own}, x6")
                t.load("x6", b, "other half")
                t.emit(f"csrw {other}, x6")
                t.load("x6", c, f"value VS-mode writes through {vcsr}")
                lab = access(t, "VS", vcsr, FORMS[1], "ok", "RV32 halves")
                t.emit(f"csrr x7, {other}")
                t.check("x7", b, lab, f"a VS-mode write of {vcsr} leaves the other half of vstimecmp")
                t.emit(f"csrr x7, {own}")
                t.check("x7", c, lab, f"a VS-mode write of {vcsr} lands in {own[4:].lower()}")

        t.either(
            "x1", vs_halves, lambda: access(t, "VS", "stimecmp", FORMS[0], "virtual", "hcounteren.TM read-only zero")
        )
    with t.rv64_only():
        access(t, "S", "vstimecmph", FORMS[0], "illegal", "RV64 has no vstimecmph")
        access(t, "VS", "stimecmph", FORMS[0], "illegal", "RV64 has no stimecmph")
    vteardown(t)
    tests.append(t)

    # ---- henvcfg_stce ----
    t = new("henvcfg_stce", REQ_H)
    t.describe(
        source=HYP,
        rule_text="The Sstc extension adds the STCE (STimecmp Enable) bit to henvcfg CSR.",
        context="STCE is henvcfg bit 63 (henvcfgh bit 31 on RV32). It is read-only zero while menvcfg.STCE=0 "
        "(menvcfg_stce_zero_op), so the test sets menvcfg.STCE first.",
        issues=f"{ISSUE}1312: writes to henvcfg.STCE while it is read-only zero are ignored.",
        plan="1. With menvcfg.STCE=1, HS-mode clears and sets henvcfg.STCE with csrc/csrs and with full writes "
        "(csrw of the current value with the bit changed), reading 0 and 1 back.\n"
        "2. Changing STCE leaves the other bits of henvcfg unchanged.",
    )
    vsetup(t)
    for csrn, bitpos, cond in (("CSR_HENVCFG", 63, "__riscv_xlen == 64"), ("CSR_HENVCFGH", 31, "__riscv_xlen == 32")):
        with t.only_if(cond):
            t.emit(f"csrr x8, {csrn}")
            t.li("x6", 1)
            t.emit(f"slli x6, x6, {bitpos}")
            for how, val in (("csrc", 0), ("csrs", 1), ("csrw", 0), ("csrw", 1)):
                lab = t.label("stce")
                if how == "csrw":
                    t.emit(f"csrr x7, {csrn}")
                    t.emit(f"{'or' if val else 'xor'} x7, x7, x6")
                    t.emit(f"{lab}:", 0)
                    t.emit(f"csrw {csrn}, x7")
                else:
                    t.emit(f"{lab}:", 0)
                    t.emit(f"{how} {csrn}, x6")
                t.emit(f"csrr x7, {csrn}")
                t.emit(f"srli x7, x7, {bitpos}")
                t.check("x7", val, lab, f"henvcfg.STCE reads {val} after {how}")
            t.comment("the other bits are unchanged")
            lab = t.label("others")
            t.emit(f"{lab}:", 0)
            t.emit(f"csrr x7, {csrn}")
            t.emit("xor x7, x7, x8")
            t.check("x7", 0, lab, "changing henvcfg.STCE leaves the other henvcfg bits (STCE was 1 before)")
    vteardown(t)
    tests.append(t)

    # ---- henvcfg_stce_op ----
    t = new("henvcfg_stce_op", REQ_H)
    t.describe(
        source=HYP,
        rule_text="The STCE bit enables vstimecmp for VS-mode when set to one.",
        context="VS-mode access also needs menvcfg.STCE=1, mcounteren.TM=1 and hcounteren.TM=1, which the test "
        "sets. Enabling means VS-mode CSR instructions on stimecmp operate on vstimecmp, and the vstimecmp "
        "comparison drives hip.VSTIP.",
        issues=ISSUE_1985 + "\n" + HTM_WARL,
        plan="1. henvcfg.STCE=0 then 1: the same VS-mode read of stimecmp raises virtual-instruction, then "
        "succeeds.\n"
        "2. With STCE=1, every CSR instruction form on stimecmp in VS-mode returns the old vstimecmp value and "
        "leaves the value the form defines; on RV32 also on stimecmph.\n"
        "3. With STCE=1 the comparison drives hip.VSTIP (htimedelta = 0, hvip.VSTIP = 0): vstimecmp = 0 gives 1, "
        "all ones gives 0.\n"
        "4. Enabling is for VS-mode only: VU-mode reads and writes of stimecmp raise virtual-instruction, with "
        "scounteren.TM at 1 and 0.\n"
        "5. Transition: with vstimecmp = 0 and hvip.VSTIP = 0, hip.VSTIP is 0 while henvcfg.STCE=0 and becomes 1 "
        "when STCE is set.",
    )
    vsetup(t)
    henv_stce(t, False)
    access(t, "VS", "stimecmp", FORMS[0], "virtual", "henvcfg.STCE=0, before enabling")
    henv_stce(t, True)
    htm_probe(t)

    def enabled() -> None:
        access(t, "VS", "stimecmp", FORMS[0], "ok", "henvcfg.STCE=1, after enabling")
        vs_forms(t, "stimecmp")
        with t.rv32_only():
            vs_forms(t, "stimecmph")

    t.either("x1", enabled, lambda: access(t, "VS", "stimecmp", FORMS[0], "virtual", "hcounteren.TM read-only zero"))
    vcmp(t, 0, "0")
    expect_vstip(t, 1, "vstimecmp = 0 with henvcfg.STCE=1")
    vcmp(t, MAX64, "all ones")
    expect_vstip(t, 0, "vstimecmp = all ones with henvcfg.STCE=1")
    t.comment("enabling is for VS-mode only")
    for stm in (1, 0):
        t.li("x7", 2)
        t.emit(f"{'csrs' if stm else 'csrc'} scounteren, x7")
        uexp = "ok" if MUT == "vu_access_leak" and stm else "virtual"
        access(t, "VU", "stimecmp", FORMS[0], uexp, f"all gates set, scounteren.TM={stm}")
        access(t, "VU", "stimecmp", FORMS[1], uexp, f"all gates set, scounteren.TM={stm}")
    t.comment("transition: STCE=0 then 1 with vstimecmp = 0 and hvip.VSTIP = 0")
    henv_stce(t, False)
    vcmp(t, 0, "0")
    hvip(t, False)
    expect_vstip(t, int(MUT == "vstip_timer_with_henvcfg_stce0"), "henvcfg.STCE=0, vstimecmp=0, hvip.VSTIP=0")
    henv_stce(t, True)
    expect_vstip(t, 1, "setting henvcfg.STCE=1 with vstimecmp=0")
    vteardown(t)
    tests.append(t)

    # ---- henvcfg_stce_zero_op ----
    t = new("henvcfg_stce_zero_op", REQ_H)
    t.describe(
        source=HYP,
        rule_text="When STCE bit is henvcfg is zero, an attempt to access stimecmp (really vstimecmp) when V=1 "
        "raises a virtual-instruction exception, and VSTIP in hip reverts to its defined behavior as if this "
        "extension is not implemented.",
        context="Here menvcfg.STCE=1; with menvcfg.STCE=0 the access raises illegal-instruction instead "
        "(menvcfg_stce_zero_op). Without Sstc, hip.VSTIP is hvip.VSTIP (hip_vstip_acc).",
        issues=ISSUE_1985 + "\n" + ISSUE_1636_VS,
        plan="1. With henvcfg.STCE=0 and hcounteren.TM at 1 and 0: every CSR instruction form on stimecmp in "
        "VS-mode raises virtual-instruction (xtval 0 or the instruction bits); on RV32 also stimecmph. A VU-mode "
        "read does too.\n"
        "2. HS-mode access to vstimecmp is unaffected: a write of a random value reads back.\n"
        "3. hip.VSTIP reverts to hvip.VSTIP: with vstimecmp = 0 and with all ones, hvip.VSTIP = 0, 1, 0 gives "
        "hip.VSTIP (and mip.VSTIP read in M-mode) 0, 1, 0.\n"
        "4. The comparison does not drive interrupts: with hideleg[6]=0, hie.VSTIE=1, vstimecmp=0 and "
        "hvip.VSTIP=0, VS-mode takes no interrupt; once hvip.VSTIP=1 it takes one into HS-mode (cause 6).",
    )
    vsetup(t)
    vcmp(t, 0, "0 (comparison true)")
    henv_stce(t, False)
    vexp = "illegal" if MUT == "henvcfg_stce_illegal" else "virtual"
    for htmv in (1, 0):
        htm(t, bool(htmv))
        t.load("x6", t.rand_x(), "rs1 value")
        for form in FORMS:
            access(t, "VS", "stimecmp", form, vexp, f"henvcfg.STCE=0, hcounteren.TM={htmv}")
        with t.rv32_only():
            for form in (FORMS[0], FORMS[2]):
                access(t, "VS", "stimecmph", form, vexp, f"henvcfg.STCE=0, hcounteren.TM={htmv}")
        access(t, "VU", "stimecmp", FORMS[0], "virtual", f"henvcfg.STCE=0, hcounteren.TM={htmv}")
    htm(t, True)
    v = t.rand(64)
    vcmp(t, v, "random, HS-mode write with henvcfg.STCE=0")
    lab = t.label("hsrw")
    t.emit(f"{lab}:", 0)
    t.emit("csrr x7, CSR_VSTIMECMP")
    t.check("x7", X(v & 0xFFFFFFFF, v), lab, "HS-mode vstimecmp read/write works with henvcfg.STCE=0")
    for cmpv, note in ((0, "0"), (MAX64, "all ones")):
        vcmp(t, cmpv, note)
        for on in (False, True, False):
            hvip(t, on)
            exp = 1 if (on or (cmpv == 0 and MUT == "vstip_timer_with_henvcfg_stce0")) else 0
            expect_vstip(t, exp, f"hvip.VSTIP={int(on)} with henvcfg.STCE=0, vstimecmp={note}")
    t.comment("the comparison does not drive interrupts")
    vcmp(t, 0, "0")
    hvip(t, False)
    hie(t, True)
    delay_window(
        t,
        "VS",
        VSTI_HS if MUT == "vstip_timer_with_henvcfg_stce0" else "ok",
        "henvcfg.STCE=0, vstimecmp=0, hvip.VSTIP=0, hideleg[6]=0, hie.VSTIE=1: no interrupt",
    )
    hie(t, True)
    hvip(t, True)
    delay_window(t, "VS", VSTI_HS, "henvcfg.STCE=0, hvip.VSTIP=1, hideleg[6]=0, hie.VSTIE=1: interrupt into HS")
    vteardown(t)
    tests.append(t)

    # ---- hcounteren_acc ----
    t = new("hcounteren_acc", REQ_H)
    t.describe(
        source=HYP,
        rule_text="In addition, when the TM bit in the hcounteren register is clear, attempts to access the "
        "vstimecmp register (via stimecmp) while executing in VS-mode will cause a virtual-instruction exception "
        "if the same bit in mcounteren is set. When this bit and the same bit in mcounteren are both set, access "
        "to the vstimecmp register (if implemented) is permitted in VS-mode.",
        context="menvcfg.STCE=1 and henvcfg.STCE=1 throughout. hcounteren.TM does not apply to HS-mode.",
        issues=ISSUE_2040 + "\n" + ISSUE_1898 + "\n" + HTM_WARL,
        plan="1. With mcounteren.TM=1 and hcounteren.TM=0, every CSR instruction form on stimecmp in VS-mode "
        "raises virtual-instruction; on RV32 also stimecmph.\n"
        "2. hcounteren.TM does not gate HS-mode: with hcounteren.TM=0, HS-mode accesses to vstimecmp and stimecmp "
        "succeed.\n"
        "3. Negative dependency: hcounteren.TM=0 does not stop the vstimecmp comparison: vstimecmp = 0 gives "
        "hip.VSTIP=1, all ones gives 0.\n"
        "4. hcounteren.TM=1 permits access: a VS-mode read returns vstimecmp and a write lands in it (or, if "
        "hcounteren.TM is read-only zero, the read still raises virtual-instruction).\n"
        "5. mcounteren.TM=0 takes precedence: VS-mode access raises illegal-instruction with hcounteren.TM at 1 "
        "and 0.",
    )
    vsetup(t)
    htm(t, False)
    t.load("x6", t.rand_x(), "rs1 value")
    hexp = "ok" if MUT == "hcounteren_ignored" else "virtual"
    for form in FORMS:
        access(t, "VS", "stimecmp", form, hexp, "mcounteren.TM=1, hcounteren.TM=0")
    with t.rv32_only():
        for form in (FORMS[0], FORMS[2]):
            access(t, "VS", "stimecmph", form, hexp, "mcounteren.TM=1, hcounteren.TM=0")
    access(t, "S", "vstimecmp", FORMS[0], "ok", "hcounteren.TM=0, HS-mode")
    access(t, "S", "vstimecmp", FORMS[1], "ok", "hcounteren.TM=0, HS-mode")
    access(t, "S", "stimecmp", FORMS[0], "ok", "hcounteren.TM=0, HS-mode")
    vcmp(t, 0, "0")
    expect_vstip(t, 1, "vstimecmp = 0 with hcounteren.TM=0")
    vcmp(t, MAX64, "all ones")
    expect_vstip(t, 0, "vstimecmp = all ones with hcounteren.TM=0")
    old, gv = t.rand(64), X(t.rand(32), t.rand(64))
    vcmp(t, old, "random")
    htm_probe(t)

    def permitted() -> None:
        lab = access(t, "VS", "stimecmp", FORMS[0], "ok", "mcounteren.TM=1, hcounteren.TM=1")
        t.check("x7", X(old & 0xFFFFFFFF, old), lab, "a VS-mode read of stimecmp returns vstimecmp")
        t.load("x6", gv, "value VS-mode writes")
        lab = access(t, "VS", "stimecmp", FORMS[1], "ok", "mcounteren.TM=1, hcounteren.TM=1")
        t.emit("csrr x7, CSR_VSTIMECMP")
        t.check("x7", gv, lab, "a VS-mode write of stimecmp lands in vstimecmp")

    t.either("x1", permitted, lambda: access(t, "VS", "stimecmp", FORMS[0], "virtual", "hcounteren.TM read-only zero"))
    tm(t, False)
    for htmv in (1, 0):
        htm(t, bool(htmv))
        access(
            t,
            "VS",
            "stimecmp",
            FORMS[0],
            "virtual" if MUT == "mcounteren_tm_virtual" else "illegal",
            f"mcounteren.TM=0, hcounteren.TM={htmv}",
        )
    tm(t, True)
    vteardown(t)
    tests.append(t)

    # ---- hip_vstip_op ----
    t = new("hip_vstip_op", REQ_HT)
    t.describe(
        source=HYP,
        rule_text="A virtual supervisor timer interrupt becomes pending, as reflected in the vstip bit in the hip "
        "register, whenever (time + htimedelta), truncated to 64 bits, contains a value greater than or equal to "
        "vstimecmp, treating the values as unsigned integers.",
        context="hvip.VSTIP is 0 throughout, so hip.VSTIP is the comparison result (hip_vstip_acc). mip.VSTIP "
        "aliases hip.VSTIP and is also read, in M-mode through T-SBI. htimedelta and the comparison inputs are "
        "computed in HS-mode from time and htimedelta.",
        issues=ISSUE_1169 + "\n" + ISSUE_2237,
        plan="1. htimedelta = 0: vstimecmp = 0, = time (just read), = time + 2^32 (equal low halves), = 2^63 "
        "(unsigned), = all ones.\n"
        "2. htimedelta = 2^40: vstimecmp = time + 2^39 is pending only because htimedelta is added; = time + "
        "htimedelta + 2^32 is not.\n"
        "3. htimedelta = -2^40 (2^64 - 2^40): vstimecmp = time is pending (the sum is a large unsigned value); "
        "= time + htimedelta + 2^32 is not.\n"
        "4. htimedelta = all ones: the sum wraps to time - 1 (truncated to 64 bits), so vstimecmp = time + 2^32 "
        "is not pending and vstimecmp = 0 is.\n"
        "5. htimedelta = 2^32 - 1, which carries out of the low half: vstimecmp = time + htimedelta is pending, "
        "and + 2^32 is not.",
    )
    vsetup(t)
    m = MUT
    cases: list[tuple[int, str, list[tuple[str, int, int, str]]]] = [
        (
            0,
            "0",
            [
                ("const", 0, 1, "0"),
                ("now", 0, 1, "time"),
                ("now", 1, int(m == "vs_compare_32bit"), "time + 2^32"),
                ("const", 1 << 63, int(m == "vs_signed_compare"), "2^63"),
                ("const", MAX64, 0, "all ones"),
            ],
        ),
        (
            1 << 40,
            "2^40",
            [("raw", 128, int(m != "vs_ignore_htimedelta"), "time + 2^39"), ("now", 1, 0, "time + htimedelta + 2^32")],
        ),
        (
            (1 << 64) - (1 << 40),
            "-2^40",
            [("raw", 0, int(m != "vs_signed_compare"), "time"), ("now", 1, 0, "time + htimedelta + 2^32")],
        ),
        (MAX64, "all ones (-1)", [("raw", 1, int(m == "vs_no_truncate"), "time + 2^32"), ("const", 0, 1, "0")]),
        (
            0xFFFFFFFF,
            "2^32 - 1",
            [("now", 0, int(m != "vs_carry_dropped"), "time + htimedelta"), ("now", 1, 0, "time + htimedelta + 2^32")],
        ),
    ]
    for delta, dnote, checks in cases:
        htd(t, delta, dnote)
        for how, v, exp, note in checks:
            if how == "const":
                vcmp(t, v, note)
            else:
                vcmp_now(t, v, delta=how == "now")
            expect_vstip(t, exp, f"vstimecmp = {note}, htimedelta = {dnote}")
    vteardown(t)
    tests.append(t)

    # ---- hip_vstip_clear ----
    t = new("hip_vstip_clear", REQ_HT)
    t.describe(
        source=HYP,
        rule_text="If the result of this comparison changes, it is guaranteed to be reflected in vstip eventually, "
        "but not necessarily immediately. The interrupt remains posted until vstimecmp becomes greater than (time "
        "+ htimedelta), typically as a result of writing vstimecmp.",
        context='"Eventually" is handled by polling hip.VSTIP a bounded number of times before each check. '
        "hvip.VSTIP is 0 throughout.",
        issues=ISSUE_1169,
        plan="1. With vstimecmp = 0, VSTIP is 1 and stays 1 across a delay.\n"
        "2. Taking the interrupt does not clear it: with hideleg[6]=0 and hie.VSTIE=1, VS-mode takes the "
        "interrupt into HS-mode (cause 6), and VSTIP is still 1 afterwards.\n"
        "3. Writing vstimecmp above time + htimedelta clears it.\n"
        "4. A change of htimedelta alone is reflected: with vstimecmp = time + htimedelta + 2^32 (VSTIP 0), "
        "raising htimedelta by 2^33 sets VSTIP, and lowering it back clears it.",
    )
    vsetup(t)
    vcmp(t, 0, "0")
    expect_vstip(t, 1, "vstimecmp = 0")
    expect_vstip(t, 1, "vstimecmp = 0, after a further delay", settle=False)
    hie(t, True)
    delay_window(t, "VS", VSTI_HS, "hideleg[6]=0, hie.VSTIE=1, vstimecmp=0: interrupt into HS")
    expect_vstip(t, 1, "taking the interrupt (vstimecmp still 0)", settle=False)
    hie(t, False)
    vcmp_now(t, 1)
    expect_vstip(t, 0, "writing vstimecmp = time + htimedelta + 2^32")
    htd(t, 1 << 33, "2^33")
    expect_vstip(t, int(MUT != "vstip_only_on_write"), "raising htimedelta by 2^33 (vstimecmp unchanged)")
    htd(t, 0, "0")
    expect_vstip(t, 0, "lowering htimedelta back to 0")
    vteardown(t)
    tests.append(t)

    # ---- hip_vstip_enable ----
    t = new("hip_vstip_enable", REQ_H)
    t.describe(
        source=HYP,
        rule_text="The interrupt will be taken based on the standard interrupt enable and delegation rules while V=1.",
        context="mideleg[6] is read-only one with H, so the VS-level timer interrupt goes to HS-mode unless "
        "hideleg[6] delegates it to VS-mode, where it is a supervisor timer interrupt (cause 5). An interrupt "
        "delegated to VS is taken only when V=1: in VS-mode when vsstatus.SIE=1 and vsie.STIE (= hie.VSTIE) = 1, "
        "and in VU-mode whenever it is enabled. One taken in HS-mode (cause 6) is always enabled while V=1, and "
        "in HS-mode needs sstatus.SIE=1. The interrupt comes from vstimecmp = 0 with hvip.VSTIP = 0.",
        plan="1. hideleg[6]=1: in VS-mode, (vsstatus.SIE, hie.VSTIE) in {00, 01, 10, 11} with VSTIP pending, and "
        "11 not pending: taken into VS-mode (cause 5) only for 11 pending. In VU-mode with vsstatus.SIE=0: taken "
        "iff hie.VSTIE=1. In HS-mode with sstatus.SIE=1 and hie.VSTIE=1: never taken.\n"
        "2. hideleg[6]=0: in VS-mode and VU-mode with every SIE 0: taken into HS-mode (cause 6) iff hie.VSTIE=1. "
        "In HS-mode: taken iff sstatus.SIE=1 and hie.VSTIE=1.\n"
        "Each taken interrupt is checked for its cause, the handler's mode, and the mode it came from.",
    )
    vsetup(t)
    hideleg(t, True)
    for sie, vstie in ((0, 0), (0, 1), (1, 0), (1, 1)):
        vs_int_case(t, 1, "VS", sie, vstie, 1)
    vs_int_case(t, 1, "VS", 1, 1, 0)
    for vstie in (0, 1):
        vs_int_case(t, 1, "VU", 0, vstie, 1)
    vs_int_case(t, 1, "S", 1, 1, 1)
    hideleg(t, False)
    for mode in ("VS", "VU"):
        for vstie in (0, 1):
            vs_int_case(t, 0, mode, 0, vstie, 1)
    vs_int_case(t, 0, "S", 1, 1, 1)
    vs_int_case(t, 0, "S", 0, 1, 1)
    vteardown(t)
    tests.append(t)

    # ---- hip_vstip_vstimecmp_op ----
    t = new("hip_vstip_vstimecmp_op", REQ_HT)
    t.describe(
        source=HYP,
        rule_text="The hip[vstip] bit, in response to timer interrupts generated by vstimecmp, is set by writing "
        "vstimecmp with a value that is less than or equal to the sum of time and htimedelta, truncated to 64 "
        "bits; it is cleared by writing vstimecmp with a greater value.",
        context="VS-mode writes vstimecmp through stimecmp, and reads time as time + htimedelta, so a guest that "
        "programs its timer from its own time sees the same rule.",
        issues=ISSUE_1169 + "\n" + HTM_WARL,
        plan="1. htimedelta = a random large value. HS-mode writes vstimecmp = time + htimedelta - 2^32 and = "
        "time + htimedelta (both set VSTIP), and = time + htimedelta + 2^32 and all ones (both clear it).\n"
        "2. VS-mode reads its time and writes stimecmp = that time (sets VSTIP), then = that time + 2^32 (clears "
        "it). If hcounteren.TM reads back 0, the VS-mode time read raises virtual-instruction instead.",
    )
    vsetup(t)
    d = ((t.rand(23) | 1) << 32) | t.rand(32)
    htd(t, d, f"{d:#x}")
    for k, exp in ((-1, 1), (1, 0), (0, 1)):
        vcmp_now(t, k)
        expect_vstip(t, exp, f"HS-mode write vstimecmp = time + htimedelta + {k}*2^32")
    vcmp(t, MAX64, "all ones")
    expect_vstip(t, 0, "HS-mode write vstimecmp = all ones")
    htm_probe(t)

    def guest_writes() -> None:
        for k, exp in ((0, 1), (1, 0)):
            desc = f"VS-mode write stimecmp = its time + {k}*2^32"
            with t.rv64_only():
                lines = ["csrr x6, time"] + (["LI(x7, 1)", "slli x7, x7, 32", "add x6, x6, x7"] if k else [])
                t.window("VS", lines + ["csrw stimecmp, x6"], "ok", desc)
            with t.rv32_only():
                rd = ["csrr x7, time", "csrr x6, timeh", "addi x6, x6, 1"] if k else ["csrr x6, timeh", "csrr x7, time"]
                t.window("VS", rd + ["csrw stimecmph, x6", "csrw stimecmp, x7"], "ok", desc)
            expect_vstip(t, exp, desc)

    t.either(
        "x1",
        guest_writes,
        lambda: t.window(
            "VS", ["csrr x6, time"], 22, "time read, hcounteren.TM read-only zero", tval=[0, enc(0xC01, 2, 6, 0)]
        ),
    )
    vteardown(t)
    tests.append(t)

    # ---- hip_vstip_acc ----
    t = new("hip_vstip_acc", REQ_H)
    t.describe(
        source=HYP,
        rule_text="vstip is read-only in hip, and is the logical-OR of hvip[vstip] and, when the sstc extension "
        "is implemented, the timer interrupt signal resulting from vstimecmp.",
        context="henvcfg.STCE=1 (the timer signal exists) and htimedelta = 0. The H suite covers hip.VSTIP "
        "without Sstc.",
        plan="1. (hvip.VSTIP, comparison) over 00, 01, 10, 11, with vstimecmp = all ones or 0: hip.VSTIP, and "
        "mip.VSTIP read in M-mode, is the OR; hvip.VSTIP reads back what was written, independent of the timer.\n"
        "2. hip.VSTIP is read-only: csrs of hip with VSTIP=0, and csrc of hip with VSTIP=1 from the timer and from "
        "hvip, leave it unchanged.",
    )
    vsetup(t)
    for hv, cm in ((0, 0), (0, 1), (1, 0), (1, 1)):
        hvip(t, bool(hv))
        vcmp(t, 0 if cm else MAX64, "0 (comparison true)" if cm else "all ones")
        exp = cm if MUT == "vstip_hvip_ignored" else (hv | cm)
        expect_vstip(t, exp, f"hvip.VSTIP={hv}, comparison={cm}")
        lab = t.label("hvip")
        t.emit(f"{lab}:", 0)
        t.emit("csrr x7, CSR_HVIP")
        t.emit(f"andi x7, x7, {VSTIP}")
        t.check("x7", VSTIP if hv else 0, lab, f"hvip.VSTIP reads back {hv} (comparison={cm})")
    t.comment("hip.VSTIP is read-only")
    hvip(t, False)
    vcmp(t, MAX64, "all ones")
    expect_vstip(t, 0, "hvip.VSTIP=0, vstimecmp all ones")
    t.li("x6", VSTIP)
    t.emit("csrs CSR_HIP, x6")
    expect_vstip(t, int(MUT == "hip_vstip_writable"), "csrs hip.VSTIP (read-only)", settle=False)
    vcmp(t, 0, "0")
    expect_vstip(t, 1, "vstimecmp = 0")
    t.li("x6", VSTIP)
    t.emit("csrc CSR_HIP, x6")
    expect_vstip(t, 1, "csrc hip.VSTIP with VSTIP from the timer (read-only)", settle=False)
    vcmp(t, MAX64, "all ones")
    hvip(t, True)
    expect_vstip(t, 1, "hvip.VSTIP=1")
    t.li("x6", VSTIP)
    t.emit("csrc CSR_HIP, x6")
    expect_vstip(t, 1, "csrc hip.VSTIP with VSTIP from hvip (read-only)", settle=False)
    vteardown(t)
    tests.append(t)

    # ---- menvcfg_stce_zero_vstip ----
    t = new("menvcfg_stce_zero_vstip", REQ_H)
    t.describe(
        source=MAC,
        rule_text="Further, if the H extension is implemented, then hip.VSTIP also reverts its defined behavior "
        "as if this extension is not implemented.",
        context="This follows menvcfg_stce_zero_op (menvcfg.STCE=0). Without Sstc, hip.VSTIP is hvip.VSTIP "
        "(hip_vstip_acc). menvcfg.STCE=0 also makes henvcfg.STCE read-only zero, so henvcfg.STCE=1 is masked.",
        issues=ISSUE_1636_VS,
        plan="1. With menvcfg.STCE=1, henvcfg.STCE=1, vstimecmp = 0 and hvip.VSTIP = 0, hip.VSTIP is 1.\n"
        "2. menvcfg.STCE=0: hvip.VSTIP = 0, 1, 0 gives hip.VSTIP (and mip.VSTIP read in M-mode) 0, 1, 0, with "
        "vstimecmp = 0.\n"
        "3. No interrupt from the comparison: with hideleg[6]=0, hie.VSTIE=1, vstimecmp = 0 and hvip.VSTIP = 0, "
        "VS-mode takes no interrupt.\n"
        "4. Setting menvcfg.STCE and henvcfg.STCE again: hip.VSTIP is 1 again.",
    )
    vsetup(t)
    vcmp(t, 0, "0")
    expect_vstip(t, 1, "menvcfg.STCE=1, henvcfg.STCE=1, vstimecmp=0")
    stce(t, False)
    for on in (False, True, False):
        hvip(t, on)
        exp = 1 if on or MUT == "vstip_not_reverted" else 0
        expect_vstip(t, exp, f"menvcfg.STCE=0, vstimecmp=0, hvip.VSTIP={int(on)}")
    hie(t, True)
    delay_window(
        t,
        "VS",
        VSTI_HS if MUT == "vstip_not_reverted" else "ok",
        "menvcfg.STCE=0, vstimecmp=0, hvip.VSTIP=0, hideleg[6]=0, hie.VSTIE=1: no interrupt",
    )
    hie(t, False)
    stce(t, True)
    henv_stce(t, True)
    expect_vstip(t, 1, "setting menvcfg.STCE and henvcfg.STCE again (vstimecmp=0)")
    vteardown(t)
    tests.append(t)

    return tests


def main() -> None:
    for t in gen():
        p = t.write()
        print(f"{p.relative_to(p.parents[2])}: ~{t.ninst} instructions")


if __name__ == "__main__":
    main()
