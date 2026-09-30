##################################
# priv/extensions/SmstateenH.py
#
# Smstateen hypervisor tests that run in HS, VS and VU modes.
# David_Harris@hmc.edu 29 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""SmstateenH test generator.

The suite boots to HS-mode and writes mstateen0 through T-SBI.  An mstateen0 bit of 0 makes the matching hstateen0
bit read-only zero and makes the state it controls illegal to access below M-mode.  When the mstateen0 bit is 1, a
VS-mode or VU-mode access that hstateen0 or the H extension forbids raises virtual instruction instead.
"""

from itertools import product

from testgen.asm.csr import csr_walk_test
from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.StateenHCommon import (
    HSTATEEN0_ENVCFG,
    HSTATEEN0_SE0,
    MSTATEEN0_ENVCFG,
    MSTATEEN0_P1P13,
    MSTATEEN0_SE0,
    hstateen0_bit,
    mstateen0_bit,
    read_in_mode,
)
from testgen.priv.registry import add_priv_test_generator

# hstateen0 bits checked by the walk with every mstateen0 bit set: all but C (custom state is optional) and CTR,
# CONTEXT, IMSIC, AIA and CSRIND, whose state Sail does not model (riscv/sail-riscv#222, #956)
HSTATEEN0_ALL_MASK = 0xE1BFFFFFFFFFFFFE


def _covergroup(mode: str) -> str:
    return f"SmstateenH_{mode}_cg"


def _gate_tests(
    test_data: TestData,
    mode: str,
    name: str,
    mbit: tuple[str, str],
    hbit: tuple[str, str] | None,
    csrs: list[str],
) -> list[str]:
    """Read each CSR in mode for every reachable value of the mstateen0 bit and the matching hstateen0 bit.

    The hstateen0 bit is written while the mstateen0 bit is 1, because hstateen0 is read-only zero, and for SE0
    inaccessible, when it is 0.  Both bits are 1 afterwards, as at boot.
    """
    coverpoint = f"cp_{mode}_mstateen0_{name}"
    states = [(m, h) for m, h in product((0, 1), repeat=2) if h <= m] if hbit else [(0, 0), (1, 0)]
    lines = [
        comment_banner(
            coverpoint,
            f"Read {', '.join(csrs)} in {mode.upper()}-mode for each value of mstateen0.{name.upper()}"
            + (f" and hstateen0.{name.upper()}" if hbit else "")
            + ".\nIllegal instruction when the mstateen0 bit is 0",
        ),
    ]
    for m, h in states:
        suffix = f"m{m}_h{h}" if hbit else f"m{m}"
        lines.extend(
            [
                *mstateen0_bit(mbit, 1),
                *(hstateen0_bit(test_data, hbit, h) if hbit else []),
                *mstateen0_bit(mbit, m),
                *read_in_mode(test_data, mode, csrs, suffix, coverpoint, _covergroup(mode)),
            ]
        )
    lines.extend([*mstateen0_bit(mbit, 1), *(hstateen0_bit(test_data, hbit, 1) if hbit else [])])
    return lines


def _mode_tests(test_data: TestData, mode: str) -> list[str]:
    """Access control by mstateen0.SE0, ENVCFG and P1P13 in mode."""
    lines = [
        *_gate_tests(test_data, mode, "se0", MSTATEEN0_SE0, HSTATEEN0_SE0, ["sstateen0", "hstateen0", "hstateen0h"]),
        *_gate_tests(test_data, mode, "envcfg", MSTATEEN0_ENVCFG, HSTATEEN0_ENVCFG, ["senvcfg", "henvcfg", "henvcfgh"]),
    ]
    if mode != "hs":
        lines.extend(_gate_tests(test_data, mode, "p1p13", MSTATEEN0_P1P13, None, ["hedelegh"]))
    return lines


def _hstateen0_roz_tests(test_data: TestData) -> list[str]:
    """Walk hstateen0 (and hstateen0h) with only mstateen0.SE0 set and with every mstateen0 bit set.

    Afterwards mstateen0 and hstateen0 are set as at boot, because the walks leave the hstateen0 bits whose mstateen0
    bit was 0 unspecified.
    """
    covergroup = _covergroup("hs")
    lines = []
    for all_set in (False, True):
        coverpoint = "cp_hs_hstateen0_walk" if all_set else "cp_hs_hstateen0_roz"
        lines.extend(
            [
                comment_banner(
                    coverpoint,
                    "Walk a 1 and a 0 through hstateen0 (and hstateen0h) in HS-mode with "
                    + (
                        "every mstateen0 bit set"
                        if all_set
                        else "only mstateen0.SE0 set.\nhstateen0 bits whose mstateen0 bit is 0 are read-only zero"
                    ),
                ),
                "#if __riscv_xlen == 64",
                f"RVTEST_TSBI_CSR_WRITE(CSR_MSTATEEN0, {-1 if all_set else 'MSTATEEN_HSTATEEN'})",
                "#else",
                f"RVTEST_TSBI_CSR_WRITE(CSR_MSTATEEN0, {-1 if all_set else 0})",
                f"RVTEST_TSBI_CSR_WRITE(CSR_MSTATEEN0H, {-1 if all_set else 'MSTATEENH_HSTATEEN'})",
                "#endif",
                *csr_walk_test(
                    test_data, ("hstateen0", HSTATEEN0_ALL_MASK if all_set else None), covergroup, coverpoint
                ),
                "#if __riscv_xlen == 32",
                *csr_walk_test(
                    test_data, ("hstateen0h", HSTATEEN0_ALL_MASK >> 32 if all_set else None), covergroup, coverpoint
                ),
                "#endif",
            ]
        )
    tmp_reg = test_data.int_regs.get_register()
    lines.extend(
        [
            "#if __riscv_xlen == 64",
            "RVTEST_TSBI_CSR_WRITE(CSR_MSTATEEN0, MSTATEEN_HSTATEEN | MSTATEEN0_HENVCFG | MSTATEEN0_JVT)",
            "#else",
            "RVTEST_TSBI_CSR_WRITE(CSR_MSTATEEN0, MSTATEEN0_JVT)",
            "RVTEST_TSBI_CSR_WRITE(CSR_MSTATEEN0H, MSTATEENH_HSTATEEN | MSTATEEN0H_HENVCFG)",
            "#endif",
            "#ifdef ZFINX_SUPPORTED",
            "RVTEST_TSBI_CSR_SET(CSR_MSTATEEN0, MSTATEEN0_FCSR)",
            "#endif",
            "#if __riscv_xlen == 64",
            f"LI(x{tmp_reg}, HSTATEEN_SSTATEEN | HSTATEEN0_SENVCFG | HSTATEEN0_JVT | HSTATEEN0_FCSR)",
            f"csrw hstateen0, x{tmp_reg}",
            "#else",
            f"LI(x{tmp_reg}, HSTATEEN0_JVT | HSTATEEN0_FCSR)",
            f"csrw hstateen0, x{tmp_reg}",
            f"LI(x{tmp_reg}, HSTATEENH_SSTATEEN | HSTATEEN0H_SENVCFG)",
            f"csrw hstateen0h, x{tmp_reg}",
            "#endif",
        ]
    )
    test_data.int_regs.return_register(tmp_reg)
    return lines


@add_priv_test_generator(
    "SmstateenH",
    required_extensions=["H", "Smstateen"],
    extra_defines=["#define BOOT_TO_SMODE"],
    # VS and VU traps need the visible trap handler
    params=["TIME_CSR_IMPLEMENTED: true"],
)
def make_smstateenh(test_data: TestData) -> list[TestChunk]:
    """Generate tests for the SmstateenH suite."""
    test_chunks: list[TestChunk] = []

    tc = test_data.new_test_chunk(test_chunks, "hs")
    tc.code.extend([*_mode_tests(test_data, "hs"), *_hstateen0_roz_tests(test_data)])

    for mode in ("vs", "vu"):
        tc = test_data.new_test_chunk(test_chunks, mode)
        tc.code.extend(_mode_tests(test_data, mode))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
