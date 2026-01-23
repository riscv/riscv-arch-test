
/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 3, 2025
Description: This test verifies the sll instruction as a hint whatever the value in the register, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*32.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",sll)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: sll ; op1:x16; op2:x28; dest:x28; op1val:-0x81;  op2val:0xa
TEST_RR_OP(sll,x0, x16, x28, 0xfffdfc00, -0x81, 0xa, x3, 0, x9)

inst_1:
// opcode: sll ; op1:x21; op2:x21; dest:x0; op1val:0x5;  op2val:0x5
TEST_RR_OP(sll,x0, x21, x21, 0, 0x5, 0x5, x3, 4, x9)

inst_2:
// opcode: sll ; op1:x18; op2:x18; dest:x18; op1val:-0x8001;  op2val:-0x8001
TEST_RR_OP(sll,x0, x18, x18, 0x80000000, -0x8001, -0x8001, x3, 8, x9)

inst_3:
// opcode: sll ; op1:x5; op2:x13; dest:x5; op1val:0x7;  op2val:0x0
TEST_RR_OP(sll,x0, x5, x13, 0x7, 0x7, 0x0, x3, 12, x9)

inst_4:
// opcode: sll ; op1:x22; op2:x12; dest:x23; op1val:0x6;  op2val:0x6
TEST_RR_OP(sll,x0, x22, x12, 0x180, 0x6, 0x6, x3, 16, x9)

inst_5:
// opcode: sll ; op1:x19; op2:x0; dest:x6; op1val:-0x80000000;  op2val:0x0
TEST_RR_OP(sll,x0, x19, x0, 0x80000000, -0x80000000, 0x0, x3, 20, x9)

inst_6:
// opcode: sll ; op1:x25; op2:x24; dest:x13; op1val:0x0;  op2val:0x4
TEST_RR_OP(sll,x0, x25, x24, 0x0, 0x0, 0x4, x3, 24, x9)

inst_7:
// opcode: sll ; op1:x12; op2:x26; dest:x16; op1val:0x7fffffff;  op2val:0x15
TEST_RR_OP(sll,x0, x12, x26, 0xffe00000, 0x7fffffff, 0x15, x3, 28, x9)

inst_8:
// opcode: sll ; op1:x6; op2:x14; dest:x20; op1val:0x1;  op2val:0x4
TEST_RR_OP(sll,x0, x6, x14, 0x10, 0x1, 0x4, x3, 32, x9)

inst_9:
// opcode: sll ; op1:x14; op2:x1; dest:x22; op1val:0x2;  op2val:0x1f
TEST_RR_OP(sll,x0, x14, x1, 0x0, 0x3, 0x1f, x3, 36, x9)

inst_10:
// opcode: sll ; op1:x29; op2:x7; dest:x21; op1val:0x4;  op2val:0x2
TEST_RR_OP(sll,x0, x29, x7, 0x10, 0x4, 0x3, x3, 40, x9)

inst_11:
// opcode: sll ; op1:x31; op2:x10; dest:x4; op1val:0x8;  op2val:0x1f
TEST_RR_OP(sll,x0, x31, x10, 0x0, 0x8, 0x1f, x3, 44, x9)

inst_12:
// opcode: sll ; op1:x17; op2:x20; dest:x7; op1val:0x10;  op2val:0x1f
TEST_RR_OP(sll,x0, x17, x20, 0x0, 0x10, 0x1f, x3, 48, x9)

inst_13:
// opcode: sll ; op1:x20; op2:x11; dest:x12; op1val:0x20;  op2val:0x17
TEST_RR_OP(sll,x0, x20, x11, 0x10000000, 0x20, 0x17, x3, 52, x9)

inst_14:
// opcode: sll ; op1:x11; op2:x22; dest:x3; op1val:0x40;  op2val:0x11
TEST_RR_OP(sll,x0, x11, x22, 0x800000, 0x40, 0x11, x3, 56, x9)

inst_15:
// opcode: sll ; op1:x0; op2:x30; dest:x24; op1val:0x0;  op2val:0x10
TEST_RR_OP(sll,x0, x0, x30, 0x0, 0x0, 0x10, x3, 60, x9)


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
