/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 5, 2025
Description: This test verifies the srliw instruction as a hint whatever the value in the registeror imm field, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*64.*);check ISA:=regex(.*RV64.*I.*Zicsr);def TEST_CASE_1=True;",srliw)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: srliw ; op1:x21; dest:x21; op1val:-0x1000000001;  immval:0xf
TEST_IMM_OP( srliw,x0, x21, 0x1ffff, -0x1000000001, 0xf, x3, 0, x14)

inst_1:
// opcode: srliw ; op1:x22; dest:x3; op1val:0x6666666666666666;  immval:0x8
TEST_IMM_OP( srliw,x0, x22, 0x666666, 0x6666666666666666, 0x8, x3, 8, x14)

inst_2:
// opcode: srliw ; op1:x11; dest:x4; op1val:-0x1000001;  immval:0x0
TEST_IMM_OP( srliw,x0, x11, -0x1000001, -0x1000001, 0x0, x3, 16, x14)

inst_3:
// opcode: srliw ; op1:x7; dest:x23; op1val:0x6666666666666666;  immval:0x0
TEST_IMM_OP( srliw,x0, x7, 0x66666666, 0x6666666666666666, 0x0, x3, 24, x14)

inst_4:
// opcode: srliw ; op1:x31; dest:x17; op1val:-0x80000000000001;  immval:0x1f
TEST_IMM_OP( srliw,x0, x31, 0x1, -0x80000000000001, 0x1f, x3, 32, x14)

inst_5:
// opcode: srliw ; op1:x10; dest:x28; op1val:0x10000000000;  immval:0x1f
TEST_IMM_OP( srliw,x0, x10, 0x0, 0x10000000000, 0x1f, x3, 40, x14)

inst_6:
// opcode: srliw ; op1:x24; dest:x9; op1val:0x9;  immval:0x9
TEST_IMM_OP( srliw,x0, x24, 0x0, 0x9, 0x9, x3, 48, x14)

inst_7:
// opcode: srliw ; op1:x20; dest:x0; op1val:-0x8000000000000000;  immval:0x1b
TEST_IMM_OP( srliw,x0, x20, 0, -0x8000000000000000, 0x1b, x3, 56, x14)

inst_8:
// opcode: srliw ; op1:x15; dest:x8; op1val:0x0;  immval:0x1
TEST_IMM_OP( srliw,x0, x15, 0x0, 0x0, 0x1, x3, 64, x14)

inst_9:
// opcode: srliw ; op1:x28; dest:x20; op1val:0x7fffffffffffffff;  immval:0xb
TEST_IMM_OP( srliw,x0, x28, 0x1fffff, 0x7fffffffffffffff, 0xb, x3, 72, x14)

inst_10:
// opcode: srliw ; op1:x23; dest:x19; op1val:0x1;  immval:0xa
TEST_IMM_OP( srliw,x0, x23, 0x0, 0x1, 0xa, x3, 80, x14)

inst_11:
// opcode: srliw ; op1:x13; dest:x15; op1val:0x2;  immval:0x11
TEST_IMM_OP( srliw,x0, x13, 0x0, 0x2, 0x11, x3, 88, x14)

inst_12:
// opcode: srliw ; op1:x8; dest:x16; op1val:0x4;  immval:0x12
TEST_IMM_OP( srliw,x0, x8, 0x0, 0x4, 0x12, x3, 96, x14)

inst_13:
// opcode: srliw ; op1:x4; dest:x26; op1val:0x8;  immval:0x12
TEST_IMM_OP( srliw,x0, x4, 0x0, 0x8, 0x12, x3, 104, x14)

inst_14:
// opcode: srliw ; op1:x2; dest:x29; op1val:0x10;  immval:0x11
TEST_IMM_OP( srliw,x0, x2, 0x0, 0x10, 0x11, x3, 112, x14)

inst_15:
// opcode: srliw ; op1:x5; dest:x27; op1val:0x20;  immval:0x6
TEST_IMM_OP( srliw,x0, x5, 0x0, 0x20, 0x6, x3, 120, x14)


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
