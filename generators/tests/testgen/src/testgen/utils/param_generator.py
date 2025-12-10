##################################
# param_generator.py
#
# jcarlin@hmc.edu 11 October 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""
Random parameter generation for instructions.

This module uses metadata declared in instruction formatters to automatically
generate the correct parameters for each instruction type.

When you add a new instruction formatter in instruction_formatters/, declare its
requirements using the decorator parameters:

    @add_instruction_formatter("I",
                               required_params={"rd", "rs1", "rs1val", "immval"},
                               imm_bits=12,
                               imm_signed=True)
    def format_i_type(instr_name, test_data, params):
        ...

The decorator supports:
  - required_params: Set of parameter names needed
  - compressed_regs: Whether to use x8-x15 (True) or x0-x31 (False)
  - imm_bits: Number of bits for immediate values
  - imm_signed: Whether immediate is signed
"""

from typing import Any

from testgen.data.params import InstructionParams
from testgen.data.test_data import TestData
from testgen.instruction_formatters import get_instr_type_config
from testgen.utils.random_values import random_int, random_range


def generate_random_params(
    test_data: TestData,
    instr_type: str,
    exclude_regs: list[int] | None = None,
    **fixed_params: Any,  # noqa: ANN401 (allow Any type for flexible fixed_params)
) -> InstructionParams:
    """
    Generate random parameters for an instruction.

    This function randomly fills in any missing parameters needed for the instruction type.
    Explicitly provided parameters are preserved.

    Args:
        test_data: Test data context (xlen, register allocators, etc.)
        instr_type: Instruction type (e.g., 'R', 'I', 'L') to determine needed parameters
        exclude_regs: List of registers to exclude from selection (e.g., [0] to exclude x0)
        **fixed_params: Fixed parameter values (e.g., rd=5, rs1val=0x100)

    Returns:
        InstructionParams with all necessary fields filled in

    Example:
        >>> params = generate_random_params(test_data, 'R', rd=5, rs1val=0x100)
        >>> # rd=5 and rs1val=0x100 are fixed, others are random
    """
    params = InstructionParams(**fixed_params)

    # Get the required parameters for this instruction type (extracted from formatters)
    instr_type_config = get_instr_type_config(instr_type)
    required_params = instr_type_config.required_params
    if required_params is None:
        raise ValueError(
            f"Unknown params for instruction type '{instr_type}'. Please add it to the instruction formatter decorator."
        )

    # Determine the register range to use (extracted from formatters)
    reg_range_raw = instr_type_config.reg_range if instr_type_config.reg_range is not None else range(0, 32)
    reg_range = list(reg_range_raw) if not isinstance(reg_range_raw, list) else reg_range_raw
    if exclude_regs is None:
        exclude_regs = []

    # Fill in missing integer register parameters (only if required)
    if "rd" in required_params and params.rd is None:
        params.rd = test_data.int_regs.get_register(exclude_regs=exclude_regs, reg_range=reg_range)

    if "rdval" in required_params and params.rdval is None:
        params.rdval = random_int(bits=test_data.xlen)

    if "rs1" in required_params and params.rs1 is None:
        params.rs1 = test_data.int_regs.get_register(exclude_regs=exclude_regs, reg_range=reg_range)

    if "rs1val" in required_params and params.rs1val is None:
        params.rs1val = random_int(bits=test_data.xlen)

    if "rs2" in required_params and params.rs2 is None:
        params.rs2 = test_data.int_regs.get_register(exclude_regs=exclude_regs, reg_range=reg_range)

    if "rs2val" in required_params and params.rs2val is None:
        params.rs2val = random_int(bits=test_data.xlen)

    if "temp_reg" in required_params and params.temp_reg is None:
        params.temp_reg = test_data.int_regs.get_register(exclude_regs=[*exclude_regs, 2], reg_range=reg_range)

    if "temp_val" in required_params and params.temp_val is None:
        params.temp_val = random_int(bits=test_data.xlen)

    if "immval" in required_params and params.immval is None:
        # Get immediate metadata from formatter config
        imm_bits = instr_type_config.imm_bits
        imm_range = instr_type_config.imm_range
        imm_signed = instr_type_config.imm_signed
        imm_nonzero = instr_type_config.imm_nonzero

        # Resolve xlen/flen expressions in imm_bits
        if isinstance(imm_bits, str):
            if imm_bits == "xlen":
                imm_bits = test_data.xlen
            elif imm_bits == "flen":
                imm_bits = test_data.flen
            elif imm_bits == "xlen_log2":
                imm_bits = test_data.xlen_log2
            elif imm_bits == "flen_log2":
                imm_bits = test_data.flen_log2
            else:
                raise ValueError(
                    f"Unknown imm_bits expression: {imm_bits}. Expected 'xlen', 'flen', 'xlen_log2', 'flen_log2', or an integer."
                )

        # Generate immediate value
        if imm_range is not None:
            # Explicit range specified (e.g., IR type with 0-10 range)
            min_val, max_val = imm_range
            params.immval = random_range(min_val, max_val, nonzero=imm_nonzero)
        elif imm_bits is not None:
            # Regular immediate: generate at actual bit width
            params.immval = random_int(imm_bits, signed=imm_signed, nonzero=imm_nonzero)
        else:
            raise ValueError(
                f"Instruction type '{instr_type}' requires immval but has no imm_bits or imm_range configured"
            )

    return params
