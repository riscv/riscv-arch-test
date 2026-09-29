##################################
# priv/extensions/pmp/PMPH.py
#
# PMPH: PMP enforcement with the hypervisor extension.
# David_Harris@hmc.edu 24 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""PMPH suite: PMP configured in M-mode and checked from VS and VU modes, for the hypervisor load and
store instructions, and on the addresses that two-stage translation produces.

The suite boots to M-mode and delegates nothing, so the M-mode handler takes every trap.  PMP checks the
supervisor physical address that G-stage translation produces and the implicit page-table reads of both
stages (machine.adoc pmp_with_paging, hypervisor.adoc H_pmp).  A page or guest-page fault of the
translation takes priority over an access fault on the final address, while an access fault on a
page-table read is the first fault the walk encounters (hypervisor.adoc HSyncExcPrio).
"""

from collections.abc import Callable
from dataclasses import dataclass, replace
from functools import partial

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.HCommon import HLV_INSTRS, HLVX_INSTRS, HSV_INSTRS, TWO_STAGE_GATE, gated
from testgen.priv.extensions.pmp._lower_mode import VS_MODE, VU_MODE, Mode, make_lower_mode_amode, make_lower_mode_base
from testgen.priv.extensions.pmp.helpers import (
    REGION_BLOBS,
    UNLOCKED_LXWR_CASES,
    cfg_byte,
    cfg_shift,
    lxwr_walk_body,
    napot_mask_defines,
    zero_pmp_regs,
)
from testgen.priv.extensions.sv.access import virtual_address
from testgen.priv.extensions.sv.generate import guest_translation_setup, guest_translation_teardown, per_xlen
from testgen.priv.extensions.sv.page_tables import (
    PteFlags,
    SvMode,
    create_page_mapping,
    write_pte,
)
from testgen.priv.registry import add_priv_test_generator

# The PMP entry each scenario programs, so that coverage can tell the scenarios apart: a page table
# (0-5), the final supervisor physical address (6), the guest virtual addresses of the two mappings
# (7, 8), and the table that holds an invalid leaf (9, 10).
# table: (entry, NAPOT low ones for its size, RV64 only)
_TABLES = {
    "vlvl0": (0, "0x1FF", False),
    "hlvl0": (1, "0x1FF", False),
    "vlvl1": (2, "0x1FF", True),
    "hlvl1": (3, "0x1FF", True),
    "Vroot": (4, "0x1FF", False),
    "Hroot": (5, "0x7FF", False),
}
# A deny region: (address label or register, entry, NAPOT low ones)
_SPA = ("TEST_FOR_EXECUTION", 6, "PMP_REGION_SIZE")
# A NAPOT region of 4 KiB page tables needs a PMP grain of at most 4 KiB, and entries 0-10 lie below the background
# entry
_TABLE_GATE = "UDB_PMP_GRANULARITY <= 10 && UDB_NUM_USABLE_PMP_ENTRIES >= 12"
_MAPPINGS = ("vs", "g")


def _deny(regions: list[tuple[str, int, str]]) -> list[str]:
    """Clear the unlocked PMP entries, then make each (address, entry, NAPOT ones) a NAPOT region without permissions.

    An address is a label or a register.  Uses x4 and x5 only, so allocator registers survive.  HFENCE.VVMA
    flushes cached VS-stage translations, which HFENCE.GVMA need not flush (hypervisor.adoc hfence.vma NOTE).
    """
    lines = [*zero_pmp_regs()]
    for address, entry, ones in regions:
        load = f"mv x5, {address}" if address.startswith("x") else f"LA(x5, {address})"
        lines.extend([load, "srli x5, x5, PMP_SHIFT", f"ori x5, x5, {ones}", f"csrw pmpaddr{entry}, x5"])
    for xlen, per_csr in ((32, 4), (64, 8)):
        csrs: dict[int, list[str]] = {}
        for _, entry, _ in regions:
            csrs.setdefault((entry // per_csr) * (xlen // 32), []).append(cfg_byte("0000", "napot", cfg_shift(entry)))
        lines.append(f"#if __riscv_xlen == {xlen}")
        for csr, values in csrs.items():
            lines.extend([f"LI(x4, {' | '.join(values)})", f"csrw pmpcfg{csr}, x4"])
        lines.append("#endif")
    return [*lines, "sfence.vma", "hfence.gvma", "hfence.vvma"]


#####################################################################
# Hypervisor loads and stores with vsatp and hgatp Bare
#####################################################################


def _hlv_probes(test_data: TestData, case: str, coverpoint: str, region: str) -> list[str]:
    """Every hsv, hlv and hlvx at ``region``.  A faulting load keeps rd's previous value."""
    addr, rd = test_data.int_regs.get_registers(2)
    lines = ["", f"LA(x{addr}, {region})", f"LI(x{rd}, RVTEST_PMP_RET_ENCODING)"]
    for instr, rv64 in (*HSV_INSTRS, *HLV_INSTRS, *HLVX_INSTRS):
        body = [
            test_data.add_testcase(f"{case}_{instr}", f"{coverpoint}_{instr.split('.')[0]}", test_data.testsuite),
            f"{instr} x{rd}, (x{addr})",
            write_sigupd(rd, test_data),
        ]
        lines.extend(gated(body, "__riscv_xlen == 64" if rv64 else None))
    test_data.int_regs.return_registers([addr, rd])
    return lines


def _make_hlv_chunk(test_data: TestData, hs: bool) -> TestChunk:
    """hsv, hlv and hlvx from M-mode (effective privilege VS) or HS-mode (VU) against each legal XWR.

    HLVX needs both R and X from PMP (hypervisor.adoc hlsv_u_op).  An hlv from M-mode is still checked
    against unlocked PMP entries, because its effective privilege is VS or VU.
    """
    mode = "HS" if hs else "M"
    chunk = test_data.begin_test_chunk(f"hlv_{mode.lower()}")
    chunk.section_header = comment_banner(
        "cp_pmp_hsv, cp_pmp_hlv, cp_pmp_hlvx",
        f"Every hsv, hlv and hlvx from {mode}-mode with hstatus.SPVP = {int(not hs)} at the start of a NAPOT region,\n"
        "L = 0, each legal XWR.  vsatp and hgatp are Bare.",
    )
    temp = test_data.int_regs.get_register()
    setup = [
        "csrw vsatp, zero",
        "csrw hgatp, zero",
        "hfence.gvma",
        f"LI(x{temp}, HSTATUS_SPVP)",
        f"{'csrc' if hs else 'csrs'} hstatus, x{temp}",
    ]
    test_data.int_regs.return_register(temp)
    chunk.code.extend(
        lxwr_walk_body(
            test_data,
            UNLOCKED_LXWR_CASES,
            "napot",
            _hlv_probes,
            "cp_pmp",
            lower_mode="S" if hs else None,
            extra_setup=setup,
        )
    )
    chunk.raw_data.extend(REGION_BLOBS["napot"])
    return test_data.end_test_chunk()


#####################################################################
# Accesses through two-stage translation
#####################################################################


def _guest_mappings(test_data: TestData, g: SvMode, vs: SvMode, user: bool, gvas: tuple[int, int]) -> list[str]:
    """Map TEST_FOR_EXECUTION for a guest in two ways and leave the guest virtual addresses in ``gvas``.

    Mapping "vs" is a VS-stage 4 KiB page at vs.data_va over the G-stage identity map, and mapping "g" is a
    G-stage 4 KiB page at g.data_va reached through a VS-stage identity superpage.  VS-stage leaves are
    user pages when ``user``.
    """
    lines = guest_translation_setup(test_data, g, vs, "VUmode" if user else "VSmode")
    pte, addr, tmp = test_data.int_regs.get_registers(3)
    lines.extend(
        [
            "// Mapping vs: VS-stage kilopage over the G-stage identity map",
            *create_page_mapping(
                vs,
                leaf_level=0,
                leaf_flags=PteFlags(user=user),
                virtual_address=vs.data_va,
                physical_address="TEST_FOR_EXECUTION",
                regs=(pte, addr, tmp),
            ),
            "// Mapping g: VS-stage identity superpage over a G-stage kilopage",
            *write_pte(
                vs,
                level=vs.levels - 1,
                flags=PteFlags(user=user),
                virtual_address=g.data_va,
                physical_address=g.data_va,
                regs=(pte, addr, tmp),
                pa_is_label=False,
                superpage=True,
            ),
            *create_page_mapping(
                g,
                leaf_level=0,
                leaf_flags=PteFlags(user=True),
                virtual_address=g.data_va,
                physical_address="TEST_FOR_EXECUTION",
                regs=(pte, addr, tmp),
            ),
            "hfence.gvma",
            "hfence.vvma",
        ]
    )
    for mode, gva in ((vs, gvas[0]), (g, gvas[1])):
        lines.extend(
            virtual_address(
                mode,
                mode.data_va,
                0,
                destination=f"x{gva}",
                physical_address="TEST_FOR_EXECUTION",
                merge_sv32_base_page=True,
                scratch=f"x{pte}",
            )
        )
    test_data.int_regs.return_registers([pte, addr, tmp])
    return lines


def _guest_leaves(test_data: TestData, g: SvMode, vs: SvMode, user: bool, flags: PteFlags) -> list[str]:
    """Rewrite the kilopage leaves of both mappings with ``flags``; G-stage leaves are always user pages."""
    pte, addr, tmp = test_data.int_regs.get_registers(3)
    lines = [
        *write_pte(
            vs,
            level=0,
            flags=replace(flags, user=user),
            virtual_address=vs.data_va,
            physical_address="TEST_FOR_EXECUTION",
            regs=(pte, addr, tmp),
        ),
        *write_pte(
            g,
            level=0,
            flags=replace(flags, user=True),
            virtual_address=g.data_va,
            physical_address="TEST_FOR_EXECUTION",
            regs=(pte, addr, tmp),
        ),
        "hfence.gvma",
        "hfence.vvma",
    ]
    test_data.int_regs.return_registers([pte, addr, tmp])
    return lines


@dataclass(frozen=True)
class _Scenario:
    """One PMP and leaf configuration that the probes run under.

    regions are (address, entry, NAPOT low ones) as for _deny; an address "{gva0}" or "{gva1}" is the guest
    virtual address of mapping vs or g.  leaves, if set, first rewrite both kilopage leaves.
    """

    name: str
    coverpoint: str
    description: str
    regions: tuple[tuple[str, int, str], ...] = ()
    leaves: PteFlags | None = None
    rv64: bool = False


def _table(name: str, entry: int | None = None) -> tuple[str, int, str]:
    """The deny region of page table ``name``, in its own PMP entry unless ``entry`` is given."""
    table_entry, ones, _ = _TABLES[name]
    return (f"rvtest_{name}_pg_tbl", table_entry if entry is None else entry, ones)


def _table_scenario(name: str, coverpoint: str, stage: str) -> _Scenario:
    return _Scenario(
        name,
        coverpoint,
        f"PMP denies the {stage} table {name}; accesses whose walk reads it raise access faults",
        (_table(name),),
        rv64=_TABLES[name][2],
    )


def _guest_scenarios(test_data: TestData, mode: str, scenarios: list[_Scenario]) -> list[str]:
    """Map both test pages for a guest, then run jalr, sw and lw from VS-mode or VU-mode at the guest virtual address
    of each mapping under each scenario.

    A faulting load keeps its preloaded value.  VU-mode cannot write the signature through the VS-stage identity
    map, which is not a user page, so M-mode checks its loads.
    """
    user = mode == "vu"
    gva_vs, gva_g = test_data.int_regs.get_registers(2)
    lines = per_xlen(lambda g, vs: _guest_mappings(test_data, g, vs, user, (gva_vs, gva_g)))
    for scenario in scenarios:
        body = [f"// {mode.upper()}-mode: {scenario.description}"]
        if scenario.leaves is not None:
            body.extend(per_xlen(partial(_guest_leaves, test_data, user=user, flags=scenario.leaves)))
        regions = [
            (address.format(gva0=f"x{gva_vs}", gva1=f"x{gva_g}"), entry, ones)
            for address, entry, ones in scenario.regions
        ]
        body.extend([*_deny(regions), "fence.i", f"RVTEST_TSBI_GOTO_{mode.upper()}MODE"])
        checks = []
        rds = test_data.int_regs.get_registers(2)
        for mapping, gva, rd in zip(_MAPPINGS, (gva_vs, gva_g), rds, strict=True):
            name = f"{mode}_{scenario.name}_{mapping}"
            body.extend(
                [
                    "LA(ra, 1f)",
                    test_data.add_testcase(f"{name}_jalr", scenario.coverpoint, test_data.testsuite),
                    f"jalr x0, 0(x{gva})",
                    "1:",
                    f"LI(x{rd}, RVTEST_PMP_RET_ENCODING)",
                    test_data.add_testcase(f"{name}_sw", scenario.coverpoint, test_data.testsuite),
                    f"sw x{rd}, 0(x{gva})",
                    f"LI(x{rd}, 42)",
                ]
            )
            label = test_data.add_testcase(f"{name}_lw", scenario.coverpoint, test_data.testsuite)
            body.extend([label, f"lw x{rd}, 0(x{gva})"])
            check = write_sigupd(rd, test_data, label=label.removesuffix(":"))
            if user:
                checks.append(check)
            else:
                body.append(check)
        test_data.int_regs.return_registers(rds)
        body.extend(["RVTEST_TSBI_GOTO_MMODE", *checks])
        lines.extend(gated(body, "__riscv_xlen == 64" if scenario.rv64 else None))
    test_data.int_regs.return_registers([gva_vs, gva_g])
    return [*lines, *zero_pmp_regs(), *guest_translation_teardown(test_data)]


def _hlv_scenarios(test_data: TestData, scenarios: list[_Scenario]) -> list[str]:
    """Map both test pages, then run hsv.w, hlv.w and hlvx.wu from HS-mode with hstatus.SPVP = 1 in each scenario."""
    gva_vs, gva_g = test_data.int_regs.get_registers(2)
    rd = test_data.int_regs.get_register()
    lines = [
        *per_xlen(lambda g, vs: _guest_mappings(test_data, g, vs, False, (gva_vs, gva_g))),
        f"LI(x{rd}, HSTATUS_SPVP)",
        f"csrs hstatus, x{rd}",
    ]
    for scenario in scenarios:
        body = [f"// HS-mode: {scenario.description}", *_deny(list(scenario.regions)), "RVTEST_TSBI_GOTO_SMODE"]
        for mapping, gva in zip(_MAPPINGS, (gva_vs, gva_g), strict=True):
            name = f"{scenario.name}_{mapping}"
            body.extend(
                [
                    f"LI(x{rd}, RVTEST_PMP_RET_ENCODING)",
                    test_data.add_testcase(f"{name}_hsv.w", scenario.coverpoint, test_data.testsuite),
                    f"hsv.w x{rd}, (x{gva})",
                ]
            )
            for instr in ("hlv.w", "hlvx.wu"):
                body.extend(
                    [
                        f"LI(x{rd}, 42)",
                        test_data.add_testcase(f"{name}_{instr}", scenario.coverpoint, test_data.testsuite),
                        f"{instr} x{rd}, (x{gva})",
                        write_sigupd(rd, test_data),
                    ]
                )
        body.append("RVTEST_TSBI_GOTO_MMODE")
        lines.extend(gated(body, "__riscv_xlen == 64" if scenario.rv64 else None))
    lines.extend([f"LI(x{rd}, HSTATUS_SPVP)", f"csrc hstatus, x{rd}", *zero_pmp_regs()])
    test_data.int_regs.return_registers([gva_vs, gva_g, rd])
    return [*lines, *guest_translation_teardown(test_data)]


_INVALID = PteFlags(valid=False)

_GUEST_SCENARIOS = [
    _Scenario(
        "gva",
        "cp_pmp_after_translation",
        "PMP denies the guest virtual addresses, which does not affect the accesses",
        (("{gva0}", 7, "PMP_REGION_SIZE"), ("{gva1}", 8, "PMP_REGION_SIZE")),
    ),
    _Scenario("spa", "cp_pmp_after_translation", "PMP denies the supervisor physical address", (_SPA,)),
    _table_scenario("vlvl1", "cp_pmp_pt", "VS-stage"),
    _table_scenario("vlvl0", "cp_pmp_pt", "VS-stage"),
    _Scenario(
        "spa_leaf_r",
        "cp_pmp_pf_priority",
        "PMP denies the supervisor physical address; R-only leaves fault jalr and sw, and lw raises an access fault",
        (_SPA,),
        PteFlags(write=False, execute=False),
    ),
    _Scenario(
        "spa_leaf_x",
        "cp_pmp_pf_priority",
        "PMP denies the supervisor physical address; X-only leaves fault sw and lw, and jalr raises an access fault",
        (_SPA,),
        PteFlags(read=False, write=False),
    ),
    _Scenario(
        "leaf_invalid_vlvl0",
        "cp_pmp_pt_priority",
        "PMP denies vlvl0, which holds the invalid VS-stage leaf, so its read raises an access fault first",
        (_table("vlvl0", 9),),
        _INVALID,
    ),
]

_GSTAGE_SCENARIOS = [
    _table_scenario("hlvl1", "cp_pmp_pt", "G-stage"),
    _table_scenario("hlvl0", "cp_pmp_pt", "G-stage"),
    _Scenario(
        "leaf_invalid_hlvl0",
        "cp_pmp_pt_priority",
        "PMP denies hlvl0, which holds the invalid G-stage leaf, so its read raises an access fault first",
        (_table("hlvl0", 10),),
        _INVALID,
    ),
]

_HLV_SCENARIOS = [
    _Scenario("none", "cp_pmp_hlv_pt", "PMP denies nothing"),
    *(_table_scenario(name, "cp_pmp_hlv_pt", "VS-stage") for name in ("Vroot", "vlvl1", "vlvl0")),
    _Scenario("spa", "cp_pmp_hlv_pt", "PMP denies the supervisor physical address", (_SPA,)),
]

_HLV_GSTAGE_SCENARIOS = [_table_scenario(name, "cp_pmp_hlv_pt", "G-stage") for name in ("Hroot", "hlvl1", "hlvl0")]


def _two_stage_chunk(
    test_data: TestData, split: str, title: str, description: str, guest: list[_Scenario], hlv: list[_Scenario]
) -> TestChunk:
    """jalr, sw and lw from VS-mode and VU-mode in each ``guest`` scenario, then the HS-mode hypervisor loads and
    stores in each ``hlv`` scenario, on the TEST_FOR_EXECUTION region under two-stage translation."""
    chunk = test_data.begin_test_chunk(split)
    chunk.section_header = comment_banner(title, description)
    chunk.code.extend(
        [
            *napot_mask_defines(),
            "RVTEST_PMP_SET_BACKGROUND x4",
            f"#if ({TWO_STAGE_GATE}) && {_TABLE_GATE}",
            *(line for mode in ("vs", "vu") if guest for line in _guest_scenarios(test_data, mode, guest)),
            *(_hlv_scenarios(test_data, hlv) if hlv else []),
            "#endif",
        ]
    )
    chunk.raw_data.extend(REGION_BLOBS["napot"])
    return test_data.end_test_chunk()


def _make_two_stage_chunks(test_data: TestData) -> list[TestChunk]:
    """PMP on the final address and on the page tables of two-stage translation."""
    # TODO: G-stage page-table reads have their own file (gstage_pt) because Sail writes mtval2 = GPA >> 2 on their
    # access faults; hypervisor.adoc requires mtval2 = 0
    return [
        _two_stage_chunk(
            test_data,
            "guest",
            "cp_pmp_after_translation, cp_pmp_pt, cp_pmp_pf_priority, cp_pmp_pt_priority",
            "jalr, sw and lw from VS-mode and VU-mode through a VS-stage and a G-stage kilopage mapping, under\n"
            "PMP regions at the guest virtual, supervisor physical and VS-stage page-table addresses",
            _GUEST_SCENARIOS,
            [],
        ),
        _two_stage_chunk(
            test_data,
            "hlv_translated",
            "cp_pmp_hlv_pt",
            "hsv.w, hlv.w and hlvx.wu from HS-mode through both mappings, under PMP regions at the VS-stage\n"
            "page tables and the supervisor physical address",
            [],
            _HLV_SCENARIOS,
        ),
        _two_stage_chunk(
            test_data,
            "gstage_pt",
            "cp_pmp_pt, cp_pmp_pt_priority, cp_pmp_hlv_pt",
            "PMP denies G-stage page tables for jalr, sw and lw from VS-mode and VU-mode, and for hsv.w, hlv.w\n"
            "and hlvx.wu from HS-mode.  Accesses whose G-stage walk reads a denied table raise access faults",
            _GSTAGE_SCENARIOS,
            _HLV_GSTAGE_SCENARIOS,
        ),
    ]


#####################################################################
# Generators
#####################################################################


def _lower_mode_chunks(chunks: Callable[[Mode], list[TestChunk]]) -> list[TestChunk]:
    """The chunks of the VS-mode and VU-mode walks, with file names prefixed by the mode."""
    result = []
    for mode in (VS_MODE, VU_MODE):
        for chunk in chunks(mode):
            chunk.split_name = f"{mode.letter.lower()}_{chunk.split_name}"
            result.append(chunk)
    return result


# VS and VU traps need the visible trap handler
_PARAMS = ["NUM_PMP_ENTRIES: '>0'", "TIME_CSR_IMPLEMENTED: true"]


@add_priv_test_generator(
    "PMPH", extra_defines=["#define BOOT_TO_MMODE"], required_extensions=["Sm", "H"], params=_PARAMS
)
def make_pmph_base(test_data: TestData) -> list[TestChunk]:
    return _lower_mode_chunks(lambda mode: make_lower_mode_base(test_data, mode))


@add_priv_test_generator(
    "PMPH",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Sm", "H"],
    params=[*_PARAMS, "PMP_NA4_SUPPORTED: true"],
)
def make_pmph_na4(test_data: TestData) -> list[TestChunk]:
    return _lower_mode_chunks(lambda mode: make_lower_mode_amode(test_data, mode, "na4"))


@add_priv_test_generator(
    "PMPH",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Sm", "H"],
    params=[*_PARAMS, "PMP_NAPOT_SUPPORTED: true"],
)
def make_pmph_napot(test_data: TestData) -> list[TestChunk]:
    return _lower_mode_chunks(lambda mode: make_lower_mode_amode(test_data, mode, "napot"))


@add_priv_test_generator(
    "PMPH",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Sm", "H"],
    params=[*_PARAMS, "PMP_TOR_SUPPORTED: true"],
)
def make_pmph_tor(test_data: TestData) -> list[TestChunk]:
    return _lower_mode_chunks(lambda mode: make_lower_mode_amode(test_data, mode, "tor"))


@add_priv_test_generator(
    "PMPH",
    extra_defines=["#define BOOT_TO_MMODE"],
    required_extensions=["Sm", "H"],
    params=[*_PARAMS, "PMP_NAPOT_SUPPORTED: true"],
)
def make_pmph_hypervisor(test_data: TestData) -> list[TestChunk]:
    return [
        _make_hlv_chunk(test_data, hs=False),
        _make_hlv_chunk(test_data, hs=True),
        *_make_two_stage_chunks(test_data),
    ]
