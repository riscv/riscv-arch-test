##################################
# priv/extensions/sv/SvZicbo.py
#
# SvZicbo suite: cache-block operations under virtual memory.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate cache-block operation tests under virtual memory."""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.sv.access import virtual_address
from testgen.priv.extensions.sv.generate import sv_data, sv_prologue
from testgen.priv.extensions.sv.page_tables import (
    SV32,
    SV39,
    SV48,
    SV57,
    SvMode,
    create_leaf_pte,
    create_page_mapping,
    create_page_walk,
)
from testgen.priv.registry import add_priv_test_generator

_MARCH = ["I", "Zicsr", "Zifencei"]


def _physical_address(sv: SvMode, pa: str, level: int) -> list[str]:
    if sv.xlen == 32 and level == 0:
        return ["LI(a5, va_data)"]
    shift = level * (10 if sv.xlen == 32 else 9) + 12
    return [
        f"LI(a5, (va_data >> {shift}) << {shift})",
        f"LI(a0, {pa})",
        f"slli a0, a0, {sv.xlen - shift}",
        f"srli a0, a0, {sv.xlen - shift}",
        "add a5, a5, a0",
    ]


def _add_operation(test_data: TestData, family: str, mode: str, address: list[str], number: int) -> list[str]:
    lines = [*address, f"RVTEST_GOTO_LOWER_MODE {mode}"]
    if family == "zicbop":
        for operation in ("prefetch.i", "prefetch.r", "prefetch.w"):
            lines.extend(
                [
                    test_data.add_testcase(f"test{number}_{operation.replace('.', '_')}", "cp_prefetch", "SvZicbo_cg"),
                    f"{operation} 0(a5)",
                    "nop",
                ]
            )
    elif family == "zicbom":
        labels = {
            operation: test_data.add_testcase(f"test{number}_{operation}", "cp_zicbom", "SvZicbo_cg").removesuffix(":")
            for operation in ("clean", "flush", "inval")
        }
        lines.extend(["addi a2, a2, 16"])
        for operation, register in (("clean", "a2"), ("flush", "a3"), ("inval", "a4")):
            lines.extend([f"{labels[operation]}:", f"cbo.{operation} (a5)", f"addi {register}, a2, 4"])
        lines.extend(
            [
                "RVTEST_GOTO_MMODE",
                *(
                    write_sigupd(reg, test_data, label=labels[op])
                    for op, reg in (("clean", 12), ("flush", 13), ("inval", 14))
                ),
            ]
        )
        return lines
    else:
        label = test_data.add_testcase(f"test{number}_zero", "cp_zicboz", "SvZicbo_cg").removesuffix(":")
        lines.extend(
            [
                "addi a2, a2, 16",
                f"{label}:",
                "cbo.zero (a5)",
                "addi a4, a2, 4",
                "RVTEST_GOTO_MMODE",
                write_sigupd(14, test_data, label=label),
            ]
        )
        return lines
    lines.append("RVTEST_GOTO_MMODE")
    return lines


class _ExceptionCases:
    """Build one cache-block exception file."""

    def __init__(self, test_data: TestData, chunk: TestChunk, sv: SvMode, mode: str, family: str) -> None:
        self.test_data = test_data
        self.chunk = chunk
        self.sv = sv
        self.mode = mode
        self.family = family
        self.user_bit = "PTE_U | " if mode == "Umode" else ""
        self.number = 0

    def _walk(
        self,
        level: int,
        *,
        overrides: dict[int, str] | None = None,
        table_addresses: dict[int, str] | None = None,
    ) -> list[str]:
        return create_page_walk(
            self.sv,
            leaf_level=level,
            overrides=overrides,
            table_addresses=table_addresses,
        )

    def _leaf(
        self,
        permissions: str,
        level: int,
        *,
        physical_address: str = "rvtest_data_1",
        superpage: bool | None = None,
    ) -> str:
        return create_leaf_pte(
            self.sv,
            physical_address=physical_address,
            level=level,
            flags=permissions,
            superpage=superpage,
        )

    def add(
        self,
        level: int,
        description: str,
        expected: str,
        pte_lines: list[str],
        *,
        physical_address: str | None = None,
        before: tuple[str, ...] = (),
        after: tuple[str, ...] = (),
        ifdef: str | None = None,
    ) -> None:
        self.number += 1
        address = (
            _physical_address(self.sv, physical_address, level)
            if physical_address is not None
            else virtual_address(self.sv, "va_data", level)
        )
        lines = [
            f"  // Test case {self.number}: {description} | Test in {self.mode[0]}-Mode | expected = {expected}",
            *pte_lines,
            "  sfence.vma",
            *before,
            "",
            *_add_operation(self.test_data, self.family, self.mode, address, self.number),
            *after,
        ]
        if ifdef:
            lines = [f"#ifdef {ifdef}", *lines, "#endif"]
        self.chunk.code.extend([*lines, ""])

    def add_standard(
        self,
        level: int,
        permissions: str,
        description: str,
        expected: str,
        *,
        before: tuple[str, ...] = (),
        after: tuple[str, ...] = (),
        ifdef: str | None = None,
    ) -> None:
        self.add(
            level,
            description,
            expected,
            [*self._walk(level), self._leaf(permissions, level)],
            before=before,
            after=after,
            ifdef=ifdef,
        )

    def add_level(self, level: int) -> None:
        sv = self.sv
        user = self.user_bit
        umode = self.mode == "Umode"
        top = level == sv.levels - 1
        leaf_permissions = f"PTE_D | PTE_A | {user}PTE_X | PTE_W | PTE_R | PTE_V"

        self.add_standard(level, f"PTE_D | PTE_A | {user}PTE_X | PTE_W | PTE_R", "PTE.V unset", "Store page fault")
        self.add_standard(
            level,
            f"PTE_D | PTE_A | {user}PTE_X | PTE_W | PTE_V",
            "Reserved W+X without R",
            "Store page fault",
            ifdef="S1P12P0_OR_LATER_SUPPORTED",
        )
        self.add_standard(
            level,
            f"PTE_D | PTE_A | {user}PTE_W | PTE_V",
            "Reserved W without R",
            "Store page fault",
            ifdef="S1P12P0_OR_LATER_SUPPORTED",
        )
        self.add_standard(
            level,
            f"PTE_D | PTE_A | {user}PTE_X | PTE_R | PTE_V",
            "RX permissions",
            "Store page fault",
        )
        if umode:
            self.add_standard(
                level,
                "PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V",
                "Supervisor page from U-Mode",
                "Store page fault",
            )
        else:
            self.add_standard(
                level,
                "PTE_D | PTE_A | PTE_X | PTE_R | PTE_V",
                "RX permissions with mstatus.SUM set",
                "Store page fault",
                before=("  LI(t0, MSTATUS_SUM)", "  csrs mstatus, t0"),
                after=("  LI(t0, MSTATUS_SUM)", "  csrc mstatus, t0"),
            )
            self.add_standard(
                level,
                "PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V",
                "User page from S-Mode",
                "Store page fault",
            )
        if self.family == "zicbom":
            execute_only = "PTE_D | PTE_A | PTE_U | PTE_X | PTE_V" if umode else "PTE_D | PTE_A | PTE_X | PTE_V"
            self.add_standard(level, execute_only, "Execute-only page", "Store page fault")
        self.add_standard(
            level,
            f"PTE_D | {user}PTE_X | PTE_W | PTE_R | PTE_V",
            "PTE.A unset",
            "Store page fault",
        )
        self.add_standard(
            level,
            f"PTE_A | {user}PTE_X | PTE_W | PTE_R | PTE_V",
            "PTE.D unset",
            "No fault",
        )

        walk = self._walk(level)
        if level > 0:
            self.add(
                level,
                "Misaligned superpage",
                "Store page fault",
                [*walk, self._leaf(leaf_permissions, level, superpage=False)],
                physical_address="0x0",
            )
        else:
            self.add(
                level,
                "Pointer encoding (V only) in the leaf",
                "Store page fault",
                [*walk, self._leaf(f"{user}PTE_V", level)],
            )

        if not top and level > 0:
            self.add(
                level,
                "Access fault on the page-table walk",
                "Store access fault",
                [
                    *self._walk(level, table_addresses={level + 1: "RVMODEL_ACCESS_FAULT_ADDRESS"}),
                    self._leaf(f"PTE_A | PTE_D | {user}PTE_X | PTE_W | PTE_R | PTE_V", level),
                ],
                ifdef="RVMODEL_ACCESS_FAULT_ADDRESS",
            )
        if level == 0:
            self.add(
                level,
                "Access fault on the page-table walk",
                "Store access fault",
                [
                    *self._walk(level, table_addresses={1: "RVMODEL_ACCESS_FAULT_ADDRESS"}),
                    self._leaf(leaf_permissions, level),
                ],
                physical_address="RVMODEL_ACCESS_FAULT_ADDRESS",
                ifdef="RVMODEL_ACCESS_FAULT_ADDRESS",
            )
        self.add(
            level,
            "Leaf PTE points to the access-fault region",
            "Store access fault",
            [*walk, self._leaf(leaf_permissions, level, physical_address="RVMODEL_ACCESS_FAULT_ADDRESS")],
            physical_address="RVMODEL_ACCESS_FAULT_ADDRESS",
            ifdef="RVMODEL_ACCESS_FAULT_ADDRESS",
        )

        if not top:
            for bit in ("PTE_D", "PTE_A", "PTE_U"):
                # The old tests place the A-bit case's leaf at level 0.
                leaf_level = 0 if bit == "PTE_A" and level > 0 else level
                self.add(
                    level,
                    f"Non-leaf PTE with {bit.removeprefix('PTE_')} bit set",
                    "Store page fault",
                    [
                        *self._walk(level, overrides={level + 1: f"{bit} | PTE_V"}),
                        self._leaf(leaf_permissions, leaf_level),
                    ],
                    ifdef="S1P12P0_OR_LATER_SUPPORTED",
                )


def _begin_test(test_data: TestData, sv: SvMode, mode: str, family: str) -> TestChunk:
    chunk = test_data.begin_test_chunk(f"{sv.name}_{family}{'_exceptions' if family != 'zicbop' else ''}_{mode}")
    chunk.section_header = comment_banner(f"cp_{family}")
    envmask = "MENVCFG_CBCFE | MENVCFG_CBIE" if family == "zicbom" else "MENVCFG_CBZE"
    setup = [f"LI(t0, {envmask})", "csrs menvcfg, t0"]
    if mode == "Umode":
        setup.append("csrs senvcfg, t0")
    chunk.code.extend(
        sv_prologue(
            sv,
            mode,
            sig_init="" if family == "zicbop" else "LI(a2, 0x800) // Test signature initialization",
            setup_asm=tuple(setup),
        )
    )
    return chunk


def _make_exceptions(test_data: TestData, sv: SvMode, mode: str, family: str) -> TestChunk:
    chunk = _begin_test(test_data, sv, mode, family)
    cases = _ExceptionCases(test_data, chunk, sv, mode, family)
    for level in sv.levels_desc:
        cases.add_level(level)
    chunk.raw_data.extend(sv_data(sv))
    return test_data.end_test_chunk()


def _make_prefetch(test_data: TestData, sv: SvMode, mode: str) -> TestChunk:
    chunk = _begin_test(test_data, sv, mode, "zicbop")
    user = "PTE_U | " if mode == "Umode" else ""
    for number, level in enumerate(sv.levels_desc, start=1):
        chunk.code.extend(
            [
                *create_page_mapping(
                    sv,
                    leaf_level=level,
                    leaf_flags=f"PTE_D | PTE_A | {user}PTE_X | PTE_W | PTE_R | PTE_V",
                ),
                "sfence.vma",
                "",
                *_add_operation(test_data, "zicbop", mode, virtual_address(sv, "va_data", level), number),
                "",
            ]
        )
    chunk.raw_data.extend(sv_data(sv))
    chunk.trap_sigupd_count = 10
    return test_data.end_test_chunk()


def _make_svzicbo(test_data: TestData, sv: SvMode, family: str) -> list[TestChunk]:
    if family == "zicbop":
        return [_make_prefetch(test_data, sv, mode) for mode in ("Smode", "Umode")]
    return [_make_exceptions(test_data, sv, mode, family) for mode in ("Smode", "Umode")]


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["I", "Sv32", "Zicbom"],
    march_extensions=_MARCH + ["Zicbom"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svzicbo_sv32_zicbom(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV32, "zicbom")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["I", "Sv32", "Zicboz"],
    march_extensions=_MARCH + ["Zicboz"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svzicbo_sv32_zicboz(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV32, "zicboz")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["I", "Sv32", "Zicbop"],
    march_extensions=_MARCH + ["Zicbop"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svzicbo_sv32_zicbop(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV32, "zicbop")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["I", "Sv39", "Zicbom"],
    march_extensions=_MARCH + ["Zicbom"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svzicbo_sv39_zicbom(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV39, "zicbom")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["I", "Sv39", "Zicboz"],
    march_extensions=_MARCH + ["Zicboz"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svzicbo_sv39_zicboz(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV39, "zicboz")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["I", "Sv39", "Zicbop"],
    march_extensions=_MARCH + ["Zicbop"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svzicbo_sv39_zicbop(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV39, "zicbop")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["I", "Sv48", "Zicbom"],
    march_extensions=_MARCH + ["Zicbom"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svzicbo_sv48_zicbom(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV48, "zicbom")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["I", "Sv48", "Zicboz"],
    march_extensions=_MARCH + ["Zicboz"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svzicbo_sv48_zicboz(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV48, "zicboz")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["I", "Sv48", "Zicbop"],
    march_extensions=_MARCH + ["Zicbop"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svzicbo_sv48_zicbop(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV48, "zicbop")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["I", "Sv57", "Zicbom"],
    march_extensions=_MARCH + ["Zicbom"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svzicbo_sv57_zicbom(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV57, "zicbom")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["I", "Sv57", "Zicboz"],
    march_extensions=_MARCH + ["Zicboz"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svzicbo_sv57_zicboz(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV57, "zicboz")


@add_priv_test_generator(
    "SvZicbo",
    required_extensions=["I", "Sv57", "Zicbop"],
    march_extensions=_MARCH + ["Zicbop"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svzicbo_sv57_zicbop(test_data: TestData) -> list[TestChunk]:
    return _make_svzicbo(test_data, SV57, "zicbop")
