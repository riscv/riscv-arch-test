#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate tests_ai/Sscofpmf: one test per normative rule about Sscofpmf (count overflow and mode-based
filtering).

The rules are in src/priv/sscofpmf.adoc, plus the LCOFI bits of mip/mie (machine.adoc), sip/sie
(supervisor.adoc), vsip/vsie with hideleg[13] (hypervisor.adoc), the mhpmevent*h CSRs and the interrupt
priority orders. Tests boot to S-mode and reach M-level CSRs (mhpmevent, mhpmcounter, mcountinhibit,
mcounteren, mip, mie) through T-SBI. Rules that need mideleg changes or M-mode execution are _Sm files.

Counter events are implementation-defined. The tests use the counter named by RVMODEL_HPM_COUNTER and the
event RVMODEL_MHPMEVENT_VAL, which RVMODEL_MHPMEVENT_CODE makes count one or more times in the current mode
(DUT macros, docs/ctp abstraction table). A DUT that cannot count sets RVMODEL_MHPMEVENT_VAL to 0; the
counting checks are then compiled out (#if RVMODEL_MHPMEVENT_VAL != 0), and only the event-independent
checks run (software writes of OF, xINH, counters, scountovf and the LCOFI bits).
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

SUITE = "Sscofpmf"
ISSUE = "https://github.com/riscv/riscv-isa-manual/issues/"
REQ = ["I", "S", "Sscofpmf"]
REQ_SM = ["I", "S", "Sscofpmf", "Sm"]
MARCH = "rv${XLEN}i_zicsr_zifencei"
SCOF = "src/priv/sscofpmf.adoc"
MAC = "src/priv/machine.adoc"
SUP = "src/priv/supervisor.adoc"
HYP = "src/priv/hypervisor.adoc"
H = "defined(H_SUPPORTED)"
COUNTS = "RVMODEL_MHPMEVENT_VAL != 0"
MUT = os.environ.get("AI_MUTANT", "")

# mhpmevent high-word bits (mhpmeventh on RV32, bits 63:32 of mhpmevent on RV64)
OFB = 1 << 31
INHB = {"M": 1 << 30, "S": 1 << 29, "U": 1 << 28, "VS": 1 << 27, "VU": 1 << 26}
ALL = ("M", "S", "U", "VS", "VU")
LCOF = 0x2000  # mip/mie/sip/sie bit 13
SIE = 0x2
SPIE = 0x20
MIE = 0x8
SSIP = 0x2
STIP = 0x20
SEIP = 0x200
LCOFI_S = X((1 << 31) | 13, (1 << 63) | 13)  # scause/mcause of a counter-overflow interrupt
HPM_MASK = 0xFFFFFFF8  # HPM3..HPM31 bits of mcounteren/hcounteren/scountovf

# CSR numbers of the designated counter (tests/env/check_defines.h)
EV, EVH, CT, CTH = "RVTEST_CSR_MHPMEVENT", "RVTEST_CSR_MHPMEVENTH", "RVTEST_CSR_MHPMCOUNTER", "RVTEST_CSR_MHPMCOUNTERH"
NBIT = "(1<<RVMODEL_HPM_COUNTER)"

ISSUE_1981 = (
    f"{ISSUE}1981: software may write OF directly. gfavor: \"'Count overflow' and the OF bit are related but "
    "architecturally distinct. A count overflow is a hardware event that results in setting of the OF bit by "
    'hardware. Hardware never clears the OF bit. Software, on the other hand, can freely write 0 or 1 to the OF bit."'
)
ISSUE_1800 = (
    f'{ISSUE}1800: LCOFI is a standard local interrupt; "as is true for all interrupts, the standard *ideleg-based '
    'interrupt delegation mechanism applies" (gfavor).'
)
ISSUE_1785 = (
    f'{ISSUE}1785: when AIA is implemented it overrides the base rule for hideleg[13] (ARC 2025-02-18: "when '
    'AIA is implemented, it overrides the base"). The test clears hvien[13] so the AIA alias of vsip[13] to '
    "hvip[13] is not in play, and accepts a writable hideleg[13] with AIA even without Shlcofideleg."
)
ISSUE_2287 = (
    f"{ISSUE}2287: with Smcdeleg/Ssccfg and menvcfg.CDE=1, VS/VU reads of scountovf raise virtual-instruction; "
    'with CDE=0 "Smcdeleg effectively does not exist" (gfavor). Tests clear menvcfg.CDE.'
)
ISSUE_1520 = (
    f"{ISSUE}1520: the mhpmevent*h CSRs exist for Sscofpmf so the OF/xINH bits do not take bits from the "
    "existing 32-bit event fields on RV32."
)
SW_OF_NOTE = (
    "Software writes of OF (issue 1981) are not count overflows (count_overflow_trigger), so whether a software "
    "write of OF=1 also sets LCOFIP is left open; tests wait for and clear any such LCOFIP before they rely on it. "
    '"When an OF bit is set" is read as a 0-to-1 transition: rewriting OF=1 over OF=1 (to change xINH) sets '
    'nothing. A handler clears LCOFIP while OF stays 1 ("The LCOFIP bit is cleared by software before servicing '
    'the count overflow interrupt"), which a level reading would make impossible.'
)
DELEG_NOTE = (
    'mideleg[13] is WARL: "An implementation can choose to subset the delegatable traps" '
    "(norm:medeleg_mideleg_warl), and bits for lower-level interrupts may even be read-only one "
    "(norm:mideleg_rd1_lower_level). S-mode cannot read mideleg, so the test observes it: an M-mode write of "
    "mie.LCOFIE shows in sie iff LCOFI is delegated (sip/sie bits of undelegated interrupts are read-only zero). "
    "LCOFIP is then read in sip when delegated and in mip (T-SBI) otherwise, LCOFIE is set in mie (T-SBI), and an "
    "LCOFI is expected in S/HS-mode when delegated and in M-mode otherwise."
)
COUNT_NOTE = (
    "Counting uses RVMODEL_HPM_COUNTER with event RVMODEL_MHPMEVENT_VAL, made to count in the current mode by "
    "RVMODEL_MHPMEVENT_CODE. The counter is preset with every xINH bit set, and counting is enabled only in the mode "
    "under test (M-mode stays inhibited, so the T-SBI handler is not counted). Only whether the counter moved or "
    "wrapped is checked, never by how much, so events that count every instruction or cycle also work. These checks "
    "exist only when RVMODEL_MHPMEVENT_VAL != 0 (a DUT that can count)."
)


# ---------------------------------------------------------------- helpers
DSLOT = 14  # scratch slot holding D = mideleg[13] as seen from S-mode (1: LCOFI delegated to S)


def new(rule: str, required: list[str] | None = None) -> TestFile:
    t = TestFile(SUITE, rule, required=required or REQ, march=MARCH, boot="S", pool=POOL_TRAP)
    t.extra_data += [".p2align 3", "scof_scr:", "  .fill 16, 8, 0", "scof_evw:", "  .fill 2, 8, 0"]
    probe_deleg(t)
    return t


def probe_deleg(t: TestFile) -> None:
    """S-mode cannot read mideleg (and T-SBI does not offer it). Its bit 13 is observed instead: an M-mode write of
    mie.LCOFIE shows in sie.LCOFIE iff LCOFI is delegated to S (sip/sie are restricted views of mip/mie: bits of
    undelegated interrupts are read-only zero). D (0/1) goes to slot DSLOT."""
    t.comment("D = mideleg[13]: does an M-mode write of mie.LCOFIE show in sie? (slot DSLOT)")
    t.li("x6", SIE)
    t.emit("csrc sstatus, x6")
    csr_op(t, "SET", "CSR_MIE", imm=LCOF)
    t.emit("csrr x6, sie")
    t.emit("srli x6, x6, 13")
    t.emit("andi x6, x6, 1")
    st_slot(t, "x6", DSLOT)
    csr_op(t, "CLEAR", "CSR_MIE", imm=LCOF)
    t.blank()


def ld_deleg(t: TestFile, reg: str) -> None:
    ld_slot(t, reg, DSLOT)


def new_sm(rule: str, required: list[str] | None = None) -> TestFile:
    t = TestFile(SUITE, rule, suffix="_Sm", required=required or REQ_SM, march=MARCH, boot="M", pool=POOL_TRAP)
    t.extra_data += [".p2align 3", "scof_scr:", "  .fill 16, 8, 0", "scof_evw:", "  .fill 2, 8, 0"]
    return t


def hi(*modes: str, of: bool = False) -> int:
    v = OFB if of else 0
    for m in modes:
        v |= INHB[m]
    return v


def hx(v: int) -> X:
    """A high-word value as the register value of mhpmeventh (RV32) or mhpmevent (RV64)."""
    return X(v, v << 32)


def csr_op(t: TestFile, op: str, csr: str, src: str | None = None, imm: int | str | None = None) -> None:
    """op (READ/WRITE/SET/CLEAR) on an M-level CSR: through T-SBI in S-mode tests (result in a0), or directly
    in M-mode tests (read result in a0; uses a1)."""
    if op != "READ":
        if src is not None:
            if src != "a1":
                t.emit(f"mv a1, {src}")
        else:
            t.emit(f"LI(a1, {imm})", 2)
    if t.boot == "M":
        insn = {"READ": "csrr a0, {c}", "WRITE": "csrw {c}, a1", "SET": "csrs {c}, a1", "CLEAR": "csrc {c}, a1"}[op]
        t.emit(insn.format(c=csr))
    else:
        t.emit(f"RVTEST_TSBI_CSR_ACCESS TSBI_CSR_{op}({csr})", 120)


def ev_csrs(n: int | None) -> tuple[str, str]:
    if n is None:
        return EV, EVH
    return f"0x{0x320 + n:x}", f"0x{0x720 + n:x}"


def ct_csrs(n: int | None) -> tuple[str, str]:
    if n is None:
        return CT, CTH
    return f"0x{0xB00 + n:x}", f"0x{0xB80 + n:x}"


def ev_write(t: TestFile, hv: int, event: bool = True, n: int | None = None, note: str = "") -> None:
    """mhpmevent = (hv in the high word) | (RVMODEL_MHPMEVENT_VAL if event else 0). On RV32 the low half is
    written first, so a configuration that enables counting takes effect with the mhpmeventh write."""
    lo, hic = ev_csrs(n)
    t.comment(f"mhpmevent{'' if n is None else n} = {note or hex(hv << 32)}{' | event' if event else ''}")
    with t.rv64_only():
        t.load("a1", hv << 32, "mhpmevent bits 63:32")
        if event:
            t.emit("LI(x6, RVMODEL_MHPMEVENT_VAL)", 2)
            t.emit("or a1, a1, x6")
        csr_op(t, "WRITE", lo, "a1")
    with t.rv32_only():
        csr_op(t, "WRITE", lo, imm="RVMODEL_MHPMEVENT_VAL" if event else 0)
        t.load("a1", hv, "mhpmeventh")
        csr_op(t, "WRITE", hic, "a1")


def ev_bits(t: TestFile, op: str, hv: int, n: int | None = None) -> None:
    """SET or CLEAR bits of the high word of mhpmevent."""
    lo, hic = ev_csrs(n)
    with t.rv64_only():
        t.load("a1", hv << 32)
        csr_op(t, op, lo, "a1")
    with t.rv32_only():
        t.load("a1", hv)
        csr_op(t, op, hic, "a1")


def ev_hi(t: TestFile, dst: str, n: int | None = None) -> None:
    """dst = the high word of mhpmevent (bits 63:32; OF is bit 31 of dst)."""
    lo, hic = ev_csrs(n)
    with t.rv64_only():
        csr_op(t, "READ", lo)
        t.emit(f"srli {dst}, a0, 32")
    with t.rv32_only():
        csr_op(t, "READ", hic)
        t.emit(f"mv {dst}, a0")


def of_of(t: TestFile, dst: str, n: int | None = None) -> None:
    """dst = mhpmevent.OF (0 or 1)."""
    lo, hic = ev_csrs(n)
    with t.rv64_only():
        csr_op(t, "READ", lo)
        t.emit(f"srli {dst}, a0, 63")
    with t.rv32_only():
        csr_op(t, "READ", hic)
        t.emit(f"srli {dst}, a0, 31")


def freeze(t: TestFile) -> None:
    t.comment("stop counting: set every xINH bit (OF and the event are kept)")
    ev_bits(t, "SET", hi(*ALL))


def ct_write(t: TestFile, v: int, n: int | None = None, note: str = "") -> None:
    """mhpmcounter = v (a 64-bit constant); high half first on RV32."""
    lo, hic = ct_csrs(n)
    with t.rv64_only():
        t.load("a1", v, note)
        csr_op(t, "WRITE", lo, "a1")
    with t.rv32_only():
        t.load("a1", v >> 32, f"{note} (high half)" if note else "")
        csr_op(t, "WRITE", hic, "a1")
        t.load("a1", v & 0xFFFFFFFF, f"{note} (low half)" if note else "")
        csr_op(t, "WRITE", lo, "a1")


def ct_write_slots(t: TestFile, slot_lo: int, slot_hi: int) -> None:
    """mhpmcounter = the value in scratch slots (lo, and hi on RV32)."""
    with t.rv32_only():
        ld_slot(t, "a1", slot_hi)
        csr_op(t, "WRITE", CTH, "a1")
    ld_slot(t, "a1", slot_lo)
    csr_op(t, "WRITE", CT, "a1")


def ct_read(t: TestFile, lo: str, hi_: str | None = None) -> None:
    """lo = mhpmcounter (low half on RV32); hi_ = mhpmcounterh on RV32, 0 on RV64."""
    csr_op(t, "READ", CT)
    t.emit(f"mv {lo}, a0")
    if hi_:
        with t.rv64_only():
            t.emit(f"li {hi_}, 0")
        with t.rv32_only():
            csr_op(t, "READ", CTH)
            t.emit(f"mv {hi_}, a0")


def st_slot(t: TestFile, reg: str, slot: int) -> None:
    """Store reg in scratch slot (clobbers x9)."""
    t.emit("LA(x9, scof_scr)", 2)
    t.emit(f"SREG {reg}, {slot}*REGWIDTH(x9)")


def ld_slot(t: TestFile, reg: str, slot: int) -> None:
    t.emit("LA(x9, scof_scr)", 2)
    t.emit(f"LREG {reg}, {slot}*REGWIDTH(x9)")


def code(t: TestFile) -> None:
    """RVMODEL_MHPMEVENT_CODE: makes the selected counter count in the current mode."""
    t.emit("LA(x9, scof_evw)", 2)
    t.emit("RVMODEL_MHPMEVENT_CODE(x9, x8)", 2)


def run_in(t: TestFile, mode: str) -> None:
    """Run the event code in `mode`, entered from the current mode and left through T-SBI."""
    if mode != t.cur:
        t.enter(mode)
    code(t)
    if mode != t.cur:
        t.leave()


def lcof_off(t: TestFile) -> None:
    """LCOFIE = 0 and LCOFIP = 0 in mie/mip (directly in M-mode tests; in S-mode tests through T-SBI, which works
    whether or not LCOFI is delegated, and through sie/sip, which are read-only zero when it is not)."""
    t.li("x6", LCOF)
    if t.boot == "M":
        t.emit("csrc mie, x6")
        t.emit("csrc mip, x6")
    else:
        t.emit("csrc sie, x6")
        t.emit("csrc sip, x6")
        csr_op(t, "CLEAR", "CSR_MIE", imm=LCOF)
        csr_op(t, "CLEAR", "CSR_MIP", imm=LCOF)


def lcofie_on(t: TestFile) -> None:
    """Enable LCOFI where it is routed: mie.LCOFIE through T-SBI (sie.LCOFIE is its alias when delegated)."""
    csr_op(t, "SET", "CSR_MIE", imm=LCOF)


def lcofip_clear(t: TestFile) -> None:
    """Software clears LCOFIP in its owner's view: S-mode sip when delegated (D=1), else M-mode mip (T-SBI)."""
    mpath, done = t.label("clrm"), t.label("clrdone")
    ld_deleg(t, "x6")
    t.emit(f"beqz x6, {mpath}")
    t.li("x6", LCOF)
    t.emit("csrc sip, x6")
    t.emit(f"j {done}")
    t.emit(f"{mpath}:", 0)
    csr_op(t, "CLEAR", "CSR_MIP", imm=LCOF)
    t.emit(f"{done}:", 0)


def counter_setup(t: TestFile) -> None:
    """Designated counter: every xINH set, OF=0, event selected, counter 0, mcountinhibit.HPMn = 0."""
    t.comment("setup: designated counter frozen (all xINH), OF=0, event selected, counter 0, mcountinhibit.HPMn=0")
    ev_write(t, hi(*ALL), note="all xINH")
    ct_write(t, 0, note="0")
    csr_op(t, "CLEAR", "CSR_MCOUNTINHIBIT", imm=NBIT)
    lcof_off(t)
    t.blank()


def counter_teardown(t: TestFile) -> None:
    t.blank()
    t.comment("teardown: counter frozen, OF=0, event 0, counter 0")
    ev_write(t, hi(*ALL), event=False, note="all xINH")
    ct_write(t, 0, note="0")
    lcof_off(t)


def probe_width(t: TestFile) -> None:
    """Write all ones to the counter and keep the read-back value R (its implemented bits) in slots 0 (low)
    and 1 (high; 0 on RV64). Slot 2 gets the top implemented bit of R (low word) and slot 3 its high word."""
    t.comment("R = implemented counter bits: write all ones and read back (slots 0/1); top bit of R in slots 2/3")
    ct_write(t, (1 << 64) - 1, note="all ones")
    ct_read(t, "x6", "x7")
    st_slot(t, "x6", 0)
    st_slot(t, "x7", 1)
    # top bit: hi word top = Rh ^ (Rh >> 1); lo word top = (Rh == 0) ? Rl ^ (Rl >> 1) : 0
    t.emit("srli x8, x7, 1")
    t.emit("xor x8, x8, x7")
    st_slot(t, "x8", 3)
    t.emit("srli x8, x6, 1")
    t.emit("xor x8, x8, x6")
    t.emit("seqz x1, x7")
    t.emit("neg x1, x1")
    t.emit("and x8, x8, x1")
    st_slot(t, "x8", 2)


def enable(t: TestFile, modes: tuple[str, ...], of: bool = False) -> None:
    """Count in `modes` only: mhpmevent = event | OF? | xINH for every other mode."""
    inh = tuple(m for m in ALL if m not in modes)
    ev_write(t, hi(*inh, of=of), note=f"count in {'/'.join(modes) or 'no mode'}{', OF=1' if of else ''}")


def moved(t: TestFile, dst: str) -> None:
    """dst = 1 if the counter (preset to 0) is nonzero."""
    ct_read(t, dst, "x7")
    t.emit(f"or {dst}, {dst}, x7")
    t.emit(f"snez {dst}, {dst}")


def poll_lcofip(t: TestFile, until: int, n: int = 500) -> None:
    """x8 = LCOFIP (0/1), polled until it equals `until` or a bounded number of reads pass. In S-mode tests it is
    read in sip (n reads) when LCOFI is delegated, and in mip through T-SBI (n/10 reads) when it is not."""
    br = "bnez" if until else "beqz"
    loop, done = t.label("wait"), t.label("waitdone")
    mloop, mpath = t.label("mwait"), t.label("mpath")
    if t.boot != "M":
        ld_deleg(t, "x8")
        t.emit(f"beqz x8, {mpath}")
    t.li("x9", n)
    t.emit(f"{loop}:", 0)
    t.emit(f"csrr x8, {'mip' if t.boot == 'M' else 'sip'}", n)
    t.emit("srli x8, x8, 13", n)
    t.emit("andi x8, x8, 1", n)
    t.emit(f"{br} x8, {done}", n)
    t.emit("addi x9, x9, -1", n)
    t.emit(f"bnez x9, {loop}", n)
    if t.boot != "M":
        m = max(n // 10, 5)
        t.emit(f"j {done}")
        t.emit(f"{mpath}:", 0)
        t.li("x9", m)
        t.emit(f"{mloop}:", 0)
        t.emit("RVTEST_TSBI_CSR_ACCESS TSBI_CSR_READ(CSR_MIP)", 120 * m)
        t.emit("srli x8, a0, 13", m)
        t.emit("andi x8, x8, 1", m)
        t.emit(f"{br} x8, {done}", m)
        t.emit("addi x9, x9, -1", m)
        t.emit(f"bnez x9, {mloop}", m)
    t.emit(f"{done}:", 0)


def expect_lcofip(t: TestFile, value: int, desc: str, settle: bool = True) -> None:
    """Check LCOFIP (sip when delegated, else mip): a change to `value` is awaited; a steady value is watched."""
    lab = t.label("lcofip")
    poll_lcofip(t, until=value if settle else 1 - value, n=500 if settle else 50)
    t.emit(f"{lab}:", 0)
    t.check("x8", value, lab, f"LCOFIP (sip if LCOFI is delegated, else mip) after {desc}")


def mip_lcofip(t: TestFile, dst: str) -> None:
    csr_op(t, "READ", "CSR_MIP")
    t.emit(f"srli {dst}, a0, 13")
    t.emit(f"andi {dst}, {dst}, 1")


def delay(t: TestFile, n: int = 50) -> None:
    loop = t.label("delay")
    t.li("x9", n)
    t.emit(f"{loop}:", 0)
    t.emit("addi x9, x9, -1", n)
    t.emit(f"bnez x9, {loop}", n)


def overflow_s(t: TestFile, of: bool = False, mode: str = "S") -> None:
    """Preset the counter to R (all implemented bits ones) while frozen, count in `mode` (OF preset to `of`),
    and freeze again. Needs probe_width first."""
    t.comment(f"overflow: counter = R, OF={int(of)}, count in {mode}, freeze")
    ev_write(t, hi(*ALL, of=of), note=f"all xINH, OF={int(of)}")
    ct_write_slots(t, 0, 1)
    enable(t, (mode,), of=of)
    run_in(t, mode)
    freeze(t)


# ---------------------------------------------------------------- tests
def gen() -> list[TestFile]:
    tests: list[TestFile] = []
    for f in (
        t_mhpmevent_inh_op,
        t_mhpmevent_of_op,
        t_hpmcounter_overflow,
        t_count_overflow_interrupt,
        t_count_overflow_trigger,
        t_mhpmevent_of_bit_set,
        t_lcofip_op,
        t_scountovf_op,
        t_scountovf_smode_read_access_control,
        t_scountovf_mmode_read_access,
        t_scountovf_smode_read_access,
        t_scountovf_vsmode_read_access,
        t_mip_lcofip_mie_lcofie_op,
        t_mip_lcofip_acc,
        t_mip_lcofip_reflects_overflow,
        t_sip_sie_sscofpmf,
        t_vsip_vsie_lcofi,
        t_sip_sie_priority_bit_order,
        t_intr_m_mode_pri,
        t_hsint_priority,
        t_mhpmeventh_presence,
        t_mcycleh_minstreth_mhpmh_op,
    ):
        r = f()
        tests += r if isinstance(r, list) else [r]
    return tests


def t_mhpmevent_of_op() -> TestFile:
    t = new("mhpmevent_of_op")
    t.describe(
        source=SCOF,
        rule_text="The OF bit is set when the corresponding hpmcounter overflows, and remains set until written "
        "by software.",
        context="OF is mhpmevent bit 63 (mhpmeventh bit 31 on RV32). " + COUNT_NOTE,
        issues=ISSUE_1981,
        plan="Event-independent, on the designated counter through T-SBI:\n"
        "1. Software writes OF=1 and OF=0 (full writes and set/clear of bit 63) and reads them back.\n"
        "2. With OF=1, writes of the xINH bits and of the counter (all ones, 0) leave OF=1.\n"
        "With counting (RVMODEL_MHPMEVENT_VAL != 0):\n"
        "3. OF=0, counter = R (all implemented bits ones), count in S-mode: OF reads 1.\n"
        "4. Remains set: further counting without overflow, a delay, xINH writes and a counter write leave OF=1.\n"
        "5. Software clears OF; counting without overflow leaves it 0.",
    )
    counter_setup(t)
    t.comment("1. software writes of OF")
    for of in (True, False, True):
        ev_write(t, hi(*ALL, of=of), note=f"all xINH, OF={int(of)}")
        lab = t.label("of")
        t.emit(f"{lab}:", 0)
        of_of(t, "x6")
        t.check("x6", int(of), lab, f"OF reads {int(of)} after a software write of mhpmevent with OF={int(of)}")
    for op in ("CLEAR", "SET", "CLEAR"):
        ev_bits(t, op, OFB)
        lab = t.label("ofbit")
        t.emit(f"{lab}:", 0)
        of_of(t, "x6")
        t.check(
            "x6", int(op == "SET"), lab, f"OF after a csr{'s' if op == 'SET' else 'c'} of bit 63 (mhpmeventh bit 31)"
        )
    t.comment("2. OF=1 survives writes of other fields and of the counter")
    ev_bits(t, "SET", OFB)
    for desc, emit in (
        ("clearing UINH", lambda: ev_bits(t, "CLEAR", INHB["U"])),
        ("setting UINH", lambda: ev_bits(t, "SET", INHB["U"])),
        ("writing the counter with all ones", lambda: ct_write(t, (1 << 64) - 1, note="all ones")),
        ("writing the counter with 0", lambda: ct_write(t, 0, note="0")),
    ):
        emit()
        lab = t.label("keep")
        t.emit(f"{lab}:", 0)
        of_of(t, "x6")
        exp = 0 if MUT == "of_cleared_by_write" and "counter" in desc else 1
        t.check("x6", exp, lab, f"OF stays 1 after {desc}")
    with t.only_if(COUNTS):
        probe_width(t)
        t.comment("3. overflow sets OF")
        overflow_s(t)
        lab = t.label("ovf")
        t.emit(f"{lab}:", 0)
        of_of(t, "x6")
        t.check("x6", 1, lab, "OF after the counter wrapped from R while counting in S-mode")
        t.comment("4. OF remains set")
        enable(t, ("S",), of=True)
        run_in(t, "S")
        delay(t)
        freeze(t)
        lab = t.label("remain")
        t.emit(f"{lab}:", 0)
        of_of(t, "x6")
        t.check(
            "x6", 0 if MUT == "of_not_sticky" else 1, lab, "OF stays 1 while counting continues without a new overflow"
        )
        ev_bits(t, "CLEAR", INHB["VU"])
        ev_bits(t, "SET", INHB["VU"])
        ct_write(t, 0, note="0")
        lab = t.label("remain2")
        t.emit(f"{lab}:", 0)
        of_of(t, "x6")
        t.check("x6", 1, lab, "OF stays 1 after xINH and counter writes following an overflow")
        lcof_off(t)
        t.comment("5. software clears OF; counting without overflow leaves it clear")
        ev_bits(t, "CLEAR", OFB)
        enable(t, ("S",))
        run_in(t, "S")
        freeze(t)
        lab = t.label("clr")
        t.emit(f"{lab}:", 0)
        of_of(t, "x6")
        t.check("x6", 0, lab, "OF stays 0 after a software clear and counting from 0 without overflow")
        lcof_off(t)
    counter_teardown(t)
    return t


def check_of(t: TestFile, exp: int, desc: str, n: int | None = None) -> None:
    lab = t.label("of")
    t.emit(f"{lab}:", 0)
    of_of(t, "x6", n)
    t.check("x6", exp, lab, desc)


def top_bits(t: TestFile, dst: str) -> None:
    """dst = (counter low & top-bit-low) | (counter high & top-bit-high): nonzero iff the top implemented bit of
    the counter is set (slots 2/3 from probe_width). Uses x6, x7."""
    ct_read(t, "x6", "x7")
    ld_slot(t, "x8", 2)
    t.emit("and x6, x6, x8")
    ld_slot(t, "x8", 3)
    t.emit("and x7, x7, x8")
    t.emit(f"or {dst}, x6, x7")


def t_hpmcounter_overflow() -> TestFile:
    t = new("hpmcounter_overflow")
    t.describe(
        source=SCOF,
        rule_text="Since hpmcounter values are unsigned values, overflow is defined as unsigned overflow of the "
        "implemented counter bits.",
        context="mhpmcounters are WARL with up to 64 implemented bits (mhpmcounter_warl, mhpmcounter_sz), so the "
        "test writes all ones and reads back R, the implemented bits, and the top implemented bit T. " + COUNT_NOTE,
        plan="With counting (RVMODEL_MHPMEVENT_VAL != 0), each case presets the counter while frozen, with OF=0, "
        "counts in S-mode and freezes again:\n"
        "1. Counter = R (all implemented bits ones): it wraps, so OF=1 and T reads 0.\n"
        "2. Counter = R >> 1 (the largest value with T clear, the signed maximum when 64 bits are implemented): "
        "crossing into T is not an overflow, so OF=0 and T reads 1.\n"
        "3. When more than 32 bits are implemented, counter = 2^32-1: the carry into bit 32 is not an overflow, so "
        "OF=0 and bits 63:32 read 1 (mhpmcounterh on RV32).\n"
        "4. Counter = 0: OF=0 and the counter moved.\n"
        "Assumption: one pass of the event code (and the S-mode instructions around it) makes far fewer than "
        "2^(w-1) events for w implemented bits, so a preset of R wraps once and R >> 1 does not wrap. Without "
        "counting (RVMODEL_MHPMEVENT_VAL = 0) the file has no checks.",
    )
    counter_setup(t)
    with t.only_if(COUNTS):
        probe_width(t)
        t.comment("1. wrap from R")
        overflow_s(t)
        check_of(t, 1, "OF after counting from R (all implemented bits ones)")
        lab = t.label("wrapped")
        t.emit(f"{lab}:", 0)
        top_bits(t, "x6")
        t.check(
            "x6", 0, lab, "top implemented counter bit is clear after the wrap (the counter wrapped to a small value)"
        )
        lcof_off(t)
        t.comment("2. counter = R >> 1: crossing the top bit is not an overflow")
        ld_slot(t, "x6", 0)
        ld_slot(t, "x7", 1)
        t.emit("srli x6, x6, 1")
        with t.rv32_only():
            t.emit("slli x8, x7, 31")
            t.emit("or x6, x6, x8")
        t.emit("srli x7, x7, 1")
        st_slot(t, "x6", 4)
        st_slot(t, "x7", 5)
        ev_write(t, hi(*ALL), note="all xINH, OF=0")
        ct_write_slots(t, 4, 5)
        enable(t, ("S",))
        run_in(t, "S")
        freeze(t)
        check_of(
            t,
            1 if MUT == "signed_overflow" else 0,
            "OF after counting from R >> 1 (top bit crossed, no unsigned overflow)",
        )
        lab = t.label("topset")
        t.emit(f"{lab}:", 0)
        top_bits(t, "x6")
        t.emit("snez x6, x6")
        t.check("x6", 1, lab, "top implemented counter bit is set after counting from R >> 1")
        lcof_off(t)
        t.comment("3. more than 32 implemented bits: counter = 2^32-1, the carry into bit 32 is not an overflow")
        ld_slot(t, "x1", 0)
        with t.rv64_only():
            t.emit("srli x1, x1, 32")
        with t.rv32_only():
            ld_slot(t, "x1", 1)

        def wide() -> None:
            ev_write(t, hi(*ALL), note="all xINH, OF=0")
            ct_write(t, 0xFFFFFFFF, note="2^32-1")
            enable(t, ("S",))
            run_in(t, "S")
            freeze(t)
            check_of(
                t, 1 if MUT == "overflow_32" else 0, "OF after counting from 2^32-1 with more than 32 implemented bits"
            )
            lab = t.label("carry")
            t.emit(f"{lab}:", 0)
            ct_read(t, "x6", "x7")
            with t.rv64_only():
                t.emit("srli x7, x6, 32")
            t.check("x7", 1, lab, "counter bits 63:32 read 1 after the carry out of bit 31")

        t.either("x1", wide, lambda: t.comment("32 or fewer implemented bits: case 1 covers bit 31"))
        lcof_off(t)
        t.comment("4. counting from 0: no overflow")
        ev_write(t, hi(*ALL), note="all xINH, OF=0")
        ct_write(t, 0, note="0")
        enable(t, ("S",))
        run_in(t, "S")
        freeze(t)
        check_of(t, 0, "OF after counting from 0")
        lab = t.label("mv")
        t.emit(f"{lab}:", 0)
        moved(t, "x6")
        t.check("x6", 1, lab, "the counter moved while counting in S-mode")
    counter_teardown(t)
    return t


def lcof_window_s(t: TestFile, taken: bool, desc: str, mode: str = "S", of: bool = False) -> None:
    """Counter preset to R with OF=`of`, mie.LCOFIE=1 (= sie.LCOFIE when delegated); count in `mode` inside a trap
    window (sstatus.SIE=1 in S-mode, SIE=0 for U/VS-mode) and wait 500 iterations ("eventually"); the LCOFI is
    taken iff `taken`: in S/HS when delegated, in M otherwise (always enabled below M). Either way the cause is
    interrupt | 13 and the trap comes from `mode`."""
    ev_write(t, hi(*ALL, of=of), note=f"all xINH, OF={int(of)}")
    ct_write_slots(t, 0, 1)
    lcof_off(t)
    t.li("x6", SIE | SPIE)
    t.emit("csrc sstatus, x6")
    lcofie_on(t)
    lab = t.label(f"int{mode}")
    t.allow(1)
    if mode == "S":
        t.emit(f"{lab}:", 0)
        t.li("x6", SIE)
        t.emit("csrs sstatus, x6")
        enable(t, ("S",), of=of)
        code(t)
        delay(t, 500)
        t.li("x6", SIE)
        t.emit("csrc sstatus, x6")
    else:
        enable(t, (mode,), of=of)
        t.enter(mode)
        t.emit(f"{lab}:", 0)
        code(t)
        delay(t, 500)
        t.leave()
    freeze(t)
    lcof_off(t)
    t.outcome(
        LCOFI_S if taken else "ok",
        lab,
        f"{desc}: LCOFI {'must' if taken else 'must not'} be taken (S/HS if delegated, else M)",
        epc=False,
        origin=mode,
    )


def t_count_overflow_interrupt() -> TestFile:
    t = new("count_overflow_interrupt")
    t.describe(
        source=SCOF,
        rule_text='If an hpmcounter overflows while the associated OF bit is zero, then a "count overflow '
        'interrupt request" is generated. If the OF bit is one, then no interrupt request is generated. '
        "Consequently the OF bit also functions as a count overflow interrupt disable for the associated "
        "hpmcounter.",
        context="The request is LCOFI, bit 13 of mip/sip. " + DELEG_NOTE + " " + COUNT_NOTE + " " + SW_OF_NOTE,
        issues=ISSUE_1981 + "\n" + ISSUE_1800,
        plan="With counting (RVMODEL_MHPMEVENT_VAL != 0), counter preset to R (all implemented bits ones):\n"
        "1. OF=0, LCOFIE=0: after the wrap LCOFIP becomes 1.\n"
        "2. OF=1 (written by software; any LCOFIP it caused is cleared first): after the wrap sip.LCOFIP stays 0 "
        "and OF stays 1.\n"
        "3. OF=0, sie.LCOFIE=1, sstatus.SIE=1, counting in S: the LCOFI is taken in S (scause = interrupt | 13).\n"
        "4. Same with OF=1: no interrupt.\n"
        "5. OF=0, sie.LCOFIE=1, counting in U only: the LCOFI is taken from U into S.\n"
        "6. With H, hideleg[13]=0: OF=0, counting in VS only: the LCOFI is taken from VS into HS.\n"
        "Each interrupt window waits 500 iterations after the event code.",
    )
    counter_setup(t)
    with t.only_if(COUNTS):
        probe_width(t)
        t.comment("1. OF=0: a request")
        overflow_s(t)
        expect_lcofip(t, 0 if MUT == "no_request" else 1, "a wrap with OF=0")
        lcof_off(t)
        t.comment("2. OF=1: no request")
        ev_write(t, hi(*ALL, of=True), note="all xINH, OF=1")
        poll_lcofip(t, 1)
        lcof_off(t)
        overflow_s(t, of=True)
        expect_lcofip(t, 1 if MUT == "of1_requests" else 0, "a wrap with OF=1", settle=MUT == "of1_requests")
        check_of(t, 1, "OF stays 1 after a wrap with OF=1")
        lcof_off(t)
        t.comment("3. OF=0, LCOFI enabled in S")
        lcof_window_s(t, MUT != "no_request", "S-mode, OF=0, sie.LCOFIE=1, sstatus.SIE=1")
        t.comment("4. OF=1, LCOFI enabled in S")
        ev_write(t, hi(*ALL, of=True), note="all xINH, OF=1")
        poll_lcofip(t, 1)
        lcof_off(t)
        lcof_window_s(t, MUT == "of1_requests", "S-mode, OF=1, sie.LCOFIE=1, sstatus.SIE=1", of=True)
        t.comment("5. OF=0, counting in U-mode")
        lcof_window_s(t, MUT != "no_request", "U-mode, OF=0, sie.LCOFIE=1", mode="U")
        with t.only_if(H):
            t.comment("6. OF=0, counting in VS-mode, LCOFI not delegated to VS")
            t.li("x6", LCOF)
            t.emit("csrc CSR_HIDELEG, x6")
            lcof_window_s(t, MUT != "no_request", "VS-mode, OF=0, sie.LCOFIE=1, hideleg[13]=0", mode="VS")
    counter_teardown(t)
    return t


def save_csr(t: TestFile, csr: str, slot: int) -> None:
    csr_op(t, "READ", csr)
    st_slot(t, "a0", slot)


def restore_csr(t: TestFile, csr: str, slot: int) -> None:
    ld_slot(t, "a1", slot)
    csr_op(t, "WRITE", csr, "a1")


def scountovf_m(t: TestFile, dst: str) -> None:
    """dst = scountovf read in M-mode (T-SBI in S-mode tests)."""
    csr_op(t, "READ", "CSR_SCOUNTOVF")
    t.emit(f"mv {dst}, a0")


def t_count_overflow_trigger() -> TestFile:
    t = new("count_overflow_trigger")
    t.describe(
        source=SCOF,
        rule_text="Count overflow never results from writes to the mhpmcounter_n_ or mhpmevent_n_ registers, only "
        "from hardware increments of counter registers.",
        context="A count overflow sets OF and requests LCOFI (mhpmevent_of_op, count_overflow_interrupt). "
        "Event-independent: nothing may count. mcountinhibit (WARL, possibly absent) is set for every HPM counter, "
        "and every mhpmevent written keeps MINH and SINH set; the test runs only in S and M (T-SBI), so U/VS/VU "
        "may be left uninhibited.",
        plan="1. For each of mhpmcounter3..31 (OF=0, every xINH set, event 0): write all ones, then 0 (a wrap by "
        "writing); on RV32 also the low half to all ones, the high half to all ones, then the low half to 0.\n"
        "2. Afterwards no OF bit is set (scountovf read in M-mode and the designated counter's mhpmevent), "
        "mip.LCOFIP (M-mode read) is 0 and sip.LCOFIP stays 0.\n"
        "3. Writes of the designated mhpmevent (event on and off, xINH patterns that keep MINH and SINH set) with the "
        "counter at all ones leave OF=0 and LCOFIP=0.\n"
        "mcountinhibit is restored at the end.",
    )
    lcof_off(t)
    save_csr(t, "CSR_MCOUNTINHIBIT", 8)
    csr_op(t, "SET", "CSR_MCOUNTINHIBIT", imm=HPM_MASK)
    t.comment("1. every counter: OF=0, then written across the wrap")
    for n in range(3, 32):
        ev_write(t, hi(*ALL), event=False, n=n, note="all xINH, OF=0")
        ct_write(t, (1 << 64) - 1, n=n, note="all ones")
        ct_write(t, 0, n=n, note="0")
        with t.rv32_only():
            csr_op(t, "WRITE", f"0x{0xB00 + n:x}", imm=-1)
            csr_op(t, "WRITE", f"0x{0xB80 + n:x}", imm=-1)
            csr_op(t, "WRITE", f"0x{0xB00 + n:x}", imm=0)
    t.comment("2. no OF, no LCOFIP")
    lab = t.label("scountovf")
    t.emit(f"{lab}:", 0)
    scountovf_m(t, "x6")
    t.li("x7", -8)
    t.emit("and x6, x6, x7")
    t.check(
        "x6",
        NBIT if MUT == "write_overflow" else 0,
        lab,
        "scountovf (M-mode read) after counter writes across the wrap",
    )
    lab = t.label("mip")
    t.emit(f"{lab}:", 0)
    mip_lcofip(t, "x6")
    t.check("x6", 0, lab, "mip.LCOFIP after counter writes across the wrap")
    expect_lcofip(t, 0, "counter writes across the wrap", settle=False)
    t.comment("3. mhpmevent writes on the designated counter (counter all ones, counting inhibited)")
    ev_write(t, hi(*ALL), note="all xINH, OF=0")
    ct_write(t, (1 << 64) - 1, note="all ones")
    for hv, note in (
        (hi("M", "S"), "MINH|SINH (U/VS/VU not entered)"),
        (hi("M", "S", "U"), "MINH|SINH|UINH"),
        (hi(*ALL), "all xINH"),
    ):
        ev_write(t, hv, note=note)
        ev_write(t, hv, event=False, note=note)
    check_of(t, 0, "OF after mhpmevent writes with the counter at all ones")
    expect_lcofip(t, 0, "mhpmevent writes", settle=False)
    t.comment("restore")
    for n in range(3, 32):
        ct_write(t, 0, n=n, note="0")
    restore_csr(t, "CSR_MCOUNTINHIBIT", 8)
    counter_teardown(t)
    return t


def other_counters_off(t: TestFile) -> None:
    """Save mcountinhibit (slot 8), inhibit every HPM counter in mcountinhibit (which may be absent), and stop every
    counter through its mhpmevent too: every xINH set, event 0, OF=0. counter_setup then re-arms the designated one."""
    save_csr(t, "CSR_MCOUNTINHIBIT", 8)
    csr_op(t, "SET", "CSR_MCOUNTINHIBIT", imm=HPM_MASK)
    t.comment("every mhpmevent: all xINH, event 0, OF=0")
    for n in range(3, 32):
        ev_write(t, hi(*ALL), event=False, n=n, note="all xINH, OF=0")


def t_mhpmevent_of_bit_set() -> TestFile:
    t = new("mhpmevent_of_bit_set")
    t.describe(
        source=SCOF,
        rule_text="Generation of a count-overflow-interrupt request by an hpmcounter sets the associated OF bit.",
        context=DELEG_NOTE
        + " "
        + COUNT_NOTE
        + " The other HPM counters are stopped (mcountinhibit, and every xINH set with event 0 in "
        "their mhpmevents) and their OF bits cleared, so only the associated OF may change.",
        plan="With counting (RVMODEL_MHPMEVENT_VAL != 0): OF=0, counter = R (all implemented bits ones), count in "
        "S-mode until it wraps (a request):\n"
        "1. The designated mhpmevent.OF reads 1.\n"
        "2. scountovf read in M-mode is exactly the designated counter's bit (no other OF set).\n"
        "3. LCOFIP becomes 1 (the request that set OF).",
    )
    other_counters_off(t)
    counter_setup(t)
    with t.only_if(COUNTS):
        probe_width(t)
        overflow_s(t)
        check_of(t, 0 if MUT == "of_not_set" else 1, "OF after the counter wrapped with OF=0")
        lab = t.label("only")
        t.emit(f"{lab}:", 0)
        scountovf_m(t, "x6")
        t.li("x7", -8)
        t.emit("and x6, x6, x7")
        t.check("x6", NBIT, lab, "scountovf (M-mode read): only the designated counter's OF is set")
        expect_lcofip(t, 1, "the wrap")
        lcof_off(t)
    restore_csr(t, "CSR_MCOUNTINHIBIT", 8)
    counter_teardown(t)
    return t


def t_lcofip_op() -> TestFile:
    t = new("lcofip_op")
    t.describe(
        source=SCOF,
        rule_text="When an OF bit is set, it eventually, but not necessarily immediately, sets the LCOFIP bit in "
        "the mip/sip registers.",
        context='The surrounding text: "The LCOFIP bit is cleared by software before servicing the count overflow '
        'interrupt resulting from one or more count overflows." So LCOFIP is set by the OF transition, and once '
        "cleared it stays clear while OF remains 1. " + COUNT_NOTE + " " + SW_OF_NOTE,
        issues=ISSUE_1981,
        plan="With counting (RVMODEL_MHPMEVENT_VAL != 0), sie.LCOFIE=0:\n"
        "1. An overflow from OF=0 sets OF; LCOFIP becomes 1 within a bounded wait, and mip.LCOFIP (M-mode read) "
        "is 1.\n"
        "2. LCOFIP stays 1 across a delay.\n"
        "3. Software clears LCOFIP (S-mode in sip if delegated, else M-mode in mip): it reads 0 and stays 0 while OF "
        "is still 1.\n"
        "4. Software clears OF; a second overflow sets OF and LCOFIP again.",
    )
    counter_setup(t)
    with t.only_if(COUNTS):
        probe_width(t)
        overflow_s(t)
        expect_lcofip(t, 1, "OF set by an overflow")
        lab = t.label("mip")
        t.emit(f"{lab}:", 0)
        mip_lcofip(t, "x6")
        t.check("x6", 1, lab, "mip.LCOFIP (M-mode read) after OF was set by an overflow")
        expect_lcofip(t, 1, "a further delay", settle=False)
        t.comment("3. software clears LCOFIP while OF=1 (S-mode sip if delegated, else M-mode mip)")
        lcofip_clear(t)
        if MUT == "lcofip_level":
            expect_lcofip(t, 1, "clearing LCOFIP while OF is still 1")
        else:
            expect_lcofip(t, 0, "clearing LCOFIP while OF is still 1", settle=False)
        check_of(t, 1, "OF is still 1 after LCOFIP was cleared")
        t.comment("4. a second overflow after OF is cleared")
        overflow_s(t)
        expect_lcofip(t, 1, "a second overflow")
        lcof_off(t)
    counter_teardown(t)
    return t


def t_mip_lcofip_reflects_overflow() -> list[TestFile]:
    t = new("mip_lcofip_reflects_overflow")
    t.describe(
        source=MAC,
        rule_text="[lcofip] reflects the occurrence of a local counter-overflow overflow interrupt request resulting "
        "from any of the mhpmevent_n_.OF bits being set.",
        context="mip.LCOFIP is read here in M-mode (T-SBI), whatever mideleg[13] holds. The _Sm file covers counting "
        "in M-mode. " + DELEG_NOTE + " " + COUNT_NOTE,
        plan="With counting (RVMODEL_MHPMEVENT_VAL != 0):\n"
        "1. Counting from 0 (no overflow, OF=0): mip.LCOFIP stays 0.\n"
        "2. A wrap from R with OF=0: mip.LCOFIP becomes 1 (awaited in sip or mip, then read in M-mode).\n"
        "3. After LCOFIP is cleared, mip.LCOFIP reads 0.",
    )
    counter_setup(t)
    with t.only_if(COUNTS):
        probe_width(t)
        t.comment("1. counting without an overflow")
        ev_write(t, hi(*ALL), note="all xINH, OF=0")
        ct_write(t, 0, note="0")
        enable(t, ("S",))
        run_in(t, "S")
        freeze(t)
        poll_lcofip(t, 1, 50)
        lab = t.label("noovf")
        t.emit(f"{lab}:", 0)
        mip_lcofip(t, "x6")
        t.check("x6", 1 if MUT == "lcofip_on_count" else 0, lab, "mip.LCOFIP after counting without an overflow")
        t.comment("2. a wrap")
        overflow_s(t)
        poll_lcofip(t, 1)
        lab = t.label("ovf")
        t.emit(f"{lab}:", 0)
        mip_lcofip(t, "x6")
        t.check("x6", 1, lab, "mip.LCOFIP (M-mode read) after a wrap with OF=0")
        lcof_off(t)
        lab = t.label("clr")
        t.emit(f"{lab}:", 0)
        mip_lcofip(t, "x6")
        t.check("x6", 0, lab, "mip.LCOFIP (M-mode read) after LCOFIP was cleared")
    counter_teardown(t)

    m = new_sm("mip_lcofip_reflects_overflow")
    m.describe(
        source=MAC,
        rule_text=t.doc["rule_text"],
        context="M-mode part: counting in M-mode only, with mideleg[13] cleared where it is writable (it is WARL: "
        "norm:medeleg_mideleg_warl, norm:mideleg_rd1_lower_level). mip.LCOFIP must reflect the request whether or "
        "not LCOFI is delegated; mie.LCOFIE=0, and a delegated interrupt is never taken in M, so no interrupt is "
        "taken. mideleg is restored. " + COUNT_NOTE,
        plan="With counting (RVMODEL_MHPMEVENT_VAL != 0), mideleg[13] cleared (if writable):\n"
        "1. Counter = R, OF=0, count in M-mode: mip.LCOFIP becomes 1 within a bounded wait, and OF is 1.\n"
        "2. Clearing mip.LCOFIP reads back 0.",
    )
    counter_setup(m)
    with m.only_if(COUNTS):
        m.emit("csrr x6, mideleg")
        st_slot(m, "x6", 12)
        m.li("x6", LCOF)
        m.emit("csrc mideleg, x6")
        probe_width(m)
        overflow_s(m, mode="M")
        loop, done = m.label("wait"), m.label("waitdone")
        m.li("x9", 500)
        m.emit(f"{loop}:", 0)
        m.emit("csrr x8, mip", 500)
        m.emit("srli x8, x8, 13", 500)
        m.emit("andi x8, x8, 1", 500)
        m.emit(f"bnez x8, {done}", 500)
        m.emit("addi x9, x9, -1", 500)
        m.emit(f"bnez x9, {loop}", 500)
        m.emit(f"{done}:", 0)
        lab = m.label("mip")
        m.emit(f"{lab}:", 0)
        m.check(
            "x8", 0 if MUT == "lcofip_needs_deleg" else 1, lab, "mip.LCOFIP after a wrap in M-mode with mideleg[13]=0"
        )
        check_of(m, 1, "OF after the wrap in M-mode")
        lcof_off(m)
        lab = m.label("clr")
        m.emit(f"{lab}:", 0)
        m.emit("csrr x8, mip")
        m.emit("srli x8, x8, 13")
        m.emit("andi x8, x8, 1")
        m.check("x8", 0, lab, "mip.LCOFIP after M-mode cleared it")
        ld_slot(m, "x6", 12)
        m.emit("csrw mideleg, x6")
    counter_teardown(m)
    return [t, m]


def t_mhpmevent_inh_op() -> list[TestFile]:
    t = new("mhpmevent_inh_op")
    t.describe(
        source=SCOF,
        rule_text="Each of the five xINH bits, when set, inhibit counting of events while in privilege mode x. "
        "All-zeroes for these bits results in counting of events in all modes.",
        context='Bits 62:58 of mhpmevent (mhpmeventh 30:26 on RV32) are MINH, SINH, UINH, VSINH, VUINH. "For each '
        'xINH bit, if the associated privilege mode is not implemented, the bit is read-only zero", so VSINH and '
        "VUINH are writable only with H. The test boots to S and enters U, VS and VU with sret, returning through "
        "T-SBI (an ecall handled in S/HS and M; hedeleg[8] is cleared so a VU ecall skips VS). A mode the hart passes through on the way is never the only "
        "uninhibited mode in a 'must not count' case. The _Sm file covers MINH. " + COUNT_NOTE,
        plan="1. Writability on the designated counter: each xINH bit alone, and all five, read back (VSINH/VUINH "
        "read-only zero without H).\n"
        "With counting (RVMODEL_MHPMEVENT_VAL != 0), the counter preset to 0 while frozen, the event code run in "
        "mode x, then frozen and checked for movement:\n"
        "2. x = S: only S uninhibited: moves; only U (or only VS/VU) uninhibited: does not move; SINH and MINH set, "
        "U/VS/VU clear (modes not entered): does not move; all xINH clear: moves.\n"
        "3. x = U: only U: moves; SINH/MINH/UINH set, VS/VU clear: does not move; all clear: moves.\n"
        "4. With H, x = VS: only VS: moves; only U or only VU: does not move; VSINH/SINH/MINH set, U/VU clear: does "
        "not move; all clear: moves. x = VU: only VU: moves; only U: does not move; VUINH/SINH/MINH set, U clear: "
        "does not move; all clear: moves.",
    )
    counter_setup(t)
    t.comment("1. writability of the xINH bits")
    inh_mask = hi(*ALL)
    for modes in [(m,) for m in ALL] + [ALL]:
        ev_write(t, hi(*modes), note="|".join(f"{m}INH" for m in modes))
        lab = t.label("inh")
        t.emit(f"{lab}:", 0)
        ev_hi(t, "x6")
        t.li("x7", inh_mask)
        t.emit("and x6, x6, x7")
        noh = hi(*[m for m in modes if m not in ("VS", "VU")])
        if any(m in ("VS", "VU") for m in modes):
            with t.only_if(H):
                t.check("x6", hi(*modes), lab, f"xINH bits read back after writing {'|'.join(modes)}INH (with H)")
            with t.only_if("!" + H):
                t.check(
                    "x6",
                    noh,
                    lab,
                    f"xINH bits read back after writing {'|'.join(modes)}INH (no H: VS/VUINH read-only 0)",
                )
        else:
            t.check("x6", hi(*modes), lab, f"xINH bits read back after writing {modes[0]}INH")

    def case(x: str, uninh: tuple[str, ...], exp: int, desc: str) -> None:
        if MUT == "sinh_ignored" and x == "S" and "S" not in uninh and "M" not in uninh and set(uninh) >= {"U"}:
            exp = 1
        if MUT == "uinh_ignored" and x == "U" and "U" not in uninh and "VS" in uninh:
            exp = 1
        if MUT == "vs_uses_sinh" and x == "VS" and uninh == ("VS",):
            exp = 0
        t.comment(f"x={x}: count in {'/'.join(uninh) or 'no mode'}")
        ev_write(t, hi(*ALL), note="all xINH")
        ct_write(t, 0, note="0")
        enable(t, uninh)
        run_in(t, x)
        freeze(t)
        lab = t.label(f"m{x}")
        t.emit(f"{lab}:", 0)
        moved(t, "x6")
        t.check("x6", exp, lab, f"counter moved (1) or not (0): event code in {x}-mode, {desc}")

    with t.only_if(H):
        t.comment("hedeleg[8]=0: a VU-mode ecall (the T-SBI return) goes to HS-mode, not through VS-mode")
        t.li("x6", 0x100)
        t.emit("csrc CSR_HEDELEG, x6")
    with t.only_if(COUNTS):
        case("S", ("S",), 1, "only S uninhibited")
        case("S", ("U",), 0, "only U uninhibited")
        case("S", ("U", "VS", "VU"), 0, "SINH and MINH set")
        case("S", ALL, 1, "all xINH clear")
        case("U", ("U",), 1, "only U uninhibited")
        case("U", ("VS", "VU"), 0, "UINH, SINH and MINH set")
        case("U", ALL, 1, "all xINH clear")
        with t.only_if(H):
            case("S", ("VS", "VU"), 0, "only VS and VU uninhibited")
            case("VS", ("VS",), 1, "only VS uninhibited")
            case("VS", ("U",), 0, "only U uninhibited")
            case("VS", ("VU",), 0, "only VU uninhibited")
            case("VS", ("U", "VU"), 0, "VSINH, SINH and MINH set")
            case("VS", ALL, 1, "all xINH clear")
            case("VU", ("VU",), 1, "only VU uninhibited")
            case("VU", ("U",), 0, "only U uninhibited")
            case("VU", ("U", "VS"), 0, "VUINH, SINH and MINH set")
            case("VU", ALL, 1, "all xINH clear")
    counter_teardown(t)

    m = new_sm("mhpmevent_inh_op")
    m.describe(
        source=SCOF,
        rule_text=t.doc["rule_text"],
        context="M-mode part (MINH): the test boots to M-mode and never leaves it; mhpmevent is written directly. "
        "Counting uses RVMODEL_HPM_COUNTER with event RVMODEL_MHPMEVENT_VAL, made to count by "
        "RVMODEL_MHPMEVENT_CODE; the counter is preset to 0 with every xINH set and only movement is checked. These "
        "checks exist only when RVMODEL_MHPMEVENT_VAL != 0.",
        plan="With counting (RVMODEL_MHPMEVENT_VAL != 0), the event code run in M-mode:\n"
        "1. Only M uninhibited: moves.\n"
        "2. Only S uninhibited: does not move.\n"
        "3. MINH set, every other xINH clear: does not move.\n"
        "4. All xINH clear: moves.",
    )
    counter_setup(m)
    with m.only_if(COUNTS):
        for uninh, exp, desc in (
            (("M",), 1, "only M uninhibited"),
            (("S",), 0, "only S uninhibited"),
            (("S", "U", "VS", "VU"), 1 if MUT == "minh_ignored" else 0, "MINH set, the others clear"),
            (ALL, 1, "all xINH clear"),
        ):
            m.comment(f"count in {'/'.join(uninh)}")
            ev_write(m, hi(*ALL), note="all xINH")
            ct_write(m, 0, note="0")
            enable(m, uninh)
            code(m)
            freeze(m)
            lab = m.label("mM")
            m.emit(f"{lab}:", 0)
            moved(m, "x6")
            m.check("x6", exp, lab, f"counter moved (1) or not (0): event code in M-mode, {desc}")
    counter_teardown(m)
    return [t, m]


# ---------------------------------------------------------------- scountovf
P_A = 0x55555550
P_B = 0xAAAAAAA8


def of_pattern(t: TestFile, pattern: int) -> None:
    """Software-write OF of every mhpmevent3..31: bit n of pattern."""
    t.comment(f"OF pattern {pattern:#010x}")
    for n in range(3, 32):
        ev_bits(t, "SET" if pattern >> n & 1 else "CLEAR", OFB, n=n)


def ofm(t: TestFile, slot: int = 6) -> None:
    """Scratch slot = the mask of OF bits read back from mhpmevent3..31 (bit n = mhpmevent_n_.OF). Uses x1."""
    t.comment("OF mask read back from every mhpmevent")
    t.emit("li x1, 0")
    for n in range(3, 32):
        of_of(t, "x6", n)
        t.emit(f"slli x6, x6, {n}")
        t.emit("or x1, x1, x6")
    st_slot(t, "x1", slot)


def counteren(t: TestFile, csr: str, pattern: int | str, slot: int) -> None:
    """Write the HPM bits of mcounteren (T-SBI) or hcounteren (HS) to pattern; keep the HPM bits read back."""
    t.comment(f"{csr} HPM bits = {pattern if isinstance(pattern, str) else hex(pattern)}")
    if csr == "mcounteren":
        csr_op(t, "CLEAR", "CSR_MCOUNTEREN", imm=HPM_MASK)
        csr_op(t, "SET", "CSR_MCOUNTEREN", imm=pattern)
        csr_op(t, "READ", "CSR_MCOUNTEREN")
        t.emit("mv x6, a0")
    else:
        t.emit(f"LI(x6, {HPM_MASK})", 2)
        t.emit(f"csrc CSR_{csr.upper()}, x6")
        t.emit(f"LI(x6, {pattern})", 2)
        t.emit(f"csrs CSR_{csr.upper()}, x6")
        t.emit(f"csrr x6, CSR_{csr.upper()}")
    t.emit(f"LI(x7, {HPM_MASK})", 2)
    t.emit("and x6, x6, x7")
    st_slot(t, "x6", slot)


def expect_scountovf(t: TestFile, reg: str, slots: list[int], lab: str, desc: str) -> None:
    """Check reg (a scountovf value) == AND of the masks in slots, ignoring bits 2:0 (no OF bits there); on RV64
    bits 63:32 must be 0 (32-bit register). Uses x1, x7, x8 (reg is copied first)."""
    t.emit(f"mv x1, {reg}")
    ld_slot(t, "x8", slots[0])
    for s in slots[1:]:
        ld_slot(t, "x7", s)
        t.emit("and x8, x8, x7")
    t.emit("xor x8, x8, x1")
    t.emit("andi x8, x8, -8")
    t.check("x8", 0, lab, f"{desc}: scountovf XOR expected (bits 2:0 ignored) is 0")


def cde_off(t: TestFile) -> None:
    """With Smcdeleg, clear menvcfg.CDE so scountovf is not redirected for VS (issue 2287)."""
    with t.only_if("defined(SMCDELEG_SUPPORTED) || defined(SSCCFG_SUPPORTED)"):
        t.comment("menvcfg.CDE = 0")
        with t.rv64_only():
            t.emit("LI(a1, 1)", 2)
            t.emit("slli a1, a1, 60")
            csr_op(t, "CLEAR", "CSR_MENVCFG", "a1")
        with t.rv32_only():
            csr_op(t, "CLEAR", "CSR_MENVCFGH", imm=0x10000000)


SCOV = 0xDA0


def enc(csr: int, f3: int, rd: int, rs1: int) -> int:
    return (csr << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | 0x73


SCOV_WRITES = [
    ("csrrw x0, CSR_SCOUNTOVF, x6", 1, 0, 6, "csrrw rd=x0"),
    ("csrrw x7, CSR_SCOUNTOVF, x6", 1, 7, 6, "csrrw"),
    ("csrrs x7, CSR_SCOUNTOVF, x6", 2, 7, 6, "csrrs rs1!=x0"),
    ("csrrc x7, CSR_SCOUNTOVF, x6", 3, 7, 6, "csrrc rs1!=x0"),
    ("csrrwi x7, CSR_SCOUNTOVF, 0x15", 5, 7, 0x15, "csrrwi"),
    ("csrrsi x7, CSR_SCOUNTOVF, 0x15", 6, 7, 0x15, "csrrsi uimm!=0"),
    ("csrrci x7, CSR_SCOUNTOVF, 0x15", 7, 7, 0x15, "csrrci uimm!=0"),
]
SCOV_READS = [
    ("csrrs x7, CSR_SCOUNTOVF, x0", "csrrs rs1=x0"),
    ("csrrc x7, CSR_SCOUNTOVF, x0", "csrrc rs1=x0"),
    ("csrrsi x7, CSR_SCOUNTOVF, 0", "csrrsi uimm=0"),
    ("csrrci x7, CSR_SCOUNTOVF, 0", "csrrci uimm=0"),
]


def t_scountovf_op() -> list[TestFile]:
    t = new("scountovf_op")
    t.describe(
        source=SCOF,
        rule_text="This extension adds the scountovf CSR, a 32-bit read-only register that contains shadow copies "
        "of the OF bits in the 29 mhpmevent CSRs (mhpmevent3 - mhpmevent31) - where scountovf bit X corresponds to "
        "mhpmeventX.",
        context="scountovf is CSR 0xDA0, an S-level read-only address. Event-independent: OF bits are written by "
        "software (issue 1981). OF of a counter that is not implemented may be read-only zero, so the expected "
        "value is built from the OF bits read back from each mhpmevent. S-mode reads need mcounteren bit X "
        "(scountovf_smode_read_access); mcounteren is WARL, so its read-back value is used. The _Sm file covers "
        "M-mode accesses.",
        issues=ISSUE_1981 + "\n" + ISSUE_2287,
        plan="1. OF patterns all 29 set, 0x55555550, 0xAAAAAAA8, none, and only the designated counter: scountovf "
        "read in M-mode (T-SBI) equals the OF mask, and read in S-mode (mcounteren HPM bits set) equals the OF mask "
        "AND mcounteren. Bits 2:0 are not checked; on RV64 bits 63:32 must be 0.\n"
        "2. Read-only: in S-mode, csrrw (rd=x0 and not), csrrs/csrrc with rs1!=x0 (also holding 0), and "
        "csrrwi/csrrsi/csrrci with uimm!=0 raise illegal-instruction (stval 0 or the instruction); the value is "
        "unchanged. csrrs/csrrc with rs1=x0 and csrrsi/csrrci with uimm=0 read without a trap.\n"
        "3. U-mode reads raise illegal-instruction (S-level CSR), with mcounteren and scounteren all ones.\n"
        "4. With H (menvcfg.CDE cleared, hcounteren all ones): a VU-mode read raises virtual-instruction (the read "
        "is allowed in VS-mode), and a VS-mode csrrw raises illegal-instruction.\n"
        "mcounteren and scounteren are restored.",
    )
    t.li("x6", SIE)
    t.emit("csrc sstatus, x6")
    save_csr(t, "CSR_MCOUNTEREN", 9)
    t.emit("csrr x6, scounteren")
    st_slot(t, "x6", 10)
    counteren(t, "mcounteren", HPM_MASK, 7)
    for pat in (HPM_MASK, P_A, P_B, 0, "single"):
        if pat == "single":
            of_pattern(t, 0)
            ev_bits(t, "SET", OFB)
        else:
            of_pattern(t, pat)
        ofm(t)
        if pat == "single" and MUT == "scountovf_shift":
            ld_slot(t, "x6", 6)
            t.emit("srli x6, x6, 3")
            st_slot(t, "x6", 6)
        lab = t.label("m")
        t.emit(f"{lab}:", 0)
        scountovf_m(t, "x6")
        expect_scountovf(t, "x6", [6], lab, f"M-mode read, OF pattern {pat if isinstance(pat, str) else hex(pat)}")
        lab = t.label("s")
        t.emit(f"{lab}:", 0)
        t.emit("csrr x6, CSR_SCOUNTOVF")
        expect_scountovf(t, "x6", [6, 7], lab, f"S-mode read, OF pattern {pat if isinstance(pat, str) else hex(pat)}")
    t.comment("2. read-only from S-mode (OF pattern 0xAAAAAAA8)")
    of_pattern(t, P_B)
    ofm(t)
    for asm, f3, rd, rs1, kind in SCOV_WRITES:
        t.li("x6", 0 if kind == "csrrs rs1!=x0" else -1)
        ok = MUT == "scountovf_writable" and kind == "csrrw"
        t.window("S", [asm], "ok" if ok else 2, f"{kind} of scountovf", None if ok else [0, enc(SCOV, f3, rd, rs1)])
        if kind == "csrrs rs1!=x0":
            t.li("x6", -1)
            t.window("S", [asm], 2, f"{kind} (rs1 = all ones) of scountovf", [0, enc(SCOV, f3, rd, rs1)])
    for asm, kind in SCOV_READS:
        lab = t.window("S", [asm], "ok", f"{kind} of scountovf")
        expect_scountovf(t, "x7", [6, 7], lab, f"{kind} reads scountovf")
    lab = t.label("after")
    t.emit(f"{lab}:", 0)
    t.emit("csrr x6, CSR_SCOUNTOVF")
    expect_scountovf(t, "x6", [6, 7], lab, "S-mode read after the write attempts (unchanged)")
    t.comment("3. U-mode read (mcounteren and scounteren all ones)")
    t.li("x6", -1)
    t.emit("csrw scounteren, x6")
    t.window(
        "U", ["csrr x7, CSR_SCOUNTOVF"], 2, "read of scountovf with every counter enable set", [0, enc(SCOV, 2, 7, 0)]
    )
    with t.only_if(H):
        t.comment(
            "4. With H (menvcfg.CDE=0, hcounteren all ones): VU-mode read raises virtual-instruction (allowed in "
            "VS-mode); a VS-mode write raises illegal-instruction (read-only)"
        )
        cde_off(t)
        t.emit("csrr x6, CSR_HCOUNTEREN")
        st_slot(t, "x6", 11)
        t.li("x6", -1)
        t.emit("csrw CSR_HCOUNTEREN, x6")
        t.window(
            "VU",
            ["csrr x7, CSR_SCOUNTOVF"],
            22,
            "read of scountovf with every counter enable set",
            [0, enc(SCOV, 2, 7, 0)],
        )
        t.window("VS", ["csrrw x7, CSR_SCOUNTOVF, x6"], 2, "csrrw of scountovf", [0, enc(SCOV, 1, 7, 6)])
        ld_slot(t, "x6", 11)
        t.emit("csrw CSR_HCOUNTEREN, x6")
    t.comment("restore")
    of_pattern(t, 0)
    ld_slot(t, "x6", 10)
    t.emit("csrw scounteren, x6")
    restore_csr(t, "CSR_MCOUNTEREN", 9)

    m = new_sm("scountovf_op")
    m.describe(
        source=SCOF,
        rule_text=t.doc["rule_text"],
        context="M-mode part: direct M-mode reads and write attempts. scountovf is a read-only CSR address, so "
        "M-mode writes raise illegal-instruction too. " + t.doc["context"].split(". ")[1] + ".",
        issues=ISSUE_1981,
        plan="1. OF patterns 0x55555550 and 0xAAAAAAA8: an M-mode read equals the OF mask read back from the "
        "mhpmevents (bits 2:0 not checked).\n"
        "2. M-mode csrrw, csrrs/csrrc with rs1!=x0 and the immediate forms with uimm!=0 raise illegal-instruction; "
        "reads with rs1=x0 and uimm=0 do not trap; the value is unchanged.",
    )
    for pat in (P_A, P_B):
        of_pattern(m, pat)
        ofm(m)
        lab = m.label("m")
        m.emit(f"{lab}:", 0)
        m.emit("csrr x6, CSR_SCOUNTOVF")
        expect_scountovf(m, "x6", [6], lab, f"M-mode read, OF pattern {pat:#x}")
    for asm, f3, rd, rs1, kind in SCOV_WRITES:
        m.li("x6", -1)
        m.window("M", [asm], 2, f"{kind} of scountovf", [0, enc(SCOV, f3, rd, rs1)])
    for asm, kind in SCOV_READS:
        lab = m.window("M", [asm], "ok", f"{kind} of scountovf")
        expect_scountovf(m, "x7", [6], lab, f"{kind} reads scountovf")
    of_pattern(m, 0)
    return [t, m]


def t_scountovf_mmode_read_access() -> TestFile:
    t = new("scountovf_mmode_read_access")
    t.describe(
        source=SCOF,
        rule_text="In M-mode, scountovf bit X is always readable.",
        context="M-mode reads go through T-SBI. Event-independent: OF bits are written by software (issue 1981); "
        "the expected value is the OF mask read back from the mhpmevents.",
        issues=ISSUE_1981,
        plan="OF patterns all set and 0x55555550; for each, mcounteren HPM bits 0, 0xAAAAAAA8 and all ones (and "
        "with H, hcounteren HPM bits 0): the M-mode read equals the full OF mask. mcounteren and hcounteren are "
        "restored.",
    )
    save_csr(t, "CSR_MCOUNTEREN", 9)
    with t.only_if(H):
        t.emit("csrr x6, CSR_HCOUNTEREN")
        st_slot(t, "x6", 10)
        t.li("x6", HPM_MASK)
        t.emit("csrc CSR_HCOUNTEREN, x6")
    for pat in (HPM_MASK, P_A):
        of_pattern(t, pat)
        ofm(t)
        for men in (0, P_B, HPM_MASK):
            counteren(t, "mcounteren", men, 7)
            lab = t.label("m")
            t.emit(f"{lab}:", 0)
            scountovf_m(t, "x6")
            expect_scountovf(
                t, "x6", [6, 7] if MUT == "m_gated" else [6], lab, f"M-mode read, OF {pat:#x}, mcounteren {men:#x}"
            )
    of_pattern(t, 0)
    with t.only_if(H):
        ld_slot(t, "x6", 10)
        t.emit("csrw CSR_HCOUNTEREN, x6")
    restore_csr(t, "CSR_MCOUNTEREN", 9)
    return t


def t_scountovf_smode_read_access() -> TestFile:
    t = new("scountovf_smode_read_access")
    t.describe(
        source=SCOF,
        rule_text="In S/HS-mode, scountovf bit X is readable when mcounteren bit X is set, and otherwise reads as "
        "zero.",
        context="mcounteren HPM bits are WARL, so the expected value uses the bits read back. scounteren gates "
        "U-mode, and hcounteren VS-mode, not S/HS-mode: both are swept as negative dependencies. Event-independent: "
        "OF bits are written by software (issue 1981).",
        issues=ISSUE_1981,
        plan="OF patterns all set and 0xAAAAAAA8. For mcounteren HPM bits 0, all ones, 0x55555550, 0xAAAAAAA8 and "
        "only the designated counter, an S-mode read (in a trap window: no trap even with mcounteren=0) equals OF "
        "mask AND mcounteren. With mcounteren all ones: scounteren 0 and all ones, and with H hcounteren 0, do not "
        "change the S-mode read. Counter enables are restored.",
    )
    t.li("x6", SIE)
    t.emit("csrc sstatus, x6")
    save_csr(t, "CSR_MCOUNTEREN", 9)
    t.emit("csrr x6, scounteren")
    st_slot(t, "x6", 10)
    with t.only_if(H):
        t.emit("csrr x6, CSR_HCOUNTEREN")
        st_slot(t, "x6", 11)

    def sread(desc: str) -> None:
        lab = t.window("S", ["csrr x7, CSR_SCOUNTOVF"], "ok", f"read of scountovf ({desc})")
        expect_scountovf(t, "x7", [6] if MUT == "s_ignores_mcounteren" else [6, 7], lab, f"S-mode read, {desc}")

    for pat in (HPM_MASK, P_B):
        of_pattern(t, pat)
        ofm(t)
        for men in (0, HPM_MASK, P_A, P_B, NBIT):
            counteren(t, "mcounteren", men, 7)
            sread(f"OF {pat:#x}, mcounteren {men if isinstance(men, str) else hex(men)}")
    counteren(t, "mcounteren", HPM_MASK, 7)
    for sen in (0, -1):
        t.li("x6", sen)
        t.emit("csrw scounteren, x6")
        if MUT == "s_gated_by_scounteren" and sen == 0:
            t.emit("li x6, 0")
            st_slot(t, "x6", 7)
        sread(f"mcounteren all ones, scounteren {sen & 0xFFFFFFFF:#x}")
    ld_slot(t, "x6", 10)
    t.emit("csrw scounteren, x6")
    with t.only_if(H):
        counteren(t, "mcounteren", HPM_MASK, 7)
        t.emit("csrw CSR_HCOUNTEREN, x0")
        sread("mcounteren all ones, hcounteren 0")
        ld_slot(t, "x6", 11)
        t.emit("csrw CSR_HCOUNTEREN, x6")
    of_pattern(t, 0)
    restore_csr(t, "CSR_MCOUNTEREN", 9)
    return t


def t_scountovf_vsmode_read_access() -> TestFile:
    t = new("scountovf_vsmode_read_access", REQ + ["H"])
    t.describe(
        source=SCOF,
        rule_text="Similarly, in VS mode, scountovf bit X is readable when mcounteren bit X and hcounteren bit X "
        "are both set, and otherwise reads as zero.",
        context="mcounteren and hcounteren HPM bits are WARL, so the expected value uses the bits read back. "
        "scounteren does not gate VS-mode (negative dependency), and hcounteren does not gate HS-mode reads. "
        "Event-independent: OF bits are written by software (issue 1981).",
        issues=ISSUE_1981 + "\n" + ISSUE_2287,
        plan="OF pattern all set (the read-back mask). For (mcounteren, hcounteren) HPM bits (all, all), (all, 0), "
        "(0, all), (0x55555550, all), (all, 0xAAAAAAA8), (0x55555550 | designated, 0x33333338 | designated), a VS-mode "
        "read (no trap) equals OF AND mcounteren AND hcounteren, and an HS-mode read equals OF AND mcounteren. "
        "With both all ones, scounteren 0 does not change the VS-mode read. Enables and menvcfg.CDE are left as "
        "the test found them except CDE, which is cleared.",
    )
    t.li("x6", SIE)
    t.emit("csrc sstatus, x6")
    cde_off(t)
    save_csr(t, "CSR_MCOUNTEREN", 9)
    t.emit("csrr x6, scounteren")
    st_slot(t, "x6", 10)
    t.emit("csrr x6, CSR_HCOUNTEREN")
    st_slot(t, "x6", 11)
    of_pattern(t, HPM_MASK)
    ofm(t)
    for men, hen in (
        (HPM_MASK, HPM_MASK),
        (HPM_MASK, 0),
        (0, HPM_MASK),
        (P_A, HPM_MASK),
        (HPM_MASK, P_B),
        (f"{P_A}|{NBIT}", f"0x33333338|{NBIT}"),
    ):
        counteren(t, "mcounteren", men, 7)
        counteren(t, "hcounteren", hen, 8)
        desc = f"mcounteren {men if isinstance(men, str) else hex(men)}, hcounteren {hen if isinstance(hen, str) else hex(hen)}"
        lab = t.window("VS", ["csrr x7, CSR_SCOUNTOVF"], "ok", f"read of scountovf ({desc})")
        slots = {"vs_ignores_hcounteren": [6, 7], "vs_ignores_mcounteren": [6, 8]}.get(MUT, [6, 7, 8])
        expect_scountovf(t, "x7", slots, lab, f"VS-mode read, {desc}")
        lab = t.label("hs")
        t.emit(f"{lab}:", 0)
        t.emit("csrr x7, CSR_SCOUNTOVF")
        expect_scountovf(t, "x7", [6, 7], lab, f"HS-mode read, {desc}")
    counteren(t, "mcounteren", HPM_MASK, 7)
    counteren(t, "hcounteren", HPM_MASK, 8)
    t.emit("csrw scounteren, x0")
    lab = t.window("VS", ["csrr x7, CSR_SCOUNTOVF"], "ok", "read of scountovf (scounteren 0)")
    expect_scountovf(t, "x7", [6, 7, 8], lab, "VS-mode read, mcounteren/hcounteren all ones, scounteren 0")
    of_pattern(t, 0)
    ld_slot(t, "x6", 10)
    t.emit("csrw scounteren, x6")
    ld_slot(t, "x6", 11)
    t.emit("csrw CSR_HCOUNTEREN, x6")
    restore_csr(t, "CSR_MCOUNTEREN", 9)
    return t


HPMC = "(CSR_HPMCOUNTER3+RVMODEL_HPM_COUNTER-3)"
HPMC_ENC = f"(({HPMC})<<20)|(2<<12)|(7<<7)|0x73"


def t_scountovf_smode_read_access_control() -> TestFile:
    t = new("scountovf_smode_read_access_control", REQ + ["Zihpm"])
    t.describe(
        source=SCOF,
        rule_text="Read access to bit X is subject to the same mcounteren (or mcounteren and hcounteren) CSRs that "
        "mediate access to the hpmcounter CSRs by S-mode (or VS-mode).",
        context="hpmcounterX is readable in S-mode iff mcounteren bit X is set (else illegal-instruction), and in "
        "VS-mode iff mcounteren and hcounteren bit X are set (mcounteren clear: illegal-instruction; only "
        "hcounteren clear: virtual-instruction). The test pairs, for the designated counter X with OF=1, each "
        "hpmcounterX read outcome with scountovf bit X. Counter-enable bits are WARL: each is set, read back and "
        "the cases follow the value held.",
        issues=ISSUE_1981 + "\n" + ISSUE_2287,
        plan="1. S-mode, mcounteren bit X set (if writable): hpmcounterX reads without a trap and scountovf bit X "
        "reads 1. mcounteren bit X clear: hpmcounterX raises illegal-instruction and scountovf bit X reads 0.\n"
        "2. With H, VS-mode: (mcounteren, hcounteren) bit X = (1,1): no trap, bit reads 1; (1,0): "
        "virtual-instruction, bit reads 0; (0,1) and (0,0): illegal-instruction, bit reads 0.\n"
        "Cases are skipped when the enable bit does not take the value (read back after each write).\n"
        "Counter enables are restored.",
    )
    t.li("x6", SIE)
    t.emit("csrc sstatus, x6")
    cde_off(t)
    save_csr(t, "CSR_MCOUNTEREN", 9)
    with t.only_if(H):
        t.emit("csrr x6, CSR_HCOUNTEREN")
        st_slot(t, "x6", 11)
    of_pattern(t, 0)
    ev_bits(t, "SET", OFB)
    tval = [0, X(HPMC_ENC, HPMC_ENC)]

    def bitx(reg: str) -> None:
        t.emit(f"srli {reg}, {reg}, RVMODEL_HPM_COUNTER")
        t.emit(f"andi {reg}, {reg}, 1")

    def s_case(men: int) -> None:
        t.window(
            "S",
            [f"csrr x7, {HPMC}"],
            "ok" if men else 2,
            f"read of hpmcounterX, mcounteren bit X={men}",
            None if men else tval,
        )
        lab = t.label("sbit")
        t.emit(f"{lab}:", 0)
        t.emit("csrr x7, CSR_SCOUNTOVF")
        bitx("x7")
        t.check("x7", men, lab, f"scountovf bit X in S-mode, mcounteren bit X={men}")

    def vs_case(men: int, hen: int) -> None:
        cause = "ok" if men and hen else (22 if men else 2)
        if MUT == "ctrl_hcen_ignored" and men and not hen:
            cause = "ok"
        t.window(
            "VS",
            [f"csrr x7, {HPMC}"],
            cause,
            f"read of hpmcounterX, mcounteren/hcounteren bit X={men}/{hen}",
            None if cause == "ok" else tval,
        )
        lab = t.window("VS", ["csrr x7, CSR_SCOUNTOVF"], "ok", f"read of scountovf, bit X enables {men}/{hen}")
        bitx("x7")
        t.check(
            "x7",
            int(bool(men and hen)) if MUT != "ctrl_hcen_ignored" else men,
            lab,
            f"scountovf bit X in VS-mode, mcounteren/hcounteren bit X={men}/{hen}",
        )

    csr_op(t, "SET", "CSR_MCOUNTEREN", imm=NBIT)
    csr_op(t, "READ", "CSR_MCOUNTEREN")
    t.emit("mv x1, a0")
    bitx("x1")

    t.either("x1", lambda: s_case(1), lambda: t.comment("mcounteren bit X is read-only zero"))

    def m_cleared() -> None:
        """Clear mcounteren bit X; x1 = 1 if it reads back 0 (WARL: it could be read-only one)."""
        csr_op(t, "CLEAR", "CSR_MCOUNTEREN", imm=NBIT)
        csr_op(t, "READ", "CSR_MCOUNTEREN")
        t.emit("mv x1, a0")
        bitx("x1")
        t.emit("seqz x1, x1")

    m_cleared()
    t.either("x1", lambda: s_case(0), lambda: t.comment("mcounteren bit X is read-only one"))
    restore_csr(t, "CSR_MCOUNTEREN", 9)
    with t.only_if(H):
        t.comment("VS-mode")
        csr_op(t, "SET", "CSR_MCOUNTEREN", imm=NBIT)
        csr_op(t, "READ", "CSR_MCOUNTEREN")
        t.emit("mv x1, a0")
        bitx("x1")
        t.emit(f"LI(x6, {NBIT})", 2)
        t.emit("csrs CSR_HCOUNTEREN, x6")
        t.emit("csrr x8, CSR_HCOUNTEREN")
        bitx("x8")
        t.emit("and x1, x1, x8")

        def both_on() -> None:
            vs_case(1, 1)
            t.emit(f"LI(x6, {NBIT})", 2)
            t.emit("csrc CSR_HCOUNTEREN, x6")
            vs_case(1, 0)
            t.emit(f"LI(x6, {NBIT})", 2)
            t.emit("csrs CSR_HCOUNTEREN, x6")

        t.either("x1", both_on, lambda: t.comment("mcounteren or hcounteren bit X is read-only zero"))
        m_cleared()

        def m_off() -> None:
            vs_case(0, 1)
            t.emit(f"LI(x6, {NBIT})", 2)
            t.emit("csrc CSR_HCOUNTEREN, x6")
            vs_case(0, 0)

        t.either("x1", m_off, lambda: t.comment("mcounteren bit X is read-only one"))
        ld_slot(t, "x6", 11)
        t.emit("csrw CSR_HCOUNTEREN, x6")
        restore_csr(t, "CSR_MCOUNTEREN", 9)
    of_pattern(t, 0)
    return t


# ---------------------------------------------------------------- LCOFI bits and interrupts
def m_lcof(t: TestFile, op: str, csr: str) -> None:
    """SET/CLEAR bit 13 of mip or mie in M-mode (T-SBI in S-mode tests)."""
    csr_op(t, op, f"CSR_{csr.upper()}", imm=LCOF)


def bit13(t: TestFile, reg: str) -> None:
    t.emit(f"srli {reg}, {reg}, 13")
    t.emit(f"andi {reg}, {reg}, 1")


def t_mip_lcofip_acc() -> TestFile:
    t = new("mip_lcofip_acc")
    t.describe(
        source=MAC,
        rule_text="lcofip is read-write in mip",
        context="M-mode accesses go through T-SBI (csrrs/csrrc/csrrw of mip). sip.LCOFIP is the same bit when LCOFI "
        "is delegated (D=1) and read-only zero otherwise. " + DELEG_NOTE + " mie.LCOFIE stays 0, so no interrupt is "
        "taken.",
        plan="1. M-mode set, clear, set, clear of mip bit 13: each is read back in M-mode, and in sip (equal to mip "
        "when delegated, 0 otherwise).\n"
        "2. M-mode csrw of mip with bit 13 set and then clear (other bits as read): read back in M-mode.",
    )
    t.li("x6", SIE)
    t.emit("csrc sstatus, x6")
    lcof_off(t)
    for op in ("SET", "CLEAR", "SET", "CLEAR"):
        exp = int(op == "SET") if MUT != "mip_lcofip_ro" else 0
        m_lcof(t, op, "mip")
        lab = t.label("mip")
        t.emit(f"{lab}:", 0)
        mip_lcofip(t, "x6")
        t.check("x6", exp, lab, f"mip.LCOFIP (M-mode read) after an M-mode {op.lower()} of bit 13")
        t.emit("csrr x7, sip")
        bit13(t, "x7")
        if exp:
            ld_deleg(t, "x8")
            t.emit("xor x7, x7, x8")
        t.check("x7", 0, lab, f"sip.LCOFIP after an M-mode {op.lower()} of mip bit 13, XOR (mip bit AND D): 0")
    for on in (1, 0):
        csr_op(t, "READ", "CSR_MIP")
        t.li("x6", LCOF)
        t.emit(f"{'or a1, a0, x6' if on else 'not x6, x6'}")
        if not on:
            t.emit("and a1, a0, x6")
        csr_op(t, "WRITE", "CSR_MIP", "a1")
        lab = t.label("mipw")
        t.emit(f"{lab}:", 0)
        mip_lcofip(t, "x6")
        t.check(
            "x6", on if MUT != "mip_lcofip_ro" else 0, lab, f"mip.LCOFIP after an M-mode csrw of mip with bit 13 = {on}"
        )
    lcof_off(t)
    return t


def s_int_case(t: TestFile, mode: str, sie: int, ie: int, desc: str, taken: bool) -> None:
    """LCOFIP is pending; run in `mode` with sstatus.SIE=sie (S-mode; set through SPIE before sret for U) inside
    a window, and check whether the LCOFI is taken in S. sie.LCOFIE must already be `ie`."""
    lab = t.label(f"int{mode}")
    if mode == "S":
        t.allow(1)
        t.emit(f"{lab}:", 0)
        if sie:
            t.li("x6", SIE)
            t.emit("csrs sstatus, x6")
        delay(t)
        t.li("x6", SIE)
        t.emit("csrc sstatus, x6")
    else:
        t.li("x6", SPIE)
        t.emit(f"{'csrs' if sie else 'csrc'} sstatus, x6")
        t.allow(1)
        t.enter(mode)
        t.emit(f"{lab}:", 0)
        delay(t)
        t.leave()
        t.li("x6", SIE | SPIE)
        t.emit("csrc sstatus, x6")
    t.outcome(
        LCOFI_S if taken else "ok",
        lab,
        f"{desc}: LCOFI {'must' if taken else 'must not'} be taken in S-mode",
        epc=False,
        origin=mode,
    )


def t_mip_lcofip_mie_lcofie_op() -> list[TestFile]:
    t = new("mip_lcofip_mie_lcofie_op")
    t.describe(
        source=MAC,
        rule_text="If the sscofpmf extension is implemented, bits mip[lcofip] and mie[lcofie] are the "
        "interrupt-pending and interrupt-enable bits for local-counter-overflow interrupts.",
        context="mie.LCOFIE and mip.LCOFIP are set and cleared in M-mode through T-SBI. When LCOFI is delegated (D=1), "
        "sie.LCOFIE and sip.LCOFIP are the same bits and the LCOFI is taken in S; otherwise sie/sip bit 13 read 0 and "
        "the LCOFI is taken in M (always enabled below M). " + DELEG_NOTE + " The _Sm file covers M-mode.",
        issues=ISSUE_1800,
        plan="1. M-mode sets and clears mie bit 13: sie.LCOFIE follows when delegated, and reads 0 otherwise.\n"
        "2. M-mode sets mip bit 13 (pending). With mie bit 13 set by M-mode and sstatus.SIE=1 in S-mode, the LCOFI "
        "is taken (xcause = interrupt | 13, from S); with mie bit 13 clear it is not.\n"
        "3. With mie bit 13 set and mip bit 13 clear, no interrupt.",
    )
    t.li("x6", SIE)
    t.emit("csrc sstatus, x6")
    lcof_off(t)
    for op in ("SET", "CLEAR"):
        m_lcof(t, op, "mie")
        lab = t.label("mie")
        t.emit(f"{lab}:", 0)
        t.emit("csrr x7, sie")
        bit13(t, "x7")
        if op == "SET":
            ld_deleg(t, "x8")
            t.emit("xor x7, x7, x8")
        t.check("x7", 0, lab, f"sie.LCOFIE after an M-mode {op.lower()} of mie bit 13, XOR (mie bit AND D): 0")
    for ie, pend in ((1, 1), (0, 1), (1, 0)):
        m_lcof(t, "SET" if ie else "CLEAR", "mie")
        m_lcof(t, "SET" if pend else "CLEAR", "mip")
        taken = bool(ie and pend) if MUT != "lcofie_ignored" else bool(pend)
        s_int_case(t, "S", 1, ie, f"S-mode, sstatus.SIE=1, mie bit 13={ie}, mip bit 13={pend}", taken)
        lcof_off(t)

    m = new_sm("mip_lcofip_mie_lcofie_op")
    m.describe(
        source=MAC,
        rule_text=t.doc["rule_text"],
        context='M-mode part: delegation needs mideleg. mideleg[13] is WARL ("An implementation can choose to '
        'subset the delegatable traps", norm:medeleg_mideleg_warl) and may be read-only one '
        "(norm:mideleg_rd1_lower_level), so it is probed by writing 1 and 0 and reading back; each case runs only "
        "with a value the bit can hold, and expects the routing that value gives. An LCOFI that is not "
        "delegated is taken in M when mie.LCOFIE=1 and either the hart is in M with mstatus.MIE=1 or in S/U "
        "(M-level interrupts are then always enabled). A delegated one is never taken in M.",
        issues=ISSUE_1800,
        plan="1. Probe mideleg[13]: set and read (r1), clear and read (r0): writable, read-only 0 or read-only 1.\n"
        "2. mip.LCOFIP=1 (software write), each case in a trap window:\n"
        "   a. If it can be 1: mideleg[13]=1, M-mode with MIE=1 and mie.LCOFIE=1: not taken.\n"
        "   b. If it can be 0: mideleg[13]=0, M-mode, taken iff MIE=1 and mie.LCOFIE=1 (sweep of both); mcause = "
        "interrupt | 13.\n"
        "   c. If it can be 0: mideleg[13]=0, S-mode (sstatus.SIE=0) and U-mode: taken in M iff mie.LCOFIE=1.\n"
        "mideleg is restored.",
    )
    m.emit("csrr x6, mideleg")
    st_slot(m, "x6", 12)
    m.comment("probe mideleg[13]: r1 (after setting) in slot 10, r0 (after clearing) in slot 11")
    for op, slot in (("csrs", 10), ("csrc", 11)):
        m.li("x6", LCOF)
        m.emit(f"{op} mideleg, x6")
        m.emit("csrr x7, mideleg")
        bit13(m, "x7")
        st_slot(m, "x7", slot)

    def m_case(mode: str, deleg: int, mie_: int, ie: int) -> None:
        taken = (not deleg) and ie and (mie_ or mode != "M")
        if MUT == "deleg_ignored" and deleg and ie and mie_:
            taken = True
        desc = f"{mode}-mode, mideleg[13]={deleg}, mstatus.MIE={mie_}, mie.LCOFIE={ie}"
        m.comment(desc)
        m.li("x6", LCOF)
        m.emit(f"{'csrs' if deleg else 'csrc'} mideleg, x6")
        m.emit(f"{'csrs' if ie else 'csrc'} mie, x6")
        m.emit("csrs mip, x6")
        m.li("x6", SIE)
        m.emit("csrc sstatus, x6")
        lab = m.label(f"m_{mode}")
        m.allow(1)
        if mode != "M":
            m.enter(mode)
        m.emit(f"{lab}:", 0)
        if mode == "M" and mie_:
            m.li("x6", MIE)
            m.emit("csrs mstatus, x6")
        delay(m)
        if mode != "M":
            m.leave()
        m.li("x6", MIE)
        m.emit("csrc mstatus, x6")
        lcof_off(m)
        m.outcome(
            X((1 << 31) | 13, (1 << 63) | 13) if taken else "ok",
            lab,
            f"{desc}: LCOFI {'must' if taken else 'must not'} be taken in M-mode",
            epc=False,
            origin=mode,
        )

    def deleg0() -> None:
        for mie_ in (0, 1):
            for ie in (0, 1):
                m_case("M", 0, mie_, ie)
        for mode in ("S", "U"):
            for ie in (0, 1):
                m_case(mode, 0, 0, ie)

    ld_slot(m, "x1", 10)
    m.either("x1", lambda: m_case("M", 1, 1, 1), lambda: m.comment("mideleg[13] is read-only zero"))
    ld_slot(m, "x1", 11)
    m.emit("seqz x1, x1")
    m.either("x1", deleg0, lambda: m.comment("mideleg[13] is read-only one"))
    ld_slot(m, "x6", 12)
    m.emit("csrw mideleg, x6")
    return [t, m]


def t_sip_sie_sscofpmf() -> TestFile:
    t = new("sip_sie_Sscofpmf")
    t.describe(
        source=SUP,
        rule_text="If the Sscofpmf extension is implemented, bits sip.LCOFIP and sie.LCOFIE are the "
        "interrupt-pending and interrupt-enable bits for local-counter-overflow interrupts. LCOFIP is read-write in "
        "sip and reflects the occurrence of a local counter-overflow overflow interrupt request resulting from any "
        "of the mhpmevent_n_.OF bits being set. If the Sscofpmf extension is not implemented, sip.LCOFIP and "
        "sie.LCOFIE are read-only zeros.",
        context="Steps 1-3 need LCOFI delegated to S. " + DELEG_NOTE + " When it is not delegated, sip.LCOFIP and "
        "sie.LCOFIE are read-only zero (restricted views of mip/mie), and that is what is checked instead. An S-level "
        "interrupt is taken in S-mode when sstatus.SIE=1 and its sie bit is set, and in U-mode whenever its sie bit is "
        "set. The last sentence (no Sscofpmf) needs a hart without Sscofpmf and is not tested here. " + COUNT_NOTE,
        issues=ISSUE_1800,
        plan="1. sip.LCOFIP read-write from S-mode: csrrs, csrrc and csrrw (other bits as read) set and clear it; "
        "each is read back in sip and in mip (M-mode read).\n"
        "2. sie.LCOFIE likewise, read back in sie and mie.\n"
        "3. With LCOFIP=1 (written in sip): in S-mode, (sstatus.SIE, sie.LCOFIE) in {00, 01, 10, 11}: taken only for "
        "11 (scause = interrupt | 13); in U-mode (SIE 0 or 1 through SPIE) taken iff sie.LCOFIE=1. With LCOFIP=0 "
        "and both enables set: not taken.\n"
        "Not delegated: S-mode writes of sip/sie bit 13 read back 0 and leave mip/mie bit 13 at 0.\n"
        "4. With counting (RVMODEL_MHPMEVENT_VAL != 0): a counter wrap with OF=0 sets LCOFIP (sip if delegated, else "
        "mip).",
    )
    t.li("x6", SIE)
    t.emit("csrc sstatus, x6")
    lcof_off(t)

    def delegated() -> None:
        for csr in ("sip", "sie"):
            for form in ("csrrs", "csrrc", "csrrw1", "csrrw0"):
                on = form in ("csrrs", "csrrw1")
                t.li("x6", LCOF)
                lab = t.label(csr)
                if form.startswith("csrrw"):
                    t.emit(f"csrr x7, {csr}")
                    t.emit("or x7, x7, x6" if on else "not x6, x6")
                    if not on:
                        t.emit("and x7, x7, x6")
                    t.emit(f"{lab}:", 0)
                    t.emit(f"csrrw x8, {csr}, x7")
                else:
                    t.emit(f"{lab}:", 0)
                    t.emit(f"{form} x8, {csr}, x6")
                t.emit(f"csrr x7, {csr}")
                bit13(t, "x7")
                exp = int(on) if not (MUT == "sip_lcofip_ro" and csr == "sip") else 0
                t.check("x7", exp, lab, f"{csr} bit 13 after {form[:5]} {'setting' if on else 'clearing'} it")
                csr_op(t, "READ", f"CSR_M{csr[1:].upper()}")
                bit13(t, "a0")
                t.check("a0", exp, lab, f"m{csr[1:]} bit 13 (M-mode read) after the S-mode {csr} write")
        t.comment("3. interrupt enables")
        for sie in (0, 1):
            for ie in (0, 1):
                t.li("x6", LCOF)
                t.emit(f"{'csrs' if ie else 'csrc'} sie, x6")
                t.emit("csrs sip, x6")
                s_int_case(t, "S", sie, ie, f"S-mode, sstatus.SIE={sie}, sie.LCOFIE={ie}, LCOFIP=1", bool(sie and ie))
                lcof_off(t)
        for sie in (0, 1):
            for ie in (0, 1):
                t.li("x6", LCOF)
                t.emit(f"{'csrs' if ie else 'csrc'} sie, x6")
                t.emit("csrs sip, x6")
                taken = bool(ie and (sie or MUT != "u_needs_sie"))
                s_int_case(t, "U", sie, ie, f"U-mode, sstatus.SIE={sie}, sie.LCOFIE={ie}, LCOFIP=1", taken)
                lcof_off(t)
        t.li("x6", LCOF)
        t.emit("csrs sie, x6")
        s_int_case(t, "S", 1, 1, "S-mode, sstatus.SIE=1, sie.LCOFIE=1, LCOFIP=0", False)
        lcof_off(t)

    def undelegated() -> None:
        t.comment("LCOFI not delegated: sip/sie bit 13 are read-only zero")
        for csr in ("sip", "sie"):
            t.li("x6", LCOF)
            lab = t.label(csr)
            t.emit(f"{lab}:", 0)
            t.emit(f"csrrs x8, {csr}, x6")
            t.emit(f"csrr x7, {csr}")
            bit13(t, "x7")
            t.check("x7", 0, lab, f"{csr} bit 13 after csrrs setting it, with LCOFI not delegated")
            csr_op(t, "READ", f"CSR_M{csr[1:].upper()}")
            bit13(t, "a0")
            t.check("a0", 0, lab, f"m{csr[1:]} bit 13 (M-mode read) after the S-mode {csr} write")

    ld_deleg(t, "x1")
    t.either("x1", delegated, undelegated)
    lcof_off(t)
    with t.only_if(COUNTS):
        counter_setup(t)
        probe_width(t)
        overflow_s(t)
        expect_lcofip(t, 1, "a counter wrap with OF=0")
        counter_teardown(t)
    lcof_off(t)
    return t


def t_vsip_vsie_lcofi() -> TestFile:
    t = new("vsip_vsie_lcofi", REQ + ["H"])
    t.describe(
        source=HYP,
        rule_text="Extension Shlcofideleg supports delegating LCOFI interrupts to VS-mode. If the Shlcofideleg "
        "extension is implemented, hideleg bit 13 is writable; otherwise, it is read-only zero. When bit 13 of "
        "hideleg is zero, vsip.LCOFIP and vsie.LCOFIE are read-only zeros. Else, vsip.LCOFIP and vsie.LCOFIE are "
        "aliases of sip.LCOFIP and sie.LCOFIE.",
        context="The test runs in HS-mode, reads vsip/vsie directly and from VS-mode (as sip/sie), and keeps "
        "sstatus.SIE=0 so HS-mode never takes the LCOFI. hvien[13] is cleared (T-SBI) under Ssaia so the AIA "
        "hvip alias of vsip[13] is not in play.",
        issues=ISSUE_1785,
        plan="The aliasing cases (3) also need LCOFI delegated to HS, observed as D (see the context of "
        "mip_lcofip_acc); without it sip.LCOFIP is read-only zero and only cases 1-2 run.\n"
        "1. hideleg[13]=0: with sip.LCOFIP=1 and sie.LCOFIE=1, vsip and vsie bit 13 read 0 (HS-mode and VS-mode "
        "reads); HS-mode writes of 1 to vsip/vsie bit 13 leave sip.LCOFIP/sie.LCOFIE unchanged at 0 and vsip/vsie "
        "bit 13 at 0.\n"
        "2. Set hideleg[13] and read it back: 1 with Shlcofideleg, 0 without Shlcofideleg and without Ssaia, "
        "either with Ssaia only.\n"
        "3. If it reads 1: sip.LCOFIP and vsip bit 13 alias in both directions (set and clear from each side), and "
        "sie.LCOFIE and vsie bit 13 likewise; the VS-mode read of sip sees bit 13; with LCOFIP=1, vsie.LCOFIE=1 and "
        "vsstatus.SIE=1 the LCOFI is taken in VS-mode (vscause = interrupt | 13), and not with vsie.LCOFIE=0; from "
        "VU-mode it is taken in VS-mode; HS-mode with sstatus.SIE=1 and sie.LCOFIE=1 does not take it; VS-mode "
        "set/clear of sip bit 13 lands in HS sip.LCOFIP.\n"
        "hideleg[13] is cleared at the end.",
    )
    t.li("x6", SIE | SPIE)
    t.emit("csrc sstatus, x6")
    lcof_off(t)
    with t.only_if("defined(SSAIA_SUPPORTED)"):
        csr_op(t, "CLEAR", "CSR_HVIEN", imm=LCOF)
    t.li("x6", LCOF)
    t.emit("csrc CSR_HIDELEG, x6")
    t.comment("1. hideleg[13]=0")

    def rd(csr: str, exp: int, desc: str) -> None:
        lab = t.label(csr)
        t.emit(f"{lab}:", 0)
        t.emit(f"csrr x7, {csr}")
        bit13(t, "x7")
        t.check("x7", exp, lab, desc)

    t.emit("csrs sip, x6")
    rd("CSR_VSIP", 1 if MUT == "vsip_alias_undelegated" else 0, "vsip bit 13 with hideleg[13]=0 and sip.LCOFIP=1")
    lab = t.window("VS", ["csrr x7, sip"], "ok", "read of sip (vsip) with hideleg[13]=0, sip.LCOFIP=1")
    bit13(t, "x7")
    t.check("x7", 0, lab, "VS-mode sip bit 13 with hideleg[13]=0 and HS sip.LCOFIP=1")
    t.li("x6", LCOF)
    t.emit("csrc sip, x6")
    t.emit("csrs CSR_VSIP, x6")
    rd("sip", 0, "sip.LCOFIP after an HS write of 1 to vsip bit 13 with hideleg[13]=0")
    rd("CSR_VSIP", 0, "vsip bit 13 after an HS write of 1 with hideleg[13]=0")
    t.li("x6", LCOF)
    t.emit("csrs sie, x6")
    rd("CSR_VSIE", 0, "vsie bit 13 with hideleg[13]=0 and sie.LCOFIE=1")
    t.li("x6", LCOF)
    t.emit("csrc sie, x6")
    t.emit("csrs CSR_VSIE, x6")
    rd("sie", 0, "sie.LCOFIE after an HS write of 1 to vsie bit 13 with hideleg[13]=0")
    rd("CSR_VSIE", 0, "vsie bit 13 after an HS write of 1 with hideleg[13]=0")
    t.comment("2. hideleg[13] writability")
    t.li("x6", LCOF)
    t.emit("csrs CSR_HIDELEG, x6")
    lab = t.label("hideleg")
    t.emit(f"{lab}:", 0)
    t.emit("csrr x1, CSR_HIDELEG")
    bit13(t, "x1")
    with t.only_if("defined(SHLCOFIDELEG_SUPPORTED)"):
        t.check("x1", 1, lab, "hideleg[13] after a write of 1 (Shlcofideleg: writable)")
    with t.only_if("!defined(SHLCOFIDELEG_SUPPORTED) && !defined(SSAIA_SUPPORTED)"):
        t.check("x1", 0, lab, "hideleg[13] after a write of 1 (no Shlcofideleg, no AIA: read-only zero)")

    def delegated() -> None:
        t.comment("3. hideleg[13]=1: aliases")
        for src, dst, other in (
            ("sip", "CSR_VSIP", None),
            ("CSR_VSIP", "sip", None),
            ("sie", "CSR_VSIE", None),
            ("CSR_VSIE", "sie", None),
        ):
            for on in (1, 0):
                t.li("x6", LCOF)
                t.emit(f"{'csrs' if on else 'csrc'} {src}, x6")
                rd(
                    dst,
                    on,
                    f"{dst.replace('CSR_', '').lower()} bit 13 after {'setting' if on else 'clearing'} "
                    f"{src.replace('CSR_', '').lower()} bit 13 with hideleg[13]=1",
                )
        t.li("x6", LCOF)
        t.emit("csrs sip, x6")
        lab = t.window("VS", ["csrr x7, sip"], "ok", "read of sip (vsip) with hideleg[13]=1, sip.LCOFIP=1")
        bit13(t, "x7")
        t.check("x7", 1, lab, "VS-mode sip bit 13 with hideleg[13]=1 and HS sip.LCOFIP=1")
        for ie in (1, 0):
            t.li("x6", LCOF)
            t.emit("csrs sip, x6")
            t.emit(f"{'csrs' if ie else 'csrc'} CSR_VSIE, x6")
            t.li("x6", SIE)
            t.emit("csrs CSR_VSSTATUS, x6")
            t.li("x6", SIE | SPIE)
            t.emit("csrc sstatus, x6")
            lab = t.label("intVS")
            t.allow(1)
            t.enter("VS")
            t.emit(f"{lab}:", 0)
            delay(t)
            t.leave()
            t.li("x6", SIE | SPIE)
            t.emit("csrc sstatus, x6")
            t.li("x6", SIE)
            t.emit("csrc CSR_VSSTATUS, x6")
            lcof_off(t)
            t.outcome(
                LCOFI_S if ie else "ok",
                lab,
                f"VS-mode, vsstatus.SIE=1, vsie.LCOFIE={ie}, LCOFIP=1: LCOFI "
                f"{'must' if ie else 'must not'} be taken in VS-mode",
                epc=False,
                origin="VS",
            )
            if ie:
                lab2 = t.label("vsh")
                t.emit(f"{lab2}:", 0)
                t.emit("AI_LOG(x7, TRAPLOG_VECT)", 10)
                t.emit("andi x7, x7, 3")
                t.check("x7", 2, lab2, "the LCOFI was taken by the VS-mode handler (handler mode 2)")
        t.comment("VU-mode: the delegated LCOFI is taken in VS-mode whatever vsstatus.SIE")
        t.li("x6", LCOF)
        t.emit("csrs sip, x6")
        t.emit("csrs CSR_VSIE, x6")
        t.li("x6", SIE | SPIE)
        t.emit("csrc sstatus, x6")
        t.li("x6", SIE)
        t.emit("csrc CSR_VSSTATUS, x6")
        lab = t.label("intVU")
        t.allow(1)
        t.enter("VU")
        t.emit(f"{lab}:", 0)
        delay(t)
        t.leave()
        t.li("x6", SIE | SPIE)
        t.emit("csrc sstatus, x6")
        lcof_off(t)
        t.outcome(
            LCOFI_S, lab, "VU-mode, vsie.LCOFIE=1, LCOFIP=1: LCOFI must be taken in VS-mode", epc=False, origin="VU"
        )
        t.comment("HS-mode must not take an LCOFI delegated to VS, even with sstatus.SIE=1 and sie.LCOFIE=1")
        t.li("x6", LCOF)
        t.emit("csrs sip, x6")
        t.emit("csrs sie, x6")
        lab = t.label("intHS")
        t.allow(1)
        t.emit(f"{lab}:", 0)
        t.li("x6", SIE)
        t.emit("csrs sstatus, x6")
        delay(t)
        t.li("x6", SIE)
        t.emit("csrc sstatus, x6")
        lcof_off(t)
        t.outcome(
            "ok",
            lab,
            "HS-mode, sstatus.SIE=1, sie.LCOFIE=1, LCOFIP=1, hideleg[13]=1: LCOFI must not be taken in HS-mode",
            epc=False,
            origin="S",
        )
        t.comment("VS-mode writes of sip bit 13 land in HS sip.LCOFIP")
        for op, on in (("csrs", 1), ("csrc", 0)):
            t.li("x6", LCOF)
            t.window("VS", [f"{op} sip, x6"], "ok", f"{op} of sip (vsip) bit 13 with hideleg[13]=1")
            rd("sip", on, f"HS sip.LCOFIP after a VS-mode {op} of sip bit 13 with hideleg[13]=1")

    t.comment("the aliasing half also needs LCOFI delegated to HS (D=1); otherwise sip.LCOFIP is read-only zero")
    ld_deleg(t, "x8")
    t.emit("and x1, x1, x8")
    t.either("x1", delegated, lambda: t.comment("hideleg[13] is read-only zero, or LCOFI is not delegated to HS"))
    t.li("x6", LCOF)
    t.emit("csrc CSR_HIDELEG, x6")
    lcof_off(t)
    return t


# ---------------------------------------------------------------- priorities
def prev_cause(t: TestFile, dst: str) -> None:
    """dst = xcause of the second-to-last trap-log entry (as AI_LOG, one entry earlier)."""
    t.emit("LA(x4, rvtest_trap_count)", 2)
    t.emit("LREG x5, 0(x4)")
    t.emit("addi x5, x5, -2")
    t.emit("andi x5, x5, RVTEST_TRAP_LOG_N-1")
    t.emit("slli x5, x5, TRAPLOG_ENTRY_SHIFT")
    t.emit("LA(x4, rvtest_trap_log)", 2)
    t.emit("add x4, x4, x5")
    t.emit(f"LREG {dst}, TRAPLOG_CAUSE*REGWIDTH(x4)")


def two_ints(t: TestFile, lab: str, first: Value, desc: str) -> None:
    """Close a window that allowed two interrupts: two traps, the last LCOFI, the one before `first`."""
    t.emit("AI_OUTCOME", 20)
    t.check("x13", 2, lab, f"{desc}: number of interrupts taken")
    last = LCOFI_S
    if MUT == "lcofi_first":
        first, last = last, first
    t.check("x14", last, lab, f"{desc}: the second interrupt taken is LCOFI (lowest priority)")
    prev_cause(t, "x15")
    t.check("x15", first, lab, f"{desc}: the first interrupt taken is the higher-priority one")


def sti_writable(t: TestFile) -> None:
    """With Sstc, clear menvcfg.STCE so mip.STIP is software-writable (then written before use: issue 1636)."""
    with t.only_if("defined(SSTC_SUPPORTED)"):
        with t.rv64_only():
            t.emit("LI(a1, 1)", 2)
            t.emit("slli a1, a1, 63")
            csr_op(t, "CLEAR", "CSR_MENVCFG", "a1")
        with t.rv32_only():
            csr_op(t, "CLEAR", "CSR_MENVCFGH", imm=0x80000000)
    csr_op(t, "CLEAR", "CSR_MIP", imm=STIP)


def t_sip_sie_priority_bit_order() -> TestFile:
    t = new("sip_sie_priority_bit_order")
    t.describe(
        source=SUP,
        rule_text="Multiple simultaneous interrupts destined for supervisor mode are handled in the following "
        "decreasing priority order: SEI, SSI, STI, LCOFI.",
        context="Only the LCOFI position is tested here (the Sscofpmf suite); the order of the others belongs to "
        "the S suite. Interrupts are made pending with S-mode writes (sip.SSIP, sip.LCOFIP) and M-mode writes "
        "(mip.STIP, mip.SEIP through T-SBI; with Sstc, menvcfg.STCE is cleared first so mip.STIP is writable). The "
        "handler masks each interrupt's sie bit, so the second one is taken right after the first; both are read "
        "from the trap log.",
        plan='For X in SSI, STI, SEI, if implemented ("Each standard interrupt type ... might not be implemented": '
        "the sie bit is probed, and X is skipped when it reads 0), and if LCOFI is delegated to S (D, observed as in "
        "mip_lcofip_acc; mideleg[13] is WARL, norm:medeleg_mideleg_warl): X and LCOFI both pending and enabled in sie, "
        "sstatus.SIE=0; set sstatus.SIE in a window that allows two interrupts: X is taken first, then LCOFI "
        "(scause = interrupt | 13).",
    )
    t.li("x6", SIE)
    t.emit("csrc sstatus, x6")
    lcof_off(t)
    sti_writable(t)
    for name, bit, cause in (("SSI", SSIP, 1), ("STI", STIP, 5), ("SEI", SEIP, 9)):
        t.comment(f"{name} and LCOFI: is {name} implemented and delegated (sie bit writable)?")
        t.li("x6", bit)
        t.emit("csrs sie, x6")
        t.emit("csrr x1, sie")
        t.emit("and x1, x1, x6")
        t.emit("snez x1, x1")
        ld_deleg(t, "x8")
        t.emit("and x1, x1, x8")

        def pair(name: str = name, bit: int = bit, cause: int = cause) -> None:
            if name == "SSI":
                t.li("x6", SSIP)
                t.emit("csrs sip, x6")
            else:
                csr_op(t, "SET", "CSR_MIP", imm=bit)
            t.li("x6", LCOF)
            t.emit("csrs sip, x6")
            t.li("x6", LCOF | bit)
            t.emit("csrs sie, x6")
            lab = t.label(f"p{name}")
            t.allow(2)
            t.emit(f"{lab}:", 0)
            t.li("x6", SIE)
            t.emit("csrs sstatus, x6")
            delay(t)
            t.li("x6", SIE)
            t.emit("csrc sstatus, x6")
            if name != "SSI":
                csr_op(t, "CLEAR", "CSR_MIP", imm=bit)
            t.li("x6", LCOF | bit)
            t.emit("csrc sie, x6")
            lcof_off(t)
            two_ints(t, lab, X((1 << 31) | cause, (1 << 63) | cause), f"S-mode, {name} and LCOFI pending")

        t.either("x1", pair, lambda name=name: t.comment(f"{name} not implemented (sie bit read-only zero)"))
        t.li("x6", bit)
        t.emit("csrc sie, x6")
    return t


def t_intr_m_mode_pri() -> TestFile:
    t = new_sm("intr_m_mode_pri")
    t.describe(
        source=MAC,
        rule_text="Multiple simultaneous interrupts destined for M-mode are handled in the following decreasing "
        "priority order: MEI, MSI, MTI, SEI, SSI, STI, LCOFI.",
        context="Only the LCOFI position is tested here (the Sscofpmf suite). The test runs in M-mode with SSI, STI, "
        "SEI and LCOFI not delegated (mideleg bits 1, 5, 9, 13 clear) and makes them pending through mip. With Sstc, "
        "menvcfg.STCE is cleared so mip.STIP is writable. MEI, MSI and MTI need platform sources and are left to "
        "the Sm suite.",
        plan="For X in SSI, STI, SEI, if implemented (mie bit writable) and if X and LCOFI are both undelegated (their "
        "mideleg bits clear; they may be read-only one for lower-level interrupts, norm:mideleg_rd1_lower_level): X and LCOFI both pending and enabled in mie; set mstatus.MIE in "
        "a window that allows two interrupts: X is taken first, then LCOFI (mcause = interrupt | 13). mideleg is "
        "restored.",
    )
    t.emit("csrr x6, mideleg")
    st_slot(t, "x6", 12)
    t.li("x6", LCOF | SSIP | STIP | SEIP)
    t.emit("csrc mideleg, x6")
    lcof_off(t)
    sti_writable(t)
    for name, bit, cause in (("SSI", SSIP, 1), ("STI", STIP, 5), ("SEI", SEIP, 9)):
        t.comment(f"{name} and LCOFI: is {name} implemented (mie bit writable) and undelegated (mideleg bit 0)?")
        t.li("x6", bit)
        t.emit("csrs mie, x6")
        t.emit("csrr x7, mie")
        t.emit("and x7, x7, x6")
        t.emit("csrr x8, mideleg")
        t.li("x9", LCOF)
        t.emit("or x9, x9, x6")
        t.emit("and x8, x8, x9")
        t.emit("seqz x8, x8")
        t.emit("snez x7, x7")
        t.emit("and x7, x7, x8")

        def pair(name: str = name, bit: int = bit, cause: int = cause) -> None:
            t.li("x6", LCOF | bit)
            t.emit("csrs mip, x6")
            t.emit("csrs mie, x6")
            lab = t.label(f"p{name}")
            t.allow(2)
            t.emit(f"{lab}:", 0)
            t.li("x6", MIE)
            t.emit("csrs mstatus, x6")
            delay(t)
            t.li("x6", MIE)
            t.emit("csrc mstatus, x6")
            t.li("x6", LCOF | bit)
            t.emit("csrc mip, x6")
            t.emit("csrc mie, x6")
            two_ints(t, lab, X((1 << 31) | cause, (1 << 63) | cause), f"M-mode, {name} and LCOFI pending")

        t.either("x7", pair, lambda name=name: t.comment(f"{name} not implemented, or mideleg bit read-only one"))
        t.li("x6", bit)
        t.emit("csrc mie, x6")
    ld_slot(t, "x6", 12)
    t.emit("csrw mideleg, x6")
    return t


def t_hsint_priority() -> TestFile:
    t = new("hsint_priority", REQ + ["H"])
    t.describe(
        source=HYP,
        rule_text="Multiple simultaneous interrupts destined for HS-mode are handled in the following decreasing "
        "priority order: SEI, SSI, STI, SGEI, VSEI, VSSI, VSTI, LCOFI.",
        context="Only the LCOFI position is tested here (the Sscofpmf suite), against the VS-level interrupts just "
        "above it. HS-mode makes VSEI, VSSI and VSTI pending through hvip and keeps them in HS (hideleg bits 10, 2, 6 "
        "clear); LCOFI (hideleg[13]=0) is made pending in sip. LCOFI is destined for HS only when mideleg[13]=1; it "
        "is WARL, observed as D (" + DELEG_NOTE + "), and the test is skipped when D=0.",
        plan="For X in VSEI, VSSI, VSTI: X (hvip, hie) and LCOFI (sip, sie) both pending and enabled, sstatus.SIE=0; "
        "set sstatus.SIE in a window that allows two interrupts: X is taken first (scause 10, 2 or 6), then LCOFI.",
    )
    t.li("x6", SIE | SPIE)
    t.emit("csrc sstatus, x6")
    lcof_off(t)
    t.li("x6", LCOF | 0x444)
    t.emit("csrc CSR_HIDELEG, x6")

    def pairs() -> None:
        for name, bit, cause in (("VSEI", 0x400, 10), ("VSSI", 0x4, 2), ("VSTI", 0x40, 6)):
            t.comment(f"{name} and LCOFI")
            t.li("x6", bit)
            t.emit("csrs CSR_HVIP, x6")
            t.emit("csrs CSR_HIE, x6")
            t.li("x6", LCOF)
            t.emit("csrs sip, x6")
            t.emit("csrs sie, x6")
            lab = t.label(f"p{name}")
            t.allow(2)
            t.emit(f"{lab}:", 0)
            t.li("x6", SIE)
            t.emit("csrs sstatus, x6")
            delay(t)
            t.li("x6", SIE)
            t.emit("csrc sstatus, x6")
            t.li("x6", bit)
            t.emit("csrc CSR_HVIP, x6")
            t.emit("csrc CSR_HIE, x6")
            lcof_off(t)
            two_ints(t, lab, X((1 << 31) | cause, (1 << 63) | cause), f"HS-mode, {name} and LCOFI pending")

    ld_deleg(t, "x1")
    t.either("x1", pairs, lambda: t.comment("LCOFI is not delegated to HS (mideleg[13]=0): it is not destined for HS"))
    return t


# ---------------------------------------------------------------- RV32 mhpmevent*h
def t_mhpmeventh_presence() -> TestFile:
    t = new_sm("mhpmeventh_presence")
    t.describe(
        source=MAC,
        rule_text="The mhpmevent_n_h CSRs are provided only if the sscofpmf extension is implemented.",
        context="RV32 only (the h CSRs do not exist on RV64; the file passes trivially there). With Sscofpmf they "
        "must exist, so M-mode reads and writes of mhpmevent3h..31h do not trap. The case without Sscofpmf needs a "
        "hart without it and is not tested here.",
        issues=ISSUE_1520,
        plan="For n = 3..31, in M-mode trap windows: csrr of mhpmevent_n_h and csrw of the value read back.",
    )
    with t.rv32_only():
        for n in range(3, 32):
            csr = f"0x{0x720 + n:x}"
            if MUT == "no_mhpmeventh" and n == 3:
                t.window("M", [f"csrr x7, {csr}"], 2, f"read of mhpmevent{n}h", [0, enc(0x720 + n, 2, 7, 0)])
            else:
                t.window("M", [f"csrr x7, {csr}"], "ok", f"read of mhpmevent{n}h")
            t.window("M", [f"csrw {csr}, x7"], "ok", f"write of mhpmevent{n}h")
    return t


def t_mcycleh_minstreth_mhpmh_op() -> TestFile:
    t = new("mcycleh_minstreth_mhpmh_op")
    t.describe(
        source=MAC,
        rule_text="reads of the mcycleh, minstreth, mhpmcounter_n_h, and mhpmevent_n_h CSRs return bits 63-32 of "
        "the corresponding register, and writes change only bits 63-32.",
        context="RV32 only; only the mhpmevent_n_h part is tested here (it exists only with Sscofpmf). The "
        "counter halves belong to the Zicntr/Zihpm suites. On the designated counter, bits 63:32 hold OF and xINH "
        "(written through T-SBI). The event field in bits 31:0 is WARL, so it is compared with its own value "
        "before the high-half write, and written only with RVMODEL_MHPMEVENT_VAL or 0.",
        plan="1. mhpmevent = RVMODEL_MHPMEVENT_VAL; mhpmeventh = OF|MINH|SINH: mhpmeventh reads back those bits "
        "(bits 31:26 checked).\n"
        "2. A write of mhpmeventh (0, then OF|UINH) leaves mhpmevent (bits 31:0) as it read before.\n"
        "3. A write of mhpmevent (0, then the event) leaves mhpmeventh (bits 31:26) as written.",
    )
    with t.rv32_only():
        csr_op(t, "WRITE", EV, imm="RVMODEL_MHPMEVENT_VAL")
        csr_op(t, "WRITE", EVH, imm=hi("M", "S", of=True))
        lab = t.label("h1")
        t.emit(f"{lab}:", 0)
        csr_op(t, "READ", EVH)
        t.li("x7", hi(*ALL, of=True))
        t.emit("and x6, a0, x7")
        t.check("x6", hi("M", "S", of=True), lab, "mhpmeventh bits 31:26 after writing OF|MINH|SINH")
        for hv in (0, hi("U", of=True)):
            csr_op(t, "READ", EV)
            t.emit("mv x1, a0")
            csr_op(t, "WRITE", EVH, imm=hv)
            lab = t.label("lo")
            t.emit(f"{lab}:", 0)
            csr_op(t, "READ", EV)
            if MUT == "eventh_clears_low":
                t.check("a0", 0, lab, f"mhpmevent after writing mhpmeventh = {hv:#x}")
            else:
                t.emit("xor x6, a0, x1")
                t.check("x6", 0, lab, f"mhpmevent (bits 31:0) unchanged by writing mhpmeventh = {hv:#x}")
        for lo in ("0", "RVMODEL_MHPMEVENT_VAL"):
            csr_op(t, "WRITE", EV, imm=lo)
            lab = t.label("hi")
            t.emit(f"{lab}:", 0)
            csr_op(t, "READ", EVH)
            t.li("x7", hi(*ALL, of=True))
            t.emit("and x6, a0, x7")
            t.check("x6", hi("U", of=True), lab, f"mhpmeventh bits 31:26 unchanged by writing mhpmevent = {lo}")
        csr_op(t, "WRITE", EVH, imm=hi(*ALL))
        csr_op(t, "WRITE", EV, imm=0)
    return t


MUTANTS = {
    "of_cleared_by_write": "a counter write clears OF",
    "of_not_sticky": "OF clears when the counter keeps counting after an overflow",
    "sinh_ignored": "SINH does not stop counting in S-mode",
    "uinh_ignored": "UINH does not stop counting in U-mode",
    "vs_uses_sinh": "VS-mode counting is filtered by SINH instead of VSINH",
    "minh_ignored": "MINH does not stop counting in M-mode",
    "signed_overflow": "overflow is detected as signed overflow (crossing into the top bit)",
    "overflow_32": "overflow is detected at bit 31 on a counter with more than 32 bits",
    "no_request": "a wrap with OF=0 does not request LCOFI",
    "of1_requests": "a wrap with OF=1 still requests LCOFI",
    "write_overflow": "writing a counter across the wrap counts as an overflow",
    "of_not_set": "an overflow request does not set OF",
    "lcofip_level": "LCOFIP follows the OF level, so clearing it while OF=1 does not stick",
    "lcofip_on_count": "LCOFIP is set by counting without an overflow",
    "lcofip_needs_deleg": "mip.LCOFIP is not set when LCOFI is not delegated",
    "scountovf_shift": "scountovf bit X-3 holds mhpmeventX.OF",
    "scountovf_writable": "scountovf is writable from S-mode with csrrw",
    "m_gated": "M-mode reads of scountovf are masked by mcounteren",
    "s_ignores_mcounteren": "S-mode reads of scountovf are not masked by mcounteren",
    "s_gated_by_scounteren": "S-mode reads of scountovf are masked by scounteren",
    "vs_ignores_hcounteren": "VS-mode reads of scountovf are not masked by hcounteren",
    "vs_ignores_mcounteren": "VS-mode reads of scountovf are not masked by mcounteren",
    "ctrl_hcen_ignored": "VS-mode hpmcounter and scountovf access ignore hcounteren",
    "mip_lcofip_ro": "mip.LCOFIP is read-only to M-mode software",
    "lcofie_ignored": "LCOFI is taken without mie.LCOFIE",
    "deleg_ignored": "a delegated LCOFI is still taken in M-mode",
    "sip_lcofip_ro": "sip.LCOFIP is read-only to S-mode software",
    "u_needs_sie": "LCOFI in U-mode is gated by sstatus.SIE",
    "vsip_alias_undelegated": "vsip.LCOFIP aliases sip.LCOFIP even with hideleg[13]=0",
    "lcofi_first": "LCOFI is taken before higher-priority interrupts",
    "no_mhpmeventh": "mhpmevent3h does not exist (illegal-instruction)",
    "eventh_clears_low": "a write of mhpmeventh clears mhpmevent bits 31:0",
}


def main() -> None:
    for t in gen():
        p = t.write()
        print(f"{p.relative_to(p.parents[2])}: ~{t.ninst} instructions")


if __name__ == "__main__":
    main()
