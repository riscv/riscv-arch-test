##################################
# priv/extensions/sv/SvHSm.py
#
# SvHSm suite: two-stage address translation seen from M-mode (MPRV with MPV) and guest traps taken in M-mode.
# David_Harris@hmc.edu 24 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate two-stage translation tests that run in M-mode or take guest traps in M-mode.

The suite boots to M-mode and delegates nothing, so the M-mode handler takes every trap and records
mtval2, mtinst and mstatus.GVA/MPV.
"""

from testgen.asm.helpers import write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.sv.generate import set_atp
from testgen.priv.extensions.sv.page_tables import (
    SV32X4,
    SV39X4,
    VS_SV32,
    VS_SV39,
    PteFlags,
    SvMode,
    create_page_mapping,
)
from testgen.priv.extensions.sv.SvH import (
    G_LEAF,
    LOADS,
    OPS,
    begin_chunk,
    guest_access,
    guest_chunk_setup,
    guest_chunk_teardown,
    map_leaf_table,
    map_test_page,
    perm_flags,
    set_csr_bits,
    status_bits,
)
from testgen.priv.registry import add_priv_test_generator

MPRV_CG = "SvHSm_mprv_cg"
TRAP_CG = "SvHSm_trap_cg"

# mstatus.MPP and MPV: M, HS, VS, U and VU
MPP_MPV = (("m", "MSTATUS_MPP", 0), ("hs", "MPP_SMODE", 0), ("vs", "MPP_SMODE", 1), ("u", "0", 0), ("vu", "0", 1))


def mprv_access(
    test_data: TestData,
    coverpoint: str,
    name: str,
    xlen: int,
    va: str,
    *,
    mprv: int,
    mpp: str,
    mpv: int,
    ops: tuple[str, ...] = ("store", "load"),
    va_is_label: bool = False,
) -> list[str]:
    """In M-mode, run each of ``ops`` at ``va`` with mstatus.MPRV, MPP and MPV (mstatush.MPV on RV32) set, and check
    each load.

    MPRV is set before each access, because a trap from M-mode leaves MPP = M and MPV = 0, and cleared after it,
    so the signature is written with M-mode translation.
    """
    va_reg, data, reg = test_data.int_regs.get_registers(3)
    bits = " | ".join(
        field for field, on in (("MSTATUS_MPRV", mprv), (mpp, mpp != "0"), ("MSTATUS_MPV", mpv and xlen == 64)) if on
    )
    arm = (
        set_csr_bits("mstatus", "MSTATUS_MPRV | MSTATUS_MPP | MSTATUS_MPV", bits or "0", reg)
        if xlen == 64
        else [
            *set_csr_bits("mstatush", "MSTATUSH_MPV", "MSTATUSH_MPV" if mpv else "0", reg),
            *set_csr_bits("mstatus", "MSTATUS_MPRV | MSTATUS_MPP", bits or "0", reg),
        ]
    )
    lines = [f"{'LA' if va_is_label else 'LI'}(x{va_reg}, {va})", f"LI(x{data}, {0x100 + test_data.test_count:#x})"]
    for op in ops:
        label = test_data.add_testcase(f"{name}_{op}", coverpoint, MPRV_CG)
        lines.extend(
            [
                *([f"LI(x{data}, -1)"] if op in LOADS else []),
                *arm,
                label,
                OPS[op].format(va=va_reg, data=data),
                *set_csr_bits("mstatus", "MSTATUS_MPRV", "0", reg),
            ]
        )
        if op in LOADS:
            lines.append(write_sigupd(data, test_data, label=label.removesuffix(":")))
    test_data.int_regs.return_registers([va_reg, data, reg])
    return [*lines, ""]


def _t_mprv_vsatp(test_data: TestData, test_chunks: list[TestChunk], vs: SvMode) -> None:
    """MPRV with MPV = 1 translates M-mode loads and stores through the VS-stage (hgatp and satp Bare)."""
    chunk = begin_chunk(
        test_data,
        f"{vs.name}_mprv_vsatp",
        "cp_vsatp_mprv_effects",
        "In M-mode with mstatus.MPRV = 1, MPV = 1 and MPP = S, U, store and load through a VS-stage leaf that is\n"
        "readable and writable (the access reaches svh_page) or execute-only (page fault).  hgatp and satp are Bare",
    )
    code = [*guest_chunk_setup(test_data, None, vs, "VS"), "csrw satp, zero", "sfence.vma"]
    for mpp_name, mpp in (("s", "MPP_SMODE"), ("u", "0")):
        for perm in ("rw", "x"):
            code.extend(map_test_page(test_data, None, vs, vs_flags=perm_flags(perm, mpp_name == "u")))
            name = f"mpp_{mpp_name}_{perm}"
            code.extend(
                mprv_access(test_data, "cp_vsatp_mprv_effects", name, vs.xlen, vs.data_va, mprv=1, mpp=mpp, mpv=1)
            )
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, vs.xlen)])
    test_chunks.append(test_data.end_test_chunk())


def _t_mprv_hgatp(test_data: TestData, test_chunks: list[TestChunk], g: SvMode) -> None:
    """HLV and HSV use the G-stage whatever MPRV is; loads and stores use it only with MPRV = 1 and MPV = 1."""
    chunk = begin_chunk(
        test_data,
        f"{g.name}_mprv_hgatp",
        "cp_hgatp_mprv_effects",
        "In M-mode with vsatp and satp Bare and a G-stage identity map that makes svh_page execute-only, execute\n"
        "lw, sw, hlv.w and hsv.w on svh_page with mstatus.MPRV = 0, 1 and MPP/MPV = M, HS, VS, U, VU.  Only hlv.w,\n"
        "hsv.w, and lw and sw with MPRV = 1 and MPV = 1, raise guest-page faults",
    )
    pte, addr, tmp = test_data.int_regs.get_registers(3)
    # M-mode makes every access, so no guest code alias is needed
    code = [
        *create_page_mapping(
            g,
            leaf_level=0,
            leaf_flags=perm_flags("x", True),
            virtual_address="svh_page",
            physical_address="svh_page",
            regs=(pte, addr, tmp),
            va_is_label=True,
        ),
        *set_atp(g, pte, addr),
        "csrw vsatp, zero",
        "csrw satp, zero",
        "sfence.vma",
        "hfence.gvma",
        "hfence.vvma",
    ]
    test_data.int_regs.return_registers([pte, addr, tmp])
    for mprv in (0, 1):
        for mode, mpp, mpv in MPP_MPV:
            name = f"mprv{mprv}_{mode}"
            ops = ("store", "load", "hsv", "hlv")
            code.extend(
                mprv_access(
                    test_data,
                    "cp_hgatp_mprv_effects",
                    name,
                    g.xlen,
                    "svh_page + 8",
                    mprv=mprv,
                    mpp=mpp,
                    mpv=mpv,
                    ops=ops,
                    va_is_label=True,
                )
            )
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, g.xlen)])
    test_chunks.append(test_data.end_test_chunk())


def _t_mprv_sum_mxr(test_data: TestData, test_chunks: list[TestChunk], g: SvMode, vs: SvMode) -> None:
    """With MPRV = 1 and MPV = 1, vsstatus.SUM replaces mstatus.SUM, and mstatus.MXR covers both stages."""
    chunk = begin_chunk(
        test_data,
        f"{g.name}_mprv_sum_mxr",
        "cp_mprv_sum, cp_mprv_mxr",
        "In M-mode with mstatus.MPRV = 1 and MPV = 1, store and load on a VS-stage user page with MPP = S and a\n"
        "supervisor page with MPP = U, with vsstatus.SUM = 0, 1 and mstatus.SUM = 0, 1, and load from pages\n"
        "execute-only in the VS-stage, the G-stage or both with MPP = S, U, vsstatus.MXR = 0, 1 and mstatus.MXR = 0, 1",
    )
    reg = test_data.int_regs.get_register()
    code = guest_chunk_setup(test_data, g, vs, "VS")
    for mpp_name, mpp, user in (("s", "MPP_SMODE", True), ("u", "0", False)):
        for vs_sum in (0, 1):
            for m_sum in (0, 1):
                code.extend(
                    [
                        *map_test_page(test_data, g, vs, vs_flags=PteFlags(user=user)),
                        *status_bits("vsstatus", reg, sum_=vs_sum),
                        *status_bits("mstatus", reg, sum_=m_sum),
                    ]
                )
                name = f"mpp_{mpp_name}_u{int(user)}_vssum{vs_sum}_msum{m_sum}"
                code.extend(mprv_access(test_data, "cp_mprv_sum", name, g.xlen, vs.data_va, mprv=1, mpp=mpp, mpv=1))
    # VS-stage leaves are user pages for MPP = U
    for mpp_name, mpp in (("s", "MPP_SMODE"), ("u", "0")):
        for vs_perm, g_perm in (("x", "rwx"), ("rwx", "x"), ("x", "x")):
            for vs_mxr in (0, 1):
                for m_mxr in (0, 1):
                    code.extend(
                        [
                            *map_test_page(
                                test_data,
                                g,
                                vs,
                                vs_flags=perm_flags(vs_perm, mpp_name == "u"),
                                g_flags=perm_flags(g_perm, True),
                            ),
                            *status_bits("vsstatus", reg, mxr=vs_mxr),
                            *status_bits("mstatus", reg, mxr=m_mxr),
                        ]
                    )
                    name = f"mpp_{mpp_name}_vs_{vs_perm}_g_{g_perm}_vsmxr{vs_mxr}_mmxr{m_mxr}"
                    code.extend(
                        mprv_access(
                            test_data,
                            "cp_mprv_mxr",
                            name,
                            g.xlen,
                            vs.data_va,
                            mprv=1,
                            mpp=mpp,
                            mpv=1,
                            ops=("load",),
                        )
                    )
    code.extend(status_bits("mstatus", reg))
    test_data.int_regs.return_register(reg)
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, g.xlen)])
    test_chunks.append(test_data.end_test_chunk())


def _t_guest_faults(test_data: TestData, test_chunks: list[TestChunk], g: SvMode, vs: SvMode, mode: str) -> None:
    """Guest page faults and guest-page faults taken in M-mode record mtval2, mtinst, GVA and MPV."""
    chunk = begin_chunk(
        test_data,
        f"{g.name}_guest_faults_{mode.lower()}",
        "cp_guest_page_fault_m",
        f"In {mode}-mode, with nothing delegated, access through an invalid VS-stage leaf (page fault), an invalid\n"
        "G-stage leaf (guest-page fault, mtval2 = guest physical address >> 2), and a VS-stage leaf table whose\n"
        "G-stage leaf is invalid (guest-page fault with a pseudoinstruction in mtinst).  mstatus.GVA = MPV = 1",
    )
    user = mode == "VU"
    code = guest_chunk_setup(test_data, g, vs, mode)
    cases = (
        ("vs_invalid", map_test_page(test_data, g, vs, vs_flags=perm_flags("inv", user))),
        ("g_invalid", map_test_page(test_data, g, vs, vs_flags=PteFlags(user=user), g_flags=perm_flags("inv", True))),
        ("table_invalid", map_leaf_table(test_data, g, vs, PteFlags(user=user), perm_flags("inv", True), G_LEAF)),
    )
    for name, setup in cases:
        code.extend(
            guest_access(test_data, TRAP_CG, "cp_guest_page_fault_m", name, mode, vs.data_va, setup=setup, driver="M")
        )
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, g.xlen)])
    test_chunks.append(test_data.end_test_chunk())


def _make_svhsm(test_data: TestData, g: SvMode, vs: SvMode) -> list[TestChunk]:
    test_chunks: list[TestChunk] = []
    _t_mprv_vsatp(test_data, test_chunks, vs)
    _t_mprv_hgatp(test_data, test_chunks, g)
    _t_mprv_sum_mxr(test_data, test_chunks, g, vs)
    for mode in ("VS", "VU"):
        _t_guest_faults(test_data, test_chunks, g, vs, mode)
    return test_chunks


@add_priv_test_generator(
    "SvHSm",
    required_extensions=["Sm", "H"],
    extra_defines=["#define BOOT_TO_MMODE"],
    # VS and VU traps need the visible trap handler
    params=["TIME_CSR_IMPLEMENTED: true", "SV32X4_TRANSLATION: true", "SV32_VSMODE_TRANSLATION: true"],
)
def make_svhsm_sv32(test_data: TestData) -> list[TestChunk]:
    return _make_svhsm(test_data, SV32X4, VS_SV32)


@add_priv_test_generator(
    "SvHSm",
    required_extensions=["Sm", "H"],
    extra_defines=["#define BOOT_TO_MMODE"],
    # VS and VU traps need the visible trap handler
    params=["TIME_CSR_IMPLEMENTED: true", "SV39X4_TRANSLATION: true", "SV39_VSMODE_TRANSLATION: true"],
)
def make_svhsm_sv39(test_data: TestData) -> list[TestChunk]:
    return _make_svhsm(test_data, SV39X4, VS_SV39)
