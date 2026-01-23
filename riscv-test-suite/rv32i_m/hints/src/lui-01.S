/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 3, 2025
Description: This test verifies the lui instruction as a hint whatever the value in the register or imm val, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*32.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;", lui)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)


inst_0:
// opcode: lui ; dest:x0 immval:0x0
TEST_CASE(x7,x0, 0x0, x3, 0, lui x0, 0x0)

inst_1:
// opcode: lui ; dest:x0 immval:0x5
TEST_CASE(x7,x0, 0x5000, x3, 4, lui x0, 0x5)

inst_2:
// opcode: lui ; dest:x0; immval:0xfffff
TEST_CASE(x7,x0, -0x1000, x3, 8, lui x0,0xfffff)

inst_3:
// opcode: lui ; dest:x0; immval:0x3
TEST_CASE(x7,x0, 0x3000, x3, 12, lui x0,0x3)

inst_4:
// opcode: lui ; dest:x0 immval:0x55555
TEST_CASE(x7,x0, 0, x3, 16, lui x0, 0x55555)

inst_5:
// opcode: lui ; dest:x0 immval:0xaaaaa
TEST_CASE(x7,x0, -0x55556000, x3, 20, lui x0, 0xaaaaa)

inst_6:
// opcode: lui ; dest:x0; immval:0x33333
TEST_CASE(x7,x0, 0x33333000, x3, 24, lui x0,0x33333)

inst_7:
// opcode: lui ; dest:x0; immval:0x66666
TEST_CASE(x7,x0, 0x66666000, x3, 28, lui x0,0x66666)

inst_8:
// opcode: lui ; dest:x0; immval:0x2d4
TEST_CASE(x7,x0, 0x2d4000, x3, 32, lui x0,0x2d4)

inst_9:
// opcode: lui ; dest:x0 immval:0x3ff
TEST_CASE(x7,x0, 0x3ff000, x3, 36, lui x0, 0x3ff)

inst_10:
// opcode: lui ; dest:x0; immval:0x2
TEST_CASE(x7,x0, 0x2000, x3, 40, lui x0,0x2)

inst_11:
// opcode: lui ; dest:x0; immval:0x55554
TEST_CASE(x7,x0, 0x55554000, x3, 44, lui x0,0x55554)

inst_12:
// opcode: lui ; dest:x0 immval:0xaaaa9
TEST_CASE(x7,x0, -0x55557000, x3, 48, lui x0, 0xaaaa9)

inst_13:
// opcode: lui ; dest:x0; immval:0x4
TEST_CASE(x7,x0, 0x4000, x3, 52, lui x0,0x4)

inst_14:
// opcode: lui ; dest:x0; immval:0x33332
TEST_CASE(x7,x0, 0x33332000, x3, 56, lui x0,0x33332)

inst_15:
// opcode: lui ; dest:x0; immval:0x66665
TEST_CASE(x7,x0, 0x66665000, x3, 60, lui x0,0x66665)

inst_16:
// opcode: lui ; dest:x0; immval:0x2d3
TEST_CASE(x7,x0, 0x2d3000, x3, 64, lui x0,0x2d3)

inst_17:
// opcode: lui ; dest:x0 immval:0x3fe
TEST_CASE(x7,x0, 0x3fe000, x3, 68, lui x0, 0x3fe)

inst_18:
// opcode: lui ; dest:x0; immval:0x55556
TEST_CASE(x7,x0, 0x55556000, x3, 72, lui x0,0x55556)

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
