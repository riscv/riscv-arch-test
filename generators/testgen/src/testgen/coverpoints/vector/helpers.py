# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
"""Helpers shared only by vector coverpoint generators."""

import re

from testgen.constants import VLEN_MAX
from testgen.data.edges import get_vector_edge
from testgen.data.state import TestData


def make_and_register_edge_label(reg_name: str, edge_name: str, suffix: str, test_data: TestData) -> str:
    """
    Makes an edge data label out of the reg_name, edge_name, and suffix in the form of
    (reg_name)_edge_(edge_name)_(suffix). Then it registers the appropriate data for the emul found in the
    suffix, the sew in test_data, and the edge_name.
    """
    assert test_data.config.sew is not None, "SEW must be set for vector operations"
    sew = test_data.config.sew

    emul: float = 1
    emulf_match = re.search(r"emulf(\d+)", suffix)
    if emulf_match is not None:
        emul = 1 / int(emulf_match.group(1))

    emul_match = re.search(r"emul(\d+)", suffix)
    if emul_match is not None:
        emul = int(emul_match.group(1))

    label = f"{reg_name}_edge_{edge_name}_{suffix}"
    if label.startswith("vs2_edge_zero_emul8_ls"):
        # FIXME: Coverage workaround because it requires all zeros in the register
        eew = int(sew * emul)
        max_elements = VLEN_MAX // eew * 8
        test_data.register_vector_data(label, eew, elements=[0] * max_elements)
    elif not ("random" in label and label in test_data.vector_labels):
        eew = int(sew * emul)
        test_data.register_vector_data(label, eew, elements=[get_vector_edge(edge_name, suffix, sew)])

    return label
