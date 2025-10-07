/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 3, 2025
Description: This test verifies the slti instruction as a hint whatever the value in the register in the imm field, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*32.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",slti)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: slti ; op1:x25; dest:x12; op1val:-0x81;  immval:-0x800
TEST_IMM_OP( slti,x0, x25, 0x0, -0x81, -0x800, x3, 0, x19)

inst_1:
// opcode: slti ; op1:x5; dest:x5; op1val:-0x1001;  immval:0x0
TEST_IMM_OP( slti,x0, x5, 0x1, -0x1001, 0x0, x3, 4, x19)

inst_2:
// opcode: slti ; op1:x4; dest:x28; op1val:-0x40000000;  immval:0x7ff
TEST_IMM_OP( slti,x0, x4, 0x1, -0x40000000, 0x7ff, x3, 8, x19)

inst_3:
// opcode: slti ; op1:x31; dest:x15; op1val:-0x11;  immval:0x1
TEST_IMM_OP( slti,x0, x31, 0x1, -0x11, 0x1, x3, 12, x19)

inst_4:
// opcode: slti ; op1:x1; dest:x13; op1val:-0x80000000;  immval:0x3
TEST_IMM_OP( slti,x0, x1, 0x1, -0x80000000, 0x3, x3, 16, x19)

inst_5:
// opcode: slti ; op1:x15; dest:x1; op1val:0x0;  immval:0x2
TEST_IMM_OP( slti,x0, x15, 0x1, 0x0, 0x3, x3, 20, x19)

inst_6:
// opcode: slti ; op1:x16; dest:x9; op1val:0x7fffffff;  immval:-0x8
TEST_IMM_OP( slti,x0, x16, 0x0, 0x7fffffff, -0x8, x3, 24, x19)

inst_7:
// opcode: slti ; op1:x11; dest:x31; op1val:0x1;  immval:-0x400
TEST_IMM_OP( slti,x0, x11, 0x0, 0x1, -0x400, x3, 28, x19)

inst_8:
// opcode: slti ; op1:x14; dest:x27; op1val:0x10;  immval:0x10
TEST_IMM_OP( slti,x0, x14, 0x0, 0x10, 0x10, x3, 32, x19)

inst_9:
// opcode: slti ; op1:x12; dest:x26; op1val:0x33333334;  immval:0x4
TEST_IMM_OP( slti,x0, x12, 0x0, 0x33333334, 0x4, x3, 36, x19)

inst_10:
// opcode: slti ; op1:x17; dest:x4; op1val:0x3fffffff;  immval:0x8
TEST_IMM_OP( slti,x0, x17, 0x0, 0x3fffffff, 0x8, x3, 40, x19)

inst_11:
// opcode: slti ; op1:x18; dest:x10; op1val:-0x2001;  immval:0x20
TEST_IMM_OP( slti,x0, x18, 0x1, -0x2001, 0x20, x3, 44, x19)

inst_12:
// opcode: slti ; op1:x27; dest:x21; op1val:0x3;  immval:0x40
TEST_IMM_OP( slti,x0, x27, 0x1, 0x3, 0x40, x3, 48, x19)

inst_13:
// opcode: slti ; op1:x3; dest:x8; op1val:0x55555554;  immval:0x80
TEST_IMM_OP( slti,x0, x5, 0x0, 0x55555554, 0x80, x3, 52, x19)

inst_14:
// opcode: slti ; op1:x7; dest:x0; op1val:0x55555554;  immval:0x100
TEST_IMM_OP( slti,x0, x7, 0, 0x55555554, 0x100, x3, 56, x19)

inst_15:
// opcode: slti ; op1:x22; dest:x24; op1val:-0x55555556;  immval:0x200
TEST_IMM_OP( slti,x0, x22, 0x1, -0x55555556, 0x200, x3, 60, x19)

inst_16:
// opcode: slti ; op1:x24; dest:x18; op1val:0x4000;  immval:0x400
TEST_IMM_OP( slti,x0, x24, 0x0, 0x4000, 0x400, x3, 64, x19)

inst_17:
// opcode: slti ; op1:x6; dest:x25; op1val:-0x401;  immval:-0x2
TEST_IMM_OP( slti,x0, x6, 0x1, -0x401, -0x3, x3, 68, x19)

inst_18:
// opcode: slti ; op1:x21; dest:x23; op1val:0x66666667;  immval:-0x3
TEST_IMM_OP( slti,x0, x21, 0x0, 0x66666667, -0x3, x3, 72, x19)

inst_19:
// opcode: slti ; op1:x0; dest:x7; op1val:0x0;  immval:-0x5
TEST_IMM_OP( slti,x0, x0, 0x0, 0x0, -0x5, x3, 76, x19)

inst_20:
// opcode: slti ; op1:x10; dest:x20; op1val:-0xb504;  immval:-0x9
TEST_IMM_OP( slti,x0, x10, 0x1, -0xb504, -0x9, x3, 80, x19)


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
