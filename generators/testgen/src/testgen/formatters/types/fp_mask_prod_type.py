##################################
# fp_mask_prod_type.py
#
# rwolk@hmc.edu September 2026
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
    write_sigupd_v_mask_prod,
)
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, VectorTypeConfig, add_instruction_formatter

# Mask = Vector op Vector
fmvv_config = InstructionTypeConfig(
    instruction_class=["vector_fp"],
    required_params={"vd", "vs1", "vs2"},
    vector_data=VectorTypeConfig(
        mask_regs={"vd"},
        masked_constraints={("vs1", "v0"), ("vs2", "v0")},
    ),
)
# Mask = Vector op Integer
fmvf_config = InstructionTypeConfig(
    instruction_class=["vector_fp"],
    required_params={"vd", "fs1", "vs2"},
    vector_data=VectorTypeConfig(mask_regs={"vd"}, masked_constraints={("vs2", "v0")}),
)


@add_instruction_formatter("FMVV", fmvv_config)
def format_fmvv(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_fp_mask_producing_type(instr_str, test_data, params, "FMVV", scalar_register=False)


@add_instruction_formatter("FMVF", fmvf_config)
def format_fmvf(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_fp_mask_producing_type(instr_str, test_data, params, "FMVF", scalar_register=True)


def format_fp_mask_producing_type(
    instr_str: str,
    test_data: TestData,
    params: InstructionParams,
    type_name: str,
    scalar_register: bool,
) -> tuple[list[str], list[str], list[str]]:
    assert params.temp_reg is not None, f"temp_reg must be provided for {type_name}-type instructions"
    assert params.sew is not None, f"sew must be provided for {type_name}-type instructions"
    assert params.lmul is not None, f"lmul must be provided for {type_name}-type instructions"
    assert params.csr_frm_val is not None, (
        f"csr_frm_val must be provided for {type_name}-type instructions as vector floating point instructions use the dyn rounding mode"
    )
    assert test_data.test_chunk is not None, f"format_{type_name.lower()}_type must be used with an active TestChunk"

    assert params.vd is not None and params.vs2 is not None, (
        f"vd and vs2 must be provided for {type_name}-type instructions"
    )
    vec_regs_to_setup = [params.vd, params.vs2]
    if not scalar_register:
        assert params.vs1 is not None, f"vs1 must be provided for {type_name}-type instructions"
        vec_regs_to_setup.append(params.vs1)

    setup = []

    # Setup Mask
    mask_copy_reg = None
    load_vd = True
    if params.maskval:
        setup.extend(prep_mask_v(params.maskval, test_data, params, clobber_vd=True, vd_v0=params.vd == 0))
        if 0 in vec_regs_to_setup:
            vec_regs_to_setup.remove(0)

        if params.vd == 0 and params.vector_suite == "length":
            mask_copy_reg = test_data.vec_regs.get_register(lmul=1)
            setup.extend(
                [
                    "# Because vd = v0, we will not overwrite it with a mask value, instead because the",
                    f"# operation will overwrite v0, we will store a copy of the mask in v{mask_copy_reg}",
                    f"vmand.mm v{mask_copy_reg}, v0, v0",
                ]
            )
            load_vd = False

    to_load = []
    # Load vd
    if load_vd:
        assert params.vd is not None and params.vd_val_pointer is not None, (
            f"vd and vd_val_pointer must be provided for {type_name}-type instructions"
        )
        to_load.append(VectorLoad(reg="vd", lmul=1, vl="vlmax"))
        test_data.test_chunk.vector_labels.append(
            (params.vd_val_pointer, *test_data.vector_labels[params.vd_val_pointer]),
        )

    # vs2 is always loaded
    assert params.vs2 is not None and params.vs2_val_pointer is not None, (
        f"vs2 and vs2_val_pointer must be provided for {type_name}-type instructions"
    )
    to_load.append(VectorLoad(reg="vs2"))
    test_data.test_chunk.vector_labels.append(
        (params.vs2_val_pointer, *test_data.vector_labels[params.vs2_val_pointer])
    )

    # Load a third operand (if present)
    testline = f"{instr_str} v{params.vd}, v{params.vs2}"
    if not scalar_register:
        assert params.vs1 is not None and params.vs1_val_pointer is not None, (
            f"vs1 and vs1_val_pointer must be provided for {type_name}-type instructions"
        )
        to_load.append(VectorLoad(reg="vs1"))
        testline += f", v{params.vs1}"
        test_data.test_chunk.vector_labels.append(
            (params.vs1_val_pointer, *test_data.vector_labels[params.vs1_val_pointer]),
        )
    else:
        assert params.fs1 is not None and params.fs1val is not None, (
            f"fs1 and fs1val must be provided for {type_name}-type instructions"
        )
        fp_load_sew_map: dict[int, Literal["half", "single", "double", "quad"]] = {
            16: "half",
            32: "single",
            64: "double",
        }
        setup.append(load_float_reg("fs1", params.fs1, params.fs1val, test_data, fp_load_sew_map[params.sew]))
        testline += f", f{params.fs1}"

    load_code, random_vl_reg = load_vec_regs(to_load, params, test_data)
    setup.extend(load_code)
    setup.append(load_test_vtype(params, random_vl_reg))

    test = [f"{testline}, v0.t"] if params.maskval else [testline]

    if params.vector_suite == "length":
        mask_reg = 0 if mask_copy_reg is None else mask_copy_reg
        recover_mask = []

        if mask_reg != 0:
            recover_mask = [f"vmand.mm v0, v{mask_reg}, v{mask_reg}"]

        vlmax_vsetvli = [load_test_vtype(params, random_vl_reg, force_vlmax=True)]

        check = [
            *write_sigupd_v_len(test_data, params, lmul=1, mask_producing=True, mask_reg=mask_reg),
            "# After a length suite sigupd, we need to do the operation as if vl=vlmax as that is a valid behavior",
            "# in the tail, according to the spec. None of the registers involved in the operation could have been",
            "# clobbered in the sigupd, however, in the case of a masked instruction with vd = v0, v0 was overwritten.",
            "# So, we may have to recover that value.",
            *recover_mask,
            *vlmax_vsetvli,
            test[0],
            "# This sigupd variant saves this result to the signature in non-selfcheck mode, and no-ops in selfcheck mode",
            *write_sigupd_v_mask_prod(test_data, params),
        ]

        if mask_reg != 0:
            test_data.vec_regs.return_register(mask_reg)
    else:
        check = [*write_sigupd_v(test_data, params, mask_producing=True)]

    # This can only be released after sigupd
    if params.maskval and params.vd != 0:
        test_data.vec_regs.return_register(0)

    # We don't need random_vl_reg anymore
    if random_vl_reg.startswith("x"):
        test_data.int_regs.return_register(int(random_vl_reg[1:]))

    handle_parameter_exclusions(params.lmul, setup, check)

    handle_vector_fp(setup, check, params.csr_frm_val, test_data)

    return (setup, test, check)
