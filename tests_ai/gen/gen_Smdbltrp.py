#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate tests_ai/Smdbltrp and tests_ai/Ssdbltrp: one test per normative rule about the double-trap extensions.

The Smdbltrp and Ssdbltrp chapters only name the fields; the behavior is tagged in machine.adoc (mstatus.MDT, MRET,
MNRET, menvcfg.DTE), supervisor.adoc (sstatus.SDT, the double-trap exception) and hypervisor.adoc (henvcfg.DTE,
vsstatus.SDT). Smdbltrp tests boot to M-mode. Ssdbltrp tests boot to S-mode and reach menvcfg through T-SBI; their
M-mode parts are <rule>_Sm.S files. Traps are checked in the framework trap log (common/ai_macros.h).

An unexpected trap in M-mode (MDT=1) puts a hart without Smrnmi into the critical-error state, which ends the run,
and with Smrnmi enters the RNMI handler at an implementation-defined address the framework does not know. No test
takes one on purpose; a DUT bug that leaves MDT=1 makes the next trap into M-mode end the run.
"""

from __future__ import annotations

import os
import sys
from contextlib import ExitStack
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent))
import dbltrplib as d
from aigen import POOL_TRAP, TestFile, X

if TYPE_CHECKING:
    from collections.abc import Callable

    from aigen import Expect

SUITE = "Smdbltrp"
ISSUE = "https://github.com/riscv/riscv-isa-manual/issues/"
MARCH = "rv${XLEN}i_zicsr_zifencei"
MAC = "src/priv/machine.adoc"
SUP = "src/priv/supervisor.adoc"
HYP = "src/priv/hypervisor.adoc"
SSD = "src/priv/ssdbltrp.adoc"
SMD = "src/priv/smdbltrp.adoc"
H = d.H
S_OK = "defined(S_SUPPORTED)"
U_OK = "defined(U_SUPPORTED)"
FA = "defined(RVMODEL_ACCESS_FAULT_ADDRESS)"
MUT = os.environ.get("AI_MUTANT", "")

MUTANTS = {
    # Smdbltrp
    "mdt_readonly0": "mstatus.MDT is read-only zero (writes of 1 ignored)",
    "mie_kept_on_mdt_set": "setting MDT by a CSR write leaves MIE set",
    "same_write_mie_wins": "RV64: a single mstatus write of MDT=1, MIE=1 leaves MIE=1",
    "mie_set_with_mdt1": "MIE can be set by a CSR write while MDT=1",
    "mdt_clear_same_write_ignored": "RV64: a write that clears MDT cannot set MIE",
    "trap_no_mdt_set": "a trap into M-mode leaves MDT=0",
    "mret_m_keeps_mdt": "MRET to M-mode leaves MDT=1",
    "mnret_m_clears_mdt": "MNRET to M-mode clears MDT",
    # Ssdbltrp
    "dte_rdonly0": "menvcfg.DTE is read-only zero",
    "sdt_not_aliased": "sstatus.SDT and mstatus.SDT are separate bits",
    "sdt_csrc_ignored": "csrc does not clear sstatus.SDT",
    "sie_kept_on_sdt_set": "setting SDT by a CSR write leaves SIE set",
    "sie_set_with_sdt1": "SIE can be set by a CSR write while SDT=1",
    "sdt_clear_same_write_ignored": "a write that clears SDT cannot set SIE",
    "dte0_sdt_writable": "with menvcfg.DTE=0, sstatus.SDT is writable",
    "dte0_double_trap": "with menvcfg.DTE=0, a trap into S-mode with SDT stored as 1 is a double trap",
    "trap_no_sdt_set": "a trap into S-mode leaves SDT=0",
    "unexpected_delivered_to_s": "a trap into S-mode with SDT=1 is delivered to S-mode",
    "unexpected_writes_scause": "a double trap also writes scause",
    "double_trap_mdt0": "a double trap into M-mode leaves MDT=0",
    "regs_mpp_m": "a double trap records MPP=M",
    "regs_mpv_set": "a double trap from S-mode records MPV=1 (as if from VS-mode)",
    "mtval2_zero": "a double trap writes mtval2 = 0",
    "mcause_unexpected": "a double trap writes mcause = the unexpected trap's cause",
    "sret_keeps_sdt": "SRET to S-mode leaves SDT=1",
    "mret_u_keeps_sdt": "MRET to U-mode leaves sstatus.SDT=1",
    "mret_s_clears_sdt": "MRET to S-mode clears sstatus.SDT",
    "mret_vu_keeps_vssdt": "MRET to VU-mode leaves vsstatus.SDT=1",
    "mret_vs_clears_vssdt": "MRET to VS-mode clears vsstatus.SDT",
    "mnret_u_keeps_sdt": "MNRET to U-mode leaves sstatus.SDT=1",
    "mnret_vu_keeps_vssdt": "MNRET to VU-mode leaves vsstatus.SDT=1",
    "vs_double_trap_to_hs": "a VS-mode double trap is taken in HS-mode",
    "vs_trap_no_sdt": "a trap into VS-mode leaves vsstatus.SDT=0",
    "henvcfg_dte0_vs_double_trap": "with henvcfg.DTE=0, a VS-mode trap with vsstatus.SDT stored as 1 is a double trap",
    "henvcfg_dte_rdonly0": "henvcfg.DTE is read-only zero with menvcfg.DTE=1",
    "vsstatus_sdt_rdonly0": "vsstatus.SDT is read-only zero with both DTE bits set",
}

ISSUE_2403 = (
    f"{ISSUE}2403: MRET and MNRET to S/HS-mode leave sstatus.SDT unchanged, and to VS-mode leave vsstatus.SDT "
    'unchanged (ved-rivos: "When machine mode uses MRET to resume execution of the trap handler in S/HS mode, the '
    'sstatus.SDT retains its state"); SRET executed in M-mode with SPP=S clears SDT ("Yes, following the rule: An SRET '
    'instruction sets the SDT bit to 0").'
)
ISSUE_2870 = (
    f"{ISSUE}2870: the U/VS/VU clause of the MRET/SRET paragraph is qualified by execution in M-mode, and the "
    "supervisor-chapter rule (SRET clears SDT) is qualified by execution in S-mode (aswaterman: the two rules "
    'discuss disjoint cases; "we want to preserve SDT after handling the trap in M-mode"). This conflicts with '
    "#2403 for SRET executed in M-mode with SPP=S, so that case accepts SDT = 0 or 1."
)
ISSUE_3155 = (
    f"{ISSUE}3155: a write of MDT 1 -> 1 also counts as setting MDT, and the state MDT=1, MIE=1 cannot be reached "
    '(ved-rivos: "MDT=1 MIE=1 state cannot be reached").'
)
ISSUE_2264 = (
    f"{ISSUE}2264: with menvcfg.DTE=0, sstatus.SDT, vsstatus.SDT and henvcfg.DTE are read-only zero; clearing them "
    'and masking them on read are both valid ("That is a valid implementation. Mask-on-read is also a valid '
    'implementation"), so after DTE is set again SDT reads 0 or its old value.'
)
ISSUE_1623 = (
    f"{ISSUE}1623: menvcfg.DTE does not affect M-mode, and SIE cannot be 1 while SDT is 1, in both the sstatus and "
    "the mstatus views."
)
ISSUE_3057 = (
    f"{ISSUE}3057: the stacking of SIE through SPIE is unaffected by Ssdbltrp; only explicit CSR writes are "
    "constrained by SDT."
)
ISSUE_3254 = (
    f"{ISSUE}3254: with Smdbltrp and Smrnmi, an exception in M-mode with mnstatus.NMIE=0 enters the critical-error "
    "state whatever MDT is."
)

# One-instruction trap classes. Each is (name, setup lines, faulting line, cause, legal xtval as a
# list (LAB = the instruction's own label), guard). The load and store address is in x6.
EBREAK = ".word 0x00100073  // ebreak"
CLASSES = {
    "ebreak": ([], EBREAK, 3, [0, "LAB"], None),
    "lw_fault": (["LI(x6, RVMODEL_ACCESS_FAULT_ADDRESS_LOAD)"], "lw x7, 0(x6)", 5, [0, "ADDR"], FA),
    "sw_fault": (["LI(x6, RVMODEL_ACCESS_FAULT_ADDRESS_STORE)"], "sw x7, 0(x6)", 7, [0, "ADDR"], FA),
}
MISALIGNED = (["LA(x6, ai_scratch)", "addi x6, x6, 1"], "lw x7, 0(x6)")


def out(suite: str) -> str:
    """The directory a test is written to: its suite, or the mutant directory."""
    return suite if SUITE == "Smdbltrp" else SUITE


def new_m(rule: str, required: list[str] | None = None, **kw: object) -> TestFile:
    """A Smdbltrp test (boot M)."""
    return TestFile(
        out("Smdbltrp"),
        rule,
        required=required or ["I", "Sm", "Smdbltrp"],
        march=MARCH,
        boot="M",
        pool=POOL_TRAP,
        **kw,  # type: ignore[arg-type]
    )


def new_s(rule: str, required: list[str] | None = None) -> TestFile:
    """An Ssdbltrp test (boot S)."""
    return TestFile(
        out("Ssdbltrp"), rule, required=required or ["I", "S", "Ssdbltrp"], march=MARCH, boot="S", pool=POOL_TRAP
    )


def new_sm(rule: str, required: list[str] | None = None) -> TestFile:
    """The M-mode part of an Ssdbltrp rule (boot M, requires Sm)."""
    return TestFile(
        out("Ssdbltrp"),
        rule,
        required=required or ["I", "Sm", "S", "Ssdbltrp"],
        march=MARCH,
        boot="M",
        pool=POOL_TRAP,
        suffix="_Sm",
    )


def scratch(t: TestFile) -> None:
    if "ai_scratch:" not in "\n".join(t.extra_data):
        t.extra_data += ["  .p2align 3", "ai_scratch:", "  .dword 0x0123456789abcdef, 0x0fedcba987654321"]


def win(
    t: TestFile,
    mode: str,
    cls: str,
    expect: Expect | None = None,
    desc: str = "",
    origin: str | None = None,
) -> str:
    """One trap window in `mode` for trap class `cls` (see CLASSES; "misaligned" is a misaligned lw). expect
    defaults to the class's own cause. Returns the window label."""
    if cls == "misaligned":
        scratch(t)
        setup, line = MISALIGNED
        cause: Expect = ["ok", 4, 5]
        tval: list = [0, "ADDR"]
    else:
        setup, line, cause, tval, _ = CLASSES[cls]
    for ln in setup:
        t.emit(ln, 2)
    lab = t.label(f"in_{mode}")
    tv = [lab if v == "LAB" else v for v in tval]
    if "ADDR" in tv:
        tv = [0, "x6"]  # replaced below: the address is only known at run time
    t.allow(1)
    if mode != t.cur:
        t.enter(mode)
    t.emit(f"{lab}:", 0)
    t.emit(line)
    if mode != t.cur:
        t.leave()
    exp = cause if expect is None else expect
    if "x6" in tv:
        t.outcome(exp, lab, f"{desc} in {mode}-mode", None, origin=origin or mode)
        tval_reg(t, lab, exp, f"{desc} in {mode}-mode")
    else:
        t.outcome(exp, lab, f"{desc} in {mode}-mode", tv, origin=origin or mode)
    return lab


def tval_reg(t: TestFile, lab: str, exp: Expect, desc: str) -> None:
    """xtval of the last trap is 0 or x6 (the faulting address); x15 = 1 when no trap was taken and none is
    required."""
    alts = exp if isinstance(exp, list) else [exp]
    ok, done = t.label("tvok"), t.label("tvdone")
    if "ok" in alts:
        t.emit("li x5, -1")
        t.emit(f"beq x14, x5, {ok}")
    d.log(t, "x15", "TRAPLOG_TVAL")
    t.emit("xor x14, x15, x6")
    t.emit("seqz x14, x14")
    t.emit("seqz x15, x15")
    t.emit("or x15, x15, x14")
    if "ok" in alts:
        t.emit(f"j {done}")
        t.emit(f"{ok}:", 0)
        t.emit("li x15, 1")
        t.emit(f"{done}:", 0)
    t.check_bool("x15", lab, f"{desc}: xtval is 0 or the faulting address")


def guard(t: TestFile, cls: str) -> str | None:
    return None if cls == "misaligned" else CLASSES[cls][4]


def cases(t: TestFile, classes: list[str], body: Callable[[str], None]) -> None:
    for cls in classes:
        g = guard(t, cls)
        if g:
            with t.only_if(g):
                body(cls)
        else:
            body(cls)


# ======================================================================== Smdbltrp: MDT and MIE
def mstatus_rw(t: TestFile, op: str, value_reg: str, rd: str = "x0") -> None:
    """M-mode CSR op on the register holding MDT (mstatus on RV64, mstatush on RV32)."""
    with t.rv64_only():
        t.emit(f"{op} {rd}, mstatus, {value_reg}")
    with t.rv32_only():
        t.emit(f"{op} {rd}, {hex(d.CSR_MSTATUSH)}, {value_reg}")


def check_mdt(t: TestFile, lab: str, value: int, desc: str, reg: str = "x8") -> None:
    d.read_mdt(t, reg)
    t.check(reg, value, lab, f"{desc}: MDT = {value}")


def check_mie(t: TestFile, lab: str, value: int, desc: str, reg: str = "x8") -> None:
    t.emit(f"csrr {reg}, mstatus")
    t.emit(f"andi {reg}, {reg}, {d.MIE}")
    t.check(reg, value * d.MIE, lab, f"{desc}: MIE = {value}")


def mie_guard_begin(t: TestFile) -> None:
    t.comment("mie = 0 while MIE is set, so no interrupt is taken; restored at the end")
    t.emit("csrrw x1, mie, x0")


def mie_guard_end(t: TestFile) -> None:
    t.emit("csrci mstatus, 8  // MIE = 0")
    d.mdt(t, False)
    t.emit("csrw mie, x1")


def gen_smdbltrp() -> list[TestFile]:
    tests = []

    # ---- mstatus_mdt_sz_warl ----
    t = new_m("mstatus_mdt_sz_warl")
    t.describe(
        source=MAC,
        rule_text="The M-mode-disable-trap (mdt) bit is a WARL field introduced by the smdbltrp extension.",
        context="MDT is mstatus bit 42 on RV64 and mstatush bit 10 on RV32. Both values are legal (traps set MDT and "
        "MRET clears it), so writes of 0 and 1 are kept. The boot code writes MDT=0. No trap is taken while MDT=1 "
        "(it would be an unexpected trap); MIE stays 0 throughout, so the MDT/MIE coupling does not matter here.",
        plan="1. MDT reads 0 after the boot code's write of 0.\n"
        "2. csrs sets MDT, csrc clears it, csrw with MDT=1 and with MDT=0 (other bits as read) sets and clears it.\n"
        "3. csrrs and csrrc return the old value with MDT and write the new one; csrrw returns the old value.\n"
        "4. Read-only forms (csrrs rd, x0 and csrrsi/csrrci with uimm=0) and writes of other bits leave MDT=1.",
    )
    lab = t.label("rd")
    t.emit(f"{lab}:", 0)
    check_mdt(t, lab, 0, "after boot")
    d.bit_x(t, "x6", d.MDT)
    lab = t.label("csrs")
    t.emit(f"{lab}:", 0)
    mstatus_rw(t, "csrrs", "x6")
    check_mdt(t, lab, 0 if MUT == "mdt_readonly0" else 1, "csrs MDT")
    lab = t.label("csrc")
    t.emit(f"{lab}:", 0)
    mstatus_rw(t, "csrrc", "x6")
    check_mdt(t, lab, 0, "csrc MDT")
    lab = t.label("csrw1")
    t.emit(f"{lab}:", 0)
    with t.rv64_only():
        t.emit("csrr x7, mstatus")
        t.emit("or x7, x7, x6")
        t.emit("csrw mstatus, x7")
    with t.rv32_only():
        t.emit("csrr x7, 0x310")
        t.emit("or x7, x7, x6")
        t.emit("csrw 0x310, x7")
    check_mdt(t, lab, 1, "csrw with MDT=1")
    lab = t.label("csrw0")
    t.emit(f"{lab}:", 0)
    with t.rv64_only():
        t.emit("csrr x7, mstatus")
        t.emit("xor x7, x7, x6")
        t.emit("csrw mstatus, x7")
    with t.rv32_only():
        t.emit("csrr x7, 0x310")
        t.emit("xor x7, x7, x6")
        t.emit("csrw 0x310, x7")
    check_mdt(t, lab, 0, "csrw with MDT=0")
    lab = t.label("csrrs")
    t.emit(f"{lab}:", 0)
    mstatus_rw(t, "csrrs", "x6", "x8")
    t.emit("and x8, x8, x6")
    t.check("x8", 0, lab, "csrrs returns the old MDT = 0")
    mstatus_rw(t, "csrrs", "x6", "x8")
    t.emit("and x8, x8, x6")
    t.check("x8", d.MDT, lab, "a second csrrs returns MDT = 1")
    lab = t.label("ro")
    t.emit(f"{lab}:", 0)
    mstatus_rw(t, "csrrs", "x0", "x8")
    with t.rv64_only():
        t.emit("csrrsi x8, mstatus, 0")
        t.emit("csrrci x8, mstatus, 0")
        t.emit("csrrci x8, mstatus, 2  // clears SIE only")
    with t.rv32_only():
        t.emit("csrrsi x8, 0x310, 0")
        t.emit("csrrci x8, 0x310, 0")
        t.emit("csrrci x8, mstatus, 2  // clears SIE only")
    check_mdt(t, lab, 1, "read-only forms and writes of other bits")
    lab = t.label("csrrc")
    t.emit(f"{lab}:", 0)
    mstatus_rw(t, "csrrc", "x6", "x8")
    t.emit("and x8, x8, x6")
    t.check("x8", d.MDT, lab, "csrrc returns the old MDT = 1")
    check_mdt(t, lab, 0, "csrrc MDT")
    lab = t.label("csrrw")
    t.emit(f"{lab}:", 0)
    with t.rv64_only():
        t.emit("csrr x7, mstatus")
        t.emit("or x7, x7, x6")
        t.emit("csrrw x8, mstatus, x7")
    with t.rv32_only():
        t.emit("csrr x7, 0x310")
        t.emit("or x7, x7, x6")
        t.emit("csrrw x8, 0x310, x7")
    t.emit("and x8, x8, x6")
    t.check("x8", 0, lab, "csrrw returns the old MDT = 0")
    check_mdt(t, lab, 1, "csrrw with MDT=1")
    d.mdt(t, False)
    check_mdt(t, lab, 0, "final csrc")
    tests.append(t)

    # ---- mstatus_mie_clr_by_mdt ----
    t = new_m("mstatus_mie_clr_by_mdt")
    t.describe(
        source=MAC,
        rule_text="When the mdt bit is set to 1 by an explicit CSR write, the mie (Machine Interrupt Enable) bit is "
        "cleared to 0.",
        context="On RV32 MDT is in mstatush and MIE in mstatus, so a write of mstatush clears a bit of another CSR. "
        "mie is 0 while MIE is set, so no interrupt is taken. The single-write RV64 case (MDT and MIE written "
        "together) is mstatus_mie_clr_by_mdt_rv64.",
        issues=ISSUE_3155,
        plan="1. With MDT=0, MIE=1: setting MDT with csrs, csrrs, csrw and csrrw (mstatus on RV64, mstatush on RV32; "
        "every other bit as read) leaves MDT=1 and MIE=0.\n"
        "2. Negative: with MDT=0, MIE=1, writes that leave MDT=0 (csrc of MDT, csrw of the register as read, "
        "csrs of SIE) leave MIE=1.",
    )
    mie_guard_begin(t)
    d.bit_x(t, "x6", d.MDT)
    for form in ("csrs", "csrrs", "csrw", "csrrw"):
        lab = t.label(form)
        d.mdt(t, False)
        t.emit("csrsi mstatus, 8  // MIE = 1")
        check_mie(t, lab, 1, "MIE set with MDT=0")
        t.emit(f"{lab}:", 0)
        if form in ("csrs", "csrrs"):
            mstatus_rw(t, "csrrs", "x6", "x8" if form == "csrrs" else "x0")
        else:
            with t.rv64_only():
                t.emit("csrr x7, mstatus")
                t.emit("or x7, x7, x6")
                t.emit(f"csrrw {'x8' if form == 'csrrw' else 'x0'}, mstatus, x7")
            with t.rv32_only():
                t.emit("csrr x7, 0x310")
                t.emit("or x7, x7, x6")
                t.emit(f"csrrw {'x8' if form == 'csrrw' else 'x0'}, 0x310, x7")
        check_mdt(t, lab, 1, f"{form} sets MDT")
        check_mie(t, lab, 1 if MUT == "mie_kept_on_mdt_set" else 0, f"{form} setting MDT clears MIE")
    for neg, lines in (
        ("csrc MDT", None),
        ("csrw of the register as read (MDT=0)", "same"),
        ("csrs SIE", "sie"),
    ):
        lab = t.label("neg")
        d.mdt(t, False)
        t.emit("csrsi mstatus, 8  // MIE = 1")
        t.emit(f"{lab}:", 0)
        if lines is None:
            mstatus_rw(t, "csrrc", "x6")
        elif lines == "same":
            with t.rv64_only():
                t.emit("csrr x7, mstatus")
                t.emit("csrw mstatus, x7")
            with t.rv32_only():
                t.emit("csrr x7, 0x310")
                t.emit("csrw 0x310, x7")
        else:
            t.emit("csrsi mstatus, 2  // SIE = 1")
            t.emit("csrci mstatus, 2")
        check_mie(t, lab, 1, f"{neg} with MDT=0 leaves MIE")
        check_mdt(t, lab, 0, f"{neg}")
    mie_guard_end(t)
    tests.append(t)

    # ---- mstatus_mie_clr_by_mdt_rv64 ----
    t = new_m("mstatus_mie_clr_by_mdt_rv64", rv64=True)
    t.describe(
        source=MAC,
        rule_text="For RV64, this clearing occurs regardless of the value written, if any, to the mie bit by the "
        "same write.",
        context="On RV64 MDT (bit 42) and MIE (bit 3) are in the same CSR, so one write can set both. mie is 0 while "
        "MIE is set. RV64-only rule: the file passes trivially on RV32.",
        issues=ISSUE_3155,
        plan="1. From MDT=0 with MIE=0 and with MIE=1: csrw, csrrw, csrs and csrrs that write MDT=1 and MIE=1 in "
        "the same write leave MDT=1, MIE=0.\n"
        "2. From MDT=1 (MIE=0): csrw with MDT=1 and MIE=1 leaves MIE=0 (a write of 1 to MDT that is already 1).",
    )
    mie_guard_begin(t)
    t.emit("li x6, 1")
    t.emit("slli x6, x6, 42")
    t.emit("ori x6, x6, 8  // MDT | MIE")
    for start in (0, 1):
        for form in ("csrw", "csrrw", "csrs", "csrrs"):
            lab = t.label(form)
            d.mdt(t, False)
            t.emit(f"{'csrsi' if start else 'csrci'} mstatus, 8  // MIE = {start}")
            t.emit(f"{lab}:", 0)
            if form in ("csrw", "csrrw"):
                t.emit("csrr x7, mstatus")
                t.emit("or x7, x7, x6")
                t.emit(f"csrrw {'x8' if form == 'csrrw' else 'x0'}, mstatus, x7")
            else:
                t.emit(f"csrrs {'x8' if form == 'csrrs' else 'x0'}, mstatus, x6")
            check_mdt(t, lab, 1, f"{form} of MDT=1, MIE=1 from MIE={start}")
            check_mie(t, lab, 1 if MUT == "same_write_mie_wins" else 0, f"{form} of MDT=1, MIE=1 from MIE={start}")
    lab = t.label("again")
    t.emit(f"{lab}:", 0)
    t.emit("csrr x7, mstatus")
    t.emit("or x7, x7, x6")
    t.emit("csrw mstatus, x7")
    check_mie(t, lab, 0, "csrw of MDT=1, MIE=1 with MDT already 1")
    mie_guard_end(t)
    tests.append(t)

    # ---- mstatus_mie_set_mdt_0 ----
    t = new_m("mstatus_mie_set_mdt_0")
    t.describe(
        source=MAC,
        rule_text="The mie bit can only be set to 1 by an explicit CSR write if the mdt bit is already 0",
        context="mie is 0 while MIE is set. The RV64 case where the same write clears MDT is "
        "mstatus_mie_set_mdt_0_rv64; here every write leaves MDT=1 or MDT was 0 before it.",
        issues=ISSUE_3155,
        plan="1. With MDT=1 (MIE=0): csrsi, csrrsi, csrs, csrrs and csrw of mstatus with MIE=1 (every other bit "
        "as read, so MDT stays 1 on RV64), and on RV32 csrrwi mstatus, 8, leave MIE=0.\n"
        "2. With MDT=0: csrsi and csrw with MIE=1 set MIE (MIE=1 is reachable).\n"
        "3. MDT cleared by one write, then MIE set by the next: MIE=1.",
    )
    mie_guard_begin(t)
    t.emit("li x6, 8  // MIE")
    for form in ("csrsi", "csrrsi", "csrs", "csrrs", "csrw"):
        lab = t.label(form)
        t.emit("csrci mstatus, 8")
        d.mdt(t, True)
        t.emit(f"{lab}:", 0)
        if form in ("csrsi", "csrrsi"):
            t.emit(f"csrrsi {'x8' if form == 'csrrsi' else 'x0'}, mstatus, 8")
        elif form in ("csrs", "csrrs"):
            t.emit(f"csrrs {'x8' if form == 'csrrs' else 'x0'}, mstatus, x6")
        else:
            t.emit("csrr x7, mstatus")
            t.emit("ori x7, x7, 8")
            t.emit("csrw mstatus, x7")
        check_mie(t, lab, 1 if MUT == "mie_set_with_mdt1" else 0, f"{form} of MIE=1 with MDT=1")
        check_mdt(t, lab, 1, f"{form} of MIE=1 with MDT=1")
    with t.rv32_only():
        lab = t.label("csrrwi")
        t.emit("csrci mstatus, 8")
        d.mdt(t, True)
        t.emit(f"{lab}:", 0)
        t.emit("csrrwi x8, mstatus, 8  // RV32: mstatush.MDT=1 is not written")
        check_mie(t, lab, 1 if MUT == "mie_set_with_mdt1" else 0, "RV32 csrrwi of MIE=1 with mstatush.MDT=1")
        check_mdt(t, lab, 1, "RV32 csrrwi of mstatus")
    d.mdt(t, False)
    for form in ("csrsi", "csrw"):
        lab = t.label(form)
        t.emit("csrci mstatus, 8")
        t.emit(f"{lab}:", 0)
        if form == "csrsi":
            t.emit("csrsi mstatus, 8")
        else:
            t.emit("csrr x7, mstatus")
            t.emit("ori x7, x7, 8")
            t.emit("csrw mstatus, x7")
        check_mie(t, lab, 1, f"{form} of MIE=1 with MDT=0")
    lab = t.label("seq")
    t.emit("csrci mstatus, 8")
    d.mdt(t, True)
    t.emit(f"{lab}:", 0)
    d.mdt(t, False)
    t.emit("csrsi mstatus, 8")
    check_mie(t, lab, 1, "MDT cleared, then csrsi MIE")
    mie_guard_end(t)
    tests.append(t)

    # ---- mstatus_mie_set_mdt_0_rv64 ----
    t = new_m("mstatus_mie_set_mdt_0_rv64", rv64=True)
    t.describe(
        source=MAC,
        rule_text="or, for RV64, is being set to 0 by the same write",
        context="Continues mstatus_mie_set_mdt_0: on RV64 one mstatus write can clear MDT and set MIE. mie is 0 "
        "while MIE is set. RV64-only rule: the file passes trivially on RV32.",
        issues=ISSUE_3155,
        plan="1. With MDT=1, MIE=0: csrw and csrrw of mstatus with MDT=0 and MIE=1 (every other bit as read) leave "
        "MDT=0, MIE=1.\n"
        "2. Contrast: csrw with MDT=1 and MIE=1 leaves MIE=0.",
    )
    mie_guard_begin(t)
    t.emit("li x6, 1")
    t.emit("slli x6, x6, 42  // MDT")
    for form in ("csrw", "csrrw"):
        lab = t.label(form)
        t.emit("csrci mstatus, 8")
        t.emit("csrs mstatus, x6  // MDT = 1")
        t.emit(f"{lab}:", 0)
        t.emit("csrr x7, mstatus")
        t.emit("xor x7, x7, x6  // MDT = 0")
        t.emit("ori x7, x7, 8  // MIE = 1")
        t.emit(f"csrrw {'x8' if form == 'csrrw' else 'x0'}, mstatus, x7")
        check_mdt(t, lab, 0, f"{form} of MDT=0, MIE=1 from MDT=1")
        check_mie(t, lab, 0 if MUT == "mdt_clear_same_write_ignored" else 1, f"{form} of MDT=0, MIE=1 from MDT=1")
    lab = t.label("contrast")
    t.emit("csrci mstatus, 8")
    t.emit("csrs mstatus, x6")
    t.emit(f"{lab}:", 0)
    t.emit("csrr x7, mstatus")
    t.emit("ori x7, x7, 8")
    t.emit("csrw mstatus, x7")
    check_mie(t, lab, 0, "csrw of MDT=1, MIE=1 from MDT=1")
    mie_guard_end(t)
    tests.append(t)

    # ---- trap_exp ----
    t = new_m("trap_exp")
    t.describe(
        source=MAC,
        rule_text="When a trap is to be taken into M-mode, if the mdt bit is currently 0, it is then set to 1, and "
        "the trap is delivered as expected.",
        context="The test boots to M-mode, where medeleg and mideleg are 0, so every trap goes to M-mode. The "
        "framework's M handler records mstatus (mstatush on RV32) on entry, before it changes anything; its MRET "
        "then clears MDT again. MDT=0 before every trap (checked).",
        plan="1. Exceptions from M-mode: ebreak, an illegal instruction (csrrw to mhartid), a load access fault "
        "(RVMODEL_ACCESS_FAULT_ADDRESS); from S-mode and U-mode (when present): ebreak. Each is delivered with its "
        "own cause, mepc and origin mode, and MDT=1 at handler entry.\n"
        "2. Interrupt: a supervisor software interrupt (mip.SSIP, not delegated) taken in M-mode with MIE=1 "
        "(with S-mode): MDT=1 at handler entry.\n"
        "3. After each trap returns, MDT reads 0.",
    )
    mdt_exp = 0 if MUT == "trap_no_mdt_set" else 1

    def after(lab: str, desc: str) -> None:
        d.log_mdt(t, lab, mdt_exp, desc)
        check_mdt(t, lab, 0, f"{desc}: after the handler's MRET")

    lab = t.label("pre")
    t.emit(f"{lab}:", 0)
    check_mdt(t, lab, 0, "before the traps")
    for mode, cls in (("M", "ebreak"), ("M", "lw_fault")):
        g = CLASSES[cls][4]
        if g:
            with t.only_if(g):
                lab = win(t, mode, cls, desc=cls)
                after(lab, f"{cls} in {mode}-mode")
        else:
            lab = win(t, mode, cls, desc=cls)
            after(lab, f"{cls} in {mode}-mode")
    lab = t.label("ill")
    t.allow(1)
    t.emit(f"{lab}:", 0)
    t.emit(".word 0xF1401073  // csrrw x0, mhartid, x0: write to a read-only CSR")
    t.outcome(2, lab, "illegal instruction in M-mode", [0, 0xF1401073], origin="M")
    after(lab, "illegal instruction in M-mode")
    for mode, cond in (("S", S_OK), ("U", U_OK)):
        with t.only_if(cond):
            lab = win(t, mode, "ebreak", desc="ebreak")
            after(lab, f"ebreak in {mode}-mode")
    with t.only_if(S_OK):
        t.comment("supervisor software interrupt taken in M-mode (mideleg = 0)")
        t.emit("csrrw x1, mie, x0")
        t.emit("csrci mstatus, 8  // MIE = 0 until the window")
        t.emit("csrsi mip, 2  // SSIP")
        t.emit("csrsi mie, 2  // SSIE")
        lab = t.label("ssi")
        t.allow(1)
        t.emit(f"{lab}:", 0)
        t.emit("csrsi mstatus, 8  // MIE = 1")
        loop = t.label("wait")
        t.li("x9", 50)
        t.emit(f"{loop}:", 0)
        t.emit("addi x9, x9, -1", 50)
        t.emit(f"bnez x9, {loop}", 50)
        t.emit("csrci mstatus, 8")
        t.emit("csrci mip, 2")
        t.emit("csrw mie, x1")
        t.outcome(X((1 << 31) | 1, (1 << 63) | 1), lab, "SSI in M-mode", epc=False, origin="M")
        after(lab, "SSI in M-mode")
    tests.append(t)

    # ---- mstatus_mdt_clr_mret_sret ----
    t = new_m("mstatus_mdt_clr_mret_sret")
    t.describe(
        source=MAC,
        rule_text="When the smdbltrp extension is implemented, executing an mret instruction, or executing an sret "
        "instruction while the current privilege mode is M, has the following additional effects. The mdt bit is "
        "set to 0.",
        context="With MPP=M the result is read directly after the MRET. In S, U, VS and VU MDT cannot be read, so "
        "the test takes an ebreak there (medeleg = 0): with MDT=0 it is an ordinary trap into M-mode, logged with "
        "its cause; a hart that left MDT=1 takes an unexpected trap instead and the run ends.",
        issues=ISSUE_2870,
        plan="1. MDT=1, MRET with MPP=M: MDT reads 0 after it, and the MRET itself does not trap.\n"
        "2. MDT=0, MRET with MPP=M: MDT stays 0.\n"
        "3. MDT=1, MRET to S, U (when present), VS and VU (with H): an ebreak there is an ordinary trap into "
        "M-mode (cause 3, origin mode as entered).\n"
        "4. MDT=1, SRET in M-mode with SPP=S and SPP=U (with S): an ebreak in the new mode is an ordinary trap.",
    )
    for start in (1, 0):
        lab = t.label("mretm")
        d.mdt(t, bool(start))
        t.allow(1)
        d.mret_to(t, "M", lab)
        t.emit(f"{lab}:", 0)
        d.read_mdt(t, "x8")
        t.outcome("ok", lab, f"MRET to M-mode with MDT={start}")
        t.check("x8", 1 if (MUT == "mret_m_keeps_mdt" and start) else 0, lab, f"MRET to M-mode with MDT={start}: MDT")
    for mode, cond in (("S", S_OK), ("U", U_OK), ("VS", H), ("VU", H)):
        with t.only_if(cond):
            if mode in ("VS", "VU"):
                d.bare_guest(t)
            d.mdt(t, True)
            lab = t.label(f"to{mode}")
            t.allow(1)
            d.mret_to(t, mode, lab)
            t.emit(f"{lab}:", 0)
            t.emit(EBREAK)
            t.leave()
            t.outcome(3, lab, f"ebreak in {mode}-mode after MRET with MDT=1", [0, lab], origin=mode)
            check_mdt(t, lab, 0, f"back in M-mode after the {mode}-mode ebreak")
    with t.only_if(S_OK):
        for spp, mode in ((1, "S"), (0, "U")):
            lab = t.label(f"sret{mode}")
            d.mdt(t, True)
            t.allow(1)
            t.emit(f"LA(x7, {lab})", 2)
            t.emit("csrw sepc, x7")
            t.li("x7", d.SPP)
            t.emit(f"{'csrs' if spp else 'csrc'} mstatus, x7  // SPP = {spp}")
            with t.only_if(H):
                t.emit("li x7, 0x80")
                t.emit("csrc 0x600, x7  // hstatus.SPV = 0")
            t.emit("sret  // in M-mode")
            t.emit(f"{lab}:", 0)
            t.emit(EBREAK)
            t.leave()
            t.outcome(3, lab, f"ebreak in {mode}-mode after SRET in M-mode with MDT=1", [0, lab], origin=mode)
            check_mdt(t, lab, 0, f"back in M-mode after the {mode}-mode ebreak")
    tests.append(t)

    # ---- mstatus_mdt_clr_mnret ----
    t = new_m("mstatus_mdt_clr_mnret", required=["I", "Sm", "Smdbltrp", "Smrnmi"])
    t.describe(
        source=MAC,
        rule_text="When the smdbltrp extension is implemented, the mnret instruction, provided by the smrnmi "
        "extension, sets the mdt bit to 0 if the new privilege mode is not M.",
        context="MNRET (0x70200073) is executed in M-mode without an RNMI: it returns to mnepc in the mode given by "
        "mnstatus.MNPP/MNPV and sets mnstatus.NMIE=1 (it is 1 already). With MNPP=M, MDT must be unchanged. In "
        "other modes MDT cannot be read, so an ebreak there (medeleg = 0) must be an ordinary trap into M-mode; "
        "a hart that left MDT=1 takes an unexpected trap instead.",
        issues=ISSUE_3254,
        plan="1. MDT=1, MNRET with MNPP=M: MDT stays 1 (then cleared by a CSR write); MDT=0, MNPP=M: stays 0.\n"
        "2. MDT=1, MNRET to S, U (when present), VS and VU (with H): an ebreak there is an ordinary trap into "
        "M-mode (cause 3).",
    )
    for start in (1, 0):
        lab = t.label("mnretm")
        d.mdt(t, bool(start))
        t.allow(1)
        mnret_to(t, "M", lab)
        t.emit(f"{lab}:", 0)
        d.read_mdt(t, "x8")
        d.mdt(t, False)
        t.outcome("ok", lab, f"MNRET to M-mode with MDT={start}")
        t.check("x8", 0 if MUT == "mnret_m_clears_mdt" else start, lab, f"MNRET to M-mode with MDT={start}: MDT")
    for mode, cond in (("S", S_OK), ("U", U_OK), ("VS", H), ("VU", H)):
        with t.only_if(cond):
            if mode in ("VS", "VU"):
                d.bare_guest(t)
            d.mdt(t, True)
            lab = t.label(f"to{mode}")
            t.allow(1)
            mnret_to(t, mode, lab)
            t.emit(f"{lab}:", 0)
            t.emit(EBREAK)
            t.leave()
            t.outcome(3, lab, f"ebreak in {mode}-mode after MNRET with MDT=1", [0, lab], origin=mode)
            check_mdt(t, lab, 0, f"back in M-mode after the {mode}-mode ebreak")
    tests.append(t)
    return tests


def mnret_to(t: TestFile, mode: str, target: str, reg: str = "x7") -> None:
    """M-mode: mnepc = target, mnstatus.MNPP/MNPV for `mode`, then MNRET."""
    mnpp = {"M": 3, "S": 1, "VS": 1, "U": 0, "VU": 0}[mode]
    t.emit(f"LA({reg}, {target})", 2)
    t.emit(f"csrw {hex(d.CSR_MNEPC)}, {reg}  // mnepc")
    t.li(reg, d.MNSTATUS_MNPP | d.MNSTATUS_MNPV)
    t.emit(f"csrc {hex(d.CSR_MNSTATUS)}, {reg}  // mnstatus.MNPP = 0, MNPV = 0")
    bits = (mnpp << 11) | (d.MNSTATUS_MNPV if mode in ("VS", "VU") else 0)
    if bits:
        t.li(reg, bits)
        t.emit(f"csrs {hex(d.CSR_MNSTATUS)}, {reg}  // mnstatus.MNPP/MNPV for {mode}-mode")
    t.emit(f".word {hex(d.MNRET)}  // mnret")


# ======================================================================== Ssdbltrp
def s_setup(t: TestFile) -> None:
    d.dte_tsbi(t, True)


def s_teardown(t: TestFile) -> None:
    t.li("x7", d.SDT)
    t.emit("csrc sstatus, x7  // SDT = 0")
    d.dte_tsbi(t, False)


def sdt_s(t: TestFile, on: bool) -> None:
    t.li("x7", d.SDT)
    t.emit(f"{'csrs' if on else 'csrc'} sstatus, x7  // SDT = {int(on)}")


def check_sdt(t: TestFile, lab: str, value: int | list[int], desc: str, csr: str = "sstatus") -> None:
    d.read_sdt(t, "x8", csr)
    t.check("x8", value, lab, f"{desc}: {csr}.SDT")


def check_sie(t: TestFile, lab: str, value: int, desc: str, csr: str = "sstatus") -> None:
    t.emit(f"csrr x8, {csr}")
    t.emit("andi x8, x8, 2")
    t.check("x8", value * d.SIE, lab, f"{desc}: {csr}.SIE = {value}")


def gen_ssdbltrp() -> list[TestFile]:
    tests: list[TestFile] = []
    tests += gen_ss_fields()
    tests += gen_ss_sie()
    tests += gen_ss_dte_op()
    tests += gen_ss_trap()
    tests += gen_ss_double()
    tests += gen_ss_sret()
    tests += gen_ss_vs()
    tests += gen_ss_xret_sm()
    return tests


def gen_ss_fields() -> list[TestFile]:
    tests = []
    # ---- menvcfg_dte ----
    t = new_s("menvcfg_dte")
    t.describe(
        source=SSD,
        rule_text="The Ssdbltrp extension adds the menvcfg.DTE (See <<sec:menvcfg>>)",
        context="menvcfg.DTE is bit 59 (menvcfgh bit 27 on RV32). The test boots to S-mode and reaches menvcfg through "
        "T-SBI; the boot code writes DTE=0. Its effect on sstatus.SDT (writable only with DTE=1) shows that the bit "
        "is the double-trap enable.",
        plan="1. DTE reads 0 after boot.\n"
        "2. Setting DTE reads back 1, and sstatus.SDT becomes writable (csrs reads back 1).\n"
        "3. Clearing DTE reads back 0, and sstatus.SDT reads 0.\n"
        "4. A full-register write with DTE=1 (other bits as read) reads back 1.",
    )
    lab = t.label("boot")
    t.emit(f"{lab}:", 0)
    tsbi_dte_read(t, "x8")
    t.check("x8", 0, lab, "menvcfg.DTE after boot")
    lab = t.label("set")
    t.emit(f"{lab}:", 0)
    d.dte_tsbi(t, True)
    tsbi_dte_read(t, "x8")
    t.check("x8", 0 if MUT == "dte_rdonly0" else 1, lab, "menvcfg.DTE after setting it")
    sdt_s(t, True)
    check_sdt(t, lab, 1, "csrs SDT with DTE=1")
    lab = t.label("clr")
    t.emit(f"{lab}:", 0)
    d.dte_tsbi(t, False)
    tsbi_dte_read(t, "x8")
    t.check("x8", 0, lab, "menvcfg.DTE after clearing it")
    check_sdt(t, lab, 0, "with DTE=0")
    lab = t.label("wr")
    t.emit(f"{lab}:", 0)
    with t.rv64_only():
        t.tsbi_csr("READ", "MENVCFG")
        d.bit_x(t, "x7", d.DTE)
        t.emit("or a1, a0, x7")
        t.tsbi_csr("WRITE", "MENVCFG", "a1")
    with t.rv32_only():
        t.tsbi_csr("READ", "MENVCFGH")
        d.bit_x(t, "x7", d.DTE)
        t.emit("or a1, a0, x7")
        t.tsbi_csr("WRITE", "MENVCFGH", "a1")
    tsbi_dte_read(t, "x8")
    t.check("x8", 1, lab, "menvcfg.DTE after a full-register write with DTE=1")
    s_teardown(t)
    tests.append(t)

    # ---- sstatus_sdt_exists ----
    t = new_s("sstatus_sdt_exists")
    t.describe(
        source=SSD,
        rule_text="and the sstatus.SDT fields (See <<sstatus>>).",
        context="SDT is bit 24 of sstatus, a view of mstatus.SDT. With menvcfg.DTE=1 (set through T-SBI) the field "
        "is writable from S-mode. M-mode reads and writes it through T-SBI; the T-SBI call's own trap and MRET "
        "back to S-mode do not change SDT.",
        issues=ISSUE_1623,
        plan="1. S-mode sets sstatus.SDT: it reads 1 in sstatus and in mstatus (M-mode view).\n"
        "2. M-mode clears mstatus.SDT: sstatus.SDT reads 0.\n"
        "3. M-mode sets mstatus.SDT: sstatus.SDT reads 1; S-mode clears it: mstatus.SDT reads 0.",
    )
    s_setup(t)
    lab = t.label("s1")
    t.emit(f"{lab}:", 0)
    sdt_s(t, True)
    check_sdt(t, lab, 1, "S-mode csrs SDT")
    t.tsbi_csr("READ", "MSTATUS")
    t.emit("srli x8, a0, 24")
    t.emit("andi x8, x8, 1")
    t.check("x8", 0 if MUT == "sdt_not_aliased" else 1, lab, "mstatus.SDT after S-mode set it")
    lab = t.label("m0")
    t.emit(f"{lab}:", 0)
    t.tsbi_csr("CLEAR", "MSTATUS", imm=d.SDT)
    check_sdt(t, lab, 0, "after M-mode cleared mstatus.SDT")
    lab = t.label("m1")
    t.emit(f"{lab}:", 0)
    t.tsbi_csr("SET", "MSTATUS", imm=d.SDT)
    check_sdt(t, lab, 1, "after M-mode set mstatus.SDT")
    sdt_s(t, False)
    t.tsbi_csr("READ", "MSTATUS")
    t.emit("srli x8, a0, 24")
    t.emit("andi x8, x8, 1")
    t.check("x8", 0, lab, "mstatus.SDT after S-mode cleared it")
    s_teardown(t)
    tests.append(t)

    # ---- sstatus_sdt ----
    t = new_s("sstatus_sdt")
    t.describe(
        source=SUP,
        rule_text="The S-mode-disable-trap (SDT) bit is a WARL field introduced by the Ssdbltrp extension to address "
        "double trap (See <<machine-double-trap>>) at privilege modes lower than M.",
        context="With menvcfg.DTE=1 both values are legal (a trap sets SDT, SRET clears it), so writes of 0 and 1 "
        "are kept. Bit 24 is out of reach of the immediate CSR forms. No trap into S-mode is taken while SDT=1.",
        plan="1. csrs/csrc, csrrs/csrrc (returning the old value) and csrw/csrrw (other bits as read) write SDT=1 "
        "and SDT=0.\n"
        "2. With SDT=1: csrrs rd, x0, csrrsi/csrrci with uimm=0 and csrrci of SIE leave SDT=1.",
    )
    s_setup(t)
    t.li("x6", d.SDT)
    for form in ("csrs", "csrc", "csrrs", "csrrc", "csrw1", "csrw0", "csrrw1"):
        lab = t.label(form)
        t.emit(f"{lab}:", 0)
        if form in ("csrs", "csrc"):
            t.emit(f"{form} sstatus, x6")
            val = 1 if form == "csrs" else 0
            if MUT == "sdt_csrc_ignored" and form == "csrc":
                val = 1
        elif form in ("csrrs", "csrrc"):
            t.emit(f"{form} x9, sstatus, x6")
            t.emit("and x9, x9, x6")
            t.check("x9", 0 if form == "csrrs" else d.SDT, lab, f"{form} returns the old SDT")
            val = 1 if form == "csrrs" else 0
        else:
            val = 1 if form.endswith("1") else 0
            t.emit("csrr x7, sstatus")
            t.emit("or x7, x7, x6")
            if not val:
                t.emit("xor x7, x7, x6")
            t.emit(f"{'csrrw x9' if form == 'csrrw1' else 'csrrw x0'}, sstatus, x7")
        check_sdt(t, lab, val, form)
    lab = t.label("ro")
    t.emit(f"{lab}:", 0)
    t.emit("csrrs x9, sstatus, x0")
    t.emit("csrrsi x9, sstatus, 0")
    t.emit("csrrci x9, sstatus, 0")
    t.emit("csrrci x9, sstatus, 2  // SIE = 0")
    check_sdt(t, lab, 1, "read-only forms and writes of other bits")
    s_teardown(t)
    tests.append(t)

    # ---- henvcfg_dte ----
    t = new_s("henvcfg_dte", ["I", "S", "H", "Ssdbltrp"])
    t.describe(
        source=SSD,
        rule_text="If the hypervisor extension is additionally implemented, then the extension adds the henvcfg.DTE "
        "(See <<sec:henvcfg>>)",
        context="henvcfg.DTE is bit 59 (henvcfgh bit 27 on RV32), written from HS-mode. With menvcfg.DTE=0 it is "
        "read-only zero (menvcfg_dte_op), so menvcfg.DTE is set first. Its effect on vsstatus.SDT (writable only "
        "with henvcfg.DTE=1) shows that it is the VS-level enable.",
        plan="1. With menvcfg.DTE=1: henvcfg.DTE written 1 reads 1 (csrs, and csrw with other bits as read), and "
        "written 0 reads 0 (csrc).\n"
        "2. With henvcfg.DTE=1, vsstatus.SDT written 1 reads 1; with henvcfg.DTE=0 it reads 0.",
    )
    s_setup(t)
    lab = t.label("set")
    t.emit(f"{lab}:", 0)
    d.henv_dte(t, True)
    d.read_dte(t, "x8", "henvcfg")
    t.check("x8", 0 if MUT == "henvcfg_dte_rdonly0" else 1, lab, "henvcfg.DTE after csrs")
    t.li("x6", d.SDT)
    t.emit(f"csrs {hex(d.CSR_VSSTATUS)}, x6  // vsstatus.SDT = 1")
    check_sdt(t, lab, 1, "vsstatus.SDT written 1 with henvcfg.DTE=1", hex(d.CSR_VSSTATUS))
    t.emit(f"csrc {hex(d.CSR_VSSTATUS)}, x6")
    lab = t.label("clr")
    t.emit(f"{lab}:", 0)
    d.henv_dte(t, False)
    d.read_dte(t, "x8", "henvcfg")
    t.check("x8", 0, lab, "henvcfg.DTE after csrc")
    t.emit(f"csrs {hex(d.CSR_VSSTATUS)}, x6")
    check_sdt(t, lab, 0, "vsstatus.SDT written 1 with henvcfg.DTE=0", hex(d.CSR_VSSTATUS))
    lab = t.label("csrw")
    t.emit(f"{lab}:", 0)
    d.bit_x(t, "x7", d.DTE)
    with t.rv64_only():
        t.emit(f"csrr x8, {hex(d.CSR_HENVCFG)}")
        t.emit("or x8, x8, x7")
        t.emit(f"csrw {hex(d.CSR_HENVCFG)}, x8")
    with t.rv32_only():
        t.emit(f"csrr x8, {hex(d.CSR_HENVCFGH)}")
        t.emit("or x8, x8, x7")
        t.emit(f"csrw {hex(d.CSR_HENVCFGH)}, x8")
    d.read_dte(t, "x8", "henvcfg")
    t.check("x8", 1, lab, "henvcfg.DTE after csrw with DTE=1")
    d.henv_dte(t, False)
    s_teardown(t)
    tests.append(t)

    # ---- vsstatus_sdt ----
    t = new_s("vsstatus_sdt", ["I", "S", "H", "Ssdbltrp"])
    t.describe(
        source=SSD,
        rule_text="and the vsstatus.SDT fields (See <<vsstatus>>).",
        context="vsstatus.SDT is bit 24. With menvcfg.DTE=1 and henvcfg.DTE=1 it is writable from HS-mode (as "
        "vsstatus) and from VS-mode (as sstatus, which VS-mode accesses as vsstatus). HS-mode sstatus.SDT is a "
        "separate bit. SRET from HS-mode into VS-mode leaves vsstatus.SDT alone (sret_dt).",
        plan="1. HS-mode writes vsstatus.SDT = 1: it reads 1, and HS sstatus.SDT stays 0.\n"
        "2. In VS-mode, sstatus.SDT reads 1 (the vsstatus bit); VS-mode clears it and sets it again, and HS-mode "
        "reads each value back from vsstatus.",
    )
    s_setup(t)
    d.henv_dte(t, True)
    t.li("x6", d.SDT)
    lab = t.label("hs")
    t.emit(f"{lab}:", 0)
    t.emit(f"csrs {hex(d.CSR_VSSTATUS)}, x6")
    check_sdt(t, lab, 0 if MUT == "vsstatus_sdt_rdonly0" else 1, "HS-mode set vsstatus.SDT", hex(d.CSR_VSSTATUS))
    check_sdt(t, lab, 0, "HS-mode set vsstatus.SDT")
    lab = t.label("vs")
    t.enter("VS")
    t.emit(f"{lab}:", 0)
    d.read_sdt(t, "x9")
    t.emit("csrc sstatus, x6")
    d.read_sdt(t, "x1")
    t.leave()
    t.check("x9", 1, lab, "VS-mode sstatus.SDT shows vsstatus.SDT = 1")
    t.check("x1", 0, lab, "VS-mode sstatus.SDT after VS-mode csrc")
    check_sdt(t, lab, 0, "after VS-mode csrc", hex(d.CSR_VSSTATUS))
    lab = t.label("vs1")
    t.enter("VS")
    t.emit(f"{lab}:", 0)
    t.emit("csrs sstatus, x6")
    t.leave()
    check_sdt(t, lab, 1, "after VS-mode csrs", hex(d.CSR_VSSTATUS))
    check_sdt(t, lab, 0, "after VS-mode csrs")
    t.emit(f"csrc {hex(d.CSR_VSSTATUS)}, x6")
    d.henv_dte(t, False)
    s_teardown(t)
    tests.append(t)
    return tests


def tsbi_dte_read(t: TestFile, reg: str) -> None:
    with t.rv64_only():
        t.tsbi_csr("READ", "MENVCFG")
        t.emit(f"srli {reg}, a0, 59")
    with t.rv32_only():
        t.tsbi_csr("READ", "MENVCFGH")
        t.emit(f"srli {reg}, a0, 27")
    t.emit(f"andi {reg}, {reg}, 1")


def gen_ss_sie() -> list[TestFile]:
    tests = []
    rule_text = (
        "When the SDT bit is set to 1 by an explicit CSR write, the SIE (Supervisor Interrupt Enable) bit is cleared "
        "to 0. This clearing occurs regardless of the value written, if any, to the SIE bit by the same write. The "
        "SIE bit can only be set to 1 by an explicit CSR write if the SDT bit is being set to 0 by the same write or "
        "is already 0."
    )
    plan = (
        "1. SDT=0, SIE=1: setting SDT with csrs, csrrs, csrw and csrrw (other bits as read) leaves SDT=1, SIE=0.\n"
        "2. SDT=0, SIE=0 and SIE=1: one write of SDT=1 and SIE=1 (csrs and csrw) leaves SDT=1, SIE=0.\n"
        "3. SDT=1: csrsi, csrrsi, csrs and csrw (SDT kept 1) of SIE=1 leave SIE=0.\n"
        "4. SDT=1: one csrw of SDT=0 and SIE=1 leaves SDT=0, SIE=1; csrc of SDT then csrsi of SIE gives SIE=1.\n"
        "5. Negative: SDT=0, SIE=1: csrc of SDT and a csrw of the register as read leave SIE=1."
    )

    def body(t: TestFile, csr: str) -> None:
        """The cases above on `csr` (sstatus from S-mode or mstatus from M-mode)."""
        t.li("x6", d.SDT)
        t.li("x9", d.SDT | d.SIE)

        def start(sdt: int, sie: int) -> None:
            t.emit(f"csrc {csr}, x9  // SDT = SIE = 0")
            if sdt:
                t.emit(f"csrs {csr}, x6  // SDT = 1")
            if sie:
                t.emit(f"csrsi {csr}, 2  // SIE = 1")

        sie_after_set = 1 if MUT == "sie_kept_on_sdt_set" else 0
        for form in ("csrs", "csrrs", "csrw", "csrrw"):
            lab = t.label(form)
            start(0, 1)
            check_sie(t, lab, 1, "SIE set with SDT=0", csr)
            t.emit(f"{lab}:", 0)
            if form in ("csrs", "csrrs"):
                t.emit(f"csrrs {'x8' if form == 'csrrs' else 'x0'}, {csr}, x6")
            else:
                t.emit(f"csrr x7, {csr}")
                t.emit("or x7, x7, x6")
                t.emit(f"csrrw {'x8' if form == 'csrrw' else 'x0'}, {csr}, x7")
            check_sdt(t, lab, 1, f"{form} SDT=1", csr)
            check_sie(t, lab, sie_after_set, f"{form} SDT=1 from SIE=1", csr)
        for sie in (0, 1):
            for form in ("csrs", "csrw"):
                lab = t.label(f"both{form}")
                start(0, sie)
                t.emit(f"{lab}:", 0)
                if form == "csrs":
                    t.emit(f"csrs {csr}, x9  // SDT = SIE = 1 in one write")
                else:
                    t.emit(f"csrr x7, {csr}")
                    t.emit("or x7, x7, x9")
                    t.emit(f"csrw {csr}, x7  // SDT = SIE = 1 in one write")
                check_sdt(t, lab, 1, f"{form} of SDT=1, SIE=1 from SIE={sie}", csr)
                check_sie(t, lab, sie_after_set, f"{form} of SDT=1, SIE=1 from SIE={sie}", csr)
        for form in ("csrsi", "csrrsi", "csrs", "csrw"):
            lab = t.label(f"sdt1{form}")
            start(1, 0)
            t.emit(f"{lab}:", 0)
            if form in ("csrsi", "csrrsi"):
                t.emit(f"csrrsi {'x8' if form == 'csrrsi' else 'x0'}, {csr}, 2")
            elif form == "csrs":
                t.emit("li x7, 2")
                t.emit(f"csrs {csr}, x7")
            else:
                t.emit(f"csrr x7, {csr}")
                t.emit("ori x7, x7, 2")
                t.emit(f"csrw {csr}, x7")
            check_sie(t, lab, 1 if MUT == "sie_set_with_sdt1" else 0, f"{form} of SIE=1 with SDT=1", csr)
            check_sdt(t, lab, 1, f"{form} of SIE=1 with SDT=1", csr)
        lab = t.label("clrset")
        start(1, 0)
        t.emit(f"{lab}:", 0)
        t.emit(f"csrr x7, {csr}")
        t.emit("xor x7, x7, x6  // SDT = 0")
        t.emit("ori x7, x7, 2  // SIE = 1")
        t.emit(f"csrw {csr}, x7")
        check_sdt(t, lab, 0, "csrw of SDT=0, SIE=1 from SDT=1", csr)
        check_sie(t, lab, 0 if MUT == "sdt_clear_same_write_ignored" else 1, "csrw of SDT=0, SIE=1 from SDT=1", csr)
        lab = t.label("seq")
        start(1, 0)
        t.emit(f"{lab}:", 0)
        t.emit(f"csrc {csr}, x6")
        t.emit(f"csrsi {csr}, 2")
        check_sie(t, lab, 1, "csrc SDT, then csrsi SIE", csr)
        for neg in ("csrc", "same"):
            lab = t.label(f"neg{neg}")
            start(0, 1)
            t.emit(f"{lab}:", 0)
            if neg == "csrc":
                t.emit(f"csrc {csr}, x6")
            else:
                t.emit(f"csrr x7, {csr}")
                t.emit(f"csrw {csr}, x7")
            check_sie(t, lab, 1, f"{'csrc of SDT' if neg == 'csrc' else 'csrw as read'} with SDT=0", csr)
        t.emit(f"csrc {csr}, x9")

    # ---- sstatus_sdt_sstatus_sie_overwrite ----
    t = new_s("sstatus_sdt_sstatus_sie_overwrite")
    t.describe(
        source=SUP,
        rule_text=rule_text,
        context="S-mode writes sstatus with menvcfg.DTE=1. sie is 0 while SIE is set, so no interrupt is taken. The "
        "same cases through mstatus are in the _Sm file.",
        issues=ISSUE_1623 + "\n" + ISSUE_3057,
        plan=plan,
    )
    s_setup(t)
    t.emit("csrrw x1, sie, x0  // no S-level interrupt enabled while SIE is set")
    body(t, "sstatus")
    t.emit("csrw sie, x1")
    s_teardown(t)
    tests.append(t)

    t = new_sm("sstatus_sdt_sstatus_sie_overwrite")
    t.describe(
        source=SUP,
        rule_text=rule_text,
        context="M-mode part: the same writes through mstatus, whose SDT and SIE are the bits sstatus shows. "
        "menvcfg.DTE=1. mie is 0 while SIE is set.",
        issues=ISSUE_1623,
        plan=plan.replace("sstatus", "mstatus"),
    )
    d.dte_m(t, True)
    t.emit("csrrw x1, mie, x0")
    body(t, "mstatus")
    t.emit("csrw mie, x1")
    d.dte_m(t, False)
    tests.append(t)
    return tests


def gen_ss_dte_op() -> list[TestFile]:
    tests = []
    # ---- menvcfg_dte_op ----
    t = new_s("menvcfg_dte_op")
    t.describe(
        source=MAC,
        rule_text="The Ssdbltrp extension adds the double-trap-enable (DTE) field in menvcfg. When menvcfg.DTE is "
        "zero, the implementation behaves as though Ssdbltrp is not implemented.",
        context="Without Ssdbltrp, sstatus.SDT, vsstatus.SDT and henvcfg.DTE are read-only zero (menvcfg_dte_sdt_rdonly0), "
        "a trap into S-mode does not set SDT, no trap is a double trap, and writing SDT does not affect SIE. When "
        "DTE is cleared with SDT=1, the bit may be cleared or masked on read; after DTE is set again it reads 0 or "
        "1. sie is 0 while SIE is set.",
        issues=ISSUE_2264,
        plan="1. DTE=1, SDT=1; clearing DTE makes sstatus.SDT read 0.\n"
        "2. With DTE=0 (SDT possibly still stored as 1): an ebreak in S-mode is taken in S-mode (cause 3), not as a "
        "double trap, and sstatus.SDT at handler entry reads 0.\n"
        "3. DTE=0: csrs of SDT reads 0; with SIE=1, csrs of SDT and csrw of SDT=1, SIE=1 leave SIE=1.\n"
        "4. DTE=0: an ebreak in U-mode: SDT reads 0 at S handler entry.\n"
        "5. With H, DTE=0: henvcfg.DTE written 1 reads 0, and vsstatus.SDT written 1 reads 0; with both written 1 and "
        "breakpoints delegated to VS-mode, a VS-mode ebreak is an ordinary trap into VS-mode (cause 3), not a double "
        "trap.\n"
        "6. After DTE is set again SDT reads 0 or 1 (#2264); that is not checked.",
    )
    s_setup(t)
    sdt_s(t, True)
    lab = t.label("clr")
    t.emit(f"{lab}:", 0)
    d.dte_tsbi(t, False)
    check_sdt(t, lab, 0, "after clearing DTE with SDT=1")
    lab = win(
        t,
        "S",
        "ebreak",
        expect=16 if MUT == "dte0_double_trap" else 3,
        desc="ebreak with DTE=0 after SDT=1",
    )
    d.log_handler(t, lab, "M" if MUT == "dte0_double_trap" else "S", "ebreak with DTE=0")
    d.log_sdt(t, lab, 0, "ebreak with DTE=0")
    t.emit("csrrw x1, sie, x0")
    lab = t.label("w")
    t.emit(f"{lab}:", 0)
    sdt_s(t, True)
    check_sdt(t, lab, 1 if MUT == "dte0_sdt_writable" else 0, "csrs SDT with DTE=0")
    lab = t.label("sie")
    t.emit("csrsi sstatus, 2")
    t.emit(f"{lab}:", 0)
    sdt_s(t, True)
    check_sie(t, lab, 1, "csrs SDT with DTE=0 and SIE=1")
    t.emit("csrr x7, sstatus")
    t.li("x6", d.SDT | d.SIE)
    t.emit("or x7, x7, x6")
    t.emit("csrw sstatus, x7")
    check_sie(t, lab, 1, "csrw of SDT=1, SIE=1 with DTE=0")
    t.emit("csrci sstatus, 2")
    t.emit("csrw sie, x1")
    with t.only_if(U_OK):
        lab = win(t, "U", "ebreak", desc="ebreak with DTE=0")
        d.log_sdt(t, lab, 0, "ebreak from U-mode with DTE=0")
    with t.only_if(H):
        lab = t.label("h")
        t.emit(f"{lab}:", 0)
        d.henv_dte(t, True)
        d.read_dte(t, "x8", "henvcfg")
        t.check("x8", 0, lab, "henvcfg.DTE written 1 with menvcfg.DTE=0")
        t.li("x6", d.SDT)
        t.emit(f"csrs {hex(d.CSR_VSSTATUS)}, x6")
        check_sdt(t, lab, 0, "vsstatus.SDT written 1 with menvcfg.DTE=0", hex(d.CSR_VSSTATUS))
        d.bare_guest(t)
        t.li("x7", 1 << 3)
        t.emit(f"csrs {hex(d.CSR_HEDELEG)}, x7  // hedeleg: breakpoint -> VS")
        lab = win(t, "VS", "ebreak", expect=3, desc="ebreak with menvcfg.DTE=0, henvcfg.DTE and vsstatus.SDT written 1")
        d.log_handler(t, lab, "VS", "VS-mode ebreak with menvcfg.DTE=0")
        t.emit(f"csrw {hex(d.CSR_HEDELEG)}, x0")
        t.li("x6", d.SDT)
        t.emit(f"csrc {hex(d.CSR_VSSTATUS)}, x6")
        d.henv_dte(t, False)
    t.comment("DTE set again: SDT reads 0 or 1 (#2264), so it is not checked")
    s_teardown(t)
    tests.append(t)
    return tests


def gen_ss_trap() -> list[TestFile]:
    tests = []
    # ---- sstatus_sdt_trap ----
    t = new_s("sstatus_sdt_trap")
    t.describe(
        source=SUP,
        rule_text="When a trap is to be taken into S-mode, if the SDT bit is currently 0, it is then set to 1, and "
        "the trap is delivered as expected.",
        context="The framework delegates breakpoints, access faults, misaligned accesses and S-level interrupts to "
        "S-mode. Its S handler records sstatus on entry and returns with SRET, which clears SDT again. With H, "
        "traps from VS/VU-mode that hedeleg does not delegate (hedeleg = 0) are taken in HS-mode and set the "
        "HS-level sstatus.SDT. menvcfg.DTE=1; SDT=0 before each trap (checked).",
        plan="1. Exceptions from S-mode: ebreak, a load and a store access fault (RVMODEL_ACCESS_FAULT_ADDRESS), a "
        "misaligned load (which may also complete). Each is taken by the S handler with its own cause, sepc, stval "
        "and SPP, and SDT=1 at entry.\n"
        "2. ebreak from U-mode, and from VS- and VU-mode into HS-mode (with H): SDT=1 at entry.\n"
        "3. Supervisor software interrupt taken in S-mode (SIE=1) and in U-mode: SDT=1 at entry.\n"
        "4. After each trap, SDT reads 0.",
    )
    s_setup(t)
    sdt_exp = 0 if MUT == "trap_no_sdt_set" else 1

    def after(lab: str, desc: str, skip_if_ok: bool = False) -> None:
        def logged() -> None:
            d.log_handler(t, lab, "S", desc)
            d.log_sdt(t, lab, sdt_exp, desc)

        if skip_if_ok:
            d.if_trapped(t, logged)
        else:
            logged()
        check_sdt(t, lab, 0, f"{desc}: after the handler's SRET")

    lab = t.label("pre")
    t.emit(f"{lab}:", 0)
    check_sdt(t, lab, 0, "before the traps")
    for cls in ("ebreak", "lw_fault", "sw_fault", "misaligned"):

        def one(c: str = cls) -> None:
            lab = win(t, "S", c, desc=c)
            after(lab, f"{c} in S-mode", skip_if_ok=c == "misaligned")

        g = guard(t, cls)
        if g:
            with t.only_if(g):
                one()
        else:
            one()
    with t.only_if(U_OK):
        lab = win(t, "U", "ebreak", desc="ebreak")
        after(lab, "ebreak in U-mode")
    with t.only_if(H):
        d.bare_guest(t)
        for mode in ("VS", "VU"):
            lab = win(t, mode, "ebreak", desc="ebreak (hedeleg = 0)")
            after(lab, f"ebreak in {mode}-mode into HS-mode")
    t.emit("csrrw x1, sie, x0")
    for mode in ("S", "U"):
        with t.only_if(U_OK) if mode == "U" else t.only_if("1"):
            t.emit("csrci sstatus, 2  // SIE = 0 until the window")
            t.emit("csrsi sip, 2  // SSIP")
            t.emit("csrsi sie, 2  // SSIE")
            lab = t.label(f"ssi{mode}")
            t.allow(1)
            if mode == "S":
                t.emit(f"{lab}:", 0)
                t.emit("csrsi sstatus, 2  // SIE = 1")
            else:
                t.emit("csrci sstatus, 2")
                t.li("x7", d.SPIE)
                t.emit("csrc sstatus, x7  // SPIE = 0: SIE stays 0 in U-mode")
                t.enter("U")
                t.emit(f"{lab}:", 0)
            loop = t.label("wait")
            t.li("x9", 50)
            t.emit(f"{loop}:", 0)
            t.emit("addi x9, x9, -1", 50)
            t.emit(f"bnez x9, {loop}", 50)
            if mode == "U":
                t.leave()
            t.emit("csrci sstatus, 2")
            t.emit("csrci sip, 2")
            t.emit("csrci sie, 2")
            t.outcome(X((1 << 31) | 1, (1 << 63) | 1), lab, f"SSI in {mode}-mode", epc=False, origin=mode)
            after(lab, f"SSI in {mode}-mode")
    t.emit("csrw sie, x1")
    s_teardown(t)
    tests.append(t)
    return tests


DT_CLASSES = ["ebreak", "lw_fault", "sw_fault", "misaligned"]


def dt_window(t: TestFile, cls: str, mode: str = "S") -> str:
    """With SDT (or vsstatus.SDT for VS) = 1, one trap of class cls that would be taken in S/VS-mode. Expected:
    a double trap into M-mode (cause 16), or no trap for a misaligned load that completes."""
    exp: Expect = ["ok", 16] if cls == "misaligned" else 16
    if MUT == "unexpected_delivered_to_s" and mode == "S":
        exp = ["ok", 4, 5] if cls == "misaligned" else CLASSES[cls][2]
    return win(t, mode, cls, expect=exp, desc=f"{cls} with SDT=1")


def dt_after(t: TestFile, cls: str, lab: str, checks: Callable[[], None]) -> None:
    """Run checks only when the window trapped (a misaligned load may complete)."""
    if cls == "misaligned":
        d.if_trapped(t, checks)
    else:
        checks()


def unexp_cause(cls: str) -> list[int]:
    return [4, 5] if cls == "misaligned" else [CLASSES[cls][2]]


def gen_ss_double() -> list[TestFile]:
    tests = []

    def dt_test(
        rule: str,
        rule_text: str,
        context: str,
        plan: str,
        checks: Callable[[TestFile, str, str], None],
        required: list[str] | None = None,
        issues: str = "",
    ) -> TestFile:
        t = new_s(rule, required)
        t.describe(source=SUP, rule_text=rule_text, context=context + " " + DT_CONTEXT, issues=issues, plan=plan)
        s_setup(t)
        for cls in DT_CLASSES:

            def one(c: str = cls) -> None:
                presets(t)
                sdt_s(t, True)
                lab = dt_window(t, c)
                dt_after(t, c, lab, lambda: checks(t, c, lab))
                sdt_s(t, False)

            g = guard(t, cls)
            if g:
                with t.only_if(g):
                    one()
            else:
                one()
        s_teardown(t)
        return t

    # ---- sstatus_sdt_unexpected_trap ----
    def unexpected(t: TestFile, cls: str, lab: str) -> None:
        d.log_handler(t, lab, "S" if MUT == "unexpected_delivered_to_s" else "M", cls)
        check_presets(t, lab, cls)
        check_sdt(t, lab, 1, f"{cls}: SDT after the double trap returns")

    tests.append(
        dt_test(
            "sstatus_sdt_unexpected_trap",
            "However, if SDT is already set to 1, then this is an unexpected trap.",
            "An unexpected trap is not delivered to S-mode: scause, sepc, stval, sstatus.SPP/SPIE are not written and "
            "the S handler is not entered.",
            "1. SDT=1 in S-mode, sepc/scause/stval preset, SPP=0 and SPIE=1: an ebreak, a load and a store access "
            "fault, and a misaligned load (when it traps) are not taken by the S handler: the M handler takes "
            "them.\n"
            "2. sepc, scause, stval, SPP and SPIE keep their presets, and SDT is still 1 when the M handler returns "
            "to S-mode.",
            unexpected,
        )
    )

    # ---- sstatus_sdt_double_trap ----
    def double(t: TestFile, cls: str, lab: str) -> None:
        d.log_handler(t, lab, "M", cls)
        with t.only_if("defined(SMDBLTRP_SUPPORTED)"):
            d.log_mdt(t, lab, 0 if MUT == "double_trap_mdt0" else 1, f"{cls} double trap")

    tests.append(
        dt_test(
            "sstatus_sdt_double_trap",
            "In the event of an unexpected trap, a double-trap exception trap is delivered into M-mode.",
            "The double-trap exception is a trap into M-mode (medeleg[16] is read-only zero): the M handler takes it, "
            "with Smdbltrp it sets mstatus.MDT, and its MRET resumes S-mode after the instruction.",
            "1. SDT=1 in S-mode: an ebreak, a load and a store access fault, and a misaligned load (when it traps) "
            "are taken by the M handler (cause 16, origin S-mode).\n"
            "2. With Smdbltrp, mstatus.MDT=1 at M handler entry.\n"
            "3. Execution continues in S-mode after the instruction.",
            double,
        )
    )

    # ---- sstatus_sdt_double_trap_regs ----
    def regs(t: TestFile, cls: str, lab: str) -> None:
        # The window checked mepc = the instruction, mtval legal values and MPP/MPV = S (origin).
        d.log(t, "x15", "TRAPLOG_STATUS")
        t.li("x5", d.MPP)
        t.emit("and x15, x15, x5")
        t.check("x15", 0x1800 if MUT == "regs_mpp_m" else 0x800, lab, f"{cls}: mstatus.MPP = S at M handler entry")
        d.log(t, "x15", "TRAPLOG_STATUS")
        t.emit(f"andi x15, x15, {d.MIE}")
        t.check("x15", 0, lab, f"{cls}: mstatus.MIE = 0 at M handler entry")
        with t.only_if(H):
            with t.rv64_only():
                d.log(t, "x15", "TRAPLOG_STATUS")
            with t.rv32_only():
                d.log(t, "x15", "TRAPLOG_STATUS2")
            t.load("x5", X(d.MPV.num(32) | d.GVA.num(32), d.MPV.num(64) | d.GVA.num(64)), "MPV | GVA")
            t.emit("and x15, x15, x5")
            mpv = X(d.MPV.v32, d.MPV.v64) if MUT == "regs_mpv_set" else 0
            t.check("x15", mpv, lab, f"{cls}: MPV = 0 and GVA = 0 (from S-mode, physical address)")
            if cls == "ebreak":
                d.log(t, "x15", "TRAPLOG_TINST")
                t.check("x15", 0, lab, f"{cls}: mtinst = 0 (breakpoint)")

    tests.append(
        dt_test(
            "sstatus_sdt_double_trap_regs",
            "To deliver this trap, the hart writes registers, except mcause and mtval2, with the same information that "
            "the unexpected trap would have written if it was taken into M-mode.",
            "A trap into M-mode from S-mode writes mepc (the instruction), mtval (0 or the pc for a breakpoint, 0 or "
            "the address for an access or misaligned fault), mstatus.MPP = S, MPIE = MIE, MIE = 0, and with H "
            "MPV = 0, GVA = 0 (no guest address) and mtinst (0 for a breakpoint).",
            "1. SDT=1 in S-mode: an ebreak, a load and a store access fault, and a misaligned load (when it traps) "
            "are taken as double traps.\n"
            "2. mepc is the instruction, mtval is 0 or the pc (ebreak) or 0 or the address (faults), MPP = S, and "
            "MIE = 0 at entry.\n"
            "3. With H: MPV = 0, GVA = 0, and mtinst = 0 for the ebreak.",
            regs,
        )
    )

    # ---- sstatus_sdt_double_trap_mtval2 ----
    def mtval2(t: TestFile, cls: str, lab: str) -> None:
        d.log(t, "x15", "TRAPLOG_TVAL2")
        exp: Expect = unexp_cause(cls)
        if MUT == "mtval2_zero":
            exp = 0
        t.check("x15", exp, lab, f"{cls}: mtval2 = the unexpected trap's mcause")

    tests.append(
        dt_test(
            "sstatus_sdt_double_trap_mtval2",
            "The mtval2 register is then set to what would be otherwise written into the mcause register by the "
            "unexpected trap.",
            "The framework records mtval2 in the trap log only with H, so the test requires H; Ssdbltrp without H "
            "also has mtval2 (mtval2_Ssdbltrp) but is not tested here. The unexpected traps are exceptions, so "
            "mtval2 is the exception code with the interrupt bit 0.",
            "1. SDT=1 in S-mode: ebreak gives mtval2 = 3, a load access fault 5, a store access fault 7, and a "
            "misaligned load (when it traps) 4 or 5.",
            mtval2,
            required=["I", "S", "H", "Ssdbltrp"],
        )
    )

    # ---- sstatus_sdt_double_trap_mcause ----
    def mcause(t: TestFile, cls: str, lab: str) -> None:
        if MUT == "mcause_unexpected":
            d.log(t, "x15", "TRAPLOG_CAUSE")
            t.check("x15", unexp_cause(cls), lab, "mutant: mcause")
        d.log(t, "x15", "TRAPLOG_CAUSE")
        t.emit("srli x15, x15, 4")
        t.check("x15", 1, lab, f"{cls}: mcause = 16 (exception code 16, interrupt bit 0)")

    tests.append(
        dt_test(
            "sstatus_sdt_double_trap_mcause",
            "The mcause register is set to 16, the double-trap exception code.",
            "mcause = 16 with the interrupt bit 0, whatever the unexpected trap's own cause.",
            "1. SDT=1 in S-mode: an ebreak, a load and a store access fault, and a misaligned load (when it traps) "
            "all write mcause = 16 (the window checks the full value).",
            mcause,
        )
    )
    return tests


DT_CONTEXT = (
    "menvcfg.DTE=1 (T-SBI). The framework delegates these exceptions to S-mode (medeleg), so with SDT=1 each is an "
    "unexpected trap. Illegal instructions are not used: the framework routes them through M-mode for emulation. "
    "Fetch faults are not used: with C, the M handler reads the instruction at mepc to step past it, which faults "
    "again inside the handler."
)

PRESET = {"sepc": "ai_scratch", "scause": 0x1F, "stval": 0x5A5A5A5A}


def presets(t: TestFile) -> None:
    """S-level trap CSRs with sentinels, SPP = 0, SPIE = 1 (before SDT is set)."""
    scratch(t)
    t.emit("LA(x7, ai_scratch)", 2)
    t.emit("csrw sepc, x7")
    t.li("x7", PRESET["scause"])
    t.emit("csrw scause, x7")
    t.li("x7", PRESET["stval"])
    t.emit("csrw stval, x7")
    t.li("x7", d.SPP)
    t.emit("csrc sstatus, x7  // SPP = 0")
    t.li("x7", d.SPIE)
    t.emit("csrs sstatus, x7  // SPIE = 1")


def check_presets(t: TestFile, lab: str, cls: str) -> None:
    t.emit("csrr x8, sepc")
    t.emit("LA(x7, ai_scratch)", 2)
    t.emit("sub x8, x8, x7")
    t.check("x8", 0, lab, f"{cls}: sepc unchanged (offset from its preset)")
    t.emit("csrr x8, scause")
    scause = PRESET["scause"]
    if MUT == "unexpected_writes_scause":
        scause = CLASSES[cls][2] if cls in CLASSES else 4
    t.check("x8", scause, lab, f"{cls}: scause unchanged")
    t.emit("csrr x8, stval")
    t.check("x8", PRESET["stval"], lab, f"{cls}: stval unchanged")
    t.emit("csrr x8, sstatus")
    t.li("x7", d.SPP | d.SPIE)
    t.emit("and x8, x8, x7")
    t.check("x8", d.SPIE, lab, f"{cls}: SPP = 0 and SPIE = 1 unchanged")


def gen_ss_sret() -> list[TestFile]:
    tests = []
    # ---- sstatus_sdt_sret ----
    t = new_s("sstatus_sdt_sret")
    t.describe(
        source=SUP,
        rule_text="An SRET instruction sets the SDT bit to 0.",
        context="SRET executed in S-mode (HS-mode with H). With SPP=S the result is read right after it. In U-mode "
        "(and VS/VU with H) SDT cannot be read, so an ebreak there must be an ordinary trap into S-mode (cause 3 in "
        "the S handler); with SDT left at 1 it would be a double trap into M-mode. menvcfg.DTE=1. The VS-mode "
        "SRET and vsstatus.SDT are covered by sret_dt (H suite).",
        issues=ISSUE_2870,
        plan="1. SDT=1, SRET to S-mode (SPP=1): SDT reads 0; SDT=0, SRET to S-mode: SDT stays 0.\n"
        "2. SDT=1, SRET to U-mode: an ebreak in U-mode is taken by the S handler (cause 3).\n"
        "3. With H: SDT=1, SRET to VS-mode and to VU-mode (hedeleg = 0): an ebreak there is taken by the HS "
        "handler.",
    )
    s_setup(t)
    for start in (1, 0):
        lab = t.label("srets")
        sdt_s(t, bool(start))
        t.allow(1)
        t.emit(f"LA(x7, {lab})", 2)
        t.emit("csrw sepc, x7")
        t.li("x7", d.SPP)
        t.emit("csrs sstatus, x7  // SPP = S")
        with t.only_if(H):
            t.emit("li x7, 0x80")
            t.emit("csrc 0x600, x7  // hstatus.SPV = 0")
        t.emit("sret")
        t.emit(f"{lab}:", 0)
        d.read_sdt(t, "x8")
        t.outcome("ok", lab, f"SRET to S-mode with SDT={start}")
        t.check("x8", 1 if (MUT == "sret_keeps_sdt" and start) else 0, lab, f"SRET to S-mode with SDT={start}: SDT")
    for mode, cond in (("U", U_OK), ("VS", H), ("VU", H)):
        with t.only_if(cond):
            if mode != "U":
                d.bare_guest(t)
            sdt_s(t, True)
            lab = win(t, mode, "ebreak", desc="ebreak after SRET with SDT=1")
            d.log_handler(t, lab, "S", f"ebreak in {mode}-mode after SRET with SDT=1")
    s_teardown(t)
    tests.append(t)
    return tests


def gen_ss_vs() -> list[TestFile]:
    tests = []
    # ---- vsstatus_sdt_op ----
    t = new_s("vsstatus_sdt_op", ["I", "S", "H", "Ssdbltrp"])
    t.describe(
        source=HYP,
        rule_text="The Ssdbltrp adds an S-mode-disable-trap (SDT) field extension to address double trap (See "
        "<<supv-double-trap>>) in VS-mode.",
        context="In VS-mode the supervisor double-trap rules apply to vsstatus.SDT: a trap into VS-mode sets it, and "
        "a trap into VS-mode while it is 1 is an unexpected trap, delivered as a double-trap exception into M-mode "
        "(medeleg[16] is read-only zero), with mtval2 = the unexpected trap's cause. menvcfg.DTE=1 and "
        "henvcfg.DTE=1; hedeleg delegates breakpoints and load access faults to VS-mode. VS-mode enters through "
        "SRET from HS-mode, which leaves vsstatus.SDT alone; GOTO_SMODE leaves VS-mode through an ecall that "
        "HS-mode takes (hedeleg[10] is read-only zero). With henvcfg.DTE=0 the VS level behaves as though "
        "Ssdbltrp were not implemented (henvcfg_dte_op).",
        plan="1. vsstatus.SDT=0: an ebreak in VS-mode and in VU-mode is taken by the VS handler with vsstatus.SDT=1 at "
        "entry.\n"
        "2. vsstatus.SDT=1 (set by HS-mode), vsepc/vscause/vstval preset: an ebreak and a load access fault in "
        "VS-mode are taken by the M handler with mcause 16, origin VS (MPP=S, MPV=1), mtval2 = 3 or 5; vsepc, "
        "vscause and vstval keep their presets and vsstatus.SDT is still 1.\n"
        "3. henvcfg.DTE cleared with vsstatus.SDT=1: an ebreak in VS-mode is taken by the VS handler (cause 3).",
    )
    s_setup(t)
    d.henv_dte(t, True)
    d.bare_guest(t)
    t.li("x7", (1 << 3) | (1 << 5))
    t.emit(f"csrs {hex(d.CSR_HEDELEG)}, x7  // hedeleg: breakpoint, load access fault -> VS")
    t.li("x6", d.SDT)
    for mode in ("VS", "VU"):
        t.emit(f"csrc {hex(d.CSR_VSSTATUS)}, x6  // vsstatus.SDT = 0")
        lab = win(t, mode, "ebreak", desc="ebreak delegated to VS-mode")
        d.log_handler(t, lab, "VS", f"ebreak in {mode}-mode")
        d.log_sdt(t, lab, 0 if MUT == "vs_trap_no_sdt" else 1, f"ebreak in {mode}-mode into VS-mode")
    classes = ["ebreak", "lw_fault"]
    for cls in classes:

        def one(c: str = cls) -> None:
            t.li("x7", 0x1F)
            t.emit(f"csrw {hex(d.CSR_VSCAUSE)}, x7")
            t.li("x7", PRESET["stval"])
            t.emit(f"csrw {hex(d.CSR_VSTVAL)}, x7")
            t.emit("LA(x7, ai_scratch)", 2)
            t.emit(f"csrw {hex(d.CSR_VSEPC)}, x7")
            scratch(t)
            t.li("x6", d.SDT)
            t.emit(f"csrs {hex(d.CSR_VSSTATUS)}, x6  // vsstatus.SDT = 1")
            lab = win(t, "VS", c, expect=16, desc=f"{c} with vsstatus.SDT=1")
            d.log_handler(t, lab, "S" if MUT == "vs_double_trap_to_hs" else "M", f"{c} VS-mode double trap")
            d.log(t, "x15", "TRAPLOG_TVAL2")
            t.check("x15", CLASSES[c][2], lab, f"{c}: mtval2 = the unexpected trap's cause")
            t.emit(f"csrr x8, {hex(d.CSR_VSEPC)}")
            t.emit("LA(x7, ai_scratch)", 2)
            t.emit("sub x8, x8, x7")
            t.check("x8", 0, lab, f"{c}: vsepc unchanged (offset from its preset)")
            t.emit(f"csrr x8, {hex(d.CSR_VSCAUSE)}")
            t.check("x8", 0x1F, lab, f"{c}: vscause unchanged")
            t.emit(f"csrr x8, {hex(d.CSR_VSTVAL)}")
            t.check("x8", PRESET["stval"], lab, f"{c}: vstval unchanged")
            check_sdt(t, lab, 1, f"{c}: after the double trap", hex(d.CSR_VSSTATUS))

        g = guard(t, cls)
        if g:
            with t.only_if(g):
                one()
        else:
            one()
    t.li("x6", d.SDT)
    t.emit(f"csrs {hex(d.CSR_VSSTATUS)}, x6")
    d.henv_dte(t, False)
    lab = win(
        t,
        "VS",
        "ebreak",
        expect=16 if MUT == "henvcfg_dte0_vs_double_trap" else 3,
        desc="ebreak with henvcfg.DTE=0 after vsstatus.SDT=1",
    )
    d.log_handler(t, lab, "M" if MUT == "henvcfg_dte0_vs_double_trap" else "VS", "ebreak with henvcfg.DTE=0")
    t.emit(f"csrw {hex(d.CSR_HEDELEG)}, x0")
    t.li("x6", d.SDT)
    d.henv_dte(t, True)
    t.emit(f"csrc {hex(d.CSR_VSSTATUS)}, x6")
    d.henv_dte(t, False)
    s_teardown(t)
    tests.append(t)
    return tests


def gen_ss_xret_sm() -> list[TestFile]:
    tests = []
    for kind in ("mret", "mnret"):
        req_s = ["I", "Sm", "S", "Smdbltrp", "Ssdbltrp"] + (["Smrnmi"] if kind == "mnret" else [])
        # ---- sstatus_sdt_clr_mret_sret_Sm / sstatus_sdt_clr_mnret_Sm ----
        rule = f"sstatus_sdt_clr_{'mret_sret' if kind == 'mret' else 'mnret'}"
        t = new_sm(rule, req_s)
        if kind == "mret":
            t.describe(
                source=MAC,
                rule_text="When the smdbltrp extension is implemented, executing an mret instruction, or executing an "
                "sret instruction while the current privilege mode is M, has the following additional effects. [...] "
                "If the Ssdbltrp extension is also implemented, and the new privilege mode is U, VS, or VU, then "
                "sstatus[sdt] is also set to 0.",
                context=XRET_CONTEXT,
                issues=ISSUE_2403 + "\n" + ISSUE_2870,
                plan="1. SDT=1, MRET to U, VS and VU (with H): SDT=0 at the next M handler entry.\n"
                "2. SDT=1, MRET to S and to M: SDT stays 1.\n"
                "3. SDT=1, SRET in M-mode to U, and (with H, hstatus.SPV=1) to VS and VU: SDT=0. SRET in M-mode to S-mode "
                "is executed but SDT is not checked (#2403 and #2870 disagree).",
            )
        else:
            t.describe(
                source=MAC,
                rule_text="When the smdbltrp extension is implemented, the mnret instruction, provided by the smrnmi "
                "extension, sets the mdt bit to 0 if the new privilege mode is not M. If the ssdbltrp extension is "
                "also implemented, and the new privilege mode is U, VS, or VU, then sstatus[sdt] is also set to 0.",
                context=XRET_CONTEXT.replace("MRET", "MNRET") + " MNRET (0x70200073) is executed in M-mode without "
                "an RNMI: it returns to mnepc in the mode of mnstatus.MNPP/MNPV.",
                issues=ISSUE_2403,
                plan="1. SDT=1, MNRET to U, VS and VU (with H): SDT=0 at the next M handler entry.\n"
                "2. SDT=1, MNRET to S and to M: SDT stays 1.",
            )
        d.dte_m(t, True)
        go = d.mret_to if kind == "mret" else mnret_to
        targets = [("U", U_OK, 0), ("S", S_OK, 1), ("VS", H, 0), ("VU", H, 0)]
        for mode, cond, keep in targets:
            with t.only_if(cond):
                if mode in ("VS", "VU"):
                    d.bare_guest(t)
                t.li("x6", d.SDT)
                t.emit("csrs mstatus, x6  // SDT = 1")
                lab = t.label(f"to{mode}")
                t.allow(1)
                go(t, mode, lab)
                t.emit(f"{lab}:", 0)
                t.emit(EBREAK)
                t.leave()
                t.outcome(3, lab, f"ebreak in {mode}-mode after {kind.upper()} with SDT=1", [0, lab], origin=mode)
                exp = keep
                if mode == "U" and f"{kind}_u_keeps_sdt" == MUT:
                    exp = 1
                if mode == "S" and MUT == "mret_s_clears_sdt" and kind == "mret":
                    exp = 0
                d.log_sdt(t, lab, exp, f"{kind.upper()} to {mode}-mode with SDT=1")
                t.emit("csrc mstatus, x6")
        lab = t.label("tom")
        t.li("x6", d.SDT)
        t.emit("csrs mstatus, x6")
        t.allow(1)
        go(t, "M", lab)
        t.emit(f"{lab}:", 0)
        t.emit("csrr x8, mstatus")
        t.outcome("ok", lab, f"{kind.upper()} to M-mode")
        t.emit("srli x8, x8, 24")
        t.emit("andi x8, x8, 1")
        t.check("x8", 1, lab, f"{kind.upper()} to M-mode with SDT=1: SDT stays 1")
        t.emit("csrc mstatus, x6")
        if kind == "mret":
            with t.only_if(S_OK):
                for spp, spv, mode in ((0, 0, "U"), (1, 0, "S"), (1, 1, "VS"), (0, 1, "VU")):
                    with ExitStack() as stack:
                        if spv:
                            stack.enter_context(t.only_if(H))
                            d.bare_guest(t)
                        t.emit("csrs mstatus, x6  // SDT = 1")
                        lab = t.label(f"sret{mode}")
                        t.allow(1)
                        t.emit(f"LA(x7, {lab})", 2)
                        t.emit("csrw sepc, x7")
                        t.li("x7", d.SPP)
                        t.emit(f"{'csrs' if spp else 'csrc'} mstatus, x7  // SPP = {spp}")
                        with t.only_if(H):
                            t.emit("li x7, 0x80")
                            t.emit(f"{'csrs' if spv else 'csrc'} 0x600, x7  // hstatus.SPV = {spv}")
                        t.emit("sret  // in M-mode")
                        t.emit(f"{lab}:", 0)
                        t.emit(EBREAK)
                        t.leave()
                        t.outcome(
                            3, lab, f"ebreak in {mode}-mode after SRET in M-mode with SDT=1", [0, lab], origin=mode
                        )
                        if mode == "S":
                            t.comment("SRET in M-mode to S-mode: SDT = 0 or 1 (#2403 vs #2870), not checked")
                        else:
                            d.log_sdt(t, lab, 0, f"SRET in M-mode to {mode}-mode with SDT=1")
                        t.emit("csrc mstatus, x6")
                        if spv:
                            t.emit("li x7, 0x80")
                            t.emit("csrc 0x600, x7  // hstatus.SPV = 0")
        d.dte_m(t, False)
        tests.append(t)

        # ---- vsstatus_sdt_clr_mret_sret_Sm / vsstatus_sdt_clr_mnret_Sm ----
        rule = f"vsstatus_sdt_clr_{'mret_sret' if kind == 'mret' else 'mnret'}"
        t = new_sm(rule, req_s[:3] + ["H"] + req_s[3:])
        t.describe(
            source=MAC,
            rule_text="Additionally, if it is VU, then vsstatus[sdt] is also set to 0.",
            context=f"Continues the {kind.upper()} rule: with the new mode VU, vsstatus.SDT is also cleared; with VS it "
            "is left alone (#2403). menvcfg.DTE=1 and henvcfg.DTE=1. medeleg = 0 (M boot), so an ebreak in the "
            "guest returns to M-mode directly, and vsstatus is read there.",
            issues=ISSUE_2403,
            plan=f"1. vsstatus.SDT=1, {kind.upper()} to VU-mode: vsstatus.SDT reads 0 after an ebreak there.\n"
            f"2. vsstatus.SDT=1, {kind.upper()} to VS-, U- and S-mode and to M-mode: vsstatus.SDT stays 1.",
        )
        d.dte_m(t, True)
        d.henv_dte(t, True)
        d.bare_guest(t)
        t.li("x6", d.SDT)
        for mode in ("VU", "VS", "U", "S", "M"):
            t.emit(f"csrs {hex(d.CSR_VSSTATUS)}, x6  // vsstatus.SDT = 1")
            lab = t.label(f"to{mode}")
            t.allow(1)
            go(t, mode, lab)
            t.emit(f"{lab}:", 0)
            if mode == "M":
                t.emit("nop")
                t.outcome("ok", lab, f"{kind.upper()} to M-mode")
            else:
                t.emit(EBREAK)
                t.leave()
                t.outcome(3, lab, f"ebreak in {mode}-mode after {kind.upper()}", [0, lab], origin=mode)
            exp = 0 if mode == "VU" else 1
            if mode == "VU" and f"{kind}_vu_keeps_vssdt" == MUT:
                exp = 1
            if mode == "VS" and MUT == "mret_vs_clears_vssdt" and kind == "mret":
                exp = 0
            check_sdt(t, lab, exp, f"{kind.upper()} to {mode}-mode with vsstatus.SDT=1", hex(d.CSR_VSSTATUS))
            t.li("x6", d.SDT)
        t.emit(f"csrc {hex(d.CSR_VSSTATUS)}, x6")
        d.henv_dte(t, False)
        d.dte_m(t, False)
        tests.append(t)
    return tests


XRET_CONTEXT = (
    "The test boots to M-mode (medeleg = 0) with menvcfg.DTE=1. After the MRET, an ebreak in the new mode traps "
    "straight back to M-mode, and the M handler records mstatus (with SDT) on entry; no trap into S-mode happens "
    "in between. M-mode reads SDT directly after an MRET to M-mode."
)


def gen() -> list[TestFile]:
    return gen_smdbltrp() + gen_ssdbltrp()


def main() -> None:
    for t in gen():
        p = t.write()
        print(f"{p.relative_to(Path(__file__).resolve().parents[1])}: ~{t.ninst} instructions")


if __name__ == "__main__":
    main()
