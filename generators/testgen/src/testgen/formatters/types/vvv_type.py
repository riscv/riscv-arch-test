##################################
# vvv_type.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import load_vec_reg, prep_base_v, write_sigupd_v, write_sigupd_v_len
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

vvv_config = InstructionTypeConfig(required_params={"vd", "vs1", "vs2"})
wwv_config = InstructionTypeConfig(required_params={"vd", "vs1", "vs2"}, vector_overlap_constraints={("vd", "vs1")})
wvv_config = InstructionTypeConfig(
    required_params={"vd", "vs1", "vs2"}, vector_overlap_constraints={("vd", "vs1"), ("vd", "vs2")}
)


@add_instruction_formatter("VVV", vvv_config)
@add_instruction_formatter("WWV", wwv_config)
@add_instruction_formatter("WVV", wvv_config)
def format_vvv_type(
    instr_str: str,
    test_data: TestData,
    params: InstructionParams,
) -> tuple[list[str], list[str], list[str]]:
    assert params.vs1 is not None and params.vs1_val_pointer is not None, (
        "vs1 and vs1_val_pointer must be provided for VVV-type instructions"
    )
    assert params.vs2 is not None and params.vs2_val_pointer is not None, (
        "vs2 and vs2_val_pointer must be provided for VVV-type instructions"
    )
    assert params.vd is not None and params.vd_val_pointer is not None, (
        "vd and vd_val_pointer must be provided for VVV-type instructions"
    )
    assert params.temp_reg is not None, "temp_reg must provided for be VVV-type instructions"
    assert params.sew is not None, "sew must provided for be VVV-type instructions"
    assert params.lmul is not None, "lmul must provided for be VVV-type instructions"
    assert test_data.test_chunk is not None, "format_vvv_type must be used with an active TestChunk"

    test_data.test_chunk.vector_labels.extend(
        [
            (params.vs1_val_pointer, *test_data.vector_labels[params.vs1_val_pointer]),
            (params.vs2_val_pointer, *test_data.vector_labels[params.vs2_val_pointer]),
            (params.vd_val_pointer, *test_data.vector_labels[params.vd_val_pointer]),
        ]
    )

    setup = []
    registers = [params.vd, params.vs2, params.vs1]
    # Preload vd at vlmax
    vd_preloaded = False
    if params.vector_suite == "length":
        setup.extend(
            load_vec_reg(
                "vd", params.vd, params.vd_val_pointer, params.temp_reg, lmul=params.lmul, sew=params.sew, vl="vlmax"
            )
        )
        vd_preloaded = True
        registers.remove(params.vd)

    setup.extend(prep_base_v(test_data, params, registers))

    if not vd_preloaded:
        setup.extend(load_vec_reg("vd", params.vd, params.vd_val_pointer, params.temp_reg, params.sew))

    setup.extend(
        [
            *load_vec_reg("vs2", params.vs2, params.vs2_val_pointer, params.temp_reg, params.sew),
            *load_vec_reg("vs1", params.vs1, params.vs1_val_pointer, params.temp_reg, params.sew),
        ]
    )

    if params.maskval:
        raise NotImplementedError("Need to load the mask val")
        test = [f"{instr_str} v{params.vd}, v{params.vs2}, v{params.vs1}, v0.t"]
    else:
        test = [f"{instr_str} v{params.vd}, v{params.vs2}, v{params.vs1}"]

    if params.vector_suite == "length":
        check = [*write_sigupd_v_len(test_data, params, 1, max(int(params.lmul), 1))]
    else:
        check = [*write_sigupd_v(test_data, params)]

    return (setup, test, check)
