##################################
# formatters/vector_params.py
#
# Random parameter generation for vector instructions.
# rwolk@hmc.edu June 2026
#
# Refactored From vector_testgen_common.py: James Kaden Cassidy kacassidy@hmc.edu 25 Jun 2025
#
# SPDX-License-Identifier: Apache-2.0
##################################

from __future__ import annotations

import dataclasses
import math
import random
from typing import Any, Literal

from testgen.constants import VLEN_MAX
from testgen.coverpoints.vector.vector_helpers import InstructionInfo, extract_instruction_info
from testgen.data.params import InstructionParams
from testgen.data.random import random_int, random_range
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, VectorTypeConfig, get_instr_type_config


def get_register_emul(
    register_name: str, lmul: float, sew: int, vector_type_config: VectorTypeConfig, info: InstructionInfo
) -> int | float:
    """
    Helper function to calculate the emul of a specific register, given the register_name, lmul, sew,
    type info and instruction info
    """

    emul = lmul * info.get_size_multiplier(register_name, sew)

    if (
        (vector_type_config.mask_regs is not None and register_name in vector_type_config.mask_regs)
        or (vector_type_config.scalar_regs is not None and register_name in vector_type_config.scalar_regs)
        or emul < 1
    ):
        emul = 1

    return emul


def randomize_register(
    register_name: str,
    test_data: TestData,
    instr_type_config: InstructionTypeConfig,
    lmul: float,
    info: InstructionInfo,
    preset: int | None = None,
) -> int:
    """
    Sets a register to a random number (aligned to its emul), or validates a preset vector register.

    Args:
        register_name: Name of the register (vs2, rs1, etc.)
        test_data: TestData object. Gives information like sew, and access to the register files.
        instr_type_config: Type config used to derive emul
        lmul: lmul value used to derive emul
        info: InstructionInfo object used to derive emul

    Optional Args:
        preset: If a preset was passed for this register to generate_random_vector_params, it is validated here.
    """

    if register_name.startswith("v"):
        sew = test_data.config.sew
        assert sew is not None, "SEW must be set when randomizing vector registers"

        segments = info.segments
        if (
            instr_type_config.instruction_class
            and "indexed" in instr_type_config.instruction_class
            and register_name == "vs2"
        ):
            segments = 1

        assert instr_type_config.vector_data is not None, "Vector Data must be provided for vector instruction types"
        emul = int(get_register_emul(register_name, lmul, sew, instr_type_config.vector_data, info))

        # If the assignment was already set, validate it
        if preset is not None:
            if preset + emul * segments > test_data.vec_regs.reg_count:
                raise ValueError(
                    f"Preset {register_name}=v{preset} with NF={segments} "
                    f"EMUL_field={emul} overflows past v{test_data.vec_regs.reg_count - 1}"
                )

            if emul > 1 and preset % emul != 0:
                raise ValueError(f"preset {register_name}=v{preset} not aligned to EMUL={emul}")
            return preset

        # Otherwise, generate a register aligned to emul and lmul
        alignment = max(emul, int(lmul)) if int(lmul) >= 1 else emul

        # We can't take the registers from the register file yet because we want to randomly generate valid overlaps
        return random.choice(list(test_data.vec_regs.free_registers(alignment, segments)))

    if preset is not None:
        return preset  # No need to validate r and f registers

    if register_name.startswith("r"):
        return test_data.int_regs.get_register(exclude_regs=[0])
    elif register_name.startswith("f"):
        return test_data.float_regs.get_register()

    raise ValueError(f"Invalid Register Name Given: {register_name}")


def randomize_registers(
    preset_params: InstructionParams,
    test_data: TestData,
    instr_type_config: InstructionTypeConfig,
    info: InstructionInfo,
    lmul: float,
) -> InstructionParams:
    """
    Randomize all registers used in an operation, and give the non-vector register random values.

    Args:
        preset_params: InstructionParams object containing the values that must be in the final params object.
        test_data: TestData object needed for register files
        instr_type_config: InstructionTypeConfig objecting giving information like the required registers
        info: InstructionInfo object that will aid emul calculation when picking a random registers
        lmul: lmul value for the test. Passed to ensure proper alignment of all registers
    """
    new_params = dataclasses.replace(preset_params)  # Copies preset_params

    if instr_type_config.required_params is None:
        return new_params

    registers = {"vs1", "vs2", "vs3", "vd", "rs1", "rs2", "rd", "fs1", "fd"}
    registers &= instr_type_config.required_params

    if "vs3" in registers:
        new_params.vs3 = randomize_register("vs3", test_data, instr_type_config, lmul, info, new_params.vs3)
    if "vs2" in registers:
        new_params.vs2 = randomize_register("vs2", test_data, instr_type_config, lmul, info, new_params.vs2)
    if "vs1" in registers:
        new_params.vs1 = randomize_register("vs1", test_data, instr_type_config, lmul, info, new_params.vs1)
    if "vd" in registers:
        new_params.vd = randomize_register("vd", test_data, instr_type_config, lmul, info, new_params.vd)

    if "rs2" in registers:
        new_params.rs2 = randomize_register("rs2", test_data, instr_type_config, lmul, info, new_params.rs2)
        if new_params.rs2val is not None:
            if info.load_store_eew is not None:
                new_params.rs2val = random_range(-2, 2 + 1) * int(info.load_store_eew / 8)
            else:
                new_params.rs2val = random_int(test_data.config.xlen)
    if "rs1" in registers:
        new_params.rs1 = randomize_register("rs1", test_data, instr_type_config, lmul, info, new_params.rs1)
        if new_params.rs1val_pointer is not None and (
            "load" in instr_type_config.instruction_class or "store" in instr_type_config.instruction_class
        ):
            new_params.rs1val_pointer = "vector_ls_random_base"

            assert test_data.config.sew is not None, "SEW must be Set For Vector Register Randomization"
            test_data.register_vector_data(
                "vector_ls_random_base",
                test_data.config.sew,
                random_elements=VLEN_MAX // test_data.config.sew,
            )
        elif new_params.rs1val is None:
            new_params.rs1val = random_int(test_data.config.xlen)
    if "rd" in registers:
        new_params.rd = randomize_register("rd", test_data, instr_type_config, lmul, info, new_params.rd)

    if "fs1" in registers:
        new_params.fs1 = randomize_register("fs1", test_data, instr_type_config, lmul, info, new_params.fs1)
        if new_params.fs1val is not None:
            new_params.fs1val = random_int(test_data.config.flen)
    if "fd" in registers:
        new_params.fd = randomize_register("fd", test_data, instr_type_config, lmul, info, new_params.fd)

    return new_params


def get_overlap_constraints(
    info: InstructionInfo, instr_type_config: InstructionTypeConfig, masked: bool, sew: int
) -> set[tuple[str, str]]:
    """
    This helper function extracts the overlap constraints from InstructionInfo and an InstructionTypeConfig pair, given
    whether or not the operation is masked and what the SEW is.
    """
    no_overlap: set[tuple[str, str]] = set()

    # Normal constrains
    assert instr_type_config.vector_data is not None, "vector_data must be provided for vector instruction types"
    no_overlap |= instr_type_config.vector_data.overlap_constraints

    # Specific Masked Constraints
    if masked:
        # Either use the overrides, or assume that there is no overlap with v0 in the masked case
        if instr_type_config.vector_data.masked_constraints is not None:
            no_overlap |= instr_type_config.vector_data.masked_constraints
        elif instr_type_config.required_params is not None:
            # Unless otherwise specified, do not overlap v0
            for reg in instr_type_config.required_params:
                if reg.startswith("v"):
                    no_overlap.add(("v0", reg))

    if info.index_eew is not None and info.index_eew != sew and instr_type_config.required_params:
        # vs2 is the index register
        # Any source overlap with this index register is illegal
        for source_reg in ["vs1", "vs3"]:
            if source_reg in instr_type_config.required_params:
                no_overlap.add(("vs2", source_reg))

        if ("vd", "vs2") not in no_overlap and ("vs2", "vd") not in no_overlap:
            # If we don't already have an overlap, apply the following rules (b and c)
            # V-spec §5.2 register-overlap rules between dest and source register groups:
            #   (a) EEW_dest == EEW_src                -> any overlap legal
            #   (b) EEW_dest <  EEW_src                -> overlap only at LOWEST part of source group
            #   (c) EEW_dest >  EEW_src, EMUL_src >= 1 -> overlap only at HIGHEST part of dest group
            if info.index_eew > sew:
                no_overlap.add(("vd", "vs2_top"))
            else:
                no_overlap.add(("vd_bottom", "vs2"))

    return no_overlap


def get_occupied_v_registers(
    register: str, info: InstructionInfo, lmul: float, sew: int, params_dict: dict[str, Any], single_register: bool
) -> list[int]:
    """
    Given a register of the form v0, vd, vd_suffix, vsX, or vsX_suffix, determine the registers that it cannot overlap with.

    Args:
        register: A register of the form v0, vd, vd_suffix, vsX, or vsX_suffix
        info: InstructionInfo object for the instruction with overlap constraints
        lmul: LMUL of the instruction. With the InstructionInfo object, we determine the emul for the specific register
        sew: SEW of the instruction. Aids EMUL calculation
        params_dict: InstructionParams object as a dict. Used to easily find the assigned register number.
        single_register: Boolean determining if the instruction takes up only one register.
    """
    if register == "v0":
        return [0]

    top_no_overlap = False
    if register[-4:] == "_top":  # if specifying no overlap with the top of a register
        top_no_overlap = True  # save for reserved section below
        register = register[:-4]  # remove "_top" from register name

    bottom_no_overlap = False
    if register[-7:] == "_bottom":  # if specifying no overlap with the bottom of a register
        bottom_no_overlap = True  # save for reserved section below
        register = register[:-7]  # remove "_bottom" from register name

    start_no_overlap = False
    if register[-6:] == "_start":
        # if specifying no overlap with the initial register of a group (single register v)
        start_no_overlap = True  # save for reserved section below
        register = register[:-6]  # remove "_start" from register name

    # We can check that the register that can't overlap is even assigned now that the suffixes have been removed
    if params_dict[register] is None:
        return []

    smallest_emul = lmul
    if info.vext_multiplier is not None:
        smallest_emul = min(smallest_emul, lmul * info.vext_multiplier)
    if info.load_store_eew is not None:
        smallest_emul = min(smallest_emul, lmul * info.load_store_eew / sew)
    if info.index_eew is not None:
        smallest_emul = min(smallest_emul, lmul * info.index_eew / sew)
    smallest_emul = int(smallest_emul)

    # segment instructions take up consecutive registers even when lmul < 1
    emul = math.ceil(info.get_size_multiplier(register, sew) * lmul) * info.segments

    if start_no_overlap or single_register or emul < 1:
        start_no_register_overlap = 0
        end_register_no_overlap = 1
    else:
        start_no_register_overlap = smallest_emul if top_no_overlap and smallest_emul >= 1 else 0
        # need to include nfields (there is no bottom or top overlap allowed)
        end_register_no_overlap = emul - smallest_emul if bottom_no_overlap and smallest_emul >= 1 else emul

    occupied = []
    for i in range(start_no_register_overlap, end_register_no_overlap):
        occupied.append(params_dict[register] + i)

    return occupied


def has_invalid_overlap(
    params: InstructionParams,
    info: InstructionInfo,
    no_overlap: set[tuple[str, str]],
    lmul: float,
    sew: int,
    scalar_vector_regs: set[str],
    mask_vector_regs: set[str],
) -> bool:
    """
    Determine if a given InstructionParams object has an invalid overlap, according to a no_overlap set.

    Args:
        params: The InstructionParams object to be tested for overlap
        info: InstructionInfo object used to aid EMUL calculations for registers
        no_overlap: Set of pairs of registers that cannot overlap
        lmul: LMUL of the test
        sew: SEW of the test
        scalar_vector_regs: Set of registers to be interpreted as single element scalar vector registers
        mask_vector_regs: Set of registers to be interpreted as one register wide vector mask registers
    """

    register_overlap = False
    params_dict = dataclasses.asdict(params)
    for no_overlap_set in no_overlap:
        register_type = no_overlap_set[0][0]  # grab either "v" "r" or "f" to get the register type
        registers_occupied = []

        for register in no_overlap_set:
            if not register_type == register[0]:
                # Ensure all registers are of the same type
                raise TypeError(f"Register type mismatch from {register_type}: '{register}'")
            elif register_type in ["r", "f"]:
                registers_occupied.append(params_dict[register])  # add register value to list to check for overlap
            elif register_type == "v":
                single_register = register in scalar_vector_regs or register in mask_vector_regs
                registers_occupied.extend(
                    get_occupied_v_registers(register, info, lmul, sew, params_dict, single_register)
                )

        if len(registers_occupied) != len(set(registers_occupied)):  # checks for duplicates
            register_overlap = True

    return register_overlap


def generate_random_vector_params(
    test_data: TestData,
    instruction: str,
    instr_type: str,
    lmul: float,
    *,
    additional_no_overlap: set[tuple[str, str]] | None = None,
    masked: bool = False,
    suite: Literal["length", "base"] = "base",
    **fixed_params: Any,  # noqa: ANN401
) -> InstructionParams:
    """
    Randomize an InstructionParams object, respecting the instruction type's overlap constraints and
    register alignment constraints.

    Args:
        test_data: TestData object containing register files and global sew
        instruction: Instruction under test, required as some EEW and EMUL information is stored in the
            name of instruction (e.g. index EEWs like in vloxei32)
        instr_type: Instruction type string that gives overlap requirements, and required registers
        lmul: The lmul that the test will be run at. Required for proper alignment

    Optional Args:
        additional_no_overlap: Set of pairs of registers that cannot overlap. Used in case where the tests
            need to be stricter than the spec, like when multiple edge values are needed at the same time.
        masked: Boolean that tells the generate whether or not to generate a mask value and to use mask constraints.
        suite: Sets whether the test is base suite or length suite. Base by default.
        fixed_params: kwargs argument that sets any default value for the resulting InstructionParams object
    """

    test_count = test_data.test_count

    sew = test_data.config.sew
    assert sew is not None, "SEW must be set for Vector Instructions"

    preset_params = InstructionParams(**fixed_params)

    instr_type_config = get_instr_type_config(instr_type)
    assert instr_type_config.vector_data is not None, (
        f"Vector Data must be provided for vector instruction type {instr_type}"
    )
    info = extract_instruction_info(instruction, instr_type)

    no_overlap = get_overlap_constraints(info, instr_type_config, masked, sew)
    if additional_no_overlap is not None:
        no_overlap |= additional_no_overlap

    mask_vector_regs = instr_type_config.vector_data.mask_regs
    if mask_vector_regs is None:
        mask_vector_regs = set()

    scalar_vector_regs = instr_type_config.vector_data.scalar_regs
    if scalar_vector_regs is None:
        scalar_vector_regs = set()

    preset_params.lmul = lmul
    # These are effective lmuls for the operation, but we still must respect the callers choice of lmul
    if instr_type in ["VLR", "VSR"]:
        # whole register load stores ignore lmul and instead use nfields as emul
        lmul = max(1, info.segments)
    elif instr_type == "VMVR":
        lmul = int(instruction[3])

    ####################################################################################
    # check and resolve and register overlap
    ####################################################################################

    invalid_overlap = True
    randomization_count = 0
    params = InstructionParams()
    preset_params_dict = dataclasses.asdict(preset_params)
    params_dict = dataclasses.asdict(params)

    while invalid_overlap:
        params = randomize_registers(preset_params, test_data, instr_type_config, info, lmul)
        params_dict = dataclasses.asdict(params)

        invalid_overlap = has_invalid_overlap(params, info, no_overlap, lmul, sew, scalar_vector_regs, mask_vector_regs)

        if invalid_overlap:
            # Return the registers that we use
            registers = {"vs1", "vs2", "vs3", "vd", "rs1", "rs2", "rd", "fs1", "fd"}
            if instr_type_config.required_params is not None:
                registers &= instr_type_config.required_params

            for register in registers:
                if params_dict[register] != preset_params_dict[register]:
                    if register.startswith("v"):
                        pass  # We haven't taketen these from the register file yet
                    elif register.startswith("r"):
                        test_data.int_regs.return_register(params_dict[register])
                    elif register.startswith("f"):
                        test_data.float_regs.return_register(params_dict[register])

        max_randomization_count = 1000
        if randomization_count >= max_randomization_count:
            raise ValueError(
                f'No Overlap constraint "{no_overlap}" cannot be met for instruction "{instruction}" with sew "{sew}" and lmul "{lmul}" after {max_randomization_count} attempts'
            )
        randomization_count = randomization_count + 1

    ####################################################################################
    # Randomize the instruction data & take vector registers from the register file
    ####################################################################################
    registers = {"vs1", "vs2", "vs3", "vd", "rs1", "rs2", "rd", "fs1", "fd"}
    if instr_type_config.required_params is not None:
        registers &= instr_type_config.required_params

    for register in registers:
        if params_dict[register] != preset_params_dict[register] and register.startswith("v"):
            segments = info.segments
            if (
                instr_type_config.instruction_class
                and "indexed" not in instr_type_config.instruction_class
                and register != "vs2"
            ):
                segments = 1

            width = math.ceil(get_register_emul(register, lmul, sew, instr_type_config.vector_data, info)) * segments
            test_data.vec_regs.allocate_operand(register, params_dict[register], width, suppress_overlap=True)

        if register.startswith("v") and params_dict[f"{register}_val_pointer"] is None:
            # Set the label
            label = f"{register}_random_{suite}_{test_count:03d}"
            setattr(params, f"{register}_val_pointer", label)  # params.register_val_pointer = label

            # Register the label
            eew = int(sew * info.get_size_multiplier(register, sew))
            element_count = 1 if suite == "base" else math.ceil(VLEN_MAX * lmul / sew)
            test_data.register_vector_data(label, eew, random_elements=element_count)

    # immediate handling
    if instr_type_config.required_params and params.immval is None and "immval" in instr_type_config.required_params:
        if instr_type_config.imm_range is not None:
            min_val, max_val = instr_type_config.imm_range
            params.immval = random_range(min_val, max_val, nonzero=instr_type_config.imm_nonzero)
        elif instr_type_config.imm_bits is not None:
            imm_bits = instr_type_config.imm_bits
            if isinstance(imm_bits, int):
                params.immval = random_int(
                    imm_bits, signed=instr_type_config.imm_signed, nonzero=instr_type_config.imm_nonzero
                )
            else:
                raise NotImplementedError("Vector random parameter generation only supports integer values of imm_bits")
        else:
            raise ValueError(
                f"Instruction type '{instr_type}' requires immval but has no imm_bits or imm_range configured"
            )

    if (
        instr_type_config.required_params is not None
        and "maskval" in instr_type_config.required_params
        and params.maskval is None
    ):
        element_count = 1 if suite == "base" else math.ceil((VLEN_MAX / sew) * lmul / sew)
        params.maskval = f"maskval_random_{suite}_{test_count:03d}"
        test_data.register_vector_data(
            f"maskval_random_{suite}_{test_count:03d}",
            sew,
            random_elements=element_count,
        )

    params.temp_reg = test_data.int_regs.get_register(exclude_regs=[0])
    params.sew = sew
    params.vector_suite = suite

    return params
