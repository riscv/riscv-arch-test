##################################
# generate/priv.py
#
# Privileged test generation orchestration.
# jcarlin@hmc.edu Jan 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Privileged test generation orchestration."""

from pathlib import Path
from random import seed

from testgen.asm.helpers import reproducible_hash
from testgen.data.config import TestConfig
from testgen.data.state import TestData
from testgen.io.writer import write_test_file
from testgen.priv.registry import (
    get_priv_test_defines,
    get_priv_test_generator,
    get_priv_test_march_extensions,
    get_priv_test_params,
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
        flen=64,
        testsuite=testsuite,
        E_ext=False,
        config_dependent=True,
        required_extensions=get_priv_test_required_extensions(testsuite),
        march_extensions=get_priv_test_march_extensions(testsuite),
        extra_params=get_priv_test_params(testsuite),
    )

    # Create test data
    test_data = TestData(test_config)

    # Begin a single TestChunk for the entire priv test
    # TODO: Might eventually want to update priv tests to use multiple test chunks instead
    # so they can be split for long priv tests (e.g. Ssstrict)
    tc = test_data.begin_test_chunk()

    # Reserve registers for priv tests:
    #   - x0: avoid so desired values are actually loaded into registers
    #   - x1/ra: used as the return address for function calls
    #   - x6, x7, x9: used by the RVTEST_GOTO_LOWER_MODE macro
    #   - x16-x31: ensure the same test can be used for I or E bases
    priv_exclude_regs = [0, 1, 6, 7, 9, *range(16, 32)]
    test_data.int_regs.consume_registers(priv_exclude_regs)

    # Seed the RNG for reproducible test generation
    seed(reproducible_hash(testsuite))

    # Generate test body
    priv_test_generator = get_priv_test_generator(testsuite)
    body_lines = priv_test_generator(test_data)

    # Return x0/zero and x1/ra
    test_data.int_regs.return_registers(priv_exclude_regs)

    # Save test chunk
    tc.code = "\n".join(body_lines)
    test_data.end_test_chunk()

    # Produce actual test file
    extra_defines = [*get_priv_test_defines(testsuite), "#define RVTEST_PRIV_TEST"]
    write_test_file(test_config, None, [tc], output_path, extra_defines=extra_defines)
    test_data.destroy()
