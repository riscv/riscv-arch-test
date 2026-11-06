#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate the pointer-masking suites: tests_ai/Smmpm, Smnpm, Ssnpm, Sspm and Supm.

One test per norm: rule of the pointer-masking chapter (src/priv/zpm.adoc) and of the PMM/HUPMM CSR fields
(machine.adoc mseccfg/menvcfg, supervisor.adoc senvcfg, hypervisor.adoc henvcfg). A rule goes to the suite whose
behavior it constrains:

- Smmpm: mseccfg.PMM and M-mode accesses (boot to M).
- Smnpm: menvcfg.PMM (S/HS, or U without S), and the rules about several modes at once: per-mode control, MPRV,
  UXL/SXL (boot to M, the mode that owns menvcfg).
- Ssnpm: senvcfg.PMM and henvcfg.PMM: U, VS and VU (boot to S).
- Sspm: what S-mode software sees, with T-SBI writing menvcfg.PMM as the execution environment's facility (boot to S).
- Supm: what U-mode software sees, with T-SBI writing senvcfg.PMM (or menvcfg.PMM without S) as the facility (the
  lowest mode); U-mode virtual addresses need M-mode to run U under satp (pm_ignore_va_Sm).

mutate.py derives the suite from this file's name, so mutants are named Spm:<mutant>; for a mutant run, SUITE is set
to the mutant directory and every test goes there.
"""

from __future__ import annotations

import contextlib
import importlib
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent))
import hmem
import spmlib

spmlib = importlib.reload(spmlib)  # re-read AI_MUTANT (mutate.py reloads this module only)
from spmlib import (
    ALL_KINDS,
    CSRN,
    HYP,
    ISSUE_1844,
    ISSUE_1944,
    ISSUE_2423,
    ISSUE_3313,
    KINDS,
    LEAF,
    M64,
    MAC,
    MXR,
    NOS,
    PMM_M,
    PMM_SH,
    S_,
    SUP,
    TAIL,
    TVAL_NOTE,
    ZPM,
    Addr,
    H,
    SvPT,
    access,
    csr_op,
    csr_read,
    dispatch,
    legal_pmm,
    new,
    pmm_field,
    pmm_write,
    pred_exact,
    pred_exact_cross,
    pred_not,
    restore,
    satp_off,
    satp_probe,
    save,
    setpm,
    sig,
    tagmask,
    window,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from hmem import MemTest

    Peff = Callable[[int, list[str]], "int | dict[str, int]"]
    MxrPeff = Callable[[int, list[str]], dict[str, int]]

SUITE = "Spm"
MUT = os.environ.get("AI_MUTANT", "")

MUTANTS = {
    "va_zero_extend": "virtual addresses are zero-extended instead of sign-extended",
    "pmlen_off_by_one_low": "bit XLEN-PMLEN is not masked (PMLEN-1 bits ignored)",
    "pmlen_off_by_one_high": "bit XLEN-PMLEN-1 is masked too (PMLEN+1 bits ignored)",
    "pmm_encodings_swapped": "PMM=10 gives PMLEN=16 and PMM=11 gives PMLEN=7",
    "va_validity_only": "masked bits that are VBITS (Sv57, PMLEN=16) only relax the validity check",
    "fetch_masked": "instruction fetch addresses are masked",
    "ptw_masked": "page-table-walk addresses are masked",
    "mxr_ignored": "MXR does not disable pointer masking for S/U accesses",
    "mxr_disables_m": "mstatus.MXR disables M-mode pointer masking",
    "mxr_loads_only": "MXR disables pointer masking for loads only",
    "menvcfg_masks_u": "menvcfg.PMM (not senvcfg.PMM) controls U-mode when S exists",
    "senvcfg_masks_s": "senvcfg.PMM controls S-mode",
    "mseccfg_masks_lower": "mseccfg.PMM controls S- and U-mode too",
    "menvcfg_masks_m": "menvcfg.PMM controls M-mode",
    "mprv_ignored": "MPRV accesses use M-mode's pointer-masking setting",
    "henvcfg_masks_vu": "henvcfg.PMM (not senvcfg.PMM) controls VU-mode",
    "senvcfg_masks_vs": "senvcfg.PMM (not henvcfg.PMM) controls VS-mode",
    "reserved_reads_back": "PMM=01 is a legal value that reads back",
    "tval_untransformed": "xtval holds the untransformed (tagged) address",
    "csr_write_masked": "software writes of addresses to xepc/xtval are masked",
    "amo_unmasked": "AMOs are not masked",
    "lrsc_unmasked": "LR/SC are not masked",
    "fp_unmasked": "FP loads and stores are not masked",
    "vec_unmasked": "vector loads and stores are not masked",
    "cbo_unmasked": "CBO.ZERO is not masked",
    "subword_unmasked": "byte and halfword accesses are not masked",
    "misaligned_second_unmasked": "the second part of a page-crossing misaligned access is not masked",
    "uxl_write_clears_pmm": "an ignored write of UXL/SXL=1 still clears PMM",
    "rv32_pmm_writable": "RV32 PMM bits (menvcfgh/mseccfgh/henvcfgh 1:0) are writable",
    "pmm_needs_fence": "a new senvcfg.PMM takes effect only after SFENCE.VMA",
    "no_pmlen_required": "an implementation of the extension may support no nonzero PMLEN",
}

INT1 = ["ld", "sd"]
REQ_M = ["I", "Sm"]


def sd(ext: str) -> str:
    """The directory of extension ext (all tests go to one directory for a mutant run)."""
    return ext if SUITE == "Spm" else SUITE


def cond(t: MemTest, c: str | None) -> contextlib.AbstractContextManager[None]:
    return t.only_if(c) if c else contextlib.nullcontext()


def groups(kinds: list[str]) -> list[tuple[str | None, list[str]]]:
    out: list[tuple[str | None, list[str]]] = []
    for k in kinds:
        c = KINDS[k][4]
        if out and out[-1][0] == c:
            out[-1][1].append(k)
        else:
            out.append((c, [k]))
    return out


GATE: list[int] = []  # scratch slots holding run-time conditions (e.g. a supported satp mode) for gated()


def gated(t: MemTest, fn: Callable[[], object]) -> None:
    """Run fn under the innermost run-time condition. Each table-consuming chunk branches on its own, because
    one AI_SKIP can skip at most 255 table entries."""
    if not GATE:
        fn()
        return
    restore(t, GATE[-1], "x5")
    t.either("x5", fn, lambda: None)


# ---------------------------------------------------------------- which register controls which mode
def ctrl_of(mode: str) -> str:
    """The CSR whose PMM applies to accesses in `mode` (MPRV_x: the MPP mode), with the mutants that pick the wrong
    one. U-mode: senvcfg (its value with S is checked; without S, menvcfg: see read_ctrl)."""
    m = {"MPRV_M": "M", "MPRV_S": "S", "MPRV_U": "U"}.get(mode, mode)
    if MUT == "mprv_ignored" and mode.startswith("MPRV"):
        m = "M"
    c = {"M": "mseccfg", "S": "menvcfg", "U": "senvcfg", "VS": "henvcfg", "VU": "senvcfg"}[m]
    if MUT == "menvcfg_masks_u" and m == "U":
        c = "menvcfg"
    if MUT == "senvcfg_masks_s" and m == "S":
        c = "senvcfg"
    if MUT == "mseccfg_masks_lower" and m in ("S", "U"):
        c = "mseccfg"
    if MUT == "menvcfg_masks_m" and m == "M":
        c = "menvcfg"
    if MUT == "henvcfg_masks_vu" and m == "VU":
        c = "henvcfg"
    if MUT == "senvcfg_masks_vs" and m == "VS":
        c = "senvcfg"
    return c


def read_ctrl(t: MemTest, mode: str, slot: int) -> None:
    """Scratch slot = the PMM value that applies to `mode`'s accesses (read from its controlling CSR)."""
    c = ctrl_of(mode)
    if c == "mseccfg":  # mseccfg may not exist without Smmpm; M-mode then has no pointer masking
        with t.only_if("defined(SMMPM_SUPPORTED)"):
            csr_read(t, "mseccfg", "x8")
        with t.only_if("!defined(SMMPM_SUPPORTED)"):
            t.emit(f"li x8, {hex(PMM_M)}" if MUT == "menvcfg_masks_m" else "li x8, 0")
    elif c == "senvcfg" and mode in ("U", "MPRV_U"):
        with t.only_if(S_):
            csr_read(t, "senvcfg", "x8")
        with t.only_if(NOS):
            csr_read(t, "menvcfg", "x8")
    else:
        csr_read(t, c, "x8")
    pmm_field(t, "x8")
    save(t, "x8", slot)


def ctrl_write(t: MemTest, mode: str, val: int, slot: int, desc: str = "") -> None:
    """Write the PMM of `mode`'s true controlling CSR (U: senvcfg, or menvcfg without S), check the value read back,
    keep it in `slot`, and re-read the register the expectations come from when a mutant picks another one."""
    true = {"M": "mseccfg", "S": "menvcfg", "U": "uctrl", "VS": "henvcfg", "VU": "senvcfg"}[mode]
    setpm(t, true, val, slot, desc)
    if ctrl_of(mode) != {"uctrl": "senvcfg"}.get(true, true):
        read_ctrl(t, mode, slot)


def sweep(
    t: MemTest,
    mode: str,
    kinds: list[str],
    addrs: list[Addr],
    vals: tuple[int, ...] = (3, 2, 0),
    peff: Peff | None = None,
    desc: str = "",
    gstage: bool = False,
    write: bool = True,
) -> None:
    """For each PMM value written to `mode`'s controlling CSR: every access kind to every address, with the
    expectations of the PMM value read back (run-time dispatch)."""
    for val in vals:
        if write:
            gated(t, lambda val=val: ctrl_write(t, mode, val, 0))
        for c, ks in groups(kinds):
            with cond(t, c):
                for k in ks:
                    for i in range(0, len(addrs), 3):

                        def body(p: int, k: str = k, chunk: list[Addr] = addrs[i : i + 3]) -> None:
                            pe = peff(p, [k]) if peff else p
                            for a in chunk:
                                access(t, mode, k, a, pe if not isinstance(pe, dict) else pe[k], desc, gstage)

                        gated(t, lambda body=body: dispatch(t, 0, body))
        if not write:
            break


def pm_off(t: MemTest, mode: str) -> None:
    true = {"M": "mseccfg", "S": "menvcfg", "U": "uctrl", "VS": "henvcfg", "VU": "senvcfg"}[mode]
    t.comment(f"pointer masking off for {mode}-mode")
    if true == "uctrl":
        with t.only_if(S_):
            csr_op(t, "CLEAR", "senvcfg", imm=PMM_M)
        with t.only_if(NOS):
            csr_op(t, "CLEAR", "menvcfg", imm=PMM_M)
    else:
        csr_op(t, "CLEAR", true, imm=PMM_M)


# ---------------------------------------------------------------- address sets
T7 = tagmask(7)  # all seven top bits
T16 = tagmask(16)


def pa(page: str = "A", off: int = 0, tag: int = 0, q: int = 7, space: str = "pa") -> Addr:
    return Addr(page, off, tag, q, space)


def pa_basic(space: str = "pa") -> list[Addr]:
    """Tags masked by PMLEN=7 and 16 (top 7 bits), and by PMLEN=16 only (bits 56:48)."""
    return [pa(tag=T7, space=space), pa(tag=0x55 << 57, space=space), pa(tag=0xA5C3 << 48, q=16, space=space)]


def pa_boundary(space: str = "pa") -> list[Addr]:
    """Single bits at the PMLEN boundaries and a pattern in 56:48 only."""
    return [
        pa(tag=1 << 63, space=space),
        pa(tag=1 << 57, space=space),
        pa(tag=1 << 56, q=16, space=space),
        pa(tag=1 << 48, q=16, space=space),
        pa(tag=0x0155 << 48, q=16, space=space),
        pa(tag=T16, q=16, space=space),
    ]


def va_set(scheme: str, R: int, vabits: int) -> list[Addr]:
    """Virtual addresses through the identity map (positive half) and the high-half alias of page A, tagged."""
    v = {"space": "va", "vabits": vabits, "R": R}
    out = [
        Addr("A", 0, T7, 7, **v),
        Addr("A", 0, 0x2A << 57, 7, **v),
        Addr("A", 0, 0xA5C3 << 48, 16, **v),
        Addr("A", 0, 1 << 56, 16, **v),  # sign bit for PMLEN=7: sign-extends to the high half
        Addr("A", 0, 0, 7, hi=True, **v),  # high half, top bits cleared
        Addr("A", 0, 0x55 << 57, 7, hi=True, **v),
        Addr("A", 0, 0x8000 << 48, 16, hi=True, **v),  # bit 63 only, 62:48 cleared
        Addr("A", 0, 0xFF7F << 48, 16, hi=True, **v),  # bit 55 cleared: only PMLEN=16 sign-extends from 47
    ]
    return out


def va_unmapped(R: int, vabits: int) -> list[Addr]:
    """Tagged versions of a valid, unmapped VA (root-level entry 5): a page fault whose xtval must be 0 or exactly
    the transformed VA."""
    c = (5 << R) + 0x1230
    v = {"space": "va", "vabits": vabits, "R": R}
    return [Addr(None, 0, T7, 7, const=c, **v), Addr(None, 0, 0x5A5A << 48, 16, const=c, **v)]


SCHEME_R = {"sv39": (30, 39), "sv48": (39, 48), "sv57": (48, 57)}


def with_satp(t: MemTest, scheme: str, perms: int, body: Callable[[int, int], object], csr: str = "satp") -> None:
    """Build a table for scheme (identity + high-half alias of page A) and, if the scheme is supported (probed
    through satp/vsatp), run body(R, vabits); then back to Bare."""
    pt = SvPT(t, f"{csr}_{scheme}", scheme)
    pt.identity(perms)
    pt.hi_alias("A", perms)
    satp_probe(t, pt, csr)
    R, vabits = SCHEME_R[scheme]
    slot = 4 + len(GATE)
    save(t, "x5", slot)
    GATE.append(slot)
    body(R, vabits)
    GATE.pop()
    satp_off(t, csr)


# ---------------------------------------------------------------- common rule texts
RULES = {
    "pm_ignore_upper_bits": (
        ZPM,
        (
            "RISC-V Pointer Masking (PM) is a feature that, when enabled, causes the CPU to "
            "ignore the upper bits of the effective address"
        ),
    ),
    "pm_ignore_va": (
        ZPM,
        (
            "The ignore transformation differs depending on whether it applies to a virtual or "
            "physical address. For virtual addresses, it replaces the upper PMLEN bits with the sign "
            "extension of the PMLEN+1st bit."
        ),
    ),
    "pm_ignore_pa": (
        ZPM,
        (
            "When applied to a physical address, including guest-physical addresses (i.e., all cases "
            "except when the active satp register's MODE field != Bare), the ignore transformation replaces "
            "the upper PMLEN bits with 0. This includes both the case of running in M-mode and running in "
            "other privilege modes with Bare address translation mode."
        ),
    ),
    "pm_apply_explicit": (
        ZPM,
        (
            "When pointer masking is enabled, the ignore transformation will be applied to every "
            "explicit memory access (e.g., loads/stores, atomics operations, and floating point "
            "loads/stores)."
        ),
    ),
    "pm_not_apply_implicit": (
        ZPM,
        "The transformation *does not* apply to implicit accesses such as page-table walks or instruction fetches.",
    ),
    "pm_deterministic_effect": (
        ZPM,
        (
            "Pointer masking with the same value of PMLEN always has the same effect for the "
            "same type of address (virtual or physical)."
        ),
    ),
    "pmlen_supported_values": (
        ZPM,
        (
            "The current standard only supports PMLEN=XLEN-48 (i.e., PMLEN=16 in RV64) and "
            "PMLEN=XLEN-57 (i.e., PMLEN=7 in RV64)."
        ),
    ),
    "pmlen_future_reserved": (
        ZPM,
        "A setting has been reserved to potentially support other values of PMLEN in future standards.",
    ),
    "pm_per_mode_control": (ZPM, "Pointer masking is controlled separately for different privilege modes."),
    "pm_auto_apply_active_mode": (
        ZPM,
        (
            "Different privilege modes may have different pointer masking settings active "
            "simultaneously and the hardware will automatically apply the pointer masking "
            "settings of the currently active privilege mode."
        ),
    ),
    "pm_config_next_higher": (
        ZPM,
        (
            "A privilege mode's pointer masking setting is configured by bits in "
            "configuration registers of the next-higher privilege mode."
        ),
    ),
    "pm_mode_only_dependency": (
        ZPM,
        (
            "the pointer masking setting that is applied only depends on the active "
            "privilege mode, not on the address that is being masked."
        ),
    ),
    "pm_explicit_accesses": (
        ZPM,
        "Unless otherwise specified, pointer masking applies to all explicit memory accesses.",
    ),
    "pm_mprv_spvp": (
        ZPM,
        (
            "MPRV and SPVP affect pointer masking as well, causing the pointer masking settings of the "
            "effective privilege mode to be applied."
        ),
    ),
    "pm_mxr_exception": (
        ZPM,
        (
            "When MXR is in effect at the effective privilege mode where explicit memory access is "
            "performed, pointer masking does not apply."
        ),
    ),
    "pm_cpu_only": (
        ZPM,
        (
            "Pointer masking only applies to accesses generated by instructions on the CPU (including "
            "CPU extensions such as an FPU). E.g., it does not apply to accesses generated by page-table walks, "
            "the IOMMU, or devices."
        ),
    ),
    "pm_misaligned_equivalence": (
        ZPM,
        (
            "Misaligned accesses are supported, subject to the same limitations as in the "
            "absence of pointer masking. The behavior is identical to applying the pointer "
            "masking transformation to every constituent aligned memory access."
        ),
    ),
    "pm_no_csr_sw": (
        ZPM,
        (
            "No pointer masking operations are applied when software reads/writes to CSRs, including "
            "those meant to hold addresses."
        ),
    ),
    "pm_warl_unaffected": (ZPM, "The implemented WARL width of CSRs is unaffected by pointer masking"),
    "pm_csr_hw_apply": (
        ZPM,
        (
            "pointer masking, when applicable, **is applied** for hardware writes to a CSR (e.g., "
            "when the hardware writes the transformed address to `stval` when taking an exception)."
        ),
    ),
    "smmpm_definition": (ZPM, "A machine-level extension that provides pointer masking for M-mode."),
    "smnpm_definition": (
        ZPM,
        (
            "A machine-level extension that provides pointer masking for the next lower privilege "
            "mode (S/HS if S-mode is implemented, or U-mode otherwise)."
        ),
    ),
    "ssnpm_definition": (
        ZPM,
        (
            "A supervisor-level extension that provides pointer masking for the next lower "
            "privilege mode (U-mode), and for VS- and VU-modes if the H extension is present."
        ),
    ),
    "pm_rv32_illegal": (
        ZPM,
        (
            "In RV32, trying to enable pointer masking will result in an illegal WARL write and not "
            "update the pointer masking configuration bits"
        ),
    ),
    "pm_uxl_clear": (ZPM, "Setting UXL/SXL to 1 will clear the corresponding pointer masking configuration bits."),
    "pmlen_illegal_warl": (
        ZPM,
        (
            "Trying to enable pointer masking in an unsupported scenario represents an illegal "
            "write to the corresponding pointer masking enable bit and follows WARL semantics."
        ),
    ),
    "mseccfg_pmm_presence_op": (
        MAC,
        (
            "If the Smmpm extension is implemented, the PMM field enables or disables "
            "pointer masking (see <<Zpm>>) for M-mode according to the values in "
            "<<norm:mseccfg_pmm_enc>>."
        ),
    ),
    "mseccfg_pmm_rdonly0": (
        MAC,
        "If Smmpm is not implemented, PMM is read-only zero. The PMM field is read-only zero for RV32.",
    ),
    "mseccfg_pmm_enc": (
        MAC,
        (
            "Legal values of PMM WARL field: 00 Pointer masking is disabled (PMLEN = 0); 01 "
            "Reserved; 10 Pointer masking is enabled with PMLEN = XLEN - 57 (PMLEN = 7 on RV64); 11 "
            "Pointer masking is enabled with PMLEN = XLEN - 48 (PMLEN = 16 on RV64)"
        ),
    ),
    "menvcfg_pmm_op": (
        MAC,
        (
            "If the Smnpm extension is implemented, the PMM field enables or disables pointer "
            "masking (see <<Zpm>>) for the next-lower privilege mode (S-/HS-mode if S-mode is "
            "implemented, or U-mode otherwise), according to the values in <<norm:menvcfg_pmm_enc>>."
        ),
    ),
    "menvcfg_pmm_rdonly0": (
        MAC,
        "If Smnpm is not implemented, PMM is read-only zero. The PMM field is read-only zero for RV32.",
    ),
    "menvcfg_pmm_enc": (
        MAC,
        (
            "Legal values of PMM WARL field: 00 disabled (PMLEN = 0); 01 Reserved; 10 PMLEN = "
            "XLEN - 57 (7 on RV64); 11 PMLEN = XLEN - 48 (16 on RV64)"
        ),
    ),
    "senvcfg_pmm_ssnpm": (
        SUP,
        (
            "If the Ssnpm extension is implemented, the PMM field enables or disables pointer "
            "masking (see <<Zpm>>) for the next-lower privilege mode (U/VU), according to the values in "
            "<<norm:senvcfg_pmm_enc>>. If Ssnpm is not implemented, PMM is read-only zero. The PMM "
            "field is read-only zero for RV32."
        ),
    ),
    "senvcfg_pmm_immediate": (
        SUP,
        "Changing senvcfg.PMM takes effect immediately, without the need to execute an SFENCE.VMA instruction.",
    ),
    "senvcfg_pmm_enc": (
        SUP,
        (
            "Legal values of PMM WARL field: 00 disabled (PMLEN = 0); 01 Reserved; 10 PMLEN = "
            "XLEN - 57 (7 on RV64); 11 PMLEN = XLEN - 48 (16 on RV64)"
        ),
    ),
    "henvcfg_pmm_op": (
        HYP,
        (
            "If the Ssnpm extension is implemented, the PMM field enables or disables pointer "
            "masking (see <<Zpm>>) for VS-mode, according to the values in <<henvcfg-pmm-values>>. When "
            "the Ssnpm extension is not implemented, the PMM field is read-only zero. The PMM field is "
            "read-only zero for RV32."
        ),
    ),
}

DISPATCH_NOTE = (
    "PMM is WARL: after each write the test reads the value the hart holds (00, 10 or 11; 01 is reserved) and "
    "checks the behavior of that value, so harts that support only some PMLEN values are tested on those."
)
TRANSFORM_NOTE = (
    "Each access is built at run time from an untagged base with its top q bits replaced by a tag. The expected "
    "outcome is the reference transformation of that address: masked (the access reaches the untagged location) "
    "or not (a physical address with any of bits 63:56 set, or one with a high bit no RAM has, raises an access "
    "fault; a non-canonical VA raises a page fault). " + TVAL_NOTE
)


def describe(t: MemTest, rule: str, plan: str, context: str = "", issues: str = "") -> None:
    src, text = RULES[rule]
    t.describe(rule_text=text, source=src, context=context, issues=issues, plan=plan)


# ---------------------------------------------------------------- generic behavior builders (one mode)
MODE_REQ = {"M": ["I", "Sm"], "S": ["I", "S"], "U": ["I", "U"]}
MODE_NAME = {"M": "M-mode", "S": "S-mode", "U": "U-mode"}
FACILITY = {
    "M": "mseccfg.PMM, written directly in M-mode",
    "S": "menvcfg.PMM, written through T-SBI (the supervisor execution environment's facility)",
    "U": "senvcfg.PMM (menvcfg.PMM without S), written through T-SBI (the application execution environment's "
    "facility)",
}


def mk(
    ext: str, rule: str, mode: str, suffix: str = "", boot: str | None = None, extra: list[str] | None = None
) -> MemTest:
    """A test of extension ext whose accesses run natively in mode (M: boot M; S: boot S; U: lowest mode)."""
    req = MODE_REQ[mode] + [ext] + (extra or [])
    b = boot if boot else {"M": "M", "S": "S", "U": None}[mode]
    return new(sd(ext), rule, req, b, suffix=suffix)


def require_some(t: MemTest, mode: str, what: str) -> None:
    """The extension provides pointer masking, so writing 10 and writing 11 do not both read 00."""
    ctrl_write(t, mode, 2, 6)
    ctrl_write(t, mode, 3, 7)
    restore(t, 6, "x8")
    restore(t, 7, "x9")
    t.emit("or x8, x8, x9")
    t.emit("snez x8, x8")
    lab = t.label("some")
    t.emit(f"{lab}:", 0)
    if MUT == "no_pmlen_required":
        t.check("x8", 0, lab, f"{what}: no nonzero PMLEN is supported")
    else:
        t.check_bool("x8", lab, f"{what}: writing 10 or 11 enables pointer masking (they do not both read 00)")


def b_ignore_upper(ext: str, mode: str) -> MemTest:
    t = mk(ext, "pm_ignore_upper_bits", mode)
    describe(
        t,
        "pm_ignore_upper_bits",
        context=f"{MODE_NAME[mode]} accesses, Bare (physical) addresses. Pointer masking is enabled through "
        f"{FACILITY[mode]}. " + DISPATCH_NOTE,
        plan="0. The extension provides masking: the facility's writes of 10 and 11 do not both read back 00.\n"
        "1. For PMM written 11, 10 and 00: ld and sd of page A with the top 7 bits set to all ones, to 0x55 "
        "and with bits 56:48 = 0xA5C3 (top 16 bits). Where the hart's PMLEN covers the tag, the access reaches the "
        "untagged location (the value, or the doubleword written); otherwise it raises an access fault and writes "
        "nothing.\n"
        "2. The same with PMM = 0 at the end shows the tag is not ignored once masking is disabled.",
    )
    require_some(t, mode, f"{ext} ({mode}-mode pointer masking)")
    sweep(t, mode, INT1, pa_basic())
    pm_off(t, mode)
    return t


def b_ignore_pa(ext: str, mode: str) -> MemTest:
    t = mk(ext, "pm_ignore_pa", mode)
    describe(
        t,
        "pm_ignore_pa",
        context=f"{MODE_NAME[mode]} accesses with Bare translation, so addresses are physical. "
        + TRANSFORM_NOTE
        + " A physical address is zero-extended: bit XLEN-PMLEN-1 is kept, not copied upward, so an address whose "
        "bit 56 (PMLEN=7) or bit 47 (PMLEN=16) is set stays an invalid physical address.",
        issues=ISSUE_1944,
        plan="1. For PMM written 11, 10 and 00, ld and sd of page A tagged with single bits 63, 57 (the lowest bit "
        "PMLEN=7 masks), 56 (XLEN-PMLEN-1 for PMLEN=7: never masked by it), 48 (the lowest bit PMLEN=16 masks), the "
        "pattern 0x155 in bits 56:48, and all of bits 63:48.\n"
        "2. Masked: the access reaches the untagged location. Not masked: an access fault, nothing written, and "
        "xtval is not the masked address.",
    )
    sweep(t, mode, INT1, pa_boundary())
    pm_off(t, mode)
    return t


def b_apply_explicit(ext: str, mode: str, rule: str = "pm_apply_explicit") -> MemTest:
    t = mk(ext, rule, mode)
    describe(
        t,
        rule,
        context=f"{MODE_NAME[mode]} accesses, Bare (physical) addresses. Each class of explicit access that "
        "could use its own address path: integer loads of every width (with an immediate added before masking), "
        "stores of every width, AMOs (Zaamo), LR/SC (Zalrsc), FP loads/stores (F), vector unit-stride "
        "loads/stores (V) and CBO.ZERO (Zicboz). Instructions outside RV64I are .word encodings and run only when "
        "their extension is supported. " + DISPATCH_NOTE,
        issues=ISSUE_1844,
        plan="1. For PMM written 11, 10 and 00, every class accesses page A with the top 7 bits all ones and with "
        "bits 63:48 = 0xA5C3.\n"
        "2. Masked: loads return the untagged location's data, stores, AMOs and SC write it (SC may also fail and "
        "write nothing), AMOs return the old value, CBO.ZERO zeroes it. Not masked: an access fault (load for loads "
        "and LR, store/AMO otherwise), nothing written.",
    )
    sweep(t, mode, ALL_KINDS, [pa(tag=T7), pa(tag=0xA5C3 << 48, q=16)], vals=(3, 2))
    pm_off(t, mode)
    return t


def fetch_case(t: MemTest, mode: str, tag: int, q: int, p: int, space: str = "pa") -> None:
    """jalr to the tagged address of a landing pad: the fetch is not masked, so it faults (and the pad, which sets
    x7, does not run)."""
    land, over = t.label("pad"), t.label("over")
    t.emit(f"j {over}")
    t.emit(f"{land}:", 0)
    t.emit("li x7, 0xBAD")
    t.emit("jalr x0, 0(x1)")
    t.emit(f"{over}:", 0)
    good = MUT == "fetch_masked" and p and (tag & ((1 << (64 - p)) - 1)) == 0
    t.la("x8", land)
    t.emit("mv x6, x8")
    t.emit(f"li x9, {hex(~tagmask(q) & M64)}", 6)
    t.emit("and x6, x6, x9")
    t.emit(f"li x9, {hex(tag)}", 6)
    t.emit("or x6, x6, x9")
    t.emit("li x7, 0")
    d = f"jalr to the {space.upper()} of a code label with bits 63:{64 - q} = {hex(tag >> (64 - q))}, PMLEN={p}"
    cause = 12 if space == "va" else 1

    def pred(lab: str) -> Callable[[], None]:
        def f() -> None:
            t.emit("AI_LOG(x15, TRAPLOG_TVAL)", 10)
            t.emit("xor x15, x15, x8")
            t.emit("snez x15, x15")
            t.check_bool("x15", lab, f"{d}: xtval is not the masked target (the fetch address is not masked)")
            t.emit("AI_LOG(x15, TRAPLOG_EPC)", 10)
            t.emit("xor x15, x15, x8")
            t.emit("snez x15, x15")
            t.check_bool("x15", lab, f"{d}: xepc is not the masked target")

        return f

    window(t, mode, ["jalr x1, 0(x6)"], "ok" if good else cause, d, None if good else pred, epc=False)
    lab = t.label("pad")
    t.emit(f"{lab}:", 0)
    t.check("x7", 0xBAD if good else 0, lab, f"{d}: the landing pad {'runs' if good else 'does not run'}")


def b_not_implicit(ext: str, mode: str) -> MemTest:
    t = mk(ext, "pm_not_apply_implicit", mode)
    va = mode == "S"
    describe(
        t,
        "pm_not_apply_implicit",
        context=f"{MODE_NAME[mode]}. The instruction-fetch half of the rule: a jalr to a tagged code address must "
        "fetch from that (invalid) address and fault, even where a data access to the same address would be "
        "masked. A landing pad at the untagged address records whether it ran. The trap handler resumes at ra. "
        + (
            "With Sv39 (when supported) the tagged target is a non-canonical VA (instruction page fault). "
            if va
            else ""
        )
        + "Page-table walks are tested in Sspm/pm_cpu_only. "
        + DISPATCH_NOTE,
        issues=ISSUE_2423,
        plan="1. For PMM written 11 and 10 (and 00 as a control): jalr to the landing pad with the top 7 bits all "
        "ones and with bits 63:48 = 0xA5C3: an instruction access fault (1), the pad does not run, and neither "
        "xepc nor xtval is the masked target.\n"
        + ("2. With Sv39 identity-mapped: the same, with an instruction page fault (12).\n" if va else ""),
    )

    def body(space: str) -> None:
        for val in (3, 2, 0):
            gated(t, lambda val=val: ctrl_write(t, mode, val, 0))
            gated(
                t,
                lambda: dispatch(
                    t, 0, lambda p: [fetch_case(t, mode, tg, q, p, space) for tg, q in ((T7, 7), (0xA5C3 << 48, 16))]
                ),
            )

    body("pa")
    if va:
        with_satp(t, "sv39", LEAF, lambda R, vb: body("va"))
    pm_off(t, mode)
    return t


def mis_case(t: MemTest, mode: str, a: Addr, p: int, store: bool, cross: bool) -> None:
    """A misaligned ld/sd of a tagged address (within page A at +3, or crossing from A into B at +4093/+4092)."""
    off = (4092 if store else 4093) if cross else 3
    b = a.moved(off)
    pe = p
    good = b.ok(pe)
    second = cross and MUT == "misaligned_second_unmasked" and p > 0
    if second:
        good = False
    if store:
        t.load("x7", 0, "zero")
        t.la("x9", "ai_pg_A+4088")
        t.emit("sd x7, 0(x9)")
        t.la("x9", "ai_pg_B")
        t.emit("sd x7, 0(x9)  // page B")
        t.load("x8", 0x1122334455667788, "value to store")
    if good:
        # the same access untagged first: masking must not change whether it traps
        u = Addr(b.page, b.off, b.rep() & tagmask(b.q), b.q, b.space, b.vabits, b.R, b.hi, b.const)
        u.emit(t, None)
        du = f"untagged misaligned {'sd' if store else 'ld'} of {u}"
        exp_u = ["ok", 6 if store else 4, 7 if store else 5]
        prx = pred_exact_cross if cross else pred_exact
        window(
            t,
            mode,
            [("sd x8, 0(x6)" if store else "ld x7, 0(x6)")],
            exp_u,
            du,
            lambda lab: prx(t, lab, du),
            save_count=True,
        )
        save(t, "x9", 5)
        if store:
            t.la("x9", "ai_pg_A+4088")
            t.emit("sd x0, 0(x9)")
            t.la("x9", "ai_pg_B")
            t.emit("sd x0, 0(x9)  // page B")
    b.emit(t, None)  # x1 = the untagged address: the transformed address when the tag is masked
    d = f"misaligned {'sd' if store else 'ld'} of {b}{' (crosses into page B)' if cross else ''}, PMLEN={p}"
    ins = "sd x8, 0(x6)" if store else "ld x7, 0(x6)"
    sp = b.space
    if good:
        exp = ["ok", 6 if store else 4, 7 if store else 5]
        pr = lambda lab: (pred_exact_cross if cross else pred_exact)(t, lab, d)
    else:
        exp = [6 if store else 4, 7 if store else 5] if sp == "pa" else [6 if store else 4, 15 if store else 13]
        pr = lambda lab: pred_not(t, lab, d)
    window(t, mode, [ins], exp, d, pr, save_count=True)

    def notrap() -> None:
        lab = t.label("misal")
        t.emit(f"{lab}:", 0)
        if store:
            t.la("x6", "ai_pg_A+4088")
            t.emit("ld x7, 0(x6)")
            t.check("x7", 0x5566778800000000, lab, f"{d}: the first part landed in A")
            t.la("x6", "ai_pg_B")
            t.emit("ld x7, 0(x6)")
            t.check("x7", 0x11223344, lab, f"{d}: the second part landed in B")
        else:
            if cross:
                v = int.from_bytes(TAIL.to_bytes(8, "little")[5:] + sig(2).to_bytes(8, "little")[:5], "little")
            else:
                from spmlib import a_bytes

                v = int.from_bytes(a_bytes()[3:11], "little")
            t.check("x7", v, lab, f"{d}: reads the untagged bytes")

    if good:
        lab = t.label("same")
        t.emit(f"{lab}:", 0)
        restore(t, 5, "x8")
        t.emit("xor x8, x8, x9")
        t.check("x8", 0, lab, f"{d}: traps exactly when the untagged access does (same limitations as without masking)")
        t.either("x9", lambda: None, notrap)
    if store:
        t.comment("restore the tail of A and the head of B")
        t.la("x6", "ai_pg_A+4088")
        t.load("x7", TAIL, "A tail")
        t.emit("sd x7, 0(x6)")
        t.la("x6", "ai_pg_B")
        t.load("x7", sig(2), "B signature")
        t.emit("sd x7, 0(x6)")


def b_misaligned(ext: str, mode: str) -> MemTest:
    t = mk(ext, "pm_misaligned_equivalence", mode)
    va = mode == "S"
    describe(
        t,
        "pm_misaligned_equivalence",
        context=f"{MODE_NAME[mode]}. Misaligned accesses may complete, or raise an address-misaligned or "
        "access fault, exactly as without pointer masking (the hart's choice; the test does not assume one). When "
        "the tag is masked and the access completes, every byte comes from (or goes to) the untagged location, "
        "including the part in the next page; when it traps, xtval is 0 or the transformed (valid) address. When "
        "the tag is not masked, the access must trap. Pages A and B are adjacent. " + DISPATCH_NOTE,
        plan="1. For PMM written 11 and 10: ld at A+3, ld at A+4093 (crossing into B) and sd at A+4092 (crossing), "
        "with the top 7 bits all ones and with bits 63:48 = 0xA5C3. When the tag is masked, the untagged access "
        "runs first, and the tagged one must trap exactly when it did; a trap's xtval is 0, the address, or (crossing) "
        "the start of page B.\n"
        + (
            "2. The same through Sv39 (when supported), identity-mapped and through the high-half alias.\n"
            if va
            else ""
        ),
    )

    def body(addrs: list[Addr]) -> None:
        for val in (3, 2):
            gated(t, lambda val=val: ctrl_write(t, mode, val, 0))
            for a in addrs:
                for st, cr in ((False, False), (False, True), (True, True)):
                    gated(t, lambda a=a, st=st, cr=cr: dispatch(t, 0, lambda p: mis_case(t, mode, a, p, st, cr)))

    body([pa(tag=T7), pa(tag=0xA5C3 << 48, q=16)])
    if va:
        with_satp(
            t,
            "sv39",
            LEAF,
            lambda R, vb: body([Addr("A", 0, T7, 7, "va", vb, R), Addr("A", 0, 0x55 << 57, 7, "va", vb, R, hi=True)]),
        )
    pm_off(t, mode)
    return t


def mxr_set(t: MemTest, on: bool) -> None:
    """mstatus/sstatus.MXR from the current mode; x5 = 1 when it reads back as set (MXR is read-only 0 without S)."""
    csr = {"M": "mstatus", "S": "sstatus", "U": "sstatus"}[t.cur]
    t.comment(f"MXR = {int(on)}")
    if t.cur == "U":
        with t.only_if(S_):
            csr_op(t, "SET" if on else "CLEAR", "sstatus", imm=MXR)
            csr_read(t, "sstatus", "x5")
        with t.only_if(NOS):
            csr_op(t, "SET" if on else "CLEAR", "mstatus", imm=MXR)
            csr_read(t, "mstatus", "x5")
    else:
        csr_op(t, "SET" if on else "CLEAR", csr, imm=MXR)
        csr_read(t, csr, "x5")
    t.emit("srli x5, x5, 19")
    t.emit("andi x5, x5, 1")


def mxr_peff(mode: str) -> MxrPeff:
    """PMLEN that applies with MXR in effect: none for S/U effective modes, unchanged for M (issue 3313)."""

    def f(p: int, ks: list[str]) -> dict[str, int]:
        out = {}
        for k in ks:
            store = KINDS[k][1] != "load"
            if mode in ("M", "MPRV_M"):
                out[k] = 0 if MUT == "mxr_disables_m" else p
            elif MUT == "mxr_ignored" or (MUT == "mxr_loads_only" and store):
                out[k] = p
            else:
                out[k] = 0
        return out

    return f


def b_mxr(ext: str, mode: str) -> MemTest:
    t = mk(ext, "pm_mxr_exception", mode)
    m = mode == "M"
    describe(
        t,
        "pm_mxr_exception",
        context=f"{MODE_NAME[mode]} accesses. "
        + (
            "MXR is never in effect for an access whose effective privilege mode is M, so M-mode pointer masking "
            "still applies with mstatus.MXR=1. "
            if m
            else "With MXR=1 pointer masking does not apply to S/U accesses, even with Bare translation (MXR has no "
            "permission effect there). The rule names every explicit access, so stores and AMOs are unmasked too. "
        )
        + "MXR is read-only zero without S-mode; the test reads it back and expects masking when it did not "
        "stick. " + DISPATCH_NOTE,
        issues=ISSUE_3313,
        plan="1. MXR=1. For PMM written 11 and 10: ld, sd"
        + (" and amoadd.d (Zaamo)" if mode != "U" else "")
        + " of page A with the top 7 bits all ones and with bits 63:48 = 0xA5C3: "
        + (
            "masked as usual (MXR is read-only zero without S, which gives the same expectation)."
            if m
            else "not masked: access faults"
            + (" (masked when MXR does not stick: read-only zero without S)" if mode == "U" else "")
            + "."
        )
        + "\n2. MXR=0, PMM written 11: ld and sd are masked again (transition back)."
        + (
            "\n3. Sv39 (when supported): the same with MXR=1 through the identity map and the high-half alias."
            if mode == "S"
            else ""
        ),
    )
    kinds = ["ld", "sd", "amoadd.d"]
    addrs = [pa(tag=T7), pa(tag=0xA5C3 << 48, q=16)]
    mxr_set(t, True)
    if mode == "U":
        t.either(
            "x5",
            lambda: sweep_inline(t, mode, kinds, addrs, mxr_peff(mode)),
            lambda: sweep_inline(t, mode, kinds, addrs, None),
        )
    else:  # MXR is writable whenever S exists; for M the expectation does not depend on it
        sweep(t, mode, kinds, addrs, vals=(3, 2), peff=mxr_peff(mode))
    mxr_set(t, False)
    sweep(t, mode, ["ld", "sd"], addrs, vals=(3,))
    pm_off(t, mode)
    return t


def sweep_inline(t: MemTest, mode: str, kinds: list[str], addrs: list[Addr], peff: Peff | None) -> None:
    """sweep() without only_if groups (for use inside a run-time branch): conditional kinds are dropped."""
    ks = [k for k in kinds if KINDS[k][4] is None]
    sweep(t, mode, ks, addrs, vals=(3, 2), peff=peff)
    del kinds


# ---------------------------------------------------------------- S-mode (Sspm) virtual-memory tests
def b_ignore_va_s(ext: str = "Sspm") -> MemTest:
    t = mk(ext, "pm_ignore_va", "S")
    describe(
        t,
        "pm_ignore_va",
        context="S-mode under satp Sv39, Sv48 and Sv57, each when supported (satp.MODE is probed: an unsupported "
        "MODE leaves satp unchanged). Each table identity-maps the root-level page holding the test image and maps "
        "the last root-level page (the top of the high half) to the same page, so page A is reachable at its "
        "physical address and at a high-half alias. " + TRANSFORM_NOTE + " Sign extension is observable: a "
        "high-half address whose top bits are cleared (or hold a tag) is masked back to the alias only by sign "
        "extension; zero extension makes it non-canonical. With Sv57 and PMLEN=16 the masked bits 56:48 select "
        "the root entry, so they must really be replaced, not just ignored by the validity check. A valid "
        "unmapped VA (root entry 5) gives a page fault whose xtval must be 0 or exactly the transformed VA.",
        issues=ISSUE_1944,
        plan="1. For each supported scheme and PMM written 11, 10 and 00: ld of page A through the identity map with "
        "the top 7 bits all ones, 0x2A, bits 63:48 = 0xA5C3, and bit 56 alone; ld of the high-half alias with "
        "bits 63:57 = 0 and 0x55, bit 63 alone, and bits 63:48 = 0xFF7F.\n"
        "2. ld of the unmapped VA tagged in the top 7 and top 16 bits: page fault, xtval 0 or the transformed VA.\n"
        "3. sd of two of the addresses, checked through the identity map.",
    )
    for scheme in ("sv39", "sv48", "sv57"):

        def body(R: int, vb: int, scheme: str = scheme) -> None:
            addrs = va_set(scheme, R, vb)
            if scheme != "sv57":
                addrs += va_unmapped(R, vb)
            sweep(t, "S", ["ld"], addrs)
            sweep(t, "S", ["sd"], [addrs[0], addrs[5]], vals=(3, 2))

        with_satp(t, scheme, LEAF, body)
    pm_off(t, "S")
    return t


def b_explicit_va(ext: str = "Sspm") -> MemTest:
    t = mk(ext, "pm_explicit_accesses", "S")
    describe(
        t,
        "pm_explicit_accesses",
        context="S-mode under Sv39 (when supported): every class of explicit access through "
        "translation, where masking happens before the TLB lookup. Classes: integer loads and stores of every "
        "width, AMOs, LR/SC, FP and vector loads/stores and CBO.ZERO (each when its extension is supported). The "
        "note's exceptions (SFENCE.*, HFENCE.*, SINVAL.*, HINVAL.*) are not memory accesses whose effect depends "
        "on the address being valid, so they are not tested. " + DISPATCH_NOTE,
        issues=ISSUE_1844,
        plan="1. With Sv39, for PMM written 11 and 10: every class accesses page A through the identity map with the "
        "top 7 bits all ones, and through the high-half alias with bits 63:57 = 0x55: the access reaches page A.\n"
        "2. Without Sv39 the file checks nothing (the Bare classes are pm_apply_explicit).",
    )

    pt = SvPT(t, "satp_sv39", "sv39")
    pt.identity(LEAF)
    pt.hi_alias("A", LEAF)
    satp_probe(t, pt)  # satp stays Sv39 when supported
    save(t, "x5", 3)
    va = [Addr("A", 0, T7, 7, "va", 39, 30), Addr("A", 0, 0x55 << 57, 7, "va", 39, 30, hi=True)]
    # a run-time branch cannot hold #if blocks, so each chunk branches on the saved probe result (gated)
    GATE.append(3)
    sweep(t, "S", ALL_KINDS, va, vals=(3, 2))
    GATE.pop()
    satp_off(t)
    pm_off(t, "S")
    return t


def b_cpu_only(ext: str = "Sspm") -> MemTest:
    t = mk(ext, "pm_cpu_only", "S")
    describe(
        t,
        "pm_cpu_only",
        context="S-mode under Sv39 (when supported). The page-table-walk part: root entry 6 points to a level-1 "
        "table at its physical address with bit 48 set, which a walk that (wrongly) applied PMLEN=16 masking "
        "would strip. A correct walk reads that address, which has no memory, and raises an access fault of the "
        "original access type. Root entry 7 points to the same table at its real address, as a control that the "
        "table maps page A. IOMMU and device accesses are outside a hart test.",
        plan="1. Build: root[7] -> L1 (real address), root[6] -> L1 | 2^48; L1 maps A's 2 MiB megapage.\n"
        "2. For PMM written 11, 10 and 00: ld through root 7 reads page A (untagged, and tagged in the top 7 bits); "
        "ld through root 6 raises a load access fault (5), untagged and tagged.",
    )
    pt = SvPT(t, "satp_sv39", "sv39")
    pt.identity(LEAF)
    l1 = t.pt_table("ptw_l1")
    t.comment("L1[(A >> 21) & 511] = megapage leaf for A's 2 MiB region")
    t.la("x7", "ai_pg_A")
    t.emit("srli x7, x7, 21")
    t.emit("andi x6, x7, 511")
    t.emit("slli x7, x7, 19")
    t.emit(f"ori x7, x7, {LEAF}")
    t.emit("slli x6, x6, 3")
    t.la("x8", l1)
    t.emit("add x8, x8, x6")
    t.emit("sd x7, 0(x8)")
    for idx, hi in ((7, 0), (6, 1 << 48)):
        t.comment(f"root[{idx}] -> L1{' | 2^48' if hi else ''}")
        t.la("x7", l1)
        if hi:
            t.emit(f"li x9, {hex(hi)}", 6)
            t.emit("or x7, x7, x9")
        t.emit("srli x7, x7, 12")
        t.emit("slli x7, x7, 10")
        t.emit("ori x7, x7, 1")
        t.la("x8", pt.root)
        t.emit(f"sd x7, {idx * 8}(x8)")
    satp_probe(t, pt)

    def body() -> None:
        for val in (3, 2, 0):
            ctrl_write(t, "S", val, 0)

            def run(p: int) -> None:
                for idx in (7, 6):
                    for tag in (0, T7, 0xA5C3 << 48):
                        q = 16 if tag >> 48 == 0xA5C3 else 7
                        masked = tag == 0 or p >= q
                        if not masked:
                            continue  # the access itself is not masked: a page fault, tested elsewhere
                        ok = idx == 7 or (MUT == "ptw_masked" and p == 16)
                        d = f"ld through root entry {idx}, top {q} bits {hex(tag >> (64 - q))}, PMLEN={p}"
                        t.la("x6", "ai_pg_A")
                        t.emit(f"li x9, {hex((1 << 30) - 1)}", 6)
                        t.emit("and x6, x6, x9")
                        t.emit(f"li x9, {hex((idx << 30) | tag)}", 6)
                        t.emit("or x6, x6, x9")
                        t.emit("mv x1, x6")
                        window(t, "S", ["ld x7, 0(x6)"], "ok" if ok else 5, d)
                        if ok:
                            lab = t.label("ptw")
                            t.emit(f"{lab}:", 0)
                            t.check("x7", sig(1), lab, f"{d}: reads page A")

            dispatch(t, 0, run)

    t.either("x5", body, lambda: None)
    satp_off(t)
    pm_off(t, "S")
    return t


def b_csr_hw_apply(ext: str = "Sspm") -> MemTest:
    t = mk(ext, "pm_csr_hw_apply", "S")
    describe(
        t,
        "pm_csr_hw_apply",
        context="S-mode under Sv39 (and Sv48), when supported. A valid VA with no mapping (root entry 5) is "
        "accessed with tags; when the tag is masked the transformed VA is valid, so the page fault must write stval "
        "= 0 or exactly that VA (never the tagged address). When the tag is not masked, the address is invalid and "
        "stval may hold 0, it, or another invalid address, but not the masked VA. Loads, stores and AMOs. Bare "
        "misaligned faults are in pm_misaligned_equivalence.",
        plan="1. For each supported scheme and PMM written 11, 10, 00: ld, sd and amoadd.d of the unmapped VA with "
        "the top 7 bits all ones and with bits 63:48 = 0x5A5A.",
    )
    for scheme in ("sv39", "sv48"):

        def body(R: int, vb: int) -> None:
            sweep(t, "S", ["ld", "sd"], va_unmapped(R, vb))

        with_satp(t, scheme, LEAF, body)
    pm_off(t, "S")
    return t


SV_EXTREMES = {
    "sv39": [0x3F_FFFF_F000, 0xFFFF_FFC0_0000_0000, 0xFFFF_FFFF_FFFF_F000],
    "sv48": [0x7FFF_FFFF_F000, 0xFFFF_8000_0000_0000],
    "sv57": [0xFF_FFFF_FFFF_F000, 0xFF00_0000_0000_0000],
}


def csr_exact(t: MemTest, c: str, v: int, p: int, note: str) -> None:
    """Software write of the valid address v to address CSR c reads back exactly (it is not masked, and the WARL
    width covers every valid address whatever PMLEN is)."""
    lab = t.label("csrv")
    t.emit(f"li x7, {hex(v)}", 6)
    t.emit(f"{lab}:", 0)
    t.emit(f"csrw {hex(CSRN[c])}, x7  // {c}")
    t.emit(f"csrr x8, {hex(CSRN[c])}")
    masked = v & ((1 << (64 - p)) - 1) if p else v
    exp = masked if (MUT == "csr_write_masked" and p) else v
    t.check("x8", exp, lab, f"{c} written with the valid address {hex(v)} (PMLEN={p}) reads it back{note}")


def csr_va_body(t: MemTest, mode: str, csrs: list[str], schemes: list[str], bare: list[int], rule: str) -> None:
    """For PMM written 11, 10, 00: bare values always; each scheme's extreme valid VAs when satp supports it."""
    for scheme in schemes:
        pt = SvPT(t, f"probe_{scheme}", scheme)
        pt.identity(LEAF)  # S-mode keeps fetching through satp until the probe turns it off
        satp_probe(t, pt)
        satp_off(t)
        save(t, "x5", 8 + schemes.index(scheme))
    for val in (3, 2, 0):
        gated(t, lambda val=val: ctrl_write(t, mode, val, 0))
        gated(t, lambda: dispatch(t, 0, lambda p: [csr_exact(t, c, v, p, "") for c in csrs for v in bare]))
        for i, scheme in enumerate(schemes):
            GATE.append(8 + i)
            gated(
                t,
                lambda scheme=scheme: dispatch(
                    t,
                    0,
                    lambda p: [csr_exact(t, c, v, p, f" ({scheme} valid)") for c in csrs for v in SV_EXTREMES[scheme]],
                ),
            )
            GATE.pop()
    del rule


def b_no_csr_sw(ext: str, mode: str) -> MemTest:
    t = mk(ext, "pm_no_csr_sw", mode)
    csrs = ["mepc", "mtval"] if mode == "M" else ["sepc", "stval"]
    describe(
        t,
        "pm_no_csr_sw",
        context=f"{MODE_NAME[mode]}, the mode that owns {' and '.join(csrs)}. These WARL CSRs must hold every valid "
        "address exactly; a tagged value is an invalid address, which they need not hold, so only valid addresses "
        "that masking would change are used: negative virtual addresses (a masking write would zero-extend or "
        "truncate their top bits), valid when satp supports the scheme (probed"
        + ("; M-mode needs S for that" if mode == "M" else "")
        + "). No trap occurs between the write and the read. "
        + DISPATCH_NOTE,
        plan=f"1. Probe satp Sv39, Sv48, Sv57. For PMM written 11, 10 and 00: write {' and '.join(csrs)} with each "
        "supported scheme's extreme valid VAs (e.g. 0xFFFFFFC000000000, 0xFFFF800000000000, 0xFF00000000000000); "
        "each reads back exactly.",
    )
    with cond(t, S_ if mode == "M" else None):
        csr_va_body(t, mode, csrs, ["sv39", "sv48", "sv57"], [], "pm_no_csr_sw")
    pm_off(t, mode)
    return t


def b_warl_unaffected(ext: str, mode: str) -> MemTest:
    t = mk(ext, "pm_warl_unaffected", mode)
    csrs = ["mepc", "mtval"] if mode == "M" else ["sepc", "stval"]
    describe(
        t,
        "pm_warl_unaffected",
        context=f"{MODE_NAME[mode]}. {' and '.join(csrs)} must hold every valid address whatever PMM is: the "
        "implemented WARL bits do not shrink to XLEN-PMLEN when masking is enabled. Sv48 and Sv57 extremes need "
        "more than 48 (57) bits, so a register narrowed to XLEN-PMLEN loses them; each scheme is probed through "
        "satp" + (" (M-mode needs S for that)" if mode == "M" else "") + ". " + DISPATCH_NOTE,
        plan="1. For PMM written 11, 10 and 00: write the image address of page A (a valid physical address) and, "
        "for each supported scheme, its extreme valid VAs (Sv39: 0x3FFFFFF000, 0xFFFFFFC000000000; Sv48: "
        "0x7FFFFFFFF000, 0xFFFF800000000000; Sv57: 0xFFFFFFFFFFF000, 0xFF00000000000000) to "
        f"{' and '.join(csrs)}; each reads back exactly.",
    )
    for val in (3, 2, 0):
        ctrl_write(t, mode, val, 0)

        def run(p: int) -> None:
            for c in csrs:
                lab = t.label("img")
                t.la("x7", "ai_pg_A")
                t.emit(f"{lab}:", 0)
                t.emit(f"csrw {hex(CSRN[c])}, x7")
                t.emit(f"csrr x8, {hex(CSRN[c])}")
                t.emit("xor x8, x8, x7")
                t.check("x8", 0, lab, f"{c} holds the physical address of page A (PMLEN={p})")

        dispatch(t, 0, run)
    with cond(t, S_ if mode == "M" else None):
        csr_va_body(t, mode, csrs, ["sv39", "sv48", "sv57"], [], "pm_warl_unaffected")
    pm_off(t, mode)
    return t


def b_mxr_s_paged(t: MemTest) -> None:
    """Sv39 part of the S-mode MXR test."""

    def body(R: int, vb: int) -> None:
        addrs = [Addr("A", 0, T7, 7, "va", vb, R), Addr("A", 0, 0x55 << 57, 7, "va", vb, R, hi=True)]
        # MXR is writable whenever S exists, so no probe is needed here
        gated(t, lambda: mxr_set(t, True))
        sweep(t, "S", ["ld", "sd"], addrs, vals=(3, 2), peff=mxr_peff("S"))
        gated(t, lambda: mxr_set(t, False))

    with_satp(t, "sv39", LEAF, body)


def b_mode_only(ext: str = "Sspm") -> MemTest:
    t = mk(ext, "pm_mode_only_dependency", "S")
    describe(
        t,
        "pm_mode_only_dependency",
        context="S-mode under Sv39 (when supported) and Bare. Software may treat the top bit as a user/kernel "
        "marker; pointer masking does not: the same S-mode setting applies to positive- and negative-half "
        "addresses, with bit 63 set or clear. " + DISPATCH_NOTE,
        plan="1. Bare: ld of page A with bits 63:57 = 0x40 (bit 63 only) and 0x3F (bit 63 clear).\n"
        "2. Sv39, for PMM written 11 and 10: ld through the identity map (a 'user' address) and the high-half alias "
        "(a 'kernel' address), each with bit 63 set and clear in the tag.",
    )
    sweep(t, "S", ["ld"], [pa(tag=0x40 << 57), pa(tag=0x3F << 57)], vals=(3, 2))

    def body(R: int, vb: int) -> None:
        v = {"space": "va", "vabits": vb, "R": R}
        addrs = [
            Addr("A", 0, 0x40 << 57, 7, **v),
            Addr("A", 0, 0x3F << 57, 7, **v),
            Addr("A", 0, 0x40 << 57, 7, hi=True, **v),
            Addr("A", 0, 0x3F << 57, 7, hi=True, **v),
        ]
        sweep(t, "S", ["ld"], addrs, vals=(3, 2))

    with_satp(t, "sv39", LEAF, body)
    pm_off(t, "S")
    return t


def b_pmlen_values(ext: str = "Sspm") -> MemTest:
    t = mk(ext, "pmlen_supported_values", "S")
    describe(
        t,
        "pmlen_supported_values",
        context="S-mode, Bare. PMM=10 must mask exactly bits 63:57 and PMM=11 exactly bits 63:48. " + DISPATCH_NOTE,
        plan="1. For PMM written 10 and 11: ld of page A with single bits 63, 57, 56, 48 and 47 set (bit 47 is never "
        "masked), and with bits 56:48 = 0x155.",
    )
    addrs = pa_boundary()[:5] + [pa(tag=1 << 47, q=17)]
    sweep(t, "S", ["ld"], addrs, vals=(2, 3))
    pm_off(t, "S")
    return t


def b_reserved(ext: str = "Sspm") -> MemTest:
    t = mk(ext, "pmlen_future_reserved", "S")
    describe(
        t,
        "pmlen_future_reserved",
        context="PMM=01 is reserved, so it is not a legal value of the WARL field: writing it leaves one of 00, 10 "
        "and 11, and the hart behaves as that value says. Tested on menvcfg.PMM through T-SBI (S-mode's setting) "
        "and, with Ssnpm, senvcfg.PMM (U-mode's).",
        plan="1. Write menvcfg.PMM = 01 (from 11 and from 00): it reads 00, 10 or 11, and S-mode ld of page A tagged "
        "in the top 7 bits and in bits 63:48 behaves as the value read.\n"
        "2. With Ssnpm: the same for senvcfg.PMM and U-mode.",
    )
    for start in (3, 0):
        ctrl_write(t, "S", start, 0)
        pmm_write(t, "menvcfg", 1)
        rlab = t.label("rsv")
        t.emit(f"{rlab}:", 0)
        t.check(
            "x8",
            1 if MUT == "reserved_reads_back" else [0, 2, 3],
            rlab,
            f"menvcfg.PMM written 01 after {start:02b} reads a legal value",
        )
        save(t, "x8", 0)
        if MUT == "reserved_reads_back":
            continue
        sweep(t, "S", ["ld"], pa_basic(), write=False)
    with t.only_if("defined(SSNPM_SUPPORTED)"):
        for start in (3, 0):
            ctrl_write(t, "U", start, 0)
            pmm_write(t, "senvcfg", 1)
            rlab = t.label("rsv")
            t.emit(f"{rlab}:", 0)
            t.check(
                "x8",
                1 if MUT == "reserved_reads_back" else [0, 2, 3],
                rlab,
                f"senvcfg.PMM written 01 after {start:02b} reads a legal value",
            )
            save(t, "x8", 0)
            if MUT != "reserved_reads_back":
                sweep(t, "U", ["ld"], pa_basic(), write=False)
        pm_off(t, "U")
    pm_off(t, "S")
    return t


# ---------------------------------------------------------------- encodings (WARL)
def b_enc(ext: str, rule: str, csr: str, boot: str, req: list[str], h: bool = False) -> MemTest:
    t = new(sd(ext), rule, req, boot)
    describe(
        t,
        rule,
        context=f"{csr}.PMM is bits 33:32 (RV64). The field is WARL: the legal values are 00, 10 and 11 (01 is "
        "reserved). A write of a legal, supported value reads back exactly; any other write leaves a legal value. "
        "The extension provides pointer masking, so at least one of 10 and 11 is supported. Other fields of the "
        "register are not changed by PMM writes. CSR forms: csrrw (read-modify-write), csrrs and csrrc; the "
        "immediate forms cannot reach bits 33:32.",
        plan="1. Clear PMM: reads 00. Write 10 and 11 (csrrs after a clear): each reads 00, 10 or 11; if 10 reads back "
        "as 11, 11 is supported and must read 11; if 11 reads 10, 10 must read 10; not both 00.\n"
        "2. Write 01: reads 00, 10 or 11.\n"
        "3. csrrw of the whole register with PMM = 11 then 10 and the other fields unchanged: PMM as in 1, other "
        "bits unchanged; csrrs/csrrc return the previous value.",
    )
    pmm_write(t, csr, 0)
    lab = t.label("enc")
    t.emit(f"{lab}:", 0)
    t.check("x8", 0, lab, f"{csr}.PMM cleared reads 00")
    pmm_write(t, csr, 2, rd="x6")
    pmm_write(t, csr, 3, rd="x7")
    lab = t.label("enc")
    t.emit(f"{lab}:", 0)
    t.check("x6", [0, 2, 3], lab, f"{csr}.PMM written 10 reads a legal value")
    t.check("x7", [0, 2, 3], lab, f"{csr}.PMM written 11 reads a legal value")
    t.comment("consistency: r10 == 3 implies r11 == 3; r11 == 2 implies r10 == 2; not both 0")
    t.emit("xori x8, x6, 3")
    t.emit("snez x8, x8  // r10 != 3")
    t.emit("xori x9, x7, 3")
    t.emit("seqz x9, x9  // r11 == 3")
    t.emit("or x8, x8, x9")
    t.check_bool("x8", lab, f"{csr}.PMM: if writing 10 reads 11, 11 is legal and writing 11 reads 11")
    t.emit("xori x8, x7, 2")
    t.emit("snez x8, x8  // r11 != 2")
    t.emit("xori x9, x6, 2")
    t.emit("seqz x9, x9  // r10 == 2")
    t.emit("or x8, x8, x9")
    t.check_bool("x8", lab, f"{csr}.PMM: if writing 11 reads 10, 10 is legal and writing 10 reads 10")
    t.emit("or x8, x6, x7")
    t.emit("snez x8, x8")
    if MUT == "no_pmlen_required":
        t.check("x8", 0, lab, f"{csr}.PMM supports no nonzero value")
    else:
        t.check_bool("x8", lab, f"{csr}.PMM: at least one of 10 and 11 is supported (the extension provides masking)")
    pmm_write(t, csr, 1)
    lab = t.label("enc")
    t.emit(f"{lab}:", 0)
    t.check(
        "x8",
        1 if MUT == "reserved_reads_back" else [0, 2, 3],
        lab,
        f"{csr}.PMM written 01 (reserved) reads a legal value",
    )
    # csrrw/csrrs/csrrc forms and the other fields
    for val in (3, 2):
        c = hex(CSRN[csr])
        lab = t.label("rw")
        t.emit(f"csrr x6, {c}")
        t.emit(f"li x9, {hex(~PMM_M & M64)}", 6)
        t.emit("and x7, x6, x9  // other fields")
        t.emit(f"li x9, {hex(val << PMM_SH)}", 6)
        t.emit("or x8, x7, x9")
        t.emit(f"{lab}:", 0)
        t.emit(f"csrrw x9, {c}, x8")
        t.emit(f"csrr x8, {c}")
        t.emit(f"li x9, {hex(~PMM_M & M64)}", 6)
        t.emit("and x9, x8, x9")
        t.emit("xor x9, x9, x7")
        t.check("x9", 0, lab, f"csrrw of {csr} with PMM={val:02b}: the other fields are unchanged")
        pmm_field(t, "x8")
        t.check("x8", [0, 2, 3], lab, f"csrrw of {csr} with PMM={val:02b}: PMM reads a legal value")
        lab = t.label("rs")
        t.emit(f"csrr x6, {c}")
        t.emit(f"li x7, {hex(PMM_M)}", 6)
        t.emit(f"{lab}:", 0)
        t.emit(f"csrrc x8, {c}, x7")
        t.emit("xor x8, x8, x6")
        t.check("x8", 0, lab, f"csrrc of {csr}.PMM returns the previous value")
        t.emit(f"csrr x8, {c}")
        pmm_field(t, "x8")
        t.check("x8", 0, lab, f"csrrc of {csr}.PMM clears it")
        t.emit(f"li x7, {hex(val << PMM_SH)}", 6)
        t.emit(f"csrrs x8, {c}, x7")
        pmm_field(t, "x8")
        t.check("x8", 0, lab, f"csrrs of {csr}.PMM returns the previous (cleared) value")
        t.emit(f"csrr x8, {c}")
        pmm_field(t, "x8")
        t.check("x8", [0, 2, 3], lab, f"csrrs of {csr}.PMM={val:02b} reads a legal value")
    pmm_write(t, csr, 0)
    del h
    return t


# ---------------------------------------------------------------- read-only zero when absent / RV32
def probe_csr(t: MemTest, csr: str) -> None:
    """x5 = 1 if csr exists (a read does not trap), else 0. The window accepts no trap or illegal instruction."""
    c = CSRN[csr]
    window(t, t.cur, [f"csrr x7, {hex(c)}  // {csr}"], ["ok", 2], f"read of {csr}", save_count=True)
    t.emit("seqz x5, x9")


def ro0_case(t: MemTest, csr: str, bits: int, desc: str) -> None:
    lab = t.label("ro0")
    c = hex(CSRN[csr])
    t.emit(f"li x7, {hex(bits)}", 6)
    t.emit(f"{lab}:", 0)
    t.emit(f"csrs {c}, x7  // {csr}")
    t.emit(f"csrr x8, {c}")
    t.emit("and x8, x8, x7")
    t.check(
        "x8",
        bits if MUT == "rv32_pmm_writable" and csr.endswith("h") else 0,
        lab,
        f"{desc}: {csr} PMM bits read 0 after setting them",
    )
    t.emit(f"csrc {c}, x7")


def b_rdonly0(ext: str, rule: str, csr: str, req: list[str], boot: str, umode_check: bool = True) -> MemTest:
    t = new(sd(ext), rule, req, boot, forbidden=[ext], rv64=False)
    hcsr = csr + "h"
    describe(
        t,
        rule,
        context=f"This test runs on harts without {ext}, including every RV32 hart (pointer masking is RV64-only, "
        f"so an RV32 hart never has {ext}); it therefore requires only the modes it uses, with "
        f"FORBIDDEN_EXTENSIONS: [{ext}]. {csr} may itself be absent; the test probes it with a read in a trap window "
        f"(illegal instruction or not). On RV64 PMM is bits 33:32 of {csr}; on RV32 the same bits are bits 1:0 of "
        f"{hcsr}.",
        plan=f"1. RV64: if {csr} exists, setting bits 33:32 leaves them 0"
        + (
            ", and M-mode ld of page A tagged in the top 7 bits, with the bits set, raises an access fault"
            if umode_check
            else ""
        )
        + f".\n2. RV32: if {hcsr} exists, setting bits 1:0 leaves them 0.",
    )
    with t.rv64_only():
        probe_csr(t, csr)

        def yes() -> None:
            ro0_case(t, csr, PMM_M, f"{ext} not implemented")
            if umode_check:
                t.emit(f"li x9, {hex(PMM_M)}", 6)
                t.emit(f"csrs {hex(CSRN[csr])}, x9")
                access(t, "M", "ld", pa(tag=T7), 0, f"{csr}.PMM is read-only zero")
                t.emit(f"li x9, {hex(PMM_M)}", 6)
                t.emit(f"csrc {hex(CSRN[csr])}, x9")

        t.either("x5", yes, lambda: None)
    with t.rv32_only():
        probe_csr(t, hcsr)
        t.either("x5", lambda: ro0_case(t, hcsr, 3, "RV32"), lambda: None)
    return t


def b_rv32_illegal() -> MemTest:
    t = new(sd("Smnpm"), "pm_rv32_illegal", ["I", "Sm"], "M", rv64=False)
    describe(
        t,
        "pm_rv32_illegal",
        context="RV32 harts cannot implement pointer masking, so this test requires only Sm and checks every PMM "
        "location an RV32 hart has: menvcfgh[1:0], mseccfgh[1:0] and henvcfgh[1:0], each probed with a read in a "
        "trap window (the CSR may be absent). On RV64 the file is empty (the RV64 forms are in the *_rdonly0 tests "
        "and the WARL encoding tests).",
        plan="1. RV32: for menvcfgh, mseccfgh and (with H) henvcfgh, when the CSR exists: setting bits 1:0 leaves them "
        "0 (an illegal WARL write that does not update the field).",
    )
    with t.rv32_only():
        for c in ("menvcfgh", "mseccfgh"):
            probe_csr(t, c)
            t.either("x5", lambda c=c: ro0_case(t, c, 3, "RV32"), lambda: None)
        with t.only_if(H):
            ro0_case(t, "henvcfgh", 3, "RV32")
    return t


# ---------------------------------------------------------------- Smmpm (M-mode)
def gen_smmpm() -> list[MemTest]:
    E = "Smmpm"
    tests = []
    t = mk(E, "mseccfg_pmm_presence_op", "M")
    describe(
        t,
        "mseccfg_pmm_presence_op",
        context="M-mode accesses (physical). mseccfg.PMM written directly. " + DISPATCH_NOTE,
        plan="1. For PMM written 11, 10 and 00: ld, lw (imm 12), sd, sw (imm 4) and amoadd.d (Zaamo) of page A with "
        "the top 7 bits all ones and 0x55, and with bits 63:48 = 0xA5C3: masked where the read-back PMLEN covers "
        "the tag, otherwise an access fault with nothing written.\n"
        "2. menvcfg.PMM and senvcfg.PMM are cleared first (where they exist), so the effect is mseccfg's.",
    )
    init_m(t)
    sweep(t, "M", ["ld", "lw", "sd", "sw", "amoadd.d"], pa_basic())
    pm_off(t, "M")
    tests.append(t)
    tests.append(b_enc(E, "mseccfg_pmm_enc", "mseccfg", "M", ["I", "Sm", E]))
    tests.append(b_rdonly0(E, "mseccfg_pmm_rdonly0", "mseccfg", ["I", "Sm"], "M", umode_check=True))

    t = mk(E, "smmpm_definition", "M")
    describe(
        t,
        "smmpm_definition",
        context="mseccfg.PMM masks M-mode accesses only. With menvcfg.PMM = senvcfg.PMM cleared to 00, S-mode (if "
        "implemented) and U-mode (if implemented) accesses entered from M-mode through mret are not masked. "
        + DISPATCH_NOTE,
        plan="1. For mseccfg.PMM written 11 and 10: M-mode ld/sd of page A tagged in the top 7 bits and in bits "
        "63:48 follow the read-back PMLEN.\n"
        "2. With the same setting: S-mode and U-mode ld of the same addresses fault (not masked).",
    )
    init_m(t)
    for val in (3, 2):
        ctrl_write(t, "M", val, 0)
        dispatch(
            t, 0, lambda p: [access(t, "M", k, a, p) for k in INT1 for a in (pa(tag=T7), pa(tag=0xA5C3 << 48, q=16))]
        )
        for m, c in (("S", S_), ("U", "defined(U_SUPPORTED)")):
            with t.only_if(c):
                read_ctrl(t, m, 1)
                dispatch(
                    t, 1, lambda p, m=m: [access(t, m, "ld", a, p) for a in (pa(tag=T7), pa(tag=0xA5C3 << 48, q=16))]
                )
    pm_off(t, "M")
    tests.append(t)

    tests.append(b_ignore_pa(E, "M"))
    tests.append(b_apply_explicit(E, "M"))
    tests.append(b_not_implicit(E, "M"))
    tests.append(b_misaligned(E, "M"))
    tests.append(b_mxr(E, "M"))
    tests.append(b_no_csr_sw(E, "M"))
    tests.append(b_warl_unaffected(E, "M"))
    return tests


# ---------------------------------------------------------------- Smnpm (boot M)
def modes_present() -> list[tuple[str, str | None]]:
    return [("M", "defined(SMMPM_SUPPORTED)"), ("S", S_), ("U", "defined(U_SUPPORTED)")]


def check_modes(t: MemTest, addrs: list[Addr], slot: int = 1, kinds: tuple[str, ...] = ("ld",)) -> None:
    """For every mode present: read its controlling PMM and check accesses from that mode against it."""
    for m, c in modes_present():
        with cond(t, c):
            read_ctrl(t, m, slot)
            dispatch(t, slot, lambda p, m=m: [access(t, m, k, a, p) for k in kinds for a in addrs])


def set_ctrl_m(t: MemTest, mode: str, val: int) -> None:
    """From M-mode: write the PMM controlling `mode` (no check)."""
    c = {"M": "mseccfg", "S": "menvcfg"}.get(mode)
    if c:
        pmm_write(t, c, val)
    else:
        with t.only_if(S_), t.only_if("defined(SSNPM_SUPPORTED)"):
            pmm_write(t, "senvcfg", val)
        with t.only_if(NOS):
            pmm_write(t, "menvcfg", val)


def all_off_m(t: MemTest) -> None:
    with t.only_if("defined(SMMPM_SUPPORTED)"):
        pmm_write(t, "mseccfg", 0)
    with t.only_if("defined(U_SUPPORTED)"):
        pmm_write(t, "menvcfg", 0)
    with t.only_if(S_), t.only_if("defined(SSNPM_SUPPORTED)"):
        pmm_write(t, "senvcfg", 0)


def init_m(t: MemTest) -> None:
    """M-boot tests: enable CBO.ZERO for U through senvcfg (the S boot does that, the M boot does not)."""
    with t.only_if(S_):
        t.emit("li x9, 0x80  // senvcfg.CBZE")
        t.emit("csrs 0x10A, x9")
    all_off_m(t)


ADDR2 = [pa(tag=T7), pa(tag=0xA5C3 << 48, q=16)]


def gen_smnpm() -> list[MemTest]:
    E = "Smnpm"
    tests = []
    REQ = ["I", "Sm", "U", E]

    for suffix, m, req, forb in (("", "S", [*REQ, "S"], None), ("_noS", "U", REQ, ["S"])):
        t = new(sd(E), "menvcfg_pmm_op", req, "M", suffix=suffix, forbidden=forb)
        describe(
            t,
            "menvcfg_pmm_op",
            context="The test boots to M-mode, writes menvcfg.PMM directly, and runs the accesses in the next-lower "
            + (
                "mode, S-mode (this file requires S; menvcfg_pmm_op_noS.S covers harts without S)"
                if m == "S"
                else "mode, U-mode (this file is for harts without S; menvcfg_pmm_op.S covers S)"
            )
            + ", entered with mret. Bare translation. "
            + DISPATCH_NOTE,
            plan=f"1. For PMM written 11, 10 and 00: ld, lw, sd, sw and amoadd.d (Zaamo) in {m}-mode of page A "
            "tagged with the top 7 bits all ones and 0x55 and with bits 63:48 = 0xA5C3.",
        )
        init_m(t)
        sweep(t, m, ["ld", "lw", "sd", "sw", "amoadd.d"], pa_basic())
        all_off_m(t)
        tests.append(t)
    tests.append(b_enc(E, "menvcfg_pmm_enc", "menvcfg", "M", REQ))
    tests.append(b_rdonly0(E, "menvcfg_pmm_rdonly0", "menvcfg", ["I", "Sm", "U"], "M", umode_check=False))

    t = new(sd(E), "smnpm_definition", REQ, "M")
    describe(
        t,
        "smnpm_definition",
        context="Smnpm masks the next-lower mode only: S/HS when S is implemented, otherwise U. With mseccfg.PMM "
        "and senvcfg.PMM at 00, M-mode accesses (and U-mode ones when S exists) are not masked by menvcfg.PMM.",
        plan="1. For menvcfg.PMM written 11 and 10: S-mode (or U-mode without S) ld of page A tagged in the top 7 "
        "bits and bits 63:48 follows the read-back PMLEN.\n"
        "2. M-mode and (with S) U-mode ld of the same addresses follow their own PMM (00): access fault.",
    )
    init_m(t)
    for val in (3, 2):
        pmm_write(t, "menvcfg", val)
        legal_pmm(t, "x8", f"menvcfg write {val:02b}")
        check_modes(t, ADDR2, 1, ("ld", "sd"))
    all_off_m(t)
    tests.append(t)

    t = new(sd(E), "pm_config_next_higher", REQ, "M")
    describe(
        t,
        "pm_config_next_higher",
        context="mseccfg.PMM configures M-mode (Smmpm), menvcfg.PMM configures S-mode (U-mode without S), "
        "senvcfg.PMM configures U-mode (Ssnpm). Each register is enabled alone, and every mode present is checked "
        "against its own register: only the configured mode is masked.",
        plan="1. For each of mseccfg (Smmpm), menvcfg, senvcfg (S and Ssnpm) alone written 11, then 10: M-, S- and "
        "U-mode ld of page A tagged in the top 7 bits and in bits 63:48; each mode follows the PMM of the register "
        "of the next-higher mode.",
    )
    init_m(t)
    for m, c in (("M", "defined(SMMPM_SUPPORTED)"), ("S", S_), ("U", f"{S_} && defined(SSNPM_SUPPORTED)")):
        with t.only_if(c):
            for val in (3, 2):
                set_ctrl_m(t, m, val)
                check_modes(t, ADDR2)
            all_off_m(t)
    tests.append(t)

    t = new(sd(E), "pm_per_mode_control", REQ, "M")
    describe(
        t,
        "pm_per_mode_control",
        context="mseccfg (Smmpm), menvcfg and senvcfg (S and Ssnpm) are set to different values at the same time; "
        "every mode follows its own. Without S, menvcfg controls U-mode.",
        plan="1. Settings (M, S, U) = (11, 10, 00), (00, 11, 10), (10, 00, 11), for the modes and registers present.\n"
        "2. For each: M-, S- and U-mode ld and sd of page A tagged in the top 7 bits and in bits 63:48.",
    )
    init_m(t)
    for vm, vs, vu in ((3, 2, 0), (0, 3, 2), (2, 0, 3)):
        with t.only_if("defined(SMMPM_SUPPORTED)"):
            pmm_write(t, "mseccfg", vm)
        with t.only_if(S_):
            pmm_write(t, "menvcfg", vs)
            with t.only_if("defined(SSNPM_SUPPORTED)"):
                pmm_write(t, "senvcfg", vu)
        with t.only_if(NOS):
            pmm_write(t, "menvcfg", vu)
        check_modes(t, ADDR2, 1, ("ld", "sd"))
    all_off_m(t)
    tests.append(t)

    t = new(sd(E), "pm_auto_apply_active_mode", REQ, "M")
    describe(
        t,
        "pm_auto_apply_active_mode",
        context="One configuration, set once: M-mode PMLEN=16 (Smmpm), S-mode PMLEN=7, U-mode masking off (Ssnpm; "
        "without S, U-mode PMLEN=7 from menvcfg). One mode is off, so a hart that supports only one PMLEN still "
        "has modes that differ. Accesses then alternate between modes without reconfiguring, "
        "so each access must use the setting of the mode it runs in.",
        plan="1. Write mseccfg=11, menvcfg=10, senvcfg=00 (where present).\n"
        "2. ld of page A with bits 63:48 = 0xA5C3 and with the top 7 bits all ones, in the order M, S, U, S, M, U, "
        "M: each follows its mode's read-back PMM.",
    )
    init_m(t)
    with t.only_if("defined(SMMPM_SUPPORTED)"):
        pmm_write(t, "mseccfg", 3)
    pmm_write(t, "menvcfg", 2)
    with t.only_if(f"{S_} && defined(SSNPM_SUPPORTED)"):
        pmm_write(t, "senvcfg", 0)
    for m in ("M", "S", "U", "S", "M", "U", "M"):
        c = dict(modes_present())[m]
        with cond(t, c):
            read_ctrl(t, m, 1)
            dispatch(t, 1, lambda p, m=m: [access(t, m, "ld", a, p) for a in (pa(tag=0xA5C3 << 48, q=16), pa(tag=T7))])
    all_off_m(t)
    tests.append(t)

    tests.append(b_mprv(E))
    tests.append(b_mxr_mprv(E))
    tests.append(b_uxl_m(E))
    tests.append(b_illegal_warl(E))
    tests.append(b_deterministic(E))
    tests.append(b_rv32_illegal())
    return tests


def mprv_tables(t: MemTest, perms: int, name: str) -> SvPT:
    pt = SvPT(t, name, "sv39")
    pt.identity(perms)
    pt.hi_alias("A", perms)
    return pt


def b_mprv(E: str) -> MemTest:
    t = new(sd(E), "pm_mprv_spvp", ["I", "Sm", "U", E], "M")
    describe(
        t,
        "pm_mprv_spvp",
        context="M-mode with mstatus.MPRV=1: loads and stores use the pointer-masking setting of the MPP mode (and "
        "its translation). Settings: mseccfg.PMM=00 (Smmpm), menvcfg.PMM=11 (S's; U's without S), senvcfg.PMM=10 "
        "(U's, with S and Ssnpm). Bare first, then Sv39 (when supported): MPP=S through a supervisor identity map, "
        "MPP=U through a user one, so S- and U-level virtual addresses are sign-extended per their own PMLEN. The "
        "SPVP half of the rule (HLV/HSV) is tested in the H suite (hstatus_hupmm_*).",
        plan="1. Bare: MPRV loads and stores with MPP = M, S (if S) and U, of page A tagged in the top 7 bits and in "
        "bits 63:48: each follows the MPP mode's read-back PMM, never M-mode's.\n"
        "2. Sv39: MPP = S and U, through the identity map and the high-half alias with tags.\n"
        "3. Then mseccfg.PMM=11 and menvcfg.PMM=00: MPP=S and U are not masked by M-mode's setting.",
    )
    init_m(t)
    with t.only_if(S_):
        pmm_write(t, "menvcfg", 3)
        with t.only_if("defined(SSNPM_SUPPORTED)"):
            pmm_write(t, "senvcfg", 2)
    with t.only_if(NOS):
        pmm_write(t, "menvcfg", 3)

    def check(modes: list[tuple[str, str | None]], addrs: list[Addr], kinds: tuple[str, ...] = ("ld", "sd")) -> None:
        for m, c in modes:
            with cond(t, c):
                read_ctrl(t, m, 1)
                dispatch(t, 1, lambda p, m=m: [access(t, m, k, a, p) for k in kinds for a in addrs])

    mpp_modes = [("MPRV_M", None), ("MPRV_S", S_), ("MPRV_U", None)]
    check(mpp_modes, ADDR2)
    with t.only_if(S_):
        for perms, m in ((LEAF, "MPRV_S"), (LEAF | 16, "MPRV_U")):
            pt = mprv_tables(t, perms, f"satp_{m[-1].lower()}")
            satp_probe(t, pt)

            def body(m: str = m) -> None:
                v = {"space": "va", "vabits": 39, "R": 30}
                check(
                    [(m, None)],
                    [
                        Addr("A", 0, T7, 7, **v),
                        Addr("A", 0, 0x55 << 57, 7, hi=True, **v),
                        Addr("A", 0, 0xA5C3 << 48, 16, **v),
                    ],
                    ("ld",),
                )

            t.either("x5", body, lambda: None)
            satp_off(t)
    with t.only_if("defined(SMMPM_SUPPORTED)"):
        pmm_write(t, "mseccfg", 3)
        pmm_write(t, "menvcfg", 0)
        with t.only_if(f"{S_} && defined(SSNPM_SUPPORTED)"):
            pmm_write(t, "senvcfg", 0)
        check(mpp_modes, ADDR2, ("ld",))
    all_off_m(t)
    return t


def b_mxr_mprv(E: str) -> MemTest:
    t = new(sd(E), "pm_mxr_exception", ["I", "Sm", "S", E], "M")
    describe(
        t,
        "pm_mxr_exception",
        context="M-mode with MPRV=1 and mstatus.MXR=1: an access whose effective mode is S or U has MXR in effect "
        "(even with Bare translation), so pointer masking does not apply to it; an access whose effective mode is M "
        "(MPP=M) is still masked. The native S-, U- and M-mode cases are in Sspm, Supm and Smmpm. Settings: "
        "mseccfg.PMM=11 (Smmpm), menvcfg.PMM=11, senvcfg.PMM=11 (Ssnpm).",
        issues=ISSUE_3313,
        plan="1. MXR=1: MPRV ld, sd and amoadd.d (Zaamo) with MPP = S and U of page A tagged in the top 7 bits and "
        "in bits 63:48: not masked (access fault). MPP = M: masked per mseccfg.PMM.\n"
        "2. MXR=0: MPP = S and U are masked again.",
    )
    init_m(t)
    with t.only_if("defined(SMMPM_SUPPORTED)"):
        pmm_write(t, "mseccfg", 3)
    pmm_write(t, "menvcfg", 3)
    with t.only_if("defined(SSNPM_SUPPORTED)"):
        pmm_write(t, "senvcfg", 3)
    t.emit(f"li x9, {hex(MXR)}")
    t.emit("csrs mstatus, x9  // MXR = 1")
    for m in ("MPRV_S", "MPRV_U", "MPRV_M"):
        for c, ks in groups(["ld", "sd", "amoadd.d"]):
            with cond(t, c):
                read_ctrl(t, m, 1)
                pe = mxr_peff(m)
                dispatch(
                    t, 1, lambda p, m=m, ks=ks, pe=pe: [access(t, m, k, a, pe(p, ks)[k]) for k in ks for a in ADDR2]
                )
    t.emit(f"li x9, {hex(MXR)}")
    t.emit("csrc mstatus, x9  // MXR = 0")
    for m in ("MPRV_S", "MPRV_U"):
        read_ctrl(t, m, 1)
        dispatch(t, 1, lambda p, m=m: [access(t, m, "ld", a, p) for a in ADDR2])
    all_off_m(t)
    return t


def xl_case(t: MemTest, field_sh: int, csr: str, mode: str, desc: str) -> None:
    """mstatus.{UXL,SXL} (bits field_sh+1:field_sh) := 1 from M-mode. If it reads 1, csr.PMM reads 00 and a write
    of 11 is ignored; back at 2 (XLEN 64) PMM is still 00. If the write was ignored (XL read-only), PMM keeps its
    value. x8 must hold the PMM read back before."""
    xm = 3 << field_sh
    t.emit("mv x7, x8  // PMM before")
    t.emit(f"li x9, {hex(xm)}", 6)
    t.emit("csrc mstatus, x9")
    t.emit(f"li x9, {hex(1 << field_sh)}", 6)
    t.emit("csrs mstatus, x9")
    t.emit("csrr x6, mstatus")
    t.emit(f"srli x6, x6, {field_sh}")
    t.emit("andi x6, x6, 3")
    t.emit("xori x5, x6, 1")
    t.emit("seqz x5, x5  // the XL field took 1")
    lab = t.label("xl")

    def took() -> None:
        t.emit(f"{lab}:", 0)
        csr_read(t, csr, "x8")
        pmm_field(t, "x8")
        t.check("x8", 0, lab, f"{desc}=1 clears {csr}.PMM")
        csr_op(t, "SET", csr, imm=PMM_M)
        csr_read(t, csr, "x8")
        pmm_field(t, "x8")
        t.check("x8", 0, lab, f"{desc}=1: writing {csr}.PMM is an illegal WARL write (stays 00)")
        t.emit(f"li x9, {hex(xm)}", 6)
        t.emit("csrc mstatus, x9")
        t.emit(f"li x9, {hex(2 << field_sh)}", 6)
        t.emit("csrs mstatus, x9")
        csr_read(t, csr, "x8")
        pmm_field(t, "x8")
        t.check("x8", 0, lab, f"{desc} back to 64: {csr}.PMM is not restored")

    def ignored() -> None:
        lab2 = t.label("xlro")
        t.emit(f"{lab2}:", 0)
        csr_read(t, csr, "x8")
        pmm_field(t, "x8")
        t.emit("xor x8, x8, x7")
        t.check(
            "x8",
            1 if MUT == "uxl_write_clears_pmm" else 0,
            lab2,
            f"{desc} is read-only (the write of 1 was ignored): {csr}.PMM keeps its value",
        )
        t.emit(f"li x9, {hex(xm)}", 6)
        t.emit("csrc mstatus, x9")
        t.emit(f"li x9, {hex(2 << field_sh)}", 6)
        t.emit("csrs mstatus, x9")

    t.either("x5", took, ignored)
    del mode


def b_uxl_m(E: str) -> MemTest:
    t = new(sd(E), "pm_uxl_clear", ["I", "Sm", "U", E], "M")
    describe(
        t,
        "pm_uxl_clear",
        context="menvcfg.PMM corresponds to S-mode (SXL) when S is implemented, otherwise to U-mode (UXL). The test "
        "writes the XL field to 1 from M-mode; when the field is read-only (XLEN fixed at 64), the write is ignored "
        "and PMM must keep its value. The UXL/senvcfg pair is in Ssnpm.",
        plan="1. menvcfg.PMM = 11 (then 10), read back. Write SXL (UXL without S) = 1.\n"
        "2. If it reads 1: PMM reads 00, setting PMM is ignored, and after XL is restored to 2, PMM is still 00.\n"
        "3. If it does not: PMM is unchanged.",
    )
    init_m(t)
    for val in (3, 2):
        pmm_write(t, "menvcfg", val)
        with t.only_if(S_):
            xl_case(t, 34, "menvcfg", "S", "mstatus.SXL")
        with t.only_if(NOS):
            xl_case(t, 32, "menvcfg", "U", "mstatus.UXL")
    all_off_m(t)
    return t


def b_illegal_warl(E: str) -> MemTest:
    t = new(sd(E), "pmlen_illegal_warl", ["I", "Sm", "U", E], "M")
    describe(
        t,
        "pmlen_illegal_warl",
        context="Writing a PMM value the hart does not support for that mode (an unsupported PMLEN, or 01) is an "
        "illegal WARL write: the field reads a legal value afterwards, and the hart masks according to that value. "
        "Checked for menvcfg (S, or U without S), mseccfg (M, Smmpm) and senvcfg (U, Ssnpm), from M-mode. Each "
        "value is written from both 00 and 11, so a field that keeps its old value on an illegal write and one "
        "that picks another legal value are both accepted.",
        plan="1. For each register present and each written value 01, 10, 11, starting from 00 and from 11: the "
        "value read is 00, 10 or 11, and ld of page A tagged in the top 7 bits and in bits 63:48 from the "
        "controlled mode behaves as that value.",
    )
    init_m(t)
    for m, c in (("M", "defined(SMMPM_SUPPORTED)"), ("S", S_), ("U", None)):
        with cond(t, c):
            for start in (0, 3):
                for val in (1, 2, 3):
                    set_ctrl_m(t, m, start)
                    set_ctrl_m(t, m, val)
                    read_ctrl(t, m, 1)
                    restore(t, 1, "x8")
                    legal_pmm(t, "x8", f"{m}-mode's PMM written {val:02b} after {start:02b}")
                    dispatch(t, 1, lambda p, m=m: [access(t, m, "ld", a, p) for a in ADDR2])
            all_off_m(t)
    return t


def b_deterministic(E: str) -> MemTest:
    t = new(sd(E), "pm_deterministic_effect", ["I", "Sm", "U", E], "M")
    describe(
        t,
        "pm_deterministic_effect",
        context="The same PMLEN in M-mode (Smmpm), S-mode and U-mode (Ssnpm with S) gives the same result for the "
        "same physical address in each mode, and S- and U-level Sv39 virtual addresses (U through MPRV=1, MPP=U) "
        "give the same result as each other. Each mode's read-back PMM selects its expectations, and the "
        "expectations come from one transformation.",
        plan="1. All present controls written 11, then 10: ld of page A with tags in bits 63:57, 63:48 and the single "
        "bits 57 and 48, from M, S and U.\n"
        "2. Sv39 (when supported), all written 11: MPRV ld with MPP=S (supervisor table) and MPP=U (user table) of "
        "page A tagged, and of its high-half alias.",
    )
    init_m(t)
    addrs = [pa(tag=T7), pa(tag=0xA5C3 << 48, q=16), pa(tag=1 << 57), pa(tag=1 << 48, q=16)]
    for val in (3, 2):
        with t.only_if("defined(SMMPM_SUPPORTED)"):
            pmm_write(t, "mseccfg", val)
        pmm_write(t, "menvcfg", val)
        with t.only_if(f"{S_} && defined(SSNPM_SUPPORTED)"):
            pmm_write(t, "senvcfg", val)
        check_modes(t, addrs)
    with t.only_if(S_):
        for perms, m in ((LEAF, "MPRV_S"), (LEAF | 16, "MPRV_U")):
            pt = mprv_tables(t, perms, f"satp_{m[-1].lower()}")
            satp_probe(t, pt)

            def body(m: str = m) -> None:
                v = {"space": "va", "vabits": 39, "R": 30}
                read_ctrl(t, m, 1)
                dispatch(
                    t,
                    1,
                    lambda p: [
                        access(t, m, "ld", a, p)
                        for a in (
                            Addr("A", 0, T7, 7, **v),
                            Addr("A", 0, 0x55 << 57, 7, hi=True, **v),
                            Addr("A", 0, 0xA5C3 << 48, 16, **v),
                        )
                    ],
                )

            t.either("x5", body, lambda: None)
            satp_off(t)
    all_off_m(t)
    return t


# ---------------------------------------------------------------- Ssnpm (boot S)
def h_bare(t: MemTest) -> None:
    t.emit("csrw 0x680, x0  // hgatp = Bare")
    t.emit("csrw 0x280, x0  // vsatp = Bare")
    t.emit(".word 0x62000073  // hfence.gvma")
    t.emit(".word 0x22000073  // hfence.vvma")


def gen_ssnpm() -> list[MemTest]:
    E = "Ssnpm"
    tests = []
    REQ = ["I", "S", "U", E]

    t = new(sd(E), "senvcfg_pmm_ssnpm", REQ, "S")
    describe(
        t,
        "senvcfg_pmm_ssnpm",
        context="S-mode writes senvcfg.PMM; U-mode (and with H, VU-mode, vsatp and hgatp Bare) accesses follow it, "
        "while S-mode accesses follow menvcfg.PMM (00) and VS-mode henvcfg.PMM (00). The read-only-zero half of "
        "the rule is senvcfg_pmm_ssnpm_absent.S; on RV32 senvcfg has no bits 33:32. " + DISPATCH_NOTE,
        plan="1. For senvcfg.PMM written 11, 10 and 00: U-mode ld, lw, sd, sh, amoadd.d (Zaamo) and lr.d/sc.d "
        "(Zalrsc) of page A tagged with the top 7 bits all ones and 0x55 and with bits 63:48 = 0xA5C3.\n"
        "2. S-mode ld of the same addresses: not masked.\n"
        "The VU/VS half (H) is senvcfg_pmm_ssnpm_H.S.",
    )
    for val in (3, 2, 0):
        ctrl_write(t, "U", val, 0)
        for c, ks in groups(["ld", "lw", "sd", "sh", "amoadd.d", "lr.d"]):
            with cond(t, c):
                dispatch(t, 0, lambda p, ks=ks: [access(t, "U", k, a, p) for k in ks for a in pa_basic()])
        read_ctrl(t, "S", 1)
        dispatch(t, 1, lambda p: [access(t, "S", "ld", a, p) for a in ADDR2])
    pm_off(t, "U")
    tests.append(t)

    t = new(sd(E), "senvcfg_pmm_ssnpm", [*REQ, "H"], "S", suffix="_H")
    describe(
        t,
        "senvcfg_pmm_ssnpm",
        context="The VU half: HS-mode writes senvcfg.PMM; VU-mode accesses (vsatp and hgatp Bare) follow it, VS-mode "
        "accesses follow henvcfg.PMM (00). " + DISPATCH_NOTE,
        plan="1. For senvcfg.PMM written 11, 10 and 00: VU-mode ld and sd of page A tagged in the top 7 bits and in "
        "bits 63:48 follow senvcfg.PMM; VS-mode ld of the same addresses does not.",
    )
    h_bare(t)
    pmm_write(t, "henvcfg", 0)
    for val in (3, 2, 0):
        ctrl_write(t, "VU", val, 0)
        read_ctrl(t, "VU", 1)
        dispatch(t, 1, lambda p: [access(t, "VU", k, a, p) for k in INT1 for a in ADDR2])
        read_ctrl(t, "VS", 1)
        dispatch(t, 1, lambda p: [access(t, "VS", "ld", a, p) for a in ADDR2])
    pm_off(t, "U")
    tests.append(t)

    t = new(sd(E), "senvcfg_pmm_ssnpm", ["I", "S"], "S", forbidden=[E], suffix="_absent")
    describe(
        t,
        "senvcfg_pmm_ssnpm",
        context="The read-only-zero half: a hart with S but without Ssnpm. senvcfg.PMM is bits 33:32 on RV64; on RV32 "
        "senvcfg has no such bits, so the file checks nothing there.",
        plan="1. RV64: setting senvcfg bits 33:32 leaves them 0, and U-mode ld of page A tagged in the top 7 bits "
        "raises an access fault.",
    )
    ro0_case(t, "senvcfg", PMM_M, "Ssnpm not implemented")
    with t.only_if("defined(U_SUPPORTED)"):
        csr_op(t, "SET", "senvcfg", imm=PMM_M)
        access(t, "U", "ld", pa(tag=T7), 0, "senvcfg.PMM is read-only zero")
        csr_op(t, "CLEAR", "senvcfg", imm=PMM_M)
    tests.append(t)

    tests.append(b_enc(E, "senvcfg_pmm_enc", "senvcfg", "S", REQ))

    t = new(sd(E), "senvcfg_pmm_immediate", REQ, "S")
    describe(
        t,
        "senvcfg_pmm_immediate",
        context="No SFENCE.VMA is executed anywhere in the test. senvcfg.PMM is changed in S-mode and the next "
        "U-mode access (after the sret that enters U) must use the new value; the value is flipped back and forth "
        "between accesses to the same address, so a stale setting cached with a translation or in the "
        "load/store unit is caught. With H, the same for VU-mode.",
        plan="1. senvcfg.PMM 00 -> 11 -> 00 -> 10 -> 00, with a U-mode ld of page A tagged in the top 7 bits after "
        "each write, and a tagged sd after the last enable.\n"
        "2. With H: the same sequence with VU-mode ld.",
    )

    def seq(mode: str) -> None:
        for val in (0, 3, 0, 2, 0):
            setpm(t, "senvcfg", val, 0)
            if MUT == "pmm_needs_fence":
                t.emit("li x9, 0")
                save(t, "x9", 0)
            dispatch(t, 0, lambda p: [access(t, mode, "ld", pa(tag=T7), p)])
            if val == 2:
                dispatch(t, 0, lambda p: [access(t, mode, "sd", pa(tag=T7), p)])

    seq("U")
    with t.only_if(H):
        h_bare(t)
        seq("VU")
    pm_off(t, "U")
    tests.append(t)

    t = new(sd(E), "henvcfg_pmm_op", ["I", "S", "H", E], "S")
    describe(
        t,
        "henvcfg_pmm_op",
        context="HS-mode writes henvcfg.PMM; VS-mode accesses (vsatp and hgatp Bare, so guest-physical addresses, "
        "zero-extended) follow it. VU-mode follows senvcfg.PMM (00 here), and HS- and U-mode are unaffected. "
        "henvcfg.PMM is WARL like senvcfg.PMM. The read-only-zero half is henvcfg_pmm_op_absent.S. hstatus.HUPMM "
        "and the HLV/HSV cases are in the H suite. " + DISPATCH_NOTE,
        plan="1. henvcfg.PMM: written 00 reads 00; written 10, 11 and 01 read 00, 10 or 11.\n"
        "2. For henvcfg.PMM written 11, 10 and 00: VS-mode ld, sd and amoadd.d (Zaamo) of page A tagged in the top "
        "7 bits (all ones, 0x55) and bits 63:48.\n"
        "3. With the same setting (senvcfg.PMM and menvcfg.PMM cleared first), VU-, U- and HS-mode ld: not "
        "masked.\n4. Ssnpm provides VS-mode masking: henvcfg writes of 10 and 11 do not both read 00.",
    )
    h_bare(t)
    pm_off(t, "U")
    pm_off(t, "S")
    for val in (0, 2, 3, 1):
        pmm_write(t, "henvcfg", val)
        lab = t.label("henvcfg_enc")
        t.emit(f"{lab}:", 0)
        t.check("x8", 0 if val == 0 else [0, 2, 3], lab, f"henvcfg.PMM written {val:02b} reads a legal value")
    require_some(t, "VS", "henvcfg.PMM (Ssnpm with H)")
    for val in (3, 2, 0):
        ctrl_write(t, "VS", val, 0)
        for c, ks in groups(["ld", "sd", "amoadd.d"]):
            with cond(t, c):
                dispatch(t, 0, lambda p, ks=ks: [access(t, "VS", k, a, p) for k in ks for a in pa_basic()])
        for m in ("VU", "U", "S"):
            read_ctrl(t, m, 1)
            dispatch(t, 1, lambda p, m=m: [access(t, m, "ld", a, p) for a in ADDR2])
    pmm_write(t, "henvcfg", 0)
    tests.append(t)

    t = new(sd(E), "henvcfg_pmm_op", ["I", "S", "H"], "S", forbidden=[E], suffix="_absent", rv64=False)
    describe(
        t,
        "henvcfg_pmm_op",
        context="The read-only-zero half: a hart with H but without Ssnpm (every RV32 hart with H, where the field "
        "would be henvcfgh[1:0]).",
        plan="1. RV64: setting henvcfg bits 33:32 leaves them 0, and VS-mode ld of page A tagged in the top 7 bits "
        "raises an access fault.\n2. RV32: setting henvcfgh bits 1:0 leaves them 0.",
    )
    with t.rv64_only():
        h_bare(t)
        ro0_case(t, "henvcfg", PMM_M, "Ssnpm not implemented")
        csr_op(t, "SET", "henvcfg", imm=PMM_M)
        access(t, "VS", "ld", pa(tag=T7), 0, "henvcfg.PMM is read-only zero")
        csr_op(t, "CLEAR", "henvcfg", imm=PMM_M)
    with t.rv32_only():
        ro0_case(t, "henvcfgh", 3, "RV32")
    tests.append(t)

    t = new(sd(E), "ssnpm_definition", REQ, "S")
    describe(
        t,
        "ssnpm_definition",
        context="Ssnpm provides masking for U-mode (senvcfg.PMM) and, with H, VS-mode (henvcfg.PMM) and VU-mode "
        "(senvcfg.PMM), and not for S-mode. Settings: senvcfg 11 then 10, henvcfg the other value. Bare "
        "translation, vsatp and hgatp Bare.",
        plan="1. senvcfg.PMM=11, henvcfg.PMM=10 (H): ld of page A tagged in the top 7 bits and in bits 63:48 from "
        "U, VU, VS and S; each follows its own register (S: menvcfg, 00).\n"
        "2. The same with senvcfg.PMM=10, henvcfg.PMM=11.",
    )
    for vu, vs in ((3, 2), (2, 3)):
        pmm_write(t, "senvcfg", vu)
        with t.only_if(H):
            h_bare(t)
            pmm_write(t, "henvcfg", vs)
        for m, c in (("U", None), ("VU", H), ("VS", H), ("S", None)):
            with cond(t, c):
                read_ctrl(t, m, 1)
                dispatch(t, 1, lambda p, m=m: [access(t, m, "ld", a, p) for a in ADDR2])
    pm_off(t, "U")
    with t.only_if(H):
        pmm_write(t, "henvcfg", 0)
    tests.append(t)

    t = new(sd(E), "pm_uxl_clear", REQ, "S")
    describe(
        t,
        "pm_uxl_clear",
        context="senvcfg.PMM corresponds to U-mode, whose XLEN is mstatus.UXL (written through T-SBI). When UXL is "
        "read-only (XLEN fixed at 64) the write of 1 is ignored and PMM must keep its value. The SXL/menvcfg pair "
        "is in Smnpm.",
        plan="1. senvcfg.PMM = 11 (then 10), read back. Write UXL = 1.\n"
        "2. If it reads 1: senvcfg.PMM reads 00, setting it is ignored, and after UXL is restored to 2 it is still "
        "00.\n3. If not: PMM is unchanged.",
    )
    for val in (3, 2):
        pmm_write(t, "senvcfg", val)
        t.emit("mv x7, x8  // PMM before")
        csr_op(t, "CLEAR", "mstatus", imm=3 << 32)
        csr_op(t, "SET", "mstatus", imm=1 << 32)
        csr_read(t, "mstatus", "x6")
        t.emit("srli x6, x6, 32")
        t.emit("andi x6, x6, 3")
        t.emit("xori x5, x6, 1")
        t.emit("seqz x5, x5")

        def took() -> None:
            lab = t.label("uxl")
            t.emit(f"{lab}:", 0)
            csr_read(t, "senvcfg", "x8")
            pmm_field(t, "x8")
            t.check("x8", 0, lab, "UXL=1 clears senvcfg.PMM")
            csr_op(t, "SET", "senvcfg", imm=PMM_M)
            csr_read(t, "senvcfg", "x8")
            pmm_field(t, "x8")
            t.check("x8", 0, lab, "UXL=1: senvcfg.PMM stays 00 when written")
            csr_op(t, "CLEAR", "mstatus", imm=3 << 32)
            csr_op(t, "SET", "mstatus", imm=2 << 32)
            csr_read(t, "senvcfg", "x8")
            pmm_field(t, "x8")
            t.check("x8", 0, lab, "UXL back to 64: senvcfg.PMM is not restored")

        def ignored() -> None:
            lab = t.label("uxlro")
            t.emit(f"{lab}:", 0)
            csr_read(t, "senvcfg", "x8")
            pmm_field(t, "x8")
            t.emit("xor x8, x8, x7")
            t.check(
                "x8",
                1 if MUT == "uxl_write_clears_pmm" else 0,
                lab,
                "UXL is read-only (the write of 1 was ignored): senvcfg.PMM keeps its value",
            )
            csr_op(t, "CLEAR", "mstatus", imm=3 << 32)
            csr_op(t, "SET", "mstatus", imm=2 << 32)

        t.either("x5", took, ignored)
    pm_off(t, "U")
    tests.append(t)

    tests += b_gpa(E)
    tests.append(b_va_vs(E))
    tests.append(b_mxr_v(E))
    return tests


def b_mxr_v(E: str) -> MemTest:
    t = new(sd(E), "pm_mxr_exception", ["I", "S", "H", E], "S")
    describe(
        t,
        "pm_mxr_exception",
        context="The VS/VU case. For an access whose effective mode is VS or VU, MXR is in effect when sstatus.MXR "
        "or vsstatus.MXR is 1, and then pointer masking does not apply (even with vsatp and hgatp Bare). "
        "henvcfg.PMM (VS) and senvcfg.PMM (VU) are written 11 and 10; the expectations follow the value read back. "
        "The S/U, M and MPRV cases are in Sspm, Supm, Smmpm and Smnpm.",
        issues=ISSUE_3313,
        plan="1. vsstatus.MXR=1 alone: VS- and VU-mode ld and sd of page A tagged in the top 7 bits and in bits "
        "63:48: not masked (access fault).\n"
        "2. sstatus.MXR=1 alone: the same.\n"
        "3. Both 0: masked per the read-back PMLEN.",
    )
    h_bare(t)
    for src in ("vsstatus", "sstatus", None):
        if src:
            t.emit(f"li x9, {hex(MXR)}")
            t.emit(f"csrs {hex(CSRN[src])}, x9  // {src}.MXR = 1")
        for m in ("VS", "VU"):
            sweep(t, m, INT1, ADDR2, vals=(3, 2), peff=None if src is None else mxr_peff(m))
        if src:
            t.emit(f"li x9, {hex(MXR)}")
            t.emit(f"csrc {hex(CSRN[src])}, x9  // {src}.MXR = 0")
    pm_off(t, "U")
    pmm_write(t, "henvcfg", 0)
    return t


def b_gpa(E: str) -> list[MemTest]:
    out = []
    for gs in (False, True):
        t = new(sd(E), "pm_ignore_pa", ["I", "S", "H", E], "S", suffix="_gstage" if gs else "")
        describe(
            t,
            "pm_ignore_pa",
            context="The guest-physical case: VS- and VU-mode accesses with vsatp Bare are guest-physical addresses, "
            "zero-extended, whether or not G-stage translation is on. "
            + (
                "This file: hgatp Sv39x4 and Sv48x4 (each when supported) identity-mapping the test image, where an "
                "address the transformation leaves outside the GPA range (41 or 50 bits) raises a guest-page fault "
                "(21/23); pm_ignore_pa.S has hgatp Bare. "
                if gs
                else "This file: hgatp Bare (faults are access faults); pm_ignore_pa_gstage.S has G-stage translation. "
            )
            + "The U-mode and S-mode physical cases are in Supm and Sspm. "
            + DISPATCH_NOTE,
            plan=(
                "1. hgatp Sv39x4 (VS and VU) and Sv48x4 (VS), each when supported: for henvcfg.PMM (VS) and senvcfg.PMM "
                "(VU) written 11, 10, 00: ld of page A tagged with single bits 63, 57, 56, 48, the pattern 0x155 in "
                "56:48 and all of 63:48. With Sv48x4 the 50-bit GPA overlaps the PMLEN=16 masked bits 49:48 (the "
                "pm-two-stage case): masked, they are zeroed and the access reaches page A; not masked, the GPA is "
                "unmapped (guest-page fault)."
                if gs
                else "1. hgatp Bare: for henvcfg.PMM (VS) and senvcfg.PMM (VU) written 11, 10, 00: VS ld and sd, and VU "
                "ld, of page A tagged with single bits 63, 57, 56, 48, the pattern 0x155 in 56:48 and all of 63:48."
            ),
        )
        h_bare(t)
        if not gs:
            sweep(t, "VS", INT1, pa_boundary())
            sweep(t, "VU", ["ld"], pa_boundary())
        else:
            for scheme, mode_val in (("sv39x4", 8), ("sv48x4", 9)):
                g = hmem.PT(t, f"g{scheme}", scheme, 64)
                g.identity(hmem.ULEAF, n=1)
                g.atp("x6")
                t.emit("csrw 0x680, x6  // hgatp")
                t.emit("csrr x5, 0x680")
                t.emit("srli x5, x5, 60")
                t.emit(f"xori x5, x5, {mode_val}")
                t.emit("seqz x5, x5")
                t.emit(".word 0x62000073  // hfence.gvma")
                save(t, "x5", 3)
                GATE.append(3)
                for m in ("VS", "VU") if scheme == "sv39x4" else ("VS",):
                    sweep(t, m, ["ld"], pa_boundary("gpa"), gstage=True)
                GATE.pop()
                h_bare(t)
        pm_off(t, "U")
        pmm_write(t, "henvcfg", 0)
        out.append(t)
    return out


def b_va_vs(E: str) -> MemTest:
    t = new(sd(E), "pm_ignore_va", ["I", "S", "H", E], "S")
    describe(
        t,
        "pm_ignore_va",
        context="The VS/VU case: vsatp Sv39 (when supported), hgatp Bare. The VS-stage table identity-maps the test "
        "image and maps the top root-level page of the high half to page A's; the VU table does the same with user "
        "pages. VS-mode follows henvcfg.PMM, VU-mode senvcfg.PMM, both sign-extending virtual addresses. Traps go "
        "to HS-mode, which is not translated by vsatp. " + TRANSFORM_NOTE,
        plan="1. vsatp Sv39 with supervisor pages: for henvcfg.PMM written 11, 10, 00, VS-mode ld of page A through "
        "the identity map and the high-half alias with tags (as in Sspm's pm_ignore_va), and of an unmapped VA.\n"
        "2. vsatp Sv39 with user pages: the same for VU-mode and senvcfg.PMM.",
    )
    h_bare(t)
    for m, perms in (("VS", LEAF), ("VU", LEAF | 16)):

        def body(R: int, vb: int, m: str = m) -> None:
            sweep(t, m, ["ld"], va_set("sv39", R, vb) + va_unmapped(R, vb))

        with_satp(t, "sv39", perms, body, csr="vsatp")
    pm_off(t, "U")
    pmm_write(t, "henvcfg", 0)
    return t


# ---------------------------------------------------------------- Sspm and Supm
def gen_sspm() -> list[MemTest]:
    E = "Sspm"
    tests = [
        b_ignore_upper(E, "S"),
        b_ignore_va_s(E),
        b_ignore_pa(E, "S"),
        b_apply_explicit(E, "S"),
        b_explicit_va(E),
        b_not_implicit(E, "S"),
        b_cpu_only(E),
        b_misaligned(E, "S"),
        b_csr_hw_apply(E),
        b_no_csr_sw(E, "S"),
        b_warl_unaffected(E, "S"),
    ]
    t = b_mxr(E, "S")
    b_mxr_s_paged(t)
    pm_off(t, "S")
    tests.append(t)
    tests += [b_mode_only(E), b_pmlen_values(E), b_reserved(E)]
    return tests


def gen_supm() -> list[MemTest]:
    E = "Supm"
    tests = [
        b_ignore_upper(E, "U"),
        b_ignore_pa(E, "U"),
        b_apply_explicit(E, "U"),
        b_not_implicit(E, "U"),
        b_misaligned(E, "U"),
        b_mxr(E, "U"),
    ]
    t = new(sd(E), "pm_ignore_va", ["I", "S", "U", "Sm", E], "M", suffix="_Sm")
    describe(
        t,
        "pm_ignore_va",
        context="U-mode under satp Sv39, Sv48 and Sv57 (each when supported). U-mode code needs user pages while "
        "the S-mode trap handler needs supervisor ones, so this part boots to M-mode (traps from U go to M, which "
        "is not translated) and requires Sm; senvcfg.PMM is written directly. The tables map the test image with "
        "user pages and the high-half alias of page A. " + TRANSFORM_NOTE,
        plan="1. For each supported scheme and senvcfg.PMM written 11, 10 and 00 (menvcfg.PMM without Ssnpm is "
        "S-mode's and stays 00): U-mode ld of page A through the identity map and the high-half alias with tags, "
        "and of an unmapped VA (Sv39, Sv48).",
    )
    init_m(t)
    with t.only_if("defined(SSNPM_SUPPORTED)"):
        for scheme in ("sv39", "sv48", "sv57"):

            def body(R: int, vb: int, scheme: str = scheme) -> None:
                addrs = va_set(scheme, R, vb) + (va_unmapped(R, vb) if scheme != "sv57" else [])
                sweep(t, "U", ["ld"], addrs)

            with_satp(t, scheme, LEAF | 16, body)
    all_off_m(t)
    tests.append(t)
    return tests


def gen() -> list[MemTest]:
    tests = []
    for ext, fn in (
        ("Smmpm", gen_smmpm),
        ("Smnpm", gen_smnpm),
        ("Ssnpm", gen_ssnpm),
        ("Sspm", gen_sspm),
        ("Supm", gen_supm),
    ):
        part = fn()
        if SUITE != "Spm":  # a mutant run writes every suite to one directory: keep the file names apart
            for t in part:
                t.suffix += f"_{ext}"
        tests += part
    names = [(t.suite, t.rule + t.suffix) for t in tests]
    dup = {n for n in names if names.count(n) > 1}
    assert not dup, f"duplicate tests: {dup}"
    return tests


def main() -> None:
    only = set(sys.argv[1:])
    for t in gen():
        if only and t.rule + t.suffix not in only and t.suite not in only:
            continue
        p = t.write()
        print(f"{p.relative_to(p.parents[2])}: ~{t.ninst} instructions")


if __name__ == "__main__":
    main()
