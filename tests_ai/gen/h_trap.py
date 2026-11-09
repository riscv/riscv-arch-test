# SPDX-License-Identifier: Apache-2.0
"""H suite: trap delegation (hedeleg), CSR writes on traps into M, HS and VS, SRET/MRET with V, the second trap
value (htval/mtval2) and the trap instruction (htinst/mtinst) for traps that are not guest-page faults.

Deterministic exceptions used, all with vsatp and hgatp Bare:
  ebreak (3); MRET below M-mode (illegal, 2); hstatus read from VS/VU (virtual, 22); ECALL_TEST (T-SBI ecall
  that the framework logs: 8, 9, 10, 11); load/store/fetch access faults (5, 7, 1) at the DUT's
  RVMODEL_ACCESS_FAULT_ADDRESS; HLV/HSV access faults; misaligned LR/SC (4/5, 6/7, with A).
"""

from __future__ import annotations

from contextlib import nullcontext
from typing import TYPE_CHECKING

from aigen import X
from hlib import (
    HYP,
    ISSUE,
    MRET,
    MUT,
    hlsv,
    hs_bits,
    new,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from aigen import Expect, TestFile, Value

MUTANTS = {
    "hedeleg_ignored": "a VS/VU exception with its hedeleg bit set is taken in HS-mode",
    "hedeleg_applies_v0": "hedeleg also delegates U-mode (V=0) exceptions to VS-mode",
    "medeleg_bypass": "hedeleg delegates to VS-mode even when medeleg does not delegate to HS-mode",
    "spv_not_written_v0": "a trap from V=0 into HS-mode leaves hstatus.SPV unchanged",
    "spvp_written_v0": "a trap from V=0 into HS-mode writes hstatus.SPVP = sstatus.SPP",
    "gva_zero": "hstatus.GVA/mstatus.GVA are always written 0",
    "gva_stale": "GVA is not written on traps that do not carry a guest virtual address",
    "spie_from_vsstatus": "a trap from V=1 into HS-mode copies vsstatus.SIE into sstatus.SPIE",
    "vsstatus_written_on_hs_trap": "a trap into HS-mode also writes vsstatus.SPP",
    "htval_eq_tval": "htval/mtval2 receive stval>>2 on access faults",
    "tinst_imm_kept": "a transformed load/store in htinst keeps the immediate offset",
    "tinst_ebreak_insn": "htinst receives the ebreak encoding on a breakpoint",
    "ecall_vs_cause9": "ecall from VS-mode reports cause 9",
    "ecall_vu_cause10": "ecall from VU-mode reports cause 10",
    "sret_v1_uses_hs_spp": "SRET in VS-mode returns to the mode given by the HS-level sstatus.SPP",
    "sret_keeps_spv": "SRET in HS-mode leaves hstatus.SPV set",
    "mret_mpp3_honors_mpv": "MRET with MPP=3 and MPV=1 enters VS-mode",
    "mpv_not_written": "a trap into M-mode from V=0 leaves mstatus.MPV unchanged",
    "hedeleg_required_ro0": "hedeleg bit 3 (breakpoint) is read-only zero",
    "hedeleg_ro_writable": "hedeleg bit 10 (ecall from VS) is writable",
    "tinst_interrupt_kept": "htinst/mtinst keep their previous value on an interrupt",
    "access_over_virtual": "HLV at a faulting address in VU-mode raises the access fault instead of virtual-instruction",
    "sret_dt_not_cleared": "SRET into VU-mode leaves vsstatus.SDT set",
    "lr_offset_nonzero": "the transformed LR carries the low address bits as its offset",
    "vs_trap_writes_sepc": "a trap into VS-mode also writes the HS-level sepc",
}

# Per-kind access-fault addresses (check_defines.h derives each from RVMODEL_ACCESS_FAULT_ADDRESS when only that
# one is defined; some configurations define only these).
FA_LD, FA_ST, FA_IF = (f"RVMODEL_ACCESS_FAULT_ADDRESS_{k}" for k in ("LOAD", "STORE", "FETCH"))
HAS_LD, HAS_ST, HAS_IF = (f"defined({a})" for a in (FA_LD, FA_ST, FA_IF))
HAS_A = "defined(ZALRSC_SUPPORTED) || defined(A_SUPPORTED)"
EBREAK = 0x00100073
SIE, SPIE, SPP, SDT = 0x2, 0x20, 0x100, 1 << 24
GVA, SPV, SPVP = 0x40, 0x80, 0x100
MIE, MPIE, MPP = 0x8, 0x80, 0x1800
HANDLER = {"M": 3, "S": 1, "VS": 2}
T_LW, T_SW = 0x2383, 0x702023  # lw x7, 8(x6) / sw x7, 8(x6) transformed: imm and rs1 (offset 0) zeroed
HLVW, _ = hlsv("hlv.w", "x7", "x6")
HSVW, _ = hlsv("hsv.w", "x0", "x6", "x7")
T_HLVW = hlsv("hlv.w", "x7", "x0")[1]  # rs1 field replaced by the offset (0)
T_HSVW = hlsv("hsv.w", "x0", "x0", "x7")[1]
LRW = (0x2 << 27) | (6 << 15) | (2 << 12) | (7 << 7) | 0x2F  # lr.w x7, (x6)
SCW = (0x3 << 27) | (7 << 20) | (6 << 15) | (2 << 12) | (8 << 7) | 0x2F  # sc.w x8, x7, (x6)
CBO_ZERO = (4 << 20) | (6 << 15) | (2 << 12) | 0x0F  # cbo.zero (x6)
T_CBO_ZERO = (4 << 20) | (2 << 12) | 0x0F
ISSUE_GVA = (
    f"{ISSUE}672 and {ISSUE}673: breakpoint and address-misaligned traps that write a guest virtual address also "
    f'set GVA. {ISSUE}2695 (aswaterman): "Since HLV etc. always have effective privilege VU or VS, their virtual '
    'addresses are always guest virtual addresses, and so GVA is set to 1." Whether writing stval=0 sets GVA is '
    "not settled, so GVA is checked only when xtval is nonzero."
)
ISSUE_3347 = (
    f"{ISSUE}3347 (aswaterman): the hedeleg bits listed as writable, including 18 and 19, are intentionally "
    f"required to be writable. {ISSUE}2191: the reserved high bits should be read-only zero."
)


# ---------------------------------------------------------------- kinds of trap
class Kind:
    """One deterministic trapping instruction. pre: setup lines before the window; lines: the instruction
    (first line) and anything after it; cause(mode); tval: legal xtval values; tinst: legal values (None: a
    runtime predicate); va: xtval may hold a (guest) virtual address; cond: preprocessor guard."""

    def __init__(
        self,
        name: str,
        pre: list[str],
        lines: list[str],
        cause: Callable[[str], int],
        tval: Expect | None,
        tinst: list[int],
        va: bool,
        cond: str | None = None,
        modes: tuple[str, ...] = ("S", "U", "VS", "VU"),
        epc: bool = True,
        lead: Sequence[str] = (),
    ) -> None:
        self.name, self.pre, self.lines, self.cause, self.tval = name, pre, lines, cause, tval
        self.lead = list(lead)  # emitted in the target mode, just before the labeled instruction
        self.tinst, self.va, self.cond, self.modes, self.epc = tinst, va, cond, modes, epc


def ecall_cause(mode: str) -> int:
    if mode == "VS":
        return 9 if MUT == "ecall_vs_cause9" else 10
    if mode == "VU":
        return 10 if MUT == "ecall_vu_cause10" else 8
    return {"U": 8, "S": 9, "M": 11}[mode]


def kinds() -> dict[str, Kind]:
    k = {}
    k["ebreak"] = Kind(
        "ebreak",
        [],
        [f".word {hex(EBREAK)}  // ebreak"],
        lambda m: 3,
        "LAB",
        [EBREAK] if MUT == "tinst_ebreak_insn" else [0],
        True,
        modes=("S", "U", "VS", "VU", "M"),
    )
    k["illegal"] = Kind(
        "illegal (mret)",
        [],
        [f".word {hex(MRET)}  // mret"],
        lambda m: 2,
        [0, MRET],
        [0],
        False,
        modes=("S", "U", "VS", "VU"),
    )
    k["virtual"] = Kind(
        "virtual (hstatus read)",
        [],
        ["csrr x7, 0x600  // hstatus"],
        lambda m: 22,
        [0, (0x600 << 20) | (2 << 12) | (7 << 7) | 0x73],
        [0],
        False,
        modes=("VS", "VU"),
    )
    k["ecall"] = Kind(
        "ecall (T-SBI ECALL_TEST)",
        [],
        ["ecall"],
        ecall_cause,
        [0],
        [0],
        False,
        modes=("S", "U", "VS", "VU", "M"),
        lead=["li a0, 0x73  // TSBI_ECALL_TEST"],
    )
    imm = [T_LW | (8 << 20)] if MUT == "tinst_imm_kept" else [0, T_LW]
    k["load"] = Kind(
        "load access fault (lw)",
        [f"LI(x6, {FA_LD}-8)"],
        ["lw x7, 8(x6)"],
        lambda m: 5,
        [0, FA_LD],
        imm,
        True,
        HAS_LD,
        modes=("S", "U", "VS", "VU", "M"),
    )
    simm = [T_SW | (8 << 7)] if MUT == "tinst_imm_kept" else [0, T_SW]
    k["store"] = Kind(
        "store access fault (sw)",
        [f"LI(x6, {FA_ST}-8)", "li x7, 0"],
        ["sw x7, 8(x6)"],
        lambda m: 7,
        [0, FA_ST],
        simm,
        True,
        HAS_ST,
        modes=("S", "U", "VS", "VU", "M"),
    )
    k["fetch"] = Kind(
        "fetch access fault (jalr)",
        [f"LI(x6, {FA_IF})"],
        ["jalr ra, 0(x6)"],
        lambda m: 1,
        [0, FA_IF],
        [0],
        True,
        HAS_IF,
        modes=("S", "U", "VS", "VU", "M"),
        epc=False,
    )
    k["hlv"] = Kind(
        "HLV.W access fault",
        [f"LI(x6, {FA_LD})"],
        [HLVW],
        lambda m: 5,
        [0, FA_LD],
        [0, T_HLVW],
        True,
        HAS_LD,
        modes=("S", "M"),
    )
    k["hsv"] = Kind(
        "HSV.W access fault",
        [f"LI(x6, {FA_ST})", "li x7, 0"],
        [HSVW],
        lambda m: 7,
        [0, FA_ST],
        [0, T_HSVW],
        True,
        HAS_ST,
        modes=("S", "M"),
    )
    return k


# ---------------------------------------------------------------- emission helpers
def logw(t: TestFile, reg: str, word: str, back: int = 0) -> None:
    """reg = word `word` of the log entry `back` entries before the last one (x4, x5 clobbered)."""
    if back == 0:
        t.emit(f"AI_LOG({reg}, {word})", 10)
        return
    t.emit("LA(x4, rvtest_trap_count)", 2)
    t.emit("LREG x5, 0(x4)")
    t.emit(f"addi x5, x5, -{1 + back}")
    t.emit("andi x5, x5, RVTEST_TRAP_LOG_N-1")
    t.emit("slli x5, x5, TRAPLOG_ENTRY_SHIFT")
    t.emit("LA(x4, rvtest_trap_log)", 2)
    t.emit("add x4, x4, x5")
    t.emit(f"LREG {reg}, ({word})*REGWIDTH(x4)")


def logchk(t: TestFile, word: str, mask: Value, exp: Expect, lab: str, desc: str, back: int = 0) -> None:
    """Check (log word & mask) against exp (one value or a list of alternatives)."""
    logw(t, "x15", word, back)
    t.check_masked("x15", mask, exp, lab, desc, tmp="x5")


def handler_is(t: TestFile, where: str, lab: str, desc: str, back: int = 0) -> None:
    logchk(t, "TRAPLOG_VECT", 3, HANDLER[where], lab, f"{desc}: taken in {where}-mode (handler 3 M, 1 HS, 2 VS)", back)


def mpv_gva(t: TestFile, which: str, value: int, lab: str, desc: str) -> None:
    """Check mstatus.MPV or GVA (which) of the last M-mode log entry."""
    bit64, bit32 = {"MPV": (39, 7), "GVA": (38, 6)}[which]
    with t.rv64_only():
        logchk(t, "TRAPLOG_STATUS", 1 << bit64, (1 << bit64) if value else 0, lab, f"{desc}: mstatus.{which}={value}")
    with t.rv32_only():
        logchk(t, "TRAPLOG_STATUS2", 1 << bit32, (1 << bit32) if value else 0, lab, f"{desc}: mstatush.{which}={value}")


def gva_ok(t: TestFile, handler: str, lab: str, desc: str) -> None:
    """GVA must be 1 when the logged xtval is nonzero (a guest virtual address was written)."""
    t.comment("GVA = 1 when xtval holds a (nonzero) guest virtual address")
    logw(t, "x14", "TRAPLOG_TVAL")
    t.emit("seqz x14, x14")
    if handler == "S":
        logw(t, "x15", "TRAPLOG_STATUS2")
        t.emit("srli x15, x15, 6")
    else:
        with t.rv64_only():
            logw(t, "x15", "TRAPLOG_STATUS")
            t.emit("srli x15, x15, 38")
        with t.rv32_only():
            logw(t, "x15", "TRAPLOG_STATUS2")
            t.emit("srli x15, x15, 6")
    t.emit("andi x15, x15, 1")
    if MUT == "gva_zero":
        t.emit("xori x15, x15, 1")  # mutant: GVA=0 is expected for a guest virtual address
    t.emit("or x15, x15, x14")
    t.check_bool("x15", lab, f"{desc}: GVA=1 because xtval holds a guest virtual address (or xtval=0)")


def gva_zero(t: TestFile, handler: str, lab: str, desc: str) -> None:
    if handler == "S":
        logchk(t, "TRAPLOG_STATUS2", GVA, GVA if MUT == "gva_stale" else 0, lab, f"{desc}: hstatus.GVA=0")
    else:
        mpv_gva(t, "GVA", 1 if MUT == "gva_stale" else 0, lab, desc)


def enter(t: TestFile, mode: str) -> None:
    if mode == t.cur:
        return
    if t.cur == "S":
        t.enter(mode)
    else:
        t.emit(f"RVTEST_TSBI_GOTO_{mode}MODE", 120)


def leave(t: TestFile, mode: str) -> None:
    if mode != t.cur:
        t.leave()


def twin(t: TestFile, mode: str, kind: Kind, desc: str, cause: Expect | None = None, n: int = 1) -> str:
    """Run `kind` in `mode` in a trap window and check cause, xepc, xtval and origin. Returns the label."""
    lab = t.label(f"{kind.name.split()[0]}_{mode}")
    for p in kind.pre:
        t.emit(p, 2)
    t.allow(n)
    enter(t, mode)
    for ln in kind.lead:
        t.emit(ln)
    t.emit(f"{lab}:", 0)
    for ln in kind.lines:
        t.emit(ln)
    leave(t, mode)
    tval = [0, lab] if kind.tval == "LAB" else kind.tval
    c = kind.cause(mode) if cause is None else cause
    t.outcome(c, lab, f"{desc}: {kind.name} in {mode}-mode", tval, epc=kind.epc, origin=mode)
    if not kind.epc:
        logchk(t, "TRAPLOG_EPC", X((1 << 32) - 1, (1 << 64) - 1), FA_IF, lab, f"{desc}: xepc is the faulting address")
    return lab


def guard(t: TestFile, cond: str | None, body: Callable[[], object]) -> None:
    if cond:
        with t.only_if(cond):
            body()
    else:
        body()


def bare(t: TestFile) -> None:
    """vsatp and hgatp Bare, hstatus.SPVP/HU as the boot leaves them (0)."""
    t.comment("vsatp = hgatp = 0 (Bare): guest virtual = guest physical = supervisor physical addresses")
    t.emit("csrw 0x280, x0  // vsatp")
    t.emit("csrw 0x680, x0  // hgatp")
    t.emit(".word 0x62000073  // hfence.gvma")


def where(mode: str, cause: int, hedeleg: int) -> str:
    """Handler mode for an exception from `mode` in an S-boot test (framework medeleg delegates every cause
    the tests use except 9, ecall from HS)."""
    if cause in (9, 11):
        return "M"
    if mode in ("VS", "VU") and (hedeleg >> cause) & 1 and cause not in (9, 10, 11, 16, 20, 21, 22, 23):
        return "S" if MUT == "hedeleg_ignored" else "VS"
    if MUT == "hedeleg_applies_v0" and mode == "U" and (hedeleg >> cause) & 1:
        return "VS"
    return "S"


# ---------------------------------------------------------------- tests
def gen() -> list[TestFile]:
    tests: list[TestFile] = []
    tests += gen_hedeleg_csr()
    tests += gen_deleg()
    tests += gen_hs_writes()
    tests += gen_vs_writes()
    tests += gen_m_writes()
    tests += gen_xret()
    tests += gen_tval2_tinst()
    tests += gen_misc()
    return tests


# ---------------------------------------------------------------- hedeleg as a CSR
REQUIRED_W = [1, 2, 3, 4, 5, 6, 7, 8, 12, 13, 15, 18, 19]
NEW_1P13 = [18, 19]  # software-check and hardware-error exceptions are defined from Sm 1.13
SM1P13 = "defined(SM1P13P0_OR_LATER_SUPPORTED)"
REQUIRED_0 = [9, 10, 11, 16, 20, 21, 22, 23]


def hedeleg_probe(t: TestFile) -> None:
    """x8 = hedeleg (low XLEN bits) after writing all ones; x9 (RV32) = hedelegh after writing all ones."""
    t.emit("li x7, -1")
    t.emit("csrw 0x602, x7  // hedeleg = all ones")
    t.emit("csrr x8, 0x602")
    with t.rv32_only():
        t.emit("csrw 0x612, x7  // hedelegh = all ones")
        t.emit("csrr x9, 0x612")


def gen_hedeleg_csr() -> list[TestFile]:
    tests = []
    req_mask = sum(1 << b for b in REQUIRED_W if b not in NEW_1P13)
    new_mask = sum(1 << b for b in NEW_1P13)
    ro_mask = sum(1 << b for b in REQUIRED_0)
    if MUT == "hedeleg_required_ro0":
        req_mask &= ~(1 << 3)

    # ---- hedeleg_bits_required ----
    t = new("hedeleg_bits_required")
    t.describe(
        source=HYP,
        rule_text="Many bits of hedeleg are required specifically to be writable or zero, as enumerated in "
        "<<hedeleg-bits>>.",
        context="Table hedeleg-bits: bits 1-8, 12, 13, 15, 18 and 19 are writable; bits 9, 10, 11, 16 and 20-23 are "
        "read-only 0 (bit 0 is hedeleg_bit0_ialign32). The test writes hedeleg in HS-mode and restores 0; no "
        "trap is taken while it is nonzero. Causes 18 (software check) and 19 (hardware error) are defined from "
        "Sm 1.13, so bits 18 and 19 are required only with SM1P13P0_OR_LATER_SUPPORTED.",
        issues=ISSUE_3347,
        plan="1. Write all ones: every required-writable bit reads 1 and every required read-only-0 bit reads 0.\n"
        "2. Write zero: every bit reads 0.\n"
        "3. Each required-writable bit alone: writing just that bit reads back just that bit (no coupling).",
    )
    lab = t.label("ones")
    t.emit(f"{lab}:", 0)
    hedeleg_probe(t)
    t.check_masked("x8", req_mask, req_mask, lab, "hedeleg: required-writable bits read 1 after writing ones", tmp="x5")
    with t.only_if(SM1P13):
        t.check_masked("x8", new_mask, new_mask, lab, "hedeleg: bits 18 and 19 read 1 after writing ones", tmp="x5")
    t.check_masked(
        "x8",
        ro_mask,
        (1 << 10) if MUT == "hedeleg_ro_writable" else 0,
        lab,
        "hedeleg: required read-only-0 bits read 0 after writing ones",
        tmp="x5",
    )
    t.emit("csrw 0x602, x0")
    t.emit("csrr x8, 0x602")
    t.check("x8", 0, lab, "hedeleg reads 0 after writing 0")
    for b in REQUIRED_W:
        with t.only_if(SM1P13) if b in NEW_1P13 else nullcontext():
            t.li("x7", 1 << b)
            t.emit("csrw 0x602, x7")
            t.emit("csrr x8, 0x602")
            exp = 0 if (MUT == "hedeleg_required_ro0" and b == 3) else 1 << b
            t.check_masked("x8", 0xFFFFFFFF, exp, lab, f"hedeleg = 1<<{b} reads back 1<<{b}", tmp="x5")
    t.emit("csrw 0x602, x0")
    tests.append(t)

    # ---- hedeleg_acc ----
    t = new("hedeleg_acc")
    t.describe(
        source=HYP,
        rule_text="Each bit of hedeleg shall be either writable or read-only zero.",
        context="So no bit is read-only one, and bits are independent: after learning the writable set W by writing "
        "all ones, any value P reads back P & W. On RV32 the same holds for hedelegh (bits 63:32).",
        issues=ISSUE_3347,
        plan="1. Write 0: hedeleg (and hedelegh) read 0, so no bit is read-only one.\n"
        "2. W = value read after writing all ones (per half on RV32).\n"
        "3. Six random patterns P (and their complements) read back P & W.",
    )
    lab = t.label("acc")
    t.emit(f"{lab}:", 0)
    t.emit("csrw 0x602, x0")
    t.emit("csrr x8, 0x602")
    t.check("x8", 0, lab, "hedeleg reads 0 after writing 0 (no read-only-one bit)")
    with t.rv32_only():
        t.emit("csrw 0x612, x0")
        t.emit("csrr x8, 0x612")
        t.check("x8", 0, lab, "hedelegh reads 0 after writing 0")
    hedeleg_probe(t)  # x8 = W (low), x9 = W (high, RV32)
    for i in range(6):
        p = t.rand(64)
        for v in (p, ~p & ((1 << 64) - 1)):
            t.load("x7", X(v & 0xFFFFFFFF, v), "pattern P")
            t.emit("csrw 0x602, x7")
            t.emit("csrr x6, 0x602")
            t.emit("and x7, x7, x8")
            t.emit("xor x6, x6, x7")
            t.check("x6", 0, lab, "hedeleg reads back P & W")
            with t.rv32_only():
                t.load("x7", X(v >> 32, 0), "pattern P (high half)")
                t.emit("csrw 0x612, x7")
                t.emit("csrr x6, 0x612")
                t.emit("and x7, x7, x9")
                t.emit("xor x6, x6, x7")
                t.check("x6", 0, lab, "hedelegh reads back P & W")
    t.emit("csrw 0x602, x0")
    with t.rv32_only():
        t.emit("csrw 0x612, x0")
    tests.append(t)

    # ---- hedeleg_sz_acc ----
    t = new("hedeleg_sz_acc")
    t.describe(
        source=HYP,
        rule_text="Register hedeleg is a 64-bit read/write register, formatted as shown in <<norm:hedeleg_img>>.",
        context="On RV64 hedeleg holds all 64 bits; on RV32 bits 63:32 are hedelegh (hedelegh_sz_acc_op). The "
        "standard exception codes are below 32, so bits 63:32 are reserved; each may be writable or read-only "
        "zero.",
        issues=ISSUE_3347,
        plan="1. HS-mode reads and writes hedeleg without a trap (all ones, then zero).\n"
        "2. Writing a value with only bits 63:32 set (hedelegh on RV32) leaves bits 31:0 zero, and writing only "
        "bits 31:0 leaves the high half zero: the halves are independent.\n"
        "3. A required-writable bit (3) round-trips through every CSR instruction form that writes "
        "(csrrw, csrrs, csrrc, csrrwi, csrrsi, csrrci with uimm=8).",
    )
    lab = t.label("sz")
    t.emit(f"{lab}:", 0)
    t.emit("li x7, -1")
    with t.rv64_only():
        t.emit("slli x7, x7, 32")
        t.emit("csrw 0x602, x7  // hedeleg = bits 63:32")
        t.emit("csrr x8, 0x602")
        t.check_masked("x8", 0xFFFFFFFF, 0, lab, "writing only bits 63:32 leaves hedeleg[31:0] = 0", tmp="x5")
        t.emit("li x7, -1")
        t.emit("srli x7, x7, 32")
        t.emit("csrw 0x602, x7  // hedeleg = bits 31:0")
        t.emit("csrr x8, 0x602")
        t.emit("srli x8, x8, 32")
        t.check("x8", 0, lab, "writing only bits 31:0 leaves hedeleg[63:32] = 0")
    with t.rv32_only():
        t.emit("csrw 0x602, x0")
        t.emit("csrw 0x612, x7  // hedelegh = all ones")
        t.emit("csrr x8, 0x602")
        t.check("x8", 0, lab, "writing hedelegh leaves hedeleg = 0")
        t.emit("csrw 0x612, x0")
        t.emit("csrw 0x602, x7")
        t.emit("csrr x8, 0x612")
        t.check("x8", 0, lab, "writing hedeleg leaves hedelegh = 0")
    t.emit("csrw 0x602, x0")
    forms = [
        ("csrrw x0, 0x602, x7", 8, 8),
        ("csrrc x0, 0x602, x7", 8, 0),
        ("csrrs x0, 0x602, x7", 8, 8),
        ("csrrci x0, 0x602, 8", None, 0),
        ("csrrsi x0, 0x602, 8", None, 8),
        ("csrrwi x0, 0x602, 0", None, 0),
    ]
    for asm, src, exp in forms:
        if src is not None:
            t.li("x7", src)
        t.emit(asm)
        t.emit("csrr x8, 0x602")
        t.check_masked("x8", 8, exp, lab, f"{asm.split()[0]} on hedeleg bit 3 gives bit 3 = {exp >> 3}", tmp="x5")
    tests.append(t)

    # ---- hedelegh_sz_acc_op ----
    t = new("hedelegh_sz_acc_op")
    t.describe(
        source=HYP,
        rule_text="When XLEN=32, hedelegh is a 32-bit read/write register that aliases bits 63:32 of hedeleg. "
        "Register hedelegh does not exist when XLEN=64.",
        context="hedelegh (0x612) is an HS-level CSR. Its bits are reserved exception codes 32-63, each writable or "
        "read-only zero. On RV64 the address is not a CSR, so access raises illegal-instruction.",
        issues=ISSUE_3347,
        plan="1. RV32: HS-mode writes 0 and reads 0; writes all ones, reads W; random P reads P & W; writing "
        "hedelegh does not change hedeleg.\n"
        "2. RV64: HS-mode reads and writes of 0x612 raise illegal-instruction.",
    )
    with t.rv32_only():
        lab = t.label("h")
        t.emit(f"{lab}:", 0)
        t.emit("csrw 0x602, x0")
        t.emit("csrw 0x612, x0")
        t.emit("csrr x8, 0x612")
        t.check("x8", 0, lab, "hedelegh reads 0 after writing 0")
        t.emit("li x7, -1")
        t.emit("csrw 0x612, x7")
        t.emit("csrr x9, 0x612")
        for _ in range(4):
            p = t.rand(32)
            t.load("x7", p, "pattern P")
            t.emit("csrw 0x612, x7")
            t.emit("csrr x6, 0x612")
            t.emit("and x7, x7, x9")
            t.emit("xor x6, x6, x7")
            t.check("x6", 0, lab, "hedelegh reads back P & W")
        t.emit("csrr x8, 0x602")
        t.check("x8", 0, lab, "hedelegh writes leave hedeleg = 0")
        t.emit("csrw 0x612, x0")
    with t.rv64_only():
        for ln in ("csrr x7, 0x612", "csrw 0x612, x0"):
            lab = t.label("h64")
            t.allow(1)
            t.emit(f"{lab}:", 0)
            t.emit(ln)
            enc = (0x612 << 20) | ((2 << 12) | (7 << 7) if ln.startswith("csrr") else (1 << 12)) | 0x73
            t.outcome(2, lab, f"RV64: {ln} (hedelegh does not exist)", [0, enc], origin="S")
    tests.append(t)

    # ---- hedeleg_bit0_ialign32 ----
    t = new("hedeleg_bit0_ialign32")
    t.describe(
        source=HYP,
        rule_text="Bit 0, corresponding to instruction address-misaligned exceptions, must be writable if IALIGN=32.",
        context="IALIGN=32 when no compressed instructions are supported (no C or Zca). With them, bit 0 may be "
        "writable or read-only zero (hedeleg_acc), so the check applies only without C and Zca. With IALIGN=32 the "
        "test also takes a delegated instruction-address-misaligned exception (cause 0) in VS-mode.",
        plan="1. Without C/Zca: hedeleg = 1 reads 1, and = 0 reads 0.\n"
        "2. Without C/Zca: with hedeleg[0]=1, a VS-mode jalr to a target 2 bytes past an instruction raises cause 0 "
        "in VS-mode (vstval = 0 or the target); with hedeleg[0]=0 it is taken in HS-mode.\n"
        "3. With C or Zca: writing bit 0 reads back 0 or 1 (no check beyond the absence of a trap).",
    )
    lab = t.label("b0")
    t.emit(f"{lab}:", 0)
    t.li("x7", 1)
    t.emit("csrw 0x602, x7")
    t.emit("csrr x8, 0x602")
    with t.only_if("!defined(ZCA_SUPPORTED) && !defined(C_SUPPORTED)"):
        t.check("x8", 1, lab, "hedeleg[0] is writable with IALIGN=32")
        bare(t)
        for deleg in (1, 0):
            t.li("x7", deleg)
            t.emit("csrw 0x602, x7")
            tgt = t.label("misal")
            k = Kind(
                "jalr to misaligned target",
                [f"LA(x6, {tgt})", "addi x6, x6, 2"],
                ["jalr ra, 0(x6)", f"{tgt}:", "nop", "nop"],
                lambda m: 0,
                None,
                [0],
                True,
                modes=("VS",),
            )
            lab2 = t.label("misVS")
            for p in k.pre:
                t.emit(p, 2)
            t.allow(1)
            t.enter("VS")
            t.emit(f"{lab2}:", 0)
            for ln in k.lines:
                t.emit(ln)
            t.leave()
            t.emit(f"LA(x6, {tgt})", 2)
            t.outcome(
                0,
                lab2,
                f"VS-mode jalr to a misaligned target, hedeleg[0]={deleg}",
                [0, f"{tgt}+2"],
                epc=True,
                origin="VS",
            )
            handler_is(t, "VS" if deleg and MUT != "hedeleg_ignored" else "S", lab2, f"hedeleg[0]={deleg}")
    t.emit("csrw 0x602, x0")
    t.emit("csrr x8, 0x602")
    t.check("x8", 0, lab, "hedeleg reads 0 after writing 0")
    tests.append(t)
    return tests


# ---------------------------------------------------------------- delegation
def gen_deleg() -> list[TestFile]:
    tests = []
    K = kinds()

    # ---- hedeleg_op ----
    t = new("hedeleg_op")
    t.describe(
        source=HYP,
        rule_text="A synchronous trap that has been delegated to HS-mode (using medeleg) is further delegated to "
        "VS-mode if V=1 before the trap and the corresponding hedeleg bit is set.",
        context="The framework's medeleg delegates causes 1-8 and 12-23 to HS-mode. The trapping instructions are "
        "ebreak (3), MRET below M-mode (illegal, 2), and load, store and fetch access faults (5, 7, 1) at the DUT's "
        "access-fault address with vsatp and hgatp Bare. A trap taken in VS-mode is handled by the framework's VS "
        "handler (handler mode 2), which logs vscause, vsepc and vstval.",
        plan="1. For each cause, hedeleg = only that bit: the exception from VS-mode and from VU-mode is taken in "
        "VS-mode with the same cause, xepc and xtval.\n"
        "2. hedeleg = 0: the same exceptions are taken in HS-mode.\n"
        "3. hedeleg = every other writable bit (all ones except that cause): taken in HS-mode, so one bit does not "
        "delegate another cause.\n"
        "4. V=0: with that hedeleg bit set, the exception from HS-mode and U-mode is taken in HS-mode.",
    )
    bare(t)
    for name in ("ebreak", "illegal", "load", "store", "fetch"):
        k = K[name]
        c = k.cause("VS")

        def body(k: Kind = k, c: int = c) -> None:
            for hd, note in (
                (1 << c, "only its bit"),
                (0, "0"),
                (0xFFFFFFFF & ~(1 << c) & ~(1 << 8), "every other bit"),
            ):
                t.li("x7", hd) if hd < 0x800 else t.load("x7", hd, "hedeleg value")
                t.emit("csrw 0x602, x7  // hedeleg")
                for mode in ("VS", "VU"):
                    lab = twin(t, mode, k, f"hedeleg = {note}")
                    handler_is(t, where(mode, c, hd), lab, f"hedeleg = {note}")
                if hd == 1 << c:
                    for mode in ("S", "U"):
                        lab = twin(t, mode, k, f"V=0, hedeleg = {note}")
                        handler_is(t, where(mode, c, hd), lab, f"V=0, hedeleg = {note}")

        guard(t, k.cond, body)
    t.emit("csrw 0x602, x0")
    tests.append(t)

    # ---- H_trap_deleg ----
    t = new("H_trap_deleg")
    t.describe(
        source=HYP,
        rule_text="When a trap occurs in HS-mode or U-mode, it goes to M-mode, unless delegated by medeleg or "
        "mideleg, in which case it goes to HS-mode. When a trap occurs in VS-mode or VU-mode, it goes to M-mode, "
        "unless delegated by medeleg or mideleg, in which case it goes to HS-mode, unless further delegated by "
        "hedeleg or hideleg, in which case it goes to VS-mode.",
        context="This file uses the framework's medeleg (ecall from HS-mode, cause 9, is not delegated). "
        "H_trap_deleg_Sm clears medeleg bits. Some hedeleg bits are read-only zero (ecall from VS 10, virtual "
        "instruction 22), so those exceptions never reach VS-mode. Interrupts are covered by the interrupt tests.",
        plan="1. hedeleg = all ones (VU ecalls go through the VS handler, which the framework supports): ebreak, "
        "illegal, access faults and ecall (cause 8) from VU go to VS-mode; from VS-mode too, except ecall (10) and "
        "virtual-instruction (22), which go to HS-mode.\n"
        "2. ecall from HS-mode goes to M-mode (medeleg[9]=0) and from U-mode to HS-mode.\n"
        "3. hedeleg = 0: everything from VS/VU goes to HS-mode.",
    )
    bare(t)
    for hd in (0xFFFFFFFF, 0):
        t.load("x7", hd, "hedeleg") if hd else t.emit("li x7, 0")
        t.emit("csrw 0x602, x7  // hedeleg")
        t.emit("csrr x8, 0x602  // hedeleg as implemented")
        for name in ("ebreak", "illegal", "virtual", "ecall", "load", "fetch"):
            k = K[name]

            def hd_body(k: Kind = k, hd: int = hd) -> None:
                for mode in k.modes:
                    if mode == "M":
                        continue
                    if hd == 0 and mode in ("S", "U"):
                        continue
                    lab = twin(t, mode, k, f"hedeleg = {hex(hd)}")
                    handler_is(t, where(mode, k.cause(mode), hd), lab, f"hedeleg = {hex(hd)}")

            guard(t, k.cond, hd_body)
    t.emit("csrw 0x602, x0")
    tests.append(t)

    # ---- H_trap_deleg_Sm ----
    t = new("H_trap_deleg", ["I", "S", "H", "Sm"], boot="M", suffix="_Sm")
    t.describe(
        source=HYP,
        rule_text="When a trap occurs in HS-mode or U-mode, it goes to M-mode, unless delegated by medeleg or "
        "mideleg, in which case it goes to HS-mode. When a trap occurs in VS-mode or VU-mode, it goes to M-mode, "
        "unless delegated by medeleg or mideleg, in which case it goes to HS-mode, unless further delegated by "
        "hedeleg or hideleg, in which case it goes to VS-mode.",
        context="M-mode part: the test boots to M-mode, where the framework leaves medeleg = 0, enters the other "
        "modes with T-SBI GOTO and returns with GOTO_MMODE (an ecall that M-mode handles directly).",
        plan="1. medeleg[3]=0 with hedeleg[3]=1: ebreak from HS, U, VS and VU is taken in M-mode (hedeleg alone "
        "does not delegate).\n"
        "2. medeleg[3]=1, hedeleg[3]=0: taken in HS-mode from every mode.\n"
        "3. medeleg[3]=1, hedeleg[3]=1: taken in VS-mode from VS and VU, in HS-mode from HS and U.\n"
        "4. The same three settings for load access faults (cause 5).",
    )
    bare(t)
    for name in ("ebreak", "load"):
        k = K[name]
        c = k.cause("VS")

        def body(k: Kind = k, c: int = c) -> None:
            for med, hed in ((0, 1), (1, 0), (1, 1)):
                t.li("x7", 1 << c)
                t.emit(f"{'csrs' if med else 'csrc'} medeleg, x7")
                t.emit(f"{'csrs' if hed else 'csrc'} 0x602, x7  // hedeleg")
                for mode in ("S", "U", "VS", "VU"):
                    if not med:
                        w = "VS" if (MUT == "medeleg_bypass" and mode in ("VS", "VU")) else "M"
                    else:
                        w = "VS" if (hed and mode in ("VS", "VU")) else "S"
                    lab = twin(t, mode, k, f"medeleg[{c}]={med}, hedeleg[{c}]={hed}")
                    handler_is(t, w, lab, f"medeleg[{c}]={med}, hedeleg[{c}]={hed}")
            t.li("x7", 1 << c)
            t.emit("csrc medeleg, x7")
            t.emit("csrc 0x602, x7")

        guard(t, k.cond, body)
    tests.append(t)

    # ---- H_cause ----
    t = new("H_cause")
    t.describe(
        source=HYP,
        rule_text="The hypervisor extension augments the trap cause encoding. <<hcauses>> lists the possible M-mode "
        "and HS-mode trap cause codes when the hypervisor extension is implemented. Codes are added for VS-level "
        "interrupts (interrupts 2, 6, 10), for supervisor-level guest external interrupts (interrupt 12), for "
        "virtual-instruction exceptions (exception 22), and for guest-page faults (exceptions 20, 21, 23). "
        "Furthermore, environment calls from VS-mode are assigned cause 10, whereas those from HS-mode or S-mode "
        "use cause 9 as usual.",
        context="ecall is T-SBI's ECALL_TEST (a0 = 0x73), which the handlers log like any trap. ecall from VU-mode "
        "is cause 8 (environment call from U-mode or VU-mode). Interrupt codes and guest-page faults are covered "
        "by the interrupt and translation tests; virtual-instruction (22) is checked here once.",
        plan="1. ecall from VS-mode: cause 10, taken in HS-mode.\n"
        "2. ecall from VU-mode: cause 8 in HS-mode, and in VS-mode (vscause 8) with hedeleg[8]=1.\n"
        "3. ecall from HS-mode: cause 9 in M-mode; from U-mode: cause 8 in HS-mode.\n"
        "4. With hedeleg = all ones, ecall from VS-mode is still cause 10 in HS-mode.\n"
        "5. A VS-mode hstatus read: cause 22.",
    )
    for hd in (0, 0x100, 0xFFFFFFFF):
        t.load("x7", hd, "hedeleg") if hd > 0x7FF else t.li("x7", hd)
        t.emit("csrw 0x602, x7  // hedeleg")
        for mode in ("VS", "VU") if hd else ("VS", "VU", "S", "U"):
            lab = twin(t, mode, K["ecall"], f"hedeleg = {hex(hd)}")
            handler_is(t, where(mode, ecall_cause(mode), hd), lab, f"hedeleg = {hex(hd)}")
    t.emit("csrw 0x602, x0")
    twin(t, "VS", K["virtual"], "hedeleg = 0")
    tests.append(t)
    return tests


# ---------------------------------------------------------------- traps into HS: hstatus/sstatus writes
def hs_trap_case(
    t: TestFile,
    mode: str,
    k: Kind,
    *,
    spvp: int,
    gva_pre: int,
    s: int,
    vs: int,
    spv_pre: int,
    checks: set[str],
    desc: str,
) -> str:
    """Trap from `mode` into HS-mode with known prior state; check the fields in `checks`."""
    t.comment(
        f"{desc}: preset SPVP={spvp}, GVA={gva_pre}, SPV={spv_pre}; HS SIE before the trap {s}, vsstatus.SIE={vs}"
    )
    for bit, on in ((SPVP, spvp), (GVA, gva_pre), (SPV, spv_pre)):
        hs_bits(t, "hstatus", bit, bool(on), f"hstatus bit {hex(bit)} = {on}")
    hs_bits(t, "vsstatus", SIE, bool(vs), f"vsstatus.SIE = {vs}")
    if mode == "S":
        hs_bits(t, "sstatus", SIE, bool(s), f"sstatus.SIE = {s} (trap from HS-mode)")
    else:
        hs_bits(t, "sstatus", SPIE, bool(s), f"sstatus.SPIE = {s}: the sret into {mode} makes SIE = {s}")
    lab = twin(t, mode, k, desc)
    v = mode in ("VS", "VU")
    spp = 1 if mode in ("S", "VS") else 0
    handler_is(t, "S", lab, desc)
    if "spv" in checks:
        exp = int(v) if not (MUT == "spv_not_written_v0" and not v) else spv_pre
        logchk(t, "TRAPLOG_STATUS2", SPV, SPV * exp, lab, f"{desc}: hstatus.SPV = V = {int(v)}")
    if "spp" in checks:
        logchk(t, "TRAPLOG_STATUS", SPP, SPP * spp, lab, f"{desc}: sstatus.SPP = {spp}")
    if "spvp" in checks:
        exp = spp if v or MUT == "spvp_written_v0" else spvp
        logchk(
            t,
            "TRAPLOG_STATUS2",
            SPVP,
            SPVP * exp,
            lab,
            f"{desc}: hstatus.SPVP = {exp} ({'= SPP, V was 1' if v else 'unchanged, V was 0'})",
        )
    if "sie" in checks:
        sp = vs if (MUT == "spie_from_vsstatus" and v) else s
        logchk(t, "TRAPLOG_STATUS", SPIE | SIE, SPIE * sp, lab, f"{desc}: sstatus.SPIE = old SIE = {s}, SIE = 0")
    if "gva" in checks:
        if k.va and (v or k.name.startswith(("HLV", "HSV"))):
            gva_ok(t, "S", lab, desc)
        else:
            gva_zero(t, "S", lab, desc)
    return lab


def gen_hs_writes() -> list[TestFile]:
    tests = []
    K = kinds()
    modes = ("S", "U", "VS", "VU")

    # ---- H_trap_hs_csrwrites ----
    t = new("H_trap_hs_csrwrites")
    t.describe(
        source=HYP,
        rule_text="When a trap is taken into HS-mode, virtualization mode V is set to 0, and hstatus.SPV and "
        "sstatus.SPP are set according to <<h-spp>>. If V was 1 before the trap, field SPVP in hstatus is set the "
        "same as sstatus.SPP; otherwise, SPVP is left unchanged. A trap into HS-mode also writes field GVA in "
        "hstatus, fields SPIE and SIE in sstatus, and CSRs sepc, scause, stval, htval, and htinst.",
        context="Table h-spp: from U SPV=0 SPP=0, HS 0/1, VU 1/0, VS 1/1. The trap log holds sstatus and hstatus on "
        "handler entry, sepc, scause, stval, htval and htinst. V=0 in the handler shows in that it runs the HS "
        "handler (handler mode 1). vsstatus belongs to VS-mode and is not among the fields written.",
        issues=ISSUE_GVA,
        plan="1. ebreak, illegal (MRET), virtual-instruction (from VS/VU), and load/fetch access faults, from HS, "
        "U, VS and VU: each preset hstatus.SPVP, GVA and SPV to the opposite of their expected value (SPVP: "
        "1 - SPP for V=1 traps, both values for V=0), and HS-level SIE to a value that differs from vsstatus.SIE.\n"
        "2. Check SPV, SPP, SPVP, SPIE = old SIE, SIE = 0, GVA (1 when stval holds a guest virtual address, else "
        "0), and cause, sepc, stval and origin.\n"
        "3. htval is 0 and htinst is 0 or the transformed instruction (H_trap_xtinst_val).\n"
        "4. vsstatus.SPP, SPIE, SIE and vsepc, vscause, vstval keep values written before the trap.",
    )
    bare(t)
    for vv, name in (("vsepc", 0x40), ("vscause", 13), ("vstval", 0x123)):
        t.li("x7", name)
        t.emit(f"csrw {hex({'vsepc': 0x241, 'vscause': 0x242, 'vstval': 0x243}[vv])}, x7  // {vv} sentinel")
    hs_bits(t, "vsstatus", SPP | SPIE, True, "vsstatus.SPP = SPIE = 1 (sentinels)")
    i = 0
    for name in ("ebreak", "illegal", "virtual", "load", "fetch"):
        k = K[name]

        def csrw_body(k: Kind = k) -> None:
            nonlocal i
            for mode in k.modes:
                if mode == "M":
                    continue
                v = mode in ("VS", "VU")
                spp = 1 if mode in ("S", "VS") else 0
                s, vs = i % 2, 1 - i % 2
                i += 1
                lab = hs_trap_case(
                    t,
                    mode,
                    k,
                    spvp=(1 - spp) if v else i % 2,
                    gva_pre=0 if k.va and v else 1,
                    s=s,
                    vs=vs,
                    spv_pre=0 if v else 1,
                    checks={"spv", "spp", "spvp", "sie", "gva"},
                    desc=f"{k.name} from {mode}",
                )
                logchk(t, "TRAPLOG_TVAL2", X((1 << 32) - 1, (1 << 64) - 1), 0, lab, f"{k.name} from {mode}: htval=0")
                logchk(
                    t,
                    "TRAPLOG_TINST",
                    X((1 << 32) - 1, (1 << 64) - 1),
                    k.tinst,
                    lab,
                    f"{k.name} from {mode}: htinst is one of its legal values",
                )
                t.emit("csrr x8, 0x200  // vsstatus")
                exp = SPIE | (0 if MUT == "vsstatus_written_on_hs_trap" and mode == "U" else SPP)
                t.check_masked(
                    "x8", SPP | SPIE, exp, lab, f"{k.name} from {mode}: vsstatus.SPP/SPIE unchanged", tmp="x5"
                )
                for num, val, nm in ((0x241, 0x40, "vsepc"), (0x242, 13, "vscause"), (0x243, 0x123, "vstval")):
                    t.emit(f"csrr x8, {hex(num)}  // {nm}")
                    t.check("x8", val, lab, f"{k.name} from {mode}: {nm} unchanged by a trap into HS-mode")

        guard(t, k.cond, csrw_body)
    hs_bits(t, "hstatus", SPVP | GVA | SPV, False, "hstatus.SPVP = GVA = SPV = 0")
    tests.append(t)

    # ---- hstatus_spv_op ----
    t = new("hstatus_spv_op")
    t.describe(
        source=HYP,
        rule_text="The SPV bit (Supervisor Previous Virtualization mode) is written by the implementation whenever "
        "a trap is taken into HS-mode. Just as the SPP bit in sstatus is set to the (nominal) privilege mode at the "
        "time of the trap, the SPV bit in hstatus is set to the value of the virtualization mode V at the time of "
        "the trap.",
        context="SPV is preset to the opposite of V before each trap, so a trap that does not write SPV is caught. "
        "A trap from VS or VU into VS-mode does not go to HS-mode and leaves hstatus alone (H_trap_vs_csrwrites).",
        plan="1. ebreak, ecall (from U, VS, VU) and load access faults from HS, U, VS and VU, with SPV preset to "
        "1 - V: hstatus.SPV on handler entry equals V (and sstatus.SPP the nominal mode).",
    )
    bare(t)
    for name in ("ebreak", "ecall", "load"):
        k = K[name]

        def body(k: Kind = k, name: str = name) -> None:
            for mode in modes:
                if name == "ecall" and mode == "S":
                    continue
                hs_trap_case(
                    t,
                    mode,
                    k,
                    spvp=0,
                    gva_pre=0,
                    s=0,
                    vs=0,
                    spv_pre=0 if mode in ("VS", "VU") else 1,
                    checks={"spv", "spp"},
                    desc=f"{k.name} from {mode}",
                )

        guard(t, k.cond, body)
    hs_bits(t, "hstatus", SPV, False, "hstatus.SPV = 0")
    tests.append(t)

    # ---- hstatus_spvp_op ----
    t = new("hstatus_spvp_op")
    t.describe(
        source=HYP,
        rule_text="When V=1 and a trap is taken into HS-mode, bit SPVP (Supervisor Previous Virtual Privilege) is "
        "set to the nominal privilege mode at the time of the trap, the same as sstatus.SPP. But if V=0 before a "
        "trap, SPVP is left unchanged on trap entry.",
        plan="1. From VS (SPVP preset 0) and VU (preset 1): SPVP = 1 and 0.\n"
        "2. From HS and U with SPVP preset 0 and then 1: SPVP keeps the preset (it is not written from SPP).\n"
        "3. Traps: ebreak, illegal (MRET) and load access faults; HLV access faults from HS-mode (V=0) also "
        "leave SPVP unchanged.",
    )
    bare(t)
    for name in ("ebreak", "illegal", "load", "hlv"):
        k = K[name]

        def spvp_body(k: Kind = k) -> None:
            for mode in k.modes:
                if mode == "M":
                    continue
                presets = (0,) if mode == "VS" else (1,) if mode == "VU" else (0, 1)
                for p in presets:
                    hs_trap_case(
                        t,
                        mode,
                        k,
                        spvp=p,
                        gva_pre=0,
                        s=0,
                        vs=0,
                        spv_pre=0,
                        checks={"spvp", "spp"},
                        desc=f"{k.name} from {mode}, SPVP preset {p}",
                    )

        guard(t, k.cond, spvp_body)
    hs_bits(t, "hstatus", SPVP, False, "hstatus.SPVP = 0")
    tests.append(t)

    # ---- hstatus_gva_op ----
    t = new("hstatus_gva_op")
    t.describe(
        source=HYP,
        rule_text="Field GVA (Guest Virtual Address) is written by the implementation whenever a trap is taken into "
        "HS-mode. For any trap (breakpoint, address misaligned, access fault, page fault, or guest-page fault) that "
        "writes a guest virtual address to stval, GVA is set to 1. For any other trap into HS-mode, GVA is set to "
        "0.",
        context="A guest virtual address comes from a VS/VU access or from HLV/HSV (whose effective mode is VS or "
        "VU) in any mode. Breakpoints, illegal, virtual-instruction and ecall traps from HS/U, and illegal, "
        "virtual and ecall from VS/VU, write no guest virtual address.",
        issues=ISSUE_GVA,
        plan="1. GVA preset 0, then a guest-virtual-address trap: ebreak, load, store and fetch access faults from "
        "VS and VU; HLV.W and HSV.W access faults from HS-mode and from U-mode with hstatus.HU=1: GVA = 1 "
        "(checked when stval is nonzero).\n"
        "2. GVA preset 1, then a trap without one: ebreak and load fault from HS and U; illegal, ecall from VS, "
        "VU, U; virtual-instruction from VS and VU: GVA = 0.",
    )
    bare(t)
    hs_bits(t, "hstatus", 0x200, True, "hstatus.HU = 1 (U-mode may execute HLV/HSV)")
    for name in ("ebreak", "load", "store", "fetch", "hlv", "hsv", "illegal", "ecall", "virtual"):
        k = K[name]

        def body(k: Kind = k, name: str = name) -> None:
            ms = [m for m in k.modes if m != "M"]
            if k.name.startswith(("HLV", "HSV")):
                ms = ["S", "U"]
            for mode in ms:
                if name == "ecall" and mode == "S":
                    continue
                v = mode in ("VS", "VU")
                guest = k.va and (v or k.name.startswith(("HLV", "HSV")))
                hs_trap_case(
                    t,
                    mode,
                    k,
                    spvp=0,
                    gva_pre=0 if guest else 1,
                    s=0,
                    vs=0,
                    spv_pre=0,
                    checks={"gva"},
                    desc=f"{k.name} from {mode}",
                )

        guard(t, k.cond, body)
    hs_bits(t, "hstatus", 0x200 | GVA, False, "hstatus.HU = GVA = 0")
    tests.append(t)
    return tests


# ---------------------------------------------------------------- traps into VS
def gen_vs_writes() -> list[TestFile]:
    tests = []
    K = kinds()

    t = new("H_trap_vs_csrwrites")
    t.describe(
        source=HYP,
        rule_text="When a trap is taken into VS-mode, vsstatus.SPP is set according to <<h-vspp>>. Register hstatus "
        "and the HS-level sstatus are not modified, and the virtualization mode V remains 1. A trap into VS-mode "
        "also writes fields SPIE and SIE in vsstatus and writes CSRs vsepc, vscause, and vstval.",
        context="Table h-vspp: from VU SPP=0, from VS SPP=1. The VS handler logs vsstatus on entry, vscause, vsepc "
        "and vstval. That V remains 1 shows when a later hstatus read in the same mode raises virtual-instruction "
        "(not a successful read). hstatus and the HS sstatus are checked from M-mode in H_trap_vs_csrwrites_Sm, "
        "because returning to HS-mode is itself a trap into HS-mode.",
        plan="1. hedeleg delegates ebreak, illegal and load access faults. From VS and VU, with vsstatus.SIE preset "
        "to 0 and 1 and vsstatus.SPP preset to the opposite of the expected value: taken in VS-mode, with "
        "vsstatus.SPP = 1 (VS) or 0 (VU), SPIE = old SIE, SIE = 0, and vscause, vsepc, vstval as for a trap.\n"
        "2. After the VS handler returns, an hstatus read in the same mode raises virtual-instruction from that "
        "mode in HS-mode (V is still 1 and the nominal mode unchanged).\n"
        "3. An HS-mode read of vscause after the window returns the trap's cause.",
    )
    bare(t)
    for name in ("ebreak", "illegal", "load"):
        k = K[name]
        c = k.cause("VS")

        def body(k: Kind = k, c: int = c) -> None:
            t.li("x7", 1 << c)
            t.emit("csrw 0x602, x7  // hedeleg")
            for mode in ("VS", "VU"):
                for vsie in (0, 1):
                    spp = 1 if mode == "VS" else 0
                    hs_bits(t, "vsstatus", SPP, not spp, f"vsstatus.SPP = {1 - spp} (opposite of expected)")
                    hs_bits(t, "vsstatus", SIE, bool(vsie), f"vsstatus.SIE = {vsie}")
                    hs_bits(t, "vsstatus", SPIE, not vsie, f"vsstatus.SPIE = {1 - vsie}")
                    lab = t.label(f"vs_{mode}")
                    for p in k.pre:
                        t.emit(p, 2)
                    t.allow(2)
                    t.enter(mode)
                    t.emit(f"{lab}:", 0)
                    for ln in k.lines:
                        t.emit(ln)
                    lab2 = t.label("still")
                    t.emit(f"{lab2}:", 0)
                    t.emit("csrr x8, 0x600  // hstatus: virtual-instruction if V is still 1")
                    t.leave()
                    t.emit("AI_OUTCOME", 20)
                    d = f"{k.name} from {mode}, vsstatus.SIE={vsie}"
                    t.check("x13", 2, lab, f"{d}: two traps (the exception, then the hstatus read)")
                    t.check("x14", 22, lab2, f"{d}: the hstatus read after the VS handler raises virtual-instruction")
                    w = "S" if MUT == "hedeleg_ignored" else "VS"
                    handler_is(t, w, lab, d, back=1)
                    logchk(t, "TRAPLOG_CAUSE", X((1 << 32) - 1, (1 << 64) - 1), c, lab, f"{d}: vscause", back=1)
                    if k.epc:
                        logw(t, "x15", "TRAPLOG_EPC", back=1)
                        t.emit(f"LA(x14, {lab})", 2)
                        t.emit("xor x15, x15, x14")
                        t.check("x15", 0, lab, f"{d}: vsepc is the trapping instruction")
                    vexp = (SPP * spp) | (SPIE * vsie)
                    logchk(
                        t,
                        "TRAPLOG_STATUS",
                        SPP | SPIE | SIE,
                        vexp,
                        lab,
                        f"{d}: vsstatus.SPP={spp}, SPIE=old SIE={vsie}, SIE=0",
                        back=1,
                    )
                    handler_is(t, "S", lab2, f"{d}, then hstatus read")
                    logchk(t, "TRAPLOG_STATUS2", SPV, SPV, lab2, f"{d}: the hstatus read came from V=1")
                    logchk(t, "TRAPLOG_STATUS", SPP, SPP * spp, lab2, f"{d}: and from nominal mode {mode}")
                    t.emit("csrr x8, 0x242  // vscause")
                    t.check("x8", c, lab, f"{d}: HS-mode reads vscause = {c}")

        guard(t, k.cond, body)
    t.emit("csrw 0x602, x0")
    tests.append(t)

    # ---- H_trap_vs_csrwrites_Sm ----
    t = new("H_trap_vs_csrwrites", ["I", "S", "H", "Sm"], boot="M", suffix="_Sm")
    t.describe(
        source=HYP,
        rule_text="When a trap is taken into VS-mode, vsstatus.SPP is set according to <<h-vspp>>. Register hstatus "
        "and the HS-level sstatus are not modified, and the virtualization mode V remains 1. A trap into VS-mode "
        "also writes fields SPIE and SIE in vsstatus and writes CSRs vsepc, vscause, and vstval.",
        context="M-mode part: the test boots to M-mode, so medeleg is 0 except for the bits set here. The guest is "
        "entered with T-SBI GOTO (an mret) and left with GOTO_MMODE, an ecall that M-mode takes directly "
        "(medeleg[8] and [10] = 0), so no trap into HS-mode happens around the trap under test.",
        plan="1. M-mode presets hstatus (SPV=0, SPVP=0, GVA=1), sstatus (SPP=1, SPIE=1, SIE=0), sepc, scause, "
        "stval, htval and htinst.\n"
        "2. medeleg[3]=hedeleg[3]=1: ebreak in VS-mode and in VU-mode is taken in VS-mode.\n"
        "3. Back in M-mode: hstatus, sstatus.SPP/SPIE/SIE, sepc, scause and stval are unchanged.",
    )
    bare(t)
    t.li("x7", 1 << 3)
    t.emit("csrs medeleg, x7")
    t.emit("csrs 0x602, x7  // hedeleg[3]")
    for mode in ("VS", "VU"):
        t.comment("HS-level sentinels")
        t.li("x7", SPV | SPVP)
        t.emit("csrc 0x600, x7  // hstatus.SPV = SPVP = 0")
        t.li("x7", GVA)
        t.emit("csrs 0x600, x7  // hstatus.GVA = 1")
        t.li("x7", SPP | SPIE)
        t.emit("csrs sstatus, x7")
        t.li("x7", SIE)
        t.emit("csrc sstatus, x7")
        for num, val in ((0x141, 0x2C0), (0x142, 12), (0x143, 0x777)):
            t.li("x7", val)
            t.emit(f"csrw {hex(num)}, x7")
        lab = twin(t, mode, K["ebreak"], "medeleg[3]=hedeleg[3]=1, guest entered from M-mode")
        handler_is(t, "S" if MUT == "hedeleg_ignored" else "VS", lab, f"ebreak from {mode}")
        t.emit("csrr x8, 0x600")
        t.check_masked(
            "x8",
            SPV | SPVP | GVA,
            GVA,
            lab,
            f"ebreak from {mode} into VS-mode leaves hstatus SPV=0, SPVP=0, GVA=1",
            tmp="x5",
        )
        t.emit("csrr x8, sstatus")
        t.check_masked(
            "x8",
            SPP | SPIE | SIE,
            SPP | SPIE,
            lab,
            f"ebreak from {mode} into VS-mode leaves sstatus SPP=1, SPIE=1, SIE=0",
            tmp="x5",
        )
        for num, val, nm in ((0x141, 0x2C0, "sepc"), (0x142, 12, "scause"), (0x143, 0x777, "stval")):
            t.emit(f"csrr x8, {hex(num)}  // {nm}")
            bad = MUT == "vs_trap_writes_sepc" and nm == "sepc"
            t.check("x8", lab if bad else val, lab, f"ebreak from {mode} into VS-mode leaves {nm}")
    t.li("x7", 1 << 3)
    t.emit("csrc medeleg, x7")
    t.emit("csrc 0x602, x7")
    tests.append(t)
    return tests


# ---------------------------------------------------------------- traps into M
def m_trap_case(
    t: TestFile, mode: str, k: Kind, *, mpv_pre: int, gva_pre: int, desc: str, checks: set[str], mie: int = 0
) -> str:
    t.comment(f"{desc}: preset MPV={mpv_pre}, GVA={gva_pre}")
    with t.rv64_only():
        for bit, on in ((39, mpv_pre), (38, gva_pre)):
            t.li("x7", 1)
            t.emit(f"slli x7, x7, {bit}")
            t.emit(f"{'csrs' if on else 'csrc'} mstatus, x7")
    with t.rv32_only():
        for bit, on in ((7, mpv_pre), (6, gva_pre)):
            t.li("x7", 1 << bit)
            t.emit(f"{'csrs' if on else 'csrc'} 0x310, x7  // mstatush")
    if mode == "M":
        t.li("x7", MIE)
        t.emit(f"{'csrs' if mie else 'csrc'} mstatus, x7  // MIE = {mie}")
    lab = twin(t, mode, k, desc)
    v = mode in ("VS", "VU")
    mpp = {"U": 0, "VU": 0, "S": 1, "VS": 1, "M": 3}[mode]
    handler_is(t, "M", lab, desc)
    if "mpv" in checks:
        exp = int(v) if not (MUT == "mpv_not_written" and not v) else mpv_pre
        mpv_gva(t, "MPV", exp, lab, f"{desc}: MPV = V = {int(v)}")
    if "mpp" in checks:
        logchk(t, "TRAPLOG_STATUS", MPP, mpp << 11, lab, f"{desc}: MPP = {mpp}")
    if "mie" in checks:
        if mode == "M":
            logchk(t, "TRAPLOG_STATUS", MPIE | MIE, MPIE * mie, lab, f"{desc}: MPIE = old MIE = {mie}, MIE = 0")
        else:
            logchk(t, "TRAPLOG_STATUS", MIE, 0, lab, f"{desc}: MIE = 0")
    if "gva" in checks:
        if k.va and (v or k.name.startswith(("HLV", "HSV"))):
            gva_ok(t, "M", lab, desc)
        else:
            gva_zero(t, "M", lab, desc)
    if "tval2" in checks:
        logchk(t, "TRAPLOG_TVAL2", X((1 << 32) - 1, (1 << 64) - 1), 0, lab, f"{desc}: mtval2 = 0")
    if "tinst" in checks:
        logchk(t, "TRAPLOG_TINST", X((1 << 32) - 1, (1 << 64) - 1), k.tinst, lab, f"{desc}: mtinst legal value")
    return lab


def gen_m_writes() -> list[TestFile]:
    tests = []
    K = kinds()
    REQ_M = ["I", "S", "H", "Sm"]
    names = ("ebreak", "illegal", "virtual", "ecall", "load", "store", "fetch", "hlv", "hsv")

    def sweep(
        t: TestFile,
        checks: set[str],
        kinds_: tuple[str, ...],
        mpv_flip: bool = True,
        gva_flip: bool = True,
        ms: tuple[str, ...] = ("M", "S", "U", "VS", "VU"),
    ) -> None:
        i = 0
        for name in kinds_:
            k = K[name]

            def body(k: Kind = k, name: str = name) -> None:
                nonlocal i
                for mode in ms:
                    if mode not in k.modes and not (k.name.startswith(("HLV", "HSV")) and mode == "M"):
                        continue
                    if name == "illegal" and mode == "M":
                        continue
                    v = mode in ("VS", "VU")
                    guest = k.va and (v or k.name.startswith(("HLV", "HSV")))
                    i += 1
                    m_trap_case(
                        t,
                        mode,
                        k,
                        mpv_pre=(1 - int(v)) if mpv_flip else 0,
                        gva_pre=(0 if guest else 1) if gva_flip else 0,
                        desc=f"{k.name} from {mode}",
                        checks=checks,
                        mie=i % 2,
                    )

            guard(t, k.cond, body)

    # ---- H_trap_m_csrwrites_Sm ----
    t = new("H_trap_m_csrwrites", REQ_M, boot="M", suffix="_Sm")
    t.describe(
        source=HYP,
        rule_text="When a trap is taken into M-mode, virtualization mode V gets set to 0, and fields MPV and MPP in "
        "mstatus (or mstatush) are set according to <<h-mpp>>. A trap into M-mode also writes fields GVA, MPIE, "
        "and MIE in mstatus/mstatush and writes CSRs mepc, mcause, mtval, mtval2, and mtinst.",
        context="The test boots to M-mode, where the framework leaves medeleg = 0, so every exception goes to "
        "M-mode. Table h-mpp: U 0/0, HS 0/1, M 0/3, VU 1/0, VS 1/1 (MPV/MPP). On RV32, MPV and GVA are in "
        "mstatush, which the M handler logs. The HS-level trap CSRs are not among those written.",
        issues=ISSUE_GVA,
        plan="1. ebreak, illegal (MRET below M), virtual-instruction, ecall, load/store/fetch access faults and "
        "HLV/HSV access faults from M, HS, U, VS and VU (as applicable), with MPV and GVA preset to the opposite "
        "of their expected values.\n"
        "2. Check MPV, MPP, MPIE = old MIE (from M-mode; MIE = 0 always), GVA, mepc, mcause, mtval, mtval2 = 0 and "
        "mtinst legal.\n"
        "3. hstatus.SPV/SPVP/GVA and sepc keep values written before the traps.",
    )
    bare(t)
    t.li("x7", SPV | SPVP | GVA)
    t.emit("csrc 0x600, x7  // hstatus.SPV = SPVP = GVA = 0")
    t.li("x7", 0x5A0)
    t.emit("csrw sepc, x7  // sepc sentinel")
    sweep(t, {"mpv", "mpp", "mie", "gva", "tval2", "tinst"}, names)
    lab = t.label("hs")
    t.emit(f"{lab}:", 0)
    t.emit("csrr x8, 0x600")
    t.check_masked("x8", SPV | SPVP | GVA, 0, lab, "traps into M-mode leave hstatus SPV, SPVP, GVA", tmp="x5")
    t.emit("csrr x8, sepc")
    t.check("x8", 0x5A0, lab, "traps into M-mode leave sepc")
    tests.append(t)

    # ---- H_trap_m_csrwrites (S-boot: ecall from HS-mode is the trap into M-mode) ----
    t = new("H_trap_m_csrwrites")
    t.describe(
        source=HYP,
        rule_text="When a trap is taken into M-mode, virtualization mode V gets set to 0, and fields MPV and MPP in "
        "mstatus (or mstatush) are set according to <<h-mpp>>. A trap into M-mode also writes fields GVA, MPIE, "
        "and MIE in mstatus/mstatush and writes CSRs mepc, mcause, mtval, mtval2, and mtinst.",
        context="Without changing medeleg, the one trap from below M into M-mode is ecall from HS-mode (cause 9, "
        "medeleg[9]=0). H_trap_m_csrwrites_Sm covers the other modes and causes.",
        plan="1. ecall from HS-mode after a VS-mode excursion (which leaves MPV state behind in the framework): "
        "taken in M-mode with cause 9, MPV = 0, MPP = 1, GVA = 0, MIE = 0, mtval = 0, mtval2 = 0 and mtinst = 0.",
    )
    for _ in range(2):
        t.allow(1)
        t.enter("VS")
        t.leave()
        lab = twin(t, "S", K["ecall"], "after a VS-mode excursion")
        handler_is(t, "M", lab, "ecall from HS-mode")
        mpv_gva(t, "MPV", 0, lab, "ecall from HS-mode")
        mpv_gva(t, "GVA", 0, lab, "ecall from HS-mode")
        logchk(t, "TRAPLOG_STATUS", MPP | MIE, 1 << 11, lab, "ecall from HS-mode: MPP = 1, MIE = 0")
        logchk(t, "TRAPLOG_TVAL2", X((1 << 32) - 1, (1 << 64) - 1), 0, lab, "ecall from HS-mode: mtval2 = 0")
        logchk(t, "TRAPLOG_TINST", X((1 << 32) - 1, (1 << 64) - 1), 0, lab, "ecall from HS-mode: mtinst = 0")
    tests.append(t)

    # ---- mstatus_mpv_op_Sm ----
    t = new("mstatus_mpv_op", REQ_M, boot="M", suffix="_Sm")
    t.describe(
        source=HYP,
        rule_text="The MPV bit (Machine Previous Virtualization Mode) is written by the implementation whenever a "
        "trap is taken into M-mode. Just as the MPP field is set to the (nominal) privilege mode at the time of the "
        "trap, the MPV bit is set to the value of the virtualization mode V at the time of the trap. When an MRET "
        "instruction is executed, the virtualization mode V is set to MPV, unless MPP=3, in which case V remains 0.",
        context="MRET's effect on V is in mret_H; this file checks the trap side, with MPV preset to the opposite "
        "of V. RV32 keeps MPV in mstatush.",
        plan="1. ebreak and ecall from M, HS, U, VS and VU with MPV preset to 1 - V: MPV = V and MPP = the nominal "
        "mode on handler entry.\n"
        "2. MRET with MPP=3 and MPV=1 stays in M-mode (an mscratch read succeeds) and leaves MPV = 0.",
    )
    bare(t)
    sweep(t, {"mpv", "mpp"}, ("ebreak", "ecall"), gva_flip=False)
    mret_m_case(t)
    tests.append(t)

    # ---- mstatus_mpv_op (S-boot) ----
    t = new("mstatus_mpv_op")
    t.describe(
        source=HYP,
        rule_text="The MPV bit (Machine Previous Virtualization Mode) is written by the implementation whenever a "
        "trap is taken into M-mode. Just as the MPP field is set to the (nominal) privilege mode at the time of the "
        "trap, the MPV bit is set to the value of the virtualization mode V at the time of the trap. When an MRET "
        "instruction is executed, the virtualization mode V is set to MPV, unless MPP=3, in which case V remains 0.",
        context="Without changing medeleg, ecall from HS-mode is the trap into M-mode; T-SBI's own GOTO_VSMODE from "
        "HS-mode ends in an MRET with MPV=1, which must enter VS-mode. mstatus_mpv_op_Sm covers the rest.",
        plan="1. ecall from HS-mode: MPV = 0 (each time, also right after a VS-mode excursion that set MPV=1).\n"
        "2. T-SBI GOTO_VSMODE from HS-mode (an MRET with MPP=1, MPV=1) lands in VS-mode: an hstatus read there "
        "raises virtual-instruction from VS-mode.",
    )
    for _ in range(2):
        lab = t.label("goto")
        t.allow(1)
        t.emit("RVTEST_TSBI_GOTO_VSMODE", 120)
        t.emit(f"{lab}:", 0)
        t.emit("csrr x7, 0x600  // hstatus")
        t.leave()
        t.outcome(
            22,
            lab,
            "after T-SBI GOTO_VSMODE (MRET with MPV=1): hstatus read",
            [0, (0x600 << 20) | (2 << 12) | (7 << 7) | 0x73],
            origin="VS",
        )
        lab = twin(t, "S", K["ecall"], "after a VS-mode excursion")
        mpv_gva(t, "MPV", 0, lab, "ecall from HS-mode")
    tests.append(t)

    # ---- mstatus_gva_op_Sm ----
    t = new("mstatus_gva_op", REQ_M, boot="M", suffix="_Sm")
    t.describe(
        source=HYP,
        rule_text="Field GVA (Guest Virtual Address) is written by the implementation whenever a trap is taken into "
        "M-mode. For any trap (breakpoint, address misaligned, access fault, page fault, or guest-page fault) that "
        "writes a guest virtual address to mtval, GVA is set to 1. For any other trap into M-mode, GVA is set to 0.",
        context="medeleg = 0 (M-mode boot). HLV/HSV from M-mode access guest virtual addresses.",
        issues=ISSUE_GVA,
        plan="1. GVA preset 0: ebreak and load/store/fetch access faults from VS and VU, and HLV/HSV access faults "
        "from M and HS: GVA = 1 when mtval is nonzero.\n"
        "2. GVA preset 1: ebreak and access faults from M, HS and U; illegal, ecall and virtual-instruction "
        "from every mode: GVA = 0.",
    )
    bare(t)
    sweep(t, {"gva"}, names, mpv_flip=False)
    tests.append(t)

    # ---- mstatus_gva_op (S-boot) ----
    t = new("mstatus_gva_op")
    t.describe(
        source=HYP,
        rule_text="Field GVA (Guest Virtual Address) is written by the implementation whenever a trap is taken into "
        "M-mode. For any trap (breakpoint, address misaligned, access fault, page fault, or guest-page fault) that "
        "writes a guest virtual address to mtval, GVA is set to 1. For any other trap into M-mode, GVA is set to 0.",
        context="Without changing medeleg, ecall from HS-mode is the trap into M-mode, and it carries no address. "
        "mstatus_gva_op_Sm covers the address cases.",
        plan="1. An HLV access fault in HS-mode sets hstatus.GVA (taken in HS-mode); the following ecall from HS-mode "
        "into M-mode writes mstatus.GVA = 0.",
    )
    bare(t)
    with t.only_if(HAS_LD):
        twin(t, "S", K["hlv"], "HLV access fault")
    lab = twin(t, "S", K["ecall"], "ecall from HS-mode")
    gva_zero(t, "M", lab, "ecall from HS-mode")
    tests.append(t)

    # ---- mtval2_trapval_Sm ----
    t = new("mtval2_trapval", REQ_M, boot="M", suffix="_Sm")
    t.describe(
        source=HYP,
        rule_text="When a guest-page-fault trap is taken into M-mode, mtval2 is written with either zero or the "
        "guest physical address that faulted, shifted right by 2 bits. For other traps, mtval2 is set to zero, but "
        "a future standard or extension may redefine mtval2's setting for other traps.",
        context="Guest-page faults are covered by the translation tests. mtval2 is WARL and may be unable to hold "
        "nonzero values; the test writes a nonzero value before each trap so that a trap that leaves mtval2 "
        "unwritten is caught where it can hold one.",
        plan="1. Before each trap M-mode writes mtval2 = 0x1000. Every trap kind (ebreak, illegal, virtual, ecall, "
        "access faults, HLV/HSV faults) from every mode: mtval2 = 0 on handler entry.",
    )
    bare(t)
    i = 0
    for name in names:
        k = K[name]

        def body(k: Kind = k, name: str = name) -> None:
            nonlocal i
            for mode in ("M", "S", "U", "VS", "VU"):
                if mode not in k.modes and not (k.name.startswith(("HLV", "HSV")) and mode == "M"):
                    continue
                if name == "illegal" and mode == "M":
                    continue
                t.li("x7", 0x1000)
                t.emit("csrw 0x34B, x7  // mtval2 = 0x1000")
                lab = twin(t, mode, k, "mtval2 preset 0x1000")
                logw(t, "x15", "TRAPLOG_TVAL")
                if MUT == "htval_eq_tval" and k.va:
                    t.emit("srli x14, x15, 2")
                    logw(t, "x15", "TRAPLOG_TVAL2")
                    t.emit("xor x15, x15, x14")
                    t.check("x15", 0, lab, f"{k.name} from {mode}: mtval2 = mtval >> 2")
                else:
                    logchk(
                        t, "TRAPLOG_TVAL2", X((1 << 32) - 1, (1 << 64) - 1), 0, lab, f"{k.name} from {mode}: mtval2 = 0"
                    )

        guard(t, k.cond, body)
    tests.append(t)
    return tests


def mret_m_case(t: TestFile) -> None:
    """MRET with MPP=3 and MPV=1 (in M-mode): stays in M-mode, MPV cleared."""
    lab = t.label("mret3")
    t.comment("MRET with MPP=3, MPV=1")
    t.emit(f"LA(x7, {lab})", 2)
    t.emit("csrw mepc, x7")
    t.li("x7", MPP)
    t.emit("csrs mstatus, x7  // MPP = 3")
    with t.rv64_only():
        t.li("x7", 1)
        t.emit("slli x7, x7, 39")
        t.emit("csrs mstatus, x7  // MPV = 1")
    with t.rv32_only():
        t.li("x7", 0x80)
        t.emit("csrs 0x310, x7  // mstatush.MPV = 1")
    exp = "VS" if MUT == "mret_mpp3_honors_mpv" else "M"
    t.allow(1)
    t.emit("mret")
    t.emit(f"{lab}:", 0)
    t.emit("csrr x7, mscratch")
    t.comment("MPV right after the MRET lands, before any further trap rewrites it")
    with t.rv64_only():
        t.emit("csrr x8, mstatus")
        t.emit("srli x8, x8, 39")
    with t.rv32_only():
        t.emit("csrr x8, 0x310")
        t.emit("srli x8, x8, 7")
    t.emit("andi x8, x8, 1")
    t.emit("RVTEST_TSBI_GOTO_MMODE", 120)
    t.outcome(
        "ok" if exp == "M" else 2,
        lab,
        "MRET with MPP=3, MPV=1: an mscratch read (M-mode only)",
        [0, (0x340 << 20) | (2 << 12) | (7 << 7) | 0x73],
        origin=exp,
    )
    t.check("x8", 0, lab, "MRET leaves MPV = 0")


# ---------------------------------------------------------------- SRET and MRET
REVEAL = {  # instruction that shows the mode: (line, encoding, {mode: outcome})
    "hstatus": (
        "csrr x7, 0x600  // hstatus",
        (0x600 << 20) | (2 << 12) | (7 << 7) | 0x73,
        {"M": "ok", "S": "ok", "VS": 22, "VU": 22, "U": 2},
    ),
    "mscratch": (
        "csrr x7, mscratch",
        (0x340 << 20) | (2 << 12) | (7 << 7) | 0x73,
        {"M": "ok", "S": 2, "VS": 2, "VU": 2, "U": 2},
    ),
}


def landing(t: TestFile, mode: str, reveal: str, lab: str, desc: str) -> None:
    """After an xRET landed at `lab` (in a window opened by the caller): the reveal instruction must give the
    outcome for `mode`, with origin `mode`."""
    line, enc, outs = REVEAL[reveal]
    o = outs[mode]
    t.outcome(
        o,
        lab,
        f"{desc}: {line.split('//')[0].strip()} shows the mode",
        None if o == "ok" else [0, enc],
        origin=None if o == "ok" else mode,
    )


def gen_xret() -> list[TestFile]:
    tests = []

    def sret_from_hs(t: TestFile, spv: int, spp: int, spie: int, desc: str) -> str:
        """In HS-mode: set SPV/SPP/SPIE, sepc = landing, sret; land and run the hstatus reveal; return to HS."""
        mode = {(1, 1): "VS", (1, 0): "VU", (0, 1): "S", (0, 0): "U"}[(spv, spp)]
        lab = t.label(f"sret_{mode}")
        t.comment(f"{desc}: SRET with hstatus.SPV={spv}, sstatus.SPP={spp}, SPIE={spie} -> {mode}")
        t.allow(1)
        t.emit(f"LA(x7, {lab})", 2)
        t.emit("csrw sepc, x7")
        hs_bits(t, "hstatus", SPV, bool(spv), f"hstatus.SPV = {spv}")
        hs_bits(t, "sstatus", SPP, bool(spp), f"sstatus.SPP = {spp}")
        hs_bits(t, "sstatus", SPIE, bool(spie), f"sstatus.SPIE = {spie}")
        hs_bits(t, "sstatus", SIE, not spie, f"sstatus.SIE = {1 - spie}")
        t.emit("sret")
        t.emit(f"{lab}:", 0)
        t.emit(REVEAL["hstatus"][0])
        if mode == "S":
            t.emit("csrr x8, sstatus  // right after the SRET")
            t.emit("csrr x9, 0x600  // hstatus right after the SRET")
        else:
            t.leave()
        landing(t, mode, "hstatus", lab, desc)
        return lab

    # ---- hstatus_spv_sret ----
    t = new("hstatus_spv_sret")
    t.describe(
        source=HYP,
        rule_text="When an SRET instruction is executed when V=0, V is set to SPV.",
        context="The mode SRET enters is shown by an hstatus read at the landing address: it succeeds in HS-mode, "
        "raises virtual-instruction from VS and VU (origin recorded by hstatus.SPV/sstatus.SPP of the trap) and "
        "illegal-instruction from U-mode.",
        plan="1. In HS-mode, SRET with (SPV, SPP) = (1, 1), (1, 0), (0, 1), (0, 0) lands in VS, VU, HS and U.\n"
        "2. Each twice, with SPIE 0 and 1.",
    )
    for spie in (0, 1):
        for spv, spp in ((1, 1), (1, 0), (0, 1), (0, 0)):
            sret_from_hs(t, spv, spp, spie, "V=0")
    tests.append(t)

    # ---- sret_v0 ----
    t = new("sret_v0")
    t.describe(
        source=HYP,
        rule_text="When executed in M-mode or HS-mode (i.e., V=0), SRET first determines what the new privilege "
        "mode will be according to the values in hstatus.SPV and sstatus.SPP, as encoded in <<h-spp>>. SRET then "
        "sets hstatus.SPV=0, and in sstatus sets SPP=0, SIE=SPIE, and SPIE=1. Lastly, SRET sets the privilege mode "
        "as previously determined, and sets pc=sepc.",
        context="This file executes SRET in HS-mode. The field updates are visible directly when SRET returns to "
        "HS-mode; after a return to VS, VU or U the next trap into HS-mode rewrites them, so sret_v0_Sm checks "
        "those from M-mode, and also SRET executed in M-mode.",
        plan="1. SRET from HS-mode to each of VS, VU, HS and U (landing shown by an hstatus read; pc = sepc).\n"
        "2. Returning to HS-mode (SPV=0, SPP=1) with SPIE = 0 and 1: right after the SRET, hstatus.SPV = 0, "
        "sstatus.SPP = 0, SIE = old SPIE, SPIE = 1.",
    )
    for spie in (0, 1):
        lab = sret_from_hs(t, 0, 1, spie, f"SPIE={spie}")
        t.check_masked(
            "x8",
            SPP | SIE | SPIE,
            SPIE | (SIE * spie),
            lab,
            f"SRET to HS-mode with SPIE={spie}: SPP=0, SIE={spie}, SPIE=1",
            tmp="x5",
        )
        t.check_masked("x9", SPV, 0, lab, "SRET leaves hstatus.SPV = 0", tmp="x5")
    for spv, spp in ((1, 1), (1, 0), (0, 0)):
        sret_from_hs(t, spv, spp, 1, "landing")
    hs_bits(t, "sstatus", SIE, False, "sstatus.SIE = 0")
    tests.append(t)

    # ---- sret_v0_Sm ----
    t = new("sret_v0", ["I", "S", "H", "Sm"], boot="M", suffix="_Sm")
    t.describe(
        source=HYP,
        rule_text="When executed in M-mode or HS-mode (i.e., V=0), SRET first determines what the new privilege "
        "mode will be according to the values in hstatus.SPV and sstatus.SPP, as encoded in <<h-spp>>. SRET then "
        "sets hstatus.SPV=0, and in sstatus sets SPP=0, SIE=SPIE, and SPIE=1. Lastly, SRET sets the privilege mode "
        "as previously determined, and sets pc=sepc.",
        context="M-mode part. medeleg = 0, so the hstatus read that shows the landing mode and the GOTO_MMODE that "
        "ends the excursion trap straight to M-mode and leave the HS-level fields as SRET left them.",
        plan="1. From HS-mode (entered with T-SBI GOTO_SMODE), SRET with SPV=1 to VS and to VU, and with SPV=0 to U: "
        "M-mode then reads hstatus.SPV = 0, sstatus.SPP = 0, SIE = old SPIE, SPIE = 1.\n"
        "2. SRET executed in M-mode with SPV=1, SPP=1 enters VS-mode.",
    )
    for spv, spp, spie in ((1, 1, 0), (1, 0, 1), (0, 0, 0), (1, 1, 1)):
        mode = {(1, 1): "VS", (1, 0): "VU", (0, 0): "U"}[(spv, spp)]
        lab = t.label(f"sret_{mode}")
        t.allow(1)
        t.emit("RVTEST_TSBI_GOTO_SMODE", 120)
        t.emit(f"LA(x7, {lab})", 2)
        t.emit("csrw sepc, x7")
        hs_bits(t, "hstatus", SPV, bool(spv))
        hs_bits(t, "sstatus", SPP, bool(spp))
        hs_bits(t, "sstatus", SPIE, bool(spie))
        hs_bits(t, "sstatus", SIE, not spie)
        t.emit("sret")
        t.emit(f"{lab}:", 0)
        t.emit(REVEAL["hstatus"][0])
        t.emit("RVTEST_TSBI_GOTO_MMODE", 120)
        landing(t, mode, "hstatus", lab, f"SRET from HS-mode, SPV={spv}, SPP={spp}")
        t.emit("csrr x8, 0x600")
        t.check_masked(
            "x8", SPV, SPV if MUT == "sret_keeps_spv" and spv else 0, lab, "SRET leaves hstatus.SPV = 0", tmp="x5"
        )
        t.emit("csrr x8, sstatus")
        t.check_masked(
            "x8",
            SPP | SIE | SPIE,
            SPIE | (SIE * spie),
            lab,
            f"SRET with SPIE={spie}: SPP=0, SIE={spie}, SPIE=1",
            tmp="x5",
        )
    # SRET in M-mode
    lab = t.label("msret")
    t.allow(1)
    t.emit(f"LA(x7, {lab})", 2)
    t.emit("csrw sepc, x7")
    hs_bits(t, "hstatus", SPV, True)
    hs_bits(t, "sstatus", SPP, True)
    t.emit("sret")
    t.emit(f"{lab}:", 0)
    t.emit(REVEAL["hstatus"][0])
    t.emit("RVTEST_TSBI_GOTO_MMODE", 120)
    landing(t, "VS", "hstatus", lab, "SRET in M-mode with SPV=1, SPP=1")
    tests.append(t)

    # ---- sret_v1 ----
    t = new("sret_v1", suffix="_mode")
    t.describe(
        source=HYP,
        rule_text="When executed in VS-mode (i.e., V=1), SRET sets the privilege mode according to <<h-vspp>>, in "
        "vsstatus sets SPP=0, SIE=SPIE, and SPIE=1, and lastly sets pc=vsepc.",
        context="hstatus.VTSR=0. The HS-level sstatus.SPP and hstatus.SPV are 0 while the guest runs (the SRET that "
        "entered VS-mode cleared them), so an SRET that wrongly used them would leave the guest for U-mode. A "
        "counter at the VS entry point catches an SRET that jumps to sepc (the entry point) instead of vsepc.",
        plan="1. In VS-mode: vsepc = landing (written through sepc), vsstatus.SPP = 1, SPIE = 0/1: SRET lands in "
        "VS-mode (an sscratch read succeeds; an hstatus read raises virtual-instruction from VS), and vsstatus "
        "reads SPP=0, SIE=old SPIE, SPIE=1.\n"
        "2. vsstatus.SPP = 0: SRET lands in VU-mode (the hstatus read raises virtual-instruction from VU); "
        "HS-mode then reads vsstatus SPP=0, SIE=old SPIE, SPIE=1.",
    )
    for spp, spie in ((1, 0), (1, 1), (0, 1), (0, 0)):
        mode = "VS" if spp else "VU"
        if MUT == "sret_v1_uses_hs_spp":
            mode = "VU"
        lab = t.label(f"vsret_{'VS' if spp else 'VU'}")
        guard_lab, skip = t.label("entered"), t.label("skip")
        t.emit("li x9, 0")
        t.allow(1)
        t.enter("VS")
        t.emit(f"{guard_lab}:", 0)
        t.emit("addi x9, x9, 1")
        t.emit("li x5, 1")
        t.emit(f"bne x9, x5, {skip}  // re-entered: the SRET jumped to sepc")
        t.emit(f"LA(x7, {lab})", 2)
        t.emit("csrw sepc, x7  // vsepc")
        t.li("x7", SPP)
        t.emit(f"{'csrs' if spp else 'csrc'} sstatus, x7  // vsstatus.SPP = {spp}")
        t.li("x7", SPIE)
        t.emit(f"{'csrs' if spie else 'csrc'} sstatus, x7  // vsstatus.SPIE = {spie}")
        t.li("x7", SIE)
        t.emit(f"{'csrc' if spie else 'csrs'} sstatus, x7  // vsstatus.SIE = {1 - spie}")
        t.emit("sret")
        t.emit(f"{lab}:", 0)
        t.emit(REVEAL["hstatus"][0])
        t.emit(f"{skip}:", 0)
        t.leave()
        landing(t, mode, "hstatus", lab, f"SRET in VS-mode with vsstatus.SPP={spp}")
        t.check("x9", 1, lab, "the VS entry point ran once (SRET went to vsepc, not sepc)")
        t.emit("csrr x8, 0x200  // vsstatus")
        t.check_masked(
            "x8",
            SPP | SIE | SPIE,
            SPIE | (SIE * spie),
            lab,
            f"SRET in VS-mode with SPIE={spie}: vsstatus SPP=0, SIE={spie}, SPIE=1",
            tmp="x5",
        )
    tests.append(t)

    # ---- sret_H ----
    t = new("sret_H")
    t.describe(
        source=HYP,
        rule_text="The SRET instruction is used to return from a trap taken into HS-mode or VS-mode. Its behavior "
        "depends on the current virtualization mode.",
        context="sret_v0 and sret_v1 check each mode in detail. Here a trap into each of HS-mode and VS-mode is "
        "returned from by an SRET in that mode.",
        plan="1. An ebreak in VS-mode delegated to VS-mode (hedeleg[3]=1): the VS handler's SRET returns to VS-mode "
        "after the ebreak, so the next instruction (an hstatus read) raises virtual-instruction from VS-mode.\n"
        "2. An ebreak in VU-mode taken in HS-mode: the HS handler's SRET returns to VU-mode (V=SPV=1, SPP=0), so "
        "the next hstatus read raises virtual-instruction from VU-mode.",
    )
    bare(t)
    for mode, hd in (("VS", 8), ("VU", 0)):
        t.li("x7", hd)
        t.emit("csrw 0x602, x7  // hedeleg")
        lab = t.label(f"ret_{mode}")
        lab2 = t.label("after")
        t.allow(2)
        t.enter(mode)
        t.emit(f"{lab}:", 0)
        t.emit(f".word {hex(EBREAK)}  // ebreak")
        t.emit(f"{lab2}:", 0)
        t.emit(REVEAL["hstatus"][0])
        t.leave()
        t.emit("AI_OUTCOME", 20)
        t.check("x13", 2, lab, f"ebreak then hstatus read in {mode}-mode: two traps")
        handler_is(t, "VS" if hd else "S", lab, f"ebreak in {mode}-mode", back=1)
        t.emit("AI_ORIGIN", 25)
        t.check(
            "x15",
            5 if mode == "VS" else 4,
            lab2,
            f"after the {'VS' if hd else 'HS'} handler's SRET, the hstatus read comes from {mode}-mode",
        )
    t.emit("csrw 0x602, x0")
    tests.append(t)

    # ---- mret_H_Sm ----
    t = new("mret_H", ["I", "S", "H", "Sm"], boot="M", suffix="_Sm")
    t.describe(
        source=HYP,
        rule_text="The MRET instruction is used to return from a trap taken into M-mode. MRET first determines what "
        "the new privilege mode will be according to the values of MPP and MPV in mstatus or mstatush, as encoded "
        "in <<h-mpp>>. MRET then in mstatus/mstatush sets MPV=0, MPP=0, MIE=MPIE, and MPIE=1. Lastly, MRET sets "
        "the privilege mode as previously determined, and sets pc=mepc.",
        context="The test boots to M-mode (medeleg = 0). The landing mode is shown by an mscratch read (succeeds "
        "only in M-mode) or an hstatus read (succeeds in M and HS, virtual-instruction from VS/VU, illegal from "
        "U); the trap's mstatus.MPP/MPV record where it came from. MPP=0 is U-mode, the least-privileged mode.",
        plan="1. MRET with (MPV, MPP) = (1, 1) lands in VS-mode, (1, 0) in VU-mode, (0, 1) in HS-mode, (0, 0) in "
        "U-mode, and (1, 3) and (0, 3) stay in M-mode; pc = mepc in each case.\n"
        "2. After MRET to M-mode with MPIE = 0 and 1: MPV = 0, MPP = 0, MIE = old MPIE, MPIE = 1.",
    )
    for mpv, mpp in ((1, 1), (1, 0), (0, 1), (0, 0), (1, 3), (0, 3)):
        mode = {(1, 1): "VS", (1, 0): "VU", (0, 1): "S", (0, 0): "U"}.get((mpv, mpp), "M")
        if MUT == "mret_mpp3_honors_mpv" and (mpv, mpp) == (1, 3):
            mode = "VS"
        for mpie in (0, 1) if mpp == 3 else (1,):
            lab = t.label(f"mret_{mode}")
            t.allow(1)
            t.emit(f"LA(x7, {lab})", 2)
            t.emit("csrw mepc, x7")
            t.li("x7", MPP)
            t.emit("csrc mstatus, x7")
            t.li("x7", mpp << 11)
            t.emit("csrs mstatus, x7  // MPP")
            t.li("x7", MPIE)
            t.emit(f"{'csrs' if mpie else 'csrc'} mstatus, x7  // MPIE = {mpie}")
            t.li("x7", MIE)
            t.emit(f"{'csrc' if mpie else 'csrs'} mstatus, x7  // MIE = {1 - mpie}")
            with t.rv64_only():
                t.li("x7", 1)
                t.emit("slli x7, x7, 39")
                t.emit(f"{'csrs' if mpv else 'csrc'} mstatus, x7  // MPV = {mpv}")
            with t.rv32_only():
                t.li("x7", 0x80)
                t.emit(f"{'csrs' if mpv else 'csrc'} 0x310, x7  // mstatush.MPV = {mpv}")
            t.emit("mret")
            t.emit(f"{lab}:", 0)
            reveal = "mscratch" if mode in ("M", "S") else "hstatus"
            t.emit(REVEAL[reveal][0])
            if mode == "M":
                t.emit("csrr x8, mstatus  // right after the MRET")
                with t.rv64_only():
                    t.emit("mv x9, x8")
                with t.rv32_only():
                    t.emit("csrr x9, 0x310")
            else:
                t.emit("RVTEST_TSBI_GOTO_MMODE", 120)
            landing(t, mode, reveal, lab, f"MRET with MPV={mpv}, MPP={mpp}")
            if mode == "M" and mpp == 3:
                t.check_masked(
                    "x8",
                    MPP | MIE | MPIE,
                    MPIE | (MIE * mpie),
                    lab,
                    f"MRET with MPIE={mpie}: MPP=0, MIE={mpie}, MPIE=1",
                    tmp="x5",
                )
                t.check_masked("x9", X(0x80, 1 << 39), 0, lab, "MRET leaves MPV = 0", tmp="x5")
    t.li("x7", MIE)
    t.emit("csrc mstatus, x7")
    tests.append(t)
    return tests


# ---------------------------------------------------------------- htval / htinst
def tinst_struct(t: TestFile, lab: str, desc: str) -> None:
    """Logged xtinst is 0, or has bits 1:0 = 11 (a transformed 32-bit standard instruction), and on RV64
    bits 63:32 = 0."""
    logw(t, "x15", "TRAPLOG_TINST")
    t.emit("seqz x14, x15")
    t.emit("andi x5, x15, 3")
    t.emit("addi x5, x5, -3")
    t.emit("seqz x5, x5")
    with t.rv64_only():
        t.emit("srli x15, x15, 32")
        t.emit("seqz x15, x15")
        t.emit("and x5, x5, x15")
    t.emit("or x5, x5, x14")
    t.check_bool("x5", lab, f"{desc}: xtinst is 0 or a 32-bit standard encoding (bits 1:0 = 11, 63:32 = 0)")


def gen_tval2_tinst() -> list[TestFile]:
    tests = []
    K = kinds()
    names = ("ebreak", "illegal", "virtual", "ecall", "load", "store", "fetch", "hlv", "hsv")
    full = X((1 << 32) - 1, (1 << 64) - 1)

    def sweep(t: TestFile, fn: Callable[[Kind, str, str, str], object]) -> None:
        for name in names:
            k = K[name]

            def body(k: Kind = k) -> None:
                for mode in k.modes:
                    if mode == "M":
                        continue
                    w = where(mode, k.cause(mode), 0)
                    lab = twin(t, mode, k, f"to {w}")
                    fn(k, mode, w, lab)

            guard(t, k.cond, body)

    # ---- htval_trapval ----
    t = new("htval_trapval")
    t.describe(
        source=HYP,
        rule_text="When a guest-page-fault trap is taken into HS-mode, htval is written with either zero or the "
        "guest physical address that faulted, shifted right by 2 bits. For other traps, htval is set to zero, but a "
        "future standard or extension may redefine htval's setting for other traps.",
        context="Guest-page faults are covered by the translation tests. htval is WARL; before each trap the test "
        "writes 0x1000 to it, so a trap that leaves htval unwritten is caught on harts where it holds that value.",
        plan="1. ebreak, illegal, virtual-instruction, ecall, load/store/fetch access faults (HS, U, VS, VU) and "
        "HLV/HSV access faults (HS): htval = 0 on HS handler entry (ecall from HS-mode goes to M-mode and checks "
        "mtval2 instead).",
    )
    bare(t)

    def chk_tval2(k: Kind, mode: str, w: str, lab: str) -> None:
        if MUT == "htval_eq_tval" and k.va:
            logw(t, "x14", "TRAPLOG_TVAL")
            t.emit("srli x14, x14, 2")
            logw(t, "x15", "TRAPLOG_TVAL2")
            t.emit("xor x15, x15, x14")
            t.check("x15", 0, lab, f"{k.name} from {mode}: htval = stval >> 2")
        else:
            logchk(t, "TRAPLOG_TVAL2", full, 0, lab, f"{k.name} from {mode}: {'htval' if w == 'S' else 'mtval2'} = 0")
        t.li("x7", 0x1000)
        t.emit("csrw 0x643, x7  // htval = 0x1000 before the next trap")

    t.li("x7", 0x1000)
    t.emit("csrw 0x643, x7  // htval = 0x1000")
    sweep(t, chk_tval2)
    tests.append(t)

    # ---- mtval2_trapval (S-boot) ----
    t = new("mtval2_trapval")
    t.describe(
        source=HYP,
        rule_text="When a guest-page-fault trap is taken into M-mode, mtval2 is written with either zero or the "
        "guest physical address that faulted, shifted right by 2 bits. For other traps, mtval2 is set to zero, but "
        "a future standard or extension may redefine mtval2's setting for other traps.",
        context="Without changing medeleg, the trap from below M into M-mode is ecall from HS-mode; "
        "mtval2_trapval_Sm covers every trap kind.",
        plan="1. After HLV and load access faults taken in HS-mode, ecall from HS-mode: mtval2 = 0 in M-mode.",
    )
    bare(t)
    for name in ("hlv", "load"):
        with t.only_if(HAS_LD):
            twin(t, "S", K[name], "taken in HS-mode")
        lab = twin(t, "S", K["ecall"], "ecall into M-mode")
        logchk(t, "TRAPLOG_TVAL2", full, 0, lab, "ecall from HS-mode: mtval2 = 0")
    tests.append(t)

    # ---- H_trap_xtinst_val ----
    t = new("H_trap_xtinst_val")
    t.describe(
        source=HYP,
        rule_text="<<tinst-values>> shows the values that may be automatically written to the trap instruction "
        "register for each standard exception cause. For exceptions that prevent the fetching of an instruction, "
        "only zero or a pseudoinstruction value may be written. A custom value may be automatically written only if "
        "the instruction that traps is non-standard.",
        context="Table tinst-values, for standard instructions (no custom values): instruction access fault, "
        "illegal instruction, breakpoint, virtual instruction and environment call: zero only; load and store access "
        "faults: zero or the transformed instruction. The transformed lw x7, 8(x6) is 0x00002383 and sw x7, 8(x6) "
        "is 0x00702023 (immediate zeroed, rs1 replaced by the address offset 0); the transformed HLV.W/HSV.W keeps "
        "every field except rs1 (offset 0).",
        plan="1. Each trap kind from HS, U, VS and VU (HLV/HSV from HS): htinst on HS handler entry, or mtinst for "
        "ecall from HS-mode, is one of the values the table allows.",
    )
    bare(t)
    sweep(
        t,
        lambda k, mode, w, lab: logchk(
            t,
            "TRAPLOG_TINST",
            full,
            k.tinst,
            lab,
            f"{k.name} from {mode}: xtinst is one of {[hex(v) for v in k.tinst]}",
        ),
    )
    tests.append(t)

    # ---- H_trap_xtinst ----
    t = new("H_trap_xtinst")
    t.describe(
        source=HYP,
        rule_text="On any trap into M-mode or HS-mode, one of these values is written automatically into the "
        "appropriate trap instruction CSR, mtinst or htinst: zero; a transformation of the trapping instruction; a "
        "custom value (allowed only if the trapping instruction is non-standard); or a special pseudoinstruction.",
        context="All trapping instructions here are standard, and pseudoinstructions arise only for guest-page "
        "faults, so the legal values are zero and the transformation. The test presets htinst to a value it may "
        "hold (the transformed HLV.W) before each trap, so a trap that leaves htinst unwritten is caught.",
        plan="1. Before each trap, HS-mode writes htinst = the transformed HLV.W. Each trap kind into HS-mode (and "
        "ecall from HS-mode into M-mode): xtinst is 0 or the transformed instruction, never the stale value (for "
        "kinds other than HLV.W).",
    )
    bare(t)

    def chk_written(k: Kind, mode: str, w: str, lab: str) -> None:
        logchk(t, "TRAPLOG_TINST", full, k.tinst, lab, f"{k.name} from {mode}: xtinst written (0 or transformed)")
        t.load("x7", T_HLVW, "transformed HLV.W")
        t.emit("csrw 0x64A, x7  // htinst = stale value")

    t.load("x7", T_HLVW, "transformed HLV.W")
    t.emit("csrw 0x64A, x7  // htinst = stale value")
    sweep(t, chk_written)
    tests.append(t)

    # ---- H_trap_xtinst_exception_lead_in ----
    t = new("H_trap_xtinst_exception_lead_in")
    t.describe(
        source=HYP,
        rule_text="On a synchronous exception, if a nonzero value is written, one of the following shall be true "
        "about the value:",
        context="The cases are listed in H_trap_xtinst_exception_list. For a standard 32-bit instruction that is "
        "not a guest-page fault, a nonzero value must therefore have bits 1:0 = 11, and on RV64 bits 63:32 = 0.",
        plan="1. Each trap kind from HS, U, VS and VU: xtinst is 0 or has bits 1:0 = 11 and bits 63:32 = 0.",
    )
    bare(t)
    sweep(t, lambda k, mode, w, lab: tinst_struct(t, lab, f"{k.name} from {mode}"))
    tests.append(t)

    # ---- H_trap_xtinst_exception_list ----
    t = new("H_trap_xtinst_exception_list")
    t.describe(
        source=HYP,
        rule_text="Bit 0 is 1, and replacing bit 1 with 1 makes the value into a valid encoding of a standard "
        "instruction. In this case, the instruction that trapped is the same kind as indicated by the register "
        "value, and the register value is the transformation of the trapping instruction, as defined later. ... "
        "Bit 0 is 1, and replacing bit 1 with 1 makes the value into an instruction encoding that is explicitly "
        "designated for a custom instruction ... The value is one of the special pseudoinstructions defined later, "
        "all of which have bits 1:0 equal to 00.",
        context="The trapping instructions are standard and none of the traps is a guest-page fault, so a nonzero "
        "value must be a standard encoding of the same kind (a load for a load, and so on), and its exact form is the "
        "transformation.",
        plan="1. Load and store access faults (lw, sw) and HLV.W/HSV.W access faults: xtinst is 0 or has the "
        "trapping instruction's opcode and funct3 (bits 14:12, 6:0) with bits 1:0 = 11, and equals the transformed "
        "value.\n"
        "2. ebreak, illegal, virtual-instruction and ecall: xtinst = 0 (no transformation is defined for them).",
    )
    bare(t)

    def kind_match(k: Kind, mode: str, w: str, lab: str) -> None:
        if len(k.tinst) > 1:
            logw(t, "x15", "TRAPLOG_TINST")
            t.emit("seqz x14, x15")
            t.load("x5", 0x707F, "opcode | funct3 mask")
            t.emit("and x15, x15, x5")
            t.load("x5", k.tinst[1] & 0x707F, "expected opcode | funct3")
            t.emit("xor x15, x15, x5")
            t.emit("seqz x15, x15")
            t.emit("or x5, x15, x14")
            t.check_bool("x5", lab, f"{k.name} from {mode}: xtinst is 0 or the same kind of instruction")
        logchk(t, "TRAPLOG_TINST", full, k.tinst, lab, f"{k.name} from {mode}: xtinst value")

    sweep(t, kind_match)
    tests.append(t)

    # ---- H_tinst_addr_offset ----
    t = new("H_tinst_addr_offset")
    t.describe(
        source=HYP,
        rule_text="In all the transformed instructions above, the Addr. Offset field that replaces the instruction's "
        "rs1 field in bits 19:15 is the positive difference between the faulting virtual address (written to mtval "
        "or stval) and the original virtual address. This difference can be nonzero only for a misaligned memory "
        "access.",
        context="Misaligned LR.W and SC.W always trap (address-misaligned or access fault) with A or Zalrsc; the "
        "transformed atomic keeps every field except rs1. LR/SC are single accesses that are never split, so the "
        "faulting virtual address is the original address and the offset is 0 (xtval may also be 0, which carries "
        "no address). Aligned load and store access faults have offset 0 too. A nonzero offset needs a split "
        "misaligned access whose second part faults, which is not forced here.",
        plan="1. lw x7, 8(x6) and sw x7, 8(x6) access faults from HS and VS: xtinst is 0 or has offset 0 (and a zero "
        "immediate).\n"
        "2. LR.W and SC.W at a 4-byte-aligned address + 1, from HS, VS and VU: xtinst is 0 or the transformed "
        "instruction with offset 0.",
    )
    bare(t)
    for name in ("load", "store"):
        cond = K[name].cond
        with t.only_if(cond) if cond else nullcontext():
            for mode in ("S", "VS"):
                lab = twin(t, mode, K[name], "aligned")
                logchk(t, "TRAPLOG_TINST", full, K[name].tinst, lab, f"{K[name].name} from {mode}: offset 0")
    with t.only_if(HAS_A):
        data, skip = t.label("data"), t.label("skip")
        t.emit(f"j {skip}")
        t.emit(".p2align 3", 0)
        t.emit(f"{data}:", 0)
        t.emit(".dword 0, 0", 0)
        t.emit(f"{skip}:", 0)
        for enc, nm, causes in ((LRW, "LR.W", [4, 5]), (SCW, "SC.W", [6, 7])):
            for mode in ("S", "VS", "VU"):
                lab = t.label(f"lr_{mode}")
                t.emit(f"LA(x6, {data}+1)", 2)
                t.emit("li x7, 0")
                t.allow(1)
                enter(t, mode)
                t.emit(f"{lab}:", 0)
                t.emit(f".word {hex(enc)}  // {nm.lower()} (x6 = aligned + 1)")
                leave(t, mode)
                t.outcome(causes, lab, f"{nm} misaligned in {mode}-mode", [0, f"{data}+1"], origin=mode)
                t0 = enc & ~(0x1F << 15)
                legal = [t0 | (1 << 15)] if MUT == "lr_offset_nonzero" else [0, t0]
                logchk(
                    t,
                    "TRAPLOG_TINST",
                    full,
                    legal,
                    lab,
                    f"{nm} misaligned in {mode}-mode: xtinst is 0 or the "
                    "transformed instruction with Addr. Offset 0 (a single access faults at its own address)",
                )
    tests.append(t)

    # ---- H_trans_cache ----
    t = new("H_trans_cache")
    t.describe(
        source=HYP,
        rule_text="For a standard cache-block management instruction (CBO.CLEAN, CBO.FLUSH, or CBO.INVAL) or "
        "cache-block zero instruction (CBO.ZERO), the transformed instruction has the format shown in "
        "<<transformedcboinst>>. The operation field corresponds to the 12 most significant bits of the trapping "
        "instruction.",
        context="Format: operation (bits 31:20), 0 in bits 19:15, funct3, 0 in bits 11:7, opcode. CBO.ZERO at the "
        "DUT's access-fault address raises a store/AMO access fault (cause 7) with vsatp and hgatp Bare; htinst is "
        "0 or the transformed CBO.ZERO 0x0040200F. The framework enables CBO.ZERO for S/HS (menvcfg.CBZE) and for "
        "VS (henvcfg.CBZE).",
        plan="1. With Zicboz: CBO.ZERO (x6 = the access-fault address) in HS-mode and in VS-mode: store access fault "
        "taken in HS-mode, htinst = 0 or 0x0040200F.",
    )
    bare(t)
    with t.only_if(f"defined(ZICBOZ_SUPPORTED) && {HAS_ST}"):
        k = Kind(
            "CBO.ZERO access fault",
            [f"LI(x6, {FA_ST})"],
            [f".word {hex(CBO_ZERO)}  // cbo.zero (x6)"],
            lambda m: 7,
            [0, FA_ST],
            [0, T_CBO_ZERO],
            True,
            modes=("S", "VS"),
        )
        for mode in ("S", "VS"):
            lab = twin(t, mode, k, "CBO.ZERO at the access-fault address")
            logchk(
                t,
                "TRAPLOG_TINST",
                full,
                [0, T_CBO_ZERO | (6 << 15)] if MUT == "tinst_imm_kept" else k.tinst,
                lab,
                f"CBO.ZERO from {mode}: htinst is 0 or the transformed CBO.ZERO",
            )
    tests.append(t)

    # ---- H_trap_xtinst_interrupt ----
    t = new("H_trap_xtinst_interrupt")
    t.describe(
        source=HYP,
        rule_text="On an interrupt, the value written to the trap instruction register is always zero.",
        context="The trap log does not record xtinst for interrupts, so the test reads htinst right after the "
        "interrupt, with no other trap in between. htinst first gets a nonzero value it can hold: the test writes the "
        "transformed HLV.W and reads it back; if the hart cannot hold it, an HLV access fault is taken first, which "
        "may leave that value. The interrupt is a supervisor software interrupt taken in HS-mode (sip.SSIP with "
        "sie.SSIE and sstatus.SIE).",
        plan="1. htinst = nonzero (written, or from an HLV fault). If it reads nonzero, take an SSI in HS-mode: "
        "htinst then reads 0.\n"
        "2. M-mode part in H_trap_xtinst_interrupt_Sm (mtinst).",
    )
    bare(t)
    with t.only_if(HAS_LD):
        twin(t, "S", K["hlv"], "an HLV fault may write a nonzero htinst")
    t.load("x7", T_HLVW, "transformed HLV.W")
    t.emit("csrr x1, 0x64A")
    t.emit("bnez x1, 1f")
    t.emit("csrw 0x64A, x7  // htinst")
    t.emit("csrr x1, 0x64A")
    t.emit("1:", 0)

    def ssi() -> None:
        lab = t.label("ssi")
        t.li("x7", SIE)
        t.emit("csrc sstatus, x7")
        t.li("x7", 2)
        t.emit("csrs sie, x7  // SSIE")
        t.emit("csrs sip, x7  // SSIP")
        t.allow(1)
        t.emit(f"{lab}:", 0)
        t.li("x7", SIE)
        t.emit("csrs sstatus, x7  // SIE = 1: take the SSI")
        t.emit("nop")
        t.emit("nop")
        t.emit("csrr x8, 0x64A  // htinst right after the interrupt")
        t.li("x7", SIE)
        t.emit("csrc sstatus, x7")
        t.li("x7", 2)
        t.emit("csrc sip, x7")
        t.emit("csrc sie, x7")
        t.outcome(X((1 << 31) | 1, (1 << 63) | 1), lab, "SSI in HS-mode", epc=False, origin="S")
        t.check("x8", T_HLVW if MUT == "tinst_interrupt_kept" else 0, lab, "htinst = 0 after an interrupt")

    t.either("x1", ssi, lambda: t.comment("htinst holds no nonzero value: nothing to check"))
    tests.append(t)

    # ---- H_trap_xtinst_interrupt_Sm ----
    t = new("H_trap_xtinst_interrupt", ["I", "S", "H", "Sm"], boot="M", suffix="_Sm")
    t.describe(
        source=HYP,
        rule_text="On an interrupt, the value written to the trap instruction register is always zero.",
        context="M-mode part: a supervisor software interrupt not delegated (mideleg[1] = 0 in an M-mode boot... "
        "the test clears it) is taken in M-mode with mstatus.MIE and mie.SSIE set. mtinst first gets a nonzero "
        "value it can hold (written, or from an HLV access fault taken in M-mode).",
        plan="1. mtinst = nonzero. If it reads nonzero, take an SSI in M-mode: mtinst then reads 0.",
    )
    bare(t)
    t.li("x7", 2)
    t.emit("csrc mideleg, x7  // SSI not delegated")
    with t.only_if(HAS_LD):
        twin(t, "M", K["hlv"], "an HLV fault may write a nonzero mtinst")
    t.load("x7", T_HLVW, "transformed HLV.W")
    t.emit("csrr x1, 0x34A")
    t.emit("bnez x1, 1f")
    t.emit("csrw 0x34A, x7  // mtinst")
    t.emit("csrr x1, 0x34A")
    t.emit("1:", 0)

    def mssi() -> None:
        lab = t.label("ssi")
        t.li("x7", MIE)
        t.emit("csrc mstatus, x7")
        t.li("x7", 2)
        t.emit("csrs mie, x7  // SSIE")
        t.emit("csrs mip, x7  // SSIP")
        t.allow(1)
        t.emit(f"{lab}:", 0)
        t.li("x7", MIE)
        t.emit("csrs mstatus, x7  // MIE = 1: take the SSI")
        t.emit("nop")
        t.emit("nop")
        t.emit("csrr x8, 0x34A  // mtinst right after the interrupt")
        t.li("x7", MIE)
        t.emit("csrc mstatus, x7")
        t.li("x7", 2)
        t.emit("csrc mip, x7")
        t.emit("csrc mie, x7")
        t.outcome(X((1 << 31) | 1, (1 << 63) | 1), lab, "SSI in M-mode", epc=False, origin="M")
        t.check("x8", T_HLVW if MUT == "tinst_interrupt_kept" else 0, lab, "mtinst = 0 after an interrupt")

    t.either("x1", mssi, lambda: t.comment("mtinst holds no nonzero value: nothing to check"))
    tests.append(t)
    return tests


# ---------------------------------------------------------------- priority, SRET and SDT
def gen_misc() -> list[TestFile]:
    tests = []
    K = kinds()

    # ---- H_exception_priority ----
    t = new("H_exception_priority")
    t.describe(
        source=HYP,
        rule_text="If an instruction raises multiple synchronous exceptions, the decreasing priority order of "
        "<<HSyncExcPrio>> indicates which exception is taken and reported in mcause or scause.",
        context="Table HSyncExcPrio puts illegal (2) and virtual instruction (22) above address-misaligned and "
        "above the access faults of an explicit memory access (5, 7). With vsatp and hgatp Bare, an HLV/HSV whose "
        "address is misaligned or is the DUT's access-fault address, executed where HLV/HSV is not allowed, must "
        "report the instruction exception. Instruction-address breakpoints and translation faults are out of reach "
        "here.",
        plan="1. HLV.W and HSV.W at the access-fault address in VS and VU: virtual-instruction (22), not 5/7.\n"
        "2. The same in U-mode with hstatus.HU=0: illegal-instruction (2).\n"
        "3. HLV.W at an odd address in VS, VU and U (HU=0): 22, 22, 2 (not 4/5).\n"
        "4. Contrast: HLV.W at the access-fault address in U-mode with HU=1 raises the load access fault.",
    )
    bare(t)
    hs_bits(t, "hstatus", 0x200, False, "hstatus.HU = 0")
    with t.only_if(f"{HAS_LD} && {HAS_ST}"):
        for name in ("hlv", "hsv"):
            k = K[name]
            for mode in ("VS", "VU", "U"):
                c = 2 if mode == "U" else 22
                if MUT == "access_over_virtual" and mode == "VU":
                    c = k.cause("S")
                kk = Kind(k.name, k.pre, k.lines, k.cause, [0, hlsv(name + ".w", "x7", "x6", "x7")[1]], [0], False)
                twin(t, mode, kk, "instruction exception over access fault", cause=c)
        hs_bits(t, "hstatus", 0x200, True, "hstatus.HU = 1")
        twin(t, "U", K["hlv"], "HU=1: the access fault is taken")
        hs_bits(t, "hstatus", 0x200, False, "hstatus.HU = 0")
    data, skip = t.label("data"), t.label("skip")
    t.emit(f"j {skip}")
    t.emit(".p2align 3", 0)
    t.emit(f"{data}:", 0)
    t.emit(".dword 0, 0", 0)
    t.emit(f"{skip}:", 0)
    for mode in ("VS", "VU", "U"):
        kk = Kind(
            "HLV.W misaligned",
            [f"LA(x6, {data}+1)"],
            [HLVW],
            lambda m: 2 if m == "U" else 22,
            [0, hlsv("hlv.w", "x7", "x6")[1]],
            [0],
            False,
        )
        twin(t, mode, kk, "instruction exception over misaligned")
    tests.append(t)

    # ---- sret_dt ----
    t = new("sret_dt", ["I", "S", "H", "Ssdbltrp"])
    t.describe(
        source=HYP,
        rule_text="If the Ssdbltrp extension is implemented, when SRET is executed in HS-mode, if the new privilege "
        "mode is VU, the SRET instruction sets vsstatus.SDT to 0. When executed in VS-mode, vsstatus.SDT is set to 0.",
        context="vsstatus.SDT (bit 24) is writable only with menvcfg.DTE=1 and henvcfg.DTE=1 (bit 59, in the high "
        "halves on RV32); the test sets both. SRET from HS-mode into VS-mode is not covered by the sentence and "
        "leaves vsstatus.SDT alone (only an SRET into VU clears it). No trap is taken into VS-mode while SDT=1.",
        plan="1. HS-mode sets vsstatus.SDT=1 and reads it back.\n"
        "2. SRET from HS-mode into VU-mode: HS-mode then reads vsstatus.SDT = 0.\n"
        "3. SDT=1 again, SRET from HS-mode into VS-mode: SDT reads 1 in VS-mode; then an SRET in VS-mode (to "
        "VS-mode, vsstatus.SPP=1) clears it: SDT reads 0 in VS-mode and in HS-mode.\n"
        "4. Restore vsstatus.SDT = 0 and the original menvcfg and henvcfg, so later traps into HS-mode do not set "
        "sstatus.SDT.",
    )
    t.comment("save menvcfg(h) in x1 and henvcfg(h) in x6, then set DTE in both")
    with t.rv64_only():
        t.tsbi_csr("READ", "MENVCFG")
        t.emit("mv x1, a0")
        t.emit("csrr x6, 0x60A  // henvcfg")
    with t.rv32_only():
        t.tsbi_csr("READ", "MENVCFGH")
        t.emit("mv x1, a0")
        t.emit("csrr x6, 0x61A  // henvcfgh")
    with t.rv64_only():
        t.li("a1", 1)
        t.emit("slli a1, a1, 59")
        t.tsbi_csr("SET", "MENVCFG", "a1")
        t.emit("csrs 0x60A, a1  // henvcfg.DTE")
    with t.rv32_only():
        t.li("a1", 1 << 27)
        t.tsbi_csr("SET", "MENVCFGH", "a1")
        t.emit("csrs 0x61A, a1  // henvcfgh.DTE")
    lab = t.label("sdt")
    t.emit(f"{lab}:", 0)
    t.load("x7", SDT, "vsstatus.SDT")
    t.emit("csrs 0x200, x7  // vsstatus.SDT = 1")
    t.emit("csrr x8, 0x200")
    t.check_masked("x8", SDT, SDT, lab, "vsstatus.SDT is writable with menvcfg.DTE = henvcfg.DTE = 1", tmp="x5")
    t.window("VU", ["nop"], "ok", "SRET from HS-mode into VU-mode")
    t.emit("csrr x8, 0x200")
    t.check_masked(
        "x8",
        SDT,
        SDT if MUT == "sret_dt_not_cleared" else 0,
        lab,
        "SRET from HS-mode into VU-mode clears vsstatus.SDT",
        tmp="x5",
    )
    t.load("x7", SDT, "vsstatus.SDT")
    t.emit("csrs 0x200, x7  // vsstatus.SDT = 1")
    l2, l3 = t.label("vssret"), t.label("vsback")
    t.allow(1)
    t.enter("VS")
    t.emit(f"{l2}:", 0)
    t.emit("csrr x8, sstatus  // vsstatus after entering VS-mode")
    t.emit(f"LA(x7, {l3})", 2)
    t.emit("csrw sepc, x7  // vsepc")
    t.li("x7", SPP)
    t.emit("csrs sstatus, x7  // vsstatus.SPP = 1")
    t.emit("sret")
    t.emit(f"{l3}:", 0)
    t.emit("csrr x9, sstatus  // vsstatus after the VS-mode SRET")
    t.leave()
    t.outcome("ok", l2, "SRET within VS-mode")
    t.check_masked("x8", SDT, SDT, l2, "SRET from HS-mode into VS-mode leaves vsstatus.SDT = 1", tmp="x5")
    t.check_masked(
        "x9", SDT, SDT if MUT == "sret_dt_not_cleared" else 0, l3, "SRET in VS-mode clears vsstatus.SDT", tmp="x5"
    )
    t.emit("csrr x8, 0x200")
    t.check_masked(
        "x8", SDT, SDT if MUT == "sret_dt_not_cleared" else 0, l3, "HS-mode reads vsstatus.SDT = 0", tmp="x5"
    )
    t.comment("restore: vsstatus.SDT = 0, then henvcfg(h) and menvcfg(h) as they were")
    t.load("x7", SDT, "vsstatus.SDT")
    t.emit("csrc 0x200, x7")
    with t.rv64_only():
        t.emit("csrw 0x60A, x6  // henvcfg")
        t.tsbi_csr("WRITE", "MENVCFG", "x1")
    with t.rv32_only():
        t.emit("csrw 0x61A, x6  // henvcfgh")
        t.tsbi_csr("WRITE", "MENVCFGH", "x1")
    tests.append(t)
    return tests
