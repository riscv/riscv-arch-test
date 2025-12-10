# signature.h
# Signature region handling macros
# Jordan Carlin jcarlin@hmc.edu October 2025
# SPDX-License-Identifier: Apache-2.0

// Define XLEN-sized pointer directive
#if __riscv_xlen == 64
  #define RVTEST_WORD_PTR .dword
#else
  #define RVTEST_WORD_PTR .word
#endif

// RVTEST_SIGBASE(sigbase, label) initializes the sigbase register to the
// address of the signature region.
// _SIG_BASE - Base register for signature region
// _TAG - Tag to identify signature region
#define RVTEST_SIGBASE(_SIG_BASE,_TAG)      ;\
  LA(_SIG_BASE,_TAG)

// RVTEST_SIGUPD(sigbase, linkreg, tempreg, sigreg) compares the value in sigreg
// with the value in memory at 0(sigbase). If they are different, it jumps to
// a failure handler whose label is formed from linkreg and tempreg. On success,
// it increments sigbase by REGWIDTH. In non-SELFCHECK mode, it simply stores
// sigreg to memory at 0(sigbase) and increments sigbase by REGWIDTH.
//  _SIG_BASE - Base register for signature region
//  _LINK_REG - Link register to use for failure jump
//  _TEMP_REG - Temporary register to use for loading signature
//  _R - Register containing value to store/compare
//  _STR_PTR - label to string describing the test
#ifdef SELFCHECK
  #define RVTEST_SIGUPD(_SIG_BASE, _LINK_REG, _TEMP_REG, _R, _STR_PTR)  \
    LREG _TEMP_REG, 0(_SIG_BASE)                            ;\
    beq _TEMP_REG, _R, 1f                                  ;\
    jal _LINK_REG, failedtest_##_LINK_REG##_##_TEMP_REG    ;\
    RVTEST_WORD_PTR _STR_PTR                                ;\
    1:                                                     ;\
    addi _SIG_BASE, _SIG_BASE, REGWIDTH
#else
  #define RVTEST_SIGUPD(_SIG_BASE, _LINK_REG, _TEMP_REG, _R, _STR_PTR)  \
    SREG _R, 0(_SIG_BASE)                                   ;\
    beq x0, x0, 1f                                         ;\
    jal _LINK_REG, failedtest_##_LINK_REG##_##_TEMP_REG    ;\
    RVTEST_WORD_PTR _STR_PTR                                ;\
    1:                                                     ;\
    addi _SIG_BASE, _SIG_BASE, REGWIDTH
#endif

// RVTEST_SIGUPD_F(sigbase, linkreg, tempreg, sigreg) compares the value in sigreg
// with the value in memory at 0(sigbase) and the value in FCSR with the value in
// memory at REGWIDTH(sigbase). If either are different, it jumps to a failure handler
// whose label is formed from linkreg and tempreg. On success, it increments sigbase
// by 2*REGWIDTH. In non-SELFCHECK mode, it simply stores sigreg to memory at 0(sigbase),
// fcsr to memory at REGWIDTH(sigbase), and increments sigbase by 2*REGWIDTH.
//  _SIG_BASE - Base register for signature region
//  _LINK_REG - Link register to use for failure jump
//  _TEMP_REG - Temporary register to use for loading signature
//  _R - Register containing value to store/compare
#ifdef SELFCHECK
  #define RVTEST_SIGUPD_F(_SIG_BASE, _LINK_REG, _TEMP_REG, _R)  \
    FLREG _TEMP_REG,0(_SIG_BASE)                           ;\
    beq _TEMP_REG, _R, 1f                                  ;\
    jal _LINK_REG, failedtest_##_LINK_REG##_##_TEMP_REG    ;\
    1:                                                     ;\
    csrr _R, fcsr                                          ;\
    LREG _TEMP_REG,FREGWIDTH(_SIG_BASE)                    ;\
    beq _TEMP_REG, _R, 2f                                  ;\
    jal _LINK_REG, failedtest_##_LINK_REG##_##_TEMP_REG    ;\
    2:                                                     ;\
    addi _SIG_BASE, _SIG_BASE, REGWIDTH+FREGWIDTH
#else
  #define RVTEST_SIGUPD_F(_SIG_BASE, _LINK_REG, _TEMP_REG, _R)  \
    FSREG _R,0(_SIG_BASE)                                  ;\
    csrr _R, fcsr                                          ;\
    SREG _TEMP_REG,FREGWIDTH(_SIG_BASE)                    ;\
    nop                                                    ;\
    nop                                                    ;\
    addi _SIG_BASE, _SIG_BASE, REGWIDTH+FREGWIDTH
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
