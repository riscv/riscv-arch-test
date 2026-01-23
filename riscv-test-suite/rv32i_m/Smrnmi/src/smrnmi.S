// -----------
// Copyright (c) 2023. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
//
// This assembly file tests the Smrnmi extension
//

#include "model_test.h"
#include "arch_test.h"

RVTEST_ISA("RV32I_Zicsr")

# Test code region
.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT
RVTEST_CODE_BEGIN

RVTEST_SIGBASE(x15, signature_x15_m)

#ifdef TEST_CASE_1
RVTEST_CASE(0,"//check ISA:=regex(.*32.*I.*Zicsr.*Smrnmi); def rvtest_mtrap_routine=True; def TEST_CASE_1=True",smrnmi)

  # Update initial value of Smrnmi CSRs to signature
  RVTEST_SIGUPD_CSR(x15, x1, CSR_MNSCRATCH)
  RVTEST_SIGUPD_CSR(x15, x1, CSR_MNEPC)
  RVTEST_SIGUPD_CSR(x15, x1, CSR_MNCAUSE)
  RVTEST_SIGUPD_CSR(x15, x1, CSR_MNSTATUS)

  # write Smrnmi CSRs, read and update sig
  li x1, 0xAAAAAAAA
  csrw CSR_MNSCRATCH, x1
  csrw CSR_MNEPC, x1
  RVTEST_SIGUPD_CSR(x15, x1, CSR_MNSCRATCH)
  RVTEST_SIGUPD_CSR(x15, x1, CSR_MNEPC)
  li x1, 0x5AAAAAAA
  csrw CSR_MNCAUSE, x1
  RVTEST_SIGUPD_CSR(x15, x1, CSR_MNCAUSE)

  # MNPP is WARL
  li x1, (1 << 11)
  csrw CSR_MNSTATUS, x1
  RVTEST_SIGUPD_CSR(x15, x1, CSR_MNSTATUS)
  li x1, (0 << 11)
  csrw CSR_MNSTATUS, x1
  RVTEST_SIGUPD_CSR(x15, x1, CSR_MNSTATUS)
  li x1, (2 << 11)
  csrw CSR_MNSTATUS, x1
  RVTEST_SIGUPD_CSR(x15, x1, CSR_MNSTATUS)
  li x1, (3 << 11)
  csrw CSR_MNSTATUS, x1
  RVTEST_SIGUPD_CSR(x15, x1, CSR_MNSTATUS)

  # Set NMIE to enable RNMI
  li x1, MNSTATUS_NMIE
  csrw CSR_MNSTATUS, x1

  # NMIE is sticky and cannot be cleared
  csrw CSR_MNSTATUS, x0
  RVTEST_SIGUPD_CSR(x15, x1, CSR_MNSTATUS)

#endif

RVTEST_CODE_END
RVMODEL_HALT

# Input data section.
RVTEST_DATA_BEGIN
    .align 4
RVTEST_DATA_END

# Output data section.
RVMODEL_DATA_BEGIN
rvtest_sig_begin:
sig_begin_canary:
CANARY;

signature_x15_m:
    .fill 32*(XLEN/32),4,0xdeadbeef

#ifdef rvtest_mtrap_routine

tsig_begin_canary:
CANARY;
mtrap_sigptr:
    .fill 64*(XLEN/32),4,0xdeadbeef
tsig_end_canary:
CANARY;

#endif

#ifdef rvtest_gpr_save

gpr_save:
    .fill 32*(XLEN/32),4,0xdeadbeef

#endif


sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END
