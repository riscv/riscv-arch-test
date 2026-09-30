##################################
# priv/extensions/sv/page_tables.py
#
# RISC-V page-table assembly helpers.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Define Sv translation modes and generate page-table assembly."""

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class SvMode:
    """Properties of one satp address-translation mode."""

    name: str
    xlen: int
    levels: int
    data_va: str
    code_va: str
    page_names: tuple[str, ...]

    @property
    def extension(self) -> str:
        return self.name.capitalize()

    @property
    def suffix(self) -> str:
        return self.name.upper()

    @property
    def satp_setup(self) -> str:
        return "SATP_SETUP_SV32" if self.xlen == 32 else f"SATP_SETUP_RV64({self.name})"

    @property
    def levels_desc(self) -> range:
        return range(self.levels - 1, -1, -1)

    def page_offset_bits(self, level: int) -> int:
        """Return the untranslated address width for a leaf at ``level``."""
        _check_level(self, level)
        return 12 + level * (10 if self.xlen == 32 else 9)

    def page_table_label(self, level: int) -> str:
        """Return the table that contains a leaf PTE at ``level``."""
        _check_level(self, level)
        return "rvtest_Sroot_pg_tbl" if level == self.levels - 1 else f"rvtest_slvl{level}_pg_tbl"


SV32 = SvMode("sv32", 32, 2, "0x90407000", "0x30000000", ("4KB", "4MB"))
SV39 = SvMode("sv39", 64, 3, "0x140802000", "0x180000000", ("4KB", "2MB", "1GB"))
SV48 = SvMode("sv48", 64, 4, "0x028500403000", "0x030080000000", ("4KB", "2MB", "1GB", "512GB"))
SV57 = SvMode("sv57", 64, 5, "0x07028500403000", "0x03000080000000", ("4KB", "2MB", "1GB", "512GB", "256TB"))
SV_MODES = (SV32, SV39, SV48, SV57)
RV64_SV_MODES = (SV39, SV48, SV57)


@dataclass(frozen=True)
class PteFlags:
    """Page-table entry flags in assembly expression order."""

    valid: bool = True
    read: bool = True
    write: bool = True
    execute: bool = True
    user: bool = False
    global_: bool = False
    accessed: bool = True
    dirty: bool = True
    extra: tuple[str, ...] = ()

    @classmethod
    def nonleaf(cls, *extra: str) -> "PteFlags":
        return cls(read=False, write=False, execute=False, accessed=False, dirty=False, extra=extra)

    def __str__(self) -> str:
        fields = [
            *self.extra,
            *(("PTE_D",) if self.dirty else ()),
            *(("PTE_A",) if self.accessed else ()),
            *(("PTE_G",) if self.global_ else ()),
            *(("PTE_U",) if self.user else ()),
            *(("PTE_X",) if self.execute else ()),
            *(("PTE_W",) if self.write else ()),
            *(("PTE_R",) if self.read else ()),
            *(("PTE_V",) if self.valid else ()),
        ]
        return " | ".join(fields)


PteExpression = PteFlags | str


def _pte_expression(flags: PteExpression) -> str:
    return str(flags)


def _check_level(mode: SvMode, level: int) -> None:
    if level < 0 or level >= mode.levels:
        raise ValueError(f"Leaf level {level} is outside {mode.levels}-level translation")


def create_page_walk(
    mode: SvMode,
    *,
    leaf_level: int,
    virtual_address: str = "va_data",
    overrides: Mapping[int, PteExpression] | None = None,
    table_addresses: Mapping[int, str] | None = None,
) -> list[str]:
    """Emit the non-leaf PTEs above ``leaf_level``."""
    _check_level(mode, leaf_level)
    overrides = overrides or {}
    table_addresses = table_addresses or {}

    lines = []
    for table_level in range(mode.levels - 2, leaf_level - 1, -1):
        pte_level = table_level + 1
        permissions = _pte_expression(overrides.get(pte_level, PteFlags.nonleaf()))
        table_address = table_addresses.get(pte_level, f"rvtest_slvl{table_level}_pg_tbl")
        lines.append(f"PTE_SETUP_{mode.suffix}({table_address}, ({permissions}), {virtual_address}, LEVEL{pte_level})")
    return lines


def create_leaf_pte(
    mode: SvMode,
    *,
    level: int,
    flags: PteExpression,
    virtual_address: str = "va_data",
    physical_address: str = "rvtest_data_1",
    superpage: bool | None = None,
) -> str:
    """Emit one leaf PTE."""
    _check_level(mode, level)
    if superpage is None:
        superpage = level > 0
    macro = "SUPERPAGE_PTE_SETUP" if superpage and level > 0 else "PTE_SETUP"
    return f"{macro}_{mode.suffix}({physical_address}, ({_pte_expression(flags)}), {virtual_address}, LEVEL{level})"


def create_page_mapping(
    mode: SvMode,
    *,
    leaf_level: int,
    leaf_flags: PteExpression,
    virtual_address: str = "va_data",
    physical_address: str = "rvtest_data_1",
    walk_overrides: Mapping[int, PteExpression] | None = None,
    walk_table_addresses: Mapping[int, str] | None = None,
    superpage: bool | None = None,
) -> list[str]:
    """Emit one page-table walk and its leaf PTE."""
    return [
        *create_page_walk(
            mode,
            leaf_level=leaf_level,
            virtual_address=virtual_address,
            overrides=walk_overrides,
            table_addresses=walk_table_addresses,
        ),
        create_leaf_pte(
            mode,
            level=leaf_level,
            flags=leaf_flags,
            virtual_address=virtual_address,
            physical_address=physical_address,
            superpage=superpage,
        ),
    ]
