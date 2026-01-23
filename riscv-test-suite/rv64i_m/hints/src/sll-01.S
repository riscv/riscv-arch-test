
/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 4, 2025
Description: This test verifies the sll instruction as a hint whatever the value in the registers, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*64.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",sll)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: sll ; op1:x22; op2:x22; dest:x6; op1val:-0x4000000001;  op2val:-0x4000000001
TEST_RR_OP(sll,x0, x22, x22, 0x8000000000000000, -0x4000000001, -0x4000000001, x3, 0, x19)

inst_1:
// opcode: sll ; op1:x31; op2:x7; dest:x7; op1val:0x400;  op2val:0xd
TEST_RR_OP(sll,x0, x31, x7, 0x800000, 0x400, 0xd, x3, 8, x19)

inst_2:
// opcode: sll ; op1:x26; op2:x26; dest:x26; op1val:-0xa;  op2val:-0xa
TEST_RR_OP(sll,x0, x26, x26, 0xfd80000000000000, -0xa, -0xa, x3, 16, x19)

inst_3:
// opcode: sll ; op1:x15; op2:x28; dest:x20; op1val:0x100000000000;  op2val:0x0
TEST_RR_OP(sll,x0, x15, x28, 0x100000000000, 0x100000000000, 0x0, x3, 24, x19)

inst_4:
// opcode: sll ; op1:x12; op2:x10; dest:x12; op1val:0x1;  op2val:0x1
TEST_RR_OP(sll,x0, x12, x10, 0x2, 0x3, 0x3, x3, 32, x19)

inst_5:
// opcode: sll ; op1:x21; op2:x27; dest:x10; op1val:-0x8000000000000000;  op2val:0xe
TEST_RR_OP(sll,x0, x21, x27, 0x0, -0x8000000000000000, 0xe, x3, 40, x19)

inst_6:
// opcode: sll ; op1:x6; op2:x25; dest:x17; op1val:0x0;  op2val:0x3b
TEST_RR_OP(sll,x0, x6, x25, 0x0, 0x0, 0x3b, x3, 48, x19)

inst_7:
// opcode: sll ; op1:x24; op2:x11; dest:x23; op1val:0x7fffffffffffffff;  op2val:0x1f
TEST_RR_OP(sll,x0, x24, x11, 0xffffffff80000000, 0x7fffffffffffffff, 0x1f, x3, 56, x19)

inst_8:
// opcode: sll ; op1:x4; op2:x24; dest:x2; op1val:0x2;  op2val:0x9
TEST_RR_OP(sll,x0, x4, x24, 0x400, 0x2, 0x9, x3, 64, x19)

inst_9:
// opcode: sll ; op1:x2; op2:x17; dest:x4; op1val:0x4;  op2val:0xb
TEST_RR_OP(sll,x0, x2, x17, 0x2000, 0x4, 0xb, x3, 72, x19)

inst_10:
// opcode: sll ; op1:x8; op2:x5; dest:x11; op1val:0x8;  op2val:0x10
TEST_RR_OP(sll,x0, x8, x5, 0x80000, 0x8, 0x10, x3, 80, x19)

inst_11:
// opcode: sll ; op1:x18; op2:x4; dest:x16; op1val:0x10;  op2val:0x1
TEST_RR_OP(sll,x0, x18, x4, 0x20, 0x10, 0x3, x3, 88, x19)

inst_12:
// opcode: sll ; op1:x3; op2:x20; dest:x22; op1val:0x20;  op2val:0xf
TEST_RR_OP(sll,x0, x5, x20, 0x100000, 0x20, 0xf, x3, 96, x19)

inst_13:
// opcode: sll ; op1:x5; op2:x6; dest:x28; op1val:0x40;  op2val:0x3
TEST_RR_OP(sll,x0, x5, x6, 0x200, 0x40, 0x3, x3, 104, x19)

inst_14:
// opcode: sll ; op1:x11; op2:x8; dest:x25; op1val:0x80;  op2val:0xd
TEST_RR_OP(sll,x0, x11, x8, 0x100000, 0x80, 0xd, x3, 112, x19)

inst_15:
// opcode: sll ; op1:x13; op2:x2; dest:x14; op1val:0x100;  op2val:0x3f
TEST_RR_OP(sll,x0, x13, x2, 0x0, 0x100, 0x3f, x3, 120, x19)


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
