
/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 5, 2025
Description: This test verifies the srai instruction as a hint whatever the value in the register or imm field, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*64.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",srai)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: srai ; op1:x13; dest:x13; op1val:-0x400000000000001;  immval:0x6
TEST_IMM_OP( srai,x0, x13, -0x10000000000001, -0x400000000000001, 0x6, x3, 0, x9)

inst_1:
// opcode: srai ; op1:x6; dest:x2; op1val:0x4;  immval:0xc
TEST_IMM_OP( srai,x0, x6, 0x0, 0x4, 0xc, x3, 8, x9)

inst_2:
// opcode: srai ; op1:x15; dest:x28; op1val:-0xa;  immval:0x0
TEST_IMM_OP( srai,x0, x15, -0xa, -0xa, 0x0, x3, 16, x9)

inst_3:
// opcode: srai ; op1:x18; dest:x30; op1val:0x9;  immval:0x0
TEST_IMM_OP( srai,x0, x18, 0x9, 0x9, 0x0, x3, 24, x9)

inst_4:
// opcode: srai ; op1:x30; dest:x29; op1val:-0x2000001;  immval:0x3f
TEST_IMM_OP( srai,x0, x30, -0x1, -0x2000001, 0x3f, x3, 32, x9)

inst_5:
// opcode: srai ; op1:x27; dest:x15; op1val:0x10000;  immval:0x3f
TEST_IMM_OP( srai,x0, x27, 0x0, 0x10000, 0x3f, x3, 40, x9)

inst_6:
// opcode: srai ; op1:x23; dest:x14; op1val:0x1;  immval:0x1
TEST_IMM_OP( srai,x0, x23, 0x0, 0x1, 0x1, x3, 48, x9)

inst_7:
// opcode: srai ; op1:x29; dest:x27; op1val:-0x8000000000000000;  immval:0x20
TEST_IMM_OP( srai,x0, x29, -0x80000000, -0x8000000000000000, 0x20, x3, 56, x9)

inst_8:
// opcode: srai ; op1:x31; dest:x22; op1val:0x0;  immval:0x7
TEST_IMM_OP( srai,x0, x31, 0x0, 0x0, 0x7, x3, 64, x9)

inst_9:
// opcode: srai ; op1:x4; dest:x16; op1val:0x7fffffffffffffff;  immval:0xc
TEST_IMM_OP( srai,x0, x4, 0x7ffffffffffff, 0x7fffffffffffffff, 0xc, x3, 72, x9)

inst_10:
// opcode: srai ; op1:x24; dest:x21; op1val:0x2;  immval:0x11
TEST_IMM_OP( srai,x0, x24, 0x0, 0x2, 0x11, x3, 80, x9)

inst_11:
// opcode: srai ; op1:x20; dest:x0; op1val:0x8;  immval:0x2a
TEST_IMM_OP( srai,x0, x20, 0, 0x8, 0x2a, x3, 88, x9)

inst_12:
// opcode: srai ; op1:x28; dest:x19; op1val:0x10;  immval:0x1f
TEST_IMM_OP( srai,x0, x28, 0x0, 0x10, 0x1f, x3, 96, x9)

inst_13:
// opcode: srai ; op1:x8; dest:x18; op1val:0x20;  immval:0x3
TEST_IMM_OP( srai,x0, x8, 0x4, 0x20, 0x3, x3, 104, x9)

inst_14:
// opcode: srai ; op1:x3; dest:x26; op1val:0x40;  immval:0xb
TEST_IMM_OP( srai,x0, x5, 0x0, 0x40, 0xb, x3, 112, x9)

inst_15:
// opcode: srai ; op1:x1; dest:x23; op1val:0x80;  immval:0x12
TEST_IMM_OP( srai,x0, x1, 0x0, 0x80, 0x12, x3, 120, x9)


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
