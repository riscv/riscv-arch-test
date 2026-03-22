##################################
# cp_custom_lr.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_custom_lr coverpoint generator."""

from testgen.asm.helpers import return_test_regs, to_hex, write_sigupd
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.params import generate_random_params


@add_coverpoint_generator("cp_custom_lr")
def make_custom_lr(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for load-reserved coverpoints."""
    if instr_type != "LR":
        raise ValueError(
            f"cp_custom_lr coverpoint generator only supports LR-type instructions, got {instr_type} for {instr_name}."
        )

    test_chunks: list[TestChunk] = []

    # cp_custom_aqrl — inline assembly, wrap as single TestChunk
    tc = test_data.begin_test_chunk()
    test_lines: list[str] = []

    for suffix in ["", ".aq", ".aqrl"]:
        params = generate_random_params(test_data, instr_type, exclude_regs=[0])
        assert (
            params.rs1 is not None
            and params.rd is not None
            and params.temp_val is not None
            and params.temp_reg is not None
        )

        # Add value to load data region
        tc.data_values.append(params.temp_val)

        test_lines.extend(
            [
                f"# Testcase: cp_custom_aqrl with suffix '{suffix}'",
                f"addi x{params.rs1}, x{test_data.int_regs.data_reg}, 0 # copy data_ptr to rs1",
                test_data.add_testcase(suffix, "cp_custom_aqrl"),
                f"{instr_name}{suffix} x{params.rd}, (x{params.rs1}) # perform load ({to_hex(params.temp_val, test_data.xlen)})",
                write_sigupd(params.rd, test_data, "int"),
                f"addi x{test_data.int_regs.data_reg}, x{test_data.int_regs.data_reg}, SIG_STRIDE # increment data_ptr",
                "",
            ]
        )

        return_test_regs(test_data, params)

    tc.code = "\n".join(test_lines)
    test_chunks.append(test_data.end_test_chunk())

    # cp_custom_rd_edges — uses format_single_testcase, each produces its own TestChunk
    edges = [0, 1, -1]
    for edge_val in edges:
        params = generate_random_params(test_data, instr_type, exclude_regs=[0], temp_val=edge_val)
        desc = f"cp_custom_rd_edges (Test source rs1 value = {test_data.xlen_format_str.format(edge_val)})"
        test_chunks.append(
            format_single_testcase(instr_name, instr_type, test_data, params, desc, f"{edge_val}", "cp_custom_rd_edges")
        )
        return_test_regs(test_data, params)

    return test_chunks
