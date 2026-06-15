##################################
# data/test_chunk.py
#
# jcarlin@hmc.edu Mar 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""TestChunk dataclass for holding test chunk output data."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TestChunk:
    """A test chunk — an unsplittable group of one or more testcases.

    A test chunk is the building block of test files. It usually contains a single
    testcase but may contain multiple testcases in the case of special coverpoints
    or privileged tests. Test chunks cannot be split across test files.

    Attributes:
        code: Assembly code for this test chunk, as a list of lines (joined with
              newlines when the file is written).
        data_values: Values for .data section
        data_strings: Debug strings for .data section
        sigupd_count: Number of signature updates
        num_testcases: Number of individual testcases (for split counting)
        section_header: Optional banner comment before a coverpoint section
        start_sig_reg: Signature pointer register expected at the start of this chunk
        start_data_reg: Data pointer register expected at the start of this chunk
        end_sig_reg: Signature pointer register in use at the end of this chunk
        end_data_reg: Data pointer register in use at the end of this chunk
    """

    code: list[str] = field(default_factory=list)
    data_values: list[int] = field(default_factory=list)
    data_strings: list[str] = field(default_factory=list)
    sigupd_count: int = 0
    num_testcases: int = 0
    section_header: str | None = None
    start_sig_reg: int = 2
    start_data_reg: int = 3
    end_sig_reg: int = 2
    end_data_reg: int = 3


def split_test_chunks(test_chunks: list[TestChunk], max_per_file: int) -> list[list[TestChunk]]:
    """
    Split a list of TestChunks into groups that don't exceed max_per_file testcases each.
    A single chunk that exceeds max_per_file is never split.
    """
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
