// Copyright (c) 2023. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
// This assembly file tests the vsha2cl.vv instruction for SEW=64.

// Define special purpose registers before including test_macros_vector.h
#define DATA_BASE x3
#define SIG_BASE x4
#define VLENB_CACHE x5
#define HELPER_GPR x6

#include "test_macros_vector.h"

RVTEST_ISA("RV32IV_Zicsr_Zvknhb,RV64IV_Zicsr_Zvknhb")

.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT

RVTEST_CODE_BEGIN

#ifdef TEST_CASE_1

RVTEST_CASE(0,"//check ISA:=regex(.*I.*V.*Zicsr.*Zvknhb);def TEST_CASE_1=True;",vsha2cl.vv)

RVTEST_V_ENABLE()
RVTEST_VALBASEUPD(DATA_BASE, dataset_tc1)
RVTEST_SIGBASE(SIG_BASE, signature_tc1)

// VSHA2CL.VV has the following inputs and outputs:
// - input VD: Current state {c, d, g, h}
// - input VS1: MessageSched plus constant[3:0]
// - input VS2: Current state {a, b, e, f}
// - output VD: Next state {a, b, e, f}
// VSHA2CL.VV requires that SEW=64 (or 32) and AVL=multiple of 4

#define VINST vsha2cl.vv

inst_0:
TEST_CASE_WVV(4, 64, VINST, v0, 0*8, v1, 0*8, v2, 0*8)
//sig[4*8]

inst_1:
TEST_CASE_WVV(8, 64, VINST, v3, 1*8, v2, 0*8, v30, 20*8)
//sig[12*8]

inst_2:
TEST_CASE_WVV(12, 64, VINST, v4, 2*8, v5, 2*8, v28, 18*8)
//sig[24*8]

inst_3:
TEST_CASE_WVV(16, 64, VINST, v7, 0*8, v6, 0*8, v26, 16*8)
//sig[40*8]

inst_4:
TEST_CASE_WVV(20, 64, VINST, v8, 2*8, v9, 3*8, v24, 14*8)
//sig[60*8]

inst_5:
TEST_CASE_WVV(24, 64, VINST, v11, 2*8, v10, 3*8, v22, 12*8)
//sig[84*8]

inst_6:
TEST_CASE_WVV(28, 64, VINST, v12, 2*8, v13, 3*8, v20, 10*8)
//sig[112*8]

inst_7:
TEST_CASE_WVV(4, 64, VINST, v15, 2*8, v14, 3*8, v18, 8*8)
//sig[116*8]

inst_8:
TEST_CASE_WVV(4, 64, VINST, v16, 0*8, v17, 4*8, v16, 0*8)
//sig[120*8]

inst_9:
TEST_CASE_WVV(4, 64, VINST, v19, 4*8, v18, 0*8, v14, 4*8)
//sig[124*8]

inst_10:
TEST_CASE_WVV(4, 64, VINST, v20, 0*8, v21, 0*8, v12, 2*8)
//sig[128*8]

inst_11:
TEST_CASE_WVV(4, 64, VINST, v20, 0*8, v21, 11*8, v10, 0*8)
//sig[132*8]

inst_12:
TEST_CASE_WVV(4, 64, VINST, v23, 2*8, v22, 9*8, v8, 8*8)
//sig[136*8]

inst_13:
TEST_CASE_WVV(4, 64, VINST, v24, 4*8, v25, 7*8, v6, 6*8)
//sig[140*8]

inst_14:
TEST_CASE_WVV(4, 64, VINST, v27, 6*8, v26, 5*8, v4, 4*8)
//sig[144*8]

inst_15:
TEST_CASE_WVV(4, 64, VINST, v28, 8*8, v29, 3*8, v2, 2*8)
//sig[148*8]

inst_16:
TEST_CASE_WVV(4, 64, VINST, v31, 10*8, v30, 1*8, v0, 0*8)
//sig[156*8]

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
    //sig[0*8..255*8]
    .fill 256, 8, 0xdeadbeefdeadbeef

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
