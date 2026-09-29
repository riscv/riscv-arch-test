##################################
# priv/extensions/SstcCommon.py
#
# Shared Sstc test generation for SstcSm and Sstc.
# sanarayanan@hmc.edu April 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Sstc helpers and stimecmp read tests shared by SstcSm and Sstc.

``mode`` is "machine", "supervisor" or "user", as in the coverpoint names.  M-mode CSRs are written directly in
machine mode and through T-SBI otherwise; user-mode tests are entered from S-mode with RVTEST_TSBI_GOTO_UMODE.
"""

from testgen.asm.csr import write_stce
from testgen.asm.helpers import comment_banner
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData


def csr_op(instr: str, mode: str) -> str:
    """An M-mode CSR instruction, issued directly in machine mode and through T-SBI otherwise."""
    return instr if mode == "machine" else tsbi_call(instr)


def mcounteren_tm(test_data: TestData, enable: bool, mode: str) -> list[str]:
    """Set or clear mcounteren.TM (bit 1)."""
    reg = test_data.int_regs.get_register()
    lines = [f"LI(x{reg}, 0x2)", csr_op(f"{'csrs' if enable else 'csrc'} mcounteren, x{reg}", mode)]
    test_data.int_regs.return_register(reg)
    return lines


def access_stimecmp(test_data: TestData) -> list[str]:
    """Read stimecmp, and stimecmph on RV32, to check whether the reads are permitted; the values are discarded."""
    reg = test_data.int_regs.get_register()
    lines = [
        f"csrr x{reg}, stimecmp",
        "#if __riscv_xlen == 32",
        f"csrr x{reg}, stimecmph",
        "#endif",
    ]
    test_data.int_regs.return_register(reg)
    return lines


def tm_tests(test_data: TestData, covergroup: str, mode: str) -> list[str]:
    """Read stimecmp with mcounteren.TM = 0/1 and STCE = 1; user mode also crosses scounteren.TM = 0/1.

    Below M-mode, TM = 0 makes the read trap; coverage is sampled at the csrr before the trap.  The suite rests
    with mcounteren.TM = scounteren.TM = 1 and STCE = 0, and these tests restore that state.
    """
    coverpoint = f"cp_{mode}_tm"
    user = mode == "user"
    lines = [
        comment_banner(coverpoint, f"{mode[0].upper()}-mode stimecmp read: mcounteren.TM = 0/1, STCE = 1"),
        "",
        *write_stce(test_data, True, mode[0].upper()),
    ]
    for tm_val in (0, 1):
        lines += mcounteren_tm(test_data, bool(tm_val), mode)
        for stm_val in (1, 0) if user else (1,):
            lines += [
                "",
                f"# {coverpoint}: TM = {tm_val}" + (f", scounteren.TM = {stm_val}" if user else ""),
                *([] if stm_val else ["csrci scounteren, 0x2"]),
                *(["RVTEST_TSBI_GOTO_UMODE"] if user else []),
                test_data.add_testcase(f"tm{tm_val}_stm{stm_val}" if user else f"tm{tm_val}", coverpoint, covergroup),
                *access_stimecmp(test_data),
                *(["RVTEST_TSBI_GOTO_SMODE"] if user else []),
                *([] if stm_val else ["csrsi scounteren, 0x2"]),
            ]
    return [*lines, "", *write_stce(test_data, False, mode[0].upper())]


def stce_tests(test_data: TestData, covergroup: str, mode: str) -> list[str]:
    """Read stimecmp with menvcfg.STCE = 0/1; mcounteren.TM = scounteren.TM = 1 from the suite's resting state.

    Below M-mode, STCE = 0 makes the read trap; coverage is sampled at the csrr before the trap.
    """
    coverpoint = f"cp_{mode}_stce"
    user = mode == "user"
    lines = [comment_banner(coverpoint, f"{mode[0].upper()}-mode stimecmp read: menvcfg.STCE = 0/1"), ""]
    for stce_val in (0, 1):
        lines += [
            "",
            f"# {coverpoint}: STCE = {stce_val}",
            *write_stce(test_data, bool(stce_val), mode[0].upper()),
            *(["RVTEST_TSBI_GOTO_UMODE"] if user else []),
            test_data.add_testcase(f"stce{stce_val}", coverpoint, covergroup),
            *access_stimecmp(test_data),
            *(["RVTEST_TSBI_GOTO_SMODE"] if user else []),
        ]
    return [*lines, "", *write_stce(test_data, False, mode[0].upper())]
