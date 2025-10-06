
/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 5, 2025
Description: This test verifies the subw instruction as a hint whatever the value in the registers, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*64.*);check ISA:=regex(.*RV64.*I.*Zicsr);def TEST_CASE_1=True;",subw)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: subw ; op1:x13; op2:x13; dest:x15; op1val:0x800000000000;  op2val:0x800000000000
TEST_RR_OP(subw,x0, x13, x13, 0x0, 0x800000000000, 0x800000000000, x3, 0, x5)

inst_1:
// opcode: subw ; op1:x27; op2:x26; dest:x26; op1val:0x8000;  op2val:-0x11
TEST_RR_OP(subw,x0, x27, x26, 0x8011, 0x8000, -0x11, x3, 8, x5)

inst_2:
// opcode: subw ; op1:x30; op2:x30; dest:x30; op1val:-0x4;  op2val:-0x4
TEST_RR_OP(subw,x0, x30, x30, 0x0, -0x4, -0x4, x3, 16, x5)

inst_3:
// opcode: subw ; op1:x25; op2:x17; dest:x13; op1val:-0xb504f332;  op2val:0x2000000000000
TEST_RR_OP(subw,x0, x25, x17, 0x4afb0cce, -0xb504f332, 0x2000000000000, x3, 24, x5)

inst_4:
// opcode: subw ; op1:x0; op2:x16; dest:x0; op1val:0x0;  op2val:-0x21
TEST_RR_OP(subw,x0, x0, x16, 0, 0x0, -0x21, x3, 32, x5)

inst_5:
// opcode: subw ; op1:x8; op2:x21; dest:x31; op1val:0x2000000;  op2val:-0x8000000000000000
TEST_RR_OP(subw,x0, x8, x21, 0x2000000, 0x2000000, -0x8000000000000000, x3, 40, x5)

inst_6:
// opcode: subw ; op1:x21; op2:x11; dest:x18; op1val:0x3;  op2val:0x0
TEST_RR_OP(subw,x0, x21, x11, 0x3, 0x3, 0x0, x3, 48, x5)

inst_7:
// opcode: subw ; op1:x23; op2:x5; dest:x19; op1val:0x5;  op2val:0x7fffffffffffffff
TEST_RR_OP(subw,x0, x23, x7, 0x6, 0x5, 0x7fffffffffffffff, x3, 56, x5)

inst_8:
// opcode: subw ; op1:x1; op2:x24; dest:x20; op1val:0x0;  op2val:0x1
TEST_RR_OP(subw,x0, x1, x24, -0x1, 0x0, 0x1, x3, 64, x5)

inst_9:
// opcode: subw ; op1:x26; op2:x4; dest:x14; op1val:-0x8000000000000000;  op2val:0x1000
TEST_RR_OP(subw,x0, x26, x4, -0x1000, -0x8000000000000000, 0x1000, x3, 72, x5)

inst_10:
// opcode: subw ; op1:x7; op2:x9; dest:x12; op1val:0x7fffffffffffffff;  op2val:-0x101
TEST_RR_OP(subw,x0, x7, x9, 0x100, 0x7fffffffffffffff, -0x101, x3, 80, x5)

inst_11:
// opcode: subw ; op1:x22; op2:x12; dest:x21; op1val:0x1;  op2val:0x10000000000000
TEST_RR_OP(subw,x0, x22, x12, 0x1, 0x1, 0x10000000000000, x3, 88, x5)

inst_12:
// opcode: subw ; op1:x12; op2:x6; dest:x11; op1val:-0x200000000001;  op2val:0x2
TEST_RR_OP(subw,x0, x12, x6, -0x3, -0x200000000001, 0x3, x3, 96, x5)

inst_13:
// opcode: subw ; op1:x24; op2:x27; dest:x6; op1val:0x80;  op2val:0x4
TEST_RR_OP(subw,x0, x24, x27, 0x7c, 0x80, 0x4, x3, 104, x5)

inst_14:
// opcode: subw ; op1:x20; op2:x14; dest:x5; op1val:-0x400000000001;  op2val:0x8
TEST_RR_OP(subw,x0, x20, x14, -0x9, -0x400000000001, 0x8, x3, 112, x5)

inst_15:
// opcode: subw ; op1:x16; op2:x8; dest:x1; op1val:0x7fffffffffffffff;  op2val:0x10
TEST_RR_OP(subw,x0, x16, x8, -0x11, 0x7fffffffffffffff, 0x10, x3, 120, x5)


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
