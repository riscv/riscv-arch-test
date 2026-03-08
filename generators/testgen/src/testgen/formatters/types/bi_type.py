##################################
# bi_type.py
#
# Jiacheng Tong tjc.challenger1024@gmail.com Mar 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import load_int_reg, write_sigupd
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

bi_config = InstructionTypeConfig(
    required_params={"rs1", "rs1val", "immval", "temp_reg", "temp_val"}, imm_bits=5, imm_signed=False
)


@add_instruction_formatter("BI", bi_config)
def format_bi_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format BI-type instruction for Zibi (rs1, cimm, offset)."""
    assert params.rs1 is not None and params.rs1val is not None
    assert params.immval is not None
    assert params.temp_reg is not None and params.temp_val is not None

    setup = [
        load_int_reg("rs1", params.rs1, params.rs1val, test_data),
        load_int_reg("branch taken value", params.temp_reg, params.temp_val, test_data),
    ]

    test = [
        f"{instr_name} x{params.rs1}, {params.immval}, 1f # perform operation",
    ]

    check = [
        f"LI(x{params.temp_reg}, -1) # branch not taken, set temp_reg to -1",
        "1:",
        write_sigupd(params.temp_reg, test_data),
    ]

    return (setup, test, check)
