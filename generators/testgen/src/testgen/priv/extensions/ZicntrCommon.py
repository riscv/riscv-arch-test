##################################
# priv/extensions/ZicntrCommon.py
#
# Shared Zicntr test generation for the Sm/S/U counter-enable suites.
# David_Harris@hmc.edu 30 August 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Functions for generating Zicntr counter-enable tests in all priv modes"""

from collections.abc import Sequence

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData

_COUNTERS = ["cycle", "time", "instret"]


def _read_counter(read_reg: int, i: int, mode: str) -> list[str]:
    """Read counter i (and its high half on RV32) in the given mode."""
    if i < 3:
        name = _COUNTERS[i]
        return [f"csrr x{read_reg}, {name}", "#if __riscv_xlen == 32", f"csrr x{read_reg}, {name}h", "#endif"]
    return [
        "#ifdef ZIHPM_SUPPORTED",
        f"csrr x{read_reg}, hpmcounter{i} # read from hpmcounter{i} in {mode}-mode",
        "#if __riscv_xlen == 32",
        f"csrr x{read_reg}, hpmcounter{i}h # read from hpmcounter{i}h in {mode}-mode",
        "#endif",
        "#endif",
    ]


def _write_counteren(csr: str, operand: str, run_mode: str, comment: str = "") -> str:
    """Write csr directly when run_mode can, otherwise through T-SBI: mcounteren is M-mode only,
    scounteren is writable from M and S."""
    instr = f"csrw {csr}, {operand}"
    if comment:
        instr += f"  # {comment}"
    if run_mode == "M" or (run_mode == "S" and csr == "scounteren"):
        return instr
    return tsbi_call(instr)


def walk_counteren(
    test_data: TestData,
    coverpoint: str,
    covergroup: str,
    *,
    csrs: list[str],
    run_mode: str,
    read_mode: str,
    mcounteren: str | None = None,
    tag: str = "",
) -> list[str]:
    """
    Walk a 1 and then a 0 through every bit of each CSR in csrs (the same value in each), reading
    every counter in read_mode after each write. Writes the running mode cannot make directly go
    through T-SBI; reads in a different mode are wrapped in T-SBI mode changes.
    """
    read_reg, ones_reg, walk_reg, inv_reg = test_data.int_regs.get_registers(4)
    lines = []
    if mcounteren == "ones":
        lines.append(f"LI(x{ones_reg}, -1)")
        lines.append(_write_counteren("mcounteren", f"x{ones_reg}", run_mode, "enable all counters in M-mode"))
    elif mcounteren == "zeros":
        lines.append(_write_counteren("mcounteren", "zero", run_mode, "disable all counters in M-mode"))
    elif mcounteren is not None:
        raise ValueError(f"mcounteren must be 'ones', 'zeros', or None, not {mcounteren!r}")

    goto_read = [f"RVTEST_TSBI_GOTO_{read_mode}MODE"] if read_mode != run_mode else []
    goto_back = [f"RVTEST_TSBI_GOTO_{run_mode}MODE"] if read_mode != run_mode else []

    lines.append(f"LI(x{walk_reg}, 1)")
    for i in range(32):
        lines.append(test_data.add_testcase(f"{tag}walking_1_{i}", coverpoint, covergroup))
        lines.extend(_write_counteren(csr, f"x{walk_reg}", run_mode, "set only the current bit") for csr in csrs)
        lines.extend([*goto_read, *_read_counter(read_reg, i, read_mode), *goto_back])
        lines.append(f"slli x{walk_reg}, x{walk_reg}, 1")

    # walking a single 0
    lines.append(f"LI(x{walk_reg}, 1)")
    for i in range(32):
        lines.append(test_data.add_testcase(f"{tag}walking_0_{i}", coverpoint, covergroup))
        lines.append(f"not x{inv_reg}, x{walk_reg}  # all bits but the current one")
        lines.extend(_write_counteren(csr, f"x{inv_reg}", run_mode, "clear only the current bit") for csr in csrs)
        lines.extend([*goto_read, *_read_counter(read_reg, i, read_mode), *goto_back])
        lines.append(f"slli x{walk_reg}, x{walk_reg}, 1")
    test_data.int_regs.return_registers([read_reg, ones_reg, walk_reg, inv_reg])
    return lines


def counteren_walk_tests(
    test_data: TestData,
    covergroup: str,
    coverpoint: str,
    description: str,
    *,
    csrs: list[str],
    run_mode: str,
    read_mode: str,
    mcounteren_settings: Sequence[str | None] = (None,),
) -> list[str]:
    """
    Banner plus one counteren walk per mcounteren setting; multiple settings get testcase name tags
    to stay unique.
    """
    lines = [comment_banner(coverpoint, description), ""]
    for setting in mcounteren_settings:
        tag = f"mcounteren_{setting}_" if len(mcounteren_settings) > 1 else ""
        lines.extend(
            walk_counteren(
                test_data,
                coverpoint,
                covergroup,
                csrs=csrs,
                run_mode=run_mode,
                read_mode=read_mode,
                mcounteren=setting,
                tag=tag,
            )
        )
    return lines


def _set_counterens(operand: str, run_mode: str) -> list[str]:
    """Write mcounteren via T-SBI, plus scounteren when it also gates the running mode."""
    lines = [tsbi_call(f"csrw mcounteren, {operand}")]
    if run_mode == "U":
        lines.extend(["#ifdef S_SUPPORTED", tsbi_call(f"csrw scounteren, {operand}"), "#endif"])
    return lines


def counter_inc_inaccessible_tests(test_data: TestData, covergroup: str, run_mode: str) -> list[str]:
    """Check that instret keeps counting while inaccessible: enable counters via T-SBI and read
    instret, disable so instret is inaccessible in run_mode, nop, re-enable, then SIGUPD the change."""
    coverpoint = "cp_mcounter_inc_inaccessible"
    description = (
        f"running in {run_mode} mode\n"
        "enable counters via T-SBI and read instret\n"
        f"disable counters via T-SBI so instret is inaccessible in {run_mode} mode\n"
        "nop\n"
        "re-enable counters via T-SBI\n"
        "read and sigupd change in instret"
    )

    old_reg, read_reg = test_data.int_regs.get_registers(2)

    lines = [
        comment_banner(coverpoint, description),
        "",
        test_data.add_testcase(run_mode, coverpoint, covergroup),
        f"# make counter accessible in {run_mode} mode",
        f"LI(x{read_reg}, -1)",
        *_set_counterens(f"x{read_reg}", run_mode),
        f"csrr x{old_reg}, instret",
        f"# make counter inaccessible in {run_mode} mode",
        *_set_counterens("zero", run_mode),
        "nop",
        f"# make counter accessible in {run_mode} mode",
        *_set_counterens(f"x{read_reg}", run_mode),
        f"csrr x{read_reg}, instret",
        f"sub x{read_reg}, x{read_reg}, x{old_reg}",
        "# SIGUPD the difference in instret",
        write_sigupd(read_reg, test_data),
    ]
    test_data.int_regs.return_registers([old_reg, read_reg])
    return lines
