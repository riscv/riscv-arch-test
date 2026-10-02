##################################
# priv/extensions/sv/Svadu.py
#
# Svadu hardware A/D-bit tests.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate hardware A/D-bit update tests."""

from testgen.asm.helpers import write_sigupd
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk, trap_sigupd_count
from testgen.priv.extensions.sv.access import add_rwx_test, virtual_address
from testgen.priv.extensions.sv.generate import begin_sv_test, sv_data
from testgen.priv.extensions.sv.page_tables import (
    SV32,
    SV39,
    SV48,
    SV57,
    PteFlags,
    SvMode,
    create_leaf_pte,
    create_page_mapping,
)
from testgen.priv.registry import add_priv_test_generator

# The S-mode driver runs from the boot identity map, so the test VAs skip the root
# slot that maps the test image (slot 2 on sv39, where rvtest_code_begin lives).
_VAS = {
    "sv32": {1: ("0x00400000", "0x00800000", "0x00C00000"), 0: ("0x01001000", "0x01002000", "0x01003000")},
    "sv39": {
        2: ("0x0C0000000", "0x100000000", "0x140000000"),
        1: ("0x000200000", "0x000400000", "0x000600000"),
        0: ("0x000001000", "0x000002000", "0x000003000"),
    },
    "sv48": {
        3: ("0x008080000000", "0x010080000000", "0x018080000000"),
        2: ("0x028040000000", "0x028080000000", "0x0280C0000000"),
        1: ("0x028000200000", "0x028000400000", "0x028000600000"),
        0: ("0x028000001000", "0x028000002000", "0x028000003000"),
    },
    "sv57": {
        4: ("0x01000000000000", "0x02000000000000", "0x03000000000000"),
        3: ("0x04008000000000", "0x04010000000000", "0x04018000000000"),
        2: ("0x04020040000000", "0x04020080000000", "0x040200C0000000"),
        1: ("0x04020300200000", "0x04020300400000", "0x04020300600000"),
        0: ("0x04020300801000", "0x04020300802000", "0x04020300803000"),
    },
}
_CODE_VA = {"sv32": "0x90000000", "sv39": "0x180000000", "sv48": "0x030080000000", "sv57": "0x05000080000000"}


def _add_adu_access(test_data: TestData, sv: SvMode, mode: str, level: int, number: int) -> list[str]:
    labels = {
        name: test_data.add_testcase(f"test{number}_{name}", "cp_ad_update", "Svadu_cg").removesuffix(":")
        for name in ("store", "load", "exec", "read_store_pte", "read_load_pte", "read_exec_pte")
    }
    table = "rvtest_Sroot_pg_tbl" if level == sv.levels - 1 else f"rvtest_slvl{level}_pg_tbl"
    load = "lw" if sv.xlen == 32 else "ld"
    # s0/s1 hold the load and store VAs because a0-a2 do not survive the mode switch.
    index_bits = 10 if sv.xlen == 32 else 9
    offsets = [
        ((int(va, 16) >> sv.page_offset_bits(level)) & ((1 << index_bits) - 1)) * (sv.xlen // 8)
        for va in _VAS[sv.name][level]
    ]
    return [
        *virtual_address(sv, f"va_data_l{level}_w", level, destination="s0", scratch="t0", merge_sv32_base_page=True),
        *virtual_address(sv, f"va_data_l{level}_r", level, destination="s1", scratch="t0", merge_sv32_base_page=True),
        *virtual_address(sv, f"va_data_l{level}_x", level, destination="a5", scratch="t0", merge_sv32_base_page=True),
        *([] if mode == "Smode" else [f"RVTEST_TSBI_GOTO_{mode.upper()}"]),
        "addi a2, a2, 16",
        f"{labels['store']}:",
        "sw a2, 20(s0)",
        "nop",
        f"{labels['load']}:",
        "lw a3, 20(s1)",
        "nop",
        f"{labels['exec']}:",
        "jalr ra, a5, 0",
        "nop",
        *([] if mode == "Smode" else ["RVTEST_TSBI_GOTO_SMODE"]),
        write_sigupd(12, test_data, label=labels["store"]),
        write_sigupd(13, test_data, label=labels["load"]),
        write_sigupd(14, test_data, label=labels["exec"]),
        f"LA(a0, {table})",
        f"{labels['read_store_pte']}:",
        f"{load} a4, {offsets[0]}(a0)",
        write_sigupd(14, test_data, label=labels["read_store_pte"]),
        f"{labels['read_load_pte']}:",
        f"{load} a4, {offsets[1]}(a0)",
        write_sigupd(14, test_data, label=labels["read_load_pte"]),
        f"{labels['read_exec_pte']}:",
        f"{load} a4, {offsets[2]}(a0)",
        write_sigupd(14, test_data, label=labels["read_exec_pte"]),
    ]


def _make_svadu_mode(test_data: TestData, sv: SvMode, mode: str) -> TestChunk:
    va_table = _VAS[sv.name]
    va_defs = tuple(
        (f"va_data_l{level}_{suffix}", va)
        for level in sorted(va_table, reverse=True)
        for suffix, va in zip(("w", "r", "x"), va_table[level], strict=True)
    )
    csr, mask = ("menvcfg", "MENVCFG_ADUE") if sv.xlen == 64 else ("menvcfgh", "MENVCFGH_ADUE")
    chunk = begin_sv_test(
        test_data,
        sv,
        mode,
        f"{sv.name}_Svadu_{mode}",
        coverpoint="cp_ad_update",
        va_defs=va_defs,
        va_code_override=_CODE_VA[sv.name],
        setup_asm=(f"LI(t0, {mask})", tsbi_call(f"csrs {csr}, t0")),
    )
    number = 0
    for level in sorted(va_table, reverse=True):
        va_w, va_r, va_x = (f"va_data_l{level}_{suffix}" for suffix in ("w", "r", "x"))
        for accessed, dirty, description in (
            (False, True, "PTE.A unset"),
            (True, False, "PTE.D unset"),
            (False, False, "PTE.A and PTE.D unset"),
        ):
            number += 1
            permissions = PteFlags(
                user=mode == "Umode",
                accessed=accessed,
                dirty=dirty,
            )
            chunk.code.extend(
                [
                    f"// Test case {number}: {description} at level {level}",
                    *create_page_mapping(
                        sv,
                        virtual_address=va_w,
                        leaf_level=level,
                        leaf_flags=permissions,
                    ),
                    create_leaf_pte(sv, virtual_address=va_r, level=level, flags=permissions),
                    create_leaf_pte(sv, virtual_address=va_x, level=level, flags=permissions),
                    "sfence.vma",
                    "",
                    *_add_adu_access(test_data, sv, mode, level, number),
                    "",
                ]
            )
    chunk.raw_data.extend(sv_data(sv))
    return test_data.end_test_chunk()


# Leaf VAs for the fault tests: va_data for 4 KiB pages, and a VA whose superpage leaf maps the 4 KiB-aligned
# rvtest_data_1, so its PPN is misaligned for every superpage size.
_FAULT_VA = {"sv32": "0x90407000", "sv39": "0x140802000", "sv48": "0x028500403000", "sv57": "0x07028500403000"}
_MISALIGNED_VA = {"sv32": "0x90400000", "sv39": "0x140000000", "sv48": "0x028000000000", "sv57": "0x07000000000000"}


def _ad_clear(*, user: bool = False, read: bool = True, extra: tuple[str, ...] = ()) -> PteFlags:
    return PteFlags(user=user, read=read, accessed=False, dirty=False, extra=extra)


def _fault_cases(sv: SvMode) -> list[tuple[str, int, PteFlags, bool, str]]:
    """Return (description, level, flags, superpage, va) for leaf PTEs that must page fault before an A/D update."""
    cases = [
        (f"Misaligned superpage at level {level}", level, _ad_clear(), False, "va_misaligned")
        for level in range(sv.levels - 1, 0, -1)
    ]
    cases.extend(
        [
            ("U page accessed from S-mode with SUM=0", 0, _ad_clear(user=True), True, "va_data"),
            ("Reserved encoding W=1 R=0", 0, _ad_clear(read=False), True, "va_data"),
        ]
    )
    if sv.xlen == 64:
        cases.extend(
            [
                ("Reserved bit 54 set", 0, _ad_clear(extra=("(1 << 54)",)), True, "va_data"),
                ("Reserved PBMT=3", 0, _ad_clear(extra=("(3 << 61)",)), True, "va_data"),
                (
                    "N=1 with reserved encoding ppn[3:0]=0000",
                    0,
                    _ad_clear(extra=("(1 << 63)",)),
                    True,
                    "va_data",
                ),
            ]
        )
        cases.extend(
            (
                f"N=1 with ppn[3:0]=1000 on a level {level} superpage",
                level,
                _ad_clear(extra=("(1 << 63)", "(1 << 13)")),
                True,
                "va_data",
            )
            for level in range(sv.levels - 1, 0, -1)
        )
    return cases


def _pte_address(sv: SvMode, va: str, level: int) -> list[str]:
    """Load a0 with the address of the leaf PTE that maps ``va`` at ``level``."""
    index_bits = 10 if sv.xlen == 32 else 9
    offset = ((int(va, 16) >> sv.page_offset_bits(level)) & ((1 << index_bits) - 1)) * (sv.xlen // 8)
    return [f"LA(a0, {sv.page_table_label(level)})", f"LI(t0, {offset})", "add a0, a0, t0"]


def _make_svadu_fault(test_data: TestData, sv: SvMode) -> TestChunk:
    """Access leaf PTEs with A=D=0 that must page fault, then check that the PTE was not updated.

    The walk checks for a leaf PTE must all pass before the hardware A/D update, so a faulting access leaves A and D
    clear.
    """
    csr, mask = ("menvcfg", "MENVCFG_ADUE") if sv.xlen == 64 else ("menvcfgh", "MENVCFGH_ADUE")
    chunk = begin_sv_test(
        test_data,
        sv,
        "Smode",
        f"{sv.name}_Svadu_fault_Smode",
        coverpoint="cp_ad_fault_no_update",
        va_defs=(("va_data", _FAULT_VA[sv.name]), ("va_misaligned", _MISALIGNED_VA[sv.name])),
        setup_asm=(f"LI(t0, {mask})", tsbi_call(f"csrs {csr}, t0")),
    )
    load = "lw" if sv.xlen == 32 else "ld"
    fault_vas = {"va_data": _FAULT_VA[sv.name], "va_misaligned": _MISALIGNED_VA[sv.name]}
    cases = _fault_cases(sv)
    for number, (description, level, flags, superpage, va) in enumerate(cases, start=1):
        label = test_data.add_testcase(f"test{number}_read_pte", "cp_ad_fault_no_update", "Svadu_cg").removesuffix(":")
        chunk.code.extend(
            [
                f"// Test case {number}: {description} | A=0 D=0 | expected = RWX page fault, PTE unchanged",
                *create_page_mapping(sv, virtual_address=va, leaf_level=level, leaf_flags=flags, superpage=superpage),
                "",
                *add_rwx_test(
                    test_data,
                    sv,
                    "Smode",
                    va,
                    level,
                    f"test{number}",
                    setup=("sfence.vma",),
                    repeat_setup=True,
                    coverpoints=dict.fromkeys(("store", "load", "exec"), "cp_ad_fault_no_update"),
                    covergroup="Svadu_cg",
                ),
                "",
                "// The PTE must still have A=0 and D=0",
                *_pte_address(sv, fault_vas[va], level),
                f"{label}:",
                f"{load} a4, 0(a0)",
                write_sigupd(14, test_data, label=label),
                "",
            ]
        )
    chunk.raw_data.extend(sv_data(sv))
    chunk.trap_sigupd_count = trap_sigupd_count(len(cases) * 3)
    return test_data.end_test_chunk()


def _make_svadu(test_data: TestData, sv: SvMode) -> list[TestChunk]:
    return [*(_make_svadu_mode(test_data, sv, mode) for mode in ("Smode", "Umode")), _make_svadu_fault(test_data, sv)]


@add_priv_test_generator(
    "Svadu",
    required_extensions=["Sv32", "Svadu"],
    march_extensions=["Svadu"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svadu_sv32(test_data: TestData) -> list[TestChunk]:
    return _make_svadu(test_data, SV32)


@add_priv_test_generator(
    "Svadu",
    required_extensions=["Sv39", "Svadu"],
    march_extensions=["Svadu"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svadu_sv39(test_data: TestData) -> list[TestChunk]:
    return _make_svadu(test_data, SV39)


@add_priv_test_generator(
    "Svadu",
    required_extensions=["Sv48", "Svadu"],
    march_extensions=["Svadu"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svadu_sv48(test_data: TestData) -> list[TestChunk]:
    return _make_svadu(test_data, SV48)


@add_priv_test_generator(
    "Svadu",
    required_extensions=["Sv57", "Svadu"],
    march_extensions=["Svadu"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svadu_sv57(test_data: TestData) -> list[TestChunk]:
    return _make_svadu(test_data, SV57)
