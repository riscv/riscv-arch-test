##################################
# fvmvvf_type.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from typing import Literal

from testgen.asm.helpers import load_float_reg
from testgen.asm.vector_helpers import (
    VectorLoad,
    handle_parameter_exclusions,
    handle_vector_fp,
    load_test_vtype,
    load_vec_regs,
    prep_mask_v,
    write_sigupd_v,
    write_sigupd_v_len,
)
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, VectorTypeConfig, add_instruction_formatter

fvmvvf_config = InstructionTypeConfig(
    instruction_class=["vector_fp"], required_params={"vd", "fs1"}, vector_data=VectorTypeConfig()
)
fvmvsf_config = InstructionTypeConfig(
    instruction_class=["vector_fp"], required_params={"vd", "fs1"}, vector_data=VectorTypeConfig(scalar_regs={"vd"})
)


@add_instruction_formatter("FVMVVF", fvmvvf_config)
def format_fvmvvf_type(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_fvmvvf_like_type(instr_str, test_data, params, "FVMVVF")


@add_instruction_formatter("FVMVSF", fvmvsf_config)
def format_fvmvsf_type(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_fvmvvf_like_type(instr_str, test_data, params, "FVMVSF", scalar_vd=True)


def format_fvmvvf_like_type(
    instr_str: str, test_data: TestData, params: InstructionParams, type_name: str, *, scalar_vd: bool = False
) -> tuple[list[str], list[str], list[str]]:
    assert params.vd is not None and params.vd_val_pointer is not None, (
        f"vd and vd_val_pointer must be provided for {type_name}-type instructions"
    )
    assert params.fs1 is not None and params.fs1val is not None, (
        f"fs1 and fs1val must be provided for {type_name}-type instructions"
    )
    assert params.temp_reg is not None, f"temp_reg must be provided for {type_name}-type instructions"
    assert params.sew is not None, f"sew must be provided for {type_name}-type instructions"
    assert params.lmul is not None, f"lmul must be provided for {type_name}-type instructions"
    assert test_data.test_chunk is not None, "format_vid_type must be used with an active TestChunk"
    assert params.csr_frm_val is not None, (
        f"csr_frm_val must be provided for {type_name}-type instructions as vector floating point instructions use the dyn rounding mode"
    )

    test_data.test_chunk.vector_labels.append(
        (params.vd_val_pointer, *test_data.vector_labels[params.vd_val_pointer]),
    )

    # Set up the instructions: Mask, vd (potentially preloaded)
    setup = []

    # Setup Mask
    if params.maskval:
        setup.extend(prep_mask_v(params.maskval, test_data, params))

    lmul = params.lmul if not scalar_vd else 1
    vl = params.vl if not scalar_vd else 1
    vd_vl = vl if params.vector_suite == "base" else "vlmax"
    load_code, random_vl_reg = load_vec_regs(
        [VectorLoad("vd", vl=vd_vl, lmul=lmul, no_fractional_load=True)], params, test_data
    )
    setup.extend(load_code)
    fp_load_sew_map: dict[int, Literal["half", "single", "double", "quad"]] = {16: "half", 32: "single", 64: "double"}
    setup.append(load_float_reg("fs1", params.fs1, params.fs1val, test_data, fp_load_sew_map[params.sew]))
    setup.append(load_test_vtype(params, random_vl_reg))

    # We don't need random_vl_reg anymore
    if random_vl_reg.startswith("x"):
        test_data.int_regs.return_register(int(random_vl_reg[1:]))

    if params.maskval:
        test = [f"{instr_str} v{params.vd}, f{params.fs1}, v0.t"]
    else:
        test = [f"{instr_str} v{params.vd}, f{params.fs1}"]

    if params.vector_suite == "length":
        check = [*write_sigupd_v_len(test_data, params, lmul, scalar_dest=scalar_vd)]
    else:
        check = [*write_sigupd_v(test_data, params)]

    # This can only be released after sigupd
    if params.maskval:
        test_data.vec_regs.return_register(0)

    handle_parameter_exclusions(params.lmul, setup, check)
    handle_vector_fp(setup, check, params.csr_frm_val, test_data)

    return (setup, test, check)
