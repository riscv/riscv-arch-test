##################################
# vvsr_type.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.vector_helpers import (
    load_vec_reg,
    prep_base_v,
    prep_mask_v,
    reload_vtype,
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
    registers = [params.vd, params.vs2, params.vs1]

    # Setup Mask
    if params.maskval:
        setup.extend(prep_mask_v(params.maskval, test_data, params, clobber_vd=True, vd_v0=params.vd == 0))

    # Preload vd at vlmax
    vd_preloaded = False
    mask_copy_reg = None
    # We need to have a special case for vd being the mask, as the initial value of vd doesn't matter
    # while the mask value does matter.
    if params.vector_suite == "length" and not (params.vd == 0 and params.maskval):
        vd_sew = params.sew * (2 if "vd" in widen else 1)
        setup.extend(
            load_vec_reg(params.vd, params.vd_val_pointer, params, sew_override=vd_sew, lmul=1, vl_register_or_imm="x0")
        )
        test_data.test_chunk.vector_labels.append(
            (params.vd_val_pointer, *test_data.vector_labels[params.vd_val_pointer])
        )
        vd_preloaded = True
        registers.remove(params.vd)
    elif params.vd == 0 and params.maskval:
        if params.vector_suite == "length":
            mask_copy_reg = test_data.vec_regs.get_register(lmul=1)
            setup.extend(
                [
                    "# vd = v0, and the operation will be masked, so we cannot load a value for vd here. Instead, because this is",
                    "# a length suite test we will make a copy of the mask, so that when the operation later overwrites it, it can",
                    "# still be retrieved",
                    f"vmand.mm v{mask_copy_reg}, v0, v0",
                ]
            )
        vd_preloaded = True
        registers.remove(params.vd)

    # vl_register_or_imm is useful if we ever overwrite vl as it allows us to easily restore it
    prep_lines, vl_register_or_imm = prep_base_v(test_data, params, registers)
    setup.extend(prep_lines)

    # Load Registers at the Proper LMULs (loading whole registers if necessary, and tracking changes to vtype)
    lmul_overwrite: int = int(max(params.lmul, 1))

    vl_overwrite: int | str = vl_register_or_imm
    if vl_overwrite == 0:  # Loads at vl=0 are a no-op
        vl_overwrite = 1

    if not vd_preloaded:
        vd_vl_overwrite = vl_overwrite if "vd" not in widen else 2
        vd_sew = params.sew * (2 if "vd" in widen else 1)
        setup.extend(
            load_vec_reg(
                params.vd,
                params.vd_val_pointer,
                params,
                sew_override=vd_sew,
                lmul=1,
                vl_register_or_imm=vd_vl_overwrite,
            )
        )
        test_data.test_chunk.vector_labels.append(
            (params.vd_val_pointer, *test_data.vector_labels[params.vd_val_pointer])
        )

    setup.extend(
        load_vec_reg(
            params.vs2,
            params.vs2_val_pointer,
            params,
            lmul=lmul_overwrite,
            vl_register_or_imm=vl_overwrite,
        )
    )

    vs1_vl_overwrite = 1 if "vs1" not in widen else 2
    vs1_sew = params.sew * (2 if "vs1" in widen else 1)
    setup.extend(
        load_vec_reg(
            params.vs1,
            params.vs1_val_pointer,
            params,
            sew_override=vs1_sew,
            lmul=1,
            vl_register_or_imm=vs1_vl_overwrite,
        )
    )

    # Ensure vtype is correct for the instruction. We overwrite lmul to 1, so this is necessary
    setup.append(reload_vtype(params, vl_register_or_imm))

    # Now we are done with the clean up register
    if isinstance(vl_register_or_imm, str) and vl_register_or_imm != "x0":
        test_data.int_regs.return_register(int(vl_register_or_imm[1:]))

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

    return (setup, test, check)
