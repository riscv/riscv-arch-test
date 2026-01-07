#!/usr/bin/env python3

##################################
# testgen.py
#
# jcarlin@hmc.edu 5 Oct 2025
# SPDX-License-Identifier: Apache-2.0
#
# Generate directed tests for functional coverage
##################################

import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Annotated

import typer
from rich.progress import track

from testgen.coverpoints import generate_tests_for_coverpoint
from testgen.data.test_config import TestConfig
from testgen.data.test_data import TestData
from testgen.utils.common import generate_test_data_section, generate_test_string_section
from testgen.utils.templates import insert_setup_template
from testgen.utils.testplans import get_extensions, read_testplan

# Global constants
# Max testcases per file before splitting. Individual coverpoints won't be split, so if one coverpoint exceeds this, the file will exceed this limit.
TESTCASES_PER_FILE = 1000

# Tests to generate RV32/64E variants for
E_EXTENSION_TESTS = {"I", "M", "Zmmul", "Zca", "Zcb", "Zba", "Zbb", "Zbs"}  # TODO: Add Zcmp and Zcmt when implemented

# CLI interface setup
testgen_app = typer.Typer(context_settings={"help_option_names": ["-h", "--help"]})


@testgen_app.command()
def generate_all_tests(
    testplan_dir: Annotated[
        Path, typer.Argument(exists=True, file_okay=False, help="Directory containing testplan CSV files")
    ],
    output_test_dir: Annotated[
        Path, typer.Option("--output_test_dir", "-o", help="Directory to output generated tests")
    ] = Path("tests"),
    extensions: Annotated[
        str,
        typer.Option(
            "--extensions", "-e", help="Comma-separated list of extensions to generate tests for (default: all)"
        ),
    ] = "all",
    jobs: Annotated[
        int | None,
        typer.Option("--jobs", "-j", help="Number of parallel jobs (default: number of CPU cores)"),
    ] = None,
) -> None:
    """
    Generate riscv-arch-test tests from testplan CSV files.
    """
    # Set number of parallel jobs to CPU count if not specified
    if jobs is None:
        jobs = os.cpu_count() or 1

    # Get list of extensions
    extensions_from_testplans = get_extensions(testplan_dir)
    extension_list: list[str] = []
    if extensions == "all":
        extension_list = extensions_from_testplans
    else:
        for ext in extensions.split(","):
            ext = ext.strip()
            if ext not in extensions_from_testplans:
                print(
                    f"Warning: Extension {ext} not found in testplans at {testplan_dir}. This is normal for priv tests."
                )
                # raise ValueError(f"Extension {ext} not found in testplans at {testplan_dir}")
            else:
                extension_list.append(ext)

    # Build list of test generation tasks (extension configs to process)
    tasks: list[tuple[int, bool, str, Path, Path]] = []
    for xlen in [32, 64]:
        for E_ext in [False, True]:
            for extension in sorted(extension_list):
                if E_ext and extension not in E_EXTENSION_TESTS:
                    continue
                tasks.append((xlen, E_ext, extension, testplan_dir, output_test_dir))

    # Execute tasks in parallel
    with ProcessPoolExecutor(max_workers=jobs) as executor:
        futures = [executor.submit(generate_tests_for_extension, task) for task in tasks]

        # Process completed tasks with progress tracking
        for future in track(futures, description="[cyan]Generating tests...", total=len(futures)):
            future.result()  # Re-raise any exceptions


def generate_tests_for_extension(task: tuple[int, bool, str, Path, Path]) -> None:
    """
    Worker function to generate tests for one extension configuration.

    Args:
        task: Tuple of (xlen, E_ext, extension, testplan_dir, output_test_dir)
    """
    # Unpack task parameters
    xlen, E_ext, extension, testplan_dir, output_test_dir = task

    # Read testplan for this extension
    instructions = read_testplan(testplan_dir / f"{extension}.csv")
    if extension == "I" and E_ext:
        extension = "E"

    # Create test configuration
    output_dir = output_test_dir / f"rv{xlen}{'e' if E_ext else 'i'}/{extension}"
    output_dir.mkdir(parents=True, exist_ok=True)
    flen = (
        128
        if extension in ["Q", "ZfaQ", "ZfhQ"]
        else 64
        if extension in ["D", "ZfaD", "ZfhD", "Zcd", "ZfaZfhD", "ZfhminD"]
        else 32
    )
    test_config = TestConfig(xlen=xlen, flen=flen, extension=extension, E_ext=E_ext)
    print(f"Generating tests for {output_dir}")

    # Iterate through each instruction in extension
    for instr_name, instr_data in sorted(instructions.items()):
        # Skip instructions not valid for this xlen
        if (xlen == 32 and not instr_data.rv32) or (xlen == 64 and not instr_data.rv64):
            continue

        generate_tests_for_instruction(
            instr_name,
            instr_data.instr_type,
            instr_data.coverpoints,
            test_config,
            output_dir,
        )


def generate_tests_for_instruction(
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
                instr_name,
                current_test_data,
                current_body_lines,
                file_idx,
                output_dir,
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
        instr_name,
        current_test_data,
        current_body_lines,
        file_idx,
        output_dir,
    )


def write_test_file(
    instr_name: str,
    test_data: TestData,
    body_lines: list[str],
    file_idx: int,
    output_dir: Path,
) -> None:
    """Write a single test file."""
    test_config = test_data.config
    extension = test_config.extension
    filename = f"{extension}-{instr_name}-{file_idx:02d}.S"

    test_file = output_dir / filename
    arch_dir = f"rv{test_config.xlen}{'e' if test_config.E_ext else 'i'}"
    test_file_relative = Path(arch_dir) / extension / filename

    extra_defines = ""
    # Enable floating point if needed
    if any(ext in extension for ext in ["F", "D", "Q", "Zf", "Zcf", "Zcd"]):
        extra_defines += "#define RVTEST_FP"

    # Construct file content
    final_lines: list[str] = []
    final_lines.append(insert_setup_template("testgen_header.S", test_config, test_file_relative, extra_defines))

    final_lines.extend(body_lines)

    # Test footer
    final_lines.append(insert_setup_template("testgen_footer.S", test_config, test_file_relative, extra_defines))

    # Generate final test string with signature size and test data section
    sig_words = test_data.sigupd_count
    test_data_section = generate_test_data_section(test_data)
    test_data_string_section = generate_test_string_section(test_data)
    test_string = (
        "\n".join(final_lines)
        .replace("@SIGUPD_COUNT_FROM_TESTGEN@", str(sig_words))
        .replace("@TEST_DATA@", test_data_section)
        .replace("@TESTCASE_STRINGS@", test_data_string_section)
    )

    # Clean up test data
    test_data.destroy()

    # Write test file if different from existing file
    if not test_file.exists() or test_file.read_text() != test_string:
        test_file.write_text(test_string)
        # print(f"Updated {test_file}")


def main() -> None:
    testgen_app()  # runs generate_tests() using Typer to fill in args


if __name__ == "__main__":
    main()
