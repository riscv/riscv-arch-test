##################################
# priv/extensions/sv/SvnapotH.py
#
# Svnapot H group: 64 KiB NAPOT translation in the VS-stage and G-stage (RV64).
# David_Harris@hmc.edu 24 September 2026
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate Svnapot two-stage address translation tests."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.sv.page_tables import (
    SV39X4,
    VS_SV39,
    PteFlags,
    SvMode,
    create_page_mapping,
    create_page_walk,
    write_pte,
)
from testgen.priv.extensions.sv.SvH import (
    BOOT,
    SV39_PARAMS,
    begin_chunk,
    guest_access,
    guest_chunk_setup,
    guest_chunk_teardown,
)
from testgen.priv.extensions.sv.Svnapot import NAPOT_64K_PPN, NAPOT_RESERVED_PPNS
from testgen.priv.registry import add_priv_test_generator

CG = "Svnapot_H_cg"

# A 64 KiB NAPOT region of 16 pages, each starting with ret and holding a distinct word at offset 8
NAPOT_PAGES = [
    ".p2align 16",
    "svh_napot:",
    *(
        line
        for page in range(16)
        for line in (".4byte 0x00008067    # ret", ".4byte 0", f".4byte {0x5A5A0000 + page:#x}", ".skip 4096 - 12")
    ),
]


def _napot_leaves(
    test_data: TestData, mode: SvMode, base: int, target: str, flags: PteFlags, pa_is_label: bool
) -> list[str]:
    """The 16 kilopage leaves of a 64 KiB NAPOT mapping from ``base`` to ``target``."""
    pte, addr, tmp = test_data.int_regs.get_registers(3)
    regs = (pte, addr, tmp)
    lines = create_page_walk(mode, leaf_level=0, virtual_address=hex(base), regs=regs)
    for page in range(16):
        lines.extend(
            write_pte(
                mode,
                level=0,
                flags=flags,
                virtual_address=hex(base + page * 0x1000),
                physical_address=target,
                regs=regs,
                pa_is_label=pa_is_label,
            )
        )
    test_data.int_regs.return_registers(list(regs))
    return lines


NAPOT_BITS = ("PTE_N", NAPOT_64K_PPN)


def _t_napot(test_data: TestData, test_chunks: list[TestChunk], g: SvMode, vs: SvMode, mode: str) -> None:
    """64 KiB NAPOT translation in the VS-stage, the G-stage and both."""
    chunk = begin_chunk(
        test_data,
        f"H_{g.name}_napot_{mode.lower()}",
        "cp_vsatp_napot, cp_hgatp_napot, cp_twostage_napot",
        f"In {mode}-mode, store, load and fetch in pages 0, 2 and 15 of a 64 KiB NAPOT mapping in the VS-stage\n"
        "(hgatp = Bare), in the G-stage (vsatp = Bare) and in both stages",
    )
    chunk.raw_data.extend(NAPOT_PAGES)
    user = mode == "VU"
    vs_base = int(vs.data_va, 16) & ~0xFFFF
    g_base = int(g.data_va, 16) & ~0xFFFF
    code = []
    for vs_stage, g_stage, name in ((vs, None, "vsatp_napot"), (None, g, "hgatp_napot"), (vs, g, "twostage_napot")):
        code.extend(guest_chunk_setup(test_data, g_stage, vs_stage, mode))
        if vs_stage is not None:
            target = "svh_napot" if g_stage is None else hex(g_base)
            flags = PteFlags(user=user, extra=NAPOT_BITS)
            code.extend(_napot_leaves(test_data, vs, vs_base, target, flags, g_stage is None))
        if g_stage is not None:
            code.extend(_napot_leaves(test_data, g, g_base, "svh_napot", PteFlags(user=True, extra=NAPOT_BITS), True))
        code.extend(["hfence.vvma", "hfence.gvma"])
        base = g_base if vs_stage is None else vs_base
        for page in (0, 2, 15):
            va = hex(base + page * 0x1000)
            code.extend(guest_access(test_data, CG, f"cp_{name}", f"{name}_page{page}", mode, va))
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, g.xlen)])
    test_chunks.append(test_data.end_test_chunk())


def _t_napot_reserved(test_data: TestData, test_chunks: list[TestChunk], g: SvMode, vs: SvMode) -> None:
    """Reserved NAPOT encodings fault in either stage: N on a superpage, or PPN[3:0] other than 1000."""
    chunk = begin_chunk(
        test_data,
        f"H_{g.name}_napot_reserved",
        "cp_vsatp_napot, cp_hgatp_napot",
        "In VS-mode, access through a VS-stage (hgatp = Bare) and a G-stage (vsatp = Bare) leaf with N set on a\n"
        "superpage, or with N set and PPN[3:0] = 0000, 0001, 0010 or 0100",
    )
    chunk.raw_data.extend(NAPOT_PAGES)
    code = []
    for stage, coverpoint in ((vs, "cp_vsatp_napot"), (g, "cp_hgatp_napot")):
        g_stage, vs_stage = (None, vs) if stage is vs else (g, None)
        code.extend(guest_chunk_setup(test_data, g_stage, vs_stage, "VS"))
        user = stage is g
        # A superpage leaf maps svh_page; a kilopage leaf maps svh_napot, whose PPN[3:0] = 0000
        cases = [
            *(
                (f"{stage.name}_superpage_lvl{level}", level, PteFlags(user=user, extra=("PTE_N",)), "svh_page")
                for level in range(1, stage.levels)
            ),
            *(
                (f"{stage.name}_ppn{ppn}", 0, PteFlags(user=user, extra=("PTE_N", f"({ppn} << 10)")), "svh_napot")
                for ppn in NAPOT_RESERVED_PPNS
            ),
        ]
        for name, level, flags, target in cases:
            pte, addr, tmp = test_data.int_regs.get_registers(3)
            setup = [
                *create_page_mapping(
                    stage,
                    leaf_level=level,
                    leaf_flags=flags,
                    virtual_address=stage.data_va,
                    physical_address=target,
                    regs=(pte, addr, tmp),
                ),
                "hfence.vvma",
                "hfence.gvma",
            ]
            test_data.int_regs.return_registers([pte, addr, tmp])
            code.extend(
                guest_access(test_data, CG, coverpoint, name, "VS", stage.data_va, setup=setup, sv=stage, level=level)
            )
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, g.xlen)])
    test_chunks.append(test_data.end_test_chunk())


@add_priv_test_generator("Svnapot", required_extensions=["H", "Svnapot"], extra_defines=BOOT, params=SV39_PARAMS)
def make_svnapot_h_sv39(test_data: TestData) -> list[TestChunk]:
    test_chunks: list[TestChunk] = []
    for mode in ("VS", "VU"):
        _t_napot(test_data, test_chunks, SV39X4, VS_SV39, mode)
    _t_napot_reserved(test_data, test_chunks, SV39X4, VS_SV39)
    return test_chunks
