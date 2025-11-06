/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 5, 2025
Description: This test verifies the srl instruction as a hint whatever the value in the registers, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*64.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",srl)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: srl ; op1:x2; op2:x2; dest:x13; op1val:-0x8000000000000000;  op2val:-0x8000000000000000
TEST_RR_OP(srl,x0, x2, x2, 0x8000000000000000, -0x8000000000000000, -0x8000000000000000, x3, 0, x14)

inst_1:
// opcode: srl ; op1:x30; op2:x21; dest:x21; op1val:0x2000000000;  op2val:0x9
TEST_RR_OP(srl,x0, x30, x21, 0x10000000, 0x2000000000, 0x9, x3, 8, x14)

inst_2:
// opcode: srl ; op1:x29; op2:x29; dest:x29; op1val:-0x400000001;  op2val:-0x400000001
TEST_RR_OP(srl,x0, x29, x29, 0x1, -0x400000001, -0x400000001, x3, 16, x14)

inst_3:
// opcode: srl ; op1:x24; op2:x9; dest:x2; op1val:0x2000;  op2val:0x0
TEST_RR_OP(srl,x0, x24, x9, 0x2000, 0x2000, 0x0, x3, 24, x14)

inst_4:
// opcode: srl ; op1:x28; op2:x22; dest:x28; op1val:0x8;  op2val:0x8
TEST_RR_OP(srl,x0, x28, x22, 0x0, 0x8, 0x8, x3, 32, x14)

inst_5:
// opcode: srl ; op1:x27; op2:x8; dest:x24; op1val:0x0;  op2val:0x3f
TEST_RR_OP(srl,x0, x27, x8, 0x0, 0x0, 0x3f, x3, 40, x14)

inst_6:
// opcode: srl ; op1:x19; op2:x24; dest:x27; op1val:0x7fffffffffffffff;  op2val:0x9
TEST_RR_OP(srl,x0, x19, x24, 0x3fffffffffffff, 0x7fffffffffffffff, 0x9, x3, 48, x14)

inst_7:
// opcode: srl ; op1:x13; op2:x1; dest:x7; op1val:0x1;  op2val:0x15
TEST_RR_OP(srl,x0, x13, x1, 0x0, 0x1, 0x15, x3, 56, x14)

inst_8:
// opcode: srl ; op1:x17; op2:x5; dest:x20; op1val:0x2;  op2val:0x5
TEST_RR_OP(srl,x0, x17, x5, 0x0, 0x2, 0x5, x3, 64, x14)

inst_9:
// opcode: srl ; op1:x15; op2:x19; dest:x12; op1val:0x4;  op2val:0xc
TEST_RR_OP(srl,x0, x15, x19, 0x0, 0x4, 0xc, x3, 72, x14)

inst_10:
// opcode: srl ; op1:x0; op2:x11; dest:x6; op1val:0x0;  op2val:0x3b
TEST_RR_OP(srl,x0, x0, x11, 0x0, 0x0, 0x3b, x3, 80, x14)

inst_11:
// opcode: srl ; op1:x7; op2:x27; dest:x26; op1val:0x20;  op2val:0x4
TEST_RR_OP(srl,x0, x7, x27, 0x2, 0x20, 0x4, x3, 88, x14)

inst_12:
// opcode: srl ; op1:x16; op2:x20; dest:x3; op1val:0x40;  op2val:0x3d
TEST_RR_OP(srl,x0, x16, x20, 0x0, 0x40, 0x3d, x3, 96, x14)

inst_13:
// opcode: srl ; op1:x9; op2:x10; dest:x25; op1val:0x80;  op2val:0xe
TEST_RR_OP(srl,x0, x9, x10, 0x0, 0x80, 0xe, x3, 104, x14)

inst_14:
// opcode: srl ; op1:x8; op2:x31; dest:x22; op1val:0x100;  op2val:0x1
TEST_RR_OP(srl,x0, x8, x31, 0x80, 0x100, 0x1, x3, 112, x14)

inst_15:
// opcode: srl ; op1:x26; op2:x25; dest:x0; op1val:0x200;  op2val:0x3f
TEST_RR_OP(srl,x0, x26, x25, 0, 0x200, 0x3f, x3, 120, x24)

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
