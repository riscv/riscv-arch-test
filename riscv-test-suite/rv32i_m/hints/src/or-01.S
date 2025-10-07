
/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 3, 2025
Description: This test verifies the or instruction as a hint whatever the value in the register, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*32.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",or)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: or ; op1:x8; op2:x26; dest:x26; op1val:0x100000;  op2val:0x10
TEST_RR_OP(or,x0, x8, x26, 0x100010, 0x100000, 0x10, x3, 0, x5)

inst_1:
// opcode: or ; op1:x6; op2:x6; dest:x17; op1val:0x2;  op2val:0x2
TEST_RR_OP(or,x0, x6, x6, 0x2, 0x2, 0x2, x3, 4, x5)

inst_2:
// opcode: or ; op1:x31; op2:x31; dest:x31; op1val:-0x10000001;  op2val:-0x10000001
TEST_RR_OP(or,x0, x31, x31, 0xefffffff, -0x10000001, -0x10000001, x3, 8, x5)

inst_3:
// opcode: or ; op1:x27; op2:x29; dest:x27; op1val:-0x801;  op2val:0x400000
TEST_RR_OP(or,x0, x27, x29, 0xfffff7ff, -0x801, 0x400000, x3, 12, x5)

inst_4:
// opcode: or ; op1:x30; op2:x19; dest:x18; op1val:-0x100001;  op2val:-0x100001
TEST_RR_OP(or,x0, x30, x19, 0xffefffff, -0x100001, -0x100001, x3, 16, x5)

inst_5:
// opcode: or ; op1:x21; op2:x14; dest:x9; op1val:0x20000;  op2val:-0x80000000
TEST_RR_OP(or,x0, x21, x14, 0x80020000, 0x20000, -0x80000000, x3, 20, x5)

inst_6:
// opcode: or ; op1:x26; op2:x24; dest:x4; op1val:-0x2001;  op2val:0x0
TEST_RR_OP(or,x0, x26, x24, 0xffffdfff, -0x2001, 0x0, x3, 24, x5)

inst_7:
// opcode: or ; op1:x9; op2:x8; dest:x30; op1val:0x0;  op2val:0x7fffffff
TEST_RR_OP(or,x0, x9, x8, 0x7fffffff, 0x0, 0x7fffffff, x3, 28, x5)

inst_8:
// opcode: or ; op1:x23; op2:x7; dest:x8; op1val:-0x800001;  op2val:0x1
TEST_RR_OP(or,x0, x23, x7, 0xff7fffff, -0x800001, 0x1, x3, 32, x5)

inst_9:
// opcode: or ; op1:x12; op2:x0; dest:x22; op1val:-0x80000000;  op2val:0x0
TEST_RR_OP(or,x0, x12, x0, 0x80000000, -0x80000000, 0x0, x3, 36, x5)

inst_10:
// opcode: or ; op1:x10; op2:x30; dest:x28; op1val:0x7fffffff;  op2val:0x40
TEST_RR_OP(or,x0, x10, x30, 0x7fffffff, 0x7fffffff, 0x40, x3, 40, x5)

inst_11:
// opcode: or ; op1:x18; op2:x21; dest:x16; op1val:0x1;  op2val:0x55555554
TEST_RR_OP(or,x0, x18, x21, 0x55555555, 0x1, 0x55555554, x3, 44, x5)

inst_12:
// opcode: or ; op1:x14; op2:x17; dest:x12; op1val:0x1000;  op2val:0x2
TEST_RR_OP(or,x0, x14, x17, 0x1002, 0x1000, 0x2, x3, 48, x5)

inst_13:
// opcode: or ; op1:x19; op2:x16; dest:x15; op1val:-0x800001;  op2val:0x4
TEST_RR_OP(or,x0, x19, x16, 0xff7fffff, -0x800001, 0x4, x3, 52, x5)

inst_14:
// opcode: or ; op1:x4; op2:x2; dest:x7; op1val:-0x401;  op2val:0x8
TEST_RR_OP(or,x0, x4, x2, 0xfffffbff, -0x401, 0x8, x3, 56, x5)

inst_15:
// opcode: or ; op1:x2; op2:x22; dest:x11; op1val:0x7fffffff;  op2val:0x20
TEST_RR_OP(or,x0, x2, x22, 0x7fffffff, 0x7fffffff, 0x20, x3, 60, x5)

inst_16:
// opcode: or ; op1:x28; op2:x15; dest:x25; op1val:-0x201;  op2val:0x80
TEST_RR_OP(or,x0, x28, x15, 0xfffffdff, -0x201, 0x80, x3, 64, x5)

inst_17:
// opcode: or ; op1:x25; op2:x1; dest:x6; op1val:0xb504;  op2val:0x100
TEST_RR_OP(or,x0, x25, x1, 0xb504, 0xb504, 0x100, x3, 68, x5)

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
