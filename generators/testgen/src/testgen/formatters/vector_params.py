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
import re
from typing import Any, Literal

from testgen.data.params import InstructionParams
from testgen.data.random import random_int
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, get_instr_type_config


@dataclasses.dataclass
class InstructionInfo:
    segments: int
    load_store_eew: int | None
    index_eew: int | None
    vext_multiplier: float | None
    widen_vs2: bool
    widen_vd: bool

    def get_size_multiplier(self, register: str, sew: int) -> int | float:
        if self.vext_multiplier and register == "vs2":
            return self.vext_multiplier
        elif self.index_eew and register == "vs2":
            return self.index_eew / sew
        elif self.load_store_eew and register in ["vs3", "vd"]:  # Either one or the other exists for these instructions
            return self.load_store_eew / sew
        elif self.widen_vd and register == "vd" or self.widen_vs2 and register == "vs2":
            return 2
        return 1


def extract_instruction_info(instruction: str, instruction_type: str) -> InstructionInfo:
    # Extract Segments
    # Generally, a segmented load/store looks like: vl___seg<nf>__.v or vl<nf>re_.v
    segmented_ls_match = re.search(r"v[ls]\w*seg(\d+)\w*.v", instruction)
    segments = int(segmented_ls_match.group(1)) if segmented_ls_match is not None else 1
    if segments < 1 or segments > 8:
        raise ValueError(f"Invalid Number of Segments in Instruction: {instruction}, Parsed {segments} segments")

    # Load/Store EEW: Ends with e<eew>.v, e<eew>ff.v,
    load_store_eew_match = re.search(r"v[ls]\w*e(\d+)(?:ff)?.v", instruction)
    load_store_eew = int(load_store_eew_match.group(1)) if load_store_eew_match is not None else None
    if load_store_eew not in [8, 16, 32, 64, None]:
        raise ValueError(f"Invalid EEW Parsed from Instruction: {instruction}, Parsed {load_store_eew} EEW")

    # index EEW: Ends with ei<eew>.v (also matches vrgatherei16.v)
    index_eew_match = re.search(r"v\w*ei(\d+).v", instruction)
    index_eew = int(index_eew_match.group(1)) if index_eew_match is not None else None
    if index_eew not in [8, 16, 32, 64, None]:
        raise ValueError(f"Invalid Index EEW Parsed from Instruction: {instruction}, Parsed {index_eew} EEW")

    vext_multiplier = 1 / int(instruction[-1]) if instruction_type == "VEXT" else None

    vd_widen = vs2_widen = False
    if instruction_type in ["WVWSR", "FWVWSR", "WWV", "WWX", "FWWF", "VWV", "VWX", "VWI"]:
        vs2_widen = True
    if instruction_type in ["WVWSR", "FWVWSR", "WVV", "WVX", "WWV", "WVS", "FWVF", "FWWF", "FWCVT"]:
        vd_widen = True

    return InstructionInfo(
        segments=segments,
        load_store_eew=load_store_eew,
        index_eew=index_eew,
        vext_multiplier=vext_multiplier,
        widen_vd=vd_widen,
        widen_vs2=vs2_widen,
    )


def randomize_register(
    register_name: str,
    test_data: TestData,
    instr_type_config: InstructionTypeConfig,
    lmul: float,
    info: InstructionInfo,
    preset: int | None = None,
) -> int:
    if register_name.startswith("v"):
        sew = test_data.config.sew
        assert sew is not None, "SEW must be set when randomizing vector registers"

        emul = lmul * info.get_size_multiplier(register_name, sew)

        emul = int(emul)
        if (
            (instr_type_config.vector_mask_regs is not None and register_name in instr_type_config.vector_mask_regs)
            or (
                instr_type_config.vector_scalar_regs is not None
                and register_name in instr_type_config.vector_scalar_regs
            )
            or emul < 1
        ):
            emul = 1

        # If the assignment was already set, validate it
        if preset is not None:
            if preset + emul * info.segments > test_data.vec_regs.reg_count:
                raise ValueError(
                    f"Preset {register_name}=v{preset} with NF={info.segments} "
                    f"EMUL_field={emul} overflows past v{test_data.vec_regs.reg_count - 1}"
                )

            if emul > 1 and preset % emul != 0:
                raise ValueError(f"preset {register_name}=v{preset} not aligned to EMUL={emul}")
            return preset

        # Otherwise, generate a register aligned to emul and lmul
        alignment = max(emul, int(lmul)) if int(lmul) >= 1 else emul

        # We can't take the registers from the register file yet because we want to randomly generate valid overlaps
        return random.choice(list(test_data.vec_regs.free_registers(alignment)))

    if preset is not None:
        return preset  # No need to validate r and f registers

    if register_name.startswith("r"):
        return test_data.int_regs.get_register(exclude_regs=[0])
    elif register_name.startswith("f"):
        return test_data.float_regs.get_register()

    raise ValueError(f"Invalid Register Name Given: {register_name}")


def random_vector(suite: Literal["base", "length"], test_data: TestData) -> list[int]:
    assert test_data.config.sew is not None, "SEW Must be Set"

    element_count = 1 if suite == "base" else test_data.config.vlen_max // test_data.config.sew
    elements = [random_int(test_data.config.sew) for _ in range(element_count)]
    return elements


def randomize_registers(
    preset_params: InstructionParams,
    test_data: TestData,
    instr_type_config: InstructionTypeConfig,
    info: InstructionInfo,
    lmul: float,
) -> InstructionParams:
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
                new_params.rs2val = random.randint(-2, 2 + 1) * int(info.load_store_eew / 8)
            else:
                new_params.rs2val = random_int(test_data.config.xlen)
    if "rs1" in registers:
        new_params.rs1 = randomize_register("rs1", test_data, instr_type_config, lmul, info, new_params.rs1)
        if new_params.rs1val_pointer is not None and instr_type_config.vector_role in ["load", "store"]:
            new_params.rs1val_pointer = "vector_ls_random_base"

            assert test_data.config.sew is not None, "SEW must be Set For Vector Register Randomization"
            test_data.register_vector_data(
                "vector_ls_random_base",
                test_data.config.sew,
                random_elements=test_data.config.vlen_max // test_data.config.sew,
            )
        else:
            new_params.rs1val = random_int(test_data.config.xlen)
    if "rd" in registers:
        new_params.rd = randomize_register("rd", test_data, instr_type_config, lmul, info, new_params.rd)

    if "fs1" in registers:
        new_params.fs1 = randomize_register("fs1", test_data, instr_type_config, lmul, info, new_params.fs2)
        if new_params.fs1val is not None:
            new_params.fs1val = random_int(test_data.config.flen)
    if "fd" in registers:
        new_params.fd = randomize_register("fd", test_data, instr_type_config, lmul, info, new_params.fd)

    return new_params


def generate_random_vector_params(
    test_data: TestData,
    instruction: str,
    instr_type: str,
    lmul: float,
    additional_no_overlap: set[tuple[str, str]] | None = None,
    masked: bool = False,
    suite: Literal["length", "base"] = "base",
    **fixed_params: Any,  # noqa: ANN401
) -> InstructionParams:
    test_count = test_data.test_count

    sew = test_data.config.sew
    assert sew is not None, "SEW must be set for Vector Instructions"

    preset_params = InstructionParams(**fixed_params)

    instr_type_config = get_instr_type_config(instr_type)
    no_overlap: set[tuple[str, str]] = set()
    if instr_type_config.vector_overlap_constraints is not None:
        no_overlap |= instr_type_config.vector_overlap_constraints
    if instr_type_config.vector_masked_constraints is not None and masked:
        no_overlap |= instr_type_config.vector_masked_constraints
    if additional_no_overlap is not None:
        no_overlap |= additional_no_overlap

    mask_vector_regs = instr_type_config.vector_mask_regs
    if mask_vector_regs is None:
        mask_vector_regs = set()

    scalar_vector_regs = instr_type_config.vector_scalar_regs
    if scalar_vector_regs is None:
        scalar_vector_regs = set()

    info = extract_instruction_info(instruction, instr_type)

    if instr_type in "whole_register_ls":  # PLACEHOLDER FOR NOW!!! FIXME
        # whole register load stores ignore lmul and instead use nfields as emul
        lmul = max(1, info.segments)

    ####################################################################################
    # check and resolve and register overlap
    ####################################################################################

    register_overlap = True
    randomization_count = 0
    params = InstructionParams()
    preset_params_dict = dataclasses.asdict(preset_params)

    while register_overlap:
        params = randomize_registers(preset_params, test_data, instr_type_config, info, lmul)

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
                    if register == "v0":
                        registers_occupied.append(0)
                    else:
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

                        smallest_emul = lmul
                        if info.vext_multiplier is not None:
                            smallest_emul = min(smallest_emul, lmul * info.vext_multiplier)
                        if info.load_store_eew is not None:
                            smallest_emul = min(smallest_emul, lmul * info.load_store_eew)
                        if info.index_eew is not None:
                            smallest_emul = min(smallest_emul, lmul * info.index_eew)
                        smallest_emul = int(smallest_emul)

                        # segment instructions take up consecutive registers even when lmul < 1
                        emul = math.ceil(info.get_size_multiplier(register, sew) * lmul) * info.segments

                        if (
                            start_no_overlap
                            or register in scalar_vector_regs
                            or register in mask_vector_regs
                            or emul < 1
                        ):
                            start_no_register_overlap = 0
                            end_register_no_overlap = 1
                        else:
                            start_no_register_overlap = smallest_emul if top_no_overlap and smallest_emul >= 1 else 0
                            # need to include nfields (there is no bottom or top overlap allowed)
                            end_register_no_overlap = (
                                emul - smallest_emul if bottom_no_overlap and smallest_emul >= 1 else emul
                            )

                        if params_dict[register] is None:
                            continue

                        for i in range(start_no_register_overlap, end_register_no_overlap):
                            registers_occupied.append(params_dict[register] + i)

            if len(registers_occupied) != len(set(registers_occupied)):  # checks for duplicates
                register_overlap = True

        if register_overlap:
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
    if test_count is not None and suite is not None:
        element_count = 1 if suite == "base" else test_data.config.vlen_max // sew
        if params.vs3_val_pointer is None:
            params.vs3_val_pointer = f"vs3_random_{suite}_{test_count:03d}"
            test_data.register_vector_data(
                f"vs3_random_{suite}_{test_count:03d}",
                int(sew * info.get_size_multiplier("vs3", sew)),
                random_elements=element_count,
            )
        if params.vd_val_pointer is None:
            params.vd_val_pointer = f"vd_random_{suite}_{test_count:03d}"
            test_data.register_vector_data(
                f"vd_random_{suite}_{test_count:03d}",
                int(sew * info.get_size_multiplier("vd", sew)),
                random_elements=element_count,
            )
        if params.vs1_val_pointer is None:
            params.vs1_val_pointer = f"vs1_random_{suite}_{test_count:03d}"
            test_data.register_vector_data(
                f"vs1_random_{suite}_{test_count:03d}",
                int(sew * info.get_size_multiplier("vs1", sew)),
                random_elements=element_count,
            )
        if params.vs2_val_pointer is None:
            params.vs2_val_pointer = f"vs2_random_{suite}_{test_count:03d}"
            test_data.register_vector_data(
                f"vs2_random_{suite}_{test_count:03d}",
                int(sew * info.get_size_multiplier("vs2", sew)),
                random_elements=element_count,
            )

        # I'm not sure if this is necessary: We will see in VLS (this is set in randomize_register)
        # if params.rs1val_pointer is None:
        #     params.rs1val_pointer = f"vd_load_random_{suite}_{test_count:03d}"

    # immediate handling
    if params.immval is None and instr_type_config.imm_range:
        params.immval = random.randint(*instr_type_config.imm_range)

    params.temp_reg = test_data.int_regs.get_register()
    params.sew = sew
    params.lmul = lmul
    params.vector_suite = suite

    return params
