##################################
# priv/sv/suites/SvaduPMP.py
#
# SvaduPMP suite: hardware A/D updates blocked by PMP permissions on the page table.
# SPDX-License-Identifier: Apache-2.0
##################################

"""SvaduPMP suite table: with Svadu enabled but the page table only readable and
executable under PMP, the hardware A/D update must fault instead of writing the PTE."""

from __future__ import annotations

from testgen.priv.sv import add_sv_suite
from testgen.priv.sv import pmp_macros as C
from testgen.priv.sv.macros import RWX_VERIFICATION, template
from testgen.priv.sv.model import SVMODES, FileSpec, SvCase, SvMode
from testgen.priv.sv.suites.Sv import _leaf, _levels_desc, _sig3, _spec, _u, _walk

_ATTR = "// Developed by: Umer Shahid & Muhammad Zain"

# The data region is mapped at VA 0; the width of the constant follows the satp mode.
_VA_DATA = {"sv32": "0x00000000", "sv39": "0x000000000", "sv48": "0x000000000000", "sv57": "0x00000000000000"}

# A/D bit combinations: each one needs a hardware update that PMP will block.
_AD_CASES = (
    ("PTE_D | ", "PTE.A unset"),
    ("PTE_A | ", "PTE.D unset"),
    ("", "PTE.A and PTE.D unset"),
)

_RUNNER = template("pmp_adu_runner")


def _runner(sv: SvMode) -> str:
    """The RWX runner plus a readback of the PTE that hardware must not have updated."""
    chain = []
    for level in range(sv.levels - 1, -1, -1):
        kw = ".if" if level == sv.levels - 1 else ".elseif"
        chain += [f"  {kw} \\level == LEVEL{level}", f"    LA( a0, {C.pt_table(sv, level)})"]
    chain.append("  .endif")
    return _RUNNER.format(
        mul=10 if sv.xlen == 32 else 9,
        xlen=sv.xlen,
        load="lw" if sv.xlen == 32 else "ld",
        readback="\n".join(chain),
    )


@add_sv_suite("SvaduPMP")
def svadupmp_files() -> list[FileSpec]:
    """SvaduPMP: Svadu hardware A/D updates against a page table PMP made read/execute only."""
    specs: list[FileSpec] = []
    for name, va_data in _VA_DATA.items():
        sv = SVMODES[name]
        csr, mask = ("menvcfg", "MENVCFG_ADUE") if sv.xlen == 64 else ("menvcfgh", "MENVCFGH_ADUE")
        for mode in ("Smode", "Umode"):
            umode = mode == "Umode"
            cases: list[SvCase] = []
            n = 0
            for level in _levels_desc(sv):
                top = level == sv.levels - 1
                for i, (bits, desc) in enumerate(_AD_CASES):
                    n += 1
                    lead: list[str] = []
                    if i == 0:
                        # Point the PMP entry at the page table holding this level's PTE
                        lead += [*C.table_napot(C.pt_table(sv, level)), ""]
                        lead += [*C.cfg_write("PMP0CFG_RX", "write_pmpcfg0"), ""] if top else ["  sfence.vma", ""]
                    perms = _u(f"{bits}PTE_X | PTE_W | PTE_R | PTE_V", umode)
                    cases.append(
                        SvCase(
                            banner=(
                                f"{desc} in the level {level} PTE, page table is an RX-only PMP region:",
                                (
                                    "Then, in {mode}-Mode, the page is accessed --> required:"
                                    " access fault, PTE unchanged"
                                ),
                            ),
                            body=(
                                *lead,
                                (
                                    f"  // Test case {n}: {desc} | Test in {mode[0]}-Mode"
                                    " | expected = access fault, PTE unchanged"
                                ),
                                *_walk(sv, level),
                                _leaf(sv, perms, level),
                                "  sfence.vma",
                                "",
                                f"  TEST_CASES_RUNNER {mode}, va_data, LEVEL{level}, test{n}",
                            ),
                            sig_strs=(
                                *((C.cfg_str("write_pmpcfg0", "!"),) if n == 1 else ()),
                                *_sig3(f"test{n}"),
                                (f"test{n}_read_pte", f"Mismatch in PTE value in Test Case {n}!"),
                            ),
                            faults=1,
                            level=level,
                        )
                    )
            specs.append(
                _spec(
                    sv,
                    "Svadu_no_pmp_perm",
                    mode,
                    cases,
                    (RWX_VERIFICATION, _runner(sv), C.cfg_defines(0, "RX")),
                    extra_ext=("Svadu", "Sm"),
                    banner=_ATTR,
                    params=C.PARAMS,
                    extra_defines=C.DEFINES,
                    pre_va_asm=C.BACKGROUND,
                    setup_asm=(f"  LI(t0, {mask})", f"  csrs {csr}, t0"),
                    va_defs=(("va_data", va_data),),
                    data_region_body=C.data_and_aligned_tables(sv),
                    emit_page_tables=False,
                    emit_trap_count=False,
                )
            )
    return specs
