##################################
# priv/extensions/sv/SvpbmtH.py
#
# Svpbmt H group: PBMT in the VS-stage and G-stage (RV64).
# David_Harris@hmc.edu 24 September 2026
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate Svpbmt two-stage address translation tests.

henvcfg.PBMTE enables PBMT in the VS-stage and menvcfg.PBMTE in the G-stage.  henvcfg.PBMTE is read-only zero
while menvcfg.PBMTE = 0.  Svpbmt exists only on RV64.
"""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.sv.page_tables import (
    SV39X4,
    SV48X4,
    SV57X4,
    VS_SV39,
    VS_SV48,
    VS_SV57,
    PteFlags,
    SvMode,
)
from testgen.priv.extensions.sv.SvH import (
    BOOT,
    SV39_PARAMS,
    begin_chunk,
    guest_access,
    guest_chunk_setup,
    guest_chunk_teardown,
    henvcfg_bits,
    henvcfg_gate,
    map_test_page,
    menvcfg_bits,
)
from testgen.priv.extensions.sv.Svpbmt import PBMT_ENCODINGS
from testgen.priv.registry import add_priv_test_generator

CG = "Svpbmt_H_cg"


def svpbmt_flush(reg: int) -> list[str]:
    """Separate accesses to svh_page with different cacheability attributes (Svpbmt).

    fence iorw, iorw; cbo.flush; fence iorw, iorw prevents loss of coherence and of memory ordering. Without
    Zicbom there is no cbo.flush, and only the fence is emitted.
    """
    return [
        "fence iorw, iorw",
        "#ifdef ZICBOM_SUPPORTED",
        f"LA(x{reg}, svh_page)",
        ".option push",
        ".option arch, +zicbom",
        f"cbo.flush (x{reg})",
        ".option pop",
        "fence iorw, iorw",
        "#endif",
    ]


def pbmt_block(lines: list[str], reg: int) -> list[str]:
    """Wrap the PBMT testcases: enable cbo.flush in HS-mode, and flush svh_page before and after them."""
    return [
        "#ifdef ZICBOM_SUPPORTED",
        "RVTEST_TSBI_CSR_SET(CSR_MENVCFG, MENVCFG_CBCFE)",
        "#endif",
        *lines,
        *svpbmt_flush(reg),
        "#ifdef ZICBOM_SUPPORTED",
        "RVTEST_TSBI_CSR_CLEAR(CSR_MENVCFG, MENVCFG_CBCFE)",
        "#endif",
    ]


def _vs_chunk(test_data: TestData, vs: SvMode, henvcfg: bool) -> TestChunk:
    """VS-stage PBMT with henvcfg.PBMTE = 0, 1, and with ``henvcfg``, henvcfg.PBMTE itself."""
    chunk = begin_chunk(
        test_data,
        f"H_{vs.name}_vs_pbmt",
        "cp_henvcfg_menvcfg, cp_vsatp_pbmt" if henvcfg else "cp_vsatp_pbmt",
        "In VS-mode with hgatp = Bare and menvcfg.PBMTE = 1, store, load and fetch through VS-stage leaves with\n"
        "PBMT = 1-3, with henvcfg.PBMTE = 0 (page fault) and 1"
        + (
            "\nIn HS-mode, set henvcfg.PBMTE with menvcfg.PBMTE = 0, where it is read-only zero, and 1"
            if henvcfg
            else ""
        ),
        stages=(vs,),
    )
    va = vs.data_va
    reg = test_data.int_regs.get_register()
    code = henvcfg_gate(test_data, 64, "PBMTE", CG) if henvcfg else []
    code.extend([*guest_chunk_setup(test_data, None, vs, "VS"), *menvcfg_bits(64, adue=0, pbmte=1)])
    pbmt_cases: list[str] = []
    for pbmte in (0, 1):
        for pbmt, (pbmt_bits, _, _) in enumerate(PBMT_ENCODINGS, start=1):
            setup = [
                *svpbmt_flush(reg),
                *henvcfg_bits(64, reg, adue=0, pbmte=pbmte),
                *map_test_page(test_data, None, vs, vs_flags=PteFlags(extra=(pbmt_bits,))),
            ]
            name = f"pbmte{pbmte}_pbmt{pbmt}"
            pbmt_cases.extend(guest_access(test_data, CG, "cp_vsatp_pbmt", name, "VS", va, setup=setup))
    code.extend(pbmt_block(pbmt_cases, reg))
    test_data.int_regs.return_register(reg)
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, 64)])
    return test_data.end_test_chunk()


def _g_chunk(test_data: TestData, g: SvMode) -> TestChunk:
    """G-stage PBMT with menvcfg.PBMTE = 0, 1."""
    chunk = begin_chunk(
        test_data,
        f"H_{g.name}_g_pbmt",
        "cp_hgatp_pbmt",
        "In VS-mode with vsatp = Bare, store, load and fetch through G-stage leaves with PBMT = 1-3, with\n"
        "menvcfg.PBMTE = 0 (guest-page fault) and 1",
        stages=(g,),
    )
    va = g.data_va
    reg = test_data.int_regs.get_register()
    code = guest_chunk_setup(test_data, g, None, "VS")
    pbmt_cases: list[str] = []
    for pbmte in (0, 1):
        for pbmt, (pbmt_bits, _, _) in enumerate(PBMT_ENCODINGS, start=1):
            setup = [
                *svpbmt_flush(reg),
                *menvcfg_bits(64, adue=0, pbmte=pbmte),
                *map_test_page(test_data, g, None, g_flags=PteFlags(user=True, extra=(pbmt_bits,))),
            ]
            name = f"pbmte{pbmte}_pbmt{pbmt}"
            pbmt_cases.extend(guest_access(test_data, CG, "cp_hgatp_pbmt", name, "VS", va, setup=setup))
    code.extend(pbmt_block(pbmt_cases, reg))
    test_data.int_regs.return_register(reg)
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, 64)])
    return test_data.end_test_chunk()


@add_priv_test_generator("Svpbmt", required_extensions=["H", "Svpbmt"], extra_defines=BOOT, params=SV39_PARAMS)
def make_svpbmt_h_sv39(test_data: TestData) -> list[TestChunk]:
    return [_vs_chunk(test_data, VS_SV39, True), _g_chunk(test_data, SV39X4)]


@add_priv_test_generator(
    "Svpbmt", required_extensions=["H", "Svpbmt"], extra_defines=BOOT, params=["SV48_VSMODE_TRANSLATION: true"]
)
def make_svpbmt_h_vs_sv48(test_data: TestData) -> list[TestChunk]:
    return [_vs_chunk(test_data, VS_SV48, False)]


@add_priv_test_generator(
    "Svpbmt", required_extensions=["H", "Svpbmt"], extra_defines=BOOT, params=["SV48X4_TRANSLATION: true"]
)
def make_svpbmt_h_g_sv48x4(test_data: TestData) -> list[TestChunk]:
    return [_g_chunk(test_data, SV48X4)]


@add_priv_test_generator(
    "Svpbmt", required_extensions=["H", "Svpbmt"], extra_defines=BOOT, params=["SV57_VSMODE_TRANSLATION: true"]
)
def make_svpbmt_h_vs_sv57(test_data: TestData) -> list[TestChunk]:
    return [_vs_chunk(test_data, VS_SV57, False)]


@add_priv_test_generator(
    "Svpbmt", required_extensions=["H", "Svpbmt"], extra_defines=BOOT, params=["SV57X4_TRANSLATION: true"]
)
def make_svpbmt_h_g_sv57x4(test_data: TestData) -> list[TestChunk]:
    return [_g_chunk(test_data, SV57X4)]
