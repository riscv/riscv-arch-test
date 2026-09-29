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
from testgen.priv.extensions.sv.generate import SvRegs, data_region, end_sv_test
from testgen.priv.registry import add_priv_test_generator


def bare_rwx(
    test_data: TestData, regs: SvRegs, name: str, *, enter: tuple[str, ...] = (), leave: tuple[str, ...] = ()
) -> list[str]:
    value, addr = f"x{regs.value}", f"x{regs.addr}"
    lines = [*enter, f"LA({addr}, rvtest_data_1)", f"addi {value}, {value}, 16"]
    for operation, register, instruction in (
        ("store", regs.value, f"sw {value}, 20({addr})"),
        ("load", regs.load, f"lw x{regs.load}, 20({addr})"),
        ("exec", regs.result, f"jalr ra, {addr}, 0"),
    ):
        lines.append(test_data.add_testcase(f"{name}_{operation}", "cp_bare_access", f"{test_data.testsuite}_cg"))
        lines.extend([instruction, write_sigupd(register, test_data, label=test_data.current_testcase_label)])
    lines.extend(leave)
    return lines


def begin_bare_test(test_data: TestData, regs: SvRegs, split_name: str) -> TestChunk:
    chunk = test_data.begin_test_chunk(split_name)
    satp_label = test_data.add_testcase("satp_bare", "cp_satp", f"{test_data.testsuite}_cg")
    chunk.code.extend(
        [
            f"LI(x{regs.value}, 0x800)",
            "csrw satp, x0",
            satp_label,
            gen_csr_read_sigupd(regs.result, ("satp", None), test_data),
        ]
    )
    chunk.raw_data.extend(data_region(regs))
    chunk.trap_sigupd_count = 10
    return chunk


@add_priv_test_generator(
    "Svbare",
    required_extensions=["Svbare"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svbare_smode(test_data: TestData) -> list[TestChunk]:
    regs = SvRegs.allocate(test_data)
    chunk = begin_bare_test(test_data, regs, "Svbare_Smode")
    chunk.code.extend(bare_rwx(test_data, regs, "test1"))
    return [end_sv_test(test_data, regs)]


@add_priv_test_generator(
    "Svbare",
    required_extensions=["Svbare"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_svbare_umode(test_data: TestData) -> list[TestChunk]:
    regs = SvRegs.allocate(test_data)
    chunk = begin_bare_test(test_data, regs, "Svbare_Umode")
    chunk.code.extend(
        bare_rwx(test_data, regs, "test1", enter=("RVTEST_TSBI_GOTO_UMODE",), leave=("RVTEST_TSBI_GOTO_SMODE",))
    )
    return [end_sv_test(test_data, regs)]
