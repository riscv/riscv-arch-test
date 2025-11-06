/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 3, 2025
Description: This test verifies the and instruction as a hint whatever the value in the register, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*32.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",and)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)


inst_0:
// opcode: and ; op1:x0; op2:x25; dest:x25; op1val:0x4000;  op2val:0x7
TEST_RR_OP(and,x0, x24, x25, 0x0, 0x4000, 0x7, x3, 0, x8)

inst_1:
// opcode: and ; op1:x0 op2:x3; dest:x18; op1val:0x800;  op2val:0x800
TEST_RR_OP(and,x0, x4, x4, 0x800, 0x800, 0x800, x3, 4, x8)

inst_2:
// opcode: and ; op1:x0; op2:x19; dest:x19; op1val:-0x3;  op2val:-0x3
TEST_RR_OP(and,x0, x19, x19, 0xfffffffd, -0x3, -0x3, x3, 8, x8)

inst_3:
// opcode: and ; op1:x0 op2:x14; dest:x5; op1val:-0x1;  op2val:0x7fffffff
TEST_RR_OP(and,x0, x5, x14, 0x7fffffff, -0x1, 0x7fffffff, x3, 12, x8)

inst_4:
// opcode: and ; op1:x0; op2:x16; dest:x20; op1val:0x5;  op2val:0x5
TEST_RR_OP(and,x0, x23, x16, 0x5, 0x5, 0x5, x3, 16, x8)

inst_5:
// opcode: and ; op1:x0; op2:x2; dest:x30; op1val:0x2;  op2val:-0x80000000
TEST_RR_OP(and,x0, x20, x2, 0x0, 0x2, -0x80000000, x3, 20, x8)

inst_6:
// opcode: and ; op1:x0 op2:x24; dest:x13; op1val:0x33333333;  op2val:0x0
TEST_RR_OP(and,x0, x7, x24, 0x0, 0x33333333, 0x0, x3, 24, x8)

inst_7:
// opcode: and ; op1:x0; op2:x27; dest:x10; op1val:-0x40000001;  op2val:0x1
TEST_RR_OP(and,x0, x30, x27, 0x1, -0x40000001, 0x1, x3, 28, x8)

inst_8:
// opcode: and ; op1:x0; op2:x18; dest:x22; op1val:-0x80000000;  op2val:0x800
TEST_RR_OP(and,x0, x28, x18, 0x0, -0x80000000, 0x800, x3, 32, x8)

inst_9:
// opcode: and ; op1:x0 op2:x15; dest:x0; op1val:0x0;  op2val:0x200
TEST_RR_OP(and,x0, x2, x15, 0, 0x0, 0x200, x3, 36, x8)

inst_10:
// opcode: and ; op1:x0; op2:x26; dest:x12; op1val:0x7fffffff;  op2val:0x55555555
TEST_RR_OP(and,x0, x25, x26, 0x55555555, 0x7fffffff, 0x55555555, x3, 40, x8)

inst_11:
// opcode: and ; op1:x0 op2:x31; dest:x2; op1val:0x1;  op2val:0x55555554
TEST_RR_OP(and,x0, x1, x31, 0x0, 0x1, 0x55555554, x3, 44, x8)

inst_12:
// opcode: and ; op1:x0; op2:x11; dest:x14; op1val:0x40000;  op2val:0x2
TEST_RR_OP(and,x0, x27, x11, 0x0, 0x40000, 0x2, x3, 48, x8)

inst_13:
// opcode: and ; op1:x0; op2:x23; dest:x4; op1val:-0x20001;  op2val:0x4
TEST_RR_OP(and,x0, x31, x23, 0x4, -0x20001, 0x4, x3, 52, x8)

inst_14:
// opcode: and ; op1:x0; op2:x9; dest:x27; op1val:-0x55555555;  op2val:0x8
TEST_RR_OP(and,x0, x21, x9, 0x8, -0x55555555, 0x8, x3, 56, x8)

inst_15:
// opcode: and ; op1:x0; op2:x7; dest:x23; op1val:0x400;  op2val:0x10
TEST_RR_OP(and,x0, x26, x7, 0x0, 0x400, 0x10, x3, 60, x19)

RVTEST_SIGBASE( x30,signature_x30_1)
TEST_STORE_GPRS_AND_STATUS(x30)

#endif


RVTEST_CODE_END
RVMODEL_HALT

RVTEST_DATA_BEGIN

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
