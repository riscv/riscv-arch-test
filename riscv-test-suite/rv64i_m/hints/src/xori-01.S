/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 5, 2025
Description: This test verifies the xori instruction as a hint whatever the value in the registers, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*64.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",xori)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: xori ; op1:x9; dest:x9; op1val:0x4;  immval:-0x800
TEST_IMM_OP( xori,x0, x9, 0xfffffffffffff804, 0x4, -0x800, x3, 0, x5)

inst_1:
// opcode: xori ; op1:x25; dest:x19; op1val:-0x8000001;  immval:0x0
TEST_IMM_OP( xori,x0, x25, 0xfffffffff7ffffff, -0x8000001, 0x0, x3, 8, x5)

inst_2:
// opcode: xori ; op1:x13; dest:x12; op1val:0x3;  immval:0x7ff
TEST_IMM_OP( xori,x0, x13, 0x7fc, 0x3, 0x7ff, x3, 16, x5)

inst_3:
// opcode: xori ; op1:x16; dest:x13; op1val:-0x5555555555555555;  immval:0x1
TEST_IMM_OP( xori,x0, x16, 0xaaaaaaaaaaaaaaaa, -0x5555555555555555, 0x1, x3, 24, x5)

inst_4:
// opcode: xori ; op1:x4; dest:x14; op1val:-0x8000000000000000;  immval:-0x9
TEST_IMM_OP( xori,x0, x4, 0x7ffffffffffffff7, -0x8000000000000000, -0x9, x3, 32, x5)

inst_5:
// opcode: xori ; op1:x29; dest:x23; op1val:0x0;  immval:0x0
TEST_IMM_OP( xori,x0, x29, 0x0, 0x0, 0x0, x3, 40, x5)

inst_6:
// opcode: xori ; op1:x28; dest:x21; op1val:0x7fffffffffffffff;  immval:0x2
TEST_IMM_OP( xori,x0, x28, 0x7ffffffffffffffd, 0x7fffffffffffffff, 0x3, x3, 48, x5)

inst_7:
// opcode: xori ; op1:x22; dest:x4; op1val:0x1;  immval:0x666
TEST_IMM_OP( xori,x0, x22, 0x667, 0x1, 0x666, x3, 56, x5)

inst_8:
// opcode: xori ; op1:x11; dest:x31; op1val:0x8000;  immval:0x4
TEST_IMM_OP( xori,x0, x11, 0x8004, 0x8000, 0x4, x3, 64, x5)

inst_9:
// opcode: xori ; op1:x17; dest:x6; op1val:-0x101;  immval:0x8
TEST_IMM_OP( xori,x0, x17, 0xfffffffffffffef7, -0x101, 0x8, x3, 72, x5)

inst_10:
// opcode: xori ; op1:x12; dest:x15; op1val:-0xa;  immval:0x10
TEST_IMM_OP( xori,x0, x12, 0xffffffffffffffe6, -0xa, 0x10, x3, 80, x5)

inst_11:
// opcode: xori ; op1:x27; dest:x22; op1val:-0x40000000001;  immval:0x20
TEST_IMM_OP( xori,x0, x27, 0xfffffbffffffffdf, -0x40000000001, 0x20, x3, 88, x5)

inst_12:
// opcode: xori ; op1:x18; dest:x1; op1val:0x40000000;  immval:0x40
TEST_IMM_OP( xori,x0, x18, 0x40000040, 0x40000000, 0x40, x3, 96, x5)

inst_13:
// opcode: xori ; op1:x7; dest:x26; op1val:-0x801;  immval:0x80
TEST_IMM_OP( xori,x0, x7, 0xfffffffffffff77f, -0x801, 0x80, x3, 104, x5)

inst_14:
// opcode: xori ; op1:x30; dest:x20; op1val:-0x400000000001;  immval:0x100
TEST_IMM_OP( xori,x0, x30, 0xffffbffffffffeff, -0x400000000001, 0x100, x3, 112, x5)

inst_15:
// opcode: xori ; op1:x6; dest:x11; op1val:0x800000000;  immval:0x200
TEST_IMM_OP( xori,x0, x6, 0x800000200, 0x800000000, 0x200, x3, 120, x5)


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
