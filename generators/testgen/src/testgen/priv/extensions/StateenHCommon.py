##################################
# priv/extensions/StateenHCommon.py
#
# Shared test generation for the H groups of Smstateen and Ssstateen.
# David_Harris@hmc.edu 29 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Helpers shared by the Smstateen and Ssstateen H groups.

Both groups boot to HS-mode.  They write hstateen0 directly and mstateen0 through T-SBI.  A stateen bit is named by
its (RV64 mask, RV32 high-half mask) pair of encoding.h constants.  Every bit these groups control is in the upper
word, so RV32 writes the high-half CSR.
"""

from testgen.asm.helpers import gated, write_sigupd
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData

HSTATEEN0_SE0 = ("HSTATEEN_SSTATEEN", "HSTATEENH_SSTATEEN")
HSTATEEN0_ENVCFG = ("HSTATEEN0_SENVCFG", "HSTATEEN0H_SENVCFG")
MSTATEEN0_SE0 = ("MSTATEEN_HSTATEEN", "MSTATEENH_HSTATEEN")
MSTATEEN0_ENVCFG = ("MSTATEEN0_HENVCFG", "MSTATEEN0H_HENVCFG")
MSTATEEN0_P1P13 = ("MSTATEEN0_PRIV113", "MSTATEEN0H_PRIV113")

# Bit 63 of mstateen1-3 controls sstateen1-3 and hstateen1-3; bit 63 of hstateen1-3 controls VS-mode access to
# sstateen1-3.  On RV32 they are bit 31 of the high-half CSRs.
STATEEN123_N = (1, 2, 3)

# The CSRs that bit 63 of mstateen1-3 controls, and bit 63 of hstateen1-3 in VS-mode
STATEEN123 = [
    "sstateen1",
    "sstateen2",
    "sstateen3",
    "hstateen1",
    "hstateen2",
    "hstateen3",
    "hstateen1h",
    "hstateen2h",
    "hstateen3h",
]

# Preprocessor conditions under which each gated CSR exists
CSR_GATES = {
    "hstateen0h": "__riscv_xlen == 32",
    "hstateen1h": "__riscv_xlen == 32",
    "hstateen2h": "__riscv_xlen == 32",
    "hstateen3h": "__riscv_xlen == 32",
    "henvcfgh": "__riscv_xlen == 32",
    "hedelegh": "__riscv_xlen == 32 && defined(SM1P13P0_OR_LATER_SUPPORTED)",
}

# CSR operands for names that LLVM does not know
CSR_OPERANDS = {"hedelegh": "CSR_HEDELEGH"}


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


def set_stateen_state(test_data: TestData) -> list[str]:
    """Enable only SE0, ENVCFG, JVT and FCSR (with Zfinx) in mstateen0 and hstateen0.

    Boot enables every standard mstateen0 bit and the matching hstateen0 bits.  The reference model lacks several of
    those features (indirect CSRs, AIA, IMSIC, CTR), so on a hart that has them the hstateen0 walks and reads would see
    writable bits that read as zero in the reference.  These groups therefore start from the state they control.
    Without Smstateen the mstateen CSRs do not exist and only hstateen0 is written.
    """
    tmp_reg = test_data.int_regs.get_register()
    lines = [
        "#ifdef SMSTATEEN_SUPPORTED",
        "#if __riscv_xlen == 64",
        "RVTEST_TSBI_CSR_WRITE(CSR_MSTATEEN0, MSTATEEN_HSTATEEN | MSTATEEN0_HENVCFG | MSTATEEN0_JVT)",
        "#else",
        "RVTEST_TSBI_CSR_WRITE(CSR_MSTATEEN0, MSTATEEN0_JVT)",
        "RVTEST_TSBI_CSR_WRITE(CSR_MSTATEEN0H, MSTATEENH_HSTATEEN | MSTATEEN0H_HENVCFG)",
        "#endif",
        "#ifdef ZFINX_SUPPORTED",
        "RVTEST_TSBI_CSR_SET(CSR_MSTATEEN0, MSTATEEN0_FCSR)",
        "#endif",
        "#endif",
        "#if __riscv_xlen == 64",
        f"LI(x{tmp_reg}, HSTATEEN_SSTATEEN | HSTATEEN0_SENVCFG | HSTATEEN0_JVT | HSTATEEN0_FCSR)",
        f"csrw hstateen0, x{tmp_reg}",
        "#else",
        f"LI(x{tmp_reg}, HSTATEEN0_JVT | HSTATEEN0_FCSR)",
        f"csrw hstateen0, x{tmp_reg}",
        f"LI(x{tmp_reg}, HSTATEENH_SSTATEEN | HSTATEEN0H_SENVCFG)",
        f"csrw hstateen0h, x{tmp_reg}",
        "#endif",
    ]
    test_data.int_regs.return_register(tmp_reg)
    return lines


def read_csrs(
    test_data: TestData,
    csrs: list[str],
    suffix: str,
    coverpoint: str,
    covergroup: str,
) -> list[str]:
    """Read each CSR and record the value, or 42 and the trap when the read traps."""
    rd = test_data.int_regs.get_register()
    lines = []
    for csr in csrs:
        lines.extend(
            gated(
                [
                    f"LI(x{rd}, 42)",
                    test_data.add_testcase(f"{csr}_{suffix}", coverpoint, covergroup),
                    f"csrr x{rd}, {CSR_OPERANDS.get(csr, csr)}",
                    write_sigupd(rd, test_data),
                ],
                CSR_GATES.get(csr),
            )
        )
    test_data.int_regs.return_register(rd)
    return lines


def read_in_mode(
    test_data: TestData,
    mode: str,
    csrs: list[str],
    suffix: str,
    coverpoint: str,
    covergroup: str,
) -> list[str]:
    """Read each CSR in mode (hs, vs or vu), entered from and returning to HS-mode."""
    if mode == "hs":
        return read_csrs(test_data, csrs, suffix, coverpoint, covergroup)
    return [
        f"RVTEST_TSBI_GOTO_{mode.upper()}MODE",
        *read_csrs(test_data, csrs, suffix, coverpoint, covergroup),
        "RVTEST_TSBI_GOTO_SMODE",
    ]


def mstateen123_bit63(test_data: TestData, value: int) -> list[str]:
    """Set (value 1) or clear (value 0) bit 63 of mstateen1-3 through T-SBI, where Smstateen is implemented."""
    reg = test_data.int_regs.get_register()
    op = "csrs" if value else "csrc"
    lines = [
        "#ifdef SMSTATEEN_SUPPORTED",
        "#if __riscv_xlen == 64",
        f"LI(x{reg}, MSTATEEN_HSTATEEN)",
        *[tsbi_call(f"{op} mstateen{n}, x{reg}") for n in STATEEN123_N],
        "#else",
        f"LI(x{reg}, MSTATEENH_HSTATEEN)",
        *[tsbi_call(f"{op} mstateen{n}h, x{reg}") for n in STATEEN123_N],
        "#endif",
        "#endif",
    ]
    test_data.int_regs.return_register(reg)
    return lines


def hstateen123_bit63(test_data: TestData, value: int) -> list[str]:
    """Set (value 1) or clear (value 0) bit 63 of hstateen1-3 from HS-mode, with bit 63 of mstateen1-3 set."""
    reg = test_data.int_regs.get_register()
    op = "csrs" if value else "csrc"
    lines = [
        "#if __riscv_xlen == 64",
        f"LI(x{reg}, HSTATEEN_SSTATEEN)",
        *[f"{op} hstateen{n}, x{reg}" for n in STATEEN123_N],
        "#else",
        f"LI(x{reg}, HSTATEENH_SSTATEEN)",
        *[f"{op} hstateen{n}h, x{reg}" for n in STATEEN123_N],
        "#endif",
    ]
    test_data.int_regs.return_register(reg)
    return lines


def access_csrs(test_data: TestData, csrs: list[str], suffix: str, coverpoint: str, covergroup: str) -> list[str]:
    """Read each CSR, then write, clear and set all 1s, reading it back after each.

    A read that traps records 42 and the trap; a write that traps records the trap.
    """
    rd, rs = test_data.int_regs.get_registers(2)
    lines = [f"LI(x{rs}, -1)"]
    for csr in csrs:
        body = [
            f"LI(x{rd}, 42)",
            test_data.add_testcase(f"{csr}_csrr_{suffix}", coverpoint, covergroup),
            f"csrr x{rd}, {csr}",
            write_sigupd(rd, test_data),
        ]
        for op in ("csrw", "csrc", "csrs"):
            body.extend(
                [
                    test_data.add_testcase(f"{csr}_{op}_{suffix}", coverpoint, covergroup),
                    f"{op} {csr}, x{rs}",
                    f"LI(x{rd}, 42)",
                    f"csrr x{rd}, {csr}",
                    write_sigupd(rd, test_data),
                ]
            )
        lines.extend(gated(body, CSR_GATES.get(csr)))
    test_data.int_regs.return_registers([rd, rs])
    return lines
