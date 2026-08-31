##################################
# priv/extensions/PrivCommon.py
#
# Shared test generation for the Sm, S, and U privileged suites.
# David_Harris@hmc.edu 31 August 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared test generation for the privileged mode suites (Sm, S, U)."""

from testgen.asm.csr import gen_csr_read_sigupd
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk

# Canonical virtual addresses have bits XLEN-1:VALEN-1 all equal, so the msb that can be walked
# independently is VALEN-2 (31 for Sv32, where VALEN = XLEN). Each tier is (msb, gate define) and
# extends the walk to the wider translation scheme when it is supported.
VADDR_GATE = "#if defined(SV39_SUPPORTED) || defined(SV32_SUPPORTED)"
VADDR_TIERS = [
    (31, None),
    (37, "SV39_SUPPORTED"),
    (46, "SV48_SUPPORTED"),
    (55, "SV57_SUPPORTED"),
]


def _vaddr_walk_step(
    test_data: TestData,
    csr_name: str,
    covergroup: str,
    bit: int,
    walking_ones: bool,
    ones_reg: int,
    walk_reg: int,
    check_reg: int,
    gated_bits: dict[int, str],
) -> list[str]:
    """One walk iteration: write a canonical address with `bit` set (or clear) and check the readback."""
    csr = (csr_name, None)
    if walking_ones:
        lines = [
            "",
            f"# Testcase: {csr_name} = bit {bit} set, 0s elsewhere",
            f"LI(x{walk_reg}, {1 << bit:#x})",
            test_data.add_testcase(f"walking1_{bit}", f"cp_{csr_name}_vaddr_walk1", covergroup),
            f"csrw {csr_name}, x{walk_reg}",
            gen_csr_read_sigupd(check_reg, csr, test_data),
        ]
    else:
        lines = [
            "",
            f"# Testcase: {csr_name} = bit {bit} clear, 1s elsewhere",
            f"LI(x{walk_reg}, {1 << bit:#x})",
            f"xor x{check_reg}, x{ones_reg}, x{walk_reg}    # clear bit {bit}",
            test_data.add_testcase(f"walking0_{bit}", f"cp_{csr_name}_vaddr_walk0", covergroup),
            f"csrw {csr_name}, x{check_reg}",
            gen_csr_read_sigupd(check_reg, csr, test_data),
        ]
    if bit in gated_bits:
        lines = [f"#ifdef {gated_bits[bit]}", *lines, f"#endif // {gated_bits[bit]}"]
    return lines


def vaddr_walk_test(
    test_data: TestData,
    csr_name: str,
    covergroup: str,
    *,
    held_low: int = 0,
    gated_bits: dict[int, str] | None = None,
) -> list[str]:
    """Write every canonical virtual address with one bit walked to csr_name and check it reads back exactly.

    held_low is a mask of low bits the CSR holds at 0 (they are not walked); gated_bits maps a bit
    to the define that makes it walkable (e.g. mepc bit 1 with ZCA_SUPPORTED). The whole test is
    under VADDR_GATE because a config with no address translation has no canonical-address rule,
    and each tier of upper bits is under its translation scheme's define.
    """
    gated_bits = gated_bits or {}
    save_reg, ones_reg, walk_reg, check_reg = test_data.int_regs.get_registers(4)
    ones = -1 & ~held_low
    for bit in gated_bits:
        ones &= ~(1 << bit)

    lines = [
        "",
        f"# Valid virtual address walk tests for {csr_name}",
        VADDR_GATE,
        f"csrr x{save_reg}, {csr_name}      # Save CSR",
        f"LI(x{ones_reg}, {ones})    # all 1s with bits {(~ones) & 0xFF:#b} held low",
    ]
    for bit, bit_gate in gated_bits.items():
        lines += [
            f"#ifdef {bit_gate}",
            f"ori x{ones_reg}, x{ones_reg}, {1 << bit}    # bit {bit} is walkable with {bit_gate}",
            f"#endif // {bit_gate}",
        ]

    for walking_ones in (True, False):
        ones_or_zeros = "1s" if walking_ones else "0s"
        zeros_or_ones = "0s" if walking_ones else "1s"
        lines.append(f"\n# Walking {ones_or_zeros} through {csr_name} with {zeros_or_ones} in the msbs")
        bit = held_low.bit_length()
        endifs = []
        for msb, tier_gate in VADDR_TIERS:
            if tier_gate is not None:
                lines.append(f"#ifdef {tier_gate}")
                endifs.append(f"#endif // {tier_gate}")
            while bit <= msb:
                lines += _vaddr_walk_step(
                    test_data, csr_name, covergroup, bit, walking_ones, ones_reg, walk_reg, check_reg, gated_bits
                )
                bit += 1
        lines += reversed(endifs)

    lines += [
        f"csrw {csr_name}, x{save_reg}            # restore CSR",
        f"#endif // {VADDR_GATE.split(' ', 1)[1]}",
    ]
    test_data.int_regs.return_registers([save_reg, ones_reg, walk_reg, check_reg])
    return lines


def vaddr_value_tests(test_data: TestData, csr_name: str, covergroup: str) -> list[str]:
    """Write real addresses (the current pc and scratch) to csr_name and check they read back exactly.

    These are valid addresses even when address translation is off, so unlike the
    canonical-address walk they are not gated on Sv* support.
    """
    csr = (csr_name, None)
    save_reg, walk_reg, check_reg = test_data.int_regs.get_registers(3)
    lines = [
        "",
        f"# {csr_name} must hold real addresses even when address translation is off",
        f"csrr x{save_reg}, {csr_name}      # Save CSR",
        "",
        f"# Testcase: {csr_name} = current pc",
        f"auipc x{walk_reg}, 0",
        test_data.add_testcase("pc", f"cp_{csr_name}_vaddr_pc", covergroup),
        f"csrw {csr_name}, x{walk_reg}    # directly follows the auipc so the value is this csrw's pc - 4",
        gen_csr_read_sigupd(check_reg, csr, test_data),
        "",
        f"# Testcase: {csr_name} = address within scratch",
        f"la x{walk_reg}, scratch",
        f"addi x{walk_reg}, x{walk_reg}, 0xA8    # low byte 0xA8 lets coverage recognize this value",
        test_data.add_testcase("scratch", f"cp_{csr_name}_vaddr_scratch", covergroup),
        f"csrw {csr_name}, x{walk_reg}",
        gen_csr_read_sigupd(check_reg, csr, test_data),
        f"csrw {csr_name}, x{save_reg}            # restore CSR",
    ]
    test_data.int_regs.return_registers([save_reg, walk_reg, check_reg])
    return lines


def addr_csr_tests(
    test_data: TestData,
    test_chunks: list[TestChunk],
    vaddr_csrs: dict[str, tuple[int, dict[int, str]]],
    covergroup: str,
    chunk_name: str,
) -> None:
    """Real-address and canonical-address walk tests for each address CSR, one chunk per CSR."""
    names = ",".join(vaddr_csrs)
    tc = test_data.new_test_chunk(test_chunks, chunk_name)
    tc.section_header = comment_banner(
        f"cp_{{{names}}}_vaddr_walk{{1,0}}, cp_{{{names}}}_vaddr_{{pc,scratch}}",
        "Write every valid virtual address as a walking 1 (0s in the msbs) and a walking 0 (1s in the msbs)\n"
        "registers that hold addresses. Canonical addresses have bits XLEN-1:VALEN-1 equal, so bits\n"
        "low..VALEN-2 are walked; requires Sv32 or Sv39 and extends the walk to Sv48/Sv57 when supported.\n"
        "Also write two real addresses — the current pc and the scratch area — which are valid even when\n"
        "address translation is off, so those tests are not gated on Sv* support",
    )
    for csr_name, (held_low, gated_bits) in vaddr_csrs.items():
        tc = test_data.new_test_chunk(test_chunks)
        tc.code.extend(vaddr_value_tests(test_data, csr_name, covergroup))
        tc.code.extend(vaddr_walk_test(test_data, csr_name, covergroup, held_low=held_low, gated_bits=gated_bits))


def csr_insufficient_priv_tests(
    test_data: TestData,
    test_chunks: list[TestChunk],
    covergroup: str,
    csr_ranges: list[range],
    chunk_name: str,
    description: str,
) -> None:
    """Attempt to read each higher-privilege CSR; every read must raise illegal instruction."""
    coverpoint = "cp_csr_insufficient_priv"
    tc = test_data.new_test_chunk(test_chunks, chunk_name)
    tc.section_header = comment_banner(coverpoint, description)
    for csr in (csr for csr_range in csr_ranges for csr in csr_range):
        tc = test_data.new_test_chunk(test_chunks, chunk_name)
        temp_reg = test_data.int_regs.get_register()
        tc.code.extend(
            [
                test_data.add_testcase(f"{csr:03x}", coverpoint, covergroup),
                f"csrr x{temp_reg}, 0x{csr:03x}    # attempt to read CSR {csr:03x}; should get illegal instruction",
                "",
            ]
        )
        test_data.int_regs.return_register(temp_reg)


def csr_ro_write_tests(
    test_data: TestData,
    test_chunks: list[TestChunk],
    covergroup: str,
    csr_ranges: list[range],
    chunk_name: str,
) -> None:
    """Attempt to write each read-only CSR; every write must raise illegal instruction."""
    coverpoint = "cp_csr_ro"
    tc = test_data.new_test_chunk(test_chunks, chunk_name)
    tc.section_header = comment_banner(coverpoint, "Attempt to write read-only CSRs.  Should throw illegal instruction")
    for csr in (csr for csr_range in csr_ranges for csr in csr_range):
        tc = test_data.new_test_chunk(test_chunks, chunk_name)
        temp_reg = test_data.int_regs.get_register()
        tc.code.extend(
            [
                test_data.add_testcase(f"{csr:03x}", coverpoint, covergroup),
                f"LI(x{temp_reg}, -1)          # x{temp_reg} = all 1s",
                f"csrw 0x{csr:03x}, x{temp_reg}    # attempt to write read-only CSR {csr:03x}; should get illegal instruction",
                "",
            ]
        )
        test_data.int_regs.return_register(temp_reg)


def priv_inst_trap_tests(
    test_data: TestData,
    covergroup: str,
    coverpoint: str,
    description: str,
    instrs: list[tuple[str, str]],
) -> list[str]:
    """An ecall answered by the T-SBI environment, then privileged instructions that must trap."""
    lines = [
        comment_banner(coverpoint, description),
        test_data.add_testcase("ecall", coverpoint, covergroup),
        "RVTEST_TSBI_ECALL_TEST  # test ecall to execution environment that just returns",
        "# ecall returns xepc in a0 (x10).  Store a0 in signature as proof ecall took place.",
        write_sigupd(10, test_data),
    ]
    for name, instr in instrs:
        lines.extend([test_data.add_testcase(name, coverpoint, covergroup), instr])
    return lines
