##################################
# hazards.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Hazard coverpoint generators (cp_gpr_hazard, cp_fpr_hazard)."""

from testgen.coverpoints.coverpoints import add_coverpoint_generator
from testgen.data.test_data import TestData
from testgen.instruction_formatters import format_instruction
from testgen.utils.param_generator import generate_random_params


@add_coverpoint_generator("cp_gpr_hazard", "cp_fpr_hazard")
def make_cp_gpr_hazard(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for register hazards (RAW, WAW, WAR)."""
    # Extract hazard class from suffix (e.g., cp_gpr_hazard_r -> 'r')
    parts = coverpoint.split("_")
    haz_class = parts[-1] if len(parts) > 3 and parts[-1] in ["r", "w", "rw"] else "rw"

    test_lines: list[str] = []

    # Determine which hazard types to test
    hazard_types: list[str] = ["nohaz"]
    if "r" in haz_class:
        hazard_types.append("raw")
    if "w" in haz_class:
        hazard_types.extend(["waw", "war"])

    # Generate test cases for each hazard type
    for haz_type in hazard_types:
        for i in range(2):  # 2 test cases per hazard type
            # Generate first instruction (add) with random registers
            params_a = generate_random_params(test_data, "R")
            assert params_a.rs1 is not None and params_a.rs2 is not None and params_a.rd is not None

            # Generate second instruction with hazard relationship to A
            if haz_type == "raw":
                # Read-After-Write: B reads what A wrote. Test with both rs1 and rs2
                if i % 2 == 0:
                    params_b = generate_random_params(test_data, instr_type, rs1=params_a.rd)
                else:
                    params_b = generate_random_params(test_data, instr_type, rs2=params_a.rd)
                # For loads, we must add 0 to avoid messing up the address calculation
                if instr_type in ["L", "JR"]:
                    test_data.int_regs.return_registers([params_a.rs1, params_a.rs2])
                    params_a.rs1 = params_a.rd
                    params_a.rs2 = 0
            elif haz_type == "waw":
                # Write-After-Write: B writes same register as A
                params_b = generate_random_params(test_data, instr_type, rd=params_a.rd)
            elif haz_type == "war":
                # Write-After-Read: B writes what A read. Test with both rs1 and rs2
                if i % 2 == 0:
                    params_b = generate_random_params(test_data, instr_type, rd=params_a.rs1)
                else:
                    params_b = generate_random_params(test_data, instr_type, rd=params_a.rs2)
            elif haz_type == "nohaz":
                # No hazard: use completely independent registers
                params_b = generate_random_params(test_data, instr_type)
            else:
                raise ValueError(f"Unknown hazard type: {haz_type}")

            # Generate both instructions
            test_lines.append(f"\n# Testcase cp_gpr_hazard {haz_type} test")
            setup1, test1, check1 = format_instruction("add", "R", test_data, params_a)
            setup2, test2, check2 = format_instruction(instr_name, instr_type, test_data, params_b)

            # Run both instructions in sequence and check results
            test_lines.extend([setup1, setup2])
            test_lines.extend([test1, test2])
            if haz_type == "waw":
                # For waw, only check the result of the second instruction
                test_lines.append(check2)
            else:
                test_lines.extend([check1, check2])

            # Return used registers
            test_data.int_regs.return_registers(params_a.used_int_regs)
            test_data.int_regs.return_registers(params_b.used_int_regs)

    return test_lines
