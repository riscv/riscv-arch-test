##################################
# cp_custom.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.coverpoints import registry
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk


@registry.add_coverpoint_generator("cp_custom_wvv")
def dispatch_wvv(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    chunks = []
    for sub_cp in [
        "cp_custom_vdOverlapTopVs2_vd_vs2_lmul1",
        "cp_custom_vdOverlapTopVs1_vd_vs1_lmul1",
        "cp_custom_vdOverlapTopVs2_vd_vs2_lmul2",
        "cp_custom_vdOverlapTopVs1_vd_vs1_lmul2",
        "cp_custom_vdOverlapTopVs2_vd_vs2_lmul4",
        "cp_custom_vdOverlapTopVs1_vd_vs1_lmul4",
    ]:
        chunks.extend(registry.generate_tests_for_coverpoint(instr_name, instr_type, sub_cp, test_data))
    return chunks


@registry.add_coverpoint_generator("cp_custom_wvv_all")
def dispatch_wvv_all(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    chunks = []
    for sub_cp in [
        "cp_custom_allVdOverlapTopVs2_vd_vs2_lmul1",
        "cp_custom_allVdOverlapTopVs2_vd_vs2_lmul2",
        "cp_custom_allVdOverlapTopVs2_vd_vs2_lmul4",
        "cp_custom_allVdOverlapTopVs1_vd_vs1_lmul1",
        "cp_custom_allVdOverlapTopVs1_vd_vs1_lmul2",
        "cp_custom_allVdOverlapTopVs1_vd_vs1_lmul4",
    ]:
        chunks.extend(registry.generate_tests_for_coverpoint(instr_name, instr_type, sub_cp, test_data))
    return chunks


@registry.add_coverpoint_generator("cp_custom_wwv_all")
def dispatch_wwv_all(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    chunks = []
    for sub_cp in [
        "cp_custom_allVdOverlapTopVs1_vd_vs1_lmul1",
        "cp_custom_allVdOverlapTopVs1_vd_vs1_lmul2",
        "cp_custom_allVdOverlapTopVs1_vd_vs1_lmul4",
    ]:
        chunks.extend(registry.generate_tests_for_coverpoint(instr_name, instr_type, sub_cp, test_data))
    return chunks


@registry.add_coverpoint_generator("cp_custom_wwv")
def dispatch_wwv(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    chunks = []
    for sub_cp in [
        "cp_custom_vdOverlapTopVs1_vd_vs1_lmul1",
        "cp_custom_vdOverlapTopVs1_vd_vs1_lmul2",
        "cp_custom_vdOverlapTopVs1_vd_vs1_lmul4",
    ]:
        chunks.extend(registry.generate_tests_for_coverpoint(instr_name, instr_type, sub_cp, test_data))
    return chunks


@registry.add_coverpoint_generator("cp_custom_shift_vv")
def dispatch_shift_vv(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    return registry.generate_tests_for_coverpoint(
        instr_name, instr_type, "cp_custom_vshift_upperbits_vs1_ones", test_data
    )


@registry.add_coverpoint_generator("cp_custom_shift_wv")
def dispatch_shift_wv(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    chunks = []
    for sub_cp in [
        "cp_custom_vdOverlapBtmVs2_vd_vs2_lmul1",
        "cp_custom_vdOverlapBtmVs2_vd_vs2_lmul2",
        "cp_custom_vdOverlapBtmVs2_vd_vs2_lmul4",
        "cp_custom_vshiftn_upperbits_vs1_ones",
    ]:
        chunks.extend(registry.generate_tests_for_coverpoint(instr_name, instr_type, sub_cp, test_data))
    return chunks


@registry.add_coverpoint_generator("cp_custom_wvx")
def dispatch_wvx(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    chunks = []
    for sub_cp in [
        "cp_custom_vdOverlapTopVs2_vd_vs2_lmul1",
        "cp_custom_vdOverlapTopVs2_vd_vs2_lmul2",
        "cp_custom_vdOverlapTopVs2_vd_vs2_lmul4",
    ]:
        chunks.extend(registry.generate_tests_for_coverpoint(instr_name, instr_type, sub_cp, test_data))
    return chunks


@registry.add_coverpoint_generator("cp_custom_wvx_all")
def dispatch_wvx_all(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    chunks = []
    for sub_cp in [
        "cp_custom_allVdOverlapTopVs2_vd_vs2_lmul1",
        "cp_custom_allVdOverlapTopVs2_vd_vs2_lmul2",
        "cp_custom_allVdOverlapTopVs2_vd_vs2_lmul4",
    ]:
        chunks.extend(registry.generate_tests_for_coverpoint(instr_name, instr_type, sub_cp, test_data))
    return chunks


@registry.add_coverpoint_generator("cp_custom_shift_vx")
def dispatch_shift_vx(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    return registry.generate_tests_for_coverpoint(
        instr_name, instr_type, "cp_custom_vshift_upperbits_rs1_ones", test_data
    )


@registry.add_coverpoint_generator("cp_custom_shift_wx")
def dispatch_shift_wx(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    chunks = []
    for sub_cp in [
        "cp_custom_vdOverlapBtmVs2_vd_vs2_lmul1",
        "cp_custom_vdOverlapBtmVs2_vd_vs2_lmul2",
        "cp_custom_vdOverlapBtmVs2_vd_vs2_lmul4",
        "cp_custom_vshiftn_upperbits_rs1_ones",
    ]:
        chunks.extend(registry.generate_tests_for_coverpoint(instr_name, instr_type, sub_cp, test_data))
    return chunks


@registry.add_coverpoint_generator("cp_custom_shift_wi")
def dispatch_shift_wi(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    chunks = []
    for sub_cp in [
        "cp_custom_vdOverlapBtmVs2_vd_vs2_lmul1",
        "cp_custom_vdOverlapBtmVs2_vd_vs2_lmul2",
        "cp_custom_vdOverlapBtmVs2_vd_vs2_lmul4",
    ]:
        chunks.extend(registry.generate_tests_for_coverpoint(instr_name, instr_type, sub_cp, test_data))
    return chunks


@registry.add_coverpoint_generator("cp_custom_shift_wi_all")
def dispatch_shift_wi_all(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    chunks = []
    for sub_cp in [
        "cp_custom_allVdOverlapBtmVs2_vd_vs2_lmul1",
        "cp_custom_allVdOverlapBtmVs2_vd_vs2_lmul2",
        "cp_custom_allVdOverlapBtmVs2_vd_vs2_lmul4",
    ]:
        chunks.extend(registry.generate_tests_for_coverpoint(instr_name, instr_type, sub_cp, test_data))
    return chunks


@registry.add_coverpoint_generator("cp_custom_vindexVV")
def dispatch_vindexVV(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    chunks = []
    for sub_cp in [
        "cp_custom_vindexedges_index_ge_vlmax",
        "cp_custom_vindexedges_index_gt_vl_lt_vlmax",
    ]:
        chunks.extend(registry.generate_tests_for_coverpoint(instr_name, instr_type, sub_cp, test_data))
    return chunks


@registry.add_coverpoint_generator("cp_custom_vindexVX")
def dispatch_vindexVX(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    # Edge cases for VX-type gather/slide are covered by cp_rs1_edges.
    return []
