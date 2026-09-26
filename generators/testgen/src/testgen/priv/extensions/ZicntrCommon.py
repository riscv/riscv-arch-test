##################################
# priv/extensions/ZicntrCommon.py
#
# Shared Zicntr test generation for the counter-enable suites.
# David_Harris@hmc.edu 30 August 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Functions for generating Zicntr counter-enable tests in all priv modes"""

from typing import Literal

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData
from testgen.priv.extensions.PrivCommon import HTIMEDELTAS, read_time, write64

Mode = Literal["M", "S", "U", "VS", "VU"]
Counteren = Literal["ones", "zeros"]

_COUNTERS = ["cycle", "time", "instret"]

# Counter-enable CSRs that each mode writes directly.  scounteren has no VS replica, so VS-mode
# writes the real register.
_DIRECT_WRITES = {
    "M": ("mcounteren", "hcounteren", "scounteren"),
    "S": ("hcounteren", "scounteren"),
    "VS": ("scounteren",),
}


def _access_counter(
    test_data: TestData, covergroup: str, coverpoint: str, bin_prefix: str, read_reg: int, i: int
) -> list[str]:
    """Read counter i and attempt to write it, low half and high half on RV32.

    The read traps or not according to the counter-enable registers; the write always raises an illegal
    instruction, because the unprivileged counters are read-only CSRs.
    """

    def access(name: str, suffix: str) -> list[str]:
        return [
            test_data.add_testcase(f"{bin_prefix}_read{suffix}", coverpoint, covergroup),
            f"csrr x{read_reg}, {name}",
            test_data.add_testcase(f"{bin_prefix}_write{suffix}", coverpoint, covergroup),
            f"csrw {name}, zero  # read-only CSR: illegal instruction whatever the counterens hold",
        ]

    if i < 3:
        name = _COUNTERS[i]
        return [
            *access(name, ""),
            "#if __riscv_xlen == 32",
            *access(f"{name}h", "h"),
            "#endif",
        ]
    return [
        "#ifdef ZIHPM_SUPPORTED",
        *access(f"hpmcounter{i}", ""),
        "#if __riscv_xlen == 32",
        *access(f"hpmcounter{i}h", "h"),
        "#endif",
        "#endif",
    ]


def _write_counteren(csr: str, operand: str, mode: Mode, comment: str = "") -> str:
    """Write csr directly when mode can, otherwise through T-SBI."""
    instr = f"csrw {csr}, {operand}"
    if comment:
        instr += f"  # {comment}"
    if csr in _DIRECT_WRITES.get(mode, ()):
        return instr
    return tsbi_call(instr)


def _preset_counteren(csr: str, setting: Counteren, mode: Mode, reg: int) -> list[str]:
    """Write all ones or all zeros to csr."""
    if setting == "zeros":
        return [_write_counteren(csr, "zero", mode, "disable all counters")]
    return [f"LI(x{reg}, -1)", _write_counteren(csr, f"x{reg}", mode, "enable all counters")]


def counteren_walk_tests(
    test_data: TestData,
    covergroup: str,
    coverpoint: str,
    description: str,
    *,
    csrs: list[str],
    mode: Mode,
    mcounteren: Counteren | None = None,
    hcounteren: Counteren | None = None,
    scounteren: Counteren | None = None,
    tag: str = "",
) -> list[str]:
    """
    Walk a 1 and then a 0 through every bit of each CSR in csrs (the same value in each), reading
    every counter after each write. Everything runs in mode; writes that mode cannot make directly
    go through T-SBI. mcounteren, hcounteren and scounteren optionally preset those registers to all
    ones or all zeros first; scounteren only when S-mode exists.
    tag prefixes the testcase names so a coverpoint tested with several mcounteren settings stays unique.
    """
    read_reg, ones_reg, walk_reg, inv_reg = test_data.int_regs.get_registers(4)
    lines = [comment_banner(coverpoint, description), ""]
    if scounteren is not None:
        lines += [
            "#ifdef S_SUPPORTED",
            *_preset_counteren("scounteren", scounteren, mode, ones_reg),
            "#endif // S_SUPPORTED",
        ]
    presets: tuple[tuple[str, Counteren | None], ...] = (("mcounteren", mcounteren), ("hcounteren", hcounteren))
    for csr, setting in presets:
        if setting is not None:
            lines += _preset_counteren(csr, setting, mode, ones_reg)

    lines.append(f"LI(x{walk_reg}, 1)")
    for i in range(32):
        lines += [
            *(_write_counteren(csr, f"x{walk_reg}", mode, "set only the current bit") for csr in csrs),
            *_access_counter(test_data, covergroup, coverpoint, f"{tag}walking_1_{i}", read_reg, i),
            f"slli x{walk_reg}, x{walk_reg}, 1",
        ]

    lines.append(f"LI(x{walk_reg}, 1)")
    for i in range(32):
        lines += [
            f"not x{inv_reg}, x{walk_reg}  # all bits but the current one",
            *(_write_counteren(csr, f"x{inv_reg}", mode, "clear only the current bit") for csr in csrs),
            *_access_counter(test_data, covergroup, coverpoint, f"{tag}walking_0_{i}", read_reg, i),
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


def htimedelta_tests(test_data: TestData, covergroup: str, mode: Mode) -> list[str]:
    """Read time in mode for each htimedelta.

    VS and VU read time + htimedelta; M, HS and U read time; each read must be within 2^30 of a baseline read.
    """
    coverpoint = f"cp_delta_{'hs' if mode == 'S' else mode.lower()}"
    virtual = mode in ("VS", "VU")
    lower = mode in ("U", "VS", "VU")
    base_lo, base_hi, val_lo, val_hi, tmp = test_data.int_regs.get_registers(5)
    lines = [
        comment_banner(
            coverpoint,
            "With htimedelta = {0, 2^30, 2^60, -2^30, -2^60}, read time (and timeh on RV32) in "
            f"{'HS' if mode == 'S' else mode}-mode.\n"
            + ("It reads time + htimedelta." if virtual else "It reads time, unaffected by htimedelta."),
        ),
    ]
    for name, delta in HTIMEDELTAS.items():
        expected = delta & ((1 << 64) - 1) if virtual else 0
        lines.extend(
            [
                *write64("htimedelta", 0, tmp),
                *read_time(base_lo, base_hi, tmp),
                *write64("htimedelta", delta, tmp),
                *([f"RVTEST_TSBI_GOTO_{mode}MODE"] if lower else []),
                f"LI(x{val_lo}, 0)",
                f"LI(x{val_hi}, 0)",
                test_data.add_testcase(name, coverpoint, covergroup),
                *read_time(val_lo, val_hi, tmp),
                *(["RVTEST_TSBI_GOTO_SMODE"] if lower else []),
                "#if __riscv_xlen == 32",
                f"sltu x{tmp}, x{val_lo}, x{base_lo}",
                f"sub x{val_hi}, x{val_hi}, x{base_hi}",
                f"sub x{val_hi}, x{val_hi}, x{tmp}",
                "#endif",
                f"sub x{val_lo}, x{val_lo}, x{base_lo}    # read - baseline",
            ]
        )
        if expected:
            lines.extend(
                [
                    "#if __riscv_xlen == 64",
                    f"LI(x{tmp}, {expected:#x})",
                    "#else",
                    f"LI(x{tmp}, {expected >> 32:#x})",
                    f"sub x{val_hi}, x{val_hi}, x{tmp}",
                    f"LI(x{tmp}, {expected & 0xFFFFFFFF:#x})",
                    f"sltu x{base_lo}, x{val_lo}, x{tmp}",
                    f"sub x{val_hi}, x{val_hi}, x{base_lo}",
                    "#endif",
                    f"sub x{val_lo}, x{val_lo}, x{tmp}    # - htimedelta",
                ]
            )
        lines.extend(
            [
                f"srli x{val_lo}, x{val_lo}, 30",
                "#if __riscv_xlen == 32",
                f"or x{val_lo}, x{val_lo}, x{val_hi}",
                "#endif",
                f"seqz x{val_lo}, x{val_lo}    # 1 if the difference is below 2^30",
                write_sigupd(val_lo, test_data),
            ]
        )
    lines.extend(write64("htimedelta", 0, tmp))
    test_data.int_regs.return_registers([base_lo, base_hi, val_lo, val_hi, tmp])
    return lines
