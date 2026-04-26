##################################
# io/writer.py
#
# Test file writing utilities.
# Jordan Carlin jcarlin@hmc.edu Jan 6 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Test file writing utilities."""

from __future__ import annotations

from pathlib import Path

from testgen.asm.sections import generate_test_data_section, generate_test_string_section
from testgen.constants import INDENT, indent_asm
from testgen.data.config import TestConfig
from testgen.data.registers import IntegerRegisterFile
from testgen.data.test_chunk import TestChunk
from testgen.io.templates import insert_footer_template, insert_header_template

SIGUPD_MARGIN = 10

# Generated test files are marked read-only (0o444) to deter manual edits.
# Regeneration temporarily restores write permission (0o644) before overwriting.
_READONLY_MODE = 0o444
_WRITABLE_MODE = 0o644


def _write_readonly(path: Path, content: str) -> None:
    """Write content to a generated file and mark it read-only to deter manual edits."""
    if path.exists():
        path.chmod(_WRITABLE_MODE)
    path.write_text(content)
    path.chmod(_READONLY_MODE)


def _reinit_pointer_registers(first_chunk: TestChunk) -> str:
    """Emit code to restore non-default signature/data pointer registers.

    RVTEST_BEGIN initializes the signature pointer in x2 and the data pointer
    in x3 at the start of every test file. When an earlier file relocated
    those pointers (e.g. because a coverpoint tested `rd=x3`), subsequent
    files need to re-establish them in whichever registers the chunks expect.
    Uses independent LA macros rather than chained `mv`s so that the two
    loads never have read-after-write dependencies on each other.
    The signature pointer must be restored to the post-canary position used
    after RVTEST_BEGIN, not to the raw `signature_base` label itself.
    """
    lines: list[str] = []
    if first_chunk.start_sig_reg != IntegerRegisterFile.default_sig_reg:
        lines.extend(
            [
                f"{INDENT}LA(x{first_chunk.start_sig_reg}, signature_base) # restore signature pointer base",
                f"{INDENT}addi x{first_chunk.start_sig_reg}, x{first_chunk.start_sig_reg}, SIG_STRIDE # advance past canary",
            ]
        )
    if first_chunk.start_data_reg != IntegerRegisterFile.default_data_reg:
        lines.append(f"{INDENT}LA(x{first_chunk.start_data_reg}, rvtest_data_begin) # restore data pointer")
    return "\n".join(lines)


def write_test_file(
    test_config: TestConfig,
    instr_name: str | None,
    test_chunks: list[TestChunk],
    output_dir: Path,
    file_idx: int = 0,
    extra_defines: list[str] | None = None,
) -> None:
    """
    Write a single test file.

    Args:
        test_config: Test configuration
        instr_name: Instruction name (None for priv tests)
        test_chunks: List of TestChunk objects containing assembly code and data
        output_dir: Directory to write the test file to
        file_idx: File index for the filename suffix (default 00)
        extra_defines: Additional #define statements for the test (e.g., trap handlers)
    """
    testsuite = test_config.testsuite

    # Combine data from all test chunks
    data_values = [v for tc in test_chunks for v in tc.data_values]
    data_strings = [s for tc in test_chunks for s in tc.data_strings]
    sigupd_count = SIGUPD_MARGIN + sum(tc.sigupd_count for tc in test_chunks)

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

    # Main test body: banner comment before coverpoint sections, 1 blank line between test chunks
    # Apply indent_asm to each line to ensure consistent indentation
    body = ""
    # Re-establish signature/data pointers if the first chunk expects non-default registers
    # (because an earlier file's chunks relocated them via mv)
    reinit = _reinit_pointer_registers(test_chunks[0])
    if reinit:
        body += reinit + "\n\n"
    for i, tc in enumerate(test_chunks):
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
        _write_readonly(test_file, test_string)
    else:
        # Content unchanged; still ensure the file is marked read-only in case it isn't already.
        test_file.chmod(_READONLY_MODE)
