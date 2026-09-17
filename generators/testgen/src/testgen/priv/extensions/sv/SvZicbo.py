##################################
# priv/extensions/sv/SvZicbo.py
#
# SvZicbo suite: cache-block operations under virtual memory.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate cache-block operation tests under virtual memory."""

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
    PteExpression,
    PteFlags,
    SvMode,
    create_leaf_pte,
    create_page_mapping,
    create_page_walk,
)
from testgen.priv.registry import add_priv_test_generator

_MARCH = ["I", "Zicsr", "Zifencei"]


def _add_operation(test_data: TestData, family: str, mode: str, address: list[str], number: int) -> list[str]:
    lines = [*address, f"RVTEST_GOTO_LOWER_MODE {mode}"]
    if family == "zicbop":
        for operation in ("prefetch.i", "prefetch.r", "prefetch.w"):
            lines.extend(
                [
                    test_data.add_testcase(f"test{number}_{operation.replace('.', '_')}", "cp_prefetch", "SvZicbo_cg"),
                    f"{operation} 0(a5)",
                    "nop",
                ]
            )
    elif family == "zicbom":
        labels = {
            operation: test_data.add_testcase(f"test{number}_{operation}", "cp_zicbom", "SvZicbo_cg").removesuffix(":")
            for operation in ("clean", "flush", "inval")
        }
        lines.extend(["addi a2, a2, 16"])
        for operation, register in (("clean", "a2"), ("flush", "a3"), ("inval", "a4")):
            lines.extend([f"{labels[operation]}:", f"cbo.{operation} (a5)", f"addi {register}, a2, 4"])
        lines.extend(
            [
                "RVTEST_GOTO_MMODE",
                *(
                    write_sigupd(reg, test_data, label=labels[op])
                    for op, reg in (("clean", 12), ("flush", 13), ("inval", 14))
                ),
            ]
        )
        return lines
    else:
        label = test_data.add_testcase(f"test{number}_zero", "cp_zicboz", "SvZicbo_cg").removesuffix(":")
        lines.extend(
            [
                "addi a2, a2, 16",
                f"{label}:",
                "cbo.zero (a5)",
                "addi a4, a2, 4",
                "RVTEST_GOTO_MMODE",
                write_sigupd(14, test_data, label=label),
            ]
        )
        return lines
    lines.append("RVTEST_GOTO_MMODE")
    return lines


def _add_exception_cases(test_data: TestData, chunk: TestChunk, sv: SvMode, mode: str, family: str) -> None:
    """Add the cache-block exception cases for each page-table level."""
    number = 0

    def leaf(
        permissions: PteExpression,
        level: int,
        *,
        physical_address: str = "rvtest_data_1",
        superpage: bool | None = None,
    ) -> str:
        return create_leaf_pte(
            sv,
            physical_address=physical_address,
            level=level,
            flags=permissions,
            superpage=superpage,
        )

    def add(
        level: int,
        description: str,
        expected: str,
        pte_lines: list[str],
        *,
        physical_address: str | None = None,
        before: tuple[str, ...] = (),
        after: tuple[str, ...] = (),
        ifdef: str | None = None,
    ) -> None:
        nonlocal number
        number += 1
        address = (
            virtual_address(
                sv,
                "va_data",
                level,
                physical_address=physical_address,
                physical_address_is_label=False,
            )
            if physical_address is not None
            else virtual_address(sv, "va_data", level)
        )
        lines = [
            f"  // Test case {number}: {description} | Test in {mode[0]}-Mode | expected = {expected}",
            *pte_lines,
            "  sfence.vma",
            *before,
            "",
            *_add_operation(test_data, family, mode, address, number),
            *after,
        ]
        if ifdef:
            lines = [f"#ifdef {ifdef}", *lines, "#endif"]
        chunk.code.extend([*lines, ""])

    def add_standard(
        level: int,
        permissions: PteExpression,
        description: str,
        expected: str,
        *,
        before: tuple[str, ...] = (),
        after: tuple[str, ...] = (),
        ifdef: str | None = None,
    ) -> None:
        add(
            level,
            description,
            expected,
            [*create_page_walk(sv, leaf_level=level), leaf(permissions, level)],
            before=before,
            after=after,
            ifdef=ifdef,
        )

    for level in sv.levels_desc:
        umode = mode == "Umode"
        top = level == sv.levels - 1
        leaf_permissions = PteFlags(user=umode)
        walk_fault_permissions = f"PTE_A | PTE_D | {'PTE_U | ' if umode else ''}PTE_X | PTE_W | PTE_R | PTE_V"

        add_standard(level, PteFlags(user=umode, valid=False), "PTE.V unset", "Store page fault")
        add_standard(
            level,
            PteFlags(user=umode, read=False),
            "Reserved W+X without R",
            "Store page fault",
            ifdef="S1P12P0_OR_LATER_SUPPORTED",
        )
        add_standard(
            level,
            PteFlags(user=umode, read=False, execute=False),
            "Reserved W without R",
            "Store page fault",
            ifdef="S1P12P0_OR_LATER_SUPPORTED",
        )
        add_standard(level, PteFlags(user=umode, write=False), "RX permissions", "Store page fault")
        if umode:
            add_standard(level, PteFlags(), "Supervisor page from U-Mode", "Store page fault")
        else:
            add_standard(
                level,
                PteFlags(write=False),
                "RX permissions with mstatus.SUM set",
                "Store page fault",
                before=("  LI(t0, MSTATUS_SUM)", "  csrs mstatus, t0"),
                after=("  LI(t0, MSTATUS_SUM)", "  csrc mstatus, t0"),
            )
            add_standard(level, PteFlags(user=True), "User page from S-Mode", "Store page fault")
        if family == "zicbom":
            add_standard(
                level,
                PteFlags(user=umode, read=False, write=False),
                "Execute-only page",
                "Store page fault",
            )
        add_standard(level, PteFlags(user=umode, accessed=False), "PTE.A unset", "Store page fault")
        add_standard(level, PteFlags(user=umode, dirty=False), "PTE.D unset", "No fault")

        walk = create_page_walk(sv, leaf_level=level)
        if level > 0:
            add(
                level,
                "Misaligned superpage",
                "Store page fault",
                [*walk, leaf(leaf_permissions, level, superpage=False)],
                physical_address="0x0",
            )
        else:
            add(
                level,
                "Pointer encoding (V only) in the leaf",
                "Store page fault",
                [*walk, leaf(PteFlags.nonleaf("PTE_U") if umode else PteFlags.nonleaf(), level)],
            )

        if not top and level > 0:
            add(
                level,
                "Access fault on the page-table walk",
                "Store access fault",
                [
                    *create_page_walk(
                        sv,
                        leaf_level=level,
                        table_addresses={level + 1: "RVMODEL_ACCESS_FAULT_ADDRESS"},
                    ),
                    leaf(walk_fault_permissions, level),
                ],
                ifdef="RVMODEL_ACCESS_FAULT_ADDRESS",
            )
        if level == 0:
            add(
                level,
                "Access fault on the page-table walk",
                "Store access fault",
                [
                    *create_page_walk(
                        sv,
                        leaf_level=level,
                        table_addresses={1: "RVMODEL_ACCESS_FAULT_ADDRESS"},
                    ),
                    leaf(leaf_permissions, level),
                ],
                physical_address="RVMODEL_ACCESS_FAULT_ADDRESS",
                ifdef="RVMODEL_ACCESS_FAULT_ADDRESS",
            )
        add(
            level,
            "Leaf PTE points to the access-fault region",
            "Store access fault",
            [*walk, leaf(leaf_permissions, level, physical_address="RVMODEL_ACCESS_FAULT_ADDRESS")],
            physical_address="RVMODEL_ACCESS_FAULT_ADDRESS",
            ifdef="RVMODEL_ACCESS_FAULT_ADDRESS",
        )

        if not top:
            for bit in ("PTE_D", "PTE_A", "PTE_U"):
                # The old tests place the A-bit case's leaf at level 0.
                leaf_level = 0 if bit == "PTE_A" and level > 0 else level
                add(
                    level,
                    f"Non-leaf PTE with {bit.removeprefix('PTE_')} bit set",
                    "Store page fault",
                    [
                        *create_page_walk(sv, leaf_level=level, overrides={level + 1: PteFlags.nonleaf(bit)}),
                        leaf(leaf_permissions, leaf_level),
                    ],
                    ifdef="S1P12P0_OR_LATER_SUPPORTED",
                )


def _begin_test(test_data: TestData, sv: SvMode, mode: str, family: str) -> TestChunk:
    envmask = "MENVCFG_CBCFE | MENVCFG_CBIE" if family == "zicbom" else "MENVCFG_CBZE"
    setup = [f"LI(t0, {envmask})", "csrs menvcfg, t0"]
    if mode == "Umode":
        setup.append("csrs senvcfg, t0")
    qualifier = "_exceptions" if family != "zicbop" else ""
    return begin_sv_test(
        test_data,
        sv,
        mode,
        f"{sv.name}_{family}{qualifier}_{mode}",
        coverpoint=f"cp_{family}",
        sig_init="" if family == "zicbop" else "LI(a2, 0x800) // Test signature initialization",
        setup_asm=tuple(setup),
    )


def _make_exceptions(test_data: TestData, sv: SvMode, mode: str, family: str) -> TestChunk:
    chunk = _begin_test(test_data, sv, mode, family)
    _add_exception_cases(test_data, chunk, sv, mode, family)
    chunk.raw_data.extend(sv_data(sv))
    return test_data.end_test_chunk()


def _make_prefetch(test_data: TestData, sv: SvMode, mode: str) -> TestChunk:
    chunk = _begin_test(test_data, sv, mode, "zicbop")
    permissions = PteFlags(user=mode == "Umode")
    for number, level in enumerate(sv.levels_desc, start=1):
        chunk.code.extend(
            [
                *create_page_mapping(
                    sv,
                    leaf_level=level,
                    leaf_flags=permissions,
                ),
                "sfence.vma",
                "",
                *_add_operation(test_data, "zicbop", mode, virtual_address(sv, "va_data", level), number),
                "",
            ]
        )
    chunk.raw_data.extend(sv_data(sv))
    chunk.trap_sigupd_count = 10
    return test_data.end_test_chunk()


def _make_svzicbo(test_data: TestData, sv: SvMode, family: str) -> list[TestChunk]:
    if family == "zicbop":
        return [_make_prefetch(test_data, sv, mode) for mode in ("Smode", "Umode")]
    return [_make_exceptions(test_data, sv, mode, family) for mode in ("Smode", "Umode")]


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["I", "Sv32", "Zicbom"],
    march_extensions=_MARCH + ["Zicbom"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svzicbo_sv32_zicbom(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV32, "zicbom")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["I", "Sv32", "Zicboz"],
    march_extensions=_MARCH + ["Zicboz"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svzicbo_sv32_zicboz(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV32, "zicboz")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["I", "Sv32", "Zicbop"],
    march_extensions=_MARCH + ["Zicbop"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svzicbo_sv32_zicbop(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV32, "zicbop")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["I", "Sv39", "Zicbom"],
    march_extensions=_MARCH + ["Zicbom"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svzicbo_sv39_zicbom(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV39, "zicbom")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["I", "Sv39", "Zicboz"],
    march_extensions=_MARCH + ["Zicboz"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svzicbo_sv39_zicboz(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV39, "zicboz")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["I", "Sv39", "Zicbop"],
    march_extensions=_MARCH + ["Zicbop"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svzicbo_sv39_zicbop(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV39, "zicbop")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["I", "Sv48", "Zicbom"],
    march_extensions=_MARCH + ["Zicbom"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svzicbo_sv48_zicbom(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV48, "zicbom")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["I", "Sv48", "Zicboz"],
    march_extensions=_MARCH + ["Zicboz"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svzicbo_sv48_zicboz(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV48, "zicboz")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["I", "Sv48", "Zicbop"],
    march_extensions=_MARCH + ["Zicbop"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svzicbo_sv48_zicbop(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV48, "zicbop")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["I", "Sv57", "Zicbom"],
    march_extensions=_MARCH + ["Zicbom"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svzicbo_sv57_zicbom(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV57, "zicbom")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["I", "Sv57", "Zicboz"],
    march_extensions=_MARCH + ["Zicboz"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svzicbo_sv57_zicboz(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV57, "zicboz")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["I", "Sv57", "Zicbop"],
    march_extensions=_MARCH + ["Zicbop"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svzicbo_sv57_zicbop(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV57, "zicbop")
