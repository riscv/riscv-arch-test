
/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 5, 2025
Description: This test verifies the sraiw instruction as a hint whatever the value in the register or imm field, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*64.*);check ISA:=regex(.*RV64.*I.*Zicsr);def TEST_CASE_1=True;",sraiw)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: sraiw ; op1:x5; dest:x5; op1val:-0x201;  immval:0x17
TEST_IMM_OP( sraiw,x0, x5, -0x1, -0x201, 0x17, x3, 0, x8)

inst_1:
// opcode: sraiw ; op1:x12; dest:x24; op1val:0x100000000;  immval:0x11
TEST_IMM_OP( sraiw,x0, x12, 0x0, 0x100000000, 0x11, x3, 8, x8)

inst_2:
// opcode: sraiw ; op1:x20; dest:x18; op1val:-0x8000000001;  immval:0x0
TEST_IMM_OP( sraiw,x0, x20, -0x1, -0x8000000001, 0x0, x3, 16, x8)

inst_3:
// opcode: sraiw ; op1:x15; dest:x6; op1val:0x100000000000;  immval:0x0
TEST_IMM_OP( sraiw,x0, x15, 0x0, 0x100000000000, 0x0, x3, 24, x8)

inst_4:
// opcode: sraiw ; op1:x29; dest:x13; op1val:-0xa;  immval:0x1f
TEST_IMM_OP( sraiw,x0, x29, -0x1, -0xa, 0x1f, x3, 32, x8)

inst_5:
// opcode: sraiw ; op1:x24; dest:x30; op1val:0x100000000000;  immval:0x1f
TEST_IMM_OP( sraiw,x0, x24, 0x0, 0x100000000000, 0x1f, x3, 40, x8)

inst_6:
// opcode: sraiw ; op1:x28; dest:x16; op1val:0x3;  immval:0x3
TEST_IMM_OP( sraiw,x0, x28, 0x0, 0x3, 0x3, x3, 48, x8)

inst_7:
// opcode: sraiw ; op1:x16; dest:x9; op1val:-0x8000000000000000;  immval:0x11
TEST_IMM_OP( sraiw,x0, x16, 0x0, -0x8000000000000000, 0x11, x3, 56, x8)

inst_8:
// opcode: sraiw ; op1:x30; dest:x10; op1val:0x0;  immval:0xe
TEST_IMM_OP( sraiw,x0, x30, 0x0, 0x0, 0xe, x3, 64, x8)

inst_9:
// opcode: sraiw ; op1:x0; dest:x20; op1val:0x0;  immval:0x1b
TEST_IMM_OP( sraiw,x0, x0, 0x0, 0x0, 0x1b, x3, 72, x8)

inst_10:
// opcode: sraiw ; op1:x27; dest:x29; op1val:0x1;  immval:0x8
TEST_IMM_OP( sraiw,x0, x27, 0x0, 0x1, 0x8, x3, 80, x8)

inst_11:
// opcode: sraiw ; op1:x13; dest:x26; op1val:0x2;  immval:0xf
TEST_IMM_OP( sraiw,x0, x13, 0x0, 0x3, 0xf, x3, 88, x8)

inst_12:
// opcode: sraiw ; op1:x7; dest:x17; op1val:0x4;  immval:0x1e
TEST_IMM_OP( sraiw,x0, x7, 0x0, 0x4, 0x1e, x3, 96, x8)

inst_13:
// opcode: sraiw ; op1:x14; dest:x7; op1val:0x8;  immval:0x9
TEST_IMM_OP( sraiw,x0, x14, 0x0, 0x8, 0x9, x3, 104, x8)

inst_14:
// opcode: sraiw ; op1:x23; dest:x1; op1val:0x10;  immval:0x13
TEST_IMM_OP( sraiw,x0, x23, 0x0, 0x10, 0x13, x3, 112, x8)

inst_15:
// opcode: sraiw ; op1:x3; dest:x11; op1val:0x20;  immval:0x1
TEST_IMM_OP( sraiw,x0, x7, 0x10, 0x20, 0x1, x3, 120, x8)


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
