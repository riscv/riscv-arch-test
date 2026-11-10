# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
"""Helpers shared only by vector coverpoint generators."""

import re

from testgen.data.edges import get_vector_edge
from testgen.data.state import TestData


def make_and_register_edge_label(reg_name: str, edge_name: str, suffix: str, test_data: TestData, sew: int) -> str:
    """
    Makes an edge data label out of the reg_name, edge_name, and suffix in the form of
    (reg_name)_edge_(edge_name)_(suffix). Then it registers the appropriate data for the emul found in the
    suffix, the sew in test_data, and the edge_name.
    """
    emul: float = 1
    emulf_match = re.search(r"emulf(\d+)", suffix)
    if emulf_match is not None:
        emul = 1 / int(emulf_match.group(1))

    emul_match = re.search(r"emul(\d+)", suffix)
    if emul_match is not None:
        emul = int(emul_match.group(1))

    label = f"{reg_name}_edge_{edge_name}_{suffix}_sew{sew}"
    if not ("random" in label and label in test_data.vector_labels):
        eew = int(sew * emul)
        test_data.register_vector_data(label, eew, elements=[get_vector_edge(edge_name, suffix, sew)])

    return label


def extract_coverpoint_sews(cp: str) -> tuple[list[int], str]:
    """
    Takes a coverpoint name of the form cp_name_8_16_... and returns set of SEWs to test and a cleaned coverpoint
    """
    parts = cp.split("_")

    available_sews = set()
    i = len(parts)
    for cp_part in parts[::-1]:
        if not cp_part.isnumeric() or cp_part == "0":
            break
        available_sews.add(int(cp_part))
        i -= 1

    return sorted(available_sews), "_".join(parts[:i])
