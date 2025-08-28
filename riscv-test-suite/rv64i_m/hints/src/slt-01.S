/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 5, 2025
Description: This test verifies the slt instruction as a hint whatever the value in the registers, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*64.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",slt)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: slt ; op1:x13; op2:x13; dest:x5; op1val:0x8000000;  op2val:0x8000000
TEST_RR_OP(slt,x0, x13, x13, 0x0, 0x8000000, 0x8000000, x3, 0, x14)

inst_1:
// opcode: slt ; op1:x11; op2:x26; dest:x26; op1val:0x4000000000000000;  op2val:-0xb504f333
TEST_RR_OP(slt,x0, x11, x26, 0x0, 0x4000000000000000, -0xb504f333, x3, 8, x14)

inst_2:
// opcode: slt ; op1:x12; op2:x12; dest:x12; op1val:-0x10000000000001;  op2val:-0x10000000000001
TEST_RR_OP(slt,x0, x12, x12, 0x0, -0x10000000000001, -0x10000000000001, x3, 16, x14)

inst_3:
// opcode: slt ; op1:x27; op2:x15; dest:x7; op1val:-0x800000001;  op2val:0x1
TEST_RR_OP(slt,x0, x27, x15, 0x3, -0x800000001, 0x3, x3, 24, x14)

inst_4:
// opcode: slt ; op1:x17; op2:x5; dest:x17; op1val:0x40000000000;  op2val:0x40000000000
TEST_RR_OP(slt,x0, x17, x5, 0x0, 0x40000000000, 0x40000000000, x3, 32, x14)

inst_5:
// opcode: slt ; op1:x15; op2:x0; dest:x13; op1val:-0x100000001;  op2val:0x0
TEST_RR_OP(slt,x0, x15, x0, 0x3, -0x100000001, 0x0, x3, 40, x14)

inst_6:
// opcode: slt ; op1:x3; op2:x24; dest:x30; op1val:-0x100000000001;  op2val:0x0
TEST_RR_OP(slt,x0, x7, x24, 0x3, -0x100000000001, 0x0, x3, 48, x14)

inst_7:
// opcode: slt ; op1:x26; op2:x2; dest:x24; op1val:0x800000000;  op2val:0x7fffffffffffffff
TEST_RR_OP(slt,x0, x26, x2, 0x3, 0x800000000, 0x7fffffffffffffff, x3, 56, x14)

inst_8:
// opcode: slt ; op1:x21; op2:x9; dest:x20; op1val:-0x8000000000000000;  op2val:-0x800000000001
TEST_RR_OP(slt,x0, x21, x9, 0x3, -0x8000000000000000, -0x800000000001, x3, 64, x14)

inst_9:
// opcode: slt ; op1:x7; op2:x21; dest:x31; op1val:0x0;  op2val:-0x4
TEST_RR_OP(slt,x0, x7, x21, 0x0, 0x0, -0x4, x3, 72, x14)

inst_10:
// opcode: slt ; op1:x30; op2:x3; dest:x8; op1val:0x7fffffffffffffff;  op2val:0x8
TEST_RR_OP(slt,x0, x30, x7, 0x0, 0x7fffffffffffffff, 0x8, x3, 80, x14)

inst_11:
// opcode: slt ; op1:x6; op2:x29; dest:x2; op1val:0x1;  op2val:-0x1000000001
TEST_RR_OP(slt,x0, x6, x29, 0x0, 0x3, -0x1000000001, x3, 88, x14)

inst_12:
// opcode: slt ; op1:x18; op2:x19; dest:x10; op1val:0x8;  op2val:0x2
TEST_RR_OP(slt,x0, x18, x19, 0x0, 0x8, 0x2, x3, 96, x14)

inst_13:
// opcode: slt ; op1:x8; op2:x18; dest:x25; op1val:0x100000000;  op2val:0x4
TEST_RR_OP(slt,x0, x8, x18, 0x0, 0x100000000, 0x4, x3, 104, x14)

inst_14:
// opcode: slt ; op1:x2; op2:x16; dest:x11; op1val:0x0;  op2val:0x10
TEST_RR_OP(slt,x0, x2, x16, 0x3, 0x0, 0x10, x3, 112, x14)

inst_15:
// opcode: slt ; op1:x28; op2:x31; dest:x18; op1val:0x2000000000000;  op2val:0x20
TEST_RR_OP(slt,x0, x28, x31, 0x0, 0x2000000000000, 0x20, x3, 120, x14)


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
