##################################
# priv/generate.py
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
from testgen.priv.registry import get_priv_test_defines, get_priv_test_generator


def generate_priv_test(extension: str, output_test_dir: Path) -> None:
    """
    Generate tests for a privileged extension.

    Args:
        extension: Extension name (e.g., "Sm")
        output_test_dir: Base directory to output generated tests
    """
    # Output always goes to priv/<extension>
    output_path = output_test_dir / "priv" / extension
    output_path.mkdir(parents=True, exist_ok=True)

    # Create test configuration - privileged tests are config_dependent and don't have a fixed xlen
    # The xlen=0 indicates this is a multi-xlen test that uses preprocessor conditionals
    test_config = TestConfig(
        xlen=0,  # One test for all XLENs
        flen=0,
        extension=extension,
        E_ext=False,
        config_dependent=True,
    )

    # Create test data
    test_data = TestData(test_config)

    # Generate test body
    priv_test_generator = get_priv_test_generator(extension)
    body_lines = priv_test_generator(test_data)

    write_test_file(
        test_data,
        body_lines,
        output_path,
        extra_defines=get_priv_test_defines(extension),
    )
