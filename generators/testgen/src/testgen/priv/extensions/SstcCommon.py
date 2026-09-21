##################################
# priv/extensions/SstcCommon.py
#
# Shared Sstc test generation for SstcSm and SstcS.
# sanarayanan@hmc.edu April 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Sstc helpers and stimecmp read tests shared by SstcSm and SstcS.

``mode`` is "Sm", "S", or "U". M-mode CSRs are written directly in Sm and through T-SBI
otherwise; U-mode tests are entered from S-mode with RVTEST_TSBI_GOTO_UMODE.
"""

from testgen.asm.helpers import comment_banner
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData

MODE_NAMES = {"Sm": "machine", "S": "supervisor", "U": "user"}
_MODE_LABELS = {"Sm": "M", "S": "S", "U": "U"}


def csr_op(instr: str, mode: str) -> str:
    """An M-mode CSR instruction, issued directly in Sm and through T-SBI otherwise."""
    return instr if mode == "Sm" else tsbi_call(instr)


def mcounteren_tm(reg: int, enable: int, mode: str) -> list[str]:
    return [f"LI(x{reg}, 0x2)", csr_op(f"{'csrs' if enable else 'csrc'} mcounteren, x{reg}", mode)]


def menvcfg_stce(reg: int, enable: bool, mode: str) -> list[str]:
    """Set or clear menvcfg.STCE (menvcfgh on RV32)."""
    op = "csrs" if enable else "csrc"
    return [
        f"# {'Enable' if enable else 'Disable'} menvcfg.STCE{'' if mode == 'Sm' else ' via T-SBI'}",
        "#if __riscv_xlen == 64",
        f"LI(x{reg}, 1)",
        f"slli x{reg}, x{reg}, 63",
        csr_op(f"{op} menvcfg, x{reg}", mode),
        "#else",
        f"LI(x{reg}, 0x80000000)",
        csr_op(f"{op} menvcfgh, x{reg}", mode),
        "#endif",
    ]


def read_stimecmp(reg: int) -> list[str]:
    """Read stimecmp, and stimecmph on RV32."""
    return [
        f"CSRR x{reg}, stimecmp",
        "#if __riscv_xlen == 32",
        f"CSRR x{reg}, stimecmph",
        "#endif",
    ]


def tm_tests(test_data: TestData, covergroup: str, mode: str) -> list[str]:
    """csrr stimecmp with mcounteren.TM={0,1} and STCE=1; U-mode also crosses scounteren.TM={0,1}.

    Below M-mode, TM=0 causes a trap; coverage is sampled at the csrr before the trap.
    scounteren.TM=1 is the suite's resting state; the TM=0 bins clear and restore it under
    #ifdef S_SUPPORTED.
    """
    coverpoint = f"cp_{MODE_NAMES[mode]}_tm"
    r_scratch = test_data.int_regs.get_register()

    lines = [
        comment_banner(coverpoint, f"{_MODE_LABELS[mode]}-mode stimecmp read: mcounteren.TM={{0,1}}"),
        "",
    ]
    stm_vals = [1, 0] if mode == "U" else [1]
    for tm_val in [0, 1]:
        for stm_val in stm_vals:
            binname = f"tm{tm_val}" if mode != "U" else f"tm{tm_val}_stm{stm_val}"
            if not stm_val:
                lines += ["#ifdef S_SUPPORTED", f"LI(x{r_scratch}, 0x2)", f"csrc scounteren, x{r_scratch}"]
            lines += [
                "",
                f"# {coverpoint}: TM={tm_val}" + (f" scounteren.TM={stm_val}" if mode == "U" else ""),
                *menvcfg_stce(r_scratch, True, mode),
                *mcounteren_tm(r_scratch, tm_val, mode),
                *(["RVTEST_TSBI_GOTO_UMODE"] if mode == "U" else []),
                test_data.add_testcase(binname, coverpoint, covergroup),
                *read_stimecmp(r_scratch),
                *(["RVTEST_TSBI_GOTO_SMODE"] if mode == "U" else []),
                *mcounteren_tm(r_scratch, 1, mode),
                *menvcfg_stce(r_scratch, False, mode),
            ]
            if not stm_val:
                lines += [f"LI(x{r_scratch}, 0x2)", f"csrs scounteren, x{r_scratch}", "#endif"]

    test_data.int_regs.return_registers([r_scratch])
    return lines


def stce_tests(test_data: TestData, covergroup: str, mode: str) -> list[str]:
    """csrr stimecmp with menvcfg.STCE={0,1}; mcounteren.TM=1 and scounteren.TM=1 from the suite init.

    Below M-mode, STCE=0 causes a trap; coverage is sampled at the csrr before the trap.
    """
    coverpoint = f"cp_{MODE_NAMES[mode]}_stce"
    r_scratch = test_data.int_regs.get_register()

    lines = [
        comment_banner(coverpoint, f"{_MODE_LABELS[mode]}-mode stimecmp read: menvcfg.STCE={{0,1}}"),
        "",
    ]
    for stce_val in [0, 1]:
        lines += [
            "",
            f"# {coverpoint}: STCE={stce_val}",
            *menvcfg_stce(r_scratch, bool(stce_val), mode),
            *(["RVTEST_TSBI_GOTO_UMODE"] if mode == "U" else []),
            test_data.add_testcase(f"stce{stce_val}", coverpoint, covergroup),
            *read_stimecmp(r_scratch),
            *(["RVTEST_TSBI_GOTO_SMODE"] if mode == "U" else []),
            *menvcfg_stce(r_scratch, False, mode),
        ]

    test_data.int_regs.return_registers([r_scratch])
    return lines
