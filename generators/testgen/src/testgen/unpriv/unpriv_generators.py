##################################
# unpriv_generators.py
#
# Jordan Carlin jcarlin@hmc.edu Jan 6 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Unprivileged test generation from CSV testplans."""

from pathlib import Path

from testgen.coverpoints import generate_tests_for_coverpoint
from testgen.data.test_config import TestConfig
from testgen.data.test_data import TestData
from testgen.utils.test_writer import write_test_file
from testgen.utils.testplans import read_testplan

# Max testcases per file before splitting. Individual coverpoints won't be split,
# so if one coverpoint exceeds this, the file will exceed this limit.
TESTCASES_PER_FILE = 1000


def generate_unpriv_extension_tests(task: tuple[int, bool, str, Path, Path]) -> None:
    """
    Generate tests for all instructions in a given unprivileged extension.

    Args:
        task: Tuple of (xlen, E_ext, extension, testplan_dir, output_test_dir)
    """
    # Unpack task parameters
    xlen, E_ext, extension, testplan_dir, output_test_dir = task

    # Read testplan for this extension
    instructions = read_testplan(testplan_dir / f"{extension}.csv")
    if extension == "I" and E_ext:
        extension = "E"

    # Create extension-wide test configuration
    output_dir = output_test_dir / f"rv{xlen}{'e' if E_ext else 'i'}/{extension}"
    output_dir.mkdir(parents=True, exist_ok=True)
    flen = (
        128
        if extension in ["Q", "ZfaQ", "ZfhQ"]
        else 64
        if extension in ["D", "ZfaD", "ZfhD", "Zcd", "ZfaZfhD", "ZfhminD"]
        else 32
    )
    config_dependent = False
    test_config = TestConfig(xlen=xlen, flen=flen, extension=extension, E_ext=E_ext, config_dependent=config_dependent)

    # Iterate through each instruction in the extension; generate separate test files for each
    for instr_name, instr_data in sorted(instructions.items()):
        # Skip instructions not valid for this xlen
        if (xlen == 32 and not instr_data.rv32) or (xlen == 64 and not instr_data.rv64):
            continue

        _generate_unpriv_tests_for_instruction(
            instr_name,
            instr_data.instr_type,
            instr_data.coverpoints,
            test_config,
            output_dir,
        )


def _generate_unpriv_tests_for_instruction(
    instr_name: str,
    instr_type: str,
    coverpoints: list[str],
    test_config: TestConfig,
    output_dir: Path,
) -> None:
    """
    Generate tests for a specific instruction based on its coverpoints.
    Splits tests into multiple parts if they exceed TESTS_PER_FILE.

    Args:
        instr_name: Instruction mnemonic (e.g., 'add', 'lw')
        instr_type: Type of instruction (e.g., 'R', 'I')
        coverpoints: List of coverpoints to generate
        test_config: Test configuration
        output_dir: Directory to output generated tests
    """
    current_test_data = TestData(test_config, instr_name)
    current_body_lines: list[str] = []
    file_idx = 0

    # Iterate through each coverpoint and generate tests
    for coverpoint in coverpoints:
        # Skip cp_asm_count if mixed with other coverpoints
        if coverpoint == "cp_asm_count" and len(coverpoints) > 1:
            continue

        # Create a copy of the current state to try generating the next coverpoint
        temp_test_data = current_test_data.copy()

        # Generate code for this coverpoint using the temporary state
        cp_code = generate_tests_for_coverpoint(instr_name, instr_type, coverpoint, temp_test_data)

        # Check if we should split
        # Split if adding this coverpoint would exceed the limit AND we have content already
        if current_test_data.test_count > 0 and (temp_test_data.test_count > TESTCASES_PER_FILE):
            # Write current file
            write_test_file(
                current_test_data,
                current_body_lines,
                output_dir,
                file_idx,
            )

            # Start new file
            file_idx += 1
            current_test_data = TestData(test_config, instr_name)
            current_body_lines = []

            # Regenerate code for this coverpoint using the NEW state
            # TODO: This is not the most efficient and could be optimized to avoid regenerating,
            # but is not currently a bottleneck and this is simpler for now.
            cp_code = generate_tests_for_coverpoint(instr_name, instr_type, coverpoint, current_test_data)
        else:
            # If we didn't split, commit the temporary state to the current state
            current_test_data = temp_test_data

        current_body_lines.append(cp_code)

    # Write the last file
    write_test_file(
        current_test_data,
        current_body_lines,
        output_dir,
        file_idx,
    )
