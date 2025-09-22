
/*
Copyright (c) 2020. RISC-V International. All rights reserved.
SPDX-License-Identifier: BSD-3-Clause

Developed By: Ubaid Rehman - https://github.com/itsubaidrehman
Date :  January 4, 2025
Description: This test verifies the auipc instruction as a hint whatever the value in the registers, 
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

RVTEST_CASE(0,"//check ISA:=regex(.*64.*);check ISA:=regex(.*I.*Zicsr);def TEST_CASE_1=True;",auipc)

RVTEST_INIT_GPRS
RVTEST_SIGBASE( x31,signature_x31_1)
TEST_STORE_GPRS_AND_STATUS(x31)

RVTEST_SIGBASE( x3,signature_x3_1)

inst_0:
// opcode: auipc ; dest:x20; immval:0x0
TEST_AUIPC(auipc,x0, 0x0, 0x0, x3, 0, x6)

inst_1:
// opcode: auipc ; dest:x18; immval:0xffdff
TEST_AUIPC(auipc,x0, -0x201000, 0xffdff, x3, 8, x6)

inst_2:
// opcode: auipc ; dest:x7; immval:0xfffff
TEST_AUIPC(auipc,x0, -0x1000, 0xfffff, x3, 16, x6)

inst_3:
// opcode: auipc ; dest:x23; immval:0x3
TEST_AUIPC(auipc,x0, 0x3000, 0x3, x3, 24, x6)

inst_4:
// opcode: auipc ; dest:x8; immval:0x55555
TEST_AUIPC(auipc,x0, 0x55555000, 0x55555, x3, 32, x6)

inst_5:
// opcode: auipc ; dest:x15; immval:0xaaaaa
TEST_AUIPC(auipc,x0, -0x55556000, 0xaaaaa, x3, 40, x6)

inst_6:
// opcode: auipc ; dest:x1; immval:0x5
TEST_AUIPC(auipc,x0, 0x5000, 0x5, x3, 48, x6)

inst_7:
// opcode: auipc ; dest:x11; immval:0x33333
TEST_AUIPC(auipc,x0, 0x33333000, 0x33333, x3, 56, x6)

inst_8:
// opcode: auipc ; dest:x10; immval:0x66666
TEST_AUIPC(auipc,x0, 0x66666000, 0x66666, x3, 64, x6)

inst_9:
// opcode: auipc ; dest:x19; immval:0x2d4
TEST_AUIPC(auipc,x0, 0x2d4000, 0x2d4, x3, 72, x6)

inst_10:
// opcode: auipc ; dest:x27; immval:0x3ff
TEST_AUIPC(auipc,x0, 0x3ff000, 0x3ff, x3, 80, x6)

inst_11:
// opcode: auipc ; dest:x26; immval:0x2
TEST_AUIPC(auipc,x0, 0x2000, 0x3, x3, 88, x6)

inst_12:
// opcode: auipc ; dest:x30; immval:0x55554
TEST_AUIPC(auipc,x0, 0x55554000, 0x55554, x3, 96, x6)

inst_13:
// opcode: auipc ; dest:x3; immval:0xaaaa9
TEST_AUIPC(auipc,x0, -0x55557000, 0xaaaa9, x3, 104, x6)

inst_14:
// opcode: auipc ; dest:x0; immval:0x4
TEST_AUIPC(auipc,x0, 0, 0x4, x3, 112, x6)

inst_15:
// opcode: auipc ; dest:x21; immval:0x33332
TEST_AUIPC(auipc,x0, 0x33332000, 0x33332, x3, 120, x6)


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
