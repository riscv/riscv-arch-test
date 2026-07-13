"""cp_ssstrictv_lmulgt1_off_group: register fields not aligned to LMUL>1 group.

For each LMUL ∈ {2, 4, 8} and each role ∈ {vd, vs1, vs2}, emit a test where the
given role's register field is not divisible by LMUL. The 9 sub-coverpoints
share ``std_trap_vec, vtype_lmul_<L>`` and the corresponding ``<role>_all_reg_unaligned_lmul_<L>``.
"""

from __future__ import annotations

from random import randint, seed as set_seed

import vector_testgen_common as common
from priv_coverpoint_registry import register
from ._ssstrictv_helpers import (build_testline, emit_vsetivli, init_operand_regs,
                                 max_legal_lmul, sig_params)

CP = "cp_ssstrictv_lmulgt1_off_group"


def _sample_unaligned_for_lmul(lmul: int) -> list[int]:
    """All register indices not divisible by ``lmul``.

    Each ``<role>_all_reg_unaligned_lmul_<L>`` cross has one bin per unaligned
    register index (16 bins for L=2, 24 for L=4, 28 for L=8). To reach 100%
    coverage we need to fire every unaligned reg. The SsstrictV ELF now uses
    test-suite splitting (see split_priv) so the ±1MiB JAL range is not a
    blocker.
    """
    return [r for r in range(1, 32) if r % lmul != 0]


def _emit_one(instruction: str, lmul: int, role: str, off_reg: int, sew: int) -> None:
    instruction_data = common.randomizeVectorInstructionData(
        instruction, sew, common.getBaseSuiteTestCount(),
        vd_val_pointer="vector_random",
        vs2_val_pointer="vector_random",
        vs1_val_pointer="vector_random",
    )
    common.remapPrivScalarRegs(instruction_data, instruction)

    # Force NON-target vector operands to be aligned multiples of LMUL so the
    # simulator's reserved-encoding check fires on the targeted bits, not on
    # an unrelated unaligned-EMUL assertion (Sail asserts before raising the
    # illegal-instruction trap — see simulator-issues/006/007).
    vec_data = instruction_data[0]
    args = common.getInstructionArguments(instruction)
    # For widening / narrowing ops one operand has EMUL = 2*lmul; aligning all
    # non-target operands to 2*lmul is the safe lower bound.
    align = lmul
    if instruction in common.vd_widen_ins or instruction in common.vs2_widen_ins:
        align = lmul * 2
    aligned_pool = [r for r in range(align, 32, align) if r != off_reg]

    def _align(name: str, exclude: set[int]) -> int:
        cands = [r for r in aligned_pool if r not in exclude]
        return cands[0] if cands else align

    used: set[int] = {0, off_reg}
    for op in ("vd", "vs1", "vs2", "vs3"):
        if op in vec_data and op in args and op != role:
            new = _align(op, used)
            vec_data[op]["reg"] = new
            used.add(new)

    common.writeLine(f"\n# Testcase {CP} (lmul={lmul}, sew={sew}, off_role={role}, reg=v{off_reg})")
    scratch = common.pickPrivScratch(instruction_data[1])
    emit_vsetivli(scratch, vl=1, sew=sew, lmul=lmul)
    init_operand_regs(instruction, instruction_data[0], sew, scratch)
    # Re-emit vsetivli right before the test so SAMPLE_BEFORE sees vtype/vl/vstart
    # (rvvi shim does not carry forward unchanged CSRs — simulator-issues/005).
    emit_vsetivli(scratch, vl=1, sew=sew, lmul=lmul)

    overrides: dict[str, int] = {}
    if role == "vd":
        overrides["override_vd"] = off_reg
        overrides["override_vs3"] = off_reg
    elif role == "vs1":
        # vs1 field bits hold rs1 (vx-form), imm5 (vi-form), or vs1 (vv-form).
        # vec_data may contain "vs1" even when args don't use it (e.g. vaadd.vx
        # has vs1 in vec_data but never in args), so check args directly.
        args = common.getInstructionArguments(instruction)
        if "vs1" in args:
            overrides["override_vs1"] = off_reg
        elif "rs1" in args and instruction not in common.vector_ls_ins:
            overrides["override_rs1"] = off_reg
        elif "imm" in args:
            # vi-form: imm5 sits in inst[19:15]; values 0..31 directly map to
            # the unaligned register check. Some viop's use unsigned imm5
            # (shifts, slides, gather, narrow-clip) — keep raw 0..31. For
            # signed-imm ops (vadd.vi etc.) map 16..31 to two's-complement.
            if instruction in common.imm_31:
                overrides["override_imm"] = off_reg
            else:
                overrides["override_imm"] = off_reg if off_reg < 16 else off_reg - 32
    elif role == "vs2":
        args = common.getInstructionArguments(instruction)
        if "vs2" in args:
            overrides["override_vs2"] = off_reg
        elif "rs2" in args:
            overrides["override_rs2"] = off_reg

    testline, vd, rd = build_testline(instruction, instruction_data, **overrides)
    sig_lmul, sig_wr = sig_params(instruction, instruction_data, lmul=lmul)

    common.add_testcase_string(CP, instruction)
    common.writeVecTest(
        instruction, CP, vd, sew, testline,
        test=instruction, rd=rd, vl=1, lmul=lmul,
        sig_lmul=sig_lmul, sig_whole_register_store=sig_wr,
        priv=True, skip_sigupd=True,
    )


def _emit_vill_test(instruction: str) -> None:
    """Emit one trap-eligible test where vtype.vill==1 is set right before.

    Mirrors the ``make_vill`` helper used for unpriv test generation. Sets
    vill=1 via ``vsetivli x0, 1, e64, mf8, tu, mu`` (illegal SEW/LMUL combo)
    and immediately issues the test instruction. The trap that follows is
    irrelevant to coverage — what matters is that ``vtype_prev_vill_set``
    samples vtype.vill==1 before the instruction.
    """
    set_seed(common.myhash(instruction + CP + "_vill"))
    sew = common.getInstructionEEW(instruction) or common.minSEW_MIN

    instruction_data = common.randomizeVectorInstructionData(
        instruction, sew, common.getBaseSuiteTestCount(),
        vd_val_pointer="vector_random",
        vs2_val_pointer="vector_random",
        vs1_val_pointer="vector_random",
    )
    common.remapPrivScalarRegs(instruction_data, instruction)

    common.writeLine(f"\n# Testcase {CP} (vill=1 side-effect)")
    scratch = common.pickPrivScratch(instruction_data[1])
    # Initialize operand vector regs first (while vtype is still legal).
    emit_vsetivli(scratch, vl=1, sew=sew, lmul=1)
    init_operand_regs(instruction, instruction_data[0], sew, scratch)
    # Now set vill=1 — illegal SEW=64 / LMUL=1/8 combo.
    common.writeLine(f"vsetivli x{scratch}, 1, e64, mf8, tu, mu",
                      "# vill=1 (illegal SEW=64, LMUL=1/8)")

    testline, vd, rd = build_testline(instruction, instruction_data)
    sig_lmul, sig_wr = sig_params(instruction, instruction_data, lmul=1)
    common.add_testcase_string(CP, instruction)
    common.writeVecTest(
        instruction, CP, vd, sew, testline,
        test=instruction, rd=rd, vl=1, lmul=1,
        sig_lmul=sig_lmul, sig_whole_register_store=sig_wr,
        priv=True, skip_sigupd=True,
    )


@register(CP)
def make(instruction: str) -> None:
    from ._ssstrictv_helpers import SKIP_COVERPOINTS
    if CP in SKIP_COVERPOINTS:
        return
    # Issue 007: Sail asserts on unaligned register groups for reduction
    # instructions (vred*.vs / vfred*.vs / vwred*.vs) BEFORE raising the
    # SsstrictV illegal-instruction trap, aborting the entire test file
    # and losing coverage for sibling instructions in the same chunk. Skip
    # off_group emission for reductions only — they keep the bins ZERO but
    # let everything else in the same .S file collect coverage.
    if instruction in common.vredins or instruction == "vrgatherei16.vv":
        return
    set_seed(common.myhash(instruction + CP))
    args = common.getInstructionArguments(instruction)
    # Whole-register loads/stores ignore vtype.LMUL but the cross still
    # samples vtype.LMUL via vtype_lmul_*; allow LMUL up to 8 for those.
    if instruction in common.whole_register_ls or instruction in common.whole_register_move:
        cap = 8
    else:
        cap = max_legal_lmul(instruction)

    # Side-effect: one vill-set test per instruction. The
    # ``vtype_prev_vill_set`` coverpoint (auto-included into every
    # SsstrictV covergroup via the standard helper) only fires when
    # vtype.vill==1 right before the test instruction, which the
    # standard make_vill path is not invoked for SsstrictV. Emit one
    # such test here so the bin fires across all 624 covergroups.
    _emit_vill_test(instruction)

    # SEW round-robin: rotate {8,16,32,64} across (lmul,role,off_reg) tuples
    # so vtype_all_sew_supported (sixteen/thirtytwo/sixtyfour bins) fires
    # in every CG without inflating the test count.
    base_sew = common.getInstructionEEW(instruction)
    if base_sew is not None:
        sews = [base_sew]
    else:
        sews = [8, 16, 32, 64]
    sidx = 0

    for lmul in (2, 4, 8):
        if lmul > cap:
            break
        for role in ("vd", "vs1", "vs2"):
            for off_reg in _sample_unaligned_for_lmul(lmul):
                _emit_one(instruction, lmul, role, off_reg, sews[sidx % len(sews)])
                sidx += 1
