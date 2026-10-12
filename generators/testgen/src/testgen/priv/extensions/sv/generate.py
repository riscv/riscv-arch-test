##################################
# priv/extensions/sv/generate.py
#
# Shared Sv assembly generation.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared assembly generation for Sv tests."""

from collections.abc import Iterable
from dataclasses import dataclass

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.sv.assembly import DATA_REGION
from testgen.priv.extensions.sv.page_tables import PTE_SETUP_ADDR_REG, PteFlags, SvMode, create_page_mapping


@dataclass(frozen=True)
class SvRegs:
    """Registers allocated for one Sv test chunk.

    ``value`` is the running store value; it is live for the whole chunk and the data-region routines read it.
    ``addr`` holds the address under test, ``load`` receives loads, and ``result`` is written by the
    data-region routines and by sc. ``scratch`` is a short-lived temporary.

    The PTE_SETUP_* and SAVE_AREA_SETUP macros and pmp.set_pmpaddr clobber t1 (x6), so only ``scratch`` may
    be x6 and it must never be live across one of them.

    The return address stays in ra (x1), which priv.py reserves for it: on a fetch fault the trap handler
    resumes at ra (``csrw CSR_XEPC, ra`` in rvtest_trap_handler.h), so every ``jalr`` that may fetch from a
    test page must link through x1, and the data-region routines return with ``jr ra``.
    """

    value: int
    addr: int
    load: int
    result: int
    scratch: int

    @classmethod
    def allocate(cls, test_data: TestData) -> "SvRegs":
        value, addr, load, result = test_data.int_regs.get_registers(4, exclude_regs=[0, PTE_SETUP_ADDR_REG])
        return cls(value, addr, load, result, test_data.int_regs.get_register(exclude_regs=[0]))

    def release(self, test_data: TestData) -> None:
        test_data.int_regs.return_registers([self.value, self.addr, self.load, self.result, self.scratch])


def data_region(regs: SvRegs, body: str = DATA_REGION) -> list[str]:
    """Return a data-region template with the chunk's registers filled in."""
    return body.strip("\n").format(value=f"x{regs.value}", result=f"x{regs.result}").splitlines()


def begin_sv_test(
    test_data: TestData,
    regs: SvRegs,
    sv: SvMode,
    priv_mode: str,
    split_name: str,
    *,
    coverpoint: str | None = None,
    code_prefix: Iterable[str] = (),
    sig_init: str | None = "0x800",
    va_defs: tuple[tuple[str, str], ...] | None = None,
    va_code_override: str | None = None,
    pre_va_asm: tuple[str, ...] = (),
    setup_asm: tuple[str, ...] = (),
) -> TestChunk:
    """Start an Sv test chunk and emit its banner and common prologue.

    ``sig_init`` is the initial running store value, loaded into ``regs.value``; None leaves it unset.
    """
    chunk = test_data.begin_test_chunk(split_name)
    chunk.section_header = comment_banner(coverpoint or f"cp_{split_name}")
    chunk.code.extend(code_prefix)
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
            "// SAVE_AREA_SETUP takes the M-mode save area in a0 and clobbers t0 and t1.",
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
        chunk.code.extend(["", f"LI(x{regs.value}, {sig_init}) // Test signature initialization"])
    chunk.code.append("")
    return chunk


def end_sv_test(test_data: TestData, regs: SvRegs) -> TestChunk:
    """Return the chunk's registers and end it."""
    regs.release(test_data)
    return test_data.end_test_chunk()


def keep_image_mapped(sv: SvMode, regs: SvRegs) -> list[str]:
    """Map the test image as a gigapage below the root.

    On Sv48/Sv57 the boot identity map is root PTE 0, so a test VA in the same
    root slot (VA 0) would unmap the running code without this path.
    """
    if sv.levels <= 3:
        return []
    pte, index, entry = (f"x{reg}" for reg in (regs.addr, regs.load, regs.scratch))
    index_mask = "0x3FF" if sv.xlen == 32 else "0x1FF"
    lines = ["// Keep the identity-mapped test image reachable through the level 2 table."]
    for level in range(sv.levels - 2, 1, -1):
        shift = sv.page_offset_bits(level)
        lines.extend(
            [
                f"LA({pte}, rvtest_code_begin)",
                f"srli {index}, {pte}, {shift}",
                f"andi {index}, {index}, {index_mask}",
                f"slli {index}, {index}, {2 if sv.xlen == 32 else 3}",
                f"LA({entry}, rvtest_slvl{level}_pg_tbl)",
                f"add {entry}, {entry}, {index}",
            ]
        )
        if level > 2:
            lines.extend(
                [
                    f"LA({pte}, rvtest_slvl{level - 1}_pg_tbl)",
                    f"srli {pte}, {pte}, 12",
                    f"slli {pte}, {pte}, 10",
                    f"ori {pte}, {pte}, PTE_V",
                ]
            )
        else:
            lines.extend(
                [
                    f"srli {pte}, {pte}, {shift}",
                    f"slli {pte}, {pte}, {shift - 2}",
                    f"ori {pte}, {pte}, PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V",
                ]
            )
        lines.append(f"SREG {pte}, 0({entry})")
    return lines


def sv_data(
    sv: SvMode,
    regs: SvRegs,
    levels: Iterable[int] | None = None,
    *,
    data_align: int = 12,
    data_region_body: str | None = None,
    page_table_align: int | str = 12,
) -> list[str]:
    """Emit the physical test region, with the chunk's registers in its routines, and Sv page tables."""
    unique_levels = sorted(set(sv.levels_desc if levels is None else levels))
    lines = ["// Physical address region for testing"]
    if unique_levels:
        level_text = (
            str(unique_levels[0])
            if len(unique_levels) == 1
            else f"{', '.join(map(str, unique_levels[:-1]))} and {unique_levels[-1]}"
        )
        lines.append(f"// Physical address region for levels {level_text}")
    region = DATA_REGION if data_region_body is None else data_region_body
    if data_align != 12:
        region = region.replace(".p2align 12", f".p2align {data_align}", 1)
    lines.extend(data_region(regs, region))
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
