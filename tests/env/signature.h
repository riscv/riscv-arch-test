# signature.h
# Signature region handling macros
# Jordan Carlin jcarlin@hmc.edu October 2025
# SPDX-License-Identifier: Apache-2.0

// RVTEST_SIGUPD(sigptr, linkreg, tempreg, sigreg, strptr)
// compares the value in sigreg with the value in memory at 0(sigptr).
// If they are different, it jumps to a failure handler whose label is formed
// from linkreg and tempreg. On success, it increments sigptr by SIG_STRIDE.
// In non-SELFCHECK mode, it simply stores sigreg to memory at 0(sigptr)
// and increments sigptr by SIG_STRIDE. strptr is included as a .word/.dword
// directive so a pointer to the string can be retrieved from the failure handler.
//  _SIG_PTR - Base register for signature region
//  _LINK_REG - Link register to use for failure jump
//  _TEMP_REG - Temporary register to use for loading signature
//  _R - Register containing value to store/compare
//  _STR_PTR - label to string describing the test
#ifdef RVTEST_SELFCHECK
  #define RVTEST_SIGUPD(_SIG_PTR, _LINK_REG, _TEMP_REG, _R, _STR_PTR)  \
    LREG _TEMP_REG, 0(_SIG_PTR)                            ;\
    beq _TEMP_REG, _R, 1f                                  ;\
    jal _LINK_REG, failedtest_##_LINK_REG##_##_TEMP_REG    ;\
    RVTEST_WORD_PTR _STR_PTR                               ;\
    1:                                                     ;\
    addi _SIG_PTR, _SIG_PTR, SIG_STRIDE
#else
  #define RVTEST_SIGUPD(_SIG_PTR, _LINK_REG, _TEMP_REG, _R, _STR_PTR)  \
    SREG _R, 0(_SIG_PTR)                                   ;\
    beq x0, x0, 1f                                         ;\
    jal _LINK_REG, failedtest_##_LINK_REG##_##_TEMP_REG    ;\
    RVTEST_WORD_PTR _STR_PTR                               ;\
    1:                                                     ;\
    addi _SIG_PTR, _SIG_PTR, SIG_STRIDE
#endif

// RVTEST_SIGUPD_NOPS is the same length as RVTEST_SIGUPD but is filled with nops
#if __riscv_xlen == 64
  #define RVTEST_SIGUPD_NOPS \
    nop ;\
    nop ;\
    nop ;\
    nop ;\
    nop
#else
  #define RVTEST_SIGUPD_NOPS \
    nop ;\
    nop ;\
    nop ;\
    nop ;\
    nop ;\
    nop
#endif

// TRAP_SIGUPD(tempreg, offset)
// Used to compare/write signatures while handling traps.
// In Self Check mode, compare reference and DUT signatures and jump to
// test_failure in case of a mismatch.
// If not in Self Check mode, just store the signatures to the signature region
// **TODO: This requires some further changes for proper error reporting
#ifdef RVTEST_SELFCHECK
  #define TRAP_SIGUPD(_TMPREG, _OFF)                         \
    LREG       _TMPREG, _OFF*REGWIDTH(T1)                   ;\
    beq        _TMPREG, T3, 2f                              ;\
    jal  T2, failedtest_x5_x4                               ;\
    2:                                                      ;
#else
  #define TRAP_SIGUPD(_TMPREG, _OFF)                         \
    SREG       _TMPREG,   _OFF*REGWIDTH(T1)                 ;\
    nop                                                     ;\
    nop                                                     ;
#endif

// RVTEST_SIGUPD_F(sigptr, linkreg, tempreg, ftempreg, sigreg, strptr)
// compares the value in sigreg with the value in memory at 0(sigptr) and the
// value in FCSR with the value in memory at SIG_STRIDE(sigptr). If either are
// different, it jumps to a failure handler whose label is formed from linkreg
// and tempreg. On success, it increments sigptr by 2*SIG_STRIDE. In non-SELFCHECK
// mode, it simply stores sigreg to memory at 0(sigptr), FCSR at SIG_STRIDE(sigptr),
// and increments sigptr by 2*SIG_STRIDE. strptr is included as a .word/.dword
// directive so a pointer to the string can be retrieved from the failure handler.
//  _SIG_PTR - Base register for signature region
//  _LINK_REG - Link register to use for failure jump
//  _TEMP_REG - Temporary register to use for loading signature
//  _F_TEMP_REG - Temporary register to use for loading fp signature
//  _FR - Floating point register containing value to store/compare
//  _STR_PTR - label to string describing the test
// Floating point values are stored to memory and then loaded back into integer registers
// for comparison, to avoid issues with NaN that arise from using feq. There is no way to
// directly transfer a floating point value to an integer register without Zfa when FLEN > XLEN.
#if FLEN == 128 && XLEN == 32
  #error "Q on RV32 is not supported yet."
#endif
#if FLEN > XLEN
  #ifdef RVTEST_SELFCHECK
    #define RVTEST_SIGUPD_F(_SIG_PTR, _LINK_REG, _TEMP_REG, _F_TEMP_REG, _FR, _STR_PTR)  \
      LA(_LINK_REG, scratch)                                 ;\
      FSREG _FR, 0(_LINK_REG)                                ;\
      LREG _LINK_REG, 0(_LINK_REG)                           ;\
      LREG _TEMP_REG, 0(_SIG_PTR)                            ;\
      beq _TEMP_REG, _LINK_REG, 1f                           ;\
      jal _LINK_REG, failedtest_##_LINK_REG##_##_TEMP_REG    ;\
      RVTEST_WORD_PTR _STR_PTR                               ;\
      1:                                                     ;\
      LA(_LINK_REG, scratch)                                 ;\
      LREG _LINK_REG, REGWIDTH(_LINK_REG)                    ;\
      LREG _TEMP_REG, SIG_STRIDE(_SIG_PTR)                   ;\
      beq _TEMP_REG, _LINK_REG, 2f                           ;\
      jal _LINK_REG, failedtest_##_LINK_REG##_##_TEMP_REG    ;\
      RVTEST_WORD_PTR _STR_PTR                               ;\
      2:                                                     ;\
      csrr _LINK_REG, fcsr                                   ;\
      LREG _TEMP_REG, 2*SIG_STRIDE(_SIG_PTR)                 ;\
      beq _TEMP_REG, _LINK_REG, 3f                           ;\
      jal _LINK_REG, failedtest_##_LINK_REG##_##_TEMP_REG    ;\
      RVTEST_WORD_PTR _STR_PTR                               ;\
      3:                                                     ;\
      addi _SIG_PTR, _SIG_PTR, 3*SIG_STRIDE
  #else
    #define RVTEST_SIGUPD_F(_SIG_PTR, _LINK_REG, _TEMP_REG, _F_TEMP_REG, _FR, _STR_PTR)  \
      LA(_LINK_REG, scratch)                                 ;\
      FSREG _FR, 0(_LINK_REG)                                ;\
      LREG _LINK_REG, 0(_LINK_REG)                           ;\
      SREG _LINK_REG, 0(_SIG_PTR)                            ;\
      beq x0, x0, 1f                                         ;\
      jal _LINK_REG, failedtest_##_LINK_REG##_##_TEMP_REG    ;\
      RVTEST_WORD_PTR _STR_PTR                               ;\
      1:                                                     ;\
      LA(_LINK_REG, scratch)                                 ;\
      LREG _LINK_REG, REGWIDTH(_LINK_REG)                    ;\
      SREG _LINK_REG, SIG_STRIDE(_SIG_PTR)                   ;\
      beq x0, x0, 2f                                         ;\
      jal _LINK_REG, failedtest_##_LINK_REG##_##_TEMP_REG    ;\
      RVTEST_WORD_PTR _STR_PTR                               ;\
      2:                                                     ;\
      csrr _LINK_REG, fcsr                                   ;\
      SREG _LINK_REG, 2*SIG_STRIDE(_SIG_PTR)                 ;\
      beq x0, x0, 3f                                         ;\
      jal _LINK_REG, failedtest_##_LINK_REG##_##_TEMP_REG    ;\
      RVTEST_WORD_PTR _STR_PTR                               ;\
      3:                                                     ;\
      addi _SIG_PTR, _SIG_PTR, 3*SIG_STRIDE
  #endif
#else
  #ifdef RVTEST_SELFCHECK
    #define RVTEST_SIGUPD_F(_SIG_PTR, _LINK_REG, _TEMP_REG, _F_TEMP_REG, _FR, _STR_PTR)  \
      LA(_LINK_REG, scratch)                                 ;\
      FSREG _FR, 0(_LINK_REG)                                ;\
      LREG _LINK_REG, 0(_LINK_REG)                           ;\
      LREG _TEMP_REG, 0(_SIG_PTR)                            ;\
      beq _TEMP_REG, _LINK_REG, 1f                           ;\
      jal _LINK_REG, failedtest_##_LINK_REG##_##_TEMP_REG    ;\
      RVTEST_WORD_PTR _STR_PTR                               ;\
      1:                                                     ;\
      csrr _LINK_REG, fcsr                                   ;\
      LREG _TEMP_REG, SIG_STRIDE(_SIG_PTR)                   ;\
      beq _TEMP_REG, _LINK_REG, 3f                           ;\
      jal _LINK_REG, failedtest_##_LINK_REG##_##_TEMP_REG    ;\
      RVTEST_WORD_PTR _STR_PTR                               ;\
      3:                                                     ;\
      addi _SIG_PTR, _SIG_PTR, 2*SIG_STRIDE
  #else
    #define RVTEST_SIGUPD_F(_SIG_PTR, _LINK_REG, _TEMP_REG, _F_TEMP_REG, _FR, _STR_PTR)  \
      LA(_LINK_REG, scratch)                                 ;\
      FSREG _FR, 0(_LINK_REG)                                ;\
      LREG _LINK_REG, 0(_LINK_REG)                           ;\
      SREG _LINK_REG, 0(_SIG_PTR)                            ;\
      beq x0, x0, 1f                                         ;\
      jal _LINK_REG, failedtest_##_LINK_REG##_##_TEMP_REG    ;\
      RVTEST_WORD_PTR _STR_PTR                               ;\
      1:                                                     ;\
      csrr _LINK_REG, fcsr                                   ;\
      SREG _LINK_REG, SIG_STRIDE(_SIG_PTR)                   ;\
      beq x0, x0, 3f                                         ;\
      jal _LINK_REG, failedtest_##_LINK_REG##_##_TEMP_REG    ;\
      RVTEST_WORD_PTR _STR_PTR                               ;\
      3:                                                     ;\
      addi _SIG_PTR, _SIG_PTR, 2*SIG_STRIDE
  #endif
#endif



// RVTEST_SIGUPD_V(_SIG_PTR, _TMP, AVL, SEW, VREG)
//  _SIG_PTR  - Base register for signature region
//  _TEMP_REG - Temporary int register to use for loading signature
//   AVL       - Application vector length (immediate constant)
//   SEW       - Element width in bits (8, 16, 32, or 64)
//   VREG      - Vector register containing data
// TODO: implement SELFCHECK version
#define RVTEST_SIGUPD_V(_SIG_PTR, _TEMP_REG, SEW, OFFSET, VREG)      \
  vse ## SEW ##.v VREG, (_SIG_PTR)                           ;\
  nop                                                         ;\
  nop                                                         ;\
  addi _SIG_PTR, _SIG_PTR, OFFSET


// Canary value to indicate bounds of signature region
#if SIG_STRIDE==8
  #define CANARY_VALUE \
      0x6F5CA309E7D4B281
  #define CANARY \
      .dword CANARY_VALUE
#else
  #define CANARY_VALUE \
      0x6F5CA309
  #define CANARY \
      .word CANARY_VALUE
#endif

// Read _CSR into _R and record/check the signature
#define RVTEST_SIGUPD_CSR_RD(_SIG_PTR, _LINK_REG, _TEMP_REG, _CSR, _R, _STR_PTR) \
    CSRR(_R, _CSR)                                       ;\
    RVTEST_SIGUPD(_SIG_PTR, _LINK_REG, _TEMP_REG, _R, _STR_PTR)

// Abbreviated form with default registers
#define RVTEST_SIGUPD_CSR_READ(_CSR, _R, _STR_PTR) \
    RVTEST_SIGUPD_CSR_RD(DEFAULT_SIG_REG, DEFAULT_LINK_REG, DEFAULT_TEMP_REG, _CSR, _R, _STR_PTR)


// Write _R1 into _CSR, then read back into _R2 and record/check the signature
#define RVTEST_SIGUPD_CSR_WR(_SIG_PTR, _LINK_REG, _TEMP_REG, _CSR, _R1, _R2, _STR_PTR) \
    CSRW(_CSR, _R1)                                      ;\
    RVTEST_SIGUPD_CSR_RD(_SIG_PTR, _LINK_REG, _TEMP_REG, _CSR, _R2, _STR_PTR)

// Abbreviated form with default registers, overwrites _R with value read back
#define RVTEST_SIGUPD_CSR_WRITE(_CSR, _R, _STR_PTR) \
    RVTEST_SIGUPD_CSR_WR(DEFAULT_SIG_REG, DEFAULT_LINK_REG, DEFAULT_TEMP_REG, _CSR, _R, _R, _STR_PTR)
