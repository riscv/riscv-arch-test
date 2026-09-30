##################################
# cr_vs_reg_edges.py
#
# Generates all tests crossing vector edge values.
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

import re

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.coverpoints.vector.helpers import make_and_register_edge_label
from testgen.data.edges import IMMEDIATE_EDGES, VECTOR_EDGES, get_general_edges
from testgen.data.random import random_int
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase, get_instruction_type_config
from testgen.instructions.vector_params import generate_random_vector_params

_KNOWN_REGS = ["vs3", "vs2", "vs1", "vd"]


def _parse_cross_regs(coverpoint: str) -> tuple[str, str]:
    """Parse 'cr_vs2_vs1_edges' -> ('vs2', 'vs1')."""
    match_pair = re.search(r"cr_(vs\d)_(vs\d|vd)_edges", coverpoint)
    if not match_pair:
        raise ValueError(f"Cannot parse register pair from coverpoint: {coverpoint}")

    r1, r2 = match_pair.group(1), match_pair.group(2)
    if r1 not in _KNOWN_REGS:
        raise ValueError(f"Parsed unknown register: {r1} from coverpoint {coverpoint}")
    if r2 not in _KNOWN_REGS:
        raise ValueError(f"Parsed unknown register: {r2} from coverpoint {coverpoint}")

    return r1, r2


@add_coverpoint_generator("cr_vs2_vs1_edges", "cr_vs2_vd_edges", "cr_vs1_vd_edges")
def make_cross_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate tests crossing edge values for any two vector registers. Supports integer and floating point crosses.
    """

    sew = test_data.config.sew
    assert sew is not None

    r1_name, r2_name = _parse_cross_regs(coverpoint)

    edges1 = edges2 = VECTOR_EDGES.vx_edges
    suffix1 = suffix2 = "emul1"
    lmul = 1

    if coverpoint.endswith("wv"):
        suffix1 = "emul2"
    elif coverpoint.endswith("wred"):
        suffix2 = "emul2"
    elif coverpoint.endswith("mm"):
        suffix1 = suffix2 = "eew1"
    elif coverpoint.endswith("f"):
        suffix1 = suffix2 = "f"
        edges1 = edges2 = VECTOR_EDGES.vf_edges
    elif coverpoint.endswith("f_bf16"):
        suffix1 = suffix2 = "f_bf16"
        edges1 = edges2 = VECTOR_EDGES.vf_edges
    elif coverpoint.endswith("fwv"):
        suffix1 = "f_emul2"
        suffix2 = "f"
        edges1 = edges2 = VECTOR_EDGES.vf_edges
    elif coverpoint.endswith("fwred"):
        suffix1 = "f"
        suffix2 = "f_emul2"
        edges1 = edges2 = VECTOR_EDGES.vf_edges
    elif "egs" in coverpoint:
        if coverpoint.endswith("egs4_subbytes"):
            lmul = 4
            edges1 = VECTOR_EDGES.v_crypto_edges  # VS2 Edges
            edges2 = VECTOR_EDGES.v_aes_edges  # VD Edges
            suffix1 = suffix2 = "emul4"
        elif coverpoint.endswith("egs4_subbytes_vs2"):
            lmul = 4
            edges1 = VECTOR_EDGES.v_aes_edges  # VS2 Edges
            edges2 = VECTOR_EDGES.v_crypto_edges  # VD Edges
            suffix1 = suffix2 = "emul4"
        elif "subbytes" in coverpoint:
            raise NotImplementedError(f"Subbytes not supported for coverpoint: {coverpoint}")
        else:
            egs_match = re.search(r"egs(\d+)", coverpoint)
            assert egs_match is not None, f"EGS Coverpoint: {coverpoint} is not supported"
            lmul = int(egs_match.group(1))
            edges1 = edges2 = VECTOR_EDGES.v_crypto_edges
            suffix1 = suffix2 = f"emul{lmul}"

    test_chunks = []
    for r1_edge in edges1:
        r1_label = make_and_register_edge_label(r1_name, r1_edge, suffix1, test_data)

        for r2_edge in edges2:
            r2_label = make_and_register_edge_label(r2_name, r2_edge, suffix2, test_data)

            params = generate_random_vector_params(
                test_data,
                instr_name,
                instr_type,
                lmul=lmul,
                additional_no_overlap={("vs1", "vs2"), ("vd", "vs1"), ("vd", "vs2")},
                masked=False,
                suite="base",
                **{f"{r1_name}_val_pointer": r1_label, f"{r2_name}_val_pointer": r2_label},
            )

            desc = f"{coverpoint} ({r1_name}={r1_edge}, {r2_name}={r2_edge})"
            bin_name = f"cp_{r1_name}_{r2_name}_edges_b{r1_edge}_{r2_edge}"

            tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

            test_chunks.append(tc)
            return_testcase_registers(test_data, params)

    return test_chunks


@add_coverpoint_generator("cr_vs2_rs1_edges")
def make_vs2_rs1_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate tests crossing edge values for vs2 and rs1. Supports only integer crosses, as rs1 is an integer register.
    """

    sew = test_data.config.sew
    assert sew is not None, "SEW must be set for vector tests"

    vs2_edges = VECTOR_EDGES.vx_edges
    suffix = "emul2" if coverpoint.endswith("wx") else "emul1"
    rs1_edges = get_general_edges(test_data.xlen)

    test_chunks = []
    for vs2_edge in vs2_edges:
        vs2_label = make_and_register_edge_label("vs2", vs2_edge, suffix, test_data)

        for rs1_edge in rs1_edges:
            params = generate_random_vector_params(
                test_data, instr_name, instr_type, lmul=1, rs1val=rs1_edge, vs2_val_pointer=vs2_label
            )
            desc = f"{coverpoint} (vs2={vs2_edge}, rs1={rs1_edge})"
            bin_name = f"cp_vs2_rs1_edges_b{vs2_edge}_{rs1_edge}"

            tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

            test_chunks.append(tc)
            return_testcase_registers(test_data, params)

    return test_chunks


@add_coverpoint_generator("cr_vs2_imm_edges")
def make_vs2_imm_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate tests crossing edge values for vs2 and an immediate value. Supports only integer crosses.
    """

    sew = test_data.config.sew
    assert sew is not None, "SEW must be set for vector tests"

    vs2_edges = VECTOR_EDGES.vx_edges
    suffix = "emul2" if coverpoint.endswith(("wi", "wiu")) else "emul1"

    config = get_instruction_type_config(instr_type)
    imm_edges = IMMEDIATE_EDGES.imm_5bit if config.imm_signed else IMMEDIATE_EDGES.imm_5bit_u

    test_chunks = []
    for vs2_edge in vs2_edges:
        vs2_label = make_and_register_edge_label("vs2", vs2_edge, suffix, test_data)

        for imm in imm_edges:
            params = generate_random_vector_params(
                test_data, instr_name, instr_type, lmul=1, immval=imm, vs2_val_pointer=vs2_label
            )
            desc = f"{coverpoint} (vs2={vs2_edge}, imm={imm})"
            bin_name = f"cp_vs2_imm_edges_b{vs2_edge}_{imm}"

            tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

            test_chunks.append(tc)
            return_testcase_registers(test_data, params)

    return test_chunks


@add_coverpoint_generator("cr_vs2_vd_edges_egs4_subbytes_sm")
def make_cr_vs2_vd_edges_sm(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    vs2_edges = {
        "vs_corner_zero": 0,
        "vs_corner_ones": (1 << 128) - 1,
        "vs_corner_walkeven": sum(1 << i for i in range(128) if i % 2 == 0),
        "vs_corner_walkodd": sum(1 << i for i in range(128) if i % 2 == 1),
        "vs_corner_random": random_int(128, signed=False),
    }

    test_chunks: list[TestChunk] = []

    for vs2_edge_name, vs2_val in vs2_edges.items():
        v2 = f"{vs2_edge_name}_subbytes_sm_cross"
        data = [(vs2_val >> (32 * i)) & (0xFFFF_FFFF) for i in range(4)]
        test_data.register_vector_data(v2, 32, elements=data)

        for i in range(0, 256, 4):
            target = 0
            for j in range(4):
                target += (i + j) << (j * 8)

            x2 = random_int(32, signed=False)
            x3 = random_int(32, signed=False)

            rk0 = vs2_val & 0xFFFF_FFFF

            x1 = x2 ^ x3 ^ target ^ rk0
            v1 = f"vs2_vd_subbytes_sm_cross_vs2_{vs2_edge_name}_vd_{i // 4}"
            test_data.register_vector_data(v1, 32, elements=[random_int(32, signed=False), x1, x2, x3])

            desc = f"{vs2_edge_name} test {i}"
            bin_name = f"b{v1}_{v2}"

            params = generate_random_vector_params(
                test_data,
                instr_name,
                instr_type,
                lmul=4,
                vd_val_pointer=v1,
                vs2_val_pointer=v2,
                additional_no_overlap={("vd", "vs1"), ("vs2", "vd"), ("vs1", "vs2")},
            )

            test_chunks.append(
                format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
            )
            return_testcase_registers(test_data, params)

    return test_chunks
