##################################
# cp_custom_sc.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_custom_sc coverpoint generator."""

from testgen.asm.helpers import load_int_reg, return_test_regs, write_sigupd
from testgen.constants import INDENT
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters.params import generate_random_params


@add_coverpoint_generator("cp_custom_sc")
def make_custom_sc(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for store-conditional coverpoints."""
    if instr_type != "SC":
        raise ValueError(
            f"cp_custom_sc coverpoint generator only supports SC-type instructions, got {instr_type} for {instr_name}."
        )

    tc = test_data.begin_test_chunk()
    lr_insn = "lr.w" if instr_name.endswith(".w") else "lr.d"
    test_lines: list[str] = []

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
        label = test_data.current_testcase_label
        retry_label = f"{label}_retry"
        success_label = f"{label}_success"
        test_lines.extend(
            [
                f"# Testcase: cp_custom_aqrl with suffix '{suffix}'",
                load_int_reg("rs2", params.rs2, params.rs2val, test_data),
                f"LA(x{params.rs1}, scratch) # rs1 = base address",
                f"LI(x{params.temp_reg}, 100) # retry counter for constrained LR/SC loop",
                f"{retry_label}:",
                f"{lr_insn} x0, (x{params.rs1}) # establish reservation",
                label_line,
                f"{instr_name}{suffix} x{params.rd}, x{params.rs2}, (x{params.rs1}) # perform operation",
                f"beqz x{params.rd}, {success_label} # SC succeeded, skip retry",
                f"addi x{params.temp_reg}, x{params.temp_reg}, -1 # decrement retry count",
                f"bnez x{params.temp_reg}, {retry_label} # retry LR/SC if not exhausted",
                f"{success_label}:",
                write_sigupd(params.rd, test_data),
                f"LA(x{params.rs1}, scratch) # reload base address",
                f"LREG x{params.temp_reg}, 0(x{params.rs1}) # load stored value",
                write_sigupd(params.temp_reg, test_data),
                "",
            ]
        )
        return_test_regs(test_data, params)

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
    sc_lr_label = test_data.current_testcase_label
    sc_lr_retry_label = f"{sc_lr_label}_retry"
    sc_lr_success_label = f"{sc_lr_label}_success"
    test_lines.extend(
        [
            f"# Testcase: cp_custom_sc_lr with prev {lr_insn}",
            load_int_reg("rs2", params.rs2, params.rs2val, test_data),
            f"LA(x{params.rs1}, scratch) # rs1 = base address",
            f"LI(x{params.temp_reg}, 100) # retry counter for constrained LR/SC loop",
            f"{sc_lr_retry_label}:",
            f"{lr_insn} x0, (x{params.rs1}) # establish reservation",
            sc_lr_label_line,
            f"{instr_name} x{params.rd}, x{params.rs2}, (x{params.rs1}) # perform operation",
            f"beqz x{params.rd}, {sc_lr_success_label} # SC succeeded, skip retry",
            f"addi x{params.temp_reg}, x{params.temp_reg}, -1 # decrement retry count",
            f"bnez x{params.temp_reg}, {sc_lr_retry_label} # retry LR/SC if not exhausted",
            f"{sc_lr_success_label}:",
            write_sigupd(params.rd, test_data),
            f"LA(x{params.rs1}, scratch) # reload base address",
            f"LREG x{params.temp_reg}, 0(x{params.rs1}) # load stored value",
            write_sigupd(params.temp_reg, test_data),
            "",
        ]
    )
    test_lines.extend(
        [
            f"# Testcase: cp_custom_sc_lr with prev {lr_insn} first to matching address and then to a different address",
            "# This test is not described with a coverpoint because it involves three consecutive instructions",
            "#  Addresses sc_pairs_latest_lr normative rule",
            load_int_reg("rs2", params.rs2, params.rs2val, test_data),
            f"LA(x{params.rs1}, scratch) # rs1 = base address",
            f"{lr_insn} x0, (x{params.rs1}) # establish reservation",
            f"addi x{params.rs1}, x{params.rs1}, 256 # change reservation address",
            f"{lr_insn} x0, (x{params.rs1}) # establish reservation at a different address that should not match sc",
            f"addi x{params.rs1}, x{params.rs1}, -256 # restore reservation address",
            test_data.add_testcase(f"prev_lr_{lr_insn}_sc_pairs_latest_lrr", "cp_custom_sc_lr"),
            f"{instr_name} x{params.rd}, x{params.rs2}, (x{params.rs1}) # perform store conditional",
            write_sigupd(params.rd, test_data),
            f"LA(x{params.rs1}, scratch) # reload base address",
            f"LREG x{params.temp_reg}, 0(x{params.rs1}) # load stored value",
            write_sigupd(params.temp_reg, test_data),
            "",
        ]
    )

    return_test_regs(test_data, params)

    # cp_custom_sc_after_sc
    params = generate_random_params(test_data, instr_type, exclude_regs=[0])
    assert (
        params.rs1 is not None
        and params.rd is not None
        and params.rs2 is not None
        and params.rs2val is not None
        and params.temp_reg is not None
        and params.temp_val is not None
    )
    test_lines.extend(
        [
            "# Testcase: cp_custom_sc_after_sc (should fail because of intervening sc)",
            load_int_reg("rs2", params.rs2, params.rs2val, test_data),
            load_int_reg("temp_reg", params.temp_reg, params.temp_val, test_data),
            f"LA(x{params.rs1}, scratch) # rs1 = base address",
            f"{lr_insn} x0, (x{params.rs1}) # establish reservation",
            test_data.add_testcase("true", "cp_custom_sc_after_sc"),
            f"{instr_name} x{params.rd}, x{params.rs2}, (x{params.rs1}) # perform operation",
            f"{instr_name} x{params.temp_reg}, x{params.temp_reg}, (x{params.rs1}) # perform operation again, should fail",
            f"{INDENT}# Check destination of both sc instructions:",
            write_sigupd(params.rd, test_data),
            write_sigupd(params.temp_reg, test_data),
            f"{INDENT}# Check that stored value is from first sc:",
            f"LA(x{params.rs1}, scratch) # reload base address",
            f"LREG x{params.temp_reg}, 0(x{params.rs1}) # load stored value",
            write_sigupd(params.temp_reg, test_data),
            "",
        ]
    )
    return_test_regs(test_data, params)

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
        test_lines.extend(
            [
                f"# Testcase: cp_custom_sc_addresses (address difference of {addr_diff})",
                load_int_reg("rs2", params.rs2, params.rs2val, test_data),
                f"LA(x{params.temp_reg}, scratch) # rs1 = base address",
                f"addi x{params.rs1}, x{params.temp_reg}, {addr_diff} # offset rs1 by {addr_diff}",
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
        return_test_regs(test_data, params)

    tc.code = "\n".join(test_lines)
    return [test_data.end_test_chunk()]
