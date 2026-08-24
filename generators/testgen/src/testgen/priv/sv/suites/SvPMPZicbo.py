##################################
# priv/sv/suites/SvPMPZicbo.py
#
# SvPMPZicbo suite: cache-block operations against PMP-protected regions under VM.
# SPDX-License-Identifier: Apache-2.0
##################################

"""SvPMPZicbo suite table: cbo.clean/flush/inval and cbo.zero on a translated address
whose physical page (pmp_on_pa) or page table (pmp_on_pte) is an X-only PMP region."""

from __future__ import annotations

from testgen.priv.sv import add_sv_suite
from testgen.priv.sv import pmp_macros as C
from testgen.priv.sv.macros import template
from testgen.priv.sv.model import SVMODES, FileSpec, SvCase, SvMode
from testgen.priv.sv.suites.Sv import _leaf, _levels_desc, _spec, _u, _walk
from testgen.priv.sv.suites.SvPMP import _PTE_VAS
from testgen.priv.sv.suites.SvZicbo import _BODY_NOARG, _VA_MATH_RV32, _VA_MATH_RV64, _runner

_ATTR = "// Developed by: Umer Shahid & Muhammad Zain"

_RWXV = "PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V"

# Cache-block batteries; unlike the SvZicbo suite these take no testcase argument
# and record no signature, because every operation is expected to fault.
V_CBOM = template("pmp_v_cbom")

V_CBOZ = template("pmp_v_cboz")

# (extension, menvcfg enable mask, battery, faults per case)
_FAMILIES = {
    "zicbom": ("Zicbom", "MENVCFG_CBCFE | MENVCFG_CBIE", V_CBOM, 3),
    "zicboz": ("Zicboz", "MENVCFG_CBZE", V_CBOZ, 1),
}


def _macros(sv: SvMode, family: str) -> tuple[str, ...]:
    """The battery plus the no-signature runner (identical to the SvZicbo prefetch runner)."""
    va_math = _VA_MATH_RV32 if sv.xlen == 32 else _VA_MATH_RV64
    battery = _FAMILIES[family][2]
    runner = _runner("TEST_CASES_RUNNER", "LOWER_MODE, VA, level", va_math, "", _BODY_NOARG)
    return (battery, runner, C.cfg_defines(0, "X"))


def _envcfg(family: str, mode: str) -> tuple[str, ...]:
    """Enable the cache-block operations for the mode under test."""
    mask = _FAMILIES[family][1]
    lines = [f"  LI(t0, {mask})", "  csrs menvcfg, t0"]
    if mode == "Umode":
        lines.append("  csrs senvcfg, t0")
    return tuple(lines)


def _case(n: int, level: int, mode: str, expected: str, pte_lines: list[str], lead: tuple[str, ...]) -> tuple[str, ...]:
    return (
        *lead,
        f"  // Test case {n}: Test in {mode[0]}-Mode | RWX set | expected = {expected}",
        *pte_lines,
        "  sfence.vma",
        "",
        f"  TEST_CASES_RUNNER {mode}, va_data, LEVEL{level}",
    )


def _on_pa(sv: SvMode, mode: str, family: str) -> FileSpec:
    """The physical page holding the data region is an X-only PMP region."""
    ext, _, _, faults = _FAMILIES[family]
    perms = _u(_RWXV, mode == "Umode")
    expected = f"{faults} access fault(s)"
    cases = [
        SvCase(
            banner=(
                f"Data region is an X-only NAPOT PMP region, PTE at level {level} with RWX permissions:",
                "Then, in {mode}-Mode, the cache-block operations run --> required: " + expected,
            ),
            body=_case(n, level, mode, expected, [*_walk(sv, level), _leaf(sv, perms, level)], ()),
            sig_strs=(C.cfg_str("pmpcfg0_x", " while setting X permission!"),) if n == 1 else (),
            faults=faults,
            level=level,
        )
        for n, level in enumerate(_levels_desc(sv), start=1)
    ]
    return _spec(
        sv,
        f"pmp_on_pa_{family}",
        mode,
        cases,
        _macros(sv, family),
        extra_ext=(ext, "Sm"),
        banner=_ATTR,
        march=f"{sv.march}_{family}",
        params=C.PARAMS,
        extra_defines=C.DEFINES,
        sig_init="",
        pre_va_asm=(
            *C.BACKGROUND,
            "",
            *C.data_napot(0, sfence=False),
            "",
            *C.cfg_write("PMP0CFG_X", "pmpcfg0_x"),
        ),
        setup_asm=_envcfg(family, mode),
        data_region_body=C.DATA_REGION_ALIGNED,
    )


def _on_pte(sv: SvMode, mode: str, family: str) -> FileSpec:
    """The page table holding the leaf PTE is an X-only PMP region."""
    ext, _, _, faults = _FAMILIES[family]
    perms = _u(_RWXV, mode == "Umode")
    expected = f"{faults} Store access fault(s)"
    cases: list[SvCase] = []
    for n, level in enumerate(_levels_desc(sv), start=1):
        top = level == sv.levels - 1
        lead = [*C.table_napot(C.pt_table(sv, level)), ""]
        if top:
            # With a granularity of 4KB or more the whole root table would lose read
            # permission and S-mode could not be entered, so that case is skipped.
            lead += [*C.cfg_write("PMP0CFG_X", "write_pmpcfg0"), "  .if (UDB_PMP_GRANULARITY < 12)"]
        else:
            lead += ["  sfence.vma", ""]
        body = list(_case(n, level, mode, expected, [*_walk(sv, level), _leaf(sv, perms, level)], tuple(lead)))
        if top:
            body.append("  .endif")
        cases.append(
            SvCase(
                banner=(
                    f"Page table holding the level {level} PTE is an X-only NAPOT PMP region:",
                    "Then, in {mode}-Mode, the cache-block operations run --> required: " + expected,
                ),
                body=tuple(body),
                sig_strs=(C.cfg_str("write_pmpcfg0", "!"),) if n == 1 else (),
                faults=faults,
                level=level,
            )
        )
    return _spec(
        sv,
        f"pmp_on_pte_{family}",
        mode,
        cases,
        _macros(sv, family),
        extra_ext=(ext, "Sm"),
        banner=_ATTR,
        march=f"{sv.march}_{family}",
        params=C.PARAMS,
        extra_defines=C.DEFINES,
        sig_init="",
        pre_va_asm=C.BACKGROUND,
        setup_asm=_envcfg(family, mode),
        va_defs=(("va_data", _PTE_VAS[sv.name][0]),),
        va_code_override=_PTE_VAS[sv.name][1],
        data_region_body=C.data_and_aligned_tables(sv),
        emit_page_tables=False,
    )


@add_sv_suite("SvPMPZicbo")
def svpmpzicbo_files() -> list[FileSpec]:
    """SvPMPZicbo: Zicbom/Zicboz operations through PMP-protected pages and page tables."""
    specs: list[FileSpec] = []
    for sv in SVMODES.values():
        for mode in ("Smode", "Umode"):
            for family in _FAMILIES:
                specs.append(_on_pa(sv, mode, family))
                specs.append(_on_pte(sv, mode, family))
    return specs
