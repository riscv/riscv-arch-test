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
from testgen.constants import indent_asm
from testgen.data.config import TestConfig
from testgen.data.testcase import TestCase
from testgen.io.templates import insert_footer_template, insert_header_template

SIGUPD_MARGIN = 10


def write_test_file(
    test_config: TestConfig,
    instr_name: str | None,
    test_cases: list[TestCase],
    output_dir: Path,
    file_idx: int = 0,
    extra_defines: list[str] | None = None,
) -> None:
    """
    Write a single test file.

    Args:
        test_config: Test configuration
        instr_name: Instruction name (None for priv tests)
        test_cases: List of TestCase objects containing assembly code and data
        output_dir: Directory to write the test file to
        file_idx: File index for the filename suffix (default 00)
        extra_defines: Additional #define statements for the test (e.g., trap handlers)
    """
    testsuite = test_config.testsuite

    # Combine data from all test cases
    data_values = [v for tc in test_cases for v in tc.data_values]
    data_strings = [s for tc in test_cases for s in tc.data_strings]
    sigupd_count = SIGUPD_MARGIN + sum(tc.sigupd_count for tc in test_cases)

    # Construct filename and paths
    if instr_name is not None:
        filename = f"{testsuite}-{instr_name}-{file_idx:02d}.S"
    else:
        filename = f"{testsuite}-{file_idx:02d}.S"
    test_file = output_dir / filename
    arch_dir = f"rv{test_config.xlen}{'e' if test_config.E_ext else 'i'}" if test_config.xlen else ""
    test_file_relative = Path(arch_dir) / testsuite / filename if arch_dir else Path(testsuite) / filename

    # Test header
    header = insert_header_template(test_config, test_file_relative, sigupd_count, extra_defines)

    # Main test body: banner comment before coverpoint sections, 1 blank line between testcases
    # Apply indent_asm to each line to ensure consistent indentation
    body = ""
    for i, tc in enumerate(test_cases):
        if tc.section_header:
            # Banner comment before coverpoint sections
            body += tc.section_header + "\n\n"
        elif i > 0:
            body += "\n\n"
        body += "\n".join(indent_asm(line) for line in tc.code.split("\n"))

    # Test footer
    test_data_section = generate_test_data_section(data_values, test_config.xlen, test_config.flen)
    test_string_section = generate_test_string_section(data_strings)
    footer = insert_footer_template(test_data_section, test_string_section)

    # Combine all test lines into final string
    test_string = f"{header}\n{body}\n{footer}"

    # Write test file if different from existing file. This avoids unnecessary rebuilds.
    if not test_file.exists() or test_file.read_text() != test_string:
        test_file.write_text(test_string)
