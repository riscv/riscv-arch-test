# Smstateen.py
# Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# Smstateen state-enable extension test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Smstateen privileged extension test generator."""

from dataclasses import replace

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.StateenCommon import (
    FEATURES,
    GateWrite,
    StateenFeature,
    feature_tests,
    illegal_access_tests,
    stateen_walk_tests,
    walk_tests,
)
from testgen.priv.registry import add_priv_test_generator

CG = "Smstateen_cg"
MSTATEEN_REGS = [f"mstateen{n}" for n in range(4)]
MSTATEENH_REGS = [f"{csr}h" for csr in MSTATEEN_REGS]
MODES = ["M", "U", "S", "VS", "VU"]
# TODO: Enable the skipped features once Sail models Smaia/Ssaia, Sscsrind, Zcmt and Smctr
# (feature, coverpoint)
FEATURE_COVERPOINTS = [
    ("envcfg", "cp_envcfg"),
    # ("csrind", "cp_csrind"),
    # ("imsic", "cp_imsic"),
    # ("aia", "cp_aia"),
    # ("jvt", "cp_jvt_access"),
    ("context", "cp_context"),
    ("p1p13", "cp_p1p13"),
    ("srmcfg", "cp_srmcfg"),
    # ("ctr", "cp_ctr"),
    ("fcsr", "cp_fcsr"),
    ("fp", "cp_fcsr_fp_instrs"),
]


def _mstateen_states(feat: StateenFeature, gate: str = "mstateen0") -> list[list[GateWrite]]:
    """Clear the bit in `gate`, then set it and the bit in each lower-level CSR.

    Clearing the bit in `gate` makes it read-only zero in the lower-level CSRs, so they must be set again.
    """
    return [[(gate, 0)], [(gate, 1), *((csr, 1) for csr in feat.lower_csrs)]]


def _se_tests(test_data: TestData, n: int, csr: str) -> list[str]:
    """Access `csr` with mstateen<n>.SE<n> set and clear: sstateen<n> from S and VS-mode, hstateen<n> from HS-mode."""
    if csr == "sstateen":
        feat = replace(FEATURES["se"], csrs=(f"sstateen{n}",), lower_csrs=(f"hstateen{n}",))
        cp, modes = "cp_mstateen_se_controls_sstateen", ["S", "VS"]
    else:
        feat = replace(
            FEATURES["se"], csrs=(f"hstateen{n}", f"hstateen{n}h"), guard="defined(H_SUPPORTED)", lower_csrs=()
        )
        cp, modes = "cp_mstateen_se_controls_hstateen", ["S"]
    return feature_tests(test_data, CG, cp, feat, states=_mstateen_states(feat, f"mstateen{n}"), modes=modes, base="M")


def _se0_only_walk(test_data: TestData, csr: str) -> list[str]:
    """Walk sstateen0 or hstateen0 from M-mode and S-mode with only mstateen0.SE0 set.

    The generator header requires S for sstateen0 and H for hstateen0.
    """
    cp = f"cp_mstateen0_se0_only_{csr}"
    walk = walk_tests(test_data, CG, cp, csr, modes=["M", "S"], base="M")
    save, saveh, tmp = test_data.int_regs.get_registers(3)
    lines = [
        f"csrr x{save}, mstateen0  # save mstateen0",
        "#if __riscv_xlen == 64",
        f"LI(x{tmp}, MSTATEEN_HSTATEEN)",
        f"csrw mstateen0, x{tmp}  # only SE0 set",
        "#else",
        f"csrr x{saveh}, mstateen0h  # save mstateen0h",
        "csrw mstateen0, zero",
        f"LI(x{tmp}, MSTATEENH_HSTATEEN)",
        f"csrw mstateen0h, x{tmp}  # only SE0 set",
        "#endif",
        *walk,
        f"csrw mstateen0, x{save}  # restore mstateen0",
        "#if __riscv_xlen == 32",
        f"csrw mstateen0h, x{saveh}  # restore mstateen0h",
        "#endif",
        f"mv x{save}, zero",
        f"mv x{saveh}, zero",
    ]
    test_data.int_regs.return_registers([save, saveh, tmp])
    return lines


@add_priv_test_generator(
    "Smstateen",
    required_extensions=["Smstateen", "Sm"],
    march_extensions=["Smstateen"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_smstateen(test_data: TestData) -> list[TestChunk]:
    """Generate tests for Smstateen state-enable extension testsuite.

    The boot code sets mstateen0-3, so each feature test clears and restores its own control bit.
    """
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()

    tc.code.extend(
        illegal_access_tests(
            test_data,
            CG,
            "cp_csr_illegal_accesses",
            MSTATEEN_REGS + MSTATEENH_REGS,
            modes=["U", "S", "VS", "VU"],
            base="M",
        )
    )
    for key, cp in FEATURE_COVERPOINTS:
        feat = FEATURES[key]
        tc = test_data.new_test_chunk(test_chunks)
        tc.code.extend(feature_tests(test_data, CG, cp, feat, states=_mstateen_states(feat), modes=MODES, base="M"))
    stateen_walk_tests(test_data, test_chunks, CG, "cp_walking_ones", MSTATEEN_REGS, base="M")
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks


def _se_csr_tests(test_data: TestData, csr: str) -> list[TestChunk]:
    """Access sstateen<n> or hstateen<n> under mstateen<n>.SE<n>, and walk the 0 register with only SE0 set."""
    test_chunks: list[TestChunk] = []
    for n in range(4):
        tc = test_data.new_test_chunk(test_chunks, csr if n == 0 else None)
        tc.code.extend(_se_tests(test_data, n, csr))
    tc = test_data.new_test_chunk(test_chunks)
    tc.code.extend(_se0_only_walk(test_data, f"{csr}0"))
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks


@add_priv_test_generator(
    "Smstateen",
    required_extensions=["Smstateen", "Sm", "S"],
    march_extensions=["Smstateen"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_smstateen_s(test_data: TestData) -> list[TestChunk]:
    """Generate Smstateen tests of sstateen, which exists only with S-mode."""
    return _se_csr_tests(test_data, "sstateen")


@add_priv_test_generator(
    "Smstateen",
    required_extensions=["Smstateen", "Sm", "H"],
    march_extensions=["Smstateen"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_smstateen_h(test_data: TestData) -> list[TestChunk]:
    """Generate Smstateen tests of hstateen, which exists only with H."""
    return _se_csr_tests(test_data, "hstateen")
