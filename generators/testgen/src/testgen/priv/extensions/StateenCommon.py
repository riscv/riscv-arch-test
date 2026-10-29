##################################
# StateenCommon.py
#
# Shared Smstateen and Ssstateen test-case generators.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared Smstateen and Ssstateen test-case generators.

Both suites test state-enable CSRs from a base privilege mode and differ only in the CSRs that
gate the state (mstateen0, hstateen0 or sstateen0) and in the modes the state is accessed from.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from testgen.asm.csr import csr_access_test, csr_walk_test
from testgen.asm.helpers import arch_block, comment_banner, gated, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk

# (testcase label, instruction template with {rd} and {rs})
Insn = tuple[str, str]
# (stateen CSR, value written to the feature's bit)
GateWrite = tuple[str, int]

# Condition for each stateen CSR level that may not exist, by the first letter of the CSR name
LEVEL_GUARDS = {"h": "defined(H_SUPPORTED)", "s": "defined(S_SUPPORTED)"}
MODE_GUARDS = {"S": "defined(S_SUPPORTED)", "VS": "defined(H_SUPPORTED)", "VU": "defined(H_SUPPORTED)"}
# Condition for a CSR to exist beyond the guard of its feature
CSR_GUARDS = {
    "sieh": "__riscv_xlen == 32",
    "siph": "__riscv_xlen == 32",
    "henvcfgh": "__riscv_xlen == 32",
    "hcontext": "defined(UDB_HCONTEXT_IMPLEMENTED)",
    **{f"{level}stateen{n}h": "__riscv_xlen == 32" for level in "mh" for n in range(4)},
}

# TODO: Remove the unchecked bits once Sail models Smaia/Ssaia, Smctr and Zcmt
# Bits are only unchecked when the DUT implements the extension.
STATEEN0_UNCHECKED_BITS = [
    (1 << 2, "ZCMT_SUPPORTED"),  # JVT
    (1 << 54, "SSCTR_SUPPORTED"),  # CTR
    (0b11 << 58, "SSAIA_SUPPORTED"),  # IMSIC, AIA
    (1 << 60, "SSCSRIND_SUPPORTED"),  # CSRIND
]


@dataclass(frozen=True)
class StateenFeature:
    """State gated by one bit of a stateen CSR."""

    mask: str  # encoding.h macro for the bit; bits 32 and up use mask_h in the "h" CSR on RV32
    mask_h: str | None = None
    csrs: tuple[str, ...] = ()  # CSRs accessed with csrrw, csrrs and csrrc
    h_csrs: tuple[str, ...] = ()  # hypervisor CSRs, which only mstateen0 controls
    insns: tuple[Insn, ...] = ()
    guard: str | None = None  # preprocessor condition for the state to exist
    arch: tuple[str, ...] = ()  # extensions the assembler needs
    lower_csrs: tuple[str, ...] = ("hstateen0",)  # CSRs below mstateen0 that also have the bit
    name: str = ""  # bit name for comments; defaults to the mask macro without its prefix

    def __post_init__(self) -> None:
        if not self.name:
            object.__setattr__(self, "name", self.mask.removeprefix("MSTATEEN0_").removeprefix("MSTATEEN_"))


FP_INSNS: tuple[Insn, ...] = (
    ("fadd_s", "fadd.s {rd}, {rs}, {rs}"),
    ("fcvt_w_s", "fcvt.w.s {rd}, {rs}"),
    ("fcvt_s_w", "fcvt.s.w {rd}, {rs}"),
    ("fclass_s", "fclass.s {rd}, {rs}"),
)

# Bits are the same in mstateen0, hstateen0 and sstateen0, but sstateen0 only has the fcsr and jvt bits.
FEATURES = {
    "fcsr": StateenFeature(
        "MSTATEEN0_FCSR",
        csrs=("frm", "fflags", "fcsr"),
        guard="defined(ZFINX_SUPPORTED)",
        arch=("zfinx",),
        lower_csrs=("hstateen0", "sstateen0"),
    ),
    "fp": StateenFeature(
        "MSTATEEN0_FCSR",
        insns=FP_INSNS,
        guard="defined(ZFINX_SUPPORTED)",
        arch=("zfinx",),
        lower_csrs=("hstateen0", "sstateen0"),
    ),
    "jvt": StateenFeature(
        "MSTATEEN0_JVT",
        csrs=("jvt",),
        guard="defined(ZCMT_SUPPORTED)",
        arch=("zcmt",),
        lower_csrs=("hstateen0", "sstateen0"),
    ),
    "csrind": StateenFeature(
        "MSTATEEN0_CSRIND",
        "MSTATEEN0H_CSRIND",
        csrs=("siselect", "sireg", "sireg2", "sireg3", "sireg4", "sireg5", "sireg6"),
        h_csrs=("vsiselect", "vsireg", "vsireg2", "vsireg3", "vsireg4", "vsireg5", "vsireg6"),
        guard="defined(SSCSRIND_SUPPORTED)",
    ),
    "ctr": StateenFeature(
        "MSTATEEN0_CTR", "MSTATEEN0H_CTR", csrs=("sctrdepth", "sctrstatus"), guard="defined(SSCTR_SUPPORTED)"
    ),
    "srmcfg": StateenFeature(
        "MSTATEEN0_PRIV114",
        "MSTATEEN0H_PRIV114",
        csrs=("srmcfg",),
        guard="defined(SSQOSID_SUPPORTED)",
        lower_csrs=(),
        name="SRMCFG",
    ),
    "p1p13": StateenFeature(
        "MSTATEEN0_PRIV113",
        "MSTATEEN0H_PRIV113",
        csrs=("hedelegh",),
        guard="defined(SM1P13P0_OR_LATER_SUPPORTED) && defined(H_SUPPORTED) && __riscv_xlen == 32",
        lower_csrs=(),
        name="P1P13",
    ),
    "context": StateenFeature(
        "MSTATEEN0_HCONTEXT",
        "MSTATEEN0H_HCONTEXT",
        csrs=("scontext",),
        h_csrs=("hcontext",),
        guard="defined(SDTRIG_SUPPORTED)",
        name="CONTEXT",
    ),
    "imsic": StateenFeature(
        "MSTATEEN0_IMSIC", "MSTATEEN0H_IMSIC", csrs=("stopei",), h_csrs=("vstopei",), guard="defined(SSAIA_SUPPORTED)"
    ),
    "aia": StateenFeature(
        "MSTATEEN0_AIA", "MSTATEEN0H_AIA", csrs=("stopi", "sieh", "siph"), guard="defined(SSAIA_SUPPORTED)"
    ),
    "envcfg": StateenFeature(
        "MSTATEEN0_HENVCFG",
        "MSTATEEN0H_HENVCFG",
        csrs=("senvcfg",),
        h_csrs=("henvcfg", "henvcfgh"),
        guard="defined(SM1P12P0_OR_LATER_SUPPORTED)",
        name="ENVCFG",
    ),
    "se": StateenFeature("MSTATEEN_HSTATEEN", "MSTATEENH_HSTATEEN", guard="defined(S_SUPPORTED)", name="SE"),
}


def _bit_lines(csr: str, feat: StateenFeature, make: Callable[[str, str], list[str]]) -> list[str]:
    """Lines from make(csr, mask macro) for the CSR holding the bit: csr on RV64, csr + "h" on RV32 above bit 31."""
    if feat.mask_h is None:
        return make(csr, feat.mask)
    return ["#if __riscv_xlen == 64", *make(csr, feat.mask), "#else", *make(f"{csr}h", feat.mask_h), "#endif"]


def _level_gated(csr: str, lines: list[str]) -> list[str]:
    """Gate `lines` on the existence of stateen CSR `csr`."""
    return gated(lines, LEVEL_GUARDS.get(csr[0]))


def _write_bit(csr: str, feat: StateenFeature, *, on: bool, reg: int) -> list[str]:
    op = "csrs" if on else "csrc"
    return _bit_lines(csr, feat, lambda c, m: [f"LI(x{reg}, {m})", f"{op} {c}, x{reg}  # {feat.name} = {int(on)}"])


def _mode_block(mode: str, base: str, body: list[str]) -> list[str]:
    """Run `body` in `mode` and return to `base`. S-mode is optional when the base is M-mode; VS and VU need H."""
    if mode == base:
        return body
    block = [f"\nRVTEST_TSBI_GOTO_{mode}MODE", *body, f"\nRVTEST_TSBI_GOTO_{base}MODE"]
    return gated(block, MODE_GUARDS.get(mode))


def _clear_unchecked(csr: str, reg: int, tmp: int) -> list[str]:
    """Clear the STATEEN0_UNCHECKED_BITS of a value read from hstateen0 or hstateen0h."""
    shift = 32 if csr.endswith("h") else 0
    lines: list[str] = []
    for bits, define in STATEEN0_UNCHECKED_BITS:
        if bits >> shift:
            mask = ~(bits >> shift) & ((1 << 64) - 1)
            lines += [f"#ifdef {define}", f"LI(x{tmp}, {mask:#x})", f"and x{reg}, x{reg}, x{tmp}", "#endif"]
    return lines


def _csr_lines(test_data: TestData, cg: str, cp: str, csrs: tuple[str, ...], tag: str, *, readable: bool) -> list[str]:
    """Access each CSR with csrrw, csrrs and csrrc.

    csr_access_test reads each CSR back for the signature, so it only works where the access does
    not trap. Otherwise write the destination register of each access to the signature.
    """
    lines: list[str] = []
    if readable:
        for csr in csrs:
            lines += gated(csr_access_test(test_data, (csr, None), cg, cp, bin_prefix=f"{tag}_"), CSR_GUARDS.get(csr))
        return lines
    rd, rs = test_data.int_regs.get_registers(2)
    lines.append(f"LI(x{rs}, -1)")
    for csr in csrs:
        access: list[str] = []
        for op in ("csrrw", "csrrs", "csrrc"):
            access += ["", test_data.add_testcase(f"{tag}_{csr}_{op}", cp, cg), f"{op} x{rd}, {csr}, x{rs}"]
            if csr in ("hstateen0", "hstateen0h"):  # TODO: Remove once Sail models every hstateen0 bit
                access += _clear_unchecked(csr, rd, rs)
                access.append(f"LI(x{rs}, -1)")
            access.append(write_sigupd(rd, test_data))
        lines += gated(access, CSR_GUARDS.get(csr))
    test_data.int_regs.return_registers([rd, rs])
    return lines


def _access_lines(
    test_data: TestData,
    cg: str,
    cp: str,
    csrs: tuple[str, ...],
    h_csrs: tuple[str, ...],
    insns: tuple[Insn, ...],
    mode: str,
    base: str,
    tag: str,
) -> list[str]:
    """Access CSRs and run insns in `mode`; h_csrs are accessed only with H."""
    readable = mode == base
    lines = _csr_lines(test_data, cg, cp, csrs, tag, readable=readable)
    if h_csrs:
        lines += gated(_csr_lines(test_data, cg, cp, h_csrs, tag, readable=readable), "defined(H_SUPPORTED)")
    if insns:
        rd, rs = test_data.int_regs.get_registers(2)
        lines.append(f"LI(x{rs}, -1)")
        for label, template in insns:
            lines += ["", test_data.add_testcase(f"{label}_{tag}", cp, cg), template.format(rd=f"x{rd}", rs=f"x{rs}")]
        test_data.int_regs.return_registers([rd, rs])
    return lines


def feature_tests(
    test_data: TestData,
    cg: str,
    cp: str,
    feat: StateenFeature,
    *,
    states: Sequence[Sequence[GateWrite]],
    modes: list[str],
    base: str,
) -> list[str]:
    """Access the feature's state from each mode in each state.

    Each state is a list of writes to the feature's bit in stateen CSRs, made in order from `base` mode.
    Write mstateen before hstateen before sstateen: a clear bit makes the same bit read-only zero in
    the lower-level CSRs. Every CSR written is saved first and restored afterwards.
    """
    gates = list(dict.fromkeys(csr for state in states for csr, _ in state))
    saves = test_data.int_regs.get_registers(len(gates))

    def per_gate(template: str) -> list[str]:
        """`template` with {csr} and {reg} filled in for the saved register of each gate CSR."""
        lines: list[str] = []
        for gate, reg in zip(gates, saves):
            lines += _level_gated(gate, _bit_lines(gate, feat, lambda c, _, r=reg: [template.format(csr=c, reg=r)]))
        return lines

    lines = [
        comment_banner(cp, f"{', '.join(gates)} {feat.name} states, accessed from {', '.join(modes)} mode"),
        *per_gate("csrr x{reg}, {csr}  # save {csr}"),
    ]
    for state in states:
        tag = "".join(f"{csr[0]}{on}" for csr, on in state)
        rd = test_data.int_regs.get_register()
        for csr, on in state:
            lines += _level_gated(csr, _write_bit(csr, feat, on=bool(on), reg=rd))
        test_data.int_regs.return_register(rd)
        for mode in modes:
            body = _access_lines(
                test_data, cg, cp, feat.csrs, feat.h_csrs, feat.insns, mode, base, f"{mode.lower()}_{tag}"
            )
            lines += _mode_block(mode, base, body)
    lines += per_gate("csrw {csr}, x{reg}  # restore {csr}")
    lines += [f"mv x{reg}, zero  # do not leave the gate CSR value in a register" for reg in saves]
    test_data.int_regs.return_registers(saves)
    return gated(arch_block(lines, *feat.arch), feat.guard)


def illegal_access_tests(
    test_data: TestData,
    cg: str,
    cp: str,
    csrs: list[str],
    *,
    modes: list[str],
    base: str,
) -> list[str]:
    """Access CSRs from modes that must not access them; every access traps."""
    lines = [comment_banner(cp, f"Access {', '.join(csrs)} from {', '.join(modes)} mode; each access traps")]
    for mode in modes:
        body = _access_lines(test_data, cg, cp, tuple(csrs), (), (), mode, base, mode.lower())
        lines += _mode_block(mode, base, body)
    return lines


def walk_tests(
    test_data: TestData,
    cg: str,
    cp: str,
    csr: str,
    *,
    modes: list[str],
    base: str,
    guard: str | None = None,
    unchecked_bits: list[tuple[int, str]] | None = None,
) -> list[str]:
    """Walk a one and a zero through every bit of a CSR from each mode.

    Each (bits, define) in `unchecked_bits` is walked but not checked when `define` is defined.
    """
    lines = [comment_banner(cp, f"Walking ones and zeros on {csr} from {', '.join(modes)} mode")]
    for mode in modes:
        prefix = f"{mode.lower()}_" if len(modes) > 1 else ""
        walk = csr_walk_test(test_data, (csr, None), cg, cp, bin_prefix=prefix, unchecked_bits=unchecked_bits)
        lines += _mode_block(mode, base, walk)
    return gated(lines, guard)


def stateen_walk_tests(
    test_data: TestData,
    test_chunks: list[TestChunk],
    cg: str,
    cp: str,
    csrs: list[str],
    *,
    base: str,
    guard: str | None = None,
) -> None:
    """Walk each mstateen or hstateen CSR from `base` mode, and its upper half on RV32, each in a new test chunk."""
    guard_h = f"{guard} && __riscv_xlen == 32" if guard else "__riscv_xlen == 32"
    for csr in csrs:
        unchecked = STATEEN0_UNCHECKED_BITS if csr.endswith("stateen0") else None
        unchecked_h = [(bits >> 32, define) for bits, define in unchecked or [] if bits >> 32] or None
        for name, cond, bits in ((csr, guard, unchecked), (f"{csr}h", guard_h, unchecked_h)):
            tc = test_data.new_test_chunk(test_chunks)
            tc.code.extend(
                walk_tests(test_data, cg, cp, name, modes=[base], base=base, guard=cond, unchecked_bits=bits)
            )
