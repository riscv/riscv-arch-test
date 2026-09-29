##################################
# priv/extensions/sv/page_tables.py
#
# RISC-V page-table assembly helpers.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Define Sv translation modes and generate page-table assembly."""

from collections.abc import Mapping
from dataclasses import dataclass, replace

# Root and lower-level page-table labels of each translation stage
_TABLES = {"s": ("Sroot", "slvl"), "vs": ("Vroot", "vlvl"), "g": ("Hroot", "hlvl")}


@dataclass(frozen=True)
class SvMode:
    """Properties of one address-translation mode and the page tables it walks.

    stage is "s" for satp, "vs" for vsatp, or "g" for hgatp.  A G-stage mode (Sv32x4, Sv39x4) translates
    guest physical addresses, which its "virtual address" arguments then name, and its root table has two
    more index bits.
    """

    name: str
    xlen: int
    levels: int
    data_va: str
    code_va: str
    page_names: tuple[str, ...]
    stage: str = "s"

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

    @property
    def atp_mode(self) -> int:
        """The MODE field of satp, vsatp or hgatp for this mode, in position."""
        return 1 << 31 if self.xlen == 32 else (self.levels + 5) << 60

    @property
    def atp_csr(self) -> str:
        """The CSR that selects this mode: satp, vsatp or hgatp."""
        return {"s": "satp", "vs": "vsatp", "g": "hgatp"}[self.stage]

    def page_offset_bits(self, level: int) -> int:
        """Return the untranslated address width for a leaf at ``level``."""
        _check_level(self, level)
        return 12 + level * (10 if self.xlen == 32 else 9)

    def index_bits(self, level: int) -> int:
        """Return the width of the table index at ``level``."""
        _check_level(self, level)
        widened = self.stage == "g" and level == self.levels - 1
        return (10 if self.xlen == 32 else 9) + (2 if widened else 0)

    def page_table_label(self, level: int) -> str:
        """Return the table that contains a leaf PTE at ``level``."""
        _check_level(self, level)
        root, lower = _TABLES[self.stage]
        return f"rvtest_{root}_pg_tbl" if level == self.levels - 1 else f"rvtest_{lower}{level}_pg_tbl"


SV32 = SvMode("sv32", 32, 2, "0x90407000", "0x30000000", ("4KB", "4MB"))
SV39 = SvMode("sv39", 64, 3, "0x140802000", "0x180000000", ("4KB", "2MB", "1GB"))
SV48 = SvMode("sv48", 64, 4, "0x028500403000", "0x030080000000", ("4KB", "2MB", "1GB", "512GB"))
SV57 = SvMode("sv57", 64, 5, "0x07028500403000", "0x03000080000000", ("4KB", "2MB", "1GB", "512GB", "256TB"))
SV_MODES = (SV32, SV39, SV48, SV57)
RV64_SV_MODES = (SV39, SV48, SV57)

# Guest translation.  The VS-stage modes take the satp modes' default addresses as guest virtual addresses;
# the G-stage defaults are guest physical addresses outside the test image's superpage.
VS_SV32 = replace(SV32, stage="vs")
VS_SV39 = replace(SV39, stage="vs")
VS_SV48 = replace(SV48, stage="vs")
SV32X4 = SvMode("sv32x4", 32, 2, "0xD0407000", "0xC0000000", ("4KB", "4MB"), stage="g")
SV39X4 = SvMode("sv39x4", 64, 3, "0x2C0802000", "0x240000000", ("4KB", "2MB", "1GB"), stage="g")
SV48X4 = SvMode("sv48x4", 64, 4, "0x28500403000", "0x18000000000", ("4KB", "2MB", "1GB", "512GB"), stage="g")
SV57X4 = SvMode(
    "sv57x4", 64, 5, "0x7028500403000", "0x3000000000000", ("4KB", "2MB", "1GB", "512GB", "256TB"), stage="g"
)


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


# TODO: write satp tables with write_pte too, and drop the PTE_SETUP_* macro path and this check
def _check_macro_stage(mode: SvMode) -> None:
    if mode.stage != "s":
        raise ValueError(f"The PTE_SETUP_* macros write satp tables only; write {mode.stage}-stage PTEs with regs")


def write_pte(
    mode: SvMode,
    *,
    level: int,
    flags: PteExpression,
    virtual_address: str,
    physical_address: str,
    regs: tuple[int, int, int],
    va_is_label: bool = False,
    pa_is_label: bool = True,
    superpage: bool = False,
    pa_reg: int | None = None,
) -> list[str]:
    """Emit code that writes one PTE into ``mode``'s table at ``level``, using three scratch registers.

    A label address is loaded with LA at run time; any other address is an assembler constant.  With ``pa_reg``,
    register x{pa_reg} holds the physical address instead.  The PPN is the physical address shifted right by 12,
    or for a superpage by the leaf's page offset width.
    """
    _check_level(mode, level)
    pte, addr, tmp = regs
    shift = mode.page_offset_bits(level)
    ppn_shift = shift if superpage else 12
    size_bits = 2 if mode.xlen == 32 else 3
    table = mode.page_table_label(level)
    if va_is_label:
        top = mode.xlen - mode.index_bits(level)
        lines = [
            f"LA(x{addr}, {virtual_address})",
            f"srli x{addr}, x{addr}, {shift}",
            f"slli x{addr}, x{addr}, {top}",
            f"srli x{addr}, x{addr}, {top - size_bits}",
            f"LA(x{tmp}, {table})",
            f"add x{addr}, x{addr}, x{tmp}",
        ]
    else:
        mask = (1 << mode.index_bits(level)) - 1
        lines = [f"LA(x{addr}, {table} + ((({virtual_address}) >> {shift}) & {mask:#x}) * {1 << size_bits})"]
    if pa_reg is not None or pa_is_label:
        lines.extend(
            [
                *([f"LA(x{pte}, {physical_address})"] if pa_reg is None else []),
                f"srli x{pte}, x{pte if pa_reg is None else pa_reg}, {ppn_shift}",
                f"slli x{pte}, x{pte}, {ppn_shift - 2}",
                f"LI(x{tmp}, {_pte_expression(flags)})",
                f"or x{pte}, x{pte}, x{tmp}",
            ]
        )
    else:
        pte_value = f"(({physical_address}) >> {ppn_shift}) << {ppn_shift - 2}"
        lines.append(f"LI(x{pte}, ({pte_value}) | ({_pte_expression(flags)}))")
    lines.append(f"SREG x{pte}, 0(x{addr})")
    return lines


def create_page_walk(
    mode: SvMode,
    *,
    leaf_level: int,
    virtual_address: str = "va_data",
    overrides: Mapping[int, PteExpression] | None = None,
    table_addresses: Mapping[int, str] | None = None,
    regs: tuple[int, int, int] | None = None,
    va_is_label: bool = False,
) -> list[str]:
    """Emit the non-leaf PTEs above ``leaf_level``.

    Without ``regs`` the satp PTE_SETUP_* macros write them, clobbering a0, a1, t0 and t1.  With ``regs``
    write_pte writes them, in any stage; a VS-stage table address is then a guest physical address.
    """
    _check_level(mode, leaf_level)
    overrides = overrides or {}
    table_addresses = table_addresses or {}

    lines = []
    for table_level in range(mode.levels - 2, leaf_level - 1, -1):
        pte_level = table_level + 1
        permissions = overrides.get(pte_level, PteFlags.nonleaf())
        table_address = table_addresses.get(pte_level, mode.page_table_label(table_level))
        if regs is None:
            _check_macro_stage(mode)
            lines.append(
                f"PTE_SETUP_{mode.suffix}({table_address}, ({_pte_expression(permissions)}), "
                f"{virtual_address}, LEVEL{pte_level})"
            )
        else:
            lines.extend(
                write_pte(
                    mode,
                    level=pte_level,
                    flags=permissions,
                    virtual_address=virtual_address,
                    physical_address=table_address,
                    regs=regs,
                    va_is_label=va_is_label,
                )
            )
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
    """Emit one leaf PTE with the satp PTE_SETUP_* macros; write_pte writes one in any stage."""
    _check_level(mode, level)
    _check_macro_stage(mode)
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
    regs: tuple[int, int, int] | None = None,
    va_is_label: bool = False,
    pa_is_label: bool = True,
) -> list[str]:
    """Emit one page-table walk and its leaf PTE, with the satp macros or, given ``regs``, with write_pte."""
    walk = create_page_walk(
        mode,
        leaf_level=leaf_level,
        virtual_address=virtual_address,
        overrides=walk_overrides,
        table_addresses=walk_table_addresses,
        regs=regs,
        va_is_label=va_is_label,
    )
    if regs is None:
        return [
            *walk,
            create_leaf_pte(
                mode,
                level=leaf_level,
                flags=leaf_flags,
                virtual_address=virtual_address,
                physical_address=physical_address,
                superpage=superpage,
            ),
        ]
    leaf = write_pte(
        mode,
        level=leaf_level,
        flags=leaf_flags,
        virtual_address=virtual_address,
        physical_address=physical_address,
        regs=regs,
        va_is_label=va_is_label,
        pa_is_label=pa_is_label,
        superpage=leaf_level > 0 if superpage is None else superpage,
    )
    return [*walk, *leaf]
