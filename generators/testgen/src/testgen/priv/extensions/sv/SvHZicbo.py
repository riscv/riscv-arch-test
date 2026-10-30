##################################
# priv/extensions/sv/SvHZicbo.py
#
# Sv HZicbo group: cache-block operations under two-stage address translation.
# David_Harris@hmc.edu 24 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Sv HZicbo group: cache-block management and zero instructions from VS-mode and VU-mode.

The group boots to HS-mode with hedeleg clear, so the HS-mode handler takes every guest trap.  It checks the
henvcfg CBO enables and the fault that each VS-stage and G-stage PTE gives a CBO; the PMP suite's HSvZicbo group
checks PMP on the final address.  A CBO faults like a store.  A cache-block management instruction needs read or
write permission and never checks D; cbo.zero needs write permission and checks D (cmo.adoc).  Boot leaves
menvcfg.ADUE = 0, which makes henvcfg.ADUE read-only zero, so a clear A or needed D bit raises a fault (Svade
behavior).
"""

import itertools
from collections.abc import Callable, Mapping
from typing import NamedTuple

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.asm.tsbi import tsbi_call
from testgen.data.random import random_int
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.exceptions.ExceptionsZicboCommon import CBO_FIELDS, CBO_ZERO_FILL, cbo_test
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
    guest_table_data,
    write_pte,
)
from testgen.priv.extensions.sv.SvZicbo import cbo_leaves
from testgen.priv.registry import add_priv_test_generator

OPS = {"zicbom": ("cbo.clean", "cbo.flush", "cbo.inval"), "zicboz": ("cbo.zero",)}
_FIELDS = {"zicbom": ("cbie", "cbcfe"), "zicboz": ("cbze",)}
DATA = "svhzicbo_data"
_DATA_REGION = [".p2align 12", f"{DATA}:", f".fill 1024, 4, {CBO_ZERO_FILL:#x}"]


class Chunk(NamedTuple):
    """One chunk's CBO family, translation modes, covergroup and home mode ("S" or "M", which checks the results), and
    the register that holds each case's guest address."""

    family: str
    g: SvMode
    vs: SvMode
    covergroup: str
    home: str
    gva: int


def mapping(
    test_data: TestData,
    stage: SvMode,
    level: int,
    flags: PteExpression,
    pa: str = DATA,
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
        pa_is_label=pa == DATA,
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


def vs_identity(test_data: TestData, c: Chunk, mode: str) -> list[str]:
    """The VS-stage superpage leaf that maps g.data_va to the same guest physical address."""
    flags = PteFlags(user=mode == "vu")
    return _pte(test_data, c.vs, c.vs.levels - 1, flags, c.g.data_va, c.g.data_va, superpage=True)


def case(
    test_data: TestData,
    c: Chunk,
    mode: str,
    name: str,
    coverpoint: str,
    expected: str,
    ptes: list[str],
    *,
    stage: SvMode,
    level: int,
    offset: str = DATA,
    va: str | None = None,
    guest: tuple[list[str], list[str]] = ([], []),
    ifdef: str | None = None,
) -> list[str]:
    """Write ``ptes``, form the guest virtual address of ``offset`` in the mapping of ``va`` (by default
    stage.data_va) at ``level``, and run the CBOs in ``mode`` between the ``guest`` setup and cleanup lines.  The home
    mode checks what cbo.zero did to the test data."""
    addr, val = test_data.int_regs.get_registers(2)
    check = c.family == "zicboz" and offset == DATA
    lines = [
        f"// {mode.upper()}-mode, {stage.name} level {level}, {name}: {expected}",
        *ptes,
        "hfence.gvma",
        "hfence.vvma",
        *virtual_address(
            stage,
            va or stage.data_va,
            level,
            destination=c.gva,
            physical_address=offset,
            physical_address_is_label=offset == DATA,
            merge_sv32_base_page=True,
            scratch=addr,
        ),
    ]
    if check:
        lines.extend([f"LA(x{addr}, {DATA})", f"LI(x{val}, {CBO_ZERO_FILL:#x})", f"sw x{val}, 0(x{addr})"])
    lines.extend([f"RVTEST_TSBI_GOTO_{mode.upper()}MODE", *guest[0]])
    for op in OPS[c.family]:
        lines.extend(
            [
                test_data.add_testcase(f"{mode}_{stage.name}_l{level}_{name}_{op}", coverpoint, c.covergroup),
                f"{op} (x{c.gva})",
            ]
        )
    lines.extend([*guest[1], f"RVTEST_TSBI_GOTO_{c.home}MODE"])
    if check:
        lines.extend([f"lw x{val}, 0(x{addr})", write_sigupd(val, test_data)])
    test_data.int_regs.return_registers([addr, val])
    return [f"#ifdef {ifdef}", *lines, "#endif"] if ifdef else lines


def _leaf_cases(
    test_data: TestData, c: Chunk, mode: str, stage: SvMode, level: int, flags: PteFlags, fault: str, prefix: list[str]
) -> list[str]:
    """The cases that both stages share: each permission of the leaf at ``level`` (``flags`` when valid), a pointer in
    place of a kilopage leaf, reserved bits in the non-leaf PTE above, and a misaligned superpage.  ``prefix``
    precedes each case's page-table writes.

    The reserved R/W/X leaves need no S1P12P0_OR_LATER_SUPPORTED guard: H requires privileged architecture 1.12 or
    later."""
    leaves = [
        ("valid", "no fault", flags),
        *(
            (leaf.name, f"{fault if leaf.faults else 'no fault'}: {leaf.description}", leaf.flags)
            for leaf in cbo_leaves(c.family, flags)
        ),
    ]
    if level == 0:
        pointer = PteFlags.nonleaf(*(["PTE_U"] if flags.user else []))
        leaves.append(("pointer", f"{fault}: a pointer in place of a leaf", pointer))
    cases = [(name, expected, mapping(test_data, stage, level, leaf)) for name, expected, leaf in leaves]
    if level < stage.levels - 1:
        for bit in ("D", "A", "U"):
            ptes = mapping(test_data, stage, level, flags, walk_overrides={level + 1: PteFlags.nonleaf(f"PTE_{bit}")})
            cases.append((f"nonleaf_{bit.lower()}", f"{fault}: {bit} is reserved in a non-leaf PTE", ptes))
    cp = f"cp_{stage.stage}_pte"
    lines = []
    for name, expected, ptes in cases:
        lines.extend(case(test_data, c, mode, name, cp, expected, [*prefix, *ptes], stage=stage, level=level))
    if level > 0:
        ptes = [*prefix, *mapping(test_data, stage, level, flags, superpage=False)]
        lines.extend(case(test_data, c, mode, "misaligned", cp, fault, ptes, stage=stage, level=level, offset="0x0"))
    return lines


def _vs_cases(test_data: TestData, c: Chunk, mode: str) -> list[str]:
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
            ptes = mapping(test_data, vs, level, PteFlags())
            lines.extend(case(test_data, c, mode, "u0", "cp_vs_pte", expected, ptes, stage=vs, level=level))
        else:
            user_page = mapping(test_data, vs, level, PteFlags(user=True))
            expected = f"{fault}: VS-mode cannot access a user page with vsstatus.SUM = 0"
            sum_on = [f"LI(x{sum_reg}, SSTATUS_SUM)", f"csrs sstatus, x{sum_reg}"]
            lines.extend(
                [
                    *case(test_data, c, mode, "u1_sum0", "cp_vs_pte", expected, user_page, stage=vs, level=level),
                    *case(
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
            case(
                test_data,
                c,
                mode,
                "leaf_gpa_unmapped",
                "cp_vs_gpa",
                "store guest-page fault on the final guest physical address",
                [*mapping(test_data, vs, level, user, g.data_va), *unmapped_gpa],
                stage=vs,
                level=level,
            )
        )
        if level < vs.levels - 1:
            # The non-leaf PTE above the leaf points at a table at guest physical address g_base, which is unmapped,
            # or which a G-stage kilopage maps to the page of the access-fault region.  There, the access-fault case's
            # index selects a PTE inside the region.
            table = [
                *mapping(test_data, vs, level, user),
                *_pte(test_data, vs, level + 1, PteFlags.nonleaf(), vs.data_va, g_base),
            ]
            faulting_table = mapping(test_data, g, 0, PteFlags(user=True), vs.access_fault_pte_address(), va=g_base)
            lines.extend(
                [
                    *case(
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
                    *case(
                        test_data,
                        c,
                        mode,
                        "nonleaf_gpa_access_fault",
                        "cp_vs_gpa",
                        "store access fault on reading a table whose supervisor physical address faults",
                        [*table, *faulting_table],
                        stage=vs,
                        level=level,
                        va=vs.access_fault_walk_va(vs.data_va, level),
                        ifdef="RVMODEL_ACCESS_FAULT_ADDRESS",
                    ),
                ]
            )
    test_data.int_regs.return_register(sum_reg)
    return lines


def _g_cases(test_data: TestData, c: Chunk, mode: str) -> list[str]:
    """G-stage PTE cases at each level, reached through a VS-stage identity superpage, and a non-leaf G-stage PTE that
    points at the page of the access-fault region, with an index there that selects a PTE inside the region."""
    g = c.g
    user = PteFlags(user=True)
    fault = "store guest-page fault"
    identity = vs_identity(test_data, c, mode)
    lines = []
    for level in g.levels_desc:
        lines.extend(
            [
                *_leaf_cases(test_data, c, mode, g, level, user, fault, identity),
                *case(
                    test_data,
                    c,
                    mode,
                    "u0",
                    "cp_g_pte",
                    f"{fault}: every G-stage access is a user access",
                    [*identity, *mapping(test_data, g, level, PteFlags())],
                    stage=g,
                    level=level,
                ),
                *case(
                    test_data,
                    c,
                    mode,
                    "leaf_access_fault",
                    "cp_g_pa",
                    "store access fault on the final supervisor physical address",
                    [*identity, *mapping(test_data, g, level, user, "RVMODEL_ACCESS_FAULT_ADDRESS")],
                    stage=g,
                    level=level,
                    offset="RVMODEL_ACCESS_FAULT_ADDRESS",
                    ifdef="RVMODEL_ACCESS_FAULT_ADDRESS",
                ),
            ]
        )
    for level in range(g.levels - 2, -1, -1):
        ptes = [
            *identity,
            *mapping(test_data, g, level, user),
            *_pte(test_data, g, level + 1, PteFlags.nonleaf(), g.data_va, g.access_fault_pte_address()),
        ]
        lines.extend(
            case(
                test_data,
                c,
                mode,
                "nonleaf_access_fault",
                "cp_g_pa",
                "store access fault on reading a G-stage table",
                ptes,
                stage=g,
                level=level,
                va=g.access_fault_walk_va(g.data_va, level),
                ifdef="RVMODEL_ACCESS_FAULT_ADDRESS",
            )
        )
    return lines


# (file name, coverpoints, description, cases for one mode)
_SECTIONS = (
    (
        "vs",
        "cp_vs_pte, cp_vs_sum, cp_vs_gpa",
        "Each VS-stage PTE, and VS-stage PTEs at unmapped or faulting guest physical addresses",
        _vs_cases,
    ),
    (
        "g",
        "cp_g_pte, cp_g_pa",
        "Each G-stage PTE, and G-stage leaf and non-leaf PTEs at faulting supervisor physical addresses",
        _g_cases,
    ),
)


def make_chunk(
    test_data: TestData,
    family: str,
    g: SvMode,
    vs: SvMode,
    *,
    group: str,
    covergroup: str,
    home: str,
    section: tuple[str, str, str, Callable[[TestData, Chunk, str], list[str]]],
    setup: tuple[str, ...] = (),
) -> TestChunk:
    """One file of ``group``, with a section's cases from VS-mode and VU-mode, after ``setup``.

    section is (file name, coverpoints, description, cases for one mode).  The CBOs are enabled in henvcfg and
    senvcfg, and cleared there at the end; boot enables them in menvcfg.
    """
    name, title, description, cases = section
    tc = test_data.begin_test_chunk(f"{group}_{g.name}_{family}_{name}")
    tc.section_header = comment_banner(title, f"{description}, for {', '.join(OPS[family])} from VS and VU")
    chunk = Chunk(family, g, vs, covergroup, home, test_data.int_regs.get_register())
    body = [
        f"LI(x{chunk.gva}, HENVCFG_CBIE | HENVCFG_CBCFE | HENVCFG_CBZE)",
        f"csrs henvcfg, x{chunk.gva}",
        f"LI(x{chunk.gva}, SENVCFG_CBIE | SENVCFG_CBCFE | SENVCFG_CBZE)",
        f"csrs senvcfg, x{chunk.gva}",
        *setup,
    ]
    for mode in ("vs", "vu"):
        body.extend(
            [
                *guest_translation_setup(test_data, g, vs, f"{mode.upper()}mode"),
                *cases(test_data, chunk, mode),
                *guest_translation_teardown(test_data),
            ]
        )
    body.extend(
        [
            f"LI(x{chunk.gva}, HENVCFG_CBIE | HENVCFG_CBCFE | HENVCFG_CBZE)",
            f"csrc henvcfg, x{chunk.gva}",
            f"LI(x{chunk.gva}, SENVCFG_CBIE | SENVCFG_CBCFE | SENVCFG_CBZE)",
            f"csrc senvcfg, x{chunk.gva}",
        ]
    )
    test_data.int_regs.return_register(chunk.gva)
    tc.code.extend(body)
    tc.raw_data.extend([*_DATA_REGION, *guest_table_data()])
    return test_data.end_test_chunk()


def _make_svhzicbo(test_data: TestData, g: SvMode, vs: SvMode, family: str) -> list[TestChunk]:
    return [
        make_chunk(test_data, family, g, vs, group="HZicbo", covergroup="Sv_HZicbo_cg", home="S", section=section)
        for section in _SECTIONS
    ]


def _henvcfg_cases(test_data: TestData, field: str, mode: str) -> list[str]:
    """Execute ``field``'s instructions in VS-mode or VU-mode for each value of menvcfg, henvcfg and, in VU-mode,
    senvcfg.  Runs from HS-mode, with vsatp and hgatp Bare; menvcfg is written through T-SBI.

    A field that menvcfg disables raises an illegal-instruction exception; otherwise one that henvcfg, or
    senvcfg in VU-mode, disables raises a virtual-instruction exception (cmo.adoc, "CSR controls").  When
    cbo.inval is enabled and any of the CBIE fields is 01, it performs a flush (hypervisor.adoc, henvcfg CBIE),
    so a load after it returns the data stored before it.
    """
    cfg = CBO_FIELDS[field]
    field_mask = ((1 << len(cfg.bins[0])) - 1) << cfg.shift
    csrs = ["menvcfg", "henvcfg", *(["senvcfg"] if mode == "VU" else [])]
    coverpoint = f"cp_{field}_{mode.lower()}"
    addr_reg, cfg_reg, mask_reg, val_reg = test_data.int_regs.get_registers(4)
    lines = [
        comment_banner(
            coverpoint,
            f"Exercise {', '.join(cfg.instrs)} in {mode}-mode across {', '.join(f'{csr}.{field}' for csr in csrs)}",
        ),
        f"#ifdef {cfg.guard}",
        f"LA(x{addr_reg}, scratch)",
        f"LI(x{mask_reg}, {field_mask:#x})  # {field} field mask",
    ]
    for values in itertools.product(cfg.bins, repeat=len(csrs)):
        for csr, value in zip(csrs, values, strict=True):
            clear, set_ = f"csrc {csr}, x{mask_reg}", f"csrs {csr}, x{cfg_reg}"
            lines.append(tsbi_call(clear) if csr == "menvcfg" else clear)
            if int(value, 2):
                lines.extend(
                    [f"LI(x{cfg_reg}, {int(value, 2) << cfg.shift:#x})", tsbi_call(set_) if csr == "menvcfg" else set_]
                )
        lines.append(f"RVTEST_TSBI_GOTO_{mode}MODE")
        tag = "_".join(f"{csr}.{field}{value}" for csr, value in zip(csrs, values, strict=True))
        flush = field == "cbie" and "00" not in values and "01" in values
        for instr in cfg.instrs:
            name = f"{instr}_{tag}"
            if flush:
                lines.extend(
                    [
                        f"LI(x{val_reg}, {random_int(32, signed=False):#x})",
                        f"sw x{val_reg}, 0(x{addr_reg})",
                        test_data.add_testcase(name, coverpoint, "Sv_HZicbo_cg"),
                        f"{instr}    0(x{addr_reg})",
                        f"lw x{val_reg}, 0(x{addr_reg})",
                        write_sigupd(val_reg, test_data),
                    ]
                )
            else:
                lines.extend(cbo_test(instr, name, coverpoint, "Sv_HZicbo_cg", addr_reg, val_reg, test_data))
        lines.append("RVTEST_TSBI_GOTO_SMODE")
    lines.append(f"#endif // {cfg.guard}")
    test_data.int_regs.return_registers([addr_reg, cfg_reg, mask_reg, val_reg])
    return lines


def _make_henvcfg(test_data: TestData, family: str) -> list[TestChunk]:
    """The family's CBOs in VS-mode and VU-mode across the menvcfg, henvcfg and senvcfg enables."""
    tc = test_data.begin_test_chunk(f"HZicbo_{family}_henvcfg")
    for field in _FIELDS[family]:
        for mode in ("VS", "VU"):
            tc.code.extend(_henvcfg_cases(test_data, field, mode))
    return [test_data.end_test_chunk()]


@add_priv_test_generator(
    "Sv",
    required_extensions=["H", "Zicbom"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svhzicbo_zicbom_henvcfg(test_data: TestData) -> list[TestChunk]:
    return _make_henvcfg(test_data, "zicbom")


@add_priv_test_generator(
    "Sv",
    required_extensions=["H", "Zicboz"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svhzicbo_zicboz_henvcfg(test_data: TestData) -> list[TestChunk]:
    return _make_henvcfg(test_data, "zicboz")


@add_priv_test_generator(
    "Sv",
    required_extensions=["H", "Zicbom"],
    extra_defines=["#define BOOT_TO_SMODE"],
    params=["SV39X4_TRANSLATION: true", "SV39_VSMODE_TRANSLATION: true"],
)
def make_svhzicbo_sv39x4_zicbom(test_data: TestData) -> list[TestChunk]:
    return _make_svhzicbo(test_data, SV39X4, VS_SV39, "zicbom")


@add_priv_test_generator(
    "Sv",
    required_extensions=["H", "Zicboz"],
    extra_defines=["#define BOOT_TO_SMODE"],
    params=["SV39X4_TRANSLATION: true", "SV39_VSMODE_TRANSLATION: true"],
)
def make_svhzicbo_sv39x4_zicboz(test_data: TestData) -> list[TestChunk]:
    return _make_svhzicbo(test_data, SV39X4, VS_SV39, "zicboz")


@add_priv_test_generator(
    "Sv",
    required_extensions=["H", "Zicbom"],
    extra_defines=["#define BOOT_TO_SMODE"],
    params=["SV32X4_TRANSLATION: true", "SV32_VSMODE_TRANSLATION: true"],
)
def make_svhzicbo_sv32x4_zicbom(test_data: TestData) -> list[TestChunk]:
    return _make_svhzicbo(test_data, SV32X4, VS_SV32, "zicbom")


@add_priv_test_generator(
    "Sv",
    required_extensions=["H", "Zicboz"],
    extra_defines=["#define BOOT_TO_SMODE"],
    params=["SV32X4_TRANSLATION: true", "SV32_VSMODE_TRANSLATION: true"],
)
def make_svhzicbo_sv32x4_zicboz(test_data: TestData) -> list[TestChunk]:
    return _make_svhzicbo(test_data, SV32X4, VS_SV32, "zicboz")
