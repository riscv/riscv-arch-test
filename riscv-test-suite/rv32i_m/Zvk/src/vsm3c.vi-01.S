// Copyright (c) 2023. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
// This assembly file tests the vsm3c.vi instruction.

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

RVTEST_CASE(0,"//check ISA:=regex(.*I.*V.*Zicsr.*Zvksh);def TEST_CASE_1=True;",vsm3c.vi)

RVTEST_V_ENABLE()
RVTEST_VALBASEUPD(DATA_BASE, dataset_tc1)
RVTEST_SIGBASE(SIG_BASE, signature_tc1)

// VSM3C.VI has the following inputs and outputs:
// - input VD: Current state {H,G.F,E,D,C,B,A}
// - input VS2: Message words {-,-,w[5],w[4],-,-,w[1],w[0]}
// - input UIMM[5]: Round number (0..31)
// - output VD: Next state {H,G.F,E,D,C,B,A}
// VSM3C.VI requires that SEW=32 and AVL=multiple of 8

#define VINST vsm3c.vi

inst_0:
TEST_CASE_WVU(8, 32, VINST, v0, 1*4, v1, 0*4, 1)
//sig[8*4]

inst_1:
TEST_CASE_WVU(8, 32, VINST, v3, 2*4, v2, 0*4, 2)
//sig[16*4]

inst_2:
TEST_CASE_WVU(16, 32, VINST, v4, 0*4, v5, 2*4, 3)
//sig[24*4]

inst_3:
TEST_CASE_WVU(24, 32, VINST, v7, 1*4, v6, 0*4, 4)
//sig[48*4]

inst_4:
TEST_CASE_WVU(24, 32, VINST, v8, 2*4, v9, 3*4, 5)
//sig[72*4]

inst_5:
TEST_CASE_WVU(8, 32, VINST, v11, 0*4, v10, 3*4, 6)
//sig[80*4]

inst_6:
TEST_CASE_WVU(8, 32, VINST, v12, 1*4, v13, 3*4, 7)
//sig[88*4]

inst_7:
TEST_CASE_WVU(8, 32, VINST, v15, 2*4, v14, 3*4, 8)
//sig[96*4]

inst_8:
TEST_CASE_WVU(8, 32, VINST, v16, 0*4, v17, 4*4, 9)
//sig[104*4]

inst_9:
TEST_CASE_WVU(8, 32, VINST, v19, 0*4, v18, 0*4, 10)
//sig[112*4]

inst_10:
TEST_CASE_WVU(8, 32, VINST, v20, 1*4, v21, 0*4, 16)
//sig[120*4]

inst_11:
TEST_CASE_WVU(8, 32, VINST, v20, 0*4, v21, 11*4, 20)
//sig[128*4]

inst_12:
TEST_CASE_WVU(8, 32, VINST, v23, 2*4, v22, 9*4, 23)
//sig[136*4]

inst_13:
TEST_CASE_WVU(8, 32, VINST, v24, 1*4, v25, 7*4, 24)
//sig[144*4]

inst_14:
TEST_CASE_WVU(8, 32, VINST, v27, 0*4, v26, 5*4, 25)
//sig[152*4]

inst_15:
TEST_CASE_WVU(8, 32, VINST, v28, 1*4, v29, 3*4, 31)
//sig[160*4]

inst_16:
TEST_CASE_WVU(8, 32, VINST, v31, 0*4, v30, 1*4, 0)
//sig[168*4]

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
    //sig[0*4..255*4]
    .fill 256, 4, 0xdeadbeef

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
