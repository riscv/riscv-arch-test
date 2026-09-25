##################################
# priv/extensions/sv/generate.py
#
# Shared Sv assembly generation.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared assembly generation for Sv tests."""

from collections.abc import Iterable

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.sv.assembly import DATA_REGION
from testgen.priv.extensions.sv.page_tables import PteFlags, SvMode, create_page_mapping


def begin_sv_test(
    test_data: TestData,
    sv: SvMode,
    priv_mode: str,
    split_name: str,
    *,
    coverpoint: str | None = None,
    code_prefix: Iterable[str] = (),
    sig_init: str = "LI(a2, 0x800) // Test signature initialization",
    va_defs: tuple[tuple[str, str], ...] | None = None,
    va_code_override: str | None = None,
    pre_va_asm: tuple[str, ...] = (),
    setup_asm: tuple[str, ...] = (),
) -> TestChunk:
    """Start an Sv test chunk and emit its banner and common prologue."""
    chunk = test_data.begin_test_chunk(split_name)
    chunk.section_header = comment_banner(coverpoint or f"cp_{split_name}")
    chunk.code.extend([*code_prefix, "", "main:"])
    if pre_va_asm:
        chunk.code.extend(["", *pre_va_asm])

    top = sv.levels - 1
    address_defs = va_defs if va_defs is not None else (("va_data", sv.data_va),)
    chunk.code.extend(
        [
            "",
            "// Virtual addresses for code and test regions",
            "",
            "// Virtual address of rvtest_data_1",
            *(f".set {name}, {value}" for name, value in address_defs),
            "",
            "// Virtual address of the code region",
            f".set va_rvtest_code_begin, {va_code_override or sv.code_va}",
            "",
            "// Map the code region.",
            *create_page_mapping(
                sv,
                virtual_address="va_rvtest_code_begin",
                physical_address="rvtest_code_begin",
                leaf_level=top,
                leaf_flags=PteFlags(user=priv_mode == "Umode", write=False),
            ),
            "sfence.vma",
            "",
            "// The boot tables identity map the test image, but that mapping is not user",
            "// accessible, so the code is mapped again at va_rvtest_code_begin. Registering",
            "// that alias lets RVTEST_TSBI_GOTO_* resume in the mapping the mode it switches",
            "// to can fetch from.",
            "LA(a0, Mtramptbl_sv)",
            f"SAVE_AREA_SETUP(va_rvtest_code_begin, rvtest_code_begin, code, LEVEL{top})",
            "",
            f"{sv.satp_setup} // Enable address translation.",
            "sfence.vma",
        ]
    )
    if setup_asm:
        chunk.code.extend(["", *setup_asm])
    if sig_init:
        # After setup_asm, which may contain a tsbi_call; those marshal through a0-a2.
        chunk.code.extend(["", sig_init])
    chunk.code.append("")
    return chunk


def keep_image_mapped(sv: SvMode) -> list[str]:
    """Map the test image as a gigapage below the root.

    On Sv48/Sv57 the boot identity map is root PTE 0, so a test VA in the same
    root slot (VA 0) would unmap the running code without this path.
    """
    if sv.levels <= 3:
        return []
    index_mask = "0x3FF" if sv.xlen == 32 else "0x1FF"
    lines = ["// Keep the identity-mapped test image reachable through the level 2 table."]
    for level in range(sv.levels - 2, 1, -1):
        shift = sv.page_offset_bits(level)
        lines.extend(
            [
                "LA(t0, rvtest_code_begin)",
                f"srli t1, t0, {shift}",
                f"andi t1, t1, {index_mask}",
                f"slli t1, t1, {2 if sv.xlen == 32 else 3}",
                f"LA(a0, rvtest_slvl{level}_pg_tbl)",
                "add a0, a0, t1",
            ]
        )
        if level > 2:
            lines.extend(
                [f"LA(t0, rvtest_slvl{level - 1}_pg_tbl)", "srli t0, t0, 12", "slli t0, t0, 10", "ori t0, t0, PTE_V"]
            )
        else:
            lines.extend(
                [
                    f"srli t0, t0, {shift}",
                    f"slli t0, t0, {shift - 2}",
                    "ori t0, t0, PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V",
                ]
            )
        lines.append("SREG t0, 0(a0)")
    return lines


def sv_data(
    sv: SvMode,
    levels: Iterable[int] | None = None,
    *,
    data_align: int = 12,
    data_region_body: str | None = None,
    page_table_align: int | str = 12,
) -> list[str]:
    """Emit the physical test region and Sv page tables."""
    unique_levels = sorted(set(sv.levels_desc if levels is None else levels))
    lines = ["// Physical address region for testing"]
    if unique_levels:
        level_text = (
            str(unique_levels[0])
            if len(unique_levels) == 1
            else f"{', '.join(map(str, unique_levels[:-1]))} and {unique_levels[-1]}"
        )
        lines.append(f"// Physical address region for levels {level_text}")
    region = data_region_body if data_region_body is not None else DATA_REGION
    if data_align != 12:
        region = region.replace(".p2align 12", f".p2align {data_align}", 1)
    lines.extend(region.strip("\n").splitlines())
    lines.extend(["", "// Page tables"])
    for level in range(sv.levels - 1):
        if page_table_align != 12:
            # A page table must be page aligned; PMP tests also align it to the PMP grain
            lines.append(".p2align 12")
        lines.extend(
            [
                f".p2align {page_table_align}",
                f"rvtest_slvl{level}_pg_tbl:",
                ".skip(4096)",
            ]
        )
    if page_table_align != 12:
        lines.append(f".p2align {page_table_align}")
    return lines
