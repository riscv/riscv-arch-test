##################################
# cp_custom_sc.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_custom_sc coverpoint generator."""

from testgen.asm.helpers import load_int_reg, return_test_regs, write_sigupd
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.formatters.params import generate_random_params


@add_coverpoint_generator("cp_custom_sc")
def make_custom_sc(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for store-conditional coverpoints."""
    if instr_type != "SC":
        raise ValueError(
            f"cp_custom_sc coverpoint generator only supports SC-type instructions, got {instr_type} for {instr_name}."
        )

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
        test_lines.extend(
            [
                f"# Testcase: cp_custom_aqrl with suffix '{suffix}'",
                load_int_reg("rs2", params.rs2, params.rs2val, test_data),
                f"LA(x{params.rs1}, scratch) # rs1 = base address",
                f"{lr_insn} x0, (x{params.rs1}) # establish reservation",
                test_data.add_testcase(suffix, "cp_custom_aqrl"),
                f"{instr_name}{suffix} x{params.rd}, x{params.rs2}, (x{params.rs1}) # perform operation",
                write_sigupd(params.rd, test_data),
                f"LA(x{params.rs1}, scratch) # reload base address",
                f"LREG x{params.temp_reg}, 0(x{params.rs1}) # load stored value",
                write_sigupd(params.temp_reg, test_data),
                "",
            ]
        )
        return_test_regs(test_data, params)

    # cp_custom_sc_lrsc
    lr_insns = ["lr.w"] if test_data.xlen == 32 else ["lr.d", "lr.w"]

    for lr_insn in lr_insns:
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
                "# Testcase: cp_custom_sc_lrsc",
                load_int_reg("rs2", params.rs2, params.rs2val, test_data),
                f"LA(x{params.rs1}, scratch) # rs1 = base address",
                f"{lr_insn} x0, (x{params.rs1}) # establish reservation",
                test_data.add_testcase(f"prev_lr_{lr_insn}", "cp_custom_sc_lrsc"),
                f"{instr_name} x{params.rd}, x{params.rs2}, (x{params.rs1}) # perform operation",
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
            "# Check destination of both sc instructions:",
            write_sigupd(params.rd, test_data),
            write_sigupd(params.temp_reg, test_data),
            "# Check that stored value is from first sc:",
            f"LA(x{params.rs1}, scratch) # reload base address",
            f"LREG x{params.temp_reg}, 0(x{params.rs1}) # load stored value",
            write_sigupd(params.temp_reg, test_data),
            "",
        ]
    )
    return_test_regs(test_data, params)

    # cp_custom_sc_after_store
    # Store to interweave and the appropriate offsets
    stores = [
        ("sb", 3),
        ("sh", 2),
        ("sw", 0 if instr_name == "sc.w" else 4),
    ]
    if test_data.xlen == 64:
        stores.append(("sd", 0))

    for store_insn, offset in stores:
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
                f"# Testcase: cp_custom_sc_after_store ({store_insn})",
                load_int_reg("rs2", params.rs2, params.rs2val, test_data),
                load_int_reg("temp_reg", params.temp_reg, params.temp_val, test_data),
                f"LA(x{params.rs1}, scratch) # rs1 = base address",
                f"{lr_insn} x0, (x{params.rs1}) # establish reservation",
                f"{store_insn} x{params.temp_reg}, {offset}(x{params.rs1}) # intervening store",
                test_data.add_testcase(store_insn, "cp_custom_sc_after_store"),
                f"{instr_name} x{params.rd}, x{params.rs2}, (x{params.rs1}) # perform operation",
                write_sigupd(params.rd, test_data),
                f"LA(x{params.rs1}, scratch) # reload base address",
                f"LREG x{params.temp_reg}, 0(x{params.rs1}) # load stored value",
                write_sigupd(params.temp_reg, test_data),
                "",
            ]
        )
        return_test_regs(test_data, params)

    # cp_custom_sc_after_load
    # Store to interweave and the appropriate offsets
    loads = [
        ("lb", 3),
        ("lb", 128),
        ("lbu", 2),
        ("lbu", 128),
        ("lh", 2),
        ("lh", 128),
        ("lhu", 0),
        ("lhu", 128),
        ("lw", 0),
        ("lw", 128),
    ]
    if test_data.xlen == 64:
        loads.extend(
            [
                ("lwu", 0),
                ("lwu", 128),
                ("ld", 0),
                ("ld", 128),
            ]
        )

    for load_insn, offset in loads:
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
                f"# Testcase: cp_custom_sc_after_load ({load_insn}, offset = {offset})",
                load_int_reg("rs2", params.rs2, params.rs2val, test_data),
                load_int_reg("temp_reg", params.temp_reg, params.temp_val, test_data),
                f"LA(x{params.rs1}, scratch) # rs1 = base address",
                f"{lr_insn} x0, (x{params.rs1}) # establish reservation",
                f"{load_insn} x{params.temp_reg}, {offset}(x{params.rs1}) # intervening load",
                test_data.add_testcase(f"{load_insn}_offset_{offset}", "cp_custom_sc_after_load"),
                f"{instr_name} x{params.rd}, x{params.rs2}, (x{params.rs1}) # perform operation",
                write_sigupd(params.rd, test_data),
                f"LA(x{params.rs1}, scratch) # reload base address",
                f"LREG x{params.temp_reg}, 0(x{params.rs1}) # load stored value",
                write_sigupd(params.temp_reg, test_data),
                "",
            ]
        )
        return_test_regs(test_data, params)

    # cp_custom_sc_addresses
    lr_insns = ["lr.w"] if test_data.xlen == 32 else ["lr.d", "lr.w"]

    for lr_insn in lr_insns:
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
                    test_data.add_testcase(
                        f"prev_lr_{lr_insn} & address_difference_{addr_diff}", "cp_custom_sc_addresses"
                    ),
                    f"{instr_name} x{params.rd}, x{params.rs2}, (x{params.rs1}) # perform operation",
                    write_sigupd(params.rd, test_data),
                    f"LA(x{params.rs1}, scratch) # reload base address",
                    f"LREG x{params.temp_reg}, {addr_diff}(x{params.rs1}) # load stored value",
                    write_sigupd(params.temp_reg, test_data),
                    "",
                ]
            )
            return_test_regs(test_data, params)

    return test_lines
