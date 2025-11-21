##################################
# cp_custom.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Custom coverpoint generator (cp_custom)."""

from testgen.coverpoints.coverpoints import add_coverpoint_generator
from testgen.data.test_data import TestData
from testgen.utils.templates import insert_test_template


@add_coverpoint_generator("cp_custom")
def make_custom(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for custom coverpoints using a template file."""
    test_lines, sigupd_count_increment = insert_test_template(f"{instr_name}.S", test_data.xlen, test_data)
    test_data.sigupd_count += sigupd_count_increment
    return [test_lines]
