##################################
# priv/extensions/sv/SvHZicbo.py
#
# SvHZicbo suite: cache-block operations under two-stage address translation.
# David_Harris@hmc.edu 24 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""SvHZicbo suite: cache-block management and zero instructions from VS-mode and VU-mode.

The suite boots to M-mode and delegates nothing, so the M-mode handler takes every trap.  It checks the
henvcfg CBO enables, the fault that each VS-stage and G-stage PTE gives a CBO, and PMP on the final
address.  A CBO faults like a store.  A cache-block management instruction needs read or write
permission and never checks D; cbo.zero needs write permission and checks D (cmo.adoc).  Boot leaves
menvcfg.ADUE = henvcfg.ADUE = 0, so a clear A or needed D bit raises a fault (Svade behavior).
"""

from collections.abc import Mapping
from dataclasses import replace
from typing import NamedTuple

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ExceptionsZicboCommon import cbo_henvcfg_helper
from testgen.priv.extensions.pmp.helpers import (
    cfg_byte,
    cfg_shift,
    napot_mask_defines,
    set_pmpaddr,
    set_pmpcfg,
    zero_pmp_regs,
)
from testgen.priv.extensions.sv.access import virtual_address
from testgen.priv.extensions.sv.generate import guest_translation_setup, guest_translation_teardown
from testgen.priv.extensions.sv.page_tables import (
    SV32X4,
    SV39X4,
    VS_SV32,
    VS_SV39,
    PteExpression,
    PteFlags,
    SvMode,
    create_page_mapping,
    write_pte,
)
from testgen.priv.registry import add_priv_test_generator

_CG = "SvHZicbo_cg"
_ENVCFG_CG = "SvHZicbo_envcfg_cg"
_OPS = {"zicbom": ("cbo.clean", "cbo.flush", "cbo.inval"), "zicboz": ("cbo.zero",)}
_FIELDS = {"zicbom": ("cbie", "cbcfe"), "zicboz": ("cbze",)}
_DATA = "svhzicbo_data"
_DATA_REGION = [".p2align 12", f"{_DATA}:", ".fill 1024, 4, 0x0C0B0000"]
# PMP entry 0 is a NAPOT region that covers the 4 KiB test page, which holds whole cache blocks; the last entry is
# the background region
_PMP_GATE = "UDB_NUM_PMP_ENTRIES > 1 && defined(UDB_PMP_NAPOT_SUPPORTED) && UDB_PMP_GRANULARITY <= 10"


class _Chunk(NamedTuple):
    """The CBO family and translation modes of one chunk, and the register that holds each case's guest address."""

    family: str
    g: SvMode
    vs: SvMode
    gva: int


def _mapping(
    test_data: TestData,
    stage: SvMode,
    level: int,
    flags: PteExpression,
    pa: str = _DATA,
    *,
    va: str | None = None,
    superpage: bool | None = None,
    walk_overrides: Mapping[int, PteExpression] | None = None,
) -> list[str]:
    """A walk and leaf for ``va``, by default stage.data_va.  A physical address other than the test data is a
    constant."""
    pte, addr, tmp = test_data.int_regs.get_registers(3)
    lines = create_page_mapping(
        stage,
        leaf_level=level,
        leaf_flags=flags,
        virtual_address=va or stage.data_va,
        physical_address=pa,
        walk_overrides=walk_overrides,
        superpage=superpage,
        regs=(pte, addr, tmp),
        pa_is_label=pa == _DATA,
    )
    test_data.int_regs.return_registers([pte, addr, tmp])
    return lines


def _pte(
    test_data: TestData, stage: SvMode, level: int, flags: PteExpression, va: str, pa: str, *, superpage: bool = False
) -> list[str]:
    """One PTE of ``stage`` for ``va`` pointing at the constant ``pa``."""
    pte, addr, tmp = test_data.int_regs.get_registers(3)
    lines = write_pte(
        stage,
        level=level,
        flags=flags,
        virtual_address=va,
        physical_address=pa,
        regs=(pte, addr, tmp),
        pa_is_label=False,
        superpage=superpage,
    )
    test_data.int_regs.return_registers([pte, addr, tmp])
    return lines


def _vs_identity(test_data: TestData, c: _Chunk, mode: str) -> list[str]:
    """The VS-stage superpage leaf that maps g.data_va to the same guest physical address."""
    flags = PteFlags(user=mode == "vu")
    return _pte(test_data, c.vs, c.vs.levels - 1, flags, c.g.data_va, c.g.data_va, superpage=True)


def _case(
    test_data: TestData,
    c: _Chunk,
    mode: str,
    name: str,
    coverpoint: str,
    expected: str,
    ptes: list[str],
    *,
    stage: SvMode,
    level: int,
    offset: str = _DATA,
    guest: tuple[list[str], list[str]] = ([], []),
    ifdef: str | None = None,
) -> list[str]:
    """Write ``ptes``, form the guest virtual address of ``offset`` in ``stage``'s mapping at ``level``, and run the
    CBOs in ``mode`` between the ``guest`` setup and cleanup lines.  M-mode checks what cbo.zero did to the test
    data."""
    addr, val = test_data.int_regs.get_registers(2)
    check = c.family == "zicboz" and offset == _DATA
    lines = [
        f"// {mode.upper()}-mode, {stage.name} level {level}, {name}: {expected}",
        *ptes,
        "hfence.gvma",
        "hfence.vvma",
        *virtual_address(
            stage,
            stage.data_va,
            level,
            destination=f"x{c.gva}",
            physical_address=offset,
            physical_address_is_label=offset == _DATA,
            merge_sv32_base_page=True,
            scratch=f"x{addr}",
        ),
    ]
    if check:
        lines.extend([f"LA(x{addr}, {_DATA})", f"LI(x{val}, 0x0C0B0000)", f"sw x{val}, 0(x{addr})"])
    lines.extend([f"RVTEST_TSBI_GOTO_{mode.upper()}MODE", *guest[0]])
    for op in _OPS[c.family]:
        lines.extend(
            [
                test_data.add_testcase(f"{mode}_{stage.name}_l{level}_{name}_{op}", coverpoint, _CG),
                f"{op} (x{c.gva})",
            ]
        )
    lines.extend([*guest[1], "RVTEST_TSBI_GOTO_MMODE"])
    if check:
        lines.extend([f"lw x{val}, 0(x{addr})", write_sigupd(val, test_data)])
    test_data.int_regs.return_registers([addr, val])
    return [f"#ifdef {ifdef}", *lines, "#endif"] if ifdef else lines


def _leaf_cases(
    test_data: TestData, c: _Chunk, mode: str, stage: SvMode, level: int, flags: PteFlags, fault: str, prefix: list[str]
) -> list[str]:
    """The cases that both stages share: each permission of the leaf at ``level`` (``flags`` when valid), a pointer in
    place of a kilopage leaf, reserved bits in the non-leaf PTE above, and a misaligned superpage.  ``prefix``
    precedes each case's page-table writes."""
    zero = c.family == "zicboz"
    reserved = f"{fault}: W without R is reserved"
    leaves = [
        ("valid", "no fault", flags),
        ("v0", fault, replace(flags, valid=False)),
        ("w", reserved, replace(flags, read=False, execute=False)),
        ("wx", reserved, replace(flags, read=False)),
        ("rx", fault if zero else "no fault: a load is permitted", replace(flags, write=False)),
        *([("x", fault, replace(flags, read=False, write=False))] if zero else []),
        ("a0", fault, replace(flags, accessed=False)),
        ("d0", fault if zero else "no fault: D is not checked", replace(flags, dirty=False)),
    ]
    if level == 0:
        pointer = PteFlags.nonleaf(*(["PTE_U"] if flags.user else []))
        leaves.append(("pointer", f"{fault}: a pointer in place of a leaf", pointer))
    cases = [(name, expected, _mapping(test_data, stage, level, leaf)) for name, expected, leaf in leaves]
    if level < stage.levels - 1:
        for bit in ("D", "A", "U"):
            ptes = _mapping(test_data, stage, level, flags, walk_overrides={level + 1: PteFlags.nonleaf(f"PTE_{bit}")})
            cases.append((f"nonleaf_{bit.lower()}", f"{fault}: {bit} is reserved in a non-leaf PTE", ptes))
    cp = f"cp_{stage.stage}_pte"
    lines = []
    for name, expected, ptes in cases:
        lines.extend(_case(test_data, c, mode, name, cp, expected, [*prefix, *ptes], stage=stage, level=level))
    if level > 0:
        ptes = [*prefix, *_mapping(test_data, stage, level, flags, superpage=False)]
        lines.extend(_case(test_data, c, mode, "misaligned", cp, fault, ptes, stage=stage, level=level, offset="0x0"))
    return lines


def _vs_cases(test_data: TestData, c: _Chunk, mode: str) -> list[str]:
    """VS-stage PTE cases at each level.  The G-stage identity maps the test data."""
    vs, g = c.vs, c.g
    user = PteFlags(user=mode == "vu")
    fault = "store page fault"
    sum_reg = test_data.int_regs.get_register()
    top = g.page_offset_bits(g.levels - 1)
    # The guest physical address of the G-stage root superpage that holds g.data_va
    g_base = f"{(int(g.data_va, 16) >> top) << top:#x}"
    unmapped_gpa = _pte(test_data, g, g.levels - 1, "0", g.data_va, "0")
    lines = []
    for level in vs.levels_desc:
        lines.extend(_leaf_cases(test_data, c, mode, vs, level, user, fault, []))
        if mode == "vu":
            expected = f"{fault}: VU-mode cannot access a supervisor page"
            ptes = _mapping(test_data, vs, level, PteFlags())
            lines.extend(_case(test_data, c, mode, "u0", "cp_vs_pte", expected, ptes, stage=vs, level=level))
        else:
            user_page = _mapping(test_data, vs, level, PteFlags(user=True))
            expected = f"{fault}: VS-mode cannot access a user page with vsstatus.SUM = 0"
            sum_on = [f"LI(x{sum_reg}, SSTATUS_SUM)", f"csrs sstatus, x{sum_reg}"]
            lines.extend(
                [
                    *_case(test_data, c, mode, "u1_sum0", "cp_vs_pte", expected, user_page, stage=vs, level=level),
                    *_case(
                        test_data,
                        c,
                        mode,
                        "u1_sum1",
                        "cp_vs_sum",
                        "no fault: vsstatus.SUM = 1",
                        user_page,
                        stage=vs,
                        level=level,
                        guest=(sum_on, [f"csrc sstatus, x{sum_reg}"]),
                    ),
                ]
            )
        lines.extend(
            _case(
                test_data,
                c,
                mode,
                "leaf_gpa_unmapped",
                "cp_vs_gpa",
                "store guest-page fault on the final guest physical address",
                [*_mapping(test_data, vs, level, user, g.data_va), *unmapped_gpa],
                stage=vs,
                level=level,
            )
        )
        if level < vs.levels - 1:
            # The non-leaf PTE above the leaf points at a table at guest physical address g_base, which is unmapped,
            # or which a G-stage kilopage maps to the access-fault region
            table = [
                *_mapping(test_data, vs, level, user),
                *_pte(test_data, vs, level + 1, PteFlags.nonleaf(), vs.data_va, g_base),
            ]
            faulting_table = _mapping(test_data, g, 0, PteFlags(user=True), "RVMODEL_ACCESS_FAULT_ADDRESS", va=g_base)
            lines.extend(
                [
                    *_case(
                        test_data,
                        c,
                        mode,
                        "nonleaf_gpa_unmapped",
                        "cp_vs_gpa",
                        "store guest-page fault on reading a table at an unmapped guest physical address",
                        [*table, *unmapped_gpa],
                        stage=vs,
                        level=level,
                    ),
                    *_case(
                        test_data,
                        c,
                        mode,
                        "nonleaf_gpa_access_fault",
                        "cp_vs_gpa",
                        "store access fault on reading a table whose supervisor physical address faults",
                        [*table, *faulting_table],
                        stage=vs,
                        level=level,
                        ifdef="RVMODEL_ACCESS_FAULT_ADDRESS",
                    ),
                ]
            )
    test_data.int_regs.return_register(sum_reg)
    return lines


def _g_cases(test_data: TestData, c: _Chunk, mode: str) -> list[str]:
    """G-stage PTE cases at each level, reached through a VS-stage identity superpage."""
    g = c.g
    user = PteFlags(user=True)
    fault = "store guest-page fault"
    identity = _vs_identity(test_data, c, mode)
    lines = []
    for level in g.levels_desc:
        lines.extend(
            [
                *_leaf_cases(test_data, c, mode, g, level, user, fault, identity),
                *_case(
                    test_data,
                    c,
                    mode,
                    "u0",
                    "cp_g_pte",
                    f"{fault}: every G-stage access is a user access",
                    [*identity, *_mapping(test_data, g, level, PteFlags())],
                    stage=g,
                    level=level,
                ),
                *_case(
                    test_data,
                    c,
                    mode,
                    "leaf_access_fault",
                    "cp_g_pa",
                    "store access fault on the final supervisor physical address",
                    [*identity, *_mapping(test_data, g, level, user, "RVMODEL_ACCESS_FAULT_ADDRESS")],
                    stage=g,
                    level=level,
                    offset="RVMODEL_ACCESS_FAULT_ADDRESS",
                    ifdef="RVMODEL_ACCESS_FAULT_ADDRESS",
                ),
            ]
        )
    return lines


def _g_walk_cases(test_data: TestData, c: _Chunk, mode: str) -> list[str]:
    """A non-leaf G-stage PTE that points at the access-fault region, at each level."""
    # TODO: Sail writes mtval2 = GPA >> 2 on these access faults; hypervisor.adoc requires mtval2 = 0
    g = c.g
    lines = []
    for level in range(g.levels - 2, -1, -1):
        ptes = [
            *_vs_identity(test_data, c, mode),
            *_mapping(test_data, g, level, PteFlags(user=True)),
            *_pte(test_data, g, level + 1, PteFlags.nonleaf(), g.data_va, "RVMODEL_ACCESS_FAULT_ADDRESS"),
        ]
        lines.extend(
            _case(
                test_data,
                c,
                mode,
                "nonleaf_access_fault",
                "cp_g_pa",
                "store access fault on reading a G-stage table",
                ptes,
                stage=g,
                level=level,
                ifdef="RVMODEL_ACCESS_FAULT_ADDRESS",
            )
        )
    return lines


def _pmp_cases(test_data: TestData, c: _Chunk, mode: str) -> list[str]:
    """PMP denies the test page (XWR = 000), then allows only reads (XWR = 001), through both stages' kilopages.

    set_pmpaddr clobbers x5 and x6 before each case loads its registers.
    """
    lines = []
    for xwr in ("000", "001"):
        region = [
            *zero_pmp_regs(),
            *set_pmpaddr("napot", 0, _DATA),
            *set_pmpcfg(0, cfg_byte(f"0{xwr}", "napot", cfg_shift(0))),
            "sfence.vma",
        ]
        expected = "store access fault" if c.family == "zicboz" or xwr == "000" else "no fault: reads are allowed"
        vs_ptes = [*region, *_mapping(test_data, c.vs, 0, PteFlags(user=mode == "vu"))]
        g_ptes = [*region, *_vs_identity(test_data, c, mode), *_mapping(test_data, c.g, 0, PteFlags(user=True))]
        lines.extend(
            [
                *_case(test_data, c, mode, f"pmp{xwr}", "cp_pmp", expected, vs_ptes, stage=c.vs, level=0),
                *_case(test_data, c, mode, f"pmp{xwr}", "cp_pmp", expected, g_ptes, stage=c.g, level=0),
            ]
        )
    return [*lines, *zero_pmp_regs()]


# (file name, coverpoints, description, gate, cases for one mode)
_SECTIONS = (
    (
        "vs",
        "cp_vs_pte, cp_vs_sum, cp_vs_gpa",
        "Each VS-stage PTE, and VS-stage PTEs at unmapped or faulting guest physical addresses",
        None,
        _vs_cases,
    ),
    (
        "g",
        "cp_g_pte, cp_g_pa",
        "Each G-stage PTE, and a G-stage leaf at a faulting supervisor physical address",
        None,
        _g_cases,
    ),
    ("g_walk", "cp_g_pa", "A non-leaf G-stage PTE at a faulting supervisor physical address", None, _g_walk_cases),
    ("pmp", "cp_pmp", "PMP denies the test page, then allows only reads", _PMP_GATE, _pmp_cases),
)


def _make_svhzicbo(test_data: TestData, g: SvMode, vs: SvMode, family: str) -> list[TestChunk]:
    chunks = []
    for name, title, description, gate, cases in _SECTIONS:
        tc = test_data.begin_test_chunk(f"{g.name}_{family}_{name}")
        tc.section_header = comment_banner(title, f"{description}, for {', '.join(_OPS[family])} from VS and VU")
        c = _Chunk(family, g, vs, test_data.int_regs.get_register())
        # Boot enables the CBOs in menvcfg and henvcfg; a boot to M-mode leaves senvcfg, which VU-mode uses, alone
        body = [f"LI(x{c.gva}, SENVCFG_CBIE | SENVCFG_CBCFE | SENVCFG_CBZE)", f"csrs senvcfg, x{c.gva}"]
        if name == "pmp":
            body.extend([*napot_mask_defines(12), "RVTEST_PMP_SET_BACKGROUND x4"])
        for mode in ("vs", "vu"):
            body.extend(
                [
                    *guest_translation_setup(test_data, g, vs, f"{mode.upper()}mode"),
                    *cases(test_data, c, mode),
                    *guest_translation_teardown(test_data),
                ]
            )
        test_data.int_regs.return_register(c.gva)
        tc.code.extend([f"#if {gate}", *body, "#endif"] if gate else body)
        tc.raw_data.extend(_DATA_REGION)
        chunks.append(test_data.end_test_chunk())
    return chunks


def _make_henvcfg(test_data: TestData, family: str) -> list[TestChunk]:
    """The family's CBOs in VS-mode and VU-mode across the menvcfg, henvcfg and senvcfg enables."""
    tc = test_data.begin_test_chunk(f"{family}_henvcfg")
    for field in _FIELDS[family]:
        for mode in ("VS", "VU"):
            tc.code.extend(cbo_henvcfg_helper(test_data, _ENVCFG_CG, field, mode=mode))
    return [test_data.end_test_chunk()]


@add_priv_test_generator(
    "SvHZicbo",
    required_extensions=["Sm", "H", "Zicbom"],
    extra_defines=["#define BOOT_TO_MMODE"],
    # VS and VU traps need the visible trap handler
    params=["TIME_CSR_IMPLEMENTED: true"],
)
def make_svhzicbo_zicbom_henvcfg(test_data: TestData) -> list[TestChunk]:
    return _make_henvcfg(test_data, "zicbom")


@add_priv_test_generator(
    "SvHZicbo",
    required_extensions=["Sm", "H", "Zicboz"],
    extra_defines=["#define BOOT_TO_MMODE"],
    # VS and VU traps need the visible trap handler
    params=["TIME_CSR_IMPLEMENTED: true"],
)
def make_svhzicbo_zicboz_henvcfg(test_data: TestData) -> list[TestChunk]:
    return _make_henvcfg(test_data, "zicboz")


@add_priv_test_generator(
    "SvHZicbo",
    required_extensions=["Sm", "H", "Zicbom"],
    extra_defines=["#define BOOT_TO_MMODE"],
    params=["TIME_CSR_IMPLEMENTED: true", "SV39X4_TRANSLATION: true", "SV39_VSMODE_TRANSLATION: true"],
)
def make_svhzicbo_sv39x4_zicbom(test_data: TestData) -> list[TestChunk]:
    return _make_svhzicbo(test_data, SV39X4, VS_SV39, "zicbom")


@add_priv_test_generator(
    "SvHZicbo",
    required_extensions=["Sm", "H", "Zicboz"],
    extra_defines=["#define BOOT_TO_MMODE"],
    params=["TIME_CSR_IMPLEMENTED: true", "SV39X4_TRANSLATION: true", "SV39_VSMODE_TRANSLATION: true"],
)
def make_svhzicbo_sv39x4_zicboz(test_data: TestData) -> list[TestChunk]:
    return _make_svhzicbo(test_data, SV39X4, VS_SV39, "zicboz")


@add_priv_test_generator(
    "SvHZicbo",
    required_extensions=["Sm", "H", "Zicbom"],
    extra_defines=["#define BOOT_TO_MMODE"],
    params=["TIME_CSR_IMPLEMENTED: true", "SV32X4_TRANSLATION: true", "SV32_VSMODE_TRANSLATION: true"],
)
def make_svhzicbo_sv32x4_zicbom(test_data: TestData) -> list[TestChunk]:
    return _make_svhzicbo(test_data, SV32X4, VS_SV32, "zicbom")


@add_priv_test_generator(
    "SvHZicbo",
    required_extensions=["Sm", "H", "Zicboz"],
    extra_defines=["#define BOOT_TO_MMODE"],
    params=["TIME_CSR_IMPLEMENTED: true", "SV32X4_TRANSLATION: true", "SV32_VSMODE_TRANSLATION: true"],
)
def make_svhzicbo_sv32x4_zicboz(test_data: TestData) -> list[TestChunk]:
    return _make_svhzicbo(test_data, SV32X4, VS_SV32, "zicboz")
