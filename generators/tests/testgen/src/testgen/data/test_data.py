##################################
# test_data.py
#
# jcarlin@hmc.edu 5 Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.registers import FloatRegisterFile, IntegerRegisterFile
from testgen.data.test_config import TestConfig


class TestData:
    """
    Context and state for test generation. Created per instruction (test file).

    This class manages mutable state during test generation, including register
    file allocation and signature space tracking. The immutable configuration
    (xlen, flen, etc.) is stored in a TestConfig object.

    Attributes:
        config: Immutable test configuration (xlen, flen, register file type)
        int_regs: Integer register file for allocation
        float_regs: Floating-point register file for allocation
        sigupd_count: Running count of integer signature updates
        sigupd_count_float: Running count of floating-point signature updates
    """

    def __init__(self, test_config: TestConfig) -> None:
        """
        Initialize test data with configuration and empty state.

        Args:
            test_config: Immutable test configuration
        """
        self._config = test_config
        self._int_regs = IntegerRegisterFile(test_config.e_register_file)
        self._float_regs = FloatRegisterFile()
        self._sigupd_count = 10  # Start with a margin of 10 spaces in signature
        self._sigupd_count_float = 0

    def __repr__(self) -> str:
        return f"TestData(config={self._config}, int_regs={self._int_regs}, float_regs={self._float_regs}, sigupd_count={self._sigupd_count}, sigupd_count_float={self._sigupd_count_float})"

    # Configuration accessor
    @property
    def config(self) -> TestConfig:
        """Get the immutable test configuration."""
        return self._config

    # Register file accessors
    @property
    def int_regs(self) -> IntegerRegisterFile:
        return self._int_regs

    @property
    def float_regs(self) -> FloatRegisterFile:
        return self._float_regs

    # Make sigupd_count variables available as properties so they can be accessed and modified directly
    @property
    def sigupd_count(self) -> int:
        return self._sigupd_count

    @sigupd_count.setter
    def sigupd_count(self, value: int) -> None:
        self._sigupd_count = value

    @property
    def sigupd_count_float(self) -> int:
        return self._sigupd_count_float

    @sigupd_count_float.setter
    def sigupd_count_float(self, value: int) -> None:
        self._sigupd_count_float = value

    # Read-only properties delegated to config
    @property
    def xlen(self) -> int:
        return self._config.xlen

    @property
    def flen(self) -> int:
        return self._config.flen

    @property
    def xlen_format_str(self) -> str:
        return self._config.xlen_format_str

    @property
    def flen_format_str(self) -> str:
        return self._config.flen_format_str

    def destroy(self) -> None:
        """Clean up resources used by TestData."""
        self._int_regs.destroy()
        self._float_regs.destroy()
