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
    if sig_init:
        chunk.code.append(sig_init)
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
            "// Set up the code-region save area.",
            "csrr a0, mscratch",
            f"SAVE_AREA_SETUP(va_rvtest_code_begin, rvtest_code_begin, code, LEVEL{top})",
            "",
            f"{sv.satp_setup} // Enable address translation.",
            "sfence.vma",
        ]
    )
    if setup_asm:
        chunk.code.extend(["", *setup_asm])
    chunk.code.append("")
    return chunk


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
