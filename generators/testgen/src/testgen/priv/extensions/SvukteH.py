##################################
# priv/extensions/SvukteH.py
#
# SvukteH test generator: hypervisor Svukte behavior.
#
# SPDX-License-Identifier: Apache-2.0
##################################

"""SvukteH test generator.

Svukte can be implemented without the hypervisor extension, so the extra behavior H
adds gets its own suite. Because qualification follows the *effective* privilege mode of
an access, H reaches three states that SvukteS and SvukteSm cannot:

  * hlv/hlvx/hsv executed in HS-mode with hstatus.SPVP=0 have an effective privilege of
    VU, so senvcfg.UKTE qualifies them without the hart entering a virtual mode. With
    hstatus.SPVP=1 the effective privilege is VS, which is never qualified.
  * hlv/hlvx/hsv executed in U-mode, which hstatus.HU permits, are qualified by
    hstatus.HUKTE instead of senvcfg.UKTE. Each of those cases sets the two fields to
    opposite values so a fault or its absence pins the behavior on HUKTE alone.
  * Ordinary accesses in VU-mode are qualified by senvcfg.UKTE, with vsatp - not satp -
    as the active satp register.

S-stage translation is left Bare, so the HS-mode and U-mode code runs untranslated and
only the VS-stage mappings matter; no S-stage page tables or save-area fixups are
needed. G-stage translation is left Bare as well, so guest physical addresses are
physical addresses and every fault below is attributable to the VS-stage address check
Svukte adds rather than to a second translation stage.
"""

from __future__ import annotations

from dataclasses import dataclass

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.SvukteCommon import (
    PTE_SUPERVISOR_RWX,
    PTE_USER_RWX,
    PTE_USER_RX,
    SV_MODES,
    SvMode,
    SvukteRegs,
    access_test,
    allocate_regs,
    bump_store_value,
    data_payload,
    deferred_sigupds,
    disable_translation,
    hypervisor_only,
    init_store_value,
    mode_guarded,
    release_regs,
    rv64_only,
    set_csr_bits,
    set_ukte,
    target_va,
    vs_stage_pte,
)
from testgen.priv.registry import add_priv_test_generator

covergroup = "SvukteH_cg"

# hlv/hlvx/hsv, in the order every explicit-guest-access case emits them. hlvx is a read
# that checks execute permission rather than read permission, so it faults as a load.
_GUEST_ACCESS_KINDS = ("hsv", "hlv", "hlvx")

# Ordinary accesses, for the VU-mode cases.
_ORDINARY_KINDS = ("store", "load", "exec")

_QUALIFIED_HS = (
    "cp_svukte_qualified_hs_write_fault",
    "cp_svukte_qualified_hs_read_fault",
    "cp_svukte_qualified_hs_read_fault",
)
_QUALIFIED_HUKTE = (
    "cp_svukte_qualified_hukte_write_fault",
    "cp_svukte_qualified_hukte_read_fault",
    "cp_svukte_qualified_hukte_read_fault",
)
_QUALIFIED_VU = (
    "cp_svukte_qualified_vu_write_fault",
    "cp_svukte_qualified_vu_read_fault",
    "cp_svukte_qualified_vu_exec_fault",
)


def _same(name: str) -> tuple[str, str, str]:
    """A coverpoint triple where every access kind contributes to one rw_acc cross."""
    return (name, name, name)


def _data_and_instr(name: str) -> tuple[str, str, str]:
    """A coverpoint triple whose execute access contributes to the instruction-side cross."""
    return (name, name, f"{name}_i")


@dataclass(frozen=True)
class _GuestCase:
    """An hlv/hlvx/hsv case: which CSR fields to set, which address, which coverpoints.

    Attributes:
        bin_name: Distinguishing part of the testcase names.
        ukte: Value for senvcfg.UKTE.
        hukte: Value for hstatus.HUKTE.
        eff_vs: Set hstatus.SPVP, making the effective privilege VS instead of VU.
        umode: Execute the instructions in U-mode (with hstatus.HU set) rather than HS-mode.
        va_attr: Which SvMode address to target.
        coverpoints: One coverpoint per entry of _GUEST_ACCESS_KINDS.
    """

    bin_name: str
    ukte: bool
    hukte: bool
    eff_vs: bool
    umode: bool
    va_attr: str
    coverpoints: tuple[str, str, str]


# Group A: HS-mode, hstatus.SPVP=0, so the effective privilege is VU and senvcfg.UKTE
# governs. Group B: hstatus.SPVP=1, so the effective privilege is VS and nothing
# qualifies the access; it targets the supervisor-half page mapped without PTE_U so it
# succeeds without depending on vsstatus.SUM.
_HS_CASES = (
    _GuestCase(
        "hs_ukte_clear_high", False, False, False, False, "va_data", _same("cp_not_svukte_qualified_hs_disabled")
    ),
    _GuestCase("hs_ukte_set_high", True, False, False, False, "va_data", _QUALIFIED_HS),
    _GuestCase("hs_ukte_set_low", True, False, False, False, "va_data_lower", _same("cp_not_svukte_qualified_hs_addr")),
    _GuestCase("hs_eff_vs_high", True, False, True, False, "va_data_super", _same("cp_not_svukte_qualified_hs_eff_vs")),
)

# Group C: U-mode with hstatus.HU set. hstatus.HUKTE replaces senvcfg.UKTE, so each case
# sets the two to opposite values.
_UMODE_CASES = (
    _GuestCase("u_hukte_clear_high", True, False, False, True, "va_data", _same("cp_not_svukte_qualified_hukte_clear")),
    _GuestCase("u_hukte_set_high", False, True, False, True, "va_data", _QUALIFIED_HUKTE),
    _GuestCase(
        "u_hukte_set_low", False, True, False, True, "va_data_lower", _same("cp_not_svukte_qualified_hukte_addr")
    ),
)


@dataclass(frozen=True)
class _VuCase:
    """A VU-mode ordinary-access case."""

    bin_name: str
    ukte: bool
    va_attr: str
    coverpoints: tuple[str, str, str]


# Group D: ordinary loads, stores and jumps executed in VU-mode.
_VU_CASES = (
    _VuCase("vu_ukte_clear_high", False, "va_data", _data_and_instr("cp_not_svukte_qualified_vu_disabled")),
    _VuCase("vu_ukte_set_high", True, "va_data", _QUALIFIED_VU),
    _VuCase("vu_ukte_set_low", True, "va_data_lower", _data_and_instr("cp_not_svukte_qualified_vu_addr")),
)


def _enable_hypervisor_translation(mode: SvMode) -> list[str]:
    """Put the hart in the configuration every case below shares.

    S-stage and G-stage translation are Bare and only the VS stage is active. hgatp must
    be written explicitly: RVTEST_TRAP_PROLOG H leaves it pointing at an empty
    rvtest_Hroot_pg_tbl, which would guest-page-fault every access made with V=1.
    """
    return [
        f"# ---- {mode.name}: hypervisor Svukte behavior ----",
        "# S-stage Bare: the HS-mode and U-mode code below runs untranslated, so only the",
        "# VS-stage mappings matter and no S-stage page tables are needed.",
        "csrw satp, zero",
        "sfence.vma",
        "# G-stage Bare, so guest physical addresses are physical addresses.",
        "csrw hgatp, zero",
        "# Keep ecall undelegated so RVTEST_GOTO_MMODE reaches M-mode from VU-mode.",
        "csrw hedeleg, zero",
        "# VS-stage mappings. Superpages only, so rvtest_Vroot_pg_tbl holds every leaf PTE.",
        *vs_stage_pte(mode, "rvtest_code_begin", PTE_USER_RX, mode.va_code, fence=False),
        *vs_stage_pte(mode, "rvtest_data_1", PTE_USER_RWX, mode.va_data, fence=False),
        *vs_stage_pte(mode, "rvtest_data_1", PTE_SUPERVISOR_RWX, mode.va_data_super, fence=False),
        *vs_stage_pte(mode, "rvtest_data_1", PTE_USER_RWX, mode.va_data_lower, fence=False),
        "hfence.vvma",
        "# Point the VS save area's code pointer at the code region's virtual address so",
        "# RVTEST_GOTO_LOWER_MODE VUmode relocates its return address. a0 is not",
        "# allocatable, but V_SAVE_AREA_SETUP requires it and no mode switch intervenes.",
        "csrr a0, mscratch",
        f"V_SAVE_AREA_SETUP({hex(mode.va_code)}, rvtest_code_begin, code, {mode.level_macro})",
        f"VSATP_SETUP({mode.name}, PA)",
        "hfence.vvma",
    ]


def _disable_hypervisor_translation() -> list[str]:
    """Return every translation stage to Bare before the next mode's block."""
    return [
        "csrw vsatp, zero",
        "csrw hgatp, zero",
        "hfence.vvma",
        *disable_translation(),
    ]


def _guest_case(test_data: TestData, mode: SvMode, regs: SvukteRegs, case: _GuestCase) -> list[str]:
    """Emit one hlv/hlvx/hsv case, run either in HS-mode or in U-mode."""
    where = "U-mode" if case.umode else "HS-mode"
    effective = "VS" if case.eff_vs else "VU"
    lines = [
        "",
        (
            f"# {case.bin_name}: {where}, effective privilege {effective}, "
            f"senvcfg.UKTE {'set' if case.ukte else 'clear'}, hstatus.HUKTE {'set' if case.hukte else 'clear'}"
        ),
        *set_ukte(regs, qualified=case.ukte),
        "# hstatus.SPVP picks the effective privilege of hlv/hlvx/hsv.",
        *set_csr_bits("hstatus", "HSTATUS_SPVP", regs.scratch, set_bits=case.eff_vs),
        "# hstatus.HUKTE qualifies these instructions when they execute in U-mode.",
        *set_csr_bits("hstatus", "HSTATUS_HUKTE", regs.scratch, set_bits=case.hukte),
        "# hstatus.HU permits hlv/hlvx/hsv in U-mode.",
        *set_csr_bits("hstatus", "HSTATUS_HU", regs.scratch, set_bits=case.umode),
        *target_va(mode, getattr(mode, case.va_attr), regs),
        *bump_store_value(regs),
    ]
    if case.umode:
        lines.append("RVTEST_GOTO_LOWER_MODE Umode")
    else:
        lines.append("RVTEST_GOTO_LOWER_MODE HSmode")

    results: list[tuple[str, int]] = []
    for kind, coverpoint in zip(_GUEST_ACCESS_KINDS, case.coverpoints):
        asm, label, check_reg = access_test(
            test_data,
            regs,
            covergroup=covergroup,
            coverpoint=coverpoint,
            bin_name=f"{mode.name}_{case.bin_name}_{kind}",
            kind=kind,
        )
        lines.extend(asm)
        results.append((label, check_reg))

    lines.append("RVTEST_GOTO_MMODE")
    lines.extend(deferred_sigupds(test_data, results))
    return lines


def _vu_case(test_data: TestData, mode: SvMode, regs: SvukteRegs, case: _VuCase) -> list[str]:
    """Emit one VU-mode ordinary-access case."""
    lines = [
        "",
        f"# {case.bin_name}: VU-mode ordinary accesses, senvcfg.UKTE {'set' if case.ukte else 'clear'}",
        *set_ukte(regs, qualified=case.ukte),
        "# hstatus.HUKTE and hstatus.HU only affect hlv/hlvx/hsv executed in U-mode; clear",
        "# them so the state sampled for these VU-mode accesses is unambiguous.",
        *set_csr_bits("hstatus", "HSTATUS_HUKTE | HSTATUS_HU", regs.scratch, set_bits=False),
        *target_va(mode, getattr(mode, case.va_attr), regs),
        *bump_store_value(regs),
        "RVTEST_GOTO_LOWER_MODE VUmode",
    ]

    results: list[tuple[str, int]] = []
    for kind, coverpoint in zip(_ORDINARY_KINDS, case.coverpoints):
        asm, label, check_reg = access_test(
            test_data,
            regs,
            covergroup=covergroup,
            coverpoint=coverpoint,
            bin_name=f"{mode.name}_{case.bin_name}_{kind}",
            kind=kind,
        )
        lines.extend(asm)
        results.append((label, check_reg))

    lines.append("RVTEST_GOTO_MMODE")
    lines.extend(deferred_sigupds(test_data, results))
    return lines


def _mode_block(test_data: TestData, mode: SvMode, regs: SvukteRegs) -> list[str]:
    """Emit every hypervisor case for one translation mode."""
    lines = list(_enable_hypervisor_translation(mode))

    lines.append("")
    lines.append("# Explicit guest accesses from HS-mode (senvcfg.UKTE qualifies)")
    for case in _HS_CASES:
        lines.extend(_guest_case(test_data, mode, regs, case))

    lines.append("")
    lines.append("# Explicit guest accesses from U-mode (hstatus.HUKTE qualifies)")
    for case in _UMODE_CASES:
        lines.extend(_guest_case(test_data, mode, regs, case))

    lines.append("")
    lines.append("# Ordinary accesses from VU-mode (senvcfg.UKTE qualifies, vsatp is the active satp)")
    for case in _VU_CASES:
        lines.extend(_vu_case(test_data, mode, regs, case))

    lines.extend(["", *_disable_hypervisor_translation()])
    return mode_guarded(mode, lines)


@add_priv_test_generator(
    "SvukteH",
    required_extensions=["Svukte", "H"],
    march_extensions=["H"],
    extra_defines=[
        # Pulls in the G-stage and VS-stage page-table helpers.
        "#define RVTEST_HYPERVISOR",
        # Nine expected faults per translation mode, each recording a six-word entry
        # because M-mode exception entries widen when the hypervisor extension is present.
        "#define TRAP_SIGUPD_COUNT 256",
    ],
)
def make_svukteh(test_data: TestData) -> list[TestChunk]:
    """Generate the SvukteH hypervisor tests for every supported RV64 translation mode."""
    tc = test_data.begin_test_chunk()
    regs = allocate_regs(test_data)

    body = [*data_payload(regs), *init_store_value(regs)]
    for mode in SV_MODES:
        body.extend(["", *_mode_block(test_data, mode, regs)])

    tc.code.append(comment_banner("SvukteH", make_svukteh.__doc__))
    tc.code.extend(rv64_only(hypervisor_only(body)))

    release_regs(test_data, regs)
    return [test_data.end_test_chunk()]
