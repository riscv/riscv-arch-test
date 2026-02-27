##################################
# generate/priv.py
#
# Privileged test generation orchestration.
# jcarlin@hmc.edu Jan 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Privileged test generation orchestration."""

from pathlib import Path

from testgen.data.config import TestConfig
from testgen.data.state import TestData
from testgen.io.writer import write_test_file
from testgen.priv.registry import (
    get_priv_test_defines,
    get_priv_test_generator,
    get_priv_test_march_extensions,
    get_priv_test_required_extensions,
)


def generate_priv_test(testsuite: str, output_test_dir: Path) -> None:
    """
    Generate tests for a privileged testsuite.

    Args:
        testsuite: Testsuite name (e.g., "ExceptionsSm")
        output_test_dir: Base directory to output generated tests
    """
    # Output always goes to priv/<testsuite>
    output_path = output_test_dir / "priv" / testsuite
    output_path.mkdir(parents=True, exist_ok=True)

    # Create test configuration - privileged tests are config_dependent and don't have a fixed xlen
    # The xlen=0 indicates this is a multi-xlen test that uses preprocessor conditionals
    test_config = TestConfig(
        xlen=0,  # One test for all XLENs
        flen=0,
        testsuite=testsuite,
        E_ext=False,
        config_dependent=True,
        required_extensions=get_priv_test_required_extensions(testsuite),
        march_extensions=get_priv_test_march_extensions(testsuite),
    )

    # Create test data
    test_data = TestData(test_config)

    # Priv tests use x1/ra as the return address for function calls, so reserve it before generating the test
    test_data.int_regs.consume_registers([1])

    # Generate test body
    priv_test_generator = get_priv_test_generator(testsuite)
    body_lines = priv_test_generator(test_data)

    # Return x1/ra
    test_data.int_regs.return_register(1)

    # Produce actual test file
    extra_defines = [*get_priv_test_defines(testsuite), "#define RVTEST_PRIV_TEST"]
    write_test_file(
        test_data,
        body_lines,
        output_path,
        extra_defines=extra_defines,
    )
