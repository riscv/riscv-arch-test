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

    # Integer register values
    rs1val: int | None = None
    rs2val: int | None = None
    rs3val: int | None = None
    rdval: int | None = None

    # Float registers
    fs1: int | None = None
    fs2: int | None = None
    fs3: int | None = None
    fd: int | None = None

    # Float register values
    fs1val: int | None = None
    fs2val: int | None = None
    fs3val: int | None = None
    fdval: int | None = None

    # Immediate value
    immval: int | None = None

    # Flags
    frm: bool = False  # Floating-point rounding mode tests
    aqrl: str = ""  # Acquire/Release for atomic operations

    @property
    def used_int_regs(self) -> list[int]:
        """Return list of all integer registers used in this test."""
        regs: list[int] = []
        for reg in [self.rs1, self.rs2, self.rs3, self.rd]:
            if reg is not None:
                regs.append(reg)
        return regs

    @property
    def used_float_regs(self) -> list[int]:
        """Return list of all float registers used in this test."""
        regs: list[int] = []
        for reg in [self.fs1, self.fs2, self.fs3, self.fd]:
            if reg is not None:
                regs.append(reg)
        return regs
