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


def add_operations(test_data: TestData, number: int, covergroup: str) -> list[str]:
    lines = []
    for name, instruction in _OPERATIONS:
        lines.extend(
            [
                test_data.add_testcase(f"test{number}_{name}", "cp_svinval", covergroup),
                instruction,
                "",
            ]
        )
    return lines


@add_priv_test_generator(
    "Svinval",
    required_extensions=["S", "Svinval"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svinval(test_data: TestData) -> list[TestChunk]:
    chunk = test_data.begin_test_chunk("Svinval")
    chunk.code.extend(
        [
            *add_operations(test_data, 1, "Svinval_cg"),
            "RVTEST_TSBI_GOTO_UMODE",
            *add_operations(test_data, 2, "Svinval_cg"),
            "RVTEST_TSBI_GOTO_SMODE",
        ]
    )
    chunk.trap_sigupd_count = 8
    return [test_data.end_test_chunk()]


@add_priv_test_generator(
    "Svinval",
    required_extensions=["Sm", "S", "Svinval"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svinvalsm_tvm(test_data: TestData) -> list[TestChunk]:
    tvm_reg = test_data.int_regs.get_register(exclude_regs=[0])
    chunk = test_data.begin_test_chunk("Sm_Svinval_mstatus_tvm")
    # The mstatus readback checks the setup that the cp_tvm coverpoint samples.
    tvm_label = test_data.add_testcase("tvm", "cp_tvm", "Svinval_Sm_cg").removesuffix(":")
    number = 0
    code: list[str] = []
    for tvm in (0, 1):
        if tvm:
            code.extend(
                [
                    f"LI(x{tvm_reg}, MSTATUS_TVM)",
                    f"csrs mstatus, x{tvm_reg}",
                    f"{tvm_label}:",
                    f"RVTEST_SIGUPD_CSR_READ(mstatus, x{tvm_reg}, {tvm_label}, {tvm_label}_str)",
                ]
            )
        previous = "Mmode"
        for mode in ("Mmode", "Smode", "Umode"):
            number += 1
            switch = [] if mode == previous else [f"RVTEST_TSBI_GOTO_{mode.upper()}"]
            code.extend([*switch, *add_operations(test_data, number, "Svinval_Sm_cg")])
            previous = mode
        if previous != "Mmode":
            code.append("RVTEST_TSBI_GOTO_MMODE")
    chunk.code.extend(code)
    chunk.sigupd_count = 1
    chunk.trap_sigupd_count = 20
    test_data.int_regs.return_register(tvm_reg)
    return [test_data.end_test_chunk()]
