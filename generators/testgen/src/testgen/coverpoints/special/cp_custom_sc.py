##################################
# cp_custom_sc.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_custom_sc coverpoint generator."""

from testgen.asm.helpers import load_int_reg, write_sigupd
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters.types.sc_type import sc_canary, sc_retry_loop
from testgen.instructions.params import generate_random_params


@add_coverpoint_generator("cp_custom_sc")
def make_custom_sc(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for store-conditional coverpoints."""
    if instr_type != "SC":
        raise ValueError(
            f"cp_custom_sc coverpoint generator only supports SC-type instructions, got {instr_type} for {instr_name}."
        )

    tc = test_data.begin_test_chunk()
    lr_insn = "lr.w" if instr_name.endswith(".w") else "lr.d"

    # cp_custom_aqrl
    for suffix in ["", ".rl", ".aqrl"]:
        params = generate_random_params(test_data, instr_type, exclude_regs=[0])
        assert (
            params.rs1 is not None
            and params.rd is not None
            and params.rs2 is not None
            and params.rs2val is not None
            and params.temp_reg is not None
        )
        label_line = test_data.add_testcase(suffix, "cp_custom_aqrl")
        setup, test, check = sc_retry_loop(
            f"{instr_name}{suffix}",
            lr_insn,
            test_data,
            rd=params.rd,
            rs1=params.rs1,
            rs2=params.rs2,
            rs2val=params.rs2val,
            temp_reg=params.temp_reg,
        )
        tc.code.extend([f"# Testcase: cp_custom_aqrl with suffix '{suffix}'", *setup, label_line, *test, *check, ""])
        return_testcase_registers(test_data, params)

    # cp_custom_sc_lr
    # only test matching lr and sc widths because it is undefined whether nonmatching ones will succeed
    lr_insn = "lr.w" if instr_name == "sc.w" else "lr.d"

    params = generate_random_params(test_data, instr_type, exclude_regs=[0])
    assert (
        params.rs1 is not None
        and params.rd is not None
        and params.rs2 is not None
        and params.rs2val is not None
        and params.temp_reg is not None
    )
    sc_lr_label_line = test_data.add_testcase(f"prev_lr_{lr_insn}", "cp_custom_sc_lr")
    setup, test, check = sc_retry_loop(
        instr_name,
        lr_insn,
        test_data,
        rd=params.rd,
        rs1=params.rs1,
        rs2=params.rs2,
        rs2val=params.rs2val,
        temp_reg=params.temp_reg,
    )
    tc.code.extend([f"# Testcase: cp_custom_sc_lr with prev {lr_insn}", *setup, sc_lr_label_line, *test, *check, ""])
    return_testcase_registers(test_data, params)

    # sc_pairs_latest_lr: fresh operands, so the SC's value differs from what the previous testcase stored
    params = generate_random_params(test_data, instr_type, exclude_regs=[0])
    assert (
        params.rs1 is not None
        and params.rd is not None
        and params.rs2 is not None
        and params.rs2val is not None
        and params.temp_reg is not None
    )
    tc.code.extend(
        [
            f"# Testcase: cp_custom_sc_lr with prev {lr_insn} first to matching address and then to a different address",
            "# This test is not described with a coverpoint because it involves three consecutive instructions",
            "#  Addresses sc_pairs_latest_lr normative rule: the SC must fail and must not write memory",
            load_int_reg("rs2", params.rs2, params.rs2val, test_data),
            f"LA(x{params.rs1}, scratch) # rs1 = base address",
            *sc_canary(params.rs1, params.rs2, params.temp_reg),
            f"{lr_insn} x0, (x{params.rs1}) # establish reservation",
            f"addi x{params.rs1}, x{params.rs1}, 256 # change reservation address",
            f"{lr_insn} x0, (x{params.rs1}) # establish reservation at a different address that should not match sc",
            f"addi x{params.rs1}, x{params.rs1}, -256 # restore reservation address",
            test_data.add_testcase(f"prev_lr_{lr_insn}_sc_pairs_latest_lrr", "cp_custom_sc_lr"),
            f"{instr_name} x{params.rd}, x{params.rs2}, (x{params.rs1}) # perform store conditional",
            write_sigupd(params.rd, test_data),
            f"LA(x{params.rs1}, scratch) # reload base address",
            f"LREG x{params.temp_reg}, 0(x{params.rs1}) # load target: must still hold the canary",
            write_sigupd(params.temp_reg, test_data),
            "",
        ]
    )
    return_testcase_registers(test_data, params)

    # cp_custom_sc_after_sc
    # The first SC goes to a different word than the LR, so its outcome may vary and is not checked.
    # Any SC invalidates the reservation, so the second SC must fail and leave the canary in place
    # whether or not the first one succeeded.
    params = generate_random_params(test_data, instr_type, exclude_regs=[0])
    assert (
        params.rs1 is not None
        and params.rd is not None
        and params.rs2 is not None
        and params.rs2val is not None
        and params.temp_reg is not None
    )
    tc.code.extend(
        [
            "# Testcase: cp_custom_sc_after_sc (should fail because of intervening sc)",
            load_int_reg("rs2", params.rs2, params.rs2val, test_data),
            f"LA(x{params.rs1}, scratch) # rs1 = base address",
            *sc_canary(params.rs1, params.rs2, params.temp_reg),
            f"addi x{params.temp_reg}, x{params.rs1}, 8 # address for the first sc: a different word",
            f"{lr_insn} x0, (x{params.rs1}) # establish reservation",
            f"{instr_name} x{params.temp_reg}, x{params.rs2}, (x{params.temp_reg}) # intervening sc; outcome not checked",
            test_data.add_testcase("true", "cp_custom_sc_after_sc"),
            f"{instr_name} x{params.rd}, x{params.rs2}, (x{params.rs1}) # sc after sc, must fail",
            write_sigupd(params.rd, test_data),
            f"LA(x{params.rs1}, scratch) # reload base address",
            f"LREG x{params.temp_reg}, 0(x{params.rs1}) # load target: must still hold the canary",
            write_sigupd(params.temp_reg, test_data),
            "",
        ]
    )
    return_testcase_registers(test_data, params)

    # cp_custom_sc_addresses
    lr_insn = "lr.w" if instr_name == "sc.w" else "lr.d"

    for addr_diff in range(8, 256, 8):
        params = generate_random_params(test_data, instr_type, exclude_regs=[0])
        assert (
            params.rs1 is not None
            and params.rd is not None
            and params.rs2 is not None
            and params.rs2val is not None
            and params.temp_reg is not None
        )
        canary_reg = test_data.int_regs.get_register(
            exclude_regs=[0, params.rd, params.rs1, params.rs2, params.temp_reg]
        )
        tc.code.extend(
            [
                f"# Testcase: cp_custom_sc_addresses (address difference of {addr_diff})",
                load_int_reg("rs2", params.rs2, params.rs2val, test_data),
                f"LA(x{params.temp_reg}, scratch) # rs1 = base address",
                f"addi x{params.rs1}, x{params.temp_reg}, {addr_diff} # offset rs1 by {addr_diff}",
                *sc_canary(params.temp_reg, params.rs2, canary_reg, addr_diff),
                f"{lr_insn} x0, (x{params.temp_reg}) # establish reservation",
                test_data.add_testcase(f"prev_lr_{lr_insn} & address_difference_{addr_diff}", "cp_custom_sc_addresses"),
                f"{instr_name} x{params.rd}, x{params.rs2}, (x{params.rs1}) # perform operation",
                write_sigupd(params.rd, test_data),
                f"LA(x{params.rs1}, scratch) # reload base address",
                f"LREG x{params.temp_reg}, {addr_diff}(x{params.rs1}) # load stored value",
                write_sigupd(params.temp_reg, test_data),
                "",
            ]
        )
        test_data.int_regs.return_register(canary_reg)
        return_testcase_registers(test_data, params)

    return [test_data.end_test_chunk()]
