
/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 4, 2025
Description: This test verifies the andi instruction as a hint whatever the value in the registers, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*64.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",andi)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: andi ; op1:x18; dest:x18; op1val:-0x101;  immval:-0x800
TEST_IMM_OP( andi,x0, x18, 0xfffffffffffff800, -0x101, -0x800, x3, 0, x11)

inst_1:
// opcode: andi ; op1:x8; dest:x17; op1val:-0x10001;  immval:0x0
TEST_IMM_OP( andi,x0, x8, 0x0, -0x10001, 0x0, x3, 8, x11)

inst_2:
// opcode: andi ; op1:x19; dest:x10; op1val:0x400;  immval:0x7ff
TEST_IMM_OP( andi,x0, x19, 0x400, 0x400, 0x7ff, x3, 16, x11)

inst_3:
// opcode: andi ; op1:x20; dest:x1; op1val:0x1000;  immval:0x1
TEST_IMM_OP( andi,x0, x20, 0x0, 0x1000, 0x1, x3, 24, x11)

inst_4:
// opcode: andi ; op1:x22; dest:x31; op1val:-0x8000000000000000;  immval:0x354
TEST_IMM_OP( andi,x0, x22, 0x0, -0x8000000000000000, 0x354, x3, 32, x11)

inst_5:
// opcode: andi ; op1:x3; dest:x24; op1val:0x0;  immval:0x2d
TEST_IMM_OP( andi,x0, x5, 0x0, 0x0, 0x2d, x3, 40, x11)

inst_6:
// opcode: andi ; op1:x6; dest:x2; op1val:0x7fffffffffffffff;  immval:0x200
TEST_IMM_OP( andi,x0, x6, 0x200, 0x7fffffffffffffff, 0x200, x3, 48, x11)

inst_7:
// opcode: andi ; op1:x1; dest:x7; op1val:0x1;  immval:-0x21
TEST_IMM_OP( andi,x0, x1, 0x1, 0x1, -0x21, x3, 56, x11)

inst_8:
// opcode: andi ; op1:x31; dest:x29; op1val:0x0;  immval:0x0
TEST_IMM_OP( andi,x0, x31, 0x0, 0x0, 0x0, x3, 64, x11)

inst_9:
// opcode: andi ; op1:x23; dest:x26; op1val:-0x11;  immval:0x2
TEST_IMM_OP( andi,x0, x23, 0x2, -0x11, 0x2, x3, 72, x11)

inst_10:
// opcode: andi ; op1:x9; dest:x27; op1val:0x1000;  immval:0x4
TEST_IMM_OP( andi,x0, x9, 0x0, 0x1000, 0x4, x3, 80, x11)

inst_11:
// opcode: andi ; op1:x2; dest:x20; op1val:-0x400000000000001;  immval:0x8
TEST_IMM_OP( andi,x0, x2, 0x8, -0x400000000000001, 0x8, x3, 88, x11)

inst_12:
// opcode: andi ; op1:x13; dest:x21; op1val:0x20000000000;  immval:0x10
TEST_IMM_OP( andi,x0, x13, 0x0, 0x20000000000, 0x10, x3, 96, x11)

inst_13:
// opcode: andi ; op1:x15; dest:x28; op1val:0x10;  immval:0x20
TEST_IMM_OP( andi,x0, x15, 0x0, 0x10, 0x20, x3, 104, x11)

inst_14:
// opcode: andi ; op1:x21; dest:x30; op1val:0x7fffffffffffffff;  immval:0x40
TEST_IMM_OP( andi,x0, x21, 0x40, 0x7fffffffffffffff, 0x40, x3, 112, x11)

inst_15:
// opcode: andi ; op1:x30; dest:x13; op1val:-0x400001;  immval:0x80
TEST_IMM_OP( andi,x0, x30, 0x80, -0x400001, 0x80, x3, 120, x11)


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
