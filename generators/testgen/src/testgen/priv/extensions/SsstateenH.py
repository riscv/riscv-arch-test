##################################
# priv/extensions/SsstateenH.py
#
# Ssstateen hypervisor tests that run in HS, VS and VU modes.
# David_Harris@hmc.edu 29 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""SsstateenH test generator.

The suite boots to HS-mode and leaves mstateen at its boot value, so it also runs on harts without Smstateen.
hstateen0 controls VS-mode and VU-mode access but not HS-mode access.  An access that only hstateen0 forbids raises
virtual instruction; so does any VU-mode access to an S or H CSR that HS-mode could make.
"""

from testgen.asm.csr import csr_walk_test
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.StateenHCommon import HSTATEEN0_ENVCFG, HSTATEEN0_SE0, hstateen0_bit, read_csrs
from testgen.priv.registry import add_priv_test_generator

STATEEN123 = [
    "sstateen1",
    "sstateen2",
    "sstateen3",
    "hstateen1",
    "hstateen2",
    "hstateen3",
    "hstateen1h",
    "hstateen2h",
    "hstateen3h",
]
# hstateen0 C, FCSR and JVT, which control the matching sstateen0 bits
HSTATEEN0_LOW = "(HSTATEEN0_CS | HSTATEEN0_FCSR | HSTATEEN0_JVT)"


def _covergroup(mode: str) -> str:
    return f"SsstateenH_{mode}_cg"


def _hstateen0_walk(test_data: TestData) -> list[str]:
    """Walk hstateen0 (and hstateen0h) from HS-mode.  C is left out of the check because custom state is optional."""
    coverpoint = "cp_hs_hstateen0_walk"
    return [
        comment_banner(
            coverpoint,
            "Walk a 1 and a 0 through hstateen0 (and hstateen0h) in HS-mode.  Bits whose mstateen0 bit is 0, or\n"
            "whose state the hart lacks, are read-only zero",
        ),
        *csr_walk_test(test_data, ("hstateen0", (1 << 64) - 2), _covergroup("hs"), coverpoint),
        "#if __riscv_xlen == 32",
        *csr_walk_test(test_data, ("hstateen0h", None), _covergroup("hs"), coverpoint),
        "#endif",
    ]


def _gate_tests(test_data: TestData, mode: str) -> list[str]:
    """Read sstateen0 and senvcfg in mode with hstateen0.SE0 and hstateen0.ENVCFG both 0 and both 1."""
    covergroup = _covergroup(mode)
    if mode == "hs":
        result = "hstateen0 does not control HS-mode, so both reads succeed"
    elif mode == "vs":
        result = "Virtual instruction when the hstateen0 bit is 0"
    else:
        result = "Always virtual instruction"
    lines = [
        comment_banner(
            f"cp_{mode}_sstateen0 and cp_{mode}_senvcfg",
            f"Read sstateen0 and senvcfg in {mode.upper()}-mode with hstateen0.SE0 = hstateen0.ENVCFG = 0 and 1.\n"
            f"{result}",
        ),
    ]
    for h in (0, 1):
        lines.extend(
            [
                *hstateen0_bit(test_data, HSTATEEN0_SE0, h),
                *hstateen0_bit(test_data, HSTATEEN0_ENVCFG, h),
                *([f"RVTEST_TSBI_GOTO_{mode.upper()}MODE"] if mode != "hs" else []),
                *read_csrs(test_data, ["sstateen0"], f"hse0_{h}", f"cp_{mode}_sstateen0", covergroup),
                *read_csrs(test_data, ["senvcfg"], f"henvcfg_{h}", f"cp_{mode}_senvcfg", covergroup),
                *(["RVTEST_TSBI_GOTO_SMODE"] if mode != "hs" else []),
            ]
        )
    return lines


def _stateen123_tests(test_data: TestData, mode: str) -> list[str]:
    """Read sstateen1-3 and hstateen1-3 (and the high halves) in mode, and in VS and VU modes hstateen0."""
    covergroup = _covergroup(mode)
    lines = [
        comment_banner(
            f"cp_{mode}_stateen123",
            f"Read sstateen1-3 and hstateen1-3 in {mode.upper()}-mode.  Bit 63 of the matching mstateen and hstateen\n"
            "CSRs controls access",
        ),
        *([f"RVTEST_TSBI_GOTO_{mode.upper()}MODE"] if mode != "hs" else []),
        *read_csrs(test_data, STATEEN123, mode, f"cp_{mode}_stateen123", covergroup),
    ]
    if mode != "hs":
        lines.extend(
            [
                comment_banner(
                    f"cp_{mode}_hstateen0",
                    f"Read hstateen0 (and hstateen0h) in {mode.upper()}-mode.  Virtual instruction when HS-mode could\n"
                    "read it",
                ),
                *read_csrs(test_data, ["hstateen0", "hstateen0h"], mode, f"cp_{mode}_hstateen0", covergroup),
                "RVTEST_TSBI_GOTO_SMODE",
            ]
        )
    return lines


def _sstateen0_roz_tests(test_data: TestData) -> list[str]:
    """sstateen0 bits whose hstateen0 bit is 0 read as zero in VS-mode.

    HS-mode writes sstateen0 while the hstateen0 bits are 1, then VS-mode reads it with them clear and set.
    """
    coverpoint = "cp_vs_sstateen0_roz"
    covergroup = _covergroup("vs")
    save_h, save_s, tmp_reg, rd = test_data.int_regs.get_registers(4)
    lines = [
        comment_banner(
            coverpoint,
            "With hstateen0.SE0 = 1, write all 1s to sstateen0 in HS-mode, then read it in VS-mode with hstateen0\n"
            "C, FCSR and JVT clear and set.  sstateen0 bits whose hstateen0 bit is 0 read as zero",
        ),
        f"csrr x{save_h}, hstateen0",
        f"csrr x{save_s}, sstateen0",
        *hstateen0_bit(test_data, HSTATEEN0_SE0, 1),
        f"LI(x{tmp_reg}, {HSTATEEN0_LOW})",
        f"csrs hstateen0, x{tmp_reg}",
        f"LI(x{tmp_reg}, -1)",
        f"csrw sstateen0, x{tmp_reg}",
    ]
    for h in (0, 1):
        lines.extend(
            [
                f"LI(x{tmp_reg}, {HSTATEEN0_LOW})",
                f"{'csrs' if h else 'csrc'} hstateen0, x{tmp_reg}",
                "RVTEST_TSBI_GOTO_VSMODE",
                f"LI(x{rd}, 42)",
                test_data.add_testcase(f"hlow_{h}", coverpoint, covergroup),
                f"csrr x{rd}, sstateen0",
                write_sigupd(rd, test_data),
                "RVTEST_TSBI_GOTO_SMODE",
            ]
        )
    lines.extend(
        [
            f"csrw sstateen0, x{save_s}",
            f"csrw hstateen0, x{save_h}",
        ]
    )
    test_data.int_regs.return_registers([save_h, save_s, tmp_reg, rd])
    return lines


@add_priv_test_generator(
    "SsstateenH",
    required_extensions=["H", "Ssstateen"],
    extra_defines=["#define BOOT_TO_SMODE"],
    # VS and VU traps need the visible trap handler
    params=["TIME_CSR_IMPLEMENTED: true"],
)
def make_ssstateenh(test_data: TestData) -> list[TestChunk]:
    """Generate tests for the SsstateenH suite."""
    test_chunks: list[TestChunk] = []

    tc = test_data.new_test_chunk(test_chunks, "hs")
    tc.code.extend([*_hstateen0_walk(test_data), *_gate_tests(test_data, "hs"), *_stateen123_tests(test_data, "hs")])

    tc = test_data.new_test_chunk(test_chunks, "vs")
    tc.code.extend(
        [*_gate_tests(test_data, "vs"), *_stateen123_tests(test_data, "vs"), *_sstateen0_roz_tests(test_data)]
    )

    tc = test_data.new_test_chunk(test_chunks, "vu")
    tc.code.extend([*_gate_tests(test_data, "vu"), *_stateen123_tests(test_data, "vu")])

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
