##################################
# cr_vxrm_vs2_vs1_edges.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.coverpoints.vector.vector_helpers import VX_CORNER_NAMES, get_corner_value
from testgen.data.edges import IMMEDIATE_EDGES, get_general_edges
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.registry import get_instr_type_config
from testgen.formatters.vector_params import generate_random_vector_params

_VXRM_MODES = ["rnu", "rne", "rdn", "rod"]


@add_coverpoint_generator("cr_vxrm_vs2_vs1_edges")
def make_vxrm_vs2_vs1_cross(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    sew = test_data.config.sew
    assert sew is not None

    # "_wv" suffix: vs2 is the widened source (emul2), vs1 is emul1
    suffix1 = suffix2 = "emul1"
    if coverpoint.endswith("_wv"):
        suffix1 = "emul2"

    test_chunks = []
    for vxrm_mode in _VXRM_MODES:
        for c1 in VX_CORNER_NAMES:
            vs2_label = f"vs2_corner_{c1}_{suffix1}"
            if not ("random" in vs2_label and vs2_label in test_data.vector_labels):
                eew = sew * (2 if suffix1 == "emul2" else 1)
                test_data.register_vector_data(vs2_label, eew, elements=[get_corner_value(c1, suffix1, sew)])

            for c2 in VX_CORNER_NAMES:
                vs1_label = f"vs1_corner_{c2}_{suffix2}"
                if not ("random" in vs1_label and vs1_label in test_data.vector_labels):
                    test_data.register_vector_data(vs1_label, sew, elements=[get_corner_value(c2, suffix2, sew)])

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

                desc = f"cr_vxrm_vs2_vs1_edges (vxrm={vxrm_mode}, vs2={c1}, vs1={c2})"
                bin_name = f"cp_vxrm_vs2_vs1_edges_b{vxrm_mode}_{c1}_{c2}"

                tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
                test_chunks.append(tc)
                return_test_regs(test_data, params)

    return test_chunks


@add_coverpoint_generator("cr_vxrm_vs2_rs1_edges")
def make_vxrm_vs2_rs1_cross(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    sew = test_data.config.sew
    assert sew is not None

    # "_wx" suffix: vs2 is the widened source (VWX type, emul2)
    suffix = "emul2" if coverpoint.endswith("_wx") else "emul1"
    rs1_edges = get_general_edges(test_data.xlen)

    test_chunks = []
    for vxrm_mode in _VXRM_MODES:
        for vs2_corner in VX_CORNER_NAMES:
            vs2_label = f"vs2_corner_{vs2_corner}_{suffix}"
            if not ("random" in vs2_label and vs2_label in test_data.vector_labels):
                eew = sew * (2 if suffix == "emul2" else 1)
                test_data.register_vector_data(vs2_label, eew, elements=[get_corner_value(vs2_corner, suffix, sew)])

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

                desc = f"cr_vxrm_vs2_rs1_edges (vxrm={vxrm_mode}, vs2={vs2_corner}, rs1={rs1_edge})"
                bin_name = f"cp_vxrm_vs2_rs1_edges_b{vxrm_mode}_{vs2_corner}_{rs1_edge}"

                tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
                test_chunks.append(tc)
                return_test_regs(test_data, params)

    return test_chunks


@add_coverpoint_generator("cr_vxrm_vs2_imm_edges")
def make_vxrm_vs2_imm_cross(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    sew = test_data.config.sew
    assert sew is not None

    # "_wi" suffix: vs2 is the widened source (VWI type, emul2)
    suffix = "emul2" if coverpoint.endswith("_wi") else "emul1"
    config = get_instr_type_config(instr_type)
    imm_edges = IMMEDIATE_EDGES.imm_5bit if config.imm_signed else IMMEDIATE_EDGES.imm_5bit_u

    test_chunks = []
    for vxrm_mode in _VXRM_MODES:
        for vs2_corner in VX_CORNER_NAMES:
            vs2_label = f"vs2_corner_{vs2_corner}_{suffix}"
            if not ("random" in vs2_label and vs2_label in test_data.vector_labels):
                eew = sew * (2 if suffix == "emul2" else 1)
                test_data.register_vector_data(vs2_label, eew, elements=[get_corner_value(vs2_corner, suffix, sew)])

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

                desc = f"cr_vxrm_vs2_imm_edges (vxrm={vxrm_mode}, vs2={vs2_corner}, imm={imm})"
                bin_name = f"cp_vxrm_vs2_imm_edges_b{vxrm_mode}_{vs2_corner}_{imm}"

                tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
                test_chunks.append(tc)
                return_test_regs(test_data, params)

    return test_chunks
