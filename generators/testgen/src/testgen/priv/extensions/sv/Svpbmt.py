##################################
# priv/extensions/sv/Svpbmt.py
#
# Svpbmt page-based memory-type tests.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate Svpbmt leaf and non-leaf PTE tests, the Zicbom group's flushes through PBMT aliases, and the Zicboz
group's cbo.zero on PBMT pages."""

from testgen.asm.helpers import gated, write_sigupd
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.sv.access import Crosses, add_rwx_test, cross_names, mode_switch
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


def _envcfg_setup(regs: SvRegs, mode: str, enables: tuple[str, ...] = ()) -> tuple[str, ...]:
    """Set menvcfg.PBMTE and the menvcfg CBO ``enables`` (CBCFE, CBZE), and the senvcfg ones for U-mode."""
    setup = [
        f"LI(x{regs.scratch}, {' | '.join(['MENVCFG_PBMTE', *(f'MENVCFG_{e}' for e in enables)])})",
        tsbi_call(f"csrs menvcfg, x{regs.scratch}"),
    ]
    if enables and mode == "Umode":
        setup.extend(
            [f"LI(x{regs.scratch}, {' | '.join(f'SENVCFG_{e}' for e in enables)})", f"csrs senvcfg, x{regs.scratch}"]
        )
    return tuple(setup)


def _begin_test(test_data: TestData, regs: SvRegs, sv: SvMode, mode: str, topic: str, banner: str) -> TestChunk:
    return begin_sv_test(
        test_data,
        regs,
        sv,
        mode,
        f"{sv.name}_{topic}_{mode}",
        coverpoint=banner,
        setup_asm=_envcfg_setup(regs, mode),
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


def _make_nc_io_alias_tests(test_data: TestData, sv: SvMode, mode: str) -> TestChunk:
    """Store through a PBMT=NC mapping of a page and load through a PBMT=IO mapping of it, and the reverse, with
    no fence or cache-block operation between them.  Neither access is cacheable, so mixing them loses no
    coherence and the load must return the store.  Each access is the first through its mapping after
    sfence.vma, so it walks the page table and the coverage sees both PTEs.
    """
    regs = SvRegs.allocate(test_data)
    # The data-region routines are never called here, so regs.result is free to hold the second address.
    other = f"x{regs.result}"
    m = mode[0].lower()
    coverpoint = f"nc_io_alias_{m}"
    chunk = begin_sv_test(
        test_data,
        regs,
        sv,
        mode,
        f"{sv.name}_Svpbmt_alias_{mode}",
        coverpoint=coverpoint,
        va_defs=(("va_nc", f"{sv.data_va} + 0x1000"), ("va_io", f"{sv.data_va} + 0x2000")),
        setup_asm=_envcfg_setup(regs, mode),
    )
    umode = mode == "Umode"
    enter, leave = mode_switch(mode, "Smode")
    (nc_bits, _, _), (io_bits, _, _) = _ALIAS_PBMT
    chunk.code.extend(
        [
            "// Map the data page at va_nc with PBMT = NC and at va_io with PBMT = IO",
            *create_page_mapping(
                sv, leaf_level=0, leaf_flags=PteFlags(user=umode, extra=(nc_bits,)), virtual_address="va_nc"
            ),
            create_leaf_pte(sv, level=0, flags=PteFlags(user=umode, extra=(io_bits,)), virtual_address="va_io"),
            "",
        ]
    )
    value, addr, load = (f"x{reg}" for reg in (regs.value, regs.addr, regs.load))
    cases = (
        ("va_nc", "va_io", "PBMT=NC", "PBMT=IO", "nc_store_io_load"),
        ("va_io", "va_nc", "PBMT=IO", "PBMT=NC", "io_store_nc_load"),
    )
    for number, (store_va, load_va, store_name, load_name, name) in enumerate(cases, start=1):
        label = test_data.add_testcase(name, coverpoint, "Svpbmt_cg")
        chunk.code.extend(
            [
                f"// Test case {number}: store through the {store_name} mapping, load through the {load_name} mapping",
                "sfence.vma",
                f"LI({addr}, {store_va} + 0x800)",
                f"LI({other}, {load_va} + 0x800)",
                *enter,
                f"addi {value}, {value}, 16",
                f"sd {value}, 0({addr})",
                label,
                f"ld {load}, 0({other})",
                *leave,
                write_sigupd(regs.load, test_data, label=label.removesuffix(":")),
                "",
            ]
        )
    return _finish_test(test_data, sv, regs)


def _make_svpbmt(test_data: TestData, sv: SvMode) -> list[TestChunk]:
    tests = []
    for mode in ("Smode", "Umode"):
        tests.extend((_make_leaf_tests(test_data, sv, mode), _make_nonleaf_tests(test_data, sv, mode)))
    if sv == SV39:
        # Aliasing does not depend on the translation mode, so Sv39, which Svpbmt requires, suffices.
        tests.extend(_make_nc_io_alias_tests(test_data, sv, mode) for mode in ("Smode", "Umode"))
    return tests


def _make_zicbom_tests(test_data: TestData, sv: SvMode, mode: str) -> TestChunk:
    """Flush a block through a PBMT=NC or IO alias (va_alias) of a cacheable page (va_data).

    Svpbmt makes fence iorw, iorw; cbo.flush to an address of the location; fence iorw, iorw restore coherence
    between accesses with different cacheability, and cache-block management instructions ignore the PBMT
    downgrade.  Each flush through va_alias is its first access after sfence.vma, so it walks the page table and
    the coverage sees its PTE.

    Writeback: dirty the block through va_data and flush it through va_alias; the uncached load through
    va_alias must return the store.

    Invalidate: cache the block through va_data and flush it through va_alias, write memory through va_alias,
    and flush again; the cacheable load through va_data must return the new value, not the copy it cached.

    The data sits halfway into the page, clear of the data-region routines.
    """
    regs = SvRegs.allocate(test_data)
    # The data-region routines are never called here, so regs.result is free to hold the alias address.
    alias = f"x{regs.result}"
    m = mode[0].lower()
    coverpoint = f"cp_cbo_flush_pbmt_{m}"
    chunk = begin_sv_test(
        test_data,
        regs,
        sv,
        mode,
        f"Zicbom_{sv.name}_{mode}",
        coverpoint=coverpoint,
        va_defs=(("va_data", sv.data_va), ("va_alias", f"{sv.data_va} + 0x1000")),
        setup_asm=_envcfg_setup(regs, mode, ("CBCFE",)),
    )
    umode = mode == "Umode"
    enter, leave = mode_switch(mode, "Smode")
    value, addr, load = (f"x{reg}" for reg in (regs.value, regs.addr, regs.load))
    chunk.code.extend(
        [
            "// Map va_data cacheable (PBMT = 0)",
            *create_page_mapping(sv, leaf_level=0, leaf_flags=PteFlags(user=umode)),
            "",
        ]
    )
    writeback = [(*pbmt, "writeback") for pbmt in _ALIAS_PBMT]
    invalidate = [(*pbmt, "invalidate") for pbmt in _ALIAS_PBMT]
    for number, (bits, description, name, kind) in enumerate([*writeback, *invalidate], start=1):
        if kind == "writeback":
            label = test_data.add_testcase(name, coverpoint, "Svpbmt_Zicbom_cg")
            title = f"cbo.flush through a {description} alias of a dirty cacheable block"
            body = [
                f"addi {value}, {value}, 16",
                f"sd {value}, 0({addr})  // Dirty the block through the cacheable mapping",
                "fence iorw, iorw",
                label,
                f"cbo.flush ({alias})",
                "fence iorw, iorw",
                f"ld {load}, 0({alias})  // Read memory through the alias",
            ]
        else:
            label = test_data.add_testcase(f"{name}_invalidate", coverpoint, "Svpbmt_Zicbom_cg")
            title = f"cbo.flush through a {description} alias of a clean cached block"
            body = [
                f"ld {load}, 0({addr})  // Cache the block through the cacheable mapping",
                "fence iorw, iorw",
                label,
                f"cbo.flush ({alias})  // Must remove the cached copy",
                "fence iorw, iorw",
                f"addi {value}, {value}, 16",
                f"sd {value}, 0({alias})  // Write memory through the alias",
                "fence iorw, iorw",
                f"cbo.flush ({alias})",
                "fence iorw, iorw",
                f"ld {load}, 0({addr})  // Read through the cacheable mapping",
            ]
        chunk.code.extend(
            [
                f"// Test case {number}: {title}",
                create_leaf_pte(sv, level=0, flags=PteFlags(user=umode, extra=(bits,)), virtual_address="va_alias"),
                "sfence.vma",
                f"LI({addr}, va_data + 0x800)",
                f"LI({alias}, va_alias + 0x800)",
                *enter,
                *body,
                *leave,
                write_sigupd(regs.load, test_data, label=label.removesuffix(":")),
                "",
            ]
        )
    return _finish_test(test_data, sv, regs)


_ZERO_CHECKED_BYTES = 256  # bytes of the block read back; the gates keep the checks inside a smaller block


def _block_gate(offset: int) -> str | None:
    return f"UDB_CACHE_BLOCK_SIZE > {offset}" if offset else None


def _make_zicboz_tests(test_data: TestData, sv: SvMode, mode: str) -> TestChunk:
    """cbo.zero a block of a PBMT=NC or IO page, which writes memory without the cache.

    Fill the block and the doublewords on either side of it, read a neighbor so the last bus read returned
    nonzero data, then cbo.zero the block and load from it in the very next instruction.  The load and every
    doubleword of the block must read zero, and the neighbors must keep their values.  Then cbo.zero the block
    again and store to it in the very next instruction; the store must not be lost.  The page has one mapping,
    so the accesses are never aliased.  The block sits a quarter of the way into the page, clear of the
    data-region routines, and the page holds a block of up to 2 KiB.
    """
    regs = SvRegs.allocate(test_data)
    m = mode[0].lower()
    coverpoint = f"cp_cbo_zero_pbmt_{m}"
    chunk = begin_sv_test(
        test_data,
        regs,
        sv,
        mode,
        f"Zicboz_{sv.name}_{mode}",
        coverpoint=coverpoint,
        setup_asm=_envcfg_setup(regs, mode, ("CBZE",)),
    )
    umode = mode == "Umode"
    enter, leave = mode_switch(mode, "Smode")
    value, addr, load, result, scratch = (
        f"x{reg}" for reg in (regs.value, regs.addr, regs.load, regs.result, regs.scratch)
    )
    neighbors = ("-8", "UDB_CACHE_BLOCK_SIZE")
    block = range(0, _ZERO_CHECKED_BYTES, 8)
    for number, (bits, description, name) in enumerate(_ALIAS_PBMT, start=1):
        zero = test_data.add_testcase(f"{name}_load", coverpoint, "Svpbmt_Zicboz_cg")
        store = test_data.add_testcase(f"{name}_store", coverpoint, "Svpbmt_Zicboz_cg")
        fill = [f"sd {value}, {offset}({addr})" for offset in neighbors]
        for offset in block:
            fill.extend(gated([f"sd {value}, {offset}({addr})"], _block_gate(offset)))
        check = [f"mv {result}, {load}"]
        for offset in block[1:]:
            check.extend(
                gated([f"ld {scratch}, {offset}({addr})", f"or {result}, {result}, {scratch}"], _block_gate(offset))
            )
        for offset in neighbors:
            check.extend(
                [
                    f"ld {scratch}, {offset}({addr})",
                    f"xor {scratch}, {scratch}, {value}",
                    f"or {result}, {result}, {scratch}",
                ]
            )
        chunk.code.extend(
            [
                f"// Test case {number}: cbo.zero on a {description} page, then a load and a store right after it",
                *create_page_mapping(sv, leaf_level=0, leaf_flags=PteFlags(user=umode, extra=(bits,))),
                "sfence.vma",
                f"LI({addr}, va_data + 0x400)",
                *enter,
                f"addi {value}, {value}, 16",
                "// Fill the block and its neighbors, then read a neighbor over the bus",
                *fill,
                f"ld {load}, -8({addr})",
                zero,
                f"cbo.zero ({addr})",
                f"ld {load}, 0({addr})  // Load right after cbo.zero",
                "// result = OR of the block | each neighbor XOR its value: 0 when only the block was zeroed",
                *check,
                f"addi {value}, {value}, 16",
                store,
                f"cbo.zero ({addr})",
                f"sd {value}, 8({addr})  // Store right after cbo.zero",
                f"ld {load}, 8({addr})",
                *leave,
                write_sigupd(regs.result, test_data, label=zero.removesuffix(":")),
                write_sigupd(regs.load, test_data, label=store.removesuffix(":")),
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
    required_extensions=["Sv39", "Svpbmt", "Zicboz"],
    march_extensions=["Svpbmt", "Zicboz"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svpbmt_zicboz(test_data: TestData) -> list[TestChunk]:
    """Generate Svpbmt_Zicboz tests: cbo.zero on PBMT=NC and IO pages from S-mode and U-mode."""
    return [_make_zicboz_tests(test_data, SV39, mode) for mode in ("Smode", "Umode")]


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
