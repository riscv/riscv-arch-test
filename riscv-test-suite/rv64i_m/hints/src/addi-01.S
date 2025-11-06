
/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 4, 2025
Description: This test verifies the addi instruction as a hint whatever the value in the register or immval, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*64.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",addi)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: addi ; op1:x19; dest:x19; op1val:-0x1001;  immval:-0x800
TEST_IMM_OP( addi,x0, x19, 0xffffffffffffe7ff, -0x1001, -0x800, x3, 0, x18)

inst_1:
// opcode: addi ; op1:x1; dest:x15; op1val:-0x10001;  immval:0x0
TEST_IMM_OP( addi,x0, x1, 0xfffffffffffeffff, -0x10001, 0x0, x3, 8, x18)

inst_2:
// opcode: addi ; op1:x22; dest:x12; op1val:0x400000;  immval:0x7ff
TEST_IMM_OP( addi,x0, x22, 0x4007ff, 0x400000, 0x7ff, x3, 16, x18)

inst_3:
// opcode: addi ; op1:x26; dest:x10; op1val:0x40000000000000;  immval:0x1
TEST_IMM_OP( addi,x0, x26, 0x40000000000001, 0x40000000000000, 0x1, x3, 24, x18)

inst_4:
// opcode: addi ; op1:x17; dest:x21; op1val:-0x8000000000000000;  immval:-0x81
TEST_IMM_OP( addi,x0, x17, 0x7fffffffffffff7f, -0x8000000000000000, -0x81, x3, 32, x18)

inst_5:
// opcode: addi ; op1:x30; dest:x25; op1val:0x0;  immval:0x4
TEST_IMM_OP( addi,x0, x30, 0x4, 0x0, 0x4, x3, 40, x18)

inst_6:
// opcode: addi ; op1:x0; dest:x24; op1val:0x0;  immval:-0x201
TEST_IMM_OP( addi,x0, x0, 0xfffffffffffffdff, 0x0, -0x201, x3, 48, x18)

inst_7:
// opcode: addi ; op1:x14; dest:x30; op1val:0x1;  immval:0x333
TEST_IMM_OP( addi,x0, x14, 0x334, 0x1, 0x333, x3, 56, x18)

inst_8:
// opcode: addi ; op1:x6; dest:x4; op1val:0x7;  immval:0x7
TEST_IMM_OP( addi,x0, x6, 0xe, 0x7, 0x7, x3, 64, x18)

inst_9:
// opcode: addi ; op1:x21; dest:x8; op1val:-0x1000000000001;  immval:0x665
TEST_IMM_OP( addi,x0, x21, 0xffff000000000664, -0x1000000000001, 0x665, x3, 72, x18)

inst_10:
// opcode: addi ; op1:x10; dest:x13; op1val:0x20000;  immval:0x2
TEST_IMM_OP( addi,x0, x10, 0x20002, 0x20000, 0x2, x3, 80, x18)

inst_11:
// opcode: addi ; op1:x25; dest:x22; op1val:-0x80000000000001;  immval:0x8
TEST_IMM_OP( addi,x0, x25, 0xff80000000000007, -0x80000000000001, 0x8, x3, 88, x18)

inst_12:
// opcode: addi ; op1:x27; dest:x9; op1val:-0x800001;  immval:0x10
TEST_IMM_OP( addi,x0, x27, 0xffffffffff80000f, -0x800001, 0x10, x3, 96, x18)

inst_13:
// opcode: addi ; op1:x28; dest:x5; op1val:-0x40000000000001;  immval:0x20
TEST_IMM_OP( addi,x0, x28, 0xffc000000000001f, -0x40000000000001, 0x20, x3, 104, x18)

inst_14:
// opcode: addi ; op1:x2; dest:x6; op1val:0x100000000000;  immval:0x40
TEST_IMM_OP( addi,x0, x2, 0x100000000040, 0x100000000000, 0x40, x3, 112, x18)

inst_15:
// opcode: addi ; op1:x9; dest:x11; op1val:0x2000000;  immval:0x80
TEST_IMM_OP( addi,x0, x9, 0x2000080, 0x2000000, 0x80, x3, 120, x18)


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
