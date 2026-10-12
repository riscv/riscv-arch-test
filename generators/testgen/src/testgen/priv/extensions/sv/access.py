##################################
# priv/extensions/sv/access.py
#
# Virtual-memory access sequences.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate direct virtual-memory access sequences."""

from collections.abc import Mapping, Sequence

from testgen.asm.helpers import write_sigupd
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
        return [f"LI(x{destination}, {va})"]

    shift = sv.page_offset_bits(level)
    load = "LA" if physical_address_is_label else "LI"
    return [
        f"LI(x{destination}, ({va} >> {shift}) << {shift})",
        f"{load}(x{scratch}, {physical_address})",
        f"slli x{scratch}, x{scratch}, {sv.xlen - shift}",
        f"srli x{scratch}, x{scratch}, {sv.xlen - shift}",
        f"add x{destination}, x{destination}, x{scratch}",
    ]


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
    coverpoints: Mapping[str, str] | None = None,
    covergroup: str | None = None,
) -> list[str]:
    """Add native records and code for one virtual-memory access test.

    ``address`` replaces the default sequence that builds ``va`` in ``regs.addr``. ``repeat_setup`` reruns
    ``setup`` after the store and the load, because a trap taken in M-mode changes mstatus.MPP. ``setup`` and
    ``cleanup`` may use only ``regs.scratch``.
    """
    assert test_data.test_chunk is not None
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
    value, addr, load = (f"x{reg}" for reg in (regs.value, regs.addr, regs.load))
    lines = [
        *(virtual_address(sv, va, level, destination=regs.addr, scratch=regs.scratch) if address is None else address),
        *enter,
        *setup,
        f"addi {value}, {value}, 16",
        "",
        "// Store",
        f"{labels['store']}:",
        f"sw {value}, 20({addr})",
        "nop",
        *repeated,
        "",
        "// Load",
        f"{labels['load']}:",
        f"lw {load}, 20({addr})",
        "nop",
        *repeated,
    ]
    if include_exec:
        lines.extend(
            [
                *((f"LA({addr}, rvtest_data_1)",) if physical_fetch else ()),
                "",
                "// Execute",
                f"{labels['exec']}:",
                f"jalr ra, {addr}, 0",
                "nop",
            ]
        )
    if cleanup:
        lines.extend(["", *cleanup])
    if leave:
        lines.extend(["", *leave])
    lines.extend(
        [
            "",
            write_sigupd(regs.value, test_data, label=labels["store"]),
            write_sigupd(regs.load, test_data, label=labels["load"]),
        ]
    )
    if include_exec:
        lines.append(write_sigupd(regs.result, test_data, label=labels["exec"]))
    return lines
