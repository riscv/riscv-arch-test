
/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 3, 2025
Description: This test verifies the andi instruction as a hint whatever the value in the register, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*32.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",andi)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: andi ; op1:x0; dest:x10; op1val:-0x2;  immval:-0x800
TEST_IMM_OP( andi,x0, x22, 0xfffff800, -0x2, -0x800, x3, 0, x24)

inst_1:
// opcode: andi ; op1:x0; dest:x25; op1val:-0x1001;  immval:0x0
TEST_IMM_OP( andi,x0, x25, 0x0, -0x1001, 0x0, x3, 4, x24)

inst_2:
// opcode: andi ; op1:x0; dest:x17; op1val:-0x2000001;  immval:0x7ff
TEST_IMM_OP( andi,x0, x16, 0x7ff, -0x2000001, 0x7ff, x3, 8, x24)

inst_3:
// opcode: andi ; op1:x0 dest:x8; op1val:-0x20001;  immval:0x1
TEST_IMM_OP( andi,x0, x2, 0x1, -0x20001, 0x1, x3, 12, x24)

inst_4:
// opcode: andi ; op1:x0; dest:x30; op1val:-0x80000000;  immval:0x4
TEST_IMM_OP( andi,x0, x28, 0x0, -0x80000000, 0x4, x3, 16, x24)

inst_5:
// opcode: andi ; op1:x0 dest:x19; op1val:0x0;  immval:-0x800
TEST_IMM_OP( andi,x0, x4, 0x0, 0x0, -0x800, x3, 20, x24)

inst_6:
// opcode: andi ; op1:x0; dest:x2; op1val:0x7fffffff;  immval:0x6
TEST_IMM_OP( andi,x0, x10, 0x6, 0x7fffffff, 0x6, x3, 24, x24)

inst_7:
// opcode: andi ; op1:x0 dest:x13; op1val:0x1;  immval:0x554
TEST_IMM_OP( andi,x0, x7, 0x0, 0x1, 0x554, x3, 28, x24)

inst_8:
// opcode: andi ; op1:x0; dest:x9; op1val:0x80;  immval:0x80
TEST_IMM_OP( andi,x0, x27, 0x80, 0x80, 0x80, x3, 32, x24)

inst_9:
// opcode: andi ; op1:x0; dest:x3; op1val:0x7fffffff;  immval:-0x2c
TEST_IMM_OP( andi,x0, x17, 0x7fffffd4, 0x7fffffff, -0x2c, x3, 36, x24)

inst_10:
// opcode: andi ; op1:x0 dest:x26; op1val:0x0;  immval:0x2
TEST_IMM_OP( andi,x0, x0, 0x0, 0x0, 0x2, x3, 40, x24)

inst_11:
// opcode: andi ; op1:x0; dest:x21; op1val:0x66666666;  immval:0x8
TEST_IMM_OP( andi,x0, x23, 0x0, 0x66666666, 0x8, x3, 44, x24)

inst_12:
// opcode: andi ; op1:x0 dest:x14; op1val:0x0;  immval:0x10
TEST_IMM_OP( andi,x0, x6, 0x0, 0x0, 0x10, x3, 48, x24)

inst_13:
// opcode: andi ; op1:x0 dest:x22; op1val:0x100;  immval:0x20
TEST_IMM_OP( andi,x0, x5, 0x0, 0x100, 0x20, x3, 52, x24)

inst_14:
// opcode: andi ; op1:x0 dest:x29; op1val:-0x5;  immval:0x40
TEST_IMM_OP( andi,x0, x8, 0x40, -0x5, 0x40, x3, 56, x24)

inst_15:
// opcode: andi ; op1:x0; dest:x23; op1val:0x1;  immval:0x100
TEST_IMM_OP( andi,x0, x12, 0x0, 0x1, 0x100, x3, 60, x24)

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
