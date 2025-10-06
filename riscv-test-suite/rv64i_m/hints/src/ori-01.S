/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 4, 2025
Description: This test verifies the ori instruction as a hint whatever the value in the register or imm field, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*64.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",ori)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: ori ; op1:x6; dest:x6; op1val:0x2000;  immval:-0x800
TEST_IMM_OP( ori,x0, x6, 0xfffffffffffff800, 0x2000, -0x800, x3, 0, x9)

inst_1:
// opcode: ori ; op1:x28; dest:x2; op1val:0x4;  immval:0x0
TEST_IMM_OP( ori,x0, x28, 0x4, 0x4, 0x0, x3, 8, x9)

inst_2:
// opcode: ori ; op1:x25; dest:x19; op1val:-0x2;  immval:0x7ff
TEST_IMM_OP( ori,x0, x25, 0xffffffffffffffff, -0x2, 0x7ff, x3, 16, x9)

inst_3:
// opcode: ori ; op1:x0; dest:x1; op1val:0x0;  immval:0x1
TEST_IMM_OP( ori,x0, x0, 0x1, 0x0, 0x1, x3, 24, x9)

inst_4:
// opcode: ori ; op1:x4; dest:x7; op1val:-0x8000000000000000;  immval:0x666
TEST_IMM_OP( ori,x0, x4, 0x8000000000000666, -0x8000000000000000, 0x666, x3, 32, x9)

inst_5:
// opcode: ori ; op1:x29; dest:x8; op1val:0x0;  immval:-0x201
TEST_IMM_OP( ori,x0, x29, 0xfffffffffffffdff, 0x0, -0x201, x3, 40, x9)

inst_6:
// opcode: ori ; op1:x22; dest:x17; op1val:0x7fffffffffffffff;  immval:-0x201
TEST_IMM_OP( ori,x0, x22, 0xffffffffffffffff, 0x7fffffffffffffff, -0x201, x3, 48, x9)

inst_7:
// opcode: ori ; op1:x17; dest:x10; op1val:0x1;  immval:-0x6
TEST_IMM_OP( ori,x0, x17, 0xfffffffffffffffb, 0x1, -0x6, x3, 56, x9)

inst_8:
// opcode: ori ; op1:x5; dest:x30; op1val:0x5;  immval:0x5
TEST_IMM_OP( ori,x0, x5, 0x5, 0x5, 0x5, x3, 64, x9)

inst_9:
// opcode: ori ; op1:x12; dest:x0; op1val:-0x200001;  immval:-0x9
TEST_IMM_OP( ori,x0, x12, 0, -0x200001, -0x9, x3, 72, x9)

inst_10:
// opcode: ori ; op1:x16; dest:x3; op1val:0x20000000000000;  immval:0x2
TEST_IMM_OP( ori,x0, x16, 0x20000000000002, 0x20000000000000, 0x2, x3, 80, x9)

inst_11:
// opcode: ori ; op1:x31; dest:x20; op1val:-0x41;  immval:0x4
TEST_IMM_OP( ori,x0, x31, 0xffffffffffffffbf, -0x41, 0x4, x3, 88, x9)

inst_12:
// opcode: ori ; op1:x3; dest:x12; op1val:0x4000;  immval:0x8
TEST_IMM_OP( ori,x0, x5, 0x4008, 0x4000, 0x8, x3, 96, x9)

inst_13:
// opcode: ori ; op1:x18; dest:x21; op1val:-0x1000000000001;  immval:0x10
TEST_IMM_OP( ori,x0, x18, 0xfffeffffffffffff, -0x1000000000001, 0x10, x3, 104, x9)

inst_14:
// opcode: ori ; op1:x15; dest:x24; op1val:0x10000000000000;  immval:0x20
TEST_IMM_OP( ori,x0, x15, 0x10000000000020, 0x10000000000000, 0x20, x3, 112, x9)

inst_15:
// opcode: ori ; op1:x10; dest:x23; op1val:-0x10000001;  immval:0x40
TEST_IMM_OP( ori,x0, x10, 0xffffffffefffffff, -0x10000001, 0x40, x3, 120, x9)


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
