"""Shared helpers for SsstrictV priv coverpoint generators.

These coverpoints are typically of the form:
    cross std_trap_vec, vtype_<lmul>, <encoding-bit-coverpoint> [, ...];

where ``std_trap_vec`` requires the standard "trap-eligible" pre-state
(``vill=0``, ``vstart=0``, ``vl != 0``, ``mstatus.vs != 0``). The encoding
coverpoints usually fix one or more bits of the instruction word
(``insn[11:7]`` = vd, ``insn[24:20]`` = vs2, ``insn[19:15]`` = vs1,
``insn[25]`` = vm, etc).

Most SsstrictV coverpoints are *reserved encoding* tests: the instruction is
illegal under the spec so it traps. We rely on the same trap-handler signature
that ExceptionsV uses (``priv=True``, ``skip_sigupd=True``) — the fact the
trap was taken is what proves the coverpoint hit on cross-model comparison.
A handful of crosses additionally require ``trap_occurred`` (mcause==2) so
the test must actually take an illegal-instruction trap.
"""

from __future__ import annotations

from random import seed as set_seed
from typing import Iterable

import vector_testgen_common as common


_LMUL_FLAG = {1: "m1", 2: "m2", 4: "m4", 8: "m8",
              "mf2": "mf2", "mf4": "mf4", "mf8": "mf8"}


def lmul_flag(lmul) -> str:
    """Return the LMUL field string for ``vsetivli`` (e.g. ``"m2"``, ``"mf4"``)."""
    return _LMUL_FLAG[lmul]


# Coverpoints that are unreachable on the Sail simulator due to documented
# simulator behaviour that doesn't violate the spec (see ../../../../simulator-issues/).
# Generators consult this set and early-return so the test corpus stays clean.
#
# POLICY: an entry here MUST cite a numbered file under simulator-issues/
# describing a direct sail-vs-spec contradiction (e.g. sail asserts/crashes on
# an encoding the spec defines as illegal-instruction). Coverpoint
# over-constraints (requiring a trap to occur) are fixed in the template, not
# skipped here.
SKIP_COVERPOINTS: frozenset[str] = frozenset({
    # Issue 006: Sail asserts on EMUL out of [1/8, 8] before reserved-encoding check
    "cp_ssstrictv_ls_emul_16",
    "cp_ssstrictv_ls_emul_f16",
})


def max_legal_lmul(instruction: str) -> int:
    """Return the largest legal LMUL for ``instruction`` (≤ 8).

    For segment LS, ``NF * EMUL ≤ 8`` is required, so EMUL ≤ 8/NF.
    For widening / narrowing ops, vd or vs2 has EEW = 2*SEW so EMUL = 2*LMUL,
    capping LMUL at 4. For non-segment, non-widening ops, the cap is 8.
    """
    nf = common.getInstructionSegments(instruction)
    if nf > 1:
        cap = 8 // nf
        # Round down to nearest power-of-two ≥ 1.
        for m in (8, 4, 2, 1):
            if m <= cap:
                return m
        return 1
    if instruction in common.vd_widen_ins or instruction in common.vs2_widen_ins:
        return 4
    return 8


def emit_vsetivli(scratch: int, vl: int, sew: int, lmul: int = 1, *, ta: str = "tu", ma: str = "mu") -> None:
    """Emit a ``vsetivli`` that yields ``vill=0, vstart=0, vl=<vl>``."""
    common.writeLine(f"vsetivli x{scratch}, {vl}, e{sew}, {lmul_flag(lmul)}, {ta}, {ma}",
                     f"# vill=0, vstart=0, vl={vl}, sew={sew}, lmul={lmul_flag(lmul)}")


def emit_init_vec(scratch: int, vreg: int, sew: int, *, label: str = "random_mask_0") -> None:
    """Initialize a single architectural vector register with a known pattern."""
    common.writeLine(f"la x{scratch}, {label}", f"# scratch <- &{label}")
    common.writeLine(f"vle{sew}.v v{vreg}, (x{scratch})", f"# init v{vreg}")


def init_operand_regs(instruction: str, vec_data: dict, sew: int, scratch: int,
                       *, regs: Iterable[str] = ("vd", "vs2", "vs3"),
                       label: str = "random_mask_0") -> None:
    """Initialize operand vector registers that exist in the instruction's signature."""
    args = common.getInstructionArguments(instruction)
    common.writeLine(f"la x{scratch}, {label}", f"# scratch <- &{label}")
    for r in regs:
        if r in args and r in vec_data:
            reg = vec_data[r]["reg"]
            common.writeLine(f"vle{sew}.v v{reg}, (x{scratch})", f"# init {r} (v{reg})")


def build_testline(instruction: str, instruction_data: list, *,
                   maskval: str | None = None,
                   override_vd: int | None = None,
                   override_vs1: int | None = None,
                   override_vs2: int | None = None,
                   override_vs3: int | None = None,
                   override_rs1: int | None = None,
                   override_rs2: int | None = None,
                   override_rd: int | None = None,
                   override_imm: int | None = None,
                   addr_label: str = "random_mask_0") -> tuple[str, int, int]:
    """Build the assembly mnemonic line. Returns (testline, vd_reg, rd_reg)."""
    args = common.getInstructionArguments(instruction)
    vec_data, scalar_data, fp_data, imm_val = instruction_data

    if override_vd is not None:
        vec_data["vd"]["reg"] = override_vd
    if override_vs1 is not None and "vs1" in vec_data:
        vec_data["vs1"]["reg"] = override_vs1
    if override_vs2 is not None and "vs2" in vec_data:
        vec_data["vs2"]["reg"] = override_vs2
    if override_vs3 is not None and "vs3" in vec_data:
        vec_data["vs3"]["reg"] = override_vs3
    if override_rs1 is not None and "rs1" in scalar_data:
        scalar_data["rs1"]["reg"] = override_rs1
    if override_rs2 is not None and "rs2" in scalar_data:
        scalar_data["rs2"]["reg"] = override_rs2
    if override_rd is not None and "rd" in scalar_data:
        scalar_data["rd"]["reg"] = override_rd
    if override_imm is not None:
        imm_val = override_imm

    testline = instruction + " "
    for arg in args:
        if arg == "vm":
            if maskval is not None:
                testline += "v0.t"
            else:
                testline = testline[:-2]
        elif arg == "v0":
            testline += "v0"
        elif arg == "imm":
            testline += f"{imm_val}"
        elif arg[0] == "v":
            testline += f"v{vec_data[arg]['reg']}"
        elif arg[0] == "r":
            reg = scalar_data[arg]["reg"]
            if arg == "rs1" and instruction in common.vector_ls_ins:
                common.writeLine(f"la x{reg}, {addr_label}", "# rs1 = valid memory address")
                testline += f"(x{reg})"
            else:
                # Skip loadScalarReg for framework-reserved regs (ra/sp/gp/tp/t0)
                # which off_group overrides may target. Their values come from
                # the framework setup and are never randomized; the trap path
                # doesn't care about the actual value, only the field bits.
                if reg not in common.PRIV_RESERVED_SCALAR_REGS:
                    common.loadScalarReg(arg, scalar_data)
                testline += f"x{reg}"
        elif arg[0] == "f":
            testline += f"f{fp_data[arg]['reg']}"
        else:
            raise TypeError(f"Unsupported argument type: '{arg}'")
        testline += ", "

    testline = testline[:-2]
    vd = vec_data["vd"]["reg"]
    rd = scalar_data["rd"]["reg"]
    return testline, vd, rd


def sig_params(instruction: str, instruction_data: list, lmul: int = 1) -> tuple[int, bool]:
    """Determine sig_lmul and sig_whole_register_store for writeVecTest."""
    vec_data = instruction_data[0]
    sig_lmul = lmul if isinstance(lmul, int) else 1
    if vec_data["vd"]["reg_type"] in ("mask", "scalar"):
        return 1, True
    if instruction in common.whole_register_move:
        return common.getLengthLmul(instruction), True
    return sig_lmul, False


def dest_field_role(instruction: str) -> str:
    """Return which operand-name occupies the destination encoding bits[11:7].

    For most vector ops, this is "vd". For unit/strided/indexed stores the
    field holds vs3. For mask/scalar reductions (vcpop.m, vfirst.m, vmv.x.s,
    vfmv.f.s) it holds rd/fd.
    """
    args = common.getInstructionArguments(instruction)
    if "vd" in args:
        return "vd"
    if "vs3" in args:
        return "vs3"
    if "rd" in args:
        return "rd"
    if "fd" in args:
        return "fd"
    return "vd"


def make_dest_zero_overrides(instruction: str) -> dict:
    """Return ``override_*`` kwargs that force the destination encoding to 0.

    Useful for masking_vd_eq_v0-style coverpoints which sample insn[11:7]==0.
    """
    role = dest_field_role(instruction)
    if role == "vd":
        return {"override_vd": 0}
    if role == "vs3":
        return {"override_vs3": 0}
    if role == "rd":
        return {"override_rd": 0}
    return {}


def issue_simple_test(instruction: str, cp: str, *,
                       sew: int | None = None, lmul: int = 1, vl: int = 1,
                       vstart: int | None = None,
                       maskval: str | None = "v0.t",
                       override_vd: int | None = None,
                       override_vs1: int | None = None,
                       override_vs2: int | None = None,
                       override_vs3: int | None = None,
                       override_rd: int | None = None,
                       override_imm: int | None = None,
                       init_regs: Iterable[str] = ("vd", "vs2", "vs3"),
                       skip_sigupd: bool = True) -> None:
    """One-shot generator for "set up trap-eligible state + execute one encoding".

    Used by the simple reserved-encoding coverpoints that just require fixed
    bits in the instruction word under standard trap-eligible conditions.
    """
    set_seed(common.myhash(instruction + cp))

    if sew is None:
        eew = common.getInstructionEEW(instruction) or common.minSEW_MIN
        sew = eew

    instruction_data = common.randomizeVectorInstructionData(
        instruction, sew, common.getBaseSuiteTestCount(),
        vd_val_pointer="vector_random",
        vs2_val_pointer="vector_random",
        vs1_val_pointer="vector_random",
    )
    common.remapPrivScalarRegs(instruction_data, instruction)

    common.writeLine(f"\n# Testcase {cp}")
    scratch = common.pickPrivScratch(instruction_data[1])
    emit_vsetivli(scratch, vl=vl, sew=sew, lmul=lmul)
    init_operand_regs(instruction, instruction_data[0], sew, scratch, regs=init_regs)
    # Re-emit vsetivli RIGHT BEFORE the test so the previous-instruction CSR
    # snapshot used by SAMPLE_BEFORE includes vtype/vl/vstart. The intervening
    # vle*.v ops do not write those CSRs, and the rvvi shim does not carry
    # forward unchanged CSR values (see simulator-issues/005).
    emit_vsetivli(scratch, vl=vl, sew=sew, lmul=lmul)
    if vstart is not None:
        common.writeLine(f"li x{scratch}, {vstart}", f"# vstart override = {vstart}")
        common.writeLine(f"csrw vstart, x{scratch}", "# install non-zero vstart")

    testline, vd, rd = build_testline(
        instruction, instruction_data, maskval=maskval,
        override_vd=override_vd, override_vs1=override_vs1,
        override_vs2=override_vs2, override_vs3=override_vs3,
        override_rd=override_rd, override_imm=override_imm,
    )
    sig_lmul, sig_wr = sig_params(instruction, instruction_data, lmul=lmul)
    write_lmul = lmul if isinstance(lmul, int) else 1

    common.add_testcase_string(cp, instruction)
    common.writeVecTest(
        instruction, cp, vd, sew, testline,
        test=instruction, rd=rd, vl=vl, lmul=write_lmul,
        sig_lmul=sig_lmul, sig_whole_register_store=sig_wr,
        priv=True, skip_sigupd=skip_sigupd,
    )
