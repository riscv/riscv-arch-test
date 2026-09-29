##################################
# s_type.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import check_store_canary, fill_store_canary, int_store_data, load_int_reg
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

s_config = InstructionTypeConfig(
    required_params={"temp_reg", "rs1", "rs1val", "rs2", "rs2val", "immval"}, imm_bits=12, imm_signed=True
)


@add_instruction_formatter("S", s_config)
def format_s_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format S-type instruction."""
    assert params.rs1 is not None, "rs1 must be provided for S-type instructions"
    assert params.rs2 is not None and params.rs2val is not None, (
        "rs2 and rs2val must be provided for S-type instructions"
    )
    assert params.temp_reg is not None, "temp_reg must be provided for S-type instructions"
    assert params.immval is not None, "immval must be provided for S-type instructions"

    # Ensure rs1 is not x0 (base address)
    if params.rs1 == 0:
        test_data.int_regs.return_register(params.rs1)
        params.rs1 = test_data.int_regs.get_register(exclude_regs=[0])

    store_bytes = {"sb": 1, "sh": 2, "sw": 4, "sd": 8}[instr_name]
    store_val, known_bytes = int_store_data(params.rs2, params.rs2val, params.rs1, params.immval, store_bytes)

    # load test value and fill the store target at scratch with a canary
    setup = [
        load_int_reg("rs2", params.rs2, params.rs2val, test_data),
        *fill_store_canary(
            params.rs1,
            params.temp_reg,
            test_data,
            area_bytes=store_bytes,
            store_val=store_val,
            store_bytes=known_bytes,
        ),
    ]

    # Handle special case where offset is -2048
    if params.immval == -2048:
        setup.extend(
            [
                f"addi x{params.rs1}, x{params.rs1}, 2047 # increment by 2047",
                f"addi x{params.rs1}, x{params.rs1}, 1 # increment by 1 more for total +2048",
            ]
        )
    else:
        setup.append(f"addi x{params.rs1}, x{params.rs1}, {-params.immval} # adjust base address for offset")

    test = [f"{instr_name} x{params.rs2}, {params.immval}(x{params.rs1}) # perform store"]
    check = [
        f"addi x{params.rs1}, x{params.rs1}, {params.immval} # restore base address",
        *check_store_canary(params.rs1, params.temp_reg, test_data, area_bytes=store_bytes),
    ]
    return (setup, test, check)
