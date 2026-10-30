##################################
# priv/extensions/sv/Svrsw60t59b.py
#
# Svrsw60t59b PTE bits 60:59 for software tests.
# David_Harris@hmc.edu October 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate Svrsw60t59b tests: accesses through PTEs with bits 60:59 set translate as if the bits were clear."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk, trap_sigupd_count
from testgen.priv.extensions.sv.access import Crosses, add_rwx_test, cross_names
from testgen.priv.extensions.sv.generate import SvRegs, begin_sv_test, end_sv_test, sv_data
from testgen.priv.extensions.sv.page_tables import SV39, SV48, SV57, PteFlags, SvMode, create_page_mapping
from testgen.priv.registry import add_priv_test_generator

# Values of PTE bits 60:59 under test: each bit alone, then both.
_RSW_BITS = (("bit 59", "(1 << 59)"), ("bit 60", "(1 << 60)"), ("bits 60:59", "(3 << 59)"))


def _make_svrsw60t59b_mode(test_data: TestData, sv: SvMode, mode: str) -> TestChunk:
    regs = SvRegs.allocate(test_data)
    crosses = Crosses(f"{test_data.testsuite}_cg", "cp_store", "cp_load", "cp_fetch")
    chunk = begin_sv_test(test_data, regs, sv, mode, f"{sv.name}_{mode}", coverpoint=cross_names(crosses))
    umode = mode == "Umode"

    # Each case is (description, page-table setup, level of the accessed page).
    cases = [
        (
            f"{sv.page_names[level]} page, leaf PTE at level {level} with {bits}",
            create_page_mapping(sv, leaf_level=level, leaf_flags=PteFlags(user=umode, extra=(value,))),
            level,
        )
        for level in sv.levels_desc
        for bits, value in _RSW_BITS
    ] + [
        (
            f"4KB page, non-leaf PTE at level {level} with {bits}",
            create_page_mapping(
                sv, leaf_level=0, leaf_flags=PteFlags(user=umode), walk_overrides={level: PteFlags.nonleaf(value)}
            ),
            0,
        )
        for level in range(sv.levels - 1, 0, -1)
        for bits, value in _RSW_BITS
    ]

    for number, (description, mapping, level) in enumerate(cases, 1):
        chunk.code.extend(
            [
                "",
                f"// Test case {number}: {description} | Test in {mode[0]}-Mode | expected = no fault",
                *mapping,
                "sfence.vma",
                "",
                *add_rwx_test(
                    test_data, sv, regs, mode, "va_data", level, f"test{number}", driver_mode="Smode", crosses=crosses
                ),
            ]
        )

    chunk.raw_data.extend(sv_data(sv, regs))
    chunk.trap_sigupd_count = trap_sigupd_count(len(cases) * 3)
    return end_sv_test(test_data, regs)


@add_priv_test_generator(
    "Svrsw60t59b",
    required_extensions=["Sv39", "Svrsw60t59b"],
    march_extensions=[],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svrsw60t59b_sv39(test_data: TestData) -> list[TestChunk]:
    return [_make_svrsw60t59b_mode(test_data, SV39, mode) for mode in ("Smode", "Umode")]


@add_priv_test_generator(
    "Svrsw60t59b",
    required_extensions=["Sv48", "Svrsw60t59b"],
    march_extensions=[],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svrsw60t59b_sv48(test_data: TestData) -> list[TestChunk]:
    return [_make_svrsw60t59b_mode(test_data, SV48, mode) for mode in ("Smode", "Umode")]


@add_priv_test_generator(
    "Svrsw60t59b",
    required_extensions=["Sv57", "Svrsw60t59b"],
    march_extensions=[],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svrsw60t59b_sv57(test_data: TestData) -> list[TestChunk]:
    return [_make_svrsw60t59b_mode(test_data, SV57, mode) for mode in ("Smode", "Umode")]
