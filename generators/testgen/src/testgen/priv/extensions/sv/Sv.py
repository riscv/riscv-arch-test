##################################
# priv/extensions/sv/Sv.py
#
# Sv suite: core virtual-memory behavior (PTE permissions, satp, mstatus VM fields).
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate core PTE, satp, and mstatus virtual-memory tests."""

from collections.abc import Mapping

from testgen.asm.csr import gen_csr_read_sigupd
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk, trap_sigupd_count
from testgen.priv.extensions.sv.access import add_rwx_test
from testgen.priv.extensions.sv.assembly import VA_ONES_DATA, VA_ZEROS_DATA
from testgen.priv.extensions.sv.generate import begin_sv_test, keep_image_mapped, sv_data
from testgen.priv.extensions.sv.page_tables import (
    SV32,
    SV39,
    SV48,
    SV57,
    PteExpression,
    PteFlags,
    SvMode,
    create_page_mapping,
)
from testgen.priv.registry import add_priv_test_generator


def change_pte_to_be(sv: SvMode) -> list[str]:
    width, shift = (4, 24) if sv.xlen == 32 else (8, 56)
    return [
        "li a3, 0",
        "li a4, 0",
        f"li a5, {shift}",
        f".rept({width})",
        "andi a3, a0, 0xFF",
        "srli a0, a0, 8",
        "sll a3, a3, a5",
        "or a4, a4, a3",
        "addi a5, a5, -8",
        ".endr",
        "SREG a4, 0(t1)",
    ]


def level_header(sv: SvMode, level: int) -> list[str]:
    return ["", f"// {sv.page_names[level]} page at level {level}", ""]


MPRV_CLEANUP = ("LI(t0, MSTATUS_MPRV)", "csrc mstatus, t0")


def mstatus_setup(kind: str) -> tuple[str, ...]:
    if kind == "mprv_s":
        return (
            "LI(t0, MSTATUS_MPRV)",
            "csrs mstatus, t0",
            "LI(t0, 0x1800)",
            "csrc mstatus, t0",
            "LI(t0, 0x800)",
            "csrs mstatus, t0",
        )
    if kind == "mprv_u":
        return ("LI(t0, MSTATUS_MPRV)", "csrs mstatus, t0", "LI(t0, 0x1800)", "csrc mstatus, t0")
    if kind == "mprv_sum_set":
        return (*mstatus_setup("mprv_s"), "LI(t0, MSTATUS_SUM)", "csrs mstatus, t0")
    if kind == "mprv_sum_unset":
        return (*mstatus_setup("mprv_s"), "LI(t0, MSTATUS_SUM)", "csrc mstatus, t0")
    raise ValueError(f"Unknown mstatus setup: {kind}")


def _add_rsw_readback(test_data: TestData, sv: SvMode, level: int, name: str) -> list[str]:
    assert test_data.test_chunk is not None
    offsets = {
        "sv32": {1: 64, 0: 28},
        "sv39": {2: 40, 1: 32, 0: 16},
        "sv48": {3: 40, 2: 160, 1: 16, 0: 24},
        "sv57": {4: 56, 3: 40, 2: 160, 1: 16, 0: 24},
    }
    table = sv.page_table_label(level)
    offset = offsets[sv.name][level]
    label = test_data.add_testcase(
        f"{name}_read_pte", f"cp_{test_data.test_chunk.split_name}", test_data.testsuite
    ).removesuffix(":")
    load = "lw" if sv.xlen == 32 else "ld"
    return [f"LA(a4, {table})", f"{label}:", f"{load} a4, {offset}(a4)", write_sigupd(14, test_data, label=label)]


def _extreme_access(
    test_data: TestData, sv: SvMode, name: str, va: str, mode: str, style: str, driver_mode: str
) -> list[str]:
    assert test_data.test_chunk is not None
    coverpoint = f"cp_{test_data.test_chunk.split_name}"
    operations = ("store", "load") if style.startswith("rw") else ("exec",)
    labels = {
        operation: test_data.add_testcase(f"{name}_{operation}", coverpoint, test_data.testsuite).removesuffix(":")
        for operation in operations
    }
    lines = [*([] if mode == driver_mode else [f"RVTEST_TSBI_GOTO_{mode.upper()}"]), f"LI(a5, {va})"]
    if style.startswith("rw"):
        instruction = "sw" if style == "rw_word" else "sb"
        load = "lw" if style == "rw_word" else "lbu"
        lines.extend(
            [
                "addi a2, a2, 16",
                f"{labels['store']}:",
                f"{instruction} a2, 0(a5)",
                "nop",
                f"{labels['load']}:",
                f"{load} a3, 0(a5)",
                "nop",
                *([] if mode == driver_mode else [f"RVTEST_TSBI_GOTO_{driver_mode.upper()}"]),
                write_sigupd(12, test_data, label=labels["store"]),
                write_sigupd(13, test_data, label=labels["load"]),
            ]
        )
    else:
        lines.extend(
            [
                f"{labels['exec']}:",
                "jalr ra, a5, 0",
                "nop",
                *([] if mode == driver_mode else [f"RVTEST_TSBI_GOTO_{driver_mode.upper()}"]),
                write_sigupd(14, test_data, label=labels["exec"]),
            ]
        )
    return lines


def emit_access(
    test_data: TestData,
    sv: SvMode,
    level: int,
    style: str,
    name: str,
    va: str,
    mode: str,
    driver_mode: str = "Smode",
) -> list[str]:
    if style in ("rw_byte", "rw_word", "x_only"):
        return _extreme_access(test_data, sv, name, va, mode, style, driver_mode)
    setup: tuple[str, ...] = ()
    cleanup: tuple[str, ...] = ()
    if style.startswith("mprv_"):
        setup, cleanup = mstatus_setup(style), MPRV_CLEANUP
    elif style == "sum":
        setup = ("LI(t0, MSTATUS_SUM)", "csrs sstatus, t0")
    return add_rwx_test(
        test_data,
        sv,
        mode,
        va,
        level,
        name,
        driver_mode=driver_mode,
        address=[f"LI(a5, {va})"] if style == "direct" else None,
        setup=setup,
        cleanup=cleanup,
        repeat_setup=style == "mprv_sum_unset",
        physical_fetch=style.startswith("mprv_"),
        include_exec=style != "sl",
    ) + (_add_rsw_readback(test_data, sv, level, name) if style == "rsw" else [])


def _t_invalid_pte(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    for mode in ("Smode", "Umode"):
        chunk = begin_sv_test(test_data, sv, mode, f"{sv.name}_invalid_pte_{mode}")
        for number, level in enumerate(sv.levels_desc, start=1):
            permissions = PteFlags(user=mode == "Umode", valid=False)
            chunk.code.extend(
                [
                    *level_header(sv, level),
                    f"// Test case {number}: V bit unset | Test in {mode[0]}-Mode | RWX bit set | expected = RWX fault",
                    *create_page_mapping(sv, leaf_level=level, leaf_flags=permissions),
                    "sfence.vma",
                    "",
                    *emit_access(test_data, sv, level, "rwx", f"test{number}", "va_data", mode),
                    "",
                ]
            )
        chunk.raw_data.extend(sv_data(sv))
        chunk.trap_sigupd_count = trap_sigupd_count(sv.levels * 3)
        test_chunks.append(test_data.end_test_chunk())


_CANONICAL_VA = {"sv39": "0x8000000140802000", "sv48": "0x8000028500403000", "sv57": "0x8007028500403000"}


def _t_canonical(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    if sv.name not in _CANONICAL_VA:
        return
    for mode in ("Smode", "Umode"):
        chunk = begin_sv_test(
            test_data,
            sv,
            mode,
            f"{sv.name}_canonical_{mode}",
            va_defs=(("va_data", _CANONICAL_VA[sv.name]),),
        )
        for number, level in enumerate(sv.levels_desc, start=1):
            permissions = PteFlags(user=mode == "Umode")
            chunk.code.extend(
                [
                    *level_header(sv, level),
                    f"// Test case {number}: Non-canonical VA | Test in {mode[0]}-Mode | RWX bit set | expected = RWX fault",
                    *create_page_mapping(sv, leaf_level=level, leaf_flags=permissions),
                    "sfence.vma",
                    "",
                    *emit_access(test_data, sv, level, "rwx", f"test{number}", "va_data", mode),
                    "",
                ]
            )
        chunk.raw_data.extend(sv_data(sv))
        chunk.trap_sigupd_count = trap_sigupd_count(sv.levels * 3)
        test_chunks.append(test_data.end_test_chunk())


def _t_global_pte(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    asid_lines = (
        ("  csrr  t0, satp", "  slli  t0, t0, 1", "  srli  t0, t0, 23", "  sfence.vma x0, t0")
        if sv.xlen == 32
        else ("  csrr  t0, satp", "  slli  t0, t0, 4", "  srli  t0, t0, 48", "  sfence.vma x0, t0")
    )
    for mode in ("Smode", "Umode"):
        chunk = begin_sv_test(test_data, sv, mode, f"{sv.name}_global_pte_{mode}")
        for number, level in enumerate(sv.levels_desc, start=1):
            permissions = PteFlags(user=mode == "Umode", global_=True)
            first_name = f"test{number}_access1"
            second_name = f"test{number}_access2"
            chunk.code.extend(
                [
                    *level_header(sv, level),
                    (
                        f"  // Test case {number}: Global PTE at level {level} | Test in {mode[0]}-Mode"
                        " | access, sfence with ASID, access again | expected = No Fault"
                    ),
                    *create_page_mapping(sv, leaf_level=level, leaf_flags=permissions),
                    "  sfence.vma",
                    "",
                    *emit_access(test_data, sv, level, "rwx", first_name, "va_data", mode),
                    "",
                    "  // Flush the TLB for the current ASID and access again",
                    *asid_lines,
                    "",
                    *emit_access(test_data, sv, level, "rwx", second_name, "va_data", mode),
                    "",
                ]
            )
        chunk.raw_data.extend(sv_data(sv))
        chunk.trap_sigupd_count = 10
        test_chunks.append(test_data.end_test_chunk())


_MISALIGNED_VA = {
    "sv32": "0x90400000",
    "sv39": "0x140000000",
    "sv48": "0x028000000000",
    "sv57": "0x07000000000000",
}


def _t_misaligned_page(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    levels = tuple(level for level in sv.levels_desc if level > 0)
    for mode in ("Smode", "Umode"):
        chunk = begin_sv_test(
            test_data,
            sv,
            mode,
            f"{sv.name}_misaligned_page_{mode}",
            va_defs=(("va_data", _MISALIGNED_VA[sv.name]),),
        )
        for number, level in enumerate(levels, start=1):
            permissions = PteFlags(user=mode == "Umode")
            chunk.code.extend(
                [
                    *level_header(sv, level),
                    f"// Test case {number}: Misaligned superpage | Test in {mode[0]}-Mode | RWX bit set | expected = RWX fault",
                    *create_page_mapping(
                        sv,
                        leaf_level=level,
                        leaf_flags=permissions,
                        superpage=False,
                    ),
                    "sfence.vma",
                    "",
                    *emit_access(test_data, sv, level, "rwx", f"test{number}", "va_data", mode),
                    "",
                ]
            )
        chunk.raw_data.extend(sv_data(sv, levels))
        chunk.trap_sigupd_count = trap_sigupd_count(len(levels) * 3)
        test_chunks.append(test_data.end_test_chunk())


def _t_mstatus_mxr(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    for mode in ("Smode", "Umode"):
        chunk = begin_sv_test(test_data, sv, mode, f"{sv.name}_mstatus_mxr_{mode}")
        number = 0
        faults = 0
        for level in sv.levels_desc:
            for operation, expected, case_faults in (
                ("csrc", "Load & Store page fault", 2),
                ("csrs", "Store page fault", 1),
            ):
                number += 1
                faults += case_faults
                permissions = PteFlags(user=mode == "Umode", read=False, write=False)
                chunk.code.extend(
                    [
                        *level_header(sv, level),
                        (
                            f"// Test case {number}: X-only page, MXR {'unset' if operation == 'csrc' else 'set'}"
                            f" | Test in {mode[0]}-Mode | expected = {expected}"
                        ),
                        *create_page_mapping(sv, leaf_level=level, leaf_flags=permissions),
                        "sfence.vma",
                        "  LI(   t0, MSTATUS_MXR)",
                        f"  {operation}  sstatus, t0",
                        "",
                        *emit_access(test_data, sv, level, "rwx", f"test{number}", "va_data", mode),
                        "",
                    ]
                )
        chunk.raw_data.extend(sv_data(sv))
        chunk.trap_sigupd_count = trap_sigupd_count(faults)
        test_chunks.append(test_data.end_test_chunk())


def _t_nleaf_pte_dau(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    for mode in ("Smode", "Umode"):
        chunk = begin_sv_test(
            test_data,
            sv,
            mode,
            f"{sv.name}_nleaf_pte_DAU_{mode}",
            code_prefix=("#ifdef S1P12P0_OR_LATER_SUPPORTED", ""),
        )
        number = 0
        for table_level in range(sv.levels - 1, 0, -1):
            for bit in ("PTE_D", "PTE_A", "PTE_U"):
                number += 1
                permissions = PteFlags(user=mode == "Umode")
                chunk.code.extend(
                    [
                        *level_header(sv, 0),
                        (
                            f"// Test case {number}: Non-leaf {bit.removeprefix('PTE_')} bit set at level {table_level}"
                            f" | Test in {mode[0]}-Mode | expected = RWX fault"
                        ),
                        *create_page_mapping(
                            sv,
                            leaf_level=0,
                            leaf_flags=permissions,
                            walk_overrides={table_level: PteFlags.nonleaf(bit)},
                        ),
                        "sfence.vma",
                        "",
                        *emit_access(test_data, sv, 0, "rwx", f"test{number}", "va_data", mode),
                        "",
                    ]
                )
        chunk.code.append("#endif")
        chunk.raw_data.extend(sv_data(sv, (0,)))
        chunk.trap_sigupd_count = trap_sigupd_count(number * 3)
        test_chunks.append(test_data.end_test_chunk())


def _t_nleaf_pte_level0(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    for mode in ("Smode", "Umode"):
        chunk = begin_sv_test(test_data, sv, mode, f"{sv.name}_nleaf_pte_level0_{mode}")
        permissions = PteFlags(
            user=mode == "Umode",
            read=False,
            write=False,
            execute=False,
            accessed=False,
            dirty=False,
        )
        chunk.code.extend(
            [
                *level_header(sv, 0),
                f"// Test case 1: Level 0 PTE with pointer encoding | Test in {mode[0]}-Mode | expected = RWX fault",
                *create_page_mapping(sv, leaf_level=0, leaf_flags=permissions),
                "sfence.vma",
                "",
                *emit_access(
                    test_data,
                    sv,
                    0,
                    "direct" if sv.name == "sv39" else "rwx",
                    "test1",
                    "va_data",
                    mode,
                ),
                "",
            ]
        )
        chunk.raw_data.extend(sv_data(sv, (0,)))
        chunk.trap_sigupd_count = trap_sigupd_count(3)
        test_chunks.append(test_data.end_test_chunk())


def _t_pte_reserved_rwx(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    for mode in ("Smode", "Umode"):
        chunk = begin_sv_test(
            test_data,
            sv,
            mode,
            f"{sv.name}_pte_reserved_rwx_{mode}",
            code_prefix=("#ifdef S1P12P0_OR_LATER_SUPPORTED", ""),
        )
        number = 0
        for level in sv.levels_desc:
            for read, write, execute, description in (
                (False, True, True, "W and X set without R"),
                (False, True, False, "W set without R"),
            ):
                number += 1
                permissions = PteFlags(
                    user=mode == "Umode",
                    read=read,
                    write=write,
                    execute=execute,
                )
                chunk.code.extend(
                    [
                        *level_header(sv, level),
                        (
                            f"// Test case {number}: Reserved encoding: {description}"
                            f" | Test in {mode[0]}-Mode | expected = RWX fault"
                        ),
                        *create_page_mapping(sv, leaf_level=level, leaf_flags=permissions),
                        "sfence.vma",
                        "",
                        *emit_access(test_data, sv, level, "rwx", f"test{number}", "va_data", mode),
                        "",
                    ]
                )
        chunk.code.append("#endif")
        chunk.raw_data.extend(sv_data(sv))
        chunk.trap_sigupd_count = trap_sigupd_count(number * 3)
        test_chunks.append(test_data.end_test_chunk())


def _t_pte_rsw(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    va_defs = (("va_data", "0x04007000"),) if sv.xlen == 32 else None
    for mode in ("Smode", "Umode"):
        chunk = begin_sv_test(test_data, sv, mode, f"{sv.name}_pte_rsw_{mode}", va_defs=va_defs)
        number = 0
        for level in sv.levels_desc:
            for rsw, description in (
                ("(1 << 8)", "RSW=01"),
                ("(1 << 9)", "RSW=10"),
                ("(1 << 9) | (1 << 8)", "RSW=11"),
            ):
                number += 1
                permissions = PteFlags(user=mode == "Umode", extra=(rsw,))
                chunk.code.extend(
                    [
                        *level_header(sv, level),
                        (
                            f"// Test case {number}: {description} | Test in {mode[0]}-Mode"
                            " | RWX bit set | expected = No Fault"
                        ),
                        *create_page_mapping(sv, leaf_level=level, leaf_flags=permissions),
                        "sfence.vma",
                        "",
                        *emit_access(test_data, sv, level, "rsw", f"test{number}", "va_data", mode),
                        "",
                    ]
                )
        chunk.raw_data.extend(sv_data(sv))
        chunk.trap_sigupd_count = 10
        test_chunks.append(test_data.end_test_chunk())


def _t_pte_reserved_field(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    if sv.name == "sv32":
        return
    top = sv.levels - 1
    chunk = begin_sv_test(
        test_data,
        sv,
        "Smode",
        f"{sv.name}_pte_reserved_field_Smode",
        code_prefix=("#ifdef S1P12P0_OR_LATER_SUPPORTED", ""),
    )
    for number, bit in enumerate(range(54, 61), start=1):
        permissions = PteFlags(extra=(f"(1 << {bit})",))
        chunk.code.extend(
            [
                *level_header(sv, top),
                f"// Test case {number}: Reserved bit {bit} set | Test in S-Mode | expected = RWX fault",
                *create_page_mapping(sv, leaf_level=top, leaf_flags=permissions),
                "sfence.vma",
                "",
                *emit_access(test_data, sv, top, "rwx", f"test{number}", "va_data", "Smode"),
                "",
            ]
        )
    chunk.code.append("#endif")
    chunk.raw_data.extend(sv_data(sv, (top,)))
    chunk.trap_sigupd_count = trap_sigupd_count(7 * 3)
    test_chunks.append(test_data.end_test_chunk())


def _t_svpbmt_disabled(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    if sv.name == "sv32":
        return
    setup = (
        (
            "  #ifdef SM1P12P0_OR_LATER_SUPPORTED",
            "      LI(t0, MENVCFG_PBMTE)",
            tsbi_call("csrc menvcfg, t0"),
            "  #endif",
        )
        if sv.name == "sv39"
        else ("  LI(t0, MENVCFG_PBMTE)", tsbi_call("csrc menvcfg, t0"))
    )
    pbmt = (
        (("(1 << 61)", "PBMT=1"), ("(2 << 61)", "PBMT=2"), ("(3 << 61)", "PBMT=3"))
        if sv.name == "sv57"
        else (("(1 << 61)", "PBMT=1"), ("(1 << 62)", "PBMT=2"), ("(1 << 62) | (1 << 61)", "PBMT=3"))
    )
    top = sv.levels - 1
    chunk = begin_sv_test(
        test_data,
        sv,
        "Smode",
        f"{sv.name}_svpbmt_disabled_Smode",
        code_prefix=("#ifdef S1P12P0_OR_LATER_SUPPORTED", ""),
        setup_asm=setup,
    )
    for number, (bits, description) in enumerate(pbmt, start=1):
        permissions = PteFlags(extra=(bits,))
        chunk.code.extend(
            [
                *level_header(sv, top),
                f"// Test case {number}: {description}, PBMTE disabled | Test in S-Mode | expected = RWX fault",
                *create_page_mapping(sv, leaf_level=top, leaf_flags=permissions),
                "sfence.vma",
                "",
                *emit_access(test_data, sv, top, "rwx", f"test{number}", "va_data", "Smode"),
                "",
            ]
        )
    chunk.code.append("#endif")
    chunk.raw_data.extend(sv_data(sv, (top,)))
    chunk.trap_sigupd_count = trap_sigupd_count(3 * 3)
    test_chunks.append(test_data.end_test_chunk())


_NAPOT_VA = {"sv39": "0x140860000", "sv48": "0x028500430000", "sv57": "0x07028500430000"}


def _t_svnapot_not_supported(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    if sv.name == "sv32":
        return
    napot_bit = "PTE_N" if sv.name == "sv39" else "(1 << 63)"
    permissions = PteFlags(extra=(napot_bit, "(1 << 13)"))
    chunk = begin_sv_test(
        test_data,
        sv,
        "Smode",
        f"{sv.name}_svnapot_not_supported_Smode",
        code_prefix=("#ifdef S1P12P0_OR_LATER_SUPPORTED", ""),
        va_defs=(("va_data", _NAPOT_VA[sv.name]),),
    )
    chunk.code.extend(
        [
            *level_header(sv, 0),
            (
                "// Test case 1: Test in S-Mode | RWX bit set | Bit 63 (PTE.N) set"
                " | PTE.PPN0[3] set (64KiB region encoding)"
            ),
            *create_page_mapping(sv, leaf_level=0, leaf_flags=permissions),
            "sfence.vma",
            "",
            *emit_access(
                test_data,
                sv,
                0,
                "direct" if sv.name == "sv39" else "rwx",
                "test1",
                "va_data",
                "Smode",
            ),
            "",
            "#endif",
        ]
    )
    chunk.raw_data.extend(sv_data(sv, (0,), data_align=16))
    chunk.trap_sigupd_count = trap_sigupd_count(3)
    test_chunks.append(test_data.end_test_chunk())


_PAGE_PERMS = (
    (True, True, True, "RWX"),
    (False, False, True, "X-only"),
    (True, False, True, "RX"),
    (True, True, False, "RW"),
    (True, False, False, "R-only"),
)


def _add_page_permission_matrix(
    test_data: TestData,
    chunk: TestChunk,
    sv: SvMode,
    mode: str,
    *,
    user_page: bool,
    fault_counts: Mapping[str, int] | int,
    style: str = "rwx",
) -> int:
    number = 0
    faults = 0
    for level in sv.levels_desc:
        for read, write, execute, description in _PAGE_PERMS:
            number += 1
            case_faults = fault_counts[description] if isinstance(fault_counts, Mapping) else fault_counts
            faults += case_faults
            expected = "No Fault" if case_faults == 0 else f"{case_faults} page fault(s)"
            permissions = PteFlags(
                user=user_page,
                read=read,
                write=write,
                execute=execute,
            )
            chunk.code.extend(
                [
                    *level_header(sv, level),
                    f"// Test case {number}: {description} page | expected = {expected}",
                    *create_page_mapping(sv, leaf_level=level, leaf_flags=permissions),
                    "sfence.vma",
                    "",
                    *emit_access(test_data, sv, level, style, f"test{number}", "va_data", mode),
                    "",
                ]
            )
    return faults


def _t_page_perm_topics(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    s_faults = {"RWX": 0, "X-only": 2, "RX": 1, "RW": 1, "R-only": 2}
    if sv.name == "sv32":
        for topic, mode, user_page, faults_for in (
            ("spage", "Smode", False, s_faults),
            ("upage", "Umode", True, s_faults),
            ("spage_access", "Umode", False, 3),
        ):
            chunk = begin_sv_test(test_data, sv, mode, f"{sv.name}_{topic}_{mode}")
            faults = _add_page_permission_matrix(
                test_data,
                chunk,
                sv,
                mode,
                user_page=user_page,
                fault_counts=faults_for,
            )
            chunk.raw_data.extend(sv_data(sv))
            chunk.trap_sigupd_count = trap_sigupd_count(faults)
            test_chunks.append(test_data.end_test_chunk())
    else:
        chunk = begin_sv_test(test_data, sv, "Umode", f"{sv.name}_spage_access_Umode")
        for number, level in enumerate(sv.levels_desc, start=1):
            chunk.code.extend(
                [
                    *level_header(sv, level),
                    f"// Test case {number}: S page | Test in U-Mode | RWX bit set | expected = RWX fault",
                    *create_page_mapping(
                        sv,
                        leaf_level=level,
                        leaf_flags=PteFlags(),
                    ),
                    "sfence.vma",
                    "",
                    *emit_access(test_data, sv, level, "rwx", f"test{number}", "va_data", "Umode"),
                    "",
                ]
            )
        chunk.raw_data.extend(sv_data(sv))
        chunk.trap_sigupd_count = trap_sigupd_count(sv.levels * 3)
        test_chunks.append(test_data.end_test_chunk())

    sum_set_faults = {"RWX": 1, "X-only": 3, "RX": 2, "RW": 1, "R-only": 2}
    for topic, faults_for, style in (
        ("upage_mstatus_sum_set", sum_set_faults, "sum"),
        ("upage_mstatus_sum_unset", 3, "rwx"),
    ):
        chunk = begin_sv_test(test_data, sv, "Smode", f"{sv.name}_{topic}_Smode")
        faults = _add_page_permission_matrix(
            test_data,
            chunk,
            sv,
            "Smode",
            user_page=True,
            fault_counts=faults_for,
            style=style,
        )
        chunk.raw_data.extend(sv_data(sv))
        chunk.trap_sigupd_count = trap_sigupd_count(faults)
        test_chunks.append(test_data.end_test_chunk())

    chunk = begin_sv_test(test_data, sv, "Smode", f"{sv.name}_spage_mstatus_sum_set_Smode")
    number = 0
    faults = 0
    spage_permissions = ((True, True, True, "RWX"), (True, False, False, "R-only"), (False, False, True, "X-only"))
    spage_faults = {"RWX": 0, "R-only": 2, "X-only": 2}
    for level in sv.levels_desc:
        for read, write, execute, description in spage_permissions:
            number += 1
            case_faults = spage_faults[description]
            faults += case_faults
            expected = "No Fault" if case_faults == 0 else f"{case_faults} page fault(s)"
            chunk.code.extend(
                [
                    *level_header(sv, level),
                    f"// Test case {number}: {description} S page, SUM set | expected = {expected}",
                    *create_page_mapping(
                        sv,
                        leaf_level=level,
                        leaf_flags=PteFlags(read=read, write=write, execute=execute),
                    ),
                    "sfence.vma",
                    "",
                    *emit_access(test_data, sv, level, "sum", f"test{number}", "va_data", "Smode"),
                    "",
                ]
            )
    chunk.raw_data.extend(sv_data(sv))
    chunk.trap_sigupd_count = trap_sigupd_count(faults)
    test_chunks.append(test_data.end_test_chunk())


def _add_va_extreme_test(
    test_data: TestData,
    chunk: TestChunk,
    sv: SvMode,
    *,
    number: int,
    va: str,
    physical_label: str,
    permissions: PteExpression,
    style: str,
) -> None:
    chunk.code.extend(
        [
            *level_header(sv, 0),
            f"// Test case {number}: {'RW' if style.startswith('rw') else 'X'} access at the VA extreme",
            *create_page_mapping(
                sv,
                virtual_address=va,
                physical_address=physical_label,
                leaf_level=0,
                leaf_flags=permissions,
            ),
            "sfence.vma",
            "",
            *emit_access(test_data, sv, 0, style, f"test{number}", va, "Smode"),
            "",
        ]
    )


def _t_va_all(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    all_ones = "0x" + "f" * (sv.xlen // 4)
    all_ones_code = all_ones[:-1] + "c"
    all_zeros = "0x" + "0" * (sv.xlen // 4)
    sig_init = (
        "  LI( a2, 0x800)              // Test signature initialization"
        if sv.xlen == 32
        else "  li a2, 0x12                 // Test signature initialization"
    )

    chunk = begin_sv_test(
        test_data,
        sv,
        "Smode",
        f"{sv.name}_VA_all_ones_Smode",
        sig_init=sig_init,
        va_defs=(("va_data_rw", all_ones), ("va_data_x", all_ones_code)),
    )
    _add_va_extreme_test(
        test_data,
        chunk,
        sv,
        number=1,
        va="va_data_rw",
        physical_label="rvtest_data_1_l0_rw",
        permissions=PteFlags(execute=False),
        style="rw_byte",
    )
    _add_va_extreme_test(
        test_data,
        chunk,
        sv,
        number=2,
        va="va_data_x",
        physical_label="rvtest_data_1_l0_x",
        permissions=PteFlags(read=False, write=False),
        style="x_only",
    )
    chunk.raw_data.extend(sv_data(sv, (0,), data_region_body=VA_ONES_DATA))
    chunk.trap_sigupd_count = 10
    test_chunks.append(test_data.end_test_chunk())

    chunk = begin_sv_test(
        test_data,
        sv,
        "Smode",
        f"{sv.name}_VA_all_zeros_Smode",
        sig_init=sig_init,
        va_defs=(("va_data", all_zeros),),
    )
    if sv.levels > 3:
        chunk.code.extend(keep_image_mapped(sv))
    _add_va_extreme_test(
        test_data,
        chunk,
        sv,
        number=1,
        va="va_data",
        physical_label="rvtest_data_1_l0_rw",
        permissions=PteFlags(execute=False),
        style="rw_word" if sv.name in ("sv32", "sv39") else "rw_byte",
    )
    _add_va_extreme_test(
        test_data,
        chunk,
        sv,
        number=2,
        va="va_data",
        physical_label="rvtest_data_1_l0_x",
        permissions=PteFlags(read=False, write=False),
        style="x_only",
    )
    chunk.raw_data.extend(sv_data(sv, (0,), data_region_body=VA_ZEROS_DATA))
    chunk.trap_sigupd_count = 10
    test_chunks.append(test_data.end_test_chunk())


def satp_csr_read(test_data: TestData, name: str, csr: str = "satp") -> list[str]:
    label = test_data.add_testcase(name, "cp_satp_access", f"{test_data.testsuite}_cg")
    return [label, gen_csr_read_sigupd(14, (csr, None), test_data)]


SATP_FIELDS = {
    "sv32": (31, "0x1FF", 22, 9),
    "sv39": (60, "0xFFFF", 44, 16),
    "sv48": (60, "0xFFFF", 44, 16),
    "sv57": (60, "0xFFFF", 44, 16),
}


def satp_access_ops(test_data: TestData, mode: str, values: tuple[int, int, int]) -> list[str]:
    lines = []
    for operation, value in zip(("csrw", "csrs", "csrc"), values, strict=True):
        lines.extend([f"li a0, {value}", f"{operation} satp, a0"])
        lines.extend(satp_csr_read(test_data, f"{mode[0].lower()}_{operation}"))
    return lines


def _t_satp_access(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    shift, asid_ones, asid_shift, asid_bits = SATP_FIELDS[sv.name]
    chunk = test_data.begin_test_chunk(f"{sv.name}_satp_access_Smode")
    chunk.section_header = comment_banner("cp_satp_access")
    chunk.code.extend(["main:", "csrw scause, zero"])
    if sv.name in ("sv32", "sv39"):
        chunk.code.extend(satp_access_ops(test_data, "Smode", (4, 8, 4)))
        chunk.code.extend(
            [
                "RVTEST_TSBI_GOTO_UMODE",
                "csrw satp, x0",
                "csrs satp, x0",
                "csrc satp, x0",
                "RVTEST_TSBI_GOTO_SMODE",
            ]
        )
    chunk.code.extend(
        [
            "// satp.PPN points at the identity-mapped root table so the S-mode code keeps running",
            "LA(a1, rvtest_Sroot_pg_tbl)",
            "srli a1, a1, 12",
            f"LI(a0, SATP_MODE_{sv.suffix} << {shift})",
            "or a1, a1, a0",
            "csrw satp, a1",
        ]
    )
    chunk.code.extend(satp_csr_read(test_data, f"mode_{sv.name}"))
    chunk.code.extend(["mv a0, a1", "csrw satp, a0"])
    chunk.code.extend(satp_csr_read(test_data, "asid_zeros"))
    chunk.code.extend([f"LI(a0, {asid_ones})", f"slli a0, a0, {asid_shift}", "or a0, a1, a0", "csrw satp, a0"])
    chunk.code.extend(satp_csr_read(test_data, "asid_ones"))
    for bit in range(asid_bits):
        chunk.code.extend(["li a2, 1", f"slli a2, a2, {asid_shift + bit}", "or a0, a1, a2", "csrw satp, a0"])
        chunk.code.extend(satp_csr_read(test_data, f"asid_walk_{bit}"))
    chunk.trap_sigupd_count = 30 if sv.name in ("sv32", "sv39") else 10
    test_chunks.append(test_data.end_test_chunk())


def _make_sv(test_data: TestData, sv: SvMode) -> list[TestChunk]:
    test_chunks: list[TestChunk] = []
    _t_invalid_pte(test_data, test_chunks, sv)
    _t_canonical(test_data, test_chunks, sv)
    _t_global_pte(test_data, test_chunks, sv)
    _t_misaligned_page(test_data, test_chunks, sv)
    _t_mstatus_mxr(test_data, test_chunks, sv)
    _t_nleaf_pte_dau(test_data, test_chunks, sv)
    _t_nleaf_pte_level0(test_data, test_chunks, sv)
    _t_pte_reserved_rwx(test_data, test_chunks, sv)
    _t_pte_rsw(test_data, test_chunks, sv)
    _t_pte_reserved_field(test_data, test_chunks, sv)
    _t_svpbmt_disabled(test_data, test_chunks, sv)
    _t_svnapot_not_supported(test_data, test_chunks, sv)
    _t_page_perm_topics(test_data, test_chunks, sv)
    _t_va_all(test_data, test_chunks, sv)
    _t_satp_access(test_data, test_chunks, sv)
    return test_chunks


@add_priv_test_generator(
    "Sv",
    required_extensions=["Sv32"],
    march_extensions=[],
)
def make_sv32(test_data: TestData) -> list[TestChunk]:
    return _make_sv(test_data, SV32)


@add_priv_test_generator(
    "Sv",
    required_extensions=["Sv39"],
    march_extensions=[],
)
def make_sv39(test_data: TestData) -> list[TestChunk]:
    return _make_sv(test_data, SV39)


@add_priv_test_generator(
    "Sv",
    required_extensions=["Sv48"],
    march_extensions=[],
)
def make_sv48(test_data: TestData) -> list[TestChunk]:
    return _make_sv(test_data, SV48)


@add_priv_test_generator(
    "Sv",
    required_extensions=["Sv57"],
    march_extensions=[],
)
def make_sv57(test_data: TestData) -> list[TestChunk]:
    return _make_sv(test_data, SV57)
