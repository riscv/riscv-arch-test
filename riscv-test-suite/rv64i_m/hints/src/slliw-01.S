/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 4, 2025
Description: This test verifies the slliw instruction as a hint whatever the value in the register or imm field, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*64.*);check ISA:=regex(.*RV64.*I.*Zicsr);def TEST_CASE_1=True;",slliw)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: slliw ; op1:x10; dest:x10; op1val:-0x40001;  immval:0x6
TEST_IMM_OP( slliw,x0, x10, -0x1000040, -0x40001, 0x6, x3, 0, x4)

inst_1:
// opcode: slliw ; op1:x28; dest:x27; op1val:0x6;  immval:0x17
TEST_IMM_OP( slliw,x0, x28, 0x3000000, 0x6, 0x17, x3, 8, x4)

inst_2:
// opcode: slliw ; op1:x14; dest:x12; op1val:-0x100000001;  immval:0x0
TEST_IMM_OP( slliw,x0, x14, -0x3, -0x100000001, 0x0, x3, 16, x4)

inst_3:
// opcode: slliw ; op1:x11; dest:x30; op1val:0x80000000000000;  immval:0x0
TEST_IMM_OP( slliw,x0, x11, 0x0, 0x80000000000000, 0x0, x3, 24, x4)

inst_4:
// opcode: slliw ; op1:x16; dest:x2; op1val:-0x10000000000001;  immval:0x1f
TEST_IMM_OP( slliw,x0, x16, -0x80000000, -0x10000000000001, 0x1f, x3, 32, x4)

inst_5:
// opcode: slliw ; op1:x31; dest:x20; op1val:0x400000000000;  immval:0x1f
TEST_IMM_OP( slliw,x0, x31, 0x0, 0x400000000000, 0x1f, x3, 40, x4)

inst_6:
// opcode: slliw ; op1:x30; dest:x15; op1val:0x5;  immval:0x5
TEST_IMM_OP( slliw,x0, x30, 0xa0, 0x5, 0x5, x3, 48, x4)

inst_7:
// opcode: slliw ; op1:x3; dest:x7; op1val:-0x8000000000000000;  immval:0x1d
TEST_IMM_OP( slliw,x0, x5, 0x0, -0x8000000000000000, 0x1d, x3, 56, x4)

inst_8:
// opcode: slliw ; op1:x25; dest:x16; op1val:0x0;  immval:0x11
TEST_IMM_OP( slliw,x0, x25, 0x0, 0x0, 0x11, x3, 64, x4)

inst_9:
// opcode: slliw ; op1:x13; dest:x23; op1val:0x7fffffffffffffff;  immval:0x4
TEST_IMM_OP( slliw,x0, x13, -0x10, 0x7fffffffffffffff, 0x4, x3, 72, x4)

inst_10:
// opcode: slliw ; op1:x12; dest:x19; op1val:0x1;  immval:0x17
TEST_IMM_OP( slliw,x0, x12, 0x800000, 0x3, 0x17, x3, 80, x4)

inst_11:
// opcode: slliw ; op1:x7; dest:x29; op1val:0x2;  immval:0x1b
TEST_IMM_OP( slliw,x0, x7, 0x10000000, 0x2, 0x1b, x3, 88, x4)

inst_12:
// opcode: slliw ; op1:x0; dest:x14; op1val:0x0;  immval:0x0
TEST_IMM_OP( slliw,x0, x0, 0x0, 0x0, 0x0, x3, 96, x4)

inst_13:
// opcode: slliw ; op1:x17; dest:x31; op1val:0x8;  immval:0x7
TEST_IMM_OP( slliw,x0, x17, 0x400, 0x8, 0x7, x3, 104, x4)

inst_14:
// opcode: slliw ; op1:x20; dest:x9; op1val:0x10;  immval:0x7
TEST_IMM_OP( slliw,x0, x20, 0x800, 0x10, 0x7, x3, 112, x4)

inst_15:
// opcode: slliw ; op1:x29; dest:x26; op1val:0x20;  immval:0x15
TEST_IMM_OP( slliw,x0, x29, 0x4000000, 0x20, 0x15, x3, 120, x4)


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
