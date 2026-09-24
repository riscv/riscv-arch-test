##################################
# priv/extensions/sv/Svbare.py
#
# Svbare tests.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Generate accesses with address translation disabled."""

from testgen.asm.csr import gen_csr_read_sigupd
from testgen.asm.helpers import write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.sv.assembly import DATA_REGION
from testgen.priv.registry import add_priv_test_generator


def bare_rwx(test_data: TestData, name: str, *, enter: tuple[str, ...] = (), leave: tuple[str, ...] = ()) -> list[str]:
    lines = [*enter, "LA(a5, rvtest_data_1)", "addi a2, a2, 16"]
    for operation, register, instruction in (
        ("store", 12, "sw a2, 20(a5)"),
        ("load", 13, "lw a3, 20(a5)"),
        ("exec", 14, "jalr ra, a5, 0"),
    ):
        lines.append(test_data.add_testcase(f"{name}_{operation}", "cp_bare_access", f"{test_data.testsuite}_cg"))
        # The nop is where the jalr returns, and where the handler resumes if the access faults.
        lines.extend([instruction, "nop", write_sigupd(register, test_data, label=test_data.current_testcase_label)])
    lines.extend(leave)
    return lines


def begin_bare_test(test_data: TestData, split_name: str) -> TestChunk:
    chunk = test_data.begin_test_chunk(split_name)
    satp_label = test_data.add_testcase("satp_bare", "cp_satp", f"{test_data.testsuite}_cg")
    chunk.code.extend(
        [
            "main:",
            "LI(a2, 0x800)",
            "csrw satp, x0",
            satp_label,
            gen_csr_read_sigupd(14, ("satp", None), test_data),
        ]
    )
    chunk.raw_data.extend(DATA_REGION.splitlines())
    chunk.trap_sigupd_count = 10
    return chunk


@add_priv_test_generator(
    "Svbare",
    required_extensions=["Svbare"],
    march_extensions=["Svbare"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svbare_smode(test_data: TestData) -> list[TestChunk]:
    chunk = begin_bare_test(test_data, "Svbare_Smode")
    chunk.code.extend(bare_rwx(test_data, "test1"))
    return [test_data.end_test_chunk()]


@add_priv_test_generator(
    "Svbare",
    required_extensions=["Svbare"],
    march_extensions=["Svbare"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svbare_umode(test_data: TestData) -> list[TestChunk]:
    chunk = begin_bare_test(test_data, "Svbare_Umode")
    chunk.code.extend(
        bare_rwx(test_data, "test1", enter=("RVTEST_TSBI_GOTO_UMODE",), leave=("RVTEST_TSBI_GOTO_SMODE",))
    )
    return [test_data.end_test_chunk()]
