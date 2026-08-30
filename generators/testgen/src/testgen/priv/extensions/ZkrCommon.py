##################################
# priv/extensions/ZkrCommon.py
#
# Shared generators for the ZkrSm / ZkrS / ZkrU seed CSR test suites.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared Zkr seed-CSR test generators, parameterized by the privilege mode the suite runs in."""

from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.asm.tsbi import tsbi_call
from testgen.data.state import TestData


def _mseccfg(mode: str, instr: str) -> str:
    """mseccfg is an M-mode CSR: access it directly in M-mode, through T-SBI from S/U-mode."""
    return instr if mode == "M" else tsbi_call(instr)


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
        *_gate(mode, [_mseccfg(mode, f"csrr x{save_reg}, mseccfg")]),
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
                            _mseccfg(mode, f"csrw mseccfg, x{mseccfg_reg}"),
                        ],
                    ),
                    # nonzero and zero rs1 to cover both insn[19:15] bins
                    test_data.add_testcase(f"{mode}_{tag}", coverpoint, covergroup),
                    f"csrrw x{dest_reg}, seed, x{src_reg}",
                    test_data.add_testcase(f"{mode}_zero_{tag}", coverpoint, covergroup),
                    f"csrrw x{dest_reg}, seed, x0",
                ]
            )

    lines.extend(_gate(mode, [_mseccfg(mode, f"csrw mseccfg, x{save_reg}")]))

    test_data.int_regs.return_registers([dest_reg, mseccfg_reg, src_reg, save_reg])
    return lines


def gen_seed_illegal_csr_op_tests(test_data: TestData, covergroup: str, mode: str) -> list[str]:
    """Read-only CSR ops on seed cause an illegal instruction in this suite's mode."""
    coverpoint = "cp_zkr_seed_illegal_csr_op"

    dest_reg, mseccfg_reg, rs1_reg, save_reg = test_data.int_regs.get_registers(4)

    sseed_useed_enabled = (1 << 9) | (1 << 8)
    lines = [
        comment_banner(coverpoint, f"CSR read ops on seed cause illegal instruction in {mode}-mode"),
        *_gate(
            mode,
            [
                _mseccfg(mode, f"csrr x{save_reg}, mseccfg"),
                f"LI(x{mseccfg_reg}, {sseed_useed_enabled})",
                _mseccfg(mode, f"csrw mseccfg, x{mseccfg_reg} # enable seed access from all modes"),
            ],
        ),
        f"LI(x{rs1_reg}, 0)",
    ]

    # (op, is_immediate) for each CSR op to test on seed
    csr_ops: list[tuple[str, bool]] = [
        ("csrrs", False),
        ("csrrc", False),
        ("csrrwi", True),
        ("csrrsi", True),
        ("csrrci", True),
        ("csrrw", False),
    ]

    for op, is_imm in csr_ops:
        for rs1_imm_val in (0, 1):
            tag = f"{op}_rs1imm{rs1_imm_val}"

            if is_imm:
                instr = f"{op} x{dest_reg}, seed, {rs1_imm_val}"
            else:
                instr = f"{op} x{dest_reg}, seed, {'x0' if rs1_imm_val == 0 else f'x{rs1_reg}'}"

            lines.extend(
                [
                    test_data.add_testcase(f"{mode}_{tag}", coverpoint, covergroup),
                    instr,
                ]
            )

    lines.extend(_gate(mode, [_mseccfg(mode, f"csrw mseccfg, x{save_reg}")]))

    test_data.int_regs.return_registers([dest_reg, mseccfg_reg, rs1_reg, save_reg])
    return lines


def gen_seed_entropy_zero_non_es16_tests(test_data: TestData, covergroup: str, mode: str) -> list[str]:
    """Read seed twice in a row using csrrw; check entropy = 0 if OPST is not ES16."""
    coverpoint = "cp_zkr_seed_entropy_zero_non_es16"

    read_reg, opst_reg, entropy_reg, cmp_reg = test_data.int_regs.get_registers(4)
    save_reg = test_data.int_regs.get_register()

    sseed_useed_enabled = (1 << 9) | (1 << 8)
    lines = [
        comment_banner(coverpoint, gen_seed_entropy_zero_non_es16_tests.__doc__),
        *_gate(
            mode,
            [
                _mseccfg(mode, f"csrr x{save_reg}, mseccfg"),
                f"LI(x{cmp_reg}, {sseed_useed_enabled})",
                _mseccfg(mode, f"csrw mseccfg, x{cmp_reg}"),
            ],
        ),
        test_data.add_testcase(f"{mode}_es16", coverpoint, covergroup),
        f"csrrw x{read_reg}, seed, zero",
        f"csrrw x{read_reg}, seed, zero",
        "# OPST bits",
        f"srli x{opst_reg}, x{read_reg}, 0x1E",
        "# entropy bits",
        f"LI(x{entropy_reg}, 0xFFFF)",
        "# Check OPST value",
        f"LI(x{cmp_reg}, 0x2)",
        f"bne x{opst_reg}, x{cmp_reg}, .Lzkr_seed_entropy_non_es16",
        "# SIGUPD 0xB0BA if OPST is ES16",
        f"LI(x{cmp_reg}, 0xB0BA)",
        write_sigupd(cmp_reg, test_data),
        "j .Lzkr_seed_entropy_done",
        ".Lzkr_seed_entropy_non_es16:",
        "# If OPST is not ES16",
        f"and x{entropy_reg}, x{entropy_reg}, x{read_reg}",
        write_sigupd(entropy_reg, test_data),
        ".Lzkr_seed_entropy_done:",
        *_gate(mode, [_mseccfg(mode, f"csrw mseccfg, x{save_reg}")]),
    ]

    test_data.int_regs.return_registers([read_reg, opst_reg, entropy_reg, cmp_reg, save_reg])
    return lines
