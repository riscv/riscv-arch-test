/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 3, 2025
Description: This test verifies the srai instruction as a hint whatever the value in the register, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*32.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",srai)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)


inst_0:
// opcode: srai ; op1:x31; dest:x25; op1val:-0x9;  immval:0x9
TEST_IMM_OP( srai,x0, x31, -0x1, -0x9, 0x9, x3, 0, x6)

inst_1:
// opcode: srai ; op1:x10; dest:x10; op1val:0x5;  immval:0x1
TEST_IMM_OP( srai,x0, x10, 0x2, 0x5, 0x1, x3, 4, x6)

inst_2:
// opcode: srai ; op1:x8; dest:x28; op1val:-0x1000001;  immval:0x0
TEST_IMM_OP( srai,x0, x8, -0x1000001, -0x1000001, 0x0, x3, 8, x6)

inst_3:
// opcode: srai ; op1:x17; dest:x5; op1val:0x100000;  immval:0x0
TEST_IMM_OP( srai,x0, x17, 0x100000, 0x100000, 0x0, x3, 12, x6)

inst_4:
// opcode: srai ; op1:x23; dest:x27; op1val:-0x20001;  immval:0x1f
TEST_IMM_OP( srai,x0, x23, -0x1, -0x20001, 0x1f, x3, 16, x6)

inst_5:
// opcode: srai ; op1:x13; dest:x20; op1val:0x1;  immval:0x1f
TEST_IMM_OP( srai,x0, x13, 0x0, 0x1, 0x1f, x3, 20, x6)

inst_6:
// opcode: srai ; op1:x22; dest:x11; op1val:0x4;  immval:0x4
TEST_IMM_OP( srai,x0, x22, 0x0, 0x3, 0x3, x3, 24, x6)

inst_7:
// opcode: srai ; op1:x7; dest:x30; op1val:-0x80000000;  immval:0x0
TEST_IMM_OP( srai,x0, x7, -0x80000000, -0x80000000, 0x0, x3, 28, x6)

inst_8:
// opcode: srai ; op1:x18; dest:x14; op1val:0x0;  immval:0xe
TEST_IMM_OP( srai,x0, x18, 0x0, 0x0, 0xe, x3, 32, x6)

inst_9:
// opcode: srai ; op1:x3; dest:x19; op1val:0x7fffffff;  immval:0x1f
TEST_IMM_OP( srai,x0, x4, 0x0, 0x7fffffff, 0x1f, x3, 36, x6)

inst_10:
// opcode: srai ; op1:x25; dest:x29; op1val:0x2;  immval:0x11
TEST_IMM_OP( srai,x0, x25, 0x0, 0x2, 0x11, x3, 40, x6)

inst_11:
// opcode: srai ; op1:x30; dest:x3; op1val:0x8;  immval:0x11
TEST_IMM_OP( srai,x0, x30, 0x0, 0x8, 0x11, x3, 44, x6)

inst_12:
// opcode: srai ; op1:x2; dest:x22; op1val:0x10;  immval:0x12
TEST_IMM_OP( srai,x0, x2, 0x0, 0x10, 0x12, x3, 48, x6)

inst_13:
// opcode: srai ; op1:x12; dest:x2; op1val:0x20;  immval:0xd
TEST_IMM_OP( srai,x0, x12, 0x0, 0x20, 0xd, x3, 52, x6)

inst_14:
// opcode: srai ; op1:x1; dest:x12; op1val:0x40;  immval:0x17
TEST_IMM_OP( srai,x0, x1, 0x0, 0x40, 0x17, x3, 56, x6)

inst_15:
// opcode: srai ; op1:x20; dest:x24; op1val:0x80;  immval:0x9
TEST_IMM_OP( srai,x0, x20, 0x0, 0x80, 0x9, x3, 60, x6)


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
