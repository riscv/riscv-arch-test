##################################
# cr_vs2_vs1_edges.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import return_test_regs
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.coverpoints.vector._corner_helpers import CORNER_NAMES, make_corner_label
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.formatters.vector_params import generate_random_vector_params

_KNOWN_REGS = ["vs3", "vs2", "vs1", "vd"]


def _parse_cross_regs(coverpoint: str) -> tuple[str, str]:
    """Parse 'cr_vs2_vs1_edges' -> ('vs2', 'vs1')."""
    inner = coverpoint[len("cr_") : -len("_edges")]
    for r1 in _KNOWN_REGS:
        if inner.startswith(r1 + "_"):
            r2 = inner[len(r1) + 1 :]
            if r2 in _KNOWN_REGS:
                return r1, r2
    raise ValueError(f"Cannot parse register pair from coverpoint: {coverpoint}")


@add_coverpoint_generator("cr_vs2_vs1_edges", "cr_vs2_vd_edges", "cr_vs1_vd_edges")
def make_cross_edges(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    sew = test_data.config.sew
    assert sew is not None

    r1_name, r2_name = _parse_cross_regs(coverpoint)

    test_chunks = []
    for c1 in CORNER_NAMES:
        for c2 in CORNER_NAMES:
            r1_label = make_corner_label(c1, sew, test_data, suffix=f"_{r1_name}")
            r2_label = make_corner_label(c2, sew, test_data, suffix=f"_{r2_name}")

            params = generate_random_vector_params(
                test_data,
                instr_name,
                instr_type,
                lmul=1,
                additional_no_overlap={(r1_name, r2_name)},
                masked=False,
                suite="base",
                **{f"{r1_name}_val_pointer": r1_label, f"{r2_name}_val_pointer": r2_label},
            )

            desc = f"{coverpoint} ({r1_name}={c1}, {r2_name}={c2})"
            bin_name = f"cp_{r1_name}_{r2_name}_edges_b{c1}_{c2}"

            tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)

            test_chunks.append(tc)
            return_test_regs(test_data, params)

    return test_chunks
