##################################
# priv/extensions/sv/SvH.py
#
# Sv H group: two-stage (VS-stage and G-stage) address translation in HS, VS and VU modes.
# David_Harris@hmc.edu 24 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate two-stage address translation tests.

The group boots to HS-mode.  Guest traps go to the HS-mode handler (hedeleg = 0) except in the tests that
delegate page faults to VS-mode.  Guest code runs at the alias that guest_translation_setup maps, and guest
accesses use the test page svh_page.  Tests that need M-mode (MPRV, and guest-page faults taken into M-mode)
are in the HSm group.
"""

from collections.abc import Sequence

from testgen.asm.csr import gen_csr_read_sigupd
from testgen.asm.helpers import comment_banner, gated, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.sv.access import virtual_address
from testgen.priv.extensions.sv.generate import (
    guest_translation_setup,
    guest_translation_teardown,
    identity_map_image,
)
from testgen.priv.extensions.sv.page_tables import (
    SV32X4,
    SV39X4,
    SV48X4,
    SV57X4,
    VS_SV32,
    VS_SV39,
    VS_SV48,
    VS_SV57,
    PteExpression,
    PteFlags,
    SvMode,
    create_page_mapping,
    create_page_walk,
    guest_table_data,
    lower_table_data,
    write_pte,
)
from testgen.priv.extensions.sv.Sv import PAGE_PERMS, PTE_RESERVED_BITS, PTE_RSW
from testgen.priv.extensions.sv.SvHFenceCommon import (
    HFENCE_GVMA,
    HFENCE_VVMA,
    ISOLATION_CASES,
    SFENCE_VMA_VS,
    fence_chunk,
)
from testgen.priv.extensions.sv.SvZicbo import CBOS
from testgen.priv.registry import add_priv_test_generator

# Guest accesses: a store and a load of the word at offset 8 of the test page, and a fetch of the ret at
# offset 0.  HLV, HLVX and HSV run in HS-mode and access offset 8 of their address, and the CBOs the cache block
# at offset 0.
OPS = {
    "store": "sw x{data}, 8(x{va})",
    "load": "lw x{data}, 8(x{va})",
    "exec": "jalr ra, 0(x{va})",
    "hsv": "hsv.w x{data}, (x{va})",
    "hlv": "hlv.w x{data}, (x{va})",
    "hlvx": "hlvx.wu x{data}, (x{va})",
    **{op.replace(".", "_"): f"{op} (x{{va}})" for ops in CBOS.values() for op in ops},
}
# The CBOs of each family, as OPS keys
CBO_OPS = {family: tuple(op.replace(".", "_") for op in ops) for family, ops in CBOS.items()}
LOADS = ("load", "hlv", "hlvx")
GUEST_OPS = ("store", "load", "exec")

# Leaves that allow every access; G-stage accesses are user-level
VS_LEAF = PteFlags()
G_LEAF = PteFlags(user=True)

VS_CG = "Sv_H_vsstage_cg"
G_CG = "Sv_H_gstage_cg"
TWO_CG = "Sv_H_twostage_cg"
HLV_CG = "Sv_H_hlv_cg"
CSR_CG = "Sv_H_csr_cg"


def begin_chunk(
    test_data: TestData, split_name: str, title: str, description: str, stages: Sequence[SvMode] = ()
) -> TestChunk:
    """Start a chunk whose data section holds two physical test pages and the page tables ``stages`` need.

    svh_page is an odd 4 KiB page, so no superpage leaf maps it aligned.  It starts with ret, holds the load/store
    word at offset 8 and ends with a nop that straddles the next page, which continues with ret.  The framework
    provides the root tables; the chunk adds the level 0-1 tables and the level 2 and 3 tables that Sv48 and Sv57
    walk.
    """
    chunk = test_data.begin_test_chunk(split_name)
    chunk.section_header = comment_banner(title, description)
    chunk.raw_data.extend(
        [
            ".p2align 13",
            ".skip 4096",
            "svh_page:",
            ".4byte 0x00008067    # ret",
            ".4byte 0",
            ".4byte 0x5a5a5a5a    # load/store word",
            ".skip 4096 - 2 - 12",
            ".4byte 0x00000013    # nop straddling the next page",
            ".4byte 0x00008067    # ret",
            ".skip 4096 - 6",
        ]
    )
    chunk.raw_data.extend([*guest_table_data(), *lower_table_data(*stages)])
    return chunk


def set_csr_bits(csr: str, mask: str, bits: str, reg: int) -> list[str]:
    """Clear ``mask`` in ``csr``, then set ``bits`` (a subset of the mask)."""
    lines = [f"LI(x{reg}, {mask})", f"csrc {csr}, x{reg}"]
    if bits != "0":
        lines.extend([f"LI(x{reg}, {bits})", f"csrs {csr}, x{reg}"])
    return lines


def status_bits(csr: str, reg: int, *, sum_: int = 0, mxr: int = 0) -> list[str]:
    """Write the SUM and MXR bits of sstatus, vsstatus or mstatus."""
    bits = " | ".join(name for name, on in (("SSTATUS_SUM", sum_), ("SSTATUS_MXR", mxr)) if on) or "0"
    return set_csr_bits(csr, "SSTATUS_SUM | SSTATUS_MXR", bits, reg)


def menvcfg_bits(xlen: int, *, adue: int, pbmte: int = 0) -> list[str]:
    """Write menvcfg.ADUE and menvcfg.PBMTE through T-SBI (menvcfgh.ADUE on RV32, which has no Svpbmt)."""
    csr, fields = (
        ("CSR_MENVCFG", (("MENVCFG_ADUE", adue), ("MENVCFG_PBMTE", pbmte)))
        if xlen == 64
        else ("CSR_MENVCFGH", (("MENVCFGH_ADUE", adue),))
    )
    lines = [f"RVTEST_TSBI_CSR_CLEAR({csr}, {' | '.join(mask for mask, _ in fields)})"]
    bits = " | ".join(mask for mask, on in fields if on)
    if bits:
        lines.append(f"RVTEST_TSBI_CSR_SET({csr}, {bits})")
    return lines


def henvcfg_bits(xlen: int, reg: int, *, adue: int, pbmte: int = 0) -> list[str]:
    """Write henvcfg.ADUE and henvcfg.PBMTE (henvcfgh.ADUE on RV32, which has no Svpbmt)."""
    csr, fields = (
        ("henvcfg", (("HENVCFG_ADUE", adue), ("HENVCFG_PBMTE", pbmte)))
        if xlen == 64
        else ("henvcfgh", (("HENVCFGH_ADUE", adue),))
    )
    bits = " | ".join(mask for mask, on in fields if on) or "0"
    return set_csr_bits(csr, " | ".join(mask for mask, _ in fields), bits, reg)


def henvcfg_gate(test_data: TestData, xlen: int, field: str, covergroup: str) -> list[str]:
    """In HS-mode, set henvcfg.``field`` (ADUE or PBMTE) with menvcfg.``field`` = 0, where it is read-only zero, and
    with menvcfg.``field`` = 1, and read it back.  RV32 has henvcfgh.ADUE and no Svpbmt."""
    if xlen == 32:
        csr, mask, bits = "henvcfgh", "HENVCFGH_ADUE", 1 << 29
    else:
        csr, mask, bits = "henvcfg", f"HENVCFG_{field}", 1 << (61 if field == "ADUE" else 62)
    val, check = test_data.int_regs.get_registers(2)
    code = []
    for m_bit in (0, 1):
        code.extend(
            [
                *menvcfg_bits(xlen, adue=m_bit if field == "ADUE" else 0, pbmte=m_bit if field == "PBMTE" else 0),
                f"LI(x{val}, {mask})",
                f"csrc {csr}, x{val}",
                test_data.add_testcase(f"{field.lower()}_menvcfg{m_bit}", "cp_henvcfg_menvcfg", covergroup),
                f"csrs {csr}, x{val}",
                gen_csr_read_sigupd(check, (csr, bits), test_data, val),
                f"csrc {csr}, x{val}",
            ]
        )
    test_data.int_regs.return_registers([val, check])
    return [*code, *menvcfg_bits(xlen, adue=0)]


def map_test_page(
    test_data: TestData,
    g: SvMode | None,
    vs: SvMode | None,
    vs_flags: PteExpression = VS_LEAF,
    g_flags: PteExpression = G_LEAF,
) -> list[str]:
    """Map vs.data_va to the guest physical address g.data_va, and that to svh_page, with kilopage leaves.

    A None stage is Bare: vs.data_va then maps to svh_page, or the guest accesses g.data_va directly.
    """
    pte, addr, tmp = test_data.int_regs.get_registers(3)
    regs = (pte, addr, tmp)
    lines = []
    if vs is not None:
        lines.extend(
            create_page_mapping(
                vs,
                leaf_level=0,
                leaf_flags=vs_flags,
                virtual_address=vs.data_va,
                physical_address="svh_page" if g is None else g.data_va,
                regs=regs,
                pa_is_label=g is None,
            )
        )
    if g is not None:
        lines.extend(
            create_page_mapping(
                g, leaf_level=0, leaf_flags=g_flags, virtual_address=g.data_va, physical_address="svh_page", regs=regs
            )
        )
    test_data.int_regs.return_registers(list(regs))
    return [*lines, "hfence.vvma", "hfence.gvma"]


def guest_access(
    test_data: TestData,
    covergroup: str,
    coverpoint: str,
    name: str,
    mode: str | None,
    va: str,
    *,
    setup: Sequence[str] = (),
    ops: Sequence[str] = GUEST_OPS,
    sv: SvMode | None = None,
    level: int = 0,
    va_is_label: bool = False,
    driver: str = "S",
) -> list[str]:
    """Run ``setup``, then the ``ops`` at address ``va`` in ``mode`` (VS or VU), or in the driver mode for None.

    With ``sv``, the address is the ``level`` superpage of ``va`` holding svh_page.  Each load's destination is
    checked back in the driver mode, because VU-mode cannot write the signature.
    """
    va_reg, data = test_data.int_regs.get_registers(2)
    if sv is not None:
        address = virtual_address(sv, va, level, destination=va_reg, physical_address="svh_page", scratch=data)
    else:
        address = [f"{'LA' if va_is_label else 'LI'}(x{va_reg}, {va})"]
    lines = [*setup, *address, f"LI(x{data}, {0x100 + test_data.test_count:#x})"]
    if mode is not None:
        lines.append(f"RVTEST_TSBI_GOTO_{mode}MODE")
    checks = []
    for op in ops:
        label = test_data.add_testcase(f"{name}_{op}", coverpoint, covergroup)
        if op in LOADS:
            lines.append(f"LI(x{data}, -1)")
        lines.extend([label, OPS[op].format(va=va_reg, data=data)])
        if op in LOADS:
            check = write_sigupd(data, test_data, label=label.removesuffix(":"))
            if mode is None:
                lines.append(check)
            else:
                checks.append(check)
    if mode is not None:
        lines.append(f"RVTEST_TSBI_GOTO_{driver}MODE")
    test_data.int_regs.return_registers([va_reg, data])
    return [*lines, *checks, ""]


def read_pte(
    test_data: TestData, mode: SvMode, level: int, va: str, covergroup: str, coverpoint: str, name: str
) -> list[str]:
    """Check the PTE at ``level`` of ``mode``'s tables that maps ``va``, whose A and D bits the hardware may set."""
    reg = test_data.int_regs.get_register()
    lines = [
        f"LA(x{reg}, {mode.pte_address(level, va)})",
        test_data.add_testcase(name, coverpoint, covergroup),
        f"LREG x{reg}, 0(x{reg})",
        write_sigupd(reg, test_data),
    ]
    test_data.int_regs.return_register(reg)
    return lines


def guest_chunk_setup(test_data: TestData, g: SvMode | None, vs: SvMode | None, mode: str) -> list[str]:
    """Turn on guest translation for ``mode`` code and clear the controls the tests change."""
    reg = test_data.int_regs.get_register()
    lines = [
        *guest_translation_setup(test_data, g, vs, f"{mode}mode"),
        *status_bits("sstatus", reg),
        *status_bits("vsstatus", reg),
        "csrw hedeleg, zero",
    ]
    test_data.int_regs.return_register(reg)
    return lines


def guest_chunk_teardown(test_data: TestData, xlen: int) -> list[str]:
    """Turn guest translation off and restore the controls the tests change."""
    reg = test_data.int_regs.get_register()
    lines = [
        *guest_translation_teardown(test_data),
        *status_bits("sstatus", reg),
        *status_bits("vsstatus", reg),
        *henvcfg_bits(xlen, reg, adue=0),
        *menvcfg_bits(xlen, adue=0),
        "csrw hedeleg, zero",
    ]
    test_data.int_regs.return_register(reg)
    return lines


# VS-stage A/D cases: (menvcfg.ADUE, henvcfg.ADUE, leaf flags, accesses).  Svade (ADUE = 0) faults on A = 0, and on
# D = 0 for a store.  The Svadu suite has the ADUE = 1 cases.
SVADE_CASES = (
    (0, 0, PteFlags(accessed=False, dirty=False), GUEST_OPS),
    (0, 0, PteFlags(dirty=False), GUEST_OPS),
)
# G-stage A/D cases: (menvcfg.ADUE, leaf flags, accesses)
G_SVADE_CASES = (
    (0, PteFlags(user=True, accessed=False, dirty=False), GUEST_OPS),
    (0, PteFlags(user=True, dirty=False), GUEST_OPS),
)


def perm_flags(perm: str, user: bool) -> PteFlags:
    """Leaf flags named by R, W and X letters, or "inv" for an invalid PTE."""
    if perm == "inv":
        return PteFlags(valid=False, user=user)
    return PteFlags(user=user, read="r" in perm, write="w" in perm, execute="x" in perm)


def vs_ad_accesses(
    test_data: TestData,
    vs: SvMode,
    cases: Sequence[tuple[int, int, PteFlags, Sequence[str]]],
    covergroup: str,
    coverpoint: str,
) -> list[str]:
    """VS-mode accesses with hgatp = Bare through VS-stage leaves with A or D clear.  The leaf is read back."""
    va = vs.data_va
    reg = test_data.int_regs.get_register()
    code = []
    for m_adue, h_adue, flags, ops in cases:
        name = f"madue{m_adue}_hadue{h_adue}_a{int(flags.accessed)}_d{int(flags.dirty)}_{ops[0]}"
        setup = [
            *menvcfg_bits(vs.xlen, adue=m_adue),
            *henvcfg_bits(vs.xlen, reg, adue=h_adue),
            *map_test_page(test_data, None, vs, vs_flags=flags),
        ]
        code.extend(guest_access(test_data, covergroup, coverpoint, name, "VS", va, setup=setup, ops=ops))
        code.extend(read_pte(test_data, vs, 0, va, covergroup, coverpoint, f"{name}_pte"))
    test_data.int_regs.return_register(reg)
    return code


def g_ad_accesses(
    test_data: TestData,
    g: SvMode,
    cases: Sequence[tuple[int, PteFlags, Sequence[str]]],
    covergroup: str,
    coverpoint: str,
) -> list[str]:
    """VS-mode accesses with vsatp = Bare through G-stage leaves with A or D clear.  The leaf is read back."""
    va = g.data_va
    code = []
    for m_adue, flags, ops in cases:
        name = f"madue{m_adue}_a{int(flags.accessed)}_d{int(flags.dirty)}_{ops[0]}"
        setup = [*menvcfg_bits(g.xlen, adue=m_adue), *map_test_page(test_data, g, None, g_flags=flags)]
        code.extend(guest_access(test_data, covergroup, coverpoint, name, "VS", va, setup=setup, ops=ops))
        code.extend(read_pte(test_data, g, 0, va, covergroup, coverpoint, f"{name}_pte"))
    return code


###########################
# VS-stage translation (hgatp = Bare)
###########################


def _t_vs_perm(test_data: TestData, test_chunks: list[TestChunk], vs: SvMode, mode: str) -> None:
    """VS-stage leaf permissions with vsstatus.SUM and vsstatus.MXR in VS-mode or VU-mode."""
    chunk = begin_chunk(
        test_data,
        f"H_{vs.name}_vs_perm_{mode.lower()}",
        "cp_vsatp_perm, cp_vsatp_sum, cp_vsstatus_mxr",
        f"In {mode}-mode with hgatp = Bare, store, load and fetch through VS-stage leaves with U = 0, 1 and each\n"
        "legal RWX, with vsstatus.SUM = 0, 1 and vsstatus.MXR = 0, 1",
        stages=(vs,),
    )
    va = vs.data_va
    reg = test_data.int_regs.get_register()
    code = guest_chunk_setup(test_data, None, vs, mode)
    cases: list[tuple[str, PteFlags, int, int]] = []
    for user in (False, True):
        cases.extend(
            (f"u{int(user)}_{desc}", PteFlags(user=user, read=r, write=w, execute=x), 0, 0)
            for r, w, x, desc in PAGE_PERMS
        )
    # SUM = 1 lets VS-mode load and store, but not fetch, on user pages; it does not affect VU-mode
    user_perms = PAGE_PERMS if mode == "VS" else PAGE_PERMS[:1]
    for user, (r, w, x, desc) in ((False, PAGE_PERMS[0]), *((True, perm) for perm in user_perms)):
        cases.append((f"sum_u{int(user)}_{desc}", PteFlags(user=user, read=r, write=w, execute=x), 1, 0))
    for user in (False, True):
        for sum_ in (0, 1):
            cases.append((f"mxr_sum{sum_}_u{int(user)}", perm_flags("x", user), sum_, 1))
    for name, flags, sum_, mxr in cases:
        coverpoint = "cp_vsstatus_mxr" if mxr else "cp_vsatp_sum" if sum_ else "cp_vsatp_perm"
        setup = [*map_test_page(test_data, None, vs, vs_flags=flags), *status_bits("vsstatus", reg, sum_=sum_, mxr=mxr)]
        code.extend(guest_access(test_data, VS_CG, coverpoint, name, mode, va, setup=setup))
    test_data.int_regs.return_register(reg)
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, vs.xlen)])
    test_chunks.append(test_data.end_test_chunk())


def _pte_format_cases(xlen: int, user: bool) -> list[tuple[str, PteExpression]]:
    """Leaves whose format decides the access: V clear, a level-0 pointer, RSW set, or a reserved bit set."""
    cases: list[tuple[str, PteExpression]] = [
        ("invalid", PteFlags(valid=False, user=user)),
        ("nonleaf_lvl0", PteFlags(user=user, read=False, write=False, execute=False, accessed=False, dirty=False)),
        *((f"rsw{number}", PteFlags(user=user, extra=(rsw,))) for number, (rsw, _) in enumerate(PTE_RSW, start=1)),
    ]
    if xlen == 64:
        cases.extend((f"reserved_{bit}", PteFlags(user=user, extra=(f"(1 << {bit})",))) for bit in PTE_RESERVED_BITS)
        cases.append(("reserved_all", PteFlags(user=user, extra=("(0x7f << 54)",))))
    return cases


def _t_vs_pte(test_data: TestData, test_chunks: list[TestChunk], vs: SvMode) -> None:
    """VS-stage PTE formats, and A/D bits with Svade, in VS-mode."""
    chunk = begin_chunk(
        test_data,
        f"H_{vs.name}_vs_pte",
        "cp_vsatp_perm, cp_vsatp_svade",
        "In VS-mode with hgatp = Bare, access through VS-stage leaves that are invalid, a level-0 pointer, or have\n"
        "RSW or reserved bits, and through leaves with A or D clear with menvcfg.ADUE = henvcfg.ADUE = 0\n"
        "(page fault, PTE unchanged)",
        stages=(vs,),
    )
    va = vs.data_va
    code = guest_chunk_setup(test_data, None, vs, "VS")
    for name, flags in _pte_format_cases(vs.xlen, False):
        code.extend(
            guest_access(
                test_data,
                VS_CG,
                "cp_vsatp_perm",
                name,
                "VS",
                va,
                setup=map_test_page(test_data, None, vs, vs_flags=flags),
            )
        )
    code.extend(vs_ad_accesses(test_data, vs, SVADE_CASES, VS_CG, "cp_vsatp_svade"))
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, vs.xlen)])
    test_chunks.append(test_data.end_test_chunk())


###########################
# G-stage translation (vsatp = Bare)
###########################


def _t_g_perm(test_data: TestData, test_chunks: list[TestChunk], g: SvMode, mode: str) -> None:
    """G-stage leaf permissions, which are checked as for U-mode, with sstatus.MXR and vsstatus.MXR."""
    chunk = begin_chunk(
        test_data,
        f"H_{g.name}_g_perm_{mode.lower()}",
        "cp_hgatp_perm, cp_hgatp_mxr",
        f"In {mode}-mode with vsatp = Bare, store, load and fetch through G-stage leaves with U = 0, 1 and each\n"
        "legal RWX, and load from an execute-only G-stage page with sstatus.MXR = 0, 1 and vsstatus.MXR = 0, 1.\n"
        "Only sstatus.MXR makes it readable",
        stages=(g,),
    )
    va = g.data_va
    reg = test_data.int_regs.get_register()
    code = guest_chunk_setup(test_data, g, None, mode)
    for user in (False, True):
        for r, w, x, desc in PAGE_PERMS:
            setup = map_test_page(test_data, g, None, g_flags=PteFlags(user=user, read=r, write=w, execute=x))
            code.extend(guest_access(test_data, G_CG, "cp_hgatp_perm", f"u{int(user)}_{desc}", mode, va, setup=setup))
    for s_mxr in (0, 1):
        for vs_mxr in (0, 1):
            setup = [
                *map_test_page(test_data, g, None, g_flags=perm_flags("x", True)),
                *status_bits("sstatus", reg, mxr=s_mxr),
                *status_bits("vsstatus", reg, mxr=vs_mxr),
            ]
            name = f"smxr{s_mxr}_vsmxr{vs_mxr}"
            code.extend(
                guest_access(test_data, G_CG, "cp_hgatp_mxr", name, mode, va, setup=setup, ops=("load", "exec"))
            )
    test_data.int_regs.return_register(reg)
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, g.xlen)])
    test_chunks.append(test_data.end_test_chunk())


def _t_g_pte(test_data: TestData, test_chunks: list[TestChunk], g: SvMode) -> None:
    """G-stage PTE formats, the G bit, misaligned superpages, and A/D bits with Svade."""
    chunk = begin_chunk(
        test_data,
        f"H_{g.name}_g_pte",
        "cp_hgatp_perm, cp_hgatp_svade",
        "In VS-mode with vsatp = Bare, access through G-stage leaves that are invalid, a level-0 pointer, have RSW,\n"
        "reserved or G bits, are misaligned superpages, or have A or D clear with menvcfg.ADUE = 0 (guest-page\n"
        "fault, PTE unchanged)",
        stages=(g,),
    )
    va = g.data_va
    code = guest_chunk_setup(test_data, g, None, "VS")
    for name, flags in [*_pte_format_cases(g.xlen, True), ("g_bit", PteFlags(user=True, global_=True))]:
        setup = map_test_page(test_data, g, None, g_flags=flags)
        code.extend(guest_access(test_data, G_CG, "cp_hgatp_perm", name, "VS", va, setup=setup))
    for level in range(1, g.levels):
        pte, addr, tmp = test_data.int_regs.get_registers(3)
        setup = [
            *create_page_mapping(
                g,
                leaf_level=level,
                leaf_flags=PteFlags(user=True),
                virtual_address=g.data_va,
                physical_address="svh_page",
                regs=(pte, addr, tmp),
                superpage=False,
            ),
            "hfence.gvma",
        ]
        test_data.int_regs.return_registers([pte, addr, tmp])
        code.extend(guest_access(test_data, G_CG, "cp_hgatp_perm", f"misaligned_lvl{level}", "VS", va, setup=setup))
    code.extend(g_ad_accesses(test_data, g, G_SVADE_CASES, G_CG, "cp_hgatp_svade"))
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, g.xlen)])
    test_chunks.append(test_data.end_test_chunk())


def _t_gpa_width(test_data: TestData, test_chunks: list[TestChunk], g: SvMode) -> None:
    """Guest physical addresses with one bit set; bits beyond the mode's width fault.

    The set bit starts at bit 37, above the guest physical addresses of the test image and the other tests.  A leaf
    at the highest level whose page offset is at most the bit maps the address.  Below the root, that walk shares
    the PTEs above the leaf with the test image, so the image is identity mapped again at the leaf's level.
    """
    top = g.levels - 1
    width = g.va_bits
    first_bit = 37
    chunk = begin_chunk(
        test_data,
        f"H_{g.name}_gpa_width",
        "cp_hgatp_gpa_width",
        f"In VS-mode with vsatp = Bare and hgatp = {g.extension}, load from guest physical addresses with one of\n"
        f"bits {first_bit}-63 set.  Bits below {width} translate through a superpage leaf; bits {width}-63 must be\n"
        "zero, or a guest-page fault occurs",
        (g,),
    )
    code = guest_chunk_setup(test_data, g, None, "VS")
    for bit in range(first_bit, 64):
        gpa = hex(1 << bit)
        level = max(lvl for lvl in range(g.levels) if g.page_offset_bits(lvl) <= bit)
        setup = []
        if bit < width:
            pte, addr, tmp = test_data.int_regs.get_registers(3)
            regs = (pte, addr, tmp)
            if level < top:
                setup = [
                    *create_page_walk(g, leaf_level=level, virtual_address=gpa, regs=regs),
                    *identity_map_image(((g, PteFlags(user=True)),), regs, level),
                ]
            setup = [
                *setup,
                *write_pte(
                    g,
                    level=level,
                    flags=PteFlags(user=True),
                    virtual_address=gpa,
                    physical_address="svh_page",
                    regs=regs,
                    superpage=True,
                ),
                "hfence.gvma",
            ]
            test_data.int_regs.return_registers(list(regs))
        code.extend(
            guest_access(
                test_data,
                G_CG,
                "cp_hgatp_gpa_width",
                f"bit{bit}",
                "VS",
                gpa,
                setup=setup,
                ops=("load",),
                sv=g,
                level=level,
            )
        )
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, g.xlen)])
    test_chunks.append(test_data.end_test_chunk())


def _t_sv32x4_gpa(test_data: TestData, test_chunks: list[TestChunk], g: SvMode, vs: SvMode) -> None:
    """Sv32x4 translates 34-bit guest physical addresses, which only a VS-stage leaf can produce."""
    chunk = begin_chunk(
        test_data,
        f"H_{g.name}_gpa_width",
        "cp_hgatp_sv32x4_gpa",
        "In VS-mode, load through a VS-stage leaf whose guest physical address has bit 32, 33 or both set, with the\n"
        "G-stage leaf valid and invalid; the guest-page fault reports guest physical address bits 33:2 in htval",
    )
    va = vs.data_va
    code = guest_chunk_setup(test_data, g, vs, "VS")
    for high in (1, 2, 3):
        gpa = hex((high << 32) | int(g.data_va, 16))
        for valid in (True, False):
            pte, addr, tmp = test_data.int_regs.get_registers(3)
            regs = (pte, addr, tmp)
            setup = [
                *create_page_mapping(
                    vs,
                    leaf_level=0,
                    leaf_flags=PteFlags(),
                    virtual_address=vs.data_va,
                    physical_address=gpa,
                    regs=regs,
                    pa_is_label=False,
                ),
                *create_page_mapping(
                    g,
                    leaf_level=0,
                    leaf_flags=PteFlags(user=True, valid=valid),
                    virtual_address=gpa,
                    physical_address="svh_page",
                    regs=regs,
                ),
                "hfence.vvma",
                "hfence.gvma",
            ]
            test_data.int_regs.return_registers(list(regs))
            name = f"gpa{high}_{'valid' if valid else 'invalid'}"
            code.extend(
                guest_access(test_data, TWO_CG, "cp_hgatp_sv32x4_gpa", name, "VS", va, setup=setup, ops=("load",))
            )
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, g.xlen)])
    test_chunks.append(test_data.end_test_chunk())


###########################
# Two-stage translation
###########################

# (VS-stage, G-stage) permissions.  The VS-stage is checked first; a G-stage denial is a guest-page fault.
TWO_STAGE_PERMS = (
    ("rwx", "rwx"),
    ("r", "rwx"),
    ("rwx", "r"),
    ("x", "r"),
    ("rw", "x"),
    ("inv", "rwx"),
    ("rwx", "inv"),
    ("inv", "inv"),
)
# vsstatus.MXR makes VS-stage execute-only pages readable, and sstatus.MXR those of both stages.  Neither makes a
# page executable.
TWO_STAGE_MXR = (("x", "rwx"), ("rwx", "x"), ("x", "x"), ("r", "r"))


def _t_two_stage(test_data: TestData, test_chunks: list[TestChunk], g: SvMode, vs: SvMode, mode: str) -> None:
    """VS-stage and G-stage permissions combined, and MXR in each stage."""
    chunk = begin_chunk(
        test_data,
        f"H_{g.name}_two_stage_{mode.lower()}",
        "cp_twostage_perm, cp_twostage_mxr",
        f"In {mode}-mode, store, load and fetch where the VS-stage or the G-stage denies the access, and load and\n"
        "fetch from execute-only and read-only pages with vsstatus.MXR = 0, 1 and sstatus.MXR = 0, 1",
        stages=(g, vs),
    )
    user = mode == "VU"
    va = vs.data_va
    reg = test_data.int_regs.get_register()
    code = guest_chunk_setup(test_data, g, vs, mode)
    for vs_perm, g_perm in TWO_STAGE_PERMS:
        setup = map_test_page(test_data, g, vs, vs_flags=perm_flags(vs_perm, user), g_flags=perm_flags(g_perm, True))
        name = f"vs_{vs_perm}_g_{g_perm}"
        code.extend(guest_access(test_data, TWO_CG, "cp_twostage_perm", name, mode, va, setup=setup))
    for vs_perm, g_perm in TWO_STAGE_MXR:
        for vs_mxr in (0, 1):
            for s_mxr in (0, 1):
                setup = [
                    *map_test_page(
                        test_data, g, vs, vs_flags=perm_flags(vs_perm, user), g_flags=perm_flags(g_perm, True)
                    ),
                    *status_bits("vsstatus", reg, mxr=vs_mxr),
                    *status_bits("sstatus", reg, mxr=s_mxr),
                ]
                name = f"vs_{vs_perm}_g_{g_perm}_vsmxr{vs_mxr}_smxr{s_mxr}"
                ops = ("load", "exec")
                code.extend(guest_access(test_data, TWO_CG, "cp_twostage_mxr", name, mode, va, setup=setup, ops=ops))
    test_data.int_regs.return_register(reg)
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, g.xlen)])
    test_chunks.append(test_data.end_test_chunk())


def map_leaf_table(
    test_data: TestData, g: SvMode, vs: SvMode, vs_flags: PteFlags, table_flags: PteFlags, g_flags: PteFlags
) -> list[str]:
    """Map vs.data_va through a VS-stage leaf table at guest physical address g.data_va + 0x1000.

    A G-stage leaf with ``table_flags`` maps that address to rvtest_vlvl0_pg_tbl, which holds the VS-stage leaf.
    """
    table_gpa = f"({g.data_va} + 0x1000)"
    pte, addr, tmp = test_data.int_regs.get_registers(3)
    regs = (pte, addr, tmp)
    lines = [
        *create_page_walk(vs, leaf_level=1, virtual_address=vs.data_va, regs=regs),
        *write_pte(
            vs,
            level=1,
            flags=PteFlags.nonleaf(),
            virtual_address=vs.data_va,
            physical_address=table_gpa,
            regs=regs,
            pa_is_label=False,
        ),
        *write_pte(
            vs,
            level=0,
            flags=vs_flags,
            virtual_address=vs.data_va,
            physical_address=g.data_va,
            regs=regs,
            pa_is_label=False,
        ),
        *create_page_mapping(
            g,
            leaf_level=0,
            leaf_flags=table_flags,
            virtual_address=table_gpa,
            physical_address="rvtest_vlvl0_pg_tbl",
            regs=regs,
        ),
        *create_page_mapping(
            g, leaf_level=0, leaf_flags=g_flags, virtual_address=g.data_va, physical_address="svh_page", regs=regs
        ),
        "hfence.vvma",
        "hfence.gvma",
    ]
    test_data.int_regs.return_registers(list(regs))
    return lines


G_NO_AD = PteFlags(user=True, accessed=False, dirty=False)
G_NO_D = PteFlags(user=True, dirty=False)
VS_NO_AD = PteFlags(accessed=False, dirty=False)
# Implicit VS-stage page-table accesses are G-stage user-level loads, and stores when the hardware updates VS-stage
# A/D bits.  A guest-page fault on one reports the original access type, with a pseudoinstruction in htinst.
# (name, coverpoint, menvcfg.ADUE, henvcfg.ADUE, VS-stage leaf, G-stage leaf of the VS-stage leaf table, G-stage
# leaf of the page, accesses, PTEs checked afterwards: "vs", "table" or "page").  The Svadu suite has the ADUE = 1
# cases.
ImplicitCase = tuple[str, str, int, int, PteFlags, PteFlags, PteFlags, Sequence[str], Sequence[str]]
IMPLICIT_CASES: tuple[ImplicitCase, ...] = (
    ("table_invalid", "cp_implicit_gpf", 0, 0, PteFlags(), PteFlags(valid=False, user=True), G_LEAF, GUEST_OPS, ()),
    ("table_xonly", "cp_implicit_gpf", 0, 0, PteFlags(), perm_flags("x", True), G_LEAF, GUEST_OPS, ()),
    ("table_supervisor", "cp_implicit_gpf", 0, 0, PteFlags(), PteFlags(), G_LEAF, GUEST_OPS, ()),
    ("table_svade", "cp_implicit_gpf", 0, 0, PteFlags(), G_NO_AD, G_LEAF, GUEST_OPS, ()),
    ("vs_svade", "cp_twostage_svade", 0, 0, VS_NO_AD, G_LEAF, G_LEAF, GUEST_OPS, ()),
    ("vs_svade_dirty", "cp_twostage_svade", 0, 0, PteFlags(dirty=False), G_LEAF, G_LEAF, GUEST_OPS, ()),
    ("g_svade", "cp_twostage_svade", 0, 0, PteFlags(), G_LEAF, G_NO_AD, GUEST_OPS, ()),
    ("g_svade_dirty", "cp_twostage_svade", 0, 0, PteFlags(), G_LEAF, G_NO_D, GUEST_OPS, ()),
)


def implicit_accesses(
    test_data: TestData, g: SvMode, vs: SvMode, cases: Sequence[ImplicitCase], covergroup: str
) -> list[str]:
    """VS-mode accesses through a VS-stage leaf table (map_leaf_table) with each case's leaves and ADUE bits."""
    va = vs.data_va
    ptes = {"vs": (vs, vs.data_va), "table": (g, f"({g.data_va} + 0x1000)"), "page": (g, g.data_va)}
    reg = test_data.int_regs.get_register()
    code = []
    for name, coverpoint, m_adue, h_adue, vs_flags, table_flags, g_flags, ops, checks in cases:
        setup = [
            *menvcfg_bits(g.xlen, adue=m_adue),
            *henvcfg_bits(g.xlen, reg, adue=h_adue),
            *map_leaf_table(test_data, g, vs, vs_flags, table_flags, g_flags),
        ]
        code.extend(guest_access(test_data, covergroup, coverpoint, name, "VS", va, setup=setup, ops=ops))
        for check in checks:
            mode, pte_va = ptes[check]
            code.extend(read_pte(test_data, mode, 0, pte_va, covergroup, coverpoint, f"{name}_{check}_pte"))
    test_data.int_regs.return_register(reg)
    return code


def _t_implicit(test_data: TestData, test_chunks: list[TestChunk], g: SvMode, vs: SvMode) -> None:
    """G-stage checks of implicit VS-stage page-table accesses, and Svade in both stages."""
    chunk = begin_chunk(
        test_data,
        f"H_{g.name}_implicit",
        "cp_implicit_gpf, cp_twostage_svade, cp_implicit_mxr",
        "In VS-mode, access through a VS-stage leaf table whose G-stage leaf is invalid, execute-only, not user or\n"
        "has A clear, and through VS-stage and G-stage leaves with A or D clear, with menvcfg.ADUE = henvcfg.ADUE\n"
        "= 0.  Load through an execute-only table with vsstatus.MXR = 1",
        stages=(g, vs),
    )
    va = vs.data_va
    reg = test_data.int_regs.get_register()
    code = [*guest_chunk_setup(test_data, g, vs, "VS"), *implicit_accesses(test_data, g, vs, IMPLICIT_CASES, TWO_CG)]
    # MXR applies only to explicit loads, so vsstatus.MXR does not make the table readable
    setup = [
        *menvcfg_bits(g.xlen, adue=0),
        *status_bits("vsstatus", reg, mxr=1),
        *map_leaf_table(test_data, g, vs, PteFlags(), perm_flags("x", True), G_LEAF),
    ]
    ops = ("load",)
    code.extend(
        guest_access(test_data, TWO_CG, "cp_implicit_mxr", "table_xonly_vsmxr1", "VS", va, setup=setup, ops=ops)
    )
    test_data.int_regs.return_register(reg)
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, g.xlen)])
    test_chunks.append(test_data.end_test_chunk())


def _t_implicit_mxr(test_data: TestData, test_chunks: list[TestChunk], g: SvMode, vs: SvMode) -> None:
    """sstatus.MXR does not make an execute-only G-stage leaf readable for an implicit VS-stage page-table read.

    MXR applies only to explicit loads (hypervisor.adoc, "readable by explicit loads").  This file is separate from
    _t_implicit because Sail applies sstatus.MXR to implicit reads, so its expected results do not raise the
    guest-page fault.
    """
    chunk = begin_chunk(
        test_data,
        f"H_{g.name}_implicit_mxr",
        "cp_implicit_mxr",
        "In VS-mode with sstatus.MXR = 1 and vsstatus.MXR = 0, 1, load through a VS-stage leaf table whose G-stage\n"
        "leaf is execute-only.  The implicit read of the table raises a load guest-page fault",
        stages=(g, vs),
    )
    va = vs.data_va
    reg = test_data.int_regs.get_register()
    code = guest_chunk_setup(test_data, g, vs, "VS")
    for vs_mxr in (0, 1):
        setup = [
            *menvcfg_bits(g.xlen, adue=0),
            *status_bits("sstatus", reg, mxr=1),
            *status_bits("vsstatus", reg, mxr=vs_mxr),
            *map_leaf_table(test_data, g, vs, PteFlags(), perm_flags("x", True), G_LEAF),
        ]
        name = f"table_xonly_smxr1_vsmxr{vs_mxr}"
        code.extend(guest_access(test_data, TWO_CG, "cp_implicit_mxr", name, "VS", va, setup=setup, ops=("load",)))
    test_data.int_regs.return_register(reg)
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, g.xlen)])
    test_chunks.append(test_data.end_test_chunk())


def _t_access_fault(test_data: TestData, test_chunks: list[TestChunk], g: SvMode, vs: SvMode) -> None:
    """Access faults of the original access type on the final supervisor physical address, on reading a VS-stage leaf
    table, and on reading a G-stage leaf table, each in the region at RVMODEL_ACCESS_FAULT_ADDRESS."""
    chunk = begin_chunk(
        test_data,
        f"H_{g.name}_access_fault",
        "cp_twostage_access_fault",
        "In VS-mode, store, load and fetch where the G-stage leaf maps the access to RVMODEL_ACCESS_FAULT_ADDRESS,\n"
        "where the G-stage maps the VS-stage leaf table there, and where a G-stage non-leaf PTE points at a table\n"
        "there.  Each takes an access fault of the original access type",
        stages=(g, vs),
    )
    table_gpa = f"({g.data_va} + 0x1000)"
    # The guest physical address whose G-stage leaf PTE is at access_fault_pte_address
    g_fault_gpa = g.access_fault_walk_va(g.data_va, 0)
    pte, addr, tmp = test_data.int_regs.get_registers(3)
    regs = (pte, addr, tmp)
    nonleaf = PteFlags.nonleaf()
    cases = (
        (
            "leaf",
            f"{vs.data_va} + (RVMODEL_ACCESS_FAULT_ADDRESS & 0xFFF)",
            [
                *create_page_mapping(
                    vs,
                    leaf_level=0,
                    leaf_flags=VS_LEAF,
                    virtual_address=vs.data_va,
                    physical_address=g.data_va,
                    regs=regs,
                    pa_is_label=False,
                ),
                *create_page_mapping(
                    g,
                    leaf_level=0,
                    leaf_flags=G_LEAF,
                    virtual_address=g.data_va,
                    physical_address="RVMODEL_ACCESS_FAULT_ADDRESS",
                    regs=regs,
                    pa_is_label=False,
                ),
            ],
        ),
        (
            "vs_table",
            vs.access_fault_walk_va(vs.data_va, 0),
            [
                *create_page_walk(vs, leaf_level=1, virtual_address=vs.data_va, regs=regs),
                *write_pte(
                    vs,
                    level=1,
                    flags=nonleaf,
                    virtual_address=vs.data_va,
                    physical_address=table_gpa,
                    regs=regs,
                    pa_is_label=False,
                ),
                *create_page_mapping(
                    g,
                    leaf_level=0,
                    leaf_flags=G_LEAF,
                    virtual_address=table_gpa,
                    physical_address="RVMODEL_ACCESS_FAULT_ADDRESS",
                    regs=regs,
                    pa_is_label=False,
                ),
            ],
        ),
        (
            "g_table",
            vs.data_va,
            [
                *create_page_mapping(
                    vs,
                    leaf_level=0,
                    leaf_flags=VS_LEAF,
                    virtual_address=vs.data_va,
                    physical_address=g_fault_gpa,
                    regs=regs,
                    pa_is_label=False,
                ),
                *create_page_walk(g, leaf_level=1, virtual_address=g_fault_gpa, regs=regs),
                *write_pte(
                    g,
                    level=1,
                    flags=nonleaf,
                    virtual_address=g_fault_gpa,
                    physical_address=g.access_fault_pte_address(),
                    regs=regs,
                    pa_is_label=False,
                ),
            ],
        ),
    )
    test_data.int_regs.return_registers(list(regs))
    code = guest_chunk_setup(test_data, g, vs, "VS")
    for name, va, ptes in cases:
        setup = [*ptes, "hfence.vvma", "hfence.gvma"]
        code.extend(guest_access(test_data, TWO_CG, "cp_twostage_access_fault", name, "VS", va, setup=setup))
    code.extend(guest_chunk_teardown(test_data, g.xlen))
    chunk.code.extend(gated(code, "defined(RVMODEL_ACCESS_FAULT_ADDRESS)"))
    test_chunks.append(test_data.end_test_chunk())


def _t_page_sizes(test_data: TestData, test_chunks: list[TestChunk], g: SvMode, vs: SvMode) -> None:
    """Two-stage translation with every combination of VS-stage and G-stage leaf levels."""
    chunk = begin_chunk(
        test_data,
        f"H_{g.name}_page_sizes",
        "cp_twostage_perm",
        "In VS-mode, store, load and fetch through each VS-stage page size combined with each G-stage page size",
        stages=(g, vs),
    )
    code = guest_chunk_setup(test_data, g, vs, "VS")
    for vs_level in vs.levels_desc:
        for g_level in g.levels_desc:
            vs_shift = vs.page_offset_bits(vs_level)
            g_shift = g.page_offset_bits(g_level)
            vs_base = (int(vs.data_va, 16) >> vs_shift) << vs_shift
            g_base = (int(g.data_va, 16) >> g_shift) << g_shift
            gpa, pte, addr, tmp = test_data.int_regs.get_registers(4)
            regs = (pte, addr, tmp)
            setup = [
                *virtual_address(g, hex(g_base), g_level, destination=gpa, physical_address="svh_page", scratch=tmp),
                *create_page_walk(vs, leaf_level=vs_level, virtual_address=hex(vs_base), regs=regs),
                *write_pte(
                    vs,
                    level=vs_level,
                    flags=PteFlags(),
                    virtual_address=hex(vs_base),
                    physical_address="",
                    regs=regs,
                    superpage=vs_level > 0,
                    pa_reg=gpa,
                ),
                *create_page_mapping(
                    g,
                    leaf_level=g_level,
                    leaf_flags=PteFlags(user=True),
                    virtual_address=hex(g_base),
                    physical_address="svh_page",
                    regs=regs,
                ),
                "hfence.vvma",
                "hfence.gvma",
            ]
            test_data.int_regs.return_registers([gpa, *regs])
            # The guest address keeps the offset bits that both leaves pass through
            va = hex(vs_base + (g_base & ((1 << vs_shift) - 1)))
            name = f"vs{vs.page_names[vs_level]}_g{g.page_names[g_level]}"
            level = min(vs_level, g_level)
            code.extend(
                guest_access(test_data, TWO_CG, "cp_twostage_perm", name, "VS", va, setup=setup, sv=vs, level=level)
            )
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, g.xlen)])
    test_chunks.append(test_data.end_test_chunk())


# (name, VS-stage leaf of the next page valid, G-stage leaf of the next page valid)
STRADDLE_CASES = (("mapped", True, True), ("g_invalid", True, False), ("vs_invalid", False, True))


def map_straddle_pages(
    test_data: TestData, g: SvMode, vs: SvMode, *, user: bool = False, vs_valid: bool = True, g_valid: bool = True
) -> list[str]:
    """Map svh_page as map_test_page does, and the next guest page to the page after svh_page, whose VS-stage and
    G-stage leaves are valid or not."""
    next_va = f"({vs.data_va} + 0x1000)"
    next_gpa = f"({g.data_va} + 0x1000)"
    pte, addr, tmp = test_data.int_regs.get_registers(3)
    regs = (pte, addr, tmp)
    lines = [
        *map_test_page(test_data, g, vs, vs_flags=PteFlags(user=user)),
        *write_pte(
            vs,
            level=0,
            flags=PteFlags(user=user, valid=vs_valid),
            virtual_address=next_va,
            physical_address=next_gpa,
            regs=regs,
            pa_is_label=False,
        ),
        *write_pte(
            g,
            level=0,
            flags=PteFlags(user=True, valid=g_valid),
            virtual_address=next_gpa,
            physical_address="svh_page + 0x1000",
            regs=regs,
        ),
        "hfence.vvma",
        "hfence.gvma",
    ]
    test_data.int_regs.return_registers(list(regs))
    return lines


def _t_straddle(test_data: TestData, test_chunks: list[TestChunk], g: SvMode, vs: SvMode, fetch: bool) -> None:
    """An instruction fetch, or a misaligned store or load, that straddles a page boundary faults on the second
    page."""
    name = "straddle" if fetch else "ldst_straddle"
    coverpoint = f"cp_{name}"
    description = (
        "In VS-mode, execute a 4-byte instruction in the last halfword of a page whose next page is mapped, has an\n"
        "invalid G-stage leaf (instruction guest-page fault) or an invalid VS-stage leaf (instruction page fault).\n"
        "stval holds the address of the next page"
        if fetch
        else "In VS-mode, store and load the word two bytes below the end of a page whose next page is mapped, has an\n"
        "invalid G-stage leaf (guest-page fault) or an invalid VS-stage leaf (page fault).  The hart performs\n"
        "misaligned accesses byte by byte, so stval holds the address of the next page"
    )
    chunk = begin_chunk(test_data, f"H_{g.name}_{name}", coverpoint, description, stages=(g, vs))
    code = guest_chunk_setup(test_data, g, vs, "VS")
    va = f"{vs.data_va} + {0xFFE if fetch else 0xFF6:#x}"
    ops = ("exec",) if fetch else ("store", "load")
    for case, vs_valid, g_valid in STRADDLE_CASES:
        setup = map_straddle_pages(test_data, g, vs, vs_valid=vs_valid, g_valid=g_valid)
        code.extend(guest_access(test_data, TWO_CG, coverpoint, case, "VS", va, setup=setup, ops=ops))
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, g.xlen)])
    test_chunks.append(test_data.end_test_chunk())


def _t_hedeleg(test_data: TestData, test_chunks: list[TestChunk], g: SvMode, vs: SvMode, mode: str) -> None:
    """With hedeleg delegating page faults, VS-stage faults go to VS-mode.  Guest-page faults cannot be delegated
    (hedeleg bits 20-23 are read-only zero), so they still go to HS-mode."""
    chunk = begin_chunk(
        test_data,
        f"H_{g.name}_hedeleg_{mode.lower()}",
        "cp_hedeleg_page_fault, cp_hedeleg_guest_page_fault",
        f"In {mode}-mode with hedeleg[12], [13], [15], [20], [21] and [23] written with 1, access through an invalid\n"
        "and a read-only VS-stage leaf (page faults taken in VS-mode) and an invalid G-stage leaf (guest-page faults\n"
        "taken in HS-mode)",
        stages=(g, vs),
    )
    user = mode == "VU"
    reg = test_data.int_regs.get_register()
    code = [
        *guest_chunk_setup(test_data, g, vs, mode),
        (
            f"LI(x{reg}, (1 << CAUSE_FETCH_PAGE_FAULT) | (1 << CAUSE_LOAD_PAGE_FAULT) | (1 << CAUSE_STORE_PAGE_FAULT)"
            " | (1 << CAUSE_FETCH_GUEST_PAGE_FAULT) | (1 << CAUSE_LOAD_GUEST_PAGE_FAULT)"
            " | (1 << CAUSE_STORE_GUEST_PAGE_FAULT))"
        ),
        f"csrw hedeleg, x{reg}",
    ]
    test_data.int_regs.return_register(reg)
    for vs_perm, g_perm in (("inv", "rwx"), ("r", "rwx"), ("rwx", "inv")):
        setup = map_test_page(test_data, g, vs, vs_flags=perm_flags(vs_perm, user), g_flags=perm_flags(g_perm, True))
        name = f"vs_{vs_perm}_g_{g_perm}"
        coverpoint = "cp_hedeleg_guest_page_fault" if g_perm == "inv" else "cp_hedeleg_page_fault"
        code.extend(guest_access(test_data, TWO_CG, coverpoint, name, mode, vs.data_va, setup=setup))
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, g.xlen)])
    test_chunks.append(test_data.end_test_chunk())


def _t_canonical(test_data: TestData, test_chunks: list[TestChunk], g: SvMode, vs: SvMode, mode: str) -> None:
    """A guest virtual address that is not sign-extended from the VS-stage mode's top bit page-faults."""
    width = vs.va_bits
    chunk = begin_chunk(
        test_data,
        f"H_{g.name}_canonical_{mode.lower()}",
        "cp_twostage_canonical",
        f"In {mode}-mode with vsatp = {vs.extension} and hgatp = {g.extension}, store, load and fetch at the mapped\n"
        f"guest virtual address with bit {width} set, and with bits 63-{width} set.  Bit {width - 1} is clear, so\n"
        "both addresses are non-canonical and raise page faults, not guest-page faults",
        stages=(g, vs),
    )
    base = int(vs.data_va, 16)
    upper = ((1 << 64) - 1) ^ ((1 << width) - 1)
    code = [
        *guest_chunk_setup(test_data, g, vs, mode),
        *map_test_page(test_data, g, vs, vs_flags=PteFlags(user=mode == "VU")),
    ]
    for name, va in ((f"bit{width}", base | 1 << width), (f"bits63_{width}", base | upper)):
        code.extend(guest_access(test_data, TWO_CG, "cp_twostage_canonical", name, mode, hex(va)))
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, g.xlen)])
    test_chunks.append(test_data.end_test_chunk())


def _t_gpa_wide(test_data: TestData, test_chunks: list[TestChunk], g: SvMode, vs: SvMode) -> None:
    """A VS-stage PPN that makes a guest physical address wider than the G-stage mode allows guest-page-faults."""
    width = g.va_bits
    chunk = begin_chunk(
        test_data,
        f"H_{g.name}_gpa_wide",
        "cp_twostage_gpa_width",
        f"In VS-mode, store, load and fetch through a VS-stage leaf whose PPN sets guest physical address bit {width}\n"
        "or 55, and through a VS-stage level-1 PTE that points to the leaf table at such an address.  Guest physical\n"
        f"address bits {width}-63 must be zero for {g.extension}, so each access raises a guest-page fault.  A hart\n"
        "that drops the high bits reaches a valid G-stage leaf instead",
        stages=(g, vs),
    )
    va = vs.data_va
    code = guest_chunk_setup(test_data, g, vs, "VS")
    for bit in (width, 55):
        high = 1 << bit
        table, pte, addr, tmp = test_data.int_regs.get_registers(4)
        regs = (pte, addr, tmp)
        g_leaf = create_page_mapping(
            g, leaf_level=0, leaf_flags=G_LEAF, virtual_address=g.data_va, physical_address="svh_page", regs=regs
        )
        leaf_setup = [
            *create_page_mapping(
                vs,
                leaf_level=0,
                leaf_flags=PteFlags(),
                virtual_address=va,
                physical_address=hex(int(g.data_va, 16) | high),
                regs=regs,
                pa_is_label=False,
            ),
            *g_leaf,
            "hfence.vvma",
            "hfence.gvma",
        ]
        table_setup = [
            *create_page_walk(vs, leaf_level=1, virtual_address=va, regs=regs),
            f"LA(x{table}, rvtest_vlvl0_pg_tbl)",
            f"LI(x{tmp}, {high:#x})",
            f"or x{table}, x{table}, x{tmp}",
            *write_pte(
                vs, level=1, flags=PteFlags.nonleaf(), virtual_address=va, physical_address="", regs=regs, pa_reg=table
            ),
            *write_pte(
                vs,
                level=0,
                flags=PteFlags(),
                virtual_address=va,
                physical_address=g.data_va,
                regs=regs,
                pa_is_label=False,
            ),
            *g_leaf,
            "hfence.vvma",
            "hfence.gvma",
        ]
        test_data.int_regs.return_registers([table, *regs])
        for name, setup in ((f"leaf_bit{bit}", leaf_setup), (f"table_bit{bit}", table_setup)):
            code.extend(guest_access(test_data, TWO_CG, "cp_twostage_gpa_width", name, "VS", va, setup=setup))
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, g.xlen)])
    test_chunks.append(test_data.end_test_chunk())


###########################
# HLV, HLVX and HSV in HS-mode
###########################


# (VS-stage, G-stage) permissions for HLV and HLVX with each MXR.  MXR makes execute-only pages readable for HLV;
# HLVX needs execute permission in both stages, and MXR does not grant it.
HLV_PERM_CASES = (
    ("x", "rwx", "cp_hlv_mxr", ("hlv", "hlvx")),
    ("rwx", "x", "cp_hlv_mxr", ("hlv", "hlvx")),
    ("r", "rwx", "cp_hlvx_perm", ("hlvx",)),
    ("rwx", "r", "cp_hlvx_perm", ("hlvx",)),
)
# HLV, HLVX and HSV through a VS-stage leaf table whose G-stage leaf is execute-only or readable.  The table reads
# are implicit loads, so HLVX needs G-stage read permission, not execute.  The Svadu suite has the A/D update case.
# (name, menvcfg.ADUE, henvcfg.ADUE, VS-stage leaf, G-stage leaf of the VS-stage leaf table, accesses)
HlvImplicitCase = tuple[str, int, int, PteFlags, PteFlags, Sequence[str]]
HLV_IMPLICIT_CASES: tuple[HlvImplicitCase, ...] = (
    ("table_xonly", 0, 0, PteFlags(), perm_flags("x", True), ("hlv", "hlvx", "hsv")),
    ("table_readable", 0, 0, PteFlags(), perm_flags("r", True), ("hlvx",)),
)


def hlv_implicit_accesses(
    test_data: TestData, g: SvMode, vs: SvMode, cases: Sequence[HlvImplicitCase], covergroup: str
) -> list[str]:
    """HS-mode HLV, HLVX and HSV with hstatus.SPVP = 1 through a VS-stage leaf table (map_leaf_table).  The caller
    clears SPVP afterwards."""
    va = f"{vs.data_va} + 8"
    reg = test_data.int_regs.get_register()
    code = []
    for name, m_adue, h_adue, vs_flags, table_flags, ops in cases:
        setup = [
            *menvcfg_bits(g.xlen, adue=m_adue),
            *henvcfg_bits(g.xlen, reg, adue=h_adue),
            *map_leaf_table(test_data, g, vs, vs_flags, table_flags, G_LEAF),
            *set_csr_bits("hstatus", "HSTATUS_SPVP", "HSTATUS_SPVP", reg),
            *status_bits("vsstatus", reg),
            *status_bits("sstatus", reg),
        ]
        code.extend(guest_access(test_data, covergroup, "cp_hlv_implicit", name, None, va, setup=setup, ops=ops))
    test_data.int_regs.return_register(reg)
    return code


def _hlv_root_gpf(test_data: TestData, g: SvMode, vs: SvMode, va: str) -> list[str]:
    """HLV, HLVX and HSV with vsatp.PPN at a guest physical page whose G-stage leaf is invalid, so the read of the
    VS-stage root table takes a guest-page fault."""
    root_gpa = f"({g.data_va} + 0x2000)"
    ppn_bits = 22 if vs.xlen == 32 else 44
    pte, addr, tmp = test_data.int_regs.get_registers(3)
    save = test_data.int_regs.get_register()
    setup = [
        *create_page_mapping(
            g,
            leaf_level=0,
            leaf_flags=PteFlags(valid=False, user=True),
            virtual_address=root_gpa,
            physical_address="svh_page",
            regs=(pte, addr, tmp),
        ),
        "hfence.gvma",
        f"csrr x{save}, vsatp",
        f"srli x{tmp}, x{save}, {ppn_bits}",
        f"slli x{tmp}, x{tmp}, {ppn_bits}",
        f"LI(x{addr}, {root_gpa} >> 12)",
        f"or x{tmp}, x{tmp}, x{addr}",
        f"csrw vsatp, x{tmp}",
        "hfence.vvma",
    ]
    test_data.int_regs.return_registers([pte, addr, tmp])
    ops = ("hlv", "hlvx", "hsv")
    lines = guest_access(test_data, HLV_CG, "cp_hlv_root_gpf", "root_invalid", None, va, setup=setup, ops=ops)
    test_data.int_regs.return_register(save)
    return [*lines, f"csrw vsatp, x{save}", "hfence.vvma"]


def _t_hlv(test_data: TestData, test_chunks: list[TestChunk], g: SvMode, vs: SvMode) -> None:
    """HLV, HLVX and HSV privilege from hstatus.SPVP against the VS-stage U bit, MXR in each stage, and the execute
    permission that HLVX needs in both stages."""
    chunk = begin_chunk(
        test_data,
        f"H_{g.name}_hlv",
        "cp_hlv_priv, cp_hlv_mxr, cp_hlvx_perm, cp_hlv_implicit, cp_hlv_root_gpf",
        "In HS-mode, execute hlv.w, hlvx.wu and hsv.w on VS-stage pages with U = 0, 1, with hstatus.SPVP = 0, 1,\n"
        "vsstatus.SUM = 0, 1 and sstatus.SUM = 0, 1 (ignored), hlv.w and hlvx.wu on execute-only VS-stage and\n"
        "G-stage pages, and hlvx.wu on read-only VS-stage and G-stage pages (a load page fault or load guest-page\n"
        "fault, because HLVX needs execute permission), with vsstatus.MXR = 0, 1 and sstatus.MXR = 0, 1.\n"
        "Execute them through a VS-stage leaf table whose G-stage leaf is execute-only or readable, and with a\n"
        "VS-stage root table whose G-stage leaf is invalid",
        stages=(g, vs),
    )
    va = f"{vs.data_va} + 8"
    reg = test_data.int_regs.get_register()
    code = guest_chunk_setup(test_data, g, vs, "VS")
    for spvp in (0, 1):
        for vs_sum in (0, 1):
            for s_sum in (0, 1):
                for user in (False, True):
                    setup = [
                        *map_test_page(test_data, g, vs, vs_flags=PteFlags(user=user)),
                        *set_csr_bits("hstatus", "HSTATUS_SPVP", "HSTATUS_SPVP" if spvp else "0", reg),
                        *status_bits("vsstatus", reg, sum_=vs_sum),
                        *status_bits("sstatus", reg, sum_=s_sum),
                    ]
                    name = f"spvp{spvp}_vssum{vs_sum}_ssum{s_sum}_u{int(user)}"
                    ops = ("hlv", "hlvx", "hsv")
                    code.extend(guest_access(test_data, HLV_CG, "cp_hlv_priv", name, None, va, setup=setup, ops=ops))
    for vs_perm, g_perm, coverpoint, ops in HLV_PERM_CASES:
        for vs_mxr in (0, 1):
            for s_mxr in (0, 1):
                setup = [
                    *map_test_page(
                        test_data, g, vs, vs_flags=perm_flags(vs_perm, False), g_flags=perm_flags(g_perm, True)
                    ),
                    *set_csr_bits("hstatus", "HSTATUS_SPVP", "HSTATUS_SPVP", reg),
                    *status_bits("vsstatus", reg, mxr=vs_mxr),
                    *status_bits("sstatus", reg, mxr=s_mxr),
                ]
                name = f"vs_{vs_perm}_g_{g_perm}_vsmxr{vs_mxr}_smxr{s_mxr}"
                code.extend(guest_access(test_data, HLV_CG, coverpoint, name, None, va, setup=setup, ops=ops))
    code.extend(hlv_implicit_accesses(test_data, g, vs, HLV_IMPLICIT_CASES, HLV_CG))
    code.extend(_hlv_root_gpf(test_data, g, vs, va))
    code.extend(set_csr_bits("hstatus", "HSTATUS_SPVP", "0", reg))
    test_data.int_regs.return_register(reg)
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, g.xlen)])
    test_chunks.append(test_data.end_test_chunk())


###########################
# vsatp, hgatp and satp MODE (RV64)
###########################

# MODE: (the symbol defined when vsatp supports it, the symbol defined when hgatp supports it as SvNNx4)
ATP_MODES = {
    8: ("UDB_SV39_VSMODE_TRANSLATION", "UDB_SV39X4_TRANSLATION"),
    9: ("UDB_SV48_VSMODE_TRANSLATION", "UDB_SV48X4_TRANSLATION"),
    10: ("UDB_SV57_VSMODE_TRANSLATION", "UDB_SV57X4_TRANSLATION"),
}


def _supported_mode_check(test_data: TestData, csr: str, gates: Sequence[str]) -> list[str]:
    """Check only that ``csr`` holds a supported MODE, which is all that writing an unsupported MODE guarantees."""
    check, mask = test_data.int_regs.get_registers(2)
    lines = [f"csrr x{check}, {csr}", f"srli x{check}, x{check}, 60", f"LI(x{mask}, 1)    # Bare"]
    for mode, gate in zip(ATP_MODES, gates, strict=True):
        lines.extend([f"#ifdef {gate}", f"ori x{mask}, x{mask}, {1 << mode:#x}", "#endif"])
    lines.extend([f"srl x{check}, x{mask}, x{check}", f"andi x{check}, x{check}, 1", write_sigupd(check, test_data)])
    test_data.int_regs.return_registers([check, mask])
    return lines


def _t_atp_mode(test_data: TestData, test_chunks: list[TestChunk]) -> None:
    """Write each MODE to vsatp and hgatp in HS-mode, and to satp (vsatp) in VS-mode."""
    chunk = begin_chunk(
        test_data,
        "H_sv39x4_atp_mode",
        "cp_vsatp_mode_field, cp_hgatp_mode_field, cp_satp_mode_field",
        "Starting from MODE = Bare and Sv39 (Sv39x4), write MODE = 0-15 to vsatp and hgatp in HS-mode, where an\n"
        "unsupported MODE leaves a supported one (the write is ignored or WARL), and to satp in VS-mode, where an\n"
        "unsupported MODE is ignored.  The other fields are zero, or the root table in VS-mode",
    )
    save, val, check = test_data.int_regs.get_registers(3)
    code = []
    for csr, stage, coverpoint in (("vsatp", 0, "cp_vsatp_mode_field"), ("hgatp", 1, "cp_hgatp_mode_field")):
        gates = [pair[stage] for pair in ATP_MODES.values()]
        code.append(f"csrr x{save}, {csr}")
        for start in (0, 8):
            for mode in range(16):
                code.extend(
                    [
                        f"LI(x{val}, {start << 60:#x})",
                        f"csrw {csr}, x{val}",
                        f"LI(x{val}, {mode << 60:#x})",
                        test_data.add_testcase(f"start{start}_mode{mode}", coverpoint, CSR_CG),
                        f"csrw {csr}, x{val}",
                    ]
                )
                if mode == 0:
                    code.append(gen_csr_read_sigupd(check, (csr, None), test_data))
                elif mode in ATP_MODES:
                    code.extend(
                        [
                            f"#ifdef {ATP_MODES[mode][stage]}",
                            gen_csr_read_sigupd(check, (csr, None), test_data),
                            "#else",
                            *_supported_mode_check(test_data, csr, gates),
                            "#endif",
                        ]
                    )
                else:
                    code.extend(_supported_mode_check(test_data, csr, gates))
        code.append(f"csrw {csr}, x{save}")

    # The VS-stage identity maps the test image for Sv39 (gigapages) and for Sv48 and Sv57 (the terapage or
    # petapage at root index 0), so VS-mode keeps running whatever MODE it selects.
    regs = (save, val, check)
    code.extend(["// Identity map the test image in the VS-stage", *identity_map_image(((VS_SV39, PteFlags()),), regs)])
    code.extend(
        [
            *write_pte(
                VS_SV48,
                level=3,
                flags=PteFlags(),
                virtual_address="rvtest_code_begin",
                physical_address="rvtest_code_begin",
                regs=regs,
                va_is_label=True,
                superpage=True,
            ),
            "csrw vsatp, zero",
            "csrw hgatp, zero",
            "hfence.vvma",
            "hfence.gvma",
            "RVTEST_TSBI_GOTO_VSMODE",
        ]
    )
    root, start_val = save, val
    for start in (0, 8):
        for mode in range(16):
            code.extend(
                [
                    f"LA(x{root}, rvtest_Vroot_pg_tbl)",
                    f"srli x{root}, x{root}, 12",
                    f"LI(x{start_val}, {start << 60:#x})",
                    *([f"or x{start_val}, x{start_val}, x{root}"] if start else []),
                    f"csrw satp, x{start_val}",
                    "sfence.vma",
                    f"LI(x{check}, {mode << 60:#x})",
                    *([f"or x{check}, x{check}, x{root}"] if mode else []),
                    test_data.add_testcase(f"start{start}_mode{mode}", "cp_satp_mode_field", CSR_CG),
                    f"csrw satp, x{check}",
                    "sfence.vma",
                    gen_csr_read_sigupd(check, ("satp", None), test_data),
                ]
            )
    code.extend(["csrw satp, zero", "sfence.vma", "RVTEST_TSBI_GOTO_SMODE"])
    test_data.int_regs.return_registers([save, val, check])
    chunk.code.extend(code)
    test_chunks.append(test_data.end_test_chunk())


def _t_bare(test_data: TestData, test_chunks: list[TestChunk], g: SvMode) -> None:
    """Guest accesses with vsatp and hgatp Bare."""
    chunk = begin_chunk(
        test_data,
        f"H_{g.name}_bare",
        "cp_stage_both_bare",
        "In VS-mode and VU-mode with vsatp and hgatp Bare, store, load and fetch at a physical address",
    )
    code = ["csrw vsatp, zero", "csrw hgatp, zero", "hfence.vvma", "hfence.gvma"]
    for mode in ("VS", "VU"):
        code.extend(
            guest_access(test_data, TWO_CG, "cp_stage_both_bare", mode.lower(), mode, "svh_page", va_is_label=True)
        )
    chunk.code.extend(code)
    test_chunks.append(test_data.end_test_chunk())


def _vs_stage_tests(test_data: TestData, vs: SvMode) -> list[TestChunk]:
    """VS-stage translation with hgatp = Bare."""
    test_chunks: list[TestChunk] = []
    for mode in ("VS", "VU"):
        _t_vs_perm(test_data, test_chunks, vs, mode)
    _t_vs_pte(test_data, test_chunks, vs)
    return test_chunks


def _g_stage_tests(test_data: TestData, g: SvMode) -> list[TestChunk]:
    """G-stage translation with vsatp = Bare."""
    test_chunks: list[TestChunk] = []
    for mode in ("VS", "VU"):
        _t_g_perm(test_data, test_chunks, g, mode)
    _t_g_pte(test_data, test_chunks, g)
    if g.xlen == 64:
        _t_gpa_width(test_data, test_chunks, g)
    return test_chunks


def _two_stage_tests(test_data: TestData, g: SvMode, vs: SvMode) -> list[TestChunk]:
    """VS-stage and G-stage translation together, in guest accesses and in HLV, HLVX and HSV."""
    test_chunks: list[TestChunk] = []
    for mode in ("VS", "VU"):
        _t_two_stage(test_data, test_chunks, g, vs, mode)
    _t_implicit(test_data, test_chunks, g, vs)
    # TODO: Uncomment when Sail no longer applies sstatus.MXR to implicit VS-stage page-table reads.
    # _t_implicit_mxr(test_data, test_chunks, g, vs)
    _t_access_fault(test_data, test_chunks, g, vs)
    _t_page_sizes(test_data, test_chunks, g, vs)
    _t_hlv(test_data, test_chunks, g, vs)
    if g.xlen == 32:
        _t_sv32x4_gpa(test_data, test_chunks, g, vs)
        return test_chunks
    for mode in ("VS", "VU"):
        _t_canonical(test_data, test_chunks, g, vs, mode)
    # A VS-stage PPN reaches guest physical address bit 55, beyond Sv39x4 and Sv48x4 but not Sv57x4
    if g.va_bits <= 55:
        _t_gpa_wide(test_data, test_chunks, g, vs)
    return test_chunks


def _fence_chunk(test_data: TestData, g: SvMode, vs: SvMode) -> TestChunk:
    fences = (HFENCE_VVMA, HFENCE_GVMA, SFENCE_VMA_VS)
    return fence_chunk(test_data, g, vs, f"H_{g.name}_fence", fences, "Sv_H_fence_cg", ISOLATION_CASES)


def _make_svh(test_data: TestData, g: SvMode, vs: SvMode) -> list[TestChunk]:
    """Every H group test for the smallest G-stage and VS-stage modes of each XLEN."""
    test_chunks: list[TestChunk] = []
    _t_bare(test_data, test_chunks, g)
    test_chunks.extend(_vs_stage_tests(test_data, vs))
    test_chunks.extend(_g_stage_tests(test_data, g))
    test_chunks.extend(_two_stage_tests(test_data, g, vs))
    for mode in ("VS", "VU"):
        _t_hedeleg(test_data, test_chunks, g, vs, mode)
    if g.xlen == 64:
        _t_atp_mode(test_data, test_chunks)
    return test_chunks


def _make_svh_straddle(test_data: TestData, g: SvMode, vs: SvMode) -> list[TestChunk]:
    test_chunks: list[TestChunk] = []
    _t_straddle(test_data, test_chunks, g, vs, fetch=True)
    return test_chunks


def _make_svh_ldst_straddle(test_data: TestData, g: SvMode, vs: SvMode) -> list[TestChunk]:
    test_chunks: list[TestChunk] = []
    _t_straddle(test_data, test_chunks, g, vs, fetch=False)
    return test_chunks


SV32_PARAMS = ["SV32X4_TRANSLATION: true", "SV32_VSMODE_TRANSLATION: true"]
SV39_PARAMS = ["SV39X4_TRANSLATION: true", "SV39_VSMODE_TRANSLATION: true"]
SV48_PARAMS = ["SV48X4_TRANSLATION: true", "SV48_VSMODE_TRANSLATION: true"]
SV57_PARAMS = ["SV57X4_TRANSLATION: true", "SV57_VSMODE_TRANSLATION: true"]
MISALIGNED_PARAMS = ["MISALIGNED_LDST: true", "MISALIGNED_SPLIT_STRATEGY: sequential_bytes"]
BOOT = ["#define BOOT_TO_SMODE"]


@add_priv_test_generator("Sv", required_extensions=["H"], extra_defines=BOOT, params=SV32_PARAMS)
def make_svh_sv32(test_data: TestData) -> list[TestChunk]:
    return [*_make_svh(test_data, SV32X4, VS_SV32), _fence_chunk(test_data, SV32X4, VS_SV32)]


@add_priv_test_generator("Sv", required_extensions=["H"], extra_defines=BOOT, params=SV39_PARAMS)
def make_svh_sv39(test_data: TestData) -> list[TestChunk]:
    return [*_make_svh(test_data, SV39X4, VS_SV39), _fence_chunk(test_data, SV39X4, VS_SV39)]


# A 4-byte instruction in the last halfword of a page needs IALIGN = 16
@add_priv_test_generator("Sv", required_extensions=["H", "Zca"], extra_defines=BOOT, params=SV32_PARAMS)
def make_svh_straddle_sv32(test_data: TestData) -> list[TestChunk]:
    return _make_svh_straddle(test_data, SV32X4, VS_SV32)


@add_priv_test_generator("Sv", required_extensions=["H", "Zca"], extra_defines=BOOT, params=SV39_PARAMS)
def make_svh_straddle_sv39(test_data: TestData) -> list[TestChunk]:
    return _make_svh_straddle(test_data, SV39X4, VS_SV39)


# The hart performs misaligned accesses byte by byte, so it faults only on the second page
@add_priv_test_generator("Sv", required_extensions=["H"], extra_defines=BOOT, params=[*SV32_PARAMS, *MISALIGNED_PARAMS])
def make_svh_ldst_straddle_sv32(test_data: TestData) -> list[TestChunk]:
    return _make_svh_ldst_straddle(test_data, SV32X4, VS_SV32)


@add_priv_test_generator("Sv", required_extensions=["H"], extra_defines=BOOT, params=[*SV39_PARAMS, *MISALIGNED_PARAMS])
def make_svh_ldst_straddle_sv39(test_data: TestData) -> list[TestChunk]:
    return _make_svh_ldst_straddle(test_data, SV39X4, VS_SV39)


@add_priv_test_generator("Sv", required_extensions=["H"], extra_defines=BOOT, params=["SV48_VSMODE_TRANSLATION: true"])
def make_svh_vs_sv48(test_data: TestData) -> list[TestChunk]:
    return _vs_stage_tests(test_data, VS_SV48)


@add_priv_test_generator("Sv", required_extensions=["H"], extra_defines=BOOT, params=["SV48X4_TRANSLATION: true"])
def make_svh_g_sv48x4(test_data: TestData) -> list[TestChunk]:
    return _g_stage_tests(test_data, SV48X4)


@add_priv_test_generator("Sv", required_extensions=["H"], extra_defines=BOOT, params=SV48_PARAMS)
def make_svh_two_stage_sv48(test_data: TestData) -> list[TestChunk]:
    return _two_stage_tests(test_data, SV48X4, VS_SV48)


@add_priv_test_generator("Sv", required_extensions=["H"], extra_defines=BOOT, params=["SV57_VSMODE_TRANSLATION: true"])
def make_svh_vs_sv57(test_data: TestData) -> list[TestChunk]:
    return _vs_stage_tests(test_data, VS_SV57)


@add_priv_test_generator("Sv", required_extensions=["H"], extra_defines=BOOT, params=["SV57X4_TRANSLATION: true"])
def make_svh_g_sv57x4(test_data: TestData) -> list[TestChunk]:
    return _g_stage_tests(test_data, SV57X4)


@add_priv_test_generator("Sv", required_extensions=["H"], extra_defines=BOOT, params=SV57_PARAMS)
def make_svh_two_stage_sv57(test_data: TestData) -> list[TestChunk]:
    return _two_stage_tests(test_data, SV57X4, VS_SV57)
