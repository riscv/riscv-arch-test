##################################
# test_data.py
#
# jcarlin@hmc.edu 5 Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from __future__ import annotations

from typing import Literal

from testgen.data.config import TestConfig
from testgen.data.registers import FloatRegisterFile, IntegerRegisterFile


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
        test_data_values: List of values to be stored in test_data section
    """

    def __init__(self, test_config: TestConfig, instr_name: str | None = None) -> None:
        """
        Initialize test data with configuration and empty state.

        Args:
            test_config: Immutable test configuration
            instr_name: Instruction name this test is exercising. Optional for priv/extension-level tests.
        """
        self._config = test_config
        self._instr_name = instr_name
        self._int_regs = IntegerRegisterFile(test_config.E_ext)
        self._float_regs = FloatRegisterFile()
        self._sigupd_count = 10  # Start with a margin of 10 spaces in signature
        self._test_count = 0
        self._test_data_values: list[int] = []  # List of integer values
        self._test_data_strings: list[str] = []  # List of string values

    def __repr__(self) -> str:
        return f"TestData(config={self._config}, int_regs={self._int_regs}, float_regs={self._float_regs}, sigupd_count={self._sigupd_count}, test_count={self._test_count})"

    # Configuration accessor
    @property
    def config(self) -> TestConfig:
        """Get the immutable test configuration."""
        return self._config

    # Extension and instruction name accessors
    @property
    def instr_name(self) -> str:
        """Get the instruction name this test is exercising."""
        if self._instr_name is None:
            raise ValueError("Instruction name is not set in TestData.")
        return self._instr_name

    @property
    def fp_load_size(self) -> Literal["single", "double", "half", "quad"]:
        """Get the floating point load size based on the instruction."""
        if self.instr_name.endswith("q"):
            return "quad"
        elif self.instr_name.endswith("d") or self.instr_name in ("c.fsdsp", "c.fldsp"):
            return "double"
        elif self.instr_name.endswith(("s", "w")) or self.instr_name in ("c.fswsp", "c.flwsp"):
            return "single"
        elif self.instr_name.endswith("h"):
            return "half"
        else:
            raise ValueError(
                f"Unknown floating point load size for instruction {self.instr_name}. Modify {__file__} as needed."
            )

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

    # Read-only properties delegated to config
    @property
    def extension(self) -> str:
        """Get the RISC-V extension this test is exercising."""
        return self._config.extension

    @property
    def xlen(self) -> int:
        return self._config.xlen

    @property
    def xlen_log2(self) -> int:
        return self._config.xlen.bit_length() - 1

    @property
    def flen(self) -> int:
        return self._config.flen

    @property
    def flen_log2(self) -> int:
        return self._config.flen.bit_length() - 1

    @property
    def xlen_format_str(self) -> str:
        return self._config.xlen_format_str

    @property
    def flen_format_str(self) -> str:
        return self._config.flen_format_str

    # Test count management
    @property
    def test_count(self) -> int:
        """Get the current test count."""
        return self._test_count

    def increment_test_count(self) -> None:
        """Increment the test count by 1."""
        self._test_count += 1

    @property
    def test_data_values(self) -> list[int]:
        """Get the list of test data values to be stored in .data section."""
        return self._test_data_values

    def add_test_data_value(self, value: int) -> None:
        """
        Add a test data value to be stored in .data section.

        Args:
            value: The integer value to store
        """
        self._test_data_values.append(value)

    @property
    def test_data_strings(self) -> list[str]:
        """Get the list of test data strings to be stored in .data section."""
        return self._test_data_strings

    def add_testcase(self, coverpoint: str, bin_name: str | None = None, covergroup: str | None = None) -> str:
        """
        Add a test data string and return the testcase label line. Also increments test count.

        Args:
            cp: The coverpoint name
            covergroup: Optional covergroup name. Defaults to '{extension}_{instr_name}_cg'.
            bin_name: Optional bin name to append to the coverpoint name.

        Returns:
            Label line string in format '{covergroup}_{coverpoint}_{bin_name}}:'
        """
        self.increment_test_count()

        if covergroup is None:
            covergroup = f"{self.extension}_{self.instr_name}_cg"

        if bin_name is None:
            bin_name = f"test_{self.test_count}"

        # Construct full coverpoint name
        full_name = f"{covergroup}_{coverpoint}_{bin_name}"

        # Add testcase string to test data strings
        self._test_data_strings.append(
            f'test_{self.test_count}: .string "\\"test: {self.test_count}; cp: {full_name}\\""'
        )

        # Return label
        return f"\n{full_name}:"

    def copy(self) -> TestData:
        """Create a deep copy of the TestData object."""
        new_data = TestData(self.config, self.instr_name)

        # Copy register state
        new_data._int_regs = self._int_regs.copy()
        new_data._float_regs = self._float_regs.copy()

        # Copy signature counts
        new_data._sigupd_count = self._sigupd_count
        new_data._test_count = self._test_count

        # Copy data values
        new_data._test_data_values = self._test_data_values.copy()
        new_data._test_data_strings = self._test_data_strings.copy()

        return new_data

    def destroy(self) -> None:
        """Clean up resources used by TestData."""
        self._int_regs.destroy()
        self._float_regs.destroy()
