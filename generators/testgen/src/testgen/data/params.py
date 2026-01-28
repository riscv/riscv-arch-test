##################################
# params.py
#
# jcarlin@hmc.edu 11 October 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""
Instruction parameter dataclass.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class InstructionParams:
    """
    Parameters for generating a single instruction test case.

    This dataclass holds all the information needed to generate a single
    instruction test, including register numbers, values, and flags.
    """

    # Integer registers
    rs1: int | None = None
    rs2: int | None = None
    rs3: int | None = None
    rd: int | None = None
    temp_reg: int | None = None  # Temporary register for use in test setup/teardown

    # Integer register values
    rs1val: int | None = None
    rs2val: int | None = None
    rs3val: int | None = None
    rdval: int | None = None
    temp_val: int | None = None

    # Float registers
    fs1: int | None = None
    fs2: int | None = None
    fs3: int | None = None
    fd: int | None = None
    temp_freg: int | None = None  # Temporary float register for use in test setup/teardown

    # Float register values
    fs1val: int | None = None
    fs2val: int | None = None
    fs3val: int | None = None
    fdval: int | None = None
    temp_fval: int | None = None

    # Immediate value
    immval: int | None = None

    # Flags
    frm: str | None = None  # Floating-point rounding mode tests
    aqrl: str | None = None  # Acquire/Release for atomic operations

    # Internal params to pass to formatters
    fp_load_type: Literal["single", "double", "half", "quad"] | None = None  # Type for FP loads/stores

    @property
    def used_int_regs(self) -> list[int]:
        """Return list of all integer registers used in this test."""
        regs: list[int] = []
        for reg in [self.rs1, self.rs2, self.rs3, self.rd, self.temp_reg]:
            if reg is not None:
                regs.append(reg)
        return regs

    @property
    def used_float_regs(self) -> list[int]:
        """Return list of all float registers used in this test."""
        regs: list[int] = []
        for reg in [self.fs1, self.fs2, self.fs3, self.fd, self.temp_freg]:
            if reg is not None:
                regs.append(reg)
        return regs
