##################################
# cr_vxrm_vs_reg_edges.py
#
# Generators for tests crossing the fixed point rounding mode and edge values.
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.coverpoints.vector.vector_helpers import make_and_register_edge_label
from testgen.data.edges import IMMEDIATE_EDGES, VECTOR_EDGES, get_general_edges
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.registry import get_instr_type_config
from testgen.formatters.vector_params import generate_random_vector_params

_VXRM_MODES = ["rnu", "rne", "rdn", "rod"]


@add_coverpoint_generator("cr_vxrm_vs2_vs1_edges")
def make_vxrm_vs2_vs1_cross(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generates tests crossing the fixed point rounding mode, and integer edge values for vs2 and vs1.
    """

    sew = test_data.config.sew
    assert sew is not None

    # "_wv" suffix: vs2 is the widened source (emul2), vs1 is emul1
    vs2_suffix = vs1_suffix = "emul1"
    if coverpoint.endswith("_wv"):
        vs2_suffix = "emul2"

    test_chunks = []
    for vxrm_mode in _VXRM_MODES:
        for vs2_edge in VECTOR_EDGES.vx_edges:
            vs2_label = make_and_register_edge_label("vs2", vs2_edge, vs2_suffix, test_data)

            for vs1_edge in VECTOR_EDGES.vx_edges:
                vs1_label = make_and_register_edge_label("vs1", vs1_edge, vs1_suffix, test_data)

                params = generate_random_vector_params(
                    test_data,
                    instr_name,
                    instr_type,
                    lmul=1,
                    additional_no_overlap={("vs1", "vs2")},
                    masked=False,
                    suite="base",
                    vs2_val_pointer=vs2_label,
                    vs1_val_pointer=vs1_label,
                    vxrm=vxrm_mode,
                )

                desc = f"cr_vxrm_vs2_vs1_edges (vxrm={vxrm_mode}, vs2={vs2_edge}, vs1={vs1_edge})"
                bin_name = f"cp_vxrm_vs2_vs1_edges_b{vxrm_mode}_{vs2_edge}_{vs1_edge}"

                tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
                test_chunks.append(tc)
                return_test_regs(test_data, params)

    return test_chunks


@add_coverpoint_generator("cr_vxrm_vs2_rs1_edges")
def make_vxrm_vs2_rs1_cross(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generates tests crossing the fixed point rounding mode, and integer edge values for vs2 and rs1.
    """

    sew = test_data.config.sew
    assert sew is not None

    # "_wx" suffix: vs2 is the widened source (VWX type, emul2)
    suffix = "emul2" if coverpoint.endswith("_wx") else "emul1"
    rs1_edges = get_general_edges(test_data.xlen)

    test_chunks = []
    for vxrm_mode in _VXRM_MODES:
        for vs2_edge in VECTOR_EDGES.vx_edges:
            vs2_label = make_and_register_edge_label("vs2", vs2_edge, suffix, test_data)

            for rs1_edge in rs1_edges:
                params = generate_random_vector_params(
                    test_data,
                    instr_name,
                    instr_type,
                    lmul=1,
                    vs2_val_pointer=vs2_label,
                    vxrm=vxrm_mode,
                )
                # rs1val is overwritten by generate_random_vector_params; override here.
                params.rs1val = rs1_edge

                desc = f"cr_vxrm_vs2_rs1_edges (vxrm={vxrm_mode}, vs2={vs2_edge}, rs1={rs1_edge})"
                bin_name = f"cp_vxrm_vs2_rs1_edges_b{vxrm_mode}_{vs2_edge}_{rs1_edge}"

                tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
                test_chunks.append(tc)
                return_test_regs(test_data, params)

    return test_chunks


@add_coverpoint_generator("cr_vxrm_vs2_imm_edges")
def make_vxrm_vs2_imm_cross(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generates tests crossing the fixed point rounding mode, and integer edge values for vs2 and an immediate.
    """

    sew = test_data.config.sew
    assert sew is not None

    # "_wi" suffix: vs2 is the widened source (VWI type, emul2)
    suffix = "emul2" if coverpoint.endswith("_wi") else "emul1"
    config = get_instr_type_config(instr_type)
    imm_edges = IMMEDIATE_EDGES.imm_5bit if config.imm_signed else IMMEDIATE_EDGES.imm_5bit_u

    test_chunks = []
    for vxrm_mode in _VXRM_MODES:
        for vs2_edge in VECTOR_EDGES.vx_edges:
            vs2_label = make_and_register_edge_label("vs2", vs2_edge, suffix, test_data)

            for imm in imm_edges:
                params = generate_random_vector_params(
                    test_data,
                    instr_name,
                    instr_type,
                    lmul=1,
                    vs2_val_pointer=vs2_label,
                    vxrm=vxrm_mode,
                    immval=imm,
                )

                desc = f"cr_vxrm_vs2_imm_edges (vxrm={vxrm_mode}, vs2={vs2_edge}, imm={imm})"
                bin_name = f"cp_vxrm_vs2_imm_edges_b{vxrm_mode}_{vs2_edge}_{imm}"

                tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
                test_chunks.append(tc)
                return_test_regs(test_data, params)

    return test_chunks
