// tsbi.h
// T-SBI (Test Supervisor Binary Interface) operation codes, shared by assembly and C tests.
//
// Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
// SPDX-License-Identifier: BSD-3-Clause

#ifndef TSBI_H
#define TSBI_H

// A T-SBI call is an ecall with the operation code in a0. Arguments go in a1 and a2.
// The result is returned in a0. Operation codes are 32-bit values. On RV64, a0 must
// hold the code zero-extended.
//
// The handler dispatches in this order:
//   1. a0 in [1, 5]: switch the caller to the privilege mode given by TSBI_GOTO_*.
//   2. a0 == 0x73 (the ecall encoding): TSBI_ECALL_TEST.
//   3. Otherwise, a0 is the encoding of an instruction for the handler to execute.
//      The handler finds the encoding in a table of supported instructions and runs
//      that copy, so it does not need self-modifying code.
// An unsupported operation fails the test or returns TSBI_RESERVED_RET in a0.

// Privilege-mode switches.
#define TSBI_GOTO_MMODE     0x00000001
#define TSBI_GOTO_SMODE     0x00000002
#define TSBI_GOTO_UMODE     0x00000003
#define TSBI_GOTO_VSMODE    0x00000004
#define TSBI_GOTO_VUMODE    0x00000005

// Record the ecall in the trap signature and return with xEPC in a0.
#define TSBI_ECALL_TEST     0x00000073

#define TSBI_SFENCE_VMA     0x12000073           // sfence.vma x0, x0: flush address-translation caches (requires S)

// Physical-memory accesses. The address is in a1. Stores write a2. Loads return the value in a0.
#define TSBI_LW             0x0005a503           // lw a0, 0(a1)
#define TSBI_LWP4           0x0045a503           // lw a0, 4(a1)
#define TSBI_LD             0x0005b503           // ld a0, 0(a1) (RV64 only)
#define TSBI_SW             0x00c5a023           // sw a2, 0(a1)
#define TSBI_SWP4           0x00c5a223           // sw a2, 4(a1)
#define TSBI_SD             0x00c5b023           // sd a2, 0(a1) (RV64 only)

// CSR accesses. csr is a 12-bit CSR number such as CSR_MIP from encoding.h.
// The CSR must be in the T-SBI CSR table in rvtest_trap_handler.h.
// Writes take the value in a1. Reads return the value in a0.
// In C, the CSR number is unsigned so that the shift into bit 31 is defined.
#ifdef __ASSEMBLER__
  #define TSBI_CSR_NUM(csr)  ((csr) & 0xFFF)
#else
  #define TSBI_CSR_NUM(csr)  ((unsigned int)(csr) & 0xFFFu)
#endif
#define TSBI_CSR_SET(csr)    ((TSBI_CSR_NUM(csr) << 20) | 0x0005a073)  // csrrs x0, csr, a1
#define TSBI_CSR_CLEAR(csr)  ((TSBI_CSR_NUM(csr) << 20) | 0x0005b073)  // csrrc x0, csr, a1
#define TSBI_CSR_WRITE(csr)  ((TSBI_CSR_NUM(csr) << 20) | 0x00059073)  // csrrw x0, csr, a1
#define TSBI_CSR_READ(csr)   ((TSBI_CSR_NUM(csr) << 20) | 0x00002573)  // csrrs a0, csr, x0

// Value returned in a0 for some unsupported operations.
#define TSBI_RESERVED_RET   (-1)

#endif // TSBI_H
