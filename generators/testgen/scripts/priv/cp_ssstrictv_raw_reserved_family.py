"""Raw .4byte reserved-encoding generators for SsstrictV.

These generators emit instruction encodings the GAS assembler refuses (vd=v0,
vm=1 on .vvm forms, vs2!=v0 on vmv.v.v, mew=1 on vector LS, mask-logical
masked, etc.). The bit-fiddling helpers live in ``_raw_encoding``; this file
just maps each coverpoint to the bits-to-flip.

Every generator:

  - Sets the standard trap-eligible state (``vill=0, vstart=0, vl!=0,
    mstatus.vs!=0``) via vsetivli.
  - Computes a reserved encoding from the base instruction word.
  - Emits the instruction as ``.4byte 0x...`` (SsstrictV doesn't care what the
    processor does after — the coverpoint only requires the encoding bits).
"""

from __future__ import annotations

import vector_testgen_common as common
from priv_coverpoint_registry import register

from ._raw_encoding import (encode, emit_raw_test, with_vd, with_vs1,
                             with_vs2, with_rs1, with_vm, with_mew, with_nf)
from ._ssstrictv_helpers import SKIP_COVERPOINTS


# --------------------------------------------------------------------------
# vadc/vsbc with vm=1 (reserved): "no mask" encoding on instructions that
# require the mask.
# --------------------------------------------------------------------------

@register("cp_ssstrictv_vadc_vsbc_vm1_reserved")
def vadc_vsbc_vm1(instruction: str) -> None:
    base = encode(instruction)
    if base is None:
        return
    # Pick distinct vd/vs2 (and vs1 for vvm) avoiding v0 to prove vm=1 is what
    # makes it reserved (not some other constraint).
    enc = with_vd(base, 8)
    enc = with_vs2(enc, 16)
    if instruction.endswith(".vvm"):
        enc = with_vs1(enc, 24)
    elif instruction.endswith(".vxm"):
        enc = with_rs1(enc, 1)  # any GPR
    elif instruction.endswith(".vim"):
        enc = with_rs1(enc, 5)  # imm5=5 (placeholder)
    enc = with_vm(enc, 1)  # the reserved bit
    sew = common.getInstructionEEW(instruction) or 8
    emit_raw_test(instruction, "cp_ssstrictv_vadc_vsbc_vm1_reserved", enc,
                  sew=sew, init_vregs=(8, 16) + ((24,) if instruction.endswith(".vvm") else ()))


# --------------------------------------------------------------------------
# vadc/vsbc with vd=v0 (reserved).
# --------------------------------------------------------------------------

@register("cp_ssstrictv_vadc_vsbc_vd_v0_reserved")
def vadc_vsbc_vd_v0(instruction: str) -> None:
    base = encode(instruction)
    if base is None:
        return
    # vm=0 (masked, .vvm/.vxm/.vim require it) but vd=v0.
    enc = with_vd(base, 0)
    enc = with_vs2(enc, 16)
    if instruction.endswith(".vvm"):
        enc = with_vs1(enc, 24)
    elif instruction.endswith(".vxm"):
        enc = with_rs1(enc, 1)
    elif instruction.endswith(".vim"):
        enc = with_rs1(enc, 5)
    sew = common.getInstructionEEW(instruction) or 8
    emit_raw_test(instruction, "cp_ssstrictv_vadc_vsbc_vd_v0_reserved", enc,
                  sew=sew, init_vregs=(16,) + ((24,) if instruction.endswith(".vvm") else ()))


# --------------------------------------------------------------------------
# Mask logical (vmand/vmnand/...) with vm=0 (reserved).
# --------------------------------------------------------------------------

_MASK_LOGICAL = {"vmand.mm", "vmnand.mm", "vmandn.mm", "vmxor.mm", "vmor.mm",
                 "vmnor.mm", "vmorn.mm", "vmxnor.mm"}


@register("cp_ssstrictv_mask_logical_vm0_reserved")
def mask_logical_vm0(instruction: str) -> None:
    if instruction not in _MASK_LOGICAL:
        return
    base = encode(instruction)
    if base is None:
        return
    enc = with_vd(base, 8)
    enc = with_vs2(enc, 16)
    enc = with_vs1(enc, 24)
    enc = with_vm(enc, 0)  # reserved: mask-logical insns must be unmasked (vm=1)
    emit_raw_test(instruction, "cp_ssstrictv_mask_logical_vm0_reserved", enc,
                  sew=8, init_vregs=(8, 16, 24))


# --------------------------------------------------------------------------
# vmv.v.* / vfmv.v.f / vid.v with vs2 != v0 (reserved).
# --------------------------------------------------------------------------

@register("cp_ssstrictv_vmv_vs2_not_v0_reserved")
def vmv_vs2_not_v0(instruction: str) -> None:
    base = encode(instruction)
    if base is None:
        return
    # Enumerate vs2 = 1..31 to cover every reserved vs2 bin in the cg.
    for vs2 in range(1, 32):
        enc = with_vd(base, 0)
        enc = with_vs2(enc, vs2)
        if instruction == "vmv.v.v":
            enc = with_vs1(enc, 24)
        elif instruction == "vmv.v.x":
            enc = with_rs1(enc, 1)
        elif instruction == "vmv.v.i":
            enc = with_rs1(enc, 5)
        emit_raw_test(instruction, "cp_ssstrictv_vmv_vs2_not_v0_reserved", enc,
                      sew=8,
                      init_vregs=(vs2,) + ((24,) if instruction == "vmv.v.v" else ()),
                      comment=f"vs2={vs2}")


@register("cp_ssstrictv_vfmv_vs2_not_v0_reserved")
def vfmv_vs2_not_v0(instruction: str) -> None:
    if instruction != "vfmv.v.f":
        return
    base = encode(instruction)
    if base is None:
        return
    for vs2 in range(1, 32):
        enc = with_vd(base, 0)
        enc = with_vs2(enc, vs2)
        enc = with_rs1(enc, 1)  # rs1 field holds fs1 (FP src). Use f1.
        emit_raw_test(instruction, "cp_ssstrictv_vfmv_vs2_not_v0_reserved", enc,
                      sew=32, init_vregs=(vs2,), comment=f"vs2={vs2}")


@register("cp_ssstrictv_vid_vs2_not_v0_reserved")
def vid_vs2_not_v0(instruction: str) -> None:
    if instruction != "vid.v":
        return
    base = encode(instruction)
    if base is None:
        return
    for vs2 in range(1, 32):
        enc = with_vd(base, 0)
        enc = with_vs2(enc, vs2)  # reserved
        enc = with_vm(enc, 1)     # vid.v is unmasked-by-default; keep vm=1
        emit_raw_test(instruction, "cp_ssstrictv_vid_vs2_not_v0_reserved", enc,
                      sew=8, init_vregs=(vs2,), comment=f"vs2={vs2}")


# --------------------------------------------------------------------------
# vmv.x.s / vmv.s.x / vfmv.f.s / vfmv.s.f with vm=0 (reserved).
# --------------------------------------------------------------------------

_VMV_XS_SX = {"vmv.x.s", "vmv.s.x"}
_VFMV_FS_SF = {"vfmv.f.s", "vfmv.s.f"}


@register("cp_ssstrictv_vmv_xs_sx_vm0_reserved")
def vmv_xs_sx_vm0(instruction: str) -> None:
    if instruction not in _VMV_XS_SX:
        return
    base = encode(instruction)
    if base is None:
        return
    enc = with_vd(base, 8)
    enc = with_vs2(enc, 16)
    enc = with_rs1(enc, 1)
    enc = with_vm(enc, 0)  # reserved (must be 1)
    emit_raw_test(instruction, "cp_ssstrictv_vmv_xs_sx_vm0_reserved", enc,
                  sew=8, init_vregs=(16,))


@register("cp_ssstrictv_vfmv_fs_sf_vm0_reserved")
def vfmv_fs_sf_vm0(instruction: str) -> None:
    if instruction not in _VFMV_FS_SF:
        return
    base = encode(instruction)
    if base is None:
        return
    enc = with_vd(base, 8)
    enc = with_vs2(enc, 16)
    enc = with_rs1(enc, 1)
    enc = with_vm(enc, 0)  # reserved
    emit_raw_test(instruction, "cp_ssstrictv_vfmv_fs_sf_vm0_reserved", enc,
                  sew=32, init_vregs=(16,))


# --------------------------------------------------------------------------
# vcompress.vm with vm=0 (reserved).
# --------------------------------------------------------------------------

@register("cp_ssstrictv_vcompress_vm0_reserved")
def vcompress_vm0(instruction: str) -> None:
    if instruction != "vcompress.vm":
        return
    base = encode(instruction)
    if base is None:
        return
    enc = with_vd(base, 8)
    enc = with_vs2(enc, 16)
    enc = with_vs1(enc, 24)
    enc = with_vm(enc, 0)  # reserved (must be 1)
    emit_raw_test(instruction, "cp_ssstrictv_vcompress_vm0_reserved", enc,
                  sew=8, init_vregs=(8, 16, 24))


# --------------------------------------------------------------------------
# vmvNr.v with reserved simm (not 0/1/3/7). simm sits in vs1[19:15].
# --------------------------------------------------------------------------

_VMVNR = {"vmv1r.v", "vmv2r.v", "vmv4r.v", "vmv8r.v"}
_RESERVED_SIMM = [n for n in range(32) if n not in (0, 1, 3, 7)]


@register("cp_ssstrictv_vmvnr_simm_reserved")
def vmvnr_simm(instruction: str) -> None:
    if instruction not in _VMVNR:
        return
    base = encode(instruction)
    if base is None:
        return
    # Strip the encoded simm (vs1 field) and emit one test per reserved value.
    cleared = with_vs1(base, 0)
    for simm in _RESERVED_SIMM:
        enc = with_vd(cleared, 8)
        enc = with_vs2(enc, 16)
        enc = with_vs1(enc, simm)
        emit_raw_test(instruction, "cp_ssstrictv_vmvnr_simm_reserved", enc,
                      sew=8, init_vregs=(16,), comment=f"simm={simm}")


# --------------------------------------------------------------------------
# Vector LS with mew=1 (reserved). 294 instructions in the family.
# --------------------------------------------------------------------------

@register("cp_ssstrictv_ls_mew_reserved")
def ls_mew(instruction: str) -> None:
    base = encode(instruction)
    if base is None:
        return
    # Use rs1=x1 (we'll set x1 to a valid LS address) and choose vd/vs2
    # avoiding v0 and avoiding overlap. For indexed LS, vs2 is the index reg.
    enc = with_vd(base, 8)
    if "xei" in instruction:
        # Indexed LS: vs2 holds the index reg.
        enc = with_vs2(enc, 16)
    enc = with_rs1(enc, 1)
    enc = with_mew(enc, 1)  # reserved
    eew = common.getInstructionEEW(instruction) or 8
    sew = eew if eew in (8, 16, 32, 64) else 8
    init = (8,)
    if "xei" in instruction:
        init = (8, 16)
    emit_raw_test(instruction, "cp_ssstrictv_ls_mew_reserved", enc,
                  sew=sew, rs1_addr=True, init_vregs=init)


# --------------------------------------------------------------------------
# Whole-register stores with reserved nf (not 0/1/3/7).
# --------------------------------------------------------------------------

_VSnR = {"vs1r.v": 0, "vs2r.v": 1, "vs4r.v": 3, "vs8r.v": 7}

# Per-mnemonic NREG (number of registers) for vsNr.v.
_VSnR_NREG = {"vs1r.v": 1, "vs2r.v": 2, "vs4r.v": 4, "vs8r.v": 8}


@register("cp_ssstrictv_ls_wr_nf_not_pow2")
@register("cp_ssstrictv_ls_wr_nreg2_vd_unaligned")
@register("cp_ssstrictv_ls_wr_nreg4_vd_unaligned")
@register("cp_ssstrictv_ls_wr_nreg8_vd_unaligned")
def ls_wr_nf(instruction: str) -> None:
    if instruction not in _VSnR:
        return
    base = encode(instruction)
    if base is None:
        return
    valid = set(_VSnR.values())

    if instruction == "vs1r.v":
        # Reserved-nf encodings (nf not in {0,1,3,7}): emit one test per reserved nf.
        cleared = with_nf(base, 0)
        for nf in range(8):
            if nf in valid:
                continue
            enc = with_vd(cleared, 8)
            enc = with_rs1(enc, 1)
            enc = with_nf(enc, nf)
            emit_raw_test(instruction, "cp_ssstrictv_ls_wr_nf_not_pow2", enc,
                          sew=8, rs1_addr=True, init_vregs=(8,), comment=f"nf={nf}")
        return

    # vs2r/vs4r/vs8r.v: reserved when vd not aligned to NREG.
    nreg = _VSnR_NREG[instruction]
    cp = f"cp_ssstrictv_ls_wr_nreg{nreg}_vd_unaligned"
    for vd in range(32):
        if vd % nreg == 0:
            continue
        enc = with_vd(base, vd)
        enc = with_rs1(enc, 1)
        emit_raw_test(instruction, cp, enc,
                      sew=8, rs1_addr=True, init_vregs=(vd,), comment=f"vd={vd} (NREG={nreg})")
