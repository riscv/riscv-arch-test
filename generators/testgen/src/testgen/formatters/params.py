##################################
# formatters/params.py
#
# Random parameter generation for instructions.
# jcarlin@hmc.edu Jan 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""
Random parameter generation for instructions.

This module uses metadata declared in instruction formatters to automatically
generate the correct parameters for each instruction type.

When you add a new instruction formatter in formatters/types/, declare its
requirements using the decorator parameters:

    @add_instruction_formatter("I", InstructionTypeConfig(
        required_params={"rd", "rs1", "rs1val", "immval"},
        imm_bits=12,
        imm_signed=True
    ))
    def format_i_type(instr_name, test_data, params):
        ...

The InstructionTypeConfig supports:
  - required_params: Set of parameter names needed
  - reg_range: Range of registers to use (e.g., range(8, 16) for compressed)
  - imm_bits: Number of bits for immediate values
  - imm_range: Explicit (min, max) range for immediates
  - imm_signed: Whether immediate is signed
  - imm_nonzero: Whether immediate must be nonzero
"""

from typing import Any

from testgen.data.params import InstructionParams
from testgen.data.random import random_int, random_range
from testgen.data.state import TestData
from testgen.formatters.registry import get_instr_type_config


def generate_random_params(
    test_data: TestData,
    instr_type: str,
    exclude_regs: list[int] | None = None,
    **fixed_params: Any,  # noqa: ANN401
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
    pair_regs = instr_type_config.pair_regs or set()  # Registers that need pairs

    # Determine the register range to use (extracted from formatters)
    reg_range_raw = instr_type_config.reg_range if instr_type_config.reg_range is not None else range(32)
    reg_range = list(reg_range_raw) if not isinstance(reg_range_raw, list) else reg_range_raw
    if exclude_regs is None:
        exclude_regs = []

    # Fill in missing integer register parameters (only if required)
    # Use get_register_pair for registers that need pairs
    if "rd" in required_params:
        if params.rd is None:
            if "rd" in pair_regs:
                params.rd = test_data.int_regs.get_register_pair(exclude_regs=exclude_regs, reg_range=reg_range)
            else:
                params.rd = test_data.int_regs.get_register(exclude_regs=exclude_regs, reg_range=reg_range)
        # Set the pair flag based on instruction type, regardless of whether the register was provided
        if "rd" in pair_regs:
            params.rd_is_pair = True

    if "rdval" in required_params and params.rdval is None:
        params.rdval = random_int(bits=test_data.xlen)

    if "rs1" in required_params:
        if params.rs1 is None:
            if "rs1" in pair_regs:
                params.rs1 = test_data.int_regs.get_register_pair(exclude_regs=exclude_regs, reg_range=reg_range)
            else:
                params.rs1 = test_data.int_regs.get_register(exclude_regs=exclude_regs, reg_range=reg_range)
        # Set the pair flag based on instruction type, regardless of whether the register was provided
        if "rs1" in pair_regs:
            params.rs1_is_pair = True

    if "rs1val" in required_params and params.rs1val is None:
        params.rs1val = random_int(bits=test_data.xlen)

    if "rs2" in required_params:
        if params.rs2 is None:
            if "rs2" in pair_regs:
                params.rs2 = test_data.int_regs.get_register_pair(exclude_regs=exclude_regs, reg_range=reg_range)
            else:
                params.rs2 = test_data.int_regs.get_register(exclude_regs=exclude_regs, reg_range=reg_range)
        # Set the pair flag based on instruction type, regardless of whether the register was provided
        if "rs2" in pair_regs:
            params.rs2_is_pair = True

    if "rs2val" in required_params and params.rs2val is None:
        params.rs2val = random_int(bits=test_data.xlen)

    if "rs3" in required_params:
        if params.rs3 is None:
            if "rs3" in pair_regs:
                params.rs3 = test_data.int_regs.get_register_pair(exclude_regs=exclude_regs, reg_range=reg_range)
            else:
                params.rs3 = test_data.int_regs.get_register(exclude_regs=exclude_regs, reg_range=reg_range)
        # Set the pair flag based on instruction type, regardless of whether the register was provided
        if "rs3" in pair_regs:
            params.rs3_is_pair = True

    if "rs3val" in required_params and params.rs3val is None:
        params.rs3val = random_int(bits=test_data.xlen)

    if "temp_reg" in required_params and params.temp_reg is None:
        params.temp_reg = test_data.int_regs.get_register(exclude_regs=[*exclude_regs, 0, 2], reg_range=reg_range)

    if "temp_val" in required_params and params.temp_val is None:
        params.temp_val = random_int(bits=test_data.xlen)

    # Fill in missing floating-point register parameters (only if required)
    if "fd" in required_params and params.fd is None:
        params.fd = test_data.float_regs.get_register(exclude_regs=exclude_regs, reg_range=reg_range)

    if "fdval" in required_params and params.fdval is None:
        params.fdval = random_int(bits=test_data.flen)

    if "fs1" in required_params and params.fs1 is None:
        params.fs1 = test_data.float_regs.get_register(exclude_regs=exclude_regs, reg_range=reg_range)

    if "fs1val" in required_params and params.fs1val is None:
        params.fs1val = random_int(bits=test_data.flen)

    if "fs2" in required_params and params.fs2 is None:
        params.fs2 = test_data.float_regs.get_register(exclude_regs=exclude_regs, reg_range=reg_range)

    if "fs2val" in required_params and params.fs2val is None:
        params.fs2val = random_int(bits=test_data.flen)

    if "fs3" in required_params and params.fs3 is None:
        params.fs3 = test_data.float_regs.get_register(exclude_regs=exclude_regs, reg_range=reg_range)

    if "fs3val" in required_params and params.fs3val is None:
        params.fs3val = random_int(bits=test_data.flen)

    if "temp_freg" in required_params and params.temp_freg is None:
        params.temp_freg = test_data.float_regs.get_register(reg_range=reg_range)

    if "temp_fval" in required_params and params.temp_fval is None:
        params.temp_fval = random_int(bits=test_data.flen)

    # Fill in missing immediate parameters (only if required)
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
