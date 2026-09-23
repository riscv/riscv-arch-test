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

_MARCH = ["I", "Zicsr", "Zifencei"]


def _add_rwx(test_data: TestData, name: str, *, mode: str | None) -> list[str]:
    labels = {
        operation: test_data.add_testcase(f"{name}_{operation}", "cp_bare_access", "Svbare_cg").removesuffix(":")
        for operation in ("store", "load", "exec")
    }
    lines = ["LA(a5, rvtest_data_1)", "addi a2, a2, 16"]
    if mode is not None:
        lines.insert(0, f"RVTEST_GOTO_LOWER_MODE {mode}")
    lines.extend(
        [
            f"{labels['store']}:",
            "sw a2, 20(a5)",
            "nop",
            f"{labels['load']}:",
            "lw a3, 20(a5)",
            "nop",
            f"{labels['exec']}:",
            "jalr ra, a5, 0",
            "nop",
        ]
    )
    if mode is not None:
        lines.append("RVTEST_GOTO_MMODE")
    lines.extend(
        [
            write_sigupd(12, test_data, label=labels["store"]),
            write_sigupd(13, test_data, label=labels["load"]),
            write_sigupd(14, test_data, label=labels["exec"]),
        ]
    )
    return lines


def _begin_bare_test(test_data: TestData, split_name: str) -> TestChunk:
    chunk = test_data.begin_test_chunk(split_name)
    satp_label = test_data.add_testcase("satp_bare", "cp_satp", "Svbare_cg")
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


def _make_bare_mode(test_data: TestData, mode: str) -> list[TestChunk]:
    chunk = _begin_bare_test(test_data, f"Svbare_{mode}mode")
    chunk.code.extend(_add_rwx(test_data, "test1", mode=f"{mode}mode"))
    return [test_data.end_test_chunk()]


@add_priv_test_generator(
    "Svbare",
    required_extensions=["I", "S", "Svbare"],
    march_extensions=_MARCH,
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svbare_smode(test_data: TestData) -> list[TestChunk]:
    return _make_bare_mode(test_data, "S")


@add_priv_test_generator(
    "Svbare",
    required_extensions=["I", "S", "Svbare"],
    march_extensions=_MARCH,
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svbare_umode(test_data: TestData) -> list[TestChunk]:
    return _make_bare_mode(test_data, "U")


@add_priv_test_generator(
    "Svbare",
    required_extensions=["I", "S", "Svbare"],
    march_extensions=_MARCH,
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_svbare_mprv(test_data: TestData) -> list[TestChunk]:
    chunk = _begin_bare_test(test_data, "Svbare_mstatus_mprv")
    for number, mpp in ((1, "S"), (2, "U")):
        label = test_data.add_testcase(f"test{number}_mstatus", "cp_mprv", "Svbare_cg")
        chunk.code.extend(
            [
                "LI(t0, MSTATUS_MPRV)",
                "csrs mstatus, t0",
                "LI(t0, 0x1800)",
                "csrc mstatus, t0",
                *(("LI(t0, 0x800)", "csrs mstatus, t0") if mpp == "S" else ()),
                label,
                gen_csr_read_sigupd(14, ("mstatus", None), test_data),
                *_add_rwx(test_data, f"test{number}", mode=None),
            ]
        )
    return [test_data.end_test_chunk()]
