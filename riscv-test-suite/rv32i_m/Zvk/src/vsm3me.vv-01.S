// Copyright (c) 2023. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
// This assembly file tests the vsm3me.vi instruction.

// Define special purpose registers before including test_macros_vector.h
#define DATA_BASE x3
#define SIG_BASE x4
#define VLENB_CACHE x5
#define HELPER_GPR x6

#include "test_macros_vector.h"

RVTEST_ISA("RV32IV_Zicsr_Zvksh,RV64IV_Zicsr_Zvksh")

.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT

RVTEST_CODE_BEGIN

#ifdef TEST_CASE_1

RVTEST_CASE(0,"//check ISA:=regex(.*I.*V.*Zicsr.*Zvksh);def TEST_CASE_1=True;",vsm3me.vv)

RVTEST_V_ENABLE()
RVTEST_VALBASEUPD(DATA_BASE, dataset_tc1)
RVTEST_SIGBASE(SIG_BASE, signature_tc1)

// VSM3ME.VV has the following inputs and outputs:
// - input VS1: Message words W[7:0]
// - input VS2: Message words W[15:8]
// - output VD: Message words W[23:16]
// VSM3ME.VV requires that SEW=32 and AVL=multiple of 8

#define VINST vsm3me.vv

inst_0:
TEST_CASE_VVV(8, 32, VINST, v0, v1, 0*8, v2, 1*8)
//sig[8*4]

inst_1:
TEST_CASE_VVV(8, 32, VINST, v5, v4, 2*8, v3, 3*8)
//sig[16*4]

inst_2:
TEST_CASE_VVV(16, 32, VINST, v6, v7, 4*8, v8, 5*8)
//sig[32*4]

inst_3:
TEST_CASE_VVV(16, 32, VINST, v9, v10, 7*8, v11, 6*8)
//sig[48*4]

inst_4:
TEST_CASE_VVV(8, 32, VINST, v12, v13, 2*8, v14, 3*8)
//sig[56*4]

inst_5:
TEST_CASE_VVV(8, 32, VINST, v15, v16, 2*8, v17, 3*8)
//sig[64*4]

inst_6:
TEST_CASE_VVV(8, 32, VINST, v18, v19, 2*8, v20, 3*8)
//sig[72*4]

inst_7:
TEST_CASE_VVV(8, 32, VINST, v21, v22, 2*8, v23, 3*8)
//sig[80*4]

inst_8:
TEST_CASE_VVV(8, 32, VINST, v24, v25, 0*8, v26, 4*8)
//sig[88*4]

inst_9:
TEST_CASE_VVV(8, 32, VINST, v27, v28, 4*8, v29, 0*8)
//sig[96*4]

inst_10:
TEST_CASE_VVV(8, 32, VINST, v30, v31, 0*8, v0, 0*8)
//sig[104*4]

inst_11:
TEST_CASE_VVV(8, 32, VINST, v0, v15, 4*8, v31, 4*8)
//sig[112*4]

#endif // TEST_CASE_1

RVTEST_CODE_END

RVMODEL_HALT

RVTEST_DATA_BEGIN
.word 0xbabecafe // trapreg_sv
.word 0xabecafeb // tramptbl_sv
.word 0xbecafeba // mtvec_save
.word 0xecafebab // mscratch_save

    .p2align 6
dataset_tc1:
TEST_CASE_BLOCK_256B_0
RVTEST_DATA_END

RVMODEL_DATA_BEGIN
rvtest_sig_begin:
sig_begin_canary:
CANARY;

signature_tc1:
    //sig[0*4..127*4]
    .fill 128, 4, 0xdeadbeef

#ifdef rvtest_mtrap_routine

tsig_begin_canary:
CANARY;
tsig_begin_canary:
CANARY;
mtrap_sigptr:
    .fill 64*(XLEN/32),4,0xdeadbeef
tsig_end_canary:
CANARY;
tsig_end_canary:
CANARY;

#endif // rvtest_mtrap_routine

#ifdef rvtest_gpr_save

gpr_save:
    .fill 32*XLEN/32,4,0xdeadbeef

#endif // rvtest_gpr_save

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END
