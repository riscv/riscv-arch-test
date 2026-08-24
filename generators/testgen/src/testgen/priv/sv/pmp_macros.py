##################################
# priv/sv/pmp_macros.py
#
# Shared assembly blocks for the PMP-under-virtual-memory suites.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Assembly building blocks shared by the PMP suites.

Every suite here configures one PMP entry and then runs an ordinary Sv
page-table test through it, so the page-table walk, the access batteries and
the file skeleton all come from :mod:`testgen.priv.sv`. Only the PMP setup
blocks and the data-section alignment are PMP-specific, and they live here.
"""

from __future__ import annotations

from testgen.priv.sv.macros import HR, template
from testgen.priv.sv.model import SvMode

# NUM_PMP_ENTRIES gate shared by every PMP test
PARAMS = ("NUM_PMP_ENTRIES: '>0'",)

# All PMP tests stay in M-mode until a runner drops to the test mode
DEFINES = ("#define BOOT_TO_MMODE",)

# Clear any inherited PMP configuration before programming the entry under test
BACKGROUND = ("  RVTEST_PMP_SET_BACKGROUND t2",)

# Program pmpaddr<n> as a NAPOT region covering the test data region.
_DATA_NAPOT = template("data_napot")

# Program pmpaddr0 as a NAPOT region covering one page table.
_TABLE_NAPOT = template("table_napot")

# Write pmpcfg0 and record the readback in the signature.
_CFG_WRITE = template("cfg_write")


def data_napot(entry: int, sfence: bool = True) -> tuple[str, ...]:
    """Lines programming pmpaddr<entry> to cover the test data region.

    ``sfence`` appends the trailing ``sfence.vma``; the Zicbo suites instead write
    pmpcfg0 immediately after the address and fence once at the end of that block.
    """
    lines = _DATA_NAPOT.format(n=entry).splitlines()
    return tuple(lines if sfence else lines[:-1])


def table_napot(table: str) -> tuple[str, ...]:
    """Lines programming pmpaddr0 to cover one page table."""
    return tuple(_TABLE_NAPOT.format(table=table).splitlines())


def cfg_write(cfg: str, label: str) -> tuple[str, ...]:
    """Lines writing ``cfg`` into pmpcfg0 under signature label ``label``."""
    return tuple(_CFG_WRITE.format(cfg=cfg, label=label).splitlines())


def cfg_str(label: str, what: str) -> tuple[str, str]:
    """The signature string entry that goes with :func:`cfg_write`."""
    return (label, f"Mismatch in pmpcfg0{what}")


_CFG_PERMS = {"RX": "PMP_X | PMP_R", "RW": "PMP_W | PMP_R", "X": "PMP_X"}


def cfg_defines(entry: int, *names: str) -> str:
    """The "// PMP Macros" block defining the PMP<entry>CFG_<name> constants a file uses."""
    lines = ["", "// PMP Macros"]
    for name in names:
        macro = f"PMP{entry}CFG_{name}"
        lines.append(f"#define {macro:<22}(((PMP_NAPOT | {_CFG_PERMS[name]}) & 0xFF) << PMP{entry}_CFG_SHIFT)")
    return "\n".join(lines)


def pt_table(sv: SvMode, level: int) -> str:
    """Name of the page table holding the PTE for a leaf at ``level``."""
    return "rvtest_Sroot_pg_tbl" if level == sv.levels - 1 else f"rvtest_slvl{level}_pg_tbl"


# The executable test region, wrapped in PMP-granularity alignment so the NAPOT
# entry above can cover it exactly.
DATA_REGION_ALIGNED = template("data_region_aligned")

_PLAIN_REGION = template("plain_region")


def data_and_aligned_tables(sv: SvMode) -> str:
    """Plain test region followed by PMP-granularity-aligned page tables.

    Used by the suites that put the PMP entry on a page table rather than on the
    data region, so each table has to start on a granularity boundary.
    """
    lines = [_PLAIN_REGION.strip("\n"), "", HR, "", "// Page Tables", ".p2align 12"]
    for j in range(sv.levels - 1):
        lines += [".p2align (UDB_PMP_GRANULARITY)", f"rvtest_slvl{j}_pg_tbl:", "    .skip(4096)"]
    lines.append(".p2align (UDB_PMP_GRANULARITY)")
    return "\n".join(lines)
