##################################
# priv/sv/suites/SvPMP.py
#
# SvPMP suite: PMP applied to the data region and to the page tables.
# SPDX-License-Identifier: Apache-2.0
##################################

"""SvPMP suite table: a PMP entry over the test data region (pmp_on_pa) or over
each page table in turn (pmp_on_pte), checked through an ordinary Sv page walk."""

from __future__ import annotations

from testgen.priv.sv import add_sv_suite
from testgen.priv.sv import pmp_macros as C
from testgen.priv.sv.model import SVMODES, FileSpec, SvCase, SvMode
from testgen.priv.sv.suites.Sv import _leaf, _levels_desc, _sig3, _spec, _std_macros, _u, _walk

_ATTR = "// Developed by: Umer Shahid & Muhammad Zain"

_RWXV = "PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V"

# pmp_on_pte maps the data region at VA 0 and moves the code region to the top of
# the address space, so the PMP entry on a page table cannot also cover the code.
_PTE_VAS = {
    "sv32": ("0x00000000", "0x90000000"),
    "sv39": ("0x00000000", "0xFFFFFFFF80000000"),
    "sv48": ("0x00000000", "0xFFFFFF0080000000"),
    "sv57": ("0x0000000000000000", "0xFFFE000080000000"),
}

# PMP configurations applied to the data region, with the faults each one causes
# per page level and the signature string recorded for the pmpcfg0 write.
_PA_CFGS = (
    ("PMP1CFG_RX", "pmpcfg0_rx", " while setting RX permission!", "Store access fault", 1),
    ("PMP1CFG_RW", "pmpcfg0_rw", " while setting RW permission!", "Instruction access fault", 1),
    ("PMP1CFG_X", "pmpcfg0_x", " while setting X permission!", "Store access fault, Load access fault", 2),
)


def _case(n: int, level: int, mode: str, inline: str, pte_lines: list[str], lead: tuple[str, ...] = ()) -> list[str]:
    """Body lines for one test case: optional lead-in, PTE setup, then the runner."""
    return [
        *lead,
        f"  // Test case {n}: {inline}",
        *pte_lines,
        "  sfence.vma",
        "",
        f"  TEST_CASES_RUNNER {mode}, va_data, LEVEL{level}, test{n}",
    ]


def _pmp_on_pa(sv: SvMode, mode: str) -> FileSpec:
    """One PMP entry covers the data region; each PMP permission set is tried at every level."""
    umode = mode == "Umode"
    perms = _u(_RWXV, umode)
    cases: list[SvCase] = []
    n = 0
    for cfg, label, what, expected, faults in _PA_CFGS:
        for i, level in enumerate(_levels_desc(sv)):
            n += 1
            # The pmpcfg0 write opens each permission group; all three signature
            # strings are attached to the first case so the data section keeps
            # the hand-written ordering (all pmpcfg strings, then the testcases).
            lead = (*C.cfg_write(cfg, label), "") if i == 0 else ()
            sig = _sig3(f"test{n}")
            if n == 1:
                sig = (*(C.cfg_str(lbl, w) for _, lbl, w, _, _ in _PA_CFGS), *sig)
            cases.append(
                SvCase(
                    banner=(
                        (
                            f"Data region is a NAPOT PMP region with {cfg.removeprefix('PMP1CFG_')} permissions,"
                            f" PTE at level {level} with RWX permissions:"
                        ),
                        "Then, in {mode}-Mode, the page is accessed --> required: " + expected,
                    ),
                    body=tuple(
                        _case(
                            n,
                            level,
                            mode,
                            f"Test in {mode[0]}-Mode | RWX bit set | expected = {expected}",
                            [*_walk(sv, level), _leaf(sv, perms, level)],
                            lead,
                        )
                    ),
                    sig_strs=sig,
                    faults=faults,
                    level=level,
                )
            )
    return _spec(
        sv,
        "pmp_on_pa",
        mode,
        cases,
        (*_std_macros(sv), C.cfg_defines(1, "RX", "RW", "X")),
        extra_ext=("Sm",),
        banner=_ATTR,
        params=C.PARAMS,
        extra_defines=C.DEFINES,
        pre_va_asm=(*C.BACKGROUND, "", *C.data_napot(1)),
        data_region_body=C.DATA_REGION_ALIGNED,
    )


def _pmp_on_pte(sv: SvMode, mode: str) -> FileSpec:
    """One PMP entry with X-only permission covers the page table holding the leaf PTE."""
    umode = mode == "Umode"
    perms = _u(_RWXV, umode)
    expected = "Store access fault, Load access fault, Instruction access fault"
    cases: list[SvCase] = []
    for n, level in enumerate(_levels_desc(sv), start=1):
        top = level == sv.levels - 1
        lead = [*C.table_napot(C.pt_table(sv, level)), ""]
        if top:
            # Only the first group writes pmpcfg0; with a granularity of 4KB or more the
            # whole root table would lose read permission, so that case is skipped.
            lead += [
                *C.cfg_write("PMP0CFG_X", "write_pmpcfg0"),
                "  .if (UDB_PMP_GRANULARITY < 12)",
            ]
        else:
            lead += ["  sfence.vma", ""]
        body = _case(
            n,
            level,
            mode,
            f"Test in {mode[0]}-Mode | RWX set | expected = {expected}",
            [*_walk(sv, level), _leaf(sv, perms, level)],
            tuple(lead),
        )
        if top:
            body.append("  .endif")
        cases.append(
            SvCase(
                banner=(
                    f"Page table holding the level {level} PTE is an X-only NAPOT PMP region:",
                    "Then, in {mode}-Mode, the page is accessed --> required: " + expected,
                ),
                body=tuple(body),
                sig_strs=((C.cfg_str("write_pmpcfg0", "!"), *_sig3(f"test{n}")) if n == 1 else _sig3(f"test{n}")),
                faults=3,
                level=level,
            )
        )
    return _spec(
        sv,
        "pmp_on_pte",
        mode,
        cases,
        (*_std_macros(sv), C.cfg_defines(0, "X")),
        extra_ext=("Sm",),
        banner=_ATTR,
        params=C.PARAMS,
        extra_defines=C.DEFINES,
        pre_va_asm=C.BACKGROUND,
        va_defs=(("va_data", _PTE_VAS[sv.name][0]),),
        va_code_override=_PTE_VAS[sv.name][1],
        data_region_body=C.data_and_aligned_tables(sv),
        emit_page_tables=False,
    )


@add_sv_suite("SvPMP")
def svpmp_files() -> list[FileSpec]:
    """SvPMP: PMP on the translated data region and on the page tables themselves."""
    specs: list[FileSpec] = []
    for sv in SVMODES.values():
        for mode in ("Smode", "Umode"):
            specs.append(_pmp_on_pa(sv, mode))
            specs.append(_pmp_on_pte(sv, mode))
    return specs
