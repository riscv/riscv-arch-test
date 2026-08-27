##################################
# cp_vs_edges.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################


from testgen.asm.vector_helpers import get_lmul_flag
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.coverpoints.vector.helpers import make_and_register_edge_label
from testgen.data.edges import VECTOR_EDGES
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

    # TODO: EGS4

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
        elif suffix.startswith("egs"):
            raise NotImplementedError("Crypto Edges are not yet Supported")

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
