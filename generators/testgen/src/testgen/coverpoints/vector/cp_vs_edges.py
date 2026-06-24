##################################
# cp_vs_edges.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.coverpoints.vector.vector_helpers import (
    VF_CORNER_NAMES,
    VLS_CORNER_NAMES,
    VX_CORNER_NAMES,
    get_base_lmul,
    get_corner_value,
)
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.vector_params import generate_random_vector_params


@add_coverpoint_generator("cp_vs2_edges")
@add_coverpoint_generator("cp_vs1_edges")
@add_coverpoint_generator("cp_vd_edges")
def make_vs2_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    assert test_data.config.sew is not None, "SEW must ve set for vector tests"
    sew = test_data.config.sew

    corners = VX_CORNER_NAMES
    suffix = ""
    vl = 1
    lmul = get_base_lmul(instr_name, instr_type, sew)
    register = coverpoint.split("_")[1]

    if coverpoint.startswith("cp_vs2_edges_"):
        suffix = coverpoint[len("cp_vs2_edges_") :]
        if suffix.startswith("f"):
            corners = VF_CORNER_NAMES
        elif suffix.startswith("ls"):
            corners = VLS_CORNER_NAMES
        elif suffix == "eew1":
            vl = 8
        elif suffix.startswith("egs"):
            raise NotImplementedError("Crypto Edges are not yet Supported")

    test_chunks = []
    for corner in corners:
        label = f"{register}_corner_{corner}_{suffix}"
        test_data.register_vector_data(label, sew, elements=[get_corner_value(corner, suffix, sew)])

        presets = {f"{register}_val_pointer": label}

        params = generate_random_vector_params(
            test_data,
            instr_name,
            instr_type,
            lmul=lmul,
            vl=vl,
            additional_no_overlap=set(),
            masked=False,
            suite="base",
            **presets,
        )

        desc = f"cp_{register}_edges (Test source {register} value = {corner})"
        bin_name = f"cp_{register}_edges_b{corner}"

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

        test_chunks.append(tc)
        return_test_regs(test_data, params)

    return test_chunks
