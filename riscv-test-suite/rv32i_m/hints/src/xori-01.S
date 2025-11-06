/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 3, 2025
Description: This test verifies the xori instruction as a hint whatever the value in the register, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*32.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",xori)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: xori ; op1:x24; dest:x10; op1val:0x33333334;  immval:-0x800
TEST_IMM_OP( xori,x0, x24, 0xcccccb34, 0x33333334, -0x800, x3, 0, x13)

inst_1:
// opcode: xori ; op1:x18; dest:x18; op1val:0x4;  immval:0x0
TEST_IMM_OP( xori,x0, x18, 0x4, 0x4, 0x0, x3, 4, x13)

inst_2:
// opcode: xori ; op1:x15; dest:x24; op1val:-0x4;  immval:0x7ff
TEST_IMM_OP( xori,x0, x15, 0xfffff803, -0x4, 0x7ff, x3, 8, x13)

inst_3:
// opcode: xori ; op1:x11; dest:x20; op1val:0x2;  immval:0x1
TEST_IMM_OP( xori,x0, x11, 0x3, 0x3, 0x1, x3, 12, x13)

inst_4:
// opcode: xori ; op1:x7; dest:x21; op1val:-0x80000000;  immval:0x554
TEST_IMM_OP( xori,x0, x7, 0x80000554, -0x80000000, 0x554, x3, 16, x13)

inst_5:
// opcode: xori ; op1:x17; dest:x27; op1val:0x0;  immval:-0x401
TEST_IMM_OP( xori,x0, x17, 0xfffffbff, 0x0, -0x401, x3, 20, x13)

inst_6:
// opcode: xori ; op1:x22; dest:x1; op1val:0x7fffffff;  immval:-0xa
TEST_IMM_OP( xori,x0, x22, 0x80000009, 0x7fffffff, -0xa, x3, 24, x13)

inst_7:
// opcode: xori ; op1:x20; dest:x22; op1val:0x1;  immval:0x4
TEST_IMM_OP( xori,x0, x20, 0x5, 0x1, 0x4, x3, 28, x13)

inst_8:
// opcode: xori ; op1:x19; dest:x31; op1val:-0x201;  immval:-0x201
TEST_IMM_OP( xori,x0, x19, 0x0, -0x201, -0x201, x3, 32, x13)

inst_9:
// opcode: xori ; op1:x9; dest:x5; op1val:-0x21;  immval:0x2
TEST_IMM_OP( xori,x0, x9, 0xffffffdd, -0x21, 0x3, x3, 36, x13)

inst_10:
// opcode: xori ; op1:x28; dest:x29; op1val:-0x80000000;  immval:0x8
TEST_IMM_OP( xori,x0, x28, 0x80000008, -0x80000000, 0x8, x3, 40, x13)

inst_11:
// opcode: xori ; op1:x30; dest:x4; op1val:-0x40000001;  immval:0x10
TEST_IMM_OP( xori,x0, x30, 0xbfffffef, -0x40000001, 0x10, x3, 44, x13)

inst_12:
// opcode: xori ; op1:x27; dest:x8; op1val:0x7fffffff;  immval:0x20
TEST_IMM_OP( xori,x0, x27, 0x7fffffdf, 0x7fffffff, 0x20, x3, 48, x13)

inst_13:
// opcode: xori ; op1:x3; dest:x25; op1val:0x66666666;  immval:0x40
TEST_IMM_OP( xori,x0, x7, 0x66666626, 0x66666666, 0x40, x3, 52, x13)

inst_14:
// opcode: xori ; op1:x31; dest:x17; op1val:-0x80001;  immval:0x80
TEST_IMM_OP( xori,x0, x31, 0xfff7ff7f, -0x80001, 0x80, x3, 56, x13)

inst_15:
// opcode: xori ; op1:x29; dest:x16; op1val:-0xb504;  immval:0x100
TEST_IMM_OP( xori,x0, x29, 0xffff4bfc, -0xb504, 0x100, x3, 60, x13)


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
    .fill 32*(XLEN/32),4,0xdeadbeef

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
