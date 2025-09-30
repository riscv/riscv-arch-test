/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 5, 2025
Description: This test verifies the sraw instruction as a hint whatever the value in the registers, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*64.*);check ISA:=regex(.*RV64.*I.*Zicsr);def TEST_CASE_1=True;",sraw)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: sraw ; op1:x13; op2:x13; dest:x2; op1val:-0x101;  op2val:-0x101
TEST_RR_OP(sraw,x0, x13, x13, -0x1, -0x101, -0x101, x3, 0, x14)

inst_1:
// opcode: sraw ; op1:x5; op2:x15; dest:x15; op1val:0x1000;  op2val:0x1f
TEST_RR_OP(sraw,x0, x5, x15, 0x0, 0x1000, 0x1f, x3, 8, x14)

inst_2:
// opcode: sraw ; op1:x6; op2:x6; dest:x6; op1val:-0x20001;  op2val:-0x20001
TEST_RR_OP(sraw,x0, x6, x6, -0x1, -0x20001, -0x20001, x3, 16, x14)

inst_3:
// opcode: sraw ; op1:x25; op2:x26; dest:x13; op1val:0x80000;  op2val:0x0
TEST_RR_OP(sraw,x0, x25, x26, 0x80000, 0x80000, 0x0, x3, 24, x14)

inst_4:
// opcode: sraw ; op1:x23; op2:x11; dest:x23; op1val:0x9;  op2val:0x9
TEST_RR_OP(sraw,x0, x23, x11, 0x0, 0x9, 0x9, x3, 32, x14)

inst_5:
// opcode: sraw ; op1:x9; op2:x18; dest:x0; op1val:-0x8000000000000000;  op2val:0xe
TEST_RR_OP(sraw,x0, x9, x18, 0, -0x8000000000000000, 0xe, x3, 40, x14)

inst_6:
// opcode: sraw ; op1:x11; op2:x27; dest:x9; op1val:0x0;  op2val:0x13
TEST_RR_OP(sraw,x0, x11, x27, 0x0, 0x0, 0x13, x3, 48, x14)

inst_7:
// opcode: sraw ; op1:x30; op2:x12; dest:x8; op1val:0x7fffffffffffffff;  op2val:0x15
TEST_RR_OP(sraw,x0, x30, x12, -0x1, 0x7fffffffffffffff, 0x15, x3, 56, x14)

inst_8:
// opcode: sraw ; op1:x29; op2:x7; dest:x21; op1val:0x1;  op2val:0x0
TEST_RR_OP(sraw,x0, x29, x7, 0x1, 0x1, 0x0, x3, 64, x14)

inst_9:
// opcode: sraw ; op1:x0; op2:x24; dest:x5; op1val:0x0;  op2val:0xa
TEST_RR_OP(sraw,x0, x0, x24, 0x0, 0x0, 0xa, x3, 72, x14)

inst_10:
// opcode: sraw ; op1:x19; op2:x22; dest:x27; op1val:0x4;  op2val:0x13
TEST_RR_OP(sraw,x0, x19, x22, 0x0, 0x4, 0x13, x3, 80, x14)

inst_11:
// opcode: sraw ; op1:x17; op2:x4; dest:x1; op1val:0x8;  op2val:0x9
TEST_RR_OP(sraw,x0, x17, x4, 0x0, 0x8, 0x9, x3, 88, x14)

inst_12:
// opcode: sraw ; op1:x1; op2:x25; dest:x31; op1val:0x10;  op2val:0x17
TEST_RR_OP(sraw,x0, x1, x25, 0x0, 0x10, 0x17, x3, 96, x14)

inst_13:
// opcode: sraw ; op1:x10; op2:x9; dest:x30; op1val:0x20;  op2val:0xf
TEST_RR_OP(sraw,x0, x10, x9, 0x0, 0x20, 0xf, x3, 104, x14)

inst_14:
// opcode: sraw ; op1:x16; op2:x23; dest:x26; op1val:0x40;  op2val:0x17
TEST_RR_OP(sraw,x0, x16, x23, 0x0, 0x40, 0x17, x3, 112, x14)


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
