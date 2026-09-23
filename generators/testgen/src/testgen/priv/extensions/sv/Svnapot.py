##################################
# priv/extensions/sv/Svnapot.py
#
# Svnapot translation tests.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate 64 KiB NAPOT translation and reserved-encoding tests."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.sv.access import add_rwx_test
from testgen.priv.extensions.sv.assembly import NAPOT_DATA, NAPOT_RESERVED_DATA
from testgen.priv.extensions.sv.generate import begin_sv_test, sv_data
from testgen.priv.extensions.sv.page_tables import (
    SV39,
    SV48,
    SV57,
    PteFlags,
    SvMode,
    create_leaf_pte,
    create_page_mapping,
)
from testgen.priv.registry import add_priv_test_generator

_NAPOT_VA = {"sv39": "0x140200000", "sv48": "0x0280C0410000", "sv57": "0x400280C0410000"}
_MARCH = ["I", "Zicsr", "Zifencei"]


def _permissions(umode: bool, ppn_bits: str | None = "(1 << 13)") -> PteFlags:
    extra_bits = ("PTE_N", ppn_bits) if ppn_bits else ("PTE_N",)
    return PteFlags(user=umode, extra=extra_bits)


def _begin_test(test_data: TestData, sv: SvMode, mode: str, topic: str) -> TestChunk:
    return begin_sv_test(
        test_data,
        sv,
        mode,
        f"{sv.name}_{topic}_{mode}",
        va_defs=(("va_data", _NAPOT_VA[sv.name]),),
    )


def _finish_test(test_data: TestData, sv: SvMode, data: str) -> TestChunk:
    assert test_data.test_chunk is not None
    test_data.test_chunk.raw_data.extend(sv_data(sv, data_align=16, data_region_body=data))
    return test_data.end_test_chunk()


def _make_napot(test_data: TestData, sv: SvMode, mode: str) -> TestChunk:
    chunk = _begin_test(test_data, sv, mode, "Svnapot")
    permissions = _permissions(mode == "Umode")
    chunk.code.extend(
        [
            "// 64 KiB NAPOT group of 16 PTEs",
            *create_page_mapping(sv, leaf_level=0, leaf_flags=permissions),
            *(
                create_leaf_pte(
                    sv,
                    virtual_address=f"(va_data+0x{offset:X}000)",
                    level=0,
                    flags=permissions,
                )
                for offset in range(1, 16)
            ),
            "sfence.vma",
            "",
        ]
    )
    for access, offset in enumerate(("", "+0x2000", "+0xF000"), start=1):
        chunk.code.extend(
            [
                *add_rwx_test(
                    test_data,
                    sv,
                    mode,
                    f"va_data{offset}",
                    0,
                    f"test1_access{access}",
                    direct_address=True,
                ),
                "",
            ]
        )
    return _finish_test(test_data, sv, NAPOT_DATA)


def _make_reserved(test_data: TestData, sv: SvMode, mode: str) -> TestChunk:
    chunk = _begin_test(test_data, sv, mode, "Svnapot_reserved_enc")
    chunk.code.append("#ifdef S1P12P0_OR_LATER_SUPPORTED")
    umode = mode == "Umode"
    number = 0
    for level in range(sv.levels - 1, 0, -1):
        number += 1
        chunk.code.extend(
            [
                f"// PTE.N on a level {level} superpage",
                *create_page_mapping(sv, leaf_level=level, leaf_flags=_permissions(umode, ppn_bits=None)),
                "sfence.vma",
                "",
                *add_rwx_test(test_data, sv, mode, "va_data", level, f"test{number}"),
                "",
            ]
        )
    for encoding in ("(1 << 10)", "(2 << 10)", "(4 << 10)", None):
        number += 1
        chunk.code.extend(
            [
                "// Reserved NAPOT PPN encoding",
                *create_page_mapping(sv, leaf_level=0, leaf_flags=_permissions(umode, ppn_bits=encoding)),
                "sfence.vma",
                "",
                *add_rwx_test(test_data, sv, mode, "va_data", 0, f"test{number}"),
                "",
            ]
        )
    chunk.code.append("#endif")
    return _finish_test(test_data, sv, NAPOT_RESERVED_DATA)


def _make_svnapot(test_data: TestData, sv: SvMode) -> list[TestChunk]:
    tests = []
    for mode in ("Smode", "Umode"):
        tests.extend((_make_napot(test_data, sv, mode), _make_reserved(test_data, sv, mode)))
    return tests


@add_priv_test_generator(
    "Svnapot",
    required_extensions=["I", "Sv39", "Svnapot"],
    march_extensions=_MARCH,
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svnapot_sv39(test_data: TestData) -> list[TestChunk]:
    return _make_svnapot(test_data, SV39)


@add_priv_test_generator(
    "Svnapot",
    required_extensions=["I", "Sv48", "Svnapot"],
    march_extensions=_MARCH,
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svnapot_sv48(test_data: TestData) -> list[TestChunk]:
    return _make_svnapot(test_data, SV48)


@add_priv_test_generator(
    "Svnapot",
    required_extensions=["I", "Sv57", "Svnapot"],
    march_extensions=_MARCH,
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svnapot_sv57(test_data: TestData) -> list[TestChunk]:
    return _make_svnapot(test_data, SV57)
