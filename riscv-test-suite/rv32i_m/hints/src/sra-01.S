
/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 3, 2025
Description: This test verifies the sra instruction as a hint whatever the value in the register, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*32.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",sra)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: sra ; op1:x16; op2:x27; dest:x27; op1val:-0x80000000;  op2val:0x8
TEST_RR_OP(sra,x0, x16, x27, -0x800000, -0x80000000, 0x8, x3, 0, x9)

inst_1:
// opcode: sra ; op1:x12; op2:x12; dest:x16; op1val:0x2000000;  op2val:0x2000000
TEST_RR_OP(sra,x0, x12, x12, 0x2000000, 0x2000000, 0x2000000, x3, 4, x9)

inst_2:
// opcode: sra ; op1:x1; op2:x1; dest:x1; op1val:-0x801;  op2val:-0x801
TEST_RR_OP(sra,x0, x1, x1, -0x1, -0x801, -0x801, x3, 8, x9)

inst_3:
// opcode: sra ; op1:x13; op2:x19; dest:x13; op1val:0x33333333;  op2val:0x0
TEST_RR_OP(sra,x0, x13, x19, 0x33333333, 0x33333333, 0x0, x3, 12, x9)

inst_4:
// opcode: sra ; op1:x28; op2:x2; dest:x8; op1val:0x6;  op2val:0x6
TEST_RR_OP(sra,x0, x28, x2, 0x0, 0x6, 0x6, x3, 16, x9)

inst_5:
// opcode: sra ; op1:x26; op2:x31; dest:x19; op1val:0x0;  op2val:0x3
TEST_RR_OP(sra,x0, x26, x31, 0x0, 0x0, 0x3, x3, 20, x9)

inst_6:
// opcode: sra ; op1:x14; op2:x28; dest:x29; op1val:0x7fffffff;  op2val:0x12
TEST_RR_OP(sra,x0, x14, x28, 0x1fff, 0x7fffffff, 0x12, x3, 24, x9)

inst_7:
// opcode: sra ; op1:x10; op2:x26; dest:x12; op1val:0x1;  op2val:0x2
TEST_RR_OP(sra,x0, x10, x26, 0x0, 0x1, 0x2, x3, 28, x9)

inst_8:
// opcode: sra ; op1:x30; op2:x16; dest:x15; op1val:0x2;  op2val:0x4
TEST_RR_OP(sra,x0, x30, x16, 0x0, 0x2, 0x4, x3, 32, x9)

inst_9:
// opcode: sra ; op1:x24; op2:x0; dest:x6; op1val:0x4;  op2val:0x0
TEST_RR_OP(sra,x0, x24, x0, 0x4, 0x4, 0x0, x3, 36, x9)

inst_10:
// opcode: sra ; op1:x21; op2:x15; dest:x3; op1val:0x8;  op2val:0xa
TEST_RR_OP(sra,x0, x21, x15, 0x0, 0x8, 0xa, x3, 40, x9)

inst_11:
// opcode: sra ; op1:x15; op2:x30; dest:x10; op1val:0x10;  op2val:0x0
TEST_RR_OP(sra,x0, x15, x30, 0x10, 0x10, 0x0, x3, 44, x9)

inst_12:
// opcode: sra ; op1:x18; op2:x4; dest:x22; op1val:0x20;  op2val:0x3
TEST_RR_OP(sra,x0, x18, x4, 0x4, 0x3, 0x3, x3, 48, x9)

inst_13:
// opcode: sra ; op1:x19; op2:x17; dest:x11; op1val:0x40;  op2val:0x17
TEST_RR_OP(sra,x0, x19, x17, 0x0, 0x40, 0x17, x3, 52, x9)

inst_14:
// opcode: sra ; op1:x5; op2:x14; dest:x0; op1val:0x80;  op2val:0x8
TEST_RR_OP(sra,x0, x5, x14, 0, 0x80, 0x8, x3, 56, x9)

inst_15:
// opcode: sra ; op1:x6; op2:x24; dest:x5; op1val:0x100;  op2val:0x4
TEST_RR_OP(sra,x0, x6, x24, 0x10, 0x100, 0x4, x3, 60, x9)


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
