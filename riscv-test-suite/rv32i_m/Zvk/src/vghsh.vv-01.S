// Copyright (c) 2023. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
// This assembly file tests the vghsh.vv instruction.

// Define special purpose registers before including test_macros_vector.h
#define DATA_BASE x3
#define SIG_BASE x4
#define VLENB_CACHE x5
#define HELPER_GPR x6

#include "test_macros_vector.h"

RVTEST_ISA("RV32IV_Zicsr_Zvkg,RV64IV_Zicsr_Zvkg")

.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT

RVTEST_CODE_BEGIN

#ifdef TEST_CASE_1

RVTEST_CASE(0,"//check ISA:=regex(.*I.*V.*Zicsr.*Zvkg);def TEST_CASE_1=True;",vghsh.vv)

RVTEST_V_ENABLE()
RVTEST_VALBASEUPD(DATA_BASE, dataset_tc1)
RVTEST_SIGBASE(SIG_BASE, signature_tc1)

// VGHSH.VV has the following inputs and outputs:
// - input VD: Partial hash Yi
// - input VS1: Cipher text
// - input VS2: Hash subkey
// - output VD: Partial hash Yi+1
// VGHSH.VV requires that SEW=32 and AVL=multiple of 4

#define VINST vghsh.vv

inst_0:
TEST_CASE_WVV(4, 32, VINST, v0, 0*4, v1, 0*4, v2, 0*4)
//sig[4*4]

inst_1:
TEST_CASE_WVV(8, 32, VINST, v3, 1*4, v2, 0*4, v30, 20*4)
//sig[12*4]

inst_2:
TEST_CASE_WVV(12, 32, VINST, v4, 2*4, v5, 2*4, v28, 18*4)
//sig[24*4]

inst_3:
TEST_CASE_WVV(16, 32, VINST, v7, 0*4, v6, 0*4, v26, 16*4)
//sig[40*4]

inst_4:
TEST_CASE_WVV(20, 32, VINST, v8, 2*4, v9, 3*4, v24, 14*4)
//sig[60*4]

inst_5:
TEST_CASE_WVV(24, 32, VINST, v11, 2*4, v10, 3*4, v22, 12*4)
//sig[84*4]

inst_6:
TEST_CASE_WVV(28, 32, VINST, v12, 2*4, v13, 3*4, v20, 10*4)
//sig[112*4]

inst_7:
TEST_CASE_WVV(4, 32, VINST, v15, 2*4, v14, 3*4, v18, 8*4)
//sig[116*4]

inst_8:
TEST_CASE_WVV(4, 32, VINST, v16, 0*4, v17, 4*4, v16, 0*4)
//sig[120*4]

inst_9:
TEST_CASE_WVV(4, 32, VINST, v19, 4*4, v18, 0*4, v14, 4*4)
//sig[124*4]

inst_10:
TEST_CASE_WVV(4, 32, VINST, v20, 0*4, v21, 0*4, v12, 2*4)
//sig[128*4]

inst_11:
TEST_CASE_WVV(4, 32, VINST, v20, 0*4, v21, 11*4, v10, 0*4)
//sig[132*4]

inst_12:
TEST_CASE_WVV(4, 32, VINST, v23, 2*4, v22, 9*4, v8, 8*4)
//sig[136*4]

inst_13:
TEST_CASE_WVV(4, 32, VINST, v24, 4*4, v25, 7*4, v6, 6*4)
//sig[140*4]

inst_14:
TEST_CASE_WVV(4, 32, VINST, v27, 6*4, v26, 5*4, v4, 4*4)
//sig[144*4]

inst_15:
TEST_CASE_WVV(4, 32, VINST, v28, 8*4, v29, 3*4, v2, 2*4)
//sig[148*4]

inst_16:
TEST_CASE_WVV(4, 32, VINST, v31, 10*4, v30, 1*4, v0, 0*4)
//sig[156*4]

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
