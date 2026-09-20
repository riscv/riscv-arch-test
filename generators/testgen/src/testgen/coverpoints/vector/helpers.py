# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
"""Helpers shared only by vector coverpoint generators."""

import re

from testgen.constants import VLEN_MAX
from testgen.data.edges import get_vector_edge
from testgen.data.random import random_int
from testgen.data.state import TestData


def crypto_edge_names(suffix: str) -> tuple[str, ...]:
    """Return element-group edge names for a vector-crypto coverpoint suffix."""
    if "subbytes" in suffix:
        return tuple(f"subbytes_{index}" for index in range(16))
    return ("zero", "ones", "walkeven", "walkodd", "random")


def make_and_register_crypto_edge_label(
    reg_name: str, edge_name: str, suffix: str, test_data: TestData
) -> str:
    """Register one EGS-wide vector-crypto edge as SEW-sized elements."""
    assert test_data.config.sew is not None
    sew = test_data.config.sew
    match = re.search(r"egs(\d+)", suffix)
    if match is None:
        raise ValueError(f"missing EGS in crypto edge suffix {suffix}")
    egs = int(match.group(1))
    width = sew * egs
    if edge_name.startswith("subbytes_"):
        block = int(edge_name.removeprefix("subbytes_")) * 16
        value = sum((block + index) << (8 * index) for index in range(16))
    elif edge_name == "zero":
        value = 0
    elif edge_name == "ones":
        value = (1 << width) - 1
    elif edge_name == "walkeven":
        value = sum(1 << index for index in range(0, width, 2))
    elif edge_name == "walkodd":
        value = sum(1 << index for index in range(1, width, 2))
    elif edge_name == "random":
        value = random_int(width)
    else:
        raise ValueError(f"unknown vector-crypto edge {edge_name}")
    elements = [(value >> (sew * index)) & ((1 << sew) - 1) for index in range(egs)]
    label = f"{reg_name}_edge_{edge_name}_{suffix}"
    if label not in test_data.vector_labels:
        test_data.register_vector_data(label, sew, elements=elements)
    return label


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
