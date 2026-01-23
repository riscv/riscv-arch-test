// -----------
// Copyright (c) 2020. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
//
// This assembly file tests the Smstaten and Ssqosid interactions
// 

#include "model_test.h"
#include "arch_test.h"

RVTEST_ISA("RV64I_Zicsr")

# Test code region
.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT
RVTEST_CODE_BEGIN

#ifdef TEST_CASE_1
  RVTEST_CASE(1,"//check ISA:=regex(.*I.*Zicsr.*Smstateen.*Ssqosid.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def TEST_CASE_1=True", srmcfg_mstateen)

  RVTEST_SIGBASE(x1,signature_x1)

  # setup PMP to allow execution in U and S mode
  li x2, PMP_TOR | PMP_X | PMP_W | PMP_R
  csrw pmpcfg0, x2
  csrr x2, pmpcfg0
  beq  x2, x0, no_TOR_try_NAPOT
  li x2, 0xFFFFFFFF
  csrw pmpaddr0, x2
  j Mend_PMP
no_TOR_try_NAPOT:
  li x2, PMP_NAPOT | PMP_X | PMP_W | PMP_R
  csrw pmpcfg0, x2
  csrr x2, pmpcfg0
  beq  x2, x0, Mend_PMP
  li x2, 0x1FFFFFFF
  csrw pmpaddr0, x2
Mend_PMP:
  csrw satp, x0

  li x2, 0x05550AAA
  csrw CSR_SRMCFG, x2

  # transfer to Umode and access the CSR - access faults
  RVTEST_GOTO_LOWER_MODE Umode
  csrw CSR_SRMCFG, x0
  nop
  nop
  nop
  nop
  nop
  RVTEST_GOTO_MMODE

  # transfer to Umode and access the CSR - access faults
  RVTEST_GOTO_LOWER_MODE Smode
  csrw CSR_SRMCFG, x0
  nop
  nop
  nop
  nop
  nop
  RVTEST_GOTO_MMODE

  csrr x2, CSR_SRMCFG
  RVTEST_SIGUPD(x1, x2, 0 * REGWIDTH)

  # Enable Smode access to srmcfg
  csrr x3, CSR_MSTATEEN0
  li x2, MSTATEEN0_PRIV114
  or x3, x2, x2
  csrw CSR_MSTATEEN0, x3

  csrr x2, CSR_MSTATEEN0
  RVTEST_SIGUPD(x1, x2, 1 * REGWIDTH)

  # transfer to Smode and access the CSR - access succeeds
  RVTEST_GOTO_LOWER_MODE Smode
  li x2, 0x0AAA0555
  csrw CSR_SRMCFG, x2
  RVTEST_GOTO_MMODE

  csrr x2, CSR_SRMCFG
  RVTEST_SIGUPD(x1, x2, 2 * REGWIDTH)

  # transfer to Umode and access the CSR - access faults
  RVTEST_GOTO_LOWER_MODE Umode
  csrw CSR_SRMCFG, x0
  nop
  nop
  nop
  nop
  nop
  RVTEST_GOTO_MMODE

  csrr x2, CSR_SRMCFG
  RVTEST_SIGUPD(x1, x2, 3 * REGWIDTH)
#endif

RVTEST_CODE_END
RVMODEL_HALT

RVTEST_DATA_BEGIN
# Input data section.
  .data
  .align 4
RVTEST_DATA_END

# Output data section.
RVMODEL_DATA_BEGIN
rvtest_sig_begin:
sig_begin_canary:
CANARY;

signature_x1:
  .fill 16*((XLEN/8)/4),4,0xdeadbeef

#ifdef rvtest_mtrap_routine
mtrap_sigptr:
  .fill 64*(XLEN/32),4,0xdeadbeef
#endif

#ifdef rvtest_gpr_save
gpr_save:
  .fill 32*(XLEN/32), 4, 0xdeadbeef
#endif

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END
