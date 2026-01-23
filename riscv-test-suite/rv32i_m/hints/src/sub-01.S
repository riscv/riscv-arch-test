/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 3, 2025
Description: This test verifies the sub instruction as a hint whatever the value in the register, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*32.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",sub)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: sub ; op1:x24; op2:x26; dest:x26; op1val:0x55555554;  op2val:0x6
TEST_RR_OP(sub,x0, x24, x26, 0x5555554e, 0x55555554, 0x6, x3, 0, x2)

inst_1:
// opcode: sub ; op1:x17; op2:x17; dest:x23; op1val:0x2000000;  op2val:0x2000000
TEST_RR_OP(sub,x0, x17, x17, 0x0, 0x2000000, 0x2000000, x3, 4, x2)

inst_2:
// opcode: sub ; op1:x16; op2:x16; dest:x16; op1val:-0x7;  op2val:-0x7
TEST_RR_OP(sub,x0, x16, x16, 0x0, -0x7, -0x7, x3, 8, x2)

inst_3:
// opcode: sub ; op1:x31; op2:x19; dest:x31; op1val:-0x3;  op2val:0x66666665
TEST_RR_OP(sub,x0, x31, x19, 0x99999998, -0x3, 0x66666665, x3, 12, x2)

inst_4:
// opcode: sub ; op1:x23; op2:x14; dest:x8; op1val:0x80000;  op2val:0x80000
TEST_RR_OP(sub,x0, x23, x14, 0x0, 0x80000, 0x80000, x3, 16, x2)

inst_5:
// opcode: sub ; op1:x13; op2:x24; dest:x18; op1val:-0x4000001;  op2val:-0x80000000
TEST_RR_OP(sub,x0, x13, x24, 0x7bffffff, -0x4000001, -0x80000000, x3, 20, x2)

inst_6:
// opcode: sub ; op1:x12; op2:x4; dest:x0; op1val:0x20;  op2val:0x0
TEST_RR_OP(sub,x0, x12, x4, 0, 0x20, 0x0, x3, 24, x2)

inst_7:
// opcode: sub ; op1:x22; op2:x9; dest:x10; op1val:-0x20000001;  op2val:0x7fffffff
TEST_RR_OP(sub,x0, x22, x9, 0x60000000, -0x20000001, 0x7fffffff, x3, 28, x2)

inst_8:
// opcode: sub ; op1:x10; op2:x27; dest:x25; op1val:0x10000;  op2val:0x1
TEST_RR_OP(sub,x0, x10, x27, 0xffff, 0x10000, 0x3, x3, 32, x2)

inst_9:
// opcode: sub ; op1:x8; op2:x3; dest:x14; op1val:-0x80000000;  op2val:-0x40000000
TEST_RR_OP(sub,x0, x8, x9, 0xc0000000, -0x80000000, -0x40000000, x3, 36, x2)

inst_10:
// opcode: sub ; op1:x25; op2:x30; dest:x29; op1val:0x0;  op2val:0x200000
TEST_RR_OP(sub,x0, x25, x30, 0xffe00000, 0x0, 0x200000, x3, 40, x2)

inst_11:
// opcode: sub ; op1:x18; op2:x8; dest:x15; op1val:0x7fffffff;  op2val:0x2000
TEST_RR_OP(sub,x0, x18, x8, 0x7fffdfff, 0x7fffffff, 0x2000, x3, 44, x2)

inst_12:
// opcode: sub ; op1:x14; op2:x15; dest:x3; op1val:0x1;  op2val:0x10
TEST_RR_OP(sub,x0, x14, x15, 0xfffffff1, 0x3, 0x10, x3, 48, x2)

inst_13:
// opcode: sub ; op1:x26; op2:x29; dest:x13; op1val:-0x7;  op2val:0x2
TEST_RR_OP(sub,x0, x26, x29, 0xfffffff7, -0x7, 0x2, x3, 52, x2)

inst_14:
// opcode: sub ; op1:x21; op2:x31; dest:x19; op1val:0x2;  op2val:0x4
TEST_RR_OP(sub,x0, x21, x31, 0xfffffffe, 0x2, 0x4, x3, 56, x2)

inst_15:
// opcode: sub ; op1:x30; op2:x5; dest:x11; op1val:-0x1000001;  op2val:0x8
TEST_RR_OP(sub,x0, x30, x5, 0xfefffff7, -0x1000001, 0x8, x3, 60, x2)

inst_16:
// opcode: sub ; op1:x28; op2:x7; dest:x30; op1val:-0x55555556;  op2val:0x20
TEST_RR_OP(sub,x0, x28, x7, 0xaaaaaa8a, -0x55555556, 0x20, x3, 64, x2)


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
