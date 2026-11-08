#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate tests_ai/Sm and tests_ai/PMP: one test per normative rule of the machine-level ISA.

The rules are the norm: tags of src/priv/machine.adoc (and src/priv/smepmp.adoc). Every test boots to M-mode,
requires Sm and probes optional behavior at run time. PMP rules (the Physical Memory Protection section, MPRV's
effect on protection and the Smepmp mseccfg fields) are written to tests_ai/PMP by pmplib.py; the rest go to
tests_ai/Sm. Mutants (MUTANTS) are expectation switches, read through smlib.mut() when the tests are generated.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent))
import pmplib
import smlib as L
from aigen import TestFile, X
from smlib import (
    ALL,
    MIE,
    MPIE,
    MPP,
    MPRV,
    MXR,
    NO_S,
    NO_U,
    RV32,
    RV64,
    SIE,
    SPIE,
    SPP,
    SUM,
    TSR,
    TVM,
    TW,
    S,
    U,
    describe,
    guard,
    mut,
    new,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from aigen import Expect

SUITE = "Sm"

MUTANTS: dict[str, str] = {
    # misa
    "misa_mxl_writable": "misa.MXL follows a write",
    "misa_reserved_set": "reserved misa letters read back what was written",
    "misa_e_follows_i": "misa.E reads as I (not its complement)",
    "misa_disable_ignored": "clearing a writable misa letter leaves its instructions enabled",
    "misa_dep_kept": "clearing F leaves D enabled",
    "misa_ialign_not_suppressed": "a misa write that clears C before a misaligned instruction takes effect",
    # traps
    "deleg_ignored": "medeleg[3] = 1 does not delegate ebreak from S/U",
    "deleg_writes_m_stack": "a trap delegated to S-mode also clears mstatus.MIE",
    "deleg_from_m": "an M-mode ebreak with medeleg[3] = 1 is taken in S-mode",
    "medelegh_rv64": "medelegh exists on RV64",
    "ecall_cause_u": "ecall from S-mode reports cause 8",
    "mepc_bit0": "mepc keeps bit 0",
    "mepc_bit1_unmasked": "mepc[1] is not masked on reads while IALIGN = 32",
    "lr_store_cause": "a misaligned LR raises a store/AMO exception",
    "mtval_sext": "mtval sign-extends the illegal instruction bits on RV64",
    "mtval_kept": "ecall leaves mtval unwritten",
    "mtval_aligned": "mtval holds the doubleword-aligned address of a faulting access",
    # interrupts
    "mie_ignored_in_m": "an M-mode interrupt is taken whatever mstatus.MIE",
    "deleg_taken_in_m": "a delegated interrupt is taken in M-mode with MIE = 1",
    "m_int_needs_mie_below_m": "an M-level interrupt below M-mode also needs MIE = 1",
    "pri_sti_over_ssi": "STI has priority over SSI",
    "pri_mti_over_msi": "MTI has priority over MSI",
    "s_before_m": "a delegated S-level interrupt is taken before a pending M-level one",
    "late_eval": "an interrupt enabled by a CSR write or MRET is taken one instruction late",
    "vectored_ignored": "Vectored mode sends interrupts to BASE",
    "direct_vectors": "Direct mode sends interrupts to BASE + 4 * cause",
    "mtvec_mode2": "mtvec.MODE reads back whatever was written, including the reserved 2 and 3",
    "mie_s_bits_no_s": "S-level mie bits writable without S-mode",
    "mip_m_writable": "a machine-level mip bit is writable",
    "hpm_event0_counts": "an hpm counter whose selector holds event 0 still counts",
    "mip_pending_clearable": "csrc clears a machine-level mip bit while its source is pending",
    "mip_clear_ignored": "writing 0 to mip.SSIP does not clear it",
    "seip_rmw_or": "csrrs/csrrc of mip write back the platform's SEI signal into the software SEIP bit",
    "tw0_traps": "S-mode wfi traps with TW = 0",
    "mcounteren_ignored": "a clear mcounteren bit does not stop S/U counter reads",
    "inhibit_ignored": "a set mcountinhibit bit does not stop its counter",
    "minstret_write_counts": "the csrw that writes minstret also increments it",
    "counter_32bit": "mcycle/minstret are 32-bit counters",
    "cycle_writable": "cycle/instret are writable",
    "menvcfg_no_u_exists": "menvcfg exists without U-mode",
    "envcfg_field_writable": "a menvcfg field of an absent extension is writable",
    "cbo_enable_ignored": "CBO instructions execute below M with their menvcfg enable clear",
    "seed_enable_ignored": "seed stays inaccessible with USEED/SSEED = 1",
    "fs_ro0": "FS is read-only 0 with F",
    "sd_ignores_vs": "SD does not summarize VS",
    "off_ignored": "FS/VS = Off does not stop FP/vector instructions",
    "fs_init_clears": "setting FS = Initial clears the FP registers",
    "no_dirty_below_m": "FS/VS stay Initial when S/U-mode code modifies the state",
    "xl_reserved": "SXL/UXL hold 0 or the reserved 3",
    "tvm_ignored": "TVM = 1 does not trap satp/sfence.vma in S-mode",
    "tsr_ignored": "TSR = 1 does not trap sret in S-mode",
    "be_ignored": "xBE = 1 has no effect on loads",
    "mret_below_m": "mret executes below M-mode",
    "xret_falls_through": "xRET continues at the next instruction instead of xepc",
    "intr_bit_clear": "mcause's Interrupt bit is clear for interrupts",
    "mtime_signed": "mtime >= mtimecmp compared as signed",
    "mtie_ignored": "MTIE does not gate the machine timer interrupt",
    "msip_all_bits": "msip bits 31:1 are writable",
    # mstatus
    "sie_writable_no_s": "SIE/SPIE writable without S-mode",
    "mpp_keeps_2": "MPP holds the reserved value 2",
    "trap_mpp_m": "a trap into M-mode records MPP = M whatever the mode it came from",
    "mret_pie_kept": "MRET leaves MPIE unchanged instead of setting it to 1",
    "mret_keeps_mprv": "MRET to a mode below M leaves MPRV set",
    "mprv_writable_no_u": "MPRV writable without U-mode",
    "satp_ro_field_writable": "MXR/SUM/TVM writable when satp has no translation mode (or read-only 0 when it has)",
    **pmplib.MUTANTS,
}

MISA_LETTERS = {  # letter: (bit, condition that the letter's extension is implemented, condition it is not)
    "A": (0, "defined(A_SUPPORTED)", "!defined(ZAAMO_SUPPORTED) || !defined(ZALRSC_SUPPORTED)"),
    "B": (1, "defined(B_SUPPORTED)", "!defined(ZBA_SUPPORTED) || !defined(ZBB_SUPPORTED) || !defined(ZBS_SUPPORTED)"),
    "C": (2, "defined(C_SUPPORTED)", "!defined(ZCA_SUPPORTED)"),
    "D": (3, "defined(D_SUPPORTED)", "!defined(D_SUPPORTED)"),
    "F": (5, "defined(F_SUPPORTED)", "!defined(F_SUPPORTED)"),
    "H": (7, "defined(H_SUPPORTED)", "!defined(H_SUPPORTED)"),
    "I": (8, "1", "0"),
    "M": (12, "defined(M_SUPPORTED)", "!defined(M_SUPPORTED)"),
    "Q": (16, "defined(Q_SUPPORTED)", "!defined(Q_SUPPORTED)"),
    "S": (18, S, NO_S),
    "U": (20, U, NO_U),
    "V": (21, "defined(V_SUPPORTED)", "!defined(V_SUPPORTED)"),
}
RESERVED_LETTERS = [6, 9, 10, 11, 14, 17, 19, 22, 24, 25]  # g j k l o r t w y z


def mxl_shift(xlen: int) -> int:
    return xlen - 2


def read_misa(t: TestFile, reg: str) -> None:
    t.emit(f"csrr {reg}, misa")


def bit_of(t: TestFile, dst: str, src: str, bit: int) -> None:
    t.emit(f"srli {dst}, {src}, {bit}")
    t.emit(f"andi {dst}, {dst}, 1")


def if_misa(t: TestFile, reg: str, body: Callable[[], object]) -> None:
    """Run body only when misa (in reg) is nonzero: a zero misa means the register is not implemented."""
    L.either(t, reg, body, lambda: None)


# ---------------------------------------------------------------- misa
def gen_misa(suite: str) -> list[TestFile]:
    tests = []
    MXLV = X(1, 2)

    # ---- misa_acc ----
    t = new(suite, "misa_acc")
    describe(
        t,
        context="misa is MRW. Writing back the value just read is a legal write and must not change the ISA.",
        plan="1. Every CSR instruction form that writes misa's current value (csrrw, csrrs/csrrc with 0, the "
        "immediate forms with 0) executes without a trap, returns the old value, and leaves misa unchanged.",
    )
    t.emit("csrr x9, misa")
    for asm, note in (
        ("csrrw x7, misa, x9", "csrrw of its own value"),
        ("csrrs x7, misa, x0", "csrrs rs1=x0"),
        ("csrrc x7, misa, x0", "csrrc rs1=x0"),
        ("csrrsi x7, misa, 0", "csrrsi 0"),
        ("csrrci x7, misa, 0", "csrrci 0"),
    ):
        lab = t.window("M", [asm], "ok", note)
        t.emit("sub x7, x7, x9")
        t.check("x7", 0, lab, f"{note}: returns the old misa")
        t.emit("csrr x8, misa")
        t.emit("sub x8, x8, x9")
        t.check("x8", 0, lab, f"{note}: misa is unchanged")
    tests.append(t)

    # ---- misa_always_rd ----
    t = new(suite, "misa_always_rd")
    describe(t, plan="1. Reading misa with csrrs rs1=x0 and csrrsi uimm=0 in M-mode does not trap.")
    for f in L.READ_FORMS:
        L.csr_window(t, "M", 0x301, "misa", f, "ok", "M-mode")
    tests.append(t)

    # ---- misa_mxl_op_nz ----
    t = new(suite, "misa_mxl_op_nz")
    describe(
        t,
        context="Tests boot to M-mode at the XLEN they were compiled for, so MXLEN = XLEN. MXL encodings: "
        "1 = 32, 2 = 64, 3 reserved (misa_mxl_enc). misa is MXLEN bits wide, so MXL is bits MXLEN-1:MXLEN-2.",
        plan="1. If misa is nonzero, misa[XLEN-1:XLEN-2] = 1 on RV32 and 2 on RV64.",
    )
    read_misa(t, "x9")

    def mxl_check() -> None:
        lab = t.label("mxl")
        t.emit(f"{lab}:", 0)
        with t.rv64_only():
            t.emit("srli x7, x9, 62")
        with t.rv32_only():
            t.emit("srli x7, x9, 30")
        t.check("x7", MXLV, lab, "misa.MXL encodes the M-mode XLEN")

    if_misa(t, "x9", mxl_check)
    tests.append(t)

    # ---- misa_mxl_acc ----
    t = new(suite, "misa_mxl_acc")
    describe(
        t,
        context="Writes keep every other misa bit at its current value, so only MXL is asked to change.",
        plan="1. Write misa with MXL replaced by 0, 1, 2 and 3 (csrrw), and set and clear the MXL bits "
        "(csrrs/csrrc): MXL keeps its value each time.\n2. misa is restored.",
    )
    read_misa(t, "x9")

    def mxl_ro() -> None:
        t.load("x8", X(3 << 30, 3 << 62), "MXL mask")
        t.emit("not x6, x8")
        t.emit("and x6, x6, x9  // misa without MXL")
        for v in range(4):
            lab = t.label("mxlw")
            t.load("x7", X(v << 30, v << 62), f"MXL = {v}")
            t.emit("or x7, x7, x6")
            t.emit(f"{lab}:", 0)
            t.emit("csrw misa, x7")
            t.emit("csrr x7, misa")
            t.emit("xor x7, x7, x9")
            t.emit("and x7, x7, x8")
            exp = X(v << 30, v << 62) if mut() == "misa_mxl_writable" else 0
            if mut() == "misa_mxl_writable":
                t.emit("csrr x7, misa")
                t.emit("and x7, x7, x8")
            t.check("x7", exp, lab, f"MXL is unchanged by csrrw with MXL = {v}")
            t.emit("csrw misa, x9")
        for op in ("csrs", "csrc"):
            lab = t.label("mxl" + op)
            t.emit(f"{lab}:", 0)
            t.emit(f"{op} misa, x8")
            t.emit("csrr x7, misa")
            t.emit("xor x7, x7, x9")
            t.emit("and x7, x7, x8")
            t.check("x7", 0, lab, f"MXL is unchanged by {op} of the MXL bits")
            t.emit("csrw misa, x9")

    if_misa(t, "x9", mxl_ro)
    tests.append(t)

    # ---- misa_e_not_i / misa_i_op / misa_e_acc ----
    t = new(suite, "misa_e_not_i")
    describe(t, plan="1. If misa is nonzero, misa.E (bit 4) = NOT misa.I (bit 8).")
    read_misa(t, "x9")

    def e_not_i() -> None:
        lab = t.label("ei")
        t.emit(f"{lab}:", 0)
        bit_of(t, "x7", "x9", 4)
        bit_of(t, "x8", "x9", 8)
        t.emit("xor x7, x7, x8")
        if mut() == "misa_e_follows_i":
            t.emit("xori x7, x7, 1")
        t.check_bool("x7", lab, "misa.E is the complement of misa.I")

    if_misa(t, "x9", e_not_i)
    tests.append(t)

    t = new(suite, "misa_i_op")
    describe(
        t,
        context="These tests require I (RV32I/RV64I), so misa.I must be set whenever misa is implemented.",
        plan="1. If misa is nonzero, misa.I = 1 and misa.E = 0.",
    )
    read_misa(t, "x9")

    def i_set() -> None:
        lab = t.label("i")
        t.emit(f"{lab}:", 0)
        t.check_masked("x9", 0x110, 0x100, lab, "misa.I = 1 and misa.E = 0 on an RV32I/RV64I hart")

    if_misa(t, "x9", i_set)
    tests.append(t)

    t = new(suite, "misa_e_acc")
    describe(
        t,
        context="Writes keep every other bit at its current value.",
        plan="1. Set misa.E (csrrs) and write misa with E flipped (csrrw): E keeps its value.\n2. misa is restored.",
    )
    read_misa(t, "x9")

    def e_ro() -> None:
        for asm in ("csrs misa, x6", "csrw misa, x7"):
            lab = t.label("e")
            t.emit("li x6, 0x10")
            t.emit("xor x7, x9, x6")
            t.emit(f"{lab}:", 0)
            t.emit(asm)
            t.emit("csrr x8, misa")
            t.emit("xor x8, x8, x9")
            t.emit("andi x8, x8, 0x10")
            t.check("x8", 0, lab, f"misa.E is read-only ({asm.split()[0]})")
            t.emit("csrw misa, x9")

    if_misa(t, "x9", e_ro)
    tests.append(t)

    # ---- misa_extensions_rsv_ret_0 ----
    t = new(suite, "misa_extensions_rsv_ret_0")
    rsv = sum(1 << b for b in RESERVED_LETTERS)
    rsvx = X(rsv | (((1 << 30) - 1) ^ ((1 << 26) - 1)), rsv | (((1 << 62) - 1) ^ ((1 << 26) - 1)))
    describe(
        t,
        context="Reserved letters (misa_extensions_enc_tbl): G, J, K, L, O, R, T, W, Y, Z (bits 6, 9, 10, 11, 14, "
        "17, 19, 22, 24, 25). Bits 26 to MXLEN-3 are also reserved (between Extensions and MXL). N and P are only "
        "tentatively reserved and are not checked.",
        plan="1. The reserved bits read 0.\n2. After csrrs of all reserved bits they still read 0.\n3. misa is "
        "restored.",
    )
    read_misa(t, "x9")
    lab = t.label("rsv")
    t.emit(f"{lab}:", 0)
    t.check_masked("x9", rsvx, 0, lab, "reserved misa bits read 0")
    t.load("x6", rsvx, "reserved misa bits")
    lab = t.label("rsvw")
    t.emit(f"{lab}:", 0)
    t.emit("csrs misa, x6")
    t.emit("csrr x7, misa")
    t.emit("csrw misa, x9")
    t.check_masked(
        "x7", rsvx, rsvx if mut() == "misa_reserved_set" else 0, lab, "reserved bits read 0 after a write of 1s"
    )
    tests.append(t)

    # ---- misa_extensions_reset_maximal ----
    t = new(suite, "misa_extensions_reset_maximal")
    describe(
        t,
        context="The framework does not write misa, so at the start of the test it holds its reset value. Each "
        "standard letter must be set when its extension is implemented (the maximal set) and clear when it is "
        "not. A letter is only checked as clear when no part of it is implemented (C: no Zca; A: Zaamo or Zalrsc "
        "missing; B: one of Zba/Zbb/Zbs missing), and as set when the full extension is implemented. I is "
        "selected over E.",
        plan="1. If misa is nonzero, each letter A, B, C, D, F, H, I, M, Q, S, U, V is 1 when its extension is "
        "implemented and 0 when it is not.",
    )
    read_misa(t, "x9")
    for name, (bit, yes, no) in MISA_LETTERS.items():
        for cond, v in ((yes, 1), (no, 0)):
            if cond == "0":
                continue

            def letter(name: str = name, bit: int = bit, v: int = v) -> None:
                lab = t.label(f"l{name}")
                t.emit(f"{lab}:", 0)
                bit_of(t, "x7", "x9", bit)
                t.check("x7", v, lab, f"misa.{name} = {v} (extension {'implemented' if v else 'absent'})")

            with t.only_if(cond):
                if_misa(t, "x9", letter)
    tests.append(t)

    # ---- misa_s_op / misa_u_op ----
    for rule, bit, cond, csr, desc in (
        ("misa_s_op", 18, S, "sstatus", "S"),
        ("misa_u_op", 20, U, "mstatus", "U"),
    ):
        t = new(suite, rule)
        describe(
            t,
            plan=f"1. On a hart with {desc}-mode, MRET with MPP={desc} enters it "
            + (
                "(sstatus is readable there and mstatus raises illegal instruction)."
                if desc == "S"
                else "(an mstatus read there raises illegal instruction, from U-mode)."
            )
            + f"\n2. If misa is nonzero, misa.{desc} = 1 exactly when {desc}-mode is implemented.",
        )
        read_misa(t, "x9")

        def present(bit: int = bit, desc: str = desc, t: TestFile = t) -> None:
            lab = t.label("b")
            t.emit(f"{lab}:", 0)
            bit_of(t, "x7", "x9", bit)
            t.check("x7", 1, lab, f"misa.{desc} = 1 on a hart with {desc}-mode")

        def absent(bit: int = bit, desc: str = desc, t: TestFile = t) -> None:
            lab = t.label("b")
            t.emit(f"{lab}:", 0)
            bit_of(t, "x7", "x9", bit)
            t.check("x7", 0, lab, f"misa.{desc} = 0 on a hart without {desc}-mode")

        with t.only_if(cond):
            if_misa(t, "x9", present)
            if desc == "S":
                t.window("S", ["csrr x7, sstatus"], "ok", "sstatus read after MRET to S")
            t.window(
                desc,
                ["csrr x7, mstatus"],
                2,
                "mstatus read after MRET with MPP=" + desc,
                [0, L.enc_csr(0x300, 2, 7, 0)],
            )
        with t.only_if(f"!({cond})"):
            if_misa(t, "x9", absent)
        tests.append(t)

    # ---- misa_m_op / misa_B_op / Zmmul_misa_m ----
    t = new(suite, "misa_m_op")
    describe(
        t,
        context="Instructions are .word encodings (MARCH stays rv${XLEN}i).",
        plan="1. If misa.M = 1: mul, mulh, mulhu, div, divu, rem, remu (and the W forms on RV64) execute in M-mode "
        "without a trap and give the M-extension results for 7 and -3.",
    )
    read_misa(t, "x9")

    def m_ops() -> None:
        bit_of(t, "x7", "x9", 12)

        def run() -> None:
            ops = [
                ("mul", 0, -21),
                ("mulh", 1, -1),
                ("mulhu", 3, 6),
                ("div", 4, -2),
                ("divu", 5, 0),
                ("rem", 6, 1),
                ("remu", 7, 7),
            ]
            for name, f3, res in ops:
                e = (1 << 25) | (8 << 20) | (6 << 15) | (f3 << 12) | (7 << 7) | 0x33
                t.li("x6", 7)
                t.li("x8", -3)
                lab = L.word_window(t, "M", e, f"{name} x7, x6, x8", "ok", f"{name} with misa.M = 1")
                if name == "mulhu":
                    exp = X(6, 6)
                elif name == "divu":
                    exp = X(0, 0)
                else:
                    exp = res
                t.check("x7", exp, lab, f"{name} 7, -3")
            with t.rv64_only():
                e = (1 << 25) | (8 << 20) | (6 << 15) | (4 << 12) | (7 << 7) | 0x3B
                t.li("x6", 7)
                t.li("x8", -3)
                lab = L.word_window(t, "M", e, "divw x7, x6, x8", "ok", "divw with misa.M = 1")
                t.check("x7", -2, lab, "divw 7, -3")

        L.either(t, "x7", run, lambda: None)

    if_misa(t, "x9", m_ops)
    tests.append(t)

    t = new(suite, "misa_B_op")
    describe(
        t,
        plan="1. If misa.B = 1, one instruction each of Zba (sh1add), Zbb (andn) and Zbs (bset) executes in "
        "M-mode without a trap and gives its result.",
    )
    read_misa(t, "x9")

    def b_ops() -> None:
        bit_of(t, "x7", "x9", 1)

        def run() -> None:
            for name, f7, f3, a, b, res in (
                ("sh1add", 0x10, 2, 5, 9, 19),
                ("andn", 0x20, 7, 0xF0F, 0x0FF, 0xF00),
                ("bset", 0x14, 1, 0x100, 3, 0x108),
            ):
                e = (f7 << 25) | (8 << 20) | (6 << 15) | (f3 << 12) | (7 << 7) | 0x33
                t.li("x6", a)
                t.li("x8", b)
                lab = L.word_window(t, "M", e, f"{name} x7, x6, x8", "ok", f"{name} with misa.B = 1")
                t.check("x7", res, lab, f"{name} {hex(a)}, {hex(b)}")

        L.either(t, "x7", run, lambda: None)

    if_misa(t, "x9", b_ops)
    tests.append(t)

    # ---- misa_extensions_disabling / Zmmul_misa_m ----
    t = new(suite, "misa_extensions_disabling", pool=["x1", "x6", "x7", "x8"])
    t.extra_data += [".p2align 4", "sm_misa_word: .dword 0, 0"]
    describe(
        t,
        context="Each letter is tried only when it is set and the write actually clears it (misa letters are "
        "WARL). Instructions are .word encodings. A disabled extension's instructions are reserved, so they raise "
        "illegal instruction (xtval 0 or the instruction bits). F, D and V need mstatus.FS/VS on, which is set "
        "before. misa is restored with its saved value after each letter. A, B and V are not tried: their "
        "instructions also belong to separately named extensions (Zaamo/Zalrsc, Zba/Zbb/Zbs, Zve*) that a hart "
        "may keep enabled, as Zmmul keeps multiplication with misa.M clear (issue 1711).",
        issues=f"{L.ISSUE}1711: with Zmmul, mul stays legal when misa.M is clear; div/rem are reserved.",
        plan="1. For M (div), F (fmv.w.x) and D (fadd.d): the instruction executes while the letter is set; csrc clears the letter; if misa reads it as "
        "clear, the instruction raises illegal instruction; misa is restored.\n"
        "2. C: with C cleared, a 16-bit instruction (two c.nop) at a 4-byte boundary raises illegal instruction "
        "(xtval 0, the halfword or both halfwords).",
    )
    t.emit("csrr x9, misa")
    t.li("x5", 0x2200)  # FS = VS = Initial
    t.emit("csrs mstatus, x5")
    t.la("x8", "sm_misa_word")
    cases = [
        (
            "M",
            12,
            "defined(M_SUPPORTED)",
            [((1 << 25) | (6 << 20) | (6 << 15) | (4 << 12) | (7 << 7) | 0x33, "div x7, x6, x6")],
        ),
        ("F", 5, "defined(F_SUPPORTED)", [((0x78 << 25) | (6 << 15) | (1 << 7) | 0x53, "fmv.w.x f1, x6")]),
        ("D", 3, "defined(D_SUPPORTED)", [((1 << 25) | (1 << 20) | (1 << 15) | (1 << 7) | 0x53, "fadd.d f1, f1, f1")]),
    ]
    for name, bit, cond, insns in cases:

        def body(name: str = name, bit: int = bit, insns: list[tuple[int, str]] = insns) -> None:
            t.comment(f"---- misa.{name}")
            bit_of(t, "x7", "x9", bit)

            def letter_set() -> None:
                t.li("x6", 3)
                for e, note in insns:
                    L.word_window(t, "M", e, note, "ok", f"{note} with misa.{name} = 1")
                t.load("x6", 1 << bit, f"misa.{name}")
                t.emit("csrc misa, x6")
                t.emit("csrr x7, misa")
                bit_of(t, "x7", "x7", bit)

                def kept() -> None:
                    t.emit("csrw misa, x9")

                def cleared() -> None:
                    t.li("x6", 3)
                    for e, note in insns:
                        exp = "ok" if mut() == "misa_disable_ignored" else 2
                        L.word_window(t, "M", e, note, exp, f"{note} with misa.{name} cleared")
                    t.emit("csrw misa, x9")

                L.either(t, "x7", kept, cleared)

            L.either(t, "x7", letter_set, lambda: None)

        with t.only_if(cond):
            if_misa(t, "x9", body)

    def c_case() -> None:
        t.comment("---- misa.C")
        bit_of(t, "x7", "x9", 2)

        def c_set() -> None:
            t.li("x6", 4)
            t.emit(".p2align 2", 0)
            t.emit("csrc misa, x6")
            t.emit("csrr x7, misa")
            t.emit("andi x7, x7, 4")

            def cleared() -> None:
                back = t.label("cback")
                t.la("x5", back)
                t.la("x4", "rvtest_trap_resume")
                t.emit("SREG x5, 0(x4)")
                lab = t.label("cnop")
                t.allow(1)
                t.emit(".p2align 2", 0)
                t.emit(f"{lab}:", 0)
                t.emit(".hword 0x0001  // c.nop, reserved while C is disabled", 1)
                t.emit(".hword 0x0001", 0)
                t.emit(f"{back}:", 0)
                exp = "ok" if mut() == "misa_disable_ignored" else 2
                t.outcome(exp, lab, "c.nop at a 4-byte boundary with misa.C cleared", [0, 1, 0x10001])
                t.emit("csrw misa, x9")

            L.either(t, "x7", lambda: t.emit("csrw misa, x9"), cleared)

        L.either(t, "x7", c_set, lambda: None)

    with t.only_if("defined(C_SUPPORTED)"):
        if_misa(t, "x9", c_case)
    t.li("x5", 0x6600)
    t.emit("csrc mstatus, x5")
    tests.append(t)

    t = new(suite, "Zmmul_misa_m")
    describe(
        t,
        context="Applies to harts with Zmmul; the test needs misa.M to be writable to clear it.",
        plan="1. With Zmmul, if misa.M can be cleared: mul and mulh execute without a trap and give their results; "
        "div raises illegal instruction (M is disabled).\n2. misa is restored.",
    )
    with t.only_if("defined(ZMMUL_SUPPORTED)"):
        t.emit("csrr x9, misa")
        bit_of(t, "x7", "x9", 12)

        def m_set() -> None:
            t.load("x6", 1 << 12, "misa.M")
            t.emit("csrc misa, x6")
            t.emit("csrr x7, misa")
            bit_of(t, "x7", "x7", 12)

            def cleared() -> None:
                t.li("x6", 7)
                t.li("x8", -3)
                lab = L.word_window(
                    t,
                    "M",
                    (1 << 25) | (8 << 20) | (6 << 15) | (7 << 7) | 0x33,
                    "mul x7, x6, x8",
                    "ok",
                    "mul with misa.M = 0 and Zmmul",
                )
                t.check("x7", -21, lab, "mul 7, -3 with misa.M = 0")
                lab = L.word_window(
                    t,
                    "M",
                    (1 << 25) | (8 << 20) | (6 << 15) | (1 << 12) | (7 << 7) | 0x33,
                    "mulh x7, x6, x8",
                    "ok",
                    "mulh with misa.M = 0 and Zmmul",
                )
                t.check("x7", -1, lab, "mulh 7, -3 with misa.M = 0")
                L.word_window(
                    t,
                    "M",
                    (1 << 25) | (8 << 20) | (6 << 15) | (4 << 12) | (7 << 7) | 0x33,
                    "div x7, x6, x8",
                    2,
                    "div with misa.M = 0",
                )
                t.emit("csrw misa, x9")

            L.either(t, "x7", lambda: t.emit("csrw misa, x9"), cleared)

        L.either(t, "x7", m_set, lambda: None)
    tests.append(t)

    # ---- misa_extensions_dependencies ----
    t = new(suite, "misa_extensions_dependencies")
    describe(
        t,
        context="D depends on F and Q depends on D. Writes clear only the depended-on letter; whether they take "
        "effect is WARL.",
        plan="1. With F and D set, clear F: if misa then reads F = 0, D also reads 0.\n2. The same for D under Q."
        "\n3. misa is restored after each.",
    )
    t.emit("csrr x9, misa")
    for y, ybit, x, xbit, cond in (("F", 5, "D", 3, "defined(D_SUPPORTED)"), ("D", 3, "Q", 16, "defined(Q_SUPPORTED)")):
        with t.only_if(cond):
            lab = t.label("dep")
            t.load("x6", 1 << ybit, f"misa.{y}")
            t.emit(f"{lab}:", 0)
            t.emit("csrc misa, x6")
            t.emit("csrr x7, misa")
            t.emit("csrw misa, x9")
            bit_of(t, "x8", "x7", ybit)
            bit_of(t, "x7", "x7", xbit)
            if mut() != "misa_dep_kept":  # the mutant expects y = 1 or x = 1 (x kept enabled)
                t.emit("xori x7, x7, 1")
            t.emit("or x7, x7, x8")
            t.check_bool("x7", lab, f"after clearing misa.{y}: {y} = 1 or {x} = 0")
    tests.append(t)

    # ---- misa_inc_ialign ----
    t = new(suite, "misa_inc_ialign")
    describe(
        t,
        context="Needs a writable misa.C. A csrc that would clear C is placed at an address = 2 mod 4 (after a "
        "c.nop), so the next instruction is not 4-byte aligned: the write must be suppressed. The same csrc at a "
        "4-byte boundary followed by an aligned instruction may take effect.",
        plan="1. csrc misa, C at 2 mod 4: misa is unchanged (C still set), and execution continues with the "
        "following 16-bit c.nop.\n2. csrc misa, C at a 4-byte boundary: misa.C reads 0 or 1 (writable or not).\n"
        "3. misa is restored and reads its original value.",
    )
    with t.only_if("defined(C_SUPPORTED)"):
        t.emit("csrr x9, misa")
        bit_of(t, "x7", "x9", 2)

        def run() -> None:
            t.li("x6", 4)
            lab = t.label("misal")
            t.emit(".p2align 2", 0)
            t.emit(".hword 0x0001  // c.nop: the csrc below is at 2 mod 4", 1)
            t.emit(f"{lab}:", 0)
            t.emit("csrc misa, x6")
            t.emit(".hword 0x0001  // c.nop at 2 mod 4: realigns", 1)
            t.emit("csrr x7, misa")
            t.emit("andi x7, x7, 4")
            t.check(
                "x7",
                0 if mut() == "misa_ialign_not_suppressed" else 4,
                lab,
                "misa.C write suppressed when the next instruction is at 2 mod 4",
            )
            lab = t.label("al")
            t.emit(".p2align 2", 0)
            t.emit(f"{lab}:", 0)
            t.emit("csrc misa, x6")
            t.emit("csrr x7, misa")
            t.emit("andi x7, x7, 4")
            t.check("x7", [0, 4], lab, "misa.C after csrc at an aligned address (WARL)")
            t.emit("csrw misa, x9")
            t.emit("csrr x7, misa")
            t.emit("sub x7, x7, x9")
            t.check("x7", 0, lab, "misa restored")

        L.either(t, "x7", run, lambda: None)
    tests.append(t)
    return tests


# ---------------------------------------------------------------- mstatus
def mpp_legal(s: bool, u: bool) -> list[int]:
    return [3] + ([1] if s else []) + ([0] if u else [])


HARTS = [  # (condition, S, U) for the three kinds of hart these tests distinguish
    (f"{S} && {U}", True, True),
    (f"{NO_S} && {U}", False, True),
    (f"{NO_S} && {NO_U}", False, False),
]


def set_field(t: TestFile, csr: str, mask: int, value: int, tmp: str = "x7", tmp2: str = "x8") -> None:
    """csr = (csr & ~mask) | value with one csrw (other fields keep their current values)."""
    t.emit(f"csrr {tmp}, {csr}")
    t.load(tmp2, X(~mask & 0xFFFFFFFF, ~mask & ((1 << 64) - 1)), f"~{hex(mask)}")
    t.emit(f"and {tmp}, {tmp}, {tmp2}")
    if value:
        t.load(tmp2, value, hex(value))
        t.emit(f"or {tmp}, {tmp}, {tmp2}")
    t.emit(f"csrw {csr}, {tmp}")


def field(t: TestFile, reg: str, csr: str, mask: int, shift: int) -> None:
    t.emit(f"csrr {reg}, {csr}")
    t.emit(f"srli {reg}, {reg}, {shift}")
    t.emit(f"andi {reg}, {reg}, {mask >> shift}")


def gen_mstatus(suite: str) -> list[TestFile]:
    tests = []

    # ---- mstatus_sie_spie_rdonly0 ----
    t = new(suite, "mstatus_sie_spie_rdonly0")
    describe(
        t,
        context="mie (the CSR) is 0 at boot, so setting mstatus.MIE cannot take an interrupt.",
        plan="1. Set and clear MIE and MPIE (csrs/csrc): each reads back as written.\n2. With S-mode: SIE and SPIE "
        "read back as written. Without S-mode: after csrs of SIE and SPIE both read 0.",
    )
    t.emit("csrw mie, x0")
    bits = [("MIE", MIE, None), ("MPIE", MPIE, None), ("SIE", SIE, S), ("SPIE", SPIE, S)]
    for name, b, cond in bits:

        def wr(name: str = name, b: int = b) -> None:
            for on in (1, 0):
                lab = t.label(name)
                t.li("x6", b)
                t.emit(f"{lab}:", 0)
                t.emit(f"csr{'s' if on else 'c'} mstatus, x6")
                t.emit("csrr x7, mstatus")
                t.check_masked("x7", b, b if on else 0, lab, f"mstatus.{name} after csr{'s' if on else 'c'}")

        guard(t, cond, wr)
    with t.only_if(NO_S):
        lab = t.label("ro")
        t.li("x6", SIE | SPIE)
        t.emit(f"{lab}:", 0)
        t.emit("csrs mstatus, x6")
        t.emit("csrr x7, mstatus")
        t.check_masked(
            "x7",
            SIE | SPIE,
            SIE | SPIE if mut() == "sie_writable_no_s" else 0,
            lab,
            "SIE and SPIE are read-only 0 without S-mode",
        )
    tests.append(t)

    # ---- mstatus_xpp_warl ----
    t = new(suite, "mstatus_xpp_warl")
    describe(
        t,
        context="MPP can hold M and every implemented lower mode; 2 is never legal. SPP can hold S and U. Each "
        "write is one csrw of mstatus with only xPP changed. An illegal value reads back as one of the legal "
        "ones (WARL).",
        plan="1. Write MPP = 0, 1, 2, 3: a legal value reads back as written; an illegal one reads back as a legal "
        "value (M, S if implemented, U if implemented).\n2. With S-mode: SPP = 0 and 1 read back as written.",
    )
    for cond, s, u in HARTS:

        def body(s: bool = s, u: bool = u) -> None:
            legal = mpp_legal(s, u)
            for v in range(4):
                lab = t.label("mpp")
                t.emit(f"{lab}:", 0)
                set_field(t, "mstatus", MPP, v << 11)
                field(t, "x7", "mstatus", MPP, 11)
                exp = v if v in legal else legal
                if mut() == "mpp_keeps_2" and v == 2:
                    exp = 2
                t.check("x7", exp, lab, f"MPP after writing {v}")
            if s:
                for v in (1, 0):
                    lab = t.label("spp")
                    t.emit(f"{lab}:", 0)
                    set_field(t, "mstatus", SPP, v << 8)
                    field(t, "x7", "mstatus", SPP, 8)
                    t.check("x7", v, lab, f"SPP after writing {v}")

        with t.only_if(cond):
            body()
    tests.append(t)

    # ---- mstatus_xpp_rdonly0 ----
    t = new(suite, "mstatus_xpp_rdonly0")
    describe(
        t,
        context="MPP always exists. SPP exists only with S-mode.",
        plan="1. Without S-mode: SPP reads 0 after csrs of SPP.",
    )
    with t.only_if(NO_S):
        lab = t.label("spp")
        t.li("x6", SPP)
        t.emit(f"{lab}:", 0)
        t.emit("csrs mstatus, x6")
        field(t, "x7", "mstatus", SPP, 8)
        t.check("x7", 0, lab, "SPP is read-only 0 without S-mode")
    tests.append(t)

    # ---- mstatus_xpie_xie_xpp_trap_op ----
    t = new(suite, "mstatus_xpie_xie_xpp_trap_op")
    describe(
        t,
        context="mie = 0, so MIE = 1 enables no interrupt. Before entering S or U, MPIE is set to the value MRET "
        "will copy into MIE. Traps into S-mode use medeleg[3] (breakpoint), where it is writable, and SIE is "
        "set before MRET (MRET does not change SIE). The handlers log xstatus as it was on entry.",
        plan="1. ebreak in M, S and U with xIE = 0 and 1 before the trap, trapping into M: MPIE = old MIE, "
        "MIE = 0, MPP = the mode the trap came from.\n2. With S-mode and medeleg[3] writable: ebreak in S and U "
        "trapping into S: SPIE = old SIE, SIE = 0, SPP = the mode the trap came from.",
    )
    t.emit("csrw mie, x0")
    for mode in ("M", "S", "U"):

        def into_m(mode: str = mode) -> None:
            for ie in (0, 1):
                if mode == "M":
                    L.csr_bits(t, "mstatus", MIE, bool(ie))
                else:
                    L.csr_bits(t, "mstatus", MPIE, bool(ie))
                lab = L.win(t, mode, [".word 0x00100073  // ebreak"], 3, f"ebreak with MIE = {ie}", [0, "LAB"])
                pp = {"M": 3, "S": 1, "U": 0}[mode]
                if mut() == "trap_mpp_m":
                    pp = 3
                L.check_log(
                    t,
                    "TRAPLOG_STATUS",
                    MIE | MPIE | MPP,
                    (ie * MPIE) | (pp << 11),
                    lab,
                    f"trap from {mode} with MIE = {ie}: MPIE = {ie}, MIE = 0, MPP = {pp}",
                )
                L.csr_bits(t, "mstatus", MIE, False)

        L.guard(t, L.MODE_COND[mode], into_m)
    with t.only_if(S):
        t.li("x6", 8)
        t.emit("csrs medeleg, x6")
        t.emit("csrr x7, medeleg")
        t.emit("andi x7, x7, 8")

        def into_s() -> None:
            for mode in ("S", "U"):
                for ie in (0, 1):
                    L.csr_bits(t, "mstatus", SIE, bool(ie))
                    lab = L.win(
                        t, mode, [".word 0x00100073  // ebreak"], 3, f"delegated ebreak with SIE = {ie}", [0, "LAB"]
                    )
                    L.check_handler(t, "S", lab, "delegated ebreak")
                    pp = {"S": 1, "U": 0}[mode]
                    L.check_log(
                        t,
                        "TRAPLOG_STATUS",
                        SIE | SPIE | SPP,
                        (ie * SPIE) | (pp << 8),
                        lab,
                        f"trap from {mode} into S with SIE = {ie}: SPIE = {ie}, SIE = 0, SPP = {pp}",
                    )
            t.emit("csrw medeleg, x0")
            L.csr_bits(t, "mstatus", SIE, False)

        L.either(t, "x7", into_s, lambda: None)
    tests.append(t)

    # ---- mstatus_xret_op ----
    t = new(suite, "mstatus_xret_op")
    describe(
        t,
        context="An MRET with MPP = M stays in M-mode, so the whole effect is read back in M-mode. For an MRET to "
        "S or U, an ebreak there shows MIE (now in MPIE) on handler entry. An SRET from M-mode to S-mode is read "
        "back in S-mode. The least-privileged mode is U on harts with U, else M.",
        plan="1. MRET with MPP = M, MPIE = 0/1 and MIE = 1/0: MIE = old MPIE, MPIE = 1, MPP = U (M without "
        "U-mode), and execution continues at mepc.\n"
        "2. MRET to S and U with MPIE = 0/1: an ebreak there logs MPIE = the MIE that MRET set.\n"
        "3. With S-mode, SRET executed in M-mode with SPP = S, SPIE = 0/1 and SIE = 1/0: in S-mode at sepc, "
        "SIE = old SPIE, SPIE = 1, SPP = U.",
    )
    t.emit("csrw mie, x0")
    for pie in (0, 1):
        for cond, u in ((U, True), (NO_U, False)):
            with t.only_if(cond):
                lab, after = t.label("mret"), t.label("mret_to")
                L.csr_bits(t, "mstatus", MPP, True)
                L.csr_bits(t, "mstatus", MPIE, bool(pie))
                L.csr_bits(t, "mstatus", MIE, not pie)
                t.la("x6", after)
                t.emit("csrw mepc, x6")
                t.emit(f"{lab}:", 0)
                t.emit("mret")
                t.emit(f"{after}:", 0)
                t.emit("csrr x7, mstatus")
                pp = 0 if u else 3
                kept = pie * MPIE if mut() == "mret_pie_kept" else MPIE
                exp = (pie * MIE) | kept | (pp << 11)
                t.check_masked(
                    "x7",
                    MIE | MPIE | MPP,
                    exp,
                    lab,
                    f"after MRET (MPP=M, MPIE={pie}): MIE = {pie}, MPIE = 1, MPP = {pp}",
                )
                L.csr_bits(t, "mstatus", MIE, False)
        for mode in ("S", "U"):

            def to_low(mode: str = mode, pie: int = pie) -> None:
                L.csr_bits(t, "mstatus", MPIE, bool(pie))
                lab = L.win(
                    t, mode, [".word 0x00100073  // ebreak"], 3, f"ebreak after MRET with MPIE = {pie}", [0, "LAB"]
                )
                L.check_log(
                    t,
                    "TRAPLOG_STATUS",
                    MPIE,
                    pie * MPIE,
                    lab,
                    f"MRET to {mode} with MPIE = {pie} set MIE = {pie} (seen as MPIE on the next trap)",
                )

            L.guard(t, L.MODE_COND[mode], to_low)
    with t.only_if(S):
        for pie in (0, 1):
            lab, after = t.label("sret"), t.label("sret_to")
            L.csr_bits(t, "mstatus", SPP, True)
            L.csr_bits(t, "mstatus", SPIE, bool(pie))
            L.csr_bits(t, "mstatus", SIE, not pie)
            t.la("x6", after)
            t.emit("csrw sepc, x6")
            t.emit(f"{lab}:", 0)
            t.emit("sret")
            t.emit(f"{after}:", 0)
            t.emit("csrr x7, sstatus")
            t.check_masked(
                "x7",
                SIE | SPIE | SPP,
                (pie * SIE) | SPIE,
                lab,
                f"SRET from M-mode (SPP=S, SPIE={pie}): in S-mode SIE = {pie}, SPIE = 1, SPP = U",
            )
            t.leave()
            L.csr_bits(t, "mstatus", SIE, False)
    tests.append(t)

    # ---- mstatus_mprv_clr_mret_sret_less_priv ----
    t = new(suite, "mstatus_mprv_clr_mret_sret_less_priv", [*L.REQ, "U"])
    describe(
        t,
        context="MPRV exists only with U-mode. With MPRV = 1 and MPP = U, M-mode loads use U-mode protection; the "
        "framework's PMP setup gives U-mode the whole address space, so the test's own loads still work.",
        plan="1. MRET to U and (with S) to S with MPRV = 1: an ebreak there logs MPRV = 0.\n"
        "2. MRET with MPP = M and MPRV = 1: MPRV stays 1.\n"
        "3. With S-mode, SRET from M-mode to S and to U with MPRV = 1: MPRV = 0 (S: read through T-SBI; U: on "
        "the next trap).",
    )
    for mode in ("U", "S"):

        def mprv_low(mode: str = mode) -> None:
            L.csr_bits(t, "mstatus", MPRV, True)
            lab = L.win(
                t, mode, [".word 0x00100073  // ebreak"], 3, f"ebreak after MRET to {mode} with MPRV = 1", [0, "LAB"]
            )
            exp = MPRV if mut() == "mret_keeps_mprv" else 0
            L.check_log(t, "TRAPLOG_STATUS", MPRV, exp, lab, f"MRET to {mode} cleared MPRV")

        L.guard(t, L.MODE_COND[mode], mprv_low)
    lab, after = t.label("mretm"), t.label("mretm_to")
    L.csr_bits(t, "mstatus", MPP, True)
    L.csr_bits(t, "mstatus", MPRV, True)
    t.la("x6", after)
    t.emit("csrw mepc, x6")
    t.emit(f"{lab}:", 0)
    t.emit("mret")
    t.emit(f"{after}:", 0)
    t.emit("csrr x7, mstatus")
    L.csr_bits(t, "mstatus", MPRV, False)
    t.check_masked("x7", MPRV, MPRV, lab, "MRET to M-mode keeps MPRV = 1")
    with t.only_if(S):
        for spp in (1, 0):
            lab, after = t.label("sret"), t.label("sret_to")
            L.csr_bits(t, "mstatus", SPP, bool(spp))
            L.csr_bits(t, "mstatus", MPRV, True)
            t.la("x6", after)
            t.emit("csrw sepc, x6")
            if spp:
                t.emit(f"{lab}:", 0)
                t.emit("sret")
                t.emit(f"{after}:", 0)
                t.tsbi_csr("READ", "MSTATUS")
                t.check_masked("a0", MPRV, 0, lab, "SRET from M-mode to S cleared MPRV")
                t.leave()
            else:
                t.allow(1)
                t.emit(f"{lab}:", 0)
                t.emit("sret")
                t.emit(f"{after}:", 0)
                t.emit(".word 0x00100073  // ebreak in U")
                t.leave()
                t.outcome(3, after, "ebreak in U after SRET from M-mode", [0, after], origin="U")
                L.check_log(t, "TRAPLOG_STATUS", MPRV, 0, lab, "SRET from M-mode to U cleared MPRV")
    tests.append(t)

    # ---- mstatus_mprv_rdonly0_no_umode ----
    t = new(suite, "mstatus_mprv_rdonly0_no_umode")
    describe(
        t,
        plan="1. Without U-mode: MPRV reads 0 after csrs.\n2. With U-mode: MPRV reads 1 after csrs and 0 after csrc.",
    )
    for cond, u in ((NO_U, False), (U, True)):
        with t.only_if(cond):
            for on in (1, 0) if u else (1,):
                lab = t.label("mprv")
                t.li("x6", MPRV)
                t.emit(f"{lab}:", 0)
                t.emit(f"csr{'s' if on else 'c'} mstatus, x6")
                t.emit("csrr x7, mstatus")
                t.emit("csrc mstatus, x6")
                exp = MPRV if (u and on) else 0
                if mut() == "mprv_writable_no_u" and not u:
                    exp = MPRV
                t.check_masked("x7", MPRV, exp, lab, f"MPRV after csr{'s' if on else 'c'}")
    tests.append(t)

    # ---- satp-dependent read-only zeros: MXR, SUM, TVM ----
    for rule, bit, name in (
        ("mstatus_mxr_rdonly0_no_smode", MXR, "MXR"),
        ("mstatus_sum_rdonly0", SUM, "SUM"),
        ("mstatus_tvm_acc", TVM, "TVM"),
    ):
        t = new(suite, rule)
        describe(
            t,
            context="satp.MODE is probed by writing each translation mode (Sv32 on RV32; Sv39, Sv48, Sv57 on RV64) "
            "and reading it back; satp is left 0.",
            plan=f"1. Without S-mode, or when satp.MODE is read-only 0: {name} reads 0 after csrs.\n"
            f"2. Otherwise {name} reads 1 after csrs and 0 after csrc.",
        )
        L.satp_probe(t, "x8")
        lab = t.label("f")
        t.li("x6", bit)
        t.emit(f"{lab}:", 0)
        t.emit("csrs mstatus, x6")
        t.emit("csrr x7, mstatus")
        t.emit("csrc mstatus, x6")
        t.emit("csrr x9, mstatus")
        t.emit("and x7, x7, x6")
        t.emit("snez x7, x7")
        t.emit("xor x7, x7, x8")
        if mut() == "satp_ro_field_writable":
            t.emit("xor x7, x7, x8")
        t.emit("seqz x7, x7")
        t.check_bool("x7", lab, f"{name} is writable exactly when S-mode and a translation mode exist")
        t.check_masked("x9", bit, 0, lab, f"{name} reads 0 after csrc")
        tests.append(t)

    for rule, bit, name, cond, what in (
        ("mstatus_tsr_acc", TSR, "TSR", S, "S-mode"),
        ("mstatus_tw_acc", TW, "TW", U, "a mode below M"),
    ):
        t = new(suite, rule)
        describe(
            t,
            plan=f"1. Without {what}: {name} reads 0 after csrs.\n2. With {what}: {name} reads 1 after "
            f"csrs and 0 after csrc.",
        )
        for c, on_exp in ((cond, True), (f"!({cond})", False)):
            with t.only_if(c):
                lab = t.label("f")
                t.li("x6", bit)
                t.emit(f"{lab}:", 0)
                t.emit("csrs mstatus, x6")
                t.emit("csrr x7, mstatus")
                t.emit("csrc mstatus, x6")
                t.emit("csrr x9, mstatus")
                t.check_masked("x7", bit, bit if on_exp else 0, lab, f"{name} after csrs")
                t.check_masked("x9", bit, 0, lab, f"{name} after csrc")
        tests.append(t)
    return tests


# ---------------------------------------------------------------- traps, delegation, trap CSRs
ILLEGAL = 0xC0001073  # csrrw x0, cycle, x0: a write to a read-only (or absent) CSR, bit 31 set
ECALL_CAUSE = {"U": 8, "S": 9, "M": 11}


def ecall_lines() -> list[str]:
    return ["li a0, 0x73  // TSBI_ECALL_TEST", "ecall"]


def gen_traps(suite: str) -> list[TestFile]:
    tests = []

    # ---- trap_def_m_mode ----
    t = new(suite, "trap_def_m_mode")
    describe(
        t,
        context="The M-mode boot leaves medeleg = mideleg = 0.",
        plan="1. With medeleg = 0: ebreak, an illegal instruction and ecall from M, S and U are taken in M-mode "
        "with their causes (3, 2, 11/9/8).\n2. With mideleg = 0: a supervisor software interrupt (S-mode harts) "
        "taken from S and U goes to M-mode.",
    )

    def traps(mode: str) -> None:
        lab = L.win(t, mode, [L.EBREAK], 3, "ebreak", [0, "LAB"])
        L.check_handler(t, "M", lab, "ebreak with medeleg = 0")
        lab = L.word_window(t, mode, ILLEGAL, "csrrw x0, cycle, x0", 2, "illegal instruction")
        L.check_handler(t, "M", lab, "illegal instruction with medeleg = 0")
        lab = t.label(f"ec{mode}")
        t.allow(1)
        if mode != "M":
            t.enter(mode)
        t.emit("li a0, 0x73  // TSBI_ECALL_TEST")
        t.emit(f"{lab}:", 0)
        t.emit("ecall")
        if mode != "M":
            t.leave()
        t.outcome(ECALL_CAUSE[mode], lab, f"ecall in {mode}-mode", 0, origin=mode)
        L.check_handler(t, "M", lab, "ecall with medeleg = 0")

    L.each_mode(t, traps)
    with t.only_if(S):
        for mode in ("S", "U"):
            t.allow(1)
            t.emit("csrci mstatus, 8  // MIE = 0: a T-SBI return to M-mode leaves MIE = 1")
            t.emit("csrsi mie, 2")
            t.emit("csrsi mip, 2")
            t.enter(mode)
            lab = t.label("ssi")
            t.emit(f"{lab}:", 0)
            L.wait(t, 50)
            t.leave()
            t.outcome(L.icause(1), lab, f"SSI pending in {mode}-mode with mideleg = 0", epc=False, origin=mode)
            L.check_handler(t, "M", lab, "SSI with mideleg = 0")
            t.emit("csrci mip, 2")
            t.emit("csrci mie, 2")
    tests.append(t)

    # ---- delegation group ----
    deleg_ctx = (
        "medeleg[3] (breakpoint) and mideleg[1] (SSI) are WARL: each case first sets the bit and runs only "
        "if it reads back as 1. Delegation is cleared at the end."
    )

    def deleg_on(t: TestFile, csr: str, bit: int) -> None:
        t.li("x6", 1 << bit)
        t.emit(f"csrs {csr}, x6")
        t.emit(f"csrr x7, {csr}")
        t.emit("and x7, x7, x6")

    t = new(suite, "medeleg_mideleg_delegate_op", [*L.REQ, "S"])
    describe(
        t,
        context=deleg_ctx,
        plan="1. medeleg[3] = 1: ebreak in S and U is taken in S-mode (scause 3).\n2. mideleg[1] = 1: SSI pending and "
        "enabled (sie.SSIE, sstatus.SIE = 1) in S, and pending in U, is taken in S-mode.",
    )
    deleg_on(t, "medeleg", 3)

    def eb_s() -> None:
        for mode in ("S", "U"):
            lab = L.win(t, mode, [L.EBREAK], 3, "ebreak with medeleg[3] = 1", [0, "LAB"])
            L.check_handler(t, "M" if mut() == "deleg_ignored" else "S", lab, "ebreak with medeleg[3] = 1")
        t.emit("csrw medeleg, x0")

    L.either(t, "x7", eb_s, lambda: None)
    deleg_on(t, "mideleg", 1)

    def ssi_s() -> None:
        for mode in ("S", "U"):
            t.allow(1)
            t.emit("csrci mstatus, 8  // MIE = 0")
            t.emit("csrsi mie, 2")
            t.emit("csrsi mstatus, 2  // SIE")
            t.emit("csrsi mip, 2")
            t.enter(mode)
            lab = t.label("ssi")
            t.emit(f"{lab}:", 0)
            L.wait(t, 50)
            t.leave()
            t.outcome(L.icause(1), lab, f"delegated SSI in {mode}-mode", epc=False, origin=mode)
            L.check_handler(t, "S", lab, "SSI with mideleg[1] = 1")
            t.emit("csrci mip, 2")
            t.emit("csrci mie, 2")
            t.emit("csrci mstatus, 2")
        t.emit("csrw mideleg, x0")

    L.either(t, "x7", ssi_s, lambda: None)
    tests.append(t)

    t = new(suite, "trap_del_s_mode_op", [*L.REQ, "S"])
    describe(
        t,
        context="medeleg[3] (breakpoint) is WARL: the test runs only if it reads back as 1. The S handler logs "
        "scause, sepc, stval and sstatus as they were on entry.",
        plan="1. medeleg[3] = 1: ebreak in U with SIE = 1 and in S with SIE = 0: scause = 3, sepc = the ebreak, "
        "stval = 0 or its address, SPP = the mode it came from, SPIE = old SIE, SIE = 0.\n2. medeleg[3] = 1 and "
        "an illegal instruction: still taken in M-mode (medeleg[2] = 0), so one bit delegates one cause.",
    )
    deleg_on(t, "medeleg", 3)

    def del_s() -> None:
        for mode, ie in (("U", 1), ("S", 0), ("S", 1), ("U", 0)):
            L.csr_bits(t, "mstatus", SIE, bool(ie))
            lab = L.win(t, mode, [L.EBREAK], 3, f"delegated ebreak with SIE = {ie}", [0, "LAB"])
            L.check_handler(t, "S", lab, "delegated ebreak")
            pp = 1 if mode == "S" else 0
            L.check_log(
                t,
                "TRAPLOG_STATUS",
                SIE | SPIE | SPP,
                (ie * SPIE) | (pp << 8),
                lab,
                f"sstatus after a delegated trap from {mode} with SIE = {ie}",
            )
        lab = L.word_window(t, "U", ILLEGAL, "csrrw x0, cycle, x0", 2, "illegal instruction with medeleg[3] only")
        L.check_handler(t, "M", lab, "illegal instruction is not delegated by medeleg[3]")
        t.emit("csrw medeleg, x0")
        L.csr_bits(t, "mstatus", SIE, False)

    L.either(t, "x7", del_s, lambda: None)
    tests.append(t)

    t = new(suite, "trap_del_s_mode_no_m_mode", [*L.REQ, "S"])
    describe(
        t,
        context="medeleg[3] (breakpoint) is WARL: the test runs only if it reads back as 1. Only a trap can bring "
        "the hart back to M-mode, and that trap rewrites mepc, mcause, "
        "mtval, MPP, MPIE and MIE, so the observable part is mstatus.MIE: a delegated trap that wrongly performed "
        "the M-mode stack update would clear MIE, which the next trap into M-mode records in MPIE. mie = 0, so "
        "MIE = 1 in S or U enables nothing.",
        plan="1. MRET to S and to U with MPIE = 1 (so MIE = 1 there), then a delegated ebreak taken in S-mode.\n"
        "2. The T-SBI return to M-mode logs MPIE = 1 and MPP = the mode it came from: the delegated trap did not "
        "touch MIE.",
    )
    t.emit("csrw mie, x0")
    deleg_on(t, "medeleg", 3)

    def no_m() -> None:
        for mode in ("S", "U"):
            L.csr_bits(t, "mstatus", MPIE, True)
            lab = t.label("del")
            t.allow(2)
            t.enter(mode)
            t.emit(f"{lab}:", 0)
            t.emit(L.EBREAK)
            t.emit("li a0, 0x73  // TSBI_ECALL_TEST: a logged trap into M-mode")
            ec = t.label("ec")
            t.emit(f"{ec}:", 0)
            t.emit("ecall")
            t.leave()
            t.emit("AI_OUTCOME", 20)
            t.check("x13", 2, lab, f"delegated ebreak then ecall in {mode}-mode: two traps")
            L.check_handler(t, "S", lab, "delegated ebreak", back=1)
            L.check_handler(t, "M", ec, "ecall")
            exp = 0 if mut() == "deleg_writes_m_stack" else MPIE
            L.check_log(
                t,
                "TRAPLOG_STATUS",
                MPIE | MPP,
                exp | ((1 if mode == "S" else 0) << 11),
                ec,
                f"ecall after a delegated trap in {mode}: MPIE = 1 (MIE was not cleared), MPP = {mode}",
            )
        t.emit("csrw medeleg, x0")

    L.either(t, "x7", no_m, lambda: None)
    tests.append(t)
    return tests


def gen_traps2(suite: str) -> list[TestFile]:
    tests = []

    def deleg_on(t: TestFile, csr: str, bit: int) -> None:
        t.li("x6", 1 << bit)
        t.emit(f"csrs {csr}, x6")
        t.emit(f"csrr x7, {csr}")
        t.emit("and x7, x7, x6")

    # ---- trap_never_trans_lower / trap_horiz ----
    for rule, mode, handler in (("trap_never_trans_lower", "M", "M"), ("trap_horiz", "S", "S")):
        t = new(suite, rule, [*L.REQ, "S"])
        describe(
            t,
            context="medeleg[3] (breakpoint) is WARL; the case runs only if it reads back as 1.",
            plan=f"1. medeleg[3] = 1 and ebreak in {mode}-mode: taken in {handler}-mode with cause 3, from {mode}.",
        )
        deleg_on(t, "medeleg", 3)

        def body(mode: str = mode, handler: str = handler, t: TestFile = t) -> None:
            lab = L.win(t, mode, [L.EBREAK], 3, "ebreak with medeleg[3] = 1", [0, "LAB"])
            h = handler
            if mut() == "deleg_from_m" and mode == "M":
                h = "S"
            L.check_handler(t, h, lab, f"ebreak in {mode}-mode with medeleg[3] = 1")
            t.emit("csrw medeleg, x0")

        L.either(t, "x7", body, lambda: None)
        tests.append(t)

    # ---- medeleg/mideleg WARL rules ----
    t = new(suite, "medeleg_mideleg_warl", [*L.REQ, "S"])
    describe(
        t,
        context="The delegatable bits are the ones that read 1 after writing all ones. They are individual "
        "read/write bits (medeleg_mideleg_per_bit_rw), so any subset of them can be written.",
        plan="1. Write all ones to medeleg and to mideleg and read back the delegatable set D; write 0 and read back "
        "the read-only-one set Z (mideleg may fix lower-level interrupt bits to 1, mideleg_rd1_lower_level).\n"
        "2. Write D & 0x55..55, D & 0xAA..AA, D and 0: each reads back as written, OR Z.\n3. Both are left 0.",
    )
    for csr in ("medeleg", "mideleg"):
        lab = t.label(csr)
        t.emit(f"{lab}:", 0)
        t.emit("li x6, -1")
        t.emit(f"csrw {csr}, x6")
        t.emit(f"csrr x9, {csr}")
        t.emit(f"csrw {csr}, x0")
        t.emit(f"csrr x8, {csr}")
        for pat, note in (
            (X(0x55555555, 0x5555555555555555), "0x55..55"),
            (X(0xAAAAAAAA, 0xAAAAAAAAAAAAAAAA), "0xAA..AA"),
            (ALL, "all ones"),
            (0, "zero"),
        ):
            t.load("x6", pat, note)
            t.emit("and x6, x6, x9")
            t.emit(f"csrw {csr}, x6")
            t.emit(f"csrr x7, {csr}")
            t.emit("or x6, x6, x8")
            t.emit("xor x7, x7, x6")
            t.check("x7", 0, lab, f"{csr} reads back (D & {note}) | Z")
        t.emit(f"csrw {csr}, x0")
    tests.append(t)

    t = new(suite, "medeleg_no_rd1", [*L.REQ, "S"])
    describe(
        t,
        context="medelegh exists from privileged architecture 1.13 (Sm1p13).",
        plan="1. After writing 0 to medeleg (and medelegh on RV32 with Sm1p13) it reads 0.",
    )
    lab = t.label("z")
    t.emit("li x6, -1")
    t.emit("csrw medeleg, x6")
    t.emit(f"{lab}:", 0)
    t.emit("csrw medeleg, x0")
    t.emit("csrr x7, medeleg")
    t.check("x7", 0, lab, "medeleg reads 0 after writing 0")
    with t.only_if(f"{RV32} && defined(SM1P13P0_OR_LATER_SUPPORTED)"):
        t.emit("csrw 0x312, x6  // medelegh")
        t.emit("csrw 0x312, x0")
        t.emit("csrr x7, 0x312")
        t.check("x7", 0, lab, "medelegh reads 0 after writing 0")
    tests.append(t)

    for rule, bit, why in (
        ("medeleg_when_rd0", 11, "ecall from M-mode cannot occur below M"),
        ("medeleg_16_rdonly0", 16, "a double trap is not delegatable"),
    ):
        t = new(suite, rule, [*L.REQ, "S"])
        describe(
            t,
            context=why + ".",
            plan=f"1. After writing all ones to medeleg, medeleg[{bit}] reads 0; medeleg is then cleared.",
        )
        lab = t.label("b")
        t.emit("li x6, -1")
        t.emit(f"{lab}:", 0)
        t.emit("csrw medeleg, x6")
        t.emit("csrr x7, medeleg")
        t.emit("csrw medeleg, x0")
        t.check_masked("x7", 1 << bit, 0, lab, f"medeleg[{bit}] is read-only 0")
        tests.append(t)

    t = new(suite, "mideleg_no_rd1", [*L.REQ, "S"])
    describe(
        t, plan="1. After writing 0 to mideleg, the machine-level interrupt bits MSI (3), MTI (7) and MEI (11) read 0."
    )
    lab = t.label("z")
    t.emit("li x6, -1")
    t.emit("csrw mideleg, x6")
    t.emit(f"{lab}:", 0)
    t.emit("csrw mideleg, x0")
    t.emit("csrr x7, mideleg")
    t.check_masked("x7", 0x888, 0, lab, "mideleg MSI/MTI/MEI bits read 0 after writing 0")
    tests.append(t)

    t = new(suite, "medelegh_sz_acc_enc_xlen32", [*L.REQ, "S"])
    describe(
        t,
        context="RV32 only (the file passes trivially on RV64); medelegh exists from privileged architecture 1.13 "
        "(Sm1p13).",
        plan="1. RV32 with Sm1p13: write all ones to medelegh: medeleg (bits 31:0) does not change, and medelegh reads back the "
        "delegatable high bits H; writing H & 0x5555.., H & 0xAAAA.. and 0 reads back exactly.",
    )
    with t.only_if(f"{RV32} && defined(SM1P13P0_OR_LATER_SUPPORTED)"):
        lab = t.label("h")
        t.emit("csrw medeleg, x0")
        t.emit(f"{lab}:", 0)
        t.emit("li x6, -1")
        t.emit("csrw 0x312, x6  // medelegh")
        t.emit("csrr x9, 0x312")
        t.emit("csrr x7, medeleg")
        t.check("x7", 0, lab, "medeleg unchanged by a medelegh write")
        for pat in (0x55555555, 0xAAAAAAAA, 0):
            t.load("x6", pat)
            t.emit("and x6, x6, x9")
            t.emit("csrw 0x312, x6")
            t.emit("csrr x7, 0x312")
            t.emit("xor x7, x7, x6")
            t.check("x7", 0, lab, f"medelegh reads back H & {hex(pat)}")
    tests.append(t)

    t = new(suite, "medelegh_omit_xlen64", [*L.REQ, "S"], rv64=True)
    describe(
        t,
        context="RV64 only.",
        plan="1. Every CSR instruction form on 0x312 (medelegh) raises illegal instruction in M-mode.",
    )
    t.li("x6", 0)
    for f in L.FORMS:
        L.csr_window(t, "M", 0x312, "medelegh", f, "ok" if mut() == "medelegh_rv64" else "illegal", "RV64")
    tests.append(t)

    t = new(suite, "medeleg_mideleg_mandatory_s_mode", [*L.REQ, "S"])
    describe(
        t,
        plan="1. medeleg and mideleg are readable and writable in M-mode (every CSR form, writing the "
        "current value 0) without a trap.",
    )
    t.emit("csrw medeleg, x0")
    t.emit("csrw mideleg, x0")
    t.li("x6", 0)
    for csr, num in (("medeleg", 0x302), ("mideleg", 0x303)):
        for f in L.FORMS:
            if "imm" in f[4] and "0x15" in f[0]:
                continue
            L.csr_window(t, "M", num, csr, f, "ok", "S-mode hart")
    t.emit("csrw medeleg, x0")
    t.emit("csrw mideleg, x0")
    tests.append(t)

    # ---- ecall / ebreak ----
    t = new(suite, "ecall_priv_mode_op")
    describe(
        t,
        context="ecall is issued as T-SBI's ECALL_TEST (a0 = 0x73), which the M handler logs like any trap. "
        "medeleg = 0.",
        plan="1. ecall in U, S and M raises cause 8, 9 and 11 (taken in M-mode) with mepc = the ecall and "
        "mtval = 0 (preset nonzero, where mtval is writable).\n2. Registers other than a0 are unchanged.",
    )

    def ec(mode: str) -> None:
        lab = t.label(f"ec{mode}")
        t.emit("li x6, 0x5a5")
        t.emit("csrw mtval, x6")
        t.li("x7", 0x123)
        t.li("x8", -7)
        t.allow(1)
        if mode != "M":
            t.enter(mode)
        t.emit("li a0, 0x73  // TSBI_ECALL_TEST")
        t.emit(f"{lab}:", 0)
        t.emit("ecall")
        if mode != "M":
            t.leave()
        cause = ECALL_CAUSE[mode]
        if mut() == "ecall_cause_u" and mode == "S":
            cause = 8
        t.outcome(cause, lab, f"ecall in {mode}-mode", 0, origin=mode)
        t.check("x7", 0x123, lab, "ecall leaves x7")
        t.check("x8", -7, lab, "ecall leaves x8")

    L.each_mode(t, ec)
    tests.append(t)

    t = new(suite, "ecall_ebreak_epc_value")
    describe(
        t,
        context="With Zca, c.ebreak is also checked (2-byte instruction).",
        plan="1. ecall, ebreak (and c.ebreak with Zca) in M, S and U: mepc = the address of the instruction itself.",
    )

    def epcs(mode: str) -> None:
        L.win(t, mode, [L.EBREAK], 3, "ebreak", [0, "LAB"])
        lab = t.label(f"ec{mode}")
        t.allow(1)
        if mode != "M":
            t.enter(mode)
        t.emit("li a0, 0x73  // TSBI_ECALL_TEST")
        t.emit(f"{lab}:", 0)
        t.emit("ecall")
        if mode != "M":
            t.leave()
        t.outcome(ECALL_CAUSE[mode], lab, f"ecall in {mode}-mode", 0, origin=mode)

    L.each_mode(t, epcs)
    with t.only_if("defined(ZCA_SUPPORTED)"):

        def cep(mode: str) -> None:
            L.win(t, mode, [".hword 0x9002  // c.ebreak", ".hword 0x0001  // c.nop"], 3, "c.ebreak", [0, "LAB"])

        L.each_mode(t, cep)
    tests.append(t)

    t = new(suite, "ebreak_debugger_transfer_op")
    describe(
        t,
        plan="1. ebreak in M, S and U raises a breakpoint exception (cause 3) and changes no register: x6-x9 keep "
        "their values.",
    )

    def ebr(mode: str) -> None:
        for r, v in (("x6", 0x111), ("x7", -2), ("x8", 0x7FF), ("x9", 0x5A5)):
            t.li(r, v)
        lab = L.win(t, mode, [L.EBREAK], 3, "ebreak", [0, "LAB"])
        for r, v in (("x6", 0x111), ("x7", -2), ("x8", 0x7FF), ("x9", 0x5A5)):
            t.check(r, v, lab, f"ebreak leaves {r}")

    L.each_mode(t, ebr)
    tests.append(t)
    return tests


def gen_trapcsrs(suite: str) -> list[TestFile]:
    tests = []

    # ---- mepc ----
    t = new(suite, "mepc_align")
    t.extra_data += [".p2align 3", "sm_mepc_data: .dword 0"]
    describe(
        t,
        context="mepc is written with patterns whose low bits are set: bit 0 must read 0, and bits 1:0 without Zca "
        "(IALIGN = 32 only). With Zca, bit 1 is not checked (it is writable while IALIGN = 16).",
        plan="1. Write mepc = a code address + 1, + 3, a data address + 1 and all ones: bit 0 reads 0 (and bit 1 "
        "without Zca).",
    )
    for src in ("code", "data", "ones"):
        for add in (1, 3) if src != "ones" else (0,):
            lab = t.label("m")
            if src == "code":
                t.la("x6", lab)
            elif src == "data":
                t.la("x6", "sm_mepc_data")
            else:
                t.emit("li x6, -1")
            if add:
                t.emit(f"addi x6, x6, {add}")
            t.emit(f"{lab}:", 0)
            t.emit("csrw mepc, x6")
            t.emit("csrr x7, mepc")
            with t.only_if("defined(ZCA_SUPPORTED)"):
                t.check_masked("x7", 1, 1 if mut() == "mepc_bit0" else 0, lab, f"mepc[0] = 0 ({src} + {add})")
            with t.only_if("!defined(ZCA_SUPPORTED)"):
                t.check_masked("x7", 3, 1 if mut() == "mepc_bit0" else 0, lab, f"mepc[1:0] = 0 ({src} + {add})")
    tests.append(t)

    t = new(suite, "mepc_warl")
    t.extra_data += [".p2align 3", "sm_mepc_data: .dword 0"]
    describe(t, plan="1. Write mepc = several valid code and data addresses (4-byte aligned): each reads back exactly.")
    for i, sym in enumerate(("CODE", "sm_mepc_data", "rvtest_trap_log", "CODE")):
        lab = t.label("w")
        t.la("x6", lab if sym == "CODE" else sym)
        if i == 3:
            t.emit("addi x6, x6, 64")
        t.emit(f"{lab}:", 0)
        t.emit("csrw mepc, x6")
        t.emit("csrr x7, mepc")
        t.emit("sub x7, x7, x6")
        t.check("x7", 0, lab, f"mepc holds the valid address {sym}")
    tests.append(t)

    for rule, csr, sent in (("mepc_op", "mepc", "LABEL"), ("mcause_op", "mcause", 13), ("mtval_op", "mtval", "LABEL")):
        t = new(suite, rule)
        describe(
            t,
            context=f"{csr} is WARL, so the sentinel is read back before the non-trapping code runs.",
            plan=f"1. Write a sentinel to {csr}, run loads, stores, arithmetic, CSR accesses to other registers and "
            f"a taken branch in M-mode without a trap: {csr} still holds the value read back.\n"
            f"2. An ebreak trap then writes {csr} (mepc = the ebreak, mcause = 3, mtval = 0 or its address).",
        )
        lab = t.label("s")
        if sent == "LABEL":
            t.la("x6", lab)
        else:
            t.li("x6", int(sent))
        t.emit(f"{lab}:", 0)
        t.emit(f"csrw {csr}, x6")
        t.emit(f"csrr x9, {csr}")
        t.la("x8", "rvtest_trap_log")
        t.emit("LREG x7, 0(x8)")
        t.emit("SREG x7, 0(x8)")
        t.emit("add x7, x7, x6")
        t.emit("csrr x7, mscratch")
        t.emit("csrr x7, mstatus")
        sk = t.label("sk")
        t.emit(f"beq x0, x0, {sk}")
        t.emit("nop")
        t.emit(f"{sk}:", 0)
        t.emit(f"csrr x7, {csr}")
        t.emit("sub x7, x7, x9")
        t.check("x7", 0, lab, f"{csr} is not written without a trap")
        L.win(t, "M", [L.EBREAK], 3, "ebreak", [0, "LAB"])
        tests.append(t)

    t = new(suite, "mepc_bit1_dyn_ialign_op")
    describe(
        t,
        context="Needs a writable misa.C. While C is disabled the test runs only 4-byte instructions at 4-byte "
        "boundaries.",
        plan="1. mepc = L + 2 (L 4-byte aligned) with C enabled reads L + 2.\n2. Clear misa.C: mepc reads L (bit 1 "
        "masked).\n3. MRET with MPP = M jumps to L (the masked value) without a trap.\n4. Set misa.C: mepc reads "
        "L + 2 again (bit 1 kept).",
    )
    with t.only_if("defined(C_SUPPORTED)"):
        t.emit("csrr x9, misa")
        t.emit("andi x7, x9, 4")

        def run() -> None:
            lab, tgt = t.label("m"), t.label("tgt")
            t.la("x8", tgt)
            t.emit("addi x6, x8, 2")
            t.emit("csrw mepc, x6")
            t.emit("csrr x7, mepc")
            t.emit("sub x7, x7, x6")
            t.check("x7", 0, lab, "mepc = L + 2 with C enabled")
            t.li("x6", 4)
            t.emit(".p2align 2", 0)
            t.emit(f"{lab}:", 0)
            t.emit("csrc misa, x6")
            t.emit("csrr x7, misa")
            t.emit("andi x7, x7, 4")

            def cleared() -> None:
                t.emit("csrr x7, mepc")
                t.emit("sub x7, x7, x8")
                t.check("x7", 2 if mut() == "mepc_bit1_unmasked" else 0, lab, "mepc reads L while C is disabled")
                L.csr_bits(t, "mstatus", MPP, True)
                t.allow(1)
                t.emit("mret")
                t.emit("nop")
                t.emit(".p2align 2", 0)
                t.emit(f"{tgt}:", 0)
                t.emit("nop")
                t.outcome("ok", tgt, "MRET to mepc = L + 2 while C is disabled")
                t.li("x6", 4)
                t.emit("csrs misa, x6")
                t.emit("addi x6, x8, 2")
                t.emit("csrr x7, mepc")
                t.emit("sub x7, x7, x6")
                t.check("x7", 0, lab, "mepc reads L + 2 again with C enabled")

            L.either(t, "x7", lambda: None, cleared)
            t.emit("csrw misa, x9")

        L.either(t, "x7", run, lambda: None)
    tests.append(t)

    # ---- mcause ----
    t = new(suite, "mcause_exccode_wlrl")
    describe(
        t,
        context="Only supported codes are guaranteed to be held: 2 (illegal instruction), 3 (breakpoint) and 11 "
        "(ecall from M) occur on every hart, 8 with U-mode and 9 with S-mode.",
        plan="1. Write each supported exception code to mcause: it reads back exactly (Interrupt bit 0).",
    )
    for code, cond in ((2, None), (3, None), (11, None), (8, U), (9, S)):

        def w(code: int = code) -> None:
            lab = t.label("c")
            t.li("x6", code)
            t.emit(f"{lab}:", 0)
            t.emit("csrw mcause, x6")
            t.emit("csrr x7, mcause")
            t.check("x7", code, lab, f"mcause holds exception code {code}")

        guard(t, cond, w)
    tests.append(t)

    t = new(suite, "mcause_sz_acc")
    describe(
        t,
        plan="1. mcause is read/write: it reads back 2 and then 3 written by csrw, and csrrs/csrrc of bit 0 "
        "change it between them.",
    )
    lab = t.label("rw")
    t.li("x6", 2)
    t.emit(f"{lab}:", 0)
    t.emit("csrw mcause, x6")
    t.emit("csrsi mcause, 1")
    t.emit("csrr x7, mcause")
    t.check("x7", 3, lab, "mcause after csrw 2, csrsi 1")
    t.emit("csrci mcause, 1")
    t.emit("csrr x7, mcause")
    t.check("x7", 2, lab, "mcause after csrci 1")
    tests.append(t)

    # misaligned LR/SC/AMO and access faults
    for rule, kind in (("mcause_exccode_ld_ldrsv", "load"), ("mcause_exccode_st_sc_amo", "store")):
        t = new(suite, rule)
        t.extra_data += [".p2align 5", "sm_amo_buf: .fill 32, 1, 0"]
        if kind == "load":
            plan = (
                "1. lw and lr.w at a misaligned address (A/Zalrsc): no trap (lw only), load-address-misaligned "
                "(4) or load-access-fault (5), never a store cause; xtval 0 or the address.\n2. lw and lr.w at "
                "RVMODEL_ACCESS_FAULT_ADDRESS: load access fault (5)."
            )
        else:
            plan = (
                "1. sw, sc.w and amoadd.w (Zaamo) at a misaligned address (amoadd.w crossing a 16-byte "
                "boundary): store-address-misaligned (6) or store-access-fault (7), never a load cause (sw may "
                "also succeed); xtval 0 or the address.\n2. sw, sc.w and amoadd.w at "
                "RVMODEL_ACCESS_FAULT_ADDRESS: store/AMO access fault (7)."
            )
        describe(t, context="Instructions are .word encodings with the address in x8.", plan=plan)
        lr = (0x02 << 27) | (8 << 15) | (2 << 12) | (7 << 7) | 0x2F
        sc = (0x03 << 27) | (6 << 20) | (8 << 15) | (2 << 12) | (7 << 7) | 0x2F
        amo = (6 << 20) | (8 << 15) | (2 << 12) | (7 << 7) | 0x2F
        lw = (8 << 15) | (2 << 12) | (7 << 7) | 0x03
        sw = (6 << 20) | (8 << 15) | (2 << 12) | 0x23
        if kind == "load":
            items = [
                (lw, "lw x7, 0(x8)", None, ["ok", 4, 5]),
                (lr, "lr.w x7, (x8)", "defined(ZALRSC_SUPPORTED)", [4, 5]),
            ]
            fa = 5
        else:
            items = [
                (sw, "sw x6, 0(x8)", None, ["ok", 6, 7]),
                (sc, "sc.w x7, x6, (x8)", "defined(ZALRSC_SUPPORTED)", [6, 7]),
                (amo, "amoadd.w x7, x6, (x8)", "defined(ZAAMO_SUPPORTED)", [6, 7]),
            ]
            fa = 7
        for e, note, cond, exp in items:

            def misal(e: int = e, note: str = note, exp: Expect = exp, t: TestFile = t) -> None:
                t.la("x8", "sm_amo_buf")
                t.emit("addi x8, x8, 14  // crosses the 16-byte boundary")
                if mut() == "lr_store_cause" and "lr" in note:
                    exp = [6, 7]
                L.word_window(t, "M", e, note, exp, f"misaligned {note}", [0, "sm_amo_buf+14"])

            guard(t, cond, misal)
        with t.only_if("defined(RVMODEL_ACCESS_FAULT_ADDRESS)"):
            for e, note, cond, exp in items:

                def af(e: int = e, note: str = note, fa: int = fa, t: TestFile = t) -> None:
                    t.emit("LI(x8, RVMODEL_ACCESS_FAULT_ADDRESS)", 2)
                    L.word_window(
                        t, "M", e, note, fa, f"{note} at the access-fault address", [0, "RVMODEL_ACCESS_FAULT_ADDRESS"]
                    )

                guard(t, cond, af)
        tests.append(t)
    return tests


def ro_csr_forms(t: TestFile, num: int, name: str, desc: str) -> None:
    """Read forms succeed; every form that writes raises illegal instruction (read-only CSR)."""
    t.li("x6", 0)
    for f in L.FORMS:
        writes = f[1] in (1, 5) or (f[1] in (2, 3) and f[3] != 0) or (f[1] in (6, 7) and f[3] != 0)
        L.csr_window(t, "M", num, name, f, "illegal" if writes else "ok", desc)


def gen_ids(suite: str) -> list[TestFile]:
    tests = []
    for rule, num, name, plan32 in (
        ("mvendorid_sz_acc_op", 0xF11, "mvendorid", True),
        ("marchid_sz_acc_op", 0xF12, "marchid", False),
        ("mhartid_sz_acc_op", 0xF14, "mhartid", False),
    ):
        t = new(suite, rule)
        describe(
            t,
            context="A write to a read-only CSR raises illegal instruction. csrrs/csrrc with rs1 = x0 and "
            "csrrsi/csrrci with uimm = 0 do not write; csrrs/csrrc with any other rs1 attempt a write even when "
            "the register holds 0 (x6 = 0 here), so they trap.",
            plan="1. csrrs rs1=x0 and csrrsi uimm=0 read without a trap; csrrw, csrrs/csrrc with rs1 = x6, csrrwi "
            "and csrrci uimm != 0 raise illegal instruction (xtval 0 or the instruction).\n"
            + ("2. RV64: mvendorid bits 63:32 read 0 (it is a 32-bit register).\n" if plan32 else "")
            + "3. Two reads return the same value.",
        )
        ro_csr_forms(t, num, name, "M-mode")
        lab = t.label("rd")
        t.emit(f"{lab}:", 0)
        t.emit(f"csrr x7, {hex(num)}")
        t.emit(f"csrr x8, {hex(num)}")
        t.emit("sub x8, x8, x7")
        t.check("x8", 0, lab, f"{name} is constant")
        if plan32:
            with t.rv64_only():
                t.emit("srli x7, x7, 32")
                t.check("x7", 0, lab, "mvendorid[63:32] = 0")
        tests.append(t)

    for rule, num, name in (
        ("mvendorid_always_rd", 0xF11, "mvendorid"),
        ("marchid_always_rd", 0xF12, "marchid"),
        ("mimpid_always_rd", 0xF13, "mimpid"),
        ("mhartid_always_rd", 0xF14, "mhartid"),
    ):
        t = new(suite, rule)
        describe(t, plan=f"1. {name} reads without a trap in M-mode (csrrs rs1=x0 and csrrsi uimm=0).")
        for f in L.READ_FORMS:
            L.csr_window(t, "M", num, name, f, "ok", "M-mode")
        tests.append(t)

    t = new(suite, "mimpid_op")
    describe(
        t,
        context="The value is free; it is read-only (Machine Information Registers are MRO).",
        plan="1. mimpid reads without a trap; writes raise illegal instruction.",
    )
    ro_csr_forms(t, 0xF13, "mimpid", "M-mode")
    tests.append(t)

    for rule, plan in (
        ("mconfigptr_sz_acc", "1. mconfigptr reads without a trap; every writing form raises illegal instruction."),
        ("mconfigptr_align", "1. mconfigptr[1:0] = 0 on RV32 and mconfigptr[2:0] = 0 on RV64."),
        ("mconfigptr_mandatory", "1. mconfigptr reads without a trap (csrrs rs1=x0, csrrsi uimm=0)."),
    ):
        t = new(suite, rule)
        describe(t, context="mconfigptr exists from privileged architecture 1.12 (Sm1p12).", plan=plan)
        with t.only_if("defined(SM1P12P0_OR_LATER_SUPPORTED)"):
            if rule == "mconfigptr_sz_acc":
                ro_csr_forms(t, 0xF15, "mconfigptr", "M-mode")
            elif rule == "mconfigptr_mandatory":
                for f in L.READ_FORMS:
                    L.csr_window(t, "M", 0xF15, "mconfigptr", f, "ok", "M-mode")
            else:
                lab = t.label("al")
                t.emit(f"{lab}:", 0)
                t.emit("csrr x7, 0xF15")
                t.check_masked("x7", X(3, 7), 0, lab, "mconfigptr is MXLEN-aligned")
        tests.append(t)

    t = new(suite, "mscratch_sz_acc")
    describe(
        t,
        context="The framework keeps its M-mode save-area pointer in mscratch, so the test saves it and restores it "
        "before any trap.",
        plan="1. Write 0, all ones, 0x55..55, 0xAA..AA, MSB only and two random values: each reads back exactly.\n"
        "2. csrrs/csrrc of single bits update it as a read/write register.\n3. mscratch is restored.",
    )
    lab = t.label("ms")
    t.emit("csrr x9, mscratch")
    vals = [0, ALL, X(0x55555555, 0x5555555555555555), X(0xAAAAAAAA, 0xAAAAAAAAAAAAAAAA), L.MSB, t.rand_x(), t.rand_x()]
    t.emit(f"{lab}:", 0)
    for v in vals:
        t.load("x6", v)
        t.emit("csrw mscratch, x6")
        t.emit("csrr x7, mscratch")
        t.emit("xor x7, x7, x6")
        t.emit("mv x8, x7")
        t.emit("csrw mscratch, x9")
        t.check("x8", 0, lab, "mscratch reads back the value written")
    t.emit("csrw mscratch, x0")
    t.emit("csrsi mscratch, 5")
    t.emit("csrci mscratch, 1")
    t.emit("csrr x8, mscratch")
    t.emit("csrw mscratch, x9")
    t.check("x8", 4, lab, "mscratch after csrw 0, csrsi 5, csrci 1")
    tests.append(t)

    # ---- mtval ----
    t = new(suite, "mtval_ill_instr_exc_in_low_bits")
    describe(
        t,
        context="csrrw x0, cycle, x0 (0xC0001073) writes a read-only CSR (or an absent one) and has bit 31 set, so "
        "an RV64 mtval that sign-extends it would read 0xFFFFFFFFC0001073. With C and D, c.fld f8, 0(x8) (0x2000) "
        "with mstatus.FS = Off is a 16-bit instruction that must raise illegal instruction (reserved encodings "
        "such as c.lwsp x0 are UNSPECIFIED, so they are not used).",
        plan="1. In M, S and U: the illegal 32-bit instruction raises cause 2 with mtval = 0 or 0xC0001073 "
        "(zero-extended).\n2. With C and D: c.fld with FS = Off raises cause 2 with mtval = 0 or 0x2000.",
    )

    def ill(mode: str) -> None:
        exp = [0, X(ILLEGAL, ILLEGAL | (0xFFFFFFFF << 32) if mut() == "mtval_sext" else ILLEGAL)]
        L.word_window(t, mode, ILLEGAL, "csrrw x0, cycle, x0", 2, "illegal 32-bit instruction", exp)

    L.each_mode(t, ill)
    with t.only_if("defined(C_SUPPORTED) && defined(D_SUPPORTED)"):
        set_field(t, "mstatus", L.FS, 0)

        def cill(mode: str) -> None:
            t.la("x8", "rvtest_trap_log")
            L.win(
                t,
                mode,
                [".hword 0x2000  // c.fld f8, 0(x8) with FS = Off", ".hword 0x0001  // c.nop"],
                2,
                "c.fld with FS = Off",
                [0, 0x2000],
            )

        L.each_mode(t, cill)
    tests.append(t)

    t = new(suite, "mtval_ebreak_op")
    describe(t, plan="1. ebreak (and c.ebreak with Zca) in M, S and U: mtval = 0 or the instruction's address.")

    def ebk(mode: str) -> None:
        L.win(t, mode, [L.EBREAK], 3, "ebreak", [0, "LAB"])

    L.each_mode(t, ebk)
    with t.only_if("defined(ZCA_SUPPORTED)"):

        def cebk(mode: str) -> None:
            L.win(t, mode, [".hword 0x9002  // c.ebreak", ".hword 0x0001  // c.nop"], 3, "c.ebreak", [0, "LAB"])

        L.each_mode(t, cebk)
    tests.append(t)

    t = new(suite, "mtval_other_traps_zero")
    describe(
        t,
        context="mtval is preset to a nonzero value before each trap (when it is writable) so a trap that leaves "
        "it unwritten is caught.",
        plan="1. ecall (T-SBI ECALL_TEST) in M, S and U: mtval = 0.\n2. A machine-level interrupt (SSI from M-mode "
        "with S-mode, otherwise MTI): mtval = 0.",
    )

    def ecz(mode: str) -> None:
        lab = t.label(f"ec{mode}")
        t.li("x6", 0x5A4)
        t.emit("csrw mtval, x6")
        t.allow(1)
        if mode != "M":
            t.enter(mode)
        t.emit("li a0, 0x73  // TSBI_ECALL_TEST")
        t.emit(f"{lab}:", 0)
        t.emit("ecall")
        if mode != "M":
            t.leave()
        t.outcome(ECALL_CAUSE[mode], lab, f"ecall in {mode}-mode", [0x5A4] if mut() == "mtval_kept" else 0, origin=mode)

    L.each_mode(t, ecz)
    for src, cond in (("SSI", S), ("MTI", f"{NO_S} && defined(RVMODEL_MTIMECMP_ADDRESS)")):

        def iz(src: str = src) -> None:
            sr = L.SRC[src]
            t.emit("csrci mstatus, 8")
            t.li("x6", 0x5A4)
            t.emit("csrw mtval, x6")
            t.li("x6", 1 << sr.cause)
            t.emit("csrs mie, x6")
            sr.raise_(t)
            lab = t.label("int")
            t.allow(1)
            t.emit("csrsi mstatus, 8")
            t.emit(f"{lab}:", 0)
            L.wait(t, 50)
            t.emit("csrci mstatus, 8")
            t.outcome(L.icause(sr.cause), lab, f"{src} in M-mode", 0, epc=False, origin="M")
            sr.clear(t)
            t.emit("csrw mie, x0")

        with t.only_if(cond):
            iz()
    tests.append(t)

    t = new(suite, "mtval_vaddr_wr_faulting_addr")
    t.extra_data += [".p2align 4", "sm_mis_buf: .fill 16, 1, 0"]
    describe(
        t,
        context="Translation is off (Bare), so the virtual address is the physical one. A misaligned access may "
        "succeed, or raise address-misaligned or access-fault.",
        plan="1. lw/sw at RVMODEL_ACCESS_FAULT_ADDRESS + 4 in M, S and U: access fault with mtval = 0 or the "
        "address.\n2. Misaligned lw, lh and sw (address = 2 mod 4 and 1 mod 2) in M, S and U: no trap, or a "
        "misaligned/access-fault exception with mtval = 0 or the address.",
    )

    def faults(mode: str) -> None:
        with t.only_if("defined(RVMODEL_ACCESS_FAULT_ADDRESS)"):
            t.emit("LI(x8, RVMODEL_ACCESS_FAULT_ADDRESS+4)", 2)
            af = "RVMODEL_ACCESS_FAULT_ADDRESS" if mut() == "mtval_aligned" else "RVMODEL_ACCESS_FAULT_ADDRESS+4"
            L.win(t, mode, ["lw x7, 0(x8)"], 5, "lw at the access-fault address", [0, af])
            L.win(t, mode, ["sw x7, 0(x8)"], 7, "sw at the access-fault address", [0, "RVMODEL_ACCESS_FAULT_ADDRESS+4"])
        for insn, off, exp in (
            ("lw x7, 0(x8)", 2, ["ok", 4, 5]),
            ("lh x7, 0(x8)", 5, ["ok", 4, 5]),
            ("sw x7, 0(x8)", 6, ["ok", 6, 7]),
        ):
            t.la("x8", "sm_mis_buf")
            t.emit(f"addi x8, x8, {off}")
            tv = [0, f"sm_mis_buf+{off}"] if mut() != "mtval_aligned" else [0, f"sm_mis_buf+{off & ~3}"]
            L.win(t, mode, [insn], exp, f"misaligned {insn.split()[0]} at +{off}", tv)

    L.each_mode(t, faults)
    tests.append(t)

    t = new(suite, "mtval_warl")
    t.extra_data += [".p2align 3", "sm_tval_data: .dword 0"]
    describe(
        t,
        context="mtval may be read-only 0; otherwise it must hold every valid address and 0.",
        plan="1. Write mtval = 0, a code address and a data address (and their + 1): each reads back as written, or "
        "0 when mtval is read-only 0 (then all read 0).",
    )
    t.la("x6", "sm_tval_data")
    t.emit("csrw mtval, x6")
    t.emit("csrr x9, mtval")
    t.emit("snez x9, x9  // 1: mtval is not read-only 0")
    for sym in (None, "CODE", "sm_tval_data", "CODE1", "sm_tval_data1"):
        lab = t.label("tv")
        if sym is None:
            t.li("x6", 0)
        else:
            t.la("x6", lab if sym.startswith("CODE") else sym.rstrip("1"))
            if sym.endswith("1"):
                t.emit("addi x6, x6, 1")
        t.emit(f"{lab}:", 0)
        t.emit("csrw mtval, x6")
        t.emit("csrr x7, mtval")
        t.emit("neg x8, x9")
        t.emit("and x6, x6, x8  // expected: the value, or 0 when read-only 0")
        t.emit("xor x7, x7, x6")
        t.check("x7", 0, lab, f"mtval holds {sym or 0}")
    tests.append(t)
    return tests


# ---------------------------------------------------------------- interrupts
M_SRC = [
    ("MTI", "defined(RVMODEL_MTIMECMP_ADDRESS)"),
    ("MSI", "!defined(RVMODEL_MTIMECMP_ADDRESS) && defined(RVMODEL_MSIP_ADDRESS)"),
]  # one M-level source


def int_case(t: TestFile, src: str, mode: str, mie_bit: int, deleg: int, mstatus_ie: int, sie: int, desc: str) -> None:
    """One interrupt case. mstatus_ie is MIE in M-mode, or MPIE (the MIE that MRET leaves) for S/U.
    Expected: taken in M when not delegated, enabled in mie and (mode < M or MIE); taken in S when delegated,
    enabled and (mode < S or (mode = S and SIE)); otherwise not taken."""
    sr = L.SRC[src]
    t.comment(f"{src}: {mode}-mode, mie bit {mie_bit}, mideleg bit {deleg}, xIE {mstatus_ie}, SIE {sie}")
    if sr.cause not in (1, 5, 9):
        _int_case(t, sr, mode, mie_bit, deleg, mstatus_ie, sie, desc)
        return
    # mideleg bits of S-level interrupts are WARL (may be read-only 0 or 1): run only if the bit holds `deleg`.
    t.li("x6", 1 << sr.cause)
    t.emit(f"csr{'s' if deleg else 'c'} mideleg, x6")
    t.emit("csrr x9, mideleg")
    t.emit("and x9, x9, x6")
    if deleg:
        t.emit("snez x9, x9")
    else:
        t.emit("seqz x9, x9")
    L.either(t, "x9", lambda: _int_case(t, sr, mode, mie_bit, deleg, mstatus_ie, sie, desc), lambda: None)
    t.emit("csrw mideleg, x0")


def _int_case(
    t: TestFile, sr: L.Src, mode: str, mie_bit: int, deleg: int, mstatus_ie: int, sie: int, desc: str
) -> None:
    src = sr.name
    t.emit("csrci mstatus, 8")
    t.emit("csrw mie, x0")
    L.csr_bits(t, "mstatus", SIE, bool(sie))
    sr.raise_(t)
    if mie_bit:
        t.li("x6", 1 << sr.cause)
        t.emit("csrs mie, x6")
    lab = t.label("int")
    t.allow(1)
    if mode == "M":
        if mstatus_ie:
            t.emit("csrsi mstatus, 8")
        t.emit(f"{lab}:", 0)
        L.wait(t, 40)
        t.emit("csrci mstatus, 8")
    else:
        L.csr_bits(t, "mstatus", MPIE, bool(mstatus_ie))
        t.enter(mode)
        t.emit(f"{lab}:", 0)
        L.wait(t, 40)
        t.leave()
    lvl = {"M": 3, "S": 1, "U": 0}[mode]
    if not mie_bit:
        exp = None
    elif not deleg:
        exp = "M" if (lvl < 3 or mstatus_ie) else None
    else:
        exp = "S" if (lvl < 1 or (lvl == 1 and sie)) else None
    if mut() == "mie_ignored_in_m" and mode == "M" and mie_bit and not deleg:
        exp = "M"
    if mut() == "deleg_taken_in_m" and mode == "M" and mie_bit and deleg and mstatus_ie:
        exp = "M"
    if mut() == "m_int_needs_mie_below_m" and mode != "M" and not deleg and not mstatus_ie:
        exp = None
    t.outcome(
        L.icause(sr.cause) if exp else "ok",
        lab,
        f"{desc}: {src} in {mode}-mode",
        epc=False,
        origin=mode if exp else None,
    )
    if exp:
        L.check_handler(t, exp, lab, desc)
    t.emit("csrw mie, x0")
    sr.clear(t)
    L.csr_bits(t, "mstatus", SIE, False)


def gen_ints(suite: str) -> list[TestFile]:
    tests = []

    t = new(suite, "intr_mip_mie_op", pool=["x6", "x7", "x8", "x9"])
    describe(
        t,
        context="Sources: the supervisor software interrupt (mip.SSIP, writable by M-mode) on harts with S-mode, "
        "and one machine-level platform interrupt (MTI through mtimecmp, or MSI through msip). In S and U, MIE is "
        "what MRET copied from MPIE. A T-SBI return to M-mode leaves MIE = 1, so every case starts with MIE = 0.",
        plan="1. In M, S and U, with the source pending, sweep mie bit = 0/1, MIE = 0/1 and (SSI) mideleg bit = 0/1: "
        "the interrupt is taken in M-mode exactly when it is enabled in mie, not delegated, and the hart is below "
        "M or MIE = 1; otherwise it is not taken in M (a delegated one may be taken in S, see the S-level rules: "
        "SIE = 0 here).",
    )
    for mode in ("M", "S", "U"):

        def body(mode: str = mode) -> None:
            for mb in (0, 1):
                for ie in (0, 1):
                    with t.only_if(S):
                        for dg in (0, 1):
                            if dg and mode == "U":
                                continue
                            int_case(t, "SSI", mode, mb, dg, ie, 0, f"mie={mb} xIE={ie} deleg={dg}")
                    for src, cond in M_SRC:
                        with t.only_if(cond):
                            int_case(t, src, mode, mb, 0, ie, 0, f"mie={mb} xIE={ie}")

        L.guard(t, L.MODE_COND[mode], body)
    tests.append(t)

    t = new(suite, "mstatus_mie_sie_op", pool=["x6", "x7", "x8", "x9"])
    describe(
        t,
        context="SSI delegated to S-mode (mideleg[1], when writable) is the S-level interrupt; MTI/MSI the M-level "
        "one. Interrupts are enabled in mie.",
        plan="1. In M-mode: an M-level interrupt is taken with MIE = 1 and not with MIE = 0.\n2. In S-mode: a "
        "delegated SSI is taken in S with SIE = 1 and not with SIE = 0.",
    )
    for src, cond in M_SRC:
        with t.only_if(cond):
            for ie in (0, 1):
                int_case(t, src, "M", 1, 0, ie, 0, f"MIE={ie}")
    with t.only_if(S):
        t.emit("csrsi mideleg, 2")
        t.emit("csrr x7, mideleg")
        t.emit("andi x7, x7, 2")
        t.emit("csrw mideleg, x0")

        def sl() -> None:
            for sie in (0, 1):
                int_case(t, "SSI", "S", 1, 1, 0, sie, f"SIE={sie}")

        L.either(t, "x7", sl, lambda: None)
    tests.append(t)

    t = new(suite, "mstatus_xie_intr_en_dis", pool=["x6", "x7", "x8", "x9"])
    describe(
        t,
        context="As in mstatus_mie_sie_op.",
        plan="1. A delegated SSI (S-level) is never taken in M-mode, even with SIE = 1 and MIE = 1.\n2. An M-level "
        "interrupt is taken in S and U even with MIE = 0; a delegated SSI is taken in U even with SIE = 0.",
    )
    with t.only_if(S):
        t.emit("csrsi mideleg, 2")
        t.emit("csrr x7, mideleg")
        t.emit("andi x7, x7, 2")
        t.emit("csrw mideleg, x0")

        def lo() -> None:
            int_case(t, "SSI", "M", 1, 1, 1, 1, "delegated, SIE=1, MIE=1")
            int_case(t, "SSI", "U", 1, 1, 0, 0, "delegated, SIE=0")

        L.either(t, "x7", lo, lambda: None)
    for src, cond in M_SRC:
        with t.only_if(cond):
            for mode in ("S", "U"):
                L.guard(t, L.MODE_COND[mode], lambda mode=mode, src=src: int_case(t, src, mode, 1, 0, 0, 0, "MIE=0"))
    tests.append(t)

    t = new(suite, "trap_del_intr_priv_lvl", [*L.REQ, "S"], pool=["x6", "x7", "x8", "x9"])
    describe(
        t,
        context="mideleg[1] (SSI) and mideleg[5] (STI) are WARL; delegated cases run when the bit reads back 1. "
        "mip.STIP is written by M-mode (with Sstc, menvcfg.STCE is cleared first).",
        plan="1. Delegated SSI/STI pending and enabled (mie, SIE = 1, MIE = 1) in M-mode: not taken.\n2. The same in "
        "S-mode: taken in S.\n3. Not delegated, in S-mode with SIE = 1 and MIE = 0 (MPIE): taken in M.",
    )
    L.stce_off(t)
    for src in ("SSI", "STI"):
        c = L.SRC[src].cause
        t.li("x6", 1 << c)
        t.emit("csrs mideleg, x6")
        t.emit("csrr x7, mideleg")
        t.emit("and x7, x7, x6")
        t.emit("csrw mideleg, x0")

        def d(src: str = src) -> None:
            int_case(t, src, "M", 1, 1, 1, 1, "delegated")
            int_case(t, src, "S", 1, 1, 0, 1, "delegated")

        L.either(t, "x7", d, lambda: None)
        int_case(t, src, "S", 1, 0, 0, 1, "not delegated")
    tests.append(t)

    # ---- priority ----
    t = new(suite, "intr_m_mode_pri", pool=["x6", "x7", "x8", "x9"])
    describe(
        t,
        context="Each group makes several interrupts pending and enabled with MIE = 0, then sets MIE: the handler "
        "masks each one in mie as it takes it, so they are taken one after another in priority order, which the "
        "trap log records (up to 4 entries). Groups use the sources the hart has: SEI, SSI, STI (S-mode, written in "
        "mip; Sstc's STCE cleared) and MEI, MSI, MTI (platform).",
        plan="1. SEI + SSI + STI: taken in the order SEI, SSI, STI.\n2. MTI + SEI + SSI + STI: MTI first.\n3. MSI + "
        "MTI: MSI first.\n4. MEI + MSI + MTI: MEI, MSI, MTI.\n5. MEI + SEI: MEI first.",
    )
    L.stce_off(t)
    groups = [
        (["SEI", "SSI", "STI"], S),
        (["MTI", "SEI", "SSI", "STI"], f"{S} && defined(RVMODEL_MTIMECMP_ADDRESS)"),
        (["MSI", "MTI"], "defined(RVMODEL_MSIP_ADDRESS) && defined(RVMODEL_MTIMECMP_ADDRESS)"),
        (
            ["MEI", "MSI", "MTI"],
            "defined(RVMODEL_SET_MEXT_INT) && defined(RVMODEL_MSIP_ADDRESS) && defined(RVMODEL_MTIMECMP_ADDRESS)",
        ),
        (["MEI", "SEI"], f"{S} && defined(RVMODEL_SET_MEXT_INT)"),
    ]
    for srcs, cond in groups:
        with t.only_if(cond):
            t.emit("csrci mstatus, 8")
            t.emit("csrw mie, x0")
            for sname in srcs:
                L.SRC[sname].raise_(t)
            t.li("x6", sum(1 << L.SRC[n].cause for n in srcs))
            t.emit("csrs mie, x6")
            lab = t.label("pri")
            t.allow(len(srcs))
            t.emit("csrsi mstatus, 8")
            t.emit(f"{lab}:", 0)
            L.wait(t, 60)
            t.emit("csrci mstatus, 8")
            t.emit("AI_OUTCOME", 20)
            t.check("x13", len(srcs), lab, f"{'+'.join(srcs)}: every pending interrupt taken")
            order = list(srcs)
            if mut() == "pri_sti_over_ssi" and "STI" in order and "SSI" in order:
                i, j = order.index("SSI"), order.index("STI")
                order[i], order[j] = order[j], order[i]
            if mut() == "pri_mti_over_msi" and "MTI" in order and "MSI" in order:
                i, j = order.index("MSI"), order.index("MTI")
                order[i], order[j] = order[j], order[i]
            for k, n in enumerate(order):
                L.check_log(
                    t,
                    "TRAPLOG_CAUSE",
                    ALL,
                    L.icause(L.SRC[n].cause),
                    lab,
                    f"{'+'.join(srcs)}: interrupt {k + 1} is {n}",
                    back=len(srcs) - 1 - k,
                )
            t.emit("csrw mie, x0")
            for sname in srcs:
                L.SRC[sname].clear(t)
    tests.append(t)

    t = new(suite, "intr_m_mode_highest_pri", [*L.REQ, "S"], pool=["x6", "x7", "x8", "x9"])
    describe(
        t,
        context="Needs a platform M-level source (MTI or MSI) and a writable mideleg[1].",
        plan="1. In S-mode with SIE = 1, a delegated SSI and an M-level interrupt both pending and enabled: the "
        "M-level one is taken first (in M-mode), then the SSI (in S-mode).",
    )
    for src, cond in M_SRC:
        with t.only_if(cond):
            t.emit("csrsi mideleg, 2")
            t.emit("csrr x7, mideleg")
            t.emit("andi x7, x7, 2")

            def both(src: str = src) -> None:
                m = L.SRC[src]
                t.emit("csrci mstatus, 8")
                t.emit("csrw mie, x0")
                m.raise_(t)
                L.SRC["SSI"].raise_(t)
                t.li("x6", (1 << m.cause) | 2)
                t.emit("csrs mie, x6")
                t.emit("csrsi mstatus, 2")
                lab = t.label("hp")
                t.allow(2)
                t.enter("S")
                t.emit(f"{lab}:", 0)
                L.wait(t, 60)
                t.leave()
                t.emit("AI_OUTCOME", 20)
                t.check("x13", 2, lab, "both interrupts taken")
                first, second = (L.SRC["SSI"], m) if mut() == "s_before_m" else (m, L.SRC["SSI"])
                L.check_log(t, "TRAPLOG_CAUSE", ALL, L.icause(first.cause), lab, "first interrupt", back=1)
                L.check_log(t, "TRAPLOG_CAUSE", ALL, L.icause(second.cause), lab, "second interrupt")
                L.check_handler(t, "M" if first is m else "S", lab, "first interrupt", back=1)
                t.emit("csrw mie, x0")
                t.emit("csrci mstatus, 2")
                m.clear(t)
                L.SRC["SSI"].clear(t)

            L.either(t, "x7", both, lambda: None)
            t.emit("csrw mideleg, x0")
    tests.append(t)

    t = new(suite, "intr_mip_mie_xret_csrwr", pool=["x6", "x7", "x8", "x9"])
    describe(
        t,
        context="The interrupt conditions must be re-evaluated right after an explicit write to mstatus or mie and "
        "right after MRET. The pending interrupt is set up (and seen in mip) before the enabling instruction.",
        plan="1. SSI (S-mode harts) or MTI/MSI pending and enabled in mie, MIE = 0: csrs mstatus.MIE traps with "
        "mepc = the next instruction.\n2. Pending with MIE = 1 and the mie bit clear: csrs mie traps with mepc = "
        "the next instruction.\n3. Pending and enabled, MRET to U-mode: taken with mepc = the MRET target.",
    )
    srcs = [
        ("SSI", S),
        ("MTI", f"{NO_S} && defined(RVMODEL_MTIMECMP_ADDRESS)"),
        ("MSI", f"{NO_S} && !defined(RVMODEL_MTIMECMP_ADDRESS) && defined(RVMODEL_MSIP_ADDRESS)"),
    ]
    for src, cond in srcs:
        with t.only_if(cond):
            sr = L.SRC[src]
            for how in ("mstatus", "mie", "mret"):
                if how == "mret":
                    t.emit("#ifdef U_SUPPORTED", 0)
                t.emit("csrci mstatus, 8")
                t.emit("csrw mie, x0")
                sr.raise_(t)
                t.li("x6", 1 << sr.cause)
                if how != "mie":
                    t.emit("csrs mie, x6")
                else:
                    t.emit("csrsi mstatus, 8")
                lab, nxt = t.label("wr"), t.label("next")
                t.allow(1)
                if how == "mret":
                    t.enter("U")
                    t.emit(f"{nxt}:", 0)
                    t.emit("nop")
                    t.leave()
                else:
                    t.emit(f"{lab}:", 0)
                    t.emit("csrsi mstatus, 8" if how == "mstatus" else "csrs mie, x6")
                    t.emit(f"{nxt}:", 0)
                    t.emit("nop")
                    t.emit("nop")
                    t.emit("csrci mstatus, 8")
                t.outcome(
                    L.icause(sr.cause), nxt, f"{src} enabled by {how}", epc=False, origin="U" if how == "mret" else "M"
                )
                L.log_word(t, "x7", "TRAPLOG_EPC")
                t.la("x8", nxt)
                if mut() == "late_eval":
                    t.emit("addi x8, x8, 4")
                t.emit("sub x7, x7, x8")
                t.check("x7", 0, nxt, f"{src} enabled by {how}: mepc = the next instruction")
                t.emit("csrw mie, x0")
                sr.clear(t)
                if how == "mret":
                    t.emit("#endif", 0)
    tests.append(t)
    return tests


def vect(xlen: int, c: int) -> int:
    """Trap-log word 0 bits 10:6 for a trap entering the framework's spreader at entry c (rvtest_trap_handler.h:
    the stub return address minus the trampoline base, times 3, shifted right by 5)."""
    return (((4 * xlen + 12 * c + 12) * 3) >> 5) & 31


WFI = 0x10500073


def gen_ints2(suite: str) -> list[TestFile]:
    tests = []

    def take_in_m(t: TestFile, sr: L.Src, lab: str) -> None:
        t.emit("csrci mstatus, 8")
        t.emit("csrw mie, x0")
        sr.raise_(t)
        t.li("x6", 1 << sr.cause)
        t.emit("csrs mie, x6")
        t.allow(1)
        t.emit("csrsi mstatus, 8")
        t.emit(f"{lab}:", 0)
        L.wait(t, 40)
        t.emit("csrci mstatus, 8")
        t.outcome(L.icause(sr.cause), lab, f"{sr.name} in M-mode", epc=False, origin="M")
        t.emit("csrw mie, x0")
        sr.clear(t)

    vctx = (
        "The framework's trap vector is a table of jumps, one per cause, each to its own stub; the M handler "
        "logs which stub ran (trap log word 0, bits 10:6). mtvec is rewritten only with its own base, read "
        "back, and restored before the end; a case runs only if the write took effect exactly."
    )

    # ---- mtvec_mode_vectored_op / mtvec_mode_direct_op ----
    for rule, mode in (("mtvec_mode_vectored_op", 1), ("mtvec_mode_direct_op", 0)):
        t = new(suite, rule, pool=["x6", "x7", "x8", "x9"])
        describe(
            t,
            context=vctx,
            plan=f"1. Set mtvec.MODE = {mode} ({'Vectored' if mode else 'Direct'}) with the same base.\n"
            "2. ebreak: enters at base (stub 0).\n3. An interrupt (MTI, else MSI, else SSI with mideleg[1] = 0) with "
            "cause c: "
            + ("enters at base + 4c (stub c)." if mode else "enters at base (stub 0).")
            + "\n4. mtvec is restored.",
        )
        for src, cond in (
            ("MTI", "defined(RVMODEL_MTIMECMP_ADDRESS)"),
            ("MSI", "!defined(RVMODEL_MTIMECMP_ADDRESS) && defined(RVMODEL_MSIP_ADDRESS)"),
            ("SSI", f"{S} && !defined(RVMODEL_MTIMECMP_ADDRESS) && !defined(RVMODEL_MSIP_ADDRESS)"),
        ):
            with t.only_if(cond):
                sr = L.SRC[src]
                t.emit("csrr x9, mtvec")
                t.emit("andi x8, x9, -4")
                if mode:
                    t.emit("ori x8, x8, 1")
                t.emit("csrw mtvec, x8")
                t.emit("csrr x7, mtvec")
                t.emit("xor x7, x7, x8")
                t.emit("seqz x7, x7")
                if src == "SSI":
                    t.emit("csrw mideleg, x0")
                    t.emit("csrr x6, mideleg")
                    t.emit("andi x6, x6, 2")
                    t.emit("seqz x6, x6  // SSI not delegated (mideleg[1] may be read-only 1)")
                    t.emit("and x7, x7, x6")

                def run(sr: L.Src = sr, mode: int = mode, t: TestFile = t) -> None:
                    lab = L.win(t, "M", [L.EBREAK], 3, "ebreak", [0, "LAB"])
                    L.check_log(
                        t,
                        "TRAPLOG_VECT",
                        0x7C0,
                        X(vect(32, 0) << 6, vect(64, 0) << 6),
                        lab,
                        "an exception enters at mtvec.BASE",
                    )
                    lab = t.label("iv")
                    take_in_m(t, sr, lab)
                    c = sr.cause if mode else 0
                    if mut() == "vectored_ignored":
                        c = 0
                    if mut() == "direct_vectors" and not mode:
                        c = sr.cause
                    L.check_log(
                        t,
                        "TRAPLOG_VECT",
                        0x7C0,
                        X(vect(32, c) << 6, vect(64, c) << 6),
                        lab,
                        f"interrupt {sr.cause} enters at BASE + {4 * c}",
                    )

                L.either(t, "x7", run, lambda: None)
                t.emit("csrw mtvec, x9")
        tests.append(t)

    t = new(suite, "mtvec_mode_enc")
    describe(
        t,
        context="mtvec is WARL; MODE values 2 and 3 are reserved. mtvec is restored after each write with no trap "
        "in between.",
        plan="1. Write mtvec = base | m for m = 0, 1, 2, 3: MODE reads 0 or 1 every time.",
    )
    t.emit("csrr x9, mtvec")
    t.emit("andi x8, x9, -4")
    for m in range(4):
        lab = t.label("m")
        t.emit(f"ori x6, x8, {m}")
        t.emit(f"{lab}:", 0)
        t.emit("csrw mtvec, x6")
        t.emit("csrr x7, mtvec")
        t.emit("csrw mtvec, x9")
        t.emit("andi x7, x7, 3")
        t.check("x7", m if mut() == "mtvec_mode2" else [0, 1], lab, f"mtvec.MODE after writing {m}")
    tests.append(t)

    # ---- mie / mip bits ----
    t = new(suite, "mie_bits_rdonly0")
    describe(
        t,
        context="Bits 0, 4, 8, 14 and 15 are not assigned to any interrupt, so they cannot become pending and must "
        "be read-only 0. Without S-mode SSIE/STIE/SEIE are read-only 0; without Sscofpmf LCOFIE is.",
        plan="1. Write all ones to mie, then 0: mie reads 0 (no read-only ones).\n2. After writing all ones: the "
        "unassigned bits, and the S-level bits without S-mode and bit 13 without Sscofpmf, read 0.",
    )
    lab = t.label("mie")
    t.emit("csrci mstatus, 8")
    t.emit("li x6, -1")
    t.emit(f"{lab}:", 0)
    t.emit("csrw mie, x6")
    t.emit("csrr x7, mie")
    t.emit("csrw mie, x0")
    t.emit("csrr x8, mie")
    t.check("x8", 0, lab, "mie reads 0 after writing 0")
    t.check_masked("x7", 0xC111, 0, lab, "unassigned mie bits 0, 4, 8, 14, 15 are read-only 0")
    with t.only_if(NO_S):
        t.check_masked(
            "x7",
            0x222,
            0x222 if mut() == "mie_s_bits_no_s" else 0,
            lab,
            "SSIE/STIE/SEIE are read-only 0 without S-mode",
        )
    with t.only_if("!defined(SSCOFPMF_SUPPORTED)"):
        t.check_masked("x7", 0x2000, 0, lab, "LCOFIE is read-only 0 without Sscofpmf")
    tests.append(t)

    t = new(suite, "mie_bits_wr")
    describe(
        t,
        context="An interrupt can become pending when software can set its mip bit (SSIP, STIP without an active "
        "stimecmp, SEIP: S-mode harts) or the platform can raise it (rvmodel_macros.h defines MTIMECMP, MSIP, "
        "the M or S external-interrupt macros).",
        plan="1. After writing all ones to mie: SSIE, STIE, SEIE (S-mode), MTIE (mtimecmp), MSIE (msip) and MEIE "
        "(external) read 1.\n2. mie is cleared.",
    )
    lab = t.label("mie")
    t.emit("csrci mstatus, 8")
    t.emit("li x6, -1")
    t.emit(f"{lab}:", 0)
    t.emit("csrw mie, x6")
    t.emit("csrr x7, mie")
    t.emit("csrw mie, x0")
    for bits, cond, what in (
        (0x222, S, "SSIE/STIE/SEIE"),
        (0x80, "defined(RVMODEL_MTIMECMP_ADDRESS)", "MTIE"),
        (0x8, "defined(RVMODEL_MSIP_ADDRESS)", "MSIE"),
        (0x800, "defined(RVMODEL_SET_MEXT_INT)", "MEIE"),
    ):
        with t.only_if(cond):
            t.check_masked("x7", bits, bits, lab, f"{what} writable")
    tests.append(t)

    t = new(suite, "mip_sxip_mie_sxie_rdonly0")
    describe(t, plan="1. Without S-mode: after csrs of bits 1, 5 and 9 in mip and in mie, they read 0.")
    with t.only_if(NO_S):
        lab = t.label("s")
        t.emit("csrci mstatus, 8")
        t.li("x6", 0x222)
        t.emit(f"{lab}:", 0)
        t.emit("csrs mie, x6")
        t.emit("csrs mip, x6")
        t.emit("csrr x7, mie")
        t.emit("csrr x8, mip")
        t.emit("csrw mie, x0")
        t.check_masked("x7", 0x222, 0, lab, "mie S-level bits read-only 0")
        t.check_masked("x8", 0x222, 0, lab, "mip S-level bits read-only 0")
    tests.append(t)

    for rule, src, bit in (
        ("mip_meip_rdonly", "MEI", 11),
        ("mip_mtip_rdonly", "MTI", 7),
        ("mip_msip_rdonly", "MSI", 3),
    ):
        t = new(suite, rule)
        sr = L.SRC[src]
        mei = src == "MEI"
        describe(
            t,
            context=f"Needs the platform {src} source ({sr.cond})."
            + (
                " Some configurations define RVMODEL_SET_MEXT_INT as an empty macro because the platform has no "
                "external interrupt source, so mip.MEIP is polled after raising it, and steps 2-3 run only if it "
                "became 1."
                if mei
                else ""
            ),
            plan=f"1. With {src} not pending: csrs mip bit {bit} leaves it 0.\n2. With {src} pending: csrc mip bit "
            f"{bit} leaves it 1.\n3. Clearing the source clears the bit.",
        )
        with t.only_if(sr.cond):
            t.emit("csrci mstatus, 8")
            t.emit("csrw mie, x0")
            sr.clear(t)
            lab = t.label("ro")
            t.li("x6", 1 << bit)
            t.emit(f"{lab}:", 0)
            t.emit("csrs mip, x6")
            t.emit("csrr x7, mip")
            t.check_masked(
                "x7", 1 << bit, 1 << bit if mut() == "mip_m_writable" else 0, lab, f"mip bit {bit} not set by csrs"
            )
            sr.raise_(t)  # polls mip until the bit is 1 (bounded)

            def pending(lab: str = lab, bit: int = bit, sr: L.Src = sr, t: TestFile = t) -> None:
                t.li("x6", 1 << bit)
                t.emit("csrc mip, x6")
                t.emit("csrr x7, mip")
                kept = 0 if mut() == "mip_pending_clearable" else 1 << bit
                t.check_masked("x7", 1 << bit, kept, lab, f"mip bit {bit} not cleared by csrc while pending")
                sr.clear(t)
                t.emit("csrr x7, mip")
                t.check_masked("x7", 1 << bit, 0, lab, f"mip bit {bit} clears with its source")

            if mei:
                t.emit("csrr x9, mip")
                t.emit(f"srli x9, x9, {bit}")
                t.emit("andi x9, x9, 1  // the platform raised MEI")
                L.either(t, "x9", pending, lambda sr=sr, t=t: sr.clear(t))
            else:
                pending()
        tests.append(t)

    for rule, bit, name in (
        ("mip_ssip_acc", 1, "SSIP"),
        ("mip_seip_acc", 9, "SEIP"),
        ("mip_stip_no_stimecmp_acc", 5, "STIP"),
    ):
        t = new(suite, rule, [*L.REQ, "S"])
        describe(
            t,
            context="With Sstc, menvcfg.STCE is cleared first so that STIP is the software-writable bit."
            if name == "STIP"
            else "mie = 0 and MIE = 0, so the pending bit is not taken.",
            plan=f"1. csrs mip.{name} reads 1; csrc reads 0 (each twice).",
        )
        if name == "STIP":
            L.stce_off(t)
        t.emit("csrci mstatus, 8")
        t.emit("csrw mie, x0")
        for _ in range(2):
            for on in (1, 0):
                lab = t.label("w")
                t.li("x6", 1 << bit)
                t.emit(f"{lab}:", 0)
                t.emit(f"csr{'s' if on else 'c'} mip, x6")
                t.emit("csrr x7, mip")
                t.check_masked(
                    "x7", 1 << bit, (1 << bit) if on else 0, lab, f"mip.{name} after csr{'s' if on else 'c'}"
                )
        tests.append(t)

    t = new(suite, "mip_stip_no_stimecmp_mmode_write", [*L.REQ, "S"], pool=["x6", "x7", "x8", "x9"])
    describe(
        t,
        context="With Sstc, menvcfg.STCE is cleared. mideleg[5] is WARL: the delegated case runs if it is writable.",
        plan="1. M-mode sets mip.STIP with STI delegated (mideleg[5]) and enabled: the interrupt is taken in S-mode "
        "(SIE = 1) with cause 5.\n2. Not delegated: taken in M-mode from S.",
    )
    L.stce_off(t)
    t.li("x6", 0x20)
    t.emit("csrs mideleg, x6")
    t.emit("csrr x7, mideleg")
    t.emit("andi x7, x7, 0x20")
    t.emit("csrw mideleg, x0")
    L.either(t, "x7", lambda: int_case(t, "STI", "S", 1, 1, 0, 1, "delegated"), lambda: None)
    int_case(t, "STI", "S", 1, 0, 0, 1, "not delegated")
    tests.append(t)

    t = new(suite, "mip_bits_wr_op")
    describe(
        t,
        context="SSIP is writable on S-mode harts.",
        plan="1. SSIP set, then cleared by writing 0 (csrc), then SSIE and MIE enabled: no interrupt is taken.\n"
        "2. SSIP set again with SSIE and MIE enabled: the interrupt is taken (control).",
    )
    with t.only_if(S):
        t.emit("csrci mstatus, 8")
        t.emit("csrsi mip, 2")
        t.emit("csrci mip, 2")
        t.emit("csrsi mie, 2")
        lab = t.label("c")
        t.allow(1)
        t.emit("csrsi mstatus, 8")
        t.emit(f"{lab}:", 0)
        L.wait(t, 40)
        t.emit("csrci mstatus, 8")
        t.outcome(
            L.icause(1) if mut() == "mip_clear_ignored" else "ok",
            lab,
            "SSIP cleared by writing 0",
            epc=False,
            origin="M",
        )
        take_in_m(t, L.SRC["SSI"], t.label("c2"))
    tests.append(t)

    # ---- supervisor external interrupt: software bit OR platform signal ----
    for rule in ("mip_seip_rdcsr", "mip_seip_wrcsr", "intr_sei_op"):
        t = new(suite, rule, [*L.REQ, "S"], pool=["x6", "x7", "x8", "x9"])
        describe(
            t,
            context="Needs the platform S-level external interrupt (RVMODEL_SET_SEXT_INT). Software's SEIP bit "
            "is written through mip.",
            plan={
                "mip_seip_rdcsr": "1. Platform signal 1, software bit 0: mip.SEIP reads 1.\n2. Signal 0, software "
                "bit 1: reads 1.\n3. Both 0: reads 0.",
                "mip_seip_wrcsr": "1. Platform signal 1, software bit 0: csrsi mip, 2 (SSIP) and csrci mip, 2 are "
                "read-modify-writes of mip.\n2. After the signal is cleared, mip.SEIP reads 0: the read-modify-writes "
                "kept the software bit 0 instead of writing back the 1 they read.",
                "intr_sei_op": "1. SEI pending through the platform signal only, and through the software bit only: "
                "with SEIE and MIE set, each is taken in M-mode with cause 9.",
            }[rule],
        )
        with t.only_if("defined(RVMODEL_SET_SEXT_INT)"):
            t.emit("csrci mstatus, 8")
            t.emit("csrw mie, x0")
            t.li("x6", 0x200)
            t.emit("csrc mip, x6")
            lab = t.label("sei")
            if rule == "mip_seip_rdcsr":
                t.emit("RVTEST_SET_SEXT_INT_M", 30)
                L.poll_mip(t, 9, 1)
                t.emit(f"{lab}:", 0)
                t.emit("csrr x7, mip")
                t.check_masked("x7", 0x200, 0x200, lab, "SEIP = signal OR software bit (signal 1)")
                t.emit("RVTEST_CLR_SEXT_INT_M", 30)
                L.poll_mip(t, 9, 0)
                t.li("x6", 0x200)
                t.emit("csrs mip, x6")
                t.emit("csrr x7, mip")
                t.check_masked("x7", 0x200, 0x200, lab, "SEIP = signal OR software bit (software 1)")
                t.emit("csrc mip, x6")
                t.emit("csrr x7, mip")
                t.check_masked("x7", 0x200, 0, lab, "SEIP = 0 with both 0")
            elif rule == "mip_seip_wrcsr":
                t.emit("RVTEST_SET_SEXT_INT_M", 30)
                L.poll_mip(t, 9, 1)
                t.emit(f"{lab}:", 0)
                t.emit("csrsi mip, 2")
                t.emit("csrci mip, 2")
                t.emit("RVTEST_CLR_SEXT_INT_M", 30)
                L.poll_mip(t, 9, 0, n=100)
                t.emit("csrr x7, mip")
                t.check_masked(
                    "x7",
                    0x200,
                    0x200 if mut() == "seip_rmw_or" else 0,
                    lab,
                    "the software SEIP bit stayed 0 through csrsi/csrci of mip",
                )
                t.li("x6", 0x200)
                t.emit("csrc mip, x6")
            else:
                for how in ("signal", "software"):
                    t.emit("csrci mstatus, 8")
                    if how == "signal":
                        t.emit("RVTEST_SET_SEXT_INT_M", 30)
                        L.poll_mip(t, 9, 1)
                    else:
                        t.li("x6", 0x200)
                        t.emit("csrs mip, x6")
                    t.li("x6", 0x200)
                    t.emit("csrs mie, x6")
                    lab = t.label("t")
                    t.allow(1)
                    t.emit("csrsi mstatus, 8")
                    t.emit(f"{lab}:", 0)
                    L.wait(t, 40)
                    t.emit("csrci mstatus, 8")
                    t.outcome(L.icause(9), lab, f"SEI through the {how}", epc=False, origin="M")
                    t.emit("csrw mie, x0")
                    if how == "signal":
                        t.emit("RVTEST_CLR_SEXT_INT_M", 30)
                        L.poll_mip(t, 9, 0, n=100)
                    t.li("x6", 0x200)
                    t.emit("csrc mip, x6")
        tests.append(t)
    return tests


def gen_wfi(suite: str) -> list[TestFile]:
    tests = []
    wake = [
        ("SSI", S),
        ("MTI", f"{NO_S} && defined(RVMODEL_MTIMECMP_ADDRESS)"),
        ("MSI", f"{NO_S} && !defined(RVMODEL_MTIMECMP_ADDRESS) && defined(RVMODEL_MSIP_ADDRESS)"),
    ]
    wfi_tv = [0, WFI]

    def wfi_m(t: TestFile, desc: str, tw: int = 0) -> None:
        """WFI in M-mode with a pending, mie-enabled interrupt and MIE = 0: resumes at the next instruction."""
        for src, cond in wake:
            with t.only_if(cond):
                sr = L.SRC[src]
                t.emit("csrci mstatus, 8")
                t.emit("csrw mie, x0")
                if tw:
                    L.csr_bits(t, "mstatus", TW, True)
                sr.raise_(t)
                t.li("x6", 1 << sr.cause)
                t.emit("csrs mie, x6")
                t.li("x7", 0)
                lab = t.window("M", [".word 0x10500073  // wfi", "li x7, 1"], "ok", f"{desc} ({sr.name} pending)")
                t.check("x7", 1, lab, "execution resumes after the wfi")
                t.emit("csrw mie, x0")
                sr.clear(t)
                if tw:
                    L.csr_bits(t, "mstatus", TW, False)

    t = new(suite, "wfi_intr_dis")
    describe(
        t,
        context="The wake-up source is SSI on S-mode harts, else MTI or MSI, pending and enabled in mie.",
        plan="1. With MIE = 0, wfi in M-mode with a pending, locally enabled interrupt: no trap, execution "
        "continues at the next instruction.",
    )
    wfi_m(t, "wfi with MIE = 0")
    tests.append(t)

    t = new(suite, "wfi_no_intr_pc")
    describe(
        t,
        context="As in wfi_intr_dis.",
        plan="1. The wfi resumes without taking an interrupt (MIE = 0): the "
        "instruction after it runs (x7 = 1) and no trap occurs.",
    )
    wfi_m(t, "wfi resuming without an interrupt")
    tests.append(t)

    t = new(suite, "wfi_unaffected_conditions", [*L.REQ, "S"])
    describe(
        t,
        context="mideleg[1] is WARL; the delegated case runs when it reads back 1.",
        plan="1. SSI delegated to S-mode, pending and enabled in sie, with MIE = SIE = 1: wfi in M-mode resumes "
        "(no trap; the delegated interrupt is not taken in M).\n2. SSI not delegated, enabled in mie, MIE = 0: wfi "
        "resumes.",
    )
    t.emit("csrci mstatus, 8")
    t.emit("csrsi mideleg, 2")
    t.emit("csrr x7, mideleg")
    t.emit("andi x7, x7, 2")

    def dl() -> None:
        t.emit("csrsi mip, 2")
        t.emit("csrsi mie, 2")
        t.emit("csrsi mstatus, 10")
        t.li("x7", 0)
        lab = t.window("M", [".word 0x10500073  // wfi", "li x7, 1"], "ok", "wfi with a delegated SSI pending")
        t.emit("csrci mstatus, 10")
        t.check("x7", 1, lab, "execution resumes after the wfi")
        t.emit("csrw mie, x0")
        t.emit("csrci mip, 2")

    L.either(t, "x7", dl, lambda: None)
    t.emit("csrw mideleg, x0")
    wfi_m(t, "wfi with a non-delegated interrupt and MIE = 0")
    tests.append(t)

    t = new(suite, "wfi_resume_any_priv", [*L.REQ, "S"])
    describe(
        t,
        context="mideleg[1] is WARL; the case runs when it reads back 1. mstatus.TW = 0.",
        plan="1. In S-mode with SIE = 0, a delegated SSI pending and enabled in sie: wfi resumes without a trap "
        "(the instruction after it runs).",
    )
    t.emit("csrci mstatus, 8")
    t.emit("csrsi mideleg, 2")
    t.emit("csrr x7, mideleg")
    t.emit("andi x7, x7, 2")

    def sl() -> None:
        t.emit("csrci mstatus, 2")
        t.emit("csrsi mip, 2")
        t.emit("csrsi mie, 2")
        t.li("x7", 0)
        lab = t.window("S", [".word 0x10500073  // wfi", "li x7, 1"], "ok", "wfi with SIE = 0 and a delegated SSI")
        t.check("x7", 1, lab, "execution resumes after the wfi")
        t.emit("csrw mie, x0")
        t.emit("csrci mip, 2")

    L.either(t, "x7", sl, lambda: None)
    t.emit("csrw mideleg, x0")
    tests.append(t)

    t = new(suite, "mstatus_tw_op", [*L.REQ, "U"])
    describe(
        t,
        context="With S-mode, a delegated SSI pending and enabled in sie with SIE = 0 is the wake-up source in "
        "S-mode (no trap from it). With TW = 1 the wfi may complete or raise illegal instruction after a bounded "
        "time (xtval 0 or the wfi encoding); TW never affects M-mode.",
        plan="1. S-mode, TW = 0: wfi completes without a trap.\n2. S-mode and U-mode, TW = 1: wfi completes or raises "
        "illegal instruction.\n3. M-mode, TW = 1, a pending enabled interrupt with MIE = 0: wfi completes without "
        "a trap.",
    )
    with t.only_if(S):
        t.emit("csrci mstatus, 8")
        t.emit("csrsi mideleg, 2")
        t.emit("csrr x7, mideleg")
        t.emit("andi x7, x7, 2")

        def stw() -> None:
            t.emit("csrci mstatus, 2")
            t.emit("csrsi mip, 2")
            t.emit("csrsi mie, 2")
            for tw in (0, 1):
                L.csr_bits(t, "mstatus", TW, bool(tw))
                exp = ["ok", 2] if tw else (2 if mut() == "tw0_traps" else "ok")
                L.word_window(t, "S", WFI, "wfi", exp, f"wfi with TW = {tw}", wfi_tv)
            t.emit("csrw mie, x0")
            t.emit("csrci mip, 2")

        L.either(t, "x7", stw, lambda: None)
        t.emit("csrw mideleg, x0")
    L.csr_bits(t, "mstatus", TW, True)
    L.word_window(t, "U", WFI, "wfi", ["ok", 2], "wfi with TW = 1", wfi_tv)
    L.csr_bits(t, "mstatus", TW, False)
    wfi_m(t, "wfi in M-mode with TW = 1", tw=1)
    tests.append(t)

    t = new(suite, "mstatus_tw_umode_op", [*L.REQ, "S", "U"])
    describe(
        t,
        context="With S-mode, U-mode wfi must complete or trap within a bounded time even with TW = 0, so the test "
        "cannot hang. No wake-up source is pending.",
        plan="1. U-mode wfi with TW = 0: completes or raises illegal instruction (xtval 0 or the encoding).",
    )
    L.csr_bits(t, "mstatus", TW, False)
    L.word_window(t, "U", WFI, "wfi", ["ok", 2], "wfi with TW = 0", wfi_tv)
    tests.append(t)

    t = new(suite, "wfi_all_privileged_modes")
    describe(
        t,
        context="As in wfi_intr_dis for M-mode. In S-mode (TW = 0) a delegated SSI with SIE = 0 is the wake-up source.",
        plan="1. wfi in M-mode completes.\n2. With S-mode: wfi in S-mode with TW = 0 completes without a trap.",
    )
    wfi_m(t, "wfi in M-mode")
    with t.only_if(S):
        t.emit("csrci mstatus, 8")
        t.emit("csrsi mideleg, 2")
        t.emit("csrr x7, mideleg")
        t.emit("andi x7, x7, 2")

        def sm() -> None:
            t.emit("csrci mstatus, 2")
            L.csr_bits(t, "mstatus", TW, False)
            t.emit("csrsi mip, 2")
            t.emit("csrsi mie, 2")
            L.word_window(t, "S", WFI, "wfi", "ok", "wfi with TW = 0", wfi_tv)
            t.emit("csrw mie, x0")
            t.emit("csrci mip, 2")

        L.either(t, "x7", sm, lambda: None)
        t.emit("csrw mideleg, x0")
    tests.append(t)
    return tests


# ---------------------------------------------------------------- counters
CNT = {
    "cycle": (0xC00, 0, "defined(ZICNTR_SUPPORTED)"),
    "time": (0xC01, 1, "defined(ZICNTR_SUPPORTED)"),
    "instret": (0xC02, 2, "defined(ZICNTR_SUPPORTED)"),
    "hpmcounter3": (0xC03, 3, "defined(ZIHPM_SUPPORTED)"),
    "hpmcounter4": (0xC04, 4, "defined(ZIHPM_SUPPORTED)"),
    "hpmcounter17": (0xC11, 17, "defined(ZIHPM_SUPPORTED)"),
    "hpmcounter31": (0xC1F, 31, "defined(ZIHPM_SUPPORTED)"),
}


def gen_counters(suite: str) -> list[TestFile]:
    tests = []

    t = new(suite, "mcounteren_clr_ill_inst_exc", [*L.REQ, "U"])
    describe(
        t,
        context="mcounteren bits are WARL. With S-mode, scounteren is set to all ones so that U-mode access depends "
        "on mcounteren alone. time may be emulated by the framework, which honors the enables.",
        plan="1. For cycle, time, instret and hpmcounter3/4/17/31 (with Zicntr/Zihpm): with the mcounteren bit "
        "clear, a read in S-mode and in U-mode raises illegal instruction (xtval 0 or the instruction).",
    )
    with t.only_if(S):
        t.emit("li x6, -1")
        t.emit("csrw scounteren, x6")
    for name, (num, bit, cond) in CNT.items():

        def body(name: str = name, num: int = num, bit: int = bit) -> None:
            t.li("x6", 1 << bit) if bit < 31 else t.load("x6", 1 << 31)
            t.emit("csrc mcounteren, x6")
            for mode in ("S", "U"):
                exp = "ok" if mut() == "mcounteren_ignored" else "illegal"
                L.guard(
                    t,
                    L.MODE_COND[mode],
                    lambda exp=exp, mode=mode: L.csr_window(
                        t, mode, num, name, L.FORMS[0], exp, f"mcounteren bit {bit} = 0"
                    ),
                )

        guard(t, cond, body)
    t.emit("li x6, -1")
    t.emit("csrw mcounteren, x6")
    tests.append(t)

    t = new(suite, "mcounteren_set_nxt_priv", [*L.REQ, "U"])
    describe(
        t,
        context="mcounteren bits are WARL and may be read-only 0; each case reads the bit back first. With S-mode, "
        "U-mode access also needs scounteren (set to all ones and read back).",
        plan="1. For each counter: set its mcounteren bit; if it reads 1, a read in S-mode (or in U-mode on a hart "
        "without S-mode) succeeds; if it reads 0, the read raises illegal instruction.\n2. With S-mode: the U-mode "
        "read succeeds exactly when both the mcounteren and scounteren bits read 1.",
    )
    with t.only_if(S):
        t.emit("li x6, -1")
        t.emit("csrw scounteren, x6")
    for name, (num, bit, cond) in CNT.items():

        def body(name: str = name, num: int = num, bit: int = bit) -> None:
            t.load("x6", 1 << bit)
            t.emit("csrs mcounteren, x6")
            for mode in ("S", "U"):

                def m(mode: str = mode) -> None:
                    t.load("x6", 1 << bit)
                    t.emit("csrr x9, mcounteren")
                    t.emit("and x9, x9, x6")
                    if mode == "U":
                        with t.only_if(S):
                            t.emit("csrr x8, scounteren")
                            t.emit("and x8, x8, x6")
                            t.emit("snez x8, x8")
                            t.emit("snez x9, x9")
                            t.emit("and x9, x9, x8")
                    L.either(
                        t,
                        "x9",
                        lambda: L.csr_window(t, mode, num, name, L.FORMS[0], "ok", f"enabled bit {bit}"),
                        lambda: L.csr_window(t, mode, num, name, L.FORMS[0], "illegal", f"bit {bit} read-only 0"),
                    )

                L.guard(t, L.MODE_COND[mode], m)

        guard(t, cond, body)
    tests.append(t)

    t = new(suite, "mcounteren_sz")
    describe(
        t,
        context="mcounteren exists with U-mode.",
        plan="1. RV64: after writing all ones, mcounteren[63:32] read 0 (32-bit register).",
    )
    with t.only_if(U), t.rv64_only():
        lab = t.label("sz")
        t.emit("li x6, -1")
        t.emit(f"{lab}:", 0)
        t.emit("csrw mcounteren, x6")
        t.emit("csrr x7, mcounteren")
        t.emit("srli x7, x7, 32")
        t.check("x7", 0, lab, "mcounteren[63:32] = 0")
    tests.append(t)

    def probe_csr(t: TestFile, reg: str, num: int, name: str) -> None:
        """reg = 1 if the CSR reads without a trap (its value is never all ones), else 0."""
        t.emit(f"li {reg}, -1")
        t.window(
            "M",
            [f"csrrs {reg}, {hex(num)}, x0  // {name}"],
            ["ok", 2],
            f"{name} probe",
            [0, L.enc_csr(num, 2, int(reg[1:]), 0)],
        )
        t.emit(f"addi {reg}, {reg}, 1")
        t.emit(f"snez {reg}, {reg}")

    def delta_lt(t: TestFile, a: str, b: str, limit: int, lab: str, desc: str) -> None:
        """Check 0 <= b - a < limit (unsigned), i.e. b is at most limit - 1 counts after a."""
        t.emit(f"sub x5, {b}, {a}")
        t.load("x4", limit)
        t.emit("sltu x5, x5, x4")
        t.check_bool("x5", lab, desc)

    t = new(suite, "mcountinhibit_sz_warl")
    describe(
        t,
        context="mcountinhibit may be absent (access traps); then the test does nothing more.",
        plan="1. After writing all ones: bit 1 (time has no inhibit) reads 0, and on RV64 bits 63:32 read 0.\n"
        "2. mcountinhibit is cleared.",
    )
    probe_csr(t, "x9", 0x320, "mcountinhibit")

    def sz() -> None:
        lab = t.label("ci")
        t.emit("li x6, -1")
        t.emit(f"{lab}:", 0)
        t.emit("csrw 0x320, x6")
        t.emit("csrr x7, 0x320")
        t.emit("csrw 0x320, x0")
        t.check_masked("x7", X(2, 0xFFFFFFFF00000002), 0, lab, "mcountinhibit bit 1 (and bits 63:32) read 0")

    L.either(t, "x9", sz, lambda: None)
    tests.append(t)

    t = new(suite, "mcountinhibit_clear_op")
    describe(
        t,
        context="CY and IR are WARL; each is tried and read back. A set bit freezes its counter; a clear (or "
        "read-only 0) bit lets it count.",
        plan="1. Set CY and IR: for each bit that reads 1, the counter (mcycle/minstret) reads the same value "
        "twice around 20 instructions; for a bit that reads 0, it increases.\n2. Clear both: mcycle and minstret "
        "increase across 20 instructions.",
    )
    probe_csr(t, "x9", 0x320, "mcountinhibit")

    def ci() -> None:
        for bit, ctr in ((0, "mcycle"), (2, "minstret")):
            lab = t.label(ctr)
            t.li("x6", 1 << bit)
            t.emit(f"{lab}:", 0)
            t.emit("csrs 0x320, x6")
            t.emit("csrr x9, 0x320")
            t.emit(f"andi x9, x9, {1 << bit}")
            t.emit(f"csrr x7, {ctr}")
            for _ in range(20):
                t.emit("nop")
            t.emit(f"csrr x8, {ctr}")
            t.emit("csrw 0x320, x0")
            t.emit("sub x8, x8, x7")
            t.emit("snez x8, x8  // 1: counted")
            t.emit("snez x9, x9  // 1: inhibited")
            t.emit("xor x8, x8, x9")
            if mut() == "inhibit_ignored":
                t.emit("xor x8, x8, x9")
            t.check_bool("x8", lab, f"{ctr} counts exactly when mcountinhibit bit {bit} reads 0")
            t.emit(f"csrr x7, {ctr}")
            for _ in range(20):
                t.emit("nop")
            t.emit(f"csrr x8, {ctr}")
            t.emit("sub x8, x8, x7")
            t.emit("snez x8, x8")
            t.check_bool("x8", lab, f"{ctr} counts after the inhibit is cleared")

    L.either(t, "x9", ci, lambda: None)
    tests.append(t)

    t = new(suite, "mcountinhibit_only_inc", [*L.REQ, "S", "Zicntr"])
    describe(
        t,
        context="mcountinhibit.CY is WARL; the case runs when it reads back 1. mcounteren.CY is set (and read back).",
        plan="1. With CY inhibited and mcounteren.CY = 1: an S-mode read of cycle does not trap.",
    )
    probe_csr(t, "x9", 0x320, "mcountinhibit")

    def oi() -> None:
        t.emit("csrsi 0x320, 1")
        t.emit("csrsi mcounteren, 1")
        t.emit("csrr x7, 0x320")
        t.emit("csrr x8, mcounteren")
        t.emit("and x7, x7, x8")
        t.emit("andi x7, x7, 1")
        L.either(t, "x7", lambda: L.csr_window(t, "S", 0xC00, "cycle", L.FORMS[0], "ok", "CY inhibited"), lambda: None)
        t.emit("csrw 0x320, x0")

    L.either(t, "x9", oi, lambda: None)
    tests.append(t)

    t = new(suite, "mcountinhibit_not_impl")
    describe(
        t,
        context="Applies when mcountinhibit is absent (its access traps).",
        plan="1. Without mcountinhibit: mcycle and minstret increase across 20 instructions.",
    )
    probe_csr(t, "x9", 0x320, "mcountinhibit")

    def ni() -> None:
        for ctr in ("mcycle", "minstret"):
            lab = t.label(ctr)
            t.emit(f"{lab}:", 0)
            t.emit(f"csrr x7, {ctr}")
            for _ in range(20):
                t.emit("nop")
            t.emit(f"csrr x8, {ctr}")
            t.emit("sub x8, x8, x7")
            t.emit("snez x8, x8")
            t.check_bool("x8", lab, f"{ctr} counts")

    L.either(t, "x9", lambda: None, ni)
    tests.append(t)

    t = new(suite, "mcycle_minstret_wr")
    describe(
        t,
        context="A CSR write takes effect after the writing instruction otherwise completes, so the csrw's own "
        "retirement does not add to the value written, and the following csrr reads the value written.",
        plan="1. csrw minstret, X then csrr minstret: reads exactly X (for three random X).\n2. csrw mcycle, X then "
        "csrr mcycle: reads X plus fewer than 1000 cycles (an instruction-cache miss may fall between them).\n3. RV32: the same for the high halves (minstreth, "
        "mcycleh read back the value written when the low half is small).",
    )
    for _ in range(3):
        v = t.rand_x()
        lab = t.label("mi")
        with t.rv64_only():
            t.load("x6", v)
            t.emit(f"{lab}:", 0)
            t.emit("csrw minstret, x6")
            t.emit("csrr x7, minstret")
            t.emit("sub x7, x7, x6")
            t.check("x7", 1 if mut() == "minstret_write_counts" else 0, lab, "minstret reads the value written")
            t.emit("csrw mcycle, x6")
            t.emit("csrr x7, mcycle")
            delta_lt(t, "x6", "x7", 1000, lab, "mcycle reads the value written plus < 1000")
        with t.rv32_only():
            t.load("x6", v)
            t.emit("csrw minstreth, x0")
            t.emit(f"{lab}:", 0)
            t.emit("csrw minstret, x6")
            t.emit("csrr x7, minstret")
            t.emit("sub x7, x7, x6")
            t.check("x7", 1 if mut() == "minstret_write_counts" else 0, lab, "minstret reads the value written")
            t.load("x6", X(0x7FFFF000 & v.num(32), 0))
            t.emit("csrw mcycle, x6")
            t.emit("csrr x7, mcycle")
            delta_lt(t, "x6", "x7", 1000, lab, "mcycle reads the value written plus < 1000")
            t.li("x6", 7)
            t.emit("csrw minstret, x0")
            t.emit("csrw minstreth, x6")
            t.emit("csrr x7, minstreth")
            t.check("x7", 7, lab, "minstreth reads the value written")
            t.emit("csrw mcycle, x0")
            t.emit("csrw mcycleh, x6")
            t.emit("csrr x7, mcycleh")
            t.check("x7", 7, lab, "mcycleh reads the value written")
    tests.append(t)

    t = new(suite, "mcycle_minstret_sz")
    describe(
        t,
        context="The counters are 64-bit on RV32 too: a carry out of bit 31 reaches bit 32.",
        plan="1. Write mcycle and minstret = 2^32 - 1 (high half 0), run 20 instructions: RV64 reads >= 2^32; RV32 "
        "mcycleh/minstreth read 1.",
    )
    for ctr in ("minstret", "mcycle"):
        lab = t.label(ctr)
        with t.rv64_only():
            t.load("x6", 0xFFFFFFFF)
            t.emit(f"{lab}:", 0)
            t.emit(f"csrw {ctr}, x6")
            for _ in range(20):
                t.emit("nop")
            t.emit(f"csrr x7, {ctr}")
            t.emit("srli x7, x7, 32")
            t.check("x7", 0 if mut() == "counter_32bit" else 1, lab, f"{ctr} carried into bit 32")
        with t.rv32_only():
            t.emit(f"csrw {ctr}h, x0")
            t.emit("li x6, -1")
            t.emit(f"{lab}:", 0)
            t.emit(f"csrw {ctr}, x6")
            for _ in range(20):
                t.emit("nop")
            t.emit(f"csrr x7, {ctr}h")
            t.check("x7", 0 if mut() == "counter_32bit" else 1, lab, f"{ctr}h = 1 after the low half wrapped")
    tests.append(t)

    t = new(suite, "mcycleh_minstreth_mhpmh_op")
    describe(
        t,
        context="RV32 only (the file passes trivially on RV64).",
        plan="1. RV32: write minstret = 5, then minstreth = 0xABC: minstreth reads 0xABC and minstret reads 5 plus "
        "fewer than 20.\n2. The same for mcycle/mcycleh (fewer than 200 cycles).",
    )
    with t.rv32_only():
        for ctr, lim in (("minstret", 20), ("mcycle", 200)):
            lab = t.label(ctr)
            t.li("x6", 5)
            t.li("x8", 0xABC)
            t.emit(f"{lab}:", 0)
            t.emit(f"csrw {ctr}, x6")
            t.emit(f"csrw {ctr}h, x8")
            t.emit(f"csrr x7, {ctr}h")
            t.emit(f"csrr x9, {ctr}")
            t.check("x7", 0xABC, lab, f"{ctr}h reads the value written")
            delta_lt(t, "x6", "x9", lim, lab, f"{ctr} kept its low half")
    tests.append(t)

    t = new(suite, "cycle_instret_hpmcounter_op_rdonly", [*L.REQ, "Zicntr"])
    describe(
        t,
        context="M-mode reads of the unprivileged counters need no enable.",
        plan="1. Write mcycle = X and minstret = Y (random): cycle reads X plus < 200 and instret Y plus < 10.\n"
        "2. Writing cycle or instret (csrrw, csrrs/csrrc with rs1 != x0, immediates) raises illegal instruction.",
    )
    for ctr, sh, lim in (("mcycle", "cycle", 200), ("minstret", "instret", 10)):
        lab = t.label(sh)
        v = t.rand_x()
        with t.rv64_only():
            t.load("x6", v)
            t.emit(f"{lab}:", 0)
            t.emit(f"csrw {ctr}, x6")
            t.emit(f"csrr x7, {sh}")
            delta_lt(t, "x6", "x7", lim, lab, f"{sh} shadows {ctr}")
        with t.rv32_only():
            t.load("x6", v)
            t.emit(f"{lab}:", 0)
            t.emit(f"csrw {ctr}h, x0")
            t.emit(f"csrw {ctr}, x0")
            t.emit(f"csrw {ctr}h, x6")
            t.emit(f"csrr x7, {sh}h")
            t.emit("sub x7, x7, x6")
            t.check("x7", 0, lab, f"{sh}h shadows {ctr}h")
        num = CNT[sh][0]
        t.li("x6", 0)
        for f in L.WRITE_FORMS:
            if f[1] in (2, 3) and f[3] == 0:
                continue
            L.csr_window(t, "M", num, sh, f, "ok" if mut() == "cycle_writable" else "illegal", "read-only")
    tests.append(t)

    t = new(suite, "mhpmevent_enc")
    describe(
        t,
        context="mhpmcounter3-31 may be read-only 0; the value read right after the write is the reference. "
        "mhpmevent3-31 are WARL (mhpmevent_sz_warl_op), so a selector may not hold 0 (e.g. it is hardwired to "
        "an event): it is read back after the write, and the counter is required not to count only when the "
        "selector reads 0. On RV32 with Sscofpmf, mhpmevent_nh is written 0 and read back too.",
        plan="1. For n = 3, 4, 17, 31: mhpmevent_n = 0 (no event), mhpmcounter_n = 0x5A: if mhpmevent_n reads 0, the "
        "counter reads the same value before and after 30 instructions.",
    )
    for n in (3, 4, 17, 31):
        lab = t.label(f"h{n}")
        t.li("x6", 0x5A)
        t.emit(f"{lab}:", 0)
        t.emit(f"csrw {hex(0x320 + n)}, x0  // mhpmevent{n} = 0")
        with t.rv32_only(), t.only_if("defined(SSCOFPMF_SUPPORTED)"):
            t.emit(f"csrw {hex(0x720 + n)}, x0  // mhpmevent{n}h = 0")
        with t.rv32_only():
            t.emit(f"csrw {hex(0xB80 + n)}, x0  // mhpmcounter{n}h")
        t.emit(f"csrw {hex(0xB00 + n)}, x6  // mhpmcounter{n}")
        t.emit(f"csrr x7, {hex(0xB00 + n)}")
        for _ in range(30):
            t.emit("nop")
        t.emit(f"csrr x8, {hex(0xB00 + n)}")
        t.emit(f"csrr x9, {hex(0x320 + n)}  // the selector actually held")
        with t.rv32_only(), t.only_if("defined(SSCOFPMF_SUPPORTED)"):
            t.emit(f"csrr x5, {hex(0x720 + n)}")
            t.emit("or x9, x9, x5")
        t.emit("sub x8, x8, x7")
        if mut() == "hpm_event0_counts":
            t.emit("snez x8, x8  // (mutant) event 0 counts")
        else:
            t.emit("seqz x8, x8  // did not count")
        t.emit("snez x9, x9  // the selector is not event 0")
        t.emit("or x8, x8, x9")
        t.check_bool("x8", lab, f"mhpmcounter{n} does not count while mhpmevent{n} reads 0 (no event)")
    tests.append(t)

    t = new(suite, "mcounteren_inc_inaccessible", [*L.REQ, "U"])
    describe(
        t,
        plan="1. With mcounteren = 0: mcycle and minstret still increase across 20 instructions.\n2. "
        "mcounteren is restored to all ones.",
    )
    t.emit("csrw mcounteren, x0")
    for ctr in ("mcycle", "minstret"):
        lab = t.label(ctr)
        t.emit(f"{lab}:", 0)
        t.emit(f"csrr x7, {ctr}")
        for _ in range(20):
            t.emit("nop")
        t.emit(f"csrr x8, {ctr}")
        t.emit("sub x8, x8, x7")
        t.emit("snez x8, x8")
        t.check_bool("x8", lab, f"{ctr} counts with mcounteren = 0")
    t.emit("li x6, -1")
    t.emit("csrw mcounteren, x6")
    tests.append(t)
    return tests


# ---------------------------------------------------------------- envcfg, seccfg
CBO = {"inval": 0, "clean": 1, "flush": 2, "zero": 4}


def cbo(op: str, rs1: int = 8) -> int:
    return (CBO[op] << 20) | (rs1 << 15) | (2 << 12) | 0x0F


def menvcfg_bits(t: TestFile, on: bool, lo: int = 0, hi: int = 0) -> None:
    """Set/clear bits in menvcfg: lo = bits 31:0, hi = bits 63:32 (menvcfgh on RV32)."""
    op = "csrs" if on else "csrc"
    if lo:
        t.li("x5", lo) if lo < (1 << 31) else t.load("x5", lo)
        t.emit(f"{op} menvcfg, x5")
    if hi:
        with t.rv64_only():
            t.load("x5", hi << 32)
            t.emit(f"{op} menvcfg, x5")
        with t.rv32_only():
            t.load("x5", hi)
            t.emit(f"{op} menvcfgh, x5")


SM1P12 = "defined(SM1P12P0_OR_LATER_SUPPORTED)"
ENVCFG_VER = "menvcfg exists from Sm 1.12 (SM1P12P0_OR_LATER_SUPPORTED); on earlier harts the test is empty."


def gen_envcfg(suite: str) -> list[TestFile]:
    tests = []

    t = new(suite, "menvcfg_menvcfgh_no_u_mode")
    describe(t, plan="1. Without U-mode: reading or writing menvcfg (and menvcfgh on RV32) raises illegal instruction.")
    with t.only_if(NO_U):
        t.li("x6", 0)
        for f in (L.FORMS[0], L.FORMS[1]):
            L.csr_window(t, "M", 0x30A, "menvcfg", f, "ok" if mut() == "menvcfg_no_u_exists" else "illegal", "no U")
            with t.rv32_only():
                L.csr_window(t, "M", 0x31A, "menvcfgh", f, "illegal", "no U")
    tests.append(t)

    t = new(suite, "menvcfg_mandatory_u_mode", [*L.REQ, "U"])
    describe(
        t,
        context=ENVCFG_VER,
        plan="1. With U-mode: menvcfg reads, and is written with its own value, without a trap (every "
        "form that writes its current value).",
    )
    with t.only_if(SM1P12):
        t.emit("csrr x6, menvcfg")
        for f in L.FORMS:
            if "0x15" in f[0]:
                continue
            L.csr_window(t, "M", 0x30A, "menvcfg", f, "ok", "U-mode hart")
    tests.append(t)

    t = new(suite, "menvcfgh_sz_acc_op", [*L.REQ, "U"])
    describe(
        t,
        context="menvcfg is restored after each write, before any trap. " + ENVCFG_VER,
        plan="1. RV64: menvcfgh (0x31A) raises illegal instruction for reads and writes.\n2. RV32: a write of all ones "
        "to menvcfgh leaves menvcfg (bits 31:0) unchanged; menvcfgh reads back the same high bits as a second "
        "identical write.",
    )
    with t.rv64_only():
        t.li("x6", 0)
        for f in (L.FORMS[0], L.FORMS[1]):
            L.csr_window(t, "M", 0x31A, "menvcfgh", f, "illegal", "RV64")
    with t.rv32_only(), t.only_if(SM1P12):
        lab = t.label("h")
        t.emit("csrr x8, menvcfg")
        t.emit("csrr x9, menvcfgh")
        t.emit("li x6, -1")
        t.emit(f"{lab}:", 0)
        t.emit("csrw menvcfgh, x6")
        t.emit("csrr x7, menvcfg")
        t.emit("csrr x6, menvcfgh")
        t.emit("csrw menvcfgh, x9")
        t.emit("csrw menvcfg, x8")
        t.emit("sub x7, x7, x8")
        t.check("x7", 0, lab, "menvcfg unchanged by a menvcfgh write")
    tests.append(t)

    fields = [
        ("menvcfg_pbmte_rdonly0", 0, 1 << 30, "!defined(SVPBMT_SUPPORTED)", "PBMTE (bit 62)", "Svpbmt"),
        ("menvcfg_adue_rdonly0", 0, 1 << 29, "!defined(SVADU_SUPPORTED)", "ADUE (bit 61)", "Svadu"),
        ("menvcfg_cde_rdonly0", 0, 1 << 28, "!defined(SMCDELEG_SUPPORTED)", "CDE (bit 60)", "Smcdeleg"),
        ("menvcfg_cbze_rdonly0", 0x80, 0, "!defined(ZICBOZ_SUPPORTED)", "CBZE (bit 7)", "Zicboz"),
        ("menvcfg_cbcfe_rdonly0", 0x40, 0, "!defined(ZICBOM_SUPPORTED)", "CBCFE (bit 6)", "Zicbom"),
        ("menvcfg_cbie_rdonly0", 0x30, 0, "!defined(ZICBOM_SUPPORTED)", "CBIE (bits 5:4)", "Zicbom"),
    ]
    for rule, lo, hi, cond, name, ext in fields:
        t = new(suite, rule, [*L.REQ, "U"])
        describe(
            t,
            context="All other menvcfg bits are written with their current values; menvcfg is restored before any "
            "trap. " + ENVCFG_VER,
            plan=f"1. Without {ext}: after csrs of {name}, the field reads 0.",
        )
        with t.only_if(f"({cond}) && {SM1P12}"):
            lab = t.label("f")
            t.emit("csrr x8, menvcfg")
            with t.rv32_only():
                t.emit("csrr x9, menvcfgh")
            t.emit(f"{lab}:", 0)
            menvcfg_bits(t, True, lo, hi)
            if lo:
                t.emit("csrr x7, menvcfg")
                t.emit("csrw menvcfg, x8")
                t.check_masked("x7", lo, lo if mut() == "envcfg_field_writable" else 0, lab, f"{name} read-only 0")
            else:
                with t.rv64_only():
                    t.emit("csrr x7, menvcfg")
                    t.emit("csrw menvcfg, x8")
                    t.check_masked(
                        "x7",
                        X(0, hi << 32),
                        X(0, hi << 32) if mut() == "envcfg_field_writable" else 0,
                        lab,
                        f"{name} read-only 0",
                    )
                with t.rv32_only():
                    t.emit("csrr x7, menvcfgh")
                    t.emit("csrw menvcfgh, x9")
                    t.check_masked("x7", hi, hi if mut() == "envcfg_field_writable" else 0, lab, f"{name} read-only 0")
        tests.append(t)

    # ---- CBO enables ----
    for rule, ext, bitlo, ops in (
        ("menvcfg_cbze_op", "Zicboz", 0x80, ["zero"]),
        ("menvcfg_cbcfe_op", "Zicbom", 0x40, ["clean", "flush"]),
    ):
        t = new(suite, rule, [*L.REQ, "S", ext])
        t.extra_data += [".p2align 12", "sm_cbo_buf: .fill 4096, 1, 0x5a"]
        describe(
            t,
            context="The block operated on is in a 4 KiB-aligned 4 KiB buffer. In U-mode senvcfg's bit is set too, "
            "so menvcfg alone decides. The bit is WARL; the enabled case runs when it reads back 1.",
            plan=f"1. menvcfg bit clear: cbo.{'/'.join(ops)} in S and U raises illegal instruction.\n2. Bit set: it "
            f"executes without a trap in S and U.\n3. In M-mode it executes whatever the bit.",
        )
        t.la("x8", "sm_cbo_buf")
        t.li("x6", bitlo)
        t.emit("csrs senvcfg, x6")
        for en in (0, 1):
            menvcfg_bits(t, bool(en), bitlo)
            t.emit("csrr x9, menvcfg")
            t.emit(f"andi x9, x9, {bitlo}")

            def cbo_run(en: int = en, t: TestFile = t, ops: list[str] = ops, bitlo: int = bitlo) -> None:
                for op in ops:
                    for mode in ("S", "U", "M"):
                        exp = "ok" if (en or mode == "M") else (2 if mut() != "cbo_enable_ignored" else "ok")
                        d = f"cbo.{op} with the menvcfg bit = {en}"
                        if mode == "U" and en:
                            # senvcfg's bit is WARL: U-mode also needs it
                            t.emit("csrr x9, senvcfg")
                            t.emit(f"andi x9, x9, {bitlo}")
                            L.either(
                                t,
                                "x9",
                                lambda op=op, d=d: L.word_window(t, "U", cbo(op), f"cbo.{op} (x8)", "ok", d),
                                lambda op=op, d=d: L.word_window(
                                    t, "U", cbo(op), f"cbo.{op} (x8)", 2, d + ", senvcfg 0"
                                ),
                            )
                        else:
                            L.word_window(t, mode, cbo(op), f"cbo.{op} (x8)", exp, d)

            if en:
                L.either(t, "x9", cbo_run, lambda: None)
            else:
                L.either(t, "x9", lambda: None, cbo_run)
        menvcfg_bits(t, False, bitlo)
        tests.append(t)

    t = new(suite, "menvcfg_cbie_warl_op", [*L.REQ, "S", "Zicbom"])
    t.extra_data += [".p2align 12", "sm_cbo_buf: .fill 4096, 1, 0x5a"]
    describe(
        t,
        context="CBIE is WARL; 10 is reserved. senvcfg.CBIE is set to 11 and read back; U-mode cases with "
        "senvcfg.CBIE = 00 expect illegal instruction.",
        plan="1. CBIE = 00: cbo.inval in S and U raises illegal instruction.\n2. CBIE = 01 and 11 (when they read "
        "back): it executes in S and U.\n3. Writing 10 reads back 00, 01 or 11.",
    )
    t.la("x8", "sm_cbo_buf")
    t.li("x6", 0x30)
    t.emit("csrs senvcfg, x6")
    for v in (0, 1, 3):
        menvcfg_bits(t, False, 0x30)
        if v:
            menvcfg_bits(t, True, v << 4)
        t.emit("csrr x9, menvcfg")
        t.emit("andi x9, x9, 0x30")
        t.emit(f"addi x9, x9, {-(v << 4)}")
        t.emit("seqz x9, x9")

        def run(v: int = v) -> None:
            L.word_window(t, "S", cbo("inval"), "cbo.inval (x8)", "ok" if v else 2, f"cbo.inval with CBIE = {v}")
            if not v:
                L.word_window(t, "U", cbo("inval"), "cbo.inval (x8)", 2, f"cbo.inval with CBIE = {v}")
                return
            # senvcfg.CBIE is WARL: U-mode executes only if it is not 00
            t.emit("csrr x9, senvcfg")
            t.emit("andi x9, x9, 0x30")
            L.either(
                t,
                "x9",
                lambda: L.word_window(t, "U", cbo("inval"), "cbo.inval (x8)", "ok", f"cbo.inval with CBIE = {v}"),
                lambda: L.word_window(t, "U", cbo("inval"), "cbo.inval (x8)", 2, f"CBIE = {v}, senvcfg.CBIE = 00"),
            )

        L.either(t, "x9", run, lambda: None)
    lab = t.label("r")
    menvcfg_bits(t, False, 0x30)
    menvcfg_bits(t, True, 0x20)
    t.emit(f"{lab}:", 0)
    t.emit("csrr x7, menvcfg")
    t.emit("andi x7, x7, 0x30")
    t.check("x7", [0, 0x10, 0x30], lab, "CBIE after writing the reserved 10")
    menvcfg_bits(t, False, 0x30)
    tests.append(t)

    for rule, bit, name, ext in (
        ("menvcfg_pbmte_henvcfg_pbmte_rdonly0", 30, "PBMTE", "Svpbmt"),
        ("menvcfg_adue_henvcfg_adue_rdonly0", 29, "ADUE", "Svadu"),
    ):
        t = new(suite, rule, [*L.REQ, "H", ext])
        describe(
            t,
            context="henvcfg is restored afterwards.",
            plan=f"1. menvcfg.{name} = 0: after setting henvcfg.{name} it reads 0.\n2. menvcfg.{name} = 1 (when "
            "writable): the write may stick (no constraint), and both are restored.",
        )
        lab = t.label("h")
        menvcfg_bits(t, False, 0, 1 << bit)
        with t.rv64_only():
            t.emit("csrr x9, 0x60A  // henvcfg")
            t.load("x6", 1 << (32 + bit))
            t.emit(f"{lab}:", 0)
            t.emit("csrs 0x60A, x6")
            t.emit("csrr x7, 0x60A")
            t.emit("csrw 0x60A, x9")
            t.check_masked("x7", X(0, 1 << (32 + bit)), 0, lab, f"henvcfg.{name} read-only 0 when menvcfg.{name} = 0")
        with t.rv32_only():
            t.emit("csrr x9, 0x61A  // henvcfgh")
            t.load("x6", 1 << bit)
            t.emit(f"{lab}:", 0)
            t.emit("csrs 0x61A, x6")
            t.emit("csrr x7, 0x61A")
            t.emit("csrw 0x61A, x9")
            t.check_masked("x7", 1 << bit, 0, lab, f"henvcfgh.{name} read-only 0 when menvcfg.{name} = 0")
        tests.append(t)

    # ---- mseccfg ----
    t = new(suite, "mseccfg_presence")
    describe(
        t,
        context="mseccfg exists when Zkr, Smmpm, Zicfilp or Smepmp is implemented (MSECCFG_SUPPORTED).",
        plan="1. With one of them: mseccfg (0x747) reads without a trap.\n2. Without any: reading it raises illegal "
        "instruction.",
    )
    with t.only_if("defined(MSECCFG_SUPPORTED)"):
        L.csr_window(t, "M", 0x747, "mseccfg", L.FORMS[0], "ok", "mseccfg present")
    with t.only_if("!defined(MSECCFG_SUPPORTED)"):
        L.csr_window(t, "M", 0x747, "mseccfg", L.FORMS[0], "illegal", "mseccfg absent")
    tests.append(t)

    t = new(suite, "mseccfgh_presence")
    describe(
        t,
        plan="1. RV32 with mseccfg: mseccfgh (0x757) reads without a trap.\n2. RV64, or without mseccfg: "
        "reading 0x757 raises illegal instruction.",
    )
    with t.only_if(f"defined(MSECCFG_SUPPORTED) && {RV32}"):
        L.csr_window(t, "M", 0x757, "mseccfgh", L.FORMS[0], "ok", "RV32")
    with t.only_if(f"!defined(MSECCFG_SUPPORTED) || {RV64}"):
        L.csr_window(t, "M", 0x757, "mseccfgh", L.FORMS[0], "illegal", "absent")
    tests.append(t)

    for rule, bit, name, cond in (
        ("mseccfg_useed_rdonly0", 8, "USEED", f"!defined(ZKR_SUPPORTED) || {NO_U}"),
        ("mseccfg_sseed_rdonly0", 9, "SSEED", f"!defined(ZKR_SUPPORTED) || {NO_S}"),
    ):
        t = new(suite, rule)
        describe(
            t,
            context="Only this bit is written (csrs/csrc); mseccfg's sticky Smepmp bits are not touched.",
            plan=f"1. With mseccfg but without Zkr (or the mode): after csrs of {name} (bit {bit}) it reads 0.",
        )
        with t.only_if(f"defined(MSECCFG_SUPPORTED) && ({cond})"):
            lab = t.label("b")
            t.li("x6", 1 << bit)
            t.emit(f"{lab}:", 0)
            t.emit("csrs 0x747, x6")
            t.emit("csrr x7, 0x747")
            t.emit("csrc 0x747, x6")
            t.check_masked("x7", 1 << bit, 0, lab, f"{name} read-only 0")
        tests.append(t)

    for rule, bit, name, mode in (
        ("mseccfg_useed_u_mode_op", 8, "USEED", "U"),
        ("mseccfg_sseed_sorhs_mode_op", 9, "SSEED", "S"),
    ):
        t = new(suite, rule, [*L.REQ, "Zkr", mode])
        describe(
            t,
            context="seed (0x015) must be accessed with a read-write instruction (csrrw). The field is set with csrs "
            "and read back (WARL).",
            plan=f"1. {name} = 0: csrrw seed and csrrs seed (read only) in {mode}-mode raise illegal instruction.\n"
            f"2. {name} = 1: csrrw seed executes without a trap; csrrs seed, x0 still raises illegal instruction.",
        )
        t.li("x6", 1 << bit)
        t.emit("csrc 0x747, x6")
        t.li("x6", 0)
        L.csr_window(t, mode, 0x015, "seed", ("csrrw x7, {c}, x6", 1, 7, 6, "csrrw"), "illegal", f"{name} = 0")
        L.csr_window(t, mode, 0x015, "seed", L.FORMS[0], "illegal", f"{name} = 0")
        t.li("x6", 1 << bit)
        t.emit("csrs 0x747, x6")
        t.emit("csrr x9, 0x747")
        t.emit(f"srli x9, x9, {bit}")
        t.emit("andi x9, x9, 1")

        def on(mode: str = mode, name: str = name, t: TestFile = t) -> None:
            t.li("x6", 0)
            L.csr_window(
                t,
                mode,
                0x015,
                "seed",
                ("csrrw x7, {c}, x6", 1, 7, 6, "csrrw"),
                "illegal" if mut() == "seed_enable_ignored" else "ok",
                f"{name} = 1",
            )
            L.csr_window(t, mode, 0x015, "seed", L.FORMS[0], "illegal", f"{name} = 1")

        L.either(t, "x9", on, lambda: None)
        t.li("x6", 1 << bit)
        t.emit("csrc 0x747, x6")
        tests.append(t)
    return tests


FMV_W_X = (0x78 << 25) | (6 << 15) | (1 << 7) | 0x53  # fmv.w.x f1, x6
FMV_X_W = (0x70 << 25) | (1 << 15) | (7 << 7) | 0x53  # fmv.x.w x7, f1
VSETVLI = (7 << 12) | (7 << 7) | 0x57  # vsetvli x7, x0, e8, m1
SD_BIT = X(1 << 31, 1 << 63)


def gen_mstatus2(suite: str) -> list[TestFile]:
    tests = []
    F, V = "defined(F_SUPPORTED)", "defined(V_SUPPORTED)"

    def fs_writes(t: TestFile, mask: int, shift: int, name: str, ro0: bool, maybe: bool = False) -> None:
        for v in (3, 0, 1, 2):
            lab = t.label(name)
            t.emit(f"{lab}:", 0)
            set_field(t, "mstatus", mask, v << shift)
            field(t, "x7", "mstatus", mask, shift)
            if ro0:
                exp = [0, v] if maybe and v in (0, 3) else (0 if not maybe else [0, v, 3])
            else:
                exp = {0: 0, 3: 3, 1: [1, 3], 2: [2, 3]}[v]
                if mut() == "fs_ro0" and name == "FS":
                    exp = 0
            t.check("x7", exp, lab, f"{name} after writing {v}")
        set_field(t, "mstatus", mask, 0)

    t = new(suite, "mstatus_fs_acc1", [*L.REQ, "F"])
    describe(
        t,
        context="Without dirtiness tracking Initial and Clean become Dirty (mstatus_fs_no_dirty_track).",
        plan="1. Write FS = 3, 0, 1, 2: reads 3, 0, 1 or 3, 2 or 3 (not read-only 0).",
    )
    fs_writes(t, L.FS, 13, "FS", False)
    tests.append(t)

    t = new(suite, "mstatus_fs_acc2")
    describe(t, plan="1. Without F and without S-mode: FS reads 0 after writing 3, 0, 1 and 2.")
    with t.only_if(f"!{F} && {NO_S}"):
        fs_writes(t, L.FS, 13, "FS", True)
    tests.append(t)

    t = new(suite, "mstatus_fs_rdonly0_s_no_F")
    describe(
        t,
        context="FS may be read-only 0 or writable here.",
        plan="1. With S-mode and without F: after writing v = 3, 0, 1, 2, FS reads 0 or a value legal for a "
        "writable FS.",
    )
    with t.only_if(f"!{F} && {S}"):
        fs_writes(t, L.FS, 13, "FS", True, maybe=True)
    tests.append(t)

    t = new(suite, "mstatus_vs_acc1", [*L.REQ, "V"])
    describe(t, plan="1. Write VS = 3, 0, 1, 2: reads 3, 0, 1 or 3, 2 or 3 (not read-only 0).")
    fs_writes(t, L.VS, 9, "VS", False)
    tests.append(t)

    t = new(suite, "mstatus_vs_acc2")
    describe(t, plan="1. Without V and without S-mode: VS reads 0 after writing 3, 0, 1 and 2.")
    with t.only_if(f"!{V} && {NO_S}"):
        fs_writes(t, L.VS, 9, "VS", True)
    tests.append(t)

    t = new(suite, "mstatus_vs_rdonly0_s_no_V")
    describe(t, plan="1. With S-mode and without V: after writing v, VS reads 0 or a value legal for a writable VS.")
    with t.only_if(f"!{V} && {S}"):
        fs_writes(t, L.VS, 9, "VS", True, maybe=True)
    tests.append(t)

    for rule in ("mstatus_sd_formula", "mstatus_sd_rdonly0", "mstatus_sd_acc"):
        t = new(suite, rule)
        describe(
            t,
            context="SD is bit MXLEN-1. FS and VS are written with each of their values; the values that read back "
            "decide the expected SD.",
            plan={
                "mstatus_sd_formula": "1. For FS, VS in {0, 1, 2, 3} (as far as writable): SD = (FS == 3) or (VS == 3) "
                "or (XS == 3).",
                "mstatus_sd_rdonly0": "1. With FS, VS and XS all reading 0 after writes of 3: SD reads 0.",
                "mstatus_sd_acc": "1. csrs and csrc of SD do not change it; writing mstatus with SD flipped does not "
                "change it.",
            }[rule],
        )
        if rule == "mstatus_sd_acc":
            for op in ("csrs", "csrc"):
                lab = t.label("sd")
                t.load("x6", SD_BIT)
                t.emit("csrr x8, mstatus")
                t.emit(f"{lab}:", 0)
                t.emit(f"{op} mstatus, x6")
                t.emit("csrr x7, mstatus")
                t.emit("xor x7, x7, x8")
                t.check_masked("x7", SD_BIT, 0, lab, f"SD unchanged by {op}")
        else:
            pairs = [(f, v) for f in range(4) for v in range(4)] if rule == "mstatus_sd_formula" else [(3, 3)]
            for fv, vv in pairs:
                lab = t.label("sd")
                t.emit(f"{lab}:", 0)
                set_field(t, "mstatus", L.FS | L.VS, (fv << 13) | (vv << 9))
                t.emit("csrr x7, mstatus")
                if rule == "mstatus_sd_rdonly0":
                    t.load("x5", L.FS | L.VS | L.XS)
                    t.emit("and x8, x7, x5")
                    t.emit("seqz x8, x8  // 1: FS, VS and XS read 0")
                    t.emit("srli x9, x7, 31")
                    with t.rv64_only():
                        t.emit("srli x9, x7, 63")
                    t.emit("andi x9, x9, 1")
                    t.emit("and x9, x9, x8  // SD set while all are 0")
                    t.emit("seqz x9, x9")
                    t.check_bool("x9", lab, "SD = 0 when FS, VS and XS are read-only 0")
                    continue
                # dirty = any of FS, VS, XS == 3
                t.emit("srli x8, x7, 13")
                t.emit("andi x8, x8, 3")
                t.emit("addi x8, x8, -3")
                t.emit("seqz x8, x8")
                t.emit("srli x9, x7, 9")
                t.emit("andi x9, x9, 3")
                t.emit("addi x9, x9, -3")
                t.emit("seqz x9, x9")
                if mut() != "sd_ignores_vs":
                    t.emit("or x8, x8, x9")
                t.emit("srli x9, x7, 15")
                t.emit("andi x9, x9, 3")
                t.emit("addi x9, x9, -3")
                t.emit("seqz x9, x9")
                t.emit("or x8, x8, x9")
                with t.rv64_only():
                    t.emit("srli x9, x7, 63")
                with t.rv32_only():
                    t.emit("srli x9, x7, 31")
                t.emit("xor x9, x9, x8")
                t.emit("seqz x9, x9")
                t.check_bool("x9", lab, f"SD after FS = {fv}, VS = {vv}: SD = (FS==3 | VS==3 | XS==3)")
            set_field(t, "mstatus", L.FS | L.VS, 0)
        tests.append(t)

    t = new(suite, "mstatus_fs_vs_xs_off_op")
    describe(
        t,
        context="Instructions are .word encodings. fcsr (0x003) and vl (0xC20) are F and V state.",
        plan="1. F: with FS = Off, fmv.w.x and csrr fcsr raise illegal instruction in M, S and U; with FS = Initial "
        "they execute.\n2. V: with VS = Off, vsetvli and csrr vl raise illegal instruction in M, S and U; with "
        "VS = Initial they execute.",
    )
    for cond, mask, shift, items in (
        (F, L.FS, 13, [(FMV_W_X, "fmv.w.x f1, x6"), (L.enc_csr(0x003, 2, 7, 0), "csrr x7, fcsr")]),
        (V, L.VS, 9, [(VSETVLI, "vsetvli x7, x0, e8, m1"), (L.enc_csr(0xC20, 2, 7, 0), "csrr x7, vl")]),
    ):
        with t.only_if(cond):
            for st in (0, 1):
                set_field(t, "mstatus", mask, st << shift)

                def off_case(mode: str, st: int = st, items: list[tuple[int, str]] = items) -> None:
                    for e, note in items:
                        exp = ("ok" if mut() == "off_ignored" else 2) if st == 0 else "ok"
                        L.word_window(t, mode, e, note, exp, f"{note} with status {st}")

                L.each_mode(t, off_case)
            set_field(t, "mstatus", mask, 0)
    tests.append(t)

    t = new(suite, "mstatus_fs_wr", [*L.REQ, "F"])
    describe(
        t,
        plan="1. With FS = Dirty, f1 = 0x12345678 (fmv.w.x).\n2. FS = Off, then FS = Initial: f1 still reads "
        "0x12345678 (fmv.x.w, sign-extended on RV64).\n3. FS = Off, then Clean: f1 unchanged.",
    )
    set_field(t, "mstatus", L.FS, 3 << 13)
    t.li("x6", 0x12345678)
    t.emit(f".word {hex(FMV_W_X)}  // fmv.w.x f1, x6")
    for st in (1, 2):
        lab = t.label("f")
        set_field(t, "mstatus", L.FS, 0)
        t.emit(f"{lab}:", 0)
        set_field(t, "mstatus", L.FS, st << 13)
        t.li("x7", 0)
        t.emit(f".word {hex(FMV_X_W)}  // fmv.x.w x7, f1")
        t.check("x7", 0 if mut() == "fs_init_clears" else 0x12345678, lab, f"f1 kept across FS = Off -> {st}")
    set_field(t, "mstatus", L.FS, 0)
    tests.append(t)

    t = new(suite, "mstatus_vs_wr", [*L.REQ, "V"])
    describe(
        t,
        plan="1. With VS = Dirty, vsetvli sets vl = VLMAX (e8, m1).\n2. VS = Off, then Initial: vl still reads "
        "the same value.",
    )
    set_field(t, "mstatus", L.VS, 3 << 9)
    t.emit(f".word {hex(VSETVLI)}  // vsetvli x7, x0, e8, m1")
    t.emit("mv x9, x7")
    lab = t.label("v")
    set_field(t, "mstatus", L.VS, 0)
    t.emit(f"{lab}:", 0)
    set_field(t, "mstatus", L.VS, 1 << 9)
    t.emit("csrr x8, vl")
    t.emit("sub x8, x8, x9")
    t.check("x8", 0, lab, "vl kept across VS = Off -> Initial")
    set_field(t, "mstatus", L.VS, 0)
    tests.append(t)

    t = new(suite, "mstatus_fs_vs_xs_update_indep_priv")
    describe(
        t,
        context="An instruction that modifies the state must leave the status Dirty, in whatever mode it runs.",
        plan="1. F: FS = Initial, then fmv.w.x f1 with a new value in M, S and U: FS reads Dirty (3) afterwards.\n"
        "2. V: VS = Initial, then vsetvli in M, S and U: VS reads Dirty.",
    )
    for cond, mask, shift, e, note in (
        (F, L.FS, 13, FMV_W_X, "fmv.w.x f1, x6"),
        (V, L.VS, 9, VSETVLI, "vsetvli x7, x0, e8, m1"),
    ):
        with t.only_if(cond):

            def body(mode: str, mask: int = mask, shift: int = shift, e: int = e, note: str = note) -> None:
                set_field(t, "mstatus", mask, 1 << shift)
                t.li("x6", t.rand(20))
                lab = L.word_window(t, mode, e, note, "ok", note)
                field(t, "x7", "mstatus", mask, shift)
                t.check(
                    "x7",
                    1 if mut() == "no_dirty_below_m" and mode != "M" else 3,
                    lab,
                    f"status Dirty after {note} in {mode}-mode",
                )

            L.each_mode(t, body)
            set_field(t, "mstatus", mask, 0)
    tests.append(t)

    # ---- SXL / UXL (RV64) ----
    for rule, shift, cond, name in (
        ("mstatus_sxl_acc_mxlen64", 34, S, "SXL"),
        ("mstatus_uxl_acc_mxlen64", 32, U, "UXL"),
    ):
        t = new(suite, rule, rv64=True)
        describe(
            t,
            context="RV64 only. The test never enters S or U while the field may hold 1; it is restored to its "
            "original value.",
            plan=f"1. With the mode: after writing {name} = 0, 1, 2, 3 it reads 1 or 2 (it encodes an XLEN).\n"
            f"2. Without the mode: {name} reads 0 after each write.",
        )
        t.emit("csrr x9, mstatus")
        for c, has in ((cond, True), (f"!({cond})", False)):
            with t.only_if(c):
                for v in range(4):
                    lab = t.label(name)
                    t.emit(f"{lab}:", 0)
                    set_field(t, "mstatus", 3 << shift, v << shift)
                    field(t, "x7", "mstatus", 3 << shift, shift)
                    exp = [1, 2] if has else 0
                    if mut() == "xl_reserved" and has and v in (0, 3):
                        exp = v
                    t.check("x7", exp, lab, f"{name} after writing {v}")
        t.emit("csrw mstatus, x9")
        tests.append(t)

    t = new(suite, "mstatus_uxl_legal_vals_smode", [*L.REQ, "S"], rv64=True)
    describe(
        t,
        context="RV64 only. mstatus is restored afterwards.",
        plan="1. For SXL, UXL written to every pair in {1, 2}: UXL reads <= SXL.",
    )
    t.emit("csrr x9, mstatus")
    for sv in (1, 2):
        for uv in (1, 2):
            lab = t.label("xl")
            t.emit(f"{lab}:", 0)
            set_field(t, "mstatus", 0xF << 32, (sv << 34) | (uv << 32))
            field(t, "x7", "mstatus", 3 << 34, 34)
            field(t, "x8", "mstatus", 3 << 32, 32)
            t.emit("sltu x8, x7, x8")
            t.emit("seqz x8, x8")
            t.check_bool("x8", lab, f"UXL <= SXL after writing SXL = {sv}, UXL = {uv}")
    t.emit("csrw mstatus, x9")
    tests.append(t)

    # ---- TVM / TSR effects ----
    t = new(suite, "mstatus_tvm_op", [*L.REQ, "S"])
    describe(
        t,
        context="TVM is writable only when satp has a translation mode (mstatus_tvm_acc); the TVM = 1 cases run when "
        "TVM reads back 1. sfence.vma = 0x12000073, sinval.vma = 0x16000073 (Svinval).",
        plan="1. TVM = 0: in S-mode csrr satp, csrw satp (0), sfence.vma (and sinval.vma) execute.\n2. TVM = 1: each "
        "raises illegal instruction in S-mode.\n3. TVM = 1: in M-mode they execute.",
    )
    L.csr_bits(t, "mstatus", TVM, False)
    items = [
        (L.enc_csr(0x180, 2, 7, 0), "csrr x7, satp", None),
        (L.enc_csr(0x180, 1, 0, 0), "csrw satp, x0", None),
        (0x12000073, "sfence.vma", None),
        (0x16000073, "sinval.vma", "defined(SVINVAL_SUPPORTED)"),
    ]

    def run(mode: str, exp: Expect, sel: str | None) -> None:
        for e, note, cond in items:
            if cond == sel:
                L.word_window(t, mode, e, note, exp, f"{note} with TVM")

    for sel in (None, "defined(SVINVAL_SUPPORTED)"):

        def blk(sel: str | None = sel) -> None:
            run("S", "ok", sel)
            L.csr_bits(t, "mstatus", TVM, True)
            t.emit("csrr x9, mstatus")
            t.load("x5", TVM)
            t.emit("and x9, x9, x5")

            def tvm1() -> None:
                run("S", "ok" if mut() == "tvm_ignored" else 2, sel)
                run("M", "ok", sel)

            L.either(t, "x9", tvm1, lambda: None)
            L.csr_bits(t, "mstatus", TVM, False)

        guard(t, sel, blk)
    tests.append(t)

    t = new(suite, "mstatus_tsr_op", [*L.REQ, "S"])
    describe(
        t,
        context="SRET with SPP = S and sepc = the next instruction stays in S-mode and continues there.",
        plan="1. TSR = 0: sret in S-mode executes (no trap).\n2. TSR = 1: sret in S-mode raises illegal instruction "
        "(xtval 0 or 0x10200073).\n3. TSR = 1: sret in M-mode executes (to S-mode at sepc).",
    )
    for tsr in (0, 1):
        L.csr_bits(t, "mstatus", TSR, bool(tsr))
        nxt = t.label("nxt")
        t.la("x6", nxt)
        t.emit("csrw sepc, x6")
        L.csr_bits(t, "mstatus", SPP, True)
        exp = 2 if tsr and mut() != "tsr_ignored" else "ok"
        L.win(t, "S", ["sret", f"{nxt}:"], exp, f"sret with TSR = {tsr}", [0, 0x10200073])
    nxt = t.label("nxt")
    t.la("x6", nxt)
    t.emit("csrw sepc, x6")
    L.csr_bits(t, "mstatus", SPP, True)
    t.allow(1)
    lab = t.label("msret")
    t.emit(f"{lab}:", 0)
    t.emit("sret")
    t.emit(f"{nxt}:", 0)
    t.emit("csrr x7, sstatus  // S-mode")
    t.leave()
    t.outcome("ok", lab, "sret in M-mode with TSR = 1")
    L.csr_bits(t, "mstatus", TSR, False)
    tests.append(t)

    # ---- endianness ----
    for rule, name, cond, mode in (
        ("mstatus_mbe_op", "MBE", None, "M"),
        ("mstatus_sbe_op", "SBE", S, "S"),
        ("mstatus_ube_op", "UBE", U, "U"),
    ):
        t = new(suite, rule)
        t.extra_data += [".p2align 3", "sm_be_word: .word 0x11223344, 0"]
        bit64 = {"MBE": 37, "SBE": 36, "UBE": 6}[name]
        describe(
            t,
            context=f"{name} is WARL (often read-only 0); the test sets it and runs only if it reads back 1. "
            + ("No trap happens while MBE = 1." if name == "MBE" else f"{mode}-mode code runs with {name} = 1.")
            + " MBE, SBE and UBE (and RV32 mstatush, which holds MBE and SBE) exist from Sm 1.12, so the test is "
            "empty on earlier harts (SM1P12P0_OR_LATER_SUPPORTED)."
            + " Instruction fetch stays little-endian (endianness_inst_fetch_little), which the code itself relies on.",
            plan=f"1. {name} = 1: lw in {mode}-mode of the word stored as 0x11223344 (little-endian) reads "
            "0x44332211; sw in that mode of 0x55667788 is read back by M-mode (MBE = 0) as 0x88776655.\n2. "
            f"{name} is cleared.",
        )

        def be(name: str = name, bit64: int = bit64, mode: str = mode, t: TestFile = t) -> None:
            def setbit(on: bool, t: TestFile = t) -> None:
                op = "csrs" if on else "csrc"
                if bit64 < 32:
                    t.li("x5", 1 << bit64)
                    t.emit(f"{op} mstatus, x5")
                else:
                    with t.rv64_only():
                        t.emit("li x5, 1  // no table load: loads may be big-endian here")
                        t.emit(f"slli x5, x5, {bit64}")
                        t.emit(f"{op} mstatus, x5")
                    with t.rv32_only():
                        t.li("x5", 1 << (bit64 - 32))
                        t.emit(f"{op} 0x310, x5  // mstatush")

            setbit(True)
            if bit64 < 32:
                t.emit("csrr x9, mstatus")
                t.emit(f"srli x9, x9, {bit64}")
            else:
                with t.rv64_only():
                    t.emit("csrr x9, mstatus")
                    t.emit(f"srli x9, x9, {bit64}")
                with t.rv32_only():
                    t.emit("csrr x9, 0x310")
                    t.emit(f"srli x9, x9, {bit64 - 32}")
            t.emit("andi x9, x9, 1")

            def run(t: TestFile = t) -> None:
                t.la("x8", "sm_be_word")
                t.li("x6", 0x55667788)
                lab = t.label("be")
                if mode == "M":
                    t.emit(f"{lab}:", 0)
                    t.emit("lw x7, 0(x8)")
                    t.emit("sw x6, 4(x8)")
                    setbit(False)
                else:
                    t.allow(0)
                    t.enter(mode)
                    t.emit(f"{lab}:", 0)
                    t.emit("lw x7, 0(x8)")
                    t.emit("sw x6, 4(x8)")
                    t.leave()
                    setbit(False)
                swapped = 0x11223344 if mut() == "be_ignored" else 0x44332211
                t.check("x7", swapped, lab, f"lw with {name} = 1 is big-endian")
                t.emit("lw x7, 4(x8)")
                t.check("x7", X(0x88776655, 0xFFFFFFFF88776655), lab, f"sw with {name} = 1 stored big-endian")

            L.either(t, "x9", run, lambda: None)
            setbit(False)

        with t.only_if(SM1P12):
            guard(t, cond, be)
        tests.append(t)
    return tests


MRET, SRET = 0x30200073, 0x10200073
MT = "defined(RVMODEL_MTIMECMP_ADDRESS) && defined(RVMODEL_MTIME_ADDRESS)"


def mtimecmp_write(t: TestFile, hi: str, lo: str) -> None:
    """mtimecmp = hi:lo (registers; RV64 uses lo as the full value). RV32 writes the low half to all ones first so
    no intermediate value is earlier than both the old and the new one."""
    t.emit("LA(x5, RVMODEL_MTIMECMP_ADDRESS)", 2)
    with t.rv64_only():
        t.emit(f"sd {lo}, 0(x5)")
    with t.rv32_only():
        t.emit("li x4, -1")
        t.emit("sw x4, 0(x5)")
        t.emit(f"sw {hi}, 4(x5)")
        t.emit(f"sw {lo}, 0(x5)")


def gen_xret_timer(suite: str) -> list[TestFile]:
    tests = []

    t = new(suite, "xret_in_lower_mode")
    describe(t, plan="1. mret in S and U, and sret in U, raise illegal instruction (xtval 0 or the encoding).")
    for mode in ("S", "U"):
        L.guard(
            t,
            L.MODE_COND[mode],
            lambda mode=mode: L.word_window(
                t, mode, MRET, "mret", "ok" if mut() == "mret_below_m" else 2, "mret below M"
            ),
        )
    with t.only_if(f"{S} && {U}"):
        L.word_window(t, "U", SRET, "sret", 2, "sret in U")
    tests.append(t)

    t = new(suite, "xret_op")
    describe(
        t,
        context="The instruction after the xRET sets x7 = 1 and is skipped when the xRET jumps to xepc, where x7 = 2 "
        "is set.",
        plan="1. MRET with MPP = M and mepc = a label two instructions ahead: execution continues at the label.\n"
        "2. With S-mode: SRET in M-mode with SPP = S and sepc = a label: execution continues there in S-mode.",
    )
    for x in ("m", "s"):

        def body(x: str = x) -> None:
            tgt, lab = t.label("tgt"), t.label("ret")
            t.la("x6", tgt)
            t.emit(f"csrw {x}epc, x6")
            if x == "m":
                L.csr_bits(t, "mstatus", MPP, True)
            else:
                L.csr_bits(t, "mstatus", SPP, True)
            t.li("x7", 0)
            t.emit(f"{lab}:", 0)
            t.emit(f"{x}ret")
            t.emit("li x7, 1")
            t.emit(f"{tgt}:", 0)
            t.emit("ori x7, x7, 2")
            if x == "s":
                t.leave()
            t.check("x7", 3 if mut() == "xret_falls_through" else 2, lab, f"{x}ret jumps to {x}epc")

        guard(t, None if x == "m" else S, body)
    tests.append(t)

    t = new(suite, "xret_in_higher_mode", [*L.REQ, "S"])
    describe(
        t,
        plan="1. SRET executed in M-mode with SPP = U returns to U-mode (an ebreak there is taken from U), and "
        "with SPP = S to S-mode (from S).",
    )
    for spp, mode in ((0, "U"), (1, "S")):
        tgt = t.label("tgt")
        t.la("x6", tgt)
        t.emit("csrw sepc, x6")
        L.csr_bits(t, "mstatus", SPP, bool(spp))
        t.allow(1)
        t.emit("sret")
        t.emit(f"{tgt}:", 0)
        t.emit(L.EBREAK)
        t.leave()
        t.outcome(3, tgt, f"ebreak after SRET from M-mode with SPP = {spp}", [0, tgt], origin=mode)
    tests.append(t)

    t = new(suite, "sret_presence", [*L.REQ, "S"])
    describe(
        t,
        context="TSR = 0.",
        plan="1. sret in S-mode with SPP = S and sepc = the next instruction executes without a trap.",
    )
    L.csr_bits(t, "mstatus", L.TSR, False)
    nxt = t.label("nxt")
    t.la("x6", nxt)
    t.emit("csrw sepc, x6")
    L.csr_bits(t, "mstatus", SPP, True)
    L.win(t, "S", ["sret", f"{nxt}:"], "ok", "sret")
    tests.append(t)

    t = new(suite, "mret_presence")
    describe(t, plan="1. mret in M-mode with MPP = M and mepc = the next instruction executes without a trap.")
    nxt = t.label("nxt")
    t.la("x6", nxt)
    t.emit("csrw mepc, x6")
    L.csr_bits(t, "mstatus", MPP, True)
    L.win(t, "M", ["mret", f"{nxt}:"], "ok", "mret")
    tests.append(t)

    # ---- mcause interrupt bit ----
    t = new(suite, "mcause_intr_op")
    describe(
        t,
        context="SSI on S-mode harts, else MTI or MSI.",
        plan="1. An interrupt sets mcause's Interrupt bit "
        "(MXLEN-1) with its code.\n2. ebreak leaves it clear (cause 3).",
    )
    for src, cond in (
        ("SSI", S),
        ("MTI", f"{NO_S} && defined(RVMODEL_MTIMECMP_ADDRESS)"),
        ("MSI", f"{NO_S} && !defined(RVMODEL_MTIMECMP_ADDRESS) && defined(RVMODEL_MSIP_ADDRESS)"),
    ):
        with t.only_if(cond):
            sr = L.SRC[src]
            t.emit("csrci mstatus, 8")
            t.emit("csrw mie, x0")
            sr.raise_(t)
            t.li("x6", 1 << sr.cause)
            t.emit("csrs mie, x6")
            lab = t.label("i")
            t.allow(1)
            t.emit("csrsi mstatus, 8")
            t.emit(f"{lab}:", 0)
            L.wait(t, 40)
            t.emit("csrci mstatus, 8")
            t.outcome(
                sr.cause if mut() == "intr_bit_clear" else L.icause(sr.cause), lab, f"{src}", epc=False, origin="M"
            )
            t.emit("csrw mie, x0")
            sr.clear(t)
    L.win(t, "M", [L.EBREAK], 3, "ebreak", [0, "LAB"])
    tests.append(t)

    # ---- machine timer ----
    def mtip_is(t: TestFile, v: int, desc: str, settle: bool = True) -> None:
        lab = t.label("mtip")
        L.poll_mip(t, 7, v if settle else 1 - v, n=200 if settle else 40)
        t.emit(f"{lab}:", 0)
        t.emit("csrr x7, mip")
        t.emit("andi x7, x7, 0x80")
        t.check("x7", 0x80 if v else 0, lab, f"mip.MTIP after {desc}")

    t = new(suite, "mtime_intr_pending")
    describe(
        t,
        context="Needs RVMODEL_MTIME_ADDRESS and RVMODEL_MTIMECMP_ADDRESS. mie = 0, so MTIP is only observed. On RV32 "
        "mtimecmp is written low = all ones, high, low.",
        plan="1. mtimecmp = 0: MTIP becomes 1.\n2. mtimecmp = mtime + 2^40: MTIP becomes 0 and stays 0.\n3. mtimecmp "
        "= 2^63 and all ones: MTIP 0 (unsigned compare).\n4. mtimecmp = 0 again: 1.",
    )
    with t.only_if(MT):
        t.emit("csrw mie, x0")
        t.li("x6", 0)
        mtimecmp_write(t, "x6", "x6")
        mtip_is(t, 1, "mtimecmp = 0")
        t.emit("LA(x8, RVMODEL_MTIME_ADDRESS)", 2)
        with t.rv64_only():
            t.emit("ld x7, 0(x8)")
            t.emit("li x6, 1")
            t.emit("slli x6, x6, 40")
            t.emit("add x7, x7, x6")
            mtimecmp_write(t, "x6", "x7")
        with t.rv32_only():
            t.emit("lw x6, 4(x8)")
            t.emit("addi x6, x6, 256")
            t.li("x7", 0)
            mtimecmp_write(t, "x6", "x7")
        mtip_is(t, 0, "mtimecmp = mtime + 2^40")
        mtip_is(t, 0, "mtimecmp = mtime + 2^40 (steady)", settle=False)
        for hi, lo, note in ((0x80000000, 0, "2^63"), (0xFFFFFFFF, 0xFFFFFFFF, "all ones")):
            with t.rv64_only():
                t.load("x7", X(0, (hi << 32) | lo))
                mtimecmp_write(t, "x6", "x7")
            with t.rv32_only():
                t.load("x6", X(hi, 0))
                t.load("x7", X(lo, 0))
                mtimecmp_write(t, "x6", "x7")
            exp = 1 if mut() == "mtime_signed" and note == "2^63" else 0
            mtip_is(t, exp, f"mtimecmp = {note}", settle=bool(exp))
        t.li("x6", 0)
        mtimecmp_write(t, "x6", "x6")
        mtip_is(t, 1, "mtimecmp = 0 again")
        t.emit("RVTEST_CLR_MTIME_INT_M", 30)
    tests.append(t)

    t = new(suite, "mtime_intr_taken")
    describe(
        t,
        context="As in mtime_intr_pending.",
        plan="1. MTIP pending: with MTIE = 0 and MIE = 1 no interrupt; "
        "with MTIE = 1 and MIE = 0 none; with both, the interrupt (cause 7) is taken in M-mode.",
    )
    with t.only_if(MT):
        for mtie, mie in ((0, 1), (1, 0), (1, 1)):
            t.emit("csrci mstatus, 8")
            t.emit("csrw mie, x0")
            t.emit("RVTEST_SET_MTIME_INT_M", 30)
            L.poll_mip(t, 7, 1)
            if mtie:
                t.li("x6", 0x80)
                t.emit("csrs mie, x6")
            lab = t.label("t")
            t.allow(1)
            if mie:
                t.emit("csrsi mstatus, 8")
            t.emit(f"{lab}:", 0)
            L.wait(t, 40)
            t.emit("csrci mstatus, 8")
            exp = L.icause(7) if (mtie and mie) or (mut() == "mtie_ignored" and mie) else "ok"
            t.outcome(exp, lab, f"MTIP with MTIE = {mtie}, MIE = {mie}", epc=False, origin="M")
            t.emit("csrw mie, x0")
            t.emit("RVTEST_CLR_MTIME_INT_M", 30)
    tests.append(t)

    t = new(suite, "mtimecmp_rv32_wr")
    describe(
        t,
        context="RV32 only (passes trivially on RV64). Values are far in the future.",
        plan="1. sw 0x11111111 to mtimecmp[31:0] and 0x40000000 to mtimecmp[63:32]: both read back.\n2. sw "
        "0x50000000 to the high half: the low half still reads 0x11111111.\n3. sw 0x22222222 to the low half: "
        "the high half still reads 0x50000000.",
    )
    with t.only_if(f"{MT} && {RV32}"):
        lab = t.label("w")
        t.emit("LA(x8, RVMODEL_MTIMECMP_ADDRESS)", 2)
        t.li("x6", 0x40000000)
        t.emit("sw x6, 4(x8)")
        t.li("x6", 0x11111111)
        t.emit(f"{lab}:", 0)
        t.emit("sw x6, 0(x8)")
        t.emit("lw x7, 0(x8)")
        t.check("x7", 0x11111111, lab, "mtimecmp low half")
        t.emit("lw x7, 4(x8)")
        t.check("x7", 0x40000000, lab, "mtimecmp high half")
        t.li("x6", 0x50000000)
        t.emit("sw x6, 4(x8)")
        t.emit("lw x7, 0(x8)")
        t.check("x7", 0x11111111, lab, "low half unchanged by a high-half write")
        t.li("x6", 0x22222222)
        t.emit("sw x6, 0(x8)")
        t.emit("lw x7, 4(x8)")
        t.check("x7", 0x50000000, lab, "high half unchanged by a low-half write")
        t.emit("RVTEST_CLR_MTIME_INT_M", 30)
    tests.append(t)

    t = new(suite, "mtime_mtimecmp_rv64_wr", rv64=True)
    describe(
        t,
        context="RV64 only.",
        plan="1. sd of 0x4000_0001_2345_6789 to mtimecmp: ld reads it back, and lw of "
        "each half reads that half.\n2. Two ld of mtime: the second is not smaller.",
    )
    with t.only_if(MT):
        lab = t.label("w")
        t.emit("LA(x8, RVMODEL_MTIMECMP_ADDRESS)", 2)
        t.load("x6", 0x4000000123456789)
        t.emit(f"{lab}:", 0)
        t.emit("sd x6, 0(x8)")
        t.emit("ld x7, 0(x8)")
        t.emit("sub x7, x7, x6")
        t.check("x7", 0, lab, "mtimecmp ld reads the sd value")
        t.emit("lwu x7, 0(x8)")
        t.check("x7", 0x23456789, lab, "low half")
        t.emit("lwu x7, 4(x8)")
        t.check("x7", 0x40000001, lab, "high half")
        t.emit("LA(x8, RVMODEL_MTIME_ADDRESS)", 2)
        t.emit("ld x6, 0(x8)")
        t.emit("ld x7, 0(x8)")
        t.emit("sltu x7, x7, x6")
        t.check("x7", 0, lab, "mtime does not go backwards")
        t.emit("RVTEST_CLR_MTIME_INT_M", 30)
    tests.append(t)

    t = new(suite, "mtime_op")
    describe(
        t,
        context="Needs RVMODEL_MTIME_ADDRESS. The wait is long (about 16000 instructions) because some "
        "simulators advance mtime only between batches of several thousand instructions.",
        plan="1. mtime read before and after the wait: the second value is larger (RV32: compared as 64-bit).",
    )
    with t.only_if("defined(RVMODEL_MTIME_ADDRESS)"):
        lab = t.label("m")
        t.emit("LA(x8, RVMODEL_MTIME_ADDRESS)", 2)
        with t.rv64_only():
            t.emit("ld x6, 0(x8)")
            L.wait(t, 8000)
            t.emit(f"{lab}:", 0)
            t.emit("ld x7, 0(x8)")
            t.emit("sltu x7, x6, x7")
        with t.rv32_only():
            t.emit("lw x6, 0(x8)")
            t.emit("lw x9, 4(x8)")
            L.wait(t, 8000)
            t.emit(f"{lab}:", 0)
            t.emit("lw x7, 0(x8)")
            t.emit("lw x5, 4(x8)")
            t.emit("sltu x7, x6, x7  // low increased")
            t.emit("sltu x4, x9, x5  // high increased")
            t.emit("or x7, x7, x4")
        t.check_bool("x7", lab, "mtime increased")
    tests.append(t)

    t = new(suite, "msip_enc")
    describe(
        t,
        context="Needs RVMODEL_MSIP_ADDRESS. mie = 0.",
        plan="1. sw 0xFFFFFFFF to msip: it reads 1 (bits 31:1 "
        "read 0), and mip.MSIP becomes 1.\n2. sw 0: it reads 0 and mip.MSIP becomes 0.",
    )
    with t.only_if("defined(RVMODEL_MSIP_ADDRESS)"):
        t.emit("csrw mie, x0")
        lab = t.label("ms")
        t.emit("LA(x8, RVMODEL_MSIP_ADDRESS)", 2)
        t.emit("li x6, -1")
        t.emit(f"{lab}:", 0)
        t.emit("sw x6, 0(x8)")
        t.emit("lw x7, 0(x8)")
        t.check("x7", -1 if mut() == "msip_all_bits" else 1, lab, "msip reads 1")
        L.poll_mip(t, 3, 1)
        t.emit("csrr x7, mip")
        t.check_masked("x7", 8, 8, lab, "mip.MSIP = 1")
        t.emit("LA(x8, RVMODEL_MSIP_ADDRESS)", 2)
        t.emit("sw x0, 0(x8)")
        t.emit("lw x7, 0(x8)")
        t.check("x7", 0, lab, "msip reads 0")
        L.poll_mip(t, 3, 0)
        t.emit("csrr x7, mip")
        t.check_masked("x7", 8, 0, lab, "mip.MSIP = 0")
    tests.append(t)

    t = new(suite, "time_op_rdonly", [*L.REQ, "Zicntr"])
    describe(
        t,
        context="time may be emulated by the framework from mtime. mtime changes reach time eventually, so time is "
        "compared with an mtime read 500 iterations earlier and one read after. RV32 compares the high words.",
        plan="1. mtime(before, waited) <= time <= mtime(after).\n2. Writing time (csrrw, csrrs/csrrc with rs1 != x0, "
        "immediates) raises illegal instruction.",
    )
    with t.only_if("defined(RVMODEL_MTIME_ADDRESS)"):
        lab = t.label("tm")
        t.emit("LA(x8, RVMODEL_MTIME_ADDRESS)", 2)
        with t.rv64_only():
            t.emit("ld x6, 0(x8)")
            L.wait(t, 500)
            t.emit(f"{lab}:", 0)
            t.emit("csrr x7, time")
            t.emit("LA(x8, RVMODEL_MTIME_ADDRESS)", 2)
            t.emit("ld x9, 0(x8)")
        with t.rv32_only():
            t.emit("lw x6, 4(x8)")
            L.wait(t, 500)
            t.emit(f"{lab}:", 0)
            t.emit("csrr x7, timeh")
            t.emit("LA(x8, RVMODEL_MTIME_ADDRESS)", 2)
            t.emit("lw x9, 4(x8)")
        t.emit("sltu x6, x7, x6  // time < earlier mtime")
        t.emit("sltu x9, x9, x7  // later mtime < time")
        t.emit("or x6, x6, x9")
        t.check("x6", 0, lab, "time lies between the earlier and the later mtime")
    t.li("x6", 0)
    for f in L.WRITE_FORMS:
        if f[1] in (2, 3) and f[3] == 0:
            continue
        L.csr_window(t, "M", 0xC01, "time", f, "illegal", "read-only")
    tests.append(t)
    return tests


def gen() -> list[TestFile]:
    pmp_suite = "PMP" if SUITE == "Sm" else SUITE  # mutants write both suites into one directory
    tests = gen_misa(SUITE)
    tests += gen_mstatus(SUITE)
    tests += gen_traps(SUITE)
    tests += gen_traps2(SUITE)
    tests += gen_trapcsrs(SUITE)
    tests += gen_ids(SUITE)
    tests += gen_ints(SUITE)
    tests += gen_ints2(SUITE)
    tests += gen_wfi(SUITE)
    tests += gen_counters(SUITE)
    tests += gen_envcfg(SUITE)
    tests += gen_mstatus2(SUITE)
    tests += gen_xret_timer(SUITE)
    tests += pmplib.gen(pmp_suite)
    return tests


if __name__ == "__main__":
    for t in gen():
        print(t.write())
