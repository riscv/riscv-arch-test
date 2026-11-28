##################################
# priv/extensions/sv/access.py
#
# Virtual-memory access sequences.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate direct virtual-memory access sequences."""

from collections.abc import Mapping, Sequence
from typing import NamedTuple

from testgen.asm.helpers import load_constant, write_sigupd
from testgen.data.state import TestData
from testgen.priv.extensions.sv.generate import SvRegs
from testgen.priv.extensions.sv.page_tables import SvMode


def virtual_address(
    sv: SvMode,
    va: str,
    level: int,
    *,
    destination: int,
    scratch: int,
    physical_address: str = "rvtest_data_1",
    physical_address_is_label: bool = True,
    merge_sv32_base_page: bool = False,
) -> list[str]:
    """Build a virtual address in x``destination`` from its mapped physical-address offset.

    x``scratch`` is clobbered.
    """
    if sv.xlen == 32 and level == 0 and not merge_sv32_base_page:
        return [load_constant(f"x{destination}", va)]

    shift = sv.page_offset_bits(level)
    return [
        load_constant(f"x{destination}", f"({va} >> {shift}) << {shift}"),
        f"LA(x{scratch}, {physical_address})"
        if physical_address_is_label
        else load_constant(f"x{scratch}", physical_address),
        f"slli x{scratch}, x{scratch}, {sv.xlen - shift}",
        f"srli x{scratch}, x{scratch}, {sv.xlen - shift}",
        f"add x{destination}, x{destination}, x{scratch}",
    ]


class Crosses(NamedTuple):
    """A covergroup and its crosses that sample the store, load and execute testcases of an access test."""

    covergroup: str
    store: str
    load: str
    execute: str

    def by_operation(self) -> dict[str, str]:
        return {"store": self.store, "load": self.load, "exec": self.execute}


def cross_names(*crosses: Crosses) -> str:
    """List the crosses of a test chunk for its banner."""
    return ", ".join(dict.fromkeys(name for cross in crosses for name in (cross.store, cross.load, cross.execute)))


def ad_crosses(covergroup: str, mode: str, *, accessed: bool, infix: str = "") -> Crosses:
    """The Svade and Svadu crosses for one A/D case. PTE.A governs every access, and PTE.D matters only
    to a store to a page with PTE.A set."""
    m = mode[0].lower()
    store = f"Dbit_unset{infix}_write_{m}" if accessed else f"Abit_unset{infix}_write_{m}"
    return Crosses(covergroup, store, f"Abit_unset{infix}_read_{m}", f"Abit_unset{infix}_exec_{m}")


def mode_switch(mode: str, driver_mode: str | None) -> tuple[list[str], list[str]]:
    """Return the T-SBI calls that enter ``mode`` from ``driver_mode`` and return."""
    if driver_mode is None or mode == driver_mode:
        return [], []
    return [f"RVTEST_TSBI_GOTO_{mode.upper()}"], [f"RVTEST_TSBI_GOTO_{driver_mode.upper()}"]


def add_rwx_test(
    test_data: TestData,
    sv: SvMode,
    regs: SvRegs,
    mode: str,
    va: str,
    level: int,
    name: str,
    *,
    driver_mode: str | None = None,
    address: Sequence[str] | None = None,
    setup: Sequence[str] = (),
    cleanup: Sequence[str] = (),
    repeat_setup: bool = False,
    physical_fetch: bool = False,
    include_exec: bool = True,
    operations: Sequence[str] | None = None,
    coverpoints: Mapping[str, str] | None = None,
    covergroup: str | None = None,
    crosses: Crosses | None = None,
) -> list[str]:
    """Add native records and code for one virtual-memory access test.

    ``address`` replaces the default sequence that builds ``va`` in ``regs.addr``. ``repeat_setup`` reruns
    ``setup`` after the store and the load, because a trap taken in M-mode changes mstatus.MPP. ``setup`` and
    ``cleanup`` may use only ``regs.scratch``. ``crosses`` names the covergroup and crosses of the testcases,
    in place of ``covergroup`` and ``coverpoints``. ``operations`` selects a subset of store, load and exec, in
    place of ``include_exec``.
    """
    assert test_data.test_chunk is not None
    if crosses is not None:
        coverpoints, covergroup = crosses.by_operation(), crosses.covergroup
    default_coverpoint = f"cp_{test_data.test_chunk.split_name}"
    if operations is None:
        operations = ("store", "load", "exec") if include_exec else ("store", "load")
    labels = {
        operation: test_data.add_testcase(
            f"{name}_{operation}",
            (coverpoints or {}).get(operation, default_coverpoint),
            covergroup or test_data.testsuite,
        ).removesuffix(":")
        for operation in operations
    }
    enter, leave = mode_switch(mode, driver_mode)
    repeated = setup if repeat_setup else ()
    value, addr, load = (f"x{reg}" for reg in (regs.value, regs.addr, regs.load))
    lines = [
        *(virtual_address(sv, va, level, destination=regs.addr, scratch=regs.scratch) if address is None else address),
        *enter,
        *setup,
        f"addi {value}, {value}, 16",
    ]
    if "store" in labels:
        lines.extend(
            [
                "",
                "// Store",
                f"{labels['store']}:",
                f"sw {value}, 20({addr})",
                "nop",
                *repeated,
            ]
        )
    if "load" in labels:
        lines.extend(
            [
                "",
                "// Load",
                f"{labels['load']}:",
                f"lw {load}, 20({addr})",
                "nop",
                *repeated,
            ]
        )
    if "exec" in labels:
        if physical_fetch:
            # MPRV does not apply to instruction fetch. Clear X in the root PTE that would map rvtest_data_1 if it
            # did, so a hart that translated the fetch with the MPP privilege would take an instruction page fault.
            # The PTE is written with MPRV clear, because an M-mode store with MPRV set is translated.
            lines.extend(
                ["", *cleanup, *_identity_pte_x(sv, regs, executable=False), *setup, f"LA({addr}, rvtest_data_1)"]
            )
        lines.extend(
            [
                "",
                "// Execute",
                f"{labels['exec']}:",
                f"jalr ra, {addr}, 0",
                "nop",
            ]
        )
    if cleanup:
        lines.extend(["", *cleanup])
    if physical_fetch and "exec" in labels:
        lines.extend(_identity_pte_x(sv, regs, executable=True))
    if leave:
        lines.extend(["", *leave])
    lines.append("")
    if "store" in labels:
        lines.append(write_sigupd(regs.value, test_data, label=labels["store"]))
    if "load" in labels:
        lines.append(write_sigupd(regs.load, test_data, label=labels["load"]))
    if "exec" in labels:
        lines.append(write_sigupd(regs.result, test_data, label=labels["exec"]))
    return lines


def _identity_pte_x(sv: SvMode, regs: SvRegs, *, executable: bool) -> list[str]:
    """Clear or set X in the root-level identity PTE that maps rvtest_data_1, using regs.scratch and regs.addr."""
    pte, temp = f"x{regs.scratch}", f"x{regs.addr}"
    top = sv.levels - 1
    return [
        f"// {'Restore' if executable else 'Clear'} X in the root PTE that maps rvtest_data_1",
        f"LA({pte}, rvtest_data_1)",
        f"srli {pte}, {pte}, {sv.page_offset_bits(top)}",
        f"andi {pte}, {pte}, {(1 << sv.index_bits(top)) - 1:#x}",
        f"slli {pte}, {pte}, {sv.pte_bytes.bit_length() - 1}",
        f"LA({temp}, {sv.page_table_label(top)})",
        f"add {pte}, {pte}, {temp}",
        f"LREG {temp}, 0({pte})",
        f"ori {temp}, {temp}, PTE_X" if executable else f"andi {temp}, {temp}, ~PTE_X",
        f"SREG {temp}, 0({pte})",
        "sfence.vma",
    ]
