##################################
# generate/priv.py
#
# Privileged test generation orchestration.
# jcarlin@hmc.edu Jan 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Privileged test generation orchestration."""

from dataclasses import replace
from pathlib import Path
from random import seed

from testgen.asm.helpers import reproducible_hash
from testgen.constants import PRIV_TRAP_SIGUPD_COUNT
from testgen.data.config import TestConfig
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk, group_test_chunks
from testgen.io.writer import write_test_file
from testgen.priv import get_priv_test_generators
from testgen.priv.registry import PrivTestRegistryEntry


def generate_priv_test(testsuite: str, output_test_dir: Path) -> None:
    """
    Generate tests for a privileged testsuite.
    Splits test chunks into multiple files if they exceed the testsuite's testcases-per-file limit
    (TESTCASES_PER_PRIV_FILE unless the generator overrides it).

    Args:
        testsuite: Testsuite name (e.g., "ExceptionsSm", "SsstrictSm")
        output_test_dir: Base directory to output generated tests
    """
    output_path = output_test_dir / "priv" / testsuite
    generated_files: set[Path] = set()
    next_file_indices: dict[str | None, int] = {}
    for entry in get_priv_test_generators(testsuite):
        generated_files.update(_generate_priv_test_entry(testsuite, output_test_dir, entry, next_file_indices))

    for stale_file in set(output_path.glob("*.S")) - generated_files:
        stale_file.unlink()


def _generate_priv_test_entry(
    testsuite: str,
    output_test_dir: Path,
    entry: PrivTestRegistryEntry,
    next_file_indices: dict[str | None, int],
) -> set[Path]:
    """Generate tests for one registry entry."""
    output_path = output_test_dir / "priv" / testsuite
    output_path.mkdir(parents=True, exist_ok=True)
    generated_files: set[Path] = set()

    test_config = TestConfig(
        xlen=0,
        flen=64,
        testsuite=testsuite,
        E_ext=False,
        required_extensions=entry.required_extensions,
        forbidden_extensions=entry.forbidden_extensions,
        march_extensions=entry.march_extensions,
        extra_params=entry.params,
    )
    test_data = TestData(test_config)

    # Reserve registers for priv tests:
    #   - x0: avoid so desired values are actually loaded into registers
    #   - x1/ra: used as the return address for function calls
    #   - x7 is clobbered in rtn_fm_mmode in rvtest_trap_handler.h  Might be freed up if this is redesigned.
    #   - x10, x11, x12 (a0/a1/a2): Used by T-SBI.
    #   - x16-x31: ensure the same test can be used for I or E bases
    priv_exclude_regs = [0, 1, 7, 10, 11, 12, *range(16, 32)]
    test_data.int_regs.consume_registers(priv_exclude_regs)

    seed_key = f"{testsuite}-{entry.generator.__name__}-0"
    seed(reproducible_hash(seed_key))

    # Generate test chunks
    chunks = list(entry.generator(test_data))

    # Group by named split, split each group into test files, and write
    for split_name, test_files in group_test_chunks(chunks, entry.testcases_per_file):
        split_config = _split_test_config(test_config, test_files[0][0])
        first_file_idx = next_file_indices.get(split_name, 0)
        for file_idx, test_file_chunks in enumerate(test_files, start=first_file_idx):
            extra_defines = list(entry.extra_defines)
            # Set default trap signature size if the chunks do not specify one
            if not any(tc.trap_sigupd_count for tc in test_file_chunks):
                extra_defines.append(f"#define TRAP_SIGUPD_COUNT {PRIV_TRAP_SIGUPD_COUNT}")
            generated_files.add(
                write_test_file(split_config, None, test_file_chunks, output_path, file_idx, extra_defines, split_name)
            )
        next_file_indices[split_name] = first_file_idx + len(test_files)

    # Clean up (make sure all registers were returned)
    test_data.int_regs.return_registers(priv_exclude_regs)
    test_data.destroy()
    return generated_files


def _split_test_config(test_config: TestConfig, first_chunk: TestChunk) -> TestConfig:
    """Add the header constraints of a named split (set on its first chunk) to the entry's configuration.

    The march string stays the entry's, so the constraints change only which targets select the files.
    """
    if not (first_chunk.required_extensions or first_chunk.forbidden_extensions or first_chunk.params):
        return test_config
    if test_config.required_extensions is None:
        raise ValueError(f"{test_config.testsuite}: split header constraints need explicit required_extensions")
    march_extensions = test_config.march_extensions
    if march_extensions is None:
        march_extensions = [
            ext for req in test_config.required_extensions for ext in (req if isinstance(req, list) else [req])
        ]
    return replace(
        test_config,
        required_extensions=[
            *test_config.required_extensions,
            *(ext for ext in first_chunk.required_extensions if ext not in test_config.required_extensions),
        ],
        forbidden_extensions=[*(test_config.forbidden_extensions or []), *first_chunk.forbidden_extensions],
        march_extensions=march_extensions,
        extra_params=[*(test_config.extra_params or []), *first_chunk.params],
    )
