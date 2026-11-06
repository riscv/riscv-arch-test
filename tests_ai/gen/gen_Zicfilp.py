#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate tests_ai/Zicfilp: one test per normative rule about Zicfilp (landing pads).

Rules come from the Zicfilp parts of src/unpriv/cfi.adoc and src/priv/cfi.adoc, and from the ELP/LPE/lpad rules
in machine.adoc, supervisor.adoc and hypervisor.adoc. Most tests boot to S-mode, enable landing pads with
menvcfg.LPE (S), senvcfg.LPE (U, VU) and henvcfg.LPE (VS), and run each case in U, S, VU and VS. M-mode parts
(mseccfg.MLPE, mstatus.MPELP, medeleg) are in _Sm files. Helpers are in zicfilplib.py.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent))
import zicfilplib as z

z = importlib.reload(z)  # re-read AI_MUTANT when mutate.py reloads this generator
from aigen import TestFile, X

if TYPE_CHECKING:
    from zicfilplib import J as JType

SUITE = "Zicfilp"
MUT = z.MUT
J, T, lp, nonlp, ebreak, lp_case, land = z.J, z.T, z.lp, z.nonlp, z.ebreak, z.lp_case, z.land
H, ZCA, SWCHK, BRK = z.H, z.ZCA, z.SWCHK, z.BRK
ISSUE = z.ISSUE

MUTANTS = {
    # ELP state machine
    "x7_sets_elp": "an indirect jump through x7 sets ELP (no software-guarded branches)",
    "x5_sets_elp": "a jump through x5 sets ELP (only x1 is treated as a link register)",
    "x6_exempt": "a jump through x6 does not set ELP (off-by-one exemption next to x7)",
    "c_jr_no_elp": "c.jr and c.jalr do not set ELP",
    "rd_link_exempt": "a jalr whose rd is x1 or x5 does not set ELP (decode on rd instead of rs1)",
    "direct_sets_elp": "jal and c.jal set ELP",
    # landing-pad check
    "any_insn_ok": "any instruction is accepted as a landing pad",
    "no_align_check": "a misaligned lpad is accepted",
    "lpl0_checks": "lpad 0 also compares its label with x7",
    "label_wrong_field": "the label is compared with x7[19:0] instead of x7[31:12]",
    "label_old_x7": "lpad compares the x7 value from before the jump (a jalr that writes x7 is not seen)",
    "auipc_any_rd": "auipc with any rd is accepted as a landing pad",
    "lpad_keeps_elp": "a successful lpad leaves ELP at LP_EXPECTED",
    "misaligned_seq_faults": "a misaligned lpad faults even with ELP=NO_LP_EXPECTED",
    "mismatch_seq_faults": "a mismatched lpad faults even with ELP=NO_LP_EXPECTED",
    "disabled_lpad_checks": "with Zicfilp disabled, lpad still checks its label",
    # traps
    "tval_target": "a landing-pad fault writes the target address to xtval",
    "epc_at_jump": "a landing-pad fault reports the jump, not the target, in xepc",
    "pelp_not_saved": "a trap does not save ELP in xPELP",
    "pelp_set_only": "a trap sets xPELP when ELP=1 but never clears it when ELP=0",
    "pelp_saved_only_if_enabled": "a trap from a mode whose LPE is 0 leaves xPELP unchanged instead of writing ELP (0)",
    "elp_leaks_disabled": "with Zicfilp disabled, an indirect jump still sets ELP (saved in xPELP by a trap)",
    "priority_illegal": "an illegal or virtual instruction at the target outranks the landing-pad fault",
    "priority_access": "the landing-pad fault outranks an instruction access fault",
    "no_link_on_fault": "a jump whose target faults does not write its link register",
    "irq_pelp_zero": "an interrupt taken at a landing-pad target saves xPELP=0",
    "m_fault_delegated": "an M-mode landing-pad fault is delegated to S when medeleg[18]=1",
    "deleg_ignored": "landing-pad faults from S/U ignore medeleg[18] (always taken in M)",
    # xRET
    "xret_ignores_lpe": "an xRET restores ELP from xPELP even when the new mode's LPE is 0",
    "xret_no_restore": "an xRET does not restore ELP from xPELP",
    "xret_keeps_pelp": "an xRET leaves xPELP unchanged",
    "xret_uses_cur_lpe": "an xRET restores ELP using the LPE of the mode executing it, not the new mode",
    # enables and fields
    "mlpe_ignored": "M-mode enforcement follows menvcfg.LPE instead of mseccfg.MLPE",
    "mlpe_enables_all": "mseccfg.MLPE=1 also enables landing pads in S and U",
    "menvcfg_enables_u": "U-mode enforcement follows menvcfg.LPE (as if S were absent)",
    "senvcfg_enables_s": "S-mode enforcement follows senvcfg.LPE",
    "henvcfg_ignored": "VS-mode enforcement follows menvcfg.LPE instead of henvcfg.LPE",
    "vu_uses_henvcfg": "VU-mode enforcement follows henvcfg.LPE instead of senvcfg.LPE",
    "mpelp_ro_mlpe0": "mstatus.MPELP is read-only zero while mseccfg.MLPE=0",
    "spelp_not_writable": "sstatus.SPELP is read-only",
    "sstatus_spelp_v1_mstatus": "with V=1, sstatus.SPELP accesses mstatus.SPELP instead of vsstatus.SPELP",
    "vs_trap_writes_mstatus": "a trap into VS-mode saves ELP in mstatus.SPELP instead of vsstatus.SPELP",
    "hs_trap_writes_vsstatus": "a trap into HS-mode also overwrites vsstatus.SPELP",
    "mlpe_reset_one": "mseccfg.MLPE resets to 1",
    "lpe_field_ro": "the LPE/MLPE enable fields are read-only zero",
}

ALL_ON = {"mlpe": 0, "menvcfg": 1, "senvcfg": 1, "henvcfg": 1}
LAB = 0x5A3C9  # a typical landing-pad label


def setup_all(t: TestFile) -> None:
    t.comment("Enable landing pads in S (menvcfg.LPE), U and VU (senvcfg.LPE) and VS (henvcfg.LPE)")
    z.s_enables(t, True, True, True)


def modes(t: TestFile, body) -> None:  # noqa: ANN001
    """body(mode) in U and S, then VU and VS under H."""
    body("U")
    body("S")
    with t.only_if(H):
        body("VU")
        body("VS")


def new(rule: str, *, sm: bool = False, required: list[str] | None = None) -> TestFile:
    return z.new(SUITE, rule, sm=sm, required=required)


def sentinel(reg: str = "x9", v: int = 0x5A5) -> list[str]:
    return [f"li {reg}, {v}"]


# ================================================================= unprivileged rules (src/unpriv/cfi.adoc)
def t_call_term() -> TestFile:
    t = new("cfi_call_term")
    t.describe(
        source=z.UNPRIV,
        rule_text="The term call is used to refer to a jal, jalr or c.jal instruction with a link register as "
        "destination, i.e., rd!=x0. Conventionally, the link register is x1 or x5. A call using jal or c.jal is "
        "termed a direct call. A c.jalr expands to jalr[x1,0(rs1)] and thus it is a call. A call using jalr or "
        "c.jalr is termed an indirect call.",
        context="Zicfilp requires a landing pad at the target of an indirect call (unless rs1 is x1, x5 or x7) and "
        "never at the target of a direct call. Landing pads are enabled in every mode. A missing landing pad is a "
        "software-check exception (cause 18) at the target.",
        plan="In U, S, VU and VS (H):\n"
        "1. Indirect calls jalr x1/x5/x9, 0(x6 or x8) and c.jalr x6 (C) to a non-lpad fault at the target; the call "
        "still writes its link register. To lpad 0 they do not fault.\n"
        "2. Direct calls jal x1, jal x5 and c.jal (RV32 with C) to a non-lpad do not fault.\n"
        "3. A jalr call whose rs1 is a link register (jalr x1, 0(x1); jalr x5, 0(x5)) does not fault.",
    )
    setup_all(t)

    def body(m: str) -> None:
        for rd, rs in ((1, 6), (5, 8), (9, 6)):
            lp_case(t, m, J("jalr", rd, rs), nonlp(), f"indirect call jalr x{rd}, 0(x{rs})")
        land(
            t,
            m,
            J("jalr", 1, 8),
            nonlp(),
            SWCHK,
            "indirect call writes x1 before the target faults",
            link=("x1", 4) if MUT != "no_link_on_fault" else ("x1", 8),
        )
        lp_case(t, m, J("jalr", 1, 6), lp(0), "indirect call to lpad 0")
        with t.only_if(ZCA):
            lp_case(t, m, J("c.jalr", rs1=6), nonlp(), "indirect call c.jalr x6")
            lp_case(t, m, J("c.jalr", rs1=8), lp(0), "c.jalr x8 to lpad 0")
        for rd in (1, 5):
            lp_case(t, m, J("jal", rd), nonlp(), f"direct call jal x{rd}")
        with t.only_if(ZCA), t.rv32_only():
            lp_case(t, m, J("c.jal"), nonlp(), "direct call c.jal")
        for r in (1, 5):
            lp_case(t, m, J("jalr", r, r), nonlp(), f"call through its link register jalr x{r}, 0(x{r})")

    modes(t, body)
    z.s_teardown(t)
    return t


def t_return_term() -> TestFile:
    t = new("cfi_return_term")
    t.describe(
        source=z.UNPRIV,
        rule_text="The term return is used to refer to a jalr instruction with rd=x0 and with rs1=x1 or rs1=x5. A "
        "c.jr instruction expands to jalr[x0,0(rs1)] and is a return if rs1=x1 or rs1=x5.",
        context="A return does not set ELP, so its target needs no landing pad. Landing pads are enabled in every "
        "mode.",
        plan="In U, S, VU and VS (H):\n"
        "1. Returns jalr x0, 0(x1), jalr x0, 0(x5), jalr x0, 8(x1) and c.jr x1, c.jr x5 (C) to a non-lpad do not "
        "fault. A return to ebreak takes a breakpoint with xPELP=0, so ELP was not set.\n"
        "2. Jumps that are not returns, jalr x0, 0(x6), jalr x0, 0(x8) and c.jr x6, fault.",
    )
    setup_all(t)

    def body(m: str) -> None:
        for r, imm in ((1, 0), (5, 0), (1, 8)):
            lp_case(t, m, J("jalr", 0, r, imm), nonlp(), f"return jalr x0, {imm}(x{r})")
        lp_case(t, m, J("jalr", 0, 5), ebreak(), "return to ebreak")
        with t.only_if(ZCA):
            for r in (1, 5):
                lp_case(t, m, J("c.jr", rs1=r), nonlp(), f"return c.jr x{r}")
            lp_case(t, m, J("c.jr", rs1=6), nonlp(), "c.jr x6 is not a return")
        for r in (6, 8):
            lp_case(t, m, J("jalr", 0, r), nonlp(), f"jalr x0, 0(x{r}) is not a return")

    modes(t, body)
    z.s_teardown(t)
    return t


def t_indirect_jump_term() -> TestFile:
    t = new("cfi_indirect_jump_term")
    t.describe(
        source=z.UNPRIV,
        rule_text="The term indirect jump is used to refer to a jalr instruction with rd=x0 and where the rs1 is not "
        "x1 or x5 (i.e., not a return). A c.jr instruction where rs1 is not x1 or x5 (i.e., not a return) is an "
        "indirect jump.",
        context="An indirect jump sets ELP unless rs1 is x7 (a software-guarded branch). Landing pads are enabled in "
        "every mode.",
        plan="In U, S, VU and VS (H):\n"
        "1. jalr x0, 0(rs1) for rs1 in {x6, x8, x9, x14, x15} and c.jr x6, x8, x15 (C) to a non-lpad fault at "
        "the target with xPELP=1; to lpad 0 they do not fault.\n"
        "2. jalr x0, 0(x7) and c.jr x7 (software-guarded) do not fault.",
    )
    setup_all(t)

    def body(m: str) -> None:
        for r in (6, 8, 9, 14, 15):
            lp_case(t, m, J("jalr", 0, r), nonlp(), f"indirect jump jalr x0, 0(x{r})")
        lp_case(t, m, J("jalr", 0, 9), lp(0), "indirect jump to lpad 0")
        lp_case(t, m, J("jalr", 0, 7), nonlp(), "software-guarded jalr x0, 0(x7)")
        with t.only_if(ZCA):
            for r in (6, 8, 15, 7):
                lp_case(t, m, J("c.jr", rs1=r), nonlp(), f"c.jr x{r}")
            lp_case(t, m, J("c.jr", rs1=6), lp(0), "c.jr x6 to lpad 0")

    modes(t, body)
    z.s_teardown(t)
    return t


def t_lpad_enc() -> TestFile:
    t = new("Zicfilp_lpad_enc")
    t.describe(
        source=z.UNPRIV,
        rule_text="The lpad instruction is encoded using the auipc major opcode with rd=x0.",
        context="Only auipc with rd=x0 is a landing pad. Other auipc instructions and other HINTs with rd=x0 (such as "
        "lui x0) are ordinary instructions, which fault when ELP=LP_EXPECTED without executing.",
        plan="In U, S, VU and VS (H), after an indirect jump (ELP=LP_EXPECTED):\n"
        "1. auipc x0, 0 and auipc x0, label (x7 matching) land without a fault.\n"
        "2. auipc x9, 0 and auipc x1, label fault (cause 18), and x9 keeps its old value (the auipc did not "
        "execute).\n"
        "3. lui x0, label (another rd=x0 HINT) and addi x0, x0, 0 fault.\n"
        "4. Sequential execution of auipc x0, label with a mismatched x7 is a no-op (no fault).",
    )
    setup_all(t)
    aup = MUT == "auipc_any_rd"

    def body(m: str) -> None:
        lp_case(t, m, J("jalr", 0, 6), lp(0), "auipc x0, 0")
        lp_case(t, m, J("jalr", 0, 6), lp(LAB), "auipc x0, label", x7=LAB << 12)
        tg = T(["auipc x9, 0  // rd=x9: not an lpad"], "auipc x9, 0", check=[("x9", 0x5A5, "x9 unchanged")])
        land(t, m, J("jalr", 0, 6), tg, "ok" if aup else SWCHK, "auipc with rd=x9", pre=["li x9, 0x5A5"], pelp=1)
        tg = T([f".word {(LAB << 12) | (1 << 7) | 0x17:#x}  // auipc x1, {LAB:#x}"], "auipc x1, label")
        land(t, m, J("jalr", 0, 8), tg, "ok" if aup else SWCHK, "auipc with rd=x1", x7=X(LAB << 12, LAB << 12))
        tg = T([f"lui x0, {LAB:#x}  // rd=x0 HINT with the lui opcode"], "lui x0, label")
        lp_case(t, m, J("jalr", 0, 6), tg, "lui x0 is not an lpad", x7=LAB << 12)
        lp_case(t, m, J("jalr", 0, 6), nonlp(), "addi x0, x0, 0 is not an lpad")
        lp_case(t, m, J("seq"), lp(LAB ^ 1), "lpad reached sequentially (ELP clear)", x7=LAB << 12)

    modes(t, body)
    z.s_teardown(t)
    return t


def t_lpad_expected() -> TestFile:
    t = new("Zicfilp_lpad_expected")
    t.describe(
        source=z.UNPRIV,
        rule_text="The zicfilp extension, when enabled, determines if an indirect call or an indirect jump must "
        "land on a landing pad, as specified in IND_CALL_JMP. If is_lp_expected is 1, then the hart updates "
        "the elp to LP_EXPECTED. [is_lp_expected = ((JALR || C.JR || C.JALR) && (rs1 != x1) && (rs1 != x5) && "
        "(rs1 != x7)) ? 1 : 0]",
        context="Zicfilp is enabled in every mode (menvcfg.LPE, senvcfg.LPE, henvcfg.LPE). ELP=LP_EXPECTED is "
        "observed as a software-check exception (cause 18, xtval 2 or 0) at a target that is not a landing pad, "
        "with xepc at the target and xPELP=1 saved. ELP=NO_LP_EXPECTED is observed as no trap at the same target.",
        plan="1. U-mode: jalr to a non-lpad for rs1 in {x1, x5, x6, x7, x8, x9, x14, x15} with "
        "rd = x0, and for rd in {x1, x5, x7, x9} with rs1 in {x6, x1, x5, x7}; a fault exactly when rs1 is "
        "not x1, x5 or x7. A nonzero immediate (-4, +8, 2047, -2048) and an odd rs1+imm do not change it.\n"
        "2. With C: c.jr and c.jalr for rs1 in {x1, x5, x6, x7, x9}.\n"
        "3. Instructions that are not JALR/C.JR/C.JALR do not set ELP: jal (rd x0, x1, x5), c.j, c.jal (RV32), a "
        "taken beq, and falling through.\n"
        "4. The fault and no-fault classes (rs1 x1, x6, x7; c.jr/c.jalr x8; jal x1) in S, VU and VS (H).",
    )
    setup_all(t)

    def sweep(mode: str, full: bool) -> None:
        rs1s = [1, 5, 6, 7, 8, 9, 14, 15] if full else [1, 6, 7]
        for r in rs1s:
            lp_case(t, mode, J("jalr", 0, r), nonlp(), f"jalr rd=x0 rs1=x{r}")
        if full:
            for rd in (1, 5, 7, 9):
                for r in (6, 1, 5, 7):
                    if r != rd:
                        lp_case(t, mode, J("jalr", rd, r), nonlp(), f"jalr rd=x{rd} rs1=x{r}")
            for imm, odd in ((-4, False), (8, False), (2047, False), (-2048, False), (0, True), (5, True)):
                lp_case(t, mode, J("jalr", 0, 8, imm, odd), nonlp(), f"jalr imm={imm}{' odd' if odd else ''}")
        with t.only_if(ZCA):
            for r in [1, 5, 6, 7, 9] if full else [8]:
                lp_case(t, mode, J("c.jr", rs1=r), nonlp(), f"c.jr x{r}")
                lp_case(t, mode, J("c.jalr", rs1=r), nonlp(), f"c.jalr x{r}")
        for jj in (J("jal", 0), J("jal", 1), J("jal", 5), J("beq"), J("seq")) if full else (J("jal", 1),):
            lp_case(t, mode, jj, nonlp(), f"{jj.text()} (not an indirect transfer)")
        if full:
            with t.only_if(ZCA):
                lp_case(t, mode, J("c.j"), nonlp(), "c.j (direct)")
                with t.rv32_only():
                    lp_case(t, mode, J("c.jal"), nonlp(), "c.jal (direct)")

    sweep("U", True)
    sweep("S", False)
    with t.only_if(H):
        sweep("VU", False)
        sweep("VS", False)
    z.s_teardown(t)
    return t


def t_indirect_branch_lpad() -> TestFile:
    t = new("Zicfilp_indirect_branch_lpad")
    t.describe(
        source=z.UNPRIV,
        rule_text="An indirect branch using jalr, c.jalr, or c.jr with rs1 as x7 is termed a software-guarded "
        "branch. Such branches do not need to land on a lpad instruction and thus do not set elp to LP_EXPECTED.",
        context="Landing pads are enabled in every mode. Not setting ELP is checked two ways: no fault at a non-lpad "
        "target, and a breakpoint at an ebreak target that saves xPELP=0 (ELP was not set and merely ignored).",
        plan="In U, S, VU and VS (H):\n"
        "1. jalr rd, imm(x7) for rd in {x0, x1, x5, x6, x7} and imm in {0, 8, -4} to a non-lpad: no fault.\n"
        "2. c.jr x7 and c.jalr x7 (C) to a non-lpad: no fault.\n"
        "3. jalr x0, 0(x7) and c.jr x7 to ebreak: breakpoint (cause 3) with xPELP=0.\n"
        "4. Contrast: jalr x0, 0(x6) and jalr x0, 0(x8) (the neighbors of x7) to a non-lpad fault.",
    )
    setup_all(t)

    def body(m: str) -> None:
        for rd, imm in ((0, 0), (1, 0), (5, 0), (6, 8), (7, 0), (0, -4)):
            lp_case(t, m, J("jalr", rd, 7, imm), nonlp(), f"software-guarded jalr x{rd}, {imm}(x7)")
        lp_case(t, m, J("jalr", 0, 7), ebreak(), "software-guarded jalr to ebreak")
        with t.only_if(ZCA):
            lp_case(t, m, J("c.jr", rs1=7), nonlp(), "software-guarded c.jr x7")
            lp_case(t, m, J("c.jalr", rs1=7), nonlp(), "software-guarded c.jalr x7")
            lp_case(t, m, J("c.jr", rs1=7), ebreak(), "software-guarded c.jr x7 to ebreak")
        for r in (6, 8):
            lp_case(t, m, J("jalr", 0, r), nonlp(), f"jalr x0, 0(x{r}) is not software-guarded")

    modes(t, body)
    z.s_teardown(t)
    return t


def t_lpad_label() -> TestFile:
    t = new("Zicfilp_lpad_label")
    t.describe(
        source=z.UNPRIV,
        rule_text="To support labeled landing pads, the indirect call/jump sites establish an expected landing pad "
        "label (e.g., using the lui instruction) in the bits 31:12 of the x7 register.",
        context="lpad compares its nonzero label with x7[31:12] when ELP=LP_EXPECTED. Bits 11:0 and, on RV64, bits "
        "63:32 of x7 are not part of the label. Landing pads are enabled in every mode.",
        plan="In U (all cases) and S, VU, VS (H) (a subset):\n"
        "1. Labels 1, 0xFFFFF, 0x80000, 0x55555, 0xAAAAA and random ones match an x7 holding the label in bits "
        "31:12 with random bits 11:0 and (RV64) random bits 63:32: no fault.\n"
        "2. x7 differing in one label bit (bit 12, 13, 21, 30 or 31): fault.\n"
        "3. lui x7 immediately before the jump (back-to-back), and x7 set long before.\n"
        "4. The label is read after the jump: jalr x7, 0(x6) writes x7 = the link address, and a landing pad whose "
        "label is the link address's bits 31:12 (written at run time into a data word, then fence.i) matches; one "
        "differing in bit 0 faults. The landing pad's next instruction returns through x7 (software-guarded).",
    )
    setup_all(t)
    rng = t.rng
    labels = [1, 0xFFFFF, 0x80000, 0x55555, 0xAAAAA, rng.getrandbits(20) | 1, rng.getrandbits(20) | 0x80000]

    def x7_for(label: int) -> int:
        return (rng.getrandbits(32) << 32) | (label << 12) | rng.getrandbits(12)

    def body(m: str) -> None:
        full = m == "U"
        for L in labels if full else labels[:3]:
            lp_case(t, m, J("jalr", 0, 6), lp(L), f"label {L:#x} matches x7[31:12]", x7=x7_for(L))
        for bit in (12, 13, 21, 30, 31) if full else (12, 31):
            L = labels[5]
            x7 = x7_for(L) ^ (1 << bit)
            lp_case(t, m, J("jalr", 0, 8), lp(L), f"label {L:#x}, x7 bit {bit} flipped", x7=x7)
        L = 0x6B2D1
        land(t, m, J("jalr", 0, 6), lp(L), "ok", "lui x7 immediately before the jump", late=[f"lui x7, {L:#x}"])
        land(
            t,
            m,
            J("jalr", 0, 6),
            lp(L),
            SWCHK,
            "lui x7 (one label bit off) immediately before the jump",
            late=[f"lui x7, {L ^ 0x40:#x}"],
            pelp=1,
        )
        if full or m == "S":
            rd_x7_case(t, m, match=True)
            rd_x7_case(t, m, match=False)

    modes(t, body)
    z.s_teardown(t)
    return t


def rd_x7_case(t: TestFile, m: str, match: bool) -> None:
    """jalr x7, 0(x6) to a run-time-built landing pad in a data word: lpad (link[31:12] or that ^ 1); jalr x0, 0(x7).
    The lpad must compare the x7 the jalr wrote."""
    code = f"{t.rule}_rtcode"
    if not any(code in ln for ln in t.extra_data):
        t.extra_data += [
            "  .p2align 3",
            f"{code}:",
            "  .word 0x00000017, 0x00038067  // lpad (rewritten); jalr x0, 0(x7)",
        ]
    jl, landl, after = t.label("jx7"), t.label("land"), t.label("after")
    desc = f"jalr x7, 0(x6) to an lpad labeled with {'the' if match else 'not the'} link address bits 31:12"
    t.comment(desc)
    t.comment("build the landing pad: (link & 0xFFFFF000) | 0x17 (^ 0x1000 for a mismatch), then fence.i")
    t.emit(f"LA(x8, {jl})", 2)
    t.emit("addi x8, x8, 4  // the link address")
    t.emit("srli x8, x8, 12")
    if not match:
        t.emit("xori x8, x8, 1")
    t.emit("slli x8, x8, 12")
    t.emit("ori x8, x8, 0x17")
    t.emit(f"LA(x9, {code})", 2)
    t.emit("sw x8, 0(x9)")
    t.emit("fence.i")
    z.set_resume(t, landl)
    t.allow(1)
    if m != t.cur:
        t.enter(m)
    t.emit(f"LA(x6, {code})", 2)
    t.li("x7", 0)
    t.emit(f"{jl}:", 0)
    t.emit("jalr x7, 0(x6)")
    t.emit(f"j {after}  // the landing pad returns here through x7")
    t.emit(f"{landl}:", 0)
    t.emit("auipc x0, 0  // lpad 0: recovery landing pad")
    t.emit(f"{after}:", 0)
    z.clear_resume(t)
    if m != t.cur:
        t.leave()
    ok = match != (MUT == "label_old_x7")
    t.outcome("ok" if ok else SWCHK, code, f"{desc} in {m}-mode", z.LP_TVAL, origin=m)


def t_lpad_imm_enc() -> TestFile:
    t = new("Zicfilp_lpad_imm_enc")
    t.describe(
        source=z.UNPRIV,
        rule_text="The lpad instruction is encoded with a 20-bit immediate value called the landing-pad-label (LPL) "
        "that is matched to the expected landing pad label. When LPL is encoded as zero, the lpad instruction does "
        "not perform the label check and in programs built with this single label mode of operation the indirect "
        "call/jump sites do not need to establish an expected landing pad label value in x7.",
        context="Landing pads are enabled in every mode. The label is all 20 bits of the immediate (instruction bits "
        "31:12).",
        plan="In U (all cases), S, VU and VS (H):\n"
        "1. lpad 0 with x7 = 0, all ones, 0xFFFFF000 and random: no fault.\n"
        "2. lpad with a nonzero label and x7 = 0: fault (labels 1, 0x80000, 0xFFFFF).\n"
        "3. All 20 bits are compared: lpad 0xFFFFF with x7[31:12] = 0x7FFFF faults, with 0xFFFFF does not; lpad 1 "
        "with x7[31:12] = 0 faults.",
    )
    setup_all(t)

    def body(m: str) -> None:
        full = m == "U"
        for x7 in (0, (1 << 64) - 1, 0xFFFFF000, t.rand(64)) if full else (0, (1 << 64) - 1):
            lp_case(t, m, J("jalr", 0, 6), lp(0), "lpad 0 with any x7", x7=x7)
        for L in (1, 0x80000, 0xFFFFF) if full else (1,):
            lp_case(t, m, J("jalr", 0, 6), lp(L), f"lpad {L:#x} with x7 = 0", x7=0)
        lp_case(t, m, J("jalr", 0, 8), lp(0xFFFFF), "lpad 0xFFFFF with x7[31:12]=0x7FFFF", x7=0x7FFFF000)
        lp_case(t, m, J("jalr", 0, 8), lp(0xFFFFF), "lpad 0xFFFFF with x7[31:12]=0xFFFFF", x7=0xFFFFF000)

    modes(t, body)
    z.s_teardown(t)
    return t


def t_elp_lpad_expected() -> TestFile:
    t = new("Zicfilp_elp_lpad_expected")
    t.describe(
        source=z.UNPRIV,
        rule_text="When elp is set to LP_EXPECTED, if the next instruction in the instruction stream is not 4-byte "
        "aligned, or is not lpad, or if the landing pad label encoded in lpad is not zero and does not match the "
        "expected landing pad label in bits 31:12 of the x7 register, then a software-check exception (cause=18) "
        'with xtval set to "landing pad fault (code=2)" is raised else the elp is updated to NO_LP_EXPECTED.',
        context="Landing pads are enabled in every mode. The exception is raised at the target, not at the jump "
        f'({ISSUE}1584: "Its the instruction at the target"). xtval may also be 0, the "No information '
        'provided" software-check code (machine.adoc, supervisor.adoc).',
        issues=f"{ISSUE}1584: xepc is the target instruction for all three conditions.",
        plan="In U, S, VU and VS (H), after an indirect jump:\n"
        "1. Each condition alone faults with cause 18, xepc = the target, xtval in {0, 2}, xPELP = 1: a non-lpad; "
        "a mismatched label; (C) a misaligned lpad 0, and a misaligned lpad with a matching label.\n"
        "2. Otherwise ELP becomes NO_LP_EXPECTED: an ebreak right after the lpad takes a breakpoint with xPELP=0, "
        "and a mismatched lpad right after the lpad does not fault.",
    )
    setup_all(t)
    keep = MUT == "lpad_keeps_elp"

    def body(m: str) -> None:
        lp_case(t, m, J("jalr", 0, 6), nonlp(), "not an lpad")
        lp_case(t, m, J("jalr", 0, 6), lp(LAB), "label mismatch", x7=(LAB ^ 0x800) << 12)
        with t.only_if(ZCA):
            lp_case(t, m, J("jalr", 0, 6), lp(0, True), "misaligned lpad 0")
            lp_case(t, m, J("jalr", 0, 8), lp(LAB, True), "misaligned lpad with a matching label", x7=LAB << 12)
        tg = T(
            [z.lpad(LAB), "SECOND:", "ebreak"], f"lpad {LAB:#x}; ebreak", size=8, traps=BRK, tval="TGT0", second=True
        )
        if keep:
            land(t, m, J("jalr", 0, 6), tg, SWCHK, "ebreak after a matching lpad", x7=X(LAB << 12, LAB << 12))
        else:
            land(t, m, J("jalr", 0, 6), tg, BRK, "ebreak after a matching lpad", x7=X(LAB << 12, LAB << 12), pelp=0)
        tg = T([z.lpad(0), z.lpad(LAB ^ 3)], "lpad 0; mismatched lpad", size=8)
        land(
            t,
            m,
            J("jalr", 0, 9),
            tg,
            SWCHK if keep else "ok",
            "mismatched lpad after lpad 0",
            x7=X(LAB << 12, LAB << 12),
        )

    modes(t, body)
    z.s_teardown(t)
    return t


def allowed_targets() -> list:
    """Instructions that are not lpad, each with checks that it did not execute (x9 holds 0x5A5 before)."""
    keep9 = [("x9", 0x5A5, "x9 unchanged")]
    return [
        T(["addi x9, x9, 1"], "addi x9, x9, 1", check=keep9),
        T(["lw x9, 0(x8)"], "lw x9, 0(x8)", check=keep9),
        T(["sw x9, 0(x8)"], "sw x9, 0(x8)", check=[("x6", "DATAW0", "the data word is unchanged")]),
        T(["beq x0, x0, LAND"], "taken beq"),
        T(["jal x9, LAND"], "jal x9", check=keep9),
        T(["auipc x9, 0"], "auipc x9, 0", check=keep9),
        T(["lui x9, 0x12345"], "lui x9", check=keep9),
        T(["csrr x9, cycle"], "csrr x9, cycle", check=keep9),
        T(["fence"], "fence"),
        T(["fence.i"], "fence.i"),
        T(["ebreak"], "ebreak"),
        T(["wfi"], "wfi"),
    ]


def t_lpad_enabled_instr_allowed() -> TestFile:
    t = new("Zicfilp_lpad_enabled_instr_allowed")
    t.describe(
        source=z.UNPRIV,
        rule_text="When zicfilp is enabled, lpad is the only instruction allowed to execute when the elp state is "
        "LP_EXPECTED. If zicfilp is not enabled then the instruction is a no-op.",
        context="Every other instruction faults (cause 18) without executing: no register or memory update, no "
        "transfer, no other exception. ecall is not used, since it is the T-SBI entry.",
        plan="1. Enabled in U, S, VU and VS (H), after jalr x0, 0(x6): addi, lw, sw, a taken beq, jal, auipc rd!=0, "
        "lui, csrr cycle, fence, fence.i, ebreak, wfi and (C) c.nop, c.addi each fault with cause 18; x9 (0x5A5 "
        "before) is unchanged and the stored-to word keeps its value. lpad 0 does not fault.\n"
        "2. Not enabled (all LPE bits 0), in the same modes: lpad with a mismatched label reached by jalr, and (C) a "
        "misaligned lpad, are no-ops: no fault, x7 and x9 unchanged.",
    )
    setup_all(t)

    def enabled(m: str) -> None:
        for tg in allowed_targets():
            pre = ["li x9, 0x5A5"]
            if "x8" in tg.lines[0]:
                pre = ["li x9, 0x5A5", "LA(x8, DATAW)"]
            land(
                t,
                m,
                J("jalr", 0, 6),
                tg,
                "ok" if MUT == "any_insn_ok" else SWCHK,
                f"{tg.note} is not lpad",
                pre=[p.replace("DATAW", z.data_word(t)) for p in pre],
                pelp=1,
            )
        with t.only_if(ZCA):
            for enc, note in ((0x0001, "c.nop"), (0x04A5, "c.addi x9, 9")):
                tg = T([f".hword {enc:#x}  // {note}"], note, size=2, check=[("x9", 0x5A5, "x9 unchanged")])
                land(
                    t,
                    m,
                    J("jalr", 0, 6),
                    tg,
                    "ok" if MUT == "any_insn_ok" else SWCHK,
                    f"{note} is not lpad",
                    pre=["li x9, 0x5A5"],
                    pelp=1,
                )
        lp_case(t, m, J("jalr", 0, 6), lp(0), "lpad 0 is allowed")

    modes(t, enabled)
    t.comment("Zicfilp not enabled in any mode")
    z.s_enables(t, False, False, False)

    def disabled(m: str) -> None:
        tg = T(
            [z.lpad(LAB)],
            f"lpad {LAB:#x}",
            lp=LAB,
            check=[("x9", 0x5A5, "x9 unchanged"), ("x7", X(0x1000, 0x1000), "x7 unchanged")],
        )
        exp = SWCHK if MUT == "disabled_lpad_checks" else "ok"
        land(
            t,
            m,
            J("jalr", 0, 6),
            tg,
            exp,
            "disabled: mismatched lpad is a no-op",
            pre=["li x9, 0x5A5"],
            x7=X(0x1000, 0x1000),
        )
        with t.only_if(ZCA):
            lp_case(t, m, J("jalr", 0, 6), lp(0, True), "disabled: misaligned lpad is a no-op", enforced=False)

    modes(t, disabled)
    return t


def t_lpad_enabled_exception() -> TestFile:
    t = new("Zicfilp_lpad_enabled_exception")
    t.describe(
        source=z.UNPRIV,
        rule_text="If zicfilp is enabled, the lpad instruction causes a software-check exception with xtval set to "
        '"landing pad fault (code=2)" if any of the following conditions are true: [the pc is not 4-byte aligned '
        "and elp is LP_EXPECTED; the elp is LP_EXPECTED and the LPL is not zero and the LPL does not match the "
        "expected landing pad label in bits 31:12 of the x7 register]",
        context="Landing pads are enabled in every mode. The exception is the lpad's own: cause 18, xepc = the lpad, "
        'xtval in {2, 0} (0 is the "No information provided" code).',
        plan="In U, S, VU and VS (H):\n"
        "1. After jalr, a mismatched lpad (labels 1 and 0xFFFFF) and (C) a misaligned lpad 0: cause 18 at the lpad, "
        "xtval in {0, 2}, from the current mode, xPELP=1.\n"
        "2. The same lpads reached with ELP clear (falling through, jal, a software-guarded jump) do not fault.",
    )
    setup_all(t)

    def body(m: str) -> None:
        for L in (1, 0xFFFFF):
            lp_case(t, m, J("jalr", 0, 6), lp(L), f"lpad {L:#x} mismatched", x7=(L ^ 0x10) << 12)
        with t.only_if(ZCA):
            lp_case(t, m, J("jalr", 0, 8), lp(0, True), "misaligned lpad 0")
        for jj in (J("seq"), J("jal", 0), J("jalr", 0, 7)):
            exp = SWCHK if MUT == "mismatch_seq_faults" else "ok"
            land(
                t,
                m,
                jj,
                lp(LAB),
                exp,
                f"mismatched lpad with ELP clear ({jj.text()})",
                x7=X(0, 0),
                pelp=0 if exp != "ok" else None,
            )

    modes(t, body)
    z.s_teardown(t)
    return t


def t_lpad_alignment_exception() -> TestFile:
    t = new("Zicfilp_lpad_alignment_exception")
    t.describe(
        source=z.UNPRIV,
        rule_text="The pc is not 4-byte aligned and elp is LP_EXPECTED.",
        context="A condition for the lpad software-check exception. A 2-mod-4 pc needs C (IALIGN=16), so the cases "
        "run only #ifdef ZCA_SUPPORTED. jalr clears bit 0 of rs1+imm, so an odd rs1+imm still targets the aligned "
        "address. Landing pads are enabled in every mode.",
        plan="In U, S, VU and VS (H), with C:\n"
        "1. A misaligned lpad 0 and a misaligned lpad with a matching label, reached by jalr x0, 0(x6), c.jr x8 "
        "and jalr with an odd rs1+imm (tgt+1): cause 18 at the lpad.\n"
        "2. An aligned lpad 0 reached with rs1+imm = tgt+1: no fault.\n"
        "3. A misaligned lpad reached with ELP clear: falling through, jal, c.j, jalr x0, 0(x7) and a return: no "
        "fault.",
    )
    setup_all(t)

    def body(m: str) -> None:
        with t.only_if(ZCA):
            lp_case(t, m, J("jalr", 0, 6), lp(0, True), "misaligned lpad 0")
            lp_case(t, m, J("jalr", 0, 6), lp(LAB, True), "misaligned matching lpad", x7=LAB << 12)
            lp_case(t, m, J("c.jr", rs1=8), lp(0, True), "c.jr to a misaligned lpad")
            lp_case(t, m, J("jalr", 0, 9, 0, True), lp(0, True), "odd rs1+imm to a misaligned lpad")
            lp_case(t, m, J("jalr", 0, 9, 0, True), lp(0), "odd rs1+imm to an aligned lpad")
            for jj in (J("seq"), J("jal", 0), J("c.j"), J("jalr", 0, 7), J("jalr", 0, 1)):
                exp = SWCHK if MUT == "misaligned_seq_faults" else "ok"
                land(
                    t,
                    m,
                    jj,
                    lp(0, True),
                    exp,
                    f"misaligned lpad with ELP clear ({jj.text()})",
                    pelp=0 if exp != "ok" else None,
                )

    modes(t, body)
    z.s_teardown(t)
    return t


def t_lpad_label_exception() -> TestFile:
    t = new("Zicfilp_lpad_label_exception")
    t.describe(
        source=z.UNPRIV,
        rule_text="The elp is LP_EXPECTED and the LPL is not zero and the LPL does not match the expected landing pad "
        "label in bits 31:12 of the x7 register.",
        context="A condition for the lpad software-check exception. Landing pads are enabled in every mode.",
        plan="In U, S, VU and VS (H):\n"
        "1. ELP=LP_EXPECTED (jalr x0, 0(x6)), LPL != 0, mismatch (x7[31:12] = LPL ^ 1, LPL ^ 0x80000, 0): cause 18.\n"
        "2. ELP=LP_EXPECTED, LPL != 0, match: no fault. ELP=LP_EXPECTED, LPL = 0, x7[31:12] != 0: no fault.\n"
        "3. ELP clear (falling through, jal, jalr x0, 0(x7), return through x5) with a mismatched LPL: no fault.",
    )
    setup_all(t)

    def body(m: str) -> None:
        for d in (1, 0x80000):
            lp_case(t, m, J("jalr", 0, 6), lp(LAB), f"label mismatch (x7 label ^ {d:#x})", x7=(LAB ^ d) << 12)
        lp_case(t, m, J("jalr", 0, 6), lp(LAB), "label mismatch (x7 = 0)", x7=0)
        lp_case(t, m, J("jalr", 0, 6), lp(LAB), "label match", x7=LAB << 12)
        lp_case(t, m, J("jalr", 0, 6), lp(0), "LPL = 0", x7=LAB << 12)
        for jj in (J("seq"), J("jal", 0), J("jalr", 0, 7), J("jalr", 0, 5)):
            exp = SWCHK if MUT == "mismatch_seq_faults" else "ok"
            land(
                t,
                m,
                jj,
                lp(LAB),
                exp,
                f"mismatch with ELP clear ({jj.text()})",
                x7=X(0x1000, 0x1000),
                pelp=0 if exp != "ok" else None,
            )

    modes(t, body)
    z.s_teardown(t)
    return t


def t_lpad_no_sw_exception() -> TestFile:
    t = new("Zicfilp_lpad_no_sw_exception")
    t.describe(
        source=z.UNPRIV,
        rule_text="If a software-check exception is not caused then the elp is updated to NO_LP_EXPECTED.",
        context="After a successful lpad, ELP is NO_LP_EXPECTED, so the next instruction needs no landing pad. "
        "Landing pads are enabled in every mode.",
        plan="In U, S, VU and VS (H), after an indirect jump to a matching lpad (label 0 and labeled):\n"
        "1. An ebreak right after it takes a breakpoint (cause 3) with xPELP=0.\n"
        "2. A non-lpad and a mismatched lpad right after it do not fault.\n"
        "3. (C) A misaligned lpad after a 2-byte c.nop after it does not fault.",
    )
    setup_all(t)
    keep = MUT == "lpad_keeps_elp"

    def body(m: str) -> None:
        for L in (0, LAB):
            tg = T(
                [z.lpad(L), "SECOND:", "ebreak"], f"lpad {L:#x}; ebreak", size=8, traps=BRK, tval="TGT0", second=True
            )
            land(
                t,
                m,
                J("jalr", 0, 6),
                tg,
                SWCHK if keep else BRK,
                f"lpad {L:#x} then ebreak",
                x7=X(LAB << 12, LAB << 12),
                pelp=1 if keep else 0,
            )
        tg = T([z.lpad(0), "addi x0, x0, 0"], "lpad 0; nop", size=8)
        land(t, m, J("jalr", 0, 8), tg, SWCHK if keep else "ok", "non-lpad after lpad 0")
        tg = T([z.lpad(LAB), z.lpad(LAB ^ 0xFF)], "lpad; mismatched lpad", size=8)
        land(
            t,
            m,
            J("jalr", 0, 8),
            tg,
            SWCHK if keep else "ok",
            "mismatched lpad after a matching lpad",
            x7=X(LAB << 12, LAB << 12),
        )
        with t.only_if(ZCA):
            tg = T([z.lpad(0), ".hword 0x0001  // c.nop", z.lpad(LAB)], "lpad 0; c.nop; misaligned lpad", size=10)
            land(
                t,
                m,
                J("jalr", 0, 8),
                tg,
                SWCHK if keep else "ok",
                "misaligned lpad after lpad 0",
                x7=X(LAB << 12, LAB << 12),
            )

    modes(t, body)
    z.s_teardown(t)
    return t


# ================================================================= privileged rules (src/priv/cfi.adoc etc.)
def t_forward_traps() -> TestFile:
    t = new("Zicfilp_forward_traps")
    t.describe(
        source=z.PRIV,
        rule_text="A trap may need to be delivered to the same or to a higher privilege mode upon completion of "
        "jalr/c.jalr/c.jr, but before the instruction at the target of indirect call/jump was decoded",
        context="The jump completes (its link register is written, ELP=LP_EXPECTED) and the trap is taken at the "
        "target, saving ELP in xPELP so the xRET can restore it. The landing-pad fault itself is such a trap; "
        "higher-priority exceptions and interrupts are tested in the _async_ rules. Landing pads are enabled in "
        "every mode, and the trap's xRET returns to a landing pad.",
        plan="In U, S, VU and VS (H):\n"
        "1. jalr x1, 0(x6), jalr x9, 0(x8) and (C) c.jalr x6 to a non-lpad: cause 18 at the target, xPELP=1, and "
        "the link register holds the jump's address + 4 (+ 2 for c.jalr).\n"
        "2. The trap goes to the same or a higher mode (handler M, S/HS or VS).",
    )
    setup_all(t)
    nl = MUT == "no_link_on_fault"

    def body(m: str) -> None:
        for rd, rs in ((1, 6), (9, 8)):
            land(
                t,
                m,
                J("jalr", rd, rs),
                nonlp(),
                SWCHK,
                f"jalr x{rd}, 0(x{rs}) to a non-lpad",
                link=(f"x{rd}", 8 if nl else 4),
                pelp=1,
                handler=z.ORIGIN_OK[m],
            )
        with t.only_if(ZCA):
            land(
                t, m, J("c.jalr", rs1=6), nonlp(), SWCHK, "c.jalr x6 to a non-lpad", link=("x1", 4 if nl else 2), pelp=1
            )

    modes(t, body)
    z.s_teardown(t)
    return t


def t_async_interrupt() -> TestFile:
    t = new("Zicfilp_forward_trap_async_interrupt")
    t.describe(
        source=z.PRIV,
        rule_text="Asynchronous interrupts. [A trap may need to be delivered ... upon completion of "
        "jalr/c.jalr/c.jr, but before the instruction at the target of indirect call/jump was decoded, due to "
        "asynchronous interrupts.]",
        context="An interrupt cannot be placed exactly after a jump. Instead, an sret restores ELP=LP_EXPECTED "
        "(SPELP=1 with the new mode's LPE=1) with a supervisor software interrupt pending and enabled for the new "
        "mode, so the interrupt is due at the sret's target, a landing pad, with ELP=LP_EXPECTED. The hart may take "
        "it there or a few instructions later; the check is consistent with either: if sepc is the target, SPELP "
        "must be 1, otherwise 0. After the interrupt's sret the landing pad must still land (ELP restored).",
        plan="1. U-mode (senvcfg.LPE=1): sip.SSIP=1, sie.SSIE=1, sstatus.SIE=0; sret with SPP=U, SPELP=1 to lpad 0 "
        "followed by a 50-iteration loop. One supervisor software interrupt is taken, from U, and (sepc == target) "
        "== (SPELP == 1).\n"
        "2. S-mode (menvcfg.LPE=1): the same with SPP=S and SPIE=1, so the sret enables the interrupt.",
    )
    setup_all(t)
    ssi = X((1 << 31) | 1, (1 << 63) | 1)
    for m in ("U", "S"):
        tgt, landl = t.label("tgt"), t.label("land")
        t.comment(f"{m}-mode: SSIP pending and enabled at the sret target")
        t.li("x6", z.SIE)
        t.emit("csrc sstatus, x6  // SIE = 0")
        t.li("x6", 2)
        t.emit("csrs sie, x6  // SSIE")
        t.emit("csrs sip, x6  // SSIP")
        t.allow(1)
        t.emit(f"LA(x6, {tgt})", 2)
        t.emit("csrw sepc, x6")
        t.li("x6", z.SPP | z.SPIE)
        t.emit(f"csr{'s' if m == 'S' else 'c'} sstatus, x6  // SPP, SPIE")
        with t.only_if(H):
            t.li("x6", 1 << 7)
            t.emit(f"csrc {z.CSR['hstatus']:#x}, x6  // SPV = 0")
        t.li("x6", z.SPELP)
        t.emit("csrs sstatus, x6  // SPELP = 1")
        t.emit("sret")
        t.emit(f"{tgt}:", 0)
        t.emit("auipc x0, 0  // lpad 0")
        loop = t.label("wait")
        t.li("x8", 50)
        t.emit(f"{loop}:", 0)
        t.emit("addi x8, x8, -1", 50)
        t.emit(f"bnez x8, {loop}", 50)
        t.emit(f"{landl}:", 0)
        if m == "U":
            t.leave()
        t.li("x6", z.SIE)
        t.emit("csrc sstatus, x6")
        t.li("x6", 2)
        t.emit("csrc sie, x6")
        t.emit("csrc sip, x6")
        t.outcome(
            ssi,
            tgt,
            f"supervisor software interrupt due at an sret target with ELP restored, {m}-mode",
            epc=False,
            origin=m,
        )
        t.comment("(sepc == target) == (SPELP == 1)")
        z.pelp_of_last_trap(t, "x14")
        if MUT == "irq_pelp_zero":
            t.emit("li x14, 0")
        t.emit("AI_LOG(x15, TRAPLOG_EPC)", 10)
        t.emit(f"LA(x5, {tgt})", 2)
        t.emit("xor x15, x15, x5")
        t.emit("seqz x15, x15  // 1: taken at the target")
        t.emit("xor x15, x15, x14")
        t.emit("seqz x15, x15")
        t.check_bool("x15", tgt, f"{m}-mode: an interrupt taken at the target saves xPELP=1, elsewhere 0")
    z.s_teardown(t)
    return t


def pmp_setup(t: TestFile, page: str) -> None:
    """M-mode: PMP entry 0 = NAPOT 4 KiB over page with R and W but no X; entry 1 = NAPOT all of memory RWX. The
    previous pmpcfg0/pmpaddr0/pmpaddr1 are saved. x8 = 1 when the hart took both entries (else the PMP cases are
    skipped)."""
    t.comment("PMP: entry 0 = NAPOT 4 KiB R W (no X) over the target page, entry 1 = all of memory RWX")
    for csr in ("pmpcfg0", "pmpaddr0", "pmpaddr1"):
        z.save_csr(t, csr, f"{t.rule}_sv_{csr}")
    t.emit(f"LA(x7, {page})", 2)
    t.emit("srli x7, x7, 2")
    t.emit("ori x7, x7, 0x1FF  // NAPOT 4 KiB")
    t.emit("csrw pmpaddr0, x7")
    t.emit("li x7, -1")
    t.emit("csrw pmpaddr1, x7")
    t.li("x7", 0x1F1B)
    t.emit("csrw pmpcfg0, x7  // entry 0 NAPOT RW, entry 1 NAPOT RWX")
    t.emit("csrr x8, pmpcfg0")
    t.li("x7", 0xFFFF)
    t.emit("and x8, x8, x7")
    t.li("x7", 0x1F1B)
    t.emit("xor x8, x8, x7")
    t.emit("seqz x8, x8  // 1: both entries took")
    with t.only_if(z.S_IMPL):
        t.emit("sfence.vma")


def pmp_restore(t: TestFile) -> None:
    for csr in ("pmpaddr1", "pmpaddr0", "pmpcfg0"):
        z.restore_csr(t, csr, f"{t.rule}_sv_{csr}")
    with t.only_if(z.S_IMPL):
        t.emit("sfence.vma")


def noexec_page(t: TestFile) -> str:
    """A 4 KiB-aligned code page (inside the test's code) whose first word is the jump target: addi x0, x0, 0. It is
    jumped over in normal flow."""
    page, after = f"{t.rule}_nxpage", t.label("afterpage")
    t.emit(f"j {after}")
    t.emit(".p2align 12", 0)
    t.emit(f"{page}:", 0)
    t.emit("addi x0, x0, 0  // target in the no-execute page")
    t.emit(".p2align 12", 0)
    t.emit(f"{after}:", 0)
    return page


def pmp_fault_case(t: TestFile, m: str, page: str, j: JType, desc: str) -> None:
    """In m (S or U, entered from M), jump to the no-execute page: an instruction access fault at the target
    (cause 1, xtval 0 or the target), with xPELP=1 when the jump set ELP. Resumes at a recovery lpad."""
    landl = t.label("land")
    t.comment(f"{desc} in {m}-mode")
    z.set_resume(t, landl)
    t.allow(1)
    t.enter(m)
    t.emit(f"LA(x{j.rs1}, {page})", 2)
    t.emit(f"jalr x{j.rd}, 0(x{j.rs1})")
    t.emit(f"{landl}:", 0)
    t.emit("auipc x0, 0  // lpad 0: recovery landing pad")
    z.clear_resume(t)
    t.leave()
    cause = SWCHK if MUT == "priority_access" else z.IACC
    t.outcome(cause, page, f"{desc} in {m}-mode", z.LP_TVAL if cause == SWCHK else [0, page], origin=m)
    z.check_pelp(t, 0 if MUT == "pelp_not_saved" else 1, page, f"{desc} in {m}-mode")


def t_async_exception() -> TestFile:
    t = new("Zicfilp_forward_trap_async_exception", sm=True, required=z.REQ_MU)
    t.describe(
        source=z.PRIV,
        rule_text="Synchronous exceptions with priority higher than that of a software-check exception with xtval "
        'set to "landing pad fault (code=2)" (See exc_priority of Privileged Specification).',
        context="M-mode test (it programs PMP). An instruction access fault at the target of an indirect jump "
        "outranks the landing-pad fault (Zicfilp_exception_priority), and is taken with ELP=LP_EXPECTED, which the "
        "trap saves in mstatus.MPELP. PMP entry 0 (NAPOT 4 KiB, R and W, no X) covers a code page; entry 1 (NAPOT, "
        "all of memory) grants RWX; the previous PMP state is restored. The cases run only if the hart accepts both "
        "entries. medeleg[1] and [18] are cleared so the traps reach M-mode.",
        plan="1. U-mode (senvcfg.LPE=1, or menvcfg.LPE=1 without S) and S-mode (menvcfg.LPE=1): jalr x0, 0(x6) and "
        "jalr x1, 0(x8) to the no-execute page: cause 1 at the target (xtval 0 or the target), from that mode, "
        "MPELP=1. The trap's mret restores ELP=1 and returns to a landing pad.",
    )
    m_deleg_off(t, (1 << 18) | 2)
    t.emit(f"csrsi {z.CSR['menvcfg']:#x}, {z.LPE}  // menvcfg.LPE (S, or U without S)")
    with t.only_if(z.S_IMPL):
        t.emit(f"csrsi {z.CSR['senvcfg']:#x}, {z.LPE}  // senvcfg.LPE (U)")
    page = noexec_page(t)
    pmp_setup(t, page)
    skip = t.label("nopmp")
    t.emit(f"beqz x8, {skip}")
    for m in ("U", "S"):
        body = lambda m=m: [
            pmp_fault_case(t, m, page, jj, f"{jj.text()} to a no-execute target")
            for jj in (J("jalr", 0, 6), J("jalr", 1, 8))
        ]
        if m == "S":
            with t.only_if(z.S_IMPL):
                body()
        else:
            body()
    t.emit(f"{skip}:", 0)
    pmp_restore(t)
    t.emit(f"csrci {z.CSR['menvcfg']:#x}, {z.LPE}")
    with t.only_if(z.S_IMPL):
        t.emit(f"csrci {z.CSR['senvcfg']:#x}, {z.LPE}")
    m_deleg_restore(t)
    return t


def illegal_targets(m: str) -> list:
    """Instructions that raise illegal-instruction (or virtual-instruction from VS/VU) in mode m."""
    out = [
        T([".word 0x00000000  // illegal (all zeros)"], "all-zero instruction", traps=z.ILL),
        T(
            [f".word {(0x300 << 20) | (2 << 12) | (9 << 7) | 0x73:#x}  // csrr x9, mstatus"],
            "csrr mstatus",
            traps=z.ILL,
        ),
    ]
    if m in ("U", "VU"):
        out.append(T([".word 0x10200073  // sret"], "sret", traps=z.ILL if m == "U" else z.VIRT))
    if m == "S":
        out.append(T([".word 0x30200073  // mret"], "mret", traps=z.ILL))
    if m in ("VS", "VU"):
        out.append(
            T(
                [f".word {(0x600 << 20) | (2 << 12) | (9 << 7) | 0x73:#x}  // csrr x9, hstatus"],
                "csrr hstatus",
                traps=z.VIRT,
            )
        )
    return out


def t_exception_priority() -> TestFile:
    t = new("Zicfilp_exception_priority")
    t.describe(
        source=z.PRIV,
        rule_text="The software-check exception caused by zicfilp has higher priority than an illegal-instruction "
        "exception but lower priority than instruction access-fault.",
        context="Landing pads are enabled in every mode. Virtual-instruction shares illegal-instruction's priority "
        "level (hypervisor.adoc exception priority table), so it ranks below the landing-pad fault too. The "
        "access-fault half needs PMP and is in the _Sm file.",
        plan="In U, S, VU and VS (H), after jalr x0, 0(x6) to an instruction that is illegal in that mode (all "
        "zeros, csrr mstatus, sret in U/VU, mret in S, csrr hstatus in VS/VU, which is virtual-instruction): cause "
        "18 with xtval in {0, 2}, not 2 or 22.",
    )
    setup_all(t)

    def body(m: str) -> None:
        for tg in illegal_targets(m):
            if MUT == "priority_illegal":
                land(t, m, J("jalr", 0, 6), tg, tg.traps, f"{tg.note} after an indirect jump", tval=[0, 0])
            else:
                land(t, m, J("jalr", 0, 6), tg, SWCHK, f"{tg.note} after an indirect jump", pelp=1)

    modes(t, body)
    z.s_teardown(t)
    return t


def t_exception_priority_sm() -> TestFile:
    t = new("Zicfilp_exception_priority", sm=True, required=z.REQ_MU)
    t.describe(
        source=z.PRIV,
        rule_text="The software-check exception caused by zicfilp has higher priority than an illegal-instruction "
        "exception but lower priority than instruction access-fault.",
        context="This file covers the access-fault half (PMP needs M-mode); Zicfilp_exception_priority.S covers "
        "illegal-instruction. PMP entry 0 (NAPOT 4 KiB, R and W, no X) covers a code page, entry 1 grants RWX on "
        "all of memory; the cases run only if the hart accepts both entries. medeleg[1] and [18] are cleared.",
        plan="U-mode (senvcfg.LPE=1, or menvcfg.LPE=1 without S) and S-mode (menvcfg.LPE=1): an indirect jump to a "
        "non-lpad in the no-execute page raises an instruction access fault (cause 1), not cause 18.",
    )
    m_deleg_off(t, (1 << 18) | 2)
    t.emit(f"csrsi {z.CSR['menvcfg']:#x}, {z.LPE}")
    with t.only_if(z.S_IMPL):
        t.emit(f"csrsi {z.CSR['senvcfg']:#x}, {z.LPE}")
    page = noexec_page(t)
    pmp_setup(t, page)
    skip = t.label("nopmp")
    t.emit(f"beqz x8, {skip}")
    pmp_fault_case(t, "U", page, J("jalr", 0, 9), "indirect jump to a no-execute non-lpad")
    with t.only_if(z.S_IMPL):
        pmp_fault_case(t, "S", page, J("jalr", 0, 9), "indirect jump to a no-execute non-lpad")
    t.emit(f"{skip}:", 0)
    pmp_restore(t)
    t.emit(f"csrci {z.CSR['menvcfg']:#x}, {z.LPE}")
    with t.only_if(z.S_IMPL):
        t.emit(f"csrci {z.CSR['senvcfg']:#x}, {z.LPE}")
    m_deleg_restore(t)
    return t


def t_lpad_sw_exception() -> TestFile:
    t = new("lpad_sw_exception")
    t.describe(
        source=z.PRIV,
        rule_text="The software-check exception due to the instruction not being an lpad instruction when ELP is "
        "LP_EXPECTED or a software-check exception caused by the lpad instruction itself leads to a trap being "
        "delivered to the same or to a higher privilege mode.",
        context="With the framework's delegation (medeleg[18]=1 if writable, hedeleg[18]=0), faults from U and S go to "
        "S (or M), and from VU and VS to HS (or M). With hedeleg[18]=1 they go to VS. The _Sm file sweeps medeleg.",
        plan="1. In U, S, VU and VS (H): a non-lpad target and a mismatched lpad: cause 18, taken by a handler in the "
        "same or a higher mode (U, S: S or M; VU, VS: VS, HS or M).\n"
        "2. H: with hedeleg[18]=1 (if it reads back 1), faults from VU and VS are taken by the VS handler.",
    )
    setup_all(t)

    def body(m: str) -> None:
        land(t, m, J("jalr", 0, 6), nonlp(), SWCHK, "non-lpad target", handler=z.ORIGIN_OK[m], pelp=1)
        land(t, m, J("jalr", 0, 8), lp(LAB), SWCHK, "mismatched lpad", x7=X(0, 0), handler=z.ORIGIN_OK[m], pelp=1)

    modes(t, body)
    with t.only_if(H):
        t.comment("hedeleg[18] = 1")
        t.li("x6", 1 << 18)
        t.emit(f"csrs {z.CSR['hedeleg']:#x}, x6  // hedeleg")
        t.emit(f"csrr x6, {z.CSR['hedeleg']:#x}")
        t.emit("srli x6, x6, 18")
        t.emit("andi x6, x6, 1")

        def vs_deleg() -> None:
            for m in ("VU", "VS"):
                land(t, m, J("jalr", 0, 6), nonlp(), SWCHK, "non-lpad target, hedeleg[18]=1", handler=[2], pelp=1)

        t.either("x6", vs_deleg, lambda: None)
        t.li("x6", 1 << 18)
        t.emit(f"csrc {z.CSR['hedeleg']:#x}, x6  // hedeleg")
    z.s_teardown(t)
    return t


def t_lpad_sw_exception_sm() -> TestFile:
    t = new("lpad_sw_exception", sm=True)
    t.describe(
        source=z.PRIV,
        rule_text="The software-check exception due to the instruction not being an lpad instruction when ELP is "
        "LP_EXPECTED or a software-check exception caused by the lpad instruction itself leads to a trap being "
        "delivered to the same or to a higher privilege mode.",
        context="M-mode part: medeleg[18] sweeps (lpad_sw_exception.S covers S-mode boot). medeleg[18] may be "
        f"read-only zero ({ISSUE}2675: the spec does not mandate which medeleg bits are writable), so the delegated "
        "cases run only when it reads back 1. An M-mode fault is never delegated. Without S there is no medeleg, "
        "and every fault goes to M.",
        plan="1. M-mode (mseccfg.MLPE=1): a landing-pad fault (non-lpad, and a mismatched lpad) is taken in M (with "
        "medeleg[18]=0 and =1 when S exists).\n"
        "2. U-mode (senvcfg.LPE=1, or menvcfg.LPE=1 without S) and S-mode (menvcfg.LPE=1) faults go to M with "
        "medeleg[18]=0 (or without S), and to S with medeleg[18]=1.",
    )
    z.mlpe(t, True)
    m_lower_lpe(t, True)
    U = "defined(U_SUPPORTED)"
    with t.only_if("!defined(S_SUPPORTED)"):
        land(t, "M", J("jalr", 0, 8), nonlp(), SWCHK, "M-mode fault", handler=[3], pelp=1)
        with t.only_if(U):
            land(t, "U", J("jalr", 0, 6), nonlp(), SWCHK, "U-mode fault (no S)", handler=[3], pelp=1)
    with t.only_if(z.S_IMPL):
        z.save_csr(t, "medeleg", f"{t.rule}_sv_medeleg")
        for d in (0, 1):
            t.comment(f"medeleg[18] = {d}")
            t.li("x5", 1 << 18)
            t.emit(f"csr{'s' if d else 'c'} medeleg, x5")
            t.emit("csrr x6, medeleg")
            t.emit("srli x6, x6, 18")
            t.emit("andi x6, x6, 1  // medeleg[18] as read back")
            m_handler = [1] if MUT == "m_fault_delegated" and d else [3]
            land(t, "M", J("jalr", 0, 8), nonlp(), SWCHK, f"M-mode fault, medeleg[18]={d}", handler=m_handler, pelp=1)
            land(
                t,
                "M",
                J("jalr", 0, 8),
                lp(LAB),
                SWCHK,
                f"M-mode mismatched lpad, medeleg[18]={d}",
                x7=X(0, 0),
                handler=m_handler,
                pelp=1,
            )

            def lower(dl: bool) -> None:
                h = [1] if dl and MUT != "deleg_ignored" else [3]
                for m in ("U", "S"):
                    land(
                        t,
                        m,
                        J("jalr", 0, 6),
                        nonlp(),
                        SWCHK,
                        f"{m}-mode fault, medeleg[18]={int(dl)}",
                        handler=h,
                        pelp=1,
                    )
                    land(
                        t,
                        m,
                        J("jalr", 0, 6),
                        lp(LAB),
                        SWCHK,
                        f"{m}-mode mismatched lpad, medeleg[18]={int(dl)}",
                        x7=X(0, 0),
                        handler=h,
                        pelp=1,
                    )

            if d:
                t.either("x6", lambda: lower(True), lambda: lower(False))
            else:
                lower(False)
        z.restore_csr(t, "medeleg", f"{t.rule}_sv_medeleg")
    z.mlpe(t, False)
    m_lower_lpe(t, False)
    return t


# ---------------------------------------------------------------- xPELP fields and traps
def trap_pelp_cases(t: TestFile, m: str, tag: str, handler: list | None = None, zca: bool = True) -> None:
    """A trap with ELP=1 (landing-pad fault) saves xPELP=1; a trap with ELP=0 (ebreak) saves 0. zca=False inside a
    run-time branch (t.either), which cannot hold #ifdef'd table entries."""
    p1 = 0 if MUT == "pelp_not_saved" or (MUT == "vs_trap_writes_mstatus" and handler == [2]) else 1
    land(t, m, J("jalr", 0, 6), nonlp(), SWCHK, f"{tag}: trap with ELP=1", pelp=p1, handler=handler)
    if zca:
        with t.only_if(ZCA):
            land(
                t,
                m,
                J("jalr", 0, 8),
                lp(0, True),
                SWCHK,
                f"{tag}: trap at a misaligned lpad with ELP=1",
                pelp=p1,
                handler=handler,
            )
    else:
        land(
            t,
            m,
            J("jalr", 0, 8),
            lp(LAB),
            SWCHK,
            f"{tag}: trap at a mismatched lpad with ELP=1",
            x7=X(0, 0),
            pelp=p1,
            handler=handler,
        )
    # ELP=0 trap with xPELP=1 beforehand, where that survives into the trap (S->S, M->M, VU/VS->VS)
    pre: list = []
    stale = False
    if handler == [2]:
        t.li("x6", z.SPELP)
        t.emit(f"csrs {z.CSR['vsstatus']:#x}, x6  // vsstatus.SPELP = 1 (stale)")
        stale = True
    elif m == t.cur == "S":
        pre = [f"li x6, {z.SPELP:#x}", "csrs sstatus, x6  // SPELP = 1 (stale)"]
        stale = True
    elif m == t.cur == "M":
        pre = [
            "#if __riscv_xlen == 64",
            "li x6, 1",
            "slli x6, x6, 41",
            "csrs mstatus, x6  // MPELP = 1 (stale)",
            "#else",
            f"li x6, {z.MPELP_H:#x}",
            f"csrs {z.CSR['mstatush']:#x}, x6  // mstatush.MPELP = 1",
            "#endif",
        ]
        stale = True
    p0 = 1 if stale and MUT == "pelp_set_only" else 0
    land(
        t,
        m,
        J("jalr", 0, 7),
        ebreak(),
        BRK,
        f"{tag}: trap with ELP=0" + (" (xPELP was 1)" if stale else ""),
        pre=pre,
        pelp=p0,
        handler=handler,
    )


def t_pelp_trap() -> TestFile:
    t = new("Zicfilp_pelp_trap")
    t.describe(
        source=z.PRIV,
        rule_text="When a trap is taken into privilege mode x, the xpelp is set to ELP and ELP is set to "
        "NO_LP_EXPECTED.",
        context="Landing pads are enabled in every mode. ELP=1 at a trap comes from a landing-pad fault at the target "
        "of an indirect jump; ELP=0 from an ebreak reached by a software-guarded jump. ELP=NO_LP_EXPECTED after the "
        "trap is shown by the handler running at all: in S-mode with menvcfg.LPE=1 (and VS with henvcfg.LPE=1) the "
        "handler's first instruction is not a landing pad. The M-mode part is in the _Sm file.",
        plan="1. Traps into S (from U and S) and into HS (from VU and VS, hedeleg[18]=0): sstatus.SPELP = 1 for a "
        "landing-pad fault (non-lpad, and misaligned lpad with C), 0 for an ebreak.\n"
        "2. H: with hedeleg[3] and hedeleg[18] set (if writable), traps from VU and VS into VS: vsstatus.SPELP = 1 "
        "and 0 likewise.\n"
        "3. xPELP is written even when the trapping mode's LPE is 0: with menvcfg.LPE=0, S-mode sets sstatus.SPELP=1 "
        "and executes ebreak; the trap saves SPELP=0.",
    )
    setup_all(t)

    def body(m: str) -> None:
        trap_pelp_cases(t, m, f"trap from {m}", z.ORIGIN_OK[m])

    modes(t, body)
    stale_pelp_case(t)
    with t.only_if(H):
        t.li("x6", (1 << 18) | (1 << 3))
        t.emit(f"csrs {z.CSR['hedeleg']:#x}, x6")
        t.emit(f"csrr x6, {z.CSR['hedeleg']:#x}")
        t.li("x7", (1 << 18) | (1 << 3))
        t.emit("and x6, x6, x7")
        t.emit("xor x6, x6, x7")
        t.emit("seqz x6, x6  // 1: hedeleg[3] and [18] took")
        t.either(
            "x6",
            lambda: [trap_pelp_cases(t, m, f"trap from {m} into VS", [2], zca=False) for m in ("VU", "VS")],
            lambda: None,
        )
        t.li("x6", (1 << 18) | (1 << 3))
        t.emit(f"csrc {z.CSR['hedeleg']:#x}, x6")
    z.s_teardown(t)
    return t


def stale_pelp_case(t: TestFile) -> None:
    """S-boot: with menvcfg.LPE=0, SPELP=1 written by software is overwritten with ELP (0) by a trap from S."""
    z.menvcfg_lpe(t, False)
    land(
        t,
        "S",
        J("seq"),
        ebreak(),
        BRK,
        "ebreak in S with menvcfg.LPE=0 after sstatus.SPELP was set to 1",
        pre=[f"li x6, {z.SPELP:#x}", "csrs sstatus, x6  // SPELP = 1 (stale)"],
        pelp=1 if MUT == "pelp_saved_only_if_enabled" else 0,
        handler=[1, 3],
    )
    z.menvcfg_lpe(t, True)


def m_stale_pelp_case(t: TestFile) -> None:
    """M-mode: with MLPE=0, MPELP=1 written by software is overwritten with ELP (0) by a trap from M."""
    z.mlpe(t, False)
    pre = [
        "#if __riscv_xlen == 64",
        "li x6, 1",
        "slli x6, x6, 41",
        "csrs mstatus, x6  // MPELP = 1 (stale)",
        "#else",
        f"li x6, {z.MPELP_H:#x}",
        f"csrs {z.CSR['mstatush']:#x}, x6  // mstatush.MPELP = 1 (stale)",
        "#endif",
    ]
    land(
        t,
        "M",
        J("seq"),
        ebreak(),
        BRK,
        "ebreak in M with MLPE=0 after MPELP was set to 1",
        pre=pre,
        pelp=1 if MUT == "pelp_saved_only_if_enabled" else 0,
        handler=[3],
    )


def m_lower_lpe(t: TestFile, on: bool) -> None:
    """M-mode: enable/disable landing pads in S and U (menvcfg, senvcfg) where they exist."""
    with t.only_if("defined(U_SUPPORTED)"):
        t.emit(f"csr{'s' if on else 'c'}i {z.CSR['menvcfg']:#x}, {z.LPE}  // menvcfg.LPE")
    with t.only_if(z.S_IMPL):
        t.emit(f"csr{'s' if on else 'c'}i {z.CSR['senvcfg']:#x}, {z.LPE}  // senvcfg.LPE")


def m_deleg_off(t: TestFile, bits: int = (1 << 18) | (1 << 3)) -> None:
    """Save medeleg and clear bits (medeleg exists only with S)."""
    with t.only_if(z.S_IMPL):
        z.save_csr(t, "medeleg", f"{t.rule}_sv_medeleg")
        t.li("x5", bits)
        t.emit("csrc medeleg, x5  // these exceptions stay in M")


def m_deleg_restore(t: TestFile) -> None:
    with t.only_if(z.S_IMPL):
        z.restore_csr(t, "medeleg", f"{t.rule}_sv_medeleg")


def t_pelp_trap_sm() -> TestFile:
    t = new("Zicfilp_pelp_trap", sm=True)
    t.describe(
        source=z.PRIV,
        rule_text="When a trap is taken into privilege mode x, the xpelp is set to ELP and ELP is set to "
        "NO_LP_EXPECTED.",
        context="M-mode part (traps into M): mseccfg.MLPE=1, menvcfg.LPE=1 and senvcfg.LPE=1 where they exist, and "
        "medeleg[3] and [18] cleared. An M-mode trap with MLPE=1 also shows ELP=NO_LP_EXPECTED after the trap: the "
        "M handler's first instruction is not a landing pad.",
        plan="1. Traps into M from M, and from S and U where implemented: mstatus.MPELP (mstatush on RV32) = 1 for a "
        "landing-pad fault (non-lpad, and misaligned lpad with C), 0 for an ebreak.\n"
        "2. MPELP is written even when MLPE=0: with MLPE=0, M-mode sets MPELP=1 and executes ebreak; the trap saves "
        "MPELP=0.",
    )
    m_deleg_off(t)
    z.mlpe(t, True)
    m_lower_lpe(t, True)
    trap_pelp_cases(t, "M", "trap from M", [3])
    with t.only_if("defined(U_SUPPORTED)"):
        trap_pelp_cases(t, "U", "trap from U", [3])
    with t.only_if(z.S_IMPL):
        trap_pelp_cases(t, "S", "trap from S", [3])
    m_stale_pelp_case(t)
    z.mlpe(t, False)
    m_lower_lpe(t, False)
    m_deleg_restore(t)
    return t


def t_mpelp_op_sm() -> TestFile:
    t = new("cfi_mstatus_mpelp_op", sm=True)
    t.describe(
        source=z.PRIV,
        rule_text="To store the previous ELP state on trap delivery to M-mode, an mpelp bit is provided in the "
        "mstatus CSR.",
        context="mstatus.MPELP is bit 41 (RV64), mstatush.MPELP bit 9 (RV32). medeleg[3] and [18] are cleared. "
        f'MPELP is writable whatever MLPE ({ISSUE}3331: "The MPELP does not become read-only zero when MLPE is 0").',
        plan="1. Traps into M from M (MLPE=1), S and U (LPE=1) with ELP=1 save MPELP=1; with ELP=0, MPELP=0.\n"
        "2. M-mode writes: setting and clearing MPELP reads back 1 and 0, with MLPE=0 and with MLPE=1.\n"
        "3. mret with MPELP=1 to M-mode (MLPE=1) at a non-lpad: cause 18; MPELP=0 to the same target: no fault.",
    )
    m_deleg_off(t)
    for on in (False, True):
        z.mlpe(t, on)
        for v in (1, 0):
            z.mpelp_set(t, bool(v))
            z.mpelp_read(t, "x9")
            lab = t.label("rd")
            t.emit(f"{lab}:", 0)
            exp = 0 if (MUT == "mpelp_ro_mlpe0" and not on) else v
            t.check("x9", exp, lab, f"MPELP written {v} with MLPE={int(on)} reads back")
    m_lower_lpe(t, True)
    trap_pelp_cases(t, "M", "trap from M", [3])
    with t.only_if("defined(U_SUPPORTED)"):
        trap_pelp_cases(t, "U", "trap from U", [3])
    with t.only_if(z.S_IMPL):
        trap_pelp_cases(t, "S", "trap from S", [3])
    en = {"mlpe": 1}
    for xp in (1, 0):
        z.xret_case(
            t,
            "mret",
            "M",
            xp,
            nonlp(),
            z.xret_expect("M", xp, nonlp(), en, frm="M"),
            f"mret to M with MPELP={xp}",
            after_pelp=True,
            pelp=1,
        )
    z.mlpe(t, False)
    m_lower_lpe(t, False)
    m_deleg_restore(t)
    return t


def tsbi_mstatus_spelp(t: TestFile, exp: int, desc: str) -> None:
    """Check mstatus.SPELP through a T-SBI read (an ecall into M, which does not change SPELP)."""
    lab = t.label("ms")
    t.emit(f"{lab}:", 0)
    t.tsbi_csr("READ", "MSTATUS")
    t.emit("srli a0, a0, 23")
    t.emit("andi a0, a0, 1")
    t.check("a0", exp, lab, f"{desc}: mstatus.SPELP (M-mode read)")


def t_spelp_op() -> TestFile:
    t = new("cfi_mstatus_spelp_op")
    t.describe(
        source=z.PRIV,
        rule_text="To store the previous ELP state on trap delivery to S/HS-mode, an spelp bit is provided in the "
        "mstatus CSR.",
        context="mstatus.SPELP is bit 23, also seen through sstatus. Traps into S/HS are logged with sstatus. "
        "Landing pads are enabled in every mode.",
        plan="1. Traps into S (from U and S) and HS (from VU and VS): SPELP=1 after a landing-pad fault, 0 after an "
        "ebreak (sstatus at handler entry).\n"
        "2. SPELP set and cleared through sstatus is seen in mstatus (M-mode read through T-SBI), and set and "
        "cleared in mstatus (T-SBI) is seen in sstatus.",
    )
    setup_all(t)
    modes(t, lambda m: trap_pelp_cases(t, m, f"trap from {m} into S/HS", z.ORIGIN_OK[m]))
    spelp_alias_cases(t)
    z.s_teardown(t)
    return t


def spelp_alias_cases(t: TestFile) -> None:
    ro = MUT == "spelp_not_writable"
    for v in (1, 0):
        t.li("x6", z.SPELP)
        t.emit(f"csr{'s' if v else 'c'} sstatus, x6  // sstatus.SPELP = {v}")
        tsbi_mstatus_spelp(t, 0 if ro else v, f"sstatus.SPELP written {v}")
    for v in (1, 0):
        t.tsbi_csr("SET" if v else "CLEAR", "MSTATUS", imm=z.SPELP)
        lab = t.label("ss")
        t.emit(f"{lab}:", 0)
        t.emit("csrr x9, sstatus")
        t.emit("srli x9, x9, 23")
        t.emit("andi x9, x9, 1")
        t.check("x9", v, lab, f"mstatus.SPELP written {v} (T-SBI): sstatus.SPELP")


def t_sstatus_spelp_op() -> TestFile:
    t = new("cfi_sstatus_spelp_op")
    t.describe(
        source=z.PRIV,
        rule_text="The spelp bit in mstatus can be accessed through the sstatus CSR.",
        context="S-mode writes of sstatus.SPELP are checked in mstatus through a T-SBI read (an ecall into M, which "
        "leaves SPELP alone), and M-mode writes are checked in sstatus. The written SPELP is the one sret uses.",
        plan="1. csrs/csrc, csrrw and csrrsi/csrrci forms on sstatus.SPELP: mstatus.SPELP follows.\n"
        "2. mstatus.SPELP set/cleared by M-mode: sstatus.SPELP follows.\n"
        "3. With senvcfg.LPE=1, sstatus.SPELP set by csrs and sret to U at a non-lpad: cause 18; cleared: no fault.",
    )
    setup_all(t)
    spelp_alias_cases(t)
    ro = MUT == "spelp_not_writable"
    t.comment("csrrw: write sstatus with SPELP set, then with it clear")
    for v in (1, 0):
        t.emit("csrr x6, sstatus")
        t.li("x7", z.SPELP)
        if v:
            t.emit("or x6, x6, x7")
        else:
            t.emit("not x7, x7")
            t.emit("and x6, x6, x7")
        t.emit("csrrw x0, sstatus, x6")
        tsbi_mstatus_spelp(t, 0 if ro else v, f"csrrw sstatus with SPELP={v}")
    en = {"menvcfg": 1, "senvcfg": 1}
    for v in (1, 0):
        exp = z.xret_expect("U", 0 if ro else v, nonlp(), en)
        z.xret_case(t, "sret", "U", v, nonlp(), exp, f"sstatus.SPELP={v} used by sret", pelp=1)
    z.s_teardown(t)
    return t


# ---------------------------------------------------------------- xRET
def sret_sweep(t: TestFile) -> None:
    """S-boot sret cases: y in {U, S, VU, VS} x xPELP x the new mode's LPE x target."""
    for y in ("U", "S"):
        for lpe in (1, 0):
            other = 1 - lpe
            en = {"menvcfg": lpe, "senvcfg": other} if y == "S" else {"menvcfg": other, "senvcfg": lpe}
            z.s_enables(t, bool(en["menvcfg"]), bool(en["senvcfg"]))
            for xp in (1, 0):
                for tg in (nonlp(), lp(0)):
                    z.xret_case(
                        t,
                        "sret",
                        y,
                        xp,
                        tg,
                        z.xret_expect(y, xp, tg, en),
                        f"sret to {y}, {y} LPE={lpe}, other mode's LPE={other}",
                        after_pelp=(y == "S"),
                        pelp=1,
                    )
    with t.only_if(H):
        for y in ("VU", "VS"):
            for lpe in (1, 0):
                other = 1 - lpe
                if y == "VS":
                    en = {"menvcfg": other, "senvcfg": other, "henvcfg": lpe}
                else:
                    en = {"menvcfg": other, "senvcfg": lpe, "henvcfg": other}
                z.s_enables(t, bool(en["menvcfg"]), bool(en["senvcfg"]), bool(en["henvcfg"]))
                for xp in (1, 0):
                    z.xret_case(
                        t,
                        "sret",
                        y,
                        xp,
                        nonlp(),
                        z.xret_expect(y, xp, nonlp(), en),
                        f"sret to {y}, {y} LPE={lpe}",
                        pelp=1,
                    )
        t.comment("sret in VS-mode uses vsstatus.SPELP: to VU (senvcfg.LPE) and to VS (henvcfg.LPE)")
        for y in ("VU", "VS"):
            for lpe in (1, 0):
                en = {"menvcfg": 0, "senvcfg": lpe if y == "VU" else 1 - lpe, "henvcfg": lpe if y == "VS" else 1 - lpe}
                z.s_enables(t, False, bool(en["senvcfg"]), bool(en["henvcfg"]))
                for xp in (1, 0):
                    z.xret_case(
                        t,
                        "sret",
                        y,
                        xp,
                        nonlp(),
                        z.xret_expect(y, xp, nonlp(), en, frm="VS"),
                        f"sret in VS to {y}, {y} LPE={lpe} (other {1 - lpe})",
                        frm="VS",
                        after_pelp=(y == "VS"),
                        pelp=1,
                    )
                    if y == "VU":
                        read_vsstatus_spelp(
                            t,
                            1 if (MUT == "xret_keeps_pelp" and xp) else 0,
                            f"after sret from VS to VU with vsstatus.SPELP={xp}",
                        )


def t_pelp_trap_return() -> TestFile:
    t = new("Zicfilp_pelp_trap_return")
    t.describe(
        source=z.PRIV,
        rule_text="An mret or sret instruction is used to return from a trap in M-mode or S-mode, respectively. When "
        "executing an xret instruction, if the new privilege mode is y, then ELP is set to the value of xpelp if yLPE "
        "(see FCFIACT) is 1; otherwise, it is set to NO_LP_EXPECTED; xpelp is set to NO_LP_EXPECTED.",
        context="ELP after the xret is observed at its target: a landing-pad fault at a non-lpad when ELP=1, none at "
        "lpad 0. yLPE is the new mode's enable: menvcfg.LPE for S, senvcfg.LPE for U and VU, henvcfg.LPE for VS. The "
        "other modes' enables are set opposite, so using the wrong one is caught. xPELP=0 after the xret is checked "
        "where it is observable: an sret to the same mode (S, and VS with H). mret is in the _Sm file.",
        issues=f"{ISSUE}3331: when the new mode's LPE is 0, xPELP is not consumed but is still set to NO_LP_EXPECTED.",
        plan="1. sret from S to U and to S: SPELP in {0, 1} x the new mode's LPE in {0, 1} (the other mode's LPE "
        "opposite) x target in {non-lpad, lpad 0}: cause 18 exactly when SPELP=1, LPE=1 and the target is a "
        "non-lpad. After sret to S, sstatus.SPELP reads 0.\n"
        "2. H: sret from HS to VU (senvcfg.LPE) and VS (henvcfg.LPE) likewise, and sret in VS-mode (vsstatus.SPELP) "
        "to VU and VS, each with the new mode's LPE = 1 and 0 (the other enable opposite); after sret from VS to VS "
        "sstatus.SPELP reads 0, and after sret from VS to VU, vsstatus.SPELP (read in HS) reads 0.",
    )
    sret_sweep(t)
    z.s_teardown(t)
    return t


def t_pelp_trap_return_sm() -> TestFile:
    t = new("Zicfilp_pelp_trap_return", sm=True)
    t.describe(
        source=z.PRIV,
        rule_text="An mret or sret instruction is used to return from a trap in M-mode or S-mode, respectively. When "
        "executing an xret instruction, if the new privilege mode is y, then ELP is set to the value of xpelp if yLPE "
        "(see FCFIACT) is 1; otherwise, it is set to NO_LP_EXPECTED; xpelp is set to NO_LP_EXPECTED.",
        context="M-mode part: mret, and sret executed in M-mode. yLPE: mseccfg.MLPE for M, menvcfg.LPE for S (or U "
        "without S), senvcfg.LPE for U. medeleg[18] is cleared, so faults at the target trap to M. mstatus.MPELP=0 "
        "after an mret is observable only after an mret to M (any trap into M rewrites it).",
        issues=f"{ISSUE}3331: MPELP is set to NO_LP_EXPECTED by mret even when MLPE=0.",
        plan="1. mret to M, S and U (where implemented): MPELP in {0, 1} x the new mode's LPE in {0, 1} (the other "
        "enables opposite) x target in {non-lpad, lpad 0}. After mret to M, MPELP reads 0.\n"
        "2. sret executed in M-mode to S and U with SPELP in {0, 1} and the new mode's LPE = 1 and 0; after sret to "
        "S, sstatus.SPELP reads 0.\n"
        "3. H: mret to VS (henvcfg.LPE) and VU (senvcfg.LPE) with MPV=1.",
    )
    m_deleg_off(t)

    def set_en(en: dict) -> None:
        z.mlpe(t, bool(en.get("mlpe")))
        with t.only_if("defined(U_SUPPORTED)"):
            t.emit(f"csr{'s' if en.get('menvcfg') else 'c'}i {z.CSR['menvcfg']:#x}, {z.LPE}  // menvcfg.LPE")
        with t.only_if(z.S_IMPL):
            t.emit(f"csr{'s' if en.get('senvcfg') else 'c'}i {z.CSR['senvcfg']:#x}, {z.LPE}  // senvcfg.LPE")
        with t.only_if(H):
            t.emit(f"csr{'s' if en.get('henvcfg') else 'c'}i {z.CSR['henvcfg']:#x}, {z.LPE}  // henvcfg.LPE")

    def sweep(kind: str, y: str, key: str, s_impl: bool, targets: list, after: bool) -> None:
        for lpe in (1, 0):
            en = {kk: 1 - lpe for kk in ("mlpe", "menvcfg", "senvcfg", "henvcfg")}
            en[key] = lpe
            set_en(en)
            for xp in (1, 0):
                for tg in targets:
                    z.xret_case(
                        t,
                        kind,
                        y,
                        xp,
                        tg,
                        z.xret_expect(y, xp, tg, en, s_impl, frm="M"),
                        f"{kind} in M to {y}, {y} LPE={lpe} (others {1 - lpe})",
                        after_pelp=after,
                        pelp=1,
                    )

    sweep("mret", "M", "mlpe", True, [nonlp(), lp(0)], True)
    with t.only_if(z.S_IMPL):
        sweep("mret", "S", "menvcfg", True, [nonlp(), lp(0)], False)
        sweep("mret", "U", "senvcfg", True, [nonlp(), lp(0)], False)
        sweep("sret", "S", "menvcfg", True, [nonlp()], True)
        sweep("sret", "U", "senvcfg", True, [nonlp()], False)
    with t.only_if("defined(U_SUPPORTED) && !defined(S_SUPPORTED)"):
        sweep("mret", "U", "menvcfg", False, [nonlp(), lp(0)], False)
    with t.only_if(H):
        sweep("mret", "VS", "henvcfg", True, [nonlp()], False)
        sweep("mret", "VU", "senvcfg", True, [nonlp()], False)
        z.mpv_set(t, False)
    set_en({})
    m_deleg_restore(t)
    return t


# ---------------------------------------------------------------- enables
def en_sweep(t: TestFile, combos: list, mode_list: list, tag: str, s_impl: bool = True) -> None:
    """For each enable combination (S-boot: menvcfg, senvcfg, henvcfg), representative cases in each mode."""
    for en in combos:
        z.s_enables(
            t, bool(en.get("menvcfg")), bool(en.get("senvcfg")), bool(en.get("henvcfg")) if "henvcfg" in en else None
        )
        for m in mode_list:
            on = z.enforced(m, en, s_impl)
            desc = f"{tag} " + ", ".join(f"{k}.LPE={v}" for k, v in en.items())

            def body(m: str = m, on: bool = on, desc: str = desc) -> None:
                z.rep_cases(t, m, on, desc, short=True)

            if m in ("VS", "VU"):
                with t.only_if(H):
                    body()
            else:
                body()


def readback_lpe(t: TestFile, csr: str, how: str) -> None:
    """Set and clear an LPE bit and read it back (S-mode csr, or M-level through T-SBI)."""
    ro = MUT == "lpe_field_ro"
    for v in (1, 0):
        lab = t.label("rb")
        if how == "tsbi":
            t.tsbi_csr("SET" if v else "CLEAR", csr.upper(), imm=z.LPE)
            t.tsbi_csr("READ", csr.upper())
            reg = "a0"
        else:
            t.emit(f"csr{'s' if v else 'c'}i {z.CSR[csr]:#x}, {z.LPE}  // {csr}")
            t.emit(f"csrr x9, {z.CSR[csr]:#x}")
            reg = "x9"
        t.emit(f"{lab}:", 0)
        t.emit(f"andi {reg}, {reg}, {z.LPE}")
        t.check(reg, 0 if ro else v * z.LPE, lab, f"{csr}.LPE written {v} reads back")


def t_menvcfg_lpe_lead_in() -> TestFile:
    t = new("menvcfg_lpe_op_lead_in")
    t.describe(
        source=z.MAC,
        rule_text="The Zicfilp extension adds the LPE field in menvcfg. When the LPE field is set to 1 and S-mode is "
        "implemented, the Zicfilp extension is enabled in S-mode. If LPE field is set to 1 and S-mode is not "
        "implemented, the Zicfilp extension is enabled in U-mode. When the LPE field is 0, the Zicfilp extension is "
        "not enabled in S-mode, and the following rules apply to S-mode. If the LPE field is 0 and S-mode is not "
        "implemented, then the same rules apply to U-mode.",
        context="S-mode boot (S implemented): menvcfg.LPE controls S only; U and VU follow senvcfg.LPE and VS "
        f"henvcfg.LPE ({ISSUE}3142: menvcfg.LPE=0 does not make senvcfg.LPE or henvcfg.LPE read-only zero). The "
        "_Sm file covers M-mode and harts without S.",
        plan="1. menvcfg.LPE set and cleared through T-SBI reads back.\n"
        "2. (menvcfg.LPE, senvcfg.LPE) over 10, 01, 11, 00 (henvcfg.LPE = 1 with H): representative cases (indirect "
        "jump and call to a non-lpad, indirect jump to ebreak) in S, U, VU and VS fault exactly where the mode's own "
        "enable is 1.",
    )
    readback_lpe(t, "menvcfg", "tsbi")
    combos = [{"menvcfg": a, "senvcfg": b, "henvcfg": 1} for a, b in ((1, 0), (0, 1), (1, 1), (0, 0))]
    en_sweep(t, combos, ["S", "U", "VU", "VS"], "")
    z.s_teardown(t)
    return t


def t_menvcfg_lpe_lead_in_sm() -> TestFile:
    t = new("menvcfg_lpe_op_lead_in", sm=True, required=z.REQ_MU)
    t.describe(
        source=z.MAC,
        rule_text="The Zicfilp extension adds the LPE field in menvcfg. When the LPE field is set to 1 and S-mode is "
        "implemented, the Zicfilp extension is enabled in S-mode. If LPE field is set to 1 and S-mode is not "
        "implemented, the Zicfilp extension is enabled in U-mode. When the LPE field is 0, the Zicfilp extension is "
        "not enabled in S-mode, and the following rules apply to S-mode. If the LPE field is 0 and S-mode is not "
        "implemented, then the same rules apply to U-mode.",
        context="M-mode part: menvcfg.LPE does not enable M-mode (mseccfg.MLPE=0), and on a hart without S it "
        "enables U-mode. medeleg[3] and [18] are cleared.",
        plan="1. menvcfg.LPE reads back 1 and 0 after M-mode csrs/csrc.\n"
        "2. menvcfg.LPE=1, MLPE=0: M-mode is not enforced.\n"
        "3. Without S: U-mode is enforced exactly when menvcfg.LPE=1 (1, 0, 1).",
    )
    m_deleg_off(t)
    ro = MUT == "lpe_field_ro"
    for v in (1, 0):
        lab = t.label("rb")
        t.emit(f"csr{'s' if v else 'c'}i {z.CSR['menvcfg']:#x}, {z.LPE}")
        t.emit(f"csrr x9, {z.CSR['menvcfg']:#x}")
        t.emit(f"andi x9, x9, {z.LPE}")
        t.emit(f"{lab}:", 0)
        t.check("x9", 0 if ro else v * z.LPE, lab, f"menvcfg.LPE written {v} reads back")
    t.emit(f"csrsi {z.CSR['menvcfg']:#x}, {z.LPE}")
    z.mlpe(t, False)
    z.rep_cases(t, "M", z.enforced("M", {"menvcfg": 1}), "M-mode with menvcfg.LPE=1, MLPE=0", short=True)
    with t.only_if("!defined(S_SUPPORTED)"):
        for v in (1, 0, 1):
            t.emit(f"csr{'s' if v else 'c'}i {z.CSR['menvcfg']:#x}, {z.LPE}")
            z.rep_cases(t, "U", z.enforced("U", {"menvcfg": v}, s_impl=False), f"U-mode without S, menvcfg.LPE={v}")
    t.emit(f"csrci {z.CSR['menvcfg']:#x}, {z.LPE}")
    m_deleg_restore(t)
    return t


def disabled_bullets(t: TestFile, m: str, tag: str) -> None:
    """The two bullets for a mode whose LPE is 0: ELP is not updated (an indirect jump to ebreak takes a
    breakpoint with xPELP=0; to a non-lpad, no fault) and lpad is a no-op (mismatched or misaligned lpad reached
    by an indirect jump does not fault, registers unchanged)."""
    lp_case(t, m, J("jalr", 0, 6), ebreak(), f"{tag}: indirect jump to ebreak (ELP not updated)", enforced=False)
    lp_case(t, m, J("jalr", 1, 8), ebreak(), f"{tag}: indirect call to ebreak (ELP not updated)", enforced=False)
    lp_case(t, m, J("jalr", 0, 6), nonlp(), f"{tag}: indirect jump to a non-lpad", enforced=False)
    tg = T(
        [z.lpad(LAB)],
        f"lpad {LAB:#x}",
        lp=LAB,
        check=[("x9", 0x5A5, "x9 unchanged"), ("x7", X(0x7000, 0x7000), "x7 unchanged")],
    )
    land(
        t,
        m,
        J("jalr", 0, 6),
        tg,
        SWCHK if MUT == "disabled_lpad_checks" else "ok",
        f"{tag}: mismatched lpad is a no-op",
        pre=["li x9, 0x5A5"],
        x7=X(0x7000, 0x7000),
    )
    with t.only_if(ZCA):
        lp_case(t, m, J("jalr", 0, 6), lp(0, True), f"{tag}: misaligned lpad is a no-op", enforced=False)


def t_menvcfg_lpe_list() -> TestFile:
    t = new("menvcfg_lpe_op_list")
    t.describe(
        source=z.MAC,
        rule_text="[When menvcfg.LPE is 0, for S-mode:] The hart does not update the ELP state; it remains as "
        "NO_LP_EXPECTED. The LPAD instruction operates as a no-op.",
        context="S-mode boot with menvcfg.LPE=0 and every other enable set (senvcfg.LPE=1, henvcfg.LPE=1), so only "
        "S-mode is disabled. ELP not being updated is shown by an indirect jump to ebreak taking a breakpoint with "
        "SPELP=0, not merely by the absence of a landing-pad fault. The _Sm file covers U on a hart without S.",
        plan="In S-mode with menvcfg.LPE=0: indirect jump and call to ebreak (cause 3, SPELP=0), indirect jump to a "
        "non-lpad (no fault), and a mismatched lpad and (C) a misaligned lpad reached by an indirect jump (no fault, "
        "x7 and x9 unchanged). Then U-mode with senvcfg.LPE=1 still faults (contrast).",
    )
    z.s_enables(t, False, True, True)
    disabled_bullets(t, "S", "S-mode, menvcfg.LPE=0")
    lp_case(t, "U", J("jalr", 0, 6), nonlp(), "U-mode, senvcfg.LPE=1 (contrast)", z.enforced("U", {"senvcfg": 1}))
    z.s_teardown(t)
    return t


def t_menvcfg_lpe_list_sm() -> TestFile:
    t = new("menvcfg_lpe_op_list", sm=True, required=z.REQ_MU)
    t.describe(
        source=z.MAC,
        rule_text="[When menvcfg.LPE is 0, for S-mode, or U-mode when S-mode is not implemented:] The hart does not "
        "update the ELP state; it remains as NO_LP_EXPECTED. The LPAD instruction operates as a no-op.",
        context="M-mode part, for harts without S: menvcfg.LPE=0 disables landing pads in U-mode. medeleg[3] and "
        "[18] are cleared.",
        plan="Without S, U-mode with menvcfg.LPE=0: indirect jump and call to ebreak (cause 3, MPELP=0), indirect "
        "jump to a non-lpad (no fault), mismatched and (C) misaligned lpads are no-ops.",
    )
    m_deleg_off(t)
    with t.only_if("!defined(S_SUPPORTED)"):
        t.emit(f"csrci {z.CSR['menvcfg']:#x}, {z.LPE}")
        disabled_bullets(t, "U", "U-mode without S, menvcfg.LPE=0")
    m_deleg_restore(t)
    return t


def t_senvcfg_lpe() -> TestFile:
    t = new("senvcfg_lpe_Zicfilp")
    t.describe(
        source=z.SUP,
        rule_text="The Zicfilp extension adds the LPE field in senvcfg. When the LPE field is set to 1, the Zicfilp "
        "extension is enabled in VU/U-mode. When the LPE field is 0, the Zicfilp extension is not enabled in "
        "VU/U-mode and the following rules apply to VU/U-mode: The hart does not update the ELP state; it remains as "
        "NO_LP_EXPECTED. The LPAD instruction operates as a no-op.",
        context=f"senvcfg.LPE is independent of menvcfg.LPE ({ISSUE}3142). It does not affect S or VS.",
        plan="1. senvcfg.LPE reads back 1 and 0.\n"
        "2. (senvcfg.LPE, menvcfg.LPE, henvcfg.LPE) over 100, 011, 111, 000: representative cases in U, VU (enforced "
        "iff senvcfg.LPE), S (iff menvcfg.LPE) and VS (iff henvcfg.LPE).\n"
        "3. senvcfg.LPE=0 with the others 1: in U and VU, ELP is not updated (indirect jumps to ebreak: cause 3 with "
        "SPELP=0) and lpad is a no-op.",
    )
    readback_lpe(t, "senvcfg", "csr")
    combos = [{"menvcfg": b, "senvcfg": a, "henvcfg": b} for a, b in ((1, 0), (0, 1), (1, 1), (0, 0))]
    en_sweep(t, combos, ["U", "VU", "S", "VS"], "")
    z.s_enables(t, True, False, True)
    disabled_bullets(t, "U", "U-mode, senvcfg.LPE=0")
    with t.only_if(H):
        disabled_bullets(t, "VU", "VU-mode, senvcfg.LPE=0")
    z.s_teardown(t)
    return t


def t_henvcfg_lpe() -> TestFile:
    t = new("henvcfg_lpe_op", required=["I", "S", "H", "Zicfilp"])
    t.describe(
        source=z.HYP,
        rule_text="The Zicfilp extension adds the LPE field in henvcfg. When the LPE field is set to 1, the Zicfilp "
        "extension is enabled in VS-mode. When the LPE field is 0, the Zicfilp extension is not enabled in VS-mode "
        "and the following rules apply to VS-mode: The hart does not update the ELP state; it remains as "
        "NO_LP_EXPECTED. The LPAD instruction operates as a no-op.",
        context=f"henvcfg.LPE is independent of menvcfg.LPE ({ISSUE}3142), and does not affect VU (senvcfg.LPE) or "
        "HS (menvcfg.LPE).",
        plan="1. henvcfg.LPE reads back 1 and 0.\n"
        "2. (henvcfg.LPE, menvcfg.LPE, senvcfg.LPE) over 100, 011, 111, 000: representative cases in VS (enforced iff "
        "henvcfg.LPE), VU (iff senvcfg.LPE) and S (iff menvcfg.LPE).\n"
        "3. henvcfg.LPE=0 with the others 1: in VS, ELP is not updated (cause 3 with SPELP=0 at an ebreak target) and "
        "lpad is a no-op.",
    )
    readback_lpe(t, "henvcfg", "csr")
    combos = [{"menvcfg": b, "senvcfg": b, "henvcfg": a} for a, b in ((1, 0), (0, 1), (1, 1), (0, 0))]
    en_sweep(t, combos, ["VS", "VU", "S"], "")
    z.s_enables(t, True, True, False)
    disabled_bullets(t, "VS", "VS-mode, henvcfg.LPE=0")
    z.s_teardown(t)
    return t


def mseccfg_rb(t: TestFile) -> None:
    ro = MUT == "lpe_field_ro"
    for v in (1, 0):
        lab = t.label("rb")
        z.mlpe(t, bool(v))
        t.emit(f"csrr x9, {z.CSR['mseccfg']:#x}  // mseccfg")
        t.li("x5", z.MLPE)
        t.emit("and x9, x9, x5")
        t.emit(f"{lab}:", 0)
        t.check("x9", 0 if ro else v * z.MLPE, lab, f"mseccfg.MLPE written {v} (csrs/csrc) reads back")


def t_mlpe_presence() -> TestFile:
    t = new("mseccfg_mlpe_presence", sm=True)
    t.describe(
        source=z.MAC,
        rule_text="The Zicfilp extension adds the MLPE field in mseccfg.",
        context="mseccfg.MLPE is bit 10.",
        plan="1. csrs/csrc of MLPE: reads back 1 and 0.\n"
        "2. csrrw of mseccfg with MLPE set and clear (other bits as read): reads back 1 and 0, and csrrw returns the "
        "old value's MLPE.",
    )
    mseccfg_rb(t)
    ro = MUT == "lpe_field_ro"
    for v in (1, 0):
        lab = t.label("rw")
        t.emit(f"csrr x6, {z.CSR['mseccfg']:#x}")
        t.li("x5", z.MLPE)
        if v:
            t.emit("or x6, x6, x5")
        else:
            t.emit("not x5, x5")
            t.emit("and x6, x6, x5")
        t.emit(f"csrrw x8, {z.CSR['mseccfg']:#x}, x6")
        t.emit(f"csrr x9, {z.CSR['mseccfg']:#x}")
        t.li("x5", z.MLPE)
        t.emit("and x9, x9, x5")
        t.emit("and x8, x8, x5")
        t.emit(f"{lab}:", 0)
        t.check("x9", 0 if ro else v * z.MLPE, lab, f"csrrw mseccfg with MLPE={v} reads back")
        t.check("x8", 0 if (ro or v) else z.MLPE, lab, "csrrw returns the previous MLPE")
    return t


def t_mlpe_set() -> TestFile:
    t = new("mseccfg_mlpe_set_op", sm=True)
    t.describe(
        source=z.MAC,
        rule_text="When MLPE field is 1, Zicfilp extension is enabled in M-mode.",
        context="medeleg[3] and [18] are cleared. MLPE=1 enables only M-mode: S and U stay disabled with "
        "menvcfg.LPE=0 and senvcfg.LPE=0.",
        plan="1. MLPE=1: representative M-mode cases (non-lpad targets of an indirect jump and call fault, lpad 0 "
        "and a matching lpad do not, a mismatched and (C) a misaligned lpad fault, x7 and x1 jumps do not, an ebreak "
        "target faults with MPELP=1).\n"
        "2. MLPE=1, menvcfg.LPE=0, senvcfg.LPE=0: S and U are not enforced.",
    )
    m_deleg_off(t)
    z.mlpe(t, True)
    z.rep_cases(t, "M", z.enforced("M", {"mlpe": 1}), "M-mode, MLPE=1")
    m_lower_lpe(t, False)
    with t.only_if("defined(U_SUPPORTED)"):
        z.rep_cases(t, "U", z.enforced("U", {"mlpe": 1}), "U-mode, MLPE=1, LPE=0", short=True)
    with t.only_if(z.S_IMPL):
        z.rep_cases(t, "S", z.enforced("S", {"mlpe": 1}), "S-mode, MLPE=1, menvcfg.LPE=0", short=True)
    z.mlpe(t, False)
    m_deleg_restore(t)
    return t


def t_mlpe_clr_lead_in() -> TestFile:
    t = new("mseccfg_mlpe_clr_op_lead_in", sm=True)
    t.describe(
        source=z.MAC,
        rule_text="When the MLPE field is 0, the Zicfilp extension is not enabled in M-mode and the following rules "
        "apply to M-mode.",
        context="medeleg[3] and [18] are cleared. The lower modes' enables do not enable M-mode.",
        plan="1. MLPE=0 with menvcfg.LPE=1 and senvcfg.LPE=1 (where they exist): representative M-mode cases do not "
        "fault.\n"
        "2. MLPE set to 1 and back to 0 (transition): the M-mode cases fault, then do not.",
    )
    m_deleg_off(t)
    m_lower_lpe(t, True)
    z.mlpe(t, False)
    z.rep_cases(t, "M", z.enforced("M", {"menvcfg": 1, "senvcfg": 1}), "M-mode, MLPE=0, lower LPE=1")
    z.mlpe(t, True)
    z.rep_cases(t, "M", z.enforced("M", {"mlpe": 1}), "M-mode, MLPE=1", short=True)
    z.mlpe(t, False)
    z.rep_cases(t, "M", z.enforced("M", {"menvcfg": 1}), "M-mode, MLPE cleared again", short=True)
    m_lower_lpe(t, False)
    m_deleg_restore(t)
    return t


def t_mlpe_clr_list() -> TestFile:
    t = new("mseccfg_mlpe_clr_op_list", sm=True)
    t.describe(
        source=z.MAC,
        rule_text="[When MLPE is 0, for M-mode:] The hart does not update the ELP state; it remains as "
        "NO_LP_EXPECTED. The LPAD instruction operates as a no-op.",
        context="medeleg[3] and [18] are cleared, menvcfg.LPE and senvcfg.LPE are 1 where they exist.",
        plan="M-mode with MLPE=0: indirect jump and call to ebreak take a breakpoint with MPELP=0; a non-lpad target "
        "does not fault; a mismatched and (C) a misaligned lpad reached by an indirect jump are no-ops (x7, x9 "
        "unchanged).",
    )
    m_deleg_off(t)
    m_lower_lpe(t, True)
    z.mlpe(t, False)
    disabled_bullets(t, "M", "M-mode, MLPE=0")
    m_lower_lpe(t, False)
    m_deleg_restore(t)
    return t


def t_mlpe_rst() -> TestFile:
    t = new("mseccfg_mlpe_rst", sm=True)
    t.describe(
        source=z.MAC,
        rule_text="If the Zicfilp extension is implemented, the mseccfg.MLPE field is reset to 0.",
        context="The framework's boot writes mseccfg = 0 when Smmpm is implemented, which hides the reset value; the "
        "check runs only without Smmpm. It is the first thing the test does.",
        issues=f"{ISSUE}1591: MLPE resets to 0.",
        plan="Without Smmpm: mseccfg.MLPE reads 0 at the start of the test.",
    )
    with t.only_if("!defined(SMMPM_SUPPORTED)"):
        lab = t.label("rst")
        t.emit(f"csrr x9, {z.CSR['mseccfg']:#x}")
        t.li("x5", z.MLPE)
        t.emit("and x9, x9, x5")
        t.emit(f"{lab}:", 0)
        t.check("x9", z.MLPE if MUT == "mlpe_reset_one" else 0, lab, "mseccfg.MLPE after reset")
    return t


# ---------------------------------------------------------------- PELP fields
def t_mstatus_pelp_op() -> TestFile:
    t = new("mstatus_spelp_mpelp_op")
    t.describe(
        source=z.MAC,
        rule_text="The zicfilp extension adds the spelp and mpelp fields that hold the previous elp, and are updated "
        "as specified in ZICFILP_FORWARD_TRAPS.",
        context="S-mode part: SPELP. Landing pads are enabled in S and U. SPELP is writable whatever menvcfg.LPE "
        f"(as for MPELP, {ISSUE}3331). The _Sm file covers MPELP and harts without S.",
        plan="1. SPELP set and cleared through sstatus reads back, with menvcfg.LPE = 1 and 0.\n"
        "2. A trap into S with ELP=1 (from U and S) sets it to 1; with ELP=0 to 0.\n"
        "3. An sret from S to S with SPELP=1 (menvcfg.LPE=1) makes ELP=1 at its target, and sets SPELP to 0.",
    )
    for s_on in (True, False):
        z.menvcfg_lpe(t, s_on)
        for v in (1, 0):
            t.li("x6", z.SPELP)
            t.emit(f"csr{'s' if v else 'c'} sstatus, x6")
            t.emit("csrr x9, sstatus")
            t.emit("srli x9, x9, 23")
            t.emit("andi x9, x9, 1")
            lab = t.label("rb")
            t.emit(f"{lab}:", 0)
            t.check(
                "x9",
                0 if MUT == "spelp_not_writable" else v,
                lab,
                f"SPELP written {v} with menvcfg.LPE={int(s_on)} reads back",
            )
    z.s_enables(t, True, True)
    for m in ("U", "S"):
        trap_pelp_cases(t, m, f"trap from {m}")
    en = {"menvcfg": 1, "senvcfg": 1}
    z.xret_case(
        t,
        "sret",
        "S",
        1,
        nonlp(),
        z.xret_expect("S", 1, nonlp(), en),
        "sret to S with SPELP=1",
        after_pelp=True,
        pelp=1,
    )
    z.xret_case(
        t,
        "sret",
        "S",
        1,
        lp(0),
        z.xret_expect("S", 1, lp(0), en),
        "sret to S with SPELP=1 to lpad 0",
        after_pelp=True,
        pelp=1,
    )
    z.s_teardown(t)
    return t


def t_mstatus_pelp_op_sm() -> TestFile:
    t = new("mstatus_spelp_mpelp_op", sm=True)
    t.describe(
        source=z.MAC,
        rule_text="The zicfilp extension adds the spelp and mpelp fields that hold the previous elp, and are updated "
        "as specified in ZICFILP_FORWARD_TRAPS. [...] If supervisor mode is not implemented, spelp is read-only 0.",
        context=f"M-mode part. MPELP is writable whatever MLPE ({ISSUE}3331). Without S, SPELP is read-only zero "
        f'({ISSUE}3371: "When S/HS is not implemented ... this bit is not provided - is read-only zero"). '
        "medeleg[3] and [18] are cleared.",
        plan="1. MPELP set and cleared reads back with MLPE = 0 and 1.\n"
        "2. Traps into M with ELP=1 set MPELP=1, with ELP=0 clear it (from M, and U where implemented).\n"
        "3. Without S: setting mstatus.SPELP leaves it 0.",
    )
    m_deleg_off(t)
    for on in (False, True):
        z.mlpe(t, on)
        for v in (1, 0):
            z.mpelp_set(t, bool(v))
            z.mpelp_read(t, "x9")
            lab = t.label("rd")
            t.emit(f"{lab}:", 0)
            t.check(
                "x9",
                0 if (MUT == "mpelp_ro_mlpe0" and not on) else v,
                lab,
                f"MPELP written {v} with MLPE={int(on)} reads back",
            )
    m_lower_lpe(t, True)
    trap_pelp_cases(t, "M", "trap from M", [3])
    with t.only_if("defined(U_SUPPORTED)"):
        trap_pelp_cases(t, "U", "trap from U", [3])
    z.mlpe(t, False)
    m_lower_lpe(t, False)
    with t.only_if("!defined(S_SUPPORTED)"):
        t.li("x5", z.SPELP)
        t.emit("csrs mstatus, x5")
        t.emit("csrr x9, mstatus")
        t.emit("srli x9, x9, 23")
        t.emit("andi x9, x9, 1")
        lab = t.label("ro")
        t.emit(f"{lab}:", 0)
        t.check("x9", 0, lab, "without S, mstatus.SPELP is read-only 0")
    m_deleg_restore(t)
    return t


def t_pelp_enc_list() -> TestFile:
    t = new("mstatus_spelp_mpelp_enc_list")
    t.describe(
        source=z.MAC,
        rule_text="0 - NO_LP_EXPECTED - no landing pad instruction expected. 1 - LP_EXPECTED - a landing pad "
        "instruction is expected.",
        context="The encoding of SPELP (and MPELP, in the _Sm file): a trap with ELP=LP_EXPECTED saves 1, with "
        "NO_LP_EXPECTED 0; an sret with SPELP=1 into a mode with LPE=1 expects a landing pad at its target, with "
        "SPELP=0 it does not.",
        plan="1. U and S (LPE=1): landing-pad fault saves SPELP=1; ebreak with ELP clear saves 0.\n"
        "2. sret to U and S with SPELP=1: a non-lpad target faults; with SPELP=0 it does not.",
    )
    z.s_enables(t, True, True)
    en = {"menvcfg": 1, "senvcfg": 1}
    for m in ("U", "S"):
        trap_pelp_cases(t, m, f"trap from {m}")
        for xp in (1, 0):
            z.xret_case(
                t, "sret", m, xp, nonlp(), z.xret_expect(m, xp, nonlp(), en), f"sret to {m}, SPELP={xp}", pelp=1
            )
    z.s_teardown(t)
    return t


def t_pelp_enc_list_sm() -> TestFile:
    t = new("mstatus_spelp_mpelp_enc_list", sm=True)
    t.describe(
        source=z.MAC,
        rule_text="0 - NO_LP_EXPECTED - no landing pad instruction expected. 1 - LP_EXPECTED - a landing pad "
        "instruction is expected.",
        context="MPELP (mstatush on RV32). MLPE=1, medeleg[3] and [18] cleared.",
        plan="1. M-mode landing-pad fault saves MPELP=1; ebreak with ELP clear saves 0.\n"
        "2. mret to M with MPELP=1: a non-lpad target faults; with MPELP=0 it does not.",
    )
    m_deleg_off(t)
    z.mlpe(t, True)
    trap_pelp_cases(t, "M", "trap from M", [3])
    for xp in (1, 0):
        z.xret_case(
            t,
            "mret",
            "M",
            xp,
            nonlp(),
            z.xret_expect("M", xp, nonlp(), {"mlpe": 1}, frm="M"),
            f"mret to M, MPELP={xp}",
            pelp=1,
        )
    z.mlpe(t, False)
    m_deleg_restore(t)
    return t


def tval_cases(t: TestFile, m: str, handler: list | None, tag: str, zca: bool = True) -> None:
    lp_case(t, m, J("jalr", 0, 6), nonlp(), f"{tag}: non-lpad")
    lp_case(t, m, J("jalr", 0, 8), lp(LAB), f"{tag}: mismatched label", x7=0)
    if zca:
        with t.only_if(ZCA):
            lp_case(t, m, J("jalr", 0, 9), lp(0, True), f"{tag}: misaligned lpad")
    if handler:
        land(t, m, J("jalr", 0, 6), nonlp(), SWCHK, f"{tag}: handler", handler=handler)


def t_stval_info() -> TestFile:
    t = new("stval_exception_info")
    t.describe(
        source=z.SUP,
        rule_text="On a trap caused by a software-check exception, the stval register holds the cause for the "
        "exception. The following encodings are defined: 0 - No information provided. 2 - Landing Pad Fault. "
        "Defined by the Zicfilp extension. 3 - Shadow Stack Fault. Defined by the Zicfiss extension.",
        context='Every landing-pad fault must leave stval (vstval in VS) = 2, or 0 ("no information provided": the '
        "platform may make stval zero for an exception, norm:stval); never 3, the target address or the instruction "
        "bits. Faults from U and S go to S (medeleg[18]=1), from VU and VS to HS, or with hedeleg[18]=1 to VS.",
        plan="1. In U, S, VU and VS: non-lpad, mismatched label and (C) misaligned lpad faults: xtval in {0, 2}.\n"
        "2. H, hedeleg[18]=1 (if writable): the same from VU and VS into the VS handler (vstval).",
    )
    setup_all(t)
    modes(t, lambda m: tval_cases(t, m, None, f"{m}-mode"))
    with t.only_if(H):
        t.li("x6", 1 << 18)
        t.emit(f"csrs {z.CSR['hedeleg']:#x}, x6")
        t.emit(f"csrr x6, {z.CSR['hedeleg']:#x}")
        t.emit("srli x6, x6, 18")
        t.emit("andi x6, x6, 1")
        t.either(
            "x6", lambda: [tval_cases(t, m, [2], f"{m}-mode into VS", zca=False) for m in ("VU", "VS")], lambda: None
        )
        t.li("x6", 1 << 18)
        t.emit(f"csrc {z.CSR['hedeleg']:#x}, x6")
    z.s_teardown(t)
    return t


def t_mtval_swchk(rule: str, text: str, plan: str, kinds: bool) -> TestFile:
    t = new(rule, sm=True)
    t.describe(
        source=z.MAC,
        rule_text=text,
        context='Traps into M (medeleg[18] cleared). mtval must be 2, or 0 ("No information provided"; the '
        "platform may make mtval zero, norm:mtval_per_exc_behavior); never 3, the address or the instruction.",
        plan=plan,
    )
    m_deleg_off(t)
    z.mlpe(t, True)
    m_lower_lpe(t, True)
    if kinds:
        tval_cases(t, "M", [3], "M-mode")
    else:
        lp_case(t, "M", J("jalr", 0, 6), nonlp(), "M-mode")
        with t.only_if("defined(U_SUPPORTED)"):
            lp_case(t, "U", J("jalr", 0, 6), nonlp(), "U-mode")
        with t.only_if(z.S_IMPL):
            lp_case(t, "S", J("jalr", 0, 6), nonlp(), "S-mode")
    z.mlpe(t, False)
    m_lower_lpe(t, False)
    m_deleg_restore(t)
    return t


# ---------------------------------------------------------------- H: vsstatus.SPELP and sstatus aliasing
def t_vsstatus_spelp_exists() -> TestFile:
    t = new("vsstatus_spelp_exists", required=["I", "S", "H", "Zicfilp"])
    t.describe(
        source=z.PRIV,
        rule_text="To store the previous ELP state on traps to VS-mode, a spelp bit is defined in the vsstatus "
        "(VS-modes version of sstatus).",
        context="vsstatus.SPELP is bit 23. Traps into VS need hedeleg[18] (and [3] for ebreak); those cases run only "
        "if the bits read back 1.",
        plan="1. HS-mode writes: vsstatus.SPELP set and cleared reads back.\n"
        "2. Traps from VU and VS into VS (hedeleg): vsstatus.SPELP = 1 after a landing-pad fault, 0 after an ebreak.",
    )
    setup_all(t)
    for v in (1, 0):
        t.li("x6", z.SPELP)
        t.emit(f"csr{'s' if v else 'c'} {z.CSR['vsstatus']:#x}, x6  // vsstatus")
        t.emit(f"csrr x9, {z.CSR['vsstatus']:#x}")
        t.emit("srli x9, x9, 23")
        t.emit("andi x9, x9, 1")
        lab = t.label("rb")
        t.emit(f"{lab}:", 0)
        t.check("x9", v, lab, f"vsstatus.SPELP written {v} reads back")
    vs_deleg(t, lambda: [trap_pelp_cases(t, m, f"trap from {m} into VS", [2], zca=False) for m in ("VU", "VS")])
    z.s_teardown(t)
    return t


def vs_deleg(t: TestFile, body) -> None:  # noqa: ANN001
    t.li("x6", (1 << 18) | (1 << 3))
    t.emit(f"csrs {z.CSR['hedeleg']:#x}, x6")
    t.emit(f"csrr x6, {z.CSR['hedeleg']:#x}")
    t.li("x7", (1 << 18) | (1 << 3))
    t.emit("and x6, x6, x7")
    t.emit("xor x6, x6, x7")
    t.emit("seqz x6, x6  // 1: hedeleg[3] and [18] took")
    t.either("x6", body, lambda: None)
    t.li("x6", (1 << 18) | (1 << 3))
    t.emit(f"csrc {z.CSR['hedeleg']:#x}, x6")


def read_vsstatus_spelp(t: TestFile, exp: int, desc: str) -> None:
    lab = t.label("vs")
    t.emit(f"csrr x9, {z.CSR['vsstatus']:#x}")
    t.emit("srli x9, x9, 23")
    t.emit("andi x9, x9, 1")
    t.emit(f"{lab}:", 0)
    t.check("x9", exp, lab, f"{desc}: vsstatus.SPELP")


def t_vsstatus_spelp_op() -> TestFile:
    t = new("vsstatus_spelp_op", required=["I", "S", "H", "Zicfilp"])
    t.describe(
        source=z.HYP,
        rule_text="The Zicfilp extension adds the SPELP field that holds the previous ELP, and is updated as "
        "specified in ZICFILP_FORWARD_TRAPS. The SPELP field is encoded as follows: 0 - NO_LP_EXPECTED - no landing "
        "pad instruction expected. 1 - LP_EXPECTED - a landing pad instruction is expected.",
        context="Landing pads are enabled in every mode. Traps into VS need hedeleg[18] and [3]; those cases run only "
        "if the bits read back 1.",
        plan="1. Traps into VS (from VU and VS) save ELP in vsstatus.SPELP: 1 after a landing-pad fault, 0 after an "
        "ebreak (vsstatus at VS handler entry).\n"
        "2. Traps into HS from VU leave vsstatus.SPELP alone: vsstatus.SPELP=1 (written by HS) still reads 1 after a "
        "landing-pad fault from VU taken in HS, and 0 still reads 0.\n"
        "3. sret in VS-mode uses vsstatus.SPELP: to VU and to VS with SPELP=1 a non-lpad target faults, with 0 it "
        "does not; after sret from VS to VS, vsstatus.SPELP reads 0.",
    )
    setup_all(t)
    vs_deleg(t, lambda: [trap_pelp_cases(t, m, f"trap from {m} into VS", [2], zca=False) for m in ("VU", "VS")])
    for v in (1, 0):
        t.li("x6", z.SPELP)
        t.emit(f"csr{'s' if v else 'c'} {z.CSR['vsstatus']:#x}, x6  // vsstatus.SPELP = {v}")
        land(
            t,
            "VU",
            J("jalr", 0, 6),
            nonlp(),
            SWCHK,
            f"fault from VU into HS with vsstatus.SPELP={v}",
            pelp=1,
            handler=[1, 3],
        )
        exp = 1 if MUT == "hs_trap_writes_vsstatus" else v
        read_vsstatus_spelp(t, exp, f"after a trap into HS (vsstatus.SPELP was {v})")
    en = {"menvcfg": 1, "senvcfg": 1, "henvcfg": 1}
    for y in ("VU", "VS"):
        for xp in (1, 0):
            z.xret_case(
                t,
                "sret",
                y,
                xp,
                nonlp(),
                z.xret_expect(y, xp, nonlp(), en, frm="VS"),
                f"sret in VS to {y}, vsstatus.SPELP={xp}",
                frm="VS",
                after_pelp=(y == "VS"),
                pelp=1,
            )
    t.li("x6", z.SPELP)
    t.emit(f"csrc {z.CSR['vsstatus']:#x}, x6")
    z.s_teardown(t)
    return t


def t_sstatus_spelp() -> TestFile:
    t = new("sstatus_spelp")
    t.describe(
        source=z.SUP,
        rule_text="Access to the SPELP field, added by Zicfilp, accesses the homonymous fields of mstatus when V=0, "
        "and the homonymous fields of vsstatus when V=1.",
        context="V=0: S-mode sstatus.SPELP against mstatus.SPELP (T-SBI reads and writes). V=1 (H): VS-mode reads and "
        "writes of sstatus.SPELP against vsstatus.SPELP read and written in HS-mode; VS-mode is entered and left "
        "with T-SBI GOTOs, which do not change vsstatus.",
        plan="1. V=0: sstatus.SPELP writes appear in mstatus, mstatus writes in sstatus (1 and 0).\n"
        "2. V=1: vsstatus.SPELP = 1 and 0 (HS write) with mstatus.SPELP the opposite: a VS-mode read of "
        "sstatus.SPELP returns the vsstatus value.\n"
        "3. V=1: VS-mode csrs/csrc of sstatus.SPELP changes vsstatus.SPELP (read in HS).",
    )
    spelp_alias_cases(t)
    alias = MUT == "sstatus_spelp_v1_mstatus"
    with t.only_if(H):
        for v in (1, 0):
            t.li("x6", z.SPELP)
            t.emit(f"csr{'s' if v else 'c'} {z.CSR['vsstatus']:#x}, x6  // vsstatus.SPELP = {v}")
            t.tsbi_csr("CLEAR" if v else "SET", "MSTATUS", imm=z.SPELP)
            t.emit("RVTEST_TSBI_GOTO_VSMODE", 120)
            t.emit("csrr x9, sstatus  // VS-mode: vsstatus")
            t.emit("RVTEST_TSBI_GOTO_SMODE", 120)
            t.emit("srli x9, x9, 23")
            t.emit("andi x9, x9, 1")
            lab = t.label("vsr")
            t.emit(f"{lab}:", 0)
            t.check(
                "x9",
                (1 - v) if alias else v,
                lab,
                f"VS-mode sstatus.SPELP with vsstatus.SPELP={v}, mstatus.SPELP={1 - v}",
            )
        for v in (1, 0):
            t.emit("RVTEST_TSBI_GOTO_VSMODE", 120)
            t.li("x6", z.SPELP)
            t.emit(f"csr{'s' if v else 'c'} sstatus, x6  // VS-mode write")
            t.emit("RVTEST_TSBI_GOTO_SMODE", 120)
            read_vsstatus_spelp(
                t, v if not alias else 1 - v, f"after a VS-mode {'csrs' if v else 'csrc'} of sstatus.SPELP"
            )
        t.tsbi_csr("CLEAR", "MSTATUS", imm=z.SPELP)
        t.li("x6", z.SPELP)
        t.emit(f"csrc {z.CSR['vsstatus']:#x}, x6")
    return t


def m_variant(rule: str, text: str, plan: str, body) -> TestFile:  # noqa: ANN001
    """The M-mode (mseccfg.MLPE=1) part of an unprivileged rule."""
    t = new(rule, sm=True)
    t.describe(
        source=z.UNPRIV,
        rule_text=text,
        context=f"M-mode part (mseccfg.MLPE=1); {rule}.S runs the rule in U, S, VU and VS.",
        plan=plan,
    )
    z.mlpe(t, True)
    body(t)
    z.mlpe(t, False)
    return t


def t_lpad_expected_sm() -> TestFile:
    def body(t: TestFile) -> None:
        for r in (1, 5, 6, 7, 8, 9, 14, 15):
            lp_case(t, "M", J("jalr", 0, r), nonlp(), f"jalr rd=x0 rs1=x{r}")
        for rd, r in ((1, 6), (5, 8), (7, 9), (1, 1), (5, 5)):
            lp_case(t, "M", J("jalr", rd, r), nonlp(), f"jalr rd=x{rd} rs1=x{r}")
        with t.only_if(ZCA):
            for r in (1, 5, 6, 7):
                lp_case(t, "M", J("c.jr", rs1=r), nonlp(), f"c.jr x{r}")
            lp_case(t, "M", J("c.jalr", rs1=8), nonlp(), "c.jalr x8")
            lp_case(t, "M", J("c.j"), nonlp(), "c.j")
        for jj in (J("jal", 1), J("beq"), J("seq")):
            lp_case(t, "M", jj, nonlp(), f"{jj.text()} (not an indirect transfer)")

    return m_variant(
        "Zicfilp_lpad_expected",
        "The zicfilp extension, when enabled, determines if an indirect call or "
        "an indirect jump must land on a landing pad, as specified in IND_CALL_JMP. If is_lp_expected is "
        "1, then the hart updates the elp to LP_EXPECTED.",
        "M-mode: jalr for rs1 in {x1, x5, x6, x7, x8, x9, x14, x15} and several rd, c.jr/c.jalr/c.j (C), "
        "jal, beq and fall-through to a non-lpad: a fault exactly when is_lp_expected.",
        body,
    )


def t_lpad_label_sm() -> TestFile:
    def body(t: TestFile) -> None:
        for L in (1, 0xFFFFF, 0x80000, 0x55555):
            lp_case(t, "M", J("jalr", 0, 6), lp(L), f"label {L:#x} matches", x7=(t.rand(32) << 32) | (L << 12) | 0xABC)
            lp_case(t, "M", J("jalr", 0, 6), lp(L), f"label {L:#x}, x7 bit 12 flipped", x7=((L << 12) ^ 0x1000))
        lp_case(t, "M", J("jalr", 0, 6), lp(0x6B2D1), "label, x7 bit 31 flipped", x7=(0x6B2D1 << 12) ^ (1 << 31))
        rd_x7_case(t, "M", match=True)
        rd_x7_case(t, "M", match=False)

    return m_variant(
        "Zicfilp_lpad_label",
        "To support labeled landing pads, the indirect call/jump sites establish an "
        "expected landing pad label (e.g., using the lui instruction) in the bits 31:12 of the x7 register.",
        "M-mode: labels 1, 0xFFFFF, 0x80000, 0x55555 match x7[31:12] with other bits random; one flipped "
        "label bit (12, 31) faults; jalr x7 to a run-time-built lpad labeled with the link address's bits "
        "31:12 matches, and with bit 12 flipped faults.",
        body,
    )


def t_instr_allowed_sm() -> TestFile:
    def body(t: TestFile) -> None:
        for tg in allowed_targets():
            pre = ["li x9, 0x5A5"] + ([f"LA(x8, {z.data_word(t)})"] if "x8" in tg.lines[0] else [])
            land(
                t,
                "M",
                J("jalr", 0, 6),
                tg,
                "ok" if MUT == "any_insn_ok" else SWCHK,
                f"{tg.note} is not lpad",
                pre=pre,
                pelp=1,
            )
        lp_case(t, "M", J("jalr", 0, 6), lp(0), "lpad 0 is allowed")
        z.mlpe(t, False)
        tg = T([z.lpad(LAB)], f"lpad {LAB:#x}", lp=LAB, check=[("x9", 0x5A5, "x9 unchanged")])
        land(
            t,
            "M",
            J("jalr", 0, 6),
            tg,
            SWCHK if MUT == "disabled_lpad_checks" else "ok",
            "MLPE=0: mismatched lpad is a no-op",
            pre=["li x9, 0x5A5"],
            x7=X(0x1000, 0x1000),
        )

    return m_variant(
        "Zicfilp_lpad_enabled_instr_allowed",
        "When zicfilp is enabled, lpad is the only instruction "
        "allowed to execute when the elp state is LP_EXPECTED. If zicfilp is not enabled then the "
        "instruction is a no-op.",
        "M-mode, MLPE=1: every non-lpad target class of the S-boot file faults with cause 18 without "
        "executing (x9 and memory unchanged); lpad 0 does not. MLPE=0: a mismatched lpad is a no-op.",
        body,
    )


def gen() -> list[TestFile]:
    return [
        t_call_term(),
        t_return_term(),
        t_indirect_jump_term(),
        t_lpad_enc(),
        t_lpad_expected(),
        t_lpad_expected_sm(),
        t_lpad_label_sm(),
        t_instr_allowed_sm(),
        t_indirect_branch_lpad(),
        t_lpad_label(),
        t_lpad_imm_enc(),
        t_elp_lpad_expected(),
        t_lpad_enabled_instr_allowed(),
        t_lpad_enabled_exception(),
        t_lpad_alignment_exception(),
        t_lpad_label_exception(),
        t_lpad_no_sw_exception(),
        t_forward_traps(),
        t_async_interrupt(),
        t_async_exception(),
        t_exception_priority(),
        t_exception_priority_sm(),
        t_lpad_sw_exception(),
        t_lpad_sw_exception_sm(),
        t_pelp_trap(),
        t_pelp_trap_sm(),
        t_mpelp_op_sm(),
        t_spelp_op(),
        t_sstatus_spelp_op(),
        t_pelp_trap_return(),
        t_pelp_trap_return_sm(),
        t_menvcfg_lpe_lead_in(),
        t_menvcfg_lpe_lead_in_sm(),
        t_menvcfg_lpe_list(),
        t_menvcfg_lpe_list_sm(),
        t_senvcfg_lpe(),
        t_henvcfg_lpe(),
        t_mlpe_presence(),
        t_mlpe_set(),
        t_mlpe_clr_lead_in(),
        t_mlpe_clr_list(),
        t_mlpe_rst(),
        t_mstatus_pelp_op(),
        t_mstatus_pelp_op_sm(),
        t_pelp_enc_list(),
        t_pelp_enc_list_sm(),
        t_stval_info(),
        t_mtval_swchk(
            "mtval_swchk_lead_in",
            "On a trap caused by a software-check exception, the mtval register holds the cause for the exception.",
            "A landing-pad fault (non-lpad target) taken into M from M (MLPE=1), and from S and U where implemented "
            "(LPE=1): mtval in {0, 2}.",
            False,
        ),
        t_mtval_swchk(
            "mtval_swchk_list",
            "0 - No information provided. 2 - Landing Pad Fault. Defined by the Zicfilp extension. 3 - Shadow Stack "
            "Fault. Defined by the Zicfiss extension.",
            "M-mode (MLPE=1) landing-pad faults of each kind, non-lpad, mismatched label and (C) misaligned lpad: "
            "mtval in {0, 2}, never 3, and taken by the M handler.",
            True,
        ),
        t_vsstatus_spelp_exists(),
        t_vsstatus_spelp_op(),
        t_sstatus_spelp(),
    ]


def main() -> None:
    for t in gen():
        p = t.write()
        print(f"{p.relative_to(p.parents[2])}: ~{t.ninst} instructions")


if __name__ == "__main__":
    main()
