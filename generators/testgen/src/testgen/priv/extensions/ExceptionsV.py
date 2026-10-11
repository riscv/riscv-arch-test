##################################
# priv/extensions/ExceptionsV.py
#
# ExceptionsV* test generator
# rwolk@hmc.edu Oct 2026
# SPDX-License-Identifier: Apache-2.0
##################################

import math
from pathlib import Path
from typing import Literal

from testgen.asm.vector_helpers import prep_vstart
from testgen.constants import VLEN_MAX
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters.registry import InstructionTypeConfig, format_instruction, get_instruction_type_config
from testgen.instructions.vector import VectorInstructionInfo, get_base_lmul, parse_vector_instruction_info
from testgen.instructions.vector_params import generate_random_vector_params
from testgen.io.testplans import read_testplan
from testgen.priv.registry import add_priv_test_generator

REGISTERED_LABELS: set[str] = set()


def get_data_label(register: str, eew: int, instr_type_config: InstructionTypeConfig, test_data: TestData) -> str:
    assert instr_type_config.vector_data is not None, "vector_data must be provided for vector instructions"
    rng = instr_type_config.vector_data.random_element_generator

    if register == "maskval":
        label = "random_maskval"
        if label in REGISTERED_LABELS:
            return label

        element_count = math.ceil(VLEN_MAX / 8)
        test_data.register_vector_data(
            label,
            8,
            random_elements=element_count,
        )

        REGISTERED_LABELS.add(label)
        return label

    name = rng.__name__ if rng else "default"
    if name == "default":
        # Different EEWs behave the same in this case
        eew = 32

    label = f"{register}_random_eew_{eew}_{name}"
    if label in REGISTERED_LABELS:
        return label

    # Assume LMUL=8. These cases are reused, its probably true at some point
    element_count = math.ceil(VLEN_MAX * 8 / eew)
    if rng == None:
        test_data.register_vector_data(label, eew, random_elements=element_count)
    else:
        elements = rng(element_count, eew, register)
        test_data.register_vector_data(label, eew, elements=elements)

    REGISTERED_LABELS.add(label)
    return label


def get_register_data_labels(
    instr_info: VectorInstructionInfo, instr_type_config: InstructionTypeConfig, sew: int, test_data: TestData
) -> dict:
    assert instr_type_config.vector_data is not None
    assert instr_type_config.required_params is not None

    vd_val_ptr = (
        get_data_label(
            "vd",
            int(sew * instr_info.get_size_multiplier("vd", sew, instr_type_config.vector_data.widened_regs)),
            instr_type_config,
            test_data,
        )
        if "vd" in instr_type_config.required_params
        else None
    )
    vs1_val_ptr = (
        get_data_label(
            "vs1",
            int(sew * instr_info.get_size_multiplier("vs1", sew, instr_type_config.vector_data.widened_regs)),
            instr_type_config,
            test_data,
        )
        if "vs1" in instr_type_config.required_params
        else None
    )
    vs2_val_ptr = (
        get_data_label(
            "vs2",
            int(sew * instr_info.get_size_multiplier("vs2", sew, instr_type_config.vector_data.widened_regs)),
            instr_type_config,
            test_data,
        )
        if "vs2" in instr_type_config.required_params
        else None
    )
    vs3_val_ptr = (
        get_data_label(
            "vs3",
            int(sew * instr_info.get_size_multiplier("vs3", sew, instr_type_config.vector_data.widened_regs)),
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


def cp_vstart(
    instr_name: str,
    instr_type: str,
    coverpoint: str,
    sews_supported: list[int],
    test_data: TestData,
    vstart_values: list[Literal["one", "vlmaxm1", "vlmaxd2", "random", "vstart_gt_vl"]],
) -> list[TestChunk]:
    instr_type_config = get_instruction_type_config(instr_type)
    assert instr_type_config.vector_data is not None, "Vector Data Must be Provided for Vector Instructions"
    assert instr_type_config.required_params is not None

    instr_info = parse_vector_instruction_info(instr_name, instr_type)

    max_multiplier = max(
        instr_info.get_size_multiplier(reg, sew, instr_type_config.vector_data.widened_regs)
        for sew in sews_supported
        for reg in instr_type_config.required_params
    )
    max_lmul = int(8 / max_multiplier)

    if instr_info.whole_registers is not None:
        # The EVL in these cases is calculated as if LMUL=nreg
        max_lmul = instr_info.whole_registers
    if instr_type in {"VSM", "VLM"}:
        # vstart is in units of bytes for these instructions (might make more sense to >> 3 the result ...)
        max_lmul = 1

    test_chunks: list[TestChunk] = []

    for vstart_val in vstart_values:
        # # Pick a random valid lmul (non-fractional)
        # lmul = 2 ** random_range(0, int(math.log2(max_lmul)))
        lmul = max_lmul

        # Initialize test chunk
        tc = test_data.begin_test_chunk()
        desc = f"{coverpoint} (vstart = {vstart_val})"
        tc.code.append(f"# Testcase {desc}")

        # Generate Per-SEW tests (ifdef'ed by UDB_SEW_MIN)
        for sew in sews_supported:
            bin_name = f"{vstart_val}_sew_{sew}"
            label_line = test_data.add_testcase(bin_name, coverpoint, f"{test_data.config.testsuite}_{instr_name}_cg")
            register_data = get_register_data_labels(instr_info, instr_type_config, sew, test_data)
            params = generate_random_vector_params(
                test_data, instr_name, instr_type, lmul, suite="length", vl="vlmax", sew=sew, **register_data
            )
            setup, test, check = format_instruction(instr_name, instr_type, test_data, params)

            pre_vstart = "\n".join(prep_vstart(test_data, params, vstart_val))
            if "store" in instr_type_config.instruction_class:
                # In this case, we should reset vstart before the reload instruction runs
                test_lines = test.split()
                assert len(test_lines) == 2, f"Unknown Vector Store Test Section (Expected 2 Test lines, Got: {test:r})"
                test = "\n".join([test_lines[0], "csrw vstart, x0", test_lines[1]])
                post_vstart = ""
            else:
                post_vstart = "csrw vstart, x0"

            if instr_type_config.vector_data.require_zero_vstart:
                # These instructions always trap, so we should never sigupd
                check = ""
                tc.sigupd_count = 0

            arch_preamble = "\n".join([".option push", ".option arch, +zve64x"] if sew * max_multiplier > 32 else [])
            arch_post = ".option pop" if sew * max_multiplier > 32 else ""
            tc.code.extend(
                [
                    f"#if (UDB_SEW_MIN <= {int(sew * max_multiplier)} && {int(sew * max_multiplier)} <= UDB_ELEN)",
                    arch_preamble,
                    setup,
                    pre_vstart,
                    label_line,
                    test,
                    post_vstart,
                    check,
                    arch_post,
                    "#endif",
                ]
            )
            return_testcase_registers(test_data, params)

        tc = test_data.end_test_chunk()
        test_chunks.append(tc)

    return test_chunks


def cp_vill(
    instr_name: str, instr_type: str, coverpoint: str, sews_supported: list[int], test_data: TestData
) -> list[TestChunk]:
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
        get_base_lmul(instr_name, instr_type, 8),
        sew=8,
        **register_data,
    )
    _setup, test, _check = format_instruction(instr_name, instr_type, test_data, params)

    # This always traps so no SIGUPD
    tc.sigupd_count = 0

    # Because there is no sigupd, we don't care about store readback
    if "store" in get_instruction_type_config(instr_type).instruction_class:
        test = test.split()[0]

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


@add_priv_test_generator(
    "ExceptionsVx",
    required_extensions=["Zve32x"],
    extra_defines=[
        "#define RVTEST_VECTOR",
        "#define VDSEW 64",  # Ensures SIGSTRIDE is the right length
        "#define RVTEST_SEW 8",  # Enables all fractional LMUL macros
    ],
    testcases_per_file=100,
)
def make_exceptions_vx(test_data: TestData) -> list[TestChunk]:
    test_chunks: list[TestChunk] = []

    instructions = read_testplan(Path("./testplans/priv/ExceptionsVx.csv"))
    for instr_data in instructions:
        for coverpoint in instr_data.coverpoints:
            match coverpoint:
                case "cp_vstart":
                    test_chunks.extend(
                        cp_vstart(
                            instr_data.instr_name,
                            instr_data.instr_type,
                            coverpoint,
                            instr_data.sews_supported,
                            test_data,
                            ["one", "vlmaxm1", "vlmaxd2", "random"],
                        )
                    )
                case "cp_vill":
                    test_chunks.extend(
                        cp_vill(
                            instr_data.instr_name,
                            instr_data.instr_type,
                            coverpoint,
                            instr_data.sews_supported,
                            test_data,
                        )
                    )
                case "cp_vstart_gt_vl":
                    test_chunks.extend(
                        cp_vstart(
                            instr_data.instr_name,
                            instr_data.instr_type,
                            coverpoint,
                            instr_data.sews_supported,
                            test_data,
                            vstart_values=["vstart_gt_vl"],
                        )
                    )
                case _:
                    raise ValueError(f"Unknown ExceptionsVx Coverpoint {coverpoint}")

    return test_chunks
