##################################
# cp_custom_vls.py
#
# rwolk@hmc.edu July 2026
# SPDX-License-Identifier: Apache-2.0
##################################

import math

from testgen.asm.helpers import write_sigupd
from testgen.constants import VLEN_MAX
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_instruction, format_single_testcase
from testgen.instructions.vector import parse_instruction_info
from testgen.instructions.vector_params import generate_random_vector_params


@add_coverpoint_generator("cp_custom_ffLS_update_vl")
def make_cp_custom_ffLS_update_vl(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """
    Coverpoint that generates a test where an exception is raised, causing a change in vl to be observed.

    The test achieves this by running a load at rs1=0x0, with element 0 masked so that a trap is not taken.
    """

    suffix = coverpoint[len("cp_custom_ffLS_update_vl") :]
    min_sew = int(suffix[len("_sew_ge") :]) if suffix.startswith("_sew_ge") else 0

    assert test_data.config.sew is not None, "SEW must be provided for vector instructions"
    if test_data.config.sew < min_sew:
        return []

    # Use LMUL=2 (while ensuring EMUL does not exceed 8)
    lmul = 2

    info = parse_instruction_info(instr_name, instr_type)
    eew = info.load_store_eew
    assert eew is not None, f"Could not extract eew from fault-only-first instruction {instr_name}"
    emul = eew * lmul / test_data.config.sew

    assert emul * info.segments <= 8, f"Cannot cover {coverpoint} for {instr_name}, given instruction constraints"

    mask_label = "ffLS_update_vl_mask"
    mask_elements = [0 for _ in range(math.ceil(VLEN_MAX / test_data.config.sew))]
    mask_elements[0] = 1
    test_data.register_vector_data(mask_label, test_data.config.sew, elements=mask_elements)
    params = generate_random_vector_params(
        test_data, instr_name, instr_type, lmul, masked=True, maskval=mask_label, vl="vlmax", suite="length"
    )

    # Do the test chunk manually as we need to override the check
    # tc = test_data.begin_test_chunk()
    # tc.code.append(f"# Testcase fault-only-first updates vl")

    # label_line = test_data.add_testcase("", coverpoint)

    # # Add test and signature update lines
    # setup, test, check = format_instruction(instr_name, instr_type, test_data, params)

    # tc.sigupd_count = 1
    # check_reg = test_data.int_regs.get_register(exclude_regs=[0])
    # check = [
    #     f"csrr x{check_reg}, vl",
    #     write_sigupd(check_reg, test_data, "int")
    # ]

    # if setup:
    #     tc.code.append(setup)
    # tc.code.extend(
    #     [
    #         label_line,
    #         test,
    #     ]
    # )
    # tc.code.extend(check)

    # tc = test_data.end_test_chunk()

    # test_data.int_regs.return_register(check_reg)
    tc = format_single_testcase(instr_name, instr_type, test_data, params, "ffLS update vl", "", coverpoint)
    return_testcase_registers(test_data, params)

    return [tc]


@add_coverpoint_generator("cp_custom_ffLS")
def make_cp_custom_ffLS(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Coverpoint that generates a test where an exception is raised, causing a change in vl to be observed.

    The test achieves this by running a load at rs1=0x0, with element 0 masked so that a trap is not taken.
    """

    suffix = coverpoint[len("cp_custom_ffLS_update_vl") :]
    min_sew = int(suffix[len("_sew_ge") :]) if suffix.startswith("_sew_ge") else 0

    assert test_data.config.sew is not None, "SEW must be provided for vector instructions"
    if test_data.config.sew < min_sew:
        return []

    # Use LMUL=2 (while ensuring EMUL does not exceed 8)
    lmul = 2

    info = parse_instruction_info(instr_name, instr_type)
    eew = info.load_store_eew
    assert eew is not None, f"Could not extract eew from fault-only-first instruction {instr_name}"
    emul = eew * lmul / test_data.config.sew

    # We might need an ifdef if vl=1 is vlmax (on lmul = 1, which could be required (e.g. 8 segments))
    ifdef = f"UDB_ZVL{eew * 2}B_SUPPORTED" if emul * info.segments > 8 else ""
    if emul * info.segments > 8:
        lmul = 1
        emul = eew * lmul / test_data.config.sew

    mask_label = "ffLS_mask"
    mask_elements = [0 for _ in range(math.ceil(VLEN_MAX / test_data.config.sew))]
    mask_elements[0] = 2
    test_data.register_vector_data(mask_label, test_data.config.sew, elements=mask_elements)
    params = generate_random_vector_params(
        test_data, instr_name, instr_type, lmul, masked=True, maskval=mask_label, vl="vlmax", suite="length"
    )

    # Do the test chunk manually as we need to override the check
    tc = test_data.begin_test_chunk()
    tc.code.append("# Testcase fault-only-first updates vl")

    label_line = test_data.add_testcase("", coverpoint)

    # Add test and signature update lines
    setup, test, check = format_instruction(instr_name, instr_type, test_data, params)

    tc.sigupd_count = 1
    check_reg = test_data.int_regs.get_register(exclude_regs=[0])
    check = "\n".join([f"csrr x{check_reg}, vl", write_sigupd(check_reg, test_data, "int")])

    setup += f"\nLI (x{params.rs1}, 0)"  # Hardcode the load

    tc.code.extend([setup, label_line, test, check])

    if ifdef != "":
        tc.code.insert(0, f"#ifdef {ifdef}")
        tc.code.append("#endif")

    tc = test_data.end_test_chunk()

    test_data.int_regs.return_register(check_reg)
    return_testcase_registers(test_data, params)

    return [tc]
