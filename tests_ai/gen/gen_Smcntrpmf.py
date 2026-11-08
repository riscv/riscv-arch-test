#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate tests_ai/Smcntrpmf: privilege-mode filtering of cycle and instret (mcyclecfg, minstretcfg).

Smcntrpmf is a machine-level extension: its CSRs are M-mode CSRs that T-SBI does not offer, so every test boots to
M-mode (boot="M") and requires Sm. Lower modes are entered with MRET (MPV=1 for VS/VU) and left through T-SBI. In a
test that boots to M-mode no exception is delegated, so every trap (including the T-SBI ecall) goes to M-mode.

Counting checks use the M-mode counters mcycle/minstret, zeroed in M-mode before a block of instructions runs in
the mode under test and read in M-mode after it. M-mode is inhibited in every check that runs a lower mode, so the
entry (MRET, from an inhibited mode), the T-SBI ecall (an exception: not retired) and the handler do not count.
Counts are exact only where the spec fixes them (instret over retired instructions, and 0 for inhibited modes);
cycle is only checked for zero versus nonzero.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent))
from aigen import POOL_TRAP, TestFile
from cntrlib import (
    INH_HI,
    ISSUE,
    MODE_COND,
    MODES,
    H,
    enter,
    guard,
    hx,
    inh,
    ld,
    mpv,
    st,
)

if TYPE_CHECKING:
    from collections.abc import Callable

SUITE = "Smcntrpmf"
MUT = os.environ.get("AI_MUTANT", "")
SRC = "src/priv/smcntrpmf.adoc"
MARCH = "rv${XLEN}i_zicsr_zifencei"
REQ = ["I", "Sm", "Zicntr", "Smcntrpmf"]

MUTANTS = {
    "minh_ignored": "MINH does not inhibit instret in M-mode",
    "inh_ignored_lower": "an xINH bit for a lower mode (S/U/VS/VU) does not inhibit counting in that mode",
    "cfg_crossed": "mcyclecfg filters instret (and minstretcfg filters cycle)",
    "wpri_writable": "bits 57:0 of mcyclecfg/minstretcfg hold the value written",
    "bit63_writable": "bit 63 of mcyclecfg/minstretcfg is writable",
    "uinh_ro0": "UINH is read-only zero although U-mode is implemented",
    "rv32_low_aliases_high": "RV32: a write of mcyclecfg also writes mcyclecfgh",
    "all_zero_m_only": "with every xINH bit clear, only M-mode counts",
    "count_off_by_one": "instret counts one extra instruction per block",
    "exception_retires": "an instruction that traps to a more privileged mode increments instret",
    "xret_not_counted": "an xRET from a counting mode does not increment instret",
}

CFG = {"cycle": ("CSR_MCYCLECFG", "CSR_MCYCLECFGH"), "instret": ("CSR_MINSTRETCFG", "CSR_MINSTRETCFGH")}
CTR = {"cycle": ("mcycle", "mcycleh"), "instret": ("minstret", "minstreth")}
UCTR = {"cycle": "cycle", "instret": "instret"}
ALLINH = inh(*MODES)
CTRS = ("cycle", "instret")
# scratch slots: measured counters (lo, hi) for cycle and instret
SLOT = {("cycle", "lo"): 0, ("cycle", "hi"): 1, ("instret", "lo"): 2, ("instret", "hi"): 3}

COUNT_NOTE = (
    "Counting is measured in M-mode: both counters are zeroed, the block runs in the mode under test, and the "
    "counters are read back. A block in a lower mode is entered with MRET (from M-mode, inhibited, so it is not "
    "counted) and left with the T-SBI GOTO (li a0 then ecall; the ecall raises an exception and does not retire). "
    "With only the mode under test counting, instret therefore counts the block plus the li: n+1. Bounds [n, n+3] "
    "allow for the RV32 two-write zeroing; exact differences between two block lengths fix the per-instruction count."
)


def new(rule: str, required: list[str] | None = None, rv32only: bool = False) -> TestFile:
    t = TestFile(SUITE, rule, required=required or REQ, march=MARCH, boot="M", pool=POOL_TRAP)
    t.extra_data += [".p2align 3", "pmf_data:", "  .fill 4, 8, 0"]
    return t


def implemented_inh() -> list[tuple[str, int]]:
    """(preprocessor condition, implemented xINH bits) for each hart shape: M, MU, MSU, MSU+H."""
    m = inh("M")
    return [
        ("!defined(U_SUPPORTED)", m),
        ("defined(U_SUPPORTED) && !defined(S_SUPPORTED)", m | inh("U")),
        ("defined(S_SUPPORTED) && !defined(H_SUPPORTED)", m | inh("S", "U")),
        (H, ALLINH),
    ]


def cfg_set(t: TestFile, ctr: str, hv: int, note: str = "") -> None:
    """mcyclecfg/minstretcfg = hv in bits 63:32 (mcyclecfgh/minstretcfgh on RV32; the low half is not written)."""
    lo, hi = CFG[ctr]
    t.load("x6", hx(hv), note or f"{ctr}cfg high word {hv:#010x}")
    with t.rv64_only():
        t.emit(f"csrw {lo}, x6")
    with t.rv32_only():
        t.emit(f"csrw {hi}, x6")


def cfgs(t: TestFile, cyc: int, ins: int) -> None:
    cfg_set(t, "cycle", cyc)
    cfg_set(t, "instret", ins)


def cfg_hi(t: TestFile, ctr: str, dst: str) -> None:
    """dst = bits 63:32 of mcyclecfg/minstretcfg."""
    lo, hi = CFG[ctr]
    with t.rv64_only():
        t.emit(f"csrr {dst}, {lo}")
        t.emit(f"srli {dst}, {dst}, 32")
    with t.rv32_only():
        t.emit(f"csrr {dst}, {hi}")


def zero(t: TestFile) -> None:
    for c in CTRS:
        lo, hi = CTR[c]
        t.emit(f"csrw {lo}, x0")
        with t.rv32_only():
            t.emit(f"csrw {hi}, x0")


def read_store(t: TestFile) -> None:
    """Store mcycle/minstret (lo, hi) into the scratch slots. Uses x6."""
    for c in ("instret", "cycle"):
        lo, hi = CTR[c]
        t.emit(f"csrr x6, {lo}")
        st(t, "x6", SLOT[(c, "lo")])
        with t.rv32_only():
            t.emit(f"csrr x6, {hi}")
        with t.rv64_only():
            t.emit("li x6, 0")
        st(t, "x6", SLOT[(c, "hi")])


def nops(n: int) -> list[str]:
    return ["addi x0, x0, 0"] * n


def mixed(n: int) -> list[str]:
    """n instructions of mixed kinds, each retiring once (x9 = pmf_data, set before the block)."""
    kinds = [
        "addi x6, x6, 1",
        "LREG x7, 0(x9)",
        "SREG x6, REGWIDTH(x9)",
        "beq x0, x0, 1f\n1:",
        "bne x0, x9, 1f\n1:",
        "bne x0, x0, 1f\n1:",
        "jal x0, 1f\n1:",
        "xor x8, x6, x7",
    ]
    return [kinds[i % len(kinds)] for i in range(n)]


def block(t: TestFile, mode: str, lines: list[str], desc: str) -> None:
    """Zero both counters in M-mode, run lines in `mode`, return to M-mode, and store the counters."""
    t.comment(f"block: {desc}")
    t.la("x9", "pmf_data")
    zero(t)
    if mode != "M":
        enter(t, mode)
    for ln in lines:
        t.emit(ln)
    if mode != "M":
        t.leave()
    read_store(t)


def load_ctr(t: TestFile, ctr: str, lo: str, hi: str) -> None:
    ld(t, lo, SLOT[(ctr, "lo")])
    ld(t, hi, SLOT[(ctr, "hi")])


def chk_zero(t: TestFile, ctr: str, desc: str, flip: bool = False) -> None:
    lab = t.label(f"{ctr}0")
    t.emit(f"{lab}:", 0)
    load_ctr(t, ctr, "x7", "x8")
    t.emit("or x7, x7, x8")
    t.emit("snez x7, x7")
    t.check("x7", 1 if flip else 0, lab, f"{ctr} moved (1) or not (0): {desc}; expect it frozen")


def chk_moved(t: TestFile, ctr: str, desc: str, flip: bool = False) -> None:
    lab = t.label(f"{ctr}m")
    t.emit(f"{lab}:", 0)
    load_ctr(t, ctr, "x7", "x8")
    t.emit("or x7, x7, x8")
    t.emit("snez x7, x7")
    t.check("x7", 0 if flip else 1, lab, f"{ctr} moved (1) or not (0): {desc}; expect it counting")


def chk_range(t: TestFile, ctr: str, lo_b: int, hi_b: int, desc: str) -> None:
    """lo_b <= counter <= hi_b (64-bit; hi_b < 2^31)."""
    lab = t.label(f"{ctr}r")
    t.emit(f"{lab}:", 0)
    load_ctr(t, ctr, "x7", "x8")
    t.emit(f"LI(x6, {lo_b})", 2)
    t.emit("sub x7, x7, x6")
    t.emit(f"LI(x6, {hi_b - lo_b + 1})", 2)
    t.emit("sltu x7, x7, x6")
    t.emit("seqz x8, x8")
    t.emit("and x7, x7, x8")
    t.check("x7", 1, lab, f"{ctr} in [{lo_b}, {hi_b}]: {desc}")


def keep(t: TestFile, ctr: str, slot: int) -> None:
    """Copy the measured low word of ctr to another slot."""
    ld(t, "x7", SLOT[(ctr, "lo")])
    st(t, "x7", slot)


def chk_diff(t: TestFile, ctr: str, slot: int, diff: int, desc: str) -> None:
    """(measured low word) - (slot) == diff exactly."""
    lab = t.label(f"{ctr}d")
    t.emit(f"{lab}:", 0)
    ld(t, "x7", SLOT[(ctr, "lo")])
    ld(t, "x8", slot)
    t.emit("sub x7, x7, x8")
    t.check("x7", diff, lab, f"{ctr} difference between the two blocks: {desc}")


def setup(t: TestFile) -> None:
    """Common setup: interrupts off; mcountinhibit = 0 (it is optional: an illegal-instruction trap is accepted, and
    an unimplemented mcountinhibit behaves as zero)."""
    t.li("x6", 0xA)
    t.emit("csrc mstatus, x6")  # MIE, SIE
    t.window("M", ["csrw mcountinhibit, x0"], ["ok", 2], "setup: clear mcountinhibit", [0, 0x32001073])


def teardown(t: TestFile) -> None:
    cfgs(t, 0, 0)


def each_mode(t: TestFile, body: Callable[[str], object], modes: tuple[str, ...] = MODES) -> None:
    for m in modes:
        guard(t, MODE_COND[m], lambda m=m: body(m))


# ---------------------------------------------------------------- tests
def gen() -> list[TestFile]:
    return [
        t_mcyclecfg_sz(),
        t_mcyclecfg_op(),
        t_rv32_high_access(),
        t_all_xinh_zero(),
        t_unimplemented_mode_bits(),
        t_counter_inhibited_behavior(),
        t_cycle_counting(),
        t_instret_non_inhibited(),
        t_instret_exception(),
        t_instret_xret(),
    ]


def rule(name: str) -> str:
    return {
        "mcyclecfg_sz": "mcyclecfg and minstretcfg are 64-bit registers",
        "mcyclecfg_op": "configure privilege mode filtering for the cycle and instret counters, respectively.",
        "rv32_high_access": "In RV32 only, accesses to the mcyclecfg and minstretcfg CSRs access the low 32 bits, "
        "while accesses to the mcyclecfgh and minstretcfgh CSRs access the high 32 bits of mcyclecfg and "
        "minstretcfg, respectively.",
        "all_xinh_zero": "When all xINH bits are zero, event counting is enabled in all modes.",
        "unimplemented_mode_bits": "For each bit in 61:58, if the associated privilege mode is not implemented, "
        "the bit is read-only zero.",
        "csr_supervisor_access": "The content of these registers may be accessible from Supervisor level if the "
        "Smcdeleg/Ssccfg extensions are implemented.",
        "counter_inhibited_behavior": "The fundamental behavior of cycle and instret is modified in that counting "
        "does not occur while executing in an inhibited privilege mode.",
        "cycle_counting": "The cycle counter will simply count CPU cycles while the CPU is in a non-inhibited "
        "privilege mode.",
        "instret_non_inhibited": "instructions that retire in a non-inhibited mode increment instret, and "
        "instructions that retire in an inhibited mode do not.",
        "instret_exception": "The former [instructions that cause synchronous exceptions to a more privileged "
        "mode] are not considered to retire, and hence do not increment instret.",
        "instret_xret": "The latter [xRET instructions that return to a less privileged mode] do retire, and "
        "should increment instret only if the originating privilege mode is not inhibited.",
    }[name]


FORMAT = (
    "Format (bits 63:58): 63 is 0 (read-only, no OF), 62 MINH, 61 SINH, 60 UINH, 59 VSINH, 58 VUINH; 57:0 are WPRI, "
    'which are read-only zero in an implementation that does not furnish them (norm:Zicsr_wpri_roz, "For forward '
    'compatibility, implementations that do not furnish these fields must make them read-only zero").'
)


def t_mcyclecfg_sz() -> TestFile:
    t = new("mcyclecfg_sz")
    t.describe(
        source=SRC,
        rule_text=rule("mcyclecfg_sz"),
        context=FORMAT + " On RV64 the whole register is one CSR; on RV32 bits 63:32 are in mcyclecfgh/minstretcfgh "
        "and bits 31:0 (all WPRI) in mcyclecfg/minstretcfg. Bits for modes the hart lacks are read-only zero "
        "(unimplemented_mode_bits), so the expected value depends on S_SUPPORTED, U_SUPPORTED and H_SUPPORTED.",
        plan="For mcyclecfg and minstretcfg:\n"
        "1. Write all ones (RV64: the CSR; RV32: the high and the low CSR): bits 63:32 read MINH plus the "
        "implemented-mode bits, and bits 31:0 read 0.\n"
        "2. Write each xINH bit alone: it reads back alone (when its mode is implemented; else 0).\n"
        "3. Write 0: reads 0. csrs/csrc of MINH set and clear it alone.\n"
        "4. The two registers are distinct: all ones in mcyclecfg leaves minstretcfg 0, and the reverse.",
    )
    setup(t)
    for ctr in CTRS:
        lo, hi = CFG[ctr]
        other = "instret" if ctr == "cycle" else "cycle"
        cfgs(t, 0, 0)
        t.comment(f"{ctr}cfg: all ones")
        lab = t.label("ones")
        t.emit("li x6, -1")
        t.emit(f"{lab}:", 0)
        t.emit(f"csrw {lo}, x6")
        with t.rv32_only():
            t.emit(f"csrw {hi}, x6")
        cfg_hi(t, ctr, "x7")
        for cond, bits in implemented_inh():
            exp = bits | (1 << 31 if MUT == "bit63_writable" else 0)
            with t.only_if(cond):
                t.check("x7", exp, lab, f"{ctr}cfg bits 63:32 after writing all ones")
        t.emit(f"csrr x7, {lo}")
        with t.rv64_only():
            t.emit("slli x7, x7, 32")
            t.emit("srli x7, x7, 32")
        t.check("x7", 0xFFFFFFFF if MUT == "wpri_writable" else 0, lab, f"{ctr}cfg bits 31:0 (WPRI) after all ones")
        cfg_hi(t, other, "x7")
        t.check("x7", 0, lab, f"{other}cfg bits 63:32 after writing all ones to {ctr}cfg")
        for m in MODES:
            lab = t.label(f"bit{m}")
            t.emit(f"{lab}:", 0)
            cfg_set(t, ctr, INH_HI[m], f"{m}INH alone")
            cfg_hi(t, ctr, "x7")
            cond = MODE_COND[m]
            if cond:
                with t.only_if(cond):
                    t.check("x7", INH_HI[m], lab, f"{ctr}cfg bits 63:32 after writing {m}INH alone")
                with t.only_if(f"!({cond})"):
                    t.check("x7", 0, lab, f"{ctr}cfg bits 63:32 after writing {m}INH alone ({m} not implemented)")
            else:
                t.check("x7", INH_HI[m], lab, f"{ctr}cfg bits 63:32 after writing {m}INH alone")
        lab = t.label("zero")
        t.emit(f"{lab}:", 0)
        cfg_set(t, ctr, 0, "0")
        cfg_hi(t, ctr, "x7")
        t.check("x7", 0, lab, f"{ctr}cfg bits 63:32 after writing 0")
        lab = t.label("csrs")
        t.load("x6", hx(INH_HI["M"]), "MINH")
        t.emit(f"{lab}:", 0)
        with t.rv64_only():
            t.emit(f"csrs {lo}, x6")
        with t.rv32_only():
            t.emit(f"csrs {hi}, x6")
        cfg_hi(t, ctr, "x7")
        t.check("x7", INH_HI["M"], lab, f"{ctr}cfg bits 63:32 after csrs MINH")
        with t.rv64_only():
            t.emit(f"csrc {lo}, x6")
        with t.rv32_only():
            t.emit(f"csrc {hi}, x6")
        cfg_hi(t, ctr, "x7")
        t.check("x7", 0, lab, f"{ctr}cfg bits 63:32 after csrc MINH")
    teardown(t)
    return t


def t_mcyclecfg_op() -> TestFile:
    t = new("mcyclecfg_op")
    t.describe(
        source=SRC,
        rule_text=rule("mcyclecfg_op"),
        context="mcyclecfg filters cycle and minstretcfg filters instret; neither filters the other counter "
        "(similar mechanisms must not cross). " + COUNT_NOTE,
        plan="Blocks of 40 instructions:\n"
        "1. M-mode: mcyclecfg = MINH, minstretcfg = 0: cycle frozen, instret in [40, 42]. mcyclecfg = 0, "
        "minstretcfg = MINH: cycle counts, instret frozen.\n"
        "2. S-mode (with S) and U-mode (with U), M inhibited in both registers: mcyclecfg also inhibits the mode, "
        "minstretcfg does not: cycle frozen, instret in [40, 43]; then the reverse.",
    )
    setup(t)
    n = 40
    m_inh = inh("M")
    cx = MUT == "cfg_crossed"
    cfgs(t, m_inh, 0)
    block(t, "M", nops(n), "M-mode, mcyclecfg = MINH, minstretcfg = 0")
    chk_zero(t, "cycle", "M-mode block, mcyclecfg = MINH", flip=cx)
    if cx:
        chk_zero(t, "instret", "M-mode block, minstretcfg = 0 (crossed)")
    else:
        chk_range(t, "instret", n, n + 2, "M-mode block of 40, minstretcfg = 0")
    cfgs(t, 0, m_inh)
    block(t, "M", nops(n), "M-mode, mcyclecfg = 0, minstretcfg = MINH")
    chk_moved(t, "cycle", "M-mode block, mcyclecfg = 0", flip=cx)
    chk_zero(t, "instret", "M-mode block, minstretcfg = MINH", flip=cx)

    def lower(m: str) -> None:
        cfgs(t, m_inh | INH_HI[m], m_inh)
        block(t, m, nops(n), f"{m}-mode, mcyclecfg = MINH|{m}INH, minstretcfg = MINH")
        chk_zero(t, "cycle", f"{m}-mode block, mcyclecfg inhibits {m}", flip=cx)
        if cx:
            chk_zero(t, "instret", f"{m}-mode block, minstretcfg does not inhibit {m} (crossed)")
        else:
            chk_range(t, "instret", n, n + 3, f"{m}-mode block of 40, minstretcfg does not inhibit {m}")
        cfgs(t, m_inh, m_inh | INH_HI[m])
        block(t, m, nops(n), f"{m}-mode, mcyclecfg = MINH, minstretcfg = MINH|{m}INH")
        chk_moved(t, "cycle", f"{m}-mode block, mcyclecfg does not inhibit {m}", flip=cx)
        chk_zero(t, "instret", f"{m}-mode block, minstretcfg inhibits {m}", flip=cx)

    each_mode(t, lower, ("S", "U"))
    teardown(t)
    return t


def t_rv32_high_access() -> TestFile:
    t = new("rv32_high_access")
    t.describe(
        source=SRC,
        rule_text=rule("rv32_high_access"),
        context="RV32 only (the file passes trivially on RV64, where mcyclecfgh/minstretcfgh do not exist). "
        + FORMAT
        + " So on RV32 the low CSR reads 0 and the xINH bits are bits 30:26 of the high CSR.",
        plan="RV32, for mcyclecfg and minstretcfg:\n"
        "1. Write all ones to the high CSR: the high CSR reads MINH plus implemented-mode bits; the low CSR still "
        "reads 0.\n"
        "2. Write all ones to the low CSR: the high CSR is unchanged; write 0 to the low CSR: unchanged again.\n"
        "3. Write 0 to the high CSR: it reads 0.\n"
        "4. The high CSR bit 30 is MINH: with it set, the counter does not count over a 40-instruction M-mode "
        "block; with only bit 30 of the low CSR written (a WPRI bit), it counts.\n"
        "5. csrrs/csrrc on the high CSR return the old high word.",
    )
    setup(t)
    with t.rv32_only():
        for ctr in CTRS:
            lo, hi = CFG[ctr]
            cfgs(t, 0, 0)
            lab = t.label("hi1")
            t.emit("li x6, -1")
            t.emit(f"{lab}:", 0)
            t.emit(f"csrw {hi}, x6")
            t.emit(f"csrr x7, {hi}")
            for cond, bits in implemented_inh():
                with t.only_if(cond):
                    t.check("x7", bits, lab, f"{ctr}cfgh after writing all ones to it")
            t.emit(f"csrr x7, {lo}")
            t.check("x7", 0, lab, f"{ctr}cfg (low) after writing all ones to {ctr}cfgh")
            for v in (-1, 0):
                lab = t.label("lo")
                t.emit(f"li x6, {v}")
                t.emit(f"{lab}:", 0)
                t.emit(f"csrw {lo}, x6")
                t.emit(f"csrr x7, {hi}")
                for cond, bits in implemented_inh():
                    with t.only_if(cond):
                        t.check(
                            "x7",
                            (0 if MUT == "rv32_low_aliases_high" and v == 0 else bits),
                            lab,
                            f"{ctr}cfgh after writing {v & 0xFFFFFFFF:#x} to {ctr}cfg (low): unchanged",
                        )
            lab = t.label("hi0")
            t.emit(f"{lab}:", 0)
            t.emit(f"csrw {hi}, x0")
            t.emit(f"csrr x7, {hi}")
            t.check("x7", 0, lab, f"{ctr}cfgh after writing 0")
            lab = t.label("rs")
            t.emit(f"LI(x6, {INH_HI['M']:#x})", 2)
            t.emit(f"{lab}:", 0)
            t.emit(f"csrrs x7, {hi}, x6")
            t.check("x7", 0, lab, f"csrrs of {ctr}cfgh returns the old value 0")
            t.emit(f"csrrc x7, {hi}, x6")
            t.check("x7", INH_HI["M"], lab, f"csrrc of {ctr}cfgh returns the old value MINH")
        n = 40
        for ctr in CTRS:
            lo, hi = CFG[ctr]
            cfgs(t, 0, 0)
            t.emit(f"LI(x6, {INH_HI['M']:#x})", 2)
            t.emit(f"csrw {hi}, x6")
            block(t, "M", nops(n), f"{ctr}cfgh = MINH (bit 30)")
            chk_zero(t, ctr, f"M-mode block with {ctr}cfgh bit 30 (MINH) set")
            t.emit(f"csrw {hi}, x0")
            t.emit(f"LI(x6, {INH_HI['M']:#x})", 2)
            t.emit(f"csrw {lo}, x6")
            block(t, "M", nops(n), f"{ctr}cfg (low) bit 30 written")
            if ctr == "cycle":
                chk_moved(t, ctr, "M-mode block with only bit 30 of mcyclecfg (low, WPRI) written")
            else:
                chk_range(t, ctr, n, n + 2, "M-mode block of 40 with only bit 30 of minstretcfg (low, WPRI) written")
            t.emit(f"csrw {lo}, x0")
    teardown(t)
    return t


def t_all_xinh_zero() -> TestFile:
    t = new("all_xinh_zero")
    t.describe(
        source=SRC,
        rule_text=rule("all_xinh_zero"),
        context="With mcyclecfg = minstretcfg = 0 every mode counts, including M-mode, so a lower-mode block also "
        "counts the entry, the T-SBI handler and the return: only lower bounds (and an upper bound of a few "
        "thousand) are checked there. " + COUNT_NOTE,
        plan="mcyclecfg = minstretcfg = 0:\n"
        "1. M-mode block of 40: instret in [40, 42], cycle counts.\n"
        "2. Blocks of 40 in S, U, VS and VU (as implemented): instret in [41, 4000], cycle counts.\n"
        "3. The same blocks with every xINH set: both frozen (the zero setting is what enables counting).",
    )
    setup(t)
    n = 40
    cfgs(t, 0, 0)
    block(t, "M", nops(n), "M-mode, all xINH zero")
    chk_moved(t, "cycle", "M-mode block, all xINH zero")
    chk_range(t, "instret", n, n + 2, "M-mode block of 40, all xINH zero")

    def lower(m: str) -> None:
        cfgs(t, 0, 0)
        block(t, m, nops(n), f"{m}-mode, all xINH zero")
        chk_moved(t, "cycle", f"{m}-mode block, all xINH zero", flip=MUT == "all_zero_m_only")
        if MUT == "all_zero_m_only":
            chk_zero(t, "instret", f"{m}-mode block, all xINH zero (mutant: only M counts)")
        else:
            chk_range(t, "instret", n + 1, 4000, f"{m}-mode block of 40 plus entry/exit, all xINH zero")
        cfgs(t, ALLINH, ALLINH)
        block(t, m, nops(n), f"{m}-mode, all xINH set")
        chk_zero(t, "cycle", f"{m}-mode block, all xINH set")
        chk_zero(t, "instret", f"{m}-mode block, all xINH set")

    each_mode(t, lower, ("S", "U", "VS", "VU"))
    teardown(t)
    return t


def t_unimplemented_mode_bits() -> TestFile:
    t = new("unimplemented_mode_bits")
    t.describe(
        source=SRC,
        rule_text=rule("unimplemented_mode_bits"),
        context="Bits 61:58 are SINH, UINH, VSINH, VUINH (bits 29:26 of mcyclecfgh/minstretcfgh on RV32). S-mode "
        "is implemented with S_SUPPORTED, U-mode with U_SUPPORTED, VS and VU with H_SUPPORTED. The bits of "
        "implemented modes are fields of the register and hold the value written. Run on M-only, M/U and full "
        "harts.",
        plan="For mcyclecfg and minstretcfg:\n"
        "1. Write all ones to bits 61:58 (csrw of the four bits): they read back as the implemented-mode bits.\n"
        "2. csrs of each bit alone from 0: it reads 1 if its mode is implemented, else 0.\n"
        "3. Write 0x55../0xAA.. patterns (all ones and 0 in the high word plus random): bits 61:58 read pattern AND "
        "implemented.",
    )
    setup(t)
    four = inh("S", "U", "VS", "VU")
    for ctr in CTRS:
        lo, hi = CFG[ctr]
        for pat in (four, 0x55555555, 0xAAAAAAAA, t.rand(32)):
            cfgs(t, 0, 0)
            lab = t.label("pat")
            t.emit(f"{lab}:", 0)
            cfg_set(t, ctr, pat & 0xBFFFFFFF if pat != four else pat, f"pattern {pat:#010x} (MINH clear)")
            cfg_hi(t, ctr, "x7")
            t.emit(f"LI(x6, {four:#x})", 2)
            t.emit("and x7, x7, x6")
            for cond, bits in implemented_inh():
                b = bits & four & pat
                if MUT == "uinh_ro0":
                    b &= ~INH_HI["U"]
                with t.only_if(cond):
                    t.check("x7", b, lab, f"{ctr}cfg bits 61:58 after writing {pat:#010x} to bits 63:32")
        for m in ("S", "U", "VS", "VU"):
            cfgs(t, 0, 0)
            lab = t.label(f"s{m}")
            t.load("x6", hx(INH_HI[m]), f"{m}INH")
            t.emit(f"{lab}:", 0)
            with t.rv64_only():
                t.emit(f"csrs {lo}, x6")
            with t.rv32_only():
                t.emit(f"csrs {hi}, x6")
            cfg_hi(t, ctr, "x7")
            cond = MODE_COND[m]
            assert cond
            exp = 0 if MUT == "uinh_ro0" and m == "U" else INH_HI[m]
            with t.only_if(cond):
                t.check("x7", exp, lab, f"{ctr}cfg bits 63:32 after csrs {m}INH ({m} implemented)")
            with t.only_if(f"!({cond})"):
                t.check("x7", 0, lab, f"{ctr}cfg bits 63:32 after csrs {m}INH ({m} not implemented: read-only 0)")
    teardown(t)
    return t


def t_counter_inhibited_behavior() -> TestFile:
    t = new("counter_inhibited_behavior")
    t.describe(
        source=SRC,
        rule_text=rule("counter_inhibited_behavior"),
        context="Each xINH bit inhibits counting in its own mode. A block in mode x is run twice with mcyclecfg = "
        "minstretcfg: once with only x counting, once with every mode inhibited; the two settings differ only in "
        "xINH, so x's bit alone stops the counting. With every mode inhibited both counters must read exactly 0 "
        "(no mode counts, transitions included). Negative dependencies: with only a mode the block never enters "
        "counting, nothing counts. " + COUNT_NOTE,
        plan="Blocks of 40 instructions, for x = M, S, U, VS, VU (as implemented):\n"
        "1. Only x counting: cycle counts, instret in [40, 43].\n"
        "2. All xINH set: cycle and instret 0.\n"
        "3. x = S: only U counting (and with H, only VS/VU): both 0. x = U: only S counting, only VS and "
        "only VU counting: both 0. x = VS: only U and only VU: both 0. x = VU: only VS: 0.",
    )
    setup(t)
    n = 40

    def case(x: str) -> None:
        only = ALLINH & ~INH_HI[x]
        cfgs(t, only, only)
        block(t, x, nops(n), f"{x}-mode, only {x} counting")
        chk_moved(t, "cycle", f"{x}-mode block, only {x} counting")
        chk_range(t, "instret", n, n + 3, f"{x}-mode block of 40, only {x} counting")
        mut = MUT == "minh_ignored" and x == "M" or MUT == "inh_ignored_lower" and x != "M"
        cfgs(t, ALLINH, ALLINH)
        block(t, x, nops(n), f"{x}-mode, every mode inhibited")
        chk_zero(t, "cycle", f"{x}-mode block, every mode inhibited", flip=mut)
        chk_zero(t, "instret", f"{x}-mode block, every mode inhibited", flip=mut)
        negs = {"S": ("U", "VS", "VU"), "U": ("S", "VS", "VU"), "VS": ("U", "VU"), "VU": ("U", "VS"), "M": ()}[x]
        for y in negs:

            def neg(y: str = y) -> None:
                o = ALLINH & ~INH_HI[y]
                cfgs(t, o, o)
                block(t, x, nops(n), f"{x}-mode, only {y} counting")
                chk_zero(t, "cycle", f"{x}-mode block, only {y} counting")
                chk_zero(t, "instret", f"{x}-mode block, only {y} counting")

            guard(t, MODE_COND[y], neg)

    each_mode(t, case)
    teardown(t)
    return t


def t_cycle_counting() -> TestFile:
    t = new("cycle_counting")
    t.describe(
        source=SRC,
        rule_text=rule("cycle_counting"),
        context="cycle counts CPU cycles while the mode is not inhibited; the cycle in which a trap or trap return "
        "changes the mode is free (Smcntrpmf, Counter Behavior), and so is the number of cycles per instruction. "
        "So only nonzero versus zero is checked. minstretcfg does not filter cycle. " + COUNT_NOTE,
        plan="1. For x = M, S, U, VS, VU (as implemented), mcyclecfg = only x counting: a block of 50 in x makes "
        "cycle nonzero, whatever minstretcfg holds (all xINH set).\n"
        "2. mcyclecfg = only x counting, block in another mode never entering x (S for x = U, VS, VU; U for x = "
        "S): cycle 0.\n"
        "3. M-mode: two cycle reads 50 instructions apart with MINH clear increase; with MINH set, they are equal.",
    )
    setup(t)
    n = 50

    def case(x: str) -> None:
        only = ALLINH & ~INH_HI[x]
        cfgs(t, only, ALLINH)
        block(t, x, nops(n), f"{x}-mode, only {x} counting in mcyclecfg, minstretcfg inhibits all")
        chk_moved(t, "cycle", f"{x}-mode block, only {x} counting")
        y = {"M": None, "S": "U", "U": "S", "VS": "S", "VU": "S"}[x]
        if y:

            def neg(y: str = y) -> None:
                block(t, y, nops(n), f"{y}-mode, only {x} counting")
                chk_zero(t, "cycle", f"{y}-mode block, only {x} counting")

            guard(t, MODE_COND[y], neg)

    each_mode(t, case)
    for minh in (0, 1):
        cfgs(t, inh("M") if minh else 0, ALLINH)
        lab = t.label("mono")
        t.emit("csrr x7, mcycle")
        t.emit(f"{lab}:", 0)
        for ln in nops(n):
            t.emit(ln)
        t.emit("csrr x8, mcycle")
        t.emit("sub x7, x8, x7")
        t.emit("snez x7, x7")
        t.check("x7", 0 if minh else 1, lab, f"mcycle changed over 50 M-mode instructions with MINH={minh}")
    teardown(t)
    return t


def t_instret_non_inhibited() -> TestFile:
    t = new("instret_non_inhibited")
    t.describe(
        source=SRC,
        rule_text=rule("instret_non_inhibited"),
        context="Every retired instruction counts once in a non-inhibited mode. Blocks of n mixed instructions (ALU, "
        "load, store, taken and not-taken branches, jumps) run in mode x with only x counting; the difference "
        "between two block lengths is exact. With x inhibited and another mode counting (one the block does not "
        "enter), the block retires nothing that counts. mcyclecfg does not filter instret. " + COUNT_NOTE,
        plan="For x = M, S, U, VS, VU (as implemented), minstretcfg = only x counting, mcyclecfg = all inhibited:\n"
        "1. Blocks of 16 and 57 mixed instructions: instret(16) in [16, 19], and instret(57) - instret(16) = 41.\n"
        "2. A block of 57 in x with minstretcfg = only another mode counting (U for x = S/M; S for the others): 0.",
    )
    setup(t)

    def case(x: str) -> None:
        only = ALLINH & ~INH_HI[x]
        cfgs(t, ALLINH, only)
        block(t, x, mixed(16), f"{x}-mode, 16 mixed, only {x} counting")
        chk_range(t, "instret", 16, 19, f"{x}-mode block of 16 mixed instructions")
        keep(t, "instret", 8)
        block(t, x, mixed(57), f"{x}-mode, 57 mixed, only {x} counting")
        chk_diff(t, "instret", 8, 42 if MUT == "count_off_by_one" else 41, f"{x}-mode blocks of 57 and 16")
        y = "U" if x in ("M", "S") else "S"

        def neg() -> None:
            o = ALLINH & ~INH_HI[y]
            cfgs(t, ALLINH, o)
            block(t, x, mixed(57), f"{x}-mode, 57 mixed, only {y} counting")
            chk_zero(t, "instret", f"{x}-mode block, only {y} counting")

        guard(t, MODE_COND[y], neg)

    each_mode(t, case)
    teardown(t)
    return t


ILLEGAL = "csrr x7, mhartid  // illegal instruction below M-mode"
EBREAK = ".word 0x00100073  // ebreak"


def t_instret_exception() -> TestFile:
    t = new("instret_exception")
    t.describe(
        source=SRC,
        rule_text=rule("instret_exception"),
        context="An instruction that raises a synchronous exception into a more privileged mode does not retire, "
        "so it does not count even in a counting mode. In an M-boot test nothing is delegated, so exceptions from "
        "S, U, VS and VU go to M-mode (inhibited), and its MRET back originates in M (inhibited). A block with a "
        "trapping instruction therefore counts exactly as many as the same block without it. " + COUNT_NOTE,
        issues=f'{ISSUE}1730: gfavor: "if an instruction (including ECALL and EBREAK) is faulted such that it is '
        "architecturally considered to have not fully completed execution architecturally (aka retired), then it "
        'must not be counted by minstret."',
        plan="For x = S, U, VS, VU (as implemented), minstretcfg = only x counting:\n"
        "1. Reference: 10 + 10 nops: instret R.\n"
        "2. 10 nops, an illegal instruction (csrr of mhartid; cause 2, to M), 10 nops: instret = R exactly.\n"
        "3. 10 nops, ebreak (cause 3, to M), 10 nops: instret = R exactly.\n"
        "Each trap is checked in the trap log (cause, epc).",
    )
    setup(t)

    def case(x: str) -> None:
        only = ALLINH & ~INH_HI[x]
        cfgs(t, ALLINH, only)
        block(t, x, nops(20), f"{x}-mode reference, 20 nops")
        keep(t, "instret", 8)
        for insn, cause, name in ((ILLEGAL, 2, "illegal instruction"), (EBREAK, 3, "ebreak")):
            lab = t.label(f"exc{x}")
            t.allow(1)
            t.comment(f"block: {x}-mode, 10 nops, {name}, 10 nops")
            t.la("x9", "pmf_data")
            zero(t)
            enter(t, x)
            for ln in nops(10):
                t.emit(ln)
            t.emit(f"{lab}:", 0)
            t.emit(insn)
            for ln in nops(10):
                t.emit(ln)
            t.leave()
            read_store(t)
            t.outcome(cause, lab, f"{name} in {x}-mode", origin=x)
            chk_diff(
                t, "instret", 8, 1 if MUT == "exception_retires" else 0, f"{x}-mode block with a {name} vs without"
            )

    each_mode(t, case, ("S", "U", "VS", "VU"))
    teardown(t)
    return t


def t_instret_xret() -> TestFile:
    t = new("instret_xret")
    t.describe(
        source=SRC,
        rule_text=rule("instret_xret"),
        context="An xRET that returns to a less privileged mode retires and counts only if the mode it executes in "
        "(the originating mode) is not inhibited. The test writes minstret = 0 in M-mode, executes the xRET with "
        "nothing else between the write and it in a counting mode, and reads instret as the first instruction in "
        "the target mode (a CSR read returns the value before its own retirement; Zicsr), so the value read is "
        'exactly the count of the xRET. The xRET retires ("The latter do retire"), so with its originating mode '
        "counting it reads 1. With only the target mode counting the spec says it 'should' not count (the NOTE's "
        "example), which is a recommendation, so 0 and 1 are both accepted there. mcounteren/scounteren/"
        "hcounteren.IR are set so the read is legal.",
        plan="minstretcfg = only the originating mode counting (expect 1), then only the target mode counting "
        "(expect 0, recommended, or 1):\n"
        "1. MRET M -> S and M -> U.\n"
        "2. SRET S -> U (entered with MRET from inhibited M; sepc/SPP preset in M).\n"
        "3. With H: MRET M -> VS and M -> VU (MPV=1); SRET HS -> VS and HS -> VU (hstatus.SPV=1); SRET VS -> VU "
        "(vsepc/vsstatus.SPP preset in M).\n"
        "Each target leaves through T-SBI; the value read is checked in M-mode.",
    )
    setup(t)
    with t.only_if("defined(U_SUPPORTED)"):
        t.li("x6", 7)
        t.emit("csrs mcounteren, x6")
    with t.only_if("defined(S_SUPPORTED)"):
        t.emit("csrs scounteren, x6")
    with t.only_if(H):
        t.emit("csrs CSR_HCOUNTEREN, x6")

    def mret_case(tgt: str, orig_counts: bool) -> None:
        """MRET from M into tgt."""
        o = "M" if orig_counts else tgt
        cfgs(t, ALLINH, ALLINH & ~INH_HI[o])
        after = t.label(f"to{tgt}")
        t.la("x14", after)
        t.emit("csrw mepc, x14")
        t.emit("LI(x14, MSTATUS_MPP)", 2)
        t.emit("csrc mstatus, x14")
        if tgt in ("S", "VS"):
            t.emit("LI(x14, MPP_SMODE)", 2)
            t.emit("csrs mstatus, x14")
        if tgt in ("VS", "VU"):
            mpv(t, True)
        t.emit("csrw minstret, x0")
        with t.rv32_only():
            t.emit("csrw minstreth, x0")
            t.emit("csrw minstret, x0")
        t.emit("mret")
        t.emit(f"{after}:", 0)
        t.emit("csrr x7, instret")
        t.leave()
        exp: list[int] = [1] if orig_counts else [0, 1]
        if MUT == "xret_not_counted" and orig_counts:
            exp = [0]
        t.check("x7", exp, after, f"instret read first in {tgt}-mode after MRET from M, only {o} counting")

    def sret_case(frm: str, tgt: str, orig_counts: bool) -> None:
        """Enter frm (S or VS) from M with MRET (M inhibited), then SRET into tgt."""
        o = frm if orig_counts else tgt
        cfgs(t, ALLINH, ALLINH & ~INH_HI[o])
        after, mid = t.label(f"to{tgt}"), t.label(f"in{frm}")
        t.la("x14", after)
        if frm == "S":
            t.emit("csrw sepc, x14")
            t.li("x14", 0x100)
            t.emit(f"{'csrs' if tgt == 'VS' else 'csrc'} sstatus, x14  // SPP")
            with t.only_if(H):
                t.li("x14", 0x80)
                t.emit(f"{'csrs' if tgt in ('VS', 'VU') else 'csrc'} CSR_HSTATUS, x14  // SPV")
        else:
            t.emit("csrw CSR_VSEPC, x14")
            t.li("x14", 0x100)
            t.emit("csrc CSR_VSSTATUS, x14  // vsstatus.SPP = 0 (VU)")
        t.la("x14", mid)
        t.emit("csrw mepc, x14")
        t.emit("LI(x14, MSTATUS_MPP)", 2)
        t.emit("csrc mstatus, x14")
        t.emit("LI(x14, MPP_SMODE)", 2)
        t.emit("csrs mstatus, x14")
        with t.only_if(H):
            mpv(t, frm == "VS")
        t.emit("csrw minstret, x0")
        with t.rv32_only():
            t.emit("csrw minstreth, x0")
            t.emit("csrw minstret, x0")
        t.emit("mret")
        t.emit(f"{mid}:", 0)
        t.emit("sret")
        t.emit(f"{after}:", 0)
        t.emit("csrr x7, instret")
        t.leave()
        exp: list[int] = [1] if orig_counts else [0, 1]
        if MUT == "xret_not_counted" and orig_counts:
            exp = [0]
        t.check("x7", exp, after, f"instret read first in {tgt}-mode after SRET from {frm}, only {o} counting")

    for tgt in ("S", "U"):
        guard(t, MODE_COND[tgt], lambda tgt=tgt: (mret_case(tgt, True), mret_case(tgt, False)))
    with t.only_if("defined(S_SUPPORTED)"):
        sret_case("S", "U", True)
        sret_case("S", "U", False)
    with t.only_if(H):
        for tgt in ("VS", "VU"):
            mret_case(tgt, True)
            mret_case(tgt, False)
            sret_case("S", tgt, True)
            sret_case("S", tgt, False)
        sret_case("VS", "VU", True)
        sret_case("VS", "VU", False)
    teardown(t)
    return t


if __name__ == "__main__":
    for t in gen():
        print(t.write())
