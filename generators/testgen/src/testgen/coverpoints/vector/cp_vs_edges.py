##################################
# cp_vs_edges.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

import re

from testgen.asm.vector_helpers import get_lmul_flag
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.coverpoints.vector.helpers import make_and_register_edge_label
from testgen.data.edges import VECTOR_EDGES
from testgen.data.random import random_int
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.registry import get_instruction_type_config
from testgen.instructions.vector import get_base_lmul, parse_vector_instruction_info
from testgen.instructions.vector_params import generate_random_vector_params


@add_coverpoint_generator("cp_vs2_edges")
@add_coverpoint_generator("cp_vs1_edges")
@add_coverpoint_generator("cp_vd_edges")
def make_vs_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """
    Generate edge values in any vector register. Supports integer, load-store, and fp edges.
    """

    assert test_data.config.sew is not None, "SEW must be set for vector tests"
    sew = test_data.config.sew

    edges = VECTOR_EDGES.vx_edges
    suffix = ""
    vl = 1
    lmul = get_base_lmul(instr_name, instr_type, sew)
    register = coverpoint.split("_")[1]

    type_config = get_instruction_type_config(instr_type)
    assert type_config.vector_data is not None, "Vector data must be provided for all vector instruction types"
    additional_no_overlap = {("vs3", "vs2")} if "store" in type_config.instruction_class else set()

    if coverpoint.startswith(f"cp_{register}_edges_"):
        suffix = coverpoint[len(f"cp_{register}_edges_") :]
        if suffix.startswith("f"):
            edges = VECTOR_EDGES.vf_edges
        elif suffix.startswith("ls"):
            edges = VECTOR_EDGES.vls_edges
            info = parse_vector_instruction_info(instr_name, instr_type)
            multiplier = info.get_size_multiplier(register, sew, type_config.vector_data.widened_regs)

            suffix += f"_emul{get_lmul_flag(multiplier)}"
        elif suffix == "eew1":
            vl = 8
        elif "subbytes_sm" in suffix:
            raise NotImplementedError(
                f"ShangMi Subbytes Edges Need to Go Through Their Own Generator, got {coverpoint}"
            )
        elif suffix == "egs4_subbytes":
            edges = VECTOR_EDGES.v_aes_edges
            lmul = 4
            vl = 4
            suffix += "_emul4"
        elif suffix.startswith("egs"):
            edges = VECTOR_EDGES.v_crypto_edges
            egs_match = re.match(r"egs(\d+)", suffix)
            assert egs_match is not None, f"EGS must be passed in the form egsN where N is the size, got {suffix}"
            lmul = int(egs_match.group(1))
            vl = int(egs_match.group(1))
            suffix += f"_emul{lmul}"

    test_chunks = []
    for edge in edges:
        label = make_and_register_edge_label(register, edge, suffix, test_data)

        presets = {f"{register}_val_pointer": label}

        params = generate_random_vector_params(
            test_data,
            instr_name,
            instr_type,
            lmul=lmul,
            vl=vl,
            additional_no_overlap=additional_no_overlap,
            masked=False,
            suite="base",
            **presets,
        )

        desc = f"cp_{register}_edges (Test source {register} value = {edge})"
        bin_name = f"cp_{register}_edges_b{edge}"

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

        test_chunks.append(tc)
        return_testcase_registers(test_data, params)

    return test_chunks


@add_coverpoint_generator("cp_vd_edges_egs4_subbytes_sm")
def make_vd_edges_egs4_subbytes(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """Hit all SM4 S-Box Values for the VD register"""

    test_chunks: list[TestChunk] = []

    for i in range(0, 256, 4):
        # On the ith iteration, we want subbytes that are {i+3}{i+2}{i+1}{i}
        # in the first sm4_subword call

        # Sail Reference: (From the Spec)
        # {rk3 @ rk2 @ rk1 @ rk0} : bits(128) = get_velem(vs2, EGW=128, keyelem);
        # {x3 @ x2 @ x1 @ x0} : bits(128) = get_velem(vd, EGW=128, i);
        # B  = x1 ^ x2 ^ x3 ^ rk0;
        # S = sm4_subword(B);

        # So we can randomly choose all of vd, and choose a specific rk0 to get the desired B
        target = 0
        for j in range(4):
            target += (i + j) << (j * 8)

        x1 = random_int(32, signed=False)
        x2 = random_int(32, signed=False)
        x3 = random_int(32, signed=False)

        rk0 = x1 ^ x2 ^ x3 ^ target
        vs2_val = [rk0] + [random_int(32, signed=False) for _ in range(3)]
        vd_val = [random_int(32, signed=False), x1, x2, x3]

        assert target == (x1 ^ x2 ^ x3 ^ rk0)

        edges_num = i // 4
        vs2_val_ptr = f"vs_corner_sm_vd_subbytes_{edges_num}_vs2"
        vd_val_ptr = f"vs_corner_sm_vd_subbytes_{edges_num}_vd"
        test_data.register_vector_data(vs2_val_ptr, 32, elements=vs2_val)
        test_data.register_vector_data(vd_val_ptr, 32, elements=vd_val)

        desc = "Test source targeting value = " + hex(target)
        bin_name = f"b{target:08x}"
        params = generate_random_vector_params(
            test_data,
            instr_name,
            instr_type,
            lmul=4,
            additional_no_overlap={("vs2", "vd")},
            vs2_val_pointer=vs2_val_ptr,
            vd_val_pointer=vd_val_ptr,
        )

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        return_testcase_registers(test_data, params)

        test_chunks.append(tc)

    return test_chunks


@add_coverpoint_generator("cp_vs2_edges_egs4_subbytes_sm")
def make_vs2_edges_egs4_subbytes(
    instr_name: str, instr_type: str, coverpoint: str, test_data: TestData
) -> list[TestChunk]:
    """Hit all SM4 S-Box Values for the VS2 register"""

    test_chunks: list[TestChunk] = []

    for i in range(0, 256, 4):
        # On the ith iteration, we want subbytes that are {i+3}{i+2}{i+1}{i}
        # in the first sm4_subword call

        # Sail Reference: (From the Spec)
        # let (rk3 @ rk2 @ rk1 @ rk0) : bits(128) = get_velem(vs2, 128, i);
        # B = rk1 ^ rk2 ^ rk3 ^ ck(4 * rnd);
        # S = sm4_subword(B);

        # From the spec:
        ck = [
            0x00070E15,
            0x1C232A31,
            0x383F464D,
            0x545B6269,
            0x70777E85,
            0x8C939AA1,
            0xA8AFB6BD,
            0xC4CBD2D9,
            0xE0E7EEF5,
            0xFC030A11,
            0x181F262D,
            0x343B4249,
            0x50575E65,
            0x6C737A81,
            0x888F969D,
            0xA4ABB2B9,
            0xC0C7CED5,
            0xDCE3EAF1,
            0xF8FF060D,
            0x141B2229,
            0x30373E45,
            0x4C535A61,
            0x686F767D,
            0x848B9299,
            0xA0A7AEB5,
            0xBCC3CAD1,
            0xD8DFE6ED,
            0xF4FB0209,
            0x10171E25,
            0x2C333A41,
            0x484F565D,
            0x646B7279,
        ]

        # Randomly choose, ck, rk2, rk3, and have a desired target, to solve for rk1
        target = 0
        for j in range(4):
            target += (i + j) << (j * 8)

        imm_val = random_int(5, signed=False)
        ck_val = ck[4 * (imm_val & 0x7)]

        rk2 = random_int(32, signed=False)
        rk3 = random_int(32, signed=False)
        rk0 = random_int(32, signed=False)

        rk1 = ck_val ^ rk2 ^ rk3 ^ target

        vs2_val = [rk0, rk1, rk2, rk3]
        assert target == (rk1 ^ rk2 ^ rk3 ^ ck_val)

        edges_num = i // 4
        vs2_val_ptr = f"vs_corner_sm_vs2_subbytes_{edges_num}_vs2"
        test_data.register_vector_data(vs2_val_ptr, 32, elements=vs2_val)

        desc = "Test source targeting value = " + hex(target)
        bin_name = f"b{target:08x}"
        params = generate_random_vector_params(
            test_data,
            instr_name,
            instr_type,
            lmul=4,
            additional_no_overlap={("vs2", "vd")},
            vs2_val_pointer=vs2_val_ptr,
            immval=imm_val,
        )

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        return_testcase_registers(test_data, params)

        test_chunks.append(tc)

    return test_chunks
