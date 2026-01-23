
/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 3, 2025
Description: This test verifies the xor instruction as a hint whatever the value in the register, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*32.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",xor)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: xor ; op1:x27; op2:x24; dest:x24; op1val:0x66666665;  op2val:0x3
TEST_RR_OP(xor,x0, x27, x24, 0x66666666, 0x66666665, 0x3, x3, 0, x20)

inst_1:
// opcode: xor ; op1:x13; op2:x13; dest:x10; op1val:0x5;  op2val:0x5
TEST_RR_OP(xor,x0, x13, x13, 0x0, 0x5, 0x5, x3, 4, x20)

inst_2:
// opcode: xor ; op1:x23; op2:x23; dest:x23; op1val:-0x4001;  op2val:-0x4001
TEST_RR_OP(xor,x0, x23, x23, 0x0, -0x4001, -0x4001, x3, 8, x20)

inst_3:
// opcode: xor ; op1:x28; op2:x14; dest:x28; op1val:-0x41;  op2val:0x8
TEST_RR_OP(xor,x0, x28, x14, 0xffffffb7, -0x41, 0x8, x3, 12, x20)

inst_4:
// opcode: xor ; op1:x1; op2:x2; dest:x18; op1val:-0x1;  op2val:-0x1
TEST_RR_OP(xor,x0, x1, x2, 0x0, -0x1, -0x1, x3, 16, x20)

inst_5:
// opcode: xor ; op1:x5; op2:x22; dest:x19; op1val:0x400000;  op2val:-0x80000000
TEST_RR_OP(xor,x0, x5, x22, 0x80400000, 0x400000, -0x80000000, x3, 20, x20)

inst_6:
// opcode: xor ; op1:x26; op2:x12; dest:x13; op1val:-0x11;  op2val:0x0
TEST_RR_OP(xor,x0, x26, x12, 0xffffffef, -0x11, 0x0, x3, 24, x20)

inst_7:
// opcode: xor ; op1:x12; op2:x11; dest:x4; op1val:-0x55555556;  op2val:0x3fffffff
TEST_RR_OP(xor,x0, x12, x11, 0xd5555555, -0x55555556, 0x3fffffff, x3, 28, x20)

inst_8:
// opcode: xor ; op1:x19; op2:x30; dest:x17; op1val:0x1;  op2val:0x1
TEST_RR_OP(xor,x0, x19, x30, 0x0, 0x1, 0x1, x3, 32, x20)

inst_9:
// opcode: xor ; op1:x11; op2:x1; dest:x3; op1val:-0x80000000;  op2val:-0x10000001
TEST_RR_OP(xor,x0, x11, x1, 0x6fffffff, -0x80000000, -0x10000001, x3, 36, x20)

inst_10:
// opcode: xor ; op1:x24; op2:x29; dest:x8; op1val:0x0;  op2val:-0xb504
TEST_RR_OP(xor,x0, x24, x29, 0xffff4afc, 0x0, -0xb504, x3, 40, x20)

inst_11:
// opcode: xor ; op1:x0; op2:x18; dest:x9; op1val:0x0;  op2val:0x1000
TEST_RR_OP(xor,x0, x0, x18, 0x1000, 0x0, 0x1000, x3, 44, x20)

inst_12:
// opcode: xor ; op1:x10; op2:x6; dest:x26; op1val:0x80000;  op2val:0x2
TEST_RR_OP(xor,x0, x10, x6, 0x80002, 0x80000, 0x2, x3, 48, x20)

inst_13:
// opcode: xor ; op1:x22; op2:x31; dest:x30; op1val:-0x21;  op2val:0x4
TEST_RR_OP(xor,x0, x22, x31, 0xffffffdb, -0x21, 0x4, x3, 52, x20)

inst_14:
// opcode: xor ; op1:x8; op2:x0; dest:x16; op1val:0x6;  op2val:0x0
TEST_RR_OP(xor,x0, x8, x0, 0x6, 0x6, 0x0, x3, 56, x20)

inst_15:
// opcode: xor ; op1:x16; op2:x27; dest:x15; op1val:0x5;  op2val:0x20
TEST_RR_OP(xor,x0, x16, x27, 0x25, 0x5, 0x20, x3, 60, x20)

inst_16:
// opcode: xor ; op1:x3; op2:x26; dest:x31; op1val:-0x200001;  op2val:0x40
TEST_RR_OP(xor,x0, x7, x26, 0xffdfffbf, -0x200001, 0x40, x3, 64, x19)


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
