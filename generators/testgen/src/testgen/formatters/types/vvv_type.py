##################################
# vvv_type.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import load_vec_reg, prep_base_v, prep_mask_v, reload_vtype, write_sigupd_v, write_sigupd_v_len
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

    # Setup Mask
    if params.maskval:
        setup.extend(prep_mask_v(params.maskval, test_data, params, clobber_vd=True))

    # Preload vd at vlmax
    vd_preloaded = False
    if params.vector_suite == "length":
        setup.extend(
            load_vec_reg(
                "vd", params.vd, params.vd_val_pointer, params, lmul=max(params.lmul, 1), vl_register_or_imm="x0"
            )
        )
        vd_preloaded = True
        registers.remove(params.vd)

    # vl_register_or_imm is useful if we ever overwrite vl as it allows us to easily restore it
    prep_lines, vl_register_or_imm = prep_base_v(test_data, params, registers)
    setup.extend(prep_lines)

    lmul_overwrite: int | None = None
    if params.lmul < 1:
        lmul_overwrite = 1
    vl_overwrite: int | None = None
    if vl_register_or_imm == 0:
        vl_overwrite = 1

    if not vd_preloaded:
        setup.extend(
            load_vec_reg(
                "vd", params.vd, params.vd_val_pointer, params, lmul=lmul_overwrite, vl_register_or_imm=vl_overwrite
            )
        )

    setup.extend(
        [
            *load_vec_reg(
                "vs2", params.vs2, params.vs2_val_pointer, params, lmul=lmul_overwrite, vl_register_or_imm=vl_overwrite
            ),
            *load_vec_reg(
                "vs1", params.vs1, params.vs1_val_pointer, params, lmul=lmul_overwrite, vl_register_or_imm=vl_overwrite
            ),
        ]
    )

    if lmul_overwrite is not None or vl_overwrite is not None:
        setup.append(reload_vtype(params, vl_register_or_imm))

    if isinstance(vl_register_or_imm, str) and vl_register_or_imm != "x0":
        test_data.int_regs.return_register(int(vl_register_or_imm[1:]))

    if params.maskval:
        test = [f"{instr_str} v{params.vd}, v{params.vs2}, v{params.vs1}, v0.t"]
    else:
        test = [f"{instr_str} v{params.vd}, v{params.vs2}, v{params.vs1}"]

    # Return non-vd registers
    test_data.vec_regs.deallocate_parameter("vs2")
    test_data.vec_regs.deallocate_parameter("vs1")

    if params.vector_suite == "length":
        check = [*write_sigupd_v_len(test_data, params, 1, params.lmul)]
    else:
        check = [*write_sigupd_v(test_data, params)]

    # This can only be released after sigupd
    if params.maskval:
        test_data.vec_regs.return_register(0)

    return (setup, test, check)
