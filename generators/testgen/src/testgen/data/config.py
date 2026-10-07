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
        sew: Selected Element Width that the test will run at (8, 16, 32, or 64 bits)
        required_extensions: List of RISC-V extensions required for the test.
                             Used for generating the march string and header defines.
                             If None, extensions are parsed from testsuite name.
        forbidden_extensions: Optional list of RISC-V extensions that must not be implemented for the test.
        march_extensions: Optional list of extensions to use for building the march string.
                          If None, march is built from required_extensions.
        extra_params: Optional list of extra parameter requirements for the test.
        extra_extension: Extensions required in addition to the testsuite's own, from a testplan row's
                         ExtraExtension column. It is appended to the file and covergroup name prefix.
    """

    xlen: int
    flen: int
    testsuite: str
    E_ext: bool = False
    sew: int | None = None
    required_extensions: list[str | list[str]] | None = None
    forbidden_extensions: list[str] | None = None
    march_extensions: list[str] | None = None
    extra_params: list[str] | None = None
    extra_extension: str = ""

    @property
    def name_prefix(self) -> str:
        """Prefix for test file and covergroup names, e.g. "Zfhmin" or "ZfhminD" for a row that also needs D."""
        return f"{self.testsuite}{self.extra_extension}"

    @property
    def xlen_format_str(self) -> str:
        """Get format string for hexadecimal representation of xlen-width values."""
        return f"0x{{:0{self.xlen // 4}x}}"

    @property
    def flen_format_str(self) -> str:
        """Get format string for hexadecimal representation of flen-width values."""
        return f"0x{{:0{self.flen // 4}x}}"
