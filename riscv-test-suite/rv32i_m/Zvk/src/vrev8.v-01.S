// Copyright (c) 2023. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
// This assembly file tests the vrev8.v instruction.

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

RVTEST_CASE(0,"//check ISA:=regex(.*I.*V.*Zicsr.*Zvkb);def TEST_CASE_1=True;",vrev8.v)

RVTEST_V_ENABLE()
RVTEST_VALBASEUPD(DATA_BASE, dataset_tc1)
RVTEST_SIGBASE(SIG_BASE, signature_tc1)

// VREV8.V has the following inputs and outputs:
// - input VS2: Input data
// - input VM: Mask encoding (<nothing> or v0.t)
// - output VD: Byte reversed data

#define VINST vrev8.v

inst_1x8:
// This test will define v0, which will later be used as mask register
TEST_CASE_VV(1, 8, VINST, v0, v0, 0*8)
//sig[1*8]

inst_2x8:
TEST_CASE_VV(2, 8, VINST, v1, v2, 0*8)
//sig[2*8]

inst_3x8:
TEST_CASE_VV(3, 8, VINST, v4, v3, 0*8)
//sig[3*8]

inst_4x8:
TEST_CASE_VV(4, 8, VINST, v5, v6, 0*8)
//sig[4*8]

inst_8x8:
TEST_CASE_VV_M(8, 8, VINST, v8, v7, 0*8)
//sig[5*8]

inst_16x8:
TEST_CASE_VV(16, 8, VINST, v9, v10, 0*8)
//sig[7*8]

inst_31x8:
TEST_CASE_VV(31, 8, VINST, v12, v11, 0*8)
//sig[11*8]


inst_1x16:
TEST_CASE_VV_M(1, 16, VINST, v13, v14, 0*8)
//sig[12*8]

inst_2x16:
TEST_CASE_VV(2, 16, VINST, v16, v15, 0*8)
//sig[13*8]

inst_4x16:
TEST_CASE_VV(4, 16, VINST, v17, v18, 0*8)
//sig[14*8]

inst_8x16:
TEST_CASE_VV(8, 16, VINST, v20, v19, 0*8)
//sig[16*8]

inst_16x16:
TEST_CASE_VV_M(16, 16, VINST, v21, v22, 0*8)
//sig[20*8]

inst_31x16:
TEST_CASE_VV(31, 16, VINST, v24, v23, 0*8)
//sig[28*8]


inst_1x32:
TEST_CASE_VV(1, 32, VINST, v25, v26, 0*8)
//sig[29*8]

inst_2x32:
TEST_CASE_VV(2, 32, VINST, v28, v27, 0*8)
//sig[30*8]

inst_4x32:
TEST_CASE_VV(4, 32, VINST, v29, v30, 0*8)
//sig[32*8]

inst_8x32:
TEST_CASE_VV_M(8, 32, VINST, v1, v31, 0*8)
//sig[36*8]

inst_16x32:
TEST_CASE_VV(16, 32, VINST, v31, v31, 0*8)
//sig[44*8]


inst_1x64:
TEST_CASE_VV(1, 64, VINST, v1, v3, 0*8)
//sig[45*8]

inst_2x64:
TEST_CASE_VV(2, 64, VINST, v2, v4, 0*8)
//sig[47*8]

inst_4x64:
TEST_CASE_VV(4, 64, VINST, v3, v5, 0*8)
//sig[51*8]

inst_8x64:
TEST_CASE_VV(8, 64, VINST, v4, v6, 0*8)
//sig[59*8]


inst_0:
TEST_CASE_VV_M(1, 64, VINST, v5, v7, 8*8)
//sig[60*8]

inst_1:
TEST_CASE_VV(1, 64, VINST, v6, v8, 9*8)
//sig[61*8]

inst_2:
TEST_CASE_VV(1, 64, VINST, v7, v9, 10*8)
//sig[62*8]

inst_3:
TEST_CASE_VV(1, 64, VINST, v8, v10, 11*8)
//sig[63*8]

inst_4:
TEST_CASE_VV_M(1, 64, VINST, v9, v20, 12*8)
//sig[64*8]

inst_5:
TEST_CASE_VV(1, 64, VINST, v10, v30, 13*8)
//sig[65*8]

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
