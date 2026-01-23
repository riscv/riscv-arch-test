/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 5, 2025
Description: This test verifies the srli instruction as a hint whatever the value in the register or imm field, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*64.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",srli)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: srli ; op1:x26; dest:x26; op1val:-0x1;  immval:0x8
TEST_IMM_OP( srli,x0, x26, 0xffffffffffffff, -0x1, 0x8, x3, 0, x20)

inst_1:
// opcode: srli ; op1:x25; dest:x0; op1val:0xb504f333;  immval:0xe
TEST_IMM_OP( srli,x0, x25, 0, 0xb504f333, 0xe, x3, 8, x20)

inst_2:
// opcode: srli ; op1:x21; dest:x6; op1val:-0x2000000001;  immval:0x0
TEST_IMM_OP( srli,x0, x21, 0xffffffdfffffffff, -0x2000000001, 0x0, x3, 16, x20)

inst_3:
// opcode: srli ; op1:x17; dest:x5; op1val:0x6666666666666666;  immval:0x0
TEST_IMM_OP( srli,x0, x17, 0x6666666666666666, 0x6666666666666666, 0x0, x3, 24, x20)

inst_4:
// opcode: srli ; op1:x30; dest:x24; op1val:-0x8;  immval:0x3f
TEST_IMM_OP( srli,x0, x30, 0x1, -0x8, 0x3f, x3, 32, x20)

inst_5:
// opcode: srli ; op1:x4; dest:x1; op1val:0x8000000000000;  immval:0x3f
TEST_IMM_OP( srli,x0, x4, 0x0, 0x8000000000000, 0x3f, x3, 40, x20)

inst_6:
// opcode: srli ; op1:x9; dest:x13; op1val:0x3;  immval:0x3
TEST_IMM_OP( srli,x0, x9, 0x0, 0x3, 0x3, x3, 48, x20)

inst_7:
// opcode: srli ; op1:x2; dest:x3; op1val:-0x8000000000000000;  immval:0x9
TEST_IMM_OP( srli,x0, x2, 0x40000000000000, -0x8000000000000000, 0x9, x3, 56, x20)

inst_8:
// opcode: srli ; op1:x8; dest:x10; op1val:0x0;  immval:0x3
TEST_IMM_OP( srli,x0, x8, 0x0, 0x0, 0x3, x3, 64, x20)

inst_9:
// opcode: srli ; op1:x6; dest:x23; op1val:0x7fffffffffffffff;  immval:0xb
TEST_IMM_OP( srli,x0, x6, 0xfffffffffffff, 0x7fffffffffffffff, 0xb, x3, 72, x20)

inst_10:
// opcode: srli ; op1:x12; dest:x28; op1val:0x1;  immval:0x15
TEST_IMM_OP( srli,x0, x12, 0x0, 0x1, 0x15, x3, 80, x20)

inst_11:
// opcode: srli ; op1:x15; dest:x7; op1val:0x2;  immval:0x3b
TEST_IMM_OP( srli,x0, x15, 0x0, 0x2, 0x3b, x3, 88, x20)

inst_12:
// opcode: srli ; op1:x11; dest:x15; op1val:0x4;  immval:0x3f
TEST_IMM_OP( srli,x0, x11, 0x0, 0x4, 0x3f, x3, 96, x20)

inst_13:
// opcode: srli ; op1:x19; dest:x9; op1val:0x8;  immval:0x8
TEST_IMM_OP( srli,x0, x19, 0x0, 0x8, 0x8, x3, 104, x20)

inst_14:
// opcode: srli ; op1:x28; dest:x25; op1val:0x10;  immval:0x7
TEST_IMM_OP( srli,x0, x28, 0x0, 0x10, 0x7, x3, 112, x20)

inst_15:
// opcode: srli ; op1:x27; dest:x31; op1val:0x20;  immval:0x11
TEST_IMM_OP( srli,x0, x27, 0x0, 0x20, 0x11, x3, 120, x20)


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
