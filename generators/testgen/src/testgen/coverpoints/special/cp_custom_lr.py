##################################
# cp_custom_lr.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_custom_lr coverpoint generator."""

from testgen.coverpoints.coverpoints import add_coverpoint_generator
from testgen.data.test_data import TestData
from testgen.instruction_formatters.instruction_formatters import format_single_test
from testgen.utils.common import return_test_regs, to_hex, write_sigupd
from testgen.utils.param_generator import generate_random_params


@add_coverpoint_generator("cp_custom_lr")
def make_custom_lr(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for load-reserved coverpoints."""
    if instr_type != "LR":
        raise ValueError(
            f"cp_custom_lr coverpoint generator only supports LR-type instructions, got {instr_type} for {instr_name}."
        )

    test_lines: list[str] = []

    # cp_custom_aqrl
    for suffix in ["", ".aq", ".aqrl"]:
        test_data.add_testcase_string("cp_custom_aqrl")
        params = generate_random_params(test_data, instr_type, exclude_regs=[0])
        assert (
            params.rs1 is not None
            and params.rd is not None
            and params.temp_val is not None
            and params.temp_reg is not None
        )

        # Add value to load data region
        test_data.add_test_data_value(params.temp_val)

        test_lines.extend(
            [
                f"# Testcase: cp_custom_aqrl with suffix '{suffix}'",
                f"addi x{params.rs1}, x{test_data.int_regs.data_reg}, 0 # copy data_ptr to rs1",
                f"{instr_name}{suffix} x{params.rd}, (x{params.rs1}) # perform load ({to_hex(params.temp_val, test_data.xlen)})",
                write_sigupd(params.rd, test_data, "int"),
                f"addi x{test_data.int_regs.data_reg}, x{test_data.int_regs.data_reg}, SIG_STRIDE # increment data_ptr",
                "",
            ]
        )

        return_test_regs(test_data, params)

    # cp_custom_rd_edges
    edges = [0, 1, -1]
    for edge_val in edges:
        test_data.add_testcase_string("cp_custom_rd_edges")
        test_lines.append("")
        params = generate_random_params(test_data, instr_type, exclude_regs=[0], temp_val=edge_val)
        desc = f"cp_custom_rd_edges (Test source rs1 value = {test_data.xlen_format_str.format(edge_val)})"
        test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc))
        return_test_regs(test_data, params)

    return test_lines
