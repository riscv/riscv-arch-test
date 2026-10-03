##################################
# fvvv_type.py
#
# rwolk@hmc.edu August 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.vector_helpers import handle_vector_fp
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, VectorTypeConfig, add_instruction_formatter
from testgen.formatters.types.vvv_type import format_vvv_like_type

fvvv_config = InstructionTypeConfig(
    instruction_class=["vector_fp"], required_params={"vd", "vs1", "vs2"}, vector_data=VectorTypeConfig()
)
fwvv_config = InstructionTypeConfig(
    instruction_class=["vector_fp"],
    required_params={"vd", "vs1", "vs2"},
    vector_data=VectorTypeConfig(overlap_constraints={("vd_bottom", "vs1"), ("vd_bottom", "vs2")}, widened_regs={"vd"}),
)
fwwv_config = InstructionTypeConfig(
    instruction_class=["vector_fp"],
    required_params={"vd", "vs1", "vs2"},
    vector_data=VectorTypeConfig(
        overlap_constraints={("vd_bottom", "vs1"), ("vs1", "vs2")},
        widened_regs={"vd", "vs2"},
    ),
)
fvvv_acc_config = InstructionTypeConfig(
    instruction_class=["vector_fp"], required_params={"vd", "vs1", "vs2"}, vector_data=VectorTypeConfig()
)
fwvv_acc_config = InstructionTypeConfig(
    instruction_class=["vector_fp"],
    required_params={"vd", "vs1", "vs2"},
    vector_data=VectorTypeConfig(overlap_constraints={("vd", "vs2"), ("vd", "vs1")}, widened_regs={"vd"}),
)


@add_instruction_formatter("FVVV", fvvv_config)
def format_vvv(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.csr_frm_val is not None, (
        "All Vector-FP instructions use the dyn rounding mode, so params.csr_frm_val MUST be provided"
    )

    setup, test, check = format_vvv_like_type(instr_str, test_data, params, "FVVV")
    handle_vector_fp(setup, check, params.csr_frm_val, test_data)

    return setup, test, check


@add_instruction_formatter("FWWV", fwwv_config)
def format_wwv(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.csr_frm_val is not None, (
        "All Vector-FP instructions use the dyn rounding mode, so params.csr_frm_val MUST be provided"
    )

    setup, test, check = format_vvv_like_type(instr_str, test_data, params, "FWWV", widen={"vd", "vs2"})
    handle_vector_fp(setup, check, params.csr_frm_val, test_data)

    return setup, test, check


@add_instruction_formatter("FWVV", fwvv_config)
def format_wvv(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.csr_frm_val is not None, (
        "All Vector-FP instructions use the dyn rounding mode, so params.csr_frm_val MUST be provided"
    )

    setup, test, check = format_vvv_like_type(instr_str, test_data, params, "FWVV", widen={"vd"})
    handle_vector_fp(setup, check, params.csr_frm_val, test_data)

    return setup, test, check


@add_instruction_formatter("FVVV_ACC", fvvv_acc_config)
def format_vvv_acc(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.csr_frm_val is not None, (
        "All Vector-FP instructions use the dyn rounding mode, so params.csr_frm_val MUST be provided"
    )

    setup, test, check = format_vvv_like_type(instr_str, test_data, params, "FVVV_ACC")
    # Overwrite the test, as otherwise it generates in the wrong order
    if params.maskval:
        test = [f"{instr_str} v{params.vd}, v{params.vs1}, v{params.vs2}, v0.t"]
    else:
        test = [f"{instr_str} v{params.vd}, v{params.vs1}, v{params.vs2}"]

    handle_vector_fp(setup, check, params.csr_frm_val, test_data)

    return setup, test, check


@add_instruction_formatter("FWVV_ACC", fwvv_acc_config)
def format_wvv_acc(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.csr_frm_val is not None, (
        "All Vector-FP instructions use the dyn rounding mode, so params.csr_frm_val MUST be provided"
    )

    setup, test, check = format_vvv_like_type(instr_str, test_data, params, "FWVV_ACC", widen={"vd"})
    # Overwrite the test, as otherwise it generates in the wrong order
    if params.maskval:
        test = [f"{instr_str} v{params.vd}, v{params.vs1}, v{params.vs2}, v0.t"]
    else:
        test = [f"{instr_str} v{params.vd}, v{params.vs1}, v{params.vs2}"]

    handle_vector_fp(setup, check, params.csr_frm_val, test_data)

    return setup, test, check
