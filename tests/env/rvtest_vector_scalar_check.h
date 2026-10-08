// rvtest_vector_scalar_check.h
// SPDX-License-Identifier: Apache-2.0
// -----------
// Scalar self-checking for vector tests (RVTEST_VEC_SCALAR_CHECK).
//
// The standard vector SIGUPD macros compare results with vector compare, mask,
// and permutation instructions. This header replaces them with versions that
// only rely on vsetvli/vsetvl, unit-stride vle<eew>.v/vse<eew>.v at EEW=SEW,
// and scalar code:
//   1. The register under test is stored to a buffer with vse<eew>.v at VLMAX.
//   2. A shared scalar routine walks the elements and classifies each one as
//      active, tail, or mask-inactive, applying the vta/vma all-ones relaxation.
//   3. In the signature (non-SELFCHECK) build the same routine copies the buffer
//      to the signature instead, so both builds run identical inline code and
//      keep identical .text and .data layouts.
// The signature layout is the same as the standard vector macros.
// Test setup code that would need other vector instructions (index range
// adjustment and reloading stored data) is emulated with scalar routines here.

#ifndef RVTEST_VECTOR_SCALAR_CHECK_H
#define RVTEST_VECTOR_SCALAR_CHECK_H

// Context block slots (each REGWIDTH bytes)
#define VSC_VL        (0*REGWIDTH)   // effective vl used to split active/tail
#define VSC_ORIGVL    (1*REGWIDTH)   // vl of the instruction under test
#define VSC_VTYPE     (2*REGWIDTH)   // vtype of the instruction under test
#define VSC_EXP       (3*REGWIDTH)   // expected value pointer (signature)
#define VSC_EXP2      (4*REGWIDTH)   // expected VLMAX mask result (mask-producing tail)
#define VSC_NELEM     (5*REGWIDTH)   // number of elements (bits in bit mode) to check
#define VSC_NBYTES    (6*REGWIDTH)   // bytes copied to the signature
#define VSC_FLAGS     (7*REGWIDTH)
#define VSC_EEWLOG    (8*REGWIDTH)   // log2(EEW/8)
#define VSC_REGION    (9*REGWIDTH)   // 0=active, 1=tail, 2=mask, 3=base
#define VSC_INDEX     (10*REGWIDTH)
#define VSC_FIRST0    (11*REGWIDTH)  // first failing index per region (4 slots)
#define VSC_PASS      (15*REGWIDTH)
#define VSC_EXPB      (16*REGWIDTH)  // expected element bytes (8 bytes)
#define VSC_ACTB      (18*REGWIDTH)  // actual element bytes (8 bytes)
#define VSC_RESULT    (20*REGWIDTH)
#define VSC_SAVE      (21*REGWIDTH)  // 9 saved registers
#define VSC_G_IEEWLOG (30*REGWIDTH)  // gather: log2(index EEW/8)

// Index adjustment (rvtest_vsc_ifix) reuses: VSC_VL = vl, VSC_EXP = divisor,
// VSC_EXP2 = shift amount or AND mask, VSC_FLAGS = VSC_IFIX_SHIFT or 0, VSC_EEWLOG.
#define VSC_IFIX_SHIFT  1

// Gather (rvtest_vsc_gather) reuses: VSC_VL = saved vl, VSC_ORIGVL = element count,
// VSC_VTYPE = saved vtype, VSC_EXP = base address, VSC_EXP2 = stride,
// VSC_NELEM = fields, VSC_NBYTES = bytes per field buffer, VSC_EEWLOG, VSC_FLAGS.
#define VSC_G_MASKED    1
#define VSC_G_UNIT      (0 << 4)
#define VSC_G_STRIDED   (1 << 4)
#define VSC_G_INDEXED   (2 << 4)

#define VSC_F_MASKED    1
#define VSC_F_BITMODE   2
#define VSC_F_VCOMPRESS 4
#define VSC_F_BASE      8
#define VSC_F_MASKPROD  16
#define VSC_F_AGNOSTIC  32  // check tail and inactive elements as agnostic regardless of vtype

// Data block layout, relative to rvtest_vsc_ctx
#define VSC_CTX_BYTES 256
#define VSC_OFF_V0    (VSC_CTX_BYTES)
#define VSC_OFF_VS1   (VSC_OFF_V0 + VLEN_BYTES)
#define VSC_OFF_ACT   (VSC_OFF_VS1 + VLEN_BYTES)
#define VSC_OFF_IDX   (VSC_OFF_ACT + UDB_VLEN)

#if UDB_MXLEN == 64
  #define VSC_SLOT_SHIFT 3
#else
  #define VSC_SLOT_SHIFT 2
#endif

#define VSC_EEWLOG_OF(_EEW) (((_EEW) >> 4) - ((_EEW) >> 6))

// _RD = _RS + _OFF. _RD and _RS must differ when _OFF does not fit in an immediate.
#define VSC_ADDI(_RD, _RS, _OFF) \
    .if ((_OFF) < 2048)         ;\
        addi _RD, _RS, _OFF     ;\
    .else                       ;\
        .ifc _RD, _RS           ;\
            .error "VSC_ADDI: _RD and _RS must differ for large offsets" ;\
        .endif                  ;\
        LI(_RD, _OFF)           ;\
        add _RD, _RD, _RS       ;\
    .endif

#undef RVTEST_SIGUPD_V
#undef RVTEST_SIGUPD_V_LEN
#undef RVTEST_SIGUPD_VLMAX_MASK_PROD

// Base suite check: compares the first vl elements of _VREG at EEW=_VD_EEW.
// _CMP selects data (vmsne.vv) or mask (vmxor.mm) comparison; _VTMP and _MTMP are unused.
#define RVTEST_SIGUPD_V(_CMP, _SIG_PTR, _LINK_REG, _TEMP_REG,                             \
    _VTMP, _MTMP, _VD_EEW, _VREG, _INST_PTR, _STR_PTR)                                    \
    .option push                                                                         ;\
    .option norvc                                                                        ;\
    LA(_TEMP_REG, rvtest_vsc_ctx)                                                        ;\
    VSC_ADDI(_LINK_REG, _TEMP_REG, VSC_OFF_ACT)                                          ;\
    vse##_VD_EEW.v _VREG, (_LINK_REG)                                                    ;\
    SREG _SIG_PTR, VSC_EXP(_TEMP_REG)                                                    ;\
    csrr _LINK_REG, vl                                                                   ;\
    SREG _LINK_REG, VSC_VL(_TEMP_REG)                                                    ;\
    SREG _LINK_REG, VSC_ORIGVL(_TEMP_REG)                                                ;\
    SREG _LINK_REG, VSC_NELEM(_TEMP_REG)                                                 ;\
    slli _LINK_REG, _LINK_REG, VSC_EEWLOG_OF(_VD_EEW)                                    ;\
    SREG _LINK_REG, VSC_NBYTES(_TEMP_REG)                                                ;\
    csrr _LINK_REG, vtype                                                                ;\
    SREG _LINK_REG, VSC_VTYPE(_TEMP_REG)                                                 ;\
    LI(_LINK_REG, VSC_EEWLOG_OF(_VD_EEW))                                                ;\
    SREG _LINK_REG, VSC_EEWLOG(_TEMP_REG)                                                ;\
    .ifc _CMP, vmxor.mm                                                                  ;\
        LI(_LINK_REG, (VSC_F_BASE | VSC_F_BITMODE))                                      ;\
    .else                                                                                ;\
        LI(_LINK_REG, VSC_F_BASE)                                                        ;\
    .endif                                                                               ;\
    SREG _LINK_REG, VSC_FLAGS(_TEMP_REG)                                                 ;\
    jal _LINK_REG, rvtest_vsc_entry_##_LINK_REG##_##_TEMP_REG                            ;\
    beqz _TEMP_REG, 2f                                                                   ;\
    jal _LINK_REG, failedtest_vsc_##_LINK_REG##_##_TEMP_REG                              ;\
    RVTEST_WORD_PTR _INST_PTR                                                            ;\
    RVTEST_WORD_PTR _STR_PTR                                                             ;\
    vxor.vv _VREG, _VREG, _VREG     /* Not executed: encodes VREG for the failure code */;\
2:                                                                                       ;\
    RVTEST_SIGUPD_V_ADVANCE(_SIG_PTR, _LINK_REG, _TEMP_REG)                              ;\
    .option pop

// Length suite check: compares the whole register group of _VR at EEW=_VD_EEW and
// LMUL=_LMUL (or the whole mask register when _MASKPROD_FLAG is set).
// _FORCE_TA_MA_FLAG checks the instruction as tail and mask agnostic whatever vta and vma are.
// _VTMP, _MTMP3, _MTMP2, and _MTMP are unused. Restores vl and vtype at the end.
#define RVTEST_SIGUPD_V_LEN(_SIG_PTR, _LINK_REG, _TEMP_REG, _TEMP_REG2, _TEMP_REG3, _VTMP, _MTMP3, _MTMP2, _MTMP, _VR, \
    _VS1, _MASK_REG, _MASKPROD_FLAG, _MASKED_FLAG, _VCOMPRESS_FLAG, _VD_EEW, _LMUL, _SCALAR_DST_FLAG, _FORCE_TA_MA_FLAG, \
    _INST_PTR, _STR_PTR) \
    .option push                                                                         ;\
    .option norvc                                                                        ;\
    LA(_TEMP_REG3, rvtest_vsc_ctx)                                                       ;\
    csrr _TEMP_REG2, vtype                                                               ;\
    SREG _TEMP_REG2, VSC_VTYPE(_TEMP_REG3)                                               ;\
    csrr _TEMP_REG, vl                                                                   ;\
    SREG _TEMP_REG, VSC_ORIGVL(_TEMP_REG3)                                               ;\
    .if (_SCALAR_DST_FLAG == 1)                                                          ;\
        li _TEMP_REG, 1                                                                  ;\
    .endif                                                                               ;\
    SREG _TEMP_REG, VSC_VL(_TEMP_REG3)                                                   ;\
    SREG _SIG_PTR, VSC_EXP(_TEMP_REG3)                                                   ;\
    vsetvli _LINK_REG, x0, e8, m1, ta, ma                                                ;\
    .if (_MASKED_FLAG == 1)                                                              ;\
        VSC_ADDI(_TEMP_REG, _TEMP_REG3, VSC_OFF_V0)                                      ;\
        vse8.v _MASK_REG, (_TEMP_REG)                                                    ;\
    .endif                                                                               ;\
    .if (_VCOMPRESS_FLAG == 1)                                                           ;\
        VSC_ADDI(_TEMP_REG, _TEMP_REG3, VSC_OFF_VS1)                                     ;\
        vse8.v _VS1, (_TEMP_REG)                                                         ;\
    .endif                                                                               ;\
    VSC_ADDI(_TEMP_REG, _TEMP_REG3, VSC_OFF_ACT)                                         ;\
    .if (_MASKPROD_FLAG == 1)                                                            ;\
        vse8.v _VR, (_TEMP_REG)                                                          ;\
        SREG _LINK_REG, VSC_NBYTES(_TEMP_REG3)                                           ;\
        slli _LINK_REG, _LINK_REG, 3                                                     ;\
        SREG _LINK_REG, VSC_NELEM(_TEMP_REG3)                                            ;\
        SREG x0, VSC_EEWLOG(_TEMP_REG3)                                                  ;\
        vsetvli _LINK_REG, x0, e8, m8, ta, ma                                            ;\
    .else                                                                                ;\
        vsetvli _LINK_REG, x0, e##_VD_EEW, m##_LMUL, ta, ma                              ;\
        vse##_VD_EEW.v _VR, (_TEMP_REG)                                                  ;\
        SREG _LINK_REG, VSC_NELEM(_TEMP_REG3)                                            ;\
        slli _LINK_REG, _LINK_REG, VSC_EEWLOG_OF(_VD_EEW)                                ;\
        SREG _LINK_REG, VSC_NBYTES(_TEMP_REG3)                                           ;\
        LI(_LINK_REG, VSC_EEWLOG_OF(_VD_EEW))                                            ;\
        SREG _LINK_REG, VSC_EEWLOG(_TEMP_REG3)                                           ;\
    .endif                                                                               ;\
    LI(_LINK_REG, ((_MASKED_FLAG * VSC_F_MASKED) | (_MASKPROD_FLAG * (VSC_F_BITMODE | VSC_F_MASKPROD)) | \
        (_VCOMPRESS_FLAG * VSC_F_VCOMPRESS) | (_FORCE_TA_MA_FLAG * VSC_F_AGNOSTIC)))     ;\
    SREG _LINK_REG, VSC_FLAGS(_TEMP_REG3)                                                ;\
    RVTEST_SIGUPD_V_ADVANCE(_SIG_PTR, _LINK_REG, _TEMP_REG)                              ;\
    SREG _SIG_PTR, VSC_EXP2(_TEMP_REG3)                                                  ;\
    mv _TEMP_REG, _TEMP_REG3                                                             ;\
    jal _LINK_REG, rvtest_vsc_entry_##_LINK_REG##_##_TEMP_REG                            ;\
    beqz _TEMP_REG, 12f                                                                  ;\
    jal _LINK_REG, failedtest_vsc_##_LINK_REG##_##_TEMP_REG                              ;\
    RVTEST_WORD_PTR _INST_PTR                                                            ;\
    RVTEST_WORD_PTR _STR_PTR                                                             ;\
    vxor.vv _VR, _VR, _VR           /* Not executed: encodes VR for the failure code */  ;\
12:                                                                                      ;\
    LA(_TEMP_REG3, rvtest_vsc_ctx)                                                       ;\
    LREG _TEMP_REG, VSC_ORIGVL(_TEMP_REG3)                                               ;\
    LREG _TEMP_REG2, VSC_VTYPE(_TEMP_REG3)                                               ;\
    vsetvl _TEMP_REG, _TEMP_REG, _TEMP_REG2                                              ;\
    .option pop

// Stores the VLMAX result of a mask-producing instruction to the next signature slot
// in the signature build. The self-checking build runs the same code but skips the copy.
#define RVTEST_SIGUPD_VLMAX_MASK_PROD(_SIG_PTR, _LINK_REG, _TEMP_REG, _VR)                \
    .option push                                                                         ;\
    .option norvc                                                                        ;\
    vsetvli _LINK_REG, x0, e8, m1, ta, ma                                                ;\
    LA(_TEMP_REG, rvtest_vsc_ctx)                                                        ;\
    SREG _LINK_REG, VSC_NBYTES(_TEMP_REG)                                                ;\
    SREG _SIG_PTR, VSC_EXP(_TEMP_REG)                                                    ;\
    VSC_ADDI(_LINK_REG, _TEMP_REG, VSC_OFF_ACT)                                          ;\
    vse8.v _VR, (_LINK_REG)                                                              ;\
    jal _LINK_REG, rvtest_vsc_copyonly_##_LINK_REG##_##_TEMP_REG                         ;\
    vsetvli _LINK_REG, x0, e8, m8, ta, ma                                                ;\
    RVTEST_SIGUPD_V_ADVANCE(_SIG_PTR, _LINK_REG, _TEMP_REG)                              ;\
    .option pop

// Places the value 0xFF in bytes [0, n/8), (1 << (n % 8)) - 1 in byte n/8 (when n < VLEN),
// and 0 above it, then loads the result into v0. Requires n <= VLEN. Leaves vtype at e8, m1, ta, ma.
#define RVTEST_VSC_LOWER_BITS_MASK(_NREG, _T1, _T2, _T3)                                  \
    LA(_T1, rvtest_vsc_mask_scratch)                                                     ;\
    csrr _T2, vlenb                                                                      ;\
    add _T2, _T2, _T1                                                                    ;\
1:                                                                                       ;\
    bgeu _T1, _T2, 2f                                                                    ;\
    sb x0, 0(_T1)                                                                        ;\
    addi _T1, _T1, 1                                                                     ;\
    j 1b                                                                                 ;\
2:                                                                                       ;\
    LA(_T1, rvtest_vsc_mask_scratch)                                                     ;\
    srli _T2, _NREG, 3                                                                   ;\
    add _T2, _T2, _T1                                                                    ;\
    li _T3, 0xff                                                                         ;\
3:                                                                                       ;\
    bgeu _T1, _T2, 4f                                                                    ;\
    sb _T3, 0(_T1)                                                                       ;\
    addi _T1, _T1, 1                                                                     ;\
    j 3b                                                                                 ;\
4:                                                                                       ;\
    srli _T3, _NREG, 3                                                                   ;\
    csrr _T2, vlenb                                                                      ;\
    bgeu _T3, _T2, 5f          /* n = VLEN: no partial byte */                           ;\
    andi _T3, _NREG, 7                                                                   ;\
    li _T2, 1                                                                            ;\
    sll _T2, _T2, _T3                                                                    ;\
    addi _T2, _T2, -1                                                                    ;\
    sb _T2, 0(_T1)                                                                       ;\
5:                                                                                       ;\
    vsetvli _T1, x0, e8, m1, ta, ma                                                      ;\
    LA(_T1, rvtest_vsc_mask_scratch)                                                     ;\
    vle8.v v0, (_T1)

// Copies the whole register _VSRC to _VDST through memory, preserving vl and vtype.
#define RVTEST_VSC_COPY_VREG(_VDST, _VSRC, _T1, _T2, _T3)                                 \
    csrr _T1, vl                                                                         ;\
    csrr _T2, vtype                                                                      ;\
    vsetvli _T3, x0, e8, m1, ta, ma                                                      ;\
    LA(_T3, rvtest_vsc_mask_scratch)                                                     ;\
    vse8.v _VSRC, (_T3)                                                                  ;\
    vle8.v _VDST, (_T3)                                                                  ;\
    vsetvl x0, _T1, _T2

// Applies vremu.vx _VREG, _VREG, _DIVREG followed by vsll.vi (_SHIFT_FLAG = 1) or
// vand.vi (_SHIFT_FLAG = 0) with immediate _IMM to the first vl elements of _VREG,
// using scalar code. vtype must have SEW = _EEW. Clobbers _LINK_REG and _TEMP_REG.
#define RVTEST_VSC_INDEX_FIXUP(_VREG, _EEW, _DIVREG, _SHIFT_FLAG, _IMM, _LINK_REG, _TEMP_REG) \
    LA(_TEMP_REG, rvtest_vsc_ctx)                                                        ;\
    csrr _LINK_REG, vl                                                                   ;\
    SREG _LINK_REG, VSC_VL(_TEMP_REG)                                                    ;\
    SREG _DIVREG, VSC_EXP(_TEMP_REG)                                                     ;\
    LI(_LINK_REG, _IMM)                                                                  ;\
    SREG _LINK_REG, VSC_EXP2(_TEMP_REG)                                                  ;\
    LI(_LINK_REG, _SHIFT_FLAG)                                                           ;\
    SREG _LINK_REG, VSC_FLAGS(_TEMP_REG)                                                 ;\
    LI(_LINK_REG, VSC_EEWLOG_OF(_EEW))                                                   ;\
    SREG _LINK_REG, VSC_EEWLOG(_TEMP_REG)                                                ;\
    VSC_ADDI(_LINK_REG, _TEMP_REG, VSC_OFF_ACT)                                          ;\
    vse##_EEW.v _VREG, (_LINK_REG)                                                       ;\
    jal _LINK_REG, rvtest_vsc_ifix_##_LINK_REG##_##_TEMP_REG                             ;\
    LA(_TEMP_REG, rvtest_vsc_ctx)                                                        ;\
    VSC_ADDI(_LINK_REG, _TEMP_REG, VSC_OFF_ACT)                                          ;\
    vle##_EEW.v _VREG, (_LINK_REG)

// The routines only use base integer instructions, so the tests do not require M.

// _RD = _RD * _RS (low XLEN bits) by shift and add. _RS must be non-negative.
// Clobbers _T1, _T2, and _T3.
#define VSC_MUL(_RD, _RS, _T1, _T2, _T3) \
    mv _T3, _RD                 ;\
    mv _T1, _RS                 ;\
    li _RD, 0                   ;\
81:                             ;\
    beqz _T1, 83f               ;\
    andi _T2, _T1, 1            ;\
    beqz _T2, 82f               ;\
    add _RD, _RD, _T3           ;\
82:                             ;\
    slli _T3, _T3, 1            ;\
    srli _T1, _T1, 1            ;\
    j 81b                       ;\
83:

// Shifts the XLEN bits of _WORD into the unsigned remainder _REM modulo _DIV, most
// significant bit first. Requires _DIV != 0 and _REM < _DIV. Clears _WORD and clobbers _CNT.
#define VSC_REMU_WORD(_REM, _WORD, _DIV, _CNT) \
    li _CNT, UDB_MXLEN          ;\
91:                             ;\
    beqz _CNT, 95f              ;\
    addi _CNT, _CNT, -1         ;\
    bltz _REM, 93f              ;\
    slli _REM, _REM, 1          ;\
    bgez _WORD, 92f             ;\
    ori _REM, _REM, 1           ;\
92:                             ;\
    slli _WORD, _WORD, 1        ;\
    bltu _REM, _DIV, 91b        ;\
    sub _REM, _REM, _DIV        ;\
    j 91b                       ;\
    /* The shift carries out of XLEN, so the remainder is at least _DIV */ ;\
93:                             ;\
    slli _REM, _REM, 1          ;\
    bgez _WORD, 94f             ;\
    ori _REM, _REM, 1           ;\
94:                             ;\
    slli _WORD, _WORD, 1        ;\
    sub _REM, _REM, _DIV        ;\
    j 91b                       ;\
95:

// Loads bit _IDX of the byte array at _BASE into _RD. Clobbers _TMP.
#define VSC_LOAD_BIT(_RD, _BASE, _IDX, _TMP)                                              \
    srli _TMP, _IDX, 3                                                                   ;\
    add _RD, _BASE, _TMP                                                                 ;\
    lbu _RD, 0(_RD)                                                                      ;\
    andi _TMP, _IDX, 7                                                                   ;\
    srl _RD, _RD, _TMP                                                                   ;\
    andi _RD, _RD, 1

// Shared routines for one link/temp register pair. The caller passes the context
// block in _T and returns through _L. On return, _T is 0 if the check passed.
// Only the jump in the entry stubs differs between the signature and self-checking builds.
.macro RVTEST_VSC_ROUTINES L, T
    .option push
    .option norvc

rvtest_vsc_entry_\L\()_\T:
#ifdef RVTEST_SELFCHECK
    j rvtest_vsc_check_\L\()_\T
#else
    j rvtest_vsc_copy_\L\()_\T
#endif

rvtest_vsc_copyonly_\L\()_\T:
#ifdef RVTEST_SELFCHECK
    j rvtest_vsc_ret0_\L\()_\T
#else
    j rvtest_vsc_copy_\L\()_\T
#endif

rvtest_vsc_ret0_\L\()_\T:
    li \T, 0
    jr \L

    // Copy NBYTES from the result buffer to the signature
rvtest_vsc_copy_\L\()_\T:
    SREG x3, VSC_SAVE+0*REGWIDTH(\T)
    SREG x6, VSC_SAVE+1*REGWIDTH(\T)
    SREG x9, VSC_SAVE+2*REGWIDTH(\T)
    SREG x12, VSC_SAVE+3*REGWIDTH(\T)
    LREG x6, VSC_NBYTES(\T)
    LREG x9, VSC_EXP(\T)
    VSC_ADDI(x3, \T, VSC_OFF_ACT)
rvtest_vsc_copy_loop_\L\()_\T:
    beqz x6, rvtest_vsc_copy_done_\L\()_\T
    lbu x12, 0(x3)
    sb x12, 0(x9)
    addi x3, x3, 1
    addi x9, x9, 1
    addi x6, x6, -1
    j rvtest_vsc_copy_loop_\L\()_\T
rvtest_vsc_copy_done_\L\()_\T:
    LREG x3, VSC_SAVE+0*REGWIDTH(\T)
    LREG x6, VSC_SAVE+1*REGWIDTH(\T)
    LREG x9, VSC_SAVE+2*REGWIDTH(\T)
    LREG x12, VSC_SAVE+3*REGWIDTH(\T)
    li \T, 0
    jr \L

    // Compare the result buffer with the signature.
    // x3 = element index, x9 = result buffer, x10 = expected, x11 = log2(EEW/8)
    // x15 = element status: bit 0 mismatch, bit 1 not all ones, bit 2 result bit (bit mode)
rvtest_vsc_check_\L\()_\T:
    SREG x1, VSC_SAVE+0*REGWIDTH(\T)
    SREG x2, VSC_SAVE+1*REGWIDTH(\T)
    SREG x3, VSC_SAVE+2*REGWIDTH(\T)
    SREG x6, VSC_SAVE+3*REGWIDTH(\T)
    SREG x9, VSC_SAVE+4*REGWIDTH(\T)
    SREG x10, VSC_SAVE+5*REGWIDTH(\T)
    SREG x11, VSC_SAVE+6*REGWIDTH(\T)
    SREG x12, VSC_SAVE+7*REGWIDTH(\T)
    SREG x15, VSC_SAVE+8*REGWIDTH(\T)
    VSC_ADDI(x9, \T, VSC_OFF_ACT)
    LREG x10, VSC_EXP(\T)
    LREG x11, VSC_EEWLOG(\T)
    li x12, -1
    SREG x12, VSC_FIRST0+0*REGWIDTH(\T)
    SREG x12, VSC_FIRST0+1*REGWIDTH(\T)
    SREG x12, VSC_FIRST0+2*REGWIDTH(\T)
    SREG x12, VSC_FIRST0+3*REGWIDTH(\T)
    SREG x0, VSC_PASS(\T)
    SREG x0, VSC_RESULT(\T)

    // vcompress: the effective vl is the number of set bits of vs1 below the original vl
    LREG x12, VSC_FLAGS(\T)
    andi x12, x12, VSC_F_VCOMPRESS
    beqz x12, rvtest_vsc_elements_\L\()_\T
    LREG x6, VSC_ORIGVL(\T)
    VSC_ADDI(x1, \T, VSC_OFF_VS1)
    li x3, 0
    li x15, 0
rvtest_vsc_popcount_\L\()_\T:
    bgeu x3, x6, rvtest_vsc_popcount_done_\L\()_\T
    VSC_LOAD_BIT(x12, x1, x3, x2)
    add x15, x15, x12
    addi x3, x3, 1
    j rvtest_vsc_popcount_\L\()_\T
rvtest_vsc_popcount_done_\L\()_\T:
    SREG x15, VSC_VL(\T)

rvtest_vsc_elements_\L\()_\T:
    li x3, 0
rvtest_vsc_loop_\L\()_\T:
    LREG x6, VSC_NELEM(\T)
    bgeu x3, x6, rvtest_vsc_loop_done_\L\()_\T
    LREG x12, VSC_FLAGS(\T)
    andi x12, x12, VSC_F_BITMODE
    beqz x12, rvtest_vsc_bytes_\L\()_\T

    // Bit mode: one mask bit per element
    VSC_LOAD_BIT(x6, x9, x3, x2)
    VSC_LOAD_BIT(x12, x10, x3, x2)
    xor x15, x6, x12
    xori x2, x6, 1
    slli x2, x2, 1
    or x15, x15, x2
    slli x2, x6, 2
    or x15, x15, x2
    j rvtest_vsc_classify_\L\()_\T

    // Byte mode: compare the 2^x11 bytes of the element
rvtest_vsc_bytes_\L\()_\T:
    sll x12, x3, x11
    add x12, x12, x9
    li x6, 1
    sll x6, x6, x11
    add x6, x6, x12
    li x15, 0
rvtest_vsc_byte_loop_\L\()_\T:
    bgeu x12, x6, rvtest_vsc_classify_\L\()_\T
    lbu x2, 0(x12)
    sub x1, x12, x9
    add x1, x1, x10
    lbu x1, 0(x1)
    beq x2, x1, rvtest_vsc_byte_same_\L\()_\T
    ori x15, x15, 1
rvtest_vsc_byte_same_\L\()_\T:
    li x1, 0xff
    beq x2, x1, rvtest_vsc_byte_ones_\L\()_\T
    ori x15, x15, 2
rvtest_vsc_byte_ones_\L\()_\T:
    addi x12, x12, 1
    j rvtest_vsc_byte_loop_\L\()_\T

    // Classify the element and decide whether a mismatch is a failure. x12 = region
rvtest_vsc_classify_\L\()_\T:
    andi x1, x15, 1
    beqz x1, rvtest_vsc_next_\L\()_\T
    LREG x6, VSC_FLAGS(\T)
    andi x12, x6, VSC_F_BASE
    beqz x12, rvtest_vsc_not_base_\L\()_\T
    li x12, 3
    j rvtest_vsc_fail_\L\()_\T
rvtest_vsc_not_base_\L\()_\T:
    LREG x2, VSC_VL(\T)
    bltu x3, x2, rvtest_vsc_body_\L\()_\T
    li x12, 1
    andi x2, x6, VSC_F_MASKPROD
    beqz x2, rvtest_vsc_tail_data_\L\()_\T
    // Mask destination tails are always agnostic: accept 1s or the VLMAX result
    andi x2, x15, 2
    beqz x2, rvtest_vsc_next_\L\()_\T
    LREG x6, VSC_EXP2(\T)
    VSC_LOAD_BIT(x2, x6, x3, x1)
    srli x1, x15, 2
    andi x1, x1, 1
    beq x1, x2, rvtest_vsc_next_\L\()_\T
    j rvtest_vsc_fail_\L\()_\T
rvtest_vsc_tail_data_\L\()_\T:
    LREG x2, VSC_FLAGS(\T)
    andi x2, x2, VSC_F_AGNOSTIC
    bnez x2, rvtest_vsc_agnostic_\L\()_\T
    LREG x2, VSC_VTYPE(\T)
    srli x2, x2, 6
    andi x2, x2, 1
    j rvtest_vsc_agnostic_\L\()_\T
rvtest_vsc_body_\L\()_\T:
    andi x2, x6, VSC_F_MASKED
    beqz x2, rvtest_vsc_active_\L\()_\T
    VSC_ADDI(x6, \T, VSC_OFF_V0)
    VSC_LOAD_BIT(x2, x6, x3, x1)
    bnez x2, rvtest_vsc_active_\L\()_\T
    li x12, 2
    LREG x2, VSC_FLAGS(\T)
    andi x2, x2, VSC_F_AGNOSTIC
    bnez x2, rvtest_vsc_agnostic_\L\()_\T
    LREG x2, VSC_VTYPE(\T)
    srli x2, x2, 7
    andi x2, x2, 1
    // x2 = agnostic policy bit: an all-ones element is also accepted
rvtest_vsc_agnostic_\L\()_\T:
    beqz x2, rvtest_vsc_fail_\L\()_\T
    andi x2, x15, 2
    beqz x2, rvtest_vsc_next_\L\()_\T
    j rvtest_vsc_fail_\L\()_\T
rvtest_vsc_active_\L\()_\T:
    li x12, 0

    // First pass records the first failing index per region.
    // Second pass sets the failing mask bits for the reported region.
rvtest_vsc_fail_\L\()_\T:
    LREG x2, VSC_PASS(\T)
    bnez x2, rvtest_vsc_mark_\L\()_\T
    slli x1, x12, VSC_SLOT_SHIFT
    add x1, x1, \T
    LREG x2, VSC_FIRST0(x1)
    bgez x2, rvtest_vsc_next_\L\()_\T
    SREG x3, VSC_FIRST0(x1)
    j rvtest_vsc_next_\L\()_\T
rvtest_vsc_mark_\L\()_\T:
    LREG x2, VSC_REGION(\T)
    bne x2, x12, rvtest_vsc_next_\L\()_\T
    LA(x2, failing_mask_vec)
    srli x1, x3, 3
    add x2, x2, x1
    lbu x6, 0(x2)
    andi x1, x3, 7
    li x12, 1
    sll x12, x12, x1
    or x6, x6, x12
    sb x6, 0(x2)
rvtest_vsc_next_\L\()_\T:
    addi x3, x3, 1
    j rvtest_vsc_loop_\L\()_\T

rvtest_vsc_loop_done_\L\()_\T:
    LREG x2, VSC_PASS(\T)
    bnez x2, rvtest_vsc_exit_\L\()_\T
    // Report active, then base, then tail, then mask-inactive mismatches
    li x12, 0
    LREG x3, VSC_FIRST0+0*REGWIDTH(\T)
    bgez x3, rvtest_vsc_found_\L\()_\T
    li x12, 3
    LREG x3, VSC_FIRST0+3*REGWIDTH(\T)
    bgez x3, rvtest_vsc_found_\L\()_\T
    li x12, 1
    LREG x3, VSC_FIRST0+1*REGWIDTH(\T)
    bgez x3, rvtest_vsc_found_\L\()_\T
    li x12, 2
    LREG x3, VSC_FIRST0+2*REGWIDTH(\T)
    bgez x3, rvtest_vsc_found_\L\()_\T
    j rvtest_vsc_exit_\L\()_\T

rvtest_vsc_found_\L\()_\T:
    SREG x12, VSC_REGION(\T)
    SREG x3, VSC_INDEX(\T)
    LA(x2, failing_mask_vec)
    csrr x6, vlenb
    add x6, x6, x2
rvtest_vsc_clear_mask_\L\()_\T:
    bgeu x2, x6, rvtest_vsc_capture_\L\()_\T
    sb x0, 0(x2)
    addi x2, x2, 1
    j rvtest_vsc_clear_mask_\L\()_\T

    // Save the failing element values for the failure report
rvtest_vsc_capture_\L\()_\T:
    SREG x0, VSC_EXPB(\T)
    SREG x0, VSC_EXPB+REGWIDTH(\T)
    SREG x0, VSC_ACTB(\T)
    SREG x0, VSC_ACTB+REGWIDTH(\T)
    LREG x6, VSC_FLAGS(\T)
    andi x6, x6, VSC_F_BITMODE
    beqz x6, rvtest_vsc_capture_bytes_\L\()_\T
    VSC_LOAD_BIT(x2, x9, x3, x1)
    sb x2, VSC_ACTB(\T)
    VSC_LOAD_BIT(x2, x10, x3, x1)
    sb x2, VSC_EXPB(\T)
    j rvtest_vsc_second_pass_\L\()_\T
rvtest_vsc_capture_bytes_\L\()_\T:
    sll x12, x3, x11
    add x1, x9, x12
    add x2, x10, x12
    li x6, 1
    sll x6, x6, x11
    li x12, 0
rvtest_vsc_capture_loop_\L\()_\T:
    bgeu x12, x6, rvtest_vsc_second_pass_\L\()_\T
    add x3, \T, x12
    lbu x15, 0(x1)
    sb x15, VSC_ACTB(x3)
    lbu x15, 0(x2)
    sb x15, VSC_EXPB(x3)
    addi x1, x1, 1
    addi x2, x2, 1
    addi x12, x12, 1
    j rvtest_vsc_capture_loop_\L\()_\T

rvtest_vsc_second_pass_\L\()_\T:
    li x2, 1
    SREG x2, VSC_PASS(\T)
    SREG x2, VSC_RESULT(\T)
    j rvtest_vsc_elements_\L\()_\T

rvtest_vsc_exit_\L\()_\T:
    LREG x1, VSC_SAVE+0*REGWIDTH(\T)
    LREG x2, VSC_SAVE+1*REGWIDTH(\T)
    LREG x3, VSC_SAVE+2*REGWIDTH(\T)
    LREG x6, VSC_SAVE+3*REGWIDTH(\T)
    LREG x9, VSC_SAVE+4*REGWIDTH(\T)
    LREG x10, VSC_SAVE+5*REGWIDTH(\T)
    LREG x11, VSC_SAVE+6*REGWIDTH(\T)
    LREG x12, VSC_SAVE+7*REGWIDTH(\T)
    LREG x15, VSC_SAVE+8*REGWIDTH(\T)
    LREG \T, VSC_RESULT(\T)
    jr \L

    // Index adjustment: x3 = element, x6 = vl, x9 = buffer, x10 = divisor, x11 = log2(EEW/8)
    // x1 = element (low word), x15 = element high word (RV32, EEW=64)
rvtest_vsc_ifix_\L\()_\T:
    SREG x1, VSC_SAVE+0*REGWIDTH(\T)
    SREG x2, VSC_SAVE+1*REGWIDTH(\T)
    SREG x3, VSC_SAVE+2*REGWIDTH(\T)
    SREG x6, VSC_SAVE+3*REGWIDTH(\T)
    SREG x9, VSC_SAVE+4*REGWIDTH(\T)
    SREG x10, VSC_SAVE+5*REGWIDTH(\T)
    SREG x11, VSC_SAVE+6*REGWIDTH(\T)
    SREG x12, VSC_SAVE+7*REGWIDTH(\T)
    SREG x15, VSC_SAVE+8*REGWIDTH(\T)
    LREG x6, VSC_VL(\T)
    LREG x10, VSC_EXP(\T)
    LREG x11, VSC_EEWLOG(\T)
    // vremu.vx uses the low SEW bits of the scalar operand when SEW < XLEN
    li x1, 8
    sll x1, x1, x11
    li x2, UDB_MXLEN
    bgeu x1, x2, rvtest_vsc_ifix_div_\L\()_\T
    li x2, 1
    sll x2, x2, x1
    addi x2, x2, -1
    and x10, x10, x2
rvtest_vsc_ifix_div_\L\()_\T:
    VSC_ADDI(x9, \T, VSC_OFF_ACT)
    li x3, 0
rvtest_vsc_ifix_loop_\L\()_\T:
    bgeu x3, x6, rvtest_vsc_ifix_done_\L\()_\T
    sll x12, x3, x11
    add x12, x12, x9
    li x15, 0
    li x2, 1
    beqz x11, rvtest_vsc_ifix_ld8_\L\()_\T
    beq x11, x2, rvtest_vsc_ifix_ld16_\L\()_\T
    li x2, 2
    beq x11, x2, rvtest_vsc_ifix_ld32_\L\()_\T
#if UDB_MXLEN == 64
    ld x1, 0(x12)
#else
    lw x1, 0(x12)
    lw x15, 4(x12)
#endif
    j rvtest_vsc_ifix_rem_\L\()_\T
rvtest_vsc_ifix_ld32_\L\()_\T:
#if UDB_MXLEN == 64
    lwu x1, 0(x12)
#else
    lw x1, 0(x12)
#endif
    j rvtest_vsc_ifix_rem_\L\()_\T
rvtest_vsc_ifix_ld16_\L\()_\T:
    lhu x1, 0(x12)
    j rvtest_vsc_ifix_rem_\L\()_\T
rvtest_vsc_ifix_ld8_\L\()_\T:
    lbu x1, 0(x12)
rvtest_vsc_ifix_rem_\L\()_\T:
    // Division by zero leaves the element unchanged
    beqz x10, rvtest_vsc_ifix_op_\L\()_\T
    // x1 = {x15, x1} mod x10. x15 is 0 except for EEW=64 on RV32.
    li x2, 0
#if UDB_MXLEN == 32
    VSC_REMU_WORD(x2, x15, x10, x12)
#endif
    VSC_REMU_WORD(x2, x1, x10, x12)
    mv x1, x2
rvtest_vsc_ifix_op_\L\()_\T:
    LREG x2, VSC_FLAGS(\T)
    andi x2, x2, VSC_IFIX_SHIFT
    beqz x2, rvtest_vsc_ifix_and_\L\()_\T
    LREG x2, VSC_EXP2(\T)
#if UDB_MXLEN == 32
    beqz x2, rvtest_vsc_ifix_st_\L\()_\T
    li x12, 32
    sub x12, x12, x2
    srl x12, x1, x12
    sll x15, x15, x2
    or x15, x15, x12
#endif
    sll x1, x1, x2
    j rvtest_vsc_ifix_st_\L\()_\T
rvtest_vsc_ifix_and_\L\()_\T:
    LREG x2, VSC_EXP2(\T)
    and x1, x1, x2
#if UDB_MXLEN == 32
    srai x2, x2, 31
    and x15, x15, x2
#endif
rvtest_vsc_ifix_st_\L\()_\T:
    sll x12, x3, x11
    add x12, x12, x9
    li x2, 1
    beqz x11, rvtest_vsc_ifix_st8_\L\()_\T
    beq x11, x2, rvtest_vsc_ifix_st16_\L\()_\T
    li x2, 2
    beq x11, x2, rvtest_vsc_ifix_st32_\L\()_\T
#if UDB_MXLEN == 64
    sd x1, 0(x12)
#else
    sw x1, 0(x12)
    sw x15, 4(x12)
#endif
    j rvtest_vsc_ifix_next_\L\()_\T
rvtest_vsc_ifix_st32_\L\()_\T:
    sw x1, 0(x12)
    j rvtest_vsc_ifix_next_\L\()_\T
rvtest_vsc_ifix_st16_\L\()_\T:
    sh x1, 0(x12)
    j rvtest_vsc_ifix_next_\L\()_\T
rvtest_vsc_ifix_st8_\L\()_\T:
    sb x1, 0(x12)
rvtest_vsc_ifix_next_\L\()_\T:
    addi x3, x3, 1
    j rvtest_vsc_ifix_loop_\L\()_\T
rvtest_vsc_ifix_done_\L\()_\T:
    j rvtest_vsc_restore_\L\()_\T

    // Gather: emulates a unit-stride, strided, or indexed (segment) load into the field
    // buffers. Masked-off elements and elements at or above the element count keep the
    // buffer contents. x3 = element, x6 = element count, x9 = destination, x10 = source,
    // x11 = log2(EEW/8), x12 = fields left
rvtest_vsc_gather_\L\()_\T:
    SREG x1, VSC_SAVE+0*REGWIDTH(\T)
    SREG x2, VSC_SAVE+1*REGWIDTH(\T)
    SREG x3, VSC_SAVE+2*REGWIDTH(\T)
    SREG x6, VSC_SAVE+3*REGWIDTH(\T)
    SREG x9, VSC_SAVE+4*REGWIDTH(\T)
    SREG x10, VSC_SAVE+5*REGWIDTH(\T)
    SREG x11, VSC_SAVE+6*REGWIDTH(\T)
    SREG x12, VSC_SAVE+7*REGWIDTH(\T)
    SREG x15, VSC_SAVE+8*REGWIDTH(\T)
    LREG x6, VSC_ORIGVL(\T)
    li x3, 0
rvtest_vsc_gather_loop_\L\()_\T:
    bgeu x3, x6, rvtest_vsc_gather_done_\L\()_\T
    LREG x15, VSC_FLAGS(\T)
    andi x1, x15, VSC_G_MASKED
    beqz x1, rvtest_vsc_gather_active_\L\()_\T
    VSC_ADDI(x1, \T, VSC_OFF_V0)
    VSC_LOAD_BIT(x2, x1, x3, x12)
    beqz x2, rvtest_vsc_gather_next_\L\()_\T
rvtest_vsc_gather_active_\L\()_\T:
    srli x1, x15, 4
    andi x1, x1, 3
    bnez x1, rvtest_vsc_gather_not_unit_\L\()_\T
    LREG x10, VSC_NELEM(\T)
    VSC_MUL(x10, x3, x1, x2, x12)
    LREG x11, VSC_EEWLOG(\T)
    sll x10, x10, x11
    j rvtest_vsc_gather_addr_\L\()_\T
rvtest_vsc_gather_not_unit_\L\()_\T:
    li x2, 1
    bne x1, x2, rvtest_vsc_gather_indexed_\L\()_\T
    LREG x10, VSC_EXP2(\T)
    VSC_MUL(x10, x3, x1, x2, x12)
    j rvtest_vsc_gather_addr_\L\()_\T
    // Index values are zero-extended and truncated to XLEN
rvtest_vsc_gather_indexed_\L\()_\T:
    LREG x11, VSC_G_IEEWLOG(\T)
    sll x10, x3, x11
    VSC_ADDI(x1, \T, VSC_OFF_IDX)
    add x10, x10, x1
    li x2, 1
    beqz x11, rvtest_vsc_gather_idx8_\L\()_\T
    beq x11, x2, rvtest_vsc_gather_idx16_\L\()_\T
    li x2, 2
    beq x11, x2, rvtest_vsc_gather_idx32_\L\()_\T
#if UDB_MXLEN == 64
    ld x10, 0(x10)
#else
    lw x10, 0(x10)
#endif
    j rvtest_vsc_gather_addr_\L\()_\T
rvtest_vsc_gather_idx32_\L\()_\T:
#if UDB_MXLEN == 64
    lwu x10, 0(x10)
#else
    lw x10, 0(x10)
#endif
    j rvtest_vsc_gather_addr_\L\()_\T
rvtest_vsc_gather_idx16_\L\()_\T:
    lhu x10, 0(x10)
    j rvtest_vsc_gather_addr_\L\()_\T
rvtest_vsc_gather_idx8_\L\()_\T:
    lbu x10, 0(x10)
rvtest_vsc_gather_addr_\L\()_\T:
    LREG x1, VSC_EXP(\T)
    add x10, x10, x1
    LREG x11, VSC_EEWLOG(\T)
    sll x9, x3, x11
    VSC_ADDI(x1, \T, VSC_OFF_ACT)
    add x9, x9, x1
    LREG x12, VSC_NELEM(\T)
rvtest_vsc_gather_field_\L\()_\T:
    beqz x12, rvtest_vsc_gather_next_\L\()_\T
    li x15, 1
    sll x15, x15, x11
    mv x2, x15
rvtest_vsc_gather_byte_\L\()_\T:
    beqz x2, rvtest_vsc_gather_byte_done_\L\()_\T
    lbu x1, 0(x10)
    sb x1, 0(x9)
    addi x10, x10, 1
    addi x9, x9, 1
    addi x2, x2, -1
    j rvtest_vsc_gather_byte_\L\()_\T
rvtest_vsc_gather_byte_done_\L\()_\T:
    LREG x1, VSC_NBYTES(\T)
    sub x1, x1, x15
    add x9, x9, x1
    addi x12, x12, -1
    j rvtest_vsc_gather_field_\L\()_\T
rvtest_vsc_gather_next_\L\()_\T:
    addi x3, x3, 1
    j rvtest_vsc_gather_loop_\L\()_\T
rvtest_vsc_gather_done_\L\()_\T:

rvtest_vsc_restore_\L\()_\T:
    LREG x1, VSC_SAVE+0*REGWIDTH(\T)
    LREG x2, VSC_SAVE+1*REGWIDTH(\T)
    LREG x3, VSC_SAVE+2*REGWIDTH(\T)
    LREG x6, VSC_SAVE+3*REGWIDTH(\T)
    LREG x9, VSC_SAVE+4*REGWIDTH(\T)
    LREG x10, VSC_SAVE+5*REGWIDTH(\T)
    LREG x11, VSC_SAVE+6*REGWIDTH(\T)
    LREG x12, VSC_SAVE+7*REGWIDTH(\T)
    LREG x15, VSC_SAVE+8*REGWIDTH(\T)
    jr \L

    .option pop
.endm

.macro RVTEST_VSC_CODE
    RVTEST_VSC_FAILURE_CODE
    RVTEST_VSC_ROUTINES x5, x4
    RVTEST_VSC_ROUTINES x8, x7
    RVTEST_VSC_ROUTINES x14, x13
.endm

// Fills v0-v31 with a constant pattern using unit-stride loads instead of splatting
// integer registers with vmv.v.x. Clobbers x1 and restores its initial value.
.macro RVTEST_VSC_INIT_VREGS
    // load a constant pattern with unit-stride loads instead of splatting
    vsetvli x1, x0, e32, m1, ta, ma // configure vector to vl = VLMAX
    LA (x1, rvtest_vsc_init_e32)
    vle32.v v0, (x1)
    vle32.v v1, (x1)
    vle32.v v2, (x1)
    vle32.v v3, (x1)
    vle32.v v4, (x1)
    vle32.v v5, (x1)
    vle32.v v6, (x1)
    vle32.v v7, (x1)
    vle32.v v8, (x1)
    vle32.v v9, (x1)
    vle32.v v10, (x1)
    vle32.v v11, (x1)
    vle32.v v12, (x1)
    vle32.v v13, (x1)
    vle32.v v14, (x1)
    vle32.v v15, (x1)
    vle32.v v16, (x1)
    vle32.v v17, (x1)
    vle32.v v18, (x1)
    vle32.v v19, (x1)
    vle32.v v20, (x1)
    vle32.v v21, (x1)
    vle32.v v22, (x1)
    vle32.v v23, (x1)
    vle32.v v24, (x1)
    vle32.v v25, (x1)
    vle32.v v26, (x1)
    vle32.v v27, (x1)
    vle32.v v28, (x1)
    vle32.v v29, (x1)
    vle32.v v30, (x1)
    vle32.v v31, (x1)
    LI (x1,  (0xFEEDBEADFEEDBEAD & MASK)) // restore x1
.endm

// Context block and buffers. The offsets of v0, vs1, and the result buffer
// from rvtest_vsc_ctx must match VSC_OFF_*.
.macro RVTEST_VSC_DATA
    .p2align 4
rvtest_vsc_ctx:
    .fill VSC_CTX_BYTES, 1, 0
rvtest_vsc_v0:
    .fill VLEN_BYTES, 1, 0
rvtest_vsc_vs1:
    .fill VLEN_BYTES, 1, 0
rvtest_vsc_actual:
    .fill UDB_VLEN, 1, 0               // LMUL=8 register group
rvtest_vsc_idx:
    .fill UDB_VLEN, 1, 0               // LMUL=8 index register group
    .p2align 4
rvtest_vsc_init_e32:
    .fill (VLEN_BYTES/4), 4, 0xFEEDBEAD
    .p2align 4
rvtest_vsc_mask_scratch:
    .fill VLEN_BYTES, 1, 0
    .p2align 4
rvtest_vsc_ones:
    .fill VLEN_BYTES, 1, 0xff
    .p2align 4
rvtest_vsc_zeros:
    .fill UDB_VLEN, 1, 0               // LMUL=8 register group
    .p2align 4
rvtest_vsc_splat_d_e8:
    .fill UDB_VLEN, 1, 0x0d
    .p2align 4
rvtest_vsc_splat_d_e16:
    .fill (UDB_VLEN/2), 2, 0x0d
    .p2align 4
rvtest_vsc_splat_d_e32:
    .fill (UDB_VLEN/4), 4, 0x0d
    .p2align 4
rvtest_vsc_splat_d_e64:
    .fill (UDB_VLEN/8), 8, 0x0d
.endm

#endif // RVTEST_VECTOR_SCALAR_CHECK_H
