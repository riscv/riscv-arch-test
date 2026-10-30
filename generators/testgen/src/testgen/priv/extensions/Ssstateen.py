# Ssstateen.py
# Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# Ssstateen state-enable extension test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Ssstateen privileged extension test generator."""

from dataclasses import replace
from itertools import product

from testgen.asm.helpers import gated
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.StateenCommon import (
    FEATURES,
    feature_tests,
    illegal_access_tests,
    stateen_walk_tests,
    walk_tests,
)
from testgen.priv.registry import add_priv_test_generator

CG = "Ssstateen_cg"
SSTATEEN_REGS = [f"sstateen{n}" for n in range(4)]
# TODO: Check sstateen0.JVT again once Sail supports Zcmt.
SSTATEEN0_UNCHECKED_BITS = [(1 << 2, "ZCMT_SUPPORTED")]  # JVT
HSTATEEN_REGS = [f"hstateen{n}" for n in range(4)]
# Access from every mode to also check that a bit does not affect the modes it does not control
MODES = ["S", "U", "VS", "VU"]
# TODO: Enable the skipped features once Sail models Zcmt, Sscsrind, Ssaia and Smctr
# (feature, coverpoint), gated by hstateen0 and sstateen0
FEATURE_COVERPOINTS = [
    ("fcsr", "cp_fcsr"),
    ("fp", "cp_fcsr_fp_instrs"),
    # ("jvt", "cp_jvt"),
]
# (feature, coverpoint), gated by hstateen0 only
HSTATEEN_FEATURE_COVERPOINTS = [
    ("envcfg", "cp_hstateen_envcfg"),
    ("context", "cp_hstateen_context"),
    # ("csrind", "cp_hstateen_csrind"),
    # ("imsic", "cp_hstateen_imsic"),
    # ("aia", "cp_hstateen_aia"),
    # ("ctr", "cp_hstateen_ctr"),
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
    tc.code.extend(
        illegal_access_tests(test_data, CG, "cp_csr_illegal_accesses", SSTATEEN_REGS, modes=["U", "VU"], base="S")
    )
    for csr in SSTATEEN_REGS:
        tc = test_data.new_test_chunk(test_chunks)
        unchecked = SSTATEEN0_UNCHECKED_BITS if csr == "sstateen0" else None
        tc.code.extend(
            walk_tests(test_data, CG, "cp_walking_ones", csr, modes=["S"], base="S", unchecked_bits=unchecked)
        )
    # Every combination of the bit in the lower-level CSRs that have it (hstateen0 with H, sstateen0)
    for key, cp in FEATURE_COVERPOINTS + HSTATEEN_FEATURE_COVERPOINTS:
        feat = FEATURES[key]
        states = [list(zip(feat.lower_csrs, bits)) for bits in product((0, 1), repeat=len(feat.lower_csrs))]
        guard = None if (key, cp) in FEATURE_COVERPOINTS else "defined(H_SUPPORTED)"
        tc = test_data.new_test_chunk(test_chunks)
        tc.code.extend(gated(feature_tests(test_data, CG, cp, feat, states=states, modes=MODES, base="S"), guard))

    tc = test_data.new_test_chunk(test_chunks)
    tc.code.extend(
        gated(
            illegal_access_tests(
                test_data,
                CG,
                "cp_hstateen_illegal_accesses",
                HSTATEEN_REGS + [f"{csr}h" for csr in HSTATEEN_REGS],
                modes=["U", "VS", "VU"],
                base="S",
            ),
            "defined(H_SUPPORTED)",
        )
    )
    stateen_walk_tests(
        test_data, test_chunks, CG, "cp_hstateen_walking_ones", HSTATEEN_REGS, base="S", guard="defined(H_SUPPORTED)"
    )
    for n in range(4):
        feat = replace(FEATURES["se"], csrs=(f"sstateen{n}",), guard="defined(H_SUPPORTED)")
        states = [[(f"hstateen{n}", 0)], [(f"hstateen{n}", 1)]]
        tc = test_data.new_test_chunk(test_chunks)
        tc.code.extend(
            feature_tests(
                test_data, CG, "cp_hstateen_se_controls_sstateen", feat, states=states, modes=["S", "VS"], base="S"
            )
        )
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
