# SPDX-License-Identifier: Apache-2.0
"""Helpers for the Smdbltrp and Ssdbltrp suites (gen_Smdbltrp.py): field masks, DTE/SDT/MDT writes in each
boot mode, trap-log field checks and VS/VU entry from M-mode."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aigen import X

if TYPE_CHECKING:
    from collections.abc import Callable

    from aigen import TestFile

# mstatus / sstatus
SIE, MIE, SPIE, MPIE, SPP = 0x2, 0x8, 0x20, 0x80, 0x100
MPP = 0x1800
SDT = 1 << 24  # sstatus/mstatus/vsstatus bit 24 (both XLENs)
MDT = X(1 << 10, 1 << 42)  # mstatush bit 10 (RV32), mstatus bit 42 (RV64)
MPV = X(1 << 7, 1 << 39)  # mstatush / mstatus
GVA = X(1 << 6, 1 << 38)
DTE = X(1 << 27, 1 << 59)  # menvcfgh/henvcfgh bit 27 (RV32), menvcfg/henvcfg bit 59 (RV64)
SSIP = 0x2
H = "defined(H_SUPPORTED)"
INT = X(1 << 31, 1 << 63)
HSTATUS_SPV = 1 << 7
CSR_HENVCFG, CSR_HENVCFGH, CSR_MSTATUSH, CSR_MTVAL2, CSR_HEDELEG = 0x60A, 0x61A, 0x310, 0x34B, 0x602
CSR_VSSTATUS, CSR_VSEPC, CSR_VSCAUSE, CSR_VSTVAL = 0x200, 0x241, 0x242, 0x243
CSR_MNEPC, CSR_MNCAUSE, CSR_MNSTATUS = 0x741, 0x742, 0x744
MNRET = 0x70200073
MNSTATUS_NMIE, MNSTATUS_MNPV, MNSTATUS_MNPP = 0x8, 0x80, 0x1800
HANDLER = {"M": 3, "S": 1, "VS": 2}  # TRAPLOG_VECT bits 1:0


def bit_x(t: TestFile, reg: str, value: X, tmp: str = "x5") -> None:
    """reg = the per-XLEN constant `value` (one bit), built without the table."""
    for xlen, cond in ((32, "__riscv_xlen == 32"), (64, "__riscv_xlen == 64")):
        v = value.num(xlen)
        with t.only_if(cond):
            if v < 0x800:
                t.emit(f"li {reg}, {v}")
            else:
                sh = v.bit_length() - 1
                assert v == 1 << sh
                t.emit(f"li {reg}, 1")
                t.emit(f"slli {reg}, {reg}, {sh}")


# ---------------------------------------------------------------- envcfg.DTE
def dte_tsbi(t: TestFile, on: bool) -> None:
    """S-boot: menvcfg.DTE through T-SBI (menvcfgh on RV32)."""
    t.comment(f"M-mode (T-SBI): menvcfg.DTE = {int(on)}")
    bit_x(t, "a1", DTE)
    op = "SET" if on else "CLEAR"
    with t.rv64_only():
        t.tsbi_csr(op, "MENVCFG", "a1")
    with t.rv32_only():
        t.tsbi_csr(op, "MENVCFGH", "a1")


def dte_m(t: TestFile, on: bool, reg: str = "x7") -> None:
    """M-boot: menvcfg.DTE directly."""
    bit_x(t, reg, DTE)
    op = "csrs" if on else "csrc"
    with t.rv64_only():
        t.emit(f"{op} menvcfg, {reg}  // menvcfg.DTE = {int(on)}")
    with t.rv32_only():
        t.emit(f"{op} 0x31A, {reg}  // menvcfgh.DTE = {int(on)}")


def henv_dte(t: TestFile, on: bool, reg: str = "x7") -> None:
    """HS- or M-mode: henvcfg.DTE."""
    bit_x(t, reg, DTE)
    op = "csrs" if on else "csrc"
    with t.rv64_only():
        t.emit(f"{op} {hex(CSR_HENVCFG)}, {reg}  // henvcfg.DTE = {int(on)}")
    with t.rv32_only():
        t.emit(f"{op} {hex(CSR_HENVCFGH)}, {reg}  // henvcfgh.DTE = {int(on)}")


def read_dte(t: TestFile, reg: str, csr: str) -> None:
    """reg = DTE bit (0/1) of menvcfg or henvcfg, read in M (menvcfg) or HS/M (henvcfg) mode."""
    lo, hi = {"menvcfg": ("menvcfg", "0x31A"), "henvcfg": (hex(CSR_HENVCFG), hex(CSR_HENVCFGH))}[csr]
    with t.rv64_only():
        t.emit(f"csrr {reg}, {lo}")
        t.emit(f"srli {reg}, {reg}, 59")
    with t.rv32_only():
        t.emit(f"csrr {reg}, {hi}")
        t.emit(f"srli {reg}, {reg}, 27")
    t.emit(f"andi {reg}, {reg}, 1")


# ---------------------------------------------------------------- MDT (M-mode)
def mdt(t: TestFile, on: bool, reg: str = "x7") -> None:
    """M-mode: set or clear mstatus.MDT (mstatush on RV32) with csrs/csrc."""
    bit_x(t, reg, MDT)
    op = "csrs" if on else "csrc"
    with t.rv64_only():
        t.emit(f"{op} mstatus, {reg}  // MDT = {int(on)}")
    with t.rv32_only():
        t.emit(f"{op} {hex(CSR_MSTATUSH)}, {reg}  // mstatush.MDT = {int(on)}")


def read_mdt(t: TestFile, reg: str) -> None:
    """reg = mstatus.MDT (0/1)."""
    with t.rv64_only():
        t.emit(f"csrr {reg}, mstatus")
        t.emit(f"srli {reg}, {reg}, 42")
    with t.rv32_only():
        t.emit(f"csrr {reg}, {hex(CSR_MSTATUSH)}")
        t.emit(f"srli {reg}, {reg}, 10")
    t.emit(f"andi {reg}, {reg}, 1")


# ---------------------------------------------------------------- trap log fields
def log(t: TestFile, reg: str, word: str) -> None:
    t.emit(f"AI_LOG({reg}, {word})", 10)


def log_handler(t: TestFile, lab: str, mode: str, desc: str) -> None:
    """The last logged trap was taken by the `mode` handler (M, S for HS/S, VS)."""
    log(t, "x15", "TRAPLOG_VECT")
    t.emit("andi x15, x15, 3")
    t.check("x15", HANDLER[mode], lab, f"{desc}: taken by the {mode}-mode handler (3 M, 1 S/HS, 2 VS)")


def log_sdt(t: TestFile, lab: str, value: int | list[int], desc: str) -> None:
    """xstatus.SDT recorded at the handler's entry (sstatus for HS/VS handlers, mstatus for M)."""
    log(t, "x15", "TRAPLOG_STATUS")
    t.emit("srli x15, x15, 24")
    t.emit("andi x15, x15, 1")
    t.check("x15", value, lab, f"{desc}: SDT at handler entry")


def log_mdt(t: TestFile, lab: str, value: int, desc: str) -> None:
    """mstatus.MDT at the M handler's entry (mstatush on RV32)."""
    with t.rv64_only():
        log(t, "x15", "TRAPLOG_STATUS")
        t.emit("srli x15, x15, 42")
    with t.rv32_only():
        log(t, "x15", "TRAPLOG_STATUS2")
        t.emit("srli x15, x15, 10")
    t.emit("andi x15, x15, 1")
    t.check("x15", value, lab, f"{desc}: mstatus.MDT at M handler entry")


def read_sdt(t: TestFile, reg: str, csr: str = "sstatus") -> None:
    """reg = SDT bit of sstatus/mstatus/vsstatus (0/1)."""
    t.emit(f"csrr {reg}, {csr}")
    t.emit(f"srli {reg}, {reg}, 24")
    t.emit(f"andi {reg}, {reg}, 1")


# ---------------------------------------------------------------- VS/VU from M-mode
def mret_to(t: TestFile, mode: str, target: str, reg: str = "x7") -> None:
    """M-mode: set MPP/MPV for `mode` (M, S, U, VS, VU) and mret to `target`."""
    mpp = {"M": 3, "S": 1, "VS": 1, "U": 0, "VU": 0}[mode]
    mpv = mode in ("VS", "VU")
    t.emit(f"LA({reg}, {target})", 2)
    t.emit(f"csrw mepc, {reg}")
    t.li(reg, MPP)
    t.emit(f"csrc mstatus, {reg}")
    if mpp:
        t.li(reg, mpp << 11)
        t.emit(f"csrs mstatus, {reg}  // MPP = {mpp}")
    mpv_bit(t, mpv, reg)
    t.emit("mret")


def mpv_bit(t: TestFile, on: bool, reg: str) -> None:
    """M-mode: mstatus.MPV (mstatush on RV32), only under H."""
    with t.only_if(H):
        bit_x(t, reg, MPV)
        op = "csrs" if on else "csrc"
        with t.rv64_only():
            t.emit(f"{op} mstatus, {reg}  // MPV = {int(on)}")
        with t.rv32_only():
            t.emit(f"{op} {hex(CSR_MSTATUSH)}, {reg}  // mstatush.MPV = {int(on)}")


def bare_guest(t: TestFile) -> None:
    """HS/M: vsatp = hgatp = 0, so VS/VU addresses are physical (the framework's defaults, made explicit)."""
    t.emit("csrw 0x280, x0  // vsatp = Bare")
    t.emit("csrw 0x680, x0  // hgatp = Bare")
    t.emit(".word 0x62000073  // hfence.gvma")


def skip_lines(t: TestFile, lo: int, hi: int) -> list[str]:
    """AI_SKIP over table entries lo..hi-1 whatever their preprocessor conditions: one AI_SKIP per distinct set
    of conditions beyond those in force, each under its own #if (TestFile._skip_lines allows only XLEN ones)."""
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


def if_trapped(t: TestFile, checks: Callable[[], None]) -> None:
    """Run checks only when the last window trapped (x14 != -1, as left by AI_OUTCOME)."""
    done, j = t.label("nt"), t.label("j")
    t.emit("li x5, -1")
    t.emit(f"beq x14, x5, {done}")
    first = len(t.table)
    checks()
    t.emit(f"j {j}")
    t.emit(f"{done}:", 0)
    t.code += skip_lines(t, first, len(t.table))
    t.emit(f"{j}:", 0)
