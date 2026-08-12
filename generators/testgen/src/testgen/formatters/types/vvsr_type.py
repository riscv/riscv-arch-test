##################################
# vvsr_type.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.vector_helpers import (
    VectorLoad,
    handle_lmul_ifdef,
    load_test_vtype,
    load_vec_regs,
    prep_mask_v,
    write_sigupd_v,
    write_sigupd_v_len,
)
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, VectorTypeConfig, add_instruction_formatter

vvsr_config = InstructionTypeConfig(
    required_params={"vd", "vs1", "vs2"},
    vector_data=VectorTypeConfig(scalar_regs={"vd", "vs1"}),
)
wvwsr_config = InstructionTypeConfig(
    required_params={"vd", "vs1", "vs2"},
    vector_data=VectorTypeConfig(
        overlap_constraints={("vs2", "vs1")}, scalar_regs={"vd", "vs1"}, widened_regs={"vd", "vs1"}
    ),
)


@add_instruction_formatter("VVSR", vvsr_config)
def format_vvsr(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_vvsr_like_type(instr_str, test_data, params, "VVSR")


@add_instruction_formatter("WVWSR", wvwsr_config)
def format_wvwsr(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.vs1 != params.vs2
    return format_vvsr_like_type(instr_str, test_data, params, "WVWSR", widen={"vd", "vs1"})


def format_vvsr_like_type(
    instr_str: str,
    test_data: TestData,
    params: InstructionParams,
    type_name: str,
    *,
    widen: set[str] | None = None,
) -> tuple[list[str], list[str], list[str]]:
    assert params.vs1 is not None and params.vs1_val_pointer is not None, (
        f"vs1 and vs1_val_pointer must be provided for {type_name}-type instructions"
    )
    assert params.vs2 is not None and params.vs2_val_pointer is not None, (
        f"vs2 and vs2_val_pointer must be provided for {type_name}-type instructions"
    )
    assert params.vd is not None and params.vd_val_pointer is not None, (
        f"vd and vd_val_pointer must be provided for {type_name}-type instructions"
    )
    assert params.temp_reg is not None, f"temp_reg must provided for be {type_name}-type instructions"
    assert params.sew is not None, f"sew must provided for be {type_name}-type instructions"
    assert params.lmul is not None, f"lmul must provided for be {type_name}-type instructions"
    assert test_data.test_chunk is not None, f"format_{type_name.lower()}_type must be used with an active TestChunk"

    if widen is None:
        widen = set()

    test_data.test_chunk.vector_labels.extend(
        [
            (params.vs1_val_pointer, *test_data.vector_labels[params.vs1_val_pointer]),
            (params.vs2_val_pointer, *test_data.vector_labels[params.vs2_val_pointer]),
            # Due to how masking works, sometimes the vd pointer is not used
        ]
    )

    setup = []

    # Setup Mask
    load_vd = True
    mask_copy_reg = None
    if params.maskval:
        setup.extend(prep_mask_v(params.maskval, test_data, params, clobber_vd=True, vd_v0=params.vd == 0))
        if params.vector_suite == "length" and params.vd == 0:
            mask_copy_reg = test_data.vec_regs.get_register(lmul=1)
            setup.extend(
                [
                    "# vd = v0, and the operation will be masked, so we cannot load a value for vd here. Instead, because this is",
                    "# a length suite test we will make a copy of the mask, so that when the operation later overwrites it, it can",
                    "# still be retrieved",
                    f"vmand.mm v{mask_copy_reg}, v0, v0",
                ]
            )
            load_vd = False

    vd_vl = 1 if params.vector_suite == "base" else "vlmax"
    vd_sew = params.sew * (2 if "vd" in widen else 1)
    vs1_sew = params.sew * (2 if "vs1" in widen else 1)

    to_load = []
    if load_vd:
        to_load.append(VectorLoad(reg="vd", vl=vd_vl, lmul=1, sew=vd_sew))
        test_data.test_chunk.vector_labels.append(
            (params.vd_val_pointer, *test_data.vector_labels[params.vd_val_pointer])
        )

    to_load.extend(
        [
            VectorLoad(reg="vs2", widen="vs2" in widen),
            VectorLoad(reg="vs1", vl=1, lmul=1, sew=vs1_sew),
        ]
    )

    load_code, random_vl_reg = load_vec_regs(to_load, params, test_data)
    setup.extend(load_code)
    setup.append(load_test_vtype(params, random_vl_reg))

    # We don't need random_vl_reg anymore
    if random_vl_reg.startswith("x"):
        test_data.int_regs.return_register(int(random_vl_reg[1:]))

    if params.maskval:
        test = [f"{instr_str} v{params.vd}, v{params.vs2}, v{params.vs1}, v0.t"]
    else:
        test = [f"{instr_str} v{params.vd}, v{params.vs2}, v{params.vs1}"]

    mask_reg = 0 if mask_copy_reg is None else mask_copy_reg
    if params.vector_suite == "length":
        check = [
            *write_sigupd_v_len(test_data, params, 1, 1, widen_vd="vd" in widen, scalar_dest=True, mask_reg=mask_reg)
        ]
    else:
        check = [*write_sigupd_v(test_data, params, widen_vd="vd" in widen)]

    # This can only be released after sigupd
    if params.maskval:
        test_data.vec_regs.return_register(mask_reg)

    handle_lmul_ifdef(params.lmul, setup, check)

    return (setup, test, check)
