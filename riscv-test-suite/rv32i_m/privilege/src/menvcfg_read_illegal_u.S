// -----------
// Copyright (c) 2023. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
//
// This assembly file tests the menvcfg CSR access.
// 

#include "model_test.h"
#include "arch_test.h"

RVTEST_ISA("RV32I_Zicbom_Zicboz_Zicsr_Ssdtso_Sstc")

# Test code region
.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT
RVTEST_CODE_BEGIN

RVTEST_SIGBASE(a1,signature_a1_m)

#ifdef TEST_CASE_1

RVTEST_CASE(0,"//check ISA:=regex(.*I.*Zicbom.*Zicboz.*Zicsr.*Ssdtso.*Sstc); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def TEST_CASE_1=True",menvcfg-read-illegal-u)

inst_S_illegal:
RVTEST_GOTO_LOWER_MODE Umode
// We have enabled the trap routines, which will store the relevant
// exception information in the exception signature.
RVTEST_CSR_READ_ILLEGAL(CSR_MENVCFG, t0)
// RVTEST_CODE_END calls RVTEST_GOTO_MMODE

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

signature_a1_m:
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
