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
from testgen.constants import TESTCASES_PER_PRIV_FILE
from testgen.data.config import TestConfig
from testgen.data.state import TestData
from testgen.data.test_chunk import group_test_chunks
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
    Splits test chunks into multiple files if they exceed TESTCASES_PER_PRIV_FILE.

    Args:
        testsuite: Testsuite name (e.g., "ExceptionsSm", "SsstrictSm")
        output_test_dir: Base directory to output generated tests
    """
    output_path = output_test_dir / "priv" / testsuite
    output_path.mkdir(parents=True, exist_ok=True)

    test_config = TestConfig(
        xlen=0,
        flen=64,
        testsuite=testsuite,
        E_ext=False,
        required_extensions=get_priv_test_required_extensions(testsuite),
        march_extensions=get_priv_test_march_extensions(testsuite),
        extra_params=get_priv_test_params(testsuite),
    )
    extra_defines = [*get_priv_test_defines(testsuite)]

    test_data = TestData(test_config)

    # Reserve registers for priv tests:
    #   - x0: avoid so desired values are actually loaded into registers
    #   - x1/ra: used as the return address for function calls
    #   - x7 is clobbered in rtn_fm_mmode in rvtest_trap_handler.h  Might be freed up if this is redesigned.
    #   - x10, x11, x12 (a0/a1/a2): Used by T-SBI.
    #   - x16-x31: ensure the same test can be used for I or E bases

    priv_exclude_regs = [0, 1, 7, 10, 11, 12, *range(16, 32)]
    test_data.int_regs.consume_registers(priv_exclude_regs)
    seed(reproducible_hash(testsuite))

    # Generate test chunks
    priv_test_generator = get_priv_test_generator(testsuite)
    chunks = priv_test_generator(test_data)

    # Group by named split, split each group into test files, and write
    for split_name, test_files in group_test_chunks(chunks, TESTCASES_PER_PRIV_FILE):
        for file_idx, test_file_chunks in enumerate(test_files):
            write_test_file(test_config, None, test_file_chunks, output_path, file_idx, extra_defines, split_name)

    # Clean up (make sure all registers were returned)
    test_data.int_regs.return_registers(priv_exclude_regs)
    test_data.destroy()
