##################################
# priv/extensions/PrivCommon.py
#
# Shared test generation for the Sm, S, U and H privileged suites.
# David_Harris@hmc.edu 31 August 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared test generation for the privileged mode suites (Sm, S, U, H)."""

from collections.abc import Callable

from testgen.asm.csr import gen_csr_read_sigupd, gen_csr_read_sigupd_in_mode, gen_csr_write_sigupd
from testgen.asm.helpers import comment_banner, gated, write_sigupd
from testgen.asm.tsbi import tsbi_call, tsbi_call_or_direct
from testgen.constants import INDENT
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk

# Status CSR whose FS and VS fields the tests in each privilege mode check; it also names their
# coverpoints and testcase labels. U-mode code reaches the fields through T-SBI (see _status_access).
# VS-mode code reaches vsstatus as sstatus and the HS-level sstatus through T-SBI. VU-mode code reaches both
# through T-SBI.
STATUS_CSR = {"M": "mstatus", "S": "sstatus", "U": "mstatus", "VS": "vsstatus", "VU": "vsstatus"}
VIRTUAL_MODES = ("VS", "VU")


def hs_status_values(priv: str, include_off: bool = True) -> tuple[int | None, ...]:
    """Values of the HS-level sstatus field to cross with the status field checked in priv (VS- and VU-mode only)."""
    if priv not in VIRTUAL_MODES:
        return (None,)
    return (0, 1, 2, 3) if include_off else (1, 2, 3)


def off_status_pairs(priv: str) -> list[tuple[int, int | None]]:
    """(xstatus field, HS-level sstatus field) pairs where an instruction needing the field traps.

    In VS- and VU-mode that is any pair with either field Off.
    """
    if priv not in VIRTUAL_MODES:
        return [(0, None)]
    return [(vs, hs) for vs in range(4) for hs in range(4) if vs == 0 or hs == 0]


def off_tag(vs: int, hs: int | None) -> str:
    """Testcase label suffix for an Off pair from off_status_pairs."""
    return "" if hs is None else f"_vs{vs}_hs{hs}"


def hs_tag(hs: int | None) -> str:
    """Testcase label suffix for an HS-level sstatus field value."""
    return "" if hs is None else f"_hs{hs}"


def hs_note(hs: int | None, field: str = "FS") -> str:
    """Testcase comment suffix for an HS-level sstatus field value."""
    return "" if hs is None else f" and sstatus.{field}={hs}"


def _status_access(priv: str, instr: Callable[[str], str], hs: bool = False) -> list[str]:
    """Run instr(csr), an access to the status CSR, from code running in priv ("M", "S", "U", "VS" or "VU").

    M- and S-mode access STATUS_CSR[priv] directly. U-mode goes through T-SBI, to sstatus when
    S-mode is supported and to mstatus otherwise. VS-mode accesses vsstatus as sstatus, or with
    hs=True the HS-level sstatus through T-SBI. VU-mode accesses vsstatus, or with hs=True sstatus,
    both through T-SBI.
    """
    if priv == "VU":
        return [tsbi_call(instr("sstatus" if hs else "vsstatus"))]
    if priv == "VS":
        return [tsbi_call(instr("sstatus")) if hs else instr("sstatus")]
    if priv != "U":  # M- or S-mode
        return [tsbi_call_or_direct(instr(STATUS_CSR[priv]), priv)]
    return ["#ifdef S_SUPPORTED", tsbi_call(instr("sstatus")), "#else", tsbi_call(instr("mstatus")), "#endif"]


def gen_status_read_sigupd(check_reg: int, test_data: TestData, priv: str, mask_reg: int | None = None) -> str:
    """Read the status CSR from code running in priv into the signature, keeping only the bits in mask_reg if given.

    VS- and VU-mode code also read the HS-level sstatus into the signature.
    """
    if mask_reg is None and priv not in ("U", *VIRTUAL_MODES):
        return gen_csr_read_sigupd_in_mode(check_reg, (STATUS_CSR[priv], None), test_data, priv)
    reads = []
    for hs in (False, True) if priv in VIRTUAL_MODES else (False,):
        lines = _status_access(priv, lambda csr: f"csrr x{check_reg}, {csr}", hs)
        if mask_reg is not None:
            lines.append(f"and x{check_reg}, x{check_reg}, x{mask_reg}    # keep only the masked bits")
        lines.append(write_sigupd(check_reg, test_data))
        reads.extend(lines)
    return "\n".join(reads)


def _set_fields(temp_reg: int, priv: str, fs: int | None, vs: int | None, hs: bool) -> list[str]:
    """Set the xstatus.FS and/or xstatus.VS that are not None, in the HS-level sstatus if hs=True."""
    fields = [(name, val) for name, val in (("FS", fs), ("VS", vs)) if val is not None]
    if not fields:
        return []
    names = " and ".join(name for name, _ in fields)
    mask = " | ".join(f"MSTATUS_{name}" for name, _ in fields)
    value = " | ".join(f"{val} * (MSTATUS_{name} & -MSTATUS_{name})" for name, val in fields if val) or "0"
    settings = ", ".join(f"{name}={val}" for name, val in fields)
    where = "HS-level " if hs else ""
    return [
        f"LI(x{temp_reg}, {mask})",
        *_status_access(priv, lambda csr: f"csrc {csr}, x{temp_reg}  # clear {where}{names}", hs),
        f"LI(x{temp_reg}, {value})",
        *_status_access(priv, lambda csr: f"csrs {csr}, x{temp_reg}  # {where}{settings}", hs),
    ]


def set_status_fields(
    temp_reg: int,
    priv: str,
    fs: int | None = None,
    vs: int | None = None,
    hs_fs: int | None = None,
    hs_vs: int | None = None,
) -> list[str]:
    """Set xstatus.FS and/or xstatus.VS from code running in priv ("M", "S", "U", "VS" or "VU").

    VS- and VU-mode code set the HS-level sstatus fields too: hs_fs and hs_vs, or Dirty for a field
    that fs or vs sets and hs_fs or hs_vs leaves unset.
    """
    if priv in VIRTUAL_MODES:
        hs_fs = 3 if fs is not None and hs_fs is None else hs_fs
        hs_vs = 3 if vs is not None and hs_vs is None else hs_vs
    return [
        *_set_fields(temp_reg, priv, fs, vs, hs=False),
        *_set_fields(temp_reg, priv, hs_fs, hs_vs, hs=True),
    ]


# Some Sv translation mode is supported. Sv48 and Sv57 imply Sv39, so Sv39 and Sv32 between them
# cover every case and the wider modes need not be named.
SV_GATE = "#if defined(SV39_SUPPORTED) || defined(SV32_SUPPORTED)"

# Canonical virtual addresses have bits XLEN-1:VALEN-1 all equal, so the msb that can be walked
# independently is VALEN-2 (31 for Sv32, where VALEN = XLEN). Each tier is (msb, gate define) and
# extends the walk to the wider translation scheme when it is supported.
VADDR_GATE = SV_GATE
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
    | (1 << 24)  # SDT: Supervisor Disable Trap
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


def addr_value_tests(test_data: TestData, csr_name: str, covergroup: str) -> list[str]:
    """Write physical addresses (the current pc and scratch) to csr_name and check they read back exactly.

    These are valid addresses even when address translation is off, so unlike the
    canonical-address walk they are not gated on Sv* support.
    """
    csr = (csr_name, None)
    save_reg, walk_reg, check_reg = test_data.int_regs.get_registers(3)
    lines = [
        "",
        f"# {csr_name} must hold physical addresses even when address translation is off",
        f"csrr x{save_reg}, {csr_name}      # Save CSR",
        "",
        f"# Testcase: {csr_name} = current pc",
        ".p2align 2    # a 4-byte-aligned pc keeps xtvec.MODE = Direct",
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
    """Physical-address and canonical-address walk tests for each address CSR, one chunk per CSR."""
    names = ",".join(vaddr_csrs)
    tc = test_data.new_test_chunk(test_chunks, chunk_name)
    tc.section_header = comment_banner(
        f"cp_{{{names}}}_vaddr_walk{{1,0}}, cp_{{{names}}}_vaddr_{{pc,scratch}}",
        "Write every valid virtual address as a walking 1 (0s in the msbs) and a walking 0 (1s in the msbs)\n"
        "to registers that hold addresses. Canonical addresses have bits XLEN-1:VALEN-1 equal, so bits\n"
        "low..VALEN-2 are walked; requires Sv32 or Sv39 and extends the walk to Sv48/Sv57 when supported.\n"
        "Also write two physical addresses — the current pc and the scratch area — which are valid even when\n"
        "address translation is off, so those tests are not gated on Sv* support",
    )
    for csr_name, (held_low, gated_bits) in vaddr_csrs.items():
        tc = test_data.new_test_chunk(test_chunks)
        tc.code.extend(addr_value_tests(test_data, csr_name, covergroup))
        tc.code.extend(vaddr_walk_test(test_data, csr_name, covergroup, held_low=held_low, gated_bits=gated_bits))


def xtval_value_tests(test_data: TestData, csr_name: str, covergroup: str) -> list[str]:
    """Write 0 and, when illegal-instruction encodings are reported in it, every ILEN-bit value to xtval.

    mtval and stval are both WARL and must hold 0; when the implementation reports the faulting
    instruction bits (UDB_REPORT_ENCODING_IN_<XTVAL>_ON_ILLEGAL_INSTRUCTION), they must also hold
    every ILEN-bit value. csr_name is "mtval" or "stval".
    """
    csr = (csr_name, None)
    ilen_guard = f"UDB_REPORT_ENCODING_IN_{csr_name.upper()}_ON_ILLEGAL_INSTRUCTION"
    save_reg, walk_reg, check_reg = test_data.int_regs.get_registers(3)
    lines = [
        "",
        f"# {csr_name} must hold 0",
        f"csrr x{save_reg}, {csr_name}      # Save CSR",
        "",
        f"# Testcase: {csr_name} = 0",
        f"LI(x{walk_reg}, 0)",
        test_data.add_testcase("zero", f"cp_{csr_name}_zero", covergroup),
        f"csrw {csr_name}, x{walk_reg}",
        gen_csr_read_sigupd(check_reg, csr, test_data),
        "",
        f"# {csr_name} must hold every ILEN-bit value when the illegal instruction encoding is reported in it",
        f"#ifdef {ilen_guard}",
    ]
    for i in range(32):
        lines.extend(
            [
                "",
                f"# Testcase: {csr_name} = bit {i} set, 0s elsewhere",
                f"LI(x{walk_reg}, {1 << i:#x})",
                test_data.add_testcase(f"walking1_{i}", f"cp_{csr_name}_ilen_walk1", covergroup),
                f"csrw {csr_name}, x{walk_reg}",
                gen_csr_read_sigupd(check_reg, csr, test_data),
            ]
        )
    lines.extend(
        [
            "",
            f"# Testcase: {csr_name} = all 32 encoding bits set",
            f"LI(x{walk_reg}, 0xFFFFFFFF)",
            test_data.add_testcase("ones", f"cp_{csr_name}_ilen_ones", covergroup),
            f"csrw {csr_name}, x{walk_reg}",
            gen_csr_read_sigupd(check_reg, csr, test_data),
            f"#endif // {ilen_guard}",
            f"csrw {csr_name}, x{save_reg}            # restore CSR",
        ]
    )
    test_data.int_regs.return_registers([save_reg, walk_reg, check_reg])
    return lines


H_GATE = "defined(H_SUPPORTED)"
S1P12_GATE = "defined(S1P12P0_OR_LATER_SUPPORTED)"

# Codes written to each cause CSR, as {kind: {code: #if condition, or None if always written}}.
# mcause need only hold the codes of supported causes (mcause_exccode_wlrl); exception codes 14 and 17 are reserved.
MCAUSE_CODES: dict[str, dict[int, str | None]] = {
    "exception": {
        **dict.fromkeys((0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 15)),
        10: H_GATE,  # ecall from VS-mode
        16: "defined(SSDBLTRP_SUPPORTED)",  # double trap
        18: "defined(ZICFILP_SUPPORTED) || defined(ZICFISS_SUPPORTED)",  # software check
        19: "defined(SM1P13P0_OR_LATER_SUPPORTED)",  # hardware error
        **dict.fromkeys((20, 21, 22, 23), H_GATE),  # guest-page faults and virtual instruction
    },
    "interrupt": {
        **dict.fromkeys((1, 3, 5, 7, 9, 11)),
        **dict.fromkeys((2, 6, 10, 12), H_GATE),  # VS-level and supervisor guest external interrupts
        13: "defined(SSCOFPMF_SUPPORTED)",  # local counter overflow
    },
}
# scause, and vscause, which must hold the same values (vscause_wlrl), must hold every code 0-31 from Ss1p12
# (scause_exception_code_sz).  Before that, they need only hold the codes of the causes that every S-mode hart
# supports, and those of the causes an extension adds: software check (Zicfilp, Zicfiss), local counter overflow
# (Sscofpmf) and the H causes.
_SCAUSE_ALWAYS = {"exception": (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 13, 15), "interrupt": (1, 3, 5, 7, 9, 11)}
_SCAUSE_EXTENSION = {"exception": (10, 18, 20, 21, 22, 23), "interrupt": (2, 6, 10, 12, 13)}


def _scause_gate(kind: str, code: int) -> str | None:
    if code in _SCAUSE_ALWAYS[kind]:
        return None
    if code in _SCAUSE_EXTENSION[kind]:
        return f"{S1P12_GATE} || {MCAUSE_CODES[kind][code]}"
    return S1P12_GATE


SCAUSE_CODES: dict[str, dict[int, str | None]] = {
    kind: {code: _scause_gate(kind, code) for code in range(32)} for kind in ("exception", "interrupt")
}


def xcause_write_tests(test_data: TestData, csr: str, covergroup: str) -> list[str]:
    """Write each exception and interrupt code that csr (mcause, scause or vscause) must hold.

    The codes are WLRL, so only legal codes are written (MCAUSE_CODES, SCAUSE_CODES).
    """
    codes = MCAUSE_CODES if csr == "mcause" else SCAUSE_CODES
    save_reg, check_reg, temp_reg = test_data.int_regs.get_registers(3)
    lines = [f"csrr x{save_reg}, {csr}     # save CSR before testing it"]
    for kind, interrupt in (("exception", 0), ("interrupt", 1)):
        coverpoint = f"cp_{csr}_write_{kind}"
        lines.append(comment_banner(coverpoint, f"with interrupt = {interrupt}: test writing each {kind} cause"))
        if interrupt:
            lines.append(f"SET_MSB(x{temp_reg})  # set x{temp_reg} to have msb = 1 for interrupt tests")
        for code, gate in sorted(codes[kind].items()):
            body = ["", f"# Testcase: set {csr} to {kind} cause {code}", f"LI(x{check_reg}, {code})"]
            if interrupt:
                body.append(f"or x{check_reg}, x{check_reg}, x{temp_reg}          # set interrupt bit")
            body.extend(
                [
                    test_data.add_testcase(f"b_{code}", coverpoint, covergroup),
                    gen_csr_write_sigupd(check_reg, csr, test_data),
                ]
            )
            lines.extend(gated(body, gate))
    lines.append(f"\ncsrw {csr}, x{save_reg}       # restore CSR")
    test_data.int_regs.return_registers([save_reg, check_reg, temp_reg])
    return lines


def xstatus_sd_tests(test_data: TestData, csr: str, covergroup: str, coverpoint: str) -> list[str]:
    """Write csr (mstatus, or sstatus in S-mode or VS-mode) with each SD, FS, XS and VS.

    SD is read-only, so writing it has no effect; it summarizes FS, XS and VS.
    """
    save_reg, check_reg, reg1, reg2, reg3 = test_data.int_regs.get_registers(5)
    lines = [
        comment_banner(
            coverpoint,
            f"Write all combinations of {csr}.SD = {{0/1}}, FS/XS/VS = {{00, 01, 10, 11}}\n"
            f"{csr}.SD is read-only, so nothing should happen",
        ),
        "",
        "# Setup",
        f"SET_MSB(x{reg1}) # put a 1 in the msb of x{reg1} (XLEN-1)",
        f"csrr x{save_reg}, {csr}        # read and save {csr}",
        f"{INDENT}# set up x{reg3} with {csr} except SD, FS, XS, VS cleared",
        f"not x{reg2}, x{reg1}              # x{reg2} has all but msb set",
        f"and x{reg3}, x{save_reg}, x{reg2} # clear SD bit",
        f"LI(x{reg2}, 0x1E600)              # x{reg2} has all FS, XS, VS bits set (bits [14:13], [16:15], [10:9], respectively)",
        f"not x{reg2}, x{reg2}              # x{reg2} has all but FS, XS, VS bits set",
        f"and x{reg3}, x{reg3}, x{reg2}     # clear FS, XS, VS bits",
    ]
    for sd in (0, 1):
        for fs in range(4):
            for xs in range(4):
                for vs in range(4):
                    fields = fs << 13 | xs << 15 | vs << 9
                    lines.extend(
                        [
                            "",
                            f"# Testcase: set {csr} to sd = {sd}, fs = {fs:02b}, xs = {xs:02b}, vs = {vs:02b}",
                            f"LI(x{check_reg}, 0x{fields:08x})  # fs = {fs:02b} xs = {xs:02b} vs = {vs:02b}",
                        ]
                    )
                    if sd == 1:
                        lines.append(f"or x{check_reg}, x{check_reg}, x{reg1}      # set SD bit")
                    lines.extend(
                        [
                            f"or x{check_reg}, x{check_reg}, x{reg3}   # value to write to {csr} with SD/FS/XS/VS bits set/clear",
                            test_data.add_testcase(
                                f"sd_{sd}_fs_{fs:02b}_xs_{xs:02b}_vs_{vs:02b}", coverpoint, covergroup
                            ),
                            gen_csr_write_sigupd(check_reg, csr, test_data),
                        ]
                    )
    lines.append(f"\ncsrw {csr}, x{save_reg}    # restore CSR")
    test_data.int_regs.return_registers([save_reg, check_reg, reg1, reg2, reg3])
    return lines


def _csr_chunks(csr_ranges: list[range], csrs_per_chunk: int) -> list[list[int]]:
    """Split the CSR numbers in csr_ranges into lists of csrs_per_chunk."""
    csrs = [csr for csr_range in csr_ranges for csr in csr_range]
    return [csrs[i : i + csrs_per_chunk] for i in range(0, len(csrs), csrs_per_chunk)]


def _in_mode(lines: list[str], mode: str | None) -> list[str]:
    """Run lines in mode ("VS" or "VU"), entered from HS-mode, or in the current mode if mode is None."""
    if mode is None:
        return lines
    return [f"RVTEST_TSBI_GOTO_{mode}MODE", *lines, "RVTEST_TSBI_GOTO_SMODE"]


def csr_insufficient_priv_tests(
    test_data: TestData,
    test_chunks: list[TestChunk],
    covergroup: str,
    csr_ranges: list[range],
    chunk_name: str,
    description: str,
    mode: str | None = None,
    csrs_per_chunk: int = 1,
) -> None:
    """Attempt to read each higher-privilege CSR; every read must raise illegal instruction.

    Each chunk of csrs_per_chunk CSRs enters mode ("VS" or "VU") from HS-mode first, if mode is given.
    """
    coverpoint = "cp_csr_insufficient_priv"
    tc = test_data.new_test_chunk(test_chunks, chunk_name)
    tc.section_header = comment_banner(coverpoint, description)
    for csrs in _csr_chunks(csr_ranges, csrs_per_chunk):
        tc = test_data.new_test_chunk(test_chunks, chunk_name)
        temp_reg = test_data.int_regs.get_register()
        for csr in csrs:
            tc.code.extend(
                [
                    test_data.add_testcase(f"{csr:03x}", coverpoint, covergroup),
                    f"LI(x{temp_reg}, 42)           # known value; the trapping csrr must leave it unchanged",
                    f"csrr x{temp_reg}, 0x{csr:03x}    # attempt to read CSR {csr:03x}; should get illegal instruction",
                    write_sigupd(temp_reg, test_data),
                    "",
                ]
            )
        tc.code[:] = _in_mode(tc.code, mode)
        test_data.int_regs.return_register(temp_reg)


def csr_ro_write_tests(
    test_data: TestData,
    test_chunks: list[TestChunk],
    covergroup: str,
    csr_ranges: list[range],
    chunk_name: str,
    mode: str | None = None,
    csrs_per_chunk: int = 1,
) -> None:
    """Attempt to write each read-only CSR; every write must raise illegal instruction.

    Each chunk of csrs_per_chunk CSRs enters mode ("VS" or "VU") from HS-mode first, if mode is given.
    """
    coverpoint = "cp_csr_ro"
    tc = test_data.new_test_chunk(test_chunks, chunk_name)
    tc.section_header = comment_banner(coverpoint, "Attempt to write read-only CSRs.  Should throw illegal instruction")
    for csrs in _csr_chunks(csr_ranges, csrs_per_chunk):
        tc = test_data.new_test_chunk(test_chunks, chunk_name)
        temp_reg, read_reg = test_data.int_regs.get_registers(2)
        for csr in csrs:
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
        tc.code[:] = _in_mode(tc.code, mode)
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
        "RVTEST_TSBI_ECALL_TEST  # ecall to the execution environment, recorded in the trap signature",
    ]
    for name in instrs:
        instr = f"{name}    # test {name} instruction"
        lines.extend([test_data.add_testcase(name, coverpoint, covergroup), instr])
    return lines


# htimedelta values.  time is far below 2^30 when the tests run.  The negative ones make time + htimedelta
# wrap modulo 2^64 once time exceeds their magnitude; neg_1 wraps for any time >= 1.  pos_2p32m1 and neg_1
# make the low-word add carry into the upper word on RV32.
HTIMEDELTAS = {
    "zero": 0,
    "pos_2p30": 1 << 30,
    "pos_2p32m1": (1 << 32) - 1,
    "pos_2p60": 1 << 60,
    "neg_1": -1,
    "neg_2p30": -(1 << 30),
    "neg_2p60": -(1 << 60),
}


def read_time(lo: int, hi: int, tmp: int) -> list[str]:
    """Read time into lo, and on RV32 timeh into hi, reading again if timeh changes between the reads."""
    return [
        "#if __riscv_xlen == 64",
        f"csrr x{lo}, time",
        "#else",
        "1:",
        f"csrr x{hi}, timeh",
        f"csrr x{lo}, time",
        f"csrr x{tmp}, timeh",
        f"bne x{hi}, x{tmp}, 1b    # timeh changed between the reads",
        "#endif",
    ]
