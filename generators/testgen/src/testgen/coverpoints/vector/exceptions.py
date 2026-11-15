##################################
# exceptions.py
#
# Vector exceptions coverpoints
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

import itertools
import math
from typing import Literal

from testgen.asm.helpers import write_sigupd
from testgen.asm.tsbi import tsbi_call
from testgen.asm.vector_helpers import prep_vstart
from testgen.constants import VLEN_MAX
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.coverpoints.vector.helpers import extract_coverpoint_sews
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters.registry import InstructionTypeConfig, format_instruction, get_instruction_type_config
from testgen.instructions.vector import (
    VectorInstructionInfo,
    get_base_lmul,
    get_legal_lmuls,
    parse_vector_instruction_info,
)
from testgen.instructions.vector_params import generate_random_vector_params


def get_data_label(register: str, eew: int, instr_type_config: InstructionTypeConfig, test_data: TestData) -> str:
    """Generates random data labels to be reused throughout ExceptionsV tests."""
    assert instr_type_config.vector_data is not None, "vector_data must be provided for vector instructions"
    rng = instr_type_config.vector_data.random_element_generator

    if register == "maskval":
        label = "random_maskval"
        if label in test_data.vector_labels:
            return label

        element_count = math.ceil(VLEN_MAX / 8)
        test_data.register_vector_data(
            label,
            8,
            random_elements=element_count,
        )

        return label

    name = rng.__name__ if rng else "default"
    if name == "default":
        # Different EEWs behave the same in this case
        eew = 64

    label = f"{register}_random_eew_{eew}_{name}"
    if label in test_data.vector_labels:
        return label

    # Assume LMUL=8. These cases are reused, its probably true at some point
    element_count = math.ceil(VLEN_MAX * 8 / eew)
    if rng is None:
        test_data.register_vector_data(label, eew, random_elements=element_count)
    else:
        elements = rng(element_count, eew, register)
        test_data.register_vector_data(label, eew, elements=elements)

    return label


def get_register_data_labels(
    instr_info: VectorInstructionInfo, instr_type_config: InstructionTypeConfig, sew: int, test_data: TestData
) -> dict:
    """Generates a dictionary with vector sources and relevant data inputs for ExceptionsV tests."""

    assert instr_type_config.vector_data is not None
    assert instr_type_config.required_params is not None

    vd_val_ptr = (
        get_data_label(
            "vd",
            int(sew * instr_info.get_size_multiplier("vd", sew, instr_type_config.vector_data)),
            instr_type_config,
            test_data,
        )
        if "vd" in instr_type_config.required_params
        else None
    )
    vs1_val_ptr = (
        get_data_label(
            "vs1",
            int(sew * instr_info.get_size_multiplier("vs1", sew, instr_type_config.vector_data)),
            instr_type_config,
            test_data,
        )
        if "vs1" in instr_type_config.required_params
        else None
    )
    vs2_val_ptr = (
        get_data_label(
            "vs2",
            int(sew * instr_info.get_size_multiplier("vs2", sew, instr_type_config.vector_data)),
            instr_type_config,
            test_data,
        )
        if "vs2" in instr_type_config.required_params
        else None
    )
    vs3_val_ptr = (
        get_data_label(
            "vs3",
            int(sew * instr_info.get_size_multiplier("vs3", sew, instr_type_config.vector_data)),
            instr_type_config,
            test_data,
        )
        if "vs3" in instr_type_config.required_params
        else None
    )
    maskval = (
        get_data_label("maskval", sew, instr_type_config, test_data)
        if "maskval" in instr_type_config.required_params
        else None
    )

    return {
        "vd_val_pointer": vd_val_ptr,
        "vs1_val_pointer": vs1_val_ptr,
        "vs2_val_pointer": vs2_val_ptr,
        "vs3_val_pointer": vs3_val_ptr,
        "maskval": maskval,
    }


@add_coverpoint_generator("cp_vstart")
def cp_vstart(
    instr_name: str,
    instr_type: str,
    coverpoint: str,
    test_data: TestData,
) -> list[TestChunk]:
    """
    Generate tests for instructions with vstart at preset values. Runs SIGUPD when instructions do not always trap, and runs
    SIGUPD on the final vstart value.
    """

    sews, coverpoint = extract_coverpoint_sews(coverpoint)

    vstart_values: list[Literal["one", "vlmaxm1", "vlmaxd2", "random", "vstart_gt_vl"]]
    vstart_values = ["vstart_gt_vl"] if coverpoint.endswith("_gt_vl") else ["one", "vlmaxm1", "vlmaxd2", "random"]

    instr_type_config = get_instruction_type_config(instr_type)
    assert instr_type_config.vector_data is not None, "Vector Data Must be Provided for Vector Instructions"
    assert instr_type_config.required_params is not None

    instr_info = parse_vector_instruction_info(instr_name, instr_type)

    # vstart is in units of bytes for these instructions
    is_mask_ls = instr_type in {"VSM", "VLM"}

    test_chunks: list[TestChunk] = []

    for vstart_val in vstart_values:
        # Initialize test chunk
        tc = test_data.begin_test_chunk()
        desc = f"{coverpoint} (vstart = {vstart_val})"
        tc.code.append(f"# Testcase {desc}")

        for sew in sews:
            lmul: int | float

            for lmul_exp in sorted(get_legal_lmuls(sew))[::-1]:
                lmul = 2**lmul_exp
                legal = True

                for reg in instr_type_config.required_params:
                    segments = instr_info.segments if reg in instr_type_config.vector_data.segmented_regs else 1
                    emul = instr_info.get_size_multiplier(reg, sew, instr_type_config.vector_data) * lmul
                    if max(emul, 1) * segments > 8:
                        legal = False
                        break

                if legal:
                    break
            else:
                raise ValueError(f"Could not find legal lmul to run {instr_name}")

            if instr_info.whole_registers is not None:
                lmul = instr_info.whole_registers

            bin_name = f"{vstart_val}_sew_{sew}"
            label_line = test_data.add_testcase(bin_name, coverpoint, f"{test_data.config.testsuite}_{instr_name}_cg")
            register_data = get_register_data_labels(instr_info, instr_type_config, sew, test_data)
            params = generate_random_vector_params(
                test_data, instr_name, instr_type, lmul, suite="length", vl="vlmax", sew=sew, **register_data
            )
            prior_sigupd_count = tc.sigupd_count
            setup, test, check = format_instruction(instr_name, instr_type, test_data, params)

            if instr_type_config.vector_data.require_zero_vstart:
                # These instructions always trap, so we should never sigupd
                check = "#endif" if setup.startswith("#if") else ""
                tc.sigupd_count = prior_sigupd_count

            eew_override = lmul_override = None
            if instr_info.load_store_eew is not None:
                eew_override = instr_info.load_store_eew
                lmul_override = lmul * (eew_override / sew) if instr_info.whole_registers is None else lmul

            pre_vstart = "\n".join(prep_vstart(test_data, params, vstart_val, is_mask_ls, eew_override, lmul_override))
            post_vstart = "\n".join(
                [
                    write_sigupd(None, test_data, "vstart"),
                    "csrw vstart, x0",
                ]
            )

            tc.code.extend(
                [
                    setup,
                    pre_vstart,
                    label_line,
                    test,
                    post_vstart,
                    check,
                ]
            )
            return_testcase_registers(test_data, params)

        tc = test_data.end_test_chunk()
        test_chunks.append(tc)

    return test_chunks


@add_coverpoint_generator("cp_vill")
def cp_vill(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Checks that instructions trap with an illegal instruction exception when vill is active.
    """

    instr_type_config = get_instruction_type_config(instr_type)
    assert instr_type_config.vector_data is not None, "Vector Data Must be Provided for Vector Instructions"
    assert instr_type_config.required_params is not None

    instr_info = parse_vector_instruction_info(instr_name, instr_type)
    tc = test_data.begin_test_chunk()
    desc = "cp_vill"
    tc.code.append(f"# Testcase {desc}")
    label_line = test_data.add_testcase("", coverpoint, f"{test_data.config.testsuite}_{instr_name}_cg")

    # We just need to get a valid test line
    register_data = get_register_data_labels(instr_info, instr_type_config, 32, test_data)
    params = generate_random_vector_params(
        test_data,
        instr_name,
        instr_type,
        get_base_lmul(instr_name, instr_type, 32),
        sew=32,
        **register_data,
    )
    _setup, test, _check = format_instruction(instr_name, instr_type, test_data, params)

    # This always traps so no SIGUPD
    tc.sigupd_count = 0

    vtype_reg, scratch = test_data.int_regs.get_registers(2, exclude_regs=[0])
    set_vill = "\n".join(
        [
            f"addi x{vtype_reg}, x0, -1",
            f"vsetvl x{scratch}, x0, x{vtype_reg}",
        ]
    )
    test_data.int_regs.return_registers([vtype_reg, scratch])

    tc.code.extend([set_vill, label_line, test])
    tc = test_data.end_test_chunk()
    return_testcase_registers(test_data, params)

    return [tc]


@add_coverpoint_generator("cp_exceptionsv_ffLS")  # Fault on first element (OK)
@add_coverpoint_generator("cp_exceptionsv_address_fault")  # Generate Address Fault test
def cp_exceptionsv_address_fault(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    sews, coverpoint = extract_coverpoint_sews(coverpoint)

    test_chunks: list[TestChunk] = []
    for sew in sews:
        tc = test_data.begin_test_chunk()
        params = generate_random_vector_params(
            test_data,
            instr_name,
            instr_type,
            get_base_lmul(instr_name, instr_type, sew),
            sew,
            rs1val_pointer="RVMODEL_ACCESS_FAULT_ADDRESS",
            vl=1,
        )
        label_line = test_data.add_testcase(f"sew{sew}", coverpoint)
        setup, test, _check = format_instruction(instr_name, instr_type, test_data, params)
        # We throw out check where the endif is found
        endif = "#endif" if setup.startswith("#if") else ""

        # Discard SIGUPD because this must fault
        tc.sigupd_count = 0
        tc.code.extend([setup, label_line, test, endif])

        tc = test_data.end_test_chunk()
        return_testcase_registers(test_data, params)
        test_chunks.append(tc)

    return test_chunks


@add_coverpoint_generator("cp_misalignv_ls_element_misaligned")
@add_coverpoint_generator("cp_misalignv_ls_wholereg_misaligned")
def cp_misalignv(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    sews, coverpoint = extract_coverpoint_sews(coverpoint)

    test_chunks: list[TestChunk] = []

    base_ptr = "misaligned_ls_base"
    if base_ptr not in test_data.vector_labels:
        test_data.register_vector_data(base_ptr, 64, random_elements=2)

    for sew in sews:
        lmul = get_base_lmul(instr_name, instr_type, sew)
        for offset in range(8):
            params = generate_random_vector_params(
                test_data, instr_name, instr_type, lmul, sew, rs1val_pointer="misaligned_ls_base"
            )

            tc = test_data.begin_test_chunk()
            label_line = test_data.add_testcase(f"sew{sew}_offset{offset}", coverpoint)
            setup, test, check = format_instruction(instr_name, instr_type, test_data, params)
            add_offset = f"addi x{params.rs1}, x{params.rs1}, {offset}"

            tc.code.extend([setup, add_offset, label_line, test, check])

            tc = test_data.end_test_chunk()
            return_testcase_registers(test_data, params)
            test_chunks.append(tc)

    return test_chunks


@add_coverpoint_generator("cp_mstatus_vs_off")
@add_coverpoint_generator("cp_mstatus_fs_off")
@add_coverpoint_generator("cp_vectorfp_mstatus_fs_state")
def cp_mstatus_v(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    sews, coverpoint = extract_coverpoint_sews(coverpoint)

    vs_options = []
    fs_options = []

    match coverpoint:
        case "cp_mstatus_vs_off":
            vs_options = [0]
            fs_options = [3]
        case "cp_mstatus_fs_off":
            vs_options = [3]
            fs_options = [0]
        case "cp_vectorfp_mstatus_fs_state":
            vs_options = [3]
            fs_options = [1, 2, 3]

    test_chunks: list[TestChunk] = []
    for sew in sews:
        lmul = get_base_lmul(instr_name, instr_type, sew)
        for vs, fs in itertools.product(vs_options, fs_options):
            params = generate_random_vector_params(
                test_data, instr_name, instr_type, lmul, sew, rs1val_pointer="misaligned_ls_base"
            )

            tc = test_data.begin_test_chunk()
            label_line = test_data.add_testcase(f"sew{sew}_vs{vs}_fs{fs}", coverpoint)
            setup, test, check = format_instruction(instr_name, instr_type, test_data, params)

            # Set the correct mstatus.vs and mstatus.fs for the test
            temp_reg = test_data.int_regs.get_register(exclude_regs=[0])
            FS_MASK = 3 << 13  # Bits [14:13]
            VS_MASK = 3 << 9  # Bits [10:9]
            set_mstatus_vs_fs = [
                f"LI(x{temp_reg}, {FS_MASK | VS_MASK})",
                tsbi_call(f"csrc mstatus, x{temp_reg}"),
                f"LI(x{temp_reg}, {(fs << 13) | (vs << 9)})",
                tsbi_call(f"csrs mstatus, x{temp_reg}"),
            ]

            # Re-Enable the mstatus bits after the test
            reenable_mstatus_bits = [
                f"LI(x{temp_reg}, {FS_MASK | VS_MASK})",
                tsbi_call(f"csrs mstatus, x{temp_reg}"),
            ]
            test_data.int_regs.return_register(temp_reg)

            tc.code.extend([setup, *set_mstatus_vs_fs, label_line, test, *reenable_mstatus_bits, check])

            tc = test_data.end_test_chunk()
            return_testcase_registers(test_data, params)
            test_chunks.append(tc)

    return test_chunks
