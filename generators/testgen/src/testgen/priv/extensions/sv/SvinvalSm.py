##################################
# priv/extensions/sv/SvinvalSm.py
#
# SvinvalSm suite: Svinval instructions with mstatus.TVM set.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate Svinval tests that set and check mstatus.TVM from M-mode."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.sv.modes import BOOT_MMODE
from testgen.priv.extensions.sv.Svinval import MARCH, add_operations
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "SvinvalSm",
    required_extensions=["Sm", "S", "Svinval"],
    march_extensions=MARCH,
    extra_defines=[BOOT_MMODE],
)
def make_svinvalsm_tvm(test_data: TestData) -> list[TestChunk]:
    chunk = test_data.begin_test_chunk("Svinval_mstatus_tvm")
    tvm_label = test_data.add_testcase("tvm", "cp_svinval_tvm", "SvinvalSm_cg").removesuffix(":")
    chunk.code.extend(
        [
            "main:",
            "LI(a0, MSTATUS_TVM)",
            "csrs mstatus, a0",
            f"{tvm_label}:",
            f"RVTEST_SIGUPD_CSR_READ(mstatus, a4, {tvm_label}, {tvm_label}_str)",
            *add_operations(test_data, 1),
            *add_operations(test_data, 2),
            "RVTEST_TSBI_GOTO_SMODE",
            *add_operations(test_data, 3),
            "RVTEST_TSBI_GOTO_MMODE",
            "RVTEST_TSBI_GOTO_UMODE",
            *add_operations(test_data, 4),
            "RVTEST_TSBI_GOTO_MMODE",
        ]
    )
    chunk.sigupd_count = 1
    chunk.trap_sigupd_count = 50
    return [test_data.end_test_chunk()]
