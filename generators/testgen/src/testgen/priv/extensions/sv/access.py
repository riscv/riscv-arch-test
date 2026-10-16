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

from testgen.asm.helpers import write_sigupd
from testgen.data.state import TestData
from testgen.priv.extensions.sv.page_tables import SvMode


def virtual_address(
    sv: SvMode,
    va: str,
    level: int,
    *,
    destination: str = "a5",
    physical_address: str = "rvtest_data_1",
    physical_address_is_label: bool = True,
    merge_sv32_base_page: bool = False,
    scratch: str = "a0",
) -> list[str]:
    """Build a virtual address from its mapped physical-address offset."""
    if sv.xlen == 32 and level == 0 and not merge_sv32_base_page:
        return [f"LI({destination}, {va})"]

    shift = sv.page_offset_bits(level)
    load = "LA" if physical_address_is_label else "LI"
    return [
        f"LI({destination}, ({va} >> {shift}) << {shift})",
        f"{load}({scratch}, {physical_address})",
        f"slli {scratch}, {scratch}, {sv.xlen - shift}",
        f"srli {scratch}, {scratch}, {sv.xlen - shift}",
        f"add {destination}, {destination}, {scratch}",
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
    coverpoints: Mapping[str, str] | None = None,
    covergroup: str | None = None,
    crosses: Crosses | None = None,
) -> list[str]:
    """Add native records and code for one virtual-memory access test.

    ``address`` replaces the default sequence that builds ``va`` in a5. ``repeat_setup`` reruns ``setup`` after
    the store and the load, because a trap taken in M-mode changes mstatus.MPP. ``crosses`` names the
    covergroup and crosses of the testcases, in place of ``covergroup`` and ``coverpoints``.
    """
    assert test_data.test_chunk is not None
    if crosses is not None:
        coverpoints, covergroup = crosses.by_operation(), crosses.covergroup
    default_coverpoint = f"cp_{test_data.test_chunk.split_name}"
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
    lines = [
        *(virtual_address(sv, va, level) if address is None else address),
        *enter,
        *setup,
        "addi a2, a2, 16",
        "",
        "// Store",
        f"{labels['store']}:",
        "sw a2, 20(a5)",
        "nop",
        *repeated,
        "",
        "// Load",
        f"{labels['load']}:",
        "lw a3, 20(a5)",
        "nop",
        *repeated,
    ]
    if include_exec:
        lines.extend(
            [
                *(("LA(a5, rvtest_data_1)",) if physical_fetch else ()),
                "",
                "// Execute",
                f"{labels['exec']}:",
                "jalr ra, a5, 0",
                "nop",
            ]
        )
    if cleanup:
        lines.extend(["", *cleanup])
    if leave:
        lines.extend(["", *leave])
    lines.extend(
        ["", write_sigupd(12, test_data, label=labels["store"]), write_sigupd(13, test_data, label=labels["load"])]
    )
    if include_exec:
        lines.append(write_sigupd(14, test_data, label=labels["exec"]))
    return lines
