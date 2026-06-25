##################################
# cr_vxrm_vs2_vs1_edges.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.coverpoints.vector.vector_helpers import VX_CORNER_NAMES, get_corner_value
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.vector_params import generate_random_vector_params

_VXRM_MODES = ["rnu", "rne", "rdn", "rod"]


@add_coverpoint_generator("cr_vxrm_vs2_vs1_edges")
def make_vxrm_cross_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
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
