# Smstateen.py
# Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# Smstateen state-enable extension test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Smstateen privileged extension test generator."""

from dataclasses import replace

from testgen.asm.helpers import comment_banner, gated, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.StateenCommon import (
    FEATURES,
    GateWrite,
    StateenFeature,
    _mode_block,
    _write_bit,
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
        # hstateen<n>.SE<n> reads as zero while mstateen<n>.SE<n> = 0, and whether it keeps its value is unspecified,
        # so set it again after mstateen<n>.SE<n> is set again.
        feat = replace(
            FEATURES["se"],
            csrs=(f"hstateen{n}", f"hstateen{n}h"),
            guard="defined(H_SUPPORTED)",
            lower_csrs=(f"hstateen{n}",),
        )
        cp, modes = "cp_mstateen_se_controls_hstateen", ["S"]
    return feature_tests(test_data, CG, cp, feat, states=_mstateen_states(feat, f"mstateen{n}"), modes=modes, base="M")


def _se0_virtual_tests(test_data: TestData) -> list[str]:
    """With mstateen<n>.SE<n> = 0, read hstateen<n> (and hstateen<n>h on RV32) from VS-mode and VU-mode, and sstateen<n>
    from VU-mode.

    The same read is illegal in HS-mode, so it is not HS-qualified and raises illegal instruction, not virtual
    instruction.  rd keeps its value.  hstateen<n>.SE<n> is read-only zero while mstateen<n>.SE<n> = 0, so hstateen<n> is
    saved and restored with mstateen<n>.
    """
    saves = test_data.int_regs.get_registers(4)
    rd, tmp = test_data.int_regs.get_registers(2)

    def rv32_gated(csr: str, body: list[str]) -> list[str]:
        """body, only on RV32 when csr is a high half."""
        return gated(body, "__riscv_xlen == 32") if csr.endswith("h") else body

    def read(csr: str, mode: str, cp: str) -> list[str]:
        body = [
            f"LI(x{rd}, 42)",
            test_data.add_testcase(f"{mode.lower()}_{csr}", cp, CG),
            f"csrr x{rd}, {csr}",
            write_sigupd(rd, test_data),
        ]
        return rv32_gated(csr, body)

    lines = [
        comment_banner(
            "cp_mstateen_se0_hstateen_virtual, cp_mstateen_se0_sstateen_vu",
            "With mstateen<n>.SE<n> = 0, read hstateen<n> from VS-mode and VU-mode and sstateen<n> from VU-mode.\n"
            "Each raises illegal instruction, because the same read is illegal in HS-mode",
        )
    ]
    for n in range(4):
        gates = [f"{level}stateen{n}{half}" for level in "mh" for half in ("", "h")]
        for csr, reg in zip(gates, saves):
            lines.extend(rv32_gated(csr, [f"csrr x{reg}, {csr}  # save {csr}"]))
        lines.extend(_write_bit(f"mstateen{n}", FEATURES["se"], on=False, reg=tmp))
        for mode in ("VS", "VU"):
            body = [
                line
                for half in ("", "h")
                for line in read(f"hstateen{n}{half}", mode, "cp_mstateen_se0_hstateen_virtual")
            ]
            if mode == "VU":
                body.extend(read(f"sstateen{n}", mode, "cp_mstateen_se0_sstateen_vu"))
            lines.extend(_mode_block(mode, "M", body))
        for csr, reg in zip(gates, saves):
            lines.extend(rv32_gated(csr, [f"csrw {csr}, x{reg}  # restore {csr}"]))
    lines.extend(f"mv x{reg}, zero  # do not leave a stateen value in a register" for reg in saves)
    test_data.int_regs.return_registers([*saves, rd, tmp])
    return gated(lines, "defined(H_SUPPORTED)")


def _se0_only_walk(test_data: TestData, csr: str, guard: str) -> list[str]:
    """Walk sstateen0 or hstateen0 from M-mode and S-mode with only mstateen0.SE0 set."""
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
    return gated(lines, guard)


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
    for csr in ("sstateen", "hstateen"):
        for n in range(4):
            tc = test_data.new_test_chunk(test_chunks)
            tc.code.extend(_se_tests(test_data, n, csr))
    tc = test_data.new_test_chunk(test_chunks)
    tc.code.extend(_se0_virtual_tests(test_data))
    tc = test_data.new_test_chunk(test_chunks)
    tc.code.extend(_se0_only_walk(test_data, "sstateen0", "defined(S_SUPPORTED)"))
    tc = test_data.new_test_chunk(test_chunks)
    tc.code.extend(_se0_only_walk(test_data, "hstateen0", "defined(H_SUPPORTED)"))
    stateen_walk_tests(test_data, test_chunks, CG, "cp_walking_ones", MSTATEEN_REGS, base="M")
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
