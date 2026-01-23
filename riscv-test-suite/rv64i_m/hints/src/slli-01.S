
/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 4, 2025
Description: This test verifies the slli instruction as a hint whatever the value in the register or imm field, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*64.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",slli)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: slli ; op1:x5; dest:x5; op1val:-0x101;  immval:0xf
TEST_IMM_OP( slli,x0, x5, 0xffffffffff7f8000, -0x101, 0xf, x3, 0, x17)

inst_1:
// opcode: slli ; op1:x8; dest:x13; op1val:0x4;  immval:0xe
TEST_IMM_OP( slli,x0, x8, 0x10000, 0x4, 0xe, x3, 8, x17)

inst_2:
// opcode: slli ; op1:x29; dest:x21; op1val:-0x9;  immval:0x0
TEST_IMM_OP( slli,x0, x29, 0xfffffffffffffff7, -0x9, 0x0, x3, 16, x17)

inst_3:
// opcode: slli ; op1:x28; dest:x16; op1val:0x4;  immval:0x0
TEST_IMM_OP( slli,x0, x28, 0x4, 0x4, 0x0, x3, 24, x17)

inst_4:
// opcode: slli ; op1:x15; dest:x10; op1val:-0x20000001;  immval:0x3f
TEST_IMM_OP( slli,x0, x15, 0x8000000000000000, -0x20000001, 0x3f, x3, 32, x17)

inst_5:
// opcode: slli ; op1:x19; dest:x12; op1val:0x10000000000000;  immval:0x3f
TEST_IMM_OP( slli,x0, x19, 0x0, 0x10000000000000, 0x3f, x3, 40, x17)

inst_6:
// opcode: slli ; op1:x22; dest:x8; op1val:0x2;  immval:0x2
TEST_IMM_OP( slli,x0, x22, 0x8, 0x2, 0x2, x3, 48, x17)

inst_7:
// opcode: slli ; op1:x6; dest:x7; op1val:-0x8000000000000000;  immval:0xb
TEST_IMM_OP( slli,x0, x6, 0x0, -0x8000000000000000, 0xb, x3, 56, x17)

inst_8:
// opcode: slli ; op1:x27; dest:x24; op1val:0x0;  immval:0xf
TEST_IMM_OP( slli,x0, x27, 0x0, 0x0, 0xf, x3, 64, x17)

inst_9:
// opcode: slli ; op1:x23; dest:x11; op1val:0x7fffffffffffffff;  immval:0x7
TEST_IMM_OP( slli,x0, x23, 0xffffffffffffff80, 0x7fffffffffffffff, 0x7, x3, 72, x17)

inst_10:
// opcode: slli ; op1:x14; dest:x9; op1val:0x1;  immval:0x3b
TEST_IMM_OP( slli,x0, x14, 0x800000000000000, 0x1, 0x3b, x3, 80, x17)

inst_11:
// opcode: slli ; op1:x26; dest:x14; op1val:0x8;  immval:0x2f
TEST_IMM_OP( slli,x0, x26, 0x4000000000000, 0x8, 0x2f, x3, 88, x17)

inst_12:
// opcode: slli ; op1:x7; dest:x0; op1val:0x10;  immval:0xe
TEST_IMM_OP( slli,x0, x7, 0, 0x10, 0xe, x3, 96, x17)

inst_13:
// opcode: slli ; op1:x30; dest:x18; op1val:0x20;  immval:0x5
TEST_IMM_OP( slli,x0, x30, 0x400, 0x20, 0x5, x3, 104, x17)

inst_14:
// opcode: slli ; op1:x24; dest:x28; op1val:0x40;  immval:0x2f
TEST_IMM_OP( slli,x0, x24, 0x20000000000000, 0x40, 0x2f, x3, 112, x17)

inst_15:
// opcode: slli ; op1:x4; dest:x1; op1val:0x80;  immval:0x12
TEST_IMM_OP( slli,x0, x4, 0x2000000, 0x80, 0x12, x3, 120, x17)

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
