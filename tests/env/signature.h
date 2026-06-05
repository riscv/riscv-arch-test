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

// RVTEST_SIGUPD_FFLAGS(sigptr, linkreg, tempreg, instptr, strptr)
// Reads fflags and compares/stores it to the signature at 0(sigptr).
// In SELFCHECK mode, compares the value in fflags with the value in memory
// at 0(sigptr) and jumps to a failure handler if different.
// In non-SELFCHECK mode, stores fflags to memory at 0(sigptr).
// In both cases, increments sigptr by SIG_STRIDE.
//  _SIG_PTR - Base register for signature region
//  _LINK_REG - Link register to use for failure jump
//  _TEMP_REG - Temporary register to use for loading signature
//  _INST_PTR - label on instruction being tested (for PC reporting)
//  _STR_PTR - label to string describing the test
#ifdef RVTEST_SELFCHECK
  #define RVTEST_SIGUPD_FFLAGS(_SIG_PTR, _LINK_REG, _TEMP_REG, _INST_PTR, _STR_PTR)  \
    .option push                                           ;\
    .option norvc                                          ;\
    csrr _LINK_REG, fflags                                 ;\
    LREG _TEMP_REG, 0(_SIG_PTR)                            ;\
    beq _TEMP_REG, _LINK_REG, 1f                           ;\
    jal _LINK_REG, failedtest_fflags_##_LINK_REG##_##_TEMP_REG ;\
    RVTEST_WORD_PTR _INST_PTR                              ;\
    RVTEST_WORD_PTR _STR_PTR                               ;\
    1:                                                     ;\
    addi _SIG_PTR, _SIG_PTR, SIG_STRIDE                    ;\
    .option pop
#else
  #define RVTEST_SIGUPD_FFLAGS(_SIG_PTR, _LINK_REG, _TEMP_REG, _INST_PTR, _STR_PTR)  \
    .option push                                           ;\
    .option norvc                                          ;\
    csrr _LINK_REG, fflags                                 ;\
    SREG _LINK_REG, 0(_SIG_PTR)                            ;\
    beq x0, x0, 1f                                         ;\
    jal _LINK_REG, failedtest_fflags_##_LINK_REG##_##_TEMP_REG ;\
    RVTEST_WORD_PTR _INST_PTR                              ;\
    RVTEST_WORD_PTR _STR_PTR                               ;\
    1:                                                     ;\
    addi _SIG_PTR, _SIG_PTR, SIG_STRIDE                    ;\
    .option pop
#endif

// RVTEST_SIGUPD_F(sigptr, linkreg, tempreg, ftempreg, sigreg, instptr, strptr)
// Checks both a floating point result register and fflags against the signature.
// Compares the float value in sigreg with the value in memory at 0(sigptr),
// then uses RVTEST_SIGUPD_FFLAGS to check fflags. When CONFIG_FLEN > UDB_MXLEN, the
// float value requires 2 signature entries (low and high words), plus 1 for
// fflags (total 3*SIG_STRIDE). When CONFIG_FLEN <= UDB_MXLEN, uses 1 entry for the
// float value plus 1 for fflags (total 2*SIG_STRIDE).
//
// On an F-only DUT with TEST_FLEN=64, CONFIG_FLEN is 32 so we take the single-
// store path. Each slot is still SIG_STRIDE (=TEST_FLEN/8) bytes wide, leaving
// 4 bytes of unused padding — harmless because the .fill reservation driven by
// SIGUPD_COUNT is already an upper bound. The scratch load uses FP_LREG so only
// the CONFIG_FLEN bits actually written by FSREG are read back.
// See tests/env/utils.h for an explanation of CONFIG_FLEN and TEST_FLEN.
//
//  _SIG_PTR - Base register for signature region
//  _LINK_REG - Link register to use for failure jump
//  _TEMP_REG - Temporary register to use for loading signature
//  _F_TEMP_REG - Temporary register to use for loading fp signature
//  _FR - Floating point register containing value to store/compare
//  _INST_PTR - label on instruction being tested (for PC reporting)
//  _STR_PTR - label to string describing the test
//
// Floating point values are stored to memory and then loaded back into integer registers
// for comparison, to avoid issues with NaN that arise from using feq. There is no way to
// directly transfer a floating point value to an integer register without Zfa when FLEN > XLEN.
#if CONFIG_FLEN == 128 && UDB_MXLEN == 32
  #error "Q on RV32 is not supported yet."
#endif
#if CONFIG_FLEN > UDB_MXLEN
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
      addi _SIG_PTR, _SIG_PTR, 2*SIG_STRIDE                  ;\
      .option pop                                            ;\
      RVTEST_SIGUPD_FFLAGS(_SIG_PTR, _LINK_REG, _TEMP_REG, _INST_PTR, _STR_PTR)
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
      addi _SIG_PTR, _SIG_PTR, 2*SIG_STRIDE                  ;\
      .option pop                                            ;\
      RVTEST_SIGUPD_FFLAGS(_SIG_PTR, _LINK_REG, _TEMP_REG, _INST_PTR, _STR_PTR)
  #endif
#else
  #ifdef RVTEST_SELFCHECK
    #define RVTEST_SIGUPD_F(_SIG_PTR, _LINK_REG, _TEMP_REG, _F_TEMP_REG, _FR, _INST_PTR, _STR_PTR)  \
      .option push                                           ;\
      .option norvc                                          ;\
      LA(_LINK_REG, scratch)                                 ;\
      FSREG _FR, 0(_LINK_REG)                                ;\
      FP_LREG _LINK_REG, 0(_LINK_REG)                        ;\
      LREG _TEMP_REG, 0(_SIG_PTR)                            ;\
      beq _TEMP_REG, _LINK_REG, 1f                           ;\
      jal _LINK_REG, failedtest_fp_##_LINK_REG##_##_TEMP_REG ;\
      RVTEST_WORD_PTR _INST_PTR                              ;\
      RVTEST_WORD_PTR _STR_PTR                               ;\
      1:                                                     ;\
      addi _SIG_PTR, _SIG_PTR, SIG_STRIDE                    ;\
      .option pop                                            ;\
      RVTEST_SIGUPD_FFLAGS(_SIG_PTR, _LINK_REG, _TEMP_REG, _INST_PTR, _STR_PTR)
  #else
    #define RVTEST_SIGUPD_F(_SIG_PTR, _LINK_REG, _TEMP_REG, _F_TEMP_REG, _FR, _INST_PTR, _STR_PTR)  \
      .option push                                           ;\
      .option norvc                                          ;\
      LA(_LINK_REG, scratch)                                 ;\
      FSREG _FR, 0(_LINK_REG)                                ;\
      FP_LREG _LINK_REG, 0(_LINK_REG)                        ;\
      SREG _LINK_REG, 0(_SIG_PTR)                            ;\
      beq x0, x0, 1f                                         ;\
      jal _LINK_REG, failedtest_fp_##_LINK_REG##_##_TEMP_REG ;\
      RVTEST_WORD_PTR _INST_PTR                              ;\
      RVTEST_WORD_PTR _STR_PTR                               ;\
      1:                                                     ;\
      addi _SIG_PTR, _SIG_PTR, SIG_STRIDE                    ;\
      .option pop                                            ;\
      RVTEST_SIGUPD_FFLAGS(_SIG_PTR, _LINK_REG, _TEMP_REG, _INST_PTR, _STR_PTR)
  #endif
#endif

// Advance _SIG_PTR by the signature stride computed from the current vl and vtype.
// The caller must set vtype.vsew appropriately before invoking this macro
// (for example via vsetvli), since the stride is derived from the runtime CSR state.
// Clobbers _TEMP_REG and _LINK_REG (both are free here after the compare).
// bytes = vl << ((vtype >> 3) & 7)  ;  bytes = (bytes + 4 + 7) & ~7
#define RVTEST_SIGUPD_V_ADVANCE(_SIG_PTR, _LINK_REG, _TEMP_REG)  \
    csrr _TEMP_REG, vl                                                   ;\
    csrr _LINK_REG, vtype                                                ;\
    srli _LINK_REG, _LINK_REG, 3                                         ;\
    andi _LINK_REG, _LINK_REG, 7                                         ;\
    sll  _TEMP_REG, _TEMP_REG, _LINK_REG                                 ;\
    addi _TEMP_REG, _TEMP_REG, 11                                        ;\
    andi _TEMP_REG, _TEMP_REG, -8                                        ;\
    add  _SIG_PTR, _SIG_PTR, _TEMP_REG

#define RVTEST_SIGUPD_V_ADVANCE_NOP \
    nop ; \
    nop ; \
    nop ; \
    nop ; \
    nop ; \
    nop ; \
    nop ; \
    nop

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
//      - sigptr is advanced by the calculated offset determined by vl and vtype.
//
// In non-SELFCHECK mode:
//   - The macro simply stores the vector register vreg to memory at
//     0(sigptr) using vse{sew}.v.
//   - No comparisons are performed.
//   - sigptr is advanced by the calculated offset.
//
// The signature stride is computed inside the macro from the current vl and
// vtype (SEW field): bytes = vl << vsew, then +4 padding, then rounded up to
// a multiple of 8.  For base suite callers vl=1; for length suite callers
// (handled by the _LEN macro below) vl is first set to VLMAX via vsetvli so
// the same formula yields VLEN*LMUL/8 bytes.
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
//   _VD_EEW     - Destination element width (for widening, 2*SEW)
//   _VREG       - Vector register under test
//   _INST_PTR   - Label of instruction under test
//   _STR_PTR    - Label to descriptive string

#ifdef RVTEST_SELFCHECK
    #define RVTEST_SIGUPD_V(_CMP, _SIG_PTR, _LINK_REG, _TEMP_REG,    \
        _VTMP, _MTMP, _VD_EEW, _VREG, _INST_PTR, _STR_PTR)           \
        .option push                                                ;\
        .option norvc                                               ;\
        vle##_VD_EEW.v _VTMP, 0(_SIG_PTR)                           ;\
        _CMP _MTMP, _VREG, _VTMP                                    ;\
        vfirst.m _TEMP_REG, _MTMP                                   ;\
        blt _TEMP_REG, x0, 2f                                       ;\
        LREG _TEMP_REG, 0(_SIG_PTR)        /* dummy instr for failed_test macro for now */ ;\
        beq  _TEMP_REG, _TEMP_REG, 1f      /* dummy instr for failed_test macro for now */ ;\
    1:                                                              ;\
        jal _LINK_REG, failedtest_vec_base_##_LINK_REG##_##_TEMP_REG         ;\
        RVTEST_WORD_PTR _INST_PTR                                   ;\
        RVTEST_WORD_PTR _STR_PTR                                    ;\
    2:                                                              ;\
        RVTEST_SIGUPD_V_ADVANCE(_SIG_PTR, _LINK_REG, _TEMP_REG)     ;\
        .option pop
#else
    #define RVTEST_SIGUPD_V(_CMP, _SIG_PTR, _LINK_REG, _TEMP_REG,    \
        _VTMP, _MTMP, _VD_EEW, _VREG, _INST_PTR, _STR_PTR)           \
        .option push                                                ;\
        .option norvc                                               ;\
        vse##_VD_EEW.v _VREG, 0(_SIG_PTR)                           ;\
        nop                                                         ;\
        nop                                                         ;\
        beq x0, x0, 2f                                              ;\
        LREG _TEMP_REG, 0(_SIG_PTR)        /* dummy instr for failed_test macro for now */ ;\
        beq  _TEMP_REG, _TEMP_REG, 1f      /* dummy instr for failed_test macro for now */ ;\
    1:                                                              ;\
        jal _LINK_REG, failedtest_vec_base_##_LINK_REG##_##_TEMP_REG         ;\
        RVTEST_WORD_PTR _INST_PTR                                   ;\
        RVTEST_WORD_PTR _STR_PTR                                    ;\
    2:                                                              ;\
        RVTEST_SIGUPD_V_ADVANCE(_SIG_PTR, _LINK_REG, _TEMP_REG)     ;\
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
// On success, sigptr is incremented by a stride computed inside the macro
// from the current vl (which has been set to VLMAX for this SEW/LMUL) and the
// vtype SEW field, so no offset operand is required from vector-testgen.
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
//   _SIG_PTR       - Base register for signature region
//   _LINK_REG      - Link register used for failure jump
//   _TEMP_REG      - Temporary scalar register
//   _TEMP_REG2     - Secondary temporary register
//   _TEMP_REG3     - Tertiary temporary register
//   _VTMP          - Temporary vector register used for loading reference and other vector operations
//   _MTMP          - Mask register containing mismatch results
//   _MTMP2         - Temporary mask register used for building active/tail/inactive masks
//   _MTMP3         - Temporary mask register used for computing a mask for when vl > SEW_MAX
//                    This takes up a disproportionate amount of calculation, so we try to avoid making this by hand
//                    if possible.
//   _VR            - Vector register under test
//   _VS1           - Vector Source 1
//   _MASKPROD_FLAG - Immediate flag indicating whether the instruction under test is mask-producing (1) or not (0)
//   _MASKED_FLAG   - Immediate flag indicating whether the instruction under test is masked (1) or unmasked (0)
//   _VCOMPRESS_FLAG - Immediate flag indicating whether the instruction under test is vcompress.m (1) or not (0),
//                     which changes effective vl of destination register.
//                     The effective vl of vd of vcompress.m is the number of 1s in vs1, with respect to the original vl setting when executed.
//   _VD_EEW        - Destination element width (for widening, 2*SEW)
//   _LMUL          - LMUL setting
//   _SCALAR_DST_FLAG - 1 if only element 0 is written (vmv.s.x, reductions); 0 otherwise.
//                    When 1, the saved vl is overridden to 1 so only element 0 is treated
//                    as active and elements 1..VLMAX-1 receive the tail-agnostic relaxation.
//   _INST_PTR      - Label of instruction under test
//   _STR_PTR       - Label to descriptive string
//   Note: _VTMP, _MTMP, _MTMP2 cannot be v0 since v0 should be saved to preserve its mask value (in case the instruction under test is masked)

#ifdef RVTEST_SELFCHECK
    #define RVTEST_SIGUPD_V_LEN(_SIG_PTR, _LINK_REG, _TEMP_REG, _TEMP_REG2, _TEMP_REG3, _VTMP, _MTMP3, _MTMP2, _MTMP, _VR,  \
        _VS1, _MASKPROD_FLAG, _MASKED_FLAG, _VCOMPRESS_FLAG, _VD_EEW, _LMUL, _SCALAR_DST_FLAG, _INST_PTR, _STR_PTR) \
        .option push                         ;                                                                      \
        .option norvc                        ;                                                                      \
        /* Save architecture state of instruction under test (vl and vtype) */                                      \
        csrr        _TEMP_REG2, vtype        ;                                                                      \
        /* vl can be loaded in 3 distinct ways */ \
        .if (_SCALAR_DST_FLAG==1) ;\
            /* For scalar-dst instructions (vmv.s.x, reductions) only element 0 is written. */                          \
            /* Override the saved vl to 1 so the active mask covers only element 0 and     */                           \
            /* elements 1..VLMAX-1 are treated as tail, getting the vta-agnostic relaxation.*/                          \
            li          _TEMP_REG, 1             ;                                                                      \
        .elseif (_VCOMPRESS_FLAG == 1) ; \
            vcpop.m _TEMP_REG, _VS1 ; /* Count number of active elements in vs1 to get effective vl for vcompress.m */ \
        .else; \
            csrr _TEMP_REG, vl ;\
        .endif ; \
        /* Set vl = VLMAX for full-register comparison*/                                                            \
        vsetvli     _LINK_REG, x0, e##_VD_EEW, m##_LMUL, ta, ma ;                                                   \
        /* Load reference from signature and compute mismatch mask */                                               \
        .if (_MASKPROD_FLAG == 1); \
            /* Mask vector comparison: Load reference from signature and compute mismatch mask */                       \
            vlm.v       _VTMP, 0(_SIG_PTR)       ;   /* Load reference data with vector unit-stride mask load */        \
            vmxor.mm    _MTMP, _VR, _VTMP        ;   /* MTMP[i] = 1 if result != reference for mask registers */        \
        .else; \
            /* Data vector comparison: Load reference from signature and compute mismatch mask */                       \
            vle##_VD_EEW##.v _VTMP, 0(_SIG_PTR)     ;                                                                   \
            vmsne.vv    _MTMP, _VR, _VTMP        ;   /* _MTMP[i] = 1 if result != reference */                          \
        .endif; \
        /* Build active element mask (i < vl && v0[i] == 1). This approach will not work if  */ \
        /* vl > SEW_MAX because the rs1 input to vmsltu.vx will get truncated, so its possible we have */ \
        /* to calculate the hard way. vl cannot exceed SEW_MAX for SEW > 16 */                  \
        .if (_VD_EEW <= 16); \
            LI          (_LINK_REG, (1 << _VD_EEW))         ; \
            bge         _TEMP_REG, _LINK_REG, 4f ; \
        .endif; \
        vid.v       _VTMP                    ;   /* VTMP[i] = i (element index) */                                  \
        vmsltu.vx   _MTMP3, _VTMP, _TEMP_REG ;   /* MTMP2[i] = (i < original vl) */                                 \
        j 5f ; \
    4: ;\
        /* Calculate the mask by hand:  */ \
        /*   1: Calculate the bits of the mask of the byte between where the zeros and ones meet */ \
        /*         i.e. the selected byte 00000000[00011111]11111111 */ \
        /*   2: Place this byte in the first element of an sew = 8 vector register that is zeros otherwise  */ \
        /*         Notice that this value also is from the selected byte upwards in the desired register */ \
        /*   3: Use vslideup to slide this value into the correct place in a vector register that is all ones */ \
        /*         This yields the desired result because the slide doesn't touch the ones below the bottom of the slide */ \
        /*    e.g. vslideup 11111111, 00000011, 3 --> 00011|111 (here sew = 1 for simplicity, */ \
        /*           and | is where the slide splits the registers) */ \
        vsetvli _LINK_REG, x0, e8, m1, ta, ma ;  /* A mask has lmul = 1, so calculate with lmul = 1 */                                                 \
        vmv.v.i _VTMP, 0; /* Zero out _VTMP, so that we can place the desired value in the first bytes */ \
        /* To move into the first byte, we need to move with tail undisturbed into vl = 1 */ \
        li _TEMP_REG3, 1; /* vl = 1 */ \
        vsetvli x0, _TEMP_REG3, e8, m1, tu, ma ;  /* Set VL = 1 */                                                 \
        /* Calculate the bits in the element bordering zeros and ones in the mask */ \
        andi _LINK_REG, _TEMP_REG, 0x7; /* _LINK_REG = vl & 0x7 */ \
        sll _LINK_REG, _TEMP_REG3, _LINK_REG; /* _LINK_REG = 1 << LINK_REG */ \
        addi _LINK_REG, _LINK_REG, -1; /* _LINK_REG -= 1 */\
        /* As, v1 = 1, this sets only the first element of vtmp to 1 */ \
        vmv.v.x _VTMP, _LINK_REG; \
        /* Return to a full vector register */ \
        vsetvli _LINK_REG, x0, e8, m1, ta, ma ;                                                   \
        /* Set the target to be all ones at the start */ \
        LI(_LINK_REG, 0xff); \
        vmv.v.x _MTMP3, _LINK_REG;\
        /* Calculate the number of elements to slide _VTMP up */ \
        srli _TEMP_REG3, _TEMP_REG, 3; /* _TEMP_REG = _TEMP_REG >> 3 (divides by 8) */ \
        vslideup.vx _MTMP3, _VTMP, _TEMP_REG3; /* Slide Up By _TEMP_REG3. rs1 is NOT truncated to SEW bytes for this instruction */ \
        vsetvli _LINK_REG, x0, e##_VD_EEW, m##_LMUL, ta, ma ; /* Return to the previous vector settings */                                \
    5: ;\
        .if (_MASKED_FLAG == 1); \
            /* Filter the active element mask, if the operation was masked */ \
            vmand.mm  _MTMP2, _MTMP3, v0       ;   /* MTMP2 = Active = (i < vl) && v0[i] == 1 */                      \
        .else ; \
            /* (vmv.v.v would generate an exception because _MTMP3 and _MTMP2 are not necessarily aligned for lmul) */ \
            vmand.mm _MTMP2, _MTMP3, _MTMP3; /* Move the base element mask into _MTMP2 */ \
        .endif; \
        /* Check active elements mismatch */                                                                        \
        vmand.mm    _MTMP2, _MTMP2, _MTMP    ;   /* Active mismatches = active (MTMP2) && mismatch (MTMP)*/         \
        vfirst.m    _LINK_REG, _MTMP2        ;   /* Find first active mismatch index; -1 if none */                 \
        bge         _LINK_REG, x0, 10f       ;   /* If >=0, mismatch found → FAIL */                                \
        /* Build tail element mask (i >= vl), _MTMP3 Contains the Base Mask */                                                                     \
        vmnand.mm   _VTMP, _MTMP3, _MTMP3      ;   /* VTMP[i] = !base = tail */            \
        /* Check whether instr is a mask-producing instruction */                                                                      \
        .if (_MASKPROD_FLAG == 1); \
            /* Mask vector tail agnostic(vta == 1) handling: all 1s in agnostic element is also legal */                \
            vmv.v.v      _MTMP2, _VR              ;   /* MTMP2[i] = (VR[i] == 1) */                                      \
            vmandn.mm   _MTMP2, _VTMP, _MTMP2    ;   /* MTMP2[i] = tail && !(VR[i] == 1) → mismatch with all 1s */  \
            /* Check tail elements mismatches */                                                                        \
            vmand.mm    _VTMP, _VTMP, _MTMP      ;   /* VTMP[i] = tail && (vd != sig) → mismatch with signature */      \
            vmand.mm    _VTMP, _VTMP, _MTMP2     ;   /* VTMP[i] = signature mismatch && not all ones */            \
            /* In the Mask Producing case, we are allowed to compute the mask as if vl = vlmax, we can safely clobber _MTMP2 now */        \
            RVTEST_SIGUPD_V_ADVANCE(_SIG_PTR, _LINK_REG, _TEMP_REG3);                                                                      \
            vlm.v _MTMP2, 0(_SIG_PTR);      /* Load the value calculated at vlmax */                                                       \
            vmxor.mm _MTMP2, _MTMP2, _VR;   /* _MTMP2[i] = (vlmax_calculation[i] != _VR[i]) */                                             \
            vmand.mm _VTMP, _VTMP, _MTMP2 ; /* VTMP[i] = signature mismatch (vlmax) && signature mismatch (normal) && all ones mismatch */ \
        .else; \
            /* Extract and check vta policy */                                                                          \
            srli        _LINK_REG, _TEMP_REG2, 6 ;   /* vta = vtype[6] */                                               \
            andi        _LINK_REG, _LINK_REG, 1  ;                                                                      \
            beqz        _LINK_REG, 1f            ;   /* If vta==0 (undisturbed), skip agnostic relaxation */            \
            /* Data vector tail agnostic(vta == 1) handling: all 1s in agnostic element is also legal */                \
            vmseq.vi    _MTMP2, _VR, -1          ;   /* MTMP2[i] = (VR[i] == -1) */                                     \
            vmandn.mm   _MTMP2, _VTMP, _MTMP2    ;   /* MTMP2[i] = tail && !(VR[i] == -1) → mismatch with all 1s */     \
        1: ;\
            /* Check tail elements mismatches */                                                                        \
            vmand.mm    _VTMP, _VTMP, _MTMP      ;   /* VTMP[i] = tail && (vd != sig) → mismatch with signature */      \
            beqz        _LINK_REG, 2f            ;   /* If vta==0 (undisturbed), skip agnostic all 1s comparison */    \
            vmand.mm    _VTMP, _VTMP, _MTMP2     ;   /* VTMP[i] = signature mismatch && all 1s mismatch */              \
        2: ;\
        .endif; \
        /* Now analyze VTMP to find a mismatch */ \
        vfirst.m    _LINK_REG, _VTMP         ;   /* Find first active mismatch index; -1 if none */                 \
        bge         _LINK_REG, x0, 20f       ;   /* If >=0, mismatch found → FAIL */                                \
        .if (_MASKED_FLAG == 0); \
            j 12f; /* If unmasked, no mask inactive → all checks have passed */ \
        .else; \
            /* Build mask inactive mask */                                                                              \
            vmandn.mm   _VTMP, _MTMP3, v0        ;   /* VTMP = base && (v0 == 0) = inactive */                      \
            /* Extract and check vma policy */                                                                          \
            srli        _LINK_REG, _TEMP_REG2, 7 ;   /* vma = vtype[7] */                                               \
            andi        _LINK_REG, _LINK_REG, 1  ;                                                                      \
            beqz        _LINK_REG, 3f            ;   /* If vma==0 (undisturbed), skip agnostic relaxation */            \
            .if (_MASKPROD_FLAG == 1); \
                /* Mask vector mask agnostic(vma == 1) handling: all 1s in agnostic element is also legal */                \
                vmv.v.v      _MTMP2, _VR              ;   /* MTMP2[i] = (VR[i] == 1) */                                      \
                vmandn.mm   _MTMP2, _VTMP, _MTMP2    ;   /* MTMP2[i] = inactive && !(VR[i] == 1) → mismatch with all 1s */  \
            .else; \
                /* Mask agnostic(vma == 1) handling: all 1s in agnostic element is also legal */                            \
                vmseq.vi    _MTMP2, _VR, -1          ;   /* MTMP2[i] = (VR[i] == -1) */                                     \
                vmandn.mm   _MTMP2, _VTMP, _MTMP2    ;   /* MTMP2[i] = inactive && !(VR[i] == -1) → mismatch with all 1s*/  \
            .endif; \
        3: \
            /* Check inactive element mismatches */                                                                     \
            vmand.mm    _VTMP, _VTMP, _MTMP      ;   /* VTMP[i] = inactive && (vd != sig) → mismatch with signature */  \
            srli        _LINK_REG, _TEMP_REG2, 7 ;   /* vma = vtype[7] */                                               \
            andi        _LINK_REG, _LINK_REG, 1  ;                                                                      \
            beqz        _LINK_REG, 4f            ;   /* If vma==0 (undisturbed), skip agnostic all 1s comparison */     \
            vmand.mm    _VTMP, _VTMP, _MTMP2     ;   /* VTMP[i] = signature mismatch && all 1s mismatch */              \
        4:                                                                                                              \
            vfirst.m    _LINK_REG, _VTMP         ;   /* Find first active mismatch index; -1 if none */                 \
            blt         _LINK_REG, x0, 12f       ;   /* If no mismatch found → PASS ALL */                              \
        .endif; \
    30:                                                                                                             \
        /* mask region FAIL path, has to come right after mask region checks */                                     \
        vsetvli     _LINK_REG, x0, e##_VD_EEW, m1, ta, ma ;  /* Set LMUL=1 to prevent vmv.v.v trapping */           \
        vmv.v.v     _VTMP, _VTMP             ;   /* Copy mismatch mask: keep fail path depth constant for debug */  \
        vsetvli     _LINK_REG, x0, e##_VD_EEW, m##_LMUL, ta, ma ;  /* Restore original LMUL */                      \
        vfirst.m    _LINK_REG, _VTMP         ;   /* Find first active mismatch index again for failure reporting */ \
        vsetvl      _TEMP_REG, _TEMP_REG, _TEMP_REG2 ;  /* Restore original vl and vtype for failure reporting */   \
        mv          _TEMP_REG2, _LINK_REG    ;   /* Copy mismatch index: keep fail path depth constant for debug */ \
        LREG        _TEMP_REG, 0(_SIG_PTR)   ;   /* Load first reference word (for debug context) */                \
        j           31f                      ;   /* Unconditional branch to failure label (mirror SIGUPD) */        \
    31:                                                                                                             \
        jal         _LINK_REG, failedtest_vec_mask_##_LINK_REG##_##_TEMP_REG ;                                      \
        RVTEST_WORD_PTR _INST_PTR            ;                                                                      \
        RVTEST_WORD_PTR _STR_PTR             ;                                                                      \
    10:                                                                                                             \
        /* active region FAIL path */                                                                               \
        vsetvli     _LINK_REG, x0, e##_VD_EEW, m1, ta, ma ;  /* Set LMUL=1 to prevent vmv.v.v trapping */           \
        vmv.v.v     _MTMP2, _MTMP2           ;   /* Copy mismatch mask: keep fail path depth constant for debug */  \
        vsetvli     _LINK_REG, x0, e##_VD_EEW, m##_LMUL, ta, ma ;  /* Restore original LMUL */                      \
        vfirst.m    _LINK_REG, _MTMP2        ;   /* Find first active mismatch index again for failure reporting */ \
        vsetvl      _TEMP_REG, _TEMP_REG, _TEMP_REG2 ;  /* Restore original vl and vtype for failure reporting */   \
        mv          _TEMP_REG2, _LINK_REG    ;   /* Copy mismatch index: keep fail path depth constant for debug */ \
        LREG        _TEMP_REG, 0(_SIG_PTR)   ;   /* Load first reference word (for debug context) */                \
        j           11f                      ;   /* Unconditional branch to failure label (mirror SIGUPD) */        \
    11:                                                                                                             \
        jal         _LINK_REG, failedtest_vec_active_##_LINK_REG##_##_TEMP_REG ;                                    \
        RVTEST_WORD_PTR _INST_PTR            ;                                                                      \
        RVTEST_WORD_PTR _STR_PTR             ;                                                                      \
    20:                                                                                                             \
        /* tail region FAIL path */                                                                                 \
        vsetvli     _LINK_REG, x0, e##_VD_EEW, m1, ta, ma ;  /* Set LMUL=1 to prevent vmv.v.v trapping */           \
        vmv.v.v     _VTMP, _VTMP             ;   /* Copy mismatch mask: keep fail path depth constant for debug */  \
        vsetvli     _LINK_REG, x0, e##_VD_EEW, m##_LMUL, ta, ma ;  /* Restore original LMUL */                      \
        vfirst.m    _LINK_REG, _VTMP         ;   /* Find first active mismatch index again for failure reporting */ \
        vsetvl      _TEMP_REG, _TEMP_REG, _TEMP_REG2 ;  /* Restore original vl and vtype for failure reporting */   \
        mv          _TEMP_REG2, _LINK_REG    ;   /* Copy mismatch index: keep fail path depth constant for debug */ \
        LREG        _TEMP_REG, 0(_SIG_PTR)   ;   /* Load first reference word (for debug context) */                \
        j           21f                      ;   /* Unconditional branch to failure label (mirror SIGUPD) */        \
    21:                                                                                                             \
        jal         _LINK_REG, failedtest_vec_tail_##_LINK_REG##_##_TEMP_REG ;                                      \
        RVTEST_WORD_PTR _INST_PTR            ;                                                                      \
        RVTEST_WORD_PTR _STR_PTR             ;                                                                      \
    12:                                                                                                             \
        /* PASS */                                                                                                  \
        RVTEST_SIGUPD_V_ADVANCE(_SIG_PTR, _LINK_REG, _TEMP_REG)                                                    ;\
        .option pop
#else
    #define RVTEST_SIGUPD_V_LEN(_SIG_PTR, _LINK_REG, _TEMP_REG, _TEMP_REG2, _TEMP_REG3, _VTMP, _MTMP3, _MTMP2, _MTMP, _VR,  \
        _VS1, _MASKPROD_FLAG, _MASKED_FLAG, _VCOMPRESS_FLAG, _VD_EEW, _LMUL, _SCALAR_DST_FLAG, _INST_PTR, _STR_PTR) \
        .option push                         ;                                                                      \
        .option norvc                        ;                                                                      \
        /* Save architecture state of instruction under test (vl and vtype) */                                      \
        nop                                  ;   /* _TEMP_REG2 load */                                              \
        nop                                  ;   /* _TEMP_REG load */                                               \
        /* Set vl = VLMAX for full-register comparison*/                                                            \
        vsetvli     _LINK_REG, x0, e ##_VD_EEW, m ##_LMUL, ta, ma ;                                                 \
        /* Load reference from signature and compute mismatch mask */                                               \
        .if (_MASKPROD_FLAG == 1) ; \
            /* Mask vector comparison: Load reference from signature and compute mismatch mask */                       \
            vsm.v       _VR, 0(_SIG_PTR)         ;   /* Load reference data with vector unit-stride mask load */        \
            nop                                  ;                                                                      \
        .else; \
            /* Data vector comparison: Load reference from signature and compute mismatch mask */                       \
            vse##_VD_EEW##.v _VR, 0(_SIG_PTR)    ;                                                                   \
            nop                                  ;                                                                      \
        .endif; \
        /* Build active element mask */                                                      \
        .if (_VD_EEW <= 16); \
            LI          (_LINK_REG, (1 << _VD_EEW))         ; \
            bge         _TEMP_REG, _LINK_REG, 4f ; \
        .endif; \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
    4: /* Comments provided for context into where we are relative to the self-checking macro */ \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        /* To move into the first byte, we need to move with tail undisturbed into vl = 1 */ \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        /* Calculate the bits in the element bordering zeros and ones in the mask */ \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        /* As, v1 = 1, this sets only the first element of vtmp to 1 */ \
        nop                                  ;                                                                      \
        /* Return to a full vector register */ \
        nop                                  ;                                                                      \
        /* Set the target to be all ones at the start */ \
        LI(_LINK_REG, 0xff)                                  ;                                                                      \
        nop                                  ;                                                                      \
        /* Calculate the number of elements to slide _VTMP up */ \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        .if (_MASKED_FLAG == 1) ; \
            nop                                  ;                                                                      \
        .else ;\
            nop                                  ;                                                                      \
        .endif ;\
        /* Check active elements mismatch */                                                                        \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        j           12f                      ;   /* Unconditional set to PASS for non-selfcheck */                  \
        /* Build tail element mask (i >= vl) */                                                                     \
        nop                                  ;                                                                      \
        /* Check whether instr is a mask-producing instruction */                                                   \
        .if (_MASKPROD_FLAG == 1) ;\
            /* Mask vector tail agnostic(vta == 1) handling: all 1s in agnostic element is also legal */                \
            nop; \
            nop; \
            /* Check tail elements mismatches */                                                                        \
            nop; \
            nop; \
            /* In the Mask Producing case, we are allowed to compute the mask as if vl = vlmax, we can safely clobber _MTMP2 now */       \
            RVTEST_SIGUPD_V_ADVANCE_NOP ; \
            nop; \
            nop; \
            nop; \
        .else ;\
            /* Extract and check vta policy */                                                                          \
            nop                                  ;                                                                      \
            nop                                  ;                                                                      \
            nop                                  ;                                                                      \
            /* Data vector tail agnostic(vta == 1) handling: all 1s in agnostic element is also legal */                \
            nop                                  ;                                                                      \
            nop                                  ;                                                                      \
        1: ;\
            /* Check tail elements mismatches */                                                                        \
            nop                                  ;                                                                      \
            nop                                  ;                                                                      \
            nop                                  ;                                                                      \
        2:  ;\
        .endif ;\
        /* Now analyze VTMP to find a mismatch */ \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        .if (_MASKED_FLAG == 0); \
            nop; \
        .else; \
            /* Build mask inactive mask */                                                                              \
            nop                                  ;                                                                      \
            /* Extract and check vma policy */                                                                          \
            nop                                  ;                                                                      \
            nop                                  ;                                                                      \
            nop                                  ;                                                                      \
            .if (_MASKPROD_FLAG == 1); \
                /* Mask vector mask agnostic(vma == 1) handling: all 1s in agnostic element is also legal */                \
                nop                                  ;                                                                      \
                nop                                  ;                                                                      \
            .else;\
                /* Mask agnostic(vma == 1) handling: all 1s in agnostic element is also legal */                            \
                nop                                  ;                                                                      \
                nop                                  ;                                                                      \
            .endif;\
        3: ; \
            /* Check inactive element mismatches */                                                                     \
            nop                                  ;                                                                      \
            nop                                  ;                                                                      \
            nop                                  ;                                                                      \
            nop                                  ;                                                                      \
            nop                                  ;                                                                      \
        4: ; \
            nop                                  ;                                                                      \
            nop                                  ;                                                                      \
        .endif; \
    30:                                                                                                             \
        /* mask region FAIL path, has to come right after mask region checks */                                     \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        LREG        _TEMP_REG, 0(_SIG_PTR)   ;   /* Load first reference word (for debug context) */                \
        j           31f                      ;   /* Unconditional branch to failure label (mirror SIGUPD) */        \
    31:                                                                                                             \
        jal         _LINK_REG, failedtest_vec_mask_##_LINK_REG##_##_TEMP_REG ;                                      \
        RVTEST_WORD_PTR _INST_PTR            ;                                                                      \
        RVTEST_WORD_PTR _STR_PTR             ;                                                                      \
    10:                                                                                                             \
        /* active region FAIL path */                                                                               \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        LREG        _TEMP_REG, 0(_SIG_PTR)   ;   /* Load first reference word (for debug context) */                \
        j           11f                      ;   /* Unconditional branch to failure label (mirror SIGUPD) */        \
    11:                                                                                                             \
        jal         _LINK_REG, failedtest_vec_active_##_LINK_REG##_##_TEMP_REG ;                                    \
        RVTEST_WORD_PTR _INST_PTR            ;                                                                      \
        RVTEST_WORD_PTR _STR_PTR             ;                                                                      \
    20:                                                                                                             \
        /* tail region FAIL path */                                                                                 \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        nop                                  ;                                                                      \
        LREG        _TEMP_REG, 0(_SIG_PTR)   ;   /* Load first reference word (for debug context) */                \
        j           21f                      ;   /* Unconditional branch to failure label (mirror SIGUPD) */        \
    21:                                                                                                             \
        jal         _LINK_REG, failedtest_vec_tail_##_LINK_REG##_##_TEMP_REG ;                                      \
        RVTEST_WORD_PTR _INST_PTR            ;                                                                      \
        RVTEST_WORD_PTR _STR_PTR             ;                                                                      \
    12:                                                                                                             \
        /* PASS */                                                                                                  \
        RVTEST_SIGUPD_V_ADVANCE(_SIG_PTR, _LINK_REG, _TEMP_REG)                                                    ;\
        .option pop
#endif

#ifdef RVTEST_SELFCHECK
    #define RVTEST_SIGUPD_VLMAX_MASK_PROD(_SIG_PTR, _LINK_REG, _TEMP_REG, _VR, _VD_EEW, _LMUL) \
        .option push                         ;                                                 \
        .option norvc                        ;                                                 \
        nop                                  ;                                                 \
        nop                                  ;                                                 \
        RVTEST_SIGUPD_V_ADVANCE_NOP          ;                                                 \
        .option pop
#else
    #define RVTEST_SIGUPD_VLMAX_MASK_PROD(_SIG_PTR, _LINK_REG, _TEMP_REG, _VR, _VD_EEW, _LMUL) \
        .option push                                            ;                              \
        .option norvc                                           ;                              \
        vsetvli     _LINK_REG, x0, e##_VD_EEW, m##_LMUL, ta, ma ;                              \
        vsm.v _VR, 0(_SIG_PTR)                                  ;                              \
        RVTEST_SIGUPD_V_ADVANCE(_SIG_PTR, _LINK_REG, _TEMP_REG) ;                              \
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
