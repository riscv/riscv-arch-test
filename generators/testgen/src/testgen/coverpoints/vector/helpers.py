# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
"""Helpers shared only by vector coverpoint generators."""

import math
import re

from testgen.constants import VLEN_MAX
from testgen.data.edges import get_vector_edge
from testgen.data.random import random_int
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk

_SM4_CK = (
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
)


def guard_element_group_vlen(test_chunk: TestChunk, sew: int, egs: int, lmul: float) -> None:
    """Compile an element-group testcase only when VLMAX can hold a complete group."""
    if egs == 1:
        return
    minimum_vlen = math.ceil(sew * egs / lmul)
    test_chunk.code.insert(0, f"#if UDB_VLEN >= {minimum_vlen}")
    test_chunk.code.append("#endif")


def crypto_edge_names(suffix: str) -> tuple[str, ...]:
    """Return element-group edge names for a vector-crypto coverpoint suffix."""
    if suffix.endswith("subbytes_sm"):
        raise ValueError("SM4 subbyte coverpoints require correlated operand generation")
    if "subbytes" in suffix:
        return tuple(f"subbytes_{index}" for index in range(16))
    return ("zero", "ones", "walkeven", "walkodd", "random")


def crypto_edge_value(edge_name: str, width: int) -> int:
    if edge_name == "zero":
        return 0
    if edge_name == "ones":
        return (1 << width) - 1
    if edge_name == "walkeven":
        return sum(1 << index for index in range(0, width, 2))
    if edge_name == "walkodd":
        return sum(1 << index for index in range(1, width, 2))
    if edge_name == "random":
        return random_int(width, signed=False)
    raise ValueError(f"unknown vector-crypto edge {edge_name}")


def sm4_subbyte_targets() -> tuple[int, ...]:
    return tuple(sum((start + offset) << (8 * offset) for offset in range(4)) for start in range(0, 256, 4))


def make_and_register_vsm4k_subbyte_operand(target: int, test_data: TestData) -> tuple[str, int]:
    imm = random_int(5, signed=False)
    rk0 = random_int(32, signed=False)
    rk2 = random_int(32, signed=False)
    rk3 = random_int(32, signed=False)
    rk1 = _SM4_CK[4 * (imm & 0x7)] ^ rk2 ^ rk3 ^ target
    label = f"vs2_edge_vsm4k_{target:08x}"
    test_data.register_vector_data(label, 32, elements=[rk0, rk1, rk2, rk3])
    return label, imm


def make_and_register_vsm4r_subbyte_operands(
    target: int, test_data: TestData, *, label_suffix: str = "", vs2_value: int | None = None
) -> tuple[str, str]:
    suffix = f"_{label_suffix}" if label_suffix else ""
    if vs2_value is None:
        x1 = random_int(32, signed=False)
        x2 = random_int(32, signed=False)
        x3 = random_int(32, signed=False)
        rk0 = x1 ^ x2 ^ x3 ^ target
        vs2_elements = [
            rk0,
            random_int(32, signed=False),
            random_int(32, signed=False),
            random_int(32, signed=False),
        ]
        vs2_label = f"vs2_edge_vsm4r_{target:08x}{suffix}"
    else:
        vs2_elements = [(vs2_value >> (32 * index)) & 0xFFFF_FFFF for index in range(4)]
        x2 = random_int(32, signed=False)
        x3 = random_int(32, signed=False)
        x1 = x2 ^ x3 ^ target ^ vs2_elements[0]
        vs2_label = f"vs2_edge_vsm4r{suffix}"

    vd_elements = [random_int(32, signed=False), x1, x2, x3]
    vd_label = f"vd_edge_vsm4r_{target:08x}{suffix}"
    test_data.register_vector_data(vs2_label, 32, elements=vs2_elements)
    test_data.register_vector_data(vd_label, 32, elements=vd_elements)
    return vs2_label, vd_label


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
    else:
        value = crypto_edge_value(edge_name, width)
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
