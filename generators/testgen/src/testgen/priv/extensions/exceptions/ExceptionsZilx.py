# SPDX-License-Identifier: Apache-2.0

"""Check indexed-load exceptions when the destination is x0."""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk, trap_sigupd_count
from testgen.instructions.zilx import ZILX_INSTRUCTIONS, indexed_load
from testgen.priv.registry import add_priv_test_generator


def _make_rd_x0(test_data: TestData, mode: str) -> list[TestChunk]:
    covergroup = f"Exceptions_{mode}_cg"
    coverpoint = "cp_zilx_rd_x0_fault"
    chunk = test_data.begin_test_chunk(f"Zilx_rd_x0_{mode}")
    chunk.section_header = comment_banner(coverpoint, "Indexed loads to x0 retain load exceptions")
    addr, index = test_data.int_regs.get_registers(2)
    for mnemonic, instruction in ZILX_INSTRUCTIONS.items():
        if instruction.rv64_only:
            chunk.code.append("#if __riscv_xlen == 64")
        for fault in ("access_fault", "misaligned"):
            if fault == "misaligned" and instruction.size == 1:
                continue
            if fault == "access_fault":
                chunk.code.extend(
                    [
                        "#ifdef RVMODEL_ACCESS_FAULT_ADDRESS_LOAD",
                        f"LI_FIXED_LEN(x{addr}, RVMODEL_ACCESS_FAULT_ADDRESS_LOAD)",
                    ]
                )
                offset = 0
            else:
                chunk.code.append(f"LA(x{addr}, scratch)")
                offset = 1
            setup, load, cleanup = indexed_load(mnemonic, 0, addr, index, offset)
            chunk.code.extend(
                [
                    *setup,
                    test_data.add_testcase(f"{mnemonic}_{fault}", coverpoint, covergroup),
                    load,
                    *cleanup,
                ]
            )
            if fault == "access_fault":
                chunk.code.append("#endif")
        if instruction.rv64_only:
            chunk.code.append("#endif")
    chunk.trap_sigupd_count = trap_sigupd_count(2 * len(ZILX_INSTRUCTIONS))
    test_data.int_regs.return_registers([addr, index])
    return [test_data.end_test_chunk()]


@add_priv_test_generator("Exceptions", required_extensions=["Zilx", "Sm"], extra_defines=["#define BOOT_TO_MMODE"])
def make_exceptions_zilx_rd_x0_m(test_data: TestData) -> list[TestChunk]:
    return _make_rd_x0(test_data, "Sm")


@add_priv_test_generator("Exceptions", required_extensions=["Zilx", "S"], extra_defines=["#define BOOT_TO_SMODE"])
def make_exceptions_zilx_rd_x0_s(test_data: TestData) -> list[TestChunk]:
    return _make_rd_x0(test_data, "S")


@add_priv_test_generator("Exceptions", required_extensions=["Zilx", "Sm", "U"])
def make_exceptions_zilx_rd_x0_u(test_data: TestData) -> list[TestChunk]:
    return _make_rd_x0(test_data, "U")
