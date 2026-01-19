
/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 4, 2025
Description: This test verifies the add instruction as a hint whatever the value in the registers, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*64.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",add)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)



inst_0:
// opcode: add ; op1:x0; op2:x0; dest:x20; op1val:0x0;  op2val:0x0
TEST_RR_OP(add,x0, x0, x0, 0x0, 0x0, 0x0, x3, 0, x16)

inst_1:
// opcode: add ; op1:x2; op2:x26; dest:x26; op1val:0x5;  op2val:-0x40000001
TEST_RR_OP(add,x0, x2, x26, 0xffffffffc0000004, 0x5, -0x40000001, x3, 8, x16)

inst_2:
// opcode: add ; op1:x22; op2:x22; dest:x22; op1val:-0x800001;  op2val:-0x800001
TEST_RR_OP(add,x0, x22, x22, 0xfffffffffefffffe, -0x800001, -0x800001, x3, 16, x16)

inst_3:
// opcode: add ; op1:x26; op2:x6; dest:x10; op1val:-0x41;  op2val:0x80000000000000
TEST_RR_OP(add,x0, x26, x6, 0x7fffffffffffbf, -0x41, 0x80000000000000, x3, 24, x16)

inst_4:
// opcode: add ; op1:x27; op2:x23; dest:x27; op1val:0x40;  op2val:0x40
TEST_RR_OP(add,x0, x27, x23, 0x80, 0x40, 0x40, x3, 32, x16)

inst_5:
// opcode: add ; op1:x20; op2:x3; dest:x2; op1val:0x6666666666666665;  op2val:-0x8000000000000000
TEST_RR_OP(add,x0, x20, x4, 0xe666666666666665, 0x6666666666666665, -0x8000000000000000, x3, 40, x16)

inst_6:
// opcode: add ; op1:x13; op2:x30; dest:x14; op1val:0x1;  op2val:0x0
TEST_RR_OP(add,x0, x13, x30, 0x1, 0x1, 0x0, x3, 48, x16)

inst_7:
// opcode: add ; op1:x6; op2:x10; dest:x7; op1val:0x20000;  op2val:0x7fffffffffffffff
TEST_RR_OP(add,x0, x6, x10, 0x800000000001ffff, 0x20000, 0x7fffffffffffffff, x3, 56, x16)

inst_8:
// opcode: add ; op1:x9; op2:x25; dest:x1; op1val:0x10000000;  op2val:0x1
TEST_RR_OP(add,x0, x9, x25, 0x10000001, 0x10000000, 0x1, x3, 64, x16)

inst_9:
// opcode: add ; op1:x14; op2:x31; dest:x5; op1val:-0x8000000000000000;  op2val:-0x101
TEST_RR_OP(add,x0, x14, x31, 0x7ffffffffffffeff, -0x8000000000000000, -0x101, x3, 72, x16)

inst_10:
// opcode: add ; op1:x29; op2:x1; dest:x19; op1val:0x0;  op2val:0x80000000000
TEST_RR_OP(add,x0, x29, x1, 0x80000000000, 0x0, 0x80000000000, x3, 80, x16)

inst_11:
// opcode: add ; op1:x15; op2:x11; dest:x21; op1val:0x7fffffffffffffff;  op2val:-0x10001
TEST_RR_OP(add,x0, x15, x11, 0x7ffffffffffefffe, 0x7fffffffffffffff, -0x10001, x3, 88, x16)

inst_12:
// opcode: add ; op1:x3; op2:x7; dest:x9; op1val:-0x5;  op2val:0x2
TEST_RR_OP(add,x0, x4, x7, 0xfffffffffffffffd, -0x5, 0x2, x3, 96, x16)

inst_13:
// opcode: add ; op1:x21; op2:x27; dest:x6; op1val:0x2000000000000000;  op2val:0x4
TEST_RR_OP(add,x0, x21, x27, 0x2000000000000004, 0x2000000000000000, 0x4, x3, 104, x16)

inst_14:
// opcode: add ; op1:x30; op2:x13; dest:x23; op1val:0x2000000000;  op2val:0x8
TEST_RR_OP(add,x0, x30, x13, 0x2000000008, 0x2000000000, 0x3, x3, 112, x16)

inst_15:
// opcode: add ; op1:x10; op2:x19; dest:x24; op1val:-0x20000000000001;  op2val:0x10
TEST_RR_OP(add,x0, x10, x19, 0xffe000000000000f, -0x20000000000001, 0x10, x3, 120, x16)

inst_16:
// opcode: add ; op1:x1; op2:x9; dest:x30; op1val:0x0;  op2val:0x20
TEST_RR_OP(add,x0, x1, x9, 0x20, 0x0, 0x20, x3, 128, x16)

inst_17:
// opcode: add ; op1:x12; op2:x4; dest:x13; op1val:0x800000000000000;  op2val:0x80
TEST_RR_OP(add,x0, x12, x4, 0x800000000000080, 0x800000000000000, 0x80, x3, 136, x16)

inst_18:
// opcode: add ; op1:x18; op2:x17; dest:x0; op1val:0x1;  op2val:0x100
TEST_RR_OP(add,x0, x18, x17, 0, 0x1, 0x100, x3, 144, x16)

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
