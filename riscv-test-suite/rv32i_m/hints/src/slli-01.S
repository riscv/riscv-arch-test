/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 3, 2025
Description: This test verifies the slli instruction as a hint whatever the value in the register and imm field, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*32.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",slli)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)


inst_0:
// opcode: slli ; op1:x17; dest:x27; op1val:-0x40000001;  immval:0x1d
TEST_IMM_OP( slli,x0, x17, 0xe0000000, -0x40000001, 0x1d, x3, 0, x7)

inst_1:
// opcode: slli ; op1:x26; dest:x26; op1val:0x66666666;  immval:0xf
TEST_IMM_OP( slli,x0, x26, 0x33330000, 0x66666666, 0xf, x3, 4, x7)

inst_2:
// opcode: slli ; op1:x22; dest:x11; op1val:-0x10001;  immval:0x0
TEST_IMM_OP( slli,x0, x22, 0xfffeffff, -0x10001, 0x0, x3, 8, x7)

inst_3:
// opcode: slli ; op1:x15; dest:x6; op1val:0x4;  immval:0x0
TEST_IMM_OP( slli,x0, x15, 0x4, 0x4, 0x0, x3, 12, x7)

inst_4:
// opcode: slli ; op1:x9; dest:x16; op1val:-0x400001;  immval:0x1f
TEST_IMM_OP( slli,x0, x9, 0x80000000, -0x400001, 0x1f, x3, 16, x7)

inst_5:
// opcode: slli ; op1:x11; dest:x20; op1val:0x4;  immval:0x1f
TEST_IMM_OP( slli,x0, x11, 0x0, 0x4, 0x1f, x3, 20, x7)

inst_6:
// opcode: slli ; op1:x1; dest:x19; op1val:0x8;  immval:0x8
TEST_IMM_OP( slli,x0, x1, 0x800, 0x8, 0x8, x3, 24, x7)

inst_7:
// opcode: slli ; op1:x19; dest:x25; op1val:-0x80000000;  immval:0x10
TEST_IMM_OP( slli,x0, x19, 0x0, -0x80000000, 0x10, x3, 28, x7)

inst_8:
// opcode: slli ; op1:x8; dest:x12; op1val:0x0;  immval:0xc
TEST_IMM_OP( slli,x0, x8, 0x0, 0x0, 0xc, x3, 32, x7)

inst_9:
// opcode: slli ; op1:x27; dest:x30; op1val:0x7fffffff;  immval:0x8
TEST_IMM_OP( slli,x0, x27, 0xffffff00, 0x7fffffff, 0x8, x3, 36, x7)

inst_10:
// opcode: slli ; op1:x2; dest:x4; op1val:0x1;  immval:0x1
TEST_IMM_OP( slli,x0, x2, 0x2, 0x1, 0x1, x3, 40, x7)

inst_11:
// opcode: slli ; op1:x31; dest:x14; op1val:0x2;  immval:0x6
TEST_IMM_OP( slli,x0, x31, 0x80, 0x2, 0x6, x3, 44, x7)

inst_12:
// opcode: slli ; op1:x24; dest:x17; op1val:0x10;  immval:0xe
TEST_IMM_OP( slli,x0, x30, 0x40000, 0x10, 0xe, x3, 48, x7)

inst_13:
// opcode: slli ; op1:x4; dest:x10; op1val:0x20;  immval:0x3
TEST_IMM_OP( slli,x0, x29, 0x100, 0x20, 0x3, x3, 52, x7)

inst_14:
// opcode: slli ; op1:x18; dest:x2; op1val:0x40;  immval:0x15
TEST_IMM_OP( slli,x0, x28, 0x8000000, 0x40, 0x15, x3, 56, x7)

inst_15:
// opcode: slli ; op1:x5; dest:x23; op1val:0x80;  immval:0x15
TEST_IMM_OP( slli,x0, x5, 0x10000000, 0x80, 0x15, x3, 60, x7)

inst_16:
// opcode: slli ; op1:x13; dest:x8; op1val:0x100;  immval:0x1
TEST_IMM_OP( slli,x0, x13, 0x200, 0x100, 0x1, x3, 64, x7)

inst_17:
// opcode: slli ; op1:x20; dest:x0; op1val:0x200;  immval:0x0
TEST_IMM_OP( slli,x0, x20, 0, 0x200, 0x0, x3, 68, x7)

inst_18:
// opcode: slli ; op1:x16; dest:x9; op1val:0x400;  immval:0x2
TEST_IMM_OP( slli,x0, x16, 0x1000, 0x400, 0x2, x3, 72, x7)

inst_19:
// opcode: slli ; op1:x21; dest:x5; op1val:0x800;  immval:0x13
TEST_IMM_OP( slli,x0, x21, 0x40000000, 0x800, 0x13, x3, 76, x7)

inst_20:
// opcode: slli ; op1:x23; dest:x1; op1val:0x1000;  immval:0x7
TEST_IMM_OP( slli,x0, x23, 0x80000, 0x1000, 0x7, x3, 80, x2)


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
