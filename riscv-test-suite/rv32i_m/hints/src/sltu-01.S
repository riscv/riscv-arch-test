
/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 3, 2025
Description: This test verifies the sltu instruction as a hint whatever the value in the register, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*32.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",sltu)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: sltu ; op1:x0; op2:x31; dest:x31; op1val:0x0;  op2val:0xfffffffe
TEST_RR_OP(sltu,x0, x0, x31, 0x1, 0x0, 0xfffffffe, x3, 0, x7)

inst_1:
// opcode: sltu ; op1:x19; op2:x19; dest:x5; op1val:0x100000;  op2val:0x100000
TEST_RR_OP(sltu,x0, x19, x19, 0x0, 0x100000, 0x100000, x3, 4, x7)

inst_2:
// opcode: sltu ; op1:x25; op2:x25; dest:x25; op1val:0x40000000;  op2val:0x40000000
TEST_RR_OP(sltu,x0, x25, x25, 0x0, 0x40000000, 0x40000000, x3, 8, x7)

inst_3:
// opcode: sltu ; op1:x14; op2:x24; dest:x14; op1val:0xfffffffe;  op2val:0xffffffff
TEST_RR_OP(sltu,x0, x14, x24, 0x1, 0xfffffffe, 0xffffffff, x3, 12, x7)

inst_4:
// opcode: sltu ; op1:x17; op2:x13; dest:x12; op1val:0x1;  op2val:0x1
TEST_RR_OP(sltu,x0, x17, x13, 0x0, 0x1, 0x1, x3, 16, x7)

inst_5:
// opcode: sltu ; op1:x26; op2:x18; dest:x24; op1val:0x0;  op2val:0xb
TEST_RR_OP(sltu,x0, x26, x18, 0x1, 0x0, 0xb, x3, 20, x7)

inst_6:
// opcode: sltu ; op1:x5; op2:x14; dest:x19; op1val:0xffffffff;  op2val:0x0
TEST_RR_OP(sltu,x0, x5, x14, 0x0, 0xffffffff, 0x0, x3, 24, x7)

inst_7:
// opcode: sltu ; op1:x3; op2:x22; dest:x0; op1val:0x4;  op2val:0x2
TEST_RR_OP(sltu,x0, x2, x22, 0, 0x4, 0x2, x3, 28, x7)

inst_8:
// opcode: sltu ; op1:x23; op2:x29; dest:x20; op1val:0xf7ffffff;  op2val:0x4
TEST_RR_OP(sltu,x0, x23, x29, 0x0, 0xf7ffffff, 0x4, x3, 32, x7)

inst_9:
// opcode: sltu ; op1:x4; op2:x6; dest:x10; op1val:0x11;  op2val:0x8
TEST_RR_OP(sltu,x0, x4, x6, 0x0, 0x11, 0x8, x3, 36, x7)

inst_10:
// opcode: sltu ; op1:x12; op2:x17; dest:x1; op1val:0x7fffffff;  op2val:0x10
TEST_RR_OP(sltu,x0, x12, x17, 0x0, 0x7fffffff, 0x10, x3, 40, x7)

inst_11:
// opcode: sltu ; op1:x30; op2:x8; dest:x6; op1val:0x2000000;  op2val:0x20
TEST_RR_OP(sltu,x0, x30, x8, 0x0, 0x2000000, 0x20, x3, 44, x7)

inst_12:
// opcode: sltu ; op1:x21; op2:x16; dest:x3; op1val:0xfffff7ff;  op2val:0x40
TEST_RR_OP(sltu,x0, x21, x16, 0x0, 0xfffff7ff, 0x40, x3, 48, x7)

inst_13:
// opcode: sltu ; op1:x29; op2:x26; dest:x17; op1val:0x400;  op2val:0x80
TEST_RR_OP(sltu,x0, x29, x26, 0x0, 0x400, 0x80, x3, 52, x7)

inst_14:
// opcode: sltu ; op1:x18; op2:x10; dest:x28; op1val:0xd;  op2val:0x100
TEST_RR_OP(sltu,x0, x18, x10, 0x1, 0xd, 0x100, x3, 56, x7)

inst_15:
// opcode: sltu ; op1:x2; op2:x28; dest:x11; op1val:0x4;  op2val:0x200
TEST_RR_OP(sltu,x0, x2, x28, 0x1, 0x4, 0x200, x3, 60, x7)

inst_16:
// opcode: sltu ; op1:x8; op2:x30; dest:x29; op1val:0xffffffbf;  op2val:0x400
TEST_RR_OP(sltu,x0, x8, x30, 0x0, 0xffffffbf, 0x400, x3, 64, x17)

inst_17:
// opcode: sltu ; op1:x22; op2:x11; dest:x7; op1val:0x80;  op2val:0x800
TEST_RR_OP(sltu,x0, x22, x11, 0x1, 0x80, 0x800, x3, 68, x17)


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
