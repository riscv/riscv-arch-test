##################################
# data/test_chunk.py
#
# jcarlin@hmc.edu Mar 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""TestChunk dataclass for holding test chunk output data."""

from dataclasses import dataclass, field


@dataclass
class TestChunk:
    """A test chunk — an unsplittable group of one or more testcases.

    A test chunk is the building block of test files. It usually contains a single
    testcase but may contain multiple testcases in the case of special coverpoints
    or privileged tests. Test chunks cannot be split across test files.

    Attributes:
        code: Assembly code for this test chunk
        data_values: Values for .data section
        data_strings: Debug strings for .data section
        sigupd_count: Number of signature updates
        num_testcases: Number of individual testcases (for split counting)
        section_header: Optional banner comment before a coverpoint section
    """

    code: str = ""
    data_values: list[int] = field(default_factory=list)
    data_strings: list[str] = field(default_factory=list)
    sigupd_count: int = 0
    num_testcases: int = 0
    section_header: str | None = None
