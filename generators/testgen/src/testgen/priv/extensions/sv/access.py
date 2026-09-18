##################################
# priv/extensions/sv/access.py
#
# Virtual-memory access sequences.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate direct virtual-memory access sequences."""

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


def add_rwx_test(
    test_data: TestData,
    sv: SvMode,
    mode: str,
    va: str,
    level: int,
    name: str,
    *,
    direct_address: bool = False,
    enter_lower_mode: bool = True,
    setup: tuple[str, ...] = (),
    cleanup: tuple[str, ...] = (),
    reset_setup_after_store: bool = False,
    physical_fetch: bool = False,
    include_exec: bool = True,
) -> list[str]:
    """Add native records and code for one virtual-memory access test."""
    assert test_data.test_chunk is not None
    coverpoint = f"cp_{test_data.test_chunk.split_name}"
    operations = ("store", "load", "exec") if include_exec else ("store", "load")
    labels = {
        operation: test_data.add_testcase(f"{name}_{operation}", coverpoint, test_data.testsuite).removesuffix(":")
        for operation in operations
    }
    lines = [
        *([f"LI(a5, {va})"] if direct_address else virtual_address(sv, va, level)),
        *setup,
        *([f"RVTEST_GOTO_LOWER_MODE {mode}"] if enter_lower_mode else []),
        "addi a2, a2, 16",
        "",
        "// Store",
        f"{labels['store']}:",
        "sw a2, 20(a5)",
        "nop",
        *([*setup] if reset_setup_after_store else []),
        "",
        "// Load",
        f"{labels['load']}:",
        "lw a3, 20(a5)",
        "nop",
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
    if enter_lower_mode:
        lines.extend(["", "RVTEST_GOTO_MMODE"])
    if cleanup:
        lines.extend(["", *cleanup])
    lines.extend(
        ["", write_sigupd(12, test_data, label=labels["store"]), write_sigupd(13, test_data, label=labels["load"])]
    )
    if include_exec:
        lines.append(write_sigupd(14, test_data, label=labels["exec"]))
    return lines
