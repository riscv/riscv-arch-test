##################################
# priv/extensions/SmstateenH.py
#
# Smstateen H group: mstateen tests that run in M, HS, VS and VU modes.
# David_Harris@hmc.edu 29 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Smstateen H group test generator.

The group boots to HS-mode and writes mstateen0 through T-SBI.  An mstateen0 bit of 0 makes the matching hstateen0
bit read-only zero and makes the state it controls illegal to access below M-mode.  When the mstateen0 bit is 1, a
VS-mode or VU-mode access that hstateen0 or the H extension forbids raises virtual instruction instead.

A VS-mode or VU-mode access to hedelegh (RV32) with mstateen0.P1P13 = 0 raises illegal instruction: hedelegh then
does not exist, so the high-half hypervisor CSR rule does not apply and the usual HS-qualified rule does
(riscv/riscv-isa-manual#3459).

Bit 63 of mstateen1-3 controls access to sstateen1-3 and hstateen1-3 below M-mode.  In M-mode, it makes bit 63 of
the matching hstateen CSR writable (1) or read-only zero (0).
"""

from itertools import product

from testgen.asm.csr import csr_walk_test
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.StateenHCommon import (
    HSTATEEN0_ENVCFG,
    HSTATEEN0_SE0,
    MSTATEEN0_ENVCFG,
    MSTATEEN0_P1P13,
    MSTATEEN0_SE0,
    STATEEN123,
    STATEEN123_N,
    access_csrs,
    hstateen0_bit,
    hstateen123_bit63,
    mstateen0_bit,
    mstateen123_bit63,
    read_in_mode,
    set_stateen_state,
)
from testgen.priv.registry import add_priv_test_generator

# hstateen0 bits checked by the walk with every mstateen0 bit set: all but C (custom state is optional) and CTR,
# IMSIC, AIA and CSRIND, whose state Sail does not model (riscv/sail-riscv#222, #956)
HSTATEEN0_ALL_MASK = 0xE3BFFFFFFFFFFFFE


_CG = "Smstateen_H_cg"


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
                *read_in_mode(test_data, mode, csrs, suffix, coverpoint, _CG),
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
    lines.extend(_mstateen123_tests(test_data, mode))
    return lines


def _mstateen123_tests(test_data: TestData, mode: str) -> list[str]:
    """Access sstateen1-3 and hstateen1-3 (and the high halves) in mode with bit 63 of mstateen1-3 = 0 and 1.

    Bit 63 of hstateen1-3 is set while the mstateen bit is 1, so that only the mstateen bit decides VS-mode access to
    sstateen1-3.  Both bits are 1 afterwards.
    """
    coverpoint = f"cp_{mode}_mstateen123"
    if mode == "hs":
        result = "the access succeeds"
    elif mode == "vs":
        result = "virtual instruction for hstateen1-3, and the sstateen access succeeds"
    else:
        result = "virtual instruction"
    lines = [
        comment_banner(
            coverpoint,
            f"Read, write, clear and set sstateen1-3 and hstateen1-3 in {mode.upper()}-mode with bit 63 of mstateen1-3\n"
            f"= 0 and 1 and bit 63 of hstateen1-3 set.  Illegal instruction when the mstateen bit is 0; else {result}",
        ),
    ]
    for m in (0, 1):
        lines.extend(
            [
                f"# mstateen1-3 bit 63 = {m}",
                *mstateen123_bit63(test_data, 1),
                *hstateen123_bit63(test_data, 1),
                *mstateen123_bit63(test_data, m),
                *([f"RVTEST_TSBI_GOTO_{mode.upper()}MODE"] if mode != "hs" else []),
                *access_csrs(test_data, STATEEN123, f"m{m}", coverpoint, _CG),
                *(["RVTEST_TSBI_GOTO_SMODE"] if mode != "hs" else []),
            ]
        )
    return lines


def _hstateen0_roz_tests(test_data: TestData) -> list[str]:
    """Walk hstateen0 (and hstateen0h) with only mstateen0.SE0 set and with every mstateen0 bit set.

    Afterwards mstateen0 and hstateen0 are set to the suite's starting state, because the walks leave the hstateen0
    bits whose mstateen0 bit was 0 unspecified.
    """
    covergroup = _CG
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
    lines.extend(set_stateen_state(test_data))
    return lines


def _hstateen123_m_tests(test_data: TestData) -> list[str]:
    """In M-mode, set and clear bit 63 of hstateen1-3 with bit 63 of mstateen1-3 = 1 and then 0, reading both back.

    Bit 63 of each hstateen CSR is writable while the matching mstateen bit is 1 and reads as zero while it is 0.  The
    hstateen bit is set before mstateen bit 63 is cleared, so the first read with it clear shows the read-only zero.
    Afterwards bit 63 of mstateen1-3 is set again and hstateen1-3 are left with an unspecified bit 63.
    """
    coverpoint = "cp_m_hstateen123_bit63"
    covergroup = _CG
    rd, mask = test_data.int_regs.get_registers(2)
    lines = [
        comment_banner(
            coverpoint,
            "In M-mode, set and clear bit 63 of hstateen1-3 (bit 31 of hstateen1h-3h on RV32) with bit 63 of the\n"
            "matching mstateen CSR = 1 and 0, and read both back.  The hstateen bit is writable when the mstateen bit\n"
            "is 1, and reads as zero when it is 0",
        ),
        "RVTEST_TSBI_GOTO_MMODE",
    ]
    for xlen, half, bit in ((64, "", "MSTATEEN_HSTATEEN"), (32, "h", "MSTATEENH_HSTATEEN")):
        lines.extend([f"#if __riscv_xlen == {xlen}", f"LI(x{mask}, {bit})"])
        for n in STATEEN123_N:
            mcsr, hcsr = f"mstateen{n}{half}", f"hstateen{n}{half}"
            for m in (1, 0):
                lines.extend(
                    [
                        f"{'csrs' if m else 'csrc'} {mcsr}, x{mask}",
                        test_data.add_testcase(f"{mcsr}_m{m}", coverpoint, covergroup),
                        f"csrr x{rd}, {mcsr}",
                        write_sigupd(rd, test_data),
                    ]
                )
                if not m:
                    lines.extend(
                        [
                            test_data.add_testcase(f"{hcsr}_roz", coverpoint, covergroup),
                            f"csrr x{rd}, {hcsr}",
                            write_sigupd(rd, test_data),
                        ]
                    )
                for op in ("csrc", "csrs") if m else ("csrs", "csrc"):
                    lines.extend(
                        [
                            test_data.add_testcase(f"{hcsr}_{op}_m{m}", coverpoint, covergroup),
                            f"{op} {hcsr}, x{mask}",
                            f"csrr x{rd}, {hcsr}",
                            write_sigupd(rd, test_data),
                        ]
                    )
            lines.append(f"csrs {mcsr}, x{mask}")
        lines.append("#endif")
    lines.append("RVTEST_TSBI_GOTO_SMODE")
    test_data.int_regs.return_registers([rd, mask])
    return lines


@add_priv_test_generator(
    "Smstateen",
    required_extensions=["H", "Smstateen"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_smstateenh(test_data: TestData) -> list[TestChunk]:
    """Generate the Smstateen H group tests in HS, VS, VU and M modes."""
    test_chunks: list[TestChunk] = []

    tc = test_data.new_test_chunk(test_chunks, "H_hs")
    tc.code.extend([*set_stateen_state(test_data), *_mode_tests(test_data, "hs"), *_hstateen0_roz_tests(test_data)])

    for mode in ("vs", "vu"):
        tc = test_data.new_test_chunk(test_chunks, f"H_{mode}")
        tc.code.extend(_mode_tests(test_data, mode))

    tc = test_data.new_test_chunk(test_chunks, "H_m")
    tc.code.extend(_hstateen123_m_tests(test_data))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
