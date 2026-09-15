##################################
# fvv_type.py
#
# rwolk@hmc.edu August 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.vector_helpers import handle_vector_fp
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, VectorTypeConfig, add_instruction_formatter
from testgen.formatters.types.vv_type import format_vv_like_type

fvv_config = InstructionTypeConfig(
    instruction_class=["vector_fp"], required_params={"vd", "vs2"}, vector_data=VectorTypeConfig()
)
fwv_config = InstructionTypeConfig(
    instruction_class=["vector_fp"],
    required_params={"vd", "vs2"},
    vector_data=VectorTypeConfig(overlap_constraints={("vd_bottom", "vs2")}, widened_regs={"vd"}),
)
fvw_config = InstructionTypeConfig(
    instruction_class=["vector_fp"],
    required_params={"vd", "vs2"},
    vector_data=VectorTypeConfig(overlap_constraints={("vd", "vs2_top")}, widened_regs={"vs2"}),
)


@add_instruction_formatter("FVV", fvv_config)
def format_fvv_type(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.csr_frm_val is not None, (
        "All Vector-FP instructions use the dyn rounding mode, so params.csr_frm_val MUST be provided"
    )

    setup, test, check = format_vv_like_type(instr_str, test_data, params, "FVV")
    handle_vector_fp(setup, check, params.csr_frm_val, test_data)

    return setup, test, check


@add_instruction_formatter("FWV", fwv_config)
def format_fwv_type(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.csr_frm_val is not None, (
        "All Vector-FP instructions use the dyn rounding mode, so params.csr_frm_val MUST be provided"
    )

    setup, test, check = format_vv_like_type(instr_str, test_data, params, "FWV", widened_regs={"vd"})
    handle_vector_fp(setup, check, params.csr_frm_val, test_data)

    return setup, test, check


@add_instruction_formatter("FVW", fvw_config)
def format_fvw_type(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.csr_frm_val is not None, (
        "All Vector-FP instructions use the dyn rounding mode, so params.csr_frm_val MUST be provided"
    )

    setup, test, check = format_vv_like_type(instr_str, test_data, params, "FVW", widened_regs={"vs2"})
    handle_vector_fp(setup, check, params.csr_frm_val, test_data)

    return setup, test, check
