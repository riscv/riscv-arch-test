##################################
# priv/extensions/sv/Svinval.py
#
# Svinval instruction tests.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate Svinval privilege and TVM tests."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

_OPERATIONS = (
    ("sfence_w_inval", "sfence.w.inval"),
    ("sinval_vma", "sinval.vma x0, x0"),
    ("sfence_inval_ir", "sfence.inval.ir"),
    ("sfence_vma", "sfence.vma x0, x0"),
)
_MARCH = ["I", "Zicsr", "Zifencei", "Svinval"]


def _add_operations(test_data: TestData, number: int) -> list[str]:
    lines = []
    for name, instruction in _OPERATIONS:
        lines.extend(
            [
                test_data.add_testcase(f"test{number}_{name}", "cp_svinval", "Svinval_cg"),
                instruction,
                "nop",
                "",
            ]
        )
    return lines


@add_priv_test_generator(
    "Svinval",
    required_extensions=["S", "Svinval"],
    march_extensions=_MARCH,
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svinval(test_data: TestData) -> list[TestChunk]:
    chunk = test_data.begin_test_chunk("Svinval")
    chunk.code.extend(
        [
            "main:",
            "RVTEST_GOTO_LOWER_MODE Smode",
            *_add_operations(test_data, 1),
            "RVTEST_GOTO_MMODE",
            "RVTEST_GOTO_LOWER_MODE Umode",
            *_add_operations(test_data, 2),
            "RVTEST_GOTO_MMODE",
        ]
    )
    chunk.trap_sigupd_count = 30
    return [test_data.end_test_chunk()]


@add_priv_test_generator(
    "Svinval",
    required_extensions=["Sm", "S", "Svinval"],
    march_extensions=_MARCH,
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svinval_tvm(test_data: TestData) -> list[TestChunk]:
    chunk = test_data.begin_test_chunk("Svinval_mstatus_tvm")
    tvm_label = test_data.add_testcase("tvm", "cp_svinval_tvm", "Svinval_cg").removesuffix(":")
    chunk.code.extend(
        [
            "main:",
            "LI(a0, MSTATUS_TVM)",
            "csrs mstatus, a0",
            f"{tvm_label}:",
            f"RVTEST_SIGUPD_CSR_READ(mstatus, a4, {tvm_label}, {tvm_label}_str)",
            *_add_operations(test_data, 1),
            *_add_operations(test_data, 2),
            "RVTEST_GOTO_LOWER_MODE Smode",
            *_add_operations(test_data, 3),
            "RVTEST_GOTO_MMODE",
            "RVTEST_GOTO_LOWER_MODE Umode",
            *_add_operations(test_data, 4),
            "RVTEST_GOTO_MMODE",
        ]
    )
    chunk.sigupd_count = 1
    chunk.trap_sigupd_count = 50
    return [test_data.end_test_chunk()]
