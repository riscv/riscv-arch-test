##################################
# test_data.py
#
# jcarlin@hmc.edu 5 Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from __future__ import annotations

import re
from typing import Literal

from testgen.data.config import TestConfig
from testgen.data.registers import FloatRegisterFile, IntegerRegisterFile
from testgen.data.testcase import TestCase

# Pre-compiled regex patterns for label normalization in add_testcase()
_LABEL_INVALID_CHARS = re.compile(r"[^a-zA-Z0-9_]")
_LABEL_MULTI_UNDERSCORE = re.compile(r"_+")


class TestData:
    """
    Context and state for test generation. Created per test file (instruction for unpriv, feature for priv).

    This class manages mutable state during test generation, including register
    file allocation and the active TestCase. The immutable configuration
    (xlen, flen, etc.) is stored in a TestConfig object.

    Attributes:
        config: Immutable test configuration (xlen, flen, register file type)
        instr_name: Instruction this test is exercising
        int_regs: Integer register file for allocation
        float_regs: Floating-point register file for allocation
        test_count: Running count of testcases generated
        testcase: Active TestCase for generated code/sigupds/etc.
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
        self._test_count = 0
        self._current_testcase_label = ""
        self._fp_load_size: Literal["single", "double", "half", "quad"] | None = None
        self.testcase: TestCase | None = None

    def __repr__(self) -> str:
        return f"TestData(config={self._config}, int_regs={self._int_regs}, float_regs={self._float_regs}, test_count={self._test_count})"

    # Configuration accessor
    @property
    def config(self) -> TestConfig:
        """Get the immutable test configuration."""
        return self._config

    # Testsuite and instruction name accessors
    @property
    def instr_name(self) -> str:
        """Get the instruction name this test is exercising."""
        if self._instr_name is None:
            raise ValueError("Instruction name is not set in TestData.")
        return self._instr_name

    @property
    def fp_load_size(self) -> Literal["single", "double", "half", "quad"]:
        """Get the floating point load size based on the instruction."""
        if self._fp_load_size is not None:
            return self._fp_load_size
        if self.instr_name.endswith("q"):
            result = "quad"
        elif self.instr_name.endswith("d") or self.instr_name in ("c.fsdsp", "c.fldsp"):
            result = "double"
        elif self.instr_name.endswith(("s", "w")) or self.instr_name in ("c.fswsp", "c.flwsp"):
            result = "single"
        elif self.instr_name.endswith(("h", "bf16")):
            result = "half"
        else:
            raise ValueError(
                f"Unknown floating point load size for instruction {self.instr_name}. Modify {__file__} as needed."
            )
        self._fp_load_size = result
        return result

    # Register file accessors
    @property
    def int_regs(self) -> IntegerRegisterFile:
        return self._int_regs

    @property
    def float_regs(self) -> FloatRegisterFile:
        return self._float_regs

    @property
    def current_testcase_label(self) -> str:
        """Get the current testcase label."""
        return self._current_testcase_label

    # Read-only properties delegated to config
    @property
    def testsuite(self) -> str:
        """Get the testsuite name."""
        return self._config.testsuite

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

    def begin_testcase(self) -> TestCase:
        """Create and set a new active TestCase."""
        self.testcase = TestCase()
        return self.testcase

    def end_testcase(self) -> TestCase:
        """Return the completed TestCase and clear the active one."""
        assert self.testcase is not None, "No active testcase to end"
        tc = self.testcase
        self.testcase = None
        return tc

    def add_testcase(self, bin_name: str, coverpoint: str, covergroup: str | None = None) -> str:
        """
        Add a test data string and return the testcase label line. Also increments test count.

        Args:
            bin_name: Bin name to append to the coverpoint name.
            coverpoint: The coverpoint name
            covergroup: Optional covergroup name. Defaults to '{extension}_{instr_name}_cg'.

        Returns:
            Label line string in format '{covergroup}_{coverpoint}_{bin_name}:'
        """
        self.increment_test_count()

        if covergroup is None:
            covergroup = f"{self.testsuite}_{self.instr_name}_cg"

        # Construct full coverpoint name
        full_name = f"{covergroup}_{coverpoint}_{bin_name}"

        # Normalize full_name to a valid assembly label
        label = full_name.replace("-", "m")
        label = _LABEL_INVALID_CHARS.sub("_", label)
        label = _LABEL_MULTI_UNDERSCORE.sub("_", label)  # Collapse consecutive underscores
        label = label.strip("_")

        # Add testcase string to the active TestCase
        assert self.testcase is not None, "No active testcase — call begin_testcase() first"
        self.testcase.data_strings.append(
            f'{label}_str: .string "\\"test: {self.test_count}; cg: {covergroup}; cp: {coverpoint}; bin: {bin_name}\\""'
        )
        self.testcase.num_tests += 1

        # Return label
        self._current_testcase_label = label
        return f"{label}:"

    def destroy(self) -> None:
        """Clean up resources used by TestData."""
        self._int_regs.destroy()
        self._float_regs.destroy()
