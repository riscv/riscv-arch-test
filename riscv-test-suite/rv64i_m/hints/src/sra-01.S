
/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 5, 2025
Description: This test verifies the sra instruction as a hint whatever the value in the registers, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*64.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",sra)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: sra ; op1:x23; op2:x23; dest:x7; op1val:-0x800000001;  op2val:-0x800000001
TEST_RR_OP(sra,x0, x23, x23, -0x1, -0x800000001, -0x800000001, x3, 0, x10)

inst_1:
// opcode: sra ; op1:x15; op2:x3; dest:x3; op1val:0x100000000;  op2val:0x3
TEST_RR_OP(sra,x0, x15, x5, 0x20000000, 0x100000000, 0x3, x3, 8, x10)

inst_2:
// opcode: sra ; op1:x4; op2:x4; dest:x4; op1val:-0x100000001;  op2val:-0x100000001
TEST_RR_OP(sra,x0, x4, x4, -0x1, -0x100000001, -0x100000001, x3, 16, x10)

inst_3:
// opcode: sra ; op1:x27; op2:x24; dest:x30; op1val:0x3333333333333333;  op2val:0x0
TEST_RR_OP(sra,x0, x27, x24, 0x3333333333333333, 0x3333333333333333, 0x0, x3, 24, x10)

inst_4:
// opcode: sra ; op1:x20; op2:x18; dest:x20; op1val:0x1;  op2val:0x1
TEST_RR_OP(sra,x0, x20, x18, 0x0, 0x1, 0x1, x3, 32, x10)

inst_5:
// opcode: sra ; op1:x2; op2:x15; dest:x24; op1val:-0x8000000000000000;  op2val:0x2
TEST_RR_OP(sra,x0, x2, x15, -0x2000000000000000, -0x8000000000000000, 0x2, x3, 40, x10)

inst_6:
// opcode: sra ; op1:x13; op2:x8; dest:x26; op1val:0x0;  op2val:0xe
TEST_RR_OP(sra,x0, x13, x8, 0x0, 0x0, 0xe, x3, 48, x10)

inst_7:
// opcode: sra ; op1:x14; op2:x0; dest:x28; op1val:0x7fffffffffffffff;  op2val:0x0
TEST_RR_OP(sra,x0, x14, x0, 0x7fffffffffffffff, 0x7fffffffffffffff, 0x0, x3, 56, x10)

inst_8:
// opcode: sra ; op1:x25; op2:x22; dest:x6; op1val:0x2;  op2val:0xa
TEST_RR_OP(sra,x0, x25, x22, 0x0, 0x2, 0xa, x3, 64, x10)

inst_9:
// opcode: sra ; op1:x29; op2:x12; dest:x18; op1val:0x4;  op2val:0x7
TEST_RR_OP(sra,x0, x29, x12, 0x0, 0x4, 0x7, x3, 72, x10)

inst_10:
// opcode: sra ; op1:x3; op2:x28; dest:x11; op1val:0x8;  op2val:0xa
TEST_RR_OP(sra,x0, x7, x28, 0x0, 0x8, 0xa, x3, 80, x10)

inst_11:
// opcode: sra ; op1:x0; op2:x16; dest:x8; op1val:0x0;  op2val:0x6
TEST_RR_OP(sra,x0, x0, x16, 0x0, 0x0, 0x6, x3, 88, x10)

inst_12:
// opcode: sra ; op1:x24; op2:x5; dest:x12; op1val:0x20;  op2val:0x1
TEST_RR_OP(sra,x0, x24, x5, 0x10, 0x20, 0x1, x3, 96, x10)

inst_13:
// opcode: sra ; op1:x31; op2:x21; dest:x2; op1val:0x40;  op2val:0x8
TEST_RR_OP(sra,x0, x31, x21, 0x0, 0x40, 0x8, x3, 104, x10)

inst_14:
// opcode: sra ; op1:x8; op2:x1; dest:x21; op1val:0x80;  op2val:0xe
TEST_RR_OP(sra,x0, x8, x1, 0x0, 0x80, 0xe, x3, 112, x10)

inst_15:
// opcode: sra ; op1:x1; op2:x30; dest:x14; op1val:0x100;  op2val:0x3
TEST_RR_OP(sra,x0, x1, x30, 0x20, 0x100, 0x3, x3, 120, x4)


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
