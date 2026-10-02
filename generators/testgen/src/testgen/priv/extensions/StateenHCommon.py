##################################
# priv/extensions/StateenHCommon.py
#
# Shared test generation for SsstateenH and SmstateenH.
# David_Harris@hmc.edu 29 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Helpers shared by SsstateenH and SmstateenH.

Both suites boot to HS-mode.  They write hstateen0 directly and mstateen0 through T-SBI.  A stateen bit is named by
its (RV64 mask, RV32 high-half mask) pair of encoding.h constants.  Every bit these suites control is in the upper
word, so RV32 writes the high-half CSR.
"""

from testgen.asm.helpers import write_sigupd
from testgen.data.state import TestData
from testgen.priv.extensions.HCommon import gated

HSTATEEN0_SE0 = ("HSTATEEN_SSTATEEN", "HSTATEENH_SSTATEEN")
HSTATEEN0_ENVCFG = ("HSTATEEN0_SENVCFG", "HSTATEEN0H_SENVCFG")
MSTATEEN0_SE0 = ("MSTATEEN_HSTATEEN", "MSTATEENH_HSTATEEN")
MSTATEEN0_ENVCFG = ("MSTATEEN0_HENVCFG", "MSTATEEN0H_HENVCFG")
MSTATEEN0_P1P13 = ("MSTATEEN0_PRIV113", "MSTATEEN0H_PRIV113")

# Preprocessor conditions under which each gated CSR exists
CSR_GATES = {
    "hstateen0h": "__riscv_xlen == 32",
    "hstateen1h": "__riscv_xlen == 32",
    "hstateen2h": "__riscv_xlen == 32",
    "hstateen3h": "__riscv_xlen == 32",
    "henvcfgh": "__riscv_xlen == 32",
    "hedelegh": "__riscv_xlen == 32 && defined(SM1P13P0_OR_LATER_SUPPORTED)",
}


def hstateen0_bit(test_data: TestData, bit: tuple[str, str], value: int) -> list[str]:
    """Set (value 1) or clear (value 0) a bit of hstateen0 from HS-mode."""
    reg = test_data.int_regs.get_register()
    op = "csrs" if value else "csrc"
    lines = [
        "#if __riscv_xlen == 64",
        f"LI(x{reg}, {bit[0]})",
        f"{op} hstateen0, x{reg}",
        "#else",
        f"LI(x{reg}, {bit[1]})",
        f"{op} hstateen0h, x{reg}",
        "#endif",
    ]
    test_data.int_regs.return_register(reg)
    return lines


def mstateen0_bit(bit: tuple[str, str], value: int) -> list[str]:
    """Set (value 1) or clear (value 0) a bit of mstateen0 through T-SBI."""
    op = "SET" if value else "CLEAR"
    return [
        "#if __riscv_xlen == 64",
        f"RVTEST_TSBI_CSR_{op}(CSR_MSTATEEN0, {bit[0]})",
        "#else",
        f"RVTEST_TSBI_CSR_{op}(CSR_MSTATEEN0H, {bit[1]})",
        "#endif",
    ]


def read_csrs(
    test_data: TestData,
    csrs: list[str],
    suffix: str,
    coverpoint: str,
    covergroup: str,
    either_causes: tuple[str, str] | None = None,
) -> list[str]:
    """Read each CSR and record the value, or 42 and the trap when the read traps.

    With either_causes, each read must raise one of the two exceptions.  RVTEST_OPTIONAL_TRAP2 skips either without
    recording it, so both give the same signature; a read that completes records the CSR value instead of 42, and
    any other exception is recorded, so both fail.
    """
    rd = test_data.int_regs.get_register()
    tmp_reg = test_data.int_regs.get_register() if either_causes else None
    lines = []
    for csr in csrs:
        label = test_data.add_testcase(f"{csr}_{suffix}", coverpoint, covergroup)
        arm = (
            [f"RVTEST_OPTIONAL_TRAP2(x{tmp_reg}, x{rd}, {label[:-1]}, {either_causes[0]}, {either_causes[1]})"]
            if either_causes
            else []
        )
        lines.extend(
            gated(
                [
                    *arm,
                    f"LI(x{rd}, 42)",
                    label,
                    f"csrr x{rd}, {csr}",
                    *([f"RVTEST_OPTIONAL_TRAP_END(x{tmp_reg})"] if either_causes else []),
                    write_sigupd(rd, test_data),
                ],
                CSR_GATES.get(csr),
            )
        )
    test_data.int_regs.return_register(rd)
    if tmp_reg is not None:
        test_data.int_regs.return_register(tmp_reg)
    return lines


def read_in_mode(
    test_data: TestData,
    mode: str,
    csrs: list[str],
    suffix: str,
    coverpoint: str,
    covergroup: str,
    either_causes: tuple[str, str] | None = None,
) -> list[str]:
    """Read each CSR in mode (hs, vs or vu), entered from and returning to HS-mode."""
    if mode == "hs":
        return read_csrs(test_data, csrs, suffix, coverpoint, covergroup, either_causes)
    return [
        f"RVTEST_TSBI_GOTO_{mode.upper()}MODE",
        *read_csrs(test_data, csrs, suffix, coverpoint, covergroup, either_causes),
        "RVTEST_TSBI_GOTO_SMODE",
    ]
