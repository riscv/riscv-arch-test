##################################
# priv/extensions/sv/Svpbmt.py
#
# Svpbmt page-based memory-type tests.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate Svpbmt leaf and non-leaf PTE tests and the Zicbom and Zicboz groups' cache-block operations through PBMT
aliases."""

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


def _begin_alias_test(
    test_data: TestData,
    regs: SvRegs,
    sv: SvMode,
    mode: str,
    group: str,
    envcfg: str,
    coverpoint: str,
    aliases: tuple[str, ...],
) -> TestChunk:
    """Start a Svpbmt_<group> chunk: set menvcfg.PBMTE and the CBO enables in ``envcfg`` (MENVCFG_/SENVCFG_
    suffixes), declare ``aliases`` on the pages above va_data, and map va_data cacheable (PBMT = 0)."""
    enables = envcfg.split()
    setup = [
        f"LI(x{regs.scratch}, MENVCFG_PBMTE | {' | '.join(f'MENVCFG_{e}' for e in enables)})",
        tsbi_call(f"csrs menvcfg, x{regs.scratch}"),
    ]
    if mode == "Umode":
        setup.extend(
            [f"LI(x{regs.scratch}, {' | '.join(f'SENVCFG_{e}' for e in enables)})", f"csrs senvcfg, x{regs.scratch}"]
        )
    chunk = begin_sv_test(
        test_data,
        regs,
        sv,
        mode,
        f"{group}_{sv.name}_{mode}",
        coverpoint=coverpoint,
        va_defs=(
            ("va_data", sv.data_va),
            *((alias, f"{sv.data_va} + {0x1000 * page:#x}") for page, alias in enumerate(aliases, start=1)),
        ),
        setup_asm=tuple(setup),
    )
    chunk.code.extend(
        [
            "// Map va_data cacheable (PBMT = 0)",
            *create_page_mapping(sv, leaf_level=0, leaf_flags=PteFlags(user=mode == "Umode")),
            "",
        ]
    )
    return chunk


def _make_alias_tests(test_data: TestData, sv: SvMode, mode: str, family: str) -> TestChunk:
    """Run cache-block operations through a PBMT=NC or IO alias (va_alias) of a cacheable page (va_data).

    Svpbmt makes fence iorw, iorw; cbo.flush to an address of the location; fence iorw, iorw restore coherence
    between accesses with different cacheability, and cache-block management instructions ignore the PBMT
    downgrade.

    zicbom: dirty the block through va_data and flush it through va_alias; the uncached load through va_alias
    must return the store, so the flush wrote the block back.

    zicboz: dirty the block through va_data and flush it through va_alias, cbo.zero it through va_zero, a second
    alias with the same PBMT, which writes memory without the cache, and flush it through va_alias again; the
    cacheable load through va_data must return zero, so the flushes left no stale copy of the block in the cache.
    The cbo.zero is the first access through va_zero, so it walks the page table and the coverage sees its PTE.

    The data sits halfway into the page, clear of the data-region routines.
    """
    regs = SvRegs.allocate(test_data)
    # The data-region routines are never called here, so regs.result is free to hold the alias address.
    alias = f"x{regs.result}"
    m = mode[0].lower()
    group = family.capitalize()
    coverpoint = f"cp_cbo_{'flush' if family == 'zicbom' else 'zero'}_pbmt_{m}"
    envcfg = "CBCFE" if family == "zicbom" else "CBCFE CBZE"
    aliases = ("va_alias",) if family == "zicbom" else ("va_alias", "va_zero")
    chunk = _begin_alias_test(test_data, regs, sv, mode, group, envcfg, coverpoint, aliases)
    umode = mode == "Umode"
    value, addr, load = (f"x{reg}" for reg in (regs.value, regs.addr, regs.load))
    for number, (bits, description, name) in enumerate(_ALIAS_PBMT, start=1):
        label = test_data.add_testcase(name, coverpoint, f"Svpbmt_{group}_cg")
        if family == "zicbom":
            title = f"cbo.flush through a {description} alias of a dirty cacheable block"
            body = [
                "fence iorw, iorw",
                label,
                f"cbo.flush ({alias})",
                "fence iorw, iorw",
                f"ld {load}, 0({alias})  // Read memory through the alias",
            ]
        else:
            title = f"cbo.zero through a {description} alias of a cached block"
            body = [
                "fence iorw, iorw",
                f"cbo.flush ({alias})",
                "fence iorw, iorw",
                f"LI({load}, va_zero + 0x800)",
                label,
                f"cbo.zero ({load})  // Zero memory without the cache",
                "fence iorw, iorw",
                f"cbo.flush ({alias})  // Must remove any copy of the block from the cache",
                "fence iorw, iorw",
                f"ld {load}, 0({addr})  // Read through the cacheable mapping",
            ]
        chunk.code.extend(
            [
                f"// Test case {number}: {title}",
                *(
                    create_leaf_pte(sv, level=0, flags=PteFlags(user=umode, extra=(bits,)), virtual_address=va)
                    for va in aliases
                ),
                "sfence.vma",
                f"LI({addr}, va_data + 0x800)",
                f"LI({alias}, va_alias + 0x800)",
                *([] if mode == "Smode" else ["RVTEST_TSBI_GOTO_UMODE"]),
                f"addi {value}, {value}, 16",
                f"sd {value}, 0({addr})  // Dirty the block through the cacheable mapping",
                *body,
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
    return [_make_alias_tests(test_data, SV39, mode, "zicbom") for mode in ("Smode", "Umode")]


@add_priv_test_generator(
    "Svpbmt",
    required_extensions=["Sv39", "Svpbmt", "Zicbom", "Zicboz"],
    march_extensions=["Svpbmt", "Zicbom", "Zicboz"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svpbmt_zicboz(test_data: TestData) -> list[TestChunk]:
    """Generate Svpbmt_Zicboz tests: cbo.zero through PBMT=NC and IO aliases from S-mode and U-mode."""
    return [_make_alias_tests(test_data, SV39, mode, "zicboz") for mode in ("Smode", "Umode")]


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
