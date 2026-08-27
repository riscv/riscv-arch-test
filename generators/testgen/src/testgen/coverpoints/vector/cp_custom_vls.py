##################################
# cp_custom_vls.py
#
# rwolk@hmc.edu July 2026
# SPDX-License-Identifier: Apache-2.0
##################################

import math
import re

from testgen.asm.helpers import write_sigupd
from testgen.constants import VLEN_MAX
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_instruction, format_single_testcase, get_instruction_type_config
from testgen.instructions.vector import parse_vector_instruction_info
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

    info = parse_vector_instruction_info(instr_name, instr_type)
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

    info = parse_vector_instruction_info(instr_name, instr_type)
    eew = info.load_store_eew
    assert eew is not None, f"Could not extract eew from fault-only-first instruction {instr_name}"
    emul = eew * lmul / test_data.config.sew

    # We might need an ifdef if vl=1 is vlmax (on lmul = 1, which could be required (e.g. 8 segments))
    # But, we only need it if we require a VLEN > max(32, sew) as max(32, sew) is the minimum VLEN
    ifdef = f"ZVL{eew * 2}B_SUPPORTED" if emul * info.segments > 8 and eew * 2 > max(32, test_data.config.sew) else ""
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
    needs_endif = "#endif" in check

    tc.sigupd_count = 1
    check_reg = test_data.int_regs.get_register(exclude_regs=[0])
    check = "\n".join([f"csrr x{check_reg}, vl", write_sigupd(check_reg, test_data, "int")])
    if needs_endif:
        check += "\n#endif"

    setup += f"\nLI (x{params.rs1}, 0)"  # Hardcode the load

    tc.code.extend([setup, label_line, test, check])

    if ifdef != "":
        tc.code.insert(0, f"#ifdef {ifdef}")
        tc.code.append("#endif")

    tc = test_data.end_test_chunk()

    test_data.int_regs.return_register(check_reg)
    return_testcase_registers(test_data, params)

    return [tc]


@add_coverpoint_generator("cp_custom_ls_indexed_truncated")
def make_cp_custom_ls_indexed_truncated(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """
    Runs a test confirming that at XLEN=32, INDEX EEW=64, the index values are truncated to XLEN bits.
    """

    info = parse_vector_instruction_info(instr_name, instr_type)
    eew = info.index_eew

    assert eew is not None, f"Unable to extract index-eew for instruction {instr_name}"
    assert eew == 64, f"EEW must be 64 for {coverpoint}"

    label = "custom_idx_trunc_eew64"
    test_data.register_vector_data(label, 64, elements=[0xFFFF_FFFF_0000_0000])

    params = generate_random_vector_params(
        test_data,
        instr_name,
        instr_type,
        1,
        additional_no_overlap={("vd", "vs2")},
        vs2_val_pointer=label,
        ignore_vector_safety=True,
    )
    desc = "Index Value Truncation"
    bin_name = "truncate_xlen32_eew64"

    tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
    return_testcase_registers(test_data, params)

    return [tc]


@add_coverpoint_generator("cp_custom_indexed_overlap")
def make_cp_custom_indexed_overlap(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """
    Covers vd/vs2 or vs3/vs2 overlaps for non-segment indexed load/stores.

    Valid src/dest overlaps include
        (a) EEW_dest == EEW_sew --> Always allowed
        (b) EEW_dest < EEW_src --> Overlaps are only allowed in the lowest part of the source register
        (c) EEW_dest > EEW_src, EMUL_src >= 1 --> overlap is allowed in the highest part of the dest register

    Src/src overlaps are only valid when the EEWs are the same
    """

    config = get_instruction_type_config(instr_type)
    assert "segmented" not in config.instruction_class, "Overlaps are prohibited for segmented load/stores"

    info = parse_vector_instruction_info(instr_name, instr_type)
    index_eew = info.index_eew
    assert index_eew is not None, f"Could not extract index EEW from {instr_name}"

    res = re.search(r"_eew(\d+)", coverpoint)
    if res:
        expected_eew = int(res.group(1))
        assert index_eew == expected_eew, (
            f"Extracted incorrect eew {index_eew} from {instr_name} for coverpoint {coverpoint}"
        )

    result_eew = test_data.config.sew
    assert result_eew is not None, "SEW must be provided for vector instructions"

    test_chunks = []
    for lmul in (1, 2, 4, 8):
        data_emul = lmul
        index_emul = lmul * (index_eew / result_eew)
        if index_emul > 8:
            continue  # This is an index EMUL > 8

        if result_eew == index_eew:
            # Then all overlaps are legal
            for reg in range(0, test_data.vec_regs.reg_count, lmul):
                if "store" in config.instruction_class:
                    test_data.vec_regs.allocate_operand("vs3", reg, lmul)
                    test_data.vec_regs.allocate_operand("vs2", reg, lmul, suppress_overlap=True)
                    params = generate_random_vector_params(test_data, instr_name, instr_type, lmul, vs3=reg, vs2=reg)
                else:
                    test_data.vec_regs.allocate_operand("vd", reg, lmul)
                    test_data.vec_regs.allocate_operand("vs2", reg, lmul, suppress_overlap=True)
                    params = generate_random_vector_params(test_data, instr_name, instr_type, lmul, vd=reg, vs2=reg)

                desc = "Index Register Overlap"
                bin_name = f"_v{reg}_lmul{lmul}"
                test_chunks.append(
                    format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
                )
                return_testcase_registers(test_data, params)
        elif result_eew < index_eew:
            # Then the dest is allowed to overlap the lowest part of the register
            if "store" in config.instruction_class:
                continue  # This type of overlap is illegal for src/src cases

            alignment = int(max(index_emul, data_emul))
            for reg in range(0, test_data.vec_regs.reg_count, alignment):
                test_data.vec_regs.allocate_operand("vd", reg, data_emul)
                test_data.vec_regs.allocate_operand("vs2", reg, int(max(index_emul, 1)), suppress_overlap=True)
                params = generate_random_vector_params(test_data, instr_name, instr_type, data_emul, vd=reg, vs2=reg)

                desc = "Index Register Overlap"
                bin_name = f"_v{reg}_lmul{lmul}"
                test_chunks.append(
                    format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
                )
                return_testcase_registers(test_data, params)
        else:
            # Then we have an index only at the highest part of the dest group
            if "store" in config.instruction_class:
                continue  # This type of overlap is illegal for src/src cases
            if index_emul < 1:
                continue  # This type of overlap only works with integer emul

            vs2_offset = int(data_emul - index_emul)
            assert vs2_offset > 0 and vs2_offset % index_emul == 0

            for reg in range(0, test_data.vec_regs.reg_count, data_emul):
                vs2_reg = reg + vs2_offset
                test_data.vec_regs.allocate_operand("vd", reg, data_emul)
                test_data.vec_regs.allocate_operand("vs2", vs2_reg, int(max(index_emul, 1)), suppress_overlap=True)
                params = generate_random_vector_params(
                    test_data, instr_name, instr_type, data_emul, vd=reg, vs2=vs2_reg
                )

                desc = "Index Register Overlap"
                bin_name = f"_vd_{reg}_vs2_{vs2_reg}_lmul{lmul}"
                test_chunks.append(
                    format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
                )
                return_testcase_registers(test_data, params)

    return test_chunks


@add_coverpoint_generator("cp_custom_indexed_emul_data_only")
def make_cp_custom_indexed_emul_data_only(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """
    Runs a test at the maximum lmul for an instruction, to verify that the emul * nf constraint only applies
    to the data register and not to the index register.
    """

    min_sew = 0
    if res := re.search(r"sew_ge(\d+)", coverpoint):
        min_sew = int(res.group(1))

    sew = test_data.config.sew
    assert sew is not None, "SEW must be provided for vector instructions"
    if sew < min_sew:
        return []

    info = parse_vector_instruction_info(instr_name, instr_type)
    segments = info.segments

    targets = {8: 1, 4: 2, 2: 4}  # Maps segments to the required lmul

    if segments not in targets:
        return []

    lmul = targets[segments]

    index_eew = info.index_eew
    assert index_eew is not None, f"Unable to extract index eew from {instr_name}"

    index_emul = index_eew * lmul // sew
    if index_emul > 8:
        return []  # This is just an illegal instruction

    desc = "EMUl x NF Constraint Only Applies to Data Register"
    bin_name = f"lmul_{lmul}"
    params = generate_random_vector_params(test_data, instr_name, instr_type, lmul)

    tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
    return_testcase_registers(test_data, params)

    return [tc]


@add_coverpoint_generator("cp_custom_ordered_index_overlap")
def make_cp_custom_ordered_index_overlap(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """
    Tests a data overlap in the index register for the ordered case.
    """

    assert test_data.config.sew is not None, "SEW must be set for vector instructions"
    label = "custom_index_overlap"
    test_data.register_vector_data(label, test_data.config.sew, elements=[0, 0])

    desc = "Data Overlap of Index Elements"
    bin_name = "zeros"
    params = generate_random_vector_params(
        test_data, instr_name, instr_type, 1, vl=2, suite="length", vs2_val_pointer=label
    )
    tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
    return_testcase_registers(test_data, params)

    return [tc]


@add_coverpoint_generator("cp_custom_vwholeRegLS_vill")
def make_cp_custom_vwholeRegLS_vill(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """
    Checks that whole register load/store operations are unaffected by the vill bit
    """

    desc = "Whole Register Load Store (vill=1)"
    bin_name = "1"
    params = generate_random_vector_params(test_data, instr_name, instr_type, 1, vl=2, suite="length")

    # Write the test manually so we can insert
    tc = test_data.begin_test_chunk()
    tc.code.append("# Testcase fault-only-first updates vl")

    label_line = test_data.add_testcase(bin_name, coverpoint)

    # Add test and signature update lines
    setup, test, check = format_instruction(instr_name, instr_type, test_data, params)

    vl_reg, vtype_reg = test_data.int_regs.get_registers(2, exclude_regs=[0])
    force_vill = "\n".join(
        [
            "# Force a vector configuration with vill = 1",
            f"csrr x{vl_reg}, vl",
            f"csrr x{vtype_reg}, vtype",
            f"LI (x{params.temp_reg}, {1 << (test_data.xlen - 1)})",
            f"vsetvl x0, x0, x{params.temp_reg}",
        ]
    )
    reset_vtype = f"vsetvl x0, x{vl_reg}, x{vtype_reg}"

    tc.code.extend([f"# {desc}", setup, force_vill, label_line, test, reset_vtype, check])

    test_data.int_regs.return_registers([vl_reg, vtype_reg])
    tc = test_data.end_test_chunk()
    return_testcase_registers(test_data, params)

    return [tc]


@add_coverpoint_generator("cp_custom_vwholeRegLS_lmul")
def make_cp_custom_vwholeRegLS_lmul(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """
    Check that while register load/stores work regardless of LMUL with vl == VLMAX
    """

    test_chunks = []
    for lmul in (1, 2, 4, 8):
        params = generate_random_vector_params(test_data, instr_name, instr_type, lmul, suite="length", vl="vlmax")
        desc = f"Whole Register Load/Store lmul={lmul}"
        bin_name = f"lmul_{lmul}"

        test_chunks.append(
            format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        )
        return_testcase_registers(test_data, params)

    return test_chunks


@add_coverpoint_generator("cp_custom_maskLS")
def make_cp_custom_maskLS(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generates a cross of lmuls > 1 and sews > 8 to cover EMUL >= 16 cases for mask load/stores.
    """

    if test_data.config.sew == 8:
        return []

    test_chunks = []
    for lmul in (2, 4, 8):
        params = generate_random_vector_params(test_data, instr_name, instr_type, lmul, vl="vlmax", suite="length")
        desc = f"Mask LS lmul={lmul}"
        bin_name = f"lmul_{lmul}"

        test_chunks.append(
            format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        )
        return_testcase_registers(test_data, params)

    return test_chunks
