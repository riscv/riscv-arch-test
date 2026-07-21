##################################
# mask_prod_type.py
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
    write_sigupd_v_mask_prod,
)
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, VectorTypeConfig, add_instruction_formatter

# Mask = Mask op Mask
mmm_config = InstructionTypeConfig(
    required_params={"vd", "vs1", "vs2"}, vector_data=VectorTypeConfig(mask_regs={"vd", "vs1", "vs2"})
)
# Mask = Vector op Vector
mvv_config = InstructionTypeConfig(
    required_params={"vd", "vs1", "vs2"},
    vector_data=VectorTypeConfig(
        mask_regs={"vd"},
        masked_constraints={("vs1", "v0"), ("vs2", "v0")},
    ),
)
# Mask = Vector op Integer
mvx_config = InstructionTypeConfig(
    required_params={"vd", "rs1", "vs2"},
    vector_data=VectorTypeConfig(mask_regs={"vd"}, masked_constraints={("vs2", "v0")}),
)
# Mask = Vector op Immediate
mvi_config = InstructionTypeConfig(
    required_params={"vd", "vs2", "immval"},
    imm_bits=5,
    vector_data=VectorTypeConfig(mask_regs={"vd"}, masked_constraints={("vs2", "v0")}),
)
# Mask = Vector op Vector (carry variant, so not maskable)
mvvc_config = InstructionTypeConfig(
    required_params={"vd", "vs1", "vs2"}, vector_data=VectorTypeConfig(mask_regs={"vd"})
)
# Mask = Vector op Integer (carry variant, so not maskable)
mvxc_config = InstructionTypeConfig(
    required_params={"vd", "rs1", "vs2"}, vector_data=VectorTypeConfig(mask_regs={"vd"})
)
# Mask = Vector op Immediate (carry variant, so not maskable)
mvic_config = InstructionTypeConfig(
    required_params={"vd", "vs2", "immval"}, imm_bits=5, vector_data=VectorTypeConfig(mask_regs={"vd"})
)
# Mask = Vector op Vector op Mask
mvvm_config = InstructionTypeConfig(
    required_params={"vd", "vs1", "vs2", "maskval"},
    vector_data=VectorTypeConfig(
        mask_regs={"vd"},
        overlap_constraints={("vs2", "v0"), ("vs1", "v0")},
    ),
)
# Mask = Vector op Integer op Mask
mvxm_config = InstructionTypeConfig(
    required_params={"vd", "rs1", "vs2", "maskval"},
    vector_data=VectorTypeConfig(
        mask_regs={"vd"},
        overlap_constraints={("vs2", "v0")},
    ),
)
# Mask = Vector op Immediate op Mask
mvim_config = InstructionTypeConfig(
    required_params={"vd", "immval", "vs2", "maskval"},
    imm_bits=5,
    vector_data=VectorTypeConfig(
        mask_regs={"vd"},
        overlap_constraints={("vs2", "v0")},
    ),
)
# Mask = unary-op(Mask)
mm_config = InstructionTypeConfig(
    required_params={"vd", "vs2"},
    vector_data=VectorTypeConfig(
        mask_regs={"vd", "vs2"},
        overlap_constraints={("vd", "vs2")},
    ),
)


@add_instruction_formatter("MMM", mmm_config)
def format_mmm(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.maskval is None, "MMM-type instructions are not maskable"
    return format_mask_producing_type(instr_str, test_data, params, "MMM", {"vd", "vs1", "vs2"}, {"vd", "vs1", "vs2"})


@add_instruction_formatter("MVV", mvv_config)
def format_mvv(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_mask_producing_type(instr_str, test_data, params, "MVV", {"vd", "vs1", "vs2"}, {"vd"})


@add_instruction_formatter("MVX", mvx_config)
def format_mvx(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_mask_producing_type(instr_str, test_data, params, "MVX", {"vd", "rs1", "vs2"}, {"vd"})


@add_instruction_formatter("MVI", mvi_config)
def format_mvi(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    return format_mask_producing_type(instr_str, test_data, params, "MVI", {"vd", "vs2", "immval"}, {"vd"})


@add_instruction_formatter("MVVC", mvvc_config)
def format_mvvc(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.maskval is None, "MVVC-type instructions are not maskable"
    return format_mask_producing_type(instr_str, test_data, params, "MVVC", {"vd", "vs1", "vs2"}, {"vd"})


@add_instruction_formatter("MVXC", mvxc_config)
def format_mvxc(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.maskval is None, "MVXC-type instructions are not maskable"
    return format_mask_producing_type(instr_str, test_data, params, "MVXC", {"vd", "rs1", "vs2"}, {"vd"})


@add_instruction_formatter("MVIC", mvic_config)
def format_mvic(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.maskval is None, "MVIC-type instructions are not maskable"
    return format_mask_producing_type(instr_str, test_data, params, "MVIC", {"vd", "vs2", "immval"}, {"vd"})


@add_instruction_formatter("MVVM", mvvm_config)
def format_mvvm(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.maskval is not None, "Masks are required for MVVM-type instructions"
    return format_mask_producing_type(instr_str, test_data, params, "MVVM", {"vd", "vs1", "vs2"}, {"vd"}, no_dot_t=True)


@add_instruction_formatter("MVXM", mvxm_config)
def format_mvxm(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.maskval is not None, "Masks are required for MVXM-type instructions"
    return format_mask_producing_type(instr_str, test_data, params, "MVXM", {"vd", "rs1", "vs2"}, {"vd"}, no_dot_t=True)


@add_instruction_formatter("MVIM", mvim_config)
def format_mvim(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.maskval is not None, "Masks are required for MVIM-type instructions"
    return format_mask_producing_type(
        instr_str, test_data, params, "MVIM", {"vd", "vs2", "immval"}, {"vd"}, no_dot_t=True
    )


@add_instruction_formatter("MM", mm_config)
def format_mm(instr_str: str, test_data: TestData, params: InstructionParams) -> tuple[list[str], list[str], list[str]]:
    return format_mask_producing_type(instr_str, test_data, params, "MM", {"vd", "vs2"}, {"vd", "vs2"})


def format_mask_producing_type(
    instr_str: str,
    test_data: TestData,
    params: InstructionParams,
    type_name: str,
    registers: set[str],
    mask_registers: set[str],
    *,
    no_dot_t: bool = False,
) -> tuple[list[str], list[str], list[str]]:
    assert params.temp_reg is not None, f"temp_reg must provided for be {type_name}-type instructions"
    assert params.sew is not None, f"sew must provided for be {type_name}-type instructions"
    assert params.lmul is not None, f"lmul must provided for be {type_name}-type instructions"
    assert test_data.test_chunk is not None, f"format_{type_name.lower()}_type must be used with an active TestChunk"

    assert params.vd is not None and params.vs2 is not None, (
        f"vd and vs2 must be provided for {type_name}-type instructions"
    )
    vec_regs_to_setup = [params.vd, params.vs2]
    if "vs1" in registers:
        assert params.vs1 is not None, f"vs1 must be provided for {type_name}-type instructions"
        vec_regs_to_setup.append(params.vs1)

    setup = []

    # Setup Mask
    if params.maskval:
        setup.extend(prep_mask_v(params.maskval, test_data, params, clobber_vd=True, vd_v0=params.vd == 0))
        if 0 in vec_regs_to_setup:
            vec_regs_to_setup.remove(0)

    # vl_register_or_imm is useful if we ever overwrite vl as it allows us to easily restore it
    prep_lines, vl_register_or_imm = prep_base_v(test_data, params, vec_regs_to_setup)
    setup.extend(prep_lines)

    testline = f"{instr_str} "

    #########
    # Load vd as a mask, unless it is v0
    #########
    mask_copy_reg = None  # In length suite, when vd = v0 we need a copy of the mask
    if not (params.maskval is not None and params.vd == 0):
        assert params.vd is not None and params.vd_val_pointer is not None, (
            f"vd and vd_val_pointer must be provided for {type_name}-type instructions"
        )
        assert "vd" in mask_registers, f"vd must be a mask register for {type_name}-type instructions"
        setup.extend(
            load_vec_reg(
                params.vd,
                params.vd_val_pointer,
                params,
                lmul=1,
                vl_register_or_imm="x0",
            )
        )
        test_data.test_chunk.vector_labels.append(
            (params.vd_val_pointer, *test_data.vector_labels[params.vd_val_pointer]),
        )
    elif params.vector_suite == "length" and params.maskval is not None:
        mask_copy_reg = test_data.vec_regs.get_register(lmul=1)
        setup.extend(
            [
                "# Because vd = v0, we will not overwrite it with a mask value, instead because the",
                f"# operation will overwrite v0, we will store a copy of the mask in v{mask_copy_reg}",
                f"vmand.mm v{mask_copy_reg}, v0, v0",
            ]
        )
    testline += f"v{params.vd}"

    ##############
    # Load vs2, and respect it if it is used as a mask
    #############
    assert params.vs2 is not None and params.vs2_val_pointer is not None, (
        f"vs2 and vs2_val_pointer must be provided for {type_name}-type instructions"
    )
    assert "vs2" in registers, "VS2 must be in registers for a mask producing operation"
    vs2_lmul = 1 if "vs2" in mask_registers else max(params.lmul, 1)
    vs2_vl = "x0" if "vs2" in mask_registers else vl_register_or_imm
    setup.extend(
        load_vec_reg(
            params.vs2,
            params.vs2_val_pointer,
            params,
            lmul=vs2_lmul,
            vl_register_or_imm=vs2_vl,
        )
    )
    test_data.test_chunk.vector_labels.append(
        (params.vs2_val_pointer, *test_data.vector_labels[params.vs2_val_pointer]),
    )
    testline += f", v{params.vs2}"

    ###############
    # Load the third operand (rs1 or vs1)
    ###############
    if "vs1" in registers:
        assert params.vs1 is not None and params.vs1_val_pointer is not None, (
            f"vs1 and vs1_val_pointer must be provided for {type_name}-type instructions"
        )
        vs1_lmul = 1 if "vs1" in mask_registers else max(params.lmul, 1)
        vs1_vl = "x0" if "vs1" in mask_registers else vl_register_or_imm
        setup.extend(load_vec_reg(params.vs1, params.vs1_val_pointer, params, lmul=vs1_lmul, vl_register_or_imm=vs1_vl))
        test_data.test_chunk.vector_labels.append(
            (params.vs1_val_pointer, *test_data.vector_labels[params.vs1_val_pointer]),
        )
        testline += f", v{params.vs1}"
    elif "rs1" in registers:
        assert params.rs1 is not None and params.rs1val is not None, (
            f"rs1 and rs1val must be provided for {type_name}-type instructions"
        )
        setup.append(f"LI (x{params.rs1}, {params.rs1val})")
        testline += f", x{params.rs1}"
    elif "immval" in registers:
        assert params.immval is not None, f"immval must be provided for {type_name}-type instructions"
        testline += f", {params.immval}"
    # MM operations don't have a third operand

    # Ensure vtype is correct for the instruction
    setup.append(reload_vtype(params, vl_register_or_imm))

    if params.maskval and not no_dot_t:
        test = [f"{testline}, v0.t"]
    elif params.maskval:
        test = [f"{testline}, v0"]
    else:
        test = [testline]

    if params.vector_suite == "length":
        mask_reg = 0 if mask_copy_reg is None else mask_copy_reg
        recover_mask = []

        if mask_reg != 0:
            recover_mask = [f"vmand.mm v0, v{mask_reg}, v{mask_reg}"]

        check = [
            *write_sigupd_v_len(test_data, params, 1, lmul=1, mask_producing=True, mask_reg=mask_reg),
            "# After a length suite sigupd, we need to do the operation as if vl=vlmax as that is a valid behavior",
            "# in the tail, according to the spec. None of the registers involved in the operation could have been",
            "# clobbered in the sigupd, however, in the case of a masked instruction with vd = v0, v0 was overwritten.",
            "# So, we may have to recover that value.",
            *recover_mask,
            reload_vtype(params, "x0"),
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

    # Now we are done with the vl register
    if isinstance(vl_register_or_imm, str) and vl_register_or_imm != "x0":
        test_data.int_regs.return_register(int(vl_register_or_imm[1:]))

    return (setup, test, check)
