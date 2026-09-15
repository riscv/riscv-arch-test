##################################
# fvmvfs.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import write_sigupd
from testgen.asm.vector_helpers import (
    VectorLoad,
    handle_parameter_exclusions,
    load_test_vtype,
    load_vec_regs,
    prep_mask_v,
)
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, VectorTypeConfig, add_instruction_formatter

fvmvfs_config = InstructionTypeConfig(
    instruction_class=["vector_fp"], required_params={"fd", "vs2"}, vector_data=VectorTypeConfig(scalar_regs={"vs2"})
)


@add_instruction_formatter("FVMVFS", fvmvfs_config)
def format_fvmvfs_type(
    instr_str: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    assert params.maskval is None, "FVMVFS-Type instructions cannot be masked"
    assert params.vs2 is not None and params.vs2_val_pointer is not None, (
        "vs2 and vs2_val_pointer must be provided for FVMVFS-type instructions"
    )
    assert params.fd is not None, "fd must be provided for FVMVFS-type instructions"
    assert params.temp_reg is not None, "temp_reg must be provided for FVMVFS-type instructions"
    assert params.sew is not None, "sew must be provided for FVMVFS-type instructions"
    assert params.lmul is not None, "lmul must be provided for FVMVFS-type instructions"
    assert test_data.test_chunk is not None, "format_fvmvfs_type must be used with an active TestChunk"

    test_data.test_chunk.vector_labels.append(
        (params.vs2_val_pointer, *test_data.vector_labels[params.vs2_val_pointer])
    )

    # Set up the instructions: Mask, vs2, no need to touch fd
    setup = []

    # Setup Mask
    if params.maskval:
        setup.extend(prep_mask_v(params.maskval, test_data, params))

    # 1 for a scalar register
    load_code, random_vl_reg = load_vec_regs([VectorLoad("vs2", vl=1, lmul=1)], params, test_data)
    setup.extend(load_code)
    setup.append(load_test_vtype(params, random_vl_reg))

    # We don't need random_vl_reg anymore
    if random_vl_reg.startswith("x"):
        test_data.int_regs.return_register(int(random_vl_reg[1:]))

    if params.maskval:
        test = [f"{instr_str} f{params.fd}, v{params.vs2}, v0.t"]
    else:
        test = [f"{instr_str} f{params.fd}, v{params.vs2}"]

    check = [write_sigupd(params.fd, test_data, "float")]

    # This can only be released after sigupd
    if params.maskval:
        test_data.vec_regs.return_register(0)

    handle_parameter_exclusions(params.lmul, setup, check)
    # These moves do not need frm to be set or fflags checked

    return (setup, test, check)
