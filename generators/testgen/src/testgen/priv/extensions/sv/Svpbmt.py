##################################
# priv/extensions/sv/Svpbmt.py
#
# Svpbmt page-based memory-type tests.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate Svpbmt leaf and non-leaf PTE tests."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.sv.access import add_rwx_test
from testgen.priv.extensions.sv.generate import begin_sv_test, sv_data
from testgen.priv.extensions.sv.page_tables import SV39, SV48, SV57, PteFlags, SvMode, create_page_mapping
from testgen.priv.registry import add_priv_test_generator

_PBMT = (("(1 << 61)", "PBMT=1", False), ("(2 << 61)", "PBMT=2", False), ("(3 << 61)", "PBMT=3", True))
_MARCH = ["I", "Zicsr", "Zifencei"]


def _begin_test(test_data: TestData, sv: SvMode, mode: str, topic: str) -> TestChunk:
    return begin_sv_test(
        test_data,
        sv,
        mode,
        f"{sv.name}_{topic}_{mode}",
        setup_asm=("LI(t0, MENVCFG_PBMTE)", "csrs menvcfg, t0"),
    )


def _finish_test(test_data: TestData, sv: SvMode) -> TestChunk:
    assert test_data.test_chunk is not None
    test_data.test_chunk.raw_data.extend(sv_data(sv))
    return test_data.end_test_chunk()


def _make_leaf_tests(test_data: TestData, sv: SvMode, mode: str) -> TestChunk:
    chunk = _begin_test(test_data, sv, mode, "Svpbmt")
    umode = mode == "Umode"
    number = 0
    for level in sv.levels_desc:
        for bits, description, guarded in _PBMT:
            number += 1
            permissions = PteFlags(user=umode, extra=(bits,))
            if guarded:
                chunk.code.append("#ifdef S1P12P0_OR_LATER_SUPPORTED")
            chunk.code.extend(
                [
                    f"// Test case {number}: {description} leaf PTE",
                    *create_page_mapping(sv, leaf_level=level, leaf_flags=permissions),
                    "sfence.vma",
                    "",
                    *add_rwx_test(test_data, sv, mode, "va_data", level, f"test{number}"),
                ]
            )
            if guarded:
                chunk.code.append("#endif")
            chunk.code.append("")
    return _finish_test(test_data, sv)


def _make_nonleaf_tests(test_data: TestData, sv: SvMode, mode: str) -> TestChunk:
    chunk = _begin_test(test_data, sv, mode, "Svpbmt_nonleaf")
    chunk.code.append("#ifdef S1P12P0_OR_LATER_SUPPORTED")
    umode = mode == "Umode"
    number = 0
    for level in (level for level in sv.levels_desc if level < sv.levels - 1):
        for bits, description, _guarded in _PBMT:
            number += 1
            permissions = PteFlags(user=umode)
            chunk.code.extend(
                [
                    f"// Test case {number}: {description} in the non-leaf PTE at level {level + 1}",
                    *create_page_mapping(
                        sv,
                        leaf_level=level,
                        leaf_flags=permissions,
                        walk_overrides={level + 1: f"{bits} | PTE_V"},
                    ),
                    "sfence.vma",
                    "",
                    *add_rwx_test(test_data, sv, mode, "va_data", level, f"test{number}"),
                    "",
                ]
            )
    chunk.code.append("#endif")
    return _finish_test(test_data, sv)


def _make_svpbmt(test_data: TestData, sv: SvMode) -> list[TestChunk]:
    tests = []
    for mode in ("Smode", "Umode"):
        tests.extend((_make_leaf_tests(test_data, sv, mode), _make_nonleaf_tests(test_data, sv, mode)))
    return tests


@add_priv_test_generator(
    "Svpbmt",
    required_extensions=["I", "Sv39", "Svpbmt"],
    march_extensions=_MARCH,
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpbmt_sv39(test_data: TestData) -> list[TestChunk]:
    return _make_svpbmt(test_data, SV39)


@add_priv_test_generator(
    "Svpbmt",
    required_extensions=["I", "Sv48", "Svpbmt"],
    march_extensions=_MARCH,
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpbmt_sv48(test_data: TestData) -> list[TestChunk]:
    return _make_svpbmt(test_data, SV48)


@add_priv_test_generator(
    "Svpbmt",
    required_extensions=["I", "Sv57", "Svpbmt"],
    march_extensions=_MARCH,
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpbmt_sv57(test_data: TestData) -> list[TestChunk]:
    return _make_svpbmt(test_data, SV57)
