/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 3, 2025
Description: This test verifies the srl instruction as a hint whatever the value in the register, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*32.*);check ISA:=regex(.*I.*);def TEST_CASE_1=True;",srl)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: srl ; op1:x26; op2:x11; dest:x11; op1val:-0x400001;  op2val:0xf
TEST_RR_OP(srl,x0, x26, x11, 0x1ff7f, -0x400001, 0xf, x3, 0, x24)

inst_1:
// opcode: srl ; op1:x31; op2:x31; dest:x12; op1val:0x55555556;  op2val:0x55555556
TEST_RR_OP(srl,x0, x31, x31, 0x155, 0x55555556, 0x55555556, x3, 4, x24)

inst_2:
// opcode: srl ; op1:x7; op2:x7; dest:x7; op1val:-0x1;  op2val:-0x1
TEST_RR_OP(srl,x0, x7, x7, 0x1, -0x1, -0x1, x3, 8, x24)

inst_3:
// opcode: srl ; op1:x18; op2:x12; dest:x18; op1val:0x100;  op2val:0x0
TEST_RR_OP(srl,x0, x18, x12, 0x100, 0x100, 0x0, x3, 12, x24)

inst_4:
// opcode: srl ; op1:x14; op2:x3; dest:x8; op1val:0x9;  op2val:0x9
TEST_RR_OP(srl,x0, x14, x5, 0x0, 0x9, 0x9, x3, 16, x24)

inst_5:
// opcode: srl ; op1:x21; op2:x22; dest:x20; op1val:-0x80000000;  op2val:0xc
TEST_RR_OP(srl,x0, x21, x22, 0x80000, -0x80000000, 0xc, x3, 20, x24)

inst_6:
// opcode: srl ; op1:x4; op2:x17; dest:x30; op1val:0x0;  op2val:0xf
TEST_RR_OP(srl,x0, x4, x17, 0x0, 0x0, 0xf, x3, 24, x24)

inst_7:
// opcode: srl ; op1:x1; op2:x4; dest:x6; op1val:0x7fffffff;  op2val:0x1e
TEST_RR_OP(srl,x0, x1, x4, 0x1, 0x7fffffff, 0x1e, x3, 28, x24)

inst_8:
// opcode: srl ; op1:x0; op2:x21; dest:x15; op1val:0x0;  op2val:0x1d
TEST_RR_OP(srl,x0, x0, x21, 0x0, 0x0, 0x1d, x3, 32, x24)

inst_9:
// opcode: srl ; op1:x28; op2:x23; dest:x5; op1val:0x2;  op2val:0x6
TEST_RR_OP(srl,x0, x28, x23, 0x0, 0x2, 0x6, x3, 36, x24)

inst_10:
// opcode: srl ; op1:x9; op2:x30; dest:x4; op1val:0x4;  op2val:0xa
TEST_RR_OP(srl,x0, x9, x30, 0x0, 0x4, 0xa, x3, 40, x24)

inst_11:
// opcode: srl ; op1:x13; op2:x29; dest:x10; op1val:0x8;  op2val:0x2
TEST_RR_OP(srl,x0, x13, x29, 0x2, 0x8, 0x2, x3, 44, x24)

inst_12:
// opcode: srl ; op1:x2; op2:x16; dest:x25; op1val:0x10;  op2val:0x7
TEST_RR_OP(srl,x0, x2, x16, 0x0, 0x10, 0x7, x3, 48, x24)


inst_13:
// opcode: srl ; op1:x11; op2:x28; dest:x3; op1val:0x20;  op2val:0x8
TEST_RR_OP(srl,x0, x11, x28, 0x0, 0x20, 0x8, x3, 0, x7)

inst_14:
// opcode: srl ; op1:x10; op2:x6; dest:x23; op1val:0x40;  op2val:0xb
TEST_RR_OP(srl,x0, x10, x6, 0x0, 0x40, 0xb, x3, 4, x7)

inst_15:
// opcode: srl ; op1:x3; op2:x1; dest:x0; op1val:0x80;  op2val:0x6
TEST_RR_OP(srl,x0, x9, x1, 0, 0x80, 0x6, x3, 8, x7)

inst_16:
// opcode: srl ; op1:x6; op2:x8; dest:x14; op1val:0x200;  op2val:0xe
TEST_RR_OP(srl,x0, x6, x8, 0x0, 0x200, 0xe, x3, 12, x7)


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
