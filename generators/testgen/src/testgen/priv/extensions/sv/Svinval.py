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


def add_operations(test_data: TestData, number: int) -> list[str]:
    lines = []
    for name, instruction in _OPERATIONS:
        lines.extend(
            [
                test_data.add_testcase(f"test{number}_{name}", "cp_svinval", f"{test_data.testsuite}_cg"),
                instruction,
                "",
            ]
        )
    return lines


@add_priv_test_generator(
    "Svinval",
    required_extensions=["S", "Svinval"],
)
def make_svinval(test_data: TestData) -> list[TestChunk]:
    chunk = test_data.begin_test_chunk("Svinval")
    chunk.code.extend(
        [
            "main:",
            *add_operations(test_data, 1),
            "RVTEST_TSBI_GOTO_UMODE",
            *add_operations(test_data, 2),
            "RVTEST_TSBI_GOTO_SMODE",
        ]
    )
    chunk.trap_sigupd_count = 30
    return [test_data.end_test_chunk()]
