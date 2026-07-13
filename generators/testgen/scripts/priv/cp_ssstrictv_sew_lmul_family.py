"""SsstrictV generators for SEW/LMUL-driven trap coverpoints.

Templates in this group set ``vtype.{vsew,vlmul}`` such that the instruction
encoding becomes reserved (e.g. widening op at SEW=ELEN, narrowing op at
LMUL=8, etc). The instruction itself is the normal mnemonic; only the
pre-state vtype determines the trap.
"""

from __future__ import annotations

import vector_testgen_common as common
from priv_coverpoint_registry import register

from ._ssstrictv_helpers import issue_simple_test, max_legal_lmul


# Maximum supported SEW for "MAX_SEW" coverpoints. RV64 supports SEW64,
# RV32 also supports SEW64 in CVA6/CVW configurations, so use 64 universally.
_MAX_SEW = 64


# ---------------------------------------------------------------------------
# Widening: dest EMUL = 2*LMUL. LMUL=8 -> EMUL=16 (reserved).
# ---------------------------------------------------------------------------

@register("cp_ssstrictv_widening_vd_emul_16")
def widening_vd_emul_16(instruction: str) -> None:
    # LMUL=8 widened to dst EMUL=16 is reserved by definition; emit unconditionally
    # (max_legal_lmul caps at 4 for widening, but that's the whole point of this cross).
    issue_simple_test(instruction, "cp_ssstrictv_widening_vd_emul_16",
                      sew=8, lmul=8, maskval=None,
                      override_vd=0, override_vs1=8, override_vs2=16)


# ---------------------------------------------------------------------------
# Narrowing: source vs2 EMUL = 2*LMUL. LMUL=8 -> EMUL=16 (reserved).
# ---------------------------------------------------------------------------

@register("cp_ssstrictv_narrowing_vs2_emul_16")
def narrowing_vs2_emul_16(instruction: str) -> None:
    if 8 > max_legal_lmul(instruction):
        return
    issue_simple_test(instruction, "cp_ssstrictv_narrowing_vs2_emul_16",
                      sew=8, lmul=8, maskval=None,
                      override_vd=0, override_vs2=16)


# ---------------------------------------------------------------------------
# Widening at SEW=ELEN: dest EEW = 2*SEW > ELEN -> trap.
# Tests use LMUL=1 with vd/vs1/vs2 chosen to avoid overlap traps.
# ---------------------------------------------------------------------------

@register("cp_ssstrictv_widening_vd_sew_eq_elen")
def widening_vd_sew_eq_elen(instruction: str) -> None:
    issue_simple_test(instruction, "cp_ssstrictv_widening_vd_sew_eq_elen",
                      sew=_MAX_SEW, lmul=1, maskval=None,
                      override_vd=8, override_vs1=12, override_vs2=10)


# ---------------------------------------------------------------------------
# Narrowing at SEW=ELEN: source EEW = 2*SEW > ELEN -> trap.
# ---------------------------------------------------------------------------

@register("cp_ssstrictv_narrowing_vs2_sew_eq_elen")
def narrowing_vs2_sew_eq_elen(instruction: str) -> None:
    issue_simple_test(instruction, "cp_ssstrictv_narrowing_vs2_sew_eq_elen",
                      sew=_MAX_SEW, lmul=1, maskval=None,
                      override_vd=8, override_vs1=12, override_vs2=10)


# ---------------------------------------------------------------------------
# Widening at MAX_SEW across LMUL=1,2,4. Same trap reason as above.
# ---------------------------------------------------------------------------

@register("cp_ssstrictv_widen_max_sew")
def widen_max_sew(instruction: str) -> None:
    cp = "cp_ssstrictv_widen_max_sew"
    cap = max_legal_lmul(instruction)
    # Per LMUL pick non-overlapping aligned register groups.
    # LMUL=1: vd=2 regs, vs1/vs2 = 1 reg each. base=8.
    # LMUL=2: vd=4 regs, vs1/vs2 = 2 regs each. base=8.
    # LMUL=4: vd=8 regs, vs1/vs2 = 4 regs each. base=8.
    layout = {
        1: (8, 12, 14),
        2: (8, 16, 20),
        4: (8, 16, 20),
    }
    for lmul in (1, 2, 4):
        if lmul > cap:
            break
        base, vs1_reg, vs2_reg = layout[lmul]
        issue_simple_test(instruction, cp, sew=_MAX_SEW, lmul=lmul,
                          maskval=None, override_vd=base,
                          override_vs1=vs1_reg, override_vs2=vs2_reg)


# ---------------------------------------------------------------------------
# Vector FP: SEW=8 (always FP-unsupported) and SEW=64 (unsupported w/o D).
# We emit one test per SEW; the cross will only sample the bins that exist
# in the current build configuration.
# ---------------------------------------------------------------------------

@register("cp_ssstrictv_vfp_eew_unsupported")
def vfp_eew_unsupported(instruction: str) -> None:
    cp = "cp_ssstrictv_vfp_eew_unsupported"
    for sew in (8, 64):
        try:
            issue_simple_test(instruction, cp, sew=sew, lmul=1, maskval=None,
                              override_vd=4, override_vs1=12, override_vs2=8)
        except Exception:
            # Some FP tests may fail to randomize at SEW=8; ignore.
            pass
        # _vl0 variant: same encoding but with vl=0 in pre-state.
        try:
            issue_simple_test(instruction, cp, sew=sew, lmul=1, vl=0, maskval=None,
                              override_vd=4, override_vs1=12, override_vs2=8)
        except Exception:
            pass
        # _vstart_ge_vl variant: vl=1, vstart=1 -> vstart>=vl true.
        try:
            issue_simple_test(instruction, cp, sew=sew, lmul=1, vl=1, vstart=1,
                              maskval=None, override_vd=4, override_vs1=12,
                              override_vs2=8)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Vector widening FP: SEW=32 widens to 64, unsupported w/o D.
# ---------------------------------------------------------------------------

@register("cp_ssstrictv_vfp_widen_eew_unsupported")
def vfp_widen_eew_unsupported(instruction: str) -> None:
    cp = "cp_ssstrictv_vfp_widen_eew_unsupported"
    issue_simple_test(instruction, cp, sew=32, lmul=1, maskval=None,
                      override_vd=8, override_vs1=12, override_vs2=10)
    # _vl0 variant.
    try:
        issue_simple_test(instruction, cp, sew=32, lmul=1, vl=0, maskval=None,
                          override_vd=8, override_vs1=12, override_vs2=10)
    except Exception:
        pass
    # _vstart_ge_vl variant.
    try:
        issue_simple_test(instruction, cp, sew=32, lmul=1, vl=1, vstart=1,
                          maskval=None, override_vd=8, override_vs1=12,
                          override_vs2=10)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Vector FP with reserved frm (5, 6, 7) -> trap.
# We pre-write the desired frm value into the fcsr field via csrw.
# ---------------------------------------------------------------------------

def _emit_frm_test(instruction: str, cp: str, frm_val: int, *,
                   vl: int = 1, vstart: int | None = None) -> None:
    """Set frm to ``frm_val`` then issue a normal-vtype FP test.

    ``vl`` controls the AVL passed to vsetivli (0 enables _vl0 cross).
    ``vstart`` (if set) is written to the vstart CSR after vsetivli to enable
    the _vstart_ge_vl cross.
    """
    sew = common.getInstructionEEW(instruction) or 32
    if sew not in (16, 32, 64):
        sew = 32
    instruction_data = common.randomizeVectorInstructionData(
        instruction, sew, common.getBaseSuiteTestCount(),
        vd_val_pointer="vector_random",
        vs2_val_pointer="vector_random",
        vs1_val_pointer="vector_random",
    )
    common.remapPrivScalarRegs(instruction_data, instruction)

    suffix = ""
    if vl == 0:
        suffix = " vl=0"
    elif vstart is not None:
        suffix = f" vstart={vstart}"
    common.writeLine(f"\n# Testcase {cp} frm={frm_val}{suffix}")
    scratch = common.pickPrivScratch(instruction_data[1])
    # Set up trap-eligible vtype first.
    common.writeLine(f"vsetivli x{scratch}, {max(vl,1)}, e{sew}, m1, tu, mu",
                     "# trap-eligible vtype")
    # Initialize operand vector regs.
    args = common.getInstructionArguments(instruction)
    common.writeLine(f"la x{scratch}, random_mask_0", "# scratch <- &random_mask_0")
    for r in ("vd", "vs2"):
        if r in args:
            reg = instruction_data[0][r]["reg"]
            common.writeLine(f"vle{sew}.v v{reg}, (x{scratch})", f"# init {r}")
    # Set reserved frm via csrw frm, x.
    common.writeLine(f"li x{scratch}, {frm_val}", f"# reserved frm value {frm_val}")
    common.writeLine(f"csrw frm, x{scratch}", "# install reserved frm")
    # Re-emit vsetivli so SAMPLE_BEFORE captures vtype/vl.
    common.writeLine(f"vsetivli x{scratch}, {vl}, e{sew}, m1, tu, mu",
                     f"# re-emit vtype for SAMPLE_BEFORE (vl={vl})")
    if vstart is not None:
        common.writeLine(f"li x{scratch}, {vstart}", f"# vstart override = {vstart}")
        common.writeLine(f"csrw vstart, x{scratch}", "# install non-zero vstart")

    from ._ssstrictv_helpers import build_testline, sig_params  # local import
    testline, vd, rd = build_testline(instruction, instruction_data, maskval=None)
    sig_lmul, sig_wr = sig_params(instruction, instruction_data, lmul=1)

    common.add_testcase_string(cp, instruction)
    # Restore frm to 0 after the (possibly trapping) test so subsequent FP
    # CSR access is sane.
    post = [f"csrwi frm, 0  # restore frm"]
    common.writeVecTest(
        instruction, cp, vd, sew, testline,
        test=instruction, rd=rd, vl=max(vl, 1), lmul=1,
        sig_lmul=sig_lmul, sig_whole_register_store=sig_wr,
        priv=True, skip_sigupd=True,
        post_instruction_lines=post,
    )


@register("cp_ssstrictv_vfp_frm_reserved")
def vfp_frm_reserved(instruction: str) -> None:
    cp = "cp_ssstrictv_vfp_frm_reserved"
    for frm_val in (5, 6, 7):
        try:
            _emit_frm_test(instruction, cp, frm_val)
        except Exception:
            pass
        # _vl0 variant
        try:
            _emit_frm_test(instruction, cp, frm_val, vl=0)
        except Exception:
            pass
        # _vstart_ge_vl variant: vl=1, vstart=1
        try:
            _emit_frm_test(instruction, cp, frm_val, vl=1, vstart=1)
        except Exception:
            pass
