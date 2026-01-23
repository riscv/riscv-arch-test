/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 4, 2025
Description: This test verifies the or instruction as a hint whatever the value in the registers, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*64.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",or)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: or ; op1:x0; op2:x0; dest:x28; op1val:0x0;  op2val:0x0
TEST_RR_OP(or,x0, x0, x0, 0x0, 0x0, 0x0, x3, 0, x5)

inst_1:
// opcode: or ; op1:x21; op2:x8; dest:x8; op1val:0x800000000000;  op2val:-0x9
TEST_RR_OP(or,x0, x21, x8, 0xfffffffffffffff7, 0x800000000000, -0x9, x3, 8, x5)

inst_2:
// opcode: or ; op1:x11; op2:x11; dest:x11; op1val:-0xb504f333;  op2val:-0xb504f333
TEST_RR_OP(or,x0, x11, x11, 0xffffffff4afb0ccd, -0xb504f333, -0xb504f333, x3, 16, x5)

inst_3:
// opcode: or ; op1:x15; op2:x5; dest:x10; op1val:-0x40001;  op2val:0x400000000000000
TEST_RR_OP(or,x0, x15, x6, 0xfffffffffffbffff, -0x40001, 0x400000000000000, x3, 24, x5)

inst_4:
// opcode: or ; op1:x7; op2:x17; dest:x7; op1val:0x3333333333333333;  op2val:0x3333333333333333
TEST_RR_OP(or,x0, x7, x17, 0x3333333333333333, 0x3333333333333333, 0x3333333333333333, x3, 32, x5)

inst_5:
// opcode: or ; op1:x4; op2:x26; dest:x14; op1val:0x100000000;  op2val:-0x8000000000000000
TEST_RR_OP(or,x0, x4, x26, 0x8000000100000000, 0x100000000, -0x8000000000000000, x3, 40, x5)

inst_6:
// opcode: or ; op1:x14; op2:x18; dest:x25; op1val:0x4;  op2val:0x0
TEST_RR_OP(or,x0, x14, x18, 0x4, 0x4, 0x0, x3, 48, x5)

inst_7:
// opcode: or ; op1:x10; op2:x12; dest:x2; op1val:0x2;  op2val:0x7fffffffffffffff
TEST_RR_OP(or,x0, x10, x12, 0x7fffffffffffffff, 0x2, 0x7fffffffffffffff, x3, 56, x5)

inst_8:
// opcode: or ; op1:x24; op2:x19; dest:x27; op1val:0x100000000000;  op2val:0x1
TEST_RR_OP(or,x0, x24, x19, 0x100000000001, 0x100000000000, 0x3, x3, 64, x5)

inst_9:
// opcode: or ; op1:x31; op2:x22; dest:x21; op1val:-0x8000000000000000;  op2val:-0x80001
TEST_RR_OP(or,x0, x31, x22, 0xfffffffffff7ffff, -0x8000000000000000, -0x80001, x3, 72, x5)

inst_10:
// opcode: or ; op1:x20; op2:x25; dest:x17; op1val:0x0;  op2val:0x100
TEST_RR_OP(or,x0, x20, x25, 0x100, 0x0, 0x100, x3, 80, x5)

inst_11:
// opcode: or ; op1:x29; op2:x9; dest:x26; op1val:0x7fffffffffffffff;  op2val:-0x40000000001
TEST_RR_OP(or,x0, x29, x9, 0xffffffffffffffff, 0x7fffffffffffffff, -0x40000000001, x3, 88, x5)

inst_12:
// opcode: or ; op1:x28; op2:x15; dest:x16; op1val:0x1;  op2val:-0x200001
TEST_RR_OP(or,x0, x28, x15, 0xffffffffffdfffff, 0x3, -0x200001, x3, 96, x5)

inst_13:
// opcode: or ; op1:x13; op2:x27; dest:x30; op1val:-0xb504f333;  op2val:0x2
TEST_RR_OP(or,x0, x13, x27, 0xffffffff4afb0ccf, -0xb504f333, 0x2, x3, 104, x5)

inst_14:
// opcode: or ; op1:x9; op2:x3; dest:x0; op1val:0x2000;  op2val:0x4
TEST_RR_OP(or,x0, x9, x7, 0, 0x2000, 0x4, x3, 112, x14)


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
