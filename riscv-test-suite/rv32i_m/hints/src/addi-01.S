/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 3, 2025
Description: This test verifies the addi instruction as a hint whatever the value in the register or imm val, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*32.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",addi)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: addi ; op1:x0; dest:x0 op1val:0x20000000;  immval:-0x800
TEST_IMM_OP( addi,x0, x20, 0x1ffff800, 0x20000000, -0x800, x3, 0, x1)

inst_1:
// opcode: addi ; op1:x0 dest:x0 op1val:0x400;  immval:0x0
TEST_IMM_OP( addi,x0, x2, 0x400, 0x400, 0x0, x3, 4, x1)

inst_2:
// opcode: addi ; op1:x0 dest:x0; op1val:-0x201;  immval:0x7ff
TEST_IMM_OP( addi,x0, x4, 0x5fe, -0x201, 0x7ff, x3, 8, x1)

inst_3:
// opcode: addi ; op1:x0; dest:x0; op1val:0x0;  immval:0x1
TEST_IMM_OP( addi,x0, x30, 0x1, 0x0, 0x1, x3, 12, x1)

inst_4:
// opcode: addi ; op1:x0; dest:x0; op1val:-0x80000000;  immval:0x10
TEST_IMM_OP( addi,x0, x27, 0x80000010, -0x80000000, 0x10, x3, 16, x1)

inst_5:
// opcode: addi ; op1:x0; dest:x0; op1val:0x7fffffff;  immval:0x6
TEST_IMM_OP( addi,x0, x17, 0x80000005, 0x7fffffff, 0x6, x3, 20, x1)

inst_6:
// opcode: addi ; op1:x0; dest:x0; op1val:0x1;  immval:0x4
TEST_IMM_OP( addi,x0, x18, 0x5, 0x1, 0x4, x3, 24, x1)

inst_7:
// opcode: addi ; op1:x0; dest:x0 op1val:0x5;  immval:0x5
TEST_IMM_OP( addi,x0, x13, 0xa, 0x5, 0x5, x3, 28, x1)

inst_8:
// opcode: addi ; op1:x0; dest:x0; op1val:-0x55555555;  immval:-0x21
TEST_IMM_OP( addi,x0, x10, 0xaaaaaa8a, -0x55555555, -0x21, x3, 32, x1)

inst_9:
// opcode: addi ; op1:x0 dest:x0; op1val:-0x11;  immval:0x2
TEST_IMM_OP( addi,x0, x9, 0xfffffff1, -0x11, 0x2, x3, 36, x1)

inst_10:
// opcode: addi ; op1:x0 dest:x0 op1val:0xb505;  immval:0x8
TEST_IMM_OP( addi,x0, x7, 0xb50d, 0xb505, 0x8, x3, 40, x1)

inst_11:
// opcode: addi ; op1:x0; dest:x0; op1val:-0xb504;  immval:0x20
TEST_IMM_OP( addi,x0, x22, 0xffff4b1c, -0xb504, 0x20, x3, 44, x1)

inst_12:
// opcode: addi ; op1:x0; dest:x0 op1val:-0x200001;  immval:0x40
TEST_IMM_OP( addi,x0, x29, 0, -0x200001, 0x40, x3, 48, x1)

inst_13:
// opcode: addi ; op1:x0; dest:x0; op1val:0x5;  immval:0x80
TEST_IMM_OP( addi,x0, x25, 0x85, 0x5, 0x80, x3, 52, x1)

inst_14:
// opcode: addi ; op1:x0; dest:x0; op1val:-0x2000001;  immval:0x100
TEST_IMM_OP( addi,x0, x11, 0xfe0000ff, -0x2000001, 0x100, x3, 56, x1)

inst_15:
// opcode: addi ; op1:x0 dest:x0 op1val:0x10;  immval:0x200
TEST_IMM_OP( addi,x0, x6, 0x210, 0x10, 0x200, x3, 60, x1)

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
