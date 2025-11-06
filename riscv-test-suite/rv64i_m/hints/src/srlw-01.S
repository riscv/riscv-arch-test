
/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 5, 2025
Description: This test verifies the srlw instruction as a hint whatever the value in the registers, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*64.*);check ISA:=regex(.*RV64.*I.*Zicsr);def TEST_CASE_1=True;",srlw)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: srlw ; op1:x17; op2:x17; dest:x24; op1val:-0xb504f333;  op2val:-0xb504f333
TEST_RR_OP(srlw,x0, x17, x17, 0x257d8, -0xb504f333, -0xb504f333, x3, 0, x10)

inst_1:
// opcode: srlw ; op1:x3; op2:x12; dest:x12; op1val:0x400000000000000;  op2val:0x2
TEST_RR_OP(srlw,x0, x5, x12, 0x0, 0x400000000000000, 0x2, x3, 8, x10)

inst_2:
// opcode: srlw ; op1:x7; op2:x7; dest:x7; op1val:-0x10000000000001;  op2val:-0x10000000000001
TEST_RR_OP(srlw,x0, x7, x7, 0x1, -0x10000000000001, -0x10000000000001, x3, 16, x10)

inst_3:
// opcode: srlw ; op1:x9; op2:x15; dest:x22; op1val:0x800000000000;  op2val:0x0
TEST_RR_OP(srlw,x0, x9, x15, 0x0, 0x800000000000, 0x0, x3, 24, x10)

inst_4:
// opcode: srlw ; op1:x11; op2:x4; dest:x11; op1val:0x7;  op2val:0x7
TEST_RR_OP(srlw,x0, x11, x4, 0x0, 0x7, 0x7, x3, 32, x10)

inst_5:
// opcode: srlw ; op1:x4; op2:x24; dest:x1; op1val:-0x8000000000000000;  op2val:0xf
TEST_RR_OP(srlw,x0, x4, x24, 0x0, -0x8000000000000000, 0xf, x3, 40, x10)

inst_6:
// opcode: srlw ; op1:x2; op2:x18; dest:x0; op1val:0x0;  op2val:0x12
TEST_RR_OP(srlw,x0, x2, x18, 0, 0x0, 0x12, x3, 48, x10)

inst_7:
// opcode: srlw ; op1:x21; op2:x0; dest:x5; op1val:0x7fffffffffffffff;  op2val:0x0
TEST_RR_OP(srlw,x0, x21, x0, -0x1, 0x7fffffffffffffff, 0x0, x3, 56, x10)

inst_8:
// opcode: srlw ; op1:x15; op2:x9; dest:x21; op1val:0x1;  op2val:0x2
TEST_RR_OP(srlw,x0, x15, x9, 0x0, 0x1, 0x2, x3, 64, x10)

inst_9:
// opcode: srlw ; op1:x13; op2:x30; dest:x6; op1val:0x2;  op2val:0x13
TEST_RR_OP(srlw,x0, x13, x30, 0x0, 0x2, 0x13, x3, 72, x10)

inst_10:
// opcode: srlw ; op1:x22; op2:x20; dest:x23; op1val:0x4;  op2val:0xe
TEST_RR_OP(srlw,x0, x22, x20, 0x0, 0x4, 0xe, x3, 80, x10)

inst_11:
// opcode: srlw ; op1:x12; op2:x26; dest:x28; op1val:0x8;  op2val:0x12
TEST_RR_OP(srlw,x0, x12, x26, 0x0, 0x8, 0x12, x3, 88, x10)

inst_12:
// opcode: srlw ; op1:x24; op2:x31; dest:x2; op1val:0x10;  op2val:0x12
TEST_RR_OP(srlw,x0, x24, x31, 0x0, 0x10, 0x12, x3, 96, x10)

inst_13:
// opcode: srlw ; op1:x16; op2:x25; dest:x27; op1val:0x20;  op2val:0x1e
TEST_RR_OP(srlw,x0, x16, x25, 0x0, 0x20, 0x1e, x3, 104, x10)

inst_14:
// opcode: srlw ; op1:x31; op2:x1; dest:x15; op1val:0x40;  op2val:0x8
TEST_RR_OP(srlw,x0, x31, x1, 0x0, 0x40, 0x8, x3, 112, x10)

inst_15:
// opcode: srlw ; op1:x0; op2:x5; dest:x25; op1val:0x0;  op2val:0xd
TEST_RR_OP(srlw,x0, x0, x5, 0x0, 0x0, 0xd, x3, 120, x10)


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
