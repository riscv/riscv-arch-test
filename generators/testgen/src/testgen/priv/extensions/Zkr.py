##################################
# priv/extensions/Zkr.py
# Zkr privileged test generators: seed CSR tests for the Sm, S, U and H groups.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Zkr test generators.

The shared test-case generators are called with mode in {"M", "S", "U"}. The H group runs the seed accesses in
VS-mode and VU-mode, where every access traps.
"""

from collections.abc import Iterator

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.asm.tsbi import tsbi_call_or_direct
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator


def _record_seed_reserved(dest_reg: int, test_data: TestData) -> list[str]:
    """Write seed[29:24] to the signature."""
    return [
        f"srli x{dest_reg}, x{dest_reg}, 24",
        f"andi x{dest_reg}, x{dest_reg}, 0x3f",
        write_sigupd(dest_reg, test_data),
    ]


# (op, is_immediate) for each CSR op to test on seed
_SEED_CSR_OPS = (
    ("csrrs", False),
    ("csrrc", False),
    ("csrrwi", True),  # not a read of seed, so it does not trap where seed is accessible
    ("csrrsi", True),
    ("csrrci", True),
    ("csrrw", False),  # not a read of seed, so it does not trap where seed is accessible
)


def _seed_csr_ops(dest_reg: int, rs1_reg: int) -> Iterator[tuple[str, int, str]]:
    """(op, rs1/uimm value, instruction) for each op in _SEED_CSR_OPS with rs1/uimm = 0 and nonzero."""
    for op, is_imm in _SEED_CSR_OPS:
        for rs1_imm_val in (0, 1):
            rs1 = rs1_imm_val if is_imm else ("x0" if rs1_imm_val == 0 else f"x{rs1_reg}")
            yield op, rs1_imm_val, f"{op} x{dest_reg}, seed, {rs1}"


def _gate(mode: str, lines: list[str]) -> list[str]:
    """In the M-mode suite the mseccfg SEED bits only exist when a lower mode does."""
    return ["#ifdef U_SUPPORTED", *lines, "#endif"] if mode == "M" else lines


def gen_seed_csrrw_tests(test_data: TestData, covergroup: str, mode: str) -> list[str]:
    """csrrw seed in this suite's mode for each of the 4 mseccfg (sseed x useed) combinations.

    In M-mode every access is legal; in S-mode it is legal only when mseccfg.sseed=1 and in U-mode
    only when mseccfg.useed=1 -- the other combinations take the expected illegal-instruction trap.
    """
    coverpoint = "cp_zkr_seed_csrrw"

    dest_reg, mseccfg_reg, src_reg, save_reg = test_data.int_regs.get_registers(4)

    lines = [
        comment_banner(coverpoint, f"csrrw seed in {mode}-mode across mseccfg.sseed/useed"),
        f"LI(x{src_reg}, 0)",
        *_gate(mode, [tsbi_call_or_direct(f"csrr x{save_reg}, mseccfg", mode)]),
    ]

    for sseed in (0, 1):
        for useed in (0, 1):
            mseccfg_val = (sseed << 9) | (useed << 8)
            tag = f"sseed{sseed}_useed{useed}"

            lines.extend(
                [
                    f"# mseccfg: sseed={sseed}, useed={useed}",
                    *_gate(
                        mode,
                        [
                            f"LI(x{mseccfg_reg}, {mseccfg_val})",
                            tsbi_call_or_direct(f"csrw mseccfg, x{mseccfg_reg}", mode),
                        ],
                    ),
                    # Test both rs1 fields and record the reserved read-only-zero bits in rd.
                    f"LI(x{dest_reg}, -1)",
                    test_data.add_testcase(f"{mode}_{tag}", coverpoint, covergroup),
                    f"csrrw x{dest_reg}, seed, x{src_reg}",
                    *_record_seed_reserved(dest_reg, test_data),
                    f"LI(x{dest_reg}, -1)",
                    test_data.add_testcase(f"{mode}_zero_{tag}", coverpoint, covergroup),
                    f"csrrw x{dest_reg}, seed, x0",
                    *_record_seed_reserved(dest_reg, test_data),
                ]
            )

    lines.extend(_gate(mode, [tsbi_call_or_direct(f"csrw mseccfg, x{save_reg}", mode)]))

    test_data.int_regs.return_registers([dest_reg, mseccfg_reg, src_reg, save_reg])
    return lines


def gen_seed_illegal_csr_op_tests(test_data: TestData, covergroup: str, mode: str) -> list[str]:
    """CSR ops on seed in this suite's mode; only the read-only forms cause an illegal instruction."""
    coverpoint = "cp_zkr_seed_illegal_csr_op"

    dest_reg, mseccfg_reg, rs1_reg, save_reg = test_data.int_regs.get_registers(4)

    sseed_useed_enabled = (1 << 9) | (1 << 8)
    lines = [
        comment_banner(coverpoint, f"CSR ops on seed in {mode}-mode; only the read-only forms trap"),
        *_gate(
            mode,
            [
                tsbi_call_or_direct(f"csrr x{save_reg}, mseccfg", mode),
                f"LI(x{mseccfg_reg}, {sseed_useed_enabled})",
                tsbi_call_or_direct(f"csrw mseccfg, x{mseccfg_reg} # enable seed access from all modes", mode),
            ],
        ),
        f"LI(x{rs1_reg}, 0)",
    ]

    for op, rs1_imm_val, instr in _seed_csr_ops(dest_reg, rs1_reg):
        lines.extend(
            [
                test_data.add_testcase(f"{mode}_{op}_rs1imm{rs1_imm_val}", coverpoint, covergroup),
                instr,
            ]
        )

    lines.extend(_gate(mode, [tsbi_call_or_direct(f"csrw mseccfg, x{save_reg}", mode)]))

    test_data.int_regs.return_registers([dest_reg, mseccfg_reg, rs1_reg, save_reg])
    return lines


def gen_seed_entropy_zero_non_es16_tests(test_data: TestData, covergroup: str, mode: str) -> list[str]:
    """Read seed twice in a row using csrrw, 100 times.
    Fail on OPST == DEAD. If OPST is WAIT/BIST, fail when entropy bits are nonzero.
    Always SIGUPD 0xB0BA on success so the scorecard does not depend on OPST.
    """
    coverpoint = "cp_zkr_seed_entropy_zero_non_es16"

    loop_count = 100

    read_reg, opst_reg, entropy_reg, cmp_reg = test_data.int_regs.get_registers(4)
    save_reg = test_data.int_regs.get_register()
    loop_reg = test_data.int_regs.get_register()

    sseed_useed_enabled = (1 << 9) | (1 << 8)
    lines = [
        comment_banner(coverpoint, gen_seed_entropy_zero_non_es16_tests.__doc__),
        *_gate(
            mode,
            [
                tsbi_call_or_direct(f"csrr x{save_reg}, mseccfg", mode),
                f"LI(x{cmp_reg}, {sseed_useed_enabled})",
                tsbi_call_or_direct(f"csrw mseccfg, x{cmp_reg}", mode),
            ],
        ),
        test_data.add_testcase(f"{mode}_es16", coverpoint, covergroup),
        f"LI(x{loop_reg}, {loop_count})",
        ".Lzkr_seed_entropy_loop:",
        f"csrrw x{read_reg}, seed, zero",
        f"csrrw x{read_reg}, seed, zero",
        "# OPST bits",
        f"srli x{opst_reg}, x{read_reg}, 0x1E",
        "# entropy bits",
        f"LI(x{entropy_reg}, 0xFFFF)",
        f"and x{entropy_reg}, x{entropy_reg}, x{read_reg}",
        "# DEAD (OPST == 3)",
        f"LI(x{cmp_reg}, 0x3)",
        f"beq x{opst_reg}, x{cmp_reg}, .Lzkr_seed_entropy_dead",
        "# ES16 (OPST == 2): skip the empty-source leak check",
        f"LI(x{cmp_reg}, 0x2)",
        f"beq x{opst_reg}, x{cmp_reg}, .Lzkr_seed_entropy_ok",
        "# WAIT/BIST: entropy must be 0 (spec seed_entropy_zero_non_es16)",
        f"bnez x{entropy_reg}, .Lzkr_seed_entropy_leak",
        ".Lzkr_seed_entropy_ok:",
        f"addi x{loop_reg}, x{loop_reg}, -1",
        f"bnez x{loop_reg}, .Lzkr_seed_entropy_loop",
        "# Same success token for ES16 and for WAIT/BIST with entropy 0",
        f"LI(x{cmp_reg}, 0xB0BA)",
        write_sigupd(cmp_reg, test_data),
        "j .Lzkr_seed_entropy_done",
        ".Lzkr_seed_entropy_dead:",
        "# DEAD: SIGUPD 0xDEAD vs Sail 0xB0BA",
        f"LI(x{cmp_reg}, 0xDEAD)",
        write_sigupd(cmp_reg, test_data),
        "j .Lzkr_seed_entropy_done",
        ".Lzkr_seed_entropy_leak:",
        "# Nonzero entropy while WAIT/BIST: SIGUPD leaked bits vs Sail 0xB0BA",
        write_sigupd(entropy_reg, test_data),
        ".Lzkr_seed_entropy_done:",
        *_gate(mode, [tsbi_call_or_direct(f"csrw mseccfg, x{save_reg}", mode)]),
    ]

    test_data.int_regs.return_registers([read_reg, opst_reg, entropy_reg, cmp_reg, save_reg, loop_reg])
    return lines


def gen_seed_virtual_access_tests(test_data: TestData, covergroup: str, mode: str) -> list[str]:
    """CSR ops on seed in VS-mode or VU-mode for each of the 4 mseccfg (sseed x useed) combinations.

    At V=1 only mseccfg.sseed matters and every access traps. With sseed=0 the access is not HS-qualified,
    so it raises an illegal-instruction exception. With sseed=1 the read-write forms are HS-qualified and
    raise a virtual-instruction exception, while the read-only forms (csrrs/csrrc with rs1=x0,
    csrrsi/csrrci with uimm=0) still raise an illegal-instruction exception. rd is recorded to check that
    the trapping access leaves it unchanged.
    """
    coverpoint = "cp_zkr_seed_access_h"

    dest_reg, mseccfg_reg, rs1_reg, save_reg = test_data.int_regs.get_registers(4)

    lines = [
        comment_banner(coverpoint, f"CSR ops on seed in {mode}-mode across mseccfg.sseed/useed; every access traps"),
        tsbi_call_or_direct(f"csrr x{save_reg}, mseccfg", mode),
        f"LI(x{rs1_reg}, 0)",
    ]

    for sseed in (0, 1):
        for useed in (0, 1):
            mseccfg_val = (sseed << 9) | (useed << 8)
            lines.extend(
                [
                    f"# mseccfg: sseed={sseed}, useed={useed}",
                    f"LI(x{mseccfg_reg}, {mseccfg_val})",
                    tsbi_call_or_direct(f"csrw mseccfg, x{mseccfg_reg}", mode),
                ]
            )
            for op, rs1_imm_val, instr in _seed_csr_ops(dest_reg, rs1_reg):
                tag = f"{mode}_{op}_rs1imm{rs1_imm_val}_sseed{sseed}_useed{useed}"
                lines.extend(
                    [
                        f"LI(x{dest_reg}, -1)",
                        test_data.add_testcase(tag, coverpoint, covergroup),
                        instr,
                        write_sigupd(dest_reg, test_data),
                    ]
                )

    lines.append(tsbi_call_or_direct(f"csrw mseccfg, x{save_reg}", mode))

    test_data.int_regs.return_registers([dest_reg, mseccfg_reg, rs1_reg, save_reg])
    return lines


@add_priv_test_generator(
    "Zkr",
    required_extensions=["Zkr", "Sm"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_zkrsm(test_data: TestData) -> list[TestChunk]:
    """Generate the Zkr seed tests in M-mode."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk("Sm")

    tc.code.extend(gen_seed_csrrw_tests(test_data, "Zkr_Sm_cg", "M"))
    tc.code.extend(gen_seed_illegal_csr_op_tests(test_data, "Zkr_Sm_cg", "M"))
    tc.code.extend(gen_seed_entropy_zero_non_es16_tests(test_data, "Zkr_Sm_cg", "M"))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks


@add_priv_test_generator(
    "Zkr",
    required_extensions=["Zkr", "S"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_zkrs(test_data: TestData) -> list[TestChunk]:
    """Generate the Zkr seed tests in S-mode."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk("S")

    tc.code.extend(gen_seed_csrrw_tests(test_data, "Zkr_S_cg", "S"))
    tc.code.extend(gen_seed_illegal_csr_op_tests(test_data, "Zkr_S_cg", "S"))
    tc.code.extend(gen_seed_entropy_zero_non_es16_tests(test_data, "Zkr_S_cg", "S"))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks


@add_priv_test_generator(
    "Zkr",
    required_extensions=["Zkr", "U"],
)
def make_zkru(test_data: TestData) -> list[TestChunk]:
    """Generate the Zkr seed tests in U-mode."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk("U")

    tc.code.extend(gen_seed_csrrw_tests(test_data, "Zkr_U_cg", "U"))
    tc.code.extend(gen_seed_illegal_csr_op_tests(test_data, "Zkr_U_cg", "U"))
    tc.code.extend(gen_seed_entropy_zero_non_es16_tests(test_data, "Zkr_U_cg", "U"))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks


@add_priv_test_generator(
    "Zkr",
    required_extensions=["Zkr", "H"],
    extra_defines=["#define BOOT_TO_SMODE"],
)
def make_zkrh(test_data: TestData) -> list[TestChunk]:
    """Generate the Zkr seed tests in VS-mode and VU-mode, entered from HS-mode.

    Boot delegates illegal-instruction and virtual-instruction exceptions to HS-mode and leaves hedeleg = 0,
    so the HS-mode trap handler records every trap from VS and VU.
    """
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk("H")

    for mode in ("VS", "VU"):
        tc.code.append(f"RVTEST_TSBI_GOTO_{mode}MODE")
        tc.code.extend(gen_seed_virtual_access_tests(test_data, "Zkr_H_cg", mode))
        tc.code.append("RVTEST_TSBI_GOTO_SMODE")

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
