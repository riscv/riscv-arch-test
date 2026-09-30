##################################
# priv/extensions/SmcntrpmfH.py
#
# Smcntrpmf privilege mode filtering of cycle and instret in VS-mode and VU-mode.
# David_Harris@hmc.edu 29 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""SmcntrpmfH test generator.

The suite boots to M-mode.  Each testcase sets mcyclecfg or minstretcfg to inhibit every mode, or every mode
but VS or VU, reads the counter in M-mode, runs a few instructions in VS or VU and reads the counter again in
M-mode.  With every mode inhibited the counter must not change.  With only VS or VU counting, mcycle must
advance, and minstret must advance by exactly the instructions retired in that mode: the mret that enters the
mode originates in M-mode and the ecall that leaves it does not retire.
"""

from typing import Literal

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

_CG = "SmcntrpmfH_cg"
_INH_BITS = ("MINH", "SINH", "UINH", "VSINH", "VUINH")
# Instructions run in the mode under test, before RVTEST_TSBI_GOTO_MMODE
_BODY_INSTRUCTIONS = 4


def _write_cfg(csr: str, inhibits: list[str], reg: int) -> list[str]:
    """Write the xINH bits of mcyclecfg or minstretcfg (bits 63:32, in the upper-half CSR on RV32)."""
    return [
        "#if __riscv_xlen == 64",
        f"LI(x{reg}, {' | '.join(f'MHPMEVENT_{bit}' for bit in inhibits)})",
        f"csrw {csr}, x{reg}",
        "#else",
        f"LI(x{reg}, {' | '.join(f'MHPMEVENTH_{bit}' for bit in inhibits)})",
        f"csrw {csr}h, x{reg}",
        f"csrw {csr}, zero",
        "#endif",
    ]


def _filter_tests(test_data: TestData, counter: Literal["cycle", "instret"], mode: Literal["VS", "VU"]) -> list[str]:
    """Count counter across a visit to mode with every mode inhibited, then with only mode counting."""
    csr = f"m{counter}cfg"
    coverpoint = f"cp_{csr}_{mode.lower()}"
    base_reg, val_reg, body_reg = test_data.int_regs.get_registers(3)
    lines = [
        comment_banner(
            coverpoint,
            f"Read m{counter} in M-mode, run {_BODY_INSTRUCTIONS} instructions in {mode}-mode and read it again, "
            f"with {csr} inhibiting\nevery mode (no change), then every mode but {mode} "
            + ("(mcycle advances)" if counter == "cycle" else f"(minstret advances by the {mode} instructions)"),
        ),
    ]
    for count_only in (False, True):
        inhibits = [bit for bit in _INH_BITS if not (count_only and bit.startswith(mode))]
        lines.extend(
            [
                *_write_cfg(csr, inhibits, val_reg),
                f"csrr x{base_reg}, m{counter}",
                f"RVTEST_TSBI_GOTO_{mode}MODE",
                test_data.add_testcase(f"count_only_{mode.lower()}" if count_only else "inhibit_all", coverpoint, _CG),
                *(
                    f"addi x{body_reg}, x{body_reg}, 1    # instruction retired in {mode}-mode"
                    for _ in range(_BODY_INSTRUCTIONS)
                ),
                "RVTEST_TSBI_GOTO_MMODE",
                f"csrr x{val_reg}, m{counter}",
                f"sub x{val_reg}, x{val_reg}, x{base_reg}",
                *([f"snez x{val_reg}, x{val_reg}    # the number of cycles varies"] if counter == "cycle" else []),
                write_sigupd(val_reg, test_data),
            ]
        )
    lines.append(f"csrw {csr}, zero")
    lines.extend(["#if __riscv_xlen == 32", f"csrw {csr}h, zero", "#endif"])
    test_data.int_regs.return_registers([base_reg, val_reg, body_reg])
    return lines


@add_priv_test_generator(
    "SmcntrpmfH",
    required_extensions=["H", "Smcntrpmf"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_smcntrpmfh(test_data: TestData) -> list[TestChunk]:
    """Generate tests for SmcntrpmfH coverpoints."""
    test_chunks: list[TestChunk] = []
    tc = test_data.new_test_chunk(test_chunks)
    tc.code.append("csrci mcountinhibit, MCOUNTINHIBIT_CY | MCOUNTINHIBIT_IR    # mcycle and minstret count")
    counters: tuple[Literal["cycle", "instret"], ...] = ("cycle", "instret")
    modes: tuple[Literal["VS", "VU"], ...] = ("VS", "VU")
    for counter in counters:
        for mode in modes:
            tc.code.extend(_filter_tests(test_data, counter, mode))
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
