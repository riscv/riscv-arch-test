##################################
# priv/extensions/sv/SvPMP.py
#
# SvPMP translated-access tests.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate PMP checks for translated data and page-table regions."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk, trap_sigupd_count
from testgen.priv.extensions.pmp import helpers as pmp
from testgen.priv.extensions.sv.access import add_rwx_test
from testgen.priv.extensions.sv.assembly import DATA_REGION_ALIGNED
from testgen.priv.extensions.sv.generate import begin_sv_test, sv_data
from testgen.priv.extensions.sv.page_tables import SV32, SV39, SV48, SV57, PteFlags, SvMode, create_page_mapping
from testgen.priv.registry import add_priv_test_generator

PMP_PTE_VAS = {
    "sv32": ("0x00000000", "0x90000000"),
    "sv39": ("0x00000000", "0xFFFFFFFF80000000"),
    "sv48": ("0x00000000", "0xFFFFFF0080000000"),
    "sv57": ("0x0000000000000000", "0xFFFE000080000000"),
}
_PA_CFGS = (
    (pmp.cfg_byte("0101", "napot", pmp.cfg_shift(1)), "pmpcfg0_rx", 1),
    (pmp.cfg_byte("0011", "napot", pmp.cfg_shift(1)), "pmpcfg0_rw", 1),
    (pmp.cfg_byte("0100", "napot", pmp.cfg_shift(1)), "pmpcfg0_x", 2),
)
_MARCH = ["I", "Zicsr", "Zifencei"]
_PARAMS = ["NUM_PMP_ENTRIES: '>0'"]
_DEFINES = ["#define BOOT_TO_MMODE"]


def _begin_test(
    test_data: TestData,
    sv: SvMode,
    mode: str,
    topic: str,
    pmp_defines: list[str],
    *,
    pre_va_asm: tuple[str, ...],
    va_defs: tuple[tuple[str, str], ...] | None = None,
    va_code_override: str | None = None,
) -> TestChunk:
    split_name = f"{sv.name}_{topic}_{mode}"
    return begin_sv_test(
        test_data,
        sv,
        mode,
        split_name,
        code_prefix=pmp_defines,
        va_defs=va_defs,
        va_code_override=va_code_override,
        pre_va_asm=pre_va_asm,
    )


def _make_pmp_on_pa(test_data: TestData, sv: SvMode, mode: str) -> TestChunk:
    chunk = _begin_test(
        test_data,
        sv,
        mode,
        "pmp_on_pa",
        pmp.napot_mask_defines(5),
        pre_va_asm=(
            "RVTEST_PMP_SET_BACKGROUND x4",
            "",
            *pmp.set_pmpaddr("napot", 1, "rvtest_data_1"),
            "sfence.vma",
        ),
    )
    permissions = PteFlags(user=mode == "Umode")
    number = 0
    faults = 0
    for cfg, name, case_faults in _PA_CFGS:
        chunk.code.extend([*pmp.write_pmpcfg0(test_data, cfg, name), ""])
        for level in sv.levels_desc:
            number += 1
            faults += case_faults
            chunk.code.extend(
                [
                    f"// Test case {number}: translated access with {cfg}",
                    *create_page_mapping(sv, leaf_level=level, leaf_flags=permissions),
                    "sfence.vma",
                    "",
                    *add_rwx_test(test_data, sv, mode, "va_data", level, f"test{number}"),
                    "",
                ]
            )
    chunk.raw_data.extend(sv_data(sv, data_region_body=DATA_REGION_ALIGNED))
    chunk.trap_sigupd_count = trap_sigupd_count(faults)
    return test_data.end_test_chunk()


def _make_pmp_on_pte(test_data: TestData, sv: SvMode, mode: str) -> TestChunk:
    va_data, va_code = PMP_PTE_VAS[sv.name]
    chunk = _begin_test(
        test_data,
        sv,
        mode,
        "pmp_on_pte",
        pmp.napot_mask_defines(),
        pre_va_asm=("RVTEST_PMP_SET_BACKGROUND x4",),
        va_defs=(("va_data", va_data),),
        va_code_override=va_code,
    )
    permissions = PteFlags(user=mode == "Umode")
    for number, level in enumerate(sv.levels_desc, start=1):
        top = level == sv.levels - 1
        chunk.code.extend([*pmp.set_pmpaddr("napot", 0, sv.page_table_label(level)), ""])
        if top:
            chunk.code.extend(
                [
                    *pmp.write_pmpcfg0(
                        test_data,
                        pmp.cfg_byte("0100", "napot", pmp.cfg_shift(0)),
                        "write_pmpcfg0",
                    ),
                    ".if (UDB_PMP_GRANULARITY < 12)",
                ]
            )
        else:
            chunk.code.extend(["sfence.vma", ""])
        chunk.code.extend(
            [
                f"// Test case {number}: PMP blocks the level {level} page table",
                *create_page_mapping(sv, leaf_level=level, leaf_flags=permissions),
                "sfence.vma",
                "",
                *add_rwx_test(test_data, sv, mode, "va_data", level, f"test{number}"),
            ]
        )
        if top:
            chunk.code.append(".endif")
        chunk.code.append("")
    chunk.raw_data.extend(sv_data(sv, page_table_align="(UDB_PMP_GRANULARITY)"))
    chunk.trap_sigupd_count = trap_sigupd_count(sv.levels * 3)
    return test_data.end_test_chunk()


def _make_svpmp(test_data: TestData, sv: SvMode) -> list[TestChunk]:
    tests = []
    for mode in ("Smode", "Umode"):
        tests.extend((_make_pmp_on_pa(test_data, sv, mode), _make_pmp_on_pte(test_data, sv, mode)))
    return tests


@add_priv_test_generator(
    "SvPMP",
    required_extensions=["I", "Sv32", "Sm"],
    march_extensions=_MARCH,
    params=_PARAMS,
    extra_defines=_DEFINES,
)
def make_svpmp_sv32(test_data: TestData) -> list[TestChunk]:
    return _make_svpmp(test_data, SV32)


@add_priv_test_generator(
    "SvPMP",
    required_extensions=["I", "Sv39", "Sm"],
    march_extensions=_MARCH,
    params=_PARAMS,
    extra_defines=_DEFINES,
)
def make_svpmp_sv39(test_data: TestData) -> list[TestChunk]:
    return _make_svpmp(test_data, SV39)


@add_priv_test_generator(
    "SvPMP",
    required_extensions=["I", "Sv48", "Sm"],
    march_extensions=_MARCH,
    params=_PARAMS,
    extra_defines=_DEFINES,
)
def make_svpmp_sv48(test_data: TestData) -> list[TestChunk]:
    return _make_svpmp(test_data, SV48)


@add_priv_test_generator(
    "SvPMP",
    required_extensions=["I", "Sv57", "Sm"],
    march_extensions=_MARCH,
    params=_PARAMS,
    extra_defines=_DEFINES,
)
def make_svpmp_sv57(test_data: TestData) -> list[TestChunk]:
    return _make_svpmp(test_data, SV57)
