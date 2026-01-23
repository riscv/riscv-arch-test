
/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 3, 2025
Description: This test verifies the add instruction as a hint whatever the value in the register, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*32.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",add)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: add ; op1:x0 op2:x24; dest:x24; op1val:0x7fffffff;  op2val:0x1
TEST_RR_OP(add,x0, x4, x24, 0x80000000, 0x7fffffff, 0x1, x3, 0, x18)

inst_1:
// opcode: add ; op1:x0; op2:x10; dest:x28; op1val:0x20000;  op2val:0x20000
TEST_RR_OP(add,x0, x10, x10, 0x40000, 0x20000, 0x20000, x3, 4, x18)

inst_2:
// opcode: add ; op1:x0; op2:x21; dest:x21; op1val:-0x1000001;  op2val:-0x1000001
TEST_RR_OP(add,x0, x21, x21, 0xfdfffffe, -0x1000001, -0x1000001, x3, 8, x18)

inst_3:
// opcode: add ; op1:x0; op2:x31; dest:x22; op1val:-0x2;  op2val:0x40000
TEST_RR_OP(add,x0, x22, x31, 0x3fffe, -0x2, 0x40000, x3, 12, x18)

inst_4:
// opcode: add ; op1:x0; op2:x6; dest:x11; op1val:0x55555556;  op2val:0x55555556
TEST_RR_OP(add,x0, x12, x6, 0xaaaaaaac, 0x55555556, 0x55555556, x3, 16, x18)

inst_5:
// opcode: add ; op1:x0; op2:x13; dest:x10; op1val:0x2;  op2val:-0x80000000
TEST_RR_OP(add,x0, x29, x13, 0x80000002, 0x2, -0x80000000, x3, 20, x18)

inst_6:
// opcode: add ; op1:x0; op2:x5; dest:x26; op1val:-0x11;  op2val:0x0
TEST_RR_OP(add,x0, x31, x5, 0xffffffef, -0x11, 0x0, x3, 24, x18)

inst_7:
// opcode: add ; op1:x0 op2:x1; dest:x7; op1val:0x66666666;  op2val:0x7fffffff
TEST_RR_OP(add,x0, x2, x1, 0xe6666665, 0x66666666, 0x7fffffff, x3, 28, x18)

inst_8:
// opcode: add ; op1:x0 op2:x25; dest:x14; op1val:-0x80000000;  op2val:-0x55555556
TEST_RR_OP(add,x0, x8, x25, 0x2aaaaaaa, -0x80000000, -0x55555556, x3, 32, x18)

inst_9:
// opcode: add ; op1:x0; op2:x8; dest:x1; op1val:0x0;  op2val:-0x2000001
TEST_RR_OP(add,x0, x13, x8, 0xfdffffff, 0x0, -0x2000001, x3, 36, x18)

inst_10:
// opcode: add ; op1:x0; op2:x9; dest:x0; op1val:0x1;  op2val:0x800000
TEST_RR_OP(add,x0, x28, x9, 0, 0x1, 0x800000, x3, 40, x18)



inst_11:
// opcode: add ; op1:x0; op2:x4; dest:x20; op1val:0x7;  op2val:0x2
TEST_RR_OP(add,x0, x14, x4, 0x9, 0x7, 0x2, x3, 44, x18)

inst_12:
// opcode: add ; op1:x0 op2:x19; dest:x16; op1val:0x8;  op2val:0x4
TEST_RR_OP(add,x0, x7, x19, 0xc, 0x8, 0x4, x3, 48, x18)

inst_13:
// opcode: add ; op1:x0; op2:x29; dest:x8; op1val:0x800;  op2val:0x8
TEST_RR_OP(add,x0, x23, x29, 0x808, 0x800, 0x8, x3, 52, x18)

inst_14:
// opcode: add ; op1:x0 op2:x27; dest:x13; op1val:0x0;  op2val:0x10
TEST_RR_OP(add,x0, x5, x27, 0x10, 0x0, 0x10, x3, 56, x18)

inst_15:
// opcode: add ; op1:x0; op2:x20; dest:x27; op1val:0x55555556;  op2val:0x20
TEST_RR_OP(add,x0, x25, x20, 0x55555576, 0x55555556, 0x20, x3, 60, x18)

inst_16:
// opcode: add ; op1:x0; op2:x26; dest:x17; op1val:-0x11;  op2val:0x40
TEST_RR_OP(add,x0, x15, x26, 0x2f, -0x11, 0x40, x3, 64, x18)

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
