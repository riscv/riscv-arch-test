/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 5, 2025
Description: This test verifies the sltu instruction as a hint whatever the value in the registers, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*64.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",sltu)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: sltu ; op1:x16; op2:x16; dest:x4; op1val:0x800;  op2val:0x800
TEST_RR_OP(sltu,x0, x16, x16, 0x0, 0x800, 0x800, x3, 0, x19)

inst_1:
// opcode: sltu ; op1:x11; op2:x29; dest:x29; op1val:0x40000000000000;  op2val:0x40000000000000
TEST_RR_OP(sltu,x0, x11, x29, 0x0, 0x40000000000000, 0x40000000000000, x3, 8, x19)

inst_2:
// opcode: sltu ; op1:x12; op2:x12; dest:x12; op1val:0x2000000000000000;  op2val:0x2000000000000000
TEST_RR_OP(sltu,x0, x12, x12, 0x0, 0x2000000000000000, 0x2000000000000000, x3, 16, x19)

inst_3:
// opcode: sltu ; op1:x31; op2:x7; dest:x15; op1val:0x6;  op2val:0xffffffffffffffff
TEST_RR_OP(sltu,x0, x31, x7, 0x3, 0x6, 0xffffffffffffffff, x3, 24, x19)

inst_4:
// opcode: sltu ; op1:x26; op2:x17; dest:x26; op1val:0x5555555555555554;  op2val:0x1
TEST_RR_OP(sltu,x0, x26, x17, 0x0, 0x5555555555555554, 0x3, x3, 32, x19)

inst_5:
// opcode: sltu ; op1:x29; op2:x18; dest:x24; op1val:0x0;  op2val:0x1
TEST_RR_OP(sltu,x0, x29, x18, 0x3, 0x0, 0x3, x3, 40, x19)

inst_6:
// opcode: sltu ; op1:x14; op2:x22; dest:x25; op1val:0xffffffffffffffff;  op2val:0x100000000000000
TEST_RR_OP(sltu,x0, x14, x22, 0x0, 0xffffffffffffffff, 0x100000000000000, x3, 48, x19)

inst_7:
// opcode: sltu ; op1:x0; op2:x20; dest:x23; op1val:0x0;  op2val:0xfffffeffffffffff
TEST_RR_OP(sltu,x0, x0, x20, 0x3, 0x0, 0xfffffeffffffffff, x3, 56, x19)

inst_8:
// opcode: sltu ; op1:x10; op2:x5; dest:x0; op1val:0x1000000000000000;  op2val:0x2
TEST_RR_OP(sltu,x0, x10, x5, 0, 0x1000000000000000, 0x2, x3, 64, x19)

inst_9:
// opcode: sltu ; op1:x18; op2:x14; dest:x16; op1val:0xfffdffffffffffff;  op2val:0x4
TEST_RR_OP(sltu,x0, x18, x14, 0x0, 0xfffdffffffffffff, 0x4, x3, 72, x19)

inst_10:
// opcode: sltu ; op1:x9; op2:x24; dest:x8; op1val:0x6666666666666665;  op2val:0x8
TEST_RR_OP(sltu,x0, x9, x24, 0x0, 0x6666666666666665, 0x8, x3, 80, x19)

inst_11:
// opcode: sltu ; op1:x22; op2:x9; dest:x31; op1val:0x80000000000000;  op2val:0x20
TEST_RR_OP(sltu,x0, x22, x9, 0x0, 0x80000000000000, 0x20, x3, 88, x19)

inst_12:
// opcode: sltu ; op1:x21; op2:x13; dest:x2; op1val:0xfffffffffffffeff;  op2val:0x40
TEST_RR_OP(sltu,x0, x21, x13, 0x0, 0xfffffffffffffeff, 0x40, x3, 96, x19)

inst_13:
// opcode: sltu ; op1:x25; op2:x30; dest:x5; op1val:0xfffffbffffffffff;  op2val:0x80
TEST_RR_OP(sltu,x0, x25, x30, 0x0, 0xfffffbffffffffff, 0x80, x3, 104, x19)

inst_14:
// opcode: sltu ; op1:x24; op2:x4; dest:x11; op1val:0x200000000000000;  op2val:0x100
TEST_RR_OP(sltu,x0, x24, x4, 0x0, 0x200000000000000, 0x100, x3, 112, x19)

inst_15:
// opcode: sltu ; op1:x13; op2:x10; dest:x27; op1val:0x400000000;  op2val:0x200
TEST_RR_OP(sltu,x0, x13, x10, 0x0, 0x400000000, 0x200, x3, 120, x19)

inst_16:
// opcode: sltu ; op1:x15; op2:x6; dest:x3; op1val:0xfffffffffffffeff;  op2val:0x400
TEST_RR_OP(sltu,x0, x15, x6, 0x0, 0xfffffffffffffeff, 0x400, x3, 128, x19)


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
