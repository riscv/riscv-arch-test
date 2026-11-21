#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate the state-enable suites: tests_ai/Smstateen and tests_ai/Ssstateen.

One test per norm: rule of src/priv/smstateen.adoc (the srmcfg rules are in the Ssqosid suite). A rule goes
to the suite whose behavior it constrains:

- Ssstateen: what S/HS-mode software sees of sstateen and hstateen, and how they gate U, VS and VU. These tests
  boot to S and never touch mstateen, so they run where M-mode is the execution environment (RVA23). The
  machine-level enables are inferred from an S-mode probe of each piece of state.
- Smstateen: mstateen itself and its gating of S, U, VS and VU (boot to S, mstateen through T-SBI), and the CSR
  structure seen from M-mode (boot to M, requires Sm). When a rule has a part in each suite, the Smstateen file is
  <rule>_Sm.S.

Every expectation is computed at run time from the stateen bits read back (they are WARL: any defined bit may be
read-only zero or one), see smstateenlib.py. The CSIND and CTR stateen rules belong to the Smcsrind/Sscsrind and
Ssctr suites.

mutate.py derives the suite from this file's name, so mutants are named Smstateen:<mutant>; for a mutant run,
SUITE is set to the mutant directory and every test goes there.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent))
import smstateenlib

smstateenlib = importlib.reload(smstateenlib)  # re-read AI_MUTANT (mutate.py reloads this module only)
from aigen import TestFile, X
from smstateenlib import (
    BIT,
    H0_DEF,
    ILLEGAL,
    ISSUE,
    M0_DEF,
    MODES,
    ONES,
    RES,
    RV32,
    RV64,
    S0_DEF,
    SM,
    H,
    Res,
    S,
    bit_op,
    check64_masked,
    check_subset,
    cnum,
    cond,
    defined,
    dyn_window,
    enc_csr,
    load_hs,
    load_m,
    load_word,
    m_write64,
    new,
    probe,
    probe_res,
    read64,
    read_bit,
    restore,
    snap,
    sweep,
    windows,
    word,
    write64,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from contextlib import AbstractContextManager

SUITE = "Smstateen"
MUT = os.environ.get("AI_MUTANT", "")

MUTANTS = {
    # gating (smstateenlib.predict)
    "hs_gated_by_h": "hstateen0 also gates HS-mode access to the state",
    "u_ignores_sstateen": "sstateen0 does not gate U-mode access to user state",
    "u_ignores_mstateen": "mstateen0 does not gate U-mode access once sstateen0 grants it",
    "vs_ignores_hstateen": "hstateen0 does not gate VS-mode access",
    "vs_snov_allowed": "VS-mode may access srmcfg/stopei (VGEIN=0) like other supervisor state when hstateen allows",
    "vu_ignores_sstateen": "sstateen0 does not gate VU-mode access to user state",
    "virtual_as_illegal": "accesses blocked by hstateen/sstateen from VS/VU raise illegal-instruction",
    "m0_virtual": "accesses blocked by mstateen from VS/VU raise virtual-instruction",
    "vu_sstateen_illegal": "a VU access blocked only by sstateen0 raises illegal-instruction",
    # structure
    "rv64_high_csrs_exist": "mstateen0h-3h/hstateen0h-3h exist on RV64",
    "warl_sticky": "a stateen CSR keeps the all-ones value after other values are written",
    "unimpl_bits_writable": "bits for state the hart lacks are writable",
    "reserved_writable": "reserved stateen bits are writable",
    "lower_not_masked": "an hstateen/sstateen bit keeps reading 1 after the mstateen bit is cleared",
    "envcfg_at_61": "the ENVCFG bit of mstateen0 is bit 61",
    "hstateen0_p1p13": "hstateen0 bit 56 (P1P13 in mstateen0, WPRI in hstateen0) is writable",
    "h63_readonly": "hstateen bit 63 is read-only zero",
    "m63_roz_with_h": "mstateen bit 63 reads zero with the hypervisor extension",
    "fcsr_writable_with_f": "mstateen0.FCSR is writable when misa.F=1",
    "m_own_level_gated": "mstateen0 also gates M-mode access",
    "hs_own_level_gated": "hstateen0/sstateen0 also gate HS-mode access",
    "c_bit_grants_all": "mstateen0.C=1 grants access to all state",
    "fcsr_bit_gates_f": "the FCSR bit gates fcsr even when misa.F=1",
    "se0_gates_sstateen1": "mstateen0.SE0 also gates sstateen1-3 and hstateen1-3",
    "envcfg_gates_sstateen0": "mstateen0.ENVCFG also gates sstateen0",
    "ro1_superset": "an sstateen or hstateen bit stays 1 after writing 0 when the mstateen bit is writable",
    "sstateen_upper_writable": "the upper 32 bits of sstateen0 are writable on RV64",
}


def out(suite: str) -> str:
    """The directory a test is written to: its suite, or the mutant directory."""
    return suite if SUITE == "Smstateen" else SUITE


REQ_M = ["I", "Sm", "Smstateen"]  # boot to M
REQ_SM = ["I", "S", "Smstateen"]  # boot to S, mstateen through T-SBI
REQ_SS = ["I", "S", "Ssstateen"]  # boot to S, no mstateen access


def tm(rule: str, suffix: str = "", **kw: object) -> TestFile:
    return new(out("Smstateen"), rule, list(kw.pop("required", REQ_M)), "M", suffix, **kw)  # type: ignore[arg-type]


def ts(rule: str, suffix: str = "", **kw: object) -> TestFile:
    return new(out("Smstateen"), rule, list(kw.pop("required", REQ_SM)), "S", suffix, **kw)  # type: ignore[arg-type]


def tss(rule: str, **kw: object) -> TestFile:
    return new(out("Ssstateen"), rule, list(kw.pop("required", REQ_SS)), "S", **kw)  # type: ignore[arg-type]


ISSUE_1528 = (
    f"{ISSUE}1528: with mstateen0[63]=0 an access to hstateen0 or sstateen0 below M-mode raises illegal-"
    "instruction; with mstateen0[63]=1 and hstateen0[63]=0 a VS-mode access to sstateen0 raises virtual-"
    "instruction (gfavor: the H extension defines when a virtual-instruction exception is taken; ZeyueShen: "
    '"The condition under which a virtual instruction exception can occur is that the register can be accessed '
    'normally in HS mode")."'
)
ISSUE_1512 = (
    f'{ISSUE}1512 (aswaterman): "if the same instruction when executed in HS-mode would have raised an illegal-'
    "instruction exception, it should raise an illegal-instruction in VS-mode. Otherwise, it should raise a "
    'virtual-instruction exception." Tests use CSR reads so read-only CSRs (stopi) never fault for being written.'
)
ISSUE_3459 = (
    f'{ISSUE}3459 (aswaterman): with mstateen0.P1P13=0, hedelegh "simply does not exist ... So the usual HS-'
    'qualified rule applies": an RV32 VS/VU access raises illegal-instruction.'
)
ISSUE_2300 = (
    f"{ISSUE}2300: custom registers are the principal form of custom state; the C bit is recommended for custom "
    "extensions that add state (gfavor, ved-rivos). No standard state is custom, so C must not open it."
)
WARL_NOTE = (
    "Each defined stateen bit is WARL and may be read-only zero or one (stateen_warl_access), and the state it "
    "controls is optional, so every expectation is computed from the bits read back after each write and from an "
    "S-mode probe of the state at the boot configuration (x6 = mstateen bit AND probe, x8 = hstateen bit, x9 = "
    "sstateen bit)."
)
HSQ = (
    "Expected causes (hypervisor.adoc, HS-qualified rule): blocked by mstateen, illegal-instruction in every mode "
    "below M; allowed by mstateen but blocked by hstateen or sstateen, or hypervisor/VS state reached from V=1, "
    "virtual-instruction in VS/VU; U-mode access to supervisor or hypervisor state, illegal-instruction."
)
RULES = {
    "mstateen_rv64_csrs": (
        "For RV64 harts, this extension adds four new 64-bit CSRs at machine level: `mstateen0` (Machine State "
        "Enable 0), `mstateen1`, `mstateen2`, and `mstateen3`."
    ),
    "sstateen_rv64_csrs": (
        "If supervisor mode is implemented, another four CSRs are defined at supervisor level: `sstateen0`, "
        "`sstateen1`, `sstateen2`, and `sstateen3`."
    ),
    "hstateen_rv64_csrs": (
        "And if the hypervisor extension is implemented, another set of CSRs is added: `hstateen0`, `hstateen1`, "
        "`hstateen2`, and `hstateen3`."
    ),
    "stateen_rv32_upper_bits_csrs": (
        "For RV32, there are CSR addresses for accessing the upper 32 bits of corresponding machine-level and "
        "hypervisor CSRs: `mstateen0h`, `mstateen1h`, `mstateen2h`, `mstateen3h`, `hstateen0h`, `hstateen1h`, "
        "`hstateen2h`, and `hstateen3h`."
    ),
    "stateen_op": (
        "The `stateen` registers at each level control access to state at all less-privileged levels, but not at "
        "its own level."
    ),
    "stateen_illegal_state_access": (
        "Just as with the `counteren` CSRs, when a `stateen` CSR prevents access to state by less-privileged levels, "
        "an attempt in one of those privilege modes to execute an instruction that would read or write the "
        "protected state raises an illegal-instruction exception, or, if executing in VS or VU mode and the "
        "circumstances for a virtual-instruction exception apply, raises a virtual-instruction exception instead "
        "of an illegal-instruction exception."
    ),
    "sstateen_user_access_control": (
        "Each bit of a supervisor-level `sstateen` CSR controls user-level access (from U-mode or VU-mode) to an "
        "extension's state."
    ),
    "mstateen_bit_correspondence": (
        "For every bit with a defined purpose in an `sstateen` CSR, the same bit is defined in the matching "
        "`mstateen` CSR to control access below machine level to the same state."
    ),
    "hstateen_encoding": (
        "With the hypervisor extension, the `hstateen` CSRs have identical encodings to the `mstateen` CSRs, except "
        "controlling accesses for a virtual machine (from VS and VU modes)."
    ),
    "stateen_warl_access": (
        "Each standard-defined bit of a `stateen` CSR is WARL and may be read-only zero or one, subject to the "
        "following conditions."
    ),
    "stateen_unimplemented_state_roz": (
        "Bits in any `stateen` CSR that are defined to control state that a hart doesn't implement are read-only "
        "zeros for that hart."
    ),
    "stateen_reserved_roz": "Likewise, all reserved bits not yet given a defined meaning are also read-only zeros.",
    "mstateen_lower_priv_roz": (
        "For every bit in an `mstateen` CSR that is zero (whether read-only zero or set to zero), the same bit "
        "appears as read-only zero in the matching `hstateen` and `sstateen` CSRs."
    ),
    "sstateen_vsmode_access_roz": (
        "For every bit in an `hstateen` CSR that is zero (whether read-only zero or set to zero), the same bit "
        "appears as read-only zero in `sstateen` when accessed in VS-mode."
    ),
    "sstateen_ro1_bits": (
        "A bit in a supervisor-level `sstateen` CSR cannot be read-only one unless the same bit is read-only one in "
        "the matching `mstateen` CSR and, if it exists, in the matching `hstateen` CSR."
    ),
    "hstateen_ro1_bits": (
        "A bit in an `hstateen` CSR cannot be read-only one unless the same bit is read-only one in the matching "
        "`mstateen` CSR."
    ),
    "mstateen_bit_63_op": (
        "For each `mstateen` CSR, bit 63 is defined to control access to the matching `sstateen` and `hstateen` CSRs."
    ),
    "hstateen_bit_63_op": (
        "Likewise, bit 63 of each `hstateen` correspondingly controls access to the matching `sstateen` CSR."
    ),
    "mstateen_bit_63_roz": (
        "Bit 63 of each `mstateen` CSR may be read-only zero only if the hypervisor extension is not implemented "
        "and the matching supervisor-level `sstateen` CSR is all read-only zeros."
    ),
    "hstateen_bit_63_writable": "Bit 63 of each `hstateen` CSR is always writable (not read-only).",
    "mstateen0_enc_img": (
        "Machine State Enable 0 Register (mstateen0): bit 0 C, 1 FCSR, 2 JVT, 3-53 WPRI, 54 CTR, 55 SRMCFG, "
        "56 P1P13, 57 CONTEXT, 58 IMSIC, 59 AIA, 60 CSRIND, 61 WPRI, 62 ENVCFG, 63 SE0."
    ),
    "hstateen0_enc_img": (
        "Hypervisor State Enable 0 Register (hstateen0): bit 0 C, 1 FCSR, 2 JVT, 3-53 WPRI, 54 CTR, 55-56 WPRI, "
        "57 CONTEXT, 58 IMSIC, 59 AIA, 60 CSRIND, 61 WPRI, 62 ENVCFG, 63 SE0."
    ),
    "sstateen0_enc_img": "Supervisor State Enable 0 Register (sstateen0): bit 0 C, 1 FCSR, 2 JVT, 3-31 WPRI.",
    "stateen0_c_op": "The C bit controls access to any and all custom state.",
    "stateen0_fcsr_op": (
        "The FCSR bit controls access to `fcsr` for the case when floating-point instructions operate on `x` "
        "registers instead of `f` registers as specified by the Zfinx and related extensions (Zdinx, etc.)."
    ),
    "mstateen0_fcsr_roz": (
        "Whenever `misa.F` = 1, FCSR bit of `mstateen0` is read-only zero (and hence read-only zero in `hstateen0` "
        "and `sstateen0` too)."
    ),
    "stateen0_fcsr0_misa_f0_illegal_fpu_instr": (
        "For convenience, when the `stateen` CSRs are implemented and `misa.F` = 0, then if the FCSR bit of a "
        "controlling `stateen0` CSR is zero, all floating-point instructions cause an illegal-instruction "
        "exception (or virtual-instruction exception, if relevant), as though they all access `fcsr`, regardless "
        "of whether they really do."
    ),
    "stateen0_jvt_op": "The JVT bit controls access to the `jvt` CSR provided by the Zcmt extension.",
    "mstateen0_se0_op": (
        "The SE0 bit in `mstateen0` controls access to the `hstateen0`, `hstateen0h`, and the `sstateen0` CSRs."
    ),
    "hstateen0_se0_op": "The SE0 bit in `hstateen0` controls access to the `sstateen0` CSR.",
    "mstateen0_envcfg_op": (
        "The ENVCFG bit in `mstateen0` controls access to the `henvcfg`, `henvcfgh`, and the `senvcfg` CSRs."
    ),
    "hstateen0_envcfg_op": "The ENVCFG bit in `hstateen0` controls access to the `senvcfg` CSRs.",
    "mstateen0_imsic_op": (
        "The IMSIC bit in `mstateen0` controls access to the IMSIC state, including CSRs `stopei` and `vstopei`, "
        "provided by the Ssaia extension."
    ),
    "hstateen0_imsic_op": (
        "The IMSIC bit in `hstateen0` controls access to the guest IMSIC state, including CSRs `stopei` (really "
        "`vstopei`), provided by the Ssaia extension."
    ),
    "mstateen0_aia_op": (
        "The AIA bit in `mstateen0` controls access to all state introduced by the Ssaia extension and not "
        "controlled by either the CSRIND or the IMSIC bits."
    ),
    "hstateen0_aia_op": (
        "The AIA bit in `hstateen0` controls access to all state introduced by the Ssaia extension and not "
        "controlled by either the CSRIND or the IMSIC bits of `hstateen0`."
    ),
    "mstateen0_context_op": (
        "The CONTEXT bit in `mstateen0` controls access to the `scontext` and `hcontext` CSRs provided by the "
        "Sdtrig extension."
    ),
    "hstateen0_context_op": (
        "The CONTEXT bit in `hstateen0` controls access to the `scontext` CSR provided by the Sdtrig extension."
    ),
    "mstateen0_p1p13_op": (
        "The P1P13 bit in `mstateen0` controls access to the `hedelegh` introduced by Privileged Specification "
        "Version 1.13."
    ),
}


def describe(t: TestFile, context: str, plan: str, issues: str = "", source: str = SM) -> None:
    t.describe(rule_text=RULES[t.rule], source=source, context=context, issues=issues, plan=plan)


# ---------------------------------------------------------------- shared pieces
def snap_all(t: TestFile, kinds: Sequence[str] = ("m", "h", "s"), ns: Sequence[int] = (0, 1, 2, 3)) -> list:
    """Snapshot the stateen CSRs a test changes (mstateen only in Smstateen tests, hstateen under H)."""
    saved = []
    for kind in kinds:
        for n in ns:
            if kind == "h":
                with t.only_if(H):
                    saved.append((kind, n, snap(t, kind, n), H))
            elif kind == "s":
                with t.only_if(S) if t.cur == "M" else _null():
                    saved.append((kind, n, snap(t, kind, n), S if t.cur == "M" else None))
            else:
                saved.append((kind, n, snap(t, kind, n), None))
    return saved


def restore_all(t: TestFile, saved: list) -> None:
    t.blank()
    for kind, n, lab, c in saved:  # mstateen first, so the lower levels are writable again
        with cond(t, c):
            restore(t, kind, n, lab)


def _null() -> AbstractContextManager[None]:
    import contextlib

    return contextlib.nullcontext()


def op_test(
    t: TestFile,
    names: Sequence[str],
    vary: str,
    smstateen: bool,
    *,
    states: Sequence[int] = (1, 0, 1),
    modes: Sequence[str] = MODES,
    extra: Callable[[int], None] | None = None,
    kinds: Sequence[str] = ("m", "h", "s"),
) -> None:
    saved = snap_all(t, kinds if smstateen else [k for k in kinds if k != "m"])
    bit = None
    for i, nm in enumerate(names):
        r = RES[nm]
        bit = {"m": r.m, "h": r.h, "s": r.s}[vary] or bit  # state without its own bit at this level: the group's
        sweep(t, r, vary, smstateen=smstateen, states=states, modes=modes, extra=extra if i == 0 else None, bit=bit)
    restore_all(t, saved)


def cross(t: TestFile, names: Sequence[str], desc: str) -> Callable[[int], None]:
    """Probe other state now (boot configuration) and return an extra() callback for sweep(): S-mode accesses to
    that state after each state of the sweep, expected per its own (unchanged) mstateen bit."""
    labs = {}
    for nm in names:
        with cond(t, RES[nm].cond):
            labs[nm] = probe_res(t, RES[nm])

    def run(st: int) -> None:
        for nm in names:
            r = RES[nm]
            with cond(t, r.cond):
                load_m(t, r, labs[nm], True)  # only x6: S-mode outcomes do not depend on x8/x9
                if st == 0 and (
                    (MUT == "se0_gates_sstateen1" and nm[1:] in ("stateen1", "stateen2", "stateen3"))
                    or (MUT == "envcfg_gates_sstateen0" and nm == "sstateen0")
                ):
                    t.li("x6", 0)
                line, enc = r.read()
                dyn_window(t, "S", line, enc, r.level, f"{nm} ({desc} written {st}; {nm}'s own bit unchanged)")

    return run


# ---------------------------------------------------------------- per-bit gating tests (boot to S)
def gate_tests() -> list[TestFile]:
    tests = []

    # ---- mstateen0_se0_op ----
    t = ts("mstateen0_se0_op")
    describe(
        t,
        context=f"{WARL_NOTE} {HSQ} hstateen0 and hstateen0h are hypervisor CSRs, so VS/VU accesses with SE0=1 raise "
        "virtual-instruction; sstateen0 is a supervisor CSR that VS-mode may access when hstateen0.SE0=1.",
        issues=ISSUE_1528,
        plan="1. Probe sstateen0, hstateen0 (H) and hstateen0h (RV32 H) from S-mode at the boot configuration.\n"
        "2. For mstateen0.SE0 = 1, 0, 1: read each from S, U, VS and VU; the outcome must match the bits read back.\n"
        "3. Crossing: with SE0 = 0, sstateen1-3, hstateen1-3 (gated by mstateen1-3[63]) and senvcfg (ENVCFG) are "
        "still accessible from S-mode.\n"
        "4. Restore mstateen0-3, hstateen0-3 and sstateen0-3.",
    )
    xr = cross(t, ["senvcfg", "sstateen1", "sstateen2", "sstateen3", "hstateen1", "hstateen2", "hstateen3"], "SE0")
    op_test(t, ["sstateen0", "hstateen0", "hstateen0h"], "m", True, extra=xr)
    tests.append(t)

    # ---- mstateen0_envcfg_op ----
    t = ts("mstateen0_envcfg_op")
    describe(
        t,
        context=f"{WARL_NOTE} {HSQ} senvcfg is a supervisor CSR that VS-mode accesses directly (hstateen0.ENVCFG "
        "gates it); henvcfg/henvcfgh are hypervisor CSRs.",
        issues="QEMU: on RV32 a write to mstateen0 clears mstateen0h.ENVCFG (https://gitlab.com/qemu-project/qemu/-/"
        "issues/4611), which config/qemu/ci.yaml already notes.",
        plan="1. Probe senvcfg, henvcfg (H) and henvcfgh (RV32 H) from S-mode at the boot configuration.\n"
        "2. For mstateen0.ENVCFG = 1, 0, 1: read each from S, U, VS and VU.\n"
        "3. Crossing: with ENVCFG = 0, sstateen0 (SE0) stays accessible from S-mode.\n"
        "4. Restore the stateen CSRs.",
    )
    xr = cross(t, ["sstateen0"], "ENVCFG")
    op_test(t, ["senvcfg", "henvcfg", "henvcfgh"], "m", True, extra=xr)
    tests.append(t)

    simple = [
        (
            "mstateen0_imsic_op",
            ["stopei"],
            (
                "stopei is the S-level IMSIC CSR (Ssaia). From VS-mode it is vstopei, which also needs hstatus.VGEIN "
                "to name a guest interrupt file; the boot leaves VGEIN = 0, so a permitted VS access raises "
                "virtual-instruction."
            ),
        ),
        (
            "mstateen0_aia_op",
            ["stopi", "hvictl"],
            (
                "stopi (VS: vstopi) and hvictl are AIA state outside the CSRIND and IMSIC groups (a read of "
                "read-only stopi never faults for being a write)."
            ),
        ),
        (
            "mstateen0_context_op",
            ["scontext", "hcontext"],
            "scontext and hcontext are optional Sdtrig CSRs; the probe finds out whether they exist.",
        ),
        (
            "mstateen0_p1p13_op",
            ["hedelegh"],
            "hedelegh exists only on RV32 with H, so the file passes trivially elsewhere.",
        ),
    ]
    for rule, names, ctx in simple:
        t = ts(rule)
        issues = ISSUE_1512 if rule == "mstateen0_aia_op" else ISSUE_3459 if rule == "mstateen0_p1p13_op" else ""
        describe(
            t,
            context=f"{ctx} {WARL_NOTE} {HSQ}",
            issues=issues,
            source=SM,
            plan=f"1. Probe {', '.join(names)} from S-mode at the boot configuration; a writable or read-only-one "
            "mstateen0 bit requires the state to exist.\n"
            f"2. For mstateen0[{RES[names[0]].m[1]}] = 1, 0, 1: read each from S, U, VS and VU.\n"
            "3. Restore the stateen CSRs.",
        )
        op_test(t, names, "m", True)
        tests.append(t)

    # ---- mstateen_bit_63_op ----
    t = ts("mstateen_bit_63_op")
    describe(
        t,
        context=f"{WARL_NOTE} {HSQ}",
        issues=ISSUE_1528,
        plan="For each N in 0-3:\n"
        "1. Probe sstateenN, hstateenN (H) and hstateenNh (RV32 H) from S-mode.\n"
        "2. For mstateenN[63] = 1, 0, 1: read each from S, U, VS and VU.\n"
        "3. Restore the stateen CSRs.",
    )
    names = [f"{k}stateen{n}{h}" for n in range(4) for k, h in (("s", ""), ("h", ""), ("h", "h"))]
    op_test(t, names, "m", True)
    tests.append(t)

    # ---- stateen0_jvt_op ----
    t = ts("stateen0_jvt_op")
    describe(
        t,
        context=f"jvt (0x017, Zcmt) is user state, so mstateen0, hstateen0 and sstateen0 all gate it. {WARL_NOTE} "
        f"{HSQ} Without Zcmt the JVT bits are read-only zero and jvt does not exist: every access is illegal.",
        plan="1. Probe jvt from S-mode.\n"
        "2. mstateen0.JVT = 1, 0, 1: read jvt from S, U, VS and VU.\n"
        "3. hstateen0.JVT = 1, 0, 1 (H): the same.\n"
        "4. sstateen0.JVT = 1, 0, 1: the same.\n"
        "5. Restore the stateen CSRs.",
    )
    saved = snap_all(t)
    av = sweep(t, RES["jvt"], "m", smstateen=True)
    sweep(t, RES["jvt"], "h", smstateen=True, avail=av)
    sweep(t, RES["jvt"], "s", smstateen=True, avail=av)
    restore_all(t, saved)
    tests.append(t)

    # ---- hstateen gates (Ssstateen) ----
    hs = [
        ("hstateen0_se0_op", ["sstateen0"], "sstateen0 is a supervisor CSR that VS-mode accesses directly."),
        ("hstateen0_envcfg_op", ["senvcfg"], "senvcfg is a supervisor CSR that VS-mode accesses directly."),
        (
            "hstateen0_aia_op",
            ["stopi", "hvictl"],
            (
                "stopi is vstopi from VS-mode; hvictl is a hypervisor CSR (virtual-instruction from V=1 whatever "
                "hstateen0.AIA is). A read of read-only stopi never faults for being a write."
            ),
        ),
        ("hstateen0_context_op", ["scontext"], "scontext is an optional Sdtrig CSR."),
    ]
    for rule, names, ctx in hs:
        t = tss(rule)
        h0 = RES[names[0]].h
        describe(
            t,
            context=f"{ctx} The machine-level enable is the environment's: an S-mode probe at the boot "
            f"configuration stands for it (x6). {WARL_NOTE} {HSQ}",
            issues=ISSUE_1512 if rule == "hstateen0_aia_op" else "",
            plan=f"1. Probe {', '.join(names)} from S-mode.\n"
            f"2. For hstateen0[{h0[1] if h0 else 59}] = 1, 0, 1: read each from S, U, VS "
            "and VU. HS-mode is never affected.\n"
            "3. Restore hstateen0.",
        )
        with t.only_if(H):
            op_test(t, names, "h", False, kinds=("h",))
        tests.append(t)

    # ---- hstateen0_imsic_op ----
    t = tss("hstateen0_imsic_op")
    describe(
        t,
        context="From VS-mode stopei is vstopei, the guest interrupt file selected by hstatus.VGEIN; with VGEIN not "
        "naming an implemented guest file, VS accesses raise virtual-instruction. VGEIN is WLRL, so it is written 1 "
        "only when hgeie bit 1 is writable (GEILEN >= 1), and read back: when it holds 1, a VS read is permitted "
        "iff hstateen0.IMSIC = 1. "
        f"{WARL_NOTE} {HSQ}",
        plan="1. Probe stopei from S-mode; with GEILEN >= 1 (hgeie bit 1 writable) set hstatus.VGEIN = 1; record "
        "whether VGEIN reads 1.\n"
        "2. For hstateen0.IMSIC = 1, 0, 1: read stopei from S, U, VS and VU.\n"
        "3. Restore hstatus, hgeie and hstateen0.",
    )
    with t.only_if(H):
        vg = word(t, "vgein")
        hs_save = word(t, "hstatus")
        ge_save = word(t, "hgeie")
        t.emit("csrr x7, CSR_HSTATUS")
        t.la("x1", hs_save)
        t.emit("SREG x7, 0(x1)")
        t.emit("csrr x7, CSR_HGEIE")
        t.la("x1", ge_save)
        t.emit("SREG x7, 0(x1)")
        t.comment("GEILEN >= 1 iff hgeie bit 1 is writable; VGEIN (WLRL) is written 1 only then")
        t.li("x7", -1)
        t.emit("csrw CSR_HGEIE, x7")
        t.emit("csrr x7, CSR_HGEIE")
        t.emit("andi x7, x7, 2")
        skip = t.label("nogeilen")
        t.emit(f"beqz x7, {skip}")
        t.li("x7", 1 << 12)
        t.emit("csrs CSR_HSTATUS, x7")
        t.emit(f"{skip}:", 0)
        t.emit("csrr x7, CSR_HSTATUS")
        t.emit("srli x7, x7, 12")
        t.emit("andi x7, x7, 0x3f")
        t.emit("addi x7, x7, -1")
        t.emit("seqz x7, x7")
        t.la("x1", vg)
        t.emit("SREG x7, 0(x1)")
        r = Res("stopei", 0x15C, "S", (0, 58), (0, 58))
        r.vgate = vg  # type: ignore[attr-defined]
        saved = snap_all(t, ("h",), (0,))
        sweep(t, r, "h", smstateen=False)
        restore_all(t, saved)
        t.la("x1", ge_save)
        t.emit("LREG x7, 0(x1)")
        t.emit("csrw CSR_HGEIE, x7")
        t.la("x1", hs_save)
        t.emit("LREG x7, 0(x1)")
        t.emit("csrw CSR_HSTATUS, x7")
    tests.append(t)

    # ---- hstateen_bit_63_op ----
    t = tss("hstateen_bit_63_op")
    describe(
        t,
        context=f"The boot sets hstateen0 only; hstateen1-3 hold whatever they reset to, which the sweep reads back. "
        f"{WARL_NOTE} {HSQ}",
        issues=ISSUE_1528,
        plan="For each N in 0-3:\n"
        "1. Probe sstateenN from S-mode.\n"
        "2. For hstateenN[63] = 1, 0, 1: read sstateenN from S, U, VS and VU.\n"
        "3. Restore hstateen0-3.",
    )
    with t.only_if(H):
        op_test(t, [f"sstateen{n}" for n in range(4)], "h", False, kinds=("h",))
    tests.append(t)

    # ---- sstateen_user_access_control ----
    t = tss("sstateen_user_access_control")
    describe(
        t,
        context="The user state with sstateen0 bits is jvt (Zcmt, JVT) and, without F, fcsr under Zfinx (FCSR). "
        f"Without those extensions the bits are read-only zero and every user access is illegal. {WARL_NOTE} {HSQ}",
        plan="1. Probe jvt (and fcsr without F) from S-mode.\n"
        "2. For sstateen0.JVT (FCSR) = 1, 0, 1: read the CSR from S, U, VS and VU. S and VS are not affected.\n"
        "3. Restore sstateen0.",
    )
    op_test(t, ["jvt", "fcsr"], "s", False, kinds=("s",))
    tests.append(t)

    # ---- mstateen_bit_correspondence ----
    t = ts("mstateen_bit_correspondence")
    describe(
        t,
        context="sstateen0 defines C, FCSR and JVT (bits 0-2); mstateen0 defines the same bits for the same state. "
        f"{WARL_NOTE} {HSQ}",
        plan="1. Write all ones to sstateen0 from S-mode and check it has no bit set that mstateen0 lacks.\n"
        "2. For mstateen0.JVT (and FCSR without F) = 1, 0, 1: read jvt (fcsr) from S, U, VS and VU.\n"
        "3. Restore the stateen CSRs.",
    )
    saved = snap_all(t)
    t.li("x7", -1)
    t.emit("csrw CSR_SSTATEEN0, x7")
    t.emit("csrr x6, CSR_SSTATEEN0")
    read64(t, "m", 0, "x8", "x9")
    lab = t.label("sub")
    t.emit(f"{lab}:", 0)
    t.emit("not x1, x8")
    t.emit("and x1, x1, x6")
    t.emit("seqz x1, x1")
    t.check_bool("x1", lab, "sstateen0 (all ones written) has no bit set that mstateen0 lacks")
    for nm in ("jvt", "fcsr"):
        sweep(t, RES[nm], "m", smstateen=True)
    restore_all(t, saved)
    tests.append(t)

    return tests


# ---------------------------------------------------------------- structure (boot to M unless noted)
KINDS = (("m", None), ("h", H), ("s", S))


def rw_pair(t: TestFile, kind: str, n: int, v1: tuple[str, str], v0: tuple[str, str]) -> None:
    """Write all ones then read into v1, write zero then read into v0 (register pairs; RV64 uses the first)."""
    write64(t, kind, n, ONES)
    read64(t, kind, n, *v1)
    write64(t, kind, n, 0)
    read64(t, kind, n, *v0)


def struct_tests() -> list[TestFile]:
    tests = []

    # ---- mstateen_rv64_csrs ----
    t = tm("mstateen_rv64_csrs")
    describe(
        t,
        context="mstateen0-3 are MRW CSRs 0x30C-0x30F. On RV32 the same addresses hold the low halves. Which bits "
        "are writable is WARL, but a bit that reads 1 after writing 0 is read-only one, so it also reads 1 after "
        "writing all ones. With the hypervisor extension bit 63 cannot be read-only zero (mstateen_bit_63_roz), so "
        "on RV64 it shows that the CSR is 64 bits wide.",
        plan="For each mstateenN (N = 0-3), in M-mode:\n"
        "1. Read it and write the value back (csrrs, csrrw) without a trap.\n"
        "2. Write all ones (v1), then zero (v0): v0 has no bit that v1 lacks; writing all ones again reads v1.\n"
        "3. RV64 with H: bit 63 of v1 is 1.\n"
        "4. Restore the boot values.",
    )
    saved = snap_all(t, ("m",))
    for n in range(4):
        c = cnum("m", n)
        t.window("M", [f"csrrs x1, {hex(c)}, x0  // read mstateen{n}"], "ok", f"read of mstateen{n}")
        t.window("M", [f"csrrw x7, {hex(c)}, x1  // write mstateen{n} back"], "ok", f"write of mstateen{n}")
        rw_pair(t, "m", n, ("x6", "x8"), ("x9", "x7"))
        check_subset(t, ("x9", "x7"), ("x6", "x8"), f"mstateen{n}: bits read 1 after writing 0 also read 1 after ones")
        write64(t, "m", n, ONES)
        read64(t, "m", n, "x9", "x7")
        lab = t.label("same")
        t.emit(f"{lab}:", 0)
        t.emit("xor x1, x9, x6")
        with t.rv32_only():
            t.emit("xor x5, x7, x8")
            t.emit("or x1, x1, x5")
        t.emit("seqz x1, x1")
        t.check_bool("x1", lab, f"mstateen{n}: writing all ones again reads the same value")
        with t.only_if(f"{H} && {RV64}"):
            lab = t.label("b63")
            t.emit(f"{lab}:", 0)
            t.emit("srli x1, x6, 63")
            t.check("x1", 0 if MUT == "m63_roz_with_h" else 1, lab, f"mstateen{n}[63] (all ones written, H)")
    restore_all(t, saved)
    tests.append(t)

    # ---- stateen_rv32_upper_bits_csrs ----
    t = tm("stateen_rv32_upper_bits_csrs")
    describe(
        t,
        context="mstateen0h-3h (0x31C-0x31F) and hstateen0h-3h (0x61C-0x61F) hold bits 63:32 of their CSRs on RV32. "
        "They do not exist on RV64, so accesses there raise illegal-instruction even in M-mode.",
        plan="RV32, for each N in M-mode:\n"
        "1. mstateenNh: read and write without a trap; writing the high half leaves the low half unchanged; v0 "
        "(after writing 0) has no bit that v1 (after writing ones) lacks; with H, bit 31 (SE) of v1 is 1.\n"
        "2. hstateenNh (H, with mstateenN all ones): the same, and only bit 31 can be set for N = 1-3.\n"
        "RV64: reads of mstateen0h-3h and hstateen0h-3h raise illegal-instruction (xtval 0 or the instruction).\n"
        "The boot values are restored.",
    )
    with t.rv32_only():
        saved = snap_all(t, ("m", "h"))
        for kind, c in (("m", None), ("h", H)):
            with cond(t, c):
                for n in range(4):
                    hi, lo = cnum(kind, n, True), cnum(kind, n)
                    nm = f"{kind}stateen{n}h"
                    if kind == "h":
                        write64(t, "m", n, ONES)
                    t.window("M", [f"csrrs x1, {hex(hi)}, x0  // read {nm}"], "ok", f"read of {nm}")
                    t.window("M", [f"csrrw x7, {hex(hi)}, x1  // write {nm} back"], "ok", f"write of {nm}")
                    t.emit(f"csrr x6, {hex(lo)}")
                    t.li("x7", -1)
                    t.emit(f"csrw {hex(hi)}, x7")
                    t.emit(f"csrr x8, {hex(hi)}")
                    t.emit(f"csrw {hex(hi)}, x0")
                    t.emit(f"csrr x9, {hex(hi)}")
                    t.emit(f"csrr x7, {hex(lo)}")
                    lab = t.label("lo")
                    t.emit(f"{lab}:", 0)
                    t.emit("xor x1, x7, x6")
                    t.emit("seqz x1, x1")
                    t.check_bool("x1", lab, f"writing {nm} leaves {kind}stateen{n} unchanged")
                    lab = t.label("sub")
                    t.emit(f"{lab}:", 0)
                    t.emit("not x1, x8")
                    t.emit("and x1, x1, x9")
                    t.emit("seqz x1, x1")
                    t.check_bool("x1", lab, f"{nm}: bits read 1 after writing 0 also read 1 after ones")
                    if n:
                        t.check_masked("x8", 0x7FFFFFFF, 0, lab, f"{nm} (ones written): only bit 31 may be set")
                    with t.only_if(H):
                        t.check_masked("x8", 0x80000000, 0x80000000, lab, f"{nm} bit 31 (SE) is writable with H")
        restore_all(t, saved)
    with t.rv64_only():
        for kind, c in (("m", None), ("h", H)):
            with cond(t, c):
                for n in range(4):
                    hi = cnum(kind, n, True)
                    e = enc_csr(hi, 2, 1, 0)
                    exp = "ok" if MUT == "rv64_high_csrs_exist" else ILLEGAL
                    t.window(
                        "M",
                        [f"csrrs x1, {hex(hi)}, x0  // {kind}stateen{n}h"],
                        exp,
                        f"read of {kind}stateen{n}h on RV64",
                        None if exp == "ok" else [0, e],
                    )
    tests.append(t)

    # ---- stateen_warl_access ----
    t = tm("stateen_warl_access")
    describe(
        t,
        context="WARL with each bit read-only zero, read-only one or writable: after writing all ones (v1) and zero "
        "(v0), a write of any p reads back (p & v1) | v0 (v0 holds the read-only ones and has no bit v1 lacks). "
        "mstateen is written all ones first so hstateen and sstateen bits are not forced to zero "
        "(mstateen_lower_priv_roz). M-mode sees sstateen without hstateen masking.",
        plan="For mstateen0-3, hstateen0-3 (H) and sstateen0-3 (S), in M-mode:\n"
        "1. v1 = value after writing all ones, v0 = value after writing 0; v0 has no bit v1 lacks.\n"
        "2. For three random 64-bit patterns p (RV32: both halves), the value read back is (p & v1) | v0.\n"
        "3. Restore the boot values.",
    )
    saved = snap_all(t)
    for n in range(4):
        write64(t, "m", n, ONES)
    for kind, c in KINDS:
        with cond(t, c):
            if kind != "m":  # the mstateen loop left random patterns there
                for n in range(4):
                    write64(t, "m", n, ONES)
            for n in range(4):
                nm = f"{kind}stateen{n}"
                rw_pair(t, kind, n, ("x6", "x8"), ("x9", "x7"))
                hi = kind != "s"
                check_subset(t, ("x9", "x7"), ("x6", "x8"), f"{nm}: v0 has no bit that v1 lacks", hi)
                for _ in range(3):
                    p = t.rand(64)
                    write64(t, kind, n, p)
                    read64(t, kind, n, "x14", "x15")
                    lab = t.label("warl")
                    t.emit(f"{lab}:", 0)
                    for xlen in (64, 32):
                        with t.only_if(f"__riscv_xlen == {xlen}"):
                            halves = [(0, "x6", "x9", "x14")]
                            if xlen == 32 and hi:
                                halves.append((32, "x8", "x7", "x15"))
                            t.li("x1", 0)
                            for off, r1, r0, rr in halves:
                                pv = (p >> off) & ((1 << xlen) - 1)
                                t.load("x13", pv, f"{nm} pattern bits {off}+")
                                if MUT == "warl_sticky":
                                    t.emit(f"mv x13, {r1}")
                                else:
                                    t.emit(f"and x13, x13, {r1}")
                                    t.emit(f"or x13, x13, {r0}")
                                t.emit(f"xor x13, x13, {rr}")
                                t.emit("or x1, x1, x13")
                    t.emit("seqz x1, x1")
                    t.check_bool("x1", lab, f"{nm}: a written pattern p reads back (p & v1) | v0")
    restore_all(t, saved)
    tests.append(t)

    # ---- stateen_unimplemented_state_roz ----
    t = tm("stateen_unimplemented_state_roz")
    unimpl = {
        "FCSR": "!defined(ZFINX_SUPPORTED)",
        "JVT": "!defined(ZCMT_SUPPORTED)",
        "CTR": "!defined(SMCTR_SUPPORTED) && !defined(SSCTR_SUPPORTED)",
        "SRMCFG": "!defined(SSQOSID_SUPPORTED)",
        "P1P13": f"{RV64} || !defined(H_SUPPORTED)",
        "CONTEXT": "!defined(SDTRIG_SUPPORTED) || !defined(S_SUPPORTED)",
        "IMSIC": "!defined(SSAIA_SUPPORTED)",
        "AIA": "!defined(SSAIA_SUPPORTED)",
        "CSRIND": "!defined(SSCSRIND_SUPPORTED) && !defined(SSAIA_SUPPORTED)",
        "ENVCFG": "!defined(S_SUPPORTED)",
    }
    describe(
        t,
        context="The supported-extension macros say which controlled state is absent: fcsr-in-x-registers (Zfinx), "
        "jvt (Zcmt), CTR state (Smctr/Ssctr), srmcfg (Ssqosid), hedelegh (RV32 with H), scontext/hcontext (Sdtrig "
        "with S), IMSIC and other AIA state (Ssaia), siselect/sireg (Sscsrind), senvcfg/henvcfg and the "
        "senvcfg/henvcfg (S). Bit 63 (SE) is not checked without S: mstateen_bit_63_roz permits read-only zero "
        "there but does not require it, and Sail, Spike and Whisper keep it writable on M+U harts, so the two rules "
        "read as leaving it open (see the README).",
        issues="QEMU makes P1P13 writable on RV64 and on RV32 without H (https://gitlab.com/qemu-project/qemu/-/"
        "work_items/4495), and ENVCFG, CSRIND, AIA and IMSIC writable without S (https://gitlab.com/qemu-project/"
        "qemu/-/work_items/4655); config/qemu/ci.yaml notes both. Imperas let P1P13 be written on RV64 (fixed in "
        "the engineering build).",
        plan="In M-mode, with all ones written to each CSR:\n"
        "1. mstateen0: each bit whose state is absent reads 0.\n"
        "2. hstateen0 (H, mstateen0 all ones): the same for its bits.\n"
        "3. sstateen0 (S): FCSR without Zfinx, JVT without Zcmt.\n"
        "5. Restore the boot values.",
    )
    saved = snap_all(t)
    exp = 1 if MUT == "unimpl_bits_writable" else 0
    for kind, c, bits in (("m", None, M0_DEF), ("h", H, H0_DEF), ("s", S, S0_DEF)):
        with cond(t, c):
            write64(t, "m", 0, ONES)
            write64(t, kind, 0, ONES)
            read64(t, kind, 0, "x6", "x8")
            for name, cc in unimpl.items():
                b = BIT[name]
                if not bits >> b & 1:
                    continue
                with t.only_if(cc):
                    check64_masked(
                        t,
                        "x6",
                        "x8",
                        1 << b,
                        exp << b,
                        f"{kind}stateen0.{name} (bit {b}) reads 0: its state is not implemented",
                        kind != "s",
                    )
    restore_all(t, saved)
    tests.append(t)

    # ---- stateen_reserved_roz, M-mode part ----
    t = tm("stateen_reserved_roz", "_Sm")
    describe(
        t,
        context="Reserved (WPRI) bits: mstateen0 bits 3-53 and 61; hstateen0 bits 3-53, 55, 56 and 61; sstateen0 "
        "bits 3-63; every bit but 63 of mstateen1-3 and hstateen1-3; every bit of sstateen1-3. This file checks "
        "them from M-mode; Ssstateen/stateen_reserved_roz.S checks the S- and VS-mode views.",
        issues="Imperas let hstateen0 bit 56 be written (fixed in the engineering build). QEMU lets sstateen1-3 bit 63 "
        "be written on RV64 (https://gitlab.com/qemu-project/qemu/-/work_items/4726, config/qemu/ci.yaml).",
        plan="In M-mode, with mstateen0-3 all ones:\n"
        "1. Write all ones to every mstateen, hstateen (H) and sstateen (S) CSR; the reserved bits read 0.\n"
        "2. Restore the boot values.",
    )
    saved = snap_all(t)
    for n in range(4):
        write64(t, "m", n, ONES)
    for kind, c in KINDS:
        with cond(t, c):
            for n in range(4):
                if kind != "m":
                    write64(t, kind, n, ONES)
                read64(t, kind, n, "x6", "x8")
                res = ONES & ~defined(kind, n)
                bad = 0
                if MUT == "reserved_writable" and kind == "m" and n == 0:
                    bad = 1 << 61
                if MUT == "hstateen0_p1p13" and kind == "h" and n == 0:
                    bad = 1 << 56
                check64_masked(
                    t, "x6", "x8", res, bad, f"{kind}stateen{n}: reserved bits read 0 (all ones written)", kind != "s"
                )
    restore_all(t, saved)
    tests.append(t)

    # ---- mstateen_lower_priv_roz ----
    t = tm("mstateen_lower_priv_roz")
    describe(
        t,
        context="M-mode reads the hstateen and sstateen CSRs directly. When an mstateen bit is 0, the matching bits "
        "of hstateen and sstateen read 0 and writes of 1 do not stick. When the mstateen bit becomes 1 again, the "
        "lower bit takes an UNSPECIFIED legal value (field modulation), so it is rewritten before it is checked.",
        issues=f"{ISSUE}1636 (field modulation): a write that changes a field's legal values leaves it UNSPECIFIED.",
        plan="For each N: mstateenN = ones; hstateenN (H) and sstateenN (S) = ones, saving h1/s1.\n"
        "1. mstateenN = 0 (reads v0, its read-only ones): hstateenN and sstateenN have no bit outside v0, before "
        "and after writing them all ones again.\n"
        "2. mstateenN = ones, write hstateenN/sstateenN all ones: they read h1/s1 again.\n"
        "3. For N = 0, one bit at a time: clear only mstateen0 bit b; hstateen0 and sstateen0 bit b reads 0 and "
        "their other bits are unchanged.\n"
        "Restore the boot values.",
    )
    saved = snap_all(t)
    for n in range(4):
        write64(t, "m", n, ONES)
        sv = {}
        for kind, c in KINDS[1:]:
            with cond(t, c):
                write64(t, kind, n, ONES)
                sv[kind] = word(t, f"{kind}1")
                read64(t, kind, n, "x6", "x8")
                t.la("x1", sv[kind])
                t.emit("SREG x6, 0(x1)")
                with t.rv32_only():
                    t.emit("SREG x8, 4(x1)")
        write64(t, "m", n, 0)
        read64(t, "m", n, "x9", "x7")
        for kind, c in KINDS[1:]:
            with cond(t, c):
                hi = kind != "s"
                for again in (False, True):
                    if again:
                        write64(t, kind, n, ONES)
                    read64(t, kind, n, "x6", "x8")
                    if MUT == "lower_not_masked":  # expect the all-ones value to persist
                        lab = t.label("mut")
                        t.emit(f"{lab}:", 0)
                        t.la("x1", sv[kind])
                        t.emit("LREG x1, 0(x1)")
                        t.emit("xor x1, x1, x6")
                        t.emit("seqz x1, x1")
                        t.check_bool("x1", lab, "mutant: hstateen/sstateen keeps its value")
                        continue
                    check_subset(
                        t,
                        ("x6", "x8"),
                        ("x9", "x7"),
                        f"{kind}stateen{n} has no bit that mstateen{n} (written 0) lacks"
                        + (" after writing it all ones" if again else ""),
                        hi,
                    )
        write64(t, "m", n, ONES)
        for kind, c in KINDS[1:]:
            with cond(t, c):
                write64(t, kind, n, ONES)
                read64(t, kind, n, "x6", "x8")
                t.la("x1", sv[kind])
                t.emit("LREG x9, 0(x1)")
                with t.rv32_only():
                    t.emit("LREG x7, 4(x1)")
                lab = t.label("again")
                t.emit(f"{lab}:", 0)
                t.emit("xor x1, x6, x9")
                with t.rv32_only():
                    if kind != "s":
                        t.emit("xor x5, x8, x7")
                        t.emit("or x1, x1, x5")
                t.emit("seqz x1, x1")
                t.check_bool(
                    "x1", lab, f"{kind}stateen{n} reads its earlier all-ones value once mstateen{n} is set again"
                )
    # one bit at a time (mstateen0)
    for name, b in BIT.items():
        for kind, c in KINDS[1:]:
            if not defined(kind, 0) >> b & 1:
                continue
            with cond(t, c):
                write64(t, "m", 0, ONES)
                write64(t, kind, 0, ONES)
                read64(t, kind, 0, "x9", "x7")
                bit_op(t, "m", 0, b, False)
                read_bit(t, "m", 0, b, "x13")  # the mstateen bit may be read-only one
                read_bit(t, kind, 0, b, "x14")
                read64(t, kind, 0, "x6", "x8")
                hi = kind != "s"
                lab = t.label("low")
                t.emit(f"{lab}:", 0)
                t.emit("xori x13, x13, 1")
                t.emit("and x14, x14, x13")
                t.emit("seqz x1, x14")
                t.check_bool(
                    "x1", lab, f"{kind}stateen0.{name} reads 0 when mstateen0.{name} reads 0 after being cleared alone"
                )
                lab = t.label("rest")
                t.emit(f"{lab}:", 0)
                with t.rv64_only():
                    t.load("x1", ONES & ~(1 << b), "other bits")
                    t.emit("and x5, x6, x1")
                    t.emit("and x1, x9, x1")
                    t.emit("xor x1, x1, x5")
                with t.rv32_only():
                    m = ONES & ~(1 << b)
                    t.load("x1", m & 0xFFFFFFFF, "other bits")
                    t.emit("and x5, x6, x1")
                    t.emit("and x1, x9, x1")
                    t.emit("xor x1, x1, x5")
                    if hi:
                        t.emit("mv x13, x1")
                        t.load("x1", m >> 32, "other bits")
                        t.emit("and x5, x8, x1")
                        t.emit("and x1, x7, x1")
                        t.emit("xor x1, x1, x5")
                        t.emit("or x1, x1, x13")
                t.emit("seqz x1, x1")
                t.check_bool(
                    "x1", lab, f"{kind}stateen0: bits other than {name} unchanged by clearing mstateen0.{name}"
                )
    restore_all(t, saved)
    tests.append(t)

    # ---- sstateen_ro1_bits / hstateen_ro1_bits ----
    for rule in ("sstateen_ro1_bits", "hstateen_ro1_bits"):
        t = tm(rule)
        lower = "s" if rule.startswith("s") else "h"
        describe(
            t,
            context="A bit is read-only one when it reads 1 after writing 0. mstateenN's read-only ones are read with "
            "mstateenN written 0; the lower CSR's with mstateenN all ones (so no bit is forced to zero) and the "
            "lower CSR written 0.",
            plan="For each N:\n"
            "1. mstateenN = 0: m0 = its value. mstateenN = ones.\n"
            + (
                "2. hstateenN = 0 (H): h0. sstateenN = 0: s0.\n3. s0 has no bit m0 lacks, and (H) none h0 lacks."
                if lower == "s"
                else "2. hstateenN = 0: h0 has no bit that m0 lacks."
            )
            + "\nRestore the boot values.",
        )
        saved = snap_all(t)
        with cond(t, H if lower == "h" else S):
            for n in range(4):
                write64(t, "m", n, 0)
                read64(t, "m", n, "x9", "x7")
                write64(t, "m", n, ONES)
                if lower == "s":
                    with t.only_if(H):
                        write64(t, "h", n, 0)
                        t.emit("// hstateenN = 0 before sstateenN is written")
                    write64(t, "s", n, 0)
                    read64(t, "s", n, "x6", "x8")
                    if MUT == "ro1_superset":
                        t.emit("li x8, 0")
                        lab = t.label("m")
                        t.emit(f"{lab}:", 0)
                        t.check_masked("x6", 1, 1, lab, "mutant: sstateen bit 0 stays 1")
                    check_subset(
                        t,
                        ("x6", "x8"),
                        ("x9", "x7"),
                        f"sstateen{n}'s read-only ones are read-only ones of mstateen{n}",
                        False,
                    )
                    with t.only_if(H):
                        read64(t, "h", n, "x9", "x7")
                        check_subset(
                            t,
                            ("x6", "x8"),
                            ("x9", "x7"),
                            f"sstateen{n}'s read-only ones are read-only ones of hstateen{n}",
                            False,
                        )
                else:
                    write64(t, "h", n, 0)
                    read64(t, "h", n, "x6", "x8")
                    if MUT == "ro1_superset":
                        lab = t.label("m")
                        t.emit(f"{lab}:", 0)
                        with t.rv64_only():
                            t.emit("srli x1, x6, 63")
                        with t.rv32_only():
                            t.emit("srli x1, x8, 31")
                        t.check("x1", 1, lab, "mutant: hstateen bit 63 stays 1")
                    check_subset(
                        t, ("x6", "x8"), ("x9", "x7"), f"hstateen{n}'s read-only ones are read-only ones of mstateen{n}"
                    )
        restore_all(t, saved)
        tests.append(t)

    # ---- mstateen_bit_63_roz ----
    t = tm("mstateen_bit_63_roz")
    describe(
        t,
        context="With H, bit 63 of every mstateen CSR is writable or read-only one. Without H it may be read-only "
        "zero only when the matching sstateen is all read-only zeros (with mstateenN all ones, so no sstateen bit "
        "is forced to zero). Without S there is no sstateen and no constraint.",
        plan="For each N, in M-mode with all ones written to mstateenN:\n"
        "1. H: mstateenN[63] reads 1.\n"
        "2. S without H: mstateenN[63] reads 1, or sstateenN written all ones reads 0.\n"
        "Restore the boot values.",
    )
    saved = snap_all(t)
    for n in range(4):
        write64(t, "m", n, ONES)
        read_bit(t, "m", n, 63, "x6")
        lab = t.label("b63")
        t.emit(f"{lab}:", 0)
        with t.only_if(H):
            t.check("x6", 0 if MUT == "m63_roz_with_h" else 1, lab, f"mstateen{n}[63] with H")
        with t.only_if(f"{S} && !{H}"):
            write64(t, "s", n, ONES)
            t.emit(f"csrr x8, {hex(cnum('s', n))}")
            t.emit("seqz x8, x8")
            t.emit("or x8, x8, x6")
            t.check_bool("x8", lab, f"mstateen{n}[63] is 1, or sstateen{n} is all read-only zero")
    restore_all(t, saved)
    tests.append(t)

    # ---- mstateen0_fcsr_roz ----
    t = tm("mstateen0_fcsr_roz")
    describe(
        t,
        context="misa.F is read at run time (it may be writable). The rule applies whenever misa.F = 1.",
        plan="1. Read misa.F.\n"
        "2. Set the FCSR bit (1) of mstateen0, hstateen0 (H) and sstateen0 (S) with mstateen0 all ones; each reads "
        "0 when misa.F = 1.\n"
        "3. Restore the boot values.",
    )
    saved = snap_all(t, ("m", "h", "s"), (0,))
    t.emit("csrr x9, misa")
    t.emit("srli x9, x9, 5")
    t.emit("andi x9, x9, 1")
    write64(t, "m", 0, ONES)
    for kind, c in KINDS:
        with cond(t, c):
            bit_op(t, kind, 0, 1, True)
            read_bit(t, kind, 0, 1, "x6")
            lab = t.label("fcsr")
            t.emit(f"{lab}:", 0)
            if MUT == "fcsr_writable_with_f":
                t.emit("xor x1, x6, x9")
            else:
                t.emit("and x1, x6, x9")
            t.emit("seqz x1, x1")
            t.check_bool("x1", lab, f"{kind}stateen0.FCSR reads 0 when misa.F = 1")
    restore_all(t, saved)
    tests.append(t)

    # ---- stateen0_fcsr0_misa_f0_illegal_fpu_instr ----
    t = tm("stateen0_fcsr0_misa_f0_illegal_fpu_instr")
    fp = [
        (0x003100D3, "fadd.s x1/f1, x2/f2, x3/f3 (reads frm, writes fflags)"),
        (0x203100D3, "fsgnj.s x1/f1, x2/f2, x3/f3 (touches no fcsr field)"),
        (enc_csr(0x003, 2, 1, 0), "csrr x1, fcsr"),
    ]
    describe(
        t,
        context="The rule applies only when misa.F = 0. The test tries to clear misa.F (with D, Q and V, which "
        "depend on it); misa is WARL, so where F stays 1 nothing more is checked. With misa.F = 0, a "
        "floating-point instruction runs on x registers (Zfinx) or is not implemented; either way it must raise "
        "illegal-instruction when the controlling FCSR bit is 0 (mstateen0 for S and U, sstateen0 too for U), even "
        "one that does not touch fcsr. With the bit 1 under Zfinx it executes.",
        plan="1. Save misa; clear misa.F, D, Q and V; read misa.F back.\n"
        "2. If misa.F = 0: for (mstateen0.FCSR, sstateen0.FCSR) = (0, 1), (1, 1) and, in U-mode, (1, 0) (bits read "
        "back), execute fadd.s, fsgnj.s and a read of fcsr in S-mode and U-mode; the outcome follows the FCSR bits "
        "(x6 = mstateen0, x9 = sstateen0). VS/VU (hstateen0.FCSR, virtual-instruction) cannot be entered from this "
        "M-mode test; stateen0_fcsr_op covers them for fcsr.\n"
        "3. Restore misa, mstateen0 and sstateen0.",
    )
    saved = snap_all(t, ("m", "s"), (0,))
    ms = word(t, "misa")
    t.emit("csrr x7, misa")
    t.la("x1", ms)
    t.emit("SREG x7, 0(x1)")
    t.li("x7", (1 << 5) | (1 << 3) | (1 << 16) | (1 << 21))
    t.emit("csrc misa, x7")
    fl = word(t, "misaF")
    t.emit("csrr x8, misa")
    t.emit("srli x8, x8, 5")
    t.emit("andi x8, x8, 1")
    t.la("x1", fl)
    t.emit("SREG x8, 0(x1)")

    def f_off(mode: str) -> None:
        for mst, sst in ((0, 1), (1, 1), (1, 0)):
            if mode == "S" and sst == 0:
                continue  # sstateen0 controls U only
            bit_op(t, "m", 0, 1, bool(mst))
            read_bit(t, "m", 0, 1, "x6")
            t.li("x9", 1)
            with t.only_if(S):
                bit_op(t, "s", 0, 1, bool(sst))
                read_bit(t, "s", 0, 1, "x9")
            t.li("x8", 1)
            for e, note in fp:
                dyn_window(
                    t,
                    mode,
                    f".word {hex(e)}  // {note}",
                    e,
                    "U",
                    f"{note} with misa.F=0, mstateen0.FCSR written {mst}, sstateen0.FCSR written {sst}",
                )

    for mode in ("S", "U"):
        with cond(t, S if mode == "S" else None):
            load_word(t, "x7", fl)
            t.either("x7", lambda: None, lambda mode=mode: f_off(mode))
    t.la("x1", ms)
    t.emit("LREG x7, 0(x1)")
    t.emit("csrw misa, x7")
    restore_all(t, saved)
    tests.append(t)

    # ---- stateen_op, M-mode part ----
    t = tm("stateen_op", "_Sm")
    describe(
        t,
        context="mstateen controls only modes below M. This file checks that clearing all of mstateen0-3 does not "
        "change any M-mode access to the controlled state; Ssstateen/stateen_op.S checks the same for hstateen and "
        "sstateen at HS-mode.",
        plan="1. With the boot mstateen values, read each controlled CSR in M-mode and record whether it trapped "
        "(the state is optional).\n"
        "2. Write 0 to mstateen0-3 and read each again: the outcome is unchanged.\n"
        "3. Restore mstateen0-3.",
    )
    names = [n for n in RES if RES[n].insn is None and n not in ("fcsr",)]
    labs = {}
    for nm in names:
        with cond(t, RES[nm].cond):
            line, e = RES[nm].read()
            labs[nm] = probe(t, "M", line, e, f"{nm} in M-mode with the boot mstateen values")
    saved = snap_all(t, ("m",))
    for n in range(4):
        write64(t, "m", n, 0)
    for nm in names:
        r = RES[nm]
        with cond(t, r.cond):
            load_word(t, "x6", labs[nm])
            if MUT == "m_own_level_gated":
                t.li("x6", 0)
            line, e = r.read()
            dyn_window(
                t, "M", line, e, r.level, f"{nm} in M-mode with mstateen0-3 = 0 (same outcome as with the boot values)"
            )
    restore_all(t, saved)
    tests.append(t)

    return tests


def s_window(t: TestFile, line: str, e: int, desc: str) -> None:
    """An S-mode access to a stateen CSR: no trap with Smstateen (the boot enables it), else no trap or
    illegal-instruction (the environment decides)."""
    with t.only_if("defined(SMSTATEEN_SUPPORTED)"):
        t.window("S", [line], "ok", desc)
    with t.only_if("!defined(SMSTATEEN_SUPPORTED)"):
        t.window("S", [line], ["ok", ILLEGAL], desc, [0, e])


def vsmask(t: TestFile) -> None:
    """sstateen_vsmode_access_roz body: VS-mode view of sstateen0 with hstateen0 bits 0-2 cleared, then set."""
    bit_op(t, "h", 0, 63, True)
    for on in (False, True):
        t.li("x7", 7)
        t.emit(f"{'csrs' if on else 'csrc'} CSR_HSTATEEN0, x7")
        t.li("x7", -1)
        t.emit("csrw CSR_SSTATEEN0, x7")
        t.emit("csrr x8, CSR_SSTATEEN0")  # s
        t.emit("csrr x9, CSR_HSTATEEN0")  # h (low bits)
        t.enter("VS")
        t.emit("csrr x6, CSR_SSTATEEN0")
        t.emit("csrw CSR_SSTATEEN0, x0")
        t.leave()
        lab = t.label("vs")
        t.emit(f"{lab}:", 0)
        t.emit("not x1, x9")
        t.emit("and x1, x1, x6")
        t.emit("seqz x1, x1")
        t.check_bool(
            "x1", lab, f"VS-mode sstateen0 has no bit hstateen0 lacks (hstateen0[2:0] {'set' if on else 'clear'})"
        )
        t.emit("csrr x7, CSR_SSTATEEN0")
        t.emit("not x1, x9")
        t.emit("and x7, x7, x1")
        t.emit("and x1, x8, x1")
        t.emit("xor x1, x1, x7")
        t.emit("seqz x1, x1")
        t.check_bool("x1", lab, "a VS write leaves the sstateen0 bits that hstateen0 masks unchanged")


# ---------------------------------------------------------------- remaining rules (boot to S)
def more_tests() -> list[TestFile]:
    tests = []
    vs_res = ["senvcfg", "sstateen0", "siselect", "stopi", "scontext", "sctrctl", "jvt"]

    # ---- stateen_illegal_state_access ----
    t = ts("stateen_illegal_state_access")
    forms = [
        ("csrrs x1, {c}, x0", 2, 1, 0, "read (csrrs rs1=x0)"),
        ("csrrw x0, {c}, x7", 1, 0, 7, "write (csrrw rd=x0)"),
        ("csrrw x1, {c}, x7", 1, 1, 7, "swap (csrrw)"),
        ("csrrs x1, {c}, x7", 2, 1, 7, "set (csrrs rs1!=x0)"),
        ("csrrc x1, {c}, x7", 3, 1, 7, "clear (csrrc rs1!=x0)"),
        ("csrrwi x1, {c}, 0", 5, 1, 0, "write immediate (csrrwi)"),
        ("csrrsi x1, {c}, 0", 6, 1, 0, "read (csrrsi uimm=0)"),
        ("csrrci x1, {c}, 0x15", 7, 1, 0x15, "clear immediate (csrrci uimm!=0)"),
    ]
    describe(
        t,
        context="senvcfg is the representative state: it exists on every hart with S-mode (Priv 1.12+) and is gated "
        "by mstateen0.ENVCFG and, from VS-mode, hstateen0.ENVCFG. Every CSR instruction form is tried, because "
        "reads and writes are both protected. Register forms write x7 = 0. "
        f"{WARL_NOTE} {HSQ}",
        issues=ISSUE_1528,
        plan="1. Probe senvcfg from S-mode; save senvcfg.\n"
        "2. mstateen0.ENVCFG = 0: all eight forms from S, U, VS and VU (illegal-instruction).\n"
        "3. mstateen0.ENVCFG = 1, hstateen0.ENVCFG = 0 (H): all eight forms from S (no trap), U (illegal), VS and VU "
        "(virtual-instruction).\n"
        "4. hstateen0.ENVCFG = 1: all eight forms from VS (no trap) and VU (virtual-instruction).\n"
        "5. henvcfg (H): mstateen0.ENVCFG = 0, 1, read from S, U, VS, VU (VS/VU: illegal, then virtual).\n"
        "6. jvt (and fcsr without F): sstateen0 bit = 0, 1, read from U (illegal) and VU (virtual) when the state "
        "exists.\n"
        "Each trap leaves xtval 0 or the instruction bits. Restore senvcfg and the stateen CSRs.",
    )
    r = RES["senvcfg"]
    saved = snap_all(t, ("m", "h", "s"), (0,))
    sv = word(t, "senvcfg")
    t.emit("csrr x7, CSR_SENVCFG")
    t.la("x1", sv)
    t.emit("SREG x7, 0(x1)")
    av = probe_res(t, r)

    def all_forms(modes: Sequence[str], desc: str) -> None:
        for asm, f3, rd, rs1, kind in forms:
            e = enc_csr(0x10A, f3, rd, rs1)
            for mode in modes:
                with cond(t, H if mode in ("VS", "VU") else None):
                    dyn_window(
                        t,
                        mode,
                        asm.format(c="0x10a") + "  // senvcfg",
                        e,
                        "S",
                        f"{kind} of senvcfg ({desc})",
                        pre=["li x7, 0"],
                    )

    load_hs(t, r)
    bit_op(t, "m", 0, 62, False)
    load_m(t, r, av, True)
    all_forms(MODES, "mstateen0.ENVCFG written 0")
    bit_op(t, "m", 0, 62, True)
    load_m(t, r, av, True)
    with t.only_if(H):
        bit_op(t, "h", 0, 62, False)
    load_hs(t, r)
    all_forms(MODES, "mstateen0.ENVCFG written 1, hstateen0.ENVCFG written 0")
    with t.only_if(H):
        bit_op(t, "h", 0, 62, True)
        load_hs(t, r)
        all_forms(("VS", "VU"), "mstateen0.ENVCFG and hstateen0.ENVCFG written 1")
    t.comment("hypervisor state (henvcfg) and user state blocked by sstateen0 (jvt, and fcsr without F)")
    sweep(t, RES["henvcfg"], "m", smstateen=True, states=(0, 1))
    for nm in ("jvt", "fcsr"):
        sweep(t, RES[nm], "s", smstateen=True, states=(0, 1), modes=("U", "VU"))
    restore_all(t, saved)
    t.la("x1", sv)
    t.emit("LREG x7, 0(x1)")
    t.emit("csrw CSR_SENVCFG, x7")
    tests.append(t)

    # ---- mstateen0_enc_img ----
    t = ts("mstateen0_enc_img")
    order = ["SE0", "ENVCFG", "CSRIND", "AIA", "IMSIC", "CONTEXT", "P1P13", "SRMCFG", "CTR", "JVT", "FCSR", "C"]
    xres = [
        "sstateen0",
        "senvcfg",
        "henvcfg",
        "siselect",
        "stopi",
        "stopei",
        "scontext",
        "hedelegh",
        "srmcfg",
        "sctrctl",
        "jvt",
    ]
    describe(
        t,
        context="Checks the layout two ways. Reserved positions (3-53, 61) read 0 after mstateen0 is written all "
        "ones. Each defined position controls its own state and nothing else: clearing one bit blocks S-mode access "
        "to that bit's state only (sstateen0 SE0, senvcfg/henvcfg ENVCFG, siselect CSRIND, stopi AIA, stopei IMSIC, "
        "scontext CONTEXT, hedelegh P1P13, srmcfg SRMCFG, sctrctl CTR, jvt JVT). Optional state is probed first. "
        + WARL_NOTE,
        plan="1. mstateen0 = all ones (T-SBI): bits 3-53 and 61 read 0. Restore.\n"
        "2. Probe each state's S-mode access at the boot configuration.\n"
        "3. For each defined bit, clear only that bit, read it back, and access every state from S-mode: only the "
        "state of the cleared bit may change (to illegal-instruction, when the bit really cleared); then set it "
        "again.\n"
        "4. Restore mstateen0.",
    )
    saved = snap_all(t, ("m",), (0,))
    m_write64(t, 0, ONES)
    read64(t, "m", 0, "x6", "x8")
    check64_masked(t, "x6", "x8", ONES & ~M0_DEF, 0, "mstateen0 reserved bits read 0 (all ones written)")
    restore_all(t, saved)
    labs = {}
    for nm in xres:
        with cond(t, RES[nm].cond):
            labs[nm] = probe_res(t, RES[nm])
    for bn in order:
        b = BIT[bn]
        if MUT == "envcfg_at_61" and bn == "ENVCFG":
            b = 61
        bit_op(t, "m", 0, b, False)
        read_bit(t, "m", 0, b, "x9")
        for nm in xres:
            rr = RES[nm]
            with cond(t, rr.cond):
                load_word(t, "x6", labs[nm])
                if rr.m[1] == BIT[bn]:
                    t.emit("and x6, x6, x9")
                line, e = rr.read()
                dyn_window(t, "S", line, e, rr.level, f"{nm} with only mstateen0.{bn} (bit {b}) cleared")
        bit_op(t, "m", 0, b, True)
    restore_all(t, saved)
    tests.append(t)

    # ---- hstateen0_enc_img ----
    t = tss("hstateen0_enc_img")
    horder = ["SE0", "ENVCFG", "CSRIND", "AIA", "CONTEXT", "CTR", "JVT", "FCSR", "C"]
    describe(
        t,
        context="Reserved positions of hstateen0 (3-53, 55, 56, 61) read 0 after it is written all ones from HS-mode, "
        "and each defined position controls only its own state from VS-mode: sstateen0 SE0, senvcfg ENVCFG, "
        "siselect (vsiselect) CSRIND, stopi (vstopi) AIA, scontext CONTEXT, sctrctl (vsctrctl) CTR, jvt JVT. The "
        "IMSIC bit is covered by hstateen0_imsic_op. " + WARL_NOTE,
        issues="Imperas let hstateen0 bit 56 be written (fixed in the engineering build).",
        plan="1. hstateen0 = all ones: the reserved bits read 0 and bit 63 reads 1. Restore.\n"
        "2. Probe each state's S-mode access.\n"
        "3. For each defined bit: clear only that bit and access every state from VS-mode (x8 is each state's "
        "hstateen0 bit read back, x9 its sstateen0 bit): only the cleared bit's state may change, to "
        "virtual-instruction; then set the bit again.\n"
        "4. Restore hstateen0.",
    )
    with t.only_if(H):
        saved = snap_all(t, ("h",), (0,))
        write64(t, "h", 0, ONES)
        read64(t, "h", 0, "x6", "x8")
        bad = (1 << 56) if MUT == "hstateen0_p1p13" else 0
        check64_masked(t, "x6", "x8", ONES & ~H0_DEF, bad, "hstateen0 reserved bits read 0 (all ones written)")
        check64_masked(t, "x6", "x8", 1 << 63, 0 if MUT == "h63_readonly" else 1 << 63, "hstateen0[63] reads 1")
        restore_all(t, saved)
        labs = {}
        for nm in vs_res:
            labs[nm] = probe_res(t, RES[nm])
        for bn in horder:
            b = BIT[bn]
            bit_op(t, "h", 0, b, False)
            for nm in vs_res:
                rr = RES[nm]
                load_word(t, "x6", labs[nm])
                load_hs(t, rr)
                line, e = rr.read()
                dyn_window(t, "VS", line, e, rr.level, f"{nm} with only hstateen0.{bn} (bit {b}) cleared")
            bit_op(t, "h", 0, b, True)
        restore_all(t, saved)
    tests.append(t)

    # ---- sstateen0_enc_img ----
    t = tss("sstateen0_enc_img")
    describe(
        t,
        context="sstateen0 defines bits 0-2 (C, FCSR, JVT); bits 3-31 and, on RV64, 32-63 are reserved. JVT gates "
        "jvt (Zcmt) and FCSR gates fcsr only without F (Zfinx); each must not gate the other. " + WARL_NOTE,
        plan="1. sstateen0 = all ones from S-mode: bits 3 and up read 0. Restore.\n"
        "2. Probe jvt (and fcsr without F) from S-mode.\n"
        "3. For each defined bit: clear only it, read jvt (fcsr) from U-mode, then set it again.\n"
        "4. Restore sstateen0.",
    )
    saved = snap_all(t, ("s",), (0,))
    t.li("x7", -1)
    t.emit("csrw CSR_SSTATEEN0, x7")
    t.emit("csrr x6, CSR_SSTATEEN0")
    lab = t.label("res")
    t.emit(f"{lab}:", 0)
    up = X(0xFFFFFFF8, ONES & ~7)
    t.check_masked(
        "x6",
        up,
        X(0, 1 << 32) if MUT == "sstateen_upper_writable" else 0,
        lab,
        "sstateen0 reserved bits read 0 (all ones written)",
    )
    restore_all(t, saved)
    labs = {}
    for nm in ("jvt", "fcsr"):
        with cond(t, RES[nm].cond):
            labs[nm] = probe_res(t, RES[nm])
    for bn in ("JVT", "FCSR", "C"):
        bit_op(t, "s", 0, BIT[bn], False)
        for nm in ("jvt", "fcsr"):
            rr = RES[nm]
            with cond(t, rr.cond):
                load_word(t, "x6", labs[nm])
                load_hs(t, rr)
                line, e = rr.read()
                dyn_window(t, "U", line, e, rr.level, f"{nm} with only sstateen0.{bn} cleared")
        bit_op(t, "s", 0, BIT[bn], True)
    restore_all(t, saved)
    tests.append(t)

    # ---- hstateen_encoding ----
    t = tss("hstateen_encoding")
    describe(
        t,
        context="hstateen0 uses mstateen0's bit positions to control the same state for the virtual machine only. "
        "With hstateen0 all zeros, VS/VU accesses to the state are blocked (virtual-instruction) while HS-mode "
        "accesses are unchanged; with hstateen0 all ones they are permitted again (as far as the bits read back "
        "allow). " + WARL_NOTE,
        plan="1. Probe each state from S-mode.\n"
        "2. hstateen0 = 0, then all ones: access senvcfg, sstateen0, siselect, stopi, scontext, sctrctl and jvt from "
        "S, VS and VU (and jvt from U).\n"
        "3. Restore hstateen0.",
    )
    with t.only_if(H):
        saved = snap_all(t, ("h",), (0,))
        labs = {}
        for nm in vs_res:
            labs[nm] = probe_res(t, RES[nm])
        for v in (0, ONES):
            write64(t, "h", 0, v)
            for nm in vs_res:
                rr = RES[nm]
                load_word(t, "x6", labs[nm])
                load_hs(t, rr)
                line, e = rr.read()
                for mode in ("S", "VS", "VU") + (("U",) if rr.level == "U" else ()):
                    dyn_window(t, mode, line, e, rr.level, f"{nm} with hstateen0 written {'all ones' if v else 0}")
        restore_all(t, saved)
    tests.append(t)

    # ---- sstateen_vsmode_access_roz ----
    t = tss("sstateen_vsmode_access_roz")
    describe(
        t,
        context="VS-mode accesses the same sstateen CSRs as HS-mode, but bits whose hstateen bit is 0 read 0 there "
        "and are read-only (a VS write leaves them unchanged, as seen from HS-mode). sstateen0 bits 0-2 are the "
        "only defined sstateen bits; where no Zcmt/Zfinx/custom state exists they are read-only zero and the "
        "checks hold trivially.",
        plan="For hstateen0 bits 0-2 cleared, then set:\n"
        "1. HS writes all ones to sstateen0 and reads s.\n"
        "2. VS reads sstateen0: no bit outside hstateen0 (read in HS).\n"
        "3. VS writes 0 to sstateen0; HS reads it: the bits hstateen0 masks still equal s.\n"
        "The checks run only when sstateen0 is accessible from S-mode (probe); hstateen0.SE0 is set first.\n"
        "Restore sstateen0 and hstateen0.",
    )
    with t.only_if(H):
        saved = snap_all(t, ("h", "s"), (0,))
        av = probe_res(t, RES["sstateen0"])
        load_word(t, "x7", av)
        t.either("x7", lambda: vsmask(t), lambda: None)
        restore_all(t, saved)
    tests.append(t)

    # ---- stateen_reserved_roz (S and VS view) ----
    t = tss("stateen_reserved_roz")
    describe(
        t,
        context="Reserved bits seen from HS-mode (hstateen0-3, sstateen0-3) and VS-mode (sstateen0-3). A stateen CSR "
        "is accessed only if an S-mode probe at the boot configuration shows it is accessible (the "
        "machine-level enable is the environment's). Smstateen/stateen_reserved_roz_Sm.S checks mstateen.",
        issues="QEMU lets sstateen1-3 bit 63 be written on RV64 (https://gitlab.com/qemu-project/qemu/-/work_items/"
        "4726, config/qemu/ci.yaml). Imperas let hstateen0 bit 56 be written (fixed in the engineering build).",
        plan="For each N (where accessible):\n"
        "1. HS: hstateenN = all ones (H): reserved bits read 0.\n"
        "2. HS: sstateenN = all ones: reserved bits read 0.\n"
        "3. VS (hstateenN[63] set): write all ones to sstateenN and read it: reserved bits read 0.\n"
        "Restore hstateen0-3 and sstateen0-3.",
    )
    saved = snap_all(t, ("h", "s"))
    for n in range(4):
        for kind, c in (("h", H), ("s", None)):
            with cond(t, c):
                av = probe_res(t, RES[f"{kind}stateen{n}"])
                load_word(t, "x7", av)

                def reserved(kind: str = kind, n: int = n) -> None:
                    write64(t, kind, n, ONES)
                    read64(t, kind, n, "x6", "x8")
                    bad = (1 << 56) if (MUT == "hstateen0_p1p13" and kind == "h" and n == 0) else 0
                    check64_masked(
                        t,
                        "x6",
                        "x8",
                        ONES & ~defined(kind, n),
                        bad,
                        f"{kind}stateen{n} reserved bits read 0 (all ones written in HS-mode)",
                        kind != "s",
                    )

                t.either("x7", reserved, lambda: None)
        with t.only_if(H):
            av = probe_res(t, RES[f"sstateen{n}"])
            load_word(t, "x7", av)

            def vs(n: int = n) -> None:
                bit_op(t, "h", n, 63, True)
                t.enter("VS")
                t.li("x7", -1)
                t.emit(f"csrw {hex(cnum('s', n))}, x7")
                t.emit(f"csrr x6, {hex(cnum('s', n))}")
                t.leave()
                lab = t.label("vs")
                t.emit(f"{lab}:", 0)
                t.check_masked(
                    "x6",
                    X(0xFFFFFFFF & ~defined("s", n), ONES & ~defined("s", n)),
                    0,
                    lab,
                    f"sstateen{n} reserved bits read 0 in VS-mode (all ones written there)",
                )

            t.either("x7", vs, lambda: None)
    restore_all(t, saved)
    tests.append(t)

    # ---- hstateen_bit_63_writable ----
    t = tss("hstateen_bit_63_writable")
    describe(
        t,
        context="With the machine-level enable for hstateenN (probed from S-mode), HS-mode can set and clear "
        "hstateenN[63] (hstateenNh bit 31 on RV32).",
        issues="Imperas kept hstateen bit 63 read-only (fixed in the engineering build).",
        plan="For each N where hstateenN is accessible: clear bit 63 (reads 0), set it (reads 1). Restore hstateen0-3.",
    )
    with t.only_if(H):
        saved = snap_all(t, ("h",))
        for n in range(4):
            av = probe_res(t, RES[f"hstateen{n}"])
            load_word(t, "x7", av)

            def body(n: int = n) -> None:
                for on in (False, True):
                    bit_op(t, "h", n, 63, on)
                    read_bit(t, "h", n, 63, "x6")
                    lab = t.label("b63")
                    t.emit(f"{lab}:", 0)
                    exp = 0 if (on and MUT == "h63_readonly") else int(on)
                    t.check("x6", exp, lab, f"hstateen{n}[63] reads {int(on)} after being written {int(on)}")

            t.either("x7", body, lambda: None)
        restore_all(t, saved)
    tests.append(t)

    # ---- sstateen_rv64_csrs / hstateen_rv64_csrs ----
    for rule, kind in (("sstateen_rv64_csrs", "s"), ("hstateen_rv64_csrs", "h")):
        t = tss(rule)
        describe(
            t,
            context=f"The {kind}stateen0-3 CSRs ({hex(cnum(kind, 0))}-{hex(cnum(kind, 3))}"
            + (", and hstateen0h-3h on RV32" if kind == "h" else "")
            + ") are accessible from S/HS-mode when the machine level enables them (bit 63 of the matching "
            "mstateen). With Smstateen the boot sets those bits, so every access must succeed; without it the "
            "environment decides and a trap is accepted. Reads and writes (of the value just read, or set/clear of "
            "0) are tried in all forms."
            + (
                " On RV64 sstateen0 is 64 bits wide and its upper 32 bits are reserved (no high-half CSR exists "
                "because they are expected to stay zero)."
                if kind == "s"
                else ""
            ),
            plan=f"For each {kind}stateenN"
            + (" (and hstateenNh on RV32)" if kind == "h" else "")
            + ": read (csrrs, csrrsi uimm=0), write back (csrrw x7 = value read), set and clear with x7 = 0 (csrrs, "
            "csrrc) and csrrci uimm=0, each without a trap (Smstateen) or with illegal-instruction allowed. "
            + ("RV64: sstateen0 written all ones has bits 63:32 zero. " if kind == "s" else "")
            + f"Restore {kind}stateen0-3.",
        )
        with cond(t, H if kind == "h" else None):
            saved = snap_all(t, (kind,))
            for n in range(4):
                csrs: list[tuple[int, str, str | None]] = [(cnum(kind, n), f"{kind}stateen{n}", None)]
                if kind == "h":
                    csrs.append((cnum(kind, n, True), f"{kind}stateen{n}h", RV32))
                for c, nm, cc in csrs:
                    with cond(t, cc):
                        fl = [
                            (f"csrrs x1, {hex(c)}, x0", enc_csr(c, 2, 1, 0), "read (csrrs rs1=x0)"),
                            (f"csrrsi x1, {hex(c)}, 0", enc_csr(c, 6, 1, 0), "read (csrrsi uimm=0)"),
                            (f"csrrw x0, {hex(c)}, x7", enc_csr(c, 1, 0, 7), "write back (csrrw x7 = value read)"),
                            (f"csrrs x1, {hex(c)}, x0", enc_csr(c, 2, 1, 0), "read"),
                        ]
                        for line, e, k in fl:
                            s_window(t, line + f"  // {nm}", e, f"{k} of {nm}")
                            t.emit("mv x7, x1")
                        for line, e, k in (
                            (f"csrrs x1, {hex(c)}, x7", enc_csr(c, 2, 1, 7), "set with x7=0 (csrrs)"),
                            (f"csrrc x1, {hex(c)}, x7", enc_csr(c, 3, 1, 7), "clear with x7=0 (csrrc)"),
                            (f"csrrci x1, {hex(c)}, 0", enc_csr(c, 7, 1, 0), "read (csrrci uimm=0)"),
                        ):
                            t.li("x7", 0)
                            s_window(t, line + f"  // {nm}", e, f"{k} of {nm}")
            if kind == "s":
                with t.rv64_only():
                    t.emit("#ifdef SMSTATEEN_SUPPORTED", 0)
                    t.li("x7", -1)
                    t.emit("csrw CSR_SSTATEEN0, x7")
                    t.emit("csrr x6, CSR_SSTATEEN0")
                    lab = t.label("up")
                    t.emit(f"{lab}:", 0)
                    t.check_masked(
                        "x6",
                        ONES << 32,
                        (1 << 32) if MUT == "sstateen_upper_writable" else 0,
                        lab,
                        "sstateen0 bits 63:32 read 0 (all ones written)",
                    )
                    t.emit("#endif", 0)
            restore_all(t, saved)
        tests.append(t)

    # ---- stateen_op (HS/S own level) ----
    t = tss("stateen_op")
    names = [
        "senvcfg",
        "sstateen0",
        "sstateen1",
        "sstateen2",
        "sstateen3",
        "siselect",
        "stopi",
        "stopei",
        "scontext",
        "srmcfg",
        "sctrctl",
        "jvt",
        "henvcfg",
        "hcontext",
        "hvictl",
        "vsiselect",
    ]
    describe(
        t,
        context="hstateen controls VS/VU and sstateen controls U/VU; neither changes what HS-mode itself may access. "
        "The test records each S-mode access at the boot configuration (the state is optional), clears hstateen0-3 "
        "and sstateen0, and repeats the accesses. Smstateen/stateen_op_Sm.S checks M-mode against mstateen.",
        plan="1. Read each controlled CSR from S-mode and record whether it trapped.\n"
        "2. hstateen0-3 = 0 (H) and sstateen0 = 0: each read has the same outcome.\n"
        "3. Restore hstateen0-3 and sstateen0.",
    )
    labs = {}
    for nm in names:
        with cond(t, RES[nm].cond):
            labs[nm] = probe_res(t, RES[nm])
    saved = snap_all(t, ("h", "s"))
    with t.only_if(H):
        for n in range(4):
            write64(t, "h", n, 0)
    t.emit("csrw CSR_SSTATEEN0, x0")
    for nm in names:
        rr = RES[nm]
        with cond(t, rr.cond):
            load_word(t, "x6", labs[nm])
            if MUT == "hs_own_level_gated" and rr.level in ("U", "S", "SnoV"):
                t.li("x6", 0)
            line, e = rr.read()
            dyn_window(t, "S", line, e, rr.level, f"{nm} with hstateen0-3 and sstateen0 written 0")
    restore_all(t, saved)
    tests.append(t)

    # ---- stateen0_c_op ----
    t = ts("stateen0_c_op")
    describe(
        t,
        context="No standard state is custom, so the C bits must not grant access to it: with C set at every level "
        "and mstateen0.ENVCFG cleared, senvcfg stays blocked; with C cleared and ENVCFG set, it is accessible. "
        + WARL_NOTE,
        issues=ISSUE_2300,
        plan="1. Set the C bit (0) of mstateen0, hstateen0 (H) and sstateen0.\n"
        "2. mstateen0.ENVCFG = 0, 1: read senvcfg from S, U, VS and VU.\n"
        "3. Clear the C bits; mstateen0.ENVCFG = 1: read senvcfg from S, VS and VU.\n"
        "4. Restore the stateen CSRs.",
    )
    saved = snap_all(t, ("m", "h", "s"), (0,))
    for kind, c in (("m", None), ("h", H), ("s", None)):
        with cond(t, c):
            bit_op(t, kind, 0, 0, True)
    if MUT == "c_bit_grants_all":
        rr = Res("senvcfg", 0x10A, "S", (0, 0), (0, 0))  # C stands in for ENVCFG: C=1 opens senvcfg
        av = probe_res(t, rr)
        load_word(t, "x6", av)
        bit_op(t, "m", 0, 62, False)
        load_hs(t, RES["senvcfg"])
        windows(t, rr, ("S",), "C=1, ENVCFG=0 (mutant)")
        bit_op(t, "m", 0, 62, True)
    else:
        av = sweep(t, RES["senvcfg"], "m", smstateen=True, states=(0, 1))
    for kind, c in (("m", None), ("h", H), ("s", None)):
        with cond(t, c):
            bit_op(t, kind, 0, 0, False)
    av2 = probe_res(t, RES["senvcfg"])
    sweep(t, RES["senvcfg"], "m", smstateen=True, states=(1,), modes=("S", "VS", "VU"), avail=av2)
    restore_all(t, saved)
    tests.append(t)

    # ---- stateen0_fcsr_op ----
    t = ts("stateen0_fcsr_op")
    describe(
        t,
        context="The FCSR bits control fcsr only when floating-point instructions use x registers (Zfinx; misa.F = "
        "0). With F, fcsr is controlled by the FS fields alone: with sstatus.FS (and vsstatus.FS) nonzero it is "
        "accessible from S, U, VS and VU whatever the FCSR bits (which are read-only zero then). Without F, fcsr "
        "follows the FCSR bits like jvt follows JVT. " + WARL_NOTE + " " + HSQ,
        plan="With F:\n"
        "1. sstatus.FS = vsstatus.FS = Initial; clear the FCSR bit of mstateen0, hstateen0 and sstateen0.\n"
        "2. Read fcsr from S, U, VS and VU: no trap.\n"
        "Without F: sweep mstateen0.FCSR, hstateen0.FCSR and sstateen0.FCSR (1, 0, 1), reading fcsr from S, U, VS "
        "and VU.\n"
        "Restore sstatus.FS, vsstatus.FS and the stateen CSRs.",
    )
    saved = snap_all(t, ("m", "h", "s"), (0,))
    with t.only_if("defined(F_SUPPORTED)"):
        st = word(t, "fs")
        t.emit("csrr x7, sstatus")
        t.la("x1", st)
        t.emit("SREG x7, 0(x1)")
        t.li("x7", 0x2000)
        t.emit("csrs sstatus, x7")
        with t.only_if(H):
            t.emit("csrr x7, CSR_VSSTATUS")
            t.emit("SREG x7, 8(x1)")
            t.extra_data.append("  .dword 0")
            t.li("x7", 0x2000)
            t.emit("csrs CSR_VSSTATUS, x7")
        for kind, c in (("m", None), ("h", H), ("s", None)):
            with cond(t, c):
                bit_op(t, kind, 0, 1, False)
        e = enc_csr(0x003, 2, 1, 0)
        exp = ILLEGAL if MUT == "fcsr_bit_gates_f" else "ok"
        for mode in MODES:
            with cond(t, H if mode in ("VS", "VU") else None):
                t.window(
                    mode,
                    ["csrrs x1, 0x003, x0  // fcsr"],
                    exp,
                    "read of fcsr with F, FS=Initial and every FCSR bit cleared",
                    None if exp == "ok" else [0, e],
                )
        t.li("x7", 0x6000)
        t.emit("csrc sstatus, x7")
        t.la("x1", st)
        t.emit("LREG x7, 0(x1)")
        t.li("x1", 0x6000)
        t.emit("and x7, x7, x1")
        t.emit("csrs sstatus, x7")
        with t.only_if(H):
            t.emit("csrc CSR_VSSTATUS, x1")
            t.la("x1", st)
            t.emit("LREG x7, 8(x1)")
            t.li("x1", 0x6000)
            t.emit("and x7, x7, x1")
            t.emit("csrs CSR_VSSTATUS, x7")
    with t.only_if("!defined(F_SUPPORTED)"):
        av = sweep(t, RES["fcsr"], "m", smstateen=True)
        sweep(t, RES["fcsr"], "h", smstateen=True, avail=av)
        sweep(t, RES["fcsr"], "s", smstateen=True, avail=av)
    restore_all(t, saved)
    tests.append(t)

    return tests


def gen() -> list[TestFile]:
    return gate_tests() + struct_tests() + more_tests()


def main() -> None:
    for t in gen():
        p = t.write()
        print(f"{p.relative_to(p.parents[2])}: ~{t.ninst} instructions")


if __name__ == "__main__":
    main()
