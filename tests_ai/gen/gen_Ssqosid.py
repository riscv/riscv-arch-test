#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate tests_ai/Ssqosid: one test per normative rule about the QoS identifiers extension (srmcfg).

Rules are in src/priv/ssqosid.adoc and, for the mstateen0.SRMCFG gate, src/priv/smstateen.adoc. Tests boot to S-mode
and change mstateen0 through T-SBI; the M-mode part of the access rule is a _Sm file. The framework boots with
mstateen0.SRMCFG = 1 (MSTATEEN0_PRIV114 in rvtest_setup.h).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent))
from aigen import POOL_TRAP, TestFile, X

if TYPE_CHECKING:
    from aigen import Expect

SUITE = "Ssqosid"
ISSUE = "https://github.com/riscv/riscv-isa-manual/issues/"
MARCH = "rv${XLEN}i_zicsr_zifencei"
QOS = "src/priv/ssqosid.adoc"
STATEEN = "src/priv/smstateen.adoc"
H = "defined(H_SUPPORTED)"
U_OK = "defined(U_SUPPORTED)"
STATEEN_OK = "defined(SMSTATEEN_SUPPORTED)"
SRMCFG = 0x181
ILLEGAL, VIRTUAL = 2, 22
FIELDS = 0x0FFF0FFF  # RCID 11:0, MCID 27:16; every other bit is WPRI
SRMCFG_BIT = X(1 << 23, 1 << 55)  # mstateen0h bit 23 (RV32), mstateen0 bit 55 (RV64)
MUT = os.environ.get("AI_MUTANT", "")

MUTANTS = {
    "s_illegal_stateen1": "S-mode access to srmcfg is illegal with mstateen0.SRMCFG=1",
    "u_access_ok": "U-mode may access srmcfg",
    "vs_ok": "VS-mode may access srmcfg with mstateen0.SRMCFG=1",
    "vs_illegal_stateen1": "VS-mode access raises illegal- instead of virtual-instruction with mstateen0.SRMCFG=1",
    "vs_virtual_stateen0": "VS-mode access raises virtual- instead of illegal-instruction with mstateen0.SRMCFG=0",
    "s_ok_stateen0": "S-mode access is permitted with mstateen0.SRMCFG=0",
    "readonly_forms_ok_stateen0": "read-only forms (csrrs x0 / csrrsi 0) do not trap with mstateen0.SRMCFG=0",
    "m_illegal_stateen0": "M-mode access is illegal with mstateen0.SRMCFG=0",
    "wpri_writable": "srmcfg WPRI bits 15:12 read back as written",
    "warl_not_kept": "a legal srmcfg value read back is not kept when written again",
    "stateen_bit_ro0": "mstateen0.SRMCFG is read-only zero",
    "value_lost_on_gate": "clearing mstateen0.SRMCFG clears srmcfg",
    "gate_bit56": "mstateen0 bit 56 (P1P13) also gates srmcfg",
    "trap_writes_srmcfg": "a trapping write still updates srmcfg",
}

# The eight CSR instruction forms: (name, funct3, rs1 or uimm, writes)
FORMS = [
    ("csrrw", 1, 6, True),
    ("csrrs x0", 2, 0, False),
    ("csrrs", 2, 6, True),
    ("csrrc", 3, 6, True),
    ("csrrwi", 5, 21, True),
    ("csrrsi 0", 6, 0, False),
    ("csrrsi", 6, 21, True),
    ("csrrci", 7, 21, True),
]


def enc(f3: int, rd: int, rs1: int, csr: int = SRMCFG) -> int:
    return (csr << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | 0x73


def new(rule: str, required: list[str] | None = None, **kw: object) -> TestFile:
    kw.setdefault("boot", "S")
    kw.setdefault("pool", POOL_TRAP)
    return TestFile(SUITE, rule, required=required or ["I", "S", "Ssqosid"], march=MARCH, **kw)  # type: ignore[arg-type]


def gate(t: TestFile, on: bool) -> None:
    """mstateen0.SRMCFG through T-SBI (mstateen0h on RV32)."""
    t.comment(f"M-mode (T-SBI): mstateen0.SRMCFG = {int(on)}")
    op = "SET" if on else "CLEAR"
    with t.rv64_only():
        t.emit("li a1, 1")
        t.emit("slli a1, a1, 55")
        t.tsbi_csr(op, "MSTATEEN0", "a1")
    with t.rv32_only():
        t.li("a1", 1 << 23)
        t.tsbi_csr(op, "MSTATEEN0H", "a1")


def gate_read(t: TestFile, reg: str) -> None:
    """reg = mstateen0.SRMCFG (T-SBI read)."""
    with t.rv64_only():
        t.tsbi_csr("READ", "MSTATEEN0")
        t.emit(f"srli {reg}, a0, 55")
    with t.rv32_only():
        t.tsbi_csr("READ", "MSTATEEN0H")
        t.emit(f"srli {reg}, a0, 23")
    t.emit(f"andi {reg}, {reg}, 1")


def access(t: TestFile, mode: str, form: tuple[str, int, int, bool], expect: Expect, desc: str) -> str:
    """One srmcfg access of `form` (rd = x8, rs1 = x6 or uimm 21) in `mode` in a trap window. Illegal and
    virtual-instruction traps may write xtval = 0 or the instruction bits."""
    name, f3, rs1, _ = form
    e = enc(f3, 8, rs1)
    alts = expect if isinstance(expect, list) else [expect]
    tval = [0, e] if any(a in (ILLEGAL, VIRTUAL) for a in alts) else None
    trap_only = "ok" not in alts
    if trap_only:
        t.li("x8", 0x77)
    lab = t.window(mode, [f".word {hex(e)}  // {name} x8, srmcfg"], expect, f"srmcfg {name} ({desc})", tval)
    if trap_only:
        t.check("x8", 0x77, lab, f"srmcfg {name} ({desc}) in {mode}-mode: rd unchanged by the trapping instruction")
    return lab


def restore(t: TestFile) -> None:
    t.emit(f"csrw {hex(SRMCFG)}, x0  // srmcfg = 0")


def gen() -> list[TestFile]:
    tests = []
    gate_issue = (
        "The framework boots with mstateen0.SRMCFG = 1 (rvtest_setup.h, MSTATEEN0_PRIV114 is bit 55). srmcfg is an "
        "S-level CSR (0x181), so U-mode access is illegal whatever the gate."
    )

    # ---- Ssqosid_srmcfg_introduced ----
    t = new("Ssqosid_srmcfg_introduced")
    t.describe(
        source=QOS,
        rule_text="To facilitate this, the QoS Identifiers extension (Ssqosid) introduces the srmcfg register, which "
        "configures a hart with two identifiers: a Resource Control ID (RCID) and a Monitoring Counter ID (MCID). "
        "These identifiers accompany each request issued by the hart to shared resource controllers.",
        context=gate_issue + " The identifiers' effect on resource controllers is not visible to the hart.",
        plan="1. In S-mode, every CSR instruction form on srmcfg (0x181) completes without a trap.\n"
        "2. A value written in S-mode is read back unchanged after a U-mode excursion (one register, no per-mode "
        "copy).",
    )
    t.li("x6", 0)
    for form in FORMS:
        access(t, "S", form, "ok", "mstateen0.SRMCFG=1")
    t.li("x6", -1)
    t.emit(f"csrw {hex(SRMCFG)}, x6")
    t.emit(f"csrr x7, {hex(SRMCFG)}")
    with t.only_if(U_OK):
        lab = t.window("U", ["nop"], "ok", "U-mode excursion")
        t.emit(f"csrr x8, {hex(SRMCFG)}")
        t.emit("sub x8, x8, x7")
        t.check("x8", 0, lab, "srmcfg after a U-mode excursion equals the value read before it (difference)")
    restore(t)
    tests.append(t)

    # ---- Ssqosid_srmcfg_register_size ----
    t = new("Ssqosid_srmcfg_register_size")
    t.describe(
        source=QOS,
        rule_text="The srmcfg register is an SXLEN-bit read/write register used to configure a Resource Control ID "
        "(RCID) and a Monitoring Counter ID (MCID). Both RCID and MCID are WARL fields.",
        context="WARL: any value may be written, and a read returns a legal value. Writing back a value just read "
        "(a legal value) keeps it. The supported RCID and MCID widths are implementation choices, so the read "
        "values themselves are not checked; the WPRI bits are checked in srmcfg_enc_img.",
        plan="1. Write all ones, zero, 0x55..., 0xAA... and three random SXLEN-bit values: no trap; read r, write r "
        "back and read r again.\n"
        "2. csrrw returns the previous value, csrrs/csrrc with rs1=x0 do not change it.",
    )
    vals = [X(-1, -1), X(0, 0), X(0x55555555, 0x5555555555555555), X(0xAAAAAAAA, 0xAAAAAAAAAAAAAAAA)]
    vals += [t.rand_x() for _ in range(3)]
    for v in vals:
        lab = t.label("rt")
        t.load("x6", v, "value written")
        t.emit(f"{lab}:", 0)
        t.emit(f"csrw {hex(SRMCFG)}, x6")
        t.emit(f"csrr x7, {hex(SRMCFG)}  // r, a legal value")
        t.emit(f"csrw {hex(SRMCFG)}, x7")
        t.emit(f"csrr x8, {hex(SRMCFG)}")
        t.emit("sub x8, x8, x7")
        t.check(
            "x8",
            1 if MUT == "warl_not_kept" else 0,
            lab,
            f"srmcfg keeps a legal value read back (difference) after writing {v}",
        )
        t.emit(f"csrrw x9, {hex(SRMCFG)}, x0")
        t.emit("sub x9, x9, x7")
        t.check("x9", 0, lab, "csrrw returns the previous value (difference)")
    lab = t.label("ro")
    t.li("x6", -1)
    t.emit(f"csrw {hex(SRMCFG)}, x6")
    t.emit(f"csrr x7, {hex(SRMCFG)}")
    t.emit(f"{lab}:", 0)
    t.emit(f"csrrs x8, {hex(SRMCFG)}, x0")
    t.emit(f"csrrc x8, {hex(SRMCFG)}, x0")
    t.emit(f"csrrsi x8, {hex(SRMCFG)}, 0")
    t.emit(f"csrr x8, {hex(SRMCFG)}")
    t.emit("sub x8, x8, x7")
    t.check("x8", 0, lab, "read-only forms leave srmcfg unchanged (difference)")
    restore(t)
    tests.append(t)

    # ---- srmcfg_enc_img ----
    t = new("srmcfg_enc_img")
    t.describe(
        source=QOS,
        rule_text="Supervisor Resource Management Configuration (srmcfg) register for SXLEN=64: RCID in bits 11:0, "
        "WPRI 15:12, MCID 27:16, WPRI 63:28 (and 31:28 for SXLEN=32).",
        context="WPRI fields not furnished by an implementation are read-only zero (Priv spec, CSR field "
        "specifications), so every bit outside RCID and MCID reads 0 whatever is written.",
        plan="1. After writing all ones, the WPRI pattern (0xF000F000...), 0x55..., 0xAA... and random values, the bits "
        "outside 0x0FFF0FFF read 0.",
    )
    wpri = X(0xF000F000, 0xFFFFFFFFF000F000)
    vals = [X(-1, -1), wpri, X(0x55555555, 0x5555555555555555), X(0xAAAAAAAA, 0xAAAAAAAAAAAAAAAA)]
    vals += [t.rand_x() for _ in range(3)]
    for v in vals:
        lab = t.label("wpri")
        t.load("x6", v, "value written")
        t.emit(f"{lab}:", 0)
        t.emit(f"csrw {hex(SRMCFG)}, x6")
        t.emit(f"csrr x7, {hex(SRMCFG)}")
        mask = (
            X(0x0000F000, 0x000000000000F000)
            if MUT == "wpri_writable"
            else X(~FIELDS & 0xFFFFFFFF, ~FIELDS & ((1 << 64) - 1))
        )
        exp = X(v.num(32) & 0xF000 & 0xFFFFFFFF, v.num(64) & 0xF000) if MUT == "wpri_writable" else 0
        t.check_masked("x7", mask, exp, lab, f"WPRI bits of srmcfg read 0 after writing {v}")
    restore(t)
    tests.append(t)

    # ---- Ssqosid_Smstateen_srmcfg_requires_mstateen0 ----
    t = new("Ssqosid_Smstateen_srmcfg_requires_mstateen0", ["I", "S", "Ssqosid", "Smstateen"])
    t.describe(
        source=QOS,
        rule_text="If extension Smstateen is implemented together with Ssqosid, then Ssqosid also requires the SRMCFG "
        "bit in mstateen0 to be implemented.",
        context="SRMCFG is mstateen0 bit 55 (mstateen0h bit 23 on RV32), reached through T-SBI. Implemented means "
        "writable: it reads back 0 and 1, and its value gates S-mode access to srmcfg.",
        plan="1. mstateen0.SRMCFG reads 1 after boot (the framework sets it).\n"
        "2. Clearing it reads 0 and an S-mode srmcfg read raises illegal-instruction; setting it reads 1 and the "
        "read completes.",
    )
    for i, on in enumerate((True, False, True)):
        lab = t.label("gate")
        t.emit(f"{lab}:", 0)
        if i:
            gate(t, on)
        gate_read(t, "x8")
        exp = 0 if (MUT == "stateen_bit_ro0") else int(on)
        t.check("x8", exp, lab, f"mstateen0.SRMCFG after writing {int(on)}")
        access(t, "S", FORMS[1], "ok" if on else ILLEGAL, f"mstateen0.SRMCFG={int(on)}")
    tests.append(t)

    # ---- Ssqosid_srmcfg_access_illegal_instruction ----
    t = new("Ssqosid_srmcfg_access_illegal_instruction", ["I", "S", "Ssqosid", "Smstateen"])
    t.describe(
        source=QOS,
        rule_text="If mstateen0.SRMCFG is 0, attempts to access srmcfg in privilege modes less privileged than M-mode "
        "raise an illegal-instruction exception.",
        context=gate_issue + " With mstateen0.SRMCFG=0 the illegal-instruction exception also applies to VS and VU "
        "(less privileged than M-mode), where an ungated access would raise virtual-instruction. The M-mode part "
        "is in the _Sm file.",
        plan="1. mstateen0.SRMCFG=0 (T-SBI), srmcfg preset to P (0x0A5A0A5A as legalized), rs1 = ~P: every CSR form (including the "
        "read-only ones) raises illegal-instruction in S-mode, xtval 0 or the instruction.\n"
        "2. A read and a write raise illegal-instruction in U-mode, and every form in VS- and VU-mode (with H).\n"
        "3. After setting the gate again, srmcfg still holds its preset (the trapping writes did not change it).",
    )
    t.li("x6", 0x0A5A0A5A)
    t.emit(f"csrw {hex(SRMCFG)}, x6")
    t.emit(f"csrr x9, {hex(SRMCFG)}  // preset P (a legal value)")
    t.emit("not x6, x9  // rs1 = ~P, so a leaked csrrw, csrrs or csrrc would change srmcfg")
    gate(t, False)
    s_exp = "ok" if MUT == "s_ok_stateen0" else ILLEGAL
    for form in FORMS:
        e: Expect = s_exp
        if MUT == "readonly_forms_ok_stateen0" and not form[3]:
            e = "ok"
        access(t, "S", form, e, "mstateen0.SRMCFG=0")
    with t.only_if(U_OK):
        for form in (FORMS[1], FORMS[0]):
            access(t, "U", form, ILLEGAL, "mstateen0.SRMCFG=0")
    with t.only_if(H):
        for mode in ("VS", "VU"):
            for form in FORMS:
                access(t, mode, form, VIRTUAL if MUT == "vs_virtual_stateen0" else ILLEGAL, "mstateen0.SRMCFG=0")
    gate(t, True)
    lab = t.label("kept")
    t.emit(f"{lab}:", 0)
    t.emit(f"csrr x8, {hex(SRMCFG)}")
    t.emit("sub x8, x8, x9")
    t.check(
        "x8", 1 if MUT == "trap_writes_srmcfg" else 0, lab, "srmcfg unchanged by the trapping accesses (difference)"
    )
    restore(t)
    tests.append(t)

    # ---- Ssqosid_srmcfg_access_illegal_instruction_Sm ----
    t = new(
        "Ssqosid_srmcfg_access_illegal_instruction",
        ["I", "Sm", "S", "Ssqosid", "Smstateen"],
        boot="M",
        suffix="_Sm",
    )
    t.describe(
        source=QOS,
        rule_text="If mstateen0.SRMCFG is 0, attempts to access srmcfg in privilege modes less privileged than M-mode "
        "raise an illegal-instruction exception.",
        context="M-mode part: the gate does not apply to M-mode. mstateen0 is written directly.",
        plan="1. mstateen0.SRMCFG=0: every CSR form on srmcfg completes in M-mode; a written value reads back.\n"
        "2. Restore mstateen0.SRMCFG=1.",
    )
    with t.rv64_only():
        t.emit("li x7, 1")
        t.emit("slli x7, x7, 55")
        t.emit("csrc mstateen0, x7")
    with t.rv32_only():
        t.li("x7", 1 << 23)
        t.emit("csrc 0x31C, x7  // mstateen0h")
    t.li("x6", 0)
    for form in FORMS:
        access(t, "M", form, ILLEGAL if MUT == "m_illegal_stateen0" else "ok", "mstateen0.SRMCFG=0")
    with t.rv64_only():
        t.emit("csrs mstateen0, x7")
    with t.rv32_only():
        t.emit("csrs 0x31C, x7")
    restore(t)
    tests.append(t)

    # ---- Ssqosid_srmcfg_access_virtual_instruction ----
    t = new("Ssqosid_srmcfg_access_virtual_instruction", ["I", "S", "H", "Ssqosid"])
    t.describe(
        source=QOS,
        rule_text="If mstateen0.SRMCFG is 1 or if extension Smstateen is not implemented, attempts to access srmcfg "
        "when V=1 raise a virtual-instruction exception.",
        context=gate_issue + " V=1 covers VS- and VU-mode. HS-mode access is permitted.",
        plan="1. mstateen0.SRMCFG=1 (as booted; set again through T-SBI with Smstateen), srmcfg preset in HS-mode: "
        "every CSR form raises virtual-instruction in VS-mode and in VU-mode, xtval 0 or the instruction.\n"
        "2. HS-mode access completes, and srmcfg still holds its preset.",
    )
    with t.only_if(STATEEN_OK):
        gate(t, True)
    t.li("x6", -1)
    t.emit(f"csrw {hex(SRMCFG)}, x6")
    t.emit(f"csrr x9, {hex(SRMCFG)}  // preset")
    for mode in ("VS", "VU"):
        for form in FORMS:
            e2: Expect = VIRTUAL
            if MUT == "vs_ok" and mode == "VS":
                e2 = "ok"
            if MUT == "vs_illegal_stateen1":
                e2 = ILLEGAL
            access(t, mode, form, e2, "mstateen0.SRMCFG=1")
    access(t, "S", FORMS[1], ILLEGAL if MUT == "s_illegal_stateen1" else "ok", "HS-mode")
    lab = t.label("kept")
    t.emit(f"{lab}:", 0)
    t.emit(f"csrr x8, {hex(SRMCFG)}")
    t.emit("sub x8, x8, x9")
    t.check("x8", 0, lab, "srmcfg unchanged by the trapping accesses (difference)")
    restore(t)
    tests.append(t)

    # ---- mstateen0_srmcfg_op ----
    t = new("mstateen0_srmcfg_op", ["I", "S", "Ssqosid", "Smstateen"])
    t.describe(
        source=STATEEN,
        rule_text="The SRMCFG bit in mstateen0 controls access to the srmcfg CSR introduced by the Ssqosid "
        "<<ssqosid>> extension.",
        context=gate_issue + " The bit controls access only: srmcfg keeps its value while access is off.",
        plan="1. SRMCFG=1: S-mode writes srmcfg (all ones) and reads it back; U-mode access is illegal.\n"
        "2. SRMCFG=0: S-mode read and write raise illegal-instruction.\n"
        "3. SRMCFG=1 again: srmcfg reads the value from step 1.\n"
        "4. Negative: clearing the neighboring bits 54 (CTR) and 56 (P1P13) of mstateen0 (bits 22 and 24 of "
        "mstateen0h on RV32), with SRMCFG=1, leaves S-mode access permitted; they are restored.",
    )
    t.li("x6", -1)
    t.emit(f"csrw {hex(SRMCFG)}, x6")
    t.emit(f"csrr x9, {hex(SRMCFG)}  // value kept across the gate")
    with t.only_if(U_OK):
        access(t, "U", FORMS[1], "ok" if MUT == "u_access_ok" else ILLEGAL, "mstateen0.SRMCFG=1")
    gate(t, False)
    access(t, "S", FORMS[1], ILLEGAL, "mstateen0.SRMCFG=0")
    access(t, "S", FORMS[0], ILLEGAL, "mstateen0.SRMCFG=0")
    gate(t, True)
    lab = t.label("kept")
    t.emit(f"{lab}:", 0)
    t.emit(f"csrr x8, {hex(SRMCFG)}")
    t.emit("sub x8, x8, x9")
    t.check(
        "x8",
        1 if MUT == "value_lost_on_gate" else 0,
        lab,
        "srmcfg after access was turned off and on again (difference)",
    )
    t.comment("negative: neighboring mstateen0 bits do not gate srmcfg")
    with t.rv64_only():
        t.tsbi_csr("READ", "MSTATEEN0")
        t.emit("mv x9, a0")
        t.emit("li a1, 5")
        t.emit("slli a1, a1, 54  // bits 54 and 56")
        t.tsbi_csr("CLEAR", "MSTATEEN0", "a1")
    with t.rv32_only():
        t.tsbi_csr("READ", "MSTATEEN0H")
        t.emit("mv x9, a0")
        t.li("a1", 5 << 22)
        t.tsbi_csr("CLEAR", "MSTATEEN0H", "a1")
    access(t, "S", FORMS[1], ILLEGAL if MUT == "gate_bit56" else "ok", "mstateen0 bits 54 and 56 = 0, SRMCFG=1")
    with t.rv64_only():
        t.tsbi_csr("WRITE", "MSTATEEN0", "x9")
    with t.rv32_only():
        t.tsbi_csr("WRITE", "MSTATEEN0H", "x9")
    restore(t)
    tests.append(t)
    return tests


def main() -> None:
    for t in gen():
        p = t.write()
        print(f"{p.relative_to(Path(__file__).resolve().parents[1])}: ~{t.ninst} instructions")


if __name__ == "__main__":
    main()
