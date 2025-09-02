
/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 4, 2025
Description: This test verifies the and instruction as a hint whatever the value in the registers, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*64.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",and)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// rs1 == rs2 != rd, rs1==x7, rs2==x7, rd==x21, rs1_val > 0 and rs2_val > 0, rs2_val == 134217728, rs1_val == 64, rs1_val != rs2_val
// opcode: and ; op1:x7; op2:x7; dest:x21; op1val:0x40;  op2val:0x40
TEST_RR_OP(and,x0, x7, x7, 0x40, 0x40, 0x40, x3, 0, x16)

inst_1:
// rs2 == rd != rs1, rs1==x19, rs2==x11, rd==x11, rs1_val > 0 and rs2_val < 0, rs1_val == 4, rs2_val == -65537
// opcode: and ; op1:x19; op2:x11; dest:x11; op1val:0x4;  op2val:-0x10001
TEST_RR_OP(and,x0, x19, x11, 0x4, 0x4, -0x10001, x3, 8, x16)

inst_2:
// rs1 == rs2 == rd, rs1==x27, rs2==x27, rd==x27, rs1_val < 0 and rs2_val < 0, rs2_val == -134217729, rs1_val == -274877906945
// opcode: and ; op1:x27; op2:x27; dest:x27; op1val:-0x4000000001;  op2val:-0x4000000001
TEST_RR_OP(and,x0, x27, x27, 0xffffffbfffffffff, -0x4000000001, -0x4000000001, x3, 16, x16)

inst_3:
// rs1 != rs2  and rs1 != rd and rs2 != rd, rs1==x20, rs2==x23, rd==x14, rs1_val < 0 and rs2_val > 0, rs1_val == -134217729, rs2_val == 562949953421312
// opcode: and ; op1:x20; op2:x23; dest:x14; op1val:-0x8000001;  op2val:0x2000000000000
TEST_RR_OP(and,x0, x20, x23, 0x2000000000000, -0x8000001, 0x2000000000000, x3, 24, x16)

inst_4:
// rs1 == rd != rs2, rs1==x17, rs2==x18, rd==x17, rs1_val == rs2_val, 
// opcode: and ; op1:x17; op2:x18; dest:x17; op1val:-0x4000000000000000;  op2val:-0x4000000000000000
TEST_RR_OP(and,x0, x17, x18, 0xc000000000000000, -0x4000000000000000, -0x4000000000000000, x3, 32, x16)

inst_5:
// rs1==x18, rs2==x29, rd==x24, rs2_val == (-2**(xlen-1)), rs2_val == -9223372036854775808, rs1_val == -144115188075855873
// opcode: and ; op1:x18; op2:x29; dest:x24; op1val:-0x200000000000001;  op2val:-0x8000000000000000
TEST_RR_OP(and,x0, x18, x29, 0x8000000000000000, -0x200000000000001, -0x8000000000000000, x3, 40, x16)

inst_6:
// rs1==x28, rs2==x5, rd==x25, rs2_val == 0, rs1_val == 2147483648
// opcode: and ; op1:x28; op2:x5; dest:x25; op1val:0x80000000;  op2val:0x0
TEST_RR_OP(and,x0, x28, x5, 0x0, 0x80000000, 0x0, x3, 48, x16)

inst_7:
// rs1==x15, rs2==x3, rd==x22, rs2_val == (2**(xlen-1)-1), rs2_val == 9223372036854775807, rs1_val == 65536
// opcode: and ; op1:x15; op2:x3; dest:x22; op1val:0x10000;  op2val:0x7fffffffffffffff
TEST_RR_OP(and,x0, x15, x5, 0x10000, 0x10000, 0x7fffffffffffffff, x3, 56, x16)

inst_8:
// rs1==x0, rs2==x19, rd==x23, rs2_val == 1, rs1_val == 33554432
// opcode: and ; op1:x0; op2:x19; dest:x23; op1val:0x0;  op2val:0x1
TEST_RR_OP(and,x0, x0, x19, 0x0, 0x0, 0x1, x3, 64, x16)

inst_9:
// rs1==x21, rs2==x17, rd==x28, rs1_val == (-2**(xlen-1)), rs1_val == -9223372036854775808, rs2_val == 2
// opcode: and ; op1:x21; op2:x17; dest:x28; op1val:-0x8000000000000000;  op2val:0x2
TEST_RR_OP(and,x0, x21, x17, 0x0, -0x8000000000000000, 0x2, x3, 72, x16)

inst_10:
// rs1==x2, rs2==x10, rd==x7, rs1_val == 0, rs2_val == 274877906944
// opcode: and ; op1:x2; op2:x10; dest:x7; op1val:0x0;  op2val:0x4000000000
TEST_RR_OP(and,x0, x2, x10, 0x0, 0x0, 0x4000000000, x3, 80, x16)

inst_11:
// rs1==x1, rs2==x12, rd==x6, rs1_val == (2**(xlen-1)-1), rs1_val == 9223372036854775807, rs2_val == 256
// opcode: and ; op1:x1; op2:x12; dest:x6; op1val:0x7fffffffffffffff;  op2val:0x100
TEST_RR_OP(and,x0, x1, x12, 0x100, 0x7fffffffffffffff, 0x100, x3, 88, x16)

inst_12:
// rs1==x10, rs2==x21, rd==x3, rs1_val == 1, rs2_val == -140737488355329
// opcode: and ; op1:x10; op2:x21; dest:x3; op1val:0x1;  op2val:-0x800000000001
TEST_RR_OP(and,x0, x10, x21, 0x1, 0x1, -0x800000000001, x3, 96, x16)

inst_13:
// rs1==x12, rs2==x9, rd==x8, rs2_val == 4, rs1_val==3 and rs2_val==4
// opcode: and ; op1:x12; op2:x9; dest:x8; op1val:0x3;  op2val:0x4
TEST_RR_OP(and,x0, x12, x9, 0x0, 0x3, 0x4, x3, 104, x16)

inst_14:
// rs1==x9, rs2==x8, rd==x0, rs2_val == 8, 
// opcode: and ; op1:x9; op2:x8; dest:x0; op1val:-0x4000000000000000;  op2val:0x8
TEST_RR_OP(and,x0, x9, x8, 0, -0x4000000000000000, 0x8, x3, 112, x16)

inst_15:
// rs1==x25, rs2==x4, rd==x2, rs2_val == 16, rs1_val == 4611686018427387904
// opcode: and ; op1:x25; op2:x4; dest:x2; op1val:0x4000000000000000;  op2val:0x10
TEST_RR_OP(and,x0, x25, x4, 0x0, 0x4000000000000000, 0x10, x3, 120, x16)


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
