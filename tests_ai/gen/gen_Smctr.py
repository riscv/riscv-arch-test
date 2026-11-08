#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate tests_ai/Ssctr and tests_ai/Smctr: one test per normative rule of the control transfer records
extension (src/priv/smctr.adoc).

Ssctr/<rule>.S boot to S-mode and need only the supervisor-level extension (sctrctl, vsctrctl, sctrdepth,
sctrstatus, the entry registers through siselect/sireg*, SCTRCLR). The M-mode parts of a rule (mctrctl, M-mode
recording, traps into M-mode, mstateen0.CTR) are Smctr/<rule>_Sm.S, which boot to M-mode and require Sm.
Helpers and the measurement pattern are in smctrlib.py.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

sys.path.insert(0, str(Path(__file__).parent))
import smctrlib as L
from aigen import TestFile, X
from smctrlib import (
    BPFRZ,
    BREAK,
    CTRDATA_WPRI,
    CUSTOM,
    FILTERS,
    FROZEN,
    ILLEGAL,
    LCOFIFRZ,
    MTE,
    RASEMU,
    RULES,
    SFIELDS,
    SRC,
    STE,
    VIRTUAL,
    C,
    H,
    M,
    S,
    U,
    Xfer,
    anchor,
    c,
    check_entry,
    check_n,
    check_xfer,
    jal,
    lo,
    off,
    rd,
    record_s,
    sctrclr,
    win,
    wr,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from aigen import Expect

T = TypeVar("T")

SUITE = "Smctr"
MUT = os.environ.get("AI_MUTANT", "")  # mutate.py: model a plausible bug in the expectations

MUTANTS: dict[str, str] = {
    "u_records_s": "sctrctl.U also enables recording in S-mode",
    "s_records_m": "mctrctl.S/U also enable recording in M-mode",
    "bpfrz_optional": "BPFRZ treated as optional (not mandatory)",
    "m_optional": "mctrctl.M treated as optional",
    "sctrctl_m_visible": "sctrctl exposes mctrctl.M",
    "mctrctl_s_access": "mctrctl accessible from S-mode",
    "mctrctl_ro": "mctrctl csrrc does not clear bits",
    "m_sctrclr_illegal": "SCTRCLR illegal in M-mode",
    "depth_short": "the buffer holds one record fewer than the depth",
    "drop_last_record": "the last transfer of a straight-line run is not recorded",
    "entries_beyond_rw": "entries beyond the depth are writable",
    "sireg4_rw": "sireg4..6 are writable for CTR entries",
    "ctrdata_wpri_rw": "ctrdata WPRI bits are writable",
    "stack_keeps_oldest": "a full buffer drops the newest record instead of the oldest",
    "wrptr_no_wrap": "WRPTR does not wrap at depth-1",
    "frozen_ignored": "FROZEN does not inhibit recording",
    "sctrclr_noop": "SCTRCLR does not clear the entries",
    "sctrclr_keeps_ccv": "the first record after SCTRCLR keeps CCV = 1",
    "sctrclr_u_ok": "SCTRCLR executes in U-mode",
    "sctrclr_vu_illegal": "SCTRCLR in VU-mode raises illegal instead of virtual instruction",
    "exc_type2": "exceptions recorded with TYPE 2",
    "int_type1": "interrupts recorded with TYPE 1",
    "mret_type1": "mret recorded with TYPE 1",
    "x5_not_link": "x5 not treated as a link register",
    "jalr_rd_rs_same_swap": "jalr x1, x1 treated as a co-routine swap",
    "ret_needs_rd0": "a return needs rd = x0",
    "ntbr_default": "not-taken branches recorded by default",
    "filter_ignored_call": "a filter bit also inhibits direct calls",
    "vfilter_from_target": "transfer-type filters of VS->HS traps come from sctrctl",
    "excinh_ignored": "EXCINH does not inhibit exceptions",
    "intrinh_ignored": "INTRINH does not inhibit interrupts",
    "trap_src_zero": "traps between enabled modes record ctrsource 0",
    "trap_src_kept": "traps from a disabled mode record the real ctrsource",
    "tret_tgt_kept": "trap returns into a disabled mode record the real ctrtarget",
    "tret_tgt_zero": "trap returns between enabled modes record ctrtarget 0",
    "tret_from_disabled": "trap returns from a disabled mode are recorded",
    "external_default": "external traps are recorded without xTE",
    "ext_tgt_kept": "external traps record the real ctrtarget",
    "ext_obeys_excinh": "external trap recording obeys EXCINH",
    "ste_ignored": "sctrctl.STE does not enable external traps",
    "vs_ste_ignored": "vsctrctl.STE does not enable external traps",
    "no_intervening": "VU->HS external traps do not need vsctrctl.STE",
    "no_intervening_m": "U->M external traps do not need sctrctl.STE",
    "vuvs_uses_sctrctl": "VU->VS external traps use sctrctl.STE",
    "vuhs_needs_only_ste": "VU->HS external traps need only sctrctl.STE",
    "vshs_needs_vsste": "VS->HS external traps need vsctrctl.STE",
    "mte_ignored": "mctrctl.MTE does not enable external traps to M-mode",
    "sm_needs_ste": "S->M external traps need sctrctl.STE",
    "sm_ste_enough": "S->M external traps need only sctrctl.STE",
    "um_mte_only": "U->M external traps need only MTE",
    "vsm_mte_only": "VS->M external traps need only MTE",
    "vsm_needs_vsste": "VS->M external traps need vsctrctl.STE",
    "vum_no_vsste": "VU->M external traps do not need all three enables",
    "bpfrz_ignored": "BPFRZ does not freeze",
    "bpfrz_only_enabled_target": "BPFRZ freezes only when the trap target mode is enabled",
    "vs_bpfrz_ignored": "vsctrctl.BPFRZ does not freeze on breakpoints to VS-mode",
    "vs_bpfrz_uses_sctrctl": "breakpoints to VS-mode freeze according to sctrctl.BPFRZ",
    "freeze_vs_wrong_ctl": "the freeze control register for VS/HS targets is swapped",
    "lcofifrz_ignored": "LCOFIFRZ does not freeze",
    "lcofi_always_freezes": "an LCOFI freezes with LCOFIFRZ = 0",
    "lcofi_recorded": "the freezing LCOFI is recorded",
    "vs_lcofifrz_ignored": "vsctrctl.LCOFIFRZ does not freeze on LCOFIs to VS-mode",
    "vs_lcofifrz_uses_sctrctl": "LCOFIs to VS-mode freeze according to sctrctl.LCOFIFRZ",
    "vs_s_ignored": "vsctrctl.U also enables VS-mode",
    "vu_uses_vs_s": "vsctrctl.S enables VU-mode",
    "vu_uses_sctrctl_u": "sctrctl.U enables VU-mode",
    "vs_sees_sctrctl": "VS-mode reads of sctrctl return sctrctl",
    "vs_entries_separate": "V=1 has its own entry registers",
    "sctrdepth_vs_ok": "sctrdepth accessible from VS-mode",
    "sctrdepth_stateen_virtual": "VS sctrdepth with mstateen0.CTR=0 raises virtual instruction",
    "hstateen_ignored": "hstateen0.CTR does not gate VS-mode CTR state",
    "hstateen_illegal": "hstateen0.CTR=0 raises illegal instead of virtual instruction",
    "hstateen_stops_recording": "hstateen0.CTR=0 stops V=1 recording",
    "hstateen_ctr_writable": "hstateen0.CTR writable while mstateen0.CTR=0",
    "stateen_ctr1_traps": "mstateen0.CTR=1 still traps S-mode accesses",
    "stateen_virtual": "mstateen0.CTR=0 raises virtual instruction from VS/VU",
    "stateen_csr_ok": "mstateen0.CTR does not gate sctrstatus",
    "stateen_sireg_ok": "mstateen0.CTR does not gate sireg* for CTR entries",
    "stateen_sctrclr_ok": "mstateen0.CTR does not gate SCTRCLR",
    "stateen_stops_recording": "mstateen0.CTR=0 stops recording",
    "rasemu_no_pop": "RASEMU returns do not pop",
    "pop_keeps_v": "RASEMU pops leave V=1",
    "swap_pushes": "RASEMU co-routine swaps push",
    "rasemu_keeps_ste": "RASEMU keeps external trap recording",
    "cc_counts_frozen": "the cycle counter runs while frozen",
    "ccv_survives_reset": "CCV stays 1 after an sctrctl write or SCTRCLR",
    "cce_extra_bit": "records use an unimplemented CCE bit",
    "misp_set_unimpl": "MISP set in records although it is not implemented",
}

TESTS: list[Callable[[], list[TestFile]]] = []


def rule(fn: Callable[[], list[TestFile]]) -> Callable[[], list[TestFile]]:
    TESTS.append(fn)
    return fn


def out(suite: str) -> str:
    return suite if SUITE == "Smctr" else SUITE


def s_test(
    name: str, plan: str, context: str = "", issues: str = "", required: list | None = None, rv64: bool = False
) -> TestFile:
    t = L.new(out("Ssctr"), name, required=required or ["I", "S", "Ssctr"], rv64=rv64)
    t.describe(rule_text=RULES[name], source=SRC, context=context, issues=issues, plan=plan)
    return t


def m_test(
    name: str, plan: str, context: str = "", issues: str = "", required: list | None = None, rv64: bool = False
) -> TestFile:
    t = L.new(out("Smctr"), name, required=required or ["I", "S", "Smctr", "Sm"], boot="M", rv64=rv64, suffix="_Sm")
    t.describe(rule_text=RULES[name], source=SRC, context=context, issues=issues, plan=plan)
    return t


CTX_MEASURE = (
    "Each measurement stops recording (sctrctl = 0), sets sctrstatus = 0 (WRPTR = 0) and executes SCTRCLR, sets "
    "the configuration, runs the transfers under test as straight-line code, and stops recording again before "
    "reading sctrstatus.WRPTR (the number of records since the anchor) and the entries through siselect = "
    "0x200 + logical entry and sireg/sireg2/sireg3 (ctrsource/ctrtarget/ctrdata). Recorded transfers have "
    "ctrsource = pc | V; ctrtarget may have MISP set; ctrdata.TYPE is the transfer type or 0 (TYPE is optional)."
)


# ================================================================ mode enables
@rule
def mctrctl_mode_op() -> list[TestFile]:
    t = s_test(
        "mctrctl_mode_op",
        plan="1. sctrctl.S=1: an S-mode jal is recorded (one record: source, target, TYPE 9 or 0).\n"
        "2. sctrctl.U=1, S=0: an S-mode jal is not recorded; a U-mode jal is (one record).\n"
        "3. sctrctl.S=1, U=0 around a U-mode window: the U-mode jal is not recorded. The first record after the "
        "anchor is the sret into U-mode (enabled to disabled: ctrtarget.PC = 0) and the second is the ecall that "
        "leaves U-mode (disabled to enabled: ctrsource.PC = 0).\n"
        "4. sctrctl.U=1 and S=1 do not enable VS/VU-mode (H): with vsctrctl = 0 a VS-mode jal is not recorded; "
        "the first two records are the sret into VS-mode (target PC 0) and the ecall out of it (source PC 0).\n"
        "The M-mode bit is tested in mctrctl_mode_op_Sm.",
        context=CTX_MEASURE,
    )
    record_s(t, S, lambda: [jal(t, "x1")], "sctrctl.S=1: S-mode jal")
    anchor(t)
    wr(t, "sctrctl", U)
    js = jal(t, "x0", "S-mode jal x0")
    (ju,), _, _ = win(t, "U", lambda: [jal(t, "x7")], desc="U-mode jal with sctrctl.U=1")
    off(t)
    rec = [ju] if MUT != "u_records_s" else [js, ju]
    check_n(t, len(rec), "sctrctl.U=1: only the U-mode jal")
    for i, x in enumerate(reversed(rec)):
        check_xfer(t, x, "sctrctl.U=1", logical=i)

    for mode, vs in (("U", False), ("VS", True)):

        def case(mode: str = mode, vs: bool = vs) -> None:
            anchor(t)
            if vs:
                wr(t, "vsctrctl", 0)
            wr(t, "sctrctl", S if not vs else S | U)
            (jx,), lab, _goto = win(t, mode, lambda: [jal(t, "x1")], desc=f"{mode}-mode jal")
            off(t)
            d = f"sctrctl={'S|U' if vs else 'S'} around a {mode}-mode window"
            L.check_n_ge(t, 2, d)
            check_entry(
                t, f"{d}: the sret into {mode}-mode (to a disabled mode)", src=f"{lab}-4", tgt=0, typ=L.T_TRET, k=0
            )
            check_entry(t, f"{d}: the ecall out of {mode}-mode (from a disabled mode)", src=0, typ=L.T_EXC, k=1)
            L.check_tgt_handler(t, f"{d}: the ecall out of {mode}-mode")
            L.not_first(t, jx.src, f"{d}: the {mode}-mode jal")

        if vs:
            with t.only_if(H):
                case()
        else:
            case()
    return [t]


@rule
def ctr_behavior_criteria_priv_mode() -> list[TestFile]:
    t = s_test(
        "ctr_behavior_criteria_priv_mode",
        plan="Exactly one mode is enabled at a time and a jal runs in S-mode and in the other mode:\n"
        "1. sctrctl.S only: both S-mode jals are recorded (U-mode with S only is in mctrctl_mode_op).\n"
        "2. sctrctl.U only: only the U-mode jal is recorded (entering and leaving U-mode record nothing: S-mode is "
        "disabled and sctrctl.STE=0).\n"
        "3. H: vsctrctl.S only (sctrctl = 0): only the VS-mode jal is recorded; the HS-mode jal is not.\n"
        "4. H: vsctrctl.U only: only the VU-mode jal is recorded; VS-mode and HS-mode jals are not.\n"
        "5. Nothing enabled (sctrctl = vsctrctl = 0): no records from S, U, VS or VU jals.",
        context=CTX_MEASURE,
    )
    record_s(t, S, lambda: [jal(t, "x0"), jal(t, "x6")], "sctrctl.S only")
    anchor(t)
    wr(t, "sctrctl", U)
    jal(t, "x0", "S-mode jal")
    (ju,), _, _ = win(t, "U", lambda: [jal(t, "x6")], desc="sctrctl.U only")
    off(t)
    check_n(t, 1, "sctrctl.U only: the U-mode jal")
    check_xfer(t, ju, "sctrctl.U only", logical=0)
    with t.only_if(H):
        for bit, mode in ((S, "VS"), (U, "VU")):
            anchor(t)
            wr(t, "vsctrctl", bit)
            jal(t, "x0", "HS-mode jal")
            if mode == "VU":
                (_jv,), _, _ = win(t, "VS", lambda: [jal(t, "x6")], desc="vsctrctl.U only, VS-mode jal")
            (jx,), _, _ = win(t, mode, lambda: [jal(t, "x7")], desc=f"vsctrctl.{'S' if bit == S else 'U'} only")
            off(t, "vsctrctl")
            d = f"vsctrctl.{'S' if bit == S else 'U'} only"
            check_n(t, 1, f"{d}: the {mode}-mode jal")
            check_xfer(t, jx, d, logical=0)
    anchor(t)
    jal(t, "x0", "S-mode jal")
    win(t, "U", lambda: [jal(t, "x6")], desc="nothing enabled")
    with t.only_if(H):
        win(t, "VS", lambda: [jal(t, "x6")], desc="nothing enabled")
        win(t, "VU", lambda: [jal(t, "x6")], desc="nothing enabled")
    check_n(t, 0, "nothing enabled")
    return [t]


# ================================================================ sctrctl / mctrctl fields
def field_sweep(t: TestFile, name: str, fields: int, desc: str) -> None:
    """Write all ones, read back v (x8); then for each field bit f write f alone and require readback == f & v,
    then write 0 and require 0 (implemented fields are writable, others read-only 0)."""
    lab = t.label("all")
    t.emit(f"{lab}:", 0)
    t.emit("li x6, -1")
    t.emit(f"csrw {c(name)}, x6  // all ones")
    t.emit(f"csrr x8, {c(name)}")
    t.load("x6", lo(fields), "field bits")
    t.emit("and x9, x8, x6")
    t.emit("xor x9, x9, x8  // set bits outside the fields")
    t.check("x9", 0, lab, f"{desc}: after writing all ones, only field bits read 1 (WPRI and read-only-0 bits read 0)")
    bits = [1 << i for i in range(64) if fields >> i & 1 and not (CUSTOM >> i & 1)]
    for b in bits:
        with t.rv64_only() if b >> 32 else _noop():
            lab = t.label("bit")
            t.emit(f"{lab}:", 0)
            wr(t, name, b, reg="x6", note=f"{name} = bit {b.bit_length() - 1} alone")
            t.emit(f"csrr x7, {c(name)}")
            t.load("x6", lo(b))
            t.emit("and x6, x6, x8  // the bit if it is implemented")
            t.emit("xor x7, x7, x6")
            t.emit("seqz x7, x7")
            t.check_bool(
                "x7",
                lab,
                f"{desc}: writing bit {b.bit_length() - 1} alone reads back the bit if it is "
                "implemented (read 1 after all ones), else 0; no other bit changes",
            )
    lab = t.label("zero")
    t.emit(f"{lab}:", 0)
    t.emit(f"csrw {c(name)}, x0")
    t.emit(f"csrr x7, {c(name)}")
    t.check("x7", 0, lab, f"{desc}: writing 0 clears every field (custom bits 0 = standard behavior)")


class _noop:
    def __enter__(self) -> None:
        return None

    def __exit__(self, *a: object) -> None:
        return None


@rule
def mctrctl_impl() -> list[TestFile]:
    t = s_test(
        "mctrctl_impl",
        plan="Through sctrctl (S-mode view of mctrctl):\n"
        "1. After writing all ones, U, S and BPFRZ read 1 (mandatory), and LCOFIFRZ reads 1 when Sscofpmf is "
        "implemented.\n"
        "2. Every field written alone reads back as itself if it read 1 after the all-ones write, else 0 "
        "(implemented fields are writable, unimplemented ones read-only 0), and writing 0 reads 0.\n"
        "RV32 reaches only bits 31:0 (no sctrctlh). The M bit is tested in mctrctl_impl_Sm.",
    )
    t.emit("li x6, -1")
    t.emit(f"csrw {c('sctrctl')}, x6")
    t.emit(f"csrr x8, {c('sctrctl')}")
    lab = t.label("mand")
    t.emit(f"{lab}:", 0)
    mand = U | S | BPFRZ
    t.li("x6", mand)
    t.emit("and x7, x8, x6")
    t.check("x7", mand if MUT != "bpfrz_optional" else U | S, lab, "sctrctl all ones: U, S and BPFRZ are implemented")
    with t.only_if(L.SSCOFPMF):
        t.li("x6", LCOFIFRZ)
        t.emit("and x7, x8, x6")
        t.check("x7", LCOFIFRZ, lab, "Sscofpmf: sctrctl.LCOFIFRZ is writable")
    field_sweep(t, "sctrctl", SFIELDS, "sctrctl")
    return [t]


@rule
def Ssctr_sctrctl_acc() -> list[TestFile]:
    t = s_test(
        "Ssctr_sctrctl_acc",
        plan="1. Writing all ones to sctrctl leaves bits 2 (M) and 9 (MTE) 0.\n"
        "2. Writing M|MTE alone reads 0.\n"
        "3. The other mctrctl fields are reachable: U, S and BPFRZ (mandatory) read back after writing all ones; "
        "the optional ones are swept in mctrctl_impl.",
    )
    lab = t.label("ones")
    t.emit(f"{lab}:", 0)
    t.emit("li x6, -1")
    t.emit(f"csrw {c('sctrctl')}, x6")
    t.emit(f"csrr x7, {c('sctrctl')}")
    t.li("x6", M | MTE)
    t.emit("and x8, x7, x6")
    t.check("x8", 0 if MUT != "sctrctl_m_visible" else M, lab, "sctrctl all ones: bits 2 and 9 read 0")
    t.li("x6", U | S | BPFRZ)
    t.emit("and x8, x7, x6")
    t.check("x8", U | S | BPFRZ, lab, "sctrctl all ones: U, S and BPFRZ are reachable")
    lab = t.label("mmte")
    t.emit(f"{lab}:", 0)
    t.li("x6", M | MTE)
    t.emit(f"csrw {c('sctrctl')}, x6")
    t.emit(f"csrr x7, {c('sctrctl')}")
    t.check("x7", 0, lab, "sctrctl = M|MTE reads 0")
    off(t)
    return [t]


@rule
def Ssctr_sctrctl_op() -> list[TestFile]:
    t = s_test(
        "Ssctr_sctrctl_op",
        plan="sctrctl is a view of mctrctl, observable from S-mode by its effect: writing sctrctl.S=1 makes S-mode "
        "jals recorded and S=0 stops it, and a value written to sctrctl reads back (U|S|BPFRZ). The mapping onto "
        "mctrctl bits is checked in M-mode in Ssctr_sctrctl_op_Sm.",
        context=CTX_MEASURE,
    )
    lab = t.label("rb")
    t.emit(f"{lab}:", 0)
    t.li("x6", U | S | BPFRZ)
    t.emit(f"csrw {c('sctrctl')}, x6")
    t.emit(f"csrr x7, {c('sctrctl')}")
    t.check("x7", U | S | BPFRZ, lab, "sctrctl = U|S|BPFRZ reads back")
    off(t)
    record_s(t, S, lambda: [jal(t, "x0")], "sctrctl.S=1")
    record_s(t, U, lambda: [jal(t, "x0")], "sctrctl.S=0", expect=False)
    return [t]


@rule
def Ssctr_transfer_steps() -> list[TestFile]:
    t = s_test(
        "Ssctr_transfer_steps",
        plan="Ssctr excludes the machine-level CSRs: every CSR instruction form on mctrctl (0x34E) raises "
        "illegal-instruction in S-mode (xtval 0 or the instruction), while sctrctl, sctrdepth, sctrstatus, "
        "siselect = 0x200 with sireg..sireg6, and SCTRCLR do not trap in S-mode.",
    )
    for f3, rdn, rs1, form in (
        (2, 7, 0, "csrr x7, {c}"),
        (1, 0, 6, "csrw {c}, x6"),
        (2, 7, 6, "csrrs x7, {c}, x6"),
        (3, 7, 6, "csrrc x7, {c}, x6"),
        (5, 7, 1, "csrrwi x7, {c}, 1"),
        (6, 7, 0, "csrrsi x7, {c}, 0"),
        (7, 7, 1, "csrrci x7, {c}, 1"),
        (1, 7, 6, "csrrw x7, {c}, x6"),
    ):
        enc = (0x34E << 20) | (rs1 << 15) | (f3 << 12) | (rdn << 7) | 0x73
        lab = t.label("m")
        t.allow(1)
        t.emit(f"{lab}: " + form.format(c=c("mctrctl")))
        t.outcome(
            ILLEGAL if MUT != "mctrctl_s_access" else "ok",
            lab,
            f"S-mode {form.split()[0]} mctrctl",
            [0, enc],
            origin="S",
        )
    lines = [f"csrr x7, {c(n)}" for n in ("sctrctl", "sctrdepth", "sctrstatus")]
    lines += ["li x7, 0x200", f"csrw {c('siselect')}, x7"] + [f"csrr x7, {c(n)}" for n in L.SIREGS]
    lines += [f".word 0x{L.SCTRCLR:08x}  // sctrclr"]
    for ln in lines:
        lab = t.label("ok")
        t.allow(1)
        t.emit(f"{lab}: {ln}")
        t.outcome("ok", lab, f"S-mode {ln.split('//')[0].strip()}")
    return [t]


@rule
def Smctr_Ssctr_depend() -> list[TestFile]:
    t = s_test(
        "Smctr_Ssctr_depend",
        plan="Ssctr depends on S-mode and Sscsrind: in S-mode, siselect accepts 0x200 and 0x2FF (reads back), and "
        "sireg, sireg2..sireg6 are accessible without a trap for both.",
    )
    for v in (0x200, 0x2FF):
        lab = t.label("sel")
        t.allow(1)
        t.li("x6", v)
        t.emit(f"{lab}: csrw {c('siselect')}, x6")
        t.emit(f"csrr x7, {c('siselect')}")
        for n in L.SIREGS:
            t.emit(f"csrr x8, {c(n)}")
        t.outcome("ok", lab, f"siselect = {v:#x} and sireg*")
        t.check("x7", v, lab, f"siselect = {v:#x} reads back")
    return [t]


# ================================================================ sctrdepth
@rule
def sctrdepth() -> list[TestFile]:
    t = s_test(
        "sctrdepth",
        plan="sctrdepth is 32 bits with DEPTH in bits 2:0 and bits 31:3 WPRI (read-only 0): writing all ones "
        "reads back a value whose bits above 2 are 0 and whose DEPTH is a legal encoding (0..4); writing 0 then "
        "reads a legal DEPTH. On RV64 bits 63:32 read 0.",
    )
    for v, nm in ((-1, "all ones"), (0, "0"), (X(0xFFFFFFF8, 0xFFFFFFFFFFFFFFF8), "all ones but DEPTH")):
        lab = t.label("d")
        t.emit(f"{lab}:", 0)
        if isinstance(v, X):
            t.load("x6", v)
            t.emit(f"csrw {c('sctrdepth')}, x6")
        else:
            wr(t, "sctrdepth", v, reg="x6")
        t.emit(f"csrr x7, {c('sctrdepth')}")
        t.emit("srli x8, x7, 3")
        t.check("x8", 0, lab, f"sctrdepth after writing {nm}: bits above DEPTH read 0")
        t.emit("andi x8, x7, 7")
        t.emit("sltiu x8, x8, 5")
        t.check_bool("x8", lab, f"sctrdepth after writing {nm}: DEPTH is a legal encoding (0..4)")
    return [t]


@rule
def sctrdepth_depth_warl() -> list[TestFile]:
    t = s_test(
        "sctrdepth_depth_warl",
        plan="For each DEPTH encoding 0..7: write it, read back r. r is legal (0..4); writing r again reads r "
        "(a legal value is held); and a supported encoding (r equals what was written) is one of 0..4, so the "
        "reserved encodings 5..7 never read back. At least one of 0..4 is supported.",
    )
    t.li("x1", 0)  # count of supported encodings
    for e in range(8):
        lab = t.label("e")
        t.emit(f"{lab}:", 0)
        L.depth_set(t, e, "x7")
        t.emit("sltiu x8, x7, 5")
        t.check_bool("x8", lab, f"DEPTH written {e}: reads a legal encoding (0..4)")
        t.emit(f"csrw {c('sctrdepth')}, x7  // write the legal value back")
        t.emit(f"csrr x8, {c('sctrdepth')}")
        t.emit("andi x8, x8, 7")
        t.emit("xor x8, x8, x7")
        t.emit("seqz x8, x8")
        t.check_bool("x8", lab, f"DEPTH written {e}: writing the value read back holds it")
        if e < 5:
            t.emit(f"addi x8, x7, {-e}")
            t.emit("seqz x8, x8")
            t.emit("add x1, x1, x8  // supported")
    lab = t.label("any")
    t.emit(f"{lab}:", 0)
    t.emit("snez x1, x1")
    t.check_bool("x1", lab, "at least one DEPTH encoding of 0..4 is supported")
    return [t]


@rule
def sctrdepth_depth() -> list[TestFile]:
    t = s_test(
        "sctrdepth_depth",
        plan="Which DEPTH values are supported is implementation-specific, but the choice must be consistent: "
        "for each encoding e in 0..4, if writing e reads back e, writing another value and then e again reads e "
        "again; if it reads back r != e, a second write of e also reads back a legal value, and r is supported "
        "(writing r reads r).",
    )
    for e in range(5):
        lab = t.label("e")
        t.emit(f"{lab}:", 0)
        L.depth_set(t, e, "x7")
        t.emit(f"addi x1, x7, {-e}")
        t.emit("snez x1, x1  // 1: e is not supported (the WARL result may depend on the previous value)")
        L.depth_set(t, 4 - e if e != 2 else 0, "x8")
        L.depth_set(t, e, "x8")
        t.emit("xor x9, x8, x7")
        t.emit("seqz x9, x9")
        t.emit("sltiu x8, x8, 5  // legal")
        t.emit("and x1, x1, x8")
        t.emit("or x9, x9, x1")
        t.check_bool(
            "x9",
            lab,
            f"DEPTH {e}: if {e} is supported, a second write of {e} after another value reads "
            f"{e} again; otherwise it reads a legal value",
        )
        lab = t.label("r")
        t.emit(f"{lab}:", 0)
        t.emit(f"csrw {c('sctrdepth')}, x7  // the value the first write produced")
        t.emit(f"csrr x8, {c('sctrdepth')}")
        t.emit("andi x8, x8, 7")
        t.emit("xor x8, x8, x7")
        t.emit("seqz x8, x8")
        t.check_bool("x8", lab, f"DEPTH {e}: the value read back after writing {e} is supported (writing it reads it)")
    return [t]


# ================================================================ sctrstatus
def jal_chain(t: TestFile, n: int) -> tuple[str, int]:
    """n back-to-back jal x0, .+4 (taken direct jumps); returns the label of the first and n."""
    base = t.label("chain")
    t.emit(f"{base}:", 0)
    for _ in range(n):
        t.emit("jal x0, .+4")
    return base, n


@rule
def sctrstatus() -> list[TestFile]:
    t = s_test(
        "sctrstatus",
        plan="sctrstatus is 32 bits and updated by hardware only while CTR is active (current mode enabled and not "
        "frozen):\n"
        "1. Active (sctrctl.S=1, FROZEN=0): three S-mode jals advance WRPTR by 3.\n"
        "2. Mode disabled (sctrctl.U=1 only): S-mode jals leave sctrstatus unchanged.\n"
        "3. Frozen (sctrctl.S=1, FROZEN=1 written by software): jals leave sctrstatus unchanged, FROZEN stays 1.\n"
        "4. On RV64, bits 63:32 of sctrstatus read 0 after writing all ones.",
        context=CTX_MEASURE,
    )
    record_s(t, S, lambda: [jal(t, "x0"), jal(t, "x6"), jal(t, "x0")], "active")
    anchor(t)
    wr(t, "sctrctl", U)
    jal_chain(t, 3)
    off(t)
    check_n(t, 0, "sctrctl.U only, S-mode jals")
    anchor(t)
    t.load("x6", lo(FROZEN))
    t.emit(f"csrw {c('sctrstatus')}, x6  // FROZEN = 1, WRPTR = 0")
    wr(t, "sctrctl", S)
    jal_chain(t, 3)
    off(t)
    lab = t.label("fz")
    t.emit(f"{lab}:", 0)
    rd(t, "x7", "sctrstatus")
    t.check("x7", lo(FROZEN), lab, "frozen: sctrstatus unchanged (FROZEN=1, WRPTR=0)")
    with t.rv64_only():
        lab = t.label("hi")
        t.emit(f"{lab}:", 0)
        t.emit("li x6, -1")
        t.emit(f"csrw {c('sctrstatus')}, x6")
        rd(t, "x7", "sctrstatus")
        t.emit("srli x7, x7, 32")
        t.check("x7", 0, lab, "sctrstatus bits 63:32 read 0 (32-bit register)")
    t.emit(f"csrw {c('sctrstatus')}, x0")
    return [t]


@rule
def Ssctr_sctrstatus_acc() -> list[TestFile]:
    t = s_test(
        "Ssctr_sctrstatus_acc",
        plan="With the custom bits of sctrctl at 0, the undefined bits of sctrstatus (30:8, and 63:32 on RV64) are "
        "read-only 0: writing all ones, and writing only those bits, reads 0 in them.",
    )
    wr(t, "sctrctl", 0)
    for v, nm in ((-1, "all ones"), (X(0x7FFFFF00, 0xFFFFFFFF7FFFFF00), "only the undefined bits")):
        lab = t.label("w")
        t.emit(f"{lab}:", 0)
        if isinstance(v, X):
            t.load("x6", v)
            t.emit(f"csrw {c('sctrstatus')}, x6")
        else:
            t.emit("li x6, -1")
            t.emit(f"csrw {c('sctrstatus')}, x6")
        rd(t, "x7", "sctrstatus")
        t.load("x6", X(0x7FFFFF00, 0xFFFFFFFF7FFFFF00), "undefined bits")
        t.emit("and x8, x7, x6")
        t.check("x8", 0, lab, f"sctrstatus after writing {nm}: undefined bits read 0")
        if not isinstance(v, X):
            t.load("x6", lo(FROZEN))
            t.emit("and x8, x7, x6")
            t.check("x8", lo(FROZEN), lab, "sctrstatus all ones: FROZEN reads 1")
    t.emit(f"csrw {c('sctrstatus')}, x0")
    return [t]


@rule
def sctrstatus_wrptr() -> list[TestFile]:
    t = s_test(
        "sctrstatus_wrptr",
        plan="With the smallest supported depth D (DEPTH written 0, 1, ... until one reads back as written):\n"
        "1. Writing WRPTR = 0xFF reads back a value with no bits above D-1 (read-only 0) - the bits D-1 needs "
        "read back 1.\n"
        "2. Writing WRPTR = D-1 holds it; one recorded jal wraps WRPTR to 0, and logical entry 0 is that jal "
        "(physical entry D-1).\n"
        "3. From WRPTR = 5, two jals give WRPTR = 7 (incremented after each record).\n"
        "4. After changing DEPTH to the largest supported value, WRPTR holds a legal value (< new depth).\n"
        "RASEMU decrements are tested in ctrctl_rasemu_op.",
        context=CTX_MEASURE,
    )
    L.depth_pick(t, largest=False, reg="x1")
    L.depth_entries(t, "x1", "x8")
    t.emit("addi x8, x8, -1  // x8 = D-1")
    lab = t.label("ff")
    t.emit(f"{lab}:", 0)
    t.li("x6", 0xFF)
    t.emit(f"csrw {c('sctrstatus')}, x6")
    rd(t, "x7", "sctrstatus")
    t.emit("xor x7, x7, x8")
    t.emit("seqz x7, x7")
    t.check_bool("x7", lab, "WRPTR = 0xFF reads D-1: bits above D-1 are read-only 0, the others hold 1")
    lab = t.label("wrap")
    t.emit(f"{lab}:", 0)
    sctrclr(t)
    t.emit(f"csrw {c('sctrstatus')}, x8  // WRPTR = D-1")
    rd(t, "x7", "sctrstatus")
    t.emit("xor x7, x7, x8")
    t.emit("seqz x7, x7")
    t.check_bool("x7", lab, "WRPTR = D-1 is held")
    wr(t, "sctrctl", S)
    j = jal(t, "x0")
    off(t)
    check_n(t, 0 if MUT != "wrptr_no_wrap" else X(16, 16), "one jal from WRPTR = D-1 wraps to 0")
    check_xfer(t, j, "after the wrap", logical=0)
    lab = t.label("inc")
    t.emit(f"{lab}:", 0)
    t.li("x6", 5)
    t.emit(f"csrw {c('sctrstatus')}, x6  // WRPTR = 5")
    wr(t, "sctrctl", S)
    jal(t, "x0")
    jal(t, "x0")
    off(t)
    check_n(t, 7, "two jals from WRPTR = 5")
    L.depth_pick(t, largest=True, reg="x1")
    L.depth_entries(t, "x1", "x8")
    lab = t.label("dch")
    t.emit(f"{lab}:", 0)
    L.nrec(t, "x7")
    t.emit("sltu x7, x7, x8")
    t.check_bool("x7", lab, "after a DEPTH change, WRPTR is below the new depth")
    t.emit(f"csrw {c('sctrstatus')}, x0")
    return [t]


@rule
def sctrstatus_frozen_op() -> list[TestFile]:
    t = s_test(
        "sctrstatus_frozen_op",
        plan="FROZEN is written by software and inhibits recording:\n"
        "1. Writing FROZEN=1 reads back 1; S-mode jal, taken branch and sret are not recorded and WRPTR does not "
        "move (sctrctl.S=1).\n"
        "2. Clearing FROZEN restores recording: the next jal is recorded.\n"
        "3. With sctrctl.U=1 (S=0), FROZEN=1 also inhibits a U-mode jal.",
        context=CTX_MEASURE,
    )
    for mode in ("S", "U"):
        anchor(t)
        lab = t.label("set")
        t.emit(f"{lab}:", 0)
        t.load("x6", lo(FROZEN))
        t.emit(f"csrw {c('sctrstatus')}, x6  // FROZEN = 1")
        rd(t, "x7", "sctrstatus")
        t.check("x7", lo(FROZEN), lab, "FROZEN = 1 reads back")
        if mode == "S":
            wr(t, "sctrctl", S)
            jal(t, "x0")
            L.branch(t, "beq", 3, 3)
            L.sret_s(t)
        else:
            wr(t, "sctrctl", U)
            win(t, "U", lambda: [jal(t, "x6")], desc="frozen")
        off(t)
        lab = t.label("fz")
        t.emit(f"{lab}:", 0)
        rd(t, "x7", "sctrstatus")
        exp = lo(FROZEN) if MUT != "frozen_ignored" else lo(FROZEN | 3)
        t.check("x7", exp, lab, f"frozen, {mode}-mode transfers: sctrstatus unchanged (no record, FROZEN kept)")
    record_s(t, S, lambda: [jal(t, "x0")], "FROZEN cleared again")
    return [t]


@rule
def sctrstatus_frozen_inhibit() -> list[TestFile]:
    t = s_test(
        "sctrstatus_frozen_inhibit",
        plan="FROZEN=1 inhibits recording of every transfer kind: with sctrctl.S=1 (and NTBREN set if implemented), "
        "FROZEN=1 then an S-mode jal, jalr, taken branch, not-taken branch, sret and an S-mode ebreak (an "
        "S-to-S exception, BPFRZ=0) leave WRPTR at 0 and logical entry 0 empty (ctrsource 0).",
        context=CTX_MEASURE,
    )
    anchor(t)
    t.emit("li x6, 0x200")
    t.emit(f"csrw {c('siselect')}, x6")
    t.la("x6", "ctr_sentinel")
    t.emit(f"csrw {c('sireg')}, x6  // logical entry 0 ctrsource = a software value")
    t.load("x6", lo(FROZEN))
    t.emit(f"csrw {c('sctrstatus')}, x6  // FROZEN = 1")
    L.probe_ctl(t, "x8", L.NTBREN)
    t.emit("ori x8, x8, 2  // S")
    t.emit(f"csrw {c('sctrctl')}, x8")
    jal(t, "x0")
    L.jalr(t, "x0", "x6")
    L.branch(t, "bne", 1, 2)
    L.nt_branch(t, "beq", 1, 2)
    L.sret_s(t)
    L.ebreak_win(t, "S", "frozen")
    off(t)
    L.nt_fixup(t)
    lab = t.label("fz")
    t.emit(f"{lab}:", 0)
    rd(t, "x7", "sctrstatus")
    t.check("x7", lo(FROZEN), lab, "frozen: WRPTR stays 0, FROZEN stays 1")
    lab = t.label("sw")
    t.emit(f"{lab}:", 0)
    t.emit("li x6, 0x200")
    t.emit(f"csrw {c('siselect')}, x6")
    t.emit(f"csrr x7, {c('sireg')}")
    t.check("x7", "ctr_sentinel", lab, "frozen: the software-written ctrsource of entry 0 is kept")
    t.emit(f"csrw {c('sctrstatus')}, x0")
    t.extra_data.append(".p2align 2\nctr_sentinel: .word 0")
    return [t]


@rule
def ctr_behavior_criteria_not_frozen() -> list[TestFile]:
    t = s_test(
        "ctr_behavior_criteria_not_frozen",
        plan="A transfer is qualified only while FROZEN=0. Sequence with sctrctl.S=1: jal A (recorded), set FROZEN, "
        "jal B (not recorded), clear FROZEN, jal C (recorded): exactly A then C are logical entries 1 and 0. "
        "Also in U-mode with sctrctl.U=1: a U-mode jal with FROZEN=1 is not recorded and one with FROZEN=0 is.",
        context=CTX_MEASURE,
    )
    anchor(t)
    wr(t, "sctrctl", S)
    a = jal(t, "x0")
    t.load("x6", lo(FROZEN))
    t.emit(f"csrw {c('sctrstatus')}, x6  // FROZEN = 1 (WRPTR = 0 written too, so read A at 0 below)")
    jal(t, "x0")
    t.li("x6", 1)
    t.emit(f"csrw {c('sctrstatus')}, x6  // FROZEN = 0, WRPTR = 1 (as after A)")
    cc = jal(t, "x0")
    off(t)
    rec = [a, cc] if MUT != "frozen_ignored" else [a, a, cc]
    check_n(t, len(rec), "jal, frozen jal, jal")
    for i, x in enumerate(reversed(rec)):
        check_xfer(t, x, "not frozen", logical=i)
    for fz in (True, False):
        anchor(t)
        if fz:
            t.load("x6", lo(FROZEN))
            t.emit(f"csrw {c('sctrstatus')}, x6  // FROZEN = 1")
        wr(t, "sctrctl", U)
        (j,), _, _ = win(t, "U", lambda: [jal(t, "x6")], desc=f"FROZEN={int(fz)}")
        off(t)
        lab = t.label("u")
        t.emit(f"{lab}:", 0)
        rd(t, "x7", "sctrstatus")
        t.check("x7", lo(FROZEN) if fz else 1, lab, f"U-mode jal with FROZEN={int(fz)}: sctrstatus")
        if not fz:
            check_xfer(t, j, "U-mode, not frozen", logical=0)
    t.emit(f"csrw {c('sctrstatus')}, x0")
    return [t]


# ================================================================ entry registers
@rule
def siselect_acc_op() -> list[TestFile]:
    t = s_test(
        "siselect_acc_op",
        plan="With siselect = 0x200 + i (i = 0, 1, 7 and 15, inside the minimum depth 16, selected with DEPTH "
        "written 0):\n"
        "1. Distinct software values written to sireg, sireg2, sireg3 land in ctrsource, ctrtarget and ctrdata of "
        "entry i: ctrsource and ctrtarget hold the valid pcs written (ctrtarget MISP may read 0); ctrdata reads "
        "TYPE 0 or 5 for a written 5.\n"
        "2. Each entry keeps its own values (writing entry 1 does not change entry 0).\n"
        "3. sireg4, sireg5 and sireg6 read 0, and writing all ones to them changes nothing (they still read 0, "
        "and the entry's other registers are unchanged).\n"
        "4. A recorded jal appears through the same registers (logical entry 0).",
        context=CTX_MEASURE,
    )
    L.depth_pick(t, largest=False, reg="x9")
    wr(t, "sctrctl", 0)
    sctrclr(t)
    pcs = {0: ("ctr_pa", "ctr_pb"), 1: ("ctr_pb", "ctr_pa"), 7: ("ctr_pc", "ctr_pa"), 15: ("ctr_pa", "ctr_pc")}
    for i, (sv, tv) in pcs.items():
        t.li("x6", 0x200 + i)
        t.emit(f"csrw {c('siselect')}, x6")
        t.la("x6", sv)
        t.emit("ori x6, x6, 1")
        t.emit(f"csrw {c('sireg')}, x6  // ctrsource = {sv} | V")
        t.la("x6", tv)
        t.emit(f"csrw {c('sireg2')}, x6  // ctrtarget = {tv}")
        t.li("x6", 5)
        t.emit(f"csrw {c('sireg3')}, x6  // ctrdata.TYPE = 5")
        t.emit("li x6, -1")
        for n in ("sireg4", "sireg5", "sireg6"):
            t.emit(f"csrw {c(n)}, x6  // {n}: read-only 0")
    for i, (sv, tv) in pcs.items():
        lab = t.label("e")
        t.emit(f"{lab}:", 0)
        t.li("x6", 0x200 + i)
        t.emit(f"csrw {c('siselect')}, x6")
        t.emit(f"csrr x7, {c('sireg')}")
        t.check("x7", f"{sv}+1", lab, f"entry {i}: sireg reads the ctrsource written")
        t.emit(f"csrr x7, {c('sireg2')}")
        t.check("x7", tv, lab, f"entry {i}: sireg2 reads the ctrtarget written")
        t.emit(f"csrr x7, {c('sireg3')}")
        t.check_masked("x7", 0xF, [0, 5], lab, f"entry {i}: sireg3 reads ctrdata.TYPE written (5) or 0")
        for n in ("sireg4", "sireg5", "sireg6"):
            t.emit(f"csrr x7, {c(n)}")
            t.check("x7", 0 if MUT != "sireg4_rw" else -1, lab, f"entry {i}: {n} reads 0 after writing all ones")
    record_s(t, S, lambda: [jal(t, "x0")], "a recorded jal through sireg*")
    t.extra_data.append(".p2align 2\nctr_pa: .word 0\nctr_pb: .word 0\nctr_pc: .word 0")
    return [t]


def pc_hold(t: TestFile, reg_name: str, desc: str, vbit: bool) -> None:
    """Valid pcs written through reg_name hold exactly (V/MISP bit 0 written as given)."""
    t.li("x6", 0x200)
    t.emit(f"csrw {c('siselect')}, x6")
    for sym in ("ctr_pa", "ctr_pc", "ctr_far"):
        for b in (0, 1):
            lab = t.label("pc")
            t.emit(f"{lab}:", 0)
            t.la("x6", sym)
            if b:
                t.emit("ori x6, x6, 1")
            t.emit(f"csrw {c(reg_name)}, x6")
            t.emit(f"csrr x7, {c(reg_name)}")
            exp = f"{sym}+{b}" if (vbit or not b) else [sym, f"{sym}+1"]
            t.check("x7", exp, lab, f"{desc}: writing the pc of {sym} with bit 0 = {b} reads it back")


@rule
def Ssctr_ctrsource_sz_acc_op() -> list[TestFile]:
    t = s_test(
        "Ssctr_ctrsource_sz_acc_op",
        plan="ctrsource holds every valid pc: writing the pcs of several code and data labels (including a "
        "16-byte-aligned data word), with V = 0 and V = 1, through sireg reads them back exactly. A recorded "
        "jal's ctrsource is its pc | V (zero-extension for XLEN < MXLEN is not reachable: the tests run with "
        "XLEN = MXLEN).",
        context=CTX_MEASURE,
    )
    wr(t, "sctrctl", 0)
    pc_hold(t, "sireg", "ctrsource", vbit=True)
    record_s(t, S, lambda: [jal(t, "x0")], "recorded jal")
    t.extra_data.append(".p2align 2\nctr_pa: .word 0\nctr_pc: .word 0\n.p2align 4\nctr_far: .word 0")
    return [t]


@rule
def ctrtarget_sz_acc() -> list[TestFile]:
    t = s_test(
        "ctrtarget_sz_acc",
        plan="ctrtarget holds every valid pc: writing the pcs of code and data labels through sireg2 reads them "
        "back (with bit 0 = 1 written, MISP may read 0 or 1). A recorded jal's ctrtarget is its target pc.",
        context=CTX_MEASURE,
    )
    wr(t, "sctrctl", 0)
    pc_hold(t, "sireg2", "ctrtarget", vbit=False)
    record_s(t, S, lambda: [jal(t, "x0")], "recorded jal")
    t.extra_data.append(".p2align 2\nctr_pa: .word 0\nctr_pc: .word 0\n.p2align 4\nctr_far: .word 0")
    return [t]


@rule
def ctrdata_sz_acc() -> list[TestFile]:
    t = s_test(
        "ctrdata_sz_acc",
        plan="ctrdata is implemented (64 bits, fields optional, unimplemented fields read-only 0): through sireg3, "
        "writing all ones reads back only TYPE, CCV and CC bits; writing 0 reads 0 (SCTRCLR zeroes entries, so "
        "0 is a legal value); writing the all-ones readback again reads it back. On RV64 bits 63:32 read 0.",
    )
    wr(t, "sctrctl", 0)
    t.li("x6", 0x200)
    t.emit(f"csrw {c('siselect')}, x6")
    lab = t.label("ones")
    t.emit(f"{lab}:", 0)
    t.emit("li x6, -1")
    t.emit(f"csrw {c('sireg3')}, x6")
    t.emit(f"csrr x8, {c('sireg3')}")
    t.check_masked("x8", CTRDATA_WPRI, 0, lab, "ctrdata all ones: only TYPE, CCV and CC bits read 1")
    t.emit(f"csrw {c('sireg3')}, x0")
    t.emit(f"csrr x7, {c('sireg3')}")
    t.check("x7", 0, lab, "ctrdata = 0 reads 0")
    t.emit(f"csrw {c('sireg3')}, x8")
    t.emit(f"csrr x7, {c('sireg3')}")
    t.emit("xor x7, x7, x8")
    t.emit("seqz x7, x7")
    t.check_bool("x7", lab, "ctrdata: the all-ones readback written again reads back")
    return [t]


@rule
def ctrdata_undef() -> list[TestFile]:
    t = s_test(
        "ctrdata_undef",
        plan="With the sctrctl custom bits 0, the undefined ctrdata bits (14:4, and 63:32 on RV64) are read-only 0: "
        "writing only those bits through sireg3 reads 0, and records of a jal, a taken branch, an sret and an "
        "S-mode exception (first record after the anchor) have them 0.",
        context=CTX_MEASURE,
    )
    wr(t, "sctrctl", 0)
    t.li("x6", 0x200)
    t.emit(f"csrw {c('siselect')}, x6")
    lab = t.label("w")
    t.emit(f"{lab}:", 0)
    t.load("x6", CTRDATA_WPRI)
    t.emit(f"csrw {c('sireg3')}, x6")
    t.emit(f"csrr x7, {c('sireg3')}")
    t.check(
        "x7", 0 if MUT != "ctrdata_wpri_rw" else CTRDATA_WPRI, lab, "ctrdata: writing only the undefined bits reads 0"
    )
    record_s(t, S, lambda: [jal(t, "x6"), L.branch(t, "blt", -1, 1), L.sret_s(t)], "records")
    L.deep(t)
    anchor(t)
    wr(t, "sctrctl", S)
    L.ebreak_win(t, "S", "S-mode exception", more=[f"csrw {c('sctrctl')}, x0"])
    L.deep_checks(
        t,
        lambda: [L.check_n_ge(t, 1, "S-mode ebreak"), check_entry(t, "S-mode ebreak", typ=L.T_EXC, k=0)],
        "S-mode ebreak",
    )
    return [t]


@rule
def ctrsource_ctrtarget_ctrdata_vbit() -> list[TestFile]:
    t = s_test(
        "ctrsource_ctrtarget_ctrdata_vbit",
        plan="1. After SCTRCLR every entry has V=0 (ctrsource reads 0).\n"
        "2. A recorded jal sets V=1 in the entry it lands in (logical 0) while older empty entries keep V=0 "
        "(logical 1).\n"
        "3. Software can clear V (write ctrsource with bit 0 = 0) and set it again.",
        context=CTX_MEASURE,
    )
    anchor(t)
    for i in (0, 1, 15):
        lab = t.label("clr")
        t.emit(f"{lab}:", 0)
        L.select(t, logical=i)
        t.emit(f"csrr x7, {c('sireg')}")
        t.check("x7", 0, lab, f"after SCTRCLR, logical entry {i} has V=0 (ctrsource 0)")
    wr(t, "sctrctl", S)
    j = jal(t, "x0")
    off(t)
    check_xfer(t, j, "recorded", logical=0)
    lab = t.label("old")
    t.emit(f"{lab}:", 0)
    L.select(t, logical=1)
    t.emit(f"csrr x7, {c('sireg')}")
    t.emit("andi x7, x7, 1")
    t.check("x7", 0, lab, "the older empty entry (logical 1) still has V=0")
    lab = t.label("sw")
    t.emit(f"{lab}:", 0)
    L.select(t, logical=0)
    t.la("x6", j.src)
    t.emit(f"csrw {c('sireg')}, x6  // V = 0")
    t.emit(f"csrr x7, {c('sireg')}")
    t.check("x7", j.src, lab, "software clears ctrsource.V")
    t.emit("ori x6, x6, 1")
    t.emit(f"csrw {c('sireg')}, x6  // V = 1")
    t.emit(f"csrr x7, {c('sireg')}")
    t.check("x7", f"{j.src}+1", lab, "software sets ctrsource.V")
    return [t]


@rule
def ctr_validbit() -> list[TestFile]:
    t = s_test(
        "ctr_validbit",
        plan="A record sets V=1 and updates every implemented field, overwriting what software left there: with "
        "WRPTR = 0, physical entry 0 (logical D-1 for the smallest depth D) is filled by software with "
        "ctrsource = 0 (V=0), ctrtarget = an unrelated pc | 1, ctrdata = all ones. One recorded jal x0 then "
        "lands there: ctrsource = pc | 1, ctrtarget = its target (MISP free), ctrdata.TYPE = 11 or 0 (not the "
        "stale 15), WPRI 0.",
        context=CTX_MEASURE,
    )
    L.depth_pick(t, largest=False, reg="x1")
    L.depth_entries(t, "x1", "x8")
    wr(t, "sctrctl", 0)
    anchor(t)
    t.emit("addi x8, x8, 0x1ff  // 0x200 + D-1: physical entry 0 while WRPTR = 0")
    t.emit(f"csrw {c('siselect')}, x8")
    t.emit(f"csrw {c('sireg')}, x0")
    t.la("x6", "ctr_pa")
    t.emit("ori x6, x6, 1")
    t.emit(f"csrw {c('sireg2')}, x6")
    t.emit("li x6, -1")
    t.emit(f"csrw {c('sireg3')}, x6")
    wr(t, "sctrctl", S)
    j = jal(t, "x0")
    off(t)
    check_n(t, 1, "one jal")
    check_xfer(t, j, "the record replaces the software contents", logical=0)
    t.extra_data.append(".p2align 2\nctr_pa: .word 0")
    return [t]


@rule
def ctrsource_op() -> list[TestFile]:
    t = s_test(
        "ctrsource_op",
        plan="ctrsource holds the pc of the recorded transfer instruction, or the epc of a recorded trap:\n"
        "1. jal, jalr, a taken bge and an sret in S-mode: ctrsource = their pcs | V.\n"
        "2. An S-mode ebreak (S-to-S exception, recorded first after the anchor): ctrsource = the ebreak pc | V "
        "(the logged sepc).\n"
        "3. A U-mode ebreak with only sctrctl.U and STE (external trap): ctrsource = the U-mode ebreak pc | V.",
        context=CTX_MEASURE,
    )
    record_s(t, S, lambda: [jal(t, "x1"), L.jalr(t, "x0", "x7"), L.branch(t, "bge", 5, -5), L.sret_s(t)], "S-mode")
    L.deep(t)
    anchor(t)
    wr(t, "sctrctl", S)
    eb, _ = L.ebreak_win(t, "S", "S-mode exception", more=[f"csrw {c('sctrctl')}, x0"])
    L.deep_checks(
        t, lambda: [L.check_n_ge(t, 1, "S-mode ebreak"), check_entry(t, "S-mode ebreak", src=eb, k=0)], "S-mode ebreak"
    )
    anchor(t)
    t.li("x6", U | STE)
    t.emit(f"csrw {c('sctrctl')}, x6  // U, STE")
    t.emit(f"csrr x7, {c('sctrctl')}")
    t.emit(f"andi x7, x7, {STE}  // STE implemented?")

    def ext() -> None:
        eb, _ = L.ebreak_win(t, "U", "U-mode external trap")
        off(t)
        L.check_n_ge(t, 1, "U-mode ebreak, STE=1")
        check_entry(t, "U-mode ebreak with STE (external trap)", src=eb, k=0)

    def noext() -> None:
        off(t)

    t.either("x7", ext, noext)
    return [t]


@rule
def ctrtarget_op() -> list[TestFile]:
    t = s_test(
        "ctrtarget_op",
        plan="ctrtarget holds the destination pc: jal (forward target), jalr with a nonzero offset, "
        "a taken bltu, and an sret (target = sepc); and for an S-mode exception the trap handler (stvec base).",
        context=CTX_MEASURE,
    )

    def body() -> list[Xfer]:
        xs = [jal(t, "x0")]
        # backward jal: jump forward to B, B jumps back to A, A jumps forward to C
        a, b, cc = t.label("bwA"), t.label("bwB"), t.label("bwC")
        t.emit(f"{a}_0: jal x0, {b}")
        t.emit(f"{a}: jal x0, {cc}")
        t.emit(f"{b}: jal x0, {a}")
        t.emit(f"{cc}:", 0)
        xs += [
            Xfer(f"{a}_0", b, L.T_DIRJMP, "jal forward"),
            Xfer(b, a, L.T_DIRJMP, "jal backward"),
            Xfer(a, cc, L.T_DIRJMP, "jal forward again"),
        ]
        src, tgt = t.label("jo"), t.label("jot")
        t.la("x7", f"{tgt}-16")
        t.emit(f"{src}: jalr x0, 16(x7)")
        t.emit(".word 0")
        t.emit(f"{tgt}:", 0)
        xs.append(Xfer(src, tgt, L.T_INDJMP, "jalr x0, 16(x7)"))
        xs.append(L.branch(t, "bltu", 1, -1))
        xs.append(L.sret_s(t))
        return xs

    record_s(t, S, body, "targets")
    L.deep(t)
    anchor(t)
    wr(t, "sctrctl", S)
    L.ebreak_win(t, "S", "S-mode exception", more=[f"csrw {c('sctrctl')}, x0"])
    L.deep_checks(
        t,
        lambda: [
            L.check_n_ge(t, 1, "S-mode ebreak"),
            check_entry(t, "S-mode ebreak", k=0),
            L.check_tgt_handler(t, "S-mode ebreak"),
        ],
        "S-mode ebreak",
    )
    return [t]


# ================================================================ SCTRCLR
def fill(t: TestFile, logicals: list[int]) -> None:
    """Write nonzero values to ctrsource, ctrtarget and ctrdata of the given logical entries."""
    for i in logicals:
        t.li("x6", 0x200 + i)
        t.emit(f"csrw {c('siselect')}, x6")
        t.la("x6", "ctr_pa")
        t.emit("ori x6, x6, 1")
        t.emit(f"csrw {c('sireg')}, x6")
        t.emit(f"csrw {c('sireg2')}, x6")
        t.emit("li x6, -1")
        t.emit(f"csrw {c('sireg3')}, x6")


def fill_rt(t: TestFile, dreg: str) -> None:
    """Fill logical entry depth-1 (depth in dreg)."""
    t.emit(f"addi x6, {dreg}, 0x1ff")
    t.emit(f"csrw {c('siselect')}, x6")
    t.la("x6", "ctr_pa")
    t.emit("ori x6, x6, 1")
    t.emit(f"csrw {c('sireg')}, x6")
    t.emit(f"csrw {c('sireg2')}, x6")
    t.emit("li x6, -1")
    t.emit(f"csrw {c('sireg3')}, x6")


def check_zero_rt(t: TestFile, dreg: str, desc: str) -> None:
    lab = t.label("z")
    t.emit(f"{lab}:", 0)
    t.emit(f"addi x6, {dreg}, 0x1ff")
    t.emit(f"csrw {c('siselect')}, x6")
    L.entry(t)
    t.emit("or x6, x6, x7")
    t.emit("or x6, x6, x8")
    t.check("x6", 0, lab, f"{desc}: logical entry depth-1 reads 0")


@rule
def sctrclr_zero_entries_op() -> list[TestFile]:
    t = s_test(
        "sctrclr_zero_entries_op",
        plan="For the smallest and the largest supported depth D (DEPTH written 0, 1, ... and 4, 3, ... until one reads back as written): software fills logical "
        "entries 0, 1 and D-1 (ctrsource, ctrtarget, ctrdata nonzero), and a recorded jal adds one more; SCTRCLR "
        "then makes all of them read 0 in ctrsource, ctrtarget and ctrdata. Entries beyond a later depth increase "
        "are UNSPECIFIED (sctrdepth_depth_entries_op), so each depth is cleared and checked on its own.",
    )
    for enc in (0, 4):
        wr(t, "sctrctl", 0)
        L.depth_pick(t, largest=enc == 4, reg="x1")
        L.depth_entries(t, "x1", "x1")
        fill(t, [0, 1])
        fill_rt(t, "x1")
        wr(t, "sctrctl", S)
        jal(t, "x0")
        off(t)
        if MUT != "sctrclr_noop":
            sctrclr(t)
        for i in (0, 1, 2):
            L.check_empty(t, i, f"DEPTH written {enc}, after SCTRCLR")
        check_zero_rt(t, "x1", f"DEPTH written {enc}, after SCTRCLR")
    t.extra_data.append(".p2align 2\nctr_pa: .word 0")
    return [t]


@rule
def sctrclr_acc() -> list[TestFile]:
    t = s_test(
        "sctrclr_acc",
        plan="1. After SCTRCLR, reads of ctrsource, ctrtarget and ctrdata return 0 for entries that held records "
        "(logical 0..2) until the next qualified transfer; transfers while CTR is inactive (sctrctl.U only, "
        "S-mode jal) do not end that.\n"
        "2. The first record after SCTRCLR has ctrdata.CCV = 0; older entries still read 0.\n"
        "3. SCTRCLR while recording is active (sctrctl.S=1): the record before it is gone, the one after is "
        "logical 0 with CCV = 0.",
        context=CTX_MEASURE,
    )
    anchor(t)
    wr(t, "sctrctl", S)
    jal(t, "x0")
    jal(t, "x0")
    jal(t, "x0")
    off(t)
    sctrclr(t)
    for i in (0, 1, 2):
        L.check_empty(t, i, "after SCTRCLR")
    wr(t, "sctrctl", U)
    jal(t, "x0", "S-mode jal while S is disabled")
    off(t)
    for i in (0, 1):
        L.check_empty(t, i, "after SCTRCLR and an unqualified S-mode jal")
    for active in (False, True):
        if not active:
            sctrclr(t)
            wr(t, "sctrctl", S)
        else:
            wr(t, "sctrctl", S)
            jal(t, "x0")
            sctrclr(t)
        j = jal(t, "x0")
        off(t)
        d = "SCTRCLR while active" if active else "first record after SCTRCLR"
        lab = check_entry(t, d, src=j.src, tgt=j.tgt, typ=L.T_DIRJMP, logical=0)
        t.emit("srli x8, x8, 15")
        t.emit("andi x8, x8, 1")
        t.check("x8", 0 if MUT != "sctrclr_keeps_ccv" else 1, lab, f"{d}: ctrdata.CCV = 0")
        L.check_empty(t, 1, f"{d}: the older entry")
    return [t]


@rule
def sctrclr_exceptions() -> list[TestFile]:
    t = s_test(
        "sctrclr_exceptions",
        plan="SCTRCLR raises illegal-instruction in U-mode (with sctrctl.U and S set, mstateen0.CTR=1), and "
        "virtual-instruction in VU-mode (H; vsctrctl.U and S set, hstateen0.CTR=1 when Ssstateen); xtval is 0 or the instruction. It "
        "executes without a trap in S-mode and in VS-mode (VS: clears the shared entries).",
    )
    enc = f".word 0x{L.SCTRCLR:08x}  // sctrclr"
    wr(t, "sctrctl", U | S)
    win(t, "U", lambda: t.emit(enc), ILLEGAL if MUT != "sctrclr_u_ok" else "ok", "SCTRCLR", [0, L.SCTRCLR])
    off(t)
    win(t, "S", lambda: t.emit(enc), "ok", "SCTRCLR")
    with t.only_if(H):
        wr(t, "vsctrctl", U | S)
        win(
            t, "VU", lambda: t.emit(enc), VIRTUAL if MUT != "sctrclr_vu_illegal" else ILLEGAL, "SCTRCLR", [0, L.SCTRCLR]
        )
        off(t, "vsctrctl")
        fill(t, [0])
        win(t, "VS", lambda: t.emit(enc), "ok", "SCTRCLR")
        L.check_empty(t, 0, "after a VS-mode SCTRCLR")
    t.extra_data.append(".p2align 2\nctr_pa: .word 0")
    return [t]


@rule
def sctrclr_zero_cycle_counter_op() -> list[TestFile]:
    t = s_test(
        "sctrclr_zero_cycle_counter_op",
        plan="SCTRCLR zeroes the cycle counter and CCV: with sctrctl.S, record A, then 300 straight-line nops while "
        "recording (the counter runs), then SCTRCLR, then record B: B has CCV = 0 (its CC is then not "
        "constrained). The same sequence without SCTRCLR (ctr_ccounter_inc) leaves CCV free.",
        context=CTX_MEASURE,
    )
    anchor(t)
    wr(t, "sctrctl", S)
    jal(t, "x0", "A")
    L.delay(t, 300)
    sctrclr(t)
    j = jal(t, "x0", "B")
    off(t)
    lab = check_entry(t, "first record after SCTRCLR", src=j.src, tgt=j.tgt, logical=0)
    t.emit("srli x8, x8, 15")
    t.emit("andi x8, x8, 1")
    t.check("x8", 0 if MUT != "sctrclr_keeps_ccv" else 1, lab, "first record after SCTRCLR: CCV = 0")
    return [t]


# ================================================================ depth and the stack
@rule
def ctr_stack() -> list[TestFile]:
    t = s_test(
        "ctr_stack",
        plan="1. Three S-mode jals A, B, C: C is logical entry 0, B entry 1, A entry 2 (younger entries push older "
        "ones down).\n"
        "2. With the smallest supported depth D (DEPTH written 0, 1, ... until one reads back), 257 back-to-back jal x0 (more than any depth): "
        "WRPTR = 257 mod D, logical entry 0 is the last jump, logical entry D-1 is jump 257-D (computed at run "
        "time), and logical entry D (when D < 256) reads 0: the oldest records were lost.",
        context=CTX_MEASURE,
    )
    record_s(t, S, lambda: [jal(t, "x0"), jal(t, "x6"), jal(t, "x0")], "three jals")
    L.depth_pick(t, largest=False, reg="x1")
    L.depth_entries(t, "x1", "x1")
    anchor(t)
    wr(t, "sctrctl", S)
    base, _n = jal_chain(t, 257)
    off(t)
    lab = t.label("wr")
    t.emit(f"{lab}:", 0)
    L.nrec(t, "x7")
    t.emit("addi x8, x1, -1")
    t.li("x9", 257)
    t.emit("and x8, x8, x9  // 257 mod D")
    t.emit("xor x7, x7, x8")
    t.emit("seqz x7, x7")
    t.check_bool("x7", lab, "257 jals: WRPTR = 257 mod D")
    check_entry(t, "257 jals", src=f"{base}+{4 * 256}", tgt=f"{base}+{4 * 257}", typ=L.T_DIRJMP, logical=0)
    lab = t.label("old")
    t.emit(f"{lab}:", 0)
    t.emit("addi x6, x1, 0x1ff")
    t.emit(f"csrw {c('siselect')}, x6  // logical D-1")
    t.emit(f"csrr x7, {c('sireg')}")
    t.la("x8", base)
    t.li("x9", 257 if MUT != "stack_keeps_oldest" else 256)
    t.emit("sub x9, x9, x1  // 257-D")
    t.emit("slli x9, x9, 2")
    t.emit("add x8, x8, x9")
    t.emit("ori x8, x8, 1")
    t.emit("xor x7, x7, x8")
    t.emit("seqz x7, x7")
    t.check_bool("x7", lab, "257 jals: logical entry D-1 is jump number 257-D (the oldest kept)")
    lab = t.label("lost")
    t.emit(f"{lab}:", 0)
    t.emit("li x6, 256")
    t.emit("sltu x7, x1, x6  // D < 256")
    t.emit("addi x6, x1, 0x200")
    t.emit("neg x9, x7")
    t.emit("and x6, x6, x9")
    t.emit("not x9, x9")
    t.emit("andi x9, x9, 0x200")
    t.emit("or x6, x6, x9  // logical D, or logical 0 when D = 256 (not checked)")
    t.emit(f"csrw {c('siselect')}, x6")
    t.emit(f"csrr x8, {c('sireg')}")
    t.emit("snez x8, x8")
    t.emit("and x8, x8, x7  // nonzero only when D < 256 and entry D is not 0")
    t.check("x8", 0, lab, "257 jals: logical entry D reads 0 (D < 256)")
    return [t]


@rule
def ctr_depth() -> list[TestFile]:
    t = s_test(
        "ctr_depth",
        plan="The buffer holds exactly the selected number of records. For the smallest and the largest supported "
        "DEPTH (DEPTH written 0, 1, ... and 4, 3, ... until one reads back as written; D = 16 << DEPTH): 257 jal x0 make logical entries 0 and D-1 valid "
        "(V=1) and, for D < 256, entry D read 0; the implementation maximum is at least the selected depth.",
        context=CTX_MEASURE,
    )
    for enc in (0, 4):
        L.depth_pick(t, largest=enc == 4, reg="x1")
        L.depth_entries(t, "x1", "x1")
        anchor(t)
        wr(t, "sctrctl", S)
        jal_chain(t, 257)
        off(t)
        lab = t.label("v")
        t.emit(f"{lab}:", 0)
        L.select(t, logical=0)
        t.emit(f"csrr x7, {c('sireg')}")
        t.emit("andi x7, x7, 1")
        t.check("x7", 1, lab, f"DEPTH written {enc}: logical entry 0 is valid")
        t.emit("addi x6, x1, 0x1ff")
        t.emit(f"csrw {c('siselect')}, x6")
        t.emit(f"csrr x7, {c('sireg')}")
        t.emit("andi x7, x7, 1")
        t.check("x7", 1 if MUT != "depth_short" else 0, lab, f"DEPTH written {enc}: logical entry D-1 is valid")
        t.emit("li x6, 256")
        t.emit("sltu x7, x1, x6")
        t.emit("addi x6, x1, 0x200")
        t.emit("neg x9, x7")
        t.emit("and x6, x6, x9")
        t.emit("not x9, x9")
        t.emit("andi x9, x9, 0x200")
        t.emit("or x6, x6, x9")
        t.emit(f"csrw {c('siselect')}, x6")
        t.emit(f"csrr x8, {c('sireg')}")
        t.emit("snez x8, x8")
        t.emit("and x8, x8, x7")
        t.check("x8", 0, lab, f"DEPTH written {enc}: logical entry D reads 0 when D < 256")
    return [t]


@rule
def sctrdepth_depth_entries_op() -> list[TestFile]:
    t = s_test(
        "sctrdepth_depth_entries_op",
        plan="For the smallest and the largest supported depth D: logical entries D, D+1 and 255 (when D < 256) "
        "read 0 in all six sireg* and stay 0 after writing nonzero values to sireg, sireg2 and sireg3 (read-only); "
        "logical entry D-1 accepts a written ctrsource (writable). Recording reaches only entries 0..D-1 "
        "(ctr_stack).",
    )
    for enc in (0, 4):
        wr(t, "sctrctl", 0)
        L.depth_pick(t, largest=enc == 4, reg="x1")
        L.depth_entries(t, "x1", "x1")
        lab = t.label("in")
        t.emit(f"{lab}:", 0)
        t.emit("addi x6, x1, 0x1ff")
        t.emit(f"csrw {c('siselect')}, x6")
        t.la("x6", "ctr_pa")
        t.emit("ori x6, x6, 1")
        t.emit(f"csrw {c('sireg')}, x6")
        t.emit(f"csrr x7, {c('sireg')}")
        t.check("x7", "ctr_pa+1", lab, f"DEPTH written {enc}: logical entry D-1 is writable")
        for off_ in (0, 1, None):
            lab = t.label("out")
            t.emit(f"{lab}:", 0)
            t.emit("li x6, 256")
            t.emit("sltu x9, x1, x6  // D < 256")
            if off_ is None:
                t.li("x6", 0x2FF)
            else:
                t.emit(f"addi x6, x1, {0x200 + off_}")
                t.li("x7", 0x2FF)
                t.comment("when D = 256, D+off is out of range: select 0x2FF instead (not checked then)")
                t.emit("neg x8, x9")
                t.emit("and x6, x6, x8")
                t.emit("not x8, x8")
                t.emit("and x8, x8, x7")
                t.emit("or x6, x6, x8")
            t.emit(f"csrw {c('siselect')}, x6")
            t.la("x6", "ctr_pa")
            t.emit("ori x6, x6, 1")
            t.emit(f"csrw {c('sireg')}, x6")
            t.emit(f"csrw {c('sireg2')}, x6")
            t.emit(f"csrw {c('sireg3')}, x6")
            t.li("x8", 0)
            for n in L.SIREGS:
                t.emit(f"csrr x7, {c(n)}")
                t.emit("or x8, x8, x7")
            t.emit("snez x8, x8")
            t.emit("and x8, x8, x9  // only when D < 256")
            where = "255" if off_ is None else f"D+{off_}"
            t.check(
                "x8",
                0 if MUT != "entries_beyond_rw" else 1,
                lab,
                f"DEPTH written {enc}: logical entry {where} reads 0 in sireg..sireg6 after writes",
            )
    t.extra_data.append(".p2align 2\nctr_pa: .word 0")
    return [t]


# ================================================================ transfer types
CTX_TYPE = CTX_MEASURE + (
    " TYPE is optional: each test first records a jal x0 and probes whether TYPE reads nonzero (then it must be "
    "11); the later checks then require the exact TYPE of every record when TYPE is implemented, and 0 when it "
    "is not."
)


def type_test(
    name: str, plan: str, body: Callable[[TestFile], list[Xfer]], only: str | None = None, mode: str = "S"
) -> TestFile:
    t = s_test(name, plan=plan, context=CTX_TYPE)
    L.type_probe(t)

    def run() -> None:
        if mode == "S":
            L.record_typed(t, S, lambda: body(t), name)
        else:
            anchor(t)
            wr(t, "sctrctl", U)
            xs, _, _ = win(t, "U", lambda: body(t), desc=name)
            off(t)
            L.nt_fixup(t)
            check_n(t, len(xs), f"{name} in U-mode")
            L.typed(t, lambda ex: L.check_typed_records(t, xs, f"{name} in U-mode", ex))

    if only:
        with t.only_if(only):
            run()
    else:
        run()
    return t


def mtype(x: Xfer, typ: int) -> Xfer:
    """Mutant helper: expect another TYPE."""
    x.typ = typ
    return x


@rule
def ctr_ttype9() -> list[TestFile]:
    def body(t: TestFile) -> list[Xfer]:
        xs = [jal(t, "x1"), jal(t, "x5")]
        if MUT == "x5_not_link":
            xs[1] = mtype(xs[1], L.T_DIRLJMP)
        return xs

    t = type_test(
        "ctr_ttype9",
        "Direct calls have TYPE 9: jal x1 and jal x5 in S-mode, and jal x1/x5 in U-mode "
        "(sctrctl.U only). c.jal (RV32 with C) is in the same rule's compressed case below.",
        body,
    )
    with t.only_if(L.RV32_C):
        L.record_typed(t, S, lambda: [L.c_jump(t, "c.jal")], "c.jal")
    anchor(t)
    wr(t, "sctrctl", U)
    xs, _, _ = win(t, "U", lambda: [jal(t, "x1"), jal(t, "x5")], desc="U-mode direct calls")
    off(t)
    check_n(t, 2, "U-mode direct calls")
    L.typed(t, lambda ex: L.check_typed_records(t, xs, "U-mode direct calls", ex))
    return [t]


@rule
def ctr_ttype8() -> list[TestFile]:
    def body(t: TestFile) -> list[Xfer]:
        xs = [L.jalr(t, "x1", "x6"), L.jalr(t, "x5", "x7"), L.jalr(t, "x1", "x1"), L.jalr(t, "x5", "x5")]
        if MUT == "jalr_rd_rs_same_swap":
            xs[2] = mtype(xs[2], L.T_CORSWAP)
        return xs

    t = type_test(
        "ctr_ttype8",
        "Indirect calls have TYPE 8: jalr x1, rs and jalr x5, rs with rs not the other "
        "link register (rs = x6, x7, and rs = rd itself: jalr x1, x1 and jalr x5, x5), and c.jalr x6 with "
        "C.",
        body,
    )
    with t.only_if(C):
        L.record_typed(t, S, lambda: [L.c_jump(t, "c.jalr", "x6"), L.c_jump(t, "c.jalr", "x1")], "c.jalr")
    return [t]


@rule
def ctr_ttype10() -> list[TestFile]:
    t = type_test(
        "ctr_ttype10",
        "Indirect jumps without linkage have TYPE 10: jalr x0, rs for rs = x6, x7, x8 (not x1/x5), and c.jr x6 with C.",
        lambda t: [L.jalr(t, "x0", "x6"), L.jalr(t, "x0", "x7"), L.jalr(t, "x0", "x8")],
    )
    with t.only_if(C):
        L.record_typed(t, S, lambda: [L.c_jump(t, "c.jr", "x6"), L.c_jump(t, "c.jr", "x9")], "c.jr")
    return [t]


@rule
def ctr_ttype11() -> list[TestFile]:
    t = type_test(
        "ctr_ttype11",
        "Direct jumps without linkage have TYPE 11: two jal x0 (forward), and c.j with C.",
        lambda t: [jal(t, "x0"), jal(t, "x0")],
    )
    with t.only_if(C):
        L.record_typed(t, S, lambda: [L.c_jump(t, "c.j")], "c.j")
    return [t]


@rule
def ctr_ttype12() -> list[TestFile]:
    def body(t: TestFile) -> list[Xfer]:
        return [L.jalr(t, "x1", "x5"), L.jalr(t, "x5", "x1")]

    t = type_test(
        "ctr_ttype12", "Co-routine swaps have TYPE 12: jalr x1, x5 and jalr x5, x1, and c.jalr x5 with C.", body
    )
    with t.only_if(C):
        L.record_typed(t, S, lambda: [L.c_jump(t, "c.jalr", "x5")], "c.jalr x5")
    return [t]


@rule
def ctr_ttype13() -> list[TestFile]:
    def body(t: TestFile) -> list[Xfer]:
        xs = [L.jalr(t, "x0", "x1"), L.jalr(t, "x0", "x5"), L.jalr(t, "x6", "x1"), L.jalr(t, "x7", "x5")]
        if MUT == "ret_needs_rd0":
            xs[2] = mtype(xs[2], L.T_INDLJMP)
        return xs

    t = type_test(
        "ctr_ttype13",
        "Function returns have TYPE 13: jalr rd, rs with rs = x1 or x5 and rd not x1/x5 "
        "(rd = x0, x6, x7), and c.jr x1, c.jr x5 with C.",
        body,
    )
    with t.only_if(C):
        L.record_typed(t, S, lambda: [L.c_jump(t, "c.jr", "x1"), L.c_jump(t, "c.jr", "x5")], "c.jr x1/x5")
    return [t]


@rule
def ctr_ttype14() -> list[TestFile]:
    t = type_test(
        "ctr_ttype14",
        "Other indirect jumps with linkage have TYPE 14: jalr rd, rs with rd not x0/x1/x5 "
        "and rs not x1/x5: jalr x6, x7; jalr x7, x7; jalr x8, x6.",
        lambda t: [L.jalr(t, "x6", "x7"), L.jalr(t, "x7", "x7"), L.jalr(t, "x8", "x6")],
    )
    return [t]


@rule
def ctr_ttype15() -> list[TestFile]:
    t = type_test(
        "ctr_ttype15",
        "Other direct jumps with linkage have TYPE 15: jal rd with rd not x0/x1/x5 (x6, x9, x15).",
        lambda t: [jal(t, "x6"), jal(t, "x9"), jal(t, "x15")],
    )
    return [t]


@rule
def ctr_ttype5() -> list[TestFile]:
    def body(t: TestFile) -> list[Xfer]:
        return [
            L.branch(t, "beq", -1, -1),
            L.branch(t, "bne", 0, 1),
            L.branch(t, "blt", -2048, 2047),
            L.branch(t, "bge", 0, 0),
            L.branch(t, "bltu", 1, -1),
            L.branch(t, "bgeu", -1, 0),
        ]

    t = type_test(
        "ctr_ttype5",
        "Taken branches have TYPE 5: beq, bne, blt, bge, bltu, bgeu taken (signed and "
        "unsigned edges, equal operands for bge), and c.beqz/c.bnez taken with C.",
        body,
    )
    with t.only_if(C):
        L.record_typed(t, S, lambda: [L.c_branch(t, "c.beqz", 0), L.c_branch(t, "c.bnez", -1)], "compressed")
    return [t]


@rule
def ctr_ttype4() -> list[TestFile]:
    t = s_test(
        "ctr_ttype4",
        plan="Not-taken branches have TYPE 4 when recorded (NTBREN=1, probed: NTBREN is "
        "optional and on RV32 not reachable). With NTBREN implemented, beq, bne, blt, bge, bltu, bgeu not "
        "taken, and c.beqz/c.bnez not taken with C, are recorded with TYPE 4 (or 0); without it they are "
        "not recorded.",
        context=CTX_TYPE,
    )
    L.type_probe(t)

    def body() -> list[Xfer]:
        return [
            L.nt_branch(t, "beq", 1, 2),
            L.nt_branch(t, "bne", 5, 5),
            L.nt_branch(t, "blt", 1, -1),
            L.nt_branch(t, "bge", -1, 1),
            L.nt_branch(t, "bltu", -1, 1),
            L.nt_branch(t, "bgeu", 0, 1),
        ]

    with t.rv64_only():
        L.probe_ctl(t, "x8", L.NTBREN)
        t.either(
            "x8",
            lambda: L.record_typed(t, lo(S | L.NTBREN), body, "NTBREN=1"),
            lambda: L.record_typed(t, S, body, "NTBREN unimplemented", expect=False),
        )
        with t.only_if(C):
            L.probe_ctl(t, "x8", L.NTBREN)
            t.either(
                "x8",
                lambda: L.record_typed(
                    t,
                    lo(S | L.NTBREN),
                    lambda: [L.c_branch(t, "c.beqz", 1), L.c_branch(t, "c.bnez", 0)],
                    "compressed, NTBREN=1",
                ),
                lambda: None,
            )
    return [t]


@rule
def ctrtarget_pc_next_br() -> list[TestFile]:
    t = s_test(
        "ctrtarget_pc_next_br",
        plan="With NTBREN=1 (probed; RV64), a recorded not-taken branch has "
        "ctrtarget = the next sequential pc: pc+4 for beq/bltu, pc+2 for c.beqz/c.bnez with C, not the "
        "branch target (an illegal word).",
        context=CTX_MEASURE,
        issues=f"{L.ISSUE}2349: the target of a recorded not-taken branch is the "
        'next sequential instruction (bcstrongx: "ctrtarget always holds the PC of the instr that is '
        'executed immediately following the source instruction"); the text now says so.',
    )
    with t.rv64_only():
        L.probe_ctl(t, "x8", L.NTBREN)
        t.either(
            "x8",
            lambda: record_s(
                t, lo(S | L.NTBREN), lambda: [L.nt_branch(t, "beq", 0, 1), L.nt_branch(t, "bltu", 3, 2)], "NTBREN=1"
            ),
            lambda: None,
        )
        with t.only_if(C):
            L.probe_ctl(t, "x8", L.NTBREN)
            t.either(
                "x8",
                lambda: record_s(
                    t,
                    lo(S | L.NTBREN),
                    lambda: [L.c_branch(t, "c.beqz", 7), L.c_branch(t, "c.bnez", 0)],
                    "compressed, NTBREN=1",
                ),
                lambda: None,
            )
    return [t]


@rule
def ctr_ttype3() -> list[TestFile]:
    t = s_test(
        "ctr_ttype3",
        plan="Trap returns have TYPE 3: an sret from S-mode to S-mode (sctrctl.S), and an "
        "sret from S-mode into U-mode with sctrctl.U|S (the first record after the anchor). mret is in "
        "ctr_ttype3_Sm.",
        context=CTX_TYPE + " " + L.DEEP_NOTE,
    )
    L.type_probe(t)
    L.record_typed(t, S, lambda: [L.sret_s(t), L.sret_s(t)], "sret S->S")
    L.deep(t)
    anchor(t)
    wr(t, "sctrctl", U | S)
    _, lab, _ = win(t, "U", lambda: t.emit("nop"), desc="sret into U-mode")
    off(t)

    def chk() -> None:
        L.check_n_ge(t, 1, "sret into U-mode")
        x = Xfer(f"{lab}-4", lab, L.T_TRET, "sret S->U (first record)")
        L.typed(t, lambda ex: _first_typed(t, x, ex))

    L.deep_checks(t, chk, "sret into U-mode")
    return [t]


def _first_typed(t: TestFile, x: Xfer, exact: bool) -> None:
    lab = check_entry(t, x.desc, src=x.src, tgt=x.tgt, k=0)
    t.check_masked("x8", 0xF, x.typ if exact else 0, lab, f"{x.desc}: ctrdata.TYPE")


@rule
def ctr_ttype1() -> list[TestFile]:
    t = s_test(
        "ctr_ttype1",
        plan="Exceptions have TYPE 1: an S-mode ebreak with sctrctl.S (S-to-S, first record "
        "after the anchor), and with sctrctl.U|STE (STE probed) a U-mode ebreak recorded as an external trap "
        "(first of two records; the second is the T-SBI ecall that leaves U-mode, also TYPE 1).",
        context=CTX_TYPE + " " + L.DEEP_NOTE,
    )
    L.type_probe(t)
    L.deep(t)
    anchor(t)
    wr(t, "sctrctl", S)
    eb, _ = L.ebreak_win(t, "S", "S-mode", more=[f"csrw {c('sctrctl')}, x0"])
    L.deep_checks(
        t, lambda: [L.check_n_ge(t, 1, "S-mode ebreak"), L.typed(t, lambda ex: _first_exc(t, eb, ex))], "S-mode ebreak"
    )
    L.probe_ctl(t, "x8", STE)

    def ext() -> None:
        anchor(t)
        wr(t, "sctrctl", U | STE)
        ebu, goto = L.ebreak_win(t, "U", "external")
        off(t)
        check_n(t, 2, "U-mode ebreak and ecall, external with STE")
        L.typed(t, lambda ex: [_first_exc(t, ebu, ex, logical=1), _first_exc(t, f"{goto}+4", ex, logical=0)])

    t.either("x8", ext, lambda: None)
    return [t]


def _first_exc(t: TestFile, src: str, exact: bool, logical: int | None = None) -> None:
    k = None if logical is not None else 0
    lab = check_entry(t, f"exception at {src}", src=src, k=k, logical=logical)
    want = (L.T_EXC if MUT != "exc_type2" else L.T_INT) if exact else 0
    t.check_masked("x8", 0xF, want, lab, f"exception at {src}: ctrdata.TYPE")


@rule
def ctr_ttype2() -> list[TestFile]:
    t = s_test(
        "ctr_ttype2",
        plan="Interrupts have TYPE 2: a supervisor software interrupt taken in S-mode with "
        "sctrctl.S (first record after the anchor; ctrsource = the interrupted pc from sepc, ctrtarget = "
        "the stvec handler including the vectored offset), and with sctrctl.U|STE (STE probed) an SSI taken "
        "from U-mode, recorded as an external trap with ctrtarget PC 0.",
        context=CTX_TYPE + " " + L.DEEP_NOTE,
    )
    L.type_probe(t)
    L.deep(t)
    L.s_interrupt(t, "S-mode", S)

    def chk() -> None:
        L.check_n_ge(t, 1, "SSI in S-mode")
        L.select(t, k=0)
        L.entry(t)
        L.check_src_epc(t, "SSI in S-mode")
        L.select(t, k=0)
        L.entry(t)
        L.check_tgt_handler(t, "SSI in S-mode", cause=1)
        L.typed(t, lambda ex: _type_k0(t, (L.T_INT if MUT != "int_type1" else L.T_EXC) if ex else 0, "SSI in S-mode"))

    L.deep_checks(t, chk, "SSI in S-mode")
    L.probe_ctl(t, "x8", STE)

    def ext() -> None:
        anchor(t)
        wr(t, "sctrctl", U | STE)
        L.u_interrupt(t, "external")
        off(t)
        L.check_n_ge(t, 1, "SSI from U-mode, external with STE")
        check_entry(t, "SSI from U-mode (external)", tgt=0, k=0)
        L.select(t, k=0)
        L.entry(t)
        L.check_src_epc(t, "SSI from U-mode (external)")
        L.typed(t, lambda ex: _type_k0(t, L.T_INT if ex else 0, "SSI from U-mode"))

    t.either("x8", ext, lambda: None)
    return [t]


def _type_k0(t: TestFile, want: int, desc: str) -> None:
    lab = t.label("ty")
    t.emit(f"{lab}:", 0)
    L.select(t, k=0)
    L.entry(t)
    t.check_masked("x8", 0xF, want, lab, f"{desc}: ctrdata.TYPE of the first record")


@rule
def ctr_ttype0() -> list[TestFile]:
    t = s_test(
        "ctr_ttype0",
        plan="TYPE 0 is not used by CTR: when TYPE is implemented (probed), records of a jal, "
        "jalr, taken branch and sret never have TYPE 0; when it is not, all read 0. Entries cleared by "
        "SCTRCLR read TYPE 0.",
        context=CTX_TYPE,
    )
    L.type_probe(t)
    anchor(t)
    wr(t, "sctrctl", S)
    xs = [jal(t, "x6"), L.jalr(t, "x0", "x7"), L.branch(t, "bge", 1, 1), L.sret_s(t)]
    off(t)

    def chk(exact: bool) -> None:
        for i in range(len(xs)):
            lab = t.label("t0")
            t.emit(f"{lab}:", 0)
            L.select(t, logical=i)
            L.entry(t)
            t.emit("andi x8, x8, 0xf")
            t.emit("snez x8, x8")
            t.check("x8", 1 if exact else 0, lab, f"record {i}: TYPE is {'nonzero' if exact else '0'}")

    L.typed(t, chk)
    sctrclr(t)
    lab = t.label("clr")
    t.emit(f"{lab}:", 0)
    L.select(t, logical=0)
    L.entry(t)
    t.check_masked("x8", 0xF, 0, lab, "after SCTRCLR: TYPE 0")
    return [t]


@rule
def ctrdata_type() -> list[TestFile]:
    t = s_test(
        "ctrdata_type",
        plan="ctrdata.TYPE identifies the transfer, or is 0 for every record if TYPE is "
        "unimplemented (probed with a jal x0). One run records one transfer of each jump class (9, 8, 10, "
        "11, 12, 13, 14, 15), a taken branch (5) and an sret (3): the TYPEs are exactly those, or all 0.",
        context=CTX_TYPE,
    )
    L.type_probe(t)
    L.record_typed(
        t,
        S,
        lambda: [
            jal(t, "x1"),
            L.jalr(t, "x1", "x6"),
            L.jalr(t, "x0", "x7"),
            jal(t, "x0"),
            L.jalr(t, "x5", "x1"),
            L.jalr(t, "x0", "x5"),
            L.jalr(t, "x8", "x6"),
            jal(t, "x8"),
            L.branch(t, "blt", -5, 5),
            L.sret_s(t),
        ],
        "one of each",
    )
    return [t]


@rule
def ctr_various_jump_enc() -> list[TestFile]:
    t = s_test(
        "ctr_various_jump_enc",
        plan="The jump encodings are classified by rd and rs1 only: the boundary cases "
        "between classes, each recorded with its TYPE (or 0): jalr x1, x1 (8, rs = rd is not a swap), jalr "
        "x5, x5 (8), jalr x1, x5 (12), jalr x5, x1 (12), jalr x0, x1 (13), jalr x6, x5 (13, rd other), jalr "
        "x0, x6 (10), jalr x6, x6 (14), jal x5 (9), jal x6 (15), jal x0 (11); and with C: c.jalr x1 (8), "
        "c.jalr x5 (12), c.jr x5 (13), c.jr x7 (10). The same set in U-mode with sctrctl.U.",
        context=CTX_TYPE,
    )
    L.type_probe(t)

    def body() -> list[Xfer]:
        xs = [
            L.jalr(t, "x1", "x1"),
            L.jalr(t, "x5", "x5"),
            L.jalr(t, "x1", "x5"),
            L.jalr(t, "x5", "x1"),
            L.jalr(t, "x0", "x1"),
            L.jalr(t, "x6", "x5"),
            L.jalr(t, "x0", "x6"),
            L.jalr(t, "x6", "x6"),
            jal(t, "x5"),
            jal(t, "x6"),
            jal(t, "x0"),
        ]
        if MUT == "jalr_rd_rs_same_swap":
            xs[0] = mtype(xs[0], L.T_CORSWAP)
        return xs

    L.record_typed(t, S, body, "S-mode")
    with t.only_if(C):
        L.record_typed(
            t,
            S,
            lambda: [
                L.c_jump(t, "c.jalr", "x1"),
                L.c_jump(t, "c.jalr", "x5"),
                L.c_jump(t, "c.jr", "x5"),
                L.c_jump(t, "c.jr", "x7"),
            ],
            "compressed",
        )
    anchor(t)
    wr(t, "sctrctl", U)
    xs, _, _ = win(t, "U", body, desc="U-mode jumps")
    off(t)
    check_n(t, len(xs), "U-mode")
    L.typed(t, lambda ex: L.check_typed_records(t, xs, "U-mode", ex))
    return [t]


@rule
def ctr_ttf_default() -> list[TestFile]:
    t = s_test(
        "ctr_ttf_default",
        plan="With every transfer type filter bit 0 (sctrctl = S only; on RV64 bits "
        "47:32 written 0), every transfer kind is recorded: jal x1, jalr x1, jalr x0 (x6), jal x0, jalr "
        "x1/x5 swap, return, jalr x6, jal x6, taken branch, sret, and an S-mode exception (separately, first "
        "record). A not-taken branch (NTBREN=0, opt-in) is not recorded.",
        context=CTX_MEASURE + " " + L.DEEP_NOTE,
    )
    record_s(
        t,
        S,
        lambda: [
            jal(t, "x1"),
            L.jalr(t, "x1", "x6"),
            L.jalr(t, "x0", "x6"),
            jal(t, "x0"),
            L.jalr(t, "x1", "x5"),
            L.jalr(t, "x0", "x1"),
            L.jalr(t, "x6", "x7"),
            jal(t, "x6"),
            L.nt_branch(t, "beq", 0, 1),
            L.branch(t, "bne", 0, 1),
            L.sret_s(t),
        ],
        "defaults",
        expect=[True] * 8 + [MUT == "ntbr_default"] + [True, True],
    )
    L.deep(t)
    anchor(t)
    wr(t, "sctrctl", S)
    eb, _ = L.ebreak_win(t, "S", "S-mode", more=[f"csrw {c('sctrctl')}, x0"])
    L.deep_checks(
        t, lambda: [L.check_n_ge(t, 1, "exception"), check_entry(t, "S-mode ebreak", src=eb, k=0)], "exception"
    )
    return [t]


@rule
def ctr_behavior() -> list[TestFile]:
    t = s_test(
        "ctr_behavior",
        plan="CTR records exactly the qualified transfers, in order. In U-mode with "
        "sctrctl.U only, a run of jal x1, a taken bltu, jalr x0, x1 (return), a not-taken bgeu (not "
        "qualified: NTBREN=0), jal x6, and a taken beq is recorded as five records in program order with "
        "their sources and targets; the sret into U-mode and the ecall out of it are not (S-mode disabled, "
        "STE=0).",
        context=CTX_MEASURE,
    )
    anchor(t)
    wr(t, "sctrctl", U)

    def body() -> list[Xfer]:
        return [
            jal(t, "x1"),
            L.branch(t, "bltu", 1, 2),
            L.jalr(t, "x0", "x1"),
            L.nt_branch(t, "bgeu", 1, 2),
            jal(t, "x6"),
            L.branch(t, "beq", 3, 3),
        ]

    xs, _, _ = win(t, "U", body, desc="qualified transfers")
    off(t)
    L.nt_fixup(t)
    rec = [x for x in xs if x.typ != L.T_NTBR]
    if MUT == "drop_last_record":
        rec = rec[:-1]
    check_n(t, len(rec), "U-mode run")
    for i, x in enumerate(reversed(rec)):
        check_xfer(t, x, "U-mode run", logical=i)
    return [t]


# ---------------------------------------------------------------- filters (RV64: bits 47:32)
FILTER_CASES: dict[str, tuple[str, str]] = {
    # rule: (filter, description of the inhibited kind)
    "mctrctl_tkbrinh_op": ("TKBRINH", "taken branches"),
    "mctrctl_indcallinh_op": ("INDCALLINH", "indirect calls"),
    "mctrctl_dircallinh_op": ("DIRCALLINH", "direct calls"),
    "mctrctl_indjmpinh_op": ("INDJMPINH", "indirect jumps"),
    "mctrctl_dirjmpinh_op": ("DIRJMPINH", "direct jumps"),
    "mctrctl_corswapinh_op": ("CORSWAPINH", "co-routine swaps"),
    "mctrctl_retinh_op": ("RETINH", "function returns"),
    "mctrctl_indljmpinh_op": ("INDLJMPINH", "other indirect jumps with linkage"),
    "mctrctl_dirljmpinh_op": ("DIRLJMPINH", "other direct jumps with linkage"),
    "mctrctl_tretinh_op": ("TRETINH", "trap returns"),
}
FILTER_TYPE = {
    "TKBRINH": L.T_TKBR,
    "INDCALLINH": L.T_INDCALL,
    "DIRCALLINH": L.T_DIRCALL,
    "INDJMPINH": L.T_INDJMP,
    "DIRJMPINH": L.T_DIRJMP,
    "CORSWAPINH": L.T_CORSWAP,
    "RETINH": L.T_RET,
    "INDLJMPINH": L.T_INDLJMP,
    "DIRLJMPINH": L.T_DIRLJMP,
    "TRETINH": L.T_TRET,
}


def one_of_each(t: TestFile) -> list[Xfer]:
    return [
        L.branch(t, "bne", 1, 0),
        L.jalr(t, "x1", "x6"),
        jal(t, "x1"),
        L.jalr(t, "x0", "x7"),
        jal(t, "x0"),
        L.jalr(t, "x5", "x1"),
        L.jalr(t, "x0", "x5"),
        L.jalr(t, "x6", "x7"),
        jal(t, "x6"),
        L.sret_s(t),
    ]


def filter_test(rule_name: str) -> list[TestFile]:
    flt, kind = FILTER_CASES[rule_name]
    bit = FILTERS[flt]
    t = s_test(
        rule_name,
        plan=f"{flt} (bit {bit.bit_length() - 1}) is optional and on RV32 not reachable, so the "
        "test is RV64-only and probes it. When implemented: with sctrctl.S|" + flt + ", one transfer of "
        "each kind (taken branch, indirect call, direct call, indirect jump, direct jump, co-routine swap, "
        "return, other indirect and direct jumps with linkage, sret) is recorded except the " + kind + "; "
        "with " + flt + " = 0 all are. When unimplemented, the bit reads 0 and all are recorded.",
        context=CTX_MEASURE,
        rv64=True,
    )
    L.probe_ctl(t, "x8", bit)
    typ = FILTER_TYPE[flt]
    mut_ignored = f"{flt.lower()}_ignored" == MUT
    kinds = [
        L.T_TKBR,
        L.T_INDCALL,
        L.T_DIRCALL,
        L.T_INDJMP,
        L.T_DIRJMP,
        L.T_CORSWAP,
        L.T_RET,
        L.T_INDLJMP,
        L.T_DIRLJMP,
        L.T_TRET,
    ]
    exp_on = [k != typ or mut_ignored for k in kinds]
    t.either(
        "x8",
        lambda: record_s(t, lo(S | bit), lambda: one_of_each(t), f"{flt}=1", expect=exp_on),
        lambda: record_s(t, lo(S | bit), lambda: one_of_each(t), f"{flt} unimplemented"),
    )
    record_s(t, S, lambda: one_of_each(t), f"{flt}=0")
    return [t]


for _r in FILTER_CASES:
    TESTS.append(lambda _r=_r: filter_test(_r))
    MUTANTS[f"{FILTER_CASES[_r][0].lower()}_ignored"] = f"{FILTER_CASES[_r][0]} does not inhibit its transfer type"


@rule
def mctrctl_ntbren_op() -> list[TestFile]:
    t = s_test(
        "mctrctl_ntbren_op",
        plan="NTBREN (bit 36, optional, RV64-only here) opts in to not-taken branches: "
        "with sctrctl.S only, a not-taken beq and bltu are not recorded while a taken bne is; with NTBREN=1 "
        "(when it is implemented) all three are, in order.",
        context=CTX_MEASURE,
        rv64=True,
    )
    body = lambda: [L.nt_branch(t, "beq", 1, 0), L.branch(t, "bne", 1, 0), L.nt_branch(t, "bltu", 2, 1)]
    record_s(t, S, body, "NTBREN=0", expect=[MUT == "ntbr_default", True, MUT == "ntbr_default"])
    L.probe_ctl(t, "x8", L.NTBREN)
    t.either("x8", lambda: record_s(t, lo(S | L.NTBREN), body, "NTBREN=1"), lambda: None)
    return [t]


@rule
def ctr_behavior_criteria_transfer_type() -> list[TestFile]:
    t = s_test(
        "ctr_behavior_criteria_transfer_type",
        plan="A transfer whose type is inhibited is not qualified. "
        "RV64 (filters are bits 47:32): for each implemented filter of TKBRINH, DIRJMPINH and RETINH "
        "(probed), with sctrctl.S and all three implemented ones set, a taken branch, a jal x0 and a return "
        "are recorded only if their filter is unimplemented, while a direct call (jal x1, no filter set) is "
        "always recorded. H: on a virtualization transition (VS-mode ebreak to HS-mode, vsctrctl.S and "
        "sctrctl.S) the filters come from vsctrctl: EXCINH set only in vsctrctl (where implemented) inhibits "
        "the ebreak's record (record 1 after the anchor, after the sret into VS-mode, is not the ebreak); "
        "EXCINH set only in sctrctl does not (record 1 is the ebreak).",
        context=CTX_MEASURE + " " + L.DEEP_NOTE,
        rv64=True,
    )
    bits = FILTERS["TKBRINH"] | FILTERS["DIRJMPINH"] | FILTERS["RETINH"]
    L.probe_ctl(t, "x8", bits)
    anchor(t)
    t.emit("ori x6, x8, 2  // S | the implemented filters")
    t.emit(f"csrw {c('sctrctl')}, x6")
    xs = [L.branch(t, "beq", 0, 0), jal(t, "x0"), jal(t, "x1"), L.jalr(t, "x0", "x1")]
    off(t)
    lab = t.label("cnt")
    t.emit(f"{lab}:", 0)
    t.comment("expected records = 1 (the call) + one per unimplemented filter")
    t.load("x6", lo(FILTERS["TKBRINH"]))
    t.emit("and x6, x6, x8")
    t.emit("seqz x7, x6")
    t.load("x6", lo(FILTERS["DIRJMPINH"]))
    t.emit("and x6, x6, x8")
    t.emit("seqz x6, x6")
    t.emit("add x7, x7, x6")
    t.load("x6", lo(FILTERS["RETINH"]))
    t.emit("and x6, x6, x8")
    t.emit("seqz x6, x6")
    t.emit("add x7, x7, x6")
    t.emit(f"addi x7, x7, {1 if MUT != 'filter_ignored_call' else 0}")
    L.nrec(t, "x9")
    t.emit("xor x9, x9, x7")
    t.emit("seqz x9, x9")
    t.check_bool("x9", lab, "records = the call + one per unimplemented filter")
    lab = t.label("call")
    t.emit(f"{lab}:", 0)
    t.load("x6", lo(FILTERS["RETINH"]))
    t.emit("and x6, x6, x8")
    t.emit("seqz x6, x6  // the return after the call is recorded")
    t.emit("addi x6, x6, 0x200")
    t.emit(f"csrw {c('siselect')}, x6")
    t.emit(f"csrr x7, {c('sireg')}")
    t.check("x7", f"{xs[2].src}+1", lab, "the direct call (no filter set for it) is recorded")
    with t.only_if(H):
        vfilter_cases(t)
    return [t]


def rec_k_is(t: TestFile, k: int, src: str, want: int, desc: str) -> None:
    """Check whether record k after the anchor has ctrsource = src | V (want 1) or not (want 0)."""
    lab = t.label("rk")
    t.emit(f"{lab}:", 0)
    L.select(t, k=k)
    t.emit(f"csrr x6, {c('sireg')}")
    t.la("x7", src)
    t.emit("ori x7, x7, 1")
    t.emit("xor x6, x6, x7")
    t.emit("seqz x6, x6")
    t.check("x6", want, lab, f"{desc}: record {k} after the anchor is {'' if want else 'not '}the transfer at {src}")


def vfilter_cases(t: TestFile) -> None:
    """VS-mode ebreak to HS-mode (hedeleg[3]=0) with vsctrctl.S and sctrctl.S: the transfer-type filters of a
    virtualization transition come from vsctrctl (EXCINH probed in each register)."""
    h_deleg(t, False)
    L.deep(t)
    for in_vs in (True, False):
        reg = "vsctrctl" if in_vs else "sctrctl"
        L.probe_ctl(t, "x8", L.EXCINH, reg)

        def case(in_vs: bool = in_vs) -> None:
            anchor(t)
            wr(t, "vsctrctl", lo(S | (L.EXCINH if in_vs else 0)))
            wr(t, "sctrctl", lo(S | (0 if in_vs else L.EXCINH)))
            d = f"VS ebreak to HS, EXCINH in {'vsctrctl' if in_vs else 'sctrctl'} only"
            eb, _ = L.ebreak_win(t, "VS", d)
            off(t)
            off(t, "vsctrctl")
            want = 0 if in_vs else 1
            if MUT == "vfilter_from_target":
                want = 1 - want
            L.deep_checks(
                t,
                lambda: [
                    L.check_n_ge(t, 2, d),
                    check_entry(t, f"{d}: the sret into VS-mode", src=f"{eb}-4", tgt=eb, typ=L.T_TRET, k=0),
                    rec_k_is(t, 1, eb, want, d),
                ],
                d,
            )

        t.either("x8", case, lambda: None)


# ================================================================ privilege-mode transitions
CTX_TRAP = (
    CTX_MEASURE
    + " "
    + L.DEEP_NOTE
    + (
        " ebreak traps are delegated to S-mode (framework medeleg); VU-mode ebreaks go to VS-mode with hedeleg[3]=1 "
        "and to HS-mode with hedeleg[3]=0. Entering a lower mode is an sret (at <window>-4) and leaving it a T-SBI "
        "ecall (at <goto>+4), which are themselves recorded according to the same rules."
    )
)


def h_deleg(t: TestFile, on: bool) -> None:
    L.hedeleg(t, 3, on)


@rule
def ctr_trap_enabled() -> list[TestFile]:
    t = s_test(
        "ctr_trap_enabled",
        plan="A trap between two enabled modes is recorded normally: with sctrctl.U|S, "
        "a U-mode ebreak is the second record after the anchor (the first is the sret into U-mode): "
        "ctrsource = the ebreak pc | V, ctrtarget = the stvec handler, TYPE 1 or 0. The M-mode target is in "
        "ctr_trap_enabled_Sm.",
        context=CTX_TRAP,
    )
    L.deep(t)
    anchor(t)
    wr(t, "sctrctl", U | S)
    eb, _ = L.ebreak_win(t, "U", "U and S enabled")
    off(t)

    def chk() -> None:
        L.check_n_ge(t, 2, "U-mode ebreak")
        check_entry(t, "the sret into U-mode", src=f"{eb}-4", tgt=eb, typ=L.T_TRET, k=0)
        check_entry(t, "U-mode ebreak", src=eb if MUT != "trap_src_zero" else 0, typ=L.T_EXC, k=1)
        L.check_tgt_handler(t, "U-mode ebreak")

    L.deep_checks(t, chk, "U-mode ebreak")
    return [t]


@rule
def ctr_trap_ee() -> list[TestFile]:
    t = s_test(
        "ctr_trap_ee",
        plan="Trap, source and target enabled: recorded.\n"
        "1. S-mode ebreak with sctrctl.S (S to S): first record = the ebreak, target the stvec handler.\n"
        "2. H: VU-mode ebreak to VS-mode (hedeleg[3]=1) with vsctrctl.U|S: the sret from HS-mode into VU "
        "is not recorded (HS disabled), so the ebreak is the first record, with ctrtarget = the vstvec "
        "handler.\n"
        "3. H: VS-mode ebreak to HS-mode (hedeleg[3]=0) with vsctrctl.S and sctrctl.S: second record (after "
        "the sret into VS-mode), target the stvec handler.",
        context=CTX_TRAP,
    )
    L.deep(t)
    anchor(t)
    wr(t, "sctrctl", S)
    eb, _ = L.ebreak_win(t, "S", "S to S", more=[f"csrw {c('sctrctl')}, x0"])
    L.deep_checks(
        t,
        lambda: [
            L.check_n_ge(t, 1, "S ebreak"),
            check_entry(t, "S-mode ebreak", src=eb, typ=L.T_EXC, k=0),
            L.check_tgt_handler(t, "S-mode ebreak"),
        ],
        "S ebreak",
    )
    with t.only_if(H):
        h_deleg(t, True)
        anchor(t)
        wr(t, "vsctrctl", U | S)
        ebv, _ = L.ebreak_win(t, "VU", "VU to VS")
        off(t, "vsctrctl")
        h_deleg(t, False)
        L.deep_checks(
            t,
            lambda: [
                L.check_n_ge(t, 1, "VU ebreak"),
                check_entry(t, "VU-mode ebreak to VS", src=ebv, typ=L.T_EXC, k=0),
                L.check_tgt_handler(t, "VU-mode ebreak to VS", tvec="vstvec"),
            ],
            "VU ebreak",
        )
        anchor(t)
        wr(t, "vsctrctl", S)
        wr(t, "sctrctl", S)
        ebs, _ = L.ebreak_win(t, "VS", "VS to HS")
        off(t)
        off(t, "vsctrctl")
        L.deep_checks(
            t,
            lambda: [
                L.check_n_ge(t, 2, "VS ebreak"),
                check_entry(t, "the sret into VS-mode", src=f"{ebs}-4", tgt=ebs, typ=L.T_TRET, k=0),
                check_entry(t, "VS-mode ebreak to HS", src=ebs, typ=L.T_EXC, k=1),
                L.check_tgt_handler(t, "VS-mode ebreak to HS"),
            ],
            "VS ebreak",
        )
    return [t]


@rule
def ctr_trap_disabled_src() -> list[TestFile]:
    t = s_test(
        "ctr_trap_disabled_src",
        plan="A trap from a disabled mode into an enabled one is partially recorded "
        "with ctrsource.PC = 0: sctrctl.S only, a U-mode ebreak. Records after the anchor: the sret into "
        "U-mode (enabled to disabled: ctrtarget PC 0), then the ebreak with ctrsource = 1 (V only), "
        "ctrtarget = the stvec handler, TYPE 1 or 0.",
        context=CTX_TRAP,
    )
    L.deep(t)
    anchor(t)
    wr(t, "sctrctl", S)
    eb, _ = L.ebreak_win(t, "U", "U disabled, S enabled")
    off(t)

    def chk() -> None:
        L.check_n_ge(t, 2, "U ebreak")
        check_entry(t, "the sret into U-mode", src=f"{eb}-4", tgt=0, typ=L.T_TRET, k=0)
        check_entry(
            t, "U-mode ebreak (from a disabled mode)", src=0 if MUT != "trap_src_kept" else eb, typ=L.T_EXC, k=1
        )
        L.check_tgt_handler(t, "U-mode ebreak")

    L.deep_checks(t, chk, "U ebreak")
    return [t]


@rule
def ctr_trap_de() -> list[TestFile]:
    t = s_test(
        "ctr_trap_de",
        plan="Trap from a disabled into an enabled mode: recorded with ctrsource.PC = 0. H: "
        "vsctrctl.S only (VU disabled, VS enabled), hedeleg[3]=1, a VU-mode ebreak: the sret from HS-mode "
        "(disabled) into VU is not recorded, so the ebreak is the first record: ctrsource = 1, ctrtarget = "
        "the vstvec handler, TYPE 1 or 0.",
        context=CTX_TRAP,
        required=["I", "S", "H", "Ssctr"],
    )
    L.deep(t)
    h_deleg(t, True)
    anchor(t)
    wr(t, "vsctrctl", S)
    L.ebreak_win(t, "VU", "VU disabled, VS enabled")
    off(t, "vsctrctl")
    h_deleg(t, False)
    L.deep_checks(
        t,
        lambda: [
            L.check_n_ge(t, 1, "VU ebreak"),
            check_entry(t, "VU-mode ebreak (from a disabled mode)", src=0, typ=L.T_EXC, k=0),
            L.check_tgt_handler(t, "VU-mode ebreak", tvec="vstvec"),
        ],
        "VU ebreak",
    )
    return [t]


def n_zero_case(
    t: TestFile, setup: Callable[[], None], mode: str, desc: str, deleg: bool | None = None, vs: bool = False
) -> None:
    if deleg is not None:
        h_deleg(t, deleg)
    anchor(t)
    setup()
    L.ebreak_win(t, mode, desc)
    off(t)
    if vs:
        off(t, "vsctrctl")
    if deleg:
        h_deleg(t, False)
    check_n(t, 0 if MUT != "external_default" else 1, desc)


@rule
def ctr_trap_disabled_tgt() -> list[TestFile]:
    t = s_test(
        "ctr_trap_disabled_tgt",
        plan="A trap from an enabled into a disabled mode (external trap) is not "
        "recorded by default: sctrctl.U only, STE=0, a U-mode ebreak: no record at all (the sret into "
        "U-mode is from a disabled mode, and the T-SBI ecall out of U-mode is another external trap).",
        context=CTX_TRAP,
    )
    n_zero_case(t, lambda: wr(t, "sctrctl", U), "U", "U enabled, S disabled, STE=0")
    return [t]


@rule
def ctr_trap_ed() -> list[TestFile]:
    t = s_test(
        "ctr_trap_ed",
        plan="External traps are not recorded by default (STE=0), H cases: VU-mode ebreak to "
        "VS-mode with vsctrctl.U only; VU-mode ebreak to HS-mode (hedeleg[3]=0) with vsctrctl.U only; "
        "VS-mode ebreak to HS-mode with vsctrctl.S only. None of them, nor the GOTO ecalls, is recorded.",
        context=CTX_TRAP,
        required=["I", "S", "H", "Ssctr"],
    )
    n_zero_case(t, lambda: wr(t, "vsctrctl", U), "VU", "VU to VS", deleg=True, vs=True)
    n_zero_case(t, lambda: wr(t, "vsctrctl", U), "VU", "VU to HS", deleg=False, vs=True)
    n_zero_case(t, lambda: wr(t, "vsctrctl", S), "VS", "VS to HS", deleg=False, vs=True)
    return [t]


@rule
def ctr_trap_dd() -> list[TestFile]:
    t = s_test(
        "ctr_trap_dd",
        plan="A trap between two disabled modes is not recorded, even with the external trap "
        "enables set: sctrctl = STE only, U-mode ebreak; H: vsctrctl = STE, sctrctl = STE, VU-mode ebreaks "
        "to VS (hedeleg[3]=1) and to HS: no records.",
        context=CTX_TRAP,
    )
    n_zero_case(t, lambda: wr(t, "sctrctl", STE), "U", "U and S disabled, STE=1")
    with t.only_if(H):

        def st() -> None:
            wr(t, "sctrctl", STE)
            wr(t, "vsctrctl", STE)

        n_zero_case(t, st, "VU", "VU and VS disabled, STE=1", deleg=True, vs=True)
        n_zero_case(t, st, "VU", "VU and HS disabled, STE=1", deleg=False, vs=True)
    return [t]


@rule
def ctr_trapret_enabled() -> list[TestFile]:
    t = s_test(
        "ctr_trapret_enabled",
        plan="A trap return between enabled modes is recorded normally: sctrctl.U|S, "
        "the sret into U-mode is the first record: ctrsource = the sret pc | V, ctrtarget = the first U-mode "
        "instruction, TYPE 3 or 0. mret is in ctr_trapret_enabled_Sm.",
        context=CTX_TRAP,
    )
    L.deep(t)
    anchor(t)
    wr(t, "sctrctl", U | S)
    _, lab, _ = win(t, "U", lambda: t.emit("nop"), desc="U and S enabled")
    off(t)
    L.deep_checks(
        t,
        lambda: [
            L.check_n_ge(t, 1, "sret"),
            check_entry(t, "sret S->U", src=f"{lab}-4", tgt=lab if MUT != "tret_tgt_zero" else 0, typ=L.T_TRET, k=0),
        ],
        "sret",
    )
    return [t]


def vs_sret_vu(t: TestFile) -> Xfer:
    """In VS-mode: sret into VU-mode (vsstatus.SPP = 0, SPIE = 0) at the label after an illegal word."""
    src, tgt = t.label("vsret"), t.label("vsrett")
    t.la("x6", tgt)
    t.emit("csrw sepc, x6  // vsepc")
    t.li("x6", L.SPP | L.SPIE)
    t.emit("csrc sstatus, x6  // vsstatus.SPP = U, SPIE = 0")
    t.emit(f"{src}: sret  // VS -> VU")
    t.emit(".word 0  // not reached")
    t.emit(f"{tgt}:", 0)
    return Xfer(src, tgt, L.T_TRET, "sret VS->VU")


def vs_sret_case(t: TestFile, vsctl: int, n: int, tgt0: bool, desc: str) -> None:
    """vsctrctl = vsctl, sctrctl = 0: in a VS window, sret into VU-mode (followed by a VU jal when vsctl = U only);
    n records expected: the sret (ctrtarget 0 if tgt0), or for vsctl = U the VU jal."""
    anchor(t)
    wr(t, "sctrctl", 0)
    wr(t, "vsctrctl", vsctl)
    xs, _, _ = win(t, "VS", lambda: [vs_sret_vu(t)] + ([jal(t, "x7")] if vsctl == U else []), desc=desc)
    off(t, "vsctrctl")
    check_n(t, n, desc)
    x = xs[0]
    if vsctl == U:
        check_xfer(t, xs[1], f"{desc}: only the VU jal", logical=0)
    else:
        check_entry(t, f"{desc}: {x.desc}", src=x.src, tgt=0 if tgt0 else x.tgt, typ=L.T_TRET, logical=0)


@rule
def ctr_trapret_ee() -> list[TestFile]:
    t = s_test(
        "ctr_trapret_ee",
        plan="Trap return, source and target enabled: recorded. sret S->S with sctrctl.S "
        "(exact: one record); H: sret HS->VS with sctrctl.S and vsctrctl.S: the first record is the sret with "
        "ctrtarget = the VS-mode label; sret VS->VU with vsctrctl.S|U and sctrctl = 0: the only record (the "
        "sret into VS-mode is from disabled HS-mode and the VU-mode ecall to HS-mode is external, STE=0).",
        context=CTX_TRAP,
    )
    record_s(t, S, lambda: [L.sret_s(t)], "sret S->S")
    with t.only_if(H):
        L.deep(t)
        anchor(t)
        wr(t, "vsctrctl", S)
        wr(t, "sctrctl", S)
        _, lab, _ = win(t, "VS", lambda: t.emit("nop"), desc="HS and VS enabled")
        off(t)
        off(t, "vsctrctl")
        L.deep_checks(
            t,
            lambda: [
                L.check_n_ge(t, 1, "sret"),
                check_entry(t, "sret HS->VS", src=f"{lab}-4", tgt=lab, typ=L.T_TRET, k=0),
            ],
            "sret",
        )
        vs_sret_case(t, S | U, 1, False, "sret VS->VU, vsctrctl.S|U")
    return [t]


@rule
def ctr_trapret_to_disabled() -> list[TestFile]:
    t = s_test(
        "ctr_trapret_to_disabled",
        plan="A trap return from an enabled mode to a disabled one is partially "
        "recorded with ctrtarget.PC = 0: sctrctl.S only, the sret into U-mode is the first record: "
        "ctrsource = the sret pc | V, ctrtarget = 0 (MISP free), TYPE 3 or 0; a U-mode jal is not recorded "
        "after it (the next record is the T-SBI ecall from U-mode with ctrsource 0).",
        context=CTX_TRAP,
    )
    L.deep(t)
    anchor(t)
    wr(t, "sctrctl", S)
    _, lab, _ = win(t, "U", lambda: jal(t, "x6"), desc="S enabled, U disabled")
    off(t)
    L.deep_checks(
        t,
        lambda: [
            L.check_n_ge(t, 2, "sret"),
            check_entry(t, "sret S->U", src=f"{lab}-4", tgt=0 if MUT != "tret_tgt_kept" else lab, typ=L.T_TRET, k=0),
            check_entry(t, "the ecall out of U-mode", src=0, typ=L.T_EXC, k=1),
        ],
        "sret",
    )
    return [t]


@rule
def ctr_trapret_ed() -> list[TestFile]:
    t = s_test(
        "ctr_trapret_ed",
        plan="Trap return from an enabled mode into a disabled one: recorded with "
        "ctrtarget.PC = 0. H: sctrctl.S, vsctrctl = 0: the sret HS->VS is the first record (ctrsource = the "
        "sret pc | V, ctrtarget 0, TYPE 3 or 0), and the VS-mode ecall back (disabled to enabled) is the "
        "second, with ctrsource 0. The enables of a virtualization transition come from sctrctl.S for HS and "
        "vsctrctl.S for VS. Within V=1: vsctrctl.S only, sctrctl = 0: an sret VS->VU is the only record, with "
        "ctrtarget 0.",
        context=CTX_TRAP,
        required=["I", "S", "H", "Ssctr"],
    )
    L.deep(t)
    anchor(t)
    wr(t, "vsctrctl", 0)
    wr(t, "sctrctl", S)
    _, lab, _ = win(t, "VS", lambda: jal(t, "x6"), desc="HS enabled, VS disabled")
    off(t)
    L.deep_checks(
        t,
        lambda: [
            L.check_n_ge(t, 2, "sret"),
            check_entry(t, "sret HS->VS", src=f"{lab}-4", tgt=0, typ=L.T_TRET, k=0),
            check_entry(t, "the ecall out of VS-mode", src=0, typ=L.T_EXC, k=1),
        ],
        "sret",
    )
    vs_sret_case(t, S, 1, True, "sret VS->VU, vsctrctl.S only")
    return [t]


@rule
def ctr_trapret_from_disabled() -> list[TestFile]:
    t = s_test(
        "ctr_trapret_from_disabled",
        plan="A trap return from a disabled mode into an enabled one is not "
        "recorded: sctrctl.U only, the sret into U-mode leaves no record; the only record is a U-mode jal "
        "(the ecall out is an external trap, STE=0).",
        context=CTX_MEASURE,
    )
    anchor(t)
    wr(t, "sctrctl", U)
    (j,), _lab, _ = win(t, "U", lambda: [jal(t, "x6")], desc="S disabled, U enabled")
    off(t)
    check_n(t, 1 if MUT != "tret_from_disabled" else 2, "sret from a disabled mode, U jal")
    check_xfer(t, j, "the only record", logical=0)
    return [t]


@rule
def ctr_trapret_de() -> list[TestFile]:
    t = s_test(
        "ctr_trapret_de",
        plan="Trap return from a disabled into an enabled mode: not recorded. H: "
        "vsctrctl.S only (sctrctl = 0): the sret HS->VS is not recorded; the only record is a VS-mode jal "
        "(the VS-mode ecall to HS is external, STE=0). Also vsctrctl.U only: sret HS->VU not recorded, "
        "only the VU-mode jal; and an sret VS->VU (VS disabled) is not recorded: only a VU jal after it.",
        context=CTX_MEASURE,
        required=["I", "S", "H", "Ssctr"],
    )
    for bit, mode in ((S, "VS"), (U, "VU")):
        anchor(t)
        wr(t, "sctrctl", 0)
        wr(t, "vsctrctl", bit)
        (j,), _, _ = win(t, mode, lambda: [jal(t, "x6")], desc=f"HS disabled, {mode} enabled")
        off(t, "vsctrctl")
        check_n(t, 1, f"sret HS->{mode} from a disabled mode, {mode} jal")
        check_xfer(t, j, f"the only record ({mode})", logical=0)
    vs_sret_case(t, U, 1, False, "sret VS->VU, vsctrctl.U only")
    return [t]


@rule
def ctr_trapret_dd() -> list[TestFile]:
    t = s_test(
        "ctr_trapret_dd",
        plan="Trap return between disabled modes: not recorded. sctrctl = STE only, sret "
        "into U-mode; H: sctrctl = vsctrctl = STE, srets into VS and VU: no records.",
        context=CTX_MEASURE,
    )
    anchor(t)
    wr(t, "sctrctl", STE)
    win(t, "U", lambda: t.emit("nop"), desc="S and U disabled")
    with t.only_if(H):
        wr(t, "vsctrctl", STE)
        win(t, "VS", lambda: t.emit("nop"), desc="HS and VS disabled")
        win(t, "VU", lambda: t.emit("nop"), desc="HS and VU disabled")
        off(t, "vsctrctl")
    off(t)
    check_n(t, 0, "trap returns between disabled modes")
    return [t]


# ================================================================ external traps
CTX_EXT = CTX_TRAP + (
    " STE (and vsctrctl.STE) are optional together with external trap recording: each case probes STE and, when "
    "it is unimplemented, requires that nothing is recorded."
)


def ext_case(
    t: TestFile, mode: str, ctl: int | X, vsctl: int | None, deleg: bool | None, expect_n: int, desc: str
) -> None:
    """ebreak in `mode`, then the GOTO ecall out; expect_n records (each an external trap with ctrtarget PC 0)."""
    if deleg is not None:
        h_deleg(t, deleg)
    anchor(t)
    if vsctl is not None:
        wr(t, "vsctrctl", vsctl)
    wr(t, "sctrctl", ctl)
    eb, goto = L.ebreak_win(t, mode, desc)
    off(t)
    if vsctl is not None:
        off(t, "vsctrctl")
    if deleg:
        h_deleg(t, False)
    check_n(t, expect_n, desc)
    srcs = [f"{goto}+4", eb] if expect_n == 2 else [eb][:expect_n]
    for i, sname in enumerate(srcs):
        check_entry(
            t,
            f"{desc}: {'the GOTO ecall' if sname != eb else 'the ebreak'}",
            src=sname,
            tgt=0 if MUT != "ext_tgt_kept" else sname,
            typ=L.T_EXC,
            logical=i,
        )


def ste_probe(t: TestFile, reg: str = "x1") -> None:
    L.probe_ctl(t, reg, STE)


@rule
def exttrap_us() -> list[TestFile]:
    t = s_test(
        "exttrap_us",
        plan="U-mode to S-mode external traps need sctrctl.STE. sctrctl.U only (S disabled): "
        "STE=0: the U-mode ebreak and the T-SBI ecall (both U to S) are not recorded; STE=1 (probed): both "
        "are, with ctrsource = their pcs, ctrtarget = 0, TYPE 1 or 0.",
        context=CTX_EXT,
    )
    ext_case(t, "U", U, None, None, 0, "STE=0")
    ste_probe(t, "x8")
    t.either(
        "x8",
        lambda: ext_case(t, "U", U | STE, None, None, 2 if MUT != "ste_ignored" else 0, "STE=1"),
        lambda: ext_case(t, "U", U | STE, None, None, 0, "STE unimplemented"),
    )
    return [t]


@rule
def mctrctl_ste_op() -> list[TestFile]:
    t = s_test(
        "mctrctl_ste_op",
        plan="STE enables recording of traps to S-mode while S=0. With sctrctl.U|STE (STE "
        "probed), a U-mode ebreak and an SSI taken from U-mode are recorded as external traps (target PC 0); "
        "with sctrctl.U|S|STE the same ebreak is a normal trap (S enabled: target = the handler), so STE "
        "only matters when S=0; with STE=0 and S=0 nothing is recorded.",
        context=CTX_EXT,
    )
    ste_probe(t, "x8")

    def on() -> None:
        ext_case(t, "U", U | STE, None, None, 2, "STE=1, S=0")
        anchor(t)
        wr(t, "sctrctl", U | STE)
        L.u_interrupt(t, "STE=1, S=0")
        off(t)
        L.check_n_ge(t, 1, "SSI from U-mode with STE")
        check_entry(t, "SSI from U-mode with STE (external)", tgt=0, typ=L.T_INT, k=0)
        L.deep(t)
        anchor(t)
        wr(t, "sctrctl", U | S | STE)
        eb, _ = L.ebreak_win(t, "U", "STE=1, S=1")
        off(t)
        L.deep_checks(
            t,
            lambda: [
                L.check_n_ge(t, 2, "STE=1 S=1"),
                check_entry(t, "U ebreak with S=1", src=eb, typ=L.T_EXC, k=1),
                L.check_tgt_handler(t, "U ebreak with S=1"),
            ],
            "STE=1 S=1",
        )

    t.either("x8", on, lambda: None)
    ext_case(t, "U", U, None, None, 0, "STE=0, S=0")
    return [t]


@rule
def exttrap_def() -> list[TestFile]:
    t = s_test(
        "exttrap_def",
        plan="External traps (enabled mode to a mode not enabled) are recorded only with the "
        "target's xTE set, and regardless of EXCINH/INTRINH: with sctrctl.U|STE (probed) and, on RV64, "
        "EXCINH and INTRINH set where implemented, a U-mode ebreak and the ecall out are still recorded (2 "
        "records, target PC 0), and so is an SSI taken from U-mode; with STE clear, none.",
        context=CTX_EXT,
    )
    ste_probe(t, "x8")
    inh = L.EXCINH | L.INTRINH

    def on() -> None:
        ext_case(
            t,
            "U",
            lo(U | STE | inh) if MUT != "ext_obeys_excinh" else lo(U | STE),
            None,
            None,
            2 if MUT != "ext_obeys_excinh" else 0,
            "STE=1, EXCINH=INTRINH=1",
        )
        anchor(t)
        wr(t, "sctrctl", lo(U | STE | inh))
        L.u_interrupt(t, "STE=1, INTRINH=1")
        off(t)
        L.check_n_ge(t, 1, "SSI from U-mode with STE and INTRINH")
        check_entry(t, "SSI from U-mode, INTRINH=1 (external)", tgt=0, typ=L.T_INT, k=0)

    t.either("x8", on, lambda: None)
    ext_case(t, "U", lo(U | inh), None, None, 0, "STE=0")
    return [t]


@rule
def exttrap_ctrtarget0() -> list[TestFile]:
    t = s_test(
        "exttrap_ctrtarget0",
        plan="An external trap's record has ctrtarget.PC = 0 (MISP free): U to S "
        "(sctrctl.U|STE) and, with H, VS to HS (vsctrctl.S, sctrctl.STE) and VU to VS (vsctrctl.U|STE, "
        "hedeleg[3]=1); each record's source is the trapping pc. STE probed.",
        context=CTX_EXT,
    )
    ste_probe(t, "x8")
    t.either("x8", lambda: ext_case(t, "U", U | STE, None, None, 2, "U to S"), lambda: None)
    with t.only_if(H):
        ste_probe(t, "x8")

        def on() -> None:
            ext_case(t, "VS", STE, S, False, 2, "VS to HS")
            ext_case(t, "VU", 0, U | STE, True, 1, "VU to VS")

        t.either("x8", on, lambda: None)
    return [t]


@rule
def exttrap_requirements() -> list[TestFile]:
    t = s_test(
        "exttrap_requirements",
        plan="Intervening modes must have their external trap enables set too. H, "
        "VU-mode ebreak to HS-mode (hedeleg[3]=0), vsctrctl.U only: with sctrctl.STE=1 and vsctrctl.STE=0 "
        "(the intervening VS-mode's enable clear) nothing is recorded; with both set, the ebreak and the "
        "ecall are (target PC 0). STE probed. The M-mode target cases are in exttrap_requirements_Sm.",
        context=CTX_EXT,
        required=["I", "S", "H", "Ssctr"],
    )
    ste_probe(t, "x8")

    def on() -> None:
        ext_case(t, "VU", STE, U, False, 0 if MUT != "no_intervening" else 2, "sctrctl.STE only")
        ext_case(t, "VU", STE, U | STE, False, 2, "both STE")

    t.either("x8", on, lambda: None)
    return [t]


@rule
def exttrap_vuvs() -> list[TestFile]:
    t = s_test(
        "exttrap_vuvs",
        plan="VU to VS external traps need vsctrctl.STE. vsctrctl.U (VS disabled), "
        "hedeleg[3]=1, VU-mode ebreak: vsctrctl.STE=0 and sctrctl.STE=1: not recorded; vsctrctl.STE=1, "
        "sctrctl.STE=0: the ebreak is recorded (target 0) and the GOTO ecall (VU to HS, which also needs "
        "sctrctl.STE) is not. STE probed.",
        context=CTX_EXT,
        required=["I", "S", "H", "Ssctr"],
    )
    ste_probe(t, "x8")

    def on() -> None:
        ext_case(t, "VU", STE, U, True, 0 if MUT != "vuvs_uses_sctrctl" else 1, "vsctrctl.STE=0, sctrctl.STE=1")
        ext_case(t, "VU", 0, U | STE, True, 1, "vsctrctl.STE=1")

    t.either("x8", on, lambda: None)
    return [t]


@rule
def exttrap_vuhs() -> list[TestFile]:
    t = s_test(
        "exttrap_vuhs",
        plan="VU to HS external traps need sctrctl.STE and vsctrctl.STE. vsctrctl.U, "
        "hedeleg[3]=0, VU-mode ebreak and the GOTO ecall (both VU to HS): (sctrctl.STE, vsctrctl.STE) = "
        "(0,0), (1,0), (0,1): no records; (1,1): two records, target PC 0. STE probed.",
        context=CTX_EXT,
        required=["I", "S", "H", "Ssctr"],
    )
    ste_probe(t, "x8")

    def on() -> None:
        for s_ste, v_ste in ((0, 0), (1, 0), (0, 1), (1, 1)):
            n = 2 if s_ste and v_ste else 0
            if MUT == "vuhs_needs_only_ste" and s_ste and not v_ste:
                n = 2
            ext_case(t, "VU", STE * s_ste, U | STE * v_ste, False, n, f"sctrctl.STE={s_ste}, vsctrctl.STE={v_ste}")

    t.either("x8", on, lambda: None)
    return [t]


@rule
def exttrap_vshs() -> list[TestFile]:
    t = s_test(
        "exttrap_vshs",
        plan="VS to HS external traps need sctrctl.STE only. vsctrctl.S (HS disabled), "
        "hedeleg[3]=0, VS-mode ebreak and the GOTO ecall: sctrctl.STE=0 with vsctrctl.STE=1: no records; "
        "sctrctl.STE=1 with vsctrctl.STE=0: both recorded (target PC 0). STE probed.",
        context=CTX_EXT,
        required=["I", "S", "H", "Ssctr"],
    )
    ste_probe(t, "x8")

    def on() -> None:
        ext_case(t, "VS", 0, S | STE, False, 0, "sctrctl.STE=0, vsctrctl.STE=1")
        ext_case(t, "VS", STE, S, False, 2 if MUT != "vshs_needs_vsste" else 0, "sctrctl.STE=1, vsctrctl.STE=0")

    t.either("x8", on, lambda: None)
    return [t]


@rule
def exttrap_implreq() -> list[TestFile]:
    t = s_test(
        "exttrap_implreq",
        plan="If external trap recording is implemented, sctrctl.STE is writable and, with "
        "H, vsctrctl.STE is writable as well: the two probes agree (STE writable in sctrctl iff in "
        "vsctrctl). The mctrctl.MTE half is in exttrap_implreq_Sm.",
        required=["I", "S", "H", "Ssctr"],
    )
    lab = t.label("p")
    t.emit(f"{lab}:", 0)
    L.probe_ctl(t, "x8", STE)
    L.probe_ctl(t, "x9", STE, "vsctrctl")
    t.emit("xor x8, x8, x9")
    t.check("x8", 0, lab, "sctrctl.STE and vsctrctl.STE are both writable or both read-only 0")
    return [t]


# ================================================================ freeze
@rule
def mctrctl_bpfrz_op() -> list[TestFile]:
    t = s_test(
        "mctrctl_bpfrz_op",
        plan="BPFRZ=1: a breakpoint exception trapping to S-mode sets sctrstatus.FROZEN "
        "and is not recorded.\n"
        "1. sctrctl.S|BPFRZ, S-mode ebreak: afterwards FROZEN=1 and WRPTR = 0 (no record of the ebreak or of "
        "the handler).\n"
        "2. sctrctl.U|BPFRZ (S disabled, STE=0), U-mode ebreak to S-mode: the freeze does not depend on the "
        "target being enabled: FROZEN=1, no record (the T-SBI ecall after it is not recorded either).\n"
        "3. BPFRZ=0 (sctrctl.S): the S-mode ebreak is recorded and FROZEN stays 0.\n"
        "The M-mode target is in mctrctl_bpfrz_op_Sm.",
        context=CTX_TRAP,
    )
    anchor(t)
    wr(t, "sctrctl", S | BPFRZ)
    L.ebreak_win(t, "S", "BPFRZ=1", more=[f"csrw {c('sctrctl')}, x0"])
    lab = t.label("fz")
    t.emit(f"{lab}:", 0)
    rd(t, "x7", "sctrstatus")
    t.check("x7", lo(FROZEN) if MUT != "bpfrz_ignored" else 0, lab, "S-mode ebreak with BPFRZ: FROZEN=1, WRPTR=0")
    anchor(t)
    wr(t, "sctrctl", U | BPFRZ)
    L.ebreak_win(t, "U", "BPFRZ=1, U enabled, S disabled")
    off(t)
    lab = t.label("fzu")
    t.emit(f"{lab}:", 0)
    rd(t, "x7", "sctrstatus")
    t.check(
        "x7",
        lo(FROZEN) if MUT != "bpfrz_only_enabled_target" else 0,
        lab,
        "U-mode ebreak to S-mode with BPFRZ (S disabled, STE=0): FROZEN=1, WRPTR=0",
    )
    L.deep(t)
    anchor(t)
    wr(t, "sctrctl", S)
    eb, _ = L.ebreak_win(t, "S", "BPFRZ=0", more=[f"csrw {c('sctrctl')}, x0"])
    lab = t.label("nfz")
    t.emit(f"{lab}:", 0)
    rd(t, "x7", "sctrstatus")
    t.emit("srli x7, x7, 31")
    t.emit("andi x7, x7, 1")
    t.check("x7", 0, lab, "BPFRZ=0: FROZEN stays 0")
    L.deep_checks(t, lambda: [L.check_n_ge(t, 1, "BPFRZ=0"), check_entry(t, "BPFRZ=0 ebreak", src=eb, k=0)], "BPFRZ=0")
    t.emit(f"csrw {c('sctrstatus')}, x0")
    return [t]


@rule
def ctr_freeze_bp() -> list[TestFile]:
    t = s_test(
        "ctr_freeze_bp",
        plan="On a breakpoint exception trapping to S-mode with BPFRZ=1, FROZEN is set and "
        "the breakpoint is not recorded: S-mode ebreak and (with C) c.ebreak with sctrctl.S|BPFRZ: FROZEN=1, "
        "no record, and recording stays inhibited afterwards (a jal after the handler returns is not "
        "recorded) until software clears FROZEN (the next jal is recorded). A trap that is not a breakpoint "
        "does not freeze: an SSI taken in S-mode with BPFRZ=1 leaves FROZEN = 0.",
        context=CTX_TRAP,
    )
    for cmp in (False, True):

        def case(cmp: bool = cmp) -> None:
            anchor(t)
            wr(t, "sctrctl", S | BPFRZ)
            lab = t.label("eb")
            t.allow(1)
            if cmp:
                L.rvc(t, [f"{lab}: c.ebreak", "c.nop"])
            else:
                t.emit(f"{lab}: ebreak")
            jal(t, "x0", "jal after the frozen breakpoint")
            off(t)
            t.outcome(BREAK, lab, f"{'c.' if cmp else ''}ebreak with BPFRZ", [0, lab], origin="S")
            lab2 = t.label("fz")
            t.emit(f"{lab2}:", 0)
            rd(t, "x7", "sctrstatus")
            t.check(
                "x7",
                lo(FROZEN) if MUT != "bpfrz_ignored" else 1,
                lab2,
                f"{'c.' if cmp else ''}ebreak with BPFRZ: FROZEN=1, nothing recorded (also not the jal after it)",
            )
            t.li("x6", 0)
            t.emit(f"csrw {c('sctrstatus')}, x6  // FROZEN = 0")
            wr(t, "sctrctl", S | BPFRZ)
            j = jal(t, "x0")
            off(t)
            check_n(t, 1, "after clearing FROZEN")
            check_xfer(t, j, "after clearing FROZEN", logical=0)

        if cmp:
            with t.only_if(C):
                case()
        else:
            case()
    L.deep(t)
    L.s_interrupt(t, "BPFRZ=1, SSI", S | BPFRZ)
    lab = t.label("ssi")
    t.emit(f"{lab}:", 0)
    rd(t, "x7", "sctrstatus")
    t.emit("srli x7, x7, 31")
    t.emit("andi x7, x7, 1")
    t.check("x7", 0, lab, "an SSI with BPFRZ=1 does not set FROZEN")
    t.emit(f"csrw {c('sctrstatus')}, x0")
    return [t]


@rule
def mctrctl_excinh_op() -> list[TestFile]:
    t = s_test(
        "mctrctl_excinh_op",
        plan="EXCINH (bit 33; RV64, probed) inhibits recording of exceptions: with "
        "sctrctl.S|EXCINH, an S-mode ebreak is not the first record after the anchor (the handler's own "
        "transfers may follow); with EXCINH=0 it is. External traps ignore EXCINH (exttrap_def).",
        context=CTX_TRAP,
        rv64=True,
    )
    L.deep(t)
    L.probe_ctl(t, "x8", L.EXCINH)

    def on() -> None:
        anchor(t)
        wr(t, "sctrctl", lo(S | L.EXCINH) if MUT != "excinh_ignored" else S)
        eb, _ = L.ebreak_win(t, "S", "EXCINH=1", more=[f"csrw {c('sctrctl')}, x0"])
        L.deep_checks(t, lambda: L.not_first(t, eb, "EXCINH=1: the ebreak"), "EXCINH=1")

    t.either("x8", on, lambda: None)
    anchor(t)
    wr(t, "sctrctl", S)
    eb, _ = L.ebreak_win(t, "S", "EXCINH=0", more=[f"csrw {c('sctrctl')}, x0"])
    L.deep_checks(
        t, lambda: [L.check_n_ge(t, 1, "EXCINH=0"), check_entry(t, "EXCINH=0 ebreak", src=eb, k=0)], "EXCINH=0"
    )
    return [t]


@rule
def mctrctl_intrinh_op() -> list[TestFile]:
    t = s_test(
        "mctrctl_intrinh_op",
        plan="INTRINH (bit 34; RV64, probed) inhibits recording of interrupts: with "
        "sctrctl.S|INTRINH an SSI taken in S-mode is not the first record (its record would have ctrsource "
        "= the interrupted pc); with INTRINH=0 it is the first record.",
        context=CTX_TRAP,
        rv64=True,
    )
    L.deep(t)
    L.probe_ctl(t, "x8", L.INTRINH)

    def first_is_int(want: int, desc: str) -> None:
        lab = t.label("int")
        t.emit(f"{lab}:", 0)
        L.nrec(t, "x9")
        t.emit("snez x9, x9")
        t.emit("addi x7, x9, -1")
        L.nrec(t, "x6")
        t.emit("addi x6, x6, 0x1ff")
        t.emit("not x7, x7")
        t.emit("and x6, x6, x7")
        t.emit("not x7, x7")
        t.emit("andi x7, x7, 0x200")
        t.emit("or x6, x6, x7  // logical 0 (0x200) when there is no record")
        t.emit(f"csrw {c('siselect')}, x6")
        t.emit(f"csrr x6, {c('sireg')}")
        t.emit("AI_LOG(x15, TRAPLOG_EPC)", 10)
        t.emit("ori x15, x15, 1")
        t.emit("xor x6, x6, x15")
        t.emit("seqz x6, x6")
        t.emit("and x6, x6, x9")
        t.check("x6", want, lab, f"{desc}: the first record is the SSI (ctrsource = sepc | V): {bool(want)}")

    def on() -> None:
        L.s_interrupt(t, "INTRINH=1", lo(S | L.INTRINH) if MUT != "intrinh_ignored" else S)
        L.deep_checks(t, lambda: first_is_int(0, "INTRINH=1"), "INTRINH=1")

    t.either("x8", on, lambda: None)
    L.s_interrupt(t, "INTRINH=0", S)
    L.deep_checks(t, lambda: first_is_int(1, "INTRINH=0"), "INTRINH=0")
    return [t]


# ================================================================ H: vsctrctl, vsiselect, sctrdepth, hstateen0
HREQ = ["I", "S", "H", "Ssctr"]
HSTATEEN0_CTR_BIT = 54


def set_hctr(t: TestFile, on: bool) -> None:
    op = "csrs" if on else "csrc"
    with t.rv64_only():
        t.li("x6", 1)
        t.emit(f"slli x6, x6, {HSTATEEN0_CTR_BIT}")
        t.emit(f"{op} 0x60c, x6  // hstateen0.CTR = {int(on)}")
    with t.rv32_only():
        t.li("x6", 1 << (HSTATEEN0_CTR_BIT - 32))
        t.emit(f"{op} 0x61c, x6  // hstateen0h.CTR = {int(on)}")


def vs_csr_window(t: TestFile, mode: str, line: str, expect: str, desc: str, enc: int | None = None) -> None:
    cause = {"ok": "ok", "illegal": ILLEGAL, "virtual": VIRTUAL}[expect]
    lab = t.label(f"acc_{mode}")
    t.allow(1)
    if mode != t.cur:
        t.enter(mode)
    t.emit(f"{lab}: {line}")
    if mode != t.cur:
        t.leave()
    t.outcome(
        cause, lab, f"{desc} in {mode}-mode", None if expect == "ok" else ([0, enc] if enc else None), origin=mode
    )


def csr_enc(csr: int, f3: int = 2, rd_: int = 7, rs1: int = 0) -> int:
    return (csr << 20) | (rs1 << 15) | (f3 << 12) | (rd_ << 7) | 0x73


FORMS8 = [
    ("csrr x7, {c}", 2, 7, 0),
    ("csrw {c}, x6", 1, 0, 6),
    ("csrrw x7, {c}, x6", 1, 7, 6),
    ("csrrs x7, {c}, x6", 2, 7, 6),
    ("csrrc x7, {c}, x6", 3, 7, 6),
    ("csrrwi x7, {c}, 1", 5, 7, 1),
    ("csrrsi x7, {c}, 0", 6, 7, 0),
    ("csrrci x7, {c}, 1", 7, 7, 1),
]


@rule
def Ssctr_vsctrctl_sz_acc_op() -> list[TestFile]:
    t = s_test(
        "Ssctr_vsctrctl_sz_acc_op",
        plan="H: with sctrctl = S and vsctrctl = U|BPFRZ written in HS-mode, a "
        "VS-mode read of sctrctl returns U|BPFRZ (vsctrctl); a VS-mode write of sctrctl = S|U lands in "
        "vsctrctl (HS reads vsctrctl = S|U) and leaves sctrctl = S. vsctrctl bits 2 and 9 read 0 after "
        "writing all ones. On RV64 a filter bit implemented in vsctrctl (DIRJMPINH, probed in vsctrctl itself: "
        "its optional fields only should match sctrctl's) reads back through sctrctl from VS-mode (64-bit "
        "register).",
        required=HREQ,
    )
    wr(t, "sctrctl", S)
    wr(t, "vsctrctl", U | BPFRZ)
    lab = t.label("vsr")
    t.allow(1)
    t.enter("VS")
    t.emit(f"{lab}: csrr x7, {c('sctrctl')}")
    t.li("x6", S | U)
    t.emit(f"csrw {c('sctrctl')}, x6")
    t.leave()
    t.outcome("ok", lab, "VS-mode sctrctl accesses")
    t.check("x7", U | BPFRZ if MUT != "vs_sees_sctrctl" else S, lab, "VS-mode read of sctrctl returns vsctrctl")
    lab = t.label("hs")
    t.emit(f"{lab}:", 0)
    rd(t, "x7", "vsctrctl")
    t.check("x7", S | U, lab, "the VS-mode write of sctrctl landed in vsctrctl")
    rd(t, "x7", "sctrctl")
    t.check("x7", S, lab, "sctrctl is unchanged by the VS-mode write")
    lab = t.label("ro")
    t.emit(f"{lab}:", 0)
    t.emit("li x6, -1")
    t.emit(f"csrw {c('vsctrctl')}, x6")
    rd(t, "x7", "vsctrctl")
    t.li("x6", M | MTE)
    t.emit("and x7, x7, x6")
    t.check("x7", 0, lab, "vsctrctl all ones: bits 2 and 9 read 0")
    with t.rv64_only():
        L.probe_ctl(t, "x8", L.DIRJMPINH, "vsctrctl")

        def hi() -> None:
            t.load("x6", lo(L.DIRJMPINH | S))
            t.emit(f"csrw {c('vsctrctl')}, x6")
            lab = t.label("hi")
            t.allow(1)
            t.enter("VS")
            t.emit(f"{lab}: csrr x7, {c('sctrctl')}")
            t.leave()
            t.outcome("ok", lab, "VS-mode read of sctrctl bit 43")
            t.check("x7", lo(L.DIRJMPINH | S), lab, "vsctrctl bit 43 (DIRJMPINH) is visible from VS-mode")

        t.either("x8", hi, lambda: None)
    off(t, "vsctrctl")
    off(t)
    return [t]


@rule
def vsctrctl_s_op() -> list[TestFile]:
    t = s_test(
        "vsctrctl_s_op",
        plan="vsctrctl.S enables recording in VS-mode: with vsctrctl.S and sctrctl = 0, a "
        "VS-mode jal is the only record; with vsctrctl = 0 and sctrctl = S|U (V=0 enables), a VS-mode jal "
        "is not recorded (only the sret/ecall partial records, checked to differ from the jal); with "
        "vsctrctl.U only, a VS-mode jal is not recorded.",
        context=CTX_MEASURE,
        required=HREQ,
    )
    anchor(t)
    wr(t, "vsctrctl", S)
    (j,), _, _ = win(t, "VS", lambda: [jal(t, "x6")], desc="vsctrctl.S")
    off(t, "vsctrctl")
    check_n(t, 1, "vsctrctl.S: VS jal")
    check_xfer(t, j, "vsctrctl.S", logical=0)
    anchor(t)
    wr(t, "vsctrctl", U)
    win(t, "VS", lambda: [jal(t, "x6")], desc="vsctrctl.U only")
    off(t, "vsctrctl")
    check_n(t, 0 if MUT != "vs_s_ignored" else 1, "vsctrctl.U only: VS jal")
    L.deep(t)
    anchor(t)
    wr(t, "sctrctl", S | U)
    (j2,), _, _ = win(t, "VS", lambda: [jal(t, "x6")], desc="sctrctl.S|U, vsctrctl=0")
    off(t)
    L.deep_checks(t, lambda: L.not_first(t, j2.src, "sctrctl.S|U, vsctrctl=0: the VS-mode jal"), "VS jal")
    return [t]


@rule
def vsctrctl_u_op() -> list[TestFile]:
    t = s_test(
        "vsctrctl_u_op",
        plan="vsctrctl.U enables recording in VU-mode: with vsctrctl.U and sctrctl = 0, a "
        "VU-mode jal is the only record; with sctrctl.U only, vsctrctl = 0, a VU-mode jal is not recorded "
        "(no records: HS is disabled too); with vsctrctl.S only, not recorded either.",
        context=CTX_MEASURE,
        required=HREQ,
    )
    anchor(t)
    wr(t, "vsctrctl", U)
    (j,), _, _ = win(t, "VU", lambda: [jal(t, "x6")], desc="vsctrctl.U")
    off(t, "vsctrctl")
    check_n(t, 1, "vsctrctl.U: VU jal")
    check_xfer(t, j, "vsctrctl.U", logical=0)
    anchor(t)
    wr(t, "sctrctl", U)
    win(t, "VU", lambda: [jal(t, "x6")], desc="sctrctl.U only")
    off(t)
    check_n(t, 0 if MUT != "vu_uses_sctrctl_u" else 1, "sctrctl.U only: VU jal")
    anchor(t)
    wr(t, "vsctrctl", S)
    win(t, "VU", lambda: [jal(t, "x6")], desc="vsctrctl.S only")
    off(t, "vsctrctl")
    check_n(t, 0 if MUT != "vu_uses_vs_s" else 1, "vsctrctl.S only: VU jal (HS disabled, VS not involved)")
    return [t]


@rule
def vsctrctl_ste_op() -> list[TestFile]:
    t = s_test(
        "vsctrctl_ste_op",
        plan="vsctrctl.STE enables recording of traps to VS-mode while vsctrctl.S=0. VS-mode "
        "software writes its own sctrctl (= vsctrctl) = U|STE; HS then reads vsctrctl = U|STE (STE probed); "
        "a VU-mode ebreak delegated to VS (hedeleg[3]=1) is recorded as an external trap (target 0), and "
        "the GOTO ecall to HS is not (sctrctl.STE=0). With vsctrctl = U only, nothing is recorded.",
        context=CTX_EXT,
        required=HREQ,
    )
    L.probe_ctl(t, "x8", STE, "vsctrctl")

    def on() -> None:
        lab = t.label("vsw")
        t.allow(1)
        t.enter("VS")
        t.li("x6", U | STE)
        t.emit(f"{lab}: csrw {c('sctrctl')}, x6  // VS-mode write: vsctrctl = U|STE")
        t.leave()
        t.outcome("ok", lab, "VS-mode write of sctrctl")
        rd(t, "x7", "vsctrctl")
        t.check("x7", U | STE, lab, "vsctrctl = U|STE written from VS-mode")
        h_deleg(t, True)
        anchor(t)
        eb, _ = L.ebreak_win(t, "VU", "vsctrctl.STE")
        off(t, "vsctrctl")
        h_deleg(t, False)
        check_n(t, 1 if MUT != "vs_ste_ignored" else 0, "vsctrctl.U|STE: VU ebreak to VS")
        check_entry(t, "VU ebreak to VS (external)", src=eb, tgt=0, typ=L.T_EXC, logical=0)

    t.either("x8", on, lambda: None)
    ext_case(t, "VU", 0, U, True, 0, "vsctrctl.STE=0")
    return [t]


def frozen_is(t: TestFile, want: int, desc: str) -> None:
    lab = t.label("fz")
    t.emit(f"{lab}:", 0)
    rd(t, "x7", "sctrstatus")
    t.emit("srli x7, x7, 31")
    t.emit("andi x7, x7, 1")
    t.check("x7", want, lab, f"{desc}: sctrstatus.FROZEN = {want}")
    t.emit(f"csrw {c('sctrstatus')}, x0")


@rule
def vsctrctl_bpfrz_op() -> list[TestFile]:
    t = s_test(
        "vsctrctl_bpfrz_op",
        plan="vsctrctl.BPFRZ freezes CTR on a breakpoint that traps to VS-mode: VU-mode "
        "ebreak with hedeleg[3]=1 and vsctrctl.U|S|BPFRZ: FROZEN=1 and nothing recorded (the sret from the "
        "disabled HS-mode is not recorded either). With vsctrctl.U|S and sctrctl.BPFRZ=1 instead, the same "
        "breakpoint does not freeze (sctrctl.BPFRZ governs traps to HS/M only).",
        context=CTX_TRAP,
        required=HREQ,
    )
    h_deleg(t, True)
    anchor(t)
    wr(t, "vsctrctl", U | S | BPFRZ)
    L.ebreak_win(t, "VU", "vsctrctl.BPFRZ=1")
    off(t, "vsctrctl")
    lab = t.label("fz")
    t.emit(f"{lab}:", 0)
    rd(t, "x7", "sctrstatus")
    t.check(
        "x7",
        lo(FROZEN) if MUT != "vs_bpfrz_ignored" else 0,
        lab,
        "VU ebreak to VS with vsctrctl.BPFRZ: FROZEN=1, no record",
    )
    t.emit(f"csrw {c('sctrstatus')}, x0")
    anchor(t)
    wr(t, "sctrctl", BPFRZ)
    wr(t, "vsctrctl", U | S)
    L.ebreak_win(t, "VU", "sctrctl.BPFRZ=1 only")
    off(t, "vsctrctl")
    off(t)
    frozen_is(t, 0 if MUT != "vs_bpfrz_uses_sctrctl" else 1, "VU ebreak to VS with only sctrctl.BPFRZ")
    h_deleg(t, False)
    return [t]


@rule
def ctr_freeze_vs() -> list[TestFile]:
    t = s_test(
        "ctr_freeze_vs",
        plan="For breakpoints that trap to VS-mode, vsctrctl.BPFRZ decides the freeze; for "
        "those that trap from VS-mode to HS-mode, sctrctl.BPFRZ does. H, VS-mode ebreak:\n"
        "1. hedeleg[3]=1 (to VS): vsctrctl.S|BPFRZ, sctrctl.BPFRZ=0: FROZEN=1; vsctrctl.S, sctrctl.BPFRZ=1: "
        "FROZEN=0.\n"
        "2. hedeleg[3]=0 (to HS): vsctrctl.S|BPFRZ, sctrctl = S: FROZEN=0; vsctrctl.S, sctrctl = S|BPFRZ: "
        "FROZEN=1.\n"
        "3. VU-mode ebreak to HS-mode (hedeleg[3]=0, a virtualization transition): vsctrctl.U|BPFRZ, "
        "sctrctl = S: FROZEN=0; vsctrctl.U, sctrctl = S|BPFRZ: FROZEN=1.\n"
        "LCOFIs that trap to VS-mode (vsctrctl.LCOFIFRZ) are in vsctrctl_lcofifrz_op_Sm.",
        context=CTX_TRAP,
        required=HREQ,
    )
    for mode, deleg, vbp, sbp, want in (
        ("VS", True, 1, 0, 1),
        ("VS", True, 0, 1, 0),
        ("VS", False, 1, 0, 0),
        ("VS", False, 0, 1, 1),
        ("VU", False, 1, 0, 0),
        ("VU", False, 0, 1, 1),
    ):
        h_deleg(t, deleg)
        anchor(t)
        wr(t, "vsctrctl", (S if mode == "VS" else U) | BPFRZ * vbp)
        wr(t, "sctrctl", (S if not deleg else 0) | BPFRZ * sbp)
        d = f"{mode} ebreak to {'VS' if deleg else 'HS'}, vsctrctl.BPFRZ={vbp}, sctrctl.BPFRZ={sbp}"
        L.ebreak_win(t, mode, d)
        off(t)
        off(t, "vsctrctl")
        if deleg:
            h_deleg(t, False)
        w = want if MUT != "freeze_vs_wrong_ctl" else 1 - want
        frozen_is(t, w, d)
    return [t]


@rule
def vsiselect_op() -> list[TestFile]:
    t = s_test(
        "vsiselect_op",
        plan="vsiselect 0x200..0x2FF reaches the same entries as siselect (no separate V=1 "
        "set): HS writes entry 0 through siselect/sireg; VS-mode (siselect = vsiselect = 0x200) reads the "
        "same ctrsource/ctrtarget via sireg/sireg2 (= vsireg*), and writes entry 1; HS reads entry 1 through "
        "siselect and through vsiselect/vsireg directly. vsireg4..6 read 0. A jal recorded in HS-mode is "
        "visible from VS-mode at logical 0.",
        context=CTX_MEASURE,
        required=HREQ,
    )
    wr(t, "sctrctl", 0)
    sctrclr(t)
    L.select(t, logical=0)
    t.la("x6", "ctr_pa")
    t.emit("ori x6, x6, 1")
    t.emit(f"csrw {c('sireg')}, x6")
    t.la("x6", "ctr_pb")
    t.emit(f"csrw {c('sireg2')}, x6")
    lab = t.label("vs")
    t.allow(1)
    t.enter("VS")
    t.emit(f"{lab}: li x6, 0x200")
    t.emit(f"csrw {c('siselect')}, x6")
    t.emit(f"csrr x7, {c('sireg')}")
    t.emit(f"csrr x8, {c('sireg2')}")
    t.emit(f"csrr x9, {c('sireg4')}")
    t.emit("li x6, 0x201")
    t.emit(f"csrw {c('siselect')}, x6")
    t.la("x6", "ctr_pb")
    t.emit("ori x6, x6, 1")
    t.emit(f"csrw {c('sireg')}, x6")
    t.leave()
    t.outcome("ok", lab, "VS-mode vsiselect/vsireg accesses")
    t.check("x7", "ctr_pa+1", lab, "VS-mode sireg (vsireg) reads the ctrsource HS wrote to entry 0")
    t.check("x8", "ctr_pb", lab, "VS-mode sireg2 (vsireg2) reads the ctrtarget HS wrote")
    t.check("x9", 0, lab, "VS-mode sireg4 (vsireg4) reads 0")
    lab = t.label("hs")
    t.emit(f"{lab}:", 0)
    L.select(t, logical=1)
    t.emit(f"csrr x7, {c('sireg')}")
    t.check("x7", "ctr_pb+1" if MUT != "vs_entries_separate" else 0, lab, "HS-mode sireg reads the entry VS-mode wrote")
    t.li("x6", 0x201)
    t.emit(f"csrw {c('vsiselect')}, x6")
    t.emit(f"csrr x7, {c('vsireg')}")
    t.check("x7", "ctr_pb+1", lab, "HS-mode vsireg with vsiselect = 0x201 reads the same entry")
    t.emit(f"csrr x7, {c('vsireg5')}")
    t.check("x7", 0, lab, "HS-mode vsireg5 reads 0")
    anchor(t)
    wr(t, "sctrctl", S)
    j = jal(t, "x0")
    off(t)
    lab = t.label("vsr")
    t.allow(1)
    t.enter("VS")
    t.emit(f"{lab}: li x6, 0x200")
    t.emit(f"csrw {c('siselect')}, x6")
    t.emit(f"csrr x7, {c('sireg')}")
    t.leave()
    t.outcome("ok", lab, "VS-mode read of logical 0")
    t.check("x7", f"{j.src}+1", lab, "VS-mode sees the HS-mode record at logical 0")
    t.extra_data.append(".p2align 2\nctr_pa: .word 0\nctr_pb: .word 0")
    return [t]


@rule
def sctrdepth_mode() -> list[TestFile]:
    t = s_test(
        "sctrdepth_mode",
        plan="Every CSR instruction form on sctrdepth raises virtual-instruction in VS-mode "
        "and in VU-mode (xtval 0 or the instruction), with hstateen0.CTR = 1 and also (Ssstateen) = 0 "
        "(sctrdepth is outside hstateen0.CTR's control); HS-mode access works; U-mode access raises "
        "illegal-instruction. mstateen0.CTR = 0 (illegal) is in sctrdepth_mode_Sm.",
        required=HREQ,
    )
    win(t, "S", lambda: t.emit(f"csrr x7, {c('sctrdepth')}"), "ok", "sctrdepth read")
    vs_csr_window(t, "U", f"csrr x7, {c('sctrdepth')}", "illegal", "sctrdepth read", csr_enc(0x15F))
    for mode in ("VS", "VU"):
        for form, f3, rdn, rs1 in FORMS8:
            exp = "virtual" if MUT != "sctrdepth_vs_ok" or mode != "VS" else "ok"
            vs_csr_window(
                t,
                mode,
                form.format(c=c("sctrdepth")),
                exp,
                f"{form.split()[0]} sctrdepth",
                csr_enc(0x15F, f3, rdn, rs1),
            )
    with t.only_if("defined(SSSTATEEN_SUPPORTED)"):
        set_hctr(t, False)
        vs_csr_window(
            t, "VS", f"csrr x7, {c('sctrdepth')}", "virtual", "sctrdepth read, hstateen0.CTR=0", csr_enc(0x15F)
        )
        set_hctr(t, True)
    return [t]


VS_STATE = [("sctrctl", 0x14E), ("sctrstatus", 0x14F)]


def vs_state_accesses(t: TestFile, expect: str, desc: str) -> None:
    for name, num in VS_STATE:
        vs_csr_window(t, "VS", f"csrr x7, {c(name)}", expect, f"read {name} ({desc})", csr_enc(num))
        vs_csr_window(t, "VS", f"csrw {c(name)}, x0", expect, f"write {name} ({desc})", csr_enc(num, 1, 0, 0))
    for n in ("sireg", "sireg2", "sireg3", "sireg6"):
        lab = t.label("ind")
        t.allow(1)
        t.enter("VS")
        t.li("x6", 0x2FF)
        t.emit(f"csrw {c('siselect')}, x6  // vsiselect = 0x2FF (allowed: CSRIND)")
        t.emit(f"{lab}: csrr x7, {c(n)}")
        t.leave()
        cause = {"ok": "ok", "virtual": VIRTUAL, "illegal": ILLEGAL}[expect]
        t.outcome(
            cause,
            lab,
            f"read {n} with siselect 0x2FF ({desc}) in VS-mode",
            None if expect == "ok" else [0, csr_enc(CSR_NUM[n])],
            origin="VS",
        )


CSR_NUM = L.CSR


@rule
def hstateen_vs() -> list[TestFile]:
    t = s_test(
        "hstateen_vs",
        plan="With mstateen0.CTR=1 (framework): hstateen0.CTR=1: VS-mode reads and writes of "
        "sctrctl (vsctrctl) and sctrstatus, reads of sireg/sireg2/sireg3/sireg6 with siselect = 0x2FF, and "
        "SCTRCLR do not trap; hstateen0.CTR=0: each of them raises virtual-instruction (xtval 0 or the "
        "instruction). sctrdepth stays virtual-instruction either way (sctrdepth_mode).",
        required=["I", "S", "H", "Ssctr", "Ssstateen"],
    )
    set_hctr(t, True)
    vs_state_accesses(t, "ok", "hstateen0.CTR=1")
    vs_csr_window(t, "VS", f".word 0x{L.SCTRCLR:08x}", "ok", "SCTRCLR (hstateen0.CTR=1)")
    set_hctr(t, False)
    vs_state_accesses(t, "virtual" if MUT != "hstateen_ignored" else "ok", "hstateen0.CTR=0")
    vs_csr_window(
        t,
        "VS",
        f".word 0x{L.SCTRCLR:08x}",
        "virtual" if MUT != "hstateen_illegal" else "illegal",
        "SCTRCLR (hstateen0.CTR=0)",
        L.SCTRCLR,
    )
    set_hctr(t, True)
    return [t]


@rule
def hstateen_ctr() -> list[TestFile]:
    t = s_test(
        "hstateen_ctr",
        plan="hstateen0.CTR controls V=1 access to the supervisor CTR state only: with "
        "hstateen0.CTR=0, HS-mode accesses to sctrctl, vsctrctl, sctrstatus, sireg* (siselect 0x200) and "
        "SCTRCLR still work, VS-mode reads of sctrctl and sireg (vsiselect 0x200) raise virtual-instruction, "
        "and the bit reads back 0 then 1 when written. hstateen0.CTR read-only 0 with mstateen0.CTR=0 is in "
        "hstateen_ctr_Sm.",
        required=["I", "S", "H", "Ssctr", "Ssstateen"],
    )
    set_hctr(t, False)
    for line in (
        f"csrr x7, {c('sctrctl')}",
        f"csrr x7, {c('vsctrctl')}",
        f"csrr x7, {c('sctrstatus')}",
        f"csrr x7, {c('sireg')}",
        f".word 0x{L.SCTRCLR:08x}",
    ):
        L.select(t, logical=0)
        vs_csr_window(t, "S", line, "ok", f"HS-mode {line.split('//')[0]} with hstateen0.CTR=0")
    vs_csr_window(t, "VS", f"csrr x7, {c('sctrctl')}", "virtual", "read sctrctl, hstateen0.CTR=0", csr_enc(0x14E))
    lab = t.label("rb")
    t.emit(f"{lab}:", 0)
    with t.rv64_only():
        t.emit("csrr x7, 0x60c")
        t.emit(f"srli x7, x7, {HSTATEEN0_CTR_BIT}")
    with t.rv32_only():
        t.emit("csrr x7, 0x61c")
        t.emit(f"srli x7, x7, {HSTATEEN0_CTR_BIT - 32}")
    t.emit("andi x7, x7, 1")
    t.check("x7", 0, lab, "hstateen0.CTR reads 0 after clearing")
    set_hctr(t, True)
    with t.rv64_only():
        t.emit("csrr x7, 0x60c")
        t.emit(f"srli x7, x7, {HSTATEEN0_CTR_BIT}")
    with t.rv32_only():
        t.emit("csrr x7, 0x61c")
        t.emit(f"srli x7, x7, {HSTATEEN0_CTR_BIT - 32}")
    t.emit("andi x7, x7, 1")
    t.check("x7", 1, lab, "hstateen0.CTR reads 1 after setting (mstateen0.CTR=1)")
    vs_csr_window(t, "VS", f"csrr x7, {c('sctrctl')}", "ok", "read sctrctl, hstateen0.CTR=1")
    return [t]


@rule
def hstateen0_ctr0_v1_op() -> list[TestFile]:
    t = s_test(
        "hstateen0_ctr0_v1_op",
        plan="With hstateen0.CTR=0, transfers in VS-mode and VU-mode are still "
        "recorded: vsctrctl.S then vsctrctl.U (written in HS-mode), a VS-mode jal and a VU-mode jal are the only two "
        "records, and sctrstatus.WRPTR moves.",
        context=CTX_MEASURE,
        required=["I", "S", "H", "Ssctr", "Ssstateen"],
    )
    set_hctr(t, False)
    anchor(t)
    wr(t, "vsctrctl", S)
    (j1,), _, _ = win(t, "VS", lambda: [jal(t, "x6")], desc="hstateen0.CTR=0")
    wr(t, "vsctrctl", U)
    (j2,), _, _ = win(t, "VU", lambda: [jal(t, "x6")], desc="hstateen0.CTR=0")
    off(t, "vsctrctl")
    set_hctr(t, True)
    rec = [j1, j2] if MUT != "hstateen_stops_recording" else []
    check_n(t, len(rec), "hstateen0.CTR=0")
    for i, x in enumerate(reversed(rec)):
        check_xfer(t, x, "hstateen0.CTR=0", logical=i)
    return [t]


# ================================================================ RASEMU
def rasemu_or_skip(t: TestFile, on: Callable[[], None]) -> None:
    L.probe_ctl(t, "x8", RASEMU)
    t.either("x8", on, lambda: None)


@rule
def mctrctl_rasemu_op() -> list[TestFile]:
    t = s_test(
        "mctrctl_rasemu_op",
        plan="RASEMU (optional, probed) enables RAS emulation. With sctrctl.S|RASEMU: "
        "call A (jal x1), a jal x0, a taken branch, call B (jalr x1), return (jalr x0, x1): only calls are "
        "recorded and the return pops B, so WRPTR = 1 and logical entry 0 is call A; the popped entry (now "
        "logical D-1) has V=0. Without RASEMU the same run records all five.",
        context=CTX_MEASURE,
    )
    L.depth_pick(t, largest=False, reg="x1")

    def body() -> list[Xfer]:
        return [jal(t, "x1"), jal(t, "x0"), L.branch(t, "beq", 0, 0), L.jalr(t, "x1", "x6"), L.jalr(t, "x0", "x1")]

    def on() -> None:
        anchor(t)
        wr(t, "sctrctl", S | RASEMU)
        xs = body()
        off(t)
        check_n(t, 1 if MUT != "rasemu_no_pop" else 2, "RASEMU: call, jump, branch, call, return")
        check_xfer(t, xs[0], "RASEMU: call A remains", logical=0)
        rd(t, "x1", "sctrdepth")
        t.emit("andi x1, x1, 7  // DEPTH (read, not rewritten: a depth change would leave WRPTR unspecified)")
        L.depth_entries(t, "x1", "x1")
        lab = t.label("pop")
        t.emit(f"{lab}:", 0)
        t.emit("addi x6, x1, 0x1ff")
        t.emit(f"csrw {c('siselect')}, x6")
        t.emit(f"csrr x7, {c('sireg')}")
        t.emit("andi x7, x7, 1")
        t.check("x7", 0, lab, "RASEMU: the popped call (logical D-1) has V=0")

    rasemu_or_skip(t, on)
    record_s(t, S, body, "RASEMU=0")
    return [t]


@rule
def ctrctl_rasemu_op() -> list[TestFile]:
    t = s_test(
        "ctrctl_rasemu_op",
        plan="RAS emulation (RASEMU probed; smallest depth D):\n"
        "1. Calls are recorded as normal (direct and indirect: jal x5, jalr x1).\n"
        "2. A return pops: WRPTR decrements and the entry at the new WRPTR gets V=0; from WRPTR = 0 a return "
        "wraps WRPTR to D-1.\n"
        "3. A co-routine swap (jalr x1, x5) overwrites logical entry 0 with its own record and leaves WRPTR "
        "unchanged.\n"
        "4. Other types are inhibited: jal x0, jalr x0 (x6), jal x6, a taken branch, an sret.\n"
        "5. The filter bits are ignored (RV64: DIRCALLINH set where implemented still records the call) and "
        "STE is ignored (sctrctl.U|RASEMU|STE: a U-mode ebreak, an external trap, is not recorded).",
        context=CTX_MEASURE,
    )

    def on() -> None:
        L.depth_pick(t, largest=False, reg="x1")
        anchor(t)
        wr(t, "sctrctl", lo(S | RASEMU | L.DIRCALLINH))
        c1 = jal(t, "x5")
        c2 = L.jalr(t, "x1", "x6")
        for x in (jal(t, "x0"), L.jalr(t, "x0", "x6"), jal(t, "x6"), L.branch(t, "bne", 0, 1), L.sret_s(t)):
            del x
        off(t)
        check_n(t, 2, "RASEMU: two calls, inhibited types")
        check_xfer(t, c2, "RASEMU", logical=0)
        check_xfer(t, c1, "RASEMU", logical=1)
        wr(t, "sctrctl", S | RASEMU)
        sw = L.jalr(t, "x1", "x5")
        off(t)
        check_n(t, 2 if MUT != "swap_pushes" else 3, "RASEMU: co-routine swap keeps WRPTR")
        check_entry(t, "RASEMU: the swap overwrote logical 0", src=sw.src, tgt=sw.tgt, logical=0)
        check_xfer(t, c1, "RASEMU: the older call stays", logical=1)
        wr(t, "sctrctl", S | RASEMU)
        L.jalr(t, "x0", "x1")
        L.jalr(t, "x0", "x5")
        off(t)
        check_n(t, 0, "RASEMU: two returns pop both")
        lab = t.label("v")
        t.emit(f"{lab}:", 0)
        rd(t, "x8", "sctrdepth")
        t.emit("andi x8, x8, 7")
        L.depth_entries(t, "x8", "x8")
        for k in (1, 2):
            t.emit(f"addi x6, x8, {0x200 - k}  // logical D-{k}: physical entry {2 - k}, popped")
            t.emit(f"csrw {c('siselect')}, x6")
            t.emit(f"csrr x7, {c('sireg')}")
            t.emit("andi x7, x7, 1")
            t.check(
                "x7",
                0 if MUT != "pop_keeps_v" else 1,
                lab,
                f"RASEMU: the call popped from physical entry {2 - k} (now logical D-{k}) has V=0",
            )
        wr(t, "sctrctl", S | RASEMU)
        L.jalr(t, "x0", "x1")
        off(t)
        lab = t.label("wrap")
        t.emit(f"{lab}:", 0)
        rd(t, "x8", "sctrdepth")
        t.emit("andi x8, x8, 7")
        L.depth_entries(t, "x8", "x8")
        L.nrec(t, "x7")
        t.emit("addi x8, x8, -1")
        t.emit("xor x7, x7, x8")
        t.emit("seqz x7, x7")
        t.check_bool("x7", lab, "RASEMU: a return at WRPTR = 0 wraps WRPTR to D-1")
        L.probe_ctl(t, "x8", STE)
        anchor(t)
        t.emit("slli x8, x8, 0")
        t.emit(f"ori x8, x8, {U | RASEMU}")
        t.emit(f"csrw {c('sctrctl')}, x8  // U | RASEMU | STE (if implemented)")
        L.ebreak_win(t, "U", "RASEMU, STE")
        off(t)
        check_n(t, 0 if MUT != "rasemu_keeps_ste" else 2, "RASEMU ignores STE: no external trap record")

    rasemu_or_skip(t, on)
    return [t]


# ================================================================ custom bits
@rule
def mctrctl_custom_op() -> list[TestFile]:
    t = s_test(
        "mctrctl_custom_op",
        plan="Custom[3:0] (bits 63:60, RV64) are WARL and 0 is standard behaviour: after "
        "writing all ones, writing 0 reads Custom = 0, and with Custom = 0 an S-mode jal is recorded "
        "normally (sctrctl.S).",
        context=CTX_MEASURE,
        rv64=True,
    )
    lab = t.label("cu")
    t.emit(f"{lab}:", 0)
    t.load("x6", lo(CUSTOM))
    t.emit(f"csrw {c('sctrctl')}, x6")
    t.emit(f"csrw {c('sctrctl')}, x0")
    rd(t, "x7", "sctrctl")
    t.emit("srli x7, x7, 60")
    t.check("x7", 0, lab, "Custom reads 0 after writing 0")
    record_s(t, S, lambda: [jal(t, "x0")], "Custom = 0")
    return [t]


@rule
def ctr_custom_bits() -> list[TestFile]:
    t = s_test(
        "ctr_custom_bits",
        plan="With the custom bits 0, CTR is standard: after writing Custom all ones and "
        "back to 0 (RV64), the undefined bits of sctrstatus and ctrdata read 0 after writes of all ones, "
        "and a recorded jal has standard ctrsource/ctrtarget/ctrdata (WPRI 0).",
        context=CTX_MEASURE,
        rv64=True,
    )
    t.load("x6", lo(CUSTOM))
    t.emit(f"csrw {c('sctrctl')}, x6")
    t.emit(f"csrw {c('sctrctl')}, x0")
    lab = t.label("st")
    t.emit(f"{lab}:", 0)
    t.emit("li x6, -1")
    t.emit(f"csrw {c('sctrstatus')}, x6")
    rd(t, "x7", "sctrstatus")
    t.load("x6", X(0x7FFFFF00, 0xFFFFFFFF7FFFFF00))
    t.emit("and x7, x7, x6")
    t.check("x7", 0, lab, "Custom = 0: sctrstatus undefined bits read 0")
    t.emit(f"csrw {c('sctrstatus')}, x0")
    L.select(t, logical=0)
    t.emit("li x6, -1")
    t.emit(f"csrw {c('sireg3')}, x6")
    t.emit(f"csrr x8, {c('sireg3')}")
    t.check_masked("x8", CTRDATA_WPRI, 0, lab, "Custom = 0: ctrdata undefined bits read 0")
    record_s(t, S, lambda: [jal(t, "x6")], "Custom = 0")
    return [t]


# ================================================================ retirement (Sdtrig)
@rule
def ctr_behavior_criteria_retires() -> list[TestFile]:
    t = s_test(
        "ctr_behavior_criteria_retires",
        plan="A transfer that does not retire is not recorded. An "
        "mcontrol6 execute trigger (Sdtrig, set through T-SBI: tselect 0, tdata2 = the address of a jal, "
        "tdata1 = type 6, S=1, execute=1, action 0) raises a breakpoint before the jal executes; the "
        "framework handler resumes after it. With sctrctl.S (BPFRZ=0) the first record after the anchor is "
        "the breakpoint exception (ctrsource = the jal pc, ctrtarget = the stvec handler), not the jal "
        "(whose target is the next label). sstatus.SIE is 1 around the jal, since Sdtrig lets an "
        "implementation suppress S-mode breakpoints while SIE=0 (reentrancy). If the trigger cannot be configured (tdata1 reads back without "
        "type 6 / execute), the test checks nothing.",
        context=CTX_TRAP,
        required=["I", "S", "Ssctr", "Sdtrig"],
    )
    L.deep(t)
    t.li("a1", 0)
    t.tsbi_csr("WRITE", "TSELECT", "a1")
    jl = t.label("tj")
    t.la("a1", jl)
    t.tsbi_csr("WRITE", "TDATA2", "a1")
    t.load("a1", X((6 << 28) | 0x14, (6 << 60) | 0x14), "mcontrol6: type 6, S=1, execute=1, action 0")
    t.tsbi_csr("WRITE", "TDATA1", "a1")
    t.tsbi_csr("READ", "TDATA1")
    t.emit("mv x8, a0")
    t.load("x6", X((0xF << 28) | 0x14, (0xF << 60) | 0x14))
    t.emit("and x8, x8, x6")
    t.load("x6", X((6 << 28) | 0x14, (6 << 60) | 0x14))
    t.emit("xor x8, x8, x6")
    t.emit("seqz x8, x8  // trigger configured")

    def on() -> None:
        anchor(t)
        wr(t, "sctrctl", S)
        t.emit("csrsi sstatus, 2  // SIE = 1: breakpoint reentrancy may suppress S-mode triggers while SIE = 0")
        t.allow(1)
        t.emit(f"{jl}: jal x0, {jl}_t")
        t.emit(f"{jl}_t:", 0)
        off(t)
        t.emit("csrci sstatus, 2")
        t.outcome(BREAK, jl, "execute trigger on a jal", [0, jl], origin="S")
        L.deep_checks(
            t,
            lambda: [
                L.check_n_ge(t, 1, "trigger"),
                check_entry(t, "the breakpoint, not the jal", src=jl, typ=L.T_EXC, k=0),
                L.check_tgt_handler(t, "the breakpoint"),
            ],
            "trigger",
        )

    t.either("x8", on, lambda: None)
    t.li("a1", 0)
    t.tsbi_csr("WRITE", "TDATA1", "a1")
    return [t]


# ================================================================ cycle counting
CTX_CYC = CTX_MEASURE + " " + L.CYC_NOTE
CYC_REQ = ["I", "S", "Ssctr", "Zicntr"]
CC_BITS = 0xFFFF0000
CCV = 1 << 15


def cyc_test(name: str, plan: str) -> TestFile:
    t = s_test(name, plan=plan, context=CTX_CYC, required=CYC_REQ)
    L.cyc_setup(t)
    off(t)
    L.cc_probe(t)
    return t


def ccv_probe(t: TestFile, out: str = "x9") -> None:
    """out = ctrdata bits 31:15 (CC and CCV) that hold 1 after writing all ones to logical entry 0's ctrdata."""
    t.emit("li x6, 0x200")
    t.emit(f"csrw {c('siselect')}, x6")
    t.li("x6", -0x8000)
    t.emit(f"csrw {c('sireg3')}, x6")
    t.emit(f"csrr {out}, {c('sireg3')}")
    t.load("x6", X(0xFFFF8000, 0xFFFF8000))
    t.emit(f"and {out}, {out}, x6")
    t.emit(f"csrw {c('sireg3')}, x0")


@rule
def ctrdata_cc_supported() -> list[TestFile]:
    t = cyc_test(
        "ctrdata_cc_supported",
        plan="CC is optional; when a record has CCV=1 its CC is the number of cycles "
        "since the prior record: record A, 200 nops, record B (sctrctl.S): B's decoded CC lies within the "
        "cycle-CSR brackets (or CC is saturated).",
    )
    L.cc_pair(t, 200)
    L.cc_check(t, "200-nop gap")
    return [t]


@rule
def ctr_ccounter_inc() -> list[TestFile]:
    t = cyc_test(
        "ctr_ccounter_inc",
        plan="The counter counts mcycle-rate cycles only while CTR is active: (1) A, 300 "
        "nops, B: B's CC within the brackets; (2) A, 100 nops, FROZEN=1 for 400 nops, FROZEN=0, 100 nops, B: "
        "B's CC within the brackets less the frozen interval (inactive cycles are not counted); (3) A, 5000 "
        "nops, B: the exponent encoding (CCE > 0 when implemented) decodes within the brackets.",
    )
    L.cc_pair(t, 300)
    L.cc_check(t, "300-nop gap")
    L.cc_pair(t, 100, frozen=400)
    L.cc_check(t, "frozen interval not counted", frozen_slots=(4, 5), frozen_lower=MUT != "cc_counts_frozen")
    L.cc_pair(t, 5000)
    L.cc_check(t, "5000-nop gap")
    return [t]


def ccv_after(t: TestFile, how: str, desc: str) -> None:
    """Record A, 300 nops, then `how` (rewrite sctrctl or SCTRCLR), record B: B has CCV = 0."""
    anchor(t)
    wr(t, "sctrctl", S)
    jal(t, "x0", "A")
    L.delay(t, 300)
    if how == "ctl":
        wr(t, "sctrctl", S, note="sctrctl = S again (a write)")
    else:
        sctrclr(t)
    j = jal(t, "x0", "B")
    off(t)
    lab = check_entry(t, desc, src=j.src, tgt=j.tgt, logical=0)
    t.emit("srli x8, x8, 15")
    t.emit("andi x8, x8, 1")
    t.check("x8", 0 if MUT != "ccv_survives_reset" else 1, lab, f"{desc}: CCV = 0")


@rule
def ctr_ccounter_reset() -> list[TestFile]:
    t = cyc_test(
        "ctr_ccounter_reset",
        plan="Writes to sctrctl and SCTRCLR reset the counter, so the next record has "
        "CCV=0: A, 300 nops, sctrctl rewritten with the same value, B: B.CCV=0; the same with SCTRCLR. Then "
        "a normal pair (no reset between) has CC within the brackets when CCV=1.",
    )
    ccv_after(t, "ctl", "write of sctrctl between A and B")
    ccv_after(t, "clr", "SCTRCLR between A and B")
    L.cc_pair(t, 200)
    L.cc_check(t, "no reset between A and B")
    return [t]


@rule
def ctr_ccounter_ccv() -> list[TestFile]:
    t = cyc_test(
        "ctr_ccounter_ccv",
        plan="CC is valid only when CCV=1, and the next record after a write to "
        "sctrctl or SCTRCLR has CCV=0: both cases give CCV=0; a pair without a reset has CCV=0 or a CC "
        "within the brackets.",
    )
    ccv_after(t, "clr", "SCTRCLR between A and B")
    ccv_after(t, "ctl", "write of sctrctl between A and B")
    L.cc_pair(t, 150)
    L.cc_check(t, "no reset between A and B")
    return [t]


@rule
def ctrdata_ccv() -> list[TestFile]:
    t = cyc_test(
        "ctrdata_ccv",
        plan="CCV marks a valid CC: in a pair with a 50-nop gap, CCV=1 implies the decoded CC "
        "is within the brackets; the first record after the anchor's SCTRCLR has CCV=0.",
    )
    L.cc_pair(t, 50)
    L.cc_check(t, "50-nop gap")
    lab = t.label("a")
    t.emit(f"{lab}:", 0)
    L.select(t, logical=1)
    t.emit(f"csrr x8, {c('sireg3')}")
    t.emit("srli x8, x8, 15")
    t.emit("andi x8, x8, 1")
    t.check("x8", 0, lab, "record A (first after SCTRCLR and a write of sctrctl): CCV = 0")
    return [t]


@rule
def ctrdata_cc() -> list[TestFile]:
    t = cyc_test(
        "ctrdata_cc",
        plan="CC = CCE (15:12) and CCM (11:0): the value decodes as CCM when CCE = 0, else as "
        "(4096 + CCM) << (CCE-1). A pair with a 5000-nop gap (more than 4095 cycles) must decode within the "
        "brackets less the granularity 2^(CCE-1) when CCV=1, unless CC is saturated (all implemented bits "
        "1); a pair with a 1000-nop gap (CCE = 0 range) likewise.",
    )
    L.cc_pair(t, 1000)
    L.cc_check(t, "1000-nop gap")
    L.cc_pair(t, 5000)
    L.cc_check(t, "5000-nop gap")
    return [t]


@rule
def ctr_ccounter_impl() -> list[TestFile]:
    t = s_test(
        "ctr_ccounter_impl",
        plan="A cycle-counting implementation implements CCV and all 12 CCM bits: after "
        "writing all ones to ctrdata bits XLEN-1:15 of logical entry 0, either none of CCV/CC reads 1 (no "
        "cycle counting) or CCV and CCM (27:16) all read 1.",
        context=CTX_MEASURE,
    )
    off(t)
    ccv_probe(t, "x9")
    lab = t.label("impl")
    t.emit(f"{lab}:", 0)
    t.emit("snez x7, x9  // some cycle-count bit is implemented")
    t.load("x6", X(0x0FFF8000, 0x0FFF8000))
    t.emit("and x8, x9, x6")
    t.emit("xor x8, x8, x6")
    t.emit("seqz x8, x8  // CCV and CCM all implemented")
    t.emit("xori x7, x7, 1")
    t.emit("or x7, x7, x8")
    t.check_bool("x7", lab, "no cycle counting, or CCV and all CCM bits implemented")
    return [t]


@rule
def ctr_ccounter_cce_rdonly0() -> list[TestFile]:
    t = cyc_test(
        "ctr_ccounter_cce_rdonly0",
        plan="Unimplemented CCE bits are read-only 0: each CCE bit (CC[15:12], "
        "ctrdata bits 31:28) written alone reads back as itself if it read 1 after writing all ones, else 0; "
        "and a recorded pair with a 5000-nop gap has no CCE bit set that is unimplemented.",
    )
    for b in range(28, 32):
        lab = t.label("cce")
        t.emit(f"{lab}:", 0)
        t.emit("li x6, 0x200")
        t.emit(f"csrw {c('siselect')}, x6")
        t.load("x6", X(1 << b, 1 << b))
        t.emit(f"csrw {c('sireg3')}, x6")
        t.emit(f"csrr x7, {c('sireg3')}")
        t.emit(f"csrw {c('sireg3')}, x0")
        t.emit("LA(x8, ctr_cyc)", 2)
        t.emit("LREG x8, 6*REGWIDTH(x8)  // implemented CC bits")
        t.emit("slli x8, x8, 16")
        t.emit("and x8, x8, x6  // the bit if implemented")
        t.emit("xor x7, x7, x8")
        t.emit("seqz x7, x7")
        t.check_bool("x7", lab, f"ctrdata bit {b} (CCE bit {b - 28}) alone reads back iff implemented")
    L.cc_pair(t, 5000)
    lab = t.label("rec")
    t.emit(f"{lab}:", 0)
    L.select(t, logical=0)
    t.emit(f"csrr x7, {c('sireg3')}")
    t.emit("srli x7, x7, 16")
    t.emit("LA(x8, ctr_cyc)", 2)
    t.emit("LREG x8, 6*REGWIDTH(x8)")
    t.emit("not x8, x8")
    t.emit("and x7, x7, x8")
    t.emit("srli x7, x7, 12  // CCE bits outside the implemented ones")
    t.check("x7", 0 if MUT != "cce_extra_bit" else 1, lab, "the record's CCE uses only implemented bits")
    return [t]


@rule
def ctr_ccounter_sat() -> list[TestFile]:
    t = cyc_test(
        "ctr_ccounter_sat",
        plan="CC saturates at all implemented CCM/CCE bits 1: with at most one CCE bit "
        "(maximum 8191 cycles) a 9000-nop gap must give CC = all implemented bits when CCV=1; with more CCE "
        "bits the gap cannot reach saturation and only the bracket check applies.",
    )
    L.cc_pair(t, 9000)
    L.cc_check(t, "9000-nop gap")
    lab = t.label("sat")
    t.emit(f"{lab}:", 0)
    L.select(t, logical=0)
    t.emit(f"csrr x8, {c('sireg3')}")
    t.emit("srli x7, x8, 15")
    t.emit("andi x7, x7, 1")
    t.emit("xori x7, x7, 1  // CCV = 0")
    t.emit("srli x8, x8, 16")
    t.emit("li x6, 0xffff")
    t.emit("and x8, x8, x6  // CC")
    t.emit("LA(x9, ctr_cyc)", 2)
    t.emit("LREG x9, 6*REGWIDTH(x9)  // implemented CC bits")
    t.emit("xor x6, x8, x9")
    t.emit("seqz x6, x6  // saturated")
    t.emit("or x7, x7, x6")
    t.emit("srli x6, x9, 13  // CCE bits 1..3 implemented: 9000 cycles cannot saturate")
    t.emit("snez x6, x6")
    t.emit("or x7, x7, x6")
    t.check_bool("x7", lab, "CCV = 0, or more than one CCE bit, or CC saturated (all implemented bits 1)")
    return [t]


@rule
def ctrtarget_misp() -> list[TestFile]:
    t = s_test(
        "ctrtarget_misp",
        plan="MISP (ctrtarget bit 0) is read-only 0 when not implemented: probe it by writing "
        "ctrtarget = 1 to logical entry 0 (sctrctl = 0); if it reads 0, records of a jal, a jalr, a taken and a "
        "not-taken branch (NTBREN where implemented, RV64) all have MISP = 0. Whether a transfer was "
        "mispredicted is not observable, so with MISP implemented nothing more is checked.",
        context=CTX_MEASURE,
    )
    off(t)
    L.select(t, logical=0)
    t.li("x6", 1)
    t.emit(f"csrw {c('sireg2')}, x6")
    t.emit(f"csrr x1, {c('sireg2')}")
    t.emit("andi x1, x1, 1  // MISP implemented")
    t.emit(f"csrw {c('sireg2')}, x0")
    anchor(t)
    wr(t, "sctrctl", lo(S | L.NTBREN))
    xs = [jal(t, "x0"), L.jalr(t, "x0", "x6"), L.branch(t, "blt", -1, 1), L.nt_branch(t, "bge", -1, 1)]
    off(t)
    L.nt_fixup(t)
    for i in range(len(xs)):
        lab = t.label("misp")
        t.emit(f"{lab}:", 0)
        L.select(t, logical=i)
        t.emit(f"csrr x7, {c('sireg2')}")
        t.emit("andi x7, x7, 1")
        t.emit("xori x8, x1, 1")
        t.emit("and x7, x7, x8  // MISP set although unimplemented")
        t.check(
            "x7",
            0 if MUT != "misp_set_unimpl" else 1,
            lab,
            f"logical entry {i}: MISP is 0 when MISP is not implemented",
        )
    return [t]


# ================================================================ M-mode parts (Smctr/<rule>_Sm.S)
MREQ = ["I", "S", "Smctr", "Sm"]
CTX_M = (
    "M-mode tests (boot M) write mctrctl directly; sctrctl is its S-level view. Each measurement anchors "
    "(sctrstatus = 0, SCTRCLR) with CTR inactive, sets mctrctl (and vsctrctl), runs the transfers, and clears "
    "mctrctl and vsctrctl before reading sctrstatus.WRPTR and the entries through siselect/sireg*. medeleg[3] and "
    "medeleg[8..10] are cleared, so ebreaks and the T-SBI ecalls that leave U, S, VS and VU trap to M-mode; with "
    "mctrctl.M = 0 the M-mode handler and the T-SBI code are not recorded. A U/S window is entered with an mret (at "
    "<window>-4) and left with a T-SBI ecall (at <goto>+4). VS/VU-mode is reached by a T-SBI GOTO_SMODE to HS-mode "
    "and an sret (at <window>-4), since MRET into V=1 is not usable on QEMU (qemu#4588, qemu#4620)."
)
CTX_MD = CTX_M + " " + L.DEEP_NOTE
SMSTATEEN_REQ = [*MREQ, "Smstateen"]


def m_test_d(name: str, plan: str, context: str = "", required: list | None = None) -> TestFile:
    """An M-mode test with the trap delegation of CTX_M."""
    t = m_test(name, plan, context=context, required=required)
    t.li("x6", (1 << 3) | (1 << 8) | (1 << 9) | (1 << 10))
    t.emit("csrc medeleg, x6  // ebreak and ecalls from U, S, VS and VU trap to M-mode")
    return t


def record_m(
    t: TestFile, ctl: int, body: Callable[[], list[Xfer]], desc: str, expect: bool | list[bool] = True
) -> None:
    """In M-mode: anchor, mctrctl = ctl, run body's transfers, mctrctl = 0, then exactly the transfers marked True
    in expect were recorded, in order."""
    anchor(t)
    wr(t, "mctrctl", ctl, note="mctrctl = configuration")
    xs = body()
    off(t, "mctrctl")
    L.nt_fixup(t)
    exp = expect if isinstance(expect, list) else [expect] * len(xs)
    rec = [x for x, e in zip(xs, exp) if e]
    check_n(t, len(rec), desc)
    for i, x in enumerate(reversed(rec)):
        check_xfer(t, x, desc, logical=i)


def vwin(
    t: TestFile, mode: str, body: Callable[[], T], expect: Expect = "ok", desc: str = "", tval: Expect | None = None
) -> tuple[T, str, str]:
    """From M-mode: a trap window that runs body() in VS- or VU-mode (T-SBI GOTO_SMODE, then an sret at
    <label>-4) and returns with T-SBI GOTO_MMODE (its ecall at <goto>+4)."""
    assert t.cur == "M" and mode in ("VS", "VU")
    lab = t.label(f"in_{mode}")
    t.allow(1)
    t.emit("RVTEST_TSBI_GOTO_SMODE", 120)
    t.cur = "S"
    t.enter(mode)
    t.emit(f"{lab}:", 0)
    res = body()
    goto = t.label("goto")
    t.emit(f"{goto}:", 0)
    t.emit("RVTEST_TSBI_GOTO_MMODE", 120)
    t.cur = "M"
    t.outcome(expect, lab, f"{desc} in {mode}-mode", tval, origin=mode)
    return res, lab, goto


def mwin(
    t: TestFile, mode: str, body: Callable[[], T], expect: Expect = "ok", desc: str = "", tval: Expect | None = None
) -> tuple[T, str, str]:
    """From M-mode: a window in any lower mode (U/S through mret, VS/VU through vwin) or in M-mode itself."""
    if mode in ("VS", "VU"):
        return vwin(t, mode, body, expect, desc, tval)
    return win(t, mode, body, expect, desc, tval)


def m_ebreak(t: TestFile, mode: str, desc: str, cause: Expect = BREAK) -> tuple[str, str]:
    """An ebreak in `mode` (trapping to M-mode under CTX_M); returns (ebreak label, goto label)."""

    def body() -> str:
        eb = t.label("eb")
        t.emit(f"{eb}: ebreak")
        return eb

    eb, _, goto = mwin(t, mode, body, cause, f"{desc}: ebreak", None)
    return eb, goto


def m_ext_case(t: TestFile, mode: str, mctl: int, vsctl: int | None, n: int, desc: str) -> None:
    """ebreak in `mode` (to M-mode), then the T-SBI ecall out (to M-mode): n records (0 or 2), each an external
    trap with ctrtarget PC 0."""
    anchor(t)
    if vsctl is not None:
        wr(t, "vsctrctl", vsctl)
    wr(t, "mctrctl", mctl)
    eb, goto = m_ebreak(t, mode, desc)
    off(t, "mctrctl")
    if vsctl is not None:
        off(t, "vsctrctl")
    check_n(t, n, desc)
    if n:
        check_entry(
            t,
            f"{desc}: the T-SBI ecall to M-mode",
            src=f"{goto}+4",
            tgt=0 if MUT != "ext_tgt_kept" else f"{goto}+4",
            typ=L.T_EXC,
            logical=0,
        )
        check_entry(t, f"{desc}: the ebreak to M-mode", src=eb, tgt=0, typ=L.T_EXC, logical=1)


def mte_probe(t: TestFile, reg: str = "x8") -> None:
    L.probe_ctl(t, reg, MTE, "mctrctl")


@rule
def mctrctl_mode_op_Sm() -> list[TestFile]:
    t = m_test_d(
        "mctrctl_mode_op",
        plan="mctrctl.M enables recording in M-mode:\n"
        "1. mctrctl.M: an M-mode jal is the only record.\n"
        "2. mctrctl.S|U (M=0): an M-mode jal is not recorded.\n"
        "3. mctrctl.M only around an S-mode window: the first record is the mret into S-mode (enabled to "
        "disabled: ctrtarget.PC 0), the second the ecall back to M-mode (disabled to enabled: ctrsource.PC "
        "0); the S-mode jal in between is not recorded.",
        context=CTX_MD,
    )
    record_m(t, M, lambda: [jal(t, "x1")], "mctrctl.M: M-mode jal")
    record_m(t, S | U, lambda: [jal(t, "x0")], "mctrctl.S|U: M-mode jal", expect=MUT == "s_records_m")
    L.deep(t)
    anchor(t)
    wr(t, "mctrctl", M)
    (_j,), lab, _ = win(t, "S", lambda: [jal(t, "x6")], desc="mctrctl.M only")
    off(t, "mctrctl")
    L.deep_checks(
        t,
        lambda: [
            L.check_n_ge(t, 2, "M only, S window"),
            check_entry(t, "the mret into S-mode", src=f"{lab}-4", tgt=0, typ=L.T_TRET, k=0),
            check_entry(t, "the ecall back to M-mode", src=0, typ=L.T_EXC, k=1),
            L.check_tgt_handler(t, "the ecall back to M-mode", tvec="mtvec"),
        ],
        "M only",
    )
    return [t]


@rule
def mctrctl_impl_Sm() -> list[TestFile]:
    t = m_test(
        "mctrctl_impl",
        plan="In M-mode: after writing all ones to mctrctl, U, S, M and BPFRZ read 1 "
        "(mandatory) and LCOFIFRZ reads 1 when Sscofpmf is implemented; every field written alone reads back "
        "as itself if it read 1 after all ones, else 0; writing 0 reads 0. RV32 reaches bits 31:0 only.",
    )
    t.emit("li x6, -1")
    t.emit(f"csrw {c('mctrctl')}, x6")
    t.emit(f"csrr x8, {c('mctrctl')}")
    lab = t.label("mand")
    t.emit(f"{lab}:", 0)
    mand = U | S | M | BPFRZ
    t.li("x6", mand)
    t.emit("and x7, x8, x6")
    t.check("x7", mand if MUT != "m_optional" else U | S | BPFRZ, lab, "mctrctl all ones: U, S, M, BPFRZ implemented")
    with t.only_if(L.SSCOFPMF):
        t.li("x6", LCOFIFRZ)
        t.emit("and x7, x8, x6")
        t.check("x7", LCOFIFRZ, lab, "Sscofpmf: mctrctl.LCOFIFRZ is writable")
    field_sweep(t, "mctrctl", L.MFIELDS, "mctrctl")
    return [t]


@rule
def Ssctr_mctrctl_sz_acc_op_Sm() -> list[TestFile]:
    t = m_test(
        "Ssctr_mctrctl_sz_acc_op",
        plan="mctrctl is read/write: U|S|M|BPFRZ written reads back; csrrc of S "
        "clears only S and returns the old value; csrrs sets it again; csrrwi 0 returns the old value and "
        "clears it. RV64 (64-bit register): a filter bit above bit 31 (DIRJMPINH, probed) written together "
        "with U reads back with it. It configures CTR: with mctrctl.M an M-mode jal is recorded.",
        context=CTX_MEASURE,
    )
    v = U | S | M | BPFRZ
    lab = t.label("rw")
    t.emit(f"{lab}:", 0)
    t.li("x6", v)
    t.emit(f"csrw {c('mctrctl')}, x6")
    t.emit(f"csrr x7, {c('mctrctl')}")
    t.check("x7", v, lab, "mctrctl = U|S|M|BPFRZ reads back")
    t.li("x6", S)
    t.emit(f"csrrc x7, {c('mctrctl')}, x6")
    t.check("x7", v, lab, "csrrc returns the old value")
    t.emit(f"csrr x7, {c('mctrctl')}")
    t.check("x7", v & ~S if MUT != "mctrctl_ro" else v, lab, "csrrc of S clears only S")
    t.emit(f"csrrs x7, {c('mctrctl')}, x6")
    t.emit(f"csrrwi x7, {c('mctrctl')}, 0")
    t.check("x7", v, lab, "csrrs set S again; csrrwi 0 returns the old value")
    t.emit(f"csrr x7, {c('mctrctl')}")
    t.check("x7", 0, lab, "csrrwi 0 clears mctrctl")
    with t.rv64_only():
        L.probe_ctl(t, "x8", L.DIRJMPINH, "mctrctl")
        lab = t.label("hi")
        t.emit(f"{lab}:", 0)
        t.load("x6", lo(U | L.DIRJMPINH))
        t.emit(f"csrw {c('mctrctl')}, x6")
        t.emit(f"csrr x7, {c('mctrctl')}")
        t.emit(f"csrw {c('mctrctl')}, x0")
        t.emit(f"ori x8, x8, {U}  // U | DIRJMPINH if implemented")
        t.emit("xor x7, x7, x8")
        t.emit("seqz x7, x7")
        t.check_bool("x7", lab, "RV64: U|DIRJMPINH reads back with DIRJMPINH when implemented (64-bit register)")
    record_m(t, M, lambda: [jal(t, "x0")], "mctrctl.M configures recording")
    return [t]


@rule
def Ssctr_sctrctl_op_Sm() -> list[TestFile]:
    t = m_test(
        "Ssctr_sctrctl_op",
        plan="sctrctl is the S-level view of mctrctl (all fields but M and MTE): with "
        "mctrctl = M|MTE|S|BPFRZ (MTE where implemented), sctrctl reads S|BPFRZ; writing sctrctl = U|BPFRZ "
        "leaves mctrctl = M|MTE|U|BPFRZ (M and MTE kept); writing sctrctl = 0 leaves M|MTE.",
    )
    mte_probe(t, "x8")
    lab = t.label("view")
    t.emit(f"{lab}:", 0)
    t.li("x6", M | MTE | S | BPFRZ)
    t.emit(f"csrw {c('mctrctl')}, x6")
    rd(t, "x7", "sctrctl")
    t.check(
        "x7", S | BPFRZ if MUT != "sctrctl_m_visible" else M | S | BPFRZ, lab, "sctrctl shows mctrctl without M, MTE"
    )
    t.li("x6", U | BPFRZ)
    t.emit(f"csrw {c('sctrctl')}, x6")
    rd(t, "x7", "mctrctl")
    t.li("x9", M | U | BPFRZ)
    t.emit("or x9, x9, x8  // M | MTE (if implemented) | U | BPFRZ")
    t.emit("xor x7, x7, x9")
    t.emit("seqz x7, x7")
    t.check_bool("x7", lab, "a write of sctrctl = U|BPFRZ changes the S-level fields of mctrctl, keeping M and MTE")
    t.emit(f"csrw {c('sctrctl')}, x0")
    rd(t, "x7", "mctrctl")
    t.emit(f"ori x9, x8, {M}")
    t.emit("xor x7, x7, x9")
    t.emit("seqz x7, x7")
    t.check_bool("x7", lab, "sctrctl = 0 leaves mctrctl = M|MTE")
    off(t, "mctrctl")
    return [t]


@rule
def Smctr_scope_Sm() -> list[TestFile]:
    t = m_test(
        "Smctr_scope",
        plan="Smctr covers every new CSR and instruction at every privilege level: in M-mode, "
        "mctrctl, sctrctl, sctrstatus, sctrdepth, (H) vsctrctl, siselect = 0x200 with sireg..sireg6, and "
        "SCTRCLR execute without a trap. The S/U/VS/VU behaviour is in the Ssctr suite.",
    )
    lines = [f"csrr x7, {c(n)}" for n in ("mctrctl", "sctrctl", "sctrstatus", "sctrdepth")]
    lines += ["li x7, 0x200", f"csrw {c('siselect')}, x7"] + [f"csrr x7, {c(n)}" for n in L.SIREGS]
    lines += [f".word 0x{L.SCTRCLR:08x}  // sctrclr"]
    for ln in lines:
        lab = t.label("ok")
        t.allow(1)
        t.emit(f"{lab}: {ln}")
        t.outcome(
            "ok" if MUT != "m_sctrclr_illegal" or "sctrclr" not in ln else ILLEGAL,
            lab,
            f"M-mode {ln.split('//')[0].strip()}",
        )
    with t.only_if(H):
        lab = t.label("vs")
        t.allow(1)
        t.emit(f"{lab}: csrr x7, {c('vsctrctl')}")
        t.outcome("ok", lab, "M-mode csrr vsctrctl")
    return [t]


@rule
def mctrctl_mte_op_Sm() -> list[TestFile]:
    t = m_test_d(
        "mctrctl_mte_op",
        plan="MTE (probed) enables recording of traps to M-mode while M=0: mctrctl.S|MTE, "
        "an S-mode ebreak and the ecall out (both S to M) are recorded with ctrtarget 0; mctrctl.S (MTE=0): "
        "no records. With M=1 (mctrctl.M|S|MTE) the same ebreak is a normal trap: its record's target is "
        "the mtvec handler (record 1, after the mret into S-mode).",
        context=CTX_MD,
    )
    mte_probe(t)

    def on() -> None:
        m_ext_case(t, "S", S | MTE, None, 2 if MUT != "mte_ignored" else 0, "MTE=1, M=0")
        L.deep(t)
        anchor(t)
        wr(t, "mctrctl", M | S | MTE)
        eb, _ = m_ebreak(t, "S", "M=1, MTE=1")
        off(t, "mctrctl")
        L.deep_checks(
            t,
            lambda: [
                L.check_n_ge(t, 2, "M=1"),
                check_entry(t, "S ebreak with M=1", src=eb, typ=L.T_EXC, k=1),
                L.check_tgt_handler(t, "S ebreak with M=1", tvec="mtvec"),
            ],
            "M=1",
        )

    t.either("x8", on, lambda: None)
    m_ext_case(t, "S", S, None, 0, "MTE=0, M=0")
    return [t]


@rule
def exttrap_Sm_Sm() -> list[TestFile]:
    t = m_test_d(
        "exttrap_Sm",
        plan="S to M external traps need mctrctl.MTE only: mctrctl.S (M disabled), S-mode "
        "ebreak and the T-SBI ecall (both S to M): MTE=1 (probed): two records, ctrtarget 0; MTE=0 with "
        "STE=1: none.",
        context=CTX_M,
    )
    mte_probe(t)
    t.either("x8", lambda: m_ext_case(t, "S", S | MTE, None, 2 if MUT != "sm_needs_ste" else 0, "MTE=1"), lambda: None)
    m_ext_case(t, "S", S | STE, None, 0 if MUT != "sm_ste_enough" else 2, "MTE=0, STE=1")
    return [t]


def ext_sweep(
    t: TestFile, mode: str, base: int, vbase: int | None, cases: list[tuple[int, int, int, int]], mut: str = ""
) -> None:
    """External traps from `mode` to M-mode for (MTE, STE, vsctrctl.STE, n) cases, when MTE is implemented (by
    exttrap_implreq, STE then is too); with MTE unimplemented, nothing is recorded even with all enables set."""
    mte_probe(t)
    if mut and mut == MUT:  # the mutant expects records in the first case that must have none
        i = next(k for k, cs in enumerate(cases) if cs[3] == 0)
        cases = [*cases[:i], (*cases[i][:3], 2), *cases[i + 1 :]]

    def on() -> None:
        for mte, ste, vste, n in cases:
            d = f"MTE={mte}, sctrctl.STE={ste}" + (f", vsctrctl.STE={vste}" if vbase is not None else "")
            m_ext_case(t, mode, base | MTE * mte | STE * ste, None if vbase is None else vbase | STE * vste, n, d)

    def off_() -> None:
        m_ext_case(t, mode, base | MTE | STE, None if vbase is None else vbase | STE, 0, "MTE unimplemented")

    t.either("x8", on, off_)


@rule
def exttrap_um_Sm() -> list[TestFile]:
    t = m_test_d(
        "exttrap_um",
        plan="U to M external traps need mctrctl.MTE and sctrctl.STE (S is the intervening "
        "mode): mctrctl.U, U-mode ebreak and T-SBI ecall (both U to M): (MTE, STE) = (0,0), (1,0), (0,1): "
        "no records; (1,1): two records, ctrtarget 0. MTE probed.",
        context=CTX_M,
    )
    ext_sweep(t, "U", U, None, [(0, 0, 0, 0), (1, 0, 0, 0), (0, 1, 0, 0), (1, 1, 0, 2)], "um_mte_only")
    return [t]


@rule
def exttrap_vsm_Sm() -> list[TestFile]:
    t = m_test_d(
        "exttrap_vsm",
        plan="VS to M external traps need mctrctl.MTE and sctrctl.STE, and not "
        "vsctrctl.STE: vsctrctl.S (sctrctl.S = 0), VS-mode ebreak and the T-SBI ecall (both VS to M): "
        "(MTE, STE, vsctrctl.STE) = (1,0,1), (0,1,1): no records; (1,1,0) and (1,1,1): two records, "
        "ctrtarget 0. MTE probed.",
        context=CTX_M,
        required=[*MREQ, "H"],
    )
    ext_sweep(
        t,
        "VS",
        0,
        S,
        [(1, 0, 1, 0), (0, 1, 1, 0), (1, 1, 0, 2 if MUT != "vsm_needs_vsste" else 0), (1, 1, 1, 2)],
        "vsm_mte_only",
    )
    return [t]


@rule
def exttrap_vum_Sm() -> list[TestFile]:
    t = m_test_d(
        "exttrap_vum",
        plan="VU to M external traps need mctrctl.MTE, sctrctl.STE and vsctrctl.STE: "
        "vsctrctl.U, VU-mode ebreak and T-SBI ecall (both VU to M): any one of the three clear: no records; "
        "all three set: two records, ctrtarget 0. MTE probed.",
        context=CTX_M,
        required=[*MREQ, "H"],
    )
    ext_sweep(t, "VU", 0, U, [(0, 1, 1, 0), (1, 0, 1, 0), (1, 1, 0, 0), (1, 1, 1, 2)], "vum_no_vsste")
    return [t]


@rule
def exttrap_requirements_Sm() -> list[TestFile]:
    t = m_test_d(
        "exttrap_requirements",
        plan="The intervening modes' enables are needed for traps to M-mode: "
        "mctrctl.MTE alone records S to M (no intervening mode: 2 records) but not U to M (S intervenes: "
        "no records); with H, MTE alone does not record VS to M (HS intervenes) while MTE|STE does. MTE "
        "probed.",
        context=CTX_M,
    )
    mte_probe(t)

    def on() -> None:
        m_ext_case(t, "S", S | MTE, None, 2, "S to M, MTE only")
        m_ext_case(t, "U", U | MTE, None, 0 if MUT != "no_intervening_m" else 2, "U to M, MTE only")

    def on_h() -> None:
        m_ext_case(t, "VS", MTE, S, 0, "VS to M, MTE only")
        m_ext_case(t, "VS", MTE | STE, S, 2, "VS to M, MTE and sctrctl.STE")

    t.either("x8", on, lambda: None)
    with t.only_if(H):
        mte_probe(t)
        t.either("x8", on_h, lambda: None)
    return [t]


@rule
def exttrap_implreq_Sm() -> list[TestFile]:
    t = m_test(
        "exttrap_implreq",
        plan="If external trap recording is implemented, mctrctl.MTE and sctrctl.STE are "
        "both implemented: MTE and STE are both writable in mctrctl or both read-only 0.",
    )
    lab = t.label("p")
    t.emit(f"{lab}:", 0)
    L.probe_ctl(t, "x8", MTE, "mctrctl")
    L.probe_ctl(t, "x9", STE, "mctrctl")
    t.emit("srli x8, x8, 9")
    t.emit("srli x9, x9, 8")
    t.emit("xor x8, x8, x9")
    t.check("x8", 0, lab, "mctrctl.MTE and STE are both writable or both read-only 0")
    return [t]


@rule
def mctrctl_bpfrz_op_Sm() -> list[TestFile]:
    t = m_test_d(
        "mctrctl_bpfrz_op",
        plan="BPFRZ=1 freezes CTR on a breakpoint that traps to M-mode, and the "
        "breakpoint is not recorded:\n"
        "1. mctrctl.M|BPFRZ, an M-mode ebreak: FROZEN=1, WRPTR=0.\n"
        "2. mctrctl.S|BPFRZ, an S-mode ebreak to M-mode (M disabled): FROZEN=1, WRPTR=0.\n"
        "3. mctrctl.M|S (BPFRZ=0), S-mode ebreak to M-mode: FROZEN=0 and the ebreak is recorded (record 1, "
        "after the mret into S-mode).",
        context=CTX_MD,
    )
    anchor(t)
    wr(t, "mctrctl", M | BPFRZ)
    lab = t.label("eb")
    t.allow(1)
    t.emit(f"{lab}: ebreak")
    off(t, "mctrctl")
    t.outcome(BREAK, lab, "M-mode ebreak with BPFRZ", [0, lab], origin="M")
    lab2 = t.label("fz")
    t.emit(f"{lab2}:", 0)
    rd(t, "x7", "sctrstatus")
    t.check("x7", lo(FROZEN) if MUT != "bpfrz_ignored" else 1, lab2, "M-mode ebreak with BPFRZ: FROZEN=1, WRPTR=0")
    anchor(t)
    wr(t, "mctrctl", S | BPFRZ)
    m_ebreak(t, "S", "S to M, BPFRZ")
    off(t, "mctrctl")
    lab2 = t.label("fzs")
    t.emit(f"{lab2}:", 0)
    rd(t, "x7", "sctrstatus")
    t.check(
        "x7",
        lo(FROZEN) if MUT != "bpfrz_only_enabled_target" else 0,
        lab2,
        "S-mode ebreak to M-mode with BPFRZ: FROZEN=1, WRPTR=0",
    )
    L.deep(t)
    anchor(t)
    wr(t, "mctrctl", M | S)
    eb, _ = m_ebreak(t, "S", "S to M, BPFRZ=0")
    off(t, "mctrctl")
    frozen_is_keep(t, 0, "BPFRZ=0")
    L.deep_checks(t, lambda: [L.check_n_ge(t, 2, "BPFRZ=0"), check_entry(t, "BPFRZ=0 ebreak", src=eb, k=1)], "BPFRZ=0")
    t.emit(f"csrw {c('sctrstatus')}, x0")
    return [t]


def frozen_is_keep(t: TestFile, want: int, desc: str) -> None:
    lab = t.label("fz")
    t.emit(f"{lab}:", 0)
    rd(t, "x7", "sctrstatus")
    t.emit("srli x7, x7, 31")
    t.emit("andi x7, x7, 1")
    t.check("x7", want, lab, f"{desc}: sctrstatus.FROZEN = {want}")


@rule
def ctr_trap_enabled_Sm() -> list[TestFile]:
    t = m_test_d(
        "ctr_trap_enabled",
        plan="A trap between enabled modes into M-mode is recorded normally: mctrctl.M|S, "
        "an S-mode ebreak to M-mode is record 1 after the anchor (record 0 is the mret into S-mode, also "
        "between enabled modes: ctrtarget = the S-mode label): ctrsource = the ebreak pc | V, ctrtarget = "
        "the mtvec handler, TYPE 1 or 0.",
        context=CTX_MD,
    )
    L.deep(t)
    anchor(t)
    wr(t, "mctrctl", M | S)
    eb, _ = m_ebreak(t, "S", "S and M enabled")
    off(t, "mctrctl")
    L.deep_checks(
        t,
        lambda: [
            L.check_n_ge(t, 2, "S ebreak to M"),
            check_entry(t, "the mret into S-mode", src=f"{eb}-4", tgt=eb, typ=L.T_TRET, k=0),
            check_entry(t, "S ebreak to M", src=eb if MUT != "trap_src_zero" else 0, typ=L.T_EXC, k=1),
            L.check_tgt_handler(t, "S ebreak to M", tvec="mtvec"),
        ],
        "S ebreak to M",
    )
    return [t]


@rule
def ctr_trapret_enabled_Sm() -> list[TestFile]:
    t = m_test_d(
        "ctr_trapret_enabled",
        plan="Trap returns between enabled modes are recorded normally: mctrctl.M, an "
        "mret M->M is the only record (target = the label after it); mctrctl.M|S, the mret into S-mode is "
        "the first record (target = the S-mode label) and an S-mode jal the second.",
        context=CTX_MD,
    )
    record_m(t, M, lambda: [L.mret_m(t)], "mret M->M")
    L.deep(t)
    anchor(t)
    wr(t, "mctrctl", M | S)
    (j,), lab, _ = win(t, "S", lambda: [jal(t, "x6")], desc="M and S enabled")
    off(t, "mctrctl")
    L.deep_checks(
        t,
        lambda: [
            L.check_n_ge(t, 2, "mret M->S"),
            check_entry(t, "mret M->S", src=f"{lab}-4", tgt=lab if MUT != "tret_tgt_zero" else 0, typ=L.T_TRET, k=0),
            check_entry(t, "S jal", src=j.src, tgt=j.tgt, k=1),
        ],
        "mret M->S",
    )
    return [t]


@rule
def ctr_ttype3_Sm() -> list[TestFile]:
    t = m_test(
        "ctr_ttype3",
        plan="An mret (M->M, mctrctl.M) is recorded with ctrdata.TYPE 3 (trap return) or 0 "
        "(TYPE unimplemented: then a recorded M-mode jal x0 also has TYPE 0).",
        context=CTX_MEASURE,
    )
    anchor(t)
    wr(t, "mctrctl", M)
    j = jal(t, "x0", "TYPE probe")
    x = L.mret_m(t)
    off(t, "mctrctl")
    check_n(t, 2, "jal x0, mret")
    lab = check_entry(t, "jal x0", src=j.src, tgt=j.tgt, typ=L.T_DIRJMP, logical=1)
    t.emit("andi x9, x8, 0xf  // the jal's TYPE: 0 if TYPE is unimplemented")
    lab = check_entry(t, "mret", src=x.src, tgt=x.tgt, logical=0)
    t.emit("andi x8, x8, 0xf")
    t.emit("snez x9, x9")
    t.emit(f"li x7, {3 if MUT != 'mret_type1' else 1}")
    t.emit("neg x9, x9")
    t.emit("and x7, x7, x9  // 3 if TYPE is implemented, else 0")
    t.emit("xor x8, x8, x7")
    t.emit("seqz x8, x8")
    t.check_bool("x8", lab, "mret: ctrdata.TYPE = 3 (0 if TYPE is unimplemented, as for the jal)")
    return [t]


# ---- state enable (Smstateen)
MSTATEEN0_CTR = 54


def m_ctr_stateen(t: TestFile, on: bool) -> None:
    op = "csrs" if on else "csrc"
    with t.rv64_only():
        t.li("x6", 1)
        t.emit(f"slli x6, x6, {MSTATEEN0_CTR}")
        t.emit(f"{op} mstateen0, x6  // mstateen0.CTR = {int(on)}")
    with t.rv32_only():
        t.li("x6", 1 << (MSTATEEN0_CTR - 32))
        t.emit(f"{op} CSR_MSTATEEN0H, x6  // mstateen0h.CTR = {int(on)}")


def m_csr_win(
    t: TestFile, mode: str, line: str, expect: Expect, desc: str, enc: int | None = None, pre: list[str] | None = None
) -> None:
    """One CSR instruction (or SCTRCLR) in `mode` inside a window; `pre` lines run in that mode first."""
    lab = t.label(f"acc_{mode}")

    def body() -> None:
        for p in pre or []:
            t.emit(p)
        t.emit(f"{lab}: {line}")

    tval = None if expect == "ok" else [0, enc] if enc is not None else None
    if mode == "M":
        t.allow(1)
        body()
        t.outcome(expect, lab, f"{desc} in M-mode", tval, origin="M")
        return
    if mode in ("VS", "VU"):
        t.allow(1)
        t.emit("RVTEST_TSBI_GOTO_SMODE", 120)
        t.cur = "S"
        t.enter(mode)
        body()
        t.emit("RVTEST_TSBI_GOTO_MMODE", 120)
        t.cur = "M"
    else:
        t.allow(1)
        t.enter(mode)
        body()
        t.leave()
    t.outcome(expect, lab, f"{desc} in {mode}-mode", tval, origin=mode)


@rule
def mstateen_ctr1_Sm() -> list[TestFile]:
    t = m_test(
        "mstateen_ctr1",
        plan="With mstateen0.CTR=1, CTR state below M-mode behaves normally: in S-mode "
        "reads and writes of sctrctl, sctrstatus and sctrdepth, sireg/sireg2/sireg3 with siselect = 0x200, and "
        "SCTRCLR do not trap; with H (hstateen0.CTR=1) a VS-mode read of sctrctl (vsctrctl) does not trap.",
        required=SMSTATEEN_REQ,
    )
    m_ctr_stateen(t, True)
    for n in ("sctrctl", "sctrstatus", "sctrdepth"):
        m_csr_win(t, "S", f"csrr x7, {c(n)}", "ok" if MUT != "stateen_ctr1_traps" else ILLEGAL, f"read {n}")
        m_csr_win(t, "S", f"csrw {c(n)}, x0", "ok", f"write {n}")
    for n in ("sireg", "sireg2", "sireg3"):
        m_csr_win(
            t,
            "S",
            f"csrr x7, {c(n)}",
            "ok",
            f"read {n} (siselect 0x200)",
            pre=["li x7, 0x200", f"csrw {c('siselect')}, x7"],
        )
    m_csr_win(t, "S", f".word 0x{L.SCTRCLR:08x}", "ok", "SCTRCLR")
    with t.only_if("defined(H_SUPPORTED) && defined(SSSTATEEN_SUPPORTED)"):
        set_hctr(t, True)
        m_csr_win(t, "VS", f"csrr x7, {c('sctrctl')}", "ok", "read sctrctl (vsctrctl), hstateen0.CTR=1")
    return [t]


def stateen0_case(t: TestFile, body: Callable[[], None]) -> None:
    """mstateen0.CTR = 0 around body(), then 1 again."""
    m_ctr_stateen(t, False)
    body()
    m_ctr_stateen(t, True)


@rule
def mstateen_ctr0_Sm() -> list[TestFile]:
    t = m_test(
        "mstateen_ctr0",
        plan="With mstateen0.CTR=0, below M-mode the listed CTR operations raise "
        "illegal-instruction (xtval 0 or the instruction): an S-mode read of sctrctl, U-mode SCTRCLR, and "
        "with H a VS-mode read of sctrctl and VU-mode SCTRCLR (illegal, not virtual-instruction); M-mode "
        "reads of sctrctl and SCTRCLR still work.",
        required=SMSTATEEN_REQ,
    )
    ill = ILLEGAL if MUT != "stateen_virtual" else VIRTUAL

    def body() -> None:
        m_csr_win(t, "S", f"csrr x7, {c('sctrctl')}", ill, "read sctrctl, mstateen0.CTR=0", csr_enc(0x14E))
        m_csr_win(t, "U", f".word 0x{L.SCTRCLR:08x}", ill, "SCTRCLR, mstateen0.CTR=0", L.SCTRCLR)
        m_csr_win(t, "M", f"csrr x7, {c('sctrctl')}", "ok", "read sctrctl, mstateen0.CTR=0")
        m_csr_win(t, "M", f".word 0x{L.SCTRCLR:08x}", "ok", "SCTRCLR, mstateen0.CTR=0")
        with t.only_if(H):
            m_csr_win(t, "VS", f"csrr x7, {c('sctrctl')}", ill, "read sctrctl, mstateen0.CTR=0", csr_enc(0x14E))
            m_csr_win(t, "VU", f".word 0x{L.SCTRCLR:08x}", ill, "SCTRCLR, mstateen0.CTR=0", L.SCTRCLR)

    stateen0_case(t, body)
    return [t]


@rule
def mstateen_ctr0_except_csr_access_Sm() -> list[TestFile]:
    t = m_test(
        "mstateen_ctr0_except_csr_access",
        plan="With mstateen0.CTR=0: every CSR instruction form on "
        "sctrctl, sctrstatus, sctrdepth and (H) vsctrctl raises illegal-instruction in S-mode (xtval 0 or the "
        "instruction); with H, VS-mode reads of sctrctl and sctrstatus raise illegal-instruction too (not "
        "virtual-instruction, and not the virtual-instruction sctrdepth normally raises in VS-mode); M-mode "
        "access still works.",
        required=SMSTATEEN_REQ,
    )

    def body() -> None:
        for name, num in (("sctrctl", 0x14E), ("sctrstatus", 0x14F), ("sctrdepth", 0x15F)):
            for form, f3, rdn, rs1 in FORMS8:
                exp = ILLEGAL if MUT != "stateen_csr_ok" or name != "sctrstatus" else "ok"
                m_csr_win(
                    t,
                    "S",
                    form.format(c=c(name)),
                    exp,
                    f"{form.split()[0]} {name}, mstateen0.CTR=0",
                    csr_enc(num, f3, rdn, rs1),
                )
        with t.only_if(H):
            for form, f3, rdn, rs1 in FORMS8[:2]:
                m_csr_win(
                    t,
                    "S",
                    form.format(c=c("vsctrctl")),
                    ILLEGAL,
                    f"{form.split()[0]} vsctrctl, mstateen0.CTR=0",
                    csr_enc(0x24E, f3, rdn, rs1),
                )
            for name, num in (("sctrctl", 0x14E), ("sctrstatus", 0x14F), ("sctrdepth", 0x15F)):
                m_csr_win(t, "VS", f"csrr x7, {c(name)}", ILLEGAL, f"read {name}, mstateen0.CTR=0", csr_enc(num))
        m_csr_win(t, "M", f"csrr x7, {c('sctrstatus')}", "ok", "read sctrstatus, mstateen0.CTR=0")

    stateen0_case(t, body)
    return [t]


@rule
def mstateen_ctr0_except_indirect_access_Sm() -> list[TestFile]:
    t = m_test(
        "mstateen_ctr0_except_indirect_access",
        plan="With mstateen0.CTR=0 (CSRIND left 1): in S-mode, "
        "writing siselect = 0x200 works, but reading any of sireg..sireg6 raises illegal-instruction, also "
        "with siselect = 0x2FF; with H, HS-mode vsireg/vsireg2/vsireg3 with vsiselect = 0x200 and a VS-mode "
        "sireg read (vsireg) with vsiselect = 0x200 raise illegal-instruction (not virtual).",
        required=SMSTATEEN_REQ,
    )
    sel = ["li x7, 0x200", f"csrw {c('siselect')}, x7"]

    def body() -> None:
        m_csr_win(t, "S", f"csrw {c('siselect')}, x7", "ok", "write siselect = 0x200", pre=["li x7, 0x200"])
        for n in L.SIREGS:
            m_csr_win(
                t,
                "S",
                f"csrr x7, {c(n)}",
                ILLEGAL if MUT != "stateen_sireg_ok" else "ok",
                f"read {n} (siselect 0x200), mstateen0.CTR=0",
                csr_enc(CSR_NUM[n]),
                pre=sel,
            )
        m_csr_win(
            t,
            "S",
            f"csrr x7, {c('sireg')}",
            ILLEGAL,
            "read sireg (siselect 0x2FF), mstateen0.CTR=0",
            csr_enc(0x151),
            pre=["li x7, 0x2FF", f"csrw {c('siselect')}, x7"],
        )
        with t.only_if(H):
            vsel = ["li x7, 0x200", f"csrw {c('vsiselect')}, x7"]
            for n in ("vsireg", "vsireg2", "vsireg3"):
                m_csr_win(
                    t,
                    "S",
                    f"csrr x7, {c(n)}",
                    ILLEGAL,
                    f"HS-mode read {n} (vsiselect 0x200), mstateen0.CTR=0",
                    csr_enc(CSR_NUM[n]),
                    pre=vsel,
                )
            m_csr_win(
                t,
                "VS",
                f"csrr x7, {c('sireg')}",
                ILLEGAL,
                "read sireg (vsiselect 0x200), mstateen0.CTR=0",
                csr_enc(0x151),
                pre=sel,
            )

    stateen0_case(t, body)
    return [t]


@rule
def mstateen_ctr0_except_sctrclr_Sm() -> list[TestFile]:
    t = m_test(
        "mstateen_ctr0_except_sctrclr",
        plan="With mstateen0.CTR=0, SCTRCLR raises illegal-instruction in "
        "S-mode and (H) VS-mode, and does not clear the entries (logical entry 0, written by M-mode, keeps "
        "its ctrsource); in M-mode it still executes and clears them.",
        required=SMSTATEEN_REQ,
    )
    enc = f".word 0x{L.SCTRCLR:08x}  // sctrclr"

    def body() -> None:
        fill(t, [0])
        m_csr_win(t, "S", enc, ILLEGAL if MUT != "stateen_sctrclr_ok" else "ok", "SCTRCLR, mstateen0.CTR=0", L.SCTRCLR)
        with t.only_if(H):
            m_csr_win(t, "VS", enc, ILLEGAL, "SCTRCLR, mstateen0.CTR=0", L.SCTRCLR)
        lab = t.label("kept")
        t.emit(f"{lab}:", 0)
        L.select(t, logical=0)
        t.emit(f"csrr x7, {c('sireg')}")
        t.emit("snez x7, x7")
        t.check("x7", 1, lab, "the trapping SCTRCLR did not clear logical entry 0")
        m_csr_win(t, "M", enc, "ok", "SCTRCLR, mstateen0.CTR=0")
        L.check_empty(t, 0, "after an M-mode SCTRCLR")

    stateen0_case(t, body)
    t.extra_data.append(".p2align 2\nctr_pa: .word 0")
    return [t]


@rule
def mstateen_ctr0_qualified_transfer_Sm() -> list[TestFile]:
    t = m_test_d(
        "mstateen_ctr0_qualified_transfer",
        plan="With mstateen0.CTR=0, transfers below M-mode are still "
        "recorded: mctrctl.S, an S-mode jal is the only record (the mret into S-mode is from disabled "
        "M-mode; the ecall out is an external trap, MTE=0); with H, vsctrctl.S and a VS-mode jal: the only "
        "record.",
        context=CTX_M,
        required=SMSTATEEN_REQ,
    )

    def body() -> None:
        anchor(t)
        wr(t, "mctrctl", S)
        (j,), _, _ = win(t, "S", lambda: [jal(t, "x6")], desc="mstateen0.CTR=0")
        off(t, "mctrctl")
        check_n(t, 1 if MUT != "stateen_stops_recording" else 0, "mstateen0.CTR=0: S jal")
        check_xfer(t, j, "mstateen0.CTR=0", logical=0)
        with t.only_if(H):
            anchor(t)
            wr(t, "vsctrctl", S)
            (jv,), _, _ = vwin(t, "VS", lambda: [jal(t, "x6")], desc="mstateen0.CTR=0")
            off(t, "vsctrctl")
            check_n(t, 1, "mstateen0.CTR=0: VS jal")
            check_xfer(t, jv, "mstateen0.CTR=0, VS", logical=0)

    stateen0_case(t, body)
    return [t]


@rule
def sctrdepth_mode_Sm() -> list[TestFile]:
    t = m_test(
        "sctrdepth_mode",
        plan="With mstateen0.CTR=0 the state-enable restriction takes precedence: "
        "sctrdepth reads raise illegal-instruction (not virtual-instruction) in VS-mode and VU-mode, and "
        "illegal-instruction in S-mode; with mstateen0.CTR=1 the VS-mode read raises virtual-instruction.",
        required=[*SMSTATEEN_REQ, "H"],
    )
    enc = csr_enc(0x15F)

    def body() -> None:
        for mode in ("S", "VS", "VU"):
            m_csr_win(
                t,
                mode,
                f"csrr x7, {c('sctrdepth')}",
                ILLEGAL if MUT != "sctrdepth_stateen_virtual" or mode == "S" else VIRTUAL,
                "read sctrdepth, mstateen0.CTR=0",
                enc,
            )

    stateen0_case(t, body)
    m_csr_win(t, "VS", f"csrr x7, {c('sctrdepth')}", VIRTUAL, "read sctrdepth, mstateen0.CTR=1", enc)
    return [t]


@rule
def hstateen_ctr_Sm() -> list[TestFile]:
    t = m_test(
        "hstateen_ctr",
        plan="hstateen0.CTR is read-only 0 while mstateen0.CTR=0: setting it reads 0; with "
        "mstateen0.CTR=1 it reads 1 after being set (and 0 after being cleared).",
        required=[*SMSTATEEN_REQ, "H"],
    )

    def rb(want: int, desc: str) -> None:
        lab = t.label("h")
        t.emit(f"{lab}:", 0)
        with t.rv64_only():
            t.emit("csrr x7, 0x60c")
            t.emit(f"srli x7, x7, {HSTATEEN0_CTR_BIT}")
        with t.rv32_only():
            t.emit("csrr x7, 0x61c")
            t.emit(f"srli x7, x7, {HSTATEEN0_CTR_BIT - 32}")
        t.emit("andi x7, x7, 1")
        t.check("x7", want, lab, desc)

    def body() -> None:
        set_hctr(t, True)
        rb(0 if MUT != "hstateen_ctr_writable" else 1, "mstateen0.CTR=0: hstateen0.CTR reads 0 after being set")

    stateen0_case(t, body)
    set_hctr(t, True)
    rb(1, "mstateen0.CTR=1: hstateen0.CTR reads 1 after being set")
    set_hctr(t, False)
    rb(0, "mstateen0.CTR=1: hstateen0.CTR reads 0 after being cleared")
    set_hctr(t, True)
    return [t]


# ---- LCOFI freeze (Sscofpmf)
LCOF_REQ = [*MREQ, "Sscofpmf"]
CTX_LCOF = (
    "A local-counter-overflow interrupt (LCOFI) is produced by a real overflow: mhpmcounterN (N = "
    "RVMODEL_HPM_COUNTER) = all ones, mhpmeventN = RVMODEL_MHPMEVENT_VAL with OF = 0 and no xINH bit (QEMU loses "
    "counts under xINH filtering), and RVMODEL_MHPMEVENT_CODE triggers the event in the mode under test (an earlier "
    "event in M-mode may already overflow it); the overflow sets OF and LCOFIP, and the interrupt is taken by the "
    "mode mideleg/hideleg select once it is enabled there (mie.LCOFIE and the target's xIE set), during a bounded wait (500 iterations: the interrupt may arrive late). The window accepts the interrupt "
    "with any epc. Afterwards LCOFIP, OF and the enables are cleared."
)
LCOFI_M = X((1 << 31) | 13, (1 << 63) | 13)


def lcof_arm(t: TestFile) -> None:
    """Counter N all ones, counting the DUT event in every mode (no xINH bit: QEMU's mode filtering loses counts,
    see README). The overflow may happen in M-mode during the setup; LCOFIP then stays pending until the window
    enables the interrupt in the target mode."""
    t.emit("#define AI_HPM_EV (0x320 + RVMODEL_HPM_COUNTER)", 0)
    t.emit("#define AI_HPM_CNT (0xB00 + RVMODEL_HPM_COUNTER)", 0)
    t.emit("li x6, RVMODEL_MHPMEVENT_VAL")
    t.emit("csrw AI_HPM_EV, x6  // mhpmeventN: the event, OF = 0, no mode inhibited")
    with t.rv32_only():
        t.emit("csrw (AI_HPM_EV + 0x400), x0  // mhpmeventNh: OF = 0, no xINH")
    t.emit("li x6, -1")
    t.emit("csrw AI_HPM_CNT, x6  // mhpmcounterN = all ones")
    with t.rv32_only():
        t.emit("csrw (AI_HPM_CNT + 0x80), x6  // mhpmcounterNh = all ones")


def lcof_event(t: TestFile) -> None:
    """The DUT event, then a bounded wait (500 iterations) for the overflow interrupt, which may arrive late."""
    t.la("x6", "ctr_ev")
    t.emit("RVMODEL_MHPMEVENT_CODE(x6, x7)", 2)
    loop = t.label("wait")
    t.li("x9", 500)
    t.emit(f"{loop}: addi x9, x9, -1", 500)
    t.emit(f"bnez x9, {loop}", 500)


def not_lcofi_record(t: TestFile, tvec: str, desc: str) -> None:
    """The LCOFI was not recorded: logical entry 0 (the last record, if any: a wait-loop branch before the interrupt)
    does not have the trap handler as its target."""
    lab = t.label("nolc")
    t.emit(f"{lab}:", 0)
    L.select(t, logical=0)
    t.emit(f"csrr x7, {c('sireg2')}")
    t.emit(f"csrr x9, {tvec}")
    t.emit("andi x9, x9, -4")
    t.emit("andi x7, x7, -2  // drop MISP")
    t.emit("xor x7, x7, x9")
    t.emit("snez x7, x7")
    t.check("x7", 1 if MUT != "lcofi_recorded" else 0, lab, f"{desc}: the last record is not a trap to {tvec}")


def lcof_clear(t: TestFile) -> None:
    t.emit("csrw AI_HPM_EV, x0  // OF = 0, event off")
    with t.rv32_only():
        t.emit("csrw (AI_HPM_EV + 0x400), x0")
    t.li("x6", 1 << 13)
    t.emit("csrc mip, x6  // LCOFIP = 0")
    t.emit("csrc mie, x6  // LCOFIE = 0")
    t.emit("csrc mideleg, x6")
    t.emit("csrci mstatus, 0xa  // MIE = SIE = 0")


def lcof_case(t: TestFile, target: str, ctl: int, frozen: int, desc: str) -> None:
    """An LCOFI from code running in `target` mode (M or S), taken in that mode, with mctrctl = ctl. When the
    target mode is enabled in ctl, the wait loop's branches before the interrupt are recorded: then only FROZEN
    and 'the LCOFI is not the last record' are checked; otherwise WRPTR must be 0 too."""
    t.li("x6", 1 << 13)
    t.emit(f"csr{'s' if target == 'S' else 'c'} mideleg, x6  // LCOFI to {target}-mode")
    t.emit("csrs mie, x6  // LCOFIE")
    if target == "S":
        t.emit("csrsi mstatus, 2  // SIE (S-mode takes the LCOFI once in S-mode)")
    lcof_arm(t)
    anchor(t)
    wr(t, "mctrctl", ctl)
    lab = t.label("lcof")
    t.allow(1)
    if target == "S":
        t.enter("S")
    t.emit(f"{lab}:", 0)
    if target == "M":
        t.emit("csrsi mstatus, 8  // MIE")
    lcof_event(t)
    if target == "S":
        t.leave()
    else:
        t.emit("csrci mstatus, 8  // MIE = 0")
    off(t, "mctrctl")
    t.outcome(L.LCOFI_CAUSE if target == "S" else LCOFI_M, lab, f"{desc}: LCOFI", epc=False, origin=target)
    lcof_clear(t)
    lab = t.label("fz")
    t.emit(f"{lab}:", 0)
    rd(t, "x7", "sctrstatus")
    enabled = bool(ctl & (S if target == "S" else M))
    if frozen and not enabled:
        t.check(
            "x7",
            lo(FROZEN) if MUT != "lcofifrz_ignored" else 0,
            lab,
            f"{desc}: FROZEN=1 and the LCOFI is not recorded (WRPTR=0)",
        )
    elif frozen:
        t.emit("srli x7, x7, 31")
        t.check("x7", 1 if MUT != "lcofifrz_ignored" else 0, lab, f"{desc}: FROZEN=1")
        not_lcofi_record(t, "stvec" if target == "S" else "mtvec", desc)
    else:
        t.emit("srli x7, x7, 31")
        t.check("x7", 0, lab, f"{desc}: FROZEN=0")
    t.emit(f"csrw {c('sctrstatus')}, x0")


@rule
def sctrstatus_frozen_set_Sm() -> list[TestFile]:
    t = m_test(
        "sctrstatus_frozen_set",
        plan="With LCOFIFRZ=1 an LCOFI that traps to S-mode or M-mode sets FROZEN and "
        "is not recorded: (1) mctrctl.S|LCOFIFRZ, overflow in S-mode, LCOFI delegated to S-mode: FROZEN=1 and the "
        "last record (a wait-loop branch before the interrupt, if any) is not the trap to stvec; (2) "
        "mctrctl.M|LCOFIFRZ, overflow in M-mode, LCOFI taken in M-mode: FROZEN=1, the last record is not the "
        "trap to mtvec; "
        "(3) mctrctl.S without LCOFIFRZ: FROZEN=0.",
        context=CTX_LCOF,
        required=LCOF_REQ,
    )
    lcof_case(t, "S", S | LCOFIFRZ, 1, "to S-mode, LCOFIFRZ=1")
    lcof_case(t, "M", M | LCOFIFRZ, 1, "to M-mode, LCOFIFRZ=1")
    lcof_case(t, "S", S, 0 if MUT != "lcofi_always_freezes" else 1, "to S-mode, LCOFIFRZ=0")
    t.extra_data.append(".p2align 3\nctr_ev: .dword 0")
    return [t]


@rule
def mctrctl_lcofifrz_op_Sm() -> list[TestFile]:
    t = m_test(
        "mctrctl_lcofifrz_op",
        plan="mctrctl.LCOFIFRZ sets FROZEN on an LCOFI that traps to M-mode or S-mode, "
        "whether or not the target mode is enabled: (1) mctrctl.U|LCOFIFRZ (S disabled), overflow in S-mode, "
        "LCOFI to S-mode: FROZEN=1; (2) mctrctl.S|LCOFIFRZ (M disabled), overflow in M-mode, LCOFI to "
        "M-mode: FROZEN=1; (3) LCOFIFRZ=0, mctrctl.M: FROZEN=0.",
        context=CTX_LCOF,
        required=LCOF_REQ,
    )
    lcof_case(t, "S", U | LCOFIFRZ, 1, "to S-mode (disabled), LCOFIFRZ=1")
    lcof_case(t, "M", S | LCOFIFRZ, 1, "to M-mode (disabled), LCOFIFRZ=1")
    lcof_case(t, "M", M, 0, "to M-mode, LCOFIFRZ=0")
    t.extra_data.append(".p2align 3\nctr_ev: .dword 0")
    return [t]


@rule
def vsctrctl_lcofifrz_op_Sm() -> list[TestFile]:
    t = m_test(
        "vsctrctl_lcofifrz_op",
        plan="An LCOFI that traps to VS-mode freezes CTR according to "
        "vsctrctl.LCOFIFRZ. Needs LCOFI delegation to VS-mode: mideleg[13] = 1 and hideleg[13] = 1 (probed; "
        "hideleg[13] is writable with Shlcofideleg). vsie.LCOFIE and "
        "vsstatus.SIE are set, and the overflow happens in VS-mode: vsctrctl.S|LCOFIFRZ: FROZEN=1 and nothing "
        "recorded (the last record, if any, is a wait-loop branch, not the trap to vstvec); vsctrctl.S with "
        "sctrctl.LCOFIFRZ=1: FROZEN=0. Virtual LCOFIs pended by a hypervisor count too (Ssaia): with hideleg[13] = 0 "
        "and hvien[13] = 1 (probed), hvip[13] = 1 and vsie[13] = 1 make interrupt 13 trap to VS-mode on entry: the "
        "same two cases.",
        context=CTX_LCOF,
        required=[*LCOF_REQ, "H"],
    )
    t.li("x6", 1 << 13)
    t.emit("csrs mideleg, x6")
    t.emit("csrs CSR_HIDELEG, x6")
    t.emit("csrr x8, CSR_HIDELEG")
    t.emit("and x8, x8, x6  // hideleg[13] writable")

    def case(vctl: int, sctl: int, frozen: int, desc: str) -> None:
        t.li("x6", 1 << 13)
        t.emit("csrs mie, x6  // LCOFIE")
        t.emit("csrs CSR_VSIE, x6  // vsie.LCOFIE")
        t.emit("csrsi CSR_VSSTATUS, 2  // vsstatus.SIE")
        lcof_arm(t)
        anchor(t)
        wr(t, "vsctrctl", vctl)
        wr(t, "mctrctl", sctl)
        _, lab, _ = vwin(t, "VS", lambda: lcof_event(t), L.LCOFI_CAUSE, desc)
        off(t, "mctrctl")
        off(t, "vsctrctl")
        t.emit("csrw AI_HPM_EV, x0")
        with t.rv32_only():
            t.emit("csrw (AI_HPM_EV + 0x400), x0")
        t.li("x6", 1 << 13)
        t.emit("csrc mip, x6")
        t.emit("csrc CSR_VSIE, x6")
        t.emit("csrci CSR_VSSTATUS, 2")
        lab = t.label("fz")
        t.emit(f"{lab}:", 0)
        rd(t, "x7", "sctrstatus")
        if frozen:
            t.emit("srli x7, x7, 31")
            t.check("x7", 1 if MUT != "vs_lcofifrz_ignored" else 0, lab, f"{desc}: FROZEN=1")
            not_lcofi_record(t, "vstvec", desc)
        else:
            t.emit("srli x7, x7, 31")
            t.check("x7", 0, lab, f"{desc}: FROZEN=0")
        t.emit(f"csrw {c('sctrstatus')}, x0")

    def on() -> None:
        case(S | LCOFIFRZ, 0, 1, "LCOFI to VS-mode, vsctrctl.LCOFIFRZ=1")
        case(S, LCOFIFRZ, 0 if MUT != "vs_lcofifrz_uses_sctrctl" else 1, "LCOFI to VS-mode, only sctrctl.LCOFIFRZ")

    t.either("x8", on, lambda: None)
    t.li("x6", 1 << 13)
    t.emit("csrc CSR_HIDELEG, x6")
    with t.only_if("defined(SSAIA_SUPPORTED)"):
        t.emit("csrs 0x608, x6  // hvien[13] = 1 (hideleg[13] = 0): a virtual interrupt 13 for VS-mode")
        t.emit("csrr x8, 0x608")
        t.emit("and x8, x8, x6  // hvien[13] writable")

        def vcase(vctl: int, sctl: int, frozen: int, desc: str) -> None:
            t.li("x6", 1 << 13)
            t.emit("csrs CSR_VSIE, x6  // vsie[13]: enable of the virtual interrupt")
            t.emit("csrsi CSR_VSSTATUS, 2  // vsstatus.SIE")
            anchor(t)
            wr(t, "vsctrctl", vctl)
            wr(t, "mctrctl", sctl)
            t.li("x6", 1 << 13)
            t.emit("csrs 0x645, x6  // hvip[13]: the hypervisor pends a virtual LCOFI")
            vwin(t, "VS", lambda: L.delay(t, 20), L.LCOFI_CAUSE, desc)
            off(t, "mctrctl")
            off(t, "vsctrctl")
            t.li("x6", 1 << 13)
            t.emit("csrc 0x645, x6  // hvip[13] = 0")
            t.emit("csrc CSR_VSIE, x6")
            t.emit("csrci CSR_VSSTATUS, 2")
            lab = t.label("vfz")
            t.emit(f"{lab}:", 0)
            rd(t, "x7", "sctrstatus")
            t.emit("srli x7, x7, 31")
            if frozen:
                t.check("x7", 1 if MUT != "vs_lcofifrz_ignored" else 0, lab, f"{desc}: FROZEN=1")
                not_lcofi_record(t, "vstvec", desc)
            else:
                t.check("x7", 0 if MUT != "vs_lcofifrz_uses_sctrctl" else 1, lab, f"{desc}: FROZEN=0")
            t.emit(f"csrw {c('sctrstatus')}, x0")

        def von() -> None:
            vcase(S | LCOFIFRZ, 0, 1, "virtual LCOFI (hvip[13]) to VS-mode, vsctrctl.LCOFIFRZ=1")
            vcase(S, LCOFIFRZ, 0, "virtual LCOFI to VS-mode, only sctrctl.LCOFIFRZ")

        t.either("x8", von, lambda: None)
        t.li("x6", 1 << 13)
        t.emit("csrc 0x608, x6  // hvien[13] = 0")
    t.li("x6", 1 << 13)
    t.emit("csrc mideleg, x6")
    t.emit("csrc mie, x6")
    t.extra_data.append(".p2align 3\nctr_ev: .dword 0")
    return [t]


# ================================================================ generation
def gen() -> list[TestFile]:
    tests: list[TestFile] = []
    for fn in TESTS:
        tests += fn()
    return tests


def main() -> None:
    for t in gen():
        p = t.write()
        print(f"{p.relative_to(p.parents[2])}: ~{t.ninst} instructions")


if __name__ == "__main__":
    main()
