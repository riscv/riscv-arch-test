##################################
# priv/extensions/sv/Svadu.py
#
# Svadu hardware A/D-bit tests.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate hardware A/D-bit update tests."""

from typing import NamedTuple

from testgen.asm.helpers import write_sigupd
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk, trap_sigupd_count
from testgen.priv.extensions.sv.access import ad_crosses, add_rwx_test, cross_names, virtual_address
from testgen.priv.extensions.sv.generate import SvRegs, begin_sv_test, end_sv_test, sv_data
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
# Fault tests: a superpage leaf here maps the 4 KiB-aligned rvtest_data_1, so its PPN is misaligned at every level.
_MISALIGNED_VA = {"sv32": "0x90400000", "sv39": "0x140000000", "sv48": "0x028000000000", "sv57": "0x07000000000000"}


def _pte_offset(sv: SvMode, va: str, level: int) -> int:
    """Return the byte offset of the level ``level`` PTE for ``va`` within its page table."""
    index_bits = 10 if sv.xlen == 32 else 9
    return ((int(va, 16) >> sv.page_offset_bits(level)) & ((1 << index_bits) - 1)) * (sv.xlen // 8)


def _enable_adue(sv: SvMode, regs: SvRegs) -> tuple[str, ...]:
    """Return setup assembly that sets ADUE in menvcfg (menvcfgh on RV32)."""
    csr, mask = ("menvcfg", "MENVCFG_ADUE") if sv.xlen == 64 else ("menvcfgh", "MENVCFGH_ADUE")
    return (f"LI(x{regs.scratch}, {mask})", tsbi_call(f"csrs {csr}, x{regs.scratch}"))


def _add_adu_access(
    test_data: TestData, sv: SvMode, regs: SvRegs, mode: str, level: int, number: int, *, accessed: bool
) -> list[str]:
    # Each PTE readback checks the A/D update of the access before it.
    crosses = ad_crosses("Svadu_cg", mode, accessed=accessed)
    by_operation = crosses.by_operation()
    labels = {
        name: test_data.add_testcase(
            f"test{number}_{name}", by_operation[name.removeprefix("read_").removesuffix("_pte")], crosses.covergroup
        ).removesuffix(":")
        for name in ("store", "load", "exec", "read_store_pte", "read_load_pte", "read_exec_pte")
    }
    load = "lw" if sv.xlen == 32 else "ld"
    offsets = [_pte_offset(sv, va, level) for va in _VAS[sv.name][level]]
    # The store, load, and fetch VAs are all built before the mode switch. The load register is free until
    # the load, so it is the scratch register for building them.
    store_addr = test_data.int_regs.get_register(exclude_regs=[0])
    load_addr = regs.scratch
    value, result = f"x{regs.value}", f"x{regs.result}"
    lines = [
        *(
            line
            for suffix, destination in (("w", store_addr), ("r", load_addr), ("x", regs.addr))
            for line in virtual_address(
                sv,
                f"va_data_l{level}_{suffix}",
                level,
                destination=destination,
                scratch=regs.load,
                merge_sv32_base_page=True,
            )
        ),
        *([] if mode == "Smode" else [f"RVTEST_TSBI_GOTO_{mode.upper()}"]),
        f"addi {value}, {value}, 16",
        f"{labels['store']}:",
        f"sw {value}, 20(x{store_addr})",
        "nop",
        f"{labels['load']}:",
        f"lw x{regs.load}, 20(x{load_addr})",
        "nop",
        f"{labels['exec']}:",
        f"jalr ra, x{regs.addr}, 0",
        "nop",
        *([] if mode == "Smode" else ["RVTEST_TSBI_GOTO_SMODE"]),
        write_sigupd(regs.value, test_data, label=labels["store"]),
        write_sigupd(regs.load, test_data, label=labels["load"]),
        write_sigupd(regs.result, test_data, label=labels["exec"]),
        f"LA(x{regs.scratch}, {sv.page_table_label(level)})",
    ]
    for name, offset in zip(("read_store_pte", "read_load_pte", "read_exec_pte"), offsets, strict=True):
        lines.extend(
            [
                f"{labels[name]}:",
                f"{load} {result}, {offset}(x{regs.scratch})",
                write_sigupd(regs.result, test_data, label=labels[name]),
            ]
        )
    test_data.int_regs.return_register(store_addr)
    return lines


def _make_svadu_mode(test_data: TestData, sv: SvMode, mode: str) -> TestChunk:
    va_table = _VAS[sv.name]
    va_defs = tuple(
        (f"va_data_l{level}_{suffix}", va)
        for level in sorted(va_table, reverse=True)
        for suffix, va in zip(("w", "r", "x"), va_table[level], strict=True)
    )
    regs = SvRegs.allocate(test_data)
    chunk = begin_sv_test(
        test_data,
        regs,
        sv,
        mode,
        f"{sv.name}_Svadu_{mode}",
        coverpoint=cross_names(
            ad_crosses("Svadu_cg", mode, accessed=False), ad_crosses("Svadu_cg", mode, accessed=True)
        ),
        va_defs=va_defs,
        va_code_override=_CODE_VA[sv.name],
        setup_asm=_enable_adue(sv, regs),
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
            permissions = PteFlags(user=mode == "Umode", accessed=accessed, dirty=dirty)
            chunk.code.extend(
                [
                    f"// Test case {number}: {description} at level {level}",
                    *create_page_mapping(sv, virtual_address=va_w, leaf_level=level, leaf_flags=permissions),
                    create_leaf_pte(sv, virtual_address=va_r, level=level, flags=permissions),
                    create_leaf_pte(sv, virtual_address=va_x, level=level, flags=permissions),
                    "sfence.vma",
                    "",
                    *_add_adu_access(test_data, sv, regs, mode, level, number, accessed=accessed),
                    "",
                ]
            )
    chunk.raw_data.extend(sv_data(sv, regs))
    return end_sv_test(test_data, regs)


_CBOS = {"zicbom": ("cbo.clean", "cbo.flush", "cbo.inval"), "zicboz": ("cbo.zero",)}


def _make_cbo_adue(test_data: TestData, sv: SvMode, family: str) -> TestChunk:
    """CBOs in S-mode with menvcfg.ADUE = 1 through a leaf with A = D = 0 and one with only D = 0, at each level.

    A CBO sets A.  cbo.zero also sets D, because it writes; a cache-block management instruction never checks or sets
    D (cmo.adoc).  Each CBO gets a fresh leaf, which is read back after it.
    """
    regs = SvRegs.allocate(test_data)
    kind = "cbm" if family == "zicbom" else "cbz"
    chunk = begin_sv_test(
        test_data,
        regs,
        sv,
        "Smode",
        f"{sv.name}_Svadu_{family}",
        coverpoint=f"Abit_unset_{kind}_s, Dbit_unset_{kind}_s",
        setup_asm=_enable_adue(sv, regs),
    )
    load = "lw" if sv.xlen == 32 else "ld"
    for level in sv.levels_desc:
        for accessed, coverpoint in ((False, f"Abit_unset_{kind}_s"), (True, f"Dbit_unset_{kind}_s")):
            for op in _CBOS[family]:
                expected = "A = 1, D = " + ("1" if family == "zicboz" else "0")
                name = f"l{level}_a{int(accessed)}_d0_{op.replace('.', '_')}"
                chunk.code.extend(
                    [
                        f"// {op} at level {level} with A = {int(accessed)}, D = 0: expected {expected}",
                        *create_page_mapping(sv, leaf_level=level, leaf_flags=PteFlags(accessed=accessed, dirty=False)),
                        "sfence.vma",
                        *virtual_address(sv, "va_data", level, destination=regs.addr, scratch=regs.scratch),
                        test_data.add_testcase(name, coverpoint, "Svadu_cg"),
                        f"{op} (x{regs.addr})",
                        f"LA(x{regs.scratch}, {sv.pte_address(level, sv.data_va)})",
                        f"{load} x{regs.result}, 0(x{regs.scratch})",
                        write_sigupd(regs.result, test_data),
                        "",
                    ]
                )
    chunk.raw_data.extend(sv_data(sv, regs))
    return end_sv_test(test_data, regs)


class _FaultCase(NamedTuple):
    description: str
    level: int
    flags: PteFlags
    va: str = "va_data"


def _ad_clear(*, user: bool = False, read: bool = True, extra: tuple[str, ...] = ()) -> PteFlags:
    return PteFlags(user=user, read=read, accessed=False, dirty=False, extra=extra)


def _fault_cases(sv: SvMode) -> list[_FaultCase]:
    """Return leaf PTEs that must page fault before any A/D update."""
    superpage_levels = range(1, sv.levels)
    rv64_cases = [
        _FaultCase("Reserved bit 54 set", 0, _ad_clear(extra=("(1 << 54)",))),
        _FaultCase("Reserved PBMT=3", 0, _ad_clear(extra=("(3 << 61)",))),
        _FaultCase("N=1 with reserved encoding ppn[3:0]=0000", 0, _ad_clear(extra=("(1 << 63)",))),
        *(
            _FaultCase(
                f"N=1 with ppn[3:0]=1000 on a level {l} superpage", l, _ad_clear(extra=("(1 << 63)", "(1 << 13)"))
            )
            for l in superpage_levels
        ),
    ]
    return [
        *(_FaultCase(f"Misaligned superpage at level {l}", l, _ad_clear(), "va_misaligned") for l in superpage_levels),
        _FaultCase("U page accessed from S-mode with SUM=0", 0, _ad_clear(user=True)),
        _FaultCase("Reserved encoding W=1 R=0", 0, _ad_clear(read=False)),
        *(rv64_cases if sv.xlen == 64 else []),
    ]


def _pte_address(sv: SvMode, regs: SvRegs, va: str, level: int) -> list[str]:
    """Load regs.scratch with the address of the leaf PTE that maps ``va`` at ``level``, using regs.result."""
    scratch, temp = f"x{regs.scratch}", f"x{regs.result}"
    return [
        f"LA({scratch}, {sv.page_table_label(level)})",
        f"LI({temp}, {_pte_offset(sv, va, level)})",
        f"add {scratch}, {scratch}, {temp}",
    ]


def _make_svadu_fault(test_data: TestData, sv: SvMode) -> TestChunk:
    """Access leaf PTEs with A=D=0 that must page fault, then check that D is still clear.

    A faulting access must not update D. A may be set speculatively, so it is not checked.
    """
    fault_vas = {"va_data": sv.data_va, "va_misaligned": _MISALIGNED_VA[sv.name]}
    regs = SvRegs.allocate(test_data)
    chunk = begin_sv_test(
        test_data,
        regs,
        sv,
        "Smode",
        f"{sv.name}_Svadu_fault_Smode",
        coverpoint="cp_ad_fault_no_update",
        va_defs=tuple(fault_vas.items()),
        setup_asm=_enable_adue(sv, regs),
    )
    cases = _fault_cases(sv)
    for number, case in enumerate(cases, start=1):
        chunk.code.extend(
            [
                f"// Test case {number}: {case.description} | A=0 D=0 | expected = RWX page fault, D unchanged",
                *create_page_mapping(
                    sv,
                    virtual_address=case.va,
                    leaf_level=case.level,
                    leaf_flags=case.flags,
                    superpage=case.va != "va_misaligned",
                ),
                "",
                *add_rwx_test(
                    test_data,
                    sv,
                    regs,
                    "Smode",
                    case.va,
                    case.level,
                    f"test{number}",
                    setup=("sfence.vma",),
                    repeat_setup=True,
                    coverpoints=dict.fromkeys(("store", "load", "exec"), "cp_ad_fault_no_update"),
                    covergroup="Svadu_cg",
                ),
                "",
                "// The PTE must still have D=0. A may have been set speculatively, so clear it before the check.",
                *_pte_address(sv, regs, fault_vas[case.va], case.level),
                test_data.add_testcase(f"test{number}_read_pte", "cp_ad_fault_no_update", "Svadu_cg"),
                f"LREG x{regs.result}, 0(x{regs.scratch})",
                f"andi x{regs.result}, x{regs.result}, ~PTE_A",
                write_sigupd(regs.result, test_data),
                "",
            ]
        )
    chunk.raw_data.extend(sv_data(sv, regs))
    chunk.trap_sigupd_count = trap_sigupd_count(len(cases) * 3)
    return end_sv_test(test_data, regs)


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


@add_priv_test_generator(
    "Svadu",
    required_extensions=["Sv32", "Svadu", "Zicbom"],
    march_extensions=["Svadu", "Zicbom"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svadu_sv32_zicbom(test_data: TestData) -> list[TestChunk]:
    return [_make_cbo_adue(test_data, SV32, "zicbom")]


@add_priv_test_generator(
    "Svadu",
    required_extensions=["Sv32", "Svadu", "Zicboz"],
    march_extensions=["Svadu", "Zicboz"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svadu_sv32_zicboz(test_data: TestData) -> list[TestChunk]:
    return [_make_cbo_adue(test_data, SV32, "zicboz")]


@add_priv_test_generator(
    "Svadu",
    required_extensions=["Sv39", "Svadu", "Zicbom"],
    march_extensions=["Svadu", "Zicbom"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svadu_sv39_zicbom(test_data: TestData) -> list[TestChunk]:
    return [_make_cbo_adue(test_data, SV39, "zicbom")]


@add_priv_test_generator(
    "Svadu",
    required_extensions=["Sv39", "Svadu", "Zicboz"],
    march_extensions=["Svadu", "Zicboz"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svadu_sv39_zicboz(test_data: TestData) -> list[TestChunk]:
    return [_make_cbo_adue(test_data, SV39, "zicboz")]


@add_priv_test_generator(
    "Svadu",
    required_extensions=["Sv48", "Svadu", "Zicbom"],
    march_extensions=["Svadu", "Zicbom"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svadu_sv48_zicbom(test_data: TestData) -> list[TestChunk]:
    return [_make_cbo_adue(test_data, SV48, "zicbom")]


@add_priv_test_generator(
    "Svadu",
    required_extensions=["Sv48", "Svadu", "Zicboz"],
    march_extensions=["Svadu", "Zicboz"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svadu_sv48_zicboz(test_data: TestData) -> list[TestChunk]:
    return [_make_cbo_adue(test_data, SV48, "zicboz")]


@add_priv_test_generator(
    "Svadu",
    required_extensions=["Sv57", "Svadu", "Zicbom"],
    march_extensions=["Svadu", "Zicbom"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svadu_sv57_zicbom(test_data: TestData) -> list[TestChunk]:
    return [_make_cbo_adue(test_data, SV57, "zicbom")]


@add_priv_test_generator(
    "Svadu",
    required_extensions=["Sv57", "Svadu", "Zicboz"],
    march_extensions=["Svadu", "Zicboz"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svadu_sv57_zicboz(test_data: TestData) -> list[TestChunk]:
    return [_make_cbo_adue(test_data, SV57, "zicboz")]
