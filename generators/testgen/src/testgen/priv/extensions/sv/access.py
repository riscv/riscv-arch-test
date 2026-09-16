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


def virtual_address(sv: SvMode, va: str, level: int) -> list[str]:
    if sv.xlen == 32:
        if level == 1:
            return [
                f"LI(a5, ({va} >> 22) << 22)",
                "LA(a0, rvtest_data_1)",
                "slli a0, a0, 10",
                "srli a0, a0, 10",
                "add a5, a5, a0",
            ]
        return [f"LI(a5, {va})"]

    shift = level * 9 + 12
    return [
        f"LI(a5, ({va} >> {shift}) << {shift})",
        "LA(a0, rvtest_data_1)",
        f"slli a0, a0, {sv.xlen - shift}",
        f"srli a0, a0, {sv.xlen - shift}",
        "add a5, a5, a0",
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
