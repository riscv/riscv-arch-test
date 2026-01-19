/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 3, 2025
Description: This test verifies the ori instruction as a hint whatever the value in the register, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*32.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",ori)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: ori ; op1:x5; dest:x22; op1val:-0x201;  immval:-0x800
TEST_IMM_OP( ori,x0, x5, 0xfffffdff, -0x201, -0x800, x3, 0, x9)

inst_1:
// opcode: ori ; op1:x27; dest:x27; op1val:0x0;  immval:0x0
TEST_IMM_OP( ori,x0, x27, 0x0, 0x0, 0x0, x3, 4, x9)

inst_2:
// opcode: ori ; op1:x17; dest:x8; op1val:0x33333334;  immval:0x7ff
TEST_IMM_OP( ori,x0, x17, 0x333337ff, 0x33333334, 0x7ff, x3, 8, x9)

inst_3:
// opcode: ori ; op1:x20; dest:x1; op1val:-0xb504;  immval:0x1
TEST_IMM_OP( ori,x0, x20, 0xffff4afd, -0xb504, 0x1, x3, 12, x9)

inst_4:
// opcode: ori ; op1:x12; dest:x19; op1val:-0x80000000;  immval:0x2d
TEST_IMM_OP( ori,x0, x12, 0x8000002d, -0x80000000, 0x2d, x3, 16, x9)

inst_5:
// opcode: ori ; op1:x8; dest:x3; op1val:0x7fffffff;  immval:0x555
TEST_IMM_OP( ori,x0, x8, 0x7fffffff, 0x7fffffff, 0x555, x3, 20, x9)

inst_6:
// opcode: ori ; op1:x28; dest:x26; op1val:0x1;  immval:0x667
TEST_IMM_OP( ori,x0, x28, 0x667, 0x1, 0x667, x3, 24, x9)

inst_7:
// opcode: ori ; op1:x16; dest:x23; op1val:0x7;  immval:-0x7
TEST_IMM_OP( ori,x0, x16, 0xffffffff, 0x7, -0x7, x3, 28, x9)

inst_8:
// opcode: ori ; op1:x25; dest:x31; op1val:0x40000;  immval:0x2
TEST_IMM_OP( ori,x0, x25, 0x40002, 0x40000, 0x3, x3, 32, x9)

inst_9:
// opcode: ori ; op1:x23; dest:x11; op1val:0x20000000;  immval:0x4
TEST_IMM_OP( ori,x0, x23, 0x20000004, 0x20000000, 0x4, x3, 36, x9)

inst_10:
// opcode: ori ; op1:x14; dest:x17; op1val:-0x201;  immval:0x8
TEST_IMM_OP( ori,x0, x14, 0xfffffdff, -0x201, 0x8, x3, 40, x9)

inst_11:
// opcode: ori ; op1:x31; dest:x7; op1val:0x2;  immval:0x10
TEST_IMM_OP( ori,x0, x31, 0x12, 0x3, 0x10, x3, 44, x9)

inst_12:
// opcode: ori ; op1:x21; dest:x4; op1val:0x8000;  immval:0x20
TEST_IMM_OP( ori,x0, x21, 0x8020, 0x8000, 0x20, x3, 48, x9)

inst_13:
// opcode: ori ; op1:x15; dest:x5; op1val:0x800;  immval:0x40
TEST_IMM_OP( ori,x0, x15, 0x840, 0x800, 0x40, x3, 52, x9)

inst_14:
// opcode: ori ; op1:x30; dest:x25; op1val:-0x40001;  immval:0x80
TEST_IMM_OP( ori,x0, x30, 0xfffbffff, -0x40001, 0x80, x3, 56, x9)

inst_15:
// opcode: ori ; op1:x11; dest:x30; op1val:-0x5;  immval:0x100
TEST_IMM_OP( ori,x0, x11, 0xfffffffb, -0x5, 0x100, x3, 60, x9)

inst_16:
// opcode: ori ; op1:x4; dest:x10; op1val:-0x80001;  immval:0x200
TEST_IMM_OP( ori,x0, x4, 0xfff7ffff, -0x80001, 0x200, x3, 64, x9)

inst_17:
// opcode: ori ; op1:x13; dest:x0; op1val:-0x40000001;  immval:0x400
TEST_IMM_OP( ori,x0, x13, 0, -0x40000001, 0x400, x3, 68, x9)

inst_18:
// opcode: ori ; op1:x26; dest:x6; op1val:-0x21;  immval:-0x2
TEST_IMM_OP( ori,x0, x26, 0xffffffff, -0x21, -0x3, x3, 72, x9)


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
