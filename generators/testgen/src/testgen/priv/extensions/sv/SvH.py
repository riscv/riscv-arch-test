##################################
# priv/extensions/sv/SvH.py
#
# SvH suite: two-stage (VS-stage and G-stage) address translation in HS, VS and VU modes.
# David_Harris@hmc.edu 24 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate two-stage address translation tests.

The suite boots to HS-mode.  Guest traps go to the HS-mode handler (hedeleg = 0) except in the tests that
delegate page faults to VS-mode.  Guest code runs at the alias that guest_translation_setup maps, and guest
accesses use the test page svh_page.  Tests that need M-mode (MPRV, and guest-page faults taken into M-mode)
are in SvHSm.
"""

from collections.abc import Sequence

from testgen.asm.csr import gen_csr_read_sigupd
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.sv.access import virtual_address
from testgen.priv.extensions.sv.generate import guest_translation_setup, guest_translation_teardown
from testgen.priv.extensions.sv.page_tables import (
    SV32X4,
    SV39X4,
    SV48X4,
    SV57X4,
    VS_SV32,
    VS_SV39,
    VS_SV48,
    PteExpression,
    PteFlags,
    SvMode,
    create_page_mapping,
    create_page_walk,
    write_pte,
)
from testgen.priv.extensions.sv.Sv import PAGE_PERMS
from testgen.priv.registry import add_priv_test_generator

# Guest accesses: a store and a load of the word at offset 8 of the test page, and a fetch of the ret at
# offset 0.  HLV, HLVX and HSV run in HS-mode and access offset 8 of their address.
OPS = {
    "store": "sw x{data}, 8(x{va})",
    "load": "lw x{data}, 8(x{va})",
    "exec": "jalr ra, 0(x{va})",
    "hsv": "hsv.w x{data}, (x{va})",
    "hlv": "hlv.w x{data}, (x{va})",
    "hlvx": "hlvx.wu x{data}, (x{va})",
}
LOADS = ("load", "hlv", "hlvx")
GUEST_OPS = ("store", "load", "exec")

# Leaves that allow every access; G-stage accesses are user-level
VS_LEAF = PteFlags()
G_LEAF = PteFlags(user=True)

VS_CG = "SvH_vsstage_cg"
G_CG = "SvH_gstage_cg"
TWO_CG = "SvH_twostage_cg"
HLV_CG = "SvH_hlv_cg"
CSR_CG = "SvH_csr_cg"


def begin_chunk(test_data: TestData, split_name: str, title: str, description: str) -> TestChunk:
    """Start a chunk whose data section holds two physical test pages.

    svh_page is an odd 4 KiB page, so no superpage leaf maps it aligned.  It starts with ret, holds the load/store
    word at offset 8 and ends with a nop that straddles the next page, which continues with ret.
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
    """Write menvcfg.ADUE and menvcfg.PBMTE through T-SBI (menvcfgh on RV32)."""
    csr, adue_mask, pbmte_mask = (
        ("CSR_MENVCFG", "MENVCFG_ADUE", "MENVCFG_PBMTE")
        if xlen == 64
        else ("CSR_MENVCFGH", "MENVCFGH_ADUE", "MENVCFGH_PBMTE")
    )
    lines = [f"RVTEST_TSBI_CSR_CLEAR({csr}, {adue_mask} | {pbmte_mask})"]
    bits = " | ".join(mask for mask, on in ((adue_mask, adue), (pbmte_mask, pbmte)) if on)
    if bits:
        lines.append(f"RVTEST_TSBI_CSR_SET({csr}, {bits})")
    return lines


def henvcfg_bits(xlen: int, reg: int, *, adue: int, pbmte: int = 0) -> list[str]:
    """Write henvcfg.ADUE and henvcfg.PBMTE (henvcfgh on RV32)."""
    csr, adue_mask, pbmte_mask = (
        ("henvcfg", "HENVCFG_ADUE", "HENVCFG_PBMTE") if xlen == 64 else ("henvcfgh", "HENVCFGH_ADUE", "HENVCFGH_PBMTE")
    )
    bits = " | ".join(mask for mask, on in ((adue_mask, adue), (pbmte_mask, pbmte)) if on) or "0"
    return set_csr_bits(csr, f"{adue_mask} | {pbmte_mask}", bits, reg)


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
        address = virtual_address(
            sv, va, level, destination=f"x{va_reg}", physical_address="svh_page", scratch=f"x{data}"
        )
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
    size = mode.xlen // 8
    mask = (1 << mode.index_bits(level)) - 1
    offset = f"((({va}) >> {mode.page_offset_bits(level)}) & {mask:#x}) * {size}"
    lines = [
        f"LA(x{reg}, {mode.page_table_label(level)} + {offset})",
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


# VS-stage A/D cases: (menvcfg.ADUE, henvcfg.ADUE, leaf flags, accesses).  Svade faults on A = 0, and on D = 0 for a
# store; Svadu sets A on any access and D on a store.  henvcfg.ADUE is read-only zero while menvcfg.ADUE = 0.
AD_CASES = (
    (0, 1, PteFlags(accessed=False, dirty=False), GUEST_OPS),
    (1, 0, PteFlags(accessed=False, dirty=False), GUEST_OPS),
    (1, 0, PteFlags(dirty=False), GUEST_OPS),
    (1, 1, PteFlags(accessed=False, dirty=False), ("load", "exec")),
    (1, 1, PteFlags(dirty=False), ("store",)),
)


def perm_flags(perm: str, user: bool) -> PteFlags:
    """Leaf flags named by R, W and X letters, or "inv" for an invalid PTE."""
    if perm == "inv":
        return PteFlags(valid=False, user=user)
    return PteFlags(user=user, read="r" in perm, write="w" in perm, execute="x" in perm)


###########################
# VS-stage translation (hgatp = Bare)
###########################


def _t_vs_perm(test_data: TestData, test_chunks: list[TestChunk], vs: SvMode, mode: str) -> None:
    """VS-stage leaf permissions with vsstatus.SUM and vsstatus.MXR in VS-mode or VU-mode."""
    chunk = begin_chunk(
        test_data,
        f"{vs.name}_vs_perm_{mode.lower()}",
        "cp_vsatp_perm, cp_vsatp_sum, cp_vsstatus_mxr",
        f"In {mode}-mode with hgatp = Bare, store, load and fetch through VS-stage leaves with U = 0, 1 and each\n"
        "legal RWX, with vsstatus.SUM = 0, 1 and vsstatus.MXR = 0, 1",
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
        *((f"rsw{rsw}", PteFlags(user=user, extra=(f"({rsw} << 8)",))) for rsw in (1, 2, 3)),
    ]
    if xlen == 64:
        cases.extend((f"reserved_{bit}", PteFlags(user=user, extra=(f"(1 << {bit})",))) for bit in range(54, 61))
        cases.append(("reserved_all", PteFlags(user=user, extra=("(0x7f << 54)",))))
    return cases


def _t_vs_pte(test_data: TestData, test_chunks: list[TestChunk], vs: SvMode) -> None:
    """VS-stage PTE formats, henvcfg.PBMTE with PBMT, and henvcfg.ADUE with A/D bits, in VS-mode."""
    chunk = begin_chunk(
        test_data,
        f"{vs.name}_vs_pte",
        "cp_vsatp_perm, cp_vsatp_pbmt, cp_vsatp_adue",
        "In VS-mode with hgatp = Bare, access through VS-stage leaves that are invalid, a level-0 pointer, or have\n"
        "RSW, reserved or PBMT bits (PBMT with henvcfg.PBMTE = 0, 1), and through leaves with A or D clear\n"
        "with henvcfg.ADUE = 0 (page fault) and 1 (hardware update, checked in the PTE)",
    )
    va = vs.data_va
    reg = test_data.int_regs.get_register()
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
    if vs.xlen == 64:
        code.extend(menvcfg_bits(64, adue=0, pbmte=1))
        for pbmte in (0, 1):
            for pbmt in (1, 2, 3):
                setup = [
                    *henvcfg_bits(64, reg, adue=0, pbmte=pbmte),
                    *map_test_page(test_data, None, vs, vs_flags=PteFlags(extra=(f"({pbmt} << 61)",))),
                ]
                code.extend(
                    guest_access(test_data, VS_CG, "cp_vsatp_pbmt", f"pbmte{pbmte}_pbmt{pbmt}", "VS", va, setup=setup)
                )
    for m_adue, h_adue, flags, ops in AD_CASES:
        name = f"madue{m_adue}_hadue{h_adue}_a{int(flags.accessed)}_d{int(flags.dirty)}_{ops[0]}"
        setup = [
            *menvcfg_bits(vs.xlen, adue=m_adue),
            *henvcfg_bits(vs.xlen, reg, adue=h_adue),
            *map_test_page(test_data, None, vs, vs_flags=flags),
        ]
        code.extend(guest_access(test_data, VS_CG, "cp_vsatp_adue", name, "VS", va, setup=setup, ops=ops))
        code.extend(read_pte(test_data, vs, 0, va, VS_CG, "cp_vsatp_adue", f"{name}_pte"))
    test_data.int_regs.return_register(reg)
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, vs.xlen)])
    test_chunks.append(test_data.end_test_chunk())


###########################
# G-stage translation (vsatp = Bare)
###########################


def _t_g_perm(test_data: TestData, test_chunks: list[TestChunk], g: SvMode, mode: str) -> None:
    """G-stage leaf permissions, which are checked as for U-mode, with sstatus.MXR and vsstatus.MXR."""
    chunk = begin_chunk(
        test_data,
        f"{g.name}_g_perm_{mode.lower()}",
        "cp_hgatp_perm, cp_hgatp_mxr",
        f"In {mode}-mode with vsatp = Bare, store, load and fetch through G-stage leaves with U = 0, 1 and each\n"
        "legal RWX, and load from an execute-only G-stage page with sstatus.MXR = 0, 1 and vsstatus.MXR = 0, 1.\n"
        "Only sstatus.MXR makes it readable",
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


# G-stage A/D cases: (menvcfg.ADUE, leaf flags, accesses)
G_AD_CASES = (
    (0, PteFlags(user=True, accessed=False, dirty=False), GUEST_OPS),
    (0, PteFlags(user=True, dirty=False), GUEST_OPS),
    (1, PteFlags(user=True, accessed=False, dirty=False), ("load", "exec")),
    (1, PteFlags(user=True, dirty=False), ("store",)),
)


def _t_g_pte(test_data: TestData, test_chunks: list[TestChunk], g: SvMode) -> None:
    """G-stage PTE formats, the G bit, misaligned superpages, menvcfg.PBMTE with PBMT and menvcfg.ADUE with A/D."""
    chunk = begin_chunk(
        test_data,
        f"{g.name}_g_pte",
        "cp_hgatp_perm, cp_hgatp_pbmt, cp_hgatp_adue",
        "In VS-mode with vsatp = Bare, access through G-stage leaves that are invalid, a level-0 pointer, have RSW,\n"
        "reserved, G or PBMT bits (PBMT with menvcfg.PBMTE = 0, 1), are misaligned superpages, or have A or D clear\n"
        "with menvcfg.ADUE = 0 (guest-page fault) and 1 (hardware update, checked in the PTE)",
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
    if g.xlen == 64:
        for pbmte in (0, 1):
            for pbmt in (1, 2, 3):
                setup = [
                    *menvcfg_bits(64, adue=0, pbmte=pbmte),
                    *map_test_page(test_data, g, None, g_flags=PteFlags(user=True, extra=(f"({pbmt} << 61)",))),
                ]
                name = f"pbmte{pbmte}_pbmt{pbmt}"
                code.extend(guest_access(test_data, G_CG, "cp_hgatp_pbmt", name, "VS", va, setup=setup))
    for m_adue, flags, ops in G_AD_CASES:
        name = f"madue{m_adue}_a{int(flags.accessed)}_d{int(flags.dirty)}_{ops[0]}"
        setup = [*menvcfg_bits(g.xlen, adue=m_adue), *map_test_page(test_data, g, None, g_flags=flags)]
        code.extend(guest_access(test_data, G_CG, "cp_hgatp_adue", name, "VS", va, setup=setup, ops=ops))
        code.extend(read_pte(test_data, g, 0, va, G_CG, "cp_hgatp_adue", f"{name}_pte"))
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, g.xlen)])
    test_chunks.append(test_data.end_test_chunk())


def _t_gpa_width(test_data: TestData, test_chunks: list[TestChunk], g: SvMode, first_bit: int, gate: str) -> None:
    """Guest physical addresses with one bit set from ``first_bit`` up; bits beyond the mode's width fault."""
    top = g.levels - 1
    width = g.page_offset_bits(top) + g.index_bits(top)
    chunk = begin_chunk(
        test_data,
        f"{g.name}_gpa_width",
        "cp_hgatp_gpa_width",
        f"In VS-mode with vsatp = Bare and hgatp = {g.extension}, load from guest physical addresses with one of\n"
        f"bits {first_bit}-63 set.  Bits below {width} translate through a root-table leaf; bits {width}-63 must be\n"
        "zero, or a guest-page fault occurs",
    )
    code = [f"#ifdef {gate}", *guest_chunk_setup(test_data, g, None, "VS")]
    for bit in range(first_bit, 64):
        setup = []
        if bit < width:
            pte, addr, tmp = test_data.int_regs.get_registers(3)
            setup = [
                *write_pte(
                    g,
                    level=top,
                    flags=PteFlags(user=True),
                    virtual_address=hex(1 << bit),
                    physical_address="svh_page",
                    regs=(pte, addr, tmp),
                    superpage=True,
                ),
                "hfence.gvma",
            ]
            test_data.int_regs.return_registers([pte, addr, tmp])
        code.extend(
            guest_access(
                test_data,
                G_CG,
                "cp_hgatp_gpa_width",
                f"bit{bit}",
                "VS",
                hex(1 << bit),
                setup=setup,
                ops=("load",),
                sv=g,
                level=top,
            )
        )
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, g.xlen), f"#endif // {gate}"])
    test_chunks.append(test_data.end_test_chunk())


def _t_sv32x4_gpa(test_data: TestData, test_chunks: list[TestChunk], g: SvMode, vs: SvMode) -> None:
    """Sv32x4 translates 34-bit guest physical addresses, which only a VS-stage leaf can produce."""
    chunk = begin_chunk(
        test_data,
        f"{g.name}_gpa_width",
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
        f"{g.name}_two_stage_{mode.lower()}",
        "cp_twostage_perm, cp_twostage_mxr",
        f"In {mode}-mode, store, load and fetch where the VS-stage or the G-stage denies the access, and load and\n"
        "fetch from execute-only and read-only pages with vsstatus.MXR = 0, 1 and sstatus.MXR = 0, 1",
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
# leaf of the page, accesses, PTEs checked afterwards)
IMPLICIT_CASES = (
    ("table_invalid", "cp_implicit_gpf", 0, 0, PteFlags(), PteFlags(valid=False, user=True), G_LEAF, GUEST_OPS, ()),
    ("table_xonly", "cp_implicit_gpf", 0, 0, PteFlags(), perm_flags("x", True), G_LEAF, GUEST_OPS, ()),
    ("table_supervisor", "cp_implicit_gpf", 0, 0, PteFlags(), PteFlags(), G_LEAF, GUEST_OPS, ()),
    ("table_svade", "cp_implicit_gpf", 0, 0, PteFlags(), G_NO_AD, G_LEAF, GUEST_OPS, ()),
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


def _t_implicit(test_data: TestData, test_chunks: list[TestChunk], g: SvMode, vs: SvMode) -> None:
    """G-stage checks of implicit VS-stage page-table accesses, and A/D updates in both stages."""
    chunk = begin_chunk(
        test_data,
        f"{g.name}_implicit",
        "cp_implicit_gpf, cp_twostage_adue",
        "In VS-mode, access through a VS-stage leaf table whose G-stage leaf is invalid, execute-only, not user,\n"
        "has A clear, or is read-only while the hardware updates VS-stage A/D bits, and through VS-stage and\n"
        "G-stage leaves with A or D clear, with menvcfg.ADUE and henvcfg.ADUE = 0, 1.  Updated PTEs are checked",
    )
    va = vs.data_va
    ptes = {"vs": (vs, vs.data_va), "table": (g, f"({g.data_va} + 0x1000)"), "page": (g, g.data_va)}
    reg = test_data.int_regs.get_register()
    code = guest_chunk_setup(test_data, g, vs, "VS")
    for name, coverpoint, m_adue, h_adue, vs_flags, table_flags, g_flags, ops, checks in IMPLICIT_CASES:
        setup = [
            *menvcfg_bits(g.xlen, adue=m_adue),
            *henvcfg_bits(g.xlen, reg, adue=h_adue),
            *map_leaf_table(test_data, g, vs, vs_flags, table_flags, g_flags),
        ]
        code.extend(guest_access(test_data, TWO_CG, coverpoint, name, "VS", va, setup=setup, ops=ops))
        for check in checks:
            mode, pte_va = ptes[check]
            code.extend(read_pte(test_data, mode, 0, pte_va, TWO_CG, coverpoint, f"{name}_{check}_pte"))
    test_data.int_regs.return_register(reg)
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, g.xlen)])
    test_chunks.append(test_data.end_test_chunk())


def _t_page_sizes(test_data: TestData, test_chunks: list[TestChunk], g: SvMode, vs: SvMode) -> None:
    """Two-stage translation with every combination of VS-stage and G-stage leaf levels."""
    chunk = begin_chunk(
        test_data,
        f"{g.name}_page_sizes",
        "cp_twostage_perm",
        "In VS-mode, store, load and fetch through each VS-stage page size combined with each G-stage page size",
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
                *virtual_address(
                    g, hex(g_base), g_level, destination=f"x{gpa}", physical_address="svh_page", scratch=f"x{tmp}"
                ),
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


def _t_straddle(test_data: TestData, test_chunks: list[TestChunk], g: SvMode, vs: SvMode) -> None:
    """An instruction fetch that straddles a page boundary faults on the second page."""
    chunk = begin_chunk(
        test_data,
        f"{g.name}_straddle",
        "cp_straddle",
        "In VS-mode, execute a 4-byte instruction in the last halfword of a page whose next page is mapped, has an\n"
        "invalid G-stage leaf (instruction guest-page fault) or an invalid VS-stage leaf (instruction page fault).\n"
        "stval holds the address of the next page",
    )
    next_va = f"({vs.data_va} + 0x1000)"
    next_gpa = f"({g.data_va} + 0x1000)"
    code = ["#ifdef ZCA_SUPPORTED", *guest_chunk_setup(test_data, g, vs, "VS")]
    for name, vs_valid, g_valid in (("mapped", True, True), ("g_invalid", True, False), ("vs_invalid", False, True)):
        pte, addr, tmp = test_data.int_regs.get_registers(3)
        regs = (pte, addr, tmp)
        setup = [
            *map_test_page(test_data, g, vs),
            *write_pte(
                vs,
                level=0,
                flags=PteFlags(valid=vs_valid),
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
        va = f"{vs.data_va} + 0xffe"
        code.extend(guest_access(test_data, TWO_CG, "cp_straddle", name, "VS", va, setup=setup, ops=("exec",)))
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, g.xlen), "#endif // ZCA_SUPPORTED"])
    test_chunks.append(test_data.end_test_chunk())


def _t_hedeleg(test_data: TestData, test_chunks: list[TestChunk], g: SvMode, vs: SvMode, mode: str) -> None:
    """With hedeleg delegating page faults, VS-stage faults go to VS-mode.  Guest-page faults cannot be delegated
    (hedeleg bits 20-23 are read-only zero), so they still go to HS-mode."""
    chunk = begin_chunk(
        test_data,
        f"{g.name}_hedeleg_{mode.lower()}",
        "cp_hedeleg_page_fault, cp_hedeleg_guest_page_fault",
        f"In {mode}-mode with hedeleg[12], [13], [15], [20], [21] and [23] written with 1, access through an invalid\n"
        "and a read-only VS-stage leaf (page faults taken in VS-mode) and an invalid G-stage leaf (guest-page faults\n"
        "taken in HS-mode)",
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


###########################
# HLV, HLVX and HSV in HS-mode
###########################


def _t_hlv(test_data: TestData, test_chunks: list[TestChunk], g: SvMode, vs: SvMode) -> None:
    """HLV, HLVX and HSV privilege from hstatus.SPVP against the VS-stage U bit, and MXR in each stage."""
    chunk = begin_chunk(
        test_data,
        f"{g.name}_hlv",
        "cp_hlv_priv, cp_hlv_mxr",
        "In HS-mode, execute hlv.w, hlvx.wu and hsv.w on VS-stage pages with U = 0, 1, with hstatus.SPVP = 0, 1,\n"
        "vsstatus.SUM = 0, 1 and sstatus.SUM = 0, 1 (ignored), and hlv.w and hlvx.wu on execute-only VS-stage and\n"
        "G-stage pages with vsstatus.MXR = 0, 1 and sstatus.MXR = 0, 1",
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
    for vs_perm, g_perm in (("x", "rwx"), ("rwx", "x")):
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
                code.extend(
                    guest_access(test_data, HLV_CG, "cp_hlv_mxr", name, None, va, setup=setup, ops=("hlv", "hlvx"))
                )
    code.extend(set_csr_bits("hstatus", "HSTATUS_SPVP", "0", reg))
    test_data.int_regs.return_register(reg)
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, g.xlen)])
    test_chunks.append(test_data.end_test_chunk())


###########################
# Svnapot in each stage (RV64)
###########################


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


# PTE.N with PPN[3:0] = 1000 encodes a 64 KiB NAPOT page
NAPOT_BITS = ("PTE_N", "(1 << 13)")


def _t_napot(test_data: TestData, test_chunks: list[TestChunk], g: SvMode, vs: SvMode, mode: str) -> None:
    """64 KiB NAPOT translation in the VS-stage, the G-stage and both."""
    chunk = begin_chunk(
        test_data,
        f"{g.name}_napot_{mode.lower()}",
        "cp_vsatp_napot, cp_hgatp_napot, cp_twostage_napot",
        f"In {mode}-mode, store, load and fetch in pages 0, 2 and 15 of a 64 KiB NAPOT mapping in the VS-stage\n"
        "(hgatp = Bare), in the G-stage (vsatp = Bare) and in both stages",
    )
    chunk.raw_data.extend(NAPOT_PAGES)
    user = mode == "VU"
    vs_base = int(vs.data_va, 16) & ~0xFFFF
    g_base = int(g.data_va, 16) & ~0xFFFF
    code = ["#ifdef SVNAPOT_SUPPORTED"]
    for vs_stage, g_stage, covergroup, name in (
        (vs, None, VS_CG, "vsatp_napot"),
        (None, g, G_CG, "hgatp_napot"),
        (vs, g, TWO_CG, "twostage_napot"),
    ):
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
            code.extend(guest_access(test_data, covergroup, f"cp_{name}", f"{name}_page{page}", mode, va))
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, g.xlen), "#endif // SVNAPOT_SUPPORTED"])
    test_chunks.append(test_data.end_test_chunk())


def _t_napot_reserved(test_data: TestData, test_chunks: list[TestChunk], g: SvMode, vs: SvMode) -> None:
    """Reserved NAPOT encodings fault in either stage: N on a superpage, or PPN[3:0] other than 1000."""
    chunk = begin_chunk(
        test_data,
        f"{g.name}_napot_reserved",
        "cp_vsatp_napot, cp_hgatp_napot",
        "In VS-mode, access through a VS-stage (hgatp = Bare) and a G-stage (vsatp = Bare) leaf with N set on a\n"
        "superpage, or with N set and PPN[3:0] = 0000, 0001, 0010 or 0100",
    )
    chunk.raw_data.extend(NAPOT_PAGES)
    code = ["#ifdef SVNAPOT_SUPPORTED"]
    for stage, covergroup, coverpoint in ((vs, VS_CG, "cp_vsatp_napot"), (g, G_CG, "cp_hgatp_napot")):
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
                for ppn in (0, 1, 2, 4)
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
                guest_access(
                    test_data, covergroup, coverpoint, name, "VS", stage.data_va, setup=setup, sv=stage, level=level
                )
            )
    chunk.code.extend([*code, *guest_chunk_teardown(test_data, g.xlen), "#endif // SVNAPOT_SUPPORTED"])
    test_chunks.append(test_data.end_test_chunk())


###########################
# vsatp, hgatp and satp MODE (RV64), and the henvcfg bits that menvcfg gates
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
        "sv39x4_atp_mode",
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
    code.append("// Identity map the test image in the VS-stage")
    for label in ("rvtest_code_begin", "rvtest_data_begin", "rvtest_sig_end"):
        code.extend(
            write_pte(
                VS_SV39,
                level=2,
                flags=PteFlags(),
                virtual_address=label,
                physical_address=label,
                regs=regs,
                va_is_label=True,
                superpage=True,
            )
        )
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
    """Guest accesses with vsatp and hgatp Bare, and henvcfg.ADUE and PBMTE, which menvcfg gates."""
    chunk = begin_chunk(
        test_data,
        f"{g.name}_bare",
        "cp_stage_both_bare, cp_henvcfg_menvcfg",
        "In VS-mode and VU-mode with vsatp and hgatp Bare, store, load and fetch at a physical address.  In HS-mode,\n"
        "set henvcfg.ADUE and henvcfg.PBMTE with menvcfg.ADUE and menvcfg.PBMTE = 0, where they are read-only\n"
        "zero, and 1",
    )
    code = ["csrw vsatp, zero", "csrw hgatp, zero", "hfence.vvma", "hfence.gvma"]
    for mode in ("VS", "VU"):
        code.extend(
            guest_access(test_data, TWO_CG, "cp_stage_both_bare", mode.lower(), mode, "svh_page", va_is_label=True)
        )
    csr, mask, bits = (
        ("henvcfg", "HENVCFG_ADUE | HENVCFG_PBMTE", 3 << 61)
        if g.xlen == 64
        else ("henvcfgh", "HENVCFGH_ADUE | HENVCFGH_PBMTE", 3 << 29)
    )
    val, check = test_data.int_regs.get_registers(2)
    for m_bits in (0, 1):
        code.extend(
            [
                *menvcfg_bits(g.xlen, adue=m_bits, pbmte=m_bits),
                f"LI(x{val}, {mask})",
                f"csrc {csr}, x{val}",
                test_data.add_testcase(f"menvcfg{m_bits}", "cp_henvcfg_menvcfg", CSR_CG),
                f"csrs {csr}, x{val}",
                gen_csr_read_sigupd(check, (csr, bits), test_data, val),
                f"csrc {csr}, x{val}",
            ]
        )
    test_data.int_regs.return_registers([val, check])
    chunk.code.extend([*code, *menvcfg_bits(g.xlen, adue=0)])
    test_chunks.append(test_data.end_test_chunk())


def _make_svh(test_data: TestData, g: SvMode, vs: SvMode) -> list[TestChunk]:
    test_chunks: list[TestChunk] = []
    _t_bare(test_data, test_chunks, g)
    for mode in ("VS", "VU"):
        _t_vs_perm(test_data, test_chunks, vs, mode)
    _t_vs_pte(test_data, test_chunks, vs)
    for mode in ("VS", "VU"):
        _t_g_perm(test_data, test_chunks, g, mode)
    _t_g_pte(test_data, test_chunks, g)
    for mode in ("VS", "VU"):
        _t_two_stage(test_data, test_chunks, g, vs, mode)
    for mode in ("VS", "VU"):
        _t_hedeleg(test_data, test_chunks, g, vs, mode)
    _t_implicit(test_data, test_chunks, g, vs)
    _t_page_sizes(test_data, test_chunks, g, vs)
    _t_straddle(test_data, test_chunks, g, vs)
    _t_hlv(test_data, test_chunks, g, vs)
    if g.xlen == 32:
        _t_sv32x4_gpa(test_data, test_chunks, g, vs)
        return test_chunks
    for mode in ("VS", "VU"):
        _t_napot(test_data, test_chunks, g, vs, mode)
    _t_napot_reserved(test_data, test_chunks, g, vs)
    _t_atp_mode(test_data, test_chunks)
    for gpa_mode, first_bit, gate in (
        (SV39X4, 37, "UDB_SV39X4_TRANSLATION"),
        (SV48X4, 39, "UDB_SV48X4_TRANSLATION"),
        (SV57X4, 48, "UDB_SV57X4_TRANSLATION"),
    ):
        _t_gpa_width(test_data, test_chunks, gpa_mode, first_bit, gate)
    return test_chunks


@add_priv_test_generator(
    "SvH",
    required_extensions=["H"],
    extra_defines=["#define BOOT_TO_SMODE"],
    # VS and VU traps need the visible trap handler
    params=["TIME_CSR_IMPLEMENTED: true", "SV32X4_TRANSLATION: true", "SV32_VSMODE_TRANSLATION: true"],
)
def make_svh_sv32(test_data: TestData) -> list[TestChunk]:
    return _make_svh(test_data, SV32X4, VS_SV32)


@add_priv_test_generator(
    "SvH",
    required_extensions=["H"],
    extra_defines=["#define BOOT_TO_SMODE"],
    # VS and VU traps need the visible trap handler
    params=["TIME_CSR_IMPLEMENTED: true", "SV39X4_TRANSLATION: true", "SV39_VSMODE_TRANSLATION: true"],
)
def make_svh_sv39(test_data: TestData) -> list[TestChunk]:
    return _make_svh(test_data, SV39X4, VS_SV39)
