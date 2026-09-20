##################################
# priv/extensions/sv/Svade.py
#
# Svade A/D-bit page-fault tests.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate Svade A/D-bit page-fault tests."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk, trap_sigupd_count
from testgen.priv.extensions.sv.access import add_rwx_test
from testgen.priv.extensions.sv.generate import begin_sv_test, sv_data
from testgen.priv.extensions.sv.page_tables import SV32, SV39, SV48, SV57, PteFlags, SvMode, create_page_mapping
from testgen.priv.registry import add_priv_test_generator

_DA_CASES = (
    ("PTE.D unset and PTE.A set", ("PTE_A",), 1),
    ("Both PTE.D and PTE.A set", ("PTE_D", "PTE_A"), 0),
    ("PTE.D set and PTE.A unset", ("PTE_D",), 3),
    ("Both PTE.D and PTE.A unset", (), 3),
)
_MARCH = ["I", "Zicsr", "Zifencei"]


def _make_svade_mode(test_data: TestData, sv: SvMode, mode: str) -> TestChunk:
    csr, mask = ("menvcfg", "MENVCFG_ADUE") if sv.xlen == 64 else ("menvcfgh", "MENVCFGH_ADUE")
    chunk = begin_sv_test(
        test_data,
        sv,
        mode,
        f"{sv.name}_Svade_{mode}",
        coverpoint="cp_ad_update",
        setup_asm=(f"LI(t0, {mask})", f"csrc {csr}, t0 // Enable Svade"),
    )

    umode = mode == "Umode"
    number = 0
    faults = 0
    for level in range(sv.levels - 1, -1, -1):
        chunk.code.extend(["", f"// {sv.page_names[level]} page at level {level}", ""])
        for description, ad_bits, case_faults in _DA_CASES:
            number += 1
            faults += case_faults
            permissions = PteFlags(
                user=umode,
                accessed="PTE_A" in ad_bits,
                dirty="PTE_D" in ad_bits,
            )
            chunk.code.extend(
                [
                    f"// Test case {number}: {description}",
                    *create_page_mapping(sv, leaf_level=level, leaf_flags=permissions),
                    "sfence.vma",
                    "",
                    *add_rwx_test(test_data, sv, mode, "va_data", level, f"test{number}"),
                    "",
                ]
            )

    chunk.raw_data.extend(sv_data(sv))
    chunk.trap_sigupd_count = trap_sigupd_count(faults)
    return test_data.end_test_chunk()


def _make_svade(test_data: TestData, sv: SvMode) -> list[TestChunk]:
    return [_make_svade_mode(test_data, sv, mode) for mode in ("Smode", "Umode")]


@add_priv_test_generator(
    "Svade",
    required_extensions=["I", "Sv32", "Svade"],
    march_extensions=_MARCH,
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svade_sv32(test_data: TestData) -> list[TestChunk]:
    return _make_svade(test_data, SV32)


@add_priv_test_generator(
    "Svade",
    required_extensions=["I", "Sv39", "Svade"],
    march_extensions=_MARCH,
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svade_sv39(test_data: TestData) -> list[TestChunk]:
    return _make_svade(test_data, SV39)


@add_priv_test_generator(
    "Svade",
    required_extensions=["I", "Sv48", "Svade"],
    march_extensions=_MARCH,
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svade_sv48(test_data: TestData) -> list[TestChunk]:
    return _make_svade(test_data, SV48)


@add_priv_test_generator(
    "Svade",
    required_extensions=["I", "Sv57", "Svade"],
    march_extensions=_MARCH,
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svade_sv57(test_data: TestData) -> list[TestChunk]:
    return _make_svade(test_data, SV57)
