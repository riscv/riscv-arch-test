/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 4, 2025
Description: This test verifies the sllw instruction as a hint whatever the value in the registers, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*64.*);check ISA:=regex(.*RV64.*I.*Zicsr);def TEST_CASE_1=True;",sllw)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: sllw ; op1:x7; op2:x7; dest:x14; op1val:-0x800000000001;  op2val:-0x800000000001
TEST_RR_OP(sllw,x0, x7, x7, -0x80000000, -0x800000000001, -0x800000000001, x3, 0, x13)

inst_1:
// opcode: sllw ; op1:x27; op2:x30; dest:x30; op1val:0x400000000000000;  op2val:0x17
TEST_RR_OP(sllw,x0, x27, x30, 0x0, 0x400000000000000, 0x17, x3, 8, x13)

inst_2:
// opcode: sllw ; op1:x5; op2:x5; dest:x5; op1val:-0x6;  op2val:-0x6
TEST_RR_OP(sllw,x0, x5, x5, -0x18000000, -0x6, -0x6, x3, 16, x13)

inst_3:
// opcode: sllw ; op1:x18; op2:x15; dest:x22; op1val:0x10000000;  op2val:0x0
TEST_RR_OP(sllw,x0, x18, x15, 0x10000000, 0x10000000, 0x0, x3, 24, x13)

inst_4:
// opcode: sllw ; op1:x26; op2:x22; dest:x26; op1val:0x5;  op2val:0x5
TEST_RR_OP(sllw,x0, x26, x22, 0xa0, 0x5, 0x5, x3, 32, x13)

inst_5:
// opcode: sllw ; op1:x14; op2:x23; dest:x29; op1val:-0x8000000000000000;  op2val:0x2
TEST_RR_OP(sllw,x0, x14, x23, 0x0, -0x8000000000000000, 0x2, x3, 40, x13)

inst_6:
// opcode: sllw ; op1:x12; op2:x14; dest:x9; op1val:0x0;  op2val:0x11
TEST_RR_OP(sllw,x0, x12, x14, 0x0, 0x0, 0x11, x3, 48, x13)

inst_7:
// opcode: sllw ; op1:x10; op2:x0; dest:x1; op1val:0x7fffffffffffffff;  op2val:0x0
TEST_RR_OP(sllw,x0, x10, x0, -0x1, 0x7fffffffffffffff, 0x0, x3, 56, x13)

inst_8:
// opcode: sllw ; op1:x31; op2:x8; dest:x19; op1val:0x1;  op2val:0x15
TEST_RR_OP(sllw,x0, x31, x8, 0x200000, 0x1, 0x15, x3, 64, x13)

inst_9:
// opcode: sllw ; op1:x23; op2:x27; dest:x17; op1val:0x2;  op2val:0x17
TEST_RR_OP(sllw,x0, x23, x27, 0x1000000, 0x2, 0x17, x3, 72, x13)

inst_10:
// opcode: sllw ; op1:x17; op2:x26; dest:x25; op1val:0x4;  op2val:0x8
TEST_RR_OP(sllw,x0, x17, x26, 0x400, 0x3, 0x8, x3, 80, x13)

inst_11:
// opcode: sllw ; op1:x11; op2:x12; dest:x16; op1val:0x8;  op2val:0x0
TEST_RR_OP(sllw,x0, x11, x12, 0x8, 0x8, 0x0, x3, 88, x13)

inst_12:
// opcode: sllw ; op1:x24; op2:x3; dest:x27; op1val:0x10;  op2val:0x0
TEST_RR_OP(sllw,x0, x24, x5, 0x10, 0x10, 0x0, x3, 96, x13)

inst_13:
// opcode: sllw ; op1:x16; op2:x10; dest:x7; op1val:0x20;  op2val:0x2
TEST_RR_OP(sllw,x0, x16, x10, 0x80, 0x20, 0x2, x3, 104, x13)

inst_14:
// opcode: sllw ; op1:x2; op2:x1; dest:x0; op1val:0x40;  op2val:0x11
TEST_RR_OP(sllw,x0, x2, x1, 0, 0x40, 0x11, x3, 112, x13)

inst_15:
// opcode: sllw ; op1:x28; op2:x21; dest:x6; op1val:0x80;  op2val:0x0
TEST_RR_OP(sllw,x0, x28, x21, 0x80, 0x80, 0x0, x3, 120, x13)

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
