/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 5, 2025
Description: This test verifies the sltiu instruction as a hint whatever the value in the register or imm field, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*64.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",sltiu)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: sltiu ; op1:x17; dest:x17; op1val:0xe;  immval:0x0
TEST_IMM_OP( sltiu,x0, x17, 0x0, 0xe, 0x0, x3, 0, x20)

inst_1:
// opcode: sltiu ; op1:x8; dest:x4; op1val:0xffffffffffefffff;  immval:0xfff
TEST_IMM_OP( sltiu,x0, x8, 0x1, 0xffffffffffefffff, 0xfff, x3, 8, x20)

inst_2:
// opcode: sltiu ; op1:x18; dest:x14; op1val:0x0;  immval:0x1
TEST_IMM_OP( sltiu,x0, x18, 0x1, 0x0, 0x1, x3, 16, x20)

inst_3:
// opcode: sltiu ; op1:x25; dest:x23; op1val:0xffffffffffffffff;  immval:0xe
TEST_IMM_OP( sltiu,x0, x25, 0x0, 0xffffffffffffffff, 0xe, x3, 24, x20)

inst_4:
// opcode: sltiu ; op1:x30; dest:x15; op1val:0x1;  immval:0x7ff
TEST_IMM_OP( sltiu,x0, x30, 0x1, 0x1, 0x7ff, x3, 32, x20)

inst_5:
// opcode: sltiu ; op1:x9; dest:x21; op1val:0x1;  immval:0x1
TEST_IMM_OP( sltiu,x0, x9, 0x0, 0x1, 0x1, x3, 40, x20)

inst_6:
// opcode: sltiu ; op1:x26; dest:x9; op1val:0x0;  immval:0x2
TEST_IMM_OP( sltiu,x0, x26, 0x1, 0x0, 0x2, x3, 48, x20)

inst_7:
// opcode: sltiu ; op1:x7; dest:x16; op1val:0xffffffffffffbfff;  immval:0x4
TEST_IMM_OP( sltiu,x0, x7, 0x0, 0xffffffffffffbfff, 0x4, x3, 56, x20)

inst_8:
// opcode: sltiu ; op1:x19; dest:x7; op1val:0x800000000;  immval:0x8
TEST_IMM_OP( sltiu,x0, x19, 0x0, 0x800000000, 0x8, x3, 64, x20)

inst_9:
// opcode: sltiu ; op1:x27; dest:x3; op1val:0x0;  immval:0x10
TEST_IMM_OP( sltiu,x0, x27, 0x1, 0x0, 0x10, x3, 72, x20)

inst_10:
// opcode: sltiu ; op1:x28; dest:x26; op1val:0xffffffffffffffff;  immval:0x20
TEST_IMM_OP( sltiu,x0, x28, 0x0, 0xffffffffffffffff, 0x20, x3, 80, x20)

inst_11:
// opcode: sltiu ; op1:x13; dest:x30; op1val:0xaaaaaaaaaaaaaaaa;  immval:0x40
TEST_IMM_OP( sltiu,x0, x13, 0x0, 0xaaaaaaaaaaaaaaaa, 0x40, x3, 88, x20)

inst_12:
// opcode: sltiu ; op1:x16; dest:x0; op1val:0x400000000;  immval:0x80
TEST_IMM_OP( sltiu,x0, x16, 0, 0x400000000, 0x80, x3, 96, x20)

inst_13:
// opcode: sltiu ; op1:x11; dest:x25; op1val:0x400000000;  immval:0x100
TEST_IMM_OP( sltiu,x0, x11, 0x0, 0x400000000, 0x100, x3, 104, x20)

inst_14:
// opcode: sltiu ; op1:x10; dest:x2; op1val:0xffffffffffffbfff;  immval:0x200
TEST_IMM_OP( sltiu,x0, x10, 0x0, 0xffffffffffffbfff, 0x200, x3, 112, x20)

inst_15:
// opcode: sltiu ; op1:x31; dest:x8; op1val:0xbfffffffffffffff;  immval:0x400
TEST_IMM_OP( sltiu,x0, x31, 0x0, 0xbfffffffffffffff, 0x400, x3, 120, x20)


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
