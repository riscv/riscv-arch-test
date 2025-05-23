// Copyright (c) 2023. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
// This assembly file tests the vclmulh.vx instruction.

// Define special purpose registers before including test_macros_vector.h
#define DATA_BASE x3
#define SIG_BASE x4
#define VLENB_CACHE x5
#define HELPER_GPR x6

#include "test_macros_vector.h"

RVTEST_ISA("RV32IV_Zicsr_Zvkb,RV64IV_Zicsr_Zvkb")

.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT

RVTEST_CODE_BEGIN

#ifdef TEST_CASE_1

RVTEST_CASE(0,"//check ISA:=regex(.*I.*V.*Zicsr.*Zvkb);def TEST_CASE_1=True;",vclmulh.vx)

RVTEST_V_ENABLE()
RVTEST_VALBASEUPD(DATA_BASE, dataset_tc1)
RVTEST_SIGBASE(SIG_BASE, signature_tc1)

// VCLMULH.VX has the following inputs and outputs:
// - input VS1: Multiplier
// - input VS2: Multiplicand
// - input VM: Mask encoding (<nothing> or v0.t)
// - output VD: Carry-less product (low-half)
// VCLMULH.VX requires that SEW=64

#define VINST vclmulh.vx

inst_0:
// This test will define v0, which will later be used as mask register
TEST_CASE_VVR(1, 64, VINST, v0, v1, 0*8, x7, 1*8)
//sig[8*1]

inst_1:
TEST_CASE_VVR(1, 64, VINST, v5, v4, 2*8, x7, 3*8)
//sig[8*2]

inst_2:
TEST_CASE_VVR(1, 64, VINST, v6, v7, 4*8, x8, 5*8)
//sig[8*3]

inst_3:
TEST_CASE_VVR(1, 64, VINST, v9, v10, 7*8, x11, 6*8)
//sig[8*4]

inst_4:
TEST_CASE_VVR_M(2, 64, VINST, v12, v13, 2*8, x14, 3*8)
//sig[8*6]

inst_5:
TEST_CASE_VVR(2, 64, VINST, v15, v16, 2*8, x17, 3*8)
//sig[8*8]

inst_6:
TEST_CASE_VVR_M(2, 64, VINST, v18, v19, 2*8, x20, 3*8)
//sig[8*10]

inst_7:
TEST_CASE_VVR_M(2, 64, VINST, v21, v22, 2*8, x23, 3*8)
//sig[8*12]

inst_8:
TEST_CASE_VVR(4, 64, VINST, v24, v25, 0*8, x26, 4*8)
//sig[8*16]

inst_9:
TEST_CASE_VVR(4, 64, VINST, v27, v28, 4*8, x29, 0*8)
//sig[8*20]

inst_10:
TEST_CASE_VVR(4, 64, VINST, v30, v31, 0*8, x7, 0*8)
//sig[8*24]

inst_11:
TEST_CASE_VVR_M(4, 64, VINST, v1, v15, 4*8, x31, 4*8)
//sig[8*28]

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
    //sig[0*8..127*8]
    .fill 128, 8, 0xdeadbeefdeadbeef

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
