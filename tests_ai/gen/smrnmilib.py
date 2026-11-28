# SPDX-License-Identifier: Apache-2.0
"""Helpers for the Smrnmi rule-derived tests (gen_Smrnmi.py).

Every test boots to M-mode: the Smrnmi state (mnscratch, mnepc, mncause, mnstatus) and MNRET exist only in M-mode.
CSRs are named by number and MNRET is emitted as a .word, so MARCH needs no Smrnmi support in the assembler.

No ACT configuration can raise an RNMI, and mnstatus.NMIE cannot be cleared by software (the framework boot sets it,
tests/env/rvtest_setup.h, SMRNMI_SUPPORTED). The tests therefore cover what is observable with NMIE = 1: the CSRs,
their WARL behavior, and MNRET.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent))
from aigen import NO_TRAP, POOL_TRAP, TestFile, X  # noqa: F401  (re-exported for gen_Smrnmi)

if TYPE_CHECKING:
    from aigen import Expect

ISSUE = "https://github.com/riscv/riscv-isa-manual/issues/"
SRC = "src/priv/smrnmi.adoc"
MAC = "src/priv/machine.adoc"
REQ = ["I", "Sm", "Smrnmi"]
MARCH = "rv${XLEN}i_zicsr_zifencei"

CSR = {"mnscratch": 0x740, "mnepc": 0x741, "mncause": 0x742, "mnstatus": 0x744}
NMIE = 1 << 3
MNPV = 1 << 7
MNPELP = 1 << 9
MNPP_SH = 11
MNRET = 0x70200073
ILLEGAL, BREAKPOINT, SWCHECK = 2, 3, 18

MSTATUS_MIE, MSTATUS_MPIE, MSTATUS_MPP, MSTATUS_MPRV = 1 << 3, 1 << 7, 3 << 11, 1 << 17
MSTATUS_TSR = 1 << 22
HSTATUS_VTSR = 1 << 22
LPE = 1 << 2  # menvcfg/senvcfg/henvcfg.LPE
MLPE = 1 << 10  # mseccfg.MLPE
CSRN = {
    "mstatus": 0x300,
    "mstatush": 0x310,
    "misa": 0x301,
    "mepc": 0x341,
    "satp": 0x180,
    "menvcfg": 0x30A,
    "senvcfg": 0x10A,
    "henvcfg": 0x60A,
    "mseccfg": 0x747,
    "hstatus": 0x600,
}

# Privilege modes: (MNPP, MNPV, preprocessor condition for the mode to exist)
MODES = {
    "M": (3, 0, None),
    "S": (1, 0, "defined(S_SUPPORTED)"),
    "U": (0, 0, "defined(U_SUPPORTED)"),
    "VS": (1, 1, "defined(H_SUPPORTED)"),
    "VU": (0, 1, "defined(H_SUPPORTED)"),
}
H = "defined(H_SUPPORTED)"


def new(suite: str, rule: str, required: list[str] | None = None, rv64: bool = False) -> TestFile:
    return TestFile(suite, rule, required=required or REQ, march=MARCH, boot="M", pool=POOL_TRAP, rv64=rv64)


def enc_csr(csr: int, f3: int, rd: int, rs1: int) -> int:
    return (csr << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | 0x73


def csrr_enc(csr: int, rd: int) -> int:
    return enc_csr(csr, 2, rd, 0)


PROBE = csrr_enc(CSRN["mstatus"], 8)  # csrr x8, mstatus: no trap in M-mode, illegal-instruction below M


def mode_cond(mode: str) -> str | None:
    return MODES[mode][2]


def mnstatus_val(mode: str, extra: int = 0, nmie: bool = True) -> int:
    pp, pv, _ = MODES[mode]
    return (NMIE if nmie else 0) | (pp << MNPP_SH) | (MNPV if pv else 0) | extra


def set_mpv(t: TestFile, on: bool) -> None:
    """mstatus.MPV (RV64 bit 39, RV32 mstatush bit 7); H only."""
    op = "csrs" if on else "csrc"
    with t.rv64_only():
        t.li("x14", 1)
        t.emit("slli x14, x14, 39")
        t.emit(f"{op} mstatus, x14")
    with t.rv32_only():
        t.li("x14", 0x80)
        t.emit(f"{op} 0x310, x14  // mstatush.MPV")


def set_mpp(t: TestFile, mode: str) -> None:
    """mstatus.MPP = MNPP encoding of mode (M, S or U)."""
    pp = MODES[mode][0]
    t.li("x14", MSTATUS_MPP)
    t.emit("csrc mstatus, x14")
    if pp:
        t.li("x14", pp << 11)
        t.emit("csrs mstatus, x14")


def leave_m(t: TestFile, mode: str) -> None:
    """Return to M-mode from `mode` with T-SBI (nothing to do in M)."""
    if mode != "M":
        t.emit("RVTEST_TSBI_GOTO_MMODE", 120)


def mnret_land(
    t: TestFile,
    mode: str,
    desc: str,
    *,
    expect_mode: str | None = None,
    extra: int = 0,
    nmie: bool = True,
    wrong_mepc: bool = True,
    after: list[str] | None = None,
    pre: list[str] | None = None,
) -> tuple[str, str]:
    """MNRET with mnepc = L and mnstatus.MNPP/MNPV = mode, in a trap window. At L, `auipc x7, 0` records the
    landing PC, then `csrr x8, mstatus` shows the privilege: no trap in M-mode, illegal-instruction below M (from the
    mode the trap came from, xPP/xPV). mepc points at a decoy W that also records its PC, so a design that returns
    through mepc (or falls through MNRET) lands at the wrong place. Checks the outcome and that x7 = L.
    expect_mode: the mode MNRET must reach (default: mode). Lines in `after` run in that mode before the return to
    M-mode; lines in `pre` run right after the window opens (before the mnepc/mnstatus writes). Returns (L, label of
    the probe)."""
    land = expect_mode or mode
    lab, probe, wrong, cont = t.label("L"), t.label("probe"), t.label("W"), t.label("cont")
    t.allow(1)
    for ln in pre or []:
        t.emit(ln)
    t.la("x14", lab)
    t.emit(f"csrw {hex(CSR['mnepc'])}, x14  // mnepc = L")
    t.li("x14", mnstatus_val(mode, extra, nmie))
    t.emit(f"csrw {hex(CSR['mnstatus'])}, x14  // mnstatus: MNPP/MNPV of {mode}")
    if wrong_mepc:
        t.la("x14", wrong)
        t.emit("csrw mepc, x14  // mepc = W (decoy)")
    t.emit(f".word {hex(MNRET)}  // mnret")
    t.emit(f"{wrong}:", 0)
    t.emit("auipc x7, 0  // W: reached only through mepc or a fall-through")
    t.emit(f"j {cont}")
    t.emit(f"{lab}:", 0)
    t.emit("auipc x7, 0  // L: x7 = landing PC")
    t.emit(f"{probe}:", 0)
    t.emit(f".word {hex(PROBE)}  // csrr x8, mstatus: illegal below M")
    t.emit(f"{cont}:", 0)
    for ln in after or []:
        t.emit(ln)
    leave_m(t, land)
    expect: Expect = "ok" if land == "M" else ILLEGAL
    t.outcome(expect, probe, f"{desc}: MNRET to {land}-mode, privilege probe", [0, PROBE], origin=land)
    t.la("x6", lab)
    t.emit("sub x7, x7, x6")
    t.check("x7", 0, lab, f"{desc}: MNRET resumes at mnepc (x7 = landing PC - L)")
    return lab, probe


def read_mnstatus(t: TestFile, reg: str = "x7") -> None:
    t.emit(f"csrr {reg}, {hex(CSR['mnstatus'])}  // mnstatus")


def misa_c(t: TestFile, reg: str) -> None:
    """reg = nonzero when IALIGN = 16 now: misa.C, or always on a hart with Zca but not C (misa.C is then 0 but
    IALIGN is 16)."""
    t.emit(f"csrr {reg}, misa")
    t.emit(f"andi {reg}, {reg}, 4")
    t.emit("#if defined(ZCA_SUPPORTED) && !defined(C_SUPPORTED)", 0)
    t.emit(f"li {reg}, 4  // Zca without C: IALIGN = 16")
    t.emit("#endif", 0)


def mpelp_from_log(t: TestFile, reg: str) -> None:
    """reg = MPELP (0/1) from the M-mode handler's saved mstatus (RV64 bit 41) or mstatush (RV32 bit 9) of the last
    logged trap."""
    with t.rv64_only():
        t.emit(f"AI_LOG({reg}, TRAPLOG_STATUS)", 10)
        t.emit(f"srli {reg}, {reg}, 41")
    with t.rv32_only():
        t.emit(f"AI_LOG({reg}, TRAPLOG_STATUS2)", 10)
        t.emit(f"srli {reg}, {reg}, 9")
    t.emit(f"andi {reg}, {reg}, 1")
