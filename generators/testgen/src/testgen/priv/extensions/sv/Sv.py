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
from testgen.priv.extensions.sv.generate import SvRegs, begin_sv_test, end_sv_test, keep_image_mapped, sv_data
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


def change_pte_to_be(sv: SvMode, regs: SvRegs, pte: int, pte_addr: int) -> list[str]:
    """Rewrite the PTE in x``pte`` big-endian and store it at x``pte_addr``.

    Clobbers x``pte`` and ``regs.addr``, ``regs.load`` and ``regs.result``, none of which is x6, so ``pte``
    and ``pte_addr`` may be the PTE_SETUP_* output registers.
    """
    width, shift = (4, 24) if sv.xlen == 32 else (8, 56)
    byte, word, amount = (f"x{reg}" for reg in (regs.load, regs.result, regs.addr))
    return [
        f"li {byte}, 0",
        f"li {word}, 0",
        f"li {amount}, {shift}",
        f".rept({width})",
        f"andi {byte}, x{pte}, 0xFF",
        f"srli x{pte}, x{pte}, 8",
        f"sll {byte}, {byte}, {amount}",
        f"or {word}, {word}, {byte}",
        f"addi {amount}, {amount}, -8",
        ".endr",
        f"SREG {word}, 0(x{pte_addr})",
    ]


def level_header(sv: SvMode, level: int) -> list[str]:
    return ["", f"// {sv.page_names[level]} page at level {level}", ""]


def mprv_cleanup(scratch: int) -> tuple[str, ...]:
    return (f"LI(x{scratch}, MSTATUS_MPRV)", f"csrc mstatus, x{scratch}")


def mstatus_setup(kind: str, scratch: int) -> tuple[str, ...]:
    t = f"x{scratch}"
    if kind == "mprv_s":
        return (
            f"LI({t}, MSTATUS_MPRV)",
            f"csrs mstatus, {t}",
            f"LI({t}, 0x1800)",
            f"csrc mstatus, {t}",
            f"LI({t}, 0x800)",
            f"csrs mstatus, {t}",
        )
    if kind == "mprv_u":
        return (f"LI({t}, MSTATUS_MPRV)", f"csrs mstatus, {t}", f"LI({t}, 0x1800)", f"csrc mstatus, {t}")
    if kind == "mprv_sum_set":
        return (*mstatus_setup("mprv_s", scratch), f"LI({t}, MSTATUS_SUM)", f"csrs mstatus, {t}")
    if kind == "mprv_sum_unset":
        return (*mstatus_setup("mprv_s", scratch), f"LI({t}, MSTATUS_SUM)", f"csrc mstatus, {t}")
    raise ValueError(f"Unknown mstatus setup: {kind}")


def _add_rsw_readback(test_data: TestData, sv: SvMode, regs: SvRegs, level: int, name: str) -> list[str]:
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
    pte = f"x{regs.result}"
    return [
        f"LA({pte}, {table})",
        f"{label}:",
        f"{load} {pte}, {offset}({pte})",
        write_sigupd(regs.result, test_data, label=label),
    ]


def _extreme_access(
    test_data: TestData, regs: SvRegs, name: str, va: str, mode: str, style: str, driver_mode: str
) -> list[str]:
    assert test_data.test_chunk is not None
    coverpoint = f"cp_{test_data.test_chunk.split_name}"
    operations = ("store", "load") if style.startswith("rw") else ("exec",)
    labels = {
        operation: test_data.add_testcase(f"{name}_{operation}", coverpoint, test_data.testsuite).removesuffix(":")
        for operation in operations
    }
    value, addr = f"x{regs.value}", f"x{regs.addr}"
    lines = [*([] if mode == driver_mode else [f"RVTEST_TSBI_GOTO_{mode.upper()}"]), f"LI({addr}, {va})"]
    if style.startswith("rw"):
        instruction = "sw" if style == "rw_word" else "sb"
        load = "lw" if style == "rw_word" else "lbu"
        lines.extend(
            [
                f"addi {value}, {value}, 16",
                f"{labels['store']}:",
                f"{instruction} {value}, 0({addr})",
                "nop",
                f"{labels['load']}:",
                f"{load} x{regs.load}, 0({addr})",
                "nop",
                *([] if mode == driver_mode else [f"RVTEST_TSBI_GOTO_{driver_mode.upper()}"]),
                write_sigupd(regs.value, test_data, label=labels["store"]),
                write_sigupd(regs.load, test_data, label=labels["load"]),
            ]
        )
    else:
        lines.extend(
            [
                f"{labels['exec']}:",
                f"jalr ra, {addr}, 0",
                "nop",
                *([] if mode == driver_mode else [f"RVTEST_TSBI_GOTO_{driver_mode.upper()}"]),
                write_sigupd(regs.result, test_data, label=labels["exec"]),
            ]
        )
    return lines


def emit_access(
    test_data: TestData,
    sv: SvMode,
    regs: SvRegs,
    level: int,
    style: str,
    name: str,
    va: str,
    mode: str,
    driver_mode: str = "Smode",
) -> list[str]:
    if style in ("rw_byte", "rw_word", "x_only"):
        return _extreme_access(test_data, regs, name, va, mode, style, driver_mode)
    setup: tuple[str, ...] = ()
    cleanup: tuple[str, ...] = ()
    if style.startswith("mprv_"):
        setup, cleanup = mstatus_setup(style, regs.scratch), mprv_cleanup(regs.scratch)
    elif style == "sum":
        setup = (f"LI(x{regs.scratch}, MSTATUS_SUM)", f"csrs sstatus, x{regs.scratch}")
    return add_rwx_test(
        test_data,
        sv,
        regs,
        mode,
        va,
        level,
        name,
        driver_mode=driver_mode,
        address=[f"LI(x{regs.addr}, {va})"] if style == "direct" else None,
        setup=setup,
        cleanup=cleanup,
        repeat_setup=style == "mprv_sum_unset",
        physical_fetch=style.startswith("mprv_"),
        include_exec=style != "sl",
    ) + (_add_rsw_readback(test_data, sv, regs, level, name) if style == "rsw" else [])


def _t_invalid_pte(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    for mode in ("Smode", "Umode"):
        regs = SvRegs.allocate(test_data)
        chunk = begin_sv_test(test_data, regs, sv, mode, f"{sv.name}_invalid_pte_{mode}")
        for number, level in enumerate(sv.levels_desc, start=1):
            permissions = PteFlags(user=mode == "Umode", valid=False)
            chunk.code.extend(
                [
                    *level_header(sv, level),
                    f"// Test case {number}: V bit unset | Test in {mode[0]}-Mode | RWX bit set | expected = RWX fault",
                    *create_page_mapping(sv, leaf_level=level, leaf_flags=permissions),
                    "sfence.vma",
                    "",
                    *emit_access(test_data, sv, regs, level, "rwx", f"test{number}", "va_data", mode),
                    "",
                ]
            )
        chunk.raw_data.extend(sv_data(sv, regs))
        chunk.trap_sigupd_count = trap_sigupd_count(sv.levels * 3)
        test_chunks.append(end_sv_test(test_data, regs))


_CANONICAL_VA = {"sv39": "0x8000000140802000", "sv48": "0x8000028500403000", "sv57": "0x8007028500403000"}


def _t_canonical(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    if sv.name not in _CANONICAL_VA:
        return
    for mode in ("Smode", "Umode"):
        regs = SvRegs.allocate(test_data)
        chunk = begin_sv_test(
            test_data,
            regs,
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
                    *emit_access(test_data, sv, regs, level, "rwx", f"test{number}", "va_data", mode),
                    "",
                ]
            )
        chunk.raw_data.extend(sv_data(sv, regs))
        chunk.trap_sigupd_count = trap_sigupd_count(sv.levels * 3)
        test_chunks.append(end_sv_test(test_data, regs))


def _t_global_pte(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    left, right = (1, 23) if sv.xlen == 32 else (4, 48)
    for mode in ("Smode", "Umode"):
        regs = SvRegs.allocate(test_data)
        asid = f"x{regs.scratch}"
        asid_lines = (
            f"  csrr  {asid}, satp",
            f"  slli  {asid}, {asid}, {left}",
            f"  srli  {asid}, {asid}, {right}",
            f"  sfence.vma x0, {asid}",
        )
        chunk = begin_sv_test(test_data, regs, sv, mode, f"{sv.name}_global_pte_{mode}")
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
                    *emit_access(test_data, sv, regs, level, "rwx", first_name, "va_data", mode),
                    "",
                    "  // Flush the TLB for the current ASID and access again",
                    *asid_lines,
                    "",
                    *emit_access(test_data, sv, regs, level, "rwx", second_name, "va_data", mode),
                    "",
                ]
            )
        chunk.raw_data.extend(sv_data(sv, regs))
        chunk.trap_sigupd_count = 10
        test_chunks.append(end_sv_test(test_data, regs))


_MISALIGNED_VA = {
    "sv32": "0x90400000",
    "sv39": "0x140000000",
    "sv48": "0x028000000000",
    "sv57": "0x07000000000000",
}


def _t_misaligned_page(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    levels = tuple(level for level in sv.levels_desc if level > 0)
    for mode in ("Smode", "Umode"):
        regs = SvRegs.allocate(test_data)
        chunk = begin_sv_test(
            test_data,
            regs,
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
                    *emit_access(test_data, sv, regs, level, "rwx", f"test{number}", "va_data", mode),
                    "",
                ]
            )
        chunk.raw_data.extend(sv_data(sv, regs, levels))
        chunk.trap_sigupd_count = trap_sigupd_count(len(levels) * 3)
        test_chunks.append(end_sv_test(test_data, regs))


def _t_mstatus_mxr(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    for mode in ("Smode", "Umode"):
        regs = SvRegs.allocate(test_data)
        chunk = begin_sv_test(test_data, regs, sv, mode, f"{sv.name}_mstatus_mxr_{mode}")
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
                        f"  LI(   x{regs.scratch}, MSTATUS_MXR)",
                        f"  {operation}  sstatus, x{regs.scratch}",
                        "",
                        *emit_access(test_data, sv, regs, level, "rwx", f"test{number}", "va_data", mode),
                        "",
                    ]
                )
        chunk.raw_data.extend(sv_data(sv, regs))
        chunk.trap_sigupd_count = trap_sigupd_count(faults)
        test_chunks.append(end_sv_test(test_data, regs))


def _t_nleaf_pte_dau(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    for mode in ("Smode", "Umode"):
        regs = SvRegs.allocate(test_data)
        chunk = begin_sv_test(
            test_data,
            regs,
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
                        *emit_access(test_data, sv, regs, 0, "rwx", f"test{number}", "va_data", mode),
                        "",
                    ]
                )
        chunk.code.append("#endif")
        chunk.raw_data.extend(sv_data(sv, regs, (0,)))
        chunk.trap_sigupd_count = trap_sigupd_count(number * 3)
        test_chunks.append(end_sv_test(test_data, regs))


def _t_nleaf_pte_level0(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    for mode in ("Smode", "Umode"):
        regs = SvRegs.allocate(test_data)
        chunk = begin_sv_test(test_data, regs, sv, mode, f"{sv.name}_nleaf_pte_level0_{mode}")
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
                    regs,
                    0,
                    "direct" if sv.name == "sv39" else "rwx",
                    "test1",
                    "va_data",
                    mode,
                ),
                "",
            ]
        )
        chunk.raw_data.extend(sv_data(sv, regs, (0,)))
        chunk.trap_sigupd_count = trap_sigupd_count(3)
        test_chunks.append(end_sv_test(test_data, regs))


def _t_pte_reserved_rwx(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    for mode in ("Smode", "Umode"):
        regs = SvRegs.allocate(test_data)
        chunk = begin_sv_test(
            test_data,
            regs,
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
                        *emit_access(test_data, sv, regs, level, "rwx", f"test{number}", "va_data", mode),
                        "",
                    ]
                )
        chunk.code.append("#endif")
        chunk.raw_data.extend(sv_data(sv, regs))
        chunk.trap_sigupd_count = trap_sigupd_count(number * 3)
        test_chunks.append(end_sv_test(test_data, regs))


def _t_pte_rsw(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    va_defs = (("va_data", "0x04007000"),) if sv.xlen == 32 else None
    for mode in ("Smode", "Umode"):
        regs = SvRegs.allocate(test_data)
        chunk = begin_sv_test(test_data, regs, sv, mode, f"{sv.name}_pte_rsw_{mode}", va_defs=va_defs)
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
                        *emit_access(test_data, sv, regs, level, "rsw", f"test{number}", "va_data", mode),
                        "",
                    ]
                )
        chunk.raw_data.extend(sv_data(sv, regs))
        chunk.trap_sigupd_count = 10
        test_chunks.append(end_sv_test(test_data, regs))


def _t_pte_reserved_field(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    if sv.name == "sv32":
        return
    top = sv.levels - 1
    regs = SvRegs.allocate(test_data)
    chunk = begin_sv_test(
        test_data,
        regs,
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
                *emit_access(test_data, sv, regs, top, "rwx", f"test{number}", "va_data", "Smode"),
                "",
            ]
        )
    chunk.code.append("#endif")
    chunk.raw_data.extend(sv_data(sv, regs, (top,)))
    chunk.trap_sigupd_count = trap_sigupd_count(7 * 3)
    test_chunks.append(end_sv_test(test_data, regs))


def _t_svpbmt_disabled(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    if sv.name == "sv32":
        return
    regs = SvRegs.allocate(test_data)
    pbmte = (f"  LI(x{regs.scratch}, MENVCFG_PBMTE)", tsbi_call(f"csrc menvcfg, x{regs.scratch}"))
    setup = ("  #ifdef SM1P12P0_OR_LATER_SUPPORTED", *pbmte, "  #endif") if sv.name == "sv39" else pbmte
    pbmt = (
        (("(1 << 61)", "PBMT=1"), ("(2 << 61)", "PBMT=2"), ("(3 << 61)", "PBMT=3"))
        if sv.name == "sv57"
        else (("(1 << 61)", "PBMT=1"), ("(1 << 62)", "PBMT=2"), ("(1 << 62) | (1 << 61)", "PBMT=3"))
    )
    top = sv.levels - 1
    chunk = begin_sv_test(
        test_data,
        regs,
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
                *emit_access(test_data, sv, regs, top, "rwx", f"test{number}", "va_data", "Smode"),
                "",
            ]
        )
    chunk.code.append("#endif")
    chunk.raw_data.extend(sv_data(sv, regs, (top,)))
    chunk.trap_sigupd_count = trap_sigupd_count(3 * 3)
    test_chunks.append(end_sv_test(test_data, regs))


_NAPOT_VA = {"sv39": "0x140860000", "sv48": "0x028500430000", "sv57": "0x07028500430000"}


def _t_svnapot_not_supported(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    if sv.name == "sv32":
        return
    napot_bit = "PTE_N" if sv.name == "sv39" else "(1 << 63)"
    permissions = PteFlags(extra=(napot_bit, "(1 << 13)"))
    regs = SvRegs.allocate(test_data)
    chunk = begin_sv_test(
        test_data,
        regs,
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
                regs,
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
    chunk.raw_data.extend(sv_data(sv, regs, (0,), data_align=16))
    chunk.trap_sigupd_count = trap_sigupd_count(3)
    test_chunks.append(end_sv_test(test_data, regs))


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
    regs: SvRegs,
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
                    *emit_access(test_data, sv, regs, level, style, f"test{number}", "va_data", mode),
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
            regs = SvRegs.allocate(test_data)
            chunk = begin_sv_test(test_data, regs, sv, mode, f"{sv.name}_{topic}_{mode}")
            faults = _add_page_permission_matrix(
                test_data,
                chunk,
                sv,
                regs,
                mode,
                user_page=user_page,
                fault_counts=faults_for,
            )
            chunk.raw_data.extend(sv_data(sv, regs))
            chunk.trap_sigupd_count = trap_sigupd_count(faults)
            test_chunks.append(end_sv_test(test_data, regs))
    else:
        regs = SvRegs.allocate(test_data)
        chunk = begin_sv_test(test_data, regs, sv, "Umode", f"{sv.name}_spage_access_Umode")
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
                    *emit_access(test_data, sv, regs, level, "rwx", f"test{number}", "va_data", "Umode"),
                    "",
                ]
            )
        chunk.raw_data.extend(sv_data(sv, regs))
        chunk.trap_sigupd_count = trap_sigupd_count(sv.levels * 3)
        test_chunks.append(end_sv_test(test_data, regs))

    sum_set_faults = {"RWX": 1, "X-only": 3, "RX": 2, "RW": 1, "R-only": 2}
    for topic, faults_for, style in (
        ("upage_mstatus_sum_set", sum_set_faults, "sum"),
        ("upage_mstatus_sum_unset", 3, "rwx"),
    ):
        regs = SvRegs.allocate(test_data)
        chunk = begin_sv_test(test_data, regs, sv, "Smode", f"{sv.name}_{topic}_Smode")
        faults = _add_page_permission_matrix(
            test_data,
            chunk,
            sv,
            regs,
            "Smode",
            user_page=True,
            fault_counts=faults_for,
            style=style,
        )
        chunk.raw_data.extend(sv_data(sv, regs))
        chunk.trap_sigupd_count = trap_sigupd_count(faults)
        test_chunks.append(end_sv_test(test_data, regs))

    regs = SvRegs.allocate(test_data)
    chunk = begin_sv_test(test_data, regs, sv, "Smode", f"{sv.name}_spage_mstatus_sum_set_Smode")
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
                    *emit_access(test_data, sv, regs, level, "sum", f"test{number}", "va_data", "Smode"),
                    "",
                ]
            )
    chunk.raw_data.extend(sv_data(sv, regs))
    chunk.trap_sigupd_count = trap_sigupd_count(faults)
    test_chunks.append(end_sv_test(test_data, regs))


def _add_va_extreme_test(
    test_data: TestData,
    chunk: TestChunk,
    sv: SvMode,
    regs: SvRegs,
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
            *emit_access(test_data, sv, regs, 0, style, f"test{number}", va, "Smode"),
            "",
        ]
    )


def _t_va_all(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    all_ones = "0x" + "f" * (sv.xlen // 4)
    all_ones_code = all_ones[:-1] + "c"
    all_zeros = "0x" + "0" * (sv.xlen // 4)
    sig_init = "0x800" if sv.xlen == 32 else "0x12"

    regs = SvRegs.allocate(test_data)
    chunk = begin_sv_test(
        test_data,
        regs,
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
        regs,
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
        regs,
        number=2,
        va="va_data_x",
        physical_label="rvtest_data_1_l0_x",
        permissions=PteFlags(read=False, write=False),
        style="x_only",
    )
    chunk.raw_data.extend(sv_data(sv, regs, (0,), data_region_body=VA_ONES_DATA))
    chunk.trap_sigupd_count = 10
    test_chunks.append(end_sv_test(test_data, regs))

    regs = SvRegs.allocate(test_data)
    chunk = begin_sv_test(
        test_data,
        regs,
        sv,
        "Smode",
        f"{sv.name}_VA_all_zeros_Smode",
        sig_init=sig_init,
        va_defs=(("va_data", all_zeros),),
    )
    if sv.levels > 3:
        chunk.code.extend(keep_image_mapped(sv, regs))
    _add_va_extreme_test(
        test_data,
        chunk,
        sv,
        regs,
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
        regs,
        number=2,
        va="va_data",
        physical_label="rvtest_data_1_l0_x",
        permissions=PteFlags(read=False, write=False),
        style="x_only",
    )
    chunk.raw_data.extend(sv_data(sv, regs, (0,), data_region_body=VA_ZEROS_DATA))
    chunk.trap_sigupd_count = 10
    test_chunks.append(end_sv_test(test_data, regs))


def satp_csr_read(test_data: TestData, name: str, check_reg: int, csr: str = "satp") -> list[str]:
    label = test_data.add_testcase(name, "cp_satp_access", f"{test_data.testsuite}_cg")
    return [label, gen_csr_read_sigupd(check_reg, (csr, None), test_data)]


SATP_FIELDS = {
    "sv32": (31, "0x1FF", 22, 9),
    "sv39": (60, "0xFFFF", 44, 16),
    "sv48": (60, "0xFFFF", 44, 16),
    "sv57": (60, "0xFFFF", 44, 16),
}


def satp_access_ops(test_data: TestData, mode: str, sources: tuple[int, int, int], check_reg: int) -> list[str]:
    """csrw, csrs and csrc satp from the ``sources`` registers, reading satp back after each."""
    lines = []
    for operation, source in zip(("csrw", "csrs", "csrc"), sources, strict=True):
        lines.append(f"{operation} satp, x{source}")
        lines.extend(satp_csr_read(test_data, f"{mode[0].lower()}_{operation}", check_reg))
    return lines


def satp_mode_value(sv: SvMode, reg: int, scratch: int, *, root: bool) -> list[str]:
    """Load ``reg`` with satp.MODE = ``sv``, and satp.PPN = the S-mode root table if ``root``, else 0.

    ``scratch`` is clobbered when ``root`` is set.

    satp_access tests never write MODE = Bare with a nonzero PPN or ASID: that is UNSPECIFIED
    [norm:satp_mode_bare_nonzero_unspec].
    """
    shift = SATP_FIELDS[sv.name][0]
    if not root:
        return [f"LI(x{reg}, SATP_MODE_{sv.suffix} << {shift})"]
    return [
        f"LA(x{reg}, rvtest_Sroot_pg_tbl)",
        f"srli x{reg}, x{reg}, 12",
        f"LI(x{scratch}, SATP_MODE_{sv.suffix} << {shift})",
        f"or x{reg}, x{reg}, x{scratch}",
    ]


def _t_satp_access(test_data: TestData, test_chunks: list[TestChunk], sv: SvMode) -> None:
    _, asid_ones, asid_shift, asid_bits = SATP_FIELDS[sv.name]
    satp_reg, base_reg, bit_reg, check_reg = test_data.int_regs.get_registers(4, exclude_regs=[0])
    satp, base, bit_value = f"x{satp_reg}", f"x{base_reg}", f"x{bit_reg}"
    chunk = test_data.begin_test_chunk(f"{sv.name}_satp_access_Smode")
    chunk.section_header = comment_banner("cp_satp_access")
    chunk.code.append("csrw scause, zero")
    if sv.name in ("sv32", "sv39"):
        # Write MODE = sv with the identity-mapped root table so S-mode keeps running, then set and
        # clear the lowest ASID bit; return to Bare with all-zero satp before the U-mode accesses.
        chunk.code.extend(satp_mode_value(sv, base_reg, satp_reg, root=True))
        chunk.code.append(f"LI({bit_value}, 1 << {asid_shift})")
        chunk.code.extend(satp_access_ops(test_data, "Smode", (base_reg, bit_reg, bit_reg), check_reg))
        chunk.code.extend(
            [
                "csrw satp, zero",
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
            *satp_mode_value(sv, base_reg, satp_reg, root=True),
            f"csrw satp, {base}",
        ]
    )
    chunk.code.extend(satp_csr_read(test_data, f"mode_{sv.name}", check_reg))
    chunk.code.extend([f"mv {satp}, {base}", f"csrw satp, {satp}"])
    chunk.code.extend(satp_csr_read(test_data, "asid_zeros", check_reg))
    chunk.code.extend(
        [
            f"LI({satp}, {asid_ones})",
            f"slli {satp}, {satp}, {asid_shift}",
            f"or {satp}, {base}, {satp}",
            f"csrw satp, {satp}",
        ]
    )
    chunk.code.extend(satp_csr_read(test_data, "asid_ones", check_reg))
    for bit in range(asid_bits):
        chunk.code.extend(
            [
                f"li {bit_value}, 1",
                f"slli {bit_value}, {bit_value}, {asid_shift + bit}",
                f"or {satp}, {base}, {bit_value}",
                f"csrw satp, {satp}",
            ]
        )
        chunk.code.extend(satp_csr_read(test_data, f"asid_walk_{bit}", check_reg))
    chunk.trap_sigupd_count = 30 if sv.name in ("sv32", "sv39") else 10
    test_data.int_regs.return_registers([satp_reg, base_reg, bit_reg, check_reg])
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
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_sv32(test_data: TestData) -> list[TestChunk]:
    return _make_sv(test_data, SV32)


@add_priv_test_generator(
    "Sv",
    required_extensions=["Sv39"],
    march_extensions=[],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_sv39(test_data: TestData) -> list[TestChunk]:
    return _make_sv(test_data, SV39)


@add_priv_test_generator(
    "Sv",
    required_extensions=["Sv48"],
    march_extensions=[],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_sv48(test_data: TestData) -> list[TestChunk]:
    return _make_sv(test_data, SV48)


@add_priv_test_generator(
    "Sv",
    required_extensions=["Sv57"],
    march_extensions=[],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_sv57(test_data: TestData) -> list[TestChunk]:
    return _make_sv(test_data, SV57)
