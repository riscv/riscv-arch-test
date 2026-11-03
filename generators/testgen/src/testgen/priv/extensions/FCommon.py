##################################
# priv/extensions/FCommon.py
#
# Shared floating-point CSR and xstatus.FS test generation for Sm_F (M-mode, mstatus.FS),
# S_F (S-mode, sstatus.FS), U_F (U-mode, sstatus.FS or mstatus.FS through T-SBI) and
# H_F (VS- and VU-mode, vsstatus.FS crossed with sstatus.FS).
# David_Harris@hmc.edu 1 March 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Functions for generating floating-point CSR and xstatus.FS tests in M-, S-, U-, VS- and VU-mode."""

import itertools
from dataclasses import dataclass

from testgen.asm.csr import gen_csr_read_sigupd
from testgen.asm.helpers import comment_banner, load_float_reg
from testgen.constants import INDENT
from testgen.data.state import TestData
from testgen.priv.extensions.PrivCommon import (
    STATUS_CSR,
    gen_status_read_sigupd,
    hs_note,
    hs_status_values,
    hs_tag,
    set_status_fields,
)

# fp CSRs
_FCSRS = [("fcsr", None), ("frm", None), ("fflags", None)]

_ACCESS_COVERPOINT = "cp_fcsr_access"

# H_F (VS- and VU-mode) tests only what the hypervisor adds (norm:vsstatus_fs_op): an fp instruction
# is illegal when either vsstatus.FS or sstatus.FS is Off, and changing fp state sets both to Dirty.
# Which instructions change fp state is already tested per instruction by Sm_F, S_F and U_F, so H_F
# uses one instruction of each kind, and accesses the fp CSRs only with both fields Dirty or one Off.
_H_ACCESS_FS_PAIRS = [(3, 3), (0, 3), (3, 0)]  # (vsstatus.FS, sstatus.FS)


@dataclass(frozen=True)
class _FcsrRegs:
    """Integer registers used by the FP CSR and xstatus.FS tests."""

    ones: int
    check: int
    scratch: int
    temp: int
    save: int


def _gen_fp_csr_init(csr_name: str, value: int, temp_reg: int, priv: str) -> str:
    """Initialize an FP CSR while xstatus.FS is Dirty."""
    lines = [
        *set_status_fields(temp_reg, priv, fs=3),
        f"LI(x{temp_reg}, {value})",
        f"csrw {csr_name}, x{temp_reg} # Initialize {csr_name}",
    ]
    return "\n".join(lines)


def _access_banner(priv: str) -> str:
    return comment_banner(
        _ACCESS_COVERPOINT,
        f"Read, write all 1s, write all 0s, set all 1s, set all 0s, restore all fp CSRs from {priv}-mode with different {STATUS_CSR[priv]}.FS",
    )


def _access_setup(regs: _FcsrRegs) -> list[str]:
    """Set up the registers the cp_fcsr_access testcases read."""
    return [f"LI(x{regs.ones}, -1)\n"]


def _gen_fcsr_access(
    test_data: TestData, priv: str, covergroup: str, regs: _FcsrRegs, fs: int, hs: int | None
) -> list[str]:
    """cp_fcsr_access testcases for one value of xstatus.FS (and of sstatus.FS in VS- and VU-mode)."""
    status = STATUS_CSR[priv]
    coverpoint = _ACCESS_COVERPOINT
    ones_reg, check_reg, temp_reg, save_reg = regs.ones, regs.check, regs.temp, regs.save
    lines = []
    for csr in _FCSRS:
        csr_name, _mask = csr
        lines.extend(
            [
                f"# Testcase: {csr_name} access with {status}.FS={fs}{hs_note(hs)}: write 1s",
                *set_status_fields(temp_reg, priv, fs=fs, hs_fs=hs),
                f"csrr x{save_reg}, {csr_name}    # Save CSR",
                test_data.add_testcase(f"fs{fs}{hs_tag(hs)}_{csr_name}_csrrw1_{status}", coverpoint, covergroup),
                f"csrw {csr_name}, x{ones_reg}    # Write all 1s to CSR",
                gen_status_read_sigupd(check_reg, test_data, priv),
                test_data.add_testcase(f"fs{fs}{hs_tag(hs)}_{csr_name}_csrrw1_csr", coverpoint, covergroup),
                gen_csr_read_sigupd(check_reg, csr, test_data),
                "",
                f"# Testcase: {csr_name} access with {status}.FS={fs}{hs_note(hs)}: write 0s",
                *set_status_fields(temp_reg, priv, fs=fs, hs_fs=hs),
                test_data.add_testcase(f"fs{fs}{hs_tag(hs)}_{csr_name}_csrrw0_{status}", coverpoint, covergroup),
                f"csrw {csr_name}, zero   # Write all 0s to CSR",
                gen_status_read_sigupd(check_reg, test_data, priv),
                test_data.add_testcase(f"fs{fs}{hs_tag(hs)}_{csr_name}_csrrw0_csr", coverpoint, covergroup),
                gen_csr_read_sigupd(check_reg, csr, test_data),
                "",
                f"# Testcase: {csr_name} access with {status}.FS={fs}{hs_note(hs)}: set all bits",
                *set_status_fields(temp_reg, priv, fs=fs, hs_fs=hs),
                test_data.add_testcase(f"fs{fs}{hs_tag(hs)}_{csr_name}_csrs_all_{status}", coverpoint, covergroup),
                f"csrs {csr_name}, x{ones_reg}    # Set all CSR bits",
                gen_status_read_sigupd(check_reg, test_data, priv),
                test_data.add_testcase(f"fs{fs}{hs_tag(hs)}_{csr_name}_csrs_all_csr", coverpoint, covergroup),
                gen_csr_read_sigupd(check_reg, csr, test_data),
                "",
                f"# Testcase: {csr_name} access with {status}.FS={fs}{hs_note(hs)}: clear all bits",
                *set_status_fields(temp_reg, priv, fs=fs, hs_fs=hs),
                test_data.add_testcase(f"fs{fs}{hs_tag(hs)}_{csr_name}_csrrc_all_{status}", coverpoint, covergroup),
                f"csrc {csr_name}, x{ones_reg}    # Clear all CSR bits",
                gen_status_read_sigupd(check_reg, test_data, priv),
                test_data.add_testcase(f"fs{fs}{hs_tag(hs)}_{csr_name}_csrrc_all_csr", coverpoint, covergroup),
                gen_csr_read_sigupd(check_reg, csr, test_data),
                f"csrw {csr_name}, x{save_reg}       # Restore CSR",
                "",
            ]
        )
    return lines


def _transition_coverpoint(priv: str) -> str:
    return f"cp_{STATUS_CSR[priv]}_FS_transition"


def _transition_banner(priv: str) -> str:
    return comment_banner(
        _transition_coverpoint(priv),
        f"Attempt different types of fp instructions crossed with values of {STATUS_CSR[priv]}.FS",
    )


def _transition_setup(test_data: TestData, priv: str, regs: _FcsrRegs) -> list[str]:
    """Set up the scratch pointer and the fp registers the cp_xstatus_FS_transition testcases read."""
    return [
        f"{INDENT}# set up for {_transition_coverpoint(priv)}",
        f"LA(x{regs.scratch}, scratch)  # pointer to scratch register",
        load_float_reg("1.0", 1, 0x3F800000, test_data, "single"),
        load_float_reg("3.0", 2, 0x40400000, test_data, "single"),
        load_float_reg("tiny", 3, 0x00800000, test_data, "single"),
        load_float_reg("signaling NaN", 4, 0x7FA00000, test_data, "single"),
        load_float_reg("1.5", 5, 0x3FC00000, test_data, "single"),
        load_float_reg("-1.0", 6, 0xBF800000, test_data, "single"),
    ]


def _gen_fs_transition(
    test_data: TestData,
    priv: str,
    covergroup: str,
    regs: _FcsrRegs,
    fs: int,
    hs: int | None,
    representative: bool = False,
) -> list[str]:
    """cp_xstatus_FS_transition testcases for one value of xstatus.FS (and of sstatus.FS in VS- and VU-mode).

    With representative, only one instruction of each kind, and none of the D or Zfa instructions.
    """
    status = STATUS_CSR[priv]
    coverpoint = _transition_coverpoint(priv)
    temp_reg, scratch_reg = regs.temp, regs.scratch

    # For FS=Initial/Clean, instructions that do not deterministically update floating-point state
    # can legally either leave FS unchanged or dirty it. Skip those cases.
    nondeterministic_initial_clean_insns = [
        f"fsw f1, 0(x{scratch_reg})",
        f"fmv.x.w x{temp_reg}, f1",
        f"fclass.s x{temp_reg}, f3",
        f"csrr x{temp_reg}, fcsr",
        f"csrr x{temp_reg}, frm",
        f"csrr x{temp_reg}, fflags",
    ]
    fp_csr_write_insns = [
        f"csrrw x{temp_reg}, fcsr, x{temp_reg}",
        f"csrrw x{temp_reg}, frm, x{temp_reg}",
        f"csrrw x{temp_reg}, fflags, x{temp_reg}",
        f"csrrs x{temp_reg}, fcsr, x{temp_reg}",
        f"csrrs x{temp_reg}, frm, x{temp_reg}",
        f"csrrs x{temp_reg}, fflags, x{temp_reg}",
        f"csrrc x{temp_reg}, fcsr, x{temp_reg}",
        f"csrrc x{temp_reg}, frm, x{temp_reg}",
        f"csrrc x{temp_reg}, fflags, x{temp_reg}",
    ]
    # Integer-result instructions that raise fflags must dirty FS. Each operand set raises a flag
    # (NV for feq.s with a signaling NaN and fcvt.wu.s of -1.0, NX for fcvt.w.s of 1.5).
    flag_raising_insns = [
        f"feq.s x{temp_reg}, f4, f4",
        f"fcvt.w.s x{temp_reg}, f5",
        f"fcvt.wu.s x{temp_reg}, f6",
    ]
    deterministic_insns = [
        f"flw f0, 0(x{scratch_reg})",
        "fadd.s f0, f1, f2",
        "fsub.s f0, f1, f2",
        "fmul.s f0, f1, f2",
        "fdiv.s f0, f1, f2",
        "fcvt.s.w f0, x0",
        "fmadd.s f0, f1, f2, f3",
        "fsqrt.s f0, f1",
        "fsgnj.s f0, f1, f2",
        f"fmv.w.x f0, x{temp_reg}",
        "fmin.s f0, f1, f2",
        f"add x{temp_reg}, x{temp_reg}, x{temp_reg}",
    ]
    insns = [*nondeterministic_initial_clean_insns, *fp_csr_write_insns, *deterministic_insns, *flag_raising_insns]
    if representative:  # one instruction of each kind
        insns = [
            nondeterministic_initial_clean_insns[0],  # fsw
            nondeterministic_initial_clean_insns[3],  # csrr fcsr
            fp_csr_write_insns[0],  # csrrw fcsr
            deterministic_insns[0],  # flw
            deterministic_insns[1],  # fadd.s
            deterministic_insns[-1],  # add, which must not change fp state
            flag_raising_insns[0],  # feq.s of a signaling NaN, which only sets fflags
        ]
    # fsw, fmv.x.w, fclass.s, csrr of FP CSRs, and fmvh.x.d have their own cross
    coverpoint_nd = f"{coverpoint}_nondeterministic"

    lines = []
    imprecise = fs in (1, 2) or hs in (1, 2)  # FS=Initial or Clean at either level
    for insn in insns:
        if imprecise and insn in nondeterministic_initial_clean_insns:
            continue  # skip nondeterministic instructions for FS=1 or FS=2
        if insn in fp_csr_write_insns:
            if "fcsr" in insn:
                csr_name = "fcsr"
            elif "frm" in insn:
                csr_name = "frm"
            else:
                csr_name = "fflags"
            setup_lines = [
                _gen_fp_csr_init(csr_name, 1 if "csrrc" in insn else 0, temp_reg, priv),
                *set_status_fields(temp_reg, priv, fs=fs, hs_fs=hs),
                f"LI(x{temp_reg}, 1) # make {insn} change {csr_name}",
            ]
        elif insn in flag_raising_insns:
            setup_lines = [
                _gen_fp_csr_init("fflags", 0, temp_reg, priv),  # clear fflags so the instruction must set a flag
                *set_status_fields(temp_reg, priv, fs=fs, hs_fs=hs),
            ]
        else:
            setup_lines = set_status_fields(temp_reg, priv, fs=fs, hs_fs=hs)
        cp = coverpoint_nd if insn in nondeterministic_initial_clean_insns else coverpoint
        lines.extend(
            [
                "",
                f"# Testcase: {insn} with {status}.FS={fs}{hs_note(hs)}",
                *setup_lines,
                test_data.add_testcase(f"fs{fs}{hs_tag(hs)}_{insn}", cp, covergroup),
                f"{insn} # execute instruction with {status}.FS={fs}{hs_note(hs)}",
                gen_status_read_sigupd(temp_reg, test_data, priv),
            ]
        )
    if representative:
        return lines
    lines.append("\n#ifdef D_SUPPORTED")
    for insn in ["fcvt.s.d f0, f1"]:
        lines.extend(
            [
                "",
                f"# Testcase: {insn} with {status}.FS={fs}{hs_note(hs)}",
                *set_status_fields(temp_reg, priv, fs=fs, hs_fs=hs),
                test_data.add_testcase(f"fs{fs}{hs_tag(hs)}_{insn}", coverpoint, covergroup),
                f"{insn} # execute instruction with {status}.FS={fs}{hs_note(hs)}",
                gen_status_read_sigupd(temp_reg, test_data, priv),
            ]
        )
    # f4 holds a NaN-boxed single, which is a NaN as a double, so fcvtmod.w.d raises NV.
    lines.append("\n#ifdef ZFA_SUPPORTED")
    insn = f"fcvtmod.w.d x{temp_reg}, f4, rtz"
    lines.extend(
        [
            "",
            f"# Testcase: {insn} with {status}.FS={fs}{hs_note(hs)}",
            _gen_fp_csr_init("fflags", 0, temp_reg, priv),  # clear fflags so the instruction must set a flag
            *set_status_fields(temp_reg, priv, fs=fs, hs_fs=hs),
            test_data.add_testcase(f"fs{fs}{hs_tag(hs)}_{insn}", coverpoint, covergroup),
            f"{insn} # execute instruction with {status}.FS={fs}{hs_note(hs)}",
            gen_status_read_sigupd(temp_reg, test_data, priv),
            "",
            "#if __riscv_xlen == 32",
        ]
    )
    for insn in [f"fmvh.x.d x{temp_reg}, f1", f"fmvp.d.x f0, x{temp_reg}, x{temp_reg}"]:
        if imprecise and insn.startswith("fmvh.x.d "):
            continue
        cp = coverpoint_nd if insn.startswith("fmvh.x.d ") else coverpoint
        lines.extend(
            [
                "",
                f"# Testcase: {insn} with {status}.FS={fs}{hs_note(hs)}",
                *set_status_fields(temp_reg, priv, fs=fs, hs_fs=hs),
                test_data.add_testcase(f"fs{fs}{hs_tag(hs)}_{insn}", cp, covergroup),
                f"{insn} # execute instruction with {status}.FS={fs}{hs_note(hs)}",
                gen_status_read_sigupd(temp_reg, test_data, priv),
            ]
        )
    lines.extend(
        [
            "",
            "#endif",
            "#endif",
            "#endif",
            "",
            "#ifdef ZFA_SUPPORTED",
        ]
    )
    for insn in ["fli.s f0, 0.5", "fround.s f0, f3, rup"]:
        lines.extend(
            [
                "",
                *set_status_fields(temp_reg, priv, fs=fs, hs_fs=hs),
                test_data.add_testcase(f"fs{fs}{hs_tag(hs)}_{insn}", coverpoint, covergroup),
                f"{insn} # execute instruction with {status}.FS={fs}{hs_note(hs)}",
                gen_status_read_sigupd(temp_reg, test_data, priv),
            ]
        )
    lines.append("\n#endif")
    return lines


def _get_fcsr_regs(test_data: TestData) -> _FcsrRegs:
    ones_reg, check_reg, scratch_reg, temp_reg, save_reg = test_data.int_regs.get_registers(5)
    return _FcsrRegs(ones=ones_reg, check=check_reg, scratch=scratch_reg, temp=temp_reg, save=save_reg)


def _return_fcsr_regs(test_data: TestData, regs: _FcsrRegs) -> None:
    test_data.int_regs.return_registers([regs.ones, regs.check, regs.temp, regs.scratch, regs.save])


def gen_fcsr_tests(test_data: TestData, priv: str, covergroup: str) -> list[str]:
    """Generate FP CSR and xstatus.FS tests in privilege mode priv ("M", "S" or "U") as the code of one chunk."""
    regs = _get_fcsr_regs(test_data)
    lines = [_access_banner(priv), *_access_setup(regs)]
    for fs, hs in itertools.product(range(4), hs_status_values(priv)):
        lines.extend(_gen_fcsr_access(test_data, priv, covergroup, regs, fs, hs))
    lines.append(_transition_banner(priv))
    lines.extend(_transition_setup(test_data, priv, regs))
    for fs, hs in itertools.product(range(4), hs_status_values(priv)):
        lines.extend(_gen_fs_transition(test_data, priv, covergroup, regs, fs, hs))
    _return_fcsr_regs(test_data, regs)
    return lines


def gen_h_fcsr_tests(test_data: TestData, priv: str, covergroup: str) -> list[str]:
    """Generate the H_F fp CSR and FS tests in VS- or VU-mode (priv) as the code of one chunk.

    For each (vsstatus.FS, sstatus.FS) pair: the cp_fcsr_access testcases if the pair is in
    _H_ACCESS_FS_PAIRS, and the representative cp_vsstatus_FS_transition instructions.
    """
    regs = _get_fcsr_regs(test_data)
    lines = [_access_banner(priv), *_access_setup(regs)]
    for fs, hs in _H_ACCESS_FS_PAIRS:
        lines.extend(_gen_fcsr_access(test_data, priv, covergroup, regs, fs, hs))
    lines.append(_transition_banner(priv))
    # The fp register loads need vsstatus.FS and sstatus.FS not Off, which the access testcases leave behind.
    lines.extend(set_status_fields(regs.temp, priv, fs=3))
    lines.extend(_transition_setup(test_data, priv, regs))
    for fs, hs in itertools.product(range(4), hs_status_values(priv)):
        lines.extend(_gen_fs_transition(test_data, priv, covergroup, regs, fs, hs, representative=True))
    _return_fcsr_regs(test_data, regs)
    return lines
