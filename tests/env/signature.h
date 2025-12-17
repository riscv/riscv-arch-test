# signature.h
# Signature region handling macros
# Jordan Carlin jcarlin@hmc.edu October 2025
# SPDX-License-Identifier: Apache-2.0

// SEW signature update stride
#ifdef RVTEST_VECTOR
  #if (VDSEW > XLEN)                // max(VDSEW, XLEN)
    #define SIG_STRIDE (VDSEW / 8)
  #else
    #define SIG_STRIDE (XLEN / 8)
  #endif
#else
  #define SIG_STRIDE REGWIDTH
#endif

// Define XLEN-sized pointer directive
#if __riscv_xlen == 64
  #define RVTEST_WORD_PTR .dword
#else
  #define RVTEST_WORD_PTR .word
#endif

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
#ifdef SELFCHECK
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
#ifdef SELFCHECK
  #define RVTEST_SIGUPD_F(_SIG_PTR, _LINK_REG, _TEMP_REG, _F_TEMP_REG, _FR, _STR_PTR)  \
    FLREG _F_TEMP_REG, 0(_SIG_PTR)                         ;\
    beq _F_TEMP_REG, _FR, 1f                               ;\
    jal _LINK_REG, failedtest_##_LINK_REG##_##_TEMP_REG    ;\
    1:                                                     ;\
    csrr _LINK_REG, fcsr                                   ;\
    LREG _TEMP_REG, SIG_STRIDE(_SIG_PTR)                   ;\
    beq _TEMP_REG, _LINK_REG, 2f                           ;\
    jal _LINK_REG, failedtest_##_LINK_REG##_##_TEMP_REG    ;\
    2:                                                     ;\
    addi _SIG_PTR, _SIG_PTR, 2*SIG_STRIDE
#else
  #define RVTEST_SIGUPD_F(_SIG_PTR, _LINK_REG, _TEMP_REG, _F_TEMP_REG, _FR, _STR_PTR)  \
    FSREG _FR, 0(_SIG_PTR)                                 ;\
    beq x0, x0, 1f                                         ;\
    jal _LINK_REG, failedtest_##_LINK_REG##_##_TEMP_REG    ;\
    1:                                                     ;\
    csrr _LINK_REG, fcsr                                   ;\
    SREG _LINK_REG, SIG_STRIDE(_SIG_PTR)                   ;\
    beq x0, x0, 2f                                         ;\
    jal _LINK_REG, failedtest_##_LINK_REG##_##_TEMP_REG    ;\
    2:                                                     ;\
    addi _SIG_PTR, _SIG_PTR, 2*SIG_STRIDE
#endif

// Canary value to indicate bounds of signature region
#if SIGALIGN==8
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
