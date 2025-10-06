/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 5, 2025
Description: This test verifies the sub instruction as a hint whatever the value in the registers, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*64.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",sub)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: sub ; op1:x21; op2:x21; dest:x16; op1val:0x8000000000;  op2val:0x8000000000
TEST_RR_OP(sub,x0, x21, x21, 0x0, 0x8000000000, 0x8000000000, x3, 0, x28)

inst_1:
// opcode: sub ; op1:x18; op2:x6; dest:x6; op1val:0x1000000000000000;  op2val:-0x2000000000001
TEST_RR_OP(sub,x0, x18, x6, 0x1002000000000001, 0x1000000000000000, -0x2000000000001, x3, 8, x28)

inst_2:
// opcode: sub ; op1:x11; op2:x11; dest:x11; op1val:-0x800000000000001;  op2val:-0x800000000000001
TEST_RR_OP(sub,x0, x11, x11, 0x0, -0x800000000000001, -0x800000000000001, x3, 16, x28)

inst_3:
// opcode: sub ; op1:x2; op2:x19; dest:x27; op1val:-0x801;  op2val:0x800
TEST_RR_OP(sub,x0, x2, x19, 0xffffffffffffefff, -0x801, 0x800, x3, 24, x28)

inst_4:
// opcode: sub ; op1:x31; op2:x20; dest:x31; op1val:0x0;  op2val:0x0
TEST_RR_OP(sub,x0, x31, x20, 0x0, 0x0, 0x0, x3, 32, x28)

inst_5:
// opcode: sub ; op1:x29; op2:x8; dest:x20; op1val:-0x2000000000001;  op2val:-0x8000000000000000
TEST_RR_OP(sub,x0, x29, x8, 0x7ffdffffffffffff, -0x2000000000001, -0x8000000000000000, x3, 40, x28)

inst_6:
// opcode: sub ; op1:x8; op2:x1; dest:x19; op1val:-0x100000001;  op2val:0x7fffffffffffffff
TEST_RR_OP(sub,x0, x8, x1, 0x7fffffff00000000, -0x100000001, 0x7fffffffffffffff, x3, 48, x28)

inst_7:
// opcode: sub ; op1:x10; op2:x3; dest:x9; op1val:0x10;  op2val:0x1
TEST_RR_OP(sub,x0, x10, x8, 0xf, 0x10, 0x1, x3, 56, x28)

inst_8:
// opcode: sub ; op1:x24; op2:x14; dest:x22; op1val:-0x8000000000000000;  op2val:-0x41
TEST_RR_OP(sub,x0, x24, x14, 0x8000000000000041, -0x8000000000000000, -0x41, x3, 64, x28)

inst_9:
// opcode: sub ; op1:x1; op2:x10; dest:x12; op1val:0x7fffffffffffffff;  op2val:0x4000000
TEST_RR_OP(sub,x0, x1, x10, 0x7ffffffffbffffff, 0x7fffffffffffffff, 0x4000000, x3, 72, x28)

inst_10:
// opcode: sub ; op1:x22; op2:x9; dest:x25; op1val:0x1;  op2val:0x4000000000000000
TEST_RR_OP(sub,x0, x22, x9, 0xc000000000000001, 0x1, 0x4000000000000000, x3, 80, x28)

inst_11:
// opcode: sub ; op1:x13; op2:x15; dest:x29; op1val:0x4;  op2val:0x4
TEST_RR_OP(sub,x0, x13, x15, 0x0, 0x4, 0x4, x3, 88, x28)

inst_12:
// opcode: sub ; op1:x5; op2:x13; dest:x10; op1val:-0x1001;  op2val:0x8
TEST_RR_OP(sub,x0, x5, x13, 0xffffffffffffeff7, -0x1001, 0x8, x3, 96, x28)

inst_13:
// opcode: sub ; op1:x0; op2:x5; dest:x7; op1val:0x0;  op2val:0x10
TEST_RR_OP(sub,x0, x0, x5, 0xfffffffffffffff0, 0x0, 0x10, x3, 104, x28)

inst_14:
// opcode: sub ; op1:x7; op2:x22; dest:x4; op1val:0x4;  op2val:0x20
TEST_RR_OP(sub,x0, x7, x22, 0xffffffffffffffe4, 0x4, 0x20, x3, 112, x28)

inst_15:
// opcode: sub ; op1:x15; op2:x17; dest:x26; op1val:0xb504f333;  op2val:0x40
TEST_RR_OP(sub,x0, x15, x17, 0xb504f2f3, 0xb504f333, 0x40, x3, 120, x28)


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
