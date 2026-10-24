##################################
# priv/extensions/sv/generate.py
#
# Shared Sv assembly generation.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared assembly generation for Sv tests."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.sv.assembly import DATA_REGION
from testgen.priv.extensions.sv.page_tables import (
    PTE_SETUP_ADDR_REG,
    SV32X4,
    SV39X4,
    VS_SV32,
    VS_SV39,
    PteFlags,
    SvMode,
    create_page_mapping,
    write_pte,
)

# G-stage and VS-stage modes of the hypervisor two-stage tests on each XLEN (not used by the S-level Sv tests)
TWO_STAGE_MODES = ((64, SV39X4, VS_SV39), (32, SV32X4, VS_SV32))


def per_xlen(build: Callable[[SvMode, SvMode], list[str]]) -> list[str]:
    """The lines ``build(g, vs)`` emits for each XLEN's G-stage and VS-stage modes, under ``#if __riscv_xlen``."""
    lines = []
    for xlen, g, vs in TWO_STAGE_MODES:
        lines.extend(["#if __riscv_xlen == 64" if xlen == 64 else "#else", *build(g, vs)])
    return [*lines, "#endif"]


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


def set_atp(mode: SvMode, reg: int, tmp: int) -> list[str]:
    """Write ``mode``'s MODE and root table to its CSR (satp, vsatp or hgatp), using two scratch registers."""
    return [
        f"LI(x{reg}, {mode.atp_mode:#x})",
        f"LA(x{tmp}, {mode.page_table_label(mode.levels - 1)})",
        f"srli x{tmp}, x{tmp}, 12",
        f"or x{tmp}, x{tmp}, x{reg}",
        f"csrw {mode.atp_csr}, x{tmp}",
    ]


def guest_translation_setup(test_data: TestData, g: SvMode | None, vs: SvMode | None, priv_mode: str) -> list[str]:
    """Identity map the test image in both stages, map the guest code alias, register it in the V save area, and
    turn on hgatp and vsatp.  A None stage stays Bare.  The alias is user accessible when ``priv_mode`` is "VUmode".
    """
    alias = vs or g
    if alias is None:
        raise ValueError("A guest code alias needs a VS-stage or G-stage translation mode")
    reg, tmp, spare = test_data.int_regs.get_registers(3)
    regs = (reg, tmp, spare)
    shift = alias.page_offset_bits(alias.levels - 1)
    lines = ["// Identity map the test image in both stages"]
    for label in ("rvtest_code_begin", "rvtest_data_begin", "rvtest_sig_end"):
        for mode, flags in ((g, PteFlags(user=True)), (vs, PteFlags())):
            if mode is not None:
                lines.extend(
                    write_pte(
                        mode,
                        level=mode.levels - 1,
                        flags=flags,
                        virtual_address=label,
                        physical_address=label,
                        regs=regs,
                        va_is_label=True,
                        superpage=True,
                    )
                )
    lines.append("// Map the code region again at the guest alias")
    if g is not None:
        lines.extend(
            write_pte(
                g,
                level=g.levels - 1,
                flags=PteFlags(user=True),
                virtual_address=g.code_va,
                physical_address="rvtest_code_begin",
                regs=regs,
                superpage=True,
            )
        )
    if vs is not None:
        lines.extend(
            write_pte(
                vs,
                level=vs.levels - 1,
                flags=PteFlags(user=priv_mode == "VUmode"),
                virtual_address=vs.code_va,
                physical_address="rvtest_code_begin" if g is None else g.code_va,
                regs=regs,
                pa_is_label=g is None,
                superpage=True,
            )
        )
    lines.extend(
        [
            "// Register the alias of rvtest_code_begin",
            f"LI(x{reg}, (({alias.code_va}) >> {shift}) << {shift})",
            f"LA(x{tmp}, rvtest_code_begin)",
            f"slli x{tmp}, x{tmp}, {alias.xlen - shift}",
            f"srli x{tmp}, x{tmp}, {alias.xlen - shift}",
            f"or x{reg}, x{reg}, x{tmp}",
            f"LA(x{tmp}, Vtramptbl_sv)",
            f"SREG x{reg}, code_bgn_off(x{tmp})",
            "",
        ]
    )
    lines.extend(["csrw hgatp, zero"] if g is None else set_atp(g, reg, tmp))
    lines.extend(["csrw vsatp, zero"] if vs is None else set_atp(vs, reg, tmp))
    lines.extend(["hfence.gvma", "hfence.vvma"])
    test_data.int_regs.return_registers(list(regs))
    return lines


def guest_translation_teardown(test_data: TestData) -> list[str]:
    """Turn guest translation off and unregister the guest code alias."""
    reg, tmp = test_data.int_regs.get_registers(2)
    lines = [
        "csrw vsatp, zero",
        "csrw hgatp, zero",
        "hfence.gvma",
        "hfence.vvma",
        f"LA(x{reg}, rvtest_code_begin)",
        f"LA(x{tmp}, Vtramptbl_sv)",
        f"SREG x{reg}, code_bgn_off(x{tmp})",
    ]
    test_data.int_regs.return_registers([reg, tmp])
    return lines


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
    # Order the stores before the walks that reach them once the test rewrites the root entry.
    lines.append("sfence.vma")
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
