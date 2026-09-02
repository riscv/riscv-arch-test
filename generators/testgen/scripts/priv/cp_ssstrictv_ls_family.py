"""Batch generator for SsstrictV LS-encoding reserved coverpoints.

Covers the high-impact load/store reserved-encoding families:

- ``cp_ssstrictv_ls_emul_16`` — (EEW/SEW)*LMUL == 16 reserved
- ``cp_ssstrictv_ls_emul_f16`` — EMUL == 1/16 reserved
- ``cp_ssstrictv_ls_emul_nfields_16`` — segment LS with NF*LMUL == 16
- ``cp_ssstrictv_ls_seg_vd_overflow`` — segment LS with vd+NF > 32 at LMUL=1
- ``cp_ssstrictv_ls_seg_vd_overflow_emulgt1`` — segment LS with vd+NF*LMUL > 32
- ``cp_ssstrictv_ls_eew_lt_sewmin`` - EEW in the width field is less than min supported eew

Encoding-bit families (``ls_mew_reserved``, ``ls_wr_nf_reserved``) require
``.insn`` raw encoding because the assembler does not accept the relevant
field overrides. Those are not implemented here.
"""

from __future__ import annotations

from random import seed as set_seed

import vector_testgen_common as common
from priv_coverpoint_registry import register
from ._ssstrictv_helpers import (build_testline, init_operand_regs, sig_params,
                                  SKIP_COVERPOINTS, override_registers)


def _emit_vsetvli_str(scratch: int, vl: int, sew: int, lmul_flag: str) -> None:
    """Emit ``vsetivli`` with an arbitrary LMUL flag string (supports ``mf*``)."""
    common.writeLine(
        f"vsetivli x{scratch}, {vl}, e{sew}, {lmul_flag}, tu, mu",
        f"# vill=0, vstart=0, vl={vl}, sew={sew}, lmul={lmul_flag}",
    )


def _ls_test(instruction: str, cp: str, sew: int, lmul_flag: str, *,
             vl: int = 1,
             vstart: int | None = None,
             override_vd: int | None = None,
             addr_offset: int = 0,
             if_guard: str = "") -> None:
    """Run one LS test with the given vsetivli + optional address offset."""
    set_seed(common.myhash(instruction + cp + lmul_flag + str(addr_offset) + str(override_vd)))

    eff_sew = sew if isinstance(sew, int) else 64

    instruction_data = common.randomizeVectorInstructionData(
        instruction, eff_sew, common.getBaseSuiteTestCount(),
        vd_val_pointer="vector_random",
        vs2_val_pointer="vector_random",
        vs1_val_pointer="vector_random",
    )
    common.remapPrivScalarRegs(instruction_data, instruction)

    if if_guard != "":
        common.writeLine(f"\n#if {if_guard}")
        common.tab_count += 1
    else:
        common.writeLine("\n")

    common.writeLine(f"# Testcase {cp} (sew={sew}, lmul={lmul_flag}, vd_off={override_vd}, addr_off={addr_offset})")
    scratch = common.pickPrivScratch(instruction_data[1])

    _emit_vsetvli_str(scratch, vl=vl, sew=sew, lmul_flag=lmul_flag)
    init_operand_regs(instruction, instruction_data[0], sew, scratch, regs=("vs2", "vs3"))
    _emit_vsetvli_str(scratch, vl=vl, sew=sew, lmul_flag=lmul_flag)

    if addr_offset:
        rs1_reg = instruction_data[1]["rs1"]["reg"]
    addr_label = "random_mask_0"

    overrides: dict = {}
    if override_vd is not None:
        overrides["override_vd"] = override_vd
        overrides["override_vs3"] = override_vd
    override_registers(instruction_data, **overrides)

    testline, vd, rd = build_testline(instruction, instruction_data, addr_label=addr_label)

    if addr_offset:
        common.writeLine(f"addi x{rs1_reg}, x{rs1_reg}, {addr_offset}",
                          f"# misalign rs1 by {addr_offset} bytes")

    if vstart is not None:
        common.writeLine(f"LI (x{scratch}, {vstart})")
        common.writeLine(f"csrw vstart, x{scratch}", f"# Set vstart={vstart}")

    sig_lmul = 1
    sig_wr = True
    common.add_testcase_string(cp, instruction)
    common.writeVecTest(
        instruction, cp, vd, sew, testline,
        test=instruction, rd=rd, vl=vl, lmul=1,
        sig_lmul=sig_lmul, sig_whole_register_store=sig_wr,
        priv=True, skip_sigupd=True,
    )

    if if_guard != "":
        common.tab_count -= 1
        common.writeLine("#endif")


def _is_segment_ls(instruction: str) -> bool:
    return common.getInstructionSegments(instruction) > 1


def _eew(instruction: str) -> int:
    return common.getInstructionEEW(instruction) or 8


# ---------------- ls_emul_16 ----------------

_EMUL16_PAIRS = [
    ("m8", 8), ("m4", 8), ("m8", 16),
    ("m2", 8), ("m4", 16), ("m8", 32),
]


@register("cp_ssstrictv_ls_emul_16")
def make_emul_16(instruction: str) -> None:
    if "cp_ssstrictv_ls_emul_16" in SKIP_COVERPOINTS:
        return
    if instruction not in common.vector_ls_ins:
        return
    if instruction in common.whole_register_ls or instruction in common.whole_register_move:
        return
    if _is_segment_ls(instruction):
        return
    eew = _eew(instruction)
    for lmul_flag, sew in _EMUL16_PAIRS:
        ratio = eew / sew
        lmul_val = {"m1": 1, "m2": 2, "m4": 4, "m8": 8}[lmul_flag]
        if abs(ratio * lmul_val - 16) > 0.01:
            continue
        _ls_test(instruction, "cp_ssstrictv_ls_emul_16",
                  sew=sew, lmul_flag=lmul_flag)


# ---------------- ls_emul_f16 ----------------

_EMULF16_PAIRS = [
    ("mf8", 16), ("mf4", 32), ("mf2", 64),
]


@register("cp_ssstrictv_ls_emul_f16")
def make_emul_f16(instruction: str) -> None:
    if "cp_ssstrictv_ls_emul_f16" in SKIP_COVERPOINTS:
        return
    if instruction not in common.vector_ls_ins:
        return
    if instruction in common.whole_register_ls or instruction in common.whole_register_move:
        return
    if _is_segment_ls(instruction):
        return
    if _eew(instruction) != 8:
        return
    for lmul_flag, sew in _EMULF16_PAIRS:
        _ls_test(instruction, "cp_ssstrictv_ls_emul_f16",
                  sew=sew, lmul_flag=lmul_flag)


# ---------------- ls_emul_nfields_16 ----------------

_NFIELDS_LMUL_PAIRS = [
    ("m8", 2), ("m4", 4), ("m2", 8),
]


@register("cp_ssstrictv_ls_emul_nfields_16")
def make_emul_nfields_16(instruction: str) -> None:
    if instruction not in common.vector_ls_ins:
        return
    nf = common.getInstructionSegments(instruction)
    if nf < 2:
        return
    eew = _eew(instruction)
    for lmul_flag, want_nf in _NFIELDS_LMUL_PAIRS:
        if nf != want_nf:
            continue
        _ls_test(instruction, "cp_ssstrictv_ls_emul_nfields_16",
                  sew=eew, lmul_flag=lmul_flag)


# ---------------- ls_seg_vd_overflow ----------------

_SEG_VD_OVERFLOW = {
    2: 31, 3: 30, 4: 29, 5: 28, 6: 27, 7: 26, 8: 25,
}


@register("cp_ssstrictv_ls_seg_vd_overflow")
def make_seg_vd_overflow(instruction: str) -> None:
    if instruction not in common.vector_ls_ins:
        return
    nf = common.getInstructionSegments(instruction)
    if nf < 2:
        return
    eew = _eew(instruction)
    vd = _SEG_VD_OVERFLOW[nf]
    _ls_test(instruction, "cp_ssstrictv_ls_seg_vd_overflow",
              sew=eew, lmul_flag="m1", override_vd=vd)


# ---------------- ls_seg_vd_overflow_emulgt1 ----------------

_SEG_VD_LMUL_OVERFLOW = [
    ("m2", 2, 30), ("m2", 3, 28), ("m2", 3, 30),
    ("m2", 4, 26), ("m2", 4, 28), ("m2", 4, 30),
    ("m4", 2, 28),
]


@register("cp_ssstrictv_ls_seg_vd_overflow_emulgt1")
def make_seg_vd_overflow_emulgt1(instruction: str) -> None:
    if instruction not in common.vector_ls_ins:
        return
    nf = common.getInstructionSegments(instruction)
    eew = _eew(instruction)
    for lmul_flag, want_nf, vd in _SEG_VD_LMUL_OVERFLOW:
        if nf != want_nf:
            continue
        _ls_test(instruction, "cp_ssstrictv_ls_seg_vd_overflow_emulgt1",
                  sew=eew, lmul_flag=lmul_flag, override_vd=vd)


# ---------------- ls_nf_eew_emul{2,4,8} ----------------
# NF*EMUL > 8 is reserved (per v-st-ext spec). Pick (lmul, sew) such that
# EMUL == EEW/SEW * LMUL == target, with NF satisfying NF*EMUL > 8.

_NF_EEW_LMUL = {
    2: ("m2", 5),  # EMUL=2, NF>=5  → NF*EMUL >= 10
    4: ("m4", 3),  # EMUL=4, NF>=3  → NF*EMUL >= 12
    8: ("m8", 2),  # EMUL=8, NF>=2  → NF*EMUL >= 16
}


def _make_nf_eew(instruction: str, target_emul: int) -> None:
    if instruction not in common.vector_ls_ins:
        return
    if instruction in common.whole_register_ls or instruction in common.whole_register_move:
        return
    nf = common.getInstructionSegments(instruction)
    lmul_flag, min_nf = _NF_EEW_LMUL[target_emul]
    if nf < min_nf:
        return
    eew = _eew(instruction)
    cp = f"cp_ssstrict_ls_nf_eew_emul{target_emul}"
    _ls_test(instruction, cp, sew=eew, lmul_flag=lmul_flag)


@register("cp_ssstrict_ls_nf_eew_emul2")
def make_nf_eew_emul2(instruction: str) -> None:
    _make_nf_eew(instruction, 2)


@register("cp_ssstrict_ls_nf_eew_emul4")
def make_nf_eew_emul4(instruction: str) -> None:
    _make_nf_eew(instruction, 4)


@register("cp_ssstrict_ls_nf_eew_emul8")
def make_nf_eew_emul8(instruction: str) -> None:
    _make_nf_eew(instruction, 8)

@register("cp_ssstrictv_ls_eew_lt_sewmin")
def make_eew_lt_sewmin(instruction: str) -> None:
    # Cover the EEW in the width field being less than SEWMIN
    width_encoded_eew = None
    if instruction in common.eew8_ins:
        width_encoded_eew = 8
    elif instruction in common.eew16_ins:
        width_encoded_eew = 16
    elif instruction in common.eew32_ins:
        width_encoded_eew = 32
    elif instruction in common.eew64_ins:
        width_encoded_eew = 64
    else:
        return

    cp = "cp_ssstrictv_ls_eew_lt_sewmin"
    for possible_sew_min in (8, 16, 32, 64):
        if width_encoded_eew < possible_sew_min:
            _ls_test(instruction, cp, possible_sew_min, "m1", if_guard=f"UDB_SEW_MIN == {possible_sew_min}")
            _ls_test(instruction, cp, possible_sew_min, "m1", vl=0, if_guard=f"UDB_SEW_MIN == {possible_sew_min}")
            _ls_test(instruction, cp, possible_sew_min, "m1", vl=1, vstart=1, if_guard=f"UDB_SEW_MIN == {possible_sew_min}")
