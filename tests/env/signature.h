# signature.h
# Signature region handling macros
# Jordan Carlin jcarlin@hmc.edu October 2025
# SPDX-License-Identifier: Apache-2.0

// RVTEST_SIGUPD(sigptr, linkreg, tempreg, sigreg, instptr, strptr)
// compares the value in sigreg with the value in memory at 0(sigptr).
// If they are different, it jumps to a failure handler whose label is formed
// from linkreg and tempreg. On success, it increments sigptr by SIG_STRIDE.
// In non-SELFCHECK mode, it simply stores sigreg to memory at 0(sigptr)
// and increments sigptr by SIG_STRIDE. instptr and strptr are included as
// .word/.dword directives so the instruction address and a pointer to the
// string can be retrieved from the failure handler.
//  _SIG_PTR - Base register for signature region
//  _LINK_REG - Link register to use for failure jump
//  _TEMP_REG - Temporary register to use for loading signature
//  _R - Register containing value to store/compare
//  _INST_PTR - label on instruction being tested (for PC reporting)
//  _STR_PTR - label to string describing the test
#ifdef RVTEST_SELFCHECK
  #define RVTEST_SIGUPD(_SIG_PTR, _LINK_REG, _TEMP_REG, _R, _INST_PTR, _STR_PTR)  \
    .option push                                           ;\
    .option norvc                                          ;\
    LREG _TEMP_REG, 0(_SIG_PTR)                            ;\
    beq _TEMP_REG, _R, 1f                                  ;\
    jal _LINK_REG, failedtest_##_LINK_REG##_##_TEMP_REG    ;\
    RVTEST_WORD_PTR _INST_PTR                              ;\
    RVTEST_WORD_PTR _STR_PTR                               ;\
    1:                                                     ;\
    addi _SIG_PTR, _SIG_PTR, SIG_STRIDE                    ;\
    .option pop
#else
  #define RVTEST_SIGUPD(_SIG_PTR, _LINK_REG, _TEMP_REG, _R, _INST_PTR, _STR_PTR)  \
    .option push                                           ;\
    .option norvc                                          ;\
    SREG _R, 0(_SIG_PTR)                                   ;\
    beq x0, x0, 1f                                         ;\
    jal _LINK_REG, failedtest_##_LINK_REG##_##_TEMP_REG    ;\
    RVTEST_WORD_PTR _INST_PTR                              ;\
    RVTEST_WORD_PTR _STR_PTR                               ;\
    1:                                                     ;\
    addi _SIG_PTR, _SIG_PTR, SIG_STRIDE                    ;\
    .option pop
#endif

// TRAP_SIGUPD(tempreg, sigreg, offset, instptr, strptr)
// Used to compare/write signatures while handling traps.
// In Self Check mode, compare reference and DUT signatures and jump to
// failedtest_trap_x7_x9 in case of a mismatch.
// In failedtest_trap_x7_x9, x7/T2 is LINK_REG & x9/T4 is TEMP_REG
// If not in Self Check mode, just store signatures to the trap signature region
#ifdef RVTEST_SELFCHECK
  #define TRAP_SIGUPD(_TMPREG, _R, _OFF, _INST_PTR, _STR_PTR)    \
    LREG _TMPREG, _OFF*REGWIDTH(T1)                             ;\
    beq  _TMPREG, _R, 2f                                        ;\
    jal  T2, failedtest_trap_x7_x9                              ;\
    RVTEST_WORD_PTR _INST_PTR                                   ;\
    RVTEST_WORD_PTR _STR_PTR                                    ;\
    .word CSR_XEPC                                              ;\
    2:                                                          ;
#else
  #define TRAP_SIGUPD(_TMPREG, _R, _OFF, _INST_PTR, _STR_PTR)    \
    SREG _R, _OFF*REGWIDTH(T1)                                  ;\
    beq  x0, x0, 2f                                             ;\
    jal  T2, failedtest_trap_x7_x9                              ;\
    RVTEST_WORD_PTR _INST_PTR                                   ;\
    RVTEST_WORD_PTR _STR_PTR                                    ;\
    .word CSR_XEPC                                              ;\
    2:                                                          ;
#endif

// RVTEST_SIGUPD_F(sigptr, linkreg, tempreg, ftempreg, sigreg, instptr, strptr)
// compares the value in sigreg with the value in memory at 0(sigptr) and the
// value in FCSR with the value in memory at SIG_STRIDE(sigptr). If either are
// different, it jumps to a failure handler whose label is formed from linkreg
// and tempreg. On success, it increments sigptr by 2*SIG_STRIDE. In non-SELFCHECK
// mode, it simply stores sigreg to memory at 0(sigptr), FCSR at SIG_STRIDE(sigptr),
// and increments sigptr by 2*SIG_STRIDE. instptr and strptr are included as
// .word/.dword directives so the instruction address and a pointer to the
// string can be retrieved from the failure handler.
//  _SIG_PTR - Base register for signature region
//  _LINK_REG - Link register to use for failure jump
//  _TEMP_REG - Temporary register to use for loading signature
//  _F_TEMP_REG - Temporary register to use for loading fp signature
//  _FR - Floating point register containing value to store/compare
//  _INST_PTR - label on instruction being tested (for PC reporting)
//  _STR_PTR - label to string describing the test
// Floating point values are stored to memory and then loaded back into integer registers
// for comparison, to avoid issues with NaN that arise from using feq. There is no way to
// directly transfer a floating point value to an integer register without Zfa when FLEN > XLEN.
#if FLEN == 128 && XLEN == 32
  #error "Q on RV32 is not supported yet."
#endif
#if FLEN > XLEN
  #ifdef RVTEST_SELFCHECK
    #define RVTEST_SIGUPD_F(_SIG_PTR, _LINK_REG, _TEMP_REG, _F_TEMP_REG, _FR, _INST_PTR, _STR_PTR)  \
      .option push                                           ;\
      .option norvc                                          ;\
      LA(_LINK_REG, scratch)                                 ;\
      FSREG _FR, 0(_LINK_REG)                                ;\
      LREG _LINK_REG, 0(_LINK_REG)                           ;\
      LREG _TEMP_REG, 0(_SIG_PTR)                            ;\
      beq _TEMP_REG, _LINK_REG, 1f                           ;\
      jal _LINK_REG, failedtest_fp_##_LINK_REG##_##_TEMP_REG ;\
      RVTEST_WORD_PTR _INST_PTR                              ;\
      RVTEST_WORD_PTR _STR_PTR                               ;\
      1:                                                     ;\
      LA(_LINK_REG, scratch)                                 ;\
      FSREG _FR, 0(_LINK_REG)                                ;\
      LREG _LINK_REG, REGWIDTH(_LINK_REG)                    ;\
      LREG _TEMP_REG, SIG_STRIDE(_SIG_PTR)                   ;\
      beq _TEMP_REG, _LINK_REG, 2f                           ;\
      jal _LINK_REG, failedtest_fp_##_LINK_REG##_##_TEMP_REG ;\
      RVTEST_WORD_PTR _INST_PTR                              ;\
      RVTEST_WORD_PTR _STR_PTR                               ;\
      2:                                                     ;\
      csrr _LINK_REG, fcsr                                   ;\
      LREG _TEMP_REG, 2*SIG_STRIDE(_SIG_PTR)                 ;\
      beq _TEMP_REG, _LINK_REG, 3f                           ;\
      jal _LINK_REG, failedtest_fflags_##_LINK_REG##_##_TEMP_REG ;\
      RVTEST_WORD_PTR _INST_PTR                              ;\
      RVTEST_WORD_PTR _STR_PTR                               ;\
      3:                                                     ;\
      addi _SIG_PTR, _SIG_PTR, 3*SIG_STRIDE                  ;\
      .option pop
  #else
    #define RVTEST_SIGUPD_F(_SIG_PTR, _LINK_REG, _TEMP_REG, _F_TEMP_REG, _FR, _INST_PTR, _STR_PTR)  \
      .option push                                           ;\
      .option norvc                                          ;\
      LA(_LINK_REG, scratch)                                 ;\
      FSREG _FR, 0(_LINK_REG)                                ;\
      LREG _LINK_REG, 0(_LINK_REG)                           ;\
      SREG _LINK_REG, 0(_SIG_PTR)                            ;\
      beq x0, x0, 1f                                         ;\
      jal _LINK_REG, failedtest_fp_##_LINK_REG##_##_TEMP_REG ;\
      RVTEST_WORD_PTR _INST_PTR                              ;\
      RVTEST_WORD_PTR _STR_PTR                               ;\
      1:                                                     ;\
      LA(_LINK_REG, scratch)                                 ;\
      FSREG _FR, 0(_LINK_REG)                                ;\
      LREG _LINK_REG, REGWIDTH(_LINK_REG)                    ;\
      SREG _LINK_REG, SIG_STRIDE(_SIG_PTR)                   ;\
      beq x0, x0, 2f                                         ;\
      jal _LINK_REG, failedtest_fp_##_LINK_REG##_##_TEMP_REG ;\
      RVTEST_WORD_PTR _INST_PTR                              ;\
      RVTEST_WORD_PTR _STR_PTR                               ;\
      2:                                                     ;\
      csrr _LINK_REG, fcsr                                   ;\
      SREG _LINK_REG, 2*SIG_STRIDE(_SIG_PTR)                 ;\
      beq x0, x0, 3f                                         ;\
      jal _LINK_REG, failedtest_fflags_##_LINK_REG##_##_TEMP_REG ;\
      RVTEST_WORD_PTR _INST_PTR                              ;\
      RVTEST_WORD_PTR _STR_PTR                               ;\
      3:                                                     ;\
      addi _SIG_PTR, _SIG_PTR, 3*SIG_STRIDE                  ;\
      .option pop
  #endif
#else
  #ifdef RVTEST_SELFCHECK
    #define RVTEST_SIGUPD_F(_SIG_PTR, _LINK_REG, _TEMP_REG, _F_TEMP_REG, _FR, _INST_PTR, _STR_PTR)  \
      .option push                                           ;\
      .option norvc                                          ;\
      LA(_LINK_REG, scratch)                                 ;\
      FSREG _FR, 0(_LINK_REG)                                ;\
      LREG _LINK_REG, 0(_LINK_REG)                           ;\
      LREG _TEMP_REG, 0(_SIG_PTR)                            ;\
      beq _TEMP_REG, _LINK_REG, 1f                           ;\
      jal _LINK_REG, failedtest_fp_##_LINK_REG##_##_TEMP_REG ;\
      RVTEST_WORD_PTR _INST_PTR                              ;\
      RVTEST_WORD_PTR _STR_PTR                               ;\
      1:                                                     ;\
      csrr _LINK_REG, fcsr                                   ;\
      LREG _TEMP_REG, SIG_STRIDE(_SIG_PTR)                   ;\
      beq _TEMP_REG, _LINK_REG, 3f                           ;\
      jal _LINK_REG, failedtest_fflags_##_LINK_REG##_##_TEMP_REG ;\
      RVTEST_WORD_PTR _INST_PTR                              ;\
      RVTEST_WORD_PTR _STR_PTR                               ;\
      3:                                                     ;\
      addi _SIG_PTR, _SIG_PTR, 2*SIG_STRIDE                  ;\
      .option pop
  #else
    #define RVTEST_SIGUPD_F(_SIG_PTR, _LINK_REG, _TEMP_REG, _F_TEMP_REG, _FR, _INST_PTR, _STR_PTR)  \
      .option push                                           ;\
      .option norvc                                          ;\
      LA(_LINK_REG, scratch)                                 ;\
      FSREG _FR, 0(_LINK_REG)                                ;\
      LREG _LINK_REG, 0(_LINK_REG)                           ;\
      SREG _LINK_REG, 0(_SIG_PTR)                            ;\
      beq x0, x0, 1f                                         ;\
      jal _LINK_REG, failedtest_fp_##_LINK_REG##_##_TEMP_REG ;\
      RVTEST_WORD_PTR _INST_PTR                              ;\
      RVTEST_WORD_PTR _STR_PTR                               ;\
      1:                                                     ;\
      csrr _LINK_REG, fcsr                                   ;\
      SREG _LINK_REG, SIG_STRIDE(_SIG_PTR)                   ;\
      beq x0, x0, 3f                                         ;\
      jal _LINK_REG, failedtest_fflags_##_LINK_REG##_##_TEMP_REG ;\
      RVTEST_WORD_PTR _INST_PTR                              ;\
      RVTEST_WORD_PTR _STR_PTR                               ;\
      3:                                                     ;\
      addi _SIG_PTR, _SIG_PTR, 2*SIG_STRIDE                  ;\
      .option pop
  #endif
#endif



// RVTEST_SIGUPD_V(cmp, sigptr, linkreg, tempreg,
//                 vtmp, mtmp, sew, offset, vreg, instptr, strptr)
//
// This macro either compares a vector register against the reference
// signature (SELFCHECK mode) or stores the vector register to the
// signature (non-SELFCHECK mode).
//
// In SELFCHECK mode:
//   1. The reference vector is loaded from memory at 0(sigptr) into vtmp.
//   2. The comparison operation cmp is executed between vreg (the register
//      under test) and the loaded reference. The cmp instruction must produce
//      a mask register mtmp where:
//         - mtmp[i] = 1  → mismatch
//         - mtmp[i] = 0  → match
//      Typical examples:
//         vmsne.vv  (for data vector comparison)
//         vmxor.mm  (for mask register comparison)
//
//   3. vfirst.m searches the mismatch mask (mtmp) for the first set bit.
//      - If no mismatches exist, vfirst.m returns -1 and execution continues.
//      - If any mismatch exists, the macro jumps to a failure handler.
//
//   4. On failure:
//      - The reference word at 0(sigptr) is loaded to tempreg.
//      - Control jumps to a failure handler label constructed from
//        linkreg and tempreg.
//      - instptr and strptr are emitted so that the failing instruction
//        address and descriptive string can be recovered.
//
//   5. On success:
//      - sigptr is advanced by offset.
//
// In non-SELFCHECK mode:
//   - The macro simply stores the vector register vreg to memory at
//     0(sigptr) using vse{sew}.v.
//   - No comparisons are performed.
//   - sigptr is advanced by offset.
//
// offset is calculated in vector-testgen.py due to the complexity of
// computing the correct signature stride for different SEW/LMUL settings.
//
// Assumptions:
//   - For mask producing instructions, the default SEW is 8.
//   - vfirst.m returns -1 if no bits are set and >=0 otherwise.
//   - The definition of base suite is testing for the first element of the vector,
//     as explained in https://github.com/riscv/riscv-arch-test/blob/act4/docs/ctp/src/v.adoc#vector-coverpoints,
//     so the macro only checks for mismatches in the first element for simplicity.
//
// Parameters:
//   _CMP        - Vector comparison instruction producing mismatch mask
//   _SIG_PTR    - Base register for signature region
//   _LINK_REG   - Link register used for failure jump
//   _TEMP_REG   - Temporary scalar register
//   _VTMP       - Temporary vector register used to load reference data
//   _MTMP       - Mask register holding mismatch results
//   _SEW        - Element width
//   _OFFSET     - Signature stride (computed in vector-testgen.py)
//   _VREG       - Vector register under test
//   _INST_PTR   - Label of instruction under test
//   _STR_PTR    - Label to descriptive string

#ifdef RVTEST_SELFCHECK
    #define RVTEST_SIGUPD_V(_CMP, _SIG_PTR, _LINK_REG, _TEMP_REG,    \
        _VTMP, _MTMP, _SEW, _OFFSET, _VREG, _INST_PTR, _STR_PTR)     \
        .option push                                                ;\
        .option norvc                                               ;\
        vle##_SEW.v _VTMP, 0(_SIG_PTR)                              ;\
        _CMP _MTMP, _VREG, _VTMP                                    ;\
        vfirst.m _TEMP_REG, _MTMP                                   ;\
        blt _TEMP_REG, x0, 2f                                       ;\
        LREG _TEMP_REG, 0(_SIG_PTR)        /* dummy instr for failed_test macro for now */ ;\
        beq  _TEMP_REG, _TEMP_REG, 1f      /* dummy instr for failed_test macro for now */ ;\
    1:                                                              ;\
        jal _LINK_REG, failedtest_##_LINK_REG##_##_TEMP_REG         ;\
        RVTEST_WORD_PTR _INST_PTR                                   ;\
        RVTEST_WORD_PTR _STR_PTR                                    ;\
    2:                                                              ;\
        addi _SIG_PTR, _SIG_PTR, _OFFSET                            ;\
        .option pop
#else
    #define RVTEST_SIGUPD_V(_CMP, _SIG_PTR, _LINK_REG, _TEMP_REG,    \
        _VTMP, _MTMP, _SEW, _OFFSET, _VREG, _INST_PTR, _STR_PTR)     \
        .option push                                                ;\
        .option norvc                                               ;\
        vse##_SEW.v _VREG, 0(_SIG_PTR)                              ;\
        nop                                                         ;\
        nop                                                         ;\
        beq x0, x0, 2f                                              ;\
        LREG _TEMP_REG, 0(_SIG_PTR)        /* dummy instr for failed_test macro for now */ ;\
        beq  _TEMP_REG, _TEMP_REG, 1f      /* dummy instr for failed_test macro for now */ ;\
    1:                                                              ;\
        jal _LINK_REG, failedtest_##_LINK_REG##_##_TEMP_REG         ;\
        RVTEST_WORD_PTR _INST_PTR                                   ;\
        RVTEST_WORD_PTR _STR_PTR                                    ;\
    2:                                                              ;\
        addi _SIG_PTR, _SIG_PTR, _OFFSET                            ;\
        .option pop
#endif


// RVTEST_SIGUPD_V_LEN(sigptr, linkreg, tempreg, maskreg, vtmp, vtmp2, mtmp, vr,
//                     maskprod_flag, masked_flag, sew, lmul, offset, instptr, strptr)
//
// Compares the vector register vreg against the reference signature stored at
// memory location 0(sigptr). The comparison is performed element-wise using
// vmsne.vv (set if neq) for data vector registers or vmxor.mm for mask vector registers,
// which must produce a mask (mtmp) indicating mismatched elements
// (1 = mismatch, 0 = match).
//
// The macro verifies correctness for:
//   1. Active elements        (i < vl and mask active if masked instruction)
//   2. Tail elements          (i >= vl), respecting vta behavior
//   3. Mask-inactive elements (i < vl and v0[i] == 0), respecting vma behavior
//
// Tail and inactive elements are checked according to vtype:
//   - If vta/vma = undisturbed, elements must match the reference exactly.
//     Note that the test initialize the whole destination register with a known pattern
//     before the instruction under test, so the reference will reflect this pattern for
//     undisturbed elements.
//   - If vta/vma = agnostic, elements may be all 1s (-1) or the the original value of the
//     destination register, in other words the reference (as explained above).
//
// On mismatch, the macro jumps to a failure handler whose label is formed from
// linkreg and tempreg. instptr and strptr are emitted as .word/.dword so that
// the failing instruction address and descriptive string can be retrieved.
//
// On success, sigptr is incremented by offset, which is calculated in vector-testgen.py
// due to the complexity of the calculations.
//
// In non-SELFCHECK mode, the macro should only update the signature and advance
// sigptr, without performing comparisons.
//
// Assumptions:
//   - The golden reference model (e.g., Sail) preserves undisturbed elements
//     exactly for vta=0 and vma=0 cases.
//   - vfirst.m returns -1 if no bits are set, and >=0 otherwise.
//
// Parameters:
//   _SIG_PTR        - Base register for signature region
//   _LINK_REG       - Link register used for failure jump
//   _TEMP_REG       - Temporary scalar register
//   _TEMP_REG2      - Secondary temporary register
//   _VTMP           - Temporary vector register used for loading reference and other vector operations
//   _MTMP           - Mask register containing mismatch results
//   _MTMP2          - Temporary mask register used for building active/tail/inactive masks
//   _VR             - Vector register under test
//   _MASKPROD_FLAG  - Immediate flag indicating whether the instruction under test is mask-producing (1) or not (0)
//   _MASKED_FLAG    - Immediate flag indicating whether the instruction under test is masked (1) or unmasked (0)
//   _VCOMPRESS_FLAG - Immediate flag indicating whether the instruction under test is vcompress.m, which changes effective vl of destination register
//                     If the instruction under test is vcompress.m, the immediate should be the number of vs1 register (e.g., v4 -> 4),
//                     and -1 if the instruction under test is not vcompress.m.
//                     The effective vl of vd of vcompress.m is the number of 1s in vs1, with respect to the original vl setting when executed.
//   _SEW            - Element width
//   _LMUL           - LMUL setting
//   _OFFSET         - Signature stride, calculated in vector-testgen.py (function writeSIGUPD_V)
//   _INST_PTR       - Label of instruction under test
//   _STR_PTR        - Label to descriptive string
//   Note: _VTMP, _MTMP, _MTMP2 cannot be v0 since v0 should be saved to preserve its mask value (in case the instruction under test is masked)

#ifdef RVTEST_SELFCHECK
    #define RVTEST_SIGUPD_V_LEN(_SIG_PTR, _LINK_REG, _TEMP_REG, _TEMP_REG2, _VTMP, _MTMP2, _MTMP, _VR, _VS1,             \
        _MASKPROD_FLAG, _MASKED_FLAG, _VCOMPRESS_FLAG, _SEW, _LMUL, _OFFSET, _INST_PTR, _STR_PTR)                                    \
        .option push                         ;                                                                      \
        .option norvc                        ;                                                                      \
        /* Save architecture state of instruction under test (vl and vtype) */                                      \
        csrr        _TEMP_REG, vl            ;                                                                      \
        csrr        _TEMP_REG2, vtype        ;                                                                      \
        /* Obtain effective vl if insstruction is vcompress.m */ \
        LI(_LINK_REG, _VCOMPRESS_FLAG)       ;   /* Load whether instr is vcompress.m which changes effective vl of vd */              \
        beqz        _LINK_REG, 0f            ;   /* If not vcompress.m, effective vl is the same as current vl, skip following */      \
        vcpop.m     _TEMP_REG, _VS1          ;   /* Count number of active elements in vs1 to get effective vl for vcompress.m */      \
    0:                                                                                                                                      \
        /* Set vl = VLMAX for full-register comparison*/                                                            \
        vsetvli     _LINK_REG, x0, e##_SEW, m##_LMUL, ta, ma ;                                                      \
        /* Load reference from signature and compute mismatch mask */                                               \
        LI(_LINK_REG, _MASKPROD_FLAG)        ;   /* Load whether instr is a mask-producing instruction */           \
        beqz        _LINK_REG, 1f            ;   /* If not mask-producing, skip to data vector comparison */        \
        /* Mask vector comparison: Load reference from signature and compute mismatch mask */                       \
        vlm.v       _VTMP, 0(_SIG_PTR)       ;   /* Load reference data with vector unit-stride mask load */        \
        vmxor.mm    _MTMP, _VR, _VTMP        ;   /* MTMP[i] = 1 if result != reference for mask registers */        \
        j           2f                       ;   /* Unconditional skip data vector comparison to active check */    \
    1:                                                                                                              \
        /* Data vector comparison: Load reference from signature and compute mismatch mask */                       \
        vle##_SEW##.v _VTMP, 0(_SIG_PTR)     ;                                                                      \
        vmsne.vv    _MTMP, _VR, _VTMP        ;   /* _MTMP[i] = 1 if result != reference */                          \
    2:                                                                                                              \
        /* Build active element mask (i < vl && v0[i] == 1) */                                                      \
        vid.v       _VTMP                    ;   /* VTMP[i] = i (element index) */                                  \
        vmsltu.vx   _MTMP2, _VTMP, _TEMP_REG ;   /* MTMP2[i] = (i < original vl) */                                 \
        LI(_LINK_REG, _MASKED_FLAG)          ;   /* Load whether instr was masked (0 = unmasked) */                 \
        beqz        _LINK_REG, 3f            ;   /* If unmasked, skip mask filtering */                             \
        vmand.mm    _MTMP2, _MTMP2, v0       ;   /* MTMP2 = Active = (i < vl) && v0[i] == 1 */                      \
    3:                                                                                                              \
        /* Check active elements mismatch */                                                                        \
        vmand.mm    _MTMP2, _MTMP2, _MTMP    ;   /* Active mismatches = active (MTMP2) && mismatch (MTMP)*/         \
        vfirst.m    _LINK_REG, _MTMP2        ;   /* Find first active mismatch index; -1 if none */                 \
        bge         _LINK_REG, x0, 10f       ;   /* If >=0, mismatch found → FAIL */                                \
        /* Build tail element mask (i >= vl) */                                                                     \
        vid.v       _VTMP                    ;   /* Recompute element indices */                                    \
        vmsltu.vx   _VTMP, _VTMP, _TEMP_REG  ;   /* VTMP[i] = (i < original vl) */                                  \
        vmnand.mm   _VTMP, _VTMP, _VTMP      ;   /* VTMP[i] = !(i < original vl) = (i >= original vl) */            \
        /* Check whether instr is a mask-producing instruction */                                                   \
        LI(_LINK_REG, _MASKPROD_FLAG)        ;   /* Load whether instr is a mask-producing instruction */           \
        bnez        _LINK_REG, 4f            ;   /* If mask-producing, tails are always treated as agnostic */      \
        /* Extract and check vta policy */                                                                          \
        srli        _LINK_REG, _TEMP_REG2, 6 ;   /* vta = vtype[6] */                                               \
        andi        _LINK_REG, _LINK_REG, 1  ;                                                                      \
        beqz        _LINK_REG, 5f            ;   /* If vta==0 (undisturbed), skip agnostic relaxation */            \
        /* Data vector tail agnostic(vta == 1) handling: all 1s in agnostic element is also legal */                \
        vmseq.vi    _MTMP2, _VR, -1          ;   /* MTMP2[i] = (VR[i] == -1) */                                     \
        vmandn.mm   _MTMP2, _VTMP, _MTMP2    ;   /* MTMP2[i] = tail && !(VR[i] == -1) → mismatch with all 1s */     \
        j           5f                       ;   /* Unconditional skip data vec agnostic handling to tail check */  \
    4:                                                                                                              \
        /* Mask vector tail agnostic handling: all 1s in agnostic element is also legal */                          \
        vmand.mm    _MTMP2, _VR, _VR         ;   /* MTMP2[i] = (VR[i] == 1) */                                      \
        vmandn.mm   _MTMP2, _VTMP, _MTMP2    ;   /* MTMP2[i] = inactive && !(VR[i] == 1) → mismatch with all 1s */  \
    5:                                                                                                              \
        /* Check tail elements mismatches */                                                                        \
        vmand.mm    _VTMP, _VTMP, _MTMP      ;   /* VTMP[i] = tail && (vd != sig) → mismatch with signature */      \
        srli        _LINK_REG, _TEMP_REG2, 6 ;   /* vta = vtype[6] */                                               \
        andi        _LINK_REG, _LINK_REG, 1  ;                                                                      \
        beqz        _LINK_REG, 6f            ;   /* If vta==0 (undisturbed), skip agnostic all 1s comparison */     \
        vmand.mm    _VTMP, _VTMP, _MTMP2     ;   /* VTMP[i] = signature mismatch && all 1s mismatch */              \
    6:                                                                                                              \
        vfirst.m    _LINK_REG, _VTMP         ;   /* Find first active mismatch index; -1 if none */                 \
        bge         _LINK_REG, x0, 10f       ;   /* If >=0, mismatch found → FAIL */                                \
        /* Build mask inactive mask */                                                                              \
        LI(_LINK_REG, _MASKED_FLAG)          ;   /* Load whether instr was masked (0 = unmasked) */                 \
        beqz        _LINK_REG, 12f           ;   /* If unmasked, no mask inactive → all checks have passed */       \
        vid.v       _VTMP                    ;   /* Recompute element indices */                                    \
        vmsltu.vx   _VTMP, _VTMP, _TEMP_REG  ;   /* MTMP2[i] = (i < original vl) */                                 \
        vmandn.mm   _VTMP, _VTMP, v0         ;   /* VTMP = Inactive = (i < vl) && (v0 == 0) */                      \
        /* Extract and check vma policy */                                                                          \
        srli        _LINK_REG, _TEMP_REG2, 7 ;   /* vma = vtype[7] */                                               \
        andi        _LINK_REG, _LINK_REG, 1  ;                                                                      \
        beqz        _LINK_REG, 8f            ;   /* If vma==0 (undisturbed), skip agnostic relaxation */            \
        /* Check whether instr is a mask-producing instruction */                                                   \
        LI(_LINK_REG, _MASKPROD_FLAG)        ;   /* Load whether instr is a mask-producing instruction */           \
        beqz        _LINK_REG, 7f            ;   /* If not mask-producing, skip to data vector comparison */        \
        /* Mask vector mask agnostic(vma == 1) handling: all 1s in agnostic element is also legal */                \
        vmand.mm    _MTMP2, _VR, _VR         ;   /* MTMP2[i] = (VR[i] == 1) */                                      \
        vmandn.mm   _MTMP2, _VTMP, _MTMP2    ;   /* MTMP2[i] = inactive && !(VR[i] == 1) → mismatch with all 1s */  \
        j           8f                       ;   /* Unconditional skip data vec agnostic to inactive check */       \
    7:                                                                                                              \
        /* Mask agnostic(vma == 1) handling: all 1s in agnostic element is also legal */                            \
        vmseq.vi    _MTMP2, _VR, -1          ;   /* MTMP2[i] = (VR[i] == -1) */                                     \
        vmandn.mm   _MTMP2, _VTMP, _MTMP2    ;   /* MTMP2[i] = inactive && !(VR[i] == -1) → mismatch with all 1s*/  \
    8:                                                                                                              \
        /* Check inactive element mismatches */                                                                     \
        vmand.mm    _VTMP, _VTMP, _MTMP      ;   /* VTMP[i] = inactive && (vd != sig) → mismatch with signature */  \
        srli        _LINK_REG, _TEMP_REG2, 7 ;   /* vma = vtype[7] */                                               \
        andi        _LINK_REG, _LINK_REG, 1  ;                                                                      \
        beqz        _LINK_REG, 9f            ;   /* If vma==0 (undisturbed), skip agnostic all 1s comparison */     \
        vmand.mm    _VTMP, _VTMP, _MTMP2     ;   /* VTMP[i] = signature mismatch && all 1s mismatch */              \
    9:                                                                                                              \
        vfirst.m    _LINK_REG, _VTMP         ;   /* Find first active mismatch index; -1 if none */                 \
        blt         _LINK_REG, x0, 12f       ;   /* If no mismatch found → PASS ALL */                              \
    10:                                                                                                             \
        /* FAIL path */                                                                                             \
        LREG        _TEMP_REG, 0(_SIG_PTR)   ;   /* Load first reference word (for debug context) */                \
        beq         _TEMP_REG, _TEMP_REG, 11f;   /* Unconditional branch to failure label (mirror SIGUPD) */        \
    11:                                                                                                             \
        jal         _LINK_REG, failedtest_##_LINK_REG##_##_TEMP_REG ;                                               \
        RVTEST_WORD_PTR _INST_PTR            ;                                                                      \
        RVTEST_WORD_PTR _STR_PTR             ;                                                                      \
    12:                                                                                                             \
        /* PASS */                                                                                                  \
        addi        _SIG_PTR, _SIG_PTR, _OFFSET;                                                                    \
        .option pop
#else
    #define RVTEST_SIGUPD_V_LEN(_SIG_PTR, _LINK_REG, _TEMP_REG, _TEMP_REG2, _VTMP, _MTMP2, _MTMP, _VR, _VS1,             \
        _MASKPROD_FLAG, _MASKED_FLAG, _VCOMPRESS_FLAG, _SEW, _LMUL, _OFFSET, _INST_PTR, _STR_PTR)                                    \
        .option push                         ;                                                                      \
        .option norvc                        ;                                                                      \
        /* Save architecture state of instruction under test (vl and vtype) */                                      \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        /* Obtain effective vl if insstruction is vcompress.m */ \
        LI(_LINK_REG, _VCOMPRESS_FLAG)            ;   /* Load whether instr is vcompress.m which changes effective vl of vd */              \
        beqz        _LINK_REG, 0f                 ;   /* If not vcompress.m, effective vl is the same as current vl, skip following */      \
        nop                                       ;   /* Count number of active elements in vs1 to get effective vl for vcompress.m */      \
    0:                                                                                                                                      \
        /* Set vl = VLMAX for full-register comparison*/                                                            \
        vsetvli     _LINK_REG, x0, e ##_SEW, m ##_LMUL, ta, ma ;                                                    \
        /* Load reference from signature and compute mismatch mask */                                               \
        LI(_LINK_REG, _MASKPROD_FLAG)        ;   /* Load whether instr is a mask-producing instruction */           \
        beqz        _LINK_REG, 1f            ;   /* If not mask-producing, skip to data vector comparison */        \
        /* Mask vector comparison: Load reference from signature and compute mismatch mask */                       \
        vsm.v       _VR, 0(_SIG_PTR)         ;   /* Load reference data with vector unit-stride mask load */        \
        nop                                  ;                                                                      \
        j           2f                       ;   /* Unconditional skip data vector comparison to active check */    \
    1:                                                                                                              \
        /* Data vector comparison: Load reference from signature and compute mismatch mask */                       \
        vse##_SEW##.v _VR, 0(_SIG_PTR)       ;                                                                      \
        nop                                  ;                                                                      \
    2:                                                                                                              \
        /* Build active element mask (i < vl && v0[i] == 1) */                                                      \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        LI(_LINK_REG, _MASKED_FLAG)          ;   /* Load whether instr was masked (0 = unmasked) */                 \
        beqz        _LINK_REG, 3f            ;   /* If unmasked, skip mask filtering */                             \
        nop                                  ;                                                                      \
    3:                                                                                                              \
        /* Check active elements mismatch */                                                                        \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        j           12f                      ;   /* Unconditional set to PASS for non-selfcheck */                  \
        /* Build tail element mask (i >= vl) */                                                                     \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        /* Check whether instr is a mask-producing instruction */                                                   \
        LI(_LINK_REG, _MASKPROD_FLAG)        ;   /* Load whether instr is a mask-producing instruction */           \
        beqz        _LINK_REG, 4f            ;   /* If not mask-producing, skip to data vector comparison */        \
        /* Extract and check vta policy */                                                                          \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        /* Mask vector tail agnostic(vta == 1) handling: all 1s in agnostic element is also legal */                \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
    4:                                                                                                              \
        /* Data vector tail agnostic(vta == 1) handling: all 1s in agnostic element is also legal */                \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
    5:                                                                                                              \
        /* Check tail elements mismatches */                                                                        \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
    6:                                                                                                              \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        /* Build mask inactive mask */                                                                              \
        LI(_LINK_REG, _MASKED_FLAG)          ;   /* Dummy instruction */                                            \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        /* Extract and check vma policy */                                                                          \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        /* Check whether instr is a mask-producing instruction */                                                   \
        LI(_LINK_REG, _MASKPROD_FLAG)        ;   /* Dummy instruction */                                            \
        nop                                  ;                                                                      \
        /* Mask vector mask agnostic(vma == 1) handling: all 1s in agnostic element is also legal */                \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
    7:                                                                                                              \
        /* Mask agnostic(vma == 1) handling: all 1s in agnostic element is also legal */                            \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
    8:                                                                                                              \
        /* Check inactive element mismatches */                                                                     \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
    9:                                                                                                              \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
    10:                                                                                                             \
        /* FAIL path */                                                                                             \
        LREG        _TEMP_REG, 0(_SIG_PTR)   ;   /* Load first reference word (for debug context) */                \
        beq         _TEMP_REG, _TEMP_REG, 11f;   /* Unconditional branch to failure label (mirror SIGUPD) */        \
    11:                                                                                                             \
        jal         _LINK_REG, failedtest_##_LINK_REG##_##_TEMP_REG ;                                               \
        RVTEST_WORD_PTR _INST_PTR            ;                                                                      \
        RVTEST_WORD_PTR _STR_PTR             ;                                                                      \
    12:                                                                                                             \
        /* PASS */                                                                                                  \
        addi        _SIG_PTR, _SIG_PTR, _OFFSET;                                                                    \
        .option pop
#endif

// Canary value to indicate bounds of signature region
#if SIG_STRIDE==8
  #define CANARY_VALUE \
      0x6F5CA309E7D4B281
  #define CANARY \
      .dword CANARY_VALUE
  #define TRAP_CANARY_VALUE \
      0xD3A91F6C8B47E25D
  #define TRAP_CANARY \
      .dword TRAP_CANARY_VALUE
#else
  #define CANARY_VALUE \
      0x6F5CA309
  #define CANARY \
      .word CANARY_VALUE
  #define TRAP_CANARY_VALUE \
      0xD3A91F6C
  #define TRAP_CANARY \
      .word TRAP_CANARY_VALUE
#endif

// Read _CSR into _R and record/check the signature
#define RVTEST_SIGUPD_CSR_RD(_SIG_PTR, _LINK_REG, _TEMP_REG, _CSR, _R, _INST_PTR, _STR_PTR) \
    CSRR(_R, _CSR)                                       ;\
    RVTEST_SIGUPD(_SIG_PTR, _LINK_REG, _TEMP_REG, _R, _INST_PTR, _STR_PTR)

// Abbreviated form with default registers
#define RVTEST_SIGUPD_CSR_READ(_CSR, _R, _INST_PTR, _STR_PTR) \
    RVTEST_SIGUPD_CSR_RD(DEFAULT_SIG_REG, DEFAULT_LINK_REG, DEFAULT_TEMP_REG, _CSR, _R, _INST_PTR, _STR_PTR)


// Write _R1 into _CSR, then read back into _R2 and record/check the signature
#define RVTEST_SIGUPD_CSR_WR(_SIG_PTR, _LINK_REG, _TEMP_REG, _CSR, _R1, _R2, _INST_PTR, _STR_PTR) \
    CSRW(_CSR, _R1)                                      ;\
    RVTEST_SIGUPD_CSR_RD(_SIG_PTR, _LINK_REG, _TEMP_REG, _CSR, _R2, _INST_PTR, _STR_PTR)

// Abbreviated form with default registers, overwrites _R with value read back
#define RVTEST_SIGUPD_CSR_WRITE(_CSR, _R, _INST_PTR, _STR_PTR) \
    RVTEST_SIGUPD_CSR_WR(DEFAULT_SIG_REG, DEFAULT_LINK_REG, DEFAULT_TEMP_REG, _CSR, _R, _R, _INST_PTR, _STR_PTR)
