
/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 4, 2025
Description: This test verifies the addiw instruction as a hint whatever the value in the register or imm field, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*64.*);check ISA:=regex(.*RV64.*I.*Zicsr);def TEST_CASE_1=True;",addiw)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: addiw ; op1:x17; dest:x17; op1val:-0x5555555555555556;  immval:-0x800
TEST_IMM_OP( addiw,x0, x17, -0x55555d56, -0x5555555555555556, -0x800, x3, 0, x5)

inst_1:
// opcode: addiw ; op1:x2; dest:x20; op1val:-0x20000001;  immval:0x0
TEST_IMM_OP( addiw,x0, x2, -0x20000001, -0x20000001, 0x0, x3, 8, x5)

inst_2:
// opcode: addiw ; op1:x20; dest:x16; op1val:-0x4000000000000000;  immval:0x7ff
TEST_IMM_OP( addiw,x0, x20, 0x7ff, -0x4000000000000000, 0x7ff, x3, 16, x5)

inst_3:
// opcode: addiw ; op1:x26; dest:x29; op1val:0x5555555555555556;  immval:0x1
TEST_IMM_OP( addiw,x0, x26, 0x55555557, 0x5555555555555556, 0x1, x3, 24, x5)

inst_4:
// opcode: addiw ; op1:x8; dest:x27; op1val:-0x8000000000000000;  immval:0x333
TEST_IMM_OP( addiw,x0, x8, 0x333, -0x8000000000000000, 0x333, x3, 32, x5)

inst_5:
// opcode: addiw ; op1:x18; dest:x25; op1val:0x0;  immval:-0x556
TEST_IMM_OP( addiw,x0, x18, -0x556, 0x0, -0x556, x3, 40, x5)

inst_6:
// opcode: addiw ; op1:x7; dest:x6; op1val:0x7fffffffffffffff;  immval:0x7
TEST_IMM_OP( addiw,x0, x7, 0x6, 0x7fffffffffffffff, 0x7, x3, 48, x5)

inst_7:
// opcode: addiw ; op1:x10; dest:x0; op1val:0x1;  immval:0x6
TEST_IMM_OP( addiw,x0, x10, 0, 0x1, 0x6, x3, 56, x5)

inst_8:
// opcode: addiw ; op1:x27; dest:x9; op1val:0x8;  immval:0x8
TEST_IMM_OP( addiw,x0, x27, 0x10, 0x8, 0x8, x3, 64, x5)

inst_9:
// opcode: addiw ; op1:x6; dest:x31; op1val:0x7;  immval:-0x400
TEST_IMM_OP( addiw,x0, x6, -0x3f9, 0x7, -0x400, x3, 72, x5)

inst_10:
// opcode: addiw ; op1:x0; dest:x22; op1val:0x0;  immval:0x2
TEST_IMM_OP( addiw,x0, x0, 0x2, 0x0, 0x2, x3, 80, x5)

inst_11:
// opcode: addiw ; op1:x16; dest:x7; op1val:-0x2;  immval:0x4
TEST_IMM_OP( addiw,x0, x16, 0x2, -0x2, 0x4, x3, 88, x5)

inst_12:
// opcode: addiw ; op1:x19; dest:x21; op1val:0x4;  immval:0x10
TEST_IMM_OP( addiw,x0, x19, 0x14, 0x4, 0x10, x3, 96, x5)

inst_13:
// opcode: addiw ; op1:x1; dest:x4; op1val:-0x2000000000001;  immval:0x20
TEST_IMM_OP( addiw,x0, x1, 0x1f, -0x2000000000001, 0x20, x3, 104, x5)

inst_14:
// opcode: addiw ; op1:x13; dest:x23; op1val:0x4000;  immval:0x40
TEST_IMM_OP( addiw,x0, x13, 0x4040, 0x4000, 0x40, x3, 112, x5)


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
