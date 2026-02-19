// -----------
// Copyright (c) 2020. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
//
// This assembly file tests the eventuality property of Ziccid
// 

#include "model_test.h"
#include "arch_test.h"

RVTEST_ISA("RV64I_Zicsr_Zifencei")

# Test code region
.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT
RVTEST_CODE_BEGIN

#ifdef TEST_CASE_1
    RVTEST_CASE(1,"//check ISA:=regex(.*64.*); check ISA:=regex(.*I.*Ziccid.*); def rvtest_mtrap_routine=True; def TEST_CASE_1=True",ziccid)

  RVTEST_SIGBASE(x13, signature_x13_1)

  la x5, insn
  li x6, 0x00100513   # li x10, 1
  li x7, 0x00000513   # li x10, 0

  sw x7, (x5)
  fence.i

  li a1, 100
loop:
  .balign 2
insn:
  .word 0

  addi a1, a1, -1
  bnez a1, 1f
  # modify instruction on 100th iteration
  sw x6, (x5)
  RVTEST_SIGUPD(x13, x6)
1:
  # break out of loop if the modified instruction is executed
  beqz x10, loop

  RVTEST_SIGUPD(x13, x10)
    
#endif

 # ---------------------------------------------------------------------------------------------
    # HALT

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
signature_x13_1:
    .fill 32*(XLEN/32),4,0xdeadbeef

mtrap_sigptr:
  .fill 4, 4, 0xdeadbeef

#ifdef rvtest_gpr_save
gpr_save:
  .fill 32*(XLEN/32), 4, 0xdeadbeef
#endif

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END
