##################################
# priv/extensions/sv/SvaduPMP.py
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
from testgen.priv.extensions.sv.access import add_rwx_test
from testgen.priv.extensions.sv.generate import begin_sv_test, sv_data
from testgen.priv.extensions.sv.page_tables import SV32, SV39, SV48, SV57, PteFlags, SvMode, create_page_mapping
from testgen.priv.registry import add_priv_test_generator

_VA_DATA = {"sv32": "0x00000000", "sv39": "0x000000000", "sv48": "0x000000000000", "sv57": "0x00000000000000"}
_AD_CASES = (
    (False, True, "PTE.A unset"),
    (True, False, "PTE.D unset"),
    (False, False, "PTE.A and PTE.D unset"),
)
_MARCH = ["I", "Zicsr", "Zifencei"]


def _add_pte_readback(test_data: TestData, sv: SvMode, level: int, number: int) -> list[str]:
    label = test_data.add_testcase(f"test{number}_read_pte", "cp_ad_update", "SvaduPMP_cg").removesuffix(":")
    return [
        f"LA(a0, {sv.page_table_label(level)})",
        f"{label}:",
        f"{'lw' if sv.xlen == 32 else 'ld'} a4, 0(a0)",
        write_sigupd(14, test_data, label=label),
    ]


def _make_svadupmp_mode(test_data: TestData, sv: SvMode, mode: str) -> TestChunk:
    csr, mask = ("menvcfg", "MENVCFG_ADUE") if sv.xlen == 64 else ("menvcfgh", "MENVCFGH_ADUE")
    chunk = begin_sv_test(
        test_data,
        sv,
        mode,
        f"{sv.name}_Svadu_no_pmp_perm_{mode}",
        coverpoint="cp_ad_update",
        code_prefix=pmp.napot_mask_defines(),
        va_defs=(("va_data", _VA_DATA[sv.name]),),
        pre_va_asm=("RVTEST_PMP_SET_BACKGROUND x4",),
        setup_asm=(f"LI(t0, {mask})", f"csrs {csr}, t0"),
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
            chunk.code.extend(
                [
                    f"// Test case {number}: {description}; PMP blocks the A/D update",
                    *create_page_mapping(sv, leaf_level=level, leaf_flags=permissions),
                    "sfence.vma",
                    "",
                    *add_rwx_test(test_data, sv, mode, "va_data", level, f"test{number}"),
                    *_add_pte_readback(test_data, sv, level, number),
                    "",
                ]
            )
    chunk.raw_data.extend(sv_data(sv, page_table_align="(UDB_PMP_GRANULARITY)"))
    return test_data.end_test_chunk()


def _make_svadupmp(test_data: TestData, sv: SvMode) -> list[TestChunk]:
    return [_make_svadupmp_mode(test_data, sv, mode) for mode in ("Smode", "Umode")]


@add_priv_test_generator(
    "SvaduPMP",
    required_extensions=["I", "Sv32", "Svadu", "Sm"],
    march_extensions=_MARCH,
    params=["NUM_PMP_ENTRIES: '>0'"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svadupmp_sv32(test_data: TestData) -> list[TestChunk]:
    return _make_svadupmp(test_data, SV32)


@add_priv_test_generator(
    "SvaduPMP",
    required_extensions=["I", "Sv39", "Svadu", "Sm"],
    march_extensions=_MARCH,
    params=["NUM_PMP_ENTRIES: '>0'"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svadupmp_sv39(test_data: TestData) -> list[TestChunk]:
    return _make_svadupmp(test_data, SV39)


@add_priv_test_generator(
    "SvaduPMP",
    required_extensions=["I", "Sv48", "Svadu", "Sm"],
    march_extensions=_MARCH,
    params=["NUM_PMP_ENTRIES: '>0'"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svadupmp_sv48(test_data: TestData) -> list[TestChunk]:
    return _make_svadupmp(test_data, SV48)


@add_priv_test_generator(
    "SvaduPMP",
    required_extensions=["I", "Sv57", "Svadu", "Sm"],
    march_extensions=_MARCH,
    params=["NUM_PMP_ENTRIES: '>0'"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svadupmp_sv57(test_data: TestData) -> list[TestChunk]:
    return _make_svadupmp(test_data, SV57)
