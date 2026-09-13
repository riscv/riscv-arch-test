##################################
# priv/extensions/ZicntrCommon.py
#
# Shared Zicntr test generation for the Sm/S/U counter-enable suites.
# David_Harris@hmc.edu 30 August 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Functions for generating Zicntr counter-enable tests in all priv modes"""

from typing import Literal

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData

Mode = Literal["M", "S", "U"]
Counteren = Literal["ones", "zeros"]

_COUNTERS = ["cycle", "time", "instret"]


def _read_counter(read_reg: int, i: int) -> list[str]:
    """Read counter i (and its high half on RV32)."""
    if i < 3:
        name = _COUNTERS[i]
        return [
            f"csrr x{read_reg}, {name}",
            "#if __riscv_xlen == 32",
            f"csrr x{read_reg}, {name}h",
            "#endif",
        ]
    return [
        "#ifdef ZIHPM_SUPPORTED",
        f"csrr x{read_reg}, hpmcounter{i}",
        "#if __riscv_xlen == 32",
        f"csrr x{read_reg}, hpmcounter{i}h",
        "#endif",
        "#endif",
    ]


def _write_counteren(csr: str, operand: str, mode: Mode, comment: str = "") -> str:
    """Write csr directly when mode can, otherwise through T-SBI: mcounteren is M-mode only,
    scounteren is writable from M and S."""
    instr = f"csrw {csr}, {operand}"
    if comment:
        instr += f"  # {comment}"
    if mode == "M" or (mode == "S" and csr == "scounteren"):
        return instr
    return tsbi_call(instr)


def counteren_walk_tests(
    test_data: TestData,
    covergroup: str,
    coverpoint: str,
    description: str,
    *,
    csrs: list[str],
    mode: Mode,
    mcounteren: Counteren | None = None,
    scounteren_ones: bool = False,
    tag: str = "",
) -> list[str]:
    """
    Walk a 1 and then a 0 through every bit of each CSR in csrs (the same value in each), reading
    every counter after each write. Everything runs in mode; writes that mode cannot make directly
    go through T-SBI. mcounteren optionally presets that register to all ones or all zeros first, and
    scounteren_ones presets scounteren to all ones when S-mode exists.
    tag prefixes the testcase names so a coverpoint tested with several mcounteren settings stays unique.
    """
    read_reg, ones_reg, walk_reg, inv_reg = test_data.int_regs.get_registers(4)
    lines = [comment_banner(coverpoint, description), ""]
    if scounteren_ones:
        lines += [
            "#ifdef S_SUPPORTED",
            f"LI(x{ones_reg}, -1)",
            _write_counteren("scounteren", f"x{ones_reg}", mode, "enable all counters for U-mode"),
            "#endif // S_SUPPORTED",
        ]
    if mcounteren == "ones":
        lines += [
            f"LI(x{ones_reg}, -1)",
            _write_counteren("mcounteren", f"x{ones_reg}", mode, "enable all counters"),
        ]
    elif mcounteren == "zeros":
        lines.append(_write_counteren("mcounteren", "zero", mode, "disable all counters"))

    lines.append(f"LI(x{walk_reg}, 1)")
    for i in range(32):
        lines += [
            test_data.add_testcase(f"{tag}walking_1_{i}", coverpoint, covergroup),
            *(_write_counteren(csr, f"x{walk_reg}", mode, "set only the current bit") for csr in csrs),
            *_read_counter(read_reg, i),
            f"slli x{walk_reg}, x{walk_reg}, 1",
        ]

    lines.append(f"LI(x{walk_reg}, 1)")
    for i in range(32):
        lines += [
            test_data.add_testcase(f"{tag}walking_0_{i}", coverpoint, covergroup),
            f"not x{inv_reg}, x{walk_reg}  # all bits but the current one",
            *(_write_counteren(csr, f"x{inv_reg}", mode, "clear only the current bit") for csr in csrs),
            *_read_counter(read_reg, i),
            f"slli x{walk_reg}, x{walk_reg}, 1",
        ]
    test_data.int_regs.return_registers([read_reg, ones_reg, walk_reg, inv_reg])
    return lines


def _set_counterens(operand: str, mode: Mode) -> list[str]:
    """Write mcounteren, plus scounteren when it also gates the running mode."""
    lines = [_write_counteren("mcounteren", operand, mode)]
    if mode == "U":
        lines += ["#ifdef S_SUPPORTED", _write_counteren("scounteren", operand, mode), "#endif"]
    return lines


def counter_inc_inaccessible_tests(test_data: TestData, covergroup: str, mode: Mode) -> list[str]:
    """Check that instret keeps counting while it is inaccessible in mode."""
    coverpoint = "cp_mcounter_inc_inaccessible"
    description = (
        f"running in {mode} mode\n"
        "enable counters and read instret\n"
        f"disable counters so instret is inaccessible in {mode} mode\n"
        "re-enable counters; the instructions doing so retire while instret is inaccessible\n"
        "read and sigupd change in instret"
    )

    old_reg, read_reg = test_data.int_regs.get_registers(2)

    lines = [
        comment_banner(coverpoint, description),
        "",
        test_data.add_testcase(mode, coverpoint, covergroup),
        f"# make counter accessible in {mode} mode",
        f"LI(x{read_reg}, -1)",
        *_set_counterens(f"x{read_reg}", mode),
        f"csrr x{old_reg}, instret",
        f"# make counter inaccessible in {mode} mode",
        *_set_counterens("zero", mode),
        f"# make counter accessible in {mode} mode",
        *_set_counterens(f"x{read_reg}", mode),
        f"csrr x{read_reg}, instret",
        f"sub x{read_reg}, x{read_reg}, x{old_reg}",
        "# SIGUPD the difference in instret",
        write_sigupd(read_reg, test_data),
    ]
    test_data.int_regs.return_registers([old_reg, read_reg])
    return lines
