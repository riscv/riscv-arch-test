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
    from aigen import Value

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

    return tests


def main() -> None:
    for t in gen():
        p = t.write()
        print(f"{p.relative_to(p.parents[2])}: ~{t.ninst} instructions")


if __name__ == "__main__":
    main()
