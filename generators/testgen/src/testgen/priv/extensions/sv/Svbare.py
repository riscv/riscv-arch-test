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
from testgen.priv.extensions.sv.modes import BOOT_SMODE
from testgen.priv.registry import add_priv_test_generator

_MARCH = ["I", "Zicsr", "Zifencei"]


def bare_rwx(test_data: TestData, name: str, *, enter: tuple[str, ...] = (), leave: tuple[str, ...] = ()) -> list[str]:
    labels = {
        operation: test_data.add_testcase(
            f"{name}_{operation}", "cp_bare_access", f"{test_data.testsuite}_cg"
        ).removesuffix(":")
        for operation in ("store", "load", "exec")
    }
    return [
        *enter,
        "LA(a5, rvtest_data_1)",
        "addi a2, a2, 16",
        f"{labels['store']}:",
        "sw a2, 20(a5)",
        "nop",
        f"{labels['load']}:",
        "lw a3, 20(a5)",
        "nop",
        f"{labels['exec']}:",
        "jalr ra, a5, 0",
        "nop",
        *leave,
        write_sigupd(12, test_data, label=labels["store"]),
        write_sigupd(13, test_data, label=labels["load"]),
        write_sigupd(14, test_data, label=labels["exec"]),
    ]


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
    required_extensions=["I", "S"],
    march_extensions=_MARCH,
    extra_defines=[BOOT_SMODE],
)
def make_svbare_smode(test_data: TestData) -> list[TestChunk]:
    chunk = begin_bare_test(test_data, "Svbare_Smode")
    chunk.code.extend(bare_rwx(test_data, "test1"))
    return [test_data.end_test_chunk()]


@add_priv_test_generator(
    "Svbare",
    required_extensions=["I", "S"],
    march_extensions=_MARCH,
    extra_defines=[BOOT_SMODE],
)
def make_svbare_umode(test_data: TestData) -> list[TestChunk]:
    chunk = begin_bare_test(test_data, "Svbare_Umode")
    chunk.code.extend(
        bare_rwx(test_data, "test1", enter=("RVTEST_TSBI_GOTO_UMODE",), leave=("RVTEST_TSBI_GOTO_SMODE",))
    )
    return [test_data.end_test_chunk()]
