/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 3, 2025
Description: This test verifies the srli instruction as a hint whatever the value in the register, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*32.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",srli)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: srli ; op1:x30; dest:x8; op1val:-0xb504;  immval:0x2
TEST_IMM_OP( srli,x0, x30, 0x3fffd2bf, -0xb504, 0x2, x3, 0, x6)

inst_1:
// opcode: srli ; op1:x17; dest:x17; op1val:0x7;  immval:0x13
TEST_IMM_OP( srli,x0, x17, 0x0, 0x7, 0x13, x3, 4, x6)

inst_2:
// opcode: srli ; op1:x27; dest:x19; op1val:-0xb504;  immval:0x0
TEST_IMM_OP( srli,x0, x27, 0xffff4afc, -0xb504, 0x0, x3, 8, x6)

inst_3:
// opcode: srli ; op1:x29; dest:x9; op1val:0x3fffffff;  immval:0x0
TEST_IMM_OP( srli,x0, x29, 0x3fffffff, 0x3fffffff, 0x0, x3, 12, x6)

inst_4:
// opcode: srli ; op1:x25; dest:x22; op1val:-0xa;  immval:0x1f
TEST_IMM_OP( srli,x0, x25, 0x1, -0xa, 0x1f, x3, 16, x6)

inst_5:
// opcode: srli ; op1:x1; dest:x13; op1val:0x200;  immval:0x1f
TEST_IMM_OP( srli,x0, x1, 0x0, 0x200, 0x1f, x3, 20, x6)

inst_6:
// opcode: srli ; op1:x21; dest:x0; op1val:0x3;  immval:0x3
TEST_IMM_OP( srli,x0, x21, 0, 0x3, 0x3, x3, 24, x6)

inst_7:
// opcode: srli ; op1:x0; dest:x29; op1val:0x0;  immval:0x9
TEST_IMM_OP( srli,x0, x0, 0x0, 0x0, 0x9, x3, 28, x6)

inst_8:
// opcode: srli ; op1:x16; dest:x18; op1val:0x0;  immval:0x1
TEST_IMM_OP( srli,x0, x16, 0x0, 0x0, 0x1, x3, 32, x6)

inst_9:
// opcode: srli ; op1:x20; dest:x27; op1val:0x7fffffff;  immval:0x11
TEST_IMM_OP( srli,x0, x20, 0x3fff, 0x7fffffff, 0x11, x3, 36, x6)

inst_10:
// opcode: srli ; op1:x31; dest:x2; op1val:0x1;  immval:0x12
TEST_IMM_OP( srli,x0, x31, 0x0, 0x1, 0x12, x3, 40, x6)

inst_11:
// opcode: srli ; op1:x7; dest:x31; op1val:0x2;  immval:0x1d
TEST_IMM_OP( srli,x0, x7, 0x0, 0x2, 0x1d, x3, 44, x6)

inst_12:
// opcode: srli ; op1:x14; dest:x16; op1val:0x4;  immval:0xf
TEST_IMM_OP( srli,x0, x14, 0x0, 0x4, 0xf, x3, 48, x6)

inst_13:
// opcode: srli ; op1:x12; dest:x25; op1val:0x8;  immval:0x1b
TEST_IMM_OP( srli,x0, x12, 0x0, 0x8, 0x1b, x3, 52, x6)

inst_14:
// opcode: srli ; op1:x4; dest:x11; op1val:0x10;  immval:0xf
TEST_IMM_OP( srli,x0, x4, 0x0, 0x10, 0xf, x3, 56, x6)

inst_15:
// opcode: srli ; op1:x24; dest:x23; op1val:0x20;  immval:0x17
TEST_IMM_OP( srli,x0, x24, 0x0, 0x20, 0x17, x3, 60, x6)

inst_16:
// opcode: srli ; op1:x8; dest:x28; op1val:0x40;  immval:0xd
TEST_IMM_OP( srli,x0, x8, 0x0, 0x40, 0xd, x3, 64, x6)

inst_17:
// opcode: srli ; op1:x15; dest:x30; op1val:0x80;  immval:0x1e
TEST_IMM_OP( srli,x0, x15, 0x0, 0x80, 0x1e, x3, 68, x6)

inst_18:
// opcode: srli ; op1:x18; dest:x20; op1val:0x100;  immval:0x1f
TEST_IMM_OP( srli,x0, x18, 0x0, 0x100, 0x1f, x3, 72, x6)

inst_19:
// opcode: srli ; op1:x13; dest:x14; op1val:0x400;  immval:0x12
TEST_IMM_OP( srli,x0, x13, 0x0, 0x400, 0x12, x3, 76, x6)

inst_20:
// opcode: srli ; op1:x11; dest:x3; op1val:0x800;  immval:0xf
TEST_IMM_OP( srli,x0, x11, 0x0, 0x800, 0xf, x3, 80, x6)


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
