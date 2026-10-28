##################################
# priv/extensions/sv/Svpbmt.py
#
# Svpbmt page-based memory-type tests.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate Svpbmt leaf and non-leaf PTE tests and the Zicbom group's cache-block flushes through PBMT aliases."""

from testgen.asm.helpers import write_sigupd
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.sv.access import Crosses, add_rwx_test, cross_names
from testgen.priv.extensions.sv.generate import SvRegs, begin_sv_test, end_sv_test, sv_data
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

_PBMT = (("(1 << 61)", "PBMT=1", False), ("(2 << 61)", "PBMT=2", False), ("(3 << 61)", "PBMT=3", True))
_ALIAS_PBMT = (("(1 << 61)", "PBMT=NC", "nc"), ("(2 << 61)", "PBMT=IO", "io"))


def _crosses(prefix: str, mode: str) -> Crosses:
    m = mode[0].lower()
    return Crosses("Svpbmt_cg", f"{prefix}_write_{m}", f"{prefix}_read_{m}", f"{prefix}_exec_{m}")


def _begin_test(test_data: TestData, regs: SvRegs, sv: SvMode, mode: str, topic: str, banner: str) -> TestChunk:
    return begin_sv_test(
        test_data,
        regs,
        sv,
        mode,
        f"{sv.name}_{topic}_{mode}",
        coverpoint=banner,
        setup_asm=(f"LI(x{regs.scratch}, MENVCFG_PBMTE)", tsbi_call(f"csrs menvcfg, x{regs.scratch}")),
    )


def _finish_test(test_data: TestData, sv: SvMode, regs: SvRegs) -> TestChunk:
    assert test_data.test_chunk is not None
    test_data.test_chunk.raw_data.extend(sv_data(sv, regs))
    return end_sv_test(test_data, regs)


def _make_leaf_tests(test_data: TestData, sv: SvMode, mode: str) -> TestChunk:
    regs = SvRegs.allocate(test_data)
    legal, reserved = _crosses("leaf_PTE_pbmt", mode), _crosses("leaf_PTE_pbmt_reserved_enc", mode)
    chunk = _begin_test(test_data, regs, sv, mode, "Svpbmt", cross_names(legal, reserved))
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
                    *add_rwx_test(
                        test_data,
                        sv,
                        regs,
                        mode,
                        "va_data",
                        level,
                        f"test{number}",
                        driver_mode="Smode",
                        # The guarded encoding, PBMT = 3, is reserved.
                        crosses=reserved if guarded else legal,
                    ),
                ]
            )
            if guarded:
                chunk.code.append("#endif")
            chunk.code.append("")
    return _finish_test(test_data, sv, regs)


def _make_nonleaf_tests(test_data: TestData, sv: SvMode, mode: str) -> TestChunk:
    regs = SvRegs.allocate(test_data)
    crosses = _crosses("nonleaf_PTE_pbmt", mode)
    chunk = _begin_test(test_data, regs, sv, mode, "Svpbmt_nonleaf", cross_names(crosses))
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
                    *add_rwx_test(
                        test_data,
                        sv,
                        regs,
                        mode,
                        "va_data",
                        level,
                        f"test{number}",
                        driver_mode="Smode",
                        crosses=crosses,
                    ),
                    "",
                ]
            )
    chunk.code.append("#endif")
    return _finish_test(test_data, sv, regs)


def _make_svpbmt(test_data: TestData, sv: SvMode) -> list[TestChunk]:
    tests = []
    for mode in ("Smode", "Umode"):
        tests.extend((_make_leaf_tests(test_data, sv, mode), _make_nonleaf_tests(test_data, sv, mode)))
    return tests


def _make_zicbom_tests(test_data: TestData, sv: SvMode, mode: str) -> TestChunk:
    """Dirty a cache block through a cacheable mapping, cbo.flush it through a PBMT=NC or IO alias of the same
    page, and read memory back through the alias.

    Svpbmt makes fence iorw, iorw; cbo.flush to an address of the location; fence iorw, iorw restore coherence
    between accesses with different cacheability, and cache-block management instructions ignore the PBMT
    downgrade, so the uncached load must return the store.  The data sits halfway into the page, clear of the
    data-region routines.
    """
    regs = SvRegs.allocate(test_data)
    # The data-region routines are never called here, so regs.result is free to hold the alias address.
    alias = regs.result
    m = mode[0].lower()
    setup = [f"LI(x{regs.scratch}, MENVCFG_PBMTE | MENVCFG_CBCFE)", tsbi_call(f"csrs menvcfg, x{regs.scratch}")]
    if mode == "Umode":
        setup.extend([f"LI(x{regs.scratch}, SENVCFG_CBCFE)", f"csrs senvcfg, x{regs.scratch}"])
    chunk = begin_sv_test(
        test_data,
        regs,
        sv,
        mode,
        f"Zicbom_{sv.name}_{mode}",
        coverpoint=f"cp_cbo_flush_pbmt_{m}",
        va_defs=(("va_data", sv.data_va), ("va_alias", f"{sv.data_va} + 0x1000")),
        setup_asm=tuple(setup),
    )
    umode = mode == "Umode"
    value, addr, load = (f"x{reg}" for reg in (regs.value, regs.addr, regs.load))
    chunk.code.extend(
        [
            "// Map va_data cacheable (PBMT = 0)",
            *create_page_mapping(sv, leaf_level=0, leaf_flags=PteFlags(user=umode)),
            "",
        ]
    )
    for number, (bits, description, name) in enumerate(_ALIAS_PBMT, start=1):
        label = test_data.add_testcase(name, f"cp_cbo_flush_pbmt_{m}", "Svpbmt_Zicbom_cg")
        chunk.code.extend(
            [
                f"// Test case {number}: cbo.flush through a {description} alias of a dirty cacheable block",
                create_leaf_pte(sv, level=0, flags=PteFlags(user=umode, extra=(bits,)), virtual_address="va_alias"),
                "sfence.vma",
                f"LI({addr}, va_data + 0x800)",
                f"LI(x{alias}, va_alias + 0x800)",
                *([] if mode == "Smode" else ["RVTEST_TSBI_GOTO_UMODE"]),
                f"addi {value}, {value}, 16",
                f"sd {value}, 0({addr})  // Dirty the block through the cacheable mapping",
                "fence iorw, iorw",
                label,
                f"cbo.flush (x{alias})",
                "fence iorw, iorw",
                f"ld {load}, 0(x{alias})  // Read memory through the alias",
                *([] if mode == "Smode" else ["RVTEST_TSBI_GOTO_SMODE"]),
                write_sigupd(regs.load, test_data, label=label.removesuffix(":")),
                "",
            ]
        )
    return _finish_test(test_data, sv, regs)


@add_priv_test_generator(
    "Svpbmt",
    required_extensions=["Sv39", "Svpbmt", "Zicbom"],
    march_extensions=["Svpbmt", "Zicbom"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svpbmt_zicbom(test_data: TestData) -> list[TestChunk]:
    """Generate Svpbmt_Zicbom tests: cbo.flush through PBMT=NC and IO aliases from S-mode and U-mode."""
    return [_make_zicbom_tests(test_data, SV39, mode) for mode in ("Smode", "Umode")]


@add_priv_test_generator(
    "Svpbmt",
    required_extensions=["Sv39", "Svpbmt"],
    march_extensions=["Svpbmt"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svpbmt_sv39(test_data: TestData) -> list[TestChunk]:
    return _make_svpbmt(test_data, SV39)


@add_priv_test_generator(
    "Svpbmt",
    required_extensions=["Sv48", "Svpbmt"],
    march_extensions=["Svpbmt"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svpbmt_sv48(test_data: TestData) -> list[TestChunk]:
    return _make_svpbmt(test_data, SV48)


@add_priv_test_generator(
    "Svpbmt",
    required_extensions=["Sv57", "Svpbmt"],
    march_extensions=["Svpbmt"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svpbmt_sv57(test_data: TestData) -> list[TestChunk]:
    return _make_svpbmt(test_data, SV57)
