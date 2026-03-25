#################################
# cmp_values.py

# aman.murad@10xengineers.ai Mar 2026
# SPDX-License-Identifier: Apache-2.0
#################################

"""Compare register values coverpoint generators (cmp_rd_rs1_val_eq, cmp_rd_rs1_val_lsb, cmp_rd_rs1_val_hw, cmp_rd_rs1_val_w, cmp_rd_rs1_val_d, cmp_rd_rs1_pair_full_val, cmp_rd_rs1_pair_partial_val, cmp_rd_rs1_sign_ext)."""

from testgen.asm.helpers import return_test_regs, load_int_reg
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData 
from testgen.data.test_chunk import TestChunk
from testgen.formatters.params import generate_random_params
from testgen.data.random import random_range
from testgen.formatters.registry import format_instruction

def generate_cmp_testcase(instr_name: str, instr_type: str, test_data: TestData, coverpoint: str, desc: str, bin_name: str, rd_val: int, rs1_val: int, load_rd: bool = True,) -> TestChunk:
    """Generate a generic compare test case for CAS instructions"""

    # Allocate registers and generate params
    params = generate_random_params(
        test_data,
        instr_type,
        exclude_regs=[0],
        rdval=rd_val,
        rs1val=rs1_val,
    )

    rd, rs1, rs2 = params.rd, params.rs1, params.rs2

    # Begin testcase
    tc = test_data.begin_test_chunk()
    lines = [f"# Testcase {desc}"]

    # Add coverage bin label
    label_line = test_data.add_testcase(bin_name, coverpoint)

    # load value into rd register (Optinal for sign ext case)
    if load_rd:
        lines.append(load_int_reg("rd compare value", rd, rd_val, test_data))

    # Allocate a temporary register for memory initialization
    temp = test_data.int_regs.get_register(exclude_regs=[rd, rs1, rs2, 0])
    lines.append(load_int_reg("memory init", temp, rs1_val, test_data))
    lines.append(f"\tLA(x{rs1}, scratch)")
    lines.append(f"\tSREG x{temp}, 0(x{rs1})")

    # Generate instruction, setup, test, and check lines
    setup, test, check = format_instruction(instr_name, instr_type, test_data, params)
    lines += [setup, label_line, test, check]

    # Assign code and end testcase
    tc.code = "\n".join(lines)
    tc = test_data.end_test_chunk()

    # Cleanup temporary allocations
    return_test_regs(test_data, params)
    test_data.int_regs.return_register(temp)

    return tc

def generate_masked_values(rd_val: int, mask: int, all_ones: int, equal_case: bool):
    """Generate rs1_val such that masked bits match or mismatch rd_val."""

    rd_masked = rd_val & mask  # Extract the masked bits

    if equal_case:
        # Keep masked bits same, randomize upper bits
        upper = random_range(0, all_ones) & ~mask
        rs1_val = upper | rd_masked
    else:
        # Generate a masked bits different from rd_vals
        new_masked = random_range(0, mask)
        while new_masked == rd_masked:
            new_masked = random_range(0, mask)

        rs1_val = (rd_val & ~mask) | new_masked

    return rs1_val

@add_coverpoint_generator("cmp_rd_rs1_val_eq")
def make_cmp_rd_rs1_val_eq(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate CAS tests where rd value is equal to or not equal to the memory value (rs1)."""

    test_chunks = []
    all_ones = (1 << test_data.xlen) - 1

    # two bins: equal and not-equal
    for equal_case in [True, False]:

        rd_val = random_range(0, all_ones)

        if equal_case:
            rs1_val = rd_val
            desc = f"{coverpoint} (rd_val == mem_val)"
            bin_name = "equal"
        else:
            rs1_val = random_range(0, all_ones)
            while rs1_val == rd_val:
                rs1_val = random_range(0, all_ones)

            desc = f"{coverpoint} (rd_val != mem_val)"
            bin_name = "not_equal"

        tc = generate_cmp_testcase(instr_name, instr_type, test_data, coverpoint, desc, bin_name, rd_val, rs1_val)

        test_chunks.append(tc)

    return test_chunks

@add_coverpoint_generator("cmp_rd_rs1_val_lsb")
def make_cmp_rd_rs1_val_lsb(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate CAS tests where the least significant byte of rd value is equal to or not equal to the least significant byte of the memory value (rs1)."""

    test_chunks = []
    all_ones = (1 << test_data.xlen) - 1
    mask = 0xFF

    for equal_case in [True, False]:

        rd_val = random_range(0, all_ones)
        rs1_val = generate_masked_values(rd_val, mask, all_ones, equal_case)

        desc = f"{coverpoint} (rd_val[7:0] {'==' if equal_case else '!='} mem_val[7:0])"
        bin_name = "equal" if equal_case else "not_equal"

        tc = generate_cmp_testcase(instr_name, instr_type, test_data, coverpoint, desc, bin_name, rd_val, rs1_val)

        test_chunks.append(tc)

    return test_chunks


@add_coverpoint_generator("cmp_rd_rs1_val_hw")
def make_cmp_rd_rs1_val_hw(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate CAS tests where the least significant half-word of rd value is equal to or not equal to the least significant half-word of the memory value (rs1)."""

    test_chunks = []
    all_ones = (1 << test_data.xlen) - 1
    mask = 0xFFFF

    for equal_case in [True, False]:

        rd_val = random_range(0, all_ones)
        rs1_val = generate_masked_values(rd_val, mask, all_ones, equal_case)

        desc = f"{coverpoint} (rd_val[15:0] {'==' if equal_case else '!='} mem_val[15:0])"
        bin_name = "equal" if equal_case else "not_equal"

        tc = generate_cmp_testcase(instr_name, instr_type, test_data, coverpoint, desc, bin_name, rd_val, rs1_val)

        test_chunks.append(tc)

    return test_chunks

@add_coverpoint_generator("cmp_rd_rs1_val_w")
def make_cmp_rd_rs1_val_w(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate CAS tests where the least significant word of rd value is equal to or not equal to the least significant word of the memory value (rs1)."""

    test_chunks: list[TestCase] = []
    all_ones = (1 << test_data.xlen) - 1
    mask = 0xFFFFFFFF

    for equal_case in [True, False]:

        rd_val = random_range(0, all_ones)
        rs1_val = generate_masked_values(rd_val, mask, all_ones, equal_case)

        desc = f"{coverpoint} (rd_val[31:0] {'==' if equal_case else '!='} mem_val[31:0])"
        bin_name = "equal" if equal_case else "not_equal"

        tc = generate_cmp_testcase(instr_name, instr_type, test_data, coverpoint, desc, bin_name, rd_val, rs1_val)

        test_chunks.append(tc)

    return test_chunks

@add_coverpoint_generator("cmp_rd_rs1_val_d")
def make_cmp_rd_rs1_val_d(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate CAS tests where the lower double word of rd value is equal to or not equal to the lower double word of the memory value (rs1)."""

    if test_data.xlen != 64 or instr_name != "amocas.q":
        return []
        
    test_chunks = []

    all_ones = (1 << test_data.xlen) - 1

    rd_lo = random_range(0, all_ones)
    rd_hi = random_range(0, all_ones)

    mem_hi = random_range(0, all_ones)
    while mem_hi == rd_hi:
        mem_hi = random_range(0, all_ones)

    rd_val = (rd_hi << 64) | rd_lo
    rs1_val = (mem_hi << 64) | rd_lo

    desc = f"{coverpoint} (lower 64 equal, upper mismatch)"
    bin_name = "partial_d_match"

    tc = generate_cmp_testcase(instr_name, instr_type, test_data, coverpoint, desc, bin_name, rd_val, rs1_val)

    test_chunks.append(tc)

    return test_chunks

@add_coverpoint_generator("cmp_rd_rs1_pair_full_val")
def make_cmp_rd_rs1_pair_full_val(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """  """

    if test_data.xlen not in [32, 64] or instr_name not in ["amocas.q", "amocas.d"] or instr_type != "AP":
        return []
        
    test_chunks = []

    all_ones = (1 << test_data.xlen) - 1

    rd_lo = random_range(0, all_ones)
    rd_hi = random_range(0, all_ones)

    rd_val = (rd_hi << test_data.xlen) | rd_lo
    rs1_val = rd_val

    desc = "full value match (rd == mem)"
    bin_name = "full_match"

    tc = generate_cmp_testcase(instr_name, instr_type, test_data, coverpoint, desc, bin_name, rd_val, rs1_val)

    test_chunks.append(tc)

    return test_chunks

@add_coverpoint_generator("cmp_rd_rs1_pair_partial_val")
def make_cmp_rd_rs1_pair_partial_val(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate tests for full register pair equality"""

    if test_data.xlen not in [32, 64] or instr_name not in ["amocas.q", "amocas.d"] or instr_type != "AP":
        return []

    test_chunks = []

    all_ones = (1 << test_data.xlen) - 1

    # lo_match: this specifies the register 1 in pair register
    # hi_match: this specifies the register 2 in pair register
    for case in ["lo_match", "hi_match"]:

        # Random value for lower register in pair
        lo = random_range(0, all_ones)
        # random value for upper register in pair
        hi = random_range(0, all_ones)

        if case == "lo_match":
            # lower register value equal, upper register value mismatch
            mem_hi = random_range(0, all_ones)
            while mem_hi == hi:
                mem_hi = random_range(0, all_ones)

            rd_val  = (hi << test_data.xlen) | lo
            rs1_val = (mem_hi << test_data.xlen) | lo

            desc = "PARTIAL VALUE (LOWER MATCH)"
            bin_name = "partial_lo"

        else:
            # upper equal, lower mismatch
            mem_lo = random_range(0, all_ones)
            while mem_lo == lo:
                mem_lo = random_range(0, all_ones)

            rd_val  = (hi << test_data.xlen) | lo
            rs1_val = (hi << test_data.xlen) | mem_lo

            desc = "PARTIAL VALUE (UPPER MATCH)"
            bin_name = "partial_hi"

        tc = generate_cmp_testcase(instr_name, instr_type, test_data, coverpoint, desc, bin_name, rd_val, rs1_val)

        test_chunks.append(tc)

    return test_chunks


@add_coverpoint_generator("cmp_rd_rs1_sign_ext")
def make_cmp_rd_rs1_sign_ext(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Generate CAS tests where rd is sign-extended from the loaded memory value (rs1)."""

    test_chunks = []

    # RV64 only, AMOCAS.W is relevant
    if test_data.xlen != 64 or instr_name != "amocas.w":
        return test_chunks

    # Select corner memory values to cover sign-extension
    corner_mem_vals = [0x00000000, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF]

    for mem_val in corner_mem_vals:

        desc = f"{coverpoint} rd sign extension"
        bin_name = f"sign_ext_match_{mem_val:08x}"

        tc = generate_cmp_testcase(instr_name, instr_type, test_data, coverpoint, desc, bin_name, 
                                   rd_val=0, rs1_val=mem_val, load_rd=False)
        
        test_chunks.append(tc)

    return test_chunks