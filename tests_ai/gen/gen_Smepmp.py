#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate tests_ai/Smepmp: one test per normative rule about Machine Mode Lockdown (mseccfg.MML) and the Smepmp
mseccfg fields.

Rules are in src/priv/smepmp.adoc (the truth table) and src/priv/machine.adoc (mseccfg). The RLB and MMWP rules and
the reset values are in tests_ai/PMP (gen_Sm.py). MML is sticky until reset, so each test is a one-shot file that
first gives the test image locked M-mode rules (gen/epmplib.py). Tests boot to M-mode; S- and U-mode accesses run
in a dedicated code page.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import epmplib as e
from aigen import POOL_TRAP, TestFile

SUITE = "Smepmp"
ISSUE = "https://github.com/riscv/riscv-isa-manual/issues/"
MARCH = "rv${XLEN}i_zicsr_zifencei"
EPMP = "src/priv/smepmp.adoc"
MAC = "src/priv/machine.adoc"
MUT = os.environ.get("AI_MUTANT", "")

MUTANTS = {
    "mml_not_settable": "mseccfg.MML is read-only zero",
    "mml_clearable": "mseccfg.MML can be cleared by a CSR write",
    "nomatch_m_exec": "M-mode may execute from a region without a matching rule when MML=1",
    "l0_m_ignored": "with MML=1, M-mode ignores S/U-mode-only (L=0) rules as with MML=0",
    "mrule_su_enforced": "an M-mode-only rule is enforced (not denied) on S/U-mode accesses",
    "mrule_unlocked": "an M-mode-only rule can be modified with RLB=0",
    "shared0010_su_w": "shared data region LRWX=0010 lets S/U-mode write",
    "shared0011_su_r_only": "shared data region LRWX=0011 gives S/U-mode read-only access",
    "shared_l0_exec": "an L=0 shared data region is executable by M-mode",
    "shared1011_m_no_r": "locked shared code region LRWX=1011 gives M-mode no read access",
    "shared1010_m_r": "locked shared code region LRWX=1010 gives M-mode read access",
    "lrwx1111_m_w": "LRWX=1111 gives M-mode write access",
    "lrwx1111_unlocked": "an LRWX=1111 rule can be modified with RLB=0",
    "x_restrict_ignored": "with MML=1 and RLB=0, an M-mode-only executable rule can be added",
    "x_restrict_l0": "with MML=1, adding an S/U-mode-only executable rule is ignored too",
    "x_restrict_rlb_kept": "RLB=1 does not lift the executable-rule restriction",
    "soru_su_denied": "S/U-mode-only rules deny S/U-mode accesses",
    "mrule_m_x_denied": "M-mode cannot execute from an M-mode-only rule with X",
    "fields_mmwp_set": "setting MML also sets MMWP",
    "truth_0001_m_x": "truth table: LRWX=0001 lets M-mode execute",
    "truth_1100_su_r": "truth table: LRWX=1100 lets S/U-mode read",
}

ISSUE_PMP = (
    "Every test first checks that entries 1-15 are OFF, no entry is locked, mseccfg.MML = MMWP = 0, entry 15 is "
    "implemented, the grain is at most 4 KiB and TOR and NAPOT are supported; otherwise it does nothing."
)
CONTEXT = (
    "The test boots to M-mode (medeleg = 0, MMWP = 0). Before setting MML it gives its own code locked R+X rules "
    "(entries 4 and 6, TOR) and the S/U code page an L=0 R+X rule (entry 2); data has no rule, which M-mode may "
    "read and write by default. Test regions are 4 KiB NAPOT pages of `ret` words; a fetch is a jalr to one, a store "
    "writes the word it holds. Faults are access faults (1 fetch, 5 load, 7 store) with xtval 0 or the address and, "
    "for a fetch, xepc = the target. " + ISSUE_PMP
)


def table() -> dict[tuple[int, int, int, int], tuple[str, str]]:
    """The MML truth table, with the active mutant's error."""
    tb = dict(e.TABLE)

    def mod(code: str, m: str | None = None, su: str | None = None) -> None:
        k = e.lrwx(code)
        tb[k] = (tb[k][0] if m is None else m, tb[k][1] if su is None else su)

    if MUT == "l0_m_ignored":
        for k in list(tb):
            if k[0] == 0 and k[1:3] != (0, 1):
                tb[k] = ("".join(c for c, b in zip("rwx", k[1:]) if b), tb[k][1])
    if MUT == "mrule_su_enforced":
        for code in ("1100", "1101", "1110", "1001"):
            k = e.lrwx(code)
            tb[k] = (tb[k][0], tb[k][0])
    if MUT == "shared0010_su_w":
        mod("0010", su="rw")
    if MUT == "shared0011_su_r_only":
        mod("0011", su="r")
    if MUT == "shared_l0_exec":
        mod("0010", m="rwx")
    if MUT == "shared1011_m_no_r":
        mod("1011", m="x")
    if MUT == "shared1010_m_r":
        mod("1010", m="rx")
    if MUT == "lrwx1111_m_w":
        mod("1111", m="rw")
    if MUT == "soru_su_denied":
        for code in ("0100", "0101", "0110", "0111", "0001"):
            mod(code, su="")
    if MUT == "mrule_m_x_denied":
        mod("1001", m="")
        mod("1101", m="r")
    if MUT == "truth_0001_m_x":
        mod("0001", m="x")
    if MUT == "truth_1100_su_r":
        mod("1100", su="r")
    return tb


def nomatch() -> tuple[str, str]:
    return ("rwx", "") if MUT == "nomatch_m_exec" else e.NOMATCH


def new(rule: str) -> tuple[TestFile, e.Epmp]:
    t = TestFile(SUITE, rule, required=["I", "Sm", "Smepmp"], march=MARCH, boot="M", pool=POOL_TRAP)
    return t, e.Epmp(t)


def check_mseccfg(t: TestFile, mask: int, value: int, desc: str) -> None:
    lab = t.label("msec")
    t.emit(f"{lab}:", 0)
    t.emit(f"csrr x8, {hex(e.MSECCFG)}")
    t.emit(f"andi x8, x8, {mask}")
    t.check("x8", value, lab, desc)


def locked(t: TestFile, p: e.Epmp, page: int, byte: int, desc: str, mutant: bool = False) -> None:
    """The test entry of page P[page] keeps pmpcfg byte `byte` and its pmpaddr after attempts to change them (RLB=0)."""
    ent = e.TEST_ENTRIES[page]
    lab = t.label("lock")
    t.emit(f"csrr x9, {hex(0x3B0 + ent)}  // pmpaddr{ent} before")
    t.emit(f"{lab}:", 0)
    p.write_cfg_byte(ent, 0, "attempt to turn it OFF")
    t.emit(f"csrw {hex(0x3B0 + ent)}, x0  // attempt to move it")
    p.read_cfg("x8", ent)
    t.check("x8", 0 if mutant else byte, lab, f"{desc}: pmpcfg byte unchanged by a write (RLB=0)")
    t.emit(f"csrr x8, {hex(0x3B0 + ent)}")
    t.emit("sub x8, x8, x9")
    t.check("x8", 0, lab, f"{desc}: pmpaddr unchanged by a write (difference)")


def gen() -> list[TestFile]:
    tests = []
    tb = table()

    # ---- mseccfg_fields_exist ----
    t, p = new("mseccfg_fields_exist")
    t.describe(
        source=EPMP,
        rule_text="this extension introduces the RLB, MMWP, and MML fields in the mseccfg CSR and their associated "
        "rules.",
        context=CONTEXT + " RLB may be hardwired to 0 (machine.adoc note: vendors who don't need it may hardwire it). "
        "MMWP is set and checked by mseccfg_mmwp_op_warl (PMP suite): setting it here would need an M-mode data rule.",
        plan="1. mseccfg reads without a trap; MML = MMWP = 0 at the start (checked by the setup).\n"
        "2. Writing RLB=1 before any rule is locked reads back 0 or 1.\n"
        "3. Writing MML=1 reads back 1, and it has its effect: an M-mode fetch from a page with no matching rule "
        "faults, while M-mode loads and stores there still complete.",
    )

    def fields() -> None:
        check_mseccfg(t, e.MML, 0 if MUT == "mml_not_settable" else e.MML, "mseccfg.MML after csrsi")
        p.rlb("x8")
        lab = t.label("rlb")
        t.emit(f"{lab}:", 0)
        t.check("x8", [0, 1], lab, "mseccfg.RLB written 1 reads 0 or 1")
        p.matrix(3, nomatch(), "no matching rule, MML=1", modes=("M",))

    p.setup(fields, require_mml=False)
    p.finish()
    tests.append(t)

    # ---- mseccfg_rlb_mmwp_mml_presence ----
    t, p = new("mseccfg_rlb_mmwp_mml_presence")
    t.describe(
        source=MAC,
        rule_text="The Smepmp extension adds the RLB, MMWP, and the MML fields in mseccfg.",
        context=CONTEXT + " RLB is bit 2, MMWP bit 1 and MML bit 0. Writing one field does not change the others.",
        plan="1. With MML=0: writing RLB=1 leaves MML = MMWP = 0 (RLB reads 0 or 1).\n"
        "2. Writing MML=1 sets bit 0 and leaves MMWP = 0.\n"
        "3. Clearing RLB leaves MML = 1.",
    )

    def presence() -> None:
        check_mseccfg(t, e.MML | e.MMWP, 0, "after writing RLB=1 with MML=0: MML = MMWP = 0")
        t.emit(f"csrsi {hex(e.MSECCFG)}, {e.MML}")
        p.fence()
        t.emit(f"csrr x1, {hex(e.MSECCFG)}")
        t.emit("andi x1, x1, 1")

        def set1() -> None:
            check_mseccfg(t, e.MMWP, e.MMWP if MUT == "fields_mmwp_set" else 0, "MMWP=0 after csrsi MML")
            t.emit(f"csrci {hex(e.MSECCFG)}, {e.RLB}")
            check_mseccfg(t, e.MML | e.RLB, e.MML, "after clearing RLB: MML=1, RLB=0")

        e.either(t, "x1", set1, lambda: t.comment("MML reads 0 (see mseccfg_fields_exist)"))

    p.setup(presence, mml=False, keep_rlb=True)
    p.finish()
    tests.append(t)

    # ---- mseccfg_mml_warl ----
    t, p = new("mseccfg_mml_warl")
    t.describe(
        source=MAC,
        rule_text="The mseccfg.MML (Machine Mode Lockdown) is a WARL field.",
        context=CONTEXT + " Writes to MML must not trap; with Smepmp MML holds 1 once set. The write here is a "
        "csrw of mseccfg as read with bit 0 set (other fields unchanged), not the setup's csrsi.",
        plan="1. csrw of mseccfg with MML=1 completes without a trap.\n"
        "2. When MML reads 1 (mseccfg_fields_exist requires it): a second csrw of the same value and a csrs of MML "
        "complete without a trap, MML still reads 1, and an M-mode fetch from a page with no rule faults.",
    )

    def warl() -> None:
        t.window(
            "M",
            [f"csrr x8, {hex(e.MSECCFG)}", "ori x8, x8, 1", f"csrw {hex(e.MSECCFG)}, x8"],
            "ok",
            "csrw mseccfg with MML=1",
        )
        t.emit(f"csrr x1, {hex(e.MSECCFG)}")
        t.emit("andi x1, x1, 1")

        def kept() -> None:
            t.window(
                "M",
                [f"csrw {hex(e.MSECCFG)}, x8", "li x7, 1", f"csrs {hex(e.MSECCFG)}, x7"],
                "ok",
                "repeated MML writes",
            )
            check_mseccfg(t, e.MML, e.MML, "MML after repeated writes")
            p.access("M", "x", 3, "x" in nomatch()[0], "no matching rule, MML=1")

        e.either(t, "x1", kept, lambda: t.comment("MML reads 0 (see mseccfg_fields_exist)"))

    p.setup(warl, mml=False)
    p.finish()
    tests.append(t)

    # ---- mseccfg_mml_sticky ----
    t, p = new("mseccfg_mml_sticky")
    t.describe(
        source=MAC,
        rule_text="This is a sticky bit, meaning that once set it cannot be unset until a PMP reset.",
        context=CONTEXT,
        plan="1. After MML is set: csrc, csrci, csrrc and csrw with MML=0 (other fields as read) leave MML = 1.\n"
        "2. The lockdown is still in force: an M-mode fetch from a page with no matching rule faults.",
    )

    def sticky() -> None:
        exp = 0 if MUT == "mml_clearable" else e.MML
        t.emit(f"csrci {hex(e.MSECCFG)}, 1")
        check_mseccfg(t, e.MML, exp, "MML after csrci")
        t.emit("li x7, 1")
        t.emit(f"csrc {hex(e.MSECCFG)}, x7")
        check_mseccfg(t, e.MML, exp, "MML after csrc")
        t.emit(f"csrrc x8, {hex(e.MSECCFG)}, x7")
        check_mseccfg(t, e.MML, exp, "MML after csrrc")
        t.emit(f"csrr x8, {hex(e.MSECCFG)}")
        t.emit("andi x8, x8, -2")
        t.emit(f"csrw {hex(e.MSECCFG)}, x8")
        check_mseccfg(t, e.MML, exp, "MML after csrw with MML=0")
        p.access("M", "x", 3, "x" in nomatch()[0], "no matching rule, after attempts to clear MML")

    p.setup(sticky)
    p.finish()
    tests.append(t)

    # ---- mseccfg_mml_set ----
    t, p = new("mseccfg_mml_set")
    t.describe(
        source=MAC,
        rule_text="When mseccfg.MML is set the system's behavior changes in the following way:",
        context=CONTEXT + " The lead-in covers the four changes listed after it (each has its own test); this test "
        "checks that the change happens when MML is set: the same rules behave differently before and after.",
        plan="1. MML=0: page P0 with an L=0 R+W+X rule and P1 with no rule: M-mode loads, stores and fetches "
        "complete in both.\n"
        "2. MML=1: P0 (now S/U-mode-only) denies M-mode every access, and P1 (no rule) denies M-mode fetches but "
        "allows loads and stores.",
    )

    def mml_set() -> None:
        p.rule(0, "0111")
        p.matrix(0, ("rwx", "rwx"), "L=0 RWX rule, MML=0", modes=("M",))
        p.matrix(1, ("rwx", ""), "no rule, MML=0", modes=("M",))
        t.emit(f"csrsi {hex(e.MSECCFG)}, {e.MML}")
        p.fence()
        t.emit(f"csrr x1, {hex(e.MSECCFG)}")
        t.emit("andi x1, x1, 1")

        def after() -> None:
            p.matrix(0, tb[e.lrwx("0111")], "L=0 RWX rule, MML=1", modes=("M",))
            p.matrix(1, nomatch(), "no rule, MML=1", modes=("M",))

        e.either(t, "x1", after, lambda: t.comment("MML reads 0 (see mseccfg_fields_exist)"))

    p.setup(mml_set, mml=False)
    p.finish()
    tests.append(t)

    # ---- mseccfg_mml_pmpcfg_l_op ----
    t, p = new("mseccfg_mml_pmpcfg_l_op")
    t.describe(
        source=MAC,
        rule_text="The meaning of pmpcfg.L changes: Instead of marking a rule as locked and enforced in all modes, "
        "it now marks a rule as M-mode-only when set and S/U-mode-only when unset. The formerly reserved encoding of "
        "pmpcfg.RW=01, and the encoding pmpcfg.LRWX=1111, now encode a Shared-Region.",
        context=CONTEXT + " L=1 rules with X cannot be added once MML is set (mseccfg_mml_x_restrict), so the L=1 "
        "R+W rule is used, which can.",
        plan="1. L=0 R+W+X (P0): M-mode denied every access; S- and U-mode load, store and fetch.\n"
        "2. L=1 R+W (P1): M-mode load and store, no fetch; S/U-mode denied.\n"
        "3. RW=01 (P2: L=0 W) is a shared data region: M-mode read/write, S/U-mode read; LRWX=1111 (P3): read-only "
        "for both.",
    )

    def l_op() -> None:
        for page, code in ((0, "0111"), (1, "1110"), (2, "0010"), (3, "1111")):
            p.rule(page, code)
            p.matrix(page, tb[e.lrwx(code)], f"LRWX={code}")

    p.setup(l_op)
    p.finish()
    tests.append(t)

    # ---- mseccfg_mml_m_rule_op ----
    t, p = new("mseccfg_mml_m_rule_op")
    t.describe(
        source=MAC,
        rule_text="An M-mode-only rule is enforced on accesses whose effective privilege mode is Machine and denied "
        "to accesses whose effective privilege mode is Supervisor or User. It also remains locked so that any "
        "further modifications to its associated configuration or address registers are ignored until a PMP reset, "
        "unless mseccfg.RLB is set.",
        context=CONTEXT + " M-mode-only rules are L=1 except LRWX=1010, 1011 and 1111 (shared). Those with X are "
        "written before MML is set (adding them afterwards is not possible); RLB is 0. The effective privilege "
        "mode of an M-mode access with MPRV=1 is MPP, so such loads count as S/U-mode accesses.",
        plan="1. Before MML: P0 = LRWX 1001, P1 = 1101. After MML: P2 = 1100, P3 = 1110, P4 = 1000.\n"
        "2. M-mode load, store and fetch of each page follow R/W/X; S- and U-mode are denied every access.\n"
        "3. M-mode loads with MPRV=1 and MPP=U (and S) of P1 and P3 fault.\n"
        "4. Writes to the pmpcfg byte and pmpaddr of P0's and P3's entries are ignored.",
    )

    def m_rule() -> None:
        for page, code in ((2, "1100"), (3, "1110"), (4, "1000")):
            p.rule(page, code)
        for page, code in ((0, "1001"), (1, "1101"), (2, "1100"), (3, "1110"), (4, "1000")):
            p.matrix(page, tb[e.lrwx(code)], f"M-mode-only LRWX={code}")
        for page, code in ((1, "1101"), (3, "1110")):
            for mpp, cond in ((0, e.U_OK), (1, e.S_OK)):
                with t.only_if(cond):
                    mprv_load(t, p, page, mpp, "r" in tb[e.lrwx(code)][1], f"M-mode-only LRWX={code}")
        for page, code in ((0, "1001"), (3, "1110")):
            locked(t, p, page, e.cfg_byte(code), f"M-mode-only LRWX={code}", MUT == "mrule_unlocked")

    pre_rules(p, [(0, "1001"), (1, "1101")])
    p.setup(m_rule)
    p.finish()
    tests.append(t)

    # ---- mseccfg_mml_soru_rule_op ----
    t, p = new("mseccfg_mml_soru_rule_op")
    t.describe(
        source=MAC,
        rule_text="An S/U-mode-only rule is enforced on accesses whose effective privilege mode is Supervisor or User "
        "and denied to accesses whose effective privilege mode is Machine.",
        context=CONTEXT + " S/U-mode-only rules are L=0 except the shared encodings 0010 and 0011. The effective "
        "privilege mode of an M-mode access with MPRV=1 is MPP.",
        plan="1. Each of LRWX 0000, 0001, 0100, 0101, 0110, 0111 in turn on P0: S- and U-mode load, store and fetch "
        "follow R/W/X; M-mode is denied every access.\n"
        "2. With LRWX=0110 on P0: an M-mode load and store with MPRV=1, MPP=U (and S) complete.",
    )

    def soru() -> None:
        for code in ("0000", "0001", "0100", "0101", "0110", "0111"):
            p.rule(0, code)
            p.matrix(0, tb[e.lrwx(code)], f"S/U-mode-only LRWX={code}")
        p.rule(0, "0110")
        for mpp, cond in ((0, e.U_OK), (1, e.S_OK)):
            with t.only_if(cond):
                mprv_load(t, p, 0, mpp, "r" in tb[e.lrwx("0110")][1], "S/U-mode-only LRWX=0110")

    p.setup(soru)
    p.finish()
    tests.append(t)

    # ---- mseccfg_mml_shared_rule_op ----
    t, p = new("mseccfg_mml_shared_rule_op")
    t.describe(
        source=MAC,
        rule_text="A Shared-Region rule is enforced on all modes, with restrictions depending on the pmpcfg.L and "
        "pmpcfg.X bits:",
        context=CONTEXT + " The shared encodings are LRWX 0010, 0011, 1010, 1011 and 1111; the L=1 ones with X "
        "need RLB to be added after MML (mseccfg_mml_shared_l1_op). This test checks that a shared rule grants "
        "access to both M-mode and S/U-mode at once (neither is denied).",
        plan="1. LRWX=0011 (P0): M-mode and S/U-mode load and store; nobody fetches.\n"
        "2. LRWX=1111 (P1): M-mode and S/U-mode load; nobody stores or fetches.",
    )

    def shared() -> None:
        for page, code in ((0, "0011"), (1, "1111")):
            p.rule(page, code)
            p.matrix(page, tb[e.lrwx(code)], f"shared LRWX={code}")

    p.setup(shared)
    p.finish()
    tests.append(t)

    # ---- mseccfg_mml_shared_l0_op ----
    t, p = new("mseccfg_mml_shared_l0_op")
    t.describe(
        source=MAC,
        rule_text="A Shared-Region rule where pmpcfg.L is not set can be used for sharing data between M-mode and "
        "S/U-mode, so is not executable. M-mode has read/write access to that region, and S/U-mode has read access "
        "if pmpcfg.X is not set, or read/write access if pmpcfg.X is set.",
        context=CONTEXT,
        plan="1. LRWX=0010 (P0): M-mode load and store; S/U-mode load only; no fetch by anyone.\n"
        "2. LRWX=0011 (P1): M-mode and S/U-mode load and store; no fetch by anyone.\n"
        "3. The rules are not locked: P0's entry is changed to 0011 and then behaves like P1.",
    )

    def shared_l0() -> None:
        for page, code in ((0, "0010"), (1, "0011")):
            p.rule(page, code)
            p.matrix(page, tb[e.lrwx(code)], f"shared LRWX={code}")
        p.rule(0, "0011", "(rewritten)")
        p.matrix(0, tb[e.lrwx("0011")], "shared LRWX=0011 after rewriting 0010")

    p.setup(shared_l0)
    p.finish()
    tests.append(t)

    # ---- mseccfg_mml_shared_l1_op ----
    t, p = new("mseccfg_mml_shared_l1_op")
    t.describe(
        source=MAC,
        rule_text="A Shared-Region rule where pmpcfg.L is set can be used for sharing code between M-mode and "
        "S/U-mode, so is not writable. Both M-mode and S/U-mode have execute access on the region, and M-mode also "
        "has read access if pmpcfg.X is set. The rule remains locked so that any further modifications to its "
        "associated configuration or address registers are ignored until a PMP reset, unless mseccfg.RLB is set.",
        context=CONTEXT + " LRWX=1010 and 1011 are reserved encodings (RW=01) while MML=0, and with MML=1 they "
        "can only be added while RLB=1 (mseccfg_mml_x_restrict). The test runs only when RLB can be set: it keeps "
        "RLB=1 through the setup, adds the rules, then clears RLB.",
        plan="1. RLB=1, MML=1: P0 = LRWX 1010 and P1 = 1011 (each reads back as written).\n"
        "2. RLB=0: P0: M-mode and S/U-mode fetch, nobody loads or stores. P1: M-mode load and fetch, S/U-mode "
        "fetch only, nobody stores.\n"
        "3. Writes to the pmpcfg byte and pmpaddr of both entries are ignored.",
    )

    def shared_l1() -> None:
        p.rlb("x1")

        def with_rlb() -> None:
            for page, code in ((0, "1010"), (1, "1011")):
                p.rule(page, code)
                lab = t.label("rd")
                t.emit(f"{lab}:", 0)
                p.read_cfg("x8", e.TEST_ENTRIES[page])
                t.check("x8", e.cfg_byte(code), lab, f"LRWX={code} added with RLB=1 reads back")
            t.emit(f"csrci {hex(e.MSECCFG)}, {e.RLB}  // RLB = 0")
            for page, code in ((0, "1010"), (1, "1011")):
                p.matrix(page, tb[e.lrwx(code)], f"locked shared LRWX={code}")
                locked(t, p, page, e.cfg_byte(code), f"locked shared LRWX={code}")

        e.either(t, "x1", with_rlb, lambda: t.comment("RLB is hardwired to 0: not tested"))

    p.setup(shared_l1, keep_rlb=True)
    p.finish()
    tests.append(t)

    # ---- mseccfg_mml_shared_lrwx_1111_op ----
    t, p = new("mseccfg_mml_shared_lrwx_1111_op")
    t.describe(
        source=MAC,
        rule_text="The encoding pmpcfg.LRWX=1111 can be used for sharing data between M-mode and S/U mode, where both "
        "modes only have read-only access to the region. The rule remains locked so that any further modifications "
        "to its associated configuration or address registers are ignored until a PMP reset, unless mseccfg.RLB is "
        "set.",
        context=CONTEXT + " The rule has no execute permission, so it can be added after MML is set; RLB is 0.",
        plan="1. LRWX=1111 on P0: M-, S- and U-mode loads complete; stores and fetches fault in every mode.\n"
        "2. Writes to its pmpcfg byte and pmpaddr are ignored.",
    )

    def l1111() -> None:
        p.rule(0, "1111")
        p.matrix(0, tb[e.lrwx("1111")], "LRWX=1111")
        locked(t, p, 0, e.cfg_byte("1111"), "LRWX=1111", MUT == "lrwx1111_unlocked")

    p.setup(l1111)
    p.finish()
    tests.append(t)

    # ---- mseccfg_mml_x_restrict ----
    t, p = new("mseccfg_mml_x_restrict")
    t.describe(
        source=MAC,
        rule_text="Adding a rule with executable privileges that either is M-mode-only or a locked Shared-Region is "
        "not possible and such pmpcfg writes are ignored, leaving pmpcfg unchanged. This restriction can be "
        "temporarily lifted by setting mseccfg.RLB",
        context=CONTEXT + " Each write is one csrw of the entry's pmpcfg register with every other byte as read, so "
        "an implementation that ignores the whole write and one that ignores only the entry's byte agree.",
        plan="1. RLB=0: csrw of an OFF entry's byte to LRWX 1001, 1101, 1010 and 1011 (NAPOT on P0) leaves it OFF, "
        "and P0 is then still a no-match region for M-mode (no fetch).\n"
        "2. Negative: LRWX 0101 (S/U-mode-only with X), 1100 and 1110 (M-mode-only without X) and 1111 (shared "
        "read-only: X set but no execute permission) are added.\n"
        "2b. A rejected write of 1101 over the 0101 rule leaves 0101.\n"
        "3. When RLB can be set (it is kept 1 through the setup): with RLB=1, LRWX 1001 on P2 is added and M-mode "
        "can fetch from it; then RLB is cleared before step 1.",
    )

    def x_restrict() -> None:
        p.rlb("x1")

        def with_rlb() -> None:
            ent = e.TEST_ENTRIES[2]
            p.napot(ent, 2)
            p.write_cfg_byte(ent, e.cfg_byte("1001"))
            lab = t.label("rlb1")
            t.emit(f"{lab}:", 0)
            p.read_cfg("x8", ent)
            t.check("x8", 0 if MUT == "x_restrict_rlb_kept" else e.cfg_byte("1001"), lab, "LRWX=1001 added with RLB=1")
            p.access("M", "x", 2, "x" in tb[e.lrwx("1001")][0], "LRWX=1001 added with RLB=1")

        e.either(t, "x1", with_rlb, lambda: t.comment("RLB is hardwired to 0"))
        t.emit(f"csrci {hex(e.MSECCFG)}, {e.RLB}  // RLB = 0")
        ent = e.TEST_ENTRIES[0]
        p.napot(ent, 0)
        for code in ("1001", "1101", "1010", "1011"):
            p.write_cfg_byte(ent, e.cfg_byte(code), "(must be ignored)")
            lab = t.label("xr")
            t.emit(f"{lab}:", 0)
            p.read_cfg("x8", ent)
            t.check(
                "x8",
                e.cfg_byte(code) if MUT == "x_restrict_ignored" else 0,
                lab,
                f"LRWX={code} not added with MML=1, RLB=0",
            )
        p.access("M", "x", 0, "x" in nomatch()[0], "after the ignored writes")
        for page, code in ((1, "0101"), (3, "1100"), (4, "1111"), (5, "1110")):
            ent = e.TEST_ENTRIES[page]
            p.napot(ent, page)
            p.write_cfg_byte(ent, e.cfg_byte(code))
            lab = t.label("ok")
            t.emit(f"{lab}:", 0)
            p.read_cfg("x8", ent)
            t.check(
                "x8", 0 if MUT == "x_restrict_l0" and code == "0101" else e.cfg_byte(code), lab, f"LRWX={code} is added"
            )

    p.setup(x_restrict, keep_rlb=True)
    p.finish()
    tests.append(t)

    # ---- mseccfg_mml_exec_code ----
    t, p = new("mseccfg_mml_exec_code")
    t.describe(
        source=MAC,
        rule_text="Executing code with Machine mode privileges is only possible from memory regions with a matching "
        "M-mode-only rule or a locked Shared-Region rule with executable privileges. Executing code from a region "
        "without a matching rule or with a matching S/U-mode-only rule is denied.",
        context=CONTEXT + " The test code itself runs from the locked R+X rules. Rules with X for M-mode are written "
        "before MML is set (P0, P1); the shared-code encodings 1010/1011 are in mseccfg_mml_shared_l1_op.",
        plan="1. M-mode fetch from P0 (LRWX 1001) and P1 (1101) completes.\n"
        "2. M-mode fetch faults from P2 (no rule), and from P3 with each S/U-mode-only rule with X (0001, 0101, "
        "0111) and with the shared data rules 0010 and 0011.\n"
        "3. M-mode fetch faults from P4 with M-mode-only rules without X (1100, 1110) and from 1111.",
    )

    def exec_code() -> None:
        for page, code in ((0, "1001"), (1, "1101")):
            p.access("M", "x", page, "x" in tb[e.lrwx(code)][0], f"LRWX={code}")
        p.access("M", "x", 2, "x" in nomatch()[0], "no rule")
        for code in ("0001", "0101", "0111", "0010", "0011"):
            p.rule(3, code)
            p.access("M", "x", 3, "x" in tb[e.lrwx(code)][0], f"LRWX={code}")
        p.set_cfg(e.TEST_ENTRIES[3], 0)
        for page, code in ((4, "1100"), (5, "1110"), (6, "1111")):
            p.rule(page, code)
            p.access("M", "x", page, "x" in tb[e.lrwx(code)][0], f"LRWX={code}")

    pre_rules(p, [(0, "1001"), (1, "1101")])
    p.setup(exec_code)
    p.finish()
    tests.append(t)

    # ---- mml_truth_table ----
    t, p = new("mml_truth_table")
    t.describe(
        source=EPMP,
        rule_text="The physical memory protection rules when mseccfg.MML is set to 1 are summarized in the truth "
        "table below. (16 rows: LRWX -> M-mode and S/U-mode access; see smepmp.adoc.)",
        context=CONTEXT + " L=1 rows lock their entry and the executable L=1 rows can only be added with RLB=1, so "
        "with RLB the whole table is swept on one entry each (RLB=1 lets locked entries be rewritten); without RLB "
        "the L=0 rows are swept on P0 and the non-executable L=1 rows (1000, 1100, 1110, 1111) each get their own "
        "page, and the executable L=1 rows are covered by mseccfg_mml_m_rule_op and mseccfg_mml_exec_code.",
        plan="1. For each row in turn: M-mode, S-mode and U-mode load, store and fetch of the row's page follow the "
        "table.\n"
        "2. A region without a matching rule: M-mode loads and stores only; S/U-mode denied.",
    )
    rows = [f"{i:04b}" for i in range(16)]

    def truth() -> None:
        p.matrix(7, nomatch(), "no matching rule")
        p.rlb("x1")

        def with_rlb() -> None:
            for code in rows:
                p.rule(0, code)
                p.matrix(0, tb[e.lrwx(code)], f"LRWX={code}")
            t.emit(f"csrci {hex(e.MSECCFG)}, {e.RLB}  // RLB = 0")

        def without() -> None:
            for code in rows[:8]:
                p.rule(0, code)
                p.matrix(0, tb[e.lrwx(code)], f"LRWX={code}")
            for page, code in ((1, "1000"), (2, "1100"), (3, "1110"), (4, "1111")):
                p.rule(page, code)
                p.matrix(page, tb[e.lrwx(code)], f"LRWX={code}")

        e.either(t, "x1", with_rlb, without)

    p.setup(truth, keep_rlb=True)
    p.finish()
    tests.append(t)
    return tests


def pre_rules(p: e.Epmp, rules: list[tuple[int, str]]) -> None:
    """Rules written before MML is set (after the image rules)."""
    p.pre = rules


def mprv_load(t: TestFile, p: e.Epmp, page: int, mpp: int, ok: bool, desc: str) -> None:
    """M-mode lw of P[page] with MPRV=1 and MPP=mpp (effective privilege S or U)."""
    p.page("x6", page)
    lab = t.label("mprv")
    t.allow(1)
    t.li("x8", 0x1800)
    t.emit("csrc mstatus, x8")
    if mpp:
        t.li("x8", mpp << 11)
        t.emit("csrs mstatus, x8")
    t.li("x7", 0x20000)
    t.emit("csrs mstatus, x7  // MPRV = 1")
    t.emit(f"{lab}:", 0)
    t.emit("lw x8, 0(x6)")
    t.emit("csrc mstatus, x7  // MPRV = 0")
    t.outcome("ok" if ok else 5, lab, f"M-mode lw of P{page} with MPRV=1, MPP={mpp} ({desc})", origin="M")
    if not ok:
        p.addr_checks("r", f"MPRV load of P{page}")


def main() -> None:
    for t in gen():
        p = t.write()
        print(f"{p.relative_to(Path(__file__).resolve().parents[1])}: ~{t.ninst} instructions")


if __name__ == "__main__":
    main()
