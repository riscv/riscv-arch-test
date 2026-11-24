##################################
# priv/extensions/pmp/SvZicbo.py
#
# PMP SvZicbo translated cache-block tests.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate cache-block operations against PMP-protected translated regions."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk, trap_sigupd_count
from testgen.priv.extensions.pmp import helpers as pmp
from testgen.priv.extensions.pmp.Sv import PMP_PTE_VAS
from testgen.priv.extensions.sv.access import virtual_address
from testgen.priv.extensions.sv.assembly import DATA_REGION_ALIGNED
from testgen.priv.extensions.sv.generate import SvRegs, begin_sv_test, end_sv_test, sv_data
from testgen.priv.extensions.sv.page_tables import SV32, SV39, SV48, SV57, PteFlags, SvMode, create_page_mapping
from testgen.priv.registry import add_priv_test_generator

_FAMILIES = {
    "Zicbom": ("MENVCFG_CBCFE | MENVCFG_CBIE", ("cbo.clean", "cbo.flush", "cbo.inval")),
    "Zicboz": ("MENVCFG_CBZE", ("cbo.zero",)),
}


def _setup_envcfg(extension: str, mode: str, scratch: int) -> tuple[str, ...]:
    mask = _FAMILIES[extension][0]
    t = f"x{scratch}"
    return (f"LI({t}, {mask})", f"csrs menvcfg, {t}", *((f"csrs senvcfg, {t}",) if mode == "Umode" else ()))


def _cross(topic: str, mode: str) -> str:
    tor = "_tor" if topic.endswith("_tor") else ""
    return f"cp_{'PA' if topic.startswith('pmp_on_pa') else 'PTE'}_PMP_rw_unset_cbo_{mode[0].lower()}{tor}"


def _add_operations(
    test_data: TestData, sv: SvMode, regs: SvRegs, mode: str, level: int, extension: str, number: int, cross: str
) -> list[str]:
    enter = [] if mode == "Mmode" else [f"RVTEST_TSBI_GOTO_{mode.upper()}"]
    leave = [] if mode == "Mmode" else ["RVTEST_TSBI_GOTO_MMODE"]
    lines = [*virtual_address(sv, "va_data", level, destination=regs.addr, scratch=regs.scratch), *enter]
    for operation in _FAMILIES[extension][1]:
        name = operation.replace(".", "_")
        lines.extend(
            [
                test_data.add_testcase(f"test{number}_{name}", cross, "PMP_SvZicbo_cg"),
                f"{operation} (x{regs.addr})",
                "nop",
            ]
        )
    lines.extend(leave)
    return lines


def _begin_test(
    test_data: TestData,
    regs: SvRegs,
    sv: SvMode,
    mode: str,
    topic: str,
    extension: str,
    *,
    pre_va_asm: tuple[str, ...],
    va_defs: tuple[tuple[str, str], ...] | None = None,
    va_code_override: str | None = None,
) -> TestChunk:
    min_granularity = 5 if topic.startswith("pmp_on_pa") else None
    return begin_sv_test(
        test_data,
        regs,
        sv,
        mode,
        f"SvZicbo_{sv.name}_{topic}_{extension.lower()}_{mode}",
        coverpoint=_cross(topic, mode),
        code_prefix=pmp.napot_mask_defines(min_granularity),
        sig_init=None,
        va_defs=va_defs,
        va_code_override=va_code_override,
        pre_va_asm=pre_va_asm,
        setup_asm=_setup_envcfg(extension, mode, regs.scratch),
    )


def _make_on_pa(test_data: TestData, sv: SvMode, mode: str, extension: str, amode: str = "napot") -> TestChunk:
    """PMP covers the translated data page with X only. NAPOT uses entry 0; the TOR twin uses entry 1,
    bounded below by pmpaddr0, over the same bytes."""
    regs = SvRegs.allocate(test_data)
    tor = amode == "tor"
    entry = 1 if tor else 0
    topic = "pmp_on_pa_tor" if tor else "pmp_on_pa"
    chunk = _begin_test(
        test_data,
        regs,
        sv,
        mode,
        topic,
        extension,
        pre_va_asm=(
            f"RVTEST_PMP_SET_BACKGROUND x{regs.scratch}",
            "",
            *pmp.set_pmpaddr(amode, entry, "rvtest_data_1", tor_bytes="(1 << PMP_REGION_SHIFT)"),
        ),
    )
    chunk.code.extend(
        [
            *pmp.write_pmpcfg0(
                test_data,
                pmp.cfg_byte("0100", amode, pmp.cfg_shift(entry)),
                "pmpcfg0_x",
                "PMP_perm_tor" if tor else "PMP_perm",
            ),
            "",
        ]
    )
    permissions = PteFlags(user=mode == "Umode")
    faults_per_case = len(_FAMILIES[extension][1])
    for number, level in enumerate(sv.levels_desc, start=1):
        chunk.code.extend(
            [
                *create_page_mapping(sv, leaf_level=level, leaf_flags=permissions),
                "sfence.vma",
                "",
                *_add_operations(test_data, sv, regs, mode, level, extension, number, _cross(topic, mode)),
                "",
            ]
        )
    chunk.raw_data.extend(sv_data(sv, regs, data_region_body=DATA_REGION_ALIGNED))
    chunk.trap_sigupd_count = trap_sigupd_count(faults_per_case * sv.levels)
    return end_sv_test(test_data, regs)


def _make_on_pte(test_data: TestData, sv: SvMode, mode: str, extension: str, amode: str = "napot") -> TestChunk:
    """PMP covers the page table at each level with X only. NAPOT uses entry 0; the TOR twin uses
    entry 1, bounded below by pmpaddr0, over the same bytes."""
    va_data, va_code = PMP_PTE_VAS[sv.name]
    regs = SvRegs.allocate(test_data)
    tor = amode == "tor"
    entry = 1 if tor else 0
    topic = "pmp_on_pte_tor" if tor else "pmp_on_pte"
    chunk = _begin_test(
        test_data,
        regs,
        sv,
        mode,
        topic,
        extension,
        pre_va_asm=(f"RVTEST_PMP_SET_BACKGROUND x{regs.scratch}",),
        va_defs=(("va_data", va_data),),
        va_code_override=va_code,
    )
    permissions = PteFlags(user=mode == "Umode")
    faults_per_case = len(_FAMILIES[extension][1])
    for number, level in enumerate(sv.levels_desc, start=1):
        top = level == sv.levels - 1
        chunk.code.extend(
            [*pmp.set_pmpaddr(amode, entry, sv.page_table_label(level), tor_bytes=pmp.TOR_TWIN_BYTES), ""]
        )
        if top:
            chunk.code.extend(
                [
                    *pmp.write_pmpcfg0(
                        test_data,
                        pmp.cfg_byte("0100", amode, pmp.cfg_shift(entry)),
                        "write_pmpcfg0",
                        "PMP_perm_tor" if tor else "PMP_perm",
                    ),
                    ".if (UDB_PMP_GRANULARITY < 12)",
                ]
            )
        else:
            chunk.code.extend(["sfence.vma", ""])
        chunk.code.extend(
            [
                *create_page_mapping(sv, leaf_level=level, leaf_flags=permissions),
                "sfence.vma",
                "",
                *_add_operations(test_data, sv, regs, mode, level, extension, number, _cross(topic, mode)),
            ]
        )
        if top:
            chunk.code.append(".endif")
        chunk.code.append("")
    chunk.raw_data.extend(sv_data(sv, regs, page_table_align="(UDB_PMP_GRANULARITY)"))
    chunk.trap_sigupd_count = trap_sigupd_count(faults_per_case * sv.levels)
    return end_sv_test(test_data, regs)


def _make_svpmpzicbo(test_data: TestData, sv: SvMode, extension: str, amode: str) -> list[TestChunk]:
    tests = []
    for mode in ("Smode", "Umode"):
        tests.extend(
            (_make_on_pa(test_data, sv, mode, extension, amode), _make_on_pte(test_data, sv, mode, extension, amode))
        )
    return tests


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sv32", "Zicbom", "Sm"],
    march_extensions=["Zicbom"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_NAPOT_SUPPORTED: true"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmpzicbo_sv32_zicbom(test_data: TestData) -> list[TestChunk]:
    return _make_svpmpzicbo(test_data, SV32, "Zicbom", "napot")


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sv32", "Zicbom", "Sm"],
    march_extensions=["Zicbom"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_TOR_SUPPORTED: true"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmpzicbo_sv32_zicbom_tor(test_data: TestData) -> list[TestChunk]:
    return _make_svpmpzicbo(test_data, SV32, "Zicbom", "tor")


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sv32", "Zicboz", "Sm"],
    march_extensions=["Zicboz"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_NAPOT_SUPPORTED: true"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmpzicbo_sv32_zicboz(test_data: TestData) -> list[TestChunk]:
    return _make_svpmpzicbo(test_data, SV32, "Zicboz", "napot")


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sv32", "Zicboz", "Sm"],
    march_extensions=["Zicboz"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_TOR_SUPPORTED: true"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmpzicbo_sv32_zicboz_tor(test_data: TestData) -> list[TestChunk]:
    return _make_svpmpzicbo(test_data, SV32, "Zicboz", "tor")


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sv39", "Zicbom", "Sm"],
    march_extensions=["Zicbom"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_NAPOT_SUPPORTED: true"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmpzicbo_sv39_zicbom(test_data: TestData) -> list[TestChunk]:
    return _make_svpmpzicbo(test_data, SV39, "Zicbom", "napot")


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sv39", "Zicbom", "Sm"],
    march_extensions=["Zicbom"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_TOR_SUPPORTED: true"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmpzicbo_sv39_zicbom_tor(test_data: TestData) -> list[TestChunk]:
    return _make_svpmpzicbo(test_data, SV39, "Zicbom", "tor")


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sv39", "Zicboz", "Sm"],
    march_extensions=["Zicboz"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_NAPOT_SUPPORTED: true"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmpzicbo_sv39_zicboz(test_data: TestData) -> list[TestChunk]:
    return _make_svpmpzicbo(test_data, SV39, "Zicboz", "napot")


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sv39", "Zicboz", "Sm"],
    march_extensions=["Zicboz"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_TOR_SUPPORTED: true"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmpzicbo_sv39_zicboz_tor(test_data: TestData) -> list[TestChunk]:
    return _make_svpmpzicbo(test_data, SV39, "Zicboz", "tor")


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sv48", "Zicbom", "Sm"],
    march_extensions=["Zicbom"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_NAPOT_SUPPORTED: true"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmpzicbo_sv48_zicbom(test_data: TestData) -> list[TestChunk]:
    return _make_svpmpzicbo(test_data, SV48, "Zicbom", "napot")


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sv48", "Zicbom", "Sm"],
    march_extensions=["Zicbom"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_TOR_SUPPORTED: true"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmpzicbo_sv48_zicbom_tor(test_data: TestData) -> list[TestChunk]:
    return _make_svpmpzicbo(test_data, SV48, "Zicbom", "tor")


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sv48", "Zicboz", "Sm"],
    march_extensions=["Zicboz"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_NAPOT_SUPPORTED: true"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmpzicbo_sv48_zicboz(test_data: TestData) -> list[TestChunk]:
    return _make_svpmpzicbo(test_data, SV48, "Zicboz", "napot")


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sv48", "Zicboz", "Sm"],
    march_extensions=["Zicboz"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_TOR_SUPPORTED: true"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmpzicbo_sv48_zicboz_tor(test_data: TestData) -> list[TestChunk]:
    return _make_svpmpzicbo(test_data, SV48, "Zicboz", "tor")


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sv57", "Zicbom", "Sm"],
    march_extensions=["Zicbom"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_NAPOT_SUPPORTED: true"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmpzicbo_sv57_zicbom(test_data: TestData) -> list[TestChunk]:
    return _make_svpmpzicbo(test_data, SV57, "Zicbom", "napot")


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sv57", "Zicbom", "Sm"],
    march_extensions=["Zicbom"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_TOR_SUPPORTED: true"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmpzicbo_sv57_zicbom_tor(test_data: TestData) -> list[TestChunk]:
    return _make_svpmpzicbo(test_data, SV57, "Zicbom", "tor")


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sv57", "Zicboz", "Sm"],
    march_extensions=["Zicboz"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_NAPOT_SUPPORTED: true"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmpzicbo_sv57_zicboz(test_data: TestData) -> list[TestChunk]:
    return _make_svpmpzicbo(test_data, SV57, "Zicboz", "napot")


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sv57", "Zicboz", "Sm"],
    march_extensions=["Zicboz"],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_TOR_SUPPORTED: true"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmpzicbo_sv57_zicboz_tor(test_data: TestData) -> list[TestChunk]:
    return _make_svpmpzicbo(test_data, SV57, "Zicboz", "tor")
