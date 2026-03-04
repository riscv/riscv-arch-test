##################################
# io/writer.py
#
# Test file writing utilities.
# Jordan Carlin jcarlin@hmc.edu Jan 6 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Test file writing utilities."""

from pathlib import Path

from testgen.asm.sections import generate_test_data_section, generate_test_string_section
from testgen.data.state import TestData
from testgen.io.templates import insert_footer_template, insert_header_template


def write_test_file(
    test_data: TestData,
    body_lines: list[str],
    output_dir: Path,
    file_idx: int = 0,
    extra_defines: list[str] | None = None,
) -> None:
    """
    Write a single test file.

    Args:
        test_data: TestData containing signature counts and testcase strings
        body_lines: List of assembly code lines for the test body
        output_dir: Directory to write the test file to
        file_idx: File index for the filename suffix (default 00)
        extra_defines: Additional #define statements for the test (e.g., trap handlers)
    """
    # Extract test configuration
    test_config = test_data.config
    testsuite = test_config.testsuite

    # Construct filename and paths
    try:
        filename = f"{testsuite}-{test_data.instr_name}-{file_idx:02d}.S"
    except ValueError:  # instr_name is None for priv tests
        filename = f"{testsuite}-{file_idx:02d}.S"
    test_file = output_dir / filename
    arch_dir = f"rv{test_config.xlen}{'e' if test_config.E_ext else 'i'}" if test_config.xlen else ""
    test_file_relative = Path(arch_dir) / testsuite / filename if arch_dir else Path(testsuite) / filename

    # Test header
    final_lines = [insert_header_template(test_config, test_file_relative, test_data.sigupd_count, extra_defines)]

    # Main test body
    final_lines.extend(body_lines)

    # Test footer
    test_data_section = generate_test_data_section(test_data)
    test_string_section = generate_test_string_section(test_data)
    final_lines.append(insert_footer_template(test_data_section, test_string_section))

    # Combine all test lines into final string
    test_string = "\n".join(final_lines)

    # Clean up test data
    test_data.destroy()

    # Write test file if different from existing file. This avoids unnecessary rebuilds.
    if not test_file.exists() or test_file.read_text() != test_string:
        test_file.write_text(test_string)
