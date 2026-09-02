##################################
# priv/extensions/PrivCommon.py
#
# Shared test generation for the Sm, S, and U privileged suites.
# David_Harris@hmc.edu 31 August 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared test generation for the privileged mode suites (Sm, S, U)."""

from testgen.asm.csr import gen_csr_read_sigupd, gen_csr_write_sigupd
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

# Standard S-mode CSRs, shared with the Sm suite (cp_scsr_from_m)
# Format: (CSR Name, Mask).  Mask specifies a set of bits to check

# Create bit masks.  WPRI fields should be 0 to ignore reads.

# sstatus bit mask
S_SSTATUS_MASK = (
    (1 << 1)  # SIE:  Supervisor Interrupt Enable
    | (1 << 5)  # SPIE: Supervisor Previous Interrupt Enable
    | (0 << 6)  # UBE not yet supported by Sail; test in Endian
    | (1 << 8)  # SPP:  Supervisor Previous Privilege
    | (3 << 9)  # VS:   Vector Status
    | (3 << 13)  # FS:   Floating-Point Status
    | (3 << 15)  # XS:   Custom Extension Status
    | (1 << 18)  # SUM:  Supervisor User Memory Access
    | (1 << 19)  # MXR:  Make eXecutable Readable
    | (1 << 23)  # SPELP: Supervisor Previous Expect Landing Pad
    | (0 << 24)  # SDT: not yet supported by Sail; TODO change to 1 when Ssdbltrp implemented
    | (1 << 31)  # SD for RV32 (probably shouldn't be tested for RV64, but seems to work ok)
    | (0 << 32)  # UXL:  User-Mode XLEN not changeable in Sail yet; should be tested in Xlen suite
    | (1 << 63)  # SD for RV64
)

S_CSRS = [
    ("sstatus", S_SSTATUS_MASK),
    # cp_scause is tested separately. WLRL fields can't be managed with masks.
    # stvec.MODE[1] must be 0. Legal values for BASE are hard to describe with a reference model
    ("stvec", 0b10),
    ("scounteren", None),
    ("sscratch", None),
    ("sepc", None),
    ("stval", None),
    ("sip", 0xFFFF),  # only test standard non-reserved portion
    ("sie", 0xFFFF),  # only test standard non-reserved portion
]
S_CSR_SENVCFG = ("senvcfg", None)


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
            gen_csr_write_sigupd(check_reg, csr_name, test_data),
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
        f"LA(x{walk_reg}, scratch)",
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
    for csr_range in csr_ranges:
        for csr in csr_range:
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
    for csr_range in csr_ranges:
        for csr in csr_range:
            tc = test_data.new_test_chunk(test_chunks, chunk_name)
            temp_reg, read_reg = test_data.int_regs.get_registers(2)
            tc.code.extend(
                [
                    test_data.add_testcase(f"{csr:03x}", coverpoint, covergroup),
                    f"LI(x{temp_reg}, -1)          # x{temp_reg} = all 1s",
                    f"LI(x{read_reg}, 42)           # known value; the trapping csrrw must leave it unchanged",
                    f"csrrw x{read_reg}, 0x{csr:03x}, x{temp_reg}    # attempt to write read-only CSR {csr:03x}; should get illegal instruction",
                    write_sigupd(read_reg, test_data),
                    "",
                ]
            )
            test_data.int_regs.return_registers([temp_reg, read_reg])


def priv_inst_trap_tests(
    test_data: TestData,
    covergroup: str,
    coverpoint: str,
    description: str,
    instrs: list[str],
) -> list[str]:
    """Test privileged instructions"""
    lines = [
        comment_banner(coverpoint, description),
        test_data.add_testcase("ecall", coverpoint, covergroup),
        "RVTEST_TSBI_ECALL_TEST  # test ecall to execution environment that just returns",
        "# ecall returns xepc in a0 (x10).  Store a0 in signature as proof ecall took place.",
        write_sigupd(10, test_data),
    ]
    for name in instrs:
        instr = f"{name}    # test {name} instruction"
        lines.extend([test_data.add_testcase(name, coverpoint, covergroup), instr])
    return lines
