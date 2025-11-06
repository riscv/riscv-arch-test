/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 4, 2025
Description: This test verifies the addw instruction as a hint whatever the value in the registers, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*64.*);check ISA:=regex(.*RV64.*I.*Zicsr);def TEST_CASE_1=True;",addw)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: addw ; op1:x21; op2:x21; dest:x3; op1val:0x200000000;  op2val:0x200000000
TEST_RR_OP(addw,x0, x21, x21, 0x0, 0x200000000, 0x200000000, x3, 0, x6)

inst_1:
// opcode: addw ; op1:x5; op2:x16; dest:x16; op1val:0x20;  op2val:-0x10001
TEST_RR_OP(addw,x0, x5, x16, -0xffe1, 0x20, -0x10001, x3, 8, x6)

inst_2:
// opcode: addw ; op1:x7; op2:x7; dest:x7; op1val:-0x8000000001;  op2val:-0x8000000001
TEST_RR_OP(addw,x0, x7, x7, -0x2, -0x8000000001, -0x8000000001, x3, 16, x6)

inst_3:
// opcode: addw ; op1:x29; op2:x11; dest:x4; op1val:-0x4001;  op2val:0x4000000000000
TEST_RR_OP(addw,x0, x29, x11, -0x4001, -0x4001, 0x4000000000000, x3, 24, x6)

inst_4:
// opcode: addw ; op1:x23; op2:x8; dest:x23; op1val:-0x800000000001;  op2val:-0x800000000001
TEST_RR_OP(addw,x0, x23, x8, -0x2, -0x800000000001, -0x800000000001, x3, 32, x6)

inst_5:
// opcode: addw ; op1:x26; op2:x28; dest:x13; op1val:0x7fffffffffffffff;  op2val:-0x8000000000000000
TEST_RR_OP(addw,x0, x26, x28, -0x3, 0x7fffffffffffffff, -0x8000000000000000, x3, 40, x6)

inst_6:
// opcode: addw ; op1:x9; op2:x30; dest:x19; op1val:0x200000000;  op2val:0x0
TEST_RR_OP(addw,x0, x9, x30, 0x0, 0x200000000, 0x0, x3, 48, x6)

inst_7:
// opcode: addw ; op1:x8; op2:x18; dest:x27; op1val:0x3333333333333332;  op2val:0x7fffffffffffffff
TEST_RR_OP(addw,x0, x8, x18, 0x33333331, 0x3333333333333332, 0x7fffffffffffffff, x3, 56, x6)

inst_8:
// opcode: addw ; op1:x18; op2:x22; dest:x8; op1val:-0x10000001;  op2val:0x1
TEST_RR_OP(addw,x0, x18, x22, -0x10000000, -0x10000001, 0x3, x3, 64, x6)

inst_9:
// opcode: addw ; op1:x13; op2:x20; dest:x0; op1val:-0x8000000000000000;  op2val:0x2000
TEST_RR_OP(addw,x0, x13, x20, 0, -0x8000000000000000, 0x2000, x3, 72, x6)

inst_10:
// opcode: addw ; op1:x30; op2:x24; dest:x28; op1val:0x0;  op2val:0x2000000
TEST_RR_OP(addw,x0, x30, x24, 0x2000000, 0x0, 0x2000000, x3, 80, x6)

inst_11:
// opcode: addw ; op1:x17; op2:x0; dest:x22; op1val:0x1;  op2val:0x0
TEST_RR_OP(addw,x0, x17, x0, 0x3, 0x3, 0x0, x3, 88, x6)

inst_12:
// opcode: addw ; op1:x0; op2:x4; dest:x2; op1val:0x0;  op2val:0x2
TEST_RR_OP(addw,x0, x0, x4, 0x2, 0x0, 0x2, x3, 96, x6)

inst_13:
// opcode: addw ; op1:x28; op2:x14; dest:x21; op1val:0x8000000;  op2val:0x4
TEST_RR_OP(addw,x0, x28, x14, 0x8000004, 0x8000000, 0x4, x3, 104, x6)

inst_14:
// opcode: addw ; op1:x4; op2:x31; dest:x10; op1val:0x800000000000000;  op2val:0x8
TEST_RR_OP(addw,x0, x4, x31, 0x8, 0x800000000000000, 0x8, x3, 112, x6)

inst_15:
// opcode: addw ; op1:x20; op2:x25; dest:x31; op1val:-0xb504f333;  op2val:0x10
TEST_RR_OP(addw,x0, x20, x25, 0x4afb0cdd, -0xb504f333, 0x10, x3, 120, x6)


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
