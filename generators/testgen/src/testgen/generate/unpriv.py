##################################
# generate/unpriv.py
#
# Unprivileged test generation orchestration.
# jcarlin@hmc.edu Jan 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Unprivileged test generation from CSV testplans."""

from pathlib import Path

from testgen.constants import (
    CONFIG_DEPENDENT_EXTENSIONS,
    TESTCASES_PER_FILE,
    get_flen_for_extension,
)
from testgen.coverpoints import generate_tests_for_coverpoint
from testgen.data.config import TestConfig
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.io.testplans import read_testplan
from testgen.io.writer import write_test_file


def generate_unpriv_extension_tests(
    xlen: int, E_ext: bool, testsuite: str, testplan_dir: Path, output_test_dir: Path
) -> None:
    """
    Generate tests for all instructions in a given unprivileged testsuite.

    Args:
        xlen: Target XLEN (32 or 64)
        E_ext: Whether to generate RV32E tests
        testsuite: Testsuite to generate tests for (e.g., 'I', 'M', 'ZcbM', 'MisalignD')
        testplan_dir: Directory containing testplan CSV files
        output_test_dir: Directory to output generated tests
    """
    # Read testplan for this testsuite
    instructions = read_testplan(testplan_dir / f"{testsuite}.csv")
    if testsuite == "I" and E_ext:
        testsuite = "E"

    # Create testsuite-wide test configuration
    output_dir = output_test_dir / f"rv{xlen}{'e' if E_ext else 'i'}/{testsuite}"
    output_dir.mkdir(parents=True, exist_ok=True)

    flen = get_flen_for_extension(testsuite)
    config_dependent = testsuite in CONFIG_DEPENDENT_EXTENSIONS
    test_config = TestConfig(xlen=xlen, flen=flen, testsuite=testsuite, E_ext=E_ext, config_dependent=config_dependent)

    # Iterate through each instruction in the testsuite; generate separate test files for each
    for instr_data in instructions:
        # Skip instructions not valid for this xlen
        if (xlen == 32 and not instr_data.rv32) or (xlen == 64 and not instr_data.rv64):
            continue

        _generate_unpriv_tests_for_instruction(
            instr_data.instr_name,
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
    Splits test chunks into multiple test files if they exceed TESTCASES_PER_FILE.

    Args:
        instr_name: Instruction mnemonic (e.g., 'add', 'lw')
        instr_type: Type of instruction (e.g., 'R', 'I')
        coverpoints: List of coverpoints to generate
        test_config: Test configuration
        output_dir: Directory to output generated tests
    """
    test_data = TestData(test_config, instr_name)
    all_test_chunks: list[TestChunk] = []

    # Iterate through each coverpoint and generate test chunks
    for coverpoint in coverpoints:
        # Skip cp_asm_count if mixed with other coverpoints
        if coverpoint == "cp_asm_count" and len(coverpoints) > 1:
            continue

        all_test_chunks.extend(generate_tests_for_coverpoint(instr_name, instr_type, coverpoint, test_data))

    # Split into test files and write
    test_files = _split_test_chunks(all_test_chunks, TESTCASES_PER_FILE)
    for file_idx, test_file_chunks in enumerate(test_files):
        write_test_file(test_config, instr_name, test_file_chunks, output_dir, file_idx)

    # Clean up (make sure all registers were returned)
    test_data.destroy()


def _split_test_chunks(test_chunks: list[TestChunk], max_per_file: int) -> list[list[TestChunk]]:
    """Split a list of TestChunks into groups that don't exceed max_per_file testcases each."""
    # Check for empty list
    if not test_chunks:
        raise ValueError("No test chunks provided!")

    test_files: list[list[TestChunk]] = []
    current_file_chunks: list[TestChunk] = []
    count = 0

    # Iterate over all test chunks and group into test files
    for tc in test_chunks:
        if count > 0 and count + tc.num_testcases > max_per_file:
            test_files.append(current_file_chunks)
            current_file_chunks = []
            count = 0
        current_file_chunks.append(tc)
        count += tc.num_testcases

    # Add final file
    if current_file_chunks:
        test_files.append(current_file_chunks)
    return test_files
