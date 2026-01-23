// -----------
// Copyright (c) 2020. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
//
// This assembly file tests the Svadu extension
// 
#include "model_test.h"
#include "arch_test.h"

# Test Virtual Machine (TVM) used by program.
RVTEST_ISA("RV32I_Zicsr")

# Test code region
.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT
RVTEST_CODE_BEGIN

#ifdef TEST_CASE_1
  RVTEST_CASE(1,"//check ISA:=regex(.*32.*);check ISA:=regex(.*I.*);check ISA:=regex(.*Svadu.*);def rvtest_mtrap_routine=True;def TEST_CASE_1=True;",svadu_sv32)

  RVTEST_SIGBASE(x1, signature_x1_0)

  # Setup PMP to cover 4G of address space
  SETUP_PMP_SVADU_TEST(x1, offset, t0, t1, t2)

  # Identity map the page_4k
  la t1, page_4k
  mv t2, t1
  PTE_SETUP_SV32(t1, PTE_V, t0, s2, t2, 1)

  # enable virtual memory in Sv32 mode
  SATP_SETUP(t0, t1, SATP32_MODE)

  # test svadu
  TEST_SVADU(x1, s2, page_4k, offset, 0x31a, MENVCFGH_ADUE)

#endif
RVTEST_CODE_END
RVMODEL_HALT

RVTEST_DATA_BEGIN
  .align 12
   page_4k:
  .fill   4096/REGWIDTH, REGWIDTH, 0
RVTEST_DATA_END

  .align 12
rvtest_Sroot_pg_tbl:
  .fill   4096/REGWIDTH, REGWIDTH, 0

# Output data section.
RVMODEL_DATA_BEGIN
rvtest_sig_begin:
sig_begin_canary:
CANARY;

signature_x1_0:
  .fill 128*(XLEN/32),4,0xdeadbeef

#ifdef rvtest_mtrap_routine
mtrap_sigptr:
  .fill 128*4, 4, 0xdeadbeef
#endif

#ifdef rvtest_gpr_save
gpr_save:
  .fill 32*(XLEN/32), 4, 0xdeadbeef
#endif

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END
