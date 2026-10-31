##################################
# priv/extensions/sv/Svrsw60t59b.py
#
# Svrsw60t59b PTE bits 60:59 for software tests.
# David_Harris@hmc.edu October 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate Svrsw60t59b tests: accesses through PTEs with bits 60:59 set translate as if the bits were clear.

The S-mode and U-mode tests use satp.  The H group sets the bits in VS-stage PTEs (hgatp = Bare) and in G-stage
PTEs (vsatp = Bare), with guest accesses in VS-mode and VU-mode.
"""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk, trap_sigupd_count
from testgen.priv.extensions.sv.access import Crosses, add_rwx_test, cross_names
from testgen.priv.extensions.sv.generate import SvRegs, begin_sv_test, end_sv_test, sv_data
from testgen.priv.extensions.sv.page_tables import (
    SV39,
    SV39X4,
    SV48,
    SV48X4,
    SV57,
    SV57X4,
    VS_SV39,
    VS_SV48,
    VS_SV57,
    PteFlags,
    SvMode,
    create_page_mapping,
)
from testgen.priv.extensions.sv.SvH import (
    BOOT,
    GUEST_OPS,
    SV39_PARAMS,
    begin_chunk,
    guest_access,
    guest_chunk_setup,
    guest_chunk_teardown,
)
from testgen.priv.registry import add_priv_test_generator

# Values of PTE bits 60:59 under test: each bit alone, then both.
_RSW_BITS = (("bit 59", "(1 << 59)"), ("bit 60", "(1 << 60)"), ("bits 60:59", "(3 << 59)"))

H_CG = "Svrsw60t59b_H_cg"


def _rsw_cases(
    sv: SvMode,
    user: bool,
    virtual_address: str = "va_data",
    physical_address: str = "rvtest_data_1",
    regs: tuple[int, int, int] | None = None,
) -> list[tuple[str, list[str], int]]:
    """(description, page-table setup, level of the accessed page) for each PTE under test in ``sv``'s tables.

    The PTEs under test are the leaf PTE at every level and each non-leaf PTE above a 4 KiB leaf, each with bit 59,
    bit 60 or both set.
    """

    def mapping(leaf_level: int, leaf_flags: PteFlags, walk_overrides: dict[int, PteFlags] | None = None) -> list[str]:
        return create_page_mapping(
            sv,
            leaf_level=leaf_level,
            leaf_flags=leaf_flags,
            virtual_address=virtual_address,
            physical_address=physical_address,
            walk_overrides=walk_overrides,
            regs=regs,
        )

    return [
        (
            f"{sv.page_names[level]} page, leaf PTE at level {level} with {bits}",
            mapping(level, PteFlags(user=user, extra=(value,))),
            level,
        )
        for level in sv.levels_desc
        for bits, value in _RSW_BITS
    ] + [
        (
            f"4KB page, non-leaf PTE at level {level} with {bits}",
            mapping(0, PteFlags(user=user), {level: PteFlags.nonleaf(value)}),
            0,
        )
        for level in range(sv.levels - 1, 0, -1)
        for bits, value in _RSW_BITS
    ]


def _make_svrsw60t59b_mode(test_data: TestData, sv: SvMode, mode: str) -> TestChunk:
    regs = SvRegs.allocate(test_data)
    crosses = Crosses(f"{test_data.testsuite}_cg", "cp_store", "cp_load", "cp_fetch")
    chunk = begin_sv_test(test_data, regs, sv, mode, f"{sv.name}_{mode}", coverpoint=cross_names(crosses))
    cases = _rsw_cases(sv, mode == "Umode")

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


def _h_chunk(test_data: TestData, sv: SvMode, mode: str) -> TestChunk:
    """Guest accesses in ``mode`` through PTEs of ``sv`` (a VS-stage or G-stage mode) with bits 60:59 set.

    The other stage is Bare.  G-stage accesses are user-level, and a VS-stage leaf needs U = 1 for VU-mode.
    """
    g_stage = sv.stage == "g"
    coverpoint = "cp_hgatp" if g_stage else "cp_vsatp"
    chunk = begin_chunk(
        test_data,
        f"H_{sv.name}_{mode.lower()}",
        f"{coverpoint}_{{load, store, fetch}}",
        f"In {mode}-mode with {'vsatp' if g_stage else 'hgatp'} = Bare, store, load and fetch through "
        f"{'G' if g_stage else 'VS'}-stage leaf PTEs at every\n"
        "level and non-leaf PTEs above a 4 KiB leaf with bit 59, bit 60 or both set (no fault)",
        stages=(sv,),
    )
    code = guest_chunk_setup(test_data, sv if g_stage else None, None if g_stage else sv, mode)
    pte, addr, tmp = test_data.int_regs.get_registers(3)
    cases = _rsw_cases(sv, g_stage or mode == "VU", sv.data_va, "svh_page", (pte, addr, tmp))
    test_data.int_regs.return_registers([pte, addr, tmp])
    # The trace reports a PTE only for an access that walks the page table, so each access follows a fence
    for number, (description, mapping, level) in enumerate(cases, 1):
        for op, setup in zip(GUEST_OPS, ([f"// Test case {number}: {description}", *mapping], [], []), strict=True):
            code.extend(
                guest_access(
                    test_data,
                    H_CG,
                    coverpoint,
                    f"test{number}",
                    mode,
                    sv.data_va,
                    setup=[*setup, "hfence.vvma", "hfence.gvma"],
                    ops=(op,),
                    sv=sv,
                    level=level,
                )
            )
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, sv.xlen)])
    return test_data.end_test_chunk()


def _h_chunks(test_data: TestData, *modes: SvMode) -> list[TestChunk]:
    return [_h_chunk(test_data, sv, mode) for sv in modes for mode in ("VS", "VU")]


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


# Sv39 and Sv39x4 share an H test.  The larger VS-stage and G-stage modes each get their own, so a configuration that
# supports only some of them still runs those.
@add_priv_test_generator(
    "Svrsw60t59b",
    required_extensions=["H", "Svrsw60t59b"],
    march_extensions=["H"],
    extra_defines=BOOT,
    params=SV39_PARAMS,
)
def make_svrsw60t59b_h_sv39(test_data: TestData) -> list[TestChunk]:
    return _h_chunks(test_data, VS_SV39, SV39X4)


@add_priv_test_generator(
    "Svrsw60t59b",
    required_extensions=["H", "Svrsw60t59b"],
    march_extensions=["H"],
    extra_defines=BOOT,
    params=["SV48_VSMODE_TRANSLATION: true"],
)
def make_svrsw60t59b_h_vs_sv48(test_data: TestData) -> list[TestChunk]:
    return _h_chunks(test_data, VS_SV48)


@add_priv_test_generator(
    "Svrsw60t59b",
    required_extensions=["H", "Svrsw60t59b"],
    march_extensions=["H"],
    extra_defines=BOOT,
    params=["SV48X4_TRANSLATION: true"],
)
def make_svrsw60t59b_h_g_sv48x4(test_data: TestData) -> list[TestChunk]:
    return _h_chunks(test_data, SV48X4)


@add_priv_test_generator(
    "Svrsw60t59b",
    required_extensions=["H", "Svrsw60t59b"],
    march_extensions=["H"],
    extra_defines=BOOT,
    params=["SV57_VSMODE_TRANSLATION: true"],
)
def make_svrsw60t59b_h_vs_sv57(test_data: TestData) -> list[TestChunk]:
    return _h_chunks(test_data, VS_SV57)


@add_priv_test_generator(
    "Svrsw60t59b",
    required_extensions=["H", "Svrsw60t59b"],
    march_extensions=["H"],
    extra_defines=BOOT,
    params=["SV57X4_TRANSLATION: true"],
)
def make_svrsw60t59b_h_g_sv57x4(test_data: TestData) -> list[TestChunk]:
    return _h_chunks(test_data, SV57X4)
