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
        vector_labels: Values for vector registers given in (label, data, sew) triples
        sigupd_count: Number of signature updates
        num_testcases: Number of individual testcases (for split counting)
        split_name: Optional named-split marker. A non-None value starts a new
                    named file group (unless the current group already has the
                    same name); subsequent None chunks stay in that group.
        section_header: Optional banner comment before a coverpoint section
        start_sig_reg: Signature pointer register expected at the start of this chunk
        start_data_reg: Data pointer register expected at the start of this chunk
        end_sig_reg: Signature pointer register in use at the end of this chunk
        end_data_reg: Data pointer register in use at the end of this chunk
    """

    code: list[str] = field(default_factory=list)
    data_values: list[int] = field(default_factory=list)
    data_strings: list[str] = field(default_factory=list)
    vector_labels: list[tuple[str, list[int], int]] = field(default_factory=list)
    sigupd_count: int = 0
    num_testcases: int = 0
    split_name: str | None = None
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


def group_test_chunks(
    test_chunks: list[TestChunk], max_per_file: int
) -> list[tuple[str | None, list[list[TestChunk]]]]:
    """
    Group TestChunks by their split_name, then length-split each group.

    A chunk with a non-None split_name starts a new named group unless the current
    group already has that name; chunks with split_name=None stay in the current
    group. An unnamed group can only occur before the first named chunk. Reusing a
    name non-contiguously raises ValueError.

    Returns an ordered list of (group_name, test_files) pairs, where test_files is
    the length-based split of that group's chunks (max_per_file testcases per file).
    """
    if not test_chunks:
        raise ValueError("No test chunks provided!")

    groups: list[tuple[str | None, list[TestChunk]]] = []
    seen_names: set[str] = set()
    current_name: str | None = None
    current_group: list[TestChunk] = []

    for tc in test_chunks:
        if tc.split_name is not None and tc.split_name != current_name:
            if tc.split_name in seen_names:
                raise ValueError(f'Split name "{tc.split_name}" reused non-contiguously!')
            seen_names.add(tc.split_name)
            if current_group:
                groups.append((current_name, current_group))
            current_name = tc.split_name
            current_group = []
        current_group.append(tc)
    groups.append((current_name, current_group))

    return [(name, split_test_chunks(chunks, max_per_file)) for name, chunks in groups]
