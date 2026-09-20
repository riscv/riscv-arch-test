##################################
# priv/extensions/sv/SvinvalSm.py
#
# SvinvalSm suite: Svinval instructions in M-mode and under mstatus.TVM.
# umer@riscv.org September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate Svinval tests in every mode with mstatus.TVM clear and set."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.sv.access import enter_mode, leave_mode
from testgen.priv.extensions.sv.Svinval import add_operations
from testgen.priv.registry import add_priv_test_generator

DRIVER = "Mmode"


@add_priv_test_generator(
    "SvinvalSm",
    required_extensions=["Sm", "S", "Svinval"],
    extra_defines=[f"#define BOOT_TO_{DRIVER[0]}MODE"],
)
def make_svinvalsm_tvm(test_data: TestData) -> list[TestChunk]:
    chunk = test_data.begin_test_chunk("Svinval_mstatus_tvm")
    tvm_label = test_data.add_testcase("tvm", "cp_svinval_tvm", "SvinvalSm_cg").removesuffix(":")
    number = 0
    code = ["main:"]
    for tvm in (0, 1):
        if tvm:
            code.extend(
                [
                    "LI(a0, MSTATUS_TVM)",
                    "csrs mstatus, a0",
                    f"{tvm_label}:",
                    f"RVTEST_SIGUPD_CSR_READ(mstatus, a4, {tvm_label}, {tvm_label}_str)",
                ]
            )
        previous = DRIVER
        for mode in ("Mmode", "Smode", "Umode"):
            number += 1
            code.extend([*enter_mode(mode, previous), *add_operations(test_data, number)])
            previous = mode
        code.extend(leave_mode(previous, DRIVER))
    chunk.code.extend(code)
    chunk.sigupd_count = 1
    chunk.trap_sigupd_count = 80
    return [test_data.end_test_chunk()]
