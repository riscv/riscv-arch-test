##################################
# hazards.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""Hazard coverpoint generators (cp_gpr_hazard, cp_fpr_hazard)."""

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_instruction
from testgen.formatters.params import generate_random_params
from testgen.formatters.registry import get_instr_type_config


@add_coverpoint_generator("cp_gpr_hazard")
def make_cp_gpr_hazard(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for register hazards (RAW, WAW, WAR)."""
    tc = test_data.begin_test_chunk()
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

    tc.code = "\n".join(test_lines)
    return [test_data.end_test_chunk()]


def _fp_producer_for(instr_name: str) -> tuple[str, str]:
    """Pick an FP producer instruction whose precision matches the instruction under test."""
    if instr_name.endswith(".d"):
        return "fadd.d", "FR"
    if instr_name.endswith(".h"):
        return "fadd.h", "FR"
    if instr_name.endswith(".q"):
        return "fadd.q", "FR"
    return "fadd.s", "FR"


@add_coverpoint_generator("cp_fpr_hazard")
def make_cp_fpr_hazard(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for FP register hazards (RAW, WAW, WAR)."""
    tc = test_data.begin_test_chunk()
    parts = coverpoint.split("_")
    haz_class = parts[-1] if len(parts) > 3 and parts[-1] in ["r", "w", "rw"] else "rw"

    test_lines: list[str] = []
    hazard_types: list[str] = ["nohaz"]
    if "r" in haz_class:
        hazard_types.append("raw")
    if "w" in haz_class:
        hazard_types.extend(["waw", "war"])

    producer_instr, producer_type = _fp_producer_for(instr_name)
    consumer_required = get_instr_type_config(instr_type).required_params or set()
    consumer_fp_srcs = [f for f in ("fs1", "fs2", "fs3") if f in consumer_required]
    consumer_has_fd = "fd" in consumer_required

    for haz_type in hazard_types:
        for i in range(2):
            params_a = generate_random_params(test_data, producer_type)
            assert params_a.fs1 is not None and params_a.fs2 is not None and params_a.fd is not None

            if haz_type == "raw":
                if consumer_fp_srcs:
                    src_field = consumer_fp_srcs[i % len(consumer_fp_srcs)]
                    params_b = generate_random_params(test_data, instr_type, **{src_field: params_a.fd})
                else:
                    # Consumer reads no FP source register — skip this iteration's hazard
                    # rather than emit a no-op test that pretends to cover RAW.
                    continue
            elif haz_type == "waw":
                if not consumer_has_fd:
                    continue
                params_b = generate_random_params(test_data, instr_type, fd=params_a.fd)
            elif haz_type == "war":
                if not consumer_has_fd:
                    continue
                src_of_a = params_a.fs1 if i % 2 == 0 else params_a.fs2
                params_b = generate_random_params(test_data, instr_type, fd=src_of_a)
            elif haz_type == "nohaz":
                params_b = generate_random_params(test_data, instr_type)
            else:
                raise ValueError(f"Unknown hazard type: {haz_type}")

            test_lines.append(f"\n# Testcase cp_fpr_hazard {haz_type} test")
            setup1, test1, check1 = format_instruction(producer_instr, producer_type, test_data, params_a)
            setup2, test2, check2 = format_instruction(instr_name, instr_type, test_data, params_b)

            test_lines.extend([setup1, setup2])
            test_lines.extend([test1, test2])
            if haz_type == "waw":
                test_lines.append(check2)
            else:
                test_lines.extend([check1, check2])

            test_data.float_regs.return_registers(params_a.used_float_regs)
            test_data.float_regs.return_registers(params_b.used_float_regs)
            test_data.int_regs.return_registers(params_a.used_int_regs)
            test_data.int_regs.return_registers(params_b.used_int_regs)

    tc.code = "\n".join(test_lines)
    return [test_data.end_test_chunk()]
