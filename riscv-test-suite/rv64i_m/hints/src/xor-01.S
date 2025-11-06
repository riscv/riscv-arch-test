/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 5, 2025
Description: This test verifies the xorw instruction as a hint whatever the value in the registers, 
              rd should be zero and there should be no architectural change.
              */ 
#include "model_test.h"
#include "arch_test.h"
RVTEST_ISA("RV64I_Zicsr")

.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT
RVTEST_CODE_BEGIN

#ifdef TEST_CASE_1

RVTEST_CASE(0,"//check ISA:=regex(.*64.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",xor)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: xor ; op1:x19; op2:x19; dest:x12; op1val:0x40000000000000;  op2val:0x40000000000000
TEST_RR_OP(xor,x0, x19, x19, 0x0, 0x40000000000000, 0x40000000000000, x3, 0, x5)

inst_1:
// opcode: xor ; op1:x28; op2:x2; dest:x2; op1val:0x5;  op2val:-0x20000000001
TEST_RR_OP(xor,x0, x28, x2, 0xfffffdfffffffffa, 0x5, -0x20000000001, x3, 8, x5)

inst_2:
// opcode: xor ; op1:x31; op2:x31; dest:x31; op1val:-0x400000001;  op2val:-0x400000001
TEST_RR_OP(xor,x0, x31, x31, 0x0, -0x400000001, -0x400000001, x3, 16, x5)

inst_3:
// opcode: xor ; op1:x11; op2:x25; dest:x10; op1val:-0x100001;  op2val:0x80000000000000
TEST_RR_OP(xor,x0, x11, x25, 0xff7fffffffefffff, -0x100001, 0x80000000000000, x3, 24, x5)

inst_4:
// opcode: xor ; op1:x17; op2:x20; dest:x17; op1val:0x8000000;  op2val:0x8000000
TEST_RR_OP(xor,x0, x17, x20, 0x0, 0x8000000, 0x8000000, x3, 32, x5)

inst_5:
// opcode: xor ; op1:x24; op2:x22; dest:x3; op1val:0x5;  op2val:-0x8000000000000000
TEST_RR_OP(xor,x0, x24, x22, 0x8000000000000005, 0x5, -0x8000000000000000, x3, 40, x5)

inst_6:
// opcode: xor ; op1:x8; op2:x3; dest:x22; op1val:0x2;  op2val:0x0
TEST_RR_OP(xor,x0, x8, x7, 0x2, 0x2, 0x0, x3, 48, x5)

inst_7:
// opcode: xor ; op1:x10; op2:x14; dest:x24; op1val:-0x100000000000001;  op2val:0x7fffffffffffffff
TEST_RR_OP(xor,x0, x10, x14, 0x8100000000000000, -0x100000000000001, 0x7fffffffffffffff, x3, 56, x5)

inst_8:
// opcode: xor ; op1:x2; op2:x4; dest:x15; op1val:-0x1000000000001;  op2val:0x1
TEST_RR_OP(xor,x0, x2, x4, 0xfffefffffffffffe, -0x1000000000001, 0x1, x3, 64, x5)

inst_9:
// opcode: xor ; op1:x21; op2:x29; dest:x23; op1val:-0x8000000000000000;  op2val:0x4
TEST_RR_OP(xor,x0, x21, x29, 0x8000000000000004, -0x8000000000000000, 0x4, x3, 72, x5)

inst_10:
// opcode: xor ; op1:x0; op2:x7; dest:x11; op1val:0x0;  op2val:-0x4001
TEST_RR_OP(xor,x0, x0, x7, 0xffffffffffffbfff, 0x0, -0x4001, x3, 80, x5)

inst_11:
// opcode: xor ; op1:x18; op2:x16; dest:x0; op1val:0x7fffffffffffffff;  op2val:0x7
TEST_RR_OP(xor,x0, x18, x16, 0, 0x7fffffffffffffff, 0x7, x3, 88, x5)

inst_12:
// opcode: xor ; op1:x25; op2:x27; dest:x14; op1val:0x1;  op2val:0x800000
TEST_RR_OP(xor,x0, x25, x27, 0x800001, 0x1, 0x800000, x3, 96, x5)

inst_13:
// opcode: xor ; op1:x30; op2:x23; dest:x29; op1val:0x2000000000;  op2val:0x2
TEST_RR_OP(xor,x0, x30, x23, 0x2000000002, 0x2000000000, 0x2, x3, 104, x5)

inst_14:
// opcode: xor ; op1:x6; op2:x1; dest:x28; op1val:0x6;  op2val:0x8
TEST_RR_OP(xor,x0, x6, x1, 0xe, 0x6, 0x8, x3, 112, x5)

inst_15:
// opcode: xor ; op1:x12; op2:x5; dest:x19; op1val:0x4000000000000;  op2val:0x10
TEST_RR_OP(xor,x0, x12, x5, 0x4000000000010, 0x4000000000000, 0x10, x3, 120, x11)

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
    .fill 64*(XLEN/32),4,0xdeadbeef

signature_x3_0:
    .fill 0*(XLEN/32),4,0xdeadbeef


signature_x3_1:
    .fill 64*(XLEN/32),4,0xdeadbeef



signature_x30_1:
    .fill 64*(XLEN/32),4,0xdeadbeef
    

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
