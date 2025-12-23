##################################
# config.py
#
# jcarlin@hmc.edu November 5, 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Test configuration for RISC-V test generation."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TestConfig:
    """
    Immutable configuration for test generation.

    This class holds configuration parameters that remain constant throughout
    test generation for a given set of tests. These values are read-only and
    cannot be modified after the TestConfig is created.

    Attributes:
        xlen: Register width (32 or 64 bits)
        flen: Floating-point register width (32, 64, or 128 bits)
        extension: RISC-V extension being tested
        e_register_file: Whether to use RV32E/RV64E (16 registers instead of 32)
    """

    xlen: int
    flen: int
    extension: str
    e_register_file: bool = False

    @property
    def xlen_format_str(self) -> str:
        """Get format string for hexadecimal representation of xlen-width values."""
        return f"0x{{:0{self.xlen // 4}x}}"

    @property
    def flen_format_str(self) -> str:
        """Get format string for hexadecimal representation of flen-width values."""
        return f"0x{{:0{self.flen // 4}x}}"
