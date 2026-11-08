#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate tests_ai/Smcdeleg and tests_ai/Ssccfg: counter delegation to S-mode (src/priv/smcdeleg.adoc, plus
menvcfg.CDE in machine.adoc).

Tests boot to S-mode and reach menvcfg, mcounteren, mcountinhibit (and mhpmevent/mhpmcounter with Sscofpmf)
through T-SBI. The rules about M-mode accesses ("While the privilege mode is M or S ...") also get an _Sm file that
boots to M-mode, and the mvip/mvien rule is M-mode only. Rules named Smcdeleg_* (and menvcfg_cde_op and the M-level
LCOFI rule) go in Smcdeleg/ and require Smcdeleg; rules named Ssccfg_* go in Ssccfg/ and require Ssccfg.

Delegated counter i is reached with siselect = 0x40 + i: sireg = counter (sireg4 = high half on RV32), sireg2 =
event selector / counter configuration (sireg5 = high half on RV32). The counter-enable bits are WARL, so every
expectation uses the bits read back.
"""

from __future__ import annotations

import os
import sys
from contextlib import nullcontext
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent))
from aigen import POOL_TRAP, TestFile, X
from cntrlib import (
    FORMS,
    INH_HI,
    ISSUE,
    LCOF,
    READ,
    SCOUNTINHIBIT,
    SCOUNTOVF,
    SIREG,
    SIREG_NAME,
    VSIREG,
    WRITE,
    H,
    cde,
    cde_read,
    csr_win,
    either,
    hx,
    inh,
    ld,
    m_op,
    men_write,
    st,
)

if TYPE_CHECKING:
    from cntrlib import Form

SUITE = "Smcdeleg"
MUT = os.environ.get("AI_MUTANT", "")
SRC = "src/priv/smcdeleg.adoc"
MAC = "src/priv/machine.adoc"
MARCH = "rv${XLEN}i_zicsr_zifencei"
ZICNTR, ZIHPM = "defined(ZICNTR_SUPPORTED)", "defined(ZIHPM_SUPPORTED)"
SCOF, CNTRPMF = "defined(SSCOFPMF_SUPPORTED)", "defined(SMCNTRPMF_SUPPORTED)"

MUTANTS = {
    "cde0_sireg_ok": "with menvcfg.CDE=0, sireg* accesses with siselect 0x40-0x5F do not trap",
    "sireg3_ok": "sireg3/sireg6 accesses with siselect 0x40-0x5F do not trap",
    "sireg4_rv64_ok": "RV64: sireg4/sireg5 accesses with siselect 0x40-0x5F do not trap",
    "sel41_ok": "siselect 0x41 (time) is accessible through sireg",
    "not_deleg_ok": "a counter whose mcounteren bit is clear is accessible through sireg",
    "cycle_instret_swapped": "siselect 0x40 aliases instret and 0x42 aliases cycle",
    "hpm_write_lost": "an S-mode sireg write of hpmcounter3 does not reach the counter",
    "cyclecfg_illegal": "sireg2 at siselect 0x40 raises illegal instruction even with Smcntrpmf",
    "hpmevent_minh_visible": "sireg2 reads hpmevent MINH",
    "hpmevent_minh_written": "an S-mode sireg2 write of MINH sets mhpmevent MINH",
    "hpmevent_of_ro": "mhpmevent OF cannot be written through sireg2",
    "sireg_rmw_as_write": "csrrs/csrrc forms of sireg on a delegated counter write the operand instead of setting or "
    "clearing bits",
    "scountinhibit_unmasked": "scountinhibit reads every mcountinhibit bit, delegated or not",
    "scountinhibit_writes_nondeleg": "an S-mode scountinhibit write also writes non-delegated mcountinhibit bits",
    "scountinhibit_cde0_ok": "scountinhibit is accessible from S-mode with menvcfg.CDE=0",
    "vs_scountinhibit_illegal": "VS-mode scountinhibit accesses with CDE=1 raise illegal instead of virtual",
    "vs_sireg_cde1_illegal": "VS-mode sireg accesses (vsiselect 0x40-0x5F) with CDE=1 raise illegal instead of virtual",
    "vs_sireg_cde0_virtual": "VS-mode sireg accesses with CDE=0 raise virtual instead of illegal",
    "hs_vsireg_ok": "HS-mode vsireg accesses with vsiselect 0x40-0x5F do not trap",
    "vs_vsiselect_ok": "VS-mode may access vsiselect directly",
    "vs_scountovf_ok": "VS-mode scountovf reads with CDE=1 do not trap",
    "hvien_lcofi_ro0": "hvien[13] is read-only zero",
    "mvip_lcofi_ro0": "mvip[13] is read-only zero",
    "cde_ignored": "menvcfg.CDE=0 does not disable scountinhibit",
    "cde_ro0": "menvcfg.CDE is read-only zero",
    "cfg_minh_visible": "sireg2/sireg5 at siselect 0x40/0x42 read mcyclecfg/minstretcfg MINH",
    "cfg_minh_written": "an S-mode sireg2/sireg5 write at siselect 0x40/0x42 writes mcyclecfg/minstretcfg MINH",
}

REQ_SM = ["I", "S", "Smcdeleg"]
REQ_SS = ["I", "S", "Ssccfg"]
EN, IMPL, SAVE_EN, SAVE_CI, TMP, TMP2 = 0, 1, 2, 3, 4, 5  # scratch slots


def out(name: str) -> str:
    return name if SUITE == "Smcdeleg" else SUITE


def new(rule: str, ext: str = "Ssccfg", required: list[str] | None = None, rv64: bool = False) -> TestFile:
    req = required or (REQ_SS if ext == "Ssccfg" else REQ_SM)
    t = TestFile(out(ext), rule, required=req, march=MARCH, boot="S", pool=POOL_TRAP, rv64=rv64)
    begin(t)
    return t


def new_sm(rule: str, ext: str = "Ssccfg", required: list[str] | None = None, rv64: bool = False) -> TestFile:
    req = required or ((REQ_SS if ext == "Ssccfg" else REQ_SM) + ["Sm"])
    t = TestFile(out(ext), rule, required=req, march=MARCH, boot="M", pool=POOL_TRAP, rv64=rv64, suffix="_Sm")
    begin(t)
    return t


def bmode(t: TestFile) -> str:
    """The boot mode of a test (always set in this suite)."""
    assert t.boot is not None
    return t.boot


def begin(t: TestFile) -> None:
    """Interrupts off; save mcounteren and mcountinhibit (restored by end())."""
    t.li("x6", 0xA)
    t.emit(f"csrc {'mstatus' if t.boot == 'M' else 'sstatus'}, x6")
    m_op(t, "READ", "CSR_MCOUNTEREN")
    st(t, "a0", SAVE_EN)
    m_op(t, "READ", "CSR_MCOUNTINHIBIT")
    st(t, "a0", SAVE_CI)


def end(t: TestFile) -> None:
    cde(t, False)
    ld(t, "a1", SAVE_EN)
    m_op(t, "WRITE", "CSR_MCOUNTEREN", "a1")
    ld(t, "a1", SAVE_CI)
    m_op(t, "WRITE", "CSR_MCOUNTINHIBIT", "a1")


def sel(t: TestFile, v: int, csr: str = "siselect") -> None:
    t.li("x6", v)
    t.emit(f"csrw {csr}, x6")


def all_en(t: TestFile) -> None:
    """mcounteren = all ones; slot EN = the bits read back."""
    men_write(t, -1, EN)


def bit_of(t: TestFile, dst: str, slot: int, n: int) -> None:
    ld(t, dst, slot)
    t.emit(f"srli {dst}, {dst}, {n}")
    t.emit(f"andi {dst}, {dst}, 1")


def sweep(
    t: TestFile,
    mode: str,
    sels: list[int],
    regs: list[int],
    expect: str,
    desc: str,
    all_forms: bool = True,
    vs: bool = False,
) -> None:
    """For each siselect value: write it (siselect, or vsiselect when vs), then access each sireg_n (vsireg_n when
    vs) with a read in a window in `mode` (all eight forms for the first register of the first value)."""
    csrsel = "CSR_VSISELECT" if vs else "siselect"
    table = VSIREG if vs else SIREG
    for i, s in enumerate(sels):
        sel(t, s, csrsel)
        for j, r in enumerate(regs):
            forms: list[Form] = FORMS if all_forms and i == 0 and j == 0 else [READ, WRITE] if j == 0 else [READ]
            name = ("v" if vs else "") + SIREG_NAME[r]
            for f in forms:
                t.li("x6", 0x5)
                csr_win(t, mode, table[r], name, f, expect, f"{desc}, {'vsiselect' if vs else 'siselect'} {s:#x}")


def check_sel(t: TestFile, v: int, csr: str = "siselect") -> None:
    lab = t.label("sel")
    t.emit(f"{lab}:", 0)
    t.emit(f"csrr x7, {csr}")
    t.check("x7", v, lab, f"{csr} holds {v:#x} (it supports 0..0xFFF)")


SELS = [0x40, 0x41, 0x42, 0x43, 0x50, 0x5F]


# ---------------------------------------------------------------- tests
def gen() -> list[TestFile]:
    tests: list[TestFile] = []
    for f in (
        t_tandem,
        t_cde_en,
        t_menvcfg_cde_op,
        t_delegated_access,
        t_illegal_sireg_cde0,
        t_illegal_sireg3_6,
        t_illegal_sireg4_5,
        t_illegal_sireg_not_delegated,
        t_missing_extension,
        t_hyp_vs_vu_direct,
        t_hyp_m_s_vsireg,
        t_hyp_vs_sireg,
        t_scountinhibit_exists,
        t_scountinhibit_delegated_rw,
        t_scountinhibit_nondelegated_ro,
        t_illegal_scountinhibit_cde0,
        t_illegal_scountinhibit_vs_vu,
        t_virtual_scountovf,
        t_lcofi_mvip_mvien,
        t_lcofi_hvip_hvien,
        t_csr_supervisor_access,
    ):
        r = f()
        tests += r if isinstance(r, list) else [r]
    return tests


DEPS = (
    "siselect 0x40: sireg = cycle, sireg4 = cycleh (Zicntr), sireg2 = cyclecfg, sireg5 = cyclecfgh (Smcntrpmf); "
    "0x41: see the illegal rules; 0x42: the same for instret; 0x43-0x5F: sireg = hpmcounterN, sireg4 = hpmcounterNh, "
    "sireg2 = hpmeventN (Zihpm), sireg5 = hpmeventNh (Zihpm and Sscofpmf). sireg4/sireg5 exist for counters only "
    "on RV32."
)


def scountinhibit_win(t: TestFile, mode: str, form: Form, expect: str, desc: str) -> str:
    t.li("x6", 0x5)
    return csr_win(t, mode, SCOUNTINHIBIT, "scountinhibit", form, expect, desc)


def t_tandem() -> TestFile:
    t = new("Smcdeleg_Ssccfg_tandem", "Smcdeleg")
    t.describe(
        source=SRC,
        rule_text="For a RISC-V hardware platform, Smcdeleg and Ssccfg must always be implemented in tandem.",
        context="Ssccfg is the S-level view of Smcdeleg: scountinhibit and the delegated counters reached through "
        "siselect/sireg (issue 2071). A hart with Smcdeleg therefore shows the Ssccfg state to S-mode once M-mode "
        "sets menvcfg.CDE. The test requires only Smcdeleg and checks that the Ssccfg features are there.",
        issues=f'{ISSUE}2071: bcstrongx: "Smcdeleg/Ssccfg should probably be viewed as two extensions that are '
        "coupled, such that both or neither are implemented ... Ssccfg is simply the portion of Smcdeleg visible at "
        'supervisor level."',
        plan="1. menvcfg.CDE is writable: set, reads 1.\n"
        "2. With CDE=1, S-mode reads scountinhibit (all eight forms) without a trap.\n"
        "3. With Zicntr and mcounteren.CY=1: siselect = 0x40, an S-mode read of sireg does not trap.\n"
        "CDE and mcounteren are restored.",
    )
    all_en(t)
    cde(t, True)
    lab = t.label("cde")
    t.emit(f"{lab}:", 0)
    cde_read(t, "x7")
    t.check("x7", 0 if MUT == "cde_ro0" else 1, lab, "menvcfg.CDE after setting it")
    for f in FORMS:
        scountinhibit_win(t, "S", f, "ok", "CDE=1")
    with t.only_if(ZICNTR):
        bit_of(t, "x1", EN, 0)
        sel(t, 0x40)
        either(
            t,
            "x1",
            lambda: csr_win(t, "S", SIREG[1], "sireg", READ, "ok", "CDE=1, siselect 0x40 (cycle)"),
            "mcounteren.CY is read-only zero",
        )
    end(t)
    return t


def lands_cycle(t: TestFile, ctr: str, w: X, desc: str, flip: bool = False, hiw: int = 0x2AAAAAAA) -> None:
    """Read the counter directly (cycle/instret, or mcycle/minstret) and check it is near w: on RV32 the high word
    equals hiw and the low word is in [w, w + 2^24); on RV64 the value is in [w, w + 2^24). flip: expect it not
    near w (the write did not land)."""
    lab = t.label(f"near{ctr}")
    t.emit(f"{lab}:", 0)
    t.emit(f"csrr x7, {ctr}")
    t.load("x8", w, f"value written to {ctr}")
    t.emit("sub x7, x7, x8")
    t.emit("srli x7, x7, 24")
    t.emit("seqz x7, x7")
    with t.rv32_only():
        t.emit(f"csrr x8, {ctr}h")
        t.li("x9", hiw)
        t.emit("xor x8, x8, x9")
        t.emit("seqz x8, x8")
        t.emit("and x7, x7, x8")
    t.check("x7", 0 if flip else 1, lab, f"{ctr} {'is not' if flip else 'is'} the value written plus < 2^24: {desc}")


def write_ctr_sireg(t: TestFile, w: X) -> None:
    """S-mode: sireg (and sireg4 on RV32) = w, with siselect already set. w.v32 is the low half; the RV32 high half
    is 0x2AAAAAAA."""
    with t.rv32_only():
        t.li("x6", 0x2AAAAAAA)
        t.emit("csrw CSR_SIREG4, x6")
    t.load("x6", w, "counter value")
    t.emit("csrw CSR_SIREG, x6")


W_CYC = X(0x1000, 0x2AAAAAAA00001000)
W_INS = X(0x2000, 0x1555555500002000)
W_FAR = X(0x80000000, 0x5555555580000000)


def t_cde_en() -> TestFile:
    t = new("Smcdeleg_cde_en", "Smcdeleg")
    t.describe(
        source=SRC,
        rule_text="When the Smcdeleg/Ssccfg extensions are enabled (menvcfg.CDE=1), it further allows M-mode to "
        "delegate select counters to S-mode.",
        context="Counter i is delegated when mcounteren[i]=1 and menvcfg.CDE=1; S-mode then reads and writes it "
        "through sireg with siselect 0x40+i. Without either, the sireg access raises illegal instruction and the "
        "counter keeps its value. Writes are checked by reading the counter directly (cycle, instret, hpmcounter3 "
        "in S-mode with mcounteren set). cycle keeps counting, so a landed value is the value written plus less "
        "than 2^24; a value that did not land is far from it. hpmcounter3 with event 0 may be read-only zero.",
        plan="For cycle (i=0, Zicntr) and hpmcounter3 (i=3, Zihpm), over (CDE, mcounteren[i]):\n"
        "1. (1, 1): an S-mode write through sireg lands in the counter.\n"
        "2. (0, 1), (1, 0), (0, 0): the sireg read and write raise illegal instruction; the counter (read with "
        "mcounteren[i] set again) does not hold the new value.\n"
        "Cases where mcounteren[i] does not take the value are skipped.",
    )
    all_en(t)
    with t.only_if(ZICNTR):
        bit_of(t, "x1", EN, 0)

        def cyc() -> None:
            cde(t, True)
            sel(t, 0x40)
            write_ctr_sireg(t, W_CYC)
            lands_cycle(t, "cycle", W_CYC, "S-mode sireg write with CDE=1, mcounteren.CY=1")
            for c, en in ((0, 1), (1, 0), (0, 0)):
                cde(t, bool(c))
                men_write(t, -1 if en else -2, TMP)
                bit_of(t, "x9", TMP, 0)
                if not en:
                    t.emit("seqz x9, x9")

                def trapped(c: int = c, en: int = en) -> None:
                    sel(t, 0x40)
                    exp = "ok" if MUT == "not_deleg_ok" and c else "illegal"
                    for f in (READ, WRITE):
                        t.load("x6", W_FAR, "a far value")
                        csr_win(t, "S", SIREG[1], "sireg", f, exp, f"CDE={c}, mcounteren.CY={en}, siselect 0x40")
                    men_write(t, -1)
                    lands_cycle(t, "cycle", W_FAR, f"after the trapped write, CDE={c}, mcounteren.CY={en}", flip=True)

                either(t, "x9", trapped, "mcounteren.CY does not take the value")

        either(t, "x1", cyc, "mcounteren.CY is read-only zero")
    with t.only_if(ZIHPM):
        bit_of(t, "x1", EN, 3)

        def hpm() -> None:
            cde(t, True)
            sel(t, 0x43)
            t.li("x6", 0x355)
            t.emit("csrw CSR_SIREG, x6")
            lab = t.label("hpm")
            t.emit(f"{lab}:", 0)
            t.emit("csrr x7, hpmcounter3")
            t.check("x7", [0x355, 0], lab, "hpmcounter3 after an S-mode sireg write of 0x355 (or read-only 0)")
            for c, en in ((0, 1), (1, 0), (0, 0)):
                cde(t, bool(c))
                men_write(t, -1 if en else ~8, TMP)
                bit_of(t, "x9", TMP, 3)
                if not en:
                    t.emit("seqz x9, x9")

                def trapped(c: int = c, en: int = en) -> None:
                    sel(t, 0x43)
                    exp = "ok" if MUT == "not_deleg_ok" and c else "illegal"
                    for f in (READ, WRITE):
                        t.li("x6", 0x2AA)
                        csr_win(t, "S", SIREG[1], "sireg", f, exp, f"CDE={c}, mcounteren.HPM3={en}, siselect 0x43")
                    men_write(t, -1)
                    lab = t.label("hpmk")
                    t.emit(f"{lab}:", 0)
                    t.emit("csrr x7, hpmcounter3")
                    t.check("x7", [0x355, 0], lab, f"hpmcounter3 keeps its value after the trapped write, CDE={c}")

                either(t, "x9", trapped, "mcounteren.HPM3 does not take the value")

        either(t, "x1", hpm, "mcounteren.HPM3 is read-only zero")
    end(t)
    return t


def t_menvcfg_cde_op() -> TestFile:
    t = new("menvcfg_cde_op", "Smcdeleg")
    t.describe(
        source=MAC,
        rule_text="If the Smcdeleg extension is implemented, the CDE (Counter Delegation Enable) bit controls whether "
        "Zicntr and Zihpm counters can be delegated to S-mode. When CDE=1, the Smcdeleg extension is enabled, see "
        "<<smcdeleg>>. When CDE=0, the Smcdeleg and Ssccfg extensions appear to be not implemented.",
        context="CDE is bit 60 of menvcfg (bit 28 of menvcfgh on RV32). 'Appear to be not implemented': "
        "scountinhibit and the delegated sireg* state raise illegal instruction (from VS-mode too: issue 2087), "
        "while the Zicntr/Zihpm counters themselves stay readable through mcounteren. State written while CDE=1 "
        "lives in mcountinhibit and survives CDE=0. mcountinhibit is WARL: IMPL = the bits that hold 1 after an "
        "M-mode write of all ones, so IR may be read-only zero.",
        issues=f"{ISSUE}2087: gfavor: with CDE=0 scountinhibit raises illegal instruction from M/HS/VS; with "
        f'CDE=1 VS/VU raise virtual instruction. {ISSUE}2547: "When CDE=0, the Smcdeleg and Ssccfg extensions '
        'appear to not be implemented."',
        plan="1. CDE is writable: set reads 1, clear reads 0.\n"
        "2. CDE=0: scountinhibit read and write and (Zicntr, mcounteren.CY) sireg at siselect 0x40 raise illegal "
        "instruction in S-mode; with H, a VS-mode scountinhibit read raises illegal instruction.\n"
        "3. CDE=1: both succeed; an S-mode write of scountinhibit.IR lands in mcountinhibit (if IR is delegated and "
        "implemented); with H, VS-mode raises "
        "virtual instruction.\n"
        "4. CDE=0 again: illegal again, and mcountinhibit.IR is still set; CDE=1: scountinhibit reads IR again.\n"
        "5. Zicntr: cycle reads in S-mode with mcounteren.CY=1 for both CDE values.",
    )
    all_en(t)
    for on in (True, False):
        cde(t, on)
        lab = t.label("cde")
        t.emit(f"{lab}:", 0)
        cde_read(t, "x7")
        t.check("x7", 1 if on and MUT != "cde_ro0" else 0, lab, f"menvcfg.CDE after writing {int(on)}")
    probe_impl(t)

    def disabled(desc: str) -> None:
        exp = "ok" if MUT == "cde_ignored" else "illegal"
        for f in (READ, WRITE):
            scountinhibit_win(t, "S", f, exp, desc)
        with t.only_if(ZICNTR):
            bit_of(t, "x9", EN, 0)
            sel(t, 0x40)
            either(
                t,
                "x9",
                lambda: csr_win(t, "S", SIREG[1], "sireg", READ, exp, f"{desc}, siselect 0x40"),
                "mcounteren.CY is read-only zero",
            )
        with t.only_if(H):
            scountinhibit_win(t, "VS", READ, exp, desc)

    def enabled(desc: str) -> None:
        scountinhibit_win(t, "S", READ, "ok", desc)
        with t.only_if(ZICNTR):
            bit_of(t, "x9", EN, 0)
            sel(t, 0x40)
            either(
                t,
                "x9",
                lambda: csr_win(t, "S", SIREG[1], "sireg", READ, "ok", f"{desc}, siselect 0x40"),
                "mcounteren.CY is read-only zero",
            )
        with t.only_if(H):
            scountinhibit_win(t, "VS", READ, "virtual", desc)

    cde(t, False)
    disabled("CDE=0")
    cde(t, True)
    enabled("CDE=1")
    lab = t.label("ir")
    t.li("x6", 4)
    t.emit(f"{lab}:", 0)
    t.emit("csrw CSR_SCOUNTINHIBIT, x6")
    m_op(t, "READ", "CSR_MCOUNTINHIBIT")
    t.emit("andi a0, a0, 4")
    ld(t, "x1", EN)
    ld(t, "x8", IMPL)
    t.emit("and x1, x1, x8")
    t.emit("andi x1, x1, 4")
    t.emit("xor a0, a0, x1")
    t.check(
        "a0", 0, lab, "mcountinhibit.IR XOR (mcounteren.IR & IMPL.IR) after an S-mode write of scountinhibit.IR (CDE=1)"
    )
    cde(t, False)
    disabled("CDE=0 again")
    lab = t.label("kept")
    t.emit(f"{lab}:", 0)
    m_op(t, "READ", "CSR_MCOUNTINHIBIT")
    t.emit("andi a0, a0, 4")
    t.emit("xor a0, a0, x1")
    t.check("a0", 0, lab, "mcountinhibit.IR kept while CDE=0")
    cde(t, True)
    lab = t.window("S", ["csrr x7, CSR_SCOUNTINHIBIT"], "ok", "read of scountinhibit (CDE=1 again)")
    t.emit("andi x7, x7, 4")
    t.emit("xor x7, x7, x1")
    t.check("x7", 0, lab, "scountinhibit.IR XOR (mcounteren.IR & IMPL.IR) after re-enabling CDE")
    with t.only_if(ZICNTR):
        bit_of(t, "x1", EN, 0)

        def reads() -> None:
            for c in (0, 1):
                cde(t, bool(c))
                t.window("S", ["csrr x7, cycle"], "ok", f"read of cycle with mcounteren.CY=1, CDE={c}")

        either(t, "x1", reads, "mcounteren.CY is read-only zero")
    m_op(t, "WRITE", "CSR_MCOUNTINHIBIT", imm=0)
    end(t)
    return t


def t_delegated_access() -> list[TestFile]:
    t = new("Smcdeleg_delegated_access", "Smcdeleg")
    t.describe(
        source=SRC,
        rule_text="The siselect (and vsiselect) index range 0x40-0x5F is reserved for delegated counter access. When "
        "a counter i is delegated (mcounteren[i]=1 and menvcfg.CDE=1) and siselect is 0x40+i, sireg* aliases "
        "counter i.",
        context=DEPS + " An alias works both ways: writes through sireg land in the counter (read directly with "
        "mcounteren set), and the counter's value shows through sireg. cycle and instret keep counting, so a "
        "landed value is the value written plus < 2^24; hpmcounterN with event 0 holds the value written or is "
        "read-only zero (small values, so a narrow counter holds them). hpmeventN through sireg2 is a subset of "
        'mhpmeventN: with Sscofpmf "event selector bit 62 (MINH) is read-only 0 when accessed through sireg*"; '
        "the other xINH bits (61:58, 29:26 of the high half) are the register's own. vsiselect is covered by the "
        "Ssccfg_hyp_* rules (counters are never delegated to VS: issue 2096).",
        issues=f"{ISSUE}2541: ved-rivos: sireg* exposes the delegated architectural view; MINH is read-only zero "
        f"there. {ISSUE}2089: hpmeventi is a subset of mhpmeventi (PR 2104).",
        plan="CDE=1, mcounteren = all ones (bits read back; counters whose bit is read-only zero are skipped):\n"
        "1. Zicntr: sireg at 0x40 written with W1 (sireg4 = high half on RV32), sireg at 0x42 with W2: cycle reads "
        "near W1 and instret near W2 (each alias lands in its own counter); sireg at 0x40 reads near W1 and at "
        "0x42 near W2; RV32 sireg4 reads the high halves.\n"
        "2. Zihpm, counters 3, 4, 17, 31: sireg written with distinct small values; each hpmcounterN reads its "
        "value or 0, and sireg reads the same as hpmcounterN. RV32: sireg4 = 1 shows in hpmcounterNh (1 or 0).\n"
        "3. Zihpm with Sscofpmf, if mhpmevent3.MINH holds a 1 written by M-mode (T-SBI; else mhpmevent3 is "
        "read-only zero and the case is skipped): S-mode writes sireg2 (sireg5 on RV32) = SINH|UINH: mhpmevent3 "
        "reads MINH|SINH|UINH (MINH kept), and sireg2 reads SINH|UINH (MINH as 0). Over mhpmevent3 = 0, an S-mode "
        "write of MINH|SINH leaves MINH 0. An S-mode write of OF=1 sets mhpmevent3.OF and reads back; OF=0 clears "
        "it (the 'clear overflow indication' use). A T-SBI write of mhpmcounter3 = 0x123 shows through sireg at "
        "0x43 (or 0).\n"
        "4. Smcntrpmf: sireg2 at 0x40 written with SINH (sireg5 on RV32) reads back SINH.\n"
        "5. Zihpm: all eight CSR forms of sireg at 0x43, each over sireg = 0x3A3: the old value (hpmcounter3 "
        "read directly) is returned and hpmcounter3 holds the form's result (0 if read-only zero).\n"
        "scounteren = 0 throughout (negative dependency: it gates U-mode, not S-mode sireg); restored at the end.\n"
        "An _Sm file repeats 1, 2 and 5 from M-mode.",
    )
    m = new_sm("Smcdeleg_delegated_access", "Smcdeleg")
    m.describe(
        source=SRC,
        rule_text=t.doc["rule_text"],
        context="M-mode part: siselect/sireg* accessed from M-mode (the Ssccfg rules apply 'while the privilege mode "
        "is M or S'). " + DEPS,
        plan="CDE=1, mcounteren = all ones (read back): 1. Zicntr: sireg at 0x40/0x42 written from M-mode with W1/W2: "
        "mcycle near W1, minstret near W2. 2. Zihpm: sireg at 0x43 written with 0x355: mhpmcounter3 reads 0x355 or 0; "
        "an M-mode write of mhpmcounter3 = 0x123 shows through sireg (or 0). 3. Zihpm: all eight CSR forms of "
        "sireg at 0x43: old value returned, mhpmcounter3 holds the result (or 0).",
    )
    for x in (t, m):
        sm = x.boot == "M"
        if not sm:
            x.emit("csrr x6, scounteren")
            st(x, "x6", TMP2)
            x.emit("csrw scounteren, x0")
        ctr = {"cycle": "mcycle" if sm else "cycle", "instret": "minstret" if sm else "instret"}
        all_en(x)
        cde(x, True)
        with x.only_if(ZICNTR):
            ld(x, "x1", EN)
            x.emit("andi x1, x1, 5")
            x.emit("addi x1, x1, -5")
            x.emit("seqz x1, x1")

            def cyc(x: TestFile = x, ctr: dict = ctr) -> None:
                c, i = (0x42, 0x40) if MUT == "cycle_instret_swapped" else (0x40, 0x42)
                sel(x, c)
                write_ctr_sireg(x, W_CYC)
                sel(x, i)
                write_ctr_sireg2(x, W_INS)
                lands_cycle(x, ctr["cycle"], W_CYC, "written through sireg at siselect 0x40")
                lands_cycle(x, ctr["instret"], W_INS, "written through sireg at siselect 0x42", hiw=0x15555555)
                for s, w, nm in ((0x40, W_CYC, "cycle"), (0x42, W_INS, "instret")):
                    sel(x, s)
                    lab = x.label("rd")
                    x.emit(f"{lab}:", 0)
                    x.emit("csrr x7, CSR_SIREG")
                    x.load("x8", w)
                    x.emit("sub x7, x7, x8")
                    x.emit("srli x7, x7, 24")
                    x.check("x7", 0, lab, f"(sireg - written {nm}) >> 24 at siselect {s:#x}")
                    with x.rv32_only():
                        x.emit("csrr x7, CSR_SIREG4")
                        x.check(
                            "x7",
                            0x2AAAAAAA if s == 0x40 else 0x15555555,
                            lab,
                            f"sireg4 (high half of {nm}) at siselect {s:#x}",
                        )

            either(x, "x1", cyc, "mcounteren.CY or IR is read-only zero")
        with x.only_if(ZIHPM):
            ns = (3, 4, 17, 31) if not sm else (3,)
            for n in ns:
                bit_of(x, "x1", EN, n)

                def wr(x: TestFile = x, n: int = n) -> None:
                    sel(x, 0x40 + n)
                    x.li("x6", 0x300 + 0x11 * n)
                    x.emit("csrw CSR_SIREG, x6")

                either(x, "x1", wr, f"mcounteren.HPM{n} is read-only zero")
            for n in ns:
                bit_of(x, "x1", EN, n)
                hc = f"mhpmcounter{n}" if sm else f"hpmcounter{n}"

                def rd(x: TestFile = x, n: int = n, hc: str = hc) -> None:
                    v = 0x300 + 0x11 * n
                    lab = x.label("hpm")
                    x.emit(f"{lab}:", 0)
                    x.emit(f"csrr x7, {hc}")
                    x.check(
                        "x7",
                        [0] if MUT == "hpm_write_lost" else [v, 0],
                        lab,
                        f"{hc} after a sireg write of {v:#x} at siselect {0x40 + n:#x} (or read-only 0)",
                    )
                    sel(x, 0x40 + n)
                    x.emit("csrr x8, CSR_SIREG")
                    x.emit("xor x8, x8, x7")
                    x.check("x8", 0, lab, f"sireg at siselect {0x40 + n:#x} XOR {hc}")
                    with x.rv32_only():
                        x.li("x6", 1)
                        x.emit("csrw CSR_SIREG4, x6")
                        x.emit(f"csrr x7, {hc}h")
                        x.check("x7", [1, 0], lab, f"{hc}h after a sireg4 write of 1 (or 0)")
                        x.emit("csrw CSR_SIREG4, x0")

                either(x, "x1", rd, f"mcounteren.HPM{n} is read-only zero")
            with x.only_if(SCOF) if not sm else nullcontext():
                bit_of(x, "x1", EN, 3)

                def back(x: TestFile = x) -> None:
                    m_op(x, "WRITE", "0xb03", imm=0x123)
                    sel(x, 0x43)
                    lab = x.label("back")
                    x.emit(f"{lab}:", 0)
                    x.emit("csrr x7, CSR_SIREG")
                    x.check("x7", [0x123, 0], lab, "sireg at 0x43 after an M-mode write of mhpmcounter3 = 0x123")

                either(x, "x1", back, "mcounteren.HPM3 is read-only zero")
            bit_of(x, "x1", EN, 3)
            either(x, "x1", lambda x=x: forms_sweep(x), "mcounteren.HPM3 is read-only zero")
        if sm:
            continue
        sireg2_checks(x)
        ld(x, "x6", TMP2)
        x.emit("csrw scounteren, x6")
        end(x)
    for x in (t, m):
        if x.boot == "M":
            end(x)
    return [t, m]


def sireg2_checks(x: TestFile) -> None:
    """S-mode only: hpmevent3 through sireg2/sireg5 (Sscofpmf) and cyclecfg through sireg2/sireg5 (Smcntrpmf)."""
    with x.only_if(f"{ZIHPM} && {SCOF}"):
        bit_of(x, "x1", EN, 3)

        def ev() -> None:
            minh, su, of = inh("M"), inh("S", "U"), 1 << 31
            allinh = inh("M", "S", "U", "VS", "VU")
            sel(x, 0x43)

            def mev(v: int) -> None:
                """M-level mhpmevent3 bits 63:32 = v (T-SBI)."""
                with x.rv64_only():
                    x.load("a1", v << 32, f"mhpmevent3 = {v:#x} << 32")
                    m_op(x, "WRITE", "CSR_MHPMEVENT3", "a1")
                with x.rv32_only():
                    m_op(x, "WRITE", "CSR_MHPMEVENT3", imm=0)
                    m_op(x, "WRITE", "CSR_MHPMEVENT3H", imm=v)

            def mev_hi(dst: str) -> None:
                """dst = M-level mhpmevent3 bits 63:32 (T-SBI)."""
                with x.rv64_only():
                    m_op(x, "READ", "CSR_MHPMEVENT3")
                    x.emit(f"srli {dst}, a0, 32")
                with x.rv32_only():
                    m_op(x, "READ", "CSR_MHPMEVENT3H")
                    x.emit(f"mv {dst}, a0")

            def swrite(v: int) -> None:
                x.load("x6", hx(v), f"{v:#x} in bits 63:32")
                with x.rv64_only():
                    x.emit("csrw CSR_SIREG2, x6")
                with x.rv32_only():
                    x.emit("csrw CSR_SIREG5, x6")

            def sread() -> None:
                with x.rv64_only():
                    x.emit("csrr x7, CSR_SIREG2")
                    x.emit("srli x7, x7, 32")
                with x.rv32_only():
                    x.emit("csrr x7, CSR_SIREG5")

            mev(minh)
            mev_hi("x9")
            x.emit("srli x9, x9, 30")
            x.emit("andi x9, x9, 1")

            def body() -> None:
                lab = x.label("ev")
                x.emit(f"{lab}:", 0)
                swrite(su)
                mev_hi("a0")
                x.emit(f"LI(x7, {allinh | of:#x})", 2)
                x.emit("and a0, a0, x7")
                x.check("a0", minh | su, lab, "mhpmevent3 bits 63:58 after an S-mode sireg2 write of SINH|UINH")
                sread()
                x.emit(f"LI(x8, {allinh:#x})", 2)
                x.emit("and x7, x7, x8")
                x.check(
                    "x7",
                    (minh | su) if MUT == "hpmevent_minh_visible" else su,
                    lab,
                    "xINH bits read through sireg2/sireg5 (MINH reads 0)",
                )
                lab = x.label("evw")
                mev(0)
                x.emit(f"{lab}:", 0)
                swrite(minh | inh("S"))
                mev_hi("a0")
                x.emit(f"LI(x7, {allinh | of:#x})", 2)
                x.emit("and a0, a0, x7")
                x.check(
                    "a0",
                    inh("S") | (minh if MUT == "hpmevent_minh_written" else 0),
                    lab,
                    "mhpmevent3 bits 63:58 after an S-mode sireg2 write of MINH|SINH over 0 (MINH not written)",
                )
                lab = x.label("of")
                mev(0)
                x.emit(f"{lab}:", 0)
                swrite(of)
                mev_hi("a0")
                x.emit("srli a0, a0, 31")
                x.check(
                    "a0",
                    0 if MUT == "hpmevent_of_ro" else 1,
                    lab,
                    "mhpmevent3.OF after an S-mode sireg2 write of OF=1",
                )
                sread()
                x.emit("srli x7, x7, 31")
                x.check("x7", 1, lab, "OF read through sireg2/sireg5")
                swrite(0)
                mev_hi("a0")
                x.emit("srli a0, a0, 31")
                x.check("a0", 0, lab, "mhpmevent3.OF after an S-mode sireg2 write of OF=0 (overflow cleared)")
                mev(0)

            either(x, "x9", body, "mhpmevent3.MINH is read-only zero (mhpmevent3 not implemented)")

        either(x, "x1", ev, "mcounteren.HPM3 is read-only zero")
    with x.only_if(f"{ZICNTR} && {CNTRPMF}"):
        bit_of(x, "x1", EN, 0)

        def cfg() -> None:
            sel(x, 0x40)
            x.load("x6", hx(inh("S")), "SINH")
            lab = x.label("cfg")
            x.emit(f"{lab}:", 0)
            with x.rv64_only():
                x.emit("csrw CSR_SIREG2, x6")
                x.emit("csrr x7, CSR_SIREG2")
            with x.rv32_only():
                x.emit("csrw CSR_SIREG5, x6")
                x.emit("csrr x7, CSR_SIREG5")
            x.check("x7", hx(inh("S")), lab, "cyclecfg (high word) read back through sireg2/sireg5 after SINH")
            with x.rv64_only():
                x.emit("csrw CSR_SIREG2, x0")
            with x.rv32_only():
                x.emit("csrw CSR_SIREG5, x0")

        either(x, "x1", cfg, "mcounteren.CY is read-only zero")


def forms_sweep(x: TestFile) -> None:
    """All eight CSR instruction forms on sireg at siselect 0x43 (hpmcounter3, delegated). Before each, sireg =
    V and x8 = the counter read directly (V, or 0 if hpmcounter3 is read-only zero). The form returns x8 as the old
    value and leaves the counter at the form's result (0 if read-only zero)."""
    hc = "mhpmcounter3" if x.boot == "M" else "hpmcounter3"
    v, op, imm = 0x3A3, 0x0F0, 0x15
    sel(x, 0x43)
    for f in FORMS:
        _, f3, rd, rs1, kind = f
        new = {
            1: op,
            2: v | op if rs1 else v,
            3: v & ~op if rs1 else v,
            5: imm,
            6: v | imm if rs1 else v,
            7: v & ~imm if rs1 else v,
        }[f3]
        if MUT == "sireg_rmw_as_write" and f3 in (2, 3, 6, 7) and rs1:
            new = op if f3 in (2, 3) else imm
        x.li("x6", v)
        x.emit("csrw CSR_SIREG, x6")
        x.emit(f"csrr x8, {hc}")
        x.li("x6", op)
        lab = csr_win(x, bmode(x), SIREG[1], "sireg", f, "ok", "siselect 0x43 (hpmcounter3), counter delegated")
        if rd:
            x.emit("xor x7, x7, x8")
            x.check("x7", 0, lab, f"{kind} of sireg at 0x43 returns the old value ({hc} before, {v:#x} or 0)")
        x.emit(f"csrr x9, {hc}")
        x.li("x1", new)
        x.emit("snez x8, x8")
        x.emit("neg x8, x8")
        x.emit("and x1, x1, x8")
        x.emit("xor x9, x9, x1")
        x.check("x9", 0, lab, f"{hc} after {kind} of sireg at 0x43 over {v:#x}: {new:#x} (or 0 if read-only zero)")
    x.emit("csrw CSR_SIREG, x0")


def write_ctr_sireg2(t: TestFile, w: X) -> None:
    """Like write_ctr_sireg, RV32 high half 0x15555555."""
    with t.rv32_only():
        t.li("x6", 0x15555555)
        t.emit("csrw CSR_SIREG4, x6")
    t.load("x6", w, "counter value")
    t.emit("csrw CSR_SIREG, x6")


def illegal_pair(
    name: str,
    rule_text: str,
    context: str,
    plan: str,
    issues: str = "",
    rv64: bool = False,
    req: list[str] | None = None,
) -> tuple[TestFile, TestFile]:
    t = new(name, required=req, rv64=rv64)
    t.describe(source=SRC, rule_text=rule_text, context=context, issues=issues, plan=plan)
    m = new_sm(name, required=(req + ["Sm"]) if req else None, rv64=rv64)
    m.describe(
        source=SRC,
        rule_text=rule_text,
        context="M-mode part. " + context,
        issues=issues,
        plan="The same sweep from M-mode (siselect written and sireg* accessed in M-mode).",
    )
    return t, m


ILLEGAL_CTX = (
    "While the privilege mode is M or S and siselect holds 0x40-0x5F, these accesses raise illegal instruction "
    "(xtval 0 or the instruction bits). siselect supports 0..0xFFF, so it holds the value written. With Smstateen, "
    "mstateen0[60] (CSRIND) is set by the framework."
)


def t_illegal_sireg_cde0() -> list[TestFile]:
    t, m = illegal_pair(
        "Ssccfg_illegal_sireg_cde0",
        "attempts to access any sireg* when menvcfg.CDE = 0;",
        ILLEGAL_CTX + " The sweep sets every mcounteren bit, so the counters would otherwise be delegated.",
        "mcounteren = all ones. CDE=1 then a control read of sireg at 0x40 (Zicntr, CY set: no trap). CDE=0: for "
        "siselect 0x40, 0x41, 0x42, 0x43, 0x50, 0x5F, every sireg1-6 raises illegal instruction on a read (all eight "
        "CSR forms of sireg at 0x40, and a write of each register at the others); siselect still holds the value.",
    )
    for x in (t, m):
        mode = bmode(x)
        all_en(x)
        with x.only_if(ZICNTR):
            cde(x, True)
            bit_of(x, "x1", EN, 0)
            sel(x, 0x40)
            either(
                x,
                "x1",
                lambda x=x, mode=mode: csr_win(x, mode, SIREG[1], "sireg", READ, "ok", "control: CDE=1, siselect 0x40"),
                "mcounteren.CY is read-only zero",
            )
        cde(x, False)
        sweep(x, mode, SELS, [1, 2, 3, 4, 5, 6], "ok" if MUT == "cde0_sireg_ok" else "illegal", "CDE=0")
        check_sel(x, SELS[-1])
        end(x)
    return [t, m]


def t_illegal_sireg3_6() -> list[TestFile]:
    t, m = illegal_pair(
        "Ssccfg_illegal_sireg3_6",
        "attempts to access sireg3 or sireg6;",
        ILLEGAL_CTX + " With CDE=1 and every mcounteren bit set, counter delegation is enabled, so the trap comes "
        "from the register choice alone (no counter state is mapped to sireg3/sireg6).",
        "CDE=1, mcounteren = all ones. For siselect 0x40, 0x41, 0x42, 0x43, 0x50, 0x5F: sireg3 and sireg6 raise "
        "illegal instruction (all eight forms of sireg3 at 0x40; read and write elsewhere). Control: sireg at 0x40 "
        "(Zicntr) reads without a trap.",
    )
    for x in (t, m):
        mode = bmode(x)
        all_en(x)
        cde(x, True)
        sweep(x, mode, SELS, [3, 6], "ok" if MUT == "sireg3_ok" else "illegal", "CDE=1, mcounteren all ones")
        with x.only_if(ZICNTR):
            bit_of(x, "x1", EN, 0)
            sel(x, 0x40)
            either(
                x,
                "x1",
                lambda x=x, mode=mode: csr_win(x, mode, SIREG[1], "sireg", READ, "ok", "control: siselect 0x40"),
                "mcounteren.CY is read-only zero",
            )
        end(x)
    return [t, m]


def t_illegal_sireg4_5() -> list[TestFile]:
    t, m = illegal_pair(
        "Ssccfg_illegal_sireg4_5_xlen64",
        "attempts to access sireg4 or sireg5 when XLEN = 64;",
        "RV64 only (the file passes trivially on RV32, where sireg4/sireg5 hold the high halves). "
        + ILLEGAL_CTX
        + " With CDE=1 and every mcounteren bit set, the counters are delegated; on RV64 the counter is whole in "
        "sireg and the event/configuration in sireg2.",
        "RV64. CDE=1, mcounteren = all ones. For siselect 0x40, 0x41, 0x42, 0x43, 0x50, 0x5F: sireg4 and sireg5 "
        "raise illegal instruction (all eight forms of sireg4 at 0x40; read and write elsewhere). Control: sireg at "
        "0x40 (Zicntr) reads without a trap.",
        rv64=True,
    )
    for x in (t, m):
        mode = bmode(x)
        all_en(x)
        cde(x, True)
        sweep(x, mode, SELS, [4, 5], "ok" if MUT == "sireg4_rv64_ok" else "illegal", "CDE=1, mcounteren all ones")
        with x.only_if(ZICNTR):
            bit_of(x, "x1", EN, 0)
            sel(x, 0x40)
            either(
                x,
                "x1",
                lambda x=x, mode=mode: csr_win(x, mode, SIREG[1], "sireg", READ, "ok", "control: siselect 0x40"),
                "mcounteren.CY is read-only zero",
            )
        end(x)
    return [t, m]


def t_illegal_sireg_not_delegated() -> list[TestFile]:
    t, m = illegal_pair(
        "Ssccfg_illegal_sireg_not_delegated",
        "attempts to access sireg* when siselect = 0x41, or when the counter selected by siselect is not delegated "
        "to S-mode (the corresponding bit in mcounteren = 0).",
        ILLEGAL_CTX + " 0x41 would select time, which is never delegated, even with mcounteren.TM=1. For other "
        "counters, mcounteren[i] = 0 alone makes them not delegated (CDE=1). Clearing one bit must not affect its "
        "neighbours.",
        "CDE=1.\n"
        "1. mcounteren = all ones: siselect 0x41, every sireg1-6 raises illegal instruction (all eight forms of "
        "sireg).\n"
        "2. For i = 0, 2, 3, 17, 31: mcounteren = all ones except bit i (skipped if bit i stays set): sireg and "
        "sireg2 (and sireg4/sireg5 on RV32) at 0x40+i raise illegal instruction; with Zicntr/Zihpm, sireg at a "
        "neighbouring delegated counter (0x42 for i=0, 0x40 for i=2, 0x44 for 3, 0x50 for 17, 0x5E for 31) reads "
        "without a trap.\n"
        "3. Transition: counter 3 delegated (sireg at 0x43 reads), then mcounteren.HPM3 cleared: illegal.",
    )
    for x in (t, m):
        mode = bmode(x)
        cde(x, True)
        all_en(x)
        sweep(
            x, mode, [0x41], [1, 2, 3, 4, 5, 6], "ok" if MUT == "sel41_ok" else "illegal", "CDE=1, mcounteren all ones"
        )
        for i, nb in ((0, 2), (2, 0), (3, 4), (17, 16), (31, 30)):
            men_write(x, ~(1 << i) & 0xFFFFFFFF if i == 31 else ~(1 << i), TMP)
            bit_of(x, "x1", TMP, i)
            x.emit("seqz x1, x1")

            def case(x: TestFile = x, i: int = i, nb: int = nb, mode: str = mode) -> None:
                sel(x, 0x40 + i)
                regs = [1, 2]
                for r in regs:
                    for f in (READ, WRITE):
                        x.li("x6", 0)
                        csr_win(
                            x,
                            mode,
                            SIREG[r],
                            SIREG_NAME[r],
                            f,
                            "ok" if MUT == "not_deleg_ok" else "illegal",
                            f"mcounteren[{i}]=0, siselect {0x40 + i:#x}",
                        )
                with x.rv32_only():
                    for r in (4, 5):
                        csr_win(
                            x,
                            mode,
                            SIREG[r],
                            SIREG_NAME[r],
                            READ,
                            "illegal",
                            f"mcounteren[{i}]=0, siselect {0x40 + i:#x}",
                        )
                cond = ZICNTR if nb in (0, 2) else ZIHPM
                with x.only_if(cond):
                    bit_of(x, "x9", TMP, nb)
                    sel(x, 0x40 + nb)
                    either(
                        x,
                        "x9",
                        lambda: csr_win(
                            x, mode, SIREG[1], "sireg", READ, "ok", f"neighbour {nb} still delegated, mcounteren[{i}]=0"
                        ),
                        f"mcounteren[{nb}] is read-only zero",
                    )

            either(x, "x1", case, f"mcounteren[{i}] is read-only one")
        with x.only_if(ZIHPM):
            all_en(x)
            bit_of(x, "x1", EN, 3)

            def trans(x: TestFile = x, mode: str = mode) -> None:
                sel(x, 0x43)
                csr_win(x, mode, SIREG[1], "sireg", READ, "ok", "counter 3 delegated")
                men_write(x, ~8, TMP)
                bit_of(x, "x9", TMP, 3)
                x.emit("seqz x9, x9")
                either(
                    x,
                    "x9",
                    lambda: csr_win(x, mode, SIREG[1], "sireg", READ, "illegal", "after clearing mcounteren.HPM3"),
                    "mcounteren.HPM3 is read-only one",
                )

            either(x, "x1", trans, "mcounteren.HPM3 is read-only zero")
        end(x)
    return [t, m]


def t_missing_extension() -> list[TestFile]:
    t, m = illegal_pair(
        "Ssccfg_missing_extension_illegal",
        "If any extension upon which the underlying state depends is not implemented, an attempt from M or S mode to "
        "access the given state through sireg* raises an illegal-instruction exception.",
        ILLEGAL_CTX + " " + DEPS + " The case for each missing extension exists only on harts without it (e.g. "
        "sireg2 at 0x40 without Smcntrpmf); on harts with it, the same access is a control that must not trap "
        "(the counter is delegated: CDE=1, mcounteren bit set).",
        "CDE=1, mcounteren = all ones (cases whose bit stays 0 are skipped, since they trap anyway):\n"
        "1. Without Zicntr: sireg/sireg2 at 0x40 and 0x42 (and sireg4/sireg5 on RV32) raise illegal instruction.\n"
        "2. Zicntr without Smcntrpmf: sireg2 at 0x40 and 0x42 (sireg5 on RV32) raise illegal; sireg does not.\n"
        "3. Without Zihpm: sireg/sireg2 (sireg4/sireg5 on RV32) at 0x43 and 0x5F raise illegal.\n"
        "4. RV32, Zihpm without Sscofpmf: sireg5 at 0x43 and 0x5F raises illegal; sireg2 does not.\n"
        "5. Controls with the extensions present: sireg2 at 0x40/0x42 (Smcntrpmf), sireg/sireg2 at 0x43/0x5F "
        "(Zihpm), sireg5 at 0x43/0x5F (RV32, Sscofpmf) do not trap.",
    )
    for x in (t, m):
        mode = bmode(x)
        cde(x, True)
        all_en(x)

        def acc(s: int, r: int, exp: str, desc: str, bit: int, x: TestFile = x, mode: str = mode) -> None:
            if exp == "ok" and MUT == "cyclecfg_illegal" and r in (2, 5) and s in (0x40, 0x42):
                exp = "illegal"
            bit_of(x, "x1", EN, bit)
            sel(x, s)
            either(
                x,
                "x1",
                lambda: csr_win(x, mode, SIREG[r], SIREG_NAME[r], READ, exp, desc),
                f"mcounteren[{bit}] is read-only zero",
            )

        with x.only_if(f"!{ZICNTR}"):
            for s in (0x40, 0x42):
                for r in (1, 2):
                    acc(s, r, "illegal", "no Zicntr", s - 0x40)
                with x.rv32_only():
                    for r in (4, 5):
                        acc(s, r, "illegal", "no Zicntr", s - 0x40)
        with x.only_if(f"{ZICNTR} && !{CNTRPMF}"):
            for s in (0x40, 0x42):
                acc(s, 2, "illegal", "Zicntr without Smcntrpmf", s - 0x40)
                acc(s, 1, "ok", "control: Zicntr", s - 0x40)
                with x.rv32_only():
                    acc(s, 5, "illegal", "Zicntr without Smcntrpmf", s - 0x40)
        with x.only_if(f"{ZICNTR} && {CNTRPMF}"):
            for s in (0x40, 0x42):
                acc(s, 2, "ok", "control: Smcntrpmf", s - 0x40)
                with x.rv32_only():
                    acc(s, 5, "ok", "control: Smcntrpmf", s - 0x40)
        with x.only_if(f"!{ZIHPM}"):
            for s in (0x43, 0x5F):
                for r in (1, 2):
                    acc(s, r, "illegal", "no Zihpm", s - 0x40)
                with x.rv32_only():
                    for r in (4, 5):
                        acc(s, r, "illegal", "no Zihpm", s - 0x40)
        with x.only_if(ZIHPM):
            for s in (0x43, 0x5F):
                for r in (1, 2):
                    acc(s, r, "ok", "control: Zihpm", s - 0x40)
                with x.rv32_only():
                    acc(s, 4, "ok", "control: Zihpm", s - 0x40)
        with x.only_if(f"{ZIHPM} && !{SCOF}"), x.rv32_only():
            for s in (0x43, 0x5F):
                acc(s, 5, "illegal", "Zihpm without Sscofpmf", s - 0x40)
        with x.only_if(f"{ZIHPM} && {SCOF}"), x.rv32_only():
            for s in (0x43, 0x5F):
                acc(s, 5, "ok", "control: Sscofpmf", s - 0x40)
        end(x)
    return [t, m]


HYP = ["I", "S", "Ssccfg", "H"]


def t_hyp_vs_vu_direct() -> TestFile:
    t = new("Ssccfg_hyp_vs_or_vu_access_vsireg_illegal", required=HYP)
    t.describe(
        source=SRC,
        rule_text="If the hypervisor (H) extension is also implemented, then as specified by extensions "
        "Smcsrind/Sscsrind, a virtual-instruction exception is raised for attempts from VS-mode or VU-mode to "
        "directly access vsiselect or vsireg*, or attempts from VU-mode to access siselect or sireg*.",
        context="vsiselect/vsireg* are hypervisor CSRs (0x250-0x257); siselect/sireg* are S-level and substitute "
        "for vsiselect/vsireg* when V=1, so VS-mode may use them but VU-mode may not. The outcome is the same for "
        "vsiselect values inside and outside the counter range, and for CDE=0 and CDE=1 (negative dependencies). "
        "xtval is 0 or the instruction bits. VU-mode sireg* accesses with CDE=0 follow this rule's explicit text "
        "(virtual instruction), which issue 2554 asks about.",
        issues=f"{ISSUE}2554 (open, no reply): asks whether the CDE-dependent illegal/virtual rule for VS-mode "
        "sireg* also applies to VU-mode. This rule (and Sscsrind, 'regardless of any other mstateen bits ... from "
        "VU-mode to access siselect or sireg*') says virtual instruction, so the test expects that.",
        plan="mcounteren/hcounteren = all ones. For CDE in (1, 0) and vsiselect (written by HS-mode) in (0x40, 0x5F, "
        "0x30):\n"
        "1. VS-mode: vsiselect read and write, and a read of each vsireg1-6 (all eight forms of vsiselect and "
        "vsireg once): virtual instruction.\n"
        "2. VU-mode: vsiselect, each vsireg1-6, siselect and each sireg1-6 read: virtual instruction; siselect write "
        "too.\n"
        "3. HS-mode vsiselect still holds the value written (the trapped writes did not land).",
    )
    all_en(t)
    t.emit("li x6, -1")
    t.emit("csrw CSR_HCOUNTEREN, x6")
    vexp = "ok" if MUT == "vs_vsiselect_ok" else "virtual"
    first = True
    for c in (1, 0):
        cde(t, bool(c))
        for s in (0x40, 0x5F, 0x30):
            sel(t, s, "CSR_VSISELECT")
            d = f"CDE={c}, vsiselect {s:#x}"
            for f in FORMS if first else [READ, WRITE]:
                t.li("x6", 0x40)
                csr_win(t, "VS", 0x250, "vsiselect", f, vexp, d)
            for r in range(1, 7):
                forms = FORMS if first and r == 1 else [READ]
                for f in forms:
                    t.li("x6", 0)
                    csr_win(t, "VS", VSIREG[r], "v" + SIREG_NAME[r], f, "virtual", d)
            for csr, nm in (
                [(0x250, "vsiselect"), (0x150, "siselect")]
                + [(VSIREG[r], "v" + SIREG_NAME[r]) for r in range(1, 7)]
                + [(SIREG[r], SIREG_NAME[r]) for r in range(1, 7)]
            ):
                csr_win(t, "VU", csr, nm, READ, "virtual", d)
            t.li("x6", 0x41)
            csr_win(t, "VU", 0x150, "siselect", WRITE, "virtual", d)
            check_sel(t, s, "CSR_VSISELECT")
            first = False
    end(t)
    return t


def t_hyp_m_s_vsireg() -> list[TestFile]:
    rt = "An attempt to access any vsireg* from M or S mode raises an illegal-instruction exception."
    ctx = (
        "Applies 'while vsiselect holds a value in the range 0x40-0x5F': counters are never delegated to VS-mode "
        "(issue 2096), so vsireg* has no counter state to show, whatever menvcfg.CDE, mcounteren and hcounteren "
        "hold. vsiselect is written by HS-mode (or M-mode) directly."
    )
    iss = (
        f'{ISSUE}2096: bcstrongx: "Smcdeleg/Ssccfg does not include any ability to delegate counters to VS-mode, so '
        'counters are inaccessible through vsireg* regardless of mcounteren/hcounteren settings."'
    )
    t = new("Ssccfg_hyp_m_s_vsireg_illegal", required=HYP)
    t.describe(
        source=SRC,
        rule_text=rt,
        context=ctx,
        issues=iss,
        plan="mcounteren/hcounteren = all ones. For CDE in (1, 0) and vsiselect in 0x40, 0x41, 0x42, 0x43, "
        "0x50, 0x5F: HS-mode accesses to vsireg1-6 raise illegal instruction (all eight forms of vsireg at "
        "0x40 with CDE=1; read and write of vsireg, read of the others elsewhere). vsiselect holds the value.",
    )
    m = new_sm("Ssccfg_hyp_m_s_vsireg_illegal", required=HYP + ["Sm"])
    m.describe(
        source=SRC,
        rule_text=rt,
        context="M-mode part. " + ctx,
        issues=iss,
        plan="The same sweep from M-mode (CDE=1 and 0).",
    )
    for x in (t, m):
        all_en(x)
        x.emit("li x6, -1")
        x.emit("csrw CSR_HCOUNTEREN, x6")
        for c in (1, 0):
            cde(x, bool(c))
            sweep(
                x,
                bmode(x),
                SELS,
                [1, 2, 3, 4, 5, 6],
                "ok" if MUT == "hs_vsireg_ok" else "illegal",
                f"CDE={c}",
                all_forms=c == 1,
                vs=True,
            )
            check_sel(x, SELS[-1], "CSR_VSISELECT")
        end(x)
    return [t, m]


def t_hyp_vs_sireg() -> TestFile:
    t = new("Ssccfg_hyp_vs_access_sireg_conditional", required=HYP)
    t.describe(
        source=SRC,
        rule_text="An attempt from VS-mode to access any sireg* (really vsireg*) raises an illegal-instruction "
        "exception if menvcfg.CDE = 0, or a virtual-instruction exception if menvcfg.CDE = 1.",
        context="Applies while vsiselect holds 0x40-0x5F. In VS-mode, siselect and sireg* are vsiselect and vsireg*; "
        "VS-mode may write siselect (it lands in vsiselect, not in the HS-level siselect). The cause depends only "
        "on CDE: not on mcounteren or hcounteren (negative dependencies), nor on the sireg number.",
        issues=f"{ISSUE}2554 (open): asks whether VU-mode accesses follow the CDE rule; VU-mode is not tested here.",
        plan="For CDE in (0, 1), (mcounteren, hcounteren) in (all, all), (all, 0), (0, all):\n"
        "1. VS-mode writes siselect = 0x40 + k (k cycling over the cases): no trap; HS-mode vsiselect reads the "
        "value and HS siselect keeps its own (0x7).\n"
        "2. VS-mode accesses sireg1-6 at vsiselect 0x40, 0x41, 0x42, 0x43, 0x5F (read; all eight forms of sireg "
        "once per CDE value): illegal instruction (CDE=0) or virtual instruction (CDE=1).",
    )
    first = {0: True, 1: True}
    k = 0
    for c in (0, 1):
        cde(t, bool(c))
        for men, hen in ((-1, -1), (-1, 0), (0, -1)):
            men_write(t, men)
            t.li("x6", hen)
            t.emit("csrw CSR_HCOUNTEREN, x6")
            exp = "illegal" if c == 0 else "virtual"
            if MUT == "vs_sireg_cde1_illegal" and c == 1:
                exp = "illegal"
            if MUT == "vs_sireg_cde0_virtual" and c == 0:
                exp = "virtual"
            d = f"CDE={c}, mcounteren {men & 0xFFFFFFFF:#x}, hcounteren {hen & 0xFFFFFFFF:#x}"
            sel(t, 0x7)
            v = 0x40 + (k % 32)
            k += 7
            t.li("x6", v)
            lab = t.window("VS", ["csrw siselect, x6"], "ok", f"write of siselect = {v:#x} ({d})")
            t.emit("csrr x7, CSR_VSISELECT")
            t.check("x7", v, lab, "vsiselect after a VS-mode siselect write")
            t.emit("csrr x7, siselect")
            t.check("x7", 0x7, lab, "HS-mode siselect after a VS-mode siselect write (unchanged)")
            for s in (0x40, 0x41, 0x42, 0x43, 0x5F):
                sel(t, s, "CSR_VSISELECT")
                for r in range(1, 7):
                    forms = FORMS if first[c] and r == 1 else [READ]
                    for f in forms:
                        t.li("x6", 0)
                        csr_win(t, "VS", SIREG[r], SIREG_NAME[r], f, exp, f"{d}, vsiselect {s:#x}")
                    first[c] = False if r == 1 else first[c]
    t.emit("li x6, -1")
    t.emit("csrw CSR_HCOUNTEREN, x6")
    end(t)
    return t


# ---------------------------------------------------------------- scountinhibit
def probe_impl(t: TestFile) -> None:
    """Slot IMPL = mcountinhibit bits that hold a 1 (write all ones, read back); mcountinhibit = 0 after."""
    m_op(t, "WRITE", "CSR_MCOUNTINHIBIT", imm=-1)
    m_op(t, "READ", "CSR_MCOUNTINHIBIT")
    st(t, "a0", IMPL)
    m_op(t, "WRITE", "CSR_MCOUNTINHIBIT", imm=0)


def ci_check(t: TestFile, actual: str, expr: list[str], lab: str, desc: str) -> None:
    """Compute the expected value into x8 with expr (x8 = IMPL, x9 = EN preloaded), XOR with actual, check 0."""
    ld(t, "x8", IMPL)
    ld(t, "x9", EN)
    for ln in expr:
        t.emit(ln)
    t.emit(f"xor x8, x8, {actual}")
    t.check("x8", 0, lab, desc)


def t_scountinhibit_exists() -> TestFile:
    t = new("Ssccfg_scountinhibit_exists")
    t.describe(
        source=SRC,
        rule_text="Smcdeleg/Ssccfg defines a new scountinhibit register, a masked alias of mcountinhibit.",
        context="scountinhibit (0x120) exists for S-mode when menvcfg.CDE=1. As a masked alias, it shows "
        "mcountinhibit's bits for delegated counters (mcounteren[i]=1) and writes reach mcountinhibit for those "
        "bits. mcountinhibit is WARL: IMPL = the bits that hold 1 after an M-mode write of all ones; mcounteren "
        "bits are read back too. Bit 1 (TM) has no inhibit bit.",
        plan="CDE=1, mcounteren = all ones (EN read back):\n"
        "1. All eight CSR forms of scountinhibit in S-mode: no trap; csrrw returns the old value.\n"
        "2. M-mode writes mcountinhibit = 0x55555555: scountinhibit reads 0x55555555 & IMPL & EN.\n"
        "3. S-mode writes scountinhibit = 0xAAAAAAAA: mcountinhibit reads (0xAAAAAAAA & EN | 0x55555555 & ~EN) & "
        "IMPL.\n"
        "mcountinhibit and mcounteren are restored.",
    )
    all_en(t)
    probe_impl(t)
    cde(t, True)
    for f in FORMS:
        scountinhibit_win(t, "S", f, "ok", "CDE=1")
    t.emit("csrw CSR_SCOUNTINHIBIT, x0")
    m_op(t, "WRITE", "CSR_MCOUNTINHIBIT", imm=0x55555555)
    lab = t.label("rd")
    t.emit(f"{lab}:", 0)
    t.emit("csrr x7, CSR_SCOUNTINHIBIT")
    expr = ["LI(x6, 0x55555555)", "and x8, x8, x6"] + ([] if MUT == "scountinhibit_unmasked" else ["and x8, x8, x9"])
    ci_check(t, "x7", expr, lab, "scountinhibit XOR (0x55555555 & IMPL & EN)")
    lab = t.label("wr")
    t.emit("LI(x6, 0xAAAAAAAA)", 2)
    t.emit(f"{lab}:", 0)
    t.emit("csrrw x7, CSR_SCOUNTINHIBIT, x6")
    ci_check(t, "x7", expr, lab, "csrrw scountinhibit returns the old value (0x55555555 & IMPL & EN)")
    m_op(t, "READ", "CSR_MCOUNTINHIBIT")
    ci_check(
        t,
        "a0",
        [
            "LI(x6, 0xAAAAAAAA)",
            "and x6, x6, x9",
            "not x5, x9",
            "LI(x7, 0x55555555)",
            "and x5, x5, x7",
            "or x6, x6, x5",
            "and x8, x8, x6",
        ],
        lab,
        "mcountinhibit XOR ((0xAAAAAAAA & EN | 0x55555555 & ~EN) & IMPL) after the S-mode write",
    )
    end(t)
    return t


PATS = [-1, 0x55555555, 0xAAAAAAAA, 0x5, 0x80000008]


def t_scountinhibit_delegated_rw() -> list[TestFile]:
    t = new("Ssccfg_scountinhibit_delegated_rw")
    t.describe(
        source=SRC,
        rule_text="For counters delegated to S-mode, the associated mcountinhibit bits can be accessed via "
        "scountinhibit",
        context="A counter is delegated when mcounteren[i]=1 (with CDE=1). For those bits, S-mode reads and writes "
        "of scountinhibit read and write mcountinhibit. Expected values use IMPL (mcountinhibit bits that hold "
        "1) and EN (mcounteren read back).",
        plan="CDE=1. For mcounteren patterns all ones, 0x55555555, 0xAAAAAAAA, 0x5 (CY, IR), 0x80000008 and a "
        "random one:\n"
        "1. mcountinhibit = 0; S-mode csrw scountinhibit = all ones: mcountinhibit = IMPL & EN, scountinhibit "
        "reads IMPL & EN.\n"
        "2. S-mode csrc of 0x0F0F0F0F: mcountinhibit = IMPL & EN & ~0x0F0F0F0F.\n"
        "3. M-mode mcountinhibit = all ones; S-mode csrw 0: mcountinhibit = IMPL & ~EN.",
    )
    m = new_sm("Ssccfg_scountinhibit_delegated_rw")
    m.describe(
        source=SRC,
        rule_text=t.doc["rule_text"],
        context="M-mode part: scountinhibit is a masked alias of "
        "mcountinhibit from M-mode too (it exists whenever CDE=1). " + t.doc["context"],
        plan="The same sweep with the scountinhibit accesses in M-mode.",
    )
    return [scountinhibit_delegated_rw_body(t), scountinhibit_delegated_rw_body(m)]


def scountinhibit_delegated_rw_body(t: TestFile) -> TestFile:
    cde(t, True)
    probe_impl(t)
    for p in PATS + [t.rand(32)]:
        men_write(t, p, EN)
        d = f"mcounteren {p & 0xFFFFFFFF:#010x}"
        m_op(t, "WRITE", "CSR_MCOUNTINHIBIT", imm=0)
        lab = t.label("set")
        t.emit("li x6, -1")
        t.emit(f"{lab}:", 0)
        t.emit("csrw CSR_SCOUNTINHIBIT, x6")
        m_op(t, "READ", "CSR_MCOUNTINHIBIT")
        ci_check(
            t, "a0", ["and x8, x8, x9"], lab, f"mcountinhibit XOR (IMPL & EN) after {t.boot}-mode writes all ones, {d}"
        )
        t.emit("csrr x7, CSR_SCOUNTINHIBIT")
        ci_check(t, "x7", ["and x8, x8, x9"], lab, f"scountinhibit XOR (IMPL & EN), {d}")
        lab = t.label("clr")
        t.emit("LI(x6, 0x0F0F0F0F)", 2)
        t.emit(f"{lab}:", 0)
        t.emit("csrc CSR_SCOUNTINHIBIT, x6")
        m_op(t, "READ", "CSR_MCOUNTINHIBIT")
        ci_check(
            t,
            "a0",
            ["and x8, x8, x9", "LI(x6, 0xF0F0F0F0)", "and x8, x8, x6"],
            lab,
            f"mcountinhibit XOR (IMPL & EN & ~0x0F0F0F0F) after {t.boot}-mode csrc, {d}",
        )
        m_op(t, "WRITE", "CSR_MCOUNTINHIBIT", imm=-1)
        lab = t.label("zero")
        t.emit(f"{lab}:", 0)
        t.emit("csrw CSR_SCOUNTINHIBIT, x0")
        m_op(t, "READ", "CSR_MCOUNTINHIBIT")
        expr = [] if MUT == "scountinhibit_writes_nondeleg" else ["not x9, x9", "and x8, x8, x9"]
        if MUT == "scountinhibit_writes_nondeleg":
            expr = ["li x8, 0"]
        ci_check(t, "a0", expr, lab, f"mcountinhibit XOR (IMPL & ~EN) after {t.boot}-mode writes 0, {d}")
    end(t)
    return t


def t_scountinhibit_nondelegated_ro() -> list[TestFile]:
    t = new("Ssccfg_scountinhibit_nondelegated_ro")
    t.describe(
        source=SRC,
        rule_text="For counters not delegated to S-mode, the associated bits in scountinhibit are read-only zero.",
        context="A counter is not delegated when mcounteren[i]=0. Those scountinhibit bits read 0 whatever "
        "mcountinhibit holds, and S-mode writes to them do not reach mcountinhibit. The mask is applied on access, "
        "not stored: clearing a mcounteren bit hides a set mcountinhibit bit, and setting it again shows it.",
        plan="CDE=1. For mcounteren patterns 0, 0x55555555, 0xAAAAAAAA, 0x5, 0x80000008 and a random one:\n"
        "1. M-mode mcountinhibit = all ones: scountinhibit reads IMPL & EN; csrrs of all ones returns the same.\n"
        "2. M-mode mcountinhibit = 0: S-mode csrw all ones leaves the non-delegated bits 0 "
        "(mcountinhibit & ~EN = 0), and S-mode reads show no bit outside EN. M-mode mcountinhibit = all ones: "
        "S-mode csrw 0 leaves them 1 (mcountinhibit = IMPL & ~EN).\n"
        "3. Transition: mcounteren = all ones, mcountinhibit = all ones; mcounteren = 0: scountinhibit reads 0 and "
        "mcountinhibit still IMPL; mcounteren = all ones: scountinhibit reads IMPL again.",
    )
    m = new_sm("Ssccfg_scountinhibit_nondelegated_ro")
    m.describe(
        source=SRC,
        rule_text=t.doc["rule_text"],
        context="M-mode part: the read-only-zero bits apply to "
        "M-mode accesses of scountinhibit too (M-mode reaches mcountinhibit directly). " + t.doc["context"],
        plan="The same sweep with the scountinhibit accesses in M-mode.",
    )
    return [scountinhibit_nondelegated_ro_body(t), scountinhibit_nondelegated_ro_body(m)]


def scountinhibit_nondelegated_ro_body(t: TestFile) -> TestFile:
    cde(t, True)
    probe_impl(t)
    for p in [0] + PATS[1:] + [t.rand(32)]:
        men_write(t, p, EN)
        d = f"mcounteren {p & 0xFFFFFFFF:#010x}"
        m_op(t, "WRITE", "CSR_MCOUNTINHIBIT", imm=-1)
        lab = t.label("rd")
        t.emit(f"{lab}:", 0)
        t.emit("csrr x7, CSR_SCOUNTINHIBIT")
        expr = [] if MUT == "scountinhibit_unmasked" else ["and x8, x8, x9"]
        ci_check(t, "x7", expr, lab, f"scountinhibit XOR (IMPL & EN) with mcountinhibit all ones, {d}")
        t.emit("li x6, -1")
        t.emit("csrrs x7, CSR_SCOUNTINHIBIT, x6")
        ci_check(t, "x7", expr, lab, f"csrrs scountinhibit old value XOR (IMPL & EN), {d}")
        m_op(t, "WRITE", "CSR_MCOUNTINHIBIT", imm=0)
        lab = t.label("wr")
        t.emit("li x6, -1")
        t.emit(f"{lab}:", 0)
        t.emit("csrw CSR_SCOUNTINHIBIT, x6")
        m_op(t, "READ", "CSR_MCOUNTINHIBIT")
        ld(t, "x9", EN)
        t.emit("not x9, x9")
        t.emit("and a0, a0, x9")
        if MUT == "scountinhibit_writes_nondeleg":
            ld(t, "x8", IMPL)
            t.emit("and x8, x8, x9")
            t.emit("xor a0, a0, x8")
        t.check("a0", 0, lab, f"non-delegated mcountinhibit bits after an {t.boot}-mode write of all ones, {d}")
        t.emit("csrr x7, CSR_SCOUNTINHIBIT")
        t.emit("and x7, x7, x9")
        t.check("x7", 0, lab, f"scountinhibit bits outside EN, {d}")
        m_op(t, "WRITE", "CSR_MCOUNTINHIBIT", imm=-1)
        lab = t.label("wr0")
        t.emit(f"{lab}:", 0)
        t.emit("csrw CSR_SCOUNTINHIBIT, x0")
        m_op(t, "READ", "CSR_MCOUNTINHIBIT")
        expr = ["li x8, 0"] if MUT == "scountinhibit_writes_nondeleg" else ["not x9, x9", "and x8, x8, x9"]
        ci_check(
            t, "a0", expr, lab, f"mcountinhibit XOR (IMPL & ~EN) after an {t.boot}-mode write of 0 over all ones, {d}"
        )
    lab = t.label("tr")
    men_write(t, -1, EN)
    m_op(t, "WRITE", "CSR_MCOUNTINHIBIT", imm=-1)
    men_write(t, 0)
    t.emit(f"{lab}:", 0)
    t.emit("csrr x7, CSR_SCOUNTINHIBIT")
    t.check("x7", 0, lab, "scountinhibit after mcounteren is cleared (mcountinhibit all ones)")
    m_op(t, "READ", "CSR_MCOUNTINHIBIT")
    ci_check(t, "a0", [], lab, "mcountinhibit XOR IMPL after mcounteren is cleared (state kept)")
    men_write(t, -1)
    t.emit("csrr x7, CSR_SCOUNTINHIBIT")
    ci_check(t, "x7", ["and x8, x8, x9"], lab, "scountinhibit XOR (IMPL & EN) after mcounteren is set again")
    end(t)
    return t


def t_illegal_scountinhibit_cde0() -> list[TestFile]:
    rt = "When menvcfg.CDE=0, attempts to access scountinhibit raise an illegal-instruction exception."
    iss = (
        f"{ISSUE}2087: gfavor confirms (1) U-mode access raises illegal instruction, (2) with CDE=0 access from "
        'M/HS/VS raises illegal instruction, (3) with CDE=1 VS/VU raise virtual instruction; "When menvcfg.CDE=0, '
        'attempts to access scountinhibit raise an illegal instruction exception" covers VU-mode too.'
    )
    t = new("Ssccfg_illegal_scountinhibit_cde0")
    t.describe(
        source=SRC,
        rule_text=rt,
        context="With CDE=0 Ssccfg appears not implemented, so scountinhibit raises illegal instruction from every "
        "mode, VS and VU included. mcounteren is all ones, so the delegation would otherwise allow it. A trapped "
        "write leaves mcountinhibit unchanged.",
        issues=iss,
        plan="mcounteren = all ones, mcountinhibit = 0, CDE=1 then 0 (the transition):\n"
        "1. S-mode: all eight forms raise illegal instruction.\n"
        "2. U-mode: read and write raise illegal instruction.\n"
        "3. With H: VS-mode and VU-mode read and write raise illegal instruction.\n"
        "4. mcountinhibit is still 0.",
    )
    m = new_sm("Ssccfg_illegal_scountinhibit_cde0")
    m.describe(
        source=SRC,
        rule_text=rt,
        context="M-mode part: with CDE=0, M-mode accesses raise illegal instruction too.",
        issues=iss,
        plan="CDE=0, mcounteren all ones: all eight forms in M-mode raise illegal instruction; "
        "mcountinhibit is unchanged.",
    )
    for x in (t, m):
        all_en(x)
        m_op(x, "WRITE", "CSR_MCOUNTINHIBIT", imm=0)
        cde(x, True)
        cde(x, False)
        exp = "ok" if MUT == "scountinhibit_cde0_ok" else "illegal"
        for f in FORMS:
            scountinhibit_win(x, bmode(x), f, exp, "CDE=0")
        if x.boot == "S":
            for mode in ("U",):
                for f in (READ, WRITE):
                    scountinhibit_win(x, mode, f, "illegal", "CDE=0")
            with x.only_if(H):
                for mode in ("VS", "VU"):
                    for f in (READ, WRITE):
                        scountinhibit_win(x, mode, f, exp, "CDE=0")
        lab = x.label("ci")
        x.emit(f"{lab}:", 0)
        m_op(x, "READ", "CSR_MCOUNTINHIBIT")
        x.check("a0", 0, lab, "mcountinhibit after the trapped writes")
        end(x)
    return [t, m]


def t_illegal_scountinhibit_vs_vu() -> TestFile:
    t = new("Ssccfg_illegal_scountinhibit_vs_vu", required=HYP)
    t.describe(
        source=SRC,
        rule_text="When Supervisor Counter Delegation is enabled, attempts to access scountinhibit from VS-mode or "
        "VU-mode raise a virtual-instruction exception.",
        context="Enabled = menvcfg.CDE=1 (issue 2087). scountinhibit has no VS counterpart, so a guest's access "
        "traps to HS-mode for emulation, whatever mcounteren and hcounteren hold. Contrasts: S-mode accesses "
        "succeed; U-mode accesses raise illegal instruction (S-level CSR from U).",
        issues=f"{ISSUE}2087: gfavor: (3) when CDE=1, access to scountinhibit from VS/VU raises a virtual-instruction "
        "exception.",
        plan="CDE=1, mcountinhibit = 0. For (mcounteren, hcounteren) = (all, all) and (all, 0):\n"
        "1. VS-mode: all eight forms (once; read and write otherwise): virtual instruction.\n"
        "2. VU-mode: read and write: virtual instruction.\n"
        "3. U-mode read: illegal instruction; S-mode read: no trap.\n"
        "4. mcountinhibit is still 0 after the trapped writes.",
    )
    cde(t, True)
    m_op(t, "WRITE", "CSR_MCOUNTINHIBIT", imm=0)
    vexp = "illegal" if MUT == "vs_scountinhibit_illegal" else "virtual"
    first = True
    for hen in (-1, 0):
        all_en(t)
        t.li("x6", hen)
        t.emit("csrw CSR_HCOUNTEREN, x6")
        d = f"CDE=1, hcounteren {hen & 0xFFFFFFFF:#x}"
        for f in FORMS if first else [READ, WRITE]:
            scountinhibit_win(t, "VS", f, vexp, d)
        first = False
        for f in (READ, WRITE):
            scountinhibit_win(t, "VU", f, vexp, d)
        scountinhibit_win(t, "U", READ, "illegal", d)
        scountinhibit_win(t, "S", READ, "ok", d)
    lab = t.label("ci")
    t.emit(f"{lab}:", 0)
    m_op(t, "READ", "CSR_MCOUNTINHIBIT")
    t.check("a0", 0, lab, "mcountinhibit after the trapped VS/VU writes")
    t.emit("li x6, -1")
    t.emit("csrw CSR_HCOUNTEREN, x6")
    end(t)
    return t


def t_virtual_scountovf() -> TestFile:
    t = new("Ssccfg_virtual_scountovf_vs_vu", required=HYP + ["Sscofpmf"])
    t.describe(
        source=SRC,
        rule_text="For implementations that support Smcdeleg/Ssccfg, Sscofpmf, and the H extension, when "
        "menvcfg.CDE=1, attempts to read scountovf from VS-mode or VU-mode raise a virtual-instruction exception.",
        context="With CDE=1 the hypervisor emulates scountovf for its guest, so every VS/VU read traps to HS-mode, "
        "whatever mcounteren and hcounteren hold (with CDE=0, scountovf follows Sscofpmf's counter-enable rules "
        "and the Sscofpmf suite tests it). HS-mode reads are unaffected. scountovf is read-only; only read forms "
        "are used.",
        issues=f'{ISSUE}2287: virtualizing scountovf; gfavor: with CDE=0 "Smcdeleg effectively does not exist".',
        plan="CDE=1. For (mcounteren, hcounteren) HPM bits (all, all), (all, 0), (0, all):\n"
        "1. VS-mode: csrrs/csrrc rs1=x0 and csrrsi/csrrci uimm=0 reads of scountovf: virtual instruction.\n"
        "2. VU-mode read: virtual instruction.\n"
        "3. HS-mode read: no trap.\n"
        "4. Control: CDE=0 with (all, all): a VS-mode read does not trap.",
    )
    reads = [
        FORMS[0],
        ("csrrc x7, {c}, x0", 3, 7, 0, "read (csrrc rs1=x0)"),
        FORMS[6],
        ("csrrci x7, {c}, 0", 7, 7, 0, "read (csrrci uimm=0)"),
    ]
    cde(t, True)
    first = True
    vexp = "ok" if MUT == "vs_scountovf_ok" else "virtual"
    for men, hen in ((-1, -1), (-1, 7), (7, -1)):
        men_write(t, men)
        t.li("x6", hen)
        t.emit("csrw CSR_HCOUNTEREN, x6")
        d = f"CDE=1, mcounteren {men & 0xFFFFFFFF:#x}, hcounteren {hen & 0xFFFFFFFF:#x}"
        for f in reads if first else reads[:1]:
            csr_win(t, "VS", SCOUNTOVF, "scountovf", f, vexp, d)
        first = False
        csr_win(t, "VU", SCOUNTOVF, "scountovf", READ, vexp, d)
        csr_win(t, "S", SCOUNTOVF, "scountovf", READ, "ok", d)
    cde(t, False)
    men_write(t, -1)
    t.emit("li x6, -1")
    t.emit("csrw CSR_HCOUNTEREN, x6")
    csr_win(t, "VS", SCOUNTOVF, "scountovf", READ, "ok", "control: CDE=0, all counter enables set")
    end(t)
    return t


def t_lcofi_mvip_mvien() -> TestFile:
    t = TestFile(
        out("Smcdeleg"),
        "Ssccfg_lcofi_mvip_mvien",
        required=["I", "S", "Sm", "Smcdeleg", "Sscofpmf", "Smaia"],
        march=MARCH,
        boot="M",
        pool=POOL_TRAP,
    )
    t.describe(
        source=SRC,
        rule_text="For implementations that support Smcdeleg, Sscofpmf, and Smaia, the local-counter-overflow "
        "interrupt (LCOFI) bit (bit 13) in each of CSRs mvip and mvien is implemented and writable.",
        context="mvien/mvip are M-mode CSRs (Smaia), so the test boots to M-mode. With mideleg[13]=0 and "
        "mvien[13]=1, sip[13] is an alias of mvip[13] (AIA, interrupt filtering for supervisor level); mip.LCOFIP is "
        "a separate bit. menvcfg.CDE is set: with CDE=0 the LCOFI bits follow AIA alone (issue 2547). Nothing is "
        "taken: the pending S-level interrupt stays pending in M-mode (sie[13] becomes UNSPECIFIED when mvien[13] "
        "goes 0 to 1, which does not matter there). mideleg[13] may be read-only one (lower-level interrupt bits "
        "may be); then sip[13] aliases mip[13] and the alias case is skipped.",
        issues=f'{ISSUE}2547: gfavor: "When CDE=0, the Smcdeleg and Ssccfg extensions appear to not be '
        "implemented\", so CDE=0 behavior is AIA's.",
        plan="CDE=1, mideleg[13] = 0 (saved and restored):\n"
        "1. mvien[13]: csrs reads 1, csrc reads 0.\n"
        "2. mvip[13] with mvien[13] = 0: csrs reads 1, csrc reads 0.\n"
        "3. If mideleg[13] reads 0: mvien[13] = 1: mvip[13] csrs reads 1; sip[13] reads 1 (alias); mip[13] reads "
        "0; csrc: mvip[13] and sip[13] read 0.",
    )
    t.li("x6", 0xA)
    t.emit("csrc mstatus, x6")
    cde(t, True)
    t.emit("csrr x6, mideleg")
    st(t, "x6", TMP)
    t.li("x6", LCOF)
    t.emit("csrc mideleg, x6")
    t.emit("csrc mie, x6")
    t.emit("csrc sie, x6")
    t.emit("csrc mip, x6")

    def bit13(csr: str, exp: int, lab: str, desc: str) -> None:
        t.emit(f"csrr x7, {csr}")
        t.emit("srli x7, x7, 13")
        t.emit("andi x7, x7, 1")
        t.check("x7", exp, lab, desc)

    for csr, nm in (("CSR_MVIEN", "mvien"), ("CSR_MVIP", "mvip")):
        lab = t.label(nm)
        t.li("x6", LCOF)
        t.emit("csrc CSR_MVIEN, x6")
        t.emit(f"{lab}:", 0)
        t.emit(f"csrs {csr}, x6")
        bit13(
            csr, 0 if MUT == "mvip_lcofi_ro0" and nm == "mvip" else 1, lab, f"{nm}[13] after csrs (mvien[13]=0 before)"
        )
        t.li("x6", LCOF)
        t.emit(f"csrc {csr}, x6")
        bit13(csr, 0, lab, f"{nm}[13] after csrc")

    def alias() -> None:
        lab = t.label("alias")
        t.li("x6", LCOF)
        t.emit("csrs CSR_MVIEN, x6")
        t.emit(f"{lab}:", 0)
        t.emit("csrs CSR_MVIP, x6")
        bit13("CSR_MVIP", 0 if MUT == "mvip_lcofi_ro0" else 1, lab, "mvip[13] after csrs with mvien[13]=1")
        bit13(
            "sip",
            0 if MUT == "mvip_lcofi_ro0" else 1,
            lab,
            "sip[13] (alias of mvip[13] with mideleg[13]=0, mvien[13]=1)",
        )
        bit13("mip", 0, lab, "mip[13] (separate from mvip[13])")
        t.li("x6", LCOF)
        t.emit("csrc CSR_MVIP, x6")
        bit13("CSR_MVIP", 0, lab, "mvip[13] after csrc")
        bit13("sip", 0, lab, "sip[13] after mvip[13] is cleared")

    t.emit("csrr x1, mideleg")
    t.emit("srli x1, x1, 13")
    t.emit("andi x1, x1, 1")
    t.emit("seqz x1, x1")
    either(t, "x1", alias, "mideleg[13] is read-only one: sip[13] aliases mip[13], not mvip[13]")
    t.li("x6", LCOF)
    t.emit("csrc CSR_MVIEN, x6")
    ld(t, "x6", TMP)
    t.emit("csrw mideleg, x6")
    cde(t, False)
    return t


def t_lcofi_hvip_hvien() -> TestFile:
    t = new("Ssccfg_lcofi_hvip_hvien", required=HYP + ["Sscofpmf", "Ssaia"])
    t.describe(
        source=SRC,
        rule_text="For implementations that support Smcdeleg/Ssccfg, Sscofpmf, Smaia/Ssaia, and the H extension, the "
        "LCOFI bit (bit 13) in each of hvip and hvien is implemented and writable.",
        context="hvien/hvip are HS-mode CSRs. With hideleg[13]=0 and hvien[13]=1, vsip[13] is an alias of "
        "hvip[13] (AIA, interrupts for VS level); 'all other bits for interrupts 13-63 must be writable in hvip'. "
        "menvcfg.CDE is set (issue 2547: with CDE=0 AIA alone applies). Nothing is taken in HS-mode (vsie[13] becomes "
        "UNSPECIFIED when hvien[13] goes 0 to 1, which does not matter there).",
        issues=f'{ISSUE}2547: gfavor: with CDE=0 "the answer ... is solely based on what is specified in the AIA '
        'spec".',
        plan="CDE=1, hideleg[13] = 0 (saved and restored):\n"
        "1. hvien[13]: csrs reads 1, csrc reads 0.\n"
        "2. hvip[13] with hvien[13]=0: csrs reads 1, csrc reads 0.\n"
        "3. hvien[13] = 1: hvip[13] csrs: vsip[13] reads 1 (alias); csrc: both 0.",
    )
    cde(t, True)
    t.emit("csrr x6, CSR_HIDELEG")
    st(t, "x6", TMP)
    t.li("x6", LCOF)
    t.emit("csrc CSR_HIDELEG, x6")
    t.emit("csrc CSR_VSIE, x6")

    def bit13(csr: str, exp: int, lab: str, desc: str) -> None:
        t.emit(f"csrr x7, {csr}")
        t.emit("srli x7, x7, 13")
        t.emit("andi x7, x7, 1")
        t.check("x7", exp, lab, desc)

    for csr, nm in (("CSR_HVIEN", "hvien"), ("CSR_HVIP", "hvip")):
        lab = t.label(nm)
        t.li("x6", LCOF)
        t.emit("csrc CSR_HVIEN, x6")
        t.emit(f"{lab}:", 0)
        t.emit(f"csrs {csr}, x6")
        bit13(csr, 0 if MUT == "hvien_lcofi_ro0" and nm == "hvien" else 1, lab, f"{nm}[13] after csrs")
        t.li("x6", LCOF)
        t.emit(f"csrc {csr}, x6")
        bit13(csr, 0, lab, f"{nm}[13] after csrc")
    lab = t.label("alias")
    t.li("x6", LCOF)
    t.emit("csrs CSR_HVIEN, x6")
    t.emit(f"{lab}:", 0)
    t.emit("csrs CSR_HVIP, x6")
    bit13("CSR_VSIP", 1, lab, "vsip[13] (alias of hvip[13] with hideleg[13]=0, hvien[13]=1)")
    t.li("x6", LCOF)
    t.emit("csrc CSR_HVIP, x6")
    bit13("CSR_HVIP", 0, lab, "hvip[13] after csrc")
    bit13("CSR_VSIP", 0, lab, "vsip[13] after hvip[13] is cleared")
    t.li("x6", LCOF)
    t.emit("csrc CSR_HVIEN, x6")
    ld(t, "x6", TMP)
    t.emit("csrw CSR_HIDELEG, x6")
    end(t)
    return t


# ---------------------------------------------------------------- Smcntrpmf through sireg2/sireg5
CFG = {"cycle": ("CSR_MCYCLECFG", "CSR_MCYCLECFGH"), "instret": ("CSR_MINSTRETCFG", "CSR_MINSTRETCFGH")}
ALLINH = inh("M", "S", "U", "VS", "VU")


def cfg_set(t: TestFile, ctr: str, hv: int, note: str) -> None:
    """M-mode: mcyclecfg/minstretcfg bits 63:32 = hv (mcyclecfgh/minstretcfgh on RV32)."""
    lo, hi = CFG[ctr]
    t.load("x6", hx(hv), note)
    with t.rv64_only():
        t.emit(f"csrw {lo}, x6")
    with t.rv32_only():
        t.emit(f"csrw {hi}, x6")


def cfg_hi(t: TestFile, ctr: str, dst: str) -> None:
    """M-mode: dst = bits 63:32 of mcyclecfg/minstretcfg."""
    lo, hi = CFG[ctr]
    with t.rv64_only():
        t.emit(f"csrr {dst}, {lo}")
        t.emit(f"srli {dst}, {dst}, 32")
    with t.rv32_only():
        t.emit(f"csrr {dst}, {hi}")


def sireg_cfg(t: TestFile, write: bool) -> None:
    """S-mode: x6 -> sireg2 (sireg5 on RV32), or x7 = bits 63:32 of sireg2 (sireg5 on RV32)."""
    with t.rv64_only():
        t.emit("csrw CSR_SIREG2, x6" if write else "csrr x7, CSR_SIREG2")
        if not write:
            t.emit("srli x7, x7, 32")
    with t.rv32_only():
        t.emit("csrw CSR_SIREG5, x6" if write else "csrr x7, CSR_SIREG5")


def t_csr_supervisor_access() -> TestFile:
    t = TestFile(
        out("Smcdeleg"),
        "csr_supervisor_access",
        required=["I", "S", "Sm", "Zicntr", "Smcntrpmf", "Smcdeleg"],
        march=MARCH,
        boot="M",
        pool=POOL_TRAP,
    )
    t.describe(
        source="src/priv/smcntrpmf.adoc",
        rule_text="The content of these registers may be accessible from Supervisor level if the Smcdeleg/Ssccfg "
        "extensions are implemented.",
        context="Smcdeleg (src/priv/smcdeleg.adoc, Indirect HPM State Mappings): with menvcfg.CDE=1 and "
        "mcounteren.CY (IR) set, siselect 0x40 (0x42) maps sireg2 to cyclecfg (instretcfg) and, on RV32, sireg5 "
        'to cyclecfgh (instretcfgh). "cyclecfg and instretcfg may represent a subset of the state accessed by the '
        "mcyclecfg and minstretcfg registers ... If Smcntrpmf is implemented, counter configuration register bit 62 "
        '(MINH) is read-only 0 when accessed through sireg*." So an S-mode read shows MINH as 0 and an S-mode '
        "write leaves mcyclecfg.MINH unchanged, while the other xINH bits are the registers' own. mcyclecfg and "
        "minstretcfg are not in the T-SBI CSR table, so the test boots to M-mode (Sm) and enters S-mode with MRET. "
        "Ssccfg_missing_extension_illegal checks that the same accesses trap without Smcntrpmf.",
        issues=f"{ISSUE}2541: the sireg* view is the delegated architectural state, not the raw m* CSR; MINH is "
        'read-only zero there (ved-rivos: "when hpmevent* is accessed via sireg*, the MINH bit is read-only zero").',
        plan="menvcfg.CDE=1, mcounteren.CY=IR=1 (skipped if either stays 0). For cycle (siselect 0x40) and instret "
        "(0x42):\n"
        "1. M-mode writes the config high word MINH|SINH; an S-mode read of sireg2 (RV64) / sireg5 (RV32) shows "
        "SINH without MINH.\n"
        "2. S-mode writes all xINH bits: M-mode reads MINH still 1 and the implemented S/U (and VS/VU with H) bits "
        "1.\n"
        "3. The other counter's configuration is untouched (sireg2 at 0x40 does not reach minstretcfg).\n"
        "4. M-mode writes 0; S-mode writes MINH|UINH: M-mode reads UINH only (MINH not written).\n"
        "mcyclecfg/minstretcfg, CDE and mcounteren are restored.",
    )
    begin(t)
    cde(t, True)
    t.li("x6", 5)
    t.emit("csrs mcounteren, x6")
    t.emit("csrr x1, mcounteren")
    t.emit("andi x1, x1, 5")
    t.emit("addi x1, x1, -5")
    t.emit("seqz x1, x1")
    sinh = INH_HI["S"]
    implemented = [("!defined(H_SUPPORTED)", inh("M", "S", "U")), (H, ALLINH)]

    def body() -> None:
        for ctr, s in (("cycle", 0x40), ("instret", 0x42)):
            other = "instret" if ctr == "cycle" else "cycle"
            cfg_set(t, "cycle", 0, "0")
            cfg_set(t, "instret", 0, "0")
            cfg_set(t, ctr, INH_HI["M"] | sinh, "MINH|SINH")
            sel(t, s)
            lab = t.label("sread")
            t.enter("S")
            t.emit(f"{lab}:", 0)
            sireg_cfg(t, False)
            t.leave()
            t.check(
                "x7",
                (INH_HI["M"] | sinh) if MUT == "cfg_minh_visible" else sinh,
                lab,
                f"S-mode read of {ctr}cfg through sireg2/sireg5 (siselect {s:#x}) with M-level MINH|SINH: MINH reads 0",
            )
            lab = t.label("swrite")
            t.load("x6", hx(ALLINH), "all xINH")
            t.enter("S")
            t.emit(f"{lab}:", 0)
            sireg_cfg(t, True)
            t.leave()
            cfg_hi(t, ctr, "x7")
            for cond, bits in implemented:
                with t.only_if(cond):
                    t.check(
                        "x7", bits, lab, f"m{ctr}cfg high word after an S-mode sireg write of all xINH (MINH kept 1)"
                    )
            cfg_hi(t, other, "x7")
            t.check("x7", 0, lab, f"m{other}cfg after the S-mode write at siselect {s:#x}")
            cfg_set(t, ctr, 0, "0")
            lab = t.label("swrite2")
            t.load("x6", hx(INH_HI["M"] | INH_HI["U"]), "MINH|UINH")
            t.enter("S")
            t.emit(f"{lab}:", 0)
            sireg_cfg(t, True)
            t.leave()
            cfg_hi(t, ctr, "x7")
            exp = INH_HI["U"] | (INH_HI["M"] if MUT == "cfg_minh_written" else 0)
            t.check("x7", exp, lab, f"m{ctr}cfg high word after an S-mode sireg write of MINH|UINH (MINH not written)")
        cfg_set(t, "cycle", 0, "0")
        cfg_set(t, "instret", 0, "0")

    either(t, "x1", body, "mcounteren.CY or IR is read-only zero")
    end(t)
    return t


if __name__ == "__main__":
    for t in gen():
        print(t.write())
