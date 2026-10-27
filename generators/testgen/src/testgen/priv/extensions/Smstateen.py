# Smstateen.py
# Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com
# Smstateen state-enable extension test generator.
# SPDX-License-Identifier: Apache-2.0
##################################

"""Smstateen privileged extension test generator."""

from testgen.asm.csr import csr_walk_test
from testgen.asm.helpers import arch_block, comment_banner, gated, write64_csr, write_sigupd
from testgen.constants import INDENT
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MSTATEEN_CSRS_64 = ["mstateen0", "mstateen1", "mstateen2", "mstateen3"]
MSTATEEN_CSRS_H = ["mstateen0h", "mstateen1h", "mstateen2h", "mstateen3h"]

CSR_OPS = ["csrrw", "csrrs", "csrrc", "csrr"]


IN_MMODE = f"{INDENT}# already in M-mode"  # M-mode is the default; just a marker comment

# Mode dispatch for the priv_mode_m_maybes_u coverpoints. Each entry is
# (label, line that switches into the mode, whether an S_SUPPORTED guard is needed).
# RVTEST_TSBI_GOTO_MMODE returns from any lower mode. Lower-mode-only coverpoints slice [1:].
_MODES_MUS = [
    ("mmode", IN_MMODE, False),
    ("umode", "RVTEST_TSBI_GOTO_UMODE", False),
    ("smode", "RVTEST_TSBI_GOTO_SMODE", True),
]

_H_CG = "Smstateen_H_cg"

# The H group's modes, entered from M-mode
_MODES_H = [
    ("hsmode", "RVTEST_TSBI_GOTO_SMODE", False),
    ("vsmode", "RVTEST_TSBI_GOTO_VSMODE", False),
    ("vumode", "RVTEST_TSBI_GOTO_VUMODE", False),
]

# Tests that are off because Sail 0.16, the reference model, does not model the state, so it cannot give the results
# on a hart that has it.  Their coverpoints and test plan rows stay, so the coverage shows as missing.  Set a flag to
# True to turn its tests on when Sail models the state.
AIA_TESTS = False  # Ssaia: cp_imsic, cp_aia and the IMSIC and AIA bits of the walks (riscv/sail-riscv#1134)
CSRIND_TESTS = False  # the CSRIND bit of the walks (riscv/sail-riscv#956)
CTR_TESTS = False  # Smctr: cp_ctr and the CTR bit of the walks
JVT_TESTS = False  # Zcmt: the jvt tests and the JVT bit of the walks (riscv/sail-riscv#1740)

# The mstateen0 and hstateen0 bits the walks leave out while their tests are off.  The sstateen0 walks can leave out
# only JVT.
STATEEN0_SKIP_BITS = (
    (0 if CSRIND_TESTS else 1 << 60)
    | (0 if AIA_TESTS else 1 << 59 | 1 << 58)
    | (0 if CTR_TESTS else 1 << 54)
    | (0 if JVT_TESTS else 1 << 2)
)

# hstateen0 bits the walks check: all but C, because custom state is optional
HSTATEEN0_WALK_MASK = 0xFFFFFFFFFFFFFFFE


# CSRs written by number, because not every assembler knows the name (LLVM lacks hedelegh)
_CSR_NUMBERS = {"hedelegh": 0x612}


def _csr_insn(op: str, rd: int, csr: str, rs1: int) -> str:
    """Emit a single CSR instruction line. csrr is read-only and only takes (rd, csr)."""
    num = _CSR_NUMBERS.get(csr)
    operand, comment = (f"{num:#x}", f"  # {csr}") if num else (csr, "")
    if op == "csrr":
        return f"{op} x{rd}, {operand}{comment}"
    return f"{op} x{rd}, {operand}, x{rs1}{comment}"


# ---------------------------------------------------------------------------
# cp_csr_illegal_accesses
#   Cross: priv_mode_s_u × mstateen_csrs × csrops
#   All CSR ops to mstateenN CSRs from U-mode AND S-mode — must trap.
# ---------------------------------------------------------------------------


def csr_illegal_accesses(
    test_data: TestData,
    *,
    covergroup: str,
    csrs: list[str],
    csrs_rv32: list[str] | None = None,
    modes: list[tuple[str, str, bool]],
    home: str,
) -> list[str]:
    """CSR ops on ``csrs`` (and ``csrs_rv32`` on RV32) from each of ``modes``, all of which trap.  ``home`` returns to
    the mode the test runs in after each mode."""
    coverpoint = "cp_csr_illegal_accesses"
    rv32 = csrs_rv32 or []
    temp_reg = test_data.int_regs.get_register()
    lines = []
    for mode_label, enter_line, needs_guard in modes:
        body = [enter_line]
        for csr in [*csrs, *rv32]:
            ops = []
            for op in CSR_OPS:
                ops.extend(
                    [
                        "",
                        test_data.add_testcase(f"{csr}_{op}_{mode_label}", coverpoint, covergroup),
                        _csr_insn(op, temp_reg, csr, temp_reg),
                    ]
                )
            body.extend(gated(ops, "__riscv_xlen == 32" if csr in rv32 else None))
        body.append(home)
        lines.extend(gated(body, "defined(S_SUPPORTED)" if needs_guard else None))
    test_data.int_regs.return_registers([temp_reg])
    return lines


def _generate_csr_illegal_accesses(test_data: TestData) -> list[str]:
    return [
        comment_banner(
            "cp_csr_illegal_accesses",
            "All CSR ops to mstateenN CSRs from U-mode and S-mode — must trap (M-only CSRs)",
        ),
        *csr_illegal_accesses(
            test_data,
            covergroup="Smstateen_cg",
            csrs=MSTATEEN_CSRS_64,
            csrs_rv32=MSTATEEN_CSRS_H,
            modes=_MODES_MUS[1:],
            home="RVTEST_TSBI_GOTO_MMODE",
        ),
    ]


# ---------------------------------------------------------------------------
# cp_walking_ones
#   Cross: mstateen_walk_csrs × csrops × csr_walk
#   mstateen_walk_csrs = mstateen0-3 always, mstateen0h-3h on RV32 only.
#   The H group walks hstateen0-3 the same way.
# ---------------------------------------------------------------------------


def stateen_walk(
    test_data: TestData,
    csr: str,
    *,
    covergroup: str,
    label: str,
    mask: int | None = None,
    skip_bits: int = 0,
    high_half: bool = False,
    tag: str = "",
) -> list[str]:
    """Walk ``csr``, and with ``high_half`` also <csr>h on RV32, checking the bits in ``mask`` (None checks them all)
    and leaving out ``skip_bits``.  ``label`` names the testcase; ``tag`` distinguishes the testcases of several
    walks of one CSR."""
    coverpoint = "cp_walking_ones"
    lines = [
        "",
        test_data.add_testcase(label.format(csr=csr), coverpoint, covergroup),
        *csr_walk_test(test_data, (csr, mask), covergroup, coverpoint, tag=tag, skip_bits=skip_bits),
    ]
    if high_half:
        high_mask = None if mask is None else mask >> 32
        lines.extend(
            [
                "#if __riscv_xlen == 32",
                "",
                test_data.add_testcase(label.format(csr=f"{csr}h"), coverpoint, covergroup),
                *csr_walk_test(
                    test_data, (f"{csr}h", high_mask), covergroup, coverpoint, tag=tag, skip_bits=skip_bits >> 32
                ),
                "#endif  // __riscv_xlen == 32",
            ]
        )
    return lines


def _generate_walking_ones(
    test_data: TestData,
    *,
    ctl: str = "mstateen",
    mask0: int | None = 0xDF80000000000006,
    skip0: int = STATEEN0_SKIP_BITS,
    covergroup: str = "Smstateen_cg",
    tag: str = "",
) -> list[str]:
    """Walk <ctl>0-3 (and <ctl>0h-3h on RV32) from M-mode.

    ``mask0`` selects which bits of <ctl>0 are checked against the signature; None checks them all.  The walk leaves
    out the bits in ``skip0``.  ``tag`` distinguishes the testcases of several walks.
    """
    lines = [
        comment_banner(
            "cp_walking_ones",
            f"Walking-1 and walking-0 patterns on {ctl}0-3 (+ {ctl}0h-3h on RV32) from M-mode",
        )
    ]
    walk = {"covergroup": covergroup, "label": f"{{csr}}_walk{tag}", "high_half": True, "tag": tag}

    # The default mask mirrors mstateen0's writable high-word bits on RV64:
    # SE0(63)|ENVCFG(62)|CSRIND(60)|AIA(59)|IMSIC(58)|CONTEXT(57)|P1P13(56)|SRMCFG(55), plus FCSR(1)|JVT(2) in the
    # low word. On RV32 mstateen0 is the low word (0x6) and those high bits live in mstateen0h (0xDF800000).
    lines.extend(stateen_walk(test_data, f"{ctl}0", mask=mask0, skip_bits=skip0, **walk))

    # mstateen1-3 define only bit 63 (SE1-SE3), which gates sstateenN (and hstateenN). It is
    # writable unless H is absent and sstateenN is all read-only zero (norm:mstateen_bit_63_roz);
    # every other bit is reserved and read-only zero, so the whole CSR is checked. hstateen1-3
    # likewise define only bit 63.
    for n in range(1, 4):
        lines.extend(stateen_walk(test_data, f"{ctl}{n}", **walk))

    return lines


# ---------------------------------------------------------------------------
# Bit-controlled feature coverpoints
#   cp_envcfg, cp_imsic, cp_aia, cp_context, cp_p1p13, cp_srmcfg, cp_ctr,
#   cp_mstateen0_se0_controls_sstateen0, cp_mstateen_se_controls_sstateen123
#
#   Each of these crosses csrops × <feature>_csr(s) × <feature>_state ×
#   priv_mode_m_maybes_u: a single mstateen control bit gates a small set of
#   S-mode CSRs, and the cross must be hit from M-, U-, and S-mode with the
#   control bit both set and cleared. They differ only in the control-bit
#   position and the gated CSR list. The H groups cross the same bits with
#   HS-, VS- and VU-mode, and with the matching hstateen bit.
# ---------------------------------------------------------------------------


def _stateen_bit(op: str, ctl: str, n: int, bit: int, temp_reg: int) -> list[str]:
    """Set (op csrs) or clear (op csrc) bit ``bit`` of <ctl><n>.  A bit above 31 is bit ``bit - 32`` of <ctl><n>h on
    RV32."""
    if bit < 32:
        return [f"LI(x{temp_reg}, {1 << bit:#x})", f"{op} {ctl}{n}, x{temp_reg}"]
    return [
        "#if __riscv_xlen == 64",
        f"LI(x{temp_reg}, {1 << bit:#x})",
        f"{op} {ctl}{n}, x{temp_reg}",
        "#else",
        f"LI(x{temp_reg}, {1 << (bit - 32):#x})",
        f"{op} {ctl}{n}h, x{temp_reg}",
        "#endif",
    ]


def bit_controlled_tests(
    test_data: TestData,
    *,
    coverpoint: str,
    bit: int,
    bit_name: str,
    banner: str,
    csrs: list[str],
    csrs_rv32: list[str] | None = None,
    covergroup: str = "Smstateen_cg",
    n: int = 0,
    ctl: str = "mstateen",
    modes: list[tuple[str, str, bool]] = _MODES_MUS,
    home: str = "RVTEST_TSBI_GOTO_MMODE",
    hstateen: bool = False,
    check: bool = False,
    preserve: bool = False,
    gates: dict[str, str] | None = None,
) -> list[str]:
    """Generate CSR-op tests in each of ``modes`` for one control bit of <ctl><n>.

    The control bit lives at ``bit`` in <ctl><n> on RV64 and at ``bit - 32`` in <ctl><n>h
    on RV32. It is written directly in the mode the test runs in: M-mode for mstateen, or
    HS-mode for hstateen, with ``home`` returning there after each mode. For each
    control-bit state (cleared, set) and each mode, every CSR in `csrs` is exercised with
    every op in CSR_OPS. The state is written before each mode because the accesses can
    change it.

    Args:
        csrs: CSRs to access.
        csrs_rv32: Additional CSRs to access on RV32 only (e.g. the AIA high halves sieh/siph).
        n: The control bit is in <ctl><n>.
        hstateen: Also set and clear the same bit of hstateen<n>, which is read-only zero
            while the mstateen bit is 0, so the (mstateen, hstateen) states are (0, 0),
            (1, 0) and (1, 1). The hstateen bit is written while the mstateen bit is 1.
        check: Record the value each op reads, for CSRs with no writable bits (sstateen1-3)
            and those whose value the control bits define (hstateen1-3).
        preserve: Save the accessed CSRs first and restore them after each mode, so writes
            of all 1s do not leak into later tests.
        gates: Preprocessor condition for each CSR that exists only on some configurations.
    """
    lines = [comment_banner(coverpoint, banner)]
    gates = gates or {}
    rv32 = csrs_rv32 or []
    all_csrs = [*csrs, *rv32]

    def gate(csr: str) -> str | None:
        return "__riscv_xlen == 32" if csr in rv32 else gates.get(csr)

    temp_reg, ones_reg = test_data.int_regs.get_registers(2)
    save_regs = test_data.int_regs.get_registers(len(all_csrs)) if preserve else []
    save = [
        line
        for csr, reg in zip(all_csrs, save_regs, strict=False)
        for line in gated([f"csrr x{reg}, {csr}  # save {csr}"], gate(csr))
    ]
    restore = [
        line
        for csr, reg in zip(all_csrs, save_regs, strict=False)
        for line in gated([f"csrw {csr}, x{reg}  # restore {csr}"], gate(csr))
    ]

    def emit_ops(tag: str, mode_label: str, refresh: list[str]) -> list[str]:
        out: list[str] = []
        for csr in all_csrs:
            body: list[str] = []
            for op in CSR_OPS:
                if refresh and csr.startswith(f"hstateen{n}"):
                    body.extend(refresh)
                body.extend(
                    [
                        "",
                        test_data.add_testcase(f"{csr}_{op}_{tag}_{mode_label}", coverpoint, covergroup),
                        _csr_insn(op, temp_reg, csr, ones_reg),
                    ]
                )
                if check:
                    body.append(write_sigupd(temp_reg, test_data))
            out.extend(gated(body, gate(csr)))
        return out

    lines.extend([f"LI(x{ones_reg}, -1)", *save])

    states = [(0, 0), (1, 0), (1, 1)] if hstateen else [(0, None), (1, None)]
    for state, h_state in states:
        tag = f"{bit_name}{state}" if h_state is None else f"{bit_name}{state}_h{h_state}"
        description = f"{ctl}{n}.{bit_name} = {state}"
        if h_state is not None:
            description += f", hstateen{n}.{bit_name} = {h_state}"
        for mode_label, enter_line, needs_guard in modes:
            if needs_guard:
                lines.append("#ifdef S_SUPPORTED")
            lines.extend(["", f"{INDENT}# {description} (bit {bit}), {mode_label}"])
            if h_state is not None:
                lines.extend(_stateen_bit("csrs", ctl, n, bit, temp_reg))
                lines.extend(_stateen_bit("csrs" if h_state else "csrc", "hstateen", n, bit, temp_reg))
            lines.extend(_stateen_bit("csrs" if state else "csrc", ctl, n, bit, temp_reg))
            # HS-mode can write hstateen<n> while the mstateen bit is 1, so each op on it rewrites the hstateen bit first
            refresh = []
            if h_state is not None and state and mode_label == "hsmode":
                refresh = _stateen_bit("csrs" if h_state else "csrc", "hstateen", n, bit, temp_reg)
            lines.append(enter_line)
            lines.extend(emit_ops(tag, mode_label, refresh))
            lines.append(home)
            lines.extend(restore)
            if needs_guard:
                lines.append("#endif  // S_SUPPORTED")

    test_data.int_regs.return_registers([temp_reg, ones_reg, *save_regs])
    return lines


# ---------------------------------------------------------------------------
# cp_jvt_access
#   Cross: priv_mode_maybes_u (S-mode + U-mode) × csrops × jvt_csr × jvt_state
#   The covergroup cross samples U/S-mode only — there is no M-mode jvt cross,
#   so M-mode jvt access is intentionally not exercised here.
# ---------------------------------------------------------------------------


def _generate_jvt(test_data: TestData) -> list[str]:
    # Lower modes only (U + S); the cp_jvt_access cross does not sample M-mode.
    return bit_controlled_tests(
        test_data,
        coverpoint="cp_jvt_access",
        bit=2,
        bit_name="jvt",
        banner="CSR ops on jvt from U/S-mode with mstateen0.jvt (bit 2) disabled and enabled",
        csrs=["jvt"],
        modes=_MODES_MUS[1:],
    )


# ---------------------------------------------------------------------------
# cp_fcsr_ro_zero
#   Cross: misa_F × csrops × mstateen0_fcsr_bit
#   Exercises the ignore_bins-covered path where fcsr reads as zero
#   when misa.F is set but mstateen0.fcsr (bit 1) is clear.
# ---------------------------------------------------------------------------


def _generate_fcsr_ro_zero(test_data: TestData) -> list[str]:
    coverpoint = "cp_fcsr_ro_zero"
    covergroup = "Smstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "misa.F set, mstateen0.fcsr (bit 1) clear — fcsr reads as zero (access-fault path)",
        )
    ]

    temp_reg, ones_reg = test_data.int_regs.get_registers(2)
    FCSR_BIT_MASK = 1 << 1  # bit 1 of mstateen0

    lines.extend(
        [
            f"LI(x{ones_reg}, -1)",
            "",
            f"{INDENT}# Ensure misa.F is set (read misa, verify F bit, then proceed)",
            f"csrr x{temp_reg}, misa",
            f"{INDENT}# bit 5 = F; test proceeds assuming F is present per MARCH",
            "",
            f"{INDENT}# Clear mstateen0.fcsr so fcsr reads zero",
            f"LI(x{temp_reg}, {FCSR_BIT_MASK})",
            f"csrc mstateen0, x{temp_reg}",
        ]
    )

    for op in CSR_OPS:
        lines.extend(
            [
                "",
                test_data.add_testcase(f"fcsr_{op.lower()}_ro_zero", coverpoint, covergroup),
                _csr_insn(op, temp_reg, "fcsr", ones_reg),
                "nop",
            ]
        )

    test_data.int_regs.return_registers([temp_reg, ones_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_fcsr
# ---------------------------------------------------------------------------


def _generate_fcsr(test_data: TestData) -> list[str]:
    coverpoint = "cp_fcsr"
    covergroup = "Smstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "M-mode CSR ops on fcsr under misa.F set and mstateen0.fcsr (bit 1) both states",
        )
    ]

    temp_reg, ones_reg = test_data.int_regs.get_registers(2)
    FCSR_BIT_MASK = 1 << 1

    lines.append(f"LI(x{ones_reg}, -1)")

    lines.extend(
        [
            "",
            f"{INDENT}# mstateen0.fcsr = 1 (only meaningful state per ignore_bins)",
            f"LI(x{temp_reg}, {FCSR_BIT_MASK})",
            f"csrs mstateen0, x{temp_reg}",
        ]
    )
    for op in CSR_OPS:
        lines.extend(
            [
                "",
                test_data.add_testcase(f"fcsr_{op.lower()}_fcsr1", coverpoint, covergroup),
                _csr_insn(op, temp_reg, "fcsr", ones_reg),
                "nop",
            ]
        )

    lines.extend(
        [
            "",
            f"{INDENT}# mstateen0.fcsr = 0",
            f"LI(x{temp_reg}, {FCSR_BIT_MASK})",
            f"csrc mstateen0, x{temp_reg}",
        ]
    )
    for op in CSR_OPS:
        lines.extend(
            [
                "",
                test_data.add_testcase(f"fcsr_{op.lower()}_fcsr0", coverpoint, covergroup),
                _csr_insn(op, temp_reg, "fcsr", ones_reg),
                "nop",
            ]
        )

    test_data.int_regs.return_registers([temp_reg, ones_reg])
    return lines


# ---------------------------------------------------------------------------
# cp_fcsr_lower
#   Cross: priv_mode_s_u × misa_F × mstateen0_fcsr_bit × csrops × fcsr_lower_mode_csrs
#   S-mode and U-mode only.
# ---------------------------------------------------------------------------


def _generate_fcsr_lower(test_data: TestData) -> list[str]:
    # Lower modes only (U + S); these crosses do not sample M-mode.
    return bit_controlled_tests(
        test_data,
        coverpoint="cp_fcsr_lower",
        bit=1,
        bit_name="fcsr",
        banner="S/U-mode CSR ops on frm/fflags/fcsr with mstateen0.fcsr (bit 1) both states",
        csrs=["frm", "fflags", "fcsr"],
        modes=_MODES_MUS[1:],
    )


# ---------------------------------------------------------------------------
# cp_fcsr_fp_instrs
#   Cross: priv_mode_s_u × misa_F × mstateen0_fcsr_bit × fp_instrs
#   S-mode and U-mode only.
# ---------------------------------------------------------------------------


def _generate_fcsr_lower_fp_instrs(test_data: TestData) -> list[str]:
    coverpoint = "cp_fcsr_fp_instrs"
    covergroup = "Smstateen_cg"

    lines = [
        comment_banner(
            coverpoint,
            "FP instructions from U/S-mode with mstateen0.fcsr (bit 1) disabled and enabled",
        )
    ]

    temp_reg1, temp_reg2, temp_reg3 = test_data.int_regs.get_registers(3)
    FCSR_BIT_MASK = 1 << 1

    fp_instrs = [
        (f"fadd.s x{temp_reg1}, x{temp_reg2}, x{temp_reg3}", "fadd_s"),
        (f"fcvt.w.s x{temp_reg1}, x{temp_reg2}", "fcvt_w_s"),
        (f"fcvt.s.w x{temp_reg1}, x{temp_reg2}", "fcvt_s_w"),
        (f"fclass.s x{temp_reg1}, x{temp_reg2}", "fclass_s"),
    ]

    # Lower modes only (U + S); these crosses do not sample M-mode.
    for mode_label, enter_line, needs_guard in _MODES_MUS[1:]:
        if needs_guard:
            lines.append("#ifdef S_SUPPORTED")
        for state in [0, 1]:
            bit_action = "csrc" if state == 0 else "csrs"
            lines.extend(
                [
                    "",
                    f"{INDENT}# mstateen0.fcsr = {state}, {mode_label}",
                    f"LI(x{temp_reg1}, {FCSR_BIT_MASK})",
                    f"{bit_action} mstateen0, x{temp_reg1}",
                ]
            )
            lines.append(enter_line)
            for insn, label in fp_instrs:
                lines.extend(
                    [
                        "",
                        test_data.add_testcase(f"{label}_fcsr{state}_{mode_label}", coverpoint, covergroup),
                        insn,
                    ]
                )
            lines.append("RVTEST_TSBI_GOTO_MMODE")
        if needs_guard:
            lines.append("#endif  // S_SUPPORTED")

    test_data.int_regs.return_registers([temp_reg1, temp_reg2, temp_reg3])
    return lines


def _se_tests(test_data: TestData, n: int, *, h_group: bool = False) -> list[str]:
    """CSR ops on sstateen<n> from S-mode with SE<n> (bit 63 of mstateen<n>) set or clear.

    The subject is the M-mode control bit, which is why this lives in Smstateen rather
    than Ssstateen. sstateen1-3 have no defined bits, so for them each access also checks
    the value read, which must be zero (norm:stateen_reserved_roz) whenever the access does
    not trap. The H group makes the accesses from HS-, VS- and VU-mode, also to hstateen<n>,
    and crosses SE<n> with bit 63 of hstateen<n>, which controls VS-mode access to sstateen<n>.
    """
    coverpoint = "cp_mstateen0_se0_controls_sstateen0" if n == 0 else "cp_mstateen_se_controls_sstateen123"
    csrs = [f"sstateen{n}", f"hstateen{n}"] if h_group else [f"sstateen{n}"]
    where = "HS-, VS- and VU-mode" if h_group else "S-mode"
    return bit_controlled_tests(
        test_data,
        coverpoint=coverpoint,
        covergroup=_H_CG if h_group else "Smstateen_cg",
        bit=63,
        bit_name="se",
        n=n,
        banner=f"CSR ops on {', '.join(csrs)} from {where} with mstateen{n}.SE{n} (bit 63) disabled and enabled",
        csrs=csrs,
        csrs_rv32=[f"hstateen{n}h"] if h_group else None,
        modes=_MODES_H if h_group else _MODES_MUS[2:],
        hstateen=h_group,
        check=n > 0,
        preserve=True,
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


@add_priv_test_generator(
    "Smstateen",
    required_extensions=["Smstateen"],
    march_extensions=["Smstateen"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_smstateen(test_data: TestData) -> list[TestChunk]:
    """Generate tests for Smstateen state-enable extension testsuite."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()

    # Unconditional coverpoints — required by all Smstateen targets
    tc.code.extend(_generate_csr_illegal_accesses(test_data))
    tc.code.extend(_generate_walking_ones(test_data))

    # cp_envcfg — only when SM1P11P0 is not present
    tc.code.append("#ifdef SM1P12P0_OR_LATER_SUPPORTED")
    tc.code.extend(
        bit_controlled_tests(
            test_data,
            coverpoint="cp_envcfg",
            bit=62,
            bit_name="envcfg",
            banner="CSR ops on senvcfg from M/S/U-mode with mstateen0.envcfg (bit 62) enabled and disabled",
            csrs=["senvcfg"],
        )
    )
    tc.code.append("#endif")

    if AIA_TESTS:
        # cp_imsic — only when IMSIC is present
        tc.code.append("#ifdef SSAIA_SUPPORTED")
        tc.code.extend(
            bit_controlled_tests(
                test_data,
                coverpoint="cp_imsic",
                bit=58,
                bit_name="imsic",
                banner="CSR ops on stopei/vstopei with mstateen0.imsic (bit 58) disabled and enabled — M/S/U-mode",
                csrs=["stopei", "vstopei"],
            )
        )
        tc.code.append("#endif  // SSAIA_SUPPORTED")

        # cp_aia — only when AIA is present
        tc.code.append("#ifdef SSAIA_SUPPORTED")
        tc.code.extend(
            bit_controlled_tests(
                test_data,
                coverpoint="cp_aia",
                bit=59,
                bit_name="aia",
                banner="CSR ops on Ssaia CSRs with mstateen0.aia (bit 59) disabled and enabled — M/S/U-mode",
                csrs=["stopi"],
                csrs_rv32=["sieh", "siph"],
            )
        )
        tc.code.append("#endif  // SSAIA_SUPPORTED")

    if JVT_TESTS:
        # cp_jvt_access — only when Zcmt is present (covers S-mode and U-mode)
        tc.code.append("#ifdef ZCMT_SUPPORTED")
        tc.code.extend(arch_block(_generate_jvt(test_data), "zcmt"))
        tc.code.append("#endif  // ZCMT_SUPPORTED")

    # cp_context — only when Sdtrig is present
    tc.code.append("#ifdef SDTRIG_SUPPORTED")
    tc.code.extend(
        bit_controlled_tests(
            test_data,
            coverpoint="cp_context",
            bit=57,
            bit_name="context",
            banner="CSR ops on scontext with mstateen0.context (bit 57) disabled and enabled — M/S/U-mode",
            csrs=["scontext"],
        )
    )
    tc.code.append("#endif  // SDTRIG_SUPPORTED")

    # cp_p1p13 — only when Sm1p13 + Hypervisor present. hedelegh is the high half of
    # hedeleg and exists only on RV32; on RV64 mstateen0.P1P13 is read-only zero.
    tc.code.append("#if defined(SM1P13P0_OR_LATER_SUPPORTED) && defined(H_SUPPORTED) && __riscv_xlen == 32")
    tc.code.extend(
        bit_controlled_tests(
            test_data,
            coverpoint="cp_p1p13",
            bit=56,
            bit_name="p1p13",
            banner="CSR ops on hedelegh with mstateen0.p1p13 (bit 56) disabled and enabled — M/S/U-mode",
            csrs=["hedelegh"],
        )
    )
    tc.code.append("#endif  // SM1P13P0_OR_LATER_SUPPORTED && H_SUPPORTED && RV32")

    # cp_srmcfg — only when Ssqosid is present
    tc.code.append("#ifdef SSQOSID_SUPPORTED")
    tc.code.extend(
        bit_controlled_tests(
            test_data,
            coverpoint="cp_srmcfg",
            bit=55,
            bit_name="srmcfg",
            banner="CSR ops on srmcfg with mstateen0.srmcfg (bit 55) disabled and enabled — M/S/U-mode",
            csrs=["srmcfg"],
        )
    )
    tc.code.append("#endif  // SSQOSID_SUPPORTED")

    if CTR_TESTS:
        # cp_ctr — only when Sctr is present
        tc.code.append("#ifdef SSCTR_SUPPORTED")
        tc.code.extend(
            bit_controlled_tests(
                test_data,
                coverpoint="cp_ctr",
                bit=54,
                bit_name="ctr",
                banner="CSR ops on sctrdepth/sctrstatus with mstateen0.ctr (bit 54) disabled and enabled — M/S/U-mode",
                csrs=["sctrdepth", "sctrstatus"],
            )
        )
        tc.code.append("#endif  // SSCTR_SUPPORTED")

    # cp_fcsr, cp_fcsr_ro_zero, cp_fcsr_lower, cp_fcsr_fp_instrs — only when Zfinx present
    tc.code.append("#ifdef ZFINX_SUPPORTED")
    fcsr_lines = [
        *_generate_fcsr_ro_zero(test_data),
        *_generate_fcsr(test_data),
        *_generate_fcsr_lower(test_data),
        *_generate_fcsr_lower_fp_instrs(test_data),
    ]
    tc.code.extend(arch_block(fcsr_lines, "zfinx"))
    tc.code.append("#endif  // ZFINX_SUPPORTED")

    test_chunks.append(test_data.end_test_chunk())

    # mstateenN.SE<N> (bit 63) gating of sstateenN, kept in its own chunk so it lands in its own file.
    # sstateenN only exists under Ssstateen, which also implies S-mode.
    tc = test_data.begin_test_chunk()
    tc.code.append("#ifdef SSSTATEEN_SUPPORTED")
    for n in range(4):
        tc.code.extend(_se_tests(test_data, n))
    tc.code.append("#endif  // SSSTATEEN_SUPPORTED")
    test_chunks.append(test_data.end_test_chunk())

    return test_chunks


# ---------------------------------------------------------------------------
# H group: mstateen control of HS-, VS- and VU-mode access, and the hstateen bits
# that mstateen makes read-only zero. It boots to M-mode, like the base tests.
# ---------------------------------------------------------------------------


def _h_gate_tests(test_data: TestData) -> list[str]:
    """cp_envcfg, cp_context, cp_p1p13 and cp_srmcfg from HS-, VS- and VU-mode.

    mstateen0.ENVCFG and CONTEXT are crossed with the same hstateen0 bit, which controls VS-mode access. hstateen0
    has no P1P13 or SRMCFG bit. HS-mode access to hedelegh is in the base tests, where S-mode is HS-mode.
    """
    common = {"covergroup": _H_CG, "modes": _MODES_H}
    lines = bit_controlled_tests(
        test_data,
        coverpoint="cp_envcfg",
        bit=62,
        bit_name="envcfg",
        banner="CSR ops on senvcfg and henvcfg from HS/VS/VU-mode with mstateen0.envcfg and hstateen0.envcfg (bit 62)",
        csrs=["senvcfg", "henvcfg"],
        csrs_rv32=["henvcfgh"],
        hstateen=True,
        preserve=True,
        **common,
    )
    # The Sdtrig context CSRs exist only where the configuration implements them; none has hcontext without scontext
    lines.append("#ifdef UDB_SCONTEXT_IMPLEMENTED")
    lines.extend(
        bit_controlled_tests(
            test_data,
            coverpoint="cp_context",
            bit=57,
            bit_name="context",
            banner="CSR ops on scontext and hcontext from HS/VS/VU-mode with mstateen0.context and "
            "hstateen0.context (bit 57)",
            csrs=["scontext", "hcontext"],
            hstateen=True,
            preserve=True,
            gates={"hcontext": "defined(UDB_HCONTEXT_IMPLEMENTED)"},
            **common,
        )
    )
    lines.append("#endif  // UDB_SCONTEXT_IMPLEMENTED")
    # hedelegh is the high half of hedeleg and exists only on RV32 from Priv 1.13
    lines.append("#if defined(SM1P13P0_OR_LATER_SUPPORTED) && __riscv_xlen == 32")
    lines.extend(
        bit_controlled_tests(
            test_data,
            coverpoint="cp_p1p13",
            bit=56,
            bit_name="p1p13",
            banner="CSR ops on hedelegh from VS/VU-mode with mstateen0.p1p13 (bit 56) disabled and enabled",
            csrs=["hedelegh"],
            covergroup=_H_CG,
            modes=_MODES_H[1:],
        )
    )
    lines.append("#endif  // SM1P13P0_OR_LATER_SUPPORTED && RV32")
    lines.append("#ifdef SSQOSID_SUPPORTED")
    lines.extend(
        bit_controlled_tests(
            test_data,
            coverpoint="cp_srmcfg",
            bit=55,
            bit_name="srmcfg",
            banner="CSR ops on srmcfg from HS/VS/VU-mode with mstateen0.srmcfg (bit 55) disabled and enabled",
            csrs=["srmcfg"],
            preserve=True,
            **common,
        )
    )
    lines.append("#endif  // SSQOSID_SUPPORTED")
    return lines


def _h_walking_ones(test_data: TestData) -> list[str]:
    """Walk hstateen0-3 from M-mode with mstateen0-3 all zeros, which makes every hstateen bit read-only zero, and
    then all ones. mstateen0-3 are left all ones."""
    temp_reg = test_data.int_regs.get_register()
    lines = []
    for state in (0, 1):
        lines.append(f"{INDENT}# mstateen0-3 = {'all ones' if state else 'zero'}")
        for n in range(4):
            lines.extend(write64_csr(f"mstateen{n}", -state, temp_reg))
        lines.extend(
            _generate_walking_ones(
                test_data,
                ctl="hstateen",
                mask0=HSTATEEN0_WALK_MASK if state else None,
                skip0=STATEEN0_SKIP_BITS if state else 0,
                covergroup=_H_CG,
                tag=f"_m{state}",
            )
        )
    test_data.int_regs.return_registers([temp_reg])
    return lines


@add_priv_test_generator(
    "Smstateen",
    required_extensions=["Smstateen", "Ssstateen", "H"],
    march_extensions=["Smstateen"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_smstateen_h(test_data: TestData) -> list[TestChunk]:
    """Generate the Smstateen H group tests."""
    test_chunks: list[TestChunk] = []

    tc = test_data.new_test_chunk(test_chunks, "H_se")
    for n in range(4):
        tc.code.extend(_se_tests(test_data, n, h_group=True))

    tc = test_data.new_test_chunk(test_chunks, "H_gate")
    tc.code.extend(_h_gate_tests(test_data))

    tc = test_data.new_test_chunk(test_chunks, "H_walk")
    tc.code.extend(_h_walking_ones(test_data))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
