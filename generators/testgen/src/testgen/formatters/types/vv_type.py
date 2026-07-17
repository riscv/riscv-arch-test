##################################
# vv_type.py
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
from testgen.coverpoints.vector.vector_helpers import extract_instruction_info
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, VectorTypeConfig, add_instruction_formatter

vmvr_config = InstructionTypeConfig(required_params={"vd", "vs2"}, vector_data=VectorTypeConfig())
vext_config = InstructionTypeConfig(
    required_params={"vd", "vs2"},
    vector_data=VectorTypeConfig(overlap_constraints={("vd_bottom", "vs2")}),
)
vm_config = InstructionTypeConfig(
    required_params={"vd", "vs2"},
    vector_data=VectorTypeConfig(
        mask_regs={"vs2"},
        overlap_constraints={("vd", "vs2")},
        masked_constraints={("vd", "v0")},
    ),
)


@add_instruction_formatter("VMVR", vmvr_config)
def format_vmvr_type(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    n_registers = int(instr_str[3])
    return format_vv_like_type(instr_str, test_data, params, "VMVR", lmul_override=n_registers, preload_vs2=True)


@add_instruction_formatter("VEXT", vext_config)
def format_vext_type(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    info = extract_instruction_info(instr_str, "VEXT")
    assert info.vext_multiplier is not None, f"Unable to extract multiplier for VEXT-type instruction {instr_str}"
    return format_vv_like_type(instr_str, test_data, params, "VEXT", vs2_lmul_multiplier=info.vext_multiplier)


@add_instruction_formatter("VM", vm_config)
def format_vm_type(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_vv_like_type(instr_str, test_data, params, "VM", vs2_mask=True)


def format_vv_like_type(
    instr_str: str,
    test_data: TestData,
    params: InstructionParams,
    type_name: str,
    *,
    lmul_override: float | None = None,
    vs2_lmul_multiplier: float = 1,
    vs2_mask: bool = False,
    preload_vs2: bool = False,
) -> tuple[list[str], list[str], list[str]]:
    assert params.vs2 is not None and params.vs2_val_pointer is not None, (
        f"vs2 and vs2_val_pointer must be provided for {type_name}-type instructions"
    )
    assert params.vd is not None and params.vd_val_pointer is not None, (
        f"vd and vd_val_pointer must be provided for {type_name}-type instructions"
    )
    assert params.temp_reg is not None, f"temp_reg must provided for be {type_name}-type instructions"
    assert params.sew is not None, f"sew must provided for be {type_name}-type instructions"
    assert params.lmul is not None or lmul_override is not None, (
        f"lmul must provided for be {type_name}-type instructions"
    )
    assert test_data.test_chunk is not None, f"format_{type_name.lower()}_type must be used with an active TestChunk"

    test_data.test_chunk.vector_labels.extend(
        [
            (params.vs2_val_pointer, *test_data.vector_labels[params.vs2_val_pointer]),
            (params.vd_val_pointer, *test_data.vector_labels[params.vd_val_pointer]),
        ]
    )

    # Set up the instructions: Mask, vd (potentially preloaded), vs2 (at correct lmul)
    setup = []
    registers = [params.vd, params.vs2]

    # Setup Mask
    if params.maskval:
        setup.extend(prep_mask_v(params.maskval, test_data, params))

    lmul = lmul_override if lmul_override is not None else params.lmul
    # This must be true because above we asserted, params.lmul is not None or lmul_override is not None
    assert lmul is not None

    # Preload vd at vlmax
    vd_preloaded = False
    if params.vector_suite == "length":
        setup.extend(load_vec_reg(params.vd, params.vd_val_pointer, params, lmul=max(lmul, 1), vl_register_or_imm="x0"))
        vd_preloaded = True
        registers.remove(params.vd)

    # Whole register moves don't care about vl, so they need to be loaded at vlmax in all length suite cases
    vs2_preloaded = False
    if params.vector_suite == "length" and preload_vs2:
        setup.extend(
            load_vec_reg(params.vs2, params.vs2_val_pointer, params, lmul=max(lmul, 1), vl_register_or_imm="x0")
        )
        vs2_preloaded = True
        registers.remove(params.vs2)

    prep_lines, vl_register_or_imm = prep_base_v(test_data, params, registers)
    setup.extend(prep_lines)

    if not vd_preloaded:
        setup.extend(load_vec_reg(params.vd, params.vd_val_pointer, params, lmul=lmul_override))

    vs2_lmul = max(lmul * vs2_lmul_multiplier, 1) if not vs2_mask else 1
    if vs2_lmul == lmul or vs2_preloaded:
        vs2_lmul = None  # Don't override anything
    vs2_sew = int(params.sew * vs2_lmul_multiplier)

    if not vs2_preloaded:
        setup.extend(
            load_vec_reg(
                params.vs2,
                params.vs2_val_pointer,
                params,
                sew_override=vs2_sew,
                lmul=vs2_lmul,
            )
        )

    if vs2_lmul is not None or lmul_override is not None:  # Then we overrode lmul in the vs2 load
        setup.append(reload_vtype(params, vl_register_or_imm))
    if isinstance(vl_register_or_imm, str) and vl_register_or_imm != "x0":
        test_data.int_regs.return_register(int(vl_register_or_imm[1:]))

    if params.maskval:
        test = [f"{instr_str} v{params.vd}, v{params.vs2}, v0.t"]
    else:
        test = [f"{instr_str} v{params.vd}, v{params.vs2}"]

    if params.vector_suite == "length":
        check = [*write_sigupd_v_len(test_data, params, 1, lmul)]
    else:
        check = [*write_sigupd_v(test_data, params)]

    # This can only be released after sigupd
    if params.maskval:
        test_data.vec_regs.return_register(0)

    return (setup, test, check)
