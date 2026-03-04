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
        testsuite: Name of the testsuite (e.g., "I", "M", "ZcbM", "MisalignD", "ExceptionsSm")
        E_ext: Whether to use RV32E/RV64E (16 registers instead of 32)
        config_dependent: Whether this test is config dependent
        required_extensions: List of RISC-V extensions required for the test.
                             Used for generating the march string and header defines.
                             If None, extensions are parsed from testsuite name.
        march_extensions: Optional list of extensions to use for building the march string.
                          If None, march is built from required_extensions.
    """

    xlen: int
    flen: int
    testsuite: str
    E_ext: bool = False
    config_dependent: bool = False
    required_extensions: list[str] | None = None
    march_extensions: list[str] | None = None

    @property
    def xlen_format_str(self) -> str:
        """Get format string for hexadecimal representation of xlen-width values."""
        return f"0x{{:0{self.xlen // 4}x}}"

    @property
    def flen_format_str(self) -> str:
        """Get format string for hexadecimal representation of flen-width values."""
        return f"0x{{:0{self.flen // 4}x}}"
