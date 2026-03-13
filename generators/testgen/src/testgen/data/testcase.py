##################################
# data/testcase.py
#
# jcarlin@hmc.edu Mar 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""TestCase dataclass for holding individual test case output data."""

from dataclasses import dataclass, field


@dataclass
class TestCase:
    """A single test case with all its output data.

    Attributes:
        code: Assembly code for this test case
        data_values: Values for .data section
        data_strings: Debug strings for .data section
        sigupd_count: Number of signature updates
        num_tests: Number of logical tests (for split counting)
    """

    code: str = ""
    data_values: list[int] = field(default_factory=list)
    data_strings: list[str] = field(default_factory=list)
    sigupd_count: int = 0
    num_tests: int = 0
