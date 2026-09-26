##################################
# priv/extensions/ExceptionsHSm.py
#
# ExceptionsHSm hypervisor exception tests whose traps are taken in M-mode.
# David_Harris@hmc.edu 24 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ExceptionsHSm test generator.

The suite boots to M-mode and delegates nothing, so the M-mode handler takes every trap.
"""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk, trap_sigupd_count
from testgen.priv.extensions.ExceptionsHCommon import (
    DELEGATED_FAULTS,
    HEDELEG_WRITABLE,
    hedeleg_tests,
    hlv_priority_tests,
    xtinst_exception_tests,
)
from testgen.priv.extensions.HCommon import HLV_INSTRS, HLVX_INSTRS, HSV_INSTRS, gated
from testgen.priv.registry import add_priv_test_generator

CG = "ExceptionsHSm_cg"


def _ecall_ebreak_tests(test_data: TestData) -> list[str]:
    """ecall and ebreak from each mode; the M-mode trap record holds mstatus.MPP/MPIE/MIE and MPV/GVA."""
    lines = [
        comment_banner(
            "cp_ecall_to_m, cp_ebreak_to_m",
            "With medeleg = 0, ecall and ebreak from M, HS, VS, U and VU modes trap to M-mode",
        )
    ]
    for mode in ("m", "s", "vs", "u", "vu"):
        lines.extend(
            [
                *([f"RVTEST_TSBI_GOTO_{mode.upper()}MODE"] if mode != "m" else []),
                test_data.add_testcase(mode, "cp_ecall_to_m", CG),
                "RVTEST_TSBI_ECALL_RECORD",
                test_data.add_testcase(mode, "cp_ebreak_to_m", CG),
                "ebreak",
                *(["RVTEST_TSBI_GOTO_MMODE"] if mode != "m" else []),
            ]
        )
    return lines


def _hlv_fault_tests(test_data: TestData) -> list[str]:
    """Every hlv, hlvx and hsv in M-mode at each address offset 0-7 of scratch and at the access-fault address.

    vsatp and hgatp are Bare, so each guest virtual address is a physical address.  Misaligned accesses may
    succeed or trap; hsv results are read back from scratch.
    """
    addr_reg, data_reg, rd = test_data.int_regs.get_registers(3)
    lines = [
        comment_banner(
            "cp_hlv_address_misaligned, cp_hsv_address_misaligned",
            "In M-mode, execute each hlv, hlvx and hsv at scratch + 0-7",
        )
    ]
    for instr, rv64 in (*HLV_INSTRS, *HLVX_INSTRS):
        for offset in range(8):
            body = [
                f"LA(x{addr_reg}, scratch)",
                f"addi x{addr_reg}, x{addr_reg}, {offset}",
                f"LI(x{rd}, 42)",
                test_data.add_testcase(f"{instr}_off{offset}", "cp_hlv_address_misaligned", CG),
                f"{instr} x{rd}, (x{addr_reg})",
                write_sigupd(rd, test_data),
            ]
            lines.extend(gated(body, "__riscv_xlen == 64" if rv64 else None))
    for instr, rv64 in HSV_INSTRS:
        for offset in range(8):
            body = [
                f"LA(x{addr_reg}, scratch)",
                f"addi x{addr_reg}, x{addr_reg}, {offset}",
                f"LI(x{data_reg}, {0x1122334455667788 if rv64 else 0x55667788:#x})",
                test_data.add_testcase(f"{instr}_off{offset}", "cp_hsv_address_misaligned", CG),
                f"{instr} x{data_reg}, (x{addr_reg})",
                f"LA(x{addr_reg}, scratch)",
            ]
            for word in (0, 4, 8, 12):
                body.extend([f"lw x{rd}, {word}(x{addr_reg})", write_sigupd(rd, test_data)])
            lines.extend(gated(body, "__riscv_xlen == 64" if rv64 else None))
    fault_lines = [
        comment_banner(
            "cp_hlv_access_fault, cp_hsv_access_fault",
            "In M-mode, execute each hlv, hlvx and hsv at the access-fault address",
        ),
        f"LA(x{addr_reg}, RVMODEL_ACCESS_FAULT_ADDRESS)",
    ]
    for instr, rv64 in (*HLV_INSTRS, *HLVX_INSTRS):
        body = [
            f"LI(x{rd}, 42)",
            test_data.add_testcase(instr, "cp_hlv_access_fault", CG),
            f"{instr} x{rd}, (x{addr_reg})",
            write_sigupd(rd, test_data),
        ]
        fault_lines.extend(gated(body, "__riscv_xlen == 64" if rv64 else None))
    for instr, rv64 in HSV_INSTRS:
        body = [test_data.add_testcase(instr, "cp_hsv_access_fault", CG), f"{instr} x{data_reg}, (x{addr_reg})"]
        fault_lines.extend(gated(body, "__riscv_xlen == 64" if rv64 else None))
    test_data.int_regs.return_registers([addr_reg, data_reg, rd])
    return [*lines, *gated(fault_lines, "defined(RVMODEL_ACCESS_FAULT_ADDRESS)")]


@add_priv_test_generator(
    "ExceptionsHSm",
    required_extensions=["Sm", "H"],
    extra_defines=["#define BOOT_TO_MMODE"],
    # VS and VU traps need the visible trap handler
    params=["TIME_CSR_IMPLEMENTED: true"],
)
def make_exceptionshsm(test_data: TestData) -> list[TestChunk]:
    """Generate tests for the ExceptionsHSm hypervisor exception testsuite."""
    test_chunks: list[TestChunk] = []
    # hedeleg matters only for traps from VS and VU, and with medeleg = 0 not even there, so none and all of its
    # writable bits suffice
    for mode in ("vs", "vu"):
        tc = test_data.new_test_chunk(test_chunks, f"hedeleg_{mode}")
        tc.code.extend(hedeleg_tests(test_data, CG, mode, "m", (0, HEDELEG_WRITABLE)))
        tc.trap_sigupd_count = trap_sigupd_count(2 * DELEGATED_FAULTS)

    tc = test_data.new_test_chunk(test_chunks, "ecall")
    tc.code.extend(_ecall_ebreak_tests(test_data))

    tc = test_data.new_test_chunk(test_chunks, "hlv")
    tc.code.extend([*_hlv_fault_tests(test_data), *hlv_priority_tests(test_data, CG, "m", "m")])

    tc = test_data.new_test_chunk(test_chunks, "xtinst")
    tc.code.extend(xtinst_exception_tests(test_data, CG, "m"))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
