##################################
# generate/unpriv.py
#
# Unprivileged test generation orchestration.
# jcarlin@hmc.edu Jan 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Unprivileged test generation from CSV testplans."""

import re
from pathlib import Path

from testgen.constants import (
    INDENT,
    TESTCASES_PER_FILE,
    get_flen_for_extension,
)
from testgen.coverpoints import generate_tests_for_coverpoint
from testgen.data.config import TestConfig
from testgen.data.registers import IntegerRegisterFile
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk, split_test_chunks
from testgen.formatters.vector_params import extract_instruction_info
from testgen.io.testplans import read_testplan
from testgen.io.writer import write_test_file


def _append_sig_reg_reset(test_file_chunks: list[TestChunk]) -> None:
    """Move the signature pointer back to the default register after the last testcase.

    Coverpoints that target x2 as a source/destination relocate the signature
    pointer to another register and leave it there. The test teardown code
    (RVTEST_CODE_END) assumes the signature pointer is in DEFAULT_SIG_REG, so
    emit a `mv` at the end of the final chunk to restore it.
    """
    last_chunk = test_file_chunks[-1]
    if last_chunk.end_sig_reg == IntegerRegisterFile.default_sig_reg:
        return
    reset = (
        "\n"
        f"{INDENT}mv x{IntegerRegisterFile.default_sig_reg}, x{last_chunk.end_sig_reg}"
        f" # restore signature pointer to default register for teardown"
    )
    last_chunk.code.append(reset)


def generate_unpriv_extension_tests(
    xlen: int, E_ext: bool, testsuite: str, testplan_dir: Path, output_test_dir: Path, is_vector: bool = False
) -> None:
    """
    Generate tests for all instructions in a given unprivileged testsuite.

    Args:
        xlen: Target XLEN (32 or 64)
        E_ext: Whether to generate RV32E tests
        testsuite: Testsuite to generate tests for (e.g., 'I', 'M', 'ZcbM', 'MisalignD')
        testplan_dir: Directory containing testplan CSV files
        output_test_dir: Directory to output generated tests
        is_vector: Set in vector test suites
    """
    # Read testplan for this testsuite
    if is_vector:
        match = re.search(r"([^0-9]*)\d*$", testsuite)
        assert match is not None, f"Unable to Parse Vector Extension {testsuite} into a Testplan and SEW Pair"

        testplan = match.group(1)
        sew = _detect_sew(testsuite)
    else:
        testplan = testsuite
        sew = None  # Not relevant in non-vector cases

    instructions = read_testplan(testplan_dir / f"{testplan}.csv")
    if testsuite == "I" and E_ext:
        testsuite = "E"

    # Create testsuite-wide test configuration
    output_dir = output_test_dir / f"rv{xlen}{'e' if E_ext else 'i'}/{testsuite}"
    output_dir.mkdir(parents=True, exist_ok=True)

    flen = get_flen_for_extension(testsuite)
    test_config = TestConfig(xlen=xlen, flen=flen, testsuite=testsuite, E_ext=E_ext, sew=sew)

    # Iterate through each instruction in the testsuite; generate separate test files for each
    for instr_data in instructions:
        # Skip instructions not valid for this xlen
        if (xlen == 32 and not instr_data.rv32) or (xlen == 64 and not instr_data.rv64):
            continue

        if is_vector and sew not in instr_data.sews_supported:
            continue

        _generate_unpriv_tests_for_instruction(
            instr_data.instr_name,
            instr_data.instr_type,
            instr_data.coverpoints,
            test_config,
            output_dir,
            is_vector,
        )


def _detect_sew(testsuite: str) -> int:
    """
    Extracts the SEW from a testsuite name
        e.g. _detect_sew("Vx64") = 64
    """

    for pattern, sew in [
        (r"Zvfbfmin$", 16),
        (r"Zvfhmin$", 16),
        (r"Zvfbfwma$", 16),
        (r"Zvk(g|nha|ned|sed|sh)$", 32),  # codespell:ignore ned
    ]:
        match = re.search(pattern, testsuite)
        if match:
            return sew

    match = re.search(r"(\d+)$", testsuite)
    if match:
        return int(match.group(1))

    return 8


def _generate_unpriv_tests_for_instruction(
    instr_name: str,
    instr_type: str,
    coverpoints: list[str],
    test_config: TestConfig,
    output_dir: Path,
    is_vector: bool = False,
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
        is_vector: Set in vector test suites
    """
    test_data = TestData(test_config, instr_name)
    all_test_chunks: list[TestChunk] = []

    # Iterate through each coverpoint and generate test chunks
    for coverpoint in coverpoints:
        # Skip cp_asm_count and std_vec if mixed with other coverpoints
        if coverpoint in ["cp_asm_count", "std_vec"] and len(coverpoints) > 1:
            continue

        all_test_chunks.extend(generate_tests_for_coverpoint(instr_name, instr_type, coverpoint, test_data))

    # Split into test files and write
    test_files = split_test_chunks(all_test_chunks, TESTCASES_PER_FILE)
    for file_idx, test_file_chunks in enumerate(test_files):
        _append_sig_reg_reset(test_file_chunks)
        if is_vector:
            assert test_config.sew is not None, "SEW must be set for vector tests"
            sew = test_config.sew
            vdsew = sew
            info = extract_instruction_info(instr_name, instr_type)
            if "vd" in info.widened_regs:
                vdsew *= 2
            elif info.load_store_eew == 64:
                vdsew = 64
            extra_defines = [
                "#define RVTEST_VECTOR",
                f"#define RVTEST_SEW {sew}",
                f"#define VDSEW {vdsew}",
            ]
        else:
            extra_defines = []

        write_test_file(test_config, instr_name, test_file_chunks, output_dir, file_idx, extra_defines)

    # Clean up (make sure all registers were returned)
    test_data.destroy()
