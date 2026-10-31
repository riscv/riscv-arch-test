##################################
# priv/extensions/sv/SvaduH.py
#
# Svadu H group: hardware A/D updates in the VS-stage and G-stage.
# David_Harris@hmc.edu 24 September 2026
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate Svadu two-stage address translation tests.

menvcfg.ADUE selects Svade or Svadu for the G-stage, and henvcfg.ADUE for the VS-stage.  henvcfg.ADUE is
read-only zero while menvcfg.ADUE = 0.  The cases with ADUE = 0 are also in the Sv suite; they are repeated here
so that each cross has every (menvcfg.ADUE, henvcfg.ADUE) pair.
"""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.sv.page_tables import (
    SV32X4,
    SV39X4,
    SV48X4,
    SV57X4,
    VS_SV32,
    VS_SV39,
    VS_SV48,
    VS_SV57,
    PteFlags,
    SvMode,
)
from testgen.priv.extensions.sv.SvH import (
    BOOT,
    CBO_OPS,
    G_LEAF,
    G_NO_AD,
    G_NO_D,
    GUEST_OPS,
    SV32_PARAMS,
    SV39_PARAMS,
    SV48_PARAMS,
    SV57_PARAMS,
    VS_NO_AD,
    HlvImplicitCase,
    ImplicitCase,
    begin_chunk,
    g_ad_accesses,
    guest_chunk_setup,
    guest_chunk_teardown,
    henvcfg_gate,
    hlv_implicit_accesses,
    implicit_accesses,
    perm_flags,
    set_csr_bits,
    vs_ad_accesses,
)
from testgen.priv.registry import add_priv_test_generator

CG = "Svadu_H_cg"

# VS-stage A/D cases: (menvcfg.ADUE, henvcfg.ADUE, leaf flags, accesses).  Svade faults on A = 0, and on D = 0 for a
# store; Svadu sets A on any access and D on a store.  The (0, 1) case writes henvcfg.ADUE, which stays zero.
AD_CASES = (
    (0, 1, PteFlags(accessed=False, dirty=False), GUEST_OPS),
    (1, 0, PteFlags(accessed=False, dirty=False), GUEST_OPS),
    (1, 0, PteFlags(dirty=False), GUEST_OPS),
    (1, 1, PteFlags(accessed=False, dirty=False), ("load", "exec")),
    (1, 1, PteFlags(dirty=False), ("store",)),
)
# G-stage A/D cases: (menvcfg.ADUE, leaf flags, accesses)
G_AD_CASES = (
    (0, G_NO_AD, GUEST_OPS),
    (0, G_NO_D, GUEST_OPS),
    (1, G_NO_AD, ("load", "exec")),
    (1, G_NO_D, ("store",)),
)
# Two-stage cases (see SvH.IMPLICIT_CASES).  With Svadu, a VS-stage A/D update is an implicit store, so the G-stage
# leaf of the VS-stage leaf table must be writable and gets D set; a read-only one raises a guest-page fault with
# the write pseudoinstruction in htinst.
IMPLICIT_CASES: tuple[ImplicitCase, ...] = (
    ("table_readonly", "cp_implicit_gpf", 1, 1, VS_NO_AD, perm_flags("r", True), G_LEAF, GUEST_OPS, ()),
    ("table_svadu", "cp_twostage_adue", 1, 0, PteFlags(), G_NO_AD, G_LEAF, ("load",), ("table",)),
    ("vs_svadu_load", "cp_twostage_adue", 1, 1, VS_NO_AD, G_NO_D, G_LEAF, ("load", "exec"), ("vs", "table")),
    ("vs_svadu_store", "cp_twostage_adue", 1, 1, PteFlags(dirty=False), G_NO_D, G_LEAF, ("store",), ("vs", "table")),
    ("vs_svade", "cp_twostage_adue", 1, 0, VS_NO_AD, G_LEAF, G_LEAF, GUEST_OPS, ()),
    ("vs_svade_dirty", "cp_twostage_adue", 1, 0, PteFlags(dirty=False), G_LEAF, G_LEAF, GUEST_OPS, ()),
    ("g_svade", "cp_twostage_adue", 0, 0, PteFlags(), G_LEAF, G_NO_AD, GUEST_OPS, ()),
    ("g_svade_dirty", "cp_twostage_adue", 0, 0, PteFlags(), G_LEAF, G_NO_D, GUEST_OPS, ()),
    ("g_svadu_load", "cp_twostage_adue", 1, 0, PteFlags(), G_LEAF, G_NO_AD, ("load", "exec"), ("page",)),
    ("g_svadu_store", "cp_twostage_adue", 1, 0, PteFlags(), G_LEAF, G_NO_D, ("store",), ("page",)),
)
HLV_IMPLICIT_CASES: tuple[HlvImplicitCase, ...] = (
    ("table_readonly", 1, 1, VS_NO_AD, perm_flags("r", True), ("hlv", "hlvx", "hsv")),
)


def _cbo_chunk(test_data: TestData, g: SvMode, vs: SvMode, family: str) -> TestChunk:
    """CBOs with ADUE = 1 through a VS-stage leaf (hgatp Bare) and a G-stage leaf (vsatp Bare) with A = D = 0.

    A CBO sets A in each stage.  cbo.zero also sets D, because it writes; a cache-block management instruction never
    checks or sets D (cmo.adoc).  Each leaf is read back.
    """
    ops = CBO_OPS[family]
    chunk = begin_chunk(
        test_data,
        f"H_{g.name}_{family}_adue",
        "cp_vsatp_adue_cbo, cp_hgatp_adue_cbo",
        f"In VS-mode with menvcfg.ADUE = henvcfg.ADUE = 1, execute {', '.join(op.replace('_', '.') for op in ops)}\n"
        "through a VS-stage leaf (hgatp = Bare) and a G-stage leaf (vsatp = Bare) with A = D = 0, and read each\n"
        f"leaf back: A is set{', and D too' if family == 'zicboz' else ', and D stays clear'}",
        stages=(g, vs),
    )
    reg = test_data.int_regs.get_register()
    code = [
        f"LI(x{reg}, HENVCFG_CBIE | HENVCFG_CBCFE | HENVCFG_CBZE)",
        f"csrs henvcfg, x{reg}",
        *guest_chunk_setup(test_data, None, vs, "VS"),
        *vs_ad_accesses(test_data, vs, ((1, 1, VS_NO_AD, ops),), CG, "cp_vsatp_adue_cbo"),
        *guest_chunk_teardown(test_data, vs.xlen),
        *guest_chunk_setup(test_data, g, None, "VS"),
        *g_ad_accesses(test_data, g, ((1, G_NO_AD, ops),), CG, "cp_hgatp_adue_cbo"),
        *guest_chunk_teardown(test_data, g.xlen),
        f"LI(x{reg}, HENVCFG_CBIE | HENVCFG_CBCFE | HENVCFG_CBZE)",
        f"csrc henvcfg, x{reg}",
    ]
    test_data.int_regs.return_register(reg)
    chunk.code.extend(code)
    return test_data.end_test_chunk()


def _vs_chunk(test_data: TestData, vs: SvMode, henvcfg: bool) -> TestChunk:
    """VS-stage A/D bits with each (menvcfg.ADUE, henvcfg.ADUE), and with ``henvcfg``, henvcfg.ADUE itself."""
    chunk = begin_chunk(
        test_data,
        f"H_{vs.name}_vs_adue",
        "cp_henvcfg_menvcfg, cp_vsatp_adue" if henvcfg else "cp_vsatp_adue",
        "In VS-mode with hgatp = Bare, store, load and fetch through VS-stage leaves with A or D clear, with\n"
        "(menvcfg.ADUE, henvcfg.ADUE) = (0, 1 written), (1, 0) and (1, 1).  Svade raises a page fault; Svadu sets\n"
        "the bits, which are checked in the PTE"
        + (
            "\nIn HS-mode, set henvcfg.ADUE with menvcfg.ADUE = 0, where it is read-only zero, and 1" if henvcfg else ""
        ),
        stages=(vs,),
    )
    code = henvcfg_gate(test_data, vs.xlen, "ADUE", CG) if henvcfg else []
    code.extend(guest_chunk_setup(test_data, None, vs, "VS"))
    code.extend(vs_ad_accesses(test_data, vs, AD_CASES, CG, "cp_vsatp_adue"))
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, vs.xlen)])
    return test_data.end_test_chunk()


def _g_chunk(test_data: TestData, g: SvMode) -> TestChunk:
    """G-stage A/D bits with menvcfg.ADUE = 0 and 1."""
    chunk = begin_chunk(
        test_data,
        f"H_{g.name}_g_adue",
        "cp_hgatp_adue",
        "In VS-mode with vsatp = Bare, store, load and fetch through G-stage leaves with A or D clear, with\n"
        "menvcfg.ADUE = 0 (guest-page fault) and 1 (hardware update, checked in the PTE)",
        stages=(g,),
    )
    code = [*guest_chunk_setup(test_data, g, None, "VS"), *g_ad_accesses(test_data, g, G_AD_CASES, CG, "cp_hgatp_adue")]
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, g.xlen)])
    return test_data.end_test_chunk()


def _two_stage_chunk(test_data: TestData, g: SvMode, vs: SvMode) -> TestChunk:
    """A/D bits in both stages, and A/D updates through a VS-stage leaf table whose G-stage leaf is read-only."""
    chunk = begin_chunk(
        test_data,
        f"H_{g.name}_implicit_adue",
        "cp_twostage_adue, cp_implicit_gpf, cp_hlv_implicit",
        "In VS-mode, store, load and fetch through VS-stage and G-stage leaves with A or D clear, with menvcfg.ADUE\n"
        "and henvcfg.ADUE = 0, 1.  Updated PTEs, including the G-stage leaf of the VS-stage leaf table, are checked.\n"
        "In VS-mode, and with hlv.w, hlvx.wu and hsv.w in HS-mode, access through a VS-stage leaf with A = D = 0\n"
        "in a table whose G-stage leaf is read-only; the A/D update raises a guest-page fault",
        stages=(g, vs),
    )
    reg = test_data.int_regs.get_register()
    code = [
        *guest_chunk_setup(test_data, g, vs, "VS"),
        *implicit_accesses(test_data, g, vs, IMPLICIT_CASES, CG),
        *hlv_implicit_accesses(test_data, g, vs, HLV_IMPLICIT_CASES, CG),
        *set_csr_bits("hstatus", "HSTATUS_SPVP", "0", reg),
    ]
    test_data.int_regs.return_register(reg)
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, g.xlen)])
    return test_data.end_test_chunk()


@add_priv_test_generator("Svadu", required_extensions=["H", "Svadu"], extra_defines=BOOT, params=SV32_PARAMS)
def make_svadu_h_sv32(test_data: TestData) -> list[TestChunk]:
    return [
        _vs_chunk(test_data, VS_SV32, True),
        _g_chunk(test_data, SV32X4),
        _two_stage_chunk(test_data, SV32X4, VS_SV32),
    ]


@add_priv_test_generator("Svadu", required_extensions=["H", "Svadu"], extra_defines=BOOT, params=SV39_PARAMS)
def make_svadu_h_sv39(test_data: TestData) -> list[TestChunk]:
    return [
        _vs_chunk(test_data, VS_SV39, True),
        _g_chunk(test_data, SV39X4),
        _two_stage_chunk(test_data, SV39X4, VS_SV39),
    ]


@add_priv_test_generator(
    "Svadu", required_extensions=["H", "Svadu"], extra_defines=BOOT, params=["SV48_VSMODE_TRANSLATION: true"]
)
def make_svadu_h_vs_sv48(test_data: TestData) -> list[TestChunk]:
    return [_vs_chunk(test_data, VS_SV48, False)]


@add_priv_test_generator(
    "Svadu", required_extensions=["H", "Svadu"], extra_defines=BOOT, params=["SV48X4_TRANSLATION: true"]
)
def make_svadu_h_g_sv48x4(test_data: TestData) -> list[TestChunk]:
    return [_g_chunk(test_data, SV48X4)]


@add_priv_test_generator("Svadu", required_extensions=["H", "Svadu"], extra_defines=BOOT, params=SV48_PARAMS)
def make_svadu_h_two_stage_sv48(test_data: TestData) -> list[TestChunk]:
    return [_two_stage_chunk(test_data, SV48X4, VS_SV48)]


@add_priv_test_generator(
    "Svadu", required_extensions=["H", "Svadu"], extra_defines=BOOT, params=["SV57_VSMODE_TRANSLATION: true"]
)
def make_svadu_h_vs_sv57(test_data: TestData) -> list[TestChunk]:
    return [_vs_chunk(test_data, VS_SV57, False)]


@add_priv_test_generator(
    "Svadu", required_extensions=["H", "Svadu"], extra_defines=BOOT, params=["SV57X4_TRANSLATION: true"]
)
def make_svadu_h_g_sv57x4(test_data: TestData) -> list[TestChunk]:
    return [_g_chunk(test_data, SV57X4)]


@add_priv_test_generator("Svadu", required_extensions=["H", "Svadu"], extra_defines=BOOT, params=SV57_PARAMS)
def make_svadu_h_two_stage_sv57(test_data: TestData) -> list[TestChunk]:
    return [_two_stage_chunk(test_data, SV57X4, VS_SV57)]


@add_priv_test_generator("Svadu", required_extensions=["H", "Svadu", "Zicbom"], extra_defines=BOOT, params=SV32_PARAMS)
def make_svadu_h_sv32_zicbom(test_data: TestData) -> list[TestChunk]:
    return [_cbo_chunk(test_data, SV32X4, VS_SV32, "zicbom")]


@add_priv_test_generator("Svadu", required_extensions=["H", "Svadu", "Zicboz"], extra_defines=BOOT, params=SV32_PARAMS)
def make_svadu_h_sv32_zicboz(test_data: TestData) -> list[TestChunk]:
    return [_cbo_chunk(test_data, SV32X4, VS_SV32, "zicboz")]


@add_priv_test_generator("Svadu", required_extensions=["H", "Svadu", "Zicbom"], extra_defines=BOOT, params=SV39_PARAMS)
def make_svadu_h_sv39_zicbom(test_data: TestData) -> list[TestChunk]:
    return [_cbo_chunk(test_data, SV39X4, VS_SV39, "zicbom")]


@add_priv_test_generator("Svadu", required_extensions=["H", "Svadu", "Zicboz"], extra_defines=BOOT, params=SV39_PARAMS)
def make_svadu_h_sv39_zicboz(test_data: TestData) -> list[TestChunk]:
    return [_cbo_chunk(test_data, SV39X4, VS_SV39, "zicboz")]
