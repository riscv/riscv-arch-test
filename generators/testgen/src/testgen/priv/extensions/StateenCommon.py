##################################
# StateenCommon.py
#
# Shared Smstateen and Ssstateen test-case generators.
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shared Smstateen and Ssstateen test-case generators.

Both suites test state-enable CSRs from a base privilege mode and differ only in the CSR that
gates the state (mstateen0 or sstateen0) and in the modes the state is accessed from.
"""

from collections.abc import Callable
from dataclasses import dataclass

from testgen.asm.csr import csr_access_test, csr_walk_test
from testgen.asm.helpers import arch_block, comment_banner, gated, write_sigupd
from testgen.data.state import TestData

# (testcase label, instruction template with {rd} and {rs})
Insn = tuple[str, str]


@dataclass(frozen=True)
class StateenFeature:
    """State gated by one bit of a stateen CSR."""

    mask: str  # encoding.h macro for the bit; bits 32 and up use mask_h in the "h" CSR on RV32
    mask_h: str | None = None
    csrs: tuple[str, ...] = ()  # CSRs accessed with csrrw, csrrs and csrrc
    rv32_csrs: tuple[str, ...] = ()  # extra CSRs on RV32 only
    insns: tuple[Insn, ...] = ()
    guard: str | None = None  # preprocessor condition for the state to exist
    arch: tuple[str, ...] = ()  # extensions the assembler needs
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

# Bits are the same in mstateen0 and sstateen0, but sstateen0 only has the fcsr and jvt bits.
FEATURES = {
    "fcsr": StateenFeature(
        "MSTATEEN0_FCSR", csrs=("frm", "fflags", "fcsr"), guard="defined(ZFINX_SUPPORTED)", arch=("zfinx",)
    ),
    "fp": StateenFeature("MSTATEEN0_FCSR", insns=FP_INSNS, guard="defined(ZFINX_SUPPORTED)", arch=("zfinx",)),
    "jvt": StateenFeature("MSTATEEN0_JVT", csrs=("jvt",), guard="defined(ZCMT_SUPPORTED)", arch=("zcmt",)),
    "ctr": StateenFeature(
        "MSTATEEN0_CTR", "MSTATEEN0H_CTR", ("sctrdepth", "sctrstatus"), guard="defined(SSCTR_SUPPORTED)"
    ),
    "srmcfg": StateenFeature(
        "MSTATEEN0_PRIV114", "MSTATEEN0H_PRIV114", ("srmcfg",), guard="defined(SSQOSID_SUPPORTED)", name="SRMCFG"
    ),
    "p1p13": StateenFeature(
        "MSTATEEN0_PRIV113",
        "MSTATEEN0H_PRIV113",
        ("hedelegh",),
        guard="defined(SM1P13P0_OR_LATER_SUPPORTED) && defined(H_SUPPORTED) && __riscv_xlen == 32",
        name="P1P13",
    ),
    "context": StateenFeature(
        "MSTATEEN0_HCONTEXT", "MSTATEEN0H_HCONTEXT", ("scontext",), guard="defined(SDTRIG_SUPPORTED)", name="CONTEXT"
    ),
    "imsic": StateenFeature(
        "MSTATEEN0_IMSIC", "MSTATEEN0H_IMSIC", ("stopei", "vstopei"), guard="defined(SSAIA_SUPPORTED)"
    ),
    "aia": StateenFeature(
        "MSTATEEN0_AIA", "MSTATEEN0H_AIA", ("stopi",), ("sieh", "siph"), guard="defined(SSAIA_SUPPORTED)"
    ),
    "envcfg": StateenFeature(
        "MSTATEEN0_HENVCFG",
        "MSTATEEN0H_HENVCFG",
        ("senvcfg",),
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


def _write_bit(csr: str, feat: StateenFeature, *, on: bool, reg: int) -> list[str]:
    op = "csrs" if on else "csrc"
    return _bit_lines(csr, feat, lambda c, m: [f"LI(x{reg}, {m})", f"{op} {c}, x{reg}  # {feat.name} = {int(on)}"])


def _mode_block(mode: str, base: str, body: list[str]) -> list[str]:
    """Run `body` in `mode` and return to `base`. S-mode is optional when the base is M-mode."""
    if mode == base:
        return body
    block = [f"\nRVTEST_TSBI_GOTO_{mode}MODE", *body, f"\nRVTEST_TSBI_GOTO_{base}MODE"]
    return gated(block, "defined(S_SUPPORTED)") if mode == "S" else block


def _csr_lines(test_data: TestData, cg: str, cp: str, csrs: tuple[str, ...], tag: str, *, readable: bool) -> list[str]:
    """Access each CSR with csrrw, csrrs and csrrc.

    csr_access_test reads each CSR back for the signature, so it only works where the access does
    not trap. Otherwise write the destination register of each access to the signature.
    """
    lines: list[str] = []
    if readable:
        for csr in csrs:
            lines += csr_access_test(test_data, (csr, None), cg, cp, bin_prefix=f"{tag}_")
        return lines
    rd, rs = test_data.int_regs.get_registers(2)
    lines.append(f"LI(x{rs}, -1)")
    for csr in csrs:
        for op in ("csrrw", "csrrs", "csrrc"):
            lines += ["", test_data.add_testcase(f"{tag}_{csr}_{op}", cp, cg), f"{op} x{rd}, {csr}, x{rs}"]
            lines.append(write_sigupd(rd, test_data))
    test_data.int_regs.return_registers([rd, rs])
    return lines


def _access_lines(
    test_data: TestData,
    cg: str,
    cp: str,
    feat_csrs: tuple[str, ...],
    rv32_csrs: tuple[str, ...],
    insns: tuple[Insn, ...],
    mode: str,
    base: str,
    tag: str,
) -> list[str]:
    """Access CSRs and run insns in `mode`; rv32_csrs are accessed on RV32 only."""
    readable = mode == base
    lines = _csr_lines(test_data, cg, cp, feat_csrs, tag, readable=readable)
    if rv32_csrs:
        lines += gated(_csr_lines(test_data, cg, cp, rv32_csrs, tag, readable=readable), "__riscv_xlen == 32")
    if insns:
        rd, rs = test_data.int_regs.get_registers(2)
        lines.append(f"LI(x{rs}, -1)")
        for label, template in insns:
            lines += ["", test_data.add_testcase(f"{label}_{tag}", cp, cg), template.format(rd=f"x{rd}", rs=f"x{rs}")]
        test_data.int_regs.return_registers([rd, rs])
    return lines


def feature_tests(
    test_data: TestData, cg: str, cp: str, feat: StateenFeature, *, gate: str, modes: list[str], base: str
) -> list[str]:
    """Access the feature's state from each mode with its bit of CSR `gate` set and clear.

    The gate bit is changed from `base` mode and the gate CSR is restored afterwards.
    """
    rd, save = test_data.int_regs.get_registers(2)
    lines = [
        comment_banner(cp, f"{gate} {feat.name} set and clear, accessed from {', '.join(modes)} mode"),
        *_bit_lines(gate, feat, lambda c, _: [f"csrr x{save}, {c}  # save {c}"]),
    ]
    for state in (0, 1):
        lines += _write_bit(gate, feat, on=bool(state), reg=rd)
        for mode in modes:
            tag = f"{mode.lower()}_{state}"
            body = _access_lines(test_data, cg, cp, feat.csrs, feat.rv32_csrs, feat.insns, mode, base, tag)
            lines += _mode_block(mode, base, body)
    lines += _bit_lines(gate, feat, lambda c, _: [f"csrw {c}, x{save}  # restore {c}"])
    test_data.int_regs.return_registers([rd, save])
    return gated(arch_block(lines, *feat.arch), feat.guard)


def illegal_access_tests(
    test_data: TestData,
    cg: str,
    cp: str,
    csrs: list[str],
    *,
    modes: list[str],
    base: str,
    rv32_csrs: tuple[str, ...] = (),
) -> list[str]:
    """Access CSRs from modes that must not access them; every access traps."""
    lines = [comment_banner(cp, f"Access {', '.join(csrs)} from {', '.join(modes)} mode; each access traps")]
    for mode in modes:
        body = _access_lines(test_data, cg, cp, tuple(csrs), rv32_csrs, (), mode, base, mode.lower())
        lines += _mode_block(mode, base, body)
    return lines


def walk_tests(
    test_data: TestData, cg: str, cp: str, csr: str, *, modes: list[str], base: str, guard: str | None = None
) -> list[str]:
    """Walk a one and a zero through every bit of a CSR from each mode."""
    lines = [comment_banner(cp, f"Walking ones and zeros on {csr} from {', '.join(modes)} mode")]
    for mode in modes:
        prefix = f"{mode.lower()}_" if len(modes) > 1 else ""
        walk = csr_walk_test(test_data, (csr, None), cg, cp, bin_prefix=prefix)
        lines += _mode_block(mode, base, walk)
    return gated(lines, guard)
