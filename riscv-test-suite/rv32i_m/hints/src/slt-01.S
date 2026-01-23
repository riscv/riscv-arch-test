
/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 3, 2025
Description: This test verifies the slt instruction as a hint whatever the value in the register, 
              rd should be zero and there should be no architectural change.
              */
#include "model_test.h"
#include "arch_test.h"
RVTEST_ISA("RV32I_Zicsr")

.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT
RVTEST_CODE_BEGIN

#ifdef TEST_CASE_1

RVTEST_CASE(0,"//check ISA:=regex(.*32.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",slt)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)


inst_0:
// opcode: slt ; op1:x18; op2:x26; dest:x26; op1val:0x66666667;  op2val:0x66666667
TEST_RR_OP(slt,x0, x18, x26, 0x0, 0x66666667, 0x66666667, x3, 0, x6)

inst_1:
// opcode: slt ; op1:x20; op2:x20; dest:x1; op1val:0x33333334;  op2val:0x33333334
TEST_RR_OP(slt,x0, x20, x20, 0x0, 0x33333334, 0x33333334, x3, 4, x6)

inst_2:
// opcode: slt ; op1:x21; op2:x21; dest:x21; op1val:-0x4001;  op2val:-0x4001
TEST_RR_OP(slt,x0, x21, x21, 0x0, -0x4001, -0x4001, x3, 8, x6)

inst_3:
// opcode: slt ; op1:x15; op2:x27; dest:x15; op1val:-0x201;  op2val:0x5
TEST_RR_OP(slt,x0, x15, x27, 0x1, -0x201, 0x5, x3, 12, x6)

inst_4:
// opcode: slt ; op1:x5; op2:x18; dest:x7; op1val:0x33333334;  op2val:-0x80000000
TEST_RR_OP(slt,x0, x5, x18, 0x0, 0x33333334, -0x80000000, x3, 16, x6)

inst_5:
// opcode: slt ; op1:x25; op2:x19; dest:x17; op1val:0x8000000;  op2val:0x0
TEST_RR_OP(slt,x0, x25, x19, 0x0, 0x8000000, 0x0, x3, 20, x6)

inst_6:
// opcode: slt ; op1:x9; op2:x31; dest:x23; op1val:0x20000;  op2val:0x7fffffff
TEST_RR_OP(slt,x0, x9, x31, 0x1, 0x20000, 0x7fffffff, x3, 24, x6)

inst_7:
// opcode: slt ; op1:x2; op2:x15; dest:x11; op1val:-0x20001;  op2val:0x1
TEST_RR_OP(slt,x0, x2, x15, 0x1, -0x20001, 0x1, x3, 28, x6)

inst_8:
// opcode: slt ; op1:x28; op2:x13; dest:x22; op1val:-0x80000000;  op2val:0x400
TEST_RR_OP(slt,x0, x28, x13, 0x1, -0x80000000, 0x400, x3, 32, x6)

inst_9:
// opcode: slt ; op1:x10; op2:x7; dest:x30; op1val:0x0;  op2val:0x8
TEST_RR_OP(slt,x0, x10, x7, 0x1, 0x0, 0x8, x3, 36, x6)

inst_10:
// opcode: slt ; op1:x24; op2:x22; dest:x5; op1val:0x7fffffff;  op2val:-0x101
TEST_RR_OP(slt,x0, x24, x22, 0x0, 0x7fffffff, -0x101, x3, 40, x6)

inst_11:
// opcode: slt ; op1:x8; op2:x3; dest:x24; op1val:0x1;  op2val:-0x201
TEST_RR_OP(slt,x0, x8, x4, 0x0, 0x1, -0x201, x3, 44, x6)

inst_12:
// opcode: slt ; op1:x26; op2:x9; dest:x2; op1val:0x10000000;  op2val:0x2
TEST_RR_OP(slt,x0, x26, x9, 0x0, 0x10000000, 0x2, x3, 48, x6)

inst_13:
// opcode: slt ; op1:x4; op2:x14; dest:x8; op1val:0x8000;  op2val:0x4
TEST_RR_OP(slt,x0, x4, x14, 0x0, 0x8000, 0x4, x3, 52, x6)

inst_14:
// opcode: slt ; op1:x6; op2:x4; dest:x25; op1val:-0x1001;  op2val:0x10
TEST_RR_OP(slt,x0, x6, x4, 0x1, -0x1001, 0x10, x3, 56, x18)


RVTEST_SIGBASE( x30,signature_x30_1)
TEST_STORE_GPRS_AND_STATUS(x30)

#endif


RVTEST_CODE_END
RVMODEL_HALT

RVTEST_DATA_BEGIN
.align 4

rvtest_data:
.word 0xbabecafe
.word 0xbabecafe
.word 0xbabecafe
.word 0xbabecafe
RVTEST_DATA_END


RVMODEL_DATA_BEGIN
rvtest_sig_begin:
sig_begin_canary:
CANARY;


signature_x31_1:
    .fill 32*(XLEN/32),4,0xdeadbeef

signature_x3_0:
    .fill 0*(XLEN/32),4,0xdeadbeef


signature_x3_1:
    .fill 32*(XLEN/32),4,0xdeadbeef

signature_x30_1:
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
