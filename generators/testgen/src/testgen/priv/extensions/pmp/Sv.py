##################################
# priv/extensions/pmp/Sv.py
#
# PMP Sv translated-access tests.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate PMP checks for translated data and page-table regions."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk, trap_sigupd_count
from testgen.priv.extensions.pmp import helpers as pmp
from testgen.priv.extensions.sv.access import Crosses, add_rwx_test, cross_names
from testgen.priv.extensions.sv.assembly import DATA_REGION_ALIGNED
from testgen.priv.extensions.sv.generate import SvRegs, begin_sv_test, end_sv_test, sv_data
from testgen.priv.extensions.sv.page_tables import SV32, SV39, SV48, SV57, PteFlags, SvMode, create_page_mapping
from testgen.priv.registry import add_priv_test_generator

PMP_PTE_VAS = {
    "sv32": ("0x00000000", "0x90000000"),
    "sv39": ("0x00000000", "0xFFFFFFFF80000000"),
    "sv48": ("0x00000000", "0xFFFFFF0080000000"),
    "sv57": ("0x0000000000000000", "0xFFFE000080000000"),
}


def _pa_cfgs(amode: str) -> tuple[tuple[str, str, int], ...]:
    """Entry 1's configuration for each PA case: (pmpcfg0 value, case name, faults per case)."""
    return (
        (pmp.cfg_byte("0101", amode, pmp.cfg_shift(1)), "pmpcfg0_rx", 1),
        (pmp.cfg_byte("0011", amode, pmp.cfg_shift(1)), "pmpcfg0_rw", 1),
        (pmp.cfg_byte("0100", amode, pmp.cfg_shift(1)), "pmpcfg0_x", 2),
    )


def _crosses(target: str, mode: str, amode: str = "napot") -> Crosses:
    """The crosses for PMP denying access to the translated address (``PA``) or the page table (``pte``)."""
    m = mode[0].lower()
    prefix = "pmp_tor" if amode == "tor" else "pmp0"
    return Crosses(
        "PMP_Sv_cg", f"{prefix}_{target}_nowrite_{m}", f"{prefix}_{target}_noread_{m}", f"{prefix}_{target}_noexec_{m}"
    )


def _begin_test(
    test_data: TestData,
    regs: SvRegs,
    sv: SvMode,
    mode: str,
    topic: str,
    pmp_defines: list[str],
    *,
    crosses: Crosses,
    pre_va_asm: tuple[str, ...],
    va_defs: tuple[tuple[str, str], ...] | None = None,
    va_code_override: str | None = None,
) -> TestChunk:
    split_name = f"Sv_{sv.name}_{topic}_{mode}"
    return begin_sv_test(
        test_data,
        regs,
        sv,
        mode,
        split_name,
        coverpoint=cross_names(crosses),
        code_prefix=pmp_defines,
        va_defs=va_defs,
        va_code_override=va_code_override,
        pre_va_asm=pre_va_asm,
    )


def _make_pmp_on_pa(test_data: TestData, sv: SvMode, mode: str, amode: str = "napot") -> TestChunk:
    """PMP entry 1 covers the translated data page. The TOR twin bounds the same bytes below with pmpaddr0."""
    regs = SvRegs.allocate(test_data)
    crosses = _crosses("PA", mode, amode)
    tor = amode == "tor"
    chunk = _begin_test(
        test_data,
        regs,
        sv,
        mode,
        "pmp_on_pa_tor" if tor else "pmp_on_pa",
        pmp.napot_mask_defines(5),
        crosses=crosses,
        pre_va_asm=(
            f"RVTEST_PMP_SET_BACKGROUND x{regs.scratch}",
            "",
            *pmp.set_pmpaddr(amode, 1, "rvtest_data_1", tor_bytes="(1 << PMP_REGION_SHIFT)"),
            "sfence.vma",
        ),
    )
    permissions = PteFlags(user=mode == "Umode")
    number = 0
    faults = 0
    for cfg, name, case_faults in _pa_cfgs(amode):
        chunk.code.extend([*pmp.write_pmpcfg0(test_data, cfg, name, "PMP1_PA_TOR" if tor else "PMP0_PA"), ""])
        for level in sv.levels_desc:
            number += 1
            faults += case_faults
            chunk.code.extend(
                [
                    f"// Test case {number}: translated access with {cfg}",
                    *create_page_mapping(sv, leaf_level=level, leaf_flags=permissions),
                    "sfence.vma",
                    "",
                    *add_rwx_test(
                        test_data,
                        sv,
                        regs,
                        mode,
                        "va_data",
                        level,
                        f"test{number}",
                        driver_mode="Mmode",
                        crosses=crosses,
                    ),
                    "",
                ]
            )
    chunk.raw_data.extend(sv_data(sv, regs, data_region_body=DATA_REGION_ALIGNED))
    chunk.trap_sigupd_count = trap_sigupd_count(faults)
    return end_sv_test(test_data, regs)


def _make_pmp_on_pte(test_data: TestData, sv: SvMode, mode: str, amode: str = "napot") -> TestChunk:
    """PMP covers the page table at each level. NAPOT uses entry 0; the TOR twin uses entry 1, bounded
    below by pmpaddr0, over the same bytes."""
    va_data, va_code = PMP_PTE_VAS[sv.name]
    regs = SvRegs.allocate(test_data)
    crosses = _crosses("pte", mode, amode)
    tor = amode == "tor"
    entry = 1 if tor else 0
    chunk = _begin_test(
        test_data,
        regs,
        sv,
        mode,
        "pmp_on_pte_tor" if tor else "pmp_on_pte",
        pmp.napot_mask_defines(),
        crosses=crosses,
        pre_va_asm=(f"RVTEST_PMP_SET_BACKGROUND x{regs.scratch}",),
        va_defs=(("va_data", va_data),),
        va_code_override=va_code,
    )
    permissions = PteFlags(user=mode == "Umode")
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
                        "PMP1_PTE_TOR" if tor else "PMP0_PTE",
                    ),
                    ".if (UDB_PMP_GRANULARITY < 12)",
                ]
            )
        else:
            chunk.code.extend(["sfence.vma", ""])
        chunk.code.extend(
            [
                f"// Test case {number}: PMP blocks the level {level} page table",
                *create_page_mapping(sv, leaf_level=level, leaf_flags=permissions),
                "sfence.vma",
                "",
                *add_rwx_test(
                    test_data,
                    sv,
                    regs,
                    mode,
                    "va_data",
                    level,
                    f"test{number}",
                    driver_mode="Mmode",
                    crosses=crosses,
                ),
            ]
        )
        if top:
            chunk.code.append(".endif")
        chunk.code.append("")
    chunk.raw_data.extend(sv_data(sv, regs, page_table_align="(UDB_PMP_GRANULARITY)"))
    chunk.trap_sigupd_count = trap_sigupd_count(sv.levels * 3)
    return end_sv_test(test_data, regs)


def _make_svpmp(test_data: TestData, sv: SvMode, amode: str) -> list[TestChunk]:
    tests = []
    for mode in ("Smode", "Umode"):
        tests.extend((_make_pmp_on_pa(test_data, sv, mode, amode), _make_pmp_on_pte(test_data, sv, mode, amode)))
    return tests


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sv32", "Sm"],
    march_extensions=[],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_NAPOT_SUPPORTED: true"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmp_sv32(test_data: TestData) -> list[TestChunk]:
    return _make_svpmp(test_data, SV32, "napot")


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sv32", "Sm"],
    march_extensions=[],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_TOR_SUPPORTED: true"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmp_sv32_tor(test_data: TestData) -> list[TestChunk]:
    return _make_svpmp(test_data, SV32, "tor")


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sv39", "Sm"],
    march_extensions=[],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_NAPOT_SUPPORTED: true"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmp_sv39(test_data: TestData) -> list[TestChunk]:
    return _make_svpmp(test_data, SV39, "napot")


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sv39", "Sm"],
    march_extensions=[],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_TOR_SUPPORTED: true"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmp_sv39_tor(test_data: TestData) -> list[TestChunk]:
    return _make_svpmp(test_data, SV39, "tor")


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sv48", "Sm"],
    march_extensions=[],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_NAPOT_SUPPORTED: true"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmp_sv48(test_data: TestData) -> list[TestChunk]:
    return _make_svpmp(test_data, SV48, "napot")


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sv48", "Sm"],
    march_extensions=[],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_TOR_SUPPORTED: true"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmp_sv48_tor(test_data: TestData) -> list[TestChunk]:
    return _make_svpmp(test_data, SV48, "tor")


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sv57", "Sm"],
    march_extensions=[],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_NAPOT_SUPPORTED: true"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmp_sv57(test_data: TestData) -> list[TestChunk]:
    return _make_svpmp(test_data, SV57, "napot")


@add_priv_test_generator(
    "PMP",
    required_extensions=["Sv57", "Sm"],
    march_extensions=[],
    params=["NUM_PMP_ENTRIES: '>0'", "PMP_TOR_SUPPORTED: true"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svpmp_sv57_tor(test_data: TestData) -> list[TestChunk]:
    return _make_svpmp(test_data, SV57, "tor")
