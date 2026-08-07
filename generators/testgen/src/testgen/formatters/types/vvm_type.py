##################################
# vvm_type.py
#
# VVM type: masked unary vector arithmetic with vd and vs2 operands
# (e.g. vabs.v from Zvabd).
#
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, VectorTypeConfig, add_instruction_formatter
from testgen.formatters.types.vv_type import format_vv_like_type

# vd and vs2 have the same width and vs2 is fully read before vd is written,
# so vd may overlap vs2 (including vd == vs2).
vvm_config = InstructionTypeConfig(required_params={"vd", "vs2"}, vector_data=VectorTypeConfig())


@add_instruction_formatter("VVM", vvm_config)
def format_vvm_type(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_vv_like_type(instr_str, test_data, params, "VVM")
