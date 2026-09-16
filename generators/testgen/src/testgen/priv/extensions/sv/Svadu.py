##################################
# priv/extensions/sv/Svadu.py
#
# Svadu hardware A/D-bit tests.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate hardware A/D-bit update tests."""

from testgen.asm.helpers import write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.sv.access import virtual_address
from testgen.priv.extensions.sv.generate import begin_sv_test, sv_data
from testgen.priv.extensions.sv.page_tables import (
    SV32,
    SV39,
    SV48,
    SV57,
    PteFlags,
    SvMode,
    create_leaf_pte,
    create_page_mapping,
)
from testgen.priv.registry import add_priv_test_generator

_VAS = {
    "sv32": {1: ("0x00400000", "0x00800000", "0x00C00000"), 0: ("0x01001000", "0x01002000", "0x01003000")},
    "sv39": {
        2: ("0x040000000", "0x080000000", "0x0C0000000"),
        1: ("0x000200000", "0x000400000", "0x000600000"),
        0: ("0x000001000", "0x000002000", "0x000003000"),
    },
    "sv48": {
        3: ("0x008080000000", "0x010080000000", "0x018080000000"),
        2: ("0x028040000000", "0x028080000000", "0x0280C0000000"),
        1: ("0x028000200000", "0x028000400000", "0x028000600000"),
        0: ("0x028000001000", "0x028000002000", "0x028000003000"),
    },
    "sv57": {
        4: ("0x01000000000000", "0x02000000000000", "0x03000000000000"),
        3: ("0x04008000000000", "0x04010000000000", "0x04018000000000"),
        2: ("0x04020040000000", "0x04020080000000", "0x040200C0000000"),
        1: ("0x04020300200000", "0x04020300400000", "0x04020300600000"),
        0: ("0x04020300801000", "0x04020300802000", "0x04020300803000"),
    },
}
_CODE_VA = {"sv32": "0x90000000", "sv39": "0x180000000", "sv48": "0x030080000000", "sv57": "0x05000080000000"}
_MARCH = ["I", "Zicsr", "Zifencei"]


def _add_adu_access(test_data: TestData, sv: SvMode, mode: str, level: int, number: int) -> list[str]:
    labels = {
        name: test_data.add_testcase(f"test{number}_{name}", "cp_ad_update", "Svadu_cg").removesuffix(":")
        for name in ("store", "load", "exec", "read_store_pte", "read_load_pte", "read_exec_pte")
    }
    table = "rvtest_Sroot_pg_tbl" if level == sv.levels - 1 else f"rvtest_slvl{level}_pg_tbl"
    load = "lw" if sv.xlen == 32 else "ld"
    stride = sv.xlen // 8
    return [
        *virtual_address(sv, f"va_data_l{level}_w", level, destination="a0", scratch="t0", merge_sv32_base_page=True),
        *virtual_address(sv, f"va_data_l{level}_r", level, destination="a1", scratch="t0", merge_sv32_base_page=True),
        *virtual_address(sv, f"va_data_l{level}_x", level, destination="a5", scratch="t0", merge_sv32_base_page=True),
        f"RVTEST_GOTO_LOWER_MODE {mode}",
        "addi a2, a2, 16",
        f"{labels['store']}:",
        "sw a2, 20(a0)",
        "nop",
        f"{labels['load']}:",
        "lw a3, 20(a1)",
        "nop",
        f"{labels['exec']}:",
        "jalr ra, a5, 0",
        "nop",
        "RVTEST_GOTO_MMODE",
        write_sigupd(12, test_data, label=labels["store"]),
        write_sigupd(13, test_data, label=labels["load"]),
        write_sigupd(14, test_data, label=labels["exec"]),
        f"LA(a0, {table})",
        f"{labels['read_store_pte']}:",
        f"{load} a4, {stride}(a0)",
        write_sigupd(14, test_data, label=labels["read_store_pte"]),
        f"{labels['read_load_pte']}:",
        f"{load} a4, {stride * 2}(a0)",
        write_sigupd(14, test_data, label=labels["read_load_pte"]),
        f"{labels['read_exec_pte']}:",
        f"{load} a4, {stride * 3}(a0)",
        write_sigupd(14, test_data, label=labels["read_exec_pte"]),
    ]


def _make_svadu_mode(test_data: TestData, sv: SvMode, mode: str) -> TestChunk:
    va_table = _VAS[sv.name]
    va_defs = tuple(
        (f"va_data_l{level}_{suffix}", va)
        for level in sorted(va_table, reverse=True)
        for suffix, va in zip(("w", "r", "x"), va_table[level], strict=True)
    )
    csr, mask = ("menvcfg", "MENVCFG_ADUE") if sv.xlen == 64 else ("menvcfgh", "MENVCFGH_ADUE")
    chunk = begin_sv_test(
        test_data,
        sv,
        mode,
        f"{sv.name}_Svadu_{mode}",
        coverpoint="cp_ad_update",
        va_defs=va_defs,
        va_code_override=_CODE_VA[sv.name],
        setup_asm=(f"LI(t0, {mask})", f"csrs {csr}, t0"),
    )
    number = 0
    for level in sorted(va_table, reverse=True):
        va_w, va_r, va_x = (f"va_data_l{level}_{suffix}" for suffix in ("w", "r", "x"))
        for accessed, dirty, description in (
            (False, True, "PTE.A unset"),
            (True, False, "PTE.D unset"),
            (False, False, "PTE.A and PTE.D unset"),
        ):
            number += 1
            permissions = PteFlags(
                user=mode == "Umode",
                accessed=accessed,
                dirty=dirty,
            )
            chunk.code.extend(
                [
                    f"// Test case {number}: {description} at level {level}",
                    *create_page_mapping(
                        sv,
                        virtual_address=va_w,
                        leaf_level=level,
                        leaf_flags=permissions,
                    ),
                    create_leaf_pte(sv, virtual_address=va_r, level=level, flags=permissions),
                    create_leaf_pte(sv, virtual_address=va_x, level=level, flags=permissions),
                    "sfence.vma",
                    "",
                    *_add_adu_access(test_data, sv, mode, level, number),
                    "",
                ]
            )
    chunk.raw_data.extend(sv_data(sv))
    return test_data.end_test_chunk()


def _make_svadu(test_data: TestData, sv: SvMode) -> list[TestChunk]:
    return [_make_svadu_mode(test_data, sv, mode) for mode in ("Smode", "Umode")]


@add_priv_test_generator(
    "Svadu",
    required_extensions=["I", "Sv32", "Svadu"],
    march_extensions=_MARCH,
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svadu_sv32(test_data: TestData) -> list[TestChunk]:
    return _make_svadu(test_data, SV32)


@add_priv_test_generator(
    "Svadu",
    required_extensions=["I", "Sv39", "Svadu"],
    march_extensions=_MARCH,
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svadu_sv39(test_data: TestData) -> list[TestChunk]:
    return _make_svadu(test_data, SV39)


@add_priv_test_generator(
    "Svadu",
    required_extensions=["I", "Sv48", "Svadu"],
    march_extensions=_MARCH,
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svadu_sv48(test_data: TestData) -> list[TestChunk]:
    return _make_svadu(test_data, SV48)


@add_priv_test_generator(
    "Svadu",
    required_extensions=["I", "Sv57", "Svadu"],
    march_extensions=_MARCH,
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svadu_sv57(test_data: TestData) -> list[TestChunk]:
    return _make_svadu(test_data, SV57)
