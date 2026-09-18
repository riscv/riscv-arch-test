##################################
# priv/extensions/sv/SvPMPZicbo.py
#
# SvPMPZicbo translated cache-block tests.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate cache-block operations against PMP-protected translated regions."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk, trap_sigupd_count
from testgen.priv.extensions.pmp import helpers as pmp
from testgen.priv.extensions.sv.access import virtual_address
from testgen.priv.extensions.sv.assembly import DATA_REGION_ALIGNED
from testgen.priv.extensions.sv.generate import begin_sv_test, sv_data
from testgen.priv.extensions.sv.page_tables import SV32, SV39, SV48, SV57, PteFlags, SvMode, create_page_mapping
from testgen.priv.extensions.sv.SvPMP import PMP_PTE_VAS
from testgen.priv.registry import add_priv_test_generator

_MARCH = ["I", "Zicsr", "Zifencei"]
_FAMILIES = {
    "Zicbom": ("MENVCFG_CBCFE | MENVCFG_CBIE", ("cbo.clean (a5)", "cbo.flush (a5)", "cbo.inval (a5)")),
    "Zicboz": ("MENVCFG_CBZE", ("cbo.zero (a5)",)),
}


def _setup_envcfg(extension: str, mode: str) -> tuple[str, ...]:
    mask = _FAMILIES[extension][0]
    return (f"LI(t0, {mask})", "csrs menvcfg, t0", *(("csrs senvcfg, t0",) if mode == "Umode" else ()))


def _add_operations(test_data: TestData, sv: SvMode, mode: str, level: int, extension: str, number: int) -> list[str]:
    lines = [*virtual_address(sv, "va_data", level), f"RVTEST_GOTO_LOWER_MODE {mode}"]
    for operation in _FAMILIES[extension][1]:
        name = operation.split()[0].replace(".", "_")
        lines.extend(
            [
                test_data.add_testcase(f"test{number}_{name}", "cp_pmp_zicbo", "SvPMPZicbo_cg"),
                operation,
                "nop",
            ]
        )
    lines.append("RVTEST_GOTO_MMODE")
    return lines


def _begin_test(
    test_data: TestData,
    sv: SvMode,
    mode: str,
    topic: str,
    extension: str,
    *,
    pre_va_asm: tuple[str, ...],
    va_defs: tuple[tuple[str, str], ...] | None = None,
    va_code_override: str | None = None,
) -> TestChunk:
    min_granularity = 5 if topic == "pmp_on_pa" else None
    return begin_sv_test(
        test_data,
        sv,
        mode,
        f"{sv.name}_{topic}_{extension.lower()}_{mode}",
        coverpoint="cp_pmp_zicbo",
        code_prefix=pmp.napot_mask_defines(min_granularity),
        sig_init="",
        va_defs=va_defs,
        va_code_override=va_code_override,
        pre_va_asm=pre_va_asm,
        setup_asm=_setup_envcfg(extension, mode),
    )


def _make_on_pa(test_data: TestData, sv: SvMode, mode: str, extension: str) -> TestChunk:
    chunk = _begin_test(
        test_data,
        sv,
        mode,
        "pmp_on_pa",
        extension,
        pre_va_asm=("RVTEST_PMP_SET_BACKGROUND x4", "", *pmp.set_pmpaddr("napot", 0, "rvtest_data_1")),
    )
    chunk.code.extend(
        [
            *pmp.write_pmpcfg0(
                test_data,
                pmp.cfg_byte("0100", "napot", pmp.cfg_shift(0)),
                "pmpcfg0_x",
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
                *_add_operations(test_data, sv, mode, level, extension, number),
                "",
            ]
        )
    chunk.raw_data.extend(sv_data(sv, data_region_body=DATA_REGION_ALIGNED))
    chunk.trap_sigupd_count = trap_sigupd_count(faults_per_case * sv.levels)
    return test_data.end_test_chunk()


def _make_on_pte(test_data: TestData, sv: SvMode, mode: str, extension: str) -> TestChunk:
    va_data, va_code = PMP_PTE_VAS[sv.name]
    chunk = _begin_test(
        test_data,
        sv,
        mode,
        "pmp_on_pte",
        extension,
        pre_va_asm=("RVTEST_PMP_SET_BACKGROUND x4",),
        va_defs=(("va_data", va_data),),
        va_code_override=va_code,
    )
    permissions = PteFlags(user=mode == "Umode")
    faults_per_case = len(_FAMILIES[extension][1])
    for number, level in enumerate(sv.levels_desc, start=1):
        top = level == sv.levels - 1
        chunk.code.extend([*pmp.set_pmpaddr("napot", 0, sv.page_table_label(level)), ""])
        if top:
            chunk.code.extend(
                [
                    *pmp.write_pmpcfg0(
                        test_data,
                        pmp.cfg_byte("0100", "napot", pmp.cfg_shift(0)),
                        "write_pmpcfg0",
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
                *_add_operations(test_data, sv, mode, level, extension, number),
            ]
        )
        if top:
            chunk.code.append(".endif")
        chunk.code.append("")
    chunk.raw_data.extend(sv_data(sv, page_table_align="(UDB_PMP_GRANULARITY)"))
    chunk.trap_sigupd_count = trap_sigupd_count(faults_per_case * sv.levels)
    return test_data.end_test_chunk()


def _make_svpmpzicbo(test_data: TestData, sv: SvMode, extension: str) -> list[TestChunk]:
    tests = []
    for mode in ("Smode", "Umode"):
        tests.extend((_make_on_pa(test_data, sv, mode, extension), _make_on_pte(test_data, sv, mode, extension)))
    return tests


@add_priv_test_generator(
    "SvPMPZicbo",
    required_extensions=["I", "Sv32", "Zicbom", "Sm"],
    march_extensions=_MARCH + ["Zicbom"],
    params=["NUM_PMP_ENTRIES: '>0'"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmpzicbo_sv32_zicbom(test_data: TestData) -> list[TestChunk]:
    return _make_svpmpzicbo(test_data, SV32, "Zicbom")


@add_priv_test_generator(
    "SvPMPZicbo",
    required_extensions=["I", "Sv32", "Zicboz", "Sm"],
    march_extensions=_MARCH + ["Zicboz"],
    params=["NUM_PMP_ENTRIES: '>0'"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmpzicbo_sv32_zicboz(test_data: TestData) -> list[TestChunk]:
    return _make_svpmpzicbo(test_data, SV32, "Zicboz")


@add_priv_test_generator(
    "SvPMPZicbo",
    required_extensions=["I", "Sv39", "Zicbom", "Sm"],
    march_extensions=_MARCH + ["Zicbom"],
    params=["NUM_PMP_ENTRIES: '>0'"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmpzicbo_sv39_zicbom(test_data: TestData) -> list[TestChunk]:
    return _make_svpmpzicbo(test_data, SV39, "Zicbom")


@add_priv_test_generator(
    "SvPMPZicbo",
    required_extensions=["I", "Sv39", "Zicboz", "Sm"],
    march_extensions=_MARCH + ["Zicboz"],
    params=["NUM_PMP_ENTRIES: '>0'"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmpzicbo_sv39_zicboz(test_data: TestData) -> list[TestChunk]:
    return _make_svpmpzicbo(test_data, SV39, "Zicboz")


@add_priv_test_generator(
    "SvPMPZicbo",
    required_extensions=["I", "Sv48", "Zicbom", "Sm"],
    march_extensions=_MARCH + ["Zicbom"],
    params=["NUM_PMP_ENTRIES: '>0'"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmpzicbo_sv48_zicbom(test_data: TestData) -> list[TestChunk]:
    return _make_svpmpzicbo(test_data, SV48, "Zicbom")


@add_priv_test_generator(
    "SvPMPZicbo",
    required_extensions=["I", "Sv48", "Zicboz", "Sm"],
    march_extensions=_MARCH + ["Zicboz"],
    params=["NUM_PMP_ENTRIES: '>0'"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmpzicbo_sv48_zicboz(test_data: TestData) -> list[TestChunk]:
    return _make_svpmpzicbo(test_data, SV48, "Zicboz")


@add_priv_test_generator(
    "SvPMPZicbo",
    required_extensions=["I", "Sv57", "Zicbom", "Sm"],
    march_extensions=_MARCH + ["Zicbom"],
    params=["NUM_PMP_ENTRIES: '>0'"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmpzicbo_sv57_zicbom(test_data: TestData) -> list[TestChunk]:
    return _make_svpmpzicbo(test_data, SV57, "Zicbom")


@add_priv_test_generator(
    "SvPMPZicbo",
    required_extensions=["I", "Sv57", "Zicboz", "Sm"],
    march_extensions=_MARCH + ["Zicboz"],
    params=["NUM_PMP_ENTRIES: '>0'"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmpzicbo_sv57_zicboz(test_data: TestData) -> list[TestChunk]:
    return _make_svpmpzicbo(test_data, SV57, "Zicboz")
