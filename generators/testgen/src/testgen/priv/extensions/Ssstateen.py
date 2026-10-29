# Ssstateen.py
# Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# Ssstateen state-enable extension test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Ssstateen privileged extension test generator."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.StateenCommon import (
    FEATURES,
    feature_tests,
    illegal_access_tests,
    walk_tests,
)
from testgen.priv.registry import add_priv_test_generator

CG = "Ssstateen_cg"
SSTATEEN_REGS = [f"sstateen{n}" for n in range(4)]
# TODO: Check sstateen0.JVT again once Sail supports Zcmt.
SSTATEEN0_UNCHECKED_BITS = [(1 << 2, "ZCMT_SUPPORTED")]  # JVT
# (feature, coverpoint)
# TODO: re-enable jvt once Sail support Zcmt
FEATURE_COVERPOINTS = [
    ("fcsr", "cp_fcsr_lower"),
    ("fp", "cp_fcsr_fp_instrs"),
    # ("jvt", "cp_jvt"),
]


@add_priv_test_generator(
    "Ssstateen",
    required_extensions=["Ssstateen"],
    march_extensions=["Ssstateen"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_ssstateen(test_data: TestData) -> list[TestChunk]:
    """Generate tests for Ssstateen state-enable extension testsuite."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()
    tc.code.extend(illegal_access_tests(test_data, CG, "cp_csr_illegal_accesses", SSTATEEN_REGS, modes=["U"], base="S"))
    for csr in SSTATEEN_REGS:
        tc = test_data.new_test_chunk(test_chunks)
        unchecked = SSTATEEN0_UNCHECKED_BITS if csr == "sstateen0" else None
        tc.code.extend(
            walk_tests(test_data, CG, "cp_walking_ones", csr, modes=["S"], base="S", unchecked_bits=unchecked)
        )
    for key, cp in FEATURE_COVERPOINTS:
        tc = test_data.new_test_chunk(test_chunks)
        tc.code.extend(feature_tests(test_data, CG, cp, FEATURES[key], gate="sstateen0", modes=["S", "U"], base="S"))
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
