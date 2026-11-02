##################################
# priv/extensions/pmp/Svadu.py
#
# Svadu tests with PMP-protected page tables.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate hardware A/D updates blocked by PMP permissions."""

from testgen.asm.helpers import write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.pmp import helpers as pmp
from testgen.priv.extensions.sv.access import ad_crosses, add_rwx_test, cross_names
from testgen.priv.extensions.sv.generate import SvRegs, begin_sv_test, end_sv_test, sv_data
from testgen.priv.extensions.sv.page_tables import SV32, SV39, SV48, SV57, PteFlags, SvMode, create_page_mapping
from testgen.priv.registry import add_priv_test_generator

_VA_DATA = {"sv32": "0x00000000", "sv39": "0x000000000", "sv48": "0x000000000000", "sv57": "0x00000000000000"}
_PMP = "_pmpW_unset"
_AD_CASES = (
    (False, True, "PTE.A unset"),
    (True, False, "PTE.D unset"),
    (False, False, "PTE.A and PTE.D unset"),
)


def _add_pte_readback(test_data: TestData, sv: SvMode, regs: SvRegs, level: int, number: int, cross: str) -> list[str]:
    label = test_data.add_testcase(f"test{number}_read_pte", cross, "PMP_Svadu_cg").removesuffix(":")
    return [
        f"LA(x{regs.scratch}, {sv.page_table_label(level)})",
        f"{label}:",
        f"{'lw' if sv.xlen == 32 else 'ld'} x{regs.result}, 0(x{regs.scratch})",
        write_sigupd(regs.result, test_data, label=label),
    ]


def _make_svadupmp_mode(test_data: TestData, sv: SvMode, mode: str) -> TestChunk:
    csr, mask = ("menvcfg", "MENVCFG_ADUE") if sv.xlen == 64 else ("menvcfgh", "MENVCFGH_ADUE")
    regs = SvRegs.allocate(test_data)
    chunk = begin_sv_test(
        test_data,
        regs,
        sv,
        mode,
        f"Svadu_{sv.name}_Svadu_no_pmp_perm_{mode}",
        coverpoint=cross_names(
            *(ad_crosses("PMP_Svadu_cg", mode, accessed=accessed, infix=_PMP) for accessed in (False, True))
        ),
        code_prefix=pmp.napot_mask_defines(),
        va_defs=(("va_data", _VA_DATA[sv.name]),),
        pre_va_asm=(f"RVTEST_PMP_SET_BACKGROUND x{regs.scratch}",),
        setup_asm=(f"LI(x{regs.scratch}, {mask})", f"csrs {csr}, x{regs.scratch}"),
    )
    number = 0
    for level in sv.levels_desc:
        for index, (accessed, dirty, description) in enumerate(_AD_CASES):
            number += 1
            if index == 0:
                chunk.code.extend([*pmp.set_pmpaddr("napot", 0, sv.page_table_label(level)), ""])
                if level == sv.levels - 1:
                    chunk.code.extend(
                        [
                            *pmp.write_pmpcfg0(
                                test_data,
                                pmp.cfg_byte("0101", "napot", pmp.cfg_shift(0)),
                                "write_pmpcfg0",
                                "PMP_pagetable",
                            ),
                            "",
                        ]
                    )
                else:
                    chunk.code.extend(["sfence.vma", ""])
            permissions = PteFlags(
                user=mode == "Umode",
                accessed=accessed,
                dirty=dirty,
            )
            crosses = ad_crosses("PMP_Svadu_cg", mode, accessed=accessed, infix=_PMP)
            chunk.code.extend(
                [
                    f"// Test case {number}: {description}; PMP blocks the A/D update",
                    *create_page_mapping(sv, leaf_level=level, leaf_flags=permissions),
                    "sfence.vma",
                    "",
                    *add_rwx_test(
                        test_data,
                        sv,
                        regs,
                        mode,
                        "va_data",
                        level,
                        f"test{number}",
                        driver_mode="Mmode",
                        crosses=crosses,
                    ),
                    # The PTE readback checks that PMP blocked the A/D update; it shares the store's cross.
                    *_add_pte_readback(test_data, sv, regs, level, number, crosses.store),
                    "",
                ]
            )
    chunk.raw_data.extend(sv_data(sv, regs, page_table_align="(UDB_PMP_GRANULARITY)"))
    return end_sv_test(test_data, regs)


def _make_svadupmp(test_data: TestData, sv: SvMode) -> list[TestChunk]:
    return [_make_svadupmp_mode(test_data, sv, mode) for mode in ("Smode", "Umode")]


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sv32", "Svadu", "Sm"],
    march_extensions=["Svadu"],
    params=["NUM_PMP_ENTRIES: '>0'"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svadupmp_sv32(test_data: TestData) -> list[TestChunk]:
    return _make_svadupmp(test_data, SV32)


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sv39", "Svadu", "Sm"],
    march_extensions=["Svadu"],
    params=["NUM_PMP_ENTRIES: '>0'"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svadupmp_sv39(test_data: TestData) -> list[TestChunk]:
    return _make_svadupmp(test_data, SV39)


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sv48", "Svadu", "Sm"],
    march_extensions=["Svadu"],
    params=["NUM_PMP_ENTRIES: '>0'"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svadupmp_sv48(test_data: TestData) -> list[TestChunk]:
    return _make_svadupmp(test_data, SV48)


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sv57", "Svadu", "Sm"],
    march_extensions=["Svadu"],
    params=["NUM_PMP_ENTRIES: '>0'"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svadupmp_sv57(test_data: TestData) -> list[TestChunk]:
    return _make_svadupmp(test_data, SV57)
