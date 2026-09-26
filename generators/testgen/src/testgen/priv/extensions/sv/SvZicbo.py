##################################
# priv/extensions/sv/SvZicbo.py
#
# SvZicbo suite: cache-block operations under virtual memory.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate cache-block operation tests under virtual memory."""

from testgen.asm.helpers import write_sigupd
from testgen.asm.tsbi import tsbi_call
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


def _add_operation(
    test_data: TestData, sv: SvMode, family: str, mode: str, address: list[str], number: int, cross: str
) -> list[str]:
    lines = [*address, *([] if mode == "Smode" else [f"RVTEST_TSBI_GOTO_{mode.upper()}"])]
    if family == "zicbop":
        for operation in ("prefetch.i", "prefetch.r", "prefetch.w"):
            lines.extend(
                [
                    test_data.add_testcase(f"test{number}_{operation.replace('.', '_')}", cross, "SvZicbo_cg"),
                    f"{operation} 0(a5)",
                    "nop",
                ]
            )
    elif family == "zicbom":
        labels = {
            operation: test_data.add_testcase(f"test{number}_{operation}", cross, "SvZicbo_cg").removesuffix(":")
            for operation in ("clean", "flush", "inval")
        }
        lines.extend(["addi a2, a2, 16"])
        for operation, register in (("clean", "a2"), ("flush", "a3"), ("inval", "a4")):
            lines.extend([f"{labels[operation]}:", f"cbo.{operation} (a5)", f"addi {register}, a2, 4"])
        lines.extend(
            [
                *([] if mode == "Smode" else ["RVTEST_TSBI_GOTO_SMODE"]),
                *(
                    write_sigupd(reg, test_data, label=labels[op])
                    for op, reg in (("clean", 12), ("flush", 13), ("inval", 14))
                ),
            ]
        )
        return lines
    else:
        label = test_data.add_testcase(f"test{number}_zero", cross, "SvZicbo_cg").removesuffix(":")
        lines.extend(
            [
                "addi a2, a2, 16",
                f"{label}:",
                "cbo.zero (a5)",
                "addi a4, a2, 4",
                *([] if mode == "Smode" else ["RVTEST_TSBI_GOTO_SMODE"]),
                write_sigupd(14, test_data, label=label),
            ]
        )
        return lines
    lines.extend([] if mode == "Smode" else ["RVTEST_TSBI_GOTO_SMODE"])
    return lines


def _add_exception_cases(test_data: TestData, chunk: TestChunk, sv: SvMode, mode: str, family: str) -> None:
    """Add the cache-block exception cases for each page-table level."""
    number = 0
    m = mode[0].lower()
    # Zicbom needs read or write permission and ignores PTE.D; Zicboz needs write permission and PTE.D.
    no_write = f"cp_PTE_r_set_w_unset_zicbom_{m}" if family == "zicbom" else f"cp_PTE_w_unset_zicboz_{m}"
    dirty_unset = f"cp_Dbit_unset_{family}_{m}"

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
        cross: str,
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
            *_add_operation(test_data, sv, family, mode, address, number, cross),
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
        cross: str,
        *,
        before: tuple[str, ...] = (),
        after: tuple[str, ...] = (),
        ifdef: str | None = None,
    ) -> None:
        add(
            level,
            description,
            expected,
            cross,
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

        add_standard(level, PteFlags(user=umode, valid=False), "PTE.V unset", "Store page fault", f"cp_PTE_inv_cbo_{m}")
        add_standard(
            level,
            PteFlags(user=umode, read=False),
            "Reserved W+X without R",
            "Store page fault",
            f"cp_PTE_res_rwx_cbo_{m}",
            ifdef="S1P12P0_OR_LATER_SUPPORTED",
        )
        add_standard(
            level,
            PteFlags(user=umode, read=False, execute=False),
            "Reserved W without R",
            "Store page fault",
            f"cp_PTE_res_rwx_cbo_{m}",
            ifdef="S1P12P0_OR_LATER_SUPPORTED",
        )
        add_standard(level, PteFlags(user=umode, write=False), "RX permissions", "Store page fault", no_write)
        if umode:
            add_standard(level, PteFlags(), "Supervisor page from U-Mode", "Store page fault", "cp_spage_rwx_cbo_u")
        else:
            add_standard(
                level,
                PteFlags(write=False),
                "RX permissions with sstatus.SUM set",
                "Store page fault",
                no_write,
                before=("  LI(t0, MSTATUS_SUM)", "  csrs sstatus, t0"),
                after=("  LI(t0, MSTATUS_SUM)", "  csrc sstatus, t0"),
            )
            add_standard(
                level, PteFlags(user=True), "User page from S-Mode", "Store page fault", "cp_upage_sumunset_cbo_s"
            )
        if family == "zicbom":
            add_standard(
                level,
                PteFlags(user=umode, read=False, write=False),
                "Execute-only page",
                "Store page fault",
                f"cp_PTE_rw_unset_zicbom_{m}",
            )
        add_standard(
            level, PteFlags(user=umode, accessed=False), "PTE.A unset", "Store page fault", f"cp_Abit_unset_cbo_{m}"
        )
        add_standard(level, PteFlags(user=umode, dirty=False), "PTE.D unset", "No fault", dirty_unset)

        walk = create_page_walk(sv, leaf_level=level)
        if level > 0:
            add(
                level,
                "Misaligned superpage",
                "Store page fault",
                f"cp_misaligned_page_cbo_{m}",
                [*walk, leaf(leaf_permissions, level, superpage=False)],
                physical_address="0x0",
            )
        else:
            add(
                level,
                "Pointer encoding (V only) in the leaf",
                "Store page fault",
                f"cp_PTE_nonleaf_lvl0_cbo_{m}",
                [*walk, leaf(PteFlags.nonleaf("PTE_U") if umode else PteFlags.nonleaf(), level)],
            )

        if not top and level > 0:
            add(
                level,
                "Access fault on the page-table walk",
                "Store access fault",
                "cp_nonleaf_PTE_to_nonexistent_pa_cbo",
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
                "cp_nonleaf_PTE_to_nonexistent_pa_cbo",
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
            f"cp_leaf_PTE_to_nonexistent_pa_cbo_{m}",
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
                    "cp_PTE_nonleaf_DAU_cbo",
                    [
                        *create_page_walk(sv, leaf_level=level, overrides={level + 1: PteFlags.nonleaf(bit)}),
                        leaf(leaf_permissions, leaf_level),
                    ],
                    ifdef="S1P12P0_OR_LATER_SUPPORTED",
                )


def _begin_test(test_data: TestData, sv: SvMode, mode: str, family: str) -> TestChunk:
    envmask = "MENVCFG_CBCFE | MENVCFG_CBIE" if family == "zicbom" else "MENVCFG_CBZE"
    setup = [f"LI(t0, {envmask})", tsbi_call("csrs menvcfg, t0")]
    if mode == "Umode":
        setup.append("csrs senvcfg, t0")
    qualifier = "_exceptions" if family != "zicbop" else ""
    return begin_sv_test(
        test_data,
        sv,
        mode,
        f"{sv.name}_{family}{qualifier}_{mode}",
        coverpoint=f"cp_PTE_rwx_zicbop_{mode[0].lower()}"
        if family == "zicbop"
        else f"SvZicbo {family} exception crosses",
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
                *_add_operation(
                    test_data,
                    sv,
                    "zicbop",
                    mode,
                    virtual_address(sv, "va_data", level),
                    number,
                    f"cp_PTE_rwx_zicbop_{mode[0].lower()}",
                ),
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
    required_extensions=["Sv32", "Zicbom"],
    march_extensions=["Zicbom"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svzicbo_sv32_zicbom(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV32, "zicbom")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["Sv32", "Zicboz"],
    march_extensions=["Zicboz"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svzicbo_sv32_zicboz(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV32, "zicboz")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["Sv32", "Zicbop"],
    march_extensions=["Zicbop"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svzicbo_sv32_zicbop(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV32, "zicbop")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["Sv39", "Zicbom"],
    march_extensions=["Zicbom"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svzicbo_sv39_zicbom(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV39, "zicbom")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["Sv39", "Zicboz"],
    march_extensions=["Zicboz"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svzicbo_sv39_zicboz(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV39, "zicboz")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["Sv39", "Zicbop"],
    march_extensions=["Zicbop"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svzicbo_sv39_zicbop(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV39, "zicbop")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["Sv48", "Zicbom"],
    march_extensions=["Zicbom"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svzicbo_sv48_zicbom(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV48, "zicbom")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["Sv48", "Zicboz"],
    march_extensions=["Zicboz"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svzicbo_sv48_zicboz(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV48, "zicboz")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["Sv48", "Zicbop"],
    march_extensions=["Zicbop"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svzicbo_sv48_zicbop(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV48, "zicbop")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["Sv57", "Zicbom"],
    march_extensions=["Zicbom"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svzicbo_sv57_zicbom(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV57, "zicbom")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["Sv57", "Zicboz"],
    march_extensions=["Zicboz"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svzicbo_sv57_zicboz(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV57, "zicboz")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["Sv57", "Zicbop"],
    march_extensions=["Zicbop"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svzicbo_sv57_zicbop(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV57, "zicbop")
